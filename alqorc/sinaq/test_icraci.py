"""Parser və interpretator sınaqları."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import aac as A                         # noqa: E402
from alqor.deyerler import AlqorXəta               # noqa: E402
from alqor.icraci import İcraçı                    # noqa: E402
from alqor.lekser import Lekser                    # noqa: E402
from alqor.menbe import Mənbə                      # noqa: E402
from alqor.parser import Parser, ayır              # noqa: E402
from alqor.xeta import XətaToplayıcı               # noqa: E402


def işlət(kod: str, giriş: list[str] | None = None):
    """Kodu icra edib (çıxış sətirləri, xəta) qaytarır."""
    x = XətaToplayıcı()
    s = Mənbə.mətndən(kod, "sınaq.alqor", x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise AssertionError("ayırma xətası:\n" + x.hesabat(False))

    sətirlər: list[str] = []
    növbə = list(giriş or [])
    icraçı = İcraçı(çıxış=sətirlər.append,
                    giriş=lambda: növbə.pop(0) if növbə else "")
    xəta = None
    try:
        icraçı.işlət(ağac)
    except AlqorXəta as e:
        xəta = e
    return sətirlər, xəta


def çıxış(kod: str, giriş: list[str] | None = None) -> list[str]:
    sətirlər, xəta = işlət(kod, giriş)
    if xəta is not None:
        raise AssertionError(f"gözlənilməyən xəta: {xəta}")
    return sətirlər


def xəta_tipi(kod: str) -> str:
    _, xəta = işlət(kod)
    if xəta is None:
        raise AssertionError("xəta gözlənilirdi, amma olmadı")
    return xəta.tip


# ═══════════════════════════════════════════════════════════════════════
#  Parser
# ═══════════════════════════════════════════════════════════════════════

class ParserQuruluşu(unittest.TestCase):
    def test_boş_proqram(self):
        ağac, x = ayır("")
        self.assertTrue(x.uğurludur())
        self.assertEqual(ağac.gövdə, [])

    def test_dəyişən_elanı(self):
        ağac, x = ayır("dəyişən a = 5")
        self.assertTrue(x.uğurludur())
        self.assertIsInstance(ağac.gövdə[0], A.DəyişənElanı)
        self.assertEqual(ağac.gövdə[0].növ, "dəyişən")

    def test_operator_prioriteti(self):
        ağac, _ = ayır("dəyişən a = 2 + 3 * 4")
        ifadə = ağac.gövdə[0].dəyərlər[0]
        self.assertEqual(ifadə.op, "+")
        self.assertEqual(ifadə.sağ.op, "*")

    def test_qüvvət_sağdan_assosiativdir(self):
        ağac, _ = ayır("dəyişən a = 2 ** 3 ** 2")
        ifadə = ağac.gövdə[0].dəyərlər[0]
        self.assertEqual(ifadə.op, "**")
        self.assertEqual(ifadə.sağ.op, "**")

    def test_son_çatışmır(self):
        _, x = ayır("əgər x > 5 onda\n    yaz(1)")
        self.assertFalse(x.uğurludur())
        self.assertEqual(x.xətalar[0].kod, "ALQ-P002")

    def test_onda_çatışmır(self):
        _, x = ayır("əgər x > 5\n    yaz(1)\nson")
        self.assertEqual(x.xətalar[0].kod, "ALQ-P004")

    def test_tip_adı_identifikator_ola_bilər(self):
        """`xassə mətn: mətn` — tip adları açar söz deyil."""
        ağac, x = ayır("""sinif Qeyd
    qurucu(açıq xassə mətn: mətn, açıq xassə tam: tam)
son""")
        self.assertTrue(x.uğurludur(), x.hesabat(False))

    def test_parametr_adı_tip_adı_ola_bilər(self):
        _, x = ayır("funksiya f(mətn: mətn) -> lüğət[mətn, tam]\n"
                    "    qaytar {}\nson")
        self.assertTrue(x.uğurludur(), x.hesabat(False))

    def test_çoxsətirli_anonim_funksiya_arqument_kimi(self):
        """Mötərizə içində bloklar üçün sətir sonu qorunmalıdır."""
        _, x = ayır("""funksiya əsas()
    s.qrup("/api", funksiya(q)
        q.al("/a", idarəedici)
        q.al("/b", idarəedici)
    son)
son""")
        self.assertTrue(x.uğurludur(), x.hesabat(False))

    def test_qısa_qurucu_sinfin_sonunu_udmur(self):
        ağac, x = ayır("""sinif A
    qurucu(açıq xassə a: tam)
son

dəyişən b = 5""")
        self.assertTrue(x.uğurludur(), x.hesabat(False))
        self.assertEqual(len(ağac.gövdə), 2)

    # ── Qısa qurucudan sonra üzvlər: girinti qaydası ──────────────────

    def test_qısa_qurucudan_sonra_göstər(self):
        """`göstər()` qurucunun gövdəsinə düşməməlidir."""
        self.assertEqual(çıxış("""komponent S
    qurucu(xassə k: mətn)
    göstər()
        qaytar <p>{özü.k}</p>
    son
son
yaz(yeni S("q").k)
yaz(<S k="z" />)"""), ["q", "<p>z</p>"])

    def test_qısa_qurucunun_öz_sonu(self):
        """Qurucu ilə eyni sütundakı `son` qurucunundur."""
        self.assertEqual(çıxış("""sinif A
    qurucu(xassə a: tam)
    son
    metod iki() -> tam
        qaytar özü.a * 2
    son
son
yaz(yeni A(4).iki())"""), ["8"])

    def test_qısa_qurucudan_sonra_vəziyyət(self):
        self.assertEqual(çıxış("""komponent S
    qurucu(xassə k: tam)
    vəziyyət n: tam = 3
    göstər()
        qaytar <p>{özü.k + özü.n}</p>
    son
