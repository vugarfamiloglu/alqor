"""
`verilənlər` — verilənlər bazası (§ 10.13).

    gətir verilənlər

    dəyişən b = verilənlər.bağlan("sqlite://./məlumat.db")
    b.icra("CREATE TABLE IF NOT EXISTS tələbə (id INTEGER PRIMARY KEY,
                                               ad TEXT, bal INTEGER)")
    b.icra("INSERT INTO tələbə (ad, bal) VALUES ($1, $2)", "Aysel", 95)

    hər s üçün b.sorğu("SELECT * FROM tələbə WHERE bal > $1", 80) içində
        yaz(s["ad"])
    son
    dəyişən say = b.birDəyər("SELECT COUNT(*) FROM tələbə")

    // Sorğu qurucusu — SQL yazmadan
    dəyişən əlaçılar = b.cədvəl("tələbə")
        .seç("ad", "bal")
        .harada("bal", ">=", 90)
        .sırala("bal", "azalan")
        .limit(10)
        .al()
    b.cədvəl("tələbə").əlavəEt({"ad": "Kamran", "bal": 88})
    b.cədvəl("tələbə").harada("id", "=", 1).yenilə({"bal": 97})

    // Tranzaksiya: funksiya xəta atsa hamısı geri qaytarılır
    b.tranzaksiya((t) => t.icra("UPDATE hesab SET balans = balans - 100"))

    b.miqrasiyaEt("miqrasiyalar/")     // 001_*.sql, 002_*.sql … bir dəfə

Parametrlər: `$1, $2…` (PostgreSQL üslubu) və ya `?`. Dəyərlər
HEÇ VAXT SQL mətninə yapışdırılmır — SQL inyeksiyası mümkün deyil.
Sorğu qurucusunda cədvəl/sütun adları və operatorlar yoxlanılır.

Hazırda SQLite (Python-un daxili `sqlite3`). `postgres://` və
`mysql://` bağlantıları üçün sürücü planlaşdırılır. `gözlə b.sorğu(…)`
də işləyir (adi dəyər `gözlə`-dən olduğu kimi keçir).
"""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("VerilənlərXətası", mesaj, None, "ALQ-R013")


_AD = re.compile(r"^[^\W\d]\w*$")
_OPERATORLAR = {"=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "NOT LIKE",
                "IN", "NOT IN", "IS", "IS NOT", "bənzər", "içində"}


def _ad(x: Any, nə: str) -> str:
    """Cədvəl/sütun adı — yalnız hərf, rəqəm, `_` (inyeksiyaya qarşı)."""
    if not isinstance(x, str) or not all(_AD.match(h) for h in x.split(".")):
        raise _xəta(f"yanlış {nə} adı: {x!r}")
    return ".".join(f'"{h}"' for h in x.split("."))


def _dollar(sql: str) -> str:
    """`$1` → `?1` (SQLite nömrəli parametri); mətn literalları toxunulmur."""
    n: list[str] = []
    i = 0
    while i < len(sql):
        c = sql[i]
        if c in "'\"":
            j = sql.find(c, i + 1)
            while j != -1 and sql[j + 1:j + 2] == c:
                j = sql.find(c, j + 2)
            j = len(sql) - 1 if j == -1 else j
            n.append(sql[i:j + 1])
            i = j + 1
            continue
        if c == "$" and i + 1 < len(sql) and sql[i + 1].isdigit():
            j = i + 1
            while j < len(sql) and sql[j].isdigit():
                j += 1
            n.append("?" + sql[i + 1:j])
            i = j
            continue
        n.append(c)
        i += 1
    return "".join(n)


def _dəyər(d: Any) -> Any:
    if d is True:
        return 1
    if d is False:
        return 0
    if d is None or isinstance(d, (int, float, str, bytes)):
        return d
    raise _xəta(f"`{tip_adı(d)}` bazaya yazıla bilmir — mətn, ədəd, "
                "məntiq, bayt və ya boş olmalıdır")


