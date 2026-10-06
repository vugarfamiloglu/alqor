"""
Alqor Studio — proqramı ayrıca prosesdə işlətmək.

Redaktordakı fayl `alqorc.py işlət` ilə AYRICA Python prosesində
işləyir: sonsuz dövr və ya çökmə Studio-nu dayandırmır, "Dayandır"
düyməsi isə prosesi (və onun uşaqlarını) öldürür.

Çıxış hadisələr siyahısına yığılır; brauzer onu Server-Sent Events
(`/api/islet/axin`) ilə oxuyur. Hər hadisənin nömrəsi var, ona görə
qoşulma qırılıb bərpa olunanda heç nə itmir və təkrarlanmır.
"""

from __future__ import annotations
import codecs
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import ALQORC

MAKS_HADİSƏ = 20000
MAKS_İŞ = 20                     # yaddaşda saxlanılan bitmiş işlər


def mühit() -> dict[str, str]:
    """Uşaq prosesin mühiti: UTF-8, buferləşməsiz, rəngsiz."""
    m = dict(os.environ)
    m["PYTHONIOENCODING"] = "utf-8"
    m["PYTHONUTF8"] = "1"
    m["PYTHONUNBUFFERED"] = "1"
    m["ALQOR_RENG"] = "0"
    m["NO_COLOR"] = "1"
    return m


class İş:
    """İşləyən (və ya bitmiş) bir proqram."""

    def __init__(self, əmr: list[str], iş_qovluğu: Path, ad: str = ""):
        self.id = secrets.token_hex(6)
        self.ad = ad
        self.əmr = əmr
        self.hadisələr: list[dict] = []
        self.şərt = threading.Condition()
        self.bitdi = False
        self.kod: int | None = None
        self.başlanğıc = time.monotonic()
        self._kəsildi = False
        əlavə: dict = {}
        if sys.platform == "win32":
            əlavə["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            əlavə["start_new_session"] = True
        self.proses = subprocess.Popen(
            əmr, cwd=str(iş_qovluğu), env=mühit(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0, **əlavə)
        self._əlavə("başladı", " ".join(əmr[2:]))
        self._saplar = [
            threading.Thread(target=self._oxu,
                             args=(self.proses.stdout, "çıxış"),
                             daemon=True, name="studio-stdout"),
            threading.Thread(target=self._oxu,
                             args=(self.proses.stderr, "xəta"),
                             daemon=True, name="studio-stderr"),
        ]
        for s in self._saplar:
            s.start()
        threading.Thread(target=self._gözlə, daemon=True,
                         name="studio-gözlə").start()

    # ── Daxili ────────────────────────────────────────────────────────

    def _əlavə(self, növ: str, mətn: str = "", **əlavə) -> None:
        with self.şərt:
            if len(self.hadisələr) >= MAKS_HADİSƏ and növ in ("çıxış",
                                                              "xəta"):
                if not self._kəsildi:
                    self._kəsildi = True
                    self.hadisələr.append({
                        "n": len(self.hadisələr), "növ": "xəta",
                        "mətn": "\n⚠ çıxış çox uzundur — qalanı "
                                "göstərilmir\n"})
                self.şərt.notify_all()
                return
            self.hadisələr.append({"n": len(self.hadisələr), "növ": növ,
                                   "mətn": mətn, **əlavə})
            self.şərt.notify_all()

    def _oxu(self, axın, növ: str) -> None:
        dekoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while True:
                # bufsize=0 → xam axın: `read` mövcud olanı dərhal verir
                parça = axın.read(4096)
                if not parça:
                    break
                mətn = dekoder.decode(parça)
                if mətn:
                    self._əlavə(növ, mətn)
        except (OSError, ValueError):
            pass
        son = dekoder.decode(b"", final=True)
        if son:
            self._əlavə(növ, son)

    def _gözlə(self) -> None:
        kod = self.proses.wait()
        for s in self._saplar:
            s.join(timeout=5)
        self.kod = kod
        müddət = time.monotonic() - self.başlanğıc
        self._əlavə("bitdi", "", kod=kod, müddət=round(müddət, 3))
        with self.şərt:
            self.bitdi = True
            self.şərt.notify_all()

    # ── İctimai ───────────────────────────────────────────────────────

    def hadisələri_al(self, n: int, müddət: float = 15.0
                      ) -> tuple[list[dict], bool]:
        """`n`-ci hadisədən başlayaraq yeniləri — yoxdursa gözləyir."""
        with self.şərt:
            if n >= len(self.hadisələr) and not self.bitdi:
                self.şərt.wait(müddət)
            return self.hadisələr[n:], self.bitdi

    def giriş(self, mətn: str) -> bool:
        """Proqramın standart girişinə bir sətir yazır."""
        if self.bitdi or self.proses.stdin is None:
            return False
        try:
            self.proses.stdin.write((mətn + "\n").encode("utf-8"))
            self.proses.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def girişi_bağla(self) -> None:
        try:
            if self.proses.stdin:
                self.proses.stdin.close()
        except OSError:
            pass

    def dayandır(self) -> None:
        if self.proses.poll() is not None:
            return
        self._əlavə("xəta", "\n⊣ dayandırıldı\n")
        try:
            if sys.platform == "win32":
                self.proses.terminate()
            else:
                os.killpg(self.proses.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
        try:
            self.proses.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                if sys.platform == "win32":
                    self.proses.kill()
                else:
                    os.killpg(self.proses.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass

    def lüğət(self) -> dict:
        return {"id": self.id, "ad": self.ad, "bitdi": self.bitdi,
                "kod": self.kod, "hadisə": len(self.hadisələr)}


class İcraMeneceri:
    def __init__(self) -> None:
        self.işlər: dict[str, İş] = {}
        self._kilid = threading.Lock()

    def başlat(self, fayl: Path, arqumentlər: list[str] | None = None,
               ad: str = "", tip_yoxla: bool = False) -> İş:
        əmr = [sys.executable, "-u", str(ALQORC), "işlət", str(fayl)]
        if tip_yoxla:
            əmr.append("--tip")
        if arqumentlər:
            əmr += ["--", *[str(a) for a in arqumentlər]]
        iş = İş(əmr, fayl.parent, ad or fayl.name)
        with self._kilid:
            self.işlər[iş.id] = iş
            bitmişlər = [i for i in self.işlər.values() if i.bitdi]
            for köhnə in bitmişlər[:-MAKS_İŞ]:
                self.işlər.pop(köhnə.id, None)
        return iş

    def al(self, id_: str) -> İş | None:
        return self.işlər.get(id_)

    def hamısını_dayandır(self) -> None:
        for iş in list(self.işlər.values()):
            iş.dayandır()
