"""
Alqor — WebSocket (RFC 6455): müştəri və server tərəfi.

Spesifikasiya § 10.12, § 11.6. Asılılıqsızdır (yalnız `socket`, `ssl`).

Müştəri (`http` modulu):

    dəyişən ws = gözlə http.vebSoket("wss://nümunə.az/soket")
    ws.hadisə("mesaj", (m) => yaz(m))
    ws.göndər("salam")
    dəyişən cavab = ws.al(5000)        // və ya hadisəsiz — növbəti mesaj
    ws.bağla()

Server (`veb` modulu):

    s.soket("/çat", funksiya(soket)
        soket.otağaQoşul("ümumi")
        soket.hadisə("mesaj", (m) => soket.otağaYayımla("ümumi", m))
        soket.hadisə("bağlandı", () => yaz("çıxdı"))
    son)

Mesajlar: mətn → mətn çərçivəsi, `bayt` → ikili çərçivə, siyahı/lüğət →
JSON mətn. Ping-ə avtomatik pong verilir, parçalanmış (fragmented)
mesajlar birləşdirilir, maksimum mesaj ölçüsü `MAKS_MESAJ`-dır.
"""

from __future__ import annotations

import base64
import hashlib
import json as _json
import os
import queue
import secrets
import socket
import ssl
import struct
import threading
import urllib.parse
from typing import Any

from .deyerler import AlqorXəta, mətnə

SEHRLİ = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAKS_MESAJ = 16 * 1024 * 1024
MƏTN, İKİLİ, BAĞLA, PİNQ, PONQ, DAVAM = 0x1, 0x2, 0x8, 0x9, 0xA, 0x0

_SON = object()                       # `al` növbəsində bağlanma işarəsi


def qəbul_açarı(açar: str) -> str:
    """`Sec-WebSocket-Key` → `Sec-WebSocket-Accept`."""
    return base64.b64encode(
        hashlib.sha1((açar + SEHRLİ).encode("ascii")).digest()).decode()


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("ŞəbəkəXətası", mesaj, None, "ALQ-R013")


class _Protokol(Exception):
    """Protokol pozuntusu — bağlantı 1002 ilə bağlanır."""


# ═══════════════════════════════════════════════════════════════════════
#  Çərçivələr
# ═══════════════════════════════════════════════════════════════════════

def çərçivə(op: int, data: bytes, maskala: bool, fin: bool = True) -> bytes:
    b0 = (0x80 if fin else 0) | op
    n = len(data)
    m = 0x80 if maskala else 0
    if n < 126:
        baş = struct.pack("!BB", b0, m | n)
    elif n < 65536:
        baş = struct.pack("!BBH", b0, m | 126, n)
    else:
        baş = struct.pack("!BBQ", b0, m | 127, n)
    if not maskala:
        return baş + data
    açar = os.urandom(4)
    return baş + açar + _maska(data, açar)


