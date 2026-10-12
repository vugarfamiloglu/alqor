"""
Alqor — forma faylları (`.forma`): vizual dizaynerin görünüş faylı.

Delphi-dəki `.dfm` + `.pas` cütü kimi: pəncərənin GÖRÜNÜŞÜ ayrı faylda,
KODU isə adi `.alq` faylındadır. Eyni qovluqdakı `Əsas.forma`
`komponent Əsas`-a birləşir:

    // Əsas.forma — Alqor Studio dizayneri yaradıb
    forma Əsas
        başlıq = "Tələbə qeydiyyatı"
        en = 800
        hündürlük = 600

        obyekt AdSahəsi: sahə
            etiket = "Ad"
        son
        obyekt Saxla: düymə
            mətn = "Saxla"
            klik = Saxla_klik          // hadisə → komponentin metodu
        son
    son

    // Əsas.alq — sizin kodunuz
    komponent Əsas
        əməl Saxla_klik()
            yaz("Salam, {özü.AdSahəsi.dəyər}!")
        son
    son

Qaydalar:
  • `obyekt Ad: növ` — `növ` vidjet adıdır (§ 14) və ya forma
    konteyneri `kətan` (sərbəst yerləşmə, § 12.6). Uşaq obyektlər
    konteynerin `məzmun`-u olur.
  • `xassə = dəyər` — dəyər literaldır (mətn, ədəd, məntiq, `boş`,
    siyahı, lüğət, kortej) və ya ad: hadisə xassəsində (`klik`,
    `dəyişdi` …) metod adı, başqa xassədə formadakı obyektin adı.
  • Hər obyekt komponentdə adı ilə sahə olur: `özü.AdSahəsi.mətn`.
    Xassəni dəyişmək (`özü.Etiket1.mətn = "…"`) görünüşü yeniləyir.
  • Giriş elementlərinin dəyəri (`dəyər`, `yanıq`, `işarələnmiş` …)
    istifadəçi yazdıqca avtomatik yenilənir.
  • Komponentdə `göstər()` yoxdursa, formanın özü göstərilir.
  • Ortaq xassələr (vidjetə ötürülmür): `görünür`, `sol`, `yuxarı`,
    `en`, `hündürlük`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .deyerler import AlqorXəta, Element
from .xeta import XətaToplayıcı, Yer

UZANTI = ".forma"

#  Vidjetə ötürülməyən, forma özünün işlətdiyi xassələr
ORTAQ_XASSƏLƏR = ("görünür", "sol", "yuxarı", "en", "hündürlük")
#  Kökün (pəncərənin) xassələri
KÖK_XASSƏLƏRİ = ("başlıq", "en", "hündürlük", "düzülüş", "boşluq",
                 "ölçüsüSabit", "mərkəzə")
#  Forma konteynerləri (vidjet deyil)
FORMA_KONTEYNERLƏRİ = ("kətan",)
#  İstifadəçinin daxil etdiyi dəyəri saxlayan xassələr
DƏYƏR_XASSƏLƏRİ = ("dəyər", "yanıq", "işarələnmiş", "seçili", "seçilmiş")


# ═══════════════════════════════════════════════════════════════════════
#  Model
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class İstinad:
    """Dəyər yerinə ad: metod (hadisə üçün) və ya forma obyekti."""
    ad: str
    yer: Yer | None = None

    def __eq__(self, o: object) -> bool:
        return isinstance(o, İstinad) and o.ad == self.ad

    def __hash__(self) -> int:
        return hash(("İstinad", self.ad))


@dataclass
class ObyektTəsviri:
    ad: str
    növ: str
    xassələr: dict[str, Any] = field(default_factory=dict)
    uşaqlar: list["ObyektTəsviri"] = field(default_factory=list)
    yer: Yer | None = None
    xassə_yerləri: dict[str, Yer] = field(default_factory=dict)
    növ_yeri: Yer | None = None


@dataclass
class FormaTəsviri:
    ad: str
    xassələr: dict[str, Any] = field(default_factory=dict)
    obyektlər: list[ObyektTəsviri] = field(default_factory=list)
    yer: Yer | None = None
    yol: Path | None = None
    xassə_yerləri: dict[str, Yer] = field(default_factory=dict)

    def hamısı(self) -> list[ObyektTəsviri]:
        """Bütün obyektlər (dərinə), sıra ilə."""
        n: list[ObyektTəsviri] = []

        def gəz(s: list[ObyektTəsviri]) -> None:
            for o in s:
                n.append(o)
                gəz(o.uşaqlar)
        gəz(self.obyektlər)
        return n

    def tap(self, ad: str) -> ObyektTəsviri | None:
        return next((o for o in self.hamısı() if o.ad == ad), None)


# ═══════════════════════════════════════════════════════════════════════
#  Vidjet məlumatı (dizayner və yoxlama üçün)
# ═══════════════════════════════════════════════════════════════════════

def _vidjet_parametrləri(növ: str) -> list[str] | None:
    from . import vidjet as V
    if növ not in getattr(V, "VİDJETLƏR", ()):
        return None
    import inspect
    f = getattr(V, növ, None)
    if f is None:
        return None
    return list(inspect.signature(f).parameters)[1:]


def hadisədir(növ: str, xassə: str) -> bool:
    """`düymə.klik`, `sahə.dəyişdi` … — dəyəri metod adı olan xassə."""
    from . import vidjet as V
    for m in V.KATALOQ:
        if m.ad == növ:
            return xassə in m.hadisələr
    from .pencere import HADİSƏLƏR
    return xassə in HADİSƏLƏR


def məlum_növlər() -> tuple[str, ...]:
    from . import vidjet as V
    return tuple(V.VİDJETLƏR) + FORMA_KONTEYNERLƏRİ


# ═══════════════════════════════════════════════════════════════════════
#  Oxuma
# ═══════════════════════════════════════════════════════════════════════

class _Oxuyucu:
    def __init__(self, tokenlər, mənbə, x: XətaToplayıcı):
        from .token import Növ
        self.N = Növ
        self.t = [t for t in tokenlər
                  if t.növ not in (Növ.SENED, Növ.DIREKTIV)]
        self.i = 0
        self.s = mənbə
        self.x = x

    # ── köməkçilər ────────────────────────────────────────────────────
    def bax(self, k: int = 0):
        j = min(self.i + k, len(self.t) - 1)
        return self.t[j]

    def al(self):
        t = self.bax()
        if self.i < len(self.t) - 1:
            self.i += 1
        return t

    def sətirləri_keç(self) -> None:
        while self.bax().növ is self.N.SETIR_SONU:
            self.al()

    def söz(self, t, *sözlər: str) -> bool:
        return t.növ in (self.N.AD, self.N.ACAR) and t.dəyər in sözlər

    def xəta(self, mesaj: str, t=None, qeyd: str = "", *köməklər: str):
        t = t or self.bax()
        raise _Dayan(mesaj, t.yer, qeyd, köməklər)

    def ad_tələb(self, nə: str) -> tuple[str, Yer]:
        t = self.al()
        if t.növ not in (self.N.AD, self.N.ACAR):
            self.xəta(f"{nə} gözlənilirdi", t, "burada ad olmalıdır")
        return str(t.dəyər), t.yer

    def sətir_sonu(self) -> None:
        t = self.bax()
        if t.növ in (self.N.SETIR_SONU, self.N.FAYL_SONU):
            self.sətirləri_keç()
            return
        self.xəta("sətir sonu gözlənilirdi", t,
                  f"`{t.dəyər}` artıqdır")

    # ── qrammatika ────────────────────────────────────────────────────
    def forma(self) -> FormaTəsviri:
        self.sətirləri_keç()
        t = self.al()
        if not self.söz(t, "forma"):
            self.xəta("forma faylı `forma Ad` ilə başlamalıdır", t,
                      "burada `forma` gözlənilirdi",
                      "nümunə: forma Əsas … son")
        ad, yer = self.ad_tələb("forma adı")
        f = FormaTəsviri(ad, yer=yer)
        self.sətir_sonu()
        self.gövdə(f.xassələr, f.obyektlər, f.xassə_yerləri, f"forma {ad}")
        self.sətirləri_keç()
        if self.bax().növ is not self.N.FAYL_SONU:
            self.xəta("`son`-dan sonra artıq mətn", self.bax())
        return f

    def gövdə(self, xassələr: dict, obyektlər: list, yerlər: dict,
              nə: str) -> None:
        while True:
            self.sətirləri_keç()
            t = self.bax()
            if t.növ is self.N.FAYL_SONU:
                self.xəta(f"`{nə}` bağlanmayıb — `son` gözlənilirdi", t)
            if self.söz(t, "son"):
                self.al()
                self.sətir_sonu()
                return
            if self.söz(t, "obyekt"):
                obyektlər.append(self.obyekt())
                continue
            ad, yer = self.ad_tələb("xassə adı və ya `obyekt`")
            if ad in xassələr:
                self.xəta(f"`{ad}` xassəsi təkrar verilib",
                          self.t[self.i - 1])
            if not self.bax().opdur("="):
                self.xəta("`=` gözlənilirdi", self.bax(),
                          "xassə belə yazılır: ad = dəyər")
            self.al()
            xassələr[ad] = self.dəyər()
            yerlər[ad] = yer
            self.sətir_sonu()

    def obyekt(self) -> ObyektTəsviri:
        self.al()                                   # obyekt
        ad, yer = self.ad_tələb("obyekt adı")
        if not self.bax().opdur(":"):
            self.xəta("`:` və növ gözlənilirdi", self.bax(),
                      "obyekt belə yazılır: obyekt Ad: növ",
                      "nümunə: obyekt Saxla: düymə")
        self.al()
        növ, növ_yeri = self.ad_tələb("növ (vidjet adı)")
        o = ObyektTəsviri(ad, növ, yer=yer, növ_yeri=növ_yeri)
        self.sətir_sonu()
        self.gövdə(o.xassələr, o.uşaqlar, o.xassə_yerləri, f"obyekt {ad}")
        return o

    def dəyər(self) -> Any:
        N = self.N
        t = self.al()
        if t.növ in (N.TAM, N.ONLUQ):
            return t.dəyər
        if t.opdur("-") and self.bax().növ in (N.TAM, N.ONLUQ):
            return -self.al().dəyər
        if t.növ is N.METN:
            if any(not hasattr(p, "dəyər") for p in (t.parçalar or [])):
                self.xəta("forma faylında şablon mətn (`{…}`) ola bilməz",
                          t, "dəyişən dəyəri kodda verin",
                          "mötərizəni saxlamaq üçün: \\{ \\}")
            return t.dəyər
        if t.növ is N.SIMVOL:
            return t.dəyər
        if self.söz(t, "doğru"):
            return True
        if self.söz(t, "yanlış"):
            return False
        if self.söz(t, "boş"):
            return None
        if t.opdur("["):
            n = []
            while not self.bax().opdur("]"):
                n.append(self.dəyər())
                if not self.bax().opdur("]"):
                    self.vergül()
            self.al()
            return n
        if t.opdur("("):
            n = []
            while not self.bax().opdur(")"):
                n.append(self.dəyər())
                if not self.bax().opdur(")"):
                    self.vergül()
            self.al()
            return tuple(n)
        if t.opdur("{"):
            d = {}
            while not self.bax().opdur("}"):
                k = self.dəyər()
                if not self.bax().opdur(":"):
                    self.xəta("`:` gözlənilirdi", self.bax())
                self.al()
                d[k] = self.dəyər()
                if not self.bax().opdur("}"):
                    self.vergül()
            self.al()
            return d
        if t.növ in (N.AD, N.ACAR):
            ad = str(t.dəyər)
            while self.bax().opdur(".") and \
                    self.bax(1).növ in (N.AD, N.ACAR):
                self.al()
                ad += "." + str(self.al().dəyər)
            return İstinad(ad, t.yer)
        self.xəta("dəyər gözlənilirdi", t,
                  "mətn, ədəd, doğru/yanlış, boş, siyahı, lüğət və ya ad")
        raise AssertionError

    def vergül(self) -> None:
        if not self.bax().opdur(","):
            self.xəta("`,` gözlənilirdi", self.bax())
        self.al()


class _Dayan(Exception):
    def __init__(self, mesaj, yer, qeyd, köməklər):
        super().__init__(mesaj)
        self.mesaj, self.yer, self.qeyd, self.köməklər = \
            mesaj, yer, qeyd, köməklər


def mətndən(mətn: str, ad: str = "<forma>", x: XətaToplayıcı | None = None,
            yol: Path | None = None) -> FormaTəsviri | None:
    """Forma mətnini oxuyur; xətalar `x`-ə yazılır (ALQ-F…)."""
    from .lekser import Lekser
    from .menbe import Mənbə
    x = x if x is not None else XətaToplayıcı()
    m = Mənbə.mətndən(mətn, ad, x)
    if m is None:
        return None
    m.yol = yol
    tokenlər = Lekser(m, x).leksə()
    if not x.uğurludur():
        return None
    try:
        f = _Oxuyucu(tokenlər, m, x).forma()
    except _Dayan as d:
        x.xəta("ALQ-F001", d.mesaj, d.yer, d.qeyd, *d.köməklər)
        return None
    f.yol = yol
    yoxla(f, x)
    return f if x.uğurludur() else None


def fayldan(yol: Path | str, x: XətaToplayıcı | None = None
            ) -> FormaTəsviri | None:
    yol = Path(yol)
    return mətndən(yol.read_text(encoding="utf-8"), yol.name, x, yol)


def yoxla(f: FormaTəsviri, x: XətaToplayıcı) -> None:
    """Adların təkrarı, naməlum növlər və xassələr."""
    görülən: dict[str, ObyektTəsviri] = {}
    növlər = set(məlum_növlər())
    for o in f.hamısı():
        if o.ad in görülən:
            x.xəta("ALQ-F002", f"`{o.ad}` adlı obyekt təkrarlanır", o.yer,
                   "hər obyektin adı formada tək olmalıdır")
        görülən[o.ad] = o
        if o.növ not in növlər:
            from difflib import get_close_matches
            yaxın = get_close_matches(o.növ, sorted(növlər), 1)
            x.xəta("ALQ-F003", f"`{o.növ}` adlı vidjet yoxdur",
                   o.növ_yeri or o.yer,
                   "naməlum növ",
                   *([f"bəlkə `{yaxın[0]}`?"] if yaxın else []))
            continue
        icazəli = _vidjet_parametrləri(o.növ)
        if icazəli is None:
            continue
        for xa in o.xassələr:
            if xa not in icazəli and xa not in ORTAQ_XASSƏLƏR:
                from difflib import get_close_matches
                yaxın = get_close_matches(xa, icazəli, 1)
                x.xəbərdarlıq(
                    "ALQ-F004", f"`{o.növ}` vidjetinin `{xa}` xassəsi yoxdur",
                    o.xassə_yerləri.get(xa, o.yer), "bu xassə nəzərə alınmır",
                    *([f"bəlkə `{yaxın[0]}`?"] if yaxın else []))
        if o.uşaqlar and "məzmun" not in icazəli and \
                o.növ not in FORMA_KONTEYNERLƏRİ:
            x.xəta("ALQ-F005", f"`{o.növ}` konteyner deyil — içində "
                   "obyekt ola bilməz", o.uşaqlar[0].yer)


# ═══════════════════════════════════════════════════════════════════════
#  Yazma (dizayner bu formatda saxlayır)
# ═══════════════════════════════════════════════════════════════════════

def _mətn_literalı(s: str) -> str:
    qaçış = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t",
             "\r": "\\r", "{": "\\{", "}": "\\}", "\0": "\\0"}
    return '"' + "".join(qaçış.get(c, c) for c in s) + '"'


def dəyər_yaz(d: Any) -> str:
    if isinstance(d, İstinad):
        return d.ad
    if d is True:
        return "doğru"
    if d is False:
        return "yanlış"
    if d is None:
        return "boş"
    if isinstance(d, str):
        return _mətn_literalı(d)
    if isinstance(d, (int, float)):
        return repr(d)
    if isinstance(d, list):
        return "[" + ", ".join(dəyər_yaz(e) for e in d) + "]"
    if isinstance(d, tuple):
        return "(" + ", ".join(dəyər_yaz(e) for e in d) + \
            ("," if len(d) == 1 else "") + ")"
    if isinstance(d, dict):
        return "{" + ", ".join(f"{dəyər_yaz(k)}: {dəyər_yaz(v)}"
                               for k, v in d.items()) + "}"
    raise TypeError(f"forma dəyəri ola bilməz: {type(d).__name__}")


def yaz(f: FormaTəsviri, başlıq_şərhi: bool = True) -> str:
    s: list[str] = []
    if başlıq_şərhi:
        s.append(f"// {f.ad}.forma — Alqor Studio dizayneri yaradıb; "
                 f"kod: {f.ad}.alq")
    s.append(f"forma {f.ad}")
    for k, v in f.xassələr.items():
        s.append(f"    {k} = {dəyər_yaz(v)}")

    def obyekt(o: ObyektTəsviri, g: int) -> None:
        if s[-1].strip() and g == 1:
            s.append("")
        p = "    " * g
        s.append(f"{p}obyekt {o.ad}: {o.növ}")
        for k, v in o.xassələr.items():
            s.append(f"{p}    {k} = {dəyər_yaz(v)}")
        for u in o.uşaqlar:
            obyekt(u, g + 1)
        s.append(f"{p}son")
    for o in f.obyektlər:
        obyekt(o, 1)
    s.append("son")
    return "\n".join(s) + "\n"


# ═══════════════════════════════════════════════════════════════════════
#  İcra: forma obyektləri və göstərmə
# ═══════════════════════════════════════════════════════════════════════

class FormaObyekti:
    """Formadakı obyekt — kodda `özü.Ad.xassə` kimi işlənir."""

    ALQOR_TİP_ADI = "formaObyekti"

    def __init__(self, t: ObyektTəsviri, sahib: Any):
        self.ad = t.ad
        self.növ = t.növ
        self.xassələr: dict[str, Any] = {
            k: _kopya(v) for k, v in t.xassələr.items()}
        self.uşaqlar = [FormaObyekti(u, sahib) for u in t.uşaqlar]
        self.sahib = sahib
        self._icazəli = _vidjet_parametrləri(t.növ) or []

    def __repr__(self) -> str:
        return f"<{self.növ} {self.ad}>"

    # ── `özü.Ad.xassə` protokolu (icraçı çağırır) ─────────────────────
    def alqor_üzv(self, icraçı, ad: str, yer) -> Any:
        if ad == "ad":
            return self.ad
        if ad == "növ":
            return self.növ
        if ad == "uşaqlar":
            return list(self.uşaqlar)
        if ad in self.xassələr:
            v = self.xassələr[ad]
            return v.ad if isinstance(v, İstinad) else v
        if ad == "görünür":
            return True
        if ad in self._icazəli or ad in ORTAQ_XASSƏLƏR:
            from .vidjet_arayis import parametrlər
            for p, d in parametrlər(self.növ):
                if p == ad:
                    import inspect
                    return None if d is inspect.Parameter.empty else d
            return None
        raise AlqorXəta("ArqumentXətası",
                        f"`{self.ad}` ({self.növ}) obyektində `{ad}` "
                        "xassəsi yoxdur", yer, "ALQ-T006")

    def alqor_üzv_qoy(self, icraçı, ad: str, dəyər: Any, yer) -> None:
        if ad in ("ad", "növ", "uşaqlar"):
            raise AlqorXəta("ArqumentXətası", f"`{ad}` yalnız oxunandır",
                            yer, "ALQ-T020")
        if self._icazəli and ad not in self._icazəli and \
                ad not in ORTAQ_XASSƏLƏR and \
                self.növ not in FORMA_KONTEYNERLƏRİ:
            raise AlqorXəta("ArqumentXətası",
                            f"`{self.növ}` vidjetinin `{ad}` xassəsi yoxdur",
                            yer, "ALQ-T006")
        self.xassələr[ad] = dəyər

    ALQOR_METODLARI = {
        "göstər": lambda i, o: o.xassələr.__setitem__("görünür", True),
        "gizlət": lambda i, o: o.xassələr.__setitem__("görünür", False),
        "xassələr": lambda i, o: {k: (v.ad if isinstance(v, İstinad) else v)
                                  for k, v in o.xassələr.items()},
    }


def _kopya(v: Any) -> Any:
    if isinstance(v, list):
        return [_kopya(e) for e in v]
    if isinstance(v, dict):
        return {k: _kopya(e) for k, e in v.items()}
    return v


def obyektləri_yarat(f: FormaTəsviri, nümunə: Any) -> dict[str, FormaObyekti]:
    """Komponent nümunəsi üçün obyekt ağacı; ad → obyekt."""
    kök = [FormaObyekti(o, nümunə) for o in f.obyektlər]
    return {o.ad: o for o in _hamısı(kök)}


def _ölçü(v: Any) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{v}px"
    return str(v)


def göstər(icraçı: Any, nümunə: Any) -> Element:
    """Formanı vidjet ağacına çevirir (komponentin `göstər()`-i)."""
    from . import vidjet as V
    from .deyerler import Daxili
    f: FormaTəsviri = forma_tap(nümunə.sinif)
    kök: list[FormaObyekti] = [nümunə.sahələr[o.ad] for o in f.obyektlər
                               if isinstance(nümunə.sahələr.get(o.ad),
                                             FormaObyekti)]
    obyektlər = {o.ad: o for o in _hamısı(kök)}

    def metod(ad: str, yer) -> Any:
        m = nümunə.sinif.metod_tap(ad)
        if m is None:
            raise AlqorXəta(
                "ArqumentXətası",
                f"`{nümunə.sinif.ad}` komponentində `{ad}` metodu yoxdur — "
                "formadakı hadisə onu çağırır", yer, "ALQ-F006")
        return m.bağla(nümunə)

    def idarəedici(o: FormaObyekti, hadisə: str, istinad: İstinad | None,
                   dəyər_xassəsi: str | None) -> Any:
        hədəf = metod(istinad.ad, istinad.yer) if istinad else None

        def işlə(*arq):
            if dəyər_xassəsi is not None and arq and arq[0] is not None:
                o.xassələr[dəyər_xassəsi] = arq[0]
            if hədəf is None:
                return None
            p = len(getattr(hədəf, "parametrlər", []) or [])
            return icraçı._çağır(hədəf, list(arq[:p]) if p else [], {}, None)
        return Daxili(f"{o.ad}.{hadisə}", işlə, 0, None)

    def element(o: FormaObyekti, mütləq: bool) -> Any:
        if o.xassələr.get("görünür", True) is False:
            return None
        if o.növ == "kətan":
            uşaqlar = [e for e in (element(u, True) for u in o.uşaqlar)
                       if e is not None]
            üslub = "position:relative;"
            for k, css in (("en", "width"), ("hündürlük", "height")):
                if k in o.xassələr:
                    üslub += f"{css}:{_ölçü(o.xassələr[k])};"
            e = Element("div", {"class": "a-kətan", "style": üslub}, uşaqlar)
        else:
            vf = getattr(V, o.növ)
            icazəli = o._icazəli
            hadisələr = next((m.hadisələr for m in V.KATALOQ
                              if m.ad == o.növ), [])
            dx = next((p for p in DƏYƏR_XASSƏLƏRİ if p in icazəli), None)
            adlı: dict[str, Any] = {}
            for k, v in o.xassələr.items():
                if k in ORTAQ_XASSƏLƏR and k not in icazəli:
                    continue
                if k not in icazəli or k in hadisələr:
                    continue
                if isinstance(v, İstinad):
                    v = obyektlər[v.ad] if v.ad in obyektlər else \
                        metod(v.ad, v.yer)
                adlı[k] = v
            for h in hadisələr:
                ist = o.xassələr.get(h)
                ist = ist if isinstance(ist, İstinad) else None
                sinxron = dx if h in ("dəyişdi", "yazıldı", "klik") else None
                if ist is not None or sinxron is not None:
                    adlı[h] = idarəedici(o, h, ist, sinxron)
            if o.uşaqlar and "məzmun" in icazəli:
                adlı["məzmun"] = [e for e in (element(u, False)
                                              for u in o.uşaqlar)
                                  if e is not None]
            e = vf(icraçı, **adlı)
        üslub = ""
        if mütləq:
            üslub = "position:absolute;"
            for k, css in (("sol", "left"), ("yuxarı", "top"),
                           ("en", "width"), ("hündürlük", "height")):
                if k in o.xassələr:
                    üslub += f"{css}:{_ölçü(o.xassələr[k])};"
        elif o.növ != "kətan":
            for k, css in (("en", "width"), ("hündürlük", "height")):
                if k in o.xassələr and k not in o._icazəli:
                    üslub += f"{css}:{_ölçü(o.xassələr[k])};"
        if üslub:
            return Element("div", {"class": "a-yer", "data-ad": o.ad,
                                   "style": üslub}, [e])
        return e

    sərbəst = f.xassələr.get("düzülüş") == "sərbəst"
    uşaqlar = [e for e in (element(o, sərbəst) for o in kök) if e is not None]
    if sərbəst:
        üslub = "position:relative;min-height:100%;"
        return Element("div", {"class": "a-forma a-kətan", "style": üslub},
                       uşaqlar)
    boşluq = f.xassələr.get("boşluq", 12)
    return Element("div", {"class": "a-forma",
                           "style": f"display:flex;flex-direction:column;"
                                    f"gap:{_ölçü(boşluq)};padding:16px"},
                   uşaqlar)


def _hamısı(kök: list[FormaObyekti]) -> list[FormaObyekti]:
    n: list[FormaObyekti] = []

    def gəz(s):
        for o in s:
            n.append(o)
            gəz(o.uşaqlar)
    gəz(kök)
    return n


# ═══════════════════════════════════════════════════════════════════════
#  Komponentə birləşmə (icraçı çağırır)
# ═══════════════════════════════════════════════════════════════════════

def komponent_üçün(komponent_adı: str, mənbə_yolu: Path | None
                   ) -> Path | None:
    """`komponent Əsas` elan olunan faylın yanındakı `Əsas.forma`."""
    if mənbə_yolu is None:
        return None
    y = Path(mənbə_yolu).parent / f"{komponent_adı}{UZANTI}"
    return y if y.is_file() else None


def birləşdir(icraçı: Any, sinif: Any, yol: Path, yer: Any) -> None:
    """Formanı komponentə bağlayır: `sinif.forma`, lazımsa `göstər()`."""
    from . import aac as A
    from .deyerler import Daxili, Funksiya, Mühit
    x = XətaToplayıcı()
    f = fayldan(yol, x)
    if f is None:
        raise AlqorXəta("SintaksisXətası",
                        f"`{yol.name}` forma faylında xəta var:\n\n"
                        + x.hesabat(False), yer, "ALQ-F001")
    if f.ad != sinif.ad:
        raise AlqorXəta("ArqumentXətası",
                        f"`{yol.name}` faylında `forma {f.ad}` var, amma "
                        f"komponentin adı `{sinif.ad}`-dir", yer, "ALQ-F007")
    # Hadisə metodları komponentdə olmalıdır — xətanı açılışda göstər
    for o in f.hamısı():
        for k, v in o.xassələr.items():
            if isinstance(v, İstinad) and f.tap(v.ad) is None and \
                    sinif.metod_tap(v.ad) is None:
                raise AlqorXəta(
                    "ArqumentXətası",
                    f"`{yol.name}`: `{o.ad}.{k} = {v.ad}` — `{sinif.ad}` "
                    f"komponentində `{v.ad}` metodu yoxdur", yer, "ALQ-F006")
    sinif.forma = f
    if sinif.metod_tap("göstər") is None:
        mühit = Mühit(sinif.mühit)
        mühit.elan("_formaGöstər",
                   Daxili("_formaGöstər",
                          lambda n: göstər(icraçı, n), 1, 1))
        yer_ = yer
        çağırış = A.Çağırış(yer_, A.Ad(yer_, "_formaGöstər"),
                            [A.Arqument(A.Özü(yer_))])
        sinif.metodlar["göstər"] = Funksiya("göstər", [], çağırış, mühit,
                                            sinif=sinif)


def forma_tap(sinif: Any) -> FormaTəsviri | None:
    while sinif is not None:
        f = getattr(sinif, "forma", None)
        if f is not None:
            return f
        sinif = sinif.baza
    return None


def nümunəyə_qoş(nümunə: Any) -> None:
    f = forma_tap(nümunə.sinif)
    if f is None:
        return
    for ad, o in obyektləri_yarat(f, nümunə).items():
        nümunə.sahələr[ad] = o
