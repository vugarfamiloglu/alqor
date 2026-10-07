"""`alqorls` — Dil Serveri Protokolu (LSP)."""

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import alqorls as L                               # noqa: E402

KÖK = Path(__file__).parent.parent
URI = "file:///tmp/sinaq.alqor"

MƏNBƏ = '''getir vidjet
/// Müstəvidə nöqtə.
sinif Nöqtə
    qurucu(açıq xassə x: tam, açıq xassə y: tam)

    /// Koordinatların cəmi.
    metod cəm() -> tam
        qaytar özü.x + özü.y
    son
son

funksiya hesabla(a: tam) -> tam
    dəyişən n = Nöqtə(a, 2)
    qaytar n.cəm() + n.x + a
son

yaz(hesabla(3))
'''


def _mesajlar(b: bytes) -> list[dict]:
    n = []
    while b:
        başlıq, _, b = b.partition(b"\r\n\r\n")
        uzunluq = int(başlıq.split(b":")[1])
        n.append(json.loads(b[:uzunluq].decode("utf-8")))
        b = b[uzunluq:]
    return n


class Müştəri:
    """Serveri yaddaşda idarə edən sadə LSP müştərisi."""

    def __init__(self):
        self.çıxış = io.BytesIO()
        self.s = L.Server(io.BytesIO(), self.çıxış)
        self.id = 0

    def göndər(self, metod: str, parametrlər=None, bildiriş=False):
        self.çıxış.seek(0)
        self.çıxış.truncate()
        m = {"jsonrpc": "2.0", "method": metod,
             "params": parametrlər or {}}
        if not bildiriş:
            self.id += 1
            m["id"] = self.id
        self.s.emal(m)
        return _mesajlar(self.çıxış.getvalue())

    def sorğu(self, metod: str, parametrlər=None):
        cavablar = [m for m in self.göndər(metod, parametrlər)
                    if m.get("id") == self.id]
        c = cavablar[0]
        if "error" in c:
            raise L.Xəta(c["error"]["code"], c["error"]["message"])
        return c["result"]

    def aç(self, mətn: str, uri: str = URI) -> list[dict]:
        m = self.göndər("textDocument/didOpen", {"textDocument": {
            "uri": uri, "text": mətn, "version": 1}}, bildiriş=True)
        return m[0]["params"]["diagnostics"]

    def dəyiş(self, mətn: str, versiya: int = 2) -> list[dict]:
        m = self.göndər("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": versiya},
            "contentChanges": [{"text": mətn}]}, bildiriş=True)
        return m[0]["params"]["diagnostics"]

    @staticmethod
    def yer(sətir: int, sütun: int) -> dict:
        return {"textDocument": {"uri": URI},
                "position": {"line": sətir, "character": sütun}}


def _mövqe(mətn: str, axtarış: str, əlavə: int = 0, n: int = 1):
    """`axtarış`-ın n-ci rastına uyğun LSP mövqeyi (sətir, sütun)."""
    i = -1
    for _ in range(n):
        i = mətn.index(axtarış, i + 1)
    i += əlavə
    sətir = mətn.count("\n", 0, i)
    return sətir, i - (mətn.rfind("\n", 0, i) + 1)


class MövqeSınağı(unittest.TestCase):
    def test_utf16_çevirmə(self):
        m = L.Mövqelər("ə😀x\nab")
        # 😀 UTF-16-da iki vahiddir
        self.assertEqual(m.lsp(2), {"line": 0, "character": 3})
        self.assertEqual(m.ofset({"line": 0, "character": 3}), 2)
        self.assertEqual(m.ofset({"line": 1, "character": 1}), 5)
        self.assertEqual(m.ofset({"line": 9, "character": 0}), 6)

    def test_uri(self):
        self.assertEqual(L.uri_yolu("file:///tmp/a%20b.alqor"),
                         Path("/tmp/a b.alqor"))
        self.assertEqual(str(L.uri_yolu("file:///C:/x/y.alqor")),
                         str(Path("C:/x/y.alqor")))
        self.assertIsNone(L.uri_yolu("untitled:1"))


