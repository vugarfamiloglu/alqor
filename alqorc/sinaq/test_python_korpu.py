"""Python kitabxanalarının birbaşa idxalı — `gətir python:...` (§ 8.14)."""

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor import python_korpu as P                # noqa: E402
from alqor.deyerler import AlqorXəta               # noqa: E402
from alqor.icraci import İcraçı                    # noqa: E402
from alqor.lekser import Lekser                    # noqa: E402
from alqor.menbe import Mənbə                      # noqa: E402
from alqor.parser import Parser                    # noqa: E402
from alqor.xeta import XətaToplayıcı               # noqa: E402

KÖK = Path(__file__).parent.parent


def _ağac(kod: str):
    x = XətaToplayıcı()
    s = Mənbə.mətndən(kod, "sınaq.alq", x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise AssertionError("ayırma xətası:\n" + x.hesabat(False))
    return ağac, s


def işlət(kod: str):
    ağac, _ = _ağac(kod)
    sətirlər: list[str] = []
    xəta = None
    try:
        İcraçı(çıxış=sətirlər.append).işlət(ağac)
    except AlqorXəta as e:
        xəta = e
    return sətirlər, xəta


def çıxış(kod: str) -> list[str]:
    sətirlər, xəta = işlət(kod)
    if xəta is not None:
        raise AssertionError(f"gözlənilməyən xəta: {xəta}")
    return sətirlər


def cli(*arq: str, cwd: str | Path, mühit=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(KÖK / "alqorc.py"), *arq],
        capture_output=True, text=True, encoding="utf-8", cwd=str(cwd),
        env={**os.environ, "PYTHONIOENCODING": "utf-8", **(mühit or {})},
        timeout=180)


def təkər_yarat(qovluq: Path, ad: str = "salam_paket",
                versiya: str = "1.0") -> Path:
    """İnternetsiz sınaq üçün əl ilə yığılmış təmiz Python təkəri."""
    info = f"{ad}-{versiya}.dist-info"
    fayllar = {
        f"{ad}/__init__.py":
            "def salamla(ad, nida=False):\n"
            "    return 'Salam, ' + ad + ('!' if nida else '')\n",
        f"{info}/METADATA":
            f"Metadata-Version: 2.1\nName: {ad.replace('_', '-')}\n"
            f"Version: {versiya}\n",
        f"{info}/WHEEL":
            "Wheel-Version: 1.0\nGenerator: sinaq\nRoot-Is-Purelib: true\n"
            "Tag: py3-none-any\n",
    }
    qeyd = []
    for a, m in fayllar.items():
        h = base64.urlsafe_b64encode(
            hashlib.sha256(m.encode()).digest()).rstrip(b"=").decode()
        qeyd.append(f"{a},sha256={h},{len(m.encode())}")
    qeyd.append(f"{info}/RECORD,,")
    qovluq.mkdir(parents=True, exist_ok=True)
    yol = qovluq / f"{ad}-{versiya}-py3-none-any.whl"
    with zipfile.ZipFile(yol, "w") as z:
        for a, m in fayllar.items():
            z.writestr(a, m)
        z.writestr(f"{info}/RECORD", "\n".join(qeyd) + "\n")
    return yol


# ═══════════════════════════════════════════════════════════════════════
#  Sintaksis və alətlər
# ═══════════════════════════════════════════════════════════════════════

