"""Alqor Studio — server, fayl API, diaqnostika, skelet, klaviatura, icra."""

import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KÖK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KÖK))

from alqor import vidjet as V                                 # noqa: E402
from studio import klaviatura as K                            # noqa: E402
from studio import sablonlar                                  # noqa: E402
from studio import skelet as S                                # noqa: E402
from studio.diaqnostika import ascii_düzəlt, yoxla            # noqa: E402
from studio.layihe import Layihə, YolXətası                   # noqa: E402
from studio.qurulus import KOD, MƏTN, ŞƏRH, Mətn, xəritə      # noqa: E402
from studio.server import Studio                              # noqa: E402

NÜMUNƏLƏR = KÖK.parent / "numuneler"


def xətalar(mətn: str) -> list[dict]:
    """Ayrılma + tip yoxlaması: xətalar və ALQ-T002 (naməlum tip)."""
    return [d for d in yoxla(mətn)["diaqnostikalar"]
            if d["səviyyə"] == "xəta" or d["kod"] == "ALQ-T002"]


# ═══════════════════════════════════════════════════════════════════════
#  Server köməkçisi
# ═══════════════════════════════════════════════════════════════════════

class ServerSınağı(unittest.TestCase):
    """Hər sınaq sinfi üçün müvəqqəti layihə + port 0-da server."""

    @classmethod
    def setUpClass(cls):
        cls.qovluq = Path(tempfile.mkdtemp(prefix="studio-sınaq-"))
        cls.layihə = cls.qovluq / "layihə"
        cls.layihə.mkdir()
        (cls.layihə / "salam.alq").write_text('yaz("salam")\n',
                                                encoding="utf-8")
        # Layihənin YANINDA, eyni prefiksli qovluq — `startswith`
        # yoxlaması olsaydı bura çatmaq olardı
        cls.qonşu = cls.qovluq / "layihə-gizli"
        cls.qonşu.mkdir()
        (cls.qonşu / "sirr.txt").write_text("SİRR", encoding="utf-8")
        (cls.qovluq / "kənar.txt").write_text("KƏNAR", encoding="utf-8")
        cls.studio = Studio(cls.layihə).fonda_başlat()

    @classmethod
    def tearDownClass(cls):
        cls.studio.dayandır()
        shutil.rmtree(cls.qovluq, ignore_errors=True)

    def sorğu(self, üsul, yol, gövdə=None, nişan=True, host=None,
              tip="application/json", başlıqlar=None):
        c = http.client.HTTPConnection("127.0.0.1", self.studio.port,
                                       timeout=30)
        b = {"Host": host or f"127.0.0.1:{self.studio.port}"}
        if nişan is True:
            b["X-Alqor-Token"] = self.studio.nişan
        elif nişan:
            b["X-Alqor-Token"] = nişan
        data = None
        if gövdə is not None:
            data = json.dumps(gövdə).encode("utf-8")
            b["Content-Type"] = tip
        b.update(başlıqlar or {})
        c.request(üsul, yol, body=data, headers=b)
        r = c.getresponse()
        mətn = r.read()
        c.close()
        try:
            d = json.loads(mətn)
        except ValueError:
            d = mətn
        return r.status, d, r

    def api(self, yol, gövdə=None):
        üsul = "GET" if gövdə is None else "POST"
        kod, d, _ = self.sorğu(üsul, yol, gövdə)
        return kod, d


# ═══════════════════════════════════════════════════════════════════════
#  1. Nişan (token), Host və HTTP qaydaları
# ═══════════════════════════════════════════════════════════════════════

