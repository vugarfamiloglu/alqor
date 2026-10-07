"""Standart kitabxana: pul, keş, növbə, planlayıcı, validasiya,
lokalizasiya, poçt."""

import socket
import socketserver
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alqor.deyerler import AlqorXəta                         # noqa: E402
from alqor.modullar import (kes, lokalizasiya, planlayici,   # noqa: E402
                            poct, pul, validasiya)
from sinaq.test_modullar import işlət                         # noqa: E402

İ = None        # icraçı lazım olmayan metodlar üçün


def m(obyekt, ad, *a, **k):
    """Kitabxana obyektinin Alqor metodunu çağırır."""
    return type(obyekt).ALQOR_METODLARI[ad](İ, obyekt, *a, **k)


# ═══════════════════════════════════════════════════════════════════════
#  pul
# ═══════════════════════════════════════════════════════════════════════

class PulSınağı(unittest.TestCase):
    def test_dəqiqlik_və_operatorlar(self):
        a = pul.yarat(0.1)
        b = pul.yarat(0.2)
        self.assertEqual(a.alqor_operator("+", b, False), pul.yarat("0.3"))
        c = pul.yarat("19.99")
        self.assertEqual(str(c.alqor_operator("*", 3, False)), "59.97 AZN")
        self.assertEqual(str(c.alqor_operator("*", 3, True)), "59.97 AZN")
        self.assertEqual(str(c.alqor_operator("əks", None, False)),
                         "-19.99 AZN")
        self.assertTrue(c.alqor_operator(">", pul.yarat(10), False))
        self.assertEqual(c.alqor_operator("/", pul.yarat(10), False), 1.999)

    def test_valyuta_qarışmır(self):
        with self.assertRaises(AlqorXəta) as x:
            pul.yarat(1).alqor_operator("+", pul.yarat(1, "USD"), False)
        self.assertEqual(x.exception.tip, "ValyutaXətası")
        with self.assertRaises(AlqorXəta):
            pul.yarat(1).alqor_operator("+", 1, False)
        with self.assertRaises(AlqorXəta):
            pul.yarat(1, "XYZ")

    def test_bölüşdürmə_qəpik_itirmir(self):
        for məbləğ, n in (("100", 3), ("0.05", 3), ("-10", 3), ("1", 7)):
            hissələr = pul.yarat(məbləğ).böl(n)
            self.assertEqual(sum(h.d for h in hissələr),
                             pul.yarat(məbləğ).d)
        self.assertEqual([str(h) for h in pul.yarat(100).böl(3)],
                         ["33.34 AZN", "33.33 AZN", "33.33 AZN"])
        self.assertEqual([str(h) for h in pul.yarat(10).payla([1, 2])],
                         ["3.34 AZN", "6.66 AZN"])

    def test_yuvarlaqlaşdırma(self):
        self.assertEqual(str(pul.yarat("2.345")), "2.35 AZN")
        self.assertEqual(str(pul.yarat("2.345", üsul="bankir")), "2.34 AZN")
        self.assertEqual(str(pul.yarat(5, "JPY").alqor_operator(
            "/", 2, False)), "3 JPY")
        self.assertEqual(str(pul.yarat("1.2345", "KWD")), "1.235 KWD")
        self.assertEqual(str(pul.yarat(1234.56).yuvarlaq(-1)), "1230.00 AZN")
        self.assertEqual(str(pul.yarat(100).faiz(18)), "18.00 AZN")

    def test_format_və_oxu(self):
        p = pul.yarat("1234567.5")
        self.assertEqual(p.formatla(), "1 234 567,50 ₼")
        self.assertEqual(p.formatla("en"), "₼1,234,567.50")
        self.assertEqual(pul.yarat(-3, "USD").formatla("en"), "-$3.00")
        self.assertEqual(str(pul.oxu("1 234,50 ₼")), "1234.50 AZN")
        self.assertEqual(str(pul.oxu("$1,234.50")), "1234.50 USD")
        self.assertEqual(str(pul.oxu("12.5 eur")), "12.50 EUR")
        self.assertEqual(pul.qəpikdən(1999).qəpik(), 1999)
        self.assertEqual(str(pul.yarat(10, "USD").çevir("AZN", "1.7")),
                         "17.00 AZN")

    def test_alqor_kodu_və_tip_yoxlaması(self):
        ç = işlət('gətir pul\n'
                  'dəyişən a: pul = pul.yarat("19.99")\n'
                  'dəyişən b = a * 3 - pul.yarat(5)\n'
                  'yaz(b, b > a, -a, 2 * a)\n'
                  'yaz(pul.cəm([a, a]).formatla())\n')
        self.assertEqual(ç, "54.97 AZN doğru -19.99 AZN 39.98 AZN\n"
                            "39,98 ₼\n")
        from sinaq.test_tipyoxlayici import kodlar as yoxla
        kodlar = [k for k in yoxla(
            "gətir pul\ndəyişən a = pul.yarat(1)\nyaz(a + 1)\n"
            "yaz(a < pul.yarat(2))\ndəyişən c: pul = -a\nyaz(c)\n")
                  if k.startswith("ALQ-T0")]
        self.assertEqual(kodlar, ["ALQ-T008"])