class Sintaksis(unittest.TestCase):
    def test_parser_formaları(self):
        ağac, _ = _ağac("gətir python:numpy kimi np\n"
                        "gətir python:os.path\n"
                        "gətir python:math.{sqrt, pi kimi PI}\n"
                        "gətir python:math.*\n"
                        "gətir riyaziyyat\n")
        a, b, c, d, e = ağac.gövdə
        self.assertTrue(a.python)
        self.assertEqual((a.yol, a.ləqəb), (["numpy"], "np"))
        self.assertEqual(b.yol, ["os", "path"])
        self.assertEqual([(x.ad, x.ləqəb) for x in c.elementlər],
                         [("sqrt", None), ("pi", "PI")])
        self.assertTrue(d.hamısı and d.python)
        self.assertFalse(e.python)

    def test_python_adlı_modul_və_dəyişən_toxunulmur(self):
        ağac, _ = _ağac("gətir python\ndəyişən python = 1\n")
        self.assertFalse(ağac.gövdə[0].python)
        self.assertEqual(ağac.gövdə[0].yol, ["python"])

    def test_alqorfmt_prefiksi_bitişik_saxlayır(self):
        from alqor.alqorfmt import formatla
        m = formatla("gətir python : math kimi m\n"
                     "dəyişən l = {python: 1}\n").mətn
        self.assertIn("gətir python:math kimi m", m)
        self.assertIn("{python: 1}", m)

    def test_tip_yoxlayıcı_istənilən_sayır(self):
        from alqor.tipyoxlayici import TipYoxlayıcı
        ağac, s = _ağac("gətir python:json\n"
                        "gətir python:math.{sqrt}\n"
                        "dəyişən x: onluq = sqrt(4)\n"
                        "yaz(json.dumps([1]), x)\n")
        x = XətaToplayıcı()
        TipYoxlayıcı(x).yoxla(ağac)
        self.assertEqual([d.mesaj for d in x.xətalar], [])

    def test_js_hədəfi_aydın_xəta(self):
        from alqor.js.derleyici import KompilyasiyaXətası, kompilyasiya
        ağac, _ = _ağac("gətir python:math\nyaz(math.pi)\n")
        with self.assertRaises(KompilyasiyaXətası) as k:
            kompilyasiya(ağac)
        self.assertIn("Python kitabxanaları JS hədəfində işləmir",
                      str(k.exception))


# ═══════════════════════════════════════════════════════════════════════
#  İcra: standart kitabxana modulları
# ═══════════════════════════════════════════════════════════════════════

