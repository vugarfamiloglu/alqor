"""
MySQL / MariaDB sürücüsü — client/server protokolu 4.1+, saf Python.

    mysql://istifadəçi:parol@host:3306/baza?ssl=true

Autentifikasiya: `mysql_native_password` (MariaDB standartı),
`caching_sha2_password` (MySQL 8 standartı: sürətli yol; tam yol TLS
üzərində və ya serverin RSA açarı ilə). TLS: `ssl=true`.

Parametrlər müştəri tərəfində TƏHLÜKƏSİZ literala çevrilir (PyMySQL kimi):
mətn qaçış simvolları ilə, bayt `X'…'`, ədəd yoxlanılmış formada —
serverin `NO_BACKSLASH_ESCAPES` rejimi də nəzərə alınır.
"""

from __future__ import annotations

import hashlib
import json as _json
import socket
import ssl
import struct
from typing import Any

from ._vb_ortaq import (MəhdudiyyətPozuldu, Nəticə, SürücüXətası,
                        parametrləri_gəz, ünvanı_ayır)

# İmkan bayraqları
_UZUN_PAROL, _UZUN_BAYRAQ, _BAZA_İLƏ = 0x1, 0x4, 0x8
_PROTOKOL_41, _SSL, _TRANZAKSİYA, _TƏHLÜKƏSİZ = 0x200, 0x800, 0x2000, 0x8000
_ÇOX_ƏMR, _ÇOX_NƏTİCƏ, _PLAGİN = 0x10000, 0x20000, 0x80000
_LENENC_AUTH = 0x200000
_DAHA_ÇOX_NƏTİCƏ = 0x08
_ƏKS_XƏTSİZ = 0x200                  # SERVER_STATUS_NO_BACKSLASH_ESCAPES
UTF8MB4 = 45                         # utf8mb4_general_ci (MySQL və MariaDB)

_TAM = {1, 2, 3, 8, 9, 13}
_ONLUQ = {4, 5}
_DECİMAL = {0, 246}
_BLOB = {249, 250, 251, 252, 253, 254, 15}
_MƏHDUDİYYƏT = {1048, 1062, 1169, 1216, 1217, 1451, 1452, 1557, 1586,
                3819, 4025}


