"""
Alqor — Korutinlər: tənbəl generatorlar və asinxron icra.

## Problem

Ağac gəzən interpretator `ver` ifadəsinə çatanda icranı DAYANDIRIB
dəyəri istifadəçiyə verməli, sonra həmin yerdən davam etməlidir.
Python-un `yield`-i bunu yalnız generator funksiyası daxilində verir —
bizim icraçımız isə adi rekursiv funksiyalar zənciridir.

## Həll

Gövdə ayrıca **sapda** işlədilir və iki hadisə ilə ciddi növbələşmə
qurulur:

    istehlakçı: `davam` siqnalını ver → `hazır` siqnalını gözlə → dəyəri al
    istehsalçı: dəyəri yaz → `hazır` siqnalını ver → `davam` siqnalını gözlə

Hər an YALNIZ BİR sap işləyir, ona görə interpretatorun vəziyyəti
paralel dəyişdirilmir — bu, sapla emulyasiya edilmiş korutindir, həqiqi
paralellik deyil.

Nəticə: sonsuz generatorlar işləyir.

    generator funksiya fibonaççi() -> tam
        dəyişən a = 0, b = 1
        həmişə
            ver a
            a, b = b, a + b
        son
    son
"""

from __future__ import annotations
import threading
from typing import Any, Callable

GÖZLƏMƏ_HƏDDİ = 300.0          # saniyə — ilişməyə qarşı qoruyucu


class _Dayandır(BaseException):
    """Korutin ləğv ediləndə gövdəyə atılır."""


# ═══════════════════════════════════════════════════════════════════════
#  Korutin
# ═══════════════════════════════════════════════════════════════════════

class Korutin:
    """
    Sap əsaslı korutin. `gövdə(ver)` çağırılır; `ver(dəyər)` icranı
    dayandırıb dəyəri istehlakçıya verir.
    """

    __slots__ = ("_gövdə", "_dəyər", "_hazır", "_davam", "_bitdi",
                 "_xəta", "_başladı", "_sap", "_ləğv", "ad")

    def __init__(self, gövdə: Callable[[Callable[[Any], None]], None],
                 ad: str = "<generator>"):
        self._gövdə = gövdə
        self.ad = ad
        self._dəyər: Any = None
        self._hazır = threading.Event()
        self._davam = threading.Event()
        self._bitdi = False
        self._xəta: BaseException | None = None
        self._başladı = False
        self._ləğv = False
        self._sap: threading.Thread | None = None

    # ── İstehsalçı tərəfi ─────────────────────────────────────────────

    def _işlə(self) -> None:
        try:
            self._gövdə(self._ver)
        except _Dayandır:
            pass
        except BaseException as x:          # noqa: BLE001
            self._xəta = x
        finally:
            self._bitdi = True
            self._hazır.set()

    def _ver(self, dəyər: Any) -> None:
        self._dəyər = dəyər
        self._hazır.set()
        if not self._davam.wait(GÖZLƏMƏ_HƏDDİ):
            raise _Dayandır()
        self._davam.clear()
        if self._ləğv:
            raise _Dayandır()

    # ── İstehlakçı tərəfi ─────────────────────────────────────────────

    def növbəti(self) -> Any:
        """Növbəti dəyəri qaytarır. Bitibsə `StopIteration` atır."""
        if self._bitdi:
            self._xətanı_at()
            raise StopIteration

        if not self._başladı:
            self._başladı = True
            self._sap = threading.Thread(target=self._işlə, daemon=True,
                                         name=f"alqor-{self.ad}")
            self._sap.start()
        else:
            self._davam.set()

        if not self._hazır.wait(GÖZLƏMƏ_HƏDDİ):
            raise TimeoutError(
                f"`{self.ad}` generatoru {GÖZLƏMƏ_HƏDDİ:.0f} saniyə "
                "cavab vermədi")
        self._hazır.clear()

        self._xətanı_at()
        if self._bitdi:
            raise StopIteration
        return self._dəyər

    def _xətanı_at(self) -> None:
        if self._xəta is not None:
            x, self._xəta = self._xəta, None
            raise x

    def bağla(self) -> None:
        """Korutini ləğv edir — sap dayanır."""
        if self._bitdi or not self._başladı:
            self._bitdi = True
            return
        self._ləğv = True
        self._davam.set()

    @property
    def bitdimi(self) -> bool:
        return self._bitdi

    def __iter__(self):
        return self

    def __next__(self):
        return self.növbəti()


