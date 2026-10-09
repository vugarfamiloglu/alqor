"""Standart kitabxana: şəkil, qrafik, pdf, ffi."""

import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.deyerler import AlqorXəta                         # noqa: E402
from alqor.modullar import _sekil_kodek as K                 # noqa: E402
from alqor.modullar import _ttf, ffi, pdf, qrafik, sekil     # noqa: E402
from sinaq.test_modullar import işlət                         # noqa: E402

try:
    from PIL import Image, ImageDraw
except ImportError:                                           # pragma: no cover
    Image = None


def _nümunə(en=37, h=23):
    """Kənarları, şəffaflığı və qradiyenti olan sınaq şəkli (RGBA)."""
    p = bytearray(en * h * 4)
    for y in range(h):
        for x in range(en):
            o = (y * en + x) * 4
            p[o:o + 4] = bytes(((x * 7) % 256, (y * 11) % 256,
                                (x * y) % 256, 255 if x < en - 5 else 90))
    return sekil.Şəkil(en, h, p)


class KodekSınağı(unittest.TestCase):
    def test_öz_formatlarımızda_gedib_qayıtma(self):
        ş = _nümunə()
        for f in ("png", "bmp"):
            en, h, p, _ = K.aç(K.yaz(f, ş.en, ş.h, ş.p))
            self.assertEqual((en, h, p), (ş.en, ş.h, ş.p), f)
        tam = ş.şəffaflıq(1).doldur("ağ").yapışdır(ş)
        opq = sekil.Şəkil(ş.en, ş.h, bytearray(tam.p))
        opq.p[3::4] = b"\xff" * (ş.en * ş.h)
        en, h, p, _ = K.aç(K.yaz("ppm", ş.en, ş.h, opq.p))
        self.assertEqual(p, opq.p)
        en, h, p, _ = K.aç(K.yaz("gif", ş.en, ş.h, opq.p))
        self.assertEqual((en, h), (ş.en, ş.h))
        orta = sum(abs(a - b) for a, b in zip(p, opq.p)) / len(p)
        self.assertLess(orta, 6)                     # median-cut palitra
        en, h, p, _ = K.aç(K.yaz("jpeg", ş.en, ş.h, opq.p, 95))
        orta = sum(abs(a - b) for a, b in zip(p, opq.p)) / len(p)
        self.assertLess(orta, 8)

    def test_gif_şəffaflıq_və_az_rəng(self):
        p = bytearray(b"\xff\x00\x00\xff" * 50 + b"\x00\x00\x00\x00" * 50)
        en, h, q, _ = K.aç(K.yaz("gif", 10, 10, p))
        self.assertEqual(q, p)

    def test_pozuq_fayllar(self):
        for b in (b"", b"salam", b"\x89PNG\r\n\x1a\n" + b"\0" * 20,
                  b"\xff\xd8\xff\xe0\0\x10JFIF\0", b"GIF89a\x01\0\x01\0"):
            with self.assertRaises(AlqorXəta):
                sekil.baytlardan(b)

    @unittest.skipIf(Image is None, "Pillow yoxdur")
    def test_pillow_ilə_müqayisə(self):
        im = Image.new("RGBA", (61, 43), (255, 0, 0, 255))
        d = ImageDraw.Draw(im)
        for i in range(0, 61, 4):
            d.line((i, 0, 60 - i, 42), fill=(i * 4, 255 - i * 4, 90, 255))
        d.ellipse((8, 8, 40, 33), fill=(0, 0, 255, 120))
        ref = im.tobytes()

        def pil(fmt, mode, **k):
            b = io.BytesIO()
            im.convert(mode).save(b, fmt, **k)
            return b.getvalue()

        for ad, b in [("png", pil("PNG", "RGBA")), ("png-rgb", pil("PNG", "RGB")),
                      ("png-P", pil("PNG", "P")), ("png-L", pil("PNG", "L")),
                      ("png-1", pil("PNG", "1")),
                      ("png-adam7", pil("PNG", "RGBA", interlace=1)),
                      ("bmp", pil("BMP", "RGB")), ("bmp-P", pil("BMP", "P")),
                      ("ppm", pil("PPM", "RGB")), ("gif", pil("GIF", "P"))]:
            _, _, p, _ = K.aç(b)
            gözlənilən = Image.open(io.BytesIO(b)).convert("RGBA").tobytes()
            self.assertEqual(p, gözlənilən, ad)
        for ad, k in [("baseline", {}), ("progressive", {"progressive": True}),
                      ("444", {"subsampling": 0}), ("422", {"subsampling": 1}),
                      ("restart", {"restart_marker_blocks": 2})]:
            b = pil("JPEG", "RGB", quality=90, **k)
            _, _, p, _ = K.aç(b)
            g = Image.open(io.BytesIO(b)).convert("RGBA").tobytes()
            self.assertLessEqual(max(abs(x - y) for x, y in zip(p, g)), 4, ad)
        b = pil("JPEG", "L", quality=90, progressive=True)
        _, _, p, _ = K.aç(b)
        g = Image.open(io.BytesIO(b)).convert("RGBA").tobytes()
        self.assertLessEqual(max(abs(x - y) for x, y in zip(p, g)), 2)
        # Bizim yazdıqlarımızı Pillow oxuyur
        for f in ("png", "jpeg", "gif", "bmp", "ppm"):
            r = Image.open(io.BytesIO(K.yaz(f, 61, 43, bytearray(ref))))
            r.load()
            self.assertEqual(r.size, (61, 43), f)

    @unittest.skipIf(Image is None, "Pillow yoxdur")
    def test_exif_istiqaməti(self):
        im = Image.new("RGB", (30, 10), "red")
        ImageDraw.Draw(im).rectangle((0, 0, 4, 9), fill="blue")
        exif = Image.Exif()
        exif[0x0112] = 6                       # 90° saat əqrəbi istiqaməti
        b = io.BytesIO()
        im.save(b, "JPEG", exif=exif, quality=95)
        ş = sekil.baytlardan(b.getvalue())
        self.assertEqual((ş.en, ş.h), (10, 30))
        r, g, bl, _ = ş.piksel(5, 1)           # mavi zolaq yuxarıya düşür
        self.assertGreater(bl, 150)
        self.assertEqual(sekil.baytlardan(b.getvalue(), False).en, 30)