son
yaz(<S k={2} />)"""), ["<p>5</p>"])

    def test_dərin_girintili_sətir_gövdədir(self):
        self.assertEqual(çıxış("""sinif A
    qurucu(xassə a: tam)
        yaz("qurulur {a}")
    son
son
yeni A(1)"""), ["qurulur 1"])

    # ── Ox funksiyasında mənimsətmə ───────────────────────────────────

    def test_lambda_gövdəsində_mənimsətmə(self):
        self.assertEqual(çıxış("""sinif A
    xassə n: tam = 0
son
dəyişən a = yeni A()
dəyişən artır = () => a.n += 2
dəyişən sıfırla = () => a.n = 0
dəyişən bir = () => a.n++
artır()
artır()
yaz(a.n)
sıfırla()
bir()
yaz(a.n)
yaz(artır())"""), ["4", "1", "boş"])

    def test_JSX_ifadəsində_artıq_token_xətadır(self):
        """Əvvəllər `{a 2}`-dən `2` səssizcə atılırdı."""
        _, x = ayır("dəyişən a = 1\nyaz(<p>{a 2}</p>)")
        self.assertFalse(x.uğurludur())
        _, x = ayır("yaz(<b klik={() => x}>{1 + 2}</b>)")
        self.assertTrue(x.uğurludur(), x.hesabat(False))

    def test_çox_xəta_bir_keçiddə(self):
        _, x = ayır("dəyişən a = $\ndəyişən b = $\ndəyişən c = $")
        self.assertGreaterEqual(len(x.xətalar), 3)


# ═══════════════════════════════════════════════════════════════════════
#  Əsas icra
# ═══════════════════════════════════════════════════════════════════════

class ƏsasİcraSınağı(unittest.TestCase):
    def test_salam_dünya(self):
        self.assertEqual(çıxış('yaz("Salam, dünya!")'),
                         ["Salam, dünya!"])

    def test_çoxlu_arqument(self):
        self.assertEqual(çıxış('yaz("a", 1, doğru, boş)'),
                         ["a 1 doğru boş"])

    def test_dəyişən(self):
        self.assertEqual(çıxış('dəyişən a = 5\nyaz(a)'), ["5"])

    def test_sabit_dəyişdirilə_bilməz(self):
        self.assertEqual(xəta_tipi("sabit A = 5\nA = 6"),
                         "ArqumentXətası")

    def test_təyin_edilməmiş_dəyişən(self):
        self.assertEqual(xəta_tipi("yaz(x)"), "ArqumentXətası")

    def test_interpolyasiya(self):
        self.assertEqual(
            çıxış('dəyişən ad = "Aysel"\ndəyişən y = 24\n'
                  'yaz("Salam, {ad}! {y + 1} olacaqsan.")'),
            ["Salam, Aysel! 25 olacaqsan."])

    def test_format_spesifikatoru(self):
        self.assertEqual(çıxış('yaz("{3.14159:.2}")'), ["3.14"])
        self.assertEqual(çıxış('yaz("{42:05}")'), ["00042"])
        self.assertEqual(çıxış('yaz("{255:x}")'), ["ff"])

    def test_giriş(self):
        self.assertEqual(çıxış('dəyişən a = oxu()\nyaz(a)', ["Aysel"]),
                         ["Aysel"])


class RiyaziSınağı(unittest.TestCase):
    def test_hesab(self):
        hallar = {
            "2 + 3": "5", "5 - 3": "2", "5 * 3": "15",
            "7 / 2": "3.5", "7 ~/ 2": "3", "7 % 3": "1",
            "2 ** 10": "1024", "-7 ~/ 2": "-3",
        }
        for ifadə, gözlənilən in hallar.items():
            with self.subTest(ifadə=ifadə):
                self.assertEqual(çıxış(f"yaz({ifadə})"), [gözlənilən])

    def test_bölmə_həmişə_onluqdur(self):
        self.assertEqual(çıxış("yaz(4 / 2)"), ["2.0"])

    def test_sıfıra_bölmə(self):
        self.assertEqual(xəta_tipi("yaz(1 ~/ 0)"), "BölməXətası")

    def test_mətn_ədədlə_toplanmır(self):
        self.assertEqual(xəta_tipi('yaz("a" + 1)'), "TipXətası")

    def test_mətn_birləşdirmə(self):
        self.assertEqual(çıxış('yaz("Sa" + "lam")'), ["Salam"])
        self.assertEqual(çıxış('yaz("-" * 5)'), ["-----"])

    def test_riyaziyyat_modulu(self):
        self.assertEqual(
            çıxış("gətir riyaziyyat\nyaz(riyaziyyat.kök(16))"), ["4.0"])
        self.assertEqual(
            çıxış("gətir riyaziyyat.{ƏBOB}\nyaz(ƏBOB(12, 18))"), ["6"])


class ŞərtSınağı(unittest.TestCase):
    KOD = """funksiya yoxla(y: tam) -> mətn
    əgər y >= 18 onda
        qaytar "yetkin"
    yoxsa əgər y >= 13 onda
        qaytar "yeniyetmə"
    yoxsa
        qaytar "uşaq"
    son
