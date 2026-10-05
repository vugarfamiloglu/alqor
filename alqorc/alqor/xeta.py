"""
Alqor — Diaqnostika və xəta hesabatı.

Bütün mesajlar Azərbaycan dilindədir. Hər xətanın kodu, yeri, altından
xətlənmiş mənbə parçası və düzəliş təklifi var.

    ✖ ALQ-T008  Operator `+` bu tiplərə tətbiq edilmir
      ┌─ əsas.alqor:12:15
      │
    12│     yaz("Yaş: " + yaş)
      │          ^^^^^^^^^^^^ `mətn` və `tam` toplanmır
      │
      = kömək: interpolyasiya istifadə edin: "Yaş: {yaş}"
      = sənəd: alqor.az/xeta/ALQ-T008
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from enum import Enum

from .token import Yer

SENED_KOKU = "alqor.az/xeta"
TAB_GENISLIK = 4


# ═══════════════════════════════════════════════════════════════════════
#  Səviyyələr
# ═══════════════════════════════════════════════════════════════════════

class Səviyyə(Enum):
    XETA = ("✖", "xəta", "31")            # qırmızı
    XEBERDARLIQ = ("⚠", "xəbərdarlıq", "33")   # sarı
    MELUMAT = ("ℹ", "məlumat", "36")      # mavi

    def __init__(self, işarə: str, ad: str, rəng: str):
        self.işarə = işarə
        self.adı = ad
        self.rəng = rəng


# ═══════════════════════════════════════════════════════════════════════
#  Rəng dəstəyi
# ═══════════════════════════════════════════════════════════════════════

def rənglər_açıqdır() -> bool:
    """
    Mühit dəyişəni `ALQOR_RENG`: həmişə | heçvaxt | avto (standart).

    Qeyd: dəyişən adı qəsdən ASCII-dir — `ALQOR_RƏNG` adlı dəyişən
    shell-də (xüsusən Windows-da) təyin oluna bilmir.
    """
    r = os.environ.get("ALQOR_RENG", "avto").lower()
    if r in ("həmişə", "hemise", "always", "1"):
        return True
    if r in ("heçvaxt", "hecvaxt", "never", "0"):
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stderr.isatty()


class _Boya:
    def __init__(self, aktiv: bool):
        self.aktiv = aktiv

    def __call__(self, mətn: str, kod: str) -> str:
        if not self.aktiv:
            return mətn
        return f"\033[{kod}m{mətn}\033[0m"

    def qalın(self, mətn: str) -> str:
        return self(mətn, "1")

    def solğun(self, mətn: str) -> str:
        return self(mətn, "90")


# ═══════════════════════════════════════════════════════════════════════
#  Diaqnostika
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Diaqnostika:
    kod: str                       # "ALQ-L003"
    mesaj: str                     # qısa başlıq
    yer: Yer | None = None
    səviyyə: Səviyyə = Səviyyə.XETA
    qeyd: str = ""                 # xəttin altındaki izah
    köməklər: list[str] = field(default_factory=list)

    @property
    def xətadır(self) -> bool:
        return self.səviyyə is Səviyyə.XETA

    # ── Çap ────────────────────────────────────────────────────────────

    def formatla(self, rəngli: bool | None = None) -> str:
        b = _Boya(rənglər_açıqdır() if rəngli is None else rəngli)
        s = self.səviyyə
        sətirlər: list[str] = []

        başlıq = b(f"{s.işarə} {self.kod}", s.rəng)
        sətirlər.append(f"{başlıq}  {b.qalın(self.mesaj)}")

        if self.yer is not None:
            sətirlər.extend(self._mənbə_parçası(b))

        for k in self.köməklər:
            sətirlər.append(f"  {b.solğun('= kömək:')} {k}")

        sətirlər.append(f"  {b.solğun('= sənəd:')} {SENED_KOKU}/{self.kod}")
        return "\n".join(sətirlər)

    def _mənbə_parçası(self, b: _Boya) -> list[str]:
        y = self.yer
        assert y is not None
        sətir_no, sütun = y.mənbə.sətir_sütun(y.başlanğıc)
        xam = y.mənbə.sətir_mətni(sətir_no)

        # Tabulyasiyaları aç və sütunu uyğunlaşdır
        mətn, sütun = _tab_aç(xam, sütun)

        w = len(str(sətir_no))
        boş = " " * w
        düz = b.solğun("│")

        # Xətt uzunluğu — sətir sonunu aşmasın
        uz = max(1, y.uzunluq)
        qalan = max(1, len(mətn) - (sütun - 1))
        uz = min(uz, qalan)

        xətt = " " * (sütun - 1) + b("^" * uz, self.səviyyə.rəng)
        if self.qeyd:
            xətt += " " + b(self.qeyd, self.səviyyə.rəng)

        return [
            f"  {boş}{b.solğun('┌─')} {b.qalın(str(y))}",
            f"  {boş}{düz}",
            f"  {b.solğun(str(sətir_no))}{düz} {mətn}",
            f"  {boş}{düz} {xətt}",
            f"  {boş}{düz}",
        ]

    def __str__(self) -> str:
        return self.formatla(rəngli=False)


def _tab_aç(mətn: str, sütun: int) -> tuple[str, int]:
    """Tabulyasiyaları boşluqla əvəz edir və sütun nömrəsini uyğunlaşdırır."""
    if "\t" not in mətn:
        return mətn, sütun
    nəticə: list[str] = []
    yeni_sütun = sütun
    for i, c in enumerate(mətn):
        if c == "\t":
            əlavə = TAB_GENISLIK - (len(nəticə) % TAB_GENISLIK)
            nəticə.append(" " * əlavə)
            if i < sütun - 1:
                yeni_sütun += əlavə - 1
        else:
            nəticə.append(c)
    return "".join(nəticə), yeni_sütun


# ═══════════════════════════════════════════════════════════════════════
#  Toplayıcı
# ═══════════════════════════════════════════════════════════════════════

class XətaToplayıcı:
    """Kompilyasiya boyunca diaqnostikaları yığır."""

    def __init__(self, xəbərdarlıq_xətadır: bool = False,
                 limit: int = 100):
        self.siyahı: list[Diaqnostika] = []
        self.xəbərdarlıq_xətadır = xəbərdarlıq_xətadır
        self.limit = limit
        self._söndürülmüş: set[str] = set()

    # ── Söndürmə (// alqor: ... direktivləri) ──────────────────────────

    def söndür(self, kod_və_ya_qrup: str) -> None:
        self._söndürülmüş.add(kod_və_ya_qrup)

    def _söndürülüb(self, kod: str) -> bool:
        return kod in self._söndürülmüş

    # ── Əlavə etmə ────────────────────────────────────────────────────

    def əlavə(self, d: Diaqnostika) -> None:
        if self._söndürülüb(d.kod):
            return
        if (self.xəbərdarlıq_xətadır
                and d.səviyyə is Səviyyə.XEBERDARLIQ):
            d.səviyyə = Səviyyə.XETA
        self.siyahı.append(d)

    def xəta(self, kod: str, mesaj: str, yer: Yer | None = None,
             qeyd: str = "", *köməklər: str) -> None:
        self.əlavə(Diaqnostika(kod, mesaj, yer, Səviyyə.XETA,
                               qeyd, list(köməklər)))

    def xəbərdarlıq(self, kod: str, mesaj: str, yer: Yer | None = None,
                    qeyd: str = "", *köməklər: str) -> None:
        self.əlavə(Diaqnostika(kod, mesaj, yer, Səviyyə.XEBERDARLIQ,
                               qeyd, list(köməklər)))

    # ── Sorğu ─────────────────────────────────────────────────────────

    @property
    def xətalar(self) -> list[Diaqnostika]:
        return [d for d in self.siyahı if d.xətadır]

    @property
    def xəbərdarlıqlar(self) -> list[Diaqnostika]:
        return [d for d in self.siyahı
                if d.səviyyə is Səviyyə.XEBERDARLIQ]

    def uğurludur(self) -> bool:
        return not self.xətalar

    def dolubmu(self) -> bool:
        return len(self.xətalar) >= self.limit

    # ── Hesabat ───────────────────────────────────────────────────────

    def hesabat(self, rəngli: bool | None = None) -> str:
        if not self.siyahı:
            return ""
        parçalar = [d.formatla(rəngli) for d in self._sıralı()]
        return "\n\n".join(parçalar)

    def _sıralı(self) -> list[Diaqnostika]:
        def açar(d: Diaqnostika):
            if d.yer is None:
                return (0, 0, 0)
            return (1, d.yer.başlanğıc, 0)
        # Xətalar əvvəl, sonra xəbərdarlıqlar; hər qrup mövqeyə görə
        xəta = sorted(self.xətalar, key=açar)
        digər = sorted((d for d in self.siyahı if not d.xətadır), key=açar)
        return xəta + digər

    def xülasə(self, rəngli: bool | None = None) -> str:
        b = _Boya(rənglər_açıqdır() if rəngli is None else rəngli)
        x, xb = len(self.xətalar), len(self.xəbərdarlıqlar)
        if x == 0 and xb == 0:
            return b("✓ Xəta yoxdur", "32")
        hissə = []
        if x:
            hissə.append(b(f"{x} xəta", "31"))
        if xb:
            hissə.append(b(f"{xb} xəbərdarlıq", "33"))
        return ", ".join(hissə)

    def çap(self, axın=None, rəngli: bool | None = None) -> None:
        axın = axın or sys.stderr
        h = self.hesabat(rəngli)
        if h:
            print(h, file=axın)
            print(file=axın)
        print(self.xülasə(rəngli), file=axın)


# ═══════════════════════════════════════════════════════════════════════
#  Xəta kodları — mesaj kataloqu
# ═══════════════════════════════════════════════════════════════════════

MESAJLAR: dict[str, str] = {
    # Leksik
    "ALQ-L001": "Fayl UTF-8 kodlaşdırmasında deyil",
    "ALQ-L002": "Tanınmayan simvol",
    "ALQ-L003": "Bağlanmamış mətn literalı",
    "ALQ-L004": "Bağlanmamış şərh bloku",
    "ALQ-L005": "Yanlış qaçış ardıcıllığı",
    "ALQ-L006": "Yanlış ədəd literalı",
    "ALQ-L007": "Ədəd diapazondan kənardır",
    "ALQ-L008": "Yanlış Unicode kod nöqtəsi",
    "ALQ-L009": "İdentifikator rəqəmlə başlaya bilməz",
    "ALQ-L010": "Açar söz identifikator kimi istifadə edilə bilməz",
    "ALQ-L011": "Bağlanmamış interpolyasiya",
    "ALQ-L012": "Tabulyasiya və boşluq qarışdırılıb",
    "ALQ-L013": "Yanlış format spesifikatoru",
    "ALQ-L014": "Homoqlif simvol aşkarlandı",
    "ALQ-L015": "Sətir sonunda artıq boşluq",
    "ALQ-L016": "Gələcək versiyalar üçün ehtiyatda saxlanılan söz",
    "ALQ-L017": "Bağlanmamış simvol literalı",
    "ALQ-L020": "ASCII açar söz istifadə olunub",
}


def mesaj(kod: str) -> str:
    return MESAJLAR.get(kod, "Naməlum xəta")
