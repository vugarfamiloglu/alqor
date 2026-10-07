"""
Alqor — `vidjet` modulunun əlavə elementləri (§ 14).

`vidjet.py`-dəki əsas 57 elementə əlavə: daha zəngin form sahələri,
qrafiklər, təqvim, karusel, vaxt xətti, qiymət kartı və s. Hamısı eyni
qaydalarla işləyir — `Element` qaytarır, həm vebdə, həm desktopda
görünür, `üslub:` qəbul edir, Alqor Studio paletində miniatürü var.

Bu fayl `vidjet.py` tərəfindən kataloq qurulmazdan əvvəl idxal olunur
(`ƏLAVƏLƏR`, `ƏLAVƏ_KATALOQ`, `ƏLAVƏ_ÜSLUB`); köməkçilər oradan gəlir.
"""

from __future__ import annotations

import calendar
import math
from typing import Any

from .deyerler import AlqorXəta, Element
from .vidjet import (DÜZÜLÜŞ, FORM, GÖSTƏRMƏ, NAVİQASİYA, NÖVLƏR, P,
                     VƏZİYYƏT, ÜST_QAT, Məlumat, _E, _giriş, _m,
                     _növü_yoxla, _sahə_çərçivəsi, _say, _seçimlər,
                     _sətirlər, _sinif, _ölçü, _uşaqlar)

_AYLAR = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "İyun", "İyul",
          "Avqust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"]
_GÜNLƏR = ["B.e", "Ç.a", "Ç", "C.a", "C", "Ş", "B"]


def _url(d: Any, icraçı: Any, şəkil: bool = False) -> str:
    """Yalnız http(s), nisbi yollar (və şəkil üçün data:image)."""
    u = _m(d, icraçı).strip()
    kiçik = u.lower().replace("\t", "").replace("\n", "")
    if kiçik.startswith(("javascript:", "vbscript:")) or (
            kiçik.startswith("data:") and not (
                şəkil and kiçik.startswith("data:image/"))):
        raise AlqorXəta("ArqumentXətası", f"icazəsiz ünvan: {u[:40]!r}",
                        kod="ALQ-R013")
    return u


def _ədəd_siyahısı(d: Any) -> list[float]:
    if d is None:
        return []
    if isinstance(d, (list, tuple)):
        return [_say(x) for x in d]
    return [_say(d)]


# ═══════════════════════════════════════════════════════════════════════
#  Form
# ═══════════════════════════════════════════════════════════════════════

def reytinq(icraçı, dəyər: Any = 0, maksimum: Any = 5, klik: Any = None,
            etiket: Any = None, söndürülmüş: Any = False) -> Element:
    d = int(_say(dəyər))
    n = max(1, min(10, int(_say(maksimum, 5))))
    ulduzlar = [_E("button", {
        "class": _sinif(f"{P}ulduz", f"{P}ulduz--dolu" if i <= d else None),
        "type": "button", "value": str(i), "title": f"{i} / {n}",
        "disabled": True if söndürülmüş else None,
        "klik": None if söndürülmüş else klik,
    }, "★") for i in range(1, n + 1)]
    kök = _E("div", {"class": f"{P}reytinq", "role": "radiogroup"},
             ulduzlar)
    if etiket is not None:
        return _E("div", {"class": f"{P}sahə"}, [
            _E("label", {"class": f"{P}etiket"}, _m(etiket, icraçı)), kök])
    return kök


def seqmentli(icraçı, seçimlər: Any = None, dəyər: Any = None,
              klik: Any = None) -> Element:
    cütlər = _seçimlər(seçimlər, icraçı)
    seçili = _m(dəyər, icraçı) if dəyər is not None else (
        cütlər[0][0] if cütlər else "")
    return _E("div", {"class": f"{P}seqmentli", "role": "radiogroup"}, [
        _E("button", {
            "class": _sinif(f"{P}seqment",
                            f"{P}seqment--seçili" if d == seçili else None),
            "type": "button", "value": d, "klik": klik,
            "aria-pressed": "true" if d == seçili else "false",
        }, e) for d, e in cütlər])


def çipSeçimi(icraçı, seçimlər: Any = None, seçilənlər: Any = None,
              klik: Any = None) -> Element:
    seçili = set(_sətirlər(seçilənlər, icraçı))
    return _E("div", {"class": f"{P}çiplər"}, [
        _E("button", {
            "class": _sinif(f"{P}çip", f"{P}çip--seçili" if d in seçili
                            else None),
            "type": "button", "value": d, "klik": klik,
            "aria-pressed": "true" if d in seçili else "false",
        }, ["✓ " if d in seçili else "", e])
        for d, e in _seçimlər(seçimlər, icraçı)])


def teqSahəsi(icraçı, etiket: Any = None, teqlər: Any = None,
              əlavəEdildi: Any = None, silindi: Any = None,
              yer: Any = "Yazın və Enter basın") -> Element:
    çiplər = [_E("span", {"class": f"{P}çip"}, [
        t, _E("button", {"class": f"{P}çip-sil", "type": "button",
                         "value": t, "title": "Sil", "klik": silindi},
              "✕") if silindi is not None else None])
        for t in _sətirlər(teqlər, icraçı)]
    giriş = _E("input", {"class": f"{P}teq-girişi", "type": "text",
                         "placeholder": _m(yer, icraçı) or None,
                         "dəyişdi": əlavəEdildi})
    return _sahə_çərçivəsi(icraçı, _E("div", {"class": f"{P}teq-sahəsi"},
                                      çiplər + [giriş]),
                           etiket, None, None, None, False)


def təsdiqKodu(icraçı, etiket: Any = None, uzunluq: Any = 6,
               dəyər: Any = None, dəyişdi: Any = None) -> Element:
    n = max(1, min(12, int(_say(uzunluq, 6))))
    giriş = _E("input", {
        "class": _sinif(f"{P}giriş", f"{P}kod-girişi"), "type": "text",
        "inputmode": "numeric", "autocomplete": "one-time-code",
        "maxlength": str(n), "pattern": "[0-9]*",
        "placeholder": "•" * n, "value": _m(dəyər, icraçı) or None,
        "style": f"--uzunluq:{n}", "dəyişdi": dəyişdi})
    return _sahə_çərçivəsi(icraçı, giriş, etiket, None, None, None, False)


def _əlavəli(icraçı, giriş: Element, ön: str | None,
             son: str | None) -> Element:
    return _E("div", {"class": f"{P}giriş-qrupu"}, [
        _E("span", {"class": f"{P}giriş-əlavəsi"}, ön) if ön else None,
        giriş,
        _E("span", {"class": f"{P}giriş-əlavəsi"}, son) if son else None,
    ])


def telefon(icraçı, etiket: Any = None, ad: Any = "telefon",
            dəyər: Any = None, ölkəKodu: Any = "+994",
            dəyişdi: Any = None, kömək: Any = None, xəta: Any = None,
            tələb: Any = False) -> Element:
    g = _giriş(icraçı, "tel", ad, dəyər, "50 123 45 67", dəyişdi, None,
               False, False, tələb, xəta, {"autocomplete": "tel"})
    return _sahə_çərçivəsi(icraçı, _əlavəli(icraçı, g, _m(ölkəKodu, icraçı),
                                            None),
                           etiket, ad, kömək, xəta, tələb)


def ePoçt(icraçı, etiket: Any = None, ad: Any = "epoçt", dəyər: Any = None,
          yer: Any = "ad@nümunə.az", dəyişdi: Any = None,
          kömək: Any = None, xəta: Any = None,
          tələb: Any = False) -> Element:
    g = _giriş(icraçı, "email", ad, dəyər, yer, dəyişdi, None, False,
               False, tələb, xəta, {"autocomplete": "email"})
    return _sahə_çərçivəsi(icraçı, g, etiket, ad, kömək, xəta, tələb)


def keçidSahəsi(icraçı, etiket: Any = None, ad: Any = "ünvan",
                dəyər: Any = None, yer: Any = "https://",
                dəyişdi: Any = None, kömək: Any = None,
                xəta: Any = None) -> Element:
    g = _giriş(icraçı, "url", ad, dəyər, yer, dəyişdi, None, False, False,
               False, xəta)
    return _sahə_çərçivəsi(icraçı, g, etiket, ad, kömək, xəta, False)


def pulSahəsi(icraçı, etiket: Any = None, ad: Any = "məbləğ",
              dəyər: Any = None, valyuta: Any = "₼", dəyişdi: Any = None,
              kömək: Any = None, xəta: Any = None) -> Element:
    g = _giriş(icraçı, "number", ad, dəyər, "0.00", dəyişdi, None, False,
               False, False, xəta, {"step": "0.01", "min": "0",
                                    "inputmode": "decimal"})
    return _sahə_çərçivəsi(icraçı, _əlavəli(icraçı, g, None,
                                            _m(valyuta, icraçı)),
                           etiket, ad, kömək, xəta, False)


def tarixAralığı(icraçı, etiket: Any = None, başlanğıc: Any = None,
                 bitmə: Any = None, başlanğıcDəyişdi: Any = None,
                 bitməDəyişdi: Any = None) -> Element:
    def g(d, f, ad):
        return _E("input", {"class": f"{P}giriş", "type": "date",
                            "value": _m(d, icraçı) or None,
                            "aria-label": ad, "dəyişdi": f})
    return _sahə_çərçivəsi(icraçı, _E("div", {"class": f"{P}aralıq"}, [
        g(başlanğıc, başlanğıcDəyişdi, "başlanğıc"),
        _E("span", {"class": f"{P}aralıq-ayırıcı"}, "—"),
        g(bitmə, bitməDəyişdi, "bitmə")]), etiket, None, None, None, False)


def tarixVaxt(icraçı, etiket: Any = None, ad: Any = "tarixVaxt",
              dəyər: Any = None, dəyişdi: Any = None) -> Element:
    g = _giriş(icraçı, "datetime-local", ad, dəyər, None, dəyişdi, None,
               False, False, False, None)
    return _sahə_çərçivəsi(icraçı, g, etiket, ad, None, None, False)


def ay(icraçı, etiket: Any = None, ad: Any = "ay", dəyər: Any = None,
       dəyişdi: Any = None) -> Element:
    g = _giriş(icraçı, "month", ad, dəyər, None, dəyişdi, None, False,
               False, False, None)
    return _sahə_çərçivəsi(icraçı, g, etiket, ad, None, None, False)


def sayğac(icraçı, etiket: Any = None, dəyər: Any = 0, minimum: Any = 0,
           maksimum: Any = 99, pillə: Any = 1,
           klik: Any = None) -> Element:
    d, mn, mx, p = (_say(dəyər), _say(minimum), _say(maksimum, 99),
                    _say(pillə, 1) or 1)

    def f(x: float) -> str:
        return str(int(x)) if float(x).is_integer() else f"{x:g}"
    azalt, artır = max(mn, d - p), min(mx, d + p)
    return _sahə_çərçivəsi(icraçı, _E("div", {"class": f"{P}sayğac"}, [
        _E("button", {"class": f"{P}sayğac-düyməsi", "type": "button",
                      "value": f(azalt), "title": "Azalt",
                      "disabled": True if d <= mn else None,
                      "klik": None if d <= mn else klik}, "−"),
        _E("output", {"class": f"{P}sayğac-dəyəri"}, f(d)),
        _E("button", {"class": f"{P}sayğac-düyməsi", "type": "button",
                      "value": f(artır), "title": "Artır",
                      "disabled": True if d >= mx else None,
                      "klik": None if d >= mx else klik}, "+"),
    ]), etiket, None, None, None, False)


_SİYAHI_SAYĞACI = [0]


def avtoTamamlama(icraçı, etiket: Any = None, ad: Any = "seçim",
                  təkliflər: Any = None, dəyər: Any = None,
                  yer: Any = None, dəyişdi: Any = None,
                  yazıldı: Any = None) -> Element:
    _SİYAHI_SAYĞACI[0] += 1
    kimlik = f"{P}təkliflər-{_SİYAHI_SAYĞACI[0]}"
    g = _giriş(icraçı, "text", ad, dəyər, yer, dəyişdi, yazıldı, False,
               False, False, None, {"list": kimlik, "autocomplete": "off"})
    siyahı = _E("datalist", {"id": kimlik}, [
        _E("option", {"value": t}) for t in _sətirlər(təkliflər, icraçı)])
    return _sahə_çərçivəsi(icraçı, _E("div", {}, [g, siyahı]), etiket, ad,
                           None, None, False)


