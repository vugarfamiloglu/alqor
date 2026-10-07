"""
TrueType şriftini oxuma və alt dəstə (subset) yaratma — `pdf` modulu üçün.

Yalnız `glyf` əsaslı TrueType (.ttf) dəstəklənir; CFF (.otf) və .ttc
kolleksiyaları üçün aydın xəta verilir. Alt dəstədə qlif nömrələri
DƏYİŞMİR (istifadə olunmayan qliflər boşaldılır) — PDF-də
`CIDToGIDMap /Identity` ilə işləmək üçün.
"""

from __future__ import annotations

import struct
from pathlib import Path


class ŞriftXətası(ValueError):
    pass


def _cəm(b: bytes) -> int:
    b = b + b"\0" * (-len(b) % 4)
    return sum(struct.unpack(f">{len(b) // 4}I", b)) & 0xFFFFFFFF


class TTF:
    def __init__(self, data: bytes, ad: str = ""):
        self.data = data
        self.ad = ad
        if data[:4] == b"ttcf":
            raise ŞriftXətası(f"{ad}: .ttc kolleksiyası dəstəklənmir — "
                              ".ttf faylı verin")
        if data[:4] == b"OTTO":
            raise ŞriftXətası(f"{ad}: CFF əsaslı OpenType (.otf) "
                              "dəstəklənmir — TrueType (.ttf) verin")
        if data[:4] not in (b"\x00\x01\x00\x00", b"true"):
            raise ŞriftXətası(f"{ad}: TrueType şrifti deyil")
        n = struct.unpack(">H", data[4:6])[0]
        self.cədvəllər: dict[str, tuple[int, int]] = {}
        for i in range(n):
            tag, _, ofs, uz = struct.unpack(">4sIII",
                                            data[12 + i * 16:28 + i * 16])
            self.cədvəllər[tag.decode("latin-1")] = (ofs, uz)
        for t in ("head", "hhea", "hmtx", "maxp", "cmap", "loca", "glyf"):
            if t not in self.cədvəllər:
                raise ŞriftXətası(f"{ad}: `{t}` cədvəli yoxdur")
        h = self.c("head")
        self.vahid = struct.unpack(">H", h[18:20])[0]
        self.bbox = struct.unpack(">hhhh", h[36:44])
        self.loca_növ = struct.unpack(">h", h[50:52])[0]
        hh = self.c("hhea")
        self.yuxarı, self.aşağı = struct.unpack(">hh", hh[4:8])
        self.metrik_sayı = struct.unpack(">H", hh[34:36])[0]
        self.qlif_sayı = struct.unpack(">H", self.c("maxp")[4:6])[0]
        hm = self.c("hmtx")
        self.enlər = []
        son = 0
        for i in range(self.qlif_sayı):
            if i < self.metrik_sayı:
                son = struct.unpack(">H", hm[i * 4:i * 4 + 2])[0]
            self.enlər.append(son)
        self.cmap = self._cmap()
        self.böyük_hərf = self.yuxarı
        self.kursiv_bucaq = 0.0
        self.bayraqlar = 32
        if "OS/2" in self.cədvəllər:
            o = self.c("OS/2")
            if len(o) >= 90 and struct.unpack(">H", o[:2])[0] >= 2:
                self.böyük_hərf = struct.unpack(">h", o[88:90])[0]
            if len(o) >= 10:
                fs = struct.unpack(">H", o[8:10])[0]
                if fs & 0x0002:
                    raise ŞriftXətası(f"{ad}: şriftin lisenziyası "
                                      "daxil etməyə icazə vermir")
        if "post" in self.cədvəllər:
            p = self.c("post")
            self.kursiv_bucaq = struct.unpack(">i", p[4:8])[0] / 65536
            if struct.unpack(">I", p[12:16])[0]:
                self.bayraqlar |= 1                  # sabit en
        if self.kursiv_bucaq:
            self.bayraqlar |= 64
        self.ps_ad = self._ps_ad() or "AlqorSrift"

    def c(self, t: str) -> bytes:
        ofs, uz = self.cədvəllər[t]
        return self.data[ofs:ofs + uz]

    def _ps_ad(self) -> str | None:
        if "name" not in self.cədvəllər:
            return None
        n = self.c("name")
        say, str_ofs = struct.unpack(">HH", n[2:6])
        for i in range(say):
            pid, eid, lid, nid, uz, ofs = struct.unpack(
                ">HHHHHH", n[6 + i * 12:18 + i * 12])
            if nid != 6:
                continue
            b = n[str_ofs + ofs:str_ofs + ofs + uz]
            try:
                s = b.decode("utf-16-be") if pid in (0, 3) else \
                    b.decode("latin-1")
            except UnicodeDecodeError:
                continue
            s = "".join(ch for ch in s if ch.isascii() and ch.isalnum() or
                        ch in "-_")
            if s:
                return s
        return None

    def _cmap(self) -> dict[int, int]:
        c = self.c("cmap")
        say = struct.unpack(">H", c[2:4])[0]
        seçim = None
        for i in range(say):
            pid, eid, ofs = struct.unpack(">HHI", c[4 + i * 8:12 + i * 8])
            f = struct.unpack(">H", c[ofs:ofs + 2])[0]
            prioritet = {(3, 10, 12): 0, (0, 4, 12): 1, (0, 6, 12): 1,
                         (3, 1, 4): 2, (0, 3, 4): 3, (0, 1, 4): 3,
                         (0, 0, 4): 4}.get((pid, eid, f))
            if prioritet is not None and (seçim is None or
                                          prioritet < seçim[0]):
                seçim = (prioritet, ofs, f)
        if seçim is None:
            raise ŞriftXətası(f"{self.ad}: Unicode cmap cədvəli yoxdur")
        _, ofs, f = seçim
        n: dict[int, int] = {}
        if f == 4:
            seg2 = struct.unpack(">H", c[ofs + 6:ofs + 8])[0]
            seg = seg2 // 2
            b = ofs + 14
            son = struct.unpack(f">{seg}H", c[b:b + seg2])
            baş = struct.unpack(f">{seg}H", c[b + seg2 + 2:b + 2 * seg2 + 2])
            delta = struct.unpack(f">{seg}h",
                                  c[b + 2 * seg2 + 2:b + 3 * seg2 + 2])
            ro_b = b + 3 * seg2 + 2
            ro = struct.unpack(f">{seg}H", c[ro_b:ro_b + seg2])
            for i in range(seg):
                for kod in range(baş[i], son[i] + 1):
                    if kod == 0xFFFF:
                        continue
                    if ro[i] == 0:
                        g = (kod + delta[i]) & 0xFFFF
                    else:
                        a = ro_b + i * 2 + ro[i] + (kod - baş[i]) * 2
                        g = struct.unpack(">H", c[a:a + 2])[0]
                        if g:
                            g = (g + delta[i]) & 0xFFFF
                    if g:
                        n[kod] = g
        else:                                        # format 12
            say = struct.unpack(">I", c[ofs + 12:ofs + 16])[0]
            for i in range(say):
                a, b, g = struct.unpack(">III", c[ofs + 16 + i * 12:
                                                  ofs + 28 + i * 12])
                for kod in range(a, b + 1):
                    n[kod] = g + kod - a
        return n

    def qlif(self, ch: str) -> int:
        return self.cmap.get(ord(ch), 0)

    def en(self, gid: int) -> float:
        """1000 vahidlik ölçüdə en (PDF `W` massivi üçün)."""
        return self.enlər[gid] * 1000 / self.vahid

    def mətn_eni(self, s: str, ölçü: float) -> float:
        return sum(self.enlər[self.cmap.get(ord(ch), 0)] for ch in s) * \
            ölçü / self.vahid

    def _loca(self) -> list[int]:
        l = self.c("loca")
        if self.loca_növ == 0:
            return [x * 2 for x in struct.unpack(f">{self.qlif_sayı + 1}H",
                                                 l[:(self.qlif_sayı + 1) * 2])]
        return list(struct.unpack(f">{self.qlif_sayı + 1}I",
                                  l[:(self.qlif_sayı + 1) * 4]))

    def alt_dəst(self, qliflər: set[int]) -> bytes:
        loca = self._loca()
        glyf = self.c("glyf")
        lazım = {0} | {g for g in qliflər if g < self.qlif_sayı}
        növbə = list(lazım)
        while növbə:                                  # tərkibli qliflər
            g = növbə.pop()
            d = glyf[loca[g]:loca[g + 1]]
            if len(d) < 10 or struct.unpack(">h", d[:2])[0] >= 0:
                continue
            i = 10
            while True:
                bayraq, komp = struct.unpack(">HH", d[i:i + 4])
                if komp not in lazım:
                    lazım.add(komp)
                    növbə.append(komp)
                i += 4 + (4 if bayraq & 1 else 2)
                if bayraq & 8:
                    i += 2
                elif bayraq & 0x40:
                    i += 4
                elif bayraq & 0x80:
                    i += 8
                if not bayraq & 0x20:
                    break
        yeni_glyf = bytearray()
        yeni_loca = []
        for g in range(self.qlif_sayı):
            yeni_loca.append(len(yeni_glyf))
            if g in lazım:
                d = glyf[loca[g]:loca[g + 1]]
                yeni_glyf += d + b"\0" * (-len(d) % 4)
        yeni_loca.append(len(yeni_glyf))
        head = bytearray(self.c("head"))
        head[8:12] = b"\0\0\0\0"
        head[50:52] = struct.pack(">h", 1)
        cədvəllər = {
            "head": bytes(head), "hhea": self.c("hhea"),
            "hmtx": self.c("hmtx"), "maxp": self.c("maxp"),
            "loca": struct.pack(f">{len(yeni_loca)}I", *yeni_loca),
            "glyf": bytes(yeni_glyf),
        }
        for t in ("cvt ", "fpgm", "prep", "OS/2", "post", "cmap"):
            if t in self.cədvəllər:
                cədvəllər[t] = self.c(t)
        if "post" in cədvəllər:                       # qlif adları lazım deyil
            cədvəllər["post"] = b"\x00\x03\x00\x00" + cədvəllər["post"][4:32]
        return _yığ(cədvəllər)