class Bağlantı:
    ALQOR_TİP_ADI = "bağlantı"

    def __init__(self, ünvan: str, yol: str):
        self.ünvan = ünvan
        self.yol = yol
        self.kilid = threading.RLock()
        try:
            self.c = sqlite3.connect(yol, check_same_thread=False,
                                     isolation_level=None)
        except sqlite3.Error as x:
            raise _xəta(f"{ünvan}: bağlantı alınmadı — {x}")
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA foreign_keys = ON")
        self.tranzaksiyada = 0
        self.son_id: int | None = None

    def __repr__(self) -> str:
        return f"<bağlantı {self.ünvan}>"

    def _icra(self, sql: str, parametrlər: tuple) -> sqlite3.Cursor:
        if self.c is None:
            raise _xəta("bağlantı bağlanıb")
        if not isinstance(sql, str):
            raise AlqorXəta("TipXətası", "SQL mətn olmalıdır", None,
                            "ALQ-T001")
        p = tuple(_dəyər(x) for x in parametrlər)
        try:
            with self.kilid:
                k = self.c.execute(_dollar(sql), p)
                if k.lastrowid:
                    self.son_id = k.lastrowid
                return k
        except sqlite3.IntegrityError as x:
            raise AlqorXəta("MəhdudiyyətXətası", f"məhdudiyyət pozuldu: {x}",
                            None, "ALQ-R013")
        except sqlite3.Error as x:
            raise _xəta(f"{x} — SQL: {sql.strip()[:200]}")

    def sorğu(self, sql: str, *p) -> list[dict]:
        return [dict(s) for s in self._icra(sql, p).fetchall()]

    def bir_sətir(self, sql: str, *p) -> dict | None:
        s = self._icra(sql, p).fetchone()
        return dict(s) if s is not None else None

    def bir_dəyər(self, sql: str, *p) -> Any:
        s = self._icra(sql, p).fetchone()
        return s[0] if s is not None else None

    def icra(self, sql: str, *p) -> int:
        return self._icra(sql, p).rowcount

    def skript(self, sql: str) -> None:
        try:
            with self.kilid:
                self.c.executescript(sql)
        except sqlite3.Error as x:
            raise _xəta(str(x))

    def tranzaksiya(self, icraçı, f) -> Any:
        with self.kilid:
            iç = self.tranzaksiyada > 0
            ad = f"alqor_{self.tranzaksiyada}"
            self.c.execute(f"SAVEPOINT {ad}" if iç else "BEGIN")
            self.tranzaksiyada += 1
            try:
                n = icraçı._çağır(f, [self], {}, None)
            except BaseException:
                self.tranzaksiyada -= 1
                self.c.execute(f"ROLLBACK TO {ad}" if iç else "ROLLBACK")
                if iç:
                    self.c.execute(f"RELEASE {ad}")
                raise
            self.tranzaksiyada -= 1
            self.c.execute(f"RELEASE {ad}" if iç else "COMMIT")
            return n

    def cədvəllər(self) -> list[str]:
        return [s[0] for s in self._icra(
            "SELECT name FROM sqlite_master WHERE type='table' AND name "
            "NOT LIKE 'sqlite_%' ORDER BY name", ()).fetchall()]

    def sütunlar(self, cədvəl: str) -> list[dict]:
        return [{"ad": s["name"], "tip": s["type"], "boşOlaBilər":
                 not s["notnull"], "açar": bool(s["pk"])}
                for s in self._icra(f"PRAGMA table_info({_ad(cədvəl, 'cədvəl')})",
                                    ()).fetchall()]

    def miqrasiya(self, qovluq: str) -> list[str]:
        q = Path(qovluq)
        if not q.is_dir():
            raise AlqorXəta("FaylTapılmadıXətası",
                            f'"{qovluq}" qovluğu tapılmadı', None, "ALQ-R009")
        self._icra("CREATE TABLE IF NOT EXISTS _alqor_miqrasiyalar "
                   "(ad TEXT PRIMARY KEY, vaxt TEXT DEFAULT "
                   "CURRENT_TIMESTAMP)", ())
        olan = {s["ad"] for s in self.sorğu(
            "SELECT ad FROM _alqor_miqrasiyalar")}
        tətbiq = []
        for f in sorted(q.glob("*.sql")):
            if f.name in olan:
                continue
            sql = f.read_text(encoding="utf-8")
            with self.kilid:
                try:
                    self.c.executescript(
                        "BEGIN;\n" + sql + "\n;INSERT INTO "
                        "_alqor_miqrasiyalar (ad) VALUES ('"
                        + f.name.replace("'", "''") + "');\nCOMMIT;")
                except sqlite3.Error as x:
                    if self.c.in_transaction:
                        self.c.execute("ROLLBACK")
                    raise _xəta(f"miqrasiya {f.name}: {x}")
            tətbiq.append(f.name)
        return tətbiq

    def bağla(self) -> None:
        if self.c is not None:
            self.c.close()
            self.c = None