class HəyatDövrüSınağı(unittest.TestCase):
    def test_initialize(self):
        m = Müştəri()
        r = m.sorğu("initialize", {"capabilities": {}})
        c = r["capabilities"]
        self.assertEqual(r["serverInfo"]["name"], "alqorls")
        for açar in ("hoverProvider", "definitionProvider",
                     "referencesProvider", "documentSymbolProvider",
                     "documentFormattingProvider", "codeActionProvider"):
            self.assertIn(açar, c)
        self.assertEqual(c["completionProvider"]["triggerCharacters"],
                         ["."])

    def test_bilinməyən_metod(self):
        m = Müştəri()
        with self.assertRaises(L.Xəta) as k:
            m.sorğu("textDocument/olmayan", {})
        self.assertEqual(k.exception.kod, -32601)
        # Bildirişlər cavabsız atlanır
        self.assertEqual(m.göndər("$/olmayan", {}, bildiriş=True), [])

    def test_shutdown_exit(self):
        m = Müştəri()
        self.assertIsNone(m.sorğu("shutdown"))
        with self.assertRaises(L.Xəta):
            m.sorğu("textDocument/hover", Müştəri.yer(0, 0))
        m.göndər("exit", bildiriş=True)
        self.assertFalse(m.s.işləyir)
        self.assertEqual(m.s.çıxış_kodu, 0)

    def test_stdio_prosesi(self):
        def mesaj(o):
            b = json.dumps(o, ensure_ascii=False).encode()
            return b"Content-Length: %d\r\n\r\n" % len(b) + b
        giriş = b"".join([
            mesaj({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {}}),
            mesaj({"jsonrpc": "2.0", "method": "textDocument/didOpen",
                   "params": {"textDocument": {
                       "uri": URI, "version": 1,
                       "text": "dəyişən x: tam = \"a\"\n"}}}),
            mesaj({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}),
            mesaj({"jsonrpc": "2.0", "method": "exit"}),
        ])
        r = subprocess.run(
            [sys.executable, str(KÖK / "alqorc.py"), "ls", "--stdio"],
            input=giriş, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        mesajlar = _mesajlar(r.stdout)
        self.assertEqual(mesajlar[0]["id"], 1)
        diaq = mesajlar[1]["params"]["diagnostics"]
        self.assertEqual(diaq[0]["code"], "ALQ-T001")
        self.assertEqual(mesajlar[2], {"jsonrpc": "2.0", "id": 2,
                                       "result": None})


class DiaqnostikaSınağı(unittest.TestCase):
    def test_sintaksis_xətası(self):
        d = Müştəri().aç("funksiya f(\n")
        self.assertTrue(d)
        self.assertEqual(d[0]["severity"], 1)
        self.assertEqual(d[0]["source"], "alqor")
        self.assertTrue(d[0]["code"].startswith("ALQ-P"))

    def test_tip_xətası_və_yeri(self):
        d = Müştəri().aç('yaz(1)\ndəyişən ad: tam = "Aysel"\n')
        t = [x for x in d if x["code"] == "ALQ-T001"]
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]["range"]["start"]["line"], 1)
        self.assertIn("mətn", t[0]["message"])

    def test_ascii_xəbərdarlığı(self):
        d = Müştəri().aç(MƏNBƏ)
        self.assertEqual([x["code"] for x in d], ["ALQ-L020"])
        self.assertEqual(d[0]["severity"], 2)
        self.assertEqual(d[0]["range"], {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 5}})

    def test_dəyişiklik_və_bağlama(self):
        m = Müştəri()
        m.aç("yaz(1)\n")
        self.assertTrue(m.dəyiş("yaz(\n"))
        self.assertEqual(m.dəyiş("yaz(2)\n", 3), [])
        r = m.göndər("textDocument/didClose",
                     {"textDocument": {"uri": URI}}, bildiriş=True)
        self.assertEqual(r[0]["params"]["diagnostics"], [])

    def test_artımlı_dəyişiklik(self):
        m = Müştəri()
        m.aç("yaz(1)\n")
        m.göndər("textDocument/didChange", {
            "textDocument": {"uri": URI, "version": 2},
            "contentChanges": [{"range": {
                "start": {"line": 0, "character": 4},
                "end": {"line": 0, "character": 5}}, "text": "42"}]},
            bildiriş=True)
        self.assertEqual(m.s.sənədlər[URI].mətn, "yaz(42)\n")