# ═══════════════════════════════════════════════════════════════════════
#  keş
# ═══════════════════════════════════════════════════════════════════════

class _SaxtaRedis(socketserver.ThreadingTCPServer):
    """Sınaq üçün kiçik RESP serveri (GET SET DEL … SCAN)."""
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        self.d: dict[str, tuple[str, float | None]] = {}
        self.kilid = threading.Lock()
        self.parol = "gizli"
        super().__init__(("127.0.0.1", 0), _RedisİşləyicisiI)


class _RedisİşləyicisiI(socketserver.StreamRequestHandler):
    def oxu_əmr(self):
        s = self.rfile.readline()
        if not s:
            return None
        n = int(s[1:])
        h = []
        for _ in range(n):
            u = int(self.rfile.readline()[1:])
            h.append(self.rfile.read(u + 2)[:-2].decode())
        return h

    def yaz(self, x):
        if x is None:
            self.wfile.write(b"$-1\r\n")
        elif isinstance(x, bool):
            self.wfile.write(b"+OK\r\n")
        elif isinstance(x, int):
            self.wfile.write(b":%d\r\n" % x)
        elif isinstance(x, list):
            self.wfile.write(b"*%d\r\n" % len(x))
            for e in x:
                self.yaz(e)
        elif isinstance(x, Exception):
            self.wfile.write(b"-ERR " + str(x).encode() + b"\r\n")
        else:
            b = x.encode()
            self.wfile.write(b"$%d\r\n%s\r\n" % (len(b), b))

    def handle(self):
        s = self.server
        girib = False
        while True:
            h = self.oxu_əmr()
            if h is None:
                return
            ə = h[0].upper()
            with s.kilid:
                indi = time.monotonic()
                for a in [a for a, (_, t) in s.d.items()
                          if t is not None and t <= indi]:
                    del s.d[a]
                if ə == "AUTH":
                    girib = h[-1] == s.parol
                    self.yaz(True if girib else Exception("parol"))
                    continue
                if not girib:
                    self.yaz(Exception("NOAUTH"))
                    continue
                if ə == "SELECT":
                    self.yaz(True)
                elif ə == "GET":
                    self.yaz(s.d.get(h[1], (None,))[0])
                elif ə == "SET":
                    t = indi + int(h[4]) / 1000 if len(h) > 3 else None
                    s.d[h[1]] = (h[2], t)
                    self.yaz(True)
                elif ə == "DEL":
                    self.yaz(sum(1 for a in h[1:] if s.d.pop(a, None)))
                elif ə == "MGET":
                    self.yaz([s.d.get(a, (None,))[0] for a in h[1:]])
                elif ə == "INCRBY":
                    v, t = s.d.get(h[1], ("0", None))
                    s.d[h[1]] = (str(int(v) + int(h[2])), t)
                    self.yaz(int(s.d[h[1]][0]))
                elif ə == "PEXPIRE":
                    s.d[h[1]] = (s.d[h[1]][0], indi + int(h[2]) / 1000)
                    self.yaz(1)
                elif ə == "PTTL":
                    x = s.d.get(h[1])
                    self.yaz(-2 if x is None else -1 if x[1] is None
                             else int((x[1] - indi) * 1000))
                elif ə == "SCAN":
                    ön = h[3][:-1].replace("\\", "")
                    self.yaz(["0", [a for a in s.d if a.startswith(ön)]])
                else:
                    self.yaz(Exception(f"naməlum {ə}"))


