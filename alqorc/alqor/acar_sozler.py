"""
Alqor — Açar sözlər cədvəli.

Üç kateqoriya var:

  1. SƏRT açar sözlər  — qorunur, identifikator kimi işlədilə bilməz
  2. KONTEKSTLİ sözlər — lekser onları AD kimi buraxır, parser kontekstə
                         görə tanıyır (`oxu`, `yaz`, `vəziyyət`, `göstər` ...)
  3. ÇOX SÖZLÜ         — lekser onları BİR tokenə birləşdirir
                         (`nə qədər ki`, `və ya`, `boş deyil` ...)

ASCII əvəzləyiciləri avtomatik yaradılır: `əgər` → `eger`.
Bu yalnız AÇAR SÖZLƏRƏ aiddir; identifikatorlarda `yaş` ≠ `yas`.
"""

from __future__ import annotations
from .elifba import latınla

# ═══════════════════════════════════════════════════════════════════════
#  1. SƏRT AÇAR SÖZLƏR
# ═══════════════════════════════════════════════════════════════════════

ELAN = [
    "dəyişən", "sabit", "dəyişməz",
    "funksiya", "sinif", "struktur", "interfeys", "sadalama",
    "modul", "obyekt", "qarışıq", "tip",
    "qurucu", "silinsin", "metod", "xassə", "genişlət",
    "komponent", "mağaza",
]

MODIFIKATOR = [
    "açıq", "gizli", "qorunan", "statik", "mücərrəd",
    "son", "tənbəl", "global", "asinxron", "generator",
]

SERT = [
    "əgər", "onda", "yoxsa", "əks", "halda",
    "varsa", "yoxdursa",
    "seç", "hal", "digər", "hallarda", "keç",
]

DOVR = [
    "nə", "qədər", "ki", "həmişə",
    "təkrarla", "dəfə",
    "hər", "üçün", "içində", "addım",
    "dayan", "davam", "et",
]

AXIN = [
    "qaytar", "ver", "gözlə", "gecikdir", "istifadə", "blok",
]

XETA = [
    "cəhd", "tut", "nəhayət", "at", "iddia", "təmin", "bərpa",
]

OBYEKT = [
    "özü", "üst", "yeni", "miras", "tətbiq", "ilə", "əvəz",
]

MODUL = [
    "gətir", "ixrac", "kimi", "standart",
]
#  `başlanğıc` və `bitiş` QƏSDƏN burada yoxdur — onlar KONTEKSTLİDİR.
#  Səbəb: `dəyişən başlanğıc = vaxt.ölç()` Azərbaycan dilində tamamilə
#  normal koddur. Bu sözlər yalnız modul səviyyəsində, ardınca yeni
#  sətir gələndə blok açar sözü sayılır.

MENTIQ = [
    "və", "ya", "deyil", "içindədir", "tipidir", "boşdur",
]

LITERAL = [
    "doğru", "yanlış", "boş", "sonsuz", "ƏdədDeyil",
]

KOMEKCI = [
    "dayanNöqtəsi",
]

ACAR_SOZLER: frozenset[str] = frozenset(
    ELAN + MODIFIKATOR + SERT + DOVR + AXIN + XETA
    + OBYEKT + MODUL + MENTIQ + LITERAL + KOMEKCI
)


# ═══════════════════════════════════════════════════════════════════════
#  1b. TİP ADLARI — açar söz DEYİL, öncədən elan olunmuş identifikator
# ═══════════════════════════════════════════════════════════════════════
#
#  Niyə qorunmur? Çünki `mətn`, `tam`, `say`, `tip` Azərbaycan dilində
#  ən təbii sahə adlarıdır:
#
#      sinif Tapşırıq
#          qurucu(açıq xassə mətn: mətn)     ← sahə adı `mətn`, tipi `mətn`
#      son
#
#      funksiya sözləriSay(mətn: mətn) -> lüğət[mətn, tam]
#
#  Bunları açar söz etsək, yuxarıdaki tamamilə normal kod işləməzdi.
#  Go (`int`, `string`) və Rust (`i32`, `str`) da eyni yolu seçib:
#  tip adları prelüddə elan olunmuş adi identifikatorlardır.
#
#  Nəticə: istifadəçi `dəyişən mətn = "salam"` yazıb tip adını
#  kölgələyə bilər. `alqorlint` bunu xəbərdarlıq kimi bildirir.

