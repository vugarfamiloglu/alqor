"""
Alqor Studio — `.forma` faylları üçün vizual dizayner (Delphi üslubu).

Dizayner `.forma` faylını `alqor.forma` modeli (`FormaTəsviri`) kimi
oxuyur, əməliyyatı modelə tətbiq edir və faylı `forma.yaz()` ilə
yenidən yazır — fayl həqiqətin yeganə mənbəyidir. Bu moduldakı bütün
funksiyalar saf funksiyadır (fayl sistemi ilə işi server görür):

    model(f)                         → interfeys üçün JSON
    əməliyyat(f, {"növ": …})         → modeli dəyişir (əlavə, sil, köçür,
                                       ad dəyiş, xassə, təkrarla …)
    düzləndir(ölçülər, növ)          → hizalama / bərabər ölçü / paylama
    html(f, qovluq)                  → kətan üçün HƏQİQİ vidjet HTML-i
    metod_əlavə(alq, komponent, ad)  → `.alq`-a `əməl` skeleti (başqa
                                       koda toxunmadan)

Interfeysə gedən dəyərlər: sadə literal JSON kimi, ad (`İstinad`)
`{"$ad": "Baza1"}`, siyahı / lüğət / kortej isə `{"$ifadə": "[1, 2]"}`
(inspektorda mətn kimi redaktə olunur, `forma` sintaksisi ilə oxunur).
"""

from __future__ import annotations

import copy
import inspect
import re
from pathlib import Path
from typing import Any

from alqor import forma as F
from alqor.deyerler import Element
from alqor.forma import FormaTəsviri, ObyektTəsviri, İstinad
from alqor.xeta import XətaToplayıcı

SƏRBƏST = "sərbəst"
TOR = 8                                  # sərbəst düzülüşdə tor addımı (px)
_AD = re.compile(r"^[^\W\d]\w*$")
#  Paletdə əlavə nişan: verilənlər komponentləri və forma konteyneri
VERİLƏNLƏR = "verilənlər"
VERİLƏNLƏR_NÖVLƏRİ = ("VerilənlərBazası", "Sorğu", "naviqator")
#  Yeni obyektin standart adı (Delphi: Button1, Database1 …)
_AD_ÖNÜ = {"VerilənlərBazası": "Baza", "naviqator": "Naviqator",
           "kətan": "Kətan"}
#  Dəyəri olmayan hadisələr (`əməl X_klik()`), qalanları `(dəyər)` alır
_PARAMETRSİZ = ("klik", "göndərildi", "bağlandı")


class FormaDizaynXətası(ValueError):
    pass


# ═══════════════════════════════════════════════════════════════════════
#  Oxuma və JSON
# ═══════════════════════════════════════════════════════════════════════

def oxu(mətn: str, ad: str = "forma.forma", yol: Path | None = None
        ) -> tuple[FormaTəsviri | None, list[dict]]:
    """Mətn → (model və ya None, diaqnostikalar — redaktor formatında)."""
    from .diaqnostika import _lüğət
    x = XətaToplayıcı()
    try:
        f = F.mətndən(mətn, ad, x, yol)
    except RecursionError:
        x.xəta("ALQ-F001", "iç-içəlik çox dərindir")
        f = None
    return f, [_lüğət(d) for d in x._sıralı()]


def dəyər_json(d: Any) -> Any:
    if isinstance(d, İstinad):
        return {"$ad": d.ad}
    if d is None or isinstance(d, (str, bool, int, float)):
        return d
    return {"$ifadə": F.dəyər_yaz(d)}


def literal_oxu(m: str) -> Any:
    """`[1, 2]`, `{"a": 1}`, `"mətn"`, `Baza1` — forma sintaksisi ilə."""
    x = XətaToplayıcı()
    f = F.mətndən(f"forma _\n    _d = {m}\nson\n", "<dəyər>", x)
    if f is None:
        xəta = x.xətalar[0].mesaj if x.xətalar else "yanlış dəyər"
        raise FormaDizaynXətası(f"dəyər oxunmadı: {xəta}")
    return f.xassələr["_d"]


def json_dəyər(d: Any) -> Any:
    if isinstance(d, dict):
        if "$ad" in d:
            ad = str(d["$ad"])
            if not _AD.match(ad.split(".")[0]):
                raise FormaDizaynXətası(f"`{ad}` ad ola bilməz")
            return İstinad(ad)
        if "$ifadə" in d:
            return literal_oxu(str(d["$ifadə"]))
        raise FormaDizaynXətası("naməlum dəyər")
    if d is None or isinstance(d, (str, bool, int, float)):
        return d
    if isinstance(d, list):
        return [json_dəyər(e) for e in d]
    raise FormaDizaynXətası("dəyər mətn, ədəd, məntiq və ya boş olmalıdır")


def görünməzdir(növ: str) -> bool:
    return növ in F.görünməyənlər()


def konteynerdir(növ: str) -> bool:
    """İçinə obyekt qoyula bilən növ: `kətan` və `məzmun`-u element olan
    vidjetlər (`mətn`, `kod`-un `məzmun`-u mətndir — konteyner deyil)."""
    if növ in F.FORMA_KONTEYNERLƏRİ:
        return True
    from alqor import vidjet as V
    f = getattr(V, növ, None) if növ in V.VİDJETLƏR else None
    if f is None:
        return False
    p = inspect.signature(f).parameters.get("məzmun")
    return p is not None and p.default is None


def sərbəstdir(f: FormaTəsviri, ana: str | None) -> bool:
    """`ana`-nın (None — formanın özü) uşaqları mütləq yerləşirmi."""
    if ana is None:
        return f.xassələr.get("düzülüş") == SƏRBƏST
    o = f.tap(ana)
    return o is not None and o.növ == "kətan"