class NaviqasiyaSınağı(unittest.TestCase):
    def setUp(self):
        self.m = Müştəri()
        self.m.aç(MƏNBƏ)

    def p(self, axtarış, əlavə=0, n=1):
        return Müştəri.yer(*_mövqe(MƏNBƏ, axtarış, əlavə, n))

    def test_hover_funksiya(self):
        r = self.m.sorğu("textDocument/hover", self.p("hesabla(3)"))
        self.assertIn("funksiya hesabla(a: tam) -> tam",
                      r["contents"]["value"])

    def test_hover_metod_sənədi(self):
        r = self.m.sorğu("textDocument/hover", self.p("cəm()", 0, 2))
        v = r["contents"]["value"]
        self.assertIn("metod cəm() -> tam", v)
        self.assertIn("Koordinatların cəmi.", v)

    def test_hover_dəyişən_və_sinif(self):
        r = self.m.sorğu("textDocument/hover", self.p("n.cəm"))
        self.assertIn("dəyişən n: Nöqtə", r["contents"]["value"])
        r = self.m.sorğu("textDocument/hover", self.p("Nöqtə(a"))
        self.assertIn("sinif Nöqtə", r["contents"]["value"])
        self.assertIn("Müstəvidə nöqtə.", r["contents"]["value"])

    def test_hover_boş_yer(self):
        self.assertIsNone(self.m.sorğu("textDocument/hover",
                                       Müştəri.yer(4, 0)))

    def test_təyinata_get(self):
        r = self.m.sorğu("textDocument/definition", self.p("hesabla(3)"))
        self.assertEqual(r[0]["range"]["start"],
                         dict(zip(("line", "character"),
                                  _mövqe(MƏNBƏ, "hesabla"))))
        # Metod: `n.cəm()` → sinifdəki elan
        r = self.m.sorğu("textDocument/definition", self.p("cəm()", 0, 2))
        self.assertEqual(r[0]["range"]["start"]["line"], 6)
        # Qısa qurucunun sahəsi: `n.x` → `açıq xassə x`
        r = self.m.sorğu("textDocument/definition", self.p("n.x", 2))
        self.assertEqual(r[0]["range"]["start"]["line"], 3)

    def test_istinadlar_sahə(self):
        r = self.m.sorğu("textDocument/references", {
            **self.p("n.x", 2), "context": {"includeDeclaration": True}})
        self.assertEqual([x["range"]["start"]["line"] for x in r],
                         [3, 7, 13])
        r = self.m.sorğu("textDocument/references", {
            **self.p("n.x", 2), "context": {"includeDeclaration": False}})
        self.assertEqual(len(r), 2)

    def test_ad_dəyişmə(self):
        r = self.m.sorğu("textDocument/rename",
                         {**self.p("a: tam"), "newName": "say"})
        dəyişikliklər = r["changes"][URI]
        self.assertEqual(len(dəyişikliklər), 3)
        self.assertTrue(all(d["newText"] == "say" for d in dəyişikliklər))

    def test_ad_dəyişmə_metod(self):
        r = self.m.sorğu("textDocument/rename",
                         {**self.p("cəm()"), "newName": "toplam"})
        self.assertEqual(
            sorted(d["range"]["start"]["line"] for d in r["changes"][URI]),
            [6, 13])

    def test_ad_dəyişmə_qadağaları(self):
        with self.assertRaises(L.Xəta):
            self.m.sorğu("textDocument/rename",
                         {**self.p("a: tam"), "newName": "əgər"})
        with self.assertRaises(L.Xəta):
            self.m.sorğu("textDocument/rename",
                         {**self.p("a: tam"), "newName": "1x"})
        with self.assertRaises(L.Xəta):                 # daxili funksiya
            self.m.sorğu("textDocument/rename",
                         {**self.p("yaz("), "newName": "çap"})
        self.assertIsNone(self.m.sorğu("textDocument/prepareRename",
                                       self.p("yaz(")))
        r = self.m.sorğu("textDocument/prepareRename", self.p("n.cəm"))
        self.assertEqual(r["placeholder"], "n")

    def test_sənəd_sxemi(self):
        r = self.m.sorğu("textDocument/documentSymbol",
                         {"textDocument": {"uri": URI}})
        self.assertEqual([(s["name"], s["kind"]) for s in r],
                         [("Nöqtə", 5), ("hesabla", 12)])
        uşaqlar = [(s["name"], s["kind"]) for s in r[0]["children"]]
        self.assertEqual(uşaqlar, [("qurucu", 9), ("cəm", 6)])
        self.assertEqual(r[0]["range"]["start"]["line"], 2)
        self.assertEqual(r[0]["range"]["end"]["line"], 9)
        self.assertEqual(r[1]["range"]["end"]["line"], 14)


