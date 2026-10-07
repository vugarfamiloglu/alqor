"""
Alqor Studio — layihədə axtarış və əvəzləmə (Ctrl+Shift+F).

Yalnız layihə qovluğunun içindəki mətn faylları gəzilir (gizli və
`qurma/`, `__pycache__` … atlanır, 2 MB-dan böyük və ikili fayllar
oxunmur). Açıq nişanların SAXLANMAMIŞ mətni də nəzərə alınır.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .layihe import GİZLİ_QOVLUQLAR, MAKS_FAYL, Layihə

MAKS_NƏTİCƏ = 2000
_ATLA = GİZLİ_QOVLUQLAR | {"qurma", "paketlər"}


class AxtarışXətası(ValueError):
    pass


def naxış(sorğu: str, hərf: bool, söz: bool, regex: bool) -> re.Pattern:
    if not sorğu:
        raise AxtarışXətası("axtarış mətni boşdur")
    try:
        p = sorğu if regex else re.escape(sorğu)
        if söz:
            p = rf"(?<!\w){p}(?!\w)"
        return re.compile(p, 0 if hərf else re.IGNORECASE)
    except re.error as x:
        raise AxtarışXətası(f"müntəzəm ifadə yanlışdır: {x}") from None


def fayllar(layihə: Layihə, filtr: str = "") -> list[Path]:
    süzgəclər = [f.strip() for f in filtr.split(",") if f.strip()]
    n = []
    for p in sorted(layihə.kök.rglob("*")):
        if not p.is_file():
            continue
        hissələr = p.relative_to(layihə.kök).parts
        if any(h in _ATLA or h.startswith(".") for h in hissələr):
            continue
        if süzgəclər and not any(fnmatch.fnmatch(p.name, s) or
                                 fnmatch.fnmatch("/".join(hissələr), s)
                                 for s in süzgəclər):
            continue
        n.append(p)
    return n


def _mətn(p: Path) -> str | None:
    try:
        if p.stat().st_size > MAKS_FAYL:
            return None
        b = p.read_bytes()
    except OSError:
        return None
    if b"\0" in b[:4096]:
        return None
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return None


def axtar(layihə: Layihə, rx: re.Pattern, filtr: str = "",
          açıqlar: dict[str, str] | None = None) -> dict:
    açıqlar = açıqlar or {}
    nəticə, cəm = [], 0
    for p in fayllar(layihə, filtr):
        yol = layihə.nisbi(p)
        mətn = açıqlar.get(yol)
        if mətn is None:
            mətn = _mətn(p)
        if mətn is None:
            continue
        sətirlər = []
        for i, s in enumerate(mətn.split("\n")):
            for m in rx.finditer(s):
                if m.end() == m.start():
                    continue
                sətirlər.append({"no": i + 1, "sütun": m.start() + 1,
                                 "uzunluq": m.end() - m.start(),
                                 "mətn": s[:400]})
                cəm += 1
                if cəm >= MAKS_NƏTİCƏ:
                    break
            if cəm >= MAKS_NƏTİCƏ:
                break
        if sətirlər:
            nəticə.append({"yol": yol, "sətirlər": sətirlər})
        if cəm >= MAKS_NƏTİCƏ:
            break
    return {"fayllar": nəticə, "say": cəm, "kəsilib": cəm >= MAKS_NƏTİCƏ}


def əvəzlə(layihə: Layihə, rx: re.Pattern, əvəz: str, regex: bool,
           filtr: str = "", açıqlar: dict[str, str] | None = None) -> dict:
    """Bütün uyğunluqları əvəzləyir. Açıq nişanların yeni mətni qaytarılır
    (disk də yazılır); bağlı fayllar diskdə dəyişir."""
    açıqlar = açıqlar or {}
    if not regex:
        əvəz = əvəz.replace("\\", "\\\\")
    dəyişən, say = {}, 0
    for p in fayllar(layihə, filtr):
        yol = layihə.nisbi(p)
        mətn = açıqlar.get(yol)
        if mətn is None:
            mətn = _mətn(p)
        if mətn is None:
            continue
        try:
            yeni, n = rx.subn(əvəz, mətn)
        except (re.error, IndexError) as x:
            raise AxtarışXətası(f"əvəz ifadəsi yanlışdır: {x}") from None
        if n:
            layihə.yaz(yol, yeni)
            dəyişən[yol] = yeni
            say += n
    return {"say": say, "fayllar": dəyişən}