def _obyekt_json(o: ObyektTəsviri) -> dict:
    return {"ad": o.ad, "növ": o.növ,
            "xassələr": {k: dəyər_json(v) for k, v in o.xassələr.items()},
            "uşaqlar": [_obyekt_json(u) for u in o.uşaqlar],
            "görünməz": görünməzdir(o.növ),
            "konteyner": konteynerdir(o.növ)}


def model(f: FormaTəsviri) -> dict:
    return {"ad": f.ad,
            "xassələr": {k: dəyər_json(v) for k, v in f.xassələr.items()},
            "obyektlər": [_obyekt_json(o) for o in f.obyektlər]}


def _json_obyekt(d: dict) -> ObyektTəsviri:
    if not isinstance(d, dict) or not isinstance(d.get("növ"), str):
        raise FormaDizaynXətası("obyekt yanlışdır")
    return ObyektTəsviri(
        str(d.get("ad") or d["növ"]), d["növ"],
        {str(k): json_dəyər(v) for k, v in (d.get("xassələr") or {}).items()},
        [_json_obyekt(u) for u in d.get("uşaqlar") or []])


# ═══════════════════════════════════════════════════════════════════════
#  Ağac köməkçiləri
# ═══════════════════════════════════════════════════════════════════════

def _ana_və_siyahı(f: FormaTəsviri, ad: str
                   ) -> tuple[ObyektTəsviri | None, list[ObyektTəsviri]]:
    def gəz(ana, s):
        for o in s:
            if o.ad == ad:
                return ana, s
            r = gəz(o, o.uşaqlar)
            if r is not None:
                return r
        return None
    r = gəz(None, f.obyektlər)
    if r is None:
        raise FormaDizaynXətası(f"`{ad}` obyekti tapılmadı")
    return r


def _uşaqlar(f: FormaTəsviri, ana: str | None) -> list[ObyektTəsviri]:
    if ana is None:
        return f.obyektlər
    o = f.tap(ana)
    if o is None:
        raise FormaDizaynXətası(f"`{ana}` obyekti tapılmadı")
    if not konteynerdir(o.növ):
        raise FormaDizaynXətası(f"`{o.ad}` ({o.növ}) konteyner deyil — "
                                "içinə obyekt qoyulmur")
    return o.uşaqlar


def _adlar(f: FormaTəsviri) -> set[str]:
    return {o.ad for o in f.hamısı()}


def yeni_ad(f: FormaTəsviri, növ: str, tutulmuş: set[str] | None = None
            ) -> str:
    from alqor.elifba import böyüyə
    ön = _AD_ÖNÜ.get(növ) or (böyüyə(növ[:1]) + növ[1:])
    adlar = _adlar(f) | (tutulmuş or set())
    i = 1
    while f"{ön}{i}" in adlar:
        i += 1
    return f"{ön}{i}"


def _təkrarsız(f: FormaTəsviri, təklif: str, tutulmuş: set[str]) -> str:
    """`Düymə1` tutulubsa `Düymə2` …; rəqəmsiz adlara rəqəm əlavə olunur."""
    adlar = _adlar(f) | tutulmuş
    if təklif not in adlar:
        return təklif
    kök = re.sub(r"\d+$", "", təklif) or təklif
    i = 1
    while f"{kök}{i}" in adlar:
        i += 1
    return f"{kök}{i}"


def standart_xassələr(növ: str, ad: str) -> dict[str, Any]:
    """Paletdən yeni gələn obyektin ilk xassələri (görünsün deyə)."""
    if növ == "kətan":
        return {"en": 320, "hündürlük": 200}
    if növ == "Sorğu" or növ == "naviqator":
        return {}
    if növ == "VerilənlərBazası":
        return {"növ": "sqlite", "fayl": "məlumat.db"}
    p = F._vidjet_parametrləri(növ) or []
    if növ in ("cədvəl",):
        return {"sütunlar": ["Ad", "Dəyər"]}
    for k in ("mətn", "etiket", "başlıq"):
        if k in p:
            return {k: ad}
    if növ in ("mətn", "kod") and "məzmun" in p:
        return {"məzmun": ad}
    return {}


# ═══════════════════════════════════════════════════════════════════════
#  Əməliyyatlar
# ═══════════════════════════════════════════════════════════════════════

def əlavə_et(f: FormaTəsviri, növ: str, ana: str | None = None,
             indeks: int | None = None, xassələr: dict | None = None,
             ad: str | None = None) -> str:
    if növ not in F.məlum_növlər():
        raise FormaDizaynXətası(f"`{növ}` adlı vidjet yoxdur")
    if görünməzdir(növ):
        ana, indeks = None, None      # görünməyənlər həmişə kökün sonunda
    siyahı = _uşaqlar(f, ana)
    if ad:
        if not _AD.match(ad):
            raise FormaDizaynXətası(f"`{ad}` ad ola bilməz")
        if ad in _adlar(f):
            raise FormaDizaynXətası(f"`{ad}` adı artıq var")
    else:
        ad = yeni_ad(f, növ)
    x = standart_xassələr(növ, ad)
    x.update(xassələr or {})
    o = ObyektTəsviri(ad, növ, x)
    siyahı.insert(len(siyahı) if indeks is None else
                  max(0, min(indeks, len(siyahı))), o)
    return ad


def sil(f: FormaTəsviri, adlar: list[str]) -> None:
    for ad in adlar:
        if f.tap(ad) is None:
            continue                  # ana ilə birlikdə artıq silinib
        _, s = _ana_və_siyahı(f, ad)
        s[:] = [o for o in s if o.ad != ad]


