"""`.forma` faylları: oxuma, yazma, xətalar və komponentə birləşmə."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import forma as F                              # noqa: E402
from alqor.xeta import XətaToplayıcı                      # noqa: E402

KÖK = Path(__file__).resolve().parent.parent

FORMA = """\
// Əsas.forma
forma Əsas
    başlıq = "Tələbə qeydiyyatı"
    en = 640
    hündürlük = 480

    obyekt Başlıq1: başlıq
        mətn = "Qeydiyyat"
        səviyyə = 2
    son
    obyekt Panel1: sütun
        boşluq = 8
        obyekt AdSahəsi: sahə
            etiket = "Ad"
            ad = "ad"
        son
        obyekt Aktiv: açar
            etiket = "Aktivdir"
            ad = "aktiv"
        son
        obyekt Saxla: düymə
            mətn = "Saxla"
            klik = Saxla_klik
        son
    son
    obyekt Nəticə: mətn
        məzmun = "Hələ heç nə yoxdur"
    son
    obyekt Gizli: mətn
        məzmun = "görünməz"
        görünür = yanlış
    son
son
"""

KOD = """\
gətir pəncərə

komponent Əsas
    əməl Saxla_klik()
        özü.Nəticə.məzmun = "Salam, {özü.AdSahəsi.dəyər}! {özü.Aktiv.yanıq}"
        özü.Saxla.mətn = "Saxlandı"
        özü.Gizli.göstər()
    son
son

funksiya əsas()
    dəyişən p = pəncərə.formaAç(Əsas, göstər: yanlış)
    yaz(p.başlıq())
    dəyişən s = pəncərə.sınaq.aç(p)
    yaz(s.ehtiva("Hələ heç nə yoxdur"), s.ehtiva("görünməz"))
    s.yaz("ad", "Aysel")
    s.hadisə("dəyişdi", "aktiv", doğru)
    s.klik("Saxla")
    yaz(s.ehtiva("Salam, Aysel! doğru"), s.ehtiva("Saxlandı"),
        s.ehtiva("görünməz"))
