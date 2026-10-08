"""
SquashFS 4.0 yazıcısı (zlib/gzip sıxma) — `mksquashfs` olmadan.

AppImage üçün: fayllar, qovluqlar və simvolik keçidlər; fraqmentlər və
xattr yoxdur (NO_FRAGMENTS | NO_XATTRS). Bütün obyektlər root:root.
"""

from __future__ import annotations

import struct
import time
import zlib

BLOK = 1 << 17                          # 128 KiB
_META = 8192
_YOX = 0xFFFFFFFFFFFFFFFF

_DIR, _FAYL, _KEÇİD = 1, 2, 3


class _Meta:
    """Metadata axını: 8 KiB-lıq bloklar, hər biri 2 baytlıq başlıqla."""

    def __init__(self):
        self.yazılmış = bytearray()     # sıxılmış bloklar
        self.bufer = bytearray()

    def mövqe(self) -> tuple[int, int]:
        """(cari blokun sıxılmış başlanğıcı, bufer daxilində ofset)"""
        return len(self.yazılmış), len(self.bufer)

    def əlavə(self, d: bytes) -> None:
        self.bufer += d
        while len(self.bufer) >= _META:
            self._boşalt(bytes(self.bufer[:_META]))
            del self.bufer[:_META]

    def _boşalt(self, blok: bytes) -> None:
        s = zlib.compress(blok, 9)
        if len(s) < len(blok):
            self.yazılmış += struct.pack("<H", len(s)) + s
        else:
            self.yazılmış += struct.pack("<H", len(blok) | 0x8000) + blok

    def bitir(self) -> bytes:
        if self.bufer:
            self._boşalt(bytes(self.bufer))
            self.bufer = bytearray()
        return bytes(self.yazılmış)


class _Qovşaq:
    def __init__(self, ad: str, növ: int, rejim: int, məzmun: bytes = b""):
        self.ad, self.növ, self.rejim, self.məzmun = ad, növ, rejim, məzmun
        self.uşaqlar: dict[str, _Qovşaq] = {}
        self.nömrə = 0
        self.ref = (0, 0)
        self.blok_başı = 0
        self.blok_ölçüləri: list[int] = []


def squashfs(fayllar: dict[str, tuple[bytes, int]],
             keçidlər: dict[str, str] | None = None,
             zaman: int | None = None) -> bytes:
    """
    fayllar: {"usr/bin/x": (məzmun, rejim)}; keçidlər: {"a": "hədəf"}.
    Qovluqlar avtomatik yaranır (0755).
    """
    zaman = int(time.time()) if zaman is None else zaman
    kök = _Qovşaq("", _DIR, 0o755)

    def qovluq(yol: list[str]) -> _Qovşaq:
        q = kök
        for h in yol:
            q = q.uşaqlar.setdefault(h, _Qovşaq(h, _DIR, 0o755))
        return q

    for yol, (d, r) in fayllar.items():
        h = yol.strip("/").split("/")
        qovluq(h[:-1]).uşaqlar[h[-1]] = _Qovşaq(h[-1], _FAYL, r & 0o7777, d)
    for yol, hədəf in (keçidlər or {}).items():
        h = yol.strip("/").split("/")
        qovluq(h[:-1]).uşaqlar[h[-1]] = _Qovşaq(h[-1], _KEÇİD, 0o777,
                                                hədəf.encode("utf-8"))

    # Post-order nömrələmə (kök sonuncu)
    sıra: list[_Qovşaq] = []

    def gəz(q: _Qovşaq) -> None:
        for a in sorted(q.uşaqlar, key=lambda x: x.encode("utf-8")):
            gəz(q.uşaqlar[a])
        sıra.append(q)
    gəz(kök)
    for i, q in enumerate(sıra, 1):
        q.nömrə = i
    valideyn = {id(u): q for q in sıra for u in q.uşaqlar.values()}

    # Məlumat blokları (superblokdan sonra)
    çıxış = bytearray(96)
    for q in sıra:
        if q.növ != _FAYL:
            continue
        q.blok_başı = len(çıxış)
        for i in range(0, len(q.məzmun), BLOK):
            p = q.məzmun[i:i + BLOK]
            s = zlib.compress(p, 9)
            if len(s) < len(p):
                çıxış += s
                q.blok_ölçüləri.append(len(s))
            else:
                çıxış += p
                q.blok_ölçüləri.append(len(p) | (1 << 24))

    inodlar, qovluqlar = _Meta(), _Meta()
    for q in sıra:
        q.ref = inodlar.mövqe()
        baş = struct.pack("<HHHHII", q.növ, q.rejim, 0, 0, zaman, q.nömrə)
        if q.növ == _FAYL:
            inodlar.əlavə(baş + struct.pack(
                "<IIII", q.blok_başı, 0xFFFFFFFF, 0, len(q.məzmun)) +
                struct.pack(f"<{len(q.blok_ölçüləri)}I", *q.blok_ölçüləri))
        elif q.növ == _KEÇİD:
            inodlar.əlavə(baş + struct.pack("<II", 1, len(q.məzmun)) +
                          q.məzmun)
        else:
            dir_ref = qovluqlar.mövqe()
            siyahı = bytearray()
            uşaqlar = [q.uşaqlar[a] for a in sorted(
                q.uşaqlar, key=lambda x: x.encode("utf-8"))]
            i = 0
            while i < len(uşaqlar):
                blok = uşaqlar[i].ref[0]
                baza = uşaqlar[i].nömrə
                qrup = []
                while i < len(uşaqlar) and len(qrup) < 256 and \
                        uşaqlar[i].ref[0] == blok and \
                        abs(uşaqlar[i].nömrə - baza) < 32767:
                    qrup.append(uşaqlar[i])
                    i += 1
                siyahı += struct.pack("<III", len(qrup) - 1, blok, baza)
                for u in qrup:
                    ad = u.ad.encode("utf-8")
                    siyahı += struct.pack("<HhHH", u.ref[1],
                                          u.nömrə - baza, u.növ,
                                          len(ad) - 1) + ad
            qovluqlar.əlavə(bytes(siyahı))
            alt = sum(1 for u in uşaqlar if u.növ == _DIR)
            ana = valideyn.get(id(q))
            ana_n = ana.nömrə if ana is not None else len(sıra) + 1
            inodlar.əlavə(baş + struct.pack(
                "<IIHHI", dir_ref[0], 2 + alt, len(siyahı) + 3, dir_ref[1],
                ana_n))

    inod_başı = len(çıxış)
    çıxış += inodlar.bitir()
    qovluq_başı = len(çıxış)
    çıxış += qovluqlar.bitir()
    fraqment_başı = len(çıxış)
    id_meta = len(çıxış)
    id_m = _Meta()
    id_m.əlavə(struct.pack("<I", 0))
    çıxış += id_m.bitir()
    id_başı = len(çıxış)
    çıxış += struct.pack("<Q", id_meta)
    istifadə = len(çıxış)
    kök_ref = (kök.ref[0] << 16) | kök.ref[1]
    çıxış[0:96] = struct.pack(
        "<IIIIIHHHHHHQQQQQQQQ", 0x73717368, len(sıra), zaman, BLOK, 0,
        1, 17, 0x10 | 0x200, 1, 4, 0, kök_ref, istifadə, id_başı, _YOX,
        inod_başı, qovluq_başı, fraqment_başı, _YOX)
    çıxış += b"\0" * (-len(çıxış) % 4096)
    return bytes(çıxış)
