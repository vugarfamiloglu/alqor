"""
Bələdçidəki kod nümunələri işləməlidir.

Qayda (bələdçi faylları üçün):
  `// addım …` ilə başlayan blok — TAM proqram: ayrılır, tip
      yoxlamasından keçir və başsız rejimdə icra olunur.
  `// parça …` ilə başlayan blok — fraqment: olduğu kimi və ya
      komponent gövdəsinə bükülərək ayrılmalıdır.
  Başqa `alqor` blokları — olduğu kimi ayrılmalıdır.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import alqor.pencere as P                                   # noqa: E402
from alqor.icraci import İcraçı                             # noqa: E402
from alqor.lekser import Lekser                             # noqa: E402
from alqor.menbe import Mənbə                               # noqa: E402
from alqor.parser import Parser                             # noqa: E402
from alqor.tipyoxlayici import TipYoxlayıcı                 # noqa: E402
from alqor.xeta import XətaToplayıcı                        # noqa: E402

BƏLƏDÇİ = Path(__file__).parent.parent.parent / "beledci"

# Yoxlanılan dərsliklər — yenisi əlavə ediləndə bura yazılır
FAYLLAR = ("03-DESKTOP-DERSLIYI.md",)


def bloklar(fayl: str) -> list[str]:
    mətn = (BƏLƏDÇİ / fayl).read_text(encoding="utf-8")
    return re.findall(r"```alqor\n(.*?)```", mətn, re.S)


def _ayır(kod: str):
    x = XətaToplayıcı()
    m = Mənbə.mətndən(kod, "bələdçi.alqor", x)
    ağac = Parser(Lekser(m, x).leksə(), m, x).ayır()
    return ağac, x


def _bük(kod: str) -> str:
    return "komponent K\n" + "".join(
        f"    {s}\n" for s in kod.split("\n")) + "son\n"


class BələdçiSınağı(unittest.TestCase):
    def setUp(self):
        self._köhnə = P._başsız_rejimdir
        P._başsız_rejimdir = lambda: True

    def tearDown(self):
        P._başsız_rejimdir = self._köhnə

    def test_addımlar_işləyir(self):
        say = 0
        for fayl in FAYLLAR:
            for b in bloklar(fayl):
                if not b.startswith("// addım"):
                    continue
                say += 1
                ağac, x = _ayır(b)
                self.assertTrue(x.uğurludur(),
                                f"{fayl}: ayrılmır\n{b}\n"
                                + x.hesabat(False))
                t = XətaToplayıcı()
                TipYoxlayıcı(t).yoxla(ağac)
                self.assertTrue(t.uğurludur(),
                                f"{fayl}: tip xətası\n{b}\n"
                                + t.hesabat(False))
                çıxış: list[str] = []
                kod = İcraçı(çıxış=çıxış.append,
                             giriş=lambda: "").işlət(ağac, [])
                self.assertEqual(kod, 0, f"{fayl}: {b[:40]}")
        self.assertGreaterEqual(say, 3)

    def test_parçalar_ayrılır(self):
        for fayl in FAYLLAR:
            for b in bloklar(fayl):
                if b.startswith("// addım"):
                    continue
                _, x = _ayır(b)
                if x.uğurludur():
                    continue
                _, x2 = _ayır(_bük(b))
                self.assertTrue(x2.uğurludur(),
                                f"{fayl}: parça ayrılmır\n{b}\n"
                                + x.hesabat(False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