son
yaz(yoxla(25))
yaz(yoxla(15))
yaz(yoxla(8))"""

    def test_şərt_zənciri(self):
        self.assertEqual(çıxış(self.KOD),
                         ["yetkin", "yeniyetmə", "uşaq"])

    def test_əks_halda(self):
        self.assertEqual(
            çıxış('əgər yanlış onda\n yaz(1)\nəks halda\n yaz(2)\nson'),
            ["2"])

    def test_şərt_məntiq_olmalıdır(self):
        self.assertEqual(xəta_tipi("əgər 1 onda\n yaz(1)\nson"),
                         "TipXətası")

    def test_şərt_ifadəsi(self):
        self.assertEqual(
            çıxış('dəyişən a = əgər doğru onda "hə" yoxsa "yox" son\n'
                  'yaz(a)'), ["hə"])

    def test_məntiqi_operatorlar(self):
        self.assertEqual(çıxış("yaz(doğru və yanlış)"), ["yanlış"])
        self.assertEqual(çıxış("yaz(doğru və ya yanlış)"), ["doğru"])
        self.assertEqual(çıxış("yaz(deyil doğru)"), ["yanlış"])

    def test_qısa_qapanma(self):
        self.assertEqual(
            çıxış("funksiya f() -> məntiq\n yaz(\"çağırıldı\")\n"
                  " qaytar doğru\nson\n"
                  "əgər yanlış və f() onda\n keç\nson\nyaz(\"bitdi\")"),
            ["bitdi"])


class DövrSınağı(unittest.TestCase):
    def test_diapazon(self):
        self.assertEqual(çıxış("hər i üçün 1..3 içində\n yaz(i)\nson"),
                         ["1", "2", "3"])

    def test_xaric_diapazon(self):
        self.assertEqual(çıxış("hər i üçün 0..<3 içində\n yaz(i)\nson"),
                         ["0", "1", "2"])

    def test_tərs_diapazon(self):
        self.assertEqual(çıxış("hər i üçün 3..1 içində\n yaz(i)\nson"),
                         ["3", "2", "1"])

    def test_addım(self):
        self.assertEqual(
            çıxış("hər i üçün 1..10 addım 3 içində\n yaz(i)\nson"),
            ["1", "4", "7", "10"])

    def test_siyahı_üzərində(self):
        self.assertEqual(
            çıxış('hər x üçün ["a", "b"] içində\n yaz(x)\nson'),
            ["a", "b"])

    def test_indekslə(self):
        self.assertEqual(
            çıxış('hər i, x üçün ["a", "b"] içində\n yaz("{i}:{x}")\nson'),
            ["0:a", "1:b"])

    def test_lüğət_üzərində(self):
        self.assertEqual(
            çıxış('hər a, d üçün {"x": 1, "y": 2} içində\n'
                  ' yaz("{a}={d}")\nson'), ["x=1", "y=2"])

    def test_nə_qədər_ki(self):
        self.assertEqual(
            çıxış("dəyişən i = 1\nnə qədər ki i <= 3\n yaz(i)\n i += 1\nson"),
            ["1", "2", "3"])

    def test_təkrarla(self):
        self.assertEqual(çıxış('təkrarla 3 dəfə\n yaz("a")\nson'),
                         ["a", "a", "a"])

    def test_təkrarla_sayğacla(self):
        self.assertEqual(çıxış("təkrarla i, 3 dəfə\n yaz(i)\nson"),
                         ["1", "2", "3"])

    def test_dayan(self):
        self.assertEqual(
            çıxış("hər i üçün 1..10 içində\n əgər i > 2 onda\n"
                  " dayan\n son\n yaz(i)\nson"), ["1", "2"])

    def test_davam_et(self):
        self.assertEqual(
            çıxış("hər i üçün 1..5 içində\n əgər i % 2 == 0 onda\n"
                  " davam et\n son\n yaz(i)\nson"), ["1", "3", "5"])

    def test_etiketli_dövr(self):
        self.assertEqual(
            çıxış("xarici: hər i üçün 1..3 içində\n"
                  " hər j üçün 1..3 içində\n"
                  "  əgər j == 2 onda\n   dayan xarici\n  son\n"
                  '  yaz("{i}{j}")\n son\nson'), ["11"])

    def test_dövr_yoxsa(self):
        self.assertEqual(
            çıxış("hər x üçün 1..3 içində\n əgər x == 99 onda\n"
                  " dayan\n son\nyoxsa\n yaz(\"tapılmadı\")\nson"),
            ["tapılmadı"])

    def test_filtrli_dövr(self):
        self.assertEqual(
            çıxış("hər x üçün 1..6 içində əgər x % 2 == 0\n yaz(x)\nson"),
            ["2", "4", "6"])

    def test_həmişə_dayanla(self):
        self.assertEqual(
            çıxış("dəyişən i = 0\nhəmişə\n i += 1\n"
                  " əgər i > 2 onda\n  dayan\n son\n yaz(i)\nson"),
            ["1", "2"])


class SeçSınağı(unittest.TestCase):
    def test_sadə(self):
        kod = """funksiya f(g: tam) -> mətn
    seç g
        hal 1 → qaytar "bir"
        hal 6, 7 → qaytar "həftəsonu"
        digər hallarda → qaytar "digər"
    son
son
yaz(f(1))
yaz(f(7))
yaz(f(3))"""
        self.assertEqual(çıxış(kod), ["bir", "həftəsonu", "digər"])

    def test_diapazonla(self):
        kod = """funksiya q(b: tam) -> mətn
    seç b
        hal 90..100 → qaytar "Əla"
        hal 70..<90 → qaytar "Yaxşı"
        digər hallarda → qaytar "Zəif"
    son
son
yaz(q(95))
yaz(q(75))
yaz(q(50))"""
        self.assertEqual(çıxış(kod), ["Əla", "Yaxşı", "Zəif"])

    def test_tipə_görə(self):
        kod = """funksiya t(x: istənilən) -> mətn
    seç tipi x
        hal tam → qaytar "ədəd"
        hal mətn → qaytar "mətn"
        digər hallarda → qaytar "naməlum"
    son
son
yaz(t(5))
yaz(t("a"))
yaz(t(doğru))"""
        self.assertEqual(çıxış(kod), ["ədəd", "mətn", "naməlum"])

    def test_kortej_naxışı(self):
        kod = """funksiya n(p: kortej[tam, tam]) -> mətn
    seç p
        hal (0, 0) → qaytar "başlanğıc"
        hal (x, 0) → qaytar "X oxunda"
        hal (x, y) → qaytar "({x}, {y})"
    son
