"""
`http` — HTTP müştərisi (§ 10.12).

    gətir http

    dəyişən c = gözlə http.al("https://api.nümunə.az/istifadəçilər")
    yaz(c.kod())                       // 200
    yaz(c.json())

    gözlə http.göndər(url, json: {"ad": "Aysel"})
    gözlə http.göndər(url, forma: {"ad": "Aysel"})     // form-urlencoded
    gözlə http.yenilə(url, json: …)    // PUT
    gözlə http.yamaq(url, json: …)     // PATCH
    gözlə http.sil(url)

    dəyişən s = yeni http.Sorğu("GÖNDƏR", url)
    s.başlıq("Authorization", "Bearer {token}").json(verilənlər)
    s.vaxtLimiti(5000)
    dəyişən c = gözlə s.göndər()

    gözlə http.faylYüklə(url, "arxiv.zip", irəliləyiş: (faiz) => yaz("{faiz}%"))
    gözlə http.faylGöndər(url, "sənəd.pdf")            // multipart

Bütün funksiyalar `Gələcək` qaytarır — `gözlə` ilə həll olunur,
`paralel(...)` ilə eyni anda bir neçə sorğu getmək olar. 4xx/5xx
cavablar xəta deyil (`c.uğurlu()`, `c.yoxla()`); bağlantı problemi —
`BağlantıXətası`, vaxtın bitməsi — `VaxtBitdiXətası`.

Yalnız `http://` və `https://` ünvanlarına icazə var (`file://` yox).
"""

from __future__ import annotations

import json as _json
import mimetypes
import secrets
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı
from ..korutin import Gələcək

VERSİYA = "0.1.0"
İSTİFADƏÇİ_AGENTİ = f"Alqor-http/{VERSİYA}"

METODLAR = {
    "AL": "GET", "GÖNDƏR": "POST", "YENİLƏ": "PUT", "YAMAQ": "PATCH",
    "SİL": "DELETE", "BAŞLIQ": "HEAD", "SEÇİMLƏR": "OPTIONS",
    "GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH",
    "DELETE": "DELETE", "HEAD": "HEAD", "OPTIONS": "OPTIONS",
}


def _xəta(tip: str, mesaj: str) -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R010")


def _json_hazırla(x: Any) -> Any:
    if isinstance(x, Nümunə):
        return {a: _json_hazırla(d) for a, d in x.sahələr.items()}
    if isinstance(x, dict):
        return {str(a): _json_hazırla(d) for a, d in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_json_hazırla(d) for d in x]
    return x


# ── Cavab ─────────────────────────────────────────────────────────────

class Cavab:
    ALQOR_TİP_ADI = "httpCavabı"

    def __init__(self, kod: int, başlıqlar: dict[str, str], gövdə: bytes,
                 url: str):
        self.kod = kod
        self.başlıqlar = başlıqlar
        self.gövdə = gövdə
        self.url = url

    def __repr__(self) -> str:
        return f"<http cavabı {self.kod}>"

    def mətn(self) -> str:
        növ = self.başlıqlar.get("content-type", "")
        kodlaşdırma = "utf-8"
        if "charset=" in növ:
            kodlaşdırma = növ.split("charset=")[-1].split(";")[0].strip()
        try:
            return self.gövdə.decode(kodlaşdırma, errors="replace")
        except LookupError:
            return self.gövdə.decode("utf-8", errors="replace")

    def json(self) -> Any:
        try:
            return _json.loads(self.mətn())
        except _json.JSONDecodeError as x:
            raise AlqorXəta("JSONXətası", f"cavab JSON deyil (sətir "
                            f"{x.lineno}): {x.msg}", None, "ALQ-R005")

    def uğurlu(self) -> bool:
        return 200 <= self.kod < 300

    def yoxla(self) -> "Cavab":
        if not self.uğurlu():
            parça = self.mətn()[:200]
            raise AlqorXəta("HTTPXətası", f"{self.kod} — {self.url}"
                            + (f": {parça}" if parça else ""), None,
                            "ALQ-R010")
        return self


