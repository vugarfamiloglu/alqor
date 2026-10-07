"""
`verilənlər` — eyni sınaqlar hər sürücüdə (SQLite, PostgreSQL, MySQL).

PostgreSQL / MySQL sınaqları yalnız ünvan verildikdə işləyir:

    ALQOR_SINAQ_PG=postgres://u:p@127.0.0.1:5432/baza
    ALQOR_SINAQ_MYSQL=mysql://u:p@127.0.0.1:3306/baza
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.deyerler import AlqorXəta                         # noqa: E402
from alqor.modullar import verilenler as V                   # noqa: E402
from alqor.modullar._vb_ortaq import parametrləri_gəz        # noqa: E402


class _Ortaq:
    ÜNVAN = ""

    def setUp(self):
        if not self.ÜNVAN:
            self.skipTest("sınaq bazası verilməyib")
        self.b = V.bağlan(self.ÜNVAN)
        self.addCleanup(self.b.bağla)
        for c in ("sifariş", "tələbə", "a", "_alqor_miqrasiyalar"):
            self.b.icra(f"DROP TABLE IF EXISTS {self.b.ad(c, 'cədvəl')}")
        d = self.b.d
        self.b.icra(
            f"CREATE TABLE {self.b.ad('tələbə', 'cədvəl')} ("
            f"id {d.tip('tam', True)}, ad VARCHAR(100) UNIQUE NOT NULL, "
            f"bal INTEGER, aktiv BOOLEAN, şəkil {d.tip('bayt', False)}, "
            f"qeyd TEXT)")

    def q(self):
        return V.Qurucu(self.b, "tələbə")

    def test_əlavə_sorğu_və_id(self):
        i1 = self.q().əlavə_et({"ad": "Aysel", "bal": 95, "aktiv": True})
        i2 = self.q().əlavə_et({"ad": "Kamran", "bal": 70, "aktiv": False})
        self.assertIsInstance(i1, int)
        self.assertEqual(i2, i1 + 1)
        r = self.b.sorğu("SELECT ad, bal FROM tələbə WHERE bal > $1 "
                         "ORDER BY bal", 60)
        self.assertEqual(r, [{"ad": "Kamran", "bal": 70},
                             {"ad": "Aysel", "bal": 95}])
        self.assertEqual(self.b.bir_dəyər(
            "SELECT ad FROM tələbə WHERE id = ?", i2), "Kamran")
        self.assertEqual(int(self.b.bir_dəyər(
            "SELECT COUNT(*) FROM tələbə")), 2)
        self.assertIsNone(self.b.bir_sətir(
            "SELECT * FROM tələbə WHERE id = $1", 999))

    def test_dəyərlərin_gediş_dönüşü(self):
        bayt = bytes(range(256))
        çətin = "o'q \"dırnaq\" \\ ə ş 😀 \n\tson"   # NUL-u PostgreSQL mətndə saxlamır
        self.q().əlavə_et({"ad": "x", "bal": None, "aktiv": True,
                           "şəkil": bayt, "qeyd": çətin})
        s = self.b.bir_sətir("SELECT * FROM tələbə WHERE ad = $1", "x")
        self.assertEqual(s["şəkil"], bayt)
        self.assertEqual(s["qeyd"], çətin)
        self.assertIsNone(s["bal"])
        self.assertIn(s["aktiv"], (True, 1))

    def test_inyeksiya_mümkün_deyil(self):
        pis = "x'); DROP TABLE tələbə; --"
        self.q().əlavə_et({"ad": pis})
        self.assertEqual(self.b.bir_dəyər(
            "SELECT ad FROM tələbə WHERE ad = ?", pis), pis)
        self.assertIn("tələbə", self.b.cədvəllər())
        # Mətn literalındakı `?` və `$1` parametr deyil
        self.assertEqual(self.b.bir_dəyər(
            "SELECT 'nə? $1' FROM tələbə WHERE ad = ?", pis), "nə? $1")

    def test_qurucu(self):
        for i, (ad, bal) in enumerate([("A", 50), ("B", 90), ("C", 75),
                                       ("D", 90)]):
            self.q().əlavə_et({"ad": ad, "bal": bal, "aktiv": i % 2 == 0})
        r = self.q().seç("ad").harada("bal", ">=", 75).sırala(
            "bal", "azalan").sırala("ad").al()
        self.assertEqual([x["ad"] for x in r], ["B", "D", "C"])
        self.assertEqual([x["ad"] for x in self.q().sırala("ad").atla(1)
                          .limit(2).al()], ["B", "C"])
        self.assertEqual([x["ad"] for x in self.q().sırala("ad").atla(3)
                          .al()], ["D"])
        self.assertEqual(self.q().harada("ad", "içində", ["A", "C"]).say(), 2)
        self.assertEqual(self.q().harada("ad", "içində", []).say(), 0)
        self.assertEqual(self.q().harada("bal", "=", 90).yenilə(
            {"bal": 91}), 2)
        self.assertEqual(self.q().harada("ad", "bənzər", "%").sil(), 4)

    def test_tranzaksiya(self):
        def iş():
            self.q().əlavə_et({"ad": "T1"})

            def iç():
                self.q().əlavə_et({"ad": "T2"})
                raise AlqorXəta("Xəta", "iç")
            with self.assertRaises(AlqorXəta):
                self.b.tranzaksiya_python(iç)       # yalnız iç geri qayıdır
            return 1
        self.b.tranzaksiya_python(iş)
        self.assertEqual([x["ad"] for x in self.q().al()], ["T1"])

        def pis():
            self.q().əlavə_et({"ad": "T3"})
            raise AlqorXəta("Xəta", "x")
        with self.assertRaises(AlqorXəta):
            self.b.tranzaksiya_python(pis)
        self.assertEqual(self.q().say(), 1)

    def test_məhdudiyyət(self):
        self.q().əlavə_et({"ad": "U"})
        with self.assertRaises(AlqorXəta) as k:
            self.q().əlavə_et({"ad": "U"})
        self.assertEqual(k.exception.tip, "MəhdudiyyətXətası")
        with self.assertRaises(AlqorXəta) as k:
            self.b.icra("SELEKT 1")
        self.assertEqual(k.exception.tip, "VerilənlərXətası")
        # Xətadan sonra bağlantı işləməyə davam edir
        self.assertEqual(self.q().say(), 1)

    def test_sxem(self):
        self.assertIn("tələbə", self.b.cədvəllər())
        s = {x["ad"]: x for x in self.b.sütunlar("tələbə")}
        self.assertTrue(s["id"]["açar"])
        self.assertFalse(s["ad"]["boşOlaBilər"])
        self.assertTrue(s["bal"]["boşOlaBilər"])

    def test_miqrasiya(self):
        with tempfile.TemporaryDirectory() as q:
            Path(q, "001_a.sql").write_text(
                "CREATE TABLE a (x INT);", encoding="utf-8")
            Path(q, "002_pis.sql").write_text(
                "INSERT INTO a VALUES (1); CREATE TABL;", encoding="utf-8")
            with self.assertRaises(AlqorXəta):
                self.b.miqrasiya(q)
            self.assertEqual(int(self.b.bir_dəyər(
                "SELECT COUNT(*) FROM a")), 0)
            Path(q, "002_pis.sql").write_text(
                "INSERT INTO a VALUES (1);\nINSERT INTO a VALUES (2);",
                encoding="utf-8")
            self.assertEqual(self.b.miqrasiya(q), ["002_pis.sql"])
            self.assertEqual(self.b.miqrasiya(q), [])
            self.assertEqual(int(self.b.bir_dəyər(
                "SELECT COUNT(*) FROM a")), 2)

    ORM = """gətir verilənlər

