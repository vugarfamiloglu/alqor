"""`alqorfmt` — kod formatlayıcısı."""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import alqorfmt as F                              # noqa: E402

KÖK = Path(__file__).parent.parent.parent


def fmt(mətn: str, **k) -> str:
    return F.formatla(mətn, **k).mətn


class GirintiSınağı(unittest.TestCase):
    def test_blok_strukturu(self):
        self.assertEqual(fmt(
            "funksiya f(a)\nəgər a onda\nyaz(1)\nyoxsa əgər a > 2 onda\n"
            "yaz(2)\nyoxsa\nyaz(3)\nson\nson\n"),
            "funksiya f(a)\n    əgər a onda\n        yaz(1)\n"
            "    yoxsa əgər a > 2 onda\n        yaz(2)\n    yoxsa\n"
            "        yaz(3)\n    son\nson\n")

    def test_seç_və_hal(self):
        self.assertEqual(fmt(
            "seç x\nhal 1\nyaz(1)\nhal 2 → yaz(2)\ndigər hallarda\n"
            "yaz(0)\nson\n"),
            "seç x\n    hal 1\n        yaz(1)\n    hal 2 → yaz(2)\n"
            "    digər hallarda\n        yaz(0)\nson\n")

    def test_dövr_və_cəhd(self):
        self.assertEqual(fmt(
            "hər i üçün 1..3 içində\ncəhd et\nyaz(i)\ntut x\nyaz(x)\n"
            "nəhayət\nyaz(0)\nson\nson\n"),
            "hər i üçün 1..3 içində\n    cəhd et\n        yaz(i)\n"
            "    tut x\n        yaz(x)\n    nəhayət\n        yaz(0)\n"
            "    son\nson\n")

    def test_sinif_komponent_qısa_qurucu(self):
        k = ("komponent S\nqurucu(xassə k: mətn)\nvəziyyət n: tam = 0\n"
             "göstər()\nqaytar <p>{özü.k}</p>\nson\nson\n")
        self.assertEqual(fmt(k),
                         "komponent S\n    qurucu(xassə k: mətn)\n"
                         "    vəziyyət n: tam = 0\n    göstər()\n"
                         "        qaytar <p>{özü.k}</p>\n    son\nson\n")

    def test_interfeys_və_sadalama(self):
        self.assertEqual(fmt(
            "interfeys Ş\nmetod sahə() -> onluq\nson\n"
            "sadalama Rəng\nQIRMIZI\nYAŞIL\nson\n"),
            "interfeys Ş\n    metod sahə() -> onluq\nson\n"
            "sadalama Rəng\n    QIRMIZI\n    YAŞIL\nson\n")

    def test_mötərizə_içində_çoxsətirli_əgər(self):
        k = ("yaz([\n1,\nəgər a onda\n2\nyoxsa\n3\nson\n])\n")
        self.assertEqual(fmt(k), "yaz([\n    1,\n    əgər a onda\n"
                                 "        2\n    yoxsa\n        3\n"
                                 "    son\n])\n")

    def test_arqument_kimi_funksiya(self):
        k = 's.al("/", funksiya(q)\nqaytar 1\nson)\n'
        self.assertEqual(fmt(k),
                         's.al("/", funksiya(q)\n    qaytar 1\nson)\n')

    def test_hizalanmış_davam_sətri_qorunur(self):
        k = ('vidjet.başlıq(mətn: "a",\n'
             '              altMətn: "b"\n'
             '                       + "c")\n')
        self.assertEqual(fmt(k), k)

    def test_davam_sətri_ən_azı_bir_pillə(self):
        self.assertEqual(fmt("dəyişən s = [\n1,\n2\n]\n"),
                         "dəyişən s = [\n    1,\n    2\n]\n")

    def test_aparıcı_nöqtəli_zəncir(self):
        k = "dəyişən a = b()\n    .c()\n    .d()\n"
        self.assertEqual(fmt(k), k)


