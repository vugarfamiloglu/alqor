"""
`html` — HTML oxuma, axtarış, təmizləmə (§ 10.17).

    gətir html

    dəyişən s = html.oxu(cavab.mətn())
    yaz(s.tap("title").mətn())
    hər a üçün s.tapHamısı("a[href]") içində
        yaz(a.atribut("href"))
    son

    html.qaç("<b>")                    // "&lt;b&gt;"
    html.mətnə("<p>Salam <b>dünya</b></p>")   // "Salam dünya"
    html.təmizlə(istifadəçiMətni)      // təhlükəsiz teqlər qalır,
                                       // <script>, onclick, javascript: atılır

HTML yaratmaq üçün interfeys sintaksisi (`<div>…</div>`, § 11) və ya
`veb.şablon` işlədilir.
"""

from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı
from ._duyun import Düyün, metod_tipləri

BOŞ = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
       "meta", "source", "track", "wbr"}

# Açıq qalan teq — yeni hansı teq gəldikdə avtomatik bağlanır
_ÖZÜ_BAĞLANAN = {
    "p": {"p", "div", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5",
          "h6", "pre", "section", "article", "header", "footer", "form",
          "blockquote", "nav", "aside", "hr"},
    "li": {"li"}, "dt": {"dt", "dd"}, "dd": {"dt", "dd"},
    "tr": {"tr", "tbody", "tfoot"}, "td": {"td", "th", "tr"},
    "th": {"td", "th", "tr"}, "option": {"option", "optgroup"},
    "thead": {"tbody", "tfoot"}, "tbody": {"tbody", "tfoot"},
}

_BLOK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
         "section", "article", "header", "footer", "ul", "ol", "table",
         "pre", "blockquote", "hr", "nav", "form", "dt", "dd"}