# ── Sorğu qurucusu ────────────────────────────────────────────────────

class Qurucu:
    ALQOR_TİP_ADI = "sorğuQurucusu"

    def __init__(self, b: Bağlantı, cədvəl: str):
        self.b = b
        self.cədvəl = _ad(cədvəl, "cədvəl")
        self.sütunlar = "*"
        self.şərtlər: list[tuple[str, str, list]] = []
        self.sıra: list[str] = []
        self.limit_: int | None = None
        self.atla_: int | None = None

    def _kopya(self) -> "Qurucu":
        n = Qurucu.__new__(Qurucu)
        n.__dict__.update(self.__dict__)
        n.şərtlər = list(self.şərtlər)
        n.sıra = list(self.sıra)
        return n

    def seç(self, *sütunlar) -> "Qurucu":
        n = self._kopya()
        n.sütunlar = ", ".join(_ad(s, "sütun") for s in sütunlar) or "*"
        return n

    def harada(self, sütun: str, op: str, dəyər: Any = None,
               bağlayıcı: str = "AND") -> "Qurucu":
        n = self._kopya()
        op_ = str(op).upper() if str(op).isascii() else str(op)
        op_ = {"BƏNZƏR": "LIKE", "bənzər": "LIKE", "içində": "IN",
               "İÇİNDƏ": "IN"}.get(op_, op_)
        if op_ not in _OPERATORLAR:
            raise _xəta(f"operator tanınmır: {op!r} — "
                        "=, !=, <, <=, >, >=, LIKE, IN, IS")
        s = _ad(sütun, "sütun")
        if op_ in ("IN", "NOT IN"):
            siyahı = list(dəyər) if isinstance(dəyər, (list, tuple, set)) \
                else [dəyər]
            if not siyahı:
                parça, p = ("0 = 1" if op_ == "IN" else "1 = 1"), []
            else:
                parça = f"{s} {op_} ({', '.join('?' * len(siyahı))})"
                p = [_dəyər(x) for x in siyahı]
        elif dəyər is None and op_ in ("=", "IS"):
            parça, p = f"{s} IS NULL", []
        elif dəyər is None and op_ in ("!=", "<>", "IS NOT"):
            parça, p = f"{s} IS NOT NULL", []
        else:
            parça, p = f"{s} {op_} ?", [_dəyər(dəyər)]
        n.şərtlər.append((bağlayıcı, parça, p))
        return n

    def sırala(self, sütun: str, istiqamət: str = "artan") -> "Qurucu":
        n = self._kopya()
        i = {"artan": "ASC", "asc": "ASC", "azalan": "DESC",
             "desc": "DESC"}.get(str(istiqamət).lower())
        if i is None:
            raise _xəta("istiqamət `artan` və ya `azalan` olmalıdır")
        n.sıra.append(f"{_ad(sütun, 'sütun')} {i}")
        return n

    def limit(self, n_: int) -> "Qurucu":
        n = self._kopya()
        n.limit_ = int(n_)
        return n

    def atla(self, n_: int) -> "Qurucu":
        n = self._kopya()
        n.atla_ = int(n_)
        return n

    def _harada(self) -> tuple[str, list]:
        if not self.şərtlər:
            return "", []
        parçalar, p = [], []
        for i, (bağ, parça, x) in enumerate(self.şərtlər):
            parçalar.append(parça if i == 0 else f"{bağ} {parça}")
            p.extend(x)
        return " WHERE " + " ".join(parçalar), p

    def sql(self) -> tuple[str, list]:
        h, p = self._harada()
        s = f"SELECT {self.sütunlar} FROM {self.cədvəl}{h}"
        if self.sıra:
            s += " ORDER BY " + ", ".join(self.sıra)
        if self.limit_ is not None or self.atla_ is not None:
            s += f" LIMIT {self.limit_ if self.limit_ is not None else -1}"
        if self.atla_ is not None:
            s += f" OFFSET {self.atla_}"
        return s, p

    def al(self) -> list[dict]:
        s, p = self.sql()
        return [dict(r) for r in self.b._icra(s, tuple(p)).fetchall()]

    def ilk(self) -> dict | None:
        r = self.limit(1).al()
        return r[0] if r else None

    def say(self) -> int:
        h, p = self._harada()
        return self.b._icra(f"SELECT COUNT(*) FROM {self.cədvəl}{h}",
                            tuple(p)).fetchone()[0]

    def əlavə_et(self, l: Any) -> int | None:
        if isinstance(l, Nümunə):
            l = l.sahələr
        if isinstance(l, list):
            return self.b.tranzaksiya_python(lambda: [self.əlavə_et(x)
                                                      for x in l])[-1] \
                if l else None
        if not isinstance(l, dict) or not l:
            raise _xəta("`əlavəEt` boş olmayan lüğət gözləyir")
        sütunlar = ", ".join(_ad(a, "sütun") for a in l)
        k = self.b._icra(f"INSERT INTO {self.cədvəl} ({sütunlar}) VALUES "
                         f"({', '.join('?' * len(l))})", tuple(l.values()))
        return k.lastrowid

    def yenilə(self, l: dict) -> int:
        if not isinstance(l, dict) or not l:
            raise _xəta("`yenilə` boş olmayan lüğət gözləyir")
        if not self.şərtlər:
            raise _xəta("`yenilə` şərtsiz bütün sətirləri dəyişərdi — "
                        "`harada(…)` əlavə edin")
        h, p = self._harada()
        təyin = ", ".join(f"{_ad(a, 'sütun')} = ?" for a in l)
        return self.b._icra(f"UPDATE {self.cədvəl} SET {təyin}{h}",
                            tuple(list(l.values()) + p)).rowcount

    def sil(self) -> int:
        if not self.şərtlər:
            raise _xəta("`sil` şərtsiz bütün cədvəli silərdi — "
                        "`harada(…)` əlavə edin")
        h, p = self._harada()
        return self.b._icra(f"DELETE FROM {self.cədvəl}{h}",
                            tuple(p)).rowcount