class KeşSınağı(unittest.TestCase):
    def test_yaddaş_lru_və_müddət(self):
        k = kes.YaddaşKeşi(maks=2)
        k.qoy("a", 1)
        k.qoy("b", 2)
        k.al("a")
        k.qoy("c", 3)
        self.assertEqual(k.açarlar(), ["a", "c"])
        k.qoy("q", 1, 0.05)
        self.assertTrue(k.var("q"))
        time.sleep(0.08)
        self.assertFalse(k.var("q"))
        self.assertEqual(k.artır("say"), 1)
        self.assertEqual(k.artır("say", 4), 5)
        k.qoy("m", "x")
        with self.assertRaises(AlqorXəta):
            k.artır("m")
        with self.assertRaises(AlqorXəta):
            k.qoy(["siyahı"], 1)

    def test_fayl_keşi(self):
        with tempfile.TemporaryDirectory() as q:
            k = kes.FaylKeşi(q, müddət=100)
            k.qoy("ə:1", {"ad": "Aysel", "s": [1, 2]})
            k2 = kes.FaylKeşi(q)                    # yeni nümunə — diskdən
            self.assertEqual(k2.al("ə:1"), {"ad": "Aysel", "s": [1, 2]})
            self.assertGreater(k2.qalanMüddət("ə:1"), 90)
            self.assertEqual(k2.açarlar(), ["ə:1"])
            self.assertEqual(k2.artır("n", 2), 2)
            with self.assertRaises(AlqorXəta):
                k.qoy("x", object())
            k.qoy("q", 1, 0.05)
            time.sleep(0.08)
            self.assertIsNone(k.al("q"))
            k.təmizlə()
            self.assertEqual(k.ölçü(), 0)

    def test_redis_keşi(self):
        s = _SaxtaRedis()
        threading.Thread(target=s.serve_forever, daemon=True).start()
        try:
            ünvan = f"redis://:gizli@127.0.0.1:{s.server_address[1]}/2"
            k = kes.RedisKeşi(ünvan, ön="t:")
            k.qoy("a", {"x": [1, "ə"]})
            self.assertEqual(k.al("a"), {"x": [1, "ə"]})
            self.assertIn("t:a", s.d)
            k.qoy("b", 5, 10)
            self.assertGreater(k.qalanMüddət("b"), 9)
            self.assertIsNone(k.qalanMüddət("a"))
            self.assertEqual(k.artır("say", 3), 3)
            self.assertEqual(k.alÇox(["a", "yox", "b"]),
                             {"a": {"x": [1, "ə"]}, "b": 5})
            self.assertEqual(k.açarlar(), ["a", "b", "say"])
            s.d["başqa"] = ("1", None)
            k.təmizlə()
            self.assertEqual(list(s.d), ["başqa"])     # ön xaricindəki qalır
            # yanlış parol
            with self.assertRaises(AlqorXəta):
                kes.RedisKeşi(ünvan.replace("gizli", "pis")).al("a")
            k.bağla()
        finally:
            s.shutdown()
            s.server_close()

    def test_redis_qoşulmur(self):
        with socket.socket() as so:
            so.bind(("127.0.0.1", 0))
            port = so.getsockname()[1]
        with self.assertRaises(AlqorXəta) as x:
            kes.RedisKeşi(f"redis://127.0.0.1:{port}", vaxtLimiti=1).al("a")
        self.assertEqual(x.exception.tip, "ŞəbəkəXətası")

    def test_alqor_kodu(self):
        ç = işlət(
            "gətir keş\n"
            "dəyişən n = 0\n"
            "funksiya ağır(x: tam) -> tam\n    n += 1\n    qaytar x * x\nson\n"
            "dəyişən s = keş.bük(ağır, müddət: 10)\n"
            "yaz(s(3), s(3), s(4), n)\n"
            "dəyişən k = keş.yaddaş()\n"
            'yaz(k.hesabla("a", () => 42), k.hesabla("a", () => 0))\n'
            "yaz(k.statistika())\n")
        self.assertEqual(ç, "9 9 16 2\n42 42\n"
                            '{"isabət": 1, "qaçırma": 1, "nisbət": 0.5, '
                            '"ölçü": 1}\n')


# ═══════════════════════════════════════════════════════════════════════
#  növbə
# ═══════════════════════════════════════════════════════════════════════