class NişanVəTəhlükəsizlik(ServerSınağı):

    def test_server_yalnız_127_0_0_1_dinləyir(self):
        self.assertEqual(self.studio.server.server_address[0], "127.0.0.1")

    def test_nişansız_api_rədd_edilir(self):
        kod, d, _ = self.sorğu("GET", "/api/melumat", nişan=False)
        self.assertEqual(kod, 401)
        self.assertIn("nişan", d["xəta"])

    def test_yanlış_nişan_rədd_edilir(self):
        kod, _, _ = self.sorğu("GET", "/api/melumat", nişan="yanlis-nisan")
        self.assertEqual(kod, 401)
        kod, _, _ = self.sorğu("POST", "/api/fayl/oxu", {"yol": "salam.alq"},
                               nişan=False)
        self.assertEqual(kod, 401)

    def test_düzgün_nişan_qəbul_edilir(self):
        kod, d = self.api("/api/melumat")
        self.assertEqual(kod, 200)
        self.assertEqual(d["ad"], "layihə")

    def test_nişan_sorğu_sətrində_də_işləyir(self):
        # EventSource başlıq göndərə bilmir — `?t=` lazımdır
        kod, _, _ = self.sorğu("GET", f"/api/agac?t={self.studio.nişan}",
                               nişan=False)
        self.assertEqual(kod, 200)

    def test_nişan_hər_sessiyada_fərqlidir(self):
        digər = Studio(self.layihə)
        try:
            self.assertNotEqual(digər.nişan, self.studio.nişan)
            self.assertGreaterEqual(len(self.studio.nişan), 24)
        finally:
            digər.server.server_close()

    def test_yad_host_rədd_edilir(self):
        # DNS rebinding: hücumçunun domeni 127.0.0.1-ə yönəlsə də olmaz
        kod, _, _ = self.sorğu("GET", "/api/melumat",
                               host=f"pis.example:{self.studio.port}")
        self.assertEqual(kod, 403)
        kod, _, _ = self.sorğu("GET", "/", host="pis.example")
        self.assertEqual(kod, 403)

    def test_localhost_host_icazəlidir(self):
        kod, _, _ = self.sorğu("GET", "/api/melumat",
                               host=f"localhost:{self.studio.port}")
        self.assertEqual(kod, 200)

    def test_post_yalnız_json(self):
        kod, _, _ = self.sorğu("POST", "/api/fayl/oxu", {"yol": "salam.alq"},
                               tip="text/plain")
        self.assertEqual(kod, 415)

    def test_interfeys_nişansız_verilir_və_csp_var(self):
        kod, mətn, r = self.sorğu("GET", "/", nişan=False)
        self.assertEqual(kod, 200)
        self.assertIn(b"Alqor Studio", mətn)
        self.assertIn("script-src 'self'",
                      r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")

    def test_statik_fayllar(self):
        for ad in ("studio.js", "redaktor.js", "dil.js", "studio.css"):
            kod, _, _ = self.sorğu("GET", f"/statik/{ad}", nişan=False)
            self.assertEqual(kod, 200, ad)

    def test_statik_qovluqdan_qaçmaq_olmur(self):
        for yol in ("/statik/../server.py", "/statik/..%2fserver.py",
                    "/statik/%2e%2e/layihe.py", "/statik/../../alqorc.py"):
            kod, _, _ = self.sorğu("GET", yol, nişan=False)
            self.assertEqual(kod, 404, yol)

    def test_server_başlığı_ascii(self):
        _, _, r = self.sorğu("GET", "/api/melumat")
        r.getheader("Server").encode("ascii")

    def test_naməlum_api(self):
        kod, _ = self.api("/api/yoxdur")
        self.assertEqual(kod, 404)



# ═══════════════════════════════════════════════════════════════════════
#  Layihədə axtarış və dil əməliyyatları (istinadlar, simvollar, ad dəyiş)
# ═══════════════════════════════════════════════════════════════════════

class AxtarışVəDil(ServerSınağı):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        (cls.layihə / "alt").mkdir()
        (cls.layihə / "alt" / "riyazi.alq").write_text(
            "funksiya cəm(a: tam, b: tam) -> tam\n    qaytar a + b\nson\n",
            encoding="utf-8")
        (cls.layihə / "esas.alq").write_text(
            'gətir "alt/riyazi.alq" kimi r\nyaz(r.cəm(1, 2))\n'
            "yaz(r.cəm(3, 4))\n", encoding="utf-8")
        (cls.layihə / "qeyd.txt").write_text("Salam Dünya\nsalam\n",
                                             encoding="utf-8")
        (cls.layihə / ".gizli").mkdir()
        (cls.layihə / ".gizli" / "x.txt").write_text("salam",
                                                     encoding="utf-8")

    def test_axtar_seçimlər(self):
        kod, d = self.api("/api/axtar", {"sorğu": "salam"})
        self.assertEqual(kod, 200, d)
        yollar = {f["yol"] for f in d["fayllar"]}
        self.assertIn("qeyd.txt", yollar)
        self.assertIn("salam.alq", yollar)
        self.assertNotIn(".gizli/x.txt", yollar)
        # hərf həssaslığı
        _, d2 = self.api("/api/axtar", {"sorğu": "Salam", "hərf": True})
        self.assertEqual(d2["say"], 1)
        # filtr
        _, d3 = self.api("/api/axtar", {"sorğu": "salam", "filtr": "*.txt"})
        self.assertEqual([f["yol"] for f in d3["fayllar"]], ["qeyd.txt"])
        # regex və sütun
        _, d4 = self.api("/api/axtar", {"sorğu": r"cəm\(\d", "regex": True})
        s = d4["fayllar"][0]["sətirlər"][0]
        self.assertEqual((s["no"], s["sütun"], s["uzunluq"]), (2, 7, 5))
        # tam söz
        _, d5 = self.api("/api/axtar", {"sorğu": "cə", "söz": True})
        self.assertEqual(d5["say"], 0)

    def test_axtar_açıq_mətn_nəzərə_alınır(self):
        _, d = self.api("/api/axtar", {
            "sorğu": "yadda", "açıqlar": {"salam.alq": "yaddaşda\n"}})
        self.assertEqual(d["say"], 1)
        kod, _ = self.api("/api/axtar", {
            "sorğu": "x", "açıqlar": {"../kənar.txt": "x"}})
        self.assertEqual(kod, 403)

    def test_axtar_xətalar(self):
        self.assertEqual(self.api("/api/axtar", {"sorğu": ""})[0], 400)
        self.assertEqual(self.api("/api/axtar",
                                  {"sorğu": "(", "regex": True})[0], 400)

    def test_əvəzlə(self):
        (self.layihə / "dəyiş.txt").write_text("a-1 a-2\n", encoding="utf-8")
        kod, d = self.api("/api/axtar/evezle", {
            "sorğu": r"a-(\d)", "regex": True, "əvəz": r"b\1",
            "filtr": "dəyiş.txt"})
        self.assertEqual(kod, 200, d)
        self.assertEqual(d["say"], 2)
        self.assertEqual((self.layihə / "dəyiş.txt").read_text(
            encoding="utf-8"), "b1 b2\n")
        # regex olmayanda tərs xətt hərfi qalır
        self.api("/api/axtar/evezle", {"sorğu": "b1", "əvəz": r"c\1",
                                       "filtr": "dəyiş.txt"})
        self.assertEqual((self.layihə / "dəyiş.txt").read_text(
            encoding="utf-8"), "c\\1 b2\n")

    def _dil(self, metod, yol, sətir, sütun, **əlavə):
        mətn = (self.layihə / yol).read_text(encoding="utf-8")
        return self.api("/api/dil", {"metod": metod, "yol": yol,
                                     "mətn": mətn, "sətir": sətir,
                                     "sütun": sütun, **əlavə})

    def test_simvollar(self):
        kod, d = self._dil("simvollar", "alt/riyazi.alq", 0, 0)
        self.assertEqual(kod, 200, d)
        self.assertIn("cəm", [x["name"] for x in d["nəticə"]])

    def test_istinadlar_layihə_üzrə(self):
        kod, d = self._dil("istinadlar", "alt/riyazi.alq", 0, 10)
        self.assertEqual(kod, 200, d)
        yollar = sorted(x["yol"] for x in d["nəticə"])
        self.assertEqual(yollar.count("esas.alq"), 2)
        self.assertIn("alt/riyazi.alq", yollar)

    def test_ad_dəyiş(self):
        kod, d = self._dil("adDəyiş", "alt/riyazi.alq", 0, 10,
                           yeniAd="topla")
        self.assertEqual(kod, 200, d)
        n = d["nəticə"]
        self.assertIn("funksiya topla(", n["alt/riyazi.alq"])
        self.assertEqual(n["esas.alq"].count("r.topla("), 2)
        # disk dəyişmir — Studio özü yazır
        self.assertIn("cəm", (self.layihə / "esas.alq").read_text(
            encoding="utf-8"))
        kod, _ = self._dil("adDəyiş", "alt/riyazi.alq", 0, 10,
                           yeniAd="1yanlış")
        self.assertEqual(kod, 400)

    def test_naməlum_metod(self):
        self.assertEqual(self._dil("nəsə", "salam.alq", 0, 0)[0], 400)


# ═══════════════════════════════════════════════════════════════════════
#  2. Fayl API — layihə qovluğu ilə məhdudlaşma
# ═══════════════════════════════════════════════════════════════════════

KƏNAR_YOLLAR = [
    "../kənar.txt",
    "a/../../kənar.txt",
    "./../kənar.txt",
    "..\\kənar.txt",
    "../layihə-gizli/sirr.txt",            # prefiks hiyləsi
    "/etc/passwd",
    "\\etc\\passwd",
    "C:/Windows/win.ini",
    "c:\\windows\\win.ini",
    "salam.alq\x00.txt",
]


class FaylAPI(ServerSınağı):

    def test_oxu(self):
        kod, d = self.api("/api/fayl/oxu", {"yol": "salam.alq"})
        self.assertEqual(kod, 200)
        self.assertEqual(d["mətn"], 'yaz("salam")\n')

    def test_kənara_çıxan_yollar_oxunmur(self):
        for yol in KƏNAR_YOLLAR:
            kod, d = self.api("/api/fayl/oxu", {"yol": yol})
            self.assertIn(kod, (400, 403), yol)
            self.assertNotIn("SİRR", json.dumps(d, ensure_ascii=False))
            self.assertNotIn("KƏNAR", json.dumps(d, ensure_ascii=False))

    def test_kənara_yazmaq_olmur(self):
        for yol in KƏNAR_YOLLAR:
            for api, gövdə in (
                    ("/api/fayl/yaz", {"yol": yol, "mətn": "PİS"}),
                    ("/api/fayl/yarat", {"yol": yol, "növ": "fayl"}),
                    ("/api/fayl/sil", {"yol": yol}),
                    ("/api/fayl/adlandir", {"yol": "salam.alq",
                                            "yeni": yol})):
                kod, _ = self.api(api, gövdə)
                self.assertIn(kod, (400, 403), f"{api} {yol!r}")
        self.assertEqual((self.qovluq / "kənar.txt").read_text("utf-8"),
                         "KƏNAR")
        self.assertTrue((self.qonşu / "sirr.txt").exists())
        self.assertTrue((self.layihə / "salam.alq").exists())

    def test_simvolik_keçid_kənara_aparmır(self):
        keçid = self.layihə / "keçid"
        try:
            os.symlink(self.qonşu, keçid)
        except (OSError, NotImplementedError):
            self.skipTest("simvolik keçid yaradıla bilmir")
        try:
            kod, _ = self.api("/api/fayl/oxu", {"yol": "keçid/sirr.txt"})
            self.assertEqual(kod, 403)
            kod, d = self.api("/api/agac")
            self.assertNotIn("keçid", [e["ad"] for e in d["uşaqlar"]])
        finally:
            keçid.unlink()

    def test_kök_silinmir(self):
        for yol in ("", ".", "./"):
            kod, _ = self.api("/api/fayl/sil", {"yol": yol})
            self.assertIn(kod, (400, 403), repr(yol))
        self.assertTrue(self.layihə.is_dir())

    def test_yarat_yaz_adlandır_sil(self):
        kod, d = self.api("/api/fayl/yarat",
                          {"yol": "qovluq/yeni.alq", "növ": "fayl"})
        self.assertEqual(kod, 200)
        self.assertEqual(d["yol"], "qovluq/yeni.alq")
        kod, _ = self.api("/api/fayl/yaz", {"yol": "qovluq/yeni.alq",
                                            "mətn": "yaz(\"ə\")\n"})
        self.assertEqual(kod, 200)
        self.assertEqual((self.layihə / "qovluq/yeni.alq").read_bytes(),
                         'yaz("ə")\n'.encode("utf-8"))
        kod, _ = self.api("/api/fayl/yarat", {"yol": "qovluq/yeni.alq"})
        self.assertEqual(kod, 409)
        kod, d = self.api("/api/fayl/adlandir", {"yol": "qovluq/yeni.alq",
                                                 "yeni": "qovluq/köhnə.alq"})
        self.assertEqual((kod, d["yol"]), (200, "qovluq/köhnə.alq"))
        kod, d = self.api("/api/agac")
        adlar = [e["ad"] for e in d["uşaqlar"]]
        self.assertIn("qovluq", adlar)
        kod, _ = self.api("/api/fayl/sil", {"yol": "qovluq"})
        self.assertEqual(kod, 200)
        self.assertFalse((self.layihə / "qovluq").exists())

    def test_utf8_olmayan_fayl(self):
        (self.layihə / "köhnə.txt").write_bytes("şəhər".encode("cp1254",
                                                               "replace")
                                                + b"\xff\xfe")
        kod, d = self.api("/api/fayl/oxu", {"yol": "köhnə.txt"})
        self.assertEqual(kod, 415)
        self.assertIn("UTF-8", d["xəta"])

    def test_layihə_sinfi_birbaşa(self):
        L = Layihə(self.layihə)
        with self.assertRaises(YolXətası):
            L.yol("../kənar.txt")
        self.assertEqual(L.yol("a/./b.alq"), self.layihə / "a" / "b.alq")


# ═══════════════════════════════════════════════════════════════════════
#  3. Diaqnostika
# ═══════════════════════════════════════════════════════════════════════

class Diaqnostika(ServerSınağı):

    def test_tip_xətasının_yeri(self):
        kod = 'yaz("salam")\ndəyişən yaş: tam = "on"\n'
        d = yoxla(kod)
        x = [p for p in d["diaqnostikalar"] if p["səviyyə"] == "xəta"]
        self.assertEqual(len(x), 1)
        self.assertEqual(x[0]["kod"], "ALQ-T001")
        self.assertEqual((x[0]["sətir"], x[0]["sütun"]), (2, 20))

    def test_bağlanmamış_mətn(self):
        d = yoxla('dəyişən a = 1\n  yaz("salam)\n')
        x = d["diaqnostikalar"][0]
        self.assertEqual(x["kod"], "ALQ-L003")
        self.assertEqual((x["sətir"], x["sütun"]), (2, 7))

    def test_ascii_xəbərdarlığı_sayılır(self):
        d = yoxla("eger doğru onda\n    yaz(1)\nson\n")
        self.assertEqual(d["ascii"], 1)
        self.assertEqual(d["xəta"], 0)
        x = d["diaqnostikalar"][0]
        self.assertEqual((x["kod"], x["sətir"], x["sütun"]),
                         ("ALQ-L020", 1, 1))
        self.assertEqual((x["sonSətir"], x["sonSütun"]), (1, 5))

    def test_api_diaqnostika(self):
        kod, d = self.api("/api/yoxla", {
            "mətn": "funksiya f() -> tam\n    qaytar \"x\"\nson\n",
            "ad": "a.alq"})
        self.assertEqual(kod, 200)
        x = [p for p in d["diaqnostikalar"] if p["səviyyə"] == "xəta"]
        self.assertTrue(x)
        self.assertEqual(x[0]["sətir"], 2)

    def test_nümunələr_təmizdir(self):
        for f in sorted(NÜMUNƏLƏR.glob("*.alq")):
            d = yoxla(f.read_text(encoding="utf-8"), f.name)
            self.assertEqual(d["xəta"], 0, f.name)

    def test_ascii_düzəlt(self):
        mətn, say = ascii_düzəlt(
            'deyisen eger_deyil = 1\neger ozu onda yaz("eger") son\n')
        self.assertEqual(say, 3)
        self.assertEqual(
            mətn, 'dəyişən eger_deyil = 1\nəgər özü onda yaz("eger") son\n')

    def test_formatlayıcı(self):
        kod, d = self.api("/api/formatla",
                          {"mətn": "eger a onda\nyaz(1,2)\n  son\n"})
        self.assertEqual(kod, 200)
        self.assertEqual(d["mətn"], "əgər a onda\n    yaz(1, 2)\nson\n")
        self.assertTrue(d["dəyişdi"])

    def test_formatlayıcı_sintaksis_xətası(self):
        kod, d = self.api("/api/formatla", {"mətn": "əgər a onda\n"})
        self.assertEqual(kod, 422)
        self.assertIn("sintaksis", d["xəta"])


# ═══════════════════════════════════════════════════════════════════════
#  4. Skelet — iki klikdə işləyən kod
# ═══════════════════════════════════════════════════════════════════════

JSX_KOMPONENT = """\
gətir pəncərə

komponent Sayğac
    vəziyyət say: tam = 0

    metod artır()
        özü.say += 1
    son

    göstər()
        qaytar <div sinif="sayğac">
            <h1>{özü.say}</h1>
            <button klik={özü.artır}>+</button>
        </div>
    son
son
"""

SİYAHI_KOMPONENT = """\
gətir vidjet

komponent Panel
    vəziyyət sahə1: mətn = ""

    metod sahə1Dəyişdi(dəyər: mətn)
        özü.sahə1 = dəyər
    son

    // Görünüş
    göstər()
        qaytar vidjet.sütun(boşluq: 12, məzmun: [
            vidjet.sahə(etiket: "Ad", ad: "sahə1",
                        dəyər: özü.sahə1, dəyişdi: özü.sahə1Dəyişdi)
        ])
    son
son
"""

BAŞQA_KOD = """\
// Hesablama
gətir riyaziyyat

funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son
"""


class Debaq(ServerSınağı):
    """Studio → `alqorc.py dap`: dayanma, addım, dəyişənlər."""

    KOD = ("funksiya kvadrat(n: tam) -> tam\n"
           "    dəyişən k = n * n\n"
           "    qaytar k\n"
           "son\n"
           "dəyişən cəm = 0\n"
           "hər x üçün [1, 2, 3] içində\n"
           "    cəm += kvadrat(x)\n"
           "son\n"
           "yaz(\"cəm: {cəm}\")\n")

    def hadisə(self, iş, n, növ, müddət=20):
        son = time.monotonic() + müddət
        while time.monotonic() < son:
            hadisələr, _ = iş.hadisələri_al(n, 1.0)
            for h in hadisələr:
                n = h["n"] + 1
                if h["növ"] == növ:
                    return h, n
        self.fail(f"{növ} hadisəsi gəlmədi")

    def test_debaq_sessiyası(self):
        (self.layihə / "debaq.alq").write_text(self.KOD, encoding="utf-8")
        kod, d = self.api("/api/debaq", {
            "yol": "debaq.alq", "nöqtələr": {"debaq.alq": [3]}})
        self.assertEqual(kod, 200, d)
        iş = self.studio.icra.al(d["id"])
        h, n = self.hadisə(iş, 0, "dayandı")
        self.assertEqual(h["səbəb"], "breakpoint")
        self.assertEqual([k["ad"] for k in h["yığın"]], ["kvadrat", "<əsas>"])
        self.assertEqual(h["yığın"][0]["yol"], "debaq.alq")
        self.assertEqual(h["yığın"][0]["sətir"], 3)
        yerli = {v["ad"]: v["dəyər"] for v in h["sahələr"][0]["dəyişənlər"]}
        self.assertEqual(yerli, {"n": "1", "k": "1"})
        # ifadə
        kod, r = self.api("/api/debaq/hesabla", {"id": d["id"],
                                                 "ifadə": "k * 10"})
        self.assertEqual((kod, r["dəyər"]), (200, "10"))
        # çağıranın kadrı
        kod, r = self.api("/api/debaq/kadr", {
            "id": d["id"], "kadr": h["yığın"][1]["id"]})
        qlobal = {v["ad"]: v["dəyər"] for v in r["sahələr"][0]["dəyişənlər"]}
        self.assertEqual(qlobal["cəm"], "0")
        # növbəti addım → 4-cü sətrə yox, çağırana qayıdana qədər
        kod, r = self.api("/api/debaq/emr", {"id": d["id"], "əmr": "çıx"})
        self.assertEqual(kod, 200, r)
        h, n = self.hadisə(iş, n, "dayandı")
        self.assertEqual(h["yığın"][0]["ad"], "<əsas>")
        # nöqtələri sil, davam et → bitir
        self.api("/api/debaq/noqteler", {"id": d["id"],
                                         "nöqtələr": {"debaq.alq": []}})
        self.api("/api/debaq/emr", {"id": d["id"], "əmr": "davam"})
        h, n = self.hadisə(iş, n, "bitdi")
        self.assertEqual(h["kod"], 0)
        çıxış = "".join(x["mətn"] for x in iş.hadisələr
                        if x["növ"] == "çıxış")
        self.assertIn("cəm: 14", çıxış)

    def test_dayanmamışda_əmr_rədd_edilir(self):
        (self.layihə / "sonsuz.alq").write_text(
            "dəyişən i = 0\nhəmişə\n    i += 1\nson\n", encoding="utf-8")
        kod, d = self.api("/api/debaq", {"yol": "sonsuz.alq"})
        iş = self.studio.icra.al(d["id"])
        time.sleep(0.5)
        kod, r = self.api("/api/debaq/emr", {"id": d["id"],
                                             "əmr": "növbəti"})
        self.assertEqual(kod, 409)
        self.api("/api/debaq/emr", {"id": d["id"], "əmr": "fasilə"})
        h, _ = self.hadisə(iş, 0, "dayandı")
        self.assertEqual(h["səbəb"], "pause")
        self.api("/api/islet/dayandir", {"id": d["id"]})
        self.hadisə(iş, 0, "bitdi")

    def test_kənar_yol_rədd_edilir(self):
        kod, _ = self.api("/api/debaq", {
            "yol": "salam.alq", "nöqtələr": {"../kənar.alq": [1]}})
        self.assertEqual(kod, 403)


class Dizayner(unittest.TestCase):
    """Vizual dizayner: ağac, əlavə et, daşı, sil — kod dəyişir."""

    KOD = """gətir vidjet

komponent Forma
    vəziyyət ad: mətn = ""

    göstər()
        qaytar vidjet.sütun(boşluq: 12, məzmun: [
            vidjet.başlıq("Qeydiyyat"),
            // ad sahəsi
            vidjet.sahə(etiket: "Ad", dəyər: özü.ad),
            vidjet.sətir([
                vidjet.düymə(mətn: "Ləğv"),
                vidjet.düymə(mətn: "Göndər", növ: "əsas")
            ]),
            özü.əlavə
        ])
    son
son
"""

    def setUp(self):
        from studio import dizayner
        self.D = dizayner

    def göstər(self, mətn):
        return mətn[mətn.index("qaytar"):mətn.index("    son\nson")]

    def adlar(self, mətn):
        k = self.D.ağac(mətn)["kök"]

        def gəz(d):
            if d.get("konteyner"):
                return [d["ad"] or "?", [gəz(u) for u in d["uşaqlar"]]]
            return (d["ad"] or "?") + (f":{d['xülasə']}" if d["xülasə"]
                                       else "")
        return gəz(k)

    def test_ağac(self):
        a = self.D.ağac(self.KOD)
        self.assertEqual(a["komponent"], "Forma")
        self.assertEqual(self.adlar(self.KOD), [
            "sütun", ["başlıq:Qeydiyyat", "sahə:Ad",
                      ["sətir", ["düymə:Ləğv", "düymə:Göndər"]],
                      "?:özü.əlavə"]])
        k = a["kök"]
        self.assertEqual(k["istiqamət"], "şaquli")
        self.assertEqual(k["uşaqlar"][2]["istiqamət"], "üfüqi")
        self.assertEqual(k["uşaqlar"][2]["yol"], [2])
        self.assertEqual(k["uşaqlar"][2]["uşaqlar"][1]["yol"], [2, 1])
        self.assertEqual(self.KOD[k["uşaqlar"][1]["mövqe"]:][:4], "sahə")

    def test_eyni_siyahıda_yer_dəyişmə(self):
        n = self.D.köçür(self.KOD, [0], [], 3)
        self.assertEqual(self.adlar(n["mətn"])[1][:3],
                         ["sahə:Ad", ["sətir", ["düymə:Ləğv", "düymə:Göndər"]],
                          "başlıq:Qeydiyyat"])
        self.assertEqual(n["yol"], [2])
        # şərh elementlə birlikdə qalır
        self.assertIn("// ad sahəsi\n            vidjet.sahə", n["mətn"])

    def test_başqa_konteynerə_daşıma(self):
        n = self.D.köçür(self.KOD, [0], [2], 1)
        self.assertEqual(self.adlar(n["mətn"]), [
            "sütun", ["sahə:Ad",
                      ["sətir", ["düymə:Ləğv", "başlıq:Qeydiyyat",
                                 "düymə:Göndər"]], "?:özü.əlavə"]])
        self.assertEqual(n["yol"], [1, 1])
        # konteynerdən çıxarma
        n2 = self.D.köçür(n["mətn"], [1, 2], [], 0)
        self.assertEqual(self.adlar(n2["mətn"])[1][0], "düymə:Göndər")
        # girinti: çoxsətirli element yeni yerə uyğunlaşır
        self.assertIn('                vidjet.başlıq("Qeydiyyat"),',
                      n["mətn"])

    def test_sil_və_qadağalar(self):
        n = self.D.sil(self.KOD, [2, 0])
        self.assertEqual(self.adlar(n["mətn"])[1][2],
                         ["sətir", ["düymə:Göndər"]])
        n = self.D.sil(n["mətn"], [2, 0])
        self.assertIn("vidjet.sətir([])", n["mətn"])
        with self.assertRaises(self.D.DizaynXətası):
            self.D.sil(self.KOD, [])
        with self.assertRaises(self.D.DizaynXətası):
            self.D.köçür(self.KOD, [2], [2], 0)          # öz içinə
        with self.assertRaises(self.D.DizaynXətası):
            self.D.köçür(self.KOD, [0], [1], 0)          # konteyner deyil
        with self.assertRaises(self.D.DizaynXətası):
            self.D.sil(self.KOD, [9])

    def test_paletdən_əlavə(self):
        n = self.D.əlavə_et(self.KOD, "nişan", [2], 1)
        self.assertEqual(self.adlar(n["mətn"])[1][2][1][1].split(":")[0],
                         "nişan")
        self.assertEqual(n["yol"], [2, 1])
        # nəticə ayrılır və tip yoxlamasından keçir
        from studio import diaqnostika
        d = diaqnostika.yoxla(n["mətn"], "f.alq")
        self.assertEqual([x for x in d["diaqnostikalar"]
                          if x["səviyyə"] == "xəta"], [], n["mətn"])

    def test_vəziyyət_və_metod_ilə_əlavə(self):
        n = self.D.əlavə_et(self.KOD, "sahə", [], 0)
        self.assertIn("vəziyyət sahə1", n["mətn"])
        self.assertEqual(self.adlar(n["mətn"])[1][0], "sahə:Ad")
        self.assertEqual(n["yol"], [0])

    def test_kök_yoxdursa(self):
        a = self.D.ağac("komponent A\n    göstər()\n        qaytar <p>x</p>"
                        "\n    son\nson\n")
        self.assertIsNone(a["kök"])
        with self.assertRaises(self.D.DizaynXətası):
            self.D.ağac("yaz(1)\n")


class Skelet(unittest.TestCase):

    def təmizdir(self, mətn, ad=""):
        x = xətalar(mətn)
        self.assertEqual(x, [], f"{ad}\n{mətn}")

    def test_boş_fayl_komponent_və_əsas_qurur(self):
        n = S.vidjet_əlavə_et("", "sahə")
        self.təmizdir(n.mətn)
        self.assertTrue(n.mətn.startswith("gətir vidjet\ngətir pəncərə\n"))
        self.assertIn("komponent Tətbiq", n.mətn)
        self.assertIn('vəziyyət sahə1: mətn = ""', n.mətn)
        self.assertIn("metod sahə1Dəyişdi(dəyər: mətn)", n.mətn)
        self.assertIn("funksiya əsas()", n.mətn)
        self.assertIn("p.məzmun(<Tətbiq />)", n.mətn)
        # Kursor vidjet çağırışının üzərindədir
        self.assertTrue(n.mətn[n.kursor:].startswith("vidjet.sahə("))

    def test_komponentsiz_fayl(self):
        n = S.vidjet_əlavə_et(BAŞQA_KOD, "düymə")
        self.təmizdir(n.mətn)
        sətirlər = n.mətn.split("\n")
        self.assertEqual(sətirlər[:3], ["// Hesablama", "gətir riyaziyyat",
                                        "gətir vidjet"])
        # Komponent mövcud koddan ƏVVƏL, funksiya toxunulmamış qalır
        self.assertLess(n.mətn.index("komponent Tətbiq"),
                        n.mətn.index("funksiya topla"))
        self.assertIn("funksiya topla(a: tam, b: tam) -> tam\n"
                      "    qaytar a + b\nson", n.mətn)
        self.assertNotIn("funksiya əsas", n.mətn)
        self.assertIn("klik: özü.düymə1Basıldı", n.mətn)

    def test_mövcud_komponent_jsx(self):
        n = S.vidjet_əlavə_et(JSX_KOMPONENT, "sahə")
        self.təmizdir(n.mətn)
        m = n.mətn
        # Vəziyyət mövcud vəziyyətdən sonra
        self.assertIn('    vəziyyət say: tam = 0\n'
                      '    vəziyyət sahə1: mətn = ""\n', m)
        # İdarəedici `göstər()`-dən əvvəl
        self.assertLess(m.index("metod sahə1Dəyişdi"), m.index("göstər()"))
        self.assertLess(m.index("metod artır"), m.index("metod sahə1Dəyişdi"))
        # Çağırış JSX-in içində, kök teqin bağlanışından əvvəl
        self.assertIn('            <button klik={özü.artır}>+</button>\n'
                      '            {vidjet.sahə(etiket: "Ad", ad: "sahə1",\n',
                      m)
        self.assertIn("dəyişdi: özü.sahə1Dəyişdi)}\n        </div>", m)
        self.assertEqual(m.count("gətir vidjet"), 1)
        self.assertTrue(m.startswith("gətir pəncərə\ngətir vidjet\n"))

    def test_məzmun_siyahısı_və_təkrar_ad(self):
        n = S.vidjet_əlavə_et(SİYAHI_KOMPONENT, "sahə")
        self.təmizdir(n.mətn)
        m = n.mətn
        self.assertIn('vəziyyət sahə2: mətn = ""', m)
        self.assertIn("metod sahə2Dəyişdi", m)
        self.assertIn("dəyişdi: özü.sahə1Dəyişdi),\n"
                      '            vidjet.sahə(etiket: "Ad", ad: "sahə2",\n'
                      "                        dəyər: özü.sahə2, "
                      "dəyişdi: özü.sahə2Dəyişdi)\n        ])", m)
        # Şərh `göstər()`-ə aiddir — metod şərhdən əvvələ yazılır
        self.assertIn("    son\n\n    // Görünüş\n    göstər()", m)
        self.assertEqual(m.count("gətir vidjet"), 1)

    def test_üç_dəfə_ard_arda(self):
        m = JSX_KOMPONENT
        for _ in range(3):
            m = S.vidjet_əlavə_et(m, "sahə").mətn
        self.təmizdir(m)
        for i in (1, 2, 3):
            self.assertEqual(m.count(f"vəziyyət sahə{i}:"), 1)
            self.assertEqual(m.count(f"metod sahə{i}Dəyişdi"), 1)
        self.assertNotIn("sahə4", m)

    def test_sabit_adların_toqquşması(self):
        # `parol` kataloqda sabit `şifrə` adı işlədir
        m = S.vidjet_əlavə_et(JSX_KOMPONENT, "parol").mətn
        m = S.vidjet_əlavə_et(m, "parol").mətn
        self.təmizdir(m)
        self.assertEqual(m.count("vəziyyət şifrə:"), 1)
        self.assertEqual(m.count("vəziyyət şifrə2:"), 1)
        self.assertIn("dəyişdi: özü.şifrə2Dəyişdi", m)

    def test_istifadəçinin_mövcud_adı_ilə_toqquşma(self):
        kod = JSX_KOMPONENT.replace("vəziyyət say: tam = 0",
                                    "vəziyyət say: tam = 0\n"
                                    "    vəziyyət düymə1: tam = 0")
        n = S.vidjet_əlavə_et(kod, "düymə")
        self.assertIn("metod düymə1Basıldı", n.mətn)    # ad tutulmayıb
        kod2 = kod.replace("metod artır()", "metod düymə1Basıldı()")
        kod2 = kod2.replace("özü.artır", "özü.düymə1Basıldı")
        n2 = S.vidjet_əlavə_et(kod2, "düymə")
        self.assertIn("metod düymə2Basıldı", n2.mətn)
        self.təmizdir(n2.mətn)

    def test_istifadəçi_adı(self):
        n = S.vidjet_əlavə_et(JSX_KOMPONENT, "sahə", None, "istifadəçiAdı")
        self.assertIn('vəziyyət istifadəçiAdı: mətn = ""', n.mətn)
        self.assertIn("metod istifadəçiAdıDəyişdi", n.mətn)
        self.təmizdir(n.mətn)
        with self.assertRaises(S.SkeletXətası):
            S.vidjet_əlavə_et(JSX_KOMPONENT, "sahə", None, "əgər")

    def test_gətir_vidjet_təkrarlanmır(self):
        m = SİYAHI_KOMPONENT
        for v in ("düymə", "tərəqqi", "modal"):
            m = S.vidjet_əlavə_et(m, v).mətn
        self.assertEqual(m.count("gətir vidjet"), 1)
        self.təmizdir(m)

    def test_göstərsiz_komponent(self):
        kod = "komponent Boş\n    vəziyyət x: tam = 0\nson\n"
        n = S.vidjet_əlavə_et(kod, "açar")
        self.təmizdir(n.mətn)
        self.assertIn("    göstər()\n        qaytar vidjet.sütun(", n.mətn)
        self.assertLess(n.mətn.index("metod açar1Dəyişdi"),
                        n.mətn.index("göstər()"))

    def test_sadə_ifadə_sütuna_bükülür(self):
        kod = ("gətir vidjet\nkomponent A\n    göstər()\n"
               '        qaytar vidjet.mətn(məzmun: "salam")\n    son\nson\n')
        n = S.vidjet_əlavə_et(kod, "cədvəl")
        self.təmizdir(n.mətn)
        self.assertIn("qaytar vidjet.sütun(boşluq: 12, məzmun: [\n"
                      '            vidjet.mətn(məzmun: "salam"),\n'
                      "            vidjet.cədvəl(", n.mətn)
        # Nümunədə işlənməyən idarəedici hadisəyə bağlanır
        self.assertIn("sətirKlik: özü.sətirBasıldı", n.mətn)

    def test_kursorun_yerinə_qoyulur(self):
        kod = ("gətir vidjet\nkomponent A\n    göstər()\n"
               "        qaytar vidjet.sütun(məzmun: [\n"
               '            vidjet.mətn(məzmun: "a"),\n'
               "\n"
               '            vidjet.mətn(məzmun: "b")\n'
               "        ])\n    son\nson\n")
        kursor = kod.index("\n\n") + 1
        n = S.vidjet_əlavə_et(kod, "düymə", kursor)
        self.təmizdir(n.mətn)
        a = n.mətn.index('məzmun: "a"')
        d = n.mətn.index("vidjet.düymə(")
        b = n.mətn.index('məzmun: "b"')
        self.assertLess(a, d)
        self.assertLess(d, b)
        self.assertIn("klik: özü.düymə1Basıldı),\n", n.mətn)

    def test_bütün_kataloq_tip_yoxlamasından_keçir(self):
        """Bütün vidjetlərin hər biri iki dəfə əlavə olunur — xəta, T002 yox."""
        for m in V.KATALOQ:
            with self.subTest(vidjet=m.ad):
                for baza in ("", JSX_KOMPONENT, SİYAHI_KOMPONENT, BAŞQA_KOD):
                    bir = S.vidjet_əlavə_et(baza, m.ad).mətn
                    iki = S.vidjet_əlavə_et(bir, m.ad).mətn
                    self.assertEqual(xətalar(iki), [], f"{m.ad}\n{iki}")
                    self.assertEqual(iki.count("gətir vidjet"), 1)
                    self.assertIn(f"vidjet.{m.ad}(", iki)

    def test_tamEn_düzəldilir(self):
        n = S.vidjet_əlavə_et("", "tərəqqi")
        self.assertIn("vəziyyət tərəqqi1: tam = 0", n.mətn)
        self.assertNotIn("tamEn", n.mətn)

    def test_yeni_sətirlər_qeyd_olunur(self):
        n = S.vidjet_əlavə_et(JSX_KOMPONENT, "sahə")
        sətirlər = n.mətn.split("\n")
        yeni = [sətirlər[i - 1] for a, b in n.yeni_sətirlər
                for i in range(a, b + 1)]
        self.assertIn("gətir vidjet", yeni)
        self.assertIn('    vəziyyət sahə1: mətn = ""', yeni)
        self.assertNotIn("    metod artır()", yeni)

    def test_naməlum_vidjet(self):
        with self.assertRaises(S.SkeletXətası) as k:
            S.vidjet_əlavə_et("", "sahe")
        self.assertIn("sahə", str(k.exception))

    # ── Mövcud çağırışın üzərinə iki klik ──

    def test_tamamla_çatışmayanları_yazır(self):
        kod = ("komponent Forma\n    göstər()\n        qaytar <div>\n"
               '            {vidjet.sahə(etiket: "Ad", ad: "ad")}\n'
               '            {vidjet.parol(etiket: "Şifrə", ad: "şifrə",\n'
               "                          dəyişdi: özü.şifrəDəyişdi)}\n"
               "        </div>\n    son\nson\n")
        n = S.çağırışı_tamamla(kod, kod.index("parol"))
        self.assertTrue(n.dəyişdi)
        self.assertIn('vəziyyət şifrə: mətn = ""', n.mətn)
        self.assertIn("metod şifrəDəyişdi(dəyər: mətn)", n.mətn)
        self.assertTrue(n.mətn.startswith("gətir vidjet\n"))
        self.assertTrue(n.mətn[n.kursor:].startswith("parol("))

        # Bağlanmamış `sahə` — arqumentlər də əlavə olunur, ad `ad:`-dan
        m = n.mətn
        n2 = S.çağırışı_tamamla(m, m.index("vidjet.sahə"))
        self.assertIn('vəziyyət ad: mətn = ""', n2.mətn)
        self.assertIn("metod adDəyişdi(dəyər: mətn)", n2.mətn)
        self.assertIn('{vidjet.sahə(etiket: "Ad", ad: "ad",\n'
                      "                         dəyər: özü.ad, "
                      "dəyişdi: özü.adDəyişdi)}", n2.mətn)
        self.assertEqual(xətalar(n2.mətn), [])

        # İkinci dəfə — dəyişiklik yoxdur
        n3 = S.çağırışı_tamamla(n2.mətn, n2.mətn.index("vidjet.sahə"))
        self.assertFalse(n3.dəyişdi)
        self.assertEqual(n3.mətn, n2.mətn)

    def test_tamamla_kursor_çağırışda_deyil(self):
        with self.assertRaises(S.SkeletXətası):
            S.çağırışı_tamamla(JSX_KOMPONENT, 5)

    def test_bir_klik_nümunəsi_və_iki_klik(self):
        """Paletdən bir klik nümunə qoyur, üzərinə iki klik tamamlayır."""
        kod = SİYAHI_KOMPONENT
        nümunə = S.nümunə_hazırla(kod, "ədəd", kod.index("göstər"))
        self.assertIn('ad: "ədəd1"', nümunə)
        yer = kod.index("        ])")
        kod = kod[:yer] + "            ,\n" + kod[yer:]
        kod = kod.replace("            ,\n",
                          "            " + nümunə.replace(
                              "\n", "\n            ") + "\n")
        kod = kod.replace("sahə1Dəyişdi)\n            vidjet.ədəd",
                          "sahə1Dəyişdi),\n            vidjet.ədəd")
        el = {e["ad"]: e for e in S.elementlər(kod)}
        self.assertEqual(el["ədəd"]["çatışmır"], ["ədəd1", "ədəd1Dəyişdi"])
        self.assertEqual(el["sahə"]["çatışmır"], [])
        n = S.çağırışı_tamamla(kod, kod.index("vidjet.ədəd") + 8)
        self.assertIn("vəziyyət ədəd1: tam = 0", n.mətn)
        self.assertIn("özü.ədəd1 = tamƏt(dəyər, 0)", n.mətn)
        self.assertEqual(xətalar(n.mətn), [])

    def test_elementlər_siyahısı(self):
        el = S.elementlər(SİYAHI_KOMPONENT)
        self.assertEqual(len(el), 2)                    # sütun + sahə
        self.assertEqual([e["ad"] for e in el], ["sütun", "sahə"])
        self.assertTrue(all(not e["çatışmır"] for e in el))
        self.assertEqual(el[1]["sətir"], 13)


# ═══════════════════════════════════════════════════════════════════════
#  5. Quruluş və klaviatura
# ═══════════════════════════════════════════════════════════════════════

class Xüsusiyyətlər(unittest.TestCase):
    MƏTN = ("gətir vidjet\nkomponent P\n    göstər()\n"
            "        qaytar vidjet.sütun(məzmun: [\n"
            '            vidjet.düymə(mətn: "Saxla", növ: "əsas",\n'
            "                         klik: özü.saxla),\n"
            '            vidjet.başlıq(mətn: "Salam {ad}")\n'
            "        ])\n    son\nson\n")

    def k(self, söz="düymə"):
        return self.MƏTN.index(söz) + 2

    def test_oxu(self):
        from studio.xususiyyet import oxu
        n = oxu(self.MƏTN, self.k())
        p = {x["ad"]: x for x in n["parametrlər"]}
        self.assertEqual(n["ad"], "düymə")
        self.assertEqual((p["mətn"]["dəyər"], p["mətn"]["növ"]),
                         ("Saxla", "mətn"))
        self.assertEqual(p["növ"]["növ"], "seçim")
        self.assertEqual(p["klik"]["növ"], "hadisə")
        self.assertFalse(p["klik"]["sadə"])
        self.assertEqual(p["söndürülmüş"]["növ"], "məntiq")
        self.assertEqual(n["üslub"], {})
        # Interpolyasiyalı mətn ifadədir — panel toxunmur
        b = {x["ad"]: x for x in oxu(self.MƏTN, self.k("başlıq("))
             ["parametrlər"]}
        self.assertFalse(b["mətn"]["sadə"])

    def test_qoy_dəyiş_əlavə_sil(self):
        from studio.xususiyyet import oxu, qoy
        k = self.k()
        m = qoy(self.MƏTN, k, "mətn", 'De "salam" {x}')["mətn"]
        self.assertIn('vidjet.düymə(mətn: "De \\"salam\\" \\{x\\}"', m)
        m = qoy(m, k, "ölçü", "böyük")["mətn"]
        self.assertIn("klik: özü.saxla,\n                         "
                      'ölçü: "böyük")', m)
        m = qoy(m, k, "üslub.fon", "#fff")["mətn"]
        m = qoy(m, k, "üslub.künc", 8)["mətn"]
        self.assertEqual(oxu(m, k)["üslub"], {"fon": "#fff", "künc": 8})
        for a in ("üslub.fon", "üslub.künc", "ölçü"):
            m = qoy(m, k, a, None)["mətn"]
        self.assertNotIn("üslub", m)
        self.assertNotIn("ölçü", m)
        self.assertIn("klik: özü.saxla),", m)
        # Nəticə həmişə ayrılır
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı
        x = XətaToplayıcı()
        mb = Mənbə.mətndən(m, "t", x)
        Parser(Lekser(mb, x).leksə(), mb, x).ayır()
        self.assertTrue(x.uğurludur(), x.siyahı)

    def test_qadağalar(self):
        from studio.xususiyyet import XüsusiyyətXətası, qoy
        for ad, d in (("klik", "x"), ("yox", 1), ("üslub.pis", "x")):
            with self.assertRaises(XüsusiyyətXətası):
                qoy(self.MƏTN, self.k(), ad, d)
        with self.assertRaises(XüsusiyyətXətası):
            qoy("yaz(1)\n", 2, "mətn", "a")

    def test_api_və_miniatürlər(self):
        from studio.miniatur import hamısı
        from alqor import vidjet as V
        self.assertEqual(set(hamısı()), set(V.VİDJETLƏR))
        self.assertIn("v-düymə", hamısı()["düymə"])


class Quruluş(unittest.TestCase):

    def test_xəritə(self):
        m = 'a = "x{b + "y"}z" // şərh\nx"{c}" /* /* iç */ */ d'
        x = xəritə(m)
        self.assertEqual(x[0], KOD)
        self.assertEqual(x[m.index('"x')], MƏTN)
        self.assertEqual(x[m.index("z")], MƏTN)
        self.assertEqual(x[m.index("şərh")], ŞƏRH)
        self.assertEqual(x[m.index("{c}")], MƏTN)       # xam mətn
        self.assertEqual(x[m.index("iç")], ŞƏRH)
        self.assertEqual(x[m.index(" d") + 1], KOD)

    def test_komponent_üzvləri(self):
        from studio.qurulus import komponentləri_tap
        k = komponentləri_tap(Mətn(JSX_KOMPONENT))
        self.assertEqual(len(k), 1)
        self.assertEqual(k[0].ad, "Sayğac")
        self.assertEqual([(u.növ, u.ad) for u in k[0].üzvlər],
                         [("vəziyyət", "say"), ("metod", "artır"),
                          ("göstər", "göstər")])
        self.assertEqual(k[0].son, 15)


class Klaviatura(unittest.TestCase):

    def test_ascii_açar_sözlər_çevrilir(self):
        self.assertEqual(K.mətni_yaz("eger x onda\n"), "əgər x onda\n")
        self.assertEqual(K.mətni_yaz("deyisen ad = 1\n"), "dəyişən ad = 1\n")
        self.assertEqual(K.mətni_yaz("ozu.ad ve ya b "), "özü.ad və ya b ")
        self.assertEqual(K.mətni_yaz("her x ucun s icinde\n"),
                         "hər x üçün s içində\n")
        self.assertEqual(K.mətni_yaz("ne qeder ki a\n"), "nə qədər ki a\n")

    def test_tip_adları_çevrilir(self):
        self.assertEqual(K.mətni_yaz("x: metn = "), "x: mətn = ")
        self.assertEqual(K.mətni_yaz("siyahi[tam] "), "siyahı[tam] ")

    def test_mətn_və_şərhdə_çevrilmir(self):
        self.assertEqual(K.mətni_yaz('yaz("eger ") '), 'yaz("eger ") ')
        self.assertEqual(K.mətni_yaz("// eger ozu\n"), "// eger ozu\n")

    def test_üzv_və_söz_hissəsi_çevrilmir(self):
        self.assertEqual(K.mətni_yaz("siyahı.ve "), "siyahı.ve ")
        self.assertEqual(K.mətni_yaz("evet "), "evet ")
        self.assertEqual(K.mətni_yaz("egerx "), "egerx ")

    def test_söz_bitmədən_çevrilmir(self):
        self.assertIsNone(K.avtomatik_çevir("eger", 4))
        self.assertEqual(K.avtomatik_çevir("eger ", 5), ("əgər ", 5))
        self.assertEqual(K.avtomatik_çevir("x = deyisen(", 12),
                         ("x = dəyişən(", 12))

    def test_kompozisiya(self):
        self.assertEqual(K.mətni_yaz(";e;i;o;u;c;s;g"), "əıöüçşğ")
        self.assertEqual(K.mətni_yaz(";E;I;O;U;C;S;G"), "ƏİÖÜÇŞĞ")
        self.assertEqual(K.mətni_yaz('yaz("b;oy;uk")'), 'yaz("böyük")')

    def test_iki_nöqtəli_vergül(self):
        self.assertEqual(K.mətni_yaz("a = 1;;e"), "a = 1;e")
        self.assertEqual(K.mətni_yaz("a;; b"), "a; b")

    def test_söndürmək_olur(self):
        self.assertEqual(K.mətni_yaz("eger ;e", ascii=False, tərkib=False),
                         "eger ;e")

    def test_spesifikasiya_cədvəli(self):
        for a, k in (("eger", "əgər"), ("deyisen", "dəyişən"),
                     ("ozu", "özü"), ("ucun", "üçün"), ("istenilen",
                                                         "istənilən"),
                     ("genislet", "genişlət"), ("mentiq", "məntiq"),
                     ("luget", "lüğət"), ("tetbiq", "tətbiq")):
            self.assertEqual(K.ASCII_CƏDVƏLİ.get(a), k, a)
        self.assertEqual(K.KOMPOZİSİYA["I"], "İ")
        self.assertEqual(K.KOMPOZİSİYA["i"], "ı")

    def test_api_cədvəl(self):
        c = K.cədvəl()
        json.dumps(c, ensure_ascii=False)
        self.assertIn("ə", c["hərflər"])


# ═══════════════════════════════════════════════════════════════════════
#  6. İcra — proqram ayrıca prosesdə, çıxış SSE ilə
# ═══════════════════════════════════════════════════════════════════════

class İcra(ServerSınağı):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        shutil.copy(NÜMUNƏLƏR / "01-salam.alq",
                    cls.layihə / "01-salam.alq")
        (cls.layihə / "sonsuz.alq").write_text(
            'yaz("başladı")\nhəmişə\n    dəyişən a = 1\nson\n',
            encoding="utf-8")

    def axın(self, id_, gözlə=30.0):
        """SSE axınını sonuna qədər oxuyur: hadisələr siyahısı."""
        c = http.client.HTTPConnection("127.0.0.1", self.studio.port,
                                       timeout=gözlə)
        c.request("GET", f"/api/islet/axin?id={id_}&t={self.studio.nişan}",
                  headers={"Host": f"127.0.0.1:{self.studio.port}"})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertTrue(r.getheader("Content-Type").startswith(
            "text/event-stream"))
        hadisələr = []
        for sətir in r:
            sətir = sətir.decode("utf-8").rstrip("\n")
            if sətir.startswith("data: "):
                h = json.loads(sətir[6:])
                hadisələr.append(h)
                if h["növ"] == "bitdi":
                    break
        c.close()
        return hadisələr

    def test_salam_nümunəsi_axınla(self):
        kod, iş = self.api("/api/islet", {"yol": "01-salam.alq"})
        self.assertEqual(kod, 200, iş)
        for s in ("Aysel", "20"):
            kod, d = self.api("/api/islet/giris", {"id": iş["id"], "mətn": s})
            self.assertEqual((kod, d["ok"]), (200, True))
        hadisələr = self.axın(iş["id"])
        çıxış = "".join(h["mətn"] for h in hadisələr if h["növ"] == "çıxış")
        self.assertIn("Adınızı daxil edin:", çıxış)
        self.assertIn("Yaşınızı daxil edin:", çıxış)
        self.assertIn("Aysel, siz yetkinsiniz.", çıxış)
        self.assertEqual(hadisələr[-1]["növ"], "bitdi")
        self.assertEqual(hadisələr[-1]["kod"], 0)
        # Nömrələr ardıcıldır — yenidən qoşulanda heç nə itmir
        self.assertEqual([h["n"] for h in hadisələr],
                         list(range(len(hadisələr))))

    def test_yenidən_qoşulma_təkrarlamır(self):
        kod, iş = self.api("/api/islet", {"yol": "salam.alq"})
        hamısı = self.axın(iş["id"])
        c = http.client.HTTPConnection("127.0.0.1", self.studio.port,
                                       timeout=10)
        c.request("GET", f"/api/islet/axin?id={iş['id']}&t="
                         f"{self.studio.nişan}",
                  headers={"Host": f"127.0.0.1:{self.studio.port}",
                           "Last-Event-ID": str(hamısı[-2]["n"])})
        qalan = [json.loads(s[6:]) for s in
                 c.getresponse().read().decode("utf-8").split("\n")
                 if s.startswith("data: ")]
        c.close()
        self.assertEqual(qalan, [hamısı[-1]])

    def test_xəta_stderr_ilə_gəlir(self):
        (self.layihə / "pis.alq").write_text("yaz(1 / 0)\n",
                                               encoding="utf-8")
        kod, iş = self.api("/api/islet", {"yol": "pis.alq"})
        hadisələr = self.axın(iş["id"])
        xəta = "".join(h["mətn"] for h in hadisələr if h["növ"] == "xəta")
        self.assertIn("pis.alq:1:", xəta)
        self.assertNotEqual(hadisələr[-1]["kod"], 0)

    def test_dayandır(self):
        kod, iş = self.api("/api/islet", {"yol": "sonsuz.alq"})
        time.sleep(0.8)
        kod, _ = self.api("/api/islet/dayandir", {"id": iş["id"]})
        self.assertEqual(kod, 200)
        hadisələr = self.axın(iş["id"], 20)
        self.assertEqual(hadisələr[-1]["növ"], "bitdi")
        self.assertNotEqual(hadisələr[-1]["kod"], 0)
        self.assertIn("dayandırıldı", "".join(h["mətn"] for h in hadisələr))

    def test_layihədən_kənar_işlədilmir(self):
        kod, _ = self.api("/api/islet", {"yol": "../kənar.txt"})
        self.assertEqual(kod, 403)


# ═══════════════════════════════════════════════════════════════════════
#  7. Önbaxış, şablonlar, vidjet API
# ═══════════════════════════════════════════════════════════════════════

class ÖnbaxışVəŞablon(ServerSınağı):

    def test_şablonlar_təmizdir(self):
        for növ in ("konsol", "veb", "desktop"):
            f = sablonlar.fayllar(növ, "Sınaq")
            self.assertEqual(xətalar(f["əsas.alq"]), [], növ)

    def test_şablon_api(self):
        kod, d = self.api("/api/sablon", {"növ": "desktop", "ad": "tətbiqim"})
        self.assertEqual(kod, 200, d)
        self.assertEqual(d["fayl"], "tətbiqim/əsas.alq")
        self.assertTrue((self.layihə / "tətbiqim" / "layihe.alq").exists())
        kod, _ = self.api("/api/sablon", {"növ": "desktop", "ad": "tətbiqim"})
        self.assertEqual(kod, 409)
        kod, _ = self.api("/api/sablon", {"növ": "desktop", "ad": "../x"})
        self.assertIn(kod, (400, 403))

    def test_önbaxış(self):
        n = S.vidjet_əlavə_et("", "düymə")
        (self.layihə / "önbaxış.alq").write_text(n.mətn, encoding="utf-8")
        kod, d = self.api("/api/onbaxis", {"yol": "önbaxış.alq"})
        self.assertEqual(kod, 200)
        self.assertNotIn("xəta", d, d)
        self.assertEqual(d["komponent"], "Tətbiq")
        import urllib.request
        with urllib.request.urlopen(d["ünvan"], timeout=10) as c:
            html = c.read().decode("utf-8")
        self.assertIn("Yadda saxla", html)
        self.assertIn(".v-düymə", html)              # vidjet üslubu
        self.assertIn("data-a-klik", html)           # hadisə bağlıdır
        self.api("/api/onbaxis/dayandir", {})

    def test_önbaxış_komponentsiz(self):
        kod, d = self.api("/api/onbaxis", {"yol": "salam.alq"})
        self.assertEqual(kod, 200)
        self.assertIn("komponent", d["xəta"])

    def test_vidjet_api(self):
        kod, d = self.api("/api/vidjet/elave", {"mətn": "", "vidjet": "sahə",
                                                "kursor": 0})
        self.assertEqual(kod, 200)
        self.assertIn("vəziyyət sahə1", d["mətn"])
        kod, d = self.api("/api/vidjet/elave", {"mətn": "", "vidjet": "yox"})
        self.assertEqual(kod, 422)
        kod, d = self.api("/api/kataloq")
        self.assertEqual(len(d["vidjetlər"]), len(V.KATALOQ))
        # Kod nümunələrində köhnə `tamEn` tipi yoxdur (CSS sinfi ola bilər)
        self.assertNotIn("tamEn", json.dumps(
            [x["nümunə"] for x in d["vidjetlər"]], ensure_ascii=False))
        self.assertIn("v-düymə", d["vidjetlər"][0]["miniatür"])

    def test_pəncərə_pencere_aparıcısı_ilə_açılır(self):
        """`pencere._pəncərəni_aç` təkrar istifadə olunur (`--app=`)."""
        import alqor.pencere as P
        from studio.server import pəncərəni_aç
        doğru = shutil.which("true")
        if not doğru:
            self.skipTest("`true` əmri yoxdur")
        köhnə = P._brauzer_tap
        P._brauzer_tap = lambda: doğru
        try:
            aparıcı, şim = pəncərəni_aç(self.studio)
        finally:
            P._brauzer_tap = köhnə
        try:
            self.assertEqual(aparıcı, "brauzer-tətbiq")
            self.assertEqual(len(şim._prosslər), 1)
            əmr = şim._prosslər[0].args
            self.assertIn(f"--app={self.studio.ünvan()}", əmr)
        finally:
            şim._prosslər[0].wait(timeout=5)

    def test_cli_sınaq_rejimi(self):
        e = dict(os.environ, PYTHONIOENCODING="utf-8")
        n = subprocess.run(
            [sys.executable, str(KÖK / "alqorc.py"), "studio",
             str(self.layihə), "--sınaq"],
            capture_output=True, text=True, encoding="utf-8", env=e,
            timeout=60)
        self.assertEqual(n.returncode, 0, n.stdout + n.stderr)
        self.assertIn("✓ API nişanla işləyir", n.stdout)


# ═══════════════════════════════════════════════════════════════════════
#  8. Brauzer sınaqları (Playwright varsa)
# ═══════════════════════════════════════════════════════════════════════

def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    return sync_playwright


class Brauzer(unittest.TestCase):
    """Redaktor və palet həqiqi brauzerdə. Playwright yoxdursa atlanır."""

    @classmethod
    def setUpClass(cls):
        sp = _playwright()
        if sp is None:
            raise unittest.SkipTest("playwright quraşdırılmayıb")
        cls.qovluq = Path(tempfile.mkdtemp(prefix="studio-brauzer-"))
        (cls.qovluq / "boş.alq").write_text("", encoding="utf-8")
        (cls.qovluq / "panel.alq").write_text(
            "gətir vidjet\n\nkomponent Panel\n    göstər()\n"
            '        qaytar vidjet.düymə(mətn: "Saxla", növ: "əsas")\n'
            "    son\nson\n", encoding="utf-8")
        (cls.qovluq / "forma.alq").write_text(
            "komponent Forma\n    göstər()\n        qaytar <div>\n"
            '            {vidjet.sahə(etiket: "Ad", ad: "ad")}\n'
            "        </div>\n    son\nson\n", encoding="utf-8")
        (cls.qovluq / "dbq.alq").write_text(Debaq.KOD, encoding="utf-8")
        (cls.qovluq / "iki.alq").write_text(
            "gətir vidjet\n\nkomponent Birinci\n    göstər()\n"
            '        qaytar vidjet.başlıq("Bir")\n    son\nson\n\n'
            "komponent İkinci\n    göstər()\n"
            '        qaytar vidjet.başlıq("İki")\n    son\nson\n',
            encoding="utf-8")
        cls.studio = Studio(cls.qovluq).fonda_başlat()
        try:
            cls.pw = sp().start()
            cls.brauzer = cls.pw.chromium.launch()
        except Exception as x:                          # noqa: BLE001
            cls.studio.dayandır()
            raise unittest.SkipTest(f"brauzer işə düşmədi: {x}")

    @classmethod
    def tearDownClass(cls):
        cls.brauzer.close()
        cls.pw.stop()
        cls.studio.dayandır()
        shutil.rmtree(cls.qovluq, ignore_errors=True)

    def setUp(self):
        self.səhifə = self.brauzer.new_page(
            viewport={"width": 1400, "height": 860})
        self.xətalar = []
        self.səhifə.on("pageerror", lambda x: self.xətalar.append(str(x)))
        self.səhifə.goto(self.studio.ünvan())
        self.səhifə.wait_for_selector(".düyün")

    def tearDown(self):
        self.səhifə.close()
        self.assertEqual(self.xətalar, [])

    def gözlə(self, ta, parça, müddət=15.0):
        """Redaktorun mətnində `parça` görünənə qədər gözləyir.
        (`wait_for_function` CSP səbəbindən `eval` edə bilmir.)"""
        son = time.monotonic() + müddət
        while time.monotonic() < son:
            if parça in ta.input_value():
                return ta.input_value()
            self.səhifə.wait_for_timeout(100)
        self.fail(f"{parça!r} gözlənildi:\n{ta.input_value()}")

    def aç(self, yol):
        p = self.səhifə
        p.click('[data-panel="layihe"]')
        p.click(f'.düyün[data-yol="{yol}"]')
        p.wait_for_selector(f'.tab.aktiv[data-yol="{yol}"]')
        return p.locator(".r-giriş")

    def test_yazı_çevrilmə_və_girinti(self):
        ta = self.aç("boş.alq")
        ta.click()
        self.səhifə.keyboard.type(
            'deyisen x = 5\neger x > 3 onda\nyaz("b;oy;uk")\nson\n')
        self.assertEqual(ta.input_value(),
                         'dəyişən x = 5\nəgər x > 3 onda\n'
                         '    yaz("böyük")\nson\n')
        # Rəngləmə: `əgər` açar söz kimi
        self.assertTrue(self.səhifə.locator(".r-örtük .t-açar",
                                            has_text="əgər").count())
        self.səhifə.keyboard.press("Control+z")
        self.assertNotEqual(ta.input_value().count("\n"), 4)
        self.səhifə.keyboard.press("Control+y")
        self.assertTrue(ta.input_value().endswith("son\n"))

    def test_tamamlama_alqorls_ilə(self):
        ta = self.aç("boş.alq")
        ta.fill("")
        ta.click()
        k = self.səhifə.keyboard
        k.type("funksiya topla(a: tam, b: tam) -> tam\nqaytar a + b\nson\n")
        self.gözlə(ta, "son\n")
        k.type("yaz(top")
        siyahı = self.səhifə.locator(".r-tamamla")
        siyahı.wait_for(state="visible")
        self.assertIn("topla", siyahı.inner_text())
        k.press("Enter")
        self.gözlə(ta, "yaz(topla")
        # imza ipucu
        k.type("(")
        imza = self.səhifə.locator(".r-imza")
        imza.wait_for(state="visible")
        self.assertIn("a: tam", imza.inner_text())
        k.type("1, ")
        self.səhifə.wait_for_timeout(400)
        self.assertEqual(imza.locator("b").inner_text(), "b: tam")
        k.press("Escape")
        # modul üzvləri `.` ilə
        k.type("2))\ngətir riyaziyyat\nyaz(riyaziyyat.")
        siyahı.wait_for(state="visible")
        self.assertIn("kök", siyahı.inner_text())
        k.type("kö")
        k.press("Tab")
        self.gözlə(ta, "riyaziyyat.kök")
        self.assertTrue(siyahı.is_hidden())

    def test_debaq_interfeysi(self):
        p = self.səhifə
        self.aç("dbq.alq")
        # sətir nömrəsinə klik — dayanma nöqtəsi
        p.click('.r-nömrələr [data-s="3"]')
        self.assertIn("n-nöqtə",
                      p.get_attribute('.r-nömrələr [data-s="3"]', "class"))
        p.click("#dym-debaq")
        vəz = p.locator("#dbq-veziyyet")
        son = time.monotonic() + 20
        while "Dayandı" not in vəz.inner_text() and time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertIn("dayanma nöqtəsi", vəz.inner_text())
        self.assertEqual(p.locator("#dbq-yigin .kadr").count(), 2)
        self.assertIn("kvadrat", p.inner_text("#dbq-yigin .kadr.seçili"))
        self.assertIn("n-icra",
                      p.get_attribute('.r-nömrələr [data-s="3"]', "class"))
        self.assertIn("k = 1", p.inner_text("#dbq-deyisenler"))
        # ifadə
        p.fill("#dbq-ifade", "n + 41")
        p.press("#dbq-ifade", "Enter")
        son = time.monotonic() + 10
        while "42" not in p.inner_text("#dbq-netice") and \
                time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertIn("n + 41 = 42", p.inner_text("#dbq-netice"))
        # çağıranın kadrı
        p.click('#dbq-yigin .kadr[data-i="1"]')
        son = time.monotonic() + 10
        while "cəm = 0" not in p.inner_text("#dbq-deyisenler") and \
                time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertIn("cəm = 0", p.inner_text("#dbq-deyisenler"))
        # nöqtəni götür, davam (F5) → bitir
        p.click('.r-nömrələr [data-s="3"]')
        p.click("#dbq-davam")
        son = time.monotonic() + 20
        while "bitdi" not in vəz.inner_text() and time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertEqual(vəz.inner_text(), "Debaq bitdi.")
        self.assertIn("cəm: 14", p.inner_text("#cixis"))
        self.assertFalse(p.locator("#dym-debaq").is_disabled())

    def test_vizual_dizayner(self):
        (self.qovluq / "dizayn.alq").write_text(Dizayner.KOD,
                                                encoding="utf-8")
        p = self.səhifə
        p.reload()
        p.wait_for_selector(".düyün")
        ta = self.aç("dizayn.alq")
        p.click("#dym-dizayn")
        p.wait_for_selector('#dizayn .dz-element[data-yol="[0]"]')
        self.assertEqual(p.locator("#dizayn .dz-konteyner").count(), 2)
        self.assertIn("Qeydiyyat", p.inner_text('[data-yol="[0]"]'))
        # 1. Elementi daşı: başlıq → sətir konteynerinin sonuna
        p.locator('#dizayn [data-yol="[0]"]').drag_to(
            p.locator('#dizayn .dz-yer[data-hedef="[2]"][data-indeks="2"]'))
        m = self.gözlə(ta, '"Göndər", növ: "əsas"),')
        self.assertLess(m.index('"Göndər"'), m.index('"Qeydiyyat"'))
        # 2. Paletdən əlavə: nişan → kökün əvvəlinə
        p.click('[data-panel="palet"]')
        p.locator('#palet [data-vidjet="nişan"]').drag_to(
            p.locator('#dizayn .dz-yer[data-hedef="[]"][data-indeks="0"]'))
        m = self.gözlə(ta, "vidjet.nişan(")
        self.assertLess(m.index("vidjet.nişan("), m.index("vidjet.sahə("))
        # 3. Sil: seç + ✕
        el = p.locator('#dizayn [data-yol="[0]"]')
        son = time.monotonic() + 10
        while "Badge" not in el.inner_text() and time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertIn("Badge", el.inner_text())
        el.hover()
        el.locator(".dz-sil").click()
        son = time.monotonic() + 10
        while "vidjet.nişan(" in ta.input_value() and \
                time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertNotIn("vidjet.nişan(", ta.input_value())
        # 4. Klik — redaktor elementin sətrinə keçir, xüsusiyyətlər açılır
        el = p.locator('#dizayn [data-yol="[0]"]')
        son = time.monotonic() + 10
        while "Text Field" not in el.inner_text() and time.monotonic() < son:
            p.wait_for_timeout(100)
        el.click()
        p.wait_for_selector("#xus-forma:not([hidden]) .xüs-başlıq")
        # Xüsusiyyətlər paneli asinxron yenilənir — əvvəlki seçim bir an
        # görünə bilər
        self.gözləŞərt(lambda: "vidjet.sahə" in p.inner_text(".xüs-başlıq"),
                       "xüsusiyyətlər sahəni göstərmədi: " +
                       p.inner_text(".xüs-başlıq"))
        # Fayl saxlanılıb
        self.assertIn("vidjet.sətir", (self.qovluq / "dizayn.alq").read_text(
            encoding="utf-8"))

    def test_fayl_parametri_ilə_açılır(self):
        p = self.səhifə
        p.goto(self.studio.ünvan() + "&fayl=forma.alq")
        p.wait_for_selector('.tab.aktiv[data-yol="forma.alq"]')
        self.assertIn("komponent Forma",
                      p.locator(".r-giriş").input_value())

    def test_palet_iki_klik(self):
        ta = self.aç("boş.alq")
        ta.fill("")
        self.səhifə.click('[data-panel="palet"]')
        self.səhifə.dblclick('[data-vidjet="tərəqqi"]')
        m = self.gözlə(ta, "tərəqqi1")
        self.assertIn("vəziyyət tərəqqi1: tam = 0", m)
        self.assertIn("gətir vidjet", m)

    def test_redaktorda_iki_klik_tamamlayır(self):
        ta = self.aç("forma.alq")
        # Örtükdəki `sahə` sözünün yerinə (üstündəki textarea-ya) iki klik
        yer = self.səhifə.locator(".r-örtük .t-çağırış", has_text="sahə")
        q = yer.first.bounding_box()
        self.səhifə.mouse.dblclick(q["x"] + q["width"] / 2,
                                   q["y"] + q["height"] / 2)
        m = self.gözlə(ta, "adDəyişdi")
        self.assertIn('vəziyyət ad: mətn = ""', m)
        self.assertIn("dəyişdi: özü.adDəyişdi", m)
        self.assertTrue(m.startswith("gətir vidjet\n"))

    def test_fayldakı_elementlər_iki_klik(self):
        ta = self.aç("forma.alq")
        self.səhifə.click('[data-panel="palet"]')
        el = self.səhifə.locator(".fayl-elementi.yarımçıq",
                                 has_text="sahə")
        el.wait_for()
        el.dblclick()
        self.gözlə(ta, "metod adDəyişdi")
        self.səhifə.wait_for_selector(".fayl-elementi.tam")

    def test_palet_miniatürləri(self):
        self.aç("boş.alq")
        self.səhifə.click('[data-panel="palet"]')
        p = self.səhifə
        from alqor import vidjet as V
        self.assertEqual(p.locator(".vidjet-elementi .miniatür").count(),
                         len(V.KATALOQ))
        # Shadow DOM içində vidjetin həqiqi HTML-i (Playwright açıq
        # shadow kökə daxil olur)
        düymə = p.locator('[data-vidjet="düymə"] .miniatür button.v-düymə')
        self.assertEqual(düymə.inner_text(), "Yadda saxla")
        self.assertTrue(p.locator(
            '[data-vidjet="cədvəl"] .miniatür table.v-cədvəl').count())
        # Beynəlxalq adlar: kartın başlığı, kod adı altda; axtarış hər ikisi
        self.assertEqual(p.inner_text('[data-vidjet="tərəqqi"] b'),
                         "Progress Bar")
        self.assertIn("vidjet.tərəqqi",
                      p.inner_text('[data-vidjet="tərəqqi"] small'))
        p.fill("#palet-axtar", "breadcrumb")
        görünən = p.locator(".vidjet-elementi:not([hidden])")
        self.assertEqual(görünən.count(), 1)
        self.assertEqual(görünən.get_attribute("data-vidjet"),
                         "çörəkQırıntıları")
        p.fill("#palet-axtar", "cədvəl")
        self.assertEqual(p.locator(".vidjet-elementi:not([hidden])")
                         .first.get_attribute("data-vidjet"), "cədvəl")

    def test_xüsusiyyətlər_paneli_və_canlı_önbaxış(self):
        ta = self.aç("panel.alq")
        p = self.səhifə
        p.click('[data-panel="palet"]')
        p.locator(".fayl-elementi", has_text="düymə").click()
        p.wait_for_selector("#xus-forma:not([hidden]) .xüs-başlıq")
        self.assertEqual(p.inner_text(".xüs-başlıq b"), "Button")
        self.assertIn("vidjet.düymə", p.inner_text(".xüs-başlıq"))
        self.assertEqual(p.input_value('[data-xus="mətn"]'), "Saxla")
        # Mətn
        p.fill('[data-xus="mətn"]', "Göndər")
        self.gözlə(ta, 'mətn: "Göndər"')
        # Seçim
        p.select_option('[data-xus="ölçü"]', "böyük")
        self.gözlə(ta, 'ölçü: "böyük"')
        # Üslub: fon rəngi və künc
        p.fill('[data-xus="üslub.fon"]', "#16a34a")
        p.fill('[data-xus="üslub.künc"]', "14")
        m = self.gözlə(ta, '"künc": 14')
        self.assertIn('üslub: {"fon": "#16a34a", "künc": 14}', m)
        # Fayl səssiz saxlanılıb, önbaxış açılıb və yenilənib
        son = time.monotonic() + 15
        while time.monotonic() < son:
            if '"künc": 14' in (self.qovluq / "panel.alq").read_text(
                    encoding="utf-8"):
                break
            p.wait_for_timeout(100)
        çərçivə = p.frame_locator("#onbaxis-cercive")
        d = çərçivə.locator("button.v-düymə")
        d.wait_for(timeout=20000)
        son = time.monotonic() + 20
        while time.monotonic() < son:
            if "border-radius:14px" in (d.get_attribute("style") or ""):
                break
            p.wait_for_timeout(150)
        self.assertIn("background:#16a34a", d.get_attribute("style"))
        self.assertEqual(d.inner_text(), "Göndər")
        # Önbaxış Studio-nun temasını izləyir (sistem temasını yox)
        tema = p.locator("html").get_attribute("data-tema")
        self.assertEqual(çərçivə.locator("html").get_attribute("data-tema"),
                         tema)
        p.click("#dym-tema")
        yeni = p.locator("html").get_attribute("data-tema")
        self.assertNotEqual(yeni, tema)
        son = time.monotonic() + 15
        while time.monotonic() < son:
            try:
                if çərçivə.locator("html").get_attribute(
                        "data-tema", timeout=1000) == yeni:
                    break
            except Exception:                           # noqa: BLE001
                pass
            p.wait_for_timeout(150)
        self.assertEqual(çərçivə.locator("html").get_attribute("data-tema"),
                         yeni)
        # Standarta qaytarmaq (✕) arqumenti silir
        p.click('[data-sətir="ölçü"] .sıfırla')
        son = time.monotonic() + 10
        while "ölçü:" in ta.input_value() and time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertNotIn("ölçü:", ta.input_value())

    # ── IDE qabığı: menyu sətri, kontekst menyular, palitra, dok ─────

    def gözləŞərt(self, f, mesaj, müddət=10.0):
        son = time.monotonic() + müddət
        while time.monotonic() < son:
            if f():
                return
            self.səhifə.wait_for_timeout(100)
        self.fail(mesaj)

    def test_menyu_sətri(self):
        p = self.səhifə
        başlıqlar = p.locator("#menyu-setri .m-başlıq").all_inner_texts()
        for ad in ("Fayl", "Redaktə", "Seçim", "Görünüş", "Keç", "İşlət",
                   "Debaq", "Alətlər", "Kömək"):
            self.assertIn(ad, başlıqlar)
        p.click('#menyu-setri .m-başlıq:has-text("Fayl")')
        menyu = p.locator(".menyu-qutu").first
        menyu.wait_for(state="visible")
        self.assertIn("Yeni fayl", menyu.inner_text())
        self.assertTrue(menyu.locator(".m-element svg").count())  # ikonlar
        # açıq menyuda üzərinə gəlmək qonşu menyunu açır
        p.hover('#menyu-setri .m-başlıq:has-text("Görünüş")')
        self.assertIn("Əmr palitrası", p.locator(".menyu-qutu").first
                      .inner_text())
        # alt menyu
        p.hover('.menyu-qutu .m-element:has-text("Panellər")')
        p.locator(".menyu-qutu").nth(1).wait_for(state="visible")
        self.assertIn("Struktur", p.locator(".menyu-qutu").nth(1)
                      .inner_text())
        p.keyboard.press("Escape")
        p.keyboard.press("Escape")
        self.gözləŞərt(lambda: p.locator(".menyu-qutu").count() == 0,
                       "menyu bağlanmadı")
        # Alt+hərf
        p.keyboard.press("Alt+k")
        p.locator(".menyu-qutu").first.wait_for(state="visible")
        self.assertIn("Sətrə keç", p.locator(".menyu-qutu").first
                      .inner_text())
        p.keyboard.press("Escape")

    def test_redaktor_kontekst_menyusu(self):
        p = self.səhifə
        ta = self.aç("panel.alq")
        ta.click(button="right")
        m = p.locator(".menyu-qutu").first
        m.wait_for(state="visible")
        mətn = m.inner_text()
        for ad in ("Təyinata keç", "Bütün istinadlar", "Kəs", "Kopyala",
                   "Hamısını seç", "Sənədi formatla"):
            self.assertIn(ad, mətn)
        m.locator('.m-element:has-text("Hamısını seç")').click()
        self.assertEqual(p.locator(".menyu-qutu").count(), 0)
        uz = len(ta.input_value())
        self.assertEqual(ta.evaluate("t => t.selectionEnd - t.selectionStart"),
                         uz)

    def test_ağac_və_tab_kontekst_menyusu(self):
        p = self.səhifə
        self.aç("forma.alq")
        p.click('.düyün[data-yol="panel.alq"]', button="right")
        m = p.locator(".menyu-qutu").first
        self.assertIn("Adını dəyiş", m.inner_text())
        m.locator('.m-element:has-text("Aç")').first.click()
        p.wait_for_selector('.tab.aktiv[data-yol="panel.alq"]')
        p.click('.tab[data-yol="panel.alq"]', button="right")
        p.locator('.menyu-qutu .m-element:has-text("Digərlərini bağla")'
                  ).click()
        self.gözləŞərt(lambda: p.locator(".tab").count() == 1,
                       "digər tablar bağlanmadı")

    def test_əmr_palitrası(self):
        p = self.səhifə
        ta = self.aç("panel.alq")
        ta.click()
        p.keyboard.press("Control+Shift+P")
        g = p.locator(".palitra-giriş")
        g.wait_for(state="visible")
        self.assertEqual(g.input_value(), ">")
        g.type("struktur")
        self.assertIn("Struktur", p.inner_text(".palitra-siyahı"))
        # fayl rejimi
        g.fill("form")
        p.wait_for_selector('.palitra-element:has-text("forma.alq")')
        p.keyboard.press("Enter")
        p.wait_for_selector('.tab.aktiv[data-yol="forma.alq"]')
        # sətrə keç
        p.keyboard.press("Control+Shift+P")
        g.fill(":3")
        p.keyboard.press("Enter")
        self.gözləŞərt(lambda: p.locator(".palitra").is_hidden(),
                       "palitra bağlanmadı")
        mövqe = ta.evaluate("t => t.value.slice(0, t.selectionStart)")
        self.assertEqual(mövqe.count("\n"), 2)

    def test_panel_köçürmə_üzən_və_saxlanma(self):
        p = self.səhifə
        sağ = '.dok[data-dok="sağ"] .dok-nişan[data-panel="cixis"]'
        p.click('.dok-nişan[data-panel="cixis"]', button="right")
        p.locator('.menyu-qutu .m-element:has-text("Sağa yerləşdir")'
                  ).click()
        p.wait_for_selector(sağ)
        self.assertTrue(p.locator("#alt-cixis").is_visible())
        # üzən pəncərə
        p.click(sağ, button="right")
        p.locator('.menyu-qutu .m-element:has-text("Üzən pəncərə et")'
                  ).click()
        p.wait_for_selector("#uzenler .üzən #alt-cixis")
        w = p.locator("#uzenler .üzən").first
        b0 = w.bounding_box()
        h = p.locator("#uzenler .üzən-başlıq").first.bounding_box()
        p.mouse.move(h["x"] + 40, h["y"] + h["height"] / 2)
        p.mouse.down()
        p.mouse.move(h["x"] + 140, h["y"] + 80, steps=5)
        p.mouse.up()
        b1 = w.bounding_box()
        self.assertGreater(b1["x"], b0["x"] + 50)
        # düzülüş yenidən yükləmədə saxlanır
        p.reload()
        p.wait_for_selector("#uzenler .üzən #alt-cixis")
        # yenidən yerləşdir → alt zonaya qayıdır
        p.click('#uzenler .üzən-başlıq', button="right")
        p.locator('.menyu-qutu .m-element:has-text("Aşağıya yerləşdir")'
                  ).click()
        p.wait_for_selector(
            '.dok[data-dok="alt"] .dok-nişan[data-panel="cixis"]')
        self.assertEqual(p.locator("#uzenler .üzən").count(), 0)

    def test_fəaliyyət_zolağı(self):
        p = self.səhifə
        p.click('[data-fealiyyet="axtar"]')
        self.assertTrue(p.locator("#panel-axtar").is_visible())
        self.assertFalse(p.locator("#panel-layihe").is_visible())
        # aktiv panelə yenidən klik — yan zonanı gizlədir
        p.click('[data-fealiyyet="axtar"]')
        self.gözləŞərt(lambda: not p.locator("#panel-axtar").is_visible(),
                       "yan zona gizlənmədi")
        p.click('[data-fealiyyet="layihe"]')
        self.assertTrue(p.locator("#panel-layihe").is_visible())

    def test_layihədə_axtarış_paneli(self):
        p = self.səhifə
        self.aç("boş.alq")
        p.keyboard.press("Control+Shift+F")
        g = p.locator("#lay-axtar")
        g.wait_for(state="visible")
        g.type("Saxla")
        p.wait_for_selector(".ax-sətir")
        self.assertIn("1 nəticə", p.inner_text("#lay-axtar-say"))
        p.click(".ax-sətir")
        p.wait_for_selector('.tab.aktiv[data-yol="panel.alq"]')
        ta = p.locator(".r-giriş")
        self.assertEqual(ta.evaluate(
            "t => t.value.slice(t.selectionStart, t.selectionEnd)"), "Saxla")

    def test_struktur_paneli(self):
        p = self.səhifə
        ta = self.aç("panel.alq")
        p.click('[data-fealiyyet="struktur"]')
        p.wait_for_selector('.st-düyün:has-text("Panel")', timeout=10000)
        p.fill("#struktur-suzgec", "göstər")
        p.wait_for_selector('.st-düyün:has-text("göstər")')
        p.click('.st-düyün:has-text("göstər")')
        mövqe = ta.evaluate("t => t.value.slice(0, t.selectionStart)")
        self.assertEqual(mövqe.count("\n"), 3)

    def test_önbaxış_komponent_seçimi(self):
        p = self.səhifə
        s = p.locator("#onbaxis-komponent")
        self.aç("boş.alq")
        p.keyboard.press("F6")
        p.wait_for_selector("#onbaxis-panel", state="visible")
        self.assertTrue(s.is_hidden())                 # komponentsiz fayl
        self.aç("panel.alq")
        self.gözləŞərt(lambda: p.locator("#onbaxis-cercive").get_attribute(
            "src") not in (None, "", "about:blank"), "önbaxış yüklənmədi",
            20)
        self.assertTrue(s.is_hidden())                 # tək komponent
        self.aç("iki.alq")
        self.gözləŞərt(lambda: s.is_visible(), "seçim görünmədi", 20)
        self.assertEqual(s.locator("option").all_inner_texts(),
                         ["Birinci", "İkinci"])
        əvvəl = p.locator("#onbaxis-cercive").get_attribute("src")
        s.select_option("İkinci")
        self.gözləŞərt(lambda: p.locator("#onbaxis-cercive").get_attribute(
            "src") != əvvəl, "önbaxış yenilənmədi", 20)
        self.assertEqual(s.input_value(), "İkinci")
        self.aç("boş.alq")
        self.gözləŞərt(lambda: s.is_hidden(), "boş seçim qaldı")

    def test_diaqnostika_dalğalı_xətt(self):
        ta = self.aç("boş.alq")
        ta.fill('dəyişən a: tam = "x"\n')
        self.səhifə.wait_for_selector(".r-örtük .d-xəta", timeout=10000)
        self.səhifə.wait_for_selector("#problemler li.xəta",
                                      state="attached")
        self.assertIn("ALQ-T001", self.səhifə.inner_text("#problemler"))


if __name__ == "__main__":
    unittest.main()