son
"""


def _oxu(m: str):
    x = XətaToplayıcı()
    return F.mətndən(m, "A.forma", x), x


def _işlət(q: Path, fayl: str = "Əsas.alq"):
    return subprocess.run(
        [sys.executable, str(KÖK / "alqorc.py"), "işlət", str(q / fayl)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        env=dict(os.environ, PYTHONIOENCODING="utf-8", ALQOR_BASSIZ="1"))


class Format(unittest.TestCase):
    def test_oxuma_və_model(self):
        f, x = _oxu(FORMA)
        self.assertTrue(x.uğurludur(), x.hesabat(False))
        self.assertEqual(f.ad, "Əsas")
        self.assertEqual(f.xassələr["en"], 640)
        self.assertEqual([o.ad for o in f.hamısı()],
                         ["Başlıq1", "Panel1", "AdSahəsi", "Aktiv", "Saxla",
                          "Nəticə", "Gizli"])
        s = f.tap("Saxla")
        self.assertEqual(s.növ, "düymə")
        self.assertEqual(s.xassələr["klik"], F.İstinad("Saxla_klik"))
        self.assertIs(f.tap("Gizli").xassələr["görünür"], False)

    def test_yazma_dövrəsi_itkisizdir(self):
        f, _ = _oxu(FORMA)
        y = F.yaz(f)
        f2, x = _oxu(y)
        self.assertTrue(x.uğurludur())
        self.assertEqual(F.yaz(f2), y)

    def test_bütün_dəyər_növləri(self):
        m = ('forma A\n    obyekt B: cədvəl\n'
             '        sütunlar = ["Ad", "Yaş"]\n'
             '        sətirlər = [["Əli", 30], ["Leyla", -7.5]]\n'
             '    son\n    obyekt C: mətn\n'
             '        məzmun = "dırnaq \\" və \\{mötərizə\\} \\n sətir"\n'
             '    son\nson\n')
        f, x = _oxu(m)
        self.assertTrue(x.uğurludur(), x.hesabat(False))
        self.assertEqual(f.tap("B").xassələr["sətirlər"],
                         [["Əli", 30], ["Leyla", -7.5]])
        self.assertEqual(f.tap("C").xassələr["məzmun"],
                         'dırnaq " və {mötərizə} \n sətir')
        self.assertEqual(F.yaz(_oxu(F.yaz(f))[0]), F.yaz(f))

    def test_xətalar(self):
        hallar = [
            ('forma A\n    obyekt B: düyme\n    son\nson\n', "ALQ-F003",
             "bəlkə `düymə`?"),
            ('forma A\n    obyekt B düymə\n    son\nson\n', "ALQ-F001", ""),
            ('forma A\n    obyekt B: mətn\n        məzmun = "{x}"\n'
             '    son\nson\n', "ALQ-F001", ""),
            ('forma A\n    başlıq = "x"\n', "ALQ-F001", ""),
            ('forma A\n    obyekt B: düymə\n    son\n    obyekt B: mətn\n'
             '    son\nson\n', "ALQ-F002", ""),
            ('forma A\n    obyekt B: düymə\n        obyekt C: mətn\n'
             '        son\n    son\nson\n', "ALQ-F005", ""),
        ]
        for m, kod, kömək in hallar:
            with self.subTest(kod=kod, m=m):
                f, x = _oxu(m)
                self.assertIsNone(f)
                self.assertIn(kod, [d.kod for d in x.siyahı])
                if kömək:
                    self.assertIn(kömək, x.hesabat(False))

    def test_naməlum_xassə_xəbərdarlıqdır(self):
        f, x = _oxu('forma A\n    obyekt B: düymə\n        mətnn = "x"\n'
                    '    son\nson\n')
        self.assertIsNotNone(f)
        self.assertEqual([d.kod for d in x.siyahı], ["ALQ-F004"])
        self.assertIn("bəlkə `mətn`?", x.hesabat(False))


class Birləşmə(unittest.TestCase):
    def setUp(self):
        self.q = Path(tempfile.mkdtemp(prefix="forma-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.q, ignore_errors=True)

    def test_forma_və_kod_birlikdə_işləyir(self):
        (self.q / "Əsas.forma").write_text(FORMA, encoding="utf-8")
        (self.q / "Əsas.alq").write_text(KOD, encoding="utf-8")
        r = _işlət(self.q)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), [
            "Tələbə qeydiyyatı", "doğru yanlış", "doğru doğru doğru"])

    def test_hadisə_metodu_yoxdursa_aydın_xəta(self):
        (self.q / "Əsas.forma").write_text(FORMA, encoding="utf-8")
        (self.q / "Əsas.alq").write_text(
            "gətir pəncərə\nkomponent Əsas\nson\n"
            "pəncərə.formaAç(Əsas, göstər: yanlış)\n", encoding="utf-8")
        r = _işlət(self.q)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ALQ-F006", r.stderr)
        self.assertIn("`Saxla_klik` metodu yoxdur", r.stderr)

    def test_forma_xətası_açılışda_göstərilir(self):
        (self.q / "Əsas.forma").write_text(
            "forma Əsas\n    obyekt B: düyme\n    son\nson\n",
            encoding="utf-8")
        (self.q / "Əsas.alq").write_text(
            "komponent Əsas\nson\n", encoding="utf-8")
        r = _işlət(self.q)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ALQ-F003", r.stderr)

    def test_sərbəst_düzülüş_və_öz_göstər_metodu(self):
        (self.q / "Kətan.forma").write_text(
            'forma Kətan\n    düzülüş = "sərbəst"\n'
            '    obyekt D: düymə\n        mətn = "Bas"\n        sol = 40\n'
            '        yuxarı = 20\n        en = 120\n    son\nson\n',
            encoding="utf-8")
        (self.q / "Kətan.alq").write_text(
            "gətir pəncərə\nkomponent Kətan\nson\n"
            "dəyişən p = pəncərə.formaAç(Kətan, göstər: yanlış)\n"
            "yaz(p.HTML())\n", encoding="utf-8")
        r = _işlət(self.q, "Kətan.alq")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("position:absolute;left:40px;top:20px;width:120px",
                      r.stdout)
        self.assertIn("Bas", r.stdout)

    def test_formasız_komponent_dəyişmir(self):
        (self.q / "Sayğac.alq").write_text(
            "gətir pəncərə\nkomponent Sayğac\n    vəziyyət say: tam = 0\n"
            "    göstər()\n        qaytar <b>{özü.say}</b>\n    son\nson\n"
            "yaz(pəncərə.formaAç(Sayğac, göstər: yanlış).HTML())\n",
            encoding="utf-8")
        r = _işlət(self.q, "Sayğac.alq")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("<b>0</b>", r.stdout)


if __name__ == "__main__":
    unittest.main()
