"""
`planlayıcı` — cron ifadələri və vaxtlı tapşırıqlar (§ 10.17).

    gətir planlayıcı

    dəyişən c = planlayıcı.cron("*/15 9-18 * * b.e-c")   // iş günləri, 15 dəq.
    yaz(c.növbəti())                                    // "2026-10-07T10:15:00"
    yaz(c.növbətilər(3, "2026-01-01T00:00:00"))
    yaz(c.izah())                                       // azərbaycanca təsvir

    dəyişən p = planlayıcı.yarat()
    p.cron("0 9 * * *", hesabatGöndər, ad: "səhər hesabatı")
    p.hər(30, yoxla)                    // hər 30 saniyədən bir
    p.sonra(5, () => yaz("5 saniyə keçdi"))
    p.başlat()                          // fon sapında
    ...
    p.dayandır()

    // və ya ön planda: p.işlət(müddət: 60)   — 60 saniyə işləyir

Cron formatı (5 sahə): `dəqiqə saat gün ay həftəGünü`
  `*`  hamısı · `5` · `1-5` · `*/10` · `1-30/5` · `1,15,30`
  Aylar: 1–12 və ya `yan fev mar apr may iyn iyl avq sen okt noy dek`
         (ingiliscə `jan … dec` də olar)
  Həftə günləri: 0–7 (0 və 7 = bazar) və ya `b.e ç.a ç c.a c ş b`
         (ingiliscə `mon … sun` də olar)
  Qısaltmalar: `@illik` `@aylıq` `@həftəlik` `@gündəlik` `@saatlıq`
         (və `@yearly @monthly @weekly @daily @hourly`)

Gün və həftə günü HƏR İKİSİ verilsə (heç biri `*` deyilsə), uyğunluq
klassik cron kimi "və ya" ilə yoxlanır. Vaxtlar yerli saat qurşağındadır;
ISO mətnləri (`"2026-10-07T09:30:00"`) qəbul edilir və qaytarılır.
"""

from __future__ import annotations

import itertools
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any

from ..deyerler import AlqorXəta, Daxili
from ._yardim import çağır, funksiya_tələb, müsbət_ədəd


