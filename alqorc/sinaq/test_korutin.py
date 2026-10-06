"""Tənbəl generatorlar və asinxron icra sınaqları."""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from alqor.korutin import Gələcək, Korutin, LəğvNişanı   # noqa: E402
from test_icraci import xəta_tipi, çıxış                 # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  Korutin mexanizmi (Python səviyyəsində)
# ═══════════════════════════════════════════════════════════════════════

class KorutinMexanizmi(unittest.TestCase):
    def test_sadə(self):
        def gövdə(ver):
            ver(1)
            ver(2)
            ver(3)
        k = Korutin(gövdə)
        self.assertEqual(list(k), [1, 2, 3])

    def test_tənbəldir(self):
        """Dəyərlər yalnız istənəndə hesablanmalıdır."""
        hesablandı: list[int] = []

        def gövdə(ver):
            for i in range(100):
                hesablandı.append(i)
                ver(i)

        k = Korutin(gövdə)
        self.assertEqual(k.növbəti(), 0)
        self.assertEqual(k.növbəti(), 1)
        self.assertLessEqual(len(hesablandı), 3)

    def test_sonsuz(self):
        def gövdə(ver):
            i = 0
            while True:
                ver(i)
                i += 1
        k = Korutin(gövdə)
        self.assertEqual([k.növbəti() for _ in range(5)],
                         [0, 1, 2, 3, 4])
        k.bağla()

    def test_bitmə(self):
        k = Korutin(lambda ver: ver(1))
        self.assertEqual(k.növbəti(), 1)
        with self.assertRaises(StopIteration):
            k.növbəti()
        self.assertTrue(k.bitdimi)

    def test_xəta_ötürülür(self):
        def gövdə(ver):
            ver(1)
            raise ValueError("pis")
        k = Korutin(gövdə)
        self.assertEqual(k.növbəti(), 1)
        with self.assertRaises(ValueError):
            k.növbəti()

    def test_bağlama(self):
        def gövdə(ver):
            while True:
                ver(1)
        k = Korutin(gövdə)
        k.növbəti()
        k.bağla()
        time.sleep(0.05)


class GələcəkMexanizmi(unittest.TestCase):
    def test_tənbəldir(self):
        işlədi = []
        g = Gələcək(lambda: (işlədi.append(1), 42)[1])
        self.assertEqual(işlədi, [])
        self.assertEqual(g.al(), 42)
        self.assertEqual(işlədi, [1])

    def test_bir_dəfə_işləyir(self):
        sayğac = []
        g = Gələcək(lambda: (sayğac.append(1), len(sayğac))[1])
        self.assertEqual(g.al(), 1)
        self.assertEqual(g.al(), 1)

    def test_xəta(self):
        def pis():
            raise ValueError("pis")
        g = Gələcək(pis)
        with self.assertRaises(ValueError):
            g.al()
        self.assertFalse(g.uğurludurmu)

    def test_paralel_başlatma(self):
        def yavaş():
            time.sleep(0.1)
            return "bitdi"
        başlanğıc = time.perf_counter()
        gələcəklər = [Gələcək(yavaş).başlat() for _ in range(4)]
        nəticələr = [g.al() for g in gələcəklər]
        müddət = time.perf_counter() - başlanğıc
        self.assertEqual(nəticələr, ["bitdi"] * 4)
        self.assertLess(müddət, 0.35, "paralel icra olmadı")


class LəğvNişanıSınağı(unittest.TestCase):
    def test_ləğv(self):
        n = LəğvNişanı()
        self.assertFalse(n.ləğvolunub)
        n.ləğvEt()
        self.assertTrue(n.ləğvolunub)

    def test_vaxtla(self):
        n = LəğvNişanı(0.05)
        self.assertFalse(n.ləğvolunub)
        time.sleep(0.15)
        self.assertTrue(n.ləğvolunub)


# ═══════════════════════════════════════════════════════════════════════
#  Dil səviyyəsində generatorlar
# ═══════════════════════════════════════════════════════════════════════

SAYLAR = ("generator funksiya saylar(n: tam) -> tam\n"
          "    hər i üçün 1..n içində\n"
          "        ver i\n"
          "    son\n"
          "son\n")

FIB = ("generator funksiya fib() -> tam\n"
       "    dəyişən a = 0, b = 1\n"
       "    həmişə\n"
       "        ver a\n"
       "        a, b = b, a + b\n"
       "    son\n"
       "son\n")


