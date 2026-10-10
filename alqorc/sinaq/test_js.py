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
    from alqor import vidjet_elave
    from sinaq.test_icraci import işlət
    # `avtoTamamlama` proses boyu sayğac işlədir (datalist id-si) — JS
    # tərəfi kimi sıfırdan başlasın
    vidjet_elave._SİYAHI_SAYĞACI[0] = 0
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


def _işlət(yol: Path, *arq: str, js: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(KÖK / "alqorc.py"), "işlət",
         *(["--js"] if js else []), str(yol), *arq],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
        env=dict(os.environ, PYTHONIOENCODING="utf-8", ALQOR_BAŞSIZ="1"))


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class İnterfeysNümunələri(unittest.TestCase):
    """`pəncərə.sınaq` ilə desktop nümunələri: Python = Node.js."""

    def test_desktop_nümunələri_eyni_nəticə_verir(self):
        for ad in ("06-desktop.alq", "09-tapsiriqlar.alq"):
            with self.subTest(ad):
                f = KÖK.parent / "numuneler" / ad
                py, js = _işlət(f, "--", "sınaq"), _işlət(f, "--", "sınaq",
                                                          js=True)
                self.assertEqual(py.returncode, 0, py.stderr)
                self.assertEqual(js.returncode, 0, js.stderr)
                self.assertEqual(js.stdout, py.stdout)

    def test_vidjet_nümunəsi_veb_hissəsinə_qədər_eynidir(self):
        f = KÖK.parent / "numuneler" / "08-vidjetler.alq"
        py, js = _işlət(f, "--", "sınaq"), _işlət(f, "--", "sınaq", js=True)
        sərhəd = "── Vebdə eyni komponent ──"
        self.assertIn(sərhəd, py.stdout)
        self.assertEqual(js.stdout, py.stdout.split(sərhəd)[0] + sərhəd + "\n")
        # Statik saytda server yoxdur — aydın icra xətası
        self.assertIn("`veb.Server` JS hədəfində (brauzerdə) dəstəklənmir",
                      js.stderr)

    def test_veb_yalnız_interfeys_proqramında_icazəlidir(self):
        with self.assertRaises(KompilyasiyaXətası):
            mətndən("gətir veb\nyaz(1)\n")
        js = mətndən("gətir pəncərə\ngətir veb\nyaz(1)\n")
        self.assertTrue('$.modulQeyd("veb"' in js)


@unittest.skipIf(NODE is None, "Node.js tapılmadı")
class HTTPMüştərisi(unittest.TestCase):
    """`http` modulu Node.js-də sinxron işləyir — Python ilə eyni nəticə."""

    @classmethod
    def setUpClass(cls):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        class İdarə(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _cavab(self, kod, gövdə, növ="application/json"):
                b = gövdə.encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", növ + "; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.send_header("X-Alqor", "bəli".encode().decode("latin-1"))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                if self.path.startswith("/json"):
                    self._cavab(200, json.dumps(
                        {"ad": "Aysel", "yaş": 30, "dillər": ["az", "en"],
                         "yol": self.path}, ensure_ascii=False))
                elif self.path == "/yox":
                    self._cavab(404, "tapılmadı", "text/plain")
                else:
                    self._cavab(200, "salam, dünya", "text/plain")

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                gövdə = self.rfile.read(n).decode("utf-8")
                self._cavab(201, json.dumps({
                    "növ": self.headers.get("Content-Type"),
                    "gövdə": gövdə, "x": self.headers.get("X-Test")},
                    ensure_ascii=False))

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), İdarə)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_python_ilə_eyni(self):
        u = f"http://127.0.0.1:{self.port}"
        kod = f'''gətir http
dəyişən c = gözlə http.al("{u}/mətn")
yaz(c.kod(), c.uğurlu(), c.mətn(), c.başlıq("content-type"))
dəyişən j = gözlə http.al("{u}/json", parametrlər: {{"a": "b c"}})
yaz(j.json()["ad"], j.json()["dillər"], j.json()["yol"])
dəyişən y = gözlə http.al("{u}/yox")
yaz(y.kod(), y.uğurlu(), y.mətn())
cəhd et
    y.yoxla()
tut x
    yaz("xəta:", x.mesaj)
son
dəyişən p = gözlə http.göndər("{u}/a", json: {{"ad": "Rəşad", "n": [1, 2.5]}},
                              başlıqlar: {{"X-Test": "1"}})
yaz(p.kod(), p.json()["növ"], p.json()["gövdə"], p.json()["x"])
dəyişən f = gözlə http.göndər("{u}/a", forma: {{"ad": "Ə b", "s": 3}})
yaz(f.json()["növ"], f.json()["gövdə"])
dəyişən s = yeni http.Sorğu("GÖNDƏR", "{u}/a")
s.başlıq("X-Test", "2").gövdə("düz mətn")
dəyişən r = gözlə s.göndər()
yaz(s.metod(), r.json()["gövdə"], r.json()["növ"], r.json()["x"])
cəhd et
    gözlə http.al("{u}/json").json()
    gözlə http.al("{u}/mətn").json()
tut x
    yaz("JSON:", x.tip)
son
cəhd et
    http.al("ftp://x")
tut x
    yaz(x.tip, x.mesaj)
son
'''
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "h.alq"
            f.write_text(kod, encoding="utf-8")
            py, js = _işlət(f), _işlət(f, js=True)
        self.assertEqual(py.returncode, 0, py.stdout + py.stderr)
        self.assertEqual(js.returncode, 0, js.stdout + js.stderr)
        self.assertIn("salam, dünya", py.stdout)
        self.assertEqual(js.stdout, py.stdout)

    def test_bağlantı_xətası(self):
        js = mətndən('gətir http\ncəhd et\n    gözlə http.al('
                     '"http://127.0.0.1:1/")\ntut x\n    yaz(x.tip)\nson\n')
        with tempfile.TemporaryDirectory() as q:
            f = Path(q) / "p.js"
            f.write_text(js, encoding="utf-8")
            r = subprocess.run([NODE, str(f)], capture_output=True,
                               text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.stdout, "BağlantıXətası\n", r.stderr)


