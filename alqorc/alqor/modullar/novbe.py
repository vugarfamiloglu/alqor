"""
`növbə` — fon iş növbəsi: işçi sapları, prioritet, gecikmə, təkrar
cəhdlər (§ 10.17).

    gətir növbə

    dəyişən n = növbə.yarat(işçilər: 4, cəhd: 3, gecikmə: 0.5)

    funksiya məktubGöndər(ünvan: mətn) -> mətn
        ...
        qaytar "göndərildi"
    son

    dəyişən iş = n.göndər(məktubGöndər, "a@b.az")
    yaz(iş.nəticə())                 // gözləyir: "göndərildi"

    // seçimlərlə: prioritet (böyük → əvvəl), gecikmə (saniyə), cəhd
    n.planla(hesabat, arqumentlər: [2026], prioritet: 10, gecikmə: 60)

    n.bitdikdə((iş) => yaz("bitdi: {iş.id()}"))
    n.uğursuzOlduqda((iş, xəta) => yaz("xəta: {xəta}"))
    n.gözlə()                         // bütün işlər bitənə qədər
    n.dayandır()

Uğursuz iş `cəhd` sayına çatana qədər yenidən növbəyə düşür; hər dəfə
gözləmə ikiqat artır (`gecikmə`, 2×`gecikmə`, 4×`gecikmə` …).

İş vəziyyətləri: "gözləyir", "işləyir", "bitdi", "uğursuz", "ləğv".
`asinxron funksiya` da göndərmək olar — nəticəsi gözlənilir.
"""

from __future__ import annotations

import heapq
import itertools
import threading
import time
from typing import Any

from ..deyerler import AlqorXəta, Daxili
from ._yardim import çağır, funksiya_tələb, müsbət_ədəd