son
yaz(n((0, 0)))
yaz(n((5, 0)))
yaz(n((1, 2)))"""
        self.assertEqual(çıxış(kod),
                         ["başlanğıc", "X oxunda", "(1, 2)"])

    def test_siyahı_naxışı(self):
        kod = """funksiya s(l: siyahı[tam]) -> mətn
    seç l
        hal [] → qaytar "boş"
        hal [tək] → qaytar "bir: {tək}"
        hal [ilk, ...qalan] → qaytar "ilk {ilk}, qalan {uzunluq(qalan)}"
    son
son
yaz(s([]))
yaz(s([7]))
yaz(s([1, 2, 3]))"""
        self.assertEqual(çıxış(kod),
                         ["boş", "bir: 7", "ilk 1, qalan 2"])


class FunksiyaSınağı(unittest.TestCase):
    def test_sadə(self):
        self.assertEqual(
            çıxış("funksiya topla(a: tam, b: tam) -> tam\n"
                  " qaytar a + b\nson\nyaz(topla(3, 4))"), ["7"])

    def test_standart_dəyər(self):
        self.assertEqual(
            çıxış('funksiya s(ad: mətn = "dünya")\n yaz("Salam, {ad}")\n'
                  'son\ns()\ns("Aysel")'),
            ["Salam, dünya", "Salam, Aysel"])

    def test_adlı_arqument(self):
        self.assertEqual(
            çıxış("funksiya q(en: tam, h: tam)\n yaz(\"{en}x{h}\")\nson\n"
                  "q(h: 200, en: 100)"), ["100x200"])

    def test_variadic(self):
        self.assertEqual(
            çıxış("funksiya c(...ə: tam) -> tam\n qaytar ə.cəm()\nson\n"
                  "yaz(c(1, 2, 3))\nyaz(c())"), ["6", "0"])

    def test_yayma(self):
        self.assertEqual(
            çıxış("funksiya c(...ə: tam) -> tam\n qaytar ə.cəm()\nson\n"
                  "yaz(c(...[1, 2, 3, 4]))"), ["10"])

    def test_çoxlu_qaytarma(self):
        self.assertEqual(
            çıxış("funksiya böl(a: tam, b: tam)\n qaytar (a ~/ b, a % b)\n"
                  "son\ndəyişən t, q = böl(17, 5)\nyaz(\"{t} {q}\")"),
            ["3 2"])

    def test_lambda(self):
        self.assertEqual(çıxış("dəyişən f = (x) => x * 2\nyaz(f(21))"),
                         ["42"])
        self.assertEqual(çıxış("dəyişən f = x => x + 1\nyaz(f(1))"), ["2"])

    def test_anonim_funksiya(self):
        self.assertEqual(
            çıxış("dəyişən f = funksiya(x) qaytar x * 3 son\nyaz(f(4))"),
            ["12"])

    def test_qapanma(self):
        kod = """funksiya sayğacYarat()
    dəyişən say = 0
    qaytar funksiya()
        say += 1
        qaytar say
    son
son
dəyişən s = sayğacYarat()
yaz(s())
yaz(s())
dəyişən s2 = sayğacYarat()
yaz(s2())"""
        self.assertEqual(çıxış(kod), ["1", "2", "1"])

    def test_rekursiya(self):
        self.assertEqual(
            çıxış("funksiya f(n: tam) -> tam\n əgər n <= 1 onda\n"
                  "  qaytar 1\n son\n qaytar n * f(n - 1)\nson\n"
                  "yaz(f(10))"), ["3628800"])

    def test_sonsuz_rekursiya_tutulur(self):
        self.assertEqual(
            xəta_tipi("funksiya f() qaytar f() son\nf()"),
            "StekDaşmaXətası")

    def test_arqument_sayı_yoxlanılır(self):
        self.assertEqual(
            xəta_tipi("funksiya f(a: tam, b: tam) qaytar 0 son\nf(1)"),
            "ArqumentXətası")

    def test_boru_operatoru(self):
        self.assertEqual(
            çıxış("funksiya ikiqat(x: tam) -> tam qaytar x * 2 son\n"
                  "yaz(5 |> ikiqat |> ikiqat)"), ["20"])

    def test_yaddaşla(self):
        kod = """@yaddaşla
funksiya fib(n: tam) -> tam
    əgər n < 2 onda
        qaytar n
    son
    qaytar fib(n - 1) + fib(n - 2)
