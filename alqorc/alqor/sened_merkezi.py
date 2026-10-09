"""
Alqor sənəd mərkəzi — internetsiz oxunan HTML sənədlər.

    alqor sənədlər                 sənədləri brauzerdə açır
    alqor sənədlər --qur [çıxış]   statik saytı qurur (standart: qurma/sened)

Mənbələr: `beledci/*.md` (dərsliklər), `spesifikasiya/*.md` (dilin rəsmi
tərifi), `numuneler/` (nümunə proqramlar) və burada yazılan səhifələr
(ilk addımlar, əmrlər arayışı). Nəticə tək qovluqdur — quraşdırıcıya
daxil edilir, Alqor Studio-nun «Kömək» menyusu da onu açır. Heç bir
xarici fayl (şrift, skript, CDN) yüklənmir.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import VERSIYA
from .acar_sozler import ACAR_SOZLER, TIP_ADLARI
from .elifba import kiçiyə, latınla

# ═══════════════════════════════════════════════════════════════════════
#  Sintaksis rəngləməsi
# ═══════════════════════════════════════════════════════════════════════

_DAXİLİLƏR = frozenset({
    "yaz", "oxu", "oxuTam", "oxuOnluq", "oxuMəntiq", "yazSətirsiz",
    "yazXəta", "uzunluq", "tip", "tamƏt", "onluqƏt", "mətnƏt", "cəm",
    "minimum", "maksimum", "sırala", "diapazon", "siyahı", "lüğət", "dəst",
    "kortej", "klonla", "çap", "panika", "dayan", "boşdur", "zip", "tərs",
    "nömrələ",
})

_ALQOR_TOKEN = re.compile(r'''
    (?P<c>//[^\n]*|/\*[\s\S]*?\*/)
  | (?P<s>[xb]?"""[\s\S]*?"""|[xb]?"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?|`[^`\n]*`?)
  | (?P<n>\b(?:0[xXbBoO][0-9a-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?)\b)
  | (?P<a>@[\w]+)
  | (?P<w>[^\W\d][\w]*)
  | (?P<j></?[A-Za-zƏÜÖĞŞÇİəüöğşçı][\w.-]*|/?>)
''', re.X)


def alqor_rənglə(kod: str) -> str:
    """Alqor kodunu `<span class=…>` ilə rəngləyir (HTML qaçışı daxil)."""
    n: list[str] = []
    i = 0
    for m in _ALQOR_TOKEN.finditer(kod):
        if m.start() > i:
            n.append(html.escape(kod[i:m.start()]))
        i = m.end()
        mətn = m.group(0)
        növ = m.lastgroup
        if növ == "w":
            if mətn in ACAR_SOZLER:
                sinif = "k"
            elif mətn in TIP_ADLARI:
                sinif = "t"
            elif mətn in _DAXİLİLƏR:
                sinif = "f"
            elif mətn[:1].isupper():
                sinif = "y"
            elif kod[i:i + 1] == "(":
                sinif = "m"
            else:
                sinif = ""
        else:
            sinif = {"c": "c", "s": "s", "n": "n", "a": "a", "j": "j"}[növ]
        e = html.escape(mətn)
        if sinif == "s" and "{" in mətn and not mətn.startswith(("x", "'")):
            e = re.sub(r"\{[^{}]*\}", lambda q: f'<span class="i">{q.group(0)}</span>', e)
        n.append(f'<span class="{sinif}">{e}</span>' if sinif else e)
    n.append(html.escape(kod[i:]))
    return "".join(n)


# ═══════════════════════════════════════════════════════════════════════
#  Markdown → HTML
# ═══════════════════════════════════════════════════════════════════════

def lövbər(mətn: str) -> str:
    s = latınla(kiçiyə(re.sub(r"<[^>]+>|[`*_]", "", mətn)))
    s = re.sub(r"[^\w\s-]", "", s, flags=re.ASCII)
    return re.sub(r"[\s_]+", "-", s).strip("-") or "bolme"


class _Səhifə:
    """Bir səhifənin çevrilmə vəziyyəti: başlıqlar, lövbərlər."""

    def __init__(self, keçid):
        self.keçid = keçid               # (href) -> yeni href | None
        self.başlıqlar: list[tuple[int, str, str]] = []
        self._lövbərlər: dict[str, int] = {}

    def lövbər_al(self, mətn: str) -> str:
        a = lövbər(mətn)
        n = self._lövbərlər.get(a, 0)
        self._lövbərlər[a] = n + 1
        return a if n == 0 else f"{a}-{n}"


def _sətirdaxili(m: str, s: _Səhifə) -> str:
    kodlar: list[str] = []

    def kod_saxla(q: re.Match) -> str:
        kodlar.append(f"<code>{html.escape(q.group(2))}</code>")
        return f"\x00{len(kodlar) - 1}\x00"

    m = re.sub(r"(`+)(.+?)\1", kod_saxla, m)
    m = html.escape(m, quote=False)

    def keçid(q: re.Match) -> str:
        mətn, href = q.group(1), html.unescape(q.group(2))
        yeni = s.keçid(href)
        if yeni is None:
            return mətn
        xarici = ' target="_blank" rel="noopener"' \
            if yeni.startswith("http") else ""
        return f'<a href="{html.escape(yeni)}"{xarici}>{mətn}</a>'

    m = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda q:
               f'<img alt="{q.group(1)}" src="{html.escape(s.keçid(html.unescape(q.group(2))) or "")}">', m)
    m = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", keçid, m)
    m = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", m)
    m = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", m)
    m = re.sub(r"(?<![\w\"=/])(https?://[^\s<)]+)",
               r'<a href="\1" target="_blank" rel="noopener">\1</a>', m)
    m = m.replace("&lt;br&gt;", "<br>")
    return re.sub(r"\x00(\d+)\x00", lambda q: kodlar[int(q.group(1))], m)


def _kod_bloku(dil: str, kod: str) -> str:
    dil = dil.strip().lower()
    if dil in ("alqor", "alq", ""):
        gövdə = alqor_rənglə(kod) if dil else html.escape(kod)
    else:
        gövdə = html.escape(kod)
    etiket = {"alqor": "Alqor", "alq": "Alqor", "bash": "terminal",
              "powershell": "PowerShell", "": ""}.get(dil, dil)
    baş = f'<span class="dil">{html.escape(etiket)}</span>' if etiket else ""
    return (f'<div class="kod">{baş}<button class="kopyala" type="button" '
            f'title="Kopyala">Kopyala</button><pre><code class="dil-{html.escape(dil or "mətn")}">'
            f"{gövdə}</code></pre></div>")


def _cədvəl(sətirlər: list[str], s: _Səhifə) -> str:
    def xanalar(sətir: str) -> list[str]:
        sətir = sətir.strip()
        if sətir.startswith("|"):
            sətir = sətir[1:]
        if sətir.endswith("|") and not sətir.endswith("\\|"):
            sətir = sətir[:-1]
        hissələr, cari, kodda = [], "", False
        i = 0
        while i < len(sətir):
            c = sətir[i]
            if c == "`":
                kodda = not kodda
            if c == "\\" and i + 1 < len(sətir) and sətir[i + 1] == "|":
                cari += "|"
                i += 2
                continue
            if c == "|" and not kodda:
                hissələr.append(cari)
                cari = ""
            else:
                cari += c
            i += 1
        hissələr.append(cari)
        return [h.strip() for h in hissələr]

    baş = xanalar(sətirlər[0])
    düzləmə = []
    for x in xanalar(sətirlər[1]):
        düzləmə.append("center" if x.startswith(":") and x.endswith(":")
                       else "right" if x.endswith(":") else "")
    n = ['<div class="cedvel"><table><thead><tr>']
    for j, h in enumerate(baş):
        st = f' style="text-align:{düzləmə[j]}"' if j < len(düzləmə) and düzləmə[j] else ""
        n.append(f"<th{st}>{_sətirdaxili(h, s)}</th>")
    n.append("</tr></thead><tbody>")
    for sətir in sətirlər[2:]:
        n.append("<tr>")
        for j, h in enumerate(xanalar(sətir)):
            st = f' style="text-align:{düzləmə[j]}"' if j < len(düzləmə) and düzləmə[j] else ""
            n.append(f"<td{st}>{_sətirdaxili(h, s)}</td>")
        n.append("</tr>")
    n.append("</tbody></table></div>")
    return "".join(n)


_SİYAHI = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def md_html(mətn: str, s: _Səhifə) -> str:
    sətirlər = mətn.replace("\t", "    ").split("\n")
    return _bloklar(sətirlər, s)


def _bloklar(sətirlər: list[str], s: _Səhifə) -> str:
    n: list[str] = []
    i = 0
    abzas: list[str] = []

    def abzas_bağla() -> None:
        if abzas:
            n.append(f"<p>{_sətirdaxili(' '.join(x.strip() for x in abzas), s)}</p>")
            abzas.clear()

    while i < len(sətirlər):
        sətir = sətirlər[i]
        st = sətir.strip()
        # Kod bloku
        m = re.match(r"^(\s*)(```+|~~~+)(.*)$", sətir)
        if m:
            abzas_bağla()
            girinti, çit, dil = len(m.group(1)), m.group(2), m.group(3)
            kod: list[str] = []
            i += 1
            while i < len(sətirlər) and not sətirlər[i].strip().startswith(çit):
                k = sətirlər[i]
                kod.append(k[girinti:] if k[:girinti].strip() == "" else k)
                i += 1
            n.append(_kod_bloku(dil, "\n".join(kod)))
            i += 1
            continue
        if not st:
            abzas_bağla()
            i += 1
            continue
        # Başlıq
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", sətir)
        if m:
            abzas_bağla()
            səviyyə = len(m.group(1))
            mətn_ = m.group(2)
            a = s.lövbər_al(mətn_)
            s.başlıqlar.append((səviyyə, mətn_, a))
            n.append(f'<h{səviyyə} id="{a}">{_sətirdaxili(mətn_, s)}'
                     f'<a class="lovber" href="#{a}" aria-label="Keçid">#</a></h{səviyyə}>')
            i += 1
            continue
        # Üfüqi xətt
        if re.match(r"^(\*\s*){3,}$|^(-\s*){3,}$|^(_\s*){3,}$", st):
            abzas_bağla()
            n.append("<hr>")
            i += 1
            continue
        # Cədvəl
        if st.startswith("|") and i + 1 < len(sətirlər) and \
                re.match(r"^\s*\|?\s*:?-{2,}", sətirlər[i + 1]):
            abzas_bağla()
            c = [sətir, sətirlər[i + 1]]
            i += 2
            while i < len(sətirlər) and sətirlər[i].strip().startswith("|"):
                c.append(sətirlər[i])
                i += 1
            n.append(_cədvəl(c, s))
            continue
        # Sitat
        if st.startswith(">"):
            abzas_bağla()
            q: list[str] = []
            while i < len(sətirlər) and sətirlər[i].strip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", sətirlər[i]))
                i += 1
            n.append(f"<blockquote>{_bloklar(q, s)}</blockquote>")
            continue
        # HTML
        if re.match(r"^<(p|div|img|br|table|details|summary|picture|source|/)", st):
            abzas_bağla()
            n.append(sətir)
            i += 1
            continue
        # Siyahı
        m = _SİYAHI.match(sətir)
        if m and (not abzas or not m.group(2)[0].isdigit()):
            abzas_bağla()
            i = _siyahı(sətirlər, i, s, n)
            continue
        abzas.append(sətir)
        i += 1
    abzas_bağla()
    return "\n".join(n)


def _siyahı(sətirlər: list[str], i: int, s: _Səhifə, n: list[str]) -> int:
    m = _SİYAHI.match(sətirlər[i])
    girinti = len(m.group(1))
    nömrəli = m.group(2)[0].isdigit()
    teq = "ol" if nömrəli else "ul"
    başla = f' start="{int(m.group(2)[:-1])}"' if nömrəli and int(m.group(2)[:-1]) != 1 else ""
    n.append(f"<{teq}{başla}>")
    while i < len(sətirlər):
        m = _SİYAHI.match(sətirlər[i])
        if not m or len(m.group(1)) != girinti or m.group(2)[0].isdigit() != nömrəli:
            break
        maddə = [m.group(3)]
        i += 1
        # Maddənin davamı (girintili sətirlər, alt siyahılar, kod)
        while i < len(sətirlər):
            x = sətirlər[i]
            if not x.strip():
                növbəti = next((y for y in sətirlər[i + 1:] if y.strip()), "")
                if len(növbəti) - len(növbəti.lstrip()) > girinti:
                    maddə.append("")
                    i += 1
                    continue
                break
            içə = len(x) - len(x.lstrip())
            if içə <= girinti and (_SİYAHI.match(x) or içə < girinti + 1):
                break
            maddə.append(x[min(içə, girinti + 2):] if içə > girinti else x)
            i += 1
        if len(maddə) == 1:
            n.append(f"<li>{_sətirdaxili(maddə[0], s)}</li>")
        else:
            iç = _bloklar(maddə, s)
            if iç.startswith("<p>"):
                son = iç.index("</p>")
                iç = iç[3:son] + iç[son + 4:]
            n.append(f"<li>{iç}</li>")
        while i < len(sətirlər) and not sətirlər[i].strip():
            növbəti = next((y for y in sətirlər[i + 1:] if y.strip()), "")
            mm = _SİYAHI.match(növbəti)
            if mm and len(mm.group(1)) == girinti:
                i += 1
            else:
                break
    n.append(f"</{teq}>")
    return i


# ═══════════════════════════════════════════════════════════════════════
#  Saytın quruluşu
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Səhifə:
    fayl: str                     # çıxış adı: "dil-dersliyi.html"
    başlıq: str
    qrup: str
    md: str = ""                  # Markdown mətni
    mənbə: Path | None = None
    təsvir: str = ""
    html_: str = ""
    başlıqlar: list = field(default_factory=list)


QRUPLAR = ("Başlanğıc", "Dərsliklər", "Arayış", "Dil spesifikasiyası",
           "Nümunələr")


def _başlıq_tap(md: str, standart: str) -> str:
    m = re.search(r"^#\s+(.+)$", md, re.M)
    if not m:
        return standart
    b = re.sub(r"`", "", m.group(1)).strip()
    b = re.sub(r"^Alqor Bələdçisi\s*[—–-]\s*\d+\.\s*", "", b)
    b = re.sub(r"^Alqor\s*[—–-]\s*", "", b)
    return b


def _slug(p: Path, ön: str = "") -> str:
    s = latınla(kiçiyə(p.stem))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return f"{ön}{s}.html"


def _ilk_addımlar() -> str:
    return f"""# Quraşdırdıqdan sonra — ilk addımlar

