"""
Alqor — Token modeli.

Lekserin çıxışı `Token` siyahısıdır. Hər tokenin mənbə faylındaki dəqiq
mövqeyi (`Yer`) var — xəta hesabatı bundan asılıdır.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol


class MənbəKimi(Protocol):
    """`Yer`-in mənbədən gözlədiyi minimum interfeys."""
    ad: str
    def sətir_sütun(self, mövqe: int) -> tuple[int, int]: ...
    def sətir_mətni(self, sətir: int) -> str: ...


# ═══════════════════════════════════════════════════════════════════════
#  Token növləri
# ═══════════════════════════════════════════════════════════════════════

class Növ(Enum):
    # ── Literallar ──────────────────────────────────────────
    TAM = auto()          # 42, 0x1F, 0b1010, 1_000
    ONLUQ = auto()        # 3.14, 1.5e3
    METN = auto()         # "salam", "Salam, {ad}", """...""", x"..."
    SIMVOL = auto()       # `ə`
    BAYT = auto()         # b"ABC"

    # ── Adlar ───────────────────────────────────────────────
    AD = auto()           # identifikator
    ACAR = auto()         # açar söz (kanonik formada)

    # ── Simvollar ───────────────────────────────────────────
    OP = auto()           # operator və ayırıcı

    # ── İnterfeys sintaksisi ────────────────────────────────
    #  Lekser JSX elementini XAM skan edib bir token kimi buraxır.
    #  `dəyər` = (başlanğıc_ofset, son_ofset). Parser `parser_jsx` ilə
    #  həmin aralığı ayırır. Belə olmasa, JSX mətnindəki `—`, `'`, `"`
    #  kimi simvollar leksik xəta verərdi.
    JSX = auto()

    # ── Struktur ────────────────────────────────────────────
    SETIR_SONU = auto()   # ifadə ayırıcısı
    FAYL_SONU = auto()

    # ── Metaməlumat (parser atlayır, alətlər oxuyur) ────────
    SENED = auto()        # /// və //!
    DIREKTIV = auto()     # // alqor: ...

    def __repr__(self) -> str:
        return self.name


# ═══════════════════════════════════════════════════════════════════════
#  Mövqe
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Yer:
    """Mənbə faylında bir parçanın yeri."""
    mənbə: Any                 # MənbəKimi
    başlanğıc: int             # simvol indeksi (0-dan)
    uzunluq: int

    @property
    def son(self) -> int:
        return self.başlanğıc + self.uzunluq

    @property
    def sətir(self) -> int:
        return self.mənbə.sətir_sütun(self.başlanğıc)[0]

    @property
    def sütun(self) -> int:
        return self.mənbə.sətir_sütun(self.başlanğıc)[1]

    @property
    def fayl(self) -> str:
        return self.mənbə.ad

    def birləşdir(self, digər: "Yer") -> "Yer":
        """İki yeri əhatə edən yer."""
        b = min(self.başlanğıc, digər.başlanğıc)
        s = max(self.son, digər.son)
        return Yer(self.mənbə, b, s - b)

    def __str__(self) -> str:
        s, st = self.mənbə.sətir_sütun(self.başlanğıc)
        return f"{self.mənbə.ad}:{s}:{st}"


# ═══════════════════════════════════════════════════════════════════════
#  Şablon mətn parçaları
# ═══════════════════════════════════════════════════════════════════════
#  "Salam, {ad}! {yaş + 1} olacaqsan"  →
#    [MətnParçası("Salam, "),
#     KodParçası(tokenlər=[AD ad], format=None),
#     MətnParçası("! "),
#     KodParçası(tokenlər=[AD yaş, OP +, TAM 1], format=None),
#     MətnParçası(" olacaqsan")]

@dataclass
class MətnParçası:
    """Şablon mətnin sabit hissəsi."""
    dəyər: str

    def __repr__(self) -> str:
        return f"Mətn({self.dəyər!r})"


@dataclass
class KodParçası:
    """Şablon mətnin `{...}` daxilindəki ifadəsi."""
    tokenlər: list["Token"]
    format: str | None = None      # `{qiymət:.2}` → ".2"

    def __repr__(self) -> str:
        f = f", format={self.format!r}" if self.format else ""
        return f"Kod({len(self.tokenlər)} token{f})"


Parça = MətnParçası | KodParçası


# ═══════════════════════════════════════════════════════════════════════
#  Token
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Token:
    növ: Növ
    dəyər: Any                            # str | int | float | bytes | None
    yer: Yer
    xam: str = ""                         # mənbədəki orijinal mətn
    parçalar: list[Parça] | None = None   # yalnız METN üçün
    ascii_idi: bool = False               # ACAR: ASCII formada yazılıbmı
    çoxsətirli: bool = False              # METN: """ ... """ idimi

    # ── Rahat yoxlamalar — parser bunları işlədir ──────────────────────

    def acardır(self, *hansı: str) -> bool:
        """`t.acardır("əgər")` və ya `t.acardır("yoxsa", "əks halda")`"""
        return self.növ is Növ.ACAR and self.dəyər in hansı

    def opdur(self, *hansı: str) -> bool:
        return self.növ is Növ.OP and self.dəyər in hansı

    def addır(self) -> bool:
        return self.növ is Növ.AD

    def literaldır(self) -> bool:
        return self.növ in (Növ.TAM, Növ.ONLUQ, Növ.METN,
                            Növ.SIMVOL, Növ.BAYT)

    def sonudur(self) -> bool:
        return self.növ is Növ.FAYL_SONU

    def sadə_mətndir(self) -> bool:
        """İnterpolyasiyası olmayan mətn literalı."""
        return self.növ is Növ.METN and not any(
            isinstance(p, KodParçası) for p in (self.parçalar or []))

    def __repr__(self) -> str:
        if self.növ is Növ.SETIR_SONU:
            return "⏎"
        if self.növ is Növ.FAYL_SONU:
            return "⊣"
        if self.növ is Növ.METN and self.parçalar:
            return f"METN{self.parçalar}"
        a = "(ascii)" if self.ascii_idi else ""
        return f"{self.növ.name}({self.dəyər!r}){a}"

    def göstər(self) -> str:
        """Diaqnostika üçün bir sətirlik təsvir."""
        yer = f"{self.yer.sətir}:{self.yer.sütun}"
        return f"{yer:>9}  {self.növ.name:<11} {self.dəyər!r}"


# ═══════════════════════════════════════════════════════════════════════
#  Operator cədvəli — maksimal udma (longest match first)
# ═══════════════════════════════════════════════════════════════════════

OPERATORLAR_3 = (
    "**=", "~/=", "<<=", ">>=", ">>>", "..<", "...", "??=", "<=>",
)

OPERATORLAR_2 = (
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "==", "!=", "<=", ">=", "&&", "||", "<<", ">>",
    "**", "~/", "??", "?.", "?=", "..", "->", "=>", "|>", "++", "--",
)

OPERATORLAR_1 = (
    "+", "-", "*", "/", "%", "=", "<", ">", "!",
    "&", "|", "^", "~", "?", ".", ",", ";", ":", "@", "#",
    "(", ")", "[", "]", "{", "}",
    "→",          # →  `hal 1 → ...` oxu
)

OPERATORLAR = OPERATORLAR_3 + OPERATORLAR_2 + OPERATORLAR_1

# Açan / bağlayan mötərizələr — sətir sonu udulması üçün
ACANLAR = frozenset("([{")
BAGLAYANLAR = frozenset(")]}")

# Bu operatorlardan sonra yeni sətir UDULMUR (ifadə bitə bilər)
IFADE_BITIREN_OP = frozenset({")", "]", "}", "!", "++", "--", "?"})

# `→` və `->` ekvivalentdir (`hal` kontekstində)
OX_FORMALARI = frozenset({"→", "->"})

# İfadəni bitirə bilən tokenlər — `<` operator yoxsa JSX olduğunu ayırır.
# `a < b` → əvvəlki token `a` ifadəni bitirir, deməli müqayisədir.
# `qaytar <div>` → `qaytar` ifadəni bitirmir, deməli JSX-dir.
IFADE_BITIREN_LITERALLAR = frozenset({
    "doğru", "yanlış", "boş", "özü", "üst", "sonsuz", "ƏdədDeyil",
})
