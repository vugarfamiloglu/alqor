"""
`konfiq` — konfiqurasiya faylları (§ 10.17).

    gətir konfiq

    dəyişən k = konfiq.oxu("tətbiq.toml", mühit: "TƏTBİQ")
    dəyişən port = k.tam("server.port", 8080)
    dəyişən baza = k.tələb("verilənlər.url")     // yoxdursa KonfiqXətası

    konfiq.mühitOxu(".env", mühitəYaz: doğru)    // .env → sistem mühiti

Format faylın uzantısından seçilir: `.toml`, `.yaml`/`.yml`, `.json`,
`.env`, `.ini`/`.cfg`. Bir neçə fayl verilsə (`konfiq.oxu([a, b])`)
sonrakı əvvəlkinin üzərinə yazılır (məs. `əsas.toml` + `yerli.toml`).

`mühit: "TƏTBİQ"` — `TƏTBİQ_SERVER_PORT=9000` mühit dəyişəni
`server.port` açarını əvəz edir (dəyər tipi avtomatik: 9000 → tam).
"""

from __future__ import annotations

import configparser
import json
import os
import re
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, tip_adı
from ..elifba import latınla

_YOX = object()


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("KonfiqXətası", mesaj, None, "ALQ-R005")


# ── .env ──────────────────────────────────────────────────────────────

_ENV_SƏTRİ = re.compile(
    r"^\s*(?:export\s+)?([A-Za-z_À-￿][\w.À-￿-]*)\s*=\s*(.*)$")


def _yerləşdir(v: str, mühit: dict) -> str:
    def əvəz(m):
        ad = m.group(1) or m.group(2)
        return mühit.get(ad, os.environ.get(ad, ""))
    return re.sub(r"\$\{([^}]+)\}|\$([A-Za-z_]\w*)", əvəz, v)


def env_oxu(mətn: str) -> dict[str, str]:
    n: dict[str, str] = {}
    sətirlər = mətn.lstrip("﻿").splitlines()
    i = 0
    while i < len(sətirlər):
        s = sətirlər[i]
        i += 1
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        m = _ENV_SƏTRİ.match(s)
        if not m:
            raise _xəta(f".env sətir {i}: `AD=dəyər` gözlənilirdi")
        ad, v = m.group(1), m.group(2).strip()
        if v[:1] in "\"'":
            q = v[0]
            v = v[1:]
            # Çox sətirli dırnaqlı dəyər
            while not _bağlanır(v, q):
                if i >= len(sətirlər):
                    raise _xəta(f".env: `{ad}` dəyərinin dırnağı bağlanmayıb")
                v += "\n" + sətirlər[i]
                i += 1
            son = _bağlanır(v, q)
            v = v[:son - 1]
            if q == '"':
                v = (v.replace("\\n", "\n").replace("\\t", "\t")
                     .replace('\\"', '"').replace("\\\\", "\\"))
                v = _yerləşdir(v, n)
        else:
            v = re.sub(r"\s+#.*$", "", v)
            v = _yerləşdir(v, n)
        n[ad] = v
    return n


def _bağlanır(v: str, q: str) -> int:
    i = 0
    while i < len(v):
        if v[i] == "\\" and q == '"':
            i += 2
            continue
        if v[i] == q:
            return i + 1
        i += 1
    return 0


# ── Fayllar ───────────────────────────────────────────────────────────

def _ini_oxu(mətn: str) -> dict:
    p = configparser.ConfigParser(interpolation=None)
    p.optionxform = str                       # açarların hərfi qorunsun
    try:
        p.read_string(mətn)
    except configparser.Error as x:
        raise _xəta(f"INI pozulub: {x}")
    n: dict[str, Any] = dict(p.defaults())
    for bölmə in p.sections():
        n[bölmə] = {a: _çevir(v) for a, v in p.items(bölmə)
                    if a not in p.defaults() or p.get(bölmə, a) !=
                    p.defaults().get(a)}
    return n


