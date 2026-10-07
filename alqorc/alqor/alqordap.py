"""
Alqor — Debaq Adapter Protokolu (DAP) serveri.

    alqor dap            # redaktor özü işə salır (stdin/stdout)

Spesifikasiya § 13.8. Asılılıqsızdır. Proqram ayrıca sapda işləyir;
interpretator hər cümlədən əvvəl `İzləyici.cümlə` qarmağını çağırır,
izləyici də dayanma nöqtəsində / addımda sapı dayandırıb redaktorun
əmrini (`continue`, `next`, `stepIn`, `stepOut`) gözləyir.

Dəstəklənir: dayanma nöqtələri (şərtli də: `x > 3`), addım-addım icra,
fasilə, çağırış yığını, dəyişənlər (yerli / qlobal, siyahı, lüğət, sinif
nümunəsi açılır), ifadə hesablama (izləmə, hover, konsol), proqram
çıxışı `output` hadisəsi kimi.
"""

from __future__ import annotations

import json
import sys
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from . import aac as A
from .deyerler import (AlqorXəta, DayanmaSiqnalı, Funksiya, Mühit, Nümunə,
                       mətnə, tip_adı)

VERSİYA = "0.1.0"
SAP_ID = 1


# ═══════════════════════════════════════════════════════════════════════
#  İzləyici — interpretatorun qarmaqları
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Kadr:
    ad: str
    funksiya: Any                    # Funksiya | None (üst səviyyə)
    mühit: Mühit                     # funksiyanın yerli mühiti
    cari_mühit: Mühit | None = None  # hazırkı blokun mühiti
    cümlə: Any = None                # hazırkı cümlə
    id: int = 0


@dataclass
class _Addım:
    növ: str                         # "next" | "in" | "out"
    dərinlik: int
    cümlə: Any


class Dayandırıldı(BaseException):
    """`disconnect` / `terminate` — proqram sapını sonlandırır."""