class BərpaSınağı(unittest.TestCase):
    def test_yarımçıq_sətirdə_hover_işləyir(self):
        m = Müştəri()
        d = m.aç('dəyişən söz = "ab"\nyaz(söz)\nsöz.\n')
        self.assertTrue(any(x["severity"] == 1 for x in d))
        r = m.sorğu("textDocument/hover", Müştəri.yer(1, 5))
        self.assertIn("dəyişən söz: mətn", r["contents"]["value"])
        r = m.sorğu("textDocument/definition", Müştəri.yer(1, 5))
        self.assertEqual(r[0]["range"]["start"], {"line": 0,
                                                  "character": 8})


class QrammatikaSınağı(unittest.TestCase):
    def test_fayllar_açar_sözlərlə_uzlaşır(self):
        from alqor import qrammatika as Q
        for yol, məzmun in Q.fayllar().items():
            self.assertEqual(yol.read_text(encoding="utf-8"), məzmun,
                             f"{yol.name} köhnəlib: python -m "
                             "alqor.qrammatika --yaz")

    def test_ascii_formalar(self):
        from alqor import qrammatika as Q
        q = json.dumps(Q.textmate(), ensure_ascii=False)
        for söz in ("əgər", "eger", "nehayet", "dəyişən",
                    "deyisen"):
            self.assertIn(söz, q)


