"""`veb` modulu və şablon mühərriki sınaqları."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from alqor.sablon import Şablon, ŞablonXətası, html_qaç   # noqa: E402
from alqor.veb import _naxışı_çevir, _müddəti_saniyəyə    # noqa: E402
from test_icraci import çıxış                             # noqa: E402

# Hər sınaqda işlənən minimal serverin başlığı
BAŞLIQ = "gətir veb\n"


# ═══════════════════════════════════════════════════════════════════════
#  Marşrut naxışları (Python səviyyəsində)
# ═══════════════════════════════════════════════════════════════════════

class NaxışÇevirmə(unittest.TestCase):
    def _uyğun(self, naxış: str, yol: str):
        import re
        return re.compile(_naxışı_çevir(naxış)).match(yol)

    def test_sadə(self):
        self.assertIsNotNone(self._uyğun("/", "/"))
        self.assertIsNotNone(self._uyğun("/salam", "/salam"))
        self.assertIsNone(self._uyğun("/salam", "/salam/əlavə"))

    def test_parametr(self):
        u = self._uyğun("/istifadəçi/:id", "/istifadəçi/42")
        self.assertIsNotNone(u)
        self.assertEqual(u.group("id"), "42")

    def test_azərbaycan_parametr_adı(self):
        u = self._uyğun("/salam/:ad", "/salam/Əli")
        self.assertEqual(u.group("ad"), "Əli")

    def test_çoxlu_parametr(self):
        u = self._uyğun("/a/:x/b/:y", "/a/1/b/2")
        self.assertEqual((u.group("x"), u.group("y")), ("1", "2"))

    def test_ixtiyari_parametr(self):
        self.assertIsNotNone(self._uyğun("/məqalə/:slug?", "/məqalə"))
        u = self._uyğun("/məqalə/:slug?", "/məqalə/salam")
        self.assertEqual(u.group("slug"), "salam")

    def test_joker(self):
        u = self._uyğun("/fayl/*yol", "/fayl/a/b/c.txt")
        self.assertEqual(u.group("yol"), "a/b/c.txt")

    def test_sonda_kəsik_qəbul_olunur(self):
        self.assertIsNotNone(self._uyğun("/salam", "/salam/"))

    def test_parametr_kəsiyi_tutmur(self):
        self.assertIsNone(self._uyğun("/a/:x", "/a/b/c"))


class MüddətAyırma(unittest.TestCase):
    def test_vahidlər(self):
        self.assertEqual(_müddəti_saniyəyə("30san"), 30)
        self.assertEqual(_müddəti_saniyəyə("1dəq"), 60)
        self.assertEqual(_müddəti_saniyəyə("2dəq"), 120)
        self.assertEqual(_müddəti_saniyəyə("1saat"), 3600)
        self.assertEqual(_müddəti_saniyəyə(45), 45)
        self.assertEqual(_müddəti_saniyəyə("naməlum"), 60.0)


# ═══════════════════════════════════════════════════════════════════════
#  Server — dil səviyyəsində
# ═══════════════════════════════════════════════════════════════════════

class ServerSınağı(unittest.TestCase):
    def test_sadə_marşrut(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/", (sorğu) => veb.mətn("Salam"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.al("/")\n'
               "    yaz(c.vəziyyət())\n"
               "    yaz(c.mətnƏt())\n"
               "son")
        self.assertEqual(çıxış(kod), ["200", "Salam"])

    def test_marşrut_parametri(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/kim/:ad", funksiya(sorğu)\n'
               '        qaytar veb.mətn("Salam, {sorğu.parametr("ad")}!")\n'
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/kim/Aysel").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["Salam, Aysel!"])

    def test_json_cavabı(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/", (q) => veb.json({"ad": "Alqor", "n": 1}))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.al("/")\n'
               '    yaz(c.json()["ad"])\n'
               "son")
        self.assertEqual(çıxış(kod), ["Alqor"])

    def test_bütün_metodlar(self):
        kod = BAŞLIQ + "funksiya əsas()\n    dəyişən s = yeni veb.Server()\n"
        for alqor_metod in ("al", "göndər", "yenilə", "yamaq", "sil"):
            kod += (f'    s.{alqor_metod}("/x", (q) => '
                    f'veb.mətn("{alqor_metod}"))\n')
        kod += ("    dəyişən m = veb.sınaq.server(s)\n"
                '    yaz(m.al("/x").mətnƏt())\n'
                '    yaz(m.göndər("/x").mətnƏt())\n'
                '    yaz(m.yenilə("/x").mətnƏt())\n'
                '    yaz(m.yamaq("/x").mətnƏt())\n'
                '    yaz(m.sil("/x").mətnƏt())\n'
                "son")
        self.assertEqual(çıxış(kod),
                         ["al", "göndər", "yenilə", "yamaq", "sil"])

    def test_metod_uyğun_gəlmir(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/x", (q) => veb.mətn("a"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.göndər("/x").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["405"])

    def test_404(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/x", (q) => veb.mətn("a"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/yoxdur").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["404"])

    def test_öz_404_səhifəsi(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.tapılmadı((q) => veb.mətn("yoxdur").kod(404))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.al("/a")\n'
               "    yaz(c.vəziyyət())\n"
               "    yaz(c.mətnƏt())\n"
               "son")
        self.assertEqual(çıxış(kod), ["404", "yoxdur"])

    def test_qrup(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.qrup("/api", funksiya(q)\n'
               '        q.al("/a", (sorğu) => veb.mətn("api-a"))\n'
               '        q.al("/b", (sorğu) => veb.mətn("api-b"))\n'
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/api/a").mətnƏt())\n'
               '    yaz(m.al("/api/b").mətnƏt())\n'
               '    yaz(m.al("/a").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["api-a", "api-b", "404"])

    def test_sorğu_gövdəsi(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.göndər("/", funksiya(sorğu)\n'
               "        qaytar veb.json(sorğu.json())\n"
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.göndər("/", {"x": 5, "ad": "Əli"})\n'
               '    yaz(c.json()["x"])\n'
               '    yaz(c.json()["ad"])\n'
               "son")
        self.assertEqual(çıxış(kod), ["5", "Əli"])

    def test_sorğu_metodu_azərbaycanca(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.hamısı("/", (q) => veb.mətn(q.metod()))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").mətnƏt())\n'
               '    yaz(m.göndər("/").mətnƏt())\n'
               '    yaz(m.sil("/").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["AL", "GÖNDƏR", "SİL"])

    def test_sorğu_parametrləri(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/axtar", funksiya(sorğu)\n'
               '        qaytar veb.mətn(sorğu.sorğuParametr("q") ?? "yox")\n'
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/axtar?q=alqor").mətnƏt())\n'
               '    yaz(m.al("/axtar").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["alqor", "yox"])

    def test_kod_və_başlıq_zəncirlənir(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/", (q) => veb.mətn("a").kod(201)\n'
               '        .başlıq("X-Test", "dəyər"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["201"])

    def test_yönləndirmə(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/köhnə", (q) => veb.yönləndir("/yeni"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/köhnə").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["302"])

    def test_avtomatik_cavab_çevrilməsi(self):
        """İdarəedici `Cavab` qaytarmasa, dəyər avtomatik çevrilir."""
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/m", (q) => "sadə mətn")\n'
               '    s.al("/l", (q) => [1, 2, 3])\n'
               '    s.al("/e", (q) => <p>element</p>)\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/m").mətnƏt())\n'
               '    yaz(m.al("/l").mətnƏt())\n'
               '    yaz(m.al("/e").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod),
                         ["sadə mətn", "[1, 2, 3]", "<p>element</p>"])

    def test_sinif_nümunəsi_json_olur(self):
        kod = (BAŞLIQ +
               "sinif T\n"
               "    qurucu(açıq xassə ad: mətn, açıq xassə n: tam)\n"
               "son\n"
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/", (q) => veb.json(yeni T("Əli", 5)))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").json()["ad"])\n'
               "son")
        self.assertEqual(çıxış(kod), ["Əli"])


class AraProqramSınağı(unittest.TestCase):
    def test_öz_ara_proqramı(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               "    s.ara(funksiya(sorğu, növbəti)\n"
               '        dəyişən c = növbəti(sorğu)\n'
               '        qaytar c.başlıq("X-Ara", "işlədi")\n'
               "    son)\n"
               '    s.al("/", (q) => veb.mətn("a"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["a"])

    def test_ara_proqram_cavabı_dəyişə_bilər(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               "    s.ara(funksiya(sorğu, növbəti)\n"
               '        qaytar veb.mətn("ara dayandırdı").kod(403)\n'
               "    son)\n"
               '    s.al("/", (q) => veb.mətn("çatılmadı"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.al("/")\n'
               "    yaz(c.vəziyyət())\n"
               "    yaz(c.mətnƏt())\n"
               "son")
        self.assertEqual(çıxış(kod), ["403", "ara dayandırdı"])

    def test_təhlükəsizlik_başlıqları(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               "    s.ara(veb.təhlükəsizlikBaşlıqları())\n"
               '    s.al("/", (q) => veb.mətn("a"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["200"])

    def test_sürət_limiti(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.ara(veb.sürətLimiti(2, "1dəq"))\n'
               '    s.al("/", (q) => veb.mətn("a"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").vəziyyət())\n'
               '    yaz(m.al("/").vəziyyət())\n'
               '    yaz(m.al("/").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["200", "200", "429"])

    def test_sıxma(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               "    s.ara(veb.sıxma(10))\n"
               '    s.al("/", (q) => veb.mətn("a" * 200))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.al("/", {"Accept-Encoding": "gzip"})\n'
               "    yaz(c.uzunluq() < 200)\n"
               "son")
        self.assertEqual(çıxış(kod), ["doğru"])

    def test_marşruta_xas_ara_proqram(self):
        kod = (BAŞLIQ +
               "funksiya qoruma(sorğu, növbəti)\n"
               '    əgər sorğu.başlıq("X-Açar") boşdur onda\n'
               '        qaytar veb.mətn("icazə yoxdur").kod(401)\n'
               "    son\n"
               "    qaytar növbəti(sorğu)\n"
               "son\n"
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/qorunan", [qoruma], (q) => veb.mətn("gizli"))\n'
               '    s.al("/açıq", (q) => veb.mətn("açıq"))\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/qorunan").vəziyyət())\n'
               '    yaz(m.al("/qorunan", {"X-Açar": "a"}).mətnƏt())\n'
               '    yaz(m.al("/açıq").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["401", "gizli", "açıq"])


class SessiyaSınağı(unittest.TestCase):
    def test_sayğac(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/", funksiya(sorğu)\n'
               '        dəyişən say = sorğu.sessiya().al("say", 0) + 1\n'
               '        sorğu.sessiya().qoy("say", say)\n'
               '        qaytar veb.mətn("{say}")\n'
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").mətnƏt())\n'
               '    yaz(m.al("/").mətnƏt())\n'
               '    yaz(m.al("/").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["1", "2", "3"])

    def test_təmizləmə(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/qoy", funksiya(sorğu)\n'
               '        sorğu.sessiya().qoy("ad", "Əli")\n'
               '        qaytar veb.mətn("qoyuldu")\n'
               "    son)\n"
               '    s.al("/oxu", funksiya(sorğu)\n'
               '        qaytar veb.mətn(sorğu.sessiya().al("ad") ?? "yox")\n'
               "    son)\n"
               '    s.al("/sil", funksiya(sorğu)\n'
               "        sorğu.sessiya().təmizlə()\n"
               '        qaytar veb.mətn("silindi")\n'
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    m.al("/qoy")\n'
               '    yaz(m.al("/oxu").mətnƏt())\n'
               '    m.al("/sil")\n'
               '    yaz(m.al("/oxu").mətnƏt())\n'
               "son")
        self.assertEqual(çıxış(kod), ["Əli", "yox"])


class XətaİdarəetməsiSınağı(unittest.TestCase):
    def test_idarəedicidəki_xəta_500_verir(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               '    s.al("/", funksiya(sorğu)\n'
               "        qaytar 1 ~/ 0\n"
               "    son)\n"
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    yaz(m.al("/").vəziyyət())\n'
               "son")
        self.assertEqual(çıxış(kod), ["500"])

    def test_öz_xəta_idarəedicisi(self):
        kod = (BAŞLIQ +
               "funksiya əsas()\n"
               "    dəyişən s = yeni veb.Server()\n"
               "    s.xətaİdarəedicisi(funksiya(sorğu, xəta)\n"
               '        qaytar veb.json({"xəta": xəta.mesaj}).kod(500)\n'
               "    son)\n"
               '    s.al("/", (q) => 1 ~/ 0)\n'
               "    dəyişən m = veb.sınaq.server(s)\n"
               '    dəyişən c = m.al("/")\n'
               "    yaz(c.vəziyyət())\n"
               '    yaz(c.json()["xəta"])\n'
               "son")
        sətirlər = çıxış(kod)
        self.assertEqual(sətirlər[0], "500")
        self.assertIn("sıfır", sətirlər[1])


# ═══════════════════════════════════════════════════════════════════════
#  Şablon mühərriki
# ═══════════════════════════════════════════════════════════════════════

class ŞablonSınağı(unittest.TestCase):
    def _göstər(self, şablon: str, verilənlər: dict) -> str:
        from alqor.icraci import İcraçı
        return Şablon(şablon).göstər(İcraçı(), verilənlər)

    def test_dəyər(self):
        self.assertEqual(
            self._göstər("Salam, {{ ad }}!", {"ad": "Aysel"}),
            "Salam, Aysel!")

    def test_ifadə(self):
        self.assertEqual(
            self._göstər("{{ yaş + 1 }}", {"yaş": 24}), "25")

    def test_html_qaçışı_avtomatikdir(self):
        self.assertEqual(
            self._göstər("{{ x }}", {"x": "<script>"}),
            "&lt;script&gt;")

    def test_xam_filtri_qaçışı_söndürür(self):
        self.assertEqual(
            self._göstər("{{ x | xam }}", {"x": "<b>a</b>"}),
            "<b>a</b>")

    def test_filtrlər(self):
        self.assertEqual(
            self._göstər("{{ a | böyüyə }}", {"a": "ışıq"}), "IŞIQ")
        self.assertEqual(
            self._göstər("{{ a | kəs(5) }}",
                         {"a": "çox uzun mətn"}), "çox u…")
        self.assertEqual(
            self._göstər("{{ a | yuvarlaqlaşdır(2) }}",
                         {"a": 3.14159}), "3.14")

    def test_pul_filtri(self):
        nəticə = self._göstər("{{ a | pul }}", {"a": 19.99})
        self.assertIn("19,99", nəticə)
        self.assertIn("₼", nəticə)

    def test_standart_filtri(self):
        self.assertEqual(
            self._göstər('{{ a | standart("yox") }}', {"a": ""}), "yox")

    def test_əgər(self):
        ş = "{% əgər var %}bəli{% yoxsa %}xeyr{% son %}"
        self.assertEqual(self._göstər(ş, {"var": True}), "bəli")
        self.assertEqual(self._göstər(ş, {"var": False}), "xeyr")

    def test_əgər_ifadə_ilə(self):
        ş = "{% əgər yaş >= 18 %}yetkin{% son %}"
        self.assertEqual(self._göstər(ş, {"yaş": 24}), "yetkin")
        self.assertEqual(self._göstər(ş, {"yaş": 10}), "")

    def test_hər(self):
        ş = "{% hər x üçün siyahı içində %}[{{ x }}]{% son %}"
        self.assertEqual(
            self._göstər(ş, {"siyahı": [1, 2, 3]}), "[1][2][3]")

    def test_hər_boş_halda(self):
        ş = ("{% hər x üçün s içində %}{{ x }}"
             "{% yoxsa %}boşdur{% son %}")
        self.assertEqual(self._göstər(ş, {"s": []}), "boşdur")

    def test_hər_lüğət_üzərində(self):
        ş = "{% hər a, d üçün l içində %}{{ a }}={{ d }};{% son %}"
        self.assertEqual(
            self._göstər(ş, {"l": {"x": 1, "y": 2}}), "x=1;y=2;")

    def test_dövr_dəyişənləri(self):
        ş = ("{% hər x üçün s içində %}{{ _indeks }}"
             "{% əgər _sondur %}!{% son %}{% son %}")
        self.assertEqual(self._göstər(ş, {"s": ["a", "b"]}), "01!")

    def test_iç_içə(self):
        ş = ("{% hər s üçün sətirlər içində %}"
             "{% hər h üçün s içində %}{{ h }}{% son %}|{% son %}")
        self.assertEqual(
            self._göstər(ş, {"sətirlər": [[1, 2], [3]]}), "12|3|")

    def test_şərh(self):
        self.assertEqual(self._göstər("a{# gizli #}b", {}), "ab")

    def test_lüğət_açarı(self):
        self.assertEqual(
            self._göstər('{{ l["ad"] }}', {"l": {"ad": "Əli"}}), "Əli")

    def test_siyahı_indeksi(self):
        self.assertEqual(
            self._göstər("{{ s[1] }}", {"s": [10, 20, 30]}), "20")

    def test_boş_dəyər_yazılmır(self):
        self.assertEqual(self._göstər("[{{ a }}]", {"a": None}), "[]")

    def test_obyekt_xassəsi(self):
        """Şablona dil obyektinin nümunəsi ötürülür."""
        kod = BAŞLIQ + """
