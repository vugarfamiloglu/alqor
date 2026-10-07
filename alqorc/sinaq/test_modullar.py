"""Əlavə standart modullar (`alqor/modullar/`)."""

import io
import math
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import modullar                                   # noqa: E402
from alqor.deyerler import AlqorXəta                         # noqa: E402
from alqor.modullar import (csv_, html_, konfiq, kodlasdirma,  # noqa: E402
                            sixma, toml_, xml_, yaml_)

KÖK = Path(__file__).parent.parent


def işlət(kod: str, qovluq: str | None = None, mühit=None) -> str:
    with tempfile.TemporaryDirectory() as q:
        q = qovluq or q
        f = Path(q) / "p.alqor"
        f.write_text(kod, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(KÖK / "alqorc.py"), "işlət", str(f)],
            capture_output=True, text=True, encoding="utf-8", cwd=q,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", **(mühit or {})},
            timeout=60)
        if r.returncode != 0:
            raise AssertionError(r.stdout + r.stderr)
        return r.stdout


class QeydSınağı(unittest.TestCase):
    def test_hər_modulun_tipi_və_icrası_uyğundur(self):
        """Tip imzaları icra üzvləri ilə eyni adları daşımalıdır."""
        class Saxta:
            pass
        for ad in modullar.adlar():
            icra = modullar._py(ad).qur(Saxta())
            tip = modullar.modul_tipi(ad).üzvlər
            self.assertEqual(sorted(icra), sorted(tip), ad)

    def test_tip_yoxlayıcısı_tanıyır(self):
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.tipyoxlayici import tipləri_yoxla
        from alqor.xeta import XətaToplayıcı
        x = XətaToplayıcı()
        m = Mənbə.mətndən('gətir xml\ndəyişən d = xml.oxu("<a/>")\n'
                          'yaz(d.tap("b").mətn())\nyaz(xml.yox())\n')
        tipləri_yoxla(Parser(Lekser(m, x).leksə(), m, x).ayır(), x)
        kodlar = [d.kod for d in x.siyahı]
        self.assertIn("ALQ-T013", kodlar)        # `tap` → düyün?
        self.assertIn("ALQ-M002", kodlar)        # olmayan üzv


class KodlaşdırmaSınağı(unittest.TestCase):
    def setUp(self):
        self.m = kodlasdirma.qur(None)

    def ç(self, ad, *a):
        return self.m[ad].f(*a)

    def test_base64_hex_url(self):
        self.assertEqual(self.ç("base64Kodla", "Salam"), "U2FsYW0=")
        self.assertEqual(self.ç("base64AçMətn", "U2FsYW0="), "Salam")
        self.assertEqual(self.ç("base64URLAç",
                                self.ç("base64URLKodla", b"\xff\xfe")),
                         b"\xff\xfe")
        self.assertEqual(self.ç("hexAç", self.ç("hexKodla", "ə")),
                         "ə".encode())
        self.assertEqual(self.ç("urlKodla", "ə ş/"), "%C9%99%20%C5%9F%2F")
        self.assertEqual(self.ç("sorğuAç", "a=1&b=x&b=y"),
                         {"a": "1", "b": ["x", "y"]})
        with self.assertRaises(AlqorXəta):
            self.ç("base64Aç", "!!!")

    def test_slug(self):
        self.assertEqual(kodlasdirma.slug("Şəki Xan Sarayı — 1762!"),
                         "seki-xan-sarayi-1762")


class CSVSınağı(unittest.TestCase):
    def test_oxu_çevir_avto(self):
        self.assertEqual(
            csv_.oxu("ad;bal;aktiv\nAysel;95;doğru\n", ayırıcı="avto",
                     çevir=True),
            [{"ad": "Aysel", "bal": 95, "aktiv": True}])

    def test_dırnaqlar_və_yeni_sətir(self):
        mətn = csv_.yaz([{"a": 'x, "y"', "b": "bir\niki"}])
        self.assertEqual(csv_.oxu(mətn), [{"a": 'x, "y"', "b": "bir\niki"}])

    def test_başlıqsız_və_bom(self):
        self.assertEqual(csv_.oxu("\ufeff1,2\n3,4\n", başlıq=False),
                         [["1", "2"], ["3", "4"]])
        self.assertTrue(csv_.yaz([[1]], bom=True).startswith("\ufeff"))

    def test_xətalar(self):
        with self.assertRaises(AlqorXəta):
            csv_.oxu("a,a\n1,2\n")
        with self.assertRaises(AlqorXəta):
            csv_.oxu("a\n1,2\n")