# ═══════════════════════════════════════════════════════════════════════
#  Gələcək (asinxron nəticə)
# ═══════════════════════════════════════════════════════════════════════

class Gələcək:
    """
    `asinxron funksiya` çağırışının nəticəsi.

    Tənbəldir: gövdə yalnız `gözlə` (və ya `paralel`) ilə işə düşür.
    `paralel(...)` bir neçə `Gələcək`-i ayrı saplarda işlədir — orada
    HƏQİQİ paralellik var (giriş-çıxış gözləməsi üçün faydalı).
    """

    __slots__ = ("_işləyici", "_dəyər", "_xəta", "_bitdi", "_kilid",
                 "_sap", "ad")

    def __init__(self, işləyici: Callable[[], Any],
                 ad: str = "<asinxron>"):
        self._işləyici = işləyici
        self.ad = ad
        self._dəyər: Any = None
        self._xəta: BaseException | None = None
        self._bitdi = False
        self._kilid = threading.Lock()
        self._sap: threading.Thread | None = None

    # ── Sinxron həll ──────────────────────────────────────────────────

    def al(self, vaxt_limiti: float | None = None) -> Any:
        """Nəticəni qaytarır; lazım gələrsə gövdəni işlədir."""
        if self._sap is not None:
            self._sap.join(vaxt_limiti)
            if self._sap.is_alive():
                raise TimeoutError(f"`{self.ad}` vaxt limitini aşdı")
        else:
            with self._kilid:
                if not self._bitdi:
                    self._işlət()
        if self._xəta is not None:
            raise self._xəta
        return self._dəyər

    def _işlət(self) -> None:
        try:
            self._dəyər = self._işləyici()
        except BaseException as x:          # noqa: BLE001
            self._xəta = x
        finally:
            self._bitdi = True

    # ── Paralel başlatma ──────────────────────────────────────────────

    def başlat(self) -> "Gələcək":
        """Gövdəni fon sapında işə salır (paralel icra üçün)."""
        with self._kilid:
            if self._sap is None and not self._bitdi:
                self._sap = threading.Thread(
                    target=self._fonda_işlət, daemon=True,
                    name=f"alqor-{self.ad}")
                _İŞLƏYƏN_SAPLAR.add(self._sap)
                self._sap.start()
        return self

    def _fonda_işlət(self) -> None:
        try:
            self._işlət()
        finally:
            _İŞLƏYƏN_SAPLAR.discard(threading.current_thread())

    @property
    def bitdimi(self) -> bool:
        if self._sap is not None:
            return not self._sap.is_alive()
        return self._bitdi

    @property
    def uğurludurmu(self) -> bool:
        return self._bitdi and self._xəta is None

    def xəta_al(self) -> BaseException | None:
        return self._xəta

    def __repr__(self) -> str:
        vəziyyət = "bitib" if self.bitdimi else "gözləyir"
        return f"<gələcək {self.ad} ({vəziyyət})>"


# Fonda işləyən `Gələcək` sapları — kanal dalanını aşkarlamaq üçün
_İŞLƏYƏN_SAPLAR: set[threading.Thread] = set()


def _başqa_sap_işləyir() -> bool:
    cari = threading.current_thread()
    return any(s is not cari and s.is_alive() for s in list(_İŞLƏYƏN_SAPLAR))


# ═══════════════════════════════════════════════════════════════════════
#  Kanal (spes. § 9.13)
# ═══════════════════════════════════════════════════════════════════════

