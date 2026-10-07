"""
`pdf` — PDF sənədi yaratma (§ 10.17). Azərbaycan hərfləri (ə ğ ş ı İ …)
üçün sistemin TrueType şrifti (DejaVu, Arial, Liberation, Noto, Segoe UI)
daxil edilir — yalnız istifadə olunan qliflər (alt dəst), fayl kiçik qalır.

    gətir pdf

    dəyişən s = pdf.sənəd(başlıq: "Aylıq hesabat", müəllif: "Alqor MMC")
    s.başlıq("Aylıq hesabat")
    s.abzas("Bu ay satış **12%** artıb. *Qeyd:* rəqəmlər ilkindir.")
    s.siyahı(["Bakı — 2 300", "Gəncə — 330"])
    s.cədvəl([["Məhsul", "Say", "Qiymət"],
              ["Alma", 120, "1,20 ₼"],
              ["Armud", 80, "1,50 ₼"]], zolaqlı: doğru)
    s.şəkil("qrafik.png", en: 120, düzləndir: "mərkəz")
    s.yeniSəhifə()
    s.mətn(20, 30, "Mütləq mövqedə mətn", ölçü: 14, rəng: "#2563eb")
    s.səhifəNömrələri("Səhifə [n] / [cəm]")
    s.saxla("hesabat.pdf")

Ölçülər millimetrlədir; koordinatlar səhifənin SOL ÜST küncündən.
`abzas` mətnində `**qalın**` və `*kursiv*` işlənir (`xam: doğru` — söndürür).
Öz şriftiniz: `pdf.sənəd(şrift: "yol/Şrift.ttf")` və ya
`şrift: {"adi": "…", "qalın": "…", "kursiv": "…", "qalınKursiv": "…"}`.
"""

from __future__ import annotations

import re
import struct
import time
import zlib
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, mətnə
from . import _ttf

MM = 72 / 25.4
ÖLÇÜLƏR = {"A3": (297, 420), "A4": (210, 297), "A5": (148, 210),
           "A6": (105, 148), "Letter": (215.9, 279.4),
           "Legal": (215.9, 355.6)}
BAŞLIQ_ÖLÇÜLƏRİ = {1: 20, 2: 16, 3: 13.5, 4: 12}