class StandartModullar(unittest.TestCase):
    def test_math_seçmə_və_ləqəb(self):
        self.assertEqual(çıxış(
            "gətir python:math.{sqrt, pi kimi PI, factorial}\n"
            "yaz(sqrt(16), factorial(20), PI > 3)\n"),
            ["4.0 2432902008176640000 doğru"])

    def test_bütöv_modul_və_alt_modul(self):
        self.assertEqual(çıxış(
            "gətir python:os.path\ngətir python:math kimi m\n"
            "yaz(path.join(\"a\", \"b\"), m.floor(2.7), tip(m))\n"),
            [f"a{os.sep}b 2 python:modul[math]"])

    def test_hamısı(self):
        self.assertEqual(çıxış("gətir python:math.*\nyaz(gcd(12, 18))\n"),
                         ["6"])

    def test_json_dərin_çevrilmə_və_adlı_arqument(self):
        n = çıxış(
            "gətir python:json\n"
            "dəyişən m = json.dumps({\"a\": [1, 2.5, doğru, boş]}, "
            "sort_keys: doğru)\n"
            "yaz(m)\n"
            "dəyişən v = json.loads(m)\n"
            "yaz(v, tip(v[\"a\"]))\n")
        self.assertEqual(n[0], '{"a": [1, 2.5, true, null]}')
        self.assertEqual(n[1], '{"a": [1, 2.5, doğru, boş]} '
                               'siyahı[istənilən]')

    def test_collections_proksi_metodları(self):
        n = çıxış(
            "gətir python:collections kimi kol\n"
            "dəyişən say = kol.Counter(\"alqoritm\")\n"
            "yaz(say[\"a\"], say.most_common(1), tip(say))\n"
            "dəyişən n = kol.namedtuple(\"Nöqtə\", [\"x\", \"y\"])(3, 4)\n"
            "yaz(n.x + n.y, n[0])\n"
            "dəyişən d = kol.deque([1, 2, 3])\n"
            "d.appendleft(0)\n"
            "yaz(uzunluq(d), 2 içindədir d, d kimi siyahı)\n")
        self.assertEqual(n, ['1 [("a", 1)] python:Counter', "7 3",
                             "4 doğru [0, 1, 2, 3]"])

    def test_datetime(self):
        self.assertEqual(çıxış(
            "gətir python:datetime.{date, timedelta}\n"
            "dəyişən g = date(2024, 2, 28) + timedelta(days: 2)\n"
            "yaz(g.isoformat(), g.year, g > date(2024, 1, 1))\n"
            "yaz(mətnƏt(g), tip(g))\n"),
            ["2024-03-01 2024 doğru", "2024-03-01 python:date"])

    def test_statistics(self):
        self.assertEqual(çıxış(
            "gətir python:statistics kimi st\n"
            "yaz(st.mean([1, 2, 3, 4]), st.median([3, 1, 2]))\n"),
            ["2.5 2"])

    def test_fractions_operatorlar(self):
        self.assertEqual(çıxış(
            "gətir python:fractions.{Fraction}\n"
            "dəyişən k = Fraction(1, 3) + Fraction(1, 6)\n"
            "yaz(k, k == Fraction(1, 2), k < 1, 1 > k, -k, k * 2, 2 * k)\n"
            "yaz(k <=> Fraction(1, 2), k kimi onluq)\n"),
            ["1/2 doğru doğru doğru -1/2 1 1", "0 0.5"])

    def test_dövr_generator_və_dilim(self):
        self.assertEqual(çıxış(
            "gətir python:itertools.{count, islice}\n"
            "gətir python:collections.{OrderedDict}\n"
            "hər x üçün islice(count(10), 3) içində\n"
            "    yaz(x)\n"
            "son\n"
            "dəyişən od = OrderedDict([[\"a\", 1], [\"b\", 2]])\n"
            "hər a, d üçün od içində\n"
            "    yaz(a, d)\n"
            "son\n"),
            ["10", "11", "12", "a 1", "b 2"])

    def test_dilim_alqor_qaydası_ilə(self):
        self.assertEqual(çıxış(
            "gətir python:collections.{UserList}\n"
            "dəyişən u = UserList([0, 1, 2, 3, 4])\n"
            "yaz(u[1..3], u[1..<3], u[2..], u[..-1])\n"),
            ["[1, 2, 3] [1, 2] [2, 3, 4] [0, 1, 2, 3, 4]"])

    def test_indeks_və_üzv_mənimsətmə(self):
        self.assertEqual(çıxış(
            "gətir python:types.{SimpleNamespace}\n"
            "gətir python:collections.{UserDict}\n"
            "dəyişən o = SimpleNamespace(a: 1)\n"
            "o.b = [1, 2]\n"
            "dəyişən u = UserDict()\n"
            "u[\"x\"] = 5\n"
            "yaz(o.a, o.b, u[\"x\"])\n"),
            ["1 [1, 2] 5"])

    def test_siyahı_eyni_obyekt_kimi_ötürülür(self):
        self.assertEqual(çıxış(
            "gətir python:bisect\n"
            "dəyişən s = [1, 3, 5]\n"
            "bisect.insort(s, 4)\n"
            "yaz(s)\n"),
            ["[1, 3, 4, 5]"])

    def test_kontekst_meneceri(self):
        self.assertEqual(çıxış(
            "gətir python:io\n"
            "istifadə b = io.StringIO(\"salam\")\n"
            "    yaz(b.read(), b.closed)\n"
            "son\n"),
            ["salam yanlış"])

    def test_məntiq_çevrilməsi(self):
        self.assertEqual(çıxış(
            "gətir python:collections.{deque}\n"
            "yaz(deque([]) kimi məntiq, məntiqƏt(deque([1])))\n"),
            ["yanlış doğru"])


# ═══════════════════════════════════════════════════════════════════════
#  Geri çağırışlar və xətalar
# ═══════════════════════════════════════════════════════════════════════

