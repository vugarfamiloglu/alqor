"""
`pul` — dəqiq pul hesablamaları və valyuta (§ 10.17).

`onluq` (ikilik kəsr) pul üçün yararsızdır: `0.1 + 0.2 != 0.3`. `pul`
dəyəri onluq əsaslı DƏQİQ ədəddir və öz valyutasını daşıyır; hər
əməliyyatdan sonra valyutanın kəsr rəqəmlərinə (AZN → 2, JPY → 0,
KWD → 3) yuvarlaqlaşdırılır.

    gətir pul

    dəyişən qiymət = pul.yarat("19.99", "AZN")
    dəyişən cəm = qiymət * 3 + pul.yarat(5, "AZN")       // 64.97 AZN
    yaz(cəm.formatla())                                   // "64,97 ₼"
    yaz(cəm.faiz(18))                                     // ƏDV: 11.69 AZN
    yaz(pul.yarat(100, "AZN").böl(3))                     // [33.34, 33.33, 33.33]
    yaz(pul.yarat(10, "USD").çevir("AZN", 1.7))           // 17.00 AZN
    yaz(qiymət > pul.yarat(10, "AZN"))                    // doğru

Fərqli valyutaları toplamaq / müqayisə etmək `ValyutaXətası` verir —
əvvəlcə `çevir` ilə eyni valyutaya keçirin.

Yuvarlaqlaşdırma üsulları: `"riyazi"` (standart, 0.5 yuxarı),
`"bankir"` (0.5 cüt rəqəmə), `"yuxarı"`, `"aşağı"`, `"sıfıra"`.
"""

from __future__ import annotations

import decimal
import re
from decimal import Decimal
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı

# kod: (simvol, kəsr rəqəmləri, ad)
VALYUTALAR: dict[str, tuple[str, int, str]] = {
    "AZN": ("₼", 2, "Azərbaycan manatı"),
    "USD": ("$", 2, "ABŞ dolları"),
    "EUR": ("€", 2, "Avro"),
    "GBP": ("£", 2, "Britaniya funt sterlinqi"),
    "TRY": ("₺", 2, "Türkiyə lirəsi"),
    "RUB": ("₽", 2, "Rusiya rublu"),
    "GEL": ("₾", 2, "Gürcüstan larisi"),
    "KZT": ("₸", 2, "Qazaxıstan tengesi"),
    "UZS": ("soʻm", 2, "Özbəkistan somu"),
    "UAH": ("₴", 2, "Ukrayna qrivnası"),
    "CHF": ("CHF", 2, "İsveçrə frankı"),
    "CNY": ("¥", 2, "Çin yuanı"),
    "JPY": ("¥", 0, "Yapon yeni"),
    "KRW": ("₩", 0, "Cənubi Koreya vonu"),
    "INR": ("₹", 2, "Hindistan rupisi"),
    "AED": ("AED", 2, "BƏƏ dirhəmi"),
    "SAR": ("SAR", 2, "Səudiyyə rialı"),
    "IRR": ("IRR", 0, "İran rialı"),
    "KWD": ("KD", 3, "Küveyt dinarı"),
    "BHD": ("BD", 3, "Bəhreyn dinarı"),
    "CAD": ("C$", 2, "Kanada dolları"),
    "AUD": ("A$", 2, "Avstraliya dolları"),
    "SEK": ("kr", 2, "İsveç kronu"),
    "NOK": ("kr", 2, "Norveç kronu"),
    "PLN": ("zł", 2, "Polşa zlotısı"),
    "BTC": ("₿", 8, "Bitkoin"),
}

ÜSULLAR = {
    "riyazi": decimal.ROUND_HALF_UP,
    "bankir": decimal.ROUND_HALF_EVEN,
    "yuxarı": decimal.ROUND_CEILING,
    "aşağı": decimal.ROUND_FLOOR,
    "sıfıra": decimal.ROUND_DOWN,
    "sıfırdan": decimal.ROUND_UP,
}

_KONTEKST = decimal.Context(prec=60, rounding=decimal.ROUND_HALF_UP,
                            traps=[decimal.InvalidOperation,
                                   decimal.DivisionByZero])


