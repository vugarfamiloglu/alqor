"""
`qrafik` — diaqramlar: SVG faylı, HTML və ya veb səhifəsinə yerləşdirmək
üçün (§ 10.17). Xarici kitabxana və brauzer lazım deyil.

    gətir qrafik

    dəyişən q = qrafik.sütun(
        etiketlər: ["Yan", "Fev", "Mar", "Apr"],
        seriyalar: [
            {"ad": "Satış", "dəyərlər": [12, 19, 7, 15]},
            {"ad": "Plan", "dəyərlər": [10, 15, 10, 14]},
        ],
        başlıq: "Aylıq satış", yBaşlıq: "min ₼")
    q.saxla("satış.svg")                 // və ya .html
    yaz(q.svg())                         // veb şablonuna qoymaq üçün

    qrafik.xətt(etiketlər: …, seriyalar: …, hamar: doğru, nöqtələr: doğru)
    qrafik.sahə(…, yığılmış: doğru)
    qrafik.zolaq(…)                      // üfüqi sütunlar
    qrafik.dairə(etiketlər: ["A", "B"], dəyərlər: [30, 70])
    qrafik.halqa(etiketlər: …, dəyərlər: …, mərkəz: "100%")
    qrafik.nöqtə(seriyalar: [{"ad": "Ölçmə", "nöqtələr": [[1, 2], [3, 5]]}])
    qrafik.histogram([1.2, 3.4, …], qutular: 10)

Ümumi seçimlər: `başlıq`, `xBaşlıq`, `yBaşlıq`, `en` (640),
`hündürlük` (400), `rənglər`, `tema` ("açıq"/"qaranlıq"), `əfsanə`,
`dəyərləriGöstər`, `yığılmış`, `min`, `maks`, `dil` (ədəd formatı, "az").
"""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili

PALİTRA = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed",
           "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569"]
TEMALAR = {
    "açıq": {"fon": "#ffffff", "mətn": "#111827", "sönük": "#6b7280",
             "tor": "#e5e7eb", "ox": "#9ca3af"},
    "qaranlıq": {"fon": "#111827", "mətn": "#f3f4f6", "sönük": "#9ca3af",
                 "tor": "#374151", "ox": "#6b7280"},
}


