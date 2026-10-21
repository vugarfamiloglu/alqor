"""
Python körpüsü — Python kitabxanalarının birbaşa idxalı (§ 8.14).

    gətir python:math.{sqrt, pi}
    gətir python:collections kimi kol
    gətir python:numpy kimi np            // `alqor python qur numpy`

    yaz(sqrt(16))                          // 4.0
    dəyişən say = kol.Counter("alqoritm")
    yaz(say.most_common(2))

Çevrilmə qaydaları (hər iki istiqamətdə, dərin):

    tam/onluq/mətn/məntiq/boş/bayt  ↔ int/float/str/bool/None/bytes
    siyahı/lüğət/dəst/kortej        ↔ list/dict/set/tuple
    Alqor funksiyası / lambda        → Python çağırıla bilən obyekti
    qalan hər şey                    → `PythonObyekti` proksisi

Kolleksiyanın heç bir elementi çevrilməyə ehtiyac duymursa EYNİ obyekt
ötürülür — `random.shuffle(siyahı)` Alqor siyahısını yerində dəyişir.
Alt siniflər (`OrderedDict`, `Counter`, `namedtuple`) proksi qalır ki,
öz metodları itməsin.

Python istisnaları `PythonXətası` (ALQ-M014) olur; `x.pythonTipi`
istisnanın sinif adını, `x.istisna` isə istisnanın özünü saxlayır.
"""

from __future__ import annotations

import importlib
import numbers
import operator
import os
import sys
from pathlib import Path
from typing import Any

from .deyerler import (AlqorXəta, AlqorDiapazon, AlqorGenerator, Çağırılan,
                       Nümunə, Siqnal, Sinif)

PAKET_QOVLUĞU = "python_paketlər"

# İdxal adı ≠ pip paket adı olan məşhur paketlər — xəta ipucu üçün
PIP_ADLARI = {
    "PIL": "pillow", "yaml": "pyyaml", "cv2": "opencv-python",
    "sklearn": "scikit-learn", "skimage": "scikit-image",
    "bs4": "beautifulsoup4", "dateutil": "python-dateutil",
    "dotenv": "python-dotenv", "jwt": "pyjwt", "serial": "pyserial",
    "usb": "pyusb", "Crypto": "pycryptodome", "docx": "python-docx",
    "pptx": "python-pptx", "magic": "python-magic", "attr": "attrs",
    "google": "protobuf", "win32api": "pywin32", "fitz": "pymupdf",
}


# ═══════════════════════════════════════════════════════════════════════
#  Yol: layihənin `python_paketlər/` qovluğu
# ═══════════════════════════════════════════════════════════════════════

_ƏLAVƏ_YOLLAR: set[str] = set()


def _yola_əlavə_et(q: str) -> None:
    if q in _ƏLAVƏ_YOLLAR or q in sys.path:
        _ƏLAVƏ_YOLLAR.add(q)
        return
    _ƏLAVƏ_YOLLAR.add(q)
    # Sistem paketlərindən ÖNDƏ (venv kimi), amma Alqorun öz qovluğundan
    # (sys.path[0]) sonra — layihə paketi `alqor`-u kölgələyə bilməz
    sys.path.insert(1 if sys.path else 0, q)


def yolları_qur(baza: Path | None) -> None:
    """
    İdxaldan əvvəl: `ALQOR_PYTHON_YOLU` mühit dəyişəni və layihənin
    (`layihe.alq` olan qovluğun) `python_paketlər/` qovluğu `sys.path`-a.
    `alqor qur` paketində (`.pyz`) qovluq arxivin içindədir.
    """
    for q in os.environ.get("ALQOR_PYTHON_YOLU", "").split(os.pathsep):
        if q:
            _yola_əlavə_et(q)
    paket = paket_qovluğu(baza)
    if paket is not None and paket.is_dir():
        _yola_əlavə_et(str(paket))