@cədvəl("istifadəçilər")
sinif İstifadəçi miras verilənlər.Model
    @açar
    xassə id: tam
    xassə ad: mətn
    @sütun("e_poçt")
    xassə poçt: mətn?
    xassə aktiv: məntiq = doğru
    @keçici
    xassə müvəqqəti: tam = 7
    @əlaqə(çox: Sifariş)
    xassə sifarişlər: siyahı[Sifariş] = []
son

sinif Sifariş miras verilənlər.Model
    xassə id: tam
    xassə istifadəçiId: tam
    xassə məbləğ: onluq
    @əlaqə(bir: İstifadəçi, açar: "istifadəçiId")
    xassə sahib: İstifadəçi?
son

funksiya əsas()
    dəyişən b = verilənlər.bağlan("ÜNVAN")
    İstifadəçi.istifadəEt(b)
    Sifariş.istifadəEt(b)
    İstifadəçi.cədvəlYarat()
    Sifariş.cədvəlYarat()
    dəyişən a = İstifadəçi.yarat({"ad": "Aysel", "poçt": "a@x.az"})
    dəyişən k = İstifadəçi.yarat({"ad": "Kamran"})
    yaz(k.id - a.id)
    Sifariş.yarat({"istifadəçiId": a.id, "məbləğ": 12.5})
    Sifariş.yarat({"istifadəçiId": a.id, "məbləğ": 30})
    k.ad = "Kamran Əliyev"
    k.aktiv = yanlış
    k.saxla()
    k.saxla()
    dəyişən t = İstifadəçi.tap(k.id)
    yaz(t.ad, t.aktiv, t.poçt)
    yaz(İstifadəçi.harada("ad", "bənzər", "A%").al()[0].poçt)
    yaz(a.yüklə("sifarişlər").uzunluq())
    dəyişən s = Sifariş.harada("məbləğ", ">", 20).ilk()
    yaz(s.yüklə("sahib").ad, s.məbləğ)
    yaz(İstifadəçi.say(), İstifadəçi.sırala("ad", "azalan").al()[0].ad)
    yaz(k.sil(), İstifadəçi.say())
    yaz(İstifadəçi.tap(999))
    yaz(a.lüğət())