def köçür(f: FormaTəsviri, adlar: list[str], ana: str | None,
          indeks: int | None = None) -> None:
    """`adlar`-ı `ana`-nın `indeks` yerinə daşıyır (indeks — daşımadan
    ƏVVƏLKİ siyahıya görə; öz yerinə buraxmaq heç nə dəyişmir)."""
    hədəf = _uşaqlar(f, ana)
    obyektlər = []
    for ad in adlar:
        o = f.tap(ad)
        if o is None:
            raise FormaDizaynXətası(f"`{ad}` obyekti tapılmadı")
        if görünməzdir(o.növ) and ana is not None:
            raise FormaDizaynXətası("görünməyən komponent konteynerə "
                                    "qoyulmur")
        if ana is not None and (ana == ad or
                                any(u.ad == ana for u in _alt(o))):
            raise FormaDizaynXətası("obyekt öz içinə daşına bilməz")
        obyektlər.append(o)
    if indeks is None:
        indeks = len(hədəf)
    indeks = max(0, min(indeks, len(hədəf)))
    # İndeksdən əvvəl gələn və daşınan obyektlər indeksi sürüşdürür
    sürüş = sum(1 for o in hədəf[:indeks] if o in obyektlər)
    for o in obyektlər:
        _, s = _ana_və_siyahı(f, o.ad)
        s.remove(o)
    indeks -= sürüş
    for i, o in enumerate(obyektlər):
        hədəf.insert(indeks + i, o)


def _alt(o: ObyektTəsviri) -> list[ObyektTəsviri]:
    n = []
    for u in o.uşaqlar:
        n.append(u)
        n.extend(_alt(u))
    return n


def ad_dəyiş(f: FormaTəsviri, köhnə: str, yeni: str) -> None:
    o = f.tap(köhnə)
    if o is None:
        raise FormaDizaynXətası(f"`{köhnə}` obyekti tapılmadı")
    if yeni == köhnə:
        return
    if not _AD.match(yeni):
        raise FormaDizaynXətası(f"`{yeni}` ad ola bilməz — hərflə "
                                "başlamalı, yalnız hərf, rəqəm və `_`")
    from alqor.acar_sozler import kanonikləşdir
    if kanonikləşdir(yeni)[0] is not None:
        raise FormaDizaynXətası(f"`{yeni}` açar sözdür — ad ola bilməz")
    if yeni in _adlar(f):
        raise FormaDizaynXətası(f"`{yeni}` adı artıq var")
    o.ad = yeni
    # Bu obyektə istinadlar (`mənbə = Sorğu1`, `baza = Baza1`)
    for x in f.hamısı():
        for k, v in x.xassələr.items():
            if isinstance(v, İstinad) and v.ad == köhnə and \
                    not F.hadisədir(x.növ, k):
                x.xassələr[k] = İstinad(yeni)


def xassə_qoy(f: FormaTəsviri, ad: str | None, xassə: str, dəyər: Any
              ) -> None:
    """`dəyər` None-dursa xassə silinir (standart dəyər işləyir)."""
    if not _AD.match(xassə):
        raise FormaDizaynXətası(f"`{xassə}` xassə adı ola bilməz")
    if ad is None:
        hədəf = f.xassələr
    else:
        o = f.tap(ad)
        if o is None:
            raise FormaDizaynXətası(f"`{ad}` obyekti tapılmadı")
        hədəf = o.xassələr
    if dəyər is None or dəyər == "" and xassə in ("sol", "yuxarı", "en",
                                                  "hündürlük"):
        hədəf.pop(xassə, None)
    else:
        hədəf[xassə] = dəyər


def təkrarla(f: FormaTəsviri, adlar: list[str]) -> list[str]:
    """Hər obyektin surəti ondan sonra (sərbəst düzülüşdə +8 px)."""
    yeni: list[str] = []
    for ad in adlar:
        o = f.tap(ad)
        if o is None:
            continue
        ana, s = _ana_və_siyahı(f, ad)
        k = copy.deepcopy(o)
        _adlandır(f, k, set(yeni))
        if sərbəstdir(f, ana.ad if ana else None):
            for p in ("sol", "yuxarı"):
                if isinstance(k.xassələr.get(p), (int, float)):
                    k.xassələr[p] += TOR * 2
        s.insert(s.index(o) + 1, k)
        yeni.append(k.ad)
    return yeni


def _adlandır(f: FormaTəsviri, o: ObyektTəsviri, tutulmuş: set[str]
              ) -> None:
    """Surət üçün yeni adlar; mətn xassəsi köhnə ad idisə o da dəyişir."""
    köhnə = o.ad
    o.ad = _təkrarsız(f, o.ad, tutulmuş)
    tutulmuş.add(o.ad)
    for k in ("mətn", "etiket", "başlıq"):
        if o.xassələr.get(k) == köhnə:
            o.xassələr[k] = o.ad
    # Hadisə idarəedicisi orijinala aiddir — surət öz idarəedicisini alsın
    for k in list(o.xassələr):
        if isinstance(o.xassələr[k], İstinad) and F.hadisədir(o.növ, k):
            del o.xassələr[k]
    for u in o.uşaqlar:
        _adlandır(f, u, tutulmuş)


def yapışdır(f: FormaTəsviri, obyektlər: list[dict], ana: str | None,
             indeks: int | None = None, sürüş: int = 0) -> list[str]:
    """Buferdəki obyektlər (`model()`-in obyekt JSON-u) — yeni adlarla."""
    hədəf = _uşaqlar(f, ana)
    if indeks is None:
        indeks = len(hədəf)
    yeni: list[str] = []
    tutulmuş: set[str] = set()
    for d in obyektlər:
        o = _json_obyekt(d)
        if o.növ not in F.məlum_növlər():
            raise FormaDizaynXətası(f"`{o.növ}` adlı vidjet yoxdur")
        _adlandır(f, o, tutulmuş)
        if sürüş:
            for p in ("sol", "yuxarı"):
                if isinstance(o.xassələr.get(p), (int, float)):
                    o.xassələr[p] += sürüş
        if görünməzdir(o.növ):
            f.obyektlər.append(o)
        else:
            hədəf.insert(min(indeks, len(hədəf)), o)
            indeks += 1
        yeni.append(o.ad)
    return yeni


