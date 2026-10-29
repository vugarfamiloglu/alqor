"""Layihə alətləri: manifest, `yeni`, `sına`, `sənəd`, `qur`, idxal."""

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from alqor import layihe as L                                # noqa: E402
from alqor import qurucu, senedci                            # noqa: E402
from alqor import sinaqci as S                               # noqa: E402

ALQORC = Path(__file__).parent.parent / "alqorc.py"


def cli(*arq: str, qovluq: Path | None = None,
        giriş: str = "") -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1",
               ALQOR_BASSIZ="1")
    return subprocess.run([sys.executable, str(ALQORC), *arq],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=qovluq, input=giriş, env=env)


class Qovluqlu(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.q = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def yaz(self, nisbi: str, mətn: str) -> Path:
        p = self.q / nisbi
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(mətn, encoding="utf-8")
        return p


# ═══════════════════════════════════════════════════════════════════════
#  Manifest
# ═══════════════════════════════════════════════════════════════════════

class ManifestSınağı(unittest.TestCase):
    def test_azərbaycan_açarları_və_doğru(self):
        m = L.oxu('''
# şərh
[paket]
ad = "kitab-rəfi"            # sətir sonu şərhi
açarSözlər = ["veb", "api"]
versiya = '1.0.0'

[tip]
sərt_boş = doğru
rejim = "sərt"

[qurma]
optimallaşdırma = 2
nisbət = 0.5
sıxılma = yanlış
hədəf = [
    "linux-x64",   # birinci
    "veb",
]

[asılılıqlar]
yerli = { yol = "../yerli", ixtiyari = true }
"@şirkət/analitika" = "1.0"
''')
        self.assertEqual(m["paket"]["açarSözlər"], ["veb", "api"])
        self.assertEqual(m["paket"]["versiya"], "1.0.0")
        self.assertIs(m["tip"]["sərt_boş"], True)
        self.assertIs(m["qurma"]["sıxılma"], False)
        self.assertEqual(m["qurma"]["optimallaşdırma"], 2)
        self.assertEqual(m["qurma"]["nisbət"], 0.5)
        self.assertEqual(m["qurma"]["hədəf"], ["linux-x64", "veb"])
        self.assertEqual(m["asılılıqlar"]["yerli"],
                         {"yol": "../yerli", "ixtiyari": True})
        self.assertEqual(m["asılılıqlar"]["@şirkət/analitika"], "1.0")

    def test_şərh_işarəsi_mətn_içində(self):
        self.assertEqual(L.oxu('a = "#1 # deyil"')["a"], "#1 # deyil")

    def test_xətalar_sətir_nömrəsi_ilə(self):
        for mətn, sətir in (('[paket\nad = 1', 1), ('a = 1\na = 2', 2),
                            ('a = sözdür', 1), ('a = [1, 2', 1),
                            ('sadəcə söz', 1)):
            with self.assertRaises(L.ManifestXətası) as k:
                L.oxu(mətn)
            self.assertEqual(k.exception.sətir, sətir, mətn)


class LayihəTapmaSınağı(Qovluqlu):
    def test_yuxarı_qovluqda_tapır(self):
        self.yaz("layihe.alq", '[paket]\nad = "x"\n[qurma]\n'
                                 'giriş = "a/b.alq"\n')
        alt = self.q / "mənbə" / "dərin"
        alt.mkdir(parents=True)
        l = L.tap(alt)
        self.assertEqual(l.ad, "x")
        self.assertEqual(l.giriş, self.q.resolve() / "a" / "b.alq")
        self.assertIsNone(L.tap(Path(tempfile.gettempdir()) / "yoxdur-x"))

    def test_standartlar(self):
        self.yaz("layihe.alq", "")
        l = L.tap(self.q)
        self.assertEqual(l.ad, self.q.resolve().name)
        self.assertEqual(l.tip_rejimi, "normal")
        self.assertEqual(l.giriş.name, "əsas.alq")


# ═══════════════════════════════════════════════════════════════════════
#  `yeni` — hər şablon işləyir və sınaqları keçir
# ═══════════════════════════════════════════════════════════════════════

class YeniSınağı(Qovluqlu):
    def test_bütün_şablonlar_sınaqdan_keçir(self):
        import alqor.pencere as P
        köhnə = P._başsız_rejimdir
        P._başsız_rejimdir = lambda: True
        try:
            for ş in L.ŞABLONLAR:
                q = self.q / f"l-{ş}"
                L.yarat(q, f"l-{ş}", ş)
                l = L.tap(q)
                self.assertTrue(l.giriş.is_file(), ş)
                fayllar = S.sınaq_faylları([l.sınaq_qovluğu])
                self.assertEqual(len(fayllar), 1, ş)
                n = S.faylı_sına(fayllar[0])
                self.assertEqual(n.xəta, "", ş)
                self.assertTrue(n.nəticələr, ş)
                for r in n.nəticələr:
                    self.assertEqual(r.vəziyyət, S.UĞURLU,
                                     f"{ş}: {r.ad}: {r.mesaj}")
                # Sənəd nümunələri də işləyir
                for r in S.sənədi_sına(l.giriş).nəticələr:
                    self.assertEqual(r.vəziyyət, S.UĞURLU,
                                     f"{ş}: {r.ad}: {r.mesaj}")
        finally:
            P._başsız_rejimdir = köhnə

    def test_şablonlar_format_edilmişdir(self):
        from alqor.alqorfmt import formatla
        for ş in L.ŞABLONLAR:
            q = self.q / ş
            for f in L.yarat(q, ş, ş):
                if f.suffix == ".alq" and f.name != "layihe.alq":
                    m = f.read_text(encoding="utf-8")
                    self.assertEqual(formatla(m).mətn, m, f"{ş}/{f.name}")

    def test_boş_olmayan_qovluq_və_pis_ad(self):
        self.yaz("dolu/a.txt", "x")
        with self.assertRaises(ValueError):
            L.yarat(self.q / "dolu", "dolu")
        with self.assertRaises(ValueError):
            L.yarat(self.q / "x", "a/b")
        with self.assertRaises(ValueError):
            L.yarat(self.q / "y", "y", "naməlum")

    def test_cli(self):
        c = cli("yeni", "tətbiq", "--şablon", "veb", qovluq=self.q)
        self.assertEqual(c.returncode, 0, c.stderr)
        self.assertTrue((self.q / "tətbiq" / "layihe.alq").is_file())
        c = cli("sına", qovluq=self.q / "tətbiq")
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertIn("2 uğurlu", c.stdout)


# ═══════════════════════════════════════════════════════════════════════
#  `sına` — sınaq işlədicisi
# ═══════════════════════════════════════════════════════════════════════

class SınaqİşlədicisiSınağı(Qovluqlu):
    KOD = '''gətir test

@sınaq("uğurlu")
funksiya a()
    test.bərabər(1 + 1, 2)
son

@sınaq("uğursuz")
funksiya b()
    test.bərabər(1 + 1, 3)
son

@sınaq
funksiya xətalı()
    yaz(1 / 0)
son

@atla("hələ yazılmayıb")
@sınaq
funksiya atlanan()
    test.uğursuz()
son

@sınaqVerilənlər([[2, 4], [3, 9], [4, 15]])
funksiya kvadrat(x: tam, g: tam)
    test.bərabər(x * x, g)
son

dəyişən say = 0

@sınaqQrupu("Qrup")
modul qrup
    @əvvəl
    funksiya hazırla()
        say = 10
    son

    @sınaq("əvvəl işləyib")
    funksiya yoxla()
        test.bərabər(say, 10)
    son
son

funksiya köməkçi()
    test.uğursuz("sınaq deyil — çağırılmamalıdır")
son
'''

    BLOKLAR = '''
funksiya topla(a, b)
    qaytar a + b
son

sınaq "toplama işləyir"
    gözlənilir topla(2, 2) == 4
    gözlənilir topla(-1, 1) == 0
son

sınaq "səhv gözlənti"
    dəyişən s = [1, 2]
    gözlənilir s == [1, 2, 3]
son

sınaq "bölmə xətası"
    gözlənilir xəta BölməXətası: 1 / 0
son

sınaq "gözlənilməz xəta"
    dəyişən x = boş
    yaz(x.y)
son

modul riyaziyyat
    funksiya kvadrat(x)
        qaytar x * x
    son
    sınaq "kvadrat"
        gözlənilir kvadrat(3) == 9
    son
son

yaz("adi icrada sınaqlar işləmir")
'''

    def test_nəticələr(self):
        n = S.faylı_sına(self.yaz("riyazi_sınaq.alq", self.KOD))
        self.assertEqual(n.xəta, "")
        v = {r.ad: r for r in n.nəticələr}
        self.assertEqual(v["uğurlu"].vəziyyət, S.UĞURLU)
        self.assertEqual(v["uğursuz"].vəziyyət, S.UĞURSUZ)
        self.assertIn("gözlənilən: 3", v["uğursuz"].mesaj)
        self.assertIn("riyazi_sınaq.alq:10", v["uğursuz"].yer)
        self.assertEqual(v["xətalı"].vəziyyət, S.XƏTA)
        self.assertIn("BölməXətası", v["xətalı"].mesaj)
        self.assertEqual(v["atlanan"].vəziyyət, S.ATLANMIŞ)
        self.assertEqual(v["kvadrat [2, 4]"].vəziyyət, S.UĞURLU)
        self.assertEqual(v["kvadrat [4, 15]"].vəziyyət, S.UĞURSUZ)
        self.assertEqual(v["Qrup › əvvəl işləyib"].vəziyyət, S.UĞURLU)
        self.assertNotIn("köməkçi", v)
        self.assertEqual(len(n.nəticələr), 8)

    def test_sınaq_blokları(self):
        """`sınaq "ad" … son` və `gözlənilir` (§ 13.5)"""
        n = S.faylı_sına(self.yaz("blok_sınaq.alq", self.BLOKLAR))
        self.assertEqual(n.xəta, "")
        v = {r.ad: r for r in n.nəticələr}
        self.assertEqual(v["toplama işləyir"].vəziyyət, S.UĞURLU)
        self.assertEqual(v["səhv gözlənti"].vəziyyət, S.UĞURSUZ)
        self.assertIn("sol: [1, 2]", v["səhv gözlənti"].mesaj)
        self.assertIn("sağ: [1, 2, 3]", v["səhv gözlənti"].mesaj)
        self.assertEqual(v["bölmə xətası"].vəziyyət, S.UĞURLU)
        self.assertEqual(v["gözlənilməz xəta"].vəziyyət, S.XƏTA)
        self.assertEqual(v["riyaziyyat › kvadrat"].vəziyyət, S.UĞURLU)
        self.assertEqual(len(n.nəticələr), 5)

    def test_filtr(self):
        n = S.faylı_sına(self.yaz("a_sınaq.alq", self.KOD), "KVADRAT")
        self.assertEqual(len(n.nəticələr), 3)

    def test_ayrılmayan_fayl(self):
        n = S.faylı_sına(self.yaz("pis_sınaq.alq", "əgər onda\n"))
        self.assertIn("ALQ-P", n.xəta)

    def test_fayl_kəşfi(self):
        self.yaz("sınaq/bir.alq", "")
        self.yaz("mənbə/iki_sınaq.alq", "")
        self.yaz("mənbə/adi.alq", "")
        self.yaz("qurma/üç_sınaq.alq", "")
        adlar = sorted(f.name for f in S.sınaq_faylları([self.q]))
        self.assertEqual(adlar, ["bir.alq", "iki_sınaq.alq"])

    def test_cli_çıxış_kodu_və_hesabat(self):
        self.yaz("sınaq/x.alq", self.KOD)
        c = cli("sına", str(self.q / "sınaq"), qovluq=self.q)
        self.assertEqual(c.returncode, 1)
        self.assertIn("✗ uğursuz", c.stdout)
        self.assertIn("Nəticə: 4 uğurlu, 2 uğursuz, 1 xəta, 1 atlanmış",
                      c.stdout)


class TestModuluSınağı(unittest.TestCase):
    def _nəticə(self, gövdə: str):
        with tempfile.TemporaryDirectory() as q:
            p = Path(q) / "t_sınaq.alq"
            p.write_text("gətir test\n@sınaq\nfunksiya t()\n" + gövdə
                         + "\nson\n", encoding="utf-8")
            return S.faylı_sına(p).nəticələr[0]

    def test_uğurlu_təsdiqlər(self):
        r = self._nəticə('''    test.boş(boş)
    test.boşDeyil(1)
    test.ehtiva([1, 2], 2)
    test.ehtiva("salam", "al")
    test.ehtiva({"a": 1}, "a")
    test.atır(() => 1 / 0, BölməXətası)
    test.atır(() => 1 / 0, "Xəta")
    test.atır(() => 1 / 0)
    test.bərabər(test.atmır(() => 5), 5)
    test.təxminən(0.1 + 0.2, 0.3)
    test.uyğun("ab12", "[0-9]+")
    test.bərabərDeyil(1, 2)''')
        self.assertEqual(r.vəziyyət, S.UĞURLU, r.mesaj)

    def test_uğursuz_təsdiqlər(self):
        for gövdə, parça in (
                ("    test.boş(1)", "boş gözlənilirdi"),
                ("    test.ehtiva([1], 5)", "içində 5 yoxdur"),
                ("    test.atır(() => 1)", "xəta gözlənilirdi"),
                ("    test.atır(() => 1 / 0, ArqumentXətası)",
                 "BölməXətası atıldı"),
                ("    test.atmır(() => 1 / 0)", "gözlənilmirdi"),
                ("    test.uyğun(\"ab\", \"[0-9]\")", "uyğun deyil"),
                ("    test.uğursuz(\"öz mesajım\")", "öz mesajım")):
            r = self._nəticə(gövdə)
            self.assertEqual(r.vəziyyət, S.UĞURSUZ, gövdə)
            self.assertIn(parça, r.mesaj, gövdə)


# ═══════════════════════════════════════════════════════════════════════
#  `sənəd`
# ═══════════════════════════════════════════════════════════════════════

class SənədSınağı(Qovluqlu):
    KOD = '''//! Həndəsə modulu.
//!
//! Sahə hesablamaları.

/// Dairənin sahəsi.
///
/// # Nümunə
/// ```alqor
/// yaz(sahə(1) > 3)
///     // girinti qorunur
/// ```
ixrac et funksiya sahə(r: onluq,
                       dəqiq: məntiq = yanlış) -> onluq
    qaytar 3.14159 * r * r
son

/// Gizli köməkçi — sənədə düşmür, çünki ixrac olunmayıb.
funksiya köməkçi() -> tam
    qaytar 1
son

/// Nöqtə.
@yaddaşla
ixrac et sinif Nöqtə
    /// X koordinatı.
    açıq xassə x: onluq = 0.0

    /// Məsafə.
    metod məsafə() -> onluq
        qaytar özü.x
    son
son
'''

    def test_elementlər_və_imzalar(self):
        f = senedci.fayl_sənədi(self.yaz("həndəsə.alq", self.KOD))
        self.assertTrue(f.sənəd.startswith("Həndəsə modulu."))
        adlar = [e.ad for e in f.elementlər]
        self.assertEqual(adlar, ["sahə", "Nöqtə"])
        sahə = f.elementlər[0]
        self.assertEqual(sahə.imza, "funksiya sahə(r: onluq, dəqiq: məntiq "
                                    "= yanlış) -> onluq")
        self.assertIn("    // girinti qorunur", sahə.sənəd)
        nöqtə = f.elementlər[1]
        self.assertEqual(nöqtə.sənəd, "Nöqtə.")
        self.assertEqual([ü.ad for ü in nöqtə.üzvlər], ["x", "məsafə"])
        self.assertEqual(nöqtə.üzvlər[1].sənəd, "Məsafə.")

    def test_markdown_və_html(self):
        f = senedci.fayl_sənədi(self.yaz("h.alq", self.KOD))
        md = senedci.markdown([f], "Həndəsə")
        self.assertIn("## funksiya `sahə`", md)
        h = senedci.html_sənəd([f], "Həndəsə <x>")
        self.assertIn("<title>Həndəsə &lt;x&gt;</title>", h)
        self.assertIn("<h5>Nümunə</h5>", h)
        self.assertIn("girinti qorunur", h)
        self.assertNotIn("köməkçi", h)

    def test_sənəd_nümunəsi_sınanır(self):
        n = S.sənədi_sına(self.yaz("h.alq", self.KOD))
        self.assertEqual([r.vəziyyət for r in n.nəticələr], [S.UĞURLU])

    def test_cli(self):
        self.yaz("layihe.alq", '[paket]\nad = "həndəsə"\n'
                                 '[qurma]\ngiriş = "mənbə/h.alq"\n')
        self.yaz("mənbə/h.alq", self.KOD)
        c = cli("sənəd", qovluq=self.q)
        self.assertEqual(c.returncode, 0, c.stderr)
        self.assertTrue((self.q / "sənəd" / "indeks.html").is_file())
        c = cli("sənəd", "--format", "markdown", qovluq=self.q)
        self.assertIn("# həndəsə",
                      (self.q / "sənəd" / "API.md").read_text("utf-8"))


# ═══════════════════════════════════════════════════════════════════════
#  `qur`, `təmizlə`, `işlət` (layihə)
# ═══════════════════════════════════════════════════════════════════════

class QurmaSınağı(Qovluqlu):
    def setUp(self):
        super().setUp()
        L.yarat(self.q / "app", "app", "konsol")
        self.l = L.tap(self.q / "app")
        self.yaz("app/sınaq/gizli.alq", "// paketə düşməməlidir")

    def test_paket_məzmunu_və_işləməsi(self):
        n = qurucu.qur(self.l, ALQORC.parent)
        self.assertEqual(n.yol.name, "app.pyz")
        with zipfile.ZipFile(n.yol) as z:
            adlar = z.namelist()
        self.assertIn("__main__.py", adlar)
        self.assertIn("alqorc.py", adlar)
        self.assertIn("alqor/icraci.py", adlar)
        self.assertIn("layihə/mənbə/əsas.alq", adlar)
        self.assertNotIn("layihə/sınaq/gizli.alq", adlar)
        self.assertFalse(any(a.startswith("alqor/__pycache__")
                             for a in adlar))
        self.assertTrue(n.yol.read_bytes().startswith(b"#!/usr/bin/env"))

        env = dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1",
                   ALQOR_KES=str(self.q / "keş"))
        c = subprocess.run([sys.executable, str(n.yol)], input="Aysel\n",
                           capture_output=True, text=True,
                           encoding="utf-8", cwd=tempfile.gettempdir(),
                           env=env)
        self.assertEqual(c.returncode, 0, c.stderr)
        self.assertIn("Salam, Aysel!", c.stdout)

    def test_təmizlə(self):
        qurucu.qur(self.l, ALQORC.parent)
        self.assertTrue(qurucu.təmizlə(self.l))
        self.assertFalse((self.q / "app" / "qurma").exists())
        self.assertFalse(qurucu.təmizlə(self.l))

    def test_təmizlə_layihədən_kənara_çıxmır(self):
        self.yaz("app/layihe.alq", '[qurma]\nçıxış = "../kənar"\n')
        (self.q / "kənar").mkdir()
        with self.assertRaises(ValueError):
            qurucu.təmizlə(L.tap(self.q / "app"))
        self.assertTrue((self.q / "kənar").exists())

    def test_işlət_fayl_olmadan(self):
        c = cli("işlət", qovluq=self.q / "app", giriş="Rəşad\n")
        self.assertEqual(c.returncode, 0, c.stderr)
        self.assertIn("Salam, Rəşad!", c.stdout)

    def test_işlət_proqram_arqumenti_bayraq_deyil(self):
        """`--`-dan sonrakı `--tip` proqramındır, tip yoxlaması deyil."""
        self.yaz("arq.alq", "funksiya əsas(a: siyahı[mətn])\n"
                              "    yaz(a)\nson\n")
        c = cli("işlət", str(self.q / "arq.alq"), "--", "--tip", "x")
        self.assertEqual(c.stdout.strip(), '["--tip", "x"]')