class ŞəkilSınağı(unittest.TestCase):
    def test_həndəsə(self):
        ş = _nümunə(8, 5)
        self.assertEqual(ş.kəs(2, 1, 3, 2).piksel(0, 0), ş.piksel(2, 1))
        d = ş.döndər(90)
        self.assertEqual((d.en, d.h), (5, 8))
        self.assertEqual(d.piksel(4, 0), ş.piksel(0, 0))     # saat əqrəbi
        self.assertEqual(ş.döndər(90).döndər(270), ş)
        self.assertEqual(ş.döndər(180).döndər(180), ş)
        self.assertEqual(ş.çevir("üfüqi").piksel(7, 0), ş.piksel(0, 0))
        self.assertEqual(ş.çevir("şaquli").piksel(0, 4), ş.piksel(0, 0))
        self.assertEqual(ş.ölçü_dəyiş(4).h, 2)
        self.assertEqual(ş.miniatür(4, 4).en, 4)
        self.assertEqual(ş.ölçü_dəyiş(16, 10, "yaxın").piksel(1, 1),
                         ş.piksel(0, 0))
        b = ş.döndər(45)
        self.assertGreater(b.en, ş.en)
        with self.assertRaises(AlqorXəta):
            ş.kəs(5, 0, 10, 2)

    def test_filtrlər_və_çəkmə(self):
        ş = sekil.yarat(20, 10, "#808080")
        self.assertEqual(ş.boz().piksel(0, 0)[:3], [128, 128, 128])
        self.assertEqual(ş.tərs().piksel(0, 0)[:3], [127, 127, 127])
        self.assertEqual(ş.parlaqlıq(2).piksel(0, 0)[:3], [255, 255, 255])
        self.assertEqual(ş.şəffaflıq(0.5).piksel(0, 0)[3], 128)
        k = ş.düzbucaqlı(2, 2, 5, 5, "#ff0000")
        self.assertEqual(k.piksel(3, 3), [255, 0, 0, 255])
        self.assertEqual(k.piksel(10, 3), [128, 128, 128, 255])
        y = ş.yapışdır(sekil.yarat(2, 2, [0, 0, 255, 128]), 1, 1)
        self.assertEqual(y.piksel(1, 1)[2], 192)
        self.assertEqual(ş.orta_rəng(), "#808080")
        self.assertEqual(sekil.rəng("#0f08"), (0, 255, 0, 136))
        self.assertEqual(sekil.rəng("rgba(1, 2, 3, 0.5)"), (1, 2, 3, 127))
        with self.assertRaises(AlqorXəta):
            sekil.rəng("yox-rəng")
        b = ş.düzbucaqlı(0, 0, 10, 10, "ağ").bulanıq(2)
        self.assertTrue(128 < b.piksel(10, 5)[0] < 255)

    def test_alqor_kodu(self):
        with tempfile.TemporaryDirectory() as q:
            ç = işlət(
                "gətir şəkil\n"
                'dəyişən k = şəkil.yarat(60, 40, "ağ")\n'
                '    .düzbucaqlı(5, 5, 20, 10, "mavi")\n'
                '    .dairə(45, 20, 10, "#e11d48", doldur: yanlış)\n'
                'k.saxla("k.png")\n'
                'dəyişən a = şəkil.aç("k.png")\n'
                "yaz(a.ölçü(), a.piksel(10, 10), a.format())\n"
                'a.ölçüDəyiş(30).döndər(90).saxla("d.jpg", keyfiyyət: 80)\n'
                'yaz(şəkil.aç("d.jpg").ölçü())\n'
                'yaz(a.dataURI().başlayır("data:image/png;base64,"))\n',
                qovluq=q)
        self.assertEqual(ç, "[60, 40] [37, 99, 235, 255] png\n[20, 30]\n"
                            "doğru\n")