class İzləyici:
    def __init__(self, server: "DAPServer", qlobal: Mühit):
        self.server = server
        self.kadrlar: list[Kadr] = [Kadr("<əsas>", None, qlobal, id=1)]
        self._növbəti_id = 2
        self.sap = threading.get_ident()
        self.nöqtələr: dict[str, dict[int, str | None]] = {}  # fayl → sətir → şərt
        self.addım: _Addım | None = None
        self.fasilə = False
        self.son_dayanma: Any = None
        self.son_sətir: tuple[str, int] | None = None
        self.dayan_girişdə = False
        self._şərt = threading.Condition()
        self._davam = False
        self.dayandırılıb = False

    # ── Qarmaqlar (proqram sapında) ───────────────────────────────────

    def daxil(self, f: Funksiya, m: Mühit) -> None:
        if threading.get_ident() != self.sap:
            return
        self.kadrlar.append(Kadr(f.ad or "<lambda>", f, m,
                                 id=self._növbəti_id))
        self._növbəti_id += 1

    def çıx(self, f: Funksiya) -> None:
        if threading.get_ident() != self.sap:
            return
        if len(self.kadrlar) > 1 and self.kadrlar[-1].funksiya is f:
            self.kadrlar.pop()

    def cümlə(self, c: Any, m: Mühit) -> None:
        if self.dayandırılıb:
            raise Dayandırıldı()
        if threading.get_ident() != self.sap:
            return
        yer = getattr(c, "yer", None)
        if yer is None or isinstance(c, (A.FunksiyaElanı, A.SinifElanı)):
            return
        k = self.kadrlar[-1]
        k.cari_mühit = m
        k.cümlə = c
        fayl = _fayl(yer)
        sətir = yer.sətir
        əvvəlki = self.son_sətir
        self.son_sətir = (fayl, sətir)
        # Eyni sətirdəki ikinci cümlə (`a; b`) yenidən dayandırmır, amma
        # dövrdə eyni cümlənin təkrarı dayandırır
        yeni_sətir = (fayl, sətir) != əvvəlki or c is self.son_dayanma

        səbəb = None
        if self.dayan_girişdə:
            self.dayan_girişdə = False
            səbəb = "entry"
        elif self.fasilə:
            self.fasilə = False
            səbəb = "pause"
        elif self.addım is not None and yeni_sətir:
            a = self.addım
            d = len(self.kadrlar)
            if a.növ == "in" or (a.növ == "next" and d <= a.dərinlik) \
                    or (a.növ == "out" and d < a.dərinlik):
                səbəb = "step"
        if səbəb is None and yeni_sətir:
            şərtlər = self.nöqtələr.get(fayl)
            if şərtlər and sətir in şərtlər:
                şərt = şərtlər[sətir]
                if not şərt or self._şərt_doğrudur(şərt, m):
                    səbəb = "breakpoint"
        if səbəb is not None:
            self._dayan(c, səbəb)

    def _şərt_doğrudur(self, şərt: str, m: Mühit) -> bool:
        try:
            return bool(self.server.hesabla(şərt, m))
        except Exception:                               # noqa: BLE001
            return True               # yanlış şərt — dayanıb göstəririk

    def _dayan(self, c: Any, səbəb: str) -> None:
        self.addım = None
        self.son_dayanma = c
        self.server.qeydləri_sıfırla()
        with self._şərt:
            self._davam = False
            self.server.hadisə("stopped", {
                "reason": səbəb, "threadId": SAP_ID,
                "allThreadsStopped": True})
            while not self._davam and not self.dayandırılıb:
                self._şərt.wait(0.2)
        if self.dayandırılıb:
            raise Dayandırıldı()

    # ── Əmrlər (server sapında) ───────────────────────────────────────

    def davam_et(self, addım: str | None = None) -> None:
        if addım is not None:
            self.addım = _Addım(addım, len(self.kadrlar), self.son_dayanma)
        with self._şərt:
            self._davam = True
            self._şərt.notify_all()

    def dayandır(self) -> None:
        self.dayandırılıb = True
        with self._şərt:
            self._şərt.notify_all()


def _fayl(yer: Any) -> str:
    yol = getattr(yer.mənbə, "yol", None)
    if yol is None:
        return getattr(yer.mənbə, "ad", "")
    try:
        return str(Path(yol).resolve())
    except OSError:
        return str(yol)


# ═══════════════════════════════════════════════════════════════════════
#  Server
# ═══════════════════════════════════════════════════════════════════════

