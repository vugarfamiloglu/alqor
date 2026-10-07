"""alqorlint — statik təhlil qaydaları."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import alqorlint as L                              # noqa: E402

KÖK = Path(__file__).parent.parent


def adlar(kod: str, **ayar) -> list[str]:
    n = L.mətni_yoxla(kod, "sinaq.alq", ayar)
    assert n.sintaksis.uğurludur(), n.sintaksis.hesabat(False)
    return [t.qayda.ad for t in n.tapıntılar]


class QaydaSınağı(unittest.TestCase):
    def test_qaydalar_cədvəli(self):
        kodlar = [q.kod for q in L.QAYDALAR]
        self.assertEqual(len(kodlar), len(set(kodlar)))
        self.assertEqual(len(L.QAYDA_ADI), len(L.QAYDALAR))
        for q in L.QAYDALAR:
            self.assertIn(q.səviyyə, ("xəta", "xəbərdarlıq", "məlumat"))
            self.assertRegex(q.kod, r"^ALQ-Y\d{3}$")

    def test_istifadəsiz_idxal_və_funksiya(self):
        a = adlar("gətir riyaziyyat\ngətir json\nyaz(json.yaz(1))\n"
                  "funksiya köməkçi()\n    yaz(1)\nson\n")
        self.assertEqual(a.count("istifadəsiz-idxal"), 1)
        self.assertIn("istifadəsiz-funksiya", a)
        self.assertNotIn("istifadəsiz-funksiya",
                         adlar("funksiya əsas()\n    yaz(1)\nson\n"))
        self.assertIn("gətir-ulduz", adlar("gətir riyaziyyat.*\n"
                                           "yaz(kök(4))\n"))

    def test_adlandırma(self):
        a = adlar("dəyişən ad_soyad = 1\nyaz(ad_soyad)\n"
                  "sinif istifadəçi\nson\n"
                  "funksiya Hesabla(X: tam) -> tam\n    qaytar X\nson\n"
                  "yaz(Hesabla(1), yeni istifadəçi())\n"
                  "sabit maksSay = 3\nyaz(maksSay)\n")
        self.assertEqual(a.count("adlandırma-dəyişən"), 3)
        self.assertIn("adlandırma-tip", a)
        self.assertIn("adlandırma-sabit", a)
        self.assertEqual(L._kiçik_dəvə("ad_soyad"), "adSoyad")
        self.assertEqual(L._böyük_dəvə("istifadəçi_hesabı"),
                         "İstifadəçiHesabı")
        self.assertEqual(L._böyük_sabit("maksSay"), "MAKS_SAY")
        self.assertEqual(L._böyük_sabit("ilkİnsan"), "İLK_İNSAN")

    def test_potensial_xətalar(self):
        a = adlar(
            "funksiya f(x: tam) -> tam\n"
            "    x = x\n"
            "    əgər yanlış onda\n        yaz(1)\n    son\n"
            "    əgər x == x onda\n        yaz(2)\n    son\n"
            "    cəhd et\n        yaz(3)\n    tut e\n    son\n"
            '    dəyişən l = {"a": 1, "a": 2}\n'
            "    seç x\n        hal 1 → yaz(1)\n"
            "        hal 1 → yaz(2)\n    son\n"
            "    əgər deyil x == 3 onda\n        yaz(l)\n    son\n"
            "    qaytar x\n    yaz(4)\nson\nyaz(f(1))\n")
        for ad in ("özünə-mənimsətmə", "sabit-şərt", "özü-ilə-müqayisə",
                   "boş-tut", "təkrar-açar", "təkrar-hal",
                   "deyil-prioriteti", "əlçatmaz-kod"):
            self.assertIn(ad, a, ad)
        # `nə qədər ki doğru` — qəsdən sonsuz dövr, xəbərdarlıq yox
        self.assertNotIn("sabit-şərt", adlar(
            "nə qədər ki doğru\n    dayan\nson\n"))

    def test_mürəkkəblik(self):
        dərin = ("funksiya f(x: tam)\n" + "".join(
            "    " * (i + 1) + "əgər x > 0 onda\n" for i in range(5)) +
            "    " * 6 + "yaz(x)\n" + "".join(
            "    " * (i + 1) + "son\n" for i in reversed(range(5))) +
            "son\nf(1)\n")
        self.assertIn("dərin-iç-içəlik", adlar(dərin))
        self.assertNotIn("dərin-iç-içəlik", adlar(dərin, maks_dərinlik=6))
        uzun = "funksiya f()\n" + "    yaz(1)\n" * 60 + "son\nf()\n"
        self.assertIn("uzun-funksiya", adlar(uzun))
        self.assertIn("çox-parametr", adlar(
            "funksiya f(a: tam, b: tam, c: tam, d: tam, e: tam, g: tam, "
            "h: tam)\n    yaz(a, b, c, d, e, g, h)\nson\n"
            "f(1, 2, 3, 4, 5, 6, 7)\n"))
        self.assertIn("uzun-sətir", adlar("yaz(" + '"x" + ' * 30 +
                                          '"y")\n'))

    def test_təhlükəsizlik(self):
        a = adlar(
            'dəyişən parol = "gizli12345"\n'
            'dəyişən açar = "AKIAABCDEFGHIJKLMNOP"\n'
            "gətir verilənlər\n"
            'dəyişən b = verilənlər.aç(":memory:")\n'
            'dəyişən ad = "x"\n'
            'b.sorğu("SELECT * FROM t WHERE ad = \'{ad}\'")\n'
            'b.sorğu("SELECT * FROM t WHERE ad = ?", ad)\n'
            'b.icra("DELETE FROM t WHERE id = " + ad)\n'
            "yaz(parol, açar)\n")
        self.assertEqual(a.count("gizli-açar"), 2)
        self.assertEqual(a.count("sql-birləşdirmə"), 2)
        self.assertIn("xam-html", adlar(
            'dəyişən ş = "<p>{{ mətn | xam }}</p>"\nyaz(ş)\n'))

    def test_performans_və_üslub(self):
        a = adlar(
            'dəyişən s = ""\n'
            "dəyişən l = [1, 2]\n"
            "hər i üçün 0..<l.uzunluq() içində\n"
            "    s += \"x{l[i]}\"\nson\n"
            "dəyişən a = doğru\ndəyişən b = yanlış\n"
            "əgər a və b və ya s == \"\" onda\n    yaz(1)\nson\n"
            "əgər a == doğru onda\n    yaz(2)\nson\n")
        for ad in ("dövrdə-mətn-birləşdirmə", "indeksli-dövr",
                   "qarışıq-prioritet", "məntiqlə-müqayisə"):
            self.assertIn(ad, a, ad)
        # Mötərizəli — xəbərdarlıq yox; tipi bilinməyən — sadələşdirmə yox
        self.assertNotIn("qarışıq-prioritet", adlar(
            "dəyişən a = doğru\nəgər (a və a) və ya a onda\n    yaz(1)\n"
            "son\n"))
        self.assertNotIn("məntiqlə-müqayisə", adlar(
            'dəyişən l = {"a": "x"}\nyaz(l["a"] == doğru)\n'))

    def test_əlçatanlıq(self):
        a = adlar(
            "gətir vidjet\n"
            "komponent K\n    göstər()\n        qaytar <div>\n"
            '            <img src="a.png"/>\n'
            '            <img src="b.png" alt=""/>\n'
            "            <button></button>\n"
            "            <button>Saxla</button>\n"
            "            <input/>\n"
            '            {vidjet.şəkil("c.png")}\n'
            "        </div>\n    son\nson\n")
        self.assertEqual(a.count("şəkil-alt"), 2)
        self.assertEqual(a.count("mətnsiz-düymə"), 1)
        self.assertEqual(a.count("etiketsiz-sahə"), 1)


class AyarSınağı(unittest.TestCase):
    KOD = ('dəyişən parol = "gizli12345"\nyaz(parol)\n'
           "funksiya F()\n    yaz(1)\nson\nF()\n")

    def test_söndür_və_xəta(self):
        n = L.mətni_yoxla(self.KOD, "a.alq", {"söndür": ["adlandırma-*"],
                                              "xəta": ["gizli-açar"]})
        self.assertEqual([(t.qayda.ad, t.səviyyə) for t in n.tapıntılar],
                         [("gizli-açar", "xəta")])

    def test_sərtlik(self):
        a = L.mətni_yoxla(self.KOD, "a.alq", {"sərtlik": "sərbəst"})
        self.assertEqual([t.qayda.ad for t in a.tapıntılar], ["gizli-açar"])
        k = "sabit maksSay = 1\nyaz(maksSay)\n"
        s = L.mətni_yoxla(k, "a.alq", {"sərtlik": "sərt"})
        self.assertEqual(s.tapıntılar[0].səviyyə, "xəbərdarlıq")
        n = L.mətni_yoxla(k, "a.alq", {})
        self.assertEqual(n.tapıntılar[0].səviyyə, "məlumat")

    def test_şərh_ilə_söndürmə(self):
        k = ('dəyişən parol = "gizli12345"   // lint: söndür gizli-açar\n'
             "yaz(parol)\n")
        self.assertEqual(adlar(k), [])
        k2 = ("// alqor: lint-söndür istifadəsiz-*\n"
              "gətir json\nfunksiya köməkçi()\n    yaz(1)\nson\n")
        self.assertEqual(adlar(k2), [])

    def test_düzəlt(self):
        k = ("gətir json\ngətir riyaziyyat\n"
             "funksiya f(a: məntiq, x: tam?)\n"
             "    əgər a == doğru onda\n        yaz(1)\n    son\n"
             "    əgər a != doğru və x == boş onda\n        yaz(2)\n    son\n"
             "son\nf(doğru, boş)\nyaz(riyaziyyat.Pİ)\n")
        n = L.mətni_yoxla(k, "a.alq")
        yeni, say = L.düzəlt(k, n.tapıntılar)
        self.assertEqual(say, 4)
        self.assertNotIn("gətir json", yeni)
        self.assertIn("əgər a onda", yeni)
        self.assertIn("əgər deyil a və x boşdur onda", yeni)
        self.assertEqual([t.qayda.ad for t in L.mətni_yoxla(
            yeni, "a.alq").tapıntılar], [])


class ƏmrSətriSınağı(unittest.TestCase):
    def işlət(self, *arq, qovluq=None):
        return subprocess.run(
            [sys.executable, str(KÖK / "alqorc.py"), "lint", *arq],
            capture_output=True, text=True, encoding="utf-8", cwd=qovluq,
            env={**os.environ, "PYTHONIOENCODING": "utf-8",
                 "ALQOR_RENG": "heçvaxt"}, timeout=60)

    def test_layihə_ayarı_json_və_düzəlt(self):
        with tempfile.TemporaryDirectory() as q:
            Path(q, "layihe.alq").write_text(
                '[paket]\nad = "sınaq"\n\n[lint]\nsöndür = ["adlandırma-*"]\n'
                'xəta = ["istifadəsiz-idxal"]\n', encoding="utf-8")
            Path(q, "a.alq").write_text("gətir json\nyaz(1)\n",
                                        encoding="utf-8")
            r = self.işlət("--json", ".", qovluq=q)
            self.assertEqual(r.returncode, 1, r.stderr)
            d = json.loads(r.stdout)
            self.assertEqual([(x["ad"], x["səviyyə"], x["sətir"]) for x in d],
                             [("istifadəsiz-idxal", "xəta", 1)])
            r = self.işlət("--düzəlt", ".", qovluq=q)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("1 problem avtomatik düzəldildi", r.stdout)
            self.assertEqual(Path(q, "a.alq").read_text(encoding="utf-8"),
                             "yaz(1)\n")

    def test_qaydalar_və_nümunələr_təmizdir(self):
        r = self.işlət("--qaydalar")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ALQ-Y051", r.stdout)
        r = self.işlət(str(KÖK.parent / "numuneler"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn(" xəta,", r.stdout.replace("0 xəta,", ""))


if __name__ == "__main__":
    unittest.main()