def _xəta(mesaj: str, tip: str = "PlanlayıcıXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


AYLAR = {"yan": 1, "fev": 2, "mar": 3, "apr": 4, "may": 5, "iyn": 6,
         "iyl": 7, "avq": 8, "sen": 9, "okt": 10, "noy": 11, "dek": 12,
         "jan": 1, "feb": 2, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
         "oct": 10, "nov": 11, "dec": 12}
GÜNLƏR = {"b.e": 1, "ç.a": 2, "ç": 3, "c.a": 4, "c": 5, "ş": 6, "b": 0,
          "be": 1, "ça": 2, "ca": 4,
          "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
          "sun": 0}
QISALTMALAR = {
    "@illik": "0 0 1 1 *", "@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *",
    "@aylıq": "0 0 1 * *", "@monthly": "0 0 1 * *",
    "@həftəlik": "0 0 * * 0", "@weekly": "0 0 * * 0",
    "@gündəlik": "0 0 * * *", "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@saatlıq": "0 * * * *", "@hourly": "0 * * * *",
}
_SAHƏLƏR = [("dəqiqə", 0, 59, {}), ("saat", 0, 23, {}),
            ("gün", 1, 31, {}), ("ay", 1, 12, AYLAR),
            ("həftəGünü", 0, 7, GÜNLƏR)]
_AY_ADLARI = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
              "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
_GÜN_ADLARI = ["bazar", "bazar ertəsi", "çərşənbə axşamı", "çərşənbə",
               "cümə axşamı", "cümə", "şənbə"]


def _ədəd(s: str, ad: str, adlar: dict, ifadə: str) -> int:
    t = s.strip().lower()
    if t in adlar:
        return adlar[t]
    if t.isdigit():
        return int(t)
    raise _xəta(f"cron `{ifadə}`: `{ad}` sahəsində `{s}` anlaşılmadı")


def _sahə(mətn: str, ad: str, a: int, b: int, adlar: dict,
          ifadə: str) -> tuple[set[int], bool]:
    """→ (qiymətlər, ulduzdur)"""
    n: set[int] = set()
    ulduz = mətn.strip() in ("*", "?")
    for hissə in mətn.split(","):
        hissə = hissə.strip()
        if not hissə:
            raise _xəta(f"cron `{ifadə}`: `{ad}` sahəsi boşdur")
        aralıq, _, addım_m = hissə.partition("/")
        addım = 1
        if addım_m:
            if not addım_m.isdigit() or int(addım_m) == 0:
                raise _xəta(f"cron `{ifadə}`: `/{addım_m}` addımı yanlışdır")
            addım = int(addım_m)
        if aralıq in ("*", "?"):
            başla, son = a, b
        elif "-" in aralıq and not aralıq.startswith("-"):
            x, _, y = aralıq.partition("-")
            başla, son = _ədəd(x, ad, adlar, ifadə), _ədəd(y, ad, adlar,
                                                          ifadə)
        else:
            başla = _ədəd(aralıq, ad, adlar, ifadə)
            son = b if addım_m else başla
        if not (a <= başla <= b and a <= son <= b):
            raise _xəta(f"cron `{ifadə}`: `{ad}` {a}–{b} arasında "
                        f"olmalıdır (`{hissə}`)")
        if başla > son:
            raise _xəta(f"cron `{ifadə}`: `{hissə}` aralığı tərsdir")
        n.update(range(başla, son + 1, addım))
    return n, ulduz


def vaxt_oxu(x: Any) -> datetime:
    if x is None:
        return datetime.now()
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return datetime.fromtimestamp(x)          # unix möhürü
    try:
        return datetime.fromisoformat(str(x).strip().replace(" ", "T")
                                      .rstrip("Z"))
    except ValueError:
        raise _xəta(f"`{x}` vaxt kimi oxunmadı — ISO formatı gözlənilir "
                    '("2026-10-07T09:30:00")')


def _iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S")


class Cron:
    ALQOR_TİP_ADI = "cron"

    def __init__(self, ifadə: Any):
        self.ifadə = str(ifadə).strip()
        m = QISALTMALAR.get(self.ifadə.lower(), self.ifadə)
        hissələr = m.split()
        if len(hissələr) != 5:
            raise _xəta(f"cron `{self.ifadə}`: 5 sahə gözlənilir "
                        "(dəqiqə saat gün ay həftəGünü), "
                        f"{len(hissələr)} verilib")
        dəyərlər = [_sahə(h, ad, a, b, adlar, self.ifadə)
                    for h, (ad, a, b, adlar) in zip(hissələr, _SAHƏLƏR)]
        (self.dəqiqə, _), (self.saat, _), (self.gün, gün_ulduz), \
            (self.ay, _), (hg, hg_ulduz) = dəyərlər
        self.həftə_günü = {0 if x == 7 else x for x in hg}
        self.gün_ulduz, self.hg_ulduz = gün_ulduz, hg_ulduz
        if not any(self._gün_mümkündür(a) for a in self.ay):
            raise _xəta(f"cron `{self.ifadə}`: heç vaxt baş vermir "
                        "(belə tarix yoxdur)")

    def _gün_mümkündür(self, ay: int) -> bool:
        # Yalnız "gün" verilib (həftə günü `*`): 31 fevral kimi tarix
        # heç vaxt gəlmir. Həftə günü verilibsə ("və ya") həmişə mümkündür.
        if self.gün_ulduz or not self.hg_ulduz:
            return True
        maks = 29 if ay == 2 else (30 if ay in (4, 6, 9, 11) else 31)
        return min(self.gün) <= maks

    def __repr__(self) -> str:
        return f"<cron {self.ifadə}>"

    def _gün_uyğun(self, t: datetime) -> bool:
        hg = (t.weekday() + 1) % 7                     # 0 = bazar
        g = t.day in self.gün
        h = hg in self.həftə_günü
        if self.gün_ulduz and self.hg_ulduz:
            return True
        if self.gün_ulduz:
            return h
        if self.hg_ulduz:
            return g
        return g or h

    def uyğundur(self, t: datetime) -> bool:
        return (t.minute in self.dəqiqə and t.hour in self.saat and
                t.month in self.ay and self._gün_uyğun(t))

    def növbəti(self, başla: datetime) -> datetime:
        t = başla.replace(second=0, microsecond=0) + timedelta(minutes=1)
        son = t + timedelta(days=366 * 8)
        while t < son:
            if t.month not in self.ay:
                il, ay = (t.year + 1, 1) if t.month == 12 else (
                    t.year, t.month + 1)
                t = datetime(il, ay, 1)
                continue
            if not self._gün_uyğun(t):
                t = datetime(t.year, t.month, t.day) + timedelta(days=1)
                continue
            if t.hour not in self.saat:
                t = datetime(t.year, t.month, t.day, t.hour) + \
                    timedelta(hours=1)
                continue
            if t.minute not in self.dəqiqə:
                t += timedelta(minutes=1)
                continue
            return t
        raise _xəta(f"cron `{self.ifadə}`: yaxın 8 ildə uyğun vaxt yoxdur")

    def izah(self) -> str:
        def siyahı(s: set[int], a: int, b: int, ad=None) -> str | None:
            if len(s) == b - a + 1:
                return None
            x = sorted(s)
            if ad is None:
                return ", ".join(str(e) for e in x)
            return ", ".join(ad(e) for e in x)
        hissələr = []
        dq = siyahı(self.dəqiqə, 0, 59)
        st = siyahı(self.saat, 0, 23)
        if dq is not None and st is not None and len(self.dəqiqə) == 1 \
                and len(self.saat) == 1:
            hissələr.append(f"saat {min(self.saat):02d}:"
                            f"{min(self.dəqiqə):02d}-da")
        else:
            hissələr.append("hər dəqiqə" if dq is None
                            else f"{dq}-ci dəqiqədə")
            if st is not None:
                hissələr.append(f"saat {st}")
        if not self.gün_ulduz:
            hissələr.append(f"ayın {siyahı(self.gün, 1, 31)}-də")
        if not self.hg_ulduz:
            hissələr.append(siyahı(self.həftə_günü, 0, 6,
                                   lambda e: _GÜN_ADLARI[e]) + " günləri")
        ay = siyahı(self.ay, 1, 12, lambda e: _AY_ADLARI[e - 1])
        if ay is not None:
            hissələr.append(f"{ay} aylarında")
        return ", ".join(hissələr)


Cron.ALQOR_METODLARI = {
    "növbəti": lambda i, c, başla=None: _iso(c.növbəti(vaxt_oxu(başla))),
    "növbətilər": lambda i, c, n, başla=None: _növbətilər(c, n, başla),
    "uyğundur": lambda i, c, t=None: c.uyğundur(vaxt_oxu(t)),
    "izah": lambda i, c: c.izah(),
    "ifadə": lambda i, c: c.ifadə,
}


def _növbətilər(c: Cron, n: Any, başla: Any) -> list[str]:
    if isinstance(n, bool) or not isinstance(n, int) or not 0 < n <= 10000:
        raise _xəta("`növbətilər` 1–10000 arası tam ədəd gözləyir")
    t, nəticə = vaxt_oxu(başla), []
    for _ in range(n):
        t = c.növbəti(t)
        nəticə.append(_iso(t))
    return nəticə


# ── Planlayıcı ────────────────────────────────────────────────────────

class Tapşırıq:
    ALQOR_TİP_ADI = "tapşırıq"

    def __init__(self, nömrə: int, ad: str, f: Any, növ: str,
                 cron: Cron | None = None, aralıq: float | None = None,
                 növbəti: float = 0.0, təkrar: bool = True,
                 üst_üstə: bool = False):
        self.nömrə, self.ad, self.f, self.növ = nömrə, ad, f, növ
        self.cron, self.aralıq = cron, aralıq
        self.növbəti_vaxt = növbəti          # unix saniyə
        self.təkrar = təkrar
        self.üst_üstə = üst_üstə
        self.say = 0
        self.son_xəta: str | None = None
        self.son_vaxt: float | None = None
        self.aktiv = True
        self.işləyir = False

    def __repr__(self) -> str:
        return f"<tapşırıq {self.ad}>"

    def lüğət(self) -> dict:
        return {"id": self.nömrə, "ad": self.ad, "növ": self.növ,
                "aktiv": self.aktiv, "say": self.say,
                "növbəti": _iso(datetime.fromtimestamp(self.növbəti_vaxt))
                if self.aktiv else None,
                "sonXəta": self.son_xəta}


Tapşırıq.ALQOR_METODLARI = {
    "id": lambda i, t: t.nömrə,
    "ad": lambda i, t: t.ad,
    "ləğvEt": lambda i, t: setattr(t, "aktiv", False),
    "aktivdir": lambda i, t: t.aktiv,
    "say": lambda i, t: t.say,
    "növbəti": lambda i, t: _iso(datetime.fromtimestamp(t.növbəti_vaxt))
    if t.aktiv else None,
    "sonXəta": lambda i, t: t.son_xəta,
    "lüğət": lambda i, t: t.lüğət(),
}


class Planlayıcı:
    ALQOR_TİP_ADI = "planlayıcı"

    def __init__(self, icraçı, saat: Any = None):
        self.icraçı = icraçı
        self._tapşırıqlar: list[Tapşırıq] = []
        self._şərt = threading.Condition()
        self._nömrə = itertools.count(1)
        self._dayan = False
        self._sap: threading.Thread | None = None
        self._işlər: list[threading.Thread] = []
        # Sınaqlar üçün: saat funksiyası (unix saniyə qaytarır)
        self._saat = saat or time.time

    def __repr__(self) -> str:
        return f"<planlayıcı {len(self._tapşırıqlar)} tapşırıq>"

    def _əlavə(self, t: Tapşırıq) -> Tapşırıq:
        with self._şərt:
            self._tapşırıqlar.append(t)
            self._şərt.notify_all()
        return t

    def cron(self, ifadə: Any, f: Any, ad: Any = None,
             üstÜstə: Any = False) -> Tapşırıq:
        funksiya_tələb(f, "cron")
        c = ifadə if isinstance(ifadə, Cron) else Cron(ifadə)
        n = c.növbəti(datetime.fromtimestamp(self._saat())).timestamp()
        return self._əlavə(Tapşırıq(next(self._nömrə),
                                    str(ad or getattr(f, "ad", "cron")), f,
                                    "cron", cron=c, növbəti=n,
                                    üst_üstə=bool(üstÜstə)))

    def hər(self, saniyə: Any, f: Any, ad: Any = None, dərhal: Any = False,
            üstÜstə: Any = False) -> Tapşırıq:
        funksiya_tələb(f, "hər")
        s = müsbət_ədəd(saniyə, "saniyə")
        return self._əlavə(Tapşırıq(
            next(self._nömrə), str(ad or getattr(f, "ad", "hər")), f, "hər",
            aralıq=s, növbəti=self._saat() + (0 if dərhal else s),
            üst_üstə=bool(üstÜstə)))

    def sonra(self, saniyə: Any, f: Any, ad: Any = None) -> Tapşırıq:
        funksiya_tələb(f, "sonra")
        s = müsbət_ədəd(saniyə, "saniyə", sıfır=True)
        return self._əlavə(Tapşırıq(
            next(self._nömrə), str(ad or getattr(f, "ad", "sonra")), f,
            "sonra", növbəti=self._saat() + s, təkrar=False))

    def vaxtında(self, vaxt: Any, f: Any, ad: Any = None) -> Tapşırıq:
        funksiya_tələb(f, "vaxtında")
        return self._əlavə(Tapşırıq(
            next(self._nömrə), str(ad or getattr(f, "ad", "vaxtında")), f,
            "vaxtında", növbəti=vaxt_oxu(vaxt).timestamp(), təkrar=False))

    # ── İcra ──────────────────────────────────────────────────────────
    def _icra_et(self, t: Tapşırıq) -> None:
        try:
            çağır(self.icraçı, t.f)
            t.son_xəta = None
        except BaseException as x:                 # noqa: BLE001
            t.son_xəta = (f"{x.tip}: {x.mesaj}" if isinstance(x, AlqorXəta)
                          else f"{type(x).__name__}: {x}")
            print(f"⚠ planlayıcı: `{t.ad}` xəta verdi — {t.son_xəta}",
                  file=sys.stderr)
        finally:
            t.say += 1
            t.son_vaxt = self._saat()
            t.işləyir = False

    def _vaxtı_çatanlar(self, indi: float) -> list[Tapşırıq]:
        hazır = []
        for t in self._tapşırıqlar:
            if not t.aktiv or t.növbəti_vaxt > indi:
                continue
            if t.işləyir and not t.üst_üstə:
                # əvvəlki icra bitməyib — bu dəfəni ötür
                self._növbətini_qur(t, indi)
                continue
            hazır.append(t)
            self._növbətini_qur(t, indi)
        return hazır

    def _növbətini_qur(self, t: Tapşırıq, indi: float) -> None:
        if not t.təkrar:
            t.aktiv = False
        elif t.növ == "hər":
            t.növbəti_vaxt += t.aralıq
            if t.növbəti_vaxt <= indi:          # gecikmə: ötürülənləri at
                t.növbəti_vaxt = indi + t.aralıq
        else:
            t.növbəti_vaxt = t.cron.növbəti(
                datetime.fromtimestamp(indi)).timestamp()

    def addım(self, arxada: bool = True) -> int:
        """Vaxtı çatan tapşırıqları işə salır; neçəsi başladı."""
        with self._şərt:
            hazır = self._vaxtı_çatanlar(self._saat())
            for t in hazır:
                t.işləyir = True
        for t in hazır:
            if arxada:
                s = threading.Thread(target=self._icra_et, args=(t,),
                                     daemon=True, name=f"alqor-{t.ad}")
                self._işlər = [x for x in self._işlər if x.is_alive()]
                self._işlər.append(s)
                s.start()
            else:
                self._icra_et(t)
        return len(hazır)

    def _dövr(self, son: float | None, boşda_çıx: bool = False) -> None:
        while True:
            with self._şərt:
                if self._dayan:
                    return
                aktivlər = [t.növbəti_vaxt for t in self._tapşırıqlar
                            if t.aktiv]
                if boşda_çıx and not aktivlər:
                    return
                indi = self._saat()
                gözlə = min(aktivlər) - indi if aktivlər else 1.0
                if son is not None:
                    gözlə = min(gözlə, son - time.monotonic())
                if gözlə > 0:
                    self._şərt.wait(min(gözlə, 1.0))
            if son is not None and time.monotonic() >= son:
                return
            self.addım()

    def başlat(self) -> None:
        with self._şərt:
            if self._sap is not None and self._sap.is_alive():
                return
            self._dayan = False
            self._sap = threading.Thread(target=self._dövr, args=(None,),
                                         daemon=True,
                                         name="alqor-planlayıcı")
            self._sap.start()

    def işlət(self, müddət: Any = None) -> None:
        """Ön planda işləyir: `müddət` saniyə və ya `dayandır()` çağırılana
        (və ya aktiv tapşırıq qalmayana) qədər."""
        son = None if müddət is None else time.monotonic() + müsbət_ədəd(
            müddət, "müddət", sıfır=True)
        self._dayan = False
        self._dövr(son, boşda_çıx=True)
        self._bitənləri_gözlə()

    def dayandır(self, gözlə: Any = True) -> None:
        with self._şərt:
            self._dayan = True
            self._şərt.notify_all()
        if self._sap is not None and self._sap is not \
                threading.current_thread():
            self._sap.join()
        if gözlə:
            self._bitənləri_gözlə()

    def _bitənləri_gözlə(self) -> None:
        for s in list(self._işlər):
            if s is not threading.current_thread():
                s.join()


Planlayıcı.ALQOR_METODLARI = {
    "cron": lambda i, p, ifadə, f, ad=None, üstÜstə=False:
        p.cron(ifadə, f, ad, üstÜstə),
    "hər": lambda i, p, s, f, ad=None, dərhal=False, üstÜstə=False:
        p.hər(s, f, ad, dərhal, üstÜstə),
    "sonra": lambda i, p, s, f, ad=None: p.sonra(s, f, ad),
    "vaxtında": lambda i, p, v, f, ad=None: p.vaxtında(v, f, ad),
    "başlat": lambda i, p: p.başlat(),
    "işlət": lambda i, p, müddət=None: p.işlət(müddət),
    "dayandır": lambda i, p, gözlə=True: p.dayandır(gözlə),
    "tapşırıqlar": lambda i, p: [t for t in p._tapşırıqlar if t.aktiv],
    "addım": lambda i, p: p.addım(arxada=False),
}


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "cron": D("cron", Cron, 1, 1),
        "növbəti": D("növbəti", lambda ifadə, başla=None: _iso(
            Cron(ifadə).növbəti(vaxt_oxu(başla))), 1, 2),
        "yoxla": D("yoxla", _yoxla, 1, 1),
        "yarat": D("yarat", lambda: Planlayıcı(icraçı)),
    }