def paket_qovluğu(baza: Path | None) -> Path | None:
    """`baza`-dan yuxarı ilk `layihe.alq`-un yanındakı `python_paketlər/`."""
    if baza is None:
        return None
    try:
        from .layihe import tap
        l = tap(baza)
    except Exception:
        return None
    return None if l is None else l.kök / PAKET_QOVLUĞU


# ═══════════════════════════════════════════════════════════════════════
#  Xətalar
# ═══════════════════════════════════════════════════════════════════════

def python_xətası(e: BaseException, yer=None) -> AlqorXəta:
    """Python istisnası → tutula bilən `PythonXətası`."""
    if isinstance(e, AlqorXəta):
        return e
    tip = type(e).__name__
    mətn = str(e)
    mesaj = f"{tip}: {mətn}" if mətn else tip
    x = AlqorXəta("PythonXətası", mesaj, yer, "ALQ-M014")
    n = Nümunə(Sinif("PythonXətası"))
    n.sahələr.update({"mesaj": mesaj, "kod": "ALQ-M014",
                      "tip": "PythonXətası", "pythonTipi": tip,
                      "istisna": PythonObyekti(e)})
    x.dəyər = n
    return x


def _tapılmadı(ad: str, çatışmayan: str, yer) -> AlqorXəta:
    kök = çatışmayan.split(".")[0]
    pip = PIP_ADLARI.get(kök, kök)
    if ad.split(".")[0] == kök:
        mesaj = (f"`{kök}` Python paketi tapılmadı — "
                 f"`alqor python qur {pip}` ilə quraşdırın")
    else:
        mesaj = (f"`{ad}` Python modulu `{kök}` asılılığını tapmadı — "
                 f"`alqor python qur {pip}` ilə quraşdırın")
    return AlqorXəta("PythonXətası", mesaj, yer, "ALQ-M013")


# ═══════════════════════════════════════════════════════════════════════
#  İdxal
# ═══════════════════════════════════════════════════════════════════════

def modul_yüklə(ad: str, yer=None, baza: Path | None = None
                ) -> "PythonObyekti":
    """`gətir python:ad` — Python modulunu idxal edib proksi qaytarır."""
    yolları_qur(baza)
    try:
        modul = importlib.import_module(ad)
    except ModuleNotFoundError as e:
        raise _tapılmadı(ad, e.name or ad, yer) from None
    except (AlqorXəta, Siqnal):
        raise
    except Exception as e:
        raise python_xətası(e, yer) from None
    return PythonObyekti(modul)


def üzv(modul: "PythonObyekti", modul_adı: str, ad: str, yer=None) -> Any:
    """`gətir python:os.{path}` — modulun üzvü və ya alt modulu."""
    m = modul.obyekt
    if hasattr(m, ad):
        try:
            return pydən(getattr(m, ad))
        except Exception as e:
            raise python_xətası(e, yer) from None
    if hasattr(m, "__path__"):                      # paket → alt modul?
        try:
            return PythonObyekti(importlib.import_module(f"{modul_adı}.{ad}"))
        except ModuleNotFoundError:
            pass
        except Exception as e:
            raise python_xətası(e, yer) from None
    raise AlqorXəta("ArqumentXətası",
                    f"`{modul_adı}` Python modulunda `{ad}` yoxdur", yer,
                    "ALQ-M002")


def hamısı(modul: "PythonObyekti") -> dict[str, Any]:
    """`gətir python:math.*` — `__all__` və ya `_` ilə başlamayan adlar."""
    m = modul.obyekt
    adlar = getattr(m, "__all__", None)
    if adlar is None:
        adlar = [a for a in dir(m) if not a.startswith("_")]
    return {a: pydən(getattr(m, a)) for a in adlar if hasattr(m, a)}


# ═══════════════════════════════════════════════════════════════════════
#  Çevrilmə
# ═══════════════════════════════════════════════════════════════════════

_SADƏ = (type(None), bool, int, float, str, bytes)


