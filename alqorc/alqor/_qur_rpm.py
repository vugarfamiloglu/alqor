"""
RPM paketi yazıcısı — `rpmbuild` olmadan, saf Python (RPM v4 formatı).

Struktur: lead (96 bayt) → imza başlığı (ölçü, MD5, SHA1, SHA256) →
əsas başlıq (ad, versiya, fayl siyahısı, asılılıqlar, skriptlər) →
cpio "newc" yükü (gzip). Başlıqlar "region" teqləri ilə yazılır —
müasir `rpm`/`dnf` bunu tələb edir.
"""

from __future__ import annotations

import gzip
import hashlib
import struct
import time

# Teq tipləri
_INT16, _INT32, _STRING, _BIN, _ARRAY, _I18N = 3, 4, 6, 7, 8, 9
_TIP_HİZALAMA = {_INT16: 2, _INT32: 4}

# rpmsense bayraqları
_LESS, _GREATER, _EQUAL, _RPMLIB = 2, 4, 8, 1 << 24


def _başlıq(teqlər: dict[int, tuple[int, object]], region: int) -> bytes:
    """{teq: (tip, dəyər)} → başlıq blobu (region teqi ilə)."""
    giriş = []
    data = bytearray()
    for teq in sorted(teqlər):
        tip, d = teqlər[teq]
        h = _TIP_HİZALAMA.get(tip, 1)
        while len(data) % h:
            data.append(0)
        ofs = len(data)
        if tip == _INT32:
            v = d if isinstance(d, list) else [d]
            data += struct.pack(f">{len(v)}i", *v)
            say = len(v)
        elif tip == _INT16:
            v = d if isinstance(d, list) else [d]
            data += struct.pack(f">{len(v)}H", *v)
            say = len(v)
        elif tip in (_STRING,):
            data += str(d).encode("utf-8") + b"\0"
            say = 1
        elif tip in (_ARRAY, _I18N):
            v = d if isinstance(d, list) else [d]
            for s in v:
                data += str(s).encode("utf-8") + b"\0"
            say = len(v)
        elif tip == _BIN:
            data += bytes(d)
            say = len(d)
        else:
            raise ValueError(tip)
        giriş.append((teq, tip, ofs, say))
    # Region: ilk giriş, məlumatın sonunda 16 baytlıq "trailer"
    il = len(giriş) + 1
    trailer_ofs = len(data)
    data += struct.pack(">iiii", region, _BIN, -il * 16, 16)
    indeks = struct.pack(">iiii", region, _BIN, trailer_ofs, 16) + b"".join(
        struct.pack(">iiii", *g) for g in giriş)
    return (b"\x8e\xad\xe8\x01\x00\x00\x00\x00" +
            struct.pack(">ii", il, len(data)) + indeks + bytes(data))


def _cpio(fayllar: list[tuple[str, bytes, int, int]], zaman: int) -> bytes:
    """[(yol, məzmun, rejim, inode)] → cpio newc (./ prefiksi ilə)."""
    n = bytearray()

    def giriş(ad: str, d: bytes, rejim: int, ino: int) -> None:
        a = ad.encode("utf-8") + b"\0"
        n.extend(("070701" + "".join(f"{x:08x}" for x in (
            ino, rejim, 0, 0, 1, zaman, len(d), 0, 0, 0, 0, len(a), 0))
                  ).encode("ascii"))
        n.extend(a)
        while len(n) % 4:
            n.append(0)
        n.extend(d)
        while len(n) % 4:
            n.append(0)

    for yol, d, rejim, ino in fayllar:
        giriş("./" + yol.lstrip("/"), d, rejim, ino)
    giriş("TRAILER!!!", b"", 0, 0)
    return bytes(n)


