"""
`xml` — XML oxuma, axtarış və yazma (§ 10.17).

    gətir xml

    dəyişən kök = xml.oxu("<kitablar><kitab il=\\"1937\\">Ölülər</kitab></kitablar>")
    hər k üçün kök.tapHamısı("kitab") içində
        yaz(k.mətn(), k.atribut("il"))
    son

    dəyişən e = xml.element("qeyd", {"id": "1"}, ["Salam"])
    yaz(e.xml())                         // <qeyd id="1">Salam</qeyd>
    yaz(xml.lüğətə("<a x=\\"1\\"><b>2</b></a>"))   // {"@x": "1", "b": "2"}

Təhlükəsizlik: `<!DOCTYPE>` daxilində `<!ENTITY>` elanları rədd edilir
("milyard gülüş" və xarici fayl hücumları).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı
from ._duyun import Düyün, metod_tipləri


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("XMLXətası", mesaj, None, "ALQ-R005")


def _ad(teq: str) -> str:
    # `{http://ad.fəzası}teq` → `teq` (ad fəzaları sadələşdirilir)
    return teq.rsplit("}", 1)[-1] if teq.startswith("{") else teq


def _düyünə(e: ET.Element) -> Düyün:
    d = Düyün(_ad(e.tag), {_ad(a): v for a, v in e.attrib.items()})
    if e.text:
        d.əlavə(e.text)
    for u in e:
        d.əlavə(_düyünə(u))
        if u.tail:
            d.əlavə(u.tail)
    return d


def oxu(mətn: str) -> Düyün:
    if not isinstance(mətn, str):
        raise AlqorXəta("TipXətası",
                        f"`xml.oxu` mətn gözləyir, `{tip_adı(mətn)}` gəlib",
                        None, "ALQ-T001")
    if re.search(r"<!ENTITY", mətn, re.I):
        raise _xəta("`<!ENTITY>` elanlarına icazə verilmir (təhlükəsizlik)")
    try:
        return _düyünə(ET.fromstring(mətn.lstrip("﻿")))
    except ET.ParseError as x:
        sətir, sütun = x.position
        raise _xəta(f"XML pozulub (sətir {sətir}, sütun {sütun + 1}): "
                    f"{str(x).split(':')[0]}")


def element(ad: str, atributlar: Any = None, uşaqlar: Any = None) -> Düyün:
    if not isinstance(ad, str) or not re.match(r"^[^\W\d][\w.:-]*$", ad):
        raise AlqorXəta("DəyərXətası", f"`{ad}` XML element adı deyil",
                        None, "ALQ-T001")
    d = Düyün(ad, {str(a): _sadə(v) for a, v in (atributlar or {}).items()})
    if uşaqlar is None:
        return d
    for u in (uşaqlar if isinstance(uşaqlar, list) else [uşaqlar]):
        d.əlavə(u if isinstance(u, Düyün) else _sadə(u))
    return d


def _sadə(v: Any) -> str:
    if v is True:
        return "doğru"
    if v is False:
        return "yanlış"
    if v is None:
        return ""
    return str(v)


def lüğətdən(l: Any, kök: str = "kök") -> Düyün:
    """`lüğət` → XML; `@ad` atribut, `#mətn` mətn, siyahı təkrar element."""
    def qur(ad: str, d: Any) -> list[Düyün]:
        if isinstance(d, Nümunə):
            d = d.sahələr
        if isinstance(d, list):
            return [x for v in d for x in qur(ad, v)]
        e = element(ad)
        if isinstance(d, dict):
            for a, v in d.items():
                a = str(a)
                if a.startswith("@"):
                    e.atr[a[1:]] = _sadə(v)
                elif a == "#mətn":
                    e.əlavə(_sadə(v))
                else:
                    for u in qur(a, v):
                        e.əlavə(u)
        elif d is not None:
            e.əlavə(_sadə(d))
        return [e]
    return qur(kök, l)[0]


def yaz(d: Any, gözəl: bool = True) -> str:
    if not isinstance(d, Düyün):
        d = lüğətdən(d)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + d.xml(gözəl) + "\n"


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
        "faylOxu": D("faylOxu", lambda y: oxu(_fayl_oxu(y)), 1, 1),
        "yaz": D("yaz", yaz, 1, 2),
        "faylYaz": D("faylYaz", lambda y, d: (Path(y).write_text(
            yaz(d), encoding="utf-8", newline="\n"), None)[1], 2, 2),
        "element": D("element", element, 1, 3),
        "lüğətə": D("lüğətə", lambda m: (
            m if isinstance(m, Düyün) else oxu(m)).lüğət(), 1, 1),
        "lüğətdən": D("lüğətdən", lüğətdən, 1, 2),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ
    D = T.Sadə("düyün")
    return {
        "oxu": F(m, qaytarır=D), "faylOxu": F(m, qaytarır=D),
        "yaz": F(e, b, qaytarır=m, standart=1),
        "faylYaz": F(m, e, qaytarır=T.HEÇ),
        "element": F(m, e, e, qaytarır=D, standart=2),
        "lüğətə": F(e, qaytarır=e),
        "lüğətdən": F(e, m, qaytarır=D, standart=1),
    }


def obyekt_tipləri() -> dict:
    return metod_tipləri()
