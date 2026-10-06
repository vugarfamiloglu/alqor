"""`konsol` modulu, çoxsətirli zəncir və açar söz etiketləri."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from test_icraci import ayır, işlət, çıxış                  # noqa: E402

BAŞLIQ = "gətir konsol\n"


def proqram(kod: str, arqumentlər: list[str],
            giriş: list[str] | None = None) -> tuple[list[str], int]:
    """`əsas(arqumentlər)` ilə işlədir → (çıxış, çıxış kodu)."""
    from alqor.icraci import İcraçı
    from alqor.lekser import Lekser
    from alqor.menbe import Mənbə
    from alqor.parser import Parser
    from alqor.xeta import XətaToplayıcı

    x = XətaToplayıcı()
    m = Mənbə.mətndən(BAŞLIQ + kod, "sınaq.alqor", x)
    ağac = Parser(Lekser(m, x).leksə(), m, x).ayır()
    assert x.uğurludur(), x.hesabat(False)
    sətirlər: list[str] = []
    növbə = list(giriş or [])
    i = İcraçı(çıxış=sətirlər.append,
               giriş=lambda: növbə.pop(0) if növbə else (_ for _ in ())
               .throw(EOFError()))
    kod_ = i.işlət(ağac, arqumentlər)
    return sətirlər, kod_


class RəngSınağı(unittest.TestCase):
    def setUp(self):
        self._köhnə = os.environ.pop("NO_COLOR", None)

    def tearDown(self):
        if self._köhnə is not None:
            os.environ["NO_COLOR"] = self._köhnə
        else:
            os.environ.pop("NO_COLOR", None)

    def test_ANSI_kodları(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.qırmızı("x"))\n'
                  'yaz(konsol.rəng("y", ön: "mavi", arxa: "ağ", '
                  'qalın: doğru))')
        self.assertEqual(s[0], "\033[31mx\033[0m")
        self.assertEqual(s[1], "\033[1;34;47my\033[0m")

    def test_NO_COLOR(self):
        os.environ["NO_COLOR"] = "1"
        self.assertEqual(çıxış(BAŞLIQ + 'yaz(konsol.yaşıl("x"))'), ["x"])

    def test_naməlum_rəng(self):
        _, x = işlət(BAŞLIQ + 'konsol.rəng("a", ön: "çəhrayı")')
        self.assertEqual(x.tip, "ArqumentXətası")
        self.assertIn("qırmızı", x.mesaj)


class SualCavabSınağı(unittest.TestCase):
    def test_soruş_standart(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.soruş("Ad: ", "Qonaq"))\n'
                  'yaz(konsol.soruş("Ad: ", "Qonaq"))', ["", "Aysel"])
        self.assertEqual(s, ["Qonaq", "Aysel"])

    def test_təsdiqlə(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.təsdiqlə("Davam?"))\n'
                  'yaz(konsol.təsdiqlə("Davam?"))\n'
                  'yaz(konsol.təsdiqlə("Davam?", doğru))',
                  ["bilmirəm", "Hə", "yox", ""])
        self.assertEqual(s, ["`hə` və ya `yox` yazın.", "doğru",
                             "yanlış", "doğru"])

    def test_seç_elementi_qaytarır(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.seç("Rəng:", '
                  '["Qırmızı", "Yaşıl", "Mavi"]))', ["9", "2"])
        self.assertEqual(s, ["Rəng:", "  1) Qırmızı", "  2) Yaşıl",
                             "  3) Mavi", "1 ilə 3 arasında nömrə yazın.",
                             "Yaşıl"])

    def test_seç_adla(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.seç("", ["Bakı", "Gəncə"]))',
                  ["gəncə"])
        self.assertEqual(s[-1], "Gəncə")

    def test_çoxSeç(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.çoxSeç("?", ["A", "B", "C"]))\n'
                  'yaz(konsol.çoxSeç("?", ["A", "B", "C"]))',
                  ["3, 1 3", ""])
        self.assertEqual(s[4], '["C", "A"]')
        self.assertEqual(s[-1], "[]")

    def test_parol_sınaqda_girişdən(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.parolSoruş().uzunluq())', ["gizli"])
        self.assertEqual(s, ["5"])

    def test_giriş_bitəndə_xəta(self):
        """EOF-da boş sətir qaytarmaq `həmişə` dövrünü sonsuz edərdi."""
        _, x = işlət(BAŞLIQ + 'konsol.soruş("?")')
        self.assertIsNone(x)              # köməkçi EOF əvəzinə "" verir
        from alqor.deyerler import AlqorXəta
        with self.assertRaises(AlqorXəta) as k:
            proqram('funksiya əsas()\n    konsol.seç("?", ["a"])\nson', [])
        self.assertEqual(k.exception.tip, "GirişÇıxışXətası")


class GöstəriciSınağı(unittest.TestCase):
    def test_irəliləyiş_borunda_yalnız_yekun(self):
        s = çıxış(BAŞLIQ + """dəyişən p = konsol.irəliləyiş(4, "Yük")
hər i üçün 1..3 içində
    p.artır()