# ── Hizalama (Delphi: Align / Size / Space Equally) ─────────────────────

DÜZLƏNDİRMƏLƏR = ("sol", "sağ", "yuxarı", "aşağı", "üfüqiMərkəz",
                  "şaquliMərkəz", "eyniEn", "eyniHündürlük", "eyniÖlçü",
                  "üfüqiPaylaş", "şaquliPaylaş")


def düzləndir(ölçülər: dict[str, dict[str, float]], növ: str
              ) -> dict[str, dict[str, int]]:
    """
    `ölçülər` — {ad: {sol, yuxarı, en, hündürlük}} (seçim sırası ilə,
    ilki — istinad obyekti, Delphi-dəki kimi). Qaytarır: dəyişən
    xassələr {ad: {xassə: dəyər}}.
    """
    if növ not in DÜZLƏNDİRMƏLƏR:
        raise FormaDizaynXətası(f"naməlum düzləndirmə: {növ}")
    adlar = list(ölçülər)
    if len(adlar) < 2:
        return {}
    g = {a: {k: float(ölçülər[a].get(k) or 0)
             for k in ("sol", "yuxarı", "en", "hündürlük")} for a in adlar}
    i = g[adlar[0]]
    n: dict[str, dict[str, int]] = {}

    def qoy(a, k, d):
        n.setdefault(a, {})[k] = int(round(d))

    for a in adlar[1:]:
        x = g[a]
        if növ == "sol":
            qoy(a, "sol", i["sol"])
        elif növ == "sağ":
            qoy(a, "sol", i["sol"] + i["en"] - x["en"])
        elif növ == "yuxarı":
            qoy(a, "yuxarı", i["yuxarı"])
        elif növ == "aşağı":
            qoy(a, "yuxarı", i["yuxarı"] + i["hündürlük"] - x["hündürlük"])
        elif növ == "üfüqiMərkəz":
            qoy(a, "sol", i["sol"] + (i["en"] - x["en"]) / 2)
        elif növ == "şaquliMərkəz":
            qoy(a, "yuxarı", i["yuxarı"] + (i["hündürlük"] - x["hündürlük"]) / 2)
        if növ in ("eyniEn", "eyniÖlçü"):
            qoy(a, "en", i["en"])
        if növ in ("eyniHündürlük", "eyniÖlçü"):
            qoy(a, "hündürlük", i["hündürlük"])
    if növ in ("üfüqiPaylaş", "şaquliPaylaş") and len(adlar) >= 3:
        p, ö = ("sol", "en") if növ == "üfüqiPaylaş" else ("yuxarı",
                                                          "hündürlük")
        sıra = sorted(adlar, key=lambda a: g[a][p])
        baş = g[sıra[0]][p]
        son = g[sıra[-1]][p] + g[sıra[-1]][ö]
        cəm = sum(g[a][ö] for a in sıra)
        ara = (son - baş - cəm) / (len(sıra) - 1)
        x = baş
        for a in sıra:
            if a not in (sıra[0], sıra[-1]):
                qoy(a, p, x)
            x += g[a][ö] + ara
    return n


def əməliyyat(f: FormaTəsviri, ə: dict, sxem: Any = None) -> dict:
    """
    Bir dizayner əməliyyatı. Qaytarır: {"seçim": [adlar]} — əməliyyatdan
    sonra seçilməli obyektlər (None — seçim dəyişmir).
    """
    növ = ə.get("növ")

    def adlar() -> list[str]:
        a = ə.get("adlar")
        if not isinstance(a, list) or not all(isinstance(x, str) for x in a):
            raise FormaDizaynXətası("`adlar` mətn siyahısı olmalıdır")
        return a

    def ana() -> str | None:
        a = ə.get("ana")
        return a if isinstance(a, str) and a else None

    def indeks() -> int | None:
        i = ə.get("indeks")
        return i if isinstance(i, int) and not isinstance(i, bool) else None

    if növ == "əlavə":
        x = {str(k): json_dəyər(v) for k, v in
             (ə.get("xassələr") or {}).items()}
        ad = əlavə_et(f, str(ə.get("vidjet") or ""), ana(), indeks(), x)
        return {"seçim": [ad]}
    if növ == "sil":
        sil(f, adlar())
        return {"seçim": []}
    if növ == "köçür":
        köçür(f, adlar(), ana(), indeks())
        for ad, x in (ə.get("xassələr") or {}).items():
            for k, v in x.items():
                xassə_qoy(f, ad, k, json_dəyər(v))
        return {"seçim": adlar()}
    if növ == "adDəyiş":
        ad_dəyiş(f, str(ə.get("ad") or ""), str(ə.get("yeni") or "").strip())
        return {"seçim": [str(ə.get("yeni")).strip()]}
    if növ == "xassə":
        a = ə.get("ad")
        xassə_qoy(f, a if isinstance(a, str) and a else None,
                  str(ə.get("xassə") or ""), json_dəyər(ə.get("dəyər")))
        return {"seçim": None}
    if növ == "xassələr":
        # {ad: {xassə: dəyər}}; "" açarı — formanın özü
        for ad, x in (ə.get("dəyişikliklər") or {}).items():
            if not isinstance(x, dict):
                raise FormaDizaynXətası("dəyişikliklər lüğət olmalıdır")
            for k, v in x.items():
                xassə_qoy(f, ad or None, str(k), json_dəyər(v))
        return {"seçim": None}
    if növ == "təkrarla":
        return {"seçim": təkrarla(f, adlar())}
    if növ == "yapışdır":
        o = ə.get("obyektlər")
        if not isinstance(o, list):
            raise FormaDizaynXətası("`obyektlər` siyahı olmalıdır")
        sürüş = TOR * 2 if sərbəstdir(f, ana()) else 0
        return {"seçim": yapışdır(f, o, ana(), indeks(), sürüş)}
    if növ == "düzləndir":
        ö = ə.get("ölçülər")
        if not isinstance(ö, dict):
            raise FormaDizaynXətası("`ölçülər` lüğət olmalıdır")
        for ad, x in düzləndir(ö, str(ə.get("necə") or "")).items():
            for k, v in x.items():
                xassə_qoy(f, ad, k, v)
        return {"seçim": None}
    if növ == "crud":
        if sxem is None:
            raise FormaDizaynXətası("sxem yoxdur — əvvəlcə cədvəlləri "
                                    "yaradın")
        return {"seçim": crud_əlavə(f, sxem, str(ə.get("cədvəl") or ""),
                                    str(ə.get("baza") or ""))}
    raise FormaDizaynXətası(f"naməlum əməliyyat: {növ}")


