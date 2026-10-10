"""`alqor-rs` (Rust icraçısı) Python etalonu ilə eyni nəticə verir.

Cargo (və ya qurulmuş `alqor-rs` binarı) yoxdursa sınaqlar atlanır.
"""

import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.rs import muqayise as M                  # noqa: E402


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

    def test_icra_parçaları(self):
        fərqlər: list[str] = []
        eyni, cəmi = M.parçalar_işlət(_B, çıxış=fərqlər.append)
        self.assertEqual(eyni, cəmi, "\n".join(fərqlər))


if __name__ == "__main__":
    unittest.main()
