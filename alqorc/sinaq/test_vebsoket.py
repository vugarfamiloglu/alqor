"""WebSocket (RFC 6455): çərçivələr, server (`veb`), müştəri (`http`)."""

import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import vebsoket as W                              # noqa: E402
from alqor.icraci import İcraçı                              # noqa: E402

KÖK = Path(__file__).parent.parent

SERVER = """gətir veb

funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.al("/", (sorğu) => veb.mətn("adi səhifə"))
    s.soket("/əks", funksiya(soket)
        soket.hadisə("mesaj", (m) => soket.göndər("əks: {m}"))
    son)
    s.soket("/otaq/:ad", funksiya(soket)
        dəyişən otaq = soket.sorğu().parametr("ad")
        soket.otağaQoşul(otaq)
        soket.hadisə("mesaj", funksiya(m)
            soket.otağaYayımla(otaq, m)
        son)
    son)
    s.soket("/json", funksiya(soket)
        soket.göndər({"salam": [1, 2, 3]})
        soket.bağla(4000, "bitdi")
    son)
    s.dinlə(PORT)
son
"""


def _boş_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ÇərçivəSınağı(unittest.TestCase):
    def test_qəbul_açarı_RFC_nümunəsi(self):
        # RFC 6455 § 1.3
        self.assertEqual(W.qəbul_açarı("dGhlIHNhbXBsZSBub25jZQ=="),
                         "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_uzunluqlar_və_maska(self):
        for n in (0, 5, 125, 126, 65535, 65536, 70000):
            data = os.urandom(n)
            for maskalı in (False, True):
                a, b = socket.socketpair()
                try:
                    a.sendall(W.çərçivə(W.İKİLİ, data, maskalı))
                    fin, op, d = W._Oxuyucu(b).çərçivə(maskalı)
                    self.assertEqual((fin, op, d), (True, W.İKİLİ, data))
                finally:
                    a.close()
                    b.close()

    def test_maska_qaydası_pozulursa_1002(self):
        a, b = socket.socketpair()
        bağ = W.Bağlantı(b, İcraçı(), müştəri=False)
        a.sendall(W.çərçivə(W.MƏTN, b"salam", maskala=False))  # maskasız
        bağ.dövr()
        self.assertEqual(bağ.bağlanma_kodu, 1002)
        a.close()

    def test_parçalanmış_mesaj_və_pinq(self):
        a, b = socket.socketpair()
        bağ = W.Bağlantı(b, İcraçı(), müştəri=False)
        a.sendall(W.çərçivə(W.MƏTN, "sa".encode(), True, fin=False)
                  + W.çərçivə(W.PİNQ, b"p1", True)
                  + W.çərçivə(W.DAVAM, "lam ə".encode(), True)
                  + W.çərçivə(W.BAĞLA, struct.pack("!H", 1000), True))
        bağ.dövr()
        self.assertEqual(bağ.al(100), "salam ə")
        self.assertIsNone(bağ.al(100))           # bağlanıb
        self.assertEqual(bağ.bağlanma_kodu, 1000)
        cavab = W._Oxuyucu(a)
        self.assertEqual(cavab.çərçivə(False)[1:], (W.PONQ, b"p1"))
        self.assertEqual(cavab.çərçivə(False)[1], W.BAĞLA)
        a.close()


class ServerVəMüştəriSınağı(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _boş_port()
        cls.q = tempfile.TemporaryDirectory()
        f = Path(cls.q.name) / "server.alq"
        f.write_text(SERVER.replace("PORT", str(cls.port)),
                     encoding="utf-8")
        cls.p = subprocess.Popen(
            [sys.executable, str(KÖK / "alqorc.py"), "işlət", str(f)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        son = time.monotonic() + 20
        while time.monotonic() < son:
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.2).close()
                return
            except OSError:
                time.sleep(0.1)
        cls.p.kill()
        raise RuntimeError("server başlamadı: "
                           + cls.p.stderr.read().decode())

    @classmethod
    def tearDownClass(cls):
        cls.p.kill()
        cls.p.wait()
        cls.p.stdout.close()
        cls.p.stderr.close()
        cls.q.cleanup()

    def url(self, yol):
        return f"ws://127.0.0.1:{self.port}{yol}"

    def test_əks_python_müştərisi(self):
        b = W.bağlan(İcraçı(), self.url("/əks"))
        b.göndər("salam")
        self.assertEqual(b.al(5000), "əks: salam")
        b.göndər("ş" * 70000)                     # 64-bit uzunluq
        self.assertEqual(b.al(5000), "əks: " + "ş" * 70000)
        b.bağla()
        self.assertFalse(b.açıq)

    def test_otaq_yayımı(self):
        a = W.bağlan(İcraçı(), self.url("/otaq/ümumi"))
        b = W.bağlan(İcraçı(), self.url("/otaq/ümumi"))
        c = W.bağlan(İcraçı(), self.url("/otaq/başqa"))
        time.sleep(0.3)
        a.göndər("hamıya salam")
        self.assertEqual(b.al(5000), "hamıya salam")
        with self.assertRaises(Exception):
            c.al(300)                             # başqa otaq
        with self.assertRaises(Exception):
            a.al(300)                             # özünə getmir
        for x in (a, b, c):
            x.bağla()

    def test_json_və_bağlanma_kodu(self):
        b = W.bağlan(İcraçı(), self.url("/json"))
        self.assertEqual(b.al(5000), '{"salam": [1, 2, 3]}')
        self.assertIsNone(b.al(5000))
        self.assertEqual((b.bağlanma_kodu, b.bağlanma_səbəbi),
                         (4000, "bitdi"))

    def test_adi_http_və_naməlum_yol(self):
        import urllib.request
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/") as c:
            self.assertEqual(c.read().decode(), "adi səhifə")
        from alqor.deyerler import AlqorXəta
        with self.assertRaises(AlqorXəta):
            W.bağlan(İcraçı(), self.url("/yoxdur"))

    def test_alqor_müştərisi(self):
        kod = f"""gətir http
gətir vaxt

asinxron funksiya əsas()
    dəyişən sk = gözlə http.vebSoket("{self.url('/əks')}")
    sk.göndər("Bakı")
    yaz(sk.al(5000))
    dəyişən gələnlər: siyahı[mətn] = []
    sk.hadisə("mesaj", (m) => gələnlər.əlavə(m))
    sk.göndər("Gəncə")
    dəyişən i = 0
    nə qədər ki gələnlər.uzunluq() == 0 və i < 100
        vaxt.gözlə(50)
        i += 1
    son
    yaz(gələnlər[0])
    sk.bağla()
    yaz(sk.açıqdır())
son
"""
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "m.alq"
            f.write_text(kod, encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "işlət", str(f),
                 "--tip"],
                capture_output=True, text=True, encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.split("\n")[:3],
                         ["əks: Bakı", "əks: Gəncə", "yanlış"])

    def test_yanlış_sxem(self):
        from alqor.deyerler import AlqorXəta
        with self.assertRaises(AlqorXəta):
            W.bağlan(İcraçı(), f"http://127.0.0.1:{self.port}/əks")


if __name__ == "__main__":
    unittest.main()