sinif İstifadəçi
    qurucu(açıq xassə ad: mətn)
son

funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.al("/", funksiya(sorğu)
        dəyişən i = yeni İstifadəçi("Aysel")
        qaytar veb.mətn("Salam, {i.ad}!")
    son)
    dəyişən m = veb.sınaq.server(s)
    yaz(m.al("/").mətnƏt())
son
"""
        self.assertEqual(çıxış(kod), ["Salam, Aysel!"])

    def test_bağlanmamış_blok(self):
        with self.assertRaises(ŞablonXətası):
            Şablon("{% əgər x %}a")

    def test_uyğunsuz_son(self):
        with self.assertRaises(ŞablonXətası):
            Şablon("a{% son %}")

    def test_naməlum_əmr(self):
        with self.assertRaises(ŞablonXətası):
            Şablon("{% naməlumƏmr %}")

    def test_naməlum_filtr(self):
        with self.assertRaises(ŞablonXətası):
            self._göstər("{{ a | yoxdurBelə }}", {"a": 1})

    def test_html_qaç_funksiyası(self):
        self.assertEqual(html_qaç('<a href="x">&'),
                         "&lt;a href=&quot;x&quot;&gt;&amp;")


class ŞablonMirasıSınağı(unittest.TestCase):
    def setUp(self):
        self.qovluq = Path(tempfile.mkdtemp())
        (self.qovluq / "əsas.alqorhtml").write_text(
            "<html><body>{% blok məzmun %}standart{% son %}"
            "<footer>alt</footer></body></html>",
            encoding="utf-8")
        (self.qovluq / "alt.alqorhtml").write_text(
            '{% genişlət "əsas.alqorhtml" %}'
            "{% blok məzmun %}<h1>{{ başlıq }}</h1>{% son %}",
            encoding="utf-8")
        (self.qovluq / "parça.alqorhtml").write_text(
            "<nav>{{ ad }}</nav>", encoding="utf-8")
        (self.qovluq / "daxil.alqorhtml").write_text(
            '{% daxilEt "parça.alqorhtml" %}<p>əsas</p>',
            encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.qovluq, ignore_errors=True)

    def _göstər(self, fayl: str, verilənlər: dict) -> str:
        from alqor.icraci import İcraçı
        from alqor.sablon import şablonu_yüklə
        ş = şablonu_yüklə(fayl, self.qovluq, keşlə=False)
        return ş.göstər(İcraçı(), verilənlər)

    def test_miras(self):
        nəticə = self._göstər("alt.alqorhtml", {"başlıq": "Salam"})
        self.assertIn("<h1>Salam</h1>", nəticə)
        self.assertIn("<footer>alt</footer>", nəticə)
        self.assertNotIn("standart", nəticə)

    def test_standart_blok(self):
        nəticə = self._göstər("əsas.alqorhtml", {})
        self.assertIn("standart", nəticə)

    def test_daxil_etmə(self):
        nəticə = self._göstər("daxil.alqorhtml", {"ad": "Menyu"})
        self.assertIn("<nav>Menyu</nav>", nəticə)
        self.assertIn("<p>əsas</p>", nəticə)

    def test_tapılmayan_şablon(self):
        with self.assertRaises(ŞablonXətası):
            self._göstər("yoxdur.alqorhtml", {})


class StatikVəŞablonCavabı(unittest.TestCase):
    """Skriptin qovluğuna nisbətən həll olunan yollar."""

    def setUp(self):
        self.qovluq = Path(tempfile.mkdtemp())
        (self.qovluq / "statik").mkdir()
        (self.qovluq / "statik" / "üslub.css").write_text(
            "body { rəng: qara }", encoding="utf-8")
        (self.qovluq / "gizli.txt").write_text("gizli", encoding="utf-8")
        (self.qovluq / "səhifə.alqorhtml").write_text(
            "<h1>{{ başlıq }}</h1>", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.qovluq, ignore_errors=True)

    def _işlət(self, kod: str) -> list[str]:
        """Kodu müvəqqəti qovluq əsas qovluq sayaraq işlədir."""
        from alqor.icraci import İcraçı
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        x = XətaToplayıcı()
        mənbə = Mənbə.mətndən(BAŞLIQ + kod, "sınaq.alqor", x)
        ağac = Parser(Lekser(mənbə, x).leksə(), mənbə, x).ayır()
        self.assertTrue(x.uğurludur(), x.hesabat(False))

        sətirlər: list[str] = []
        icraçı = İcraçı(çıxış=sətirlər.append, giriş=lambda: "")
        icraçı.əsas_qovluq = self.qovluq
        icraçı.işlət(ağac, [])
        return sətirlər

    # Statik qovluğu quraşdırılmış server
    QUR = """
