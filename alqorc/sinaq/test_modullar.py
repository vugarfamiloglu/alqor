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


class ŞifrəSınağı(unittest.TestCase):
    def test_aes_fips197(self):
        from alqor.modullar.sifre import _AES
        p = bytes.fromhex("00112233445566778899aabbccddeeff")
        self.assertEqual(_AES(bytes(range(32))).blok(p).hex(),
                         "8ea2b7ca516745bfeafc49904b496089")
        self.assertEqual(_AES(bytes(range(16))).blok(p).hex(),
                         "69c4e0d86a7b0430d8cdb78070b4c55a")

    def test_gcm_nist(self):
        from alqor.modullar.sifre import gcm_şifrələ
        _, t = gcm_şifrələ(bytes(32), bytes(12), b"")
        self.assertEqual(t.hex(), "530f8afbc74536b9a963b4f1c4cb738b")
        c, t = gcm_şifrələ(bytes(32), bytes(12), bytes(16))
        self.assertEqual(c.hex(), "cea7403d4d606b6e074ec5d3baf39d18")
        self.assertEqual(t.hex(), "d0d1c8a799996bf0265b98b5d48ab919")

    def test_gcm_cryptography_ilə_eynidir(self):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            self.skipTest("cryptography quraşdırılmayıb")
        from alqor.modullar.sifre import gcm_şifrələ
        for n in (0, 1, 15, 16, 17, 333):
            for nl in (12, 16):
                k, iv, pt = os.urandom(32), os.urandom(nl), os.urandom(n)
                c, t = gcm_şifrələ(k, iv, pt, b"aad")
                self.assertEqual(c + t, AESGCM(k).encrypt(iv, pt, b"aad"))

    def test_şifrələ_aç_və_dəyişiklik(self):
        from alqor.modullar import sifre as Ş
        açar = os.urandom(32)
        ş = Ş.şifrələ("məxfi ə", açar)
        self.assertEqual(Ş.şifrə_aç(ş, açar).decode(), "məxfi ə")
        self.assertNotEqual(ş, Ş.şifrələ("məxfi ə", açar))   # nonce
        pis = bytearray(ş)
        pis[20] ^= 1
        with self.assertRaises(AlqorXəta):
            Ş.şifrə_aç(bytes(pis), açar)
        with self.assertRaises(AlqorXəta):
            Ş.şifrə_aç(ş, os.urandom(32))
        with self.assertRaises(AlqorXəta):
            Ş.şifrələ("x", "mətn açar")

    def test_parol(self):
        from alqor.modullar import sifre as Ş
        h = Ş.parol_heş("gizli")
        self.assertTrue(h.startswith("$scrypt$"))
        self.assertTrue(Ş.parol_yoxla("gizli", h))
        self.assertFalse(Ş.parol_yoxla("Gizli", h))
        self.assertFalse(Ş.parol_yoxla("gizli", "$scrypt$pozuq"))
        self.assertNotEqual(h, Ş.parol_heş("gizli"))          # duz

    def test_jwt(self):
        from alqor.modullar import sifre as Ş
        t = Ş.jwt_yarat({"id": 5, "ad": "Aysel"}, "a", müddət=60)
        self.assertEqual(Ş.jwt_oxu(t, "a")["ad"], "Aysel")
        for pis in (t, Ş.jwt_yarat({"id": 1}, "a", müddət=-10)):
            with self.assertRaises(AlqorXəta):
                Ş.jwt_oxu(pis, "b" if pis is t else "a")
        # alg: none hücumu
        b, g, _ = t.split(".")
        import base64
        none = base64.urlsafe_b64encode(
            b'{"alg":"none"}').decode().rstrip("=")
        with self.assertRaises(AlqorXəta):
            Ş.jwt_oxu(f"{none}.{g}.", "a")

    def test_heş(self):
        from alqor.modullar import sifre as Ş
        self.assertEqual(Ş.heş("abc"), "ba7816bf8f01cfea414140de5dae2223"
                                       "b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(len(Ş.heş("abc", "sha512")), 128)
        with self.assertRaises(AlqorXəta):
            Ş.heş("x", "md4")


class HTTPSınağı(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import http.server
        import json
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _cavab(self, kod, b, növ="application/json"):
                self.send_response(kod)
                self.send_header("Content-Type", növ)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                try:
                    self.wfile.write(b)
                except BrokenPipeError:          # müştəri vaxtı bitib getdi
                    pass

            def do_GET(self):
                if self.path == "/y":
                    self.send_response(302)
                    self.send_header("Location", "/j")
                    self.end_headers()
                elif self.path == "/404":
                    self._cavab(404, b"yox", "text/plain")
                elif self.path == "/yavas":
                    import time
                    time.sleep(1.5)
                    self._cavab(200, b"{}")
                else:
                    self._cavab(200, json.dumps({
                        "yol": self.path,
                        "a": self.headers.get("X-A")}).encode())

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                self._cavab(201, json.dumps({
                    "n": self.headers.get("Content-Type"),
                    "g": self.rfile.read(n).decode()}).encode())
            do_PUT = do_PATCH = do_DELETE = do_POST

        cls.s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        cls.U = f"http://127.0.0.1:{cls.s.server_port}"
        threading.Thread(target=cls.s.serve_forever, daemon=True).start()
        os.environ["NO_PROXY"] = "127.0.0.1,localhost"

    @classmethod
    def tearDownClass(cls):
        cls.s.shutdown()
        cls.s.server_close()

    def m(self):
        from alqor.modullar import http_
        return http_

    def test_al_göndər(self):
        H = self.m()
        c = H._sorğu("GET", self.U + "/a", parametrlər={"q": "çay"},
                     başlıqlar={"X-A": "1"}).icra()
        self.assertEqual(c.kod, 200)
        self.assertEqual(c.json(), {"yol": "/a?q=%C3%A7ay", "a": "1"})
        c = H._sorğu("POST", self.U + "/b", json={"ad": "Ə"}).icra()
        self.assertEqual(c.kod, 201)
        self.assertEqual(c.json()["g"], '{"ad": "Ə"}')
        c = H._sorğu("PUT", self.U + "/b", forma={"a": "ə b"}).icra()
        self.assertEqual(c.json()["g"], "a=%C9%99+b")

    def test_yönləndirmə_404_vaxt(self):
        H = self.m()
        self.assertTrue(H._sorğu("GET", self.U + "/y").icra().url
                        .endswith("/j"))
        c = H._sorğu("GET", self.U + "/404").icra()
        self.assertEqual((c.kod, c.uğurlu()), (404, False))
        with self.assertRaises(AlqorXəta) as k:
            c.yoxla()
        self.assertEqual(k.exception.tip, "HTTPXətası")
        with self.assertRaises(AlqorXəta) as k:
            H._sorğu("GET", self.U + "/yavas", vaxtLimiti=200).icra()
        self.assertEqual(k.exception.tip, "VaxtBitdiXətası")
        with self.assertRaises(AlqorXəta) as k:
            H._sorğu("GET", "http://127.0.0.1:1/").icra()
        self.assertEqual(k.exception.tip, "BağlantıXətası")

    def test_yalnız_http(self):
        H = self.m()
        for u in ("file:///etc/passwd", "ftp://x.az/a", "javascript:1"):
            with self.assertRaises(AlqorXəta):
                H.Sorğu("AL", u)


class VerilənlərSınağı(unittest.TestCase):
    def setUp(self):
        from alqor.modullar import verilenler as V
        self.V = V
        self.b = V.bağlan("sqlite::yaddaş:")
        self.b.icra("CREATE TABLE t (id INTEGER PRIMARY KEY, ad TEXT "
                    "UNIQUE, bal INTEGER CHECK (bal >= 0))")
        q = V.Qurucu(self.b, "t")
        for ad, bal in (("Aysel", 95), ("Kamran", 88), ("Elşən", 60)):
            q.əlavə_et({"ad": ad, "bal": bal})
        self.q = q

    def test_parametrlər_və_inyeksiya(self):
        self.assertEqual(self.b.bir_dəyər(
            "SELECT bal FROM t WHERE ad = $1", "Aysel"), 95)
        self.assertEqual(self.b.sorğu(
            "SELECT ad FROM t WHERE ad = $1", "x' OR '1'='1"), [])
        self.assertEqual(self.V._dollar("SELECT '$1', $2"),
                         "SELECT '$1', ?2")
        with self.assertRaises(AlqorXəta):
            self.V.Qurucu(self.b, "t; DROP TABLE t")
        with self.assertRaises(AlqorXəta):
            self.q.harada("bal", "; DROP", 1)

    def test_qurucu(self):
        q = self.q
        self.assertEqual([s["ad"] for s in q.harada("bal", ">", 70)
                          .sırala("bal", "azalan").al()],
                         ["Aysel", "Kamran"])
        self.assertEqual(q.harada("ad", "içində", ["Aysel", "X"]).say(), 1)
        self.assertEqual(q.harada("ad", "bənzər", "K%").ilk()["bal"], 88)
        self.assertEqual(q.sırala("id").limit(1).atla(1).al()[0]["ad"],
                         "Kamran")
        self.assertEqual(q.harada("ad", "=", "Elşən").yenilə({"bal": 1}), 1)
        self.assertEqual(q.harada("bal", "<", 10).sil(), 1)
        with self.assertRaises(AlqorXəta):
            q.sil()
        with self.assertRaises(AlqorXəta):
            q.yenilə({"bal": 0})

    def test_məhdudiyyət(self):
        with self.assertRaises(AlqorXəta) as k:
            self.q.əlavə_et({"ad": "Aysel", "bal": 1})
        self.assertEqual(k.exception.tip, "MəhdudiyyətXətası")

    def test_miqrasiya(self):
        with tempfile.TemporaryDirectory() as q:
            Path(q, "001_a.sql").write_text(
                "CREATE TABLE a (x INT);", encoding="utf-8")
            Path(q, "002_pis.sql").write_text(
                "INSERT INTO a VALUES (1); CREATE TABL;", encoding="utf-8")
            with self.assertRaises(AlqorXəta):
                self.b.miqrasiya(q)
            # 001 tətbiq olundu, 002 tam geri qaytarıldı
            self.assertEqual(self.b.bir_dəyər("SELECT COUNT(*) FROM a"), 0)
            Path(q, "002_pis.sql").write_text(
                "INSERT INTO a VALUES (1);", encoding="utf-8")
            self.assertEqual(self.b.miqrasiya(q), ["002_pis.sql"])
            self.assertEqual(self.b.miqrasiya(q), [])


class ŞəbəkəSınağı(unittest.TestCase):
    def test_tcp_udp(self):
        ç = işlət('gətir şəbəkə\n'
                  'dəyişən s = şəbəkə.TCPServer(0, (k) => '
                  'k.göndər("Salam, " + k.sətirAl() + "\\n")).başlat()\n'
                  'dəyişən k = şəbəkə.TCPBağlan("127.0.0.1", s.port())\n'
                  'k.göndər("Aysel\\n")\nyaz(k.sətirAl())\n'
                  'k.bağla()\ns.dayandır()\n'
                  'dəyişən a = şəbəkə.UDPSoket()\n'
                  'dəyişən b = şəbəkə.UDPSoket()\n'
                  'a.göndər("ping", "127.0.0.1", b.port())\n'
                  'yaz(b.al()["verilən"])\n')
        self.assertEqual(ç.split("\n")[:2], ["Salam, Aysel", 'b"ping"'])


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