son
yaz(fib(30))"""
        self.assertEqual(çıxış(kod), ["832040"])


class KolleksiyaSınağı(unittest.TestCase):
    def test_siyahı(self):
        self.assertEqual(
            çıxış("dəyişən s = [3, 1, 2]\ns.əlavə(4)\nyaz(s)\n"
                  "yaz(uzunluq(s))\nyaz(s[0])\nyaz(s[-1])"),
            ["[3, 1, 2, 4]", "4", "3", "4"])

    def test_siyahı_metodları(self):
        self.assertEqual(çıxış("yaz([3,1,2].sıralanmış())"), ["[1, 2, 3]"])
        self.assertEqual(çıxış("yaz([1,2,3].çevir((x) => x * 2))"),
                         ["[2, 4, 6]"])
        self.assertEqual(çıxış("yaz([1,2,3,4].filtr((x) => x > 2))"),
                         ["[3, 4]"])
        self.assertEqual(çıxış("yaz([1,2,3].yığ(0, (a, b) => a + b))"),
                         ["6"])
        self.assertEqual(çıxış("yaz([1,2,3].cəm())"), ["6"])
        self.assertEqual(çıxış("yaz([1,2,3].tərs())"), ["[3, 2, 1]"])
        self.assertEqual(çıxış("yaz([1,1,2].təkrarsız())"), ["[1, 2]"])
        self.assertEqual(çıxış("yaz([1,2,3].hamısı((x) => x > 0))"),
                         ["doğru"])

    def test_indeks_diapazondan_kənar(self):
        self.assertEqual(xəta_tipi("dəyişən s = [1]\nyaz(s[5])"),
                         "İndeksXətası")

    def test_lüğət(self):
        self.assertEqual(
            çıxış('dəyişən l = {"a": 1}\nl["b"] = 2\nyaz(l["a"])\n'
                  'yaz(uzunluq(l))\nyaz(l.al("yox", 0))'),
            ["1", "2", "0"])

    def test_lüğətdə_açar_yoxdur(self):
        self.assertEqual(xəta_tipi('yaz({"a": 1}["b"])'), "AçarXətası")

    def test_dəst(self):
        self.assertEqual(
            çıxış("dəyişən d = dəst(1, 2, 2, 3)\nyaz(uzunluq(d))"), ["3"])

    def test_dəst_əməliyyatları(self):
        self.assertEqual(
            çıxış("dəyişən a = dəst(1, 2)\ndəyişən b = dəst(2, 3)\n"
                  "yaz(uzunluq(a.birləşmə(b)))\n"
                  "yaz(uzunluq(a.kəsişmə(b)))"), ["3", "1"])

    def test_kortej(self):
        self.assertEqual(
            çıxış("dəyişən k = (1, \"iki\")\nyaz(k.0)\nyaz(k.1)"),
            ["1", "iki"])

    def test_dağıtma(self):
        self.assertEqual(
            çıxış("dəyişən a, b = (1, 2)\nyaz(\"{a} {b}\")"), ["1 2"])
        self.assertEqual(
            çıxış("dəyişən ilk, ...qalan = [1, 2, 3]\n"
                  "yaz(ilk)\nyaz(qalan)"), ["1", "[2, 3]"])

    def test_dəyişdirmə(self):
        self.assertEqual(
            çıxış("dəyişən a = 1\ndəyişən b = 2\na, b = b, a\n"
                  "yaz(\"{a} {b}\")"), ["2 1"])

    def test_siyahı_qurması(self):
        self.assertEqual(çıxış("yaz([x * x üçün x içində 1..4])"),
                         ["[1, 4, 9, 16]"])
        self.assertEqual(
            çıxış("yaz([x üçün x içində 1..6 əgər x % 2 == 0])"),
            ["[2, 4, 6]"])

    def test_lüğət_qurması(self):
        self.assertEqual(çıxış("yaz({x: x * x üçün x içində 1..3})"),
                         ["{1: 1, 2: 4, 3: 9}"])

    def test_yayma_literalda(self):
        self.assertEqual(çıxış("yaz([...[1, 2], 3])"), ["[1, 2, 3]"])

    def test_dilim(self):
        self.assertEqual(çıxış("yaz([1,2,3,4,5][1..3])"), ["[2, 3, 4]"])
        self.assertEqual(çıxış('yaz("salam"[0..2])'), ["sal"])

    def test_üzvlük(self):
        self.assertEqual(çıxış("yaz(2 içindədir [1, 2, 3])"), ["doğru"])
        self.assertEqual(çıxış('yaz("a" içindədir "salam")'), ["doğru"])
        self.assertEqual(çıxış('yaz("x" içindədir {"a": 1})'), ["yanlış"])


class MətnSınağı(unittest.TestCase):
    def test_az_hərf_çevrilməsi(self):
        self.assertEqual(çıxış('yaz("ışıq".böyüyə())'), ["IŞIQ"])
        self.assertEqual(çıxış('yaz("imran".böyüyə())'), ["İMRAN"])
        self.assertEqual(çıxış('yaz("IŞIQ".kiçiyə())'), ["ışıq"])
        self.assertEqual(çıxış('yaz("İ".kiçiyə())'), ["i"])

    def test_metodlar(self):
        self.assertEqual(çıxış('yaz("  a  ".kəs())'), ["a"])
        self.assertEqual(çıxış('yaz("a,b".böl(","))'), ['["a", "b"]'])
        self.assertEqual(çıxış('yaz(", ".birləşdir(["a", "b"]))'), ["a, b"])
        self.assertEqual(çıxış('yaz("salam".uzunluq())'), ["5"])
        self.assertEqual(çıxış('yaz("salam".tərs())'), ["malas"])
        self.assertEqual(çıxış('yaz("salam".əvəz("a", "o"))'), ["solom"])
        self.assertEqual(çıxış('yaz("salam".ehtiva("ala"))'), ["doğru"])

    def test_əlifba_sırası_müqayisədə(self):
        """`ə` hərfi `e` ilə `f` arasındadır."""
        self.assertEqual(çıxış('yaz("e" < "ə")'), ["doğru"])
        self.assertEqual(çıxış('yaz("ə" < "f")'), ["doğru"])

    def test_sırala_az_qaydası(self):
        self.assertEqual(
            çıxış('yaz(sırala(["zəfər", "əlif", "ağac", "ev"]))'),
            ['["ağac", "ev", "əlif", "zəfər"]'])

    def test_yazıyla_ədəd(self):
        self.assertEqual(
            çıxış("gətir mətn\nyaz(mətn.yazıylaƏdəd(125))"),
            ["yüz iyirmi beş"])


class SinifSınağı(unittest.TestCase):
    İNSAN = """sinif İnsan
    xassə ad: mətn
    xassə yaş: tam

    qurucu(ad: mətn, yaş: tam)
        özü.ad = ad
        özü.yaş = yaş
    son

    metod təqdim()
        yaz("Mən {özü.ad}, {özü.yaş} yaşım var.")
    son
