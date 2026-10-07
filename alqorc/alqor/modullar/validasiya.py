"""
`validasiya` — giriş yoxlaması: zəncirvari qaydalar və sxemlər (§ 10.17).

    gətir validasiya
    dəyişən v = validasiya

    dəyişən qeydiyyat = v.sxem({
        "ad":       v.mətn().kəs().min(2).maks(50),
        "yaş":      v.tam().aralıq(18, 120),
        "epoçt":    v.ePoçt(),
        "telefon":  v.telefon().ixtiyari(),
        "rol":      v.biri(["admin", "redaktor"]).standart("redaktor"),
        "parol":    v.mətn().min(8).naxış("[0-9]", "ən azı bir rəqəm olmalıdır"),
        "təkrar":   v.mətn().eyni("parol", "parollar eyni deyil"),
        "etiketlər": v.siyahı(v.mətn().maks(20)).maks(5).ixtiyari(),
        "ünvan":    v.lüğət({"şəhər": v.mətn(), "poçt": v.mətn().naxış("^AZ[0-9]\\{4}$")}),
    })

    dəyişən n = qeydiyyat.yoxla(forma)
    əgər n.etibarlıdır() onda
        yadda(n.dəyərlər())             // təmizlənmiş, çevrilmiş dəyərlər
    yoxsa
        yaz(n.xətalar())                // {"yaş": ["ən azı 18 olmalıdır"], …}
    son

    dəyişən d = qeydiyyat.təsdiqlə(forma)  // səhvdə ValidasiyaXətası atır

Növlər: `mətn tam onluq ədəd məntiq ePoçt url telefon uuid ip tarix
vaxt fin vöen iban kart siyahı lüğət biri istənilən`.

Qayda metodları: `min maks aralıq uzunluq naxış kəs kiçik böyük
ixtiyari boşOla standart mesaj yoxla çevir eyni fərqli biri müsbət
mənfiOlmayan unikal elementlər ciddi`.

Formalardan gələn mətnlər çevrilir: `v.tam()` "42" → 42, `v.məntiq()`
"doğru" / "on" / "1" → doğru. `ciddi()` bunu söndürür.

Ayrıca yoxlayıcılar: `ePoçtdur urldir telefondur uuiddir ipdir tarixdir
findir vöendir ibandır kartdır`.
"""

from __future__ import annotations

import ipaddress
import re
from datetime import date, datetime
from typing import Any, Callable

from ..deyerler import AlqorXəta, Daxili, tip_adı
from ._yardim import çağır, funksiya_tələb

_YOX = object()

_EPOÇT = re.compile(
    r"^(?=.{3,254}$)[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@(?:[A-Za-z0-9À-￿](?:[A-Za-z0-9À-￿-]{0,61}"
    r"[A-Za-z0-9À-￿])?\.)+[A-Za-zÀ-￿]{2,63}$")
_URL = re.compile(r"^(https?|ftp)://[^\s/?#:]+(:\d{1,5})?([/?#]\S*)?$",
                  re.I)
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-"
                   r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
# AZ mobil/şəhər kodları: 10 12 18 22 … 50 51 55 60 70 77 99
_AZ_KODLAR = {"10", "12", "18", "20", "21", "22", "23", "24", "25", "26",
              "50", "51", "55", "60", "70", "77", "99"}


# ── Ayrıca yoxlayıcılar ───────────────────────────────────────────────

def ePoçtdur(x: Any) -> bool:
    return isinstance(x, str) and ".." not in x and bool(_EPOÇT.match(x))


def urldir(x: Any) -> bool:
    return isinstance(x, str) and bool(_URL.match(x))