def rpm(ad: str, versiya: str, xülasə: str, təsvir: str, naşir: str,
        fayllar: dict[str, tuple[bytes, int]], qovluqlar: list[str],
        tələblər: list[tuple[str, str, int]],
        postin: str = "", postun: str = "", lisenziya: str = "Proprietary",
        url: str = "") -> bytes:
    """
    fayllar: {"/usr/bin/x": (məzmun, rejim)}; qovluqlar: paketin sahib
    olduğu qovluqlar ("/usr/lib/x"); tələblər: [(ad, versiya, bayraq)].
    """
    zaman = int(time.time())
    buraxılış = "1"
    girişlər: list[tuple[str, bytes, int]] = []
    for q in sorted(qovluqlar):
        girişlər.append((q, b"", 0o40755))
    for y, (d, r) in sorted(fayllar.items()):
        girişlər.append((y, d, 0o100000 | r))
    payload = _cpio([(y, d, r, i + 1) for i, (y, d, r) in
                     enumerate(girişlər)], zaman)
    sıxılmış = gzip.compress(payload, 9, mtime=zaman)

    dir_adları: list[str] = []
    dir_ind, baz_adlar = [], []
    for y, _, _ in girişlər:
        q, _, b = y.rpartition("/")
        q += "/"
        if q not in dir_adları:
            dir_adları.append(q)
        dir_ind.append(dir_adları.index(q))
        baz_adlar.append(b)
    say = len(girişlər)
    tələb = [("rpmlib(CompressedFileNames)", "3.0.4-1",
              _RPMLIB | _LESS | _EQUAL),
             ("rpmlib(PayloadFilesHavePrefix)", "4.0-1",
              _RPMLIB | _LESS | _EQUAL),
             ("rpmlib(FileDigests)", "4.6.0-1", _RPMLIB | _LESS | _EQUAL)]
    if postin or postun:
        tələb.append(("/bin/sh", "", 0))
    tələb += tələblər
    teqlər: dict[int, tuple[int, object]] = {
        100: (_ARRAY, ["C"]),
        1000: (_STRING, ad), 1001: (_STRING, versiya),
        1002: (_STRING, buraxılış),
        1004: (_I18N, [xülasə]), 1005: (_I18N, [təsvir or xülasə]),
        1006: (_INT32, zaman), 1007: (_STRING, "alqor"),
        1009: (_INT32, sum(len(d) for _, d, _ in girişlər)),
        1011: (_STRING, naşir),
        1014: (_STRING, lisenziya), 1016: (_I18N, ["Applications/Alqor"]),
        1021: (_STRING, "linux"), 1022: (_STRING, "noarch"),
        1028: (_INT32, [len(d) if r & 0o100000 else 4096
                        for _, d, r in girişlər]),
        1030: (_INT16, [r for _, _, r in girişlər]),
        1033: (_INT16, [0] * say),
        1034: (_INT32, [zaman] * say),
        1035: (_ARRAY, [hashlib.sha256(d).hexdigest() if r & 0o100000
                        else "" for _, d, r in girişlər]),
        1036: (_ARRAY, [""] * say),
        1037: (_INT32, [0] * say),
        1039: (_ARRAY, ["root"] * say), 1040: (_ARRAY, ["root"] * say),
        1044: (_STRING, f"{ad}-{versiya}-{buraxılış}.src.rpm"),
        1047: (_ARRAY, [ad]), 1112: (_INT32, [_EQUAL]),
        1113: (_ARRAY, [f"{versiya}-{buraxılış}"]),
        1048: (_INT32, [b for _, _, b in tələb]),
        1049: (_ARRAY, [a for a, _, _ in tələb]),
        1050: (_ARRAY, [v for _, v, _ in tələb]),
        1064: (_STRING, "4.18.0"),
        1095: (_INT32, [1] * say), 1096: (_INT32, list(range(1, say + 1))),
        1097: (_ARRAY, [""] * say),
        1116: (_INT32, dir_ind), 1117: (_ARRAY, baz_adlar),
        1118: (_ARRAY, dir_adları),
        1124: (_STRING, "cpio"), 1125: (_STRING, "gzip"),
        1126: (_STRING, "9"),
        5011: (_INT32, [8]),                           # SHA256 fayl həzmi
        # Yük həzmləri (rpm ≥ 4.14; yeni rpm versiyaları -K-da yoxlayır)
        5092: (_ARRAY, [hashlib.sha256(sıxılmış).hexdigest()]),
        5093: (_INT32, [8]),                           # SHA256
        5097: (_ARRAY, [hashlib.sha256(payload).hexdigest()]),
    }
    if url:
        teqlər[1020] = (_STRING, url)
    if postin:
        teqlər[1024] = (_STRING, postin)
        teqlər[1086] = (_STRING, "/bin/sh")
    if postun:
        teqlər[1026] = (_STRING, postun)
        teqlər[1088] = (_STRING, "/bin/sh")
    başlıq = _başlıq(teqlər, 63)                   # RPMTAG_HEADERIMMUTABLE

    imza = _başlıq({
        1000: (_INT32, len(başlıq) + len(sıxılmış)),
        1004: (_BIN, hashlib.md5(başlıq + sıxılmış).digest()),
        1007: (_INT32, len(payload)),
        269: (_STRING, hashlib.sha1(başlıq).hexdigest()),
        273: (_STRING, hashlib.sha256(başlıq).hexdigest()),
    }, 62)                                         # RPMTAG_HEADERSIGNATURES
    imza += b"\0" * (-len(imza) % 8)

    lead = (b"\xed\xab\xee\xdb" + struct.pack(">BBhh", 3, 0, 0, 0) +
            f"{ad}-{versiya}-{buraxılış}".encode("utf-8")[:65].ljust(66,
                                                                    b"\0")
            + struct.pack(">hh", 1, 5) + b"\0" * 16)
    assert len(lead) == 96
    return lead + imza + başlıq + sıxılmış
