"""
Alqor — `alqorhub`: paket deposu serveri (Spesifikasiya § 8.9).

    alqor hub --qovluq hub-məlumat --port 8790 [--host 0.0.0.0]
              [--admin ad1,ad2]

Xarici asılılıq yoxdur: `http.server` + SQLite. Arxivlər
`<qovluq>/fayllar/` altında, metaməlumat `<qovluq>/hub.db`-dədir.

HTTP API (JSON, UTF-8):

    GET  /api/paketlər?q=söz               axtarış
    GET  /api/paket/<ad>                   metaməlumat + versiyalar
    GET  /api/paket/<ad>/<versiya>/fayl    arxiv (.tar.gz)
    PUT  /api/paket/<ad>/<versiya>         yayımla (Authorization: Bearer)
    POST /api/paket/<ad>/<versiya>/geri-çək   {"geri": doğru|yanlış}
    POST /api/paket/<ad>/sahib             {"istifadəçi": …, "sil": yanlış}
    POST /api/qeydiyyat | /api/giriş       {"ad": …, "parol": …} → nişan
    GET  /api/xəbərdarlıqlar               təhlükəsizlik xəbərdarlıqları
    POST /api/xəbərdarlıqlar               (admin) yeni xəbərdarlıq

Veb səhifələr: `/` (axtarış, ən yenilər), `/paket/<ad>` (README,
versiyalar, quraşdırma əmri).

Qaydalar: eyni versiya iki dəfə yayımlanmır (dəyişməzlik); versiya
silinmir, yalnız geri çəkilir; ilk yayımlayan sahib olur; arxivdəki
`layihe.alq` ad/versiyası URL ilə üst-üstə düşməlidir; arxivdə mütləq
yol, `..`, keçid və cihaz faylı rədd edilir.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .alqorpm import MAKS_ARXİV, PMXətası, arxiv_manifesti
from .paketler import Aralıq, Versiya, VersiyaXətası, ad_yoxla

_SXEM = """
CREATE TABLE IF NOT EXISTS istifadəçilər (
    ad TEXT PRIMARY KEY, duz BLOB, həzm BLOB, yaradılıb INTEGER);
CREATE TABLE IF NOT EXISTS nişanlar (
    həzm TEXT PRIMARY KEY, istifadəçi TEXT, yaradılıb INTEGER);
CREATE TABLE IF NOT EXISTS paketlər (
    ad TEXT PRIMARY KEY, təsvir TEXT, yaradılıb INTEGER,
    endirmə INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sahiblər (
    paket TEXT, istifadəçi TEXT, PRIMARY KEY (paket, istifadəçi));
CREATE TABLE IF NOT EXISTS versiyalar (
    paket TEXT, versiya TEXT, sha256 TEXT, ölçü INTEGER, manifest TEXT,
    readme TEXT, yayımlayan TEXT, tarix INTEGER,
    geri_çəkilib INTEGER DEFAULT 0, PRIMARY KEY (paket, versiya));
CREATE TABLE IF NOT EXISTS xəbərdarlıqlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT, paket TEXT, aralıq TEXT,
    səviyyə TEXT, başlıq TEXT, təsvir TEXT, düzəlib TEXT, tarix INTEGER);
