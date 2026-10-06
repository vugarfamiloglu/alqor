"""
`alqorfmt` — Alqor kod formatlayıcısı (spesifikasiya § 13.3).

    python alqorfmt.py .                 qovluqdakı bütün faylları
    python alqorfmt.py --yoxla .         CI: format lazımdırsa kod 1
    python alqorfmt.py --fərq fayl.alqor

`python alqorc.py format …` ilə eynidir.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import alqorc  # noqa: E402  — UTF-8 axınları qurur

if __name__ == "__main__":
    sys.exit(alqorc.əmr_format(sys.argv[1:]))
