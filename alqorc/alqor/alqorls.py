"""
Alqor — `alqor ls` (`alqorls`): Dil Serveri Protokolu (LSP).

Spesifikasiya § 13.7.

Redaktor (VS Code, Neovim, Helix, Alqor Studio…) bu serveri işə salıb
stdin/stdout üzərindən JSON-RPC 2.0 ilə danışır. Asılılıq yoxdur —
yalnız Python standart kitabxanası.

Dəstəklənən imkanlar (LSP 3.17 alt çoxluğu):

    textDocument/publishDiagnostics   leksik, sintaksis və tip xətaları
    textDocument/completion           `x.` → üzvlər; açar sözlər, adlar
    textDocument/hover                tip, imza, `///` sənədi
    textDocument/signatureHelp        `f(` → parametrlər
    textDocument/definition           elana get
    textDocument/references           bütün istifadələr
    textDocument/prepareRename,
    textDocument/rename               təhlükəsiz ad dəyişmə
    textDocument/documentSymbol       sənəd sxemi
    textDocument/formatting           alqorfmt
    textDocument/codeAction           ASCII → kanonik, homoqlif, "bəlkə"

Analiz mərhələləri `alqor yoxla` ilə eynidir: mənbə → lekser → parser →
tip yoxlayıcısı. Tip yoxlayıcısı `qeyd` rejimində işləyir: hər ad
istifadəsinin hansı elana bağlandığını və hər ifadənin tipini yadda
saxlayır — təyinata get, istinadlar və tamamlama bunun üzərində qurulur.

Fayl yazılarkən çox vaxt sintaksisi yarımçıq olur (`vidjet.` yazılıb,
ad hələ yox). Belə halda tamamlama SON UĞURLU analizdən istifadə edir.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import unquote, urlparse

from . import aac as A
from . import acar_sozler as AS
from . import tipler as T
from . import tipyoxlayici as TY
from .elifba import ad_başlanğıcı_ola_bilər, ad_davamı_ola_bilər
from .lekser import Lekser
from .menbe import Mənbə
from .parser import Parser
from .token import Növ, Token, Yer
from .xeta import Diaqnostika, Səviyyə, XətaToplayıcı

VERSİYA = "2.3.1"


# ═══════════════════════════════════════════════════════════════════════
#  Mövqelər: LSP (sətir, UTF-16 sütun, 0-dan) ↔ simvol indeksi
# ═══════════════════════════════════════════════════════════════════════

def _utf16_uzunluq(s: str) -> int:
    return sum(2 if ord(c) > 0xFFFF else 1 for c in s)


class Mövqelər:
    """Mətnin sətir başları — çevirmələr üçün."""

    def __init__(self, mətn: str):
        self.mətn = mətn
        self.başlar = [0]
        for i, c in enumerate(mətn):
            if c == "\n":
                self.başlar.append(i + 1)

    def lsp(self, ofset: int) -> dict:
        from bisect import bisect_right
        ofset = max(0, min(ofset, len(self.mətn)))
        s = bisect_right(self.başlar, ofset) - 1
        return {"line": s,
                "character": _utf16_uzunluq(
                    self.mətn[self.başlar[s]:ofset])}

    def ofset(self, pos: dict) -> int:
        sətir = pos.get("line", 0)
        if sətir >= len(self.başlar):
            return len(self.mətn)
        baş = self.başlar[sətir]
        son = (self.başlar[sətir + 1] - 1 if sətir + 1 < len(self.başlar)
               else len(self.mətn))
        qalan = pos.get("character", 0)
        i = baş
        while i < son and qalan > 0:
            qalan -= 2 if ord(self.mətn[i]) > 0xFFFF else 1
            i += 1
        return i

    def aralıq(self, baş: int, son: int) -> dict:
        return {"start": self.lsp(baş), "end": self.lsp(son)}


# ═══════════════════════════════════════════════════════════════════════
#  Analiz
# ═══════════════════════════════════════════════════════════════════════

ELAN_SİNİFLƏRİ = (A.FunksiyaElanı, A.SinifElanı, A.MetodElanı,
                  A.XassəElanı, A.QurucuElanı, A.DəyişənElanı,
                  A.InterfeysElanı, A.SadalamaElanı, A.ModulElanı,
                  A.TipAliası)


@dataclass
class Analiz:
    mətn: str
    mənbə: Mənbə
    mövqelər: Mövqelər
    tokenlər: list[Token]
    diaqnostikalar: list[Diaqnostika]
    ağac: A.Proqram | None = None
    dərinlik: dict[int, int] = field(default_factory=dict)
    yoxlayıcı: Any = None             # TipYoxlayıcı | None
    bağlamalar: list = field(default_factory=list)
    uğurlu: bool = False              # sintaksis xətasız
    elanlar: dict[int, Any] = field(default_factory=dict)  # başlanğıc → qovşaq
    siniflər: dict[str, A.SinifElanı] = field(default_factory=dict)

    # ── Tokenlər ──────────────────────────────────────────────────────

    def token_at(self, ofset: int) -> tuple[int, Token] | None:
        """`ofset`-i əhatə edən (və ya ondan dərhal əvvəl bitən) ad."""
        əvvəlki = None
        for i, t in enumerate(self.tokenlər):
            if t.yer.başlanğıc <= ofset < t.yer.son:
                return i, t
            if t.yer.son == ofset:
                əvvəlki = (i, t)
            if t.yer.başlanğıc > ofset:
                break
        return əvvəlki

    def token_indeksi(self, başlanğıc: int) -> int | None:
        for i, t in enumerate(self.tokenlər):
            if t.yer.başlanğıc == başlanğıc and t.növ is not Növ.SETIR_SONU:
                return i
            if t.yer.başlanğıc > başlanğıc:
                return None
        return None

    def ad_yeri(self, yer: Yer | None, ad: str) -> tuple[int, int] | None:
        """
        Elan yeri adətən açar sözdür (`funksiya`, `açıq`, `gətir`);
        adın özünün yerini irəlidəki tokenlərdə axtarırıq.
        """
        if yer is None:
            return None
        for t in self.tokenlər:
            if t.yer.başlanğıc < yer.başlanğıc:
                continue
            if t.növ is Növ.SETIR_SONU and t.yer.başlanğıc > yer.son:
                break
            if t.növ in (Növ.AD, Növ.ACAR) and t.dəyər == ad:
                return t.yer.başlanğıc, t.yer.son
        return None

    def üzv_adı_yeri(self, e: A.Üzv) -> tuple[int, int] | None:
        """`a.b` — `Üzv.yer` nöqtədir; ad ondan sonrakı tokendir."""
        i = self.token_indeksi(e.yer.başlanğıc)
        if i is None or i + 1 >= len(self.tokenlər):
            return None
        t = self.tokenlər[i + 1]
        return (t.yer.başlanğıc, t.yer.son) if t.dəyər == e.ad else None


def _qovşaqları_gəz(q: Any, ziyarət):
    """Ağacın bütün qovşaqları (dataclass sahələri üzrə)."""
    yığın = [q]
    görülən: set[int] = set()
    while yığın:
        x = yığın.pop()
        if isinstance(x, list | tuple):
            yığın.extend(reversed(x))
            continue
        if not is_dataclass(x) or isinstance(x, type) or id(x) in görülən:
            continue
        görülən.add(id(x))
        ziyarət(x)
        for f in fields(x):
            if f.name == "yer":
                continue
            v = getattr(x, f.name, None)
            if isinstance(v, list | tuple) or is_dataclass(v):
                yığın.append(v)


def analiz_et(mətn: str, ad: str = "<redaktor>",
              yol: Path | None = None, rejim: str = "normal") -> Analiz:
    x = XətaToplayıcı()
    m = Mənbə.mətndən(mətn, ad, x)
    m.yol = yol
    tokenlər = Lekser(m, x).leksə()
    a = Analiz(mətn, m, Mövqelər(m.mətn), tokenlər, [])
    p = Parser(tokenlər, m, x)
    p.dərinlik_qeydi = {}
    try:
        ağac = p.ayır()
    except Exception:                                   # noqa: BLE001
        ağac = None
    a.ağac = ağac
    a.dərinlik = p.dərinlik_qeydi
    a.uğurlu = ağac is not None and x.uğurludur()
    if a.uğurlu:
        rejim = _direktiv_rejimi(ağac, rejim)
        TY._QEYD_SİYAHISI = []
        try:
            y = TY.TipYoxlayıcı(x, rejim)
            y.qeyd = True
            y.yoxla(ağac)
            a.yoxlayıcı = y
        except Exception:                               # noqa: BLE001
            # Tip yoxlayıcısının daxili xətası redaktoru susdurmamalıdır
            a.yoxlayıcı = None
        finally:
            a.bağlamalar = TY._QEYD_SİYAHISI or []
            TY._QEYD_SİYAHISI = None

        def qeyd(q):
            if isinstance(q, ELAN_SİNİFLƏRİ) and q.yer is not None:
                a.elanlar.setdefault(q.yer.başlanğıc, q)
            if isinstance(q, A.Parametr) and q.yer is not None:
                a.elanlar.setdefault(q.yer.başlanğıc, q)
            if isinstance(q, A.SinifElanı | A.InterfeysElanı):
                a.siniflər.setdefault(q.ad, q)
        _qovşaqları_gəz(ağac, qeyd)
    a.diaqnostikalar = list(x.siyahı)
    return a


def _direktiv_rejimi(ağac: A.Proqram, standart: str) -> str:
    for d in ağac.direktivlər or []:
        for r in TY.REJİMLƏR:
            if re.search(rf"\btip\b.*\b{r}\b", d):
                return r
    return standart


# ═══════════════════════════════════════════════════════════════════════
#  Tiplər və üzvlər
# ═══════════════════════════════════════════════════════════════════════

def _üzvlər(a: Analiz, tip: T.Tip) -> dict[str, T.Tip]:
    tip = T.açılmış(tip)
    if isinstance(tip, T.ModulTipi):
        return dict(tip.üzvlər)
    if isinstance(tip, T.SinifTipi):
        n: dict[str, T.Tip] = {}
        s: T.SinifTipi | None = tip
        while s is not None:
            for d in (s.sahələr, s.metodlar, s.statiklər):
                for k, v in d.items():
                    n.setdefault(k, v)
            s = s.baza
        return n
    if isinstance(tip, T.SadalamaTipi):
        n = {v: tip for v in tip.variantlar}
        n.update(tip.metodlar)
        return n
    if a.yoxlayıcı is not None:
        c = a.yoxlayıcı._metod_cədvəli(tip)
        if c:
            return dict(c)
    return {}


def _adın_tipi(a: Analiz, ad: str, ofset: int) -> T.Tip | None:
    """Ad üçün tip — ən yaxın əvvəlki elan, sonra daxili adlar/modullar."""
    ən_yaxşı = None
    for b in a.bağlamalar:
        if b.ad == ad and b.yer is not None \
                and b.yer.başlanğıc <= ofset:
            if ən_yaxşı is None or b.yer.başlanğıc >= ən_yaxşı.yer.başlanğıc:
                ən_yaxşı = b
    if ən_yaxşı is not None:
        return ən_yaxşı.tip
    for b in a.bağlamalar:
        if b.ad == ad:
            return b.tip
    if a.yoxlayıcı is not None:
        b = a.yoxlayıcı.qlobal.adlar.get(ad)
        if b is not None:
            return b.tip
    if ad in TY._modullar():
        return TY._modullar()[ad]
    return None


def _zənciri_həll(a: Analiz, zəncir: list[str], ofset: int) -> T.Tip | None:
    """`["n", "nöqtə", "x"]` → `n.nöqtə.x`-in tipi."""
    if not zəncir:
        return None
    if zəncir[0] == "özü":
        tip = _özü_tipi(a, ofset)
    else:
        tip = _adın_tipi(a, zəncir[0], ofset)
    for ad in zəncir[1:]:
        if tip is None:
            return None
        tip = _üzvlər(a, tip).get(ad)
    return tip


def _özü_tipi(a: Analiz, ofset: int) -> T.Tip | None:
    """`ofset`-i əhatə edən sinif."""
    ən_yaxşı = None
    for s in a.siniflər.values():
        if s.yer.başlanğıc <= ofset and (
                ən_yaxşı is None
                or s.yer.başlanğıc > ən_yaxşı.yer.başlanğıc):
            ən_yaxşı = s
    if ən_yaxşı is None or a.yoxlayıcı is None:
        return None
    return a.yoxlayıcı.siniflər.get(ən_yaxşı.ad)


_ZƏNCİR = re.compile(r"((?:[^\W\d]\w*\s*\.\s*)*)([^\W\d]\w*)?$")


def _sətirdən_zəncir(sətir: str) -> tuple[list[str], str] | None:
    """
    Kursordan əvvəlki mətn `a.b.c` və ya `a.b.` ilə bitirsə — üzv
    tamamlamasıdır. Qaytarır: (obyekt zənciri, yazılmış ad başlanğıcı).
    """
    m = _ZƏNCİR.search(sətir)
    if not m or not m.group(1):
        return None
    zəncir = [p.strip() for p in m.group(1).split(".") if p.strip()]
    # Zəncirdən əvvəl çağırış/indeks varsa (`f().`) — bilmirik
    əvvəl = sətir[:m.start()].rstrip()
    if əvvəl.endswith((")", "]", '"')):
        return None
    return zəncir, m.group(2) or ""


# ═══════════════════════════════════════════════════════════════════════
#  Elanlar, istinadlar
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Hədəf:
    """Kursor altındakı simvol."""
    növ: str                      # "bağlama" | "üzv"
    ad: str
    bağlama: Any = None           # TY.Bağlama
    sinif: str | None = None      # üzv üçün — sahibi olan sinif
    tip: T.Tip | None = None
    obyekt: T.Tip | None = None
    aralıq: tuple[int, int] | None = None


def _açar(b) -> tuple:
    return (b.ad, b.yer.başlanğıc if b.yer is not None else -1)


def hədəfi_tap(a: Analiz, ofset: int) -> Hədəf | None:
    if a.yoxlayıcı is None:
        return None
    y = a.yoxlayıcı
    # 1. Ad istifadəsi
    for e, b in y.istinadlar:
        if e.yer.başlanğıc <= ofset <= e.yer.son:
            b = _mənşəyə(b)
            return Hədəf("bağlama", b.ad, b, tip=b.tip,
                         aralıq=(e.yer.başlanğıc, e.yer.son))
    # 1b. Fayl modulunun üzvü `m.f` — həmin fayldakı elan
    for e, b in getattr(y, "üzv_istinadları", ()):
        yer = a.üzv_adı_yeri(e)
        if yer and yer[0] <= ofset <= yer[1]:
            return Hədəf("bağlama", b.ad, b, tip=b.tip, aralıq=yer)
    # 2. Üzv müraciəti `a.b`
    for e, tip, obyekt in y.ifadə_tipləri:
        if not isinstance(e, A.Üzv):
            continue
        yer = a.üzv_adı_yeri(e)
        if yer and yer[0] <= ofset <= yer[1]:
            sinif = _sahib_sinif(obyekt, e.ad)
            return Hədəf("üzv", e.ad, sinif=sinif, tip=tip, obyekt=obyekt,
                         aralıq=yer)
    # 3. Elanın öz adı — əvvəlcə sinif üzvləri (qısa qurucunun
    # `açıq xassə x` parametri həm parametr, həm sahədir — sahə sayırıq)
    for q in a.elanlar.values():
        if not isinstance(q, A.MetodElanı | A.XassəElanı | A.Parametr):
            continue
        yer = a.ad_yeri(q.yer, q.ad)
        if yer and yer[0] <= ofset <= yer[1]:
            sinif = _elanın_sinfi(a, q)
            if sinif is not None and (
                    not isinstance(q, A.Parametr) or q.xassə_görünüşü):
                tip = None
                st = y.siniflər.get(sinif)
                if st is not None:
                    tip = st.üzv(q.ad)
                return Hədəf("üzv", q.ad, sinif=sinif, tip=tip,
                             obyekt=st, aralıq=yer)
    for b in a.bağlamalar:
        yer = a.ad_yeri(b.yer, b.ad)
        if yer and yer[0] <= ofset <= yer[1]:
            b = _mənşəyə(b)
            return Hədəf("bağlama", b.ad, b, tip=b.tip, aralıq=yer)
    return None


def _mənşəyə(b):
    """
    `gətir "./x.alq".{f}` — ləqəbsiz idxal olunan ad həmin fayldakı
    elanın özüdür (keçid, istinad, ad dəyişmə onun üzərindən gedir).
    `{f kimi g}` isə yerli addır.
    """
    m = getattr(b, "mənşə", None)
    return m if m is not None and m.ad == b.ad else b


def _yerlidir(a: Analiz, b) -> bool:
    return b is not None and b.yer is not None and b.yer.mənbə is a.mənbə


def bağlama_açarı(b) -> tuple | None:
    """Fayllar arası eyni elan: (fayl, ad, ofset)."""
    if b is None or b.yer is None:
        return None
    m = b.yer.mənbə
    yol = getattr(m, "yol", None)
    f = str(Path(yol).resolve()) if yol is not None else f"<{id(m)}>"
    return (f, b.ad, b.yer.başlanğıc)


def mənbədə_ad_yeri(m: Mənbə, yer: Yer, ad: str) -> tuple[int, int]:
    """Tokenləri olmayan (başqa fayldakı) elanın adının yeri."""
    mətn = m.mətn
    son = mətn.find("\n", yer.son)
    if son < 0:
        son = len(mətn)
    x = re.compile(r"(?<!\w)" + re.escape(ad) + r"(?!\w)").search(
        mətn, yer.başlanğıc, son)
    return x.span() if x else (yer.başlanğıc, yer.son)


def layihə_simvoludur(a: Analiz, h: Hədəf) -> bool:
    """Başqa fayllardan da görünə bilən elan (faylın qlobal adı)."""
    if h.növ != "bağlama" or h.bağlama is None or h.bağlama.yer is None:
        return False
    b = h.bağlama
    if b.elan_növü in ("daxili", "parametr", "modul", "idxal"):
        return False
    if not _yerlidir(a, b):
        return True
    if a.yoxlayıcı is None:
        return False
    return a.yoxlayıcı.qlobal.adlar.get(b.ad) is b


def fayl_istinadları(a: Analiz, açar: tuple, ad: str, elan_daxil: bool
                     ) -> list[tuple[int, int]]:
    """`a` faylında `açar` elanına bütün istinadlar (layihə üzrə)."""
    y = a.yoxlayıcı
    if y is None:
        return []
    nəticə: list[tuple[int, int]] = []
    if elan_daxil:
        for b in a.bağlamalar:
            if bağlama_açarı(b) == açar and _yerlidir(a, b):
                yer = a.ad_yeri(b.yer, b.ad)
                if yer:
                    nəticə.append(yer)
    for e, b in y.istinadlar:
        if bağlama_açarı(_mənşəyə(b)) == açar:
            nəticə.append((e.yer.başlanğıc, e.yer.son))
    for e, b in getattr(y, "üzv_istinadları", ()):
        if bağlama_açarı(b) == açar:
            yer = a.üzv_adı_yeri(e)
            if yer:
                nəticə.append(yer)
    # `gətir "./x.alq".{f, f kimi g}` — idxal siyahısındakı ad
    for b in a.bağlamalar:
        m = getattr(b, "mənşə", None)
        if m is not None and bağlama_açarı(m) == açar and _yerlidir(a, b):
            yer = a.ad_yeri(b.yer, m.ad)
            if yer:
                nəticə.append(yer)
    return sorted(set(nəticə))


def _sahib_sinif(obyekt: T.Tip | None, ad: str) -> str | None:
    s = obyekt if isinstance(obyekt, T.SinifTipi) else None
    while s is not None:
        if ad in s.sahələr or ad in s.metodlar or ad in s.statiklər:
            return s.ad
        s = s.baza
    return obyekt.ad if isinstance(obyekt, T.SinifTipi) else None


def _elanın_sinfi(a: Analiz, q: Any) -> str | None:
    for ad, s in a.siniflər.items():
        for ü in s.üzvlər:
            if ü is q:
                return ad
            if isinstance(ü, A.QurucuElanı) and any(
                    p is q for p in ü.parametrlər):
                return ad
    return None


def üzv_elanı(a: Analiz, sinif: str | None, ad: str) -> Any:
    """Sinif (və ya bazası) daxilində `ad` üzvünün AST qovşağı."""
    görülən = set()
    while sinif and sinif not in görülən:
        görülən.add(sinif)
        s = a.siniflər.get(sinif)
        if s is None:
            return None
        for ü in s.üzvlər:
            if getattr(ü, "ad", None) == ad and not isinstance(
                    ü, A.QurucuElanı):
                return ü
            if isinstance(ü, A.QurucuElanı):
                for p in ü.parametrlər:
                    if p.ad == ad and p.xassə_görünüşü:
                        return p
        st = a.yoxlayıcı.siniflər.get(sinif) if a.yoxlayıcı else None
        sinif = st.baza.ad if st is not None and st.baza else None
    return None


def təyinat(a: Analiz, h: Hədəf) -> tuple[int, int] | None:
    if h.növ == "bağlama":
        if h.bağlama is None or h.bağlama.yer is None:
            return None
        return a.ad_yeri(h.bağlama.yer, h.ad) or (
            h.bağlama.yer.başlanğıc, h.bağlama.yer.son)
    q = üzv_elanı(a, h.sinif, h.ad)
    if q is None:
        return None
    return a.ad_yeri(q.yer, h.ad)


def istinadlar(a: Analiz, h: Hədəf, elan_daxil: bool = True
               ) -> list[tuple[int, int]]:
    y = a.yoxlayıcı
    nəticə: list[tuple[int, int]] = []
    if h.növ == "bağlama":
        if h.bağlama is None or h.bağlama.yer is None:
            return []
        açar = _açar(h.bağlama)
        if elan_daxil:
            yer = a.ad_yeri(h.bağlama.yer, h.ad)
            if yer:
                nəticə.append(yer)
        for e, b in y.istinadlar:
            if _açar(b) == açar:
                nəticə.append((e.yer.başlanğıc, e.yer.son))
    else:
        if h.sinif is None:
            return []
        q = üzv_elanı(a, h.sinif, h.ad)
        sahib = _elanın_sinfi(a, q) if q is not None else h.sinif
        if elan_daxil and q is not None:
            yer = a.ad_yeri(q.yer, h.ad)
            if yer:
                nəticə.append(yer)
        if isinstance(q, A.Parametr) and q.yer is not None:
            # Qurucu gövdəsində parametr kimi işlənməsi (`x`, `özü.x` yox)
            for e, b in y.istinadlar:
                if b.yer is not None and _açar(b) == (
                        h.ad, q.yer.başlanğıc):
                    nəticə.append((e.yer.başlanğıc, e.yer.son))
        for e, _tip, obyekt in y.ifadə_tipləri:
            if isinstance(e, A.Üzv) and e.ad == h.ad \
                    and _sahib_sinif(obyekt, h.ad) == sahib:
                yer = a.üzv_adı_yeri(e)
                if yer:
                    nəticə.append(yer)
    return sorted(set(nəticə))


def adı_yoxla(ad: str) -> str | None:
    """Yeni ad düzgündürsə None, yoxsa səbəb."""
    if not ad or not ad_başlanğıcı_ola_bilər(ad[0]) \
            or not all(ad_davamı_ola_bilər(c) for c in ad[1:]):
        return f"`{ad}` düzgün ad deyil"
    if ad in AS.ACAR_SOZLER:
        return f"`{ad}` açar sözdür"
    return None


# ═══════════════════════════════════════════════════════════════════════
#  Hover, imza
# ═══════════════════════════════════════════════════════════════════════

def _imza_mətni(a: Analiz, q: Any) -> str:
    from .senedci import _imza
    try:
        return _imza(q, a.mənbə.mətn, a.tokenlər)
    except Exception:                                   # noqa: BLE001
        return getattr(q, "ad", "")


def hover_mətni(a: Analiz, h: Hədəf) -> str:
    hissələr: list[str] = []
    sənəd = ""
    if h.növ == "bağlama":
        b = h.bağlama
        q = a.elanlar.get(b.yer.başlanğıc) if _yerlidir(a, b) else None
        if q is not None and not isinstance(q, A.Parametr | A.İdxal) \
                and b.elan_növü in ("funksiya", "sinif", "sadalama",
                                    "tip", "modul"):
            imza = _imza_mətni(a, q)
            sənəd = getattr(q, "sənəd", None) or ""
        elif b.elan_növü == "daxili":
            imza = f"{b.ad}: {_tip_mətni(b.tip)}"
        elif b.yer is not None and not _yerlidir(a, b) and \
                isinstance(b.tip, T.FunksiyaTipi) and \
                b.elan_növü == "funksiya":
            imza = (f"funksiya {b.ad}("
                    f"{', '.join(_param_mətni(x) for x in b.tip.parametrlər)})"
                    f" -> {_tip_mətni(b.tip.qaytarma)}")
        elif b.elan_növü == "modul" or isinstance(b.tip, T.ModulTipi):
            imza = f"gətir {b.tip.ad}" if isinstance(
                b.tip, T.ModulTipi) else f"modul {b.ad}"
        else:
            söz = {"parametr": "parametr", "dəyişən": "dəyişən"}.get(
                b.elan_növü, b.elan_növü)
            if b.sabit and b.elan_növü == "dəyişən":
                söz = "sabit"
            imza = f"{söz} {b.ad}: {_tip_mətni(b.tip)}"
        hissələr.append(f"```alqor\n{imza}\n```")
    else:
        q = üzv_elanı(a, h.sinif, h.ad) if h.sinif else None
        if q is not None and not isinstance(q, A.Parametr):
            imza = _imza_mətni(a, q)
            sənəd = getattr(q, "sənəd", None) or ""
        else:
            sahib = (h.sinif or (h.obyekt.ad if isinstance(
                h.obyekt, T.ModulTipi) else
                _tip_mətni(h.obyekt) if h.obyekt else ""))
            imza = f"{sahib}.{h.ad}: {_tip_mətni(h.tip)}"
        hissələr.append(f"```alqor\n{imza}\n```")
        if isinstance(h.obyekt, T.ModulTipi) and h.obyekt.ad == "vidjet":
            sənəd = _vidjet_izahı(h.ad) or sənəd
    if sənəd:
        hissələr.append(sənəd.strip())
    if h.növ == "bağlama" and h.bağlama is not None and \
            h.bağlama.yer is not None and not _yerlidir(a, h.bağlama):
        yol = getattr(h.bağlama.yer.mənbə, "yol", None)
        if yol is not None:
            hissələr.append(f"*{Path(yol).name}*")
    return "\n\n".join(hissələr)


def _tip_mətni(t: T.Tip | None) -> str:
    if t is None:
        return "?"
    if isinstance(t, T.FunksiyaTipi):
        p = ", ".join(_param_mətni(x) for x in t.parametrlər)
        return f"({p}) -> {t.qaytarma.mətn()}"
    return t.mətn()


def _param_mətni(p: T.Parametr) -> str:
    ad = p.ad or "_"
    s = f"{'...' if p.variadic else ''}{ad}: {p.tip.mətn()}"
    return s + (" = …" if p.standartı_var else "")


def _vidjet_izahı(ad: str) -> str | None:
    try:
        from .vidjet import _KATALOQ_XƏRİTƏSİ
    except Exception:                                   # noqa: BLE001
        return None
    from .vidjet import BEYNƏLXALQ_ADLAR
    m = _KATALOQ_XƏRİTƏSİ.get(ad)
    if m is None:
        return None
    beynəlxalq = BEYNƏLXALQ_ADLAR.get(ad)
    return f"**{beynəlxalq}** — {m.izah}" if beynəlxalq else m.izah


# ═══════════════════════════════════════════════════════════════════════
#  Tamamlama
# ═══════════════════════════════════════════════════════════════════════

# LSP CompletionItemKind
K_METN, K_METOD, K_FUNKSIYA, K_QURUCU, K_SAHE, K_DEYISEN = 1, 2, 3, 4, 5, 6
K_SINIF, K_INTERFEYS, K_MODUL, K_XASSE, K_SADALAMA = 7, 8, 9, 10, 13
K_ACAR, K_SNIPPET, K_SABIT, K_VARIANT = 14, 15, 21, 20

ŞABLONLAR: dict[str, tuple[str, str]] = {
    "funksiya": ("funksiya ${1:ad}(${2}) -> ${3:heç}\n\t$0\nson",
                 "funksiya elanı"),
    "əgər": ("əgər ${1:şərt} onda\n\t$0\nson", "şərt"),
    "əgər…yoxsa": ("əgər ${1:şərt} onda\n\t${2}\nyoxsa\n\t$0\nson",
                   "şərt + əks hal"),
    "hər": ("hər ${1:x} üçün ${2:siyahı} içində\n\t$0\nson", "dövr"),
    "nə qədər ki": ("nə qədər ki ${1:şərt}\n\t$0\nson", "şərtli dövr"),
    "sinif": ("sinif ${1:Ad}\n\tqurucu(${2})\n\t$0\nson", "sinif elanı"),
    "metod": ("metod ${1:ad}(${2}) -> ${3:heç}\n\t$0\nson", "metod"),
    "cəhd et": ("cəhd et\n\t${1}\ntut ${2:x}\n\t$0\nson", "xəta tutma"),
    "seç": ("seç ${1:dəyər}\n\thal ${2:1} → ${3}\n\tdigər hallarda → $0\nson",
            "seç / hal"),
}


def _növ_kodu(tip: T.Tip | None, varsayılan: int = K_SAHE) -> int:
    if isinstance(tip, T.FunksiyaTipi):
        return K_FUNKSIYA
    if isinstance(tip, T.SinifTipi):
        return K_INTERFEYS if tip.quruluş == "interfeys" else K_SINIF
    if isinstance(tip, T.ModulTipi):
        return K_MODUL
    if isinstance(tip, T.SadalamaTipi):
        return K_SADALAMA
    return varsayılan


def üzv_tamamlaması(a: Analiz, zəncir: list[str], ofset: int
                    ) -> list[dict] | None:
    tip = _zənciri_həll(a, zəncir, ofset)
    if tip is None:
        return None
    vidjet = isinstance(tip, T.ModulTipi) and tip.ad == "vidjet"
    nəticə = []
    for ad, t in sorted(_üzvlər(a, tip).items()):
        if ad.startswith("_"):
            continue
        növ = _növ_kodu(t, K_SAHE)
        if isinstance(tip, T.SinifTipi) and növ == K_FUNKSIYA:
            növ = K_METOD
        if isinstance(tip, T.SadalamaTipi) and t is tip:
            növ = K_VARIANT
        maddə = {"label": ad, "kind": növ, "detail": _tip_mətni(t)}
        if vidjet:
            izah = _vidjet_izahı(ad)
            if izah:
                maddə["documentation"] = izah
        nəticə.append(maddə)
    return nəticə


def ümumi_tamamlama(a: Analiz | None, ofset: int, sətir: str
                    ) -> list[dict]:
    # `gətir ` → modul adları
    if re.match(r"^\s*(gətir|getir)\s+[\w.]*$", sətir):
        return [{"label": ad, "kind": K_MODUL, "detail": "modul"}
                for ad in sorted(TY._modullar())]
    nəticə: dict[str, dict] = {}
    for söz in sorted(AS.ACAR_SOZLER):
        nəticə[söz] = {"label": söz, "kind": K_ACAR}
    for ad, (gövdə, izah) in ŞABLONLAR.items():
        nəticə[ad + " …"] = {
            "label": ad + " …", "kind": K_SNIPPET, "detail": izah,
            "filterText": ad, "insertText": gövdə,
            "insertTextFormat": 2, "sortText": "0" + ad}
    for ad in sorted(AS.TIP_ADLARI):
        nəticə[ad] = {"label": ad, "kind": K_SINIF, "detail": "tip"}
    if a is not None and a.yoxlayıcı is not None:
        for ad, b in a.yoxlayıcı.qlobal.adlar.items():
            if b.elan_növü == "daxili" and not ad.startswith("_"):
                nəticə.setdefault(ad, {
                    "label": ad, "kind": _növ_kodu(b.tip, K_FUNKSIYA),
                    "detail": _tip_mətni(b.tip)})
    if a is not None:
        for b in a.bağlamalar:
            if b.ad.startswith("_") and b.elan_növü != "dəyişən":
                continue
            if b.ad == "özü":
                continue
            nəticə[b.ad] = {
                "label": b.ad,
                "kind": _növ_kodu(b.tip, K_DEYISEN),
                "detail": _tip_mətni(b.tip), "sortText": "1" + b.ad}
    return list(nəticə.values())


# ═══════════════════════════════════════════════════════════════════════
#  Sənəd sxemi
# ═══════════════════════════════════════════════════════════════════════

# LSP SymbolKind
S_MODUL, S_SINIF, S_METOD, S_XASSE, S_SAHE, S_QURUCU = 2, 5, 6, 7, 8, 9
S_SADALAMA, S_INTERFEYS, S_FUNKSIYA, S_DEYISEN, S_SABIT = 10, 11, 12, 13, 14
S_VARIANT = 22


def _blok_sonu(a: Analiz, baş: int) -> int:
    """Elanın son ofseti: dərinliyi elanınkından dərin olmayan, sonrakı
    sətirdəki ilk token (`son` daxil)."""
    i = a.token_indeksi(baş)
    if i is None:
        return baş
    d = a.dərinlik.get(baş, 0)
    sətir_sonu = a.mənbə.mətn.find("\n", baş)
    if sətir_sonu < 0:
        return len(a.mənbə.mətn)
    son = sətir_sonu
    for t in a.tokenlər[i + 1:]:
        if t.növ in (Növ.SETIR_SONU, Növ.FAYL_SONU):
            continue
        if t.yer.başlanğıc <= sətir_sonu:
            son = max(son, t.yer.son)
            continue
        td = a.dərinlik.get(t.yer.başlanğıc)
        if td is not None and td <= d:
            if t.növ is Növ.ACAR and t.dəyər == "son":
                return t.yer.son
            return son
        son = t.yer.son
    return son


def sənəd_sxemi(a: Analiz) -> list[dict]:
    if a.ağac is None:
        return []

    def simvol(q, ad: str, növ: int, uşaqlar=None, detail="") -> dict:
        baş = q.yer.başlanğıc
        son = _blok_sonu(a, baş)
        ad_yeri = a.ad_yeri(q.yer, ad) or (baş, q.yer.son)
        s = {"name": ad or "?", "kind": növ,
             "range": a.mövqelər.aralıq(baş, max(son, ad_yeri[1])),
             "selectionRange": a.mövqelər.aralıq(*ad_yeri)}
        if detail:
            s["detail"] = detail
        if uşaqlar:
            s["children"] = uşaqlar
        return s

    def elementlər(gövdə) -> list[dict]:
        n = []
        for q in gövdə or []:
            if q.yer is None:
                continue
            if isinstance(q, A.FunksiyaElanı):
                n.append(simvol(q, q.ad, S_FUNKSIYA,
                                detail=_imza_mətni(a, q)))
            elif isinstance(q, A.MetodElanı):
                n.append(simvol(q, q.ad, S_METOD,
                                detail=_imza_mətni(a, q)))
            elif isinstance(q, A.XassəElanı):
                n.append(simvol(q, q.ad, S_XASSE))
            elif isinstance(q, A.QurucuElanı):
                n.append(simvol(q, q.ad or "qurucu", S_QURUCU))
            elif isinstance(q, A.SinifElanı):
                n.append(simvol(q, q.ad, S_SINIF, elementlər(q.üzvlər)))
            elif isinstance(q, A.InterfeysElanı):
                n.append(simvol(q, q.ad, S_INTERFEYS,
                                elementlər(q.üzvlər)))
            elif isinstance(q, A.SadalamaElanı):
                variantlar = [simvol(v, v.ad, S_VARIANT)
                              for v in q.variantlar
                              if getattr(v, "yer", None) is not None]
                n.append(simvol(q, q.ad, S_SADALAMA,
                                variantlar + elementlər(q.üzvlər)))
            elif isinstance(q, A.ModulElanı):
                n.append(simvol(q, q.ad, S_MODUL, elementlər(q.gövdə)))
            elif isinstance(q, A.DəyişənElanı):
                for b in q.bağlamalar:
                    ad = getattr(b, "ad", None)
                    if isinstance(ad, str):
                        n.append(simvol(q, ad, S_DEYISEN
                                        if q.növ == "dəyişən"
                                        else S_SABIT))
        return n

    return elementlər(a.ağac.gövdə)


# ═══════════════════════════════════════════════════════════════════════
#  Kod linzaları, semantik rənglər
# ═══════════════════════════════════════════════════════════════════════

def _annotasiya(q: Any, ad: str) -> Any:
    for x in getattr(q, "annotasiyalar", None) or []:
        if x.ad == ad:
            return x
    return None


def _sınaq_adı(q: A.FunksiyaElanı) -> str | None:
    s = _annotasiya(q, "sınaq")
    if s is None and _annotasiya(q, "sınaqVerilənlər") is None:
        return None
    if s is not None and s.arqumentlər:
        d = s.arqumentlər[0].dəyər
        if isinstance(d, A.Literal) and isinstance(d.dəyər, str):
            return d.dəyər
    return q.ad


def kod_linzaları(a: Analiz, uri: str) -> list[dict]:
    """Üst səviyyə elanların üstündə: istinad sayı, `▶ Sına`."""
    if a.ağac is None:
        return []
    n: list[dict] = []

    def linza(q, ad: str) -> None:
        yer = a.ad_yeri(q.yer, ad)
        if yer is None:
            return
        n.append({"range": a.mövqelər.aralıq(*yer),
                  "data": {"uri": uri, "ofset": yer[0]}})

    def gəz(gövdə, qrup: bool) -> None:
        for q in gövdə or []:
            if q.yer is None:
                continue
            if isinstance(q, A.FunksiyaElanı):
                sınaq = _sınaq_adı(q)
                if sınaq is not None:
                    yer = a.ad_yeri(q.yer, q.ad)
                    if yer is not None:
                        n.append({"range": a.mövqelər.aralıq(*yer),
                                  "command": {
                                      "title": "▶ Sına",
                                      "command": "alqor.sına",
                                      "arguments": [uri, sınaq]}})
                    continue
                if not qrup:
                    linza(q, q.ad)
            elif isinstance(q, A.SinifElanı | A.InterfeysElanı
                            | A.SadalamaElanı) and not qrup:
                linza(q, q.ad)
            elif isinstance(q, A.ModulElanı):
                gəz(q.gövdə, qrup=True)

    gəz(a.ağac.gövdə, qrup=False)
    return n


SEMANTİK_NÖVLƏR = ["namespace", "class", "enum", "interface", "function",
                   "method", "property", "variable", "parameter", "type",
                   "enumMember", "typeParameter"]
SEMANTİK_ƏLAMƏTLƏR = ["declaration", "readonly", "defaultLibrary", "async"]
_SN = {ad: i for i, ad in enumerate(SEMANTİK_NÖVLƏR)}
_SƏ = {ad: 1 << i for i, ad in enumerate(SEMANTİK_ƏLAMƏTLƏR)}


def _tipə_görə(tip: T.Tip | None, varsayılan: str) -> str:
    if isinstance(tip, T.ModulTipi):
        return "namespace"
    if isinstance(tip, T.SinifTipi):
        return "interface" if tip.quruluş == "interfeys" else "class"
    if isinstance(tip, T.SadalamaTipi):
        return "enum"
    if isinstance(tip, T.FunksiyaTipi):
        return "function"
    return varsayılan


def _bağlama_növü(b) -> tuple[str, int]:
    növ = {"funksiya": "function", "parametr": "parameter",
           "tip": "type", "modul": "namespace"}.get(b.elan_növü)
    if b.elan_növü in ("sinif", "sadalama", "daxili", "idxal"):
        növ = _tipə_görə(b.tip, "variable")
    if növ is None:
        növ = _tipə_görə(b.tip, "variable") if isinstance(
            b.tip, T.FunksiyaTipi) else "variable"
    əl = 0
    if b.sabit and b.elan_növü == "dəyişən":
        əl |= _SƏ["readonly"]
    if b.elan_növü == "daxili":
        əl |= _SƏ["defaultLibrary"]
    if isinstance(b.tip, T.FunksiyaTipi) and b.tip.asinxron:
        əl |= _SƏ["async"]
    return növ, əl


def semantik_tokenlər(a: Analiz) -> list[int]:
    """LSP `semanticTokens/full` — nisbi kodlaşdırılmış 5-lik ardıcıllıq."""
    y = a.yoxlayıcı
    if y is None:
        return []
    tapılan: dict[int, tuple[int, str, int]] = {}

    def əlavə(baş: int, son: int, növ: str, əl: int = 0) -> None:
        if son > baş and baş not in tapılan:
            tapılan[baş] = (son, növ, əl)

    # Elanlar
    for b in a.bağlamalar:
        if not _yerlidir(a, b):
            continue
        yer = a.ad_yeri(b.yer, b.ad)
        if yer:
            növ, əl = _bağlama_növü(_mənşəyə(b))
            əlavə(*yer, növ, əl | _SƏ["declaration"])
    for q in a.elanlar.values():
        if isinstance(q, A.MetodElanı):
            yer = a.ad_yeri(q.yer, q.ad)
            if yer:
                əlavə(*yer, "method", _SƏ["declaration"])
        elif isinstance(q, A.XassəElanı):
            yer = a.ad_yeri(q.yer, q.ad)
            if yer:
                əlavə(*yer, "property", _SƏ["declaration"])
    # Ad istifadələri
    for e, b in y.istinadlar:
        if e.ad == "özü":
            continue
        növ, əl = _bağlama_növü(_mənşəyə(b))
        əlavə(e.yer.başlanğıc, e.yer.son, növ, əl)
    # Üzvlər `a.b`
    for e, tip, obyekt in y.ifadə_tipləri:
        if not isinstance(e, A.Üzv):
            continue
        yer = a.üzv_adı_yeri(e)
        if not yer:
            continue
        if isinstance(obyekt, T.ModulTipi):
            növ = _tipə_görə(tip, "variable")
            əl = _SƏ["defaultLibrary"] if not obyekt.elanlar else 0
        elif isinstance(obyekt, T.SadalamaTipi):
            növ, əl = "enumMember", 0
        else:
            növ = "method" if isinstance(tip, T.FunksiyaTipi) \
                else "property"
            əl = 0
        əlavə(*yer, növ, əl)

    data: list[int] = []
    əvvəlki_sətir = əvvəlki_sütun = 0
    for baş in sorted(tapılan):
        son, növ, əl = tapılan[baş]
        b = a.mövqelər.lsp(baş)
        e = a.mövqelər.lsp(son)
        if e["line"] != b["line"]:
            continue
        sətir, sütun = b["line"], b["character"]
        data += [sətir - əvvəlki_sətir,
                 sütun - (əvvəlki_sütun if sətir == əvvəlki_sətir else 0),
                 e["character"] - sütun, _SN[növ], əl]
        əvvəlki_sətir, əvvəlki_sütun = sətir, sütun
    return data


# ═══════════════════════════════════════════════════════════════════════
#  Diaqnostika, kod əməliyyatları
# ═══════════════════════════════════════════════════════════════════════

def _diaqnostika_lsp(a: Analiz, d: Diaqnostika) -> dict:
    if d.yer is not None and d.yer.mənbə is a.mənbə:
        baş, son = d.yer.başlanğıc, d.yer.son
        if son == baş:
            son = baş + 1
    else:
        baş = son = 0
    mesaj = d.mesaj + (f": {d.qeyd}" if d.qeyd else "")
    if d.köməklər:
        mesaj += "\n" + "\n".join(f"• {k}" for k in d.köməklər)
    s = {"range": a.mövqelər.aralıq(baş, son),
         "severity": 1 if d.səviyyə is Səviyyə.XETA else (
             2 if d.səviyyə is Səviyyə.XEBERDARLIQ else 3),
         "code": d.kod, "source": "alqor", "message": mesaj}
    if d.kod.startswith("ALQ-") and "istifadə olunmayıb" in d.mesaj:
        s["tags"] = [1]                                 # Unnecessary
    return s


_TƏKLİF = [
    re.compile(r"bəlkə:\s*`?([^\s`,]+)`?"),
    re.compile(r"`([^`]+)`\s+demək istəyirdiniz"),
    re.compile(r"kanonik forma:\s*(\S+)"),
]


def kod_əməliyyatları(a: Analiz, uri: str, baş: int, son: int
                      ) -> list[dict]:
    n: list[dict] = []
    for d in a.diaqnostikalar:
        if d.yer is None or d.yer.mənbə is not a.mənbə:
            continue
        if d.yer.son < baş or d.yer.başlanğıc > son:
            continue
        aralıq = a.mövqelər.aralıq(d.yer.başlanğıc, d.yer.son)
        əvəzlər: list[str] = []
        if d.kod == "ALQ-L014":
            continue        # mənbə artıq düzəldilib — aşağıdakı ümumi əməl
        for k in [d.qeyd, *d.köməklər]:
            for r in _TƏKLİF:
                for m in r.finditer(k or ""):
                    v = m.group(1).strip("'\"")
                    if v not in əvəzlər and (
                            not adı_yoxla(v) or v in AS.ACAR_SOZLER):
                        əvəzlər.append(v)
        for v in əvəzlər[:3]:
            n.append({
                "title": f"`{v}` ilə əvəz et",
                "kind": "quickfix",
                "diagnostics": [_diaqnostika_lsp(a, d)],
                "isPreferred": len(əvəzlər) == 1,
                "edit": {"changes": {uri: [
                    {"range": aralıq, "newText": v}]}}})
    ümumi = _hamısını_düzəlt(a, uri)
    if ümumi:
        n.append(ümumi)
    return n


def _hamısını_düzəlt(a: Analiz, uri: str) -> dict | None:
    kodlar = {d.kod for d in a.diaqnostikalar}
    if not kodlar & {"ALQ-L020", "ALQ-L014"}:
        return None
    from .alqorfmt import FormatXətası, formatla
    try:
        r = formatla(a.mətn, ascii_düzəlt=True, homoqlif_düzəlt=True,
                     boşluqlar=False)
    except FormatXətası:
        return None
    if not r.dəyişdi:
        return None
    return {"title": "ASCII açar sözləri və oxşar simvolları düzəlt",
            "kind": "source.fixAll.alqor",
            "edit": {"changes": {uri: [_bütün_mətn(a.mətn, r.mətn)]}}}


def _bütün_mətn(köhnə: str, yeni: str) -> dict:
    m = Mövqelər(köhnə)
    return {"range": m.aralıq(0, len(köhnə)), "newText": yeni}


# ═══════════════════════════════════════════════════════════════════════
#  Server
# ═══════════════════════════════════════════════════════════════════════

class Xəta(Exception):
    def __init__(self, kod: int, mesaj: str):
        super().__init__(mesaj)
        self.kod = kod


def uri_yolu(uri: str) -> Path | None:
    p = urlparse(uri)
    if p.scheme != "file":
        return None
    yol = unquote(p.path)
    if re.match(r"^/[A-Za-z]:", yol):          # file:///C:/...
        yol = yol[1:]
    return Path(yol)


@dataclass
class Sənəd:
    uri: str
    mətn: str
    versiya: int = 0
    analiz: Analiz | None = None
    son_uğurlu: Analiz | None = None
    bərpa: Analiz | None = None       # xətalı sətirlər boşaldılmış analiz
    lint: list = field(default_factory=list)   # alqorlint tapıntıları


class Server:
    def __init__(self, giriş: BinaryIO, çıxış: BinaryIO):
        self.giriş = giriş
        self.çıxış = çıxış
        self.sənədlər: dict[str, Sənəd] = {}
        self.bağlanır = False
        self.işləyir = True
        self.çıxış_kodu = 0
        self.rejim = "normal"
        self.lint = True                  # alqorlint diaqnostikaları
        self.köklər: list[Path] = []          # iş sahəsinin qovluqları
        self._disk_analizləri: dict[str, tuple[Any, Analiz]] = {}
        # Tip yoxlayıcısı idxal olunan faylı oxuyanda redaktordakı
        # (saxlanmamış) mətni görsün
        TY.FAYL_MƏTNİ = self._açıq_mətn

    # ── Nəqliyyat ─────────────────────────────────────────────────────

    def oxu(self) -> dict | None:
        uzunluq = None
        while True:
            sətir = self.giriş.readline()
            if not sətir:
                return None
            sətir = sətir.strip()
            if not sətir:
                break
            ad, _, dəyər = sətir.decode("ascii", "replace").partition(":")
            if ad.strip().lower() == "content-length":
                uzunluq = int(dəyər.strip())
        if uzunluq is None:
            return {}
        gövdə = self.giriş.read(uzunluq)
        try:
            return json.loads(gövdə.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._göndər({"jsonrpc": "2.0", "id": None, "error": {
                "code": -32700, "message": "JSON ayrıla bilmədi"}})
            return {}

    def _göndər(self, m: dict) -> None:
        b = json.dumps(m, ensure_ascii=False).encode("utf-8")
        self.çıxış.write(b"Content-Length: %d\r\n\r\n" % len(b) + b)
        self.çıxış.flush()

    def bildiriş(self, metod: str, parametrlər: Any) -> None:
        self._göndər({"jsonrpc": "2.0", "method": metod,
                      "params": parametrlər})

    # ── Dövr ──────────────────────────────────────────────────────────

    def işlət(self) -> int:
        while self.işləyir:
            m = self.oxu()
            if m is None:
                break
            if m:
                self.emal(m)
        return self.çıxış_kodu

    def emal(self, m: dict) -> None:
        metod = m.get("method")
        id_ = m.get("id")
        if metod is None:
            return                                      # cavab — gözləmirik
        işləyici = self.METODLAR.get(metod)
        try:
            if işləyici is None:
                if id_ is not None:
                    raise Xəta(-32601, f"metod dəstəklənmir: {metod}")
                return
            if self.bağlanır and metod not in ("exit",):
                raise Xəta(-32600, "server bağlanır")
            nəticə = işləyici(self, m.get("params") or {})
            if id_ is not None:
                self._göndər({"jsonrpc": "2.0", "id": id_,
                              "result": nəticə})
        except Xəta as x:
            if id_ is not None:
                self._göndər({"jsonrpc": "2.0", "id": id_, "error": {
                    "code": x.kod, "message": str(x)}})
        except Exception as x:                          # noqa: BLE001
            print(traceback.format_exc(), file=sys.stderr)
            if id_ is not None:
                self._göndər({"jsonrpc": "2.0", "id": id_, "error": {
                    "code": -32603,
                    "message": f"daxili xəta: {type(x).__name__}: {x}"}})

    # ── Həyat dövrü ───────────────────────────────────────────────────

    def m_initialize(self, p: dict) -> dict:
        seçimlər = p.get("initializationOptions") or {}
        if seçimlər.get("tipRejimi") in TY.REJİMLƏR:
            self.rejim = seçimlər["tipRejimi"]
        if "lint" in seçimlər:
            self.lint = bool(seçimlər["lint"])
        köklər = [q.get("uri") for q in p.get("workspaceFolders") or []]
        if not köklər and p.get("rootUri"):
            köklər = [p["rootUri"]]
        for uri in köklər:
            yol = uri_yolu(uri or "")
            if yol is not None and yol.is_dir():
                self.köklər.append(yol)
        if not self.köklər and p.get("rootPath"):
            if Path(p["rootPath"]).is_dir():
                self.köklər.append(Path(p["rootPath"]))
        return {
            "capabilities": {
                "positionEncoding": "utf-16",
                "textDocumentSync": {"openClose": True, "change": 1,
                                     "save": {"includeText": False}},
                "completionProvider": {"triggerCharacters": ["."],
                                       "resolveProvider": False},
                "hoverProvider": True,
                "signatureHelpProvider": {"triggerCharacters": ["(", ","]},
                "definitionProvider": True,
                "referencesProvider": True,
                "workspaceSymbolProvider": True,
                "codeLensProvider": {"resolveProvider": True},
                "semanticTokensProvider": {
                    "legend": {"tokenTypes": SEMANTİK_NÖVLƏR,
                               "tokenModifiers": SEMANTİK_ƏLAMƏTLƏR},
                    "full": True},
                "renameProvider": {"prepareProvider": True},
                "documentSymbolProvider": True,
                "documentFormattingProvider": True,
                "codeActionProvider": {"codeActionKinds": [
                    "quickfix", "source.fixAll.alqor"]},
            },
            "serverInfo": {"name": "alqorls", "version": VERSİYA},
        }

    def m_initialized(self, p: dict) -> None:
        return None

    def m_shutdown(self, p: dict) -> None:
        self.bağlanır = True
        return None

    def m_exit(self, p: dict) -> None:
        self.çıxış_kodu = 0 if self.bağlanır else 1
        self.işləyir = False

    # ── Sənədlərin sinxronlaşdırılması ────────────────────────────────

    def _yenilə(self, s: Sənəd) -> None:
        yol = uri_yolu(s.uri)
        ad = yol.name if yol else s.uri.rsplit("/", 1)[-1]
        s.analiz = analiz_et(s.mətn, ad, yol, self.rejim)
        s.bərpa = None
        if s.analiz.uğurlu and s.analiz.yoxlayıcı is not None:
            s.son_uğurlu = s.analiz
        else:
            sətirlər = {d.yer.sətir - 1 for d in s.analiz.diaqnostikalar
                        if d.xətadır and d.yer is not None
                        and d.yer.mənbə is s.analiz.mənbə}
            if sətirlər and len(sətirlər) <= 5:
                s.bərpa = self._sətirsiz_analiz(s, *sətirlər)
        diaq = [_diaqnostika_lsp(s.analiz, d)
                for d in s.analiz.diaqnostikalar]
        s.lint = self._lint(s, yol)
        for t in s.lint:
            d = _diaqnostika_lsp(s.analiz, t.diaqnostika())
            d["source"] = "alqorlint"
            diaq.append(d)
        self.bildiriş("textDocument/publishDiagnostics", {
            "uri": s.uri, "version": s.versiya, "diagnostics": diaq})

    def _lint(self, s: "Sənəd", yol: Path | None) -> list:
        """`alqorlint` qaydaları (tip yoxlayıcısının tapdıqları xaric —
        onlar artıq diaqnostikadadır)."""
        a = s.analiz
        if not self.lint or not a.uğurlu or a.ağac is None:
            return []
        try:
            from . import alqorlint as AL
            ayar = AL.ayar_oxu(yol.parent if yol else ".")
            y = AL.Yoxlayıcı(a.mənbə, a.ağac, {**AL.STANDART_AYAR, **ayar},
                             str(yol) if yol else "")
            return AL.süz(y.işlət(), a.mətn, a.mənbə, ayar)
        except Exception:                                   # noqa: BLE001
            return []

    def m_didOpen(self, p: dict) -> None:
        td = p["textDocument"]
        s = Sənəd(td["uri"], td.get("text", ""), td.get("version", 0))
        self.sənədlər[s.uri] = s
        self._yenilə(s)

    def m_didChange(self, p: dict) -> None:
        td = p["textDocument"]
        s = self.sənədlər.get(td["uri"])
        if s is None:
            return
        for d in p.get("contentChanges", []):
            if "range" in d:                     # artımlı — dəstəkləsək də
                m = Mövqelər(s.mətn)
                b = m.ofset(d["range"]["start"])
                e = m.ofset(d["range"]["end"])
                s.mətn = s.mətn[:b] + d["text"] + s.mətn[e:]
            else:
                s.mətn = d["text"]
        s.versiya = td.get("version", s.versiya)
        self._yenilə(s)
        self._asılıları_yenilə(s)

    def m_didClose(self, p: dict) -> None:
        uri = p["textDocument"]["uri"]
        self.sənədlər.pop(uri, None)
        self.bildiriş("textDocument/publishDiagnostics",
                      {"uri": uri, "diagnostics": []})

    def m_didSave(self, p: dict) -> None:
        return None

    def _asılıları_yenilə(self, s: Sənəd) -> None:
        """Bu faylı `gətir` edən açıq sənədlər yenidən yoxlanır."""
        yol = uri_yolu(s.uri)
        if yol is None:
            return
        for d in list(self.sənədlər.values()):
            if d is not s and "gətir" in d.mətn and yol.stem in d.mətn:
                self._yenilə(d)

    # ── Layihə (iş sahəsi) ────────────────────────────────────────────

    def _açıq_mətn(self, yol: Path) -> str | None:
        for d in self.sənədlər.values():
            p = uri_yolu(d.uri)
            if p is not None and _eyni_fayl(p, yol):
                return d.mətn
        return None

    def _uri(self, yol: Path) -> str:
        for d in self.sənədlər.values():
            p = uri_yolu(d.uri)
            if p is not None and _eyni_fayl(p, yol):
                return d.uri
        return Path(yol).resolve().as_uri()

    def layihə_faylları(self) -> list[Path]:
        """Açıq sənədlər + iş sahəsindəki bütün `.alq` faylları."""
        görülən: set[str] = set()
        n: list[Path] = []

        def əlavə(p: Path) -> None:
            açar = str(p.resolve())
            if açar not in görülən:
                görülən.add(açar)
                n.append(p)

        for d in self.sənədlər.values():
            p = uri_yolu(d.uri)
            if p is not None:
                əlavə(p)
        for kök in self.köklər:
            for p in _alqor_faylları(kök):
                əlavə(p)
        return n

    def fayl_analizi(self, yol: Path) -> Analiz | None:
        for d in self.sənədlər.values():
            p = uri_yolu(d.uri)
            if p is not None and _eyni_fayl(p, yol):
                return self._naviqasiya(d)
        try:
            st = yol.stat()
            açar = str(yol.resolve())
        except OSError:
            return None
        vəziyyət = (st.st_mtime_ns, st.st_size, self.rejim)
        köhnə = self._disk_analizləri.get(açar)
        if köhnə is not None and köhnə[0] == vəziyyət:
            return köhnə[1]
        try:
            mətn = yol.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        a = analiz_et(mətn, yol.name, yol, self.rejim)
        self._disk_analizləri[açar] = (vəziyyət, a)
        return a

    def layihə_istinadları(self, a: Analiz, h: Hədəf, elan_daxil: bool
                           ) -> list[tuple[str, Analiz, tuple[int, int]]]:
        """(uri, analiz, aralıq) — bütün layihə faylları üzrə."""
        açar = bağlama_açarı(h.bağlama)
        n: list[tuple[str, Analiz, tuple[int, int]]] = []
        cari = a.mənbə.yol
        if cari is None:                     # adsız sənəd — yalnız özü
            return [("", a, y) for y in fayl_istinadları(
                a, açar, h.ad, elan_daxil)]
        for yol in self.layihə_faylları():
            if _eyni_fayl(yol, cari):
                fa = a
            else:
                mətn = self._açıq_mətn(yol)
                if mətn is None:
                    try:
                        mətn = yol.read_text(encoding="utf-8")
                    except (OSError, UnicodeDecodeError):
                        continue
                if h.ad not in mətn:
                    continue
                fa = self.fayl_analizi(yol)
                if fa is None:
                    continue
            uri = self._uri(yol)
            for y in fayl_istinadları(fa, açar, h.ad, elan_daxil):
                n.append((uri, fa, y))
        return n

    def m_codeLens(self, p: dict) -> list:
        s = self._sənəd(p)
        a = s.analiz if s.analiz.ağac is not None else self._naviqasiya(s)
        return kod_linzaları(a, s.uri)

    def m_codeLens_resolve(self, p: dict) -> dict:
        data = p.get("data") or {}
        s = self.sənədlər.get(data.get("uri", ""))
        if s is None:
            return {**p, "command": {"title": "", "command": ""}}
        a = self._naviqasiya(s)
        ofset = data.get("ofset", 0)
        h = hədəfi_tap(a, ofset)
        yerlər: list[dict] = []
        if h is not None:
            if layihə_simvoludur(a, h):
                yerlər = [{"uri": uri or s.uri,
                           "range": fa.mövqelər.aralıq(*y)}
                          for uri, fa, y in self.layihə_istinadları(
                              a, h, False)]
            else:
                yerlər = [{"uri": s.uri, "range": a.mövqelər.aralıq(*y)}
                          for y in istinadlar(a, h, False)]
        n = len(yerlər)
        başlıq = "istinad yoxdur" if n == 0 else f"{n} istinad"
        return {**p, "command": {
            "title": başlıq, "command": "alqor.istinadlarıGöstər",
            "arguments": [s.uri, a.mövqelər.lsp(ofset), yerlər]}}

    def m_semanticTokens(self, p: dict) -> dict:
        s = self._sənəd(p)
        a = self._naviqasiya(s)
        return {"data": semantik_tokenlər(a)}

    def m_symbol(self, p: dict) -> list:
        sorğu = (p.get("query") or "").casefold()
        n: list[dict] = []
        for yol in self.layihə_faylları():
            a = self.fayl_analizi(yol)
            if a is None:
                continue
            uri = self._uri(yol)

            def gəz(simvollar, konteyner=None):
                for x in simvollar:
                    if _uyğundur(sorğu, x["name"]):
                        m = {"name": x["name"], "kind": x["kind"],
                             "location": {"uri": uri,
                                          "range": x["selectionRange"]}}
                        if konteyner:
                            m["containerName"] = konteyner
                        n.append(m)
                    gəz(x.get("children") or [], x["name"])
            gəz(sənəd_sxemi(a))
            if len(n) >= 500:
                break
        return n[:500]

    # ── Sorğular ──────────────────────────────────────────────────────

    def _sənəd(self, p: dict) -> Sənəd:
        uri = p["textDocument"]["uri"]
        s = self.sənədlər.get(uri)
        if s is None:
            yol = uri_yolu(uri)
            if yol is None or not yol.is_file():
                raise Xəta(-32602, f"sənəd açılmayıb: {uri}")
            s = Sənəd(uri, yol.read_text(encoding="utf-8"))
            self.sənədlər[uri] = s
            self._yenilə(s)
        return s

    def _yer(self, s: Sənəd, p: dict) -> tuple[Analiz, int]:
        a = self._naviqasiya(s)
        return a, a.mövqelər.ofset(p["position"])

    def m_completion(self, p: dict) -> dict:
        s = self._sənəd(p)
        a = s.analiz                       # həqiqi mətn (bərpa yox)
        ofset = a.mövqelər.ofset(p["position"])
        sətir_başı = a.mövqelər.başlar[p["position"]["line"]] \
            if p["position"]["line"] < len(a.mövqelər.başlar) else ofset
        sətir = a.mənbə.mətn[sətir_başı:ofset]
        istinad = self._tamamlama_analizi(s, p["position"]["line"])
        z = _sətirdən_zəncir(sətir)
        if z is not None:
            zəncir, _ = z
            maddələr = (üzv_tamamlaması(istinad, zəncir, ofset)
                        if istinad else None) or []
            return {"isIncomplete": False, "items": maddələr}
        if _şərhdə_və_ya_mətndə(sətir):
            return {"isIncomplete": False, "items": []}
        return {"isIncomplete": False,
                "items": ümumi_tamamlama(istinad, ofset, sətir)}

    def _sətirsiz_analiz(self, s: Sənəd, *nömrələr: int) -> Analiz | None:
        """
        Yarımçıq sətir (`s.`) bütün faylın analizini pozur. Həmin
        sətirləri EYNİ UZUNLUQDA boşluqla əvəz edib yenidən analiz
        edirik: qalan elanlar görünür, bütün ofsetlər də dəyişmir.
        """
        sətirlər = s.mətn.split("\n")
        for n in nömrələr:
            if 0 <= n < len(sətirlər):
                sətirlər[n] = " " * len(sətirlər[n])
        a = analiz_et("\n".join(sətirlər), yol=uri_yolu(s.uri),
                      rejim=self.rejim)
        return a if a.yoxlayıcı is not None else None

    def _naviqasiya(self, s: Sənəd) -> Analiz:
        """Hover, keçid, istinad üçün analiz — xətalı halda bərpa olunmuş."""
        if s.analiz.yoxlayıcı is None and s.bərpa is not None:
            return s.bərpa
        return s.analiz

    def _tamamlama_analizi(self, s: Sənəd, sətir: int) -> Analiz | None:
        if s.analiz.yoxlayıcı is not None:
            return s.analiz
        return (self._sətirsiz_analiz(s, sətir) or s.bərpa
                or s.son_uğurlu)

    def m_hover(self, p: dict) -> dict | None:
        s = self._sənəd(p)
        a, ofset = self._yer(s, p)
        h = hədəfi_tap(a, ofset)
        if h is None:
            return None
        return {"contents": {"kind": "markdown",
                             "value": hover_mətni(a, h)},
                "range": a.mövqelər.aralıq(*h.aralıq)}

    def m_signatureHelp(self, p: dict) -> dict | None:
        s = self._sənəd(p)
        a = s.analiz
        ofset = a.mövqelər.ofset(p["position"])
        istinad = self._tamamlama_analizi(s, p["position"]["line"])
        if istinad is None:
            return None
        çağırış = _açıq_çağırış(a.mənbə.mətn, ofset)
        if çağırış is None:
            return None
        zəncir, aktiv = çağırış
        tip = _zənciri_həll(istinad, zəncir, ofset)
        if isinstance(tip, T.SinifTipi):
            tip = tip.quruculər.get("")
        if not isinstance(tip, T.FunksiyaTipi):
            return None
        parametrlər = [_param_mətni(x) for x in tip.parametrlər]
        etiket = (f"{'.'.join(zəncir)}({', '.join(parametrlər)})"
                  f" -> {tip.qaytarma.mətn()}")
        return {"signatures": [{
            "label": etiket,
            "parameters": [{"label": x} for x in parametrlər]}],
            "activeSignature": 0,
            "activeParameter": min(aktiv, max(0, len(parametrlər) - 1))}

    def m_definition(self, p: dict) -> list | None:
        s = self._sənəd(p)
        a, ofset = self._yer(s, p)
        h = hədəfi_tap(a, ofset)
        if h is None:
            return None
        b = h.bağlama
        if h.növ == "bağlama" and b is not None and b.yer is not None \
                and not _yerlidir(a, b):
            m = b.yer.mənbə
            if getattr(m, "yol", None) is None:
                return None
            return [{"uri": self._uri(Path(m.yol)),
                     "range": Mövqelər(m.mətn).aralıq(
                         *mənbədə_ad_yeri(m, b.yer, b.ad))}]
        yer = təyinat(a, h)
        if yer is None:
            return None
        return [{"uri": s.uri, "range": a.mövqelər.aralıq(*yer)}]

    def m_references(self, p: dict) -> list:
        s = self._sənəd(p)
        a, ofset = self._yer(s, p)
        h = hədəfi_tap(a, ofset)
        if h is None:
            return []
        daxil = (p.get("context") or {}).get("includeDeclaration", True)
        if layihə_simvoludur(a, h):
            return [{"uri": uri or s.uri, "range": fa.mövqelər.aralıq(*y)}
                    for uri, fa, y in self.layihə_istinadları(a, h, daxil)]
        return [{"uri": s.uri, "range": a.mövqelər.aralıq(*y)}
                for y in istinadlar(a, h, daxil)]

    def _adlandırıla_bilər(self, a: Analiz, ofset: int) -> Hədəf:
        h = hədəfi_tap(a, ofset)
        if h is None:
            raise Xəta(-32602, "burada adı dəyişdiriləcək simvol yoxdur")
        if h.növ == "bağlama" and (
                h.bağlama is None or h.bağlama.yer is None
                or h.bağlama.elan_növü in ("daxili",)):
            raise Xəta(-32602, f"`{h.ad}` daxili addır — dəyişdirilə bilməz")
        if h.növ == "bağlama" and h.bağlama.elan_növü in ("modul", "idxal") \
                and h.ad == h.bağlama.ad and _modul_adıdır(h.ad):
            raise Xəta(-32602, f"`{h.ad}` modul adıdır — `gətir {h.ad} "
                               "kimi yeniAd` yazın")
        if h.ad == "özü":
            raise Xəta(-32602, "`özü` dəyişdirilə bilməz")
        if h.növ == "üzv" and üzv_elanı(a, h.sinif, h.ad) is None:
            raise Xəta(-32602, f"`{h.ad}` bu faylda elan olunmayıb")
        return h

    def m_prepareRename(self, p: dict) -> dict | None:
        s = self._sənəd(p)
        a, ofset = self._yer(s, p)
        try:
            h = self._adlandırıla_bilər(a, ofset)
        except Xəta:
            return None
        return {"range": a.mövqelər.aralıq(*h.aralıq),
                "placeholder": h.ad}

    def m_rename(self, p: dict) -> dict:
        s = self._sənəd(p)
        a, ofset = self._yer(s, p)
        yeni = p.get("newName", "")
        səbəb = adı_yoxla(yeni)
        if səbəb:
            raise Xəta(-32602, səbəb)
        h = self._adlandırıla_bilər(a, ofset)
        if layihə_simvoludur(a, h):
            dəyişikliklər: dict[str, list] = {}
            for uri, fa, y in self.layihə_istinadları(a, h, True):
                dəyişikliklər.setdefault(uri or s.uri, []).append(
                    {"range": fa.mövqelər.aralıq(*y), "newText": yeni})
            return {"changes": dəyişikliklər}
        yerlər = istinadlar(a, h, True)
        return {"changes": {s.uri: [
            {"range": a.mövqelər.aralıq(*y), "newText": yeni}
            for y in yerlər]}}

    def m_documentSymbol(self, p: dict) -> list:
        s = self._sənəd(p)
        return sənəd_sxemi(s.analiz)

    def m_formatting(self, p: dict) -> list | None:
        s = self._sənəd(p)
        from .alqorfmt import FormatXətası, formatla
        try:
            r = formatla(s.mətn, s.uri.rsplit("/", 1)[-1])
        except FormatXətası as x:
            self.bildiriş("window/showMessage",
                          {"type": 2, "message": f"alqorfmt: {x}"})
            return None
        if not r.dəyişdi or r.mətn == s.mətn:
            return []
        return [_bütün_mətn(s.mətn, r.mətn)]

    def m_codeAction(self, p: dict) -> list:
        s = self._sənəd(p)
        a = s.analiz
        r = p.get("range") or {"start": {"line": 0, "character": 0},
                               "end": {"line": 0, "character": 0}}
        b, e = a.mövqelər.ofset(r["start"]), a.mövqelər.ofset(r["end"])
        n = kod_əməliyyatları(a, s.uri, b, e)
        for t in getattr(s, "lint", None) or []:
            if not t.düzəliş or t.yer is None or not (
                    t.yer.başlanğıc <= e and b <= t.yer.son):
                continue
            db, de, yeni = t.düzəliş
            n.append({
                "title": f"Düzəlt: {t.qeyd}" if "→" in t.qeyd
                else f"Düzəlt [{t.qayda.ad}]",
                "kind": "quickfix",
                "diagnostics": [_diaqnostika_lsp(a, t.diaqnostika())],
                "edit": {"changes": {s.uri: [{
                    "range": a.mövqelər.aralıq(db, de),
                    "newText": yeni}]}}})
        return n

    METODLAR = {
        "initialize": m_initialize,
        "initialized": m_initialized,
        "shutdown": m_shutdown,
        "exit": m_exit,
        "textDocument/didOpen": m_didOpen,
        "textDocument/didChange": m_didChange,
        "textDocument/didClose": m_didClose,
        "textDocument/didSave": m_didSave,
        "textDocument/completion": m_completion,
        "textDocument/hover": m_hover,
        "textDocument/signatureHelp": m_signatureHelp,
        "textDocument/definition": m_definition,
        "textDocument/references": m_references,
        "textDocument/prepareRename": m_prepareRename,
        "textDocument/rename": m_rename,
        "textDocument/documentSymbol": m_documentSymbol,
        "textDocument/formatting": m_formatting,
        "textDocument/codeAction": m_codeAction,
        "workspace/symbol": m_symbol,
        "textDocument/codeLens": m_codeLens,
        "codeLens/resolve": m_codeLens_resolve,
        "textDocument/semanticTokens/full": m_semanticTokens,
    }


_GİZLİ_QOVLUQLAR = {"node_modules", "__pycache__", "hədəf", "hedef",
                    "dist", "build", "venv", ".venv"}


def _alqor_faylları(kök: Path, hədd: int = 2000) -> list[Path]:
    n: list[Path] = []
    try:
        for p in sorted([*kök.rglob("*.alq"), *kök.rglob("*.alqor")]):
            hissələr = p.relative_to(kök).parts[:-1]
            if any(h.startswith(".") or h in _GİZLİ_QOVLUQLAR
                   for h in hissələr):
                continue
            n.append(p)
            if len(n) >= hədd:
                break
    except OSError:
        pass
    return n


def _eyni_fayl(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == Path(b).resolve()
    except OSError:
        return False


def _uyğundur(sorğu: str, ad: str) -> bool:
    """Boş sorğu hər şeyə; yoxsa hərflər ardıcıllıqla (`tpl` → `topla`)."""
    if not sorğu:
        return True
    i = 0
    for c in ad.casefold():
        if i < len(sorğu) and c == sorğu[i]:
            i += 1
    return i == len(sorğu)


def _modul_adıdır(ad: str) -> bool:
    return ad in TY._modullar()


def _şərhdə_və_ya_mətndə(sətir: str) -> bool:
    """Kursor `//` şərhindədir və ya bağlanmamış dırnaq içindədir."""
    dırnaq = False
    i = 0
    while i < len(sətir):
        c = sətir[i]
        if dırnaq:
            if c == "\\":
                i += 1
            elif c == '"':
                dırnaq = False
        elif c == '"':
            dırnaq = True
        elif sətir.startswith("//", i):
            return True
        i += 1
    return dırnaq


def _açıq_çağırış(mətn: str, ofset: int) -> tuple[list[str], int] | None:
    """Kursoru əhatə edən bağlanmamış `(` — (funksiya zənciri, vergül sayı)."""
    dərinlik = 0
    vergül = 0
    i = ofset - 1
    sətir_sayı = 0
    while i >= 0:
        c = mətn[i]
        if c == "\n":
            sətir_sayı += 1
            if sətir_sayı > 20:
                return None
        elif c in ")]}":
            dərinlik += 1
        elif c in "[{":
            if dərinlik == 0:
                return None
            dərinlik -= 1
        elif c == "(":
            if dərinlik == 0:
                break
            dərinlik -= 1
        elif c == "," and dərinlik == 0:
            vergül += 1
        i -= 1
    else:
        return None
    əvvəl = mətn[max(0, i - 200):i]
    m = re.search(r"([^\W\d]\w*(?:\s*\.\s*[^\W\d]\w*)*)\s*$", əvvəl)
    if not m:
        return None
    zəncir = [x.strip() for x in m.group(1).split(".")]
    if zəncir[-1] in AS.ACAR_SOZLER:
        return None
    return zəncir, vergül


def işə_sal(giriş: BinaryIO | None = None,
            çıxış: BinaryIO | None = None) -> int:
    giriş = giriş or sys.stdin.buffer
    if çıxış is None:
        çıxış = sys.stdout.buffer
        # Protokol kanalını qoruyuruq: təsadüfi `print` stderr-ə getsin
        sys.stdout = sys.stderr
    return Server(giriş, çıxış).işlət()


if __name__ == "__main__":
    sys.exit(işə_sal())
