"""
Alqor — `alqorfmt`: kod formatlayıcısı.

Spesifikasiya § 13.3.

TƏHLÜKƏSİZLİK — FORMATLAYICI KODU POZA BİLMƏZ
─────────────────────────────────────────────
Format edilmiş mətn yenidən leksə və ayrılır. Token axını (ASCII
açar sözlərin kanonik forması istisna) və sintaksis ağacı (mövqelər
nəzərə alınmadan) orijinalla EYNİ olmalıdır. Fərq çıxarsa nəticə
atılır və `FormatXətası` qaldırılır — fayl toxunulmaz qalır.

GİRİNTİ PARSERDƏN GƏLİR
───────────────────────
Açar sözləri sayan evristika əvəzinə parser hər tokenin hansı blok
dərinliyində istehlak olunduğunu qeyd edir (`Parser.dərinlik_qeydi`).
Məntiqi sətrin girintisi = 4 × ilk tokeninin dərinliyi. Mötərizə
içində davam edən sətirlər nisbi girintisini saxlayır (hizalama
qorunur). Çoxsətirli mətn və JSX tokenlərinin içi yalnız sürüşdürülür.

NƏ EDİR
───────
  • girinti: 4 boşluq, blok strukturuna görə
  • ASCII açar sözlər → kanonik forma (`eger` → `əgər`)
  • sətir daxilində: vergüldən sonra bir boşluq, ikili operator
    ətrafında bir boşluq, mötərizə daxilində boşluq yox
  • sətir sonundakı boşluqlar, ardıcıl boş sətirlər (ən çox 2),
    faylın sonunda tək `\\n`, CRLF → LF, BOM, NFC
  • şərhlər, sətir sonu şərhlərinin hizalanması qorunur

NƏ ETMİR (hələ)
──────────────
  • uzun sətirləri bölmək — `alqorlint` xəbərdarlıq edəcək
  • çoxsətirli siyahılara sondakı vergül əlavə etmək
"""

from __future__ import annotations

import dataclasses
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import acar_sozler as AS
from . import aac as A
from .lekser import Lekser
from .menbe import Mənbə
from .parser import Parser
from .token import Növ, Token
from .xeta import XətaToplayıcı

GİRİNTİ = 4
MAKS_BOŞ_SƏTİR = 2


class FormatXətası(Exception):
    """Fayl format edilə bilmir — toxunulmaz qalır."""


@dataclass
class Nəticə:
    mətn: str
    dəyişdi: bool
    ascii_düzəlişləri: int = 0
    homoqlif_düzəlişləri: int = 0
    qeydlər: list[str] = field(default_factory=list)

    def fərq(self, köhnə: str, ad: str = "fayl") -> str:
        return "".join(difflib.unified_diff(
            köhnə.splitlines(keepends=True),
            self.mətn.splitlines(keepends=True),
            f"{ad} (köhnə)", f"{ad} (yeni)"))


# ═══════════════════════════════════════════════════════════════════════
#  Ayırma
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class _Ayrılmış:
    mənbə: Mənbə
    tokenlər: list[Token]
    ağac: Any
    dərinlik: dict[int, int]


def _ayır(mətn: str, ad: str) -> _Ayrılmış:
    x = XətaToplayıcı()
    m = Mənbə.mətndən(mətn, ad, x)
    tokenlər = Lekser(m, x, ascii_xəbərdarlığı=False).leksə()
    p = Parser(tokenlər, m, x)
    p.dərinlik_qeydi = {}
    ağac = p.ayır()
    if not x.uğurludur():
        ilk = x.xətalar[0]
        raise FormatXətası(
            f"faylda sintaksis xətası var — əvvəlcə onu düzəldin "
            f"({ilk.kod}: {ilk.mesaj}, {ilk.yer})")
    return _Ayrılmış(m, tokenlər, ağac, p.dərinlik_qeydi)


# ═══════════════════════════════════════════════════════════════════════
#  Doğrulama — nəticə orijinalla eyni proqramdır
# ═══════════════════════════════════════════════════════════════════════