class GeneratorSınağı(unittest.TestCase):
    def test_sadə_dövr(self):
        self.assertEqual(
            çıxış(SAYLAR + "hər x üçün saylar(3) içində\n yaz(x)\nson"),
            ["1", "2", "3"])

    def test_siyahıya_çevirmə(self):
        self.assertEqual(çıxış(SAYLAR + "yaz(saylar(4).siyahıyaÇevir())"),
                         ["[1, 2, 3, 4]"])

    def test_növbəti_və_bitdi(self):
        kod = (SAYLAR + "dəyişən g = saylar(2)\n"
               "yaz(g.növbəti())\nyaz(g.növbəti())\nyaz(g.bitdi())")
        self.assertEqual(çıxış(kod), ["1", "2", "yanlış"])

    def test_bitdikdən_sonra_xəta(self):
        kod = (SAYLAR + "dəyişən g = saylar(1)\n"
               "yaz(g.növbəti())\nyaz(g.növbəti())")
        self.assertEqual(xəta_tipi(kod), "KolleksiyaXətası")

    def test_sonsuz_generator(self):
        """Ən vacib sınaq — əvvəl bu mümkün deyildi."""
        kod = (FIB + "dəyişən say = 0\n"
               "hər f üçün fib() içində\n"
               "    əgər say >= 8 onda dayan son\n"
               "    yaz(f)\n"
               "    say += 1\n"
               "son")
        self.assertEqual(çıxış(kod),
                         ["0", "1", "1", "2", "3", "5", "8", "13"])

    def test_sonsuz_ilk(self):
        self.assertEqual(çıxış(FIB + "yaz(fib().ilk(6))"),
                         ["[0, 1, 1, 2, 3, 5]"])

    def test_tənbəldir(self):
        """Generator gövdəsi yalnız lazım olduqda işləməlidir."""
        kod = ("generator funksiya g() -> tam\n"
               '    yaz("birinci")\n'
               "    ver 1\n"
               '    yaz("ikinci")\n'
               "    ver 2\n"
               "son\n"
               "dəyişən it = g()\n"
               'yaz("başlamadı")\n'
               "yaz(it.növbəti())")
        self.assertEqual(çıxış(kod), ["başlamadı", "birinci", "1"])

    def test_çevir_tənbəldir(self):
        self.assertEqual(
            çıxış(FIB + "yaz(fib().çevir((x) => x * 2).ilk(5))"),
            ["[0, 2, 2, 4, 6]"])

    def test_filtr(self):
        self.assertEqual(
            çıxış(FIB + "yaz(fib().filtr((x) => x % 2 == 0).ilk(4))"),
            ["[0, 2, 8, 34]"])

    def test_atla(self):
        self.assertEqual(çıxış(SAYLAR + "yaz(saylar(5).atla(2).ilk(2))"),
                         ["[3, 4]"])

    def test_tap(self):
        self.assertEqual(çıxış(FIB + "yaz(fib().tap((x) => x > 50))"),
                         ["55"])

    def test_cəm(self):
        self.assertEqual(çıxış(SAYLAR + "yaz(saylar(4).cəm())"), ["10"])

    def test_generator_qurması(self):
        self.assertEqual(
            çıxış("dəyişən g = (x * x üçün x içində 1..4)\n"
                  "yaz(g.siyahıyaÇevir())"), ["[1, 4, 9, 16]"])

    def test_tip_adı(self):
        self.assertEqual(çıxış(SAYLAR + "yaz(tip(saylar(1)))"),
                         ["generator"])


# ═══════════════════════════════════════════════════════════════════════
#  Dil səviyyəsində asinxron
# ═══════════════════════════════════════════════════════════════════════

ASINXRON = ("gətir vaxt\n"
            "asinxron funksiya gec(ms: tam, ad: mətn) -> mətn\n"
            "    vaxt.gözlə(ms)\n"
            '    qaytar ad\n'
            "son\n")