class BoşluqSınağı(unittest.TestCase):
    def test_operatorlar_və_vergül(self):
        self.assertEqual(fmt("dəyişən x=f( 1,2 )*3+-4\n"),
                         "dəyişən x = f(1, 2) * 3 + -4\n")

    def test_təkli_mənfi(self):
        self.assertEqual(fmt("yaz(-1, a - b, -a, [ -2 ])\n"),
                         "yaz(-1, a - b, -a, [-2])\n")

    def test_davam_sətrindəki_ikili_operator(self):
        k = 'yaz("a"\n    + "b")\n'
        self.assertEqual(fmt(k), k)

    def test_üzv_adı_olan_açar_söz(self):
        self.assertEqual(fmt('s.statik("/a", "b")\nveb.boş(204)\n'),
                         's.statik("/a", "b")\nveb.boş(204)\n')

    def test_adlı_arqument_və_tip(self):
        self.assertEqual(fmt("funksiya f(a : tam)->tam\nqaytar g(x : 1)\n"
                             "son\n"),
                         "funksiya f(a: tam) -> tam\n    qaytar g(x: 1)\n"
                         "son\n")

    def test_ox_və_diapazon(self):
        self.assertEqual(fmt("dəyişən f=(x)=>x*2\nyaz(1 .. 3)\n"),
                         "dəyişən f = (x) => x * 2\nyaz(1..3)\n")

    def test_sətir_sonu_şərhinin_hizalanması_qorunur(self):
        k = "dəyişən a = 1        // birinci\ndəyişən bc = 22      // ikinci\n"
        self.assertEqual(fmt(k), k)


class MətnSınağı(unittest.TestCase):
    def test_ascii_açar_sözlər(self):
        n = F.formatla("eger dogru onda\nyaz(1)\nson\n")
        self.assertEqual(n.mətn, "əgər doğru onda\n    yaz(1)\nson\n")
        self.assertEqual(n.ascii_düzəlişləri, 2)

    def test_ascii_saxla(self):
        self.assertEqual(fmt("eger a onda\nson\n", ascii_düzəlt=False),
                         "eger a onda\nson\n")

    def test_mətn_daxilinə_toxunulmur(self):
        k = 'yaz("eger   a,b")\n'
        self.assertEqual(fmt(k), k)

    def test_xam_çoxsətirli_mətn_yalnız_sürüşür(self):
        k = ('əgər a onda\ndəyişən c = x"""\n  .a{b:1}\n  """\nson\n')
        n = fmt(k)
        self.assertIn('    dəyişən c = x"""\n      .a{b:1}\n      """', n)

    def test_JSX_sürüşür(self):
        k = "göstər()\nqaytar <div>\n    <p>a</p>\n</div>\nson\n"
        self.assertEqual(fmt("komponent K\n" + k + "son\n"),
                         "komponent K\n    göstər()\n"
                         "        qaytar <div>\n            <p>a</p>\n"
                         "        </div>\n    son\nson\n")

    def test_şərh_sətirləri(self):
        self.assertEqual(fmt("// başlıq\nəgər a onda\n// gövdə\nyaz(1)\n"
                             "// sondan əvvəl\nson\n"),
                         "// başlıq\nəgər a onda\n    // gövdə\n"
                         "    yaz(1)\n    // sondan əvvəl\nson\n")

    def test_boş_sətirlər_sətir_sonları_tab_BOM(self):
        k = "﻿yaz(1)   \r\n\r\n\r\n\r\n\r\nəgər a onda\r\n\tyaz(2)\r\nson"
        self.assertEqual(fmt(k), "yaz(1)\n\n\nəgər a onda\n    yaz(2)\nson\n")


class TəhlükəsizlikSınağı(unittest.TestCase):
    def test_sintaksis_xətası_rədd_edilir(self):
        with self.assertRaises(F.FormatXətası) as k:
            fmt("əgər a onda\n")
        self.assertIn("sintaksis", str(k.exception))

    def test_homoqlif_bayraqsız_rədd_edilir(self):
        k = "dəyişən а = 1\n"               # kiril `а`
        with self.assertRaises(F.FormatXətası) as x:
            fmt(k)
        self.assertIn("homoqlif", str(x.exception))
        self.assertEqual(fmt(k, homoqlif_düzəlt=True), "dəyişən a = 1\n")

    def test_doğrulama_pozuq_nəticəni_rədd_edir(self):
        """`_qur` səhv kod qaytarsa belə fayl dəyişmir."""
        köhnə = F._qur
        F._qur = lambda a, ascii, boş: ("yaz(2)\n", 0)
        try:
            with self.assertRaises(F.FormatXətası) as k:
                fmt("yaz(1)\n")
            self.assertIn("dəyişdirilmədi", str(k.exception))
        finally:
            F._qur = köhnə

    def test_qısa_qurucu_mənası_dəyişmir(self):
        """Girinti § 6.3.1-də mənalıdır — formatlama onu qorumalıdır."""
        for k in ("sinif A\n    qurucu(xassə a: tam)\n        yaz(a)\n"
                  "    son\nson\n",
                  "sinif A\n    qurucu(xassə a: tam)\n    metod b()\n"
                  "    son\nson\n"):
            self.assertEqual(fmt(k), k)


