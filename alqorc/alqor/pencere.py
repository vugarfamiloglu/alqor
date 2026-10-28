"""
Alqor — `pəncərə` modulu: desktop tətbiqləri.

Spesifikasiya § 12. Xarici asılılıq yoxdur.

ARXİTEKTURA — yerli server + yerli pəncərə (Tauri modeli)
─────────────────────────────────────────────────────────
Komponentin `göstər()` metodu JSX qaytarır; JSX artıq HTML-ə çevrilir
(`veb` modulu ilə eyni kod). Deməli desktop tətbiqi üçün ayrı düzülüş
mühərriki yazmağa ehtiyac yoxdur: HTML-i `127.0.0.1`-dəki yerli server
verir, onu isə yerli pəncərə göstərir.

Aparıcı (pəncərəni açan) bu sıra ilə seçilir:

  1. `pywebview`  — quraşdırılıbsa həqiqi yerli pəncərə (WebKitGTK /
                    WebView2), çərçivəsiz, ayrı proses yoxdur
  2. Chrome/Edge/Chromium `--app=URL` — çərçivəsiz tətbiq pəncərəsi,
                    heç bir asılılıq tələb etmir (standart yol)
  3. Sistem brauzeri — son çarə, adi nişanda açılır
  4. Başsız        — `pəncərə.sınaq` və CI üçün; pəncərə açılmır

HADİSƏLƏR ƏSAS SAPDA İŞLƏYİR
─────────────────────────────
Brauzer `/_alqor/hadise`-yə sorğu göndərir, server sapı isə işi
növbəyə qoyub cavab gözləyir. Növbəni `pəncərə.işlət()` — yəni əsas
sap — boşaldır. Bu, iki şeyə zəmanət verir:

  • Alqor idarəedicisi həmişə eyni sapda işləyir (vəziyyət yarışı yox)
  • `dialoq.*` tkinter dialoqlarını əsas sapdan çağırır (tələbdir)

    gətir pəncərə

    funksiya əsas()
        dəyişən p = yeni pəncərə.Pəncərə("Salam", 400, 300)
        p.məzmun(<h1>Salam, dünya!</h1>)
        p.göstər()
        pəncərə.işlət()
    son
"""

from __future__ import annotations
import json as _json
import os
import queue
import shutil
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .deyerler import AlqorXəta, Element, Nümunə, mətnə, tip_adı
from .elifba import latınla

# ═══════════════════════════════════════════════════════════════════════
#  Hadisələr
# ═══════════════════════════════════════════════════════════════════════

# Alqor atributu → (DOM hadisəsi, ASCII atribut şəkilçisi)
#
# Atribut adları ASCII-dir: `data-a-deyisdi`. HTML atribut adında
# Azərbaycan hərfi işləmir — brauzerin `dataset` xəritələnməsi onları
# etibarlı çevirmir.
HADİSƏLƏR: dict[str, tuple[str, str]] = {
    "klik": ("click", "klik"),
    "ikiKlik": ("dblclick", "ikiklik"),
    "dəyişdi": ("change", "deyisdi"),
    "yazıldı": ("input", "yazildi"),
    "göndərildi": ("submit", "gonderildi"),
    "fokus": ("focusin", "fokus"),
    "fokusGetdi": ("focusout", "fokusgetdi"),
    "düyməBasma": ("keydown", "duymebasma"),
    "düyməBuraxma": ("keyup", "duymeburaxma"),
    "siçanÜstdə": ("mouseover", "sicanustde"),
    "siçanÇıxdı": ("mouseout", "sicancixdi"),
    "sürükləndi": ("dragstart", "suruklendi"),
    "buraxıldı": ("drop", "buraxildi"),
    "sürüşdü": ("scroll", "surusdu"),
    "basıldı": ("pointerdown", "basildi"),
}

# Dəyər göndərən hadisələr — idarəediciyə sahənin dəyəri ötürülür
DƏYƏRLİ = frozenset({"dəyişdi", "yazıldı"})


class Reyestr:
    """
    Hadisə idarəediciləri. Hər yenidən göstərmədə sıfırlanır — köhnə
    HTML-dən gələn id-lər etibarsızlaşır ki, silinmiş düymə basılanda
    artıq olmayan idarəedici çağırılmasın.
    """

    __slots__ = ("_cədvəl", "_sayğac", "nəsil")

    def __init__(self) -> None:
        self._cədvəl: dict[str, Any] = {}
        self._sayğac = 0
        self.nəsil = 0

    def sıfırla(self) -> None:
        self._cədvəl.clear()
        self._sayğac = 0
        self.nəsil += 1

    def yaz(self, idarəedici: Any) -> str:
        self._sayğac += 1
        açar = f"n{self.nəsil}h{self._sayğac}"
        self._cədvəl[açar] = idarəedici
        return açar

    def al(self, açar: str) -> Any:
        return self._cədvəl.get(açar)


# ═══════════════════════════════════════════════════════════════════════
#  HTML-ə çevirmə — hadisələrlə
# ═══════════════════════════════════════════════════════════════════════

TƏK_TEQLƏR = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
})

# Alqor atributu → HTML atributu
ATRIBUTLAR = {
    "sinif": "class", "üslub": "style", "kimlik": "id", "növ": "type",
    "dəyər": "value", "ad": "name", "yer": "placeholder",
    "başlıq": "title", "mənbə": "src", "ünvan": "href",
    "alternativ": "alt", "sıra": "tabindex", "söndürülmüş": "disabled",
    "oxunaqlı": "readonly", "tələb": "required", "seçilmiş": "selected",
    "işarələnmiş": "checked", "en": "width", "hündürlük": "height",
    "hədəf": "target", "rol": "role",
}

_QAÇIŞ = {"&": "&amp;", "<": "&lt;", ">": "&gt;",
          '"': "&quot;", "'": "&#39;"}


def qaç(mətn: str) -> str:
    return "".join(_QAÇIŞ.get(c, c) for c in mətn)


def HTML_ə(dəyər: Any, reyestr: Reyestr, icraçı: Any) -> str:
    """Elementi (və ya istənilən dəyəri) hadisələri bağlayaraq çevirir."""
    if dəyər is None or dəyər is False:
        return ""
    if dəyər is True:
        return "doğru"
    if isinstance(dəyər, Element):
        return _element_html(dəyər, reyestr, icraçı)
    if isinstance(dəyər, (list, tuple)):
        return "".join(HTML_ə(u, reyestr, icraçı) for u in dəyər)
    if isinstance(dəyər, str):
        return qaç(dəyər)
    return qaç(mətnə(dəyər, icraçı))


def _element_html(e: Element, reyestr: Reyestr, icraçı: Any) -> str:
    if e.ad == "":                              # parça <>…</>
        return "".join(HTML_ə(u, reyestr, icraçı) for u in e.uşaqlar)

    hissələr: list[str] = []
    for ad, d in e.atributlar.items():
        if ad in HADİSƏLƏR:
            if d is None:
                continue
            if not callable(d) and not hasattr(d, "çağır"):
                raise AlqorXəta(
                    "TipXətası",
                    f"`{ad}` atributu funksiya olmalıdır, "
                    f"`{tip_adı(d)}` gəlib", kod="ALQ-T008")
            _, şəkilçi = HADİSƏLƏR[ad]
            hissələr.append(f' data-a-{şəkilçi}="{reyestr.yaz(d)}"')
            continue
        if callable(d) or hasattr(d, "çağır"):
            continue                            # naməlum idarəedici
        html_adı = ATRIBUTLAR.get(ad, ad)
        if d is True:
            hissələr.append(f" {html_adı}")
        elif d is False or d is None:
            continue
        else:
            hissələr.append(f' {html_adı}="{qaç(mətnə(d, icraçı))}"')

    atr = "".join(hissələr)
    if e.ad in TƏK_TEQLƏR:
        return f"<{e.ad}{atr}>"
    içi = "".join(HTML_ə(u, reyestr, icraçı) for u in e.uşaqlar)
    return f"<{e.ad}{atr}>{içi}</{e.ad}>"


# ═══════════════════════════════════════════════════════════════════════
#  Menyu
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class MenyuElementi:
    ad: str = ""
    qısayol: str = ""
    klik: Any = None
    ayırıcıdır: bool = False
    söndürülmüş: bool = False
    işarələnmiş: bool | None = None


@dataclass
class Menyu:
    ad: str
    elementlər: list[MenyuElementi] = field(default_factory=list)