def _xəta(mesaj: str, tip: str = "PDFXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _rəng(r: Any) -> tuple[float, float, float]:
    from .sekil import rəng
    c = rəng(r)
    return (c[0] / 255, c[1] / 255, c[2] / 255)


def _ə(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


def _pdf_mətn(s: str) -> str:
    """Info lüğəti üçün UTF-16BE hex mətni."""
    return "<FEFF" + s.encode("utf-16-be").hex().upper() + ">"


class _Şrift:
    def __init__(self, ttf: _ttf.TTF, ad: str, sənəd: "Sənəd | None" = None):
        self.t = ttf
        self.ad = ad                                 # /F1 …
        self.istifadə: dict[int, str] = {}
        self.sənəd = sənəd

    def parçalar(self, s: str) -> list[tuple["_Şrift", str]]:
        """Mətni şriftlərə böl: əsas şriftdə olmayan simvollar (məs. ₼)
        ehtiyat şriftdən götürülür."""
        n: list[tuple[_Şrift, str]] = []
        for ch in s:
            ş = self
            if not self.t.cmap.get(ord(ch)) and self.sənəd is not None \
                    and not ch.isspace():
                ş = self.sənəd._ehtiyat(ch) or self
            if n and n[-1][0] is ş:
                n[-1] = (ş, n[-1][1] + ch)
            else:
                n.append((ş, ch))
        return n

    def kodla(self, s: str) -> str:
        n = []
        for ch in s:
            g = self.t.cmap.get(ord(ch), 0)
            if g:
                self.istifadə.setdefault(g, ch)
            n.append(f"{g:04X}")
        return "".join(n)

    def en(self, s: str, ölçü: float) -> float:
        """mm ilə."""
        return sum(ş.t.mətn_eni(p, ölçü) for ş, p in self.parçalar(s)) / MM


class _Səhifə:
    def __init__(self, en: float, h: float):
        self.en, self.h = en, h
        self.əmrlər: list[str] = []
        self.şriftlər: set[str] = set()
        self.şəkillər: set[str] = set()


class Sənəd:
    ALQOR_TİP_ADI = "pdfSənədi"

    def __init__(self, ölçü: Any = "A4", istiqamət: str = "portret",
                 kənar: Any = 20, şrift: Any = None, başlıq: Any = None,
                 müəllif: Any = None, mövzu: Any = None,
                 şriftÖlçüsü: Any = 11, sətirAralığı: Any = 1.4):
        if isinstance(ölçü, str):
            if ölçü not in ÖLÇÜLƏR:
                raise _xəta(f"naməlum səhifə ölçüsü `{ölçü}` — "
                            + ", ".join(ÖLÇÜLƏR), "ArqumentXətası")
            en, h = ÖLÇÜLƏR[ölçü]
        elif isinstance(ölçü, list) and len(ölçü) == 2:
            en, h = float(ölçü[0]), float(ölçü[1])
        else:
            raise _xəta('`ölçü` "A4" kimi ad və ya [en, hündürlük] (mm) '
                        "olmalıdır", "ArqumentXətası")
        if istiqamət == "albom":
            en, h = max(en, h), min(en, h)
        elif istiqamət != "portret":
            raise _xəta('`istiqamət` "portret" və ya "albom" olmalıdır',
                        "ArqumentXətası")
        self.en, self.h = en, h
        k = kənar if isinstance(kənar, list) else [kənar] * 4
        if len(k) != 4:
            raise _xəta("`kənar` ədəd və ya [üst, sağ, alt, sol] olmalıdır",
                        "ArqumentXətası")
        self.üst, self.sağ, self.alt, self.sol = (float(x) for x in k)
        self.ölçü = float(şriftÖlçüsü)
        self.aralıq = float(sətirAralığı)
        self.info = {"Title": başlıq, "Author": müəllif, "Subject": mövzu}
        self._şriftləri_yüklə(şrift)
        self.səhifələr: list[_Səhifə] = []
        self.şəkillər: dict[str, dict] = {}
        self.nömrə_şablonu: tuple | None = None
        self.y = 0.0
        self.yeni_səhifə()

    # ── Şriftlər ──────────────────────────────────────────────────────
    def _şriftləri_yüklə(self, şrift: Any) -> None:
        if şrift is None:
            dəst = _ttf.sistem_şrifti()
            if dəst is None:
                raise _xəta("sistemdə TrueType şrift tapılmadı — "
                            '`pdf.sənəd(şrift: "yol/Şrift.ttf")` verin')
            yollar = dict(zip(("adi", "qalın", "kursiv", "qalınKursiv"),
                              dəst))
        elif isinstance(şrift, str):
            yollar = {"adi": şrift}
        elif isinstance(şrift, dict) and "adi" in şrift:
            yollar = dict(şrift)
        else:
            raise _xəta('`şrift` yol və ya {"adi": …, "qalın": …} '
                        "olmalıdır", "ArqumentXətası")
        self.şriftlər: dict[str, _Şrift] = {}
        keş: dict[str, _Şrift] = {}
        for növ in ("adi", "qalın", "kursiv", "qalınKursiv"):
            yol = yollar.get(növ)
            if not yol:
                continue
            if yol in keş:
                self.şriftlər[növ] = keş[yol]
                continue
            try:
                data = Path(str(yol)).read_bytes()
            except OSError:
                raise AlqorXəta("FaylTapılmadıXətası",
                                f'"{yol}" şrift faylı tapılmadı', None,
                                "ALQ-R009")
            try:
                t = _ttf.TTF(data, Path(str(yol)).name)
            except _ttf.ŞriftXətası as x:
                raise _xəta(str(x))
            except (struct.error, IndexError):
                raise _xəta(f'"{yol}" şrift faylı pozulub')
            ş = _Şrift(t, f"F{len(keş) + 1}", self)
            keş[yol] = ş
            self.şriftlər[növ] = ş
        a = self.şriftlər["adi"]
        self.şriftlər.setdefault("qalın", a)
        self.şriftlər.setdefault("kursiv", a)
        self.şriftlər.setdefault("qalınKursiv",
                                 self.şriftlər["qalın"]
                                 if self.şriftlər["qalın"] is not a
                                 else self.şriftlər["kursiv"])
        # Qalın şrift yoxdursa — kontur ilə "süni qalın"
        self.süni_qalın = self.şriftlər["qalın"] is a
        self._ehtiyatlar: list[_Şrift] | None = None
        self._ehtiyat_keş: dict[str, _Şrift | None] = {}
        self._şrift_sayı = len(keş)

    def _ehtiyat(self, ch: str) -> "_Şrift | None":
        if ch in self._ehtiyat_keş:
            return self._ehtiyat_keş[ch]
        if self._ehtiyatlar is None:
            self._ehtiyatlar = []
            əsaslar = {ş.t.ad for ş in self.şriftlər.values()}
            for yol in _ttf.EHTİYAT_ŞRİFTLƏR:
                if Path(yol).is_file() and Path(yol).name not in əsaslar:
                    try:
                        t = _ttf.TTF(Path(yol).read_bytes(), Path(yol).name)
                    except (_ttf.ŞriftXətası, struct.error, IndexError,
                            OSError):
                        continue
                    self._şrift_sayı += 1
                    self._ehtiyatlar.append(
                        _Şrift(t, f"F{self._şrift_sayı}", None))
        n = next((ş for ş in self._ehtiyatlar if ş.t.cmap.get(ord(ch))),
                 None)
        self._ehtiyat_keş[ch] = n
        return n

    def _ş(self, qalın: bool, kursiv: bool) -> _Şrift:
        return self.şriftlər[("qalınKursiv" if qalın and kursiv else
                              "qalın" if qalın else
                              "kursiv" if kursiv else "adi")]

    # ── Səhifə və kursor ──────────────────────────────────────────────
    @property
    def səhifə(self) -> _Səhifə:
        return self.səhifələr[-1]

    @property
    def məzmun_eni(self) -> float:
        return self.en - self.sol - self.sağ

    def yeni_səhifə(self) -> None:
        self.səhifələr.append(_Səhifə(self.en, self.h))
        self.y = self.üst

    def _yer(self, h: float) -> None:
        """`h` mm hündürlük yoxdursa yeni səhifəyə keç."""
        if self.y + h > self.h - self.alt and self.y > self.üst + 0.01:
            self.yeni_səhifə()

    def _y(self, y_mm: float) -> float:
        return (self.h - y_mm) * MM

    # ── Aşağı səviyyəli çəkmə ─────────────────────────────────────────
    def _mətn_əmri(self, x: float, y_baz: float, s: str, ş: _Şrift,
                   ölçü: float, rəng=(0, 0, 0), süni_qalın=False) -> None:
        if not s:
            return
        p = self.səhifə
        r, g, b = rəng
        əlavə = ""
        if süni_qalın:
            əlavə = f"2 Tr {_ə(ölçü * 0.03)} w {_ə(r)} {_ə(g)} {_ə(b)} RG "
        hissələr = []
        for şr, parça in ş.parçalar(s):
            p.şriftlər.add(şr.ad)
            hissələr.append(f"/{şr.ad} {_ə(ölçü)} Tf <{şr.kodla(parça)}> Tj")
        p.əmrlər.append(
            f"BT {əlavə}{_ə(r)} {_ə(g)} {_ə(b)} rg "
            f"{_ə(x * MM)} {_ə(self._y(y_baz))} Td {' '.join(hissələr)} ET")

    def mətn(self, x: Any, y: Any, s: Any, ölçü: Any = None,
             rəng: Any = "qara", qalın: bool = False, kursiv: bool = False,
             düzləndir: str = "sol") -> None:
        """Mütləq mövqedə bir sətir (`y` — sətrin ÜST kənarı)."""
        ö = float(ölçü or self.ölçü)
        ş = self._ş(qalın, kursiv)
        s = mətnə(s)
        x = float(x)
        if düzləndir == "mərkəz":
            x -= ş.en(s, ö) / 2
        elif düzləndir == "sağ":
            x -= ş.en(s, ö)
        baz = float(y) + self._yuxarı(ş, ö)
        self._mətn_əmri(x, baz, s, ş, ö, _rəng(rəng),
                        qalın and self.süni_qalın)

    def _yuxarı(self, ş: _Şrift, ölçü: float) -> float:
        return ş.t.yuxarı / ş.t.vahid * ölçü / MM

    def xətt(self, x1: Any, y1: Any, x2: Any, y2: Any, rəng: Any = "boz",
             qalınlıq: Any = 0.3) -> None:
        r, g, b = _rəng(rəng)
        self.səhifə.əmrlər.append(
            f"{_ə(r)} {_ə(g)} {_ə(b)} RG {_ə(float(qalınlıq) * MM)} w "
            f"{_ə(float(x1) * MM)} {_ə(self._y(float(y1)))} m "
            f"{_ə(float(x2) * MM)} {_ə(self._y(float(y2)))} l S")

    def düzbucaqlı(self, x: Any, y: Any, en: Any, h: Any,
                   rəng: Any = "boz", doldur: bool = True,
                   qalınlıq: Any = 0.3, künc: Any = 0) -> None:
        r, g, b = _rəng(rəng)
        x, y, en, h = float(x), float(y), float(en), float(h)
        k = min(float(künc), en / 2, h / 2)
        if k > 0:
            yol = self._yuvarlaq_yol(x, y, en, h, k)
        else:
            yol = (f"{_ə(x * MM)} {_ə(self._y(y + h))} {_ə(en * MM)} "
                   f"{_ə(h * MM)} re")
        if doldur:
            self.səhifə.əmrlər.append(f"{_ə(r)} {_ə(g)} {_ə(b)} rg {yol} f")
        else:
            self.səhifə.əmrlər.append(
                f"{_ə(r)} {_ə(g)} {_ə(b)} RG {_ə(float(qalınlıq) * MM)} w "
                f"{yol} S")

    def _yuvarlaq_yol(self, x, y, en, h, k) -> str:
        c = 0.5523 * k

        def p(a, b):
            return f"{_ə(a * MM)} {_ə(self._y(b))}"
        return (f"{p(x + k, y)} m {p(x + en - k, y)} l "
                f"{p(x + en - k + c, y)} {p(x + en, y + k - c)} "
                f"{p(x + en, y + k)} c {p(x + en, y + h - k)} l "
                f"{p(x + en, y + h - k + c)} {p(x + en - k + c, y + h)} "
                f"{p(x + en - k, y + h)} c {p(x + k, y + h)} l "
                f"{p(x + k - c, y + h)} {p(x, y + h - k + c)} "
                f"{p(x, y + h - k)} c {p(x, y + k)} l "
                f"{p(x, y + k - c)} {p(x + k - c, y)} {p(x + k, y)} c h")

    def dairə(self, mx: Any, my: Any, radius: Any, rəng: Any = "boz",
              doldur: bool = True, qalınlıq: Any = 0.3) -> None:
        R = float(radius)
        self.düzbucaqlı(float(mx) - R, float(my) - R, 2 * R, 2 * R, rəng,
                        doldur, qalınlıq, künc=R)

    # ── Mətn axını ────────────────────────────────────────────────────
    @staticmethod
    def _parçala(s: str, xam: bool) -> list[tuple[str, bool, bool]]:
        """`**qalın**`, `*kursiv*` → [(mətn, qalın, kursiv)]"""
        if xam:
            return [(s, False, False)]
        n: list[tuple[str, bool, bool]] = []
        qalın = kursiv = False
        bufer = []
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in "*\\":
                bufer.append(s[i + 1])
                i += 2
                continue
            if s.startswith("**", i):
                n.append(("".join(bufer), qalın, kursiv))
                bufer = []
                qalın = not qalın
                i += 2
                continue
            if s[i] == "*":
                n.append(("".join(bufer), qalın, kursiv))
                bufer = []
                kursiv = not kursiv
                i += 1
                continue
            bufer.append(s[i])
            i += 1
        n.append(("".join(bufer), qalın, kursiv))
        return [x for x in n if x[0]]

    def _sətirlər(self, parçalar, ölçü: float, en: float) -> list[list]:
        """Sözləri sətirlərə böl → [[(söz, ş, qalın, en_mm, boşluq_önündə)]]"""
        sözlər = []                       # (mətn, şrift, qalın, önündə boşluq)
        boşluq = False
        for mətn_, q, k in parçalar:
            ş = self._ş(q, k)
            for hissə in re.split(r"(\s+)", mətn_):
                if not hissə:
                    continue
                if hissə.isspace():
                    if "\n" in hissə:
                        sözlər.append(("\n", ş, q, False))
                    boşluq = True
                    continue
                if sözlər and not boşluq and sözlər[-1][0] != "\n":
                    # eyni söz daxilində üslub dəyişməsi — bitişik
                    sözlər.append((hissə, ş, q, False))
                else:
                    sözlər.append((hissə, ş, q, boşluq and bool(sözlər)))
                boşluq = False
        sətirlər: list[list] = [[]]
        cari = 0.0
        for söz, ş, q, ön in sözlər:
            if söz == "\n":
                sətirlər.append([])
                cari = 0.0
                continue
            boş = ş.en(" ", ölçü) if ön and sətirlər[-1] else 0.0
            w = ş.en(söz, ölçü)
            if sətirlər[-1] and cari + boş + w > en + 1e-6:
                sətirlər.append([])
                cari, boş = 0.0, 0.0
            while w > en and len(söz) > 1:              # çox uzun söz
                k = len(söz)
                while k > 1 and ş.en(söz[:k], ölçü) > en - cari:
                    k -= 1
                sətirlər[-1].append((söz[:k], ş, q, ş.en(söz[:k], ölçü),
                                     False))
                sətirlər.append([])
                cari = 0.0
                söz = söz[k:]
                w = ş.en(söz, ölçü)
            sətirlər[-1].append((söz, ş, q, w, boş > 0))
            cari += boş + w
        return sətirlər

    def _sətir_çək(self, sətir: list, x: float, baz: float, ölçü: float,
                   en: float, düzləndir: str, son: bool, rəng) -> None:
        boşluqlar = [ş.en(" ", ölçü) if ön else 0.0
                     for _, ş, _, _, ön in sətir]
        cəm = sum(w for *_, w, _ in sətir) + sum(boşluqlar)
        əlavə = 0.0
        if düzləndir == "mərkəz":
            x += (en - cəm) / 2
        elif düzləndir == "sağ":
            x += en - cəm
        elif düzləndir == "ikiTərəf" and not son:
            ara = sum(1 for b in boşluqlar if b)
            if ara:
                əlavə = (en - cəm) / ara
        for (söz, ş, q, w, ön), b in zip(sətir, boşluqlar):
            if ön:
                x += b + əlavə
            self._mətn_əmri(x, baz, söz, ş, ölçü, rəng,
                            q and self.süni_qalın)
            x += w

    def abzas(self, s: Any, ölçü: Any = None, düzləndir: str = "sol",
              rəng: Any = "qara", qalın: bool = False, kursiv: bool = False,
              xam: bool = False, girinti: Any = 0, sonra: Any = None) -> None:
        if düzləndir not in ("sol", "sağ", "mərkəz", "ikiTərəf"):
            raise _xəta('`düzləndir` "sol", "sağ", "mərkəz" və ya '
                        '"ikiTərəf" olmalıdır', "ArqumentXətası")
        ö = float(ölçü or self.ölçü)
        mətn_ = mətnə(s)
        parçalar = self._parçala(mətn_, xam)
        if qalın or kursiv:
            parçalar = [(m, q or qalın, k or kursiv) for m, q, k in parçalar]
        g = float(girinti)
        sətirlər = self._sətirlər(parçalar, ö, self.məzmun_eni - g)
        lh = ö * self.aralıq / MM
        r = _rəng(rəng)
        for i, sətir in enumerate(sətirlər):
            self._yer(lh)
            baz = self.y + (lh - ö / MM) / 2 + self._yuxarı(
                self.şriftlər["adi"], ö)
            self._sətir_çək(sətir, self.sol + g, baz, ö,
                            self.məzmun_eni - g, düzləndir,
                            i == len(sətirlər) - 1, r)
            self.y += lh
        self.y += float(sonra if sonra is not None else ö * 0.5 / MM)

    def başlıq(self, s: Any, səviyyə: Any = 1, rəng: Any = "#111827") -> None:
        sv = int(səviyyə)
        ö = BAŞLIQ_ÖLÇÜLƏRİ.get(sv, 12)
        if self.y > self.üst + 0.01:
            self.y += ö * 0.6 / MM
        self._yer(ö * 3 / MM)                  # başlıq səhifə sonunda qalmasın
        self.abzas(s, ölçü=ö, qalın=True, rəng=rəng, xam=True,
                   sonra=ö * 0.45 / MM)

    def siyahı(self, elementlər: Any, nömrəli: bool = False,
               ölçü: Any = None) -> None:
        if not isinstance(elementlər, list):
            raise _xəta("`siyahı` siyahı gözləyir", "TipXətası")
        ö = float(ölçü or self.ölçü)
        lh = ö * self.aralıq / MM
        ş = self.şriftlər["adi"]
        for i, e in enumerate(elementlər):
            işarə = f"{i + 1}." if nömrəli else ("•" if ş.t.qlif("•")
                                                  else "-")
            self._yer(lh)
            baz = self.y + (lh - ö / MM) / 2 + self._yuxarı(ş, ö)
            self._mətn_əmri(self.sol + 2, baz, işarə, ş, ö, (0, 0, 0))
            self.abzas(e, ölçü=ö, girinti=8, sonra=ö * 0.15 / MM)
        self.y += ö * 0.35 / MM

    def boşluq(self, mm: Any = 5) -> None:
        self.y += float(mm)

    def ayırıcı(self, rəng: Any = "#d1d5db", qalınlıq: Any = 0.3) -> None:
        self._yer(4)
        self.y += 2
        self.xətt(self.sol, self.y, self.en - self.sağ, self.y, rəng,
                  qalınlıq)
        self.y += 3

    # ── Cədvəl ────────────────────────────────────────────────────────
    def cədvəl(self, sətirlər: Any, başlıqlı: bool = True, enlər: Any = None,
               ölçü: Any = None, zolaqlı: bool = False,
               düzləndir: Any = None, kənarRəngi: Any = "#d1d5db",
               başlıqFonu: Any = "#f3f4f6") -> None:
        if not isinstance(sətirlər, list) or not sətirlər or not all(
                isinstance(s, list) for s in sətirlər):
            raise _xəta("`cədvəl` sətir siyahısı gözləyir: [[…], […]]",
                        "TipXətası")
        n = max(len(s) for s in sətirlər)
        cədvəl_ = [[mətnə(x) if x is not None else "" for x in s] +
                   [""] * (n - len(s)) for s in sətirlər]
        ö = float(ölçü or self.ölçü - 1)
        pad = 1.8
        lh = ö * 1.3 / MM
        ş_adi, ş_qalın = self._ş(False, False), self._ş(True, False)
        if enlər is not None:
            if not isinstance(enlər, list) or len(enlər) != n:
                raise _xəta(f"`enlər` {n} ədədli siyahı olmalıdır",
                            "ArqumentXətası")
            e = [float(x) for x in enlər]
        else:
            təbii = [max(max((ş_qalın if (başlıqlı and i == 0) else ş_adi)
                             .en(w, ö) for w in s[j].split() or [""])
                         for i, s in enumerate(cədvəl_)) for j in range(n)]
            tam = [max((ş_qalın if (başlıqlı and i == 0) else ş_adi)
                       .en(s[j], ö) for i, s in enumerate(cədvəl_))
                   for j in range(n)]
            e = [t + 2 * pad for t in tam]
            if sum(e) > self.məzmun_eni:
                minimum = [t + 2 * pad for t in təbii]
                artıq = self.məzmun_eni - sum(minimum)
                if artıq <= 0:
                    e = [self.məzmun_eni / n] * n
                else:
                    çəki = [max(0.0, a - b) for a, b in zip(e, minimum)]
                    c = sum(çəki) or 1
                    e = [m + artıq * w / c for m, w in zip(minimum, çəki)]
        rəqəm = re.compile(r"^[-+]?[\d\s.,]+(\s?[%₼$€£]|\s?[A-Z]{3})?$")
        düz = düzləndir if isinstance(düzləndir, list) else [
            "sağ" if all(rəqəm.match(s[j]) for s in
                         cədvəl_[1 if başlıqlı else 0:] if s[j])
            and any(s[j] for s in cədvəl_[1 if başlıqlı else 0:])
            else "sol" for j in range(n)]
        kr = _rəng(kənarRəngi)

        def sətir_ölç(s, başlıq_mı):
            ş_q = başlıq_mı
            hüceyrələr = [self._sətirlər([(s[j], ş_q, False)], ö,
                                         e[j] - 2 * pad) for j in range(n)]
            return hüceyrələr, max(len(h) for h in hüceyrələr) * lh + 2 * pad

        def sətir_çək(hüceyrələr, h, başlıq_mı, zolaq):
            x = self.sol
            if başlıq_mı:
                self.düzbucaqlı(self.sol, self.y, sum(e), h, başlıqFonu)
            elif zolaq:
                self.düzbucaqlı(self.sol, self.y, sum(e), h, "#f9fafb")
            for j, sət in enumerate(hüceyrələr):
                for k, xətt_ in enumerate(sət):
                    baz = self.y + pad + k * lh + (lh - ö / MM) / 2 + \
                        self._yuxarı(ş_adi, ö)
                    self._sətir_çək(xətt_, x + pad, baz, ö, e[j] - 2 * pad,
                                    "sol" if başlıq_mı else düz[j], True,
                                    (0.07, 0.09, 0.15))
                x += e[j]
            self.y += h
            sərhədlər.append(self.y)

        başlıq_s = sətir_ölç(cədvəl_[0], True) if başlıqlı else None
        self._yer((başlıq_s[1] if başlıq_s else 0) + 3 * lh)
        üst = self.y
        sərhədlər: list[float] = []
        if başlıq_s:
            sətir_çək(*başlıq_s, True, False)
        for i, s in enumerate(cədvəl_[1 if başlıqlı else 0:]):
            hüceyrələr, h = sətir_ölç(s, False)
            if self.y + h > self.h - self.alt:
                self._şaquli(üst, e, kr, sərhədlər)
                self.yeni_səhifə()
                üst = self.y
                sərhədlər = []
                if başlıq_s:
                    sətir_çək(*başlıq_s, True, False)
            sətir_çək(hüceyrələr, h, False, zolaqlı and i % 2 == 1)
        self._şaquli(üst, e, kr, sərhədlər)
        self.y += self.ölçü * 0.6 / MM

    def _şaquli(self, üst: float, e: list[float], kr,
                sərhədlər: list[float]) -> None:
        r, g, b = kr
        x = self.sol
        a = [f"{_ə(r)} {_ə(g)} {_ə(b)} RG {_ə(0.2 * MM)} w"]
        for y in sərhədlər:
            a.append(f"{_ə(self.sol * MM)} {_ə(self._y(y))} m "
                     f"{_ə((self.sol + sum(e)) * MM)} {_ə(self._y(y))} l")
        for w in [0.0] + e:
            x += w
            a.append(f"{_ə(x * MM)} {_ə(self._y(üst))} m "
                     f"{_ə(x * MM)} {_ə(self._y(self.y))} l")
        a.append(f"{_ə(self.sol * MM)} {_ə(self._y(üst))} m "
                 f"{_ə((self.sol + sum(e)) * MM)} {_ə(self._y(üst))} l S")
        self.səhifə.əmrlər.append(" ".join(a))

    # ── Şəkil ─────────────────────────────────────────────────────────
    def _şəkil_qeyd(self, mənbə: Any) -> tuple[str, int, int]:
        from .sekil import Şəkil, baytlardan
        if isinstance(mənbə, Şəkil):
            ş, b = mənbə, None
        else:
            if isinstance(mənbə, (bytes, bytearray)):
                b = bytes(mənbə)
            else:
                try:
                    b = Path(str(mənbə)).read_bytes()
                except FileNotFoundError:
                    raise AlqorXəta("FaylTapılmadıXətası",
                                    f'"{mənbə}" faylı tapılmadı', None,
                                    "ALQ-R009")
            ş = None
        ad = f"Im{len(self.şəkillər) + 1}"
        if b is not None and b[:3] == b"\xff\xd8\xff":
            m = _jpeg_ölçü(b)
            if m and m[2] in (1, 3):
                en, h, k = m
                self.şəkillər[ad] = {"növ": "jpeg", "en": en, "h": h,
                                     "data": b, "rəng": "/DeviceGray"
                                     if k == 1 else "/DeviceRGB"}
                return ad, en, h
        if ş is None:
            ş = baytlardan(b)
        rgb = bytearray(ş.en * ş.h * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = ş.p[0::4], ş.p[1::4], ş.p[2::4]
        alfa = bytes(ş.p[3::4])
        self.şəkillər[ad] = {"növ": "xam", "en": ş.en, "h": ş.h,
                             "data": bytes(rgb),
                             "alfa": None if alfa == b"\xff" * len(alfa)
                             else alfa}
        return ad, ş.en, ş.h

    def şəkil(self, mənbə: Any, en: Any = None, hündürlük: Any = None,
              x: Any = None, y: Any = None, düzləndir: str = "sol") -> None:
        ad, pe, ph = self._şəkil_qeyd(mənbə)
        if en is None and hündürlük is None:
            en = min(pe * 25.4 / 96, self.məzmun_eni)
        if en is None:
            en = float(hündürlük) * pe / ph
        if hündürlük is None:
            hündürlük = float(en) * ph / pe
        en, hündürlük = float(en), float(hündürlük)
        axın = x is None and y is None
        if axın:
            if en > self.məzmun_eni:
                hündürlük *= self.məzmun_eni / en
                en = self.məzmun_eni
            self._yer(hündürlük)
            y = self.y
            x = self.sol + {"sol": 0, "mərkəz": (self.məzmun_eni - en) / 2,
                            "sağ": self.məzmun_eni - en}.get(düzləndir, 0)
        x, y = float(x or 0), float(y or 0)
        self.səhifə.şəkillər.add(ad)
        self.səhifə.əmrlər.append(
            f"q {_ə(en * MM)} 0 0 {_ə(hündürlük * MM)} {_ə(x * MM)} "
            f"{_ə(self._y(y + hündürlük))} cm /{ad} Do Q")
        if axın:
            self.y += hündürlük + 3

    # ── Çıxış ─────────────────────────────────────────────────────────
    def səhifə_nömrələri(self, şablon: str = "[n] / [cəm]",
                         mövqe: str = "altMərkəz", ölçü: Any = 9) -> None:
        if mövqe not in ("altMərkəz", "altSağ", "altSol", "üstSağ",
                         "üstMərkəz"):
            raise _xəta("`mövqe`: altMərkəz, altSağ, altSol, üstSağ, "
                        "üstMərkəz", "ArqumentXətası")
        self.nömrə_şablonu = (str(şablon), mövqe, float(ölçü))

    def baytlar(self) -> bytes:
        if self.nömrə_şablonu:
            şablon, mövqe, ö = self.nömrə_şablonu
            ş = self.şriftlər["adi"]
            cəm = len(self.səhifələr)
            cari = self.səhifələr
            for i, p in enumerate(cari):
                m = şablon
                for a, v in (("n", i + 1), ("cəm", cəm)):
                    m = m.replace("{" + a + "}", str(v)).replace(
                        "[" + a + "]", str(v))
                w = ş.en(m, ö)
                y = p.h - self.alt / 2 if mövqe.startswith("alt") else \
                    self.üst / 2
                x = {"Mərkəz": (p.en - w) / 2, "Sağ": p.en - self.sağ - w,
                     "Sol": self.sol}[mövqe[3:]]
                hissələr = []
                for şr, parça in ş.parçalar(m):
                    p.şriftlər.add(şr.ad)
                    hissələr.append(f"/{şr.ad} {_ə(ö)} Tf "
                                    f"<{şr.kodla(parça)}> Tj")
                p.əmrlər.append(
                    f"BT 0.42 0.45 0.5 rg {_ə(x * MM)} "
                    f"{_ə((p.h - y) * MM)} Td {' '.join(hissələr)} ET")
        return _PDFYazan(self).yaz()

    def saxla(self, yol: Any) -> None:
        Path(str(yol)).write_bytes(self.baytlar())


def _jpeg_ölçü(b: bytes) -> tuple[int, int, int] | None:
    i = 2
    while i + 9 < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, en = struct.unpack(">HH", b[i + 5:i + 9])
            return en, h, b[i + 9]
        if m == 0xD8 or 0xD0 <= m <= 0xD7 or m == 0xFF:
            i += 1 if m == 0xFF else 2
            continue
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None


class _PDFYazan:
    def __init__(self, s: Sənəd):
        self.s = s
        self.obyektlər: list[bytes | None] = []

    def ayır(self) -> int:
        self.obyektlər.append(None)
        return len(self.obyektlər)

    def qoy(self, n: int, d: bytes | str) -> None:
        self.obyektlər[n - 1] = d.encode("latin-1") if isinstance(d, str) \
            else d

    def axın(self, n: int, lüğət: str, data: bytes, sıx: bool = True) -> None:
        if sıx:
            data = zlib.compress(data, 9)
            lüğət += " /Filter /FlateDecode"
        self.qoy(n, f"<< {lüğət} /Length {len(data)} >>\nstream\n"
                 .encode("latin-1") + data + b"\nendstream")

    def _şrift(self, ş: _Şrift) -> int:
        t = ş.t
        type0, cid, desk, fayl, uni = (self.ayır() for _ in range(5))
        alt = t.alt_dəst(set(ş.istifadə))
        self.axın(fayl, f"/Length1 {len(alt)}", alt)
        h = zlib.crc32((ş.ad + t.ps_ad).encode())
        prefiks = "".join(chr(65 + (h >> (i * 5)) % 26) for i in range(6))
        ad = f"{prefiks}+{t.ps_ad}"
        miq = 1000 / t.vahid
        bb = " ".join(str(int(v * miq)) for v in t.bbox)
        self.qoy(desk, f"<< /Type /FontDescriptor /FontName /{ad} "
                       f"/Flags {t.bayraqlar} /FontBBox [{bb}] "
                       f"/ItalicAngle {_ə(t.kursiv_bucaq)} "
                       f"/Ascent {int(t.yuxarı * miq)} "
                       f"/Descent {int(t.aşağı * miq)} "
                       f"/CapHeight {int(t.böyük_hərf * miq)} /StemV 80 "
                       f"/FontFile2 {fayl} 0 R >>")
        enlər = " ".join(f"{g} [{_ə(t.en(g))}]"
                         for g in sorted(ş.istifadə))
        self.qoy(cid, f"<< /Type /Font /Subtype /CIDFontType2 "
                      f"/BaseFont /{ad} /CIDSystemInfo << /Registry (Adobe) "
                      f"/Ordering (Identity) /Supplement 0 >> "
                      f"/FontDescriptor {desk} 0 R /CIDToGIDMap /Identity "
                      f"/DW 1000 /W [{enlər}] >>")
        xəritə = sorted(ş.istifadə.items())
        bloklar = []
        for i in range(0, len(xəritə), 100):
            parça = xəritə[i:i + 100]
            bloklar.append(f"{len(parça)} beginbfchar\n" + "\n".join(
                f"<{g:04X}> <{ch.encode('utf-16-be').hex().upper()}>"
                for g, ch in parça) + "\nendbfchar")
        cmap = ("/CIDInit /ProcSet findresource begin 12 dict begin "
                "begincmap /CIDSystemInfo << /Registry (Adobe) /Ordering "
                "(UCS) /Supplement 0 >> def /CMapName /Adobe-Identity-UCS "
                "def /CMapType 2 def 1 begincodespacerange <0000> <FFFF> "
                "endcodespacerange\n" + "\n".join(bloklar) +
                "\nendcmap CMapName currentdict /CMap defineresource pop "
                "end end")
        self.axın(uni, "", cmap.encode("latin-1"))
        self.qoy(type0, f"<< /Type /Font /Subtype /Type0 /BaseFont /{ad} "
                        f"/Encoding /Identity-H /DescendantFonts [{cid} 0 R] "
                        f"/ToUnicode {uni} 0 R >>")
        return type0

    def _şəkil(self, m: dict) -> int:
        n = self.ayır()
        if m["növ"] == "jpeg":
            self.axın(n, f"/Type /XObject /Subtype /Image /Width {m['en']} "
                         f"/Height {m['h']} /ColorSpace {m['rəng']} "
                         f"/BitsPerComponent 8 /Filter /DCTDecode",
                      m["data"], sıx=False)
            return n
        əlavə = ""
        if m.get("alfa"):
            a = self.ayır()
            self.axın(a, f"/Type /XObject /Subtype /Image /Width {m['en']} "
                         f"/Height {m['h']} /ColorSpace /DeviceGray "
                         f"/BitsPerComponent 8", m["alfa"])
            əlavə = f" /SMask {a} 0 R"
        self.axın(n, f"/Type /XObject /Subtype /Image /Width {m['en']} "
                     f"/Height {m['h']} /ColorSpace /DeviceRGB "
                     f"/BitsPerComponent 8{əlavə}", m["data"])
        return n

    def yaz(self) -> bytes:
        s = self.s
        kataloq, səhifələr_n = self.ayır(), self.ayır()
        səhifə_n = []
        for p in s.səhifələr:
            səhifə_n.append((self.ayır(), self.ayır(), p))
        # Məzmun axınları — şriftlərin istifadə olunan qlifləri burada
        # toplanır, ona görə şriftlərdən ƏVVƏL kodlanmalıdır (artıq kodlanıb)
        şriftlər = {}
        hamısı = list(s.şriftlər.values()) + list(s._ehtiyatlar or [])
        for ş in {id(x): x for x in hamısı}.values():
            if ş.istifadə:
                şriftlər[ş.ad] = self._şrift(ş)
        şəkillər = {ad: self._şəkil(m) for ad, m in s.şəkillər.items()}
        for pn, mn, p in səhifə_n:
            məzmun = "\n".join(p.əmrlər).encode("latin-1")
            self.axın(mn, "", məzmun)
            ş = " ".join(f"/{a} {şriftlər[a]} 0 R" for a in sorted(
                p.şriftlər) if a in şriftlər)
            ş_ = " ".join(f"/{a} {şəkillər[a]} 0 R" for a in sorted(
                p.şəkillər))
            self.qoy(pn, f"<< /Type /Page /Parent {səhifələr_n} 0 R "
                         f"/MediaBox [0 0 {_ə(p.en * MM)} {_ə(p.h * MM)}] "
                         f"/Resources << /Font << {ş} >> "
                         f"/XObject << {ş_} >> >> /Contents {mn} 0 R >>")
        self.qoy(səhifələr_n, f"<< /Type /Pages /Kids [" + " ".join(
            f"{pn} 0 R" for pn, _, _ in səhifə_n) +
            f"] /Count {len(səhifə_n)} >>")
        self.qoy(kataloq, f"<< /Type /Catalog /Pages {səhifələr_n} 0 R "
                          f"/Lang (az) >>")
        info = self.ayır()
        tarix = time.strftime("D:%Y%m%d%H%M%S")
        sahələr = [f"/Producer {_pdf_mətn('Alqor pdf')}",
                   f"/CreationDate ({tarix})"]
        for a, v in s.info.items():
            if v:
                sahələr.append(f"/{a} {_pdf_mətn(mətnə(v))}")
        self.qoy(info, "<< " + " ".join(sahələr) + " >>")

        çıxış = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
        ofslar = []
        for i, d in enumerate(self.obyektlər):
            ofslar.append(len(çıxış))
            çıxış += f"{i + 1} 0 obj\n".encode() + d + b"\nendobj\n"
        xref = len(çıxış)
        çıxış += f"xref\n0 {len(self.obyektlər) + 1}\n".encode()
        çıxış += b"0000000000 65535 f \n"
        for o in ofslar:
            çıxış += f"{o:010d} 00000 n \n".encode()
        idx = zlib.crc32(bytes(çıxış)).to_bytes(4, "big").hex() * 4
        çıxış += (f"trailer\n<< /Size {len(self.obyektlər) + 1} "
                  f"/Root {kataloq} 0 R /Info {info} 0 R "
                  f"/ID [<{idx}> <{idx}>] >>\nstartxref\n{xref}\n%%EOF\n"
                  ).encode()
        return bytes(çıxış)


Sənəd.ALQOR_METODLARI = {
    "başlıq": lambda i, s, m, səviyyə=1, rəng="#111827":
        s.başlıq(m, səviyyə, rəng),
    "abzas": lambda i, s, m, **k: s.abzas(m, **k),
    "siyahı": lambda i, s, e, nömrəli=False, ölçü=None:
        s.siyahı(e, nömrəli, ölçü),
    "cədvəl": lambda i, s, c, **k: s.cədvəl(c, **k),
    "şəkil": lambda i, s, m, **k: s.şəkil(m, **k),
    "mətn": lambda i, s, x, y, m, **k: s.mətn(x, y, m, **k),
    "xətt": lambda i, s, x1, y1, x2, y2, rəng="boz", qalınlıq=0.3:
        s.xətt(x1, y1, x2, y2, rəng, qalınlıq),
    "düzbucaqlı": lambda i, s, x, y, en, h, **k:
        s.düzbucaqlı(x, y, en, h, **k),
    "dairə": lambda i, s, x, y, r, **k: s.dairə(x, y, r, **k),
    "boşluq": lambda i, s, mm=5: s.boşluq(mm),
    "ayırıcı": lambda i, s, rəng="#d1d5db", qalınlıq=0.3:
        s.ayırıcı(rəng, qalınlıq),
    "yeniSəhifə": lambda i, s: s.yeni_səhifə(),
    "səhifəNömrələri": lambda i, s, şablon="[n] / [cəm]",
    mövqe="altMərkəz", ölçü=9: s.səhifə_nömrələri(şablon, mövqe, ölçü),
    "səhifəSayı": lambda i, s: len(s.səhifələr),
    "mövqe": lambda i, s: s.y,
    "en": lambda i, s: s.en,
    "hündürlük": lambda i, s: s.h,
    "mətnEni": lambda i, s, m, ölçü=None, qalın=False:
        s._ş(qalın, False).en(mətnə(m), float(ölçü or s.ölçü)),
    "baytlar": lambda i, s: s.baytlar(),
    "saxla": lambda i, s, yol: s.saxla(yol),
}


def qur(icraçı) -> dict[str, Any]:
    return {
        "sənəd": Daxili("sənəd", lambda **k: Sənəd(**k), 0, 0),
        "ölçülər": Daxili("ölçülər", lambda: {k: list(v) for k, v in
                                               ÖLÇÜLƏR.items()}),
        "sistemŞrifti": Daxili("sistemŞrifti", lambda: (
            (_ttf.sistem_şrifti() or [None])[0])),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    return {
        "sənəd": Fsərbəst(T.Sadə("pdfSənədi")),
        "ölçülər": F(qaytarır=T.Lüğət(T.MƏTN, T.Siyahı(T.ONLUQ))),
        "sistemŞrifti": F(qaytarır=T.ixtiyari(T.MƏTN)),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    h, o = T.HEÇ, T.ONLUQ
    return {"pdfSənədi": {
        **{ad: Fsərbəst(h) for ad in (
            "başlıq", "abzas", "siyahı", "cədvəl", "şəkil", "mətn", "xətt",
            "düzbucaqlı", "dairə", "boşluq", "ayırıcı", "yeniSəhifə",
            "səhifəNömrələri", "saxla")},
        "səhifəSayı": F(qaytarır=T.TAM),
        "mövqe": F(qaytarır=o), "en": F(qaytarır=o),
        "hündürlük": F(qaytarır=o),
        "mətnEni": Fsərbəst(o),
        "baytlar": F(qaytarır=T.BAYT),
    }}