class DAPServer:
    def __init__(self, giriş: BinaryIO, çıxış: BinaryIO):
        self.giriş = giriş
        self.çıxış = çıxış
        self._yazma = threading.Lock()
        self._seq = 0
        self.işləyir = True
        self.izləyici: İzləyici | None = None
        self.icraçı: Any = None
        self.proqram: dict | None = None      # launch parametrləri
        self.konfiq_hazır = False
        self.sap: threading.Thread | None = None
        self.nöqtələr: dict[str, dict[int, str | None]] = {}
        self.qlobal_əvvəl: dict[str, Any] = {}
        self._qeydlər: dict[int, Any] = {}
        self._qeyd_sayı = 1000
        self.çıxış_kodu: int | None = None

    # ── Nəqliyyat ─────────────────────────────────────────────────────

    def oxu(self) -> dict | None:
        uzunluq = None
        while True:
            sətir = self.giriş.readline()
            if not sətir:
                return None
            sətir = sətir.strip()
            if not sətir:
                break
            ad, _, dəyər = sətir.decode("ascii", "replace").partition(":")
            if ad.strip().lower() == "content-length":
                uzunluq = int(dəyər.strip())
        if uzunluq is None:
            return {}
        try:
            return json.loads(self.giriş.read(uzunluq).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _göndər(self, m: dict) -> None:
        with self._yazma:
            self._seq += 1
            m["seq"] = self._seq
            b = json.dumps(m, ensure_ascii=False).encode("utf-8")
            self.çıxış.write(b"Content-Length: %d\r\n\r\n" % len(b) + b)
            self.çıxış.flush()

    def hadisə(self, ad: str, gövdə: dict | None = None) -> None:
        self._göndər({"type": "event", "event": ad, "body": gövdə or {}})

    def çap(self, mətn: str, kateqoriya: str = "stdout") -> None:
        self.hadisə("output", {"category": kateqoriya, "output": mətn})

    # ── Dövr ──────────────────────────────────────────────────────────

    def işlət(self) -> int:
        while self.işləyir:
            m = self.oxu()
            if m is None:
                break
            if m:
                self.emal(m)
        if self.izləyici is not None:
            self.izləyici.dayandır()
        if self.sap is not None:
            self.sap.join(timeout=2)
        return self.çıxış_kodu or 0

    def emal(self, m: dict) -> None:
        if m.get("type") != "request":
            return
        əmr = m.get("command", "")
        cavab = {"type": "response", "request_seq": m.get("seq", 0),
                 "command": əmr, "success": True}
        işləyici = self.ƏMRLƏR.get(əmr)
        sonra = None
        try:
            if işləyici is None:
                raise ValueError(f"əmr dəstəklənmir: {əmr}")
            nəticə = işləyici(self, m.get("arguments") or {})
            if isinstance(nəticə, tuple):
                nəticə, sonra = nəticə
            if nəticə is not None:
                cavab["body"] = nəticə
        except Exception as x:                          # noqa: BLE001
            cavab["success"] = False
            cavab["message"] = str(x)
            if not isinstance(x, (ValueError, AlqorXəta)):
                print(traceback.format_exc(), file=sys.stderr)
        self._göndər(cavab)
        if sonra is not None:
            sonra()

    # ── Həyat dövrü ───────────────────────────────────────────────────

    def ə_initialize(self, a: dict):
        return ({
            "supportsConfigurationDoneRequest": True,
            "supportsConditionalBreakpoints": True,
            "supportsEvaluateForHovers": True,
            "supportsTerminateRequest": True,
            "supportsSetVariable": False,
            "supportsStepBack": False,
        }, lambda: self.hadisə("initialized"))

    def ə_launch(self, a: dict):
        proqram = a.get("program")
        if not proqram:
            raise ValueError("`program` göstərilməyib (işlədiləcək .alq faylı)")
        p = Path(proqram)
        if not p.is_file():
            raise ValueError(f'"{proqram}" faylı tapılmadı')
        self.proqram = dict(a, program=str(p.resolve()))
        if self.konfiq_hazır:
            return None, self._başlat
        return None

    def ə_configurationDone(self, a: dict):
        self.konfiq_hazır = True
        if self.proqram is not None and self.sap is None:
            return None, self._başlat
        return None

    def ə_disconnect(self, a: dict):
        if self.izləyici is not None:
            self.izləyici.dayandır()
        self.işləyir = False
        return None

    def ə_terminate(self, a: dict):
        if self.izləyici is not None:
            self.izləyici.dayandır()
        return None

    # ── Dayanma nöqtələri ─────────────────────────────────────────────

    def ə_setBreakpoints(self, a: dict):
        yol = (a.get("source") or {}).get("path") or ""
        try:
            açar = str(Path(yol).resolve())
        except OSError:
            açar = yol
        nöqtələr = a.get("breakpoints")
        if nöqtələr is None:
            nöqtələr = [{"line": x} for x in a.get("lines") or []]
        sətirlər: dict[int, str | None] = {}
        cavab = []
        for i, n in enumerate(nöqtələr):
            sətirlər[n["line"]] = n.get("condition") or None
            cavab.append({"id": i + 1, "verified": True, "line": n["line"]})
        self.nöqtələr[açar] = sətirlər
        if self.izləyici is not None:
            self.izləyici.nöqtələr = dict(self.nöqtələr)
        return {"breakpoints": cavab}

    def ə_setExceptionBreakpoints(self, a: dict):
        return {"breakpoints": []}

    # ── İcra idarəsi ──────────────────────────────────────────────────

    def ə_threads(self, a: dict):
        return {"threads": [{"id": SAP_ID, "name": "əsas"}]}

    def _izləyici(self) -> İzləyici:
        if self.izləyici is None:
            raise ValueError("proqram işləmir")
        return self.izləyici

    def ə_continue(self, a: dict):
        self._izləyici().davam_et()
        return {"allThreadsContinued": True}

    def ə_next(self, a: dict):
        self._izləyici().davam_et("next")

    def ə_stepIn(self, a: dict):
        self._izləyici().davam_et("in")

    def ə_stepOut(self, a: dict):
        self._izləyici().davam_et("out")

    def ə_pause(self, a: dict):
        self._izləyici().fasilə = True

    # ── Yığın, dəyişənlər ─────────────────────────────────────────────

    def ə_stackTrace(self, a: dict):
        iz = self._izləyici()
        kadrlar = []
        for k in reversed(iz.kadrlar):
            yer = getattr(k.cümlə, "yer", None)
            kadr = {"id": k.id, "name": k.ad, "line": 0, "column": 0}
            if yer is not None:
                sətir, sütun = yer.mənbə.sətir_sütun(yer.başlanğıc)
                kadr["line"], kadr["column"] = sətir, sütun
                yol = getattr(yer.mənbə, "yol", None)
                kadr["source"] = {"name": getattr(yer.mənbə, "ad", ""),
                                  "path": str(yol) if yol else None}
            kadrlar.append(kadr)
        başla = a.get("startFrame", 0)
        say = a.get("levels") or len(kadrlar)
        return {"stackFrames": kadrlar[başla:başla + say],
                "totalFrames": len(kadrlar)}

    def _kadr(self, id_: int | None) -> Kadr:
        iz = self._izləyici()
        for k in iz.kadrlar:
            if k.id == id_:
                return k
        return iz.kadrlar[-1]

    def ə_scopes(self, a: dict):
        k = self._kadr(a.get("frameId"))
        sahələr = []
        if k.funksiya is not None:
            sahələr.append({"name": "Yerli", "presentationHint": "locals",
                            "variablesReference": self._qeyd(
                                ("yerli", k)), "expensive": False})
        sahələr.append({"name": "Qlobal",
                        "variablesReference": self._qeyd(("qlobal", k)),
                        "expensive": False})
        return {"scopes": sahələr}

    def qeydləri_sıfırla(self) -> None:
        self._qeydlər.clear()

    def _qeyd(self, obyekt: Any) -> int:
        self._qeyd_sayı += 1
        self._qeydlər[self._qeyd_sayı] = obyekt
        return self._qeyd_sayı

    def _yerli_adlar(self, k: Kadr) -> dict[str, Any]:
        adlar: dict[str, Any] = {}
        m = k.cari_mühit or k.mühit
        dayan = k.funksiya.mühit if k.funksiya is not None else None
        while m is not None and m is not dayan:
            for ad, d in m.adlar.items():
                if ad not in adlar and not ad.startswith("__"):
                    adlar[ad] = d
            if m is k.mühit:
                break
            m = m.üst
        return adlar

    def _qlobal_adlar(self) -> dict[str, Any]:
        q = self.icraçı.qlobal
        return {ad: d for ad, d in q.adlar.items()
                if not ad.startswith("__") and (
                    ad not in self.qlobal_əvvəl
                    or self.qlobal_əvvəl[ad] is not d)}

    def ə_variables(self, a: dict):
        obyekt = self._qeydlər.get(a.get("variablesReference"))
        if obyekt is None:
            return {"variables": []}
        if isinstance(obyekt, tuple) and len(obyekt) == 2 and \
                obyekt[0] in ("yerli", "qlobal") and \
                isinstance(obyekt[1], Kadr):
            cüt = (self._yerli_adlar(obyekt[1]) if obyekt[0] == "yerli"
                   else self._qlobal_adlar())
            elementlər = list(cüt.items())
        elif isinstance(obyekt, dict):
            elementlər = [(mətnə(k, self.icraçı), v)
                          for k, v in obyekt.items()]
        elif isinstance(obyekt, (list, tuple)):
            elementlər = [(f"[{i}]", v) for i, v in enumerate(obyekt)]
        elif isinstance(obyekt, (set, frozenset)):
            elementlər = [(f"[{i}]", v) for i, v in enumerate(obyekt)]
        elif isinstance(obyekt, Nümunə):
            elementlər = list(obyekt.sahələr.items())
        else:
            elementlər = []
        return {"variables": [self._dəyişən(ad, d)
                              for ad, d in elementlər[:500]]}

    def _dəyişən(self, ad: str, d: Any) -> dict:
        açılır = isinstance(d, (list, tuple, dict, set, frozenset)) and \
            len(d) > 0 or (isinstance(d, Nümunə) and d.sahələr)
        return {"name": str(ad), "value": self._göstər(d),
                "type": _tip(d),
                "variablesReference": self._qeyd(d) if açılır else 0}

    def _göstər(self, d: Any) -> str:
        try:
            if isinstance(d, str):
                return json.dumps(d, ensure_ascii=False)
            if isinstance(d, Funksiya):
                return f"funksiya {d.ad}"
            m = mətnə(d, self.icraçı)
        except Exception:                               # noqa: BLE001
            m = f"<{_tip(d)}>"
        return m if len(m) <= 300 else m[:297] + "…"

    # ── İfadə hesablama ───────────────────────────────────────────────

    def hesabla(self, ifadə: str, m: Mühit) -> Any:
        from .lekser import Lekser
        from .menbe import Mənbə
        from .parser import Parser
        from .xeta import XətaToplayıcı
        x = XətaToplayıcı()
        s = Mənbə.mətndən(ifadə, "<ifadə>")
        ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        if not x.uğurludur() or len(ağac.gövdə) != 1 or \
                not isinstance(ağac.gövdə[0], A.İfadəCümləsi):
            raise ValueError("ifadə ayrıla bilmədi")
        köhnə = self.icraçı.izləyici
        self.icraçı.izləyici = None          # hesablama dayandırılmasın
        try:
            return self.icraçı._ifadə(ağac.gövdə[0].ifadə, m)
        finally:
            self.icraçı.izləyici = köhnə

    def ə_evaluate(self, a: dict):
        k = self._kadr(a.get("frameId"))
        try:
            d = self.hesabla(a.get("expression", ""),
                             k.cari_mühit or k.mühit)
        except AlqorXəta as x:
            raise ValueError(f"{x.tip}: {x.mesaj}") from None
        return {"result": self._göstər(d), "type": _tip(d),
                "variablesReference": self._dəyişən("", d)[
                    "variablesReference"]}

    # ── Proqramın işə salınması ───────────────────────────────────────

    def _başlat(self) -> None:
        if self.sap is not None:
            return
        self.sap = threading.Thread(target=self._icra, daemon=True,
                                    name="alqor-proqram")
        self.sap.start()

    def _icra(self) -> None:
        from .icraci import İcraçı
        from .lekser import Lekser
        from .menbe import Mənbə
        from .parser import Parser
        from .xeta import XətaToplayıcı

        a = self.proqram or {}
        yol = Path(a["program"])
        kod = 0
        x = XətaToplayıcı()
        s = Mənbə.fayldan(yol, x)
        ağac = None
        if s is not None:
            ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        if s is None or not x.uğurludur():
            for d in x.xətalar:
                yer = f"{d.yer.mənbə.ad}:{d.yer.sətir}: " if d.yer else ""
                self.çap(f"✖ {d.kod} {yer}{d.mesaj}"
                         f"{': ' + d.qeyd if d.qeyd else ''}\n", "stderr")
            self._bitir(2)
            return

        icraçı = İcraçı(çıxış=lambda m: self.çap(m + "\n"),
                        giriş=self._giriş)
        icraçı.əsas_qovluq = yol.parent
        self.icraçı = icraçı
        self.qlobal_əvvəl = dict(icraçı.qlobal.adlar)
        iz = İzləyici(self, icraçı.qlobal)
        iz.nöqtələr = dict(self.nöqtələr)
        iz.dayan_girişdə = bool(a.get("stopOnEntry"))
        self.izləyici = iz
        icraçı.izləyici = iz
        köhnə_stdout = sys.stdout
        sys.stdout = _ÇıxışAxını(self)
        try:
            kod = icraçı.işlət(ağac, [str(x) for x in a.get("args") or []])
        except Dayandırıldı:
            kod = 0
        except DayanmaSiqnalı as d:
            kod = d.kod
        except AlqorXəta as xəta:
            yer = ""
            if xəta.yer is not None:
                yer = f" ({xəta.yer.mənbə.ad}:{xəta.yer.sətir})"
            self.çap(f"✖ {xəta.tip}: {xəta.mesaj}{yer}\n", "stderr")
            kod = 1
        except RecursionError:
            self.çap("✖ StekDaşmaXətası: çağırış dərinliyi həddi aşıldı\n",
                     "stderr")
            kod = 1
        except Exception as xəta:                       # noqa: BLE001
            self.çap(f"✖ daxili xəta: {type(xəta).__name__}: {xəta}\n",
                     "stderr")
            kod = 1
        finally:
            sys.stdout = köhnə_stdout
            icraçı.izləyici = None
        self._bitir(kod if isinstance(kod, int) else 0)

    def _giriş(self, sorğu: str = "") -> str:
        if sorğu:
            self.çap(sorğu)
        self.çap("⚠ debaq rejimində klaviaturadan oxumaq mümkün deyil — "
                 "boş mətn qaytarıldı\n", "console")
        return ""

    def _bitir(self, kod: int) -> None:
        self.çıxış_kodu = kod
        self.hadisə("exited", {"exitCode": kod})
        self.hadisə("terminated")

    ƏMRLƏR = {
        "initialize": ə_initialize,
        "launch": ə_launch,
        "configurationDone": ə_configurationDone,
        "disconnect": ə_disconnect,
        "terminate": ə_terminate,
        "setBreakpoints": ə_setBreakpoints,
        "setExceptionBreakpoints": ə_setExceptionBreakpoints,
        "threads": ə_threads,
        "continue": ə_continue,
        "next": ə_next,
        "stepIn": ə_stepIn,
        "stepOut": ə_stepOut,
        "pause": ə_pause,
        "stackTrace": ə_stackTrace,
        "scopes": ə_scopes,
        "variables": ə_variables,
        "evaluate": ə_evaluate,
    }


def _tip(d: Any) -> str:
    try:
        return tip_adı(d)
    except Exception:                                   # noqa: BLE001
        return type(d).__name__


class _ÇıxışAxını:
    """Proqramın `print`-ləri protokol kanalını pozmasın."""

    def __init__(self, server: DAPServer):
        self.server = server

    def write(self, s: str) -> int:
        if s:
            self.server.çap(s)
        return len(s)

    def flush(self) -> None:
        pass


def işə_sal(giriş: BinaryIO | None = None,
            çıxış: BinaryIO | None = None) -> int:
    giriş = giriş or sys.stdin.buffer
    if çıxış is None:
        çıxış = sys.stdout.buffer
        sys.stdout = sys.stderr
    return DAPServer(giriş, çıxış).işlət()


if __name__ == "__main__":
    sys.exit(işə_sal())
