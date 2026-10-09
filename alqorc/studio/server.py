"""
Alqor Studio — HTTP server, JSON API və pəncərənin açılması.

ARXİTEKTURA
───────────
`pəncərə` modulu ilə eyni model: `127.0.0.1`-də təsadüfi portda
`ThreadingHTTPServer`, interfeys isə Chrome/Edge/Brave `--app=`
pəncərəsində (və ya pywebview-da) açılır. Pəncərəni açan kod
`alqor.pencere._pəncərəni_aç` — təkrar yazılmır.

TƏHLÜKƏSİZLİK
─────────────
  • Server yalnız `127.0.0.1`-ə bağlanır
  • Hər sessiya üçün təsadüfi NİŞAN (token): bütün `/api/*` sorğuları
    `X-Alqor-Token` başlığı (və ya SSE üçün `?t=`) tələb edir — başqa
    yerli veb səhifələr Studio-nu idarə edə bilməsin
  • `Host` başlığı yoxlanır — DNS rebinding hücumuna qarşı
  • POST gövdəsi yalnız `application/json` — sadə formalar işləmir
  • Fayl API-si layihə qovluğu ilə məhdudlaşır (`layihe.py`)
"""

from __future__ import annotations
import hmac
import json
import queue
import secrets
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from . import STATİK, VERSIYA, diaqnostika, klaviatura, sablonlar, skelet
from .icra import İcraMeneceri, mühit
from .layihe import Layihə, YolXətası

MAKS_GÖVDƏ = 16 * 1024 * 1024
ÖNBAXIŞ_GÖZLƏMƏ = 20.0            # önbaxış prosesinin ilk cavabı (san.)
NƏBZ_HƏDDİ = 180.0                 # pəncərədən bu qədər səs yoxdursa bitir

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}

