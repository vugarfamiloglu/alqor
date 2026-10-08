"""
macOS `.dmg` yazıcısı — `hdiutil` olmadan (Linux/Windows-da da işləyir).

Disk imajı: ISO 9660 + Rock Ridge (POSIX icazələri, uzun/Unicode adlar,
simvolik keçidlər — macOS-un `cd9660` sürücüsü oxuyur), UDIF
konteynerinə bükülür: zlib bloklar ("UDZO"), XML plist-də `blkx` cədvəli,
sonda 512 baytlıq `koly` treyleri; CRC32 yoxlama cəmləri hdiutil-in
gözlədiyi kimi.
"""

from __future__ import annotations

import base64
import struct
import time
import uuid
import zlib

SEKTOR = 2048


# ═══════════════════════════════════════════════════════════════════════
#  ISO 9660 + Rock Ridge
# ═══════════════════════════════════════════════════════════════════════

def _iki(n: int, ölçü: int) -> bytes:
    """Hər iki bayt sırası (both-endian)."""
    f = {2: "H", 4: "I"}[ölçü]
    return struct.pack("<" + f, n) + struct.pack(">" + f, n)


def _tarix7(t: time.struct_time) -> bytes:
    return bytes([t.tm_year - 1900, t.tm_mon, t.tm_mday, t.tm_hour,
                  t.tm_min, t.tm_sec, 0])


def _tarix17(t: time.struct_time) -> bytes:
    return (time.strftime("%Y%m%d%H%M%S", t) + "00").encode() + b"\0"


class _D:
    def __init__(self, ad: str, növ: str, rejim: int = 0o755,
                 məzmun: bytes = b"", hədəf: str = ""):
        self.ad, self.növ, self.rejim = ad, növ, rejim
        self.məzmun, self.hədəf = məzmun, hədəf
        self.uşaqlar: dict[str, _D] = {}
        self.iso = ""
        self.lba = 0
        self.ölçü = 0
        self.ino = 0
        self.valideyn: _D | None = None


def _su(d: _D, xüsusi: str = "") -> bytes:
    """Rock Ridge sistem istifadəsi sahəsi."""
    n = b""
    if xüsusi == "kök.":
        n += b"SP\x07\x01\xbe\xef\x00"
    n += b"RR\x05\x01\x89"                               # PX NM SL TF
    tip = {"dir": 0o040000, "fayl": 0o100000, "keçid": 0o120000}[d.növ]
    nlink = 2 + sum(1 for u in d.uşaqlar.values() if u.növ == "dir") \
        if d.növ == "dir" else 1
    n += b"PX\x2c\x01" + _iki(tip | d.rejim, 4) + _iki(nlink, 4) + \
        _iki(0, 4) + _iki(0, 4) + _iki(d.ino, 4)
    if not xüsusi:
        ad = d.ad.encode("utf-8")
        while ad:                                    # NM ≤ 250 bayt parçalar
            p, ad = ad[:240], ad[240:]
            n += b"NM" + bytes([5 + len(p), 1, 1 if ad else 0]) + p
    if d.növ == "keçid":
        komp = b""
        for h in d.hədəf.split("/"):
            if h == "" and not komp:
                komp += b"\x08\x00"                    # kök
            elif h == ".":
                komp += b"\x02\x00"
            elif h == "..":
                komp += b"\x04\x00"
            elif h:
                b = h.encode("utf-8")
                komp += bytes([0, len(b)]) + b
        n += b"SL" + bytes([5 + len(komp), 1, 0]) + komp
    if xüsusi == "kök.":
        ident, təsvir, mənbə = b"RRIP_1991A", b"ROCK RIDGE", b"ALQOR"
        n += b"ER" + bytes([8 + len(ident) + len(təsvir) + len(mənbə), 1,
                            len(ident), len(təsvir), len(mənbə), 1]) + \
            ident + təsvir + mənbə
    return n


def _qeyd_düz(d: _D, ad: bytes, su: bytes, bayraq: int,
              zaman: bytes) -> bytes:
    """Qovluq qeydi. `ad`: b"\\0" (.), b"\\1" (..) və ya ISO adı."""
    gövdə = (_iki(d.lba, 4) + _iki(d.ölçü, 4) + zaman +
             bytes([bayraq, 0, 0]) + _iki(1, 2) + bytes([len(ad)]))
    # 33 baytlıq başlıq + ad cüt uzunluqda olmalıdır
    qeyd = gövdə + ad + (b"\0" if len(ad) % 2 == 0 else b"") + su
    if len(qeyd) % 2:
        qeyd += b"\0"
    uz = 2 + len(qeyd)
    if uz > 255:
        raise ValueError(f"ad çox uzundur: {d.ad}")
    return bytes([uz, 0]) + qeyd