funksiya müştəri() -> istənilən
    dəyişən s = yeni veb.Server()
    s.statik("/statik", "statik")
    qaytar veb.sınaq.server(s)
son
"""

    def test_statik_fayl_verilir(self):
        sətirlər = self._işlət(self.QUR + """
funksiya əsas()
    dəyişən c = müştəri().al("/statik/üslub.css")
    yaz(c.vəziyyət())
    yaz(c.mətnƏt())
son
""")
        self.assertEqual(sətirlər, ["200", "body { rəng: qara }"])

    def test_məzmun_tipi_təyin_olunur(self):
        sətirlər = self._işlət(self.QUR + """
funksiya əsas()
    yaz(müştəri().al("/statik/üslub.css").başlıq("Content-Type"))
son
""")
        self.assertIn("text/css", sətirlər[0])

    def test_qovluqdan_qaçmaq_mümkün_deyil(self):
        """`../` ilə kök qovluqdan kənara çıxmaq rədd edilir."""
        for pis in ("/statik/../gizli.txt",
                    "/statik/..%2Fgizli.txt",
                    "/statik/%2e%2e/gizli.txt",
                    "/statik/....//gizli.txt",
                    "/statik/..\\gizli.txt"):
            # Alqor mətn literalı üçün tərs kəsiyi ikiləşdiririk
            qaçırılmış = pis.replace("\\", "\\\\")
            sətirlər = self._işlət(self.QUR + f"""