def pydən(x: Any, _görülən: dict | None = None) -> Any:
    """Python dəyəri → Alqor dəyəri."""
    t = type(x)
    if t in _SADƏ or isinstance(x, (PythonObyekti, Çağırılan, Nümunə)):
        return x
    if isinstance(x, numbers.Integral) and not isinstance(x, bool):
        return int(x)                    # IntEnum, numpy.int64 …
    if isinstance(x, float):
        return float(x)                  # numpy.float64 …
    if isinstance(x, str) and not hasattr(x, "__dict__"):
        return str(x)
    if t in (list, tuple, dict, set, frozenset):
        görülən = {} if _görülən is None else _görülən
        if id(x) in görülən:
            return görülən[id(x)]
        görülən[id(x)] = x
        n = _kolleksiya(x, lambda e: pydən(e, görülən))
        görülən[id(x)] = n
        return n
    if isinstance(x, _AlqorÇağırışı):
        return x.f
    return (PythonFunksiyası if callable(x) else PythonObyekti)(x)


def pyə(x: Any, icraçı=None, _görülən: dict | None = None) -> Any:
    """Alqor dəyəri → Python dəyəri."""
    t = type(x)
    if t in _SADƏ:
        return x
    if isinstance(x, PythonObyekti):
        return x.obyekt
    if t in (list, tuple, dict, set, frozenset):
        görülən = {} if _görülən is None else _görülən
        if id(x) in görülən:
            return görülən[id(x)]
        görülən[id(x)] = x
        n = _kolleksiya(x, lambda e: pyə(e, icraçı, görülən))
        görülən[id(x)] = n
        return n
    if isinstance(x, AlqorDiapazon):
        return list(x)
    if isinstance(x, AlqorGenerator):
        return (pyə(e, icraçı) for e in x)
    if isinstance(x, Çağırılan):
        return _AlqorÇağırışı(x, icraçı)
    return x                       # Nümunə, Modul … olduğu kimi


def _kolleksiya(x: Any, çevir) -> Any:
    """Elementləri çevirir; heç biri dəyişməyibsə EYNİ obyekti qaytarır."""
    if isinstance(x, dict):
        cütlər = [(çevir(a), çevir(d)) for a, d in x.items()]
        if all(a is a0 and d is d0
               for (a, d), (a0, d0) in zip(cütlər, x.items())):
            return x
        return dict(cütlər)
    elementlər = [çevir(e) for e in x]
    if type(x) is frozenset:
        return set(elementlər)
    if all(e is e0 for e, e0 in zip(elementlər, x)):
        return x
    return type(x)(elementlər)


class _AlqorÇağırışı:
    """Python-a ötürülən Alqor funksiyası (`sorted(..., key: f)`)."""

    __slots__ = ("f", "icraçı", "__weakref__")

    def __init__(self, f: Çağırılan, icraçı):
        self.f = f
        self.icraçı = icraçı

    @property
    def __name__(self) -> str:                         # noqa: A003
        return getattr(self.f, "ad", "alqor_funksiyası")

    def __call__(self, *arqumentlər, **adlı):
        if self.icraçı is None:
            raise AlqorXəta("PythonXətası",
                            "Alqor funksiyası icraçısız çağırıla bilməz",
                            None, "ALQ-M014")
        n = self.icraçı._çağır(self.f, [pydən(a) for a in arqumentlər],
                               {k: pydən(v) for k, v in adlı.items()}, None)
        return pyə(n, self.icraçı)

    def __repr__(self) -> str:
        return f"<alqor {self.f!r}>"


# ═══════════════════════════════════════════════════════════════════════
#  Proksi
# ═══════════════════════════════════════════════════════════════════════

_OPERATORLAR = {
    "+": operator.add, "-": operator.sub, "*": operator.mul,
    "/": operator.truediv, "~/": operator.floordiv, "%": operator.mod,
    "**": operator.pow, "&": operator.and_, "|": operator.or_,
    "^": operator.xor, "<<": operator.lshift, ">>": operator.rshift,
    "<": operator.lt, ">": operator.gt, "<=": operator.le,
    ">=": operator.ge,
}