def telefon_normal(x: Any) -> str | None:
    """Telefonu `+994501234567` şəklinə salır; tanınmırsa `None`."""
    if not isinstance(x, str):
        return None
    s = re.sub(r"[\s().-]", "", x)
    if s.startswith("00"):
        s = "+" + s[2:]
    if re.fullmatch(r"0\d{9}", s):                    # 050 123 45 67
        s = "+994" + s[1:]
    elif re.fullmatch(r"\d{9}", s) and s[:2] in _AZ_KODLAR:
        s = "+994" + s
    elif re.fullmatch(r"994\d{9}", s):
        s = "+" + s
    if s.startswith("+994"):
        return s if re.fullmatch(r"\+994\d{9}", s) and \
            s[4:6] in _AZ_KODLAR else None
    return s if re.fullmatch(r"\+[1-9]\d{6,14}", s) else None


def telefondur(x: Any) -> bool:
    return telefon_normal(x) is not None


def uuiddir(x: Any) -> bool:
    return isinstance(x, str) and bool(_UUID.match(x))


def ipdir(x: Any, versiya: Any = None) -> bool:
    if not isinstance(x, str):
        return False
    try:
        a = ipaddress.ip_address(x)
    except ValueError:
        return False
    return versiya is None or a.version == versiya


def tarixdir(x: Any) -> bool:
    if not isinstance(x, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
        return False
    try:
        date.fromisoformat(x)
        return True
    except ValueError:
        return False


def vaxtdır(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    try:
        datetime.fromisoformat(x.rstrip("Z"))
        return True
    except ValueError:
        return False


def findir(x: Any) -> bool:
    """Şəxsiyyət vəsiqəsinin FİN kodu: 7 simvol, böyük latın hərfi və
    rəqəm (I və O hərfləri işlənmir)."""
    return isinstance(x, str) and bool(
        re.fullmatch(r"[0-9A-HJ-NP-Z]{7}", x))


def vöendir(x: Any) -> bool:
    """VÖEN: 10 rəqəm, sonuncu 1 (hüquqi şəxs) və ya 2 (fiziki şəxs)."""
    return isinstance(x, str) and bool(re.fullmatch(r"\d{9}[12]", x))


def ibandır(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    s = x.replace(" ", "").upper()
    uzunluqlar = {"AZ": 28, "TR": 26, "DE": 22, "GB": 22, "FR": 27,
                  "GE": 22, "RU": 33, "UA": 29, "KZ": 20, "NL": 18}
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    if s[:2] in uzunluqlar and len(s) != uzunluqlar[s[:2]]:
        return False
    r = s[4:] + s[:4]
    ədəd = "".join(str(int(c, 36)) for c in r)
    return int(ədəd) % 97 == 1


def kartdır(x: Any) -> bool:
    """Bank kartı nömrəsi — Luhn alqoritmi (13–19 rəqəm)."""
    if not isinstance(x, str):
        return False
    s = re.sub(r"[\s-]", "", x)
    if not re.fullmatch(r"\d{13,19}", s):
        return False
    cəm = 0
    for i, c in enumerate(reversed(s)):
        d = int(c)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        cəm += d
    return cəm % 10 == 0


# ── Qayda ─────────────────────────────────────────────────────────────

_NÖV_ADI = {"mətn": "mətn", "tam": "tam ədəd", "onluq": "ədəd",
            "ədəd": "ədəd", "məntiq": "doğru/yanlış", "siyahı": "siyahı",
            "lüğət": "lüğət"}

_DOĞRU = {"doğru", "dogru", "true", "1", "bəli", "beli", "hə", "on", "yes"}
_YANLIŞ = {"yanlış", "yanlis", "false", "0", "xeyr", "off", "no", ""}


class _Uğursuz(Exception):
    def __init__(self, mesaj: str):
        self.mesaj = mesaj


class Qayda:
    ALQOR_TİP_ADI = "qayda"

    def __init__(self, növ: str):
        self.növ = növ
        self.addımlar: list[tuple[str, Callable]] = []
        self.ixtiyari = False
        self.boş_ola = False
        self.standart_: Any = _YOX
        self.mesaj_: str | None = None
        self.ciddi_ = False
        self.element: "Qayda | None" = None
        self.sahələr: "Sxem | None" = None
        self.eynilər: list[tuple[str, str, bool]] = []   # (sahə, mesaj, eyni)

    def __repr__(self) -> str:
        return f"<qayda {self.növ}>"

    def _kopya(self) -> "Qayda":
        q = Qayda(self.növ)
        q.__dict__.update({k: (list(v) if isinstance(v, list) else v)
                           for k, v in self.__dict__.items()})
        return q

    def _əlavə(self, ad: str, f: Callable) -> "Qayda":
        q = self._kopya()
        q.addımlar.append((ad, f))
        return q

    # ── Növ yoxlaması və çevirmə ──────────────────────────────────────
    def _növ_yoxla(self, x: Any) -> Any:
        n = self.növ
        if n in ("istənilən",):
            return x
        if n == "mətn" or n in _MƏTN_NÖVLƏRİ:
            if isinstance(x, (int, float)) and not isinstance(x, bool) \
                    and not self.ciddi_ and n == "mətn":
                return str(x)
            if not isinstance(x, str):
                raise _Uğursuz("mətn olmalıdır")
            return x
        if n == "tam":
            if isinstance(x, str) and not self.ciddi_ and \
                    re.fullmatch(r"\s*[+-]?\d+\s*", x):
                return int(x)
            if isinstance(x, float) and x.is_integer() and not self.ciddi_:
                return int(x)
            if isinstance(x, bool) or not isinstance(x, int):
                raise _Uğursuz("tam ədəd olmalıdır")
            return x
        if n in ("onluq", "ədəd"):
            if isinstance(x, str) and not self.ciddi_:
                try:
                    v = float(x.strip().replace(",", "."))
                    if v == v and abs(v) != float("inf"):
                        return int(v) if n == "ədəd" and v.is_integer() \
                            and re.fullmatch(r"\s*[+-]?\d+\s*", x) else v
                except ValueError:
                    pass
            if isinstance(x, bool) or not isinstance(x, (int, float)) \
                    or x != x:
                raise _Uğursuz("ədəd olmalıdır")
            return float(x) if n == "onluq" else x
        if n == "məntiq":
            if isinstance(x, bool):
                return x
            if not self.ciddi_:
                if isinstance(x, str) and x.strip().lower() in _DOĞRU:
                    return True
                if isinstance(x, str) and x.strip().lower() in _YANLIŞ:
                    return False
                if x in (0, 1) and isinstance(x, int):
                    return bool(x)
            raise _Uğursuz("doğru və ya yanlış olmalıdır")
        if n == "siyahı":
            if isinstance(x, tuple):
                x = list(x)
            if not isinstance(x, list):
                raise _Uğursuz("siyahı olmalıdır")
            return x
        if n == "lüğət":
            if not isinstance(x, dict):
                raise _Uğursuz("lüğət olmalıdır")
            return x
        return x

    # ── Əsas yoxlama ──────────────────────────────────────────────────
    def _yoxla(self, icraçı, x: Any, yol: str, xətalar: dict,
               bütöv: dict | None) -> Any:
        """Dəyəri yoxlayır; xətaları `xətalar`-a yazır, təmiz dəyəri
        qaytarır (xəta varsa `_YOX`)."""
        if isinstance(x, str) and any(a == "kəs" for a, _ in self.addımlar):
            x = x.strip()
        boşdur = x is None or x is _YOX or (
            isinstance(x, str) and x == "" and self.növ != "məntiq")
        if boşdur:
            if self.standart_ is not _YOX:
                return self.standart_
            if self.ixtiyari or (x is None and self.boş_ola):
                return _YOX if x is _YOX else None
            self._xəta(xətalar, yol, "boş ola bilməz" if isinstance(x, str)
                       else "tələb olunur")
            return _YOX
        try:
            x = self._növ_yoxla(x)
            for _, f in self.addımlar:
                x = f(icraçı, x)
        except _Uğursuz as u:
            self._xəta(xətalar, yol, u.mesaj)
            return _YOX
        if self.element is not None:
            n, pozuldu = [], False
            for i, e in enumerate(x):
                d = self.element._yoxla(icraçı, e, f"{yol}.{i}" if yol
                                        else str(i), xətalar, bütöv)
                if d is _YOX:
                    pozuldu = True
                n.append(d)
            if pozuldu:
                return _YOX
            x = n
        if self.sahələr is not None:
            x = self.sahələr._yoxla(icraçı, x, yol, xətalar)
            if x is _YOX:
                return _YOX
        if bütöv is not None:
            for sahə, mesaj, eyni in self.eynilər:
                if (bütöv.get(sahə) == x) != eyni:
                    self._xəta(xətalar, yol, mesaj)
                    return _YOX
        return x

    def _xəta(self, xətalar: dict, yol: str, mesaj: str) -> None:
        xətalar.setdefault(yol or "dəyər", []).append(self.mesaj_ or mesaj)


_MƏTN_NÖVLƏRİ = {"ePoçt", "url", "telefon", "uuid", "ip", "tarix", "vaxt",
                 "fin", "vöen", "iban", "kart"}


def _ölçü(x: Any) -> tuple[Any, str]:
    if isinstance(x, str):
        return len(x), "simvol"
    if isinstance(x, (list, dict)):
        return len(x), "element"
    return x, ""


def _min(q: Qayda, n: Any) -> Qayda:
    def f(_, x):
        v, vahid = _ölçü(x)
        if v < n:
            raise _Uğursuz(f"ən azı {n} {vahid}".rstrip() +
                           (" olmalıdır" if vahid else " olmalıdır"))
        return x
    if isinstance(n, str) and q.növ in ("tarix", "vaxt"):
        def f(_, x):                                  # noqa: F811
            if x < n:
                raise _Uğursuz(f"{n} və ya sonra olmalıdır")
            return x
    return q._əlavə("min", f)


def _maks(q: Qayda, n: Any) -> Qayda:
    def f(_, x):
        v, vahid = _ölçü(x)
        if v > n:
            raise _Uğursuz(f"ən çox {n} {vahid}".rstrip() + " olmalıdır")
        return x
    if isinstance(n, str) and q.növ in ("tarix", "vaxt"):
        def f(_, x):                                  # noqa: F811
            if x > n:
                raise _Uğursuz(f"{n} və ya əvvəl olmalıdır")
            return x
    return q._əlavə("maks", f)


def _uzunluq(q: Qayda, n: Any) -> Qayda:
    def f(_, x):
        if len(x) != n:
            v = "simvol" if isinstance(x, str) else "element"
            raise _Uğursuz(f"düz {n} {v} olmalıdır")
        return x
    return q._əlavə("uzunluq", f)


def _naxış(q: Qayda, n: str, mesaj: str | None = None) -> Qayda:
    try:
        r = re.compile(n)
    except re.error as x:
        raise AlqorXəta("ArqumentXətası", f"naxış yanlışdır: {x}", None,
                        "ALQ-T004")

    def f(_, x):
        if not r.search(x):
            raise _Uğursuz(mesaj or "formatı yanlışdır")
        return x
    return q._əlavə("naxış", f)


def _biri(q: Qayda, dəyərlər: Any) -> Qayda:
    if not isinstance(dəyərlər, (list, set, tuple)):
        raise AlqorXəta("TipXətası", "`biri` siyahı gözləyir", None,
                        "ALQ-T001")
    d = list(dəyərlər)

    def f(_, x):
        if x not in d:
            raise _Uğursuz("bunlardan biri olmalıdır: " +
                           ", ".join(str(e) for e in d))
        return x
    return q._əlavə("biri", f)


def _yoxla_f(q: Qayda, funksiya: Any, mesaj: str = "yanlışdır") -> Qayda:
    funksiya_tələb(funksiya, "yoxla")

    def f(icraçı, x):
        n = çağır(icraçı, funksiya, x)
        if isinstance(n, str):            # funksiya xəta mətni qaytara bilər
            raise _Uğursuz(n)
        if not n:
            raise _Uğursuz(mesaj)
        return x
    return q._əlavə("yoxla", f)


def _çevir(q: Qayda, funksiya: Any) -> Qayda:
    funksiya_tələb(funksiya, "çevir")
    return q._əlavə("çevir", lambda icraçı, x: çağır(icraçı, funksiya, x))


def _bayraq(q: Qayda, ad: str, d: Any = True) -> Qayda:
    k = q._kopya()
    setattr(k, ad, d)
    return k


def _eyni(q: Qayda, sahə: str, mesaj: str | None, eyni: bool) -> Qayda:
    k = q._kopya()
    k.eynilər.append((str(sahə), mesaj or (
        f"`{sahə}` ilə eyni olmalıdır" if eyni
        else f"`{sahə}` ilə eyni olmamalıdır"), eyni))
    return k


def _unikal(q: Qayda) -> Qayda:
    def f(_, x):
        görülən = []
        for e in x:
            if e in görülən:
                raise _Uğursuz("təkrarlanan elementlər var")
            görülən.append(e)
        return x
    return q._əlavə("unikal", f)


def _ədəd_şərti(q: Qayda, ad: str, şərt: Callable, mesaj: str) -> Qayda:
    def f(_, x):
        if not şərt(x):
            raise _Uğursuz(mesaj)
        return x
    return q._əlavə(ad, f)


def _elementlər(q: Qayda, e: Any) -> Qayda:
    k = q._kopya()
    k.element = _qayda_al(e)
    return k


def _sahələr(q: Qayda, s: Any) -> Qayda:
    k = q._kopya()
    k.sahələr = s if isinstance(s, Sxem) else Sxem(s)
    return k


def _aralıq(q: Qayda, a: Any, b: Any) -> Qayda:
    return _maks(_min(q, a), b)


Qayda.ALQOR_METODLARI = {
    "min": lambda i, q, n: _min(q, n),
    "maks": lambda i, q, n: _maks(q, n),
    "aralıq": lambda i, q, a, b: _aralıq(q, a, b),
    "uzunluq": lambda i, q, n: _uzunluq(q, n),
    "naxış": lambda i, q, n, mesaj=None: _naxış(q, n, mesaj),
    "kəs": lambda i, q: q._əlavə("kəs", lambda _, x: x.strip()
                                 if isinstance(x, str) else x),
    "kiçik": lambda i, q: q._əlavə("kiçik", lambda _, x: _az_kiçik(x)),
    "böyük": lambda i, q: q._əlavə("böyük", lambda _, x: _az_böyük(x)),
    "ixtiyari": lambda i, q: _bayraq(q, "ixtiyari"),
    "boşOla": lambda i, q: _bayraq(q, "boş_ola"),
    "standart": lambda i, q, d: _bayraq(q, "standart_", d),
    "mesaj": lambda i, q, m: _bayraq(q, "mesaj_", str(m)),
    "ciddi": lambda i, q: _bayraq(q, "ciddi_"),
    "yoxla": lambda i, q, f, mesaj="yanlışdır": _yoxla_f(q, f, mesaj),
    "çevir": lambda i, q, f: _çevir(q, f),
    "eyni": lambda i, q, s, mesaj=None: _eyni(q, s, mesaj, True),
    "fərqli": lambda i, q, s, mesaj=None: _eyni(q, s, mesaj, False),
    "biri": lambda i, q, d: _biri(q, d),
    "müsbət": lambda i, q: _ədəd_şərti(q, "müsbət", lambda x: x > 0,
                                       "müsbət olmalıdır"),
    "mənfiOlmayan": lambda i, q: _ədəd_şərti(
        q, "mənfiOlmayan", lambda x: x >= 0, "mənfi ola bilməz"),
    "unikal": lambda i, q: _unikal(q),
    "elementlər": lambda i, q, e: _elementlər(q, e),
    "sahələr": lambda i, q, s: _sahələr(q, s),
    "yoxlaDəyər": lambda i, q, x: _tək_yoxla(i, q, x),
}


def _az_kiçik(x: Any) -> Any:
    from .. import elifba as E
    return E.kiçiyə(x) if isinstance(x, str) else x


def _az_böyük(x: Any) -> Any:
    from .. import elifba as E
    return E.böyüyə(x) if isinstance(x, str) else x


def _qayda_al(x: Any) -> Qayda:
    if isinstance(x, Qayda):
        return x
    if isinstance(x, (dict, Sxem)):
        return _sahələr(Qayda("lüğət"), x)
    raise AlqorXəta("TipXətası", f"qayda gözlənilir, `{tip_adı(x)}` gəlib",
                    None, "ALQ-T001")


# ── Sxem və nəticə ────────────────────────────────────────────────────

class Nəticə:
    ALQOR_TİP_ADI = "validasiyaNəticəsi"

    def __init__(self, dəyərlər: Any, xətalar: dict):
        self.dəyərlər = dəyərlər
        self.xətalar = xətalar

    def __repr__(self) -> str:
        return ("<etibarlı>" if not self.xətalar
                else f"<{len(self.xətalar)} sahədə xəta>")

    def mətn(self) -> str:
        return "; ".join(f"{a}: {', '.join(m)}"
                         for a, m in self.xətalar.items())


Nəticə.ALQOR_METODLARI = {
    "etibarlıdır": lambda i, n: not n.xətalar,
    "xətalar": lambda i, n: n.xətalar,
    "dəyərlər": lambda i, n: n.dəyərlər,
    "ilkXəta": lambda i, n: (f"{next(iter(n.xətalar))}: "
                             f"{next(iter(n.xətalar.values()))[0]}"
                             if n.xətalar else None),
    "sahəXətası": lambda i, n, s: (n.xətalar.get(s) or [None])[0],
    "mətn": lambda i, n: n.mətn(),
}


class Sxem:
    ALQOR_TİP_ADI = "sxem"

    def __init__(self, sahələr: Any, artıq: Any = "at"):
        if not isinstance(sahələr, dict):
            raise AlqorXəta("TipXətası", "`sxem` lüğət gözləyir: "
                            '{"sahə": validasiya.mətn(), …}', None,
                            "ALQ-T001")
        if artıq not in ("at", "saxla", "xəta"):
            raise AlqorXəta("ArqumentXətası",
                            '`artıq` "at", "saxla" və ya "xəta" olmalıdır',
                            None, "ALQ-T004")
        self.sahələr = {str(a): _qayda_al(q) for a, q in sahələr.items()}
        self.artıq = artıq

    def __repr__(self) -> str:
        return f"<sxem {', '.join(self.sahələr)}>"

    def _yoxla(self, icraçı, x: Any, yol: str, xətalar: dict) -> Any:
        if not isinstance(x, dict):
            xətalar.setdefault(yol or "dəyər", []).append("lüğət olmalıdır")
            return _YOX
        n: dict = {}
        pozuldu = False
        for a, q in self.sahələr.items():
            d = q._yoxla(icraçı, x.get(a, _YOX), f"{yol}.{a}" if yol else a,
                         xətalar, x)
            if d is _YOX:
                if a in x or not q.ixtiyari:
                    pozuldu = pozuldu or any(
                        k == (f"{yol}.{a}" if yol else a) or
                        k.startswith((f"{yol}.{a}" if yol else a) + ".")
                        for k in xətalar)
                continue
            n[a] = d
        for a in x:
            if a not in self.sahələr:
                if self.artıq == "saxla":
                    n[a] = x[a]
                elif self.artıq == "xəta":
                    xətalar.setdefault(f"{yol}.{a}" if yol else str(a),
                                       []).append("gözlənilməyən sahə")
                    pozuldu = True
        return _YOX if pozuldu else n

    def yoxla(self, icraçı, x: Any) -> Nəticə:
        xətalar: dict = {}
        d = self._yoxla(icraçı, x, "", xətalar)
        return Nəticə(None if d is _YOX else d, xətalar)

    def təsdiqlə(self, icraçı, x: Any) -> Any:
        n = self.yoxla(icraçı, x)
        if n.xətalar:
            raise AlqorXəta("ValidasiyaXətası", n.mətn(), None, "ALQ-R005")
        return n.dəyərlər


Sxem.ALQOR_METODLARI = {
    "yoxla": lambda i, s, x: s.yoxla(i, x),
    "təsdiqlə": lambda i, s, x: s.təsdiqlə(i, x),
    "sahələr": lambda i, s: list(s.sahələr),
    "genişlət": lambda i, s, əlavə: Sxem(
        {**s.sahələr, **(əlavə.sahələr if isinstance(əlavə, Sxem)
                         else əlavə)}, s.artıq),
    "seç": lambda i, s, adlar: Sxem(
        {a: q for a, q in s.sahələr.items() if a in adlar}, s.artıq),
    "qismən": lambda i, s: Sxem(
        {a: _bayraq(q, "ixtiyari") for a, q in s.sahələr.items()},
        s.artıq),
}


def _tək_yoxla(icraçı, q: Qayda, x: Any) -> Nəticə:
    xətalar: dict = {}
    d = q._yoxla(icraçı, x, "", xətalar, None)
    return Nəticə(None if d is _YOX else d, xətalar)


# ── Xüsusi növlər ─────────────────────────────────────────────────────

def _xüsusi(növ: str, yoxlayıcı: Callable, mesaj: str,
            normal: Callable | None = None) -> Qayda:
    q = Qayda(növ)

    def f(_, x):
        if not yoxlayıcı(x):
            raise _Uğursuz(mesaj)
        return normal(x) if normal else x
    q.addımlar.append((növ, f))
    return q


def _növlər() -> dict[str, Callable[[], Qayda]]:
    return {
        "mətn": lambda: Qayda("mətn"),
        "tam": lambda: Qayda("tam"),
        "onluq": lambda: Qayda("onluq"),
        "ədəd": lambda: Qayda("ədəd"),
        "məntiq": lambda: Qayda("məntiq"),
        "istənilən": lambda: Qayda("istənilən"),
        "ePoçt": lambda: _xüsusi(
            "ePoçt", ePoçtdur, "düzgün e-poçt ünvanı deyil",
            lambda x: x.strip()),
        "url": lambda: _xüsusi("url", urldir, "düzgün URL deyil"),
        "telefon": lambda: _xüsusi(
            "telefon", telefondur, "düzgün telefon nömrəsi deyil",
            telefon_normal),
        "uuid": lambda: _xüsusi("uuid", uuiddir, "düzgün UUID deyil",
                                lambda x: x.lower()),
        "ip": lambda: _xüsusi("ip", ipdir, "düzgün IP ünvanı deyil"),
        "tarix": lambda: _xüsusi("tarix", tarixdir,
                                 "tarix İİİİ-AA-GG formatında olmalıdır"),
        "vaxt": lambda: _xüsusi("vaxt", vaxtdır,
                                "vaxt ISO formatında olmalıdır"),
        "fin": lambda: _xüsusi("fin", lambda x: findir(x.upper()),
                               "FİN kod 7 simvoldan ibarət olmalıdır",
                               lambda x: x.upper()),
        "vöen": lambda: _xüsusi("vöen", vöendir,
                                "VÖEN 10 rəqəmdən ibarət olmalıdır"),
        "iban": lambda: _xüsusi("iban", ibandır, "düzgün IBAN deyil",
                                lambda x: x.replace(" ", "").upper()),
        "kart": lambda: _xüsusi("kart", kartdır,
                                "düzgün kart nömrəsi deyil",
                                lambda x: re.sub(r"[\s-]", "", x)),
    }


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    n: dict[str, Any] = {ad: D(ad, f) for ad, f in _növlər().items()}
    n.update({
        "siyahı": D("siyahı", lambda e=None: _elementlər(
            Qayda("siyahı"), e) if e is not None else Qayda("siyahı"), 0, 1),
        "lüğət": D("lüğət", lambda s=None: _sahələr(Qayda("lüğət"), s)
                   if s is not None else Qayda("lüğət"), 0, 1),
        "biri": D("biri", lambda d: _biri(Qayda("istənilən"), d), 1, 1),
        "sxem": D("sxem", lambda s, artıq="at": Sxem(s, artıq), 1, 2),
        "ePoçtdur": D("ePoçtdur", ePoçtdur, 1, 1),
        "urldir": D("urldir", urldir, 1, 1),
        "telefondur": D("telefondur", telefondur, 1, 1),
        "telefonNormal": D("telefonNormal", telefon_normal, 1, 1),
        "uuiddir": D("uuiddir", uuiddir, 1, 1),
        "ipdir": D("ipdir", ipdir, 1, 2),
        "tarixdir": D("tarixdir", tarixdir, 1, 1),
        "findir": D("findir", findir, 1, 1),
        "vöendir": D("vöendir", vöendir, 1, 1),
        "ibandır": D("ibandır", ibandır, 1, 1),
        "kartdır": D("kartdır", kartdır, 1, 1),
    })
    return n


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ
    Q, S = T.Sadə("qayda"), T.Sadə("sxem")
    n: dict = {ad: F(qaytarır=Q) for ad in _növlər()}
    n.update({
        "siyahı": F(Q, qaytarır=Q, standart=1),
        "lüğət": F(e, qaytarır=Q, standart=1),
        "biri": F(T.Siyahı(), qaytarır=Q),
        "sxem": F(T.Lüğət(m, e), m, qaytarır=S, standart=1),
        "telefonNormal": F(e, qaytarır=T.ixtiyari(m)),
        "ipdir": F(e, T.TAM, qaytarır=b, standart=1),
    })
    for ad in ("ePoçtdur", "urldir", "telefondur", "uuiddir", "tarixdir",
               "findir", "vöendir", "ibandır", "kartdır"):
        n[ad] = F(e, qaytarır=b)
    return n


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ
    Q, S, N = T.Sadə("qayda"), T.Sadə("sxem"), T.Sadə("validasiyaNəticəsi")
    q = {ad: F(qaytarır=Q) for ad in (
        "kəs", "kiçik", "böyük", "ixtiyari", "boşOla", "ciddi", "müsbət",
        "mənfiOlmayan", "unikal")}
    q.update({
        "min": F(e, qaytarır=Q), "maks": F(e, qaytarır=Q),
        "aralıq": F(e, e, qaytarır=Q), "uzunluq": F(T.TAM, qaytarır=Q),
        "naxış": F(m, m, qaytarır=Q, standart=1),
        "standart": F(e, qaytarır=Q), "mesaj": F(m, qaytarır=Q),
        "yoxla": F(e, m, qaytarır=Q, standart=1),
        "çevir": F(e, qaytarır=Q),
        "eyni": F(m, m, qaytarır=Q, standart=1),
        "fərqli": F(m, m, qaytarır=Q, standart=1),
        "biri": F(T.Siyahı(), qaytarır=Q),
        "elementlər": F(e, qaytarır=Q), "sahələr": F(e, qaytarır=Q),
        "yoxlaDəyər": F(e, qaytarır=N),
    })
    return {
        "qayda": q,
        "sxem": {
            "yoxla": F(e, qaytarır=N), "təsdiqlə": F(e, qaytarır=e),
            "sahələr": F(qaytarır=T.Siyahı(m)),
            "genişlət": F(e, qaytarır=S),
            "seç": F(T.Siyahı(m), qaytarır=S),
            "qismən": F(qaytarır=S),
        },
        "validasiyaNəticəsi": {
            "etibarlıdır": F(qaytarır=b),
            "xətalar": F(qaytarır=T.Lüğət(m, T.Siyahı(m))),
            "dəyərlər": F(qaytarır=e),
            "ilkXəta": F(qaytarır=T.ixtiyari(m)),
            "sahəXətası": F(m, qaytarır=T.ixtiyari(m)),
            "mətn": F(qaytarır=m),
        },
    }
