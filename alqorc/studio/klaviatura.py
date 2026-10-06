"""
Alqor Studio — Azərbaycan klaviaturası olmayanlar üçün köməkçi.

Spesifikasiya § 1.7 "Redaktor giriş metodu" üç qat müəyyən edir:

  1. Avtomatik söz çevrilməsi — yazılan ASCII açar söz söz sərhədində
     dərhal kanonik formaya keçir: `eger` + boşluq → `əgər `
  2. Kompozisiya düyməsi — `;` prefiksi: `;e` → `ə`, `;I` → `İ`,
     `;;` → `;`
  3. Hərf paneli — redaktorun altında `ə ı ğ ş ç ö ü İ` düymələri

(3-cü qat və kompilyatorun özünün ASCII qəbul etməsi — ALQ-L020 —
ayrıca mövcuddur.) Bu modul 1-ci və 2-ci qatın QAYDALARINI saxlayır.
Brauzer tərəfi (`statik/redaktor.js`) eyni qaydaları `/api/klaviatura`
cədvəlindən oxuyur; Python versiyası sınaqlar və etalon üçündür.
"""

from __future__ import annotations

from alqor import acar_sozler as AS
from alqor.elifba import latınla

from .qurulus import KOD, xəritə

# ═══════════════════════════════════════════════════════════════════════
#  Cədvəllər
# ═══════════════════════════════════════════════════════════════════════

# Spesifikasiya § 1.7, "Kompozisiya düyməsi" cədvəli
KOMPOZİSİYA: dict[str, str] = {
    "e": "ə", "E": "Ə",
    "i": "ı", "I": "İ",
    "o": "ö", "O": "Ö",
    "u": "ü", "U": "Ü",
    "c": "ç", "C": "Ç",
    "s": "ş", "S": "Ş",
    "g": "ğ", "G": "Ğ",
    ";": ";",
}
PREFİKS = ";"


def _ascii_cədvəli() -> dict[str, str]:
    """
    Tək sözlük ASCII → kanonik. Çox sözlü açar sözlərin hər hissəsi
    özü açar sözdür (`ne qeder ki` → `nə` `qədər` `ki`), ona görə tək
    söz cədvəli kifayətdir. Spesifikasiya cədvəlindəki tip adları da
    (`metn` → `mətn`, `siyahi` → `siyahı`) əlavə olunur.
    """
    c = {a: k for a, k in AS.ASCII_ALIAS.items() if " " not in a}
    for t in AS.TIP_ADLARI:
        a = latınla(t)
        if a != t and a not in c:
            c[a] = t
    return c


ASCII_CƏDVƏLİ: dict[str, str] = _ascii_cədvəli()

# Sözü bitirən simvollar — bunlardan biri yazılanda əvvəlki söz yoxlanılır
SƏRHƏDLƏR = frozenset(" \t\n()[]{},:.=<>!+-*/%&|^?")


def _ad_simvoludur(c: str) -> bool:
    return c.isalnum() or c == "_"


# ═══════════════════════════════════════════════════════════════════════
#  1. Avtomatik söz çevrilməsi
# ═══════════════════════════════════════════════════════════════════════

def söz_çevir(söz: str) -> str | None:
    """`eger` → `əgər`; açar söz deyilsə və ya artıq kanonikdirsə None."""
    return ASCII_CƏDVƏLİ.get(söz)


def avtomatik_çevir(mətn: str, kursor: int) -> tuple[str, int] | None:
    """
    `kursor`-dan əvvəlki simvol söz sərhədidir (yenicə yazılıb). Ondan
    əvvəlki söz ASCII açar sözdürsə kanonik formaya çevrilir.

    Çevrilmir:
      • mətn literalı və şərh içində
      • üzv adında (`siyahı.ve` — nöqtədən sonra)
      • sözün ortasında (`evet` sözündəki `ve` deyil, bütöv söz)

    Qaytarır: (yeni mətn, yeni kursor) və ya None.
    """
    if kursor <= 0 or kursor > len(mətn):
        return None
    if mətn[kursor - 1] not in SƏRHƏDLƏR:
        return None
    son = kursor - 1
    baş = son
    while baş > 0 and _ad_simvoludur(mətn[baş - 1]):
        baş -= 1
    söz = mətn[baş:son]
    kanonik = söz_çevir(söz)
    if not kanonik:
        return None
    if baş > 0 and mətn[baş - 1] == ".":
        return None
    if xəritə(mətn[:son])[baş] != KOD:
        return None
    yeni = mətn[:baş] + kanonik + mətn[son:]
    return yeni, kursor + len(kanonik) - len(söz)


# ═══════════════════════════════════════════════════════════════════════
#  2. `;` kompozisiyası
# ═══════════════════════════════════════════════════════════════════════

def kompozisiya(mətn: str, kursor: int) -> tuple[str, int] | None:
    """
    `kursor`-dan əvvəlki iki simvol `;` + hərfdirsə Azərbaycan hərfi ilə
    əvəzlənir: `;e` → `ə`. `;;` tək `;` verir (literal nöqtəli vergül).
    Mətn literalı içində də işləyir — Azərbaycan mətni yazmaq üçün.
    """
    if kursor < 2 or kursor > len(mətn):
        return None
    if mətn[kursor - 2] != PREFİKS:
        return None
    hərf = KOMPOZİSİYA.get(mətn[kursor - 1])
    if hərf is None:
        return None
    return mətn[:kursor - 2] + hərf + mətn[kursor:], kursor - 1


def mətni_yaz(düymələr: str, ascii: bool = True,
              tərkib: bool = True) -> str:
    """
    Simvolları bir-bir "yazır" — redaktorun davranışını sınamaq üçün.

        mətni_yaz("eger x onda")  → "əgər x onda"
        mətni_yaz(";salam")       → "şalam"
    """
    mətn = ""
    kursor = 0
    son_tərkib = False
    for c in düymələr:
        mətn = mətn[:kursor] + c + mətn[kursor:]
        kursor += 1
        if tərkib and not son_tərkib:
            n = kompozisiya(mətn, kursor)
            if n is not None:
                mətn, kursor = n
                # `;;` → `;` — bu `;` növbəti hərflə birləşməməlidir
                son_tərkib = c == PREFİKS
                continue
        son_tərkib = False
        if ascii:
            n = avtomatik_çevir(mətn, kursor)
            if n is not None:
                mətn, kursor = n
    return mətn


def cədvəl() -> dict:
    """Brauzer tərəfi üçün — `/api/klaviatura`."""
    return {
        "ascii": ASCII_CƏDVƏLİ,
        "kompozisiya": KOMPOZİSİYA,
        "prefiks": PREFİKS,
        "sərhədlər": "".join(sorted(SƏRHƏDLƏR)),
        "hərflər": ["ə", "ı", "ğ", "ş", "ç", "ö", "ü", "İ",
                    "Ə", "Ğ", "Ş", "Ç", "Ö", "Ü"],
    }
