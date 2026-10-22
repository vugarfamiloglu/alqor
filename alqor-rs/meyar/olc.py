"""Meyar ölçmələri: Python etalonu, Rust ağac icraçısı və Rust VM.

    python3 meyar/olc.py            # alqor-rs qovluğundan; Rust: ağac və VM
    python3 meyar/olc.py --python   # Python etalonunu da ölç (çox yavaşdır)

Hər ölçmə 5 dəfə təkrarlanır, ən kiçik vaxt götürülür.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

KÖK = Path(__file__).resolve().parent
RS = KÖK.parent
B = RS / "target" / "release" / ("alqor-rs.exe" if os.name == "nt" else "alqor-rs")
PY = RS.parent / "alqorc" / "alqorc.py"


def ölç(arq, mühit, n=5):
    ən = None
    çıxış = None
    for _ in range(n):
        t = time.perf_counter()
        r = subprocess.run(arq, capture_output=True, env=dict(os.environ, **mühit))
        v = time.perf_counter() - t
        çıxış = r.stdout
        ən = v if ən is None else min(ən, v)
    return ən, çıxış


def main():
    python = "--python" in sys.argv
    if not B.exists():
        subprocess.run(["cargo", "build", "--release", "-q"], cwd=RS, check=True)
    print(f"{'meyar':<16}{'python':>10}{'ağac':>10}{'vm':>10}{'ağac/vm':>9}")
    for f in sorted(KÖK.glob("*.alq")):
        a, ça = ölç([str(B), "işlət", str(f)], {"ALQOR_VM": "0"})
        v, çv = ölç([str(B), "işlət", str(f)], {"ALQOR_VM": "1"})
        p = None
        if python:
            p, çp = ölç([sys.executable, str(PY), "işlət", str(f)], {}, n=1)
            if çp != ça:
                print(f"  ✖ {f.name}: Python çıxışı fərqlidir")
        if ça != çv:
            print(f"  ✖ {f.name}: VM çıxışı fərqlidir")
        ps = f"{p * 1000:>8.0f}ms" if p is not None else f"{'—':>10}"
        print(f"{f.stem:<16}{ps}{a * 1000:>8.0f}ms{v * 1000:>8.0f}ms{a / v:>8.2f}x")


if __name__ == "__main__":
    main()