class _Ayırıcı(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.kök = Düyün("#sənəd")
        self.yığın: list[Düyün] = [self.kök]

    def _cari(self) -> Düyün:
        return self.yığın[-1]

    def handle_starttag(self, teq, atributlar):
        # Avtomatik bağlanma: <li>a<li>b, <p>a<div>
        while len(self.yığın) > 1:
            cari = self._cari().ad_
            if cari in _ÖZÜ_BAĞLANAN and teq in _ÖZÜ_BAĞLANAN[cari]:
                self.yığın.pop()
            else:
                break
        d = Düyün(teq, {a: (v if v is not None else "")
                        for a, v in atributlar}, boşdur=teq in BOŞ)
        self._cari().əlavə(d)
        if teq not in BOŞ:
            self.yığın.append(d)

    def handle_startendtag(self, teq, atributlar):
        d = Düyün(teq, {a: (v if v is not None else "")
                        for a, v in atributlar}, boşdur=True)
        self._cari().əlavə(d)

    def handle_endtag(self, teq):
        for i in range(len(self.yığın) - 1, 0, -1):
            if self.yığın[i].ad_ == teq:
                del self.yığın[i:]
                return
        # Açılmamış teqin bağlanması — nəzərə alınmır (brauzer kimi)

    def handle_data(self, mətn):
        self._cari().əlavə(mətn)


def oxu(mətn: str) -> Düyün:
    if not isinstance(mətn, str):
        raise AlqorXəta("TipXətası",
                        f"`html.oxu` mətn gözləyir, `{tip_adı(mətn)}` gəlib",
                        None, "ALQ-T001")
    a = _Ayırıcı()
    a.feed(mətn)
    a.close()
    return a.kök


def mətnə(m: Any) -> str:
    """HTML → oxunaqlı düz mətn (blok elementlər yeni sətir)."""
    kök = m if isinstance(m, Düyün) else oxu(m)
    n: list[str] = []

    def gəz(d: Düyün):
        for u in d.uşaq:
            if isinstance(u, str):
                n.append(re.sub(r"\s+", " ", u))
            elif u.ad_ in ("script", "style", "head", "template"):
                continue
            else:
                if u.ad_ in _BLOK:
                    n.append("\n")
                gəz(u)
                if u.ad_ in _BLOK:
                    n.append("\n")
    gəz(kök)
    sətirlər = [s.strip() for s in "".join(n).split("\n")]
    nəticə: list[str] = []
    for s in sətirlər:
        if s or (nəticə and nəticə[-1]):
            nəticə.append(s)
    return "\n".join(nəticə).strip()


# ── Təmizləmə (XSS) ───────────────────────────────────────────────────

İCAZƏLİ_TEQLƏR = ["a", "b", "strong", "i", "em", "u", "s", "p", "br",
                  "ul", "ol", "li", "blockquote", "code", "pre", "h1",
                  "h2", "h3", "h4", "h5", "h6", "hr", "span", "div", "img",
                  "table", "thead", "tbody", "tr", "th", "td", "sub", "sup"]
İCAZƏLİ_ATRİBUTLAR = {"a": ["href", "title"], "img": ["src", "alt",
                                                      "title", "width",
                                                      "height"],
                      "*": ["class"]}
_TƏHLÜKƏLİ_SXEM = re.compile(r"^\s*(javascript|vbscript|data)\s*:", re.I)
_ATILAN_MƏZMUN = {"script", "style", "iframe", "object", "embed",
                  "template", "noscript", "textarea", "select"}


def təmizlə(m: str, teqlər: list | None = None,
            atributlar: dict | None = None) -> str:
    icazəli = set(teqlər if teqlər is not None else İCAZƏLİ_TEQLƏR)
    atr_icazə = atributlar if atributlar is not None else İCAZƏLİ_ATRİBUTLAR
    kök = oxu(m)

    def url_təhlükəsizdir(v: str) -> bool:
        # `jav&#x09;ascript:` kimi gizlədilmiş formalar — boşluqlar atılır
        təmiz = re.sub(r"[\x00-\x20]", "", _html.unescape(v))
        return not _TƏHLÜKƏLİ_SXEM.match(təmiz)

    def yaz(d: Düyün) -> str:
        n: list[str] = []
        for u in d.uşaq:
            if isinstance(u, str):
                n.append(_html.escape(u, quote=False))
                continue
            if u.ad_ in _ATILAN_MƏZMUN:
                continue
            iç = yaz(u)
            if u.ad_ not in icazəli:
                n.append(iç)                 # teq atılır, mətn qalır
                continue
            icazə = set(atr_icazə.get(u.ad_, [])) | set(atr_icazə.get("*", []))
            atr = []
            for a, v in u.atr.items():
                if a not in icazə or a.startswith("on"):
                    continue
                if a in ("href", "src") and not url_təhlükəsizdir(v):
                    continue
                atr.append(f' {a}="{_html.escape(v, quote=True)}"')
            if u.ad_ == "a" and any(a.startswith(" href") for a in atr):
                atr.append(' rel="noopener noreferrer nofollow"')
            if u.ad_ in BOŞ:
                n.append(f"<{u.ad_}{''.join(atr)}>")
            else:
                n.append(f"<{u.ad_}{''.join(atr)}>{iç}</{u.ad_}>")
        return "".join(n)

    return yaz(kök)


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "oxu": D("oxu", oxu, 1, 1),
        "qaç": D("qaç", lambda m: _html.escape(str(m)), 1, 1),
        "aç": D("aç", lambda m: _html.unescape(str(m)), 1, 1),
        "mətnə": D("mətnə", mətnə, 1, 1),
        "təmizlə": D("təmizlə", təmizlə, 1, 3),
        "icazəliTeqlər": list(İCAZƏLİ_TEQLƏR),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e = T.MƏTN, T.İSTƏNİLƏN
    return {
        "oxu": F(m, qaytarır=T.Sadə("düyün")),
        "qaç": F(e, qaytarır=m), "aç": F(m, qaytarır=m),
        "mətnə": F(e, qaytarır=m),
        "təmizlə": F(m, T.Siyahı(m), e, qaytarır=m, standart=2),
        "icazəliTeqlər": T.Siyahı(m),
    }


def obyekt_tipləri() -> dict:
    return metod_tipləri()
