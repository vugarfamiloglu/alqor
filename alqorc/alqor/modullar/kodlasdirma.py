"""
`kodlaşdırma` — Base64, hex, URL, HTML, UTF-8 çevirmələri (§ 10.17).

    gətir kodlaşdırma

    kodlaşdırma.base64Kodla("Salam")          // "U2FsYW0="
    kodlaşdırma.base64AçMətn("U2FsYW0=")      // "Salam"
    kodlaşdırma.urlKodla("ə ş")               // "%C9%99%20%C5%9F"
    kodlaşdırma.sorğuKodla({"q": "çay", "s": 2})   // "q=%C3%A7ay&s=2"
    kodlaşdırma.slug("Şəki xanlığı!")         // "seki-xanligi"
"""

from __future__ import annotations

import base64
import binascii
import html
import re
import zlib
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlencode

from ..deyerler import AlqorXəta, Daxili, tip_adı


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("FormatXətası", mesaj, None, "ALQ-R005")


def _bayt(x: Any, ad: str) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        return x.encode("utf-8")
    if isinstance(x, list) and all(isinstance(b, int) for b in x):
        return bytes(x)
    raise AlqorXəta("TipXətası",
                    f"`{ad}` mətn və ya bayt gözləyir, `{tip_adı(x)}` gəlib",
                    None, "ALQ-T001")


def _mətn(b: bytes, ad: str) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        raise _xəta(f"`{ad}`: nəticə UTF-8 mətn deyil — baytı "
                    "`…Aç` funksiyası ilə alın")


def _b64_aç(m: Any, url: bool = False) -> bytes:
    s = m.decode("ascii") if isinstance(m, bytes) else str(m)
    s = "".join(s.split())
    s += "=" * (-len(s) % 4)
    try:
        return (base64.urlsafe_b64decode(s) if url
                else base64.b64decode(s, validate=True))
    except (binascii.Error, ValueError):
        raise _xəta("Base64 formatı pozulub")


def _hex_aç(m: str) -> bytes:
    try:
        return bytes.fromhex("".join(str(m).split()))
    except ValueError:
        raise _xəta("hex formatı pozulub (0-9, a-f cütləri gözlənilir)")


_AZ = str.maketrans({"ə": "e", "Ə": "e", "ı": "i", "I": "i", "İ": "i",
                     "ö": "o", "Ö": "o", "ü": "u", "Ü": "u", "ç": "c",
                     "Ç": "c", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g"})


def slug(m: str, ayırıcı: str = "-") -> str:
    """URL və fayl adı üçün: kiçik ASCII, sözlər `-` ilə."""
    s = str(m).translate(_AZ).lower()
    s = re.sub(r"[^a-z0-9]+", ayırıcı, s)
    return s.strip(ayırıcı)


def _sorğu_kodla(l: dict) -> str:
    cütlər = []
    for a, d in l.items():
        if isinstance(d, (list, tuple)):
            cütlər.extend((str(a), _sadə(x)) for x in d)
        elif d is not None:
            cütlər.append((str(a), _sadə(d)))
    return urlencode(cütlər, quote_via=quote)


def _sadə(d: Any) -> str:
    if d is True:
        return "doğru"
    if d is False:
        return "yanlış"
    return str(d)


def _sorğu_aç(m: str) -> dict:
    n: dict[str, Any] = {}
    for a, d in parse_qs(str(m).lstrip("?"), keep_blank_values=True).items():
        n[a] = d[0] if len(d) == 1 else d
    return n


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "base64Kodla": D("base64Kodla", lambda x: base64.b64encode(
            _bayt(x, "base64Kodla")).decode("ascii"), 1, 1),
        "base64Aç": D("base64Aç", lambda m: _b64_aç(m), 1, 1),
        "base64AçMətn": D("base64AçMətn", lambda m: _mətn(
            _b64_aç(m), "base64AçMətn"), 1, 1),
        "base64URLKodla": D("base64URLKodla", lambda x: base64
                            .urlsafe_b64encode(_bayt(x, "base64URLKodla"))
                            .decode("ascii").rstrip("="), 1, 1),
        "base64URLAç": D("base64URLAç", lambda m: _b64_aç(m, True), 1, 1),
        "hexKodla": D("hexKodla", lambda x: _bayt(x, "hexKodla").hex(),
                      1, 1),
        "hexAç": D("hexAç", _hex_aç, 1, 1),
        "urlKodla": D("urlKodla", lambda m: quote(str(m), safe=""), 1, 1),
        "urlAç": D("urlAç", lambda m: unquote(str(m)), 1, 1),
        "yolKodla": D("yolKodla", lambda m: quote(str(m), safe="/"), 1, 1),
        "sorğuKodla": D("sorğuKodla", _sorğu_kodla, 1, 1),
        "sorğuAç": D("sorğuAç", _sorğu_aç, 1, 1),
        "htmlQaç": D("htmlQaç", lambda m: html.escape(str(m)), 1, 1),
        "htmlAç": D("htmlAç", lambda m: html.unescape(str(m)), 1, 1),
        "utf8Kodla": D("utf8Kodla", lambda m: str(m).encode("utf-8"), 1, 1),
        "utf8Aç": D("utf8Aç", lambda b: _mətn(_bayt(b, "utf8Aç"),
                                               "utf8Aç"), 1, 1),
        "baytlar": D("baytlar", lambda x: list(_bayt(x, "baytlar")), 1, 1),
        "crc32": D("crc32", lambda x: zlib.crc32(_bayt(x, "crc32")), 1, 1),
        "slug": D("slug", slug, 1, 2),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b, i = T.MƏTN, T.İSTƏNİLƏN, T.BAYT, T.TAM
    return {
        "base64Kodla": F(e, qaytarır=m), "base64Aç": F(e, qaytarır=b),
        "base64AçMətn": F(e, qaytarır=m),
        "base64URLKodla": F(e, qaytarır=m), "base64URLAç": F(e, qaytarır=b),
        "hexKodla": F(e, qaytarır=m), "hexAç": F(m, qaytarır=b),
        "urlKodla": F(m, qaytarır=m), "urlAç": F(m, qaytarır=m),
        "yolKodla": F(m, qaytarır=m),
        "sorğuKodla": F(T.Lüğət(), qaytarır=m),
        "sorğuAç": F(m, qaytarır=T.Lüğət(m, e)),
        "htmlQaç": F(e, qaytarır=m), "htmlAç": F(m, qaytarır=m),
        "utf8Kodla": F(m, qaytarır=b), "utf8Aç": F(e, qaytarır=m),
        "baytlar": F(e, qaytarır=T.Siyahı(i)),
        "crc32": F(e, qaytarır=i),
        "slug": F(m, m, qaytarır=m, standart=1),
    }