CSP = ("default-src 'self'; script-src 'self'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "frame-src http://127.0.0.1:*; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")


class ApiXətası(Exception):
    def __init__(self, mesaj: str, kod: int = 400):
        super().__init__(mesaj)
        self.kod = kod


# ═══════════════════════════════════════════════════════════════════════
#  Studio — vəziyyət
# ═══════════════════════════════════════════════════════════════════════

class Studio:
    def __init__(self, qovluq: str | Path, port: int = 0,
                 ilk_fayl: str | None = None):
        self.layihə = Layihə(qovluq)
        # Fayl əlaqəsi (`.alq` iki klik): Studio bu faylı açıb başlayır
        self.ilk_fayl = ilk_fayl
        self.nişan = secrets.token_urlsafe(24)
        self.icra = İcraMeneceri()
        self._önbaxış: subprocess.Popen | None = None
        self._önbaxış_kilidi = threading.Lock()
        self.son_nəbz: float | None = None
        self.bağlanma: float | None = None
        self.server = ThreadingHTTPServer(("127.0.0.1", port),
                                          _İdarəedici_yarat(self))
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self._sap: threading.Thread | None = None
        self.marşrutlar = self._marşrutlar()
        self._dil: Any = None

    # ── Ünvanlar ──────────────────────────────────────────────────────

    @property
    def kök_ünvan(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def ünvan(self) -> str:
        """Pəncərənin açdığı ünvan — nişan sorğu sətrindədir."""
        ünvan = f"{self.kök_ünvan}/?t={self.nişan}"
        if self.ilk_fayl:
            ünvan += "&fayl=" + urllib.parse.quote(self.ilk_fayl)
        return ünvan

    def host_icazəlidir(self, host: str | None) -> bool:
        return host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    def nişan_düzdür(self, nişan: str | None) -> bool:
        return bool(nişan) and hmac.compare_digest(
            str(nişan).encode(), self.nişan.encode())

    # ── Həyat dövrü ───────────────────────────────────────────────────

    def fonda_başlat(self) -> "Studio":
        self._sap = threading.Thread(target=self.server.serve_forever,
                                     daemon=True, name="alqor-studio")
        self._sap.start()
        return self

    def dayandır(self) -> None:
        self.icra.hamısını_dayandır()
        self.önbaxışı_dayandır()
        self.server.shutdown()
        self.server.server_close()

    def bitməlidir(self) -> bool:
        """Pəncərə bağlanıbsa (və yenidən qoşulmayıbsa) — doğru."""
        indi = time.monotonic()
        if self.bağlanma is not None and indi - self.bağlanma > 5:
            if self.son_nəbz is None or self.son_nəbz < self.bağlanma:
                return True
        return (self.son_nəbz is not None
                and indi - self.son_nəbz > NƏBZ_HƏDDİ)

    # ── Layihə ayarları ───────────────────────────────────────────────

    def tip_rejimi(self) -> str:
        """`layihe.alq` → `[tip] rejim`."""
        f = self.layihə.kök / "layihe.alq"
        try:
            mətn = f.read_text(encoding="utf-8")
        except OSError:
            return "normal"
        bölmə = ""
        for s in mətn.splitlines():
            s = s.strip()
            if s.startswith("["):
                bölmə = s
            elif bölmə == "[tip]" and s.startswith("rejim"):
                d = s.split("=", 1)[-1].strip().strip("\"'")
                if d in diaqnostika.TİP_REJİMLƏRİ:
                    return d
        return "normal"

    # ── Önbaxış ───────────────────────────────────────────────────────

    def önbaxışı_dayandır(self) -> None:
        with self._önbaxış_kilidi:
            p, self._önbaxış = self._önbaxış, None
        if p is None:
            return
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=2)
        if p.stdin is not None:
            try:
                p.stdin.close()
            except OSError:
                pass

    def önbaxışı_başlat(self, fayl: Path, komponent: str | None) -> dict:
        self.önbaxışı_dayandır()
        əmr = [sys.executable, "-u", str(Path(__file__).parent /
                                         "onbaxis.py"), str(fayl)]
        if komponent:
            əmr.append(komponent)
        p = subprocess.Popen(əmr, cwd=str(fayl.parent), env=mühit(),
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        with self._önbaxış_kilidi:
            self._önbaxış = p
        növbə: queue.Queue[str] = queue.Queue()
        xəta_parçaları: list[bytes] = []

        def stdout_oxu() -> None:
            assert p.stdout is not None
            # Hər sətir bir cavabdır: ilki başlanğıc, sonrakılar `yenilə`
            for sətir in iter(p.stdout.readline, b""):
                növbə.put(sətir.decode("utf-8", "replace"))
            növbə.put("")
            p.stdout.close()           # proses bitdi — boru da bağlanır

        def stderr_oxu() -> None:
            assert p.stderr is not None
            for parça in iter(lambda: p.stderr.read1(4096), b""):
                if len(xəta_parçaları) < 256:
                    xəta_parçaları.append(parça)
            p.stderr.close()

        threading.Thread(target=stdout_oxu, daemon=True).start()
        threading.Thread(target=stderr_oxu, daemon=True).start()
        try:
            sətir = növbə.get(timeout=ÖNBAXIŞ_GÖZLƏMƏ)
        except queue.Empty:
            self.önbaxışı_dayandır()
            return {"xəta": "Önbaxış cavab vermədi — komponentin "
                            "qurulması çox uzun çəkir (sonsuz dövr?)"}
        if not sətir.strip():
            time.sleep(0.1)
            return {"xəta": b"".join(xəta_parçaları).decode(
                "utf-8", "replace").strip() or "önbaxış prosesi bitdi"}
        try:
            n = json.loads(sətir)
        except ValueError:
            return {"xəta": sətir}
        if "ünvan" in n:
            with self._önbaxış_kilidi:
                if self._önbaxış is p:
                    self._önbaxış_məlumatı = {
                        "fayl": fayl, "komponent": n.get("komponent"),
                        "istənən": komponent, "növbə": növbə, "cavab": n}
        return n

    def önbaxışı_yenilə(self, fayl: Path, komponent: str | None) -> dict:
        """
        İşləyən önbaxışa `yenilə` göndərir — proses, server və ünvan
        qalır, yalnız komponent yenidən qurulur. Önbaxış yoxdursa,
        başqa fayla və ya komponentə aiddirsə, təzəsini başladır.
        """
        with self._önbaxış_kilidi:
            p = self._önbaxış
            m = getattr(self, "_önbaxış_məlumatı", None)
        uyğun = (p is not None and p.poll() is None and m is not None
                 and m["fayl"] == fayl and p.stdin is not None
                 and komponent in (None, m["komponent"]))
        if not uyğun:
            return self.önbaxışı_başlat(fayl, komponent)
        növbə: queue.Queue[str] = m["növbə"]
        while not növbə.empty():                 # köhnə cavablar
            növbə.get_nowait()
        try:
            p.stdin.write("yenilə\n".encode())
            p.stdin.flush()
            sətir = növbə.get(timeout=ÖNBAXIŞ_GÖZLƏMƏ)
        except (OSError, queue.Empty):
            return self.önbaxışı_başlat(fayl, komponent)
        if not sətir.strip():
            return self.önbaxışı_başlat(fayl, komponent)
        try:
            n = json.loads(sətir)
        except ValueError:
            return {"xəta": sətir}
        if "xəta" in n:
            return n
        cavab = dict(m["cavab"])
        cavab["komponentlər"] = n.get("komponentlər",
                                      cavab.get("komponentlər"))
        cavab["yeniləndi"] = True
        return cavab

    # ── API marşrutları ───────────────────────────────────────────────

    def _marşrutlar(self) -> dict[tuple[str, str], Callable[[dict], Any]]:
        return {
            ("GET", "/api/melumat"): self.api_məlumat,
            ("GET", "/api/agac"): lambda _: self.layihə.ağac(),
            ("GET", "/api/kataloq"): self.api_kataloq,
            ("GET", "/api/klaviatura"): self.api_klaviatura,
            ("POST", "/api/fayl/oxu"): self.api_oxu,
            ("POST", "/api/fayl/yaz"): self.api_yaz,
            ("POST", "/api/fayl/yarat"): self.api_yarat,
            ("POST", "/api/fayl/adlandir"): self.api_adlandır,
            ("POST", "/api/fayl/sil"): self.api_sil,
            ("POST", "/api/vidjet/elave"): self.api_vidjet_əlavə,
            ("POST", "/api/vidjet/numune"): self.api_vidjet_nümunə,
            ("POST", "/api/vidjet/tamamla"): self.api_vidjet_tamamla,
            ("POST", "/api/vidjet/elementler"): self.api_elementlər,
            ("POST", "/api/vidjet/xususiyyetler"): self.api_xüsusiyyətlər,
            ("POST", "/api/vidjet/xususiyyet"): self.api_xüsusiyyət_qoy,
            ("POST", "/api/yoxla"): self.api_yoxla,
            ("POST", "/api/dil"): self.api_dil,
            ("POST", "/api/axtar"): self.api_axtar,
            ("POST", "/api/axtar/evezle"): self.api_axtar_əvəzlə,
            ("POST", "/api/dizayn/agac"): self.api_dizayn_ağac,
            ("POST", "/api/dizayn/emeliyyat"): self.api_dizayn_əməliyyat,
            ("POST", "/api/debaq"): self.api_debaq,
            ("POST", "/api/debaq/emr"): self.api_debaq_əmr,
            ("POST", "/api/debaq/noqteler"): self.api_debaq_nöqtələr,
            ("POST", "/api/debaq/hesabla"): self.api_debaq_hesabla,
            ("POST", "/api/debaq/deyisenler"): self.api_debaq_dəyişənlər,
            ("POST", "/api/debaq/kadr"): self.api_debaq_kadr,
            ("POST", "/api/ascii-duzelt"): self.api_ascii,
            ("POST", "/api/formatla"): self.api_formatla,
            ("POST", "/api/islet"): self.api_işlət,
            ("POST", "/api/islet/giris"): self.api_giriş,
            ("POST", "/api/islet/dayandir"): self.api_dayandır,
            ("POST", "/api/onbaxis"): self.api_önbaxış,
            ("POST", "/api/onbaxis/dayandir"): lambda _: (
                self.önbaxışı_dayandır() or {"ok": True}),
            ("POST", "/api/sablon"): self.api_şablon,
            ("POST", "/api/nebz"): self.api_nəbz,
            ("POST", "/api/bagla"): self.api_bağla,
        }

    @staticmethod
    def _mətn(s: dict, ad: str, standart: str | None = None) -> str:
        d = s.get(ad, standart)
        if not isinstance(d, str):
            raise ApiXətası(f"`{ad}` sahəsi (mətn) lazımdır")
        return d

    @staticmethod
    def _tam(s: dict, ad: str) -> int | None:
        d = s.get(ad)
        if d is None:
            return None
        if isinstance(d, bool) or not isinstance(d, int):
            raise ApiXətası(f"`{ad}` tam ədəd olmalıdır")
        return d

    def api_məlumat(self, _: dict) -> dict:
        from alqor import VERSIYA as ALQOR_VERSIYA
        return {
            "ad": self.layihə.ad, "kök": str(self.layihə.kök),
            "versiya": VERSIYA, "alqorVersiya": ALQOR_VERSIYA,
            "şablonlar": sablonlar.siyahı(),
            "formatlayıcı": True,
            "tipRejimi": self.tip_rejimi(),
            "platforma": sys.platform,
        }

    def api_kataloq(self, _: dict) -> dict:
        from alqor import vidjet as V
        from . import miniatur
        şəkillər = miniatur.hamısı()
        return {
            "üslub": miniatur.üslub(),
            "kateqoriyalar": list(V.KATEQORİYALAR),
            "kateqoriyaAdları": dict(V.KATEQORİYA_BEYNƏLXALQ),
            "vidjetlər": [{
                "ad": m.ad, "beynəlxalqAd": V.BEYNƏLXALQ_ADLAR[m.ad],
                "kateqoriya": m.kateqoriya, "izah": m.izah,
                "nümunə": skelet._düzəlt(m.nümunə),
                "hadisələr": list(m.hadisələr),
                "skeletVar": bool(m.skelet or m.vəziyyət),
                "miniatür": şəkillər.get(m.ad, ""),
            } for m in V.KATALOQ],
        }

    def api_klaviatura(self, _: dict) -> dict:
        from alqor import acar_sozler as AS
        from alqor.lekser import BLOK_ACANLAR
        c = klaviatura.cədvəl()
        c.update({
            "açarSözlər": sorted(AS.ACAR_SOZLER - set(AS.LITERAL)),
            "literallar": list(AS.LITERAL),
            "tiplər": sorted(AS.TIP_ADLARI),
            "kontekstli": sorted(AS.KONTEKSTLI),
            "blokAçanlar": sorted(BLOK_ACANLAR),
        })
        return c

    # ── Fayllar ───────────────────────────────────────────────────────

    def api_oxu(self, s: dict) -> dict:
        yol = self._mətn(s, "yol")
        return {"yol": yol, "mətn": self.layihə.oxu(yol)}

    def api_yaz(self, s: dict) -> dict:
        self.layihə.yaz(self._mətn(s, "yol"), self._mətn(s, "mətn"))
        return {"ok": True}

    def api_yarat(self, s: dict) -> dict:
        növ = s.get("növ", "fayl")
        if növ not in ("fayl", "qovluq"):
            raise ApiXətası("`növ` fayl və ya qovluq olmalıdır")
        yol = self.layihə.yarat(self._mətn(s, "yol"), növ,
                                self._mətn(s, "mətn", ""))
        return {"yol": yol}

    def api_adlandır(self, s: dict) -> dict:
        return {"yol": self.layihə.adını_dəyiş(self._mətn(s, "yol"),
                                               self._mətn(s, "yeni"))}

    def api_sil(self, s: dict) -> dict:
        self.layihə.sil(self._mətn(s, "yol"))
        return {"ok": True}

    def api_şablon(self, s: dict) -> dict:
        növ = self._mətn(s, "növ")
        ad = self._mətn(s, "ad").strip() or "yeni-layihə"
        if "/" in ad or "\\" in ad:
            raise ApiXətası("layihə adında `/` ola bilməz")
        try:
            fayllar = sablonlar.fayllar(növ, ad)
        except KeyError as x:
            raise ApiXətası(str(x.args[0]))
        qovluq = self.layihə.yol(ad)
        if qovluq.exists():
            raise ApiXətası(f'"{ad}" artıq mövcuddur', 409)
        for nisbi, mətn in fayllar.items():
            self.layihə.yarat(f"{ad}/{nisbi}", "fayl", mətn)
        return {"qovluq": self.layihə.nisbi(qovluq),
                "fayl": f"{self.layihə.nisbi(qovluq)}/əsas.alq"}

    # ── Vidjetlər ─────────────────────────────────────────────────────

    def api_vidjet_əlavə(self, s: dict) -> dict:
        ad = s.get("ad")
        return skelet.vidjet_əlavə_et(
            self._mətn(s, "mətn"), self._mətn(s, "vidjet"),
            self._tam(s, "kursor"),
            ad if isinstance(ad, str) and ad else None).lüğət()

    def api_vidjet_nümunə(self, s: dict) -> dict:
        return {"kod": skelet.nümunə_hazırla(
            self._mətn(s, "mətn"), self._mətn(s, "vidjet"),
            self._tam(s, "kursor"))}

    def api_vidjet_tamamla(self, s: dict) -> dict:
        kursor = self._tam(s, "kursor")
        if kursor is None:
            raise ApiXətası("`kursor` lazımdır")
        return skelet.çağırışı_tamamla(self._mətn(s, "mətn"),
                                       kursor).lüğət()

    def api_elementlər(self, s: dict) -> dict:
        return {"elementlər": skelet.elementlər(self._mətn(s, "mətn"))}

    def api_xüsusiyyətlər(self, s: dict) -> dict:
        from .xususiyyet import XüsusiyyətXətası, oxu
        kursor = self._tam(s, "kursor")
        if kursor is None:
            raise ApiXətası("`kursor` lazımdır")
        try:
            return oxu(self._mətn(s, "mətn"), kursor)
        except XüsusiyyətXətası as x:
            return {"xəta": str(x)}

    def api_xüsusiyyət_qoy(self, s: dict) -> dict:
        from .xususiyyet import XüsusiyyətXətası, qoy
        kursor = self._tam(s, "kursor")
        if kursor is None:
            raise ApiXətası("`kursor` lazımdır")
        dəyər = s.get("dəyər")
        if not (dəyər is None or isinstance(dəyər, (str, int, float, bool))):
            raise ApiXətası("`dəyər` mətn, ədəd, məntiq və ya boş olmalıdır")
        try:
            return qoy(self._mətn(s, "mətn"), kursor, self._mətn(s, "ad"),
                       dəyər)
        except XüsusiyyətXətası as x:
            raise ApiXətası(str(x), 422)

    # ── Dil alətləri ──────────────────────────────────────────────────

    def api_yoxla(self, s: dict) -> dict:
        rejim = s.get("rejim") or self.tip_rejimi()
        return diaqnostika.yoxla(self._mətn(s, "mətn"),
                                 Path(self._mətn(s, "ad",
                                                 "fayl.alq")).name,
                                 rejim if isinstance(rejim, str)
                                 else "normal",
                                 bool(s.get("tip", True)),
                                 self._lint_ayarı() if s.get("lint", True)
                                 else None)

    def _lint_ayarı(self) -> dict:
        from alqor.alqorlint import ayar_oxu
        return ayar_oxu(self.layihə.kök)

    def api_dil(self, s: dict) -> dict:
        """Tamamlama / imza / hover / təyinat — `alqorls` vasitəsilə."""
        from .dilserver import DilKörpüsü
        if self._dil is None:
            self._dil = DilKörpüsü(self.layihə.kök, self.tip_rejimi())
        yol = self.layihə.yol(self._mətn(s, "yol"))
        sətir, sütun = self._tam(s, "sətir"), self._tam(s, "sütun")
        if sətir is None or sütun is None:
            raise ApiXətası("`sətir` və `sütun` lazımdır")
        try:
            yeni_ad = s.get("yeniAd")
            return {"nəticə": self._dil.sorğu(
                self._mətn(s, "metod"), yol, self._mətn(s, "mətn"),
                sətir, sütun,
                yeni_ad if isinstance(yeni_ad, str) else None)}
        except ValueError as x:
            raise ApiXətası(str(x)) from None

    def _axtarış_naxışı(self, s: dict):
        from . import axtaris
        try:
            return axtaris.naxış(self._mətn(s, "sorğu"), bool(s.get("hərf")),
                                 bool(s.get("söz")), bool(s.get("regex")))
        except axtaris.AxtarışXətası as x:
            raise ApiXətası(str(x)) from None

    def _açıqlar(self, s: dict) -> dict[str, str]:
        a = s.get("açıqlar") or {}
        if not isinstance(a, dict):
            raise ApiXətası("`açıqlar` lüğət olmalıdır")
        for yol in a:
            self.layihə.yol(yol)
        return {k: v for k, v in a.items() if isinstance(v, str)}

    def api_axtar(self, s: dict) -> dict:
        from . import axtaris
        return axtaris.axtar(self.layihə, self._axtarış_naxışı(s),
                             self._mətn(s, "filtr", ""), self._açıqlar(s))

    def api_axtar_əvəzlə(self, s: dict) -> dict:
        from . import axtaris
        try:
            return axtaris.əvəzlə(self.layihə, self._axtarış_naxışı(s),
                                  self._mətn(s, "əvəz", ""),
                                  bool(s.get("regex")),
                                  self._mətn(s, "filtr", ""), self._açıqlar(s))
        except axtaris.AxtarışXətası as x:
            raise ApiXətası(str(x)) from None

    def api_ascii(self, s: dict) -> dict:
        mətn, say = diaqnostika.ascii_düzəlt(self._mətn(s, "mətn"))
        return {"mətn": mətn, "say": say}

    def api_formatla(self, s: dict) -> dict:
        from alqor.alqorfmt import FormatXətası, formatla
        try:
            n = formatla(self._mətn(s, "mətn"), "redaktor.alq",
                         homoqlif_düzəlt=True)
        except FormatXətası as x:
            # Sintaksis xətası olan fayl formatlanmır — redaktor olduğu
            # kimi qalır, istifadəçi səbəbi görür
            raise ApiXətası(f"Format edilmədi: {x}", 422)
        return {"mətn": n.mətn, "dəyişdi": n.dəyişdi,
                "ascii": n.ascii_düzəlişləri}

    # ── İcra ──────────────────────────────────────────────────────────

    def api_işlət(self, s: dict) -> dict:
        yol = self.layihə.yol(self._mətn(s, "yol"))
        if not yol.is_file():
            raise ApiXətası("fayl tapılmadı — əvvəlcə saxlayın", 404)
        arq = s.get("arqumentlər") or []
        if not isinstance(arq, list):
            raise ApiXətası("`arqumentlər` siyahı olmalıdır")
        iş = self.icra.başlat(yol, [str(a) for a in arq],
                              self.layihə.nisbi(yol), bool(s.get("tip")))
        return iş.lüğət()

    # ── Vizual dizayner ───────────────────────────────────────────────

    @staticmethod
    def _yol_siyahısı(s: dict, ad: str) -> list[int]:
        d = s.get(ad)
        if not isinstance(d, list) or not all(
                isinstance(x, int) and not isinstance(x, bool) and x >= 0
                for x in d):
            raise ApiXətası(f"`{ad}` tam ədədlər siyahısı olmalıdır")
        return d

    def api_dizayn_ağac(self, s: dict) -> dict:
        from . import dizayner
        try:
            return dizayner.ağac(self._mətn(s, "mətn"), self._tam(s, "kursor"),
                                 s.get("komponent") or None)
        except dizayner.DizaynXətası as x:
            return {"xəta": str(x)}

    def api_dizayn_əməliyyat(self, s: dict) -> dict:
        from . import dizayner as D
        mətn = self._mətn(s, "mətn")
        komp = s.get("komponent") or None
        növ = self._mətn(s, "əməliyyat")
        try:
            if növ == "sil":
                return D.sil(mətn, self._yol_siyahısı(s, "yol"), komp)
            indeks = self._tam(s, "indeks") or 0
            hədəf = self._yol_siyahısı(s, "hədəf")
            if növ == "köçür":
                return D.köçür(mətn, self._yol_siyahısı(s, "yol"), hədəf,
                               indeks, komp)
            if növ == "əlavə":
                return D.əlavə_et(mətn, self._mətn(s, "vidjet"), hədəf,
                                  indeks, komp)
        except skelet.SkeletXətası as x:
            raise ApiXətası(str(x), 422) from None
        raise ApiXətası(f"naməlum əməliyyat: {növ}")

    # ── Debaq ─────────────────────────────────────────────────────────

    def _nöqtələr(self, s: dict) -> dict[str, list[int]]:
        n = s.get("nöqtələr") or {}
        if not isinstance(n, dict):
            raise ApiXətası("`nöqtələr` lüğət olmalıdır")
        nəticə = {}
        for yol, sətirlər in n.items():
            self.layihə.yol(yol)                    # layihədən kənar olmasın
            if not isinstance(sətirlər, list):
                raise ApiXətası("sətirlər siyahı olmalıdır")
            nəticə[yol] = [int(x) for x in sətirlər
                           if isinstance(x, int) and x > 0]
        return nəticə

    def api_debaq(self, s: dict) -> dict:
        from .debaq import DebaqSessiyası
        yol = self.layihə.yol(self._mətn(s, "yol"))
        if not yol.is_file():
            raise ApiXətası("fayl tapılmadı — əvvəlcə saxlayın", 404)
        sessiya = DebaqSessiyası(yol, self.layihə.kök, self._nöqtələr(s),
                                 self.layihə.nisbi(yol))
        self.icra.əlavə_et(sessiya)
        return sessiya.lüğət()

    def _debaq(self, s: dict):
        from .debaq import DebaqSessiyası
        iş = self._iş(s)
        if not isinstance(iş, DebaqSessiyası):
            raise ApiXətası("bu iş debaq sessiyası deyil")
        return iş

    def _debaq_çağır(self, f, *a):
        from .debaq import DebaqXətası
        try:
            return f(*a)
        except DebaqXətası as x:
            raise ApiXətası(str(x), 409) from None

    def api_debaq_əmr(self, s: dict) -> dict:
        d = self._debaq(s)
        self._debaq_çağır(d.əmr_ver, self._mətn(s, "əmr"))
        return {"ok": True}

    def api_debaq_nöqtələr(self, s: dict) -> dict:
        d = self._debaq(s)
        for yol, sətirlər in self._nöqtələr(s).items():
            self._debaq_çağır(d.nöqtələri_qoy, yol, sətirlər)
        return {"ok": True}

    def api_debaq_hesabla(self, s: dict) -> dict:
        d = self._debaq(s)
        return self._debaq_çağır(d.hesabla, self._mətn(s, "ifadə"),
                                 self._tam(s, "kadr"))

    def api_debaq_dəyişənlər(self, s: dict) -> dict:
        d = self._debaq(s)
        ref = self._tam(s, "ref")
        if not ref:
            raise ApiXətası("`ref` lazımdır")
        return {"dəyişənlər": self._debaq_çağır(d.dəyişənlər, ref)}

    def api_debaq_kadr(self, s: dict) -> dict:
        d = self._debaq(s)
        kadr = self._tam(s, "kadr")
        if kadr is None:
            raise ApiXətası("`kadr` lazımdır")
        return {"sahələr": self._debaq_çağır(d.sahələr, kadr)}

    def _iş(self, s: dict):
        iş = self.icra.al(self._mətn(s, "id"))
        if iş is None:
            raise ApiXətası("belə iş yoxdur", 404)
        return iş

    def api_giriş(self, s: dict) -> dict:
        iş = self._iş(s)
        if s.get("bağla"):
            iş.girişi_bağla()
            return {"ok": True}
        return {"ok": iş.giriş(self._mətn(s, "mətn"))}

    def api_dayandır(self, s: dict) -> dict:
        self._iş(s).dayandır()
        return {"ok": True}

    def api_önbaxış(self, s: dict) -> dict:
        yol = self.layihə.yol(self._mətn(s, "yol"))
        if not yol.is_file():
            raise ApiXətası("fayl tapılmadı — əvvəlcə saxlayın", 404)
        k = s.get("komponent")
        k = k if isinstance(k, str) and k else None
        if s.get("canlı"):
            return self.önbaxışı_yenilə(yol, k)
        return self.önbaxışı_başlat(yol, k)

    # ── Pəncərənin həyatı ─────────────────────────────────────────────

    def api_nəbz(self, _: dict) -> dict:
        self.son_nəbz = time.monotonic()
        return {"ok": True}

    def api_bağla(self, _: dict) -> dict:
        self.bağlanma = time.monotonic()
        return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════
#  HTTP idarəedicisi
# ═══════════════════════════════════════════════════════════════════════

def _İdarəedici_yarat(studio: Studio):

    class İdarəedici(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        # HTTP başlıqları latin-1 ilə kodlaşır — ASCII olmalıdır
        server_version = "Alqor-Studio"
        sys_version = ""

        def log_message(self, *a):                  # səssiz
            pass

        # ── Cavablar ──────────────────────────────────────────────────

        def _göndər(self, gövdə: bytes, tip: str, kod: int = 200,
                    başlıqlar: dict[str, str] | None = None) -> None:
            self.send_response(kod)
            self.send_header("Content-Type", tip)
            self.send_header("Content-Length", str(len(gövdə)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            if self.close_connection:
                self.send_header("Connection", "close")
            for a, d in (başlıqlar or {}).items():
                self.send_header(a, d)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(gövdə)

        def _JSON(self, d: Any, kod: int = 200) -> None:
            self._göndər(json.dumps(d, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8", kod)

        def _xəta(self, mesaj: str, kod: int) -> None:
            self._JSON({"xəta": mesaj}, kod)

        # ── Yoxlamalar ────────────────────────────────────────────────

        def _yol_və_sorğu(self) -> tuple[str, dict[str, str]]:
            p = urllib.parse.urlsplit(self.path)
            sorğu = {a: d[0] for a, d in
                     urllib.parse.parse_qs(p.query).items()}
            return urllib.parse.unquote(p.path), sorğu

        def _host_yoxla(self) -> bool:
            if studio.host_icazəlidir(self.headers.get("Host")):
                return True
            self._xəta("icazəsiz Host başlığı", 403)
            return False

        def _nişan_yoxla(self, sorğu: dict[str, str]) -> bool:
            n = self.headers.get("X-Alqor-Token") or sorğu.get("t")
            if studio.nişan_düzdür(n):
                return True
            self._xəta("nişan (token) yanlışdır və ya yoxdur", 401)
            return False

        # ── GET ───────────────────────────────────────────────────────

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            if not self._host_yoxla():
                return
            yol, sorğu = self._yol_və_sorğu()
            if yol in ("/", "/index.html"):
                self._statik("index.html", {"Content-Security-Policy": CSP})
                return
            if yol.startswith("/statik/"):
                self._statik(yol[len("/statik/"):])
                return
            if yol == "/sened" or yol.startswith("/sened/"):
                self._sənəd(yol[len("/sened/"):] or "index.html")
                return
            if yol == "/favicon.ico":
                self._statik("ikon.svg")
                return
            if not yol.startswith("/api/"):
                self._xəta("tapılmadı", 404)
                return
            if not self._nişan_yoxla(sorğu):
                return
            if yol == "/api/islet/axin":
                self._axın(sorğu)
                return
            self._api("GET", yol, {})

        def _statik(self, ad: str,
                    başlıqlar: dict[str, str] | None = None) -> None:
            try:
                p = (STATİK / ad).resolve()
            except (OSError, ValueError):
                self._xəta("tapılmadı", 404)
                return
            if not p.is_relative_to(STATİK) or not p.is_file():
                self._xəta("tapılmadı", 404)
                return
            tip = MIME.get(p.suffix.lower(), "application/octet-stream")
            self._göndər(p.read_bytes(), tip, 200, başlıqlar)

        def _sənəd(self, ad: str) -> None:
            """Oflayn sənəd mərkəzi (Kömək menyusu)."""
            from alqor.sened_merkezi import sənəd_qovluğu
            kök = sənəd_qovluğu(Path(__file__).resolve().parent.parent)
            try:
                p = (kök / ad).resolve()
            except (OSError, ValueError):
                self._xəta("tapılmadı", 404)
                return
            if not p.is_relative_to(kök.resolve()) or not p.is_file():
                self._xəta("tapılmadı", 404)
                return
            tip = MIME.get(p.suffix.lower(), "application/octet-stream")
            self._göndər(p.read_bytes(), tip, 200, None)

        # ── POST ──────────────────────────────────────────────────────

        def do_POST(self) -> None:
            # Gövdə oxunmadan rədd edilən sorğudan sonra əlaqə bağlanır —
            # oxunmamış baytlar növbəti sorğu kimi ayrılmasın
            self.close_connection = True
            if not self._host_yoxla():
                return
            yol, sorğu = self._yol_və_sorğu()
            if not yol.startswith("/api/"):
                self._xəta("tapılmadı", 404)
                return
            if not self._nişan_yoxla(sorğu):
                return
            tip = (self.headers.get("Content-Type") or "").split(";")[0]
            if tip.strip().lower() != "application/json":
                self._xəta("Content-Type application/json olmalıdır", 415)
                return
            try:
                uzunluq = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                uzunluq = -1
            if not 0 <= uzunluq <= MAKS_GÖVDƏ:
                self._xəta("sorğu gövdəsi çox böyükdür", 413)
                return
            xam = self.rfile.read(uzunluq)
            self.close_connection = False
            try:
                gövdə = json.loads(xam or b"{}")
            except ValueError:
                self._xəta("JSON yanlışdır", 400)
                return
            if not isinstance(gövdə, dict):
                self._xəta("JSON obyekt olmalıdır", 400)
                return
            self._api("POST", yol, gövdə)

        def _api(self, üsul: str, yol: str, gövdə: dict) -> None:
            f = studio.marşrutlar.get((üsul, yol))
            if f is None:
                self._xəta("belə API yoxdur", 404)
                return
            try:
                self._JSON(f(gövdə))
            except (ApiXətası, YolXətası) as x:
                self._xəta(str(x), x.kod)
            except skelet.SkeletXətası as x:
                self._xəta(str(x), 422)
            except OSError as x:
                self._xəta(f"fayl sistemi xətası: {x.strerror or x}", 500)
            except Exception as x:                      # noqa: BLE001
                self._xəta(f"daxili xəta: {type(x).__name__}: {x}", 500)

        # ── Server-Sent Events ────────────────────────────────────────

        def _axın(self, sorğu: dict[str, str]) -> None:
            iş = studio.icra.al(sorğu.get("id", ""))
            if iş is None:
                self._xəta("belə iş yoxdur", 404)
                return
            try:
                n = max(0, int(sorğu.get("n", "0")))
                # EventSource yenidən qoşulanda sonuncu alınan nömrəni
                # göndərir — təkrar göndərməyək
                son_id = self.headers.get("Last-Event-ID")
                if son_id:
                    n = max(n, int(son_id) + 1)
            except ValueError:
                n = 0
            self.close_connection = True
            self.send_response(200)
            self.send_header("Content-Type",
                             "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                while True:
                    hadisələr, bitdi = iş.hadisələri_al(n, 10.0)
                    if not hadisələr:
                        if bitdi:
                            break
                        self.wfile.write(b": nebz\n\n")
                        self.wfile.flush()
                        continue
                    hissələr = []
                    for h in hadisələr:
                        hissələr.append(
                            f"id: {h['n']}\ndata: "
                            f"{json.dumps(h, ensure_ascii=False)}\n\n")
                    n += len(hadisələr)
                    self.wfile.write("".join(hissələr).encode("utf-8"))
                    self.wfile.flush()
                    if bitdi and n >= len(iş.hadisələr):
                        break
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

    return İdarəedici


# ═══════════════════════════════════════════════════════════════════════
#  Pəncərə — `pəncərə` modulunun aparıcısı ilə
# ═══════════════════════════════════════════════════════════════════════

class _TətbiqŞimi:
    """`pencere._pəncərəni_aç` gözlədiyi minimum `Tətbiq` interfeysi."""

    def __init__(self, ünvan: str):
        self._ünvan = ünvan
        self._prosslər: list[subprocess.Popen] = []

    def ünvan(self, _p: Any) -> str:
        return self._ünvan


class _PəncərəŞimi:
    _başlıq = "Alqor Studio"
    _en = 1440
    _hündürlük = 900
    _dəyişə_bilər = True


def pəncərəni_aç(studio: Studio) -> tuple[str, _TətbiqŞimi]:
    from alqor.pencere import _pəncərəni_aç
    şim = _TətbiqŞimi(studio.ünvan())
    return _pəncərəni_aç(şim, _PəncərəŞimi()), şim


def _özünü_yoxla(studio: Studio) -> list[tuple[str, bool]]:
    """`--sınaq` rejimi: əsas marşrutlar cavab verirmi."""
    import urllib.error
    import urllib.request
    nəticə: list[tuple[str, bool]] = []

    def al(yol: str, nişanlı: bool) -> int:
        s = urllib.request.Request(studio.kök_ünvan + yol)
        if nişanlı:
            s.add_header("X-Alqor-Token", studio.nişan)
        try:
            with urllib.request.urlopen(s, timeout=10) as c:
                return c.status
        except urllib.error.HTTPError as x:
            return x.code

    nəticə.append(("interfeys (/)", al("/", False) == 200))
    nəticə.append(("redaktor skripti", al("/statik/studio.js",
                                           False) == 200))
    nəticə.append(("API nişansız rədd edilir",
                   al("/api/melumat", False) == 401))
    nəticə.append(("API nişanla işləyir", al("/api/melumat", True) == 200))
    nəticə.append(("vidjet kataloqu", al("/api/kataloq", True) == 200))
    return nəticə


def işə_sal(qovluq: str | Path, port: int = 0, başsız: bool | None = None,
            sınaq: bool = False, ilk_fayl: str | None = None) -> int:
    """`python alqorc.py studio [qovluq] [--fayl ad]` — giriş nöqtəsi."""
    try:
        studio = Studio(qovluq, port, ilk_fayl).fonda_başlat()
    except YolXətası as x:
        print(f"✖ {x}", file=sys.stderr)
        return 4
    except OSError as x:
        print(f"✖ server qaldırıla bilmədi: {x}", file=sys.stderr)
        return 1

    print(f"Alqor Studio {VERSIYA}")
    print(f"  Layihə : {studio.layihə.kök}")
    print(f"  Ünvan  : {studio.ünvan()}")
    sys.stdout.flush()

    if sınaq:
        uğurlu = True
        for ad, ok in _özünü_yoxla(studio):
            print(f"  {'✓' if ok else '✖'} {ad}")
            uğurlu = uğurlu and ok
        studio.dayandır()
        return 0 if uğurlu else 1

    if başsız is None:
        from alqor.pencere import _başsız_rejimdir
        başsız = _başsız_rejimdir()

    şim: _TətbiqŞimi | None = None
    if başsız:
        print("  Rejim  : başsız — ünvanı brauzerdə açın "
              "(dayandırmaq: Ctrl+C)")
    else:
        aparıcı, şim = pəncərəni_aç(studio)
        print(f"  Pəncərə: {aparıcı}")
    sys.stdout.flush()

    try:
        while True:
            time.sleep(0.5)
            if not başsız and studio.bitməlidir():
                break
    except KeyboardInterrupt:
        print("\n⊣ dayandırıldı")
    finally:
        studio.dayandır()
        if şim is not None:
            for p in şim._prosslər:
                try:
                    p.terminate()
                except OSError:
                    pass
    return 0