son
"""

    def test_sinif_və_metod(self):
        self.assertEqual(
            çıxış(self.İNSAN + 'yeni İnsan("Aysel", 24).təqdim()'),
            ["Mən Aysel, 24 yaşım var."])

    def test_qısa_qurucu(self):
        self.assertEqual(
            çıxış('sinif A\n qurucu(açıq xassə x: tam)\nson\n'
                  'yaz(yeni A(5).x)'), ["5"])

    def test_miras_və_polimorfizm(self):
        kod = """sinif Heyvan
    qurucu(açıq xassə ad: mətn)
    metod səs() -> mətn
        qaytar "..."
    son
son
sinif İt miras Heyvan
    qurucu(ad: mətn)
        üst(ad)
    son
    əvəz et metod səs() -> mətn
        qaytar "Hav"
    son
son
hər h üçün [yeni İt("Bozo"), yeni Heyvan("X")] içində
    yaz("{h.ad}: {h.səs()}")
son"""
        self.assertEqual(çıxış(kod), ["Bozo: Hav", "X: ..."])

    def test_üst_metod_çağırışı(self):
        kod = """sinif A
    metod f()
        yaz("A")
    son
son
sinif B miras A
    əvəz et metod f()
        üst.f()
        yaz("B")
    son
son
yeni B().f()"""
        self.assertEqual(çıxış(kod), ["A", "B"])

    def test_hesablanan_xassə(self):
        kod = """sinif D
    qurucu(açıq xassə en: onluq, açıq xassə h: onluq)
    xassə sahə: onluq
        oxu qaytar özü.en * özü.h son
    son
son
yaz(yeni D(3, 4).sahə)"""
        self.assertEqual(çıxış(kod), ["12.0"])

    def test_mücərrəd_sinif_yaradılmır(self):
        kod = """mücərrəd sinif F
    mücərrəd metod sahə() -> onluq
son
dəyişən f = yeni F()"""
        self.assertEqual(xəta_tipi(kod), "TipXətası")

    def test_mücərrəd_metod_tətbiq_olunmalıdır(self):
        kod = """mücərrəd sinif F
    mücərrəd metod sahə() -> onluq
son
sinif D miras F
son"""
        self.assertEqual(xəta_tipi(kod), "TipXətası")

    def test_operator_yükləmə(self):
        kod = """sinif V
    qurucu(açıq xassə x: tam, açıq xassə y: tam)
    metod topla(d: V) -> V
        qaytar yeni V(özü.x + d.x, özü.y + d.y)
    son
    metod mətnƏt() -> mətn
        qaytar "({özü.x}, {özü.y})"
    son
son
yaz(yeni V(1, 2) + yeni V(3, 4))"""
        self.assertEqual(çıxış(kod), ["(4, 6)"])

    def test_struktur_dəyərlə_kopyalanır(self):
        kod = """struktur N
    xassə x: tam
son
dəyişən a = N(x: 1)
dəyişən b = a
b.x = 99
yaz(a.x)"""
        self.assertEqual(çıxış(kod), ["1"])

    def test_statik_üzv(self):
        kod = """sinif S
    statik xassə say: tam = 0
    statik metod artır()
        S.say += 1
    son
son
S.artır()
S.artır()
yaz(S.say)"""
        self.assertEqual(çıxış(kod), ["2"])

    def test_genişlətmə(self):
        kod = """genişlət mətn
    metod ikiqat() -> mətn
        qaytar özü + özü
    son
son
yaz("ab".ikiqat())"""
        self.assertEqual(çıxış(kod), ["abab"])


class SadalamaSınağı(unittest.TestCase):
    def test_sadə(self):
        kod = """sadalama Rəng
    QIRMIZI
    YAŞIL
son
yaz(Rəng.QIRMIZI)
yaz(Rəng.QIRMIZI.sıra())
yaz(uzunluq(Rəng.hamısı()))"""
        self.assertEqual(çıxış(kod), ["QIRMIZI", "0", "2"])

    def test_dəyərli(self):
        kod = """sadalama Status: tam
    GÖZLƏYİR = 0
    BİTDİ = 2
son
yaz(Status.BİTDİ.dəyər())"""
        self.assertEqual(çıxış(kod), ["2"])


class XətaSınağı(unittest.TestCase):
    def test_cəhd_tut(self):
        self.assertEqual(
            çıxış('cəhd et\n at Xəta("pis")\ntut (x: Xəta)\n'
                  ' yaz("tutuldu: {x.mesaj}")\nson'),
            ["tutuldu: pis"])

    def test_nəhayət(self):
        self.assertEqual(
            çıxış('cəhd et\n yaz("a")\ntut\n yaz("b")\nnəhayət\n'
                  ' yaz("c")\nson'), ["a", "c"])

    def test_tip_seçimi(self):
        kod = """cəhd et
    dəyişən n = 1 ~/ 0
tut (x: BölməXətası)
    yaz("bölmə")
tut (x: Xəta)
    yaz("digər")
son"""
        self.assertEqual(çıxış(kod), ["bölmə"])

    def test_iyerarxiya(self):
        kod = """cəhd et
    at TipXətası("t")
tut (x: ArqumentXətası)
    yaz("arqument alt növü tutuldu")
son"""
        self.assertEqual(çıxış(kod), ["arqument alt növü tutuldu"])

    def test_iddia(self):
        self.assertEqual(xəta_tipi('iddia yanlış, "pozuldu"'),
                         "İddiaXətası")

    def test_təmin(self):
        kod = """funksiya b(a: tam, d: tam) -> onluq
    təmin d != 0 yoxsa
        at ArqumentXətası("sıfır")
    son
    qaytar a / d
son
cəhd et
    yaz(b(1, 0))
tut (x: ArqumentXətası)
    yaz("tutuldu")
son"""
        self.assertEqual(çıxış(kod), ["tutuldu"])

    def test_gecikdir(self):
        kod = """funksiya f()
    gecikdir yaz("təmizlik")
    yaz("iş")