TIP_ADLARI: frozenset[str] = frozenset([
    "tam", "onluq", "mətn", "məntiq", "simvol", "bayt",
    "siyahı", "lüğət", "dəst", "kortej", "funksiyaTipi",
    "istənilən", "heç",
])


# ═══════════════════════════════════════════════════════════════════════
#  2. KONTEKSTLİ SÖZLƏR — qorunmur
# ═══════════════════════════════════════════════════════════════════════
#  Bunlar yalnız müəyyən mövqedə açar söz kimi davranır. Lekser onları
#  adi identifikator kimi buraxır, parser özü tanıyır. Beləliklə
#  `yaz("salam")` funksiya çağırışı olaraq işləyir, amma
#  `xassə sahə: onluq  oxu ... son  yaz(d) ... son  son` da işləyir.

KONTEKSTLI: frozenset[str] = frozenset([
    "oxu", "yaz",                                  # xassə aksessorları
    "vəziyyət", "hesablanan", "əməl", "hadisə", "göstər",   # komponent
    "sınaq", "ölç", "sil", "panika", "eynidir",    # standart kitabxana
    "başlanğıc", "bitiş",                          # modul blokları
    "makro",                                       # makro elanı (§ 5.12)
    "aktyor",                                      # aktyor elanı (§ 9.12)
    "gözlənilir",                                  # gözlənti (§ 13.5)
    "tələb", "zəmanət",                            # müqavilələr (§ 5.13)
])


# ═══════════════════════════════════════════════════════════════════════
#  3. ÇOX SÖZLÜ AÇAR SÖZLƏR
# ═══════════════════════════════════════════════════════════════════════
#  Lekser bunları maksimal-udma (maximal munch) ilə BİR ACAR tokenə
#  birləşdirir. Sıra vacibdir: uzun olanlar əvvəl yoxlanılır.
#
#  Niyə lekserdə? Çünki bu söz ardıcıllıqlarının başqa mənası yoxdur,
#  və parserin işini xeyli sadələşdirir.

COX_SOZLU: list[tuple[str, ...]] = [
    ("nə", "qədər", "ki"),        # while
    ("digər", "hallarda"),        # default
    ("yoxsa", "əgər"),            # else if
    ("əks", "halda"),             # else (uzun forma)
    ("davam", "et"),              # continue
    ("cəhd", "et"),               # try
    ("ixrac", "et"),              # export
    ("əvəz", "et"),               # override
    ("və", "ya"),                 # or
    ("boş", "deyil"),             # is not null
]

# Kanonik formalar (boşluqla birləşdirilmiş)
COX_SOZLU_KANONIK: frozenset[str] = frozenset(
    " ".join(p) for p in COX_SOZLU
)

# İlk sözə görə indeks — lekser üçün sürətli axtarış
COX_SOZLU_INDEKS: dict[str, list[tuple[str, ...]]] = {}
for _p in COX_SOZLU:
    COX_SOZLU_INDEKS.setdefault(_p[0], []).append(_p)
for _k in COX_SOZLU_INDEKS:
    COX_SOZLU_INDEKS[_k].sort(key=len, reverse=True)


# ═══════════════════════════════════════════════════════════════════════
#  4. ALİASLAR
# ═══════════════════════════════════════════════════════════════════════

# Qısa formalar → kanonik forma
QISA_ALIAS: dict[str, str] = {
    "davam": "davam et",          # `davam` tək işlənərsə
    "əks halda": "yoxsa",         # ikisi də `else` deməkdir
}

# ASCII əvəzləyiciləri — avtomatik yaradılır
# `əgər` → `eger`,  `nə qədər ki` → `ne qeder ki`
def _ascii_cədvəli() -> dict[str, str]:
    cədvəl: dict[str, str] = {}
    hamısı = list(ACAR_SOZLER) + list(COX_SOZLU_KANONIK)
    for söz in hamısı:
        a = latınla(söz)
        if a != söz:
            if a in cədvəl and cədvəl[a] != söz:
                raise AssertionError(
                    f"ASCII toqquşması: '{a}' → '{cədvəl[a]}' və '{söz}'")
            cədvəl[a] = söz
    return cədvəl