def _qısayolu_normallaşdır(q: str) -> str:
    """`Ctrl+Shift+S` → brauzer üçün `ctrl+shift+s`."""
    hissələr = [h.strip().lower() for h in str(q).split("+") if h.strip()]
    sıra = {"ctrl": 0, "control": 0, "cmd": 1, "meta": 1,
            "alt": 2, "shift": 3}
    dəyişdiricilər = sorted((h for h in hissələr if h in sıra),
                            key=lambda h: sıra[h])
    dəyişdiricilər = ["ctrl" if d == "control" else
                      "meta" if d == "cmd" else d
                      for d in dəyişdiricilər]
    açarlar = [h for h in hissələr if h not in sıra]
    return "+".join(dəyişdiricilər + açarlar)


def _menyu_html(menyular: list[Menyu], reyestr: Reyestr,
                icraçı: Any) -> str:
    if not menyular:
        return ""
    sətirlər: list[str] = []
    for m in menyular:
        elementlər: list[str] = []
        for e in m.elementlər:
            if e.ayırıcıdır:
                elementlər.append('<li class="ayırıcı"></li>')
                continue
            siniflər = ["element"]
            atr = ""
            if e.söndürülmüş or e.klik is None:
                siniflər.append("sönük")
            else:
                atr = (f' data-a-klik="{reyestr.yaz(e.klik)}"'
                       f' data-a-ad="{qaç(e.ad)}"')
                if e.qısayol:
                    atr += (' data-a-qisayol="'
                            f'{qaç(_qısayolu_normallaşdır(e.qısayol))}"')
            işarə = ""
            if e.işarələnmiş is not None:
                işarə = '<span class="işarə">✓</span>' \
                    if e.işarələnmiş else '<span class="işarə"></span>'
            qısa = (f'<span class="qısayol">{qaç(e.qısayol)}</span>'
                    if e.qısayol else "")
            elementlər.append(
                f'<li class="{" ".join(siniflər)}"{atr}>{işarə}'
                f'<span class="mətn">{qaç(e.ad)}</span>{qısa}</li>')
        sətirlər.append(
            f'<div class="menyu"><button class="başlıq">{qaç(m.ad)}'
            f'</button><ul class="açılan">{"".join(elementlər)}</ul></div>')
    return "".join(sətirlər)


# ═══════════════════════════════════════════════════════════════════════
#  Pəncərə
# ═══════════════════════════════════════════════════════════════════════

class Pəncərə:
    """Bir desktop pəncərəsi."""

    def __init__(self, icraçı: Any, başlıq: str = "Alqor",
                 en: int = 800, hündürlük: int = 600):
        self._icraçı = icraçı
        self._başlıq = str(başlıq)
        self._en = int(en)
        self._hündürlük = int(hündürlük)
        self._məzmun: Any = None
        self._komponent: Nümunə | None = None
        self._menyular: list[Menyu] = []
        self._reyestr = Reyestr()
        self._açıqdır = False
        self._bağlandı = threading.Event()
        self._mərkəzə = False
        self._dəyişə_bilər = True
        self._üslub = ""
        self._bağlananda: Any = None
        self._tətbiq = tətbiq(icraçı)
        self._tətbiq.qeyd_et(self)

    # ── Quraşdırma ────────────────────────────────────────────────────

    def başlıq(self, mətn: Any = None):
        """Arqumentsiz oxuyur, arqumentlə təyin edir."""
        if mətn is None:
            return self._başlıq
        self._başlıq = mətnə(mətn, self._icraçı)
        return self

    def məzmun(self, dəyər: Any) -> "Pəncərə":
        """
        Pəncərənin məzmunu. Üç formada verilə bilər:

            p.məzmun(<h1>Salam</h1>)       sabit element
            p.məzmun(<Sayğac />)           komponent — vəziyyət dəyişəndə
                                           özü yenidən göstərilir
            p.məzmun(() => <p>{x}</p>)     funksiya — hər dəfə çağırılır
            p.məzmun(menecer)              komponent NÜMUNƏSİ — menyudan
                                           `menecer.saxla()` çağırmaq üçün
        """
        self._məzmun = dəyər
        self._komponent = None
        if isinstance(dəyər, Element) and dəyər.komponent is not None:
            self._komponent = dəyər.komponent
        elif isinstance(dəyər, Nümunə):
            if dəyər.sinif.metod_tap("göstər") is None:
                raise AlqorXəta(
                    "TipXətası",
                    f"`{dəyər.sinif.ad}` komponent deyil — `göstər()` "
                    "metodu yoxdur", kod="ALQ-T053")
            self._komponent = dəyər
        return self

    def menyu(self, menyular: Any) -> "Pəncərə":
        self._menyular = [m for m in _siyahıya(menyular)
                          if isinstance(m, Menyu)]
        return self

    def üslub(self, CSS: Any) -> "Pəncərə":
        """Tətbiqə xas CSS — standart üslubdan sonra əlavə olunur."""
        self._üslub = mətnə(CSS, self._icraçı)
        return self

    def ölç(self, en: int, hündürlük: int) -> "Pəncərə":
        self._en, self._hündürlük = int(en), int(hündürlük)
        return self

    def mərkəzə(self) -> "Pəncərə":
        self._mərkəzə = True
        return self

    def ölçüsüSabit(self) -> "Pəncərə":
        self._dəyişə_bilər = False
        return self

    def bağlananda(self, idarəedici: Any) -> "Pəncərə":
        self._bağlananda = idarəedici
        return self

    # ── İdarəetmə ─────────────────────────────────────────────────────

    def göstər(self) -> "Pəncərə":
        """Pəncərəni açır. `pəncərə.işlət()` çağırılana qədər blok etmir."""
        if not self._açıqdır:
            self._açıqdır = True
            self._bağlandı.clear()
            self._tətbiq.aç(self)
        return self

    def bağla(self) -> None:
        if not self._açıqdır:
            return
        if self._bağlananda is not None:
            self._icraçı._çağır(self._bağlananda, [], {}, None)
        self._açıqdır = False
        self._bağlandı.set()
        self._tətbiq.yoxla_bitdi()

    def açıqdır(self) -> bool:
        return self._açıqdır

    def yenilə(self) -> "Pəncərə":
        """Məzmunu yenidən göstərməyə məcbur edir."""
        self._tətbiq.yenilə(self)
        return self

    def gözlə(self) -> None:
        """Pəncərə bağlanana qədər gözləyir."""
        self._bağlandı.wait()

    def ünvan(self) -> str:
        return self._tətbiq.ünvan(self)

    # ── Göstərmə ──────────────────────────────────────────────────────

    def kök_HTML(self) -> str:
        """Yalnız məzmun — hadisə cavabında bu göndərilir."""
        self._reyestr.sıfırla()
        return self._məzmunu_çevir()

    def _məzmunu_çevir(self) -> str:
        d = self._məzmun
        if self._komponent is not None:
            d = self._komponenti_göstər()
        elif callable(d) or hasattr(d, "çağır"):
            d = self._icraçı._çağır(d, [], {}, None)
        return HTML_ə(d, self._reyestr, self._icraçı)

    def _komponenti_göstər(self) -> Any:
        n = self._komponent
        assert n is not None
        göstər = n.sinif.metod_tap("göstər")
        if göstər is None:
            raise AlqorXəta(
                "TipXətası",
                f"`{n.sinif.ad}` komponentində `göstər()` metodu yoxdur",
                kod="ALQ-T053")
        # Hesablanan xassələrin keşi vəziyyət dəyişdikdən sonra köhnədir
        n._keş.clear()
        return self._icraçı.funksiya_çağır(göstər.bağla(n), [], {}, None)

    def menyu_HTML(self) -> str:
        return _menyu_html(self._menyular, self._reyestr, self._icraçı)

    def səhifə(self) -> str:
        """Tam HTML sənədi — pəncərə ilk açılanda bu yüklənir."""
        kök = self.kök_HTML()
        menyu = self.menyu_HTML()
        menyu_blok = (f'<nav id="alqor-menyu" class="menyu-sətri">{menyu}'
                      '</nav>') if menyu else \
            '<nav id="alqor-menyu" class="menyu-sətri" hidden></nav>'
        return (
            "<!DOCTYPE html>\n"
            '<html lang="az"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,'
            'initial-scale=1">'
            f"<title>{qaç(self._başlıq)}</title>"
            f"<style>{ÜSLUB}{_vidjet_üslubu()}{self._üslub}</style>"
            "</head><body>"
            f"{menyu_blok}"
            f'<main id="alqor-kök">{kök}</main>'
            f"<script>{SKRIPT}</script></body></html>")

    # ── Hadisələr ─────────────────────────────────────────────────────

    def hadisəni_işlət(self, açar: str, dəyər: Any = None) -> dict:
        """
        İdarəedicini çağırır, sonra məzmunu yenidən göstərir.
        Qaytarılan lüğət brauzerə JSON kimi gedir.
        """
        idarəedici = self._reyestr.al(açar)
        if idarəedici is None:
            # Köhnə nəsildən gələn hadisə — HTML-i yeniləyib ötürük
            return {"html": self.kök_HTML(), "menyu": self.menyu_HTML(),
                    "başlıq": self._başlıq, "köhnə": True}
        arqumentlər = [] if dəyər is None else [dəyər]
        try:
            self._icraçı._çağır(idarəedici, arqumentlər, {}, None)
        except TypeError:
            self._icraçı._çağır(idarəedici, [], {}, None)
        if not self._açıqdır:
            return {"bağlı": True}
        return {"html": self.kök_HTML(), "menyu": self.menyu_HTML(),
                "başlıq": self._başlıq}


