"""
İcra motorunun seçimi: Python icraçısı (`py`) və ya Rust icraçısı
(`alqor-rs`, `rs`).

    alqor işlət proqram.alq                 # standart: ALQOR_MOTOR və ya `py`
    alqor işlət --motor rs proqram.alq      # həmişə alqor-rs
    alqor işlət --motor avto proqram.alq    # mümkünsə alqor-rs, yoxsa Python

`avto` proqramı İCRA ETMƏDƏN yoxlayır: bütün `gətir` cümlələri (yerli
`.alq` modulları da rekursiv) Rust icraçısının dəstəklədiyi modullara
aiddirsə və proqram yalnız Python-da olan qlobal adları (`pəncərə`,
`vidjet` …) işlətmirsə, `alqor-rs` seçilir. Əks halda — və ya binar
tapılmasa — Python icraçısı işləyir.

`alqor-rs` binarı belə axtarılır:
  1. `ALQOR_RS` mühit dəyişəni (binarın tam yolu);
  2. quraşdırma: `<kök>/bin/alqor-rs[.exe]` (alqorc/ qovluğunun yanında);
  3. repo: `alqor-rs/target/{release,debug}/` — ən son qurulanı.
"""

from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

MOTORLAR = ("py", "rs", "avto")

# Rust icraçısında hələ olmayan üzvlər (modul → üzv adları). Proqram
# modulu işlədir və bu adda üzvə müraciət edirsə — Python icraçısı.
RS_ƏSKİK_ÜZVLƏR: dict[str, frozenset[str]] = {
    "veb": frozenset({"komponent", "soket"}),
    "http": frozenset({"vebSoket"}),
}

_ALQORC = Path(__file__).resolve().parents[1]          # alqorc/
_KÖK = _ALQORC.parent                                   # quraşdırma / repo kökü
_AD = "alqor-rs.exe" if os.name == "nt" else "alqor-rs"


def binar() -> Path | None:
    """İstifadə olunacaq `alqor-rs` binarı (tapılmasa None)."""
    m = os.environ.get("ALQOR_RS")
    if m:
        p = Path(m)
        return p if p.is_file() else None
    q = _KÖK / "bin" / _AD
    if q.is_file():
        return q
    # Repo: ən son qurulan (release və ya debug)
    namizədlər = [p for p in (_KÖK / "alqor-rs" / "target" / "release" / _AD,
                              _KÖK / "alqor-rs" / "target" / "debug" / _AD)
                  if p.is_file()]
    if not namizədlər:
        return None
    return max(namizədlər, key=lambda p: p.stat().st_mtime)


