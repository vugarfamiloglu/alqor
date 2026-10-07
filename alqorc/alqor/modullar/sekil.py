"""
`şəkil` — şəkil emalı: oxuma/yazma, ölçü, kəsmə, döndərmə, filtrlər,
çəkmə (§ 10.17). Xarici kitabxanasızdır (təmiz Python) — böyük fotolarda
(10+ meqapiksel) əməliyyatlar saniyələr çəkə bilər.

    gətir şəkil

    dəyişən ş = şəkil.aç("foto.jpg")              // PNG JPEG GIF BMP PPM
    yaz(ş.en(), ş.hündürlük())

    ş.miniatür(300, 300).saxla("kiçik.jpg", keyfiyyət: 85)
    ş.kəs(10, 10, 200, 100).boz().saxla("parça.png")
    ş.ölçüDəyiş(800).döndər(90).çevir("üfüqi").saxla("yeni.png")
    ş.parlaqlıq(1.2).kontrast(1.1).itilə().saxla("parlaq.jpg")

    dəyişən kətan = şəkil.yarat(400, 200, "#ffffff")
        .düzbucaqlı(20, 20, 160, 80, "mavi")
        .dairə(300, 100, 60, "#e11d48", doldur: yanlış, qalınlıq: 4)
        .xətt(0, 199, 399, 0, "qara", qalınlıq: 2)
        .yapışdır(şəkil.aç("loqo.png"), 10, 120, şəffaflıq: 0.8)
    kətan.saxla("kətan.png")
    yaz(kətan.dataURI())                          // <img src="…"> üçün

Bütün əməliyyatlar YENİ şəkil qaytarır (orijinal dəyişmir), ona görə
zəncirləmək olar. Rənglər: "#rgb", "#rrggbb", "#rrggbbaa", "rgb(1,2,3)",
[r, g, b] / [r, g, b, a] və adlar (qırmızı, yaşıl, mavi, ağ, qara, sarı,
narıncı, bənövşəyi, çəhrayı, boz, şəffaf …).

JPEG faylının EXIF istiqaməti `aç` zamanı avtomatik tətbiq olunur.
"""

from __future__ import annotations

import base64
import math
import re
import struct
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı
from . import _sekil_kodek as K

RƏNGLƏR = {
    "qara": (0, 0, 0), "ağ": (255, 255, 255), "qırmızı": (220, 38, 38),
    "yaşıl": (22, 163, 74), "mavi": (37, 99, 235), "sarı": (250, 204, 21),
    "narıncı": (249, 115, 22), "bənövşəyi": (147, 51, 234),
    "çəhrayı": (236, 72, 153), "boz": (128, 128, 128),
    "açıqBoz": (229, 231, 235), "tündBoz": (55, 65, 81),
    "göy": (14, 165, 233), "qəhvəyi": (146, 64, 14),
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "orange": (255, 165, 0), "purple": (128, 0, 128), "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}
FORMATLAR = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif",
             ".bmp": "bmp", ".ppm": "ppm", ".pgm": "ppm"}
_MIME = {"png": "image/png", "jpeg": "image/jpeg", "gif": "image/gif",
         "bmp": "image/bmp", "ppm": "image/x-portable-pixmap"}
MAKS_PİKSEL = 100_000_000