def faylSürüklə(icraçı, etiket: Any = None, ad: Any = "fayl",
                növlər: Any = None, çoxlu: Any = False,
                dəyişdi: Any = None,
                mətn: Any = "Faylı bura sürükləyin və ya seçin") -> Element:
    return _E("label", {"class": f"{P}sürüklə-sahəsi"}, [
        _E("span", {"class": f"{P}sürüklə-ikonu"}, "⇪"),
        _E("b", {}, _m(etiket, icraçı)) if etiket is not None else None,
        _E("span", {"class": f"{P}sönük"}, _m(mətn, icraçı)),
        _E("input", {"type": "file", "name": _m(ad, icraçı) or None,
                     "accept": _m(növlər, icraçı) or None,
                     "multiple": True if çoxlu else None,
                     "dəyişdi": dəyişdi}),
    ])


def keçidDüyməsi(icraçı, mətn: Any = "", basılı: Any = False,
                 klik: Any = None, ikon: Any = None) -> Element:
    return _E("button", {
        "class": _sinif(f"{P}düymə", f"{P}düymə--ikinci",
                        f"{P}keçid-düyməsi",
                        f"{P}keçid-düyməsi--basılı" if basılı else None),
        "type": "button", "aria-pressed": "true" if basılı else "false",
        "value": "yanlış" if basılı else "doğru", "klik": klik,
    }, [_E("span", {"class": f"{P}ikon"}, _m(ikon, icraçı))
        if ikon is not None else None, _m(mətn, icraçı)])


def açılanMenyu(icraçı, mətn: Any = "Menyu", elementlər: Any = None,
                klik: Any = None, növ: Any = "ikinci") -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "ikinci"), NÖVLƏR, "düymə növü")
    return _E("details", {"class": f"{P}açılan"}, [
        _E("summary", {"class": _sinif(f"{P}düymə", f"{P}düymə--{n}")},
           [_m(mətn, icraçı), _E("span", {"class": f"{P}ox"}, "▾")]),
        _E("div", {"class": f"{P}açılan-menyu", "role": "menu"}, [
            _E("button", {"class": f"{P}menyu-elementi", "type": "button",
                          "role": "menuitem", "value": d, "klik": klik}, e)
            for d, e in _seçimlər(elementlər, icraçı)]),
    ])


def bölünmüşDüymə(icraçı, mətn: Any = "", klik: Any = None,
                  elementlər: Any = None, seçildi: Any = None,
                  növ: Any = "əsas") -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "əsas"), NÖVLƏR, "düymə növü")
    return _E("div", {"class": f"{P}bölünmüş-düymə"}, [
        _E("button", {"class": _sinif(f"{P}düymə", f"{P}düymə--{n}"),
                      "type": "button", "klik": klik}, _m(mətn, icraçı)),
        _E("details", {"class": f"{P}açılan"}, [
            _E("summary", {"class": _sinif(f"{P}düymə", f"{P}düymə--{n}",
                                           f"{P}bölünmüş-ox"),
                           "title": "Digər seçimlər"}, "▾"),
            _E("div", {"class": f"{P}açılan-menyu", "role": "menu"}, [
                _E("button", {"class": f"{P}menyu-elementi",
                              "type": "button", "value": d,
                              "klik": seçildi}, e)
                for d, e in _seçimlər(elementlər, icraçı)]),
        ]),
    ])


def üzənDüymə(icraçı, ikon: Any = "+", başlıq: Any = "Əlavə et",
              klik: Any = None, tərəf: Any = "sağ") -> Element:
    t = _növü_yoxla(_m(tərəf, icraçı, "sağ"), ("sol", "sağ"),
                    "düymə tərəfi")
    return _E("button", {
        "class": _sinif(f"{P}üzən-düymə", f"{P}üzən-düymə--{t}"),
        "type": "button", "title": _m(başlıq, icraçı),
        "aria-label": _m(başlıq, icraçı), "klik": klik,
    }, _m(ikon, icraçı))


# ═══════════════════════════════════════════════════════════════════════
#  Göstərmə
# ═══════════════════════════════════════════════════════════════════════

def çip(icraçı, mətn: Any = "", növ: Any = "ikinci", silindi: Any = None,
        ikon: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "ikinci"), NÖVLƏR, "çip növü")
    return _E("span", {"class": _sinif(f"{P}çip", f"{P}çip--{n}")}, [
        _E("span", {"class": f"{P}ikon"}, _m(ikon, icraçı))
        if ikon is not None else None,
        _m(mətn, icraçı),
        _E("button", {"class": f"{P}çip-sil", "type": "button",
                      "title": "Sil", "value": _m(mətn, icraçı),
                      "klik": silindi}, "✕") if silindi is not None
        else None])


def ikon(icraçı, simvol: Any = "★", ölçü: Any = 20,
         başlıq: Any = None) -> Element:
    return _E("span", {
        "class": f"{P}ikon-tək", "role": "img" if başlıq else None,
        "aria-label": _m(başlıq, icraçı) or None,
        "aria-hidden": None if başlıq else "true",
        "title": _m(başlıq, icraçı) or None,
        "style": f"font-size:{_ölçü(ölçü) or '20px'}",
    }, _m(simvol, icraçı))


def klaviş(icraçı, düymələr: Any = None) -> Element:
    adlar = _sətirlər(düymələr, icraçı) or ["Ctrl", "S"]
    uşaqlar: list = []
    for i, d in enumerate(adlar):
        if i:
            uşaqlar.append(_E("span", {"class": f"{P}klaviş-ayırıcı"}, "+"))
        uşaqlar.append(_E("kbd", {"class": f"{P}klaviş"}, d))
    return _E("span", {"class": f"{P}klavişlər"}, uşaqlar)


def vaxtXətti(icraçı, elementlər: Any = None) -> Element:
    """`elementlər`: [["2024", "Başlıq", "izah"], ...] və ya lüğətlər."""
    sətirlər = []
    for e in (elementlər or []):
        if isinstance(e, dict):
            t, b, i = (e.get("tarix"), e.get("başlıq"), e.get("mətn"))
        elif isinstance(e, (list, tuple)):
            t, b, i = (list(e) + [None, None, None])[:3]
        else:
            t, b, i = None, e, None
        sətirlər.append(_E("li", {"class": f"{P}vaxt-nöqtəsi"}, [
            _E("span", {"class": f"{P}vaxt-tarixi"}, _m(t, icraçı))
            if t is not None else None,
            _E("b", {}, _m(b, icraçı)),
            _E("p", {"class": f"{P}sönük"}, _m(i, icraçı))
            if i is not None else None]))
    return _E("ol", {"class": f"{P}vaxt-xətti"}, sətirlər)


def ağac(icraçı, elementlər: Any = None, açılmış: Any = True,
         klik: Any = None) -> Element:
    """`elementlər`: ["fayl", ["qovluq", [uşaqlar…]], …]"""
    def qur(siyahı) -> Element:
        uşaqlar = []
        for e in siyahı or []:
            if isinstance(e, (list, tuple)) and len(e) == 2 and \
                    isinstance(e[1], (list, tuple)):
                uşaqlar.append(_E("li", {}, _E("details", {
                    "open": True if açılmış else None}, [
                    _E("summary", {"class": f"{P}ağac-qovluq"},
                       ["📁 ", _m(e[0], icraçı)]), qur(e[1])])))
            else:
                ad = _m(e, icraçı)
                uşaqlar.append(_E("li", {}, _E("button", {
                    "class": f"{P}ağac-elementi", "type": "button",
                    "value": ad, "klik": klik}, ["📄 ", ad])))
        return _E("ul", {"class": f"{P}ağac", "role": "tree"}, uşaqlar)
    return qur(elementlər)


def siyahıQrupu(icraçı, elementlər: Any = None, klik: Any = None,
                seçili: Any = None) -> Element:
    """`elementlər`: ["Ad", ["Başlıq", "alt mətn"], …]"""
    seç = _m(seçili, icraçı) if seçili is not None else None
    sətirlər = []
    for e in elementlər or []:
        if isinstance(e, (list, tuple)):
            b, a = _m(e[0], icraçı), (_m(e[1], icraçı) if len(e) > 1
                                       else None)
        else:
            b, a = _m(e, icraçı), None
        sətirlər.append(_E("button" if klik is not None else "div", {
            "class": _sinif(f"{P}siyahı-qrupu-elementi",
                            f"{P}siyahı-qrupu-elementi--seçili"
                            if b == seç else None),
            "type": "button" if klik is not None else None,
            "value": b if klik is not None else None, "klik": klik,
        }, [_E("span", {"class": f"{P}sq-başlıq"}, b),
            _E("span", {"class": f"{P}sönük"}, a) if a else None,
            _E("span", {"class": f"{P}sq-ox"}, "›")
            if klik is not None else None]))
    return _E("div", {"class": f"{P}siyahı-qrupu"}, sətirlər)


def avatarQrupu(icraçı, adlar: Any = None, maksimum: Any = 4) -> Element:
    from . import vidjet as V
    hamısı = _sətirlər(adlar, icraçı)
    n = max(1, int(_say(maksimum, 4)))
    uşaqlar = [V.avatar.__wrapped__(icraçı, a, None, "kiçik")
               for a in hamısı[:n]]
    if len(hamısı) > n:
        uşaqlar.append(_E("span", {"class": _sinif(
            f"{P}avatar", f"{P}avatar--kiçik", f"{P}avatar-artıq")},
            f"+{len(hamısı) - n}"))
    return _E("div", {"class": f"{P}avatar-qrupu"}, uşaqlar)


def göstərici(icraçı, dəyər: Any = 0, minimum: Any = 0, maksimum: Any = 100,
              etiket: Any = None, aşağı: Any = None,
              yuxarı: Any = None) -> Element:
    mn, mx = _say(minimum), _say(maksimum, 100)
    d = _say(dəyər)
    return _E("div", {"class": f"{P}göstərici"}, [
        _E("div", {"class": f"{P}tərəqqi-başı"}, [
            _E("span", {}, _m(etiket, icraçı)), _E("span", {}, f"{d:g}")])
        if etiket is not None else None,
        _E("meter", {"min": f"{mn:g}", "max": f"{mx:g}", "value": f"{d:g}",
                     "low": f"{_say(aşağı):g}" if aşağı is not None
                     else None,
                     "high": f"{_say(yuxarı):g}" if yuxarı is not None
                     else None})])


def qiymətKartı(icraçı, plan: Any = "Əsas", qiymət: Any = "0 ₼",
                dövr: Any = "/ ay", xüsusiyyətlər: Any = None,
                düyməMətni: Any = "Seç", klik: Any = None,
                seçilmiş: Any = False) -> Element:
    return _E("div", {"class": _sinif(f"{P}qiymət-kartı",
                                      f"{P}qiymət-kartı--seçilmiş"
                                      if seçilmiş else None)}, [
        _E("h3", {"class": f"{P}qiymət-planı"}, _m(plan, icraçı)),
        _E("p", {"class": f"{P}qiymət"}, [
            _m(qiymət, icraçı),
            _E("span", {"class": f"{P}sönük"}, " " + _m(dövr, icraçı))]),
        xüsusiyyətSiyahısı(icraçı, xüsusiyyətlər),
        _E("button", {"class": _sinif(f"{P}düymə",
                                      f"{P}düymə--{'əsas' if seçilmiş else 'ikinci'}",
                                      f"{P}düymə--tamEn"),
                      "type": "button", "value": _m(plan, icraçı),
                      "klik": klik}, _m(düyməMətni, icraçı))])


def xüsusiyyətSiyahısı(icraçı, elementlər: Any = None,
                       işarə: Any = "✓") -> Element:
    return _E("ul", {"class": f"{P}xüsusiyyət-siyahısı"}, [
        _E("li", {}, [_E("span", {"class": f"{P}xs-işarə"},
                         _m(işarə, icraçı)), x])
        for x in _sətirlər(elementlər, icraçı)])