def _xəta(mesaj: str, tip: str = "PulXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _valyuta(kod: Any) -> str:
    k = str(kod).strip().upper()
    if k not in VALYUTALAR:
        raise _xəta(f"naməlum valyuta `{kod}` — `pul.valyutalar()` "
                    "siyahısına baxın və ya `pul.valyutaƏlavəEt` işlədin")
    return k


def _üsul(ad: Any) -> str:
    if ad not in ÜSULLAR:
        raise _xəta(f"naməlum yuvarlaqlaşdırma üsulu `{ad}` — "
                    + ", ".join(f'"{x}"' for x in ÜSULLAR))
    return ÜSULLAR[ad]


def ədəd(x: Any, ad: str = "məbləğ") -> Decimal:
    """Alqor dəyəri → Decimal (onluq ədəd mətn kimi oxunur — 0.1 dəqiq)."""
    if isinstance(x, Pul):
        return x.d
    if isinstance(x, bool):
        raise _xəta(f"`{ad}` ədəd olmalıdır, `məntiq` gəlib", "TipXətası")
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise _xəta(f"`{ad}` sonlu ədəd olmalıdır")
        return Decimal(repr(x))
    if isinstance(x, str):
        s = x.strip().replace(" ", "").replace(" ", "").replace("_", "")
        if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3}){2,}(,\d+)?", s) or \
                re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+,\d+", s):
            s = s.replace(".", "").replace(",", ".")        # 1.234,50
        elif re.fullmatch(r"[+-]?\d+,\d+", s):
            s = s.replace(",", ".")                          # 12,50
        else:
            s = s.replace(",", "")                           # 1,234.50
        try:
            return Decimal(s)
        except decimal.InvalidOperation:
            raise _xəta(f"`{x}` ədəd deyil")
    raise _xəta(f"`{ad}` ədəd və ya mətn olmalıdır, `{tip_adı(x)}` gəlib",
                "TipXətası")