def _maska(data: bytes, açar: bytes) -> bytes:
    if not data:
        return b""
    # Tam ədəd XOR — böyük mesajlarda bayt-bayt dövrdən xeyli sürətli
    uzun = (açar * (len(data) // 4 + 1))[:len(data)]
    return (int.from_bytes(data, "big") ^ int.from_bytes(uzun, "big")
            ).to_bytes(len(data), "big")


class _Oxuyucu:
    def __init__(self, s: socket.socket, əvvəlki: bytes = b""):
        self.s = s
        self.bufer = bytearray(əvvəlki)

    def oxu(self, n: int) -> bytes:
        while len(self.bufer) < n:
            p = self.s.recv(max(65536, n - len(self.bufer)))
            if not p:
                raise ConnectionResetError("bağlantı qırıldı")
            self.bufer += p
        d = bytes(self.bufer[:n])
        del self.bufer[:n]
        return d

    def çərçivə(self, maskalı_gözlənilir: bool) -> tuple[bool, int, bytes]:
        b0, b1 = self.oxu(2)
        fin, op = bool(b0 & 0x80), b0 & 0x0F
        if b0 & 0x70:
            raise _Protokol("RSV bitləri dəstəklənmir")
        maskalı = bool(b1 & 0x80)
        if maskalı != maskalı_gözlənilir:
            raise _Protokol("maska qaydası pozulub")
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack("!H", self.oxu(2))[0]
        elif n == 127:
            n = struct.unpack("!Q", self.oxu(8))[0]
        if n > MAKS_MESAJ:
            raise _Protokol("mesaj çox böyükdür")
        if op >= 0x8 and (n > 125 or not fin):
            raise _Protokol("idarə çərçivəsi yanlışdır")
        açar = self.oxu(4) if maskalı else b""
        data = self.oxu(n)
        return fin, op, _maska(data, açar) if maskalı else data


# ═══════════════════════════════════════════════════════════════════════
#  Bağlantı
# ═══════════════════════════════════════════════════════════════════════

class Bağlantı:
    """Açıq WebSocket — həm müştəri, həm server tərəfi."""

    ALQOR_TİP_ADI = "vebSoket"

    def __init__(self, s: socket.socket, icraçı, müştəri: bool,
                 əvvəlki: bytes = b"", qovşaq: "Qovşaq | None" = None,
                 sorğu: Any = None):
        self.s = s
        self.icraçı = icraçı
        self.müştəri = müştəri
        self._oxuyucu = _Oxuyucu(s, əvvəlki)
        self._yazma = threading.Lock()
        self._idarəedicilər: dict[str, list] = {}
        self._növbə: queue.Queue = queue.Queue()
        self.açıq = True
        self.bağlanma_kodu: int | None = None
        self.bağlanma_səbəbi = ""
        self.qovşaq = qovşaq
        self.sorğu = sorğu
        self.id = secrets.token_hex(4)
        self.otaqlar: set[str] = set()
        self._bitdi = threading.Event()

    # ── Göndərmə ──────────────────────────────────────────────────────

    def _yaz(self, op: int, data: bytes) -> None:
        with self._yazma:
            try:
                self.s.sendall(çərçivə(op, data, self.müştəri))
            except OSError as x:
                self.açıq = False
                raise _xəta(f"WebSocket-ə yazıla bilmədi: {x}") from None

    def göndər(self, x: Any) -> None:
        if not self.açıq:
            raise _xəta("WebSocket bağlıdır")
        if isinstance(x, (bytes, bytearray)):
            self._yaz(İKİLİ, bytes(x))
        elif isinstance(x, str):
            self._yaz(MƏTN, x.encode("utf-8"))
        elif isinstance(x, (list, dict, int, float, bool)) or x is None:
            from .modullar.http_ import _json_hazırla
            self._yaz(MƏTN, _json.dumps(_json_hazırla(x),
                                        ensure_ascii=False).encode("utf-8"))
        else:
            self._yaz(MƏTN, mətnə(x, self.icraçı).encode("utf-8"))

    def bağla(self, kod: int = 1000, səbəb: str = "") -> None:
        if not self.açıq:
            return
        try:
            self._yaz(BAĞLA, struct.pack("!H", int(kod))
                      + str(səbəb).encode("utf-8")[:120])
        except AlqorXəta:
            pass
        self.açıq = False
        # Qarşı tərəfin bağlama cavabını qısa müddət gözləyirik
        self._bitdi.wait(2)
        self._soketi_bağla()

    def _soketi_bağla(self) -> None:
        try:
            self.s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.s.close()
        except OSError:
            pass

    # ── Hadisələr ─────────────────────────────────────────────────────

    def hadisə(self, ad: str, f: Any) -> "Bağlantı":
        if ad not in ("mesaj", "bağlandı", "xəta", "qoşuldu"):
            raise AlqorXəta("ArqumentXətası",
                            f"naməlum WebSocket hadisəsi: `{ad}` "
                            "(mesaj, bağlandı, xəta)", None, "ALQ-R013")
        self._idarəedicilər.setdefault(ad, []).append(f)
        return self

    def _yay(self, ad: str, *arq: Any) -> None:
        for f in list(self._idarəedicilər.get(ad, ())):
            try:
                self.icraçı._çağır(f, list(arq), {}, None)
            except AlqorXəta as x:
                if ad != "xəta" and self._idarəedicilər.get("xəta"):
                    self._yay("xəta", self.icraçı._xəta_obyekti(x))
                else:
                    import sys
                    print(f"✖ WebSocket idarəedicisi: {x.tip}: {x.mesaj}",
                          file=sys.stderr)

    def al(self, müddət_ms: Any = None) -> Any:
        """Növbəti mesaj (hadisə idarəedicisi yoxdursa); bağlıdırsa `boş`."""
        try:
            m = self._növbə.get(timeout=None if müddət_ms is None
                                else max(0.0, float(müddət_ms) / 1000))
        except queue.Empty:
            raise AlqorXəta("VaxtBitdiXətası",
                            f"{müddət_ms} ms ərzində mesaj gəlmədi",
                            None, "ALQ-R013") from None
        if m is _SON:
            self._növbə.put(_SON)
            return None
        return m

    # ── Oxuma dövrü ───────────────────────────────────────────────────

    def dövr(self) -> None:
        """Çərçivələri oxuyur — müştəridə fon sapında, serverdə sorğu sapında."""
        parçalar: list[bytes] = []
        parça_op = 0
        try:
            while True:
                fin, op, data = self._oxuyucu.çərçivə(
                    maskalı_gözlənilir=not self.müştəri)
                if op == PİNQ:
                    if self.açıq:
                        self._yaz(PONQ, data)
                    continue
                if op == PONQ:
                    continue
                if op == BAĞLA:
                    if len(data) >= 2:
                        self.bağlanma_kodu = struct.unpack("!H", data[:2])[0]
                        self.bağlanma_səbəbi = data[2:].decode(
                            "utf-8", "replace")
                    if self.açıq:
                        self.açıq = False
                        try:
                            with self._yazma:
                                self.s.sendall(çərçivə(BAĞLA, data[:2],
                                                       self.müştəri))
                        except OSError:
                            pass
                    break
                if op in (MƏTN, İKİLİ):
                    if parçalar:
                        raise _Protokol("parçalanmış mesaj bitməyib")
                    parça_op = op
                    parçalar = [data]
                elif op == DAVAM:
                    if not parçalar:
                        raise _Protokol("gözlənilməz davam çərçivəsi")
                    parçalar.append(data)
                    if sum(map(len, parçalar)) > MAKS_MESAJ:
                        raise _Protokol("mesaj çox böyükdür")
                else:
                    raise _Protokol(f"naməlum əməliyyat kodu {op}")
                if not fin:
                    continue
                tam = b"".join(parçalar)
                parçalar = []
                if parça_op == MƏTN:
                    try:
                        mesaj: Any = tam.decode("utf-8")
                    except UnicodeDecodeError:
                        raise _Protokol("mətn UTF-8 deyil") from None
                else:
                    mesaj = tam
                if self._idarəedicilər.get("mesaj"):
                    self._yay("mesaj", mesaj)
                else:
                    self._növbə.put(mesaj)
        except _Protokol as x:
            if self.açıq:
                try:
                    self._yaz(BAĞLA, struct.pack("!H", 1002)
                              + str(x).encode("utf-8")[:120])
                except AlqorXəta:
                    pass
            self.bağlanma_kodu = 1002
            self.bağlanma_səbəbi = str(x)
        except (OSError, ConnectionResetError, ValueError):
            if self.bağlanma_kodu is None:
                self.bağlanma_kodu = 1006
        finally:
            self.açıq = False
            self._bitdi.set()
            self._soketi_bağla()
            self._növbə.put(_SON)
            if self.qovşaq is not None:
                self.qovşaq.çıxar(self)
            self._yay("bağlandı", self.bağlanma_kodu or 1005,
                      self.bağlanma_səbəbi)

    # ── Server: otaqlar, yayım ────────────────────────────────────────

    def otağa_qoşul(self, ad: str) -> None:
        if self.qovşaq is not None:
            self.qovşaq.otağa_qoşul(self, str(ad))

    def otaqdan_çıx(self, ad: str) -> None:
        if self.qovşaq is not None:
            self.qovşaq.otaqdan_çıx(self, str(ad))

    def otağa_yayımla(self, ad: str, x: Any, özünə: bool = False) -> int:
        if self.qovşaq is None:
            return 0
        return self.qovşaq.yayımla(x, self.qovşaq.otaq(str(ad)),
                                   None if özünə else self)

    def yayımla(self, x: Any, özünə: bool = False) -> int:
        if self.qovşaq is None:
            return 0
        return self.qovşaq.yayımla(x, self.qovşaq.hamısı(),
                                   None if özünə else self)

    def __repr__(self) -> str:
        return f"<vebSoket {self.id} {'açıq' if self.açıq else 'bağlı'}>"


Bağlantı.ALQOR_METODLARI = {
    "göndər": lambda i, b, x: b.göndər(x),
    "hadisə": lambda i, b, ad, f: b.hadisə(ad, f),
    "al": lambda i, b, müddət=None: b.al(müddət),
    "bağla": lambda i, b, kod=1000, səbəb="": b.bağla(kod, səbəb),
    "açıqdır": lambda i, b: b.açıq,
    "kimlik": lambda i, b: b.id,
    "sorğu": lambda i, b: b.sorğu,
    "otağaQoşul": lambda i, b, ad: b.otağa_qoşul(ad),
    "otaqdanÇıx": lambda i, b, ad: b.otaqdan_çıx(ad),
    "otağaYayımla": lambda i, b, ad, x, özünə=False:
        b.otağa_yayımla(ad, x, bool(özünə)),
    "yayımla": lambda i, b, x, özünə=False: b.yayımla(x, bool(özünə)),
    "bağlanmaKodu": lambda i, b: b.bağlanma_kodu,
}


class Qovşaq:
    """Bir server yolunun bütün bağlantıları və otaqları."""

    def __init__(self):
        self._kilid = threading.Lock()
        self._bağlantılar: set[Bağlantı] = set()
        self._otaqlar: dict[str, set[Bağlantı]] = {}

    def əlavə(self, b: Bağlantı) -> None:
        with self._kilid:
            self._bağlantılar.add(b)

    def çıxar(self, b: Bağlantı) -> None:
        with self._kilid:
            self._bağlantılar.discard(b)
            for ad in list(b.otaqlar):
                self._otaqlar.get(ad, set()).discard(b)
                if not self._otaqlar.get(ad):
                    self._otaqlar.pop(ad, None)

    def otağa_qoşul(self, b: Bağlantı, ad: str) -> None:
        with self._kilid:
            self._otaqlar.setdefault(ad, set()).add(b)
            b.otaqlar.add(ad)

    def otaqdan_çıx(self, b: Bağlantı, ad: str) -> None:
        with self._kilid:
            self._otaqlar.get(ad, set()).discard(b)
            b.otaqlar.discard(ad)

    def otaq(self, ad: str) -> list[Bağlantı]:
        with self._kilid:
            return list(self._otaqlar.get(ad, ()))

    def hamısı(self) -> list[Bağlantı]:
        with self._kilid:
            return list(self._bağlantılar)

    def yayımla(self, x: Any, kimə: list[Bağlantı],
                istisna: Bağlantı | None) -> int:
        n = 0
        for b in kimə:
            if b is istisna or not b.açıq:
                continue
            try:
                b.göndər(x)
                n += 1
            except AlqorXəta:
                pass
        return n


# ═══════════════════════════════════════════════════════════════════════
#  Müştəri əl sıxması
# ═══════════════════════════════════════════════════════════════════════

def bağlan(icraçı, url: str, başlıqlar: dict | None = None,
           vaxt_limiti: float = 15.0) -> Bağlantı:
    u = urllib.parse.urlsplit(str(url))
    if u.scheme not in ("ws", "wss"):
        raise AlqorXəta("ArqumentXətası",
                        f"WebSocket ünvanı `ws://` və ya `wss://` ilə "
                        f"başlamalıdır: `{url}`", None, "ALQ-R013")
    host = u.hostname or ""
    port = u.port or (443 if u.scheme == "wss" else 80)
    yol = (u.path or "/") + (f"?{u.query}" if u.query else "")
    try:
        s = socket.create_connection((host, port), timeout=vaxt_limiti)
        if u.scheme == "wss":
            s = ssl.create_default_context().wrap_socket(
                s, server_hostname=host)
    except (OSError, ssl.SSLError) as x:
        raise AlqorXəta("BağlantıXətası",
                        f"{host}:{port} — {x}", None, "ALQ-R013") from None
    açar = base64.b64encode(os.urandom(16)).decode()
    host_başlığı = host if port in (80, 443) else f"{host}:{port}"
    sətirlər = [f"GET {urllib.parse.quote(yol, safe='/?&=%:@')} HTTP/1.1",
                f"Host: {host_başlığı}", "Upgrade: websocket",
                "Connection: Upgrade", f"Sec-WebSocket-Key: {açar}",
                "Sec-WebSocket-Version: 13",
                "User-Agent: Alqor-vebSoket/0.1"]
    for a, d in (başlıqlar or {}).items():
        a, d = str(a), mətnə(d, icraçı)
        if "\r" in a + d or "\n" in a + d:
            raise AlqorXəta("ArqumentXətası", "başlıqda sətir sonu ola "
                            "bilməz", None, "ALQ-R013")
        sətirlər.append(f"{a}: {d}")
    try:
        s.sendall(("\r\n".join(sətirlər) + "\r\n\r\n").encode("utf-8"))
        cavab = b""
        while b"\r\n\r\n" not in cavab:
            p = s.recv(4096)
            if not p:
                raise ConnectionResetError("server cavab vermədi")
            cavab += p
            if len(cavab) > 65536:
                raise _xəta("əl sıxma cavabı çox uzundur")
    except (OSError, ConnectionResetError) as x:
        s.close()
        raise AlqorXəta("BağlantıXətası", f"əl sıxma alınmadı: {x}",
                        None, "ALQ-R013") from None
    baş, _, qalan = cavab.partition(b"\r\n\r\n")
    sətirlər = baş.decode("iso-8859-1").split("\r\n")
    status = sətirlər[0].split(" ", 2)
    b = {}
    for x in sətirlər[1:]:
        a, _, d = x.partition(":")
        b[a.strip().lower()] = d.strip()
    if len(status) < 2 or status[1] != "101":
        s.close()
        raise _xəta(f"server WebSocket qəbul etmədi: {sətirlər[0]}")
    if b.get("sec-websocket-accept") != qəbul_açarı(açar):
        s.close()
        raise _xəta("Sec-WebSocket-Accept yanlışdır")
    s.settimeout(None)
    bağ = Bağlantı(s, icraçı, True, qalan)
    threading.Thread(target=bağ.dövr, daemon=True,
                     name="alqor-vebsoket").start()
    return bağ


# ═══════════════════════════════════════════════════════════════════════
#  Server əl sıxması (`veb` modulu çağırır)
# ═══════════════════════════════════════════════════════════════════════

def server_əl_sıxması(işləyici) -> bool:
    """
    `BaseHTTPRequestHandler` üzərində 101 cavabı. Uğursuzdursa 400
    göndərir və False qaytarır.
    """
    h = işləyici.headers
    açar = h.get("Sec-WebSocket-Key", "")
    if (h.get("Upgrade", "").lower() != "websocket"
            or "upgrade" not in h.get("Connection", "").lower()
            or h.get("Sec-WebSocket-Version") != "13" or not açar):
        gövdə = b"400 WebSocket sorgusu deyil"
        işləyici.send_response(400, "Bad Request")
        işləyici.send_header("Content-Length", str(len(gövdə)))
        işləyici.end_headers()
        işləyici.wfile.write(gövdə)
        return False
    işləyici.send_response(101, "Switching Protocols")
    işləyici.send_header("Upgrade", "websocket")
    işləyici.send_header("Connection", "Upgrade")
    işləyici.send_header("Sec-WebSocket-Accept", qəbul_açarı(açar))
    işləyici.end_headers()
    işləyici.wfile.flush()
    return True


def soket_sorğusudur(işləyici) -> bool:
    return işləyici.headers.get("Upgrade", "").lower() == "websocket"
