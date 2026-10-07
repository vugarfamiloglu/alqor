"""
`csv` — CSV oxuma və yazma (§ 10.17).

    gətir csv

    dəyişən sətirlər = csv.faylOxu("tələbələr.csv")      // siyahı[lüğət]
    hər s üçün sətirlər içində
        yaz(s["ad"])
    son

    csv.faylYaz("nəticə.csv", [{"ad": "Aysel", "bal": 95}])

Seçimlər (adlı arqumentlər):

    ayırıcı: ","        `"avto"` — `,` `;` `\\t` `|` arasından özü seçir
    başlıq: doğru       birinci sətir sütun adlarıdır → siyahı[lüğət]
    çevir: yanlış       "42" → 42, "3.5" → 3.5, "doğru" → doğru
    sütunlar: [...]     yazarkən sütun sırası (lüğət sətirləri üçün)
    bom: yanlış         yazarkən UTF-8 BOM (Excel Azərbaycan hərflərini
                        düzgün göstərsin)
"""

from __future__ import annotations

import csv as _csv
import io
import re
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı

_ƏDƏD = re.compile(r"^-?\d+$")
_ONLUQ = re.compile(r"^-?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("CSVXətası", mesaj, None, "ALQ-R005")


def _ayırıcı(mətn: str, ayırıcı: str) -> str:
    if ayırıcı != "avto":
        if len(ayırıcı) != 1:
            raise AlqorXəta("DəyərXətası",
                            "`ayırıcı` bir simvol olmalıdır (və ya \"avto\")",
                            None, "ALQ-T001")
        return ayırıcı
    nümunə = "\n".join(mətn.splitlines()[:20])
    try:
        return _csv.Sniffer().sniff(nümunə, delimiters=",;\t|").delimiter
    except _csv.Error:
        return ","


def _çevir(d: str) -> Any:
    if _ƏDƏD.match(d):
        return int(d)
    if _ONLUQ.match(d):
        return float(d)
    if d in ("doğru", "true"):
        return True
    if d in ("yanlış", "false"):
        return False
    if d == "":
        return None
    return d


def oxu(mətn: str, ayırıcı: str = ",", başlıq: bool = True,
        çevir: bool = False) -> list:
    if not isinstance(mətn, str):
        raise AlqorXəta("TipXətası",
                        f"`csv.oxu` mətn gözləyir, `{tip_adı(mətn)}` gəlib",
                        None, "ALQ-T001")
    mətn = mətn.lstrip("﻿")
    a = _ayırıcı(mətn, ayırıcı)
    try:
        sətirlər = list(_csv.reader(io.StringIO(mətn, newline=""),
                                    delimiter=a, strict=True))
    except _csv.Error as x:
        raise _xəta(f"CSV pozulub: {x}")
    sətirlər = [s for s in sətirlər if s]
    if çevir:
        sətirlər = [[_çevir(d) for d in s] if i or not başlıq else s
                    for i, s in enumerate(sətirlər)]
    if not başlıq:
        return sətirlər
    if not sətirlər:
        return []
    adlar = [str(x).strip() for x in sətirlər[0]]
    təkrar = {x for x in adlar if adlar.count(x) > 1}
    if təkrar:
        raise _xəta(f"başlıqda təkrarlanan sütun: {', '.join(sorted(təkrar))}")
    nəticə = []
    for n, s in enumerate(sətirlər[1:], start=2):
        if len(s) > len(adlar):
            raise _xəta(f"{n}-ci sətirdə {len(s)} sahə var, başlıqda "
                        f"{len(adlar)}")
        s = s + [None if çevir else ""] * (len(adlar) - len(s))
        nəticə.append(dict(zip(adlar, s)))
    return nəticə


def _dəyər(d: Any) -> str:
    if d is None:
        return ""
    if d is True:
        return "doğru"
    if d is False:
        return "yanlış"
    if isinstance(d, float) and d.is_integer():
        return str(d)
    return str(d)


def yaz(sətirlər: Any, ayırıcı: str = ",", sütunlar: list | None = None,
        başlıq: bool = True, bom: bool = False) -> str:
    if not isinstance(sətirlər, list):
        raise AlqorXəta("TipXətası", "`csv.yaz` siyahı gözləyir, "
                        f"`{tip_adı(sətirlər)}` gəlib", None, "ALQ-T001")
    if ayırıcı == "avto":
        ayırıcı = ","
    çıxış = io.StringIO()
    w = _csv.writer(çıxış, delimiter=ayırıcı, lineterminator="\n")
    lüğətlər = all(isinstance(s, dict) for s in sətirlər) and sətirlər
    if lüğətlər or sütunlar:
        adlar = list(sütunlar) if sütunlar else []
        if not adlar:
            for s in sətirlər:
                for a in s:
                    if a not in adlar:
                        adlar.append(a)
        if başlıq:
            w.writerow([str(a) for a in adlar])
        for s in sətirlər:
            if isinstance(s, dict):
                w.writerow([_dəyər(s.get(a)) for a in adlar])
            else:
                w.writerow([_dəyər(d) for d in s])
    else:
        for s in sətirlər:
            if not isinstance(s, (list, tuple)):
                raise AlqorXəta("TipXətası", "`csv.yaz` sətirləri lüğət və "
                                "ya siyahı olmalıdır", None, "ALQ-T001")
            w.writerow([_dəyər(d) for d in s])
    return ("﻿" if bom else "") + çıxış.getvalue()


def _fayl_oxu(yol: str) -> str:
    try:
        return Path(yol).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" faylı tapılmadı',
                        None, "ALQ-R009")
    except UnicodeDecodeError:
        # Köhnə Excel faylları çox vaxt Windows-1254 (türk/az) olur
        return Path(yol).read_bytes().decode("cp1254")


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    def fayl_yaz(yol, sətirlər, **k):
        Path(yol).write_text(yaz(sətirlər, **k), encoding="utf-8",
                             newline="")
        return None

    return {
        "oxu": D("oxu", oxu, 1, 1),
        "yaz": D("yaz", yaz, 1, 1),
        "faylOxu": D("faylOxu", lambda y, **k: oxu(_fayl_oxu(y), **k), 1, 1),
        "faylYaz": D("faylYaz", fayl_yaz, 2, 2),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import Fsərbəst
    # Adlı seçimlər çoxdur — sayı yoxlanılmır, nəticə tipi verilir
    return {
        "oxu": Fsərbəst(T.Siyahı()), "faylOxu": Fsərbəst(T.Siyahı()),
        "yaz": Fsərbəst(T.MƏTN), "faylYaz": Fsərbəst(T.HEÇ),
    }