def crud_əlavə(f: FormaTəsviri, sxem: Any, cədvəl: str, baza: str
               ) -> list[str]:
    """«Cədvəldən forma yarat»: Sorğu + cədvəl + sahələr + naviqator."""
    from alqor.forma_verilenler import crud_obyektləri
    b = f.tap(baza) if baza else None
    if b is None or b.növ != "VerilənlərBazası":
        raise FormaDizaynXətası("VerilənlərBazası komponenti seçilməyib")
    try:
        yeni = crud_obyektləri(sxem, cədvəl, baza, _adlar(f))
    except ValueError as x:
        raise FormaDizaynXətası(str(x)) from None
    # Sorğu görünməyənlərin yanına, görünənlər formanın sonuna
    for o in yeni:
        f.obyektlər.append(o)
    return [o.ad for o in yeni]


# ═══════════════════════════════════════════════════════════════════════
#  Kataloq (palet + inspektor üçün)
# ═══════════════════════════════════════════════════════════════════════

_MƏNTİQ_ADLARI = {"tələb", "söndürülmüş", "oxunaqlı", "zolaqlı",
                  "çərçivəli", "tamEn", "gözləyir", "işarələnmiş", "yanıq",
                  "üfüqi", "görünür", "açılmış", "faizGöstər", "kənar",
                  "seçilmiş", "təhlükəli", "basılı"}
_ƏDƏD_ADLARI = {"en", "hündürlük", "sol", "yuxarı", "boşluq", "sütunlar",
                "səviyyə", "dəyər", "minimum", "maksimum", "addım",
                "sətirlər", "ölçü"}


def _param_növü(vidjet: str, p: str, standart: Any) -> tuple[str, list | None]:
    from .xususiyyet import İFADƏLƏR, RƏNGLƏR, _seçimlər
    s = _seçimlər(vidjet, p)
    if s:
        return "seçim", s
    if p in RƏNGLƏR:
        return "rəng", None
    if isinstance(standart, bool) or (standart is None and p in _MƏNTİQ_ADLARI):
        return "məntiq", None
    if isinstance(standart, (int, float)):
        return "ədəd", None
    if p in İFADƏLƏR or p == "üslub" or isinstance(standart,
                                                   (list, dict, tuple)):
        return "ifadə", None
    return "mətn", None


def _parametrlər(növ: str) -> list[dict]:
    from alqor import vidjet as V
    from alqor import vidjet_arayis as AR
    from .xususiyyet import HADİSƏLƏR
    m = next((x for x in V.KATALOQ if x.ad == növ), None)
    hadisələr = set(m.hadisələr) if m else set()
    n = []
    for p, d in AR.parametrlər(növ):
        if p in hadisələr or p in HADİSƏLƏR:
            continue
        if p == "məzmun" and konteynerdir(növ):
            continue
        standart = None if d is inspect.Parameter.empty else d
        k, s = _param_növü(növ, p, standart)
        n.append({"ad": p, "növ": k, "seçimlər": s,
                  "izah": AR.izah(növ, p) or "",
                  "standart": standart if isinstance(
                      standart, (str, int, float, bool)) else None})
    return n