def fayl_oxu(yol: str) -> dict:
    p = Path(yol)
    try:
        mətn = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" faylı tapılmadı',
                        None, "ALQ-R009")
    ad = p.name.lower()
    uzantı = p.suffix.lower()
    if uzantı == ".toml":
        from .toml_ import oxu
        d = oxu(mətn)
    elif uzantı in (".yaml", ".yml"):
        from .yaml_ import oxu
        d = oxu(mətn)
    elif uzantı == ".json":
        try:
            d = json.loads(mətn)
        except json.JSONDecodeError as x:
            raise _xəta(f"{p.name}: JSON pozulub (sətir {x.lineno}): "
                        f"{x.msg}")
    elif uzantı == ".env" or ad == ".env" or ad.startswith(".env."):
        d = env_oxu(mətn)
    elif uzantı in (".ini", ".cfg", ".conf"):
        d = _ini_oxu(mətn)
    else:
        raise _xəta(f"`{p.name}`: format tanınmadı (toml, yaml, json, "
                    "env, ini)")
    if d is None:
        return {}
    if not isinstance(d, dict):
        raise _xəta(f"{p.name}: kökdə lüğət gözlənilirdi, "
                    f"`{tip_adı(d)}` gəlib")
    return d


def _birləşdir(a: dict, b: dict) -> dict:
    n = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(n.get(k), dict):
            n[k] = _birləşdir(n[k], v)
        else:
            n[k] = v
    return n


def _çevir(v: str) -> Any:
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    if v.lower() in ("doğru", "dogru", "true", "bəli", "beli", "on", "yes"):
        return True
    if v.lower() in ("yanlış", "yanlis", "false", "xeyr", "off", "no"):
        return False
    return v