Alqor {VERSIYA.split('-')[0]} kompüterinizə quraşdırılıb. Bu səhifə ilk 10
dəqiqəni addım-addım izah edir. Bütün sənədlər bu kompüterdədir —
internet lazım deyil.

## 1. Alqor Studio-nu açın

**Başlat** menyusunda **Alqor Studio** seçin (masaüstü qısayolunu da
seçmisinizsə, oradan). Studio ilk açılışda `Sənədlər\\Alqor` qovluğunu
yaradır və nümunə proqramları ora kopyalayır.

Studio-da:

| Hissə | Nə edir |
|---|---|
| Sol panel | Layihə faylları, element paleti, axtarış |
| Mərkəz | Kod redaktoru — rəngləmə, avtomatik tamamlama, xəta işarələri |
| Sağ panel | Canlı önbaxış (interfeys proqramları üçün) |
| Aşağı panel | Proqramın çıxışı, xətalar, debaq |

Faydalı qısayollar: **F5** — işə sal, **F7** — vizual dizayner,
**Ctrl+Shift+P** — əmr palitrası, **Ctrl+S** — saxla.

## 2. İlk proqram

Studio-da yeni fayl yaradın (`salam.alq`) və yazın:

```alqor
yaz("Adınız nədir?")
dəyişən ad = oxu()
yaz("Salam, {{ad}}! Alqor-a xoş gəldiniz.")
```