# ═══════════════════════════════════════════════════════════════════════
#  Yerli fayl idxalı
# ═══════════════════════════════════════════════════════════════════════

class YerliİdxalSınağı(Qovluqlu):
    def test_yol_idxal_edən_fayla_nisbətəndir(self):
        self.yaz("lib/riyazi.alq", "funksiya iki() -> tam\n"
                                     "    qaytar 2\nson\n")
        self.yaz("app/əsas.alq",
                 'gətir "../lib/riyazi.alq" kimi r\nyaz(r.iki())\n')
        # Başqa qovluqdan işə salınır
        c = cli("işlət", str(self.q / "app" / "əsas.alq"),
                qovluq=Path(tempfile.gettempdir()))
        self.assertEqual(c.stdout.strip(), "2", c.stderr)

    def test_keş_icraçıya_bağlıdır(self):
        """İki interpretator eyni modulun vəziyyətini paylaşmır."""
        from test_icraci import işlət
        m = self.yaz("say.alq", "dəyişən n = 0\n"
                                  "funksiya artır() -> tam\n"
                                  "    n += 1\n    qaytar n\nson\n")
        kod = f'gətir "{m.as_posix()}" kimi s\nyaz(s.artır())\n'
        self.assertEqual(işlət(kod)[0], ["1"])
        self.assertEqual(işlət(kod)[0], ["1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
