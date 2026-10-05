"""
Alqor — Azərbaycan əlifbası və `az-AZ` hərf qaydaları.

Bu modul dilin ən kritik hissəsidir: standart Unicode böyük/kiçik hərf
çevrilməsi Azərbaycan dili üçün YANLIŞ nəticə verir.

    Standart Unicode:   "ışıq".upper() → "IŞIK"   ✖
    Azərbaycan qaydası: böyüyə("ışıq") → "IŞIQ"   ✓

    Standart Unicode:   "i".upper() → "I"         ✖
    Azərbaycan qaydası: böyüyə("i")  → "İ"        ✓

    Standart Unicode:   "I".lower() → "i"         ✖
    Azərbaycan qaydası: kiçiyə("I")  → "ı"        ✓
"""

# ───────────────────────────────────────────────────────────────────────
#  Əlifba — rəsmi Azərbaycan sırası ilə, 32 hərf
#  Hər iki sətirdə hərflər eyni mövqedədir: KICIK[n] ↔ BOYUK[n]
#  Diqqət: 13-cü mövqe I/ı, 14-cü mövqe İ/i — bu, bütün problemin mənbəyidir.
# ───────────────────────────────────────────────────────────────────────

KICIK = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz"
BOYUK = "ABCÇDEƏFGĞHXIİJKQLMNOÖPRSŞTUÜVYZ"

assert len(KICIK) == len(BOYUK) == 32

# Mövqe cədvəlləri — O(1) axtarış üçün
_KICIK_MOVQE = {h: i for i, h in enumerate(KICIK)}
_BOYUK_MOVQE = {h: i for i, h in enumerate(BOYUK)}

# Çevrilmə cədvəlləri
_BOYUYE = {KICIK[i]: BOYUK[i] for i in range(32)}
_KICIYE = {BOYUK[i]: KICIK[i] for i in range(32)}

# Hərf dəstləri
HERFLER = frozenset(KICIK) | frozenset(BOYUK)
REQEMLER = frozenset("0123456789")

SAITLER = frozenset("aeəıioöuü") | frozenset("AEƏIİOÖUÜ")
SAMITLER = HERFLER - SAITLER

QALIN_SAITLER = frozenset("aıouAIOU")       # arxa saitlər
INCE_SAITLER = frozenset("eəiöüEƏİÖÜ")      # ön saitlər

# Unicode kod nöqtələri — sənədləşmə və diaqnostika üçün
KOD_NOQTELERI = {
    "ə": 0x0259, "Ə": 0x018F,
    "ı": 0x0131, "I": 0x0049,
    "i": 0x0069, "İ": 0x0130,
    "ö": 0x00F6, "Ö": 0x00D6,
    "ü": 0x00FC, "Ü": 0x00DC,
    "ç": 0x00E7, "Ç": 0x00C7,
    "ş": 0x015F, "Ş": 0x015E,
    "ğ": 0x011F, "Ğ": 0x011E,
}


# ───────────────────────────────────────────────────────────────────────
#  Hərf sinifləri
# ───────────────────────────────────────────────────────────────────────

def hərfdir(c: str) -> bool:
    """Azərbaycan əlifbasının hərfidirmi?"""
    return c in HERFLER


def rəqəmdir(c: str) -> bool:
    return c in REQEMLER


def kiçik_hərfdir(c: str) -> bool:
    return c in _KICIK_MOVQE


def böyük_hərfdir(c: str) -> bool:
    return c in _BOYUK_MOVQE


def saitdir(c: str) -> bool:
    return c in SAITLER


def samitdir(c: str) -> bool:
    return c in SAMITLER


def qalın_saitdir(c: str) -> bool:
    """Arxa sait: a, ı, o, u — ahəng qanunu üçün."""
    return c in QALIN_SAITLER


def incə_saitdir(c: str) -> bool:
    """Ön sait: e, ə, i, ö, ü — ahəng qanunu üçün."""
    return c in INCE_SAITLER


# ───────────────────────────────────────────────────────────────────────
#  Böyük / kiçik hərf çevrilməsi — az-AZ qaydaları
# ───────────────────────────────────────────────────────────────────────

def böyüyə(mətn: str) -> str:
    """
    Azərbaycan qaydası ilə böyük hərflərə çevirir.

        böyüyə("ışıq")  → "IŞIQ"
        böyüyə("i")     → "İ"
        böyüyə("imran") → "İMRAN"
    """
    return "".join(_BOYUYE.get(c, c.upper()) for c in mətn)


