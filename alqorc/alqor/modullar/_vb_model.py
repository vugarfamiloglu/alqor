"""
`verilənlər.Model` — ORM (§ 10.13).

    @cədvəl("istifadəçilər")
    sinif İstifadəçi miras verilənlər.Model
        @açar
        xassə id: tam
        xassə ad: mətn
        @sütun("e_poçt")
        xassə poçt: mətn?
        @əlaqə(çox: Sifariş)              // Sifariş.istifadəçiId → id
        xassə sifarişlər: siyahı[Sifariş]
    son

    İstifadəçi.istifadəEt(b)              // və ya verilənlər.Model.istifadəEt(b)
    İstifadəçi.cədvəlYarat()              // CREATE TABLE IF NOT EXISTS
    dəyişən i = İstifadəçi.yarat({"ad": "Aysel"})
    i.ad = "Aysel Məmmədova"
    i.saxla()                             // id 0/boş → INSERT, yoxsa UPDATE
    dəyişən tapılan = İstifadəçi.tap(i.id)          // və ya boş
    dəyişən siyahı = İstifadəçi.harada("ad", "bənzər", "A%").sırala("ad").al()
    i.yüklə("sifarişlər")                 // əlaqəni doldurur
    i.sil()

Annotasiyalar: `@cədvəl(ad)` (sinif), `@açar`, `@sütun(ad)`, `@keçici`
(bazada saxlanılmır), `@əlaqə(çox: Sinif, açar: "xariciAçar")` və
`@əlaqə(bir: Sinif, açar: "xariciAçar")`. Açar göstərilməyibsə `id`.
Sorğu qurucusunda XASSƏ adları işlədilir — sütun adına özü çevrilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import aac as A
from ..deyerler import AlqorXəta, Daxili, Nümunə, Sinif


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("VerilənlərXətası", mesaj, None, "ALQ-R013")


def _kiçik_ilk(s: str) -> str:
    if not s:
        return s
    c = {"İ": "i", "I": "ı"}.get(s[0], s[0].lower())
    return c + s[1:]


# ═══════════════════════════════════════════════════════════════════════
#  Metaməlumat
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Sahə:
    ad: str                      # xassə adı
    sütun: str
    tip: str                     # tam | onluq | mətn | məntiq | bayt | …
    boş_ola_bilər: bool
    açar: bool = False


@dataclass
class Əlaqə:
    ad: str
    növ: str                     # "çox" | "bir"
    hədəf: Sinif
    açar: str                    # xarici açarın XASSƏ adı


@dataclass
class Meta:
    sinif: Sinif
    cədvəl: str
    sahələr: list[Sahə] = field(default_factory=list)
    əlaqələr: dict[str, Əlaqə] = field(default_factory=dict)

    @property
    def açar(self) -> Sahə:
        for s in self.sahələr:
            if s.açar:
                return s
        raise _xəta(f"`{self.sinif.ad}` modelində açar yoxdur — `@açar` "
                    "və ya `id` xassəsi əlavə edin")

    def sahə(self, ad: str) -> Sahə:
        for s in self.sahələr:
            if s.ad == ad or s.sütun == ad:
                return s
        raise _xəta(f"`{self.sinif.ad}` modelində `{ad}` sahəsi yoxdur")


def _annot(annotasiyalar: list, ad: str) -> A.Annotasiya | None:
    for a in annotasiyalar or []:
        if a.ad == ad:
            return a
    return None


def _arqumentlər(icraçı, a: A.Annotasiya, mühit) -> tuple[list, dict]:
    mövqeli, adlı = [], {}
    for x in a.arqumentlər:
        d = icraçı._ifadə(x.dəyər, mühit)
        if x.ad:
            adlı[x.ad] = d
        else:
            mövqeli.append(d)
    return mövqeli, adlı


def meta(icraçı, s: Sinif) -> Meta:
    if not isinstance(s, Sinif) or s is MODEL or not _modeldir(s):
        raise _xəta("bu sinif `verilənlər.Model`-dən miras almır")
    mühit = s.mühit or icraçı.qlobal
    a = _annot(s.annotasiyalar, "cədvəl")
    cədvəl = s.ad
    if a is not None:
        p, _ = _arqumentlər(icraçı, a, mühit)
        if p:
            cədvəl = str(p[0])
    m = Meta(s, cədvəl)
    for x in s.bütün_xassələr():
        ann = x.annotasiyalar
        if _annot(ann, "keçici") is not None:
            continue
        əl = _annot(ann, "əlaqə")
        if əl is not None:
            _, adlı = _arqumentlər(icraçı, əl, mühit)
            if "çox" in adlı:
                növ, hədəf = "çox", adlı["çox"]
                açar = adlı.get("açar") or _kiçik_ilk(s.ad) + "Id"
            elif "bir" in adlı:
                növ, hədəf = "bir", adlı["bir"]
                açar = adlı.get("açar") or x.ad + "Id"
            else:
                raise _xəta(f"`@əlaqə` `çox:` və ya `bir:` gözləyir "
                            f"({s.ad}.{x.ad})")
            if not isinstance(hədəf, Sinif):
                raise _xəta(f"`@əlaqə` hədəfi sinif olmalıdır ({s.ad}.{x.ad})")
            m.əlaqələr[x.ad] = Əlaqə(x.ad, növ, hədəf, str(açar))
            continue
        sütun = x.ad
        st = _annot(ann, "sütun")
        if st is not None:
            p, _ = _arqumentlər(icraçı, st, mühit)
            if p:
                sütun = str(p[0])
        tip, boş = "mətn", True
        if isinstance(x.tip, A.TipAdı):
            tip, boş = x.tip.tam_ad, bool(x.tip.ixtiyari)
        m.sahələr.append(Sahə(x.ad, sütun, tip, boş,
                              _annot(ann, "açar") is not None))
    if not any(s_.açar for s_ in m.sahələr):
        for s_ in m.sahələr:
            if s_.ad == "id":
                s_.açar = True
                break
    return m


def _modeldir(s: Sinif | None) -> bool:
    while s is not None:
        if s is MODEL:
            return True
        s = s.baza
    return False


# ═══════════════════════════════════════════════════════════════════════
#  Bağlantı
# ═══════════════════════════════════════════════════════════════════════

_BAĞLANTILAR: dict[int, Any] = {}


def _bağlantı(s: Sinif):
    c: Sinif | None = s
    while c is not None:
        b = _BAĞLANTILAR.get(id(c))
        if b is not None:
            return b
        c = c.baza
    raise _xəta(f"`{s.ad}` modelinin bağlantısı yoxdur — "
                f"`{s.ad}.istifadəEt(b)` və ya "
                "`verilənlər.Model.istifadəEt(b)` çağırın")


def _qurucu(s: Sinif):
    from .verilenler import Qurucu
    m_ = _META(s)
    return Qurucu(_bağlantı(s), m_.cədvəl), m_


_ICRAÇI: list = [None]


def _META(s: Sinif) -> Meta:
    return meta(_ICRAÇI[0], s)


# ═══════════════════════════════════════════════════════════════════════
#  Sətir ↔ nümunə
# ═══════════════════════════════════════════════════════════════════════

def _dəyər(sahə: Sahə, d: Any) -> Any:
    if d is None:
        return None
    if sahə.tip == "məntiq":
        return bool(d)
    if sahə.tip == "tam" and isinstance(d, float) and d.is_integer():
        return int(d)
    if sahə.tip == "onluq" and isinstance(d, int):
        return float(d)
    if sahə.tip == "bayt" and isinstance(d, str):
        return d.encode("utf-8")
    return d


def _boş_nümunə(icraçı, s: Sinif) -> Nümunə:
    n = Nümunə(s)
    for x in s.bütün_xassələr():
        if x.standart is not None:
            n.sahələr[x.ad] = icraçı._ifadə(x.standart, s.mühit
                                            or icraçı.qlobal)
        else:
            n.sahələr[x.ad] = icraçı._xassə_standartı(x)
    return n


def _nümunə(icraçı, s: Sinif, m: Meta, sətir: dict) -> Nümunə:
    n = _boş_nümunə(icraçı, s)
    for sh in m.sahələr:
        if sh.sütun in sətir:
            n.sahələr[sh.ad] = _dəyər(sh, sətir[sh.sütun])
    return n


def _yeni_dir(d: Any) -> bool:
    return d is None or d == 0 or d == ""


def _sütunlar(m: Meta, n: Nümunə, açarsız: bool) -> dict:
    l = {}
    for sh in m.sahələr:
        if açarsız and sh.açar:
            continue
        l[sh.sütun] = n.sahələr.get(sh.ad)
    return l


def saxla(icraçı, n: Nümunə) -> Nümunə:
    q, m = _qurucu(n.sinif)
    açar = m.açar
    d = n.sahələr.get(açar.ad)
    b = q.b
    if not _yeni_dir(d):
        dəyişən = q.harada(açar.sütun, "=", d).yenilə(
            _sütunlar(m, n, True)) if len(m.sahələr) > 1 else 1
        if dəyişən:
            return n
        if q.harada(açar.sütun, "=", d).say():
            return n                    # MySQL: dəyişməyən sətir 0 sayılır
        q.əlavə_et(_sütunlar(m, n, False))
        return n
    yeni_id = q.əlavə_et(_sütunlar(m, n, True))
    if yeni_id is None and b.son_id is not None:
        yeni_id = b.son_id
    n.sahələr[açar.ad] = _dəyər(açar, yeni_id)
    return n


def sil(icraçı, n: Nümunə) -> bool:
    q, m = _qurucu(n.sinif)
    d = n.sahələr.get(m.açar.ad)
    if _yeni_dir(d):
        return False
    return q.harada(m.açar.sütun, "=", d).sil() > 0


def yüklə(icraçı, n: Nümunə, ad: str) -> Any:
    m = _META(n.sinif)
    əl = m.əlaqələr.get(ad)
    if əl is None:
        raise _xəta(f"`{n.sinif.ad}` modelində `{ad}` əlaqəsi yoxdur")
    if əl.növ == "çox":
        d = n.sahələr.get(m.açar.ad)
        nəticə = ModelSorğusu(əl.hədəf).harada(əl.açar, "=", d).al()
    else:
        hm = _META(əl.hədəf)
        d = n.sahələr.get(əl.açar)
        if d is None:
            raise _xəta(f"`{n.sinif.ad}` modelində `{əl.açar}` xarici açar "
                        "xassəsi yoxdur")
        nəticə = tap(icraçı, əl.hədəf, d) if not _yeni_dir(d) else None
        del hm
    n.sahələr[ad] = nəticə
    return nəticə


def lüğət(icraçı, n: Nümunə) -> dict:
    m = _META(n.sinif)
    return {sh.ad: n.sahələr.get(sh.ad) for sh in m.sahələr}


# ── Sinif tərəfi ──────────────────────────────────────────────────────

def tap(icraçı, s: Sinif, açar: Any) -> Nümunə | None:
    q, m = _qurucu(s)
    sətir = q.harada(m.açar.sütun, "=", açar).ilk()
    return _nümunə(icraçı, s, m, sətir) if sətir is not None else None


def yarat(icraçı, s: Sinif, l: dict | None = None) -> Nümunə:
    m = _META(s)
    n = _boş_nümunə(icraçı, s)
    for a, d in (l or {}).items():
        sh = m.sahə(str(a))
        n.sahələr[sh.ad] = d
    return saxla(icraçı, n)


def cədvəl_yarat(icraçı, s: Sinif) -> None:
    b = _bağlantı(s)
    m = _META(s)
    sütunlar = []
    for sh in m.sahələr:
        t = b.d.tip(sh.tip, sh.açar)
        if not sh.açar and not sh.boş_ola_bilər and sh.tip in (
                "tam", "onluq", "məntiq", "mətn", "bayt"):
            t += " NOT NULL"
        sütunlar.append(f"{b.ad(sh.sütun)} {t}")
    b._əmr(f"CREATE TABLE IF NOT EXISTS {b.ad(m.cədvəl, 'cədvəl')} "
           f"({', '.join(sütunlar)})")


class ModelSorğusu:
    """Sorğu qurucusu, amma sətirlər model nümunələrinə çevrilir."""

    ALQOR_TİP_ADI = "modelSorğusu"

    def __init__(self, s: Sinif, q=None):
        self.s = s
        if q is None:
            q, self.m = _qurucu(s)
        else:
            self.m = _META(s)
        self.q = q

    def _yeni(self, q) -> "ModelSorğusu":
        return ModelSorğusu(self.s, q)

    def harada(self, ad, op, d=None, bağ="AND"):
        return self._yeni(self.q.harada(self.m.sahə(str(ad)).sütun, op, d,
                                        bağ))

    def sırala(self, ad, i="artan"):
        return self._yeni(self.q.sırala(self.m.sahə(str(ad)).sütun, i))

    def limit(self, n):
        return self._yeni(self.q.limit(n))

    def atla(self, n):
        return self._yeni(self.q.atla(n))

    def al(self) -> list[Nümunə]:
        return [_nümunə(_ICRAÇI[0], self.s, self.m, r) for r in self.q.al()]

    def ilk(self) -> Nümunə | None:
        r = self.limit(1).al()
        return r[0] if r else None

    def say(self) -> int:
        return self.q.say()

    def sil(self) -> int:
        return self.q.sil()


ModelSorğusu.ALQOR_METODLARI = {
    "harada": lambda i, q, a, o, d=None: q.harada(a, o, d),
    "vəHarada": lambda i, q, a, o, d=None: q.harada(a, o, d, "AND"),
    "yaHarada": lambda i, q, a, o, d=None: q.harada(a, o, d, "OR"),
    "sırala": lambda i, q, a, y="artan": q.sırala(a, y),
    "limit": lambda i, q, n: q.limit(n),
    "atla": lambda i, q, n: q.atla(n),
    "al": lambda i, q: q.al(),
    "ilk": lambda i, q: q.ilk(),
    "say": lambda i, q: q.say(),
    "sil": lambda i, q: q.sil(),
}


# ═══════════════════════════════════════════════════════════════════════
#  Model sinfi
# ═══════════════════════════════════════════════════════════════════════

class _Üzv:
    """Çağıran sinfə (və ya nümunəyə) bağlanan üzv."""

    def __init__(self, ad: str, f, mn: int, mx: int | None,
                 nümunə: bool = False):
        self.ad, self.f, self.mn, self.mx = ad, f, mn, mx
        self.nümunə = nümunə

    def alqor_bağla(self, sinif: Sinif, n: Nümunə | None) -> Daxili:
        if self.nümunə:
            if n is None:
                raise _xəta(f"`{self.ad}` nümunə metodudur — "
                            f"`{sinif.ad}` nümunəsində çağırın")
            return Daxili(self.ad, lambda icraçı, *a, **k: self._çağır(
                icraçı, n, *a, **k), self.mn, self.mx, True)
        return Daxili(self.ad, lambda icraçı, *a, **k: self._çağır(
            icraçı, sinif, *a, **k), self.mn, self.mx, True)

    def _çağır(self, icraçı, hədəf, *a, **k):
        _ICRAÇI[0] = icraçı
        return self.f(icraçı, hədəf, *a, **k)


def _istifadə_et(icraçı, s: Sinif, b: Any) -> None:
    from .verilenler import Bağlantı
    if not isinstance(b, Bağlantı):
        raise AlqorXəta("TipXətası", "`istifadəEt` bağlantı gözləyir "
                        "(verilənlər.bağlan(…))", None, "ALQ-T001")
    _BAĞLANTILAR[id(s)] = b


MODEL = Sinif("Model", mücərrəd=False)
MODEL.statiklər.update({
    "istifadəEt": _Üzv("istifadəEt", _istifadə_et, 1, 1),
    "tap": _Üzv("tap", tap, 1, 1),
    "hamısı": _Üzv("hamısı", lambda i, s: ModelSorğusu(s).al(), 0, 0),
    "harada": _Üzv("harada", lambda i, s, a, o, d=None:
                   ModelSorğusu(s).harada(a, o, d), 2, 3),
    "sırala": _Üzv("sırala", lambda i, s, a, y="artan":
                   ModelSorğusu(s).sırala(a, y), 1, 2),
    "say": _Üzv("say", lambda i, s: ModelSorğusu(s).say(), 0, 0),
    "yarat": _Üzv("yarat", yarat, 0, 1),
    "cədvəlYarat": _Üzv("cədvəlYarat", cədvəl_yarat, 0, 0),
    "saxla": _Üzv("saxla", saxla, 0, 0, nümunə=True),
    "sil": _Üzv("sil", sil, 0, 0, nümunə=True),
    "yüklə": _Üzv("yüklə", yüklə, 1, 1, nümunə=True),
    "lüğət": _Üzv("lüğət", lüğət, 0, 0, nümunə=True),
})
