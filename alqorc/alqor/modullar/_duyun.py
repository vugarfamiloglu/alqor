"""
XML və HTML üçün ümumi ağac düyünü + sadə CSS seçicisi.

    d.ad()                    "a"
    d.atribut("href")         mətn? (yoxdursa boş)
    d.atributlar()            lüğət
    d.mətn()                  bütün iç mətn (uşaqlar daxil)
    d.uşaqlar()               element uşaqları
    d.tap("div.kart > a")     ilk uyğun gələn (yoxdursa boş)
    d.tapHamısı("li")         hamısı
    d.xml() / d.html()        mətnə çevirmə

Seçici: `teq`, `.sinif`, `#id`, `[atr]`, `[atr=dəyər]`, `*`, nəsil
(boşluq), birbaşa uşaq (`>`), bir neçə seçici (`,`).
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

from ..deyerler import AlqorXəta


class Düyün:
    ALQOR_TİP_ADI = "düyün"
    __slots__ = ("ad_", "atr", "uşaq", "valideyn", "boşdur")

    def __init__(self, ad: str, atr: dict | None = None,
                 uşaq: list | None = None, boşdur: bool = False):
        self.ad_ = ad
        self.atr: dict[str, str] = dict(atr or {})
        self.uşaq: list[Düyün | str] = list(uşaq or [])
        self.valideyn: Düyün | None = None
        self.boşdur = boşdur                 # HTML boş elementi (<br>)
        for u in self.uşaq:
            if isinstance(u, Düyün):
                u.valideyn = self

    def __repr__(self) -> str:
        return f"<{self.ad_}>"

    def əlavə(self, u: "Düyün | str") -> None:
        if isinstance(u, Düyün):
            u.valideyn = self
        self.uşaq.append(u)

    # ── Sorğular ──────────────────────────────────────────────────────

    def elementlər(self) -> list["Düyün"]:
        return [u for u in self.uşaq if isinstance(u, Düyün)]

    def mətn(self) -> str:
        n: list[str] = []

        def gəz(d: Düyün):
            for u in d.uşaq:
                if isinstance(u, str):
                    n.append(u)
                elif u.ad_ not in ("script", "style"):
                    gəz(u)
        gəz(self)
        return "".join(n)

    def nəsillər(self):
        for u in self.uşaq:
            if isinstance(u, Düyün):
                yield u
                yield from u.nəsillər()

    def tap_hamısı(self, seçici: str) -> list["Düyün"]:
        qruplar = _seçicini_ayır(seçici)
        n = []
        for d in self.nəsillər():
            if any(_uyğundur(d, q) for q in qruplar):
                n.append(d)
        return n

    def tap(self, seçici: str) -> "Düyün | None":
        qruplar = _seçicini_ayır(seçici)
        for d in self.nəsillər():
            if any(_uyğundur(d, q) for q in qruplar):
                return d
        return None

    # ── Yazma ─────────────────────────────────────────────────────────

    def xml(self, gözəl: bool = False, _ind: int = 0) -> str:
        atr = "".join(f' {a}="{_atr_qaç(v)}"' for a, v in self.atr.items())
        if not self.uşaq:
            return f"<{self.ad_}{atr}/>"
        yalnız_element = all(isinstance(u, Düyün) for u in self.uşaq)
        if gözəl and yalnız_element:
            ön = "  " * (_ind + 1)
            iç = "".join(f"\n{ön}{u.xml(True, _ind + 1)}" for u in self.uşaq)
            return f"<{self.ad_}{atr}>{iç}\n{'  ' * _ind}</{self.ad_}>"
        iç = "".join(_mətn_qaç(u) if isinstance(u, str)
                     else u.xml(gözəl, _ind + 1) for u in self.uşaq)
        return f"<{self.ad_}{atr}>{iç}</{self.ad_}>"

    def html(self) -> str:
        if self.ad_ == "#sənəd":
            return "".join(_mətn_qaç(u) if isinstance(u, str) else u.html()
                           for u in self.uşaq)
        atr = "".join(f' {a}="{_atr_qaç(v)}"' if v != "" else f" {a}"
                      for a, v in self.atr.items())
        if self.boşdur:
            return f"<{self.ad_}{atr}>"
        xam = self.ad_ in ("script", "style")
        iç = "".join((u if xam else _mətn_qaç(u)) if isinstance(u, str)
                     else u.html() for u in self.uşaq)
        return f"<{self.ad_}{atr}>{iç}</{self.ad_}>"

    def lüğət(self) -> Any:
        """XML-i lüğətə: atributlar `@ad`, mətn `#mətn`, təkrarlanan
        uşaqlar siyahıya yığılır."""
        n: dict[str, Any] = {f"@{a}": v for a, v in self.atr.items()}
        for u in self.elementlər():
            d = u.lüğət()
            if u.ad_ in n:
                if not isinstance(n[u.ad_], list):
                    n[u.ad_] = [n[u.ad_]]
                n[u.ad_].append(d)
            else:
                n[u.ad_] = d
        mətn = "".join(u for u in self.uşaq if isinstance(u, str)).strip()
        if not n:
            return mətn
        if mətn:
            n["#mətn"] = mətn
        return n

    # ── Alqor metodları ───────────────────────────────────────────────

    ALQOR_METODLARI: dict = {}


def _atr_qaç(v: str) -> str:
    return (str(v).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def _mətn_qaç(v: str) -> str:
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;")


# ── CSS seçicisi ──────────────────────────────────────────────────────

_SADƏ = re.compile(
    r"""(?P<teq>[\w:*-]+)?
        (?P<qalan>(?:\#[\w-]+|\.[\w-]+|\[\s*[\w:-]+\s*(?:[~^$*|]?=\s*
            (?:"[^"]*"|'[^']*'|[^\]\s]+)\s*)?\])*)""", re.X | re.U)
_HİSSƏ = re.compile(
    r"""\#(?P<id>[\w-]+)|\.(?P<sinif>[\w-]+)|\[\s*(?P<atr>[\w:-]+)\s*
        (?:(?P<op>[~^$*|]?=)\s*(?P<d>"[^"]*"|'[^']*'|[^\]\s]+)\s*)?\]""",
    re.X | re.U)


def _seçicini_ayır(seçici: str) -> list[list[tuple[str, dict]]]:
    """`"div.a > p, span"` → [[(" ", div.a), (">", p)], [(" ", span)]]"""
    if not isinstance(seçici, str) or not seçici.strip():
        raise AlqorXəta("DəyərXətası", "seçici boş ola bilməz", None,
                        "ALQ-T001")
    qruplar = []
    for qrup in seçici.split(","):
        addımlar: list[tuple[str, dict]] = []
        s = qrup.strip()
        əlaqə = " "
        while s:
            if s[0] == ">":
                əlaqə = ">"
                s = s[1:].lstrip()
                continue
            m = _SADƏ.match(s)
            if not m or m.end() == 0:
                raise AlqorXəta("DəyərXətası",
                                f"seçici başa düşülmədi: {seçici!r}",
                                None, "ALQ-T001")
            şərt = {"teq": m.group("teq"), "id": None, "siniflər": [],
                    "atr": []}
            for h in _HİSSƏ.finditer(m.group("qalan")):
                if h.group("id"):
                    şərt["id"] = h.group("id")
                elif h.group("sinif"):
                    şərt["siniflər"].append(h.group("sinif"))
                else:
                    d = h.group("d")
                    if d and d[0] in "\"'":
                        d = d[1:-1]
                    şərt["atr"].append((h.group("atr"), h.group("op"), d))
            addımlar.append((əlaqə, şərt))
            əlaqə = " "
            s = s[m.end():].lstrip()
        qruplar.append(addımlar)
    return qruplar


def _tək_uyğun(d: Düyün, ş: dict) -> bool:
    if ş["teq"] and ş["teq"] != "*" and d.ad_.lower() != ş["teq"].lower():
        return False
    if ş["id"] and d.atr.get("id") != ş["id"]:
        return False
    if ş["siniflər"]:
        siniflər = d.atr.get("class", "").split()
        if not all(s in siniflər for s in ş["siniflər"]):
            return False
    for ad, op, dəyər in ş["atr"]:
        if ad not in d.atr:
            return False
        v = d.atr[ad]
        if op == "=" and v != dəyər:
            return False
        if op == "~=" and dəyər not in v.split():
            return False
        if op == "^=" and not v.startswith(dəyər):
            return False
        if op == "$=" and not v.endswith(dəyər):
            return False
        if op == "*=" and dəyər not in v:
            return False
        if op == "|=" and not (v == dəyər or v.startswith(dəyər + "-")):
            return False
    return True


def _uyğundur(d: Düyün, addımlar: list[tuple[str, dict]]) -> bool:
    """Sağdan sola: son addım `d`-yə, əvvəlkilər əcdadlara."""
    def yoxla(d: Düyün | None, i: int) -> bool:
        if d is None:
            return False
        əlaqə, ş = addımlar[i]
        if not _tək_uyğun(d, ş):
            return False
        if i == 0:
            return True
        if əlaqə == ">":
            return yoxla(d.valideyn, i - 1)
        v = d.valideyn
        while v is not None:
            if yoxla(v, i - 1):
                return True
            v = v.valideyn
        return False
    return yoxla(d, len(addımlar) - 1)


# ── Alqor metodları ───────────────────────────────────────────────────

Düyün.ALQOR_METODLARI = {
    "ad": lambda i, d: d.ad_,
    "atribut": lambda i, d, a, s=None: d.atr.get(a, s),
    "atributlar": lambda i, d: dict(d.atr),
    "atributQoy": lambda i, d, a, v: (d.atr.__setitem__(a, str(v)), d)[1],
    "mətn": lambda i, d: d.mətn(),
    "uşaqlar": lambda i, d: d.elementlər(),
    "valideyn": lambda i, d: d.valideyn,
    "tap": lambda i, d, s: d.tap(s),
    "tapHamısı": lambda i, d, s: d.tap_hamısı(s),
    "əlavəEt": lambda i, d, u: (d.əlavə(u), d)[1],
    "xml": lambda i, d, gözəl=False: d.xml(gözəl),
    "html": lambda i, d: d.html(),
    "lüğət": lambda i, d: d.lüğət(),
}


def metod_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ
    D = T.Sadə("düyün")
    return {"düyün": {
        "ad": F(qaytarır=m),
        "atribut": F(m, e, qaytarır=T.ixtiyari(m), standart=1),
        "atributlar": F(qaytarır=T.Lüğət(m, m)),
        "atributQoy": F(m, e, qaytarır=D),
        "mətn": F(qaytarır=m),
        "uşaqlar": F(qaytarır=T.Siyahı(D)),
        "valideyn": F(qaytarır=T.ixtiyari(D)),
        "tap": F(m, qaytarır=T.ixtiyari(D)),
        "tapHamısı": F(m, qaytarır=T.Siyahı(D)),
        "əlavəEt": F(e, qaytarır=D),
        "xml": F(b, qaytarır=m, standart=1),
        "html": F(qaytarır=m),
        "lüğət": F(qaytarır=e),
    }}


def mətn_açılışı(m: str) -> str:
    return _html.unescape(m)