class PythonObyekti:
    """Alqor tərəfində Python obyekti — üzv, indeks, dövr, operator."""

    __slots__ = ("obyekt",)

    def __init__(self, obyekt: Any):
        self.obyekt = obyekt

    # ── Tip adı və mətn ───────────────────────────────────────────────
    def alqor_tip_adı(self) -> str:
        o = self.obyekt
        if isinstance(o, type(sys)):
            return f"python:modul[{o.__name__}]"
        if isinstance(o, type):
            return f"python:sinif[{o.__name__}]"
        return f"python:{type(o).__name__}"

    def __str__(self) -> str:
        return str(self.obyekt)

    def __repr__(self) -> str:
        return repr(self.obyekt)

    # ── Python protokolları (Alqor kitabxanası və Python kodu üçün) ──
    def __eq__(self, digər: Any) -> bool:
        return bool(self.obyekt == pyə(digər))

    def __hash__(self) -> int:
        return hash(self.obyekt)

    def __len__(self) -> int:
        return len(self.obyekt)

    def __iter__(self):
        return (pydən(e) for e in self.obyekt)

    def __bool__(self) -> bool:
        return bool(self.obyekt)

    def __int__(self) -> int:
        return int(self.obyekt)

    def __float__(self) -> float:
        return float(self.obyekt)

    # ── Üzvlər ────────────────────────────────────────────────────────
    def alqor_üzv(self, icraçı, ad: str, yer) -> Any:
        o = self.obyekt
        try:
            return pydən(getattr(o, ad))
        except AttributeError:
            pass
        except (AlqorXəta, Siqnal):
            raise
        except Exception as e:
            raise python_xətası(e, yer) from None
        if isinstance(o, type(sys)) and hasattr(o, "__path__"):
            try:
                return PythonObyekti(
                    importlib.import_module(f"{o.__name__}.{ad}"))
            except ModuleNotFoundError:
                pass
            except Exception as e:
                raise python_xətası(e, yer) from None
        raise AlqorXəta("ArqumentXətası",
                        f"`{self.alqor_tip_adı()}` tipində `{ad}` üzvü "
                        "yoxdur", yer, "ALQ-T006")

    def alqor_üzv_qoy(self, icraçı, ad: str, dəyər: Any, yer) -> None:
        self._et(yer, setattr, self.obyekt, ad, pyə(dəyər, icraçı))

    # ── İndeks və dilim ───────────────────────────────────────────────
    def alqor_indeks(self, icraçı, indeks: Any, yer) -> Any:
        return pydən(self._et(yer, operator.getitem, self.obyekt,
                              pyə(indeks, icraçı)))

    def alqor_indeks_qoy(self, icraçı, indeks: Any, dəyər: Any,
                         yer) -> None:
        self._et(yer, operator.setitem, self.obyekt, pyə(indeks, icraçı),
                 pyə(dəyər, icraçı))

    def alqor_dilim(self, icraçı, b: Any, s: Any, daxil: bool, yer) -> Any:
        """Alqor dilimi `a[1..3]` son həddi DAXİL edir, `a[1..<3]` yox."""
        if daxil and isinstance(s, int):
            s = None if s == -1 else s + 1
        return pydən(self._et(yer, operator.getitem, self.obyekt,
                              slice(b, s)))

    # ── Dövr, üzvlük, uzunluq ─────────────────────────────────────────
    @property
    def alqor_lüğətdir(self) -> bool:
        """`hər a, d üçün sayğac içində` — Mapping lüğət kimi gəzilir."""
        from collections.abc import Mapping
        return isinstance(self.obyekt, Mapping)

    def alqor_iterasiya(self, yer):
        try:
            it = iter(self.obyekt)
        except TypeError as e:
            raise python_xətası(e, yer) from None

        def axın():
            while True:
                try:
                    e = next(it)
                except StopIteration:
                    return
                except (AlqorXəta, Siqnal):
                    raise
                except Exception as x:
                    raise python_xətası(x, yer) from None
                yield pydən(e)
        return axın()

    def alqor_ehtiva(self, element: Any, yer) -> bool:
        return bool(self._et(yer, operator.contains, self.obyekt,
                             pyə(element)))

    def alqor_uzunluq(self, yer=None) -> int:
        return self._et(yer, len, self.obyekt)

    # ── Operatorlar (`icraci._kitabxana_operatoru`) ────────────────
    def alqor_operator(self, op: str, digər: Any, sağdadır: bool) -> Any:
        if op == "əks":
            return pydən(self._et(None, operator.neg, self.obyekt))
        a, b = self.obyekt, pyə(digər)
        if sağdadır:
            a, b = b, a
        if op == "<=>":
            kiçik = self._et(None, operator.lt, a, b)
            böyük = self._et(None, operator.gt, a, b)
            return (1 if böyük else 0) - (1 if kiçik else 0)
        f = _OPERATORLAR.get(op)
        if f is None:
            return NotImplemented
        return pydən(self._et(None, f, a, b))

    # ── Çevirmə: `tamƏt(x)`, `x kimi məntiq` … ───────────────────────
    def alqor_çevir(self, hədəf: str, yer) -> Any:
        f = {"tam": int, "onluq": float, "məntiq": bool,
             "siyahı": lambda o: [pydən(e) for e in o],
             "dəst": lambda o: {pydən(e) for e in o}}.get(hədəf)
        if f is None:
            return NotImplemented
        return self._et(yer, f, self.obyekt)

    # ── Kontekst meneceri: `istifadə f = open("a.txt")` ───────────────
    def alqor_kontekst_aç(self, yer) -> Any:
        if not hasattr(type(self.obyekt), "__enter__"):
            return NotImplemented
        return pydən(self._et(yer, type(self.obyekt).__enter__,
                              self.obyekt))

    def alqor_kontekst_bağla(self, xəta: BaseException | None, yer) -> None:
        çıx = getattr(type(self.obyekt), "__exit__", None)
        if çıx is None:
            return
        if xəta is None:
            self._et(yer, çıx, self.obyekt, None, None, None)
        else:
            self._et(yer, çıx, self.obyekt, type(xəta), xəta,
                     xəta.__traceback__)

    # ── Köməkçi ───────────────────────────────────────────────────────
    @staticmethod
    def _et(yer, f, *arqumentlər, **adlı):
        try:
            return f(*arqumentlər, **adlı)
        except (AlqorXəta, Siqnal):
            raise
        except Exception as e:
            raise python_xətası(e, yer) from None