def iso9660(fayllar: dict[str, tuple[bytes, int]],
            keçidlər: dict[str, str], cild: str) -> bytes:
    kök = _D("", "dir")
    for yol, (m, r) in fayllar.items():
        h = yol.strip("/").split("/")
        q = kök
        for a in h[:-1]:
            q = q.uşaqlar.setdefault(a, _D(a, "dir"))
        q.uşaqlar[h[-1]] = _D(h[-1], "fayl", r & 0o7777, m)
    for yol, hədəf in keçidlər.items():
        h = yol.strip("/").split("/")
        q = kök
        for a in h[:-1]:
            q = q.uşaqlar.setdefault(a, _D(a, "dir"))
        q.uşaqlar[h[-1]] = _D(h[-1], "keçid", 0o777, hədəf=hədəf)

    # Qovluqlar BFS sırası ilə (path table bunu tələb edir)
    qovluqlar = [kök]
    for q in qovluqlar:
        for i, a in enumerate(sorted(q.uşaqlar)):
            u = q.uşaqlar[a]
            u.valideyn = q
            u.iso = (f"D{i:06d}" if u.növ == "dir" else f"F{i:06d}.;1")
            if u.növ == "dir":
                qovluqlar.append(u)
    hamısı = []

    def gəz(q):
        hamısı.append(q)
        for u in q.uşaqlar.values():
            gəz(u)
    gəz(kök)
    for i, d in enumerate(hamısı, 1):
        d.ino = i
    kök.valideyn = kök

    zaman_t = time.gmtime()
    zaman = _tarix7(zaman_t)

    def uşaqlar_sıralı(q):
        return sorted(q.uşaqlar.values(), key=lambda u: u.iso)

    # Path table
    def path_table(böyük: bool) -> bytes:
        n = b""
        f = ">" if böyük else "<"
        for q in qovluqlar:
            ad = b"\0" if q is kök else q.iso.encode()
            ana = qovluqlar.index(q.valideyn) + 1
            n += bytes([len(ad), 0]) + struct.pack(f + "IH", q.lba, ana) + ad
            if len(ad) % 2:
                n += b"\0"
        return n

    # Qovluq ölçüləri (qeydlər sektor sərhədini keçmir)
    def qeydlər(q) -> list[bytes]:
        n = [_qeyd_düz(q, b"\0", _su(q, "kök." if q is kök else "."), 2,
                       zaman),
             _qeyd_düz(q.valideyn, b"\x01", _su(q.valideyn, ".."), 2,
                       zaman)]
        for u in uşaqlar_sıralı(q):
            n.append(_qeyd_düz(u, u.iso.encode(), _su(u),
                               2 if u.növ == "dir" else 0, zaman))
        return n

    def ölç(q) -> int:
        cari, sekt = 0, 1
        for r in qeydlər(q):
            if cari + len(r) > SEKTOR:
                sekt += 1
                cari = 0
            cari += len(r)
        return sekt * SEKTOR

    pt_ölçü = len(path_table(False))
    pt_sekt = (pt_ölçü + SEKTOR - 1) // SEKTOR
    lba = 18 + 2 * pt_sekt
    # iki keçid: ölçülər LBA-dan asılı deyil, ona görə birbaşa
    for q in qovluqlar:
        q.ölçü = ölç(q)
        q.lba = lba
        lba += q.ölçü // SEKTOR
    fayl_sırası = [d for d in hamısı if d.növ == "fayl"]
    for d in fayl_sırası:
        d.ölçü = len(d.məzmun)
        d.lba = lba if d.ölçü else 0
        lba += (d.ölçü + SEKTOR - 1) // SEKTOR
    cəm = lba
    for q in qovluqlar:                 # ölçü dəyişmir — yenidən yoxla
        assert ölç(q) == q.ölçü

    imaj = bytearray(cəm * SEKTOR)
    kök_qeyd = _qeyd_düz(kök, b"\0", b"", 2, zaman)
    assert len(kök_qeyd) == 34
    cild_id = cild.upper()[:32].ljust(32).encode("ascii")
    pvd = (b"\x01CD001\x01\x00" + b"ALQOR".ljust(32) + cild_id + b"\0" * 8 +
           _iki(cəm, 4) + b"\0" * 32 + _iki(1, 2) + _iki(1, 2) +
           _iki(SEKTOR, 2) + _iki(pt_ölçü, 4) +
           struct.pack("<II", 18, 0) + struct.pack(">II", 18 + pt_sekt, 0) +
           kök_qeyd + b" " * 128 + b"ALQOR".ljust(128) + b"ALQOR".ljust(128)
           + b"ALQOR QURASDIRICI".ljust(128) + b" " * 37 * 3 +
           _tarix17(zaman_t) * 2 + b"0" * 16 + b"\0" + b"0" * 16 + b"\0" +
           b"\x01\x00")
    imaj[16 * SEKTOR:16 * SEKTOR + len(pvd)] = pvd
    imaj[17 * SEKTOR:17 * SEKTOR + 7] = b"\xffCD001\x01"
    imaj[18 * SEKTOR:18 * SEKTOR + pt_ölçü] = path_table(False)
    m = (18 + pt_sekt) * SEKTOR
    imaj[m:m + pt_ölçü] = path_table(True)
    for q in qovluqlar:
        o = q.lba * SEKTOR
        cari = 0
        for r in qeydlər(q):
            if cari + len(r) > SEKTOR:
                o += SEKTOR - cari
                cari = 0
            imaj[o:o + len(r)] = r
            o += len(r)
            cari += len(r)
    for d in fayl_sırası:
        if d.ölçü:
            imaj[d.lba * SEKTOR:d.lba * SEKTOR + d.ölçü] = d.məzmun
    return bytes(imaj)


