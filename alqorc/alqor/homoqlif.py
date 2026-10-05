"""
Alqor — Homoqlif (oxşar simvol) aşkarlanması və düzəldilməsi.

Problem: `ə` (U+0259) hərfinə çox simvol oxşayır — `ä` (U+00E4),
`ǝ` (U+01DD), `∂` (U+2202). Kiril `е` (U+0435) latın `e`-dən (U+0065)
fərqlənmir. Nəticədə eyni görünən iki identifikator fərqli olur və
proqramçı saatlarla tapılmayan səhv axtarır.

Bu modul mənbə faylı lekserə verilməzdən əvvəl onları düzəldir və
xəbərdarlıq (ALQ-L014) qeyd edir.

NFC normalizasiyası ayrıca aparılır (menbe.py) — o, `s`+U+0327 → `ş` və
`g`+U+0306 → `ğ` kimi parçalanmış formaları birləşdirir. Burada yalnız
NFC-nin həll edə BİLMƏDİYİ hallar var.
"""

from __future__ import annotations
from dataclasses import dataclass

# ───────────────────────────────────────────────────────────────────────
#  1 simvol → 1 simvol əvəzləmələr (uzunluq dəyişmir, mövqelər qorunur)
# ───────────────────────────────────────────────────────────────────────

EVEZLEMELER: dict[str, str] = {
    # ── "ə" hərfinə oxşayanlar ──────────────────────────────────
    "ä": "ə",   # ä  LATIN SMALL LETTER A WITH DIAERESIS
    "Ä": "Ə",   # Ä
    "ǝ": "ə",   # ǝ  LATIN SMALL LETTER TURNED E
    "Ǝ": "Ə",   # Ǝ  LATIN CAPITAL LETTER REVERSED E
    "∂": "ə",   # ∂  PARTIAL DIFFERENTIAL (köhnə mətnlərdə)
    "ә": "ə",   # ә  CYRILLIC SMALL SCHWA
    "Ә": "Ə",   # Ә  CYRILLIC CAPITAL SCHWA

    # ── Kiril hərfləri (latın hərflərindən fərqlənmir) ──────────
    "а": "a",   # а
    "е": "e",   # е
    "о": "o",   # о
    "с": "c",   # с
    "р": "p",   # р
    "х": "x",   # х
    "у": "y",   # у
    "і": "i",   # і  CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
    "ѕ": "s",   # ѕ  CYRILLIC SMALL LETTER DZE
    "ј": "j",   # ј  CYRILLIC SMALL LETTER JE
    "һ": "h",   # һ  CYRILLIC SMALL LETTER SHHA
    "А": "A",   # А
    "В": "B",   # В
    "Е": "E",   # Е
    "К": "K",   # К
    "М": "M",   # М
    "Н": "H",   # Н
    "О": "O",   # О
    "Р": "P",   # Р
    "С": "C",   # С
    "Т": "T",   # Т
    "Х": "X",   # Х
    "І": "I",   # І
    "Ѕ": "S",   # Ѕ
    "Ј": "J",   # Ј

    # ── Yunan hərfləri ──────────────────────────────────────────
    "α": "a",   # α
    "ε": "e",   # ε
    "ο": "o",   # ο
    "ρ": "p",   # ρ
    "υ": "u",   # υ
    "Α": "A",   # Α
    "Β": "B",   # Β
    "Ε": "E",   # Ε
    "Η": "H",   # Η
    "Ι": "I",   # Ι
    "Κ": "K",   # Κ
    "Μ": "M",   # Μ
    "Ν": "N",   # Ν
    "Ο": "O",   # Ο
    "Ρ": "P",   # Ρ
    "Τ": "T",   # Τ
    "Χ": "X",   # Χ

    # ── "ı" hərfinə oxşayanlar ──────────────────────────────────
    "ɩ": "ı",   # ɩ  LATIN SMALL LETTER IOTA
    "ι": "ı",   # ι  GREEK SMALL LETTER IOTA

    # ── Rumın/türk latın variantları ────────────────────────────
    "ș": "ş",   # ș  LATIN SMALL LETTER S WITH COMMA BELOW
    "Ș": "Ş",   # Ș
    "ţ": "t",   # ţ  LATIN SMALL LETTER T WITH CEDILLA
    "ț": "t",   # ț  LATIN SMALL LETTER T WITH COMMA BELOW

    # ── Boşluq variantları ──────────────────────────────────────
    " ": " ",   # NO-BREAK SPACE
    " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", " ": " ", " ": " ",
    " ": " ",   # NARROW NO-BREAK SPACE
    " ": " ",   # MEDIUM MATHEMATICAL SPACE
    "　": " ",   # IDEOGRAPHIC SPACE
    " ": " ",   # OGHAM SPACE MARK
}