class MySürücü:
    ad = "mysql"
    sitat = "`"

    def __init__(self, ünvan: str):
        u = ünvanı_ayır(ünvan, 3306)
        self.istifadəçi = u.istifadəçi or "root"
        self.parol = u.parol or ""
        self.baza = u.baza
        try:
            self.s = socket.create_connection(
                (u.host, u.port), timeout=float(u.seçimlər.get(
                    "connect_timeout", 15)))
        except OSError as x:
            raise SürücüXətası(f"{u.host}:{u.port} — {x}") from None
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._bufer = bytearray()
        self.seq = 0
        self.status = 0
        self.tls = False
        self._host = u.host
        self._tls_istə = u.seçimlər.get("ssl", "").lower() in (
            "1", "true", "bəli", "required", "require")
        self._əl_sıxma()
        self.s.settimeout(None)

    # ── Paketlər ──────────────────────────────────────────────────────

    def _oxu_bayt(self, n: int) -> bytes:
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

    def _paket(self) -> bytes:
        gövdə = b""
        while True:
            baş = self._oxu_bayt(4)
            n = baş[0] | baş[1] << 8 | baş[2] << 16
            self.seq = (baş[3] + 1) & 0xFF
            gövdə += self._oxu_bayt(n)
            if n < 0xFFFFFF:
                return gövdə

    def _yaz(self, d: bytes) -> None:
        b = b""
        while True:
            parça, d = d[:0xFFFFFF], d[0xFFFFFF:]
            b += struct.pack("<I", len(parça))[:3] + bytes([self.seq]) + parça
            self.seq = (self.seq + 1) & 0xFF
            if len(parça) < 0xFFFFFF:
                break
        try:
            self.s.sendall(b)
        except OSError as x:
            raise SürücüXətası(f"bağlantı qırıldı: {x}") from None

    def _xəta(self, p: bytes) -> Exception:
        kod = struct.unpack("<H", p[1:3])[0]
        mesaj = p[9:].decode("utf-8", "replace") if p[3:4] == b"#" else \
            p[3:].decode("utf-8", "replace")
        if kod in _MƏHDUDİYYƏT:
            return MəhdudiyyətPozuldu(f"[{kod}] {mesaj}")
        return SürücüXətası(f"[{kod}] {mesaj}")

    # ── Əl sıxma ──────────────────────────────────────────────────────

    def _əl_sıxma(self) -> None:
        p = self._paket()
        if p[0] == 0xFF:
            raise self._xəta(p)
        if p[0] != 10:
            raise SürücüXətası(f"protokol versiyası {p[0]} dəstəklənmir")
        i = p.index(b"\0", 1)
        self.server_versiyası = p[1:i].decode()
        i += 1 + 4
        nonce = p[i:i + 8]
        i += 9
        imkan = struct.unpack("<H", p[i:i + 2])[0]
        i += 2 + 1 + 2
        imkan |= struct.unpack("<H", p[i:i + 2])[0] << 16
        i += 2
        auth_uz = p[i]
        i += 1 + 10
        if imkan & _TƏHLÜKƏSİZ:
            n = max(13, auth_uz - 8)
            nonce += p[i:i + n].rstrip(b"\0")
            i += n
        plagin = "mysql_native_password"
        if imkan & _PLAGİN and i < len(p):
            plagin = p[i:p.index(b"\0", i) if b"\0" in p[i:] else len(p)
                       ].decode()

        bayraq = (_UZUN_PAROL | _UZUN_BAYRAQ | _PROTOKOL_41 | _TRANZAKSİYA
                  | _TƏHLÜKƏSİZ | _ÇOX_ƏMR | _ÇOX_NƏTİCƏ | _PLAGİN
                  | _LENENC_AUTH)
        if self.baza:
            bayraq |= _BAZA_İLƏ
        if self._tls_istə:
            if not imkan & _SSL:
                raise SürücüXətası("server TLS-i dəstəkləmir")
            bayraq |= _SSL
            self._yaz(struct.pack("<IIB", bayraq, 1 << 24, UTF8MB4)
                      + b"\0" * 23)
            try:
                k = ssl.create_default_context()
                k.check_hostname = False
                k.verify_mode = ssl.CERT_NONE
                self.s = k.wrap_socket(self.s, server_hostname=self._host)
            except (ssl.SSLError, OSError) as x:
                raise SürücüXətası(f"TLS alınmadı: {x}") from None
            self.tls = True
        cavab = self._auth(plagin, nonce)
        d = (struct.pack("<IIB", bayraq, 1 << 24, UTF8MB4) + b"\0" * 23
             + self.istifadəçi.encode("utf-8") + b"\0"
             + _lenenc(len(cavab)) + cavab)
        if self.baza:
            d += self.baza.encode("utf-8") + b"\0"
        d += plagin.encode() + b"\0"
        self._yaz(d)
        self._auth_sonu(plagin, nonce)

    def _auth(self, plagin: str, nonce: bytes) -> bytes:
        pw = self.parol.encode("utf-8")
        if not pw:
            return b""
        if plagin == "mysql_native_password":
            a = hashlib.sha1(pw).digest()
            b = hashlib.sha1(nonce[:20] + hashlib.sha1(a).digest()).digest()
            return bytes(x ^ y for x, y in zip(a, b))
        if plagin == "caching_sha2_password":
            a = hashlib.sha256(pw).digest()
            b = hashlib.sha256(hashlib.sha256(a).digest()
                               + nonce[:20]).digest()
            return bytes(x ^ y for x, y in zip(a, b))
        if plagin == "mysql_clear_password":
            if not self.tls:
                raise SürücüXətası("açıq parol yalnız TLS ilə göndərilir "
                                   "(?ssl=true)")
            return pw + b"\0"
        raise SürücüXətası(f"autentifikasiya plagini dəstəklənmir: {plagin}")

    def _auth_sonu(self, plagin: str, nonce: bytes) -> None:
        while True:
            p = self._paket()
            if p[0] == 0x00:
                self._ok(p)
                return
            if p[0] == 0xFF:
                raise self._xəta(p)
            if p[0] == 0xFE:                     # AuthSwitchRequest
                j = p.index(b"\0", 1)
                plagin = p[1:j].decode()
                nonce = p[j + 1:].rstrip(b"\0")
                self._yaz(self._auth(plagin, nonce))
                continue
            if p[0] == 0x01 and plagin == "caching_sha2_password":
                if p[1:2] == b"\x03":                # sürətli yol uğurlu
                    continue
                if p[1:2] == b"\x04":                # tam autentifikasiya
                    pw = self.parol.encode("utf-8") + b"\0"
                    if self.tls:
                        self._yaz(pw)
                    else:
                        self._yaz(b"\x02")             # açıq açarı istə
                        pem = self._paket()[1:]
                        şifrəli = _rsa_oaep(pem, bytes(
                            x ^ nonce[i % len(nonce)]
                            for i, x in enumerate(pw)))
                        self._yaz(şifrəli)
                    continue
            raise SürücüXətası(f"gözlənilməz autentifikasiya paketi "
                               f"0x{p[0]:02x}")

    def _ok(self, p: bytes) -> tuple[int, int]:
        i = 1
        say, i = _lenenc_oxu(p, i)
        son_id, i = _lenenc_oxu(p, i)
        if i + 2 <= len(p):
            self.status = struct.unpack("<H", p[i:i + 2])[0]
        return say, son_id

    # ── Sorğular ──────────────────────────────────────────────────────

    def literal(self, x: Any) -> str:
        if x is None:
            return "NULL"
        if x is True:
            return "1"
        if x is False:
            return "0"
        if isinstance(x, int):
            return str(int(x))
        if isinstance(x, float):
            if x != x or x in (float("inf"), float("-inf")):
                raise SürücüXətası("MySQL NaN/sonsuzluq saxlaya bilmir")
            return repr(x)
        if isinstance(x, (bytes, bytearray)):
            return "X'" + bytes(x).hex() + "'"
        s = str(x)
        if self.status & _ƏKS_XƏTSİZ:
            return "'" + s.replace("'", "''") + "'"
        return "'" + s.translate(_QAÇIŞ) + "'"

    def icra(self, sql: str, parametrlər: tuple) -> Nəticə:
        ardıcıl = iter(range(len(parametrlər)))

        def əvəz(növ: str, n: int | None) -> str:
            if növ == "$":
                if not 1 <= n <= len(parametrlər):
                    raise SürücüXətası(f"${n} parametri verilməyib")
                return self.literal(parametrlər[n - 1])
            try:
                return self.literal(parametrlər[next(ardıcıl)])
            except StopIteration:
                raise SürücüXətası("`?` parametrləri çatışmır") from None
        hazır = parametrləri_gəz(sql, əvəz, mysql=True) if parametrlər \
            else sql
        return self._sorğu(hazır)[-1]

    def skript(self, sql: str) -> list[Nəticə]:
        return self._sorğu(sql)

    def _sorğu(self, sql: str) -> list[Nəticə]:
        self.seq = 0
        self._yaz(b"\x03" + sql.encode("utf-8"))
        nəticələr = []
        xəta = None
        while True:
            p = self._paket()
            if p[0] == 0xFF:
                xəta = self._xəta(p)
                break
            if p[0] == 0x00:
                say, son_id = self._ok(p)
                nəticələr.append(Nəticə(say=say, son_id=son_id or None))
            elif p[0] == 0xFB:
                raise SürücüXətası("LOCAL INFILE dəstəklənmir")
            else:
                nəticələr.append(self._nəticə_dəsti(p))
            if not self.status & _DAHA_ÇOX_NƏTİCƏ:
                break
        if xəta is not None:
            raise xəta
        return nəticələr

    def _nəticə_dəsti(self, p: bytes) -> Nəticə:
        say, _ = _lenenc_oxu(p, 0)
        n = Nəticə(say=0)
        tiplər: list[tuple[int, int, int]] = []
        for _ in range(say):
            c = self._paket()
            i = 0
            dəyərlər = []
            for _ in range(6):
                u, i = _lenenc_oxu(c, i)
                dəyərlər.append(c[i:i + u])
                i += u
            i += 1                                   # 0x0c
            charset, _, tip, bayraq = struct.unpack("<HIBH", c[i:i + 9])
            n.sütunlar.append(dəyərlər[4].decode("utf-8"))
            tiplər.append((tip, charset, bayraq))
        p = self._paket()                            # EOF
        if p[0] == 0xFE and len(p) >= 5:
            self.status = struct.unpack("<H", p[3:5])[0]
        while True:
            p = self._paket()
            if p[0] == 0xFE and len(p) < 9:
                self.status = struct.unpack("<H", p[3:5])[0]
                break
            if p[0] == 0xFF:
                raise self._xəta(p)
            sətir = []
            i = 0
            for tip, charset, bayraq in tiplər:
                if p[i] == 0xFB:
                    sətir.append(None)
                    i += 1
                    continue
                u, i = _lenenc_oxu(p, i)
                sətir.append(_çevir(tip, charset, p[i:i + u]))
                i += u
            n.sətirlər.append(tuple(sətir))
        n.say = len(n.sətirlər)
        return n

    def bağla(self) -> None:
        try:
            self.seq = 0
            self._yaz(b"\x01")
        except SürücüXətası:
            pass
        try:
            self.s.close()
        except OSError:
            pass

    # ── Dialekt ───────────────────────────────────────────────────────

    def limit(self, limit: int | None, atla: int | None) -> str:
        if limit is None and atla is None:
            return ""
        s = f" LIMIT {int(limit) if limit is not None else 18446744073709551615}"
        if atla is not None:
            s += f" OFFSET {int(atla)}"
        return s

    def cədvəllər_sql(self) -> str:
        return ("SELECT table_name AS ad FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_type = "
                "'BASE TABLE' ORDER BY table_name")

    def sütunlar_sql(self) -> str:
        return ("SELECT column_name AS ad, data_type AS tip, is_nullable = "
                "'YES' AS boş, column_key = 'PRI' AS açar FROM "
                "information_schema.columns WHERE table_schema = DATABASE() "
                "AND table_name = $1 ORDER BY ordinal_position")

    qaytarma = False

    def tip(self, növ: str, açar: bool) -> str:
        if açar and növ == "tam":
            return "BIGINT AUTO_INCREMENT PRIMARY KEY"
        if açar and növ == "mətn":
            return "VARCHAR(191) PRIMARY KEY"
        return {"tam": "BIGINT", "onluq": "DOUBLE", "məntiq": "BOOLEAN",
                "bayt": "LONGBLOB"}.get(növ, "TEXT") + \
            (" PRIMARY KEY" if açar else "")