**F5** basın — proqram aşağı paneldə işləyəcək. `{{ad}}` — mətnin içinə
dəyişənin dəyərini qoyur (interpolyasiya).

## 3. Terminaldan işləmək

Quraşdırıcı `alqor` əmrini **PATH**-a əlavə edib. Yeni PowerShell və ya
«Alqor terminalı» (Başlat menyusunda) açın:

```powershell
alqor yeni mənim-layihəm --şablon konsol
cd mənim-layihəm
alqor işlət
```

Şablonlar: `konsol`, `veb`, `desktop`, `kitabxana`. Layihə qovluğunda
`layihe.alq` (ayarlar), `mənbə\\əsas.alq` (proqram) və `sınaqlar\\` olur.

> Klaviaturanızda Azərbaycan hərfləri yoxdursa, açar sözləri ASCII ilə
> yaza bilərsiniz: `eger` → `əgər`, `islet` → `işlət`. Alqor onları tanıyır.

## 4. Proqramı paylaşmaq

```powershell
alqor qur --exe                # qurma\\<ad>.exe — istənilən Windows-da işləyir
alqor qur                      # qurma\\<ad>.pyz — Alqor olan kompüterdə işləyir
alqor qur --hədəf veb əsas.alq # qurma\\veb\\index.html — brauzerdə açılır
alqor qur --quraşdırıcı        # öz proqramınız üçün quraşdırıcı
alqor yerləşdir                # internetə çıxarmaq üçün hazır qovluq
```

`.exe` bir fayldır: dostunuza göndərin, o, heç nə quraşdırmadan işlədəcək.
İlk açılış bir neçə saniyə çəkir (proqram açılır), sonrakılar dərhal.
Pəncərəli proqramlar (`gətir pəncərə`) konsolsuz açılır. Studio-da:
**İşlət → Qur: tək .exe** (Ctrl+Shift+B).

Ətraflı: [Əmrlər arayışı](emrler.html) və
[Vebə yerləşdirmə](yerlesdirme.html).

## 5. Növbəti nə oxumalı?

| Məqsəd | Səhifə |
|---|---|
| Dili sıfırdan öyrənmək | [Dil dərsliyi](beledci-01-dil-dersliyi.html) — 17 dərs, tapşırıqlarla |
| Bir səhifədə hər şey | [Tez arayış](beledci-06-tez-arayis.html) |
| Veb sayt yazmaq | [Veb dərsliyi](beledci-02-veb-dersliyi.html) |
| Desktop tətbiq | [Desktop dərsliyi](beledci-03-desktop-dersliyi.html) və [Vidjet dərsliyi](beledci-07-vidjet-dersliyi.html) |
| Başqa dil bilirsiniz | [Köçürmə bələdçisi](beledci-04-kocurme-beledcisi.html) — Python/JS/C#/PHP qarşılıqları |
| Xəta mesajı aldınız | [Xəta lüğəti](beledci-05-xeta-lugeti.html) — hər kodun izahı |
| Hazır proqramlara baxmaq | [Nümunələr](numuneler.html) |

## Problem olarsa

- **`alqor` tanınmır** — quraşdırmadan sonra terminalı bağlayıb yenidən
  açın (PATH yenilənsin) və ya «Alqor terminalı»ndan istifadə edin.
- **Azərbaycan hərfləri terminalda pozulur** — Windows Terminal və ya
  PowerShell 7 işlədin; Alqor çıxışı UTF-8-dir.
- **Silmək** — *Parametrlər → Tətbiqlər → Alqor → Sil*. Layihələriniz
  (`Sənədlər\\Alqor`) toxunulmaz qalır.
"""


def _yerləşdirmə() -> str:
    return """# Vebə yerləşdirmə

Proqramınızı başqaları internetdən açsın deyə bir əmr kifayətdir:

```powershell
cd Sənədlər\\Alqor\\saytım
alqor yerləşdir
```

Nəticə `qurma\\yerləşdir\\` qovluğudur. İçində `YERLESDIR.md` var:
seçdiyiniz platforma üçün addım-addım təlimat. Studio-da:
**İşlət → Qur: vebə yerləşdir**.

## İki növ — Alqor özü seçir

| Proqramınız | Nəticə | Harada yerləşir |
|---|---|---|
| `gətir veb` **yoxdur** (konsol proqramı, hesablamalar, oyun) | **Statik sayt**: `index.html` — proqram JavaScript-ə çevrilib brauzerdə işləyir | Netlify, GitHub Pages, Cloudflare Pages, istənilən hostinq — **pulsuz**, server lazım deyil |
| `gətir veb` **var** (`veb.Server`, API, formalar) | **Server paketi**: `tetbiq.pyz` + `Dockerfile` | Render, Fly.io, Railway, öz VPS-iniz |

Məcburi seçmək: `alqor yerləşdir --statik` və ya `--server`.

## Statik sayt

```alqor
gətir konsol

funksiya əsas()
    dəyişən ad = konsol.soruş("Adınız: ", standart: "dünya")
    yaz(konsol.yaşıl("Salam, {ad}!"))
son
```

`alqor yerləşdir` → `qurma\\yerləşdir\\index.html`. Əvvəlcə yoxlayın:
faylı iki dəfə klikləyin — proqram brauzerdə işləyir. `oxu()` və
`konsol.soruş()` brauzerdə sual pəncərəsi açır.

### Netlify Drop — 1 dəqiqə

1. https://app.netlify.com/drop açın (pulsuz qeydiyyat).
2. `qurma\\yerləşdir` qovluğunu səhifəyə sürükləyin.
3. `https://<ad>.netlify.app` ünvanı dərhal işləyir.

