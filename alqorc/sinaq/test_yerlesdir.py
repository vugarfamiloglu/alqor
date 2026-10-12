"""`alqor yerləşdir`: statik sayt və Docker server paketi."""

import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import yerlesdir as Y                          # noqa: E402
from alqor.layihe import Layihə, tap, yarat               # noqa: E402
from alqor.js.muqayise import node_tap                    # noqa: E402

KÖK = Path(__file__).resolve().parent.parent


def _layihə(q: Path, şablon: str) -> Layihə:
    yarat(q, "sınaq", şablon)
    return tap(q)


def _alqor(*arq, cwd):
    return subprocess.run(
        [sys.executable, str(KÖK / "alqorc.py"), *arq], cwd=cwd,
        capture_output=True, text=True, encoding="utf-8", timeout=180,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def _boş_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Növ(unittest.TestCase):
    def test_veb_şablonu_serverdir_konsol_deyil(self):
        with tempfile.TemporaryDirectory() as q:
            self.assertTrue(Y.serverdirmi(_layihə(Path(q) / "v", "veb")))
            self.assertFalse(Y.serverdirmi(_layihə(Path(q) / "k", "konsol")))
            # Desktop şablonu `Əsas.forma` ilədir — forma vebdə server
            # kimi işləyir (`ALQOR_VEB=1`)
            self.assertTrue(Y.serverdirmi(_layihə(Path(q) / "d", "desktop")))

    def test_pəncərəli_veb_budağı_statikdir(self):
        # 08/09 nümunələri: `gətir veb` + `gətir pəncərə` → statik
        with tempfile.TemporaryDirectory() as q:
            kök = Path(q) / "n"
            _layihə(kök, "konsol")
            (kök / "mənbə" / "əsas.alq").write_text(
                "gətir vidjet\ngətir pəncərə\ngətir veb\n", encoding="utf-8")
            self.assertFalse(Y.serverdirmi(tap(kök)))

    def test_sistem_adı(self):
        self.assertEqual(Y._sistem_adı("Mənim Saytım"), "menim-saytim")
        self.assertEqual(Y._sistem_adı("!!!"), "alqor-tetbiq")


@unittest.skipIf(node_tap() is None, "Node.js tapılmadı")
class Statik(unittest.TestCase):
    def test_konsol_layihəsi_statik_sayt_olur(self):
        with tempfile.TemporaryDirectory() as q:
            kök = Path(q).resolve() / "k"
            _layihə(kök, "konsol")
            r = _alqor("yerləşdir", cwd=kök)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Statik sayt", r.stdout)
            ç = kök / "qurma" / "yerləşdir"
            for f in ("index.html", "404.html", ".nojekyll", "YERLESDIR.md"):
                self.assertTrue((ç / f).is_file(), f)
            html = (ç / "index.html").read_text(encoding="utf-8")
            self.assertIn("<script>", html)
            self.assertIn("netlify", (ç / "YERLESDIR.md").read_text(
                encoding="utf-8").lower())

    def test_desktop_layihəsi_statik_interfeys_saytıdır(self):
        with tempfile.TemporaryDirectory() as q:
            kök = Path(q).resolve() / "d"
            _layihə(kök, "desktop")
            # Formasız desktop proqramı (vidjetlər kodla) — statik sayt
            (kök / "mənbə" / "Əsas.forma").unlink()
            (kök / "mənbə" / "Əsas.alq").write_text(
                "gətir pəncərə\ngətir vidjet\n\nkomponent Əsas\n"
                "    göstər()\n        qaytar vidjet.düymə(mətn: \"Bas\")\n"
                "    son\nson\n\nfunksiya əsas()\n"
                "    dəyişən p = yeni pəncərə.Pəncərə(\"d\", 300, 200)\n"
                "    p.məzmun(<Əsas />)\n    p.göstər()\n"
                "    pəncərə.işlət()\nson\n", encoding="utf-8")
            r = _alqor("yerləşdir", cwd=kök)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Statik sayt", r.stdout)
            html = (kök / "qurma" / "yerləşdir" / "index.html").read_text(
                encoding="utf-8")
            self.assertIn('id="alqor-kök"', html)
            self.assertIn(".v-düymə", html)            # vidjet üslubu
            self.assertIn("alqorBağla(göndər)", html)

    def test_desktop_nümunələri_statik_yerləşir(self):
        nümunələr = KÖK.parent / "numuneler"
        for ad in ("06-desktop.alq", "08-vidjetler.alq",
                   "09-tapsiriqlar.alq"):
            with self.subTest(ad), tempfile.TemporaryDirectory() as q:
                r = _alqor("yerləşdir", str(nümunələr / ad), "--çıxış",
                           str(Path(q) / "s"), cwd=q)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("Statik sayt", r.stdout)
                self.assertTrue((Path(q) / "s" / "index.html").is_file())

    def test_tək_fayl_və_çıxış_qovluğu(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q).resolve()
            (q / "salam.alq").write_text('yaz("Salam")\n', encoding="utf-8")
            r = _alqor("yerləşdir", "salam.alq", "--çıxış", "docs", cwd=q)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((q / "docs" / "index.html").is_file())

    def test_xətalı_proqram_yerləşdirilmir(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q).resolve()
            (q / "x.alq").write_text("yaz(\n", encoding="utf-8")
            r = _alqor("yerləşdir", "x.alq", cwd=q)
            self.assertEqual(r.returncode, 2)
            self.assertFalse((q / "qurma" / "yerləşdir").exists())

    def test_js_dəstəkləməyən_modul_serverə_yönləndirir(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q).resolve()
            (q / "t.alq").write_text("gətir sap\nyaz(1)\n", encoding="utf-8")
            r = _alqor("yerləşdir", "t.alq", "--statik", cwd=q)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--server", r.stderr)


class FormaLayihəsi(unittest.TestCase):
    def test_forma_server_olur_xətalı_forma_yerləşdirilmir(self):
        with tempfile.TemporaryDirectory() as q:
            kök = Path(q).resolve() / "f"
            _layihə(kök, "konsol")
            (kök / "mənbə" / "əsas.alq").write_text(
                "gətir pəncərə\nkomponent Əsas\nson\nfunksiya əsas()\n"
                "    pəncərə.formaAç(Əsas)\n    pəncərə.işlət()\nson\n",
                encoding="utf-8")
            f = kök / "mənbə" / "Əsas.forma"
            f.write_text("forma Əsas\n    obyekt D: düyme\n    son\nson\n",
                         encoding="utf-8")
            r = _alqor("yerləşdir", cwd=kök)
            self.assertEqual(r.returncode, 2)
            self.assertIn("ALQ-F003", r.stderr)
            f.write_text("forma Əsas\n    obyekt D: düymə\n"
                         '        mətn = "Bas"\n    son\nson\n',
                         encoding="utf-8")
            r = _alqor("yerləşdir", cwd=kök)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Server paketi", r.stdout)
            self.assertIn("ALQOR_VEB=1", (kök / "qurma" / "yerləşdir" /
                                         "Dockerfile").read_text())


class Server(unittest.TestCase):
    def test_veb_layihəsi_docker_paketi_və_PORT(self):
        with tempfile.TemporaryDirectory() as q:
            kök = Path(q).resolve() / "v"
            _layihə(kök, "veb")
            r = _alqor("yerləşdir", cwd=kök)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Server paketi", r.stdout)
            ç = kök / "qurma" / "yerləşdir"
            docker = (ç / "Dockerfile").read_text(encoding="utf-8")
            self.assertIn("ALQOR_HOST=0.0.0.0", docker)
            self.assertIn('CMD ["python", "/app/tetbiq.pyz"]', docker)
            self.assertIn("docker build -t sinaq",
                          (ç / "YERLESDIR.md").read_text(encoding="utf-8"))

            # Platformanın verdiyi PORT-da dinləyir
            port = _boş_port()
            p = subprocess.Popen(
                [sys.executable, str(ç / "tetbiq.pyz")], cwd=q,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=dict(os.environ, PORT=str(port),
                         ALQOR_KES=str(Path(q) / "keş")))
            try:
                cavab = None
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(
                                f"http://127.0.0.1:{port}/", timeout=2) as c:
                            cavab = c.status
                        break
                    except OSError:
                        time.sleep(0.2)
                self.assertEqual(cavab, 200)
            finally:
                p.terminate()
                p.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
