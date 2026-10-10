"""
Python etalonu ilə `alqor-rs` arasında diferensial müqayisə.

    python -m alqor.rs.muqayise tokenlər [fayl...]   # standart: repo-dakı bütün .alq
    python -m alqor.rs.muqayise tokenlər --korpus    # test_icraci kod parçaları
    python -m alqor.rs.muqayise aac [fayl...]        # AAC çapı + diaqnostika
    python -m alqor.rs.muqayise aac --korpus         # test_icraci kod parçaları
    python -m alqor.rs.muqayise aac --parçalar       # sınaqlarda ayrılan bütün
                                                     # mətnlər (xətalılar daxil)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RS = REPO / "alqor-rs"


def binar(buraxılış: bool = False) -> Path | None:
    """Qurulmuş `alqor-rs` binarı (və ya `ALQOR_RS`)."""
    if os.environ.get("ALQOR_RS"):
        return Path(os.environ["ALQOR_RS"])
    ad = "alqor-rs.exe" if os.name == "nt" else "alqor-rs"
    for q in (("release", "debug") if buraxılış else ("debug", "release")):
        b = RS / "target" / q / ad
        if b.is_file():
            return b
    return None


def qur(buraxılış: bool = False) -> Path | None:
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
    if not Path(cargo).exists() and not shutil.which("cargo"):
        return binar(buraxılış)
    arq = [cargo, "build", "-q"] + (["--release"] if buraxılış else [])
    r = subprocess.run(arq, cwd=RS, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        return None
    return binar(buraxılış)


def _tok_növ(t) -> str:
    return t.növ.name


def python_tokenləri(yol: Path) -> tuple[str, bool]:
    from ..lekser import Lekser
    from ..menbe import Mənbə
    from ..token import KodParçası, Növ
    from ..xeta import XətaToplayıcı
    x = XətaToplayıcı()
    m = Mənbə.fayldan(yol, x)
    if m is None:
        return "", False
    ç = []
    for t in Lekser(m, x).leksə():
        n = t.növ
        if n is Növ.TAM:
            d = str(t.dəyər)
        elif n is Növ.ONLUQ:
            d = _rust_f64(t.dəyər)
        elif n is Növ.BAYT:
            d = "[" + ", ".join(str(b) for b in t.dəyər) + "]"
        elif n is Növ.METN:
            if t.parçalar is not None:
                d = "+".join(
                    "{%d token%s}" % (len(p.tokenlər),
                                      f":{p.format}" if p.format else "")
                    if isinstance(p, KodParçası) else _rust_str(p.dəyər)
                    for p in t.parçalar)
            else:
                d = _rust_str(t.dəyər)
        elif n in (Növ.SIMVOL, Növ.SENED, Növ.DIREKTIV):
            d = _rust_str(t.dəyər)
        elif n in (Növ.SETIR_SONU, Növ.FAYL_SONU):
            d = "" if t.dəyər is None else str(t.dəyər)
        elif n is Növ.JSX:
            d = ""
        else:
            d = str(t.dəyər)
        ç.append(f"{t.yer.sətir}:{t.yer.sütun} {n.name} {d}")
    return "\n".join(ç) + ("\n" if ç else ""), x.uğurludur()


def _rust_str(s: str) -> str:
    """Rust `{:?}` formatı (str üçün)."""
    n = ['"']
    for c in s:
        if c == '"':
            n.append('\\"')
        elif c == "\\":
            n.append("\\\\")
        elif c == "\n":
            n.append("\\n")
        elif c == "\r":
            n.append("\\r")
        elif c == "\t":
            n.append("\\t")
        elif c == "\0":
            n.append("\\0")
        elif ord(c) < 0x20 or ord(c) == 0x7f:
            n.append("\\u{%x}" % ord(c))
        else:
            n.append(c)
    n.append('"')
    return "".join(n)


def _rust_f64(x: float) -> str:
    """Rust `{:?}` formatı (f64)."""
    if x != x:
        return "NaN"
    if x in (float("inf"), float("-inf")):
        return "inf" if x > 0 else "-inf"
    r = repr(x)
    if "e" in r:
        m, e = r.split("e")
        e = int(e)
        if "." not in m:
            m += ".0" if False else ""
        return f"{m}e{e}"
    return r


def python_aac(yol: Path) -> tuple[str, bool]:
    from ..lekser import Lekser
    from ..menbe import Mənbə
    from ..parser import Parser
    from ..xeta import XətaToplayıcı
    from .aac_capi import aac_çapı
    x = XətaToplayıcı()
    m = Mənbə.fayldan(yol, x)
    if m is None:
        return "", False
    p = Parser(Lekser(m, x).leksə(), m, x).ayır()
    return aac_çapı(p), x.uğurludur()


def rust_aac(b: Path, yol: Path) -> tuple[str, bool]:
    r = subprocess.run([str(b), "aac", str(yol)], capture_output=True)
    return r.stdout.decode("utf-8", "replace"), r.returncode == 0


def rust_tokenləri(b: Path, yol: Path) -> tuple[str, bool]:
    r = subprocess.run([str(b), "tokenlər", str(yol)], capture_output=True)
    return r.stdout.decode("utf-8", "replace"), r.returncode == 0


def bütün_alq() -> list[Path]:
    return sorted(p for p in REPO.rglob("*.alq")
                  if "target" not in p.parts and "qurma" not in p.parts
                  and ".git" not in p.parts)


def korpus() -> list[dict]:
    """`test_icraci` kod parçaları: (kod, giriş, çıxış, xəta) — etalon."""
    import io
    import unittest
    sys.path.insert(0, str(REPO / "alqorc"))
    from sinaq import test_icraci as T
    qeyd: list[dict] = []
    orijinal = T.işlət

    def yazan(kod, giriş=None):
        s, x = orijinal(kod, giriş)
        qeyd.append({"kod": kod, "giriş": list(giriş or []),
                     "çıxış": list(s), "xəta": x.tip if x else None})
        return s, x

    T.işlət = yazan
    try:
        unittest.TextTestRunner(stream=io.StringIO()).run(
            unittest.TestLoader().loadTestsFromModule(T))
    finally:
        T.işlət = orijinal
    görülən: set[str] = set()
    n = []
    for q in qeyd:
        if q["kod"] not in görülən:
            görülən.add(q["kod"])
            n.append(q)
    return n


def korpus_faylları(q: Path) -> list[Path]:
    q.mkdir(parents=True, exist_ok=True)
    n = []
    for i, k in enumerate(korpus()):
        f = q / f"k{i:04d}.alq"
        f.write_text(k["kod"], encoding="utf-8")
        n.append(f)
    return n


def main(a: list[str]) -> int:
    if not a or a[0] not in ("tokenlər", "tokenler", "aac"):
        print(__doc__)
        return 3
    b = qur()
    if b is None:
        print("alqor-rs qurulmadı", file=sys.stderr)
        return 2
    import tempfile
    if a[1:] == ["--korpus"]:
        fayllar = korpus_faylları(Path(tempfile.mkdtemp(prefix="alqor-rs-")))
    else:
        fayllar = [Path(x) for x in a[1:]] or bütün_alq()
    py, rs = ((python_aac, rust_aac) if a[0] == "aac"
              else (python_tokenləri, rust_tokenləri))
    pis = müqayisə_et(b, fayllar, py, rs)
    print(f"{len(fayllar) - pis}/{len(fayllar)} fayl eyni")
    return 1 if pis else 0


def müqayisə_et(b: Path, fayllar: list[Path], py, rs,
                çıxış=print) -> int:
    """Fərqli faylların sayı; hər fərq üçün ilk fərqli sətir çap olunur."""
    pis = 0
    for f in fayllar:
        p, pu = py(f)
        r, ru = rs(b, f)
        if p != r or pu != ru:
            pis += 1
            ps, rsl = p.splitlines(), r.splitlines()
            i = next((i for i, (x, y) in enumerate(zip(ps, rsl)) if x != y),
                     min(len(ps), len(rsl)))
            çıxış(f"✖ {f}: "
                  f"sətir {i + 1}\n    py: {ps[i] if i < len(ps) else '—'}\n"
                  f"    rs: {rsl[i] if i < len(rsl) else '—'}"
                  + ("" if pu == ru else f"\n    uğur: py={pu} rs={ru}"))
    return pis


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
