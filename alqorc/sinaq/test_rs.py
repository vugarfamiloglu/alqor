"""
Rust implementasiyası (`alqor-rs/`) — Python etalonu ilə diferensial
müqayisə: tokenlər, AAC, xəta mesajları və icra nəticələri eyni olmalıdır.
Cargo yoxdursa sınaqlar ötürülür.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.rs import muqayise as M                        # noqa: E402

CARGO = shutil.which("cargo") or (
    str(Path.home() / ".cargo" / "bin" / "cargo")
    if (Path.home() / ".cargo" / "bin" / "cargo").exists() else None)


@unittest.skipIf(CARGO is None, "cargo tapılmadı")
class RustMüqayisəsi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binar = M.qur()
        if cls.binar is None:
            raise AssertionError("alqor-rs qurulmadı")
        cls.q = Path(tempfile.mkdtemp(prefix="alqor-rs-sinaq-"))
        cls.korpus = M.korpus_faylları(cls.q / "korpus")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.q, ignore_errors=True)

    def müqayisə(self, fayllar, py, rs):
        fərqlər: list[str] = []
        pis = M.müqayisə_et(self.binar, fayllar, py, rs, çıxış=fərqlər.append)
        self.assertEqual(pis, 0, "\n".join(fərqlər[:5]))

    def test_tokenlər_repo_faylları(self):
        self.müqayisə(M.bütün_alq(), M.python_tokenləri, M.rust_tokenləri)

    def test_tokenlər_korpus(self):
        self.müqayisə(self.korpus, M.python_tokenləri, M.rust_tokenləri)

    def test_aac_və_diaqnostika_repo_faylları(self):
        self.müqayisə(M.bütün_alq(), M.python_aac_diaq, M.rust_aac_diaq)

    def test_aac_və_diaqnostika_korpus(self):
        self.müqayisə(self.korpus, M.python_aac_diaq, M.rust_aac_diaq)

    def test_xətalı_kod_diaqnostikaları(self):
        nümunələr = [
            "yaz(1\n", "dəyişən = 5\n", "əgər x\n    yaz(1)\n",
            'yaz("bağlanmamış\n', "x = 1 $ 2\n", 'yaz("\\y")\n',
            "eger doğru\n    yaz(1)\nson\n", "funksiya f(\n",
            "sinif A\n    xassə\nson\n", "<div>\n", "seç x\nson\n",
            "hər x üçün\nson\n", "1 +\n", "qaytar qaytar\n",
            # Makrolar (§ 5.12)
            "makro k(x) = x * x\nyaz(k!(1, 2))\n",
            "makro t(n, iş: blok)\n    yaz(iş)\nson\nt!(1)\n    yaz(2)\nson\n",
            "makro p(a: tam)\n    yaz(a)\nson\np!(1)\n",
            "makro b(iş: blok)\n    iş\nson\ndəyişən y = b!()\n",
            "makro q(x) = x\nyaz(q!())\n", "makro r(x)\n    yaz(x)\n",
            # Sorğu (§ 4.13)
            "yaz(sorğu hər x üçün [1] içində seç x harada x son)\n",
            "yaz(sorğu hər x üçün [1] içində qrupla x (a, b) son)\n",
            "yaz(sorğu hər x üçün [1] içində tap x son)\n",
            "yaz(sorğu hər x üçün [1]\n",
            # Şəkilçi formaları (§ 4.14)
            "yaz(siyahı(1-dən 3))\n",
            "dəyişən l = []\nl-a əlavə et 5\n",
            # Sınaq sintaksisi (§ 13.5)
            'sınaq "a{1}"\nson\n',
            "gözlənilir xəta Tip 1\n",
            "gözlənilir\n",
            # Müqavilələr (§ 5.13)
            "funksiya f(x)\n    yaz(x)\n    tələb x > 0\nson\n",
            "tələb 1 > 0\n",
            "generator funksiya g()\n    zəmanət nəticə\n    ver 1\nson\n",
        ]
        fayllar = []
        for i, k in enumerate(nümunələr):
            f = self.q / f"x{i:02d}.alq"
            f.write_text(k, encoding="utf-8")
            fayllar.append(f)
        self.müqayisə(fayllar, M.python_aac_diaq, M.rust_aac_diaq)


def _binar():
    if shutil.which("cargo") or (Path.home() / ".cargo" / "bin" / "cargo").exists():
        return M.qur()
    return M.binar()


_B = _binar()


@unittest.skipIf(_B is None, "cargo / alqor-rs mövcud deyil")
class RustİcraMüqayisəsi(unittest.TestCase):
    def test_icraçı_korpusu(self):
        fərqlər: list[str] = []
        eyni, cəmi = M.korpus_işlət(_B, çıxış=fərqlər.append)
        self.assertEqual(eyni, cəmi, "\n".join(fərqlər))

    def test_nümunə_proqramlar(self):
        fərqlər: list[str] = []
        fayllar = M.proqramlar()
        self.assertGreater(len(fayllar), 10)
        pis = M.proqram_işlət(_B, fayllar, çıxış=fərqlər.append)
        self.assertEqual(pis, 0, "\n".join(fərqlər))

    def test_python_kitabxanası_aydın_xəta(self):
        """`gətir python:…` Rust icraçısında aydın xəta verir (§ 8.14)."""
        import subprocess
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "p.alq"
            f.write_text("gətir python:math\nyaz(math.pi)\n",
                         encoding="utf-8")
            r = subprocess.run([str(_B), "işlət", str(f)],
                               capture_output=True, timeout=60)
        çıxış = (r.stdout + r.stderr).decode("utf-8", "replace")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Python kitabxanaları yalnız əsas (Python) "
                      "icraçısında işləyir", çıxış)
        self.assertIn("ALQ-M015", çıxış)

    def test_icra_parçaları(self):
        fərqlər: list[str] = []
        eyni, cəmi = M.parçalar_işlət(_B, çıxış=fərqlər.append)
        self.assertEqual(eyni, cəmi, "\n".join(fərqlər))


@unittest.skipIf(_B is None or M.node_tap() is None,
                 "cargo / alqor-rs və ya node mövcud deyil")
class RustWasmMüqayisəsi(unittest.TestCase):
    """WebAssembly paketi (wasm/alqor.js + alqor.wasm) yerli binarla eynidir."""

    def test_wasm_parçalar(self):
        if M.wasm_qur() is None:
            self.skipTest("wasm32-unknown-unknown hədəfi yoxdur")
        fərqlər: list[str] = []
        eyni, cəmi = M.wasm_müqayisə(_B, M.node_tap(), çıxış=fərqlər.append)
        self.assertGreater(cəmi, 50)
        self.assertEqual(eyni, cəmi, "\n".join(fərqlər))


if __name__ == "__main__":
    unittest.main()