class GeriÇağırışlar(unittest.TestCase):
    def test_lambda_və_funksiya_python_a(self):
        self.assertEqual(çıxış(
            "gətir python:builtins.{sorted, map, list}\n"
            "gətir python:functools.{reduce}\n"
            "funksiya kvadrat(x)\n"
            "    qaytar x * x\n"
            "son\n"
            "yaz(sorted([\"alma\", \"ət\", \"bal\"], key: (s) => uzunluq(s),"
            " reverse: doğru))\n"
            "yaz(list(map(kvadrat, [1, 2, 3])))\n"
            "yaz(reduce((a, b) => a + b, [1, 2, 3, 4]))\n"),
            ['["alma", "bal", "ət"]', "[1, 4, 9]", "10"])

    def test_python_funksiyası_alqor_funksiyasına(self):
        self.assertEqual(çıxış(
            "gətir python:math.{sqrt}\n"
            "yaz([4, 9].çevir(sqrt))\n"),
            ["[2.0, 3.0]"])

    def test_alqor_xətası_geri_çağırışdan_keçir(self):
        _, x = işlət(
            "gətir python:builtins.{sorted}\n"
            "sorted([1, 2], key: (a) => 1 / 0)\n")
        self.assertEqual(x.tip, "BölməXətası")


class Xətalar(unittest.TestCase):
    def test_python_istisnası_tutulur(self):
        self.assertEqual(çıxış(
            "gətir python:json\n"
            "cəhd et\n"
            "    json.loads(\"\\{pis\")\n"
            "tut (x: PythonXətası)\n"
            "    yaz(x.pythonTipi, x.kod, x.mesaj.başlayır(\"JSON\"))\n"
            "son\n"
            "cəhd et\n"
            "    json.loads(\"[\")\n"
            "tut (x: Xəta)\n"
            "    yaz(\"ümumi\", x.tip)\n"
            "son\n"),
            ["JSONDecodeError ALQ-M014 doğru", "ümumi PythonXətası"])

    def test_mühafizəli_tutma(self):
        self.assertEqual(çıxış(
            "gətir python:builtins.{int}\n"
            "cəhd et\n"
            "    int(\"x\")\n"
            "tut (x: PythonXətası) əgər x.pythonTipi == \"KeyError\"\n"
            "    yaz(\"açar\")\n"
            "tut (x: PythonXətası) əgər x.pythonTipi == \"ValueError\"\n"
            "    yaz(\"dəyər\")\n"
            "son\n"),
            ["dəyər"])

    def test_istisna_obyekti(self):
        self.assertEqual(çıxış(
            "gətir python:builtins.{int}\n"
            "cəhd et\n"
            "    int(\"x\")\n"
            "tut (x: PythonXətası)\n"
            "    yaz(x.pythonTipi, tip(x.istisna))\n"
            "son\n"),
            ["ValueError python:ValueError"])

    def test_paket_tapılmadı_mesajı(self):
        _, x = işlət("gətir python:yoxdur_paketi_123 kimi y\n")
        self.assertEqual((x.tip, x.kod), ("PythonXətası", "ALQ-M013"))
        self.assertEqual(x.mesaj, "`yoxdur_paketi_123` Python paketi "
                         "tapılmadı — `alqor python qur yoxdur_paketi_123`"
                         " ilə quraşdırın")

    def test_pip_adı_ipucu(self):
        x = P._tapılmadı("yaml", "yaml", None)
        self.assertIn("alqor python qur pyyaml", x.mesaj)

    def test_olmayan_üzv(self):
        _, x = işlət("gətir python:math.{yoxdur}\n")
        self.assertEqual((x.tip, x.kod), ("ArqumentXətası", "ALQ-M002"))
        _, x = işlət("gətir python:math\nmath.yoxdur\n")
        self.assertEqual(x.kod, "ALQ-T006")


