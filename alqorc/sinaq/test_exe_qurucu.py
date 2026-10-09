"""`alqor qur --exe`: başladıcı + yük formatı."""

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import exe_qurucu as EQ                       # noqa: E402
from alqor.layihe import Layihə                           # noqa: E402


def yükü_oxu(exe: bytes):
    """Rust başladıcısının etdiyini Python-da təkrarlayır."""
    assert exe[-8:] == EQ.İZ
    baş = struct.unpack("<Q", exe[-16:-8])[0]
    b = exe[baş:-16]
    assert b[:8] == EQ.SEHR
    i = 8

    def u32():
        nonlocal i
        v = struct.unpack("<I", b[i:i + 4])[0]
        i += 4
        return v

    def mətn():
        nonlocal i
        n = u32()
        s = b[i:i + n].decode()
        i += n
        return s

    say = u32()
    ad, id_, giriş = mətn(), mətn(), mətn()
    fayllar = {}
    for _ in range(say):
        yol = mətn()
        ölçü, sıx = struct.unpack("<QQ", b[i:i + 16])
        i += 16
        parça = b[i:i + sıx]
        i += sıx
        fayllar[yol] = parça if sıx == ölçü else zlib.decompress(parça, -15)
    return baş, ad, id_, giriş, fayllar


class ExeQurucu(unittest.TestCase):
    def test_yük_formatı(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q)
            py = q / "python"
            (py / "Lib" / "__pycache__").mkdir(parents=True)
            (py / "python.exe").write_bytes(b"MZ" + b"\0" * 100)
            (py / "Lib" / "os.py").write_text("x = 1\n" * 200)
            (py / "Lib" / "__pycache__" / "os.pyc").write_bytes(b"atla")
            (py / "python.pdb").write_bytes(b"atla")
            pyz = q / "t.pyz"
            pyz.write_bytes("PK-tətbiq".encode())
            exe = EQ.exe_yarat(pyz, q / "qurma" / "Hesab.exe", "Hesab Əli",
                               py, konsol=True)
            m = exe.read_bytes()
            başladıcı = (EQ.RESURSLAR / "baslatici-konsol.exe").read_bytes()
            self.assertTrue(m.startswith(başladıcı))
            baş, ad, id_, giriş, f = yükü_oxu(m)
            self.assertEqual(baş, len(başladıcı))
            self.assertEqual(ad, "Hesab-Eli")
            self.assertEqual(len(id_), 16)
            self.assertEqual(giriş, "tetbiq.pyz")
            self.assertEqual(f["tetbiq.pyz"], "PK-tətbiq".encode())
            self.assertEqual(f["python/Lib/os.py"], b"x = 1\n" * 200)
            self.assertNotIn("python/python.pdb", f)
            self.assertFalse(any("__pycache__" in k for k in f))

    def test_başladıcılar_windows_exe(self):
        for ad in ("baslatici-konsol.exe", "baslatici-pencere.exe"):
            b = (EQ.RESURSLAR / ad).read_bytes()
            self.assertEqual(b[:2], b"MZ")
            pe = struct.unpack("<I", b[0x3C:0x40])[0]
            self.assertEqual(b[pe:pe + 4], b"PE\0\0")
            alt_sistem = struct.unpack("<H", b[pe + 24 + 68:pe + 24 + 70])[0]
            self.assertEqual(alt_sistem, 3 if "konsol" in ad else 2)

    def test_konsol_və_pəncərə_seçimi(self):
        with tempfile.TemporaryDirectory() as q:
            k = Path(q)
            (k / "mənbə").mkdir()
            f = k / "mənbə" / "əsas.alq"
            f.write_text('yaz("salam")\n', encoding="utf-8")
            L = Layihə(k, {})
            self.assertTrue(EQ.konsoldurmu(L))
            f.write_text("gətir pəncərə\n", encoding="utf-8")
            self.assertFalse(EQ.konsoldurmu(L))
            L = Layihə(k, {"quraşdırıcı": {"konsol": True}})
            self.assertTrue(EQ.konsoldurmu(L))

    def test_xətalı_proqram_qurulmur(self):
        with tempfile.TemporaryDirectory() as q:
            k = Path(q)
            (k / "mənbə").mkdir()
            (k / "mənbə" / "əsas.alq").write_text("yaz(\n", encoding="utf-8")
            with self.assertRaises(EQ.QurmaXətası):
                EQ.sintaksisi_yoxla(Layihə(k, {}))


if __name__ == "__main__":
    unittest.main()