def _token_imzası(tokenlər: list[Token]) -> list[tuple]:
    imza: list[tuple] = []
    for t in tokenlər:
        if t.növ in (Növ.SETIR_SONU, Növ.FAYL_SONU):
            continue
        if t.növ is Növ.JSX:
            # Dəyəri ofsetlərdir — mətni müqayisə edilir (aşağıda)
            imza.append((t.növ, None))
            continue
        imza.append((t.növ, t.dəyər if not isinstance(t.dəyər, list)
                     else repr(t.dəyər)))
    return imza


def _ağac_imzası(q: Any) -> Any:
    """AST-in mövqesiz təsviri."""
    if isinstance(q, list):
        return [_ağac_imzası(e) for e in q]
    if isinstance(q, tuple):
        return tuple(_ağac_imzası(e) for e in q)
    if dataclasses.is_dataclass(q) and not isinstance(q, type):
        sahələr = []
        for f in dataclasses.fields(q):
            if f.name in ("yer", "sənəd"):
                continue
            sahələr.append((f.name, _ağac_imzası(getattr(q, f.name))))
        return (type(q).__name__, tuple(sahələr))
    if isinstance(q, dict):
        return tuple(sorted((k, _ağac_imzası(v)) for k, v in q.items()))
    return q


def _jsx_mətnləri(a: _Ayrılmış) -> list[str]:
    """JSX tokenlərinin mətni — sətir başı boşluqları nəzərə alınmadan."""
    nəticə = []
    for t in a.tokenlər:
        if t.növ is Növ.JSX:
            b, s = t.dəyər
            nəticə.append(" ".join(a.mənbə.mətn[b:s].split()))
    return nəticə


def _doğrula(köhnə: _Ayrılmış, yeni_mətn: str, ad: str) -> None:
    try:
        yeni = _ayır(yeni_mətn, ad)
    except FormatXətası as x:
        raise FormatXətası(
            f"daxili xəta: format edilmiş kod ayrılmır ({x}) — fayl "
            "dəyişdirilmədi") from None
    if _token_imzası(köhnə.tokenlər) != _token_imzası(yeni.tokenlər):
        raise FormatXətası("daxili xəta: token axını dəyişdi — fayl "
                           "dəyişdirilmədi")
    if _jsx_mətnləri(köhnə) != _jsx_mətnləri(yeni):
        raise FormatXətası("daxili xəta: JSX dəyişdi — fayl "
                           "dəyişdirilmədi")
    if _ağac_imzası(köhnə.ağac) != _ağac_imzası(yeni.ağac):
        raise FormatXətası("daxili xəta: proqramın quruluşu dəyişdi — "
                           "fayl dəyişdirilmədi")


# ═══════════════════════════════════════════════════════════════════════
#  Sətir daxilində boşluqlar
# ═══════════════════════════════════════════════════════════════════════

# İki tərəfində bir boşluq olan ikili operatorlar
İKİLİ = frozenset({
    "=", "+=", "-=", "*=", "/=", "~/=", "%=", "**=", "??=",
    "==", "!=", "<", ">", "<=", ">=", "<=>", "===", "!==",
    "+", "-", "*", "/", "~/", "%", "**", "??", "->", "=>", "→",
    "&", "|", "^", "<<", ">>",
})
# Özündən əvvəl boşluq olmayanlar
ƏVVƏLSİZ = frozenset({",", ")", "]", ".", "?.", ";", "!", ":", "++",
                      "--", "..", "..<"})
# Özündən sonra boşluq olmayanlar
SONRASIZ = frozenset({"(", "[", ".", "?.", "@", "...", "..", "..<"})
# Bu tokenlərdən sonra gələn `-`/`+` təkli operatordur
OPERAND_SONU = (Növ.AD, Növ.TAM, Növ.ONLUQ, Növ.METN, Növ.SIMVOL,
                Növ.BAYT, Növ.JSX)