def rəy(icraçı, mətn: Any = "", ad: Any = "", vəzifə: Any = None,
        reytinqi: Any = None) -> Element:
    from . import vidjet as V
    return _E("figure", {"class": f"{P}rəy"}, [
        reytinq(icraçı, reytinqi, 5, None, None, True)
        if reytinqi is not None else None,
        _E("blockquote", {"class": f"{P}rəy-mətni"}, _m(mətn, icraçı)),
        _E("figcaption", {"class": f"{P}rəy-müəllif"}, [
            V.avatar.__wrapped__(icraçı, _m(ad, icraçı), None, "kiçik"),
            _E("span", {}, [_E("b", {}, _m(ad, icraçı)),
                            _E("span", {"class": f"{P}sönük"},
                               _m(vəzifə, icraçı))
                            if vəzifə is not None else None])])])


def qəhrəman(icraçı, başlıq: Any = "", altMətn: Any = None,
             hərəkətlər: Any = None, mərkəzdə: Any = True) -> Element:
    return _E("section", {"class": _sinif(f"{P}qəhrəman",
                                          f"{P}qəhrəman--mərkəz"
                                          if mərkəzdə else None)}, [
        _E("h1", {"class": f"{P}qəhrəman-başlığı"}, _m(başlıq, icraçı)),
        _E("p", {"class": f"{P}qəhrəman-mətni"}, _m(altMətn, icraçı))
        if altMətn is not None else None,
        _E("div", {"class": f"{P}qəhrəman-hərəkətləri"}, hərəkətlər)
        if hərəkətlər is not None else None])


def səhifəAltlığı(icraçı, mətn: Any = "", keçidlər: Any = None) -> Element:
    """`keçidlər`: [["/haqqında", "Haqqında"], …]"""
    return _E("footer", {"class": f"{P}səhifə-altlığı"}, [
        _E("span", {"class": f"{P}sönük"}, _m(mətn, icraçı)),
        _E("nav", {"class": f"{P}altlıq-keçidləri"}, [
            _E("a", {"href": _url(u, icraçı)}, e)
            for u, e in _seçimlər(keçidlər, icraçı)])])


def qeydQutusu(icraçı, başlıq: Any = None, mətn: Any = "",
               növ: Any = "məlumat", ikon: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "məlumat"),
                    ("məlumat", "uğur", "xəbərdarlıq", "təhlükə"),
                    "qeyd növü")
    standart = {"məlumat": "ℹ", "uğur": "✓", "xəbərdarlıq": "⚠",
                "təhlükə": "⛔"}[n]
    return _E("aside", {"class": _sinif(f"{P}qeyd-qutusu",
                                        f"{P}qeyd-qutusu--{n}")}, [
        _E("span", {"class": f"{P}qeyd-ikonu"},
           _m(ikon, icraçı) if ikon is not None else standart),
        _E("div", {}, [_E("b", {}, _m(başlıq, icraçı))
                       if başlıq is not None else None,
                       _E("p", {}, _m(mətn, icraçı))])])


def elanZolağı(icraçı, mətn: Any = "", növ: Any = "məlumat",
               hərəkət: Any = None, bağlandı: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "məlumat"),
                    ("məlumat", "uğur", "xəbərdarlıq", "təhlükə"),
                    "elan növü")
    return _E("div", {"class": _sinif(f"{P}elan-zolağı",
                                      f"{P}elan-zolağı--{n}"),
                      "role": "status"}, [
        _E("span", {}, _m(mətn, icraçı)), hərəkət,
        _E("button", {"class": f"{P}modal-bağla", "type": "button",
                      "title": "Bağla", "klik": bağlandı}, "✕")
        if bağlandı is not None else None])


def təqvim(icraçı, il: Any = 2026, ayı: Any = 1, seçili: Any = None,
           klik: Any = None, qeydlilər: Any = None) -> Element:
    i = int(_say(il, 2026))
    a = max(1, min(12, int(_say(ayı, 1))))
    seç = _m(seçili, icraçı) if seçili is not None else ""
    qeydli = set(_sətirlər(qeydlilər, icraçı))
    həftələr = calendar.Calendar(firstweekday=0).monthdayscalendar(i, a)
    əvvəl_i, əvvəl_a = (i - 1, 12) if a == 1 else (i, a - 1)
    sonra_i, sonra_a = (i + 1, 1) if a == 12 else (i, a + 1)
    sətirlər = [_E("tr", {}, [_E("th", {}, g) for g in _GÜNLƏR])]
    for h in həftələr:
        xanalar = []
        for g in h:
            if not g:
                xanalar.append(_E("td", {}))
                continue
            t = f"{i:04d}-{a:02d}-{g:02d}"
            xanalar.append(_E("td", {}, _E("button", {
                "class": _sinif(f"{P}gün", f"{P}gün--seçili" if t == seç
                                else None,
                                f"{P}gün--qeydli" if t in qeydli else None),
                "type": "button", "value": t, "klik": klik}, str(g))))
        sətirlər.append(_E("tr", {}, xanalar))
    return _E("div", {"class": f"{P}təqvim"}, [
        _E("div", {"class": f"{P}təqvim-başı"}, [
            _E("button", {"class": f"{P}təqvim-ox", "type": "button",
                          "value": f"{əvvəl_i:04d}-{əvvəl_a:02d}",
                          "title": "Əvvəlki ay", "klik": klik}, "‹"),
            _E("b", {}, f"{_AYLAR[a - 1]} {i}"),
            _E("button", {"class": f"{P}təqvim-ox", "type": "button",
                          "value": f"{sonra_i:04d}-{sonra_a:02d}",
                          "title": "Növbəti ay", "klik": klik}, "›")]),
        _E("table", {}, sətirlər)])


# ── Qrafiklər (SVG) ───────────────────────────────────────────────────

def _svg(en: float, hündürlük: float, uşaqlar: list,
         başlıq: str | None) -> Element:
    return _E("svg", {"class": f"{P}qrafik", "viewBox": f"0 0 {en:g} "
                      f"{hündürlük:g}", "role": "img",
                      "aria-label": başlıq or "qrafik",
                      "xmlns": "http://www.w3.org/2000/svg"},
              ([_E("title", {}, başlıq)] if başlıq else []) + uşaqlar)


def _qrafik_qabı(icraçı, başlıq, svg: Element, əfsanə: list | None) -> Element:
    return _E("figure", {"class": f"{P}qrafik-qabı"}, [
        _E("figcaption", {"class": f"{P}qrafik-başlığı"}, _m(başlıq, icraçı))
        if başlıq is not None else None, svg,
        _E("div", {"class": f"{P}əfsanə"}, əfsanə) if əfsanə else None])


def sütunQrafiki(icraçı, dəyərlər: Any = None, etiketlər: Any = None,
                 başlıq: Any = None, hündürlük: Any = 160) -> Element:
    d = _ədəd_siyahısı(dəyərlər)
    e = _sətirlər(etiketlər, icraçı)
    H = max(60.0, _say(hündürlük, 160))
    W = max(1, len(d)) * 40
    mx = max([abs(x) for x in d] + [1e-9])
    uşaqlar: list = []
    for i, x in enumerate(d):
        h = (H - 22) * abs(x) / mx
        uşaqlar.append(_E("rect", {
            "class": f"{P}q{i % 6 + 1}", "x": f"{i * 40 + 8:g}",
            "y": f"{H - 18 - h:g}", "width": "24", "height": f"{h:g}",
            "rx": "3"}, _E("title", {}, f"{e[i] if i < len(e) else i + 1}:"
                                    f" {x:g}")))
        if i < len(e):
            uşaqlar.append(_E("text", {"x": f"{i * 40 + 20:g}",
                                       "y": f"{H - 4:g}",
                                       "class": f"{P}q-mətn"}, e[i]))
    return _qrafik_qabı(icraçı, başlıq, _svg(W, H, uşaqlar, _m(
        başlıq, icraçı) or None), None)


def xəttQrafiki(icraçı, dəyərlər: Any = None, etiketlər: Any = None,
                başlıq: Any = None, hündürlük: Any = 160,
                sahəli: Any = True) -> Element:
    d = _ədəd_siyahısı(dəyərlər) or [0]
    e = _sətirlər(etiketlər, icraçı)
    H = max(60.0, _say(hündürlük, 160))
    W = max(2, len(d)) * 40
    mn, mx = min(d), max(d)
    aralıq = (mx - mn) or 1
    nöqtələr = [(20 + i * (W - 40) / max(1, len(d) - 1),
                 8 + (H - 30) * (1 - (x - mn) / aralıq))
                for i, x in enumerate(d)]
    yol = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
                   for i, (x, y) in enumerate(nöqtələr))
    uşaqlar: list = []
    if sahəli:
        uşaqlar.append(_E("path", {
            "class": f"{P}q-sahə",
            "d": f"{yol} L{nöqtələr[-1][0]:.1f},{H - 20:g} "
                 f"L{nöqtələr[0][0]:.1f},{H - 20:g} Z"}))
    uşaqlar.append(_E("path", {"class": f"{P}q-xətt", "d": yol}))
    for i, (x, y) in enumerate(nöqtələr):
        uşaqlar.append(_E("circle", {"class": f"{P}q-nöqtə", "cx": f"{x:.1f}",
                                     "cy": f"{y:.1f}", "r": "3"},
                          _E("title", {}, f"{d[i]:g}")))
        if i < len(e):
            uşaqlar.append(_E("text", {"x": f"{x:.1f}", "y": f"{H - 4:g}",
                                       "class": f"{P}q-mətn"}, e[i]))
    return _qrafik_qabı(icraçı, başlıq, _svg(W, H, uşaqlar, _m(
        başlıq, icraçı) or None), None)


def dairəQrafiki(icraçı, dəyərlər: Any = None, etiketlər: Any = None,
                 başlıq: Any = None, halqa: Any = True) -> Element:
    d = [max(0.0, x) for x in _ədəd_siyahısı(dəyərlər)]
    e = _sətirlər(etiketlər, icraçı)
    cəm = sum(d) or 1
    R, r = 50.0, (30.0 if halqa else 0.0)
    bucaq = -math.pi / 2
    uşaqlar: list = []
    əfsanə: list = []
    for i, x in enumerate(d):
        pay = x / cəm
        if pay <= 0:
            continue
        son = bucaq + pay * 2 * math.pi
        if pay >= 0.9999:
            son = bucaq + 2 * math.pi - 1e-4
        böyük = 1 if son - bucaq > math.pi else 0
        p = [(60 + R * math.cos(bucaq), 60 + R * math.sin(bucaq)),
             (60 + R * math.cos(son), 60 + R * math.sin(son)),
             (60 + r * math.cos(son), 60 + r * math.sin(son)),
             (60 + r * math.cos(bucaq), 60 + r * math.sin(bucaq))]
        yol = (f"M{p[0][0]:.2f},{p[0][1]:.2f} A{R:g},{R:g} 0 {böyük} 1 "
               f"{p[1][0]:.2f},{p[1][1]:.2f} L{p[2][0]:.2f},{p[2][1]:.2f}")
        yol += (f" A{r:g},{r:g} 0 {böyük} 0 {p[3][0]:.2f},{p[3][1]:.2f} Z"
                if r else " Z")
        ad = e[i] if i < len(e) else str(i + 1)
        uşaqlar.append(_E("path", {"class": f"{P}q{i % 6 + 1}", "d": yol},
                          _E("title", {}, f"{ad}: {x:g} "
                                          f"({pay * 100:.0f}%)")))
        əfsanə.append(_E("span", {"class": f"{P}əfsanə-elementi"}, [
            _E("i", {"class": f"{P}əfsanə-rəngi {P}qf{i % 6 + 1}"}),
            f"{ad} · {pay * 100:.0f}%"]))
        bucaq = son
    return _qrafik_qabı(icraçı, başlıq, _svg(120, 120, uşaqlar, _m(
        başlıq, icraçı) or None), əfsanə)


def kiçikQrafik(icraçı, dəyərlər: Any = None, en: Any = 100,
                hündürlük: Any = 28) -> Element:
    d = _ədəd_siyahısı(dəyərlər) or [0]
    W, H = max(20.0, _say(en, 100)), max(10.0, _say(hündürlük, 28))
    mn, mx = min(d), max(d)
    aralıq = (mx - mn) or 1
    yol = " ".join(
        f"{'M' if i == 0 else 'L'}{2 + i * (W - 4) / max(1, len(d) - 1):.1f},"
        f"{2 + (H - 4) * (1 - (x - mn) / aralıq):.1f}"
        for i, x in enumerate(d))
    return _E("svg", {"class": f"{P}kiçik-qrafik", "viewBox":
                      f"0 0 {W:g} {H:g}", "width": f"{W:g}",
                      "height": f"{H:g}", "aria-hidden": "true"},
              [_E("path", {"class": f"{P}q-xətt", "d": yol})])