def kataloq() -> dict:
    from alqor import vidjet as V
    from alqor.forma_verilenler import KOMPONENTLƏR
    növlər: dict[str, dict] = {}
    for m in V.KATALOQ:
        növlər[m.ad] = {
            "ad": m.ad, "beynəlxalqAd": V.BEYNƏLXALQ_ADLAR.get(m.ad, m.ad),
            "kateqoriya": m.kateqoriya, "izah": m.izah,
            "hadisələr": list(m.hadisələr), "parametrlər": _parametrlər(m.ad),
            "konteyner": konteynerdir(m.ad), "görünməz": False}
    növlər["kətan"] = {
        "ad": "kətan", "beynəlxalqAd": "Canvas", "kateqoriya": "düzülüş",
        "izah": "Sərbəst yerləşmə: içindəki obyektlər sol/yuxarı ilə",
        "hadisələr": [], "parametrlər": [], "konteyner": True,
        "görünməz": False}
    növlər["naviqator"] = {
        "ad": "naviqator", "beynəlxalqAd": "DB Navigator",
        "kateqoriya": VERİLƏNLƏR,
        "izah": "Sorğunun sətirləri arasında gəzmək: ⏮ ◀ ▶ ⏭ ＋ 🗑 💾",
        "hadisələr": [], "konteyner": False, "görünməz": False,
        "parametrlər": [{"ad": "düymələr", "növ": "ifadə", "seçimlər": None,
                         "standart": None,
                         "izah": "göstərilən düymələr: [\"ilk\", \"son\", …]"}]}
    izahlar = {"VerilənlərBazası": ("Database", "Bazaya qoşulma (sqlite, "
                                    "postgres, mysql) + .sxem cədvəlləri"),
               "Sorğu": ("Query / Table", "Cədvəl + cari sətir; vidjetlər "
                         "`mənbə` ilə bağlanır")}
    for ad, sinif in KOMPONENTLƏR.items():
        b, izah = izahlar.get(ad, (ad, ""))
        növlər[ad] = {
            "ad": ad, "beynəlxalqAd": b, "kateqoriya": VERİLƏNLƏR,
            "izah": izah, "hadisələr": [], "konteyner": False,
            "görünməz": True, "metodlar": dict(sinif.METODLAR),
            "parametrlər": [{
                "ad": k, "növ": ("istinad" if k == "baza" else
                                 "məntiq" if isinstance(d, bool) else
                                 "ədəd" if isinstance(d, (int, float))
                                 or k in ("port", "limit") else
                                 "ifadə" if isinstance(d, (dict, list)) else
                                 "seçim" if k == "növ" else "mətn"),
                "seçimlər": ["sqlite", "postgres", "mysql"] if k == "növ"
                else None, "izah": izah_,
                "standart": d if isinstance(d, (str, int, float, bool))
                else None} for k, (d, izah_) in sinif.XASSƏLƏR.items()]}
    kateqoriyalar = [{"ad": k, "başlıq": _KATEQORİYA_ADI.get(k, k),
                      "beynəlxalq": V.KATEQORİYA_BEYNƏLXALQ.get(k, k)}
                     for k in V.KATEQORİYALAR]
    kateqoriyalar.append({"ad": VERİLƏNLƏR, "başlıq": "Verilənlər",
                          "beynəlxalq": "Data Access"})
    from .xususiyyet import RƏNGLƏR  # noqa: F401  (inspektor rəngləri)
    return {
        "kateqoriyalar": kateqoriyalar,
        "növlər": növlər,
        "kök": [
            {"ad": "başlıq", "növ": "mətn", "izah": "Pəncərənin başlığı"},
            {"ad": "en", "növ": "ədəd", "izah": "Pəncərənin eni, px",
             "standart": 800},
            {"ad": "hündürlük", "növ": "ədəd",
             "izah": "Pəncərənin hündürlüyü, px", "standart": 600},
            {"ad": "düzülüş", "növ": "seçim", "seçimlər": ["axın", SƏRBƏST],
             "izah": "axın — obyektlər alt-alta; sərbəst — sol/yuxarı ilə",
             "standart": "axın"},
            {"ad": "boşluq", "növ": "ədəd",
             "izah": "Axın düzülüşündə obyektlər arası məsafə, px",
             "standart": 12},
            {"ad": "mərkəzə", "növ": "məntiq",
             "izah": "Pəncərə ekranın mərkəzində açılsın"},
            {"ad": "ölçüsüSabit", "növ": "məntiq",
             "izah": "İstifadəçi pəncərənin ölçüsünü dəyişə bilməsin"},
        ],
        "ortaq": [
            {"ad": "görünür", "növ": "məntiq", "standart": True,
             "izah": "yanlış — obyekt göstərilmir (kodda özü.Ad.göstər())"},
            {"ad": "sol", "növ": "ədəd", "izah": "Sərbəst düzülüşdə sol, px"},
            {"ad": "yuxarı", "növ": "ədəd",
             "izah": "Sərbəst düzülüşdə yuxarı, px"},
            {"ad": "en", "növ": "ədəd", "izah": "En, px"},
            {"ad": "hündürlük", "növ": "ədəd", "izah": "Hündürlük, px"},
        ],
        "bağlama": [
            {"ad": "mənbə", "növ": "sorğu",
             "izah": "Sorğu komponenti — vidjet onun cari sətrini göstərir"},
            {"ad": "sütun", "növ": "sütun",
             "izah": "Sorğunun sütunu (cədvəl üçün lazım deyil)"},
        ],
        "tor": TOR,
    }


_KATEQORİYA_ADI = {"form": "Forma", "göstərmə": "Göstərmə",
                   "vəziyyət": "Vəziyyət", "düzülüş": "Düzülüş",
                   "naviqasiya": "Naviqasiya", "üst qat": "Üst qat"}


# ═══════════════════════════════════════════════════════════════════════
#  Verilənlər: sxem və sütunlar (inspektordakı açılan siyahılar üçün)
# ═══════════════════════════════════════════════════════════════════════

def sxem_yolu(f: FormaTəsviri, baza: str, qovluq: Path) -> Path:
    """Komponentin `.sxem` faylı: `sxem` xassəsi və ya `<baza>.sxem`."""
    o = f.tap(baza)
    if o is None or o.növ != "VerilənlərBazası":
        raise FormaDizaynXətası(f"`{baza}` VerilənlərBazası deyil")
    ad = o.xassələr.get("sxem")
    if isinstance(ad, str) and ad.strip():
        return qovluq / ad.strip()
    return qovluq / f"{baza}.sxem"


def sxem_oxu(yol: Path) -> tuple[Any, list[str]]:
    """(Sxem və ya None, xəta mesajları)."""
    from alqor import sxem as S
    if not yol.is_file():
        return None, []
    x = XətaToplayıcı()
    try:
        s = S.fayldan(yol, x)
    except (OSError, UnicodeDecodeError) as e:
        return None, [str(e)]
    return s, [f"{d.kod}: {d.mesaj}" for d in x.xətalar]


