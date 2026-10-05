"""
Əlifba sınaqları — dilin ən kritik hissəsi.

Hər sınaq Python-un standart davranışı ilə müqayisə edir, çünki məhz
orada səhv var.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import elifba as E      # noqa: E402


class HərfÇevrilməsi(unittest.TestCase):
    """az-AZ nöqtəli/nöqtəsiz `i` qaydası."""

    def test_böyüyə_i(self):
        self.assertEqual(E.böyüyə("i"), "İ")
        self.assertEqual("i".upper(), "I")          # Python yanlış

    def test_böyüyə_nöqtəsiz_ı(self):
        self.assertEqual(E.böyüyə("ı"), "I")

    def test_kiçiyə_böyük_I(self):
        self.assertEqual(E.kiçiyə("I"), "ı")
        self.assertEqual("I".lower(), "i")          # Python yanlış

    def test_kiçiyə_nöqtəli_İ(self):
        self.assertEqual(E.kiçiyə("İ"), "i")
        self.assertNotEqual("İ".lower(), "i")       # Python "i̇" verir

    def test_işıq(self):
        self.assertEqual(E.böyüyə("ışıq"), "IŞIQ")

    def test_imran(self):
        self.assertEqual(E.böyüyə("imran"), "İMRAN")
        self.assertEqual("imran".upper(), "IMRAN")  # Python yanlış

    def test_bütün_əlifba_dövrə_vurur(self):
        """kiçiyə(böyüyə(x)) == x — hər hərf üçün."""
        for h in E.KICIK:
            with self.subTest(hərf=h):
                self.assertEqual(E.kiçiyə(E.böyüyə(h)), h)
        for h in E.BOYUK:
            with self.subTest(hərf=h):
                self.assertEqual(E.böyüyə(E.kiçiyə(h)), h)

    def test_mövqe_uyğunluğu(self):
        self.assertEqual(len(E.KICIK), 32)
        self.assertEqual(len(E.BOYUK), 32)
        for i in range(32):
            self.assertEqual(E.böyüyə(E.KICIK[i]), E.BOYUK[i])

    def test_ı_i_mövqeləri(self):
        """13-cü mövqe I/ı, 14-cü mövqe İ/i — bütün problemin mənbəyi."""
        self.assertEqual(E.KICIK[12], "ı")
        self.assertEqual(E.BOYUK[12], "I")
        self.assertEqual(E.KICIK[13], "i")
        self.assertEqual(E.BOYUK[13], "İ")

    def test_əlifbadan_kənar_simvollar_dəyişmir(self):
        self.assertEqual(E.böyüyə("abc-123_xyz"), "ABC-123_XYZ")
        self.assertEqual(E.böyüyə("w"), "W")        # w əlifbada yoxdur

    def test_baş_böyük(self):
        self.assertEqual(E.baş_böyük("ışıq"), "Işıq")
        self.assertEqual(E.baş_böyük("imran"), "İmran")

    def test_hər_söz_böyük(self):
        self.assertEqual(E.hər_söz_böyük("salam dünya"), "Salam Dünya")
        self.assertEqual(E.hər_söz_böyük("ışıqlı imran"), "Işıqlı İmran")


class ƏlifbaSırası(unittest.TestCase):
    def test_ə_hərfi_e_ilə_f_arasındadır(self):
        self.assertEqual(E.sırala(["f", "ə", "e"]), ["e", "ə", "f"])
        self.assertEqual(sorted(["f", "ə", "e"]), ["e", "f", "ə"])  # yanlış

    def test_ı_i_dən_əvvəldir(self):
        self.assertEqual(E.sırala(["i", "ı"]), ["ı", "i"])

    def test_x_h_dan_sonra_ı_dan_əvvəldir(self):
        self.assertEqual(E.sırala(["ı", "x", "h"]), ["h", "x", "ı"])

    def test_q_k_dan_sonradır(self):
        self.assertEqual(E.sırala(["q", "k", "l"]), ["k", "q", "l"])

    def test_tam_əlifba_sırada_qalır(self):
        hərflər = list(E.KICIK)
        self.assertEqual(E.sırala(hərflər), hərflər)

    def test_söz_sırası(self):
        söz = ["zəfər", "əlif", "ağac", "ilk", "ışıq", "ev", "çay"]
        self.assertEqual(E.sırala(söz),
                         ["ağac", "çay", "ev", "əlif", "ışıq", "ilk",
                          "zəfər"])

    def test_böyük_kiçik_fərqi_ikinci_dərəcəlidir(self):
        self.assertEqual(E.sırala(["b", "A", "a", "B"]),
                         ["a", "A", "b", "B"])

    def test_müqayisə(self):
        self.assertEqual(E.müqayisə("e", "ə"), -1)
        self.assertEqual(E.müqayisə("ə", "e"), 1)
        self.assertEqual(E.müqayisə("ə", "ə"), 0)

    def test_rəqəmlər_hərflərdən_əvvəl(self):
        self.assertEqual(E.sırala(["a", "1"]), ["1", "a"])


class HərfSinifləri(unittest.TestCase):
    def test_hərfdir(self):
        for h in "aəışğçöüAƏIİŞĞÇÖÜ":
            self.assertTrue(E.hərfdir(h), h)
        for d in "123 -_$":
            self.assertFalse(E.hərfdir(d), d)
        self.assertFalse(E.hərfdir("w"))       # əlifbada yoxdur

    def test_saitlər(self):
        saitlər = [c for c in E.KICIK if E.saitdir(c)]
        self.assertEqual(saitlər, ["a", "e", "ə", "ı", "i", "o", "ö",
                                   "u", "ü"])
        self.assertEqual(len(saitlər), 9)

    def test_qalın_incə_saitlər(self):
        self.assertEqual([c for c in E.KICIK if E.qalın_saitdir(c)],
                         ["a", "ı", "o", "u"])
        self.assertEqual([c for c in E.KICIK if E.incə_saitdir(c)],
                         ["e", "ə", "i", "ö", "ü"])

    def test_sait_və_samit_ayrılır(self):
        for c in E.KICIK:
            self.assertNotEqual(E.saitdir(c), E.samitdir(c), c)


class Latınlaşdırma(unittest.TestCase):
    def test_açar_sözlər(self):
        hallar = {
            "əgər": "eger", "dəyişən": "deyisen", "üçün": "ucun",
            "içində": "icinde", "nə qədər ki": "ne qeder ki",
            "mücərrəd": "mucerred", "lüğət": "luget", "siyahı": "siyahi",
            "özü": "ozu", "qarışıq": "qarisiq", "həmişə": "hemise",
        }
        for az, ascii_ in hallar.items():
            with self.subTest(söz=az):
                self.assertEqual(E.latınla(az), ascii_)

    def test_İ_böyük_I_olur(self):
        self.assertEqual(E.latınla("İstifadəçi"), "Istifadeci")

    def test_ascii_dəyişmir(self):
        self.assertEqual(E.latınla("funksiya"), "funksiya")


class IdentifikatorQaydaları(unittest.TestCase):
    def test_başlanğıc(self):
        for c in "aəşİ_":
            self.assertTrue(E.ad_başlanğıcı_ola_bilər(c), c)
        for c in "123-$ ":
            self.assertFalse(E.ad_başlanğıcı_ola_bilər(c), c)

    def test_davam(self):
        for c in "aə9_İ":
            self.assertTrue(E.ad_davamı_ola_bilər(c), c)
        for c in "- $.":
            self.assertFalse(E.ad_davamı_ola_bilər(c), c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
