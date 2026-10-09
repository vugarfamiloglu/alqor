"""
Alqor — `veb` modulu: HTTP server və marşrutlaşdırma.

Spesifikasiya § 11. Python-un `http.server` modulu üzərində qurulub —
xarici asılılıq yoxdur.

    gətir veb

    funksiya əsas()
        dəyişən s = yeni veb.Server()
        s.ara(veb.jurnal())
        s.al("/", funksiya(sorğu)
            qaytar veb.mətn("Salam, dünya!")
        son)
        s.dinlə(8080)
    son
"""

from __future__ import annotations
import gzip
import json as _json
import mimetypes
import re
import secrets
import os
import socket
import sys
import threading
import time
import traceback
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .deyerler import AlqorXəta, Element, Nümunə, mətnə, tip_adı

# HTTP metodu → Alqor adı
METOD_ADLARI = {
    "GET": "AL", "POST": "GÖNDƏR", "PUT": "YENİLƏ",
    "PATCH": "YAMAQ", "DELETE": "SİL", "HEAD": "BAŞLIQ",
    "OPTIONS": "SEÇİMLƏR",
}

# Alqor marşrut metodu → HTTP
MARŞRUT_METODLARI = {
    "al": "GET", "göndər": "POST", "yenilə": "PUT",
    "yamaq": "PATCH", "sil": "DELETE", "hamısı": "*",
}

VƏZİYYƏT_MƏTNLƏRİ = {
    200: "OK", 201: "Created", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 304: "Not Modified",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 409: "Conflict",
    413: "Payload Too Large", 422: "Unprocessable Content",
    429: "Too Many Requests", 500: "Internal Server Error",
    503: "Service Unavailable",
}

MAKS_GÖVDƏ = 16 * 1024 * 1024          # 16 MB


# ═══════════════════════════════════════════════════════════════════════
#  Cavab
# ═══════════════════════════════════════════════════════════════════════