Cavab.ALQOR_METODLARI = {
    "kod": lambda i, c: c.kod,
    "uğurlu": lambda i, c: c.uğurlu(),
    "yoxla": lambda i, c: c.yoxla(),
    "mətn": lambda i, c: c.mətn(),
    "json": lambda i, c: c.json(),
    "bayt": lambda i, c: c.gövdə,
    "başlıq": lambda i, c, a, s=None: c.başlıqlar.get(str(a).lower(), s),
    "başlıqlar": lambda i, c: dict(c.başlıqlar),
    "url": lambda i, c: c.url,
}


# ── Sorğu ─────────────────────────────────────────────────────────────

class Sorğu:
    ALQOR_TİP_ADI = "httpSorğusu"

    def __init__(self, metod: str, url: str):
        m = METODLAR.get(str(metod).upper())
        if m is None:
            raise AlqorXəta("DəyərXətası", f"`{metod}` HTTP metodu deyil — "
                            "AL, GÖNDƏR, YENİLƏ, YAMAQ, SİL", None, "ALQ-T001")
        self.metod = m
        self.url = _url_yoxla(url)
        self.başlıqlar: dict[str, str] = {}
        self.parametrlər: list[tuple[str, str]] = []
        self.gövdə_: bytes | None = None
        self.vaxt = 30.0
        self.yönləndir = True
        self.irəliləyiş = None

    def başlıq(self, a: str, d: Any) -> "Sorğu":
        self.başlıqlar[str(a)] = str(d)
        return self

    def parametr(self, a: str, d: Any) -> "Sorğu":
        self.parametrlər.append((str(a), str(d)))
        return self

    def gövdə(self, x: Any) -> "Sorğu":
        if isinstance(x, bytes):
            self.gövdə_ = x
            self.başlıqlar.setdefault("Content-Type",
                                      "application/octet-stream")
        elif isinstance(x, str):
            self.gövdə_ = x.encode("utf-8")
            self.başlıqlar.setdefault("Content-Type",
                                      "text/plain; charset=utf-8")
        elif x is None:
            self.gövdə_ = None
        else:
            return self.json(x)
        return self

    def json(self, x: Any) -> "Sorğu":
        self.gövdə_ = _json.dumps(_json_hazırla(x),
                                  ensure_ascii=False).encode("utf-8")
        self.başlıqlar["Content-Type"] = "application/json; charset=utf-8"
        return self

    def forma(self, l: dict) -> "Sorğu":
        self.gövdə_ = urllib.parse.urlencode(
            [(str(a), str(d)) for a, d in l.items()]).encode()
        self.başlıqlar["Content-Type"] = "application/x-www-form-urlencoded"
        return self

    def vaxt_limiti(self, ms: int) -> "Sorğu":
        self.vaxt = max(0.001, int(ms) / 1000)
        return self

    def tam_url(self) -> str:
        if not self.parametrlər:
            return self.url
        ayırıcı = "&" if "?" in self.url else "?"
        return self.url + ayırıcı + urllib.parse.urlencode(self.parametrlər)

    def icra(self, hədəf_fayl: Path | None = None, çağır=None) -> Cavab:
        başlıqlar = {"User-Agent": İSTİFADƏÇİ_AGENTİ,
                     "Accept-Encoding": "identity", **self.başlıqlar}
        r = urllib.request.Request(self.tam_url(), data=self.gövdə_,
                                   method=self.metod, headers=başlıqlar)
        try:
            with _açıcı(self.yönləndir).open(r, timeout=self.vaxt) as c:
                return self._oxu(c, c.status, hədəf_fayl, çağır)
        except urllib.error.HTTPError as c:
            return self._oxu(c, c.code, None, None)
        except urllib.error.URLError as x:
            səbəb = x.reason
            if isinstance(səbəb, (socket.timeout, TimeoutError)):
                raise _xəta("VaxtBitdiXətası",
                            f"{self.url}: {self.vaxt:g} s ərzində cavab "
                            "gəlmədi")
            if isinstance(səbəb, ssl.SSLError):
                raise _xəta("BağlantıXətası",
                            f"{self.url}: TLS sertifikatı yoxlanmadı ({səbəb})")
            raise _xəta("BağlantıXətası", f"{self.url}: {səbəb}")
        except (socket.timeout, TimeoutError):
            raise _xəta("VaxtBitdiXətası",
                        f"{self.url}: {self.vaxt:g} s ərzində cavab gəlmədi")
        except (ConnectionError, OSError) as x:
            raise _xəta("BağlantıXətası", f"{self.url}: {x}")

    def _oxu(self, c, kod: int, hədəf_fayl, çağır) -> Cavab:
        başlıqlar = {a.lower(): d for a, d in c.headers.items()}
        if hədəf_fayl is None:
            return Cavab(kod, başlıqlar, c.read(), c.geturl())
        ümumi = int(başlıqlar.get("content-length", "0") or 0)
        alınan = 0
        son_faiz = -1
        müvəqqəti = hədəf_fayl.with_name(hədəf_fayl.name + ".yüklənir")
        try:
            with open(müvəqqəti, "wb") as f:
                while blok := c.read(64 * 1024):
                    f.write(blok)
                    alınan += len(blok)
                    if çağır and ümumi:
                        faiz = alınan * 100 // ümumi
                        if faiz != son_faiz:
                            son_faiz = faiz
                            çağır(faiz)
            müvəqqəti.replace(hədəf_fayl)
        finally:
            if müvəqqəti.exists():
                müvəqqəti.unlink()
        if çağır and son_faiz != 100:
            çağır(100)
        return Cavab(kod, başlıqlar, b"", c.geturl())


