"""
Rust implementasiyası (`alqor-rs/`) — Python etalonu ilə diferensial
müqayisə: tokenlər, AAC və xəta mesajları eyni olmalıdır.
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
        ]
        fayllar = []
        for i, k in enumerate(nümunələr):
            f = self.q / f"x{i:02d}.alq"
            f.write_text(k, encoding="utf-8")
            fayllar.append(f)
        self.müqayisə(fayllar, M.python_aac_diaq, M.rust_aac_diaq)


if __name__ == "__main__":
    unittest.main()