def _xəta(mesaj: str, tip: str = "QrafikXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _ədəd_mi(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and \
        math.isfinite(x)


def _q(x: Any) -> str:
    return html.escape(str(x), quote=True)


def _f(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def gözəl_addım(aralıq: float, say: int = 5) -> float:
    if aralıq <= 0:
        return 1.0
    xam = aralıq / say
    q = 10 ** math.floor(math.log10(xam))
    for m in (1, 2, 2.5, 5, 10):
        if xam <= m * q:
            return m * q
    return 10 * q


def _ox_bölgüləri(mn: float, mx: float) -> list[float]:
    if mn == mx:
        mn, mx = (mn - 1, mx + 1) if mn else (0, 1)
    a = gözəl_addım(mx - mn)
    b = math.floor(mn / a) * a
    s = math.ceil(mx / a) * a
    n, x = [], b
    while x <= s + a / 2:
        n.append(round(x, 10))
        x += a
    return n


def _ədəd_mətni(v: float, dil: str) -> str:
    from .lokalizasiya import ədəd
    if abs(v - round(v)) < 1e-9:
        v = int(round(v))
    elif abs(v) < 100:
        v = round(v, 2)
    else:
        v = round(v, 1)
    return ədəd(v, dil)


class Qrafik:
    ALQOR_TİP_ADI = "qrafik"

    def __init__(self, növ: str, s: dict):
        self.növ = növ
        self.s = s
        self.en = int(s.get("en", 640))
        self.h = int(s.get("hündürlük", 400))
        if not (50 <= self.en <= 10000 and 50 <= self.h <= 10000):
            raise _xəta("`en` və `hündürlük` 50–10000 arasında olmalıdır")
        self.t = TEMALAR.get(s.get("tema", "açıq"))
        if self.t is None:
            raise _xəta('`tema` "açıq" və ya "qaranlıq" olmalıdır')
        self.rənglər = list(s.get("rənglər") or PALİTRA)
        self.dil = str(s.get("dil", "az"))
        self.şrift = str(s.get("şrift",
                               "system-ui, -apple-system, Segoe UI, "
                               "Roboto, sans-serif"))
        self._yoxla()

    def __repr__(self) -> str:
        return f"<qrafik {self.növ}>"

    # ── Giriş yoxlaması ───────────────────────────────────────────────
    def _yoxla(self) -> None:
        s = self.s
        if self.növ in ("dairə", "halqa"):
            d = s.get("dəyərlər")
            if not isinstance(d, list) or not d or not all(
                    _ədəd_mi(x) and x >= 0 for x in d):
                raise _xəta("`dəyərlər` mənfi olmayan ədədlər siyahısı "
                            "olmalıdır")
            if sum(d) <= 0:
                raise _xəta("dəyərlərin cəmi sıfırdan böyük olmalıdır")
            e = s.get("etiketlər") or [str(i + 1) for i in range(len(d))]
            if len(e) != len(d):
                raise _xəta("`etiketlər` və `dəyərlər` eyni uzunluqda "
                            "olmalıdır")
            s["etiketlər"] = e
            return
        ser = s.get("seriyalar")
        if not isinstance(ser, list) or not ser:
            raise _xəta("`seriyalar` boş olmayan siyahı olmalıdır: "
                        '[{"ad": …, "dəyərlər": […]}]')
        for i, x in enumerate(ser):
            if not isinstance(x, dict):
                raise _xəta("hər seriya lüğət olmalıdır", "TipXətası")
            if self.növ == "nöqtə":
                n = x.get("nöqtələr")
                if not isinstance(n, list) or not all(
                        isinstance(p, (list, tuple)) and len(p) == 2 and
                        _ədəd_mi(p[0]) and _ədəd_mi(p[1]) for p in n):
                    raise _xəta(f"{i + 1}-ci seriya: `nöqtələr` [[x, y], …] "
                                "olmalıdır")
            else:
                d = x.get("dəyərlər")
                if not isinstance(d, list) or not all(
                        v is None or _ədəd_mi(v) for v in d):
                    raise _xəta(f"{i + 1}-ci seriya: `dəyərlər` ədəd "
                                "siyahısı olmalıdır (boş = `boş`)")
        if self.növ != "nöqtə":
            uz = max(len(x["dəyərlər"]) for x in ser)
            e = s.get("etiketlər") or [str(i + 1) for i in range(uz)]
            if len(e) < uz:
                raise _xəta("`etiketlər` dəyərlərdən azdır")
            s["etiketlər"] = [str(x) for x in e]

    def rəng(self, i: int, seriya: dict | None = None) -> str:
        if seriya and seriya.get("rəng"):
            return str(seriya["rəng"])
        return self.rənglər[i % len(self.rənglər)]

    # ── SVG ───────────────────────────────────────────────────────────
    def svg(self) -> str:
        t = self.t
        n = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {self.en} {self.h}" width="{self.en}" '
             f'height="{self.h}" font-family="{_q(self.şrift)}" '
             f'font-size="12" role="img" '
             f'aria-label="{_q(self.s.get("başlıq") or self.növ)}">',
             f'<rect width="100%" height="100%" fill="{t["fon"]}"/>']
        üst = 16
        if self.s.get("başlıq"):
            n.append(f'<text x="{self.en / 2}" y="28" text-anchor="middle" '
                     f'font-size="16" font-weight="600" fill="{t["mətn"]}">'
                     f'{_q(self.s["başlıq"])}</text>')
            üst = 44
        əfsanə = self._əfsanə_elementləri()
        alt_əfsanə = 0
        if əfsanə and self.s.get("əfsanə", True):
            alt_əfsanə = 28
            n.append(self._əfsanə(əfsanə, self.h - 14))
        sahə = (üst, self.h - 8 - alt_əfsanə)
        if self.növ in ("dairə", "halqa"):
            n.append(self._dairə(sahə))
        else:
            n.append(self._oxlu(sahə))
        n.append("</svg>")
        return "\n".join(n)

    def _əfsanə_elementləri(self) -> list[tuple[str, str]]:
        if self.növ in ("dairə", "halqa"):
            return [(e, self.rəng(i))
                    for i, e in enumerate(self.s["etiketlər"])]
        ser = self.s["seriyalar"]
        if len(ser) == 1 and self.növ != "nöqtə":
            return []
        return [(str(x.get("ad", f"Seriya {i + 1}")), self.rəng(i, x))
                for i, x in enumerate(ser)]

    def _əfsanə(self, el: list, y: float) -> str:
        enlər = [len(a) * 7 + 30 for a, _ in el]
        x = (self.en - sum(enlər)) / 2
        n = ['<g class="əfsanə">']
        for (ad, r), e in zip(el, enlər):
            n.append(f'<rect x="{_f(x)}" y="{_f(y - 9)}" width="12" '
                     f'height="12" rx="2" fill="{_q(r)}"/>'
                     f'<text x="{_f(x + 17)}" y="{_f(y + 1)}" '
                     f'fill="{self.t["mətn"]}">{_q(ad)}</text>')
            x += e
        n.append("</g>")
        return "".join(n)

    def _dairə(self, sahə: tuple) -> str:
        d = self.s["dəyərlər"]
        etiketlər = self.s["etiketlər"]
        cəm = sum(d)
        mx, my = self.en / 2, (sahə[0] + sahə[1]) / 2
        R = min(self.en, sahə[1] - sahə[0]) / 2 - 16
        r = R * 0.6 if self.növ == "halqa" else 0
        n = []
        bucaq = -math.pi / 2
        for i, v in enumerate(d):
            if v == 0:
                continue
            a = v / cəm * 2 * math.pi
            son = bucaq + a
            if a >= 2 * math.pi - 1e-9:
                yol = (f'<circle cx="{_f(mx)}" cy="{_f(my)}" r="{_f(R)}" '
                       f'fill="{self.rəng(i)}"/>')
                if r:
                    yol += (f'<circle cx="{_f(mx)}" cy="{_f(my)}" '
                            f'r="{_f(r)}" fill="{self.t["fon"]}"/>')
                n.append(yol)
            else:
                böyük = 1 if a > math.pi else 0
                x1, y1 = mx + R * math.cos(bucaq), my + R * math.sin(bucaq)
                x2, y2 = mx + R * math.cos(son), my + R * math.sin(son)
                if r:
                    x3, y3 = mx + r * math.cos(son), my + r * math.sin(son)
                    x4, y4 = mx + r * math.cos(bucaq), my + r * math.sin(
                        bucaq)
                    p = (f"M{_f(x1)},{_f(y1)} A{_f(R)},{_f(R)} 0 {böyük} 1 "
                         f"{_f(x2)},{_f(y2)} L{_f(x3)},{_f(y3)} "
                         f"A{_f(r)},{_f(r)} 0 {böyük} 0 {_f(x4)},{_f(y4)} Z")
                else:
                    p = (f"M{_f(mx)},{_f(my)} L{_f(x1)},{_f(y1)} "
                         f"A{_f(R)},{_f(R)} 0 {böyük} 1 {_f(x2)},{_f(y2)} Z")
                n.append(f'<path d="{p}" fill="{self.rəng(i)}" '
                         f'stroke="{self.t["fon"]}" stroke-width="2">'
                         f'<title>{_q(etiketlər[i])}: '
                         f'{_ədəd_mətni(v, self.dil)}</title></path>')
            if self.s.get("dəyərləriGöstər", True) and a > 0.25:
                orta = bucaq + a / 2
                rr = (R + r) / 2 if r else R * 0.65
                faiz = v / cəm * 100
                n.append(f'<text x="{_f(mx + rr * math.cos(orta))}" '
                         f'y="{_f(my + rr * math.sin(orta) + 4)}" '
                         f'text-anchor="middle" fill="#ffffff" '
                         f'font-weight="600">{_ədəd_mətni(faiz, self.dil)}%'
                         f'</text>')
            bucaq = son
        if r and self.s.get("mərkəz"):
            n.append(f'<text x="{_f(mx)}" y="{_f(my + 7)}" '
                     f'text-anchor="middle" font-size="20" font-weight="700" '
                     f'fill="{self.t["mətn"]}">{_q(self.s["mərkəz"])}</text>')
        return "\n".join(n)

    def _oxlu(self, sahə: tuple) -> str:
        t = self.t
        s = self.s
        üfüqi = self.növ == "zolaq"
        yığılmış = bool(s.get("yığılmış"))
        ser = s["seriyalar"]
        if self.növ == "nöqtə":
            xs = [p[0] for x in ser for p in x["nöqtələr"]]
            ys = [p[1] for x in ser for p in x["nöqtələr"]]
            xa, xü = min(xs, default=0), max(xs, default=1)
            pay = (xü - xa) * 0.05 or 0.5
            xb = _ox_bölgüləri(xa - pay, xü + pay)
            ya, yü = min(ys, default=0), max(ys, default=1)
            pay = (yü - ya) * 0.05 or 0.5
            ys = [ya - pay, yü + pay]
        else:
            if yığılmış:
                uz = len(s["etiketlər"])
                müs = [sum(max(0, x["dəyərlər"][i] or 0) for x in ser
                           if i < len(x["dəyərlər"])) for i in range(uz)]
                mən = [sum(min(0, x["dəyərlər"][i] or 0) for x in ser
                           if i < len(x["dəyərlər"])) for i in range(uz)]
                ys = müs + mən
            else:
                ys = [v for x in ser for v in x["dəyərlər"] if v is not None]
            if self.növ in ("sütun", "zolaq", "sahə", "histogram"):
                ys = ys + [0]
        mn = s.get("min", min(ys, default=0))
        mx = s.get("maks", max(ys, default=1))
        yb = _ox_bölgüləri(mn, mx)
        y0, y1 = yb[0], yb[-1]

        etiket_en = max(len(_ədəd_mətni(v, self.dil)) for v in yb) * 7 + 12
        sol = 16 + etiket_en + (18 if s.get("yBaşlıq") else 0)
        sağ = self.en - 20
        üst, alt = sahə[0] + 6, sahə[1] - 26 - (18 if s.get("xBaşlıq")
                                                 else 0)
        if üfüqi:
            uzun = max((len(e) for e in s["etiketlər"]), default=1)
            sol = 16 + min(uzun * 7, self.en // 3) + 8
        n = []

        def yv(v):            # dəyər → piksel (dəyər oxu)
            if üfüqi:
                return sol + (v - y0) / (y1 - y0) * (sağ - sol)
            return alt - (v - y0) / (y1 - y0) * (alt - üst)

        # tor və dəyər oxu bölgüləri
        for v in yb:
            p = yv(v)
            if üfüqi:
                n.append(f'<line x1="{_f(p)}" y1="{üst}" x2="{_f(p)}" '
                         f'y2="{alt}" stroke="{t["tor"]}"/>'
                         f'<text x="{_f(p)}" y="{alt + 16}" '
                         f'text-anchor="middle" fill="{t["sönük"]}">'
                         f'{_ədəd_mətni(v, self.dil)}</text>')
            else:
                n.append(f'<line x1="{sol}" y1="{_f(p)}" x2="{sağ}" '
                         f'y2="{_f(p)}" stroke="{t["tor"]}"/>'
                         f'<text x="{sol - 8}" y="{_f(p + 4)}" '
                         f'text-anchor="end" fill="{t["sönük"]}">'
                         f'{_ədəd_mətni(v, self.dil)}</text>')
        if s.get("yBaşlıq"):
            n.append(f'<text transform="translate(16,{_f((üst + alt) / 2)}) '
                     f'rotate(-90)" text-anchor="middle" '
                     f'fill="{t["sönük"]}">{_q(s["yBaşlıq"])}</text>')
        if s.get("xBaşlıq"):
            n.append(f'<text x="{_f((sol + sağ) / 2)}" y="{sahə[1] - 4}" '
                     f'text-anchor="middle" fill="{t["sönük"]}">'
                     f'{_q(s["xBaşlıq"])}</text>')

        if self.növ == "nöqtə":
            x0, x1 = xb[0], xb[-1]

            def xv(v):
                return sol + (v - x0) / (x1 - x0) * (sağ - sol)
            for v in xb:
                n.append(f'<text x="{_f(xv(v))}" y="{alt + 16}" '
                         f'text-anchor="middle" fill="{t["sönük"]}">'
                         f'{_ədəd_mətni(v, self.dil)}</text>')
            for i, x in enumerate(ser):
                r = self.rəng(i, x)
                for px, py in x["nöqtələr"]:
                    n.append(f'<circle cx="{_f(xv(px))}" cy="{_f(yv(py))}" '
                             f'r="{_f(float(x.get("ölçü", 4)))}" fill="{r}" '
                             f'fill-opacity="0.8"><title>'
                             f'({_ədəd_mətni(px, self.dil)}, '
                             f'{_ədəd_mətni(py, self.dil)})</title>'
                             f'</circle>')
            n.append(self._oxlar(sol, sağ, üst, alt, üfüqi, yv))
            return "\n".join(n)

        etiketlər = s["etiketlər"]
        k = len(etiketlər)
        uzunluq = (alt - üst) if üfüqi else (sağ - sol)
        addım = uzunluq / max(1, k)

        def kat(i):           # kateqoriyanın mərkəzi (piksel)
            if üfüqi:
                return üst + addım * (i + 0.5)
            if self.növ in ("xətt", "sahə") and k > 1:
                return sol + (sağ - sol) * i / (k - 1)
            return sol + addım * (i + 0.5)

        # kateqoriya etiketləri (çox olanda seyrəlt)
        hər = max(1, math.ceil(k / max(1, uzunluq / (
            20 if üfüqi else max(40, max(len(e) for e in etiketlər) * 7)))))
        for i, e in enumerate(etiketlər):
            if i % hər:
                continue
            if üfüqi:
                n.append(f'<text x="{sol - 8}" y="{_f(kat(i) + 4)}" '
                         f'text-anchor="end" fill="{t["mətn"]}">{_q(e)}'
                         f'</text>')
            else:
                n.append(f'<text x="{_f(kat(i))}" y="{alt + 16}" '
                         f'text-anchor="middle" fill="{t["mətn"]}">{_q(e)}'
                         f'</text>')

        sıfır = yv(max(y0, min(0, y1))) if y0 <= 0 <= y1 else yv(y0)
        if self.növ in ("sütun", "zolaq", "histogram"):
            m = len(ser)
            qrup = addım * (0.95 if self.növ == "histogram" else 0.75)
            bir = qrup if yığılmış or m == 1 else qrup / m
            yığın_m = [0.0] * k
            yığın_n = [0.0] * k
            for j, x in enumerate(ser):
                r = self.rəng(j, x)
                for i, v in enumerate(x["dəyərlər"][:k]):
                    if v is None:
                        continue
                    if yığılmış:
                        baza = yığın_m[i] if v >= 0 else yığın_n[i]
                        a, b = yv(baza), yv(baza + v)
                        if v >= 0:
                            yığın_m[i] += v
                        else:
                            yığın_n[i] += v
                        mövqe = kat(i) - bir / 2
                    else:
                        a, b = sıfır, yv(v)
                        mövqe = kat(i) - qrup / 2 + j * bir
                    başlıq = (f'<title>{_q(x.get("ad", ""))} {_q(etiketlər[i])}'
                              f': {_ədəd_mətni(v, self.dil)}</title>')
                    if üfüqi:
                        n.append(f'<rect x="{_f(min(a, b))}" y="{_f(mövqe)}" '
                                 f'width="{_f(abs(b - a))}" '
                                 f'height="{_f(bir - 1)}" fill="{r}" rx="2">'
                                 f'{başlıq}</rect>')
                    else:
                        n.append(f'<rect x="{_f(mövqe)}" y="{_f(min(a, b))}" '
                                 f'width="{_f(bir - 1)}" '
                                 f'height="{_f(abs(b - a))}" fill="{r}" '
                                 f'rx="2">{başlıq}</rect>')
                    if s.get("dəyərləriGöstər") and not yığılmış:
                        if üfüqi:
                            n.append(f'<text x="{_f(max(a, b) + 4)}" '
                                     f'y="{_f(mövqe + bir / 2 + 4)}" '
                                     f'fill="{t["mətn"]}">'
                                     f'{_ədəd_mətni(v, self.dil)}</text>')
                        else:
                            n.append(f'<text x="{_f(mövqe + bir / 2)}" '
                                     f'y="{_f(min(a, b) - 4)}" '
                                     f'text-anchor="middle" '
                                     f'fill="{t["mətn"]}">'
                                     f'{_ədəd_mətni(v, self.dil)}</text>')
        else:                                           # xətt / sahə
            baza = [0.0] * k
            for j, x in enumerate(ser):
                r = self.rəng(j, x)
                nöqtələr = []
                alt_n = []
                for i, v in enumerate(x["dəyərlər"][:k]):
                    if v is None:
                        nöqtələr.append(None)
                        continue
                    əsas = baza[i] if yığılmış else 0
                    nöqtələr.append((kat(i), yv(əsas + v)))
                    alt_n.append((kat(i), yv(əsas)))
                    if yığılmış:
                        baza[i] += v
                parçalar = [[]]
                for p in nöqtələr:
                    if p is None:
                        parçalar.append([])
                    else:
                        parçalar[-1].append(p)
                for parça in parçalar:
                    if not parça:
                        continue
                    d = self._yol(parça, bool(s.get("hamar")))
                    if self.növ == "sahə":
                        geri = [q for q in alt_n if parça[0][0] <= q[0] <=
                                parça[-1][0]][::-1]
                        d2 = d + " " + " ".join(
                            f"L{_f(a)},{_f(b)}" for a, b in geri) + " Z"
                        n.append(f'<path d="{d2}" fill="{r}" '
                                 f'fill-opacity="0.25" stroke="none"/>')
                    n.append(f'<path d="{d}" fill="none" stroke="{r}" '
                             f'stroke-width="{_f(float(x.get("qalınlıq", 2.5)))}" '
                             f'stroke-linejoin="round" stroke-linecap="round"/>')
                if s.get("nöqtələr", self.növ == "xətt" and k <= 24):
                    for i, p in enumerate(nöqtələr):
                        if p is None:
                            continue
                        v = x["dəyərlər"][i]
                        n.append(f'<circle cx="{_f(p[0])}" cy="{_f(p[1])}" '
                                 f'r="3.5" fill="{t["fon"]}" stroke="{r}" '
                                 f'stroke-width="2"><title>'
                                 f'{_q(x.get("ad", ""))} {_q(etiketlər[i])}: '
                                 f'{_ədəd_mətni(v, self.dil)}</title>'
                                 f'</circle>')
        n.append(self._oxlar(sol, sağ, üst, alt, üfüqi, yv))
        return "\n".join(n)

    def _oxlar(self, sol, sağ, üst, alt, üfüqi, yv) -> str:
        c = self.t["ox"]
        return (f'<line x1="{sol}" y1="{alt}" x2="{sağ}" y2="{alt}" '
                f'stroke="{c}"/><line x1="{sol}" y1="{üst}" x2="{sol}" '
                f'y2="{alt}" stroke="{c}"/>')

    @staticmethod
    def _yol(p: list[tuple[float, float]], hamar: bool) -> str:
        if not hamar or len(p) < 3:
            return "M" + " L".join(f"{_f(x)},{_f(y)}" for x, y in p)
        # Katmull-Rom → kub Bezye
        d = [f"M{_f(p[0][0])},{_f(p[0][1])}"]
        for i in range(len(p) - 1):
            p0 = p[i - 1] if i else p[i]
            p1, p2 = p[i], p[i + 1]
            p3 = p[i + 2] if i + 2 < len(p) else p2
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d.append(f"C{_f(c1[0])},{_f(c1[1])} {_f(c2[0])},{_f(c2[1])} "
                     f"{_f(p2[0])},{_f(p2[1])}")
        return " ".join(d)

    def html(self) -> str:
        başlıq = _q(self.s.get("başlıq") or "Qrafik")
        return (f'<!doctype html><html lang="az"><head><meta charset="utf-8">'
                f'<title>{başlıq}</title><style>body{{margin:0;'
                f'background:{self.t["fon"]};display:grid;place-items:center;'
                f'min-height:100vh}}svg{{max-width:100%;height:auto}}</style>'
                f'</head><body>{self.svg()}</body></html>')

    def saxla(self, yol: Any) -> None:
        p = Path(str(yol))
        if p.suffix.lower() == ".svg":
            p.write_text(self.svg(), encoding="utf-8")
        elif p.suffix.lower() in (".html", ".htm"):
            p.write_text(self.html(), encoding="utf-8")
        else:
            raise _xəta(f'"{yol}": yalnız .svg və .html dəstəklənir')


Qrafik.ALQOR_METODLARI = {
    "svg": lambda i, q: q.svg(),
    "html": lambda i, q: q.html(),
    "saxla": lambda i, q, yol: q.saxla(yol),
    "dataURI": lambda i, q: "data:image/svg+xml;base64," + __import__(
        "base64").b64encode(q.svg().encode("utf-8")).decode("ascii"),
    "növ": lambda i, q: q.növ,
}


def histogram(dəyərlər: Any, qutular: Any = 10, **s: Any) -> Qrafik:
    if not isinstance(dəyərlər, list) or not dəyərlər or not all(
            _ədəd_mi(v) for v in dəyərlər):
        raise _xəta("`histogram` ədəd siyahısı gözləyir")
    n = int(qutular)
    if not 1 <= n <= 500:
        raise _xəta("`qutular` 1–500 arasında olmalıdır")
    mn, mx = min(dəyərlər), max(dəyərlər)
    en = (mx - mn) / n or 1
    say = [0] * n
    for v in dəyərlər:
        say[min(n - 1, int((v - mn) / en))] += 1
    etiketlər = [_ədəd_mətni(mn + en * (i + 0.5), str(s.get("dil", "az")))
                 for i in range(n)]
    s.setdefault("yBaşlıq", "say")
    return Qrafik("histogram", {**s, "etiketlər": etiketlər,
                                "seriyalar": [{"ad": s.get("ad", "say"),
                                               "dəyərlər": say}]})


def qur(icraçı) -> dict[str, Any]:
    def növ(ad):
        def f(**s):
            if "dəyərlər" in s and ad not in ("dairə", "halqa") and \
                    "seriyalar" not in s:
                s["seriyalar"] = [{"ad": s.get("ad", ""),
                                   "dəyərlər": s.pop("dəyərlər")}]
            return Qrafik(ad, s)
        return Daxili(ad, f, 0, 0)

    n = {ad: növ(ad) for ad in ("sütun", "zolaq", "xətt", "sahə", "dairə",
                                "halqa", "nöqtə")}
    n["histogram"] = Daxili("histogram", histogram, 1, 2)
    n["yarat"] = Daxili("yarat", lambda növ_, **s: Qrafik(
        _növ_yoxla(növ_), s), 1, 1)
    n["palitra"] = Daxili("palitra", lambda: list(PALİTRA))
    return n


def _növ_yoxla(n: Any) -> str:
    if n not in ("sütun", "zolaq", "xətt", "sahə", "dairə", "halqa",
                 "nöqtə"):
        raise _xəta(f"naməlum qrafik növü `{n}`", "ArqumentXətası")
    return n


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    Q = T.Sadə("qrafik")
    n = {ad: Fsərbəst(Q) for ad in ("sütun", "zolaq", "xətt", "sahə",
                                     "dairə", "halqa", "nöqtə", "histogram",
                                     "yarat")}
    n["palitra"] = F(qaytarır=T.Siyahı(T.MƏTN))
    return n


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m = T.MƏTN
    return {"qrafik": {
        "svg": F(qaytarır=m), "html": F(qaytarır=m),
        "saxla": F(m, qaytarır=T.HEÇ), "dataURI": F(qaytarır=m),
        "növ": F(qaytarır=m),
    }}