OPERAND_SONU_OP = frozenset({")", "]", "}", "!", "++", "--"})
OPERAND_SONU_ACAR = frozenset({"doğru", "yanlış", "boş", "özü", "üst"})


def _operand_sonudur(t: Token | None) -> bool:
    if t is None:
        return False
    if t.növ in OPERAND_SONU:
        return True
    if t.növ is Növ.OP:
        return t.dəyər in OPERAND_SONU_OP
    if t.növ is Növ.ACAR:
        return t.dəyər in OPERAND_SONU_ACAR
    return False


def _arasında(əvvəlki: Token, cari: Token, əvvəlkindən_əvvəl: Token | None,
              orijinal: str) -> str:
    """İki token arasındakı boşluq. `orijinal` — mənbədəki boşluq."""
    a = əvvəlki.dəyər if əvvəlki.növ is Növ.OP else None
    b = cari.dəyər if cari.növ is Növ.OP else None

    # Təkli `-x`, `+x`, `!x`: operatordan sonra boşluq yox
    if a in ("-", "+") and not _operand_sonudur(əvvəlkindən_əvvəl):
        return ""
    if b in İKİLİ:
        if b in ("-", "+") and not _operand_sonudur(əvvəlki):
            # Təkli: `f(-1)`, `[-2]`, `a + -4`, `qaytar -x`
            if a in SONRASIZ:
                return ""
            if a == "," or a == ":" or a in İKİLİ \
                    or əvvəlki.növ is Növ.ACAR:
                return " "
            return " " if orijinal else ""
        if b in ("<", ">") and a in ("[",):
            return ""
        return " "
    if a in İKİLİ:
        return " "
    if b in ƏVVƏLSİZ:
        # `ad: dəyər`, `x: tam` — iki nöqtədən əvvəl boşluq yox
        return ""
    if a == ",":
        return " "
    if a == ":":
        return " "
    if a in SONRASIZ:
        return ""
    if b in ("(", "["):
        # Çağırış və indeks: `f(x)`, `s[0]`. Açar sözdən sonra
        # (`əgər (a)`, `qaytar [1]`) orijinal saxlanılır; nöqtədən
        # sonrakı açar söz üzv adıdır: `s.statik(...)`, `veb.boş(204)`
        if (əvvəlki.növ is Növ.ACAR and əvvəlkindən_əvvəl is not None
                and əvvəlkindən_əvvəl.növ is Növ.OP
                and əvvəlkindən_əvvəl.dəyər in (".", "?.")):
            return ""
        if əvvəlki.növ is Növ.ACAR:
            return " " if orijinal else ""
        return ""
    if b in ("{",) or a in ("}",):
        return " " if orijinal else ""
    if a == "{":
        return " " if orijinal else ""
    if b == "}":
        return " " if orijinal else ""
    # Qalan hallarda: orijinalda boşluq varsa bir boşluq
    return " " if orijinal else ""


# ═══════════════════════════════════════════════════════════════════════
#  Formatlama
# ═══════════════════════════════════════════════════════════════════════

def formatla(mətn: str, ad: str = "<mətn>", ascii_düzəlt: bool = True,
             homoqlif_düzəlt: bool = False,
             boşluqlar: bool = True) -> Nəticə:
    """
    Mətni format edir. Sintaksis xətası olan və ya doğrulamadan
    keçməyən mətn üçün `FormatXətası` qaldırır.
    """
    a = _ayır(mətn, ad)
    if a.mənbə.homoqliflər and not homoqlif_düzəlt:
        h = a.mənbə.homoqliflər[0]
        raise FormatXətası(
            f"faylda {len(a.mənbə.homoqliflər)} oxşar simvol (homoqlif) "
            f"var, məs. {h.kod} {h.ad} — `--homoqlif-düzəlt` ilə "
            "işlədin")

    yeni, ascii_say = _qur(a, ascii_düzəlt, boşluqlar)
    try:
        _doğrula(a, yeni, ad)
    except FormatXətası:
        if not boşluqlar:
            raise
        # Sətir daxili boşluqlar səbəb olubsa — yalnız girinti
        yeni, ascii_say = _qur(a, ascii_düzəlt, False)
        _doğrula(a, yeni, ad)

    return Nəticə(yeni, yeni != mətn, ascii_say,
                  len(a.mənbə.homoqliflər))