_QAÇIŞ = str.maketrans({"\0": "\\0", "\n": "\\n", "\r": "\\r",
                        "\\": "\\\\", "'": "\\'", '"': '\\"',
                        "\x1a": "\\Z"})


def _lenenc(n: int) -> bytes:
    if n < 251:
        return bytes([n])
    if n < 1 << 16:
        return b"\xfc" + struct.pack("<H", n)
    if n < 1 << 24:
        return b"\xfd" + struct.pack("<I", n)[:3]
    return b"\xfe" + struct.pack("<Q", n)


def _lenenc_oxu(p: bytes, i: int) -> tuple[int, int]:
    b = p[i]
    if b < 251:
        return b, i + 1
    if b == 0xFC:
        return struct.unpack("<H", p[i + 1:i + 3])[0], i + 3
    if b == 0xFD:
        return int.from_bytes(p[i + 1:i + 4], "little"), i + 4
    return struct.unpack("<Q", p[i + 1:i + 9])[0], i + 9


def _çevir(tip: int, charset: int, d: bytes) -> Any:
    if tip in _TAM:
        return int(d)
    if tip in _ONLUQ:
        return float(d)
    if tip in _DECİMAL:
        m = d.decode()
        return int(m) if m.lstrip("-").isdigit() else float(m)
    if tip == 16:                                    # BIT
        return int.from_bytes(d, "big")
    if tip == 245:                                   # JSON
        try:
            return _json.loads(d)
        except ValueError:
            return d.decode("utf-8", "replace")
    if tip in _BLOB and charset == 63:               # ikili
        return d
    return d.decode("utf-8", "replace")