ASCII_ALIAS: dict[str, str] = _ascii_cədvəli()

# ASCII çox sözlü formaların ilk sözləri (lekser birləşdirmə üçün)
ASCII_COX_SOZLU: dict[str, tuple[str, ...]] = {}
for _p in COX_SOZLU:
    _ap = tuple(latınla(s) for s in _p)
    if _ap != _p:
        ASCII_COX_SOZLU[" ".join(_ap)] = _p


# ═══════════════════════════════════════════════════════════════════════
#  5. SABİTLƏR — parserin istifadəsi üçün
# ═══════════════════════════════════════════════════════════════════════
#  Parser `t.acar == AS.EGER` yazır, `t.acar == "əgər"` deyil —
#  yazı səhvi kompilyasiya vaxtı tutulsun.

EGER = "əgər"
ONDA = "onda"
YOXSA = "yoxsa"
YOXSA_EGER = "yoxsa əgər"
EKS_HALDA = "əks halda"
SON = "son"
SEC = "seç"
HAL = "hal"
DIGER_HALLARDA = "digər hallarda"
KEC = "keç"
VARSA = "varsa"
YOXDURSA = "yoxdursa"

NE_QEDER_KI = "nə qədər ki"
HEMISE = "həmişə"
TEKRARLA = "təkrarla"
DEFE = "dəfə"
HER = "hər"
UCUN = "üçün"
ICINDE = "içində"
ADDIM = "addım"
DAYAN = "dayan"
DAVAM_ET = "davam et"

DEYISEN = "dəyişən"
SABIT = "sabit"
DEYISMEZ = "dəyişməz"
FUNKSIYA = "funksiya"
QAYTAR = "qaytar"
VER = "ver"
GOZLE = "gözlə"
ASINXRON = "asinxron"
GENERATOR = "generator"
BLOK = "blok"
GECIKDIR = "gecikdir"
ISTIFADE = "istifadə"

SINIF = "sinif"
STRUKTUR = "struktur"
INTERFEYS = "interfeys"
SADALAMA = "sadalama"
MODUL = "modul"
OBYEKT = "obyekt"
QARISIQ = "qarışıq"
TIP = "tip"
QURUCU = "qurucu"
SILINSIN = "silinsin"
METOD = "metod"
XASSE = "xassə"
GENISLET = "genişlət"
KOMPONENT = "komponent"
MAGAZA = "mağaza"

OZU = "özü"
UST = "üst"
YENI = "yeni"
MIRAS = "miras"
TETBIQ = "tətbiq"
ILE = "ilə"
EVEZ_ET = "əvəz et"

ACIQ = "açıq"
GIZLI = "gizli"
QORUNAN = "qorunan"
STATIK = "statik"
MUCERRED = "mücərrəd"
TENBEL = "tənbəl"
GLOBAL = "global"

CEHD_ET = "cəhd et"
TUT = "tut"
NEHAYET = "nəhayət"
AT = "at"
IDDIA = "iddia"
TEMIN = "təmin"
BERPA = "bərpa"

GETIR = "gətir"
IXRAC_ET = "ixrac et"
KIMI = "kimi"
STANDART = "standart"
BASLANGIC = "başlanğıc"
BITIS = "bitiş"

VE = "və"
VE_YA = "və ya"
DEYIL = "deyil"
ICINDEDIR = "içindədir"
TIPIDIR = "tipidir"
BOSDUR = "boşdur"
BOS_DEYIL = "boş deyil"

DOGRU = "doğru"
YANLIS = "yanlış"
BOS = "boş"
SONSUZ = "sonsuz"
EDED_DEYIL = "ƏdədDeyil"

DAYAN_NOQTESI = "dayanNöqtəsi"


# ═══════════════════════════════════════════════════════════════════════
#  6. KÖMƏKÇİ FUNKSİYALAR
# ═══════════════════════════════════════════════════════════════════════

def açar_sözdür(söz: str) -> bool:
    """Sərt açar sözdürmü?"""
    return söz in ACAR_SOZLER