class NövbəSınağı(unittest.TestCase):
    def test_alqor_kodu(self):
        ç = işlət(
            "gətir növbə\n"
            "dəyişən n = növbə.yarat(işçilər: 3, cəhd: 3, gecikmə: 0.01)\n"
            "funksiya kvadrat(x: tam) -> tam\n    qaytar x * x\nson\n"
            "dəyişən sayğac = 0\n"
            "funksiya kövrək() -> mətn\n    sayğac += 1\n"
            '    əgər sayğac < 3 onda\n        at "hələ yox"\n    son\n'
            '    qaytar "alındı"\nson\n'
            'funksiya pis()\n    at "pis"\nson\n'
            "yaz(n.göndər(kvadrat, 7).nəticə())\n"
            "dəyişən b = n.göndər(kövrək)\n"
            "yaz(b.nəticə(), b.cəhdlər())\n"
            "yaz(n.çevir(kvadrat, [1, 2, 3, 4]))\n"
            "dəyişən c = n.planla(kvadrat, arqumentlər: [5], gecikmə: 5)\n"
            "yaz(c.ləğvEt(), c.vəziyyət())\n"
            "dəyişən d = n.planla(pis, cəhd: 1)\n"
            "n.gözlə()\n"
            "yaz(d.vəziyyət(), d.xəta())\n"
            "yaz(n.say())\n"
            "n.dayandır()\n")
        self.assertEqual(ç.splitlines(), [
            "49", "alındı 3", "[1, 4, 9, 16]", "doğru ləğv",
            "uğursuz Xəta: pis",
            '{"gözləyir": 0, "işləyir": 0, "bitdi": 6, "uğursuz": 1, '
            '"ləğv": 1}'])

    def test_prioritet_və_paralellik(self):
        ç = işlət(
            "gətir növbə\ngətir vaxt\n"
            "dəyişən sıra = []\n"
            "dəyişən n = növbə.yarat(işçilər: 1)\n"
            "funksiya qeyd(x: tam)\n    sıra.əlavə(x)\nson\n"
            "n.planla(qeyd, arqumentlər: [0], gecikmə: 0.1)\n"
            "hər i üçün [1, 2, 3] içində\n"
            "    n.planla(qeyd, arqumentlər: [i], prioritet: i, "
            "gecikmə: 0.05)\nson\n"
            "n.gözlə()\nyaz(sıra)\n"
            "dəyişən p = növbə.yarat(işçilər: 4)\n"
            "dəyişən t = vaxt.ölç()\n"
            "p.çevir((x) => vaxt.gözlə(200), [1, 2, 3, 4])\n"
            "yaz(vaxt.ölç() - t < 0.6)\n")
        self.assertEqual(ç, "[3, 2, 1, 0]\ndoğru\n")


# ═══════════════════════════════════════════════════════════════════════
#  planlayıcı
# ═══════════════════════════════════════════════════════════════════════

class PlanlayıcıSınağı(unittest.TestCase):
    def növbəti(self, ifadə, başla):
        return planlayici.Cron(ifadə).növbəti(
            datetime.fromisoformat(başla)).isoformat()

    def test_cron_növbəti(self):
        self.assertEqual(self.növbəti("*/15 9-18 * * b.e-c",
                                      "2026-10-09T18:40:00"),
                         "2026-10-09T18:45:00")
        self.assertEqual(self.növbəti("*/15 9-18 * * b.e-c",
                                      "2026-10-09T18:45:00"),
                         "2026-10-12T09:00:00")       # cümə → bazar ertəsi
        self.assertEqual(self.növbəti("0 0 29 2 *", "2026-03-01T00:00:00"),
                         "2028-02-29T00:00:00")
        self.assertEqual(self.növbəti("@aylıq", "2026-12-31T12:00:00"),
                         "2027-01-01T00:00:00")
        # gün VƏ həftə günü → "və ya"
        self.assertEqual(self.növbəti("30 8 15 * b", "2026-10-02T00:00:00"),
                         "2026-10-04T08:30:00")
        self.assertEqual(self.növbəti("0 12 * yan,iyl mon",
                                      "2026-10-07T00:00:00"),
                         "2027-01-04T12:00:00")
        self.assertEqual(self.növbəti("5 4 * * 7", "2026-10-07T00:00:00"),
                         "2026-10-11T04:05:00")

    def test_cron_xətaları(self):
        for ifadə in ("61 * * * *", "* * *", "*/0 * * * *", "5-1 * * * *",
                      "0 0 31 2 *", "x * * * *"):
            with self.assertRaises(AlqorXəta, msg=ifadə):
                planlayici.Cron(ifadə)

    def test_izah(self):
        self.assertEqual(planlayici.Cron("0 9 * yan-mar *").izah(),
                         "saat 09:00-da, yanvar, fevral, mart aylarında")

    def test_saxta_saatla_addım(self):
        saat = [datetime(2026, 10, 7, 8, 59, 30).timestamp()]
        p = planlayici.Planlayıcı(None, saat=lambda: saat[0])
        olanlar = []
        p._icra_et = lambda t: (olanlar.append(t.ad),
                                setattr(t, "işləyir", False))
        p.cron("0 9 * * *", Daxiliş("səhər"), ad="səhər")
        p.hər(60, Daxiliş("dəqiqəlik"), ad="dəqiqəlik")
        p.sonra(10, Daxiliş("bir"), ad="bir")
        self.assertEqual(p.addım(arxada=False), 0)
        saat[0] += 30                                  # 09:00:00
        p.addım(arxada=False)
        self.assertEqual(sorted(olanlar), ["bir", "səhər"])
        saat[0] += 30
        p.addım(arxada=False)
        self.assertEqual(olanlar[-1], "dəqiqəlik")
        saat[0] += 3600 * 5                            # gecikmə: bir dəfə
        olanlar.clear()
        p.addım(arxada=False)
        self.assertEqual(olanlar, ["dəqiqəlik"])
        self.assertEqual(datetime.fromtimestamp(
            p._tapşırıqlar[0].növbəti_vaxt).isoformat(),
            "2026-10-08T09:00:00")

    def test_alqor_kodu(self):
        ç = işlət(
            "gətir planlayıcı\n"
            "dəyişən p = planlayıcı.yarat()\n"
            "dəyişən say = 0\n"
            "p.hər(0.05, () => say += 1)\n"
            'p.sonra(0.02, () => yaz("bir dəfə"))\n'
            "p.işlət(müddət: 0.33)\n"
            "yaz(say >= 3, say <= 7)\n"
            'yaz(planlayıcı.növbəti("@illik", "2026-05-05T00:00:00"))\n'
            'yaz(planlayıcı.yoxla("0 25 * * *"))\n')
        self.assertEqual(ç.splitlines(), [
            "bir dəfə", "doğru doğru", "2027-01-01T00:00:00",
            "cron `0 25 * * *`: `saat` 0–23 arasında olmalıdır (`25`)"])


