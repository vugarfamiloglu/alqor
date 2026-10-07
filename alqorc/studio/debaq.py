"""
Alqor Studio — debaq sessiyası.

Proqram `alqorc.py dap` (Debaq Adapter Protokolu) ilə ayrıca prosesdə
işləyir; Studio serveri DAP MÜŞTƏRİSİDİR. Hadisələr adi icradakı kimi
`İş.hadisələr` siyahısına yığılır və brauzer onları eyni SSE axını
(`/api/islet/axin`) ilə oxuyur:

    çıxış / xəta     proqramın çıxışı
    dayandı          səbəb, çağırış yığını, dəyişənlər (sahələr)
    davam            proqram yenidən işləyir
    bitdi            proses bitdi (kod)
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any

from . import ALQORC
from .icra import İş

AÇILMA_HƏDDİ = 200                   # bir sahədə göstərilən dəyişən sayı


class DebaqXətası(Exception):
    pass


class DebaqSessiyası(İş):
    def __init__(self, fayl: Path, kök: Path,
                 nöqtələr: dict[str, list[int]], ad: str = ""):
        self.kök = kök
        self._seq = 0
        self._yazma = threading.Lock()
        self._cavablar: dict[int, dict] = {}
        self._cavab_şərti = threading.Condition()
        self.dayanıb = False
        self.proqram_kodu: int | None = None
        əmr = [sys.executable, "-u", str(ALQORC), "dap"]
        super().__init__(əmr, fayl.parent, ad or fayl.name)
        threading.Thread(target=self._başlat, args=(fayl, nöqtələr),
                         daemon=True, name="studio-debaq").start()

    # ── DAP nəqliyyatı ────────────────────────────────────────────────

    def _oxu(self, axın, növ: str) -> None:
        if növ != "çıxış":                   # stderr — adi kimi
            return super()._oxu(axın, növ)
        try:
            while True:
                uzunluq = None
                while True:
                    s = axın.readline()
                    if not s:
                        return
                    s = s.strip()
                    if not s:
                        break
                    if s.lower().startswith(b"content-length"):
                        uzunluq = int(s.split(b":", 1)[1])
                if uzunluq is None:
                    continue
                gövdə = b""
                while len(gövdə) < uzunluq:
                    p = axın.read(uzunluq - len(gövdə))
                    if not p:
                        return
                    gövdə += p
                self._mesaj(json.loads(gövdə.decode("utf-8")))
        except (OSError, ValueError):
            pass

    def _göndər(self, əmr: str, arq: dict | None = None) -> int:
        with self._yazma:
            self._seq += 1
            n = self._seq
            b = json.dumps({"seq": n, "type": "request", "command": əmr,
                            "arguments": arq or {}},
                           ensure_ascii=False).encode("utf-8")
            try:
                self.proses.stdin.write(
                    b"Content-Length: %d\r\n\r\n" % len(b) + b)
                self.proses.stdin.flush()
            except (OSError, ValueError, AttributeError):
                raise DebaqXətası("debaq prosesi işləmir") from None
        return n

    def sorğu(self, əmr: str, arq: dict | None = None,
              müddət: float = 10.0) -> Any:
        n = self._göndər(əmr, arq)
        with self._cavab_şərti:
            if not self._cavab_şərti.wait_for(
                    lambda: n in self._cavablar or self.bitdi, müddət):
                raise DebaqXətası(f"`{əmr}` cavabı gəlmədi")
            c = self._cavablar.pop(n, None)
        if c is None:
            raise DebaqXətası("debaq prosesi bitdi")
        if not c.get("success"):
            raise DebaqXətası(c.get("message") or f"`{əmr}` alınmadı")
        return c.get("body") or {}

    def _mesaj(self, m: dict) -> None:
        if m.get("type") == "response":
            with self._cavab_şərti:
                self._cavablar[m.get("request_seq")] = m
                self._cavab_şərti.notify_all()
            return
        if m.get("type") != "event":
            return
        ad, g = m.get("event"), m.get("body") or {}
        if ad == "output":
            self._əlavə("xəta" if g.get("category") == "stderr"
                        else "çıxış", g.get("output", ""))
        elif ad == "stopped":
            # Cavab gözləyən sorğular oxuyucu sapda edilə bilməz
            threading.Thread(target=self._dayandı,
                             args=(g.get("reason", ""),),
                             daemon=True).start()
        elif ad == "exited":
            self.proqram_kodu = g.get("exitCode")
        elif ad == "terminated":
            self.dayanıb = False
            self.girişi_bağla()              # DAP prosesi də bitsin

    # ── Başlanğıc ─────────────────────────────────────────────────────

    def _başlat(self, fayl: Path, nöqtələr: dict[str, list[int]]) -> None:
        try:
            self.sorğu("initialize", {"adapterID": "alqor",
                                      "clientID": "alqor-studio"})
            self.sorğu("launch", {"program": str(fayl)})
            for yol, sətirlər in nöqtələr.items():
                self.nöqtələri_qoy(yol, sətirlər)
            self.sorğu("configurationDone")
        except DebaqXətası as x:
            self._əlavə("xəta", f"✖ debaq başlamadı: {x}\n")
            self.dayandır()

    # ── Vəziyyət ──────────────────────────────────────────────────────

    def _nisbi(self, yol: str | None) -> str | None:
        if not yol:
            return None
        try:
            return Path(yol).resolve().relative_to(self.kök).as_posix()
        except (ValueError, OSError):
            return None

    def dəyişənlər(self, ref: int) -> list[dict]:
        v = self.sorğu("variables", {"variablesReference": ref})
        return [{"ad": x["name"], "dəyər": x["value"],
                 "tip": x.get("type", ""), "ref": x["variablesReference"]}
                for x in v.get("variables", [])[:AÇILMA_HƏDDİ]]

    def _dayandı(self, səbəb: str) -> None:
        self.dayanıb = True
        try:
            kadrlar = self.sorğu("stackTrace", {"threadId": 1}).get(
                "stackFrames", [])
            yığın = [{"id": k["id"], "ad": k["name"], "sətir": k["line"],
                      "sütun": k.get("column", 1),
                      "yol": self._nisbi((k.get("source") or {}).get("path"))}
                     for k in kadrlar]
            sahələr = self.sahələr(yığın[0]["id"]) if yığın else []
        except DebaqXətası as x:
            self._əlavə("xəta", f"✖ debaq: {x}\n")
            return
        self._əlavə("dayandı", "", səbəb=səbəb, yığın=yığın,
                    sahələr=sahələr)

    def sahələr(self, kadr: int) -> list[dict]:
        n = []
        for s in self.sorğu("scopes", {"frameId": kadr}).get("scopes", []):
            n.append({"ad": s["name"],
                      "dəyişənlər": self.dəyişənlər(
                          s["variablesReference"])})
        return n

    # ── Əmrlər ────────────────────────────────────────────────────────

    ƏMRLƏR = {"davam": "continue", "növbəti": "next", "daxil": "stepIn",
              "çıx": "stepOut", "fasilə": "pause"}

    def əmr_ver(self, ad: str) -> None:
        dap = self.ƏMRLƏR.get(ad)
        if dap is None:
            raise DebaqXətası(f"naməlum əmr: {ad}")
        if dap != "pause":
            if not self.dayanıb:
                raise DebaqXətası("proqram dayanmayıb")
            self.dayanıb = False
            self._əlavə("davam")
        self.sorğu(dap, {"threadId": 1})

    def nöqtələri_qoy(self, yol: str, sətirlər: list[int]) -> None:
        tam = (self.kök / yol).resolve()
        self.sorğu("setBreakpoints", {
            "source": {"path": str(tam)},
            "breakpoints": [{"line": int(s)} for s in sətirlər]})

    def hesabla(self, ifadə: str, kadr: int | None = None) -> dict:
        if not self.dayanıb:
            raise DebaqXətası("ifadə yalnız proqram dayananda hesablanır")
        arq: dict = {"expression": ifadə, "context": "repl"}
        if kadr is not None:
            arq["frameId"] = kadr
        r = self.sorğu("evaluate", arq)
        return {"dəyər": r.get("result", ""), "tip": r.get("type", ""),
                "ref": r.get("variablesReference", 0)}

    def dayandır(self) -> None:
        if not self.bitdi:
            try:
                self._göndər("terminate")
            except DebaqXətası:
                pass
        super().dayandır()
