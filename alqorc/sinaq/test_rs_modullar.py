"""
Rust icraçısının əlavə standart modulları (`alqor-rs/src/icraci/mod_*.rs`)
— Python etalonu ilə diferensial müqayisə.

    sinaq/rs_modul_parcalari.alq   `=====` ilə ayrılmış parçalar: stdout,
                                   stderr və çıxış kodu tam eyni olmalıdır

Şəbəkə (http, veb) və verilənlər bazası sınaqları yerli serverlə və
müvəqqəti SQLite faylları ilə aparılır — internet lazım deyil.
"""

import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.rs import muqayise as M                        # noqa: E402

PARÇALAR = Path(__file__).parent / "rs_modul_parcalari.alq"


def _binar():
    if shutil.which("cargo") or (Path.home() / ".cargo" / "bin" / "cargo").exists():
        return M.qur()
    return M.binar()


_B = _binar()


@unittest.skipIf(_B is None, "cargo / alqor-rs mövcud deyil")
class RustModulMüqayisəsi(unittest.TestCase):
    def test_modul_parçaları(self):
        fərqlər: list[str] = []
        eyni, cəmi = M.parçalar_işlət(_B, PARÇALAR, çıxış=fərqlər.append)
        self.assertEqual(eyni, cəmi, "\n".join(fərqlər))


if __name__ == "__main__":
    unittest.main()