# ── Media ─────────────────────────────────────────────────────────────

def video(icraçı, mənbə: Any = "", poster: Any = None,
          idarəetmə: Any = True, avtomatik: Any = False,
          səssiz: Any = False, təkrar: Any = False) -> Element:
    return _E("video", {
        "class": f"{P}video", "src": _url(mənbə, icraçı) or None,
        "poster": _url(poster, icraçı, True) if poster else None,
        "controls": True if idarəetmə else None,
        "autoplay": True if avtomatik else None,
        "muted": True if (səssiz or avtomatik) else None,
        "loop": True if təkrar else None, "playsinline": True,
        "preload": "metadata"})


def audio(icraçı, mənbə: Any = "", idarəetmə: Any = True,
          təkrar: Any = False) -> Element:
    return _E("audio", {"class": f"{P}audio",
                        "src": _url(mənbə, icraçı) or None,
                        "controls": True if idarəetmə else None,
                        "loop": True if təkrar else None,
                        "preload": "metadata"})


def yerləşdirmə(icraçı, ünvan: Any = "", başlıq: Any = "Yerləşdirilmiş "
                "məzmun", hündürlük: Any = 315,
                nisbət: Any = None) -> Element:
    u = _url(ünvan, icraçı)
    if u and not u.startswith(("https://", "http://", "/")):
        raise AlqorXəta("ArqumentXətası", "yerləşdirmə yalnız http(s) "
                        "ünvanı qəbul edir", kod="ALQ-R013")
    return _E("div", {"class": f"{P}yerləşdirmə",
                      "style": f"aspect-ratio:{_m(nisbət, icraçı)}"
                      if nisbət is not None else
                      f"height:{_ölçü(hündürlük)}"},
              _E("iframe", {"src": u or "about:blank",
                            "title": _m(başlıq, icraçı),
                            "loading": "lazy",
                            "referrerpolicy": "strict-origin-when-"
                                              "cross-origin",
                            "sandbox": "allow-scripts allow-same-origin "
                                       "allow-popups allow-presentation",
                            "allow": "fullscreen; picture-in-picture"}))


def qalereya(icraçı, şəkillər: Any = None, sütunlar: Any = 3,
             klik: Any = None) -> Element:
    """`şəkillər`: ["a.jpg", ["b.jpg", "izah"], …]"""
    uşaqlar = []
    for i, ş in enumerate(şəkillər or []):
        mənbə, izah = (ş[0], ş[1] if len(ş) > 1 else "") \
            if isinstance(ş, (list, tuple)) else (ş, "")
        img = _E("img", {"src": _url(mənbə, icraçı, True),
                         "alt": _m(izah, icraçı), "loading": "lazy"})
        uşaqlar.append(_E("button", {"class": f"{P}qalereya-elementi",
                                     "type": "button", "value": str(i),
                                     "klik": klik}, img)
                       if klik is not None else
                       _E("div", {"class": f"{P}qalereya-elementi"}, img))
    return _E("div", {"class": f"{P}qalereya",
                      "style": f"--sütunlar:{int(_say(sütunlar, 3))}"},
              uşaqlar)


def karusel(icraçı, slaydlar: Any = None, cari: Any = 0,
            klik: Any = None) -> Element:
    """Hər slayd element, şəkil ünvanı və ya ["şəkil", "başlıq"]."""
    siyahı = list(slaydlar or [])
    n = len(siyahı)
    c = int(_say(cari)) % n if n else 0

    def slayd(s) -> Any:
        if isinstance(s, Element):
            return s
        if isinstance(s, (list, tuple)):
            return [_E("img", {"src": _url(s[0], icraçı, True),
                               "alt": _m(s[1] if len(s) > 1 else "",
                                         icraçı)}),
                    _E("div", {"class": f"{P}slayd-başlığı"},
                       _m(s[1], icraçı)) if len(s) > 1 else None]
        return _E("img", {"src": _url(s, icraçı, True), "alt": ""})
    return _E("div", {"class": f"{P}karusel", "role": "region",
                      "aria-roledescription": "karusel"}, [
        _E("div", {"class": f"{P}slayd"}, slayd(siyahı[c]) if n else None),
        _E("button", {"class": f"{P}karusel-ox {P}karusel-ox--sol",
                      "type": "button", "value": str((c - 1) % n if n else 0),
                      "title": "Əvvəlki", "klik": klik}, "‹"),
        _E("button", {"class": f"{P}karusel-ox {P}karusel-ox--sağ",
                      "type": "button", "value": str((c + 1) % n if n else 0),
                      "title": "Növbəti", "klik": klik}, "›"),
        _E("div", {"class": f"{P}karusel-nöqtələri"}, [
            _E("button", {"class": _sinif(f"{P}karusel-nöqtə",
                                          f"{P}karusel-nöqtə--cari"
                                          if i == c else None),
                          "type": "button", "value": str(i),
                          "title": f"{i + 1}-ci slayd", "klik": klik})
            for i in range(n)])])


def işarəliMətn(icraçı, mətn: Any = "") -> Element:
    """Markdown → HTML (alt çoxluq: başlıq, siyahı, kod, `kod`, **qalın**).
    Mətn qaçırılır — HTML yeridilə bilməz."""
    from .modullar.html_ import oxu
    from .senedci import md_html

    def çevir(d) -> list:
        n: list = []
        for u in d.uşaq:
            if isinstance(u, str):
                n.append(u)
            else:
                n.append(Element(u.ad_, dict(u.atr), çevir(u)))
        return n
    # md_html mətni qaçırır — ağacda yalnız onun öz teqləri olur
    return _E("div", {"class": f"{P}markdown"},
              çevir(oxu(md_html(_m(mətn, icraçı), əsl_başlıqlar=True))))


def profilKartı(icraçı, ad: Any = "", vəzifə: Any = None,
                mənbə: Any = None, hərəkətlər: Any = None,
                statistika: Any = None) -> Element:
    from . import vidjet as V
    st = [_E("div", {}, [_E("b", {}, _m(d, icraçı)),
                         _E("span", {"class": f"{P}sönük"}, a)])
          for a, d in _seçimlər_cüt(statistika, icraçı)]
    return _E("div", {"class": f"{P}profil-kartı"}, [
        V.avatar.__wrapped__(icraçı, _m(ad, icraçı), mənbə, "böyük"),
        _E("h3", {}, _m(ad, icraçı)),
        _E("p", {"class": f"{P}sönük"}, _m(vəzifə, icraçı))
        if vəzifə is not None else None,
        _E("div", {"class": f"{P}profil-statistikası"}, st) if st else None,
        _E("div", {"class": f"{P}profil-hərəkətləri"}, hərəkətlər)
        if hərəkətlər is not None else None])


def _seçimlər_cüt(d: Any, icraçı) -> list[tuple[str, Any]]:
    if isinstance(d, dict):
        return [(str(a), b) for a, b in d.items()]
    return [(a, b) for a, b in _seçimlər(d, icraçı)]


def bildirişNişanı(icraçı, ikon: Any = "🔔", say: Any = 0,
                   klik: Any = None, maksimum: Any = 99) -> Element:
    n = int(_say(say))
    mx = int(_say(maksimum, 99))
    return _E("button", {"class": f"{P}bildiriş-nişanı", "type": "button",
                         "title": f"{n} bildiriş", "klik": klik}, [
        _m(ikon, icraçı),
        _E("span", {"class": f"{P}say-nişanı"},
           f"{mx}+" if n > mx else str(n)) if n > 0 else None])


# ═══════════════════════════════════════════════════════════════════════
#  Vəziyyət (feedback)
# ═══════════════════════════════════════════════════════════════════════

def yüklənməÖrtüyü(icraçı, məzmun: Any = None, yüklənir: Any = True,
                   mətn: Any = "Yüklənir…") -> Element:
    return _E("div", {"class": f"{P}yüklənmə-qabı",
                      "aria-busy": "true" if yüklənir else None}, [
        _E("div", {}, məzmun),
        _E("div", {"class": f"{P}yüklənmə-örtüyü"}, [
            _E("span", {"class": f"{P}fırlanan"}),
            _E("span", {}, _m(mətn, icraçı))]) if yüklənir else None])


def nəticə(icraçı, növ: Any = "uğur", başlıq: Any = "",
           mətn: Any = None, hərəkətlər: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "uğur"),
                    ("uğur", "təhlükə", "xəbərdarlıq", "məlumat", "404"),
                    "nəticə növü")
    işarə = {"uğur": "✓", "təhlükə": "✕", "xəbərdarlıq": "!",
             "məlumat": "i", "404": "404"}[n]
    return _E("div", {"class": _sinif(f"{P}nəticə", f"{P}nəticə--{n}")}, [
        _E("div", {"class": f"{P}nəticə-ikonu"}, işarə),
        _E("h2", {}, _m(başlıq, icraçı)),
        _E("p", {"class": f"{P}sönük"}, _m(mətn, icraçı))
        if mətn is not None else None,
        _E("div", {"class": f"{P}nəticə-hərəkətləri"}, hərəkətlər)
        if hərəkətlər is not None else None])


def şifrəGücü(icraçı, şifrə: Any = "") -> Element:
    ş = _m(şifrə, icraçı)
    bal = 0
    if len(ş) >= 8:
        bal += 1
    if len(ş) >= 12:
        bal += 1
    if any(c.islower() for c in ş) and any(c.isupper() for c in ş):
        bal += 1
    if any(c.isdigit() for c in ş):
        bal += 1
    if any(not c.isalnum() for c in ş):
        bal += 1
    səviyyə = 0 if not ş else (1 if bal <= 2 else 2 if bal <= 3 else 3)
    adlar = ["", "Zəif", "Orta", "Güclü"]
    return _E("div", {"class": _sinif(f"{P}şifrə-gücü",
                                      f"{P}şifrə-gücü--{səviyyə}")}, [
        _E("div", {"class": f"{P}şg-zolaqlar"},
           [_E("span", {}) for _ in range(3)]),
        _E("span", {"class": f"{P}şg-mətn"}, adlar[səviyyə])])


# ═══════════════════════════════════════════════════════════════════════
#  Düzülüş
# ═══════════════════════════════════════════════════════════════════════

def konteyner(icraçı, məzmun: Any = None, en: Any = 1100) -> Element:
    return _E("div", {"class": f"{P}konteyner",
                      "style": f"max-width:{_ölçü(en)}"}, məzmun)


def mərkəz(icraçı, məzmun: Any = None, hündürlük: Any = None) -> Element:
    return _E("div", {"class": f"{P}mərkəz",
                      "style": f"min-height:{_ölçü(hündürlük)}"
                      if hündürlük is not None else None}, məzmun)


def ikiSütun(icraçı, sol: Any = None, sağ: Any = None, nisbət: Any = "1:1",
             boşluq: Any = 16) -> Element:
    try:
        a, b = (float(x) for x in _m(nisbət, icraçı, "1:1").split(":"))
    except ValueError:
        raise AlqorXəta("ArqumentXətası", "`nisbət` \"1:2\" kimi olmalıdır",
                        kod="ALQ-R013")
    return _E("div", {"class": f"{P}iki-sütun",
                      "style": f"grid-template-columns:{a:g}fr {b:g}fr;"
                               f"gap:{_ölçü(boşluq)}"}, [
        _E("div", {}, sol), _E("div", {}, sağ)])


def nisbət(icraçı, məzmun: Any = None, forma: Any = "16/9") -> Element:
    return _E("div", {"class": f"{P}nisbət",
                      "style": f"aspect-ratio:{_m(forma, icraçı, '16/9')}"},
              məzmun)


def sürüşmə(icraçı, məzmun: Any = None, hündürlük: Any = 240) -> Element:
    return _E("div", {"class": f"{P}sürüşmə", "tabindex": "0",
                      "style": f"max-height:{_ölçü(hündürlük)}"}, məzmun)


