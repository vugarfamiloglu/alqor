"""Studio forma dizayneri: saf əməliyyatlar, kətan HTML-i, `.alq` metodları,
server API-si (`/api/forma/*`)."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import forma as F                              # noqa: E402
from alqor import sxem as SX                              # noqa: E402
from alqor.forma import İstinad                           # noqa: E402
from alqor.xeta import XətaToplayıcı                      # noqa: E402
from studio import forma_dizayner as D                    # noqa: E402

FORMA = """\
forma Əsas
    başlıq = "Sınaq"
    en = 640
    hündürlük = 480

    obyekt Başlıq1: başlıq
        mətn = "Salam"
    son
    obyekt Panel1: sütun
        obyekt Ad: sahə
            etiket = "Ad"
        son
        obyekt Saxla: düymə
            mətn = "Saxla"
            klik = Saxla_klik
        son
    son
    obyekt Kətan1: kətan
        en = 300
        hündürlük = 200
        obyekt A: düymə
            mətn = "A"
            sol = 8
            yuxarı = 8
        son
    son
son
"""

SXEM = """\
sxem Məktəb
    cədvəl tələbələr
        id: tam açar
        ad: mətn məcburi
        sinif: tam = 1
    son
son
"""


def oxu(m=FORMA):
    f, d = D.oxu(m)
    assert f is not None, d
    return f


def yenidən(f):
    """Yazılan mətn yenidən oxunur — fayl həmişə etibarlı qalmalıdır."""
    x = XətaToplayıcı()
    g = F.mətndən(F.yaz(f), "A.forma", x)
    assert g is not None, x.hesabat(False)
    return g


def adlar(s):
    return [o.ad for o in s]


class Əməliyyatlar(unittest.TestCase):
    def test_əlavə_unikal_ad_və_standart_xassə(self):
        f = oxu()
        self.assertEqual(D.əlavə_et(f, "düymə"), "Düymə1")
        self.assertEqual(D.əlavə_et(f, "düymə"), "Düymə2")
        self.assertEqual(f.tap("Düymə2").xassələr, {"mətn": "Düymə2"})
        self.assertEqual(D.əlavə_et(f, "sahə", "Panel1", 0), "Sahə1")
        self.assertEqual(adlar(f.tap("Panel1").uşaqlar), ["Sahə1", "Ad", "Saxla"])
        self.assertEqual(D.əlavə_et(f, "VerilənlərBazası", "Panel1", 0), "Baza1")
        self.assertEqual(f.obyektlər[-1].ad, "Baza1")         # həmişə kökdə
        yenidən(f)

    def test_əlavə_qadağalar(self):
        f = oxu()
        with self.assertRaises(D.FormaDizaynXətası):
            D.əlavə_et(f, "yoxdur")
        with self.assertRaises(D.FormaDizaynXətası):
            D.əlavə_et(f, "düymə", "Saxla")            # konteyner deyil
        with self.assertRaises(D.FormaDizaynXətası):
            D.əlavə_et(f, "düymə", ad="Saxla")         # ad tutulub

    def test_konteyner(self):
        self.assertTrue(D.konteynerdir("sütun"))
        self.assertTrue(D.konteynerdir("kətan"))
        self.assertFalse(D.konteynerdir("mətn"))       # məzmun mətndir
        self.assertFalse(D.konteynerdir("düymə"))

    def test_sil(self):
        f = oxu()
        D.sil(f, ["Ad", "Panel1"])
        self.assertIsNone(f.tap("Saxla"))
        self.assertEqual(adlar(f.obyektlər), ["Başlıq1", "Kətan1"])

    def test_köçür(self):
        f = oxu()
        D.köçür(f, ["Saxla"], None, 0)
        self.assertEqual(adlar(f.obyektlər), ["Saxla", "Başlıq1", "Panel1",
                                              "Kətan1"])
        # Eyni siyahıda: indeks daşımadan əvvəlki siyahıya görədir
        D.köçür(f, ["Saxla"], None, 2)
        self.assertEqual(adlar(f.obyektlər), ["Başlıq1", "Saxla", "Panel1",
                                              "Kətan1"])
        D.köçür(f, ["Başlıq1", "Saxla"], "Panel1", None)
        self.assertEqual(adlar(f.tap("Panel1").uşaqlar),
                         ["Ad", "Başlıq1", "Saxla"])
        with self.assertRaises(D.FormaDizaynXətası):
            D.köçür(f, ["Panel1"], "Panel1")
        yenidən(f)

    def test_ad_dəyiş_istinadları_yeniləyir(self):
        f = oxu()
        D.əlavə_et(f, "VerilənlərBazası")
        D.əlavə_et(f, "Sorğu", xassələr={"baza": İstinad("Baza1")})
        D.ad_dəyiş(f, "Baza1", "Məktəb")
        self.assertEqual(f.tap("Sorğu1").xassələr["baza"], İstinad("Məktəb"))
        D.ad_dəyiş(f, "Saxla", "Yadda")
        # Hadisə metodu adı obyektin adı ilə dəyişmir
        self.assertEqual(f.tap("Yadda").xassələr["klik"],
                         İstinad("Saxla_klik"))
        for pis in ("1x", "Ad", "əgər", ""):
            with self.assertRaises(D.FormaDizaynXətası):
                D.ad_dəyiş(f, "Yadda", pis)

    def test_xassə_qoy_və_sil(self):
        f = oxu()
        D.xassə_qoy(f, "Saxla", "növ", "ikinci")
        D.xassə_qoy(f, None, "düzülüş", "sərbəst")
        self.assertEqual(f.xassələr["düzülüş"], "sərbəst")
        D.xassə_qoy(f, "Saxla", "mətn", None)
        self.assertNotIn("mətn", f.tap("Saxla").xassələr)
        self.assertEqual(yenidən(f).tap("Saxla").xassələr["növ"], "ikinci")

    def test_json_dəyərləri(self):
        self.assertEqual(D.dəyər_json(İstinad("A")), {"$ad": "A"})
        self.assertEqual(D.dəyər_json([1, "a"]), {"$ifadə": '[1, "a"]'})
        self.assertEqual(D.json_dəyər({"$ifadə": '{"fon": "#fff"}'}),
                         {"fon": "#fff"})
        self.assertEqual(D.json_dəyər({"$ad": "Baza1"}), İstinad("Baza1"))
        with self.assertRaises(D.FormaDizaynXətası):
            D.json_dəyər({"$ifadə": "[1, "})
        f = oxu()
        m = D.model(f)
        self.assertEqual(m["obyektlər"][1]["uşaqlar"][1]["xassələr"]["klik"],
                         {"$ad": "Saxla_klik"})
        self.assertTrue(m["obyektlər"][1]["konteyner"])
        json.dumps(m, ensure_ascii=False)

    def test_təkrarla_və_yapışdır(self):
        f = oxu()
        yeni = D.təkrarla(f, ["Saxla", "A"])
        self.assertEqual(yeni, ["Saxla1", "A1"])
        k = f.tap("Saxla1")
        self.assertNotIn("klik", k.xassələr)              # hadisə surətə keçmir
        self.assertEqual(adlar(f.tap("Panel1").uşaqlar), ["Ad", "Saxla",
                                                          "Saxla1"])
        self.assertEqual(f.tap("A1").xassələr["sol"], 24)  # sərbəst: +16
        bufer = [D.model(f)["obyektlər"][1]]               # Panel1 uşaqlarla
        y = D.yapışdır(f, bufer, None)
        self.assertEqual(y, ["Panel2"])
        self.assertEqual(adlar(f.tap("Panel2").uşaqlar), ["Ad1", "Saxla2",
                                                          "Saxla3"])
        g = yenidən(f)
        self.assertEqual(len({o.ad for o in g.hamısı()}), len(g.hamısı()))

    def test_düzləndir(self):
        ö = {"A": {"sol": 10, "yuxarı": 10, "en": 100, "hündürlük": 20},
             "B": {"sol": 40, "yuxarı": 50, "en": 60, "hündürlük": 30},
             "C": {"sol": 200, "yuxarı": 90, "en": 40, "hündürlük": 10}}
        self.assertEqual(D.düzləndir(ö, "sol"), {"B": {"sol": 10},
                                                 "C": {"sol": 10}})
        self.assertEqual(D.düzləndir(ö, "sağ")["B"], {"sol": 50})
        self.assertEqual(D.düzləndir(ö, "aşağı")["C"], {"yuxarı": 20})
        self.assertEqual(D.düzləndir(ö, "üfüqiMərkəz")["B"], {"sol": 30})
        self.assertEqual(D.düzləndir(ö, "eyniÖlçü")["C"],
                         {"en": 100, "hündürlük": 20})
        # Paylama: 10..240 aralığında 200 px obyekt, 2 boşluq × 15
        self.assertEqual(D.düzləndir(ö, "üfüqiPaylaş"), {"B": {"sol": 125}})
        self.assertEqual(D.düzləndir({"A": ö["A"]}, "sol"), {})
        with self.assertRaises(D.FormaDizaynXətası):
            D.düzləndir(ö, "naməlum")

    def test_əməliyyat_girişi(self):
        f = oxu()
        r = D.əməliyyat(f, {"növ": "əlavə", "vidjet": "düymə",
                            "ana": "Kətan1",
                            "xassələr": {"sol": 16, "yuxarı": 24}})
        self.assertEqual(r["seçim"], ["Düymə1"])
        self.assertEqual(f.tap("Düymə1").xassələr["yuxarı"], 24)
        D.əməliyyat(f, {"növ": "xassələr", "dəyişikliklər": {
            "Düymə1": {"sol": 40}, "": {"en": 700}}})
        self.assertEqual(f.xassələr["en"], 700)
        D.əməliyyat(f, {"növ": "köçür", "adlar": ["Düymə1"], "ana": None,
                        "indeks": 0, "xassələr": {"Düymə1": {"sol": None,
                                                            "yuxarı": None}}})
        self.assertEqual(f.obyektlər[0].xassələr, {"mətn": "Düymə1"})
        D.əməliyyat(f, {"növ": "düzləndir", "necə": "yuxarı", "ölçülər": {
            "A": {"sol": 0, "yuxarı": 5, "en": 10, "hündürlük": 10},
            "Kətan1": {"sol": 0, "yuxarı": 50, "en": 10, "hündürlük": 10}}})
        self.assertEqual(f.tap("Kətan1").xassələr["yuxarı"], 5)
        with self.assertRaises(D.FormaDizaynXətası):
            D.əməliyyat(f, {"növ": "naməlum"})
        with self.assertRaises(D.FormaDizaynXətası):
            D.əməliyyat(f, {"növ": "sil", "adlar": "Saxla"})
        yenidən(f)

    def test_crud(self):
        f = oxu()
        s = SX.mətndən(SXEM)
        with self.assertRaises(D.FormaDizaynXətası):
            D.crud_əlavə(f, s, "tələbələr", "Baza1")       # baza yoxdur
        D.əlavə_et(f, "VerilənlərBazası")
        yeni = D.crud_əlavə(f, s, "tələbələr", "Baza1")
        self.assertEqual(yeni[0], "Tələbələr")
        self.assertEqual(f.tap("Tələbələr").növ, "Sorğu")
        self.assertEqual(f.tap("TələbələrNaviqator").növ, "naviqator")
        with self.assertRaises(D.FormaDizaynXətası):
            D.crud_əlavə(f, s, "yoxdur", "Baza1")
        yenidən(f)


class Kətan(unittest.TestCase):
    def test_html_həqiqi_vidjetlər_və_işarələr(self):
        f = oxu()
        D.əlavə_et(f, "VerilənlərBazası")
        h = D.html(f)
        self.assertIn('data-dz="Saxla"', h)
        self.assertIn('class="v-düymə', h)                 # vidjetin öz HTML-i
        self.assertIn('data-konteyner="1"', h)
        self.assertIn("position:absolute;left:8px;top:8px", h)
        self.assertNotIn("Baza1", h)                        # görünməyən
        self.assertIn("dz-kök", h)

    def test_sərbəst_və_boş_konteyner(self):
        f = oxu()
        D.xassə_qoy(f, None, "düzülüş", "sərbəst")
        D.əlavə_et(f, "sətir")
        h = D.html(f)
        self.assertIn('data-serbest="1"', h)
        self.assertIn("dz-boş", h)

    def test_gizli_və_xətalı_obyekt(self):
        f = oxu()
        D.xassə_qoy(f, "Saxla", "görünür", False)
        D.xassə_qoy(f, "Başlıq1", "səviyyə", "yanlış dəyər")
        h = D.html(f)
        self.assertIn("dz-gizli", h)                        # dizaynda görünür

    def test_bağlı_cədvəl_sxem_sütunları(self):
        q = Path(tempfile.mkdtemp())
        try:
            (q / "m.sxem").write_text(SXEM, encoding="utf-8")
            f = oxu()
            D.əlavə_et(f, "VerilənlərBazası", xassələr={"sxem": "m.sxem"})
            D.crud_əlavə(f, SX.mətndən(SXEM), "tələbələr", "Baza1")
            v = D.verilənlər(f, q)
            self.assertEqual(v["bazalar"]["Baza1"]["cədvəllər"]["tələbələr"],
                             ["id", "ad", "sinif"])
            self.assertEqual(v["sorğular"]["Tələbələr"]["sütunlar"],
                             ["id", "ad", "sinif"])
            h = D.html(f, q)
            self.assertIn(">sinif<", h)
            self.assertNotIn((q / "məlumat.db").name, [p.name for p in q.iterdir()])
        finally:
            shutil.rmtree(q, ignore_errors=True)

    def test_kataloq(self):
        k = D.kataloq()
        self.assertIn("verilənlər", [x["ad"] for x in k["kateqoriyalar"]])
        self.assertEqual(k["növlər"]["Sorğu"]["kateqoriya"], "verilənlər")
        self.assertTrue(k["növlər"]["VerilənlərBazası"]["görünməz"])
        düymə = k["növlər"]["düymə"]
        self.assertIn("klik", düymə["hadisələr"])
        p = {x["ad"]: x for x in düymə["parametrlər"]}
        self.assertNotIn("klik", p)
        self.assertEqual(p["növ"]["növ"], "seçim")
        self.assertNotIn("məzmun", {x["ad"] for x in
                                     k["növlər"]["sütun"]["parametrlər"]})
        json.dumps(k, ensure_ascii=False)


ALQ = """\
// kod
gətir pəncərə