# ── RSA-OAEP (caching_sha2_password tam yolu, TLS-siz) ────────────────

def _rsa_oaep(pem: bytes, mesaj: bytes) -> bytes:
    import base64
    import os
    sətirlər = [x for x in pem.decode().strip().splitlines()
                if not x.startswith("-----")]
    der = base64.b64decode("".join(sətirlər))
    n, e = _açar(der)
    k = (n.bit_length() + 7) // 8
    hl = 20                                          # SHA-1
    if len(mesaj) > k - 2 * hl - 2:
        raise SürücüXətası("parol RSA açarı üçün çox uzundur")
    lhash = hashlib.sha1(b"").digest()
    db = lhash + b"\0" * (k - len(mesaj) - 2 * hl - 2) + b"\x01" + mesaj
    toxum = os.urandom(hl)
    db_maska = _mgf1(toxum, k - hl - 1)
    maskalı_db = bytes(x ^ y for x, y in zip(db, db_maska))
    toxum_maska = _mgf1(maskalı_db, hl)
    maskalı_toxum = bytes(x ^ y for x, y in zip(toxum, toxum_maska))
    em = b"\0" + maskalı_toxum + maskalı_db
    return pow(int.from_bytes(em, "big"), e, n).to_bytes(k, "big")


def _mgf1(toxum: bytes, uzunluq: int) -> bytes:
    n = b""
    i = 0
    while len(n) < uzunluq:
        n += hashlib.sha1(toxum + i.to_bytes(4, "big")).digest()
        i += 1
    return n[:uzunluq]


def _der(d: bytes, i: int) -> tuple[int, int, int]:
    """(teq, məzmunun başı, məzmunun sonu)"""
    teq = d[i]
    u = d[i + 1]
    i += 2
    if u & 0x80:
        n = u & 0x7F
        u = int.from_bytes(d[i:i + n], "big")
        i += n
    return teq, i, i + u


def _açar(der: bytes) -> tuple[int, int]:
    """SubjectPublicKeyInfo və ya PKCS#1 RSAPublicKey → (n, e)."""
    _, b, _ = _der(der, 0)                           # SEQUENCE
    teq, b2, s2 = _der(der, b)
    if teq == 0x30:                                  # SPKI: alqoritm + BIT STRING
        teq, b3, s3 = _der(der, s2)
        der, b = der[b3 + 1:s3], 0                   # BIT STRING-in 0 baytı
        _, b, _ = _der(der, b)
        teq, b2, s2 = _der(der, b)
    n = int.from_bytes(der[b2:s2], "big")
    _, b3, s3 = _der(der, s2)
    e = int.from_bytes(der[b3:s3], "big")
    return n, e