def _yoxla(ifadə: Any) -> str | None:
    """Cron ifadəsi düzgündürsə `boş`, yoxsa xəta mətni."""
    try:
        Cron(ifadə)
        return None
    except AlqorXəta as x:
        return x.mesaj


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m = T.MƏTN
    return {
        "cron": F(m, qaytarır=T.Sadə("cron")),
        "növbəti": F(m, T.İSTƏNİLƏN, qaytarır=m, standart=1),
        "yoxla": F(m, qaytarır=T.ixtiyari(m)),
        "yarat": F(qaytarır=T.Sadə("planlayıcı")),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, o, i, b, h = (T.MƏTN, T.İSTƏNİLƏN, T.ONLUQ, T.TAM, T.MƏNTİQ,
                        T.HEÇ)
    Tp = T.Sadə("tapşırıq")
    return {
        "cron": {
            "növbəti": F(e, qaytarır=m, standart=1),
            "növbətilər": F(i, e, qaytarır=T.Siyahı(m), standart=1),
            "uyğundur": F(e, qaytarır=b, standart=1),
            "izah": F(qaytarır=m), "ifadə": F(qaytarır=m),
        },
        "planlayıcı": {
            "cron": F(e, e, m, b, qaytarır=Tp, standart=2),
            "hər": F(o, e, m, b, b, qaytarır=Tp, standart=3),
            "sonra": F(o, e, m, qaytarır=Tp, standart=1),
            "vaxtında": F(e, e, m, qaytarır=Tp, standart=1),
            "başlat": F(qaytarır=h),
            "işlət": F(o, qaytarır=h, standart=1),
            "dayandır": F(b, qaytarır=h, standart=1),
            "tapşırıqlar": F(qaytarır=T.Siyahı(Tp)),
            "addım": F(qaytarır=i),
        },
        "tapşırıq": {
            "id": F(qaytarır=i), "ad": F(qaytarır=m),
            "ləğvEt": F(qaytarır=h), "aktivdir": F(qaytarır=b),
            "say": F(qaytarır=i),
            "növbəti": F(qaytarır=T.ixtiyari(m)),
            "sonXəta": F(qaytarır=T.ixtiyari(m)),
            "lüğət": F(qaytarır=T.Lüğət(m, e)),
        },
    }