def _qur(a: _Ayrılmış, ascii_düzəlt: bool,
         boşluqlar: bool) -> tuple[str, int]:
    """
    Girinti alqoritmi. Hər kod sətri üçün ilk tokeninin:
      • parser dərinliyi `d` (neçə blok gövdəsinin içindədir),
      • mötərizə yığını `Y` (hansı açıq `(` `[` `{` içindədir)
    məlumdur.

      Y boşdur, məntiqi sətir başı
        və ya dərinlik dəyişib       → 4·d
      Y boşdur, davam sətri          → köhnə + son məntiqi sətrin sürüşməsi
      Y doludur, d mötərizəni açan sətrin dərinliyindən fərqlidir və ya
      sətir yeni cümlədir            → eyni Y-li ən yaxın "lövbər" sətrə
                                       nisbətən: lövbər + 4·(d − d_lövbər)
      Y doludur, qalan hallar        → köhnə + mötərizəni açan sətrin
                                       sürüşməsi (hizalama qorunur)

    Belə ki, `vidjet.sütun(məzmun: [ … əgər … yoxsa … son ])` kimi
    mötərizə içindəki çoxsətirli bloklar da düzgün girintilənir.
    """
    m = a.mənbə.mətn
    sətirlər = m.split("\n")
    başlar = [0]
    for s in sətirlər[:-1]:
        başlar.append(başlar[-1] + len(s) + 1)

    tokenlər = [t for t in a.tokenlər
                if t.növ not in (Növ.FAYL_SONU, Növ.SENED, Növ.DIREKTIV)]

    def sətir_nömrəsi(ofset: int) -> int:
        lo, hi = 0, len(başlar) - 1
        while lo < hi:
            orta = (lo + hi + 1) // 2
            if başlar[orta] <= ofset:
                lo = orta
            else:
                hi = orta - 1
        return lo

    # ── Token → sətir, çoxsətirli tokenlər, mötərizə yığını ──────────
    sətir_tokenləri: dict[int, list[int]] = {}
    örtülü: dict[int, int] = {}
    yığın_qeydi: dict[int, tuple[int, ...]] = {}    # token → açıq mötərizələr
    yığın: list[int] = []
    məntiqi_baş: set[int] = set()
    əvvəlki: Token | None = None
    for i, t in enumerate(tokenlər):
        if t.növ is Növ.SETIR_SONU:
            əvvəlki = t
            continue
        if əvvəlki is None or əvvəlki.növ is Növ.SETIR_SONU or (
                əvvəlki.növ is Növ.OP and əvvəlki.dəyər == ";"):
            məntiqi_baş.add(i)
        yığın_qeydi[i] = tuple(yığın)
        if t.növ is Növ.OP:
            if t.dəyər in ("(", "[", "{"):
                yığın.append(i)
            elif t.dəyər in (")", "]", "}") and yığın:
                yığın.pop()
        b = t.yer.başlanğıc
        sb = sətir_nömrəsi(b)
        sətir_tokenləri.setdefault(sb, []).append(i)
        ss = sətir_nömrəsi(max(b, b + t.yer.uzunluq - 1))
        for n in range(sb + 1, ss + 1):
            örtülü[n] = i
        əvvəlki = t

    def köhnə_girinti(n: int) -> int:
        s = sətirlər[n]
        baş = s[:len(s) - len(s.lstrip(" \t"))]
        return len(baş.expandtabs(GİRİNTİ))

    def dərinlik(i: int) -> int:
        return a.dərinlik.get(tokenlər[i].yer.başlanğıc, 0)

    # ── Kod sətirlərinin yeni girintisi ──────────────────────────────
    girinti: dict[int, int] = {}
    sürüşmə: dict[int, int] = {}            # sətir → yeni − köhnə
    son_məntiqi_sürüşmə = 0
    son_məntiqi_dərinlik = 0
    # Mötərizə yığını → həmin yığınla başlayan sətirlər (lövbərlər)
    yığın_sətirləri: dict[tuple[int, ...], list[int]] = {}

    for n in range(len(sətirlər)):
        if n in örtülü or n not in sətir_tokenləri:
            continue
        i = sətir_tokenləri[n][0]
        Y = yığın_qeydi[i]
        d = dərinlik(i)
        köhnə = köhnə_girinti(n)
        baş = i in məntiqi_baş

        if not Y:
            # `onda`, `et` kimi sözlərdən sonra lekser sətir sonu
            # buraxmır — gövdənin ilk sətri dərinliyin artmasından tanınır
            if baş or d != son_məntiqi_dərinlik:
                g = d * GİRİNTİ
                son_məntiqi_sürüşmə = g - köhnə
                son_məntiqi_dərinlik = d
            else:
                g = köhnə + son_məntiqi_sürüşmə
        else:
            açan_sətir = sətir_nömrəsi(tokenlər[Y[-1]].yer.başlanğıc)
            açan_ilk = sətir_tokenləri[açan_sətir][0]
            d_açan = dərinlik(açan_ilk)
            if baş or d != d_açan:
                lövbər = None
                for k in reversed(yığın_sətirləri.get(Y, [])):
                    if dərinlik(sətir_tokenləri[k][0]) <= d:
                        lövbər = k
                        break
                if lövbər is not None:
                    d_l = dərinlik(sətir_tokenləri[lövbər][0])
                    g = girinti[lövbər] + GİRİNTİ * (d - d_l)
                else:
                    g = girinti[açan_sətir] + GİRİNTİ * max(0, d - d_açan)
                    if d == d_açan:
                        # Mötərizədəki ilk cümlə: köhnə nisbi girinti
                        g = köhnə + sürüşmə.get(açan_sətir, 0)
            else:
                g = köhnə + sürüşmə.get(açan_sətir, 0)
                # Davam sətri açan sətirdən ən azı bir pillə dərin olur;
                # bağlayan mötərizə ilə başlayan sətir isə onunla hizalanır
                t0 = tokenlər[i]
                if t0.növ is Növ.OP and t0.dəyər in (")", "]", "}"):
                    g = max(g, girinti[açan_sətir])
                else:
                    g = max(g, girinti[açan_sətir] + GİRİNTİ)
        g = max(0, g)
        girinti[n] = g
        sürüşmə[n] = g - köhnə
        yığın_sətirləri.setdefault(Y, []).append(n)

    BAĞLAYANLAR = ("son", "yoxsa", "yoxsa əgər", "tut", "nəhayət",
                   "hal", "digər hallarda")

    def şərh_girintisi(n: int) -> int:
        for k in range(n + 1, len(sətirlər)):
            if k in girinti:
                t = tokenlər[sətir_tokenləri[k][0]]
                if t.növ is Növ.ACAR and t.dəyər in BAĞLAYANLAR:
                    return girinti[k] + GİRİNTİ
                return girinti[k]
        return 0

    # ── Çıxış ────────────────────────────────────────────────────────
    ascii_say = 0
    çıxış: list[str] = []
    boş_say = 0
    for n, xam in enumerate(sətirlər):
        sətir = xam.rstrip(" \t")

        # Çoxsətirli tokenin (mətn, JSX) içi — yalnız sürüşdürülür
        if n in örtülü:
            t = tokenlər[örtülü[n]]
            d = sürüşmə.get(sətir_nömrəsi(t.yer.başlanğıc), 0)
            sürüşən = t.növ is Növ.JSX or (
                t.növ is Növ.METN and m.startswith(
                    ('"""', 'x"""'), t.yer.başlanğıc))
            if sürüşən and d and sətir.strip():
                if d > 0:
                    sətir = " " * d + sətir
                else:
                    kəs = min(-d, len(sətir) - len(sətir.lstrip(" ")))
                    sətir = sətir[kəs:]
            elif not sürüşən:
                sətir = xam
            çıxış.append(sətir.rstrip(" \t") if sürüşən else sətir)
            boş_say = 0
            continue

        if not sətir.strip():
            boş_say += 1
            if boş_say <= MAKS_BOŞ_SƏTİR:
                çıxış.append("")
            continue
        boş_say = 0

        if n not in girinti:                        # yalnız şərh
            çıxış.append(" " * şərh_girintisi(n) + sətir.lstrip(" \t"))
            continue

        sayğac = [0]
        mətn_hissəsi = _sətri_qur(sətir, başlar[n], sətir_tokenləri[n],
                                  tokenlər, m, ascii_düzəlt, boşluqlar,
                                  sayğac)
        ascii_say += sayğac[0]
        çıxış.append(" " * girinti[n] + mətn_hissəsi.lstrip(" \t"))

    while çıxış and not çıxış[-1].strip():
        çıxış.pop()
    return "\n".join(çıxış) + "\n", ascii_say