def tətbiqQabığı(icraçı, başlıq: Any = None, yan: Any = None,
                 məzmun: Any = None, altlıq: Any = None) -> Element:
    return _E("div", {"class": f"{P}tətbiq-qabığı"}, [
        _E("header", {"class": f"{P}tq-başlıq"}, başlıq)
        if başlıq is not None else None,
        _E("aside", {"class": f"{P}tq-yan"}, yan) if yan is not None else None,
        _E("main", {"class": f"{P}tq-məzmun"}, məzmun),
        _E("footer", {"class": f"{P}tq-altlıq"}, altlıq)
        if altlıq is not None else None])


# ═══════════════════════════════════════════════════════════════════════
#  Naviqasiya
# ═══════════════════════════════════════════════════════════════════════

def yanNaviqasiya(icraçı, elementlər: Any = None, cari: Any = None,
                  klik: Any = None, başlıq: Any = None) -> Element:
    """`elementlər`: ["Ana", ["ayarlar", "⚙ Ayarlar"], …]"""
    c = _m(cari, icraçı) if cari is not None else None
    return _E("nav", {"class": f"{P}yan-naviqasiya"}, [
        _E("div", {"class": f"{P}yn-başlıq"}, _m(başlıq, icraçı))
        if başlıq is not None else None] + [
        _E("button", {"class": _sinif(f"{P}yn-element",
                                      f"{P}yn-element--cari" if d == c
                                      else None),
                      "type": "button", "value": d, "klik": klik,
                      "aria-current": "page" if d == c else None}, e)
        for d, e in _seçimlər(elementlər, icraçı)])


def alətlərPaneli(icraçı, məzmun: Any = None) -> Element:
    return _E("div", {"class": f"{P}alətlər-paneli", "role": "toolbar"},
              məzmun)


# ═══════════════════════════════════════════════════════════════════════
#  Üst qat
# ═══════════════════════════════════════════════════════════════════════

def açılanPanel(icraçı, düymə: Any = "Ətraflı", məzmun: Any = None,
                açılmış: Any = False) -> Element:
    return _E("details", {"class": f"{P}açılan {P}açılan-panel",
                          "open": True if açılmış else None}, [
        _E("summary", {"class": _sinif(f"{P}düymə", f"{P}düymə--ikinci")},
           _m(düymə, icraçı) if not isinstance(düymə, Element) else düymə),
        _E("div", {"class": f"{P}açılan-menyu {P}açılan-panel-gövdəsi"},
           məzmun)])


def təsdiqDialoqu(icraçı, başlıq: Any = "Əminsiniz?", mətn: Any = "",
                  görünür: Any = True, təsdiqləndi: Any = None,
                  ləğvEdildi: Any = None, təsdiqMətni: Any = "Bəli",
                  ləğvMətni: Any = "Xeyr", təhlükəli: Any = False) -> Element:
    from . import vidjet as V
    return V.modal.__wrapped__(
        icraçı, başlıq, _E("p", {}, _m(mətn, icraçı)),
        _E("div", {"class": f"{P}dialoq-düymələri"}, [
            _E("button", {"class": _sinif(f"{P}düymə", f"{P}düymə--ikinci"),
                          "type": "button", "klik": ləğvEdildi},
               _m(ləğvMətni, icraçı)),
            _E("button", {"class": _sinif(
                f"{P}düymə",
                f"{P}düymə--{'təhlükə' if təhlükəli else 'əsas'}"),
                "type": "button", "klik": təsdiqləndi},
               _m(təsdiqMətni, icraçı))]),
        görünür, ləğvEdildi, "kiçik")


def altVərəq(icraçı, başlıq: Any = "", məzmun: Any = None,
             görünür: Any = True, bağlandı: Any = None) -> Element:
    if not görünür:
        return Element("", {}, [])
    return _E("div", {"class": f"{P}yan-örtüyü"}, _E("section", {
        "class": f"{P}alt-vərəq", "role": "dialog"}, [
        _E("div", {"class": f"{P}alt-vərəq-tutacaq"}),
        _E("div", {"class": f"{P}yan-başı"}, [
            _E("h3", {"class": f"{P}yan-başlığı"}, _m(başlıq, icraçı)),
            _E("button", {"class": f"{P}modal-bağla", "type": "button",
                          "title": "Bağla", "klik": bağlandı}, "✕")
            if bağlandı is not None else None]),
        _E("div", {"class": f"{P}yan-gövdəsi"}, məzmun)]))


# ═══════════════════════════════════════════════════════════════════════
#  Kataloq
# ═══════════════════════════════════════════════════════════════════════

def _seçim_skeleti(ad: str, tip: str = "mətn", çevir: str = "dəyər") -> str:
    return (f"metod {{ad}}Seçildi(dəyər: mətn)\n"
            f"    özü.{{ad}} = {çevir}\n"
            "son")