class AsinxronSınağı(unittest.TestCase):
    def test_gözlə(self):
        self.assertEqual(çıxış(ASINXRON + 'yaz(gözlə gec(1, "a"))'),
                         ["a"])

    def test_gələcək_tipi(self):
        self.assertEqual(çıxış(ASINXRON + 'yaz(tip(gec(1, "a")))'),
                         ["gələcək"])

    def test_tənbəldir(self):
        """`asinxron` funksiya çağırılanda gövdə dərhal işləməməlidir."""
        kod = ("asinxron funksiya f()\n"
               '    yaz("işlədi")\n'
               "son\n"
               "dəyişən g = f()\n"
               'yaz("hələ yox")\n'
               "gözlə g")
        self.assertEqual(çıxış(kod), ["hələ yox", "işlədi"])

    def test_paralel_çağırış(self):
        kod = (ASINXRON +
               'dəyişən (a, b) = gözlə paralel(gec(1, "x"), gec(1, "y"))\n'
               'yaz("{a}{b}")')
        self.assertEqual(çıxış(kod), ["xy"])

    def test_paralel_hamısı(self):
        kod = (ASINXRON +
               'yaz(gözlə paralel.hamısı([gec(1, "a"), gec(1, "b")]))')
        self.assertEqual(çıxış(kod), ['["a", "b"]'])

    def test_paralel_həqiqətən_paraleldir(self):
        kod = (ASINXRON + "gətir riyaziyyat\n"
               "dəyişən b = vaxt.ölç()\n"
               'dəyişən _n = gözlə paralel.hamısı('
               '[gec(120, "a"), gec(120, "b"), gec(120, "c")])\n'
               "dəyişən müddət = (vaxt.ölç() - b) * 1000\n"
               "yaz(müddət < 300)")
        self.assertEqual(çıxış(kod), ["doğru"])

    def test_paralel_ilk_bitən(self):
        kod = (ASINXRON +
               'yaz(gözlə paralel.ilkBitən([gec(200, "yavaş"), '
               'gec(5, "tez")]))')
        self.assertEqual(çıxış(kod), ["tez"])

    def test_paralel_hamısı_nəticə(self):
        kod = ("asinxron funksiya yaxşı() -> tam\n    qaytar 1\nson\n"
               "asinxron funksiya pis() -> tam\n"
               '    at Xəta("sındı")\nson\n'
               "dəyişən n = gözlə paralel.hamısıNəticə([yaxşı(), pis()])\n"
               # Kortej dağıtmaq üçün mötərizə lazımdır — vergüllü forma
               # (`hər a, b üçün`) indeks + element verir (Spes. § 4.5)
               "hər (uğur, dəyər) üçün n içində\n"
               '    yaz("{uğur}: {dəyər}")\n'
               "son")
        sətirlər = çıxış(kod)
        self.assertEqual(sətirlər[0], "doğru: 1")
        self.assertIn("yanlış", sətirlər[1])

    def test_paralel_çevir(self):
        kod = ("asinxron funksiya ikiqat(x: tam) -> tam\n"
               "    qaytar x * 2\nson\n"
               "yaz(gözlə paralel.çevir([1, 2, 3], ikiqat))")
        self.assertEqual(çıxış(kod), ["[2, 4, 6]"])

    def test_paralel_məhdud(self):
        kod = (ASINXRON +
               "yaz(uzunluq(gözlə paralel.məhdud(2, "
               '[gec(1, "a"), gec(1, "b"), gec(1, "c")])))')
        self.assertEqual(çıxış(kod), ["3"])

    def test_vaxt_limitlə(self):
        kod = (ASINXRON +
               "cəhd et\n"
               '    yaz(gözlə vaxt.limitlə(30, gec(300, "yavaş")))\n'
               "tut (x: VaxtBitdiXətası)\n"
               '    yaz("vaxt bitdi")\n'
               "son")
        self.assertEqual(çıxış(kod), ["vaxt bitdi"])

    def test_asinxron_xətası_tutulur(self):
        kod = ("asinxron funksiya pis()\n"
               '    at ArqumentXətası("pis")\n'
               "son\n"
               "cəhd et\n"
               "    gözlə pis()\n"
               "tut (x: ArqumentXətası)\n"
               '    yaz("tutuldu")\n'
               "son")
        self.assertEqual(çıxış(kod), ["tutuldu"])

    def test_gözlə_adi_dəyərdə(self):
        self.assertEqual(çıxış("yaz(gözlə 5)"), ["5"])

    def test_ləğv_nişanı(self):
        kod = ("dəyişən n = yeni LəğvNişanı()\n"
               "yaz(n.ləğvolunub())\n"
               "n.ləğvEt()\n"
               "yaz(n.ləğvolunub())")
        self.assertEqual(çıxış(kod), ["yanlış", "doğru"])

    def test_sap_başlat(self):
        kod = ("funksiya ağır() -> tam\n    qaytar 42\nson\n"
               "yaz(gözlə sap.başlat(ağır))")
        self.assertEqual(çıxış("gətir sap\n" + kod), ["42"])


class BaşlanğıcKontekstliSınağı(unittest.TestCase):
    """`başlanğıc` və `bitiş` adi dəyişən adı ola bilər."""

    def test_dəyişən_adı_kimi(self):
        self.assertEqual(
            çıxış("dəyişən başlanğıc = 5\ndəyişən bitiş = 10\n"
                  "yaz(bitiş - başlanğıc)"), ["5"])

    def test_blok_kimi(self):
        kod = ("başlanğıc\n"
               '    yaz("modul açıldı")\n'
               "son\n"
               'yaz("əsas kod")')
        self.assertEqual(çıxış(kod), ["modul açıldı", "əsas kod"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