class TamamlamaSınağı(unittest.TestCase):
    def tamamla(self, mətn: str, sətir: int, sütun: int) -> list[str]:
        m = Müştəri()
        m.aç(mətn)
        r = m.sorğu("textDocument/completion", Müştəri.yer(sətir, sütun))
        return r["items"]

    def test_modul_üzvləri_yarımçıq_kodda(self):
        mətn = "gətir vidjet\nvidjet.\n"
        maddələr = self.tamamla(mətn, 1, 7)
        adlar = [x["label"] for x in maddələr]
        self.assertIn("düymə", adlar)
        self.assertIn("sahə", adlar)
        düymə = next(x for x in maddələr if x["label"] == "düymə")
        self.assertEqual(düymə["kind"], L.K_FUNKSIYA)

    def test_mətn_metodları(self):
        mətn = 'dəyişən s = "abc"\ns.bö\n'
        adlar = [x["label"] for x in self.tamamla(mətn, 1, 4)]
        self.assertIn("böyüyə", adlar)
        self.assertIn("uzunluq", adlar)

    def test_sinif_üzvləri(self):
        mətn = MƏNBƏ + "dəyişən p = Nöqtə(1, 2)\np.\n"
        sətir = mətn.count("\n") - 1
        maddələr = self.tamamla(mətn, sətir, 2)
        növlər = {x["label"]: x["kind"] for x in maddələr}
        self.assertEqual(növlər.get("cəm"), L.K_METOD)
        self.assertIn("x", növlər)

    def test_özü(self):
        mətn = ("sinif A\n    qurucu(açıq xassə ad: mətn)\n"
                "    metod f()\n        yaz(özü.)\n    son\nson\n")
        adlar = [x["label"] for x in self.tamamla(mətn, 3, 16)]
        self.assertIn("ad", adlar)
        self.assertIn("f", adlar)

    def test_ümumi_tamamlama(self):
        mətn = "funksiya topla(a, b)\n    qaytar a + b\nson\n\n"
        maddələr = self.tamamla(mətn, 3, 0)
        adlar = {x["label"]: x for x in maddələr}
        self.assertEqual(adlar["əgər"]["kind"], L.K_ACAR)
        self.assertIn("topla", adlar)
        self.assertIn("yaz", adlar)
        self.assertIn("tam", adlar)
        şablon = adlar["funksiya …"]
        self.assertEqual(şablon["insertTextFormat"], 2)

    def test_gətir_modulları(self):
        adlar = [x["label"] for x in self.tamamla("gətir \n", 0, 6)]
        self.assertIn("riyaziyyat", adlar)
        self.assertIn("vidjet", adlar)
        self.assertNotIn("əgər", adlar)

    def test_şərhdə_və_mətndə_yox(self):
        self.assertEqual(self.tamamla("// salam \n", 0, 9), [])
        self.assertEqual(self.tamamla('yaz("sal\n', 0, 8), [])

    def test_imza_köməyi(self):
        mətn = ("funksiya topla(a: tam, b: tam) -> tam\n"
                "    qaytar a + b\nson\ntopla(1, \n")
        m = Müştəri()
        m.aç(mətn)
        r = m.sorğu("textDocument/signatureHelp", Müştəri.yer(3, 9))
        self.assertEqual(r["signatures"][0]["label"],
                         "topla(a: tam, b: tam) -> tam")
        self.assertEqual(r["activeParameter"], 1)


class FormatVəDüzəlişSınağı(unittest.TestCase):
    def test_formatlama(self):
        m = Müştəri()
        m.aç("funksiya f()\nyaz(1)\nson\n")
        r = m.sorğu("textDocument/formatting", {
            "textDocument": {"uri": URI},
            "options": {"tabSize": 4, "insertSpaces": True}})
        self.assertEqual(r[0]["newText"], "funksiya f()\n    yaz(1)\nson\n")
        # Artıq səliqəli — dəyişiklik yoxdur
        m.dəyiş(r[0]["newText"])
        self.assertEqual(m.sorğu("textDocument/formatting", {
            "textDocument": {"uri": URI}, "options": {}}), [])

    def test_sintaksis_xətasında_format_yoxdur(self):
        m = Müştəri()
        m.aç("funksiya f(\n")
        cavab = m.göndər("textDocument/formatting", {
            "textDocument": {"uri": URI}, "options": {}})
        self.assertEqual(cavab[0]["method"], "window/showMessage")
        self.assertIsNone(cavab[1]["result"])

    def test_ascii_düzəlişi(self):
        m = Müştəri()
        m.aç(MƏNBƏ)
        r = m.sorğu("textDocument/codeAction", {
            "textDocument": {"uri": URI},
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 0, "character": 5}},
            "context": {"diagnostics": []}})
        tez = [x for x in r if x["kind"] == "quickfix"]
        self.assertEqual(tez[0]["title"], "`gətir` ilə əvəz et")
        self.assertEqual(tez[0]["edit"]["changes"][URI][0]["newText"],
                         "gətir")
        hamısı = [x for x in r if x["kind"] == "source.fixAll.alqor"]
        self.assertTrue(hamısı[0]["edit"]["changes"][URI][0]["newText"]
                        .startswith("gətir vidjet\n"))

    def test_bəlkə_təklifi(self):
        m = Müştəri()
        m.aç('dəyişən s = "a"\nyaz(s.uzunlug())\n')
        r = m.sorğu("textDocument/codeAction", {
            "textDocument": {"uri": URI},
            "range": {"start": {"line": 1, "character": 0},
                      "end": {"line": 1, "character": 15}},
            "context": {"diagnostics": []}})
        başlıqlar = [x["title"] for x in r]
        self.assertIn("`uzunluq` ilə əvəz et", başlıqlar)


