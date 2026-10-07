"""
`sıxma` — gzip, zip, tar (§ 10.17).

    gətir sıxma

    dəyişən b = sıxma.gzipSıx("çox uzun mətn ...")      // bayt
    yaz(sıxma.gzipAçMətn(b))

    sıxma.zipYarat("arxiv.zip", ["hesabat.pdf", "şəkillər/"])
    sıxma.zipAç("arxiv.zip", "çıxış/")
    hər f üçün sıxma.zipSiyahı("arxiv.zip") içində
        yaz(f["ad"], f["ölçü"])
    son

    sıxma.tarYarat("ehtiyat.tar.gz", ["layihə/"])
    sıxma.tarAç("ehtiyat.tar.gz", "bərpa/")

Təhlükəsizlik: açarkən arxivdən hədəf qovluqdan kənara çıxan yollar
(`../../etc/passwd`, mütləq yollar, simvolik keçidlər) rədd edilir.
"""

from __future__ import annotations

import gzip
import os
import tarfile
import zipfile
import zlib
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("SıxmaXətası", mesaj, None, "ALQ-R005")


def _bayt(x: Any, ad: str) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        return x.encode("utf-8")
    raise AlqorXəta("TipXətası",
                    f"`{ad}` mətn və ya bayt gözləyir, `{tip_adı(x)}` gəlib",
                    None, "ALQ-T001")


def _mətn(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        raise _xəta("açılan məlumat UTF-8 mətn deyil — `gzipAç` işlədin")


def gzip_aç(b: Any) -> bytes:
    try:
        return gzip.decompress(_bayt(b, "gzipAç"))
    except (OSError, EOFError, zlib.error) as x:
        raise _xəta(f"gzip məlumatı pozulub: {x}")


def _fayllar(yollar: Any) -> list[tuple[Path, str]]:
    """[(fayl, arxivdəki ad)] — qovluqlar rekursiv açılır."""
    siyahı = yollar if isinstance(yollar, list) else [yollar]
    n: list[tuple[Path, str]] = []
    for y in siyahı:
        p = Path(str(y))
        if not p.exists():
            raise AlqorXəta("FaylTapılmadıXətası", f'"{y}" tapılmadı',
                            None, "ALQ-R009")
        if p.is_dir():
            kök = p.resolve().parent
            for f in sorted(p.rglob("*")):
                if f.is_file() and not f.is_symlink():
                    n.append((f, f.resolve().relative_to(kök).as_posix()))
        else:
            n.append((p, p.name))
    return n


def _hədəf(qovluq: Path, ad: str) -> Path:
    """Arxivdəki adı hədəf qovluğa həll edir — kənara çıxmağa icazə yox."""
    if ad.startswith(("/", "\\")) or (len(ad) > 1 and ad[1] == ":"):
        raise _xəta(f"arxivdə mütləq yol var: {ad!r}")
    yol = (qovluq / ad).resolve()
    if yol != qovluq and not yol.is_relative_to(qovluq):
        raise _xəta(f"arxivdəki yol qovluqdan kənara çıxır: {ad!r}")
    return yol


# ── zip ───────────────────────────────────────────────────────────────

def zip_yarat(arxiv: str, yollar: Any) -> int:
    fayllar = _fayllar(yollar)
    with zipfile.ZipFile(arxiv, "w", zipfile.ZIP_DEFLATED) as z:
        for f, ad in fayllar:
            z.write(f, ad)
    return len(fayllar)


def _zip_aç_obyekt(arxiv: str) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(arxiv)
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{arxiv}" tapılmadı',
                        None, "ALQ-R009")
    except zipfile.BadZipFile:
        raise _xəta(f'"{arxiv}" zip arxivi deyil və ya pozulub')


def zip_aç(arxiv: str, qovluq: str = ".") -> list[str]:
    hədəf_q = Path(qovluq).resolve()
    with _zip_aç_obyekt(arxiv) as z:
        üzvlər = z.infolist()
        for u in üzvlər:                   # əvvəlcə hamısını yoxla
            _hədəf(hədəf_q, u.filename)
            if (u.external_attr >> 16) & 0o170000 == 0o120000:
                raise _xəta(f"arxivdə simvolik keçid var: {u.filename!r}")
        hədəf_q.mkdir(parents=True, exist_ok=True)
        for u in üzvlər:
            z.extract(u, hədəf_q)
        return [u.filename for u in üzvlər if not u.is_dir()]


def zip_siyahı(arxiv: str) -> list[dict]:
    with _zip_aç_obyekt(arxiv) as z:
        return [{"ad": u.filename, "ölçü": u.file_size,
                 "sıxılmış": u.compress_size, "qovluq": u.is_dir()}
                for u in z.infolist()]


def zip_oxu(arxiv: str, ad: str) -> bytes:
    with _zip_aç_obyekt(arxiv) as z:
        try:
            return z.read(ad)
        except KeyError:
            raise _xəta(f'"{ad}" arxivdə yoxdur')


# ── tar ───────────────────────────────────────────────────────────────

def _tar_rejimi(arxiv: str, yaz: bool) -> str:
    a = arxiv.lower()
    s = ("gz" if a.endswith((".gz", ".tgz")) else
         "bz2" if a.endswith((".bz2", ".tbz")) else
         "xz" if a.endswith((".xz", ".txz")) else "")
    return ("w:" if yaz else "r:") + s if s else ("w" if yaz else "r:*")


