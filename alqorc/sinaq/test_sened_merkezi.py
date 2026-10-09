"""Oflayn sənəd mərkəzi və Windows paylaması."""

import html
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import sened_merkezi as SM                      # noqa: E402
from alqor import windows_paylama as WP                    # noqa: E402

KÖK = Path(__file__).parent.parent
REPO = KÖK.parent


def _html(md: str) -> str:
    return SM.md_html(md, SM._Səhifə(lambda h: h.replace(".md", ".html")))


class Markdown(unittest.TestCase):
    def test_başlıq_lövbər_və_cədvəl(self):
        h = _html("## Şərt — əgər\n\n| a | b |\n|---|:-:|\n| `x \\| y` | 2 |\n")
        self.assertIn('<h2 id="sert-eger">', h)
        self.assertIn("<code>x | y</code>", h)
        self.assertIn('text-align:center', h)

    def test_kod_rənglənir_və_qaçış(self):
        h = _html('```alqor\nəgər x < 5 onda yaz("a {x}") son\n```')
        self.assertIn('<span class="k">əgər</span>', h)
        self.assertIn('<span class="f">yaz</span>', h)
        self.assertIn("&lt;", h)
        self.assertIn('<span class="i">{x}</span>', h)

    def test_iç_içə_siyahı_və_sitat(self):
        h = _html("- bir\n  - iki\n- üç\n\n> **Qeyd:** bax [dərs](01-DIL.md#a)\n")
        self.assertEqual(h.count("<ul>"), 2)
        self.assertIn('<a href="01-DIL.html#a">dərs</a>', h)
        self.assertIn("<blockquote>", h)

    def test_nömrəli_siyahı(self):
        h = _html("3. üç\n4. dörd\n")
        self.assertIn('<ol start="3">', h)


class Sayt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = tempfile.TemporaryDirectory()
        cls.yol = Path(cls.q.name) / "sened"
        SM.qur(REPO, cls.yol)

    @classmethod
    def tearDownClass(cls):
        cls.q.cleanup()

    def test_bütün_bölmələr_var(self):
        adlar = {p.name for p in self.yol.glob("*.html")}
        for ad in ("index.html", "ilk-addimlar.html", "emrler.html",
                   "beledci-01-dil-dersliyi.html", "beledci-05-xeta-lugeti.html",
                   "spes-10-standart-kitabxana.html", "numuneler.html"):
            self.assertIn(ad, adlar)
        self.assertGreaterEqual(len(adlar), 35)
        for f in ("stil.css", "sened.js", "axtaris.js"):
            self.assertTrue((self.yol / f).is_file())

    def test_daxili_keçidlər_qırıq_deyil(self):
        idlər = {p.name: set(re.findall(r'id="([^"]+)"', p.read_text("utf-8")))
                 for p in self.yol.glob("*.html")}
        qırıq = []
        for p in self.yol.glob("*.html"):
            for h in re.findall(r'href="([^"]+)"', p.read_text("utf-8")):
                h = html.unescape(h)
                if h.startswith("http") or h.endswith((".css", ".svg")):
                    continue
                fayl, _, lv = h.partition("#")
                fayl = fayl or p.name
                if fayl not in idlər or (lv and lv not in idlər[fayl]):
                    qırıq.append(f"{p.name} → {h}")
        self.assertEqual(qırıq, [])

    def test_xarici_resurs_yoxdur(self):
        for p in self.yol.glob("*.html"):
            m = p.read_text("utf-8")
            self.assertNotRegex(m, r'<(script|link)[^>]+(src|href)="https?:')

    def test_axtarış_indeksi(self):
        m = (self.yol / "axtaris.js").read_text("utf-8")
        self.assertIn("əgər", m)
        self.assertIn("cəhd et", m)


class WindowsPaylaması(unittest.TestCase):
    def test_qovluq_və_iss(self):
        with tempfile.TemporaryDirectory() as q:
            q = Path(q)
            saxta = q / "python.zip"
            with zipfile.ZipFile(saxta, "w") as z:
                z.writestr("python.exe", b"MZ")
                z.writestr("pythonw.exe", b"MZ")
            d = WP.paylama_qovluğu(KÖK, q / "çıxış", python_zip=saxta)
            for f in ("python/python.exe", "alqorc/alqorc.py",
                      "alqorc/alqor/icraci.py", "alqorc/studio/server.py",
                      "bin/alqor.cmd", "bin/alqorpm.cmd", "bin/studio.pyw",
                      "sened/index.html", "numuneler/01-salam.alq",
                      "ikon.ico"):
                self.assertTrue((d / f).is_file(), f)
            self.assertFalse(list(d.rglob("__pycache__")))
            self.assertFalse((d / "alqorc" / "sinaq").exists())
            cmd = (d / "bin" / "alqorpm.cmd").read_bytes()
            cmd.decode("ascii")
            self.assertIn(b"alqorc.py\" pm %*", cmd)
            iss = WP.iss_yaz(q / "çıxış").read_text("utf-8-sig")
            self.assertIn("PrivilegesRequired=lowest", iss)
            self.assertIn("RegWriteExpandStringValue", iss)
            self.assertIn(r"{app}\sened\index.html", iss)
            self.assertIn("ChangesEnvironment=yes", iss)
            # Pascal identifikatorları ASCII olmalıdır
            kod = iss.split("[Code]", 1)[1]
            for söz in re.findall(r"\b(?:var|const|procedure|function)\b[^;]*", kod):
                söz.encode("ascii")


if __name__ == "__main__":
    unittest.main()
