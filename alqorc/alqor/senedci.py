"""
Alqor — `alqor sənəd` (`alqordoc`): koddan API sənədi.

Spesifikasiya § 13.6.

`///` sənəd şərhləri elanın üstündə, `//!` faylın başında yazılır:

    //! Həndəsə funksiyaları.

    /// Dairənin sahəsi.
    ///
    /// ```alqor
    /// yaz(sahə(2))     // 12.566…
    /// ```
    ixrac et funksiya sahə(r: onluq) -> onluq
        …
    son

Faylda `ixrac et` varsa yalnız ixrac olunanlar, yoxdursa `gizli`
olmayan bütün yuxarı səviyyəli elanlar sənədləşdirilir. İmza mənbədən
olduğu kimi götürülür. Nəticə: Markdown və ya tək fayllı HTML.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import aac as A
from .lekser import Lekser
from .menbe import Mənbə
from .parser import Parser
from .token import Növ
from .xeta import XətaToplayıcı


@dataclass
class Element:
    növ: str                       # funksiya, sinif, komponent, …
    ad: str
    imza: str
    sənəd: str = ""
    üzvlər: list["Element"] = field(default_factory=list)


@dataclass
class FaylSənədi:
    yol: Path
    ad: str
    sənəd: str = ""
    elementlər: list[Element] = field(default_factory=list)


def _növ(c) -> str | None:
    ad = type(c).__name__
    return {
        "FunksiyaElanı": "funksiya", "SinifElanı": "sinif",
        "ModulElanı": "modul", "InterfeysElanı": "interfeys",
        "SadalamaElanı": "sadalama", "DəyişənElanı": "sabit",
        "MetodElanı": "metod", "XassəElanı": "xassə",
        "QurucuElanı": "qurucu", "TipAliası": "tip",
    }.get(ad)


def _imza(c, mətn: str, tokenlər: list) -> str:
    """Elanın başlığı: başlanğıc tokenindən sətir sonuna qədər."""
    b = c.yer.başlanğıc
    i = 0
    while i < len(tokenlər) and tokenlər[i].yer.başlanğıc < b:
        i += 1
    dərinlik = 0
    son = b
    while i < len(tokenlər):
        t = tokenlər[i]
        if t.növ in (Növ.SETIR_SONU, Növ.FAYL_SONU) and dərinlik == 0:
            break
        if t.növ is Növ.OP and t.dəyər in ("(", "[", "{"):
            dərinlik += 1
        elif t.növ is Növ.OP and t.dəyər in (")", "]", "}"):
            dərinlik -= 1
        # Bir sətirlik gövdə (`funksiya f() qaytar 1 son`) imzaya düşməsin
        if t.növ is Növ.ACAR and t.dəyər in ("qaytar", "son") \
                and dərinlik == 0 and t.yer.başlanğıc > b:
            break
        son = t.yer.başlanğıc + t.yer.uzunluq
        i += 1
    başlıq = " ".join(mətn[b:son].split())
    # Elanı başlatan `ixrac et` / görünüş sözləri c.yer-dən əvvəldədir
    return başlıq


def fayl_sənədi(yol: Path) -> FaylSənədi:
    x = XətaToplayıcı()
    m = Mənbə.fayldan(yol, x)
    if m is None:
        raise ValueError(f"{yol} oxunmadı")
    tokenlər = Lekser(m, x, ascii_xəbərdarlığı=False).leksə()
    p = Parser(tokenlər, m, x)
    ağac = p.ayır()
    if not x.uğurludur():
        ilk = x.xətalar[0]
        raise ValueError(f"{yol}: {ilk.kod} {ilk.mesaj} ({ilk.yer})")

    üst = [c for c in ağac.gövdə if _növ(c)]
    ixrac_var = any(getattr(c, "ixrac", False) for c in üst)

    def görünür(c) -> bool:
        if ixrac_var:
            return bool(getattr(c, "ixrac", False))
        return getattr(c, "görünüş", None) != "gizli" \
            and not getattr(c, "ad", "x").startswith("_")

    def element(c) -> Element:
        ad = getattr(c, "ad", None) or ""
        if not ad and isinstance(c, A.DəyişənElanı) and c.bağlamalar:
            ad = getattr(c.bağlamalar[0], "ad", "") or ""
        e = Element(_növ(c) or "", ad, _imza(c, m.mətn, tokenlər),
                    (getattr(c, "sənəd", None) or "").strip())
        if "komponent" in e.imza.split()[:3]:
            e.növ = "komponent"
        for ü in (getattr(c, "üzvlər", None) or []):
            if _növ(ü) and getattr(ü, "görünüş", None) != "gizli" \
                    and not (getattr(ü, "ad", "") or "").startswith("_"):
                e.üzvlər.append(element(ü))
        return e

    elementlər = [element(c) for c in üst if görünür(c)]
    return FaylSənədi(yol, yol.stem, (p.modul_sənədi or "").strip(),
                      elementlər)


# ═══════════════════════════════════════════════════════════════════════
#  Markdown
# ═══════════════════════════════════════════════════════════════════════

def markdown(fayllar: list[FaylSənədi], başlıq: str) -> str:
    s = [f"# {başlıq}", ""]
    for f in fayllar:
        if len(fayllar) > 1:
            s += [f"## `{f.ad}`", ""]
        if f.sənəd:
            s += [f.sənəd, ""]
        for e in f.elementlər:
            s += _md_element(e, 3 if len(fayllar) > 1 else 2)
    return "\n".join(s).rstrip() + "\n"


def _md_element(e: Element, səviyyə: int) -> list[str]:
    s = [f"{'#' * səviyyə} {e.növ} `{e.ad}`", "",
         "```alqor", e.imza, "```", ""]
    if e.sənəd:
        s += [e.sənəd, ""]
    for ü in e.üzvlər:
        s += _md_element(ü, min(6, səviyyə + 1))
    return s


# ═══════════════════════════════════════════════════════════════════════
#  HTML
# ═══════════════════════════════════════════════════════════════════════

_ÜSLUB = """
*{box-sizing:border-box}
:root{--fon:#fff;--mətn:#1b1b1f;--sönük:#6b6b73;--kənar:#e4e4e7;
 --kod:#f4f4f5;--vurgu:#0b6bcb}
@media (prefers-color-scheme:dark){:root{--fon:#18181b;--mətn:#f4f4f5;
 --sönük:#a1a1aa;--kənar:#3f3f46;--kod:#27272a;--vurgu:#4c9ef0}}
body{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;
 background:var(--fon);color:var(--mətn);display:flex}
nav{width:260px;flex:none;padding:24px 16px;border-right:1px solid
 var(--kənar);height:100vh;position:sticky;top:0;overflow:auto;
 font-size:14px}
nav a{display:block;color:var(--mətn);text-decoration:none;padding:2px 8px;
 border-radius:4px}
nav a:hover{background:var(--kod)}
nav .fayl{font-weight:600;margin-top:12px}
main{flex:1;max-width:860px;padding:32px 40px;min-width:0}
h1{margin-top:0}
h2,h3,h4{scroll-margin-top:16px}
.növ{color:var(--sönük);font-weight:400;font-size:.8em;margin-right:6px}
pre{background:var(--kod);padding:12px 14px;border-radius:6px;
 overflow-x:auto;font-size:14px}
code{font-family:ui-monospace,"Cascadia Code",Consolas,monospace}
p code,li code{background:var(--kod);padding:1px 5px;border-radius:4px}
.element{border-top:1px solid var(--kənar);padding-top:8px;margin-top:24px}
.üzvlər{margin-left:20px}
@media (max-width:760px){body{display:block}nav{display:none}
 main{padding:20px 16px}}
"""


def _sətirdaxili(m: str) -> str:
    m = html.escape(m)
    m = re.sub(r"`([^`]+)`", r"<code>\1</code>", m)
    m = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", m)
    return m


def md_html(mətn: str) -> str:
    """Sənəd şərhlərində işlənən Markdown alt çoxluğu."""
    s: list[str] = []
    sətirlər = mətn.split("\n")
    i = 0
    abzas: list[str] = []
    siyahı = False

    def abzası_bağla():
        nonlocal abzas
        if abzas:
            s.append(f"<p>{_sətirdaxili(' '.join(abzas))}</p>")
            abzas = []

    def siyahını_bağla():
        nonlocal siyahı
        if siyahı:
            s.append("</ul>")
            siyahı = False

    while i < len(sətirlər):
        sətir = sətirlər[i]
        if sətir.startswith("```"):
            abzası_bağla()
            siyahını_bağla()
            kod: list[str] = []
            i += 1
            while i < len(sətirlər) and not sətirlər[i].startswith("```"):
                kod.append(sətirlər[i])
                i += 1
            s.append(f"<pre><code>{html.escape(chr(10).join(kod))}"
                     "</code></pre>")
        elif sətir.startswith("#"):
            abzası_bağla()
            siyahını_bağla()
            s.append(f"<h5>{_sətirdaxili(sətir.lstrip('#').strip())}</h5>")
        elif sətir.lstrip().startswith(("- ", "* ")):
            abzası_bağla()
            if not siyahı:
                s.append("<ul>")
                siyahı = True
            s.append(f"<li>{_sətirdaxili(sətir.lstrip()[2:])}</li>")
        elif not sətir.strip():
            abzası_bağla()
            siyahını_bağla()
        else:
            siyahını_bağla()
            abzas.append(sətir.strip())
        i += 1
    abzası_bağla()
    siyahını_bağla()
    return "\n".join(s)


def _lövbər(*hissələr: str) -> str:
    return "-".join(re.sub(r"\W+", "-", h).strip("-") for h in hissələr)


def html_sənəd(fayllar: list[FaylSənədi], başlıq: str) -> str:
    nav: list[str] = []
    gövdə: list[str] = [f"<h1>{html.escape(başlıq)}</h1>"]
    for f in fayllar:
        nav.append(f'<a class="fayl" href="#{_lövbər(f.ad)}">'
                   f"{html.escape(f.ad)}</a>")
        gövdə.append(f'<h2 id="{_lövbər(f.ad)}"><code>'
                     f"{html.escape(f.ad)}</code></h2>")
        if f.sənəd:
            gövdə.append(md_html(f.sənəd))
        for e in f.elementlər:
            nav.append(f'<a href="#{_lövbər(f.ad, e.ad)}">'
                       f"{html.escape(e.ad)}</a>")
            gövdə.append(_html_element(e, f.ad, 3))
    return (
        "<!DOCTYPE html>\n<html lang=\"az\"><head><meta charset=\"UTF-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(başlıq)}</title><style>{_ÜSLUB}</style>"
        f"</head><body><nav>{''.join(nav)}</nav><main>"
        + "\n".join(gövdə)
        + "<p style='color:var(--sönük);margin-top:48px'>"
          "alqor sənəd ilə yaradılıb</p></main></body></html>\n")


def _html_element(e: Element, fayl: str, səviyyə: int) -> str:
    h = min(6, səviyyə)
    s = [f'<section class="element"><h{h} id="{_lövbər(fayl, e.ad)}">'
         f'<span class="növ">{html.escape(e.növ)}</span>'
         f"<code>{html.escape(e.ad)}</code></h{h}>",
         f"<pre><code>{html.escape(e.imza)}</code></pre>"]
    if e.sənəd:
        s.append(md_html(e.sənəd))
    if e.üzvlər:
        s.append('<div class="üzvlər">')
        for ü in e.üzvlər:
            s.append(_html_element(ü, f"{fayl}-{e.ad}", səviyyə + 1))
        s.append("</div>")
    s.append("</section>")
    return "\n".join(s)
