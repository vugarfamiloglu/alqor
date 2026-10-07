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

Sürücülər (hamısı asılılıqsız):
    sqlite://yol.db, sqlite::yaddaş:      Python-un daxili `sqlite3`-ü
    postgres://u:p@host:5432/baza         PostgreSQL protokolu v3 (_vb_pg)
    mysql://u:p@host:3306/baza            MySQL / MariaDB (_vb_mysql)
`gözlə b.sorğu(…)` də işləyir (adi dəyər `gözlə`-dən olduğu kimi keçir).
"""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı
from ._vb_ortaq import (MəhdudiyyətPozuldu, Nəticə, SürücüXətası,
                        gizli_ünvan, parametrləri_gəz)


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("VerilənlərXətası", mesaj, None, "ALQ-R013")


_AD = re.compile(r"^[^\W\d]\w*$")
_OPERATORLAR = {"=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "NOT LIKE",
                "IN", "NOT IN", "IS", "IS NOT", "bənzər", "içində"}


def _ad(x: Any, nə: str, sitat: str = '"') -> str:
    """Cədvəl/sütun adı — yalnız hərf, rəqəm, `_` (inyeksiyaya qarşı)."""
    if not isinstance(x, str) or not all(_AD.match(h) for h in x.split(".")):
        raise _xəta(f"yanlış {nə} adı: {x!r}")
    return ".".join(f"{sitat}{h}{sitat}" for h in x.split("."))


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


class _SqliteSürücü:
    ad = "sqlite"
    sitat = '"'
    qaytarma = False

    def __init__(self, ünvan: str, yol: str):
        try:
            self.c = sqlite3.connect(yol, check_same_thread=False,
                                     isolation_level=None)
        except sqlite3.Error as x:
            raise SürücüXətası(f"bağlantı alınmadı — {x}") from None
        self.c.execute("PRAGMA foreign_keys = ON")

    def icra(self, sql: str, p: tuple) -> Nəticə:
        try:
            k = self.c.execute(_dollar(sql), p)
        except sqlite3.IntegrityError as x:
            raise MəhdudiyyətPozuldu(str(x)) from None
        except sqlite3.Error as x:
            raise SürücüXətası(str(x)) from None
        n = Nəticə(say=k.rowcount, son_id=k.lastrowid or None)
        if k.description:
            n.sütunlar = [d[0] for d in k.description]
            n.sətirlər = [tuple(r) for r in k.fetchall()]
        return n

    def skript(self, sql: str) -> list[Nəticə]:
        try:
            self.c.executescript(sql)
        except sqlite3.IntegrityError as x:
            raise MəhdudiyyətPozuldu(str(x)) from None
        except sqlite3.Error as x:
            raise SürücüXətası(str(x)) from None
        return [Nəticə()]

    def bağla(self) -> None:
        self.c.close()

    def limit(self, limit: int | None, atla: int | None) -> str:
        if limit is None and atla is None:
            return ""
        s = f" LIMIT {int(limit) if limit is not None else -1}"
        return s + (f" OFFSET {int(atla)}" if atla is not None else "")

    def cədvəllər_sql(self) -> str:
        return ("SELECT name FROM sqlite_master WHERE type='table' AND name "
                "NOT LIKE 'sqlite_%' ORDER BY name")

    def tip(self, növ: str, açar: bool) -> str:
        if açar and növ == "tam":
            return "INTEGER PRIMARY KEY AUTOINCREMENT"
        return {"tam": "INTEGER", "onluq": "REAL", "məntiq": "BOOLEAN",
                "bayt": "BLOB"}.get(növ, "TEXT") + \
            (" PRIMARY KEY" if açar else "")


class Bağlantı:
    ALQOR_TİP_ADI = "bağlantı"

    def __init__(self, ünvan: str, sürücü: Any):
        self.ünvan = ünvan
        self.d = sürücü
        self.kilid = threading.RLock()
        self.tranzaksiyada = 0
        self.son_id: int | None = None

    @property
    def sitat(self) -> str:
        return self.d.sitat

    def __repr__(self) -> str:
        return f"<bağlantı {gizli_ünvan(self.ünvan)}>"

    def ad(self, x: Any, nə: str = "sütun") -> str:
        return _ad(x, nə, self.d.sitat)

    def _hazırla(self, sql: str) -> str:
        """PostgreSQL `?` bilmir — `$n`-siz sorğuda `?` → `$1, $2…`."""
        if self.d.ad != "postgres" or "?" not in sql:
            return sql
        nömrəli = []
        parametrləri_gəz(sql, lambda n_, i: nömrəli.append(n_) or "")
        if "$" in nömrəli:
            return sql
        say = iter(range(1, 10 ** 6))
        return parametrləri_gəz(
            sql, lambda n_, i: f"${i}" if n_ == "$" else f"${next(say)}")

    def _icra(self, sql: str, parametrlər: tuple) -> Nəticə:
        if self.d is None:
            raise _xəta("bağlantı bağlanıb")
        if not isinstance(sql, str):
            raise AlqorXəta("TipXətası", "SQL mətn olmalıdır", None,
                            "ALQ-T001")
        p = tuple(_dəyər(x) for x in parametrlər)
        try:
            with self.kilid:
                n = self.d.icra(self._hazırla(sql), p)
        except MəhdudiyyətPozuldu as x:
            raise AlqorXəta("MəhdudiyyətXətası", f"məhdudiyyət pozuldu: {x}",
                            None, "ALQ-R013") from None
        except SürücüXətası as x:
            raise _xəta(f"{x} — SQL: {sql.strip()[:200]}") from None
        if n.son_id:
            self.son_id = n.son_id
        return n

    def _əmr(self, sql: str) -> None:
        self._icra(sql, ())

    def sorğu(self, sql: str, *p) -> list[dict]:
        return self._icra(sql, p).lüğətlər()

    def bir_sətir(self, sql: str, *p) -> dict | None:
        r = self._icra(sql, p).lüğətlər()
        return r[0] if r else None

    def bir_dəyər(self, sql: str, *p) -> Any:
        r = self._icra(sql, p).sətirlər
        return r[0][0] if r and r[0] else None

    def icra(self, sql: str, *p) -> int:
        return self._icra(sql, p).say

    def skript(self, sql: str) -> None:
        try:
            with self.kilid:
                self.d.skript(sql)
        except MəhdudiyyətPozuldu as x:
            raise AlqorXəta("MəhdudiyyətXətası", f"məhdudiyyət pozuldu: {x}",
                            None, "ALQ-R013") from None
        except SürücüXətası as x:
            raise _xəta(str(x)) from None

    def tranzaksiya(self, icraçı, f) -> Any:
        return self._tranzaksiya(lambda: icraçı._çağır(f, [self], {}, None))

    def _tranzaksiya(self, f) -> Any:
        with self.kilid:
            iç = self.tranzaksiyada > 0
            ad = f"alqor_{self.tranzaksiyada}"
            self._əmr(f"SAVEPOINT {ad}" if iç else "BEGIN")
            self.tranzaksiyada += 1
            try:
                n = f()
            except BaseException:
                self.tranzaksiyada -= 1
                try:
                    self._əmr(f"ROLLBACK TO SAVEPOINT {ad}" if iç
                              else "ROLLBACK")
                    if iç:
                        self._əmr(f"RELEASE SAVEPOINT {ad}")
                except AlqorXəta:
                    pass
                raise
            self.tranzaksiyada -= 1
            self._əmr(f"RELEASE SAVEPOINT {ad}" if iç else "COMMIT")
            return n

    tranzaksiya_python = _tranzaksiya

    def cədvəllər(self) -> list[str]:
        return [s[0] for s in self._icra(self.d.cədvəllər_sql(), ()).sətirlər]

    def sütunlar(self, cədvəl: str) -> list[dict]:
        if self.d.ad == "sqlite":
            return [{"ad": s["name"], "tip": s["type"], "boşOlaBilər":
                     not s["notnull"], "açar": bool(s["pk"])}
                    for s in self._icra(
                        f"PRAGMA table_info({self.ad(cədvəl, 'cədvəl')})",
                        ()).lüğətlər()]
        _ad(cədvəl, "cədvəl")
        return [{"ad": s["ad"], "tip": s["tip"], "boşOlaBilər": bool(s["boş"]),
                 "açar": bool(s["açar"])}
                for s in self._icra(self.d.sütunlar_sql(), (cədvəl,))
                .lüğətlər()]

    def miqrasiya(self, qovluq: str) -> list[str]:
        q = Path(qovluq)
        if not q.is_dir():
            raise AlqorXəta("FaylTapılmadıXətası",
                            f'"{qovluq}" qovluğu tapılmadı', None, "ALQ-R009")
        mətn_tipi = "VARCHAR(191)" if self.d.ad == "mysql" else "TEXT"
        self._əmr("CREATE TABLE IF NOT EXISTS _alqor_miqrasiyalar "
                  f"(ad {mətn_tipi} PRIMARY KEY, vaxt TIMESTAMP DEFAULT "
                  "CURRENT_TIMESTAMP)")
        olan = {s["ad"] for s in self.sorğu(
            "SELECT ad FROM _alqor_miqrasiyalar")}
        tətbiq = []
        for f in sorted(q.glob("*.sql")):
            if f.name in olan:
                continue
            if not re.fullmatch(r"[\w.\-]+", f.name):
                raise _xəta(f"miqrasiya faylının adı yanlışdır: {f.name}")
            sql = f.read_text(encoding="utf-8").strip().rstrip(";")
            with self.kilid:
                try:
                    self.d.skript(
                        "BEGIN;\n" + sql + ";\nINSERT INTO "
                        "_alqor_miqrasiyalar (ad) VALUES ('" + f.name
                        + "');\nCOMMIT;")
                except SürücüXətası as x:
                    try:
                        # `skript` yox: sqlite3-ün executescript-i əvvəlcə
                        # COMMIT edərdi
                        self.d.icra("ROLLBACK", ())
                    except SürücüXətası:
                        pass
                    raise _xəta(f"miqrasiya {f.name}: {x}") from None
            tətbiq.append(f.name)
        return tətbiq

    def bağla(self) -> None:
        if self.d is not None:
            self.d.bağla()
            self.d = None


# ── Sorğu qurucusu ────────────────────────────────────────────────────

class Qurucu:
    ALQOR_TİP_ADI = "sorğuQurucusu"

    def __init__(self, b: Bağlantı, cədvəl: str):
        self.b = b
        self.cədvəl = b.ad(cədvəl, "cədvəl")
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
        n.sütunlar = ", ".join(self.b.ad(s) for s in sütunlar) or "*"
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
        s = self.b.ad(sütun)
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
        n.sıra.append(f"{self.b.ad(sütun)} {i}")
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
        s += self.b.d.limit(self.limit_, self.atla_)
        return s, p

    def al(self) -> list[dict]:
        s, p = self.sql()
        return self.b._icra(s, tuple(p)).lüğətlər()

    def ilk(self) -> dict | None:
        r = self.limit(1).al()
        return r[0] if r else None

    def say(self) -> int:
        h, p = self._harada()
        return int(self.b._icra(f"SELECT COUNT(*) FROM {self.cədvəl}{h}",
                                tuple(p)).sətirlər[0][0])

    def əlavə_et(self, l: Any) -> int | None:
        if isinstance(l, Nümunə):
            l = l.sahələr
        if isinstance(l, list):
            return self.b.tranzaksiya_python(lambda: [self.əlavə_et(x)
                                                      for x in l])[-1] \
                if l else None
        if not isinstance(l, dict) or not l:
            raise _xəta("`əlavəEt` boş olmayan lüğət gözləyir")
        sütunlar = ", ".join(self.b.ad(a) for a in l)
        sql = (f"INSERT INTO {self.cədvəl} ({sütunlar}) VALUES "
               f"({', '.join('?' * len(l))})")
        if self.b.d.qaytarma:
            k = self.b._icra(sql + " RETURNING *", tuple(l.values()))
            if not k.sətirlər:
                return None
            r = dict(zip(k.sütunlar, k.sətirlər[0]))
            return r.get("id", k.sətirlər[0][0])
        return self.b._icra(sql, tuple(l.values())).son_id

    def yenilə(self, l: dict) -> int:
        if not isinstance(l, dict) or not l:
            raise _xəta("`yenilə` boş olmayan lüğət gözləyir")
        if not self.şərtlər:
            raise _xəta("`yenilə` şərtsiz bütün sətirləri dəyişərdi — "
                        "`harada(…)` əlavə edin")
        h, p = self._harada()
        təyin = ", ".join(f"{self.b.ad(a)} = ?" for a in l)
        return self.b._icra(f"UPDATE {self.cədvəl} SET {təyin}{h}",
                            tuple(list(l.values()) + p)).say

    def sil(self) -> int:
        if not self.şərtlər:
            raise _xəta("`sil` şərtsiz bütün cədvəli silərdi — "
                        "`harada(…)` əlavə edin")
        h, p = self._harada()
        return self.b._icra(f"DELETE FROM {self.cədvəl}{h}",
                            tuple(p)).say


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

    def sqlite(yol: str) -> Bağlantı:
        try:
            return Bağlantı(ünvan, _SqliteSürücü(ünvan, yol))
        except SürücüXətası as x:
            raise _xəta(f"{ünvan}: {x}") from None

    if ünvan in ("sqlite::yaddaş:", "sqlite::memory:", ":yaddaş:"):
        return sqlite(":memory:")
    if ünvan.startswith("sqlite://"):
        yol = ünvan[len("sqlite://"):]
        if not yol:
            raise _xəta("sqlite yolu boşdur: sqlite://./ad.db")
        Path(yol).parent.mkdir(parents=True, exist_ok=True)
        return sqlite(yol)
    if ünvan.endswith((".db", ".sqlite", ".sqlite3")) and "://" not in ünvan:
        return sqlite(ünvan)
    sxem = ünvan.split("://")[0] if "://" in ünvan else ""
    try:
        if sxem in ("postgres", "postgresql"):
            from ._vb_pg import PgSürücü
            return Bağlantı(ünvan, PgSürücü(ünvan))
        if sxem in ("mysql", "mariadb"):
            from ._vb_mysql import MySürücü
            return Bağlantı(ünvan, MySürücü(ünvan))
    except SürücüXətası as x:
        raise AlqorXəta("BağlantıXətası", f"{gizli_ünvan(ünvan)}: {x}",
                        None, "ALQ-R013") from None
    raise _xəta(f"bağlantı ünvanı tanınmadı: {gizli_ünvan(ünvan)!r} "
                "(sqlite://yol.db, postgres://…, mysql://…)")


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