def _xəta(mesaj: str, tip: str = "NövbəXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _tam(x: Any, ad: str, minimum: int = 0) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or x < minimum:
        raise _xəta(f"`{ad}` ən azı {minimum} olan tam ədəd olmalıdır, "
                    f"`{x!r}` gəlib", "ArqumentXətası")
    return x


class İş:
    ALQOR_TİP_ADI = "iş"

    def __init__(self, növbə: "Növbə", nömrə: int, f: Any, arq: list,
                 adlı: dict, prioritet: int, cəhd: int, ad: str):
        self.növbə = növbə
        self.nömrə = nömrə
        self.f, self.arq, self.adlı = f, arq, adlı
        self.prioritet = prioritet
        self.maks_cəhd = cəhd
        self.ad = ad
        self.cəhdlər = 0
        self.vəziyyət = "gözləyir"
        self.dəyər: Any = None
        self.xəta: BaseException | None = None
        self.hadisə = threading.Event()
        self.başladı: float | None = None
        self.bitdi: float | None = None

    def __repr__(self) -> str:
        return f"<iş #{self.nömrə} {self.ad} ({self.vəziyyət})>"

    def nəticə(self, vaxt_limiti: Any = None) -> Any:
        t = None if vaxt_limiti is None else müsbət_ədəd(
            vaxt_limiti, "vaxtLimiti", sıfır=True)
        if not self.hadisə.wait(t):
            raise AlqorXəta("VaxtXətası",
                            f"iş #{self.nömrə} vaxt limitində bitmədi",
                            None, "ALQ-R011")
        if self.vəziyyət == "ləğv":
            raise _xəta(f"iş #{self.nömrə} ləğv edilib")
        if self.xəta is not None:
            raise self.xəta
        return self.dəyər

    def xəta_mətni(self) -> str | None:
        if self.xəta is None:
            return None
        if isinstance(self.xəta, AlqorXəta):
            return f"{self.xəta.tip}: {self.xəta.mesaj}"
        return f"{type(self.xəta).__name__}: {self.xəta}"

    def ləğv_et(self) -> bool:
        return self.növbə._ləğv(self)

    def lüğət(self) -> dict:
        müddət = (round(self.bitdi - self.başladı, 4)
                  if self.bitdi and self.başladı else None)
        return {"id": self.nömrə, "ad": self.ad, "vəziyyət": self.vəziyyət,
                "cəhdlər": self.cəhdlər, "prioritet": self.prioritet,
                "xəta": self.xəta_mətni(), "müddət": müddət}


İş.ALQOR_METODLARI = {
    "id": lambda i, x: x.nömrə,
    "ad": lambda i, x: x.ad,
    "vəziyyət": lambda i, x: x.vəziyyət,
    "nəticə": lambda i, x, vaxtLimiti=None: x.nəticə(vaxtLimiti),
    "bitib": lambda i, x: x.hadisə.is_set(),
    "uğurlu": lambda i, x: x.vəziyyət == "bitdi",
    "xəta": lambda i, x: x.xəta_mətni(),
    "cəhdlər": lambda i, x: x.cəhdlər,
    "ləğvEt": lambda i, x: x.ləğv_et(),
    "lüğət": lambda i, x: x.lüğət(),
}


class Növbə:
    ALQOR_TİP_ADI = "növbə"

    def __init__(self, icraçı, işçilər: Any = 2, cəhd: Any = 1,
                 gecikmə: Any = 1.0, ad: Any = "növbə"):
        self.icraçı = icraçı
        self.işçi_sayı = _tam(işçilər, "işçilər", 1)
        self.cəhd = _tam(cəhd, "cəhd", 1)
        self.gecikmə = müsbət_ədəd(gecikmə, "gecikmə", sıfır=True)
        self.ad = str(ad)
        self._yığın: list = []               # (vaxt, -prioritet, sıra, iş)
        self._hazır: list = []               # (-prioritet, sıra, iş)
        self._sıra = itertools.count()
        self._nömrə = itertools.count(1)
        self._şərt = threading.Condition()
        self._işlər: dict[int, İş] = {}
        self._aktiv = 0
        self._dayanıb = False
        self._bitdikdə: list = []
        self._uğursuz: list = []
        self._saplar = [threading.Thread(target=self._işçi, daemon=True,
                                         name=f"alqor-{self.ad}-{i}")
                        for i in range(self.işçi_sayı)]
        for s in self._saplar:
            s.start()

    def __repr__(self) -> str:
        return f"<növbə {self.ad} ({self.işçi_sayı} işçi)>"

    # ── İş əlavə etmək ────────────────────────────────────────────────
    def planla(self, f: Any, arqumentlər: Any = None, adlı: Any = None,
               prioritet: Any = 0, gecikmə: Any = 0, cəhd: Any = None,
               ad: Any = None) -> İş:
        funksiya_tələb(f, "göndər")
        if self._dayanıb:
            raise _xəta("növbə dayandırılıb — yeni iş qəbul etmir")
        arq = list(arqumentlər or [])
        if adlı is not None and not isinstance(adlı, dict):
            raise _xəta("`adlı` lüğət olmalıdır", "TipXətası")
        if isinstance(prioritet, bool) or not isinstance(prioritet, int):
            raise _xəta("`prioritet` tam ədəd olmalıdır", "TipXətası")
        g = müsbət_ədəd(gecikmə, "gecikmə", sıfır=True)
        iş = İş(self, next(self._nömrə), f, arq, dict(adlı or {}),
                prioritet, self.cəhd if cəhd is None else _tam(cəhd, "cəhd",
                                                               1),
                str(ad) if ad is not None else getattr(f, "ad", "iş"))
        with self._şərt:
            self._işlər[iş.nömrə] = iş
            heapq.heappush(self._yığın, (time.monotonic() + g, -prioritet,
                                         next(self._sıra), iş))
            self._şərt.notify()
        return iş

    def göndər(self, f: Any, *arq: Any, **adlı: Any) -> İş:
        return self.planla(f, list(arq), adlı)

    # ── İşçi ──────────────────────────────────────────────────────────
    def _növbəti(self) -> İş | None:
        with self._şərt:
            while True:
                # Vaxtı çatanlar gecikmə yığınından hazır yığına keçir;
                # hazırlar arasında prioritet (sonra gəliş sırası) həlledir.
                indi = time.monotonic()
                while self._yığın and self._yığın[0][0] <= indi:
                    _, mp, sıra, iş = heapq.heappop(self._yığın)
                    heapq.heappush(self._hazır, (mp, sıra, iş))
                while self._hazır:
                    _, _, iş = heapq.heappop(self._hazır)
                    if iş.vəziyyət == "ləğv":
                        continue
                    iş.vəziyyət = "işləyir"
                    self._aktiv += 1
                    return iş
                if self._dayanıb and not self._yığın:
                    return None
                gözlə = self._yığın[0][0] - indi if self._yığın else 1.0
                self._şərt.wait(min(gözlə, 1.0))

    def _işçi(self) -> None:
        while True:
            iş = self._növbəti()
            if iş is None:
                return
            iş.cəhdlər += 1
            iş.başladı = iş.başladı or time.monotonic()
            try:
                iş.dəyər = çağır(self.icraçı, iş.f, *iş.arq, **iş.adlı)
                iş.xəta = None
                iş.vəziyyət = "bitdi"
            except BaseException as x:            # noqa: BLE001
                iş.xəta = x
                if iş.cəhdlər < iş.maks_cəhd and not self._dayanıb:
                    g = self.gecikmə * (2 ** (iş.cəhdlər - 1))
                    with self._şərt:
                        iş.vəziyyət = "gözləyir"
                        heapq.heappush(self._yığın, (
                            time.monotonic() + g, -iş.prioritet,
                            next(self._sıra), iş))
                        self._aktiv -= 1
                        self._şərt.notify_all()
                    continue
                iş.vəziyyət = "uğursuz"
            iş.bitdi = time.monotonic()
            self._geri_çağır(iş)
            with self._şərt:
                self._aktiv -= 1
                iş.hadisə.set()
                self._şərt.notify_all()

    def _geri_çağır(self, iş: İş) -> None:
        siyahı = self._bitdikdə if iş.vəziyyət == "bitdi" else self._uğursuz
        for f in list(siyahı):
            try:
                if iş.vəziyyət == "bitdi":
                    çağır(self.icraçı, f, iş)
                else:
                    çağır(self.icraçı, f, iş, iş.xəta_mətni())
            except BaseException as x:            # noqa: BLE001
                # geri çağırışın xətası işi pozmasın, amma gizlənməsin
                import sys
                print(f"⚠ növbə `{self.ad}`: geri çağırış xətası: {x}",
                      file=sys.stderr)

    def _ləğv(self, iş: İş) -> bool:
        with self._şərt:
            if iş.vəziyyət != "gözləyir":
                return False
            iş.vəziyyət = "ləğv"
            iş.bitdi = time.monotonic()
            iş.hadisə.set()
            self._şərt.notify_all()
            return True

    # ── İdarə ─────────────────────────────────────────────────────────
    def gözlə(self, vaxt_limiti: Any = None) -> bool:
        son = None if vaxt_limiti is None else \
            time.monotonic() + müsbət_ədəd(vaxt_limiti, "vaxtLimiti",
                                           sıfır=True)
        with self._şərt:
            while any(not x.hadisə.is_set() for x in self._işlər.values()):
                if son is not None:
                    qalan = son - time.monotonic()
                    if qalan <= 0:
                        return False
                    self._şərt.wait(min(qalan, 0.5))
                else:
                    self._şərt.wait(0.5)
        return True

    def dayandır(self, gözlə: Any = True) -> None:
        """Yeni iş qəbul etmir. `gözlə: doğru` — növbədəkilər bitir;
        `yanlış` — gözləyən işlər ləğv olunur."""
        with self._şərt:
            self._dayanıb = True
            if not gözlə:
                for *_, iş in self._yığın + self._hazır:
                    if iş.vəziyyət == "gözləyir":
                        iş.vəziyyət = "ləğv"
                        iş.hadisə.set()
                self._yığın.clear()
                self._hazır.clear()
            self._şərt.notify_all()
        if gözlə:
            for s in self._saplar:
                s.join()

    def say(self) -> dict:
        n = {"gözləyir": 0, "işləyir": 0, "bitdi": 0, "uğursuz": 0,
             "ləğv": 0}
        with self._şərt:
            for x in self._işlər.values():
                n[x.vəziyyət] += 1
        return n

    def təmizlə(self) -> int:
        """Bitmiş işləri yaddaşdan çıxarır (uzun işləyən növbələr üçün)."""
        with self._şərt:
            bitmiş = [k for k, x in self._işlər.items() if x.hadisə.is_set()]
            for k in bitmiş:
                del self._işlər[k]
            return len(bitmiş)


Növbə.ALQOR_METODLARI = {
    "göndər": lambda i, n, f, *a, **k: n.göndər(f, *a, **k),
    "planla": lambda i, n, f, arqumentlər=None, adlı=None, prioritet=0,
    gecikmə=0, cəhd=None, ad=None: n.planla(f, arqumentlər, adlı, prioritet,
                                             gecikmə, cəhd, ad),
    "çevir": lambda i, n, f, siyahı: [x.nəticə() for x in
                                       [n.göndər(f, e) for e in siyahı]],
    "gözlə": lambda i, n, vaxtLimiti=None: n.gözlə(vaxtLimiti),
    "dayandır": lambda i, n, gözlə=True: n.dayandır(gözlə),
    "say": lambda i, n: n.say(),
    "işlər": lambda i, n: list(n._işlər.values()),
    "təmizlə": lambda i, n: n.təmizlə(),
    "bitdikdə": lambda i, n, f: n._bitdikdə.append(
        funksiya_tələb(f, "bitdikdə")) and None,
    "uğursuzOlduqda": lambda i, n, f: n._uğursuz.append(
        funksiya_tələb(f, "uğursuzOlduqda")) and None,
    "işçilər": lambda i, n: n.işçi_sayı,
}


def qur(icraçı) -> dict[str, Any]:
    return {
        "yarat": Daxili("yarat", lambda işçilər=2, cəhd=1, gecikmə=1.0,
                        ad="növbə": Növbə(icraçı, işçilər, cəhd, gecikmə,
                                          ad), 0, 4),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    return {"yarat": F(T.TAM, T.TAM, T.ONLUQ, T.MƏTN,
                       qaytarır=T.Sadə("növbə"), standart=4)}


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    m, e, o, i, b, h = (T.MƏTN, T.İSTƏNİLƏN, T.ONLUQ, T.TAM, T.MƏNTİQ,
                        T.HEÇ)
    İ = T.Sadə("iş")
    return {
        "növbə": {
            "göndər": Fsərbəst(İ),
            "planla": F(e, T.Siyahı(), T.Lüğət(m, e), i, o, i, m,
                        qaytarır=İ, standart=6),
            "çevir": F(e, T.Siyahı(), qaytarır=T.Siyahı()),
            "gözlə": F(o, qaytarır=b, standart=1),
            "dayandır": F(b, qaytarır=h, standart=1),
            "say": F(qaytarır=T.Lüğət(m, i)),
            "işlər": F(qaytarır=T.Siyahı(İ)),
            "təmizlə": F(qaytarır=i),
            "bitdikdə": F(e, qaytarır=h),
            "uğursuzOlduqda": F(e, qaytarır=h),
            "işçilər": F(qaytarır=i),
        },
        "iş": {
            "id": F(qaytarır=i), "ad": F(qaytarır=m),
            "vəziyyət": F(qaytarır=m),
            "nəticə": F(o, qaytarır=e, standart=1),
            "bitib": F(qaytarır=b), "uğurlu": F(qaytarır=b),
            "xəta": F(qaytarır=T.ixtiyari(m)),
            "cəhdlər": F(qaytarır=i), "ləğvEt": F(qaytarır=b),
            "lüğət": F(qaytarır=T.Lüğət(m, e)),
        },
    }
