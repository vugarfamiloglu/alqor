"""
`alqor qur --exe` — proqramı tək Windows `.exe` faylına çevirir.

Nəticə Alqor quraşdırılmamış kompüterdə də işləyir: `.exe`-nin içində
Python və proqram var. Quruluş:

    [başladıcı (Rust, ~350 KB)][yük: Python + tətbiq.pyz][izləyici]

İlk işə salınmada yük `%LOCALAPPDATA%\\Alqor\\tetbiqler\\<ad>-<id>\\`
qovluğuna açılır (bir neçə saniyə), sonra hər dəfə dərhal işləyir.
Başladıcının mənbəyi: `alqor-rs/baslatici/`.

Konsol və ya pəncərə:
  • `gətir pəncərə` / `gətir vidjet` olan proqram — konsolsuz (pəncərə)
  • qalanları — konsol proqramı
  • `layihe.alq` → `[quraşdırıcı] konsol = doğru|yanlış` və ya
    `--konsol` / `--pəncərə` bayrağı ilə dəyişdirilir
"""

from __future__ import annotations

import hashlib
import re
import struct
import zlib
from pathlib import Path

from . import qurucu

RESURSLAR = Path(__file__).parent / "resurslar"
SEHR = b"ALQPAK01"
İZ = b"ALQORPAK"

#  Python-un tətbiqə lazım olmayan hissələri — ölçünü azaldır
_ATLA = re.compile(r"(^|/)(__pycache__|test|tests|idlelib|ensurepip|"
                   r"lib2to3|turtledemo|pydoc_data)(/|$)|\.pdb$|/_test")


def konsoldurmu(layihə) -> bool:
    q = layihə.məlumat.get("quraşdırıcı") or {}
    if "konsol" in q:
        return bool(q["konsol"])
    for f in layihə.kök.rglob("*.alq"):
        if "qurma" in f.parts or "paketlər" in f.parts:
            continue
        try:
            m = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"^\s*gətir\s+(pəncərə|vidjet)\b", m, re.M):
            return False
    return True


def python_qovluğu(alqorc_kökü: Path, keş: Path | None = None) -> Path:
    """Windows Python-u: quraşdırılmış Alqor-un özününkü və ya endirilən."""
    quraşdırılmış = alqorc_kökü.parent / "python"
    if (quraşdırılmış / "python.exe").is_file():
        return quraşdırılmış
    from .windows_paylama import python_daxil_et
    keş = keş or Path.home() / ".cache" / "alqor"
    hədəf = keş / "windows-python"
    if not (hədəf / "python.exe").is_file():
        python_daxil_et(hədəf, keş)
    return hədəf


def _yük(ad: str, id_: str, giriş: str,
         fayllar: list[tuple[str, bytes]]) -> bytes:
    def mətn(s: str) -> bytes:
        b = s.encode("utf-8")
        return struct.pack("<I", len(b)) + b

    hissələr = [SEHR, struct.pack("<I", len(fayllar)), mətn(ad), mətn(id_),
                mətn(giriş)]
    for yol, məzmun in fayllar:
        c = zlib.compressobj(6, zlib.DEFLATED, -15)
        sıxılmış = c.compress(məzmun) + c.flush()
        if len(sıxılmış) >= len(məzmun):
            sıxılmış = məzmun                 # sıxılmır — olduğu kimi
        hissələr += [mətn(yol), struct.pack("<QQ", len(məzmun), len(sıxılmış)),
                     sıxılmış]
    return b"".join(hissələr)


def exe_yarat(pyz: Path, hədəf: Path, ad: str, python: Path,
              konsol: bool = True) -> Path:
    """`pyz` + `python/` → tək `.exe`."""
    fayllar: list[tuple[str, bytes]] = []
    for f in sorted(python.rglob("*")):
        nisbi = f.relative_to(python).as_posix()
        if f.is_file() and not _ATLA.search(nisbi):
            fayllar.append((f"python/{nisbi}", f.read_bytes()))
    pyz_baytlar = pyz.read_bytes()
    fayllar.append(("tetbiq.pyz", pyz_baytlar))
    h = hashlib.sha256(pyz_baytlar)
    h.update(str(len(fayllar)).encode())
    id_ = h.hexdigest()[:16]
    təhlükəsiz_ad = re.sub(r"[^A-Za-z0-9_.-]+", "-",
                           ad.translate(str.maketrans("əıöüğşçƏİÖÜĞŞÇ",
                                                      "eiougscEIOUGSC"))) or "tetbiq"
    başladıcı = (RESURSLAR / ("baslatici-konsol.exe" if konsol
                              else "baslatici-pencere.exe")).read_bytes()
    yük = _yük(təhlükəsiz_ad, id_, "tetbiq.pyz", fayllar)
    hədəf.parent.mkdir(parents=True, exist_ok=True)
    müvəqqəti = hədəf.with_suffix(".exe.yeni")
    with open(müvəqqəti, "wb") as f:
        f.write(başladıcı)
        f.write(yük)
        f.write(struct.pack("<Q", len(başladıcı)) + İZ)
    müvəqqəti.replace(hədəf)
    return hədəf


class QurmaXətası(RuntimeError):
    pass


def sintaksisi_yoxla(layihə) -> None:
    """Xətalı proqram `.exe`-yə çevrilməsin — xəta qurmada görünsün."""
    from .lekser import Lekser
    from .menbe import Mənbə
    from .parser import Parser
    from .xeta import XətaToplayıcı
    fayllar = [layihə.giriş] + [
        f for f in sorted((layihə.kök / "mənbə").rglob("*.alq"))
        if f != layihə.giriş] if (layihə.kök / "mənbə").is_dir() \
        else [layihə.giriş]
    for f in fayllar:
        x = XətaToplayıcı()
        m = Mənbə.fayldan(f, x)
        if m is not None:
            Parser(Lekser(m, x).leksə(), m, x).ayır()
        if not x.uğurludur():
            raise QurmaXətası("proqramda xəta var:\n\n" + x.hesabat())


def qur(layihə, alqorc_kökü: Path, konsol: bool | None = None) -> Path:
    sintaksisi_yoxla(layihə)
    n = qurucu.qur(layihə, alqorc_kökü)
    if konsol is None:
        konsol = konsoldurmu(layihə)
    return exe_yarat(n.yol, layihə.çıxış / f"{layihə.ad}.exe", layihə.ad,
                     python_qovluğu(alqorc_kökü), konsol)
