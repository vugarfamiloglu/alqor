"""
PostgreSQL sürücüsü — frontend/backend protokolu v3, saf Python.

    postgres://istifadəçi:parol@host:5432/baza?sslmode=prefer

Autentifikasiya: SCRAM-SHA-256 (PostgreSQL 14+ standartı), md5, açıq
parol (yalnız TLS-də tövsiyə olunur). TLS: `sslmode=disable | prefer
(standart) | require | verify-full`.

Sorğular genişlənmiş protokolla gedir (Parse/Bind/Execute): parametrlər
SQL mətnindən AYRI göndərilir — inyeksiya mümkün deyil. Nəticə sütunları
tip OID-inə görə Alqor dəyərlərinə çevrilir.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json as _json
import os
import socket
import ssl
import struct
from typing import Any

from ._vb_ortaq import (MəhdudiyyətPozuldu, Nəticə, SürücüXətası, ünvanı_ayır)

_TAM = {20, 21, 23, 26, 28}
_ONLUQ = {700, 701}
_JSON = {114, 3802}


def _cstr(s: str) -> bytes:
    return s.encode("utf-8") + b"\0"


class PgSürücü:
    ad = "postgres"
    sitat = '"'

    def __init__(self, ünvan: str):
        u = ünvanı_ayır(ünvan, 5432)
        self.istifadəçi = u.istifadəçi or os.environ.get("PGUSER", "postgres")
        self.parol = u.parol if u.parol is not None else \
            os.environ.get("PGPASSWORD", "")
        self.baza = u.baza or self.istifadəçi
        rejim = u.seçimlər.get("sslmode", "prefer")
        try:
            self.s = socket.create_connection(
                (u.host, u.port), timeout=float(u.seçimlər.get(
                    "connect_timeout", 15)))
        except OSError as x:
            raise SürücüXətası(f"{u.host}:{u.port} — {x}") from None
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._bufer = bytearray()
        if rejim != "disable":
            self._tls(u.host, rejim)
        self.s.settimeout(None)
        self.parametrlər: dict[str, str] = {}
        self._başla()

    # ── Nəqliyyat ─────────────────────────────────────────────────────

    def _tls(self, host: str, rejim: str) -> None:
        self.s.sendall(struct.pack("!ii", 8, 80877103))
        cavab = self.s.recv(1)
        if cavab == b"S":
            k = ssl.create_default_context()
            if rejim != "verify-full":
                # libpq-dəki kimi: require/prefer şifrələyir, sertifikatı
                # yoxlamır; verify-full yoxlayır
                k.check_hostname = False
                k.verify_mode = ssl.CERT_NONE
            try:
                self.s = k.wrap_socket(self.s, server_hostname=host)
            except (ssl.SSLError, OSError) as x:
                raise SürücüXətası(f"TLS alınmadı: {x}") from None
        elif rejim in ("require", "verify-full"):
            raise SürücüXətası("server TLS-i dəstəkləmir (sslmode="
                               f"{rejim})")

    def _oxu(self, n: int) -> bytes:
        while len(self._bufer) < n:
            try:
                p = self.s.recv(max(65536, n - len(self._bufer)))
            except OSError as x:
                raise SürücüXətası(f"bağlantı qırıldı: {x}") from None
            if not p:
                raise SürücüXətası("server bağlantını bağladı")
            self._bufer += p
        d = bytes(self._bufer[:n])
        del self._bufer[:n]
        return d

    def _mesaj(self) -> tuple[bytes, bytes]:
        növ = self._oxu(1)
        uzunluq = struct.unpack("!i", self._oxu(4))[0]
        return növ, self._oxu(uzunluq - 4)

    def _göndər(self, *mesajlar: tuple[bytes, bytes]) -> None:
        b = b"".join(n + struct.pack("!i", len(d) + 4) + d
                     for n, d in mesajlar)
        try:
            self.s.sendall(b)
        except OSError as x:
            raise SürücüXətası(f"bağlantı qırıldı: {x}") from None

    @staticmethod
    def _xəta_sahələri(d: bytes) -> dict[str, str]:
        n = {}
        for hissə in d.split(b"\0"):
            if hissə:
                n[chr(hissə[0])] = hissə[1:].decode("utf-8", "replace")
        return n

    def _xəta(self, d: bytes) -> Exception:
        f = self._xəta_sahələri(d)
        kod = f.get("C", "")
        mesaj = f.get("M", "naməlum xəta")
        if f.get("D"):
            mesaj += f" ({f['D']})"
        if kod.startswith("23"):
            return MəhdudiyyətPozuldu(f"[{kod}] {mesaj}")
        return SürücüXətası(f"[{kod}] {mesaj}")

    # ── Başlanğıc, autentifikasiya ────────────────────────────────────

    def _başla(self) -> None:
        gövdə = (struct.pack("!i", 196608) + _cstr("user")
                 + _cstr(self.istifadəçi) + _cstr("database")
                 + _cstr(self.baza) + _cstr("client_encoding") + _cstr("UTF8")
                 + _cstr("application_name") + _cstr("alqor") + b"\0")
        self.s.sendall(struct.pack("!i", len(gövdə) + 4) + gövdə)
        scram = None
        while True:
            n, d = self._mesaj()
            if n == b"R":
                kod = struct.unpack("!i", d[:4])[0]
                if kod == 0:
                    continue
                if kod == 3:
                    self._göndər((b"p", _cstr(self.parol)))
                elif kod == 5:
                    duz = d[4:8]
                    iç = hashlib.md5((self.parol + self.istifadəçi).encode(
                        "utf-8")).hexdigest()
                    xaric = hashlib.md5(iç.encode() + duz).hexdigest()
                    self._göndər((b"p", _cstr("md5" + xaric)))
                elif kod == 10:
                    mexanizmlər = [x.decode() for x in d[4:].split(b"\0")
                                   if x]
                    if "SCRAM-SHA-256" not in mexanizmlər:
                        raise SürücüXətası("SASL mexanizmi dəstəklənmir: "
                                           + ", ".join(mexanizmlər))
                    scram = _Scram(self.parol)
                    ilk = scram.ilk_mesaj().encode()
                    self._göndər((b"p", _cstr("SCRAM-SHA-256")
                                  + struct.pack("!i", len(ilk)) + ilk))
                elif kod == 11:
                    self._göndər((b"p", scram.son_mesaj(d[4:].decode())
                                  .encode()))
                elif kod == 12:
                    scram.yoxla(d[4:].decode())
                else:
                    raise SürücüXətası(f"autentifikasiya növü {kod} "
                                       "dəstəklənmir")
            elif n == b"S":
                a, b, _ = d.split(b"\0", 2)
                self.parametrlər[a.decode()] = b.decode()
            elif n == b"K":
                pass
            elif n == b"Z":
                return
            elif n == b"E":
                raise self._xəta(d)
            elif n == b"N":
                pass

    # ── Sorğular ──────────────────────────────────────────────────────

    @staticmethod
    def _param(x: Any) -> bytes | None:
        if x is None:
            return None
        if x is True:
            return b"true"
        if x is False:
            return b"false"
        if isinstance(x, (bytes, bytearray)):
            return b"\\x" + bytes(x).hex().encode()
        if isinstance(x, float):
            if x != x or x in (float("inf"), float("-inf")):
                return {"nan": b"NaN", "inf": b"Infinity",
                        "-inf": b"-Infinity"}[repr(x)]
            return repr(x).encode()
        return str(x).encode("utf-8")

    def icra(self, sql: str, parametrlər: tuple) -> Nəticə:
        """`$1, $2…` parametrli bir əmr (genişlənmiş protokol)."""
        bind = struct.pack("!hh", 0, len(parametrlər))
        for p in parametrlər:
            b = self._param(p)
            bind += struct.pack("!i", -1) if b is None else \
                struct.pack("!i", len(b)) + b
        bind = b"\0\0" + bind + struct.pack("!h", 0)
        self._göndər((b"P", b"\0" + _cstr(sql) + struct.pack("!h", 0)),
                     (b"B", bind), (b"D", b"P\0"),
                     (b"E", b"\0" + struct.pack("!i", 0)), (b"S", b""))
        return self._nəticələr()[-1]

    def skript(self, sql: str) -> list[Nəticə]:
        """Bir neçə əmr (sadə protokol) — miqrasiyalar üçün."""
        self._göndər((b"Q", _cstr(sql)))
        return self._nəticələr()

    def _nəticələr(self) -> list[Nəticə]:
        nəticələr: list[Nəticə] = []
        cari = Nəticə()
        oidlər: list[int] = []
        xəta: Exception | None = None
        while True:
            n, d = self._mesaj()
            if n == b"T":
                say = struct.unpack("!h", d[:2])[0]
                i = 2
                cari.sütunlar, oidlər = [], []
                for _ in range(say):
                    j = d.index(b"\0", i)
                    cari.sütunlar.append(d[i:j].decode("utf-8"))
                    oid = struct.unpack("!i", d[j + 7:j + 11])[0]
                    oidlər.append(oid)
                    i = j + 19
            elif n == b"D":
                say = struct.unpack("!h", d[:2])[0]
                i = 2
                sətir = []
                for k in range(say):
                    u = struct.unpack("!i", d[i:i + 4])[0]
                    i += 4
                    if u < 0:
                        sətir.append(None)
                        continue
                    sətir.append(_çevir(oidlər[k], d[i:i + u]))
                    i += u
                cari.sətirlər.append(tuple(sətir))
            elif n == b"C":
                etiket = d.rstrip(b"\0").decode()
                h = etiket.split()
                if h and h[-1].isdigit():
                    cari.say = int(h[-1])
                nəticələr.append(cari)
                cari = Nəticə()
            elif n in (b"I", b"n"):
                if n == b"I":
                    nəticələr.append(cari)
                    cari = Nəticə()
            elif n == b"E":
                xəta = xəta or self._xəta(d)
            elif n == b"Z":
                if xəta is not None:
                    raise xəta
                return nəticələr or [cari]
            # 1, 2, 3, N, S, s — ötürülür

    def bağla(self) -> None:
        try:
            self._göndər((b"X", b""))
        except SürücüXətası:
            pass
        try:
            self.s.close()
        except OSError:
            pass

    # ── Dialekt ───────────────────────────────────────────────────────

    def limit(self, limit: int | None, atla: int | None) -> str:
        s = ""
        if limit is not None:
            s += f" LIMIT {int(limit)}"
        if atla is not None:
            s += f" OFFSET {int(atla)}"
        return s

    def cədvəllər_sql(self) -> str:
        return ("SELECT table_name FROM information_schema.tables WHERE "
                "table_schema = current_schema() AND table_type = "
                "'BASE TABLE' ORDER BY table_name")

    def sütunlar_sql(self) -> str:
        return ("SELECT c.column_name AS ad, c.data_type AS tip, "
                "c.is_nullable = 'YES' AS boş, EXISTS (SELECT 1 FROM "
                "information_schema.key_column_usage k JOIN "
                "information_schema.table_constraints t ON "
                "t.constraint_name = k.constraint_name AND t.table_schema = "
                "k.table_schema WHERE t.constraint_type = 'PRIMARY KEY' AND "
                "k.table_name = c.table_name AND k.column_name = "
                "c.column_name AND k.table_schema = c.table_schema) AS açar "
                "FROM information_schema.columns c WHERE c.table_schema = "
                "current_schema() AND c.table_name = $1 ORDER BY "
                "c.ordinal_position")

    qaytarma = True                   # INSERT … RETURNING

    def tip(self, növ: str, açar: bool) -> str:
        if açar and növ == "tam":
            return "BIGSERIAL PRIMARY KEY"
        return {"tam": "BIGINT", "onluq": "DOUBLE PRECISION",
                "məntiq": "BOOLEAN", "bayt": "BYTEA"}.get(növ, "TEXT") + \
            (" PRIMARY KEY" if açar else "")


def _çevir(oid: int, d: bytes) -> Any:
    if oid in _TAM:
        return int(d)
    if oid == 16:
        return d == b"t"
    if oid in _ONLUQ:
        return float(d)
    if oid == 1700:
        m = d.decode()
        return int(m) if m.lstrip("-").isdigit() else float(m)
    if oid == 17:
        m = d.decode()
        return bytes.fromhex(m[2:]) if m.startswith("\\x") else d
    if oid in _JSON:
        try:
            return _json.loads(d)
        except ValueError:
            return d.decode("utf-8", "replace")
    return d.decode("utf-8", "replace")


class _Scram:
    """SCRAM-SHA-256 (RFC 5802, 7677) — kanal bağlaması olmadan."""

    def __init__(self, parol: str):
        self.parol = parol
        self.nonce = base64.b64encode(os.urandom(18)).decode()
        self.ilk_bare = f"n=,r={self.nonce}"

    def ilk_mesaj(self) -> str:
        return "n,," + self.ilk_bare

    def son_mesaj(self, server_ilk: str) -> str:
        a = dict(x.split("=", 1) for x in server_ilk.split(","))
        if not a["r"].startswith(self.nonce):
            raise SürücüXətası("SCRAM: server nonce-u yanlışdır")
        duz = base64.b64decode(a["s"])
        say = int(a["i"])
        self.duzlu = hashlib.pbkdf2_hmac("sha256", _saslprep(self.parol)
                                         .encode("utf-8"), duz, say)
        müştəri_açarı = hmac.new(self.duzlu, b"Client Key",
                                 hashlib.sha256).digest()
        saxlanan = hashlib.sha256(müştəri_açarı).digest()
        sonsuz = f"c=biws,r={a['r']}"
        self.auth = f"{self.ilk_bare},{server_ilk},{sonsuz}".encode()
        imza = hmac.new(saxlanan, self.auth, hashlib.sha256).digest()
        sübut = bytes(x ^ y for x, y in zip(müştəri_açarı, imza))
        return f"{sonsuz},p={base64.b64encode(sübut).decode()}"

    def yoxla(self, server_son: str) -> None:
        a = dict(x.split("=", 1) for x in server_son.split(","))
        server_açarı = hmac.new(self.duzlu, b"Server Key",
                                hashlib.sha256).digest()
        gözlənilən = hmac.new(server_açarı, self.auth, hashlib.sha256).digest()
        if not hmac.compare_digest(base64.b64decode(a.get("v", "")),
                                   gözlənilən):
            raise SürücüXətası("SCRAM: serverin imzası yanlışdır")


def _saslprep(s: str) -> str:
    """Sadələşdirilmiş SASLprep: NFKC (PostgreSQL ASCII olmayan parolları
    da belə normallaşdırır)."""
    import unicodedata
    return unicodedata.normalize("NFKC", s)