def Daxiliş(ad):
    from alqor.deyerler import Daxili
    return Daxili(ad, lambda: None)


# ═══════════════════════════════════════════════════════════════════════
#  validasiya
# ═══════════════════════════════════════════════════════════════════════

class ValidasiyaSınağı(unittest.TestCase):
    def test_yoxlayıcılar(self):
        v = validasiya
        self.assertTrue(v.ePoçtdur("a.b+c@alqor.az"))
        self.assertFalse(v.ePoçtdur("a@b"))
        self.assertFalse(v.ePoçtdur("a..b@c.az"))
        self.assertEqual(v.telefon_normal("050 123 45 67"), "+994501234567")
        self.assertEqual(v.telefon_normal("(012) 555-12-34"),
                         "+994125551234")
        self.assertEqual(v.telefon_normal("00994 70 1112233"),
                         "+994701112233")
        self.assertIsNone(v.telefon_normal("+994 33 1234567"))   # kod yox
        self.assertEqual(v.telefon_normal("+1 202 555 0143"), "+12025550143")
        self.assertTrue(v.ibandır("AZ21 NABZ 0000 0000 1370 1000 1944"))
        self.assertFalse(v.ibandır("AZ22NABZ00000000137010001944"))
        self.assertTrue(v.kartdır("4111 1111 1111 1111"))
        self.assertFalse(v.kartdır("4111 1111 1111 1112"))
        self.assertTrue(v.findir("5ABC12D"))
        self.assertFalse(v.findir("5ABO12D"))
        self.assertTrue(v.vöendir("1234567891"))
        self.assertFalse(v.vöendir("1234567893"))
        self.assertTrue(v.ipdir("::1") and v.ipdir("10.0.0.1", 4))
        self.assertFalse(v.ipdir("::1", 4))
        self.assertTrue(v.tarixdir("2028-02-29"))
        self.assertFalse(v.tarixdir("2026-02-29"))
        self.assertTrue(v.uuiddir("123e4567-e89b-42d3-a456-426614174000"))

    def test_sxem_alqor_kodu(self):
        ç = işlət(
            "gətir validasiya\ndəyişən v = validasiya\n"
            "dəyişən s = v.sxem({\n"
            '    "ad": v.mətn().kəs().min(2).maks(50),\n'
            '    "yaş": v.tam().aralıq(18, 120),\n'
            '    "epoçt": v.ePoçt(),\n'
            '    "telefon": v.telefon().ixtiyari(),\n'
            '    "rol": v.biri(["admin", "redaktor"]).standart("redaktor"),\n'
            '    "parol": v.mətn().min(8).naxış("[0-9]", "rəqəm lazımdır"),\n'
            '    "təkrar": v.mətn().eyni("parol", "parollar eyni deyil"),\n'
            '    "etiketlər": v.siyahı(v.mətn().maks(5)).maks(3)'
            ".ixtiyari(),\n"
            '    "ünvan": v.lüğət({"şəhər": v.mətn(), '
            '"poçt": v.mətn().naxış(x"^AZ[0-9]{4}$")}),\n'
            "})\n"
            'dəyişən n = s.yoxla({"ad": "  Aysel ", "yaş": "25", '
            '"epoçt": "a@b.az", "telefon": "050 123 45 67", '
            '"parol": "gizli123", "təkrar": "gizli123", '
            '"ünvan": {"şəhər": "Bakı", "poçt": "AZ1000"}, "artıq": 1})\n'
            "yaz(n.etibarlıdır(), n.dəyərlər())\n"
            'dəyişən m = s.yoxla({"ad": "A", "yaş": 10, "epoçt": "yox", '
            '"parol": "abcdefgh", "təkrar": "x", '
            '"etiketlər": ["uzun söz", "a"], "ünvan": {"şəhər": ""}})\n'
            "yaz(m.xətalar())\n"
            "cəhd et\n    s.təsdiqlə({})\ntut x\n    yaz(x.mesaj)\nson\n"
            'yaz(v.tam().ciddi().yoxlaDəyər("5").ilkXəta())\n'
            'yaz(v.məntiq().yoxlaDəyər("on").dəyərlər())\n'
            'yaz(v.mətn().yoxla((x) => x.uzunluq() % 2 == 0, "cüt olmalıdır")'
            '.yoxlaDəyər("abc").ilkXəta())\n')
        self.assertEqual(ç.splitlines(), [
            'doğru {"ad": "Aysel", "yaş": 25, "epoçt": "a@b.az", '
            '"telefon": "+994501234567", "rol": "redaktor", '
            '"parol": "gizli123", "təkrar": "gizli123", '
            '"ünvan": {"şəhər": "Bakı", "poçt": "AZ1000"}}',
            '{"ad": ["ən azı 2 simvol olmalıdır"], '
            '"yaş": ["ən azı 18 olmalıdır"], '
            '"epoçt": ["düzgün e-poçt ünvanı deyil"], '
            '"parol": ["rəqəm lazımdır"], '
            '"təkrar": ["parollar eyni deyil"], '
            '"etiketlər.0": ["ən çox 5 simvol olmalıdır"], '
            '"ünvan.şəhər": ["boş ola bilməz"], '
            '"ünvan.poçt": ["tələb olunur"]}',
            "ad: tələb olunur; yaş: tələb olunur; epoçt: tələb olunur; "
            "parol: tələb olunur; təkrar: tələb olunur; ünvan: tələb olunur",
            "dəyər: tam ədəd olmalıdır",
            "doğru",
            "dəyər: cüt olmalıdır"])

    def test_artıq_sahələr_və_qismən(self):
        ç = işlət(
            "gətir validasiya\ndəyişən v = validasiya\n"
            'dəyişən s = v.sxem({"a": v.tam()}, artıq: "xəta")\n'
            'yaz(s.yoxla({"a": 1, "b": 2}).xətalar())\n'
            'dəyişən q = v.sxem({"a": v.tam(), "b": v.mətn()}).qismən()\n'
            'yaz(q.yoxla({"b": "x"}).dəyərlər())\n')
        self.assertEqual(ç, '{"b": ["gözlənilməyən sahə"]}\n{"b": "x"}\n')