def veb_rejimidir() -> bool:
    """`ALQOR_VEB=1` — desktop proqramı veb tətbiqi kimi işləyir
    (`alqor yerləşdir` Docker paketində qoyur)."""
    return os.environ.get("ALQOR_VEB", "").lower() in ("1", "doğru", "true")


def forma_pəncərəsi(icraçı: Any, komponent: Any, göstər: bool = True
                    ) -> Pəncərə:
    """`pəncərə.formaAç(Əsas)` — `Əsas.forma`-dakı başlıq və ölçü ilə
    pəncərə yaradır, komponenti içinə qoyur və (standart) göstərir."""
    from . import forma as F
    from .deyerler import Sinif
    if not isinstance(komponent, Sinif):
        raise AlqorXəta("TipXətası", "`formaAç` komponent gözləyir "
                        f"(məs. `formaAç(Əsas)`), {tip_adı(komponent)} "
                        "verilib", kod="ALQ-T002")
    f = F.forma_tap(komponent)
    x = f.xassələr if f is not None else {}
    if veb_rejimidir():
        # Pəncərə açılmır — `pəncərə.işlət()` veb serveri qaldırır
        t = tətbiq(icraçı)
        t.veb_formaları.append((f"/{komponent.ad}", komponent))
        p = Pəncərə(icraçı, x.get("başlıq", komponent.ad))
        t.pəncərələr.remove(p)
        return p
    p = Pəncərə(icraçı, x.get("başlıq", komponent.ad),
                x.get("en", 800), x.get("hündürlük", 600))
    if x.get("mərkəzə"):
        p.mərkəzə()
    if x.get("ölçüsüSabit"):
        p.ölçüsüSabit()
    p.məzmun(icraçı.nümunə_yarat(komponent, None, [], {}, None))
    if göstər:
        p.göstər()
    return p


def _vidjet_üslubu() -> str:
    """
    `vidjet` elementlərinin CSS-i. Hər pəncərəyə qoşulur: vidjet
    istifadə edilməsə də zərəri yoxdur (sinifləri `v-` prefikslidir),
    istifadə edildikdə isə üslubsuz düymə və sahələr görünməz.
    """
    from .vidjet import ÜSLUB as V
    return V


def _siyahıya(d: Any) -> list:
    if isinstance(d, (list, tuple)):
        return list(d)
    return [d]


# ═══════════════════════════════════════════════════════════════════════
#  Üslub və brauzer tərəfi
# ═══════════════════════════════════════════════════════════════════════

ÜSLUB = """
*{box-sizing:border-box}
:root{
 --fon:#ffffff;--mətn:#1a1a1a;--kənar:#d8d8d8;--vurgu:#0b6bcb;
 --menyu-fon:#f4f4f5;--üst:#eaeaec;--sönük:#9a9a9f
}
@media (prefers-color-scheme:dark){:root{
 --fon:#1c1c1e;--mətn:#f2f2f4;--kənar:#3a3a3d;--vurgu:#4c9ef0;
 --menyu-fon:#262629;--üst:#333336;--sönük:#79797f}}
:root[data-tema="qaranlıq"]{color-scheme:dark;
 --fon:#1c1c1e;--mətn:#f2f2f4;--kənar:#3a3a3d;--vurgu:#4c9ef0;
 --menyu-fon:#262629;--üst:#333336;--sönük:#79797f}
:root[data-tema="işıqlı"]{color-scheme:light;
 --fon:#ffffff;--mətn:#1a1a1a;--kənar:#d8d8d8;--vurgu:#0b6bcb;
 --menyu-fon:#f4f4f5;--üst:#eaeaec;--sönük:#9a9a9f}
html,body{margin:0;height:100%}
body{font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
 background:var(--fon);color:var(--mətn);
 display:flex;flex-direction:column;
 -webkit-user-select:none;user-select:none}
#alqor-kök{flex:1;padding:16px;overflow:auto}
#alqor-kök input,#alqor-kök textarea{user-select:text}
button{font:inherit;padding:6px 14px;border:1px solid var(--kənar);
 border-radius:6px;background:var(--menyu-fon);color:inherit;
 cursor:pointer}
button:hover{background:var(--üst)}
button:active{transform:translateY(1px)}
input,select,textarea{font:inherit;padding:6px 8px;
 border:1px solid var(--kənar);border-radius:6px;
 background:var(--fon);color:inherit}
/* ── Menyu sətri ── */
.menyu-sətri{display:flex;background:var(--menyu-fon);
 border-bottom:1px solid var(--kənar);flex:none;
 position:relative;z-index:10}
.menyu-sətri[hidden]{display:none}
.menyu-sətri .menyu{position:relative}
.menyu-sətri .başlıq{border:0;border-radius:0;background:none;
 padding:6px 12px}
.menyu-sətri .menyu:hover .başlıq{background:var(--üst)}
.menyu-sətri .açılan{display:none;position:absolute;left:0;top:100%;
 margin:0;padding:4px 0;min-width:200px;list-style:none;
 background:var(--menyu-fon);border:1px solid var(--kənar);
 border-radius:0 0 6px 6px;box-shadow:0 6px 18px rgba(0,0,0,.18)}
.menyu-sətri .menyu:hover .açılan{display:block}
.menyu-sətri .element{display:flex;align-items:center;gap:10px;
 padding:5px 12px;cursor:pointer;white-space:nowrap}
.menyu-sətri .element:hover{background:var(--vurgu);color:#fff}
.menyu-sətri .element.sönük{color:var(--sönük);cursor:default}
.menyu-sətri .element.sönük:hover{background:none;color:var(--sönük)}
.menyu-sətri .mətn{flex:1}
.menyu-sətri .işarə{width:1em;text-align:center}
.menyu-sətri .qısayol{color:var(--sönük);font-size:.85em}
.menyu-sətri .element:hover .qısayol{color:#e8e8e8}
.menyu-sətri .ayırıcı{height:1px;margin:4px 0;
 background:var(--kənar)}
/* ── Daxili dialoq (tkinter olmayanda) ── */
#alqor-dialoq{position:fixed;inset:0;display:flex;align-items:center;
 justify-content:center;background:rgba(0,0,0,.35);z-index:100}
#alqor-dialoq .qutu{background:var(--fon);border-radius:10px;
 padding:20px;min-width:280px;max-width:420px;
 box-shadow:0 10px 40px rgba(0,0,0,.3)}
#alqor-dialoq h3{margin:0 0 8px}
#alqor-dialoq .düymələr{display:flex;gap:8px;justify-content:flex-end;
 margin-top:16px}
#alqor-xəta{padding:16px;font-family:ui-monospace,monospace;
 white-space:pre-wrap;color:#c0392b}
"""

# ── Brauzer nüvəsi: `pəncərə` və `veb` üçün ORTAQ ──────────────────────
#
# İki problem həll olunur:
#
# 1. YAMAQ, ƏVƏZLƏMƏ YOX. Hər hadisədən sonra kökü `innerHTML` ilə
#    əvəzləmək yazılan sahənin fokusunu və dəyərini itirirdi — `yazıldı`
#    hadisəli axtarış sahəsinə "rəşad" yazmaq mümkün deyildi. `yamaq()`
#    mövcud DOM-u yeni HTML-ə uyğunlaşdırır: düyünlər yerində qalır,
#    fokusdakı sahənin dəyərinə toxunulmur, `<details>`-in açıq/qapalı
#    vəziyyəti istifadəçiyə məxsusdur.
#
# 2. NÖVBƏ, ATMA YOX. Sorğu gedərkən gələn hadisələr əvvəllər atılırdı —
#    sürətlə yazılan hərflər serverə çatmırdı. İndi növbəyə düşürlər.
#    Hadisə açarı (`data-a-*`) GÖNDƏRMƏ anında elementdən oxunur: yamaq
#    düyünü saxladığı üçün element yeni nəslin açarını daşıyır. Dəyər
#    hadisələri (`dəyişdi`, `yazıldı`) eyni element üçün birləşdirilir
#    və dəyər də göndərmə anında oxunur — server sonuncu mətni alır.
#
# `alqorBağla(göndər)` — `göndər(id, dəyər)` vəd (Promise) qaytarır.