def _açar_adı(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", latınla(s).upper()).strip("_")


def _mühitdən(d: dict, ön: str) -> dict:
    """`ÖN_A_B` mühit dəyişənləri `a.b` açarlarını əvəz edir."""
    ön = _açar_adı(ön) + "_"
    mühit = {_açar_adı(a): v for a, v in os.environ.items()}

    def gəz(l: dict, yol: list[str]) -> dict:
        n = dict(l)
        for a, v in l.items():
            alt = yol + [str(a)]
            if isinstance(v, dict):
                n[a] = gəz(v, alt)
                continue
            ad = ön + "_".join(_açar_adı(x) for x in alt)
            if ad in mühit:
                n[a] = _çevir(mühit[ad])
        return n
    return gəz(d, [])


# ── Konfiq obyekti ────────────────────────────────────────────────────

class Konfiq:
    ALQOR_TİP_ADI = "konfiq"

    def __init__(self, d: dict, mənbə: str = ""):
        self.d = d
        self.mənbə = mənbə

    def __repr__(self) -> str:
        return f"<konfiq {self.mənbə}>"

    def tap(self, yol: str) -> Any:
        cari: Any = self.d
        for h in str(yol).split("."):
            if isinstance(cari, dict) and h in cari:
                cari = cari[h]
            elif isinstance(cari, list) and h.isdigit() and \
                    int(h) < len(cari):
                cari = cari[int(h)]
            else:
                return _YOX
        return cari

    def al(self, yol: str, standart: Any = None) -> Any:
        v = self.tap(yol)
        return standart if v is _YOX else v

    def tələb(self, yol: str) -> Any:
        v = self.tap(yol)
        if v is _YOX or v is None:
            raise _xəta(f"`{yol}` konfiqurasiyada yoxdur"
                        + (f" ({self.mənbə})" if self.mənbə else ""))
        return v

    def tipli(self, yol: str, standart: Any, tip: str) -> Any:
        v = self.tap(yol)
        if v is _YOX or v is None:
            return standart
        try:
            if tip == "tam":
                if isinstance(v, bool):
                    raise ValueError
                return int(v)
            if tip == "onluq":
                return float(v)
            if tip == "məntiq":
                if isinstance(v, bool):
                    return v
                c = _çevir(str(v))
                if isinstance(c, bool):
                    return c
                raise ValueError
            if tip == "mətn":
                return v if isinstance(v, str) else str(v)
            if tip == "siyahı":
                if isinstance(v, list):
                    return v
                if isinstance(v, str):
                    return [x.strip() for x in v.split(",") if x.strip()]
                raise ValueError
        except (TypeError, ValueError):
            raise _xəta(f"`{yol}` {tip} olmalıdır, `{v!r}` yazılıb")
        return v


Konfiq.ALQOR_METODLARI = {
    "al": lambda i, k, y, s=None: k.al(y, s),
    "tələb": lambda i, k, y: k.tələb(y),
    "var": lambda i, k, y: k.tap(y) is not _YOX,
    "tam": lambda i, k, y, s=None: k.tipli(y, s, "tam"),
    "onluq": lambda i, k, y, s=None: k.tipli(y, s, "onluq"),
    "məntiq": lambda i, k, y, s=None: k.tipli(y, s, "məntiq"),
    "mətn": lambda i, k, y, s=None: k.tipli(y, s, "mətn"),
    "siyahı": lambda i, k, y, s=None: k.tipli(y, s, "siyahı"),
    "bölmə": lambda i, k, y: Konfiq(
        k.al(y, {}) if isinstance(k.al(y, {}), dict) else {},
        f"{k.mənbə}:{y}"),
    "lüğət": lambda i, k: k.d,
}


def oxu(yollar: Any, mühit: str | None = None,
        standart: dict | None = None) -> Konfiq:
    siyahı = yollar if isinstance(yollar, list) else [yollar]
    d: dict = dict(standart or {})
    for y in siyahı:
        d = _birləşdir(d, fayl_oxu(y))
    if mühit:
        d = _mühitdən(d, mühit)
    return Konfiq(d, ", ".join(str(y) for y in siyahı))


def mühit_oxu(yol: str = ".env", mühitəYaz: bool = False,
              üzərinəYaz: bool = False) -> dict:
    try:
        mətn = Path(yol).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AlqorXəta("FaylTapılmadıXətası", f'"{yol}" faylı tapılmadı',
                        None, "ALQ-R009")
    d = env_oxu(mətn)
    if mühitəYaz:
        for a, v in d.items():
            if üzərinəYaz or a not in os.environ:
                os.environ[a] = v
    return d


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "oxu": D("oxu", oxu, 1, 1),
        "lüğətdən": D("lüğətdən", lambda d, mühit=None: Konfiq(
            _mühitdən(d, mühit) if mühit else d, "lüğət"), 1, 1),
        "mühitOxu": D("mühitOxu", mühit_oxu, 0, 1),
        "envOxu": D("envOxu", env_oxu, 1, 1),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import Fsərbəst, F
    m, e = T.MƏTN, T.İSTƏNİLƏN
    K = T.Sadə("konfiq")
    return {"oxu": Fsərbəst(K), "lüğətdən": Fsərbəst(K),
            "mühitOxu": Fsərbəst(T.Lüğət(m, m)),
            "envOxu": F(m, qaytarır=T.Lüğət(m, m))}


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ
    K = T.Sadə("konfiq")
    return {"konfiq": {
        "al": F(m, e, qaytarır=e, standart=1),
        "tələb": F(m, qaytarır=e),
        "var": F(m, qaytarır=b),
        "tam": F(m, e, qaytarır=T.TAM, standart=1),
        "onluq": F(m, e, qaytarır=T.ONLUQ, standart=1),
        "məntiq": F(m, e, qaytarır=b, standart=1),
        "mətn": F(m, e, qaytarır=m, standart=1),
        "siyahı": F(m, e, qaytarır=T.Siyahı(), standart=1),
        "bölmə": F(m, qaytarır=K),
        "lüğət": F(qaytarır=T.Lüğət(m, e)),
    }}