def _yığ(cədvəllər: dict[str, bytes]) -> bytes:
    adlar = sorted(cədvəllər)
    n = len(adlar)
    q = 1
    while q * 2 <= n:
        q *= 2
    bas = struct.pack(">IHHHH", 0x00010000, n, q * 16, q.bit_length() - 1,
                      n * 16 - q * 16)
    ofs = 12 + n * 16
    kat = bytearray()
    məlumat = bytearray()
    for t in adlar:
        d = cədvəllər[t]
        kat += struct.pack(">4sIII", t.encode("latin-1"), _cəm(d),
                           ofs + len(məlumat), len(d))
        məlumat += d + b"\0" * (-len(d) % 4)
    şrift = bytearray(bas + kat + məlumat)
    if "head" in cədvəllər:
        düzəliş = (0xB1B0AFBA - _cəm(bytes(şrift))) & 0xFFFFFFFF
        h = ofs + sum(len(cədvəllər[t]) + (-len(cədvəllər[t]) % 4)
                      for t in adlar[:adlar.index("head")])
        şrift[h + 8:h + 12] = struct.pack(">I", düzəliş)
    return bytes(şrift)


# Sistem şriftləri: (adi, qalın, kursiv, qalın kursiv)
SİSTEM_ŞRİFTLƏRİ = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"),
    ("/usr/share/fonts/TTF/DejaVuSans.ttf",
     "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/TTF/DejaVuSans-Oblique.ttf",
     "/usr/share/fonts/TTF/DejaVuSans-BoldOblique.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"),
    ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
     "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
     "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf",
     "/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf",
     "C:/Windows/Fonts/ariali.ttf", "C:/Windows/Fonts/arialbi.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf",
     "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/segoeuiz.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
     "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf",
     "/Library/Fonts/Arial Italic.ttf", "/Library/Fonts/Arial Bold Italic.ttf"),
]


# Əsas şriftdə olmayan simvollar (məs. ₼ U+20BC) üçün axtarılır
EHTİYAT_ŞRİFTLƏR = [
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/gnu-free/FreeSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf",
    "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/seguisym.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]


def sistem_şrifti() -> tuple[str | None, ...] | None:
    for dəst in SİSTEM_ŞRİFTLƏRİ:
        if Path(dəst[0]).is_file():
            return tuple(p if Path(p).is_file() else None for p in dəst)
    return None