@lru_cache(maxsize=None)
def _sorğu(b: str, əmr: str) -> frozenset[str]:
    try:
        r = subprocess.run([b, əmr], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    if r.returncode != 0:
        return frozenset()
    return frozenset(s.strip() for s in
                     r.stdout.decode("utf-8", "replace").splitlines()
                     if s.strip())


def rs_modulları(b: Path) -> frozenset[str]:
    """`alqor-rs modullar` — Rust icraçısının dəstəklədiyi modullar."""
    return _sorğu(str(b), "modullar")


def rs_qlobalları(b: Path) -> frozenset[str]:
    return _sorğu(str(b), "qloballar")


@lru_cache(maxsize=None)
def py_qlobalları() -> frozenset[str]:
    from .icraci import İcraçı
    return frozenset(İcraçı().qlobal.adlar)


def motor_tap(arqumentlər: list[str]) -> str | None:
    """`--motor X` / `--motor=X` → X; yoxdursa `ALQOR_MOTOR` və ya None."""
    for k, a in enumerate(arqumentlər):
        if a == "--motor" and k + 1 < len(arqumentlər):
            return arqumentlər[k + 1]
        if a.startswith("--motor="):
            return a.split("=", 1)[1]
    return os.environ.get("ALQOR_MOTOR") or None


# ═══════════════════════════════════════════════════════════════════════
#  Statik yoxlama
# ═══════════════════════════════════════════════════════════════════════

def _gəz(düyün, ziyarət):
    """AAC-nin bütün düyünlərini gəzir (dataclass sahələri üzrə)."""
    yığın = [düyün]
    while yığın:
        d = yığın.pop()
        if isinstance(d, (list, tuple)):
            yığın.extend(d)
            continue
        if not dataclasses.is_dataclass(d) or isinstance(d, type):
            continue
        ziyarət(d)
        for f in dataclasses.fields(d):
            v = getattr(d, f.name, None)
            if isinstance(v, (list, tuple)) or (
                    dataclasses.is_dataclass(v) and not isinstance(v, type)):
                yığın.append(v)


def _ayır(yol: Path):
    from .lekser import Lekser
    from .menbe import Mənbə
    from .parser import Parser
    from .xeta import XətaToplayıcı
    x = XətaToplayıcı()
    s = Mənbə.fayldan(str(yol), x)
    if s is None:
        return None
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    return ağac if x.uğurludur() else None


def rs_uyğunluğu(ağac, yol: Path | None, b: Path) -> str | None:
    """
    Proqram Rust icraçısında işləyə bilərmi? `None` — bəli; əks halda
    səbəb (məs. "`yaml` modulu Rust icraçısında yoxdur").
    """
    from . import aac as A
    modullar = rs_modulları(b)
    if not modullar:
        return "`alqor-rs modullar` cavab vermədi"
    yalnız_py = py_qlobalları() - rs_qlobalları(b)
    baxılan: set[Path] = set()

    def yoxla(ağac, baza: Path | None) -> str | None:
        səbəb: list[str] = []

        işlənən: set[str] = set()
        üzvlər: set[str] = set()

        def ziyarət(d):
            if səbəb:
                return
            if isinstance(d, A.İdxal):
                səbəb.extend(_idxal(d, baza))
                if d.yol:
                    işlənən.add(d.yol[0])
            elif isinstance(d, A.Ad):
                if d.ad in yalnız_py:
                    səbəb.append(f"`{d.ad}` Rust icraçısında yoxdur")
                işlənən.add(d.ad)
            elif isinstance(d, A.Üzv):
                üzvlər.add(d.ad)
            elif isinstance(d, A.TipAdı) and d.yol:
                if d.yol[0] in yalnız_py:
                    səbəb.append(f"`{d.yol[0]}` Rust icraçısında yoxdur")
                işlənən.add(d.yol[0])

        def _idxal(d, baza):
            if getattr(d, "python", False):
                return [f"`gətir python:{'.'.join(d.yol)}` yalnız Python "
                        "icraçısında"]
            if d.mətn_yolu is not None:
                p = Path(d.mətn_yolu)
                if not p.is_absolute() and baza is not None:
                    p = baza / p
                if not p.exists():
                    for u in (".alq", ".alqor"):
                        if Path(f"{p}{u}").is_file():
                            p = Path(f"{p}{u}")
                            break
                if not p.is_file():
                    return [f"`{d.mətn_yolu}` modulu (qovluq/paket) yalnız "
                            "Python icraçısında"]
                p = p.resolve()
                if p in baxılan:
                    return []
                baxılan.add(p)
                alt = _ayır(p)
                if alt is None:
                    return [f"`{d.mətn_yolu}` ayrıla bilmədi"]
                s = yoxla(alt, p.parent)
                return [s] if s else []
            ad = ".".join(d.yol)
            if not d.yol or ":" in ad:
                return [f"`gətir {ad}` Rust icraçısında yoxdur"]
            if d.yol[0] in modullar:
                return []
            return [f"`{ad}` modulu Rust icraçısında yoxdur"]

        _gəz(ağac, ziyarət)
        if not səbəb:
            for m, adlar in RS_ƏSKİK_ÜZVLƏR.items():
                if m in işlənən and adlar & üzvlər:
                    ad = sorted(adlar & üzvlər)[0]
                    səbəb.append(f"`{m}` modulunun `{ad}` üzvü Rust "
                                 "icraçısında yoxdur")
        return səbəb[0] if səbəb else None

    return yoxla(ağac, yol.resolve().parent if yol is not None else None)


def seç(motor: str, ağac, yol: Path | None) -> tuple[str, Path | None, str]:
    """(motor, binar, səbəb) — `motor` `py` və ya `rs`."""
    if motor == "py":
        return "py", None, ""
    b = binar()
    if b is None:
        return "py", None, "alqor-rs binarı tapılmadı"
    if motor == "rs":
        return "rs", b, ""
    səbəb = rs_uyğunluğu(ağac, yol, b)
    if səbəb:
        return "py", None, səbəb
    return "rs", b, ""


def rs_işlət(b: Path, yol: str, proqram_arqumentləri: list[str],
             mətn: str | None = None) -> int:
    """`alqor-rs işlət` — stdin/stdout/stderr ötürülür, çıxış kodu qaytarılır."""
    sys.stdout.flush()
    sys.stderr.flush()
    arq = [str(b), "işlət", yol, "--", *proqram_arqumentləri]
    try:
        if mətn is not None:
            r = subprocess.run(arq, input=mətn.encode("utf-8"))
            return r.returncode
        return subprocess.call(arq)
    except KeyboardInterrupt:
        return 130