class Nümunələr(unittest.TestCase):
    """Repodakı bütün kod artıq kanonik formatdadır."""

    def test_nümunələr_dəyişmir_və_idempotentdir(self):
        fayllar = F.faylları_tap([str(KÖK / "numuneler")])
        self.assertGreaterEqual(len(fayllar), 10)
        for f in fayllar:
            m = f.read_text(encoding="utf-8")
            n = F.formatla(m, f.name)
            self.assertEqual(n.mətn, m, f"{f.name}:\n{n.fərq(m, f.name)}")

    def test_bələdçi_proqramları_idempotentdir(self):
        for md in sorted((KÖK / "beledci").glob("*.md")):
            for b in re.findall(r"```alqor\n(.*?)```",
                                md.read_text(encoding="utf-8"), re.S):
                try:
                    bir = fmt(b)
                except F.FormatXətası:
                    continue                    # parça — tam proqram deyil
                self.assertEqual(fmt(bir), bir, f"{md.name}:\n{b}")


class FaylTapmaSınağı(unittest.TestCase):
    def test_manifest_və_qurma_atlanır(self):
        import tempfile
        with tempfile.TemporaryDirectory() as q:
            q = Path(q)
            (q / "mənbə").mkdir()
            (q / "qurma").mkdir()
            for f in ("layihe.alq", "mənbə/əsas.alq", "qurma/köhnə.alq"):
                (q / f).write_text('yaz("a")\n', encoding="utf-8")
            adlar = [f.name for f in F.faylları_tap([str(q)])]
            self.assertEqual(adlar, ["əsas.alq"])
            # açıq verilən fayl atlanmır
            self.assertEqual(len(F.faylları_tap([str(q / "layihe.alq")])), 1)


class CLISınağı(unittest.TestCase):
    def _işlət(self, *arq: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(KÖK / "alqorc" / "alqorc.py"),
             "format", *arq],
            capture_output=True, text=True, encoding="utf-8",
            env={"PYTHONIOENCODING": "utf-8", "PATH": ""})

    def test_yoxla_fərq_yaz(self):
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "a.alq"
            f.write_text("eger a onda\nyaz(1)\nson\n", encoding="utf-8")
            c = self._işlət("--yoxla", q)
            self.assertEqual(c.returncode, 1, c.stdout + c.stderr)
            c = self._işlət("--fərq", str(f))
            self.assertIn("+əgər a onda", c.stdout)
            self.assertEqual(f.read_text(encoding="utf-8"),
                             "eger a onda\nyaz(1)\nson\n")
            c = self._işlət(q)
            self.assertEqual(c.returncode, 0)
            self.assertEqual(f.read_text(encoding="utf-8"),
                             "əgər a onda\n    yaz(1)\nson\n")
            c = self._işlət("--yoxla", q)
            self.assertEqual(c.returncode, 0)

    def test_sintaksis_xətası_kod_2(self):
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "pis.alq"
            f.write_text("əgər onda\n", encoding="utf-8")
            c = self._işlət(str(f))
            self.assertEqual(c.returncode, 2)
            self.assertEqual(f.read_text(encoding="utf-8"), "əgər onda\n")


class AdlıYayma(unittest.TestCase):
    def test_iki_ulduz_təklidir(self):
        kod = "funksiya f(a, ...b, **c) qaytar g(...b, **c) son\n" \
              "yaz(f(1, ** {\"x\": 2}), 2 ** 3)\n"
        self.assertEqual(
            fmt(kod),
            "funksiya f(a, ...b, **c) qaytar g(...b, **c) son\n"
            "yaz(f(1, **{\"x\": 2}), 2 ** 3)\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