def tar_yarat(arxiv: str, yollar: Any) -> int:
    fayllar = _fayllar(yollar)
    with tarfile.open(arxiv, _tar_rejimi(arxiv, True)) as t:
        for f, ad in fayllar:
            t.add(f, ad)
    return len(fayllar)


def _tar_obyekt(arxiv: str) -> tarfile.TarFile:
    try:
        return tarfile.open(arxiv, "r:*")
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{arxiv}" tapılmadı',
                        None, "ALQ-R009")
    except tarfile.TarError:
        raise _xəta(f'"{arxiv}" tar arxivi deyil və ya pozulub')


def tar_aç(arxiv: str, qovluq: str = ".") -> list[str]:
    hədəf_q = Path(qovluq).resolve()
    with _tar_obyekt(arxiv) as t:
        üzvlər = t.getmembers()
        for u in üzvlər:
            _hədəf(hədəf_q, u.name)
            if u.issym() or u.islnk() or u.isdev():
                raise _xəta(f"arxivdə icazəsiz üzv (keçid/cihaz): "
                            f"{u.name!r}")
        hədəf_q.mkdir(parents=True, exist_ok=True)
        t.extractall(hədəf_q, filter="data")
        return [u.name for u in üzvlər if u.isfile()]


def tar_siyahı(arxiv: str) -> list[dict]:
    with _tar_obyekt(arxiv) as t:
        return [{"ad": u.name, "ölçü": u.size, "qovluq": u.isdir()}
                for u in t.getmembers()]


def fayl_sıx(yol: str) -> str:
    p = Path(yol)
    if not p.is_file():
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" tapılmadı',
                        None, "ALQ-R009")
    hədəf = p.with_name(p.name + ".gz")
    with open(p, "rb") as g, gzip.open(hədəf, "wb") as ç:
        while blok := g.read(1 << 20):
            ç.write(blok)
    return str(hədəf)


def fayl_aç(yol: str) -> str:
    p = Path(yol)
    if p.suffix != ".gz":
        raise _xəta(f'"{yol}" `.gz` faylı deyil')
    hədəf = p.with_suffix("")
    try:
        with gzip.open(p, "rb") as g, open(hədəf, "wb") as ç:
            while blok := g.read(1 << 20):
                ç.write(blok)
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" tapılmadı',
                        None, "ALQ-R009")
    except (OSError, EOFError) as x:
        raise _xəta(f"gzip faylı pozulub: {x}")
    return str(hədəf)


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "gzipSıx": D("gzipSıx", lambda x, s=9: gzip.compress(
            _bayt(x, "gzipSıx"), compresslevel=s, mtime=0), 1, 2),
        "gzipAç": D("gzipAç", gzip_aç, 1, 1),
        "gzipAçMətn": D("gzipAçMətn", lambda b: _mətn(gzip_aç(b)), 1, 1),
        "zlibSıx": D("zlibSıx", lambda x, s=9: zlib.compress(
            _bayt(x, "zlibSıx"), s), 1, 2),
        "zlibAç": D("zlibAç", lambda b: _zlib_aç(b), 1, 1),
        "faylSıx": D("faylSıx", fayl_sıx, 1, 1),
        "faylAç": D("faylAç", fayl_aç, 1, 1),
        "zipYarat": D("zipYarat", zip_yarat, 2, 2),
        "zipAç": D("zipAç", zip_aç, 1, 2),
        "zipSiyahı": D("zipSiyahı", zip_siyahı, 1, 1),
        "zipOxu": D("zipOxu", zip_oxu, 2, 2),
        "tarYarat": D("tarYarat", tar_yarat, 2, 2),
        "tarAç": D("tarAç", tar_aç, 1, 2),
        "tarSiyahı": D("tarSiyahı", tar_siyahı, 1, 1),
    }


def _zlib_aç(b: Any) -> bytes:
    try:
        return zlib.decompress(_bayt(b, "zlibAç"))
    except zlib.error as x:
        raise _xəta(f"zlib məlumatı pozulub: {x}")


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b, i = T.MƏTN, T.İSTƏNİLƏN, T.BAYT, T.TAM
    sl = T.Siyahı(T.Lüğət(m, e))
    return {
        "gzipSıx": F(e, i, qaytarır=b, standart=1),
        "gzipAç": F(e, qaytarır=b), "gzipAçMətn": F(e, qaytarır=m),
        "zlibSıx": F(e, i, qaytarır=b, standart=1),
        "zlibAç": F(e, qaytarır=b),
        "faylSıx": F(m, qaytarır=m), "faylAç": F(m, qaytarır=m),
        "zipYarat": F(m, e, qaytarır=i),
        "zipAç": F(m, m, qaytarır=T.Siyahı(m), standart=1),
        "zipSiyahı": F(m, qaytarır=sl), "zipOxu": F(m, m, qaytarır=b),
        "tarYarat": F(m, e, qaytarır=i),
        "tarAç": F(m, m, qaytarır=T.Siyahı(m), standart=1),
        "tarSiyahı": F(m, qaytarır=sl),
    }
