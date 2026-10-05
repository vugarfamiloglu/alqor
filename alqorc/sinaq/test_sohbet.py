"""İnteraktiv rejim (REPL) sınaqları."""

import builtins
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.sohbet import META_ƏMRLƏR, Söhbət, yarımçıqdır   # noqa: E402


def seans(sətirlər: list[str]) -> tuple[str, str]:
    """
    Verilən sətirləri REPL-ə ötürür, (stdout, stderr) qaytarır.

    Sonda `:çıx` avtomatik əlavə olunur.
    """
    növbə = list(sətirlər) + [":çıx"]
    köhnə_input = builtins.input

    def saxta_input(soruş=""):
        if not növbə:
            raise EOFError
        return növbə.pop(0)

    çıxış, xəta = io.StringIO(), io.StringIO()
    builtins.input = saxta_input
    try:
        with redirect_stdout(çıxış), redirect_stderr(xəta):
            Söhbət(rəngli=False).işlət()
    finally:
        builtins.input = köhnə_input
    return çıxış.getvalue(), xəta.getvalue()


class YarımçıqAşkarlanması(unittest.TestCase):
    def test_tam_girişlər(self):
        for kod in ("2 + 2", 'yaz("a")', "dəyişən a = 5",
                    "əgər doğru onda\n yaz(1)\nson",
                    "funksiya f() qaytar 1 son",
                    "[1, 2, 3]", ""):
            with self.subTest(kod=kod):
                self.assertFalse(yarımçıqdır(kod), kod)

    def test_açıq_bloklar(self):
        for kod in ("əgər doğru onda", "funksiya f()",
                    "sinif A", "hər x üçün 1..5 içində",
                    "nə qədər ki doğru", "cəhd et",
                    "əgər doğru onda\n yaz(1)",
                    "seç x", "həmişə"):
            with self.subTest(kod=kod):
                self.assertTrue(yarımçıqdır(kod), kod)

    def test_bağlanmamış_mötərizə(self):
        for kod in ("topla(1,", "[1, 2", "{\"a\": 1"):
            with self.subTest(kod=kod):
                self.assertTrue(yarımçıqdır(kod), kod)

    def test_bağlanmamış_mətn(self):
        self.assertTrue(yarımçıqdır('yaz("salam'))

    def test_bağlanmamış_şərh(self):
        self.assertTrue(yarımçıqdır("/* şərh"))

    def test_iç_içə_bloklar(self):
        kod = "funksiya f()\n əgər doğru onda\n  yaz(1)\n son"
        self.assertTrue(yarımçıqdır(kod))
        self.assertFalse(yarımçıqdır(kod + "\nson"))


class İfadəÇapı(unittest.TestCase):
    def test_ədəd(self):
        out, _ = seans(["2 + 2"])
        self.assertIn("4", out)
        self.assertIn("// tam", out)

    def test_mətn_dırnaqda(self):
        out, _ = seans(['"salam"'])
        self.assertIn('"salam"', out)
        self.assertIn("// mətn", out)

    def test_boş_dəyər_çap_olunmur(self):
        out, _ = seans(['yaz("x")'])
        self.assertIn("x", out)
        self.assertNotIn("// heç", out)

    def test_elan_çap_olunmur(self):
        out, _ = seans(["dəyişən a = 5"])
        self.assertNotIn("// tam", out)

    def test_siyahı(self):
        out, _ = seans(["[1, 2, 3]"])
        self.assertIn("[1, 2, 3]", out)

    def test_az_hərf_çevrilməsi(self):
        out, _ = seans(['"ışıq".böyüyə()'])
        self.assertIn("IŞIQ", out)


class VəziyyətSaxlanması(unittest.TestCase):
    def test_dəyişən_saxlanılır(self):
        out, _ = seans(["dəyişən a = 5", "a * 3"])
        self.assertIn("15", out)

    def test_funksiya_saxlanılır(self):
        out, _ = seans(["funksiya ikiqat(x: tam) -> tam",
                        "    qaytar x * 2",
                        "son",
                        "ikiqat(21)"])
        self.assertIn("42", out)

    def test_sinif_saxlanılır(self):
        out, _ = seans(["sinif A", "    qurucu(açıq xassə x: tam)", "son",
                        "yeni A(7).x"])
        self.assertIn("7", out)

    def test_nəticə_dəyişəni(self):
        out, _ = seans(["10 + 5", "nəticə * 2"])
        self.assertIn("30", out)

    def test_təmizlə(self):
        out, _ = seans(["dəyişən a = 5", ":təmizlə", "a"])
        self.assertIn("təmizləndi", out)
        self.assertIn("ALQ-T022", out + _xəta_mətni(["dəyişən a = 5",
                                                     ":təmizlə", "a"]))


def _xəta_mətni(sətirlər):
    return seans(sətirlər)[1]


class ÇoxsətirliGiriş(unittest.TestCase):
    def test_blok(self):
        out, _ = seans(["əgər 5 > 3 onda",
                        '    yaz("böyük")',
                        "son"])
        self.assertIn("böyük", out)

    def test_dövr(self):
        out, _ = seans(["hər i üçün 1..3 içində",
                        "    yaz(i)",
                        "son"])
        for n in ("1", "2", "3"):
            self.assertIn(n, out)

    def test_iki_boş_sətir_ləğv_edir(self):
        out, _ = seans(["əgər doğru onda", "", "", "2 + 2"])
        self.assertIn("ləğv edildi", out)
        self.assertIn("4", out)

    def test_çoxsətirli_arqument(self):
        out, _ = seans(["yaz(",
                        '    "a",',
                        '    "b"',
                        ")"])
        self.assertIn("a b", out)


