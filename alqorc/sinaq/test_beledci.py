"""
Bələdçidəki kod nümunələri işləməlidir.

Qayda (bələdçi faylları üçün):
  `// addım …` ilə başlayan blok — TAM proqram: ayrılır, tip
      yoxlamasından keçir və başsız rejimdə icra olunur.
  `// parça …` ilə başlayan blok — fraqment: olduğu kimi və ya
      komponent gövdəsinə bükülərək ayrılmalıdır.
  Başqa `alqor` blokları — olduğu kimi ayrılmalıdır.
  `alqorhtml` blokları şablon kimi ayrılmalıdır; `<!-- fayl: yol -->`
      ilə başlayanlar addım proqramları işləməzdən əvvəl müvəqqəti
      layihə qovluğuna yazılır.

Sınaqda `pəncərə` başsızdır. `veb.Server.dinlə()` port açmır: əvəzinə
parametrsiz hər GET marşrutuna və komponentə sınaq sorğusu göndərir —
şablon və ya idarəedici xətası (5xx) sınağı sındırır.
"""

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import alqor.pencere as P                                   # noqa: E402
import alqor.veb as VEB                                     # noqa: E402
from alqor.icraci import İcraçı                             # noqa: E402
from alqor.lekser import Lekser                             # noqa: E402
from alqor.menbe import Mənbə                               # noqa: E402
from alqor.parser import Parser                             # noqa: E402
from alqor.tipyoxlayici import TipYoxlayıcı                 # noqa: E402
from alqor.xeta import XətaToplayıcı                        # noqa: E402

BƏLƏDÇİ = Path(__file__).parent.parent.parent / "beledci"

# Yoxlanılan dərsliklər — yenisi əlavə ediləndə bura yazılır
FAYLLAR = ("00-BASLANGIC.md", "02-VEB-DERSLIYI.md",
           "03-DESKTOP-DERSLIYI.md",
           "07-VIDJET-DERSLIYI.md")


def bloklar(fayl: str, dil: str = "alqor") -> list[str]:
    mətn = (BƏLƏDÇİ / fayl).read_text(encoding="utf-8")
    return re.findall(rf"```{dil}\n(.*?)```", mətn, re.S)


FAYL_QEYDİ = re.compile(r"<!-- fayl: (\S+) -->\n")


def _ayır(kod: str):
    x = XətaToplayıcı()
    m = Mənbə.mətndən(kod, "bələdçi.alq", x)
    ağac = Parser(Lekser(m, x).leksə(), m, x).ayır()
    return ağac, x


def _bük(kod: str) -> str:
    return "komponent K\n" + "".join(
        f"    {s}\n" for s in kod.split("\n")) + "son\n"


class BələdçiSınağı(unittest.TestCase):
    def setUp(self):
        self._köhnə = P._başsız_rejimdir
        P._başsız_rejimdir = lambda: True
        self._köhnə_dinlə = VEB.Server.dinlə
        self.yoxlanılan: list[str] = []
        VEB.Server.dinlə = lambda özü, *a, **k: self._marşrutları_yoxla(
            özü)
        self.qovluq = Path(tempfile.mkdtemp())

    def tearDown(self):
        P._başsız_rejimdir = self._köhnə
        VEB.Server.dinlə = self._köhnə_dinlə
        shutil.rmtree(self.qovluq, ignore_errors=True)

    def _marşrutları_yoxla(self, server) -> None:
        müştəri = VEB.SınaqMüştərisi(server, server._icraçı)
        yollar = [m.naxış for m in server._marşrutlar
                  if m.metod in ("GET", "*") and ":" not in m.naxış
                  and "*" not in m.naxış]
        yollar += [q.yol for q in server._komponentlər]
        for yol in yollar:
            c = müştəri.al(yol)
            self.assertLess(c.vəziyyət, 500,
                            f"{yol} → {c.vəziyyət}\n{c.mətnƏt()[:400]}")
            self.yoxlanılan.append(yol)

    def _şablonları_yaz(self, fayl: str) -> None:
        for b in bloklar(fayl, "alqorhtml"):
            m = FAYL_QEYDİ.match(b)
            if m:
                yol = self.qovluq / m.group(1)
                yol.parent.mkdir(parents=True, exist_ok=True)
                yol.write_text(b[m.end():], encoding="utf-8")

    def test_şablonlar_ayrılır(self):
        from alqor.sablon import ayır
        for fayl in FAYLLAR:
            for b in bloklar(fayl, "alqorhtml"):
                ayır(b, fayl)

    def test_addımlar_işləyir(self):
        say = 0
        for fayl in FAYLLAR:
            self._şablonları_yaz(fayl)
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
                i = İcraçı(çıxış=çıxış.append, giriş=lambda: "")
                i.əsas_qovluq = self.qovluq
                kod = i.işlət(ağac, [])
                self.assertEqual(kod, 0, f"{fayl}: {b[:40]}")
        self.assertGreaterEqual(say, 7)
        # Veb addımlarının səhifələri həqiqətən göstərildi
        for yol in ("/", "/axtar"):
            self.assertIn(yol, self.yoxlanılan)

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
