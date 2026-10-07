"""
`toml` — TOML oxuma və yazma (§ 10.17).

    gətir toml

    dəyişən k = toml.faylOxu("tətbiq.toml")
    yaz(k["server"]["port"])

    toml.faylYaz("çıxış.toml", {"ad": "Alqor", "server": {"port": 8080}})

Oxuma TOML 1.0-ın hamısını dəstəkləyir (Python `tomllib`). Tarix/vaxt
dəyərləri ISO mətni kimi qaytarılır (`vaxt` modulu ilə eyni forma).
"""

from __future__ import annotations

import datetime as _dt
import math
import re
import tomllib
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("TOMLXətası", mesaj, None, "ALQ-R005")


def _alqorla(x: Any) -> Any:
    if isinstance(x, dict):
        return {a: _alqorla(d) for a, d in x.items()}
    if isinstance(x, list):
        return [_alqorla(d) for d in x]
    if isinstance(x, (_dt.datetime, _dt.date, _dt.time)):
        return x.isoformat()
    return x


def oxu(mətn: str) -> dict:
    if not isinstance(mətn, str):
        raise AlqorXəta("TipXətası",
                        f"`toml.oxu` mətn gözləyir, `{tip_adı(mətn)}` gəlib",
                        None, "ALQ-T001")
    try:
        return _alqorla(tomllib.loads(mətn.lstrip("﻿")))
    except tomllib.TOMLDecodeError as x:
        raise _xəta(f"TOML pozulub: {x}")


# ── Yazma ──────────────────────────────────────────────────────────────

_ÇILPAQ = re.compile(r"^[A-Za-z0-9_-]+$")


def _açar(a: Any) -> str:
    a = str(a)
    return a if _ÇILPAQ.match(a) else _mətn(a)


def _mətn(s: str) -> str:
    n = ['"']
    for c in s:
        if c == '"':
            n.append('\\"')
        elif c == "\\":
            n.append("\\\\")
        elif c == "\n":
            n.append("\\n")
        elif c == "\t":
            n.append("\\t")
        elif c == "\r":
            n.append("\\r")
        elif ord(c) < 0x20 or ord(c) == 0x7F:
            n.append(f"\\u{ord(c):04X}")
        else:
            n.append(c)
    n.append('"')
    return "".join(n)


def _sadələşdir(x: Any) -> Any:
    if isinstance(x, Nümunə):
        return {a: _sadələşdir(d) for a, d in x.sahələr.items()}
    if isinstance(x, dict):
        return {a: _sadələşdir(d) for a, d in x.items() if d is not None}
    if isinstance(x, (list, tuple, set)):
        return [_sadələşdir(d) for d in x]
    return x


def _dəyər(x: Any) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return repr(x)
    if isinstance(x, str):
        return _mətn(x)
    if isinstance(x, list):
        return "[" + ", ".join(_dəyər(d) for d in x) + "]"
    if isinstance(x, dict):
        return "{" + ", ".join(f"{_açar(a)} = {_dəyər(d)}"
                               for a, d in x.items()) + "}"
    if x is None:
        raise _xəta("TOML-da `boş` dəyər yoxdur — açarı buraxın")
    raise _xəta(f"`{tip_adı(x)}` TOML-a yazıla bilmir")


def _cədvəl_siyahısıdır(d: Any) -> bool:
    return isinstance(d, list) and bool(d) and all(
        isinstance(x, dict) for x in d)


def _yaz_cədvəl(l: dict, yol: list[str], s: list[str]) -> None:
    sadə = [(a, d) for a, d in l.items()
            if not isinstance(d, dict) and not _cədvəl_siyahısıdır(d)]
    for a, d in sadə:
        s.append(f"{_açar(a)} = {_dəyər(d)}")
    for a, d in l.items():
        if isinstance(d, dict):
            alt = yol + [_açar(a)]
            # Yalnız alt cədvəlləri olan cədvəlin başlığı lazım deyil
            if any(not isinstance(x, dict) and not _cədvəl_siyahısıdır(x)
                   for x in d.values()) or not d:
                if s:
                    s.append("")
                s.append(f"[{'.'.join(alt)}]")
            _yaz_cədvəl(d, alt, s)
        elif _cədvəl_siyahısıdır(d):
            alt = yol + [_açar(a)]
            for x in d:
                if s:
                    s.append("")
                s.append(f"[[{'.'.join(alt)}]]")
                _yaz_cədvəl(x, alt, s)


def yaz(l: Any) -> str:
    l = _sadələşdir(l)
    if not isinstance(l, dict):
        raise AlqorXəta("TipXətası", "`toml.yaz` lüğət gözləyir, "
                        f"`{tip_adı(l)}` gəlib", None, "ALQ-T001")
    s: list[str] = []
    _yaz_cədvəl(l, [], s)
    return "\n".join(s) + "\n"


def _fayl_oxu(yol: str) -> str:
    try:
        return Path(yol).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" faylı tapılmadı',
                        None, "ALQ-R009")


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "oxu": D("oxu", oxu, 1, 1),
        "yaz": D("yaz", yaz, 1, 1),
        "faylOxu": D("faylOxu", lambda y: oxu(_fayl_oxu(y)), 1, 1),
        "faylYaz": D("faylYaz", lambda y, l: (Path(y).write_text(
            yaz(l), encoding="utf-8", newline="\n"), None)[1], 2, 2),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e = T.MƏTN, T.İSTƏNİLƏN
    l = T.Lüğət(m, e)
    return {"oxu": F(m, qaytarır=l), "faylOxu": F(m, qaytarır=l),
            "yaz": F(e, qaytarır=m), "faylYaz": F(m, e, qaytarır=T.HEÇ)}