def verilənlər(f: FormaTəsviri, qovluq: Path | None) -> dict:
    """{"bazalar": {Baza1: {sxem, cədvəllər: {t: [sütun]}, xətalar}},
        "sorğular": {Sorğu1: {baza, cədvəl, sütunlar}}}"""
    bazalar: dict[str, dict] = {}
    sxemlər: dict[str, Any] = {}
    for o in f.hamısı():
        if o.növ != "VerilənlərBazası":
            continue
        d: dict[str, Any] = {"sxem": None, "cədvəllər": {}, "xətalar": [],
                             "var": False}
        if qovluq is not None:
            y = sxem_yolu(f, o.ad, qovluq)
            d["sxem"] = y.name
            s, xətalar = sxem_oxu(y)
            d["var"] = y.is_file()
            d["xətalar"] = xətalar
            if s is not None:
                sxemlər[o.ad] = s
                d["cədvəllər"] = {c.ad: [x.ad for x in c.sahələr]
                                  for c in s.cədvəllər}
        bazalar[o.ad] = d
    sorğular: dict[str, dict] = {}
    for o in f.hamısı():
        if o.növ != "Sorğu":
            continue
        b = o.xassələr.get("baza")
        b = b.ad if isinstance(b, İstinad) else None
        c = o.xassələr.get("cədvəl")
        c = c if isinstance(c, str) else None
        sütunlar = bazalar.get(b or "", {}).get("cədvəllər", {}).get(c or "",
                                                                     [])
        sorğular[o.ad] = {"baza": b, "cədvəl": c, "sütunlar": sütunlar}
    return {"bazalar": bazalar, "sorğular": sorğular}


# ═══════════════════════════════════════════════════════════════════════
#  Kətan: həqiqi vidjet HTML-i (dizayn rejimi)
# ═══════════════════════════════════════════════════════════════════════

def _ölçü(v: Any) -> str:
    return f"{v}px" if isinstance(v, (int, float)) and \
        not isinstance(v, bool) else str(v)


def html(f: FormaTəsviri, qovluq: Path | None = None) -> str:
    """
    Formanın görünüşü — işləyən proqramdakı kimi, `vidjet` modulunun
    özü ilə qurulur. Hər obyekt `<div class="dz-o" data-dz="Ad">`
    içindədir (seçim üçün). Görünməyən komponentlər çəkilmir; hadisələr
    bağlanmır; bazaya qoşulmur (bağlı cədvəl sxemdəki sütunları göstərir).
    """
    from alqor import vidjet as V
    from alqor import forma_verilenler as FV
    from alqor.icraci import İcraçı
    from types import SimpleNamespace

    i = İcraçı(çıxış=lambda *_: None)
    məl = verilənlər(f, qovluq)

    def obyekt(o: ObyektTəsviri, mütləq: bool) -> Element | None:
        if görünməzdir(o.növ):
            return None
        sinif = "dz-o"
        if o.xassələr.get("görünür", True) is False:
            sinif += " dz-gizli"
        if o.növ == "naviqator":
            e = FV.naviqator(i, SimpleNamespace(ad=o.ad,
                                                xassələr=o.xassələr), None)
        elif o.növ == "kətan":
            uşaqlar = [x for x in (obyekt(u, True) for u in o.uşaqlar)
                       if x is not None]
            üslub = "position:relative;"
            for k, css in (("en", "width"), ("hündürlük", "height")):
                if k in o.xassələr:
                    üslub += f"{css}:{_ölçü(o.xassələr[k])};"
            e = Element("div", {"class": "a-kətan dz-kətan", "style": üslub},
                        uşaqlar)
        else:
            e = _vidjet(V, i, o, məl, obyekt)
        üslub = ""
        if mütləq:
            üslub = "position:absolute;"
            for k, css in (("sol", "left"), ("yuxarı", "top"),
                           ("en", "width"), ("hündürlük", "height")):
                if k in o.xassələr:
                    üslub += f"{css}:{_ölçü(o.xassələr[k])};"
        elif o.növ != "kətan":
            icazəli = F._vidjet_parametrləri(o.növ) or []
            for k, css in (("en", "width"), ("hündürlük", "height")):
                if k in o.xassələr and k not in icazəli:
                    üslub += f"{css}:{_ölçü(o.xassələr[k])};"
        a = {"class": sinif, "data-dz": o.ad, "data-nov": o.növ}
        if konteynerdir(o.növ):
            a["data-konteyner"] = "1"
        if o.növ == "kətan":
            a["data-serbest"] = "1"
        if üslub:
            a["style"] = üslub
        return Element("div", a, [e])

    sərbəst = f.xassələr.get("düzülüş") == SƏRBƏST
    uşaqlar = [e for e in (obyekt(o, sərbəst) for o in f.obyektlər)
               if e is not None]
    if sərbəst:
        kök = Element("div", {"class": "a-forma a-kətan dz-kök",
                              "data-serbest": "1",
                              "style": "position:relative;min-height:100%"},
                      uşaqlar)
    else:
        kök = Element("div", {"class": "a-forma dz-kök",
                              "style": "display:flex;flex-direction:column;"
                                       f"gap:{_ölçü(f.xassələr.get('boşluq', 12))};"
                                       "padding:16px;min-height:100%"},
                      uşaqlar)
    return kök.HTML(i)


