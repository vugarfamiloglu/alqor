"""
Alqor — `vidjet` modulu: hazır interfeys elementləri.

Spesifikasiya § 14. Xarici asılılıq yoxdur.

BİR MƏNBƏ, İKİ HƏDƏF
────────────────────
Hər vidjet `Element` qaytarır — yəni JSX ağacı. Həmin ağacı həm `veb`
modulu (brauzerə HTML kimi), həm də `pəncərə` modulu (desktop
pəncərəsinə) göstərir. Deməli eyni form, eyni cədvəl, eyni tərəqqi
çubuğu hər iki hədəfdə işləyir — ayrı kod yazmaq lazım deyil.

    gətir vidjet

    funksiya əsas()
        dəyişən p = yeni pəncərə.Pəncərə("Qeydiyyat")
        p.məzmun(vidjet.form(məzmun: [
            vidjet.sahə(etiket: "Ad", ad: "ad"),
            vidjet.parol(etiket: "Şifrə", ad: "şifrə"),
            vidjet.düymə(mətn: "Göndər", növ: "əsas")
        ]))
        p.göstər()
        pəncərə.işlət()
    son

ÜSLUB
─────
`pəncərə` modulu vidjet üslubunu özü əlavə edir. Vebdə `<head>` daxilinə
`vidjet.üslublar()` qoyulur, ya da bütün səhifə `vidjet.səhifə(...)` ilə
qurulur.

IDE ÜÇÜN KATALOQ
────────────────
`vidjet.kataloq()` hər vidjetin adını, kateqoriyasını, parametrlərini,
hadisələrini və **kod skeletini** qaytarır. Alqor Studio bunu
oxuyur: paletdən element əlavə edilir, üzərinə iki dəfə klikləndikdə
`vidjet.skelet(ad)` qaytardığı kod redaktora yazılır və element
dərhal işləyən vəziyyətə gəlir.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .deyerler import AlqorXəta, Element, Nümunə, mətnə

# ═══════════════════════════════════════════════════════════════════════
#  Köməkçilər
# ═══════════════════════════════════════════════════════════════════════

# Vidjet sinifləri `v-` prefiksi ilə başlayır ki, istifadəçinin öz
# CSS-i ilə toqquşmasın.
P = "v-"


def _E(teq: str, atributlar: dict[str, Any] | None = None,
       uşaqlar: Any = None) -> Element:
    """Element qurur; `boş` atributları atır."""
    atr = {a: d for a, d in (atributlar or {}).items() if d is not None}
    return Element(teq, atr, _uşaqlar(uşaqlar))


def _uşaqlar(d: Any) -> list:
    if d is None:
        return []
    if isinstance(d, (list, tuple)):
        nəticə: list = []
        for u in d:
            if u is None or u is False:
                continue
            nəticə.append(u)
        return nəticə
    return [d]


FORM_TEQLƏRİ = frozenset({"input", "select", "textarea"})


def _nişanla(kök: Element, etiket_mətni: str) -> Element:
    """
    Ağacdaki birinci form elementinə `data-a-ad` yazır. Sınaq
    sürücüsü və IDE elementi görünən etiketinə görə tapa bilsin.
    """
    if not etiket_mətni:
        return kök
    hədəf = _ilk_form_elementi(kök)
    if hədəf is not None:
        hədəf.atributlar.setdefault("data-a-ad", etiket_mətni)
    return kök


def _ilk_form_elementi(e: Any) -> Element | None:
    if not isinstance(e, Element):
        return None
    if e.ad in FORM_TEQLƏRİ:
        return e
    for u in e.uşaqlar:
        nəticə = _ilk_form_elementi(u)
        if nəticə is not None:
            return nəticə
    return None


def _sinif(*hissələr: Any) -> str:
    """`v-düymə v-düymə--əsas` kimi əlavəSinif sətri qurur."""
    toplu: list[str] = []
    for h in hissələr:
        if not h:
            continue
        toplu.extend(str(h).split())
    return " ".join(dict.fromkeys(toplu))


def _m(dəyər: Any, icraçı: Any = None, standart: str = "") -> str:
    if dəyər is None:
        return standart
    if isinstance(dəyər, str):
        return dəyər
    return mətnə(dəyər, icraçı)


def _say(dəyər: Any, standart: float = 0.0) -> float:
    if isinstance(dəyər, bool) or dəyər is None:
        return standart
    if isinstance(dəyər, (int, float)):
        return float(dəyər)
    try:
        return float(str(dəyər).replace(",", "."))
    except ValueError:
        return standart


def _sətirlər(d: Any, icraçı: Any = None) -> list[str]:
    if d is None:
        return []
    if isinstance(d, (list, tuple, set)):
        return [_m(u, icraçı) for u in d]
    return [_m(d, icraçı)]


def _lüğət(d: Any) -> dict:
    """Lüğət, nümunə və ya cüt siyahısını lüğətə çevirir."""
    if d is None:
        return {}
    if isinstance(d, dict):
        return {str(a): b for a, b in d.items()}
    if isinstance(d, Nümunə):
        return dict(d.sahələr)
    if isinstance(d, (list, tuple)):
        nəticə = {}
        for u in d:
            if isinstance(u, (list, tuple)) and len(u) >= 2:
                nəticə[str(u[0])] = u[1]
        return nəticə
    raise AlqorXəta("TipXətası",
                    "lüğət və ya cüt siyahısı gözlənilir",
                    kod="ALQ-T004")


def _seçimlər(d: Any, icraçı: Any = None) -> list[tuple[str, str]]:
    """
    Seçim siyahısı üç formada verilə bilər:
        ["a", "b"]                       dəyər = etiket
        {"az": "Azərbaycan"}             dəyər → etiket
        [["az", "Azərbaycan"]]           cütlər
    """
    if d is None:
        return []
    if isinstance(d, dict):
        return [(str(a), _m(b, icraçı)) for a, b in d.items()]
    if isinstance(d, (list, tuple)):
        nəticə: list[tuple[str, str]] = []
        for u in d:
            if isinstance(u, (list, tuple)) and len(u) >= 2:
                nəticə.append((_m(u[0], icraçı), _m(u[1], icraçı)))
            else:
                mətn = _m(u, icraçı)
                nəticə.append((mətn, mətn))
        return nəticə
    mətn = _m(d, icraçı)
    return [(mətn, mətn)]


def _ölçü(dəyər: Any) -> str | None:
    """`16` → `16px`, `"2rem"` → `"2rem"`."""
    if dəyər is None:
        return None
    if isinstance(dəyər, bool):
        return None
    if isinstance(dəyər, (int, float)):
        return f"{dəyər:g}px"
    return str(dəyər)


# ═══════════════════════════════════════════════════════════════════════
#  Düymələr və hərəkət
# ═══════════════════════════════════════════════════════════════════════

NÖVLƏR = ("əsas", "ikinci", "sakit", "təhlükə", "uğur", "xəbərdarlıq",
          "əlaqə")
ÖLÇÜLƏR = ("kiçik", "orta", "böyük")


def _növü_yoxla(növ: str, icazəli: tuple[str, ...], sahə: str) -> str:
    if növ not in icazəli:
        raise AlqorXəta(
            "ArqumentXətası",
            f"`{sahə}` sahəsi `{növ}` yoxdur. İcazəli: "
            f"{', '.join(icazəli)}", kod="ALQ-R013")
    return növ


def düymə(icraçı, mətn: Any = "", klik: Any = None, növ: Any = "əsas",
          ölçü: Any = "orta", söndürülmüş: Any = False,
          gözləyir: Any = False, tamEn: Any = False, ikon: Any = None,
          kimlik: Any = None, əlavəSinif: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "əsas"), NÖVLƏR, "düymə növü")
    ö = _növü_yoxla(_m(ölçü, icraçı, "orta"), ÖLÇÜLƏR, "düymə ölçüsü")
    uşaqlar: list = []
    if gözləyir:
        uşaqlar.append(_E("span", {"class": f"{P}fırlanan {P}fırlanan--kiçik"}))
    elif ikon is not None:
        uşaqlar.append(_E("span", {"class": f"{P}ikon"}, _m(ikon, icraçı)))
    uşaqlar.append(_m(mətn, icraçı))
    return _E("button", {
        "class": _sinif(f"{P}düymə", f"{P}düymə--{n}", f"{P}düymə--{ö}",
                        f"{P}düymə--tamEn" if tamEn else None, əlavəSinif),
        "type": "button",
        "id": _m(kimlik, icraçı) or None,
        "disabled": True if (söndürülmüş or gözləyir) else None,
        "klik": None if (söndürülmüş or gözləyir) else klik,
    }, uşaqlar)


def ikonDüymə(icraçı, ikon: Any = "", klik: Any = None,
              başlıq: Any = None, növ: Any = "sakit",
              söndürülmüş: Any = False, kimlik: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "sakit"), NÖVLƏR, "düymə növü")
    return _E("button", {
        "class": _sinif(f"{P}düymə", f"{P}düymə--{n}", f"{P}düymə--ikon"),
        "type": "button",
        "title": _m(başlıq, icraçı) or None,
        "id": _m(kimlik, icraçı) or None,
        "disabled": True if söndürülmüş else None,
        "klik": None if söndürülmüş else klik,
    }, _m(ikon, icraçı))


def düyməQrupu(icraçı, məzmun: Any = None) -> Element:
    return _E("div", {"class": f"{P}düymə-qrupu"}, məzmun)


def əlaqə(icraçı, mətn: Any = "", ünvan: Any = "#", klik: Any = None,
          yeniNişan: Any = False) -> Element:
    return _E("a", {
        "class": f"{P}əlaqə",
        "href": _m(ünvan, icraçı, "#"),
        "target": "_blank" if yeniNişan else None,
        "rel": "noopener noreferrer" if yeniNişan else None,
        "klik": klik,
    }, _m(mətn, icraçı))


# ═══════════════════════════════════════════════════════════════════════
#  Form sahələri
# ═══════════════════════════════════════════════════════════════════════

def _sahə_çərçivəsi(icraçı, daxili: Element, etiket: Any, ad: Any,
                    kömək: Any, xəta: Any, tələb: Any) -> Element:
    uşaqlar: list = []
    kimlik = _m(ad, icraçı) or None
    if etiket is not None and _m(etiket, icraçı):
        uşaqlar.append(_E("label", {
            "class": f"{P}etiket", "for": kimlik,
        }, [_m(etiket, icraçı)] + (
            [_E("span", {"class": f"{P}tələb"}, "*")] if tələb else [])))
    uşaqlar.append(daxili)
    if xəta is not None and _m(xəta, icraçı):
        uşaqlar.append(_E("p", {"class": f"{P}xəta-mətni"},
                          _m(xəta, icraçı)))
    elif kömək is not None and _m(kömək, icraçı):
        uşaqlar.append(_E("p", {"class": f"{P}kömək"}, _m(kömək, icraçı)))
    return _nişanla(_E("div", {
        "class": _sinif(f"{P}sahə", f"{P}sahə--xətalı" if xəta else None),
    }, uşaqlar), _m(etiket, icraçı))


def _giriş(icraçı, HTML_növü: str, ad, dəyər, yer, dəyişdi, yazıldı,
           söndürülmüş, oxunaqlı, tələb, xəta, əlavə=None) -> Element:
    atr: dict[str, Any] = {
        "class": _sinif(f"{P}giriş",
                        f"{P}giriş--xətalı" if xəta else None),
        "type": HTML_növü,
        "id": _m(ad, icraçı) or None,
        "name": _m(ad, icraçı) or None,
        "value": _m(dəyər, icraçı) if dəyər is not None else None,
        "placeholder": _m(yer, icraçı) or None,
        "disabled": True if söndürülmüş else None,
        "readonly": True if oxunaqlı else None,
        "required": True if tələb else None,
        "dəyişdi": dəyişdi,
        "yazıldı": yazıldı,
    }
    atr.update(əlavə or {})
    return _E("input", atr)


def sahə(icraçı, etiket: Any = None, ad: Any = "", dəyər: Any = None,
         yer: Any = None, kömək: Any = None, xəta: Any = None,
         dəyişdi: Any = None, yazıldı: Any = None, tələb: Any = False,
         söndürülmüş: Any = False, oxunaqlı: Any = False) -> Element:
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "text", ad, dəyər, yer, dəyişdi, yazıldı,
               söndürülmüş, oxunaqlı, tələb, xəta),
        etiket, ad, kömək, xəta, tələb)


def parol(icraçı, etiket: Any = None, ad: Any = "şifrə",
          yer: Any = None, kömək: Any = None, xəta: Any = None,
          dəyişdi: Any = None, tələb: Any = False,
          söndürülmüş: Any = False) -> Element:
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "password", ad, None, yer, dəyişdi, None,
               söndürülmüş, False, tələb, xəta,
               {"autocomplete": "current-password"}),
        etiket, ad, kömək, xəta, tələb)


def ədəd(icraçı, etiket: Any = None, ad: Any = "", dəyər: Any = None,
         minimum: Any = None, maksimum: Any = None, pillə: Any = None,
         kömək: Any = None, xəta: Any = None, dəyişdi: Any = None,
         tələb: Any = False, söndürülmüş: Any = False) -> Element:
    əlavə: dict[str, Any] = {}
    if minimum is not None:
        əlavə["min"] = f"{_say(minimum):g}"
    if maksimum is not None:
        əlavə["max"] = f"{_say(maksimum):g}"
    if pillə is not None:
        əlavə["step"] = f"{_say(pillə, 1):g}"
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "number", ad, dəyər, None, dəyişdi, None,
               söndürülmüş, False, tələb, xəta, əlavə),
        etiket, ad, kömək, xəta, tələb)


def axtarış(icraçı, ad: Any = "axtarış", yer: Any = "Axtar…",
            dəyər: Any = None, yazıldı: Any = None,
            göndərildi: Any = None) -> Element:
    return _E("form", {
        "class": f"{P}axtarış", "göndərildi": göndərildi,
    }, [
        _E("span", {"class": f"{P}axtarış-ikonu"}, "⌕"),
        _giriş(icraçı, "search", ad, dəyər, yer, None, yazıldı,
               False, False, False, None),
    ])


def çoxsətirli(icraçı, etiket: Any = None, ad: Any = "",
               dəyər: Any = None, yer: Any = None, sətirlər: Any = 4,
               kömək: Any = None, xəta: Any = None, dəyişdi: Any = None,
               tələb: Any = False, söndürülmüş: Any = False) -> Element:
    daxili = _E("textarea", {
        "class": _sinif(f"{P}giriş", f"{P}çoxsətirli",
                        f"{P}giriş--xətalı" if xəta else None),
        "id": _m(ad, icraçı) or None,
        "name": _m(ad, icraçı) or None,
        "rows": f"{int(_say(sətirlər, 4))}",
        "placeholder": _m(yer, icraçı) or None,
        "disabled": True if söndürülmüş else None,
        "required": True if tələb else None,
        "dəyişdi": dəyişdi,
    }, _m(dəyər, icraçı) if dəyər is not None else None)
    return _sahə_çərçivəsi(icraçı, daxili, etiket, ad, kömək, xəta, tələb)


def seçim(icraçı, etiket: Any = None, ad: Any = "",
          seçimlər: Any = None, dəyər: Any = None, kömək: Any = None,
          xəta: Any = None, dəyişdi: Any = None, tələb: Any = False,
          söndürülmüş: Any = False, boşEtiket: Any = None) -> Element:
    cari = _m(dəyər, icraçı) if dəyər is not None else None
    variantlar: list = []
    if boşEtiket is not None:
        variantlar.append(_E("option", {"value": ""},
                             _m(boşEtiket, icraçı)))
    for d, e in _seçimlər(seçimlər, icraçı):
        variantlar.append(_E("option", {
            "value": d, "selected": True if d == cari else None,
        }, e))
    daxili = _E("select", {
        "class": _sinif(f"{P}giriş", f"{P}seçim",
                        f"{P}giriş--xətalı" if xəta else None),
        "id": _m(ad, icraçı) or None,
        "name": _m(ad, icraçı) or None,
        "disabled": True if söndürülmüş else None,
        "required": True if tələb else None,
        "dəyişdi": dəyişdi,
    }, variantlar)
    return _sahə_çərçivəsi(icraçı, daxili, etiket, ad, kömək, xəta, tələb)


def qeyd(icraçı, etiket: Any = "", ad: Any = "",
         işarələnmiş: Any = False, dəyişdi: Any = None,
         söndürülmüş: Any = False, kömək: Any = None) -> Element:
    sıra = _nişanla(_E("label", {"class": f"{P}qeyd"}, [
        _E("input", {
            "type": "checkbox",
            "id": _m(ad, icraçı) or None,
            "name": _m(ad, icraçı) or None,
            "checked": True if işarələnmiş else None,
            "disabled": True if söndürülmüş else None,
            "dəyişdi": dəyişdi,
        }),
        _E("span", {"class": f"{P}qeyd-mətni"}, _m(etiket, icraçı)),
    ]), _m(etiket, icraçı))
    if kömək is None:
        return sıra
    return _E("div", {"class": f"{P}sahə"}, [
        sıra, _E("p", {"class": f"{P}kömək"}, _m(kömək, icraçı))])


def açar(icraçı, etiket: Any = "", ad: Any = "", yanıq: Any = False,
         dəyişdi: Any = None, söndürülmüş: Any = False) -> Element:
    return _nişanla(_E("label", {
        "class": _sinif(f"{P}açar", f"{P}açar--sönük" if söndürülmüş
                        else None),
    }, [
        _E("input", {
            "type": "checkbox",
            "id": _m(ad, icraçı) or None,
            "name": _m(ad, icraçı) or None,
            "checked": True if yanıq else None,
            "disabled": True if söndürülmüş else None,
            "dəyişdi": dəyişdi,
        }),
        _E("span", {"class": f"{P}açar-yolu"}, [
            _E("span", {"class": f"{P}açar-topu"})]),
        _E("span", {"class": f"{P}açar-mətni"}, _m(etiket, icraçı)),
    ]), _m(etiket, icraçı))


def radioQrupu(icraçı, etiket: Any = None, ad: Any = "",
               seçimlər: Any = None, dəyər: Any = None,
               dəyişdi: Any = None, üfüqi: Any = False,
               kömək: Any = None, xəta: Any = None) -> Element:
    cari = _m(dəyər, icraçı) if dəyər is not None else None
    sıra: list = []
    qrup = _m(ad, icraçı)
    for i, (d, e) in enumerate(_seçimlər(seçimlər, icraçı)):
        sıra.append(_nişanla(_E("label", {"class": f"{P}radio"}, [
            _E("input", {
                "type": "radio",
                "id": f"{qrup}-{i}" if qrup else None,
                "name": qrup or None,
                "value": d,
                "checked": True if d == cari else None,
                "dəyişdi": dəyişdi,
            }),
            _E("span", {"class": f"{P}radio-mətni"}, e),
        ]), e))
    daxili = _E("div", {
        "class": _sinif(f"{P}radio-qrupu",
                        f"{P}radio-qrupu--üfüqi" if üfüqi else None),
    }, sıra)
    return _sahə_çərçivəsi(icraçı, daxili, etiket, None, kömək, xəta,
                           False)


def sürüşdürücü(icraçı, etiket: Any = None, ad: Any = "",
                dəyər: Any = 0, minimum: Any = 0, maksimum: Any = 100,
                pillə: Any = 1, dəyişdi: Any = None,
                dəyəriGöstər: Any = True,
                söndürülmüş: Any = False) -> Element:
    d = _say(dəyər)
    daxili: list = [_E("input", {
        "class": f"{P}sürüşdürücü",
        "type": "range",
        "id": _m(ad, icraçı) or None,
        "name": _m(ad, icraçı) or None,
        "min": f"{_say(minimum):g}",
        "max": f"{_say(maksimum, 100):g}",
        "step": f"{_say(pillə, 1):g}",
        "value": f"{d:g}",
        "disabled": True if söndürülmüş else None,
        "dəyişdi": dəyişdi,
        "yazıldı": dəyişdi,
    })]
    if dəyəriGöstər:
        daxili.append(_E("output", {"class": f"{P}sürüşdürücü-dəyəri"},
                         f"{d:g}"))
    return _sahə_çərçivəsi(
        icraçı, _E("div", {"class": f"{P}sürüşdürücü-sırası"}, daxili),
        etiket, ad, None, None, False)


def tarix(icraçı, etiket: Any = None, ad: Any = "tarix",
          dəyər: Any = None, minimum: Any = None, maksimum: Any = None,
          dəyişdi: Any = None, tələb: Any = False,
          söndürülmüş: Any = False) -> Element:
    əlavə: dict[str, Any] = {}
    if minimum is not None:
        əlavə["min"] = _m(minimum, icraçı)
    if maksimum is not None:
        əlavə["max"] = _m(maksimum, icraçı)
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "date", ad, dəyər, None, dəyişdi, None,
               söndürülmüş, False, tələb, None, əlavə),
        etiket, ad, None, None, tələb)


def vaxt(icraçı, etiket: Any = None, ad: Any = "vaxt",
         dəyər: Any = None, dəyişdi: Any = None,
         söndürülmüş: Any = False) -> Element:
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "time", ad, dəyər, None, dəyişdi, None,
               söndürülmüş, False, False, None),
        etiket, ad, None, None, False)


def rəng(icraçı, etiket: Any = None, ad: Any = "rəng",
         dəyər: Any = "#3366cc", dəyişdi: Any = None) -> Element:
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "color", ad, dəyər, None, dəyişdi, None,
               False, False, False, None),
        etiket, ad, None, None, False)


def faylSahəsi(icraçı, etiket: Any = None, ad: Any = "fayl",
               növlər: Any = None, çoxlu: Any = False,
               dəyişdi: Any = None, kömək: Any = None) -> Element:
    əlavə: dict[str, Any] = {}
    if növlər is not None:
        əlavə["accept"] = ",".join(_sətirlər(növlər, icraçı))
    if çoxlu:
        əlavə["multiple"] = True
    return _sahə_çərçivəsi(
        icraçı,
        _giriş(icraçı, "file", ad, None, None, dəyişdi, None,
               False, False, False, None, əlavə),
        etiket, ad, kömək, None, False)


def form(icraçı, məzmun: Any = None, göndərildi: Any = None,
         başlıq: Any = None, sıx: Any = False) -> Element:
    uşaqlar: list = []
    if başlıq is not None and _m(başlıq, icraçı):
        uşaqlar.append(_E("h2", {"class": f"{P}form-başlığı"},
                          _m(başlıq, icraçı)))
    uşaqlar.extend(_uşaqlar(məzmun))
    return _E("form", {
        "class": _sinif(f"{P}form", f"{P}form--sıx" if sıx else None),
        "göndərildi": göndərildi,
    }, uşaqlar)


def sahəDəsti(icraçı, başlıq: Any = "", məzmun: Any = None) -> Element:
    uşaqlar: list = []
    if _m(başlıq, icraçı):
        uşaqlar.append(_E("legend", {"class": f"{P}sahə-dəsti-başlığı"},
                          _m(başlıq, icraçı)))
    uşaqlar.extend(_uşaqlar(məzmun))
    return _E("fieldset", {"class": f"{P}sahə-dəsti"}, uşaqlar)


def etiket(icraçı, mətn: Any = "", sahəsi: Any = None) -> Element:
    return _E("label", {
        "class": f"{P}etiket", "for": _m(sahəsi, icraçı) or None,
    }, _m(mətn, icraçı))


# ═══════════════════════════════════════════════════════════════════════
#  Göstərmə
# ═══════════════════════════════════════════════════════════════════════

def başlıq(icraçı, mətn: Any = "", səviyyə: Any = 1,
           altMətn: Any = None) -> Element:
    n = int(_say(səviyyə, 1))
    n = 1 if n < 1 else (6 if n > 6 else n)
    baş = _E(f"h{n}", {"class": f"{P}başlıq"}, _m(mətn, icraçı))
    if altMətn is None:
        return baş
    return _E("div", {"class": f"{P}başlıq-qrupu"}, [
        baş, _E("p", {"class": f"{P}alt-mətn"}, _m(altMətn, icraçı))])


def mətn(icraçı, məzmun: Any = "", sönük: Any = False,
         ölçü: Any = None, qalın: Any = False) -> Element:
    return _E("p", {
        "class": _sinif(f"{P}mətn", f"{P}mətn--sönük" if sönük else None,
                        f"{P}mətn--qalın" if qalın else None,
                        f"{P}mətn--{_m(ölçü, icraçı)}" if ölçü else None),
    }, _m(məzmun, icraçı))


def nişan(icraçı, mətn: Any = "", növ: Any = "ikinci") -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "ikinci"), NÖVLƏR, "nişan növü")
    return _E("span", {
        "class": _sinif(f"{P}nişan", f"{P}nişan--{n}"),
    }, _m(mətn, icraçı))


def xəbərdarlıq(icraçı, mətn: Any = "", növ: Any = "xəbərdarlıq",
                başlıq: Any = None, bağlana: Any = False,
                bağlandı: Any = None) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "xəbərdarlıq"),
                    ("uğur", "xəbərdarlıq", "təhlükə", "məlumat"),
                    "xəbərdarlıq növü")
    işarələr = {"uğur": "✓", "xəbərdarlıq": "!", "təhlükə": "✕",
                "məlumat": "i"}
    daxili: list = [_E("span", {"class": f"{P}xəbərdarlıq-ikonu"},
                       işarələr[n])]
    gövdə: list = []
    if başlıq is not None and _m(başlıq, icraçı):
        gövdə.append(_E("strong", {"class": f"{P}xəbərdarlıq-başlığı"},
                        _m(başlıq, icraçı)))
    gövdə.append(_E("span", {}, _m(mətn, icraçı)))
    daxili.append(_E("div", {"class": f"{P}xəbərdarlıq-gövdəsi"}, gövdə))
    if bağlana:
        daxili.append(_E("button", {
            "class": f"{P}xəbərdarlıq-bağla", "type": "button",
            "title": "Bağla", "klik": bağlandı,
        }, "✕"))
    return _E("div", {
        "class": _sinif(f"{P}xəbərdarlıq", f"{P}xəbərdarlıq--{n}"),
        "role": "alert",
    }, daxili)


def kart(icraçı, başlıq: Any = None, məzmun: Any = None,
         altlıq: Any = None, altMətn: Any = None,
         klik: Any = None) -> Element:
    uşaqlar: list = []
    if başlıq is not None and _m(başlıq, icraçı):
        baş: list = [_E("h3", {"class": f"{P}kart-başlığı"},
                        _m(başlıq, icraçı))]
        if altMətn is not None:
            baş.append(_E("p", {"class": f"{P}alt-mətn"},
                          _m(altMətn, icraçı)))
        uşaqlar.append(_E("div", {"class": f"{P}kart-başı"}, baş))
    uşaqlar.append(_E("div", {"class": f"{P}kart-gövdəsi"}, məzmun))
    if altlıq is not None:
        uşaqlar.append(_E("div", {"class": f"{P}kart-altlığı"}, altlıq))
    return _E("div", {
        "class": _sinif(f"{P}kart", f"{P}kart--basılan" if klik else None),
        "klik": klik,
    }, uşaqlar)


def cədvəl(icraçı, sütunlar: Any = None, sətirlər: Any = None,
           boşMətn: Any = "Məlumat yoxdur", zolaqlı: Any = True,
           çərçivəli: Any = False, sətirKlik: Any = None) -> Element:
    """
    `sütunlar` — başlıqlar: `["Ad", "Yaş"]` və ya
    `[["ad", "Ad"], ["yaş", "Yaş"]]` (açar → başlıq).
    `sətirlər` — siyahı siyahısı, lüğət siyahısı və ya nümunə siyahısı.
    """
    sütun_cütləri = _seçimlər(sütunlar, icraçı)
    baş = _E("thead", {}, _E("tr", {}, [
        _E("th", {}, e) for _, e in sütun_cütləri]))

    gövdə_sətirləri: list = []
    for sətir in _uşaqlar(sətirlər):
        hücrələr: list = []
        if isinstance(sətir, (list, tuple)):
            dəyərlər = list(sətir)
        else:
            qeyd_ = _lüğət(sətir)
            dəyərlər = [qeyd_.get(a) for a, _ in sütun_cütləri]
        for d in dəyərlər:
            hücrələr.append(_E("td", {}, d if isinstance(d, Element)
                               else _m(d, icraçı)))
        gövdə_sətirləri.append(_E("tr", {
            "class": f"{P}sətir--basılan" if sətirKlik else None,
            "klik": sətirKlik,
        }, hücrələr))

    if not gövdə_sətirləri:
        gövdə_sətirləri.append(_E("tr", {}, _E("td", {
            "class": f"{P}cədvəl-boş",
            "colspan": str(max(1, len(sütun_cütləri))),
        }, _m(boşMətn, icraçı))))

    return _E("div", {"class": f"{P}cədvəl-qabı"}, _E("table", {
        "class": _sinif(f"{P}cədvəl",
                        f"{P}cədvəl--zolaqlı" if zolaqlı else None,
                        f"{P}cədvəl--çərçivəli" if çərçivəli else None),
    }, [baş, _E("tbody", {}, gövdə_sətirləri)]))


def siyahı(icraçı, elementlər: Any = None, nömrəli: Any = False,
           işarəsiz: Any = False) -> Element:
    uşaqlar = [u if isinstance(u, Element) and u.ad == "li"
               else _E("li", {}, u if isinstance(u, Element)
                       else _m(u, icraçı))
               for u in _uşaqlar(elementlər)]
    return _E("ol" if nömrəli else "ul", {
        "class": _sinif(f"{P}siyahı",
                        f"{P}siyahı--işarəsiz" if işarəsiz else None),
    }, uşaqlar)


def təsvirSiyahısı(icraçı, cütlər: Any = None) -> Element:
    uşaqlar: list = []
    for a, d in _lüğət(cütlər).items():
        uşaqlar.append(_E("dt", {}, a))
        uşaqlar.append(_E("dd", {}, d if isinstance(d, Element)
                          else _m(d, icraçı)))
    return _E("dl", {"class": f"{P}təsvir-siyahısı"}, uşaqlar)


def kod(icraçı, məzmun: Any = "", dil: Any = None) -> Element:
    return _E("pre", {
        "class": f"{P}kod", "data-dil": _m(dil, icraçı) or None,
    }, _E("code", {}, _m(məzmun, icraçı)))


def sitat(icraçı, mətn: Any = "", mənbə: Any = None) -> Element:
    uşaqlar: list = [_E("p", {}, _m(mətn, icraçı))]
    if mənbə is not None:
        uşaqlar.append(_E("footer", {"class": f"{P}sitat-mənbəyi"},
                          _m(mənbə, icraçı)))
    return _E("blockquote", {"class": f"{P}sitat"}, uşaqlar)


def şəkil(icraçı, mənbə: Any = "", alternativ: Any = "",
          en: Any = None, hündürlük: Any = None,
          yuvarlaq: Any = False) -> Element:
    return _E("img", {
        "class": _sinif(f"{P}şəkil",
                        f"{P}şəkil--yuvarlaq" if yuvarlaq else None),
        "src": _m(mənbə, icraçı),
        "alt": _m(alternativ, icraçı),
        "width": _ölçü(en),
        "height": _ölçü(hündürlük),
        "loading": "lazy",
    })


def avatar(icraçı, ad: Any = "", mənbə: Any = None,
           ölçü: Any = "orta") -> Element:
    ö = _növü_yoxla(_m(ölçü, icraçı, "orta"), ÖLÇÜLƏR, "avatar ölçüsü")
    əlavəSinif = _sinif(f"{P}avatar", f"{P}avatar--{ö}")
    if mənbə is not None and _m(mənbə, icraçı):
        return _E("img", {
            "class": əlavəSinif, "src": _m(mənbə, icraçı),
            "alt": _m(ad, icraçı),
        })
    hərflər = "".join(s[0] for s in _m(ad, icraçı).split()[:2])
    from .elifba import böyüyə
    return _E("span", {"class": əlavəSinif, "title": _m(ad, icraçı) or None},
              böyüyə(hərflər) if hərflər else "?")


def ayırıcı(icraçı, mətn: Any = None) -> Element:
    if mətn is None or not _m(mətn, icraçı):
        return _E("hr", {"class": f"{P}ayırıcı"})
    return _E("div", {"class": f"{P}ayırıcı-mətnli"},
              _E("span", {}, _m(mətn, icraçı)))


def boşBaxış(icraçı, başlıq: Any = "Heç nə yoxdur",
             mətn: Any = None, ikon: Any = "○",
             hərəkət: Any = None) -> Element:
    uşaqlar: list = [
        _E("div", {"class": f"{P}boş-ikonu"}, _m(ikon, icraçı)),
        _E("h3", {}, _m(başlıq, icraçı)),
    ]
    if mətn is not None:
        uşaqlar.append(_E("p", {"class": f"{P}mətn {P}mətn--sönük"},
                          _m(mətn, icraçı)))
    if hərəkət is not None:
        uşaqlar.append(hərəkət)
    return _E("div", {"class": f"{P}boş-baxış"}, uşaqlar)


# ═══════════════════════════════════════════════════════════════════════
#  Vəziyyət göstəriciləri
# ═══════════════════════════════════════════════════════════════════════

def tərəqqi(icraçı, dəyər: Any = 0, maksimum: Any = 100,
            etiket: Any = None, faizGöstər: Any = True,
            növ: Any = "əsas", qeyriMüəyyən: Any = False) -> Element:
    n = _növü_yoxla(_m(növ, icraçı, "əsas"), NÖVLƏR, "tərəqqi növü")
    maks = _say(maksimum, 100) or 100
    d = _say(dəyər)
    d = 0.0 if d < 0 else (maks if d > maks else d)
    faiz = 0.0 if qeyriMüəyyən else (d / maks * 100)

    üst: list = []
    if etiket is not None and _m(etiket, icraçı):
        üst.append(_E("span", {"class": f"{P}tərəqqi-etiketi"},
                       _m(etiket, icraçı)))
    if faizGöstər and not qeyriMüəyyən:
        üst.append(_E("span", {"class": f"{P}tərəqqi-faizi"},
                       f"{faiz:.0f}%"))

    uşaqlar: list = []
    if üst:
        uşaqlar.append(_E("div", {"class": f"{P}tərəqqi-başı"}, üst))
    uşaqlar.append(_E("div", {
        "class": _sinif(f"{P}tərəqqi-yolu",
                        f"{P}tərəqqi-yolu--qeyri-müəyyən"
                        if qeyriMüəyyən else None),
        "role": "progressbar",
        "aria-valuenow": None if qeyriMüəyyən else f"{d:g}",
        "aria-valuemax": f"{maks:g}",
    }, _E("div", {
        "class": _sinif(f"{P}tərəqqi-dolğusu", f"{P}tərəqqi-dolğusu--{n}"),
        "style": None if qeyriMüəyyən else f"width:{faiz:.2f}%",
    })))
    return _E("div", {"class": f"{P}tərəqqi"}, uşaqlar)


def halqaTərəqqi(icraçı, dəyər: Any = 0, maksimum: Any = 100,
                 ölçü: Any = 64, mətn: Any = None) -> Element:
    maks = _say(maksimum, 100) or 100
    d = _say(dəyər)
    d = 0.0 if d < 0 else (maks if d > maks else d)
    faiz = d / maks * 100
    ö = int(_say(ölçü, 64))
    return _E("div", {
        "class": f"{P}halqa",
        "style": (f"--v-halqa-ölçü:{ö}px;"
                  f"--v-halqa-faiz:{faiz:.2f}"),
        "role": "progressbar",
    }, _E("span", {"class": f"{P}halqa-mətni"},
          _m(mətn, icraçı) if mətn is not None else f"{faiz:.0f}%"))


def fırlanan(icraçı, ölçü: Any = "orta", mətn: Any = None) -> Element:
    ö = _növü_yoxla(_m(ölçü, icraçı, "orta"), ÖLÇÜLƏR, "fırlanan ölçüsü")
    çarx = _E("span", {
        "class": _sinif(f"{P}fırlanan", f"{P}fırlanan--{ö}"),
        "role": "status",
    })
    if mətn is None:
        return çarx
    return _E("div", {"class": f"{P}fırlanan-qrupu"},
              [çarx, _E("span", {}, _m(mətn, icraçı))])


def skeletYüklənmə(icraçı, sətirlər: Any = 3,
                   en: Any = None) -> Element:
    n = max(1, int(_say(sətirlər, 3)))
    uşaqlar = [_E("span", {
        "class": f"{P}skelet-sətri",
        "style": f"width:{_ölçü(en)}" if en is not None else None,
    }) for _ in range(n)]
    return _E("div", {"class": f"{P}skelet"}, uşaqlar)


def statistika(icraçı, etiket: Any = "", dəyər: Any = "",
               dəyişmə: Any = None, ikon: Any = None) -> Element:
    uşaqlar: list = []
    if ikon is not None:
        uşaqlar.append(_E("span", {"class": f"{P}statistika-ikonu"},
                          _m(ikon, icraçı)))
    daxili: list = [
        _E("span", {"class": f"{P}statistika-etiketi"},
           _m(etiket, icraçı)),
        _E("strong", {"class": f"{P}statistika-dəyəri"},
           _m(dəyər, icraçı)),
    ]
    if dəyişmə is not None:
        d = _say(dəyişmə)
        işarə = "▲" if d > 0 else ("▼" if d < 0 else "■")
        əlavəSinif = "artıb" if d > 0 else ("azalıb" if d < 0 else "sabit")
        daxili.append(_E("span", {
            "class": _sinif(f"{P}statistika-dəyişməsi",
                            f"{P}statistika-dəyişməsi--{əlavəSinif}"),
        }, f"{işarə} {abs(d):g}%"))
    uşaqlar.append(_E("div", {}, daxili))
    return _E("div", {"class": f"{P}statistika"}, uşaqlar)


# ═══════════════════════════════════════════════════════════════════════
#  Düzülüş
# ═══════════════════════════════════════════════════════════════════════

def qutu(icraçı, məzmun: Any = None, boşluq: Any = None,
         kənar: Any = False, fon: Any = None,
         kimlik: Any = None) -> Element:
    üslub: list[str] = []
    if boşluq is not None:
        üslub.append(f"padding:{_ölçü(boşluq)}")
    if fon is not None:
        üslub.append(f"background:{_m(fon, icraçı)}")
    return _E("div", {
        "class": _sinif(f"{P}qutu", f"{P}qutu--kənarlı" if kənar else None),
        "id": _m(kimlik, icraçı) or None,
        "style": ";".join(üslub) or None,
    }, məzmun)


def sətir(icraçı, məzmun: Any = None, boşluq: Any = 8,
          düzləndir: Any = "başlanğıc", şaquli: Any = "mərkəz",
          sarı: Any = True) -> Element:
    return _E("div", {
        "class": _sinif(f"{P}sətir", f"{P}sətir--sarı" if sarı else None),
        "style": (f"gap:{_ölçü(boşluq)};"
                  f"justify-content:{_DÜZLƏNDİRMƏ.get(
                      _m(düzləndir, icraçı), 'flex-start')};"
                  f"align-items:{_DÜZLƏNDİRMƏ.get(
                      _m(şaquli, icraçı), 'center')}"),
    }, məzmun)


def sütun(icraçı, məzmun: Any = None, boşluq: Any = 8,
          düzləndir: Any = "dolu") -> Element:
    # Standart `dolu`: şaquli yığında uşaqlar (naviqasiya, cədvəl, form)
    # tam eni tutur. `başlanğıc` onları məzmun enində saxlayırdı.
    return _E("div", {
        "class": f"{P}sütun",
        "style": (f"gap:{_ölçü(boşluq)};"
                  f"align-items:{_DÜZLƏNDİRMƏ.get(
                      _m(düzləndir, icraçı), 'stretch')}"),
    }, məzmun)


_DÜZLƏNDİRMƏ = {
    "başlanğıc": "flex-start", "mərkəz": "center", "son": "flex-end",
    "ara": "space-between", "ətraf": "space-around",
    "dolu": "stretch", "bərabər": "space-evenly",
}


def tor(icraçı, məzmun: Any = None, sütunlar: Any = 2,
        boşluq: Any = 12, minimum: Any = None) -> Element:
    if minimum is not None:
        şablon = (f"repeat(auto-fill,minmax({_ölçü(minimum)},1fr))")
    else:
        şablon = f"repeat({max(1, int(_say(sütunlar, 2)))},1fr)"
    return _E("div", {
        "class": f"{P}tor",
        "style": f"grid-template-columns:{şablon};gap:{_ölçü(boşluq)}",
    }, məzmun)


def boşluq(icraçı, hündürlük: Any = 16) -> Element:
    return _E("div", {
        "class": f"{P}boşluq",
        "style": f"height:{_ölçü(hündürlük)}",
    })


def panel(icraçı, başlıq: Any = None, məzmun: Any = None,
          alətlər: Any = None) -> Element:
    uşaqlar: list = []
    if başlıq is not None or alətlər is not None:
        baş: list = []
        if başlıq is not None:
            baş.append(_E("h3", {"class": f"{P}panel-başlığı"},
                          _m(başlıq, icraçı)))
        if alətlər is not None:
            baş.append(_E("div", {"class": f"{P}panel-alətləri"},
                          alətlər))
        uşaqlar.append(_E("div", {"class": f"{P}panel-başı"}, baş))
    uşaqlar.append(_E("div", {"class": f"{P}panel-gövdəsi"}, məzmun))
    return _E("section", {"class": f"{P}panel"}, uşaqlar)


def bölmə(icraçı, başlıq: Any = None, məzmun: Any = None,
          altMətn: Any = None) -> Element:
    uşaqlar: list = []
    if başlıq is not None:
        uşaqlar.append(_E("h2", {"class": f"{P}bölmə-başlığı"},
                          _m(başlıq, icraçı)))
    if altMətn is not None:
        uşaqlar.append(_E("p", {"class": f"{P}alt-mətn"},
                          _m(altMətn, icraçı)))
    uşaqlar.extend(_uşaqlar(məzmun))
    return _E("section", {"class": f"{P}bölmə"}, uşaqlar)


# ═══════════════════════════════════════════════════════════════════════
#  Naviqasiya
# ═══════════════════════════════════════════════════════════════════════

def naviqasiya(icraçı, başlıq: Any = "", elementlər: Any = None,
               sağ: Any = None) -> Element:
    uşaqlar: list = []
    if _m(başlıq, icraçı):
        uşaqlar.append(_E("strong", {"class": f"{P}nav-başlığı"},
                          _m(başlıq, icraçı)))
    if elementlər is not None:
        uşaqlar.append(_E("div", {"class": f"{P}nav-elementləri"},
                          elementlər))
    if sağ is not None:
        uşaqlar.append(_E("div", {"class": f"{P}nav-sağ"}, sağ))
    return _E("nav", {"class": f"{P}nav"}, uşaqlar)


def nişanlar(icraçı, elementlər: Any = None, cari: Any = None,
             klik: Any = None, məzmun: Any = None) -> Element:
    cütlər = _seçimlər(elementlər, icraçı)
    seçili = _m(cari, icraçı) if cari is not None else (
        cütlər[0][0] if cütlər else "")
    düymələr = [_E("button", {
        "class": _sinif(f"{P}nişan-düyməsi",
                        f"{P}nişan-düyməsi--seçili" if d == seçili
                        else None),
        "type": "button",
        "value": d,
        "role": "tab",
        "klik": klik,
    }, e) for d, e in cütlər]
    uşaqlar: list = [_E("div", {"class": f"{P}nişan-sətri", "role": "tablist"},
                        düymələr)]
    if məzmun is not None:
        uşaqlar.append(_E("div", {"class": f"{P}nişan-gövdəsi"}, məzmun))
    return _E("div", {"class": f"{P}nişanlar"}, uşaqlar)


def yığcam(icraçı, başlıq: Any = "", məzmun: Any = None,
           açılmış: Any = False) -> Element:
    return _E("details", {
        "class": f"{P}yığcam", "open": True if açılmış else None,
    }, [
        _E("summary", {"class": f"{P}yığcam-başlığı"},
           _m(başlıq, icraçı)),
        _E("div", {"class": f"{P}yığcam-gövdəsi"}, məzmun),
    ])


def səhifələmə(icraçı, səhifə: Any = 1, cəmi: Any = 1,
               klik: Any = None) -> Element:
    cari = max(1, int(_say(səhifə, 1)))
    son = max(1, int(_say(cəmi, 1)))
    düymələr: list = [_E("button", {
        "class": f"{P}səhifə-düyməsi",
        "type": "button", "value": str(cari - 1),
        "disabled": True if cari <= 1 else None,
        "klik": None if cari <= 1 else klik,
    }, "‹")]

    # Birinci, sonuncu və cari səhifənin ətrafı göstərilir
    nömrələr: list[int] = []
    for n in range(1, son + 1):
        if n <= 2 or n > son - 2 or abs(n - cari) <= 1:
            nömrələr.append(n)
    əvvəlki = 0
    for n in nömrələr:
        if əvvəlki and n - əvvəlki > 1:
            düymələr.append(_E("span", {"class": f"{P}səhifə-fasiləsi"},
                                "…"))
        düymələr.append(_E("button", {
            "class": _sinif(f"{P}səhifə-düyməsi",
                            f"{P}səhifə-düyməsi--seçili" if n == cari
                            else None),
            "type": "button", "value": str(n), "klik": klik,
        }, str(n)))
        əvvəlki = n

    düymələr.append(_E("button", {
        "class": f"{P}səhifə-düyməsi",
        "type": "button", "value": str(cari + 1),
        "disabled": True if cari >= son else None,
        "klik": None if cari >= son else klik,
    }, "›"))
    return _E("nav", {"class": f"{P}səhifələmə"}, düymələr)


def addımlar(icraçı, adlar: Any = None, cari: Any = 1) -> Element:
    adlar = _sətirlər(adlar, icraçı)
    n = int(_say(cari, 1))
    uşaqlar: list = []
    for i, ad in enumerate(adlar, start=1):
        vəziyyət = ("bitmiş" if i < n else
                    "cari" if i == n else "gözləyən")
        uşaqlar.append(_E("li", {
            "class": _sinif(f"{P}addım", f"{P}addım--{vəziyyət}"),
        }, [
            _E("span", {"class": f"{P}addım-nömrəsi"},
               "✓" if i < n else str(i)),
            _E("span", {"class": f"{P}addım-adı"}, ad),
        ]))
    return _E("ol", {"class": f"{P}addımlar"}, uşaqlar)


def çörəkQırıntıları(icraçı, yollar: Any = None,
                     klik: Any = None) -> Element:
    cütlər = _seçimlər(yollar, icraçı)
    uşaqlar: list = []
    for i, (d, e) in enumerate(cütlər):
        if i:
            uşaqlar.append(_E("span", {"class": f"{P}qırıntı-ayırıcısı"},
                               "/"))
        son = (i == len(cütlər) - 1)
        uşaqlar.append(_E("span" if son else "a", {
            "class": _sinif(f"{P}qırıntı",
                            f"{P}qırıntı--son" if son else None),
            "href": None if son else (d or "#"),
            "value": d,
            "klik": None if son else klik,
        }, e))
    return _E("nav", {"class": f"{P}qırıntılar"}, uşaqlar)


# ═══════════════════════════════════════════════════════════════════════
#  Üst qat
# ═══════════════════════════════════════════════════════════════════════

def modal(icraçı, başlıq: Any = "", məzmun: Any = None,
          altlıq: Any = None, görünür: Any = True,
          bağlandı: Any = None, ölçü: Any = "orta") -> Element:
    if not görünür:
        return Element("", {}, [])
    ö = _növü_yoxla(_m(ölçü, icraçı, "orta"), ÖLÇÜLƏR, "modal ölçüsü")
    baş: list = [_E("h3", {"class": f"{P}modal-başlığı"},
                    _m(başlıq, icraçı))]
    if bağlandı is not None:
        baş.append(_E("button", {
            "class": f"{P}modal-bağla", "type": "button",
            "title": "Bağla", "klik": bağlandı,
        }, "✕"))
    uşaqlar: list = [
        _E("div", {"class": f"{P}modal-başı"}, baş),
        _E("div", {"class": f"{P}modal-gövdəsi"}, məzmun),
    ]
    if altlıq is not None:
        uşaqlar.append(_E("div", {"class": f"{P}modal-altlığı"}, altlıq))
    return _E("div", {
        "class": f"{P}modal-örtüyü", "role": "dialog",
    }, _E("div", {
        "class": _sinif(f"{P}modal", f"{P}modal--{ö}"),
    }, uşaqlar))


def yanPanel(icraçı, başlıq: Any = "", məzmun: Any = None,
             görünür: Any = True, tərəf: Any = "sağ",
             bağlandı: Any = None) -> Element:
    if not görünür:
        return Element("", {}, [])
    t = _növü_yoxla(_m(tərəf, icraçı, "sağ"), ("sol", "sağ"),
                    "yan panel tərəfi")
    baş: list = [_E("h3", {"class": f"{P}yan-başlığı"},
                    _m(başlıq, icraçı))]
    if bağlandı is not None:
        baş.append(_E("button", {
            "class": f"{P}modal-bağla", "type": "button",
            "title": "Bağla", "klik": bağlandı,
        }, "✕"))
    return _E("div", {"class": f"{P}yan-örtüyü"}, _E("aside", {
        "class": _sinif(f"{P}yan-panel", f"{P}yan-panel--{t}"),
    }, [
        _E("div", {"class": f"{P}yan-başı"}, baş),
        _E("div", {"class": f"{P}yan-gövdəsi"}, məzmun),
    ]))


def ipucu(icraçı, mətn: Any = "", məzmun: Any = None,
          tərəf: Any = "üst") -> Element:
    t = _növü_yoxla(_m(tərəf, icraçı, "üst"),
                    ("üst", "alt", "sol", "sağ"), "ipucu tərəfi")
    return _E("span", {
        "class": _sinif(f"{P}ipucu", f"{P}ipucu--{t}"),
        "data-ipucu": _m(mətn, icraçı),
    }, məzmun)


def bildirişQutusu(icraçı, mətn: Any = "", növ: Any = "məlumat",
                   bağlandı: Any = None) -> Element:
    return _E("div", {"class": f"{P}bildiriş-qutusu"},
              xəbərdarlıq(icraçı, mətn, növ, None,
                          bağlandı is not None, bağlandı))


# ═══════════════════════════════════════════════════════════════════════
#  Vidjet kataloqu — Alqor Studio üçün
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Məlumat:
    """
    Bir vidjetin IDE təsviri.

    `skelet` — paletdən əlavə edilmiş elementin üzərinə iki dəfə
    klikləndikdə redaktora yazılacaq kod. `{ad}` yer tutucusu
    istifadəçinin verdiyi adla əvəzlənir.
    """
    ad: str
    kateqoriya: str
    izah: str
    nümunə: str
    hadisələr: list[str] = field(default_factory=list)
    skelet: str = ""
    vəziyyət: str = ""


FORM = "form"
GÖSTƏRMƏ = "göstərmə"
VƏZİYYƏT = "vəziyyət"
DÜZÜLÜŞ = "düzülüş"
NAVİQASİYA = "naviqasiya"
ÜST_QAT = "üst qat"

KATALOQ: list[Məlumat] = [
    # ── Düymələr ──
    Məlumat("düymə", FORM, "Basıla bilən düymə",
            'vidjet.düymə(mətn: "Yadda saxla", növ: "əsas",\n'
            '             klik: özü.{ad}Basıldı)',
            ["klik"],
            'metod {ad}Basıldı()\n'
            '    // Düymə basıldıqda bu kod işləyir\n'
            'son'),
    Məlumat("ikonDüymə", FORM, "Yalnız ikondan ibarət düymə",
            'vidjet.ikonDüymə(ikon: "✕", başlıq: "Sil",\n'
            '                 klik: özü.{ad}Basıldı)',
            ["klik"],
            'metod {ad}Basıldı()\n'
            '    // …\n'
            'son'),
    Məlumat("düyməQrupu", FORM, "Yanaşı duran düymələr",
            'vidjet.düyməQrupu(məzmun: [\n'
            '    vidjet.düymə(mətn: "Bəli"),\n'
            '    vidjet.düymə(mətn: "Xeyr", növ: "ikinci")\n'
            '])'),
    Məlumat("əlaqə", FORM, "Keçid (link)",
            'vidjet.əlaqə(mətn: "Ətraflı", ünvan: "/haqqında")',
            ["klik"]),

    # ── Form sahələri ──
    Məlumat("sahə", FORM, "Mətn sahəsi",
            'vidjet.sahə(etiket: "Ad", ad: "{ad}",\n'
            '            dəyər: özü.{ad}, dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi", "yazıldı"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son',
            'vəziyyət {ad}: mətn = ""'),
    Məlumat("parol", FORM, "Şifrə sahəsi",
            'vidjet.parol(etiket: "Şifrə", ad: "şifrə",\n'
            '             dəyişdi: özü.şifrəDəyişdi)',
            ["dəyişdi"],
            'metod şifrəDəyişdi(dəyər: mətn)\n'
            '    özü.şifrə = dəyər\n'
            'son',
            'vəziyyət şifrə: mətn = ""'),
    Məlumat("ədəd", FORM, "Ədəd sahəsi",
            'vidjet.ədəd(etiket: "Yaş", ad: "{ad}", minimum: 0,\n'
            '            maksimum: 120, dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = tamƏt(dəyər, 0)\n'
            'son',
            'vəziyyət {ad}: tam = 0'),
    Məlumat("axtarış", FORM, "Axtarış sahəsi",
            'vidjet.axtarış(yazıldı: özü.axtar)',
            ["yazıldı", "göndərildi"],
            'metod axtar(sorğu: mətn)\n'
            '    özü.sorğu = sorğu\n'
            'son',
            'vəziyyət sorğu: mətn = ""'),
    Məlumat("çoxsətirli", FORM, "Çoxsətirli mətn sahəsi",
            'vidjet.çoxsətirli(etiket: "Qeyd", ad: "{ad}",\n'
            '                  sətirlər: 5, dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son',
            'vəziyyət {ad}: mətn = ""'),
    Məlumat("seçim", FORM, "Açılan siyahı",
            'vidjet.seçim(etiket: "Şəhər", ad: "{ad}",\n'
            '             seçimlər: ["Bakı", "Gəncə", "Sumqayıt"],\n'
            '             dəyər: özü.{ad}, dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son',
            'vəziyyət {ad}: mətn = ""'),
    Məlumat("qeyd", FORM, "İşarələmə qutusu",
            'vidjet.qeyd(etiket: "Qəbul edirəm", ad: "{ad}",\n'
            '            işarələnmiş: özü.{ad},\n'
            '            dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(_dəyər: istənilən)\n'
            '    özü.{ad} = deyil özü.{ad}\n'
            'son',
            'vəziyyət {ad}: məntiq = yanlış'),
    Məlumat("açar", FORM, "Yandır/söndür açarı",
            'vidjet.açar(etiket: "Bildirişlər", ad: "{ad}",\n'
            '            yanıq: özü.{ad}, dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(_dəyər: istənilən)\n'
            '    özü.{ad} = deyil özü.{ad}\n'
            'son',
            'vəziyyət {ad}: məntiq = yanlış'),
    Məlumat("radioQrupu", FORM, "Bir variantın seçimi",
            'vidjet.radioQrupu(etiket: "Ödəniş", ad: "{ad}",\n'
            '                  seçimlər: ["Nağd", "Kart"],\n'
            '                  dəyər: özü.{ad},\n'
            '                  dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son',
            'vəziyyət {ad}: mətn = ""'),
    Məlumat("sürüşdürücü", FORM, "Sürüşdürülən dəyər",
            'vidjet.sürüşdürücü(etiket: "Səs", ad: "{ad}",\n'
            '                   dəyər: özü.{ad},\n'
            '                   dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = tamƏt(dəyər, 0)\n'
            'son',
            'vəziyyət {ad}: tam = 50'),
    Məlumat("tarix", FORM, "Tarix seçimi",
            'vidjet.tarix(etiket: "Doğum tarixi", ad: "{ad}",\n'
            '             dəyişdi: özü.{ad}Dəyişdi)',
            ["dəyişdi"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son',
            'vəziyyət {ad}: mətn = ""'),
    Məlumat("vaxt", FORM, "Vaxt seçimi",
            'vidjet.vaxt(etiket: "Saat", ad: "{ad}")', ["dəyişdi"]),
    Məlumat("rəng", FORM, "Rəng seçimi",
            'vidjet.rəng(etiket: "Rəng", ad: "{ad}")', ["dəyişdi"]),
    Məlumat("faylSahəsi", FORM, "Fayl yükləmə sahəsi",
            'vidjet.faylSahəsi(etiket: "Şəkil", ad: "{ad}",\n'
            '                  növlər: ["image/*"])', ["dəyişdi"]),
    Məlumat("form", FORM, "Form qabı",
            'vidjet.form(başlıq: "Qeydiyyat",\n'
            '            göndərildi: özü.göndər, məzmun: [\n'
            '    vidjet.sahə(etiket: "Ad", ad: "ad"),\n'
            '    vidjet.düymə(mətn: "Göndər")\n'
            '])',
            ["göndərildi"],
            'metod göndər()\n'
            '    // Formun məlumatlarını işlə\n'
            'son'),
    Məlumat("sahəDəsti", FORM, "Qruplaşdırılmış sahələr",
            'vidjet.sahəDəsti(başlıq: "Ünvan", məzmun: [\n'
            '    vidjet.sahə(etiket: "Şəhər", ad: "şəhər")\n'
            '])'),
    Məlumat("etiket", FORM, "Sahə etiketi",
            'vidjet.etiket(mətn: "Ad", sahəsi: "ad")'),

    # ── Göstərmə ──
    Məlumat("başlıq", GÖSTƏRMƏ, "Başlıq (h1–h6)",
            'vidjet.başlıq(mətn: "Tapşırıqlar", səviyyə: 1,\n'
            '              altMətn: "Bugünkü işlər")'),
    Məlumat("mətn", GÖSTƏRMƏ, "Abzas",
            'vidjet.mətn(məzmun: "Salam, dünya!")'),
    Məlumat("nişan", GÖSTƏRMƏ, "Kiçik nişan (badge)",
            'vidjet.nişan(mətn: "Yeni", növ: "uğur")'),
    Məlumat("xəbərdarlıq", GÖSTƏRMƏ, "Bildiriş qutusu",
            'vidjet.xəbərdarlıq(mətn: "Yadda saxlanıldı",\n'
            '                   növ: "uğur")',
            ["bağlandı"],
            'metod xəbərdarlığıBağla()\n'
            '    özü.xəbərdarlıqGörünür = yanlış\n'
            'son',
            'vəziyyət xəbərdarlıqGörünür: məntiq = doğru'),
    Məlumat("kart", GÖSTƏRMƏ, "Kart qabı",
            'vidjet.kart(başlıq: "Hesabat", məzmun: [\n'
            '    vidjet.mətn(məzmun: "Məzmun")\n'
            '])', ["klik"]),
    Məlumat("cədvəl", GÖSTƏRMƏ, "Məlumat cədvəli",
            'vidjet.cədvəl(\n'
            '    sütunlar: [["ad", "Ad"], ["yaş", "Yaş"]],\n'
            '    sətirlər: özü.{ad})',
            ["sətirKlik"],
            'metod sətirBasıldı()\n'
            '    // Sətir seçildi\n'
            'son',
            'vəziyyət {ad}: siyahı[istənilən] = []'),
    Məlumat("siyahı", GÖSTƏRMƏ, "Sadalama siyahısı",
            'vidjet.siyahı(elementlər: ["bir", "iki", "üç"])'),
    Məlumat("təsvirSiyahısı", GÖSTƏRMƏ, "Açar–dəyər siyahısı",
            'vidjet.təsvirSiyahısı(cütlər: {"Ad": "Əli", "Yaş": 30})'),
    Məlumat("kod", GÖSTƏRMƏ, "Kod bloku",
            'vidjet.kod(məzmun: "yaz(\\"salam\\")", dil: "alqor")'),
    Məlumat("sitat", GÖSTƏRMƏ, "Sitat",
            'vidjet.sitat(mətn: "Bilik gücdür", mənbə: "Atalar sözü")'),
    Məlumat("şəkil", GÖSTƏRMƏ, "Şəkil",
            'vidjet.şəkil(mənbə: "/statik/logo.png",\n'
            '             alternativ: "Loqo", en: 120)'),
    Məlumat("avatar", GÖSTƏRMƏ, "İstifadəçi avatarı",
            'vidjet.avatar(ad: "Aysel Məmmədova")'),
    Məlumat("ayırıcı", GÖSTƏRMƏ, "Ayırıcı xətt",
            'vidjet.ayırıcı(mətn: "və ya")'),
    Məlumat("boşBaxış", GÖSTƏRMƏ, "Boş vəziyyət",
            'vidjet.boşBaxış(başlıq: "Tapşırıq yoxdur",\n'
            '                mətn: "Yeni tapşırıq əlavə edin")'),

    # ── Vəziyyət ──
    Məlumat("tərəqqi", VƏZİYYƏT, "Tərəqqi çubuğu",
            'vidjet.tərəqqi(dəyər: özü.{ad}, maksimum: 100,\n'
            '               etiket: "Yüklənir")',
            [], '', 'vəziyyət {ad}: tam = 0'),
    Məlumat("halqaTərəqqi", VƏZİYYƏT, "Halqa şəklində tərəqqi",
            'vidjet.halqaTərəqqi(dəyər: özü.{ad}, ölçü: 80)',
            [], '', 'vəziyyət {ad}: tam = 0'),
    Məlumat("fırlanan", VƏZİYYƏT, "Gözləmə göstəricisi",
            'vidjet.fırlanan(mətn: "Yüklənir…")'),
    Məlumat("skeletYüklənmə", VƏZİYYƏT, "Yüklənmə skeleti",
            'vidjet.skeletYüklənmə(sətirlər: 3)'),
    Məlumat("statistika", VƏZİYYƏT, "Rəqəmli göstərici",
            'vidjet.statistika(etiket: "Satış", dəyər: "1 240 ₼",\n'
            '                  dəyişmə: 12)'),

    # ── Düzülüş ──
    Məlumat("qutu", DÜZÜLÜŞ, "Sadə qab",
            'vidjet.qutu(boşluq: 16, kənar: doğru, məzmun: [])'),
    Məlumat("sətir", DÜZÜLÜŞ, "Üfüqi düzülüş",
            'vidjet.sətir(boşluq: 8, düzləndir: "ara", məzmun: [])'),
    Məlumat("sütun", DÜZÜLÜŞ, "Şaquli düzülüş",
            'vidjet.sütun(boşluq: 12, məzmun: [])'),
    Məlumat("tor", DÜZÜLÜŞ, "Tor (grid) düzülüşü",
            'vidjet.tor(sütunlar: 3, boşluq: 12, məzmun: [])'),
    Məlumat("boşluq", DÜZÜLÜŞ, "Şaquli boşluq",
            'vidjet.boşluq(hündürlük: 24)'),
    Məlumat("panel", DÜZÜLÜŞ, "Başlıqlı panel",
            'vidjet.panel(başlıq: "Ayarlar", məzmun: [])'),
    Məlumat("bölmə", DÜZÜLÜŞ, "Səhifə bölməsi",
            'vidjet.bölmə(başlıq: "Haqqında", məzmun: [])'),

    # ── Naviqasiya ──
    Məlumat("naviqasiya", NAVİQASİYA, "Üst naviqasiya sətri",
            'vidjet.naviqasiya(başlıq: "Tətbiqim", elementlər: [\n'
            '    vidjet.əlaqə(mətn: "Ana səhifə", ünvan: "/")\n'
            '])'),
    Məlumat("nişanlar", NAVİQASİYA, "Nişanlar (tabs)",
            'vidjet.nişanlar(elementlər: ["Ümumi", "Ayarlar"],\n'
            '                cari: özü.{ad}, klik: özü.{ad}Seçildi)',
            ["klik"],
            'metod {ad}Seçildi(dəyər: mətn)\n'
            '    özü.{ad} = dəyər\n'
            'son',
            'vəziyyət {ad}: mətn = "Ümumi"'),
    Məlumat("yığcam", NAVİQASİYA, "Açılıb-yığılan bölmə",
            'vidjet.yığcam(başlıq: "Ətraflı", açılmış: yanlış,\n'
            '              məzmun: [])'),
    Məlumat("səhifələmə", NAVİQASİYA, "Səhifələrə bölmə",
            'vidjet.səhifələmə(səhifə: özü.{ad}, cəmi: 10,\n'
            '                  klik: özü.{ad}Dəyişdi)',
            ["klik"],
            'metod {ad}Dəyişdi(dəyər: mətn)\n'
            '    özü.{ad} = tamƏt(dəyər, 1)\n'
            'son',
            'vəziyyət {ad}: tam = 1'),
    Məlumat("addımlar", NAVİQASİYA, "Addım göstəricisi",
            'vidjet.addımlar(adlar: ["Ad", "Ünvan", "Təsdiq"],\n'
            '                cari: özü.{ad})',
            [], '', 'vəziyyət {ad}: tam = 1'),
    Məlumat("çörəkQırıntıları", NAVİQASİYA, "Yol göstəricisi",
            'vidjet.çörəkQırıntıları(yollar: [\n'
            '    ["/", "Ana səhifə"], ["/mal", "Mallar"]\n'
            '])', ["klik"]),

    # ── Üst qat ──
    Məlumat("modal", ÜST_QAT, "Modal pəncərə",
            'vidjet.modal(başlıq: "Təsdiq", görünür: özü.{ad},\n'
            '             bağlandı: özü.{ad}Bağla, məzmun: [])',
            ["bağlandı"],
            'metod {ad}Bağla()\n'
            '    özü.{ad} = yanlış\n'
            'son',
            'vəziyyət {ad}: məntiq = yanlış'),
    Məlumat("yanPanel", ÜST_QAT, "Yan panel (drawer)",
            'vidjet.yanPanel(başlıq: "Menyu", görünür: özü.{ad},\n'
            '                bağlandı: özü.{ad}Bağla, məzmun: [])',
            ["bağlandı"],
            'metod {ad}Bağla()\n'
            '    özü.{ad} = yanlış\n'
            'son',
            'vəziyyət {ad}: məntiq = yanlış'),
    Məlumat("ipucu", ÜST_QAT, "Üzərinə gələndə görünən izah",
            'vidjet.ipucu(mətn: "Silinəcək",\n'
            '             məzmun: vidjet.ikonDüymə(ikon: "✕"))'),
    Məlumat("bildirişQutusu", ÜST_QAT, "Küncdə görünən bildiriş",
            'vidjet.bildirişQutusu(mətn: "Saxlanıldı", növ: "uğur")',
            ["bağlandı"]),
]

_KATALOQ_XƏRİTƏSİ = {m.ad: m for m in KATALOQ}

# Kataloq tək həqiqət mənbəyidir: modulun ixrac etdiyi vidjetlərin
# siyahısı buradan qurulur, ona görə kataloqda olub funksiyası olmayan
# (və ya əksinə) vidjet yarana bilmir.
VİDJETLƏR: tuple[str, ...] = tuple(m.ad for m in KATALOQ)


def _kataloqu_yoxla() -> None:
    import sys as _sys
    bu = _sys.modules[__name__]
    çatışmayan = [a for a in VİDJETLƏR if not callable(
        getattr(bu, a, None))]
    if çatışmayan:
        raise RuntimeError(
            "kataloqda var, funksiyası yoxdur: " + ", ".join(çatışmayan))
    təkrar = [a for a in VİDJETLƏR if VİDJETLƏR.count(a) > 1]
    if təkrar:
        raise RuntimeError("kataloqda təkrar: " + ", ".join(set(təkrar)))


def kataloq(icraçı, kateqoriya: Any = None) -> list:
    """IDE paleti üçün bütün vidjetlərin təsviri."""
    k = _m(kateqoriya, icraçı) if kateqoriya is not None else None
    if k and k not in KATEQORİYALAR:
        raise AlqorXəta(
            "ArqumentXətası",
            f"`{k}` kateqoriyası yoxdur. İcazəli: "
            f"{', '.join(KATEQORİYALAR)}", kod="ALQ-R013")
    return [{
        "ad": m.ad,
        "kateqoriya": m.kateqoriya,
        "izah": m.izah,
        "nümunə": m.nümunə,
        "hadisələr": list(m.hadisələr),
        "skelet": m.skelet,
        "vəziyyət": m.vəziyyət,
    } for m in KATALOQ if not k or m.kateqoriya == k]


KATEQORİYALAR = (FORM, GÖSTƏRMƏ, VƏZİYYƏT, DÜZÜLÜŞ, NAVİQASİYA, ÜST_QAT)


def kateqoriyalar(icraçı) -> list[str]:
    return list(KATEQORİYALAR)


def skelet(icraçı, ad: Any, dəyişənAdı: Any = "") -> str:
    """
    Elementin işləməsi üçün lazım olan kod. Alqor Studio-da elementin
    üzərinə iki dəfə klikləndikdə bu mətn redaktora yazılır.

        vidjet.skelet("sahə", "istifadəçiAdı")
        → vəziyyət istifadəçiAdı: mətn = ""
        →
        → metod istifadəçiAdıDəyişdi(dəyər: mətn)
        →     özü.istifadəçiAdı = dəyər
        → son
    """
    vidjet_adı = _m(ad, icraçı)
    m = _KATALOQ_XƏRİTƏSİ.get(vidjet_adı)
    if m is None:
        yaxın = [a for a in _KATALOQ_XƏRİTƏSİ
                 if vidjet_adı and vidjet_adı in a]
        kömək = f" Oxşarlar: {', '.join(yaxın[:5])}" if yaxın else ""
        raise AlqorXəta(
            "ArqumentXətası",
            f"`{vidjet_adı}` vidjeti yoxdur.{kömək}", kod="ALQ-R013")

    d = _m(dəyişənAdı, icraçı) or _standart_ad(vidjet_adı)
    hissələr: list[str] = []
    if m.vəziyyət:
        hissələr.append(m.vəziyyət.replace("{ad}", d))
    if m.skelet:
        hissələr.append(m.skelet.replace("{ad}", d))
    return "\n\n".join(hissələr)


def nümunə(icraçı, ad: Any, dəyişənAdı: Any = "") -> str:
    """Vidjetin JSX istifadə nümunəsi."""
    vidjet_adı = _m(ad, icraçı)
    m = _KATALOQ_XƏRİTƏSİ.get(vidjet_adı)
    if m is None:
        raise AlqorXəta("ArqumentXətası",
                        f"`{vidjet_adı}` vidjeti yoxdur",
                        kod="ALQ-R013")
    d = _m(dəyişənAdı, icraçı) or _standart_ad(vidjet_adı)
    return m.nümunə.replace("{ad}", d)


def _standart_ad(vidjet_adı: str) -> str:
    """`sahə` → `sahə1` kimi təhlükəsiz dəyişən adı."""
    from .elifba import KICIK
    təmiz = "".join(c for c in vidjet_adı
                    if c in KICIK or c.isalnum() or c == "_")
    return təmiz or "element"


# ═══════════════════════════════════════════════════════════════════════
#  Üslub
# ═══════════════════════════════════════════════════════════════════════

ÜSLUB = """
.v-sahə,.v-form,.v-sütun{display:flex;flex-direction:column}
:root{
 --v-fon:#fff;--v-mətn:#17171a;--v-kənar:#d7d7db;--v-sönük:#6c6c75;
 --v-vurgu:#0b6bcb;--v-vurgu-mətn:#fff;--v-üst:#f4f4f6;
 --v-uğur:#167c3c;--v-xəbərdarlıq:#9a6700;--v-təhlükə:#c0392b;
 --v-radius:8px;--v-kölgə:0 1px 3px rgba(0,0,0,.1)
}
@media (prefers-color-scheme:dark){:root{
 --v-fon:#1c1c1f;--v-mətn:#f1f1f4;--v-kənar:#3a3a40;--v-sönük:#9a9aa3;
 --v-vurgu:#4c9ef0;--v-vurgu-mətn:#0b1620;--v-üst:#26262b;
 --v-uğur:#4ac776;--v-xəbərdarlıq:#e3b341;--v-təhlükə:#ff7b72;
 --v-kölgə:0 1px 3px rgba(0,0,0,.4)}}