def _sətri_qur(sətir: str, sətir_başı: int, indekslər: list[int],
               tokenlər: list[Token], m: str, ascii_düzəlt: bool,
               boşluqlar: bool, sayğac: list[int]) -> str:
    """
    Sətrin token hissəsini yenidən qurur: ASCII açar sözlər kanonik
    formaya, tokenlər arası boşluqlar qaydaya görə. Sətir sonundakı
    şərh (və ondan əvvəlki boşluq — hizalama) olduğu kimi qalır.
    """
    hissələr: list[str] = []
    son_ofset: int | None = None
    sətir_sonu = sətir_başı + len(sətir)
    ilk = indekslər[0]
    # Təkli/ikili operatoru ayırmaq üçün əvvəlki sətrin tokenləri də
    # nəzərə alınır: `+ "…"` davam sətrində ikilidir
    əvvəlki = tokenlər[ilk - 1] if ilk > 0 else None
    əvvəlkindən_əvvəl = tokenlər[ilk - 2] if ilk > 1 else None

    for i in indekslər:
        t = tokenlər[i]
        b = t.yer.başlanğıc
        s = min(b + t.yer.uzunluq, sətir_sonu)
        mətn = m[b:s]
        if ascii_düzəlt and t.növ is Növ.ACAR and isinstance(t.dəyər, str):
            if mətn != t.dəyər and " ".join(mətn.split()) != t.dəyər:
                mətn = t.dəyər
                sayğac[0] += 1
        if son_ofset is None:
            hissələr.append(mətn)
        else:
            orijinal = m[son_ofset:b]
            if boşluqlar and əvvəlki is not None and "\n" not in orijinal:
                ara = _arasında(əvvəlki, t, əvvəlkindən_əvvəl, orijinal)
            else:
                ara = orijinal
            hissələr.append(ara + mətn)
        əvvəlkindən_əvvəl, əvvəlki = əvvəlki, t
        son_ofset = b + t.yer.uzunluq

    baş = sətir[:max(0, tokenlər[ilk].yer.başlanğıc - sətir_başı)]
    quyruq = m[son_ofset:sətir_sonu] if son_ofset < sətir_sonu else ""
    return baş + "".join(hissələr) + quyruq


# ═══════════════════════════════════════════════════════════════════════
#  Fayllar
# ═══════════════════════════════════════════════════════════════════════

UZANTILAR = (".alqor", ".alq")


def faylları_tap(yollar: list[str]) -> list[Path]:
    nəticə: list[Path] = []
    for y in yollar:
        p = Path(y)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.suffix in UZANTILAR and not any(
                        h.startswith(".")
                        for h in f.relative_to(p).parts):
                    nəticə.append(f)
        elif p.suffix in UZANTILAR or p.exists():
            nəticə.append(p)
    return nəticə
