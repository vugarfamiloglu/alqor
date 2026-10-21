"""
Python etalonu ilə `alqor-rs` arasında diferensial müqayisə.

    python -m alqor.rs.muqayise tokenlər [fayl...]   # standart: repo-dakı bütün .alq
    python -m alqor.rs.muqayise tokenlər --korpus    # test_icraci kod parçaları
    python -m alqor.rs.muqayise aac --mənbələr --diaq
        # sınaqlarda parserə verilən bütün mənbələr, xəta mesajları ilə
    python -m alqor.rs.muqayise aac [fayl...]        # AAC çapı + diaqnostika
    python -m alqor.rs.muqayise aac --korpus         # test_icraci kod parçaları
    python -m alqor.rs.muqayise aac --parçalar       # sınaqlarda ayrılan bütün
                                                     # mətnlər (xətalılar daxil)
    python -m alqor.rs.muqayise işlət --korpus       # test_icraci parçalarını icra:
                                                     # stdout sətirləri + xəta tipi
    python -m alqor.rs.muqayise işlət [fayl...]      # proqramlar (standart: js_numuneler
                                                     # və numuneler): stdout + çıxış kodu
    python -m alqor.rs.muqayise işlət --parçalar     # sinaq/rs_icra_parcalari.alq:
                                                     # stdout + stderr + çıxış kodu
    python -m alqor.rs.muqayise wasm                 # WebAssembly paketi (node) yerli
                                                     # binarla eyni nəticə verir
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


def python_aac_diaq(yol: Path) -> tuple[str, bool]:
    """AAC + diaqnostikalar (`alqor-rs aac --diaq` formatı)."""
    from ..lekser import Lekser
    from ..menbe import Mənbə
    from ..parser import Parser
    from ..xeta import XətaToplayıcı
    from .aac_capi import aac_çapı, diaq_çapı
    x = XətaToplayıcı()
    m = Mənbə.fayldan(yol, x)
    if m is None:
        return "", False
    p = Parser(Lekser(m, x).leksə(), m, x).ayır()
    return aac_çapı(p) + "## diaqnostika\n" + diaq_çapı(x), x.uğurludur()


def rust_aac_diaq(b: Path, yol: Path) -> tuple[str, bool]:
    r = subprocess.run([str(b), "aac", str(yol), "--diaq"],
                       capture_output=True)
    return r.stdout.decode("utf-8", "replace"), r.returncode == 0


#  Mənbə korpusu üçün işlədilən sınaq modulları
MƏNBƏ_SINAQLARI = ("test_icraci", "test_tipyoxlayici", "test_lekser",
                   "test_beledci", "test_konsol", "test_alqorfmt",
                   "test_alqorlint", "test_modullar", "test_spesifikasiya")


def mənbə_korpusu() -> list[str]:
    """Sınaqlar işləyərkən parserə verilən bütün mənbələr (xətalılar da)."""
    import io
    import importlib
    import unittest
    sys.path.insert(0, str(REPO / "alqorc"))
    from .. import parser as P
    görülən: dict[str, None] = {}
    orijinal = P.Parser.ayır

    def yazan(self):
        görülən.setdefault(self.s.mətn, None)
        return orijinal(self)
    P.Parser.ayır = yazan
    try:
        for ad in MƏNBƏ_SINAQLARI:
            try:
                m = importlib.import_module(f"sinaq.{ad}")
            except ImportError:
                continue
            unittest.TextTestRunner(stream=io.StringIO()).run(
                unittest.TestLoader().loadTestsFromModule(m))
    finally:
        P.Parser.ayır = orijinal
    return list(görülən)


def mənbə_faylları(q: Path) -> list[Path]:
    q.mkdir(parents=True, exist_ok=True)
    n = []
    for i, m in enumerate(mənbə_korpusu()):
        f = q / f"m{i:05d}.alq"
        f.write_text(m, encoding="utf-8")
        n.append(f)
    return n


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


# ═══════════════════════════════════════════════════════════════════════
#  İcra müqayisəsi (`işlət`)
# ═══════════════════════════════════════════════════════════════════════

#  Proqramlara verilən standart giriş (fayl adı → stdin)
GİRİŞLƏR = {
    "konsol.alq": "\nmavi\nx\nhə\n3,1\n",
    "01-salam.alq": "Aysel\n21\n",
    "03-kalkulyator.alq": "2 + 3\n10 / 4\n7 * 6\nçıx\n",
}

#  Proqramlara verilən arqumentlər (`-- …`)
ARQUMENTLƏR = {
    "07-fayl-emali.alq": ["../README.md"],
}

#  Qrafik/veb mühit tələb edən nümunələr — müqayisə olunmur; Python
#  kitabxanaları (`gətir python:…`) yalnız Python icraçısındadır
İSTİSNA_SÖZLƏR = ("veb", "pəncərə", "vidjet", "python")


def _mühit() -> dict:
    m = dict(os.environ)
    m["ALQOR_RENG"] = "0"
    m["NO_COLOR"] = "1"
    m["PYTHONIOENCODING"] = "utf-8"
    m["PYTHONHASHSEED"] = "0"
    return m


def _xəta_tipi(stderr: str) -> str | None:
    """`✖ ALQ-R004  BoşDəyərXətası: ...` → `BoşDəyərXətası`"""
    import re
    m = re.search(r"✖ ALQ-\S+\s+(\S+?):", stderr)
    return m.group(1) if m else None


def _çıxış(r) -> tuple[str, str, int]:
    """Windows-da Python mətn axını `\\r\\n` yazır — sətir sonları eyniləşdirilir."""
    oxu = lambda b: b.decode("utf-8", "replace").replace("\r\n", "\n")  # noqa: E731
    return oxu(r.stdout), oxu(r.stderr), r.returncode


def rust_işlət(b: Path, yol: Path, giriş: str = "",
               arq: list[str] | None = None) -> tuple[str, str, int]:
    r = subprocess.run([str(b), "işlət", str(yol), "--", *(arq or [])],
                       input=giriş.encode("utf-8"), capture_output=True,
                       env=_mühit(), cwd=yol.parent, timeout=120)
    return _çıxış(r)


def python_işlət(yol: Path, giriş: str = "",
                 arq: list[str] | None = None) -> tuple[str, str, int]:
    r = subprocess.run([sys.executable, str(REPO / "alqorc" / "alqorc.py"),
                        "işlət", str(yol), "--", *(arq or [])],
                       input=giriş.encode("utf-8"), capture_output=True,
                       env=_mühit(), cwd=yol.parent, timeout=300)
    return _çıxış(r)


def proqramlar() -> list[Path]:
    """İcra müqayisəsinə daxil olan nümunə proqramlar."""
    n = sorted((REPO / "alqorc" / "sinaq" / "js_numuneler").glob("*.alq"))
    for p in sorted((REPO / "numuneler").glob("*.alq")):
        mətn = p.read_text(encoding="utf-8")
        if any(f"gətir {s}" in mətn or f"{s}." in mətn
               for s in İSTİSNA_SÖZLƏR):
            continue
        n.append(p)
    return n


def korpus_işlət(b: Path, çıxış=print) -> tuple[int, int]:
    """test_icraci korpusu: (eyni, cəmi)."""
    import tempfile
    q = Path(tempfile.mkdtemp(prefix="alqor-rs-isl-"))
    k = korpus()
    eyni = 0
    for i, x in enumerate(k):
        f = q / f"k{i:04d}.alq"
        f.write_text(x["kod"], encoding="utf-8")
        giriş = "".join(s + "\n" for s in x["giriş"])
        try:
            o, e, kod = rust_işlət(b, f, giriş)
        except subprocess.TimeoutExpired:
            çıxış(f"✖ {f}: vaxt bitdi")
            continue
        sətirlər = o.split("\n")
        if sətirlər and sətirlər[-1] == "":
            sətirlər.pop()
        gözlənilən = "\n".join(x["çıxış"]).split("\n") if x["çıxış"] else []
        tip = _xəta_tipi(e) if kod != 0 else None
        if sətirlər == gözlənilən and tip == x["xəta"]:
            eyni += 1
            continue
        j = next((j for j, (a, c) in enumerate(zip(gözlənilən, sətirlər))
                  if a != c), min(len(gözlənilən), len(sətirlər)))
        çıxış(f"✖ {f}: sətir {j + 1}\n"
              f"    py: {gözlənilən[j] if j < len(gözlənilən) else '—'}\n"
              f"    rs: {sətirlər[j] if j < len(sətirlər) else '—'}"
              + ("" if tip == x["xəta"]
                 else f"\n    xəta: py={x['xəta']} rs={tip} {e.strip()[:300]}"))
    return eyni, len(k)


def proqram_işlət(b: Path, fayllar: list[Path], çıxış=print) -> int:
    """Proqramlar: stdout + çıxış kodu. Fərqli faylların sayı."""
    pis = 0
    for f in fayllar:
        giriş = GİRİŞLƏR.get(f.name, "")
        arq = ARQUMENTLƏR.get(f.name)
        po, pe, pk = python_işlət(f, giriş, arq)
        ro, re_, rk = rust_işlət(b, f, giriş, arq)
        # Python `paralel`/`başlat` sapları çıxışı bəzən qarışdırır —
        # fərq olarsa etalonu bir neçə dəfə təkrar işlədirik
        for _ in range(3):
            if po == ro and pk == rk:
                break
            po, pe, pk = python_işlət(f, giriş, arq)
        if po == ro and pk == rk:
            continue
        pis += 1
        ps, rsl = po.splitlines(), ro.splitlines()
        i = next((i for i, (x, y) in enumerate(zip(ps, rsl)) if x != y),
                 min(len(ps), len(rsl)))
        çıxış(f"✖ {f}: sətir {i + 1}\n"
              f"    py: {ps[i] if i < len(ps) else '—'}\n"
              f"    rs: {rsl[i] if i < len(rsl) else '—'}"
              + ("" if pk == rk else f"\n    kod: py={pk} rs={rk} {re_.strip()[:300]}"))
    return pis


PARÇALAR = REPO / "alqorc" / "sinaq" / "rs_icra_parcalari.alq"


def parçalar_işlət(b: Path, fayl: Path = PARÇALAR,
                   çıxış=print) -> tuple[int, int]:
    """`=====` ilə ayrılmış parçalar: stdout, stderr və kod tam eyni olmalıdır."""
    import tempfile
    q = Path(tempfile.mkdtemp(prefix="alqor-rs-par-"))
    parçalar = fayl.read_text(encoding="utf-8").split("=====\n")
    eyni = 0
    for k, kod in enumerate(parçalar):
        f = q / f"p{k:03d}.alq"
        f.write_text(kod, encoding="utf-8")
        giriş, arq = "bir\niki\n", ["x", "y"]
        py = python_işlət(f, giriş, arq)
        rs = rust_işlət(b, f, giriş, arq)
        if py == rs:
            eyni += 1
            continue
        çıxış(f"✖ parça #{k} ({f}): kod py={py[2]} rs={rs[2]}")
        for ad, x, y in (("stdout", py[0], rs[0]), ("stderr", py[1], rs[1])):
            x, y = x.splitlines(), y.splitlines()
            if x != y:
                i = next((i for i, (m, n) in enumerate(zip(x, y)) if m != n),
                         min(len(x), len(y)))
                çıxış(f"    {ad} py: {x[i] if i < len(x) else '—'}\n"
                      f"    {ad} rs: {y[i] if i < len(y) else '—'}")
    return eyni, len(parçalar)


WASM = RS / "wasm" / "alqor.wasm"


def wasm_qur() -> Path | None:
    """`wasm/alqor.wasm`-ı qurur (wasm32 hədəfi quraşdırılıbsa)."""
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
    if not Path(cargo).exists():
        return WASM if WASM.is_file() else None
    rustup = Path(cargo).with_name("rustup")
    if rustup.exists():
        r = subprocess.run([str(rustup), "target", "list", "--installed"],
                           capture_output=True, text=True)
        if "wasm32-unknown-unknown" not in r.stdout:
            return WASM if WASM.is_file() else None
    env = dict(os.environ,
               RUSTFLAGS="-C link-arg=-zstack-size=33554432",
               PATH=str(Path(cargo).parent) + os.pathsep + os.environ.get("PATH", ""))
    r = subprocess.run([cargo, "rustc", "-q", "--lib", "--crate-type", "cdylib",
                        "--target", "wasm32-unknown-unknown", "--profile", "wasm"],
                       cwd=RS, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        return None
    shutil.copy(RS / "target" / "wasm32-unknown-unknown" / "wasm" / "deps"
                / "alqor.wasm", WASM)
    return WASM


def node_tap() -> str | None:
    return shutil.which("node") or next(
        (str(p) for p in Path("/opt").glob("node*/bin/node") if p.is_file()), None)


def wasm_işlət(node: str, fayl: Path) -> list[tuple[str, str, int]]:
    """`=====` parçalarını wasm paketi ilə icra edir."""
    import json
    r = subprocess.run([node, str(RS / "wasm" / "sina.mjs"), "--parçalar",
                        str(fayl)], capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace"))
    n = []
    for s in r.stdout.decode("utf-8").splitlines():
        d = json.loads(s)
        n.append((d["stdout"], d["stderr"], d["kod"]))
    return n


#  wasm-da işləməyən parçalar (fayl sistemi, mühit, platforma)
WASM_İSTİSNA = ("fayl.", "sistem.", "konsol.terminaldır", "vaxt.")


def wasm_müqayisə(b: Path, node: str, fayl: Path = PARÇALAR,
                  çıxış=print) -> tuple[int, int]:
    """WebAssembly nəticəsi yerli binarla eyni olmalıdır (fayl adı istisna)."""
    import tempfile
    q = Path(tempfile.mkdtemp(prefix="alqor-wasm-"))
    parçalar = fayl.read_text(encoding="utf-8").split("=====\n")
    wn = wasm_işlət(node, fayl)
    eyni = cəmi = 0
    for k, (kod, w) in enumerate(zip(parçalar, wn)):
        if any(x in kod for x in WASM_İSTİSNA):
            continue
        cəmi += 1
        f = q / "proqram.alq"
        f.write_text(kod, encoding="utf-8")
        r = rust_işlət(b, f, "bir\niki\n")
        if r == w:
            eyni += 1
            continue
        çıxış(f"✖ wasm parça #{k}: kod yerli={r[2]} wasm={w[2]}\n"
              f"    yerli: {(r[0] + r[1])[-300:]!r}\n    wasm:  {(w[0] + w[1])[-300:]!r}")
    return eyni, cəmi


def main(a: list[str]) -> int:
    if a and a[0] == "wasm":
        b, node = qur(), node_tap()
        if not WASM.is_file():
            wasm_qur()
        if b is None or node is None or not WASM.is_file():
            print("alqor-rs, node və ya wasm/alqor.wasm yoxdur", file=sys.stderr)
            return 2
        eyni, cəmi = wasm_müqayisə(b, node)
        print(f"{eyni}/{cəmi} parça eyni (wasm)")
        return 0 if eyni == cəmi else 1
    if a and a[0] in ("işlət", "islet"):
        b = qur()
        if b is None:
            print("alqor-rs qurulmadı", file=sys.stderr)
            return 2
        if a[1:] == ["--korpus"]:
            eyni, cəmi = korpus_işlət(b)
            print(f"{eyni}/{cəmi} parça eyni")
            return 0 if eyni == cəmi else 1
        if a[1:2] == ["--parçalar"]:
            eyni, cəmi = parçalar_işlət(
                b, Path(a[2]) if len(a) > 2 else PARÇALAR)
            print(f"{eyni}/{cəmi} parça eyni")
            return 0 if eyni == cəmi else 1
        fayllar = [Path(x).resolve() for x in a[1:]] or proqramlar()
        pis = proqram_işlət(b, fayllar)
        print(f"{len(fayllar) - pis}/{len(fayllar)} proqram eyni")
        return 1 if pis else 0
    if not a or a[0] not in ("tokenlər", "tokenler", "aac"):
        print(__doc__)
        return 3
    b = qur()
    if b is None:
        print("alqor-rs qurulmadı", file=sys.stderr)
        return 2
    import tempfile
    diaq = "--diaq" in a
    a = [x for x in a if x != "--diaq"]
    if a[1:] == ["--korpus"]:
        fayllar = korpus_faylları(Path(tempfile.mkdtemp(prefix="alqor-rs-")))
    elif a[1:] == ["--mənbələr"] or a[1:] == ["--menbeler"]:
        fayllar = mənbə_faylları(Path(tempfile.mkdtemp(prefix="alqor-rs-")))
    else:
        fayllar = [Path(x) for x in a[1:]] or bütün_alq()
    if a[0] == "aac":
        py, rs = (python_aac_diaq, rust_aac_diaq) if diaq else \
            (python_aac, rust_aac)
    else:
        py, rs = python_tokenləri, rust_tokenləri
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