# ═══════════════════════════════════════════════════════════════════════
#  lokalizasiya
# ═══════════════════════════════════════════════════════════════════════

class LokalizasiyaSınağı(unittest.TestCase):
    def test_cəm_kateqoriyaları(self):
        k = lokalizasiya.cəm_kateqoriyası
        self.assertEqual([k("ru", n) for n in (1, 3, 5, 11, 21, 22, 112)],
                         ["bir", "az", "çox", "çox", "bir", "az", "çox"])
        self.assertEqual([k("az", n) for n in (0, 1, 2)],
                         ["digər", "bir", "digər"])
        self.assertEqual(k("ar", 2), "iki")

    def test_format(self):
        L = lokalizasiya
        self.assertEqual(L.ədəd(1234567.891), "1 234 567,891")
        self.assertEqual(L.ədəd(1234), "1234")
        self.assertEqual(L.ədəd(-1234567, "en"), "-1,234,567")
        self.assertEqual(L.ədəd(1234.5, "tr", 2), "1.234,50")
        self.assertEqual(L.tarix("2026-10-07", "az", "tam"),
                         "2026, 7 oktyabr, çərşənbə")
        self.assertEqual(L.tarix("2026-10-07T14:05:00", "en", saat=True),
                         "October 7, 2026, 2:05 PM")
        self.assertEqual(L.tarix("2026-10-07", "ru"), "7 октября 2026 г.")
        self.assertEqual(L.nisbi_vaxt(-90), "1 dəqiqə əvvəl")
        self.assertEqual(L.nisbi_vaxt(7200, "ru"), "через 2 часа")
        self.assertEqual(L.nisbi_vaxt(-5 * 86400, "ru"), "5 дней назад")
        self.assertEqual(L.nisbi_vaxt(-3 * 86400, "en"), "3 days ago")
        self.assertEqual(L.nisbi_vaxt(3, "az"), "indicə")
        self.assertEqual(L.siyahı_mətni(["a", "b", "c"], "en"),
                         "a, b, and c")
        self.assertEqual(L.faiz(0.185, rəqəm=1), "18,5 %")

    def test_tərcümə_faylları(self):
        with tempfile.TemporaryDirectory() as q:
            Path(q, "az.json").write_text(
                '{"salam": "Salam, {ad}!", "menyu": {"fayl": "Fayl"}, '
                '"mesaj": {"bir": "{say} mesaj", "digər": "{say} mesaj"}}',
                encoding="utf-8")
            Path(q, "ru.toml").write_text(
                'salam = "Привет, {ad}!"\n[mesaj]\nbir = "{say} сообщение"\n'
                'az = "{say} сообщения"\n"çox" = "{say} сообщений"\n',
                encoding="utf-8")
            Path(q, "en.yaml").write_text(
                "salam: Hello, {ad}!\nqiymət: 'Total: {n:ədəd}'\n",
                encoding="utf-8")
            t = lokalizasiya.yüklə(q, "az")
            self.assertEqual(t.t("salam", {"ad": "Aysel"}), "Salam, Aysel!")
            r = t.dil("ru-RU")
            self.assertEqual([r.t("mesaj", say=n) for n in (1, 3, 11)],
                             ["1 сообщение", "3 сообщения", "11 сообщений"])
            self.assertEqual(r.t("menyu.fayl"), "Fayl")     # standarta düşür
            self.assertEqual(t.dil("en").t("qiymət", n=1234567),
                             "Total: 1,234,567")
            self.assertEqual(t.t("yoxdur"), "yoxdur")
            self.assertEqual(sorted(t.çatışmayan), ["az:yoxdur"])

    def test_alqor_kodu(self):
        ç = işlət(
            "gətir lokalizasiya\n"
            'dəyişən t = lokalizasiya.yarat({"az": {"m": "\\{say} fayl"}, '
            '"en": {"m": {"bir": x"{say} file", "digər": x"{say} files"}}})\n'
            'yaz(t.t("m", say: 2), t.dil("en").t("m", say: 1), '
            't.dil("en").t("m", say: 5))\n')
        self.assertEqual(ç, "2 fayl 1 file 5 files\n")