son
yaz(p.cari())
p.bitir()
p.bitir()""")
        self.assertEqual(s[0], "3")
        self.assertEqual(len(s), 2)
        self.assertIn("100%", s[1])
        self.assertIn("(4/4)", s[1])

    def test_irəliləyiş_hədləri(self):
        s = çıxış(BAŞLIQ + """dəyişən p = konsol.irəliləyiş(10)
p.yenilə(99)
yaz(p.cari())
p.yenilə(-5)
yaz(p.cari())""")
        self.assertEqual(s, ["10", "0"])

    def test_fırlanan(self):
        s = çıxış(BAŞLIQ + """dəyişən f = konsol.fırlanan("İşlənir")
yaz(f.işləyir())
f.dayandır("Bitdi")
yaz(f.işləyir())""")
        self.assertEqual(s, ["doğru", "Bitdi", "yanlış"])

    def test_cədvəl(self):
        s = çıxış(BAŞLIQ + 'konsol.cədvəl(["Ad", "Yaş"], '
                  '[["Aysel", 24], ["Rəşad"]])')
        self.assertEqual(s, ["Ad    │ Yaş", "──────┼────",
                             "Aysel │ 24", "Rəşad │"])

    def test_tip_adları(self):
        s = çıxış(BAŞLIQ + 'yaz(tip(konsol.irəliləyiş(3)))\n'
                  'yaz(tip(konsol.arqumentlər()))')
        self.assertEqual(s, ["irəliləyiş", "arqumentlər"])


class ArqumentSınağı(unittest.TestCase):
    KOD = """
funksiya əsas()
    dəyişən a = konsol.arqumentlər()
        .proqram("hesabla")
        .versiya("1.0.0")
        .təsvir("Riyazi hesablayıcı")
        .parametr("əməliyyat", "topla | çıx")
        .parametr("ədədlər", "Ədədlər", çoxlu: doğru)
        .bayraq("--ətraflı", "-ə", "Ətraflı çıxış")
        .seçim("--format", "-f", "Format", standart: "mətn")
        .təhlil()
    yaz(a.dəyər("əməliyyat"), a.siyahı("ədədlər"),
        a.bayraq("--ətraflı"), a.dəyər("--format"))
son
"""

    def test_təhlil(self):
        s, kod = proqram(self.KOD, ["topla", "1", "-ə", "2", "-f=json"])
        self.assertEqual(s, ['topla ["1", "2"] doğru json'])
        self.assertEqual(kod, 0)

    def test_standart_dəyər_və_cüt_tire(self):
        s, _ = proqram(self.KOD, ["çıx", "--", "-5"])
        self.assertEqual(s, ['çıx ["-5"] yanlış mətn'])

    def test_kömək(self):
        s, kod = proqram(self.KOD, ["--kömək"])
        self.assertEqual(kod, 0)
        h = "\n".join(s)
        for parça in ("hesabla 1.0.0", "İSTİFADƏ:",
                      "hesabla [SEÇİMLƏR] <əməliyyat> <ədədlər>...",
                      "-ə, --ətraflı", "-f, --format <FORMAT>",
                      "[standart: mətn]", "-v, --versiya"):
            self.assertIn(parça, h)

    def test_versiya(self):
        s, kod = proqram(self.KOD, ["-v"])
        self.assertEqual((s, kod), (["hesabla 1.0.0"], 0))

    def test_səhv_arqument_kod_3(self):
        """§ 13.16: 3 — yanlış əmr sətri istifadəsi."""
        for arq in (["--naməlum"], [], ["topla"], ["topla", "1", "-f"],
                    ["topla", "1", "--ətraflı=x"]):
            s, kod = proqram(self.KOD, arq)
            self.assertEqual((s, kod), ([], 3), arq)

    def test_sistem_arqumentləri_proqramındır(self):
        s, _ = proqram("gətir sistem\nfunksiya əsas()\n"
                       "    yaz(sistem.arqumentlər())\nson", ["a", "b"])
        self.assertEqual(s, ['["a", "b"]'])


class ZəncirVəEtiketSınağı(unittest.TestCase):
    """Dil: aparıcı nöqtə ilə zəncir, açar söz adlı arqument etiketi."""

    def test_aparıcı_nöqtəli_zəncir(self):
        self.assertEqual(çıxış("""dəyişən s = [3, 1, 2]
    // şərh sətri zənciri qırmır
    .çevir((x) => x * 10)

    .filtr((x) => x > 10)
yaz(s)
dəyişən t = boş
yaz(t
    ?.uzunluq())"""), ["[30, 20]", "boş"])

    def test_diapazon_və_yayma_zəncir_deyil(self):
        _, x = ayır("dəyişən a = 1\n..5")
        self.assertFalse(x.uğurludur())

    def test_açar_söz_etiket(self):
        s = çıxış(BAŞLIQ + 'yaz(konsol.rəng("a", ön: "qırmızı"))\n'
                  'yaz(konsol.təsdiqlə("?", standart: yanlış))', [""])
        self.assertEqual(s[-1], "yanlış")

    def test_çoxsözlü_açar_söz_etiket_deyil(self):
        _, x = ayır('f(və ya: 1)')
        self.assertFalse(x.uğurludur())


if __name__ == "__main__":
    unittest.main(verbosity=2)
