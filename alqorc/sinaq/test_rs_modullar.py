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
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Əks)
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


if __name__ == "__main__":
    unittest.main()