class TOMLSınağı(unittest.TestCase):
    def test_gediş_dönüş(self):
        d = {"ad": "Alqor", "versiya": 1.5, "aktiv": True,
             "dillər": ["az", "en"], "server": {"port": 8080,
                                                "tls": {"var": False}},
             "istifadəçi": [{"ad": "a"}, {"ad": "b", "rollar": ["x"]}],
             "boş_cədvəl": {}, "mətn": 'qoşa "dırnaq"\nsətir'}
        self.assertEqual(toml_.oxu(toml_.yaz(d)), d)

    def test_tarix_mətn_olur(self):
        self.assertEqual(toml_.oxu("t = 2026-10-07T10:00:00")["t"],
                         "2026-10-07T10:00:00")

    def test_xəta(self):
        with self.assertRaises(AlqorXəta) as k:
            toml_.oxu("a = ")
        self.assertEqual(k.exception.tip, "TOMLXətası")


class YAMLSınağı(unittest.TestCase):
    def test_konfiqurasiya_faylı(self):
        mətn = """
# docker-compose
version: '3.8'
services:
  veb: &baza
    image: "nginx:1.25"
    ports:
      - "80:80"
    environment:
      - DEBUG=0
  ikinci:
    <<: *baza
    ports: [8080, 8443]
təsvir: |
  Bir
  iki
qatlanmış: >-
  bir
  iki
"""
        d = yaml_.oxu(mətn)
        self.assertEqual(d["version"], "3.8")
        self.assertEqual(d["services"]["veb"]["ports"], ["80:80"])
        self.assertEqual(d["services"]["ikinci"]["image"], "nginx:1.25")
        self.assertEqual(d["services"]["ikinci"]["ports"], [8080, 8443])
        self.assertEqual(d["təsvir"], "Bir\niki\n")
        self.assertEqual(d["qatlanmış"], "bir iki")

    def test_skalyarlar(self):
        d = yaml_.oxu("a: ~\nb: true\nc: 0x10\nd: -.inf\ne: '007'\n"
                      "f: yes\ng: 1e3\n")
        self.assertEqual(d["a"], None)
        self.assertIs(d["b"], True)
        self.assertEqual(d["c"], 16)
        self.assertEqual(d["d"], -math.inf)
        self.assertEqual(d["e"], "007")
        self.assertEqual(d["f"], "yes")          # YAML 1.2: mətndir
        self.assertEqual(d["g"], 1000.0)

    def test_yığcam_və_iç_içə(self):
        self.assertEqual(
            yaml_.oxu("- ad: a\n  say: 1\n- - x\n  - y\n- {b: [1, 2]}\n"),
            [{"ad": "a", "say": 1}, ["x", "y"], {"b": [1, 2]}])

    def test_bir_neçə_sənəd(self):
        self.assertEqual(yaml_.oxu_hamısı("a: 1\n---\nb: 2\n"),
                         [{"a": 1}, {"b": 2}])
        with self.assertRaises(AlqorXəta):
            yaml_.oxu("a: 1\n---\nb: 2\n")

    def test_gediş_dönüş(self):
        d = {"ad": "Alqor", "rəqəm": "42", "boş": None, "bayraq": "true",
             "siyahı": [1, {"a": [2, 3]}, [4]], "mətn": "bir\niki\n",
             "iki_nöqtə": "a: b", "boş_mətn": "", "boş_siyahı": [],
             "tire": "-x", "ə": {"ş": "ç"}}
        self.assertEqual(yaml_.oxu(yaml_.yaz(d)), d)

    def test_xətalar_sətir_nömrəsi_ilə(self):
        for mətn, söz in [("a: 1\n  b: 2\n", "sətir 2"),
                          ("a: [1, 2\n", "bağlanmayıb"),
                          ("a: 1\na: 2\n", "təkrarlanır"),
                          ("a:\n\tb: 1\n", "TAB"),
                          ("a: *yox\n", "ankoru")]:
            with self.assertRaises(AlqorXəta) as k:
                yaml_.oxu(mətn)
            self.assertIn(söz, k.exception.mesaj)
            self.assertEqual(k.exception.tip, "YAMLXətası")