def kiçiyə(mətn: str) -> str:
    """
    Azərbaycan qaydası ilə kiçik hərflərə çevirir.

        kiçiyə("IŞIQ")  → "ışıq"
        kiçiyə("İ")     → "i"
        kiçiyə("I")     → "ı"
    """
    return "".join(_KICIYE.get(c, c.lower()) for c in mətn)


def baş_böyük(mətn: str) -> str:
    """İlk hərfi böyük, qalanı kiçik."""
    if not mətn:
        return mətn
    return böyüyə(mətn[0]) + kiçiyə(mətn[1:])


def hər_söz_böyük(mətn: str) -> str:
    """Hər sözün ilk hərfini böyüdür."""
    nəticə = []
    yeni_söz = True
    for c in mətn:
        if hərfdir(c):
            nəticə.append(böyüyə(c) if yeni_söz else kiçiyə(c))
            yeni_söz = False
        else:
            nəticə.append(c)
            yeni_söz = True
    return "".join(nəticə)


# ───────────────────────────────────────────────────────────────────────
#  Sıralama (collation) — az-AZ
#  Unicode-un öz sırası yanlışdır: "ə" hərfi Unicode-da "z"-dən sonra gəlir,
#  Azərbaycan əlifbasında isə "e" ilə "f" arasındadır.
# ───────────────────────────────────────────────────────────────────────

# Sinif nömrələri: hərf olmayanlar hərflərdən əvvəl sıralanır
_SINIF_DIGER = 0
_SINIF_HERF = 1


def sıralama_açarı(mətn: str):
    """
    `sorted(..., key=sıralama_açarı)` üçün açar.

    İki mərhələli müqayisə:
      1. Hərfin əlifbadaki mövqeyi (böyük/kiçik fərqi nəzərə alınmır)
      2. Bərabərlikdə kiçik hərf böyükdən əvvəl
    """
    əsas = []
    ikinci = []
    for c in mətn:
        if c in _KICIK_MOVQE:
            əsas.append((_SINIF_HERF, _KICIK_MOVQE[c]))
            ikinci.append(0)
        elif c in _BOYUK_MOVQE:
            əsas.append((_SINIF_HERF, _BOYUK_MOVQE[c]))
            ikinci.append(1)
        else:
            əsas.append((_SINIF_DIGER, ord(c)))
            ikinci.append(0)
    return (tuple(əsas), tuple(ikinci))


def müqayisə(a: str, b: str) -> int:
    """az-AZ sırası ilə müqayisə: -1, 0, 1."""
    ka, kb = sıralama_açarı(a), sıralama_açarı(b)
    return -1 if ka < kb else (1 if ka > kb else 0)


def sırala(sözlər):
    """Azərbaycan əlifba sırası ilə sıralayır."""
    return sorted(sözlər, key=sıralama_açarı)


# ───────────────────────────────────────────────────────────────────────
#  Latınlaşdırma — URL, fayl adı, ASCII açar sözü üçün
# ───────────────────────────────────────────────────────────────────────

LATIN_EVEZ = {
    "ə": "e", "Ə": "E",
    "ı": "i", "I": "I",
    "i": "i", "İ": "I",
    "ö": "o", "Ö": "O",
    "ü": "u", "Ü": "U",
    "ç": "c", "Ç": "C",
    "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G",
}


def latınla(mətn: str) -> str:
    """
    Azərbaycan hərflərini ASCII qarşılığı ilə əvəz edir.

        latınla("əgər")   → "eger"
        latınla("dəyişən") → "deyisen"

    DİQQƏT: bu çevrilmə yalnız AÇAR SÖZLƏR və URL/fayl adları üçündür.
    İdentifikatorlarda tətbiq olunmur — `yaş` və `yas` fərqli adlardır.
    """
    return "".join(LATIN_EVEZ.get(c, c) for c in mətn)


# ───────────────────────────────────────────────────────────────────────
#  İdentifikator qaydaları (Spesifikasiya § 1.5)
# ───────────────────────────────────────────────────────────────────────

def ad_başlanğıcı_ola_bilər(c: str) -> bool:
    """İdentifikatorun ilk simvolu ola bilərmi?"""
    return hərfdir(c) or c == "_"


def ad_davamı_ola_bilər(c: str) -> bool:
    """İdentifikatorun sonraki simvolu ola bilərmi?"""
    return hərfdir(c) or rəqəmdir(c) or c == "_"