def _nüvə_skripti() -> str:
    cədvəl = _json.dumps([list(d) for d in HADİSƏLƏR.values()],
                         separators=(",", ":"))
    dəyərli = _json.dumps({HADİSƏLƏR[a][1]: 1 for a in sorted(DƏYƏRLİ)},
                          separators=(",", ":"))
    return (f"const HADISƏLƏR={cədvəl},DƏYƏRLİ={dəyərli};" + r"""
// Göndərilməmiş dəyər hadisəsi olan sahələr: yamaq onların dəyərinə
// toxunmur — yoxsa serverin köhnə cavabı istifadəçinin yeni seçimini
// (məs. işarələnmiş qutucuğu) geri qaytarardı
const gözləyən=new Set();
function yamaq(kök,html){
 const ş=document.createElement("template");ş.innerHTML=html;
 uşaqlar(kök,ş.content);
}
function uyğundur(a,b){
 if(a.nodeType!==b.nodeType)return false;
 if(a.nodeType!==1)return true;
 return a.tagName===b.tagName&&a.getAttribute("type")===b.getAttribute("type");
}
function uşaqlar(k,y){
 const yn=Array.from(y.childNodes);
 for(let i=0;i<yn.length;i++){
  const a=k.childNodes[i],b=yn[i];
  if(!a){k.appendChild(document.importNode(b,true));continue}
  if(!uyğundur(a,b)){k.replaceChild(document.importNode(b,true),a);continue}
  if(a.nodeType===1)element(a,b);
  else if(a.data!==b.data)a.data=b.data;
 }
 while(k.childNodes.length>yn.length)k.removeChild(k.lastChild);
}
function element(a,b){
 const fokus=a===document.activeElement||gözləyən.has(a),teq=a.tagName;
 for(const at of Array.from(a.attributes))
  if(!b.hasAttribute(at.name)&&!(teq==="DETAILS"&&at.name==="open"))
   a.removeAttribute(at.name);
 for(const at of Array.from(b.attributes))
  if(a.getAttribute(at.name)!==at.value)a.setAttribute(at.name,at.value);
 if(teq==="INPUT"){
  const t=a.type;
  if(t==="checkbox"||t==="radio"){
   if(!gözləyən.has(a))a.checked=b.hasAttribute("checked")}
  else if(t!=="file"&&!fokus){
   const d=b.getAttribute("value")||"";if(a.value!==d)a.value=d}
  return;
 }
 if(teq==="TEXTAREA"){
  if(!fokus&&a.value!==b.value)a.value=b.value;return}
 uşaqlar(a,b);
 if(teq==="SELECT"&&!fokus){
  const s=b.querySelector("option[selected]");if(s)a.value=s.value}
}
function alqorBağla(göndər){
 const növbə=[];let gedir=false;
 async function boşalt(){
  if(gedir)return;gedir=true;
  try{
   while(növbə.length){
    const h=növbə.shift();
    if(DƏYƏRLİ[h.ad])gözləyən.delete(h.s);
    if(!h.t.isConnected)continue;      // element artıq yoxdur
    const id=h.t.getAttribute("data-a-"+h.ad);
    if(!id)continue;
    let d=h.d;
    if(DƏYƏRLİ[h.ad])d=h.s.type==="checkbox"?h.s.checked:h.s.value;
    try{await göndər(id,d)}catch(x){növbə.length=0;gözləyən.clear()}
   }
  }finally{gedir=false}
 }
 for(const [DOM,ad] of HADISƏLƏR){
  document.addEventListener(DOM,function(h){
   const t=h.target.closest?h.target.closest("[data-a-"+ad+"]"):null;
   if(!t)return;
   if(DOM==="click"||DOM==="submit")h.preventDefault();
   const s=h.target;
   if(DƏYƏRLİ[ad]){
    // Eyni sahə üçün gözləyən hadisə varsa, o, son dəyəri götürəcək
    if(növbə.some(x=>x.t===t&&x.ad===ad))return;
    gözləyən.add(s);
    növbə.push({t:t,ad:ad,s:s});
   }else{
    let d;
    if(DOM==="keydown"||DOM==="keyup")d=h.key;
    else{
     // Bir idarəedici bir çox düyməyə bağlı ola bilər (nişanlar,
     // səhifələmə) — hansının basıldığı `value` ilə bilinir
     const v=t.getAttribute("value");if(v!==null)d=v}
    növbə.push({t:t,ad:ad,s:s,d:d});
   }
   boşalt();
  },true);
 }
}
""")


NÜVƏ_SKRİPTİ = _nüvə_skripti()

SKRIPT = "(function(){" + NÜVƏ_SKRİPTİ + r"""
 // `?tema=qaranlıq|işıqlı` — sistem temasının əvəzinə (Studio önbaxışı)
 try{const t=new URLSearchParams(location.search).get("tema");
  if(t==="qaranlıq"||t==="işıqlı")document.documentElement.dataset.tema=t;}
 catch(e){}
 const kök=document.getElementById("alqor-kök");
 const menyu=document.getElementById("alqor-menyu");
 let bağlı=false;

 async function göndər(id,dəyər){
  if(bağlı) return;
  try{
   const c=await fetch("/_alqor/hadise",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id:id,dəyər:dəyər===undefined?null:dəyər})});
   const n=await c.json();
   if(n.xəta){kök.innerHTML='<pre id="alqor-xəta">'+n.xəta+"</pre>";return}
   if(n.bağlı){bağlı=true;window.close();
    document.body.innerHTML='<p style="padding:16px">'+
     "Pəncərə bağlandı.</p>";return}
   if(n.html!==undefined) yamaq(kök,n.html);
   if(n.menyu!==undefined&&menyu){menyu.innerHTML=n.menyu;
    menyu.hidden=!n.menyu}
   if(n.başlıq) document.title=n.başlıq;
  }catch(x){ /* server dayandı — pəncərə bağlanır */ }
 }
 alqorBağla(göndər);

 // Menyu qısayolları
 document.addEventListener("keydown",function(h){
  const hissələr=[];
  if(h.ctrlKey)hissələr.push("ctrl");
  if(h.metaKey)hissələr.push("meta");
  if(h.altKey)hissələr.push("alt");
  if(h.shiftKey)hissələr.push("shift");
  const a=h.key.toLowerCase();
  if(["control","meta","alt","shift"].includes(a)) return;
  hissələr.push(a);
  const naxış=hissələr.join("+");
  const t=document.querySelector('[data-a-qisayol="'+naxış+'"]');
  if(t){h.preventDefault();göndər(t.getAttribute("data-a-klik"))}
 });

 // Pəncərə bağlananda serveri xəbərdar et
 window.addEventListener("pagehide",function(){
  if(bağlı) return;
  navigator.sendBeacon?navigator.sendBeacon("/_alqor/baglandi"):0;
 });
})();
"""


# ═══════════════════════════════════════════════════════════════════════
#  Tətbiq — server, hadisə növbəsi, pəncərə siyahısı
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class _İş:
    """Əsas sapda icra olunacaq iş."""
    funksiya: Callable[[], Any]
    hazır: threading.Event = field(default_factory=threading.Event)
    nəticə: Any = None
    xəta: BaseException | None = None

    def işlət(self) -> None:
        try:
            self.nəticə = self.funksiya()
        except BaseException as x:              # noqa: BLE001
            self.xəta = x
        finally:
            self.hazır.set()

    def gözlə(self, müddət: float = 300.0) -> Any:
        if not self.hazır.wait(müddət):
            raise AlqorXəta("VaxtBitdiXətası",
                            "hadisə idarəedicisi cavab vermədi",
                            kod="ALQ-R014")
        if self.xəta is not None:
            raise self.xəta
        return self.nəticə


