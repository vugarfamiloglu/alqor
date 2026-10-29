"""
Alqor — ölçü vahidləri (spes. § 3.8).

    dəyişən məsafə = 5 km
    dəyişən vaxt = 30 dəq
    yaz(məsafə + 300 m)            // 5.3 km
    yaz(məsafə / vaxt)             // 0.16666666666666666 km/dəq
    yaz((məsafə / vaxt) kimi m)    // ✖ ölçülər uyğun deyil
    yaz((90 km/saat).çevir("m/san"))   // 25.0 m/san

Kəmiyyət = ədəd + vahid. Vahid — sadə vahidlərin qüvvətləri hasili
(`km/saat` = km¹·saat⁻¹); ölçü vektoru (uzunluq, kütlə, vaxt, verilənlər)
uyğun gəlməyən kəmiyyətlər toplanmır (`VahidXətası`).

Bu modulun hesabı `alqor-rs/src/icraci/vahid.rs` və `js/icra.js`-də eyni
qaydalarla təkrarlanır.
"""

from __future__ import annotations

from typing import Any

# ad → (SI əmsalı, ölçü: uzunluq, kütlə, vaxt, verilənlər)
VAHİDLƏR: dict[str, tuple[float, tuple[int, int, int, int]]] = {
    # uzunluq
    "mm": (0.001, (1, 0, 0, 0)), "sm": (0.01, (1, 0, 0, 0)),
    "dm": (0.1, (1, 0, 0, 0)), "m": (1.0, (1, 0, 0, 0)),
    "km": (1000.0, (1, 0, 0, 0)), "düym": (0.0254, (1, 0, 0, 0)),
    "fut": (0.3048, (1, 0, 0, 0)), "mil": (1609.344, (1, 0, 0, 0)),
    # sahə və həcm
    "ha": (10000.0, (2, 0, 0, 0)),
    "ml": (0.000001, (3, 0, 0, 0)), "l": (0.001, (3, 0, 0, 0)),
    # kütlə
    "mq": (0.000001, (0, 1, 0, 0)), "q": (0.001, (0, 1, 0, 0)),
    "kq": (1.0, (0, 1, 0, 0)), "ton": (1000.0, (0, 1, 0, 0)),
    # vaxt
    "ms": (0.001, (0, 0, 1, 0)), "san": (1.0, (0, 0, 1, 0)),
    "dəq": (60.0, (0, 0, 1, 0)), "saat": (3600.0, (0, 0, 1, 0)),
    "gün": (86400.0, (0, 0, 1, 0)), "həftə": (604800.0, (0, 0, 1, 0)),
    # verilənlər
    "B": (1.0, (0, 0, 0, 1)), "KB": (1024.0, (0, 0, 0, 1)),
    "MB": (1048576.0, (0, 0, 0, 1)), "GB": (1073741824.0, (0, 0, 0, 1)),
    "TB": (1099511627776.0, (0, 0, 0, 1)),
}

_ÜST = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
_ÜSTDƏN = {v: k for k, v in zip("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")}


class VahidXətası(Exception):
    """Vahid mətni təhlil olunmadı və ya ölçülər uyğun deyil."""

    def __init__(self, mesaj: str, kod: str = "ALQ-T084"):
        super().__init__(mesaj)
        self.mesaj, self.kod = mesaj, kod


class Vahid:
    """Sadə vahidlərin qüvvətləri: `(("km", 1), ("saat", -1))`."""

    __slots__ = ("hissələr",)

    def __init__(self, hissələr: tuple[tuple[str, int], ...]):
        self.hissələr = hissələr

    @staticmethod
    def birləşdir(*siyahılar) -> "Vahid":
        """Hissələri toplayır (eyni ad — qüvvətlər cəmlənir, sıra
        ilk görünməyə görə), sıfır qüvvətlər atılır."""
        sıra: list[str] = []
        üst: dict[str, int] = {}
        for siyahı in siyahılar:
            for ad, n in siyahı:
                if ad not in üst:
                    sıra.append(ad)
                    üst[ad] = 0
                üst[ad] += n
        return Vahid(tuple((a, üst[a]) for a in sıra if üst[a] != 0))

    def qüvvət(self, n: int) -> "Vahid":
        return Vahid.birləşdir(tuple((a, k * n) for a, k in self.hissələr))

    @property
    def əmsal(self) -> float:
        e = 1.0
        for ad, n in self.hissələr:
            e *= VAHİDLƏR[ad][0] ** n
        return e

    @property
    def ölçü(self) -> tuple[int, ...]:
        ö = [0, 0, 0, 0]
        for ad, n in self.hissələr:
            for i, x in enumerate(VAHİDLƏR[ad][1]):
                ö[i] += x * n
        return tuple(ö)

    def boşdur(self) -> bool:
        return not self.hissələr

    def __str__(self) -> str:
        def yaz(ad: str, n: int) -> str:
            return ad if n == 1 else ad + str(n).translate(_ÜST)
        surət = [yaz(a, n) for a, n in self.hissələr if n > 0]
        məxrəc = [yaz(a, -n) for a, n in self.hissələr if n < 0]
        s = "·".join(surət) or ("1" if məxrəc else "")
        if məxrəc:
            s += "/" + "·".join(məxrəc)
        return s