class PythonFunksiyası(PythonObyekti, Çağırılan):
    """Çağırıla bilən Python obyekti: funksiya, metod, sinif."""

    __slots__ = ()

    @property
    def ad(self) -> str:
        return getattr(self.obyekt, "__name__", "python")

    def alqor_tip_adı(self) -> str:
        o = self.obyekt
        if isinstance(o, type):
            return f"python:sinif[{o.__name__}]"
        return f"python:funksiya[{getattr(o, '__name__', '?')}]"

    def çağır(self, icraçı, arqumentlər: list, adlı: dict, yer=None) -> Any:
        a = [pyə(x, icraçı) for x in arqumentlər]
        k = {ad: pyə(x, icraçı) for ad, x in adlı.items()}
        return pydən(self._et(yer, self.obyekt, *a, **k))

    __hash__ = PythonObyekti.__hash__
    __eq__ = PythonObyekti.__eq__


# ═══════════════════════════════════════════════════════════════════════
#  Paket idarəsi — `alqor python qur | siyahı | sil`
# ═══════════════════════════════════════════════════════════════════════

# Dəyər alan pip seçimləri: `--find-links Q` → hər ikisi pip-ə ötürülür
_PIP_DƏYƏRLİ = {"-f", "--find-links", "-i", "--index-url",
                "--extra-index-url", "--platform", "--python-version",
                "--implementation", "--abi", "--only-binary", "--no-binary",
                "-c", "--constraint", "-r", "--requirement", "--proxy",
                "--trusted-host", "--cert", "--timeout", "--retries"}


class PaketXətası(Exception):
    pass


