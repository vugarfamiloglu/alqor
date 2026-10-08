"""Quraşdırıcı generatoru: .deb, .rpm, .AppImage, Windows zip + Inno Setup,
macOS .app və .dmg."""

import base64
import io
import os
import plistlib
import struct
import zlib
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
from alqor._qur_dmg import iso9660                          # noqa: E402
from alqor._qur_squashfs import squashfs                    # noqa: E402

KÖK = Path(__file__).parent.parent
SAXTA_RUNTIME = b"\x7fELF" + bytes(4092)                   # sınaq üçün


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
        (cls.q / "runtime").write_bytes(SAXTA_RUNTIME)
        os.environ["ALQOR_APPIMAGE_RUNTIME"] = str(cls.q / "runtime")
        os.environ["ALQOR_DMG_SAF"] = "1"
        cls.fayllar = Q.qur(cls.t, cls.q / "qurma")

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("ALQOR_APPIMAGE_RUNTIME", None)
        os.environ.pop("ALQOR_DMG_SAF", None)
        shutil.rmtree(cls.q, ignore_errors=True)

    def test_bütün_formatlar(self):
        adlar = sorted(f.name for f in self.fayllar)
        for gözlənilən in ("kitab-refi_1.2.0_all.deb",
                           "kitab-refi-1.2.0-1.noarch.rpm",
                           "Kitab_Refi-1.2.0-x86_64.AppImage",
                           "kitab-refi-1.2.0-macos.zip",
                           "kitab-refi-1.2.0.dmg"):
            self.assertIn(gözlənilən, adlar)
        n = Q.qur(self.t, self.q / "yalnız", ("linux", "macos"),
                  formatlar=("rpm", "dmg"))
        self.assertEqual(sorted(f.suffix for f in n), [".dmg", ".rpm"])

    def test_rpm_quruluşu(self):
        d = (self.q / "qurma" / "kitab-refi-1.2.0-1.noarch.rpm").read_bytes()
        self.assertEqual(d[:4], b"\xed\xab\xee\xdb")
        self.assertEqual(d[96:99], b"\x8e\xad\xe8")      # imza başlığı
        il, dl = struct.unpack(">ii", d[104:112])
        i = 112 + il * 16 + dl
        i += -i % 8
        self.assertEqual(d[i:i + 3], b"\x8e\xad\xe8")     # əsas başlıq
        il, dl = struct.unpack(">ii", d[i + 8:i + 16])
        yük = d[i + 16 + il * 16 + dl:]
        cpio = zlib.decompress(yük, 31)
        self.assertTrue(cpio.startswith(b"070701"))
        self.assertIn(b"./usr/bin/kitab-refi", cpio)
        self.assertIn(b"TRAILER!!!", cpio)

    @unittest.skipIf(shutil.which("rpm") is None, "rpm yoxdur")
    def test_rpm_alət_ilə(self):
        rpm = self.q / "qurma" / "kitab-refi-1.2.0-1.noarch.rpm"
        r = subprocess.run(["rpm", "-K", "--nosignature", str(rpm)],
                           capture_output=True, text=True)
        self.assertIn("digests OK", r.stdout, r.stderr)
        r = subprocess.run(["rpm", "-qpl", str(rpm)], capture_output=True,
                           text=True)
        self.assertIn("/usr/bin/kitab-refi", r.stdout)
        self.assertIn("/usr/share/applications/kitab-refi.desktop", r.stdout)
        r = subprocess.run(["rpm", "-qpR", str(rpm)], capture_output=True,
                           text=True)
        self.assertIn("python3 >= 3.12", r.stdout)
        kök = self.q / "rpmkök"
        r = subprocess.run(["rpm", "--root", str(kök), "--nodeps",
                            "--noscripts", "-i", str(rpm)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, str(
            kök / "usr/lib/kitab-refi/kitab-refi.pyz")], capture_output=True,
            text=True)
        self.assertEqual(r.stdout, "salam\n")

    def test_appimage(self):
        ai = self.q / "qurma" / "Kitab_Refi-1.2.0-x86_64.AppImage"
        d = ai.read_bytes()
        self.assertTrue(d.startswith(SAXTA_RUNTIME))
        self.assertTrue(os.access(ai, os.X_OK))
        sq = d[len(SAXTA_RUNTIME):]
        self.assertEqual(sq[:4], b"hsqs")
        if shutil.which("unsquashfs") is None:
            return
        f = self.q / "ai.sqfs"
        f.write_bytes(sq)
        hədəf = self.q / "ai"
        subprocess.run(["unsquashfs", "-q", "-d", str(hədəf), str(f)],
                       check=True, capture_output=True)
        self.assertTrue((hədəf / "AppRun").stat().st_mode & 0o111)
        self.assertEqual(os.readlink(hədəf / ".DirIcon"), "kitab-refi.png")
        self.assertIn("Exec=kitab-refi", (hədəf / "kitab-refi.desktop")
                      .read_text(encoding="utf-8"))
        r = subprocess.run([str(hədəf / "AppRun")], capture_output=True,
                           text=True)
        self.assertEqual(r.stdout, "salam\n", r.stderr)

    def test_squashfs_böyük_və_çox_fayl(self):
        if shutil.which("unsquashfs") is None:
            self.skipTest("unsquashfs yoxdur")
        f = {"a/b.bin": (os.urandom(300_000) + b"z" * 300_000, 0o644)}
        for i in range(300):
            f[f"çox/ad-{i:03d}.txt"] = (str(i).encode() * i, 0o600)
        (self.q / "t.sqfs").write_bytes(squashfs(f, {"keçid": "a/b.bin"}))
        h = self.q / "sq"
        subprocess.run(["unsquashfs", "-q", "-d", str(h),
                        str(self.q / "t.sqfs")], check=True,
                       capture_output=True)
        self.assertEqual((h / "a/b.bin").read_bytes(), f["a/b.bin"][0])
        self.assertEqual(len(list((h / "çox").iterdir())), 300)
        self.assertEqual((h / "çox/ad-007.txt").read_bytes(), b"7" * 7)
        self.assertEqual(os.readlink(h / "keçid"), "a/b.bin")

    def test_dmg(self):
        d = (self.q / "qurma" / "kitab-refi-1.2.0.dmg").read_bytes()
        koly = d[-512:]
        self.assertEqual(koly[:4], b"koly")
        uz = struct.unpack(">Q", koly[32:40])[0]          # DataForkLength
        xml_ofs, xml_uz = struct.unpack(">QQ", koly[216:232])
        plist = plistlib.loads(d[xml_ofs:xml_ofs + xml_uz])
        mish = plist["resource-fork"]["blkx"][0]["Data"]
        self.assertEqual(mish[:4], b"mish")
        say = struct.unpack(">I", mish[200:204])[0]
        imaj = bytearray()
        for k in range(say):
            t, _, s, n, o, l = struct.unpack(
                ">IIQQQQ", mish[204 + k * 40:244 + k * 40])
            if t == 0x80000005:
                imaj += zlib.decompress(d[o:o + l])
            elif t == 2:
                imaj += bytes(n * 512)
        self.assertEqual(struct.unpack(">I", mish[72:76])[0],
                         zlib.crc32(imaj) & 0xFFFFFFFF)
        self.assertEqual(uz, xml_ofs)
        self.assertEqual(bytes(imaj[32769:32774]), b"CD001")
        if shutil.which("isoinfo"):
            iso = self.q / "dmg.iso"
            iso.write_bytes(imaj)
            r = subprocess.run(["isoinfo", "-R", "-l", "-i", str(iso)],
                               capture_output=True, text=True)
            self.assertIn("Kitab Rəfi.app", r.stdout)
            self.assertIn("Applications -> /Applications", r.stdout)
            self.assertRegex(r.stdout, r"-rwxr-xr-x .* kitab-refi")
        if shutil.which("dmg2img"):
            r = subprocess.run(["dmg2img", str(self.q / "qurma" /
                                               "kitab-refi-1.2.0.dmg"),
                                str(self.q / "geri.img")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((self.q / "geri.img").read_bytes(), imaj)

    def test_iso_uzun_adlar(self):
        if shutil.which("isoinfo") is None:
            self.skipTest("isoinfo yoxdur")
        ad = "çox-uzun-" + "ə" * 60 + ".txt"
        iso = self.q / "uzun.iso"
        iso.write_bytes(iso9660({f"q/{ad}": (b"x", 0o644)}, {}, "T"))
        r = subprocess.run(["isoinfo", "-R", "-l", "-i", str(iso)],
                           capture_output=True, text=True)
        self.assertIn(ad, r.stdout)

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
        for f in ("kitab-refi.pyz", "kitab-refi.cmd", "Qurasdir.cmd",
                  "qurasdir.ps1", "sil.ps1", "ikon.ico"):
            self.assertIn(f"kitab-refi/{f}", adlar)
        # cmd.exe OEM kod səhifəsində oxuyur — .cmd faylları ASCII olmalıdır
        for ad in adlar:
            if ad.endswith(".cmd"):
                z.read(ad).decode("ascii")
        ps = z.read("kitab-refi/qurasdir.ps1")
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