class Pul:
    ALQOR_TİP_ADI = "pul"
    __slots__ = ("d", "valyuta")

    def __init__(self, d: Decimal, valyuta: str, üsul: str = "riyazi"):
        self.valyuta = valyuta
        self.d = self._yuvarla(d, üsul)

    def _yuvarla(self, d: Decimal, üsul: str = "riyazi") -> Decimal:
        r = VALYUTALAR[self.valyuta][1]
        try:
            return d.quantize(Decimal(1).scaleb(-r), rounding=_üsul(üsul),
                              context=_KONTEKST)
        except decimal.InvalidOperation:
            raise _xəta("məbləğ çox böyükdür")

    # ── Əsas ──────────────────────────────────────────────────────────
    @property
    def rəqəm(self) -> int:
        return VALYUTALAR[self.valyuta][1]

    def __repr__(self) -> str:
        return f"{self.d:f} {self.valyuta}"

    __str__ = __repr__

    def __eq__(self, o: Any) -> bool:
        return isinstance(o, Pul) and o.valyuta == self.valyuta and \
            o.d == self.d

    def __hash__(self) -> int:
        return hash((self.d, self.valyuta))

    def _eyni(self, o: "Pul", əməl: str) -> None:
        if o.valyuta != self.valyuta:
            raise _xəta(f"`{self.valyuta}` və `{o.valyuta}` {əməl} — "
                        "əvvəlcə `çevir` işlədin", "ValyutaXətası")

    def yeni(self, d: Decimal, üsul: str = "riyazi") -> "Pul":
        return Pul(d, self.valyuta, üsul)

    # ── Operatorlar (`icraçı._kitabxana_operatoru`) ──────────────────
    def alqor_operator(self, op: str, o: Any, sağdadır: bool) -> Any:
        if op == "əks":
            return self.yeni(-self.d)
        if op in ("+", "-"):
            if not isinstance(o, Pul):
                if sağdadır:
                    return NotImplemented
                raise _xəta(f"`pul {op} {tip_adı(o)}` — hər iki tərəf "
                            "`pul` olmalıdır", "TipXətası")
            self._eyni(o, "toplanmır" if op == "+" else "çıxılmır")
            if op == "+":
                return self.yeni(self.d + o.d)
            return self.yeni(o.d - self.d if sağdadır else self.d - o.d)
        if op == "*":
            if isinstance(o, Pul):
                raise _xəta("iki `pul` bir-birinə vurulmur", "TipXətası")
            return self.yeni(self.d * ədəd(o, "vuruq"))
        if op == "/":
            if sağdadır:
                raise _xəta("ədəd `pul`-a bölünmür", "TipXətası")
            if isinstance(o, Pul):
                self._eyni(o, "bölünmür")
                if o.d == 0:
                    raise AlqorXəta("BölməXətası", "sıfıra bölmək olmaz",
                                    None, "ALQ-R001")
                return float(self.d / o.d)
            b = ədəd(o, "bölən")
            if b == 0:
                raise AlqorXəta("BölməXətası", "sıfıra bölmək olmaz", None,
                                "ALQ-R001")
            return self.yeni(self.d / b)
        if op in ("<", ">", "<=", ">=", "<=>"):
            if not isinstance(o, Pul):
                raise _xəta(f"`pul` və `{tip_adı(o)}` müqayisə edilmir",
                            "TipXətası")
            self._eyni(o, "müqayisə edilmir")
            a, b = (o.d, self.d) if sağdadır else (self.d, o.d)
            n = -1 if a < b else (1 if a > b else 0)
            if op == "<=>":
                return n
            return {"<": n < 0, ">": n > 0, "<=": n <= 0, ">=": n >= 0}[op]
        return NotImplemented

    # ── Metodlar ──────────────────────────────────────────────────────
    def böl(self, n: int) -> list["Pul"]:
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise _xəta("`böl` müsbət tam ədəd gözləyir")
        return self.payla([1] * n)

    def payla(self, nisbətlər: list) -> list["Pul"]:
        """Məbləği nisbətlərə görə bölür — qəpik itmir, artıq qalıq
        qəpiklər ilk paylara bir-bir verilir."""
        if not isinstance(nisbətlər, list) or not nisbətlər:
            raise _xəta("`payla` boş olmayan nisbət siyahısı gözləyir")
        n = [ədəd(x, "nisbət") for x in nisbətlər]
        if any(x < 0 for x in n) or sum(n) == 0:
            raise _xəta("nisbətlər mənfi olmamalı, cəmi sıfırdan böyük "
                        "olmalıdır")
        vahid = Decimal(1).scaleb(-self.rəqəm)
        cəm_vahid = int((self.d / vahid).to_integral_value())
        işarə = -1 if cəm_vahid < 0 else 1
        cəm_vahid = abs(cəm_vahid)
        hissələr = [int((Decimal(cəm_vahid) * x / sum(n))
                        .to_integral_value(decimal.ROUND_FLOOR)) for x in n]
        qalıq = cəm_vahid - sum(hissələr)
        for i in range(qalıq):
            hissələr[i % len(hissələr)] += 1
        return [self.yeni(Decimal(h * işarə) * vahid) for h in hissələr]

    def faiz(self, f: Any, üsul: str = "riyazi") -> "Pul":
        return self.yeni(self.d * ədəd(f, "faiz") / 100, üsul)

    def çevir(self, valyuta: Any, məzənnə: Any,
              üsul: str = "riyazi") -> "Pul":
        m = ədəd(məzənnə, "məzənnə")
        if m <= 0:
            raise _xəta("məzənnə müsbət olmalıdır")
        return Pul(self.d * m, _valyuta(valyuta), üsul)

    def yuvarlaq(self, rəqəm: int = 0, üsul: str = "riyazi") -> "Pul":
        """Daha kobud yuvarlaqlaşdırma: `yuvarlaq(0)` → tam manat,
        `yuvarlaq(-1)` → 10-luqlara."""
        q = Decimal(1).scaleb(-int(rəqəm))
        return self.yeni(self.d.quantize(q, rounding=_üsul(üsul))
                         if rəqəm >= 0 else
                         (self.d / q).quantize(Decimal(1),
                                               rounding=_üsul(üsul)) * q)

    def qəpik(self) -> int:
        return int(self.d.scaleb(self.rəqəm))

    def formatla(self, dil: str = "az", simvol: bool = True,
                 rəqəm: int | None = None) -> str:
        return formatla(self.d, self.valyuta, dil, simvol, rəqəm)


def formatla(d: Decimal, valyuta: str, dil: str = "az",
             simvol: bool = True, rəqəm: int | None = None) -> str:
    r = VALYUTALAR[valyuta][1] if rəqəm is None else int(rəqəm)
    q = abs(d).quantize(Decimal(1).scaleb(-r), rounding=decimal.ROUND_HALF_UP)
    tam, _, kəsr = f"{q:f}".partition(".")
    dil = str(dil).split("-")[0].lower()
    min_ayır, kəsr_ayır = {
        "en": (",", "."), "tr": (".", ","), "de": (".", ","),
        "ru": (" ", ","), "az": (" ", ","), "fr": (" ", ","),
    }.get(dil, (" ", ","))
    qruplar = []
    while len(tam) > 3:
        qruplar.insert(0, tam[-3:])
        tam = tam[:-3]
    qruplar.insert(0, tam)
    s = min_ayır.join(qruplar) + (kəsr_ayır + kəsr if kəsr else "")
    işarə = "-" if d < 0 and q != 0 else ""
    işarə_ = VALYUTALAR[valyuta][0] if simvol else valyuta
    if dil == "en":
        return f"{işarə}{işarə_}{s}" if simvol else f"{işarə}{s} {işarə_}"
    if dil == "tr" and simvol:
        return f"{işarə}{işarə_}{s}"
    return f"{işarə}{s} {işarə_}"