class XətadanBərpa(unittest.TestCase):
    def test_sintaksis_xətası_seansı_dayandırmır(self):
        out, xəta = seans(["dəyişən a = $", "2 + 2"])
        self.assertIn("ALQ-L002", xəta)
        self.assertIn("4", out)

    def test_icra_xətası_seansı_dayandırmır(self):
        out, xəta = seans(["1 ~/ 0", "2 + 2"])
        self.assertIn("BölməXətası", xəta)
        self.assertIn("4", out)

    def test_təyin_edilməmiş_ad(self):
        _, xəta = seans(["yoxdurbelə"])
        self.assertIn("ALQ-T022", xəta)

    def test_sıfıra_bölmə_düzgün_kod(self):
        """`1 ~/ 0` BölməXətası verməlidir, leksik xəta yox."""
        _, xəta = seans(["1 ~/ 0"])
        self.assertIn("ALQ-R001", xəta)
        self.assertNotIn("ALQ-L006", xəta)

    def test_sətir_sonunda_sıfır(self):
        """`0` sətrin sonunda onaltılıq prefiks sayılmamalıdır."""
        out, xəta = seans(["0"])
        self.assertNotIn("ALQ-L006", xəta)
        self.assertIn("0", out)


class MetaƏmrlər(unittest.TestCase):
    def test_kömək(self):
        out, _ = seans([":kömək"])
        self.assertIn("Meta-əmrlər", out)
        self.assertIn(":tip", out)

    def test_kömək_ləqəbləri(self):
        for ad in (":k", ":?"):
            with self.subTest(ad=ad):
                self.assertIn("Meta-əmrlər", seans([ad])[0])

    def test_tip(self):
        out, _ = seans([":tip 42"])
        self.assertIn("tam", out)
        out, _ = seans([':tip "a"'])
        self.assertIn("mətn", out)

    def test_siyahı(self):
        out, _ = seans(["dəyişən a = 5",
                        "funksiya f() qaytar 1 son",
                        ":siyahı"])
        self.assertIn("a", out)
        self.assertIn("f", out)
        self.assertIn("funksiya", out)

    def test_siyahı_boş(self):
        out, _ = seans([":siyahı"])
        self.assertIn("təyin edilməyib", out)

    def test_vaxt(self):
        out, _ = seans([":vaxt 1 + 1"])
        self.assertIn("ms", out)
        self.assertIn("2", out)

    def test_tokenlər(self):
        out, _ = seans([":tokenlər dəyişən a = 5"])
        self.assertIn("ACAR", out)
        self.assertIn("dəyişən", out)

    def test_aac(self):
        out, _ = seans([":aac 1 + 2"])
        self.assertIn("İkili", out)

    def test_hərflər(self):
        out, _ = seans([":hərflər"])
        self.assertIn("ə ı ğ ş ç ö ü", out)
        self.assertIn("eger", out)

    def test_əlifba(self):
        out, _ = seans([":əlifba"])
        self.assertIn("32 hərf", out)

    def test_tarixçə(self):
        out, _ = seans(["2 + 2", "3 + 3", ":tarixçə"])
        self.assertIn("2 + 2", out)
        self.assertIn("3 + 3", out)

    def test_naməlum_əmr(self):
        out, _ = seans([":yoxdurbelə"])
        self.assertIn("naməlum əmr", out)

    def test_ascii_söndürmə(self):
        out, _ = seans([":ascii qapat", "eger doğru onda", " yaz(1)", "son"])
        self.assertNotIn("ALQ-L020", out)
        self.assertIn("qapalı", out)

    def test_ascii_xəbərdarlığı_standart_açıqdır(self):
        out, _ = seans(["eger doğru onda", " yaz(1)", "son"])
        self.assertIn("ALQ-L020", out)

    def test_bütün_əmrlər_çağırıla_bilir(self):
        """Hər meta-əmr arqumentsiz çağırılanda çökməməlidir."""
        for ad in META_ƏMRLƏR:
            if ad in ("çıx", "cix", "q"):
                continue
            with self.subTest(əmr=ad):
                seans([f":{ad}"])      # istisna atmasa kifayətdir


class FaylƏməliyyatları(unittest.TestCase):
    def test_yüklə_və_saxla(self):
        import tempfile
        qovluq = Path(tempfile.mkdtemp())
        mənbə = qovluq / "modul.alqor"
        mənbə.write_text(
            "funksiya salam() -> mətn\n    qaytar \"salam\"\nson\n",
            encoding="utf-8")
        try:
            out, _ = seans([f":yüklə {mənbə}", "salam()"])
            self.assertIn("salam", out)

            hədəf = qovluq / "seans.alqor"
            out, _ = seans(["dəyişən a = 1", f":saxla {hədəf}"])
            self.assertIn("saxlanıldı", out)
            self.assertTrue(hədəf.exists())
            self.assertIn("dəyişən a = 1",
                          hədəf.read_text(encoding="utf-8"))
        finally:
            import shutil
            shutil.rmtree(qovluq, ignore_errors=True)

    def test_yüklə_tapılmayan_fayl(self):
        out, _ = seans([":yüklə yoxdur-belə-fayl.alqor"])
        self.assertIn("tapılmadı", out)


class ÜzvTəklifi(unittest.TestCase):
    def test_ascii_üzv_adı_təklif_olunur(self):
        _, xəta = seans(["[1, 2].cem()"])
        self.assertIn("cəm", xəta)
        self.assertIn("AÇAR SÖZLƏRƏ", xəta)

    def test_yaxın_ad_təklif_olunur(self):
        _, xəta = seans(['"abc".uzu()'])
        self.assertIn("bəlkə", xəta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