def kontekstlidir(söz: str) -> bool:
    return söz in KONTEKSTLI


def kanonikləşdir(söz: str) -> tuple[str | None, bool]:
    """
    Bir sözü kanonik açar söz formasına salır — ASCII çevrilməsi ilə.

    DİQQƏT: `QISA_ALIAS` BURADA tətbiq olunmur. Səbəb: `davam` sözü
    dərhal `davam et`-ə çevrilsəydi, lekser çox sözlü birləşməni
    (`davam` + `et`) artıq tapa bilməzdi — `COX_SOZLU_INDEKS` ilk SÖZƏ
    görə indekslidir. Aliaslar birləşmə cəhdindən SONRA `tamamla()` ilə
    tətbiq edilir.

    Qaytarır: (kanonik_forma | None, ascii_idi)

        kanonikləşdir("əgər")  → ("əgər", False)
        kanonikləşdir("eger")  → ("əgər", True)
        kanonikləşdir("davam") → ("davam", False)    ← alias hələ yox
        kanonikləşdir("yaş")   → (None, False)       ← identifikator
    """
    if söz in ACAR_SOZLER:
        return söz, False
    if söz in ASCII_ALIAS:
        return ASCII_ALIAS[söz], True
    return None, False


def tamamla(kanonik: str) -> str:
    """
    Qısa aliasları son formaya salır. Birləşmə cəhdindən SONRA çağırılır.

        tamamla("davam")     → "davam et"
        tamamla("əks halda") → "yoxsa"
        tamamla("əgər")      → "əgər"
    """
    return QISA_ALIAS.get(kanonik, kanonik)


# ── Yeni sətrin udulacağı tokenlər (Spesifikasiya § 1.11) ──────────────
#  Sətrin sonunda bu açar sözlər varsa, ifadə növbəti sətirdə davam edir.

#  DİQQƏT: `içində` BURADA OLMAMALIDIR. O, `hər ... içində` başlığının
#  SON tokenidir — ondan sonra ifadə davam etmir, dövrün gövdəsi başlayır.
#  Siyahıda olsaydı, aşağıdaki iki konstruksiya fərqlənməzdi:
#      hər x üçün s içində əgər x > 5      ← filtr şərti
#      hər x üçün s içində
#          əgər x > 5 onda ... son         ← gövdədəki şərt
#  Yeni sətir udulanda parser ikincini də filtr kimi oxuyurdu.
DAVAM_ACAR_SOZLERI: frozenset[str] = frozenset([
    VE, VE_YA, DEYIL, KIMI, TIPIDIR, ICINDEDIR,
    YENI, GETIR, AT, VER, GOZLE, IDDIA,
    MIRAS, TETBIQ, ILE, UCUN, ADDIM, ONDA, HAL,
])


# ── Qorunmuş, lakin hələ istifadə olunmayan sözlər ─────────────────────
#  İstifadəçi bunları identifikator kimi işlədə bilər, amma xəbərdarlıq alır
#  (ALQ-L016). Yalnız müstəqil ad mövqeyində — `veb.makro` kimi üzv
#  adlarında xəbərdarlıq verilmir.
#
#  DİQQƏT: bu siyahıya yalnız HƏQİQƏTƏN açar söz ola biləcək sözlər
#  düşməlidir. Standart kitabxanada işlənən adi sözlər (`şablon`, `qeyd`,
#  `kanal`, `icazə` …) BURAYA SALINMAMALIDIR — onlar `veb.şablon()`,
#  `Kanal[tam]` kimi mövcud API-lərdə var.

EHTIYAT: frozenset[str] = frozenset([
    "ömür",        # ömür parametrləri (lifetime)
    "təsir",       # effekt sistemi
])


# ── Özünü yoxlama ──────────────────────────────────────────────────────
#  Sərt və kontekstli dəstlər kəsişməməlidir.
assert not (ACAR_SOZLER & KONTEKSTLI), \
    f"toqquşma: {ACAR_SOZLER & KONTEKSTLI}"

#  Çox sözlü birləşmələrin hər komponenti sərt açar söz olmalıdır.
for _p in COX_SOZLU:
    for _s in _p:
        assert _s in ACAR_SOZLER, f"'{_s}' açar söz deyil ({_p})"