def _vidjet(V, i, o: ObyektTəsviri, məl: dict, obyekt) -> Element:
    vf = getattr(V, o.növ, None)
    if vf is None:
        return Element("div", {"class": "dz-xəta"}, [f"{o.növ}?"])
    icazəli = F._vidjet_parametrləri(o.növ) or []
    hadisələr = next((m.hadisələr for m in V.KATALOQ if m.ad == o.növ), [])
    adlı: dict[str, Any] = {}
    for k, v in o.xassələr.items():
        if k not in icazəli or k in hadisələr or isinstance(v, İstinad):
            continue
        adlı[k] = v
    if konteynerdir(o.növ):
        uşaqlar = [x for x in (obyekt(u, False) for u in o.uşaqlar)
                   if x is not None]
        if not uşaqlar:
            uşaqlar = [Element("div", {"class": "dz-boş"},
                               ["Bura element sürükləyin"])]
        adlı["məzmun"] = uşaqlar
    # Məlumat bağlaması: bazaya qoşulmadan — sxemdəki sütunlar
    mənbə = o.xassələr.get("mənbə")
    if isinstance(mənbə, İstinad):
        sorğu = məl["sorğular"].get(mənbə.ad) or {}
        if o.növ == "cədvəl" and "sütunlar" not in adlı:
            adlı["sütunlar"] = sorğu.get("sütunlar") or ["…"]
            adlı.setdefault("boşMətn", f"{mənbə.ad} sətirləri")
        sütun = o.xassələr.get("sütun")
        if isinstance(sütun, str) and sütun:
            if "yer" in icazəli and "yer" not in adlı:
                adlı["yer"] = f"‹{sütun}›"
            elif "mətn" in icazəli and "mətn" not in adlı:
                adlı["mətn"] = f"‹{sütun}›"
            elif o.növ == "mətn" and "məzmun" not in adlı:
                adlı["məzmun"] = f"‹{sütun}›"
    try:
        return vf(i, **adlı)
    except Exception as x:                              # noqa: BLE001
        return Element("div", {"class": "dz-xəta"},
                       [f"{o.ad}: {type(x).__name__}: {x}"])


# ═══════════════════════════════════════════════════════════════════════
#  `.alq` — komponent metodları (hadisə idarəediciləri)
# ═══════════════════════════════════════════════════════════════════════

def _komponent(mətn: str, ad: str):
    from .qurulus import Mətn, komponentləri_tap
    t = Mətn(mətn)
    return t, next((k for k in komponentləri_tap(t) if k.ad == ad), None)


def metodlar(mətn: str, komponent: str) -> list[str]:
    """`komponent Ad`-ın `əməl` (və `metod`) adları, sıra ilə."""
    _, k = _komponent(mətn, komponent)
    if k is None:
        return []
    return [u.ad for u in k.üzvlər if u.növ in ("əməl", "metod") and u.ad]


def hadisə_metodu(obyekt: str, hadisə: str) -> str:
    return f"{obyekt}_{hadisə}"


def metod_əlavə(mətn: str, komponent: str, ad: str,
                parametrlər: str = "", şərh: str = "") -> tuple[str, int]:
    """
    `komponent`-ə `əməl ad(parametrlər) … son` skeleti əlavə edir —
    komponentin sonuna, başqa sətirlərə toxunmadan. Metod artıq varsa
    mətn dəyişmir. Qaytarır: (mətn, metodun gövdəsinin sətri — 1-dən).
    """
    t, k = _komponent(mətn, komponent)
    if k is not None:
        for u in k.üzvlər:
            if u.ad == ad and u.növ in ("əməl", "metod"):
                return mətn, u.baş + 2
    sətirlər = mətn.split("\n")
    if k is None or k.son is None:
        # Komponent yoxdur — faylın sonuna yeni komponent
        n = mətn.rstrip("\n")
        əlavə = [f"komponent {komponent}"] + _skelet(ad, parametrlər, şərh,
                                                    "    ") + ["son"]
        baş = len(n.split("\n")) + (2 if n else 0)
        yeni = (n + "\n\n" if n else "") + "\n".join(əlavə) + "\n"
        return yeni, baş + 2
    g = " " * k.üzv_girintisi
    yer = k.son                                  # `son` sətrindən əvvəl
    blok = _skelet(ad, parametrlər, şərh, g)
    # Əvvəlki üzvdən boş sətirlə ayrılsın
    əvvəl = yer - 1
    while əvvəl > k.baş and not sətirlər[əvvəl].strip():
        əvvəl -= 1
    if əvvəl > k.baş:
        blok = [""] + blok
    sətirlər[əvvəl + 1:yer] = blok
    gövdə = əvvəl + 1 + (1 if əvvəl > k.baş else 0) + 2
    return "\n".join(sətirlər), gövdə


def _skelet(ad: str, parametrlər: str, şərh: str, g: str) -> list[str]:
    return [f"{g}əməl {ad}({parametrlər})",
            f"{g}    // {şərh or 'hadisə baş verəndə işləyir'}",
            f"{g}son"]


def hadisə_parametrləri(hadisə: str) -> str:
    return "" if hadisə in _PARAMETRSİZ else "dəyər"


# ═══════════════════════════════════════════════════════════════════════
#  Yeni forma («Fayl → Yeni forma…»)
# ═══════════════════════════════════════════════════════════════════════

def yeni_forma(ad: str) -> tuple[str, str]:
    """(`Ad.forma` mətni, `Ad.alq` mətni)."""
    if not _AD.match(ad):
        raise FormaDizaynXətası(f"`{ad}` forma adı ola bilməz — hərflə "
                                "başlamalı, yalnız hərf, rəqəm və `_`")
    f = FormaTəsviri(ad, {"başlıq": ad, "en": 640, "hündürlük": 480})
    kod = (f"// {ad}.alq — `{ad}.forma` formasının kodu. Hadisə "
           "idarəedicilərini\n// dizayner bura yazır "
           "(obyektə iki klik).\n\n"
           "gətir pəncərə\n\n"
           f"komponent {ad}\nson\n\n"
           "funksiya əsas()\n"
           f"    pəncərə.formaAç({ad})\n"
           "    pəncərə.işlət()\n"
           "son\n")
    return F.yaz(f), kod