def arqumentləri_ayır(arqumentlər: list[str]) -> tuple[list[str], list[str]]:
    """`[paket..., pip seçimləri...]` → (paketlər, pip seçimləri)."""
    paketlər: list[str] = []
    seçimlər: list[str] = []
    i = 0
    while i < len(arqumentlər):
        a = arqumentlər[i]
        if a == "--":
            seçimlər.extend(arqumentlər[i + 1:])
            break
        if a.startswith("-"):
            seçimlər.append(a)
            if a in _PIP_DƏYƏRLİ and i + 1 < len(arqumentlər):
                seçimlər.append(arqumentlər[i + 1])
                i += 1
        else:
            paketlər.append(a)
        i += 1
    return paketlər, seçimlər


def pip_hazırla(çıxış=print) -> None:
    """pip yoxdursa `ensurepip` ilə quraşdırmağa çalışır."""
    import importlib.util
    import subprocess
    if importlib.util.find_spec("pip") is not None:
        return
    if importlib.util.find_spec("ensurepip") is not None:
        çıxış("… pip tapılmadı — `ensurepip` ilə quraşdırılır")
        r = subprocess.run([sys.executable, "-m", "ensurepip",
                            "--default-pip"], capture_output=True, text=True)
        importlib.invalidate_caches()
        if r.returncode == 0 and importlib.util.find_spec("pip") is not None:
            return
    raise PaketXətası(
        f"pip tapılmadı ({sys.executable}). Quraşdırın: "
        f"`{Path(sys.executable).name} -m ensurepip --upgrade` və ya "
        "əməliyyat sisteminin `python3-pip` paketi")


def paket_qur(qovluq: Path, paketlər: list[str],
              seçimlər: list[str] | None = None, çıxış=print) -> int:
    """`pip install --target python_paketlər/ ...` — pip-in çıxış kodu."""
    import subprocess
    pip_hazırla(çıxış)
    qovluq.mkdir(parents=True, exist_ok=True)
    əmr = [sys.executable, "-m", "pip", "install", "--target", str(qovluq),
           "--upgrade", "--disable-pip-version-check", "--no-input",
           *(seçimlər or []), *paketlər]
    return subprocess.run(əmr).returncode


def _norm(ad: str) -> str:
    import re
    return re.sub(r"[-_.]+", "-", ad).lower()


def _paylamalar(qovluq: Path):
    from importlib import metadata
    if not qovluq.is_dir():
        return []
    return [d for d in metadata.distributions(path=[str(qovluq)])
            if d.metadata["Name"]]


def paket_siyahısı(qovluq: Path) -> list[tuple[str, str]]:
    """Quraşdırılmış paketlər: [(ad, versiya)] — əlifba sırası ilə."""
    return sorted({(d.metadata["Name"], d.version)
                   for d in _paylamalar(qovluq)},
                  key=lambda c: _norm(c[0]))


def paket_sil(qovluq: Path, adlar: list[str]) -> list[str]:
    """
    `pip uninstall` `--target` qovluğunu tanımır — paketin `RECORD`
    siyahısındakı faylları özümüz silirik. Silinən adları qaytarır.
    """
    import shutil
    istənən = {_norm(a) for a in adlar}
    silinən: list[str] = []
    kök = qovluq.resolve()
    for d in _paylamalar(qovluq):
        ad = d.metadata["Name"]
        if _norm(ad) not in istənən:
            continue
        qovluqlar: set[Path] = set()
        for f in d.files or []:
            yol = (kök / str(f)).resolve()
            try:
                yol.relative_to(kök)          # qovluqdan kənara çıxmasın
            except ValueError:
                continue
            if yol.is_file() or yol.is_symlink():
                yol.unlink()
            qovluqlar.update(p for p in yol.parents
                             if p != kök and kök in p.parents)
        for q in sorted(qovluqlar, key=lambda p: len(p.parts), reverse=True):
            if q.name == "__pycache__":
                shutil.rmtree(q, ignore_errors=True)
            try:
                q.rmdir()                     # yalnız boşdursa
            except OSError:
                pass
        info = getattr(d, "_path", None)
        if info is not None and Path(info).exists():
            shutil.rmtree(info, ignore_errors=True)
        silinən.append(ad)
    return silinən
