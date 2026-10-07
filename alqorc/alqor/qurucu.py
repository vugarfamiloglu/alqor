"""
Alqor — `alqor qur`: tək fayllı paket (`qurma/<ad>.pyz`).

Spesifikasiya § 13.2. Etalon implementasiyada maşın koduna kompilyator
yoxdur; `qur` Python zipapp yaradır:

    qurma/kitab-refi.pyz
    ├── __main__.py         başladıcı
    ├── alqorc.py           CLI (işlət əmri)
    ├── alqor/              icra mühiti (lekser, parser, interpretator…)
    └── layihə/             layihənin faylları (mənbə, şablon, statik…)

İşə salınanda `layihə/` qovluğu bir dəfə keş qovluğuna açılır
(`~/.cache/alqor/<ad>-<həş>/`; `ALQOR_KES` ilə dəyişdirilir), çünki
şablonlar, statik fayllar və `gətir "./x.alq"` həqiqi fayl yolu
gözləyir. Paketin həşi dəyişəndə yeni qovluq yaradılır.

    python kitab-refi.pyz             (Windows, Linux, macOS)
    ./kitab-refi.pyz                  (Linux/macOS — shebang ilə)

Tələb: hədəf kompüterdə Python 3.12+. Quraşdırıcı generatoru (.deb,
AppImage, .exe) bu paketi Python ilə birlikdə bükəcək.
"""

from __future__ import annotations

import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .layihe import Layihə

# Paketə daxil edilməyən qovluqlar (layihə kökünə nisbətən)
XARİC = {"qurma", "sınaq", "sinaq", "test", "sənəd", "paketlər",
         "__pycache__", ".git", ".github", ".idea", ".vscode",
         "node_modules"}

_BAŞLADICI = '''\
# Alqor paketi — `alqor qur` yaradıb. Əl ilə dəyişməyin.
import hashlib
import os
import sys
import zipfile
from pathlib import Path

AD = {ad!r}
GİRİŞ = {giriş!r}


def _keş() -> Path:
    paket = Path(sys.argv[0]).resolve()
    h = hashlib.sha256()
    with open(paket, "rb") as f:
        for parça in iter(lambda: f.read(1 << 20), b""):
            h.update(parça)
    baza = os.environ.get("ALQOR_KES") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.cache"),
        "alqor")
    hədəf = Path(baza) / f"{{AD}}-{{h.hexdigest()[:16]}}"
    if not (hədəf / ".hazir").exists():
        hədəf.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(paket) as z:
            for ad in z.namelist():
                if ad.startswith("layihə/") and not ad.endswith("/"):
                    yol = hədəf / ad[len("layihə/"):]
                    yol.parent.mkdir(parents=True, exist_ok=True)
                    yol.write_bytes(z.read(ad))
        (hədəf / ".hazir").write_text("1")
    return hədəf


def main() -> int:
    import alqorc
    kök = _keş()
    return alqorc.əmr_işlət([str(kök / GİRİŞ), "--", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
'''


@dataclass
class QurmaNəticəsi:
    yol: Path
    ölçü: int
    fayl_sayı: int


def _layihə_faylları(layihə: Layihə) -> list[Path]:
    fayllar: list[Path] = []
    çıxış = layihə.çıxış.resolve()
    for f in sorted(layihə.kök.rglob("*")):
        if not f.is_file():
            continue
        nisbi = f.relative_to(layihə.kök)
        if any(h in XARİC or (h.startswith(".") and h != ".")
               for h in nisbi.parts[:-1]):
            continue
        if f.name.startswith(".") or f.suffix in (".pyz", ".pyc"):
            continue
        try:
            f.resolve().relative_to(çıxış)
            continue
        except ValueError:
            pass
        fayllar.append(f)
    return fayllar


def qur(layihə: Layihə, alqorc_kökü: Path) -> QurmaNəticəsi:
    """`alqorc_kökü` — `alqorc.py` və `alqor/` paketinin olduğu qovluq."""
    if not layihə.giriş.is_file():
        raise FileNotFoundError(
            f"giriş faylı tapılmadı: {layihə.giriş} "
            "(`layihe.alq` → [qurma] giriş)")
    çıxış = layihə.çıxış
    çıxış.mkdir(parents=True, exist_ok=True)
    hədəf = çıxış / f"{layihə.ad}.pyz"
    giriş = layihə.giriş.relative_to(layihə.kök).as_posix()

    say = 0
    müvəqqəti = hədəf.with_suffix(".pyz.yeni")
    with zipfile.ZipFile(müvəqqəti, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("__main__.py",
                   _BAŞLADICI.format(ad=layihə.ad, giriş=giriş))
        z.write(alqorc_kökü / "alqorc.py", "alqorc.py")
        for f in sorted((alqorc_kökü / "alqor").rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            z.write(f, "alqor/" + f.relative_to(
                alqorc_kökü / "alqor").as_posix())
            say += 1
        for f in _layihə_faylları(layihə):
            z.write(f, "layihə/" + f.relative_to(layihə.kök).as_posix())
            say += 1

    # Shebang — Linux/macOS-da birbaşa icra
    məzmun = müvəqqəti.read_bytes()
    hədəf.write_bytes(b"#!/usr/bin/env python3\n" + məzmun)
    müvəqqəti.unlink()
    try:
        hədəf.chmod(hədəf.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP
                    | stat.S_IXOTH)
    except OSError:
        pass
    return QurmaNəticəsi(hədəf, hədəf.stat().st_size, say)


def təmizlə(layihə: Layihə) -> bool:
    """`qurma/` qovluğunu silir — yalnız layihənin içindədirsə."""
    import shutil
    ç = layihə.çıxış.resolve()
    try:
        ç.relative_to(layihə.kök.resolve())
    except ValueError:
        raise ValueError(f"{ç} layihə qovluğunun xaricindədir — silinmədi")
    if ç == layihə.kök.resolve():
        raise ValueError("çıxış qovluğu layihənin kökü ola bilməz")
    if not ç.exists():
        return False
    shutil.rmtree(ç)
    return True

