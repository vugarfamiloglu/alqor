"""
`keş` — yaddaş, fayl və Redis keşi (§ 10.17).

    gətir keş

    dəyişən k = keş.yaddaş(maks: 1000, müddət: 60)     // LRU, 60 saniyə
    k.qoy("istifadəçi:1", {"ad": "Aysel"})
    yaz(k.al("istifadəçi:1"))
    dəyişən say = k.artır("baxış")                     // 1, 2, 3 …
    dəyişən d = k.hesabla("hesabat", () => ağırHesabat(), müddət: 300)

    dəyişən f = keş.fayl(".keş")                       // proses yenidən başlasa da qalır
    dəyişən r = keş.redis("redis://:parol@127.0.0.1:6379/0", ön: "tətbiq:")

    // Funksiya nəticələrini keşləmək
    dəyişən sürətli = keş.bük(yavaşFunksiya, müddət: 30)

Üç keşin metodları eynidir: `qoy`, `al`, `var`, `sil`, `təmizlə`,
`ölçü`, `açarlar`, `hesabla`, `artır`, `qalanMüddət`, `alÇox`, `qoyÇox`,
`statistika`. Açar mətn olmalıdır. Fayl və Redis keşində dəyər JSON
kimi saxlanır (mətn, ədəd, məntiq, boş, siyahı, lüğət).

`müddət` saniyə ilə verilir; verilməsə keşin standart müddəti, o da yoxdursa
— müddətsiz.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from ..deyerler import AlqorXəta, Daxili, tip_adı
from ._yardim import çağır, funksiya_tələb, müsbət_ədəd

_YOX = object()


def _xəta(mesaj: str, tip: str = "KeşXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _açar(a: Any) -> str:
    if isinstance(a, bool) or not isinstance(a, (str, int)):
        raise _xəta(f"keş açarı mətn olmalıdır, `{tip_adı(a)}` gəlib",
                    "TipXətası")
    return str(a)


def _müddət(ö: Any) -> float | None:
    if ö is None:
        return None
    return müsbət_ədəd(ö, "müddət")


def _json(d: Any) -> str:
    def çevir(x):
        if isinstance(x, tuple):
            return [çevir(e) for e in x]
        if isinstance(x, list):
            return [çevir(e) for e in x]
        if isinstance(x, dict):
            n = {}
            for a, v in x.items():
                if not isinstance(a, str):
                    raise _xəta("JSON keşdə lüğət açarları mətn olmalıdır")
                n[a] = çevir(v)
            return n
        if x is None or isinstance(x, (str, int, float, bool)):
            return x
        raise _xəta(f"`{tip_adı(x)}` fayl/Redis keşində saxlanmır — "
                    "mətn, ədəd, siyahı və lüğət işlədin")
    return json.dumps(çevir(d), ensure_ascii=False, separators=(",", ":"))


class _Keş:
    """Ortaq məntiq; alt siniflər `_al`, `_qoy`, `_sil` … verir."""

    ALQOR_TİP_ADI = "keş"

    def __init__(self, müddət: Any = None):
        self.müddət = _müddət(müddət)
        self.isabət = 0
        self.qaçırma = 0
        self._kilidlər: dict[str, threading.Lock] = {}
        self._ümumi = threading.Lock()

    def _ö(self, müddət: Any) -> float | None:
        return self.müddət if müddət is None else _müddət(müddət)

    def al(self, a: Any, standart: Any = None) -> Any:
        d = self._al(_açar(a))
        if d is _YOX:
            self.qaçırma += 1
            return standart
        self.isabət += 1
        return d

    def qoy(self, a: Any, d: Any, müddət: Any = None) -> None:
        self._qoy(_açar(a), d, self._ö(müddət))

    def var(self, a: Any) -> bool:
        return self._al(_açar(a)) is not _YOX

    def hesabla(self, icraçı, a: Any, f: Any, müddət: Any = None) -> Any:
        """Açar varsa dəyəri, yoxsa `f()` hesablayıb saxlayır. Eyni açarı
        eyni anda bir neçə sap istəsə `f` yalnız bir dəfə işləyir."""
        a = _açar(a)
        funksiya_tələb(f, "hesabla")
        d = self._al(a)
        if d is not _YOX:
            self.isabət += 1
            return d
        with self._ümumi:
            kilid = self._kilidlər.setdefault(a, threading.Lock())
        with kilid:
            d = self._al(a)
            if d is not _YOX:
                self.isabət += 1
                return d
            self.qaçırma += 1
            d = çağır(icraçı, f)
            self._qoy(a, d, self._ö(müddət))
            return d

    def alÇox(self, açarlar: Any) -> dict:
        if not isinstance(açarlar, list):
            raise _xəta("`alÇox` açar siyahısı gözləyir", "TipXətası")
        n = {}
        for a in açarlar:
            d = self._al(_açar(a))
            if d is not _YOX:
                n[str(a)] = d
        return n

    def qoyÇox(self, l: Any, müddət: Any = None) -> None:
        if not isinstance(l, dict):
            raise _xəta("`qoyÇox` lüğət gözləyir", "TipXətası")
        for a, d in l.items():
            self.qoy(a, d, müddət)

    def statistika(self) -> dict:
        cəm = self.isabət + self.qaçırma
        return {"isabət": self.isabət, "qaçırma": self.qaçırma,
                "nisbət": round(self.isabət / cəm, 4) if cəm else 0.0,
                "ölçü": self.ölçü()}


# ── Yaddaş keşi (LRU + müddət) ──────────────────────────────────────────

class YaddaşKeşi(_Keş):
    def __init__(self, maks: Any = 1000, müddət: Any = None):
        super().__init__(müddət)
        if maks is not None and (isinstance(maks, bool) or
                                 not isinstance(maks, int) or maks < 1):
            raise _xəta("`maks` müsbət tam ədəd olmalıdır", "ArqumentXətası")
        self.maks = maks
        self._d: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()
        self._k = threading.RLock()

    def __repr__(self) -> str:
        return f"<keş yaddaş {len(self._d)}/{self.maks}>"

    def _al(self, a: str) -> Any:
        with self._k:
            x = self._d.get(a)
            if x is None:
                return _YOX
            if x[1] is not None and x[1] <= time.monotonic():
                del self._d[a]
                return _YOX
            self._d.move_to_end(a)
            return x[0]

    def _qoy(self, a: str, d: Any, müddət: float | None) -> None:
        with self._k:
            self._d[a] = (d, None if müddət is None else
                          time.monotonic() + müddət)
            self._d.move_to_end(a)
            if self.maks is not None:
                while len(self._d) > self.maks:
                    self._d.popitem(last=False)

    def sil(self, a: Any) -> bool:
        with self._k:
            return self._d.pop(_açar(a), None) is not None

    def təmizlə(self) -> None:
        with self._k:
            self._d.clear()

    def _köhnələri_at(self) -> None:
        t = time.monotonic()
        for a in [a for a, (_, s) in self._d.items()
                  if s is not None and s <= t]:
            del self._d[a]

    def ölçü(self) -> int:
        with self._k:
            self._köhnələri_at()
            return len(self._d)

    def açarlar(self) -> list:
        with self._k:
            self._köhnələri_at()
            return list(self._d)

    def qalanMüddət(self, a: Any) -> float | None:
        with self._k:
            x = self._d.get(_açar(a))
            if x is None or x[1] is None:
                return None
            return max(0.0, round(x[1] - time.monotonic(), 3))

    def artır(self, a: Any, n: Any = 1) -> int:
        a = _açar(a)
        with self._k:
            d = self._al(a)
            if d is _YOX:
                d, son = 0, (None if self.müddət is None
                             else time.monotonic() + self.müddət)
            else:
                son = self._d[a][1]
            if isinstance(d, bool) or not isinstance(d, int):
                raise _xəta(f"`{a}` tam ədəd deyil — artırılmır")
            d += n
            self._d[a] = (d, son)
            return d


# ── Fayl keşi ─────────────────────────────────────────────────────────

class FaylKeşi(_Keş):
    def __init__(self, qovluq: Any = ".keş", müddət: Any = None):
        super().__init__(müddət)
        self.qovluq = Path(str(qovluq))
        self.qovluq.mkdir(parents=True, exist_ok=True)
        self._k = threading.RLock()

    def __repr__(self) -> str:
        return f"<keş fayl {self.qovluq}>"

    def _yol(self, a: str) -> Path:
        h = hashlib.sha256(a.encode("utf-8")).hexdigest()
        return self.qovluq / h[:2] / f"{h}.json"

    def _oxu(self, p: Path) -> dict | None:
        try:
            x = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if x.get("son") is not None and x["son"] <= time.time():
            try:
                p.unlink()
            except OSError:
                pass
            return None
        return x

    def _al(self, a: str) -> Any:
        x = self._oxu(self._yol(a))
        return _YOX if x is None else x["d"]

    def _qoy(self, a: str, d: Any, müddət: float | None) -> None:
        p = self._yol(a)
        mətn = ('{"a":' + json.dumps(a, ensure_ascii=False) + ',"son":' +
                json.dumps(None if müddət is None else time.time() + müddət) +
                ',"d":' + _json(d) + "}")
        p.parent.mkdir(exist_ok=True)
        müv = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        müv.write_text(mətn, encoding="utf-8")
        os.replace(müv, p)

    def _hamısı(self):
        for p in self.qovluq.glob("??/*.json"):
            x = self._oxu(p)
            if x is not None:
                yield p, x

    def sil(self, a: Any) -> bool:
        p = self._yol(_açar(a))
        try:
            p.unlink()
            return True
        except FileNotFoundError:
            return False

    def təmizlə(self) -> None:
        for p in self.qovluq.glob("??/*.json"):
            try:
                p.unlink()
            except OSError:
                pass

    def ölçü(self) -> int:
        return sum(1 for _ in self._hamısı())

    def açarlar(self) -> list:
        return sorted(x["a"] for _, x in self._hamısı())

    def qalanMüddət(self, a: Any) -> float | None:
        x = self._oxu(self._yol(_açar(a)))
        if x is None or x.get("son") is None:
            return None
        return max(0.0, round(x["son"] - time.time(), 3))

    def artır(self, a: Any, n: Any = 1) -> int:
        a = _açar(a)
        with self._k:
            x = self._oxu(self._yol(a))
            d = 0 if x is None else x["d"]
            if isinstance(d, bool) or not isinstance(d, int):
                raise _xəta(f"`{a}` tam ədəd deyil — artırılmır")
            qalan = self.müddət if x is None else (
                None if x.get("son") is None else
                max(0.001, x["son"] - time.time()))
            self._qoy(a, d + n, qalan)
            return d + n


# ── Redis keşi (RESP2 protokolu, xarici kitabxanasız) ─────────────────

class RedisXətası(Exception):
    pass


class RedisMüştəri:
    def __init__(self, ünvan: str, vaxt_limiti: float = 5.0):
        u = urlparse(ünvan)
        if u.scheme not in ("redis", "rediss"):
            raise _xəta("Redis ünvanı `redis://` və ya `rediss://` ilə "
                        "başlamalıdır")
        self.host = u.hostname or "127.0.0.1"
        self.port = u.port or 6379
        self.tls = u.scheme == "rediss"
        self.istifadəçi = unquote(u.username) if u.username else None
        self.parol = unquote(u.password) if u.password else None
        yol = (u.path or "/").strip("/")
        self.baza = int(yol) if yol.isdigit() else 0
        self.vaxt_limiti = vaxt_limiti
        self._s: socket.socket | None = None
        self._f = None
        self._k = threading.Lock()

    def _qoşul(self) -> None:
        s = socket.create_connection((self.host, self.port),
                                     timeout=self.vaxt_limiti)
        if self.tls:
            s = ssl.create_default_context().wrap_socket(
                s, server_hostname=self.host)
        self._s, self._f = s, s.makefile("rb")
        try:
            if self.parol is not None:
                self._göndər(*(["AUTH", self.istifadəçi, self.parol]
                               if self.istifadəçi else ["AUTH", self.parol]))
            if self.baza:
                self._göndər("SELECT", str(self.baza))
        except BaseException:
            self._f.close()
            s.close()
            self._s = self._f = None
            raise

    def bağla(self) -> None:
        with self._k:
            if self._s is not None:
                try:
                    self._s.close()
                except OSError:
                    pass
            self._s = self._f = None

    @staticmethod
    def _kodla(*hissələr: Any) -> bytes:
        n = [b"*%d\r\n" % len(hissələr)]
        for h in hissələr:
            b = h if isinstance(h, bytes) else str(h).encode("utf-8")
            n.append(b"$%d\r\n%s\r\n" % (len(b), b))
        return b"".join(n)

    def _oxu(self) -> Any:
        sətir = self._f.readline()
        if not sətir:
            raise ConnectionError("Redis bağlantısı kəsildi")
        t, qalan = sətir[:1], sətir[1:-2]
        if t == b"+":
            return qalan.decode("utf-8")
        if t == b"-":
            raise RedisXətası(qalan.decode("utf-8", "replace"))
        if t == b":":
            return int(qalan)
        if t == b"$":
            n = int(qalan)
            if n < 0:
                return None
            b = self._f.read(n + 2)
            return b[:-2].decode("utf-8")
        if t == b"*":
            n = int(qalan)
            return None if n < 0 else [self._oxu() for _ in range(n)]
        raise ConnectionError(f"Redis: naməlum cavab {sətir[:20]!r}")

    def _göndər(self, *hissələr: Any) -> Any:
        self._s.sendall(self._kodla(*hissələr))
        return self._oxu()

    def əmr(self, *hissələr: Any) -> Any:
        with self._k:
            for cəhd in range(2):
                try:
                    if self._s is None:
                        self._qoşul()
                    return self._göndər(*hissələr)
                except RedisXətası as x:
                    raise _xəta(f"Redis: {x}")
                except (OSError, ConnectionError) as x:
                    if self._s is not None:
                        try:
                            self._s.close()
                        except OSError:
                            pass
                    self._s = self._f = None
                    if cəhd:
                        raise _xəta(f"Redis-ə qoşulmaq olmadı "
                                    f"({self.host}:{self.port}): {x}",
                                    "ŞəbəkəXətası")


class RedisKeşi(_Keş):
    def __init__(self, ünvan: Any = "redis://127.0.0.1:6379/0",
                 ön: Any = "", müddət: Any = None, vaxtLimiti: Any = 5):
        super().__init__(müddət)
        self.r = RedisMüştəri(str(ünvan),
                              müsbət_ədəd(vaxtLimiti, "vaxtLimiti"))
        self.ön = str(ön)

    def __repr__(self) -> str:
        return f"<keş redis {self.r.host}:{self.r.port}/{self.r.baza}>"

    def _al(self, a: str) -> Any:
        d = self.r.əmr("GET", self.ön + a)
        if d is None:
            return _YOX
        try:
            return json.loads(d)
        except ValueError:
            return d

    def _qoy(self, a: str, d: Any, müddət: float | None) -> None:
        if müddət is None:
            self.r.əmr("SET", self.ön + a, _json(d))
        else:
            self.r.əmr("SET", self.ön + a, _json(d), "PX",
                       max(1, int(müddət * 1000)))

    def sil(self, a: Any) -> bool:
        return bool(self.r.əmr("DEL", self.ön + _açar(a)))

    def _skan(self) -> list[str]:
        n, kursor = [], "0"
        naxış = self.ön.replace("\\", "\\\\").replace("*", "\\*") \
            .replace("?", "\\?").replace("[", "\\[") + "*"
        while True:
            kursor, açarlar = self.r.əmr("SCAN", kursor, "MATCH", naxış,
                                         "COUNT", 500)
            n.extend(açarlar)
            if str(kursor) == "0":
                return n

    def təmizlə(self) -> None:
        """Yalnız `ön` ilə başlayan açarlar silinir (bütün baza YOX)."""
        açarlar = self._skan()
        for i in range(0, len(açarlar), 500):
            self.r.əmr("DEL", *açarlar[i:i + 500])

    def ölçü(self) -> int:
        return len(self._skan())

    def açarlar(self) -> list:
        return sorted(a[len(self.ön):] for a in self._skan())

    def qalanMüddət(self, a: Any) -> float | None:
        ms = self.r.əmr("PTTL", self.ön + _açar(a))
        return None if ms < 0 else ms / 1000

    def artır(self, a: Any, n: Any = 1) -> int:
        a = self.ön + _açar(a)
        d = self.r.əmr("INCRBY", a, int(n))
        if d == n and self.müddət is not None:
            self.r.əmr("PEXPIRE", a, int(self.müddət * 1000))
        return d

    def alÇox(self, açarlar: Any) -> dict:
        if not isinstance(açarlar, list):
            raise _xəta("`alÇox` açar siyahısı gözləyir", "TipXətası")
        if not açarlar:
            return {}
        dəyərlər = self.r.əmr("MGET", *[self.ön + _açar(a) for a in açarlar])
        n = {}
        for a, d in zip(açarlar, dəyərlər):
            if d is not None:
                try:
                    n[str(a)] = json.loads(d)
                except ValueError:
                    n[str(a)] = d
        return n

    def bağla(self) -> None:
        self.r.bağla()


_KEŞ_METODLARI = {
    "qoy": lambda i, k, a, d, müddət=None: k.qoy(a, d, müddət),
    "al": lambda i, k, a, standart=None: k.al(a, standart),
    "var": lambda i, k, a: k.var(a),
    "sil": lambda i, k, a: k.sil(a),
    "təmizlə": lambda i, k: k.təmizlə(),
    "ölçü": lambda i, k: k.ölçü(),
    "açarlar": lambda i, k: k.açarlar(),
    "hesabla": lambda i, k, a, f, müddət=None: k.hesabla(i, a, f, müddət),
    "artır": lambda i, k, a, n=1: k.artır(a, n),
    "azalt": lambda i, k, a, n=1: k.artır(a, -n),
    "qalanMüddət": lambda i, k, a: k.qalanMüddət(a),
    "alÇox": lambda i, k, a: k.alÇox(a),
    "qoyÇox": lambda i, k, l, müddət=None: k.qoyÇox(l, müddət),
    "statistika": lambda i, k: k.statistika(),
    "bağla": lambda i, k: getattr(k, "bağla", lambda: None)(),
}
for _s in (YaddaşKeşi, FaylKeşi, RedisKeşi):
    _s.ALQOR_METODLARI = _KEŞ_METODLARI


def bük(icraçı, f: Any, müddət: Any = None, maks: Any = 1000,
        keş: Any = None) -> Daxili:
    """Funksiyanı keşləyən sarğı: eyni arqumentlər → saxlanmış nəticə."""
    from ..deyerler import mətnə
    funksiya_tələb(f, "bük")
    k = keş if isinstance(keş, _Keş) else YaddaşKeşi(maks, müddət)
    ad = getattr(f, "ad", "funksiya")

    def sarğı(*a, **adlı):
        açar = ad + "(" + ", ".join(
            [_açar_mətni(x, mətnə) for x in a] +
            [f"{n}: {_açar_mətni(v, mətnə)}"
             for n, v in sorted(adlı.items())]) + ")"
        return k.hesabla(icraçı, açar,
                         Daxili(ad, lambda: çağır(icraçı, f, *a, **adlı)),
                         müddət)

    d = Daxili(ad, sarğı, 0, None)
    return d


def _açar_mətni(x: Any, mətnə) -> str:
    if isinstance(x, str):
        return json.dumps(x, ensure_ascii=False)
    return mətnə(x)


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "yaddaş": D("yaddaş", lambda maks=1000, müddət=None:
                    YaddaşKeşi(maks, müddət), 0, 2),
        "fayl": D("fayl", lambda qovluq=".keş", müddət=None:
                  FaylKeşi(qovluq, müddət), 0, 2),
        "redis": D("redis", lambda ünvan="redis://127.0.0.1:6379/0", ön="",
                   müddət=None, vaxtLimiti=5:
                   RedisKeşi(ünvan, ön, müddət, vaxtLimiti), 0, 4),
        "bük": D("bük", lambda f, müddət=None, maks=1000, keş=None:
                 bük(icraçı, f, müddət, maks, keş), 1, 4),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, o, i = T.MƏTN, T.İSTƏNİLƏN, T.ONLUQ, T.TAM
    K = T.Sadə("keş")
    return {
        "yaddaş": F(i, o, qaytarır=K, standart=2),
        "fayl": F(m, o, qaytarır=K, standart=2),
        "redis": F(m, m, o, o, qaytarır=K, standart=4),
        "bük": F(e, o, i, K, qaytarır=e, standart=3),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, o, i, b, h = (T.MƏTN, T.İSTƏNİLƏN, T.ONLUQ, T.TAM, T.MƏNTİQ,
                        T.HEÇ)
    return {"keş": {
        "qoy": F(m, e, o, qaytarır=h, standart=1),
        "al": F(m, e, qaytarır=e, standart=1),
        "var": F(m, qaytarır=b), "sil": F(m, qaytarır=b),
        "təmizlə": F(qaytarır=h), "ölçü": F(qaytarır=i),
        "açarlar": F(qaytarır=T.Siyahı(m)),
        "hesabla": F(m, e, o, qaytarır=e, standart=1),
        "artır": F(m, i, qaytarır=i, standart=1),
        "azalt": F(m, i, qaytarır=i, standart=1),
        "qalanMüddət": F(m, qaytarır=T.ixtiyari(o)),
        "alÇox": F(T.Siyahı(m), qaytarır=T.Lüğət(m, e)),
        "qoyÇox": F(T.Lüğət(m, e), o, qaytarır=h, standart=1),
        "statistika": F(qaytarır=T.Lüğət(m, e)),
        "bağla": F(qaytarır=h),
    }}