son
f()"""
        self.assertEqual(çıxış(kod), ["iş", "təmizlik"])


class BoşDəyərSınağı(unittest.TestCase):
    def test_boş_birləşdirmə(self):
        self.assertEqual(
            çıxış('dəyişən a: mətn? = boş\nyaz(a ?? "standart")'),
            ["standart"])

    def test_təhlükəsiz_çağırış(self):
        self.assertEqual(
            çıxış("dəyişən a: mətn? = boş\nyaz(a?.uzunluq())"), ["boş"])

    def test_boşdur(self):
        self.assertEqual(
            çıxış("dəyişən a: mətn? = boş\nyaz(a boşdur)\n"
                  "yaz(a boş deyil)"), ["doğru", "yanlış"])

    def test_varsa(self):
        kod = """funksiya tap(x: tam) -> tam?
    əgər x > 0 onda
        qaytar x
    son
    qaytar boş
son
varsa d = tap(5) onda
    yaz("tapıldı: {d}")
yoxsa
    yaz("yox")
son
varsa d = tap(-1) onda
    yaz("tapıldı")
yoxsa
    yaz("yox")
son"""
        self.assertEqual(çıxış(kod), ["tapıldı: 5", "yox"])

    def test_məcburi_açma_xəta_atır(self):
        self.assertEqual(
            xəta_tipi("dəyişən a: mətn? = boş\nyaz(a!)"),
            "BoşDəyərXətası")


class TipSınağı(unittest.TestCase):
    def test_tip_funksiyası(self):
        hallar = {"42": "tam", "3.14": "onluq", '"a"': "mətn",
                  "doğru": "məntiq", "boş": "heç", "[1]": "siyahı[tam]"}
        for ifadə, gözlənilən in hallar.items():
            with self.subTest(ifadə=ifadə):
                self.assertEqual(çıxış(f"yaz(tip({ifadə}))"),
                                 [gözlənilən])

    def test_çevirmə(self):
        self.assertEqual(çıxış('yaz("42" kimi tam)'), ["42"])
        self.assertEqual(çıxış("yaz(3.9 kimi tam)"), ["3"])
        self.assertEqual(çıxış("yaz(42 kimi mətn)"), ["42"])
        self.assertEqual(çıxış('yaz("abc" kimi? tam)'), ["boş"])

    def test_çevirmə_xətası(self):
        self.assertEqual(xəta_tipi('yaz("abc" kimi tam)'),
                         "ÇevrilməXətası")

    def test_tipidir(self):
        self.assertEqual(çıxış('yaz(5 tipidir tam)'), ["doğru"])
        self.assertEqual(çıxış('yaz("a" tipidir tam)'), ["yanlış"])

    def test_tamƏt(self):
        self.assertEqual(çıxış('yaz(tamƏt("42"))'), ["42"])
        self.assertEqual(çıxış('yaz(tamƏt("abc", 0))'), ["0"])


class ModulSınağı(unittest.TestCase):
    def test_modul_bloku(self):
        kod = """modul riyazi
    ixrac et funksiya kvadrat(x: tam) -> tam
        qaytar x * x
    son