# ═══════════════════════════════════════════════════════════════════════
#  Brauzer: statik interfeys səhifəsi Chromium-da (Playwright)
# ═══════════════════════════════════════════════════════════════════════

def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


SAYĞAC = """gətir pəncərə

komponent Sayğac
    vəziyyət say: tam = 0
    göstər()
        qaytar <button klik={() => özü.say += 1}>Basıldı: {özü.say}</button>
    son
son

dəyişən p = yeni pəncərə.Pəncərə("Sayğac", 320, 200)
p.məzmun(<Sayğac />)
p.göstər()
pəncərə.işlət()
"""

İNTERFEYS = """gətir pəncərə
gətir pəncərə.dialoq
gətir vidjet

komponent Kart
    xassə ad: mətn = ""
    göstər()
        qaytar <li sinif="kart">{özü.ad}</li>
    son
son

komponent Forma
    vəziyyət ad: mətn = ""
    vəziyyət adlar: siyahı[mətn] = []
    vəziyyət razı: məntiq = yanlış
    vəziyyət cavab: mətn = ""

    metod yazıldı(d: mətn)
        özü.ad = d
    son
    metod razılıq(d: məntiq)
        özü.razı = d
    son
    metod əlavə()
        özü.adlar = özü.adlar + [özü.ad]
        özü.ad = ""
    son
    metod soruş()
        əgər dialoq.təsdiqlə("Silinsin?", "hamısı") onda
            özü.adlar = []
        son
        özü.cavab = dialoq.soruş("Ad", "yazın") ?? "yox"
    son

    göstər()
        qaytar <div>
            {vidjet.form(göndərildi: özü.əlavə, məzmun: [
                vidjet.sahə(etiket: "Ad", ad: "ad", dəyər: özü.ad,
                            yazıldı: özü.yazıldı),
                vidjet.qeyd(etiket: "Razıyam", ad: "razı",
                            işarələnmiş: özü.razı, dəyişdi: özü.razılıq),
                vidjet.düymə(mətn: "Əlavə et", klik: özü.əlavə)])}
            <p id="say">{uzunluq(özü.adlar)} ad, razı: {mətnƏt(özü.razı)}</p>
            <ul>{özü.adlar.çevir((a) => <Kart ad={a} />)}</ul>
            <button id="sil" klik={özü.soruş}>Sil</button>
            <p id="cavab">{özü.cavab}</p>
        </div>
    son
son

dəyişən p = yeni pəncərə.Pəncərə("Forma")
p.menyu([pəncərə.menyu("Fayl", [
    pəncərə.element("Bağla", qısayol: "Ctrl+Q", klik: () => p.bağla())])])
p.üslub(x".kart{color:rgb(255, 0, 0)}")
p.məzmun(<Forma />)
p.göstər()
yaz("konsola")
pəncərə.işlət()
"""


