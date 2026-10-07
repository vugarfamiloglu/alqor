"""`alqor dap` — Debaq Adapter Protokolu."""

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

KÖK = Path(__file__).parent.parent

PROQRAM = """funksiya kvadrat(n: tam) -> tam
    dəyişən k = n * n
    qaytar k
son

dəyişən cəm = 0
dəyişən siyahı = [1, 2, 3]
hər x üçün siyahı içində
    cəm += kvadrat(x)
son
yaz("cəm: {cəm}")
"""


class Müştəri:
    def __init__(self):
        mühit = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.p = subprocess.Popen(
            [sys.executable, str(KÖK / "alqorc.py"), "dap"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=mühit)
        self.seq = 0
        self.q: queue.Queue = queue.Queue()
        self.hadisələr: list[dict] = []
        threading.Thread(target=self._oxu, daemon=True).start()

    def _oxu(self):
        o = self.p.stdout
        while True:
            uzunluq = None
            while True:
                s = o.readline()
                if not s:
                    return
                s = s.strip()
                if not s:
                    break
                if s.lower().startswith(b"content-length"):
                    uzunluq = int(s.split(b":")[1])
            self.q.put(json.loads(o.read(uzunluq).decode("utf-8")))

    def göndər(self, əmr, arq=None) -> int:
        self.seq += 1
        b = json.dumps({"seq": self.seq, "type": "request", "command": əmr,
                        "arguments": arq or {}}).encode("utf-8")
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(b) + b)
        self.p.stdin.flush()
        return self.seq

    def gözlə(self, şərt, vaxt=15):
        while True:
            m = self.q.get(timeout=vaxt)
            if m.get("type") == "event":
                self.hadisələr.append(m)
            if şərt(m):
                return m

    def sorğu(self, əmr, arq=None):
        n = self.göndər(əmr, arq)
        c = self.gözlə(lambda m: m.get("type") == "response"
                       and m.get("request_seq") == n)
        if not c["success"]:
            raise AssertionError(c.get("message"))
        return c.get("body")

    def hadisə(self, ad):
        return self.gözlə(lambda m: m.get("type") == "event"
                          and m.get("event") == ad)

    def bağla(self):
        try:
            self.göndər("disconnect")
        except OSError:
            pass
        try:
            self.p.wait(5)
        except subprocess.TimeoutExpired:
            self.p.kill()
        for a in (self.p.stdin, self.p.stdout, self.p.stderr):
            a.close()


