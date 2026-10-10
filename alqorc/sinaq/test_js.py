"""
JS hədəfi: Python icraçısı ilə Node.js çıxışının müqayisəsi.

Korpus `test_icraci.py`-dakı bütün kod parçalarından yığılır (hər
parçanın Python nəticəsi etalondur), üstəlik `sinaq/js_numuneler/`
proqramları. Node.js yoxdursa sınaqlar ötürülür.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.js import KompilyasiyaXətası, mətndən, veb_səhifəsi  # noqa: E402
from alqor.js.muqayise import js_işlət, node_tap               # noqa: E402

KÖK = Path(__file__).parent.parent
NÜMUNƏLƏR = Path(__file__).parent / "js_numuneler"
NODE = node_tap()


def _korpus() -> list[dict]:
    """`test_icraci` parçalarını işlədib (kod, giriş, çıxış, xəta) yığır."""
    from sinaq import test_icraci as T
    qeyd: list[dict] = []
    orijinal = T.işlət

    def yazan(kod, giriş=None):
        s, x = orijinal(kod, giriş)
        qeyd.append({"kod": kod, "giriş": list(giriş or []),
                     "çıxış": list(s), "xəta": x.tip if x else None})
        return s, x

    T.işlət = yazan
    try:
        unittest.TextTestRunner(stream=io.StringIO()).run(
            unittest.TestLoader().loadTestsFromModule(T))
    finally:
        T.işlət = orijinal
    görülən: set[str] = set()
    n = []
    for q in qeyd:
        if q["kod"] not in görülən:
            görülən.add(q["kod"])
            n.append(q)
    return n


def _python_çıxışı(yol: Path) -> tuple[str, int]:
    r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "işlət",
                        str(yol)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    return r.stdout, r.returncode


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class KorpusMüqayisəsi(unittest.TestCase):
    def test_icraçı_parçaları_eyni_nəticə_verir(self):
        korpus = _korpus()
        self.assertGreater(len(korpus), 150)
        js = js_işlət(korpus, NODE)
        fərqlər = []
        for n, j in zip(korpus, js):
            if j["çıxış"] != n["çıxış"] or j["xəta"] != n["xəta"]:
                fərqlər.append(f"{n['kod']}\n  python: {n['çıxış']} "
                               f"{n['xəta']}\n  js    : {j['çıxış']} "
                               f"{j['xəta']}")
        self.assertEqual(fərqlər, [], "\n\n".join(fərqlər[:5]))


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class NümunəProqramlar(unittest.TestCase):
    def test_nümunələr_eyni_çıxış_verir(self):
        fayllar = sorted(NÜMUNƏLƏR.glob("[0-9]*.alq"))
        self.assertGreaterEqual(len(fayllar), 10)
        for f in fayllar:
            with self.subTest(f.name):
                gözlənilən, kod = _python_çıxışı(f)
                self.assertEqual(kod, 0)
                r = subprocess.run(
                    [sys.executable, str(KÖK / "alqorc.py"), "işlət", "--js",
                     str(f)], capture_output=True, text=True,
                    encoding="utf-8", timeout=120)
                self.assertEqual(r.stdout, gözlənilən, r.stderr)

    def test_giriş_stdin_ilə(self):
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "g.alq"
            f.write_text('dəyişən ad = oxu("Ad: ")\n'
                         'dəyişən n = oxuTam()\n'
                         'yaz("Salam, {ad}! {n * 2}")\n', encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "işlət", "--js",
                 str(f)], input="Aysel\n21\n", capture_output=True,
                text=True, encoding="utf-8", timeout=60)
            self.assertEqual(r.stdout, "Ad: Salam, Aysel! 42\n")

    def test_konsol_modulu_python_ilə_eyni(self):
        f = KÖK / "sinaq" / "js_numuneler" / "konsol.alq"
        giriş = "\nmavi\nx\nhə\n3,1\n"
        mühit = dict(os.environ, NO_COLOR="1", PYTHONIOENCODING="utf-8")
        çıxışlar = []
        for bayraq in ([], ["--js"]):
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "işlət", *bayraq,
                 str(f)], input=giriş, capture_output=True, text=True,
                encoding="utf-8", timeout=120, env=mühit)
            self.assertEqual(r.returncode, 0, r.stderr)
            çıxışlar.append(r.stdout)
        self.assertEqual(çıxışlar[0], çıxışlar[1])
        self.assertIn("Salam, Dünya", çıxışlar[1])
        self.assertIn("Leyla │ 7", çıxışlar[1])

    def test_xəta_çıxış_kodu(self):
        js = mətndən('yaz("a")\nat ArqumentXətası("pis")\nyaz("b")\n')
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "p.js"
            f.write_text(js, encoding="utf-8")
            r = subprocess.run([NODE, str(f)], capture_output=True,
                               text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "a\n")
        self.assertIn("ArqumentXətası: pis", r.stderr)

    def test_əsas_funksiyası_və_arqumentlər(self):
        js = mətndən('gətir sistem\nfunksiya əsas(arq)\n'
                     '    yaz(arq, sistem.arqumentlər())\n    qaytar 3\nson\n')
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "p.js"
            f.write_text(js, encoding="utf-8")
            r = subprocess.run([NODE, str(f), "x", "y"], capture_output=True,
                               text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, '["x", "y"] ["x", "y"]\n')


# ═══════════════════════════════════════════════════════════════════════
#  Vidjetlər: Python ilə JS eyni HTML qurur
# ═══════════════════════════════════════════════════════════════════════

_HADİSƏ_PARAMETRLƏRİ = {
    "klik", "dəyişdi", "yazıldı", "göndərildi", "bağlandı", "seçildi",
    "silindi", "əlavəEdildi", "başlanğıcDəyişdi", "bitməDəyişdi",
    "sətirKlik", "təsdiqləndi", "ləğvEdildi",
}
_SİYAHI_PARAMETRLƏRİ = {
    "elementlər", "seçimlər", "adlar", "yollar", "teqlər", "təkliflər",
    "düymələr", "seçilənlər", "keçidlər", "qeydlilər", "xüsusiyyətlər",
    "etiketlər",
}
_MƏZMUN_PARAMETRLƏRİ = {
    "məzmun", "altlıq", "alətlər", "sağ", "sol", "yan", "hərəkət",
    "hərəkətlər",
}
_XÜSUSİ = {
    "sütunlar": '[["ad", "Ad"], ["yaş", "Yaş"]]',
    "sətirlər": '[{"ad": "Aysel", "yaş": 30}, ["Rəşad <b>", 25]]',
    "dəyərlər": "[3, 7.5, 1, 0]",
    "cütlər": '{"Plan": "Komanda", "Say": 3}',
    "statistika": '{"Post": 12, "İzləyici": "1,2k"}',
    "şəkillər": '["a.png", ["b.png", "İzah"]]',
    "slaydlar": '["a.png", ["b.png", "Başlıq"]]',
    "növ": '"təhlükə"', "tərəf": '"sol"', "düzləndir": '"mərkəz"',
    "şaquli": '"son"', "nisbət": '"1:2"', "forma": '"4/3"',
    "ünvan": '"https://alqor.az/a?b=1&c=2"',
    "mənbə": '"https://alqor.az/ş.png"',
    "poster": '"https://alqor.az/p.png"', "il": "2024", "ayı": "2",
    "seçili": '"2024-02-14"', "cari": '"İki <b>"',
}
_MARKDOWN = ('"# Baş\\n\\nSalam **qalın** `kod <x>`\\n- a\\n- b\\n\\n'
             '```\\nx < y\\n```\\nson sətir"')


def _nümunə_dəyəri(ad: str, standart) -> str:
    """Parametrin adına və standartına görə real Alqor dəyəri."""
    if ad in _HADİSƏ_PARAMETRLƏRİ:
        return "(x) => yaz(x)"
    if ad in _XÜSUSİ:
        return _XÜSUSİ[ad]
    if ad in _SİYAHI_PARAMETRLƏRİ:
        return '["Bir", "İki <b>", "Üç & dörd"]'
    if ad in _MƏZMUN_PARAMETRLƏRİ:
        if standart == "":
            return _MARKDOWN
        return '[vidjet.mətn(məzmun: "iç"), "düz <mətn>"]'
    if ad == "ölçü":
        return '"böyük"' if isinstance(standart, str) else "32"
    if isinstance(standart, bool):
        return "yanlış" if standart else "doğru"
    if isinstance(standart, int):
        return "3"
    if ad == "dəyər":
        return '"5"'
    if isinstance(standart, str) and standart.startswith("#"):
        return '"#ff0000"'
    return '"Mətn <&> \\"q\\" İı"'


def _vidjet_kodları() -> list[str]:
    import inspect

    from alqor import vidjet as V
    kodlar = []
    for ad in V.VİDJETLƏR:
        parametrlər = list(inspect.signature(getattr(V, ad))
                           .parameters.values())[1:-1]   # icraçı, üslub
        arq = ", ".join(f"{p.name}: {_nümunə_dəyəri(p.name, p.default)}"
                        for p in parametrlər)
        for çağırış in (f"vidjet.{ad}()", f"vidjet.{ad}({arq})"):
            kodlar.append(
                "gətir vidjet\ngətir pəncərə\n"
                f"dəyişən e = {çağırış}\n"
                "dəyişən p = yeni pəncərə.Pəncərə(\"s\")\n"
                "p.məzmun(<div>{e}</div>)\n"
                "dəyişən s = pəncərə.sınaq.aç(p)\n"
                "yaz(s.HTML())\nyaz(e)\n")
    kodlar += [
        'gətir vidjet\nyaz(vidjet.düymə(mətn: "A", üslub: {"fon": "#16a34a",'
        ' "künc": 20, "en": 120, "qalın": doğru}))\n'
        'yaz(vidjet.sahə(etiket: "Ad", üslub: {"rəng": "red", '
        '"maksEn": 300, "kursiv": doğru}))\n',
        'gətir vidjet\nyaz(vidjet.düymə(mətn: "A", üslub: {"fon": "url(x)"}))\n',
        'gətir vidjet\nyaz(vidjet.düymə(mətn: "A", növ: "yox"))\n',
        'gətir vidjet\nyaz(uzunluq(vidjet.kataloq()), '
        'uzunluq(vidjet.kataloq("form")), vidjet.kateqoriyalar())\n'
        'yaz(vidjet.kataloq()[5])\nyaz(vidjet.skelet("sahə", "ad"))\n'
        'yaz(vidjet.skelet("seçim"))\nyaz(vidjet.nümunə("cədvəl", "c"))\n',
        'gətir vidjet\nyaz(vidjet.skelet("düym"))\n',
        'gətir vidjet\nyaz(vidjet.kataloq("yox"))\n',
        'gətir vidjet\ndəyişən a = vidjet.səhifə(başlıq: "S", məzmun: '
        '[vidjet.başlıq(mətn: "B", səviyyə: 9)], əlavəÜslub: "a{b:c}")\n'
        'yaz(a)\n'
        'yaz(vidjet.üslub() == vidjet.üslublar().uşaqlar[0])\n'
        'yaz(uzunluq(vidjet.üslub()) > 1000)\n',
        'gətir vidjet\nyaz(vidjet.təqvim(il: 2026, ayı: 2, seçili: '
        '"2026-02-03"))\nyaz(vidjet.təqvim(il: 2024, ayı: 12))\n'
        'yaz(vidjet.karusel(slaydlar: ["a.png", "b.png"], cari: 0))\n',
        'gətir vidjet\nyaz(vidjet.ikiSütun(nisbət: "a:b"))\n',
        'gətir vidjet\nyaz(vidjet.şifrəGücü(şifrə: "Abcdefgh12!x"), '
        'vidjet.şifrəGücü(şifrə: "abc"))\nyaz(vidjet.statistika(etiket: "a",'
        ' dəyər: 1, dəyişmə: "−3,5 %"))\nyaz(vidjet.səhifələmə(səhifə: 5, '
        'cəmi: 12))\nyaz(vidjet.tərəqqi(dəyər: 33, maksimum: 0))\n'
        'yaz(vidjet.dairəQrafiki(dəyərlər: [1, 0, 2.5], halqa: yanlış))\n'
        'yaz(vidjet.cədvəl(sütunlar: ["A"], sətirlər: []))\n',
    ]
    return kodlar


def _vidjet_korpusu() -> list[dict]:
    from sinaq.test_icraci import işlət
    korpus = []
    for kod in _vidjet_kodları():
        s, x = işlət(kod)
        korpus.append({"kod": kod, "giriş": [], "çıxış": list(s),
                       "xəta": x.tip if x else None})
    return korpus


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class VidjetMüqayisəsi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.korpus = _vidjet_korpusu()

    def test_vidjetlər_python_ilə_eyni_HTML_qurur(self):
        from alqor import vidjet as V
        self.assertGreaterEqual(len(self.korpus), 2 * len(V.VİDJETLƏR))
        js = js_işlət(self.korpus, NODE)
        fərqlər = []
        for n, j in zip(self.korpus, js):
            if j["çıxış"] != n["çıxış"] or j["xəta"] != n["xəta"]:
                fərqlər.append(f"{n['kod']}\n  python: {n['çıxış']} "
                               f"{n['xəta']}\n  js    : {j['çıxış']} "
                               f"{j['xəta']}")
        self.assertEqual(fərqlər, [], f"{len(fərqlər)} fərq:\n\n" +
                         "\n\n".join(fərqlər[:4]))

    def test_nümunə_çağırışları_əsasən_xətasızdır(self):
        # Müqayisə yalnız xətaları yoxlamasın: nümunə dəyərləri realdır
        xətalı = [k["kod"] for k in self.korpus if k["xəta"]]
        self.assertLess(len(xətalı), 12, "\n".join(xətalı))


class Kompilyasiya(unittest.TestCase):
    def test_dəstəklənməyən_modul_aydın_xəta_verir(self):
        with self.assertRaises(KompilyasiyaXətası) as k:
            mətndən("gətir veb\nyaz(1)\n")
        self.assertIn("veb", str(k.exception))
        self.assertIn("dəstəklənmir", str(k.exception))

    def test_veb_səhifəsi(self):
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı
        x = XətaToplayıcı()
        s = Mənbə.mətndən('yaz("</script> salam")\n', "v.alq", x)
        html = veb_səhifəsi(Parser(Lekser(s, x).leksə(), s, x).ayır(),
                            "Sınaq <1>")
        self.assertIn("<title>Sınaq &lt;1&gt;</title>", html)
        self.assertEqual(html.count("</script>"), 1)
        self.assertIn('id="çıxış"', html)

    def test_qur_hədəf_js(self):
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "salam.alq"
            f.write_text('yaz("salam")\n', encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "qur", "--hədəf",
                 "js", str(f)], cwd=q, capture_output=True, text=True,
                encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            çıxış = Path(q) / "qurma" / "salam.js"
            self.assertTrue(çıxış.is_file())
            r = subprocess.run(
                [sys.executable, str(KÖK / "alqorc.py"), "qur", "--hədəf",
                 "veb", str(f)], cwd=q, capture_output=True, text=True,
                encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((Path(q) / "qurma" / "veb" / "index.html")
                            .is_file())
            if NODE:
                r = subprocess.run([NODE, str(çıxış)], capture_output=True,
                                   text=True, encoding="utf-8")
                self.assertEqual(r.stdout, "salam\n")


class Dil(unittest.TestCase):
    """JS işi zamanı Python icraçısında tapılıb düzəldilən hallar."""

    def test_şərtli_seç_ifadə_halları(self):
        from sinaq.test_icraci import çıxış
        self.assertEqual(çıxış(
            "dəyişən t = 25\nseç\n    hal t < 10 → yaz(\"soyuq\")\n"
            "    hal t < 30 → yaz(\"isti\")\n"
            "    digər hallarda → yaz(\"çox\")\nson\n"), ["isti"])

    def test_lambda_blok_gövdəsi_ver(self):
        from sinaq.test_icraci import çıxış
        self.assertEqual(çıxış(
            "dəyişən say = 0\ndəyişən f = () => blok\n    say += 1\n"
            "    ver say * 10\nson\nf()\nyaz(f())\n"), ["20"])


if __name__ == "__main__":
    unittest.main()
