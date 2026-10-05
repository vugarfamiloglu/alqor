"""
Alqor — Mənbə faylının oxunması və hazırlanması.

Lekser mətni görməzdən əvvəl beş mərhələ:

  1. UTF-8 dekodlaşdırma        → ALQ-L001
  2. BOM-un atılması
  3. NFC normalizasiya          (s+̧ → ş,  g+̆ → ğ,  o+̈ → ö)
  4. Sətir sonlarının LF-ə çevrilməsi
  5. Homoqlif düzəlişi          → ALQ-L014 xəbərdarlıqları

Bundan sonra sətir/sütun xəritəsi qurulur.
"""

from __future__ import annotations
import unicodedata
from pathlib import Path

from . import homoqlif
from .token import Yer
from .xeta import Diaqnostika, Səviyyə, XətaToplayıcı, mesaj

BOM = "﻿"


class Mənbə:
    """Hazırlanmış mənbə mətni + mövqe xəritəsi."""

    __slots__ = ("ad", "mətn", "yol", "_sətir_başları", "homoqliflər")

    def __init__(self, ad: str, mətn: str, yol: Path | None = None,
                 homoqliflər: list[homoqlif.Tapıntı] | None = None):
        self.ad = ad
        self.mətn = mətn
        self.yol = yol
        self.homoqliflər = homoqliflər or []
        self._sətir_başları = _sətir_başları_qur(mətn)

    # ── Yaradıcılar ───────────────────────────────────────────────────

    @classmethod
    def mətndən(cls, mətn: str, ad: str = "<yaddaş>",
                toplayıcı: XətaToplayıcı | None = None) -> "Mənbə":
        hazır, tapıntılar = hazırla(mətn)
        m = cls(ad, hazır, None, tapıntılar)
        if toplayıcı is not None:
            m.homoqlif_xəbərdarlıqları(toplayıcı)
        return m

    @classmethod
    def fayldan(cls, yol: str | Path,
                toplayıcı: XətaToplayıcı) -> "Mənbə | None":
        """
        Faylı oxuyur. UTF-8 deyilsə ALQ-L001 verir və None qaytarır.
        """
        p = Path(yol)
        try:
            xam = p.read_bytes()
        except FileNotFoundError:
            toplayıcı.xəta("ALQ-R009", f'"{p}" faylı tapılmadı')
            return None
        except PermissionError:
            toplayıcı.xəta("ALQ-R012", f'"{p}" faylını oxumaq icazəsi yoxdur')
            return None

        try:
            mətn = xam.decode("utf-8")
        except UnicodeDecodeError as x:
            toplayıcı.xəta(
                "ALQ-L001", mesaj("ALQ-L001"), None, "",
                f"bayt mövqeyi {x.start}-də yanlış UTF-8 ardıcıllığı var",
                "faylı UTF-8-ə çevirin: "
                f"iconv -f WINDOWS-1254 -t UTF-8 {p.name} -o {p.name}.yeni",
                "redaktorunuzda standart kodlaşdırmanı UTF-8 edin",
            )
            return None

        hazır, tapıntılar = hazırla(mətn)
        m = cls(p.name, hazır, p, tapıntılar)
        m.homoqlif_xəbərdarlıqları(toplayıcı)
        return m

    # ── Homoqlif xəbərdarlıqları ──────────────────────────────────────

    def homoqlif_xəbərdarlıqları(self, toplayıcı: XətaToplayıcı) -> None:
        for t in self.homoqliflər:
            toplayıcı.xəbərdarlıq(
                "ALQ-L014", mesaj("ALQ-L014"),
                Yer(self, t.mövqe, 1 if t.əvəz else 0),
                t.mesaj(),
                "avtomatik düzəldildi — mənbə faylı dəyişməyib",
                "faylı həmişəlik düzəltmək: alqorfmt --homoqlif-düzəlt .",
            )

    # ── Mövqe xəritəsi ────────────────────────────────────────────────

    @property
    def sətir_sayı(self) -> int:
        return len(self._sətir_başları)

    @property
    def uzunluq(self) -> int:
        return len(self.mətn)

    def sətir_sütun(self, mövqe: int) -> tuple[int, int]:
        """Simvol indeksindən (sətir, sütun) — ikisi də 1-dən başlayır."""
        mövqe = max(0, min(mövqe, len(self.mətn)))
        from bisect import bisect_right
        i = bisect_right(self._sətir_başları, mövqe) - 1
        return i + 1, mövqe - self._sətir_başları[i] + 1

    def mövqe(self, sətir: int, sütun: int) -> int:
        """(sətir, sütun) → simvol indeksi."""
        if not 1 <= sətir <= self.sətir_sayı:
            return 0
        return self._sətir_başları[sətir - 1] + (sütun - 1)

    def sətir_mətni(self, sətir: int) -> str:
        if not 1 <= sətir <= self.sətir_sayı:
            return ""
        b = self._sətir_başları[sətir - 1]
        s = (self._sətir_başları[sətir] - 1
             if sətir < self.sətir_sayı else len(self.mətn))
        return self.mətn[b:s].rstrip("\n")

    def parça(self, yer: Yer) -> str:
        return self.mətn[yer.başlanğıc:yer.son]

    def yer(self, başlanğıc: int, uzunluq: int = 1) -> Yer:
        return Yer(self, başlanğıc, uzunluq)

    def __repr__(self) -> str:
        return (f"Mənbə({self.ad!r}, {self.sətir_sayı} sətir, "
                f"{len(self.mətn)} simvol)")


