"""alqorpm (paket meneceri), alqorhub (depo) və paket idxalı."""

import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import alqorhub as H                               # noqa: E402
from alqor import alqorpm as P                                # noqa: E402
from alqor.paketler import Aralıq, Versiya, paket_tap         # noqa: E402

KÖK = Path(__file__).parent.parent


class VersiyaSınağı(unittest.TestCase):
    def test_sıralama(self):
        v = [Versiya.oxu(x) for x in ("1.0.0", "1.0.0-beta", "1.0.0-alpha.2",
                                      "1.0.0-alpha.10", "0.9.9", "1.2")]
        self.assertEqual([str(x) for x in sorted(v)],
                         ["0.9.9", "1.0.0-alpha.2", "1.0.0-alpha.10",
                          "1.0.0-beta", "1.0.0", "1.2.0"])

    def test_aralıqlar(self):
        hal = {
            "^1.2.3": (["1.2.3", "1.9.0"], ["2.0.0", "1.2.2"]),
            "^0.2.3": (["0.2.9"], ["0.3.0"]),
            "^0.0.3": (["0.0.3"], ["0.0.4"]),
            "~1.4.2": (["1.4.9"], ["1.5.0"]),
            "2.1": (["2.1.0", "2.9.9"], ["3.0.0", "2.0.9"]),
            "=1.2.3": (["1.2.3"], ["1.2.4"]),
            ">=1.2 <2": (["1.5.0"], ["2.0.0", "1.1.0"]),
            "1.2.*": (["1.2.7"], ["1.3.0"]),
            "*": (["0.0.1", "9.9.9"], ["1.0.0-beta"]),
            "1.0 || ^3": (["1.5.0", "3.1.0"], ["2.0.0"]),
            ">=1.0.0-beta": (["1.0.0-beta.2", "1.0.0"], ["1.0.1-rc"]),
        }
        for a, (bəli, xeyr) in hal.items():
            r = Aralıq(a)
            for v in bəli:
                self.assertTrue(r.uyğundur(v), f"{a} ∋ {v}")
            for v in xeyr:
                self.assertFalse(r.uyğundur(v), f"{a} ∌ {v}")


def _paket(q: Path, ad: str, versiya: str, ası: dict | None = None,
           kod: str = "funksiya f() -> tam\n    qaytar 1\nson\n") -> Path:
    (q / "mənbə").mkdir(parents=True, exist_ok=True)
    s = f'[paket]\nad = "{ad}"\nversiya = "{versiya}"\ntəsvir = "{ad} təsviri"\n'
    s += '\n[qurma]\ngiriş = "mənbə/əsas.alq"\n\n[asılılıqlar]\n'
    for a, d in (ası or {}).items():
        s += f'{json.dumps(a, ensure_ascii=False) if "/" in a else a} = ' \
             f'{json.dumps(d, ensure_ascii=False) if isinstance(d, str) else P._dəyər_mətni(d)}\n'
    (q / "layihe.alq").write_text(s, encoding="utf-8")
    (q / "mənbə" / "əsas.alq").write_text(kod, encoding="utf-8")
    (q / "README.md").write_text(f"# {ad}\n\nSınaq paketi.\n",
                                 encoding="utf-8")
    return q