Pul.ALQOR_METODLARI = {
    "məbləğ": lambda i, p: f"{p.d:f}",
    "onluq": lambda i, p: float(p.d),
    "qəpik": lambda i, p: p.qəpik(),
    "valyuta": lambda i, p: p.valyuta,
    "simvol": lambda i, p: VALYUTALAR[p.valyuta][0],
    "formatla": lambda i, p, dil="az", simvol=True, rəqəm=None:
        p.formatla(dil, simvol, rəqəm),
    "mətn": lambda i, p: repr(p),
    "böl": lambda i, p, n: p.böl(n),
    "payla": lambda i, p, n: p.payla(n),
    "faiz": lambda i, p, f, üsul="riyazi": p.faiz(f, üsul),
    "çevir": lambda i, p, v, m, üsul="riyazi": p.çevir(v, m, üsul),
    "yuvarlaq": lambda i, p, r=0, üsul="riyazi": p.yuvarlaq(r, üsul),
    "mütləq": lambda i, p: p.yeni(abs(p.d)),
    "sıfırdır": lambda i, p: p.d == 0,
    "müsbətdir": lambda i, p: p.d > 0,
    "mənfidir": lambda i, p: p.d < 0,
    "topla": lambda i, p, o: p.alqor_operator("+", o, False),
    "çıx": lambda i, p, o: p.alqor_operator("-", o, False),
    "vur": lambda i, p, o, üsul="riyazi": p.yeni(
        p.d * ədəd(o, "vuruq"), üsul),
    "bölHissə": lambda i, p, o, üsul="riyazi": p.yeni(
        p.d / ədəd(o, "bölən"), üsul),
    "lüğət": lambda i, p: {"məbləğ": f"{p.d:f}", "valyuta": p.valyuta},
}


def yarat(məbləğ: Any, valyuta: Any = "AZN", üsul: str = "riyazi") -> Pul:
    return Pul(ədəd(məbləğ), _valyuta(valyuta), üsul)


def qəpikdən(n: Any, valyuta: Any = "AZN") -> Pul:
    if not isinstance(n, int) or isinstance(n, bool):
        raise _xəta("`qəpikdən` tam ədəd gözləyir", "TipXətası")
    v = _valyuta(valyuta)
    return Pul(Decimal(n).scaleb(-VALYUTALAR[v][1]), v)


_SİMVOLDAN = {}


def oxu(m: Any) -> Pul:
    """"12,50 AZN", "₼ 12.50", "$1,234.50", "1 234,50 ₼" → pul."""
    s = str(m).strip()
    if not _SİMVOLDAN:
        for k, (sim, _, _) in VALYUTALAR.items():
            _SİMVOLDAN.setdefault(sim, k)
    kod = None
    for k in sorted(VALYUTALAR, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z]){k}(?![A-Za-z])", s, re.I):
            kod = k
            s = re.sub(k, "", s, flags=re.I)
            break
    if kod is None:
        for sim in sorted(_SİMVOLDAN, key=len, reverse=True):
            if sim in s:
                kod = _SİMVOLDAN[sim]
                s = s.replace(sim, "")
                break
    if kod is None:
        raise _xəta(f"`{m}` mətnində valyuta tapılmadı")
    return Pul(ədəd(s.strip()), kod)


def cəm(siyahı: Any, valyuta: Any = None) -> Pul:
    if not isinstance(siyahı, list):
        raise _xəta("`cəm` siyahı gözləyir", "TipXətası")
    if not siyahı:
        if valyuta is None:
            raise _xəta("boş siyahının cəmi üçün `valyuta` verin")
        return Pul(Decimal(0), _valyuta(valyuta))
    n = siyahı[0]
    if not isinstance(n, Pul):
        raise _xəta("`cəm` yalnız `pul` siyahısı qəbul edir", "TipXətası")
    for x in siyahı[1:]:
        n = n.alqor_operator("+", x, False)
    return n