funksiya əsas()
    dəyişən c = müştəri().al("{qaçırılmış}")
    yaz(c.vəziyyət())
    yaz("gizli" içindədir c.mətnƏt())
son
""")
            self.assertIn(sətirlər[0], ("400", "403", "404"),
                          f"{pis} → {sətirlər[0]}")
            self.assertEqual(sətirlər[1], "yanlış", pis)

    def test_olmayan_statik_fayl(self):
        sətirlər = self._işlət(self.QUR + """
funksiya əsas()
    yaz(müştəri().al("/statik/yoxdur.css").vəziyyət())
son
""")
        self.assertEqual(sətirlər, ["404"])

    def test_şablon_cavabı(self):
        sətirlər = self._işlət("""
funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.şablonQovluğu(".")
    s.al("/", funksiya(sorğu)
        qaytar veb.şablon("səhifə.alqorhtml", {"başlıq": "Salam"})
    son)
    dəyişən c = veb.sınaq.server(s).al("/")
    yaz(c.vəziyyət())
    yaz(c.mətnƏt())
son
""")
        self.assertEqual(sətirlər, ["200", "<h1>Salam</h1>"])

    def test_fayl_cavabı(self):
        sətirlər = self._işlət("""
funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.al("/f", (q) => veb.fayl("gizli.txt"))
    yaz(veb.sınaq.server(s).al("/f").mətnƏt())