/* ── Düymələr ── */
.v-düymə{display:inline-flex;align-items:center;gap:6px;
 font:inherit;padding:8px 16px;border:1px solid transparent;
 border-radius:var(--v-radius);cursor:pointer;line-height:1.2;
 background:var(--v-üst);color:var(--v-mətn);
 border-color:var(--v-kənar)}
.v-düymə:hover:not([disabled]){filter:brightness(.95)}
.v-düymə:active:not([disabled]){transform:translateY(1px)}
.v-düymə[disabled]{opacity:.5;cursor:not-allowed}
.v-düymə--əsas{background:var(--v-vurgu);color:var(--v-vurgu-mətn);
 border-color:transparent}
.v-düymə--ikinci{background:var(--v-üst);color:var(--v-mətn)}
.v-düymə--sakit{background:transparent;border-color:transparent;
 color:var(--v-mətn)}
.v-düymə--sakit:hover:not([disabled]){background:var(--v-üst)}
.v-düymə--təhlükə{background:var(--v-təhlükə);color:#fff;
 border-color:transparent}
.v-düymə--uğur{background:var(--v-uğur);color:#fff;
 border-color:transparent}
.v-düymə--xəbərdarlıq{background:var(--v-xəbərdarlıq);color:#fff;
 border-color:transparent}