def valyuta_əlavə_et(kod: str, simvol: str, rəqəm: int = 2,
                     ad: str = "") -> None:
    k = str(kod).strip().upper()
    if not re.fullmatch(r"[A-Z]{3,4}", k):
        raise _xəta("valyuta kodu 3–4 böyük latın hərfi olmalıdır")
    if not isinstance(rəqəm, int) or not 0 <= rəqəm <= 18:
        raise _xəta("`rəqəm` 0–18 arası tam ədəd olmalıdır")
    VALYUTALAR[k] = (str(simvol), rəqəm, str(ad or k))
    _SİMVOLDAN.clear()


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    def böyük_kiçik(f):
        def g(siyahı):
            if not isinstance(siyahı, list) or not siyahı:
                raise _xəta("boş olmayan `pul` siyahısı gözlənilir")
            n = siyahı[0]
            for x in siyahı[1:]:
                if f(x.alqor_operator("<=>", n, False)):
                    n = x
            return n
        return g

    return {
        "yarat": D("yarat", yarat, 1, 3),
        "qəpikdən": D("qəpikdən", qəpikdən, 1, 2),
        "oxu": D("oxu", oxu, 1, 1),
        "sıfır": D("sıfır", lambda valyuta="AZN": Pul(
            Decimal(0), _valyuta(valyuta)), 0, 1),
        "cəm": D("cəm", cəm, 1, 2),
        "minimum": D(
            "minimum", böyük_kiçik(lambda n: n < 0), 1, 1),
        "maksimum": D("maksimum", böyük_kiçik(lambda n: n > 0), 1, 1),
        "puldur": D("puldur", lambda x: isinstance(x, Pul), 1, 1),
        "valyutalar": D("valyutalar", lambda: {
            k: {"simvol": v[0], "rəqəm": v[1], "ad": v[2]}
            for k, v in VALYUTALAR.items()}),
        "valyutaƏlavəEt": D("valyutaƏlavəEt", valyuta_əlavə_et, 2, 4),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i = T.MƏTN, T.İSTƏNİLƏN, T.TAM
    P = T.Sadə("pul")
    return {
        "yarat": F(e, m, m, qaytarır=P, standart=2),
        "qəpikdən": F(i, m, qaytarır=P, standart=1),
        "oxu": F(m, qaytarır=P),
        "sıfır": F(m, qaytarır=P, standart=1),
        "cəm": F(T.Siyahı(P), m, qaytarır=P, standart=1),
        "minimum": F(T.Siyahı(P), qaytarır=P),
        "maksimum": F(T.Siyahı(P), qaytarır=P),
        "puldur": F(e, qaytarır=T.MƏNTİQ),
        "valyutalar": F(qaytarır=T.Lüğət(m, T.Lüğət(m, e))),
        "valyutaƏlavəEt": F(m, m, i, m, qaytarır=T.HEÇ, standart=2),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, b, o = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.MƏNTİQ, T.ONLUQ
    P = T.Sadə("pul")
    return {"pul": {
        "məbləğ": F(qaytarır=m), "onluq": F(qaytarır=o),
        "qəpik": F(qaytarır=i), "valyuta": F(qaytarır=m),
        "simvol": F(qaytarır=m),
        "formatla": F(m, b, i, qaytarır=m, standart=3),
        "mətn": F(qaytarır=m),
        "böl": F(i, qaytarır=T.Siyahı(P)),
        "payla": F(T.Siyahı(), qaytarır=T.Siyahı(P)),
        "faiz": F(e, m, qaytarır=P, standart=1),
        "çevir": F(m, e, m, qaytarır=P, standart=1),
        "yuvarlaq": F(i, m, qaytarır=P, standart=2),
        "mütləq": F(qaytarır=P),
        "sıfırdır": F(qaytarır=b), "müsbətdir": F(qaytarır=b),
        "mənfidir": F(qaytarır=b),
        "topla": F(P, qaytarır=P), "çıx": F(P, qaytarır=P),
        "vur": F(e, m, qaytarır=P, standart=1),
        "bölHissə": F(e, m, qaytarır=P, standart=1),
        "lüğət": F(qaytarır=T.Lüğət(m, m)),
    }}


def operator_tipi(op: str, sol, sağ):
    """Tip yoxlayıcısı üçün: `pul` operatorlarının nəticə tipi."""
    from .. import tipler as T
    P = T.Sadə("pul")
    if T.naməlumdur(sol) or T.naməlumdur(sağ) or sol == T.İSTƏNİLƏN or \
            sağ == T.İSTƏNİLƏN:
        return T.NAMƏLUM
    if op == "əks":
        return P
    if op in ("+", "-"):
        return P if sol == P and sağ == P else T.HEÇ
    if op == "*":
        if (sol == P and T.ədəddir(sağ)) or (sağ == P and T.ədəddir(sol)):
            return P
        return T.HEÇ
    if op == "/":
        if sol == P and sağ == P:
            return T.ONLUQ
        return P if sol == P and T.ədəddir(sağ) else T.HEÇ
    if op in ("<", ">", "<=", ">="):
        return T.MƏNTİQ if sol == P and sağ == P else T.HEÇ
    if op == "<=>":
        return T.TAM if sol == P and sağ == P else T.HEÇ
    return T.HEÇ