# ═══════════════════════════════════════════════════════════════════════
#  poçt
# ═══════════════════════════════════════════════════════════════════════

class _SaxtaSMTP(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        self.qutu: list[tuple[str, list[str], bytes]] = []
        super().__init__(("127.0.0.1", 0), _SMTPİşləyicisi)


class _SMTPİşləyicisi(socketserver.StreamRequestHandler):
    def c(self, s):
        self.wfile.write(s.encode() + b"\r\n")

    def handle(self):
        import base64
        self.c("220 saxta ESMTP")
        kimdən, kimə, girib = "", [], False
        while True:
            s = self.rfile.readline()
            if not s:
                return
            s = s.decode("utf-8").rstrip("\r\n")
            ə = s.split(" ")[0].upper()
            if ə == "EHLO":
                self.c("250-saxta")
                self.c("250-AUTH PLAIN")
                self.c("250 SMTPUTF8")
            elif ə == "AUTH":
                x = base64.b64decode(s.split(" ")[2]).split(b"\0")
                girib = x[1:] == [b"bot@alqor.az", b"gizli"]
                self.c("235 ok" if girib else "535 yox")
            elif ə == "MAIL":
                if not girib:
                    self.c("530 auth lazım")
                    continue
                kimdən = s.split(":", 1)[1].split()[0].strip("<>")
                self.c("250 ok")
            elif ə == "RCPT":
                ü = s.split(":", 1)[1].strip().strip("<>")
                if ü.startswith("redd"):
                    self.c("550 yoxdur")
                else:
                    kimə.append(ü)
                    self.c("250 ok")
            elif ə == "DATA":
                self.c("354 davam")
                məlumat = b""
                while True:
                    x = self.rfile.readline()
                    if x == b".\r\n":
                        break
                    məlumat += x
                self.server.qutu.append((kimdən, kimə, məlumat))
                kimə = []
                self.c("250 qəbul")
            elif ə == "NOOP" or ə == "RSET":
                self.c("250 ok")
            elif ə == "QUIT":
                self.c("221 sağ ol")
                return
            else:
                self.c("502 ?")


class PoçtSınağı(unittest.TestCase):
    def məktub(self, **k):
        return poct.Məktub(**{
            "kimdən": "Alqor Bot <bot@alqor.az>",
            "kimə": ["Aysel <aysel@nümunə.az>", "b@c.az"],
            "mövzu": "Hesabat — oktyabr", "mətn": "Salam! Əlavəyə baxın.",
            "html": "<p>Salam!</p>", **k})

    def test_məktub_qurulması(self):
        m = self.məktub(gizliKopya="gizli@c.az", cavabla="cavab@c.az")
        m.əlavə_et({"ad": "qeyd.json", "məzmun": "{}"})
        d = poct.oxu(m.mesaj().as_bytes())
        self.assertEqual(d["mövzu"], "Hesabat — oktyabr")
        self.assertEqual(d["kimə"], ["aysel@nümunə.az", "b@c.az"])
        self.assertEqual(d["mətn"].strip(), "Salam! Əlavəyə baxın.")
        self.assertEqual(d["html"].strip(), "<p>Salam!</p>")
        self.assertEqual(d["əlavələr"][0]["ad"], "qeyd.json")
        self.assertEqual(d["əlavələr"][0]["növ"], "application/json")
        self.assertNotIn("Bcc", d["başlıqlar"])              # gizli qalır
        self.assertIn("gizli@c.az", m.alıcılar())

    def test_başlıq_inyeksiyası_və_ünvanlar(self):
        with self.assertRaises(AlqorXəta):
            self.məktub(mövzu="a\r\nBcc: hücum@pis.az")
        with self.assertRaises(AlqorXəta):
            self.məktub(kimə="a@b.az\nBcc: x@y.az")
        with self.assertRaises(AlqorXəta):
            self.məktub(kimə="ünvan-deyil")
        with self.assertRaises(AlqorXəta):
            poct.Məktub(kimə="a@b.az").mesaj()                # kimdən yox

    def test_smtp_ilə_göndərmə(self):
        s = _SaxtaSMTP()
        threading.Thread(target=s.serve_forever, daemon=True).start()
        port = s.server_address[1]
        try:
            g = poct.SMTP("127.0.0.1", port, "bot@alqor.az", "gizli",
                          şifrələmə="yox")
            m = self.məktub(kopya="redd@c.az")
            n = g.göndər(m)
            self.assertIn("redd@c.az", n["rəddEdilənlər"])
            g.göndər(self.məktub(mövzu="ikinci"))         # eyni bağlantı
            g.bağla()
            self.assertEqual(len(s.qutu), 2)
            kimdən, kimə, məlumat = s.qutu[0]
            self.assertEqual(kimdən, "bot@alqor.az")
            self.assertEqual(kimə, ["aysel@nümunə.az", "b@c.az"])
            self.assertEqual(poct.oxu(məlumat)["mövzu"], "Hesabat — oktyabr")
            with self.assertRaises(AlqorXəta) as x:
                poct.göndər(m, {"host": "127.0.0.1", "port": port,
                                "şifrələmə": "yox",
                                "istifadəçi": "bot@alqor.az",
                                "parol": "pis"})
            self.assertIn("parol", x.exception.mesaj)
        finally:
            s.shutdown()
            s.server_close()

    def test_alqor_kodu(self):
        with tempfile.TemporaryDirectory() as q:
            Path(q, "hesabat.txt").write_text("hesabat", encoding="utf-8")
            ç = işlət(
                "gətir poçt\n"
                'dəyişən m = poçt.məktub(kimdən: "bot@alqor.az", '
                'kimə: "a@b.az", mövzu: "Salam", mətn: "Mətn", '
                'əlavələr: ["hesabat.txt"])\n'
                "dəyişən t = poçt.sınaq()\nt.göndər(m)\n"
                "dəyişən g = t.göndərilənlər()[0]\n"
                'yaz(g["mövzu"], g["alıcılar"], '
                'g["əlavələr"].çevir((e) => e["ad"]))\n'
                'yaz(poçt.ünvanDüzgündür("a@b"))\n', qovluq=q)
        self.assertEqual(ç, 'Salam ["a@b.az"] ["hesabat.txt"]\nyanlış\n')


if __name__ == "__main__":
    unittest.main()
