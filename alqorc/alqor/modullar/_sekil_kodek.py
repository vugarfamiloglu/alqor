"""
`şəkil` modulunun kodekləri — xarici kitabxanasız, təmiz Python.

Hamısı RGBA (hər piksel 4 bayt, sətir-sətir) `bytearray` ilə işləyir:

    aç(baytlar) -> (en, hündürlük, rgba)
    yaz(format, en, hündürlük, rgba, keyfiyyət) -> baytlar

Formatlar: PNG (bütün rəng növləri, 1–16 bit, Adam7), JPEG (baseline və
progressive, 4:4:4 / 4:2:2 / 4:2:0, boz, CMYK, EXIF istiqaməti; yazma —
baseline), GIF (ilk kadr; yazma — 256 rəngə median-cut), BMP (1/4/8/24/32
bit, RLE-siz), PPM/PGM (P2 P3 P5 P6).
"""

from __future__ import annotations

import math
import struct
import zlib


class KodekXətası(ValueError):
    pass


def format_tap(b: bytes) -> str | None:
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if b[:2] == b"BM":
        return "bmp"
    if b[:2] in (b"P2", b"P3", b"P5", b"P6"):
        return "ppm"
    return None


def aç(b: bytes) -> tuple[int, int, bytearray, dict]:
    f = format_tap(b)
    if f is None:
        raise KodekXətası("şəkil formatı tanınmadı (PNG, JPEG, GIF, BMP, "
                          "PPM dəstəklənir)")
    return {"png": png_aç, "jpeg": jpeg_aç, "gif": gif_aç, "bmp": bmp_aç,
            "ppm": ppm_aç}[f](b)


def yaz(format: str, en: int, h: int, rgba: bytearray,
        keyfiyyət: int = 90) -> bytes:
    if format == "png":
        return png_yaz(en, h, rgba)
    if format == "jpeg":
        return jpeg_yaz(en, h, rgba, keyfiyyət)
    if format == "gif":
        return gif_yaz(en, h, rgba)
    if format == "bmp":
        return bmp_yaz(en, h, rgba)
    if format == "ppm":
        return ppm_yaz(en, h, rgba)
    raise KodekXətası(f"`{format}` formatında yazmaq olmur")


# ═══════════════════════════════════════════════════════════════════════
#  PNG
# ═══════════════════════════════════════════════════════════════════════