def _xəta(mesaj: str, tip: str = "ŞəkilXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def rəng(x: Any) -> tuple[int, int, int, int]:
    if isinstance(x, (list, tuple)) and len(x) in (3, 4) and all(
            isinstance(e, (int, float)) and not isinstance(e, bool)
            for e in x):
        v = [max(0, min(255, int(round(e)))) for e in x]
        return (v[0], v[1], v[2], v[3] if len(v) == 4 else 255)
    if isinstance(x, str):
        s = x.strip()
        if s in ("şəffaf", "transparent"):
            return (0, 0, 0, 0)
        if s in RƏNGLƏR:
            return RƏNGLƏR[s] + (255,)
        m = re.fullmatch(r"#([0-9a-fA-F]{3,8})", s)
        if m and len(m.group(1)) in (3, 4, 6, 8):
            h = m.group(1)
            if len(h) in (3, 4):
                h = "".join(c * 2 for c in h)
            v = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
            return (v[0], v[1], v[2], v[3] if len(v) == 4 else 255)
        m = re.fullmatch(r"rgba?\(([^)]*)\)", s)
        if m:
            h = [e.strip() for e in m.group(1).split(",")]
            if len(h) in (3, 4):
                try:
                    v = [int(float(e)) for e in h[:3]]
                    a = int(float(h[3]) * 255) if len(h) == 4 else 255
                    return (*[max(0, min(255, e)) for e in v],
                            max(0, min(255, a)))
                except ValueError:
                    pass
    raise _xəta(f"rəng anlaşılmadı: `{x}`", "ArqumentXətası")


def _hex(r: tuple) -> str:
    return "#" + "".join(f"{v:02x}" for v in (r[:3] if r[3] == 255 else r))


def _ölçü_yoxla(en: Any, h: Any) -> tuple[int, int]:
    for v, ad in ((en, "en"), (h, "hündürlük")):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise _xəta(f"`{ad}` müsbət tam ədəd olmalıdır", "ArqumentXətası")
    if en * h > MAKS_PİKSEL:
        raise _xəta("şəkil çox böyükdür")
    return en, h


class Şəkil:
    ALQOR_TİP_ADI = "şəkil"
    __slots__ = ("en", "h", "p", "format")

    def __init__(self, en: int, h: int, p: bytearray, format: str = ""):
        self.en, self.h, self.p, self.format = en, h, p, format

    def __repr__(self) -> str:
        return f"<şəkil {self.en}×{self.h}>"

    def __eq__(self, o: Any) -> bool:
        return isinstance(o, Şəkil) and (o.en, o.h, o.p) == (self.en, self.h,
                                                             self.p)

    __hash__ = None  # type: ignore[assignment]

    def yeni(self, en: int, h: int, p: bytearray) -> "Şəkil":
        return Şəkil(en, h, p, self.format)

    # ── Həndəsə ───────────────────────────────────────────────────────
    def kəs(self, x: int, y: int, en: int, h: int) -> "Şəkil":
        x, y = int(x), int(y)
        en, h = _ölçü_yoxla(int(en), int(h))
        if x < 0 or y < 0 or x + en > self.en or y + h > self.h:
            raise _xəta(f"kəsmə sahəsi şəkildən kənara çıxır "
                        f"({self.en}×{self.h})", "ArqumentXətası")
        n = bytearray(en * h * 4)
        for yy in range(h):
            o = ((y + yy) * self.en + x) * 4
            n[yy * en * 4:(yy + 1) * en * 4] = self.p[o:o + en * 4]
        return self.yeni(en, h, n)

    def ölçü_dəyiş(self, en: Any = None, h: Any = None,
                   üsul: str = "avto") -> "Şəkil":
        if en is None and h is None:
            raise _xəta("`en` və ya `hündürlük` verin", "ArqumentXətası")
        if en is None:
            en = max(1, round(self.en * h / self.h))
        if h is None:
            h = max(1, round(self.h * en / self.en))
        en, h = _ölçü_yoxla(int(en), int(h))
        if üsul == "avto":
            üsul = "orta" if en <= self.en and h <= self.h else "bilinear"
        if üsul == "yaxın":
            return self._yaxın(en, h)
        if üsul == "orta":
            if en > self.en or h > self.h:
                return self._bilinear(en, h)
            return self._orta(en, h)
        if üsul == "bilinear":
            return self._bilinear(en, h)
        raise _xəta('`üsul` "avto", "yaxın", "bilinear" və ya "orta" '
                    "olmalıdır", "ArqumentXətası")

    def _yaxın(self, en: int, h: int) -> "Şəkil":
        n = bytearray(en * h * 4)
        xs = [min(self.en - 1, int((x + 0.5) * self.en / en)) * 4
              for x in range(en)]
        for y in range(h):
            sy = min(self.h - 1, int((y + 0.5) * self.h / h))
            s = sy * self.en * 4
            o = y * en * 4
            for x, sx in enumerate(xs):
                n[o + x * 4:o + x * 4 + 4] = self.p[s + sx:s + sx + 4]
        return self.yeni(en, h, n)

    def _bilinear(self, en: int, h: int) -> "Şəkil":
        p, se = self.p, self.en

        def ox(n, mənbə):
            f = mənbə / n
            r = []
            for k in range(n):
                q = (k + 0.5) * f - 0.5
                a = max(0, min(mənbə - 1, math.floor(q)))
                b = min(mənbə - 1, a + 1)
                r.append((a, b, max(0.0, min(1.0, q - a))))
            return r
        xs, ys = ox(en, self.en), ox(h, self.h)
        n = bytearray(en * h * 4)
        for y, (y0, y1, ty) in enumerate(ys):
            r0, r1 = y0 * se * 4, y1 * se * 4
            o = y * en * 4
            for x0, x1, tx in xs:
                a0, a1 = r0 + x0 * 4, r0 + x1 * 4
                b0, b1 = r1 + x0 * 4, r1 + x1 * 4
                for k in range(4):
                    üst = p[a0 + k] + (p[a1 + k] - p[a0 + k]) * tx
                    alt = p[b0 + k] + (p[b1 + k] - p[b0 + k]) * tx
                    n[o] = int(üst + (alt - üst) * ty + 0.5)
                    o += 1
        return self.yeni(en, h, n)

    def _orta(self, en: int, h: int) -> "Şəkil":
        """Kiçiltmə: hər hədəf pikseli mənbə sahəsinin ortalaması
        (aliasing olmur)."""
        p, se = self.p, self.en
        fx, fy = self.en / en, self.h / h
        n = bytearray(en * h * 4)
        xa = [(int(x * fx), max(int(x * fx) + 1, int((x + 1) * fx)))
              for x in range(en)]
        o = 0
        for y in range(h):
            y0 = int(y * fy)
            y1 = max(y0 + 1, int((y + 1) * fy))
            for x0, x1 in xa:
                r = g = b = a = 0
                say = (x1 - x0) * (y1 - y0)
                for yy in range(y0, y1):
                    s = (yy * se + x0) * 4
                    for k in range(s, s + (x1 - x0) * 4, 4):
                        al = p[k + 3]
                        r += p[k] * al
                        g += p[k + 1] * al
                        b += p[k + 2] * al
                        a += al
                if a:
                    n[o:o + 4] = bytes((r // a, g // a, b // a,
                                        (a + say // 2) // say))
                o += 4
        return self.yeni(en, h, n)

    def miniatür(self, maks_en: int, maks_h: Any = None) -> "Şəkil":
        maks_h = maks_en if maks_h is None else maks_h
        f = min(maks_en / self.en, maks_h / self.h, 1.0)
        if f >= 1.0:
            return self.kopya()
        return self.ölçü_dəyiş(max(1, round(self.en * f)),
                               max(1, round(self.h * f)))

    def döndər(self, bucaq: Any, fon: Any = "şəffaf",
               genişlət: bool = True) -> "Şəkil":
        b = float(bucaq) % 360
        if b == 0:
            return self.kopya()
        if b in (90.0, 180.0, 270.0):
            return self._döndər90(int(b))
        return self._döndər_ixtiyari(b, rəng(fon), genişlət)

    def _döndər90(self, b: int) -> "Şəkil":
        """Saat əqrəbi istiqamətində 90/180/270°."""
        en, h, p = self.en, self.h, self.p
        if b == 180:
            n = bytearray(len(p))
            for i in range(en * h):
                j = (en * h - 1 - i) * 4
                n[i * 4:i * 4 + 4] = p[j:j + 4]
            return self.yeni(en, h, n)
        n = bytearray(len(p))
        for y in range(h):
            for x in range(en):
                s = (y * en + x) * 4
                if b == 90:
                    nx, ny = h - 1 - y, x
                else:
                    nx, ny = y, en - 1 - x
                d = (ny * h + nx) * 4
                n[d:d + 4] = p[s:s + 4]
        return self.yeni(h, en, n)

    def _döndər_ixtiyari(self, b: float, fon: tuple, genişlət: bool):
        r = math.radians(b)
        c, s = math.cos(r), math.sin(r)
        if genişlət:
            en = int(math.ceil(abs(self.en * c) + abs(self.h * s)))
            h = int(math.ceil(abs(self.en * s) + abs(self.h * c)))
        else:
            en, h = self.en, self.h
        mx, my = self.en / 2, self.h / 2
        nx, ny = en / 2, h / 2
        n = bytearray(bytes(fon) * (en * h))
        p, se, sh = self.p, self.en, self.h
        for y in range(h):
            for x in range(en):
                dx, dy = x + 0.5 - nx, y + 0.5 - ny
                sx = dx * c + dy * s + mx - 0.5
                sy = -dx * s + dy * c + my - 0.5
                if sx < -0.5 or sy < -0.5 or sx > se - 0.5 or sy > sh - 0.5:
                    continue
                x0, y0 = max(0, int(math.floor(sx))), max(0, int(
                    math.floor(sy)))
                x1, y1 = min(se - 1, x0 + 1), min(sh - 1, y0 + 1)
                tx, ty = max(0.0, sx - x0), max(0.0, sy - y0)
                o = (y * en + x) * 4
                for k in range(4):
                    a = p[(y0 * se + x0) * 4 + k] + (
                        p[(y0 * se + x1) * 4 + k] -
                        p[(y0 * se + x0) * 4 + k]) * tx
                    bb = p[(y1 * se + x0) * 4 + k] + (
                        p[(y1 * se + x1) * 4 + k] -
                        p[(y1 * se + x0) * 4 + k]) * tx
                    n[o + k] = int(a + (bb - a) * ty + 0.5)
        return self.yeni(en, h, n)

    def çevir(self, istiqamət: str = "üfüqi") -> "Şəkil":
        en, h, p = self.en, self.h, self.p
        n = bytearray(len(p))
        if istiqamət == "üfüqi":
            for y in range(h):
                for x in range(en):
                    s = (y * en + x) * 4
                    d = (y * en + en - 1 - x) * 4
                    n[d:d + 4] = p[s:s + 4]
        elif istiqamət == "şaquli":
            sətir = en * 4
            for y in range(h):
                n[(h - 1 - y) * sətir:(h - y) * sətir] = \
                    p[y * sətir:(y + 1) * sətir]
        else:
            raise _xəta('`istiqamət` "üfüqi" və ya "şaquli" olmalıdır',
                        "ArqumentXətası")
        return self.yeni(en, h, n)

    # ── Rəng filtrləri ────────────────────────────────────────────────
    def _lut(self, f, alfa: bool = False) -> "Şəkil":
        cədvəl = bytes(max(0, min(255, int(round(f(v))))) for v in range(256))
        n = bytearray(self.p)
        for k in range(3 + alfa):
            n[k::4] = bytes(n[k::4]).translate(cədvəl)
        return self.yeni(self.en, self.h, n)

    def boz(self) -> "Şəkil":
        p = self.p
        n = bytearray(p)
        for i in range(0, len(p), 4):
            v = (p[i] * 299 + p[i + 1] * 587 + p[i + 2] * 114 + 500) // 1000
            n[i] = n[i + 1] = n[i + 2] = v
        return self.yeni(self.en, self.h, n)

    def sepiya(self) -> "Şəkil":
        p = self.p
        n = bytearray(p)
        for i in range(0, len(p), 4):
            r, g, b = p[i], p[i + 1], p[i + 2]
            n[i] = min(255, int(r * .393 + g * .769 + b * .189))
            n[i + 1] = min(255, int(r * .349 + g * .686 + b * .168))
            n[i + 2] = min(255, int(r * .272 + g * .534 + b * .131))
        return self.yeni(self.en, self.h, n)

    def tərs(self) -> "Şəkil":
        return self._lut(lambda v: 255 - v)

    def parlaqlıq(self, f: Any) -> "Şəkil":
        f = float(f)
        return self._lut(lambda v: v * f)

    def kontrast(self, f: Any) -> "Şəkil":
        f = float(f)
        p = self.p
        orta = sum(p[0::4]) * .299 + sum(p[1::4]) * .587 + sum(p[2::4]) * .114
        orta /= max(1, self.en * self.h)
        return self._lut(lambda v: orta + (v - orta) * f)

    def qamma(self, q: Any) -> "Şəkil":
        q = float(q)
        if q <= 0:
            raise _xəta("qamma müsbət olmalıdır", "ArqumentXətası")
        return self._lut(lambda v: 255 * (v / 255) ** (1 / q))

    def doyma(self, f: Any) -> "Şəkil":
        f = float(f)
        p = self.p
        n = bytearray(p)
        for i in range(0, len(p), 4):
            r, g, b = p[i], p[i + 1], p[i + 2]
            l = r * .299 + g * .587 + b * .114
            for k, v in ((0, r), (1, g), (2, b)):
                d = l + (v - l) * f
                n[i + k] = 0 if d < 0 else (255 if d > 255 else int(d + .5))
        return self.yeni(self.en, self.h, n)

    def şəffaflıq(self, f: Any) -> "Şəkil":
        f = max(0.0, min(1.0, float(f)))
        n = bytearray(self.p)
        n[3::4] = bytes(int(a * f + .5) for a in self.p[3::4])
        return self.yeni(self.en, self.h, n)

    def _konvolyusiya_1d(self, çəki: list[float], üfüqi: bool) -> bytearray:
        en, h, p = self.en, self.h, self.p
        r = len(çəki) // 2
        n = bytearray(len(p))
        for y in range(h):
            for x in range(en):
                cəm = [0.0, 0.0, 0.0, 0.0]
                for k, w in enumerate(çəki):
                    if üfüqi:
                        xx = min(en - 1, max(0, x + k - r))
                        o = (y * en + xx) * 4
                    else:
                        yy = min(h - 1, max(0, y + k - r))
                        o = (yy * en + x) * 4
                    cəm[0] += p[o] * w
                    cəm[1] += p[o + 1] * w
                    cəm[2] += p[o + 2] * w
                    cəm[3] += p[o + 3] * w
                o = (y * en + x) * 4
                for k in range(4):
                    v = cəm[k]
                    n[o + k] = 0 if v < 0 else (255 if v > 255
                                                else int(v + .5))
        return n

    def bulanıq(self, radius: Any = 2) -> "Şəkil":
        """Qauss bulanıqlığı (ayrılan nüvə)."""
        r = float(radius)
        if r <= 0:
            return self.kopya()
        σ = r / 2 if r > 1 else 0.5
        k = int(math.ceil(r))
        çəki = [math.exp(-(i * i) / (2 * σ * σ)) for i in range(-k, k + 1)]
        c = sum(çəki)
        çəki = [w / c for w in çəki]
        ara = self.yeni(self.en, self.h, self._konvolyusiya_1d(çəki, True))
        return self.yeni(self.en, self.h, ara._konvolyusiya_1d(çəki, False))

    def itilə(self, miqdar: Any = 1.0) -> "Şəkil":
        """Kəskinləşdirmə (unsharp mask)."""
        m = float(miqdar)
        b = self.bulanıq(1.5)
        n = bytearray(self.p)
        for i in range(len(n)):
            if i % 4 == 3:
                continue
            v = self.p[i] + (self.p[i] - b.p[i]) * m
            n[i] = 0 if v < 0 else (255 if v > 255 else int(v + .5))
        return self.yeni(self.en, self.h, n)

    # ── Çəkmə ─────────────────────────────────────────────────────────
    def _qarışdır(self, n: bytearray, x: int, y: int, r: tuple,
                  örtük: float = 1.0) -> None:
        if not (0 <= x < self.en and 0 <= y < self.h):
            return
        o = (y * self.en + x) * 4
        a = r[3] / 255 * örtük
        if a >= 1:
            n[o:o + 4] = bytes(r)
            return
        if a <= 0:
            return
        da = n[o + 3] / 255
        ya = a + da * (1 - a)
        if ya <= 0:
            return
        for k in range(3):
            n[o + k] = int((r[k] * a + n[o + k] * da * (1 - a)) / ya + .5)
        n[o + 3] = int(ya * 255 + .5)

    def doldur(self, r: Any) -> "Şəkil":
        return self.yeni(self.en, self.h,
                         bytearray(bytes(rəng(r)) * (self.en * self.h)))

    def piksel(self, x: int, y: int) -> list[int]:
        if not (0 <= x < self.en and 0 <= y < self.h):
            raise _xəta(f"({x}, {y}) şəkildən kənardadır", "İndeksXətası")
        o = (y * self.en + x) * 4
        return list(self.p[o:o + 4])

    def piksel_qoy(self, x: int, y: int, r: Any) -> "Şəkil":
        n = bytearray(self.p)
        if 0 <= x < self.en and 0 <= y < self.h:
            o = (y * self.en + x) * 4
            n[o:o + 4] = bytes(rəng(r))
        return self.yeni(self.en, self.h, n)

    def düzbucaqlı(self, x: Any, y: Any, en: Any, h: Any, r: Any,
                   doldur: bool = True, qalınlıq: Any = 1) -> "Şəkil":
        c = rəng(r)
        n = bytearray(self.p)
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + int(en), y0 + int(h)
        q = max(1, int(qalınlıq))
        for yy in range(max(0, y0), min(self.h, y1)):
            for xx in range(max(0, x0), min(self.en, x1)):
                if doldur or yy < y0 + q or yy >= y1 - q or xx < x0 + q or \
                        xx >= x1 - q:
                    self._qarışdır(n, xx, yy, c)
        return self.yeni(self.en, self.h, n)

    def xətt(self, x1: Any, y1: Any, x2: Any, y2: Any, r: Any,
             qalınlıq: Any = 1) -> "Şəkil":
        """Hamarlanmış (antialiased) xətt — məsafə sahəsi ilə."""
        c = rəng(r)
        n = bytearray(self.p)
        x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
        yarı = max(0.5, float(qalınlıq) / 2)
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        for yy in range(max(0, int(min(y1, y2) - yarı - 1)),
                        min(self.h, int(max(y1, y2) + yarı + 2))):
            for xx in range(max(0, int(min(x1, x2) - yarı - 1)),
                            min(self.en, int(max(x1, x2) + yarı + 2))):
                px, py = xx - x1, yy - y1
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, (px * dx + py * dy)
                                                     / L2))
                d = math.hypot(px - t * dx, py - t * dy)
                örtük = max(0.0, min(1.0, yarı + 0.5 - d))
                if örtük > 0:
                    self._qarışdır(n, xx, yy, c, örtük)
        return self.yeni(self.en, self.h, n)

    def dairə(self, mx: Any, my: Any, radius: Any, r: Any,
              doldur: bool = True, qalınlıq: Any = 1) -> "Şəkil":
        c = rəng(r)
        n = bytearray(self.p)
        mx, my, R = float(mx), float(my), float(radius)
        q = float(qalınlıq)
        for yy in range(max(0, int(my - R - 2)), min(self.h, int(my + R + 2))):
            for xx in range(max(0, int(mx - R - 2)),
                            min(self.en, int(mx + R + 2))):
                d = math.hypot(xx + 0.5 - mx, yy + 0.5 - my)
                if doldur:
                    örtük = R + 0.5 - d
                else:
                    örtük = min(R + 0.5 - d, d - (R - q) + 0.5)
                örtük = max(0.0, min(1.0, örtük))
                if örtük > 0:
                    self._qarışdır(n, xx, yy, c, örtük)
        return self.yeni(self.en, self.h, n)

    def yapışdır(self, digər: Any, x: Any = 0, y: Any = 0,
                 şəffaflıq: Any = 1.0) -> "Şəkil":
        if not isinstance(digər, Şəkil):
            raise _xəta(f"`yapışdır` şəkil gözləyir, `{tip_adı(digər)}` "
                        "gəlib", "TipXətası")
        n = bytearray(self.p)
        x, y, f = int(x), int(y), float(şəffaflıq)
        q = digər.p
        for yy in range(max(0, -y), min(digər.h, self.h - y)):
            for xx in range(max(0, -x), min(digər.en, self.en - x)):
                o = (yy * digər.en + xx) * 4
                self._qarışdır(n, x + xx, y + yy, tuple(q[o:o + 4]), f)
        return self.yeni(self.en, self.h, n)

    # ── Məlumat ───────────────────────────────────────────────────────
    def kopya(self) -> "Şəkil":
        return self.yeni(self.en, self.h, bytearray(self.p))

    def orta_rəng(self) -> str:
        n = max(1, self.en * self.h)
        return _hex((sum(self.p[0::4]) // n, sum(self.p[1::4]) // n,
                     sum(self.p[2::4]) // n, 255))

    def histogram(self) -> dict:
        n = {}
        for ad, k in (("r", 0), ("g", 1), ("b", 2), ("a", 3)):
            say = [0] * 256
            for v in self.p[k::4]:
                say[v] += 1
            n[ad] = say
        return n

    def baytlar(self, format: str = "png", keyfiyyət: Any = 90) -> bytes:
        f = FORMATLAR.get("." + str(format).lower().lstrip("."), None)
        if f is None:
            raise _xəta(f"`{format}` formatı dəstəklənmir — png, jpeg, gif, "
                        "bmp, ppm")
        q = int(keyfiyyət)
        if not 1 <= q <= 100:
            raise _xəta("`keyfiyyət` 1–100 arasında olmalıdır",
                        "ArqumentXətası")
        return K.yaz(f, self.en, self.h, self.p, q)

    def saxla(self, yol: Any, keyfiyyət: Any = 90,
              format: Any = None) -> None:
        p = Path(str(yol))
        f = format or p.suffix.lower()
        if not f or "." + str(f).lower().lstrip(".") not in FORMATLAR:
            raise _xəta(f'"{yol}": format uzantıdan tapılmadı — .png .jpg '
                        ".gif .bmp .ppm")
        p.write_bytes(self.baytlar(str(f), keyfiyyət))

    def data_uri(self, format: str = "png", keyfiyyət: Any = 90) -> str:
        f = FORMATLAR["." + str(format).lower().lstrip(".")]
        return (f"data:{_MIME[f]};base64," +
                base64.b64encode(self.baytlar(format, keyfiyyət))
                .decode("ascii"))


Şəkil.ALQOR_METODLARI = {
    "en": lambda i, ş: ş.en,
    "hündürlük": lambda i, ş: ş.h,
    "ölçü": lambda i, ş: [ş.en, ş.h],
    "format": lambda i, ş: ş.format or None,
    "kəs": lambda i, ş, x, y, en, h: ş.kəs(x, y, en, h),
    "ölçüDəyiş": lambda i, ş, en=None, hündürlük=None, üsul="avto":
        ş.ölçü_dəyiş(en, hündürlük, üsul),
    "miniatür": lambda i, ş, en, h=None: ş.miniatür(en, h),
    "döndər": lambda i, ş, b, fon="şəffaf", genişlət=True:
        ş.döndər(b, fon, genişlət),
    "çevir": lambda i, ş, ist="üfüqi": ş.çevir(ist),
    "boz": lambda i, ş: ş.boz(),
    "sepiya": lambda i, ş: ş.sepiya(),
    "tərs": lambda i, ş: ş.tərs(),
    "parlaqlıq": lambda i, ş, f: ş.parlaqlıq(f),
    "kontrast": lambda i, ş, f: ş.kontrast(f),
    "qamma": lambda i, ş, q: ş.qamma(q),
    "doyma": lambda i, ş, f: ş.doyma(f),
    "şəffaflıq": lambda i, ş, f: ş.şəffaflıq(f),
    "bulanıq": lambda i, ş, r=2: ş.bulanıq(r),
    "itilə": lambda i, ş, m=1.0: ş.itilə(m),
    "doldur": lambda i, ş, r: ş.doldur(r),
    "piksel": lambda i, ş, x, y: ş.piksel(x, y),
    "pikselQoy": lambda i, ş, x, y, r: ş.piksel_qoy(x, y, r),
    "düzbucaqlı": lambda i, ş, x, y, en, h, r, doldur=True, qalınlıq=1:
        ş.düzbucaqlı(x, y, en, h, r, doldur, qalınlıq),
    "xətt": lambda i, ş, x1, y1, x2, y2, r, qalınlıq=1:
        ş.xətt(x1, y1, x2, y2, r, qalınlıq),
    "dairə": lambda i, ş, x, y, rad, r, doldur=True, qalınlıq=1:
        ş.dairə(x, y, rad, r, doldur, qalınlıq),
    "yapışdır": lambda i, ş, d, x=0, y=0, şəffaflıq=1.0:
        ş.yapışdır(d, x, y, şəffaflıq),
    "kopya": lambda i, ş: ş.kopya(),
    "ortaRəng": lambda i, ş: ş.orta_rəng(),
    "histogram": lambda i, ş: ş.histogram(),
    "baytlar": lambda i, ş, f="png", keyfiyyət=90: ş.baytlar(f, keyfiyyət),
    "saxla": lambda i, ş, yol, keyfiyyət=90, format=None:
        ş.saxla(yol, keyfiyyət, format),
    "dataURI": lambda i, ş, f="png", keyfiyyət=90: ş.data_uri(f, keyfiyyət),
}


def _istiqamət_tətbiq(ş: Şəkil, ist: int) -> Şəkil:
    if ist == 2:
        return ş.çevir("üfüqi")
    if ist == 3:
        return ş._döndər90(180)
    if ist == 4:
        return ş.çevir("şaquli")
    if ist == 5:
        return ş._döndər90(90).çevir("üfüqi")
    if ist == 6:
        return ş._döndər90(90)
    if ist == 7:
        return ş._döndər90(270).çevir("üfüqi")
    if ist == 8:
        return ş._döndər90(270)
    return ş


def baytlardan(b: Any, avtoDöndər: bool = True) -> Şəkil:
    if isinstance(b, list):
        b = bytes(b)
    if not isinstance(b, (bytes, bytearray)):
        raise _xəta(f"bayt gözlənilir, `{tip_adı(b)}` gəlib", "TipXətası")
    try:
        en, h, p, m = K.aç(bytes(b))
    except K.KodekXətası as x:
        raise _xəta(str(x))
    except (IndexError, struct.error, ValueError, ZeroDivisionError) as x:
        raise _xəta(f"şəkil faylı pozulub ({type(x).__name__})")
    ş = Şəkil(en, h, p, K.format_tap(bytes(b)) or "")
    if avtoDöndər and m.get("istiqamət", 1) != 1:
        ş = _istiqamət_tətbiq(ş, m["istiqamət"])
    return ş


def aç(yol: Any, avtoDöndər: bool = True) -> Şəkil:
    try:
        b = Path(str(yol)).read_bytes()
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" faylı tapılmadı',
                        None, "ALQ-R009")
    return baytlardan(b, avtoDöndər)


def yarat(en: Any, h: Any, fon: Any = "şəffaf") -> Şəkil:
    en, h = _ölçü_yoxla(en, h)
    return Şəkil(en, h, bytearray(bytes(rəng(fon)) * (en * h)))


def data_uri_aç(m: Any) -> Şəkil:
    s = str(m)
    if not s.startswith("data:") or ";base64," not in s:
        raise _xəta("data URI `data:…;base64,…` formatında olmalıdır")
    return baytlardan(base64.b64decode(s.split(",", 1)[1]))


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "aç": D("aç", aç, 1, 2),
        "baytlardan": D("baytlardan", baytlardan, 1, 2),
        "dataURIdən": D("dataURIdən", data_uri_aç, 1, 1),
        "yarat": D("yarat", yarat, 2, 3),
        "rəng": D("rəng", lambda r: list(rəng(r)), 1, 1),
        "formatlar": D("formatlar", lambda: ["png", "jpeg", "gif", "bmp",
                                             "ppm"]),
        "formatTap": D("formatTap", lambda b: K.format_tap(bytes(b)), 1, 1),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, b = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.MƏNTİQ
    Ş = T.Sadə("şəkil")
    return {
        "aç": F(m, b, qaytarır=Ş, standart=1),
        "baytlardan": F(e, b, qaytarır=Ş, standart=1),
        "dataURIdən": F(m, qaytarır=Ş),
        "yarat": F(i, i, e, qaytarır=Ş, standart=1),
        "rəng": F(e, qaytarır=T.Siyahı(i)),
        "formatlar": F(qaytarır=T.Siyahı(m)),
        "formatTap": F(e, qaytarır=T.ixtiyari(m)),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, b, o = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.MƏNTİQ, T.ONLUQ
    Ş = T.Sadə("şəkil")
    ş = {ad: F(qaytarır=Ş) for ad in (
        "boz", "sepiya", "tərs", "kopya")}
    ş.update({ad: F(o, qaytarır=Ş) for ad in (
        "parlaqlıq", "kontrast", "qamma", "doyma", "şəffaflıq")})
    ş.update({
        "en": F(qaytarır=i), "hündürlük": F(qaytarır=i),
        "ölçü": F(qaytarır=T.Siyahı(i)),
        "format": F(qaytarır=T.ixtiyari(m)),
        "kəs": F(i, i, i, i, qaytarır=Ş),
        "ölçüDəyiş": F(i, i, m, qaytarır=Ş, standart=3),
        "miniatür": F(i, i, qaytarır=Ş, standart=1),
        "döndər": F(o, e, b, qaytarır=Ş, standart=2),
        "çevir": F(m, qaytarır=Ş, standart=1),
        "bulanıq": F(o, qaytarır=Ş, standart=1),
        "itilə": F(o, qaytarır=Ş, standart=1),
        "doldur": F(e, qaytarır=Ş),
        "piksel": F(i, i, qaytarır=T.Siyahı(i)),
        "pikselQoy": F(i, i, e, qaytarır=Ş),
        "düzbucaqlı": F(o, o, o, o, e, b, o, qaytarır=Ş, standart=2),
        "xətt": F(o, o, o, o, e, o, qaytarır=Ş, standart=1),
        "dairə": F(o, o, o, e, b, o, qaytarır=Ş, standart=2),
        "yapışdır": F(Ş, i, i, o, qaytarır=Ş, standart=3),
        "ortaRəng": F(qaytarır=m),
        "histogram": F(qaytarır=T.Lüğət(m, T.Siyahı(i))),
        "baytlar": F(m, i, qaytarır=T.BAYT, standart=2),
        "saxla": F(m, i, m, qaytarır=T.HEÇ, standart=2),
        "dataURI": F(m, i, qaytarır=m, standart=2),
    })
    return {"şəkil": ş}
