"""
Tip yoxlayıcı sınaqları.

İki qrup var:
  1. YANLIŞ XƏBƏRDARLIQ YOXDUR — düzgün kodda heç nə bildirilməməlidir.
     Bu, yoxlayıcının ən vacib keyfiyyətidir.
  2. Hər xəta kodu tutulur.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import tipler as T                        # noqa: E402
from alqor.lekser import Lekser                      # noqa: E402
from alqor.menbe import Mənbə                        # noqa: E402
from alqor.parser import Parser                      # noqa: E402
from alqor.tipyoxlayici import TipYoxlayıcı          # noqa: E402
from alqor.xeta import XətaToplayıcı                 # noqa: E402


def yoxla(kod: str, rejim: str = "normal"):
    """Kodu yoxlayır → (kodlar, yoxlayıcı). Ayırma xətası varsa qaldırır."""
    x = XətaToplayıcı()
    s = Mənbə.mətndən(kod, "sınaq.alq", x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise AssertionError("ayırma xətası:\n" + x.hesabat(False))

    t = XətaToplayıcı()
    y = TipYoxlayıcı(t, rejim)
    y.yoxla(ağac)
    return [d.kod for d in t.siyahı], t


def kodlar(kod: str, rejim: str = "normal") -> list[str]:
    return yoxla(kod, rejim)[0]


def təmizdir(kod: str, rejim: str = "normal") -> bool:
    k, t = yoxla(kod, rejim)
    if k:
        raise AssertionError(
            "gözlənilməyən diaqnostika:\n" + t.hesabat(False))
    return True


def tipi(ifadə: str) -> str:
    """İfadənin çıxarılmış tipini mətn kimi qaytarır."""
    from alqor import aac as A
    x = XətaToplayıcı()
    kod = f"dəyişən _nəticə = {ifadə}"
    s = Mənbə.mətndən(kod, "sınaq.alq", x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise AssertionError(x.hesabat(False))
    y = TipYoxlayıcı(XətaToplayıcı())
    y.yoxla(ağac)
    b = y.qlobal.tap("_nəticə")
    return b.tip.mətn() if b else "?"


# ═══════════════════════════════════════════════════════════════════════
#  1. Yanlış xəbərdarlıq olmamalıdır
# ═══════════════════════════════════════════════════════════════════════

class YanlışXəbərdarlıqYoxdur(unittest.TestCase):
    """Düzgün kod tamamilə təmiz keçməlidir."""

    def test_sadə_proqram(self):
        self.assertTrue(təmizdir(
            'dəyişən ad = "Aysel"\n'
            "dəyişən yaş = 24\n"
            'yaz("Salam, {ad}! {yaş + 1} olacaqsan.")'))

    def test_funksiya(self):
        self.assertTrue(təmizdir(
            "funksiya topla(a: tam, b: tam) -> tam\n"
            "    qaytar a + b\n"
            "son\n"
            "yaz(topla(3, 4))"))

    def test_son_ifadə_avtomatik_qaytarılır(self):
        self.assertTrue(təmizdir(
            "funksiya ikiqat(x: tam) -> tam\n"
            "    x * 2\n"
            "son\n"
            "yaz(ikiqat(5))"))

    def test_dövrlər(self):
        self.assertTrue(təmizdir(
            "hər i üçün 1..5 içində\n"
            '    yaz("{i}")\n'
            "son\n"
            'hər x üçün ["a", "b"] içində\n'
            "    yaz(x.böyüyə())\n"
            "son\n"
            'hər a, d üçün {"x": 1} içində\n'
            '    yaz("{a}={d}")\n'
            "son"))

    def test_siniflər(self):
        self.assertTrue(təmizdir(
            "sinif İnsan\n"
            "    qurucu(açıq xassə ad: mətn, açıq xassə yaş: tam)\n"
            "    metod təqdim()\n"
            '        yaz("{özü.ad}, {özü.yaş}")\n'
            "    son\n"
            "son\n"
            'yeni İnsan("Aysel", 24).təqdim()'))

    def test_miras_və_üst(self):
        self.assertTrue(təmizdir(
            "mücərrəd sinif Fiqur\n"
            "    qurucu(açıq xassə ad: mətn)\n"
            "    mücərrəd metod sahə() -> onluq\n"
            "son\n"
            "sinif Dairə miras Fiqur\n"
            "    qurucu(açıq xassə r: onluq)\n"
            '        üst("Dairə")\n'
            "    son\n"
            "    əvəz et metod sahə() -> onluq\n"
            "        qaytar 3.14 * özü.r * özü.r\n"
            "    son\n"
            "son\n"
            "yaz(yeni Dairə(2.0).sahə())"))

    def test_ixtiyari_yoxlanmış(self):
        self.assertTrue(təmizdir(
            "funksiya tap(x: tam) -> mətn?\n"
            "    əgər x > 0 onda\n"
            '        qaytar "var"\n'
            "    son\n"
            "    qaytar boş\n"
            "son\n"
            "dəyişən a = tap(5)\n"
            "əgər a boş deyil onda\n"
            "    yaz(a.böyüyə())\n"
            "son\n"
            'yaz(a ?? "standart")\n'
            "yaz(a?.uzunluq())"))

    def test_varsa_daralması(self):
        self.assertTrue(təmizdir(
            "funksiya tap() -> mətn?\n"
            '    qaytar "a"\n'
            "son\n"
            "varsa d = tap() onda\n"
            "    yaz(d.böyüyə())\n"
            "son"))

    def test_tipidir_daralması(self):
        self.assertTrue(təmizdir(
            "funksiya f(x: tam | mətn)\n"
            "    əgər x tipidir mətn onda\n"
            "        yaz(x.böyüyə())\n"
            "    son\n"
            "son\n"
            'f("a")'))

    def test_kolleksiya_metodları(self):
        self.assertTrue(təmizdir(
            "dəyişən s = [3, 1, 2]\n"
            "s.əlavə(4)\n"
            "yaz(s.sıralanmış())\n"
            "yaz(s.çevir((x) => x * 2))\n"
            "yaz(s.filtr((x) => x > 1))\n"
            "yaz(s.cəm())\n"
            "yaz(uzunluq(s))\n"
            'dəyişən l = {"a": 1}\n'
            'yaz(l.al("a", 0) + 1)\n'
            "yaz(l.açarlar())"))

    def test_lüğət_al_standartla(self):
        """`al(açar, standart)` ixtiyari QAYTARMAMALIDIR."""
        self.assertTrue(təmizdir(
            'dəyişən l = {"a": 1}\n'
            'dəyişən n: tam = l.al("a", 0)\n'
            "yaz(n + 1)"))

    def test_modullar(self):
        self.assertTrue(təmizdir(
            "gətir riyaziyyat\n"
            "gətir riyaziyyat.{kök}\n"
            "yaz(riyaziyyat.Pİ)\n"
            "yaz(kök(16.0))\n"
            "gətir vaxt kimi v\n"
            "yaz(v.indi())"))

    def test_xətalar(self):
        self.assertTrue(təmizdir(
            "cəhd et\n"
            '    at ArqumentXətası("pis")\n'
            "tut (x: ArqumentXətası)\n"
            "    yaz(x.mesaj)\n"
            "nəhayət\n"
            '    yaz("bitdi")\n'
            "son"))

    def test_sadalama(self):
        self.assertTrue(təmizdir(
            "sadalama Rəng\n"
            "    QIRMIZI\n"
            "    YAŞIL\n"
            "son\n"
            "dəyişən r = Rəng.QIRMIZI\n"
            "seç r\n"
            "    hal QIRMIZI → yaz(1)\n"
            "    hal YAŞIL → yaz(2)\n"
            "son"))

    def test_generator(self):
        self.assertTrue(təmizdir(
            "generator funksiya saylar(n: tam) -> tam\n"
            "    hər i üçün 1..n içində\n"
            "        ver i\n"
            "    son\n"
            "son\n"
            "yaz(saylar(3).siyahıyaÇevir())\n"
            "hər x üçün saylar(3) içində\n"
            "    yaz(x + 1)\n"
            "son"))

    def test_asinxron(self):
        self.assertTrue(təmizdir(
            "gətir vaxt\n"
            "asinxron funksiya al(ms: tam) -> mətn\n"
            "    vaxt.gözlə(ms)\n"
            '    qaytar "bitdi"\n'
            "son\n"
            "asinxron funksiya əsas()\n"
            "    dəyişən a = gözlə al(1)\n"
            "    yaz(a.böyüyə())\n"
            "son"))

    def test_jsx(self):
        self.assertTrue(təmizdir(
            "komponent Düymə\n"
            '    xassə mətn: mətn = "Bas"\n'
            "    göstər()\n"
            "        qaytar <button>{özü.mətn}</button>\n"
            "    son\n"
            "son\n"
            'yaz(<Düymə mətn="Göndər" />)'))

    def test_dağıtma(self):
        self.assertTrue(təmizdir(
            "dəyişən a, b = (1, 2)\n"
            "yaz(a + b)\n"
            "dəyişən ilk, ...qalan = [1, 2, 3]\n"
            "yaz(ilk + uzunluq(qalan))"))

    def test_qurmalar(self):
        self.assertTrue(təmizdir(
            "dəyişən k = [x * x üçün x içində 1..4]\n"
            "yaz(k.cəm())\n"
            "dəyişən l = {x: x * 2 üçün x içində 1..3}\n"
            "yaz(l.açarlar())"))

    def test_bütün_nümunələr(self):
        """Həqiqi nümunə proqramlarda yanlış xəbərdarlıq olmamalıdır."""
        qovluq = Path(__file__).parent.parent.parent / "numuneler"
        if not qovluq.exists():
            self.skipTest("nümunələr yoxdur")

        # `veb` və `pəncərə` modulları hələ yoxdur — ALQ-M001 gözləniləndir
        İCAZƏLİ = {"ALQ-M001"}
        for f in sorted(qovluq.glob("*.alq")):
            with self.subTest(fayl=f.name):
                x = XətaToplayıcı()
                s = Mənbə.fayldan(f, x)
                self.assertIsNotNone(s)
                ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
                self.assertTrue(x.uğurludur(), x.hesabat(False))
                t = XətaToplayıcı()
                TipYoxlayıcı(t).yoxla(ağac)
                qalan = [d for d in t.siyahı if d.kod not in İCAZƏLİ]
                self.assertEqual(
                    qalan, [],
                    f"{f.name} yanlış diaqnostika verdi:\n"
                    + t.hesabat(False))


# ═══════════════════════════════════════════════════════════════════════
#  2. Tip çıxarılması
# ═══════════════════════════════════════════════════════════════════════

class TipÇıxarılması(unittest.TestCase):
    def test_literallar(self):
        hallar = {
            "42": "tam", "3.14": "onluq", '"a"': "mətn",
            "doğru": "məntiq", "boş": "heç", "`ə`": "simvol",
        }
        for ifadə, gözlənilən in hallar.items():
            with self.subTest(ifadə=ifadə):
                self.assertEqual(tipi(ifadə), gözlənilən)

    def test_kolleksiyalar(self):
        self.assertEqual(tipi("[1, 2, 3]"), "siyahı[tam]")
        self.assertEqual(tipi('["a"]'), "siyahı[mətn]")
        self.assertEqual(tipi('{"a": 1}'), "lüğət[mətn, tam]")
        self.assertEqual(tipi("dəst(1, 2)"), "dəst")
        self.assertEqual(tipi('(1, "a")'), "kortej[tam, mətn]")
        self.assertEqual(tipi("1..5"), "diapazon")

    def test_qarışıq_siyahı(self):
        self.assertEqual(tipi('[1, "a"]'), "siyahı[tam | mətn]")

    def test_operatorlar(self):
        self.assertEqual(tipi("1 + 2"), "tam")
        self.assertEqual(tipi("1 + 2.0"), "onluq")
        self.assertEqual(tipi("7 / 2"), "onluq")
        self.assertEqual(tipi("7 ~/ 2"), "tam")
        self.assertEqual(tipi("1 < 2"), "məntiq")
        self.assertEqual(tipi("1 <=> 2"), "tam")
        self.assertEqual(tipi('"a" + "b"'), "mətn")
        self.assertEqual(tipi('"a" * 3'), "mətn")

    def test_metod_nəticəsi(self):
        self.assertEqual(tipi('"a".böyüyə()'), "mətn")
        self.assertEqual(tipi('"a".uzunluq()'), "tam")
        self.assertEqual(tipi('"a,b".böl(",")'), "siyahı[mətn]")
        self.assertEqual(tipi("[1].sıralanmış()"), "siyahı[tam]")
        self.assertEqual(tipi("[1].ilk()"), "tam?")

    def test_ixtiyari(self):
        self.assertEqual(tipi('"abc".tap("b")'), "tam?")
        self.assertEqual(tipi('"abc".tap("b") ?? 0'), "tam")

    def test_jsx(self):
        self.assertEqual(tipi("<div />"), "element")

    def test_şərt_ifadəsi(self):
        self.assertEqual(tipi("əgər doğru onda 1 yoxsa 2 son"), "tam")
        self.assertEqual(
            tipi('əgər doğru onda 1 yoxsa "a" son'), "tam | mətn")


# ═══════════════════════════════════════════════════════════════════════
#  3. Xətaların tutulması
# ═══════════════════════════════════════════════════════════════════════

class XətalarTutulur(unittest.TestCase):
    def _tutulur(self, kod: str, gözlənilən: str,
                 rejim: str = "normal") -> None:
        k = kodlar(kod, rejim)
        self.assertIn(gözlənilən, k, f"kod: {kod!r} → {k}")

    def test_T001_tip_uyğunsuzluğu(self):
        self._tutulur('dəyişən a: tam = "salam"', "ALQ-T001")

    def test_T003_arqument_sayı(self):
        self._tutulur(
            "funksiya f(a: tam, b: tam) -> tam\n qaytar a + b\nson\n"
            "yaz(f(1))", "ALQ-T003")

    def test_T003_çox_arqument(self):
        self._tutulur(
            "funksiya f(a: tam) -> tam\n qaytar a\nson\n"
            "yaz(f(1, 2, 3))", "ALQ-T003")

    def test_T004_arqument_tipi(self):
        self._tutulur(
            "funksiya f(a: tam) -> tam\n qaytar a\nson\n"
            'yaz(f("x"))', "ALQ-T004")

    def test_T005_qaytarma_tipi(self):
        self._tutulur(
            'funksiya f() -> tam\n qaytar "mətn"\nson', "ALQ-T005")

    def test_T006_naməlum_üzv(self):
        self._tutulur('yaz("a".yoxdurBelə())', "ALQ-T006")

    def test_T006_ascii_üzv_təklifi(self):
        k, t = yoxla("yaz([1, 2].cem())")
        self.assertIn("ALQ-T006", k)
        hesabat = t.hesabat(False)
        self.assertIn("cəm", hesabat)
        self.assertIn("AÇAR SÖZLƏRƏ", hesabat)

    def test_T007_şərt_məntiq_olmalıdır(self):
        self._tutulur("əgər 1 onda\n yaz(1)\nson", "ALQ-T007")
        self._tutulur("dəyişən s = [1]\nəgər s onda\n yaz(1)\nson",
                      "ALQ-T007")
        self._tutulur('əgər "a" onda\n yaz(1)\nson', "ALQ-T007")

    def test_T008_operator(self):
        self._tutulur('yaz("yaş: " + 24)', "ALQ-T008")
        self._tutulur('yaz([1] - [2])', "ALQ-T008")
        self._tutulur('yaz("a" < 1)', "ALQ-T008")

    def test_T009_indeks(self):
        self._tutulur('dəyişən s = [1]\nyaz(s["a"])', "ALQ-T009")
        self._tutulur("yaz(5[0])", "ALQ-T009")

    def test_T009_iterasiya(self):
        self._tutulur("hər x üçün 5 içində\n yaz(x)\nson", "ALQ-T009")

    def test_T012_boş_mənimsətmə(self):
        self._tutulur("dəyişən a: mətn = boş", "ALQ-T012")

    def test_T013_ixtiyari_yoxlanmır(self):
        self._tutulur(
            "dəyişən a: mətn? = boş\nyaz(a.uzunluq())", "ALQ-T013")

    def test_T014_çevrilmə(self):
        self._tutulur("dəyişən s = [1]\nyaz(s kimi tam)", "ALQ-T014")

    def test_T020_sabitə_mənimsətmə(self):
        self._tutulur("sabit A = 5\nA = 6", "ALQ-T020")

    def test_T022_təyin_edilməmiş(self):
        self._tutulur("yaz(x)", "ALQ-T022")

    def test_T022_oxşar_ad_təklifi(self):
        k, t = yoxla("dəyişən sayğac = 1\nyaz(sayğ)")
        self.assertIn("ALQ-T022", k)
        self.assertIn("sayğac", t.hesabat(False))

    def test_T023_təkrar_elan(self):
        self._tutulur("dəyişən a = 1\ndəyişən a = 2\nyaz(a)", "ALQ-T023")

    def test_T024_istifadəsiz_dəyişən(self):
        self._tutulur(
            "funksiya f()\n dəyişən a = 5\nson\nf()", "ALQ-T024")

    def test_T024_alt_xətt_istisnadır(self):
        self.assertTrue(təmizdir(
            "funksiya f()\n dəyişən _a = 5\nson\nf()"))

    def test_T025_çatılmayan_kod(self):
        self._tutulur(
            "funksiya f() -> tam\n qaytar 1\n yaz(2)\nson\nyaz(f())",
            "ALQ-T025")

    def test_T031_seç_tamlığı(self):
        self._tutulur(
            "sadalama R\n QIRMIZI\n YAŞIL\nson\n"
            "seç R.QIRMIZI\n hal QIRMIZI → yaz(1)\nson", "ALQ-T031")

    def test_T040_qaytar_yoxdur(self):
        self._tutulur("funksiya f() -> tam\n yaz(1)\nson", "ALQ-T040")

    def test_T040_son_ifadə_tipi(self):
        self._tutulur('funksiya f() -> tam\n "mətn"\nson', "ALQ-T040")

    def test_T052_mücərrəd(self):
        self._tutulur(
            "mücərrəd sinif F\n mücərrəd metod g() -> tam\nson\n"
            "dəyişən f = yeni F()", "ALQ-T052")

    def test_T053_komponentdə_göstər_yoxdur(self):
        self._tutulur("sinif X\nson\nyaz(<X />)", "ALQ-T053")

    def test_P013_gözlə_sinxronda(self):
        self._tutulur("funksiya f()\n gözlə 5\nson\nf()", "ALQ-P013")

    def test_P008_dayan_dövrdən_kənarda(self):
        self._tutulur("dayan", "ALQ-P008")

    def test_M002_modulda_üzv_yoxdur(self):
        self._tutulur("gətir riyaziyyat\nyaz(riyaziyyat.yoxdurBelə())",
                      "ALQ-M002")

    def test_M002_seçmə_idxalda(self):
        self._tutulur("gətir riyaziyyat.{yoxdurBelə}", "ALQ-M002")

    def test_T015_lazımsız_boş_yoxlaması(self):
        self._tutulur("dəyişən a = 5\nyaz(a boşdur)", "ALQ-T015")

    def test_T002_naməlum_tip(self):
        self._tutulur("dəyişən a: YoxdurBeləTip = 5", "ALQ-T002")


# ═══════════════════════════════════════════════════════════════════════
#  4. Axın əsaslı daralma
# ═══════════════════════════════════════════════════════════════════════

class AxınDaralması(unittest.TestCase):
    İXTİYARİ = ("funksiya tap() -> mətn?\n"
                '    qaytar "a"\n'
                "son\n")

    def test_boş_deyil(self):
        self.assertTrue(təmizdir(
            self.İXTİYARİ + "dəyişən a = tap()\n"
            "əgər a boş deyil onda\n    yaz(a.böyüyə())\nson"))

    def test_boşdursa_qaytar(self):
        self.assertTrue(təmizdir(
            self.İXTİYARİ +
            "funksiya f()\n"
            "    dəyişən a = tap()\n"
            "    əgər a boşdur onda\n        qaytar\n    son\n"
            "    yaz(a.böyüyə())\n"
            "son\nf()"))

    def test_bərabərdir_boş(self):
        self.assertTrue(təmizdir(
            self.İXTİYARİ + "dəyişən a = tap()\n"
            "əgər a != boş onda\n    yaz(a.böyüyə())\nson"))

    def test_deyil_inversiyası(self):
        self.assertTrue(təmizdir(
            self.İXTİYARİ + "dəyişən a = tap()\n"
            "əgər deyil (a boşdur) onda\n    yaz(a.böyüyə())\nson"))

    def test_və_ilə_iki_daralma(self):
        self.assertTrue(təmizdir(
            self.İXTİYARİ +
            "dəyişən a = tap()\ndəyişən b = tap()\n"
            "əgər a boş deyil və b boş deyil onda\n"
            "    yaz(a.böyüyə() + b.böyüyə())\n"
            "son"))

    def test_daralma_olmadan_xəta(self):
        """Daralma olmadan həmin kod ALQ-T013 verməlidir."""
        self.assertIn("ALQ-T013", kodlar(
            self.İXTİYARİ + "dəyişən a = tap()\nyaz(a.böyüyə())"))

    def test_yoxdursa_daralması(self):
        self.assertTrue(təmizdir(
            self.İXTİYARİ +
            "funksiya f()\n"
            "    yoxdursa a = tap() onda\n        qaytar\n    son\n"
            "    yaz(a.böyüyə())\n"
            "son\nf()"))

    def test_tipidir_birləşmədə(self):
        self.assertTrue(təmizdir(
            "funksiya f(x: tam | mətn)\n"
            "    əgər x tipidir mətn onda\n"
            "        yaz(x.uzunluq())\n"
            "    yoxsa əgər x tipidir tam onda\n"
            "        yaz(x + 1)\n"
            "    son\n"
            "son\n"
            "f(5)"))


# ═══════════════════════════════════════════════════════════════════════
#  5. Sərtlik rejimləri
# ═══════════════════════════════════════════════════════════════════════

class Rejimlər(unittest.TestCase):
    PİS = 'dəyişən a: tam = "mətn"'

    def test_sərbəst_rejim_yumşaqdır(self):
        self.assertNotIn("ALQ-T001", kodlar(self.PİS, "sərbəst"))

    def test_normal_rejim_tutur(self):
        self.assertIn("ALQ-T001", kodlar(self.PİS, "normal"))

    def test_sərt_rejim_parametr_tipi_tələb_edir(self):
        self.assertIn("ALQ-T080", kodlar(
            "funksiya f(a)\n yaz(a)\nson\nf(1)", "sərt"))

    def test_normal_rejim_parametr_tipini_tələb_etmir(self):
        self.assertNotIn("ALQ-T080", kodlar(
            "funksiya f(a)\n yaz(a)\nson\nf(1)", "normal"))

    def test_sərbəst_istifadəsizi_bildirmir(self):
        self.assertNotIn("ALQ-T024", kodlar(
            "funksiya f()\n dəyişən a = 5\nson\nf()", "sərbəst"))

    def test_istənilən_tipi_yoxlamanı_söndürür(self):
        self.assertTrue(təmizdir(
            "funksiya f(x: istənilən)\n"
            "    yaz(x.nəOlsa())\n"
            "    yaz(x + 1)\n"
            "son\n"
            "f(5)"))


# ═══════════════════════════════════════════════════════════════════════
#  6. Tip əməliyyatları (tipler.py)
# ═══════════════════════════════════════════════════════════════════════

class TipƏməliyyatları(unittest.TestCase):
    def test_uyğunluq(self):
        self.assertTrue(T.uyğundur(T.TAM, T.TAM))
        self.assertTrue(T.uyğundur(T.TAM, T.ONLUQ))       # genişlənmə
        self.assertFalse(T.uyğundur(T.ONLUQ, T.TAM))
        self.assertTrue(T.uyğundur(T.SİMVOL, T.MƏTN))
        self.assertFalse(T.uyğundur(T.MƏTN, T.TAM))

    def test_istənilən_həmişə_uyğundur(self):
        self.assertTrue(T.uyğundur(T.İSTƏNİLƏN, T.TAM))
        self.assertTrue(T.uyğundur(T.MƏTN, T.İSTƏNİLƏN))

    def test_ixtiyari(self):
        ixt = T.ixtiyari(T.MƏTN)
        self.assertTrue(T.ixtiyaridir(ixt))
        self.assertTrue(T.uyğundur(T.MƏTN, ixt))
        self.assertTrue(T.uyğundur(T.HEÇ, ixt))
        self.assertFalse(T.uyğundur(ixt, T.MƏTN))
        self.assertEqual(T.açılmış(ixt), T.MƏTN)
        self.assertEqual(ixt.mətn(), "mətn?")

    def test_kolleksiya_kovariantlığı(self):
        self.assertTrue(T.uyğundur(T.Siyahı(T.TAM), T.Siyahı(T.ONLUQ)))
        self.assertFalse(T.uyğundur(T.Siyahı(T.MƏTN), T.Siyahı(T.TAM)))

    def test_birləşmə(self):
        b = T.birləşmə(T.TAM, T.MƏTN, T.TAM)
        self.assertEqual(b.mətn(), "tam | mətn")
        self.assertTrue(T.uyğundur(T.TAM, b))
        self.assertFalse(T.uyğundur(T.MƏNTİQ, b))

    def test_birləşdirmə(self):
        self.assertEqual(T.birləşdir(T.TAM, T.TAM), T.TAM)
        self.assertEqual(T.birləşdir(T.TAM, T.ONLUQ), T.ONLUQ)
        self.assertEqual(
            T.birləşdir(T.TAM, T.MƏTN).mətn(), "tam | mətn")

    def test_iterasiya_elementi(self):
        self.assertEqual(T.iterasiya_elementi(T.Siyahı(T.TAM)), T.TAM)
        self.assertEqual(
            T.iterasiya_elementi(T.Lüğət(T.MƏTN, T.TAM)), T.MƏTN)
        self.assertEqual(T.iterasiya_elementi(T.MƏTN), T.SİMVOL)
        self.assertEqual(T.iterasiya_elementi(T.DİAPAZON), T.TAM)

    def test_sinif_mirası(self):
        baza = T.SinifTipi("Heyvan")
        törəmə = T.SinifTipi("İt", baza=baza)
        self.assertTrue(T.uyğundur(törəmə, baza))
        self.assertFalse(T.uyğundur(baza, törəmə))

    def test_interfeys_uyğunluğu(self):
        s = T.SinifTipi("Sənəd", interfeyslər=("Çapedilən",))
        i = T.SinifTipi("Çapedilən", quruluş="interfeys")
        self.assertTrue(T.uyğundur(s, i))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class Generiklər(unittest.TestCase):
    TƏRİF = """funksiya ilk[T](s: siyahı[T]) -> T?
    əgər s.uzunluq() == 0 onda
        qaytar boş
    son
    qaytar s[0]