class HubSınağı(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = Path(tempfile.mkdtemp(prefix="alqorpm-")).resolve()
        cls.hub = H.Hub(cls.q / "hub", adminlər={"admin"})
        cls.s = H.server(cls.hub, port=0)
        threading.Thread(target=cls.s.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.s.server_address[1]}"
        cls.nişan = cls.hub.qeydiyyat("aysel", "gizli12345")
        cls.admin = cls.hub.qeydiyyat("admin", "gizli12345")
        os.environ["ALQOR_EV"] = str(cls.q / "ev")
        # paketlər: a 1.0.0, 1.1.0, 2.0.0; b 1.0.0 (a ^1); c 1.0.0 (a ^2)
        for ad, v, ası in [("a", "1.0.0", {}), ("a", "1.1.0", {}),
                           ("a", "2.0.0", {}), ("b", "1.0.0", {"a": "^1"}),
                           ("c", "1.0.0", {"a": "^2"}),
                           ("@şirkət/analitika", "0.3.0", {"a": "*"})]:
            d = _paket(cls.q / "mənbələr" / f"{ad}-{v}".replace("/", "_"),
                       ad, v, ası,
                       f'funksiya versiyaMətni() -> mətn\n    qaytar "{ad} {v}"\nson\n')
            arxiv, _ = P.arxiv_yarat(d)
            cls.hub.yayımla("aysel", ad, v, arxiv)

    @classmethod
    def tearDownClass(cls):
        cls.s.shutdown()
        cls.s.server_close()
        os.environ.pop("ALQOR_EV", None)
        shutil.rmtree(cls.q, ignore_errors=True)

    def layihə(self, ad: str, ası: dict, kod: str = "yaz(1)\n") -> Path:
        q = Path(tempfile.mkdtemp(dir=self.q))
        _paket(q, ad, "0.1.0", ası, kod)
        return q

    def həll(self, ası: dict, kilid=None):
        k = self.layihə("l", ası)
        return P.Həlledici(k, P.Depo(self.url), kilid or {}).həll_et(ası, {})

    def test_həll_ən_yüksək_uyğun(self):
        h = self.həll({"a": "^1"})
        self.assertEqual(h.seçimlər["a"].versiya, "1.1.0")
        h = self.həll({"b": "1", "a": "*"})
        self.assertEqual(h.seçimlər["a"].versiya, "1.1.0")   # b ^1 tələb edir

    def test_ziddiyyət(self):
        with self.assertRaises(P.PMXətası) as x:
            self.həll({"b": "1", "c": "1"})
        self.assertIn("b@1.0.0 tələb edir: ^1", str(x.exception))
        self.assertIn("c@1.0.0 tələb edir: ^2", str(x.exception))
        with self.assertRaises(P.PMXətası):
            self.həll({"a": "^5"})
        with self.assertRaises(P.PMXətası):
            self.həll({"yoxdur": "1"})

    def test_kilid_üstünlüyü(self):
        kilid = {"a": P.Seçim("a", "1.0.0", "depo:x")}
        self.assertEqual(self.həll({"a": "^1"}, kilid).seçimlər["a"].versiya,
                         "1.0.0")

    def test_hub_qaydaları(self):
        d = _paket(self.q / "x", "a", "1.1.0")
        arxiv, _ = P.arxiv_yarat(d)
        with self.assertRaises(H.HubXətası) as x:             # dəyişməzlik
            self.hub.yayımla("aysel", "a", "1.1.0", arxiv)
        self.assertEqual(x.exception.kod, 409)
        başqa = self.hub.qeydiyyat("orxan", "gizli12345")
        d = _paket(self.q / "y", "a", "9.0.0")
        with self.assertRaises(H.HubXətası) as x:             # sahib deyil
            self.hub.yayımla(self.hub.kim(başqa), "a", "9.0.0",
                             P.arxiv_yarat(d)[0])
        self.assertEqual(x.exception.kod, 403)
        with self.assertRaises(H.HubXətası) as x:             # ad uyğunsuz
            self.hub.yayımla("aysel", "z", "9.0.0", P.arxiv_yarat(d)[0])
        self.assertEqual(x.exception.kod, 400)
        with self.assertRaises(H.HubXətası):
            self.hub.giriş("aysel", "yanlış-parol")
        # pis arxiv: `..` yolu
        b = io.BytesIO()
        with gzip.GzipFile(fileobj=b, mode="wb") as gz, \
                tarfile.open(fileobj=gz, mode="w") as t:
            m = b'[paket]\nad = "pis"\nversiya = "1.0.0"\n'
            for ad, data in (("paket/layihe.alq", m), ("paket/../x", b"x")):
                ti = tarfile.TarInfo(ad)
                ti.size = len(data)
                t.addfile(ti, io.BytesIO(data))
        with self.assertRaises(H.HubXətası):
            self.hub.yayımla("aysel", "pis", "1.0.0", b.getvalue())
        with self.assertRaises(P.PMXətası):
            P.arxiv_aç(b.getvalue(), self.q / "açıq")

    def test_http_api_və_veb(self):
        with urllib.request.urlopen(self.url + "/api/paket/a") as c:
            m = json.loads(c.read())
        self.assertEqual(m["son"], "2.0.0")
        self.assertEqual(m["sahiblər"], ["aysel"])
        u = self.url + "/api/paket/%40%C5%9Firk%C9%99t/analitika"
        with urllib.request.urlopen(u) as c:
            self.assertEqual(json.loads(c.read())["son"], "0.3.0")
        with urllib.request.urlopen(self.url + "/?q=analit") as c:
            h = c.read().decode()
        self.assertIn("@şirkət/analitika", h)
        with urllib.request.urlopen(self.url + "/paket/b") as c:
            h = c.read().decode()
        self.assertIn("<h1>b", h)
        self.assertIn("Sınaq paketi.", h)                      # README
        self.assertIn("alqorpm əlavə b", h)
        r = urllib.request.Request(self.url + "/api/paket/a/3.0.0",
                                   data=b"x", method="PUT")
        try:
            urllib.request.urlopen(r)
            self.fail("nişansız yayım qəbul edildi")
        except urllib.error.HTTPError as x:
            self.assertEqual(x.code, 401)

    def test_tam_ssenari_cli(self):
        k = self.layihə("tətbiq", {}, "gətir b\ngətir \"@şirkət/analitika\" "
                                      "kimi an\nyaz(b.versiyaMətni(), an.versiyaMətni())\n")
        mühit = {**os.environ, "ALQORHUB": self.url,
                 "PYTHONIOENCODING": "utf-8", "ALQOR_RENG": "heçvaxt"}

        def pm(*a, kod=0):
            r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "pm",
                                *a], cwd=k, capture_output=True, text=True,
                               encoding="utf-8", env=mühit, timeout=120)
            self.assertEqual(r.returncode, kod, r.stdout + r.stderr)
            return r.stdout
        pm("əlavə", "b", "@şirkət/analitika@^0.3")
        m = (k / "layihe.alq").read_text(encoding="utf-8")
        self.assertIn('b = "^1.0.0"', m)
        self.assertIn('"@şirkət/analitika" = "^0.3"', m)
        kilid = P.kilid_oxu(k)
        self.assertEqual({a: s.versiya for a, s in kilid.items()},
                         {"a": "1.1.0", "b": "1.0.0",
                          "@şirkət/analitika": "0.3.0"})
        r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "işlət",
                            "mənbə/əsas.alq"], cwd=k, capture_output=True,
                           text=True, encoding="utf-8", env=mühit)
        self.assertEqual(r.stdout, "b 1.0.0 @şirkət/analitika 0.3.0\n",
                         r.stderr)
        self.assertIn("└── a@1.1.0", pm("ağac"))
        # paketlər/ silinsə də kilidə görə eyni versiyalar qayıdır
        shutil.rmtree(k / "paketlər")
        pm("yüklə")
        self.assertTrue((k / "paketlər" / "a" / "mənbə" / "əsas.alq")
                        .read_text(encoding="utf-8").count("a 1.1.0"))
        # təhlükəsizlik xəbərdarlığı → yoxla 1 qaytarır
        self.hub.xəbərdarlıq_əlavə("admin", {
            "paket": "a", "aralıq": "<1.2", "səviyyə": "yüksək",
            "başlıq": "Sınaq", "düzəlib": "2.0.0"})
        self.assertIn("[yüksək] Sınaq", pm("yoxla", kod=1))
        pm("sil", "b")
        self.assertFalse((k / "paketlər" / "b").exists())
        self.assertNotIn("b =", (k / "layihe.alq").read_text(
            encoding="utf-8"))

    def test_yol_asılılığı_və_tip_yoxlaması(self):
        yerli = _paket(self.q / "yerli-paket", "yerli", "0.5.0", {},
                       "funksiya topla(a: tam, b: tam) -> tam\n"
                       "    qaytar a + b\nson\n")
        k = self.layihə("t2", {"yerli": {"yol": os.path.relpath(
            yerli, self.q / "x")}},
            "gətir yerli\nyaz(yerli.topla(2, 3))\n")
        # yol layihə qovluğuna nisbətəndir
        P.manifest_qoy(k, "asılılıqlar", "yerli",
                       {"yol": os.path.relpath(yerli, k)})
        mühit = {**os.environ, "ALQORHUB": self.url,
                 "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "pm",
                            "yüklə"], cwd=k, capture_output=True, text=True,
                           encoding="utf-8", env=mühit)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(P.kilid_oxu(k)["yerli"].mənbə.startswith("yol:"))
        r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "işlət",
                            "mənbə/əsas.alq"], cwd=k, capture_output=True,
                           text=True, encoding="utf-8", env=mühit)
        self.assertEqual(r.stdout, "5\n", r.stderr)
        (k / "mənbə" / "əsas.alq").write_text(
            'gətir yerli\nyaz(yerli.topla("x", 3))\n', encoding="utf-8")
        r = subprocess.run([sys.executable, str(KÖK / "alqorc.py"), "yoxla",
                            "mənbə/əsas.alq"], cwd=k, capture_output=True,
                           text=True, encoding="utf-8", env=mühit)
        self.assertIn("ALQ-T004", r.stdout + r.stderr)
        self.assertEqual(paket_tap("yerli", k / "mənbə"),
                         k / "paketlər" / "yerli" / "mənbə" / "əsas.alq")