# ═══════════════════════════════════════════════════════════════════════
#  Çevrilmə qaydaları (birbaşa)
# ═══════════════════════════════════════════════════════════════════════

class Çevrilmə(unittest.TestCase):
    def test_sadə_və_dərin(self):
        from collections import Counter
        from fractions import Fraction
        self.assertIs(P.pydən(None), None)
        self.assertEqual(P.pydən({"a": (1, [2.0])}), {"a": (1, [2.0])})
        self.assertIsInstance(P.pydən(Fraction(1, 2)), P.PythonObyekti)
        self.assertIsInstance(P.pydən(Counter()), P.PythonObyekti)
        self.assertIsInstance(P.pydən(len), P.PythonFunksiyası)
        self.assertEqual(P.pydən(frozenset({1})), {1})
        v = P.pydən([Fraction(1, 2)])
        self.assertIsInstance(v[0], P.PythonObyekti)
        self.assertEqual(P.pyə(v), [Fraction(1, 2)])

    def test_dəyişməyən_kolleksiya_eyni_obyektdir(self):
        s = [1, "a", (2, 3)]
        self.assertIs(P.pyə(s), s)
        self.assertIs(P.pydən(s), s)

    def test_dövri_kolleksiya(self):
        s: list = [1]
        s.append(s)
        self.assertIs(P.pydən(s), s)

    def test_int_alt_sinfi(self):
        import enum

        class R(enum.IntEnum):
            A = 3
        self.assertEqual(type(P.pydən(R.A)), int)


# ═══════════════════════════════════════════════════════════════════════
#  Yerli paketlər, layihə və CLI
# ═══════════════════════════════════════════════════════════════════════

class YerliPaket(unittest.TestCase):
    def setUp(self):
        self.q = Path(tempfile.mkdtemp(prefix="alqor-py-"))

    def tearDown(self):
        shutil.rmtree(self.q, ignore_errors=True)
        for ad in [m for m in sys.modules if m.startswith("saxta_paket")]:
            del sys.modules[ad]

    def test_mühit_dəyişəni_ilə_saxta_paket(self):
        p = self.q / "yol" / "saxta_paket"
        p.mkdir(parents=True)
        (p / "__init__.py").write_text(
            "class Sayğac:\n"
            "    def __init__(self, b=0):\n        self.n = b\n"
            "    def artır(self, k=1):\n        self.n += k\n"
            "        return self\n"
            "def tətbiq(f, *a, **k):\n    return f(*a, **k)\n",
            encoding="utf-8")
        (p / "alt.py").write_text("X = 42\n", encoding="utf-8")
        köhnə = os.environ.get("ALQOR_PYTHON_YOLU")
        os.environ["ALQOR_PYTHON_YOLU"] = str(self.q / "yol")
        try:
            n = çıxış(
                "gətir python:saxta_paket kimi sp\n"
                "gətir python:saxta_paket.{alt}\n"
                "dəyişən s = sp.Sayğac(b: 5).artır().artır(k: 10)\n"
                "yaz(s.n, alt.X, sp.alt.X)\n"
                "yaz(sp.tətbiq((a, b) => a - b, 10, b: 3))\n")
        finally:
            if köhnə is None:
                os.environ.pop("ALQOR_PYTHON_YOLU", None)
            else:
                os.environ["ALQOR_PYTHON_YOLU"] = köhnə
        self.assertEqual(n, ["16 42 42", "7"])

    def test_layihə_asılılıqları(self):
        from alqor.layihe import Layihə, oxu
        l = Layihə(self.q, oxu('[python]\nasılılıqlar = ["requests>=2", '
                               '"rich"]\n'))
        self.assertEqual(l.python_asılılıqları, ["requests>=2", "rich"])
        l = Layihə(self.q, oxu('[python]\nasılılıqlar = { requests = ">=2",'
                               ' rich = "13.0", x = "*" }\n'))
        self.assertEqual(l.python_asılılıqları,
                         ["requests>=2", "rich==13.0", "x"])
        self.assertEqual(Layihə(self.q, {}).python_asılılıqları, [])

    def test_gitignore_şablonu(self):
        from alqor.layihe import yarat
        yarat(self.q / "l", "l")
        self.assertIn("python_paketlər/",
                      (self.q / "l" / ".gitignore").read_text("utf-8"))

    def test_arqumentlərin_ayrılması(self):
        self.assertEqual(
            P.arqumentləri_ayır(["a", "--no-index", "--find-links", "q",
                                 "b", "--", "-x", "y"]),
            (["a", "b"], ["--no-index", "--find-links", "q", "-x", "y"]))