class Kanal:
    """
    Saplar və aktyorlar arasında mesaj növbəsi (FIFO).

        dəyişən k = Kanal()            // və ya yeni Kanal[tam](tutum: 10)
        k.göndər(5)
        yaz(k.al())
        k.bağla()
        hər x üçün k içində ... son    // bağlanıb boşalana qədər

    Boş kanaldan oxuyan sap göndərən gələnə qədər gözləyir. Göndərə biləcək
    başqa sap yoxdursa — dalan (`ALQ-R018`).
    """

    ALQOR_TİP_ADI = "Kanal"

    def __init__(self, tutum: int | None = None):
        from collections import deque
        self._növbə: Any = deque()
        self._bağlı = False
        self._şərt = threading.Condition()
        self.tutum = tutum

    def göndər(self, x: Any) -> None:
        with self._şərt:
            if self._bağlı:
                raise _xəta("KanalXətası", "bağlanmış kanala göndərmək olmaz",
                            "ALQ-R019")
            # Tutum doludursa göndərən sap oxuyanı gözləyir (yalnız
            # başqa sap oxuya bilərsə — əks halda növbə böyüyür)
            while (self.tutum is not None and len(self._növbə) >= self.tutum
                   and threading.current_thread() is not
                   threading.main_thread()):
                if not self._şərt.wait(0.05) and not _başqa_sap_işləyir() \
                        and not threading.main_thread().is_alive():
                    break
            self._növbə.append(x)
            self._şərt.notify_all()

    def al(self) -> Any:
        """Növbəti dəyər; kanal bağlanıb boşdursa `boş`."""
        var, x = self._al()
        return x if var else None

    def _al(self) -> tuple[bool, Any]:
        with self._şərt:
            while not self._növbə:
                if self._bağlı:
                    return False, None
                if not _başqa_sap_işləyir() and \
                        threading.current_thread() is threading.main_thread():
                    raise _xəta("DalanXətası",
                                "kanal boşdur və ona göndərən yoxdur — dalan",
                                "ALQ-R018")
                self._şərt.wait(0.05)
            x = self._növbə.popleft()
            self._şərt.notify_all()
            return True, x

    def cəhdAl(self) -> Any:
        with self._şərt:
            if self._növbə:
                x = self._növbə.popleft()
                self._şərt.notify_all()
                return x
            return None

    def bağla(self) -> None:
        with self._şərt:
            self._bağlı = True
            self._şərt.notify_all()

    def alqor_uzunluq(self) -> int:
        return len(self._növbə)

    @staticmethod
    def alqor_iterasiya(k: "Kanal", yer=None):
        while True:
            var, x = k._al()
            if not var:
                return
            yield x

    def __repr__(self) -> str:
        return (f"<kanal {len(self._növbə)} element"
                f"{', bağlı' if self._bağlı else ''}>")

    ALQOR_METODLARI = {
        "göndər": lambda i, k, x: k.göndər(x),
        "al": lambda i, k: k.al(),
        "cəhdAl": lambda i, k: k.cəhdAl(),
        "bağla": lambda i, k: k.bağla(),
        "bağlıdır": lambda i, k: k._bağlı,
        "boşdur": lambda i, k: not k._növbə,
        "uzunluq": lambda i, k: len(k._növbə),
    }


def _xəta(tip: str, mesaj: str, kod: str):
    from .deyerler import AlqorXəta
    return AlqorXəta(tip, mesaj, None, kod)


# ═══════════════════════════════════════════════════════════════════════
#  Aktyor poçtu (spes. § 9.12)
# ═══════════════════════════════════════════════════════════════════════

class Mesaj:
    """Aktyora göndərilmiş metod çağırışı."""
    __slots__ = ("metod", "arqumentlər", "adlı", "yer", "bitdi",
                 "nəticə", "xəta", "gözlənildi")

    def __init__(self, metod, arqumentlər, adlı, yer):
        self.metod, self.arqumentlər, self.adlı, self.yer = \
            metod, arqumentlər, adlı, yer
        self.bitdi = False
        self.nəticə: Any = None
        self.xəta: BaseException | None = None
        self.gözlənildi = False


# ═══════════════════════════════════════════════════════════════════════
#  Ləğv nişanı
# ═══════════════════════════════════════════════════════════════════════

class LəğvNişanı:
    """
    Uzun əməliyyatları ləğv etmək üçün.

        dəyişən n = yeni LəğvNişanı()
        ...
        n.yoxla()        // ləğv olunubsa LəğvXətası atır
        n.ləğvEt()
    """

    __slots__ = ("_hadisə", "_taymer")

    def __init__(self, saniyə: float | None = None):
        self._hadisə = threading.Event()
        self._taymer: threading.Timer | None = None
        if saniyə is not None:
            self._taymer = threading.Timer(saniyə, self._hadisə.set)
            self._taymer.daemon = True
            self._taymer.start()

    def ləğvEt(self) -> None:
        self._hadisə.set()
        if self._taymer is not None:
            self._taymer.cancel()

    @property
    def ləğvolunub(self) -> bool:
        return self._hadisə.is_set()

    def gözlə(self, saniyə: float | None = None) -> bool:
        return self._hadisə.wait(saniyə)

    def __repr__(self) -> str:
        return (f"<ləğvNişanı "
                f"{'ləğv olunub' if self.ləğvolunub else 'aktiv'}>")