.v-düymə--əlaqə{background:none;border:0;color:var(--v-vurgu);
 text-decoration:underline;padding:2px 4px}
.v-düymə--kiçik{padding:4px 10px;font-size:.875em}
.v-düymə--böyük{padding:11px 22px;font-size:1.0625em}
.v-düymə--tamEn{width:100%;justify-content:center}
.v-düymə--ikon{padding:7px;aspect-ratio:1;justify-content:center}
.v-düymə-qrupu{display:inline-flex}
.v-düymə-qrupu .v-düymə{border-radius:0;margin-left:-1px}
.v-düymə-qrupu .v-düymə:first-child{border-radius:var(--v-radius) 0 0
 var(--v-radius);margin-left:0}
.v-düymə-qrupu .v-düymə:last-child{border-radius:0 var(--v-radius)
 var(--v-radius) 0}
.v-əlaqə{color:var(--v-vurgu);text-decoration:none}
.v-əlaqə:hover{text-decoration:underline}

/* ── Form ── */
.v-form{gap:14px}
.v-form--sıx{gap:8px}
.v-form-başlığı{margin:0 0 4px;font-size:1.25em}
.v-sahə{gap:5px}
.v-etiket{font-size:.9em;font-weight:600;color:var(--v-mətn)}
.v-tələb{color:var(--v-təhlükə);margin-left:3px}
.v-giriş{font:inherit;padding:8px 10px;border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);background:var(--v-fon);
 color:var(--v-mətn);width:100%}