def _tranzaksiya_python(self, f):
    with self.kilid:
        self.c.execute("SAVEPOINT alqor_py")
        try:
            n = f()
        except BaseException:
            self.c.execute("ROLLBACK TO alqor_py")
            self.c.execute("RELEASE alqor_py")
            raise
        self.c.execute("RELEASE alqor_py")
        return n


Bağlantı.tranzaksiya_python = _tranzaksiya_python


Bağlantı.ALQOR_METODLARI = {
    "sorğu": lambda i, b, s, *p: b.sorğu(s, *p),
    "birSətir": lambda i, b, s, *p: b.bir_sətir(s, *p),
    "birDəyər": lambda i, b, s, *p: b.bir_dəyər(s, *p),
    "icra": lambda i, b, s, *p: b.icra(s, *p),
    "skript": lambda i, b, s: b.skript(s),
    "sonId": lambda i, b: b.son_id,
    "tranzaksiya": lambda i, b, f: b.tranzaksiya(i, f),
    "cədvəl": lambda i, b, ad: Qurucu(b, ad),
    "cədvəllər": lambda i, b: b.cədvəllər(),
    "sütunlar": lambda i, b, c: b.sütunlar(c),
    "miqrasiyaEt": lambda i, b, q: b.miqrasiya(q),
    "bağla": lambda i, b: b.bağla(),
}