# Tam genişlikli latın HƏRFLƏRİ və RƏQƏMLƏRİ (ＡＢＣ → ABC, ０１２ → 012).
# Durğu işarələri qəsdən daxil edilmir — onlar mətn literalında qanuni
# məzmun ola bilər.
for _aralıq in ((0xFF10, 0xFF19), (0xFF21, 0xFF3A), (0xFF41, 0xFF5A)):
    for _k in range(_aralıq[0], _aralıq[1] + 1):
        EVEZLEMELER.setdefault(chr(_k), chr(_k - 0xFEE0))

# ── QƏSDƏN DAXİL EDİLMƏYƏNLƏR ──────────────────────────────────────────
#  Bunlar homoqlif DEYİL, qanuni durğu işarələridir və şərhlərdə,
#  mətn literallarında normal istifadə olunur:
#
#     – —  (en/em dash)     "// Nümunə 1 — Ən sadə proqram"  ← düzgündür
#     " " ' '               mətn daxilində sitat
#     × ÷                   riyazi mətn
#
#  Kod mövqeyində görünsələr, lekser onları ALQ-L002 kimi bildirir —
#  bu, səssiz "düzəliş"dən daha dürüstdür.

# ───────────────────────────────────────────────────────────────────────
#  Silinəcək görünməz simvollar
# ───────────────────────────────────────────────────────────────────────

SILINECEK: dict[str, str] = {
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "‎": "LEFT-TO-RIGHT MARK",
    "‏": "RIGHT-TO-LEFT MARK",
    "⁠": "WORD JOINER",
    "­": "SOFT HYPHEN",
    "﻿": "ZERO WIDTH NO-BREAK SPACE (BOM)",
    "‪": "LEFT-TO-RIGHT EMBEDDING",
    "‫": "RIGHT-TO-LEFT EMBEDDING",
    "‬": "POP DIRECTIONAL FORMATTING",
    "‭": "LEFT-TO-RIGHT OVERRIDE",
    "‮": "RIGHT-TO-LEFT OVERRIDE",
    "⁦": "LEFT-TO-RIGHT ISOLATE",
    "⁧": "RIGHT-TO-LEFT ISOLATE",
    "⁨": "FIRST STRONG ISOLATE",
    "⁩": "POP DIRECTIONAL ISOLATE",
}

# Sətir ayırıcı variantları → LF
SETIR_AYIRICILAR = {
    " ": "\n",   # LINE SEPARATOR
    " ": "\n",   # PARAGRAPH SEPARATOR
    "\u000b": "\n",   # VERTICAL TAB
    "\u000c": "\n",   # FORM FEED
    "\u0085": "\n",   # NEXT LINE
}


@dataclass
class Tapıntı:
    """Aşkarlanmış homoqlif."""
    mövqe: int           # düzəldilmiş mətndəki mövqe
    tapılan: str         # orijinal simvol
    əvəz: str            # nə ilə əvəz olundu ("" = silindi)
    ad: str              # simvolun Unicode adı / izahı

    @property
    def kod(self) -> str:
        return "U+%04X" % ord(self.tapılan)

    def mesaj(self) -> str:
        if self.əvəz == "":
            return f"görünməz simvol silindi: {self.ad} ({self.kod})"
        return (f"'{self.tapılan}' ({self.kod}) → "
                f"'{self.əvəz}' (U+%04X)" % ord(self.əvəz))


def düzəlt(mətn: str) -> tuple[str, list[Tapıntı]]:
    """
    Mətndəki homoqlifləri düzəldir.

    Qaytarır: (düzəldilmiş mətn, tapıntılar siyahısı)

    Mövqelər DÜZƏLDİLMİŞ mətnə görədir — lekser və xəta hesabatı
    hamısı həmin mətn üzərində işləyir.
    """
    if not _şübhə_var(mətn):
        return mətn, []

    nəticə: list[str] = []
    tapıntılar: list[Tapıntı] = []

    for c in mətn:
        if c in SILINECEK:
            tapıntılar.append(Tapıntı(len(nəticə), c, "", SILINECEK[c]))
            continue

        if c in SETIR_AYIRICILAR:
            tapıntılar.append(Tapıntı(
                len(nəticə), c, "\n", "sətir ayırıcı variantı"))
            nəticə.append("\n")
            continue

        əvəz = EVEZLEMELER.get(c)
        if əvəz is not None and əvəz != c:
            tapıntılar.append(Tapıntı(len(nəticə), c, əvəz, _ad(c)))
            nəticə.append(əvəz)
            continue

        nəticə.append(c)

    return "".join(nəticə), tapıntılar


def _şübhə_var(mətn: str) -> bool:
    """Sürətli ön yoxlama: ASCII + Azərbaycan hərfləri varsa işə düşməyək."""
    from .elifba import HERFLER
    for c in mətn:
        o = ord(c)
        if o < 0x80:
            continue
        if c in HERFLER:
            continue
        return True
    return False


def _ad(c: str) -> str:
    import unicodedata
    try:
        return unicodedata.name(c)
    except ValueError:
        return "naməlum simvol"