.v-giriş:focus{outline:2px solid var(--v-vurgu);outline-offset:-1px;
 border-color:var(--v-vurgu)}
.v-giriş[disabled]{opacity:.6;cursor:not-allowed}
.v-giriş--xətalı{border-color:var(--v-təhlükə)}
.v-çoxsətirli{resize:vertical;min-height:72px}
.v-seçim{appearance:none;
 background-image:linear-gradient(45deg,transparent 50%,
 var(--v-sönük) 50%),linear-gradient(135deg,var(--v-sönük) 50%,
 transparent 50%);
 background-position:calc(100% - 16px) 50%,calc(100% - 11px) 50%;
 background-size:5px 5px,5px 5px;background-repeat:no-repeat;
 padding-right:32px}
.v-kömək{margin:0;font-size:.825em;color:var(--v-sönük)}
.v-xəta-mətni{margin:0;font-size:.825em;color:var(--v-təhlükə)}
.v-qeyd,.v-radio{display:flex;align-items:center;gap:8px;
 cursor:pointer}
.v-qeyd-mətni,.v-radio-mətni,.v-açar-mətni{line-height:1.3}
.v-radio-qrupu{display:flex;flex-direction:column;gap:6px}
.v-radio-qrupu--üfüqi{flex-direction:row;flex-wrap:wrap;gap:16px}
.v-sahə-dəsti{border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);padding:14px;margin:0;
 display:flex;flex-direction:column;gap:12px}