son
yaz(riyazi.kvadrat(5))"""
        self.assertEqual(çıxış(kod), ["25"])

    def test_standart_modul_idxalı(self):
        self.assertEqual(
            çıxış("gətir riyaziyyat kimi r\nyaz(r.faktorial(5))"), ["120"])

    def test_seçmə_idxal(self):
        self.assertEqual(
            çıxış("gətir riyaziyyat.{faktorial}\nyaz(faktorial(5))"),
            ["120"])

    def test_tapılmayan_modul(self):
        self.assertEqual(xəta_tipi("gətir yoxdurbelə"), "ArqumentXətası")


class JSXSınağı(unittest.TestCase):
    """İnterfeys sintaksisi — lekserdə xam skan, parserdə ayırma."""

    def test_sadə_element(self):
        self.assertEqual(çıxış("yaz(<div>salam</div>)"),
                         ["<div>salam</div>"])

    def test_öz_bağlanan(self):
        self.assertEqual(çıxış("yaz(<br />)"), ["<br>"])
        self.assertEqual(çıxış('yaz(<img mənbə="a.png" />)'),
                         ['<img src="a.png">'])

    def test_atributlar(self):
        self.assertEqual(çıxış('yaz(<div sinif="qutu">a</div>)'),
                         ['<div class="qutu">a</div>'])

    def test_məntiqi_atribut(self):
        self.assertEqual(çıxış("yaz(<input söndürülüb />)"),
                         ["<input disabled>"])

    def test_ifadə_atributu(self):
        self.assertEqual(
            çıxış('dəyişən r = "qırmızı"\nyaz(<div sinif={r}>a</div>)'),
            ['<div class="qırmızı">a</div>'])

    def test_atributda_interpolyasiya(self):
        self.assertEqual(
            çıxış('dəyişən r = "yaşıl"\n'
                  'yaz(<div sinif="düymə-{r}">a</div>)'),
            ['<div class="düymə-yaşıl">a</div>'])

    def test_yayma_atributu(self):
        self.assertEqual(
            çıxış('dəyişən x = {"sinif": "a", "id": "b"}\n'
                  "yaz(<div {...x} />)"),
            ['<div class="a" id="b"></div>'])

    def test_ifadə_uşağı(self):
        self.assertEqual(
            çıxış('dəyişən ad = "Aysel"\nyaz(<h1>Salam, {ad}!</h1>)'),
            ["<h1>Salam, Aysel!</h1>"])

    def test_iç_içə(self):
        self.assertEqual(çıxış("yaz(<div><p><b>a</b></p></div>)"),
                         ["<div><p><b>a</b></p></div>"])

    def test_siyahı_uşağı_düzlənir(self):
        self.assertEqual(
            çıxış('yaz(<ul>{["a", "b"].çevir((m) => <li>{m}</li>)}</ul>)'),
            ["<ul><li>a</li><li>b</li></ul>"])

    def test_parça(self):
        self.assertEqual(çıxış("yaz(<><b>a</b><i>b</i></>)"),
                         ["<b>a</b><i>b</i>"])

    def test_mətndə_sadə_kiçikdir(self):
        """`5 < 10` JSX mətni daxilində qanunidir."""
        self.assertEqual(çıxış("yaz(<p>5 < 10</p>)"),
                         ["<p>5 &lt; 10</p>"])

    def test_mətndə_tire(self):
        """`—` leksik xəta verməməlidir — lekser JSX-i xam skan edir."""
        self.assertEqual(çıxış("yaz(<p>Nümunə — izah</p>)"),
                         ["<p>Nümunə — izah</p>"])

    def test_xss_qoruması(self):
        self.assertEqual(çıxış('yaz(<p>{"<script>pis()</script>"}</p>)'),
                         ["<p>&lt;script&gt;pis()&lt;/script&gt;</p>"])

    def test_çoxsətirli_boşluq_yığılır(self):
        kod = "yaz(<div>\n    Salam\n    dünya\n</div>)"
        self.assertEqual(çıxış(kod), ["<div>Salam dünya</div>"])

    def test_müqayisə_jsx_deyil(self):
        self.assertEqual(çıxış("yaz(1 < 2)"), ["doğru"])
        self.assertEqual(çıxış("dəyişən a = 5\nyaz(a < 10)"), ["doğru"])

    def test_komponent(self):
        kod = ('komponent Düymə\n'
               '    xassə mətn: mətn = "Bas"\n'
               '    göstər()\n'
               '        qaytar <button>{özü.mətn}</button>\n'
               '    son\n'
               'son\n'
               'yaz(<Düymə mətn="Göndər" />)')
        self.assertEqual(çıxış(kod), ["<button>Göndər</button>"])

    def test_komponent_standart_xassə(self):
        kod = ('komponent D\n'
               '    xassə mətn: mətn = "standart"\n'
               '    göstər() qaytar <b>{özü.mətn}</b> son\n'
               'son\n'
               'yaz(<D />)')
        self.assertEqual(çıxış(kod), ["<b>standart</b>"])

    def test_komponent_uşaqları(self):
        kod = ('komponent Kart\n'
               '    göstər()\n'
               '        qaytar <div sinif="kart">{özü.uşaqlar}</div>\n'
               '    son\n'
               'son\n'
               'yaz(<Kart><p>içi</p></Kart>)')
        self.assertEqual(çıxış(kod),
                         ['<div class="kart"><p>içi</p></div>'])

    def test_komponent_göstər_yoxdursa(self):
        self.assertEqual(xəta_tipi("sinif X\nson\nyaz(<X />)"),
                         "TipXətası")

    def test_tapılmayan_komponent(self):
        self.assertEqual(xəta_tipi("yaz(<YoxdurBelə />)"),
                         "ArqumentXətası")

    def test_element_üzvləri(self):
        kod = ('dəyişən e = <div sinif="x"><b>qalın</b></div>\n'
               'yaz(e.ad)\n'
               'yaz(e.mətn())\n'
               'yaz(e.atribut("sinif"))\n'
               'yaz(e.tap("b").mətn())\n'
               'yaz(uzunluq(e.uşaqlar))')
        self.assertEqual(çıxış(kod), ["div", "qalın", "x", "qalın", "1"])

    def test_tip_adı(self):
        self.assertEqual(çıxış("yaz(tip(<div />))"), ["element"])

    def test_bağlanmamış_element(self):
        _, x = ayır("yaz(<div>salam)")
        self.assertFalse(x.uğurludur())
        self.assertEqual(x.xətalar[0].kod, "ALQ-P031")

    def test_uyğun_gəlməyən_teq(self):
        _, x = ayır("yaz(<div>a</span>)")
        self.assertIn("ALQ-P032", [d.kod for d in x.xətalar])

    def test_boş_uşaq_atılır(self):
        self.assertEqual(çıxış("yaz(<div>{boş}{yanlış}a</div>)"),
                         ["<div>a</div>"])

    def test_funksiyadan_qaytarma(self):
        kod = ("funksiya f()\n"
               "    qaytar <p>a</p>\n"
               "son\n"
               "yaz(f())")
        self.assertEqual(çıxış(kod), ["<p>a</p>"])


class NümunələrSınağı(unittest.TestCase):
    """Həqiqi nümunə proqramların icrası."""

    def _nümunə(self, ad: str) -> Path:
        return Path(__file__).parent.parent.parent / "numuneler" / ad

    def test_salam(self):
        yol = self._nümunə("01-salam.alqor")
        if not yol.exists():
            self.skipTest("nümunə yoxdur")
        kod = yol.read_text(encoding="utf-8")
        sətirlər = çıxış(kod, ["Aysel", "24"])
        self.assertIn("Aysel, siz yetkinsiniz.", sətirlər)

    def test_dövrlər(self):
        yol = self._nümunə("02-dovrler.alqor")
        if not yol.exists():
            self.skipTest("nümunə yoxdur")
        sətirlər = çıxış(yol.read_text(encoding="utf-8"))
        self.assertIn("Rəqəm: 1", sətirlər)
        self.assertIn("Salam", sətirlər)

    def test_siniflər(self):
        yol = self._nümunə("04-siniflər.alqor")
        if not yol.exists():
            self.skipTest("nümunə yoxdur")
        sətirlər = çıxış(yol.read_text(encoding="utf-8"))
        self.assertTrue(any("Dairə" in s for s in sətirlər))
        self.assertTrue(any("Ən böyük" in s for s in sətirlər))


if __name__ == "__main__":
    unittest.main(verbosity=2)
