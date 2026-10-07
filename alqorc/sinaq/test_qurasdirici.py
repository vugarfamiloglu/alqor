"""Quraşdırıcı generatoru: .deb, Windows zip + Inno Setup, macOS .app."""

import io
import os
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import qurasdirici as Q                           # noqa: E402

KÖK = Path(__file__).parent.parent


def _ar(d: bytes) -> dict[str, bytes]:
    assert d.startswith(b"!<arch>\n")
    i, n = 8, {}
    while i < len(d):
        ad = d[i:i + 16].decode().strip()
        ölçü = int(d[i + 48:i + 58].decode().strip())
        n[ad] = d[i + 60:i + 60 + ölçü]
        i += 60 + ölçü + (ölçü % 2)
    return n


class QuraşdırıcıSınağı(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = Path(tempfile.mkdtemp())
        cls.pyz = cls.q / "t.pyz"
        with zipfile.ZipFile(cls.pyz, "w") as z:
            z.writestr("__main__.py", "print('salam')\n")
        res = KÖK / "alqor" / "resurslar"
        cls.t = Q.Tətbiq(
            ad="Kitab Rəfi", başlıq="Kitab Rəfi", versiya="1.2.0",
            pyz=cls.pyz, təsvir="Kitabxana", naşir="Aysel",
            png=res / "ikon-256.png", ico=res / "alqor.ico", konsol=False,
            uzantılar=[".kitab"])
        cls.fayllar = Q.qur(cls.t, cls.q / "qurma")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.q, ignore_errors=True)

    def test_sistem_adı(self):
        self.assertEqual(self.t.sistem_adı, "kitab-refi")
        self.assertEqual(Q.Tətbiq("Şəki Çay", "", "x", self.pyz)
                         .versiya_təmiz, "0.1.0")

    def test_deb(self):
        deb = self.q / "qurma" / "kitab-refi_1.2.0_all.deb"
        üzvlər = _ar(deb.read_bytes())
        self.assertEqual(list(üzvlər), ["debian-binary", "control.tar.gz",
                                        "data.tar.gz"])
        self.assertEqual(üzvlər["debian-binary"], b"2.0\n")
        with tarfile.open(fileobj=io.BytesIO(üzvlər["control.tar.gz"])) as t:
            control = t.extractfile("./control").read().decode()
        self.assertIn("Package: kitab-refi\n", control)
        self.assertIn("Depends: python3 (>= 3.12)", control)
        with tarfile.open(fileobj=io.BytesIO(üzvlər["data.tar.gz"])) as t:
            adlar = {m.name: m for m in t.getmembers()}
            bin_ = adlar["./usr/bin/kitab-refi"]
            self.assertEqual(bin_.mode & 0o777, 0o755)
            masaüstü = t.extractfile(
                "./usr/share/applications/kitab-refi.desktop").read().decode()
        self.assertIn("Terminal=false", masaüstü)
        self.assertIn("MimeType=application/x-kitab-refi-kitab;", masaüstü)
        if shutil.which("dpkg-deb"):
            r = subprocess.run(["dpkg-deb", "--info", str(deb)],
                               capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_windows(self):
        z = zipfile.ZipFile(self.q / "qurma" / "kitab-refi-1.2.0-windows.zip")
        adlar = set(z.namelist())
        for f in ("kitab-refi.pyz", "kitab-refi.cmd", "Quraşdır.cmd",
                  "quraşdır.ps1", "sil.ps1", "ikon.ico"):
            self.assertIn(f"kitab-refi/{f}", adlar)
        ps = z.read("kitab-refi/quraşdır.ps1")
        self.assertTrue(ps.startswith("﻿".encode()))      # BOM
        ps = ps.decode("utf-8-sig")
        self.assertIn('$Basliq = "Kitab Rəfi"', ps)
        self.assertIn('foreach ($u in @(".kitab"))', ps)
        cmd = z.read("kitab-refi/kitab-refi.cmd").decode()
        self.assertIn("\r\n", cmd)
        self.assertIn('pythonw.exe', cmd)                     # pəncərəli
        iss = (self.q / "qurma" / "kitab-refi-1.2.0-windows.iss").read_text(
            encoding="utf-8-sig")
        self.assertRegex(iss, r"AppId=\{\{[0-9A-F-]{36}\}")
        self.assertIn('Subkey: "Software\\Classes\\.kitab"', iss)
        self.assertIn("PrivilegesRequired=lowest", iss)

    def test_macos(self):
        z = zipfile.ZipFile(self.q / "qurma" / "kitab-refi-1.2.0-macos.zip")
        plist = plistlib.loads(z.read("Kitab Rəfi.app/Contents/Info.plist"))
        self.assertEqual(plist["CFBundleExecutable"], "kitab-refi")
        self.assertEqual(plist["CFBundleDocumentTypes"][0]
                         ["CFBundleTypeExtensions"], ["kitab"])
        i = z.getinfo("Kitab Rəfi.app/Contents/MacOS/kitab-refi")
        self.assertEqual((i.external_attr >> 16) & 0o777, 0o755)

    def test_studio_paketi_işləyir(self):
        pyz = Q.studio_pyz(KÖK, self.q / "studio.pyz")
        layihə = self.q / "layihə"
        layihə.mkdir()
        (layihə / "a.alq").write_text("yaz(1)\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(pyz), str(layihə / "a.alq"), "--sınaq",
             "--başsız"], capture_output=True, text=True, encoding="utf-8",
            timeout=60, env={**os.environ, "PYTHONIOENCODING": "utf-8",
                             "ALQOR_KES": str(self.q / "keş")})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("fayl=a.alq", r.stdout)
        self.assertIn("✓ vidjet kataloqu", r.stdout)


if __name__ == "__main__":
    unittest.main()