class Tətbiq:
    """
    İcraçıya bir ədəd. Serveri saxlayır, pəncərələri sayır, hadisə
    növbəsini idarə edir.
    """

    def __init__(self, icraçı: Any):
        self.icraçı = icraçı
        self.pəncərələr: list[Pəncərə] = []
        self.növbə: queue.Queue[_İş] = queue.Queue()
        self.başsız = _başsız_rejimdir()
        self.aparıcı: str = ""
        self._server: Any = None
        self._port = 0
        self._prosslər: list[subprocess.Popen] = []
        self._bitdi = threading.Event()
        self._işləyir = False
        # `dayandır()` iki sapdan gələ bilər: tətbiqin öz sapı və
        # çağıran kod. Serveri yalnız bir dəfə bağlamalıyıq.
        self._qıfıl = threading.Lock()
        # Sınaq rejimində dialoq cavabları buradan götürülür
        self.dialoq_cavabları: list[Any] = []
        self.dialoq_jurnalı: list[tuple[str, str]] = []
        # Veb rejimi (`ALQOR_VEB=1`): formalar pəncərədə yox, veb
        # serverdə açılır — hər brauzer sessiyası öz nümunəsini alır
        self.veb_formaları: list[tuple[str, Any]] = []

    # ── Pəncərələr ────────────────────────────────────────────────────

    def qeyd_et(self, p: Pəncərə) -> None:
        self.pəncərələr.append(p)

    def açıqlar(self) -> list[Pəncərə]:
        return [p for p in self.pəncərələr if p.açıqdır()]

    def aç(self, p: Pəncərə) -> None:
        if self.başsız:
            return
        self._serveri_qaldır()
        self.aparıcı = _pəncərəni_aç(self, p)

    def ünvan(self, p: Pəncərə) -> str:
        if not self._port:
            self._serveri_qaldır()
        nömrə = self.pəncərələr.index(p)
        return f"http://127.0.0.1:{self._port}/?p={nömrə}"

    def yenilə(self, p: Pəncərə) -> None:
        """
        Məzmunu yenidən göstərir. Brauzer tərəfi hadisə cavabında
        yenilənir; proqramdan çağırılanda növbəti sorğuda görünür.
        """
        p.kök_HTML()

    def yoxla_bitdi(self) -> None:
        if not self.açıqlar():
            self._bitdi.set()

    # ── Server ────────────────────────────────────────────────────────

    def _serveri_qaldır(self) -> None:
        with self._qıfıl:
            if self._server is not None:
                return
            from http.server import ThreadingHTTPServer
            self._server = ThreadingHTTPServer(
                ("127.0.0.1", 0), _İdarəedici_yarat(self))
            self._port = self._server.server_address[1]
            sap = threading.Thread(target=self._server.serve_forever,
                                   daemon=True, name="alqor-pəncərə")
            sap.start()

    def dayandır(self) -> None:
        for p in list(self.pəncərələr):
            if p.açıqdır():
                p._açıqdır = False
                p._bağlandı.set()
        for pr in self._prosslər:
            try:
                pr.terminate()
            except Exception:                   # noqa: BLE001
                pass
        self._prosslər.clear()
        # Serveri qıfılın altında ƏLDƏN alırıq: iki sap da `is not
        # None`-u keçib `server_close()`-u iki dəfə çağıra bilər.
        with self._qıfıl:
            server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()
        self._bitdi.set()

    # ── Əsas dövr ─────────────────────────────────────────────────────

    def işlət(self) -> None:
        """
        Bütün pəncərələr bağlanana qədər hadisə növbəsini boşaldır.
        Hadisələr BU sapda — əsas sapda — işləyir.
        """
        if self.veb_formaları and veb_rejimidir():
            self._veb_serveri()
            return
        if self.başsız:
            return
        if not self.açıqlar():
            return
        self._işləyir = True
        self._bitdi.clear()
        try:
            while self.açıqlar():
                try:
                    iş = self.növbə.get(timeout=0.1)
                except queue.Empty:
                    continue
                iş.işlət()
        except KeyboardInterrupt:
            pass
        finally:
            self._işləyir = False
            self.dayandır()

    def _veb_serveri(self) -> None:
        """Formaları veb serverdə verir: ilki `/`, digərləri `/Ad`."""
        from .veb import Server
        s = Server(self.icraçı)
        for i, (yol, komponent) in enumerate(self.veb_formaları):
            s.komponent("/" if i == 0 else yol, komponent)
        s.dinlə(8080, "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")

    def növbəyə(self, funksiya: Callable[[], Any]) -> Any:
        """
        Server sapından çağırılır: işi əsas sapa ötürüb nəticəni
        gözləyir. `işlət()` hələ başlamayıbsa dərhal icra edir.
        """
        if not self._işləyir or threading.current_thread() is \
                threading.main_thread():
            return funksiya()
        iş = _İş(funksiya)
        self.növbə.put(iş)
        return iş.gözlə()


def tətbiq(icraçı: Any) -> Tətbiq:
    t = getattr(icraçı, "_pəncərə_tətbiqi", None)
    if t is None:
        t = Tətbiq(icraçı)
        icraçı._pəncərə_tətbiqi = t
    return t


def _başsız_rejimdir() -> bool:
    """CI, `--başsız` və ya ekransız Linux → pəncərə açılmır."""
    if os.environ.get("ALQOR_BAŞSIZ") or os.environ.get("ALQOR_BASSIZ"):
        return True
    if "--başsız" in sys.argv or "--bassiz" in sys.argv:
        return True
    if sys.platform.startswith("linux"):
        return not (os.environ.get("DISPLAY")
                    or os.environ.get("WAYLAND_DISPLAY"))
    return False


# ═══════════════════════════════════════════════════════════════════════
#  HTTP idarəedicisi
# ═══════════════════════════════════════════════════════════════════════