# ═══════════════════════════════════════════════════════════════════════
#  Hazırlama mərhələləri
# ═══════════════════════════════════════════════════════════════════════

def hazırla(mətn: str) -> tuple[str, list[homoqlif.Tapıntı]]:
    """
    Xam mətni lekserə hazır vəziyyətə gətirir.

    Qaytarır: (hazır mətn, homoqlif tapıntıları)
    """
    # 1. BOM
    if mətn.startswith(BOM):
        mətn = mətn[1:]

    # 2. NFC — parçalanmış hərfləri birləşdirir
    #    Qeyd: ə (U+0259) parçalanmır, ona görə `ä` → `ə` NFC-nin işi deyil,
    #    homoqlif modulunun işidir.
    if not unicodedata.is_normalized("NFC", mətn):
        mətn = unicodedata.normalize("NFC", mətn)

    # 3. Sətir sonları
    if "\r" in mətn:
        mətn = mətn.replace("\r\n", "\n").replace("\r", "\n")

    # 4. Homoqliflər
    #    Direktiv leksərdən ƏVVƏL yoxlanılır, çünki düzəliş burada baş verir.
    if _homoqlif_söndürülüb(mətn):
        return mətn, []
    mətn, tapıntılar = homoqlif.düzəlt(mətn)

    return mətn, tapıntılar


def _homoqlif_söndürülüb(mətn: str) -> bool:
    """`// alqor: homoqlif-yoxlama söndür` direktivini axtarır."""
    baş = mətn.find("alqor:")
    while baş != -1:
        sətir_sonu = mətn.find("\n", baş)
        sətir = mətn[baş:sətir_sonu if sətir_sonu != -1 else len(mətn)]
        sadə = (sətir.replace("ə", "e").replace("ö", "o")
                     .replace("ü", "u").replace("ğ", "g"))
        if "homoqlif" in sadə and "sondur" in sadə:
            return True
        baş = mətn.find("alqor:", baş + 6)
    return False


def _sətir_başları_qur(mətn: str) -> list[int]:
    başlar = [0]
    yer = mətn.find("\n")
    while yer != -1:
        başlar.append(yer + 1)
        yer = mətn.find("\n", yer + 1)
    return başlar
