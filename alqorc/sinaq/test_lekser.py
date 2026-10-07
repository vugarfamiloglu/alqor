"""Lekser sınaqları."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.lekser import leksə                              # noqa: E402
from alqor.token import KodParçası, MətnParçası, Növ         # noqa: E402


def tokenlər(mətn: str):
    """
    Struktur tokenləri olmadan — yalnız məzmun.

    Faylın sonundaki SETIR_SONU atılır: lekser onu qəsdən emissiya edir
    (son ifadə də bitməlidir), amma sınaqlarda səs-küy yaradır.
    """
    ts, x = leksə(mətn)
    süzgəc = [t for t in ts
              if t.növ not in (Növ.FAYL_SONU, Növ.SENED, Növ.DIREKTIV)]
    while süzgəc and süzgəc[-1].növ is Növ.SETIR_SONU:
        süzgəc.pop()
    return süzgəc, x


def dəyərlər(mətn: str):
    ts, _ = tokenlər(mətn)
    return [t.dəyər for t in ts if t.növ is not Növ.SETIR_SONU]


class ƏdədSınaqları(unittest.TestCase):
    def test_tam(self):
        self.assertEqual(dəyərlər("42"), [42])
        self.assertEqual(dəyərlər("0"), [0])
        self.assertEqual(dəyərlər("1_000_000"), [1000000])

    def test_əsaslar(self):
        self.assertEqual(dəyərlər("0x1F"), [31])
        self.assertEqual(dəyərlər("0b1010"), [10])
        self.assertEqual(dəyərlər("0o755"), [493])
        self.assertEqual(dəyərlər("0xFF_FF"), [65535])

    def test_onluq(self):
        self.assertEqual(dəyərlər("3.14"), [3.14])
        self.assertEqual(dəyərlər("1.5e3"), [1500.0])
        self.assertEqual(dəyərlər("2.5E-4"), [0.00025])
        self.assertEqual(dəyərlər("1_234.567_8"), [1234.5678])

    def test_diapazon_nöqtə_ilə_qarışmır(self):
        """`1..5` → TAM, OP(..), TAM — onluq ədəd DEYİL."""
        ts, x = tokenlər("1..5")
        self.assertTrue(x.uğurludur())
        self.assertEqual([(t.növ, t.dəyər) for t in ts],
                         [(Növ.TAM, 1), (Növ.OP, ".."), (Növ.TAM, 5)])

    def test_üzv_çağırışı(self):
        """`nöqtə.0` — kortej indeksi."""
        self.assertEqual(dəyərlər("5.mətnƏt()"),
                         [5, ".", "mətnƏt", "(", ")"])

    def test_nöqtə_ilə_bitən_ədəd_xətadır(self):
        """§ 1.9.2: `5.` xətadır — `5.0` yazılmalıdır."""
        for kod in ("5.", "yaz(5.)", "x = 5.\nyaz(1)", "5. + 1"):
            _, x = tokenlər(kod)
            self.assertEqual([d.kod for d in x.xətalar], ["ALQ-L006"], kod)
            self.assertIn("5.0", " ".join(x.xətalar[0].köməklər))

    def test_iç_içə_kortej_indeksi(self):
        """`t.1.0` — iki kortej indeksi, `1.0` onluq deyil."""
        self.assertEqual(dəyərlər("t.1.0"), ["t", ".", 1, ".", 0])
        self.assertEqual(dəyərlər("1..2.5"), [1, "..", 2.5])

    def test_ədəd_hərflə_birləşə_bilməz(self):
        _, x = tokenlər("5abc")
        self.assertFalse(x.uğurludur())
        self.assertEqual(x.xətalar[0].kod, "ALQ-L006")

    def test_daşma(self):
        _, x = tokenlər("99999999999999999999999")
        self.assertEqual(x.xətalar[0].kod, "ALQ-L007")

    def test_prefiksdən_sonra_rəqəm_yoxdur(self):
        _, x = tokenlər("0x")
        self.assertEqual(x.xətalar[0].kod, "ALQ-L006")


class MətnSınaqları(unittest.TestCase):
    def test_sadə(self):
        self.assertEqual(dəyərlər('"Salam"'), ["Salam"])
        self.assertEqual(dəyərlər("'Salam'"), ["Salam"])
        self.assertEqual(dəyərlər('""'), [""])

    def test_azərbaycan_hərfləri(self):
        self.assertEqual(dəyərlər('"Şəhərin işığı"'), ["Şəhərin işığı"])

    def test_qaçışlar(self):
        self.assertEqual(dəyərlər(r'"a\nb"'), ["a\nb"])
        self.assertEqual(dəyərlər(r'"a\tb"'), ["a\tb"])
        self.assertEqual(dəyərlər(r'"a\\b"'), ["a\\b"])
        self.assertEqual(dəyərlər(r'"a\"b"'), ['a"b'])
        self.assertEqual(dəyərlər(r'"\u{259}"'), ["ə"])
        self.assertEqual(dəyərlər(r'"\x41"'), ["A"])
        self.assertEqual(dəyərlər(r'"\{a\}"'), ["{a}"])

    def test_tanınmayan_qaçış(self):
        _, x = tokenlər(r'"a\qb"')
        self.assertEqual(x.xətalar[0].kod, "ALQ-L005")

    def test_yanlış_kod_nöqtəsi(self):
        _, x = tokenlər(r'"\u{110000}"')
        self.assertEqual(x.xətalar[0].kod, "ALQ-L008")

    def test_bağlanmamış(self):
        _, x = tokenlər('yaz("Salam, dünya)')
        self.assertFalse(x.uğurludur())
        self.assertEqual(x.xətalar[0].kod, "ALQ-L003")

    def test_xam_mətn(self):
        ts, x = tokenlər(r'x"C:\yeni\test"')
        self.assertTrue(x.uğurludur())
        self.assertEqual(ts[0].dəyər, "C:\\yeni\\test")

    def test_bayt_mətn(self):
        ts, _ = tokenlər('b"ABC"')
        self.assertEqual(ts[0].növ, Növ.BAYT)
        self.assertEqual(ts[0].dəyər, b"ABC")

    def test_çoxsətirli(self):
        mətn = '"""\n    birinci\n    ikinci\n    """'
        ts, x = tokenlər(mətn)
        self.assertTrue(x.uğurludur())
        self.assertTrue(ts[0].çoxsətirli)
        self.assertEqual(ts[0].dəyər, "birinci\nikinci\n")


class InterpolyasiyaSınaqları(unittest.TestCase):
    def test_sadə(self):
        ts, x = tokenlər('"Salam, {ad}!"')
        self.assertTrue(x.uğurludur())
        p = ts[0].parçalar
        self.assertEqual(len(p), 3)
        self.assertEqual(p[0], MətnParçası("Salam, "))
        self.assertIsInstance(p[1], KodParçası)
        self.assertEqual([t.dəyər for t in p[1].tokenlər], ["ad"])
        self.assertEqual(p[2], MətnParçası("!"))

    def test_ifadə(self):
        ts, _ = tokenlər('"Gələn il {yaş + 1} olacaq"')
        kod = [p for p in ts[0].parçalar if isinstance(p, KodParçası)][0]
        self.assertEqual([t.dəyər for t in kod.tokenlər], ["yaş", "+", 1])

    def test_format(self):
        ts, _ = tokenlər('"Qiymət: {q:.2}"')
        kod = [p for p in ts[0].parçalar if isinstance(p, KodParçası)][0]
        self.assertEqual(kod.format, ".2")

    def test_iç_içə_mötərizə(self):
        ts, x = tokenlər('"{f(g(x), [1, 2])}"')
        self.assertTrue(x.uğurludur(), x.hesabat(False))
        kod = [p for p in ts[0].parçalar if isinstance(p, KodParçası)][0]
        self.assertIn("f", [t.dəyər for t in kod.tokenlər])

    def test_çoxlu(self):
        ts, _ = tokenlər('"{a} və {b}"')
        kodlar = [p for p in ts[0].parçalar if isinstance(p, KodParçası)]
        self.assertEqual(len(kodlar), 2)

    def test_bağlanmamış(self):
        _, x = tokenlər('"Salam, {ad"')
        self.assertFalse(x.uğurludur())
        self.assertIn("ALQ-L011", [d.kod for d in x.xətalar])

    def test_sadə_mətndir(self):
        ts, _ = tokenlər('"sabit"')
        self.assertTrue(ts[0].sadə_mətndir())
        ts2, _ = tokenlər('"{x}"')
        self.assertFalse(ts2[0].sadə_mətndir())


class AçarSözSınaqları(unittest.TestCase):
    def test_kanonik(self):
        ts, _ = tokenlər("əgər x onda son")
        self.assertEqual([(t.növ, t.dəyər) for t in ts],
                         [(Növ.ACAR, "əgər"), (Növ.AD, "x"),
                          (Növ.ACAR, "onda"), (Növ.ACAR, "son")])

    def test_ascii_alias(self):
        ts, x = tokenlər("eger x onda son")
        self.assertEqual(ts[0].dəyər, "əgər")
        self.assertTrue(ts[0].ascii_idi)
        self.assertEqual(ts[0].xam, "eger")
        self.assertIn("ALQ-L020", [d.kod for d in x.xəbərdarlıqlar])

    def test_çox_sözlü(self):
        ts, _ = tokenlər("nə qədər ki x")
        self.assertEqual(ts[0].dəyər, "nə qədər ki")
        self.assertEqual(ts[0].növ, Növ.ACAR)
        self.assertEqual(ts[1].dəyər, "x")

    def test_çox_sözlü_ascii(self):
        ts, x = tokenlər("ne qeder ki x")
        self.assertEqual(ts[0].dəyər, "nə qədər ki")
        self.assertTrue(ts[0].ascii_idi)

    def test_bütün_çox_sözlülər(self):
        hallar = {
            "digər hallarda": "digər hallarda",
            "yoxsa əgər": "yoxsa əgər",
            "davam et": "davam et",
            "cəhd et": "cəhd et",
            "ixrac et": "ixrac et",
            "əvəz et": "əvəz et",
            "və ya": "və ya",
            "boş deyil": "boş deyil",
        }
        for giriş, gözlənilən in hallar.items():
            with self.subTest(giriş=giriş):
                ts, _ = tokenlər(giriş)
                self.assertEqual(ts[0].dəyər, gözlənilən)
                self.assertEqual(len(ts), 1, f"{giriş} → {ts}")

    def test_əks_halda_yoxsaya_çevrilir(self):
        ts, _ = tokenlər("əks halda")
        self.assertEqual(ts[0].dəyər, "yoxsa")

    def test_davam_tək(self):
        ts, _ = tokenlər("davam")
        self.assertEqual(ts[0].dəyər, "davam et")

    def test_çox_sözlü_sətir_keçmir(self):
        """`yoxsa` yeni sətirdən sonra `əgər` ilə birləşməməlidir."""
        ts, _ = tokenlər("yoxsa\n    əgər x onda son")
        self.assertEqual(ts[0].dəyər, "yoxsa")
        self.assertEqual(ts[1].növ, Növ.SETIR_SONU)
        self.assertEqual(ts[2].dəyər, "əgər")

    def test_identifikatorda_ascii_çevrilməsi_yoxdur(self):
        """`yas` açar söz deyil və `yaş`-a çevrilmir."""
        ts, _ = tokenlər("yas = yaş")
        self.assertEqual(ts[0].növ, Növ.AD)
        self.assertEqual(ts[0].dəyər, "yas")
        self.assertEqual(ts[2].dəyər, "yaş")

    def test_kontekstli_sözlər_qorunmur(self):
        for söz in ("oxu", "yaz", "vəziyyət", "göstər", "sınaq"):
            with self.subTest(söz=söz):
                ts, _ = tokenlər(söz)
                self.assertEqual(ts[0].növ, Növ.AD)

    def test_ehtiyat_söz_xəbərdarlığı(self):
        _, x = tokenlər("dəyişən makro = 5")
        self.assertIn("ALQ-L016", [d.kod for d in x.xəbərdarlıqlar])

    def test_üzv_adında_ehtiyat_xəbərdarlığı_yoxdur(self):
        _, x = tokenlər("veb.makro(5)")
        self.assertEqual(x.xəbərdarlıqlar, [])

    def test_hərfə_həssasdır(self):
        ts, _ = tokenlər("Əgər ƏGƏR")
        self.assertEqual(ts[0].növ, Növ.AD)
        self.assertEqual(ts[1].növ, Növ.AD)


class IdentifikatorSınaqları(unittest.TestCase):
    def test_azərbaycan_hərfləri(self):
        for ad in ("ad", "yaş", "ümumiMəbləğ", "İstifadəçi", "_gizli",
                   "şəbəkə_bağlantısı", "sayğac2", "ƏnBöyükDəyər"):
            with self.subTest(ad=ad):
                ts, x = tokenlər(ad)
                self.assertTrue(x.uğurludur())
                self.assertEqual(ts[0].növ, Növ.AD)
                self.assertEqual(ts[0].dəyər, ad)

    def test_tanınmayan_simvol(self):
        _, x = tokenlər("ad$ = 5")
        self.assertEqual(x.xətalar[0].kod, "ALQ-L002")


class OperatorSınaqları(unittest.TestCase):
    def test_maksimal_udma(self):
        hallar = [
            ("**=", ["**="]), ("~/=", ["~/="]), (">>>", [">>>"]),
            ("..<", ["..<"]), ("...", ["..."]), ("<=>", ["<=>"]),
            ("??=", ["??="]), ("~/", ["~/"]), ("|>", ["|>"]),
            ("->", ["->"]), ("=>", ["=>"]), ("?.", ["?."]),
            ("++", ["++"]), ("**", ["**"]), ("..", [".."]),
            ("<=", ["<="]), ("==", ["=="]), ("!=", ["!="]),
        ]
        for giriş, gözlənilən in hallar:
            with self.subTest(op=giriş):
                self.assertEqual(dəyərlər(giriş), gözlənilən)

    def test_ox_formaları(self):
        self.assertEqual(dəyərlər("hal 1 → yaz"), ["hal", 1, "→", "yaz"])
        self.assertEqual(dəyərlər("hal 1 -> yaz"), ["hal", 1, "->", "yaz"])

    def test_ardıcıl(self):
        self.assertEqual(dəyərlər("a+=1"), ["a", "+=", 1])
        self.assertEqual(dəyərlər("a ~/ b"), ["a", "~/", "b"])
        self.assertEqual(dəyərlər("x?.y ?? z"), ["x", "?.", "y", "??", "z"])


class SətirSonuSınaqları(unittest.TestCase):
    def _struktur(self, mətn):
        ts, _ = tokenlər(mətn)
        return ["⏎" if t.növ is Növ.SETIR_SONU else t.dəyər for t in ts]

    def test_adi(self):
        self.assertEqual(self._struktur("a = 1\nb = 2"),
                         ["a", "=", 1, "⏎", "b", "=", 2])

    def test_mötərizədə_udulur(self):
        self.assertEqual(self._struktur("topla(\n 1,\n 2\n)"),
                         ["topla", "(", 1, ",", 2, ")"])

    def test_siyahıda_udulur(self):
        self.assertEqual(self._struktur("[\n 1,\n 2,\n]"),
                         ["[", 1, ",", 2, ",", "]"])

    def test_operatordan_sonra_udulur(self):
        self.assertEqual(self._struktur("a = 1 +\n 2"),
                         ["a", "=", 1, "+", 2])

    def test_və_açar_sözündən_sonra_udulur(self):
        self.assertEqual(self._struktur("a və\n b"), ["a", "və", "b"])
        self.assertEqual(self._struktur("a və ya\n b"),
                         ["a", "və ya", "b"])

    def test_təkrar_sətir_sonu_yoxdur(self):
        self.assertEqual(self._struktur("a\n\n\n\nb"), ["a", "⏎", "b"])

    def test_faylın_başında_yoxdur(self):
        self.assertEqual(self._struktur("\n\na"), ["a"])

    def test_bağlayan_mötərizədən_sonra_var(self):
        self.assertEqual(self._struktur("f()\ng()"),
                         ["f", "(", ")", "⏎", "g", "(", ")"])


class ŞərhSınaqları(unittest.TestCase):
    def test_sətir_şərhi(self):
        self.assertEqual(dəyərlər("a // şərh\nb"), ["a", "b"])

    def test_blok_şərhi(self):
        self.assertEqual(dəyərlər("a /* şərh */ b"), ["a", "b"])

    def test_iç_içə_blok(self):
        self.assertEqual(dəyərlər("a /* bir /* iki */ üç */ b"), ["a", "b"])

    def test_bağlanmamış_blok(self):
        _, x = tokenlər("a /* şərh")
        self.assertEqual(x.xətalar[0].kod, "ALQ-L004")

    def test_sənəd_şərhi(self):
        ts, _ = leksə("/// Sənəd\nfunksiya f()")
        sənədlər = [t for t in ts if t.növ is Növ.SENED]
        self.assertEqual(len(sənədlər), 1)
        self.assertEqual(sənədlər[0].dəyər, "Sənəd")

    def test_modul_sənədi(self):
        ts, _ = leksə("//! Modul sənədi")
        self.assertEqual([t.dəyər for t in ts if t.növ is Növ.SENED],
                         ["Modul sənədi"])

    def test_direktiv(self):
        ts, _ = leksə("// alqor: hədəf veb\na")
        self.assertEqual([t.dəyər for t in ts if t.növ is Növ.DIREKTIV],
                         ["hədəf veb"])

    def test_ascii_xəbərdarlığı_söndürülür(self):
        _, x = leksə("// alqor: ascii-xeberdarliq sondur\neger x onda son")
        self.assertEqual(x.xəbərdarlıqlar, [])

    def test_şərhdə_tire_homoqlif_deyil(self):
        """`—` qanuni durğu işarəsidir, düzəldilməməlidir."""
        _, x = leksə("// Nümunə 1 — Ən sadə proqram\na = 1")
        self.assertEqual(x.siyahı, [], x.hesabat(False))

    def test_shebang(self):
        ts, x = tokenlər("#!/usr/bin/env alqor\nyaz(1)")
        self.assertTrue(x.uğurludur())
        self.assertEqual(ts[0].dəyər, "yaz")


class SimvolSınaqları(unittest.TestCase):
    def test_sadə(self):
        ts, x = tokenlər("`ə`")
        self.assertTrue(x.uğurludur())
        self.assertEqual(ts[0].növ, Növ.SIMVOL)
        self.assertEqual(ts[0].dəyər, "ə")

    def test_qaçış(self):
        ts, _ = tokenlər(r"`\n`")
        self.assertEqual(ts[0].dəyər, "\n")

    def test_bağlanmamış(self):
        _, x = tokenlər("`ə")
        self.assertEqual(x.xətalar[0].kod, "ALQ-L017")


class MövqeSınaqları(unittest.TestCase):
    def test_sətir_sütun(self):
        ts, _ = tokenlər("a = 1\nbb = 22")
        a, bb = ts[0], ts[4]
        self.assertEqual((a.yer.sətir, a.yer.sütun), (1, 1))
        self.assertEqual((bb.yer.sətir, bb.yer.sütun), (2, 1))

    def test_uzunluq(self):
        ts, _ = tokenlər("dəyişən")
        self.assertEqual(ts[0].yer.uzunluq, 7)

    def test_xəta_mövqeyi(self):
        _, x = tokenlər("a = 1\nb = $")
        d = x.xətalar[0]
        self.assertEqual(d.yer.sətir, 2)
        self.assertEqual(d.yer.sütun, 5)


class TamProqramSınağı(unittest.TestCase):
    PROQRAM = '''// Nümunə proqram
gətir riyaziyyat

/// İki ədədi toplayır
funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son

funksiya əsas()
    dəyişən ad = oxu("Adınız: ")
    dəyişən yaş = oxuTam("Yaşınız: ")

    əgər yaş >= 18 və ad != "" onda
        yaz("{ad}, siz yetkinsiniz.")
    yoxsa əgər yaş >= 13 onda
        yaz("{ad}, siz yeniyetməsiniz.")
    yoxsa
        yaz("{ad}, siz uşaqsınız.")
    son

    dəyişən i = 1
    nə qədər ki i <= 5
        yaz("Rəqəm: {i}")
        i += 1
    son

    hər x üçün 1..10 addım 2 içində
        əgər x == 5 onda davam et son
        yaz(x)
    son

    cəhd et
        dəyişən n = tamƏt(ad)
    tut (x: ÇevrilməXətası)
        yaz("Ədəd deyil")
    nəhayət
        yaz("bitdi")
    son
son
'''

    def test_xəta_yoxdur(self):
        ts, x = leksə(self.PROQRAM, "sınaq.alq")
        self.assertTrue(x.uğurludur(), x.hesabat(False))
        self.assertEqual(x.xəbərdarlıqlar, [], x.hesabat(False))

    def test_açar_sözlər_tanınır(self):
        ts, _ = leksə(self.PROQRAM)
        acarlar = {t.dəyər for t in ts if t.növ is Növ.ACAR}
        for gözlənilən in ("gətir", "funksiya", "qaytar", "dəyişən",
                           "əgər", "və", "onda", "yoxsa əgər", "yoxsa",
                           "son", "nə qədər ki", "hər", "üçün", "addım",
                           "içində", "davam et", "cəhd et", "tut",
                           "nəhayət"):
            self.assertIn(gözlənilən, acarlar)
        # Tip adları açar söz DEYİL — öncədən elan olunmuş identifikatorlar
        for tip_adı in ("tam", "mətn", "siyahı", "lüğət"):
            self.assertNotIn(tip_adı, acarlar)

    def test_sənəd_şərhi_saxlanılır(self):
        ts, _ = leksə(self.PROQRAM)
        self.assertEqual([t.dəyər for t in ts if t.növ is Növ.SENED],
                         ["İki ədədi toplayır"])

    def test_interpolyasiyalar(self):
        ts, _ = leksə(self.PROQRAM)
        şablonlar = [t for t in ts if t.növ is Növ.METN
                     and not t.sadə_mətndir()]
        self.assertEqual(len(şablonlar), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