ƏLAVƏ_KATALOQ: list[Məlumat] = [
    # ── Form ──
    Məlumat("reytinq", FORM, "Ulduzla qiymətləndirmə",
            'vidjet.reytinq(dəyər: özü.{ad}, klik: özü.{ad}Seçildi)',
            ["klik"], _seçim_skeleti("", "tam", "tamƏt(dəyər, 0)"),
            "vəziyyət {ad}: tam = 0"),
    Məlumat("seqmentli", FORM, "Seqmentli seçim (bir neçə düymədən biri)",
            'vidjet.seqmentli(seçimlər: ["Gün", "Həftə", "Ay"],\n'
            '                 dəyər: özü.{ad}, klik: özü.{ad}Seçildi)',
            ["klik"], _seçim_skeleti(""), 'vəziyyət {ad}: mətn = "Gün"'),
    Məlumat("çipSeçimi", FORM, "Çiplərlə çoxlu seçim",
            'vidjet.çipSeçimi(seçimlər: ["Alqor", "Python", "Rust"],\n'
            '                 seçilənlər: özü.{ad}, klik: özü.{ad}Dəyişdi)',
            ["klik"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    əgər dəyər içindədir özü.{ad} onda\n'
            '        özü.{ad} = özü.{ad}.filtr((x) => x != dəyər)\n'
            '    yoxsa\n'
            '        özü.{ad} = özü.{ad} + [dəyər]\n'
            '    son\n'
            'son',
            "vəziyyət {ad}: siyahı[mətn] = []"),
    Məlumat("teqSahəsi", FORM, "Teq daxil etmə sahəsi",
            'vidjet.teqSahəsi(etiket: "Teqlər", teqlər: özü.{ad},\n'
            '                 əlavəEdildi: özü.{ad}Əlavə,\n'
            '                 silindi: özü.{ad}Sil)',
            ["əlavəEdildi", "silindi"],
            'metod {ad}Əlavə(dəyər: mətn)\n'
            '    əgər dəyər.kəs() != "" onda\n'
            '        özü.{ad} = özü.{ad} + [dəyər.kəs()]\n'
            '    son\n'
            'son\n\n'
            'metod {ad}Sil(dəyər: mətn)\n'
            '    özü.{ad} = özü.{ad}.filtr((x) => x != dəyər)\n'
            'son',
            "vəziyyət {ad}: siyahı[mətn] = []"),
    Məlumat("təsdiqKodu", FORM, "Təsdiq kodu (OTP) sahəsi",
            'vidjet.təsdiqKodu(etiket: "SMS kodu", uzunluq: 6,\n'
            '                  dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("telefon", FORM, "Telefon nömrəsi sahəsi",
            'vidjet.telefon(etiket: "Telefon", dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("ePoçt", FORM, "E-poçt sahəsi",
            'vidjet.ePoçt(etiket: "E-poçt", dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("keçidSahəsi", FORM, "URL (veb ünvan) sahəsi",
            'vidjet.keçidSahəsi(etiket: "Sayt", dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("pulSahəsi", FORM, "Məbləğ (valyuta) sahəsi",
            'vidjet.pulSahəsi(etiket: "Məbləğ", valyuta: "₼",\n'
            '                 dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = onluqƏt(dəyər, 0.0)\n'
            'son', 'vəziyyət {ad}: onluq = 0.0'),
    Məlumat("tarixAralığı", FORM, "Tarix aralığı",
            'vidjet.tarixAralığı(etiket: "Dövr",\n'
            '                    başlanğıcDəyişdi: özü.{ad}Başlanğıc,\n'
            '                    bitməDəyişdi: özü.{ad}Bitmə)',
            ["başlanğıcDəyişdi", "bitməDəyişdi"],
            'metod {ad}Başlanğıc(dəyər: mətn)\n'
            '    özü.{ad}Baş = dəyər\n'
            'son\n\n'
            'metod {ad}Bitmə(dəyər: mətn)\n'
            '    özü.{ad}Son = dəyər\n'
            'son',
            'vəziyyət {ad}Baş: mətn = ""\nvəziyyət {ad}Son: mətn = ""'),
    Məlumat("tarixVaxt", FORM, "Tarix və vaxt seçimi",
            'vidjet.tarixVaxt(etiket: "Görüş", dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("ay", FORM, "Ay seçimi",
            'vidjet.ay(etiket: "Ay", dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("sayğac", FORM, "Artır/azalt sayğacı (stepper)",
            'vidjet.sayğac(etiket: "Say", dəyər: özü.{ad},\n'
            '              klik: özü.{ad}Dəyişdi)',
            ["klik"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = tamƏt(dəyər, 0)\n'
            'son', 'vəziyyət {ad}: tam = 1'),
    Məlumat("avtoTamamlama", FORM, "Təklifli sahə (autocomplete)",
            'vidjet.avtoTamamlama(etiket: "Şəhər",\n'
            '                     təkliflər: ["Bakı", "Gəncə", "Şəki"],\n'
            '                     dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi", "yazıldı"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("faylSürüklə", FORM, "Fayl sürükləmə sahəsi (dropzone)",
            'vidjet.faylSürüklə(etiket: "Sənəd yüklə",\n'
            '                   dəyişdi: özü.{ad}Seçildi)',
            ["dəyişdi"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("keçidDüyməsi", FORM, "Basılı qalan düymə (toggle)",
            'vidjet.keçidDüyməsi(mətn: "Qalın", ikon: "B",\n'
            '                    basılı: özü.{ad}, klik: özü.{ad}Dəyiş)',
            ["klik"],
            'metod {ad}Dəyiş()\n'
            '    özü.{ad} = deyil özü.{ad}\n'
            'son', 'vəziyyət {ad}: məntiq = yanlış'),
    Məlumat("açılanMenyu", FORM, "Açılan menyu (dropdown)",
            'vidjet.açılanMenyu(mətn: "Əməliyyatlar",\n'
            '                   elementlər: ["Redaktə", "Kopyala", "Sil"],\n'
            '                   klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    // dəyər — seçilən menyu elementi\n'
            'son'),
    Məlumat("bölünmüşDüymə", FORM, "Bölünmüş düymə (əsas əməl + menyu)",
            'vidjet.bölünmüşDüymə(mətn: "Saxla", klik: özü.{ad}Saxla,\n'
            '                     elementlər: ["Kimi saxla", "Hamısını"],\n'
            '                     seçildi: özü.{ad}Seçildi)',
            ["klik", "seçildi"],
            'metod {ad}Saxla()\n'
            '    // əsas əməl\n'
            'son\n\n'
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    // menyudan seçim\n'
            'son'),
    Məlumat("üzənDüymə", FORM, "Üzən əməliyyat düyməsi (FAB)",
            'vidjet.üzənDüymə(ikon: "+", başlıq: "Yeni",\n'
            '                 klik: özü.{ad}Basıldı)',
            ["klik"],
            'metod {ad}Basıldı()\n'
            '    // …\n'
            'son'),

    # ── Göstərmə ──
    Məlumat("çip", GÖSTƏRMƏ, "Çip (silinə bilən teq)",
            'vidjet.çip(mətn: "Alqor", növ: "əsas")', ["silindi"]),
    Məlumat("ikon", GÖSTƏRMƏ, "İkon (simvol)",
            'vidjet.ikon(simvol: "⚙", ölçü: 24, başlıq: "Ayarlar")'),
    Məlumat("klaviş", GÖSTƏRMƏ, "Klaviatura düyməsi",
            'vidjet.klaviş(düymələr: ["Ctrl", "S"])'),
    Məlumat("vaxtXətti", GÖSTƏRMƏ, "Vaxt xətti (timeline)",
            'vidjet.vaxtXətti(elementlər: [\n'
            '    ["2024", "Başlanğıc", "Layihə yaradıldı"],\n'
            '    ["2026", "1.0", "İlk buraxılış"]\n'
            '])'),
    Məlumat("ağac", GÖSTƏRMƏ, "Ağac görünüşü (fayl ağacı)",
            'vidjet.ağac(elementlər: [\n'
            '    ["mənbə", ["əsas.alq", "model.alq"]],\n'
            '    "README.md"\n'
            '], klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("siyahıQrupu", GÖSTƏRMƏ, "Klikləyən sətirli siyahı",
            'vidjet.siyahıQrupu(elementlər: [\n'
            '    ["Profil", "Ad, şəkil"], ["Təhlükəsizlik", "Şifrə"]\n'
            '], seçili: özü.{ad}, klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("avatarQrupu", GÖSTƏRMƏ, "Avatar qrupu",
            'vidjet.avatarQrupu(adlar: ["Aysel Əliyeva", "Kamran Rəhimov",\n'
            '                           "Nərmin Həsənova"])'),
    Məlumat("göstərici", GÖSTƏRMƏ, "Ölçü göstəricisi (meter)",
            'vidjet.göstərici(etiket: "Disk", dəyər: 72, yuxarı: 80)'),
    Məlumat("qiymətKartı", GÖSTƏRMƏ, "Qiymət planı kartı",
            'vidjet.qiymətKartı(plan: "Pro", qiymət: "19 ₼",\n'
            '                   xüsusiyyətlər: ["10 layihə", "Dəstək"],\n'
            '                   klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    // dəyər — plan adı\n'
            'son'),
    Məlumat("xüsusiyyətSiyahısı", GÖSTƏRMƏ, "İşarəli xüsusiyyət siyahısı",
            'vidjet.xüsusiyyətSiyahısı(elementlər: ["Sürətli", "Pulsuz"])'),
    Məlumat("rəy", GÖSTƏRMƏ, "Müştəri rəyi (testimonial)",
            'vidjet.rəy(mətn: "Çox rahatdır!", ad: "Aysel Əliyeva",\n'
            '           vəzifə: "Dizayner", reytinqi: 5)'),
    Məlumat("qəhrəman", GÖSTƏRMƏ, "Böyük giriş bölməsi (hero)",
            'vidjet.qəhrəman(başlıq: "Alqor ilə proqramlaşdır",\n'
            '                altMətn: "Azərbaycan dilində",\n'
            '                hərəkətlər: [vidjet.düymə(mətn: "Başla")])'),
    Məlumat("səhifəAltlığı", GÖSTƏRMƏ, "Səhifə altlığı (footer)",
            'vidjet.səhifəAltlığı(mətn: "© 2026 Alqor",\n'
            '                     keçidlər: [["/haqqında", "Haqqında"]])'),
    Məlumat("qeydQutusu", GÖSTƏRMƏ, "Diqqət çəkən qeyd (callout)",
            'vidjet.qeydQutusu(başlıq: "Məsləhət",\n'
            '                  mətn: "Ctrl+S ilə saxlayın")'),
    Məlumat("elanZolağı", GÖSTƏRMƏ, "Səhifə üstü elan zolağı (banner)",
            'vidjet.elanZolağı(mətn: "Yeni versiya çıxıb!",\n'
            '                  növ: "məlumat")', ["bağlandı"]),
    Məlumat("təqvim", GÖSTƏRMƏ, "Aylıq təqvim",
            'vidjet.təqvim(il: 2026, ayı: 10, seçili: özü.{ad},\n'
            '              klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    // gün: "2026-10-07"; ay keçidi: "2026-11"\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = ""'),
    Məlumat("sütunQrafiki", GÖSTƏRMƏ, "Sütun qrafiki (bar chart)",
            'vidjet.sütunQrafiki(başlıq: "Satış",\n'
            '                    dəyərlər: [12, 19, 7, 15],\n'
            '                    etiketlər: ["Y", "F", "M", "A"])'),
    Məlumat("xəttQrafiki", GÖSTƏRMƏ, "Xətt qrafiki (line chart)",
            'vidjet.xəttQrafiki(başlıq: "Ziyarət",\n'
            '                   dəyərlər: [3, 8, 5, 12, 9],\n'
            '                   etiketlər: ["B.e", "Ç.a", "Ç", "C.a", "C"])'),
    Məlumat("dairəQrafiki", GÖSTƏRMƏ, "Dairə qrafiki (pie / donut)",
            'vidjet.dairəQrafiki(dəyərlər: [50, 30, 20],\n'
            '                    etiketlər: ["Veb", "Mobil", "Desktop"])'),
    Məlumat("kiçikQrafik", GÖSTƏRMƏ, "Kiçik xətt qrafiki (sparkline)",
            'vidjet.kiçikQrafik(dəyərlər: [3, 5, 4, 8, 6, 9])'),
    Məlumat("video", GÖSTƏRMƏ, "Video oynadıcı",
            'vidjet.video(mənbə: "/media/təqdimat.mp4")'),
    Məlumat("audio", GÖSTƏRMƏ, "Audio oynadıcı",
            'vidjet.audio(mənbə: "/media/mahnı.mp3")'),
    Məlumat("yerləşdirmə", GÖSTƏRMƏ, "Xarici məzmun (embed, iframe)",
            'vidjet.yerləşdirmə(ünvan: "https://www.openstreetmap.org/'
            'export/embed.html", nisbət: "16/9")'),
    Məlumat("qalereya", GÖSTƏRMƏ, "Şəkil qalereyası",
            'vidjet.qalereya(şəkillər: ["/şəkil/1.jpg", "/şəkil/2.jpg",\n'
            '                           "/şəkil/3.jpg"], sütunlar: 3)'),
    Məlumat("karusel", GÖSTƏRMƏ, "Slayd göstəricisi (carousel)",
            'vidjet.karusel(slaydlar: [["/şəkil/1.jpg", "Bakı"],\n'
            '                          ["/şəkil/2.jpg", "Şəki"]],\n'
            '               cari: özü.{ad}, klik: özü.{ad}Keç)',
            ["klik"],
            'metod {ad}Keç(dəyər: mətn)\n'
            '    özü.{ad} = tamƏt(dəyər, 0)\n'
            'son', 'vəziyyət {ad}: tam = 0'),
    Məlumat("işarəliMətn", GÖSTƏRMƏ, "Markdown işarələməli mətn",
            'vidjet.işarəliMətn(mətn: "## Başlıq\\n\\n**Qalın** mətn")'),
    Məlumat("profilKartı", GÖSTƏRMƏ, "Profil kartı",
            'vidjet.profilKartı(ad: "Aysel Əliyeva", vəzifə: "Proqramçı",\n'
            '                   statistika: {"Layihə": 12, "İzləyici": 340})'),
    Məlumat("bildirişNişanı", GÖSTƏRMƏ, "Saylı bildiriş ikonu",
            'vidjet.bildirişNişanı(say: özü.{ad}, klik: özü.{ad}Aç)',
            ["klik"],
            'metod {ad}Aç()\n'
            '    özü.{ad} = 0\n'
            'son', 'vəziyyət {ad}: tam = 3'),

    # ── Vəziyyət ──
    Məlumat("yüklənməÖrtüyü", VƏZİYYƏT, "Məzmunun üstündə yüklənmə",
            'vidjet.yüklənməÖrtüyü(yüklənir: özü.{ad}, məzmun: [])',
            [], '', 'vəziyyət {ad}: məntiq = doğru'),
    Məlumat("nəticə", VƏZİYYƏT, "Nəticə səhifəsi (uğur, xəta, 404)",
            'vidjet.nəticə(növ: "uğur", başlıq: "Sifariş qəbul olundu",\n'
            '              mətn: "Təşəkkür edirik!")'),
    Məlumat("şifrəGücü", VƏZİYYƏT, "Şifrənin gücü göstəricisi",
            'vidjet.şifrəGücü(şifrə: özü.{ad})',
            [], '', 'vəziyyət {ad}: mətn = ""'),

    # ── Düzülüş ──
    Məlumat("konteyner", DÜZÜLÜŞ, "Mərkəzlənmiş en məhdud qab",
            'vidjet.konteyner(en: 960, məzmun: [])'),
    Məlumat("mərkəz", DÜZÜLÜŞ, "Məzmunu ortaya qoyur",
            'vidjet.mərkəz(hündürlük: 200, məzmun: [])'),
    Məlumat("ikiSütun", DÜZÜLÜŞ, "İki sütunlu düzülüş (split)",
            'vidjet.ikiSütun(nisbət: "1:2", sol: [], sağ: [])'),
    Məlumat("nisbət", DÜZÜLÜŞ, "Sabit en/hündürlük nisbəti",
            'vidjet.nisbət(forma: "16/9", məzmun: [])'),
    Məlumat("sürüşmə", DÜZÜLÜŞ, "Sürüşən sahə (scroll area)",
            'vidjet.sürüşmə(hündürlük: 240, məzmun: [])'),
    Məlumat("tətbiqQabığı", DÜZÜLÜŞ, "Tətbiq skeleti: başlıq, yan, məzmun",
            'vidjet.tətbiqQabığı(başlıq: vidjet.başlıq(mətn: "Tətbiq"),\n'
            '                    yan: [], məzmun: [])'),

    # ── Naviqasiya ──
    Məlumat("yanNaviqasiya", NAVİQASİYA, "Yan menyu (sidebar)",
            'vidjet.yanNaviqasiya(elementlər: ["Ana", "Hesabatlar",\n'
            '                                  "Ayarlar"],\n'
            '                     cari: özü.{ad}, klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son', 'vəziyyət {ad}: mətn = "Ana"'),
    Məlumat("alətlərPaneli", NAVİQASİYA, "Alətlər paneli (toolbar)",
            'vidjet.alətlərPaneli(məzmun: [\n'
            '    vidjet.ikonDüymə(ikon: "B", başlıq: "Qalın"),\n'
            '    vidjet.ikonDüymə(ikon: "I", başlıq: "Maili")\n'
            '])'),

    # ── Üst qat ──
    Məlumat("açılanPanel", ÜST_QAT, "Açılan panel (popover)",
            'vidjet.açılanPanel(düymə: "Filtr", məzmun: [])'),
    Məlumat("təsdiqDialoqu", ÜST_QAT, "Təsdiq dialoqu",
            'vidjet.təsdiqDialoqu(başlıq: "Silinsin?",\n'
            '                     mətn: "Bu əməl geri qaytarılmır.",\n'
            '                     görünür: özü.{ad}, təhlükəli: doğru,\n'
            '                     təsdiqləndi: özü.{ad}Bəli,\n'
            '                     ləğvEdildi: özü.{ad}Xeyr)',
            ["təsdiqləndi", "ləğvEdildi"],
            'metod {ad}Bəli()\n'
            '    özü.{ad} = yanlış\n'
            '    // silmə əməli\n'
            'son\n\n'
            'metod {ad}Xeyr()\n'
            '    özü.{ad} = yanlış\n'
            'son', 'vəziyyət {ad}: məntiq = yanlış'),
    Məlumat("altVərəq", ÜST_QAT, "Aşağıdan açılan panel (bottom sheet)",
            'vidjet.altVərəq(başlıq: "Paylaş", görünür: özü.{ad},\n'
            '                bağlandı: özü.{ad}Bağla, məzmun: [])',
            ["bağlandı"],
            'metod {ad}Bağla()\n'
            '    özü.{ad} = yanlış\n'
            'son', 'vəziyyət {ad}: məntiq = yanlış'),
]

ƏLAVƏ_ADLAR: dict[str, str] = {
    "reytinq": "Rating", "seqmentli": "Segmented Control",
    "çipSeçimi": "Chip Select", "teqSahəsi": "Tag Input",
    "təsdiqKodu": "OTP Input", "telefon": "Phone Field",
    "ePoçt": "Email Field", "keçidSahəsi": "URL Field",
    "pulSahəsi": "Currency Field", "tarixAralığı": "Date Range Picker",
    "tarixVaxt": "Date Time Picker", "ay": "Month Picker",
    "sayğac": "Number Stepper", "avtoTamamlama": "Autocomplete",
    "faylSürüklə": "Dropzone", "keçidDüyməsi": "Toggle Button",
    "açılanMenyu": "Dropdown Menu", "bölünmüşDüymə": "Split Button",
    "üzənDüymə": "Floating Action Button",
    "çip": "Chip", "ikon": "Icon", "klaviş": "Kbd",
    "vaxtXətti": "Timeline", "ağac": "Tree View",
    "siyahıQrupu": "List Group", "avatarQrupu": "Avatar Group",
    "göstərici": "Meter", "qiymətKartı": "Pricing Card",
    "xüsusiyyətSiyahısı": "Feature List", "rəy": "Testimonial",
    "qəhrəman": "Hero", "səhifəAltlığı": "Footer",
    "qeydQutusu": "Callout", "elanZolağı": "Banner",
    "təqvim": "Calendar", "sütunQrafiki": "Bar Chart",
    "xəttQrafiki": "Line Chart", "dairəQrafiki": "Pie Chart",
    "kiçikQrafik": "Sparkline", "video": "Video", "audio": "Audio",
    "yerləşdirmə": "Embed", "qalereya": "Image Gallery",
    "karusel": "Carousel", "işarəliMətn": "Markdown",
    "profilKartı": "Profile Card", "bildirişNişanı": "Notification Badge",
    "yüklənməÖrtüyü": "Loading Overlay", "nəticə": "Result",
    "şifrəGücü": "Password Strength",
    "konteyner": "Container", "mərkəz": "Center",
    "ikiSütun": "Split Layout", "nisbət": "Aspect Ratio",
    "sürüşmə": "Scroll Area", "tətbiqQabığı": "App Shell",
    "yanNaviqasiya": "Sidebar Nav", "alətlərPaneli": "Toolbar",
    "açılanPanel": "Popover", "təsdiqDialoqu": "Confirm Dialog",
    "altVərəq": "Bottom Sheet",
}

ƏLAVƏLƏR: dict = {m.ad: globals()[m.ad] for m in ƏLAVƏ_KATALOQ}

ƏLAVƏ_ÜSLUB = """
/* ═══ Əlavə elementlər ═══ */
.v-sönük{color:var(--v-sönük)}
.v-aralıq-ayırıcı{color:var(--v-sönük)}
.v-açılan-panel{vertical-align:top}
.v-keçid-düyməsi{transition:background .15s}
.v-elan-zolağı--məlumat,.v-qeyd-qutusu--məlumat,.v-nəticə--uğur,.v-şifrə-gücü--0{}
/* Reytinq */
.v-reytinq{display:inline-flex;gap:2px}
.v-ulduz{border:0;background:none;font-size:22px;line-height:1;padding:0 1px;
 cursor:pointer;color:var(--v-kənar)}
.v-ulduz--dolu{color:#f5a524}
.v-ulduz[disabled]{cursor:default}
/* Seqmentli */
.v-seqmentli{display:inline-flex;padding:3px;gap:2px;border-radius:var(--v-radius);
 background:var(--v-üst);border:1px solid var(--v-kənar)}
.v-seqment{border:0;background:none;font:inherit;padding:5px 14px;border-radius:6px;
 cursor:pointer;color:var(--v-sönük)}
.v-seqment--seçili{background:var(--v-fon);color:var(--v-mətn);box-shadow:var(--v-kölgə)}
/* Çiplər */
.v-çiplər{display:flex;flex-wrap:wrap;gap:6px}
.v-çip{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;
 border-radius:999px;border:1px solid var(--v-kənar);background:var(--v-üst);
 color:var(--v-mətn);font:inherit;font-size:.9em}
button.v-çip{cursor:pointer}
.v-çip--seçili,.v-çip--əsas{background:var(--v-vurgu);color:var(--v-vurgu-mətn);border-color:transparent}
.v-çip--uğur{background:var(--v-uğur);color:#fff;border-color:transparent}
.v-çip--təhlükə{background:var(--v-təhlükə);color:#fff;border-color:transparent}
.v-çip--xəbərdarlıq{background:var(--v-xəbərdarlıq);color:#fff;border-color:transparent}
.v-çip-sil{border:0;background:none;color:inherit;cursor:pointer;padding:0 0 0 2px;opacity:.7}
.v-çip-sil:hover{opacity:1}
.v-teq-sahəsi{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:6px 8px;
 border:1px solid var(--v-kənar);border-radius:var(--v-radius);background:var(--v-fon)}
.v-teq-girişi{flex:1;min-width:120px;border:0;outline:0;background:none;color:inherit;font:inherit}
/* OTP */
.v-kod-girişi{letter-spacing:.6em;font-family:ui-monospace,Consolas,monospace;
 font-size:1.25em;text-align:center;max-width:calc(var(--uzunluq,6) * 1.9em)}
/* Əlavəli giriş */
.v-giriş-qrupu{display:flex;align-items:stretch}
.v-giriş-qrupu .v-giriş{flex:1;min-width:0}
.v-giriş-qrupu .v-giriş:not(:first-child){border-top-left-radius:0;border-bottom-left-radius:0}
.v-giriş-qrupu .v-giriş:not(:last-child){border-top-right-radius:0;border-bottom-right-radius:0}
.v-giriş-əlavəsi{display:flex;align-items:center;padding:0 10px;background:var(--v-üst);
 border:1px solid var(--v-kənar);color:var(--v-sönük)}
.v-giriş-əlavəsi:first-child{border-right:0;border-radius:var(--v-radius) 0 0 var(--v-radius)}
.v-giriş-əlavəsi:last-child{border-left:0;border-radius:0 var(--v-radius) var(--v-radius) 0}
.v-aralıq{display:flex;align-items:center;gap:8px}
.v-aralıq .v-giriş{flex:1;min-width:0}
/* Sayğac */
.v-sayğac{align-self:flex-start;display:inline-flex;align-items:stretch;border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);overflow:hidden}
.v-sayğac-düyməsi{border:0;background:var(--v-üst);color:var(--v-mətn);font:inherit;
 width:36px;font-size:18px;cursor:pointer}
.v-sayğac-düyməsi[disabled]{opacity:.4;cursor:not-allowed}
.v-sayğac-dəyəri{min-width:48px;display:flex;align-items:center;justify-content:center;
 font-variant-numeric:tabular-nums;background:var(--v-fon)}
/* Dropzone */
.v-sürüklə-sahəsi{display:flex;flex-direction:column;align-items:center;gap:4px;
 padding:22px;border:2px dashed var(--v-kənar);border-radius:var(--v-radius);
 cursor:pointer;text-align:center;background:var(--v-fon)}
.v-sürüklə-sahəsi:hover{border-color:var(--v-vurgu)}
.v-sürüklə-sahəsi input{position:absolute;opacity:0;width:1px;height:1px}
.v-sürüklə-ikonu{font-size:26px;color:var(--v-vurgu)}
/* Toggle */
.v-keçid-düyməsi--basılı{background:var(--v-vurgu);color:var(--v-vurgu-mətn);border-color:transparent}
/* Açılan menyu */
.v-açılan{position:relative;display:inline-block}
.v-açılan>summary{list-style:none}
.v-açılan>summary::-webkit-details-marker{display:none}
.v-ox{margin-left:6px;font-size:.8em;opacity:.7}
.v-açılan-menyu{position:absolute;z-index:20;top:calc(100% + 4px);left:0;min-width:180px;
 padding:4px;background:var(--v-fon);border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);box-shadow:0 8px 24px rgba(0,0,0,.15);
 display:flex;flex-direction:column}
.v-menyu-elementi{border:0;background:none;color:inherit;font:inherit;text-align:left;
 padding:7px 10px;border-radius:6px;cursor:pointer}
.v-menyu-elementi:hover{background:var(--v-üst)}
.v-bölünmüş-düymə{display:inline-flex}
.v-bölünmüş-düymə>.v-düymə{border-top-right-radius:0;border-bottom-right-radius:0}
.v-bölünmüş-ox{border-top-left-radius:0;border-bottom-left-radius:0;padding:8px 10px;
 border-left:1px solid rgba(255,255,255,.35)}
/* FAB */
.v-üzən-düymə{position:fixed;bottom:24px;width:56px;height:56px;border-radius:50%;border:0;
 background:var(--v-vurgu);color:var(--v-vurgu-mətn);font-size:26px;cursor:pointer;
 box-shadow:0 6px 18px rgba(0,0,0,.25);z-index:30}
.v-üzən-düymə--sağ{right:24px}.v-üzən-düymə--sol{left:24px}
/* İkon, klaviş */
.v-ikon-tək{display:inline-flex;line-height:1}
.v-klavişlər{display:inline-flex;align-items:center;gap:3px}
.v-klaviş{font:12px ui-monospace,Consolas,monospace;padding:2px 6px;border-radius:5px;
 border:1px solid var(--v-kənar);border-bottom-width:2px;background:var(--v-üst)}
.v-klaviş-ayırıcı{color:var(--v-sönük);font-size:.85em}
/* Vaxt xətti */
.v-vaxt-xətti{list-style:none;margin:0;padding:0 0 0 18px;border-left:2px solid var(--v-kənar)}
.v-vaxt-nöqtəsi{position:relative;padding:0 0 14px 6px}
.v-vaxt-nöqtəsi::before{content:"";position:absolute;left:-25px;top:4px;width:10px;height:10px;
 border-radius:50%;background:var(--v-vurgu);border:2px solid var(--v-fon)}
.v-vaxt-tarixi{display:block;font-size:.8em;color:var(--v-sönük)}
.v-vaxt-nöqtəsi p{margin:2px 0 0}
/* Ağac */
.v-ağac{list-style:none;margin:0;padding-left:14px}
.v-ağac:first-child{padding-left:0}
.v-ağac summary{cursor:pointer;padding:2px 0}
.v-ağac-elementi{border:0;background:none;color:inherit;font:inherit;padding:2px 4px;
 border-radius:4px;cursor:pointer;text-align:left}
.v-ağac-elementi:hover{background:var(--v-üst)}
/* Siyahı qrupu */
.v-siyahı-qrupu{display:flex;flex-direction:column;border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);overflow:hidden}
.v-siyahı-qrupu-elementi{display:grid;grid-template-columns:1fr auto;gap:0 8px;
 padding:10px 14px;border:0;border-top:1px solid var(--v-kənar);background:var(--v-fon);
 color:inherit;font:inherit;text-align:left}
.v-siyahı-qrupu-elementi:first-child{border-top:0}
button.v-siyahı-qrupu-elementi{cursor:pointer}
button.v-siyahı-qrupu-elementi:hover{background:var(--v-üst)}
.v-siyahı-qrupu-elementi--seçili{box-shadow:inset 3px 0 0 var(--v-vurgu);background:var(--v-üst)}
.v-siyahı-qrupu-elementi .v-sönük{grid-column:1;font-size:.88em}
.v-sq-ox{grid-row:1/span 2;grid-column:2;align-self:center;color:var(--v-sönük)}
/* Avatar qrupu */
.v-avatar-qrupu{display:inline-flex}
.v-avatar-qrupu>*{margin-left:-8px;box-shadow:0 0 0 2px var(--v-fon)}
.v-avatar-qrupu>:first-child{margin-left:0}
.v-avatar-artıq{background:var(--v-üst);color:var(--v-sönük)}
/* Meter */
.v-göstərici meter{width:100%;height:12px}
/* Qiymət kartı */
.v-qiymət-kartı{display:flex;flex-direction:column;gap:10px;padding:20px;
 border:1px solid var(--v-kənar);border-radius:12px;background:var(--v-fon)}
.v-qiymət-kartı--seçilmiş{border:2px solid var(--v-vurgu)}
.v-qiymət-planı{margin:0;font-size:1em;color:var(--v-sönük)}
.v-qiymət{margin:0;font-size:2em;font-weight:700}
.v-qiymət .v-sönük{font-size:.45em;font-weight:400}
.v-xüsusiyyət-siyahısı{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.v-xs-işarə{color:var(--v-uğur);margin-right:8px;font-weight:700}
/* Rəy */
.v-rəy{margin:0;padding:18px;border:1px solid var(--v-kənar);border-radius:12px;
 background:var(--v-fon);display:flex;flex-direction:column;gap:10px}
.v-rəy-mətni{margin:0;font-size:1.05em}
.v-rəy-mətni::before{content:"“";font-size:2em;line-height:0;vertical-align:-.35em;
 color:var(--v-vurgu);margin-right:4px}
.v-rəy-müəllif{display:flex;align-items:center;gap:10px}
.v-rəy-müəllif>span{display:flex;flex-direction:column}
/* Hero */
.v-qəhrəman{padding:48px 24px;display:flex;flex-direction:column;gap:14px}
.v-qəhrəman--mərkəz{align-items:center;text-align:center}
.v-qəhrəman-başlığı{margin:0;font-size:2.4em;line-height:1.15}
.v-qəhrəman-mətni{margin:0;font-size:1.15em;color:var(--v-sönük);max-width:640px}
.v-qəhrəman-hərəkətləri{display:flex;gap:10px;flex-wrap:wrap}
/* Footer */
.v-səhifə-altlığı{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;
 padding:18px 0;border-top:1px solid var(--v-kənar)}
.v-altlıq-keçidləri{display:flex;gap:16px}
.v-altlıq-keçidləri a{color:var(--v-sönük);text-decoration:none}
.v-altlıq-keçidləri a:hover{color:var(--v-vurgu)}
/* Callout */
.v-qeyd-qutusu{display:flex;gap:12px;padding:12px 14px;border-radius:var(--v-radius);
 border-left:4px solid var(--q-rəng,var(--v-vurgu));background:var(--v-üst)}
.v-qeyd-qutusu p{margin:2px 0 0}
.v-qeyd-ikonu{font-size:1.2em;color:var(--q-rəng,var(--v-vurgu))}
.v-qeyd-qutusu--uğur{--q-rəng:var(--v-uğur)}
.v-qeyd-qutusu--xəbərdarlıq{--q-rəng:var(--v-xəbərdarlıq)}
.v-qeyd-qutusu--təhlükə{--q-rəng:var(--v-təhlükə)}
/* Banner */
.v-elan-zolağı{display:flex;align-items:center;justify-content:center;gap:12px;
 padding:8px 14px;background:var(--v-vurgu);color:var(--v-vurgu-mətn)}
.v-elan-zolağı--uğur{background:var(--v-uğur)}
.v-elan-zolağı--xəbərdarlıq{background:var(--v-xəbərdarlıq)}
.v-elan-zolağı--təhlükə{background:var(--v-təhlükə)}
.v-elan-zolağı .v-modal-bağla{color:inherit}
/* Təqvim */
.v-təqvim{display:inline-block;padding:10px;border:1px solid var(--v-kənar);
 border-radius:12px;background:var(--v-fon)}
.v-təqvim-başı{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.v-təqvim-ox{border:0;background:none;color:inherit;font-size:20px;cursor:pointer;
 width:30px;border-radius:6px}
.v-təqvim-ox:hover{background:var(--v-üst)}
.v-təqvim table{border-collapse:collapse}
.v-təqvim th{font-size:.75em;color:var(--v-sönük);font-weight:500;padding:4px}
.v-təqvim td{padding:1px;text-align:center}
.v-gün{width:34px;height:34px;border:0;border-radius:50%;background:none;color:inherit;
 font:inherit;cursor:pointer;position:relative}
.v-gün:hover{background:var(--v-üst)}
.v-gün--seçili{background:var(--v-vurgu);color:var(--v-vurgu-mətn)}
.v-gün--qeydli::after{content:"";position:absolute;bottom:4px;left:50%;width:4px;height:4px;
 margin-left:-2px;border-radius:50%;background:var(--v-təhlükə)}
/* Qrafiklər */
.v-qrafik-qabı{margin:0;display:flex;flex-direction:column;gap:6px}
.v-qrafik-başlığı{font-weight:600}
.v-qrafik{width:100%;max-height:260px;overflow:visible}
.v-q-mətn{font-size:10px;text-anchor:middle;fill:var(--v-sönük)}
.v-q1,.v-qf1{fill:#3b82f6;background:#3b82f6}.v-q2,.v-qf2{fill:#10b981;background:#10b981}
.v-q3,.v-qf3{fill:#f59e0b;background:#f59e0b}.v-q4,.v-qf4{fill:#ef4444;background:#ef4444}
.v-q5,.v-qf5{fill:#8b5cf6;background:#8b5cf6}.v-q6,.v-qf6{fill:#06b6d4;background:#06b6d4}
.v-q-xətt{fill:none;stroke:var(--v-vurgu);stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
.v-q-sahə{fill:var(--v-vurgu);opacity:.12}
.v-q-nöqtə{fill:var(--v-fon);stroke:var(--v-vurgu);stroke-width:2}
.v-əfsanə{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.85em}
.v-əfsanə-elementi{display:inline-flex;align-items:center;gap:6px}
.v-əfsanə-rəngi{width:10px;height:10px;border-radius:3px;display:inline-block}
.v-kiçik-qrafik{vertical-align:middle}
/* Media */
.v-video{width:100%;border-radius:var(--v-radius);background:#000}
.v-audio{width:100%}
.v-yerləşdirmə{width:100%;border-radius:var(--v-radius);overflow:hidden;border:1px solid var(--v-kənar)}
.v-yerləşdirmə iframe{width:100%;height:100%;border:0;display:block}
.v-qalereya{display:grid;grid-template-columns:repeat(var(--sütunlar,3),1fr);gap:8px}
.v-qalereya-elementi{padding:0;border:0;background:var(--v-üst);border-radius:var(--v-radius);
 overflow:hidden;aspect-ratio:1;display:block}
.v-qalereya-elementi img{width:100%;height:100%;object-fit:cover;display:block}
button.v-qalereya-elementi{cursor:zoom-in}
.v-karusel{position:relative;border-radius:12px;overflow:hidden;background:var(--v-üst);aspect-ratio:16/9}
.v-slayd{position:absolute;inset:0}
.v-slayd img{width:100%;height:100%;object-fit:cover;display:block}
.v-slayd-başlığı{position:absolute;left:0;right:0;bottom:0;padding:24px 16px 28px;color:#fff;
 font-weight:600;background:linear-gradient(transparent,rgba(0,0,0,.6))}
.v-karusel-ox{position:absolute;top:50%;transform:translateY(-50%);width:36px;height:36px;
 border-radius:50%;border:0;background:rgba(255,255,255,.85);color:#111;font-size:22px;cursor:pointer}
.v-karusel-ox--sol{left:10px}.v-karusel-ox--sağ{right:10px}
.v-karusel-nöqtələri{position:absolute;bottom:8px;left:0;right:0;display:flex;justify-content:center;gap:6px}
.v-karusel-nöqtə{width:8px;height:8px;border-radius:50%;border:0;padding:0;
 background:rgba(255,255,255,.55);cursor:pointer}
.v-karusel-nöqtə--cari{background:#fff;width:20px;border-radius:4px}
.v-markdown>:first-child{margin-top:0}
.v-markdown pre{background:var(--v-üst);padding:10px;border-radius:6px;overflow:auto}
.v-markdown code{font-family:ui-monospace,Consolas,monospace}
/* Profil */
.v-profil-kartı{display:flex;flex-direction:column;align-items:center;gap:6px;padding:22px;
 border:1px solid var(--v-kənar);border-radius:12px;background:var(--v-fon);text-align:center}
.v-profil-kartı h3,.v-profil-kartı p{margin:0}
.v-profil-statistikası{display:flex;gap:22px;margin-top:6px}
.v-profil-statistikası>div{display:flex;flex-direction:column}
.v-profil-hərəkətləri{display:flex;gap:8px;margin-top:8px}
/* Bildiriş nişanı */
.v-bildiriş-nişanı{position:relative;border:0;background:none;font-size:22px;cursor:pointer;
 padding:4px 6px;color:inherit}
.v-say-nişanı{position:absolute;top:-2px;right:-4px;min-width:18px;height:18px;padding:0 5px;
 border-radius:9px;background:var(--v-təhlükə);color:#fff;font-size:11px;line-height:18px;font-weight:700}
/* Yüklənmə örtüyü */
.v-yüklənmə-qabı{position:relative;min-height:60px}
.v-yüklənmə-örtüyü{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
 gap:10px;background:color-mix(in srgb,var(--v-fon) 75%,transparent);border-radius:var(--v-radius)}
/* Nəticə */
.v-nəticə{display:flex;flex-direction:column;align-items:center;text-align:center;gap:8px;padding:32px 16px}
.v-nəticə h2,.v-nəticə p{margin:0}
.v-nəticə-ikonu{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;
 justify-content:center;font-size:30px;font-weight:700;color:#fff;background:var(--n-rəng,var(--v-uğur))}
.v-nəticə--təhlükə{--n-rəng:var(--v-təhlükə)}.v-nəticə--xəbərdarlıq{--n-rəng:var(--v-xəbərdarlıq)}
.v-nəticə--məlumat{--n-rəng:var(--v-vurgu)}
.v-nəticə--404 .v-nəticə-ikonu{width:auto;height:auto;border-radius:0;background:none;
 color:var(--v-sönük);font-size:56px}
.v-nəticə-hərəkətləri{display:flex;gap:8px;margin-top:6px}
/* Şifrə gücü */
.v-şifrə-gücü{display:flex;align-items:center;gap:10px}
.v-şg-zolaqlar{display:flex;gap:4px;flex:1}
.v-şg-zolaqlar span{flex:1;height:6px;border-radius:3px;background:var(--v-kənar)}
.v-şifrə-gücü--1 .v-şg-zolaqlar span:nth-child(-n+1){background:var(--v-təhlükə)}
.v-şifrə-gücü--2 .v-şg-zolaqlar span:nth-child(-n+2){background:var(--v-xəbərdarlıq)}
.v-şifrə-gücü--3 .v-şg-zolaqlar span{background:var(--v-uğur)}
.v-şg-mətn{font-size:.85em;color:var(--v-sönük);min-width:44px}
/* Düzülüş */
.v-konteyner{margin:0 auto;width:100%;padding:0 16px}
.v-mərkəz{display:flex;align-items:center;justify-content:center;text-align:center}
.v-iki-sütun{display:grid;align-items:start}
@media (max-width:640px){.v-iki-sütun{grid-template-columns:1fr!important}}
.v-nisbət{width:100%;overflow:hidden;border-radius:var(--v-radius)}
.v-nisbət>*{width:100%;height:100%;object-fit:cover}
.v-sürüşmə{overflow:auto;border:1px solid var(--v-kənar);border-radius:var(--v-radius);padding:8px}
.v-tətbiq-qabığı{display:grid;grid-template-columns:220px 1fr;grid-template-rows:auto 1fr auto;
 min-height:320px;border:1px solid var(--v-kənar);border-radius:var(--v-radius);overflow:hidden}
.v-tq-başlıq{grid-column:1/-1;padding:10px 16px;border-bottom:1px solid var(--v-kənar);background:var(--v-üst)}
.v-tq-başlıq>*{margin:0}
.v-tq-yan{padding:10px;border-right:1px solid var(--v-kənar);background:var(--v-üst)}
.v-tq-məzmun{padding:16px;min-width:0}
.v-tq-altlıq{grid-column:1/-1;padding:8px 16px;border-top:1px solid var(--v-kənar);color:var(--v-sönük)}
/* Yan naviqasiya */
.v-yan-naviqasiya{display:flex;flex-direction:column;gap:2px;min-width:180px}
.v-yn-başlıq{font-size:.75em;text-transform:uppercase;letter-spacing:.05em;color:var(--v-sönük);padding:6px 10px}
.v-yn-element{border:0;background:none;color:inherit;font:inherit;text-align:left;
 padding:8px 10px;border-radius:6px;cursor:pointer}
.v-yn-element:hover{background:var(--v-üst)}
.v-yn-element--cari{background:var(--v-vurgu);color:var(--v-vurgu-mətn)}
/* Toolbar */
.v-alətlər-paneli{display:flex;align-items:center;gap:4px;padding:4px;border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);background:var(--v-üst)}
/* Popover */
.v-açılan-panel-gövdəsi{padding:12px;min-width:220px}
/* Təsdiq dialoqu */
.v-dialoq-düymələri{display:flex;justify-content:flex-end;gap:8px}
/* Alt vərəq */
.v-alt-vərəq{position:fixed;left:0;right:0;bottom:0;max-height:80vh;overflow:auto;
 background:var(--v-fon);border-radius:16px 16px 0 0;padding:6px 16px 16px;
 box-shadow:0 -8px 30px rgba(0,0,0,.25)}
.v-alt-vərəq-tutacaq{width:40px;height:4px;border-radius:2px;background:var(--v-kənar);margin:4px auto 6px}
"""
