"""
`ffi` — C kitabxanalarını çağırmaq (§ 10.17).

    gətir ffi

    dəyişən c = ffi.yüklə("c")                         // libc / msvcrt
    dəyişən strlen = c.funksiya("strlen", qaytarır: "ölçü",
                                parametrlər: ["mətn"])
    yaz(strlen("salam"))                               // 5

    dəyişən m = ffi.yüklə("m")
    dəyişən kök = m.funksiya("sqrt", "onluq", ["onluq"])
    yaz(kök(2.0))

    // Strukturlar
    dəyişən Nöqtə = ffi.struktur("Nöqtə", [["x", "tam32"], ["y", "tam32"]])
    dəyişən n = Nöqtə.yarat({"x": 3, "y": 4})
    n.qoy("x", 10)
    yaz(n.al("x"), n.lüğət(), Nöqtə.ölçü())

    // Bufer (char* çıxış parametrləri üçün)
    dəyişən b = ffi.bufer(64)
    c.funksiya("snprintf", "tam", ["bufer", "ölçü", "mətn", "tam"])(b, 64, "%d", 42)
    yaz(b.mətn())                                      // "42"

    // Geri çağırış (C → Alqor), məs. qsort üçün
    dəyişən müq = ffi.geriÇağırış((a, b) => …, "tam", ["göstərici", "göstərici"])

Tiplər: tam8 tam16 tam32 tam64 işarəsiz8 işarəsiz16 işarəsiz32
işarəsiz64 tam uzun ölçü onluq onluq32 məntiq simvol mətn mətnGeniş
göstərici bufer heç (+ `ffi.struktur` ilə yaradılan strukturlar).

DİQQƏT: yerli (native) kod yaddaşı birbaşa idarə edir — yanlış imza və ya
göstərici prosesi çökdürə bilər. Alqorun təhlükəsizlik zəmanətləri bu
sərhəddə bitir.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı
from ._yardim import çağır, funksiya_tələb

TİPLƏR: dict[str, Any] = {
    "tam8": ctypes.c_int8, "tam16": ctypes.c_int16, "tam32": ctypes.c_int32,
    "tam64": ctypes.c_int64, "işarəsiz8": ctypes.c_uint8,
    "işarəsiz16": ctypes.c_uint16, "işarəsiz32": ctypes.c_uint32,
    "işarəsiz64": ctypes.c_uint64, "tam": ctypes.c_int,
    "uzun": ctypes.c_long, "ölçü": ctypes.c_size_t,
    "onluq": ctypes.c_double, "onluq32": ctypes.c_float,
    "məntiq": ctypes.c_bool, "simvol": ctypes.c_char,
    "mətn": ctypes.c_char_p, "mətnGeniş": ctypes.c_wchar_p,
    "göstərici": ctypes.c_void_p, "bufer": ctypes.c_void_p, "heç": None,
}


def _xəta(mesaj: str, tip: str = "FFIXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _tip(t: Any) -> Any:
    if isinstance(t, Struktur):
        return t.c
    if t not in TİPLƏR:
        raise _xəta(f"naməlum C tipi `{t}` — " + ", ".join(TİPLƏR),
                    "ArqumentXətası")
    return TİPLƏR[t]


def _arqument(t: Any, x: Any) -> Any:
    """Alqor dəyəri → ctypes arqumenti."""
    if isinstance(t, Struktur):
        if not isinstance(x, StrukturDəyəri) or x.tip is not t:
            raise _xəta(f"`{t.ad}` strukturu gözlənilir", "TipXətası")
        return x.c
    if t == "mətn":
        if x is None:
            return None
        if isinstance(x, str):
            return x.encode("utf-8")
        if isinstance(x, (bytes, bytearray)):
            return bytes(x)
        raise _xəta(f"`mətn` parametri mətn gözləyir, `{tip_adı(x)}` gəlib",
                    "TipXətası")
    if t in ("bufer", "göstərici"):
        if x is None:
            return None
        if isinstance(x, Bufer):
            return ctypes.cast(x.c, ctypes.c_void_p)
        if isinstance(x, StrukturDəyəri):
            return ctypes.cast(ctypes.pointer(x.c), ctypes.c_void_p)
        if isinstance(x, GeriÇağırış):
            return ctypes.cast(x.c, ctypes.c_void_p)
        if isinstance(x, int) and not isinstance(x, bool):
            return x
        raise _xəta(f"`{t}` parametri bufer, struktur və ya ünvan (tam) "
                    f"gözləyir, `{tip_adı(x)}` gəlib", "TipXətası")
    if t in ("onluq", "onluq32"):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise _xəta(f"`{t}` ədəd gözləyir", "TipXətası")
        return float(x)
    if t == "məntiq":
        return bool(x)
    if t == "simvol":
        if isinstance(x, str) and len(x.encode("utf-8")) == 1:
            return x.encode("utf-8")
        raise _xəta("`simvol` bir ASCII simvol gözləyir", "TipXətası")
    if t == "mətnGeniş":
        return None if x is None else str(x)
    if isinstance(x, bool) or not isinstance(x, int):
        raise _xəta(f"`{t}` tam ədəd gözləyir, `{tip_adı(x)}` gəlib",
                    "TipXətası")
    return x


def _nəticə(t: Any, x: Any) -> Any:
    if isinstance(t, Struktur):
        return StrukturDəyəri(t, x)
    if t == "mətn":
        return None if x is None else x.decode("utf-8", "replace")
    if t == "simvol":
        return x.decode("latin-1") if isinstance(x, bytes) else x
    if t == "göstərici" or t == "bufer":
        return x or 0
    return x


class Kitabxana:
    ALQOR_TİP_ADI = "cKitabxanası"

    def __init__(self, ad: Any, çağırış: str = "c"):
        yol = self._tap(str(ad))
        try:
            if çağırış == "stdcall":
                if sys.platform != "win32":
                    raise _xəta("`stdcall` yalnız Windows-da var")
                self.c = ctypes.WinDLL(yol)
            elif çağırış == "c":
                self.c = ctypes.CDLL(yol)
            else:
                raise _xəta('`çağırış` "c" və ya "stdcall" olmalıdır',
                            "ArqumentXətası")
        except OSError as x:
            raise _xəta(f'"{ad}" kitabxanası yüklənmədi: {x}')
        self.ad = str(ad)
        self.yol = yol

    @staticmethod
    def _tap(ad: str) -> str | None:
        if Path(ad).exists():
            return str(Path(ad).resolve())
        if ad in ("c", "m") and sys.platform == "win32":
            return "msvcrt"
        if ad == "c" and sys.platform == "darwin":
            return "/usr/lib/libSystem.B.dylib"
        if ad == "c" and sys.platform.startswith("linux"):
            return ctypes.util.find_library("c") or "libc.so.6"
        tapılan = ctypes.util.find_library(ad)
        if tapılan is None:
            # birbaşa ad ilə də yoxla (məs. "libsqlite3.so.0")
            return ad
        return tapılan

    def __repr__(self) -> str:
        return f"<C kitabxanası {self.ad}>"

    def funksiya(self, ad: Any, qaytarır: Any = "tam",
                 parametrlər: Any = None, variadik: Any = False) -> Daxili:
        try:
            f = getattr(self.c, str(ad))
        except AttributeError:
            # Windows C kitabxanası POSIX adlarını `_` ilə ixrac edir:
            # snprintf → _snprintf, strdup → _strdup
            try:
                if sys.platform != "win32":
                    raise
                f = getattr(self.c, "_" + str(ad))
            except AttributeError:
                raise _xəta(f"`{self.ad}` kitabxanasında `{ad}` simvolu "
                            "yoxdur")
        p = list(parametrlər or [])
        f.restype = _tip(qaytarır)
        if not variadik:
            f.argtypes = [_tip(t) for t in p]

        def çağırış(*a):
            if len(a) != len(p) and not (variadik and len(a) >= len(p)):
                raise AlqorXəta("ArqumentXətası",
                                f"`{ad}` {len(p)} arqument gözləyir, "
                                f"{len(a)} verilib", None, "ALQ-T003")
            arq = []
            for i, x in enumerate(a):
                if i < len(p):
                    v = _arqument(p[i], x)
                    if variadik:
                        c = _tip(p[i])
                        if c is not None and v is not None and \
                                not isinstance(p[i], Struktur) and \
                                not isinstance(v, (ctypes._SimpleCData,
                                                   ctypes.Structure)):
                            v = c(v)
                    arq.append(v)
                else:                                # variadik əlavələr
                    arq.append(ctypes.c_double(x) if isinstance(x, float)
                               else x.encode("utf-8") if isinstance(x, str)
                               else ctypes.c_int64(x) if isinstance(x, int)
                               else x)
            return _nəticə(qaytarır, f(*arq))
        return Daxili(str(ad), çağırış, 0, None)


Kitabxana.ALQOR_METODLARI = {
    "funksiya": lambda i, k, ad, qaytarır="tam", parametrlər=None,
    variadik=False: k.funksiya(ad, qaytarır, parametrlər, variadik),
    "var": lambda i, k, ad: hasattr(k.c, str(ad)),
    "yol": lambda i, k: k.yol,
}


class Bufer:
    ALQOR_TİP_ADI = "cBufer"

    def __init__(self, ölçü: Any):
        if isinstance(ölçü, (bytes, bytearray, list)):
            b = bytes(ölçü)
            self.c = ctypes.create_string_buffer(b, len(b))
        else:
            if isinstance(ölçü, bool) or not isinstance(ölçü, int) or \
                    not 0 < ölçü <= 1 << 30:
                raise _xəta("bufer ölçüsü müsbət tam ədəd olmalıdır",
                            "ArqumentXətası")
            self.c = ctypes.create_string_buffer(ölçü)

    def __repr__(self) -> str:
        return f"<C bufer {len(self.c)} bayt>"


Bufer.ALQOR_METODLARI = {
    "ölçü": lambda i, b: len(b.c),
    "baytlar": lambda i, b: bytes(b.c.raw),
    "mətn": lambda i, b: b.c.value.decode("utf-8", "replace"),
    "yaz": lambda i, b, d, ofs=0: _bufer_yaz(b, d, ofs),
    "ünvan": lambda i, b: ctypes.addressof(b.c),
}


def _bufer_yaz(b: Bufer, d: Any, ofs: int) -> None:
    v = d.encode("utf-8") if isinstance(d, str) else bytes(d)
    if ofs < 0 or ofs + len(v) > len(b.c):
        raise _xəta("bufer sərhədindən kənara yazmaq olmaz", "İndeksXətası")
    ctypes.memmove(ctypes.addressof(b.c) + ofs, v, len(v))


class Struktur:
    ALQOR_TİP_ADI = "cStruktur"

    def __init__(self, ad: Any, sahələr: Any, paket: Any = None):
        if not isinstance(sahələr, list) or not all(
                isinstance(s, list) and len(s) == 2 for s in sahələr):
            raise _xəta('sahələr [["ad", "tip"], …] olmalıdır',
                        "ArqumentXətası")
        self.ad = str(ad)
        self.sahələr = [(str(a), t) for a, t in sahələr]
        atributlar: dict = {"_fields_": [(a, _tip(t))
                                         for a, t in self.sahələr]}
        if paket is not None:
            atributlar["_pack_"] = int(paket)
        self.c = type(self.ad.encode("ascii", "replace").decode() or "S",
                      (ctypes.Structure,), atributlar)

    def __repr__(self) -> str:
        return f"<C struktur {self.ad}>"


Struktur.ALQOR_METODLARI = {
    "yarat": lambda i, s, d=None: StrukturDəyəri(s, None, d),
    "ölçü": lambda i, s: ctypes.sizeof(s.c),
    "sahələr": lambda i, s: [a for a, _ in s.sahələr],
}


class StrukturDəyəri:
    ALQOR_TİP_ADI = "cStrukturDəyəri"

    def __init__(self, tip: Struktur, c: Any = None, d: Any = None):
        self.tip = tip
        self.c = c if c is not None else tip.c()
        for a, v in (d or {}).items():
            self.qoy(a, v)

    def __repr__(self) -> str:
        return f"{self.tip.ad}{self.lüğət()}"

    def _sahə(self, a: str) -> Any:
        for ad, t in self.tip.sahələr:
            if ad == a:
                return t
        raise _xəta(f"`{self.tip.ad}` strukturunda `{a}` sahəsi yoxdur")

    def al(self, a: Any) -> Any:
        t = self._sahə(str(a))
        return _nəticə(t, getattr(self.c, str(a)))

    def qoy(self, a: Any, v: Any) -> None:
        t = self._sahə(str(a))
        setattr(self.c, str(a), _arqument(t, v))

    def lüğət(self) -> dict:
        return {a: self.al(a) for a, _ in self.tip.sahələr}


StrukturDəyəri.ALQOR_METODLARI = {
    "al": lambda i, s, a: s.al(a),
    "qoy": lambda i, s, a, v: s.qoy(a, v),
    "lüğət": lambda i, s: s.lüğət(),
    "ünvan": lambda i, s: ctypes.addressof(s.c),
    "baytlar": lambda i, s: bytes(memoryview(s.c).cast("B")),
}


class GeriÇağırış:
    ALQOR_TİP_ADI = "cGeriÇağırış"

    def __init__(self, icraçı, f: Any, qaytarır: Any, parametrlər: Any):
        funksiya_tələb(f, "geriÇağırış")
        p = list(parametrlər or [])
        tip = ctypes.CFUNCTYPE(_tip(qaytarır), *[_tip(t) for t in p])

        def körpü(*a):
            try:
                arq = [_nəticə(t, x) for t, x in zip(p, a)]
                n = çağır(icraçı, f, *arq)
                return _arqument(qaytarır, n) if qaytarır != "heç" else None
            except BaseException as x:              # noqa: BLE001
                # C yığınından istisna keçirmək olmaz — xəbər ver, 0 qaytar
                print(f"⚠ ffi geri çağırışı xəta verdi: {x}",
                      file=sys.stderr)
                return 0 if qaytarır != "heç" else None
        self.c = tip(körpü)                 # obyekt yaşadıqca keçərlidir

    def __repr__(self) -> str:
        return "<C geri çağırış>"


GeriÇağırış.ALQOR_METODLARI = {
    "ünvan": lambda i, g: ctypes.cast(g.c, ctypes.c_void_p).value,
}


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "yüklə": D("yüklə", lambda ad, çağırış="c": Kitabxana(ad, çağırış),
                   1, 2),
        "bufer": D("bufer", Bufer, 1, 1),
        "struktur": D("struktur", Struktur, 2, 3),
        "geriÇağırış": D("geriÇağırış", lambda f, qaytarır="heç",
                         parametrlər=None: GeriÇağırış(icraçı, f, qaytarır,
                                                       parametrlər), 1, 3),
        "tiplər": D("tiplər", lambda: {k: (ctypes.sizeof(v) if v else 0)
                                       for k, v in TİPLƏR.items()}),
        "platforma": D("platforma", lambda: sys.platform),
        "kitabxanaTap": D("kitabxanaTap", lambda ad: ctypes.util.find_library(
            str(ad)), 1, 1),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e = T.MƏTN, T.İSTƏNİLƏN
    return {
        "yüklə": F(m, m, qaytarır=T.Sadə("cKitabxanası"), standart=1),
        "bufer": F(e, qaytarır=T.Sadə("cBufer")),
        "struktur": F(m, T.Siyahı(), T.TAM, qaytarır=T.Sadə("cStruktur"),
                      standart=1),
        "geriÇağırış": F(e, m, T.Siyahı(m), qaytarır=T.Sadə("cGeriÇağırış"),
                         standart=2),
        "tiplər": F(qaytarır=T.Lüğət(m, T.TAM)),
        "platforma": F(qaytarır=m),
        "kitabxanaTap": F(m, qaytarır=T.ixtiyari(m)),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, i, b, h = T.MƏTN, T.İSTƏNİLƏN, T.TAM, T.MƏNTİQ, T.HEÇ
    SD = T.Sadə("cStrukturDəyəri")
    return {
        "cKitabxanası": {
            "funksiya": F(m, e, T.Siyahı(), b, qaytarır=e, standart=3),
            "var": F(m, qaytarır=b), "yol": F(qaytarır=T.ixtiyari(m)),
        },
        "cBufer": {
            "ölçü": F(qaytarır=i), "baytlar": F(qaytarır=T.BAYT),
            "mətn": F(qaytarır=m), "yaz": F(e, i, qaytarır=h, standart=1),
            "ünvan": F(qaytarır=i),
        },
        "cStruktur": {
            "yarat": F(T.Lüğət(m, e), qaytarır=SD, standart=1),
            "ölçü": F(qaytarır=i), "sahələr": F(qaytarır=T.Siyahı(m)),
        },
        "cStrukturDəyəri": {
            "al": F(m, qaytarır=e), "qoy": F(m, e, qaytarır=h),
            "lüğət": F(qaytarır=T.Lüğət(m, e)), "ünvan": F(qaytarır=i),
            "baytlar": F(qaytarır=T.BAYT),
        },
        "cGeriÇağırış": {"ünvan": F(qaytarır=i)},
    }