class DAPSınağı(unittest.TestCase):
    def setUp(self):
        self._q = tempfile.TemporaryDirectory()
        self.fayl = Path(self._q.name) / "proqram.alqor"
        self.fayl.write_text(PROQRAM, encoding="utf-8")
        self.m = Müştəri()
        self.addCleanup(self._q.cleanup)
        self.addCleanup(self.m.bağla)

    def başlat(self, nöqtələr, **launch):
        m = self.m
        imk = m.sorğu("initialize", {"adapterID": "alqor"})
        self.assertTrue(imk["supportsConfigurationDoneRequest"])
        m.hadisə("initialized")
        m.sorğu("launch", {"program": str(self.fayl), **launch})
        r = m.sorğu("setBreakpoints", {
            "source": {"path": str(self.fayl)},
            "breakpoints": nöqtələr})
        self.assertTrue(all(b["verified"] for b in r["breakpoints"]))
        m.sorğu("configurationDone")

    def dəyişənlər(self, kadr_id, sahə="Yerli"):
        sahələr = self.m.sorğu("scopes", {"frameId": kadr_id})["scopes"]
        ref = next(s["variablesReference"] for s in sahələr
                   if s["name"] == sahə)
        return {v["name"]: v for v in self.m.sorğu(
            "variables", {"variablesReference": ref})["variables"]}

    def test_dayanma_yığın_dəyişənlər_addım(self):
        self.başlat([{"line": 3}])
        m = self.m
        s = m.hadisə("stopped")
        self.assertEqual(s["body"]["reason"], "breakpoint")
        kadrlar = m.sorğu("stackTrace", {"threadId": 1})["stackFrames"]
        self.assertEqual([k["name"] for k in kadrlar], ["kvadrat", "<əsas>"])
        self.assertEqual(kadrlar[0]["line"], 3)
        self.assertEqual(kadrlar[1]["line"], 9)
        yerli = self.dəyişənlər(kadrlar[0]["id"])
        self.assertEqual(yerli["n"]["value"], "1")
        self.assertEqual(yerli["k"]["value"], "1")
        self.assertEqual(yerli["k"]["type"], "tam")
        qlobal = self.dəyişənlər(kadrlar[0]["id"], "Qlobal")
        self.assertIn("siyahı", qlobal)
        self.assertNotIn("yaz", qlobal)             # daxili adlar yox
        # siyahı açılır
        ref = qlobal["siyahı"]["variablesReference"]
        self.assertGreater(ref, 0)
        el = m.sorğu("variables", {"variablesReference": ref})["variables"]
        self.assertEqual([v["value"] for v in el], ["1", "2", "3"])
        # ifadə hesablama
        r = m.sorğu("evaluate", {"expression": "k + n * 10",
                                 "frameId": kadrlar[0]["id"]})
        self.assertEqual(r["result"], "11")
        # dövrdə yenə dayanır (ikinci iterasiya)
        m.sorğu("continue", {"threadId": 1})
        m.hadisə("stopped")
        kadrlar = m.sorğu("stackTrace", {"threadId": 1})["stackFrames"]
        self.assertEqual(self.dəyişənlər(kadrlar[0]["id"])["n"]["value"],
                         "2")
        # stepOut → çağıran sətirə qayıdır
        m.sorğu("stepOut", {"threadId": 1})
        self.assertEqual(m.hadisə("stopped")["body"]["reason"], "step")
        kadrlar = m.sorğu("stackTrace", {"threadId": 1})["stackFrames"]
        self.assertEqual([k["name"] for k in kadrlar], ["<əsas>"])
        # nöqtələri sil, sona qədər işlət
        m.sorğu("setBreakpoints", {"source": {"path": str(self.fayl)},
                                   "breakpoints": []})
        m.sorğu("continue", {"threadId": 1})
        ç = m.hadisə("exited")
        self.assertEqual(ç["body"]["exitCode"], 0)
        çıxış = "".join(h["body"]["output"] for h in m.hadisələr
                        if h["event"] == "output")
        self.assertIn("cəm: 14", çıxış)

    def test_girişdə_dayanma_və_next(self):
        self.başlat([], stopOnEntry=True)
        m = self.m
        self.assertEqual(m.hadisə("stopped")["body"]["reason"], "entry")
        sətirlər = []
        for _ in range(4):
            kadr = m.sorğu("stackTrace", {"threadId": 1})["stackFrames"][0]
            sətirlər.append(kadr["line"])
            m.sorğu("next", {"threadId": 1})
            m.hadisə("stopped")
        # next funksiyaya girmir: 6 → 7 → 8 → 9
        self.assertEqual(sətirlər, [6, 7, 8, 9])
        m.sorğu("stepIn", {"threadId": 1})
        m.hadisə("stopped")
        kadr = m.sorğu("stackTrace", {"threadId": 1})["stackFrames"][0]
        self.assertEqual((kadr["name"], kadr["line"]), ("kvadrat", 2))

    def test_şərtli_dayanma(self):
        self.başlat([{"line": 2, "condition": "n == 3"}])
        self.m.hadisə("stopped")
        kadr = self.m.sorğu("stackTrace", {"threadId": 1})["stackFrames"][0]
        self.assertEqual(self.dəyişənlər(kadr["id"])["n"]["value"], "3")

    def test_icra_xətası_çıxışa_düşür(self):
        self.fayl.write_text('dəyişən s = [1]\nyaz(s[5])\n', encoding="utf-8")
        self.başlat([])
        ç = self.m.hadisə("exited")
        self.assertEqual(ç["body"]["exitCode"], 1)
        xəta = [h for h in self.m.hadisələr if h["event"] == "output"
                and h["body"]["category"] == "stderr"]
        self.assertTrue(xəta)
        self.assertIn("proqram.alqor:2", xəta[0]["body"]["output"])


if __name__ == "__main__":
    unittest.main()