def təhlil_et(mətn: str) -> Vahid:
    """`"km/saat"`, `"m/san²"`, `"kq·m"` → `Vahid`."""
    s = mətn.replace(" ", "")
    if not s:
        raise VahidXətası("vahid boşdur")
    hissələr: list[tuple[str, int]] = []
    for i, qisim in enumerate(s.split("/")):
        if i > 1:
            raise VahidXətası(f"`{mətn}` — yalnız bir `/` ola bilər")
        if qisim == "1" and i == 0:
            continue
        for p in qisim.replace("*", "·").split("·"):
            ad, üst = p, ""
            while ad and (ad[-1] in _ÜSTDƏN):
                üst = _ÜSTDƏN[ad[-1]] + üst
                ad = ad[:-1]
            if "^" in ad:
                ad, üst = ad.split("^", 1)
            if ad not in VAHİDLƏR:
                raise VahidXətası(f"`{ad}` naməlum vahiddir")
            try:
                n = int(üst) if üst else 1
            except ValueError:
                raise VahidXətası(f"`{p}` — qüvvət tam ədəd olmalıdır") \
                    from None
            hissələr.append((ad, -n if i == 1 else n))
    return Vahid.birləşdir(hissələr)


def vahiddir(ad: str) -> bool:
    return ad in VAHİDLƏR


class Kəmiyyət:
    """Ədəd və onun vahidi."""

    __slots__ = ("dəyər", "vahid")
    ALQOR_TİP_ADI = "kəmiyyət"
    ALQOR_METODLARI = {
        "dəyər": lambda i, k: k.dəyər,
        "vahid": lambda i, k: str(k.vahid),
        "çevir": lambda i, k, v: i.kəmiyyəti_çevir(k, v, None),
    }

    def __init__(self, dəyər: Any, vahid: Vahid):
        self.dəyər, self.vahid = dəyər, vahid

    def __repr__(self) -> str:
        return f"<kəmiyyət {self.dəyər} {self.vahid}>"

    def __str__(self) -> str:
        from .deyerler import mətnə
        return f"{mətnə(self.dəyər)} {self.vahid}"

    def alqor_operator(self, op: str, digər: Any, sağdadır: bool) -> Any:
        if op == "əks":
            return Kəmiyyət(-self.dəyər, self.vahid)
        return NotImplemented

    def alqor_çevir(self, hədəf: str, yer=None) -> Any:
        if hədəf == "mətn":
            return str(self)
        return NotImplemented

    def __eq__(self, digər: Any) -> bool:
        if not isinstance(digər, Kəmiyyət) or \
                digər.vahid.ölçü != self.vahid.ölçü:
            return False
        return self.dəyər * self.vahid.əmsal == \
            digər.dəyər * digər.vahid.əmsal

    def __hash__(self) -> int:
        return hash((self.vahid.ölçü, float(self.dəyər * self.vahid.əmsal)))


def yarat(dəyər: Any, vahid: Vahid) -> Any:
    """Vahidsiz nəticə adi ədəd olur."""
    if vahid.boşdur():
        return dəyər
    return Kəmiyyət(dəyər, vahid)


def nisbət(mənbə: Vahid, hədəf: Vahid) -> float | None:
    """`mənbə`-dəki dəyəri `hədəf`-ə çevirən vurğu (eyni vahid — `None`)."""
    if str(mənbə) == str(hədəf):
        return None
    return mənbə.əmsal / hədəf.əmsal


def uyğunsuz(a: Vahid, b: Vahid, əməl: str) -> VahidXətası:
    return VahidXətası(f"`{a or 'ədəd'}` və `{b or 'ədəd'}` {əməl} — "
                       "ölçülər uyğun deyil")