class QrafikSınağı(unittest.TestCase):
    def test_növlər_svg_qurur(self):
        s = [{"ad": "A", "dəyərlər": [1, 5, None, 3]},
             {"ad": "B", "dəyərlər": [2, -1, 4, 0]}]
        et = ["Yan", "Fev", "Mar", "Apr"]
        import xml.dom.minidom
        for növ in ("sütun", "zolaq", "xətt", "sahə"):
            for yığ in (False, True):
                q = qrafik.Qrafik(növ, {"etiketlər": et, "seriyalar": s,
                                        "başlıq": "<Sınaq & \"x\">",
                                        "yığılmış": yığ, "hamar": True})
                svg = q.svg()
                xml.dom.minidom.parseString(svg)          # düzgün XML
                self.assertIn("&lt;Sınaq &amp;", svg)
        for növ in ("dairə", "halqa"):
            svg = qrafik.Qrafik(növ, {"dəyərlər": [1, 0, 3],
                                      "etiketlər": ["a", "b", "c"],
                                      "mərkəz": "75%"}).svg()
            xml.dom.minidom.parseString(svg)
            self.assertIn("75%", svg)
        svg = qrafik.Qrafik("dairə", {"dəyərlər": [5]}).svg()
        self.assertIn("<circle", svg)                    # tək dilim — dairə
        svg = qrafik.Qrafik("nöqtə", {"seriyalar": [
            {"nöqtələr": [[1, 2], [3, 4]]}]}).svg()
        xml.dom.minidom.parseString(svg)
        svg = qrafik.histogram([1, 2, 2, 3, 9], qutular=4).svg()
        self.assertEqual(svg.count("<rect") - 1, 4)       # fon + 4 sütun

    def test_bölgülər(self):
        self.assertEqual(qrafik._ox_bölgüləri(0, 23), [0, 5, 10, 15, 20, 25])
        self.assertEqual(qrafik._ox_bölgüləri(-3, 7)[0], -4)
        self.assertEqual(qrafik._ox_bölgüləri(5, 5), [4, 4.5, 5, 5.5, 6])

    def test_xətalar(self):
        for növ, s in [("sütun", {}), ("sütun", {"seriyalar": [{"dəyərlər":
                                                               ["x"]}]}),
                       ("dairə", {"dəyərlər": [-1, 2]}),
                       ("dairə", {"dəyərlər": [0, 0]}),
                       ("sütun", {"seriyalar": [{"dəyərlər": [1]}],
                                  "tema": "yaşıl"})]:
            with self.assertRaises(AlqorXəta, msg=(növ, s)):
                qrafik.Qrafik(növ, s)

    def test_alqor_kodu(self):
        with tempfile.TemporaryDirectory() as q:
            ç = işlət(
                "gətir qrafik\ngətir fayl\n"
                'dəyişən q = qrafik.sütun(etiketlər: ["a", "b"], '
                'dəyərlər: [3, 4], başlıq: "Sınaq")\n'
                'q.saxla("q.svg")\nq.saxla("q.html")\n'
                'yaz(fayl.oxu("q.svg").başlayır("<svg"), '
                'fayl.oxu("q.html").ehtiva("Sınaq"))\n'
                'yaz(qrafik.dairə(dəyərlər: [1, 2]).növ())\n', qovluq=q)
        self.assertEqual(ç, "doğru doğru\ndairə\n")