### GitHub Pages

```powershell
alqor yerləşdir --çıxış docs
git add docs
git commit -m "Sayt"
git push
```

GitHub-da: **Settings → Pages → Branch: main, Folder: /docs**. Ünvan:
`https://<istifadəçi>.github.io/<repo>/`.

### Brauzerdə nə işləyir?

Statik saytda proqram JavaScript-ə çevrilir. Bu modullar dəstəklənir:
`riyaziyyat`, `mətn`, `təsadüfi`, `vaxt`, `json`, `naxış`, `sistem`,
`jurnal`, `paralel`, `konsol` və öz modullarınız. Başqa modul
(`veb`, `fayl`, `verilənlər`…) işlədirsinizsə, `alqor yerləşdir`
bunu deyir — onda server növünü seçin.

## Server tətbiqi

```alqor
gətir veb

dəyişən s = yeni veb.Server()
s.al("/", (sorğu) => veb.html(<h1>Salam, dünya!</h1>))
s.al("/salam/:ad", (sorğu) => veb.html(<h1>Salam, {sorğu.parametr("ad")}!</h1>))
s.dinlə(8080)
```

`alqor yerləşdir` bu faylları yaradır:

| Fayl | Nədir |
|---|---|
| `tetbiq.pyz` | Proqramınız və Alqor icra mühiti, tək fayl |
| `Dockerfile` | Konteyner təsviri (Python 3.12) |
| `YERLESDIR.md` | Render, Fly.io və VPS üçün addımlar |

**Port**: kodda `s.dinlə(8080)` yazsanız da, platforma `PORT` mühit
dəyişənini verirsə, server həmin portda açılır. `ALQOR_HOST=0.0.0.0`
serveri bütün şəbəkə interfeyslərində açır (Dockerfile bunu özü edir).
Kodda heç nə dəyişmək lazım deyil.

### Yerli yoxlama

```powershell
python qurma\\yerləşdir\\tetbiq.pyz     # http://127.0.0.1:8080
```

### Render.com — pulsuz plan

1. `qurma\\yerləşdir` qovluğunu GitHub-da yeni repoya yükləyin.
2. render.com → **New → Web Service** → reponu seçin.
3. **Runtime: Docker** avtomatik seçilir → **Create Web Service**.
4. Bir neçə dəqiqəyə `https://<ad>.onrender.com` hazırdır.

### Öz serveriniz (VPS)

```bash
docker build -t saytim .
docker run -d --restart always -p 80:8080 saytim
```

Docker yoxdursa: serverdə Python 3.12 qurun və
`ALQOR_HOST=0.0.0.0 PORT=80 python tetbiq.pyz` işlədin.

## Yeniləmək

Kodu dəyişdikdən sonra yenidən `alqor yerləşdir` işlədin və qovluğu
təzədən yükləyin (Netlify-da sürükləyin, GitHub-da `git push`).

## Problem olarsa

- **"statik sayta çevrilmədi: `X` modulu JS hədəfində dəstəklənmir"** —
  `alqor yerləşdir --server` işlədin.
- **"proqramda xəta var"** — əvvəlcə `alqor işlət` ilə xətanı düzəldin;
  xətalı proqram yerləşdirilmir.
- **Render-də sayt açılmır** — *Logs* bölməsinə baxın; `PORT`-u kodda
  dəyişməyin, Alqor onu özü oxuyur.
"""


def _əmrlər() -> str:
    return """# Əmrlər arayışı

Terminalda (PowerShell, cmd, «Alqor terminalı») işlədilən bütün əmrlər.
Hər əmrin ASCII forması da var: `işlət` = `islet` = `run`.

## Proqramı işlətmək

```powershell
alqor işlət proqram.alq           # faylı icra edir
alqor işlət                       # layihə qovluğunda: giriş faylı (layihe.alq)
alqor işlət proqram.alq -- a b    # proqrama arqument: sistem.arqumentlər()
alqor işlət --tip proqram.alq     # əvvəl tipləri yoxlayır
alqor işlət --js proqram.alq      # JavaScript-ə çevirib Node.js ilə (sürətli)
alqor söhbət                      # interaktiv rejim (REPL)
```

İnteraktiv rejimdə ifadə yazıb dərhal nəticəni görürsünüz:

```
alqor> 2 ** 64
18446744073709551616  // tam
alqor> "ışıq".böyüyə()
"IŞIQ"  // mətn
```

## Layihə

| Əmr | Nə edir |
|---|---|
| `alqor yeni ad --şablon konsol` | Yeni layihə: `konsol`, `veb`, `desktop`, `kitabxana` |
| `alqor sına` | `@sınaq` funksiyalarını işlədir; `--filtr söz`, `--ətraflı` |
| `alqor sənəd` | `///` şərhlərindən API sənədi: `sənəd/indeks.html` |
| `alqor format .` | Kodu səliqəyə salır; `--yoxla` dəyişdirmədən yoxlayır |
| `alqor lint .` | Statik təhlil (35 qayda); `--düzəlt` avtomatik düzəldir |
| `alqor yoxla fayl.alq` | Sintaksis və tip xətalarını göstərir |
| `alqor təmizlə` | `qurma\\` qovluğunu silir |

## Qurmaq və paylaşmaq

| Əmr | Nəticə |
|---|---|
| `alqor qur --exe` | `qurma\\<ad>.exe` — **tək fayl**, Alqor və Python olmayan Windows kompüterində də işləyir |
| `alqor qur --exe proqram.alq` | Layihəsiz tək fayldan `.exe` |
| `alqor qur` | `qurma\\<ad>.pyz` — tək fayllı paket (Alqor/Python olan kompüterdə) |
| `alqor qur --quraşdırıcı` | Proqramınız üçün Windows quraşdırıcısı |
| `alqor qur --hədəf js fayl.alq` | `qurma\\<ad>.js` — Node.js ilə işləyir |
| `alqor qur --hədəf veb fayl.alq` | `qurma\\veb\\index.html` — brauzerdə açılır, server lazım deyil |
| `alqor yerləşdir` | `qurma\\yerləşdir\\` — internetə yükləmək üçün hazır qovluq ([ətraflı](yerlesdirme.html)) |
| `alqor yerləşdir --statik` / `--server` | Növü məcburi seçir (statik sayt və ya Docker) |
| `alqor yerləşdir --çıxış docs` | GitHub Pages üçün `docs\\` qovluğu |

JavaScript hədəfi bu modulları dəstəkləyir: `riyaziyyat`, `mətn`,
`təsadüfi`, `vaxt`, `json`, `naxış`, `sistem`, `jurnal`, `paralel`,
`konsol`;
Node.js-də həm də `fayl`, `qovluq`, `yol`.

## Paketlər

```powershell
alqor pm əlavə tarix_alətləri     # asılılıq əlavə edir (layihe.alq)
alqor pm sil tarix_alətləri
alqor pm siyahı                   # quraşdırılmış paketlər
alqor pm ağac                     # asılılıq ağacı
```

`alqorpm`, `alqorlint`, `alqorfmt` əmrləri `alqor pm`, `alqor lint`,
`alqor format`-ın qısa formalarıdır.

## Alətlər

