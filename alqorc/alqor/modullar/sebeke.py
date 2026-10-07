"""
`şəbəkə` — aşağı səviyyəli TCP/UDP (§ 10.12).

    gətir şəbəkə

    dəyişən s = gözlə şəbəkə.TCPBağlan("nümunə.az", 80)
    s.göndər("HEAD / HTTP/1.0\\r\\nHost: nümunə.az\\r\\n\\r\\n")
    yaz(s.sətirAl())
    s.bağla()

    // Exo server
    dəyişən server = şəbəkə.TCPServer(9000, (k) => k.göndər(k.al()))
    server.başlat()          // fon sapında; server.dinlə() — bloklayır
    server.dayandır()

    dəyişən u = şəbəkə.UDPSoket(5000)
    u.göndər("salam", "127.0.0.1", 5001)
    dəyişən m = u.al()       // {"verilən": bayt, "ünvan": "…", "port": …}

    şəbəkə.ünvanTap("nümunə.az")       // ["93.184.…"]
    şəbəkə.portAçıqdır("localhost", 5432)

TCPServer standart olaraq yalnız `127.0.0.1`-də dinləyir; şəbəkəyə
açmaq üçün `ünvan: "0.0.0.0"` açıq yazılmalıdır.
"""

from __future__ import annotations

import socket
import socketserver
import threading
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı


def _xəta(x: Exception, nə: str) -> AlqorXəta:
    if isinstance(x, (socket.timeout, TimeoutError)):
        return AlqorXəta("VaxtBitdiXətası", f"{nə}: vaxt bitdi", None,
                         "ALQ-R011")
    return AlqorXəta("BağlantıXətası", f"{nə}: {x}", None, "ALQ-R010")


def _bayt(x: Any) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        return x.encode("utf-8")
    raise AlqorXəta("TipXətası", f"mətn və ya bayt gözlənilir, "
                    f"`{tip_adı(x)}` gəlib", None, "ALQ-T001")


def _host(h: str) -> str:
    return h.encode("idna").decode() if h and not h.isascii() else h


class Soket:
    ALQOR_TİP_ADI = "soket"

    def __init__(self, s: socket.socket, ad: str):
        self.s = s
        self.ad = ad
        self.bufer = b""

    def __repr__(self) -> str:
        return f"<soket {self.ad}>"

    def göndər(self, x: Any) -> int:
        b = _bayt(x)
        try:
            self.s.sendall(b)
        except OSError as e:
            raise _xəta(e, self.ad)
        return len(b)

    def al(self, n: int = 65536) -> bytes:
        if self.bufer:
            b, self.bufer = self.bufer[:n], self.bufer[n:]
            return b
        try:
            return self.s.recv(int(n))
        except OSError as e:
            raise _xəta(e, self.ad)

    def sətir_al(self, maks: int = 1 << 20) -> str | None:
        while b"\n" not in self.bufer:
            if len(self.bufer) > maks:
                raise AlqorXəta("DəyərXətası", "sətir çox uzundur", None,
                                "ALQ-R010")
            try:
                parça = self.s.recv(4096)
            except OSError as e:
                raise _xəta(e, self.ad)
            if not parça:
                if not self.bufer:
                    return None
                s, self.bufer = self.bufer, b""
                return s.decode("utf-8", "replace")
            self.bufer += parça
        s, _, self.bufer = self.bufer.partition(b"\n")
        return s.rstrip(b"\r").decode("utf-8", "replace")

    def vaxt_limiti(self, ms: int | None) -> "Soket":
        self.s.settimeout(None if ms is None else int(ms) / 1000)
        return self

    def bağla(self) -> None:
        try:
            self.s.close()
        except OSError:
            pass


Soket.ALQOR_METODLARI = {
    "göndər": lambda i, s, x: s.göndər(x),
    "al": lambda i, s, n=65536: s.al(n),
    "alMətn": lambda i, s, n=65536: s.al(n).decode("utf-8", "replace"),
    "sətirAl": lambda i, s: s.sətir_al(),
    "vaxtLimiti": lambda i, s, ms: s.vaxt_limiti(ms),
    "ünvan": lambda i, s: s.ad,
    "bağla": lambda i, s: s.bağla(),
}


def tcp_bağlan(host: str, port: int, vaxtLimiti: int = 10000) -> Soket:
    try:
        s = socket.create_connection((_host(host), int(port)),
                                     timeout=int(vaxtLimiti) / 1000)
    except OSError as e:
        raise _xəta(e, f"{host}:{port}")
    return Soket(s, f"{host}:{port}")