@unittest.skipIf(_playwright() is None, "playwright yoxdur")
class Brauzer(unittest.TestCase):
    """`alqor yerləşdir` nəticəsi serversiz işləyir: klik → DOM yenilənir."""

    @classmethod
    def setUpClass(cls):
        cls.q = tempfile.TemporaryDirectory()
        cls.pw = _playwright()().start()
        try:
            cls.brauzer = cls.pw.chromium.launch()
        except Exception as x:                      # noqa: BLE001
            cls.pw.stop()
            cls.q.cleanup()
            raise unittest.SkipTest(f"Chromium açılmadı: {x}")

    @classmethod
    def tearDownClass(cls):
        cls.brauzer.close()
        cls.pw.stop()
        cls.q.cleanup()

    def _səhifə(self, kod: str, ad: str = "p"):
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı
        x = XətaToplayıcı()
        s = Mənbə.mətndən(kod, ad + ".alq", x)
        html = veb_səhifəsi(Parser(Lekser(s, x).leksə(), s, x).ayır(), ad)
        yol = Path(self.q.name) / (ad + ".html")
        yol.write_text(html, encoding="utf-8")
        səhifə = self.brauzer.new_page()
        self.xətalar: list[str] = []
        self.konsol: list[str] = []
        səhifə.on("pageerror", lambda e: self.xətalar.append(str(e)))
        səhifə.on("console", lambda m: self.konsol.append(m.text))
        self.addCleanup(səhifə.close)
        return səhifə, yol

    def test_readme_sayğacı_klikdə_yenilənir(self):
        s, yol = self._səhifə(SAYĞAC, "sayğac")
        s.goto(yol.as_uri())
        self.assertEqual(s.title(), "Sayğac")
        düymə = s.locator("#alqor-kök button")
        self.assertEqual(düymə.inner_text(), "Basıldı: 0")
        for _ in range(3):
            düymə.click()
        self.assertEqual(düymə.inner_text(), "Basıldı: 3")
        self.assertEqual(self.xətalar, [])

    def test_vidjetlər_sahə_fokusu_dialoq_və_menyu(self):
        s, yol = self._səhifə(İNTERFEYS, "forma")
        cavablar = []

        def dialoq(d):
            cavablar.append((d.type, d.message))
            d.accept("Leyla") if d.type == "prompt" else d.accept()
        s.on("dialog", dialoq)
        s.goto(yol.as_uri())
        # Vidjet üslubu və pəncərənin öz üslubu qoşulub
        self.assertIn("v-düymə", s.content())
        sahə = s.locator("#ad")
        sahə.click()
        s.keyboard.type("Aysel", delay=15)
        # Hər hərfdə yenidən göstərilir, amma yazılan mətn və fokus qalır
        self.assertEqual(sahə.input_value(), "Aysel")
        self.assertTrue(s.evaluate("document.activeElement.id === 'ad'"))
        s.click("button:text-is('Əlavə et')")
        self.assertEqual(sahə.input_value(), "")
        sahə.click()
        s.keyboard.type("Rəşad")
        s.keyboard.press("Enter")                     # forma göndərildi
        self.assertEqual(s.inner_text("#say"), "2 ad, razı: yanlış")
        kartlar = s.locator("li.kart")
        self.assertEqual(kartlar.all_inner_texts(), ["Aysel", "Rəşad"])
        self.assertEqual(kartlar.first.evaluate(
            "e => getComputedStyle(e).color"), "rgb(255, 0, 0)")
        s.click("#razı")
        self.assertEqual(s.inner_text("#say"), "2 ad, razı: doğru")
        s.click("#sil")
        self.assertEqual(cavablar, [("confirm", "Silinsin?\n\nhamısı"),
                                    ("prompt", "Ad\n\nyazın")])
        self.assertEqual(s.inner_text("#say"), "0 ad, razı: doğru")
        self.assertEqual(s.inner_text("#cavab"), "Leyla")
        self.assertIn("konsola", self.konsol)
        # Menyu qısayolu: Ctrl+Q pəncərəni bağlayır
        s.keyboard.press("Control+q")
        self.assertIn("Pəncərə bağlandı", s.inner_text("#alqor-kök"))
        self.assertEqual(self.xətalar, [])

    def test_http_brauzerdə_sinxron_sorğu(self):
        import functools
        import threading
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        kod = ('gətir pəncərə\ngətir http\n'
               'komponent Yükləyici\n    vəziyyət mətn: mətn = "-"\n'
               '    metod yüklə()\n'
               '        dəyişən c = gözlə http.al(sistem_ünvanı() + "/d.json")\n'
               '        özü.mətn = "{c.kod()} {c.json()["ad"]}"\n    son\n'
               '    göstər()\n        qaytar <button klik={özü.yüklə}>'
               '{özü.mətn}</button>\n    son\nson\n'
               'funksiya sistem_ünvanı() -> mətn\n    qaytar "ÜNVAN"\nson\n'
               'dəyişən p = yeni pəncərə.Pəncərə("h")\np.məzmun(<Yükləyici />)\n'
               'p.göstər()\n')
        (Path(self.q.name) / "d.json").write_text('{"ad": "Aysel"}',
                                                   encoding="utf-8")
        class Səssiz(SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(
            Səssiz, directory=self.q.name))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        ünvan = f"http://127.0.0.1:{server.server_address[1]}"
        s, yol = self._səhifə(kod.replace("ÜNVAN", ünvan), "http")
        s.goto(f"{ünvan}/{yol.name}")
        s.click("#alqor-kök button")
        self.assertEqual(s.inner_text("#alqor-kök button"), "200 Aysel")
        self.assertEqual(self.xətalar, [])

    def test_idarəedici_xətası_interfeysi_silmir(self):
        kod = ("gətir pəncərə\ngətir pəncərə.dialoq\n"
               "dəyişən p = yeni pəncərə.Pəncərə(\"x\")\n"
               "p.məzmun(<button klik={() => dialoq.faylAç()}>Aç</button>)\n"
               "p.göstər()\n")
        s, yol = self._səhifə(kod, "xeta")
        s.goto(yol.as_uri())
        s.click("button:text-is('Aç')")
        self.assertIn("brauzerdə dəstəklənmir",
                      s.inner_text("#alqor-xəta-qutusu"))
        self.assertEqual(s.locator("#alqor-kök button").count(), 1)

    def test_nümunələr_brauzerdə_işləyir(self):
        nümunələr = KÖK.parent / "numuneler"
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        def aç(ad):
            x = XətaToplayıcı()
            m = Mənbə.fayldan(nümunələr / ad, x)
            html = veb_səhifəsi(Parser(Lekser(m, x).leksə(), m, x).ayır(),
                                ad, (nümunələr / ad).resolve())
            yol = Path(self.q.name) / (ad + ".html")
            yol.write_text(html, encoding="utf-8")
            s = self.brauzer.new_page()
            self.addCleanup(s.close)
            xətalar = []
            s.on("pageerror", lambda e: xətalar.append(str(e)))
            s.on("dialog", lambda d: d.accept())
            s.goto(yol.as_uri())
            return s, xətalar

        s, x = aç("06-desktop.alq")
        s.click("button:text-is('+')")
        s.click("button:text-is('+')")
        self.assertEqual(s.inner_text("h1"), "2")
        s.click("button:text-is('Sıfırla')")          # təsdiq → bəli
        self.assertEqual(s.inner_text("h1"), "0")
        self.assertEqual(x, [])

        s, x = aç("08-vidjetler.alq")
        s.click("input[type=search]")
        s.keyboard.type("rəşad", delay=15)
        mətn = s.inner_text("#alqor-kök")
        self.assertIn("Rəşad Əliyev", mətn)
        self.assertNotIn("Aysel", mətn)
        self.assertEqual(s.input_value("input[type=search]"), "rəşad")
        s.click("button:text-is('Ayarlar')")
        self.assertTrue(s.is_checked("#bildirişlər"))
        s.click(".v-açar")
        self.assertFalse(s.is_checked("#bildirişlər"))
        self.assertEqual(x, [])

        s, x = aç("09-tapsiriqlar.alq")
        s.click("#yeniAd")
        s.keyboard.type("Süd al")
        s.click("button:text-is('Əlavə et')")
        s.click("tr:has-text('Süd al')")
        self.assertIn("1 / 1 bitib", s.inner_text("#alqor-kök"))
        self.assertEqual(x, [])


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