class _Yoxdur:
    """`başlıq(ad)` oxuyucusunu `başlıq(ad, boş)`dan ayırmaq üçün."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<yoxdur>"


_YOXDUR = _Yoxdur()


class Cavab:
    """HTTP cavabı. Metodları zəncirlənə bilir."""

    __slots__ = ("vəziyyət", "başlıqlar", "gövdə", "kukilər")

    def __init__(self, gövdə: bytes = b"", vəziyyət: int = 200,
                 tip: str = "text/plain; charset=utf-8"):
        self.vəziyyət = vəziyyət
        self.gövdə = gövdə
        self.başlıqlar: dict[str, str] = {"Content-Type": tip}
        self.kukilər: list[str] = []

    # ── Zəncirlənən dəyişdiricilər ────────────────────────────────────

    def kod(self, v: int) -> "Cavab":
        self.vəziyyət = int(v)
        return self

    def başlıq(self, ad: str, dəyər: Any = _YOXDUR):
        """
        İki arqumentlə başlığı təyin edir və `özü`nü qaytarır:
            veb.mətn("a").başlıq("X-Ad", "dəyər")
        Bir arqumentlə başlığı oxuyur (`boş` — yoxdursa):
            cavab.başlıq("Content-Type")
        """
        if dəyər is _YOXDUR:
            açar = str(ad).lower()
            if açar == "set-cookie" and self.kukilər:
                # Kukilər ayrıca saxlanılır (hər biri ayrı başlıqdır)
                return ", ".join(self.kukilər)
            for k, v in self.başlıqlar.items():
                if k.lower() == açar:
                    return v
            return None
        self.başlıqlar[str(ad)] = str(dəyər)
        return self

    def kuki(self, ad: str, dəyər: str, müddət: int | None = None,
             yol: str = "/", yalnızHTTP: bool = True,
             təhlükəsiz: bool = False,
             eyniSayt: str = "Lax") -> "Cavab":
        hissələr = [f"{ad}={urllib.parse.quote(str(dəyər))}",
                    f"Path={yol}", f"SameSite={eyniSayt}"]
        if müddət is not None:
            hissələr.append(f"Max-Age={int(müddət)}")
        if yalnızHTTP:
            hissələr.append("HttpOnly")
        if təhlükəsiz:
            hissələr.append("Secure")
        self.kukilər.append("; ".join(hissələr))
        return self

    def kukiSil(self, ad: str, yol: str = "/") -> "Cavab":
        self.kukilər.append(f"{ad}=; Path={yol}; Max-Age=0")
        return self

    # ── Sorğu ─────────────────────────────────────────────────────────

    def mətnƏt(self) -> str:
        return self.gövdə.decode("utf-8", "replace")

    def uzunluq(self) -> int:
        return len(self.gövdə)

    def __repr__(self) -> str:
        return f"<cavab {self.vəziyyət} {len(self.gövdə)} bayt>"


# ═══════════════════════════════════════════════════════════════════════
#  Sorğu
# ═══════════════════════════════════════════════════════════════════════

class Sorğu:
    __slots__ = ("_metod", "_yol", "_sorğu_sətri", "_başlıqlar",
                 "_gövdə", "_parametrlər", "_ip", "_sessiya",
                 "_server", "_json_keşi", "_form_keşi")

    def __init__(self, metod: str, yol: str, sorğu_sətri: str,
                 başlıqlar: dict[str, str], gövdə: bytes, ip: str,
                 server: "Server"):
        self._metod = metod
        self._yol = yol
        self._sorğu_sətri = sorğu_sətri
        self._başlıqlar = {k.lower(): v for k, v in başlıqlar.items()}
        self._gövdə = gövdə
        self._parametrlər: dict[str, str] = {}
        self._ip = ip
        self._server = server
        self._sessiya: dict[str, Any] | None = None
        self._json_keşi: Any = None
        self._form_keşi: dict[str, str] | None = None

    # ── Əsas ──────────────────────────────────────────────────────────

    def metod(self) -> str:
        return METOD_ADLARI.get(self._metod, self._metod)

    def yol(self) -> str:
        return self._yol

    def tamURL(self) -> str:
        host = self._başlıqlar.get("host", "localhost")
        sorğu = f"?{self._sorğu_sətri}" if self._sorğu_sətri else ""
        return f"http://{host}{self._yol}{sorğu}"

    def IP(self) -> str:
        return self._ip

    def istifadəçiAgenti(self) -> str:
        return self._başlıqlar.get("user-agent", "")

    # ── Parametrlər ───────────────────────────────────────────────────

    def parametr(self, ad: str, standart: Any = None) -> Any:
        return self._parametrlər.get(str(ad), standart)

    def parametrlər(self) -> dict[str, str]:
        return dict(self._parametrlər)

    def sorğuParametr(self, ad: str, standart: Any = None) -> Any:
        hamısı = urllib.parse.parse_qs(self._sorğu_sətri)
        dəyər = hamısı.get(str(ad))
        return dəyər[0] if dəyər else standart

    def sorğuParametrHamısı(self) -> dict[str, str]:
        return {k: v[0] for k, v in
                urllib.parse.parse_qs(self._sorğu_sətri).items()}

    # ── Başlıqlar və kukilər ──────────────────────────────────────────

    def başlıq(self, ad: str, standart: Any = None) -> Any:
        return self._başlıqlar.get(str(ad).lower(), standart)

    def başlıqlar(self) -> dict[str, str]:
        return dict(self._başlıqlar)

    def kuki(self, ad: str, standart: Any = None) -> Any:
        xam = self._başlıqlar.get("cookie", "")
        for parça in xam.split(";"):
            if "=" not in parça:
                continue
            k, v = parça.split("=", 1)
            if k.strip() == str(ad):
                return urllib.parse.unquote(v.strip())
        return standart

    # ── Gövdə ─────────────────────────────────────────────────────────

    def gövdə(self) -> str:
        return self._gövdə.decode("utf-8", "replace")

    def gövdəBayt(self) -> bytes:
        return self._gövdə

    def json(self) -> Any:
        if self._json_keşi is None:
            if not self._gövdə:
                return None
            try:
                self._json_keşi = _json.loads(
                    self._gövdə.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as x:
                raise AlqorXəta("JSONXətası",
                                f"sorğu gövdəsi JSON deyil: {x}",
                                kod="ALQ-R005")
        return self._json_keşi

    def form(self) -> dict[str, str]:
        if self._form_keşi is None:
            mətn = self._gövdə.decode("utf-8", "replace")
            self._form_keşi = {
                k: v[0] for k, v in
                urllib.parse.parse_qs(mətn).items()}
        return dict(self._form_keşi)

    # ── Sessiya ───────────────────────────────────────────────────────

    def sessiya(self) -> "Sessiya":
        return Sessiya(self)

    def __repr__(self) -> str:
        return f"<sorğu {self.metod()} {self._yol}>"


class Sessiya:
    """Sorğuya bağlı sessiya — yaddaşda saxlanılır."""

    __slots__ = ("_sorğu",)

    def __init__(self, sorğu: Sorğu):
        self._sorğu = sorğu

    @property
    def _anbar(self) -> dict[str, Any]:
        s = self._sorğu
        if s._sessiya is None:
            açar = s.kuki(SESSİYA_KUKİSİ)
            s._sessiya = s._server._sessiyalar.setdefault(
                açar or "", {}) if açar else {}
        return s._sessiya

    def al(self, ad: str, standart: Any = None) -> Any:
        return self._anbar.get(str(ad), standart)

    def qoy(self, ad: str, dəyər: Any) -> None:
        s = self._sorğu
        açar = s.kuki(SESSİYA_KUKİSİ)
        if not açar:
            açar = secrets.token_urlsafe(24)
            s._server._yeni_sessiyalar[threading.get_ident()] = açar
        anbar = s._server._sessiyalar.setdefault(açar, {})
        anbar[str(ad)] = dəyər
        s._sessiya = anbar

    def sil(self, ad: str) -> Any:
        return self._anbar.pop(str(ad), None)

    def təmizlə(self) -> None:
        s = self._sorğu
        açar = s.kuki(SESSİYA_KUKİSİ)
        if açar:
            s._server._sessiyalar.pop(açar, None)
        s._sessiya = {}

    def ehtiva(self, ad: str) -> bool:
        return str(ad) in self._anbar

    def __repr__(self) -> str:
        return f"<sessiya {len(self._anbar)} açar>"


SESSİYA_KUKİSİ = "alqor_sessiya"


# ═══════════════════════════════════════════════════════════════════════
#  Marşrut
# ═══════════════════════════════════════════════════════════════════════

_PARAMETR = re.compile(r":([A-Za-zƏəİıĞğŞşÇçÖöÜü_][\w]*)(\?)?")
_JOKER = re.compile(r"\*([A-Za-zƏəİıĞğŞşÇçÖöÜü_][\w]*)?")


@dataclass
class Marşrut:
    metod: str
    naxış: str
    idarəedici: Any
    ara_proqramlar: list = field(default_factory=list)
    _rx: Any = None

    def __post_init__(self):
        self._rx = re.compile(_naxışı_çevir(self.naxış))

    def uyğundur(self, metod: str, yol: str) -> dict[str, str] | None:
        if self.metod != "*" and self.metod != metod:
            return None
        u = self._rx.match(yol)
        if u is None:
            return None
        return {k: urllib.parse.unquote(v)
                for k, v in u.groupdict().items() if v is not None}


def _naxışı_çevir(naxış: str) -> str:
    """`/istifadəçi/:id` → `^/istifadəçi/(?P<id>[^/]+)$`"""
    nəticə = ["^"]
    i = 0
    while i < len(naxış):
        p = _PARAMETR.match(naxış, i)
        if p:
            ad, ixtiyari = p.group(1), p.group(2)
            if ixtiyari:
                # `/a/:b?` → `b` olmaya da bilər
                if nəticə and nəticə[-1] == "/":
                    nəticə.pop()
                nəticə.append(f"(?:/(?P<{ad}>[^/]+))?")
            else:
                nəticə.append(f"(?P<{ad}>[^/]+)")
            i = p.end()
            continue
        j = _JOKER.match(naxış, i)
        if j:
            ad = j.group(1)
            nəticə.append(f"(?P<{ad}>.*)" if ad else ".*")
            i = j.end()
            continue
        nəticə.append(re.escape(naxış[i]))
        i += 1
    nəticə.append("/?$")
    return "".join(nəticə)


# ═══════════════════════════════════════════════════════════════════════
#  Marşrut qrupu
# ═══════════════════════════════════════════════════════════════════════

class Qrup:
    """`s.qrup("/api", funksiya(q) ... son)` daxilində işlənir."""

    __slots__ = ("_server", "_prefiks", "_ara")

    def __init__(self, server: "Server", prefiks: str, ara: list):
        self._server = server
        self._prefiks = prefiks.rstrip("/")
        self._ara = ara

    def _əlavə(self, metod: str, naxış: str, *arqumentlər) -> "Qrup":
        idarəedici, ara = _idarəedicini_ayır(arqumentlər)
        self._server._marşrutlar.append(Marşrut(
            metod, self._prefiks + naxış, idarəedici,
            self._ara + ara))
        return self

    def al(self, naxış, *a): return self._əlavə("GET", naxış, *a)
    def göndər(self, naxış, *a): return self._əlavə("POST", naxış, *a)
    def yenilə(self, naxış, *a): return self._əlavə("PUT", naxış, *a)
    def yamaq(self, naxış, *a): return self._əlavə("PATCH", naxış, *a)
    def sil(self, naxış, *a): return self._əlavə("DELETE", naxış, *a)
    def hamısı(self, naxış, *a): return self._əlavə("*", naxış, *a)

    def qrup(self, prefiks: str, qurucu: Any) -> "Qrup":
        alt = Qrup(self._server, self._prefiks + prefiks, list(self._ara))
        self._server._icraçı._çağır(qurucu, [alt], {}, None)
        return self

    def ara(self, ara_proqram: Any) -> "Qrup":
        self._ara.append(ara_proqram)
        return self

    def __repr__(self) -> str:
        return f"<qrup {self._prefiks or '/'}>"


def _idarəedicini_ayır(arqumentlər: tuple) -> tuple[Any, list]:
    """`(idarəedici)` və ya `([ara1, ara2], idarəedici)` formaları."""
    if len(arqumentlər) == 1:
        return arqumentlər[0], []
    if len(arqumentlər) >= 2 and isinstance(arqumentlər[0], list):
        return arqumentlər[1], list(arqumentlər[0])
    return arqumentlər[-1], list(arqumentlər[:-1])


# ═══════════════════════════════════════════════════════════════════════
#  Server
# ═══════════════════════════════════════════════════════════════════════

def qovluğu_həll(icraçı, qovluq) -> Path:
    """
    Nisbi qovluğu skriptin qovluğuna nisbətən həll edir. Cari iş
    qovluğu etibarsızdır — `alqor işlət ../layihə/əsas.alq` da
    işləməlidir.
    """
    q = Path(qovluq)
    if q.is_absolute():
        return q
    kök = getattr(icraçı, "əsas_qovluq", None)
    if kök is None:
        return q
    namizəd = Path(kök) / q
    if namizəd.exists() or not q.exists():
        return namizəd
    return q


def şablon_qovluğunu_təyin_et(icraçı, qovluq) -> None:
    """`veb.şablonQovluğu(...)` və `server.şablonQovluğu(...)` — biri."""
    icraçı._veb_şablon_qovluğu = Path(qovluq)


def şablon_qovluğu(icraçı) -> Path:
    q = getattr(icraçı, "_veb_şablon_qovluğu", None)
    return qovluğu_həll(icraçı, q if q is not None else Path("şablon"))


class Server:
    def __init__(self, icraçı):
        self._icraçı = icraçı
        self._marşrutlar: list[Marşrut] = []
        self._ara_proqramlar: list = []
        self._statik: list[tuple[str, Path, str]] = []
        # Statik və şablon yolları `qovluğu_həll` ilə təyin olunur
        self._xəta_idarəedicisi: Any = None
        self._tapılmadı: Any = None
        self._soketlər: dict[str, Any] = {}
        self._sessiyalar: dict[str, dict[str, Any]] = {}
        self._yeni_sessiyalar: dict[int, str] = {}
        self._http: ThreadingHTTPServer | None = None
        self._inkişaf = True
        self._komponentlər: list[_KomponentQoşması] = []

    # ── Marşrutlar ────────────────────────────────────────────────────

    def _əlavə(self, metod: str, naxış: str, *arqumentlər) -> "Server":
        idarəedici, ara = _idarəedicini_ayır(arqumentlər)
        self._marşrutlar.append(
            Marşrut(metod, naxış, idarəedici, ara))
        return self

    def al(self, naxış, *a): return self._əlavə("GET", naxış, *a)
    def göndər(self, naxış, *a): return self._əlavə("POST", naxış, *a)
    def yenilə(self, naxış, *a): return self._əlavə("PUT", naxış, *a)
    def yamaq(self, naxış, *a): return self._əlavə("PATCH", naxış, *a)
    def sil(self, naxış, *a): return self._əlavə("DELETE", naxış, *a)
    def hamısı(self, naxış, *a): return self._əlavə("*", naxış, *a)

    def qrup(self, prefiks: str, qurucu: Any) -> "Server":
        q = Qrup(self, prefiks, [])
        self._icraçı._çağır(qurucu, [q], {}, None)
        return self

    def ara(self, ara_proqram: Any) -> "Server":
        self._ara_proqramlar.append(ara_proqram)
        return self

    def statik(self, prefiks: str, qovluq: str,
               indeks: str = "") -> "Server":
        self._statik.append(
            (prefiks.rstrip("/"), qovluğu_həll(self._icraçı, qovluq),
             indeks))
        return self

    def şablonQovluğu(self, qovluq: str) -> "Server":
        şablon_qovluğunu_təyin_et(self._icraçı, qovluq)
        return self

    def komponent(self, yol: str, mənbə: Any, başlıq: Any = "Alqor",
                  üslub: Any = None) -> "Server":
        """
        Komponenti `yol`-a qoşur — vidjet hadisələri vebdə də işləyir.

            s.komponent("/", Panel, başlıq: "Heyət paneli")
            s.komponent("/say", () => yeni Sayğac(10))

        `mənbə` komponent sinfi və ya nümunə qaytaran funksiyadır. Hər
        brauzer sessiyası öz nümunəsini alır: bir istifadəçinin
        `vəziyyət` dəyişikliyi digərinə görünmür.
        """
        yol = str(yol)
        if not yol.startswith("/"):
            raise AlqorXəta(
                "ArqumentXətası",
                f"komponent yolu `/` ilə başlamalıdır: `{yol}`",
                kod="ALQ-R013")
        if any(q.yol == yol for q in self._komponentlər):
            raise AlqorXəta(
                "ArqumentXətası",
                f"`{yol}` yoluna artıq komponent qoşulub",
                kod="ALQ-R013")
        self._komponentlər.append(_KomponentQoşması(
            len(self._komponentlər), yol, mənbə,
            mətnə(başlıq, self._icraçı),
            mətnə(üslub, self._icraçı) if üslub is not None else ""))
        return self

    def soket(self, naxış: str, idarəedici: Any) -> "Server":
        """
        WebSocket marşrutu (§ 11.6): hər qoşulmada `idarəedici(soket)`
        çağırılır; `soket.hadisə("mesaj", …)`, `soket.göndər(…)`,
        `soket.otağaYayımla(…)`.
        """
        from .vebsoket import Qovşaq
        self._soketlər[str(naxış)] = (Marşrut("GET", str(naxış),
                                              idarəedici, []), Qovşaq())
        return self

    def _soket_tap(self, yol: str):
        for marşrut, qovşaq in self._soketlər.values():
            if marşrut.uyğundur("GET", yol) is not None:
                return marşrut, qovşaq
        return None

    def _soketi_idarə_et(self, işləyici) -> bool:
        """WebSocket sorğusudursa idarə edir (bağlanana qədər) — True."""
        from . import vebsoket as W
        if not self._soketlər or işləyici.command != "GET" or \
                not W.soket_sorğusudur(işləyici):
            return False
        ayrılmış = urllib.parse.urlsplit(_yolu_düzəlt(işləyici.path))
        yol = urllib.parse.unquote(ayrılmış.path, encoding="utf-8",
                                   errors="replace") or "/"
        tapılan = self._soket_tap(yol)
        if tapılan is None:
            return False
        marşrut, qovşaq = tapılan
        işləyici.close_connection = True
        if not W.server_əl_sıxması(işləyici):
            return True
        sorğu = Sorğu("GET", yol, ayrılmış.query,
                      dict(işləyici.headers.items()), b"",
                      işləyici.client_address[0], self)
        sorğu._parametrlər = marşrut.uyğundur("GET", yol) or {}
        b = W.Bağlantı(işləyici.connection, self._icraçı, False,
                       qovşaq=qovşaq, sorğu=sorğu)
        qovşaq.əlavə(b)
        try:
            self._icraçı._çağır(marşrut.idarəedici, [b], {}, None)
        except AlqorXəta as x:
            print(f"✖ WebSocket {yol}: {x.tip}: {x.mesaj}", file=sys.stderr)
            b.bağla(1011, "server xətası")
            qovşaq.çıxar(b)
            return True
        b._yay("qoşuldu")
        b.dövr()
        return True

    def xətaİdarəedicisi(self, f: Any) -> "Server":
        self._xəta_idarəedicisi = f
        return self

    def tapılmadı(self, f: Any) -> "Server":
        self._tapılmadı = f
        return self

    def marşrutlar(self) -> list:
        return [(m.metod, m.naxış) for m in self._marşrutlar]

    # ── Sorğunun idarə olunması ───────────────────────────────────────

    def _idarə_et(self, sorğu: Sorğu) -> Cavab:
        # Pozulmuş yol ara proqramlara da çatmır
        if yol_təhlükəlidir(sorğu._yol):
            return Cavab("400 Yol etibarsızdır".encode("utf-8"), 400)
        zəncir = list(self._ara_proqramlar)

        def nüvə(s: Sorğu) -> Cavab:
            return self._marşrutu_tap(s)

        return self._zənciri_işlət(zəncir, nüvə, sorğu)

    def _zənciri_işlət(self, zəncir: list, nüvə: Callable,
                       sorğu: Sorğu) -> Cavab:
        if not zəncir:
            return _cavaba_çevir(nüvə(sorğu), self._icraçı)

        ara = zəncir[0]
        qalan = zəncir[1:]

        def növbəti(s: Sorğu) -> Cavab:
            return self._zənciri_işlət(qalan, nüvə, s)

        from .deyerler import Daxili
        növbəti_funksiya = Daxili("növbəti", lambda s: növbəti(s), 1, 1)
        nəticə = self._icraçı._çağır(ara, [sorğu, növbəti_funksiya],
                                     {}, None)
        return _cavaba_çevir(nəticə, self._icraçı)

    def _marşrutu_tap(self, sorğu: Sorğu) -> Cavab:
        # 1. Statik fayllar
        statik = self._statik_cavab(sorğu)
        if statik is not None:
            return statik

        # 2. Komponentlər
        if self._komponentlər:
            k = self._komponent_cavabı(sorğu)
            if k is not None:
                return k

        # 3. Marşrutlar
        yol_var = False
        for m in self._marşrutlar:
            parametrlər = m.uyğundur(sorğu._metod, sorğu._yol)
            if parametrlər is None:
                if m._rx.match(sorğu._yol):
                    yol_var = True
                continue
            sorğu._parametrlər = parametrlər
            if m.ara_proqramlar:
                def nüvə(s: Sorğu, _m=m) -> Cavab:
                    return self._icraçı._çağır(_m.idarəedici, [s], {},
                                               None)
                return self._zənciri_işlət(
                    list(m.ara_proqramlar), nüvə, sorğu)
            return _cavaba_çevir(
                self._icraçı._çağır(m.idarəedici, [sorğu], {}, None),
                self._icraçı)

        # 4. Metod uyğun gəlmir
        if yol_var:
            return Cavab("405 Metod icazəli deyil".encode("utf-8"), 405)

        # 5. Tapılmadı
        if self._tapılmadı is not None:
            return _cavaba_çevir(
                self._icraçı._çağır(self._tapılmadı, [sorğu], {}, None),
                self._icraçı)
        return self._404(sorğu)

    def _404(self, sorğu: Sorğu) -> Cavab:
        if not self._inkişaf:
            return Cavab(b"404 Not Found", 404)
        sətirlər = "".join(
            f"<li><code>{m.metod}</code> {m.naxış}</li>"
            for m in self._marşrutlar)
        html = (
            "<!DOCTYPE html><html lang='az'><head><meta charset='utf-8'>"
            "<title>404 — Tapılmadı</title>"
            "<style>body{font-family:system-ui;max-width:42rem;"
            "margin:3rem auto;padding:0 1rem;line-height:1.6}"
            "code{background:#f4f4f5;padding:.1rem .3rem;border-radius:3px}"
            "h1{font-size:1.5rem}</style></head><body>"
            f"<h1>404 — <code>{_qaç(sorğu._yol)}</code> tapılmadı</h1>"
            f"<p>Bu serverdə belə marşrut yoxdur.</p>"
            f"<h2>Mövcud marşrutlar</h2><ul>{sətirlər}</ul>"
            "<p style='color:#71717a'>Alqor inkişaf serveri</p>"
            "</body></html>")
        return Cavab(html.encode("utf-8"), 404,
                     "text/html; charset=utf-8")

    # ── Komponentlər ──────────────────────────────────────────────────

    def _komponent_cavabı(self, sorğu: Sorğu) -> Cavab | None:
        if sorğu._metod == "POST" and sorğu._yol == HADİSƏ_YOLU:
            return self._komponent_hadisəsi(sorğu)
        if sorğu._metod not in ("GET", "HEAD"):
            return None
        for q in self._komponentlər:
            if q.yol == sorğu._yol:
                return self._komponent_səhifəsi(q, sorğu)
        return None

    def _komponent_səhifəsi(self, q: "_KomponentQoşması",
                            sorğu: Sorğu) -> Cavab:
        from .pencere import qaç
        from .vidjet import ƏSAS_ÜSLUB, ÜSLUB as VİDJET_ÜSLUBU

        açar = sorğu.kuki(KOMPONENT_KUKİSİ)
        yeni_açar = None
        if not açar or not KOMPONENT_AÇARI.fullmatch(açar):
            açar = yeni_açar = secrets.token_urlsafe(24)
        ss = q.sessiya(açar, self._icraçı, yarat=True)
        assert ss is not None
        with ss.qıfıl:
            kök = ss.göstər(self._icraçı)
        html = (
            "<!DOCTYPE html>\n"
            '<html lang="az"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,'
            'initial-scale=1">'
            f"<title>{qaç(q.başlıq)}</title>"
            f"<style>{ƏSAS_ÜSLUB}{VİDJET_ÜSLUBU}{q.üslub}</style>"
            "</head><body>"
            f'<main id="alqor-kök" class="v-gövdə" '
            f'data-a-komponent="{q.nömrə}">{kök}</main>'
            f"<script>{VEB_SKRİPTİ}</script></body></html>")
        c = Cavab(html.encode("utf-8"), 200, "text/html; charset=utf-8")
        c.başlıq("Cache-Control", "no-store")
        if yeni_açar:
            # `Strict`: kuki başqa saytdan başlanan sorğuya qoşulmur
            c.kuki(KOMPONENT_KUKİSİ, yeni_açar, eyniSayt="Strict")
        return c

    def _komponent_hadisəsi(self, sorğu: Sorğu) -> Cavab:
        from .pencere import kənar_sorğudur

        başlıqlar = {"Host": sorğu.başlıq("host") or "",
                     "Origin": sorğu.başlıq("origin") or ""}
        if kənar_sorğudur(başlıqlar):
            return Cavab(b"403 Forbidden", 403)
        tip = (sorğu.başlıq("content-type") or "").lower()
        if not tip.startswith("application/json"):
            # JSON tələbi kənar saytı CORS ön-yoxlamasına məcbur edir
            return Cavab(b"415 Unsupported Media Type", 415)
        try:
            v = _json.loads(sorğu._gövdə or b"{}")
            nömrə = int(v.get("k"))
            açar_id = str(v.get("id") or "")
        except (ValueError, TypeError, AttributeError):
            return Cavab(b"400 Bad Request", 400)
        if not 0 <= nömrə < len(self._komponentlər):
            return Cavab(b"404 Not Found", 404)
        q = self._komponentlər[nömrə]
        açar = sorğu.kuki(KOMPONENT_KUKİSİ)
        ss = (q.sessiya(açar, self._icraçı, yarat=False)
              if açar and KOMPONENT_AÇARI.fullmatch(açar) else None)
        if ss is None:
            # Sessiya köhnəlib (server yenidən başladı, vaxtı bitdi) —
            # brauzer səhifəni yenidən yükləyir
            return _json_cavab({"yenidən": True}, self._icraçı)
        with ss.qıfıl:
            nəticə = ss.hadisəni_işlət(self._icraçı, açar_id,
                                       v.get("dəyər"))
        c = Cavab(_json.dumps(nəticə, ensure_ascii=False).encode("utf-8"),
                  200, "application/json; charset=utf-8")
        c.başlıq("Cache-Control", "no-store")
        return c

    def _statik_cavab(self, sorğu: Sorğu) -> Cavab | None:
        if sorğu._metod not in ("GET", "HEAD"):
            return None
        for prefiks, qovluq, indeks in self._statik:
            if prefiks and not sorğu._yol.startswith(prefiks + "/") \
                    and sorğu._yol != prefiks:
                continue
            nisbi = sorğu._yol[len(prefiks):].lstrip("/")
            if not nisbi and indeks:
                nisbi = indeks
            if not nisbi:
                continue
            # Yol qaçışının qarşısını alırıq. `startswith` yaramaz:
            # `/veb-gizli` mətn kimi `/veb` ilə başlayır, amma onun
            # içində DEYİL. `is_relative_to` həqiqi seqment müqayisəsi
            # aparır. Simvolik keçidlər `resolve()` ilə açılır.
            try:
                hədəf = (qovluq / nisbi).resolve()
                kök = qovluq.resolve()
            except OSError:
                continue
            if hədəf != kök and not hədəf.is_relative_to(kök):
                return Cavab(b"403 Forbidden", 403)
            if hədəf.is_dir() and indeks:
                hədəf = hədəf / indeks
            if not hədəf.is_file():
                continue
            tip = (mimetypes.guess_type(str(hədəf))[0]
                   or "application/octet-stream")
            if tip.startswith("text/") or tip in (
                    "application/javascript", "application/json"):
                tip += "; charset=utf-8"
            c = Cavab(hədəf.read_bytes(), 200, tip)
            c.başlıq("Cache-Control", "public, max-age=3600")
            return c
        return None

    # ── Dinləmə ───────────────────────────────────────────────────────

    def dinlə(self, port: int = 8080, host: str = "127.0.0.1") -> None:
        server = self
        # Hostinq platformaları (Render, Fly.io, Docker) portu və ünvanı
        # mühit dəyişəni ilə verir — `alqor yerləşdir` bunlara güvənir
        port = int(os.environ.get("PORT") or os.environ.get("ALQOR_PORT")
                   or port)
        host = os.environ.get("ALQOR_HOST") or host

        class İşləyici(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "Alqor"
            sys_version = ""

            def log_message(self, format, *args):
                pass                        # `veb.jurnal()` ara proqramı

            def _işlə(self):
                try:
                    if server._soketi_idarə_et(self):
                        return
                except (BrokenPipeError, ConnectionResetError):
                    return
                try:
                    cavab = server._sorğunu_qur_və_işlət(self)
                except Exception:           # noqa: BLE001
                    cavab = server._daxili_xəta(traceback.format_exc())
                try:
                    self._göndər(cavab)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _göndər(self, cavab: Cavab):
                gövdə = cavab.gövdə
                self.send_response(
                    cavab.vəziyyət,
                    VƏZİYYƏT_MƏTNLƏRİ.get(cavab.vəziyyət, ""))
                for ad, dəyər in cavab.başlıqlar.items():
                    self.send_header(ad, dəyər)
                for k in cavab.kukilər:
                    self.send_header("Set-Cookie", k)
                self.send_header("Content-Length", str(len(gövdə)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(gövdə)

            do_GET = do_POST = do_PUT = do_PATCH = _işlə
            do_DELETE = do_HEAD = do_OPTIONS = _işlə

        try:
            self._http = ThreadingHTTPServer((host, port), İşləyici)
        except OSError as x:
            raise AlqorXəta(
                "ŞəbəkəXətası",
                f"{host}:{port} dinlənilə bilmədi — {x.strerror}. "
                "Port məşğuldurmu?", kod="ALQ-R013")
        self._http.daemon_threads = True

        ünvan = f"http://{host}:{port}"
        print(f"✓ Alqor veb serveri: {ünvan}")
        print(f"  {len(self._marşrutlar)} marşrut, "
              f"{len(self._ara_proqramlar)} ara proqram")
        print("  Dayandırmaq üçün Ctrl+C")
        sys.stdout.flush()
        try:
            self._http.serve_forever()
        except KeyboardInterrupt:
            print("\n⊣ server dayandırıldı")
        finally:
            self._http.server_close()

    def dayandır(self) -> None:
        if self._http is not None:
            threading.Thread(target=self._http.shutdown,
                             daemon=True).start()

    def _sorğunu_qur_və_işlət(self, işləyici) -> Cavab:
        ayrılmış = urllib.parse.urlsplit(_yolu_düzəlt(işləyici.path))
        uzunluq = int(işləyici.headers.get("Content-Length") or 0)
        if uzunluq > MAKS_GÖVDƏ:
            return Cavab(b"413 Payload Too Large", 413)
        gövdə = işləyici.rfile.read(uzunluq) if uzunluq else b""

        sorğu = Sorğu(
            işləyici.command,
            urllib.parse.unquote(ayrılmış.path, encoding="utf-8",
                                 errors="replace") or "/",
            ayrılmış.query,
            dict(işləyici.headers.items()),
            gövdə,
            işləyici.client_address[0],
            self)

        sap = threading.get_ident()
        self._yeni_sessiyalar.pop(sap, None)
        try:
            cavab = self._idarə_et(sorğu)
        except AlqorXəta as x:
            cavab = self._alqor_xətası(sorğu, x)

        # Yeni sessiya yaradılıbsa kukini göndəririk
        yeni = self._yeni_sessiyalar.pop(sap, None)
        if yeni:
            cavab.kuki(SESSİYA_KUKİSİ, yeni, müddət=86400)
        return cavab

    def _alqor_xətası(self, sorğu: Sorğu, x: AlqorXəta) -> Cavab:
        if self._xəta_idarəedicisi is not None:
            try:
                from .deyerler import Nümunə as _N
                obyekt = self._icraçı._xəta_obyekti(x)
                return _cavaba_çevir(
                    self._icraçı._çağır(self._xəta_idarəedicisi,
                                        [sorğu, obyekt], {}, None),
                    self._icraçı)
            except AlqorXəta:
                pass

        yer = f" ({x.yer})" if x.yer else ""
        mesaj = f"{x.tip}: {x.mesaj}{yer}"
        print(f"✖ {sorğu.metod()} {sorğu._yol} → {mesaj}",
              file=sys.stderr)

        if not self._inkişaf:
            return Cavab(b"500 Internal Server Error", 500)
        html = (
            "<!DOCTYPE html><html lang='az'><head><meta charset='utf-8'>"
            "<title>500 — Server xətası</title>"
            "<style>body{font-family:system-ui;max-width:48rem;"
            "margin:3rem auto;padding:0 1rem;line-height:1.6}"
            "pre{background:#18181b;color:#fafafa;padding:1rem;"
            "border-radius:6px;overflow-x:auto}</style></head><body>"
            "<h1>500 — Server xətası</h1>"
            f"<pre>{_qaç(mesaj)}</pre>"
            f"<p><code>{sorğu.metod()} {_qaç(sorğu._yol)}</code></p>"
            "</body></html>")
        return Cavab(html.encode("utf-8"), 500,
                     "text/html; charset=utf-8")

    def _daxili_xəta(self, iz: str) -> Cavab:
        print(iz, file=sys.stderr)
        if not self._inkişaf:
            return Cavab(b"500 Internal Server Error", 500)
        return Cavab(
            f"<pre>{_qaç(iz)}</pre>".encode("utf-8"), 500,
            "text/html; charset=utf-8")

    def __repr__(self) -> str:
        return f"<server {len(self._marşrutlar)} marşrut>"


# ═══════════════════════════════════════════════════════════════════════
#  Komponent qoşması — vidjet hadisələri vebdə
# ═══════════════════════════════════════════════════════════════════════

KOMPONENT_KUKİSİ = "alqor_komponent"
KOMPONENT_AÇARI = re.compile(r"[A-Za-z0-9_-]{16,64}")
HADİSƏ_YOLU = "/_alqor/hadise"
# Bir qoşma üçün yaddaşda saxlanılan sessiya sayı və ömrü. Hədd
# keçiləndə ən köhnə sessiya atılır — kukisiz botlar yaddaşı doldura
# bilməsin.
MAKS_KOMPONENT_SESSİYASI = 1000
KOMPONENT_ÖMRÜ = 2 * 3600                # saniyə, son fəaliyyətdən


class _KomponentSessiyası:
    """Bir brauzer sessiyasının komponent nümunəsi və hadisə reyestri."""

    __slots__ = ("nümunə", "reyestr", "qıfıl", "son_istifadə")

    def __init__(self, nümunə: Nümunə):
        from .pencere import Reyestr
        self.nümunə = nümunə
        self.reyestr = Reyestr()
        # Bir sessiyanın hadisələri ardıcıl işləyir: iki sürətli klik
        # `vəziyyət`-i yarışa salmasın
        self.qıfıl = threading.Lock()
        self.son_istifadə = time.monotonic()

    def göstər(self, icraçı) -> str:
        from .pencere import HTML_ə
        n = self.nümunə
        göstər = n.sinif.metod_tap("göstər")
        if göstər is None:
            raise AlqorXəta(
                "TipXətası",
                f"`{n.sinif.ad}` komponentində `göstər()` metodu yoxdur",
                kod="ALQ-T053")
        n._keş.clear()
        ağac = icraçı.funksiya_çağır(göstər.bağla(n), [], {}, None)
        self.reyestr.sıfırla()
        return HTML_ə(ağac, self.reyestr, icraçı)

    def hadisəni_işlət(self, icraçı, açar: str, dəyər: Any) -> dict:
        self.son_istifadə = time.monotonic()
        idarəedici = self.reyestr.al(açar)
        if idarəedici is None:
            # Köhnə nəsildən gələn hadisə — yalnız HTML yenilənir
            return {"html": self.göstər(icraçı), "köhnə": True}
        arqumentlər = [] if dəyər is None else [dəyər]
        try:
            icraçı._çağır(idarəedici, arqumentlər, {}, None)
        except TypeError:
            icraçı._çağır(idarəedici, [], {}, None)
        return {"html": self.göstər(icraçı)}


class _KomponentQoşması:
    """`s.komponent(yol, mənbə)` — bir yol, çox sessiya."""

    __slots__ = ("nömrə", "yol", "mənbə", "başlıq", "üslub",
                 "_sessiyalar", "_qıfıl")

    def __init__(self, nömrə: int, yol: str, mənbə: Any, başlıq: str,
                 üslub: str):
        self.nömrə = nömrə
        self.yol = yol
        self.mənbə = mənbə
        self.başlıq = başlıq
        self.üslub = üslub
        self._sessiyalar: dict[str, _KomponentSessiyası] = {}
        self._qıfıl = threading.Lock()

    def _nümunə_yarat(self, icraçı) -> Nümunə:
        from .deyerler import Sinif
        m = self.mənbə
        if isinstance(m, Sinif):
            n = icraçı.nümunə_yarat(m, None, [], {}, None)
        else:
            n = icraçı._çağır(m, [], {}, None)
            if isinstance(n, Element) and n.komponent is not None:
                n = n.komponent                 # `() => <Panel />`
        if not isinstance(n, Nümunə) or \
                n.sinif.metod_tap("göstər") is None:
            raise AlqorXəta(
                "TipXətası",
                f"`{self.yol}` üçün komponent gözlənilirdi — "
                "`göstər()` metodu olan sinif və ya onun nümunəsini "
                "qaytaran funksiya verin", kod="ALQ-T053")
        return n

    def sessiya(self, açar: str, icraçı,
                yarat: bool) -> _KomponentSessiyası | None:
        indi = time.monotonic()
        with self._qıfıl:
            ss = self._sessiyalar.get(açar)
            if ss is not None and indi - ss.son_istifadə > KOMPONENT_ÖMRÜ:
                del self._sessiyalar[açar]
                ss = None
            if ss is not None:
                ss.son_istifadə = indi
                # Lüğətin sonuna keçir — ən yeni istifadə edilən
                self._sessiyalar[açar] = self._sessiyalar.pop(açar)
                return ss
            if not yarat:
                return None
        # Nümunə qıfılsız yaradılır: istifadəçi kodu uzun işləyə bilər
        ss = _KomponentSessiyası(self._nümunə_yarat(icraçı))
        with self._qıfıl:
            while len(self._sessiyalar) >= MAKS_KOMPONENT_SESSİYASI:
                self._sessiyalar.pop(next(iter(self._sessiyalar)))
            self._sessiyalar[açar] = ss
        return ss

    def sessiya_sayı(self) -> int:
        return len(self._sessiyalar)


def _veb_skripti() -> str:
    """
    Brauzer tərəfi: `pəncərə` modulunun ortaq nüvəsi (DOM yamağı +
    hadisə növbəsi) üstündə. Fərq yalnız göndərmədədir: komponent
    nömrəsi gövdəyə qoşulur, köhnəlmiş sessiyada səhifə yenidən
    yüklənir.
    """
    from .pencere import NÜVƏ_SKRİPTİ
    return (
        "(function(){" + NÜVƏ_SKRİPTİ +
        'const kök=document.getElementById("alqor-kök");'
        "const k=+kök.dataset.aKomponent;"
        "async function göndər(id,d){"
        f' const c=await fetch("{HADİSƏ_YOLU}",{{method:"POST",'
        '  credentials:"same-origin",'
        '  headers:{"Content-Type":"application/json"},'
        "  body:JSON.stringify({k:k,id:id,dəyər:d===undefined?null:d})});"
        " if(!c.ok){kök.insertAdjacentHTML(\"afterbegin\","
        "  '<p class=\"v-xəbərdarlıq v-xəbərdarlıq--təhlükə\">'+"
        "  'Server xətası: '+c.status+'</p>');return}"
        " const n=await c.json();"
        " if(n.yenidən){location.reload();return}"
        " if(n.html!==undefined)yamaq(kök,n.html);"
        "}"
        "alqorBağla(göndər);"
        "})();")


VEB_SKRİPTİ = _veb_skripti()


def _qaç(m: str) -> str:
    return (m.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


def _yolu_düzəlt(xam: str) -> str:
    """
    `BaseHTTPRequestHandler.path` xam baytları LATIN-1 kimi dekodlaşdırır.
    `/salam/Əli` yolu belə pozulur. Baytları geri alıb UTF-8 kimi
    oxuyuruq — bu olmasa Azərbaycan hərfli URL-lər işləməz.
    """
    try:
        return xam.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return xam


def yol_təhlükəlidir(yol: str) -> bool:
    """
    Sorğu yolu normallaşdırılmış formadadırmı?

    Marşrutlar və statik fayllar oxunmadan ƏVVƏL yoxlanılır. Bir yol
    normallaşdırılmış sayılmır — deməli rədd edilir — əgər onda:

    * NUL baytı var (fayl sistemi API-lərini çaşdırır),
    * tərs kəsik var (Windows-da qovluq ayırıcısıdır: `..\\gizli`),
    * `.` və ya `..` adlı seqment var (qovluqdan qaçmaq),
    * boş daxili seqment var (`//` — `....//` kimi fəndlər `..`-ni
      kəsən serverləri aldatmaq üçün yazılır; biz kəsmirik, amma
      belə yolu da qəbul etmirik).

    Rədd cavabı sorğu yolunu ƏKS ETDİRMİR — hücumçunun mətni
    cavabda görünməməlidir.
    """
    if not yol or "\x00" in yol or "\\" in yol:
        return True
    seqmentlər = yol.split("/")
    for i, s in enumerate(seqmentlər):
        if s in (".", ".."):
            return True
        if not s and 0 < i < len(seqmentlər) - 1:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════
#  Nəticənin cavaba çevrilməsi
# ═══════════════════════════════════════════════════════════════════════

def _cavaba_çevir(nəticə: Any, icraçı) -> Cavab:
    """İdarəedici `Cavab` qaytarmasa, dəyəri avtomatik çeviririk."""
    if isinstance(nəticə, Cavab):
        return nəticə
    if nəticə is None:
        return Cavab(b"", 204)
    if isinstance(nəticə, Element):
        return Cavab(nəticə.HTML(icraçı).encode("utf-8"), 200,
                     "text/html; charset=utf-8")
    if isinstance(nəticə, str):
        return Cavab(nəticə.encode("utf-8"), 200,
                     "text/html; charset=utf-8"
                     if nəticə.lstrip().startswith("<")
                     else "text/plain; charset=utf-8")
    if isinstance(nəticə, (dict, list, tuple, int, float, bool)):
        return _json_cavab(nəticə, icraçı)
    if isinstance(nəticə, Nümunə):
        return _json_cavab(nəticə, icraçı)
    return Cavab(mətnə(nəticə, icraçı).encode("utf-8"))


def _json_cavab(dəyər: Any, icraçı) -> Cavab:
    from .kitabxana import _json_hazırla
    gövdə = _json.dumps(_json_hazırla(dəyər, icraçı),
                        ensure_ascii=False).encode("utf-8")
    return Cavab(gövdə, 200, "application/json; charset=utf-8")


# ═══════════════════════════════════════════════════════════════════════
#  Cavab qurucuları
# ═══════════════════════════════════════════════════════════════════════

def c_mətn(icraçı, dəyər: Any) -> Cavab:
    return Cavab(mətnə(dəyər, icraçı).encode("utf-8"), 200,
                 "text/plain; charset=utf-8")


def c_html(icraçı, dəyər: Any) -> Cavab:
    gövdə = (dəyər.HTML(icraçı) if isinstance(dəyər, Element)
             else mətnə(dəyər, icraçı))
    # Tam sənəd verilirsə DOCTYPE lazımdır — onsuz brauzer «quirks»
    # rejiminə düşür və CSS fərqli hesablanır.
    kəsik = gövdə.lstrip()
    if kəsik[:5].lower() == "<html" and not kəsik[:9].lower().startswith(
            "<!doctype"):
        gövdə = "<!DOCTYPE html>" + chr(10) + gövdə
    return Cavab(gövdə.encode("utf-8"), 200,
                 "text/html; charset=utf-8")


def c_json(icraçı, dəyər: Any) -> Cavab:
    return _json_cavab(dəyər, icraçı)


def c_boş(kod: int = 204) -> Cavab:
    return Cavab(b"", int(kod))


def c_yönləndir(ünvan: str, kod: int = 302) -> Cavab:
    c = Cavab(b"", int(kod))
    c.başlıq("Location", str(ünvan))
    return c


def c_xəta(kod: int, mesaj: Any = "") -> Cavab:
    mətn = str(mesaj) or VƏZİYYƏT_MƏTNLƏRİ.get(int(kod), "Xəta")
    return Cavab(mətn.encode("utf-8"), int(kod),
                 "text/plain; charset=utf-8")


def c_fayl(icraçı, yol: str, ad: str = "") -> Cavab:
    p = qovluğu_həll(icraçı, yol)
    if not p.is_file():
        raise AlqorXəta("FaylTapılmadıXətası",
                        f'"{yol}" faylı tapılmadı', kod="ALQ-R009")
    tip = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    c = Cavab(p.read_bytes(), 200, tip)
    if ad:
        c.başlıq("Content-Disposition",
                 f'attachment; filename="{ad}"')
    return c


def c_şablon(icraçı, server_qovluğu: Path, yol: str,
             verilənlər: Any = None) -> Cavab:
    from .sablon import ŞablonXətası, şablonu_yüklə
    try:
        ş = şablonu_yüklə(yol, server_qovluğu)
        hazır = ş.göstər(icraçı, _lüğətə_çevir(verilənlər))
    except ŞablonXətası as x:
        raise AlqorXəta("FormatXətası", f"şablon xətası: {x}",
                        kod="ALQ-R005")
    return Cavab(hazır.encode("utf-8"), 200, "text/html; charset=utf-8")


def _lüğətə_çevir(verilənlər: Any) -> dict[str, Any]:
    if verilənlər is None:
        return {}
    if isinstance(verilənlər, dict):
        return {str(k): v for k, v in verilənlər.items()}
    if isinstance(verilənlər, Nümunə):
        return dict(verilənlər.sahələr)
    raise AlqorXəta("TipXətası",
                    f"şablon verilənləri lüğət olmalıdır, "
                    f"`{tip_adı(verilənlər)}` gəlib", kod="ALQ-T004")


# ═══════════════════════════════════════════════════════════════════════
#  Ara proqramlar
# ═══════════════════════════════════════════════════════════════════════

def ara_jurnal(icraçı):
    from .deyerler import Daxili

    def işlə(sorğu: Sorğu, növbəti) -> Cavab:
        başlanğıc = time.perf_counter()
        cavab = _cavaba_çevir(
            icraçı._çağır(növbəti, [sorğu], {}, None), icraçı)
        müddət = (time.perf_counter() - başlanğıc) * 1000
        rəng = ("\033[32m" if cavab.vəziyyət < 400
                else "\033[31m" if cavab.vəziyyət >= 500
                else "\033[33m")
        print(f"{rəng}{cavab.vəziyyət}\033[0m "
              f"{sorğu.metod():<7} {sorğu._yol:<32} "
              f"{müddət:7.2f} ms  {len(cavab.gövdə)} bayt")
        sys.stdout.flush()
        return cavab

    return Daxili("jurnal", işlə, 2, 2)


def ara_CORS(icraçı, mənbələr: Any = None, metodlar: Any = None):
    from .deyerler import Daxili
    icazəli = ", ".join(mənbələr) if isinstance(mənbələr, list) \
        else (mənbələr or "*")
    icazəli_metodlar = ", ".join(metodlar) if isinstance(metodlar, list) \
        else "GET, POST, PUT, PATCH, DELETE, OPTIONS"

    def işlə(sorğu: Sorğu, növbəti) -> Cavab:
        if sorğu._metod == "OPTIONS":
            cavab = Cavab(b"", 204)
        else:
            cavab = _cavaba_çevir(
                icraçı._çağır(növbəti, [sorğu], {}, None), icraçı)
        cavab.başlıq("Access-Control-Allow-Origin", icazəli)
        cavab.başlıq("Access-Control-Allow-Methods", icazəli_metodlar)
        cavab.başlıq("Access-Control-Allow-Headers",
                     "Content-Type, Authorization")
        return cavab

    return Daxili("CORS", işlə, 2, 2)


def ara_sıxma(icraçı, minimum: int = 512):
    from .deyerler import Daxili

    def işlə(sorğu: Sorğu, növbəti) -> Cavab:
        cavab = _cavaba_çevir(
            icraçı._çağır(növbəti, [sorğu], {}, None), icraçı)
        qəbul = sorğu.başlıq("accept-encoding", "") or ""
        tip = cavab.başlıqlar.get("Content-Type", "")
        sıxıla_bilər = (tip.startswith("text/")
                        or "json" in tip or "javascript" in tip
                        or "svg" in tip)
        if ("gzip" in qəbul and sıxıla_bilər
                and len(cavab.gövdə) >= minimum
                and "Content-Encoding" not in cavab.başlıqlar):
            cavab.gövdə = gzip.compress(cavab.gövdə, 6)
            cavab.başlıq("Content-Encoding", "gzip")
            cavab.başlıq("Vary", "Accept-Encoding")
        return cavab

    return Daxili("sıxma", işlə, 2, 2)


def ara_təhlükəsizlik(icraçı):
    from .deyerler import Daxili

    def işlə(sorğu: Sorğu, növbəti) -> Cavab:
        cavab = _cavaba_çevir(
            icraçı._çağır(növbəti, [sorğu], {}, None), icraçı)
        cavab.başlıq("X-Content-Type-Options", "nosniff")
        cavab.başlıq("X-Frame-Options", "DENY")
        cavab.başlıq("Referrer-Policy", "strict-origin-when-cross-origin")
        cavab.başlıq("X-XSS-Protection", "0")
        return cavab

    return Daxili("təhlükəsizlikBaşlıqları", işlə, 2, 2)


def ara_sürət_limiti(icraçı, say: int = 100, pəncərə: Any = "1dəq"):
    from .deyerler import Daxili
    saniyə = _müddəti_saniyəyə(pəncərə)
    qeydlər: dict[str, list[float]] = {}
    kilid = threading.Lock()

    def işlə(sorğu: Sorğu, növbəti) -> Cavab:
        indi = time.time()
        açar = sorğu.IP()
        with kilid:
            vaxtlar = [t for t in qeydlər.get(açar, [])
                       if indi - t < saniyə]
            if len(vaxtlar) >= int(say):
                qeydlər[açar] = vaxtlar
                c = Cavab(b"429 Too Many Requests", 429)
                c.başlıq("Retry-After", str(int(saniyə)))
                return c
            vaxtlar.append(indi)
            qeydlər[açar] = vaxtlar
        return _cavaba_çevir(
            icraçı._çağır(növbəti, [sorğu], {}, None), icraçı)

    return Daxili("sürətLimiti", işlə, 2, 2)


def _müddəti_saniyəyə(dəyər: Any) -> float:
    if isinstance(dəyər, (int, float)):
        return float(dəyər)
    m = str(dəyər).strip().lower()
    vahidlər = {"san": 1, "s": 1, "dəq": 60, "deq": 60, "dq": 60,
                "saat": 3600, "s/": 3600, "gün": 86400, "gun": 86400}
    for vahid, çarpan in sorted(vahidlər.items(),
                                key=lambda x: -len(x[0])):
        if m.endswith(vahid):
            rəqəm = m[:-len(vahid)].strip() or "1"
            try:
                return float(rəqəm) * çarpan
            except ValueError:
                return 60.0
    try:
        return float(m)
    except ValueError:
        return 60.0


def ara_sessiya(icraçı, gizli: Any = None):
    """Sessiya kukisini təmin edir (anbar serverin yaddaşındadır)."""
    from .deyerler import Daxili

    def işlə(sorğu: Sorğu, növbəti) -> Cavab:
        return _cavaba_çevir(
            icraçı._çağır(növbəti, [sorğu], {}, None), icraçı)

    return Daxili("sessiya", işlə, 2, 2)


# ═══════════════════════════════════════════════════════════════════════
#  Sınaq müştərisi
# ═══════════════════════════════════════════════════════════════════════

class SınaqMüştərisi:
    """Serveri port açmadan sınamaq üçün (`veb.sınaq.server`)."""

    __slots__ = ("_server", "_icraçı", "_kukilər")

    def __init__(self, server: Server, icraçı):
        self._server = server
        self._icraçı = icraçı
        self._kukilər: dict[str, str] = {}

    def _sorğu(self, metod: str, yol: str, gövdə: Any = None,
               başlıqlar: Any = None) -> Cavab:
        ayrılmış = urllib.parse.urlsplit(yol)
        xam = b""
        b = {"Host": "sınaq"}
        if self._kukilər:
            b["Cookie"] = "; ".join(f"{k}={v}" for k, v in
                                    self._kukilər.items())
        if isinstance(başlıqlar, dict):
            b.update({str(k): str(v) for k, v in başlıqlar.items()})
        if gövdə is not None:
            if isinstance(gövdə, (dict, list)):
                from .kitabxana import _json_hazırla
                xam = _json.dumps(_json_hazırla(gövdə, self._icraçı),
                                  ensure_ascii=False).encode("utf-8")
                b.setdefault("Content-Type", "application/json")
            else:
                xam = mətnə(gövdə, self._icraçı).encode("utf-8")

        sorğu = Sorğu(metod, urllib.parse.unquote(ayrılmış.path) or "/",
                      ayrılmış.query, b, xam, "127.0.0.1", self._server)
        sap = threading.get_ident()
        self._server._yeni_sessiyalar.pop(sap, None)
        try:
            cavab = self._server._idarə_et(sorğu)
        except AlqorXəta as x:
            cavab = self._server._alqor_xətası(sorğu, x)
        yeni = self._server._yeni_sessiyalar.pop(sap, None)
        if yeni:
            self._kukilər[SESSİYA_KUKİSİ] = yeni
        for k in cavab.kukilər:
            ad_dəyər = k.split(";")[0]
            if "=" in ad_dəyər:
                ad, dəyər = ad_dəyər.split("=", 1)
                if dəyər:
                    self._kukilər[ad] = dəyər
                else:
                    self._kukilər.pop(ad, None)
        return cavab

    def al(self, yol, başlıqlar=None):
        return self._sorğu("GET", yol, None, başlıqlar)

    def göndər(self, yol, gövdə=None, başlıqlar=None):
        return self._sorğu("POST", yol, gövdə, başlıqlar)

    def yenilə(self, yol, gövdə=None, başlıqlar=None):
        return self._sorğu("PUT", yol, gövdə, başlıqlar)

    def yamaq(self, yol, gövdə=None, başlıqlar=None):
        return self._sorğu("PATCH", yol, gövdə, başlıqlar)

    def sil(self, yol, başlıqlar=None):
        return self._sorğu("DELETE", yol, None, başlıqlar)

    def __repr__(self) -> str:
        return "<sınaq müştərisi>"


# ═══════════════════════════════════════════════════════════════════════
#  Boş port tapma (inkişaf üçün)
# ═══════════════════════════════════════════════════════════════════════

def boş_port(başlanğıc: int = 8080, cəhd: int = 50) -> int:
    for p in range(int(başlanğıc), int(başlanğıc) + cəhd):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return int(başlanğıc)