komponent Əsas
    vəziyyət say: tam = 0

    əməl Saxla_klik()
        yaz("salam")
    son
son

funksiya əsas()
    pəncərə.formaAç(Əsas)
son
"""


class Metodlar(unittest.TestCase):
    def test_metodlar(self):
        self.assertEqual(D.metodlar(ALQ, "Əsas"), ["Saxla_klik"])
        self.assertEqual(D.metodlar(ALQ, "Yox"), [])

    def test_əlavə_başqa_koda_toxunmur(self):
        m, s = D.metod_əlavə(ALQ, "Əsas", "Ad_dəyişdi", "dəyər")
        əvvəl, sonra = ALQ.split("son\nson\n")
        self.assertTrue(m.startswith(əvvəl + "son\n\n    əməl Ad_dəyişdi"
                                                "(dəyər)\n"))
        self.assertTrue(m.endswith("    son\nson\n" + sonra))
        self.assertEqual(m.split("\n")[s - 1].strip(),
                         "// hadisə baş verəndə işləyir")
        self.assertEqual(m.split("\n")[s - 2].strip(),
                         "əməl Ad_dəyişdi(dəyər)")
        self.assertEqual(D.metodlar(m, "Əsas"), ["Saxla_klik", "Ad_dəyişdi"])
        # Təkrar — dəyişmir, mövcud metodun sətri qaytarılır
        m2, s2 = D.metod_əlavə(m, "Əsas", "Saxla_klik")
        self.assertEqual(m2, m)
        self.assertEqual(m.split("\n")[s2 - 2].strip(), "əməl Saxla_klik()")
        from studio.diaqnostika import yoxla
        self.assertEqual([d for d in yoxla(m)["diaqnostikalar"]
                          if d["səviyyə"] == "xəta"], [])

    def test_boş_komponent_və_komponentsiz_fayl(self):
        m, s = D.metod_əlavə("komponent X\nson\n", "X", "B_klik")
        self.assertEqual(m, "komponent X\n    əməl B_klik()\n        // "
                            "hadisə baş verəndə işləyir\n    son\nson\n")
        self.assertEqual(s, 3)
        m, s = D.metod_əlavə("gətir pəncərə\n", "X", "B_klik")
        self.assertIn("komponent X\n    əməl B_klik()", m)
        self.assertEqual(m.split("\n")[s - 2].strip(), "əməl B_klik()")

    def test_hadisə_parametrləri(self):
        self.assertEqual(D.hadisə_parametrləri("klik"), "")
        self.assertEqual(D.hadisə_parametrləri("dəyişdi"), "dəyər")
        self.assertEqual(D.hadisə_metodu("Saxla", "klik"), "Saxla_klik")

    def test_yeni_forma(self):
        forma, kod = D.yeni_forma("Giriş")
        f = oxu(forma)
        self.assertEqual((f.ad, f.xassələr["başlıq"]), ("Giriş", "Giriş"))
        self.assertIn("komponent Giriş\nson", kod)
        self.assertIn("pəncərə.formaAç(Giriş)", kod)
        with self.assertRaises(D.FormaDizaynXətası):
            D.yeni_forma("1x")


# ═══════════════════════════════════════════════════════════════════════
#  Server API
# ═══════════════════════════════════════════════════════════════════════

from sinaq.test_studio import ServerSınağı                 # noqa: E402


class API(ServerSınağı):
    def setUp(self):
        for p in list(self.layihə.iterdir()):
            if p.suffix in (".forma", ".sxem", ".db") or p.name in (
                    "Əsas.alq", "modellər.alq", "Yeni.alq"):
                p.unlink()
        (self.layihə / "Əsas.forma").write_text(FORMA, encoding="utf-8")
        (self.layihə / "Əsas.alq").write_text(ALQ, encoding="utf-8")

    def ə(self, əməliyyat, mətn=None):
        g = {"yol": "Əsas.forma", "əməliyyat": əməliyyat}
        if mətn is not None:
            g["mətn"] = mətn
        return self.api("/api/forma/emeliyyat", g)

    def fayl(self, ad="Əsas.forma"):
        return (self.layihə / ad).read_text(encoding="utf-8")

    def test_oxu(self):
        kod, d = self.api("/api/forma/oxu", {"yol": "Əsas.forma"})
        self.assertEqual(kod, 200, d)
        self.assertEqual(d["metodlar"], ["Saxla_klik"])
        self.assertEqual(d["alq"], "Əsas.alq")
        self.assertIn('data-dz="Saxla"', d["html"])
        kod, d = self.api("/api/forma/oxu", {"yol": "Əsas.forma",
                                             "mətn": "forma X\n  obyekt"})
        self.assertIsNone(d["forma"])
        self.assertTrue(d["diaqnostikalar"])
        kod, _ = self.api("/api/forma/oxu", {"yol": "../x.forma"})
        self.assertNotEqual(kod, 200)
        kod, _ = self.api("/api/forma/oxu", {"yol": "salam.alq"})
        self.assertEqual(kod, 400)

    def test_əməliyyat_faylı_yazır(self):
        kod, d = self.ə({"növ": "əlavə", "vidjet": "düymə"})
        self.assertEqual(kod, 200, d)
        self.assertEqual(d["seçim"], ["Düymə1"])
        self.assertIn("obyekt Düymə1: düymə", self.fayl())
        self.assertEqual(d["mətn"], self.fayl())
        # Xətalı mətn — əməliyyat rədd edilir, fayl dəyişmir
        kod, d = self.ə({"növ": "sil", "adlar": ["Düymə1"]}, "forma X\n")
        self.assertEqual(kod, 422)
        self.assertIn("Düymə1", self.fayl())
        kod, d = self.ə({"növ": "əlavə", "vidjet": "yox"})
        self.assertEqual(kod, 422)
        # Geri al — bütöv mətn
        kod, d = self.ə({"növ": "mətn", "mətn": FORMA})
        self.assertEqual((kod, self.fayl()), (200, FORMA))

    def test_hadisə_idarəedicisi(self):
        kod, d = self.api("/api/forma/hadise", {
            "yol": "Əsas.forma", "obyekt": "Ad", "hadisə": "dəyişdi"})
        self.assertEqual(kod, 200, d)
        self.assertEqual(d["metod"], "Ad_dəyişdi")
        self.assertTrue(d["yeniMetod"])
        alq = self.fayl("Əsas.alq")
        self.assertIn("    əməl Ad_dəyişdi(dəyər)\n", alq)
        self.assertTrue(alq.startswith(ALQ.split("son\nson")[0]))
        self.assertIn("dəyişdi = Ad_dəyişdi", self.fayl())
        self.assertEqual(alq.split("\n")[d["sətir"] - 2].strip(),
                         "əməl Ad_dəyişdi(dəyər)")
        # Mövcud metod — yalnız keçid
        kod, d = self.api("/api/forma/hadise", {
            "yol": "Əsas.forma", "obyekt": "Saxla", "hadisə": "klik"})
        self.assertFalse(d["yeniMetod"])
        self.assertEqual(self.fayl("Əsas.alq"), alq)

    def test_yeni_forma(self):
        kod, d = self.api("/api/forma/yeni", {"ad": "Yeni"})
        self.assertEqual(kod, 200, d)
        self.assertTrue((self.layihə / "Yeni.forma").is_file())
        self.assertIn("komponent Yeni", self.fayl("Yeni.alq"))
        kod, _ = self.api("/api/forma/yeni", {"ad": "Yeni"})
        self.assertEqual(kod, 409)
        kod, _ = self.api("/api/forma/yeni", {"ad": "../Pis"})
        self.assertEqual(kod, 400)

    def test_sxem_redaktoru_crud_və_model(self):
        self.ə({"növ": "əlavə", "vidjet": "VerilənlərBazası"})
        kod, d = self.api("/api/forma/sxem", {"yol": "Əsas.forma",
                                              "baza": "Baza1"})
        self.assertEqual((kod, d["fayl"], d["var"]), (200, "Baza1.sxem",
                                                      False))
        sx = SX.mətndən(SXEM).lüğət()
        # Xətalı sxem saxlanmır
        pis = json.loads(json.dumps(sx))
        pis["cədvəllər"][0]["sahələr"].append(
            dict(pis["cədvəllər"][0]["sahələr"][1]))
        kod, d = self.api("/api/forma/sxem/yaz", {
            "yol": "Əsas.forma", "baza": "Baza1", "sxem": pis})
        self.assertTrue(d["xətalar"])
        self.assertFalse((self.layihə / "Baza1.sxem").exists())
        kod, d = self.api("/api/forma/sxem/yaz", {
            "yol": "Əsas.forma", "baza": "Baza1", "sxem": sx})
        self.assertEqual(kod, 200, d)
        self.assertIsNotNone(SX.fayldan(self.layihə / "Baza1.sxem"))
        self.assertIn('sxem = "Baza1.sxem"', self.fayl())
        self.assertEqual(d["verilənlər"]["bazalar"]["Baza1"]["cədvəllər"],
                         {"tələbələr": ["id", "ad", "sinif"]})
        kod, d = self.ə({"növ": "crud", "baza": "Baza1",
                         "cədvəl": "tələbələr"})
        self.assertEqual(kod, 200, d)
        self.assertIn("obyekt Tələbələr: Sorğu", self.fayl())
        self.assertEqual(d["verilənlər"]["sorğular"]["Tələbələr"]["sütunlar"],
                         ["id", "ad", "sinif"])
        kod, d = self.api("/api/forma/model", {"yol": "Əsas.forma",
                                               "baza": "Baza1"})
        self.assertEqual(kod, 200, d)
        self.assertIn("sinif Tələbə", self.fayl("modellər.alq"))

    def test_sxem_idxal(self):
        from alqor.modullar.verilenler import bağlan
        b = bağlan(f"sqlite://{self.layihə / 'k.db'}")
        b.icra("CREATE TABLE kitablar (id INTEGER PRIMARY KEY, ad TEXT "
               "NOT NULL, il INTEGER)")
        b.bağla()
        self.ə({"növ": "əlavə", "vidjet": "VerilənlərBazası",
                "xassələr": {"fayl": "k.db"}})
        kod, d = self.api("/api/forma/sxem/idxal", {"yol": "Əsas.forma",
                                                    "baza": "Baza1"})
        self.assertEqual(kod, 200, d)
        c = d["sxem"]["cədvəllər"][0]
        self.assertEqual(c["ad"], "kitablar")
        self.assertEqual([(s["ad"], s["tip"]) for s in c["sahələr"]],
                         [("id", "tam"), ("ad", "mətn"), ("il", "tam")])
        self.ə({"növ": "xassə", "ad": "Baza1", "xassə": "fayl",
                "dəyər": "yoxdur.db"})
        kod, d = self.api("/api/forma/sxem/idxal", {"yol": "Əsas.forma",
                                                    "baza": "Baza1"})
        self.assertEqual(kod, 404)
        self.assertFalse((self.layihə / "yoxdur.db").exists())

    def test_kataloq(self):
        kod, d = self.api("/api/forma/kataloq")
        self.assertEqual(kod, 200)
        self.assertIn("VerilənlərBazası", d["növlər"])


if __name__ == "__main__":
    unittest.main()
