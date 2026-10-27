"""
Rust icraçısının əlavə standart modulları (`alqor-rs/src/icraci/mod_*.rs`)
— Python etalonu ilə diferensial müqayisə.

    sinaq/rs_modul_parcalari.alq   `=====` ilə ayrılmış parçalar: stdout,
                                   stderr və çıxış kodu tam eyni olmalıdır

Şəbəkə (http, veb) və verilənlər bazası sınaqları yerli serverlə və
müvəqqəti SQLite faylları ilə aparılır — internet lazım deyil.
"""

import json
import os
import shutil
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.rs import muqayise as M                        # noqa: E402

PARÇALAR = Path(__file__).parent / "rs_modul_parcalari.alq"
ŞƏBƏKƏ_PARÇALARI = Path(__file__).parent / "rs_sebeke_parcalari.alq"


class _SəssizServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass                    # vaxtı bitmiş müştərilər — səs-küy yox


class _Əks(BaseHTTPRequestHandler):
    """Sınaq serveri: sorğunu JSON kimi qaytarır (`/əks`), statuslar,
    yönləndirmə, gecikmə, fayl."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _cavab(self, kod, gövdə, tip="application/json; charset=utf-8",
               başlıqlar=()):
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(gövdə)))
        for a, d in başlıqlar:
            self.send_header(a, d)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(gövdə)

    def _işlə(self):
        from urllib.parse import unquote, urlsplit
        u = urlsplit(self.path)
        yol = unquote(u.path)
        n = int(self.headers.get("Content-Length") or 0)
        gövdə = self.rfile.read(n) if n else b""
        if yol.startswith("/kod/"):
            k = int(yol[5:])
            return self._cavab(k, f"kod {k}".encode(), "text/plain")
        if yol == "/yönləndir":
            return self._cavab(302, b"", "text/plain",
                               [("Location", "/%C9%99ks?y=1")])
        if yol == "/yavaş":
            time.sleep(1.5)
            return self._cavab(200, b"gec", "text/plain")
        if yol == "/fayl":
            return self._cavab(200, bytes(range(256)) * 1000,
                               "application/octet-stream")
        if yol == "/latin":
            return self._cavab(200, "Ağ".encode("latin-1", "replace"),
                               "text/plain; charset=iso-8859-1")
        if yol == "/pis-json":
            return self._cavab(200, b"{x", "application/json")
        b = {k.lower(): v for k, v in self.headers.items()
             if k.lower() in ("content-type", "x-ad", "authorization",
                              "accept-encoding", "user-agent")}
        b["user-agent"] = b.get("user-agent", "").split("/")[0]
        g = gövdə.decode("utf-8", "replace")
        if g.startswith("--alqor-"):
            g = "multipart " + str(len(gövdə))
        self._cavab(200, json.dumps(
            {"metod": self.command, "yol": yol, "sorğu": u.query,
             "başlıqlar": dict(sorted(b.items())), "gövdə": g},
            ensure_ascii=False).encode(), başlıqlar=[("X-Server", "sinaq")])

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _işlə


def _binar():
    if shutil.which("cargo") or (Path.home() / ".cargo" / "bin" / "cargo").exists():
        return M.qur()
    return M.binar()


_B = _binar()


@unittest.skipIf(_B is None, "cargo / alqor-rs mövcud deyil")
class RustModulMüqayisəsi(unittest.TestCase):
    def test_modul_parçaları(self):
        fərqlər: list[str] = []
        eyni, cəmi = M.parçalar_işlət(_B, PARÇALAR, çıxış=fərqlər.append)
        self.assertEqual(eyni, cəmi, "\n".join(fərqlər))

    def test_şəbəkə_parçaları(self):
        """http, şəbəkə, veb — yerli sınaq serveri ilə (internet lazım deyil)."""
        server = _SəssizServer(("127.0.0.1", 0), _Əks)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        köhnə = os.environ.get("ALQOR_SINAQ_URL")
        os.environ["ALQOR_SINAQ_URL"] = \
            f"http://127.0.0.1:{server.server_address[1]}"
        try:
            fərqlər: list[str] = []
            eyni, cəmi = M.parçalar_işlət(_B, ŞƏBƏKƏ_PARÇALARI,
                                          çıxış=fərqlər.append)
            self.assertEqual(eyni, cəmi, "\n".join(fərqlər))
        finally:
            server.shutdown()
            if köhnə is None:
                os.environ.pop("ALQOR_SINAQ_URL", None)
            else:
                os.environ["ALQOR_SINAQ_URL"] = köhnə

    def test_veb_server_dinlə(self):
        """`server.dinlə()` — həqiqi HTTP üzərindən Python və Rust eyni cavab verir."""
        import socket
        import subprocess
        import tempfile
        import urllib.error
        import urllib.request
        q = Path(tempfile.mkdtemp(prefix="alqor-veb-"))
        (q / "server.alq").write_text(_VEB_SERVERİ, encoding="utf-8")

        def boş_port():
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        def işlət(əmr):
            port = boş_port()
            env = dict(os.environ, PORT=str(port), PYTHONIOENCODING="utf-8")
            p = subprocess.Popen(əmr + [str(q / "server.alq")], cwd=q, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for _ in range(200):
                    try:
                        socket.create_connection(("127.0.0.1", port), 0.1).close()
                        break
                    except OSError:
                        time.sleep(0.05)
                n = []
                for metod, yol, gövdə in (("GET", "/", None), ("GET", "/salam/%C6%8Fli?x=1", None),
                                          ("POST", "/json", b'{"a": [1, 2]}'), ("GET", "/yox", None),
                                          ("DELETE", "/", None), ("GET", "/x", None), ("HEAD", "/", None),
                                          ("GET", "/xəta", None)):
                    r = urllib.request.Request(
                        f"http://127.0.0.1:{port}{urllib.parse.quote(yol, safe='/%?=')}",
                        data=gövdə, method=metod,
                        headers={"Content-Type": "application/json"})
                    try:
                        c = urllib.request.urlopen(r, timeout=10)
                    except urllib.error.HTTPError as x:
                        c = x
                    b = {k: v for k, v in c.headers.items() if k not in ("Date",)}
                    n.append((c.status, b, c.read()))
                return n
            finally:
                p.kill()
                p.communicate()

        import urllib.parse
        py = işlət([sys.executable, str(M.REPO / "alqorc" / "alqorc.py"), "işlət"])
        rs = işlət([str(_B), "işlət"])
        for a, b in zip(py, rs):
            b[1].pop("Connection", None)
            self.assertEqual(a, b)


@unittest.skipIf(_B is None, "cargo / alqor-rs mövcud deyil")
class MotorSeçimi(unittest.TestCase):
    """`alqor işlət --motor py|rs|avto` (alqor/motor.py)."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.q = Path(tempfile.mkdtemp(prefix="alqor-motor-"))
        cls.köhnə = os.environ.get("ALQOR_RS")
        os.environ["ALQOR_RS"] = str(_B)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.q, ignore_errors=True)
        if cls.köhnə is None:
            os.environ.pop("ALQOR_RS", None)
        else:
            os.environ["ALQOR_RS"] = cls.köhnə

    def seçim(self, kod: str, ad: str = "p.alq") -> str:
        from alqor import motor
        f = self.q / ad
        f.write_text(kod, encoding="utf-8")
        return motor.seç("avto", motor._ayır(f), f)[0]

    def test_rs_seçilir(self):
        for kod in ('yaz(1)\n', 'gətir şifrə\nyaz(şifrə.heş("a"))\n',
                    'gətir riyaziyyat.{kök}\nyaz(kök(4))\n',
                    'dəyişən s = yeni veb.Server()\n',
                    'gətir http kimi h\nyaz(h)\n'):
            self.assertEqual(self.seçim(kod), "rs", kod)

    def test_python_seçilir(self):
        for kod in ('gətir yaml\n', 'gətir python:math\n',
                    'pəncərə.başlıq("x")\n', 'vidjet.düymə(mətn: "a")\n',
                    'dəyişən s = yeni veb.Server()\ns.komponent("/", 1)\n',
                    'gətir naməlumPaket\n', 'gətir "./yoxdur.alq"\n',
                    'gətir verilənlər\nsinif A miras verilənlər.Model\nson\n'):
            self.assertEqual(self.seçim(kod), "py", kod)

    def test_yerli_modul_rekursiv(self):
        (self.q / "alt.alq").write_text("gətir yaml\n", encoding="utf-8")
        (self.q / "orta.alq").write_text('gətir "./alt.alq"\n',
                                         encoding="utf-8")
        self.assertEqual(self.seçim('gətir "./orta.alq" kimi o\n'), "py")
        (self.q / "alt.alq").write_text("dəyişən x = 1\n",
                                        encoding="utf-8")
        self.assertEqual(self.seçim('gətir "./orta.alq" kimi o\n'), "rs")

    def test_cli_motorları_eyni_nəticə(self):
        import subprocess
        f = self.q / "cli.alq"
        f.write_text('gətir kodlaşdırma\nyaz(kodlaşdırma.slug("Şəki"), '
                     'sistem.arqumentlər())\nyaz(oxu())\n', encoding="utf-8")
        n = {}
        for m in ("py", "rs", "avto"):
            r = subprocess.run(
                [sys.executable, str(M.REPO / "alqorc" / "alqorc.py"), "işlət",
                 "--motor", m, str(f), "--", "a", "b"],
                input="dünya\n".encode(), capture_output=True,
                env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            n[m] = (r.returncode, r.stdout.decode("utf-8"))
        self.assertEqual(n["py"], (0, 'seki ["a", "b"]\ndünya\n'))
        self.assertEqual(n["rs"], n["py"])
        self.assertEqual(n["avto"], n["py"])

    def test_naməlum_motor(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(M.REPO / "alqorc" / "alqorc.py"), "işlət",
             "--motor", "xyz", "x.alq"], capture_output=True)
        self.assertEqual(r.returncode, 3)


_VEB_SERVERİ = """\
dəyişən s = yeni veb.Server()
s.al("/", (r) => veb.mətn("Salam!"))
s.al("/salam/:ad", (r) => {"ad": r.parametr("ad"), "x": r.sorğuParametr("x")})
s.göndər("/json", (r) => r.json())
s.al("/x", (r) => veb.mətn("x").kuki("a", "b").başlıq("X-Y", "z"))
s.al("/xəta", (r) => 1 / 0)
s.dinlə()
"""


if __name__ == "__main__":
    unittest.main()
