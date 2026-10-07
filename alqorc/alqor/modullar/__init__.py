"""
Alqor — standart kitabxananın əlavə modulları (§ 10.12–10.17).

Hər modul öz faylındadır və TƏNBƏL yüklənir: `gətir csv` yazılmayan
proqram `csv` faylını heç idxal etmir. Modul faylı iki funksiya verir:

    def qur(icraçı) -> dict[str, Any]
        İcra üçün üzvlər (`Daxili`, sabitlər, alt modullar).

    def tiplər() -> dict[str, T.Tip]
        Tip yoxlayıcısı və `alqorls` üçün üzvlərin imzaları.

İstəyə görə:

    def obyekt_tipləri() -> dict[str, dict[str, T.Tip]]
        Modulun qaytardığı obyektlərin metodları — açar `T.Sadə`-nin
        adıdır (məs. "xmlElement"). Tip yoxlayıcısı `x.` üzvlərini
        buradan götürür, `alqorls` tamamlaması da.

Python obyektləri Alqor-a `ALQOR_TİP_ADI` / `ALQOR_METODLARI` sinif
atributları ilə görünür (`kitabxana._cədvəl_tap`).
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any

# Alqor adı → Python modulu (bu paketdə)
QEYD: dict[str, str] = {
    "kodlaşdırma": "kodlasdirma",
    "csv": "csv_",
    "toml": "toml_",
    "yaml": "yaml_",
    "xml": "xml_",
    "html": "html_",
    "konfiq": "konfiq",
    "sıxma": "sixma",
    "şifrə": "sifre",
    "http": "http_",
    "şəbəkə": "sebeke",
    "verilənlər": "verilenler",
}


def adlar() -> list[str]:
    return list(QEYD)


def _py(ad: str):
    return importlib.import_module(f"{__name__}.{QEYD[ad]}")


def icra_modulu(icraçı, ad: str):
    """`gətir <ad>` — hər icraçı üçün bir dəfə qurulur."""
    from ..deyerler import Modul
    keş: dict = icraçı.__dict__.setdefault("_əlavə_modullar", {})
    if ad not in keş:
        keş[ad] = Modul(ad, _py(ad).qur(icraçı))
    return keş[ad]


@lru_cache(maxsize=None)
def modul_tipi(ad: str):
    from .. import tipler as T
    return T.ModulTipi(ad, dict(_py(ad).tiplər()))


@lru_cache(maxsize=None)
def _obyekt_cədvəli() -> dict[str, dict[str, Any]]:
    n: dict[str, dict[str, Any]] = {}
    for ad in QEYD:
        f = getattr(_py(ad), "obyekt_tipləri", None)
        if f is not None:
            n.update(f())
    return n


def obyekt_metodları(tip_adı: str) -> dict[str, Any] | None:
    return _obyekt_cədvəli().get(tip_adı)
