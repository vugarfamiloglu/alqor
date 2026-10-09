"""
JS hədəfi: Python icraçısı ilə Node.js çıxışının müqayisəsi.

Korpus `test_icraci.py`-dakı bütün kod parçalarından yığılır (hər
parçanın Python nəticəsi etalondur), üstəlik `sinaq/js_numuneler/`
proqramları. Node.js yoxdursa sınaqlar ötürülür.
"""

import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.js import KompilyasiyaXətası, mətndən, veb_səhifəsi  # noqa: E402
from alqor.js.muqayise import js_işlət, node_tap               # noqa: E402

KÖK = Path(__file__).parent.parent
NÜMUNƏLƏR = Path(__file__).parent / "js_numuneler"
NODE = node_tap()


def _korpus() -> list[dict]:
    """`test_icraci` parçalarını işlədib (kod, giriş, çıxış, xəta) yığır."""
    from sinaq import test_icraci as T
    qeyd: list[dict] = []
    orijinal = T.işlət

    def yazan(kod, giriş=None):
        s, x = orijinal(kod, giriş)
        qeyd.append({"kod": kod, "giriş": list(giriş or []),
                     "çıxış": list(s), "xəta": x.tip if x else None})
        return s, x

    T.işlət = yazan
    try:
        unittest.TextTestRunner(stream=io.StringIO()).run(
            unittest.TestLoader().loadTestsFromModule(T))
    finally:
        T.işlət = orijinal
    görülən: set[str] = set()
    n = []
    for q in qeyd:
        if q["kod"] not in görülən:
            görülən.add(q["kod"])
            n.append(q)
    return n


def _python_çıxışı(yol: Path) -> tuple[str, int]:
    r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "işlət",
                        str(yol)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    return r.stdout, r.returncode


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class KorpusMüqayisəsi(unittest.TestCase):
    def test_icraçı_parçaları_eyni_nəticə_verir(self):
        korpus = _korpus()
        self.assertGreater(len(korpus), 150)
        js = js_işlət(korpus, NODE)
        fərqlər = []
        for n, j in zip(korpus, js):
            if j["çıxış"] != n["çıxış"] or j["xəta"] != n["xəta"]:
                fərqlər.append(f"{n['kod']}\n  python: {n['çıxış']} "
                               f"{n['xəta']}\n  js    : {j['çıxış']} "
                               f"{j['xəta']}")
        self.assertEqual(fərqlər, [], "\n\n".join(fərqlər[:5]))


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class NümunəProqramlar(unittest.TestCase):
    def test_nümunələr_eyni_çıxış_verir(self):
        fayllar = sorted(NÜMUNƏLƏR.glob("[0-9]*.alq"))
        self.assertGreaterEqual(len(fayllar), 10)
        for f in fayllar:
            with self.subTest(f.name):
                gözlənilən, kod = _python_çıxışı(f)
                self.assertEqual(kod, 0)
                r = subprocess.run(
                    [sys.executable, str(KÖK / "alqorc.py"), "işlət", "--js",
                     str(f)], capture_output=True, text=True,
                    encoding="utf-8", timeout=120)
                self.assertEqual(r.stdout, gözlənilən, r.stderr)

    def test_giriş_stdin_ilə(self):
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "g.alq"
            f.write_text('dəyişən ad = oxu("Ad: ")\n'
                         'dəyişən n = oxuTam()\n'
                         'yaz("Salam, {ad}! {n * 2}")\n', encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "işlət", "--js",
                 str(f)], input="Aysel\n21\n", capture_output=True,
                text=True, encoding="utf-8", timeout=60)
            self.assertEqual(r.stdout, "Ad: Salam, Aysel! 42\n")

    def test_xəta_çıxış_kodu(self):
        js = mətndən('yaz("a")\nat ArqumentXətası("pis")\nyaz("b")\n')
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "p.js"
            f.write_text(js, encoding="utf-8")
            r = subprocess.run([NODE, str(f)], capture_output=True,
                               text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "a\n")
        self.assertIn("ArqumentXətası: pis", r.stderr)

    def test_əsas_funksiyası_və_arqumentlər(self):
        js = mətndən('gətir sistem\nfunksiya əsas(arq)\n'
                     '    yaz(arq, sistem.arqumentlər())\n    qaytar 3\nson\n')
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "p.js"
            f.write_text(js, encoding="utf-8")
            r = subprocess.run([NODE, str(f), "x", "y"], capture_output=True,
                               text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, '["x", "y"] ["x", "y"]\n')


class Kompilyasiya(unittest.TestCase):
    def test_dəstəklənməyən_modul_aydın_xəta_verir(self):
        with self.assertRaises(KompilyasiyaXətası) as k:
            mətndən("gətir veb\nyaz(1)\n")
        self.assertIn("veb", str(k.exception))
        self.assertIn("dəstəklənmir", str(k.exception))

    def test_veb_səhifəsi(self):
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı
        x = XətaToplayıcı()
        s = Mənbə.mətndən('yaz("</script> salam")\n', "v.alq", x)
        html = veb_səhifəsi(Parser(Lekser(s, x).leksə(), s, x).ayır(),
                            "Sınaq <1>")
        self.assertIn("<title>Sınaq &lt;1&gt;</title>", html)
        self.assertEqual(html.count("</script>"), 1)
        self.assertIn('id="çıxış"', html)

    def test_qur_hədəf_js(self):
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "salam.alq"
            f.write_text('yaz("salam")\n', encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "qur", "--hədəf",
                 "js", str(f)], cwd=q, capture_output=True, text=True,
                encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            çıxış = Path(q) / "qurma" / "salam.js"
            self.assertTrue(çıxış.is_file())
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "qur", "--hədəf",
                 "veb", str(f)], cwd=q, capture_output=True, text=True,
                encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((Path(q) / "qurma" / "veb" / "index.html")
                            .is_file())
            if NODE:
                r = subprocess.run([NODE, str(çıxış)], capture_output=True,
                                   text=True, encoding="utf-8")
                self.assertEqual(r.stdout, "salam\n")


class Dil(unittest.TestCase):
    """JS işi zamanı Python icraçısında tapılıb düzəldilən hallar."""

    def test_şərtli_seç_ifadə_halları(self):
        from sinaq.test_icraci import çıxış
        self.assertEqual(çıxış(
            "dəyişən t = 25\nseç\n    hal t < 10 → yaz(\"soyuq\")\n"
            "    hal t < 30 → yaz(\"isti\")\n"
            "    digər hallarda → yaz(\"çox\")\nson\n"), ["isti"])

    def test_lambda_blok_gövdəsi_ver(self):
        from sinaq.test_icraci import çıxış
        self.assertEqual(çıxış(
            "dəyişən say = 0\ndəyişən f = () => blok\n    say += 1\n"
            "    ver say * 10\nson\nf()\nyaz(f())\n"), ["20"])


if __name__ == "__main__":
    unittest.main()