.v-sahə-dəsti-başlığı{padding:0 6px;font-weight:600}
.v-axtarış{position:relative;display:flex;align-items:center}
.v-axtarış .v-giriş{padding-left:32px}
.v-axtarış-ikonu{position:absolute;left:11px;color:var(--v-sönük);
 font-size:1.15em;pointer-events:none}

/* Açar */
.v-açar{display:inline-flex;align-items:center;gap:9px;
 cursor:pointer}
.v-açar--sönük{opacity:.6;cursor:not-allowed}
.v-açar input{position:absolute;opacity:0;width:0;height:0}
.v-açar-yolu{width:38px;height:22px;border-radius:11px;
 background:var(--v-kənar);position:relative;flex:none;
 transition:background .15s}
.v-açar-topu{position:absolute;top:3px;left:3px;width:16px;height:16px;
 border-radius:50%;background:#fff;transition:transform .15s;
 box-shadow:0 1px 2px rgba(0,0,0,.3)}
.v-açar input:checked+.v-açar-yolu{background:var(--v-vurgu)}
.v-açar input:checked+.v-açar-yolu .v-açar-topu{
 transform:translateX(16px)}

/* Sürüşdürücü */
.v-sürüşdürücü-sırası{display:flex;align-items:center;gap:10px}
.v-sürüşdürücü{flex:1;accent-color:var(--v-vurgu)}
.v-sürüşdürücü-dəyəri{min-width:3ch;text-align:right;
 font-variant-numeric:tabular-nums;color:var(--v-sönük)}