_ADAM7 = [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
          (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]


def _süzgəci_aç(data: bytes, i: int, sətir_uz: int, sətir_sayı: int,
                bpp: int) -> tuple[list[bytearray], int]:
    sətirlər = []
    əvvəlki = bytearray(sətir_uz)
    for _ in range(sətir_sayı):
        if i >= len(data):
            raise KodekXətası("PNG: məlumat natamamdır")
        f = data[i]
        s = bytearray(data[i + 1:i + 1 + sətir_uz])
        i += 1 + sətir_uz
        if len(s) < sətir_uz:
            raise KodekXətası("PNG: məlumat natamamdır")
        if f == 1:
            for x in range(bpp, sətir_uz):
                s[x] = (s[x] + s[x - bpp]) & 255
        elif f == 2:
            s = bytearray((a + b) & 255 for a, b in zip(s, əvvəlki))
        elif f == 3:
            for x in range(sətir_uz):
                sol = s[x - bpp] if x >= bpp else 0
                s[x] = (s[x] + ((sol + əvvəlki[x]) >> 1)) & 255
        elif f == 4:
            for x in range(sətir_uz):
                a = s[x - bpp] if x >= bpp else 0
                b = əvvəlki[x]
                c = əvvəlki[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                s[x] = (s[x] + pr) & 255
        elif f != 0:
            raise KodekXətası(f"PNG: naməlum süzgəc {f}")
        sətirlər.append(s)
        əvvəlki = s
    return sətirlər, i


def png_aç(b: bytes) -> tuple[int, int, bytearray, dict]:
    i = 8
    idat = []
    plte = b""
    trns = b""
    ihdr = None
    məlumat: dict = {}
    while i + 8 <= len(b):
        uz, növ = struct.unpack(">I4s", b[i:i + 8])
        c = b[i + 8:i + 8 + uz]
        i += 12 + uz
        if növ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", c)
        elif növ == b"PLTE":
            plte = c
        elif növ == b"tRNS":
            trns = c
        elif növ == b"IDAT":
            idat.append(c)
        elif növ == b"pHYs" and len(c) == 9 and c[8] == 1:
            məlumat["dpi"] = round(struct.unpack(">I", c[:4])[0] * 0.0254)
        elif növ == b"IEND":
            break
    if ihdr is None:
        raise KodekXətası("PNG: IHDR yoxdur")
    en, h, dərinlik, növ, _, _, interlace = ihdr
    if en == 0 or h == 0 or en * h > 100_000_000:
        raise KodekXətası("PNG: ölçü yanlışdır")
    kanal = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(növ)
    if kanal is None or dərinlik not in (1, 2, 4, 8, 16):
        raise KodekXətası("PNG: rəng növü dəstəklənmir")
    try:
        data = zlib.decompress(b"".join(idat))
    except zlib.error as x:
        raise KodekXətası(f"PNG: sıxılmış məlumat pozulub ({x})")
    bpp = max(1, kanal * dərinlik // 8)
    rgba = bytearray(en * h * 4)

    palitra = [tuple(plte[j:j + 3]) + (255,) for j in range(0, len(plte), 3)]
    for j, a in enumerate(trns if növ == 3 else b""):
        if j < len(palitra):
            palitra[j] = palitra[j][:3] + (a,)
    şəffaf = None
    if trns and növ == 0:
        şəffaf = struct.unpack(">H", trns[:2])[0]
    elif trns and növ == 2:
        şəffaf = struct.unpack(">HHH", trns[:6])

    def piksellər(s: bytearray, n: int):
        """Sətirdən n pikselin RGBA dəyərləri."""
        if dərinlik < 8:
            mask = (1 << dərinlik) - 1
            for x in range(n):
                bit = x * dərinlik
                v = (s[bit >> 3] >> (8 - dərinlik - (bit & 7))) & mask
                if növ == 3:
                    yield palitra[v] if v < len(palitra) else (0, 0, 0, 255)
                else:
                    g = v * 255 // mask
                    yield (g, g, g, 0 if şəffaf == v else 255)
            return
        addım = 2 if dərinlik == 16 else 1
        for x in range(n):
            o = x * kanal * addım
            if dərinlik == 16:
                v = [(s[o + 2 * k] << 8) | s[o + 2 * k + 1]
                     for k in range(kanal)]
                v8 = [e >> 8 for e in v]
            else:
                v = v8 = s[o:o + kanal]
            if növ == 0:
                yield (v8[0], v8[0], v8[0],
                       0 if şəffaf is not None and v[0] == şəffaf else 255)
            elif növ == 2:
                yield (v8[0], v8[1], v8[2],
                       0 if şəffaf is not None and tuple(v[:3]) == şəffaf
                       else 255)
            elif növ == 3:
                yield palitra[v[0]] if v[0] < len(palitra) else (0, 0, 0,
                                                                  255)
            elif növ == 4:
                yield (v8[0], v8[0], v8[0], v8[1])
            else:
                yield tuple(v8)

    if interlace:
        i = 0
        for x0, y0, dx, dy in _ADAM7:
            pe = (en - x0 + dx - 1) // dx
            ph = (h - y0 + dy - 1) // dy
            if pe == 0 or ph == 0:
                continue
            sətir_uz = (pe * kanal * dərinlik + 7) // 8
            sətirlər, i = _süzgəci_aç(data, i, sətir_uz, ph, bpp)
            for sy, s in enumerate(sətirlər):
                y = y0 + sy * dy
                for sx, p in enumerate(piksellər(s, pe)):
                    o = (y * en + x0 + sx * dx) * 4
                    rgba[o:o + 4] = bytes(p)
    else:
        sətir_uz = (en * kanal * dərinlik + 7) // 8
        sətirlər, _ = _süzgəci_aç(data, 0, sətir_uz, h, bpp)
        for y, s in enumerate(sətirlər):
            o = y * en * 4
            if növ == 6 and dərinlik == 8:
                rgba[o:o + en * 4] = s
            elif növ == 2 and dərinlik == 8 and şəffaf is None:
                r = rgba
                r[o:o + en * 4:4] = s[0::3]
                r[o + 1:o + en * 4:4] = s[1::3]
                r[o + 2:o + en * 4:4] = s[2::3]
                r[o + 3:o + en * 4:4] = b"\xff" * en
            else:
                rgba[o:o + en * 4] = bytes(
                    k for p in piksellər(s, en) for k in p)
    return en, h, rgba, məlumat


def _png_parça(növ: bytes, c: bytes) -> bytes:
    return (struct.pack(">I", len(c)) + növ + c +
            struct.pack(">I", zlib.crc32(növ + c) & 0xFFFFFFFF))


def png_yaz(en: int, h: int, rgba: bytearray) -> bytes:
    şəffaf = bytes(rgba[3::4]) != b"\xff" * (en * h)
    if şəffaf:
        kanal, növ, sətir = 4, 6, en * 4
        mənbə = rgba
    else:
        kanal, növ, sətir = 3, 2, en * 3
        mənbə = bytearray(en * h * 3)
        mənbə[0::3] = rgba[0::4]
        mənbə[1::3] = rgba[1::4]
        mənbə[2::3] = rgba[2::4]
    xam = bytearray()
    əvvəlki = bytes(sətir)
    for y in range(h):
        s = bytes(mənbə[y * sətir:(y + 1) * sətir])
        # "Up" süzgəci — sürətli və adətən 0-dan yaxşı sıxılır
        up = bytes((a - b) & 255 for a, b in zip(s, əvvəlki))
        xam += b"\x02" + up
        əvvəlki = s
    ihdr = struct.pack(">IIBBBBB", en, h, 8, növ, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _png_parça(b"IHDR", ihdr) +
            _png_parça(b"IDAT", zlib.compress(bytes(xam), 6)) +
            _png_parça(b"IEND", b""))


# ═══════════════════════════════════════════════════════════════════════
#  JPEG
# ═══════════════════════════════════════════════════════════════════════

ZİQZAQ = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19,
          26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28, 35, 42, 49,
          56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52,
          45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]

_COS = [[(math.sqrt(0.5) if u == 0 else 1.0) * 0.5 *
         math.cos((2 * x + 1) * u * math.pi / 16) for u in range(8)]
        for x in range(8)]


def _idct(c: list[float]) -> list[int]:
    """8×8 tərs DCT (ayrılan): c — təbii sırada dekvantlanmış əmsallar."""
    ara = [0.0] * 64
    C = _COS
    for v in range(8):                           # sətirlər üzrə (u → x)
        r = c[v * 8:v * 8 + 8]
        if not any(r[1:]):
            d = r[0] * C[0][0]
            for x in range(8):
                ara[v * 8 + x] = d
            continue
        for x in range(8):
            cx = C[x]
            ara[v * 8 + x] = (r[0] * cx[0] + r[1] * cx[1] + r[2] * cx[2] +
                              r[3] * cx[3] + r[4] * cx[4] + r[5] * cx[5] +
                              r[6] * cx[6] + r[7] * cx[7])
    n = [0] * 64
    for x in range(8):                           # sütunlar üzrə (v → y)
        s = [ara[v * 8 + x] for v in range(8)]
        for y in range(8):
            cy = C[y]
            d = (s[0] * cy[0] + s[1] * cy[1] + s[2] * cy[2] + s[3] * cy[3] +
                 s[4] * cy[4] + s[5] * cy[5] + s[6] * cy[6] + s[7] * cy[7])
            d = int(d + 128.5)
            n[y * 8 + x] = 0 if d < 0 else (255 if d > 255 else d)
    return n


class _Huffman:
    __slots__ = ("maks", "min", "göst", "dəyərlər")

    def __init__(self, sayılar: bytes, dəyərlər: bytes):
        self.maks = [-1] * 18
        self.min = [0] * 17
        self.göst = [0] * 17
        self.dəyərlər = dəyərlər
        kod = 0
        k = 0
        for l in range(1, 17):
            n = sayılar[l - 1]
            self.göst[l] = k
            self.min[l] = kod
            kod += n
            k += n
            self.maks[l] = kod - 1 if n else -1
            kod <<= 1
        self.maks[17] = 0x7FFFFFFF


class _Bitlər:
    __slots__ = ("d", "i", "acc", "n", "marker")

    def __init__(self, d: bytes, i: int):
        self.d, self.i, self.acc, self.n, self.marker = d, i, 0, 0, None

    def bit(self) -> int:
        if self.n == 0:
            if self.marker is not None:
                self.acc, self.n = 0, 8
            else:
                b = self.d[self.i] if self.i < len(self.d) else 0
                self.i += 1
                if b == 0xFF:
                    c = self.d[self.i] if self.i < len(self.d) else 0
                    if c == 0:
                        self.i += 1
                    else:
                        self.marker = self.i - 1
                        b = 0
                self.acc, self.n = b, 8
        self.n -= 1
        return (self.acc >> self.n) & 1

    def bitlər(self, k: int) -> int:
        v = 0
        for _ in range(k):
            v = (v << 1) | self.bit()
        return v

    def al(self, k: int) -> int:
        """`receive` + `extend` (JPEG F.2.2.1)."""
        if k == 0:
            return 0
        v = self.bitlər(k)
        return v if v >= 1 << (k - 1) else v - (1 << k) + 1

    def huff(self, t: _Huffman) -> int:
        kod = self.bit()
        l = 1
        while kod > t.maks[l]:
            kod = (kod << 1) | self.bit()
            l += 1
            if l > 16:
                raise KodekXətası("JPEG: Huffman kodu pozulub")
        return t.dəyərlər[t.göst[l] + kod - t.min[l]]

    def yenidən(self) -> None:
        """RST markerindən sonra: bitləri at, markeri keç."""
        self.n = 0
        if self.marker is not None:
            self.i = self.marker + 2
            self.marker = None
        else:
            while self.i + 1 < len(self.d):
                if self.d[self.i] == 0xFF and 0xD0 <= self.d[self.i + 1] <= \
                        0xD7:
                    self.i += 2
                    break
                self.i += 1


def _exif_istiqaməti(c: bytes) -> int:
    if not c.startswith(b"Exif\0\0"):
        return 1
    t = c[6:]
    if len(t) < 8:
        return 1
    e = "<" if t[:2] == b"II" else ">"
    try:
        ofs = struct.unpack(e + "I", t[4:8])[0]
        n = struct.unpack(e + "H", t[ofs:ofs + 2])[0]
        for k in range(n):
            o = ofs + 2 + k * 12
            tag, tip, say = struct.unpack(e + "HHI", t[o:o + 8])
            if tag == 0x0112:
                return struct.unpack(e + "H", t[o + 8:o + 10])[0]
    except struct.error:
        pass
    return 1


def jpeg_aç(b: bytes) -> tuple[int, int, bytearray, dict]:
    i = 2
    qt: dict[int, list[int]] = {}
    ht: dict[tuple[int, int], _Huffman] = {}
    komp: list[dict] = []
    en = h = 0
    ri = 0
    progressive = False
    adobe = None
    istiqamət = 1
    hmaks = vmaks = 1
    mcux = mcuy = 0
    while i < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m == 0xD8 or 0xD0 <= m <= 0xD7 or m == 0x01:
            i += 2
            continue
        if m == 0xD9:
            break
        uz = struct.unpack(">H", b[i + 2:i + 4])[0]
        c = b[i + 4:i + 2 + uz]
        if m == 0xDB:                                   # DQT
            j = 0
            while j < len(c):
                dəq, nö = c[j] >> 4, c[j] & 15
                if dəq:
                    t = list(struct.unpack(">64H", c[j + 1:j + 129]))
                    j += 129
                else:
                    t = list(c[j + 1:j + 65])
                    j += 65
                qt[nö] = t
        elif m == 0xC4:                                 # DHT
            j = 0
            while j < len(c):
                sinif, nö = c[j] >> 4, c[j] & 15
                sayılar = c[j + 1:j + 17]
                n = sum(sayılar)
                ht[(sinif, nö)] = _Huffman(sayılar, c[j + 17:j + 17 + n])
                j += 17 + n
        elif m in (0xC0, 0xC1, 0xC2):                   # SOF
            progressive = m == 0xC2
            _, h, en, n = struct.unpack(">BHHB", c[:6])
            if en == 0 or h == 0:
                raise KodekXətası("JPEG: ölçü yanlışdır (DNL dəstəklənmir)")
            for k in range(n):
                cid, hv, tq = c[6 + k * 3:9 + k * 3]
                komp.append({"id": cid, "h": hv >> 4, "v": hv & 15,
                             "tq": tq, "pred": 0})
            hmaks = max(x["h"] for x in komp)
            vmaks = max(x["v"] for x in komp)
            mcux = (en + 8 * hmaks - 1) // (8 * hmaks)
            mcuy = (h + 8 * vmaks - 1) // (8 * vmaks)
            for x in komp:
                x["bx"] = mcux * x["h"]
                x["by"] = mcuy * x["v"]
                x["en"] = (en * x["h"] + hmaks - 1) // hmaks
                x["hün"] = (h * x["v"] + vmaks - 1) // vmaks
                x["əmsal"] = [[0] * 64 for _ in range(x["bx"] * x["by"])]
        elif m in (0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE,
                   0xCF):
            raise KodekXətası("JPEG: lossless/arifmetik kodlama "
                              "dəstəklənmir")
        elif m == 0xDD:
            ri = struct.unpack(">H", c[:2])[0]
        elif m == 0xEE and c.startswith(b"Adobe") and len(c) >= 12:
            adobe = c[11]
        elif m == 0xE1:
            istiqamət = _exif_istiqaməti(c)
        elif m == 0xDA:                                 # SOS
            if not komp:
                raise KodekXətası("JPEG: SOS SOF-dan əvvəl gəlib")
            n = c[0]
            sk = []
            for k in range(n):
                cid, td = c[1 + k * 2], c[2 + k * 2]
                x = next(y for y in komp if y["id"] == cid)
                x["td"], x["ta"] = td >> 4, td & 15
                sk.append(x)
            ss, se, ahal = c[1 + n * 2], c[2 + n * 2], c[3 + n * 2]
            bit = _Bitlər(b, i + 2 + uz)
            _skan(bit, sk, ht, ss, se, ahal >> 4, ahal & 15, progressive,
                  ri, mcux, mcuy)
            # növbəti markerə keç
            j = bit.marker if bit.marker is not None else bit.i
            while j + 1 < len(b) and not (b[j] == 0xFF and b[j + 1] not in
                                          (0, *range(0xD0, 0xD8))):
                j += 1
            i = j
            continue
        i += 2 + uz
    if not komp:
        raise KodekXətası("JPEG: kadr tapılmadı")

    # Dekvantlama + IDCT
    müstəvilər = []
    for x in komp:
        q = qt.get(x["tq"])
        if q is None:
            raise KodekXətası("JPEG: kvantlama cədvəli yoxdur")
        bx, by = x["bx"], x["by"]
        pen = bx * 8
        müs = bytearray(pen * by * 8)
        for blok_i, ə in enumerate(x["əmsal"]):
            təbii = [0.0] * 64
            for k in range(64):
                if ə[k]:
                    təbii[ZİQZAQ[k]] = ə[k] * q[k]
            piks = _idct(təbii)
            oy, ox = (blok_i // bx) * 8, (blok_i % bx) * 8
            for yy in range(8):
                o = (oy + yy) * pen + ox
                müs[o:o + 8] = bytes(piks[yy * 8:yy * 8 + 8])
        müstəvilər.append((müs, pen, x["h"], x["v"]))
        x["əmsal"] = None

    # Tam ölçülü müstəvilər: alt-seçilmiş xroma bilinear genişlənir
    # (libjpeg-in "fancy upsampling"-i kimi — kənarlar pilləli olmur)
    tam: list = []
    for müs, pen, hh, vv in müstəvilər:
        if hh == hmaks and vv == vmaks:
            tam.append((müs, pen))
            continue
        fx, fy = hmaks / hh, vmaks / vv
        cen = (en * hh + hmaks - 1) // hmaks
        chün = (h * vv + vmaks - 1) // vmaks

        def oxlar(n, f, son):
            n_ = []
            for k in range(n):
                q = (k + 0.5) / f - 0.5
                a = math.floor(q)
                t = q - a
                n_.append((min(max(a, 0), son), min(max(a + 1, 0), son), t))
            return n_
        xs = oxlar(en, fx, cen - 1)
        ys = oxlar(h, fy, chün - 1)
        yeni = bytearray(en * h)
        for y, (y0, y1, ty) in enumerate(ys):
            s0, s1 = y0 * pen, y1 * pen
            o = y * en
            for x, (x0, x1, tx) in enumerate(xs):
                a = müs[s0 + x0] + (müs[s0 + x1] - müs[s0 + x0]) * tx
                b_ = müs[s1 + x0] + (müs[s1 + x1] - müs[s1 + x0]) * tx
                yeni[o + x] = int(a + (b_ - a) * ty + 0.5)
        tam.append((yeni, en))

    rgba = bytearray(en * h * 4)
    nk = len(komp)
    çevir = (adobe != 0) if nk == 3 else (adobe == 2)
    for y in range(h):
        sətirlər = [(müs, y * pen) for müs, pen in tam]
        o = y * en * 4
        for xx in range(en):
            v = [müs[s + xx] for müs, s in sətirlər]
            if nk == 1:
                r = g = bl = v[0]
            elif nk >= 3:
                if çevir:
                    yy_, cb, cr = v[0], v[1] - 128, v[2] - 128
                    r = yy_ + 1.402 * cr
                    g = yy_ - 0.344136 * cb - 0.714136 * cr
                    bl = yy_ + 1.772 * cb
                    r = 0 if r < 0 else (255 if r > 255 else int(r + 0.5))
                    g = 0 if g < 0 else (255 if g > 255 else int(g + 0.5))
                    bl = 0 if bl < 0 else (255 if bl > 255 else int(bl + 0.5))
                else:
                    r, g, bl = v[0], v[1], v[2]
                if nk == 4:                              # CMYK (Adobe tərs)
                    k = v[3]
                    r, g, bl = r * k // 255, g * k // 255, bl * k // 255
            else:
                r = g = bl = v[0]
            rgba[o:o + 4] = bytes((r, g, bl, 255))
            o += 4
    məlumat = {"istiqamət": istiqamət, "progressive": progressive}
    return en, h, rgba, məlumat


def _skan(bit: _Bitlər, sk: list[dict], ht: dict, ss: int, se: int,
          ah: int, al: int, progressive: bool, ri: int, mcux: int,
          mcuy: int) -> None:
    for x in sk:
        x["pred"] = 0
    eobrun = [0]

    def dc_ilk(x, ə):
        t = bit.huff(ht[(0, x["td"])])
        x["pred"] += bit.al(t)
        ə[0] = x["pred"] << al

    def dc_dəqiq(x, ə):
        if bit.bit():
            ə[0] |= 1 << al

    def ac_ilk(x, ə):
        if eobrun[0]:
            eobrun[0] -= 1
            return
        k = ss
        t = ht[(1, x["ta"])]
        while k <= se:
            rs = bit.huff(t)
            r, s = rs >> 4, rs & 15
            if s == 0:
                if r < 15:
                    eobrun[0] = (1 << r) - 1
                    if r:
                        eobrun[0] += bit.bitlər(r)
                    break
                k += 16
                continue
            k += r
            if k > 63:
                break
            ə[k] = bit.al(s) * (1 << al)
            k += 1

    def ac_dəqiq(x, ə):
        p1, m1 = 1 << al, -1 << al
        k = ss
        if eobrun[0] <= 0:
            t = ht[(1, x["ta"])]
            while k <= se:
                rs = bit.huff(t)
                r, s = rs >> 4, rs & 15
                dəyər = 0
                if s == 0:
                    if r < 15:
                        eobrun[0] = 1 << r
                        if r:
                            eobrun[0] += bit.bitlər(r)
                        break
                else:
                    dəyər = p1 if bit.bit() else m1
                while k <= se:
                    if ə[k]:
                        if bit.bit() and (ə[k] & p1) == 0:
                            ə[k] += p1 if ə[k] >= 0 else m1
                    else:
                        if r == 0:
                            if dəyər:
                                ə[k] = dəyər
                            k += 1
                            break
                        r -= 1
                    k += 1
                else:
                    continue
        if eobrun[0] > 0:
            while k <= se:
                if ə[k] and bit.bit() and (ə[k] & p1) == 0:
                    ə[k] += p1 if ə[k] >= 0 else m1
                k += 1
            eobrun[0] -= 1

    def baseline(x, ə):
        t = bit.huff(ht[(0, x["td"])])
        x["pred"] += bit.al(t)
        ə[0] = x["pred"]
        ta = ht[(1, x["ta"])]
        k = 1
        while k < 64:
            rs = bit.huff(ta)
            r, s = rs >> 4, rs & 15
            if s == 0:
                if r == 15:
                    k += 16
                    continue
                break
            k += r
            if k > 63:
                break
            ə[k] = bit.al(s)
            k += 1

    if not progressive:
        dekod = baseline
    elif ss == 0:
        dekod = dc_ilk if ah == 0 else dc_dəqiq
    else:
        dekod = ac_ilk if ah == 0 else ac_dəqiq

    def bərpa(say):
        if ri and say and say % ri == 0:
            bit.yenidən()
            for x in sk:
                x["pred"] = 0
            eobrun[0] = 0

    if len(sk) == 1:
        x = sk[0]
        bx_say = (x["en"] + 7) // 8
        by_say = (x["hün"] + 7) // 8
        say = 0
        for by in range(by_say):
            for bx in range(bx_say):
                bərpa(say)
                dekod(x, x["əmsal"][by * x["bx"] + bx])
                say += 1
    else:
        say = 0
        for my in range(mcuy):
            for mx in range(mcux):
                bərpa(say)
                for x in sk:
                    for v in range(x["v"]):
                        for hh in range(x["h"]):
                            bi = (my * x["v"] + v) * x["bx"] + \
                                mx * x["h"] + hh
                            dekod(x, x["əmsal"][bi])
                say += 1


# ── JPEG yazma (baseline, 4:2:0) ──────────────────────────────────────

_STD_Y = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
          14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
          18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
          49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103,
          99]
_STD_C = [17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99,
          24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99, 99, 99, 99, 99] + \
    [99] * 32
_DC_Y = (bytes([0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]),
         bytes(range(12)))
_DC_C = (bytes([0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]),
         bytes(range(12)))
_AC_Y = (bytes([0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d]), bytes.fromhex(
    "01020300041105122131410613516107227114328191a1082342b1c11552d1f02433"
    "627282090a161718191a25262728292a3435363738393a434445464748494a535455"
    "565758595a636465666768696a737475767778797a838485868788898a9293949596"
    "9798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4"
    "d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9fa"))
_AC_C = (bytes([0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77]),
         bytes.fromhex(
    "000102031104052131061241510761711322328108144291a1b1c109233352f015"
    "6272d10a162434e125f11718191a262728292a35363738393a434445464748494a53"
    "5455565758595a636465666768696a737475767778797a82838485868788898a9293"
    "9495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9ca"
    "d2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9fa"))


def _kod_cədvəli(sayılar: bytes, dəyərlər: bytes) -> dict[int, tuple[int,
                                                                    int]]:
    n, kod, k = {}, 0, 0
    for l in range(1, 17):
        for _ in range(sayılar[l - 1]):
            n[dəyərlər[k]] = (kod, l)
            kod += 1
            k += 1
        kod <<= 1
    return n


class _BitYazan:
    def __init__(self):
        self.b = bytearray()
        self.acc = 0
        self.n = 0

    def yaz(self, kod: int, uz: int) -> None:
        self.acc = (self.acc << uz) | (kod & ((1 << uz) - 1))
        self.n += uz
        while self.n >= 8:
            self.n -= 8
            bayt = (self.acc >> self.n) & 255
            self.b.append(bayt)
            if bayt == 0xFF:
                self.b.append(0)
        self.acc &= (1 << self.n) - 1

    def bitir(self) -> bytes:
        if self.n:
            self.yaz((1 << (8 - self.n)) - 1, 8 - self.n)
        return bytes(self.b)


def _fdct(blok: list[float]) -> list[float]:
    ara = [0.0] * 64
    C = _COS
    for y in range(8):
        s = blok[y * 8:y * 8 + 8]
        for u in range(8):
            ara[y * 8 + u] = sum(s[x] * C[x][u] for x in range(8))
    n = [0.0] * 64
    for u in range(8):
        s = [ara[y * 8 + u] for y in range(8)]
        for v in range(8):
            n[v * 8 + u] = sum(s[y] * C[y][v] for y in range(8))
    return n


def jpeg_yaz(en: int, h: int, rgba: bytearray, keyfiyyət: int = 90) -> bytes:
    q = max(1, min(100, int(keyfiyyət)))
    ş = 5000 / q if q < 50 else 200 - 2 * q

    def cədvəl(t):
        return [max(1, min(255, (x * ş + 50) // 100)) for x in t]
    qy = cədvəl(_STD_Y)
    qc = cədvəl(_STD_C)
    # təbii sıra → ziqzaq sırası üçün kvant cədvəlləri
    qy_z = [qy[ZİQZAQ[k]] for k in range(64)]
    qc_z = [qc[ZİQZAQ[k]] for k in range(64)]

    # Y, Cb, Cr müstəviləri (ağ fon üzərində alfa)
    n = en * h
    Y = [0.0] * n
    Cb = [0.0] * n
    Cr = [0.0] * n
    for p in range(n):
        o = p * 4
        a = rgba[o + 3]
        if a == 255:
            r, g, b = rgba[o], rgba[o + 1], rgba[o + 2]
        else:
            r = (rgba[o] * a + 255 * (255 - a)) / 255
            g = (rgba[o + 1] * a + 255 * (255 - a)) / 255
            b = (rgba[o + 2] * a + 255 * (255 - a)) / 255
        Y[p] = 0.299 * r + 0.587 * g + 0.114 * b - 128
        Cb[p] = -0.168736 * r - 0.331264 * g + 0.5 * b
        Cr[p] = 0.5 * r - 0.418688 * g - 0.081312 * b

    dc_y, ac_y = _kod_cədvəli(*_DC_Y), _kod_cədvəli(*_AC_Y)
    dc_c, ac_c = _kod_cədvəli(*_DC_C), _kod_cədvəli(*_AC_C)
    w = _BitYazan()
    pred = [0, 0, 0]

    def kateqoriya(v: int) -> int:
        return abs(v).bit_length()

    def kodla(blok: list[float], qz: list[int], dc, ac, kanal: int) -> None:
        d = _fdct(blok)
        z = [int(round(d[ZİQZAQ[k]] / qz[k])) for k in range(64)]
        fərq = z[0] - pred[kanal]
        pred[kanal] = z[0]
        s = kateqoriya(fərq)
        w.yaz(*dc[s])
        if s:
            w.yaz(fərq if fərq > 0 else fərq - 1 + (1 << s), s)
        sıfır = 0
        son = 63
        while son > 0 and z[son] == 0:
            son -= 1
        for k in range(1, son + 1):
            v = z[k]
            if v == 0:
                sıfır += 1
                continue
            while sıfır > 15:
                w.yaz(*ac[0xF0])
                sıfır -= 16
            s = kateqoriya(v)
            w.yaz(*ac[(sıfır << 4) | s])
            w.yaz(v if v > 0 else v - 1 + (1 << s), s)
            sıfır = 0
        if son < 63:
            w.yaz(*ac[0x00])

    def blok_al(m: list[float], x0: int, y0: int, addım: int) -> list[float]:
        n = []
        for yy in range(8):
            y = min(h - 1, y0 + yy * addım)
            for xx in range(8):
                x = min(en - 1, x0 + xx * addım)
                if addım == 1:
                    n.append(m[y * en + x])
                else:
                    x2, y2 = min(en - 1, x + 1), min(h - 1, y + 1)
                    n.append((m[y * en + x] + m[y * en + x2] +
                              m[y2 * en + x] + m[y2 * en + x2]) / 4)
        return n

    for my in range(0, h, 16):
        for mx in range(0, en, 16):
            for by in (0, 8):
                for bx in (0, 8):
                    kodla(blok_al(Y, mx + bx, my + by, 1), qy_z, dc_y, ac_y,
                          0)
            kodla(blok_al(Cb, mx, my, 2), qc_z, dc_c, ac_c, 1)
            kodla(blok_al(Cr, mx, my, 2), qc_z, dc_c, ac_c, 2)
    data = w.bitir()

    def seq(m: int, c: bytes) -> bytes:
        return bytes([0xFF, m]) + struct.pack(">H", len(c) + 2) + c

    dqt = bytes([0]) + bytes(qy_z) + bytes([1]) + bytes(qc_z)
    sof = struct.pack(">BHHB", 8, h, en, 3) + bytes(
        [1, 0x22, 0, 2, 0x11, 1, 3, 0x11, 1])
    dht = (bytes([0x00]) + _DC_Y[0] + _DC_Y[1] +
           bytes([0x10]) + _AC_Y[0] + _AC_Y[1] +
           bytes([0x01]) + _DC_C[0] + _DC_C[1] +
           bytes([0x11]) + _AC_C[0] + _AC_C[1])
    sos = bytes([3, 1, 0x00, 2, 0x11, 3, 0x11, 0, 63, 0])
    jfif = b"JFIF\0" + bytes([1, 1, 0, 0, 1, 0, 1, 0, 0])
    return (b"\xff\xd8" + seq(0xE0, jfif) + seq(0xDB, dqt) + seq(0xC0, sof)
            + seq(0xC4, dht) + seq(0xDA, sos) + data + b"\xff\xd9")


# ═══════════════════════════════════════════════════════════════════════
#  GIF
# ═══════════════════════════════════════════════════════════════════════

def _lzw_aç(data: bytes, min_kod: int, piksel_sayı: int) -> bytearray:
    təmizlə = 1 << min_kod
    son = təmizlə + 1
    ölçü = min_kod + 1
    lüğət: list[bytes] = [bytes([i]) for i in range(təmizlə)] + [b"", b""]
    n = bytearray()
    əvvəlki: bytes | None = None
    acc = bits = 0
    for b in data:
        acc |= b << bits
        bits += 8
        while bits >= ölçü:
            kod = acc & ((1 << ölçü) - 1)
            acc >>= ölçü
            bits -= ölçü
            if kod == təmizlə:
                ölçü = min_kod + 1
                del lüğət[təmizlə + 2:]
                əvvəlki = None
                continue
            if kod == son:
                return n
            if kod < len(lüğət):
                giriş = lüğət[kod]
                if əvvəlki is not None:
                    lüğət.append(əvvəlki + giriş[:1])
            elif əvvəlki is not None and kod == len(lüğət):
                giriş = əvvəlki + əvvəlki[:1]
                lüğət.append(giriş)
            else:
                raise KodekXətası("GIF: LZW kodu pozulub")
            n += giriş
            əvvəlki = giriş
            if len(lüğət) == (1 << ölçü) and ölçü < 12:
                ölçü += 1
            if len(n) >= piksel_sayı:
                return n
    return n


def gif_aç(b: bytes) -> tuple[int, int, bytearray, dict]:
    en, h, bayraq, fon, _ = struct.unpack("<HHBBB", b[6:13])
    i = 13
    qlobal = []
    if bayraq & 0x80:
        n = 2 << (bayraq & 7)
        qlobal = [tuple(b[i + k * 3:i + k * 3 + 3]) for k in range(n)]
        i += n * 3
    rgba = bytearray(en * h * 4)
    şəffaf = None
    kadr_sayı = 0
    nəticə = None
    while i < len(b):
        x = b[i]
        if x == 0x3B:
            break
        if x == 0x21:
            etiket = b[i + 1]
            i += 2
            if etiket == 0xF9 and b[i] >= 4:
                if b[i + 1] & 1:
                    şəffaf = b[i + 4]
            while b[i]:
                i += 1 + b[i]
            i += 1
            continue
        if x != 0x2C:
            raise KodekXətası("GIF: blok pozulub")
        sol, üst, ke, kh, kb = struct.unpack("<HHHHB", b[i + 1:i + 10])
        i += 10
        palitra = qlobal
        if kb & 0x80:
            n = 2 << (kb & 7)
            palitra = [tuple(b[i + k * 3:i + k * 3 + 3]) for k in range(n)]
            i += n * 3
        min_kod = b[i]
        i += 1
        parça = bytearray()
        while b[i]:
            parça += b[i + 1:i + 1 + b[i]]
            i += 1 + b[i]
        i += 1
        kadr_sayı += 1
        if nəticə is not None:
            continue                       # yalnız ilk kadr
        ind = _lzw_aç(bytes(parça), min_kod, ke * kh)
        sətirlər = list(range(kh))
        if kb & 0x40:                      # interlace
            sətirlər = (list(range(0, kh, 8)) + list(range(4, kh, 8)) +
                        list(range(2, kh, 4)) + list(range(1, kh, 2)))
        for sı, y in enumerate(sətirlər):
            yy = üst + y
            if yy >= h:
                continue
            for xx in range(ke):
                k = sı * ke + xx
                if k >= len(ind) or sol + xx >= en:
                    continue
                v = ind[k]
                if v == şəffaf or v >= len(palitra):
                    continue
                o = (yy * en + sol + xx) * 4
                rgba[o:o + 4] = bytes(palitra[v]) + b"\xff"
        nəticə = rgba
    if nəticə is None:
        raise KodekXətası("GIF: kadr yoxdur")
    return en, h, nəticə, {"kadrlar": kadr_sayı}


def _median_kəsmə(rənglər: dict[int, int], n: int) -> list[tuple]:
    """15-bitlik rəng histoqramı → ən çox `n` rəngli palitra."""
    qutular = [list(rənglər.items())]
    while len(qutular) < n:
        qutular.sort(key=lambda q: -sum(c for _, c in q) if len(q) > 1
                     else 0)
        q = qutular[0]
        if len(q) < 2:
            break
        aralıq = []
        for k in (10, 5, 0):
            dəy = [(r >> k) & 31 for r, _ in q]
            aralıq.append(max(dəy) - min(dəy))
        k = (10, 5, 0)[aralıq.index(max(aralıq))]
        q.sort(key=lambda e: (e[0] >> k) & 31)
        cəm = sum(c for _, c in q)
        yarı, s = 0, 0
        for j, (_, c) in enumerate(q):
            s += c
            if s >= cəm / 2:
                yarı = max(1, min(len(q) - 1, j + 1))
                break
        qutular[0:1] = [q[:yarı], q[yarı:]]
    palitra = []
    for q in qutular:
        cəm = sum(c for _, c in q) or 1
        palitra.append(tuple(
            int(sum(((r >> k) & 31) * 255 / 31 * c for r, c in q) / cəm)
            for k in (10, 5, 0)))
    return palitra


def _lzw_kodla(ind: bytes, min_kod: int) -> bytes:
    təmizlə = 1 << min_kod
    son = təmizlə + 1
    ölçü = min_kod + 1
    lüğət = {bytes([i]): i for i in range(təmizlə)}
    növbəti = təmizlə + 2
    çıxış = bytearray()
    acc = bits = 0

    def yaz(kod):
        nonlocal acc, bits
        acc |= kod << bits
        bits += ölçü
        while bits >= 8:
            çıxış.append(acc & 255)
            acc >>= 8
            bits -= 8

    yaz(təmizlə)
    w = b""
    for k in ind:
        wk = w + bytes([k])
        if wk in lüğət:
            w = wk
            continue
        yaz(lüğət[w])
        if növbəti < 4096:
            lüğət[wk] = növbəti
            növbəti += 1
            if növbəti > (1 << ölçü) and ölçü < 12:
                ölçü += 1
        else:
            yaz(təmizlə)
            lüğət = {bytes([i]): i for i in range(təmizlə)}
            növbəti = təmizlə + 2
            ölçü = min_kod + 1
        w = bytes([k])
    if w:
        yaz(lüğət[w])
    yaz(son)
    if bits:
        çıxış.append(acc & 255)
    return bytes(çıxış)


def gif_yaz(en: int, h: int, rgba: bytearray) -> bytes:
    n = en * h
    unikal: dict[tuple, int] = {}
    şəffaf_var = False
    for p in range(n):
        o = p * 4
        if rgba[o + 3] < 128:
            şəffaf_var = True
            continue
        k = (rgba[o], rgba[o + 1], rgba[o + 2])
        if k not in unikal:
            unikal[k] = len(unikal)
            if len(unikal) > 256:
                break
    maks = 255 if şəffaf_var else 256
    if len(unikal) <= maks:
        palitra = list(unikal)
        xəritə = dict(unikal)
        ən_yaxın = xəritə.__getitem__
    else:
        hist: dict[int, int] = {}
        for p in range(n):
            o = p * 4
            if rgba[o + 3] >= 128:
                k = ((rgba[o] >> 3) << 10) | ((rgba[o + 1] >> 3) << 5) | \
                    (rgba[o + 2] >> 3)
                hist[k] = hist.get(k, 0) + 1
        palitra = _median_kəsmə(hist, maks)
        keş: dict[int, int] = {}

        def ən_yaxın(r):
            k = ((r[0] >> 3) << 10) | ((r[1] >> 3) << 5) | (r[2] >> 3)
            v = keş.get(k)
            if v is None:
                v = min(range(len(palitra)), key=lambda j: (
                    (palitra[j][0] - r[0]) ** 2 + (palitra[j][1] - r[1]) ** 2
                    + (palitra[j][2] - r[2]) ** 2))
                keş[k] = v
            return v
    şəffaf_ind = len(palitra) if şəffaf_var else None
    if şəffaf_var:
        palitra = palitra + [(0, 0, 0)]
    bit = max(1, (len(palitra) - 1).bit_length())
    palitra += [(0, 0, 0)] * ((1 << bit) - len(palitra))
    ind = bytearray(n)
    for p in range(n):
        o = p * 4
        if rgba[o + 3] < 128:
            ind[p] = şəffaf_ind
        else:
            ind[p] = ən_yaxın((rgba[o], rgba[o + 1], rgba[o + 2]))
    min_kod = max(2, bit)
    data = _lzw_kodla(bytes(ind), min_kod)
    parçalar = b"".join(bytes([len(data[k:k + 255])]) + data[k:k + 255]
                        for k in range(0, len(data), 255)) + b"\0"
    gce = b""
    if şəffaf_var:
        gce = b"\x21\xf9\x04\x01\x00\x00" + bytes([şəffaf_ind]) + b"\x00"
    return (b"GIF89a" + struct.pack("<HHBBB", en, h, 0x80 | (bit - 1), 0, 0)
            + b"".join(bytes(c) for c in palitra) + gce +
            b"\x2c" + struct.pack("<HHHHB", 0, 0, en, h, 0) +
            bytes([min_kod]) + parçalar + b"\x3b")


# ═══════════════════════════════════════════════════════════════════════
#  BMP və PPM
# ═══════════════════════════════════════════════════════════════════════

def bmp_aç(b: bytes) -> tuple[int, int, bytearray, dict]:
    ofs = struct.unpack("<I", b[10:14])[0]
    bas = struct.unpack("<I", b[14:18])[0]
    if bas == 12:
        en, h, _, bpp = struct.unpack("<HHHH", b[18:26])
        sıxma = 0
    else:
        en, h, _, bpp, sıxma = struct.unpack("<iiHHI", b[18:34])
    yuxarıdan = h < 0
    h = abs(h)
    if sıxma not in (0, 3) or bpp not in (1, 4, 8, 24, 32):
        raise KodekXətası("BMP: sıxılmış və ya bu bit dərinliyi "
                          "dəstəklənmir")
    palitra = []
    if bpp <= 8:
        pst = 14 + bas
        say = struct.unpack("<I", b[46:50])[0] if bas >= 40 else 0
        say = say or (1 << bpp)
        el = 3 if bas == 12 else 4
        palitra = [(b[pst + k * el + 2], b[pst + k * el + 1],
                    b[pst + k * el]) for k in range(say)]
    maskalar = None
    if sıxma == 3 and bpp == 32:
        maskalar = struct.unpack("<IIII", b[54:70]) if bas >= 56 else \
            struct.unpack("<III", b[54:66]) + (0,)
    sətir = ((en * bpp + 31) // 32) * 4
    rgba = bytearray(en * h * 4)
    for y in range(h):
        hy = y if yuxarıdan else h - 1 - y
        s = b[ofs + hy * sətir:ofs + (hy + 1) * sətir]
        o = y * en * 4
        for x in range(en):
            if bpp == 24:
                bb, g, r = s[x * 3:x * 3 + 3]
                a = 255
            elif bpp == 32:
                v = struct.unpack("<I", s[x * 4:x * 4 + 4])[0]
                if maskalar:
                    def k(m):
                        if not m:
                            return 255
                        sh = (m & -m).bit_length() - 1
                        return ((v & m) >> sh) * 255 // (m >> sh)
                    r, g, bb, a = (k(maskalar[0]), k(maskalar[1]),
                                   k(maskalar[2]),
                                   k(maskalar[3]) if maskalar[3] else 255)
                else:
                    bb, g, r, a = s[x * 4:x * 4 + 4]
                    a = 255 if bas < 56 and a == 0 else a
            else:
                bit = x * bpp
                v = (s[bit >> 3] >> (8 - bpp - (bit & 7))) & ((1 << bpp) - 1)
                r, g, bb = palitra[v] if v < len(palitra) else (0, 0, 0)
                a = 255
            rgba[o:o + 4] = bytes((r, g, bb, a))
            o += 4
    return en, h, rgba, {}


def bmp_yaz(en: int, h: int, rgba: bytearray) -> bytes:
    sətir = en * 4
    data = bytearray()
    for y in range(h - 1, -1, -1):
        s = rgba[y * sətir:(y + 1) * sətir]
        t = bytearray(sətir)
        t[0::4], t[1::4], t[2::4], t[3::4] = s[2::4], s[1::4], s[0::4], \
            s[3::4]
        data += t
    bas = struct.pack("<IiiHHIIiiII", 108, en, h, 1, 32, 3, len(data),
                      2835, 2835, 0, 0) + struct.pack(
        "<IIII", 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000) + \
        b"BGRs" + bytes(48)
    return (b"BM" + struct.pack("<IHHI", 14 + len(bas) + len(data), 0, 0,
                                14 + len(bas)) + bas + bytes(data))


def ppm_aç(b: bytes) -> tuple[int, int, bytearray, dict]:
    növ = b[:2]
    sözlər: list[bytes] = []
    i = 2
    lazım = 3
    while len(sözlər) < lazım:
        while i < len(b) and b[i:i + 1].isspace():
            i += 1
        if b[i:i + 1] == b"#":
            while i < len(b) and b[i] not in (10, 13):
                i += 1
            continue
        j = i
        while j < len(b) and not b[j:j + 1].isspace():
            j += 1
        sözlər.append(b[i:j])
        i = j
    en, h, maks = (int(x) for x in sözlər)
    i += 1
    kanal = 3 if növ in (b"P3", b"P6") else 1
    if növ in (b"P5", b"P6"):
        addım = 2 if maks > 255 else 1
        xam = b[i:i + en * h * kanal * addım]
        if addım == 2:
            dəy = [(xam[k] << 8 | xam[k + 1]) * 255 // maks
                   for k in range(0, len(xam), 2)]
        else:
            dəy = list(xam) if maks == 255 else [v * 255 // maks
                                                 for v in xam]
    else:
        dəy = [int(x) * 255 // maks for x in b[i:].split()[:en * h * kanal]]
    rgba = bytearray(en * h * 4)
    for p in range(en * h):
        if kanal == 3:
            r, g, bb = dəy[p * 3:p * 3 + 3]
        else:
            r = g = bb = dəy[p]
        rgba[p * 4:p * 4 + 4] = bytes((r, g, bb, 255))
    return en, h, rgba, {}


def ppm_yaz(en: int, h: int, rgba: bytearray) -> bytes:
    rgb = bytearray(en * h * 3)
    rgb[0::3], rgb[1::3], rgb[2::3] = rgba[0::4], rgba[1::4], rgba[2::4]
    return f"P6\n{en} {h}\n255\n".encode() + bytes(rgb)