# ═══════════════════════════════════════════════════════════════════════
#  UDIF (.dmg) konteyneri
# ═══════════════════════════════════════════════════════════════════════

def _cəm32(crc: int) -> bytes:
    """UDIFChecksum: tip 2 (CRC32), 32 bit, 32 sözlük massiv."""
    return struct.pack(">II", 2, 32) + struct.pack(">I", crc) + b"\0" * 124


def udif(imaj: bytes, ad: str = "disk image") -> bytes:
    assert len(imaj) % 512 == 0
    sektor_sayı = len(imaj) // 512
    PARÇA = 2048                                   # sektor (1 MiB)
    məlumat = bytearray()
    parçalar = []
    for s in range(0, sektor_sayı, PARÇA):
        n = min(PARÇA, sektor_sayı - s)
        xam = imaj[s * 512:(s + n) * 512]
        if not any(xam):
            parçalar.append((2, s, n, len(məlumat), 0))       # sıfırlar
            continue
        c = zlib.compress(xam, 9)
        parçalar.append((0x80000005, s, n, len(məlumat), len(c)))
        məlumat += c
    parçalar.append((0xFFFFFFFF, sektor_sayı, 0, len(məlumat), 0))
    blkx_crc = zlib.crc32(imaj) & 0xFFFFFFFF
    mish = (b"mish" + struct.pack(">IQQQII", 1, 0, sektor_sayı, 0, 0x208, 0)
            + b"\0" * 24 + _cəm32(blkx_crc) +
            struct.pack(">I", len(parçalar)) + b"".join(
                struct.pack(">IIQQQQ", t, 0, s, n, o, l)
                for t, s, n, o, l in parçalar))
    ad_x = (ad.replace("&", "&amp;").replace("<", "&lt;"))
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
        '"-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n\t<key>resource-fork</key>\n'
        '\t<dict>\n\t\t<key>blkx</key>\n\t\t<array>\n\t\t\t<dict>\n'
        '\t\t\t\t<key>Attributes</key>\n\t\t\t\t<string>0x0050</string>\n'
        f'\t\t\t\t<key>CFName</key>\n\t\t\t\t<string>{ad_x}</string>\n'
        '\t\t\t\t<key>Data</key>\n\t\t\t\t<data>\n'
        f'{base64.encodebytes(mish).decode()}\t\t\t\t</data>\n'
        '\t\t\t\t<key>ID</key>\n\t\t\t\t<string>0</string>\n'
        f'\t\t\t\t<key>Name</key>\n\t\t\t\t<string>{ad_x}</string>\n'
        '\t\t\t</dict>\n\t\t</array>\n'
        '\t\t<key>plst</key>\n\t\t<array>\n\t\t\t<dict>\n'
        '\t\t\t\t<key>Attributes</key>\n\t\t\t\t<string>0x0050</string>\n'
        '\t\t\t\t<key>Data</key>\n\t\t\t\t<data>\n'
        f'{base64.encodebytes(bytes(204)).decode()}\t\t\t\t</data>\n'
        '\t\t\t\t<key>ID</key>\n\t\t\t\t<string>0</string>\n'
        '\t\t\t\t<key>Name</key>\n\t\t\t\t<string></string>\n'
        '\t\t\t</dict>\n\t\t</array>\n\t</dict>\n</dict>\n</plist>\n'
    ).encode("utf-8")
    master = zlib.crc32(struct.pack(">I", blkx_crc)) & 0xFFFFFFFF
    xml_ofs = len(məlumat)
    koly = (b"koly" + struct.pack(">IIIQQQQQII", 4, 512, 1, 0, 0,
                                  len(məlumat), 0, 0, 1, 1) +
            uuid.uuid4().bytes + _cəm32(zlib.crc32(bytes(məlumat))
                                        & 0xFFFFFFFF) +
            struct.pack(">QQ", xml_ofs, len(plist)) + b"\0" * 120 +
            _cəm32(master) + struct.pack(">IQ", 1, sektor_sayı) +
            b"\0" * 12)
    assert len(koly) == 512, len(koly)
    return bytes(məlumat) + plist + koly