@unittest.skipIf(_ttf.sistem_şrifti() is None, "sistemdə TrueType şrift yoxdur")
class PDFSınağı(unittest.TestCase):
    def test_ttf_alt_dəst(self):
        yol = _ttf.sistem_şrifti()[0]
        t = _ttf.TTF(Path(yol).read_bytes())
        g = {t.qlif(c) for c in "Salam əğşıİ"}
        self.assertNotIn(0, g)
        alt = _ttf.TTF(t.alt_dəst(g))
        self.assertLess(len(t.alt_dəst(g)), len(t.data) // 3)
        self.assertEqual(alt.qlif_sayı, t.qlif_sayı)
        self.assertEqual(alt.enlər[t.qlif("ə")], t.enlər[t.qlif("ə")])
        with self.assertRaises(_ttf.ŞriftXətası):
            _ttf.TTF(b"OTTO" + b"\0" * 100)

    def sənəd(self):
        s = pdf.Sənəd(başlıq="Sınaq hesabatı", müəllif="Alqor")
        s.başlıq("Başlıq — ə ğ ş ı İ")
        s.abzas("Adi **qalın** və *kursiv* mətn. " * 30,
                düzləndir="ikiTərəf")
        s.siyahı(["bir", "iki"], nömrəli=True)
        s.cədvəl([["Ad", "Say", "Qiymət"], ["Alma", 3, "1,20 ₼"]] +
                 [[f"Sətir {i}", i, f"{i},00"] for i in range(80)],
                 zolaqlı=True)
        s.şəkil(_nümunə(), en=40)
        s.mətn(10, 10, "Mütləq", rəng="#2563eb")
        s.düzbucaqlı(10, 20, 30, 10, rəng="sarı", künc=2)
        s.səhifə_nömrələri("Səhifə [n] / [cəm]")
        return s

    def test_struktur_və_mətn(self):
        b = self.sənəd().baytlar()
        self.assertTrue(b.startswith(b"%PDF-1.7"))
        self.assertTrue(b.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"/Subtype /Type0", b)
        self.assertIn(b"/FontFile2", b)
        self.assertLess(len(b), 400_000)
        try:
            import pypdf
        except ImportError:
            self.skipTest("pypdf yoxdur")
        r = pypdf.PdfReader(io.BytesIO(b))
        self.assertGreaterEqual(len(r.pages), 3)
        self.assertEqual(r.metadata.title, "Sınaq hesabatı")
        mətn = r.pages[0].extract_text()
        self.assertIn("ə ğ ş ı İ", mətn)
        self.assertIn("qalın", mətn)
        self.assertIn(f"Səhifə 1 / {len(r.pages)}",
                      r.pages[0].extract_text())

    @unittest.skipIf(shutil.which("pdftotext") is None, "poppler yoxdur")
    def test_poppler_oxuyur(self):
        with tempfile.TemporaryDirectory() as q:
            p = Path(q, "s.pdf")
            self.sənəd().saxla(p)
            r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8",
                                str(p), "-"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Başlıq — ə ğ ş ı İ", r.stdout)
            self.assertIn("1,20 ₼", r.stdout)
            self.assertNotIn("Syntax Error", r.stderr)

    def test_jpeg_birbaşa_daxil_edilir(self):
        ş = _nümunə(16, 16)
        ş.p[3::4] = b"\xff" * 256
        jpg = K.yaz("jpeg", 16, 16, ş.p, 90)
        s = pdf.Sənəd()
        s.şəkil(jpg, en=20)
        b = s.baytlar()
        self.assertIn(b"/DCTDecode", b)
        self.assertIn(jpg, b)

    def test_xətalar(self):
        with self.assertRaises(AlqorXəta):
            pdf.Sənəd(ölçü="B9")
        with self.assertRaises(AlqorXəta):
            pdf.Sənəd(şrift="/yoxdur.ttf")
        s = pdf.Sənəd()
        with self.assertRaises(AlqorXəta):
            s.cədvəl("x")
        with self.assertRaises(AlqorXəta):
            s.abzas("x", düzləndir="yan")

    def test_alqor_kodu(self):
        with tempfile.TemporaryDirectory() as q:
            ç = işlət(
                "gətir pdf\n"
                'dəyişən s = pdf.sənəd(başlıq: "Sınaq", istiqamət: "albom")\n'
                's.başlıq("Salam")\ns.abzas("Mətn **qalın**")\n'
                's.cədvəl([["a", "b"], [1, 2]])\n'
                's.səhifəNömrələri()\ns.saxla("s.pdf")\n'
                "yaz(s.səhifəSayı(), s.en() > s.hündürlük())\n", qovluq=q)
        self.assertEqual(ç, "1 doğru\n")


class FFISınağı(unittest.TestCase):
    def test_libc_və_libm(self):
        c = ffi.Kitabxana("c")
        strlen = c.funksiya("strlen", "ölçü", ["mətn"])
        self.assertEqual(strlen.f("salam"), 5)
        self.assertEqual(strlen.f("ə"), 2)                  # UTF-8 bayt
        m = ffi.Kitabxana("m")
        self.assertAlmostEqual(m.funksiya("sqrt", "onluq", ["onluq"]).f(2),
                               2 ** 0.5)
        with self.assertRaises(AlqorXəta):
            c.funksiya("yoxdur_bele_funksiya")
        with self.assertRaises(AlqorXəta):
            strlen.f(5)
        with self.assertRaises(AlqorXəta):
            c.funksiya("strlen", "naməlum", ["mətn"])

    def test_alqor_kodu(self):
        ç = işlət(
            "gətir ffi\n"
            'dəyişən c = ffi.yüklə("c")\n'
            'dəyişən b = ffi.bufer(32)\n'
            'c.funksiya("snprintf", "tam", ["bufer", "ölçü", "mətn"], '
            'variadik: doğru)(b, 32, "%d-%s", 42, "ok")\n'
            "yaz(b.mətn())\n"
            'dəyişən N = ffi.struktur("Nöqtə", [["x", "tam32"], '
            '["y", "tam32"]])\n'
            'dəyişən n = N.yarat({"x": 3, "y": 4})\nn.qoy("x", 10)\n'
            "yaz(n.lüğət(), N.ölçü())\n"
            "dəyişən massiv = ffi.bufer([5, 3, 9, 1])\n"
            'dəyişən memcmp = c.funksiya("memcmp", "tam", '
            '["göstərici", "göstərici", "ölçü"])\n'
            "dəyişən müq = ffi.geriÇağırış((a, b) => memcmp(a, b, 1), "
            '"tam", ["göstərici", "göstərici"])\n'
            'c.funksiya("qsort", "heç", ["bufer", "ölçü", "ölçü", '
            '"göstərici"])(massiv, 4, 1, müq)\n'
            "yaz(massiv.baytlar().siyahıyaÇevir())\n")
        self.assertEqual(ç, '42-ok\n{"x": 10, "y": 4} 8\n[1, 3, 5, 9]\n')


if __name__ == "__main__":
    unittest.main()