class XMLSınağı(unittest.TestCase):
    def test_oxu_seçici(self):
        k = xml_.oxu('<k xmlns="http://x"><a id="1"><b>B</b></a>'
                     '<a id="2" class="z y"/></k>')
        self.assertEqual(k.ad_, "k")
        self.assertEqual([d.atr["id"] for d in k.tap_hamısı("a")],
                         ["1", "2"])
        self.assertEqual(k.tap("a > b").mətn(), "B")
        self.assertEqual(k.tap("a.y").atr["id"], "2")
        self.assertEqual(k.tap("[id=2]").atr["id"], "2")
        self.assertIsNone(k.tap("c"))

    def test_entity_rədd_edilir(self):
        with self.assertRaises(AlqorXəta) as k:
            xml_.oxu('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                     '<a>&x;</a>')
        self.assertIn("ENTITY", k.exception.mesaj)

    def test_yaz_qaçış_lüğət(self):
        e = xml_.element("a", {"x": 'q"<'}, ["1 < 2 & 3"])
        self.assertEqual(e.xml(), '<a x="q&quot;&lt;">1 &lt; 2 &amp; 3</a>')
        self.assertEqual(xml_.oxu(e.xml()).mətn(), "1 < 2 & 3")
        d = {"@v": "1", "ad": ["x", "y"], "iç": {"#mətn": "t", "@q": "2"}}
        self.assertEqual(xml_.lüğətdən(d).lüğət(), d)

    def test_pozulmuş(self):
        with self.assertRaises(AlqorXəta) as k:
            xml_.oxu("<a><b></a>")
        self.assertIn("sətir 1", k.exception.mesaj)


class HTMLSınağı(unittest.TestCase):
    def test_avtomatik_bağlanma(self):
        s = html_.oxu("<ul><li>a<li>b</ul><p>bir<p>iki<br>üç")
        self.assertEqual([d.mətn() for d in s.tap_hamısı("li")], ["a", "b"])
        self.assertEqual([d.mətn() for d in s.tap_hamısı("p")],
                         ["bir", "ikiüç"])

    def test_mətnə(self):
        self.assertEqual(html_.mətnə("<h1>Başlıq</h1><p>Salam <b>dünya"
                                     "</b></p><script>x()</script>"),
                         "Başlıq\n\nSalam dünya")

    def test_təmizlə_xss(self):
        pis = ('<img src=x onerror="alert(1)"><a href="jav&#x09;ascript:'
               'alert(1)">a</a><script>alert(1)</script><svg onload=x>'
               '<b>qalın</b><a href="https://az">ok</a>'
               '<iframe src="//pis"></iframe>')
        t = html_.təmizlə(pis)
        for söz in ("onerror", "javascript", "script", "onload", "iframe",
                    "svg"):
            self.assertNotIn(söz, t.lower())
        self.assertIn("<b>qalın</b>", t)
        self.assertIn('href="https://az"', t)

    def test_təmizlə_mətni_qaçır(self):
        self.assertEqual(html_.təmizlə("1 < 2 &amp; <i>x</i>",
                                       teqlər=["i"]),
                         "1 &lt; 2 &amp; <i>x</i>")


class KonfiqSınağı(unittest.TestCase):
    def test_env(self):
        d = konfiq.env_oxu('# şərh\nexport A=1\nB="bir\\niki"\n'
                           "C='${A}'\nD=${A}2 # şərh\nE=\"çox\nsətir\"\n")
        self.assertEqual(d, {"A": "1", "B": "bir\niki", "C": "${A}",
                             "D": "12", "E": "çox\nsətir"})

    def test_fayllar_birləşir_və_mühit(self):
        with tempfile.TemporaryDirectory() as q:
            a = Path(q) / "əsas.toml"
            b = Path(q) / "yerli.yaml"
            a.write_text('[server]\nport = 80\nhost = "a"\n',
                         encoding="utf-8")
            b.write_text("server:\n  host: b\n", encoding="utf-8")
            os.environ["TƏTBİQ_SERVER_PORT"] = "9000"
            try:
                k = konfiq.oxu([str(a), str(b)], mühit="TƏTBİQ")
            finally:
                del os.environ["TƏTBİQ_SERVER_PORT"]
            self.assertEqual(k.d, {"server": {"port": 9000, "host": "b"}})
            self.assertEqual(k.tipli("server.port", 0, "tam"), 9000)
            with self.assertRaises(AlqorXəta):
                k.tələb("verilənlər.url")
            with self.assertRaises(AlqorXəta):
                k.tipli("server.host", 0, "tam")

    def test_ini(self):
        with tempfile.TemporaryDirectory() as q:
            p = Path(q) / "a.ini"
            p.write_text("[baza]\nport = 5432\naktiv = bəli\n",
                         encoding="utf-8")
            self.assertEqual(konfiq.fayl_oxu(str(p)),
                             {"baza": {"port": 5432, "aktiv": True}})


class SıxmaSınağı(unittest.TestCase):
    def test_gzip(self):
        m = sixma.qur(None)
        b = m["gzipSıx"].f("salam " * 100)
        self.assertLess(len(b), 100)
        self.assertEqual(m["gzipAçMətn"].f(b), "salam " * 100)
        with self.assertRaises(AlqorXəta):
            m["gzipAç"].f(b"pis")

    def test_zip_tar_gediş_dönüş(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q)
            (q / "qov" / "iç").mkdir(parents=True)
            (q / "qov" / "iç" / "ə.txt").write_text("ş", encoding="utf-8")
            (q / "b.txt").write_text("b", encoding="utf-8")
            for ad, yarat, aç in (("a.zip", sixma.zip_yarat, sixma.zip_aç),
                                  ("a.tar.gz", sixma.tar_yarat,
                                   sixma.tar_aç)):
                self.assertEqual(yarat(str(q / ad), [str(q / "qov"),
                                                     str(q / "b.txt")]), 2)
                hədəf = q / ("ç" + ad)
                aç(str(q / ad), str(hədəf))
                self.assertEqual((hədəf / "qov" / "iç" / "ə.txt").read_text(
                    encoding="utf-8"), "ş")

    def test_zip_slip_rədd_edilir(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q)
            with zipfile.ZipFile(q / "pis.zip", "w") as z:
                z.writestr("../../kənar.txt", "x")
            with self.assertRaises(AlqorXəta):
                sixma.zip_aç(str(q / "pis.zip"), str(q / "h"))
            self.assertFalse((q.parent / "kənar.txt").exists())

    def test_tar_keçidi_rədd_edilir(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q)
            with tarfile.open(q / "pis.tar", "w") as t:
                i = tarfile.TarInfo("keçid")
                i.type = tarfile.SYMTYPE
                i.linkname = "/etc/passwd"
                t.addfile(i)
            with self.assertRaises(AlqorXəta):
                sixma.tar_aç(str(q / "pis.tar"), str(q / "h"))


class AlqorKoduSınağı(unittest.TestCase):
    def test_gətir_və_istifadə(self):
        ç = işlət('gətir csv\ngətir yaml\ngətir html\n'
                  'dəyişən c = csv.oxu("a,b\\n1,2\\n", çevir: doğru)\n'
                  'yaz(c[0]["b"] + 1)\n'
                  'yaz(yaml.oxu("x: [1, 2]")["x"])\n'
                  'yaz(html.oxu("<p>salam</p>").tap("p")?.mətn())\n'
                  'cəhd et\n    yaml.oxu("a: [")\n'
                  'tut (x: FormatXətası)\n    yaz("tutuldu", x.tip)\nson\n')
        self.assertEqual(ç.split("\n")[:4],
                         ["3", "[1, 2]", "salam", "tutuldu YAMLXətası"])


if __name__ == "__main__":
    unittest.main()
