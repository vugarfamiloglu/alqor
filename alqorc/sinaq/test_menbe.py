"""Mənbə hazırlanması, homoqliflər və xəta hesabatı sınaqları."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import homoqlif as H                      # noqa: E402
from alqor.menbe import Mənbə, hazırla               # noqa: E402
from alqor.xeta import Səviyyə, XətaToplayıcı        # noqa: E402


class Hazırlama(unittest.TestCase):
    def test_bom_atılır(self):
        m, _ = hazırla("﻿yaz(1)")
        self.assertEqual(m, "yaz(1)")

    def test_crlf_lf_olur(self):
        m, _ = hazırla("a\r\nb\rc")
        self.assertEqual(m, "a\nb\nc")

    def test_nfc_parçalanmış_hərfləri_birləşdirir(self):
        # s + COMBINING CEDILLA → ş
        m, _ = hazırla("ş")
        self.assertEqual(m, "ş")
        # g + COMBINING BREVE → ğ
        m, _ = hazırla("ğ")
        self.assertEqual(m, "ğ")
        # o + COMBINING DIAERESIS → ö
        m, _ = hazırla("ö")
        self.assertEqual(m, "ö")

    def test_ə_nfc_ilə_düzəlmir(self):
        """`ə` (U+0259) parçalanmır — `ä`→`ə` homoqlif modulunun işidir."""
        import unicodedata
        self.assertEqual(unicodedata.decomposition("ə"), "")

    def test_homoqlif_direktivi_düzəlişi_söndürür(self):
        mətn = "// alqor: homoqlif-yoxlama söndür\ndäyişən = 1"
        m, tapıntılar = hazırla(mətn)
        self.assertEqual(tapıntılar, [])
        self.assertIn("däyişən", m)


class Homoqliflər(unittest.TestCase):
    def test_ä_ə_olur(self):
        m, t = H.düzəlt("däyişən")
        self.assertEqual(m, "dəyişən")
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].tapılan, "ä")
        self.assertEqual(t[0].əvəz, "ə")
        self.assertEqual(t[0].kod, "U+00E4")

    def test_kiril_hərfləri(self):
        m, t = H.düzəlt("еv")            # kiril е
        self.assertEqual(m, "ev")
        self.assertEqual(len(t), 1)

    def test_yunan_hərfləri(self):
        m, _ = H.düzəlt("ο")             # yunan ο
        self.assertEqual(m, "o")

    def test_görünməz_simvol_silinir(self):
        m, t = H.düzəlt("ad​soyad")
        self.assertEqual(m, "adsoyad")
        self.assertEqual(t[0].əvəz, "")
        self.assertIn("ZERO WIDTH SPACE", t[0].ad)

    def test_nbsp_boşluq_olur(self):
        m, _ = H.düzəlt("a b")
        self.assertEqual(m, "a b")

    def test_tam_genişlikli_hərflər(self):
        m, _ = H.düzəlt("ａｂｃ")   # ａｂｃ
        self.assertEqual(m, "abc")

    def test_tam_genişlikli_rəqəmlər(self):
        m, _ = H.düzəlt("０１２")   # ０１２
        self.assertEqual(m, "012")

    def test_tire_homoqlif_DEYİL(self):
        """`—` qanuni durğu işarəsidir — şərhlərdə normaldır."""
        for c in ("–", "—", "−", "×", "÷"):
            with self.subTest(simvol=c):
                m, t = H.düzəlt(f"// Nümunə {c} izah")
                self.assertEqual(t, [], f"{c!r} səhvən düzəldilir")

    def test_dırnaq_homoqlif_DEYİL(self):
        """Ağıllı dırnaqlar mətn məzmununda qanunidir."""
        for c in ("‘", "’", "“", "”", "«"):
            with self.subTest(simvol=c):
                _, t = H.düzəlt(f'yaz("{c}")')
                self.assertEqual(t, [])

    def test_azərbaycan_hərfləri_toxunulmur(self):
        mətn = "dəyişən yaş = işıq + Şəhər - Ğəribə"
        m, t = H.düzəlt(mətn)
        self.assertEqual(m, mətn)
        self.assertEqual(t, [])

    def test_ascii_toxunulmur(self):
        mətn = "funksiya topla(a, b) { return a + b; }"
        m, t = H.düzəlt(mətn)
        self.assertEqual(m, mətn)
        self.assertEqual(t, [])

    def test_mövqe_düzgündür(self):
        m, t = H.düzəlt("abäcd")
        self.assertEqual(t[0].mövqe, 2)
        self.assertEqual(m[2], "ə")

    def test_əvəzləmə_uzunluğu_1_e_1(self):
        """Mövqelərin qorunması üçün bütün əvəzləmələr tək simvol olmalı."""
        for tapılan, əvəz in H.EVEZLEMELER.items():
            with self.subTest(simvol=tapılan):
                self.assertEqual(len(tapılan), 1)
                self.assertEqual(len(əvəz), 1)


class MövqeXəritəsi(unittest.TestCase):
    def setUp(self):
        self.m = Mənbə("sınaq.alqor", "birinci\nikinci\nüçüncü")

    def test_sətir_sayı(self):
        self.assertEqual(self.m.sətir_sayı, 3)

    def test_sətir_sütun(self):
        self.assertEqual(self.m.sətir_sütun(0), (1, 1))
        self.assertEqual(self.m.sətir_sütun(6), (1, 7))
        self.assertEqual(self.m.sətir_sütun(8), (2, 1))
        self.assertEqual(self.m.sətir_sütun(15), (3, 1))

    def test_sətir_mətni(self):
        self.assertEqual(self.m.sətir_mətni(1), "birinci")
        self.assertEqual(self.m.sətir_mətni(2), "ikinci")
        self.assertEqual(self.m.sətir_mətni(3), "üçüncü")
        self.assertEqual(self.m.sətir_mətni(99), "")

    def test_mövqe_dövrə_vurur(self):
        for mövqe in range(len(self.m.mətn)):
            s, st = self.m.sətir_sütun(mövqe)
            self.assertEqual(self.m.mövqe(s, st), mövqe)

    def test_azərbaycan_hərfləri_sütunu_pozmur(self):
        m = Mənbə("a.alqor", "dəyişən ışıq = 5")
        self.assertEqual(m.sətir_sütun(m.mətn.index("ışıq")), (1, 9))


class XətaHesabatı(unittest.TestCase):
    def setUp(self):
        self.m = Mənbə("əsas.alqor", 'yaz("Yaş: " + yaş)\nson')
        self.x = XətaToplayıcı()

    def test_xəta_formatı(self):
        self.x.xəta("ALQ-T008", "Operator `+` bu tiplərə tətbiq edilmir",
                    self.m.yer(5, 7), "`mətn` və `tam` toplanmır",
                    'interpolyasiya istifadə edin: "Yaş: {yaş}"')
        h = self.x.hesabat(rəngli=False)
        self.assertIn("✖ ALQ-T008", h)
        self.assertIn("əsas.alqor:1:6", h)
        self.assertIn("^^^^^^^", h)
        self.assertIn("= kömək:", h)
        self.assertIn("= sənəd: alqor.az/xeta/ALQ-T008", h)

    def test_xəbərdarlıq_işarəsi(self):
        self.x.xəbərdarlıq("ALQ-L020", "ASCII açar söz", self.m.yer(0, 3))
        self.assertIn("⚠", self.x.hesabat(rəngli=False))

    def test_uğurludur(self):
        self.assertTrue(self.x.uğurludur())
        self.x.xəbərdarlıq("ALQ-L020", "x", None)
        self.assertTrue(self.x.uğurludur())       # xəbərdarlıq xəta deyil
        self.x.xəta("ALQ-L002", "x", None)
        self.assertFalse(self.x.uğurludur())

    def test_xəbərdarlıq_xətaya_çevrilir(self):
        x = XətaToplayıcı(xəbərdarlıq_xətadır=True)
        x.xəbərdarlıq("ALQ-L020", "x", None)
        self.assertFalse(x.uğurludur())

    def test_söndürmə(self):
        self.x.söndür("ALQ-L020")
        self.x.xəbərdarlıq("ALQ-L020", "x", None)
        self.assertEqual(self.x.siyahı, [])

    def test_xülasə(self):
        self.assertIn("✓", self.x.xülasə(rəngli=False))
        self.x.xəta("ALQ-L002", "x", None)
        self.x.xəbərdarlıq("ALQ-L020", "y", None)
        s = self.x.xülasə(rəngli=False)
        self.assertIn("1 xəta", s)
        self.assertIn("1 xəbərdarlıq", s)

    def test_sıralama_xətalar_əvvəl(self):
        self.x.xəbərdarlıq("ALQ-L020", "x", self.m.yer(0, 1))
        self.x.xəta("ALQ-L002", "y", self.m.yer(10, 1))
        sıralı = self.x._sıralı()
        self.assertEqual(sıralı[0].səviyyə, Səviyyə.XETA)

    def test_tabulyasiya_xətti_düzgün_yerləşdirir(self):
        """Tab 4 boşluğa açılır — xətt `yaz` sözünün altında olmalıdır."""
        m = Mənbə("t.alqor", "\tyaz(x)")
        x = XətaToplayıcı()
        x.xəta("ALQ-L002", "test", m.yer(1, 3))      # `yaz`
        sətirlər = x.hesabat(rəngli=False).split("\n")

        kod_sətri = [s for s in sətirlər if "yaz(x)" in s][0]
        xətt_sətri = [s for s in sətirlər if "^" in s][0]

        # Hər iki sətirdə `│`-dan sonraki sürüşmə eyni olmalıdır
        kod_sürüşmə = kod_sətri.index("yaz") - kod_sətri.index("│")
        xətt_sürüşmə = xətt_sətri.index("^") - xətt_sətri.index("│")
        self.assertEqual(xətt_sürüşmə, kod_sürüşmə)
        self.assertEqual(xətt_sətri.count("^"), 3)
        self.assertNotIn("\t", kod_sətri)


class FaylOxuma(unittest.TestCase):
    def test_tapılmayan_fayl(self):
        x = XətaToplayıcı()
        m = Mənbə.fayldan("yoxdur-belə-fayl.alqor", x)
        self.assertIsNone(m)
        self.assertEqual(x.xətalar[0].kod, "ALQ-R009")

    def test_ə_hərfi_köhnə_kodlaşmalarda_yoxdur(self):
        """
        Azərbaycan dilinin UTF-8-dən başqa seçimi yoxdur: `ə` (U+0259)
        heç bir geniş yayılmış 8-bitlik kod səhifəsində mövcud deyil.
        Bu, dilin `Yalnız UTF-8` qaydasının səbəbidir (Spes. § 1.1).
        """
        for kodlaşma in ("windows-1254", "iso-8859-9", "windows-1252",
                         "windows-1251", "cp437"):
            with self.subTest(kodlaşma=kodlaşma):
                with self.assertRaises(UnicodeEncodeError):
                    "ə".encode(kodlaşma)

    def test_utf8_olmayan_fayl(self):
        import tempfile
        # windows-1254 (türk) `ğ ş ı` saxlayır, `ə` saxlamır —
        # alınan baytlar etibarlı UTF-8 deyil.
        with tempfile.NamedTemporaryFile(suffix=".alqor", delete=False) as f:
            f.write("değişen yaş = 5".encode("windows-1254"))
            yol = f.name
        try:
            x = XətaToplayıcı()
            m = Mənbə.fayldan(yol, x)
            self.assertIsNone(m)
            self.assertEqual(x.xətalar[0].kod, "ALQ-L001")
            self.assertIn("iconv", x.hesabat(rəngli=False))
        finally:
            Path(yol).unlink()

    def test_nümunələr_oxunur(self):
        kök = Path(__file__).parent.parent.parent / "numuneler"
        if not kök.exists():
            self.skipTest("nümunələr qovluğu yoxdur")
        fayllar = sorted(kök.glob("*.alqor"))
        self.assertGreater(len(fayllar), 0)
        for f in fayllar:
            with self.subTest(fayl=f.name):
                x = XətaToplayıcı()
                m = Mənbə.fayldan(f, x)
                self.assertIsNotNone(m)
                self.assertTrue(x.uğurludur(), x.hesabat(rəngli=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