class ManifestSınağı(unittest.TestCase):
    def test_redaktə_formatı_qoruyur(self):
        with tempfile.TemporaryDirectory() as q:
            p = Path(q, "layihe.alq")
            p.write_text('# şərh\n[paket]\nad = "x"\n\n[asılılıqlar]\n'
                         'veb = "2.1"   # qalır\n\n[sınaq]\nqovluq = "s"\n',
                         encoding="utf-8")
            P.manifest_qoy(Path(q), "asılılıqlar", "json", "^1.0")
            P.manifest_qoy(Path(q), "asılılıqlar", "@a/b", {"yol": "../b"})
            P.manifest_qoy(Path(q), "inkişaf_asılılıqları", "t", "1")
            m = p.read_text(encoding="utf-8")
            self.assertIn('veb = "2.1"   # qalır\njson = "^1.0"\n'
                          '"@a/b" = { yol = "../b" }\n\n[sınaq]', m)
            self.assertTrue(m.startswith("# şərh\n"))
            P.manifest_qoy(Path(q), "asılılıqlar", "@a/b", None)
            self.assertNotIn("@a/b", p.read_text(encoding="utf-8"))
            from alqor.layihe import oxu
            self.assertEqual(oxu(p.read_text(encoding="utf-8"))
                             ["inkişaf_asılılıqları"], {"t": "1"})


if __name__ == "__main__":
    unittest.main()