| Əmr | Nə edir |
|---|---|
| `alqor studio [qovluq]` | Alqor Studio-nu açır |
| `alqor sənədlər` | Bu sənədləri brauzerdə açır |
| `alqor ls` | Dil serveri (LSP) — VS Code, Neovim |
| `alqor dap` | Debaqçı (DAP) |
| `alqor hərf "ışıq"` | Azərbaycan böyük/kiçik hərf qaydalarını göstərir |
| `alqor sırala zəfər ağac çay` | Əlifba sırası ilə sıralayır |
| `alqor versiya` | Versiya |
| `alqor kömək` | Əmrlərin qısa siyahısı |

## Mühit dəyişənləri

| Dəyişən | Mənası |
|---|---|
| `ALQOR_RENG` | `həmişə` / `heçvaxt` / `avto` — rəngli xəta çıxışı |
| `ALQOR_NODE` | `--js` üçün Node.js yolu |

## Çıxış kodları

| Kod | Mənası |
|---|---|
| 0 | Uğurlu |
| 1 | İcra xətası |
| 2 | Sintaksis və ya tip xətası |
| 3 | Yanlış əmr və ya arqument |
| 4 | Fayl tapılmadı / oxunmadı |
"""


def _nümunə_səhifəsi(f: Path, repo: Path) -> tuple[str, str]:
    mətn = f.read_text(encoding="utf-8")
    şərh: list[str] = []
    for sətir in mətn.splitlines():
        if sətir.startswith("//"):
            şərh.append(sətir[2:].strip())
        else:
            break
    başlıq = şərh[0] if şərh else f.stem
    başlıq = re.sub(r"^Nümunə\s*\d+\s*[—–-]\s*", "", başlıq)
    izah = "\n".join(şərh[1:]).strip()
    nisbi = f.relative_to(repo).as_posix()
    md = [f"# {başlıq}", ""]
    if izah:
        md += ["```", izah, "```", ""]
    md += ["## Necə işlətmək", "", "```powershell",
           f"alqor işlət {nisbi.replace('/', chr(92))}", "```", "",
           "Studio-da: faylı açın və **F5** basın. Nümunələr ilk açılışda "
           "`Sənədlər\\Alqor\\nümunələr` qovluğuna kopyalanır.", "",
           "## Kod", "", "```alqor", mətn.rstrip(), "```"]
    return başlıq, "\n".join(md)


def səhifələr(repo: Path) -> list[Səhifə]:
    n: list[Səhifə] = [
        Səhifə("ilk-addimlar.html", "İlk addımlar", "Başlanğıc",
               _ilk_addımlar(), təsvir="Quraşdırmadan sonra 10 dəqiqə"),
        Səhifə("yerlesdirme.html", "Vebə yerləşdirmə", "Başlanğıc",
               _yerləşdirmə(), təsvir="Proqramı internetə çıxarmaq"),
    ]
    bələdçi = repo / "beledci"
    sıra = {"00": "Başlanğıc", "01": "Dərsliklər", "02": "Dərsliklər",
            "03": "Dərsliklər", "07": "Dərsliklər", "04": "Dərsliklər",
            "06": "Arayış", "05": "Arayış"}
    for nömrə in ("00", "01", "02", "03", "07", "04", "06", "05"):
        for f in sorted(bələdçi.glob(f"{nömrə}-*.md")):
            md = f.read_text(encoding="utf-8")
            n.append(Səhifə(_slug(f, "beledci-"), _başlıq_tap(md, f.stem),
                            sıra[nömrə], md, f))
            if nömrə == "06":
                n.append(Səhifə("emrler.html", "Əmrlər arayışı", "Arayış",
                                _əmrlər(), təsvir="alqor işlət, yeni, qur…"))
    spes = repo / "spesifikasiya"
    for f in sorted(spes.glob("[0-9]*.md")):
        md = f.read_text(encoding="utf-8")
        n.append(Səhifə(_slug(f, "spes-"), _başlıq_tap(md, f.stem),
                        "Dil spesifikasiyası", md, f))
    açar = spes / "acar-sozler.md"
    if açar.is_file():
        md = açar.read_text(encoding="utf-8")
        n.append(Səhifə("spes-acar-sozler.html", "Açar sözlər", "Arayış",
                        md, açar))
    ebnf = spes / "qrammatika.ebnf"
    if ebnf.is_file():
        n.append(Səhifə("spes-qrammatika.html", "Rəsmi qrammatika (EBNF)",
                        "Arayış",
                        "# Rəsmi qrammatika (EBNF)\n\nAlqor-un sintaksisinin "
                        "formal tərifi.\n\n```ebnf\n"
                        + ebnf.read_text(encoding="utf-8") + "\n```\n", ebnf))
    nümunələr = repo / "numuneler"
    if nümunələr.is_dir():
        siyahı = ["# Nümunə proqramlar", "",
                  "Hər nümunə tam, işləyən proqramdır — kodu oxuyun, "
                  "dəyişin, işlədin.", "", "| Nümunə | Mövzu |", "|---|---|"]
        alt: list[Səhifə] = []
        fayllar = sorted(nümunələr.glob("*.alq")) + sorted(
            p for q in sorted(nümunələr.iterdir()) if q.is_dir()
            for p in q.glob("*.alq"))
        for f in fayllar:
            başlıq, md = _nümunə_səhifəsi(f, repo)
            ad = _slug(f.relative_to(nümunələr).with_suffix(""), "numune-") \
                if f.parent == nümunələr else \
                _slug(Path(f"{f.parent.name}-{f.stem}"), "numune-")
            alt.append(Səhifə(ad, başlıq, "Nümunələr", md, f))
            siyahı.append(f"| [{f.relative_to(nümunələr).as_posix()}]({ad}) | {başlıq} |")
        n.append(Səhifə("numuneler.html", "Bütün nümunələr", "Nümunələr",
                        "\n".join(siyahı)))
        n += alt
    return n


# ═══════════════════════════════════════════════════════════════════════
#  HTML şablonu
# ═══════════════════════════════════════════════════════════════════════

_CSS = r"""
:root{--fon:#fbfaf7;--panel:#f2f0ea;--mətn:#1d1d1f;--sönük:#666158;--kənar:#e2ded4;
--vurğu:#0f6b5c;--vurğu2:#e8f3f0;--kod-fon:#f4f2ec;--k:#a3304b;--t:#1f5fa8;--s:#2f7d32;
--n:#a15c00;--c:#8a857a;--f:#6b3fa0;--y:#00627a;--i:#b0477a;--j:#1f5fa8;--a:#a15c00;color-scheme:light}
:root[data-tema=qaranliq]{--fon:#16171a;--panel:#1d1f23;--mətn:#e6e3dc;--sönük:#9b968b;--kənar:#2e3036;
--vurğu:#4fc1a9;--vurğu2:#1c2d2a;--kod-fon:#1f2125;--k:#ff7b95;--t:#7cb7ff;--s:#8fd694;--n:#f0b46b;
--c:#7d786e;--f:#c49bff;--y:#5fd0e6;--i:#ff9ccc;--j:#7cb7ff;--a:#f0b46b;color-scheme:dark}
@media (prefers-color-scheme:dark){:root:not([data-tema=aydin]){--fon:#16171a;--panel:#1d1f23;--mətn:#e6e3dc;
--sönük:#9b968b;--kənar:#2e3036;--vurğu:#4fc1a9;--vurğu2:#1c2d2a;--kod-fon:#1f2125;--k:#ff7b95;--t:#7cb7ff;
--s:#8fd694;--n:#f0b46b;--c:#7d786e;--f:#c49bff;--y:#5fd0e6;--i:#ff9ccc;--j:#7cb7ff;--a:#f0b46b;color-scheme:dark}}
*{box-sizing:border-box}html{scroll-padding-top:72px}
body{margin:0;background:var(--fon);color:var(--mətn);font:16px/1.65 "Segoe UI",system-ui,-apple-system,Roboto,sans-serif}
a{color:var(--vurğu)}code,pre{font-family:"Cascadia Code",Consolas,"JetBrains Mono",ui-monospace,monospace}
header.ust{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:16px;height:56px;padding:0 20px;
background:var(--fon);border-bottom:1px solid var(--kənar)}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px;color:var(--mətn);text-decoration:none}
.logo img{height:28px}.versiya{font-size:12px;color:var(--sönük);font-weight:400}
.axtar{position:relative;flex:1;max-width:480px;margin-left:auto}
.axtar input{width:100%;padding:8px 12px;border:1px solid var(--kənar);border-radius:8px;background:var(--panel);
color:var(--mətn);font:inherit;font-size:14px}
.axtar input:focus{outline:2px solid var(--vurğu);outline-offset:-1px}
#netice{position:absolute;top:42px;left:0;right:0;max-height:70vh;overflow:auto;background:var(--fon);
border:1px solid var(--kənar);border-radius:8px;box-shadow:0 8px 28px rgba(0,0,0,.18);display:none}
#netice a{display:block;padding:8px 12px;text-decoration:none;color:var(--mətn);border-bottom:1px solid var(--kənar)}
#netice a:hover,#netice a.secili{background:var(--vurğu2)}#netice small{display:block;color:var(--sönük);font-size:12px}
#netice b{color:var(--vurğu)}
.duyme{border:1px solid var(--kənar);background:var(--panel);color:var(--mətn);border-radius:8px;padding:6px 10px;
cursor:pointer;font:inherit;font-size:13px}
.menyu-duyme{display:none}
.duzen{display:grid;grid-template-columns:270px minmax(0,1fr) 220px;max-width:1440px;margin:0 auto}
nav.yan{position:sticky;top:56px;height:calc(100vh - 56px);overflow:auto;padding:20px 12px 40px 20px;
border-right:1px solid var(--kənar);font-size:14px}
nav.yan h4{margin:18px 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--sönük)}
nav.yan a{display:block;padding:4px 10px;border-radius:6px;color:var(--mətn);text-decoration:none}
nav.yan a:hover{background:var(--panel)}nav.yan a.aktiv{background:var(--vurğu2);color:var(--vurğu);font-weight:600}
main{padding:32px 48px 80px;min-width:0}
article{max-width:860px}
article h1{font-size:34px;line-height:1.2;margin:0 0 24px}
article h2{font-size:24px;margin:44px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--kənar)}
article h3{font-size:19px;margin:30px 0 10px}article h4{font-size:16px;margin:24px 0 8px}
.lovber{margin-left:8px;color:var(--sönük);text-decoration:none;opacity:0;font-weight:400}
h1:hover .lovber,h2:hover .lovber,h3:hover .lovber,h4:hover .lovber{opacity:1}
p code,li code,td code,th code{background:var(--kod-fon);padding:1px 5px;border-radius:4px;font-size:.9em}
.kod{position:relative;margin:16px 0;border:1px solid var(--kənar);border-radius:10px;background:var(--kod-fon)}
.kod pre{margin:0;padding:16px 18px;overflow:auto;font-size:14px;line-height:1.55}
.kod .dil{position:absolute;top:6px;right:84px;font-size:11px;color:var(--sönük);text-transform:uppercase;letter-spacing:.05em}
.kopyala{position:absolute;top:6px;right:8px;font-size:12px;padding:2px 8px;border:1px solid var(--kənar);
border-radius:6px;background:var(--fon);color:var(--sönük);cursor:pointer;opacity:0}
.kod:hover .kopyala,.kopyala:focus{opacity:1}
.k{color:var(--k);font-weight:600}.t{color:var(--t)}.s{color:var(--s)}.n{color:var(--n)}.c{color:var(--c);font-style:italic}
.f{color:var(--f)}.y{color:var(--y)}.i{color:var(--i)}.j{color:var(--j)}.a{color:var(--a)}.m{color:var(--f)}
.cedvel{overflow-x:auto;margin:16px 0}table{border-collapse:collapse;width:100%;font-size:14.5px}
th,td{border:1px solid var(--kənar);padding:7px 10px;text-align:left;vertical-align:top}th{background:var(--panel)}
blockquote{margin:16px 0;padding:10px 16px;border-left:4px solid var(--vurğu);background:var(--vurğu2);border-radius:0 8px 8px 0}
blockquote p{margin:6px 0}hr{border:0;border-top:1px solid var(--kənar);margin:32px 0}
img{max-width:100%;border-radius:8px}
aside.toc{position:sticky;top:56px;height:calc(100vh - 56px);overflow:auto;padding:32px 16px;font-size:13px}
aside.toc b{display:block;color:var(--sönük);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
aside.toc a{display:block;padding:3px 0 3px 10px;color:var(--sönük);text-decoration:none;border-left:2px solid var(--kənar)}
aside.toc a.h3{padding-left:22px}aside.toc a.aktiv{color:var(--vurğu);border-left-color:var(--vurğu)}
.ardicil{display:flex;justify-content:space-between;gap:16px;margin-top:56px;padding-top:20px;border-top:1px solid var(--kənar)}
.ardicil a{flex:1;padding:12px 16px;border:1px solid var(--kənar);border-radius:10px;text-decoration:none;color:var(--mətn)}
.ardicil a small{display:block;color:var(--sönük);font-size:12px}.ardicil a.sonra{text-align:right}
.kartlar{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin:20px 0}
.kart{display:block;padding:16px 18px;border:1px solid var(--kənar);border-radius:12px;text-decoration:none;color:var(--mətn);background:var(--panel)}
.kart:hover{border-color:var(--vurğu)}.kart b{display:block;margin-bottom:4px;color:var(--vurğu)}.kart span{font-size:14px;color:var(--sönük)}
.qəhrəman{padding:28px 32px;border-radius:16px;background:var(--vurğu2);margin-bottom:28px}
.qəhrəman h1{margin:0 0 8px}.qəhrəman p{margin:0;font-size:18px;color:var(--sönük)}
@media (max-width:1180px){.duzen{grid-template-columns:250px minmax(0,1fr)}aside.toc{display:none}}
@media (max-width:820px){.duzen{display:block}nav.yan{display:none;position:fixed;top:56px;left:0;right:0;bottom:0;
height:auto;background:var(--fon);z-index:4;border:0}body.menyu-acik nav.yan{display:block}
.menyu-duyme{display:inline-block}main{padding:20px 16px 60px}.axtar{max-width:none}.logo .versiya{display:none}}
@media print{header.ust,nav.yan,aside.toc,.ardicil,.kopyala{display:none}.duzen{display:block}}
"""

_JS = r"""
(function(){
var kok=document.documentElement;
try{var t=localStorage.getItem("alqor-tema");if(t)kok.dataset.tema=t;}catch(e){}
document.getElementById("tema").onclick=function(){
  var q=kok.dataset.tema==="qaranliq"||(!kok.dataset.tema&&matchMedia("(prefers-color-scheme:dark)").matches);
  kok.dataset.tema=q?"aydin":"qaranliq";try{localStorage.setItem("alqor-tema",kok.dataset.tema);}catch(e){}};
document.getElementById("menyu").onclick=function(){document.body.classList.toggle("menyu-acik");};
document.querySelectorAll(".kopyala").forEach(function(d){d.onclick=function(){
  var k=d.parentNode.querySelector("code").innerText;
  var bitdi=function(){d.textContent="Kopyalandı ✓";setTimeout(function(){d.textContent="Kopyala";},1500);};
  if(navigator.clipboard)navigator.clipboard.writeText(k).then(bitdi,function(){});else{
  var t=document.createElement("textarea");t.value=k;document.body.appendChild(t);t.select();
  try{document.execCommand("copy");bitdi();}catch(e){}t.remove();}};});
var a=document.querySelector("nav.yan a.aktiv");if(a)a.scrollIntoView({block:"center"});
// Mündəricat — oxunan bölməni işıqlandırır
var toc=[].slice.call(document.querySelectorAll("aside.toc a"));
if(toc.length&&"IntersectionObserver" in window){var hed={};toc.forEach(function(x){hed[x.getAttribute("href").slice(1)]=x;});
var io=new IntersectionObserver(function(e){e.forEach(function(g){if(g.isIntersecting){toc.forEach(function(x){x.classList.remove("aktiv");});
var x=hed[g.target.id];if(x)x.classList.add("aktiv");}});},{rootMargin:"-60px 0px -70% 0px"});
document.querySelectorAll("article h2[id],article h3[id]").forEach(function(h){io.observe(h);});}
// Axtarış (Azərbaycan hərfləri: "eger" → "əgər" də tapılır)
var XERITE={"ə":"e","ı":"i","İ":"i","I":"i","ö":"o","ü":"u","ç":"c","ş":"s","ğ":"g"};
function sade(s){return s.replace(/[İI]/g,"i").toLowerCase().replace(/[əıöüçşğ]/g,function(c){return XERITE[c];});}
var inp=document.getElementById("axtar"),net=document.getElementById("netice"),sec=-1;
function qac(s){return s.replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function axtar(){var q=sade(inp.value.trim());sec=-1;if(q.length<2){net.style.display="none";return;}
var sozler=q.split(/\s+/),n=[];
for(var i=0;i<AXTARIS.length;i++){var e=AXTARIS[i],b=sade(e.b),m=sade(e.m),bal=0,ok=true;
for(var j=0;j<sozler.length;j++){var s=sozler[j];if(b.indexOf(s)>=0)bal+=10;else if(m.indexOf(s)>=0)bal+=1;else{ok=false;break;}}
if(ok){if(b.indexOf(q)===0)bal+=20;n.push([bal,e]);}}
n.sort(function(x,y){return y[0]-x[0];});n=n.slice(0,30);
net.innerHTML=n.length?n.map(function(x){var e=x[1];var i=sade(e.m).indexOf(sozler[0]);
var p=e.m.substr(Math.max(0,i-40),140);return'<a href="'+e.u+'"><b>'+qac(e.b)+'</b><small>'+qac(e.s)+' · …'+qac(p)+'…</small></a>';}).join("")
:'<a><small>Heç nə tapılmadı</small></a>';net.style.display="block";}
inp.addEventListener("input",axtar);inp.addEventListener("focus",axtar);
inp.addEventListener("keydown",function(ev){var x=net.querySelectorAll("a[href]");if(!x.length)return;
if(ev.key==="ArrowDown"||ev.key==="ArrowUp"){ev.preventDefault();sec=(sec+(ev.key==="ArrowDown"?1:-1)+x.length)%x.length;
x.forEach(function(a,i){a.classList.toggle("secili",i===sec);});x[sec].scrollIntoView({block:"nearest"});}
else if(ev.key==="Enter"){location.href=(x[sec>=0?sec:0]).getAttribute("href");}
else if(ev.key==="Escape"){net.style.display="none";inp.blur();}});
document.addEventListener("click",function(ev){if(!ev.target.closest(".axtar"))net.style.display="none";});
document.addEventListener("keydown",function(ev){if(ev.key==="/"&&document.activeElement!==inp){ev.preventDefault();inp.focus();}});
})();
"""


def _şablon(s: Səhifə, nav: str, toc: str, əvvəl: Səhifə | None,
            sonra: Səhifə | None) -> str:
    ardıcıl = ""
    if əvvəl or sonra:
        ardıcıl = '<div class="ardicil">'
        ardıcıl += (f'<a href="{əvvəl.fayl}"><small>← Əvvəlki</small>'
                    f"{html.escape(əvvəl.başlıq)}</a>" if əvvəl else "<span></span>")
        ardıcıl += (f'<a class="sonra" href="{sonra.fayl}"><small>Növbəti →</small>'
                    f"{html.escape(sonra.başlıq)}</a>" if sonra else "<span></span>")
        ardıcıl += "</div>"
    v = VERSIYA.split("-")[0]
    return f"""<!DOCTYPE html>
<html lang="az"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(s.başlıq)} — Alqor sənədləri</title>
<link rel="icon" href="loqo.svg"><link rel="stylesheet" href="stil.css">
</head><body>
<header class="ust">
<button class="duyme menyu-duyme" id="menyu" type="button" aria-label="Menyu">☰</button>
<a class="logo" href="index.html"><img src="loqo.svg" alt="">Alqor <span class="versiya">sənədlər · {v}</span></a>
<div class="axtar"><input id="axtar" type="search" placeholder="Axtar… (məs. siyahı, cəhd et, eger)" autocomplete="off"><div id="netice"></div></div>
<button class="duyme" id="tema" type="button" title="Tema">◐</button>
</header>
<div class="duzen">
<nav class="yan">{nav}</nav>
<main><article>{s.html_}</article>{ardıcıl}</main>
<aside class="toc">{toc}</aside>
</div>
<script src="axtaris.js"></script><script src="sened.js"></script>
</body></html>
"""


def _ana_səhifə(səhifələr: list[Səhifə]) -> str:
    kart = lambda f, b, t: (f'<a class="kart" href="{f}"><b>{html.escape(b)}</b>'
                            f"<span>{html.escape(t)}</span></a>")
    q = {s.fayl: s for s in səhifələr}

    def k(fayl: str, təsvir: str) -> str:
        s = q.get(fayl)
        return kart(fayl, s.başlıq, təsvir) if s else ""

    nümunə = """dəyişən meyvələr = ["alma", "armud", "üzüm"]

hər m üçün meyvələr içində
    yaz("Mən {m} sevirəm")
son"""
    return f"""<div class="qəhrəman"><h1>Alqor sənədləri</h1>
<p>Azərbaycan dilində proqramlaşdırma — dərsliklər, arayış, dilin tam
təsviri və nümunələr. Hamısı bu kompüterdədir, internet lazım deyil.</p></div>
{_kod_bloku("alqor", nümunə)}
<h2 id="baslayin">Haradan başlamalı?</h2>
<div class="kartlar">
{k("ilk-addimlar.html", "Quraşdırmadan sonra: Studio, ilk proqram, terminal")}
{k("beledci-00-baslangic.html", "10 dəqiqəlik tur")}
{k("beledci-01-dil-dersliyi.html", "Sıfırdan 17 dərs, tapşırıqlarla")}
{k("beledci-06-tez-arayis.html", "Bütün dil bir səhifədə")}
</div>
<h2 id="derslikler">Dərsliklər</h2>
<div class="kartlar">
{k("beledci-02-veb-dersliyi.html", "Veb sayt, forma, JSON API")}
{k("beledci-03-desktop-dersliyi.html", "Pəncərə, menyu, dialoq")}
{k("yerlesdirme.html", "Saytınızı internetə çıxarın: Netlify, Render, VPS")}
{k("beledci-07-vidjet-dersliyi.html", "118 hazır interfeys elementi")}
{k("beledci-04-kocurme-beledcisi.html", "Python, JS, C#, PHP bilənlərə")}
</div>
<h2 id="arayis">Arayış</h2>
<div class="kartlar">
{k("emrler.html", "alqor işlət, yeni, qur, sına…")}
{k("beledci-05-xeta-lugeti.html", "Hər xəta kodunun izahı və həlli")}
{k("spes-10-standart-kitabxana.html", "Bütün modullar və funksiyalar")}
{k("spes-acar-sozler.html", "Açar sözlər və ASCII formaları")}
{k("numuneler.html", "Tam işləyən proqramlar")}
</div>
<p>Axtarış üçün yuxarıdakı sahəni işlədin (və ya <code>/</code> basın).
Azərbaycan hərfləri olmadan da tapır: <code>eger</code> → <code>əgər</code>.</p>"""


def qur(repo: Path, çıxış: Path) -> Path:
    """Sənəd saytını `çıxış/` qovluğuna qurur. Qaytarır: index.html."""
    if çıxış.exists():
        shutil.rmtree(çıxış)
    çıxış.mkdir(parents=True)
    hamısı = səhifələr(repo)
    mənbə_xəritəsi = {s.mənbə.resolve(): s.fayl for s in hamısı if s.mənbə}
    şəkillər: dict[Path, str] = {}

    for s in hamısı:
        baza = s.mənbə.parent if s.mənbə else repo

        def keçid(href: str, baza=baza) -> str | None:
            if re.match(r"^[a-z]+:", href) or href.startswith("#"):
                return href
            yol, _, lövbər_ = href.partition("#")
            if not yol:
                return href
            if yol.endswith(".html"):
                return href
            hədəf = (baza / yol).resolve()
            if hədəf in mənbə_xəritəsi:
                return mənbə_xəritəsi[hədəf] + (f"#{lövbər_}" if lövbər_ else "")
            if hədəf.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".gif") \
                    and hədəf.is_file():
                ad = "sekil-" + hədəf.name
                şəkillər[hədəf] = ad
                return ad
            return None

        ç = _Səhifə(keçid)
        s.html_ = md_html(s.md, ç)
        s.başlıqlar = ç.başlıqlar

    # Ana səhifə
    ana = Səhifə("index.html", "Xoş gəlmisiniz", "Başlanğıc")
    ana.html_ = _ana_səhifə(hamısı)
    ana.başlıqlar = [(2, "Haradan başlamalı?", "baslayin"),
                     (2, "Dərsliklər", "derslikler"), (2, "Arayış", "arayis")]
    sıralı = [ana] + sorted(hamısı, key=lambda s: QRUPLAR.index(s.qrup))

    # Axtarış indeksi — h2/h3 bölmələri
    indeks: list[dict] = []
    for s in sıralı:
        mətn = re.sub(r"<[^>]+>", " ", s.html_)
        mətn = html.unescape(re.sub(r"\s+", " ", mətn))
        indeks.append({"b": s.başlıq, "s": s.qrup, "u": s.fayl, "m": mətn[:400]})
        hissələr = re.split(r'<h([23]) id="([^"]+)">', s.html_)
        for j in range(1, len(hissələr) - 2, 3):
            parça = hissələr[j + 2]
            b = html.unescape(re.sub(r"<[^>]+>", "", parça.split("</h", 1)[0])).rstrip("#").strip()
            gövdə = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", parça.split("</h", 1)[-1])))
            indeks.append({"b": b, "s": s.başlıq, "u": f"{s.fayl}#{hissələr[j + 1]}",
                           "m": gövdə[:600]})

    for i, s in enumerate(sıralı):
        nav = []
        for q in QRUPLAR:
            nav.append(f"<h4>{html.escape(q)}</h4>")
            for x in sıralı:
                if x.qrup == q:
                    aktiv = ' class="aktiv"' if x is s else ""
                    nav.append(f'<a href="{x.fayl}"{aktiv}>{html.escape(x.başlıq)}</a>')
        toc_b = [(lv, t, a) for lv, t, a in s.başlıqlar if lv in (2, 3)]
        toc = ""
        if len(toc_b) > 1:
            toc = "<b>Bu səhifədə</b>" + "".join(
                f'<a class="h{lv}" href="#{a}">{html.escape(re.sub("[`*]", "", t))}</a>'
                for lv, t, a in toc_b)
        əvvəl = sıralı[i - 1] if i > 0 else None
        sonra = sıralı[i + 1] if i + 1 < len(sıralı) else None
        (çıxış / s.fayl).write_text(_şablon(s, "".join(nav), toc, əvvəl, sonra),
                                    encoding="utf-8")

    (çıxış / "stil.css").write_text(_CSS, encoding="utf-8")
    (çıxış / "sened.js").write_text(_JS, encoding="utf-8")
    (çıxış / "axtaris.js").write_text(
        "var AXTARIS=" + json.dumps(indeks, ensure_ascii=False) + ";\n",
        encoding="utf-8")
    loqo = repo / "loqo" / "alqor-ikon.svg"
    if not loqo.is_file():
        loqo = next(iter(sorted((repo / "loqo").glob("*.svg"))), None) \
            if (repo / "loqo").is_dir() else None
    if loqo:
        shutil.copyfile(loqo, çıxış / "loqo.svg")
    for mənbə, ad in şəkillər.items():
        shutil.copyfile(mənbə, çıxış / ad)
    return çıxış / "index.html"


def sənəd_qovluğu(alqorc_kökü: Path) -> Path:
    """Quraşdırılmış Alqor-da `<kök>/sened`, inkişafda keş qovluğu."""
    quraşdırılmış = alqorc_kökü.parent / "sened"
    if (quraşdırılmış / "index.html").is_file():
        return quraşdırılmış
    import os
    keş = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache") / \
        "alqor" / f"sened-{VERSIYA}"
    repo = alqorc_kökü.parent
    if not (keş / "index.html").is_file() or _köhnədir(repo, keş):
        qur(repo, keş)
    return keş


def _köhnədir(repo: Path, keş: Path) -> bool:
    try:
        vaxt = (keş / "index.html").stat().st_mtime
        for q in ("beledci", "spesifikasiya", "numuneler"):
            for f in (repo / q).rglob("*"):
                if f.is_file() and f.stat().st_mtime > vaxt:
                    return True
        return Path(__file__).stat().st_mtime > vaxt
    except OSError:
        return True