class TCPServer:
    ALQOR_TİP_ADI = "tcpServer"

    def __init__(self, icraçı, port: int, işləyici, ünvan: str = "127.0.0.1"):
        server_özü = self

        class İşləyici(socketserver.BaseRequestHandler):
            def handle(self):
                k = Soket(self.request, "{}:{}".format(*self.client_address))
                try:
                    icraçı._çağır(işləyici, [k], {}, None)
                except AlqorXəta as x:
                    server_özü.xətalar.append(str(x))
                finally:
                    k.bağla()

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        try:
            self.server = Server((ünvan, int(port)), İşləyici)
        except OSError as e:
            raise _xəta(e, f"{ünvan}:{port}")
        self.xətalar: list[str] = []
        self.sap: threading.Thread | None = None

    def port(self) -> int:
        return self.server.server_address[1]

    def başlat(self) -> "TCPServer":
        if self.sap is None:
            self.sap = threading.Thread(target=self.server.serve_forever,
                                        daemon=True)
            self.sap.start()
        return self

    def dinlə(self) -> None:
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server.server_close()

    def dayandır(self) -> None:
        self.server.shutdown()
        self.server.server_close()


TCPServer.ALQOR_METODLARI = {
    "başlat": lambda i, s: s.başlat(),
    "dinlə": lambda i, s: s.dinlə(),
    "dayandır": lambda i, s: s.dayandır(),
    "port": lambda i, s: s.port(),
    "xətalar": lambda i, s: list(s.xətalar),
}


class UDPSoket:
    ALQOR_TİP_ADI = "udpSoket"

    def __init__(self, port: int = 0, ünvan: str = "127.0.0.1"):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.s.bind((ünvan, int(port)))
        except OSError as e:
            raise _xəta(e, f"udp {ünvan}:{port}")
        self.s.settimeout(10)

    def göndər(self, x: Any, host: str, port: int) -> int:
        try:
            return self.s.sendto(_bayt(x), (_host(host), int(port)))
        except OSError as e:
            raise _xəta(e, f"udp {host}:{port}")

    def al(self, n: int = 65536) -> dict:
        try:
            b, (h, p) = self.s.recvfrom(int(n))
        except OSError as e:
            raise _xəta(e, "udp")
        return {"verilən": b, "ünvan": h, "port": p}


UDPSoket.ALQOR_METODLARI = {
    "göndər": lambda i, u, x, h, p: u.göndər(x, h, p),
    "al": lambda i, u, n=65536: u.al(n),
    "port": lambda i, u: u.s.getsockname()[1],
    "vaxtLimiti": lambda i, u, ms: (u.s.settimeout(
        None if ms is None else int(ms) / 1000), u)[1],
    "bağla": lambda i, u: u.s.close(),
}


def ünvan_tap(host: str) -> list[str]:
    try:
        return sorted({a[4][0] for a in socket.getaddrinfo(_host(host),
                                                            None)})
    except OSError as e:
        raise _xəta(e, host)


def port_açıqdır(host: str, port: int, ms: int = 1000) -> bool:
    try:
        with socket.create_connection((_host(host), int(port)),
                                      timeout=int(ms) / 1000):
            return True
    except OSError:
        return False


def yerli_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))        # paket getmir
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "TCPBağlan": D("TCPBağlan", tcp_bağlan, 2, 3),
        "TCPServer": D("TCPServer", lambda p, f, ünvan="127.0.0.1":
                       TCPServer(icraçı, p, f, ünvan), 2, 3),
        "UDPSoket": D("UDPSoket", UDPSoket, 0, 2),
        "ünvanTap": D("ünvanTap", ünvan_tap, 1, 1),
        "portAçıqdır": D("portAçıqdır", port_açıqdır, 2, 3),
        "yerliIP": D("yerliIP", yerli_ip),
        "hostAdı": D("hostAdı", socket.gethostname),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, b = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.MƏNTİQ
    return {
        "TCPBağlan": F(m, i, i, qaytarır=T.Sadə("soket"), standart=1),
        "TCPServer": F(i, e, m, qaytarır=T.Sadə("tcpServer"), standart=1),
        "UDPSoket": F(i, m, qaytarır=T.Sadə("udpSoket"), standart=2),
        "ünvanTap": F(m, qaytarır=T.Siyahı(m)),
        "portAçıqdır": F(m, i, i, qaytarır=b, standart=1),
        "yerliIP": F(qaytarır=m), "hostAdı": F(qaytarır=m),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, h, b = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.HEÇ, T.BAYT
    S = T.Sadə("soket")
    return {
        "soket": {
            "göndər": F(e, qaytarır=i), "al": F(i, qaytarır=b, standart=1),
            "alMətn": F(i, qaytarır=m, standart=1),
            "sətirAl": F(qaytarır=T.ixtiyari(m)),
            "vaxtLimiti": F(e, qaytarır=S), "ünvan": F(qaytarır=m),
            "bağla": F(qaytarır=h),
        },
        "tcpServer": {
            "başlat": F(qaytarır=T.Sadə("tcpServer")), "dinlə": F(qaytarır=h),
            "dayandır": F(qaytarır=h), "port": F(qaytarır=i),
            "xətalar": F(qaytarır=T.Siyahı(m)),
        },
        "udpSoket": {
            "göndər": F(e, m, i, qaytarır=i),
            "al": F(i, qaytarır=T.Lüğət(m, e), standart=1),
            "port": F(qaytarır=i), "vaxtLimiti": F(e, qaytarır=e),
            "bağla": F(qaytarır=h),
        },
    }