son
"""

    def test_orm(self):
        from alqor.icraci import İcraçı
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı
        for c in ("Sifariş", "istifadəçilər"):
            self.b.icra(f"DROP TABLE IF EXISTS {self.b.ad(c, 'cədvəl')}")
        if self.b.d.ad == "sqlite":
            self.skipTest("yaddaşdakı SQLite hər bağlantıda yenidir — "
                          "test_modullar-da sınanır")
        x = XətaToplayıcı()
        m = Mənbə.mətndən(self.ORM.replace("ÜNVAN", self.ÜNVAN), "orm.alq")
        ağac = Parser(Lekser(m, x).leksə(), m, x).ayır()
        self.assertTrue(x.uğurludur(), x.siyahı)
        çıxış = []
        İcraçı(çıxış=çıxış.append).işlət(ağac)
        self.assertEqual(çıxış, [
            "1", "Kamran Əliyev yanlış boş", "a@x.az", "2", "Aysel 30.0",
            "2 Kamran Əliyev", "doğru 1", "boş",
            '{"id": ' + çıxış[-1].split(":")[1].split(",")[0].strip()
            + ', "ad": "Aysel", "poçt": "a@x.az", "aktiv": doğru}'])
        for c in ("Sifariş", "istifadəçilər"):
            self.b.icra(f"DROP TABLE IF EXISTS {self.b.ad(c, 'cədvəl')}")


class SQLite(_Ortaq, unittest.TestCase):
    ÜNVAN = "sqlite::yaddaş:"


class PostgreSQL(_Ortaq, unittest.TestCase):
    ÜNVAN = os.environ.get("ALQOR_SINAQ_PG", "")

    def test_parol_jurnalda_gizlənir(self):
        self.assertNotIn(":gizli@", repr(self.b))
        with self.assertRaises(AlqorXəta) as k:
            V.bağlan(self.ÜNVAN.replace("://", "://yox", 1)
                     if "@" in self.ÜNVAN else "postgres://x:y@127.0.0.1:1/z")
        self.assertEqual(k.exception.tip, "BağlantıXətası")


class MySQL(_Ortaq, unittest.TestCase):
    ÜNVAN = os.environ.get("ALQOR_SINAQ_MYSQL", "")

    def test_no_backslash_escapes_rejimi(self):
        self.b.icra("SET SESSION sql_mode = CONCAT(@@sql_mode, "
                    "',NO_BACKSLASH_ESCAPES')")
        pis = "a\\' OR 1=1 -- "
        self.q().əlavə_et({"ad": pis})
        self.assertEqual(self.b.bir_dəyər(
            "SELECT ad FROM tələbə WHERE ad = ?", pis), pis)
        self.assertEqual(self.q().say(), 1)


class ParametrSınağı(unittest.TestCase):
    def test_literallar_və_şərhlər_toxunulmur(self):
        n = []
        parametrləri_gəz(
            "SELECT '?', \"$1\", $$ ? $$, $t$ $2 $t$ -- ?\n /* $3 */ ? , $4",
            lambda növ, i: n.append((növ, i)) or "")
        self.assertEqual(n, [("?", None), ("$", 4)])

    def test_mysql_qaçışı(self):
        n = []
        parametrləri_gəz(r"SELECT 'a\'?' , ?", lambda a, b: n.append(a) or "",
                         mysql=True)
        self.assertEqual(n, ["?"])


if __name__ == "__main__":
    unittest.main()