def _İdarəedici_yarat(t: Tətbiq):
    from http.server import BaseHTTPRequestHandler

    class İdarəedici(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        # HTTP başlıqları latin-1 ilə kodlaşır — ASCII olmalıdır
        server_version = "Alqor-Pencere"
        sys_version = ""

        def log_message(self, *a):              # səssiz
            pass

        # ── Köməkçilər ────────────────────────────────────────────────

        def _göndər(self, gövdə: bytes, tip: str, kod: int = 200) -> None:
            self.send_response(kod)
            self.send_header("Content-Type", tip)
            self.send_header("Content-Length", str(len(gövdə)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(gövdə)

        def _JSON(self, d: dict, kod: int = 200) -> None:
            self._göndər(
                _json.dumps(d, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8", kod)

        def _pəncərə(self) -> Pəncərə | None:
            import urllib.parse as u
            sorğu = u.parse_qs(u.urlparse(self.path).query)
            nömrə = int(sorğu.get("p", ["0"])[0] or 0)
            if 0 <= nömrə < len(t.pəncərələr):
                return t.pəncərələr[nömrə]
            return t.pəncərələr[0] if t.pəncərələr else None

        # ── Marşrutlar ────────────────────────────────────────────────

        def _yol(self) -> str:
            """Faizlə kodlanmış yolu açır (brauzer qeyri-ASCII kodlayır)."""
            import urllib.parse as u
            return u.unquote(self.path.split("?")[0])

        def do_GET(self) -> None:
            yol = self._yol()
            # GET-də `Origin` olmur; yalnız `Host` yoxlanılır
            host = (self.headers.get("Host") or "").strip().lower()
            if host not in (f"127.0.0.1:{t._port}",
                            f"localhost:{t._port}"):
                self._göndər(b"forbidden", "text/plain", 403)
                return
            if yol in ("/", "/index.html"):
                p = self._pəncərə()
                if p is None:
                    self._göndər(b"pencere yoxdur", "text/plain", 404)
                    return
                try:
                    səhifə = t.növbəyə(p.səhifə)
                except BaseException as x:       # noqa: BLE001
                    səhifə = _xəta_səhifəsi(x)
                self._göndər(səhifə.encode("utf-8"),
                             "text/html; charset=utf-8")
                return
            if yol == "/_alqor/veziyyet":
                self._JSON({"pəncərələr": len(t.açıqlar())})
                return
            self._göndər(b"tapilmadi", "text/plain", 404)

        def _gövdəni_at(self) -> None:
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if 0 < n <= 1 << 20:
                self.rfile.read(n)

        def do_POST(self) -> None:
            yol = self._yol()
            if kənar_sorğudur(self.headers, t._port):
                # Gövdə oxunmadan bağlantı bağlansa Windows onu kəsir
                # (RST) və müştəri 403 cavabını ala bilmir
                self._gövdəni_at()
                self._göndər(b"forbidden", "text/plain", 403)
                return
            if yol != "/_alqor/hadise":
                self._gövdəni_at()
            p = self._pəncərə()
            if p is None:
                if yol == "/_alqor/hadise":
                    self._gövdəni_at()
                self._JSON({"bağlı": True})
                return

            if yol == "/_alqor/baglandi":
                t.növbəyə(p.bağla)
                self._JSON({"bağlı": True})
                return

            if yol != "/_alqor/hadise":
                self._göndər(b"tapilmadi", "text/plain", 404)
                return

            uzunluq = int(self.headers.get("Content-Length") or 0)
            try:
                v = _json.loads(self.rfile.read(uzunluq) or b"{}")
            except ValueError:
                v = {}
            açar = str(v.get("id") or "")
            dəyər = v.get("dəyər")

            try:
                nəticə = t.növbəyə(
                    lambda: p.hadisəni_işlət(açar, dəyər))
            except AlqorXəta as x:
                nəticə = {"xəta": _xəta_mətni(x)}
            except BaseException as x:            # noqa: BLE001
                nəticə = {"xəta": _xəta_mətni(x)}
            self._JSON(nəticə)

    return İdarəedici


def kənar_sorğudur(başlıqlar: Any, port: int | None = None) -> bool:
    """
    Sorğu başqa saytdan gəlirmi? Hadisə son nöqtələri bunu yoxlayır.

    Yerli server `127.0.0.1`-də dinləyir, amma istifadəçinin brauzerində
    açıq olan İSTƏNİLƏN sayt ora sorğu göndərə bilər. `text/plain`
    gövdəli POST "sadə sorğu"dur — CORS ön-yoxlaması olmadan çatır və
    "Sil" düyməsinin idarəedicisini işə sala bilərdi. Ona görə:

    * `Origin` başlığı varsa, `Host` ilə eyni mənbəni göstərməlidir.
      Brauzerlər POST sorğularında `Origin`-i həmişə göndərir və onu
      skript dəyişə bilmir.
    * `port` verilibsə (desktop), `Host` yalnız `127.0.0.1:port` və ya
      `localhost:port` ola bilər — DNS rebinding hücumuna qarşı: kənar
      domen bizim IP-yə yönəldilsə də `Host` başlığı o domen olaraq
      qalır.

    `Origin` olmayan sorğular (urllib, curl, sınaqlar) brauzerdən
    gəlmir — onlar CSRF vektoru deyil.
    """
    host = (başlıqlar.get("Host") or "").strip().lower()
    if port is not None:
        if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return True
    mənbə = (başlıqlar.get("Origin") or "").strip().lower()
    if not mənbə:
        return False
    if mənbə == "null":
        return True
    return mənbə not in (f"http://{host}", f"https://{host}")


def _xəta_mətni(x: BaseException) -> str:
    if isinstance(x, AlqorXəta):
        return f"{x.tip}: {x.mesaj}"
    return f"{type(x).__name__}: {x}"


def _xəta_səhifəsi(x: BaseException) -> str:
    return ("<!DOCTYPE html><html lang=\"az\"><head>"
            '<meta charset="UTF-8"><title>Xəta</title>'
            f"<style>{ÜSLUB}</style></head><body>"
            f'<pre id="alqor-xəta">{qaç(_xəta_mətni(x))}</pre>'
            "</body></html>")


# ═══════════════════════════════════════════════════════════════════════
#  Aparıcılar — pəncərəni kim açır
# ═══════════════════════════════════════════════════════════════════════

# Chrome ailəsi: `--app=URL` çərçivəsiz tətbiq pəncərəsi verir
BRAUZERLƏR = [
    ("Google Chrome", ["google-chrome", "google-chrome-stable",
                       "chrome", "chromium", "chromium-browser"]),
    ("Microsoft Edge", ["microsoft-edge", "microsoft-edge-stable",
                        "msedge"]),
    ("Brave", ["brave-browser", "brave"]),
]

PENCERE_YOLLARI = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _brauzer_tap() -> str | None:
    for _, əmrlər in BRAUZERLƏR:
        for ə in əmrlər:
            yol = shutil.which(ə)
            if yol:
                return yol
    if sys.platform == "win32":
        for yol in PENCERE_YOLLARI:
            if Path(yol).is_file():
                return yol
    if sys.platform == "darwin":
        namizəd = ("/Applications/Google Chrome.app/Contents/MacOS/"
                   "Google Chrome")
        if Path(namizəd).is_file():
            return namizəd
    return None


def _pəncərəni_aç(t: Tətbiq, p: Pəncərə) -> str:
    """Mövcud olan ən yaxşı aparıcı ilə açır, adını qaytarır."""
    ünvan = t.ünvan(p)

    # 1. pywebview — həqiqi yerli pəncərə
    try:
        import webview                          # type: ignore
    except ImportError:
        webview = None                          # type: ignore
    if webview is not None:
        def _işlət() -> None:
            webview.create_window(
                p._başlıq, ünvan, width=p._en, height=p._hündürlük,
                resizable=p._dəyişə_bilər)
            webview.start()
        threading.Thread(target=_işlət, daemon=True,
                         name="alqor-webview").start()
        return "pywebview"

    # 2. Chrome ailəsi `--app=` rejimi
    brauzer = _brauzer_tap()
    if brauzer:
        profil = Path(_müvəqqəti_qovluq()) / "brauzer-profili"
        əmr = [brauzer, f"--app={ünvan}",
               f"--window-size={p._en},{p._hündürlük}",
               f"--user-data-dir={profil}",
               "--no-first-run", "--no-default-browser-check",
               "--disable-features=TranslateUI",
               "--disable-background-networking"]
        try:
            pr = subprocess.Popen(
                əmr, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            t._prosslər.append(pr)
            return "brauzer-tətbiq"
        except OSError:
            pass

    # 3. Sistem brauzeri — son çarə
    webbrowser.open(ünvan)
    return "brauzer"


def _müvəqqəti_qovluq() -> str:
    import tempfile
    q = Path(tempfile.gettempdir()) / "alqor-pəncərə"
    q.mkdir(parents=True, exist_ok=True)
    return str(q)


# ═══════════════════════════════════════════════════════════════════════
#  Dialoqlar
# ═══════════════════════════════════════════════════════════════════════

class _Tk:
    """
    tkinter kök pəncərəsi — yalnız lazım olanda yaradılır və gizli
    qalır. tkinter yoxdursa (`python3-tk` quraşdırılmayıb) `None`.
    """

    _kök: Any = None
    _mümkündür: bool | None = None

    @classmethod
    def mümkündür(cls) -> bool:
        if cls._mümkündür is None:
            try:
                import tkinter                  # noqa: F401
                cls._mümkündür = not _başsız_rejimdir()
            except ImportError:
                cls._mümkündür = False
        return bool(cls._mümkündür)

    @classmethod
    def kök(cls) -> Any:
        import tkinter
        if cls._kök is None or not cls._kök.winfo_exists():
            cls._kök = tkinter.Tk()
            cls._kök.withdraw()
            # Dialoqlar brauzer pəncərəsinin üstündə görünsün
            cls._kök.attributes("-topmost", True)
        return cls._kök


def _cavab_götür(t: Tətbiq, növ: str, mesaj: str, standart: Any) -> Any:
    """
    Sınaq/başsız rejimdə dialoq cavabı: `pəncərə.sınaq.cavablar([...])`
    ilə əvvəlcədən verilənlər növbəsindən, yoxsa standart dəyər.
    """
    t.dialoq_jurnalı.append((növ, mesaj))
    if t.dialoq_cavabları:
        return t.dialoq_cavabları.pop(0)
    return standart


def d_təsdiqlə(icraçı: Any, başlıq: Any, mesaj: Any = "") -> bool:
    t = tətbiq(icraçı)
    b, m = mətnə(başlıq, icraçı), mətnə(mesaj, icraçı)
    if not _Tk.mümkündür():
        return bool(_cavab_götür(t, "təsdiqlə", f"{b} {m}".strip(), False))
    from tkinter import messagebox
    t.dialoq_jurnalı.append(("təsdiqlə", f"{b} {m}".strip()))
    return bool(messagebox.askyesno(b, m or b, parent=_Tk.kök()))


def d_xəbərdarlıq(icraçı: Any, başlıq: Any, mesaj: Any = "") -> None:
    t = tətbiq(icraçı)
    b, m = mətnə(başlıq, icraçı), mətnə(mesaj, icraçı)
    if not _Tk.mümkündür():
        _cavab_götür(t, "xəbərdarlıq", f"{b} {m}".strip(), None)
        return
    from tkinter import messagebox
    t.dialoq_jurnalı.append(("xəbərdarlıq", f"{b} {m}".strip()))
    messagebox.showwarning(b, m or b, parent=_Tk.kök())


def d_məlumat(icraçı: Any, başlıq: Any, mesaj: Any = "") -> None:
    t = tətbiq(icraçı)
    b, m = mətnə(başlıq, icraçı), mətnə(mesaj, icraçı)
    if not _Tk.mümkündür():
        _cavab_götür(t, "məlumat", f"{b} {m}".strip(), None)
        return
    from tkinter import messagebox
    t.dialoq_jurnalı.append(("məlumat", f"{b} {m}".strip()))
    messagebox.showinfo(b, m or b, parent=_Tk.kök())


def d_xəta(icraçı: Any, başlıq: Any, mesaj: Any = "") -> None:
    t = tətbiq(icraçı)
    b, m = mətnə(başlıq, icraçı), mətnə(mesaj, icraçı)
    if not _Tk.mümkündür():
        _cavab_götür(t, "xəta", f"{b} {m}".strip(), None)
        return
    from tkinter import messagebox
    t.dialoq_jurnalı.append(("xəta", f"{b} {m}".strip()))
    messagebox.showerror(b, m or b, parent=_Tk.kök())


def d_soruş(icraçı: Any, başlıq: Any, mesaj: Any = "",
            standart: Any = "") -> str | None:
    t = tətbiq(icraçı)
    b, m = mətnə(başlıq, icraçı), mətnə(mesaj, icraçı)
    s = mətnə(standart, icraçı) if standart is not None else ""
    if not _Tk.mümkündür():
        return _cavab_götür(t, "soruş", f"{b} {m}".strip(), None)
    from tkinter import simpledialog
    t.dialoq_jurnalı.append(("soruş", f"{b} {m}".strip()))
    return simpledialog.askstring(b, m or b, initialvalue=s,
                                  parent=_Tk.kök())


def _süzgəcləri_çevir(süzgəclər: Any, icraçı: Any) -> list[tuple[str, str]]:
    """
    Alqor formatı → tkinter formatı.

        {"Mətn faylı": "*.txt", "Şəkil": ["*.png", "*.jpg"]}
        [["Mətn faylı", "*.txt"]]
    """
    if süzgəclər is None:
        return [("Bütün fayllar", "*.*")]
    cüt: list[tuple[str, str]] = []
    if isinstance(süzgəclər, dict):
        sıra = süzgəclər.items()
    elif isinstance(süzgəclər, (list, tuple)):
        sıra = [(s[0], s[1]) if isinstance(s, (list, tuple)) and len(s) > 1
                else (str(s), str(s)) for s in süzgəclər]
    else:
        return [("Bütün fayllar", "*.*")]
    for ad, naxış in sıra:
        if isinstance(naxış, (list, tuple)):
            naxış = " ".join(str(n) for n in naxış)
        cüt.append((mətnə(ad, icraçı), str(naxış)))
    return cüt or [("Bütün fayllar", "*.*")]


def d_faylAç(icraçı: Any, süzgəclər: Any = None,
             qovluq: Any = None) -> str | None:
    t = tətbiq(icraçı)
    if not _Tk.mümkündür():
        return _cavab_götür(t, "faylAç", "", None)
    from tkinter import filedialog
    t.dialoq_jurnalı.append(("faylAç", ""))
    nəticə = filedialog.askopenfilename(
        parent=_Tk.kök(),
        filetypes=_süzgəcləri_çevir(süzgəclər, icraçı),
        initialdir=mətnə(qovluq, icraçı) if qovluq else None)
    return nəticə or None


def d_faylAçHamısı(icraçı: Any, süzgəclər: Any = None,
                   qovluq: Any = None) -> list[str]:
    t = tətbiq(icraçı)
    if not _Tk.mümkündür():
        cavab = _cavab_götür(t, "faylAçHamısı", "", [])
        return list(cavab) if isinstance(cavab, (list, tuple)) else []
    from tkinter import filedialog
    t.dialoq_jurnalı.append(("faylAçHamısı", ""))
    return list(filedialog.askopenfilenames(
        parent=_Tk.kök(),
        filetypes=_süzgəcləri_çevir(süzgəclər, icraçı),
        initialdir=mətnə(qovluq, icraçı) if qovluq else None))


def d_faylSaxla(icraçı: Any, standartAd: Any = "",
                süzgəclər: Any = None, qovluq: Any = None) -> str | None:
    t = tətbiq(icraçı)
    ad = mətnə(standartAd, icraçı) if standartAd else ""
    if not _Tk.mümkündür():
        return _cavab_götür(t, "faylSaxla", ad, None)
    from tkinter import filedialog
    t.dialoq_jurnalı.append(("faylSaxla", ad))
    uzantı = Path(ad).suffix
    nəticə = filedialog.asksaveasfilename(
        parent=_Tk.kök(), initialfile=ad or None,
        defaultextension=uzantı or None,
        filetypes=_süzgəcləri_çevir(süzgəclər, icraçı),
        initialdir=mətnə(qovluq, icraçı) if qovluq else None)
    return nəticə or None


def d_qovluqSeç(icraçı: Any, qovluq: Any = None) -> str | None:
    t = tətbiq(icraçı)
    if not _Tk.mümkündür():
        return _cavab_götür(t, "qovluqSeç", "", None)
    from tkinter import filedialog
    t.dialoq_jurnalı.append(("qovluqSeç", ""))
    nəticə = filedialog.askdirectory(
        parent=_Tk.kök(),
        initialdir=mətnə(qovluq, icraçı) if qovluq else None)
    return nəticə or None


def d_rəngSeç(icraçı: Any, standart: Any = "#3366cc") -> str | None:
    t = tətbiq(icraçı)
    s = mətnə(standart, icraçı) if standart else "#3366cc"
    if not _Tk.mümkündür():
        return _cavab_götür(t, "rəngSeç", s, None)
    from tkinter import colorchooser
    t.dialoq_jurnalı.append(("rəngSeç", s))
    nəticə = colorchooser.askcolor(color=s, parent=_Tk.kök())
    return nəticə[1] if nəticə and nəticə[1] else None


# ═══════════════════════════════════════════════════════════════════════
#  Bildiriş
# ═══════════════════════════════════════════════════════════════════════

def bildiriş(icraçı: Any, başlıq: Any, mesaj: Any = "") -> None:
    """
    Sistem bildirişi. Linux-da `notify-send`, macOS-da AppleScript,
    Windows-da PowerShell toast; heç biri yoxdursa dialoq pəncərəsi.
    """
    t = tətbiq(icraçı)
    b, m = mətnə(başlıq, icraçı), mətnə(mesaj, icraçı)
    t.dialoq_jurnalı.append(("bildiriş", f"{b} {m}".strip()))
    if t.başsız:
        return

    try:
        if sys.platform.startswith("linux") and shutil.which("notify-send"):
            subprocess.run(["notify-send", b, m], check=False,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
            return
        if sys.platform == "darwin":
            skript = (f'display notification "{m}" '
                      f'with title "{b}"')
            subprocess.run(["osascript", "-e", skript], check=False,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
            return
        if sys.platform == "win32":
            if _windows_toast(b, m):
                return
    except (OSError, subprocess.SubprocessError):
        pass

    if _Tk.mümkündür():
        from tkinter import messagebox
        messagebox.showinfo(b, m or b, parent=_Tk.kök())


def _windows_toast(başlıq: str, mesaj: str) -> bool:
    ps = (
        "[Windows.UI.Notifications.ToastNotificationManager,"
        "Windows.UI.Notifications,ContentType=WindowsRuntime]"
        "|Out-Null;"
        "$x=[Windows.UI.Notifications.ToastNotificationManager]::"
        "GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        f"$t=$x.GetElementsByTagName('text');"
        f"$t[0].AppendChild($x.CreateTextNode({_ps_mətn(başlıq)}))"
        "|Out-Null;"
        f"$t[1].AppendChild($x.CreateTextNode({_ps_mətn(mesaj)}))"
        "|Out-Null;"
        "[Windows.UI.Notifications.ToastNotificationManager]::"
        "CreateToastNotifier('Alqor').Show("
        "[Windows.UI.Notifications.ToastNotification]::new($x))"
    )
    try:
        nəticə = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-Command", ps],
            check=False, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=10)
        return nəticə.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _ps_mətn(m: str) -> str:
    return "'" + m.replace("'", "''") + "'"


# ═══════════════════════════════════════════════════════════════════════
#  Sınaq sürücüsü — pəncərə açmadan
# ═══════════════════════════════════════════════════════════════════════

class Sürücü:
    """
    Pəncərəni başsız idarə edir: HTML-i oxuyur, düymələri basır.
    `06-desktop.alq -- sınaq` və avtomatik sınaqlar bunu işlədir.

        dəyişən s = pəncərə.sınaq.aç(p)
        s.klik("+")
        yaz(s.mətn())
    """

    def __init__(self, icraçı: Any, p: Pəncərə):
        self.i = icraçı
        self.p = p
        if not p.açıqdır():
            p._açıqdır = True
        self._HTML = ""
        self.yenilə()

    # ── Oxuma ─────────────────────────────────────────────────────────

    def yenilə(self) -> "Sürücü":
        self._HTML = self.p.kök_HTML()
        return self

    def HTML(self) -> str:
        return self._HTML

    def səhifə(self) -> str:
        return self.p.səhifə()

    def menyu(self) -> str:
        return self.p.menyu_HTML()

    def başlıq(self) -> str:
        return self.p._başlıq

    def mətn(self) -> str:
        """Teqləri silib yalnız mətni qaytarır."""
        return _teqsiz(self._HTML)

    def ehtiva(self, parça: Any) -> bool:
        return mətnə(parça, self.i) in self._HTML

    def açıqdır(self) -> bool:
        return self.p.açıqdır()

    def dialoqlar(self) -> list:
        return [list(d) for d in tətbiq(self.i).dialoq_jurnalı]

    # ── Hadisələr ─────────────────────────────────────────────────────

    def klik(self, nişan: Any = None, dəyər: Any = None) -> "Sürücü":
        """
        Düyməni basır. `nişan` — düymənin mətni, `kimlik` dəyəri və ya
        menyu elementinin adı. Verilməsə ilk klik idarəedicisi işləyir.
        """
        hədəf = mətnə(nişan, self.i) if nişan is not None else None
        açar = self._açar_tap("klik", hədəf)
        if açar is None:
            açar = self._menyuda_tap(hədəf)
        if açar is not None and dəyər is None:
            # Elementin `value` atributu idarəediciyə ötürülür
            dəyər = _teq_atributu(
                _teqi_tap(self._HTML + self.p.menyu_HTML(),
                          "data-a-klik", açar), "value") or None
        if açar is None:
            # Qeyd qutusu və açar: brauzerdə klik `change` doğurur
            açar, çevrilmiş = self._qeydi_tap(hədəf)
            if açar is not None and dəyər is None:
                dəyər = çevrilmiş
        if açar is None:
            raise AlqorXəta(
                "ArqumentXətası",
                f'"{hədəf}" üçün klik idarəedicisi tapılmadı'
                if hədəf else "klik idarəedicisi yoxdur",
                kod="ALQ-R013")
        self._işlət(açar, dəyər)
        return self

    def yaz(self, nişan: Any, dəyər: Any) -> "Sürücü":
        """Sahəyə dəyər yazır (`dəyişdi` hadisəsi)."""
        hədəf = mətnə(nişan, self.i)
        açar = self._açar_tap("deyisdi", hədəf) \
            or self._açar_tap("yazildi", hədəf)
        if açar is None:
            raise AlqorXəta(
                "ArqumentXətası",
                f'"{hədəf}" sahəsi tapılmadı', kod="ALQ-R013")
        # Brauzer kimi: qutucuq/açar `məntiq`, qalan sahələr mətn göndərir
        self._işlət(açar, dəyər if isinstance(dəyər, bool)
                    else mətnə(dəyər, self.i))
        return self

    def hadisə(self, ad: Any, nişan: Any = None,
               dəyər: Any = None) -> "Sürücü":
        """İstənilən hadisəni göndərir: `s.hadisə("ikiKlik", "Sil")`."""
        alqor_adı = mətnə(ad, self.i)
        if alqor_adı not in HADİSƏLƏR:
            raise AlqorXəta(
                "ArqumentXətası",
                f"`{alqor_adı}` hadisəsi yoxdur. İcazəli: "
                f"{', '.join(sorted(HADİSƏLƏR))}", kod="ALQ-R013")
        _, şəkilçi = HADİSƏLƏR[alqor_adı]
        hədəf = mətnə(nişan, self.i) if nişan is not None else None
        açar = self._açar_tap(şəkilçi, hədəf)
        if açar is None:
            raise AlqorXəta(
                "ArqumentXətası",
                f"`{alqor_adı}` idarəedicisi tapılmadı", kod="ALQ-R013")
        self._işlət(açar, dəyər)
        return self

    def bağla(self) -> "Sürücü":
        self.p.bağla()
        return self

    # ── Daxili ────────────────────────────────────────────────────────

    def _işlət(self, açar: str, dəyər: Any) -> None:
        self.p.hadisəni_işlət(açar, dəyər)
        self._HTML = self.p.kök_HTML()

    def _açar_tap(self, şəkilçi: str, hədəf: str | None) -> str | None:
        """HTML-dən `data-a-<şəkilçi>` atributunu tapır."""
        for HTML in (self._HTML, self.p.menyu_HTML()):
            açar = _atribut_tap(HTML, f"data-a-{şəkilçi}", hədəf)
            if açar:
                return açar
        return None

    def _menyuda_tap(self, hədəf: str | None) -> str | None:
        if hədəf is None:
            return None
        return _atribut_tap(self.p.menyu_HTML(), "data-a-klik", hədəf)

    def _qeydi_tap(self, hədəf: str | None) -> tuple[str | None, Any]:
        """
        `dəyişdi` idarəedicisi olan qeyd qutusunu tapır və klikdən
        sonrakı dəyərini hesablayır (işarəli ↔ işarəsiz).
        """
        for şəkilçi in ("deyisdi", "yazildi"):
            açar = self._açar_tap(şəkilçi, hədəf)
            if açar is None:
                continue
            teq = _teqi_tap(self._HTML, f"data-a-{şəkilçi}", açar)
            if 'type="checkbox"' in teq or 'type="radio"' in teq:
                return açar, " checked" not in teq
            return açar, None
        return None, None


def _teqsiz(HTML: str) -> str:
    """Teqləri atır, mətni boşluqla ayırır."""
    nəticə: list[str] = []
    teqdə = False
    for c in HTML:
        if c == "<":
            teqdə = True
            nəticə.append(" ")
        elif c == ">":
            teqdə = False
        elif not teqdə:
            nəticə.append(c)
    mətn = "".join(nəticə)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                 ("&#39;", "'"), ("&amp;", "&")):
        mətn = mətn.replace(a, b)
    return " ".join(mətn.split())


def _atribut_tap(HTML: str, atribut: str,
                 hədəf: str | None) -> str | None:
    """
    `atribut` daşıyan teqləri gəzir. `hədəf` verilibsə teqin mətni,
    `id`-si və ya `title`-ı ilə uyğunluq axtarır.
    """
    naxış = f'{atribut}="'
    yer = 0
    ilk: str | None = None
    # İkinci dərəcəli uyğunluq: mətni hədəflə BAŞLAYAN element (cədvəl
    # sətri "Süd al  bitib"). Yalnız dəqiq uyğunluq tapılmasa işlənir —
    # "Sil" "Bitmişləri sil" düyməsini deyil, "Sil"-i tapsın.
    başlanğıc: str | None = None
    while True:
        i = HTML.find(naxış, yer)
        if i < 0:
            break
        baş = i + len(naxış)
        son = HTML.find('"', baş)
        açar = HTML[baş:son]
        yer = son
        if ilk is None:
            ilk = açar
        if hədəf is None:
            return açar
        teq_başı = HTML.rfind("<", 0, i)
        teq_sonu = HTML.find(">", son)
        if teq_başı < 0 or teq_sonu < 0:
            continue
        teq = HTML[teq_başı:teq_sonu + 1]
        # Teqin daxilindəki mətn
        ad = teq[1:].split(" ", 1)[0].split(">")[0]
        bağlayıcı = f"</{ad}>"
        mətn_sonu = HTML.find(bağlayıcı, teq_sonu)
        içi = HTML[teq_sonu + 1:mətn_sonu] if mətn_sonu > 0 else ""
        mətn = _teqsiz(içi)
        if _uyğundur(hədəf, mətn):
            return açar
        # Menyu adı, kimlik, başlıq, sahə adı və dəyəri də nişan sayılır
        for atr_adı in ("data-a-ad", "id", "title", "name", "value"):
            if _uyğundur(hədəf, _teq_atributu(teq, atr_adı)):
                return açar
        if başlanğıc is None and _başlayır(mətn, hədəf):
            başlanğıc = açar
    return başlanğıc


def _başlayır(mətn: str, hədəf: str) -> bool:
    """Söz sərhədində: "Süd al bitib" "Süd al" ilə başlayır, "Südlü" yox."""
    if not mətn or not hədəf:
        return False
    for m, h in ((mətn, hədəf),
                 (latınla(mətn).lower(), latınla(hədəf).lower())):
        if m.startswith(h) and (len(m) == len(h) or m[len(h)] == " "):
            return True
    return False


def _teqi_tap(HTML: str, atribut: str, açar: str) -> str:
    """Verilmiş açarı daşıyan teqin mətnini qaytarır."""
    i = HTML.find(f'{atribut}="{açar}"')
    if i < 0:
        return ""
    baş = HTML.rfind("<", 0, i)
    son = HTML.find(">", i)
    return HTML[baş:son + 1] if baş >= 0 and son > 0 else ""


def _uyğundur(hədəf: str, mətn: str) -> bool:
    if not mətn:
        return False
    if hədəf == mətn:
        return True
    # ASCII yazılış da qəbul olunur: "Sifirla" → "Sıfırla"
    return latınla(hədəf).lower() == latınla(mətn).lower()


def _teq_atributu(teq: str, ad: str) -> str:
    naxış = f'{ad}="'
    i = teq.find(" " + naxış)
    if i < 0:
        return ""
    baş = i + len(naxış) + 1
    son = teq.find('"', baş)
    return teq[baş:son] if son > 0 else ""
