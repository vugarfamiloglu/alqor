"""
Alqor — Statik tip yoxlayıcı (tədrici tiplər).

## Fəlsəfə

Yanlış xəbərdarlıq verən yoxlayıcı heç yoxlayıcıdan pisdir. Ona görə
əsas qayda: **yalnız ƏMİN OLDUĞUMUZ halda xəta bildir.** Hər hansı
operandın tipi `istənilən` və ya naməlumdursa, yoxlama atlanır.

## Üç sərtlik rejimi (`layihe.alq` → `[tip] rejim`)

| Rejim | Davranış |
|---|---|
| `sərbəst` | Yalnız açıq yazılmış tiplər yoxlanılır |
| `normal` | Çıxarma + yoxlama (standart) |
| `sərt` | Açıq funksiya imzaları məcburi, naməlum üzvlər xətadır |

## Axın əsaslı daralma

    əgər x tipidir mətn onda
        yaz(x.böyüyə())      ← x burada `mətn` kimi tanınır
    son

    varsa i = tap() onda
        yaz(i.ad)            ← i burada ixtiyari deyil
    son
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from . import aac as A
from . import tipler as T
from .token import Yer
from .xeta import XətaToplayıcı

REJİMLƏR = ("sərbəst", "normal", "sərt")

# Qeyd rejimində `Əhatə.elan` bütün elanları bura yazır (sapa bağlı
# deyil — `alqorls` analizi ardıcıl aparır)
_QEYD_SİYAHISI: list | None = None

# Fayl modulları (`gətir "./x.alq"`): həll olunmuş yol → (açar, tip).
# Açar faylın vəziyyətidir (mtime/ölçü və ya redaktordakı mətn).
_FAYL_KEŞİ: dict[str, tuple[Any, T.ModulTipi]] = {}
_YÜKLƏNİR: set[str] = set()
# `alqorls` açıq sənədlərin (yaddaşdakı, saxlanmamış) mətnini verir:
#   Path → str | None
FAYL_MƏTNİ: Any = None


# ═══════════════════════════════════════════════════════════════════════
#  Əhatə dairəsi
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Bağlama:
    ad: str
    tip: T.Tip
    sabit: bool = False
    yer: Yer | None = None
    istifadə_olunub: bool = False
    elan_növü: str = "dəyişən"      # dəyişən | parametr | funksiya | sinif
    # `gətir "./x.alq".{f}` — idxal olunan adın həmin fayldakı elanı
    mənşə: "Bağlama | None" = None


class Əhatə:
    __slots__ = ("adlar", "üst", "növ", "qaytarma", "dövrdə", "generator",
                 "asinxron", "son_ifadə_tipi", "son_ifadə_yeri")

    def __init__(self, üst: "Əhatə | None" = None, növ: str = "blok",
                 qaytarma: T.Tip | None = None):
        self.adlar: dict[str, Bağlama] = {}
        self.üst = üst
        self.növ = növ
        self.qaytarma = qaytarma
        self.dövrdə = üst.dövrdə if üst else False
        self.generator = üst.generator if üst else False
        self.asinxron = üst.asinxron if üst else False
        # Son ifadə avtomatik qaytarılır (Spes. § 5.3) — tipi yoxlanmalıdır
        self.son_ifadə_tipi: T.Tip | None = None
        self.son_ifadə_yeri: Yer | None = None

    def tap(self, ad: str) -> Bağlama | None:
        ə: Əhatə | None = self
        while ə is not None:
            if ad in ə.adlar:
                return ə.adlar[ad]
            ə = ə.üst
        return None

    def yerli_tap(self, ad: str) -> Bağlama | None:
        return self.adlar.get(ad)

    def elan(self, b: Bağlama) -> None:
        self.adlar[b.ad] = b
        if _QEYD_SİYAHISI is not None and b.yer is not None:
            _QEYD_SİYAHISI.append(b)

    def funksiya_əhatəsi(self) -> "Əhatə | None":
        ə: Əhatə | None = self
        while ə is not None:
            if ə.növ == "funksiya":
                return ə
            ə = ə.üst
        return None

    def alt(self, növ: str = "blok",
            qaytarma: T.Tip | None = None) -> "Əhatə":
        return Əhatə(self, növ, qaytarma)


# ═══════════════════════════════════════════════════════════════════════
#  İmza köməkçiləri
# ═══════════════════════════════════════════════════════════════════════

def F(*parametrlər: T.Tip, qaytarır: T.Tip = T.NAMƏLUM,
      standart: int = 0, variadic: bool = False) -> T.FunksiyaTipi:
    """
    Qısa imza qurucusu.

    `standart` — sonuncu N parametrin standart dəyəri var (ixtiyari).
    """
    n = len(parametrlər)
    p: list[T.Parametr] = []
    for i, t in enumerate(parametrlər):
        p.append(T.Parametr(
            f"a{i}", t,
            standartı_var=(i >= n - standart) if standart else False,
            variadic=(variadic and i == n - 1)))
    return T.FunksiyaTipi(tuple(p), qaytarır)


def Fsərbəst(qaytarır: T.Tip = T.NAMƏLUM) -> T.FunksiyaTipi:
    """Arqument sayı yoxlanılmayan funksiya."""
    return T.FunksiyaTipi(
        (T.Parametr("a", T.İSTƏNİLƏN, variadic=True),), qaytarır)


# ═══════════════════════════════════════════════════════════════════════
#  Daxili funksiyalar
# ═══════════════════════════════════════════════════════════════════════

def _daxili_adlar() -> dict[str, T.Tip]:
    i, m, t, b = T.TAM, T.MƏTN, T.NAMƏLUM, T.MƏNTİQ
    o, h, e = T.ONLUQ, T.HEÇ, T.İSTƏNİLƏN

    d: dict[str, T.Tip] = {
        # Giriş / çıxış
        "yaz": Fsərbəst(h),
        "yazSətirsiz": Fsərbəst(h),
        "yazXəta": Fsərbəst(h),
        "oxu": F(m, qaytarır=m, standart=1),
        "oxuTam": F(m, b, qaytarır=i, standart=2),
        "oxuOnluq": F(m, qaytarır=o, standart=1),
        "oxuMəntiq": F(m, qaytarır=b, standart=1),
        "oxuHamısı": F(qaytarır=m),
        # Tip və çevirmə
        "tip": F(e, qaytarır=m),
        "tamƏt": F(e, e, i, qaytarır=i, standart=2),
        "onluqƏt": F(e, e, qaytarır=o, standart=1),
        "mətnƏt": F(e, qaytarır=m),
        "məntiqƏt": F(e, qaytarır=b),
        "simvolƏt": F(i, qaytarır=T.SİMVOL),
        "kodƏt": F(T.SİMVOL, qaytarır=i),
        # Kolleksiya
        "uzunluq": F(e, qaytarır=i),
        "boşdur": F(e, qaytarır=b),
        "cəm": F(e, e, qaytarır=t, standart=1),
        "minimum": Fsərbəst(t),
        "maksimum": Fsərbəst(t),
        "sırala": F(e, e, qaytarır=T.Siyahı(), standart=1),
        "tərs": F(e, qaytarır=T.Siyahı()),
        "nömrələ": F(e, qaytarır=T.Siyahı(T.Kortej())),
        "zip": Fsərbəst(T.Siyahı(T.Kortej())),
        "diapazon": F(i, i, i, qaytarır=T.DİAPAZON, standart=2),
        "siyahı": F(e, qaytarır=T.Siyahı(), standart=1),
        "dəst": Fsərbəst(T.Dəst()),
        "lüğət": F(e, qaytarır=T.Lüğət(), standart=1),
        "kortej": F(e, qaytarır=T.Kortej(), standart=1),
        # Digər
        "klonla": F(e, qaytarır=t),
        "çap": Fsərbəst(h),
        "ölç": F(e, qaytarır=t),
        "panika": F(m, qaytarır=h, standart=1),
        "dayan": F(i, qaytarır=h, standart=1),
        "eynidir": F(e, e, qaytarır=b),
        "heş": F(e, qaytarır=i),
        "LəğvNişanı": F(o, qaytarır=T.Sadə("ləğvNişanı"), standart=1),
        "Gələcək": F(e, qaytarır=T.Gələcək()),
    }

    # Xəta sinifləri — hamısı eyni imza
    from .deyerler import XETA_AGACI
    for ad in XETA_AGACI:
        if ad != "Atılan":
            d[ad] = Fsərbəst(T.SinifTipi(ad))

    return d


# ═══════════════════════════════════════════════════════════════════════
#  Daxili tiplərin metodları
# ═══════════════════════════════════════════════════════════════════════

def _mətn_metodları() -> dict[str, T.Tip]:
    m, i, b, e = T.MƏTN, T.TAM, T.MƏNTİQ, T.İSTƏNİLƏN
    return {
        "uzunluq": F(qaytarır=i), "baytUzunluğu": F(qaytarır=i),
        "böyüyə": F(qaytarır=m), "kiçiyə": F(qaytarır=m),
        "başBöyük": F(qaytarır=m), "hərSözBöyük": F(qaytarır=m),
        "kəs": F(m, qaytarır=m, standart=1),
        "başKəs": F(m, qaytarır=m, standart=1),
        "sonKəs": F(m, qaytarır=m, standart=1),
        "əvəz": F(m, m, qaytarır=m), "əvəzİlk": F(m, m, qaytarır=m),
        "böl": F(m, i, qaytarır=T.Siyahı(m), standart=2),
        "sətirlər": F(qaytarır=T.Siyahı(m)),
        "simvollar": F(qaytarır=T.Siyahı(T.SİMVOL)),
        "sözlər": F(qaytarır=T.Siyahı(m)),
        "baytlar": F(qaytarır=T.Siyahı(i)),
        "birləşdir": F(e, qaytarır=m),
        "ehtiva": F(m, qaytarır=b), "başlayır": F(m, qaytarır=b),
        "bitir": F(m, qaytarır=b),
        "tap": F(m, qaytarır=T.ixtiyari(i)),
        "sonTap": F(m, qaytarır=T.ixtiyari(i)),
        "hamısınıTap": F(m, qaytarır=T.Siyahı(i)),
        "say": F(m, qaytarır=i),
        "dilim": F(i, i, qaytarır=m, standart=1),
        "təkrar": F(i, qaytarır=m), "tərs": F(qaytarır=m),
        "doldur": F(i, m, qaytarır=m, standart=1),
        "solDoldur": F(i, m, qaytarır=m, standart=1),
        "sağDoldur": F(i, m, qaytarır=m, standart=1),
        "mərkəz": F(i, m, qaytarır=m, standart=1),
        "boşdur": F(qaytarır=b), "yalnızBoşluq": F(qaytarır=b),
        "rəqəmdir": F(qaytarır=b), "hərfdir": F(qaytarır=b),
        "müqayisə": F(m, qaytarır=i),
        "müqayisəHərfsiz": F(m, qaytarır=i),
        "normalizasiya": F(qaytarır=m), "latınla": F(qaytarır=m),
        "URLKodla": F(qaytarır=m), "URLAç": F(qaytarır=m),
        "base64Kodla": F(qaytarır=m), "base64Aç": F(qaytarır=m),
        "HTMLQaç": F(qaytarır=m),
        "formatla": Fsərbəst(m),
        "mətnƏt": F(qaytarır=m), "klonla": F(qaytarır=m),
        "tamƏt": F(qaytarır=i),
        "saitdir": F(qaytarır=b), "samitdir": F(qaytarır=b),
        "qalınSait": F(qaytarır=b), "incəSait": F(qaytarır=b),
    }


def _siyahı_metodları(element: T.Tip) -> dict[str, T.Tip]:
    i, b, h, e = T.TAM, T.MƏNTİQ, T.HEÇ, T.İSTƏNİLƏN
    s = T.Siyahı(element)
    ixt = T.ixtiyari(element)
    return {
        "əlavə": F(element, qaytarır=h),
        "əlavəHamısı": F(e, qaytarır=h),
        "daxilEt": F(i, element, qaytarır=h),
        "sil": F(i, qaytarır=element),
        "silDəyər": F(element, qaytarır=b),
        "silHamısı": F(element, qaytarır=h),
        "sonunuSil": F(qaytarır=element),
        "təmizlə": F(qaytarır=h),
        "sırala": F(e, qaytarır=h, standart=1),
        "sıralaAçar": F(e, qaytarır=h),
        "qarışdır": F(qaytarır=h), "tərsinəÇevir": F(qaytarır=h),
        "sıralanmış": F(e, qaytarır=s, standart=1),
        "tərs": F(qaytarır=s),
        "dilim": F(i, i, qaytarır=s, standart=1),
        "çevir": F(e, qaytarır=T.Siyahı()),
        "filtr": F(e, qaytarır=s),
        "yığ": F(e, e, qaytarır=T.NAMƏLUM),
        "yığSağdan": F(e, e, qaytarır=T.NAMƏLUM),
        "düzlə": F(qaytarır=T.Siyahı()),
        "düzləÇevir": F(e, qaytarır=T.Siyahı()),
        "təkrarsız": F(qaytarır=s),
        "birləşdir": F(e, qaytarır=s),
        "qrupla": F(e, qaytarır=T.Lüğət(T.NAMƏLUM, s)),
        "hissələrə": F(i, qaytarır=T.Siyahı(s)),
        "pəncərə": F(i, qaytarır=T.Siyahı(s)),
        "zip": F(e, qaytarır=T.Siyahı(T.Kortej())),
        "nömrələ": F(qaytarır=T.Siyahı(T.Kortej((i, element)))),
        "uzunluq": F(qaytarır=i), "boşdur": F(qaytarır=b),
        "ehtiva": F(element, qaytarır=b),
        "tap": F(e, qaytarır=ixt),
        "tapİndeks": F(e, qaytarır=T.ixtiyari(i)),
        "indeks": F(element, qaytarır=T.ixtiyari(i)),
        "sonİndeks": F(element, qaytarır=T.ixtiyari(i)),
        "say": F(element, qaytarır=i),
        "sayŞərt": F(e, qaytarır=i),
        "hamısı": F(e, qaytarır=b), "hərHansı": F(e, qaytarır=b),
        "heçBiri": F(e, qaytarır=b),
        "ilk": F(qaytarır=ixt), "son": F(qaytarır=ixt),
        "minimum": F(qaytarır=ixt), "maksimum": F(qaytarır=ixt),
        "cəm": F(qaytarır=element if T.ədəddir(element) else T.NAMƏLUM),
        "orta": F(qaytarır=T.ONLUQ),
        "hərBiri": F(e, qaytarır=h),
        "klonla": F(qaytarır=s),
        "al": F(i, e, qaytarır=ixt, standart=1),
        "mətnƏt": F(qaytarır=T.MƏTN),
        "siyahıyaÇevir": F(qaytarır=s),
    }


def _lüğət_metodları(açar: T.Tip, dəyər: T.Tip) -> dict[str, T.Tip]:
    i, b, h, e = T.TAM, T.MƏNTİQ, T.HEÇ, T.İSTƏNİLƏN
    l = T.Lüğət(açar, dəyər)
    return {
        "al": F(açar, dəyər, qaytarır=T.ixtiyari(dəyər), standart=1),
        "qoy": F(açar, dəyər, qaytarır=h),
        "sil": F(açar, qaytarır=T.ixtiyari(dəyər)),
        "təmizlə": F(qaytarır=h),
        "ehtiva": F(açar, qaytarır=b),
        "ehtivaDəyər": F(dəyər, qaytarır=b),
        "uzunluq": F(qaytarır=i), "boşdur": F(qaytarır=b),
        "açarlar": F(qaytarır=T.Siyahı(açar)),
        "dəyərlər": F(qaytarır=T.Siyahı(dəyər)),
        "cütlər": F(qaytarır=T.Siyahı(T.Kortej((açar, dəyər)))),
        "birləşdir": F(l, qaytarır=l),
        "çevir": F(e, qaytarır=T.Lüğət()),
        "filtr": F(e, qaytarır=l),
        "hərBiri": F(e, qaytarır=h),
        "alVəYaQoy": F(açar, e, qaytarır=dəyər),
        "yenilə": F(açar, e, qaytarır=dəyər),
        "tərsÇevir": F(qaytarır=T.Lüğət(dəyər, açar)),
        "klonla": F(qaytarır=l), "mətnƏt": F(qaytarır=T.MƏTN),
    }


def _dəst_metodları(element: T.Tip) -> dict[str, T.Tip]:
    i, b, h, e = T.TAM, T.MƏNTİQ, T.HEÇ, T.İSTƏNİLƏN
    d = T.Dəst(element)
    return {
        "əlavə": F(element, qaytarır=h), "sil": F(element, qaytarır=h),
        "ehtiva": F(element, qaytarır=b),
        "uzunluq": F(qaytarır=i), "boşdur": F(qaytarır=b),
        "təmizlə": F(qaytarır=h),
        "birləşmə": F(d, qaytarır=d), "kəsişmə": F(d, qaytarır=d),
        "fərq": F(d, qaytarır=d), "simmetrikFərq": F(d, qaytarır=d),
        "altDəstdir": F(d, qaytarır=b), "üstDəstdir": F(d, qaytarır=b),
        "kəsişmir": F(d, qaytarır=b),
        "siyahıyaÇevir": F(qaytarır=T.Siyahı(element)),
        "çevir": F(e, qaytarır=T.Dəst()), "filtr": F(e, qaytarır=d),
        "klonla": F(qaytarır=d), "mətnƏt": F(qaytarır=T.MƏTN),
    }


def _ədəd_metodları(özü: T.Tip) -> dict[str, T.Tip]:
    i, b, m, o = T.TAM, T.MƏNTİQ, T.MƏTN, T.ONLUQ
    ümumi = {
        "mətnƏt": F(qaytarır=m), "mütləq": F(qaytarır=özü),
        "işarə": F(qaytarır=i),
    }
    if özü == T.TAM:
        ümumi.update({
            "cütdür": F(qaytarır=b), "təkdir": F(qaytarır=b),
            "kvadrat": F(qaytarır=i), "onluğaÇevir": F(qaytarır=o),
            "ikilik": F(qaytarır=m), "onaltılıq": F(qaytarır=m),
            "sıraSayı": F(qaytarır=m), "yazıyla": F(qaytarır=m),
        })
    else:
        ümumi.update({
            "yuvarlaqlaşdır": F(i, qaytarır=o, standart=1),
            "aşağıYuvarlaq": F(qaytarır=i), "yuxarıYuvarlaq": F(qaytarır=i),
            "kəs": F(qaytarır=i), "tamƏt": F(qaytarır=i),
            "tamdır": F(qaytarır=b), "sonludur": F(qaytarır=b),
            "ədəddir": F(qaytarır=b),
        })
    return ümumi


def _element_metodları() -> dict[str, T.Tip]:
    m, i, b = T.MƏTN, T.TAM, T.MƏNTİQ
    return {
        "ad": m, "atributlar": T.Lüğət(m, T.İSTƏNİLƏN),
        "uşaqlar": T.Siyahı(T.İSTƏNİLƏN),
        "HTML": F(qaytarır=m), "mətn": F(qaytarır=m),
        "mətnƏt": F(qaytarır=m),
        "tap": F(m, qaytarır=T.ixtiyari(T.ELEMENT)),
        "atribut": F(m, T.İSTƏNİLƏN, qaytarır=T.İSTƏNİLƏN, standart=1),
        "uzunluq": F(qaytarır=i), "uşaqSayı": F(qaytarır=i),
        "boşdur": F(qaytarır=b),
    }


def _generator_metodları(element: T.Tip) -> dict[str, T.Tip]:
    i, b, h, e = T.TAM, T.MƏNTİQ, T.HEÇ, T.İSTƏNİLƏN
    g = T.Generator(element)
    return {
        "növbəti": F(qaytarır=element), "bitdi": F(qaytarır=b),
        "bağla": F(qaytarır=h),
        "siyahıyaÇevir": F(qaytarır=T.Siyahı(element)),
        "ilk": F(i, qaytarır=T.Siyahı(element)),
        "çevir": F(e, qaytarır=T.Generator()),
        "filtr": F(e, qaytarır=g), "atla": F(i, qaytarır=g),
        "tap": F(e, qaytarır=T.ixtiyari(element)),
        "hərBiri": F(e, qaytarır=h), "cəm": F(qaytarır=element),
        "uzunluq": F(qaytarır=i),
    }


def _gələcək_metodları(nəticə: T.Tip) -> dict[str, T.Tip]:
    return {
        "al": F(T.ONLUQ, qaytarır=nəticə, standart=1),
        "başlat": F(qaytarır=T.Gələcək(nəticə)),
        "bitdi": F(qaytarır=T.MƏNTİQ),
        "uğurludur": F(qaytarır=T.MƏNTİQ),
        "mətnƏt": F(qaytarır=T.MƏTN),
    }


def _ləğv_metodları() -> dict[str, T.Tip]:
    return {
        "ləğvEt": F(qaytarır=T.HEÇ),
        "ləğvolunub": F(qaytarır=T.MƏNTİQ),
        "gözlə": F(T.ONLUQ, qaytarır=T.MƏNTİQ, standart=1),
        "yoxla": F(qaytarır=T.HEÇ),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Modul imzaları
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
#  veb modulunun tipləri
# ═══════════════════════════════════════════════════════════════════════

SERVER = T.Sadə("server")
PƏNCƏRƏ = T.Sadə("pəncərə")
MENYU = T.Sadə("menyu")
MENYU_ELEMENTİ = T.Sadə("menyuElementi")
SÜRÜCÜ = T.Sadə("sürücü")
SORĞU = T.Sadə("sorğu")
CAVAB = T.Sadə("cavab")
QRUP = T.Sadə("qrup")
SESSİYA = T.Sadə("sessiya")
MÜŞTƏRİ = T.Sadə("müştəri")


def _marşrut_metodları(özü: T.Tip) -> dict[str, T.Tip]:
    """`al` / `göndər` / … — hamısı `özü` qaytarır (zəncirlənə bilir)."""
    m, e = T.MƏTN, T.İSTƏNİLƏN
    nəticə: dict[str, T.Tip] = {}
    for ad in ("al", "göndər", "yenilə", "yamaq", "sil", "hamısı"):
        nəticə[ad] = F(m, e, e, qaytarır=özü, standart=1)
    nəticə["qrup"] = F(m, e, qaytarır=özü)
    nəticə["ara"] = F(e, qaytarır=özü)
    return nəticə


def _server_metodları() -> dict[str, T.Tip]:
    m, i, e, h = T.MƏTN, T.TAM, T.İSTƏNİLƏN, T.HEÇ
    d = _marşrut_metodları(SERVER)
    d.update({
        "statik": F(m, m, m, qaytarır=SERVER, standart=1),
        "şablonQovluğu": F(m, qaytarır=SERVER),
        "komponent": F(m, e, m, m, qaytarır=SERVER, standart=2),
        "xətaİdarəedicisi": F(e, qaytarır=SERVER),
        "tapılmadı": F(e, qaytarır=SERVER),
        "dinlə": F(i, m, qaytarır=h, standart=2),
        "dayandır": F(qaytarır=h),
        "marşrutlar": F(qaytarır=T.Siyahı(T.Siyahı(m))),
        "mətnƏt": F(qaytarır=m),
    })
    return d


def _sorğu_metodları() -> dict[str, T.Tip]:
    m, b, e = T.MƏTN, T.MƏNTİQ, T.İSTƏNİLƏN
    return {
        "metod": F(qaytarır=m), "yol": F(qaytarır=m),
        "tamURL": F(qaytarır=m), "IP": F(qaytarır=m),
        "istifadəçiAgenti": F(qaytarır=m),
        "parametr": F(m, e, qaytarır=T.ixtiyari(m), standart=1),
        "parametrlər": F(qaytarır=T.Lüğət(m, m)),
        "sorğuParametr": F(m, e, qaytarır=T.ixtiyari(m), standart=1),
        "sorğuParametrHamısı": F(qaytarır=T.Lüğət(m, m)),
        "başlıq": F(m, e, qaytarır=T.ixtiyari(m), standart=1),
        "başlıqlar": F(qaytarır=T.Lüğət(m, m)),
        "kuki": F(m, e, qaytarır=T.ixtiyari(m), standart=1),
        "gövdə": F(qaytarır=m), "gövdəBayt": F(qaytarır=T.BAYT),
        "json": F(qaytarır=e), "form": F(qaytarır=T.Lüğət(m, m)),
        "sessiya": F(qaytarır=SESSİYA),
        "mətnƏt": F(qaytarır=m),
    }


def _cavab_metodları() -> dict[str, T.Tip]:
    m, i, b, e = T.MƏTN, T.TAM, T.MƏNTİQ, T.İSTƏNİLƏN
    return {
        "kod": F(i, qaytarır=CAVAB),
        # Bir arqumentlə oxuyur (`mətn?`), ikiylə təyin edib cavabı
        # qaytarır — nəticə arqument sayından asılıdır
        "başlıq": F(m, e, qaytarır=e, standart=1),
        "kuki": F(m, m, qaytarır=CAVAB),
        "kukiSil": F(m, m, qaytarır=CAVAB, standart=1),
        "vəziyyət": F(qaytarır=i), "mətnƏt": F(qaytarır=m),
        "json": F(qaytarır=e), "uzunluq": F(qaytarır=i),
        "uğurludur": F(qaytarır=b),
    }


def _müştəri_metodları() -> dict[str, T.Tip]:
    m, e = T.MƏTN, T.İSTƏNİLƏN
    return {
        "al": F(m, e, qaytarır=CAVAB, standart=1),
        "sil": F(m, e, qaytarır=CAVAB, standart=1),
        "göndər": F(m, e, e, qaytarır=CAVAB, standart=2),
        "yenilə": F(m, e, e, qaytarır=CAVAB, standart=2),
        "yamaq": F(m, e, e, qaytarır=CAVAB, standart=2),
    }


def _vidjet_modulu() -> T.ModulTipi:
    """
    Bütün vidjetlərin imzası `vidjet` modulunun Python funksiyalarından
    çıxarılır. Beləliklə parametr adları heç vaxt bir-birindən
    aralanmır: yeni vidjet əlavə edildikdə tip imzası da hazırdır.
    """
    import inspect

    from . import vidjet as _v

    m, e = T.MƏTN, T.İSTƏNİLƏN
    üzvlər: dict[str, T.Tip] = {}
    for ad in _v.VİDJETLƏR:
        imza = inspect.signature(getattr(_v, ad))
        # Birinci parametr `icraçı`-dır, Alqor tərəfində görünmür
        parametrlər = list(imza.parameters.values())[1:]
        üzvlər[ad] = T.FunksiyaTipi(tuple(
            T.Parametr(p.name, e,
                       standartı_var=(p.default is not
                                      inspect.Parameter.empty))
            for p in parametrlər), T.ELEMENT)

    üzvlər.update({
        # IDE kataloqu
        "kataloq": F(m, qaytarır=T.Siyahı(T.Lüğət(m, e)), standart=1),
        "kateqoriyalar": F(qaytarır=T.Siyahı(m)),
        "skelet": F(m, m, qaytarır=m, standart=1),
        "nümunə": F(m, m, qaytarır=m, standart=1),
        # Üslub
        "üslub": F(qaytarır=m),
        "üslublar": F(qaytarır=T.ELEMENT),
        "səhifə": F(m, e, m, m, qaytarır=T.ELEMENT, standart=4),
    })
    return T.ModulTipi("vidjet", üzvlər)


def _pəncərə_metodları() -> dict[str, T.Tip]:
    m, i, b, e, h = (T.MƏTN, T.TAM, T.MƏNTİQ, T.İSTƏNİLƏN, T.HEÇ)
    return {
        "başlıq": F(m, qaytarır=T.Birləşmə([PƏNCƏRƏ, m]), standart=1),
        "məzmun": F(e, qaytarır=PƏNCƏRƏ),
        "menyu": F(T.Siyahı(MENYU),
                   qaytarır=T.Birləşmə([PƏNCƏRƏ, T.MƏTN]),
                   standart=1),
        "üslub": F(m, qaytarır=PƏNCƏRƏ),
        "ölç": F(i, i, qaytarır=PƏNCƏRƏ),
        "mərkəzə": F(qaytarır=PƏNCƏRƏ),
        "ölçüsüSabit": F(qaytarır=PƏNCƏRƏ),
        "bağlananda": F(e, qaytarır=PƏNCƏRƏ),
        "göstər": F(qaytarır=PƏNCƏRƏ),
        "bağla": F(qaytarır=h),
        "açıqdır": F(qaytarır=b),
        "yenilə": F(qaytarır=PƏNCƏRƏ),
        "gözlə": F(qaytarır=h),
        "ünvan": F(qaytarır=m),
        "HTML": F(qaytarır=m),
        "səhifə": F(qaytarır=m),
    }


def _sürücü_metodları() -> dict[str, T.Tip]:
    m, b, e = T.MƏTN, T.MƏNTİQ, T.İSTƏNİLƏN
    return {
        "klik": F(m, e, qaytarır=SÜRÜCÜ, standart=2),
        "yaz": F(m, e, qaytarır=SÜRÜCÜ),
        "hadisə": F(m, m, e, qaytarır=SÜRÜCÜ, standart=2),
        "yenilə": F(qaytarır=SÜRÜCÜ),
        "bağla": F(qaytarır=SÜRÜCÜ),
        "HTML": F(qaytarır=m),
        "səhifə": F(qaytarır=m),
        "menyu": F(qaytarır=m),
        "başlıq": F(qaytarır=m),
        "mətn": F(qaytarır=m),
        "ehtiva": F(m, qaytarır=b),
        "açıqdır": F(qaytarır=b),
        "dialoqlar": F(qaytarır=T.Siyahı(T.Siyahı(m))),
    }


def _pəncərə_modulu() -> T.ModulTipi:
    m, i, b, e, h = (T.MƏTN, T.TAM, T.MƏNTİQ, T.İSTƏNİLƏN, T.HEÇ)
    ixtiyari_m = T.ixtiyari(m)
    dialoq = T.ModulTipi("pəncərə.dialoq", {
        "təsdiqlə": F(m, m, qaytarır=b, standart=1),
        "xəbərdarlıq": F(m, m, qaytarır=h, standart=1),
        "məlumat": F(m, m, qaytarır=h, standart=1),
        "xəta": F(m, m, qaytarır=h, standart=1),
        "soruş": F(m, m, m, qaytarır=ixtiyari_m, standart=2),
        "faylAç": F(e, m, qaytarır=ixtiyari_m, standart=2),
        "faylAçHamısı": F(e, m, qaytarır=T.Siyahı(m), standart=2),
        "faylSaxla": F(m, e, m, qaytarır=ixtiyari_m, standart=3),
        "qovluqSeç": F(m, qaytarır=ixtiyari_m, standart=1),
        "rəngSeç": F(m, qaytarır=ixtiyari_m, standart=1),
    })
    sınaq = T.ModulTipi("pəncərə.sınaq", {
        "aç": F(PƏNCƏRƏ, qaytarır=SÜRÜCÜ),
        "cavablar": F(T.Siyahı(T.İSTƏNİLƏN), qaytarır=h),
        "jurnal": F(qaytarır=T.Siyahı(T.Siyahı(m))),
        "təmizlə": F(qaytarır=h),
    })
    return T.ModulTipi("pəncərə", {
        "Pəncərə": F(m, i, i, qaytarır=PƏNCƏRƏ, standart=3),
        "menyu": F(m, T.Siyahı(MENYU_ELEMENTİ), qaytarır=MENYU,
                   standart=1),
        "element": F(m, m, e, b, b, qaytarır=MENYU_ELEMENTİ, standart=4),
        "ayırıcı": F(qaytarır=MENYU_ELEMENTİ),
        "bildiriş": F(m, m, qaytarır=h, standart=1),
        "işlət": F(qaytarır=h),
        "dayandır": F(qaytarır=h),
        "pəncərələr": F(qaytarır=T.Siyahı(PƏNCƏRƏ)),
        "aparıcı": F(qaytarır=m),
        "başsızdır": F(qaytarır=b),
        "dialoq": dialoq,
        "sınaq": sınaq,
    })


def _veb_modulu() -> T.ModulTipi:
    m, i, e, h = T.MƏTN, T.TAM, T.İSTƏNİLƏN, T.HEÇ
    sınaq = T.ModulTipi("veb.sınaq", {
        "server": F(SERVER, qaytarır=MÜŞTƏRİ),
    })
    return T.ModulTipi("veb", {
        "Server": F(qaytarır=SERVER),
        "mətn": F(e, qaytarır=CAVAB),
        "html": F(e, qaytarır=CAVAB),
        "json": F(e, qaytarır=CAVAB),
        "boş": F(i, qaytarır=CAVAB, standart=1),
        "yönləndir": F(m, qaytarır=CAVAB),
        "yönləndirDaimi": F(m, qaytarır=CAVAB),
        "xəta": F(i, e, qaytarır=CAVAB, standart=1),
        "fayl": F(m, qaytarır=CAVAB),
        "yüklə": F(m, m, qaytarır=CAVAB, standart=1),
        "şablon": F(m, e, qaytarır=CAVAB, standart=1),
        "şablonQovluğu": F(m, qaytarır=h),
        "jurnal": F(qaytarır=e),
        "CORS": F(e, e, qaytarır=e, standart=2),
        "sıxma": F(i, qaytarır=e, standart=1),
        "təhlükəsizlikBaşlıqları": F(qaytarır=e),
        "sessiya": F(e, qaytarır=e, standart=1),
        "sürətLimiti": F(i, e, qaytarır=e, standart=2),
        "boşPort": F(i, qaytarır=i, standart=1),
        "sınaq": sınaq,
    })


def fayl_modulu(yol: Any, rejim: str = "normal") -> T.ModulTipi:
    """Həll olunmuş fayl yolu → modul tipi (keşlənir, dövrə qorunur)."""
    from .lekser import Lekser
    from .menbe import Mənbə
    from .parser import Parser
    global _QEYD_SİYAHISI

    açar_yol = str(yol)
    mətn = FAYL_MƏTNİ(yol) if FAYL_MƏTNİ is not None else None
    if mətn is not None:
        vəziyyət: Any = ("mətn", hash(mətn), rejim)
    else:
        try:
            st = yol.stat()
        except OSError:
            return T.ModulTipi(yol.stem)
        vəziyyət = ("fayl", st.st_mtime_ns, st.st_size, rejim)
    köhnə = _FAYL_KEŞİ.get(açar_yol)
    if köhnə is not None and köhnə[0] == vəziyyət:
        return köhnə[1]
    if açar_yol in _YÜKLƏNİR:               # dövri idxal: a → b → a
        return T.ModulTipi(yol.stem, yol=yol)

    x = XətaToplayıcı()
    if mətn is None:
        m = Mənbə.fayldan(yol, x)
    else:
        m = Mənbə.mətndən(mətn, yol.name)
        m.yol = yol
    modul = T.ModulTipi(yol.stem, yol=yol)
    if m is None:
        return modul
    _YÜKLƏNİR.add(açar_yol)
    qeyd = _QEYD_SİYAHISI
    _QEYD_SİYAHISI = None                    # idxal edənin qeydinə qarışmasın
    try:
        ağac = Parser(Lekser(m, x).leksə(), m, x).ayır()
        if x.uğurludur():
            y = TipYoxlayıcı(x, rejim)
            y.yoxla(ağac)
            for ad, b in y.qlobal.adlar.items():
                if b.elan_növü == "daxili":
                    continue
                modul.üzvlər[ad] = b.tip
                modul.elanlar[ad] = b
    except Exception:                         # noqa: BLE001
        pass
    finally:
        _QEYD_SİYAHISI = qeyd
        _YÜKLƏNİR.discard(açar_yol)
    _FAYL_KEŞİ[açar_yol] = (vəziyyət, modul)
    return modul


def _modullar() -> dict[str, T.ModulTipi]:
    i, o, m, b, h, e = (T.TAM, T.ONLUQ, T.MƏTN, T.MƏNTİQ, T.HEÇ,
                        T.İSTƏNİLƏN)

    riyaziyyat = T.ModulTipi("riyaziyyat", {
        "Pİ": o, "PI": o, "E": o, "TAU": o, "QIZILNİSBƏT": o,
        "SONSUZ": o, "ƏDƏDDEYİL": o,
        "mütləq": F(e, qaytarır=T.NAMƏLUM),
        "işarə": F(e, qaytarır=i),
        "kök": F(e, qaytarır=o), "kubKök": F(e, qaytarır=o),
        "qüvvət": F(e, e, qaytarır=T.NAMƏLUM),
        "eksp": F(e, qaytarır=o),
        "loq": F(e, e, qaytarır=o, standart=1),
        "loq10": F(e, qaytarır=o), "loq2": F(e, qaytarır=o),
        "loqƏsas": F(e, e, qaytarır=o),
        "yuvarlaqlaşdır": F(e, i, qaytarır=T.NAMƏLUM, standart=1),
        "aşağıYuvarlaq": F(e, qaytarır=i),
        "yuxarıYuvarlaq": F(e, qaytarır=i),
        "kəs": F(e, qaytarır=i),
        "min": Fsərbəst(T.NAMƏLUM), "maks": Fsərbəst(T.NAMƏLUM),
        "məhdudla": F(e, e, e, qaytarır=T.NAMƏLUM),
        "sin": F(e, qaytarır=o), "kos": F(e, qaytarır=o),
        "tan": F(e, qaytarır=o), "arksin": F(e, qaytarır=o),
        "arkkos": F(e, qaytarır=o), "arktan": F(e, qaytarır=o),
        "arktan2": F(e, e, qaytarır=o),
        "hipsin": F(e, qaytarır=o), "hipkos": F(e, qaytarır=o),
        "hiptan": F(e, qaytarır=o),
        "dərəcəyə": F(e, qaytarır=o), "radiana": F(e, qaytarır=o),
        "ƏBOB": Fsərbəst(i), "ƏKOB": Fsərbəst(i),
        "faktorial": F(i, qaytarır=i),
        "sadədir": F(i, qaytarır=b),
        "sadəBölənlər": F(i, qaytarır=T.Siyahı(i)),
        "modul": F(e, e, qaytarır=T.NAMƏLUM),
        "modQüvvət": F(i, i, i, qaytarır=i),
        "ədəddirmi": F(e, qaytarır=b), "sonludur": F(e, qaytarır=b),
        "tamdır": F(e, qaytarır=b),
        "orta": F(e, qaytarır=o), "median": F(e, qaytarır=o),
        "moda": F(e, qaytarır=T.NAMƏLUM),
        "dispersiya": F(e, qaytarır=o),
        "standartKənarlaşma": F(e, qaytarır=o),
    })

    mətn_m = T.ModulTipi("mətn", {
        "formatla": Fsərbəst(m),
        "yerliƏdəd": F(e, i, qaytarır=m, standart=1),
        "yerliPul": F(e, qaytarır=m), "yerliFaiz": F(e, qaytarır=m),
        "yazıylaƏdəd": F(i, qaytarır=m), "sıraSayı": F(i, qaytarır=m),
        "saitdir": F(T.SİMVOL, qaytarır=b),
        "samitdir": F(T.SİMVOL, qaytarır=b),
        "qalınSait": F(T.SİMVOL, qaytarır=b),
        "incəSait": F(T.SİMVOL, qaytarır=b),
        "şəkilçi": F(m, m, qaytarır=m),
        "böyüyə": F(m, qaytarır=m), "kiçiyə": F(m, qaytarır=m),
        "müqayisə": F(m, m, qaytarır=i), "əlifba": m,
    })

    təsadüfi = T.ModulTipi("təsadüfi", {
        "tam": F(i, i, qaytarır=i),
        "onluq": F(o, o, qaytarır=o, standart=2),
        "məntiq": F(qaytarır=b),
        "seç": F(e, qaytarır=T.NAMƏLUM),
        "seçN": F(e, i, qaytarır=T.Siyahı()),
        "qarışdır": F(e, qaytarır=h),
        "mətn": F(i, qaytarır=m), "UUID": F(qaytarır=m),
        "toxum": F(i, qaytarır=h),
    })

    vaxt = T.ModulTipi("vaxt", {
        "möhür": F(qaytarır=i), "möhürMs": F(qaytarır=i),
        "indi": F(qaytarır=m), "bugün": F(qaytarır=m),
        "formatla": F(m, i, qaytarır=m, standart=1),
        "azərbaycanca": F(qaytarır=m),
        "ayAdı": F(i, qaytarır=m), "ayAdıBaş": F(i, qaytarır=m),
        "günAdı": F(i, qaytarır=m),
        "ayAdları": F(qaytarır=T.Siyahı(m)),
        "günAdları": F(qaytarır=T.Siyahı(m)),
        "gözlə": F(i, qaytarır=h), "gözləSaniyə": F(o, qaytarır=h),
        "ölç": F(qaytarır=o),
        "limitlə": F(i, e, qaytarır=T.NAMƏLUM),
    })

    fayl = T.ModulTipi("fayl", {
        "oxu": F(m, qaytarır=m), "yaz": F(m, e, qaytarır=h),
        "əlavəEt": F(m, e, qaytarır=h),
        "oxuSətirlər": F(m, qaytarır=T.Siyahı(m)),
        "oxuBayt": F(m, qaytarır=T.BAYT),
        "yazBayt": F(m, e, qaytarır=h),
        "vardır": F(m, qaytarır=b), "sil": F(m, qaytarır=h),
        "kopyala": F(m, m, qaytarır=h), "köçür": F(m, m, qaytarır=h),
        "adDəyiş": F(m, m, qaytarır=h),
        "ölçü": F(m, qaytarır=i), "MIMETipi": F(m, qaytarır=m),
    })

    qovluq = T.ModulTipi("qovluq", {
        "yarat": F(m, qaytarır=h), "yaratDərin": F(m, qaytarır=h),
        "sil": F(m, qaytarır=h), "silDərin": F(m, qaytarır=h),
        "vardır": F(m, qaytarır=b),
        "siyahı": F(m, qaytarır=T.Siyahı(m), standart=1),
        "axtar": F(m, m, qaytarır=T.Siyahı(m)),
        "cari": F(qaytarır=m), "dəyiş": F(m, qaytarır=h),
        "ev": F(qaytarır=m), "müvəqqəti": F(qaytarır=m),
    })

    yol = T.ModulTipi("yol", {
        "birləşdir": Fsərbəst(m), "mütləq": F(m, qaytarır=m),
        "qovluq": F(m, qaytarır=m), "fayl": F(m, qaytarır=m),
        "ad": F(m, qaytarır=m), "uzantı": F(m, qaytarır=m),
        "normalizə": F(m, qaytarır=m), "nisbi": F(m, m, qaytarır=m),
        "ayırıcı": m,
    })

    json_m = T.ModulTipi("json", {
        "oxu": F(m, qaytarır=e), "yaz": F(e, qaytarır=m),
        "yazGözəl": F(e, qaytarır=m),
        "faylOxu": F(m, qaytarır=e), "faylYaz": F(m, e, qaytarır=h),
    })

    naxış = T.ModulTipi("naxış", {
        "qur": F(m, m, qaytarır=T.NAMƏLUM, standart=1),
        "uyğundur": F(m, m, qaytarır=b),
        "tap": F(m, m, qaytarır=T.ixtiyari(m)),
        "hamısınıTap": F(m, m, qaytarır=T.Siyahı(m)),
        "əvəz": F(m, m, m, qaytarır=m),
        "böl": F(m, m, qaytarır=T.Siyahı(m)),
    })

    sistem = T.ModulTipi("sistem", {
        "arqumentlər": F(qaytarır=T.Siyahı(m)),
        "mühit": F(m, m, qaytarır=T.ixtiyari(m), standart=1),
        "mühitQoy": F(m, m, qaytarır=h),
        "platforma": F(qaytarır=m), "memarlıq": F(qaytarır=m),
        "nüvəSayı": F(qaytarır=i), "istifadəçi": F(qaytarır=m),
        "hostAdı": F(qaytarır=m), "dayan": F(i, qaytarır=h, standart=1),
    })

    konsol = T.ModulTipi("konsol", {
        "qırmızı": F(e, qaytarır=m), "yaşıl": F(e, qaytarır=m),
        "sarı": F(e, qaytarır=m), "mavi": F(e, qaytarır=m),
        "boz": F(e, qaytarır=m),
        "qalın": F(e, qaytarır=m), "altXətt": F(e, qaytarır=m),
        "rəng": F(e, m, m, b, qaytarır=m, standart=3),
        "təmizlə": F(qaytarır=h),
        "kursor": F(i, i, qaytarır=h, standart=1),
        "ölçü": F(qaytarır=T.Kortej((i, i))),
        "terminaldır": F(qaytarır=b),
        "cədvəl": F(e, e, qaytarır=h),
        "soruş": F(m, e, qaytarır=m, standart=2),
        "parolSoruş": F(m, qaytarır=m, standart=1),
        "təsdiqlə": F(m, e, qaytarır=b, standart=1),
        "seç": F(m, T.Siyahı(e), qaytarır=e),
        "çoxSeç": F(m, T.Siyahı(e), qaytarır=T.Siyahı(e)),
        "irəliləyiş": F(i, m, qaytarır=e, standart=1),
        "fırlanan": F(m, qaytarır=e, standart=1),
        "arqumentlər": F(qaytarır=e),
    })

    jurnal = T.ModulTipi("jurnal", {
        a: Fsərbəst(h) for a in
        ("debaq", "info", "xəbərdarlıq", "xəta", "kritik")
    })

    test = T.ModulTipi("test", {
        "bərabər": F(e, e, m, qaytarır=h, standart=1),
        "bərabərDeyil": F(e, e, m, qaytarır=h, standart=1),
        "doğru": F(b, m, qaytarır=h, standart=1),
        "yanlış": F(b, m, qaytarır=h, standart=1),
        "təxminən": F(e, e, o, m, qaytarır=h, standart=2),
        "boş": F(e, m, qaytarır=h, standart=1),
        "boşDeyil": F(e, m, qaytarır=h, standart=1),
        "ehtiva": F(e, e, m, qaytarır=h, standart=1),
        "atır": F(e, e, m, qaytarır=e, standart=2),
        "atmır": F(e, m, qaytarır=e, standart=1),
        "uyğun": F(m, m, m, qaytarır=h, standart=1),
        "uğursuz": F(m, qaytarır=h, standart=1),
    })

    paralel = T.ModulTipi("paralel", {
        "hamısı": F(e, qaytarır=T.Siyahı()),
        "hamısıNəticə": F(e, qaytarır=T.Siyahı(T.Kortej())),
        "ilkBitən": F(e, qaytarır=T.NAMƏLUM),
        "ilkUğurlu": F(e, qaytarır=T.NAMƏLUM),
        "məhdud": F(i, e, qaytarır=T.Siyahı()),
        "çevir": F(e, e, qaytarır=T.Siyahı()),
    }, çağırıla_bilir=True)

    sap = T.ModulTipi("sap", {
        "başlat": Fsərbəst(T.Gələcək()),
        "xəritələ": F(e, e, i, qaytarır=T.Siyahı(), standart=1),
        "nüvəSayı": F(qaytarır=i), "gözlə": F(i, qaytarır=h),
    })

    return {
        "veb": _veb_modulu(),
        "pəncərə": _pəncərə_modulu(),
        "vidjet": _vidjet_modulu(),
        "riyaziyyat": riyaziyyat, "mətn": mətn_m, "təsadüfi": təsadüfi,
        "vaxt": vaxt, "fayl": fayl, "qovluq": qovluq, "yol": yol,
        "json": json_m, "naxış": naxış, "sistem": sistem,
        "konsol": konsol, "jurnal": jurnal, "test": test,
        "paralel": paralel, "sap": sap,
        **_əlavə_modullar(),
    }


def _əlavə_modullar() -> dict[str, T.ModulTipi]:
    """`alqor/modullar/` paketindəki modulların tipləri."""
    from . import modullar
    return {ad: modullar.modul_tipi(ad) for ad in modullar.adlar()}


# ═══════════════════════════════════════════════════════════════════════
#  Tip yoxlayıcı
# ═══════════════════════════════════════════════════════════════════════

class TipYoxlayıcı:
    def __init__(self, toplayıcı: XətaToplayıcı, rejim: str = "normal"):
        self.x = toplayıcı
        self.rejim = rejim if rejim in REJİMLƏR else "normal"
        self.qlobal = Əhatə(növ="qlobal")
        self.modullar = _modullar()
        self.siniflər: dict[str, T.SinifTipi] = {}
        self.sadalamalar: dict[str, T.SadalamaTipi] = {}
        self._cari_sinif: T.SinifTipi | None = None
        # `alqorls` üçün qeyd rejimi (standart olaraq söndürülüb):
        #   istinadlar — ad istifadəsi → elan (təyinata get, istinadlar)
        #   ifadə_tipləri — ad/üzv ifadəsi → tip (hover, tamamlama)
        #   bağlamalar — bütün elanlar (sənəd sxemi, tamamlama)
        self.qeyd = False
        self.istinadlar: list[tuple[A.Ad, Bağlama]] = []
        self.ifadə_tipləri: list[tuple[Any, T.Tip, T.Tip | None]] = []
        self.bağlamalar: list[Bağlama] = []
        # `m.f` — fayl modulunun üzvü → həmin fayldakı elan
        self.üzv_istinadları: list[tuple[A.Üzv, Bağlama]] = []
        self._son_obyekt_tipi: T.Tip | None = None
        self._generik_adlar: frozenset[str] = frozenset()
        self._qaldırılmış_idxallar: set[int] = set()
        for ad, tip in _daxili_adlar().items():
            self.qlobal.elan(Bağlama(ad, tip, True, None, True, "daxili"))

    @property
    def sərtdir(self) -> bool:
        return self.rejim == "sərt"

    @property
    def sərbəstdir(self) -> bool:
        return self.rejim == "sərbəst"

    # ═══════════════════════════════════════════════════════════════════
    #  Giriş nöqtəsi
    # ═══════════════════════════════════════════════════════════════════

    def yoxla(self, ağac: A.Proqram) -> None:
        ə = self.qlobal
        self._elanları_qaldır(ağac.gövdə, ə)
        for c in ağac.gövdə:
            self._cümlə(c, ə)
        self._istifadəsizləri_bildir(ə)

    # ── Elanların qaldırılması ────────────────────────────────────────

    def _elanları_qaldır(self, gövdə: list[A.Cümlə], ə: Əhatə) -> None:
        # 0. `gətir` — modul tipləri funksiya imzalarında işlənə bilsin
        #    (`funksiya f() -> pəncərə.Pəncərə`)
        for c in gövdə:
            if isinstance(c, A.İdxal):
                self._c_idxal(c, ə)
                self._qaldırılmış_idxallar.add(id(c))

        # 1. Sinif / sadalama adları (bir-birinə istinad edə bilsin)
        for c in gövdə:
            if isinstance(c, A.SinifElanı):
                s = T.SinifTipi(c.ad, quruluş=c.quruluş,
                                mücərrəd=c.mücərrəd)
                self.siniflər[c.ad] = s
                ə.elan(Bağlama(c.ad, s, True, c.yer, True, "sinif"))
            elif isinstance(c, A.SadalamaElanı):
                e = T.SadalamaTipi(
                    c.ad, tuple(v.ad for v in c.variantlar))
                self.sadalamalar[c.ad] = e
                ə.elan(Bağlama(c.ad, e, True, c.yer, True, "sadalama"))
            elif isinstance(c, A.InterfeysElanı):
                s = T.SinifTipi(c.ad, quruluş="interfeys", mücərrəd=True)
                self.siniflər[c.ad] = s
                ə.elan(Bağlama(c.ad, s, True, c.yer, True, "sinif"))
            elif isinstance(c, A.TipAliası):
                ə.elan(Bağlama(c.ad, self._tip(c.tip, ə), True, c.yer,
                               True, "tip"))

        # 2. Sinif üzvlərinin imzaları
        for c in gövdə:
            if isinstance(c, A.SinifElanı):
                self._sinif_imzası(c, ə)
            elif isinstance(c, A.SadalamaElanı):
                self._sadalama_imzası(c, ə)
            elif isinstance(c, A.InterfeysElanı):
                self._interfeys_imzası(c, ə)

        # 3. Funksiya imzaları
        for c in gövdə:
            if isinstance(c, A.FunksiyaElanı):
                ə.elan(Bağlama(c.ad, self._funksiya_imzası(c, ə), True,
                               c.yer, False, "funksiya"))

    def _generiklərlə(self, c: Any):
        """`funksiya f[T, Element](…)` — elan olunan generik adlar."""
        import contextlib

        @contextlib.contextmanager
        def kontekst():
            köhnə = self._generik_adlar
            self._generik_adlar = köhnə | {
                g[0] if isinstance(g, (tuple, list)) else str(g)
                for g in (getattr(c, "generiklər", None) or [])}
            try:
                yield
            finally:
                self._generik_adlar = köhnə
        return kontekst()

    def _funksiya_imzası(self, c: Any, ə: Əhatə) -> T.FunksiyaTipi:
        with self._generiklərlə(c):
            return self._funksiya_imzası_(c, ə)

    def _funksiya_imzası_(self, c: Any, ə: Əhatə) -> T.FunksiyaTipi:
        parametrlər: list[T.Parametr] = []
        for p in c.parametrlər:
            tip = self._tip(p.tip, ə) if p.tip else T.NAMƏLUM
            if self.sərtdir and p.tip is None and not p.variadic:
                self.x.xəbərdarlıq(
                    "ALQ-T080", "Sərt rejimdə parametr tipi məcburidir",
                    p.yer, f"`{p.ad}` parametrinin tipi yazılmayıb")
            parametrlər.append(T.Parametr(
                p.ad, tip, p.standart is not None,
                p.variadic or p.adlı_variadic, p.yalnız_adlı))

        qaytarma_qovşağı = getattr(c, "qaytarma_tipi", None)
        qaytarma = (self._tip(qaytarma_qovşağı, ə)
                    if qaytarma_qovşağı else T.NAMƏLUM)
        if getattr(c, "generator", False):
            qaytarma = T.Generator(qaytarma)
        elif getattr(c, "asinxron", False):
            qaytarma = T.Gələcək(qaytarma)
        return T.FunksiyaTipi(tuple(parametrlər), qaytarma,
                              getattr(c, "asinxron", False),
                              getattr(c, "generator", False))

    def _sinif_imzası(self, c: A.SinifElanı, ə: Əhatə) -> None:
        s = self.siniflər[c.ad]
        if c.baza is not None:
            baza = self._tip(c.baza, ə)
            if isinstance(baza, T.SinifTipi):
                s.baza = baza
        s.interfeyslər = tuple(
            t.tam_ad for t in c.interfeyslər if isinstance(t, A.TipAdı))

        for ü in c.üzvlər:
            if isinstance(ü, A.XassəElanı):
                tip = self._tip(ü.tip, ə) if ü.tip else T.NAMƏLUM
                if ü.statik:
                    s.statiklər[ü.ad] = tip
                else:
                    s.sahələr[ü.ad] = tip
            elif isinstance(ü, A.MetodElanı):
                imza = self._funksiya_imzası(ü, ə)
                if ü.statik:
                    s.statiklər[ü.ad] = imza
                else:
                    s.metodlar[ü.ad] = imza
            elif isinstance(ü, A.QurucuElanı):
                s.quruculər[ü.ad or ""] = self._funksiya_imzası(ü, ə)
                # Qısa qurucu: `açıq xassə ad: mətn`
                for p in ü.parametrlər:
                    if p.xassə_görünüşü:
                        s.sahələr[p.ad] = (self._tip(p.tip, ə) if p.tip
                                           else T.NAMƏLUM)

    def _interfeys_imzası(self, c: A.InterfeysElanı, ə: Əhatə) -> None:
        s = self.siniflər[c.ad]
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı):
                s.metodlar[ü.ad] = self._funksiya_imzası(ü, ə)
            elif isinstance(ü, A.XassəElanı):
                s.sahələr[ü.ad] = (self._tip(ü.tip, ə) if ü.tip
                                   else T.NAMƏLUM)

    def _sadalama_imzası(self, c: A.SadalamaElanı, ə: Əhatə) -> None:
        e = self.sadalamalar[c.ad]
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı):
                e.metodlar[ü.ad] = self._funksiya_imzası(ü, ə)

    # ═══════════════════════════════════════════════════════════════════
    #  Tip ifadələrinin həlli
    # ═══════════════════════════════════════════════════════════════════

    def _tip(self, q: Any, ə: Əhatə) -> T.Tip:
        if q is None:
            return T.NAMƏLUM

        if isinstance(q, A.TipBirləşmə):
            return T.birləşmə(*[self._tip(v, ə) for v in q.variantlar])

        if isinstance(q, A.TipKortej):
            t = T.Kortej(tuple(self._tip(e, ə) for e in q.elementlər))
            return T.ixtiyari(t) if q.ixtiyari else t

        if isinstance(q, A.TipFunksiya):
            p = tuple(T.Parametr(f"a{i}", self._tip(x, ə))
                      for i, x in enumerate(q.parametrlər))
            t = T.FunksiyaTipi(p, self._tip(q.qaytarma, ə))
            return T.ixtiyari(t) if q.ixtiyari else t

        if not isinstance(q, A.TipAdı):
            return T.NAMƏLUM

        ad = q.tam_ad
        arq = [self._tip(a, ə) for a in q.arqumentlər]
        əsas = self._tip_adından(ad, arq, q, ə)
        return T.ixtiyari(əsas) if q.ixtiyari else əsas

    def _tip_adından(self, ad: str, arq: list[T.Tip], q: A.TipAdı,
                     ə: Əhatə) -> T.Tip:
        sadələr = {
            "tam": T.TAM, "onluq": T.ONLUQ, "mətn": T.MƏTN,
            "məntiq": T.MƏNTİQ, "simvol": T.SİMVOL, "bayt": T.BAYT,
            "heç": T.HEÇ, "istənilən": T.İSTƏNİLƏN,
            "element": T.ELEMENT, "diapazon": T.DİAPAZON,
        }
        if ad in sadələr:
            return sadələr[ad]
        if ad == "siyahı":
            return T.Siyahı(arq[0] if arq else T.NAMƏLUM)
        if ad == "dəst":
            return T.Dəst(arq[0] if arq else T.NAMƏLUM)
        if ad == "lüğət":
            return T.Lüğət(arq[0] if arq else T.NAMƏLUM,
                           arq[1] if len(arq) > 1 else T.NAMƏLUM)
        if ad == "kortej":
            return T.Kortej(tuple(arq))
        if ad == "generator":
            return T.Generator(arq[0] if arq else T.NAMƏLUM)
        if ad == "gələcək":
            return T.Gələcək(arq[0] if arq else T.NAMƏLUM)
        if ad == "funksiyaTipi":
            return T.FunksiyaTipi()

        if ad in self.siniflər:
            return self.siniflər[ad]
        if ad in self.sadalamalar:
            return self.sadalamalar[ad]

        b = ə.tap(q.yol[0])
        if b is not None:
            b.istifadə_olunub = True
            if isinstance(b.tip, (T.SinifTipi, T.SadalamaTipi)):
                return b.tip
            if b.elan_növü == "tip":
                return b.tip
            if isinstance(b.tip, T.ModulTipi) and len(q.yol) > 1:
                üzv: Any = b.tip
                for h in q.yol[1:]:
                    üzv = (üzv.üzvlər.get(h)
                           if isinstance(üzv, T.ModulTipi) else None)
                if isinstance(üzv, (T.SinifTipi, T.SadalamaTipi)):
                    return üzv
                # `pəncərə.Pəncərə`, `http.Sorğu` — qurucu funksiyadır;
                # annotasiyada onun yaratdığı obyektin tipi nəzərdə tutulur
                if isinstance(üzv, T.FunksiyaTipi) and \
                        q.yol[-1][:1].isupper() and \
                        not T.naməlumdur(üzv.qaytarma):
                    return üzv.qaytarma
                if üzv is None and not self.sərbəstdir:
                    self.x.xəta("ALQ-T002", "Naməlum tip", q.yer,
                                f"`{b.tip.ad}` modulunda `{q.yol[-1]}` "
                                "tipi yoxdur")
            return T.NAMƏLUM

        # Generik parametr: elan olunub (`f[Element]`) və ya qısa ad (`T`)
        if ad in self._generik_adlar or (len(ad) <= 2
                                         and ad[:1].isupper()):
            return T.Generik(ad)

        if not self.sərbəstdir:
            self.x.xəta("ALQ-T002", "Naməlum tip", q.yer,
                        f"`{ad}` adlı tip tapılmadı",
                        "əsas tiplər: tam, onluq, mətn, məntiq, simvol",
                        "kolleksiyalar: siyahı[T], lüğət[A,D], dəst[T]")
        return T.NAMƏLUM

    # ═══════════════════════════════════════════════════════════════════
    #  Cümlələr
    # ═══════════════════════════════════════════════════════════════════

    def _blok(self, gövdə: list[A.Cümlə], ə: Əhatə) -> bool:
        """Bloku yoxlayır. True → blok mütləq çıxır (qaytar/at/dayan)."""
        çıxır = False
        ə.son_ifadə_tipi = None
        ə.son_ifadə_yeri = None
        son_indeks = len(gövdə) - 1

        for i, c in enumerate(gövdə):
            if çıxır and not isinstance(c, (A.FunksiyaElanı,
                                            A.SinifElanı)):
                self.x.xəbərdarlıq(
                    "ALQ-T025", "Çatılmayan kod", getattr(c, "yer", None),
                    "bu sətirə heç vaxt çatılmır")
                break

            # Blokun SON ifadəsi avtomatik qaytarılır — tipini saxlayırıq
            if i == son_indeks and isinstance(c, A.İfadəCümləsi):
                ə.son_ifadə_tipi = self._ifadə(c.ifadə, ə)
                ə.son_ifadə_yeri = getattr(c.ifadə, "yer", c.yer)
                continue

            if self._cümlə(c, ə):
                çıxır = True
        return çıxır

    def _cümlə(self, c: A.Cümlə, ə: Əhatə) -> bool:
        işləyici = _CÜMLƏLƏR.get(type(c))
        if işləyici is None:
            return False
        return bool(işləyici(self, c, ə))

    # ── Elanlar ───────────────────────────────────────────────────────

    def _c_dəyişən(self, c: A.DəyişənElanı, ə: Əhatə) -> bool:
        sabit = c.növ in ("sabit", "dəyişməz")

        if not c.dəyərlər:
            for b in c.bağlamalar:
                tip = self._tip(b.tip, ə) if b.tip else T.NAMƏLUM
                self._bağla(b, tip, ə, sabit)
            return False

        if len(c.bağlamalar) == len(c.dəyərlər):
            for b, d in zip(c.bağlamalar, c.dəyərlər):
                elan_tipi = self._tip(b.tip, ə) if b.tip else None
                dəyər_tipi = self._ifadə(d, ə)
                if elan_tipi is not None:
                    self._mənimsətmə_yoxla(dəyər_tipi, elan_tipi,
                                           getattr(d, "yer", b.yer),
                                           b.ad or "dəyişən")
                    self._bağla(b, elan_tipi, ə, sabit)
                else:
                    self._bağla(b, dəyər_tipi, ə, sabit)
            return False

        # Dağıtma: `dəyişən a, b = kortej`
        if len(c.dəyərlər) == 1:
            dəyər_tipi = self._ifadə(c.dəyərlər[0], ə)
            self._dağıtma(c.bağlamalar, dəyər_tipi, ə, sabit,
                          getattr(c.dəyərlər[0], "yer", c.yer))
            return False

        self.x.xəta(
            "ALQ-T001", "Mənimsətmədə saylar uyğun gəlmir", c.yer,
            f"{len(c.bağlamalar)} ad, {len(c.dəyərlər)} dəyər")
        return False

    def _dağıtma(self, bağlamalar: list[A.Bağlama], tip: T.Tip,
                 ə: Əhatə, sabit: bool, yer: Yer | None) -> None:
        qalan_var = any(b.növ == "qalan" for b in bağlamalar)

        if isinstance(tip, T.Kortej) and tip.elementlər and not qalan_var:
            if len(tip.elementlər) != len(bağlamalar):
                self.x.xəta(
                    "ALQ-T001", "Dağıtmada element sayı uyğun gəlmir",
                    yer,
                    f"{len(bağlamalar)} ad, "
                    f"{len(tip.elementlər)} element")
            for b, t in zip(bağlamalar, tip.elementlər):
                self._bağla(b, t, ə, sabit)
            return

        element = T.iterasiya_elementi(tip)
        if not T.naməlumdur(tip) and not T.iterasiya_oluna_bilir(tip):
            self.x.xəta("ALQ-T001",
                        f"`{tip.mətn()}` dağıtıla bilməz", yer, "",
                        "dağıtma yalnız kortej, siyahı və obyektlərdə")
        for b in bağlamalar:
            self._bağla(b, T.Siyahı(element) if b.növ == "qalan"
                        else element, ə, sabit)

    def _bağla(self, b: A.Bağlama, tip: T.Tip, ə: Əhatə,
               sabit: bool) -> None:
        if b.növ == "atma":
            return
        if b.növ in ("ad", "qalan"):
            elan_tipi = self._tip(b.tip, ə) if b.tip else tip
            if b.tip is not None:
                self._mənimsətmə_yoxla(tip, elan_tipi, b.yer, b.ad or "")
            self._ad_elan(b.ad or "_", elan_tipi, ə, sabit, b.yer)
            return
        if b.növ == "kortej":
            self._dağıtma(b.alt, tip, ə, sabit, b.yer)
            return
        if b.növ == "obyekt":
            for ad, alt in b.sahələr:
                sahə = self._üzv_tipi(tip, ad, b.yer, bildir=False)
                if alt is None:
                    self._ad_elan(ad, sahə, ə, sabit, b.yer)
                else:
                    self._bağla(alt, sahə, ə, sabit)

    def _ad_elan(self, ad: str, tip: T.Tip, ə: Əhatə, sabit: bool,
                 yer: Yer | None, növ: str = "dəyişən") -> None:
        köhnə = ə.yerli_tap(ad)
        if köhnə is not None and köhnə.elan_növü != "daxili":
            self.x.xəbərdarlıq(
                "ALQ-T023", "Təkrar elan", yer,
                f"`{ad}` bu əhatədə artıq elan olunub")
        elif (ə.üst is not None and ə.tap(ad) is not None
              and ə.tap(ad).elan_növü not in ("daxili", "funksiya")):
            self.x.xəbərdarlıq(
                "ALQ-T026", "Xarici adı kölgələyir", yer,
                f"`{ad}` xarici əhatədə də var")
        ə.elan(Bağlama(ad, tip, sabit, yer, False, növ))

    def _c_funksiya(self, c: A.FunksiyaElanı, ə: Əhatə) -> bool:
        b = ə.tap(c.ad)
        imza = (b.tip if b and isinstance(b.tip, T.FunksiyaTipi)
                else self._funksiya_imzası(c, ə))
        if b is None:
            ə.elan(Bağlama(c.ad, imza, True, c.yer, False, "funksiya"))
        self._funksiya_gövdəsi(c, imza, ə)
        return False

    def _funksiya_gövdəsi(self, c: Any, imza: T.FunksiyaTipi, ə: Əhatə,
                          özü: T.Tip | None = None) -> None:
        with self._generiklərlə(c):
            self._funksiya_gövdəsi_(c, imza, ə, özü)

    def _funksiya_gövdəsi_(self, c: Any, imza: T.FunksiyaTipi, ə: Əhatə,
                           özü: T.Tip | None = None) -> None:
        gövdə = getattr(c, "gövdə", None)
        if gövdə is None:
            return

        qaytarma = imza.qaytarma
        if imza.generator and isinstance(qaytarma, T.Generator):
            qaytarma = qaytarma.element
        elif imza.asinxron and isinstance(qaytarma, T.Gələcək):
            qaytarma = qaytarma.nəticə

        alt = ə.alt("funksiya", qaytarma)
        alt.generator = imza.generator
        alt.asinxron = imza.asinxron
        alt.dövrdə = False

        if özü is not None:
            alt.elan(Bağlama("özü", özü, True, c.yer, True, "parametr"))

        for p, tp in zip(c.parametrlər, imza.parametrlər):
            tip = tp.tip
            if tp.variadic:
                tip = T.Siyahı(tip) if not isinstance(tip, T.Lüğət) else tip
            if p.standart is not None:
                standart_tipi = self._ifadə(p.standart, ə)
                if tp.tip is not T.NAMƏLUM:
                    self._mənimsətmə_yoxla(standart_tipi, tp.tip, p.yer,
                                           p.ad)
            # `açıq xassə ad: mətn` formasındaki parametrlər avtomatik
            # sahəyə çevrilir — istifadəsiz sayılmamalıdır
            işlənib = (p.ad.startswith("_")
                       or getattr(p, "xassə_görünüşü", None) is not None)
            alt.elan(Bağlama(p.ad, tip, False, p.yer, işlənib,
                             "parametr"))

        çıxır = self._blok(gövdə, alt)

        # Qaytarma yolu yoxlaması
        if (not çıxır and not imza.generator
                and qaytarma not in (T.HEÇ, T.NAMƏLUM)
                and not T.naməlumdur(qaytarma)
                and not self.sərbəstdir):
            son = alt.son_ifadə_tipi
            if son is None:
                self.x.xəta(
                    "ALQ-T040", "Bütün yollarda `qaytar` yoxdur",
                    getattr(c, "yer", None),
                    f"funksiya `{qaytarma.mətn()}` qaytarmalıdır",
                    "hər budaqda `qaytar` olduğundan əmin olun")
            elif (not T.naməlumdur(son)
                  and not T.uyğundur(son, qaytarma)):
                # Son ifadə avtomatik qaytarılır, amma tipi uyğun gəlmir
                self.x.xəta(
                    "ALQ-T040", "Qaytarılan dəyər tipə uyğun deyil",
                    alt.son_ifadə_yeri or getattr(c, "yer", None),
                    f"son ifadə `{son.mətn()}` verir, "
                    f"`{qaytarma.mətn()}` gözlənilir",
                    "açıq `qaytar` əlavə edin")

        self._istifadəsizləri_bildir(alt)

    def _c_sinif(self, c: A.SinifElanı, ə: Əhatə) -> bool:
        s = self.siniflər.get(c.ad)
        if s is None:
            return False
        köhnə, self._cari_sinif = self._cari_sinif, s
        try:
            for ü in c.üzvlər:
                if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                    imza = (s.statiklər.get(ü.ad) if ü.statik
                            else s.metodlar.get(ü.ad))
                    if isinstance(imza, T.FunksiyaTipi):
                        self._funksiya_gövdəsi(
                            ü, imza, ə, None if ü.statik else s)
                elif isinstance(ü, A.QurucuElanı):
                    imza = s.quruculər.get(ü.ad or "")
                    if isinstance(imza, T.FunksiyaTipi):
                        self._funksiya_gövdəsi(ü, imza, ə, s)
                elif isinstance(ü, A.XassəElanı):
                    self._xassə_yoxla(ü, s, ə)
                elif isinstance(ü, A.DağıdıcıElanı):
                    alt = ə.alt("funksiya", T.HEÇ)
                    alt.elan(Bağlama("özü", s, True, ü.yer, True,
                                     "parametr"))
                    self._blok(ü.gövdə, alt)
        finally:
            self._cari_sinif = köhnə
        return False

    def _xassə_yoxla(self, ü: A.XassəElanı, s: T.SinifTipi,
                     ə: Əhatə) -> None:
        tip = s.sahələr.get(ü.ad) or s.statiklər.get(ü.ad) or T.NAMƏLUM
        if ü.standart is not None:
            dəyər = self._ifadə(ü.standart, ə)
            if ü.tip is not None:
                self._mənimsətmə_yoxla(dəyər, tip, ü.yer, ü.ad)
        for gövdə, qaytarma in ((ü.oxu_gövdəsi, tip),
                                (ü.yaz_gövdəsi, T.HEÇ)):
            if gövdə is None:
                continue
            alt = ə.alt("funksiya", qaytarma)
            alt.elan(Bağlama("özü", s, True, ü.yer, True, "parametr"))
            if gövdə is ü.yaz_gövdəsi and ü.yaz_parametri:
                alt.elan(Bağlama(ü.yaz_parametri, tip, False, ü.yer,
                                 True, "parametr"))
            self._blok(gövdə, alt)

    def _c_interfeys(self, c: A.InterfeysElanı, ə: Əhatə) -> bool:
        s = self.siniflər.get(c.ad)
        if s is None:
            return False
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                imza = s.metodlar.get(ü.ad)
                if isinstance(imza, T.FunksiyaTipi):
                    self._funksiya_gövdəsi(ü, imza, ə, s)
        return False

    def _c_sadalama(self, c: A.SadalamaElanı, ə: Əhatə) -> bool:
        e = self.sadalamalar.get(c.ad)
        for v in c.variantlar:
            if v.dəyər is not None:
                self._ifadə(v.dəyər, ə)
            for a in v.arqumentlər:
                self._ifadə(a.dəyər, ə)
        if e is not None:
            for ü in c.üzvlər:
                if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                    imza = e.metodlar.get(ü.ad)
                    if isinstance(imza, T.FunksiyaTipi):
                        self._funksiya_gövdəsi(ü, imza, ə, e)
        return False

    def _c_qarışıq(self, c: A.QarışıqElanı, ə: Əhatə) -> bool:
        return False

    def _c_genişlətmə(self, c: A.Genişlətmə, ə: Əhatə) -> bool:
        özü = self._tip(c.tip, ə)
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                self._funksiya_gövdəsi(ü, self._funksiya_imzası(ü, ə), ə,
                                       özü)
        return False

    def _c_modul(self, c: A.ModulElanı, ə: Əhatə) -> bool:
        alt = ə.alt("modul")
        self._elanları_qaldır(c.gövdə, alt)
        self._blok(c.gövdə, alt)
        üzvlər = {a: b.tip for a, b in alt.adlar.items()}
        ə.elan(Bağlama(c.ad, T.ModulTipi(c.ad, üzvlər), True, c.yer,
                       False, "modul"))
        return False

    def _c_idxal(self, c: A.İdxal, ə: Əhatə) -> bool:
        if id(c) in self._qaldırılmış_idxallar:
            return False                     # artıq qaldırılıb
        ad = ".".join(c.yol) if c.yol else (c.mətn_yolu or "")
        modul = self.modullar.get(ad)
        if modul is None and c.mətn_yolu is not None:
            modul = self._fayl_modulu(c)

        if modul is None and c.mətn_yolu is None and not c.elementlər \
                and not c.hamısı and ad and ad not in self.modullar:
            if not self.sərbəstdir and "." not in ad and "/" not in ad:
                self.x.xəbərdarlıq(
                    "ALQ-M001", "Modul tanınmır", c.yer,
                    f"`{ad}` standart kitabxanada yoxdur",
                    "yerli fayl üçün: gətir \"./fayl.alq\"")

        if c.hamısı:
            if modul is not None:
                for a, t in modul.üzvlər.items():
                    ə.elan(Bağlama(a, t, True, c.yer, True, "idxal"))
            return False

        if c.elementlər:
            for e in c.elementlər:
                tip = (modul.üzvlər.get(e.ad, T.NAMƏLUM) if modul
                       else T.NAMƏLUM)
                if modul is not None and e.ad not in modul.üzvlər \
                        and not self.sərbəstdir:
                    self.x.xəta(
                        "ALQ-M002", "Modulda belə ixrac yoxdur", c.yer,
                        f"`{ad}` modulunda `{e.ad}` yoxdur")
                ə.elan(Bağlama(e.ləqəb or e.ad, tip, True, c.yer, False,
                               "idxal",
                               modul.elanlar.get(e.ad) if modul else None))
            return False

        yerli_ad = c.ləqəb or (c.yol[-1] if c.yol else ad)
        ə.elan(Bağlama(yerli_ad, modul or T.ModulTipi(yerli_ad), True,
                       c.yer, False, "modul"))
        return False

    def _fayl_modulu(self, c: A.İdxal) -> T.ModulTipi | None:
        """
        `gətir "./x.alq" kimi m` — faylı ayırıb ayrıca yoxlayırıq;
        onun qlobal elanları modulun üzvləri olur (icraçıdakı kimi).
        Nisbi yol idxal edən faylın qovluğuna nisbətəndir.
        """
        from pathlib import Path
        mənbə = getattr(c.yer, "mənbə", None)
        əsas = getattr(mənbə, "yol", None)
        p = Path(c.mətn_yolu or "")
        if not p.is_absolute():
            if əsas is None:
                return None                  # yaddaşdakı mətn — baza yoxdur
            p = Path(əsas).resolve().parent / p
        if not p.exists():
            for uzantı in (".alq", ".alqor"):
                if Path(str(p) + uzantı).exists():
                    p = Path(str(p) + uzantı)
                    break
        if not p.is_file():
            if not self.sərbəstdir:
                self.x.xəta("ALQ-M001", "Modul faylı tapılmadı", c.yer,
                            f'"{c.mətn_yolu}" yoxdur')
            return None
        return fayl_modulu(p.resolve(), self.rejim)

    def _c_tip_aliası(self, c: A.TipAliası, ə: Əhatə) -> bool:
        if ə.yerli_tap(c.ad) is None:
            ə.elan(Bağlama(c.ad, self._tip(c.tip, ə), True, c.yer, True,
                           "tip"))
        return False

    # ── İdarəetmə ─────────────────────────────────────────────────────

    def _c_ifadə(self, c: A.İfadəCümləsi, ə: Əhatə) -> bool:
        self._ifadə(c.ifadə, ə)
        return False

    def _c_şərt(self, c: A.Şərt, ə: Əhatə) -> bool:
        hamısı_çıxır = True
        çıxan_şərtlər: list[A.İfadə] = []

        for şərt, gövdə in c.budaqlar:
            self._şərt_yoxla(şərt, ə)
            alt = ə.alt()
            self._daralmanı_tətbiq(şərt, True, alt)
            if self._blok(gövdə, alt):
                # Bu budaq mütləq çıxır (qaytar/at/dayan) — deməli
                # `əgər`-dən sonrakı koda yalnız şərt YANLIŞ olanda
                # çatılır. Əks daralma tətbiq olunmalıdır:
                #     əgər a boşdur onda qaytar son
                #     yaz(a.böyüyə())      ← burada `a` boş deyil
                çıxan_şərtlər.append(şərt)
            else:
                hamısı_çıxır = False

        if c.yoxsa is not None:
            alt = ə.alt()
            for şərt, _ in c.budaqlar:
                self._daralmanı_tətbiq(şərt, False, alt)
            if not self._blok(c.yoxsa, alt):
                hamısı_çıxır = False
            return hamısı_çıxır

        for şərt in çıxan_şərtlər:
            self._daralmanı_tətbiq(şərt, False, ə)
        return False

    def _c_varsa(self, c: A.Varsa, ə: Əhatə) -> bool:
        alt = ə.alt()
        for bağlama, ifadə in c.bağlamalar:
            tip = self._ifadə(ifadə, alt)
            açıq = T.açılmış(tip)
            if bağlama is not None:
                self._bağla(bağlama, açıq, alt, False)
            elif isinstance(ifadə, A.Ad):
                b = alt.tap(ifadə.ad)
                if b is not None:
                    alt.elan(Bağlama(ifadə.ad, açıq, b.sabit, b.yer,
                                     True, b.elan_növü))
        gövdə_çıxır = self._blok(c.gövdə, alt)
        if c.yoxsa is None:
            return False
        return gövdə_çıxır and self._blok(c.yoxsa, ə.alt())

    def _c_yoxdursa(self, c: A.Yoxdursa, ə: Əhatə) -> bool:
        for bağlama, ifadə in c.bağlamalar:
            tip = self._ifadə(ifadə, ə)
            açıq = T.açılmış(tip)
            if bağlama is not None:
                self._bağla(bağlama, açıq, ə, False)
            elif isinstance(ifadə, A.Ad):
                b = ə.tap(ifadə.ad)
                if b is not None:
                    ə.elan(Bağlama(ifadə.ad, açıq, b.sabit, b.yer, True,
                                   b.elan_növü))
        çıxır = self._blok(c.gövdə, ə.alt())
        if not çıxır and not self.sərbəstdir:
            self.x.xəbərdarlıq(
                "ALQ-T041", "`yoxdursa` bloku çıxmalıdır", c.yer,
                "`qaytar`, `at`, `dayan` və ya `davam et` lazımdır")
        return False

    def _c_seç(self, c: A.Seç, ə: Əhatə) -> bool:
        tip = self._ifadə(c.ifadə, ə) if c.ifadə is not None else T.MƏNTİQ
        hamısı_çıxır = bool(c.hallar) or c.digər is not None
        for hal in c.hallar:
            alt = ə.alt()
            for naxış in hal.naxışlar:
                self._naxış(naxış, tip, alt, c.tipə_görə)
            if hal.mühafizə is not None:
                self._şərt_yoxla(hal.mühafizə, alt)
            if not self._blok(hal.gövdə, alt):
                hamısı_çıxır = False
        if c.digər is not None:
            if not self._blok(c.digər, ə.alt()):
                hamısı_çıxır = False
        else:
            hamısı_çıxır = False

        # Sadalama üzərində tamlıq yoxlaması
        if (isinstance(tip, T.SadalamaTipi) and c.digər is None
                and not self.sərbəstdir):
            əhatə_olunan = {
                n.dəyər for hal in c.hallar for n in hal.naxışlar
                if n.növ == "ad" and isinstance(n.dəyər, str)}
            əhatə_olunan |= {
                (n.tip.yol[-1] if isinstance(n.tip, A.TipAdı) else "")
                for hal in c.hallar for n in hal.naxışlar
                if n.növ in ("tip", "obyekt") and n.tip is not None}
            çatışmayan = [v for v in tip.variantlar
                          if v not in əhatə_olunan]
            if çatışmayan:
                self.x.xəta(
                    "ALQ-T031", "`seç` bütün halları əhatə etmir", c.yer,
                    f"çatışmayan: {', '.join(çatışmayan[:5])}",
                    "`digər hallarda` bəndi əlavə edin")
        return hamısı_çıxır

    def _naxış(self, n: A.Naxış, tip: T.Tip, ə: Əhatə,
               tipə_görə: bool) -> None:
        if n.növ == "atma":
            return
        if n.növ == "literal":
            self._ifadə(n.dəyər, ə)
            return
        if n.növ == "diapazon":
            self._ifadə(n.dəyər, ə)
            self._ifadə(n.diapazon_son, ə)
            return
        if n.növ == "tip":
            hədəf = self._tip(n.tip, ə)
            if tipə_görə:
                return
            return
        if n.növ == "ad":
            if isinstance(tip, T.SadalamaTipi) and n.dəyər in tip.variantlar:
                return
            ə.elan(Bağlama(str(n.dəyər), tip, False, n.yer, True,
                           "parametr"))
            return
        if n.növ in ("kortej", "siyahı"):
            element = (tip.elementlər if isinstance(tip, T.Kortej)
                       else None)
            for i, alt in enumerate(n.alt):
                alt_tipi = (element[i] if element and i < len(element)
                            else T.iterasiya_elementi(tip))
                self._naxış(alt, alt_tipi, ə, False)
            if n.qalan:
                ə.elan(Bağlama(n.qalan, T.Siyahı(
                    T.iterasiya_elementi(tip)), False, n.yer, True,
                    "parametr"))
            return
        if n.növ == "obyekt":
            hədəf = self._tip(n.tip, ə) if n.tip else T.NAMƏLUM
            for alt in n.alt:
                self._naxış(alt, T.NAMƏLUM, ə, False)
            for ad, alt in n.sahələr:
                sahə = self._üzv_tipi(hədəf, ad, n.yer, bildir=False)
                if alt is None:
                    ə.elan(Bağlama(ad, sahə, False, n.yer, True,
                                   "parametr"))
                else:
                    self._naxış(alt, sahə, ə, False)

    def _c_nə_qədər_ki(self, c: A.NəQədərKi, ə: Əhatə) -> bool:
        self._şərt_yoxla(c.şərt, ə)
        alt = ə.alt()
        alt.dövrdə = True
        self._daralmanı_tətbiq(c.şərt, True, alt)
        self._blok(c.gövdə, alt)
        return False

    def _c_həmişə(self, c: A.Həmişə, ə: Əhatə) -> bool:
        alt = ə.alt()
        alt.dövrdə = True
        self._blok(c.gövdə, alt)
        return False      # `dayan` ola bilər, çıxmış saymırıq

    def _c_təkrarla(self, c: A.Təkrarla, ə: Əhatə) -> bool:
        say = self._ifadə(c.say, ə)
        if not T.naməlumdur(say) and say != T.TAM:
            self.x.xəta("ALQ-T001",
                        "`təkrarla` tam ədəd gözləyir",
                        getattr(c.say, "yer", c.yer),
                        f"`{say.mətn()}` gəlib")
        alt = ə.alt()
        alt.dövrdə = True
        if c.sayğac:
            alt.elan(Bağlama(c.sayğac, T.TAM, True, c.yer, True,
                             "parametr"))
        self._blok(c.gövdə, alt)
        return False

    def _c_təkrarla_nə_qədər(self, c: A.TəkrarlaNəQədər,
                             ə: Əhatə) -> bool:
        alt = ə.alt()
        alt.dövrdə = True
        self._blok(c.gövdə, alt)
        self._şərt_yoxla(c.şərt, ə)
        return False

    def _c_hər(self, c: A.Hər, ə: Əhatə) -> bool:
        mənbə = self._ifadə(c.mənbə, ə)
        if not T.naməlumdur(mənbə) and not T.iterasiya_oluna_bilir(mənbə):
            self.x.xəta(
                "ALQ-T009", "Bu tip üzərində dövr qurulmur",
                getattr(c.mənbə, "yer", c.yer),
                f"`{mənbə.mətn()}` iterasiya olunmur",
                "siyahı, dəst, lüğət, mətn, diapazon və generator olar")

        element = T.iterasiya_elementi(mənbə)
        if c.asinxron and isinstance(element, T.Gələcək):
            element = element.nəticə

        alt = ə.alt()
        alt.dövrdə = True

        if len(c.bağlamalar) >= 2:
            if isinstance(mənbə, T.Lüğət):
                self._bağla(c.bağlamalar[0], mənbə.açar, alt, False)
                self._bağla(c.bağlamalar[1], mənbə.dəyər, alt, False)
                for b in c.bağlamalar[2:]:
                    self._bağla(b, T.NAMƏLUM, alt, False)
            else:
                self._bağla(c.bağlamalar[0], T.TAM, alt, False)
                qalan = c.bağlamalar[1:]
                if len(qalan) == 1:
                    self._bağla(qalan[0], element, alt, False)
                else:
                    self._dağıtma(qalan, element, alt, False, c.yer)
        else:
            self._bağla(c.bağlamalar[0], element, alt, False)

        if c.addım is not None:
            self._ifadə(c.addım, alt)
        if c.şərt is not None:
            self._şərt_yoxla(c.şərt, alt)
        self._blok(c.gövdə, alt)
        if c.yoxsa is not None:
            self._blok(c.yoxsa, ə.alt())
        return False

    def _c_dayan(self, c: A.Dayan, ə: Əhatə) -> bool:
        if not ə.dövrdə:
            self.x.xəta("ALQ-P008", "`dayan` dövrədən kənarda", c.yer)
        return True

    def _c_davam(self, c: A.DavamEt, ə: Əhatə) -> bool:
        if not ə.dövrdə:
            self.x.xəta("ALQ-P009", "`davam et` dövrədən kənarda", c.yer)
        return True

    def _c_qaytar(self, c: A.Qaytar, ə: Əhatə) -> bool:
        f = ə.funksiya_əhatəsi()
        if f is None:
            self.x.xəta("ALQ-P010", "`qaytar` funksiyadan kənarda", c.yer)
            return True

        if not c.dəyərlər:
            if (f.qaytarma not in (None, T.HEÇ)
                    and not T.naməlumdur(f.qaytarma)
                    and not self.sərbəstdir):
                self.x.xəta(
                    "ALQ-T005", "Qaytarma dəyəri gözlənilirdi", c.yer,
                    f"funksiya `{f.qaytarma.mətn()}` qaytarmalıdır")
            return True

        tip = (self._ifadə(c.dəyərlər[0], ə) if len(c.dəyərlər) == 1
               else T.Kortej(tuple(self._ifadə(d, ə)
                                   for d in c.dəyərlər)))
        if f.qaytarma is not None and not T.naməlumdur(f.qaytarma):
            if not T.uyğundur(tip, f.qaytarma):
                self.x.xəta(
                    "ALQ-T005", "Qaytarma tipi uyğun deyil",
                    getattr(c.dəyərlər[0], "yer", c.yer),
                    f"`{tip.mətn()}` qaytarılır, "
                    f"`{f.qaytarma.mətn()}` gözlənilir")
        return True

    def _c_ver(self, c: A.Ver, ə: Əhatə) -> bool:
        if c.dəyər is not None:
            tip = self._ifadə(c.dəyər, ə)
            f = ə.funksiya_əhatəsi()
            if (f is not None and f.generator and f.qaytarma is not None
                    and not T.naməlumdur(f.qaytarma)
                    and not T.uyğundur(tip, f.qaytarma)):
                self.x.xəta(
                    "ALQ-T005", "`ver` tipi uyğun deyil",
                    getattr(c.dəyər, "yer", c.yer),
                    f"`{tip.mətn()}` verilir, "
                    f"`{f.qaytarma.mətn()}` gözlənilir")
        return False

    def _c_at(self, c: A.At, ə: Əhatə) -> bool:
        if c.ifadə is not None:
            self._ifadə(c.ifadə, ə)
        return True

    def _c_cəhd(self, c: A.Cəhd, ə: Əhatə) -> bool:
        gövdə_çıxır = self._blok(c.gövdə, ə.alt())
        hamısı_çıxır = gövdə_çıxır
        for tutma in c.tutmalar:
            alt = ə.alt()
            tip: T.Tip = T.NAMƏLUM
            if tutma.tiplər:
                tip = T.birləşmə(*[self._tip(t, alt)
                                   for t in tutma.tiplər])
            if tutma.ad:
                alt.elan(Bağlama(tutma.ad, tip, True, tutma.yer, True,
                                 "parametr"))
            if tutma.mühafizə is not None:
                self._şərt_yoxla(tutma.mühafizə, alt)
            if not self._blok(tutma.gövdə, alt):
                hamısı_çıxır = False
        if c.nəhayət is not None:
            self._blok(c.nəhayət, ə.alt())
        return hamısı_çıxır and bool(c.tutmalar)

    def _c_iddia(self, c: A.İddia, ə: Əhatə) -> bool:
        self._şərt_yoxla(c.şərt, ə)
        if c.mesaj is not None:
            self._ifadə(c.mesaj, ə)
        return False

    def _c_təmin(self, c: A.Təmin, ə: Əhatə) -> bool:
        self._şərt_yoxla(c.şərt, ə)
        self._blok(c.gövdə, ə.alt())
        return False

    def _c_gecikdir(self, c: A.Gecikdir, ə: Əhatə) -> bool:
        self._ifadə(c.ifadə, ə)
        return False

    def _c_istifadə(self, c: A.İstifadə, ə: Əhatə) -> bool:
        alt = ə.alt()
        for ad, ifadə in c.bağlamalar:
            alt.elan(Bağlama(ad, self._ifadə(ifadə, ə), True, c.yer,
                             False, "dəyişən"))
        self._blok(c.gövdə, alt)
        self._istifadəsizləri_bildir(alt)
        return False

    def _c_global(self, c: A.Global, ə: Əhatə) -> bool:
        for ad in c.adlar:
            b = self.qlobal.tap(ad)
            ə.elan(Bağlama(ad, b.tip if b else T.NAMƏLUM, False, c.yer,
                           True, "global"))
        return False

    def _c_artırma(self, c: A.Artırma, ə: Əhatə) -> bool:
        tip = self._ifadə(c.hədəf, ə)
        if not T.naməlumdur(tip) and not T.ədəddir(tip):
            self.x.xəta("ALQ-T008",
                        f"`{c.op}` operatoru `{tip.mətn()}` tipinə "
                        "tətbiq edilmir", c.yer)
        self._mənimsətmə_hədəfi_yoxla(c.hədəf, ə)
        return False

    def _c_keç(self, c: A.Cümlə, ə: Əhatə) -> bool:
        return False

    def _c_blok_qovşağı(self, c: Any, ə: Əhatə) -> bool:
        self._blok(c.gövdə, ə.alt())
        return False

    # ═══════════════════════════════════════════════════════════════════
    #  Şərtlər və daralma
    # ═══════════════════════════════════════════════════════════════════

    def _şərt_yoxla(self, şərt: A.İfadə, ə: Əhatə) -> None:
        tip = self._ifadə(şərt, ə)
        if T.naməlumdur(tip) or tip == T.MƏNTİQ:
            return
        köməklər = ["şərt `məntiq` tipi olmalıdır"]
        if isinstance(tip, (T.Siyahı, T.Lüğət, T.Dəst)):
            köməklər.append("boş olub-olmamağı yoxlamaq üçün: "
                            "`deyil boşdur(x)`")
        elif T.ədəddir(tip):
            köməklər.append("sıfırla müqayisə edin: `x != 0`")
        elif T.ixtiyaridir(tip):
            köməklər.append("boş yoxlaması: `x boş deyil`")
        self.x.xəta("ALQ-T007", "Şərt `məntiq` tipi olmalıdır",
                    getattr(şərt, "yer", None),
                    f"`{tip.mətn()}` gəlib", *köməklər)

    def _daralmanı_tətbiq(self, şərt: A.İfadə, doğru: bool,
                          ə: Əhatə) -> None:
        """`əgər x tipidir mətn onda` → gövdədə `x: mətn`."""
        for ad, tip in self._daralma(şərt, doğru, ə).items():
            b = ə.tap(ad)
            ə.elan(Bağlama(ad, tip, b.sabit if b else False,
                           b.yer if b else None, True,
                           b.elan_növü if b else "dəyişən"))

    def _daralma(self, şərt: A.İfadə, doğru: bool,
                 ə: Əhatə) -> dict[str, T.Tip]:
        nəticə: dict[str, T.Tip] = {}

        # deyil (...)
        if isinstance(şərt, A.TəkOperand) and şərt.op in ("deyil", "!"):
            return self._daralma(şərt.operand, not doğru, ə)

        # x tipidir T
        if isinstance(şərt, A.TipYoxlama) and isinstance(şərt.ifadə, A.Ad):
            hədəf = self._tip(şərt.tip, ə)
            if doğru and not T.naməlumdur(hədəf):
                nəticə[şərt.ifadə.ad] = hədəf
            return nəticə

        # x boşdur / x boş deyil
        if isinstance(şərt, A.BoşYoxlama) and isinstance(şərt.ifadə, A.Ad):
            b = ə.tap(şərt.ifadə.ad)
            if b is not None:
                boş_olmalı = (şərt.inkar is False) == doğru
                nəticə[şərt.ifadə.ad] = (T.HEÇ if boş_olmalı
                                         else T.açılmış(b.tip))
            return nəticə

        # x == boş / x != boş
        if isinstance(şərt, A.İkili) and şərt.op in ("==", "!="):
            for sol, sağ in ((şərt.sol, şərt.sağ), (şərt.sağ, şərt.sol)):
                if (isinstance(sol, A.Ad) and isinstance(sağ, A.Literal)
                        and sağ.növ == "boş"):
                    b = ə.tap(sol.ad)
                    if b is not None:
                        boşdur = (şərt.op == "==") == doğru
                        nəticə[sol.ad] = (T.HEÇ if boşdur
                                          else T.açılmış(b.tip))
                    return nəticə

        # a və b → hər ikisi daralır (doğru budaqda)
        if isinstance(şərt, A.İkili) and şərt.op in ("və", "&&") and doğru:
            nəticə.update(self._daralma(şərt.sol, True, ə))
            nəticə.update(self._daralma(şərt.sağ, True, ə))
            return nəticə

        # a və ya b → yalnız yanlış budaqda hər ikisi daralır
        if (isinstance(şərt, A.İkili) and şərt.op in ("və ya", "||")
                and not doğru):
            nəticə.update(self._daralma(şərt.sol, False, ə))
            nəticə.update(self._daralma(şərt.sağ, False, ə))
            return nəticə

        return nəticə

    # ═══════════════════════════════════════════════════════════════════
    #  İfadələr
    # ═══════════════════════════════════════════════════════════════════

    def _ifadə(self, e: Any, ə: Əhatə) -> T.Tip:
        if e is None:
            return T.NAMƏLUM
        işləyici = _İFADƏLƏR.get(type(e))
        if işləyici is None:
            return T.NAMƏLUM
        tip = işləyici(self, e, ə)
        if self.qeyd and isinstance(e, (A.Ad, A.Üzv)):
            obyekt = self._son_obyekt_tipi if isinstance(e, A.Üzv) \
                else None
            self.ifadə_tipləri.append((e, tip, obyekt))
        return tip

    def _e_literal(self, e: A.Literal, ə: Əhatə) -> T.Tip:
        return {
            "tam": T.TAM, "onluq": T.ONLUQ, "mətn": T.MƏTN,
            "simvol": T.SİMVOL, "bayt": T.BAYT, "məntiq": T.MƏNTİQ,
            "boş": T.HEÇ,
        }.get(e.növ, T.NAMƏLUM)

    def _e_şablon(self, e: A.ŞablonMətn, ə: Əhatə) -> T.Tip:
        for p in e.parçalar:
            if isinstance(p, A.KodHissəsi):
                self._ifadə(p.ifadə, ə)
        return T.MƏTN

    def _e_ad(self, e: A.Ad, ə: Əhatə) -> T.Tip:
        b = ə.tap(e.ad)
        if b is None:
            if e.ad in self.modullar:
                return self.modullar[e.ad]
            self.x.xəta(
                "ALQ-T022", "Təyin edilməmiş dəyişən", e.yer,
                f"`{e.ad}` heç yerdə elan olunmayıb",
                *self._oxşar_adlar(e.ad, ə))
            return T.NAMƏLUM
        b.istifadə_olunub = True
        if self.qeyd:
            self.istinadlar.append((e, b))
        return b.tip

    def _oxşar_adlar(self, ad: str, ə: Əhatə) -> list[str]:
        from .elifba import latınla
        namizədlər: list[str] = []
        cari: Əhatə | None = ə
        while cari is not None:
            namizədlər.extend(cari.adlar)
            cari = cari.üst
        for n in namizədlər:
            if latınla(n) == ad and n != ad:
                return [f"`{n}` demək istəyirdiniz? ASCII çevrilməsi "
                        "yalnız açar sözlərə aiddir"]
        yaxın = [n for n in namizədlər
                 if len(n) > 2 and n.startswith(ad[:3])][:3]
        return [f"bəlkə: {', '.join(yaxın)}"] if yaxın else []

    def _e_özü(self, e: A.Özü, ə: Əhatə) -> T.Tip:
        b = ə.tap("özü")
        if b is None:
            self.x.xəta("ALQ-P011", "`özü` metoddan kənarda", e.yer)
            return T.NAMƏLUM
        return b.tip

    def _e_üst(self, e: A.Üst, ə: Əhatə) -> T.Tip:
        if self._cari_sinif is not None and self._cari_sinif.baza:
            return self._cari_sinif.baza
        return T.NAMƏLUM

    # ── Operatorlar ───────────────────────────────────────────────────

    def _e_ikili(self, e: A.İkili, ə: Əhatə) -> T.Tip:
        op = e.op

        if op in ("və", "&&", "və ya", "||"):
            self._şərt_yoxla(e.sol, ə)
            alt = ə.alt()
            self._daralmanı_tətbiq(e.sol, op in ("və", "&&"), alt)
            self._şərt_yoxla(e.sağ, alt)
            return T.MƏNTİQ

        sol = self._ifadə(e.sol, ə)

        if op == "??":
            sağ = self._ifadə(e.sağ, ə)
            if not T.ixtiyaridir(sol) and not T.naməlumdur(sol):
                self.x.xəbərdarlıq(
                    "ALQ-T015", "`??` ixtiyari olmayan dəyərdə", e.yer,
                    f"`{sol.mətn()}` heç vaxt boş olmur")
            return T.birləşdir(T.açılmış(sol), sağ)

        sağ = self._ifadə(e.sağ, ə)
        return self._ikili_nəticə(op, sol, sağ, e)

    def _ikili_nəticə(self, op: str, sol: T.Tip, sağ: T.Tip,
                      e: A.İkili) -> T.Tip:
        if op in ("==", "!="):
            return T.MƏNTİQ

        if T.naməlumdur(sol) or T.naməlumdur(sağ):
            return T.NAMƏLUM

        # Sinif operator yükləməsi
        if isinstance(sol, T.SinifTipi):
            metod = _OPERATOR_METODLARI.get(op)
            if metod:
                imza = sol.üzv(metod)
                if isinstance(imza, T.FunksiyaTipi):
                    return imza.qaytarma
            if op in ("<", ">", "<=", ">="):
                return T.MƏNTİQ
            return T.NAMƏLUM

        if op in ("<", ">", "<=", ">="):
            if not self._müqayisə_olunur(sol, sağ):
                self._operator_xətası(op, sol, sağ, e)
            return T.MƏNTİQ
        if op == "<=>":
            return T.TAM

        if op in ("..", "..<"):
            return T.DİAPAZON

        if op in ("&", "|", "^", "<<", ">>", ">>>"):
            if isinstance(sol, T.Dəst) and isinstance(sağ, T.Dəst):
                return sol
            if sol == T.TAM and sağ == T.TAM:
                return T.TAM
            self._operator_xətası(op, sol, sağ, e)
            return T.NAMƏLUM

        if op == "+":
            if sol == T.MƏTN:
                if sağ != T.MƏTN:
                    self.x.xəta(
                        "ALQ-T008", "Operator bu tiplərə tətbiq edilmir",
                        e.yer,
                        f"`mətn` və `{sağ.mətn()}` toplanmır",
                        'interpolyasiya işlədin: "mətn: {dəyər}"',
                        "və ya çevirin: mətn + mətnƏt(dəyər)")
                return T.MƏTN
            if isinstance(sol, T.Siyahı):
                if not isinstance(sağ, T.Siyahı):
                    self._operator_xətası(op, sol, sağ, e)
                return T.birləşdir(sol, sağ)
            if T.ədəddir(sol) and T.ədəddir(sağ):
                return T.ONLUQ if T.ONLUQ in (sol, sağ) else T.TAM
            self._operator_xətası(op, sol, sağ, e)
            return T.NAMƏLUM

        if op == "*":
            if sol == T.MƏTN and sağ == T.TAM:
                return T.MƏTN
            if isinstance(sol, T.Siyahı) and sağ == T.TAM:
                return sol
            if T.ədəddir(sol) and T.ədəddir(sağ):
                return T.ONLUQ if T.ONLUQ in (sol, sağ) else T.TAM
            self._operator_xətası(op, sol, sağ, e)
            return T.NAMƏLUM

        if op == "/":
            if T.ədəddir(sol) and T.ədəddir(sağ):
                return T.ONLUQ
            self._operator_xətası(op, sol, sağ, e)
            return T.NAMƏLUM

        if op == "~/":
            if T.ədəddir(sol) and T.ədəddir(sağ):
                return T.TAM
            self._operator_xətası(op, sol, sağ, e)
            return T.NAMƏLUM

        if op in ("-", "%", "**"):
            if T.ədəddir(sol) and T.ədəddir(sağ):
                return T.ONLUQ if T.ONLUQ in (sol, sağ) else T.TAM
            self._operator_xətası(op, sol, sağ, e)
            return T.NAMƏLUM

        return T.NAMƏLUM

    @staticmethod
    def _müqayisə_olunur(sol: T.Tip, sağ: T.Tip) -> bool:
        if T.ədəddir(sol) and T.ədəddir(sağ):
            return True
        if sol == sağ and sol in (T.MƏTN, T.SİMVOL):
            return True
        if isinstance(sol, T.Dəst) and isinstance(sağ, T.Dəst):
            return True
        return False

    def _operator_xətası(self, op: str, sol: T.Tip, sağ: T.Tip,
                         e: Any) -> None:
        self.x.xəta(
            "ALQ-T008", "Operator bu tiplərə tətbiq edilmir",
            getattr(e, "yer", None),
            f"`{op}` operatoru `{sol.mətn()}` və `{sağ.mətn()}` "
            "tiplərinə tətbiq edilmir")

    def _e_tək(self, e: A.TəkOperand, ə: Əhatə) -> T.Tip:
        if e.op in ("deyil", "!"):
            self._şərt_yoxla(e.operand, ə)
            return T.MƏNTİQ
        tip = self._ifadə(e.operand, ə)
        if T.naməlumdur(tip):
            return T.NAMƏLUM
        if e.op in ("-", "+"):
            if isinstance(tip, T.SinifTipi):
                return tip
            if not T.ədəddir(tip):
                self.x.xəta(
                    "ALQ-T008", "Operator bu tipə tətbiq edilmir", e.yer,
                    f"`{e.op}` `{tip.mətn()}` tipinə tətbiq edilmir")
            return tip
        if e.op == "~":
            if tip != T.TAM:
                self.x.xəta("ALQ-T008", "`~` tam ədəd tələb edir", e.yer,
                            f"`{tip.mətn()}` gəlib")
            return T.TAM
        return T.NAMƏLUM

    def _e_mənimsətmə(self, e: A.Mənimsətmə, ə: Əhatə) -> T.Tip:
        dəyərlər = [self._ifadə(d, ə) for d in e.dəyərlər]

        if len(e.hədəflər) == 1 and len(dəyərlər) == 1:
            hədəf_tipi = self._ifadə(e.hədəflər[0], ə)
            self._mənimsətmə_hədəfi_yoxla(e.hədəflər[0], ə)
            if e.op == "=":
                self._mənimsətmə_yoxla(
                    dəyərlər[0], hədəf_tipi,
                    getattr(e.dəyərlər[0], "yer", e.yer),
                    self._hədəf_adı(e.hədəflər[0]))
                return dəyərlər[0]
            if e.op in ("??=", "?="):
                return T.birləşdir(T.açılmış(hədəf_tipi), dəyərlər[0])
            nəticə = self._ikili_nəticə(e.op[:-1], hədəf_tipi,
                                        dəyərlər[0], e)
            self._mənimsətmə_yoxla(nəticə, hədəf_tipi, e.yer,
                                   self._hədəf_adı(e.hədəflər[0]))
            return nəticə

        for h in e.hədəflər:
            self._ifadə(h, ə)
            self._mənimsətmə_hədəfi_yoxla(h, ə)
        return T.NAMƏLUM

    @staticmethod
    def _hədəf_adı(h: A.İfadə) -> str:
        if isinstance(h, A.Ad):
            return h.ad
        if isinstance(h, A.Üzv):
            return h.ad
        return "hədəf"

    def _mənimsətmə_hədəfi_yoxla(self, h: A.İfadə, ə: Əhatə) -> None:
        if isinstance(h, A.Ad):
            b = ə.tap(h.ad)
            if b is not None and b.sabit:
                self.x.xəta(
                    "ALQ-T020", "Sabitə mənimsətmə", h.yer,
                    f"`{h.ad}` {b.elan_növü}dir, dəyişdirilə bilməz")

    def _mənimsətmə_yoxla(self, mənbə: T.Tip, hədəf: T.Tip,
                          yer: Yer | None, ad: str) -> None:
        if T.naməlumdur(mənbə) or T.naməlumdur(hədəf):
            return
        if self.sərbəstdir:
            return
        if T.uyğundur(mənbə, hədəf):
            return

        köməklər: list[str] = []
        if mənbə == T.HEÇ:
            self.x.xəta(
                "ALQ-T012", "`boş` bu tipə mənimsədilə bilməz", yer,
                f"`{ad}` tipi `{hədəf.mətn()}`-dir",
                f"ixtiyari etmək üçün: `{hədəf.mətn()}?`")
            return
        if hədəf == T.TAM and mənbə == T.ONLUQ:
            köməklər.append("açıq çevirin: `x kimi tam` "
                            "(onluq hissə kəsilir)")
        elif hədəf == T.MƏTN:
            köməklər.append("çevirin: `mətnƏt(x)`")
        elif hədəf == T.TAM and mənbə == T.MƏTN:
            köməklər.append("çevirin: `tamƏt(x)`")
        self.x.xəta(
            "ALQ-T001", "Tip uyğunsuzluğu", yer,
            f"`{mənbə.mətn()}` → `{hədəf.mətn()}`", *köməklər)

    # ── Müraciət ──────────────────────────────────────────────────────

    def _e_üzv(self, e: A.Üzv, ə: Əhatə) -> T.Tip:
        obyekt = self._ifadə(e.obyekt, ə)

        if T.ixtiyaridir(obyekt) and not e.təhlükəsiz:
            if not T.naməlumdur(obyekt) and obyekt != T.HEÇ:
                self.x.xəta(
                    "ALQ-T013",
                    "İxtiyari dəyər yoxlanmadan istifadə olunub", e.yer,
                    f"`{obyekt.mətn()}` boş ola bilər",
                    "təhlükəsiz çağırış: `?.`",
                    "yoxlama: `əgər x boş deyil onda ... son`",
                    "standart dəyər: `x ?? standart`")
        obyekt = T.açılmış(obyekt)
        self._son_obyekt_tipi = obyekt
        tip = self._üzv_tipi(obyekt, e.ad, e.yer)
        if self.qeyd and isinstance(obyekt, T.ModulTipi) \
                and e.ad in obyekt.elanlar:
            self.üzv_istinadları.append((e, obyekt.elanlar[e.ad]))
        if not e.təhlükəsiz:
            return tip
        # `a?.uzunluq()` → `tam?`. İxtiyarilik funksiyanın ÖZÜNƏ yox,
        # onun NƏTİCƏSİNƏ tətbiq olunur, yoxsa çağırılmaz olardı.
        if isinstance(tip, T.FunksiyaTipi):
            return T.FunksiyaTipi(tip.parametrlər,
                                  T.ixtiyari(tip.qaytarma),
                                  tip.asinxron, tip.generator)
        return T.ixtiyari(tip)

    def _üzv_tipi(self, obyekt: T.Tip, ad: str, yer: Yer | None,
                  bildir: bool = True) -> T.Tip:
        if T.naməlumdur(obyekt):
            return T.NAMƏLUM

        if isinstance(obyekt, T.ModulTipi):
            if ad in obyekt.üzvlər:
                return obyekt.üzvlər[ad]
            if bildir and not self.sərbəstdir and obyekt.üzvlər:
                self.x.xəta(
                    "ALQ-M002", "Modulda belə üzv yoxdur", yer,
                    f"`{obyekt.ad}` modulunda `{ad}` yoxdur",
                    *self._üzv_təklifi(ad, obyekt.üzvlər))
            return T.NAMƏLUM

        if isinstance(obyekt, T.SinifTipi):
            üzv = obyekt.üzv(ad)
            if üzv is not None:
                return üzv
            if ad in obyekt.quruculər:
                return obyekt.quruculər[ad]
            if bildir and self.sərtdir:
                self.x.xəta(
                    "ALQ-T006", "Bu tipdə belə üzv yoxdur", yer,
                    f"`{obyekt.ad}` tipində `{ad}` yoxdur")
            return T.NAMƏLUM

        if isinstance(obyekt, T.SadalamaTipi):
            if ad in obyekt.variantlar:
                return obyekt
            if ad in obyekt.metodlar:
                return obyekt.metodlar[ad]
            if ad in ("hamısı",):
                return F(qaytarır=T.Siyahı(obyekt))
            if ad in ("adla", "dəyərlə"):
                return F(T.İSTƏNİLƏN, qaytarır=T.ixtiyari(obyekt))
            if ad in ("sıra", "sayı"):
                return F(qaytarır=T.TAM)
            if ad in ("dəyər",):
                return F(qaytarır=T.NAMƏLUM)
            if ad in ("adı", "mətnƏt"):
                return F(qaytarır=T.MƏTN)
            return T.NAMƏLUM

        cədvəl = self._metod_cədvəli(obyekt)
        if cədvəl is None:
            if bildir and not self.sərbəstdir:
                self.x.xəta(
                    "ALQ-T006", "Bu tipdə üzv yoxdur", yer,
                    f"`{obyekt.mətn()}` tipində `{ad}` ola bilməz")
            return T.NAMƏLUM

        if ad in cədvəl:
            return cədvəl[ad]

        if bildir and not self.sərbəstdir:
            self.x.xəta(
                "ALQ-T006", "Bu tipdə belə üzv yoxdur", yer,
                f"`{obyekt.mətn()}` tipində `{ad}` yoxdur",
                *self._üzv_təklifi(ad, cədvəl))
        return T.NAMƏLUM

    def _üzv_təklifi(self, ad: str, cədvəl: dict) -> list[str]:
        from .elifba import latınla
        for n in cədvəl:
            if latınla(n) == ad and n != ad:
                return [f"`{n}` demək istəyirdiniz? ASCII çevrilməsi "
                        "yalnız AÇAR SÖZLƏRƏ aiddir, üzv adlarına yox"]
        yaxın = [n for n in cədvəl if n.startswith(ad[:3])][:4]
        return [f"bəlkə: {', '.join(yaxın)}"] if yaxın else []

    def _metod_cədvəli(self, t: T.Tip) -> dict[str, T.Tip] | None:
        if t == T.MƏTN or t == T.SİMVOL:
            return _mətn_metodları()
        if isinstance(t, T.Siyahı):
            return _siyahı_metodları(t.element)
        if isinstance(t, T.Lüğət):
            return _lüğət_metodları(t.açar, t.dəyər)
        if isinstance(t, T.Dəst):
            return _dəst_metodları(t.element)
        if t in (T.TAM, T.ONLUQ):
            return _ədəd_metodları(t)
        if t == T.MƏNTİQ:
            return {"mətnƏt": F(qaytarır=T.MƏTN),
                    "tamƏt": F(qaytarır=T.TAM)}
        if t == T.ELEMENT:
            return _element_metodları()
        if isinstance(t, T.Generator):
            return _generator_metodları(t.element)
        if isinstance(t, T.Gələcək):
            return _gələcək_metodları(t.nəticə)
        if isinstance(t, T.Kortej):
            return {"uzunluq": F(qaytarır=T.TAM),
                    "siyahıyaÇevir": F(qaytarır=T.Siyahı()),
                    "mətnƏt": F(qaytarır=T.MƏTN),
                    "ehtiva": F(T.İSTƏNİLƏN, qaytarır=T.MƏNTİQ)}
        if t == T.DİAPAZON:
            return {"siyahıyaÇevir": F(qaytarır=T.Siyahı(T.TAM)),
                    "uzunluq": F(qaytarır=T.TAM),
                    "ehtiva": F(T.TAM, qaytarır=T.MƏNTİQ),
                    "mətnƏt": F(qaytarır=T.MƏTN),
                    "çevir": F(T.İSTƏNİLƏN, qaytarır=T.Siyahı()),
                    "filtr": F(T.İSTƏNİLƏN, qaytarır=T.Siyahı(T.TAM)),
                    "cəm": F(qaytarır=T.TAM)}
        if t == T.BAYT:
            return {"uzunluq": F(qaytarır=T.TAM),
                    "mətnƏt": F(qaytarır=T.MƏTN),
                    "siyahıyaÇevir": F(qaytarır=T.Siyahı(T.TAM)),
                    "base64Kodla": F(qaytarır=T.MƏTN)}
        if t == T.Sadə("ləğvNişanı"):
            return _ləğv_metodları()
        if t == SERVER:
            return _server_metodları()
        if t == SORĞU:
            return _sorğu_metodları()
        if t == CAVAB:
            return _cavab_metodları()
        if t == QRUP:
            return _marşrut_metodları(QRUP)
        if t == SESSİYA:
            return {
                "al": F(T.MƏTN, T.İSTƏNİLƏN, qaytarır=T.İSTƏNİLƏN,
                        standart=1),
                "qoy": F(T.MƏTN, T.İSTƏNİLƏN, qaytarır=T.HEÇ),
                "sil": F(T.MƏTN, qaytarır=T.İSTƏNİLƏN),
                "təmizlə": F(qaytarır=T.HEÇ),
                "ehtiva": F(T.MƏTN, qaytarır=T.MƏNTİQ),
            }
        if t == PƏNCƏRƏ:
            return _pəncərə_metodları()
        if t == SÜRÜCÜ:
            return _sürücü_metodları()
        if t == MÜŞTƏRİ:
            return _müştəri_metodları()
        if isinstance(t, T.Sadə):
            from . import modullar
            return modullar.obyekt_metodları(t.ad)
        return None

    def _e_çağırış(self, e: A.Çağırış, ə: Əhatə) -> T.Tip:
        funksiya = self._ifadə(e.funksiya, ə)
        if isinstance(funksiya, T.FunksiyaTipi) and \
                T.generiklidir(funksiya):
            return self._generik_çağırış(e, funksiya, ə)
        arqumentlər = [(a, self._ifadə(a.dəyər, ə)) for a in e.arqumentlər]

        # `üst(...)` — BAZA QURUCUSUNUN çağırışıdır, nümunə yaratma deyil.
        # Ona görə mücərrədlik yoxlaması tətbiq olunmur.
        if isinstance(e.funksiya, A.Üst):
            if isinstance(funksiya, T.SinifTipi):
                qurucu = funksiya.quruculər.get("")
                if isinstance(qurucu, T.FunksiyaTipi):
                    self._arqumentləri_yoxla(qurucu, arqumentlər, e,
                                             f"üst({funksiya.ad})")
            return T.HEÇ

        if isinstance(funksiya, T.SinifTipi):
            return self._qurucu_çağırışı(funksiya, arqumentlər, e)

        if isinstance(funksiya, T.ModulTipi):
            if not funksiya.çağırıla_bilir and not self.sərbəstdir:
                self.x.xəta(
                    "ALQ-T008", "Modul çağırıla bilməz", e.yer,
                    f"`{funksiya.ad}` moduldur",
                    f"üzvünü çağırın: `{funksiya.ad}.funksiya()`")
            return T.NAMƏLUM

        if not isinstance(funksiya, T.FunksiyaTipi):
            if not T.naməlumdur(funksiya) and not self.sərbəstdir:
                self.x.xəta(
                    "ALQ-T008", "Bu dəyər çağırıla bilməz", e.yer,
                    f"`{funksiya.mətn()}` funksiya deyil")
            return T.NAMƏLUM

        self._arqumentləri_yoxla(funksiya, arqumentlər, e,
                                 self._çağırış_adı(e))
        return self._nəticəni_dəqiqləşdir(e, funksiya.qaytarma,
                                          arqumentlər)

    def _generik_çağırış(self, e: A.Çağırış, imza: T.FunksiyaTipi,
                         ə: Əhatə) -> T.Tip:
        """
        `funksiya ilk[T](s: siyahı[T]) -> T?` çağırışı: generiklər
        arqumentlərdən çıxarılır (əvvəlcə adi arqumentlər, sonra
        lambdalar — lambdanın tipsiz parametrləri artıq məlum `T`-ni
        alır), ziddiyyət ALQ-T004 verir, nəticə dəqiq tipdir.
        """
        mövqeli = [p for p in imza.parametrlər if not p.yalnız_adlı]
        x: dict[str, T.Tip] = {}
        tiplər: dict[int, T.Tip] = {}

        def parametr(i: int, a) -> T.Parametr | None:
            if a.ad:
                return next((p for p in imza.parametrlər if p.ad == a.ad),
                            None)
            return mövqeli[i] if i < len(mövqeli) else (
                mövqeli[-1] if mövqeli and mövqeli[-1].variadic else None)

        sıra = list(enumerate(e.arqumentlər))
        # Lambdalar sonra: onların parametr tipləri digər arqumentlərdən
        sıra.sort(key=lambda c: isinstance(c[1].dəyər, A.Lambda))
        mövqe_sayı = {id(a): i for i, a in enumerate(
            [a for a in e.arqumentlər if not a.ad and not a.yayma])}
        for _, a in sıra:
            p = parametr(mövqe_sayı.get(id(a), -1), a) \
                if not a.yayma else None
            if isinstance(a.dəyər, A.Lambda) and p is not None and \
                    isinstance(T.açılmış(p.tip), T.FunksiyaTipi):
                gözlənilən = T.yerləşdir(T.açılmış(p.tip), x)
                tip = self._e_lambda(a.dəyər, ə, gözlənilən)
            else:
                tip = self._ifadə(a.dəyər, ə)
            tiplər[id(a)] = tip
            if p is None:
                continue
            ziddiyyət = T.uyğunlaşdır(p.tip, tip, x)
            if ziddiyyət and not self.sərbəstdir:
                self.x.xəta(
                    "ALQ-T004", "Generik tip ziddiyyəti",
                    getattr(a.dəyər, "yer", e.yer),
                    f"`{ziddiyyət}` əvvəl `{x[ziddiyyət].mətn()}` "
                    f"kimi təyin olunub, bu arqument `{tip.mətn()}`-dir",
                    f"`{self._çağırış_adı(e)}` bütün `{ziddiyyət}` "
                    "yerlərində eyni tipi gözləyir")
                return T.NAMƏLUM
        konkret = T.yerləşdir(imza, x)
        arqumentlər = [(a, tiplər[id(a)]) for a in e.arqumentlər]
        self._arqumentləri_yoxla(konkret, arqumentlər, e,
                                 self._çağırış_adı(e))
        nəticə = konkret.qaytarma
        # Çıxarılmayan generik — nəticə naməlumdur (yalan xəta verməsin)
        if T.generiklidir(nəticə):
            nəticə = T.yerləşdir(nəticə, _NAMƏLUMLAR(nəticə))
        return nəticə

    @staticmethod
    def _nəticəni_dəqiqləşdir(e: A.Çağırış, nəticə: T.Tip,
                              arqumentlər: list) -> T.Tip:
        """
        Bəzi funksiyaların nəticəsi arqument sayından asılıdır:

            l.al("a")        → dəyər?      (tapılmaya bilər)
            l.al("a", 0)     → dəyər       (standart dəyər var)

        İmza sistemi bunu ifadə edə bilmir, ona görə burada
        dəqiqləşdirilir.
        """
        if not isinstance(e.funksiya, A.Üzv):
            return nəticə
        STANDARTLI = {"al", "mühit", "tap"}
        if (e.funksiya.ad in ("al", "mühit")
                and len(arqumentlər) >= 2):
            return T.açılmış(nəticə)
        return nəticə

    @staticmethod
    def _çağırış_adı(e: A.Çağırış) -> str:
        f = e.funksiya
        if isinstance(f, A.Ad):
            return f.ad
        if isinstance(f, A.Üzv):
            return f.ad
        return "funksiya"

    def _arqumentləri_yoxla(self, imza: T.FunksiyaTipi, arqumentlər: list,
                            e: Any, ad: str) -> None:
        mövqeli = [(a, t) for a, t in arqumentlər
                   if a.ad is None and not a.yayma]
        yayma_var = any(a.yayma for a, _ in arqumentlər)
        adlı = {a.ad: t for a, t in arqumentlər if a.ad}

        minimum = imza.minimum_arqument
        maksimum = imza.maksimum_arqument

        if not yayma_var:
            verilən = len(mövqeli) + len(adlı)
            if verilən < minimum:
                self.x.xəta(
                    "ALQ-T003", "Arqument sayı uyğun deyil",
                    getattr(e, "yer", None),
                    f"`{ad}` ən azı {minimum} arqument gözləyir, "
                    f"{verilən} verilib")
                return
            if maksimum is not None and len(mövqeli) > maksimum:
                self.x.xəta(
                    "ALQ-T003", "Arqument sayı uyğun deyil",
                    getattr(e, "yer", None),
                    f"`{ad}` ən çox {maksimum} mövqeli arqument qəbul "
                    f"edir, {len(mövqeli)} verilib")
                return

        mövqeli_parametrlər = [p for p in imza.parametrlər
                               if not p.yalnız_adlı]
        for i, (a, tip) in enumerate(mövqeli):
            if i >= len(mövqeli_parametrlər):
                break
            p = mövqeli_parametrlər[i]
            gözlənilən = T.Siyahı(p.tip) if p.variadic else p.tip
            if p.variadic:
                gözlənilən = p.tip
            if T.naməlumdur(p.tip):
                continue
            if not T.uyğundur(tip, gözlənilən):
                self.x.xəta(
                    "ALQ-T004", "Arqument tipi uyğun deyil",
                    getattr(a.dəyər, "yer", getattr(e, "yer", None)),
                    f"{i + 1}-ci arqument: `{tip.mətn()}` verilib, "
                    f"`{gözlənilən.mətn()}` gözlənilir")

        parametr_adları = {p.ad for p in imza.parametrlər}
        for a_adı, tip in adlı.items():
            uyğun = next((p for p in imza.parametrlər if p.ad == a_adı),
                         None)
            if uyğun is None:
                continue
            if not T.naməlumdur(uyğun.tip) and not T.uyğundur(tip,
                                                              uyğun.tip):
                self.x.xəta(
                    "ALQ-T004", "Arqument tipi uyğun deyil",
                    getattr(e, "yer", None),
                    f"`{a_adı}`: `{tip.mətn()}` verilib, "
                    f"`{uyğun.tip.mətn()}` gözlənilir")

    def _qurucu_çağırışı(self, s: T.SinifTipi, arqumentlər: list,
                         e: Any) -> T.Tip:
        if s.mücərrəd and not self.sərbəstdir:
            self.x.xəta(
                "ALQ-T052", "Mücərrəd sinifdən obyekt yaradıla bilməz",
                getattr(e, "yer", None),
                f"`{s.ad}` mücərrəddir")
        qurucu = s.quruculər.get("")
        if isinstance(qurucu, T.FunksiyaTipi):
            self._arqumentləri_yoxla(qurucu, arqumentlər, e, s.ad)
        return s

    def _e_yeni(self, e: A.Yeni, ə: Əhatə) -> T.Tip:
        tip = self._tip(e.tip, ə)
        arqumentlər = [(a, self._ifadə(a.dəyər, ə)) for a in e.arqumentlər]
        if isinstance(tip, T.SinifTipi):
            if e.qurucu:
                qurucu = tip.quruculər.get(e.qurucu)
                if qurucu is None and not self.sərbəstdir:
                    self.x.xəta(
                        "ALQ-T006", "Adlı qurucu tapılmadı", e.yer,
                        f"`{tip.ad}` sinfində `{e.qurucu}` qurucusu yoxdur")
                elif isinstance(qurucu, T.FunksiyaTipi):
                    self._arqumentləri_yoxla(qurucu, arqumentlər, e,
                                             f"{tip.ad}.{e.qurucu}")
                return tip
            return self._qurucu_çağırışı(tip, arqumentlər, e)
        return tip

    def _e_indeks(self, e: A.İndeks, ə: Əhatə) -> T.Tip:
        obyekt = T.açılmış(self._ifadə(e.obyekt, ə))
        indeks = self._ifadə(e.indeks, ə)

        if not T.naməlumdur(obyekt) and not T.indekslənə_bilir(obyekt):
            self.x.xəta(
                "ALQ-T009", "Bu tip indekslənə bilməz", e.yer,
                f"`{obyekt.mətn()}` indekslənmir")
            return T.NAMƏLUM

        gözlənilən = T.indeks_açarı(obyekt)
        if (not T.naməlumdur(gözlənilən) and not T.naməlumdur(indeks)
                and not T.uyğundur(indeks, gözlənilən)):
            self.x.xəta(
                "ALQ-T009", "İndeks tipi uyğun deyil",
                getattr(e.indeks, "yer", e.yer),
                f"`{gözlənilən.mətn()}` gözlənilir, "
                f"`{indeks.mətn()}` verilib")
        # `kortej[tam, mətn]` və sabit indeks `c[0]` → dəqiq element
        if isinstance(obyekt, T.Kortej) and obyekt.elementlər and \
                isinstance(e.indeks, A.Literal) and \
                isinstance(e.indeks.dəyər, int) and \
                not isinstance(e.indeks.dəyər, bool):
            i = e.indeks.dəyər
            n = len(obyekt.elementlər)
            if -n <= i < n:
                return obyekt.elementlər[i]
            self.x.xəta("ALQ-T009", "Kortej indeksi hüdud xaricindədir",
                        e.yer, f"{n} elementli kortejdə `{i}` indeksi yoxdur")
            return T.NAMƏLUM
        return T.indeks_nəticəsi(obyekt)

    def _e_dilim(self, e: A.Dilim, ə: Əhatə) -> T.Tip:
        obyekt = T.açılmış(self._ifadə(e.obyekt, ə))
        for hissə in (e.başlanğıc, e.son):
            if hissə is None:
                continue
            tip = self._ifadə(hissə, ə)
            if not T.naməlumdur(tip) and tip != T.TAM:
                self.x.xəta("ALQ-T009",
                            "Dilim hədləri tam ədəd olmalıdır",
                            getattr(hissə, "yer", e.yer),
                            f"`{tip.mətn()}` gəlib")
        if not T.naməlumdur(obyekt) and not isinstance(
                obyekt, (T.Siyahı, T.Kortej)) and obyekt not in (T.MƏTN,
                                                                 T.BAYT):
            self.x.xəta("ALQ-T009", "Bu tip dilimlənə bilməz", e.yer,
                        f"`{obyekt.mətn()}` dilimlənmir")
        return obyekt

    def _e_məcburi_açma(self, e: A.MəcburiAçma, ə: Əhatə) -> T.Tip:
        tip = self._ifadə(e.ifadə, ə)
        if not T.ixtiyaridir(tip) and not T.naməlumdur(tip):
            self.x.xəbərdarlıq(
                "ALQ-T015", "`!` ixtiyari olmayan dəyərdə", e.yer,
                f"`{tip.mətn()}` heç vaxt boş olmur")
        return T.açılmış(tip)

    def _e_yayma(self, e: A.Yayma, ə: Əhatə) -> T.Tip:
        return T.açılmış(self._ifadə(e.ifadə, ə))

    def _e_gözlə(self, e: A.Gözlə, ə: Əhatə) -> T.Tip:
        tip = self._ifadə(e.ifadə, ə)
        f = ə.funksiya_əhatəsi()
        if f is not None and not f.asinxron and not self.sərbəstdir:
            self.x.xəta(
                "ALQ-P013", "`gözlə` asinxron olmayan funksiyada", e.yer,
                "funksiyanı `asinxron funksiya` kimi elan edin")
        if isinstance(tip, T.Gələcək):
            return tip.nəticə
        if isinstance(tip, T.Siyahı) and isinstance(tip.element,
                                                    T.Gələcək):
            return T.Siyahı(tip.element.nəticə)
        if isinstance(tip, T.Kortej):
            return T.Kortej(tuple(
                x.nəticə if isinstance(x, T.Gələcək) else x
                for x in tip.elementlər))
        return tip

    def _e_çevirmə(self, e: A.Çevirmə, ə: Əhatə) -> T.Tip:
        mənbə = self._ifadə(e.ifadə, ə)
        hədəf = self._tip(e.tip, ə)
        if (not T.naməlumdur(mənbə) and not T.naməlumdur(hədəf)
                and not self.sərbəstdir
                and not self._çevrilə_bilir(mənbə, hədəf)):
            self.x.xəta(
                "ALQ-T014", "Çevrilmə mümkün deyil", e.yer,
                f"`{mənbə.mətn()}` → `{hədəf.mətn()}`",
                "icazəli: tam ↔ onluq ↔ mətn, istənilən tip → mətn")
        return T.ixtiyari(hədəf) if e.təhlükəsiz else hədəf

    @staticmethod
    def _çevrilə_bilir(mənbə: T.Tip, hədəf: T.Tip) -> bool:
        if hədəf == T.MƏTN:
            return True
        if T.uyğundur(mənbə, hədəf):
            return True
        sadələr = (T.TAM, T.ONLUQ, T.MƏTN, T.MƏNTİQ, T.SİMVOL)
        if mənbə in sadələr and hədəf in sadələr:
            return True
        if isinstance(hədəf, (T.Siyahı, T.Dəst)):
            return T.iterasiya_oluna_bilir(mənbə)
        return False

    def _e_tip_yoxlama(self, e: A.TipYoxlama, ə: Əhatə) -> T.Tip:
        self._ifadə(e.ifadə, ə)
        self._tip(e.tip, ə)
        return T.MƏNTİQ

    def _e_üzvlük(self, e: A.Üzvlük, ə: Əhatə) -> T.Tip:
        element = self._ifadə(e.element, ə)
        kolleksiya = self._ifadə(e.kolleksiya, ə)
        if not T.naməlumdur(kolleksiya):
            if not (T.iterasiya_oluna_bilir(kolleksiya)
                    or kolleksiya == T.MƏTN):
                self.x.xəta(
                    "ALQ-T008", "`içindədir` bu tipə tətbiq edilmir",
                    e.yer, f"`{kolleksiya.mətn()}` kolleksiya deyil")
            else:
                gözlənilən = (kolleksiya.açar
                              if isinstance(kolleksiya, T.Lüğət)
                              else T.iterasiya_elementi(kolleksiya))
                if (not T.naməlumdur(gözlənilən)
                        and not T.naməlumdur(element)
                        and not T.uyğundur(element, gözlənilən)
                        and kolleksiya != T.MƏTN):
                    self.x.xəbərdarlıq(
                        "ALQ-T015", "`içindədir` tipləri uyğun gəlmir",
                        e.yer,
                        f"`{element.mətn()}` `{kolleksiya.mətn()}` "
                        "daxilində heç vaxt tapılmaz")
        return T.MƏNTİQ

    def _e_boş_yoxlama(self, e: A.BoşYoxlama, ə: Əhatə) -> T.Tip:
        tip = self._ifadə(e.ifadə, ə)
        if (not T.ixtiyaridir(tip) and not T.naməlumdur(tip)
                and tip != T.HEÇ):
            self.x.xəbərdarlıq(
                "ALQ-T015", "Boş yoxlaması lazımsızdır", e.yer,
                f"`{tip.mətn()}` heç vaxt boş olmur")
        return T.MƏNTİQ

    def _e_boru(self, e: A.Boru, ə: Əhatə) -> T.Tip:
        dəyər = self._ifadə(e.dəyər, ə)
        funksiya = self._ifadə(e.funksiya, ə)
        if isinstance(funksiya, T.FunksiyaTipi):
            if funksiya.parametrlər:
                p = funksiya.parametrlər[0]
                if (not T.naməlumdur(p.tip)
                        and not T.uyğundur(dəyər, p.tip)):
                    self.x.xəta(
                        "ALQ-T004", "Boru arqumenti uyğun deyil", e.yer,
                        f"`{dəyər.mətn()}` → `{p.tip.mətn()}`")
            return funksiya.qaytarma
        return T.NAMƏLUM

    def _e_diapazon(self, e: A.Diapazon, ə: Əhatə) -> T.Tip:
        for hissə in (e.başlanğıc, e.son, e.addım):
            if hissə is None:
                continue
            tip = self._ifadə(hissə, ə)
            if (not T.naməlumdur(tip) and tip != T.TAM
                    and tip != T.SİMVOL):
                self.x.xəta(
                    "ALQ-T001", "Diapazon hədləri tam ədəd olmalıdır",
                    getattr(hissə, "yer", e.yer),
                    f"`{tip.mətn()}` gəlib")
        return T.DİAPAZON

    # ── Kolleksiyalar ─────────────────────────────────────────────────

    def _e_siyahı(self, e: A.SiyahıLiteralı, ə: Əhatə) -> T.Tip:
        element: T.Tip = T.NAMƏLUM
        yaymalar = e.yaymalar or [False] * len(e.elementlər)
        for x, yayma in zip(e.elementlər, yaymalar):
            tip = self._ifadə(x, ə)
            element = T.birləşdir(
                element, T.iterasiya_elementi(tip) if yayma else tip)
        return T.Siyahı(element)

    def _e_lüğət(self, e: A.LüğətLiteralı, ə: Əhatə) -> T.Tip:
        açar: T.Tip = T.NAMƏLUM
        dəyər: T.Tip = T.NAMƏLUM
        for a, d in zip(e.açarlar, e.dəyərlər):
            d_tipi = self._ifadə(d, ə)
            if a is None:
                if isinstance(d_tipi, T.Lüğət):
                    açar = T.birləşdir(açar, d_tipi.açar)
                    dəyər = T.birləşdir(dəyər, d_tipi.dəyər)
                continue
            açar = T.birləşdir(açar, self._ifadə(a, ə))
            dəyər = T.birləşdir(dəyər, d_tipi)
        return T.Lüğət(açar, dəyər)

    def _e_dəst(self, e: A.DəstLiteralı, ə: Əhatə) -> T.Tip:
        element: T.Tip = T.NAMƏLUM
        for x in e.elementlər:
            element = T.birləşdir(element, self._ifadə(x, ə))
        return T.Dəst(element)

    def _e_kortej(self, e: A.KortejLiteralı, ə: Əhatə) -> T.Tip:
        return T.Kortej(tuple(self._ifadə(x, ə) for x in e.elementlər))

    def _e_qurma(self, e: A.Qurma, ə: Əhatə) -> T.Tip:
        mənbə = self._ifadə(e.mənbə, ə)
        if not T.naməlumdur(mənbə) and not T.iterasiya_oluna_bilir(mənbə):
            self.x.xəta(
                "ALQ-T009", "Qurmada iterasiya mümkün deyil",
                getattr(e.mənbə, "yer", e.yer),
                f"`{mənbə.mətn()}` iterasiya olunmur")
        alt = ə.alt()
        self._bağla(e.bağlama, T.iterasiya_elementi(mənbə), alt, False)
        if e.şərt is not None:
            self._şərt_yoxla(e.şərt, alt)
        nəticə = self._ifadə(e.ifadə, alt)
        if e.növ == "lüğət":
            return T.Lüğət(nəticə, self._ifadə(e.dəyər_ifadəsi, alt))
        if e.növ == "dəst":
            return T.Dəst(nəticə)
        if e.növ == "generator":
            return T.Generator(nəticə)
        return T.Siyahı(nəticə)

    # ── Blok şəklində ifadələr ────────────────────────────────────────

    def _e_şərt_ifadəsi(self, e: A.ŞərtIfadəsi, ə: Əhatə) -> T.Tip:
        nəticə: T.Tip = T.NAMƏLUM
        for şərt, dəyər in e.budaqlar:
            self._şərt_yoxla(şərt, ə)
            alt = ə.alt()
            self._daralmanı_tətbiq(şərt, True, alt)
            nəticə = T.birləşdir(nəticə, self._ifadə(dəyər, alt))
        if e.yoxsa is not None:
            nəticə = T.birləşdir(nəticə, self._ifadə(e.yoxsa, ə))
        else:
            nəticə = T.ixtiyari(nəticə)
        return nəticə

    def _e_blok_ifadəsi(self, e: A.BlokIfadəsi, ə: Əhatə) -> T.Tip:
        alt = ə.alt()
        nəticə: T.Tip = T.NAMƏLUM
        for c in e.gövdə:
            if isinstance(c, A.Ver) and c.dəyər is not None:
                nəticə = T.birləşdir(nəticə, self._ifadə(c.dəyər, alt))
            else:
                self._cümlə(c, alt)
        return nəticə

    def _e_lambda(self, e: A.Lambda, ə: Əhatə,
                  gözlənilən: T.FunksiyaTipi | None = None) -> T.Tip:
        """`gözlənilən` — kontekstdən gələn imza: tipsiz parametrlər
        onun tiplərini alır (`xəritələ(s, (x) => x * 2)`)."""
        kontekst = list(gözlənilən.parametrlər) if gözlənilən else []

        def p_tipi(i: int, p) -> T.Tip:
            if p.tip:
                return self._tip(p.tip, ə)
            if i < len(kontekst) and not T.generiklidir(kontekst[i].tip):
                return kontekst[i].tip
            return T.NAMƏLUM
        parametrlər = tuple(
            T.Parametr(p.ad, p_tipi(i, p),
                       p.standart is not None,
                       p.variadic or p.adlı_variadic, p.yalnız_adlı)
            for i, p in enumerate(e.parametrlər))
        qaytarma = self._tip(e.qaytarma_tipi, ə) if e.qaytarma_tipi \
            else T.NAMƏLUM

        alt = ə.alt("funksiya", qaytarma)
        alt.asinxron = e.asinxron
        alt.generator = e.generator
        for p, tp in zip(e.parametrlər, parametrlər):
            alt.elan(Bağlama(p.ad, tp.tip, False, p.yer, True,
                             "parametr"))

        if isinstance(e.gövdə, list):
            self._blok(e.gövdə, alt)
        else:
            nəticə = self._ifadə(e.gövdə, alt)
            if T.naməlumdur(qaytarma):
                qaytarma = nəticə

        imza = T.FunksiyaTipi(parametrlər, qaytarma, e.asinxron,
                              e.generator)
        if e.asinxron:
            return T.FunksiyaTipi(parametrlər, T.Gələcək(qaytarma),
                                  True, False)
        return imza

    # ── JSX ───────────────────────────────────────────────────────────

    def _e_jsx(self, e: A.JSXElement, ə: Əhatə) -> T.Tip:
        for a in e.atributlar:
            if a.dəyər is not None:
                self._ifadə(a.dəyər, ə)
        for u in e.uşaqlar:
            if not isinstance(u, A.JSXMətn):
                self._ifadə(u, ə)

        if e.komponentdir:
            b = ə.tap(e.ad.split(".")[0])
            if b is None:
                self.x.xəta(
                    "ALQ-T022", "Komponent tapılmadı", e.yer,
                    f"`<{e.ad} />` adlı sinif və ya funksiya yoxdur")
            else:
                b.istifadə_olunub = True
                if isinstance(b.tip, T.SinifTipi):
                    if b.tip.üzv("göstər") is None and not self.sərbəstdir:
                        self.x.xəta(
                            "ALQ-T053",
                            "Komponentdə `göstər()` metodu yoxdur",
                            e.yer, f"`{b.tip.ad}` komponent ola bilməz")
        return T.ELEMENT

    def _e_jsx_parça(self, e: A.JSXParça, ə: Əhatə) -> T.Tip:
        for u in e.uşaqlar:
            if not isinstance(u, A.JSXMətn):
                self._ifadə(u, ə)
        return T.ELEMENT

    # ═══════════════════════════════════════════════════════════════════
    #  İstifadəsiz adlar
    # ═══════════════════════════════════════════════════════════════════

    def _istifadəsizləri_bildir(self, ə: Əhatə) -> None:
        if self.sərbəstdir:
            return
        for b in ə.adlar.values():
            if (b.istifadə_olunub or b.ad.startswith("_")
                    or b.elan_növü in ("daxili", "global", "idxal",
                                       "sinif", "sadalama", "tip",
                                       "modul")):
                continue
            if b.elan_növü == "funksiya" and ə.növ == "qlobal":
                continue
            növ = {"parametr": "parametr"}.get(b.elan_növü, "dəyişən")
            self.x.xəbərdarlıq(
                "ALQ-T024", f"İstifadə olunmayan {növ}", b.yer,
                f"`{b.ad}` heç yerdə işlənmir",
                "qəsdəndirsə `_` ilə başlayan ad verin")


# ═══════════════════════════════════════════════════════════════════════
#  Operator → metod
# ═══════════════════════════════════════════════════════════════════════

_OPERATOR_METODLARI = {
    "+": "topla", "-": "çıx", "*": "vur", "/": "böl",
    "%": "qalıq", "**": "qüvvət",
}


# ═══════════════════════════════════════════════════════════════════════
#  Dispetçer
# ═══════════════════════════════════════════════════════════════════════

_CÜMLƏLƏR: dict[type, Any] = {
    A.İfadəCümləsi: TipYoxlayıcı._c_ifadə,
    A.DəyişənElanı: TipYoxlayıcı._c_dəyişən,
    A.FunksiyaElanı: TipYoxlayıcı._c_funksiya,
    A.SinifElanı: TipYoxlayıcı._c_sinif,
    A.InterfeysElanı: TipYoxlayıcı._c_interfeys,
    A.SadalamaElanı: TipYoxlayıcı._c_sadalama,
    A.QarışıqElanı: TipYoxlayıcı._c_qarışıq,
    A.Genişlətmə: TipYoxlayıcı._c_genişlətmə,
    A.ModulElanı: TipYoxlayıcı._c_modul,
    A.TipAliası: TipYoxlayıcı._c_tip_aliası,
    A.İdxal: TipYoxlayıcı._c_idxal,
    A.Şərt: TipYoxlayıcı._c_şərt,
    A.Varsa: TipYoxlayıcı._c_varsa,
    A.Yoxdursa: TipYoxlayıcı._c_yoxdursa,
    A.Seç: TipYoxlayıcı._c_seç,
    A.NəQədərKi: TipYoxlayıcı._c_nə_qədər_ki,
    A.Həmişə: TipYoxlayıcı._c_həmişə,
    A.Təkrarla: TipYoxlayıcı._c_təkrarla,
    A.TəkrarlaNəQədər: TipYoxlayıcı._c_təkrarla_nə_qədər,
    A.Hər: TipYoxlayıcı._c_hər,
    A.Dayan: TipYoxlayıcı._c_dayan,
    A.DavamEt: TipYoxlayıcı._c_davam,
    A.Qaytar: TipYoxlayıcı._c_qaytar,
    A.Ver: TipYoxlayıcı._c_ver,
    A.At: TipYoxlayıcı._c_at,
    A.Cəhd: TipYoxlayıcı._c_cəhd,
    A.İddia: TipYoxlayıcı._c_iddia,
    A.Təmin: TipYoxlayıcı._c_təmin,
    A.Gecikdir: TipYoxlayıcı._c_gecikdir,
    A.İstifadə: TipYoxlayıcı._c_istifadə,
    A.Global: TipYoxlayıcı._c_global,
    A.Artırma: TipYoxlayıcı._c_artırma,
    A.Keç: TipYoxlayıcı._c_keç,
    A.DayanNöqtəsi: TipYoxlayıcı._c_keç,
    A.İxracSiyahısı: TipYoxlayıcı._c_keç,
    A.Başlanğıc: TipYoxlayıcı._c_blok_qovşağı,
    A.Bitiş: TipYoxlayıcı._c_blok_qovşağı,
    A.DağıdıcıElanı: TipYoxlayıcı._c_keç,
}

_İFADƏLƏR: dict[type, Any] = {
    A.Literal: TipYoxlayıcı._e_literal,
    A.ŞablonMətn: TipYoxlayıcı._e_şablon,
    A.Ad: TipYoxlayıcı._e_ad,
    A.Özü: TipYoxlayıcı._e_özü,
    A.Üst: TipYoxlayıcı._e_üst,
    A.İkili: TipYoxlayıcı._e_ikili,
    A.TəkOperand: TipYoxlayıcı._e_tək,
    A.Mənimsətmə: TipYoxlayıcı._e_mənimsətmə,
    A.Üzv: TipYoxlayıcı._e_üzv,
    A.Çağırış: TipYoxlayıcı._e_çağırış,
    A.Yeni: TipYoxlayıcı._e_yeni,
    A.İndeks: TipYoxlayıcı._e_indeks,
    A.Dilim: TipYoxlayıcı._e_dilim,
    A.MəcburiAçma: TipYoxlayıcı._e_məcburi_açma,
    A.Yayma: TipYoxlayıcı._e_yayma,
    A.Gözlə: TipYoxlayıcı._e_gözlə,
    A.Çevirmə: TipYoxlayıcı._e_çevirmə,
    A.TipYoxlama: TipYoxlayıcı._e_tip_yoxlama,
    A.Üzvlük: TipYoxlayıcı._e_üzvlük,
    A.BoşYoxlama: TipYoxlayıcı._e_boş_yoxlama,
    A.Boru: TipYoxlayıcı._e_boru,
    A.Diapazon: TipYoxlayıcı._e_diapazon,
    A.SiyahıLiteralı: TipYoxlayıcı._e_siyahı,
    A.LüğətLiteralı: TipYoxlayıcı._e_lüğət,
    A.DəstLiteralı: TipYoxlayıcı._e_dəst,
    A.KortejLiteralı: TipYoxlayıcı._e_kortej,
    A.Qurma: TipYoxlayıcı._e_qurma,
    A.ŞərtIfadəsi: TipYoxlayıcı._e_şərt_ifadəsi,
    A.BlokIfadəsi: TipYoxlayıcı._e_blok_ifadəsi,
    A.Lambda: TipYoxlayıcı._e_lambda,
    A.JSXElement: TipYoxlayıcı._e_jsx,
    A.JSXParça: TipYoxlayıcı._e_jsx_parça,
}


# ═══════════════════════════════════════════════════════════════════════
#  Rahat funksiya
# ═══════════════════════════════════════════════════════════════════════

def tipləri_yoxla(ağac: A.Proqram, toplayıcı: XətaToplayıcı,
                  rejim: str = "normal") -> TipYoxlayıcı:
    y = TipYoxlayıcı(toplayıcı, rejim)
    y.yoxla(ağac)
    return y


def _NAMƏLUMLAR(t: T.Tip) -> dict[str, T.Tip]:
    """Tipdəki bütün generik adları → naməlum."""
    n: dict[str, T.Tip] = {}

    def gəz(x: T.Tip) -> None:
        if isinstance(x, T.Generik):
            n[x.ad] = T.NAMƏLUM
        for f in ("element", "nəticə", "açar", "dəyər", "qaytarma"):
            v = getattr(x, f, None)
            if isinstance(v, T.Tip):
                gəz(v)
        for v in getattr(x, "elementlər", ()) or ():
            gəz(v)
        for v in getattr(x, "variantlar", ()) or ():
            gəz(v)
        for p in getattr(x, "parametrlər", ()) or ():
            if isinstance(p, T.Parametr):
                gəz(p.tip)
    gəz(t)
    return n