def _url_yoxla(url: Any) -> str:
    if not isinstance(url, str):
        raise AlqorXəta("TipXətası", f"URL mətn olmalıdır, `{tip_adı(url)}` "
                        "gəlib", None, "ALQ-T001")
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise AlqorXəta("DəyərXətası", f"`{url}` — yalnız http:// və "
                        "https:// ünvanlarına icazə var", None, "ALQ-T001")
    # Azərbaycan hərfli domen (IDN) və yol: `nümunə.az/şəkil`
    host = p.hostname.encode("idna").decode() if p.hostname else ""
    netloc = host + (f":{p.port}" if p.port else "")
    if p.username:
        netloc = f"{p.username}:{p.password or ''}@{netloc}"
    yol = urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~")
    sorğu = urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?-._~")
    return urllib.parse.urlunsplit((p.scheme, netloc, yol, sorğu,
                                    p.fragment))


class _YalnızHTTP(urllib.request.HTTPRedirectHandler):
    """Yönləndirmə `file://` və ya başqa sxemə apara bilməz."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme not in ("http", "https"):
            raise _xəta("BağlantıXətası", f"təhlükəli yönləndirmə: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _Yönləndirməsiz(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _açıcı(yönləndir: bool):
    return urllib.request.build_opener(
        _YalnızHTTP if yönləndir else _Yönləndirməsiz)


def _sorğu(metod: str, url: str, gövdə: Any = None, json: Any = None,
           forma: Any = None, başlıqlar: dict | None = None,
           parametrlər: dict | None = None, vaxtLimiti: int | None = None,
           yönləndir: bool = True) -> Sorğu:
    s = Sorğu(metod, url)
    for a, d in (başlıqlar or {}).items():
        s.başlıq(a, d)
    for a, d in (parametrlər or {}).items():
        s.parametr(a, d)
    if json is not None:
        s.json(json)
    elif forma is not None:
        s.forma(forma)
    elif gövdə is not None:
        s.gövdə(gövdə)
    if vaxtLimiti is not None:
        s.vaxt_limiti(vaxtLimiti)
    s.yönləndir = bool(yönləndir)
    return s


def _gələcək(s: Sorğu, **k) -> Gələcək:
    return Gələcək(lambda: s.icra(**k), f"http {s.metod} {s.url}")


def _multipart(yol: Path, sahə: str, əlavə: dict) -> tuple[bytes, str]:
    sərhəd = "alqor-" + secrets.token_hex(12)
    hissələr: list[bytes] = []
    for a, d in əlavə.items():
        hissələr.append(
            f'--{sərhəd}\r\nContent-Disposition: form-data; name="{a}"'
            f"\r\n\r\n{d}\r\n".encode())
    növ = mimetypes.guess_type(yol.name)[0] or "application/octet-stream"
    ad = yol.name.replace('"', "")
    hissələr.append(
        f'--{sərhəd}\r\nContent-Disposition: form-data; name="{sahə}"; '
        f"filename*=UTF-8''{urllib.parse.quote(ad)}; "
        f'filename="{ad}"\r\nContent-Type: {növ}\r\n\r\n'.encode()
        + yol.read_bytes() + b"\r\n")
    hissələr.append(f"--{sərhəd}--\r\n".encode())
    return b"".join(hissələr), f"multipart/form-data; boundary={sərhəd}"


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    def metod(m):
        return lambda url, **k: _gələcək(_sorğu(m, url, **k))

    def fayl_yüklə(url, yol, irəliləyiş=None, **k):
        s = _sorğu("GET", url, **k)
        çağır = (lambda f: icraçı._çağır(irəliləyiş, [f], {}, None)) \
            if irəliləyiş is not None else None

        def iş():
            c = s.icra(Path(yol), çağır)
            return c.yoxla() if not c.uğurlu() else c
        return Gələcək(iş, f"http yüklə {url}")

    def fayl_göndər(url, yol, sahə="fayl", əlavə=None, **k):
        p = Path(yol)
        if not p.is_file():
            raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" tapılmadı',
                            None, "ALQ-R009")
        s = _sorğu("POST", url, **k)
        gövdə, növ = _multipart(p, sahə, əlavə or {})
        s.gövdə_ = gövdə
        s.başlıqlar["Content-Type"] = növ
        return _gələcək(s)

    return {
        "al": D("al", metod("GET"), 1, 1),
        "göndər": D("göndər", metod("POST"), 1, 1),
        "yenilə": D("yenilə", metod("PUT"), 1, 1),
        "yamaq": D("yamaq", metod("PATCH"), 1, 1),
        "sil": D("sil", metod("DELETE"), 1, 1),
        "başlıq": D("başlıq", metod("HEAD"), 1, 1),
        "Sorğu": D("Sorğu", Sorğu, 2, 2),
        "faylYüklə": D("faylYüklə", fayl_yüklə, 2, 2),
        "faylGöndər": D("faylGöndər", fayl_göndər, 2, 2),
    }


Sorğu.ALQOR_METODLARI = {
    "başlıq": lambda i, s, a, d: s.başlıq(a, d),
    "parametr": lambda i, s, a, d: s.parametr(a, d),
    "gövdə": lambda i, s, x: s.gövdə(x),
    "json": lambda i, s, x: s.json(x),
    "forma": lambda i, s, l: s.forma(l),
    "vaxtLimiti": lambda i, s, ms: s.vaxt_limiti(ms),
    "göndər": lambda i, s: _gələcək(s),
    "url": lambda i, s: s.tam_url(),
    "metod": lambda i, s: s.metod,
}


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    m = T.MƏTN
    G = T.Gələcək(T.Sadə("httpCavabı"))
    return {
        "al": Fsərbəst(G), "göndər": Fsərbəst(G), "yenilə": Fsərbəst(G),
        "yamaq": Fsərbəst(G), "sil": Fsərbəst(G), "başlıq": Fsərbəst(G),
        "Sorğu": F(m, m, qaytarır=T.Sadə("httpSorğusu")),
        "faylYüklə": Fsərbəst(G), "faylGöndər": Fsərbəst(G),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, b = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.MƏNTİQ
    C = T.Sadə("httpCavabı")
    S = T.Sadə("httpSorğusu")
    return {
        "httpCavabı": {
            "kod": F(qaytarır=i), "uğurlu": F(qaytarır=b),
            "yoxla": F(qaytarır=C), "mətn": F(qaytarır=m),
            "json": F(qaytarır=e), "bayt": F(qaytarır=T.BAYT),
            "başlıq": F(m, e, qaytarır=T.ixtiyari(m), standart=1),
            "başlıqlar": F(qaytarır=T.Lüğət(m, m)), "url": F(qaytarır=m),
        },
        "httpSorğusu": {
            "başlıq": F(m, e, qaytarır=S), "parametr": F(m, e, qaytarır=S),
            "gövdə": F(e, qaytarır=S), "json": F(e, qaytarır=S),
            "forma": F(T.Lüğət(), qaytarır=S),
            "vaxtLimiti": F(i, qaytarır=S),
            "göndər": F(qaytarır=T.Gələcək(C)),
            "url": F(qaytarır=m), "metod": F(qaytarır=m),
        },
    }