son
""")
        self.assertEqual(sətirlər, ["gizli"])


class NümunəSınağı(unittest.TestCase):
    def test_05_veb_serveri_işləyir(self):
        yol = (Path(__file__).parent.parent.parent / "numuneler"
               / "05-veb-server.alqor")
        if not yol.exists():
            self.skipTest("nümunə yoxdur")

        from alqor.icraci import İcraçı
        from alqor.lekser import Lekser
        from alqor.menbe import Mənbə
        from alqor.parser import Parser
        from alqor.xeta import XətaToplayıcı

        x = XətaToplayıcı()
        s = Mənbə.fayldan(yol, x)
        ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        self.assertTrue(x.uğurludur(), x.hesabat(False))

        sətirlər: list[str] = []
        icraçı = İcraçı(çıxış=sətirlər.append, giriş=lambda: "")
        icraçı.əsas_qovluq = yol.parent
        kod = icraçı.işlət(ağac, ["sınaq"])
        self.assertEqual(kod, 0)

        hamısı = "\n".join(sətirlər)
        self.assertIn("201", hamısı)
        self.assertIn("422", hamısı)
        self.assertIn("Süd al", hamısı)
        self.assertIn("Tapşırıqlar", hamısı)


if __name__ == "__main__":
    unittest.main(verbosity=2)