son
funksiya eyni[T](a: T, b: T) -> T
    qaytar a ?? b
son
funksiya xəritələ[T, Nəticə](s: siyahı[T], f: funksiyaTipi(T) -> Nəticə) -> siyahı[Nəticə]
    dəyişən n: siyahı[Nəticə] = []
    hər x üçün s içində
        n.əlavə(f(x))
    son
    qaytar n
son
"""

    def test_nəticə_tipi_çıxarılır(self):
        təmizdir(self.TƏRİF + "dəyişən a: tam = ilk([1, 2]) ?? 0\nyaz(a)\n")
        self.assertIn("ALQ-T001", kodlar(
            self.TƏRİF + 'dəyişən a: mətn = ilk([1, 2]) ?? ""\nyaz(a)\n'))

    def test_ziddiyyət(self):
        self.assertIn("ALQ-T004", kodlar(self.TƏRİF + 'eyni(1, "x")\n'))
        təmizdir(self.TƏRİF + "yaz(eyni(1, 2.5))\n")       # tam → onluq

    def test_lambda_kontekstdən_tip_alır(self):
        təmizdir(self.TƏRİF +
                 "dəyişən m: siyahı[tam] = xəritələ([1, 2], (x) => x * 2)\n"
                 "yaz(m)\n")
        self.assertIn("ALQ-T006", kodlar(
            self.TƏRİF + "yaz(xəritələ([1, 2], (x) => x.uzunluq()))\n"))
        self.assertIn("ALQ-T001", kodlar(
            self.TƏRİF + "dəyişən m: siyahı[mətn] = "
            "xəritələ([1], (x) => x + 1)\nyaz(m)\n"))

    def test_uzun_generik_adı(self):
        təmizdir("funksiya bir[Element](e: Element) -> Element\n"
                 "    qaytar e\nson\ndəyişən x: tam = bir(5)\nyaz(x)\n")

    def test_funksiya_tipi_annotasiyası(self):
        self.assertEqual(tipi("(a: tam) => a"),
                         "funksiyaTipi(tam) -> tam")
        təmizdir("dəyişən f: funksiyaTipi(tam) -> tam = (a) => a\n"
                 "yaz(f(1))\n")

    def test_kortej_sabit_indeks(self):
        self.assertEqual(tipi('(1, "x")[1]'), "mətn")
        self.assertIn("ALQ-T009", kodlar('dəyişən k = (1, 2)\nyaz(k[5])\n'))


class ModulTipləriAnnotasiyada(unittest.TestCase):
    def test_qurucu_adı_tip_kimi(self):
        təmizdir("gətir pəncərə\n"
                 "funksiya yarat() -> pəncərə.Pəncərə\n"
                 '    qaytar yeni pəncərə.Pəncərə("A")\nson\n'
                 "funksiya göstər(p: pəncərə.Pəncərə)\n    p.göstər()\nson\n"
                 "göstər(yarat())\n")
        self.assertIn("ALQ-T006", kodlar(
            "gətir pəncərə\nfunksiya f(p: pəncərə.Pəncərə)\n"
            "    p.yoxdur()\nson\n"))

    def test_əlavə_modul(self):
        təmizdir('gətir http\ndəyişən s: http.Sorğu = '
                 'yeni http.Sorğu("AL", "https://a.az")\nyaz(s.url())\n')

    def test_naməlum_modul_tipi(self):
        k = kodlar("gətir pəncərə\ndəyişən x: pəncərə.Yox = 1\nyaz(x)\n")
        self.assertEqual(k.count("ALQ-T002"), 1)     # təkrar yoxdur


class SərtRejimƏhatəsi(unittest.TestCase):
    """İcrada olan hər üzvün tip imzası var — `sərt` rejim yanlış
    "belə üzv yoxdur" xətası verməsin. Yeni funksiya əlavə edəndə
    imzası da yazılmalıdır, yoxsa bu sınaq uğursuz olur."""

    def test_modul_üzvləri(self):
        from alqor.deyerler import Modul
        from alqor.icraci import İcraçı
        from alqor.kitabxana import _modulları_qur
        from alqor import tipler as T, tipyoxlayici as TY
        tiplər = TY._modullar()
        çatmır = []

        def gəz(m, t, ön):
            for a, d in m.üzvlər.items():
                if a not in t.üzvlər:
                    çatmır.append(ön + a)
                elif isinstance(d, Modul) and isinstance(t.üzvlər[a],
                                                         T.ModulTipi):
                    gəz(d, t.üzvlər[a], f"{ön}{a}.")
        for ad, m in _modulları_qur(İcraçı()).items():
            self.assertIn(ad, tiplər)
            gəz(m, tiplər[ad], f"{ad}.")
        self.assertEqual(çatmır, [])

    def test_daxili_tip_metodları(self):
        from alqor import kitabxana as K, tipler as T
        from alqor.xeta import XətaToplayıcı
        y = TipYoxlayıcı(XətaToplayıcı())
        for py, tip in ((str, T.MƏTN), (list, T.Siyahı(T.TAM)),
                        (dict, T.Lüğət(T.MƏTN, T.TAM)),
                        (set, T.Dəst(T.TAM)), (int, T.TAM),
                        (float, T.ONLUQ), (bytes, T.BAYT)):
            icra = set(K._CƏDVƏLLƏR.get(py) or {})
            self.assertEqual(icra - set(y._metod_cədvəli(tip) or {}),
                             set(), py.__name__)

    def test_əlavə_modul_obyektləri(self):
        from alqor import modullar as M
        cəd = M._obyekt_cədvəli()
        for ad in M.adlar():
            for v in vars(M._py(ad)).values():
                if isinstance(v, type) and hasattr(v, "ALQOR_TİP_ADI") \
                        and hasattr(v, "ALQOR_METODLARI"):
                    self.assertIn(v.ALQOR_TİP_ADI, cəd, ad)
                    self.assertEqual(set(v.ALQOR_METODLARI) -
                                     set(cəd[v.ALQOR_TİP_ADI]), set(),
                                     v.ALQOR_TİP_ADI)

    def test_nümunələr_sərt_rejimdə_təmizdir(self):
        from pathlib import Path
        kök = Path(__file__).resolve().parents[2] / "numuneler"
        for f in sorted(kök.rglob("*.alq")):
            with self.subTest(fayl=f.name):
                k, t = yoxla(f.read_text(encoding="utf-8"), "sərt")
                self.assertEqual([x for x in t.xətalar], [],
                                 t.hesabat(False))
