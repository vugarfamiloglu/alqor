"""
Alqor — verilənlər bazası sxemi (`.sxem`): Studio-nun cədvəl redaktoru.

Cədvəllər və sahələr bir faylda təsvir olunur; proqram bazaya qoşulanda
çatışmayan cədvəl və sütunlar avtomatik yaradılır (heç nə silinmir).
Eyni sxem SQLite, PostgreSQL və MySQL-də işləyir.

    // mekteb.sxem
    sxem Məktəb
        cədvəl qruplar
            id: tam açar
            ad: mətn məcburi tək
        son
        cədvəl tələbələr
            id: tam açar
            ad: mətn məcburi
            soyad: mətn
            sinif: tam = 1
            doğum_tarixi: tarix
            aktiv: məntiq = doğru
            qrup_id: tam → qruplar.id
        son
    son

Sahə: `ad: tip [açar] [məcburi] [tək] [= standart] [→ cədvəl.sütun]`
Tiplər: tam, onluq, mətn, məntiq, tarix, tarixVaxt, bayt.
`açar` olan `tam` sahə avtomatik artır (1, 2, 3 …).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .xeta import XətaToplayıcı, Yer

UZANTI = ".sxem"
TİPLƏR = ("tam", "onluq", "mətn", "məntiq", "tarix", "tarixVaxt", "bayt")
BAYRAQLAR = ("açar", "məcburi", "tək")
_AD = re.compile(r"^[^\W\d]\w*$")


@dataclass
class Sahə:
    ad: str
    tip: str = "mətn"
    açar: bool = False
    məcburi: bool = False
    tək: bool = False
    standart: Any = None
    standart_var: bool = False
    əlaqə: tuple[str, str] | None = None        # (cədvəl, sütun)
    yer: Yer | None = None

    def lüğət(self) -> dict:
        return {"ad": self.ad, "tip": self.tip, "açar": self.açar,
                "məcburi": self.məcburi, "tək": self.tək,
                "standart": self.standart if self.standart_var else None,
                "standartVar": self.standart_var,
                "əlaqə": ".".join(self.əlaqə) if self.əlaqə else None}


@dataclass
class Cədvəl:
    ad: str
    sahələr: list[Sahə] = field(default_factory=list)
    yer: Yer | None = None

    def açar(self) -> Sahə | None:
        return next((s for s in self.sahələr if s.açar), None)

    def sahə(self, ad: str) -> Sahə | None:
        return next((s for s in self.sahələr if s.ad == ad), None)


@dataclass
class Sxem:
    ad: str
    cədvəllər: list[Cədvəl] = field(default_factory=list)
    yol: Path | None = None

    def cədvəl(self, ad: str) -> Cədvəl | None:
        return next((c for c in self.cədvəllər if c.ad == ad), None)

    def lüğət(self) -> dict:
        return {"ad": self.ad, "cədvəllər": [
            {"ad": c.ad, "sahələr": [s.lüğət() for s in c.sahələr]}
            for c in self.cədvəllər]}


def lüğətdən(d: dict) -> Sxem:
    """Studio-nun cədvəl redaktorundan gələn JSON → Sxem."""
    s = Sxem(str(d.get("ad") or "Baza"))
    for c in d.get("cədvəllər") or []:
        cd = Cədvəl(str(c["ad"]))
        for f in c.get("sahələr") or []:
            əl = f.get("əlaqə")
            cd.sahələr.append(Sahə(
                str(f["ad"]), str(f.get("tip") or "mətn"),
                bool(f.get("açar")), bool(f.get("məcburi")),
                bool(f.get("tək")), f.get("standart"),
                bool(f.get("standartVar")) or f.get("standart") is not None,
                tuple(str(əl).split(".", 1)) if əl and "." in str(əl)
                else None))
        s.cədvəllər.append(cd)
    return s


# ═══════════════════════════════════════════════════════════════════════
#  Oxuma
# ═══════════════════════════════════════════════════════════════════════

class _Dayan(Exception):
    def __init__(self, mesaj, yer, qeyd="", *köməklər):
        super().__init__(mesaj)
        self.mesaj, self.yer, self.qeyd, self.köməklər = \
            mesaj, yer, qeyd, köməklər


class _Oxuyucu:
    def __init__(self, tokenlər):
        from .token import Növ
        self.N = Növ
        self.t = [t for t in tokenlər
                  if t.növ not in (Növ.SENED, Növ.DIREKTIV)]
        self.i = 0

    def bax(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def al(self):
        t = self.bax()
        if self.i < len(self.t) - 1:
            self.i += 1
        return t

    def söz(self, t, *s) -> bool:
        return t.növ in (self.N.AD, self.N.ACAR) and t.dəyər in s

    def boşları_keç(self):
        while self.bax().növ is self.N.SETIR_SONU:
            self.al()

    def ad(self, nə: str) -> tuple[str, Yer]:
        t = self.al()
        if t.növ not in (self.N.AD, self.N.ACAR):
            raise _Dayan(f"{nə} gözlənilirdi", t.yer)
        return str(t.dəyər), t.yer

    def sətir_sonu(self):
        t = self.bax()
        if t.növ not in (self.N.SETIR_SONU, self.N.FAYL_SONU):
            raise _Dayan("sətir sonu gözlənilirdi", t.yer,
                         f"`{t.dəyər}` artıqdır")
        self.boşları_keç()

    def sxem(self) -> Sxem:
        self.boşları_keç()
        t = self.al()
        if not self.söz(t, "sxem"):
            raise _Dayan("sxem faylı `sxem Ad` ilə başlamalıdır", t.yer)
        ad, _ = self.ad("sxem adı")
        s = Sxem(ad)
        self.sətir_sonu()
        while True:
            self.boşları_keç()
            t = self.bax()
            if self.söz(t, "son"):
                self.al()
                self.boşları_keç()
                if self.bax().növ is not self.N.FAYL_SONU:
                    raise _Dayan("`son`-dan sonra artıq mətn", self.bax().yer)
                return s
            if t.növ is self.N.FAYL_SONU:
                raise _Dayan("`sxem` bağlanmayıb — `son` gözlənilirdi", t.yer)
            if not self.söz(t, "cədvəl"):
                raise _Dayan("`cədvəl` və ya `son` gözlənilirdi", t.yer,
                             "", "nümunə: cədvəl tələbələr … son")
            s.cədvəllər.append(self.cədvəl())

    def cədvəl(self) -> Cədvəl:
        self.al()
        ad, yer = self.ad("cədvəl adı")
        c = Cədvəl(ad, yer=yer)
        self.sətir_sonu()
        while True:
            self.boşları_keç()
            t = self.bax()
            if self.söz(t, "son"):
                self.al()
                self.sətir_sonu()
                return c
            if t.növ is self.N.FAYL_SONU:
                raise _Dayan(f"`cədvəl {ad}` bağlanmayıb", t.yer)
            c.sahələr.append(self.sahə())

    def sahə(self) -> Sahə:
        ad, yer = self.ad("sahə adı")
        if not self.bax().opdur(":"):
            raise _Dayan("`:` və tip gözlənilirdi", self.bax().yer,
                         "sahə belə yazılır: ad: tip", "nümunə: ad: mətn")
        self.al()
        tip, tip_yeri = self.ad("tip")
        if tip not in TİPLƏR:
            from difflib import get_close_matches
            y = get_close_matches(tip, TİPLƏR, 1)
            raise _Dayan(f"`{tip}` tipi yoxdur", tip_yeri,
                         "icazəli: " + ", ".join(TİPLƏR),
                         *([f"bəlkə `{y[0]}`?"] if y else []))
        s = Sahə(ad, tip, yer=yer)
        while True:
            t = self.bax()
            if t.növ in (self.N.SETIR_SONU, self.N.FAYL_SONU):
                break
            if self.söz(t, *BAYRAQLAR):
                self.al()
                setattr(s, str(t.dəyər), True)
            elif t.opdur("="):
                self.al()
                s.standart, s.standart_var = self.dəyər(), True
            elif t.opdur("→") or t.opdur("->"):
                self.al()
                c, _ = self.ad("cədvəl adı")
                if not self.bax().opdur("."):
                    raise _Dayan("`cədvəl.sütun` gözlənilirdi", self.bax().yer)
                self.al()
                st, _ = self.ad("sütun adı")
                s.əlaqə = (c, st)
            else:
                raise _Dayan(f"`{t.dəyər}` burada gözlənilmirdi", t.yer,
                             "sahədən sonra: açar, məcburi, tək, "
                             "= standart, → cədvəl.sütun")
        self.sətir_sonu()
        return s

    def dəyər(self) -> Any:
        N = self.N
        t = self.al()
        if t.növ in (N.TAM, N.ONLUQ):
            return t.dəyər
        if t.opdur("-") and self.bax().növ in (N.TAM, N.ONLUQ):
            return -self.al().dəyər
        if t.növ is N.METN:
            return t.dəyər
        if self.söz(t, "doğru"):
            return True
        if self.söz(t, "yanlış"):
            return False
        if self.söz(t, "boş"):
            return None
        raise _Dayan("standart dəyər literal olmalıdır", t.yer)


def mətndən(mətn: str, ad: str = "<sxem>", x: XətaToplayıcı | None = None,
            yol: Path | None = None) -> Sxem | None:
    from .lekser import Lekser
    from .menbe import Mənbə
    x = x if x is not None else XətaToplayıcı()
    m = Mənbə.mətndən(mətn, ad, x)
    if m is None:
        return None
    m.yol = yol
    tokenlər = Lekser(m, x).leksə()
    if not x.uğurludur():
        return None
    try:
        s = _Oxuyucu(tokenlər).sxem()
    except _Dayan as d:
        x.xəta("ALQ-D001", d.mesaj, d.yer, d.qeyd, *d.köməklər)
        return None
    s.yol = yol
    yoxla(s, x)
    return s if x.uğurludur() else None


def fayldan(yol: Path | str, x: XətaToplayıcı | None = None) -> Sxem | None:
    yol = Path(yol)
    return mətndən(yol.read_text(encoding="utf-8"), yol.name, x, yol)


def yoxla(s: Sxem, x: XətaToplayıcı) -> None:
    adlar: set[str] = set()
    for c in s.cədvəllər:
        if not _AD.match(c.ad):
            x.xəta("ALQ-D002", f"`{c.ad}` cədvəl adı ola bilməz", c.yer,
                   "yalnız hərf, rəqəm və `_`")
        if c.ad in adlar:
            x.xəta("ALQ-D002", f"`{c.ad}` cədvəli təkrarlanır", c.yer)
        adlar.add(c.ad)
        sahə_adları: set[str] = set()
        for f in c.sahələr:
            if f.ad in sahə_adları:
                x.xəta("ALQ-D003", f"`{c.ad}.{f.ad}` sahəsi təkrarlanır",
                       f.yer)
            sahə_adları.add(f.ad)
        if sum(1 for f in c.sahələr if f.açar) > 1:
            x.xəta("ALQ-D004", f"`{c.ad}` cədvəlində bir neçə `açar` var",
                   c.yer, "hər cədvəldə bir açar sahə olur")
        if not c.sahələr:
            x.xəta("ALQ-D003", f"`{c.ad}` cədvəlində sahə yoxdur", c.yer)
    for c in s.cədvəllər:
        for f in c.sahələr:
            if f.əlaqə is None:
                continue
            hc = s.cədvəl(f.əlaqə[0])
            if hc is None or hc.sahə(f.əlaqə[1]) is None:
                x.xəta("ALQ-D005", f"`{c.ad}.{f.ad}` əlaqəsi "
                       f"`{'.'.join(f.əlaqə)}` tapılmadı", f.yer,
                       "əlaqə sxemdəki cədvəlin sahəsinə olmalıdır")


# ═══════════════════════════════════════════════════════════════════════
#  Yazma
# ═══════════════════════════════════════════════════════════════════════

def _literal(d: Any) -> str:
    from .forma import dəyər_yaz
    return dəyər_yaz(d)


def yaz(s: Sxem) -> str:
    n = [f"// {s.ad} — verilənlər bazası sxemi (Alqor Studio cədvəl "
         "redaktoru)", f"sxem {s.ad}"]
    for c in s.cədvəllər:
        n.append(f"    cədvəl {c.ad}")
        for f in c.sahələr:
            h = [f"        {f.ad}: {f.tip}"]
            h += [b for b in BAYRAQLAR if getattr(f, b)]
            if f.standart_var:
                h.append(f"= {_literal(f.standart)}")
            if f.əlaqə:
                h.append(f"→ {f.əlaqə[0]}.{f.əlaqə[1]}")
            n.append(" ".join(h))
        n.append("    son")
    n.append("son")
    return "\n".join(n) + "\n"


# ═══════════════════════════════════════════════════════════════════════
#  SQL (DDL) — sqlite / postgres / mysql
# ═══════════════════════════════════════════════════════════════════════

def _dialekt(ünvan_və_ya_növ: str) -> str:
    u = ünvan_və_ya_növ.lower()
    if u.startswith(("postgres", "postgresql")):
        return "postgres"
    if u.startswith(("mysql", "mariadb")):
        return "mysql"
    return "sqlite"


def _q(ad: str, d: str) -> str:
    return f"`{ad}`" if d == "mysql" else f'"{ad}"'


_SQL_TİP = {
    "sqlite": {"tam": "INTEGER", "onluq": "REAL", "mətn": "TEXT",
               "məntiq": "BOOLEAN", "tarix": "DATE", "tarixVaxt": "TIMESTAMP",
               "bayt": "BLOB"},
    "postgres": {"tam": "BIGINT", "onluq": "DOUBLE PRECISION", "mətn": "TEXT",
                 "məntiq": "BOOLEAN", "tarix": "DATE",
                 "tarixVaxt": "TIMESTAMP", "bayt": "BYTEA"},
    "mysql": {"tam": "BIGINT", "onluq": "DOUBLE", "mətn": "TEXT",
              "məntiq": "BOOLEAN", "tarix": "DATE", "tarixVaxt": "DATETIME",
              "bayt": "LONGBLOB"},
}


def _sql_literal(d: Any) -> str:
    if d is None:
        return "NULL"
    if d is True:
        return "TRUE"
    if d is False:
        return "FALSE"
    if isinstance(d, (int, float)):
        return repr(d)
    return "'" + str(d).replace("'", "''") + "'"


def sütun_sql(f: Sahə, d: str) -> str:
    tip = _SQL_TİP[d][f.tip]
    if d == "mysql" and f.tip == "mətn" and (f.tək or f.açar):
        tip = "VARCHAR(255)"           # MySQL TEXT-ə indeks qoymur
    h = [_q(f.ad, d)]
    if f.açar and f.tip == "tam":
        h.append({"sqlite": "INTEGER PRIMARY KEY AUTOINCREMENT",
                  "postgres": "BIGINT GENERATED BY DEFAULT AS IDENTITY "
                              "PRIMARY KEY",
                  "mysql": "BIGINT AUTO_INCREMENT PRIMARY KEY"}[d])
        return " ".join(h)
    h.append(tip)
    if f.açar:
        h.append("PRIMARY KEY")
    if f.məcburi and not f.açar:
        h.append("NOT NULL")
    if f.tək and not f.açar:
        h.append("UNIQUE")
    if f.standart_var and not (d == "mysql" and f.tip in ("mətn", "bayt")):
        h.append("DEFAULT " + _sql_literal(f.standart))
    return " ".join(h)


def cədvəl_sql(c: Cədvəl, d: str) -> str:
    sətirlər = [sütun_sql(f, d) for f in c.sahələr]
    for f in c.sahələr:
        if f.əlaqə:
            sətirlər.append(
                f"FOREIGN KEY ({_q(f.ad, d)}) REFERENCES "
                f"{_q(f.əlaqə[0], d)} ({_q(f.əlaqə[1], d)})")
    return (f"CREATE TABLE IF NOT EXISTS {_q(c.ad, d)} (\n    "
            + ",\n    ".join(sətirlər) + "\n)")


def ddl(s: Sxem, dialekt: str = "sqlite") -> list[str]:
    """Bütün cədvəllər — əlaqə sırası ilə (istinad olunan əvvəl)."""
    d = _dialekt(dialekt)
    return [cədvəl_sql(c, d) for c in _sıralı(s)]


def _sıralı(s: Sxem) -> list[Cədvəl]:
    sıra: list[Cədvəl] = []
    görülən: set[str] = set()

    def əlavə(c: Cədvəl, yol: tuple = ()) -> None:
        if c.ad in görülən or c.ad in yol:
            return
        for f in c.sahələr:
            if f.əlaqə and f.əlaqə[0] != c.ad:
                h = s.cədvəl(f.əlaqə[0])
                if h is not None:
                    əlavə(h, yol + (c.ad,))
        görülən.add(c.ad)
        sıra.append(c)
    for c in s.cədvəllər:
        əlavə(c)
    return sıra


def tətbiq_et(bağlantı: Any, s: Sxem) -> list[str]:
    """Çatışmayan cədvəlləri və sütunları yaradır. Qaytarır: icra
    olunan əmrlər. Mövcud sütunlar dəyişdirilmir, heç nə silinmir."""
    d = _dialekt(getattr(bağlantı, "ünvan", "") or "")
    mövcud = {c.lower() for c in bağlantı.cədvəllər()}
    əmrlər: list[str] = []
    for c in _sıralı(s):
        if c.ad.lower() not in mövcud:
            sql = cədvəl_sql(c, d)
            bağlantı.icra(sql)
            əmrlər.append(sql)
            continue
        var = {x["ad"].lower() for x in bağlantı.sütunlar(c.ad)}
        for f in c.sahələr:
            if f.ad.lower() in var:
                continue
            g = Sahə(f.ad, f.tip, False, False, f.tək and d != "sqlite",
                     f.standart, f.standart_var)
            sql = (f"ALTER TABLE {_q(c.ad, d)} ADD COLUMN "
                   f"{sütun_sql(g, d)}")
            bağlantı.icra(sql)
            əmrlər.append(sql)
    return əmrlər


def idxal(bağlantı: Any, ad: str = "Baza") -> Sxem:
    """Mövcud bazanın cədvəllərindən sxem (əlaqələr idxal olunmur)."""
    s = Sxem(ad)
    for cədvəl_adı in bağlantı.cədvəllər():
        c = Cədvəl(cədvəl_adı)
        for x in bağlantı.sütunlar(cədvəl_adı):
            c.sahələr.append(Sahə(x["ad"], _tip_tanı(x.get("tip") or ""),
                                  açar=bool(x.get("açar")),
                                  məcburi=not x.get("boşOlaBilər", True)
                                  and not x.get("açar")))
        s.cədvəllər.append(c)
    return s


def _tip_tanı(sql_tipi: str) -> str:
    t = sql_tipi.upper()
    if "INT" in t:
        return "tam"
    if any(k in t for k in ("REAL", "DOUB", "FLOA", "NUMERIC", "DECIMAL")):
        return "onluq"
    if "BOOL" in t:
        return "məntiq"
    if "TIMESTAMP" in t or "DATETIME" in t:
        return "tarixVaxt"
    if "DATE" in t:
        return "tarix"
    if "BLOB" in t or "BYTEA" in t or "BINARY" in t:
        return "bayt"
    return "mətn"


# ═══════════════════════════════════════════════════════════════════════
#  ORM model kodu (kodda `Tələbə.harada(…)` yazmaq üçün)
# ═══════════════════════════════════════════════════════════════════════

_ALQOR_TİP = {"tam": "tam", "onluq": "onluq", "mətn": "mətn",
              "məntiq": "məntiq", "tarix": "mətn", "tarixVaxt": "mətn",
              "bayt": "bayt"}


def sinif_adı(cədvəl: str) -> str:
    """`tələbələr` → `Tələbə`, `qrup_üzvləri` → `QrupÜzvü` (təxmini)."""
    hissələr = [h for h in cədvəl.split("_") if h]
    n = []
    for h in hissələr:
        for şəkilçi in ("lər", "lar"):
            if h.endswith(şəkilçi) and len(h) > len(şəkilçi) + 1:
                h = h[:-len(şəkilçi)]
                break
        from .elifba import böyüyə
        n.append(böyüyə(h[:1]) + h[1:])
    return "".join(n) or "Qeyd"


def xassə_adı(sütun: str) -> str:
    """Sütun adı Alqor açar sözüdürsə (`sinif`, `eger`) — `sinif_`."""
    from .acar_sozler import kanonikləşdir
    return sütun + "_" if kanonikləşdir(sütun)[0] is not None else sütun


def model_kodu(s: Sxem) -> str:
    n = [f"// {s.ad} — sxemdən yaradılan modellər (Alqor Studio). Əl ilə "
         "dəyişməyin:", "// sxem dəyişəndə fayl yenidən yaradılır.",
         "", "gətir verilənlər", ""]
    for c in s.cədvəllər:
        n.append(f'@cədvəl("{c.ad}")')
        n.append(f"sinif {sinif_adı(c.ad)} miras verilənlər.Model")
        for f in c.sahələr:
            if f.açar:
                n.append("    @açar")
            tip = _ALQOR_TİP[f.tip]
            if not (f.məcburi or f.açar):
                tip += "?"
            ad = xassə_adı(f.ad)
            if ad != f.ad:
                n.append(f'    @sütun("{f.ad}")')
            n.append(f"    xassə {ad}: {tip}")
        n.append("son")
        n.append("")
    return "\n".join(n)