/* ── Göstərmə ── */
.v-başlıq{margin:0;line-height:1.25}
.v-başlıq-qrupu{display:flex;flex-direction:column;gap:3px}
.v-alt-mətn{margin:0;color:var(--v-sönük);font-size:.9em}
.v-mətn{margin:0}
.v-mətn--sönük{color:var(--v-sönük)}
.v-mətn--qalın{font-weight:600}
.v-mətn--kiçik{font-size:.875em}
.v-mətn--böyük{font-size:1.125em}
.v-nişan{display:inline-block;padding:2px 9px;border-radius:999px;
 font-size:.8em;font-weight:600;background:var(--v-üst);
 color:var(--v-mətn)}
.v-nişan--əsas{background:var(--v-vurgu);color:var(--v-vurgu-mətn)}
.v-nişan--uğur{background:var(--v-uğur);color:#fff}
.v-nişan--xəbərdarlıq{background:var(--v-xəbərdarlıq);color:#fff}
.v-nişan--təhlükə{background:var(--v-təhlükə);color:#fff}
.v-xəbərdarlıq{display:flex;gap:10px;align-items:flex-start;
 padding:12px 14px;border-radius:var(--v-radius);
 border:1px solid var(--v-kənar);background:var(--v-üst)}
.v-xəbərdarlıq-ikonu{flex:none;width:20px;height:20px;
 border-radius:50%;display:grid;place-items:center;font-size:.8em;
 font-weight:700;color:#fff;background:var(--v-sönük)}
.v-xəbərdarlıq--uğur .v-xəbərdarlıq-ikonu{background:var(--v-uğur)}
.v-xəbərdarlıq--xəbərdarlıq .v-xəbərdarlıq-ikonu{
 background:var(--v-xəbərdarlıq)}
.v-xəbərdarlıq--təhlükə .v-xəbərdarlıq-ikonu{background:var(--v-təhlükə)}
.v-xəbərdarlıq--məlumat .v-xəbərdarlıq-ikonu{background:var(--v-vurgu)}
.v-xəbərdarlıq-gövdəsi{display:flex;flex-direction:column;gap:2px;
 flex:1}
.v-xəbərdarlıq-bağla,.v-modal-bağla{border:0;background:none;
 cursor:pointer;color:var(--v-sönük);font-size:1em;padding:0 2px;
 line-height:1}
.v-kart{border:1px solid var(--v-kənar);border-radius:var(--v-radius);
 background:var(--v-fon);box-shadow:var(--v-kölgə);overflow:hidden}
.v-kart--basılan{cursor:pointer}
.v-kart--basılan:hover{border-color:var(--v-vurgu)}
.v-kart-başı{padding:14px 16px;border-bottom:1px solid var(--v-kənar)}
.v-kart-başlığı{margin:0;font-size:1.05em}
.v-kart-gövdəsi{padding:16px}
.v-kart-altlığı{padding:12px 16px;border-top:1px solid var(--v-kənar);
 background:var(--v-üst);display:flex;gap:8px;justify-content:flex-end}
.v-cədvəl-qabı{overflow-x:auto;border:1px solid var(--v-kənar);
 border-radius:var(--v-radius)}
.v-cədvəl{width:100%;border-collapse:collapse;font-size:.95em}
.v-cədvəl th,.v-cədvəl td{padding:9px 12px;text-align:left}
.v-cədvəl thead th{background:var(--v-üst);font-weight:600;
 border-bottom:1px solid var(--v-kənar);white-space:nowrap}
.v-cədvəl--zolaqlı tbody tr:nth-child(even){background:var(--v-üst)}
.v-cədvəl--çərçivəli th,.v-cədvəl--çərçivəli td{
 border:1px solid var(--v-kənar)}
.v-sətir--basılan{cursor:pointer}
.v-sətir--basılan:hover{background:var(--v-üst)}
.v-cədvəl-boş{text-align:center;color:var(--v-sönük);padding:28px}
.v-siyahı{margin:0;padding-left:22px;display:flex;
 flex-direction:column;gap:4px}
.v-siyahı--işarəsiz{list-style:none;padding-left:0}
.v-təsvir-siyahısı{display:grid;grid-template-columns:auto 1fr;
 gap:6px 16px;margin:0}
.v-təsvir-siyahısı dt{font-weight:600;color:var(--v-sönük)}
.v-təsvir-siyahısı dd{margin:0}
.v-kod{background:var(--v-üst);border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);padding:12px 14px;overflow-x:auto;
 font-family:ui-monospace,"Cascadia Code",Consolas,monospace;
 font-size:.9em;margin:0}
.v-sitat{margin:0;padding:10px 16px;border-left:3px solid var(--v-vurgu);
 background:var(--v-üst);border-radius:0 var(--v-radius)
 var(--v-radius) 0}
.v-sitat p{margin:0}
.v-sitat-mənbəyi{margin-top:6px;font-size:.85em;color:var(--v-sönük)}
.v-şəkil{max-width:100%;height:auto;border-radius:var(--v-radius)}
.v-şəkil--yuvarlaq{border-radius:50%}
.v-avatar{display:inline-grid;place-items:center;border-radius:50%;
 background:var(--v-vurgu);color:var(--v-vurgu-mətn);font-weight:600;
 width:40px;height:40px;object-fit:cover;flex:none}
.v-avatar--kiçik{width:28px;height:28px;font-size:.8em}
.v-avatar--böyük{width:56px;height:56px;font-size:1.25em}
.v-ayırıcı{border:0;border-top:1px solid var(--v-kənar);margin:14px 0}
.v-ayırıcı-mətnli{display:flex;align-items:center;gap:12px;
 color:var(--v-sönük);font-size:.875em;margin:14px 0}
.v-ayırıcı-mətnli::before,.v-ayırıcı-mətnli::after{content:"";flex:1;
 border-top:1px solid var(--v-kənar)}
.v-boş-baxış{text-align:center;padding:40px 20px;
 display:flex;flex-direction:column;align-items:center;gap:8px}
.v-boş-baxış h3{margin:0}
.v-boş-ikonu{font-size:2.5em;color:var(--v-sönük);line-height:1}

/* ── Vəziyyət ── */
.v-tərəqqi{display:flex;flex-direction:column;gap:5px}
.v-tərəqqi-başı{display:flex;justify-content:space-between;
 font-size:.85em;color:var(--v-sönük)}
.v-tərəqqi-faizi{font-variant-numeric:tabular-nums}
.v-tərəqqi-yolu{height:8px;background:var(--v-üst);border-radius:999px;
 overflow:hidden}
.v-tərəqqi-dolğusu{height:100%;background:var(--v-vurgu);
 border-radius:999px;transition:width .2s}
.v-tərəqqi-dolğusu--uğur{background:var(--v-uğur)}
.v-tərəqqi-dolğusu--təhlükə{background:var(--v-təhlükə)}
.v-tərəqqi-dolğusu--xəbərdarlıq{background:var(--v-xəbərdarlıq)}
.v-tərəqqi-yolu--qeyri-müəyyən .v-tərəqqi-dolğusu{width:35%;
 animation:v-sürüş 1.1s ease-in-out infinite}
@keyframes v-sürüş{0%{margin-left:-35%}100%{margin-left:100%}}
.v-halqa{--v-halqa-ölçü:64px;--v-halqa-faiz:0;
 width:var(--v-halqa-ölçü);height:var(--v-halqa-ölçü);
 border-radius:50%;display:grid;place-items:center;
 background:conic-gradient(var(--v-vurgu)
  calc(var(--v-halqa-faiz)*1%),var(--v-üst) 0)}
.v-halqa::before{content:"";position:absolute;
 width:calc(var(--v-halqa-ölçü) - 16px);
 height:calc(var(--v-halqa-ölçü) - 16px);
 border-radius:50%;background:var(--v-fon)}
.v-halqa-mətni{position:relative;font-size:.8em;font-weight:600}
.v-fırlanan{display:inline-block;width:18px;height:18px;flex:none;
 border:2px solid var(--v-kənar);border-top-color:var(--v-vurgu);
 border-radius:50%;animation:v-fırlan .7s linear infinite}
.v-fırlanan--kiçik{width:13px;height:13px;border-width:2px}
.v-fırlanan--böyük{width:28px;height:28px;border-width:3px}
@keyframes v-fırlan{to{transform:rotate(360deg)}}
.v-fırlanan-qrupu{display:inline-flex;align-items:center;gap:9px;
 color:var(--v-sönük)}
.v-skelet{display:flex;flex-direction:column;gap:8px}
.v-skelet-sətri{height:12px;border-radius:6px;background:var(--v-üst);
 animation:v-nəbz 1.3s ease-in-out infinite}
.v-skelet-sətri:last-child{width:70%}
@keyframes v-nəbz{50%{opacity:.45}}
.v-statistika{display:flex;gap:12px;align-items:center;
 padding:14px 16px;border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);background:var(--v-fon)}
.v-statistika-ikonu{font-size:1.6em;color:var(--v-vurgu)}
.v-statistika-etiketi{display:block;font-size:.825em;
 color:var(--v-sönük)}
.v-statistika-dəyəri{display:block;font-size:1.5em;line-height:1.2}
.v-statistika-dəyişməsi{font-size:.8em;font-weight:600}
.v-statistika-dəyişməsi--artıb{color:var(--v-uğur)}
.v-statistika-dəyişməsi--azalıb{color:var(--v-təhlükə)}
.v-statistika-dəyişməsi--sabit{color:var(--v-sönük)}

/* ── Düzülüş ── */
.v-qutu{min-width:0}
.v-qutu--kənarlı{border:1px solid var(--v-kənar);
 border-radius:var(--v-radius)}
.v-sətir{display:flex}
.v-sətir--sarı{flex-wrap:wrap}
.v-tor{display:grid}
.v-boşluq{flex:none}
.v-panel{border:1px solid var(--v-kənar);border-radius:var(--v-radius);
 background:var(--v-fon);overflow:hidden}
.v-panel-başı{display:flex;align-items:center;justify-content:space-between;
 gap:12px;padding:12px 16px;border-bottom:1px solid var(--v-kənar);
 background:var(--v-üst)}
.v-panel-başlığı{margin:0;font-size:1em}
.v-panel-alətləri{display:flex;gap:6px}
.v-panel-gövdəsi{padding:16px}
.v-bölmə{display:flex;flex-direction:column;gap:12px;margin:24px 0}
.v-bölmə-başlığı{margin:0}

/* ── Naviqasiya ── */
.v-nav{display:flex;align-items:center;gap:20px;padding:10px 16px;
 border-bottom:1px solid var(--v-kənar);background:var(--v-üst)}
.v-nav-başlığı{font-size:1.05em}
.v-nav-elementləri{display:flex;gap:16px;flex:1}
.v-nav-sağ{display:flex;gap:10px;align-items:center}
.v-nişanlar{display:flex;flex-direction:column}
.v-nişan-sətri{display:flex;gap:2px;
 border-bottom:1px solid var(--v-kənar)}
.v-nişan-düyməsi{font:inherit;border:0;background:none;cursor:pointer;
 padding:9px 15px;color:var(--v-sönük);
 border-bottom:2px solid transparent;margin-bottom:-1px}
.v-nişan-düyməsi:hover{color:var(--v-mətn)}
.v-nişan-düyməsi--seçili{color:var(--v-vurgu);
 border-bottom-color:var(--v-vurgu);font-weight:600}
.v-nişan-gövdəsi{padding:16px 0}
.v-yığcam{border:1px solid var(--v-kənar);
 border-radius:var(--v-radius);overflow:hidden}
.v-yığcam-başlığı{padding:11px 14px;cursor:pointer;font-weight:600;
 background:var(--v-üst)}
.v-yığcam-gövdəsi{padding:14px}
.v-səhifələmə{display:flex;gap:4px;align-items:center}
.v-səhifə-düyməsi{font:inherit;min-width:34px;height:34px;
 border:1px solid var(--v-kənar);border-radius:var(--v-radius);
 background:var(--v-fon);color:var(--v-mətn);cursor:pointer}
.v-səhifə-düyməsi:hover:not([disabled]){background:var(--v-üst)}
.v-səhifə-düyməsi[disabled]{opacity:.4;cursor:not-allowed}
.v-səhifə-düyməsi--seçili{background:var(--v-vurgu);
 color:var(--v-vurgu-mətn);border-color:transparent}
.v-səhifə-fasiləsi{padding:0 4px;color:var(--v-sönük)}
.v-addımlar{display:flex;gap:8px;list-style:none;margin:0;padding:0;
 flex-wrap:wrap}
.v-addım{display:flex;align-items:center;gap:8px;flex:1;
 min-width:120px;color:var(--v-sönük)}
.v-addım-nömrəsi{width:26px;height:26px;border-radius:50%;flex:none;
 display:grid;place-items:center;font-size:.85em;font-weight:600;
 background:var(--v-üst);border:1px solid var(--v-kənar)}
.v-addım--cari{color:var(--v-mətn);font-weight:600}
.v-addım--cari .v-addım-nömrəsi{background:var(--v-vurgu);
 color:var(--v-vurgu-mətn);border-color:transparent}
.v-addım--bitmiş .v-addım-nömrəsi{background:var(--v-uğur);color:#fff;
 border-color:transparent}
.v-qırıntılar{display:flex;gap:8px;align-items:center;font-size:.9em;
 flex-wrap:wrap}
.v-qırıntı{color:var(--v-vurgu);text-decoration:none}
.v-qırıntı--son{color:var(--v-sönük)}
.v-qırıntı-ayırıcısı{color:var(--v-sönük)}

/* ── Üst qat ── */
.v-modal-örtüyü,.v-yan-örtüyü{position:fixed;inset:0;z-index:50;
 background:rgba(0,0,0,.4);display:flex}
.v-modal-örtüyü{align-items:center;justify-content:center;padding:20px}
.v-modal{background:var(--v-fon);border-radius:12px;width:100%;
 max-width:480px;max-height:88vh;display:flex;flex-direction:column;
 box-shadow:0 14px 48px rgba(0,0,0,.3)}
.v-modal--kiçik{max-width:340px}
.v-modal--böyük{max-width:760px}
.v-modal-başı{display:flex;align-items:center;
 justify-content:space-between;gap:12px;padding:15px 18px;
 border-bottom:1px solid var(--v-kənar)}
.v-modal-başlığı{margin:0;font-size:1.1em}
.v-modal-gövdəsi{padding:18px;overflow:auto;flex:1}
.v-modal-altlığı{padding:13px 18px;border-top:1px solid var(--v-kənar);
 display:flex;gap:8px;justify-content:flex-end}
.v-yan-panel{background:var(--v-fon);width:min(380px,86vw);
 display:flex;flex-direction:column;
 box-shadow:0 0 40px rgba(0,0,0,.3)}
.v-yan-panel--sağ{margin-left:auto}
.v-yan-başı{display:flex;align-items:center;
 justify-content:space-between;gap:12px;padding:15px 18px;
 border-bottom:1px solid var(--v-kənar)}
.v-yan-başlığı{margin:0;font-size:1.1em}
.v-yan-gövdəsi{padding:18px;overflow:auto;flex:1}
.v-ipucu{position:relative;display:inline-flex}
.v-ipucu::after{content:attr(data-ipucu);position:absolute;
 padding:5px 9px;border-radius:6px;background:#17171a;color:#fff;
 font-size:.8em;white-space:nowrap;opacity:0;pointer-events:none;
 transition:opacity .12s;z-index:60}
.v-ipucu:hover::after{opacity:1}
.v-ipucu--üst::after{bottom:100%;left:50%;transform:translateX(-50%);
 margin-bottom:6px}
.v-ipucu--alt::after{top:100%;left:50%;transform:translateX(-50%);
 margin-top:6px}
.v-ipucu--sol::after{right:100%;top:50%;transform:translateY(-50%);
 margin-right:6px}
.v-ipucu--sağ::after{left:100%;top:50%;transform:translateY(-50%);
 margin-left:6px}
.v-bildiriş-qutusu{position:fixed;right:18px;bottom:18px;z-index:60;
 max-width:min(380px,92vw);box-shadow:0 8px 28px rgba(0,0,0,.22);
 border-radius:var(--v-radius)}
"""


def üslub(icraçı) -> str:
    """Vidjet CSS-i — mətn kimi."""
    return ÜSLUB


def üslublar(icraçı) -> Element:
    """`<head>` daxilinə qoyulan `<style>` elementi."""
    return Element("style", {}, [ÜSLUB])


def səhifə(icraçı, başlıq: Any = "Alqor", məzmun: Any = None,
           dil: Any = "az", əlavəÜslub: Any = None) -> Element:
    """
    Vidjet üslubu hazır tam HTML sənədi — veb üçün.

        qaytar veb.html(vidjet.səhifə(başlıq: "Ana səhifə",
                                      məzmun: [...]))
    """
    baş: list = [
        Element("meta", {"charset": "UTF-8"}),
        Element("meta", {
            "name": "viewport",
            "content": "width=device-width,initial-scale=1"}),
        Element("title", {}, [_m(başlıq, icraçı, "Alqor")]),
        Element("style", {}, [ƏSAS_ÜSLUB + ÜSLUB]),
    ]
    if əlavəÜslub is not None:
        baş.append(Element("style", {}, [_m(əlavəÜslub, icraçı)]))
    return Element("html", {"lang": _m(dil, icraçı, "az")}, [
        Element("head", {}, baş),
        Element("body", {"class": f"{P}gövdə"}, _uşaqlar(məzmun)),
    ])


# `vidjet.səhifə` üçün minimal sənəd üslubu (desktopda `pəncərə` verir)
ƏSAS_ÜSLUB = """
*{box-sizing:border-box}
html,body{margin:0}
body{font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
 background:var(--v-fon);color:var(--v-mətn)}
.v-gövdə{padding:20px;max-width:1100px;margin:0 auto}
"""


_kataloqu_yoxla()