def _pip_var() -> bool:
    import importlib.util
    return importlib.util.find_spec("pip") is not None


@unittest.skipUnless(_pip_var(), "pip yoxdur")
class PaketƏmrləri(unittest.TestCase):
    """`alqor python qur | siyahı | sil` — yerli təkərlə, internetsiz."""

    @classmethod
    def setUpClass(cls):
        cls.q = Path(tempfile.mkdtemp(prefix="alqor-pip-"))
        təkər_yarat(cls.q / "təkərlər")
        cls.l = cls.q / "layihə"
        cls.l.mkdir()
        (cls.l / "layihe.alq").write_text(
            '[paket]\nad = "pysinaq"\n\n[qurma]\ngiriş = "əsas.alq"\n\n'
            '[python]\nasılılıqlar = ["salam-paket>=1"]\n', encoding="utf-8")
        (cls.l / "əsas.alq").write_text(
            "gətir python:salam_paket.{salamla}\n"
            "yaz(salamla(\"Dünya\", nida: doğru))\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.q, ignore_errors=True)

    def _pip(self, *arq):
        return cli("python", *arq, cwd=self.l)

    def test_qur_işlət_paketlə_sil(self):
        mühit = {"PIP_NO_INDEX": "1", "PIP_CONFIG_FILE": os.devnull}
        r = cli("python", "qur", "--no-index", "--find-links",
                str(self.q / "təkərlər"), cwd=self.l, mühit=mühit)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.l / "python_paketlər" / "salam_paket").is_dir())

        r = self._pip("siyahı")
        self.assertIn("salam-paket==1.0", r.stdout)

        r = cli("işlət", "əsas.alq", cwd=self.l)
        self.assertEqual(r.stdout.strip(), "Salam, Dünya!", r.stderr)

        # `alqor qur` paketi python_paketlər/-i daxil edir
        r = cli("qur", cwd=self.l)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        pyz = self.l / "qurma" / "pysinaq.pyz"
        with zipfile.ZipFile(pyz) as z:
            self.assertIn("layihə/python_paketlər/salam_paket/__init__.py",
                          z.namelist())
        r = subprocess.run([sys.executable, str(pyz)], capture_output=True,
                           text=True, encoding="utf-8", cwd=str(self.q),
                           env={**os.environ, "PYTHONIOENCODING": "utf-8",
                                "ALQOR_KES": str(self.q / "keş")},
                           timeout=120)
        self.assertEqual(r.stdout.strip(), "Salam, Dünya!", r.stderr)

        r = self._pip("sil", "salam_paket")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("silindi: salam-paket", r.stdout)
        self.assertFalse(
            (self.l / "python_paketlər" / "salam_paket").exists())
        self.assertIn("boşdur", self._pip("siyahı").stdout)

        r = cli("işlət", "əsas.alq", cwd=self.l)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("alqor python qur salam_paket", r.stderr + r.stdout)

    def test_layihəsiz_xəta(self):
        r = cli("python", "siyahı", cwd=self.q)
        self.assertEqual(r.returncode, 3)
        self.assertIn("layihe.alq", r.stderr)

    def test_naməlum_alt_əmr(self):
        r = self._pip("uç")
        self.assertEqual(r.returncode, 3)


if __name__ == "__main__":
    unittest.main()