KÖMƏK = """/// İki ədədin cəmi.
funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son

sabit ƏMSAL = 3
"""

ƏSAS = """gətir "./kömək.alqor" kimi k
gətir "./kömək".{topla}

dəyişən x = k.topla(1, 2) + topla(3, 4) * k.ƏMSAL
yaz(x)
"""

DİGƏR = """gətir "./kömək.alqor".{topla kimi cəm}
yaz(cəm(1, 1))
"""


class LayihəSınağı(unittest.TestCase):
    """Fayllar arası: `gətir "./x.alqor"` — keçid, istinad, ad dəyişmə."""

    def setUp(self):
        import tempfile
        self._q = tempfile.TemporaryDirectory()
        self.kök = Path(self._q.name)
        (self.kök / "kömək.alqor").write_text(KÖMƏK, encoding="utf-8")
        (self.kök / "əsas.alqor").write_text(ƏSAS, encoding="utf-8")
        alt = self.kök / "alt"
        alt.mkdir()
        (alt / "digər.alqor").write_text(
            DİGƏR.replace("./kömək", "../kömək"), encoding="utf-8")
        self.m = Müştəri()
        self.m.sorğu("initialize", {"capabilities": {},
                                    "rootUri": self.kök.as_uri()})
        self.uri = (self.kök / "əsas.alqor").as_uri()
        self.m.aç(ƏSAS, self.uri)

    def tearDown(self):
        self._q.cleanup()

    def yer(self, axtarış, n=1, əlavə=1):
        s, c = _mövqe(ƏSAS, axtarış, əlavə, n)
        return {"textDocument": {"uri": self.uri},
                "position": {"line": s, "character": c}}

    def test_tip_yoxlaması_faylları_görür(self):
        d = self.m.aç(ƏSAS.replace("topla(3, 4)", 'topla(3, "a")'),
                      self.uri)
        self.assertTrue(any("ALQ-T004" == x.get("code") for x in d), d)
        d = self.m.aç(ƏSAS.replace("k.ƏMSAL", "k.yoxdur"), self.uri)
        self.assertTrue(any("ALQ-M002" == x.get("code") for x in d), d)

    def test_təyinata_keçid_başqa_fayla(self):
        for yer in (self.yer("k.topla", əlavə=3), self.yer("topla(3")):
            r = self.m.sorğu("textDocument/definition", yer)
            self.assertEqual(len(r), 1)
            self.assertTrue(r[0]["uri"].endswith("k%C3%B6m%C9%99k.alqor")
                            or r[0]["uri"].endswith("kömək.alqor"),
                            r[0]["uri"])
            self.assertEqual(r[0]["range"]["start"],
                             {"line": 1, "character": 9})

    def test_hover_başqa_fayldan(self):
        h = self.m.sorğu("textDocument/hover", self.yer("k.topla", əlavə=3))
        self.assertIn("funksiya topla(a: tam, b: tam) -> tam",
                      h["contents"]["value"])
        self.assertIn("kömək.alqor", h["contents"]["value"])

    def test_istinadlar_layihə_üzrə(self):
        r = self.m.sorğu("textDocument/references", {
            **self.yer("topla(3"), "context": {"includeDeclaration": True}})
        fayllar = {}
        for x in r:
            ad = Path(L.uri_yolu(x["uri"])).name
            fayllar[ad] = fayllar.get(ad, 0) + 1
        # elan (kömək) + idxal siyahısı, k.topla, topla(3 (əsas)
        # + idxal siyahısı (digər, ləqəbli — `cəm` istifadəsi deyil)
        self.assertEqual(fayllar, {"kömək.alqor": 1, "əsas.alqor": 3,
                                   "digər.alqor": 1})

    def test_ad_dəyişmə_layihə_üzrə(self):
        r = self.m.sorğu("textDocument/rename", {
            **self.yer("topla(3"), "newName": "cəmlə"})
        dəyişikliklər = {Path(L.uri_yolu(u)).name: len(v)
                         for u, v in r["changes"].items()}
        self.assertEqual(dəyişikliklər, {"kömək.alqor": 1, "əsas.alqor": 3,
                                         "digər.alqor": 1})
        # Tətbiq edilmiş mətn yenə də düzgün yoxlanır
        for u, v in r["changes"].items():
            yol = L.uri_yolu(u)
            mətn = self.m.s._açıq_mətn(yol) or yol.read_text("utf-8")
            mv = L.Mövqelər(mətn)
            for d in sorted(v, key=lambda d: -mv.ofset(d["range"]["start"])):
                b = mv.ofset(d["range"]["start"])
                e = mv.ofset(d["range"]["end"])
                self.assertEqual(mətn[b:e], "topla")
                mətn = mətn[:b] + d["newText"] + mətn[e:]
            yol.write_text(mətn, encoding="utf-8")
        a = L.analiz_et((self.kök / "əsas.alqor").read_text("utf-8"),
                        "əsas.alqor", self.kök / "əsas.alqor")
        self.assertEqual([d for d in a.diaqnostikalar if d.xətadır], [])

    def test_ləqəbli_ad_yerli_qalır(self):
        uri = (self.kök / "alt" / "digər.alqor").as_uri()
        mətn = DİGƏR.replace("./kömək", "../kömək")
        self.m.aç(mətn, uri)
        s, c = _mövqe(mətn, "cəm(1", 1)
        r = self.m.sorğu("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": s, "character": c},
            "context": {"includeDeclaration": True}})
        self.assertEqual({x["uri"] for x in r}, {uri})
        self.assertEqual(len(r), 2)

    def test_açıq_sənəd_dəyişəndə_asılılar_yenilənir(self):
        kuri = (self.kök / "kömək.alqor").as_uri()
        self.m.aç(KÖMƏK, kuri)
        m = self.m.göndər("textDocument/didChange", {
            "textDocument": {"uri": kuri, "version": 2},
            "contentChanges": [{"text": KÖMƏK.replace(
                "b: tam) -> tam", "b: mətn) -> tam").replace(
                "a + b", "a")}]}, bildiriş=True)
        əsas = [x for x in m if x["params"]["uri"] == self.uri]
        self.assertTrue(əsas)
        self.assertTrue(any(d.get("code") == "ALQ-T004"
                            for d in əsas[-1]["params"]["diagnostics"]))

    def test_iş_sahəsi_simvolları(self):
        r = self.m.sorğu("workspace/symbol", {"query": "tpl"})
        self.assertEqual([x["name"] for x in r], ["topla"])
        r = self.m.sorğu("workspace/symbol", {"query": ""})
        adlar = {x["name"] for x in r}
        self.assertTrue({"topla", "ƏMSAL", "x"} <= adlar, adlar)

    def test_dövri_idxal_donmur(self):
        (self.kök / "a.alqor").write_text(
            'gətir "./b.alqor" kimi b\nfunksiya f() -> tam\n'
            '    qaytar 1\nson\n', encoding="utf-8")
        (self.kök / "b.alqor").write_text(
            'gətir "./a.alqor" kimi a\nfunksiya g() -> tam\n'
            '    qaytar a.f()\nson\n', encoding="utf-8")
        a = L.analiz_et((self.kök / "a.alqor").read_text("utf-8"),
                        "a.alqor", self.kök / "a.alqor")
        self.assertIsNotNone(a.yoxlayıcı)


if __name__ == "__main__":
    unittest.main()