Qurucu.ALQOR_METODLARI = {
    "seç": lambda i, q, *s: q.seç(*s),
    "harada": lambda i, q, s, o, d=None: q.harada(s, o, d),
    "vəHarada": lambda i, q, s, o, d=None: q.harada(s, o, d, "AND"),
    "yaHarada": lambda i, q, s, o, d=None: q.harada(s, o, d, "OR"),
    "sırala": lambda i, q, s, y="artan": q.sırala(s, y),
    "limit": lambda i, q, n: q.limit(n),
    "atla": lambda i, q, n: q.atla(n),
    "al": lambda i, q: q.al(),
    "ilk": lambda i, q: q.ilk(),
    "say": lambda i, q: q.say(),
    "əlavəEt": lambda i, q, l: q.əlavə_et(l),
    "yenilə": lambda i, q, l: q.yenilə(l),
    "sil": lambda i, q: q.sil(),
    "sql": lambda i, q: q.sql()[0],
}


def bağlan(ünvan: str) -> Bağlantı:
    if not isinstance(ünvan, str):
        raise AlqorXəta("TipXətası", "bağlantı ünvanı mətn olmalıdır", None,
                        "ALQ-T001")
    if ünvan in ("sqlite::yaddaş:", "sqlite::memory:", ":yaddaş:"):
        return Bağlantı(ünvan, ":memory:")
    if ünvan.startswith("sqlite://"):
        yol = ünvan[len("sqlite://"):]
        if not yol:
            raise _xəta("sqlite yolu boşdur: sqlite://./ad.db")
        Path(yol).parent.mkdir(parents=True, exist_ok=True)
        return Bağlantı(ünvan, yol)
    if ünvan.endswith((".db", ".sqlite", ".sqlite3")) and "://" not in ünvan:
        return Bağlantı(ünvan, ünvan)
    sxem = ünvan.split("://")[0] if "://" in ünvan else ünvan
    if sxem in ("postgres", "postgresql", "mysql", "mariadb"):
        raise _xəta(f"`{sxem}` sürücüsü hələ hazır deyil — hazırda "
                    "sqlite://yol.db dəstəklənir")
    raise _xəta(f"bağlantı ünvanı tanınmadı: {ünvan!r} (nümunə: "
                "sqlite://./məlumat.db)")


def qur(icraçı) -> dict[str, Any]:
    return {"bağlan": Daxili("bağlan", bağlan, 1, 1)}


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    return {"bağlan": F(T.MƏTN, qaytarır=T.Sadə("bağlantı"))}


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    m, e, i = T.MƏTN, T.İSTƏNİLƏN, T.TAM
    sət = T.Lüğət(m, e)
    Q = T.Sadə("sorğuQurucusu")
    return {
        "bağlantı": {
            "sorğu": Fsərbəst(T.Siyahı(sət)),
            "birSətir": Fsərbəst(T.ixtiyari(sət)),
            "birDəyər": Fsərbəst(e), "icra": Fsərbəst(i),
            "skript": F(m, qaytarır=T.HEÇ),
            "sonId": F(qaytarır=T.ixtiyari(i)),
            "tranzaksiya": F(e, qaytarır=e),
            "cədvəl": F(m, qaytarır=Q),
            "cədvəllər": F(qaytarır=T.Siyahı(m)),
            "sütunlar": F(m, qaytarır=T.Siyahı(sət)),
            "miqrasiyaEt": F(m, qaytarır=T.Siyahı(m)),
            "bağla": F(qaytarır=T.HEÇ),
        },
        "sorğuQurucusu": {
            "seç": Fsərbəst(Q),
            "harada": F(m, m, e, qaytarır=Q, standart=1),
            "vəHarada": F(m, m, e, qaytarır=Q, standart=1),
            "yaHarada": F(m, m, e, qaytarır=Q, standart=1),
            "sırala": F(m, m, qaytarır=Q, standart=1),
            "limit": F(i, qaytarır=Q), "atla": F(i, qaytarır=Q),
            "al": F(qaytarır=T.Siyahı(sət)),
            "ilk": F(qaytarır=T.ixtiyari(sət)),
            "say": F(qaytarır=i),
            "əlavəEt": F(e, qaytarır=T.ixtiyari(i)),
            "yenilə": F(T.Lüğət(), qaytarır=i), "sil": F(qaytarır=i),
            "sql": F(qaytarır=m),
        },
    }