"""


class HubXətası(Exception):
    def __init__(self, kod: int, mesaj: str):
        super().__init__(mesaj)
        self.kod = kod


def _parol_həzmi(parol: str, duz: bytes) -> bytes:
    return hashlib.scrypt(parol.encode("utf-8"), salt=duz, n=2 ** 14, r=8,
                          p=1, dklen=32)


class Hub:
    """Depo məntiqi (HTTP-dən asılı deyil — sınaqlar birbaşa işlədir)."""

    def __init__(self, qovluq: Path | str, adminlər: set[str] | None = None):
        self.qovluq = Path(qovluq)
        (self.qovluq / "fayllar").mkdir(parents=True, exist_ok=True)
        self.adminlər = adminlər or set()
        self._kilid = threading.Lock()
        self.db = sqlite3.connect(self.qovluq / "hub.db",
                                  check_same_thread=False)
        self.db.executescript(_SXEM)

    def _q(self, sql: str, *p) -> list[tuple]:
        with self._kilid:
            c = self.db.execute(sql, p)
            n = c.fetchall()
            self.db.commit()
            return n

    # ── Hesablar ──────────────────────────────────────────────────────
    def qeydiyyat(self, ad: str, parol: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9əıöüğşçƏIİÖÜĞŞÇ_-]{2,39}", ad or ""):
            raise HubXətası(400, "istifadəçi adı 2–39 simvol: hərf, rəqəm, "
                                 "_ və -")
        if len(parol or "") < 8:
            raise HubXətası(400, "parol ən azı 8 simvol olmalıdır")
        duz = secrets.token_bytes(16)
        try:
            self._q("INSERT INTO istifadəçilər VALUES (?, ?, ?, ?)", ad, duz,
                    _parol_həzmi(parol, duz), int(time.time()))
        except sqlite3.IntegrityError:
            raise HubXətası(409, f"`{ad}` adı artıq tutulub")
        return self._nişan_yarat(ad)

    def giriş(self, ad: str, parol: str) -> str:
        r = self._q("SELECT duz, həzm FROM istifadəçilər WHERE ad = ?", ad)
        if not r or not hmac.compare_digest(
                _parol_həzmi(parol or "", r[0][0]), r[0][1]):
            time.sleep(0.2)
            raise HubXətası(401, "istifadəçi adı və ya parol yanlışdır")
        return self._nişan_yarat(ad)

    def _nişan_yarat(self, ad: str) -> str:
        n = "alq_" + secrets.token_urlsafe(32)
        self._q("INSERT INTO nişanlar VALUES (?, ?, ?)",
                hashlib.sha256(n.encode()).hexdigest(), ad, int(time.time()))
        return n

    def kim(self, nişan: str | None) -> str | None:
        if not nişan:
            return None
        r = self._q("SELECT istifadəçi FROM nişanlar WHERE həzm = ?",
                    hashlib.sha256(nişan.encode()).hexdigest())
        return r[0][0] if r else None

    # ── Paketlər ──────────────────────────────────────────────────────
    def sahiblər(self, ad: str) -> list[str]:
        return [r[0] for r in self._q(
            "SELECT istifadəçi FROM sahiblər WHERE paket = ? ORDER BY 1", ad)]

    def _fayl(self, ad: str, versiya: str) -> Path:
        return self.qovluq / "fayllar" / ad.replace("/", "%") / \
            f"{versiya}.tar.gz"

    def yayımla(self, istifadəçi: str | None, ad: str, versiya: str,
                data: bytes) -> dict:
        if istifadəçi is None:
            raise HubXətası(401, "giriş tələb olunur (alqorpm giriş)")
        try:
            ad_yoxla(ad)
            v = Versiya.oxu(versiya)
        except VersiyaXətası as x:
            raise HubXətası(400, str(x))
        if str(v) != versiya:
            raise HubXətası(400, f"versiya tam formada olmalıdır: {v}")
        if len(data) > MAKS_ARXİV:
            raise HubXətası(413, "arxiv çox böyükdür")
        try:
            m = arxiv_manifesti(data)
            self._arxivi_yoxla(data)
        except PMXətası as x:
            raise HubXətası(400, str(x))
        except Exception:                               # noqa: BLE001
            raise HubXətası(400, "arxiv oxunmadı (.tar.gz gözlənilir)")
        p = m.get("paket") or {}
        if str(p.get("ad")) != ad or str(p.get("versiya")) != versiya:
            raise HubXətası(400, f"manifestdəki ad/versiya "
                                 f"({p.get('ad')}@{p.get('versiya')}) URL "
                                 f"ilə uyğun deyil ({ad}@{versiya})")
        for a, d in (m.get("asılılıqlar") or {}).items():
            if isinstance(d, dict) and ("yol" in d or "qit" in d):
                raise HubXətası(400, f"`{a}`: yol/qit asılılığı ilə "
                                     "yayımlamaq olmaz")
            try:
                Aralıq(d if isinstance(d, str) else d.get("versiya", "*"))
            except VersiyaXətası as x:
                raise HubXətası(400, f"`{a}`: {x}")
        sahiblər = self.sahiblər(ad)
        if sahiblər and istifadəçi not in sahiblər:
            raise HubXətası(403, f"`{ad}` paketinin sahibi deyilsiniz")
        if self._q("SELECT 1 FROM versiyalar WHERE paket = ? AND "
                   "versiya = ?", ad, versiya):
            raise HubXətası(409, f"{ad}@{versiya} artıq yayımlanıb — "
                                 "versiyanı artırın (alqorpm versiya patch)")
        f = self._fayl(ad, versiya)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        readme = _readme(data)
        indi = int(time.time())
        təsvir = str(p.get("təsvir") or "")
        if not sahiblər:
            self._q("INSERT OR IGNORE INTO paketlər VALUES (?, ?, ?, 0)", ad,
                    təsvir, indi)
            self._q("INSERT INTO sahiblər VALUES (?, ?)", ad, istifadəçi)
        self._q("UPDATE paketlər SET təsvir = ? WHERE ad = ?", təsvir, ad)
        self._q("INSERT INTO versiyalar VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                ad, versiya, hashlib.sha256(data).hexdigest(), len(data),
                json.dumps(m, ensure_ascii=False), readme, istifadəçi, indi)
        return {"ad": ad, "versiya": versiya,
                "sha256": hashlib.sha256(data).hexdigest()}

    @staticmethod
    def _arxivi_yoxla(data: bytes) -> None:
        import io
        import tarfile
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            for m in t.getmembers():
                if not m.name.startswith("paket/") or ".." in \
                        m.name.split("/") or not (m.isfile() or m.isdir()):
                    raise PMXətası(f"arxivdə icazəsiz element: {m.name}")

    def meta(self, ad: str, kök_url: str = "") -> dict:
        p = self._q("SELECT təsvir, endirmə FROM paketlər WHERE ad = ?", ad)
        if not p:
            raise HubXətası(404, f"`{ad}` paketi tapılmadı")
        vs = {}
        son = None
        for versiya, sha, ölçü, man, yay, tarix, geri in self._q(
                "SELECT versiya, sha256, ölçü, manifest, yayımlayan, tarix, "
                "geri_çəkilib FROM versiyalar WHERE paket = ?", ad):
            m = json.loads(man)
            vs[versiya] = {
                "sha256": sha, "ölçü": ölçü, "yayımlayan": yay,
                "tarix": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime(tarix)),
                "geri_çəkilib": bool(geri),
                "asılılıqlar": {a: (d if isinstance(d, str) else
                                    d.get("versiya", "*"))
                                for a, d in (m.get("asılılıqlar") or
                                             {}).items()},
                "fayl": f"{kök_url}/api/paket/"
                        f"{urllib.parse.quote(ad, safe='@')}/{versiya}/fayl"}
            v = Versiya.oxu(versiya)
            if not geri and not v.ön and (son is None or v > son):
                son = v
        son_m = {}
        if son is not None:
            son_m = json.loads(self._q(
                "SELECT manifest FROM versiyalar WHERE paket = ? AND "
                "versiya = ?", ad, str(son))[0][0]).get("paket") or {}
        return {"ad": ad, "təsvir": p[0][0], "endirmə": p[0][1],
                "son": str(son) if son else None,
                "lisenziya": son_m.get("lisenziya"),
                "depo_url": son_m.get("depo"),
                "sahiblər": self.sahiblər(ad), "versiyalar": vs}

    def fayl(self, ad: str, versiya: str) -> bytes:
        f = self._fayl(ad, versiya)
        if not self._q("SELECT 1 FROM versiyalar WHERE paket = ? AND "
                       "versiya = ?", ad, versiya) or not f.is_file():
            raise HubXətası(404, f"{ad}@{versiya} tapılmadı")
        self._q("UPDATE paketlər SET endirmə = endirmə + 1 WHERE ad = ?", ad)
        return f.read_bytes()

    def axtar(self, q: str, hədd: int = 50) -> list[dict]:
        q = (q or "").strip().lower()
        sətirlər = self._q("SELECT ad, təsvir, endirmə FROM paketlər")
        n = []
        for ad, təsvir, endirmə in sətirlər:
            if q and q not in ad.lower() and q not in (təsvir or "").lower():
                continue
            m = self.meta(ad)
            n.append({"ad": ad, "təsvir": təsvir, "son": m["son"],
                      "endirmə": endirmə})
        n.sort(key=lambda x: (not x["ad"].lower().startswith(q),
                              -x["endirmə"], x["ad"]))
        return n[:hədd]

    def geri_çək(self, istifadəçi: str | None, ad: str, versiya: str,
                 geri: bool) -> None:
        if istifadəçi is None:
            raise HubXətası(401, "giriş tələb olunur")
        if istifadəçi not in self.sahiblər(ad) and \
                istifadəçi not in self.adminlər:
            raise HubXətası(403, "yalnız sahib geri çəkə bilər")
        if not self._q("SELECT 1 FROM versiyalar WHERE paket = ? AND "
                       "versiya = ?", ad, versiya):
            raise HubXətası(404, f"{ad}@{versiya} tapılmadı")
        self._q("UPDATE versiyalar SET geri_çəkilib = ? WHERE paket = ? AND "
                "versiya = ?", int(geri), ad, versiya)

    def sahib(self, istifadəçi: str | None, ad: str, digər: str,
              sil: bool) -> list[str]:
        if istifadəçi not in self.sahiblər(ad):
            raise HubXətası(403, "yalnız sahib dəyişə bilər")
        if not self._q("SELECT 1 FROM istifadəçilər WHERE ad = ?", digər):
            raise HubXətası(404, f"`{digər}` istifadəçisi yoxdur")
        if sil:
            if len(self.sahiblər(ad)) == 1:
                raise HubXətası(400, "son sahibi silmək olmaz")
            self._q("DELETE FROM sahiblər WHERE paket = ? AND istifadəçi = ?",
                    ad, digər)
        else:
            self._q("INSERT OR IGNORE INTO sahiblər VALUES (?, ?)", ad, digər)
        return self.sahiblər(ad)

    def xəbərdarlıqlar(self) -> list[dict]:
        return [{"id": i, "paket": p, "aralıq": a, "səviyyə": s,
                 "başlıq": b, "təsvir": t, "düzəlib": d,
                 "tarix": time.strftime("%Y-%m-%d", time.gmtime(tr))}
                for i, p, a, s, b, t, d, tr in self._q(
                    "SELECT * FROM xəbərdarlıqlar ORDER BY id")]

    def xəbərdarlıq_əlavə(self, istifadəçi: str | None, d: dict) -> dict:
        if istifadəçi not in self.adminlər:
            raise HubXətası(403, "yalnız admin xəbərdarlıq əlavə edə bilər")
        try:
            Aralıq(str(d.get("aralıq", "*")))
        except VersiyaXətası as x:
            raise HubXətası(400, str(x))
        if d.get("səviyyə") not in ("aşağı", "orta", "yüksək", "kritik"):
            raise HubXətası(400, "səviyyə: aşağı | orta | yüksək | kritik")
        self._q("INSERT INTO xəbərdarlıqlar (paket, aralıq, səviyyə, başlıq, "
                "təsvir, düzəlib, tarix) VALUES (?, ?, ?, ?, ?, ?, ?)",
                str(d.get("paket")), str(d.get("aralıq", "*")),
                d["səviyyə"], str(d.get("başlıq", "")),
                str(d.get("təsvir", "")), str(d.get("düzəlib") or ""),
                int(time.time()))
        return self.xəbərdarlıqlar()[-1]


def _readme(data: bytes) -> str:
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        for ad in ("paket/README.md", "paket/OXUYUN.md", "paket/readme.md"):
            try:
                return t.extractfile(ad).read().decode("utf-8", "replace")[
                    :200_000]
            except KeyError:
                continue
    return ""


# ═══════════════════════════════════════════════════════════════════════
#  Veb səhifələr
# ═══════════════════════════════════════════════════════════════════════

_ÜSLUB = """
:root{--fon:#f8fafc;--kart:#fff;--mətn:#0f172a;--sönük:#64748b;--kənar:#e2e8f0;
--əsas:#2563eb}
@media(prefers-color-scheme:dark){:root{--fon:#0b1120;--kart:#111827;
--mətn:#e5e7eb;--sönük:#94a3b8;--kənar:#1f2937;--əsas:#60a5fa}}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 system-ui,-apple-system,
Segoe UI,Roboto,sans-serif;background:var(--fon);color:var(--mətn)}
header{background:var(--kart);border-bottom:1px solid var(--kənar)}
.iç{max-width:960px;margin:0 auto;padding:16px}
header .iç{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
a{color:var(--əsas);text-decoration:none}a:hover{text-decoration:underline}
.loqo{font-weight:700;font-size:20px;color:var(--mətn)}
form{flex:1;display:flex;min-width:220px}input{flex:1;padding:9px 12px;
border:1px solid var(--kənar);border-radius:8px;background:var(--fon);
color:var(--mətn);font:inherit}
.kart{background:var(--kart);border:1px solid var(--kənar);border-radius:10px;
padding:14px 16px;margin:10px 0}
.kart h3{margin:0 0 4px;font-size:16px}.sönük{color:var(--sönük);font-size:13px}
code,pre{font-family:ui-monospace,Consolas,monospace;font-size:13px}
pre{background:var(--fon);border:1px solid var(--kənar);border-radius:8px;
padding:10px 12px;overflow-x:auto}
.cərgə{display:grid;grid-template-columns:1fr 260px;gap:20px}
@media(max-width:760px){.cərgə{grid-template-columns:1fr}}
.nişan{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;
background:var(--fon);border:1px solid var(--kənar);margin-left:6px}
"""


def _md(mətn: str) -> str:
    """Sadə Markdown → HTML (başlıq, kod bloku, siyahı, abzas, keçid)."""
    n, kod, siyahı = [], None, False

    def sətir(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                   r'<a href="\2" rel="nofollow noopener">\1</a>', s)
        return s
    for s in mətn.split("\n"):
        if s.startswith("```"):
            if kod is None:
                kod = []
            else:
                n.append("<pre><code>" + html.escape("\n".join(kod)) +
                         "</code></pre>")
                kod = None
            continue
        if kod is not None:
            kod.append(s)
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        li = re.match(r"^\s*[-*]\s+(.*)", s)
        if siyahı and not li:
            n.append("</ul>")
            siyahı = False
        if m:
            k = len(m.group(1)) + 1
            n.append(f"<h{k}>{sətir(m.group(2))}</h{k}>")
        elif li:
            if not siyahı:
                n.append("<ul>")
                siyahı = True
            n.append(f"<li>{sətir(li.group(1))}</li>")
        elif s.strip():
            n.append(f"<p>{sətir(s)}</p>")
    if siyahı:
        n.append("</ul>")
    if kod is not None:
        n.append("<pre><code>" + html.escape("\n".join(kod)) +
                 "</code></pre>")
    return "\n".join(n)


def _səhifə(başlıq: str, gövdə: str, q: str = "") -> bytes:
    return (f"<!doctype html><html lang=\"az\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,"
            f"initial-scale=1\"><title>{html.escape(başlıq)} — alqorhub"
            f"</title><style>{_ÜSLUB}</style></head><body><header><div "
            f"class=\"iç\"><a class=\"loqo\" href=\"/\">alqorhub</a>"
            f"<form action=\"/\"><input name=\"q\" value=\"{html.escape(q)}\""
            f" placeholder=\"Paket axtar…\" aria-label=\"Paket axtar\">"
            f"</form></div></header><main class=\"iç\">{gövdə}</main>"
            f"</body></html>").encode("utf-8")


def ana_səhifə(hub: Hub, q: str) -> bytes:
    n = hub.axtar(q)
    kartlar = "".join(
        f'<div class="kart"><h3><a href="/paket/{urllib.parse.quote(x["ad"], safe="@")}">'
        f'{html.escape(x["ad"])}</a><span class="nişan">'
        f'{html.escape(x["son"] or "—")}</span></h3><div>'
        f'{html.escape(x["təsvir"] or "")}</div><div class="sönük">'
        f'{x["endirmə"]} endirmə</div></div>' for x in n)
    başlıq = f"«{html.escape(q)}» üçün {len(n)} nəticə" if q else \
        f"{len(n)} paket"
    return _səhifə("Paketlər", f"<h2>{başlıq}</h2>{kartlar or '<p>Heç nə tapılmadı.</p>'}", q)


def paket_səhifəsi(hub: Hub, ad: str) -> bytes:
    m = hub.meta(ad)
    son = m["son"]
    readme = ""
    if son:
        r = hub._q("SELECT readme FROM versiyalar WHERE paket = ? AND "
                   "versiya = ?", ad, son)
        readme = _md(r[0][0]) if r and r[0][0] else ""
    vs = sorted(m["versiyalar"], key=Versiya.oxu, reverse=True)
    versiyalar = "".join(
        f"<li>{html.escape(v)}"
        f"{' <span class=nişan>geri çəkilib</span>' if m['versiyalar'][v]['geri_çəkilib'] else ''}"
        f" <span class=sönük>{m['versiyalar'][v]['tarix'][:10]}</span></li>"
        for v in vs[:30])
    yan = (f'<div class="kart"><b>Quraşdırma</b><pre>alqorpm əlavə '
           f'{html.escape(ad)}</pre><b>İstifadə</b><pre>gətir '
           f'{html.escape(ad) if not ad.startswith("@") else html.escape(chr(34) + ad + chr(34)) + " kimi m"}'
           f'</pre><div class="sönük">Sahiblər: '
           f'{html.escape(", ".join(m["sahiblər"]))}<br>'
           f'Lisenziya: {html.escape(str(m.get("lisenziya") or "—"))}<br>'
           f'Endirmə: {m["endirmə"]}</div></div>'
           f'<div class="kart"><b>Versiyalar</b><ul>{versiyalar}</ul></div>')
    gövdə = (f"<h1>{html.escape(ad)} <span class=nişan>"
             f"{html.escape(son or '—')}</span></h1>"
             f"<p class=sönük>{html.escape(m['təsvir'] or '')}</p>"
             f"<div class=cərgə><div class=kart>{readme or '<p class=sönük>README yoxdur.</p>'}</div>"
             f"<div>{yan}</div></div>")
    return _səhifə(ad, gövdə)


# ═══════════════════════════════════════════════════════════════════════
#  HTTP
# ═══════════════════════════════════════════════════════════════════════

def işləyici_sinfi(hub: Hub):
    class İşləyici(BaseHTTPRequestHandler):
        server_version = "alqorhub/1"
        protocol_version = "HTTP/1.1"

        def log_message(self, *a) -> None:              # sakit
            if os.environ.get("ALQORHUB_JURNAL"):
                super().log_message(*a)

        def _cavab(self, kod: int, gövdə: bytes, növ: str) -> None:
            self.send_response(kod)
            self.send_header("Content-Type", növ)
            self.send_header("Content-Length", str(len(gövdə)))
            self.send_header("X-Content-Type-Options", "nosniff")
            if növ.startswith("text/html"):
                self.send_header("Content-Security-Policy",
                                 "default-src 'none'; style-src "
                                 "'unsafe-inline'; img-src https: data:")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(gövdə)

        def _json(self, kod: int, d: Any) -> None:
            self._cavab(kod, json.dumps(d, ensure_ascii=False).encode(
                "utf-8"), "application/json; charset=utf-8")

        def _gövdə(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAKS_ARXİV + 1024:
                raise HubXətası(413, "sorğu çox böyükdür")
            return self.rfile.read(n) if n else b""

        def _istifadəçi(self) -> str | None:
            a = self.headers.get("Authorization") or ""
            return hub.kim(a[7:].strip()) if a.startswith("Bearer ") else None

        def _yol(self) -> tuple[list[str], dict]:
            u = urllib.parse.urlsplit(self.path)
            hissələr = [urllib.parse.unquote(h) for h in u.path.split("/")
                        if h]
            # `@sahə/ad` iki hissədir — birləşdir
            n = []
            for h in hissələr:
                if len(n) >= 2 and n[-2] == "paket" and \
                        n[-1].startswith("@") and "/" not in n[-1]:
                    n[-1] += "/" + h
                else:
                    n.append(h)
            return n, dict(urllib.parse.parse_qsl(u.query))

        def _işlə(self) -> None:
            try:
                h, sorğu = self._yol()
                kök = f"http://{self.headers.get('Host', 'localhost')}"
                if h[:1] == ["api"]:
                    return self._api(h[1:], sorğu, kök)
                if self.command not in ("GET", "HEAD"):
                    raise HubXətası(405, "icazəsiz üsul")
                if not h:
                    return self._cavab(200, ana_səhifə(hub, sorğu.get("q", "")),
                                       "text/html; charset=utf-8")
                if h[0] == "paket" and len(h) == 2:
                    return self._cavab(200, paket_səhifəsi(hub, h[1]),
                                       "text/html; charset=utf-8")
                raise HubXətası(404, "səhifə tapılmadı")
            except HubXətası as x:
                if (self._yol()[0][:1] or [""])[0] == "api":
                    self._json(x.kod, {"xəta": str(x)})
                else:
                    self._cavab(x.kod, _səhifə("Xəta", f"<h2>{x.kod}</h2>"
                                               f"<p>{html.escape(str(x))}</p>"),
                                "text/html; charset=utf-8")
            except (ValueError, KeyError) as x:
                self._json(400, {"xəta": f"yanlış sorğu: {x}"})

        def _api(self, h: list[str], sorğu: dict, kök: str) -> None:
            ü = self.command
            if h == ["paketlər"] and ü == "GET":
                return self._json(200, {"nəticə": hub.axtar(sorğu.get("q",
                                                                      ""))})
            if h in (["qeydiyyat"], ["giriş"]) and ü == "POST":
                d = json.loads(self._gövdə() or b"{}")
                f = hub.qeydiyyat if h == ["qeydiyyat"] else hub.giriş
                return self._json(201 if h == ["qeydiyyat"] else 200,
                                  {"nişan": f(str(d.get("ad", "")),
                                              str(d.get("parol", "")))})
            if h == ["xəbərdarlıqlar"]:
                if ü == "GET":
                    return self._json(200, hub.xəbərdarlıqlar())
                if ü == "POST":
                    return self._json(201, hub.xəbərdarlıq_əlavə(
                        self._istifadəçi(), json.loads(self._gövdə())))
            if h[:1] == ["paket"] and len(h) >= 2:
                ad = h[1]
                if len(h) == 2 and ü in ("GET", "HEAD"):
                    return self._json(200, hub.meta(ad, kök))
                if len(h) == 3 and h[2] == "sahib" and ü == "POST":
                    d = json.loads(self._gövdə())
                    return self._json(200, {"sahiblər": hub.sahib(
                        self._istifadəçi(), ad, str(d.get("istifadəçi")),
                        bool(d.get("sil")))})
                if len(h) == 3 and ü == "PUT":
                    return self._json(201, hub.yayımla(
                        self._istifadəçi(), ad, h[2], self._gövdə()))
                if len(h) == 4 and h[3] == "fayl" and ü in ("GET", "HEAD"):
                    return self._cavab(200, hub.fayl(ad, h[2]),
                                       "application/gzip")
                if len(h) == 4 and h[3] == "geri-çək" and ü == "POST":
                    d = json.loads(self._gövdə() or b"{}")
                    hub.geri_çək(self._istifadəçi(), ad, h[2],
                                 bool(d.get("geri", True)))
                    return self._json(200, {"ok": True})
            raise HubXətası(404, "API ünvanı tapılmadı")

        do_GET = do_POST = do_PUT = do_HEAD = _işlə

    return İşləyici


def server(hub: Hub, host: str = "127.0.0.1", port: int = 8790
           ) -> ThreadingHTTPServer:
    s = ThreadingHTTPServer((host, port), işləyici_sinfi(hub))
    s.daemon_threads = True
    return s


def əsas(arqumentlər: list[str]) -> int:
    qovluq, host, port, adminlər = "hub-məlumat", "127.0.0.1", 8790, set()
    i = 0
    while i < len(arqumentlər):
        a = arqumentlər[i]
        v = arqumentlər[i + 1] if i + 1 < len(arqumentlər) else ""
        if a == "--qovluq":
            qovluq, i = v, i + 1
        elif a == "--host":
            host, i = v, i + 1
        elif a == "--port":
            port, i = int(v), i + 1
        elif a == "--admin":
            adminlər = {x.strip() for x in v.split(",") if x.strip()}
            i += 1
        elif a in ("--kömək", "-k"):
            print(__doc__)
            return 0
        i += 1
    hub = Hub(qovluq, adminlər)
    s = server(hub, host, port)
    print(f"alqorhub: http://{host}:{s.server_address[1]}/  "
          f"(məlumat: {Path(qovluq).resolve()})")
    print(f"  istifadə: ALQORHUB=http://{host}:{s.server_address[1]} "
          "alqorpm …   (dayandırmaq: Ctrl+C)")
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":                              # pragma: no cover
    sys.exit(əsas(sys.argv[1:]))
