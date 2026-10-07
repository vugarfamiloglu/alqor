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
        (cls.layihə / "salam.alqor").write_text('yaz("salam")\n',
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
        kod, _, _ = self.sorğu("POST", "/api/fayl/oxu", {"yol": "salam.alqor"},
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
        kod, _, _ = self.sorğu("POST", "/api/fayl/oxu", {"yol": "salam.alqor"},
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
    "salam.alqor\x00.txt",
]


class FaylAPI(ServerSınağı):

    def test_oxu(self):
        kod, d = self.api("/api/fayl/oxu", {"yol": "salam.alqor"})
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
                    ("/api/fayl/adlandir", {"yol": "salam.alqor",
                                            "yeni": yol})):
                kod, _ = self.api(api, gövdə)
                self.assertIn(kod, (400, 403), f"{api} {yol!r}")
        self.assertEqual((self.qovluq / "kənar.txt").read_text("utf-8"),
                         "KƏNAR")
        self.assertTrue((self.qonşu / "sirr.txt").exists())
        self.assertTrue((self.layihə / "salam.alqor").exists())

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
                          {"yol": "qovluq/yeni.alqor", "növ": "fayl"})
        self.assertEqual(kod, 200)
        self.assertEqual(d["yol"], "qovluq/yeni.alqor")
        kod, _ = self.api("/api/fayl/yaz", {"yol": "qovluq/yeni.alqor",
                                            "mətn": "yaz(\"ə\")\n"})
        self.assertEqual(kod, 200)
        self.assertEqual((self.layihə / "qovluq/yeni.alqor").read_bytes(),
                         'yaz("ə")\n'.encode("utf-8"))
        kod, _ = self.api("/api/fayl/yarat", {"yol": "qovluq/yeni.alqor"})
        self.assertEqual(kod, 409)
        kod, d = self.api("/api/fayl/adlandir", {"yol": "qovluq/yeni.alqor",
                                                 "yeni": "qovluq/köhnə.alqor"})
        self.assertEqual((kod, d["yol"]), (200, "qovluq/köhnə.alqor"))
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
        self.assertEqual(L.yol("a/./b.alqor"), self.layihə / "a" / "b.alqor")


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
            "ad": "a.alqor"})
        self.assertEqual(kod, 200)
        x = [p for p in d["diaqnostikalar"] if p["səviyyə"] == "xəta"]
        self.assertTrue(x)
        self.assertEqual(x[0]["sətir"], 2)

    def test_nümunələr_təmizdir(self):
        for f in sorted(NÜMUNƏLƏR.glob("*.alqor")):
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
        """57 vidjetin hər biri iki dəfə əlavə olunur — xəta, T002 yox."""
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
        shutil.copy(NÜMUNƏLƏR / "01-salam.alqor",
                    cls.layihə / "01-salam.alqor")
        (cls.layihə / "sonsuz.alqor").write_text(
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
        kod, iş = self.api("/api/islet", {"yol": "01-salam.alqor"})
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
        kod, iş = self.api("/api/islet", {"yol": "salam.alqor"})
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
        (self.layihə / "pis.alqor").write_text("yaz(1 / 0)\n",
                                               encoding="utf-8")
        kod, iş = self.api("/api/islet", {"yol": "pis.alqor"})
        hadisələr = self.axın(iş["id"])
        xəta = "".join(h["mətn"] for h in hadisələr if h["növ"] == "xəta")
        self.assertIn("pis.alqor:1:", xəta)
        self.assertNotEqual(hadisələr[-1]["kod"], 0)

    def test_dayandır(self):
        kod, iş = self.api("/api/islet", {"yol": "sonsuz.alqor"})
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
            self.assertEqual(xətalar(f["əsas.alqor"]), [], növ)

    def test_şablon_api(self):
        kod, d = self.api("/api/sablon", {"növ": "desktop", "ad": "tətbiqim"})
        self.assertEqual(kod, 200, d)
        self.assertEqual(d["fayl"], "tətbiqim/əsas.alqor")
        self.assertTrue((self.layihə / "tətbiqim" / "layihe.alqor").exists())
        kod, _ = self.api("/api/sablon", {"növ": "desktop", "ad": "tətbiqim"})
        self.assertEqual(kod, 409)
        kod, _ = self.api("/api/sablon", {"növ": "desktop", "ad": "../x"})
        self.assertIn(kod, (400, 403))

    def test_önbaxış(self):
        n = S.vidjet_əlavə_et("", "düymə")
        (self.layihə / "önbaxış.alqor").write_text(n.mətn, encoding="utf-8")
        kod, d = self.api("/api/onbaxis", {"yol": "önbaxış.alqor"})
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
        kod, d = self.api("/api/onbaxis", {"yol": "salam.alqor"})
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
        (cls.qovluq / "boş.alqor").write_text("", encoding="utf-8")
        (cls.qovluq / "panel.alqor").write_text(
            "gətir vidjet\n\nkomponent Panel\n    göstər()\n"
            '        qaytar vidjet.düymə(mətn: "Saxla", növ: "əsas")\n'
            "    son\nson\n", encoding="utf-8")
        (cls.qovluq / "forma.alqor").write_text(
            "komponent Forma\n    göstər()\n        qaytar <div>\n"
            '            {vidjet.sahə(etiket: "Ad", ad: "ad")}\n'
            "        </div>\n    son\nson\n", encoding="utf-8")
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
        ta = self.aç("boş.alqor")
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

    def test_palet_iki_klik(self):
        ta = self.aç("boş.alqor")
        ta.fill("")
        self.səhifə.click('[data-panel="palet"]')
        self.səhifə.dblclick('[data-vidjet="tərəqqi"]')
        m = self.gözlə(ta, "tərəqqi1")
        self.assertIn("vəziyyət tərəqqi1: tam = 0", m)
        self.assertIn("gətir vidjet", m)

    def test_redaktorda_iki_klik_tamamlayır(self):
        ta = self.aç("forma.alqor")
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
        ta = self.aç("forma.alqor")
        self.səhifə.click('[data-panel="palet"]')
        el = self.səhifə.locator(".fayl-elementi.yarımçıq",
                                 has_text="sahə")
        el.wait_for()
        el.dblclick()
        self.gözlə(ta, "metod adDəyişdi")
        self.səhifə.wait_for_selector(".fayl-elementi.tam")

    def test_palet_miniatürləri(self):
        self.aç("boş.alqor")
        self.səhifə.click('[data-panel="palet"]')
        p = self.səhifə
        self.assertEqual(p.locator(".vidjet-elementi .miniatür").count(), 57)
        # Shadow DOM içində vidjetin həqiqi HTML-i (Playwright açıq
        # shadow kökə daxil olur)
        düymə = p.locator('[data-vidjet="düymə"] .miniatür button.v-düymə')
        self.assertEqual(düymə.inner_text(), "Yadda saxla")
        self.assertTrue(p.locator(
            '[data-vidjet="cədvəl"] .miniatür table.v-cədvəl').count())

    def test_xüsusiyyətlər_paneli_və_canlı_önbaxış(self):
        ta = self.aç("panel.alqor")
        p = self.səhifə
        p.click('[data-panel="palet"]')
        p.locator(".fayl-elementi", has_text="düymə").click()
        p.wait_for_selector("#xus-forma:not([hidden]) .xüs-başlıq")
        self.assertEqual(p.inner_text(".xüs-başlıq b"), "düymə")
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
            if '"künc": 14' in (self.qovluq / "panel.alqor").read_text(
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
        # Standarta qaytarmaq (✕) arqumenti silir
        p.click('[data-sətir="ölçü"] .sıfırla')
        son = time.monotonic() + 10
        while "ölçü:" in ta.input_value() and time.monotonic() < son:
            p.wait_for_timeout(100)
        self.assertNotIn("ölçü:", ta.input_value())

    def test_diaqnostika_dalğalı_xətt(self):
        ta = self.aç("boş.alqor")
        ta.fill('dəyişən a: tam = "x"\n')
        self.səhifə.wait_for_selector(".r-örtük .d-xəta", timeout=10000)
        self.səhifə.wait_for_selector("#problemler li.xəta",
                                      state="attached")
        self.assertIn("ALQ-T001", self.səhifə.inner_text("#problemler"))


if __name__ == "__main__":
    unittest.main()
