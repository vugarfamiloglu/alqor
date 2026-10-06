"""
Alqor — Standart kitabxana.

Üç hissə:
  1. `nüvə` — avtomatik əlçatan qlobal funksiyalar
  2. Daxili tiplərin metodları (`"salam".böyüyə()`, `siyahı.filtr(...)`)
  3. Modullar (`riyaziyyat`, `vaxt`, `fayl`, `json` ...)
"""

from __future__ import annotations
import base64
import html
import json as _json
import math
import os
import random as _random
import re as _re
import sys
import time as _time
import urllib.parse
from pathlib import Path
from typing import Any, Callable

from . import elifba as E
from .korutin import Gələcək, Korutin, LəğvNişanı
from .deyerler import (AlqorDiapazon, AlqorGenerator, AlqorXəta, BağlıMetod,
                       Element,
                       Çağırılan, Daxili, DayanmaSiqnalı, Funksiya, Modul,
                       Mühit, Nümunə, Sadalama, SadalamaDəyəri, Sinif,
                       mətnə, tip_adı)

# Genişlətmələr: tip adı → {metod adı: Funksiya}
_GENİŞLƏTMƏLƏR: dict[str, dict[str, Funksiya]] = {}


def genişlətmə_qeyd(tip: str, ad: str, f: Funksiya) -> None:
    _GENİŞLƏTMƏLƏR.setdefault(tip, {})[ad] = f


# ═══════════════════════════════════════════════════════════════════════
#  Köməkçilər
# ═══════════════════════════════════════════════════════════════════════

def _çağır(icraçı, f: Any, *arqumentlər) -> Any:
    return icraçı._çağır(f, list(arqumentlər), {}, None)


def _xəta(tip: str, mesaj: str, kod: str = "") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, kod)


def _tam_yoxla(dəyər: Any, ad: str) -> int:
    if not isinstance(dəyər, int) or isinstance(dəyər, bool):
        raise _xəta("TipXətası",
                    f"`{ad}` tam ədəd gözləyir, `{tip_adı(dəyər)}` gəlib",
                    "ALQ-T004")
    return dəyər


def _mətn_yoxla(dəyər: Any, ad: str) -> str:
    if not isinstance(dəyər, str):
        raise _xəta("TipXətası",
                    f"`{ad}` mətn gözləyir, `{tip_adı(dəyər)}` gəlib",
                    "ALQ-T004")
    return dəyər


def _indeks(kolleksiya: Any, i: int) -> int:
    n = len(kolleksiya)
    j = i + n if i < 0 else i
    if not 0 <= j < n:
        raise _xəta("İndeksXətası",
                    f"indeks {i} diapazondan kənardır (uzunluq {n})",
                    "ALQ-R002")
    return j


# ═══════════════════════════════════════════════════════════════════════
#  1. NÜVƏ — qlobal funksiyalar
# ═══════════════════════════════════════════════════════════════════════

def qlobal_mühit(icraçı) -> Mühit:
    m = Mühit()

    def d(ad: str, f: Callable, min_arq: int = 0,
          maks_arq: int | None = None) -> None:
        m.elan(ad, Daxili(ad, f, min_arq, maks_arq))

    # ── Giriş / Çıxış ───────────────────────────────────────
    def yaz(*arqumentlər):
        icraçı.çıxış(" ".join(mətnə(a, icraçı) for a in arqumentlər))

    def yazSətirsiz(*arqumentlər):
        sys.stdout.write(" ".join(mətnə(a, icraçı) for a in arqumentlər))
        sys.stdout.flush()

    def yazXəta(*arqumentlər):
        print(" ".join(mətnə(a, icraçı) for a in arqumentlər),
              file=sys.stderr)

    def oxu(soruş: str = ""):
        if soruş:
            sys.stdout.write(soruş)
            sys.stdout.flush()
        try:
            return icraçı.giriş()
        except EOFError:
            # Girişin sonu — "" qaytarmaq `həmişə` dövrlərini sonsuz
            # fırlandırırdı. Python `input()` kimi xəta atırıq.
            raise _xəta("GirişÇıxışXətası",
                        "girişin sonu — oxunacaq məlumat qalmadı",
                        "ALQ-R009")

    def oxuTam(soruş: str = "", təkrar: bool = True):
        while True:
            m_ = oxu(soruş)
            try:
                return int(m_.strip())
            except ValueError:
                if not təkrar:
                    raise _xəta("ÇevrilməXətası",
                                f'"{m_}" tam ədəd deyil', "ALQ-R005")
                yaz("Düzgün tam ədəd daxil edin.")

    def oxuOnluq(soruş: str = ""):
        while True:
            m_ = oxu(soruş)
            try:
                return float(m_.strip().replace(",", "."))
            except ValueError:
                yaz("Düzgün ədəd daxil edin.")

    def oxuMəntiq(soruş: str = ""):
        while True:
            c = E.kiçiyə(oxu(soruş).strip())
            if c in ("hə", "he", "bəli", "beli", "doğru", "dogru", "h", "b"):
                return True
            if c in ("yox", "xeyr", "yanlış", "yanlis", "y", "x"):
                return False
            yaz("`hə` və ya `yox` yazın.")

    d("yaz", yaz)
    d("yazSətirsiz", yazSətirsiz)
    d("yazXəta", yazXəta)
    d("oxu", oxu, 0, 1)
    d("oxuTam", oxuTam, 0, 2)
    d("oxuOnluq", oxuOnluq, 0, 1)
    d("oxuMəntiq", oxuMəntiq, 0, 1)
    d("oxuHamısı", lambda: sys.stdin.read())

    # ── Tip və çevirmə ──────────────────────────────────────
    d("tip", lambda x: tip_adı(x), 1, 1)

    def tamƏt(x, standart=None, əsas=10):
        try:
            if isinstance(x, bool):
                return 1 if x else 0
            if isinstance(x, (int, float)):
                return int(x)
            return int(str(x).strip(), əsas)
        except (ValueError, TypeError):
            if standart is not None:
                return standart
            raise _xəta("ÇevrilməXətası",
                        f'"{mətnə(x, icraçı)}" tam ədədə çevrilə bilmir',
                        "ALQ-R005")

    def onluqƏt(x, standart=None):
        try:
            if isinstance(x, bool):
                return 1.0 if x else 0.0
            return float(str(x).strip().replace(",", ".")) \
                if isinstance(x, str) else float(x)
        except (ValueError, TypeError):
            if standart is not None:
                return standart
            raise _xəta("ÇevrilməXətası",
                        f'"{mətnə(x, icraçı)}" ədədə çevrilə bilmir',
                        "ALQ-R005")

    d("tamƏt", tamƏt, 1, 3)
    d("onluqƏt", onluqƏt, 1, 2)
    d("mətnƏt", lambda x: mətnə(x, icraçı), 1, 1)
    d("məntiqƏt", lambda x: icraçı._çevir(x, "məntiq", None), 1, 1)
    d("simvolƏt", lambda k: chr(_tam_yoxla(k, "simvolƏt")), 1, 1)
    d("kodƏt", lambda s: ord(_mətn_yoxla(s, "kodƏt")[0]), 1, 1)

    # ── Kolleksiya köməkçiləri ──────────────────────────────
    def uzunluq(x):
        if isinstance(x, Nümunə):
            metod = x.sinif.metod_tap("uzunluq")
            if metod is not None:
                return icraçı.funksiya_çağır(metod.bağla(x), [], {})
        if isinstance(x, (str, list, dict, set, tuple, bytes,
                          AlqorDiapazon)):
            return len(x)
        raise _xəta("TipXətası",
                    f"`{tip_adı(x)}` tipinin uzunluğu yoxdur", "ALQ-T006")

    def boşdur(x):
        if x is None:
            return True
        return uzunluq(x) == 0

    def _say_yoxla(k):
        elementlər = list(icraçı._iterasiya(k, None))
        for e in elementlər:
            if not isinstance(e, (int, float)) or isinstance(e, bool):
                raise _xəta("TipXətası",
                            f"ədəd gözlənilirdi, `{tip_adı(e)}` gəlib",
                            "ALQ-T004")
        return elementlər

    def cəm(k, başlanğıc=0):
        return sum(_say_yoxla(k), başlanğıc)

    def minimum(*a):
        k = list(icraçı._iterasiya(a[0], None)) if len(a) == 1 else list(a)
        if not k:
            raise _xəta("BoşKolleksiyaXətası",
                        "boş kolleksiyada minimum yoxdur", "ALQ-R014")
        return min(k, key=_sıralama_açarı)

    def maksimum(*a):
        k = list(icraçı._iterasiya(a[0], None)) if len(a) == 1 else list(a)
        if not k:
            raise _xəta("BoşKolleksiyaXətası",
                        "boş kolleksiyada maksimum yoxdur", "ALQ-R014")
        return max(k, key=_sıralama_açarı)

    def sırala(k, açar=None):
        elementlər = list(icraçı._iterasiya(k, None))
        if açar is None:
            return sorted(elementlər, key=_sıralama_açarı)
        return sorted(elementlər, key=lambda x: _sıralama_açarı(
            _çağır(icraçı, açar, x)))

    d("uzunluq", uzunluq, 1, 1)
    d("boşdur", boşdur, 1, 1)
    d("cəm", cəm, 1, 2)
    d("minimum", minimum, 1)
    d("maksimum", maksimum, 1)
    d("sırala", sırala, 1, 2)
    d("tərs", lambda k: list(reversed(list(icraçı._iterasiya(k, None)))),
      1, 1)
    d("nömrələ", lambda k: [(i, x) for i, x in
                            enumerate(icraçı._iterasiya(k, None))], 1, 1)
    d("zip", lambda *k: [tuple(t) for t in zip(
        *[list(icraçı._iterasiya(x, None)) for x in k])], 1)
    d("diapazon", lambda *a: _diapazon_yarat(a), 1, 3)
    d("siyahı", lambda k=None: ([] if k is None
                                else list(icraçı._iterasiya(k, None))), 0, 1)
    d("dəst", lambda *a: (set(icraçı._iterasiya(a[0], None))
                          if len(a) == 1 and isinstance(
                              a[0], (list, tuple, set, AlqorDiapazon))
                          else set(a)), 0)
    d("lüğət", lambda k=None: {} if k is None else dict(k), 0, 1)
    d("kortej", lambda k=None: () if k is None
      else tuple(icraçı._iterasiya(k, None)), 0, 1)

    # ── Digər ───────────────────────────────────────────────
    def klonla(x):
        import copy
        if isinstance(x, Nümunə):
            return x.klonla()
        if isinstance(x, (list, dict, set)):
            return copy.deepcopy(x)
        return x

    def çap(*a):
        for x in a:
            icraçı.çıxış(f"{tip_adı(x)} = {mətnə(x, icraçı)}")

    def ölç(f):
        başlanğıc = _time.perf_counter()
        nəticə = _çağır(icraçı, f)
        müddət = (_time.perf_counter() - başlanğıc) * 1000
        icraçı.çıxış(f"⏱ {müddət:.3f} ms")
        return nəticə

    def panika(mesaj=""):
        raise AlqorXəta("KritikXəta", mətnə(mesaj, icraçı) or "panika",
                        None, "ALQ-R008")

    def dayan(kod=0):
        raise DayanmaSiqnalı(_tam_yoxla(kod, "dayan"))

    d("klonla", klonla, 1, 1)
    d("çap", çap, 1)
    d("ölç", ölç, 1, 1)
    d("panika", panika, 0, 1)
    d("dayan", dayan, 0, 1)
    d("eynidir", lambda a, b: a is b, 2, 2)
    d("heş", lambda x: hash(x) if not isinstance(x, Nümunə) else id(x), 1, 1)

    # ── Asinxron köməkçi tiplər ─────────────────────────────
    m.elan("LəğvNişanı", Daxili(
        "LəğvNişanı",
        lambda saniyə=None: LəğvNişanı(saniyə), 0, 1))
    m.elan("Gələcək", Daxili(
        "Gələcək", lambda f: Gələcək(lambda: _çağır(icraçı, f)), 1, 1))

    # ── Xəta sinifləri — `at Xəta("...")` üçün ──────────────
    from .deyerler import XETA_AGACI
    for xəta_adı in XETA_AGACI:
        if xəta_adı == "Atılan":
            continue
        m.elan(xəta_adı, _XətaSinfi(xəta_adı))

    # ── Modullar ────────────────────────────────────────────
    for ad, modul in _modulları_qur(icraçı).items():
        m.elan(ad, modul)

    return m


def _diapazon_yarat(a: tuple) -> AlqorDiapazon:
    if len(a) == 1:
        return AlqorDiapazon(0, _tam_yoxla(a[0], "diapazon"), None, True)
    if len(a) == 2:
        return AlqorDiapazon(a[0], a[1], None, True)
    return AlqorDiapazon(a[0], a[1], a[2], True)


def _sıralama_açarı(x: Any):
    if isinstance(x, str):
        return (1,) + E.sıralama_açarı(x)[0]
    if isinstance(x, bool):
        return (0, int(x))
    if isinstance(x, (int, float)):
        return (0, x)
    return (2, id(x))


class _XətaSinfi(Çağırılan):
    """`Xəta("mesaj")`, `ArqumentXətası("mesaj", kod: 5)` yaradır."""

    def __init__(self, ad: str):
        self.ad = ad

    def çağır(self, icraçı, arqumentlər, adlı, yer=None):
        s = Sinif(self.ad)
        n = Nümunə(s)
        n.sahələr["mesaj"] = (mətnə(arqumentlər[0], icraçı)
                              if arqumentlər else "")
        n.sahələr["tip"] = self.ad
        n.sahələr["kod"] = adlı.get("kod")
        n.sahələr["səbəb"] = adlı.get("səbəb")
        for a, dd in adlı.items():
            n.sahələr.setdefault(a, dd)
        return n

    def __repr__(self) -> str:
        return f"<xəta {self.ad}>"


# ═══════════════════════════════════════════════════════════════════════
#  2. DAXİLİ TİPLƏRİN METODLARI
# ═══════════════════════════════════════════════════════════════════════

def mövcud_üzvlər(obyekt: Any) -> list[str]:
    """Obyektin bütün mümkün üzv adları — xəta təklifləri üçün."""
    adlar: list[str] = []
    tip = tip_adı(obyekt).split("[")[0]
    adlar.extend(_GENİŞLƏTMƏLƏR.get(tip, {}))
    cədvəl = _CƏDVƏLLƏR.get(type(obyekt))
    if cədvəl is None:
        if isinstance(obyekt, AlqorDiapazon):
            cədvəl = _DIAPAZON
        elif isinstance(obyekt, AlqorGenerator):
            cədvəl = _GENERATOR
    if cədvəl:
        adlar.extend(cədvəl)
    if isinstance(obyekt, Nümunə):
        adlar.extend(obyekt.sahələr)
        s = obyekt.sinif
        while s is not None:
            adlar.extend(s.metodlar)
            adlar.extend(s.hesablananlar)
            s = s.baza
    if isinstance(obyekt, Modul):
        adlar.extend(obyekt.üzvlər)
    return sorted(set(adlar))


def daxili_metod(icraçı, obyekt: Any, ad: str) -> BağlıMetod | None:
    """`obyekt.ad` — daxili tip metodu varsa qaytarır."""
    tip = tip_adı(obyekt).split("[")[0]

    # İstifadəçi genişlətmələri daxili metodları üstələyir
    gen = _GENİŞLƏTMƏLƏR.get(tip)
    if gen and ad in gen:
        return BağlıMetod(ad, obyekt,
                          lambda o, *a: icraçı.funksiya_çağır(
                              gen[ad].bağla(o), list(a), {}))

    cədvəl = _CƏDVƏLLƏR.get(type(obyekt))
    if cədvəl is None:
        if isinstance(obyekt, AlqorDiapazon):
            cədvəl = _DIAPAZON
        elif isinstance(obyekt, AlqorGenerator):
            cədvəl = _GENERATOR
        elif isinstance(obyekt, bool):
            cədvəl = _MƏNTİQ
        else:
            return None

    f = cədvəl.get(ad)
    if f is None:
        return None
    return BağlıMetod(ad, obyekt, lambda o, *a, **k: f(icraçı, o, *a, **k))


# ── Mətn metodları (az-AZ qaydaları ilə) ───────────────────────────────

def _m_formatla(icraçı, s, *a):
    nəticə = s
    for i, dəyər in enumerate(a):
        nəticə = nəticə.replace("{}", mətnə(dəyər, icraçı), 1)
        nəticə = nəticə.replace("{" + str(i) + "}", mətnə(dəyər, icraçı))
    return nəticə


_MƏTN: dict[str, Callable] = {
    "uzunluq": lambda i, s: len(s),
    "baytUzunluğu": lambda i, s: len(s.encode("utf-8")),
    "böyüyə": lambda i, s: E.böyüyə(s),
    "kiçiyə": lambda i, s: E.kiçiyə(s),
    "başBöyük": lambda i, s: E.baş_böyük(s),
    "hərSözBöyük": lambda i, s: E.hər_söz_böyük(s),
    "kəs": lambda i, s, c=None: s.strip() if c is None else s.strip(c),
    "başKəs": lambda i, s, c=None: s.lstrip() if c is None else s.lstrip(c),
    "sonKəs": lambda i, s, c=None: s.rstrip() if c is None else s.rstrip(c),
    "əvəz": lambda i, s, a, b: s.replace(a, b),
    "əvəzİlk": lambda i, s, a, b: s.replace(a, b, 1),
    "böl": lambda i, s, ayırıcı=None, maks=-1: (
        s.split() if ayırıcı is None else s.split(ayırıcı, maks)),
    "sətirlər": lambda i, s: s.split("\n"),
    "simvollar": lambda i, s: list(s),
    "sözlər": lambda i, s: s.split(),
    "baytlar": lambda i, s: list(s.encode("utf-8")),
    "birləşdir": lambda i, s, k: s.join(
        mətnə(x, i) for x in i._iterasiya(k, None)),
    "ehtiva": lambda i, s, alt: alt in s,
    "başlayır": lambda i, s, alt: s.startswith(alt),
    "bitir": lambda i, s, alt: s.endswith(alt),
    "tap": lambda i, s, alt: (None if s.find(alt) < 0 else s.find(alt)),
    "sonTap": lambda i, s, alt: (None if s.rfind(alt) < 0 else s.rfind(alt)),
    "hamısınıTap": lambda i, s, alt: [
        k.start() for k in _re.finditer(_re.escape(alt), s)],
    "say": lambda i, s, alt: s.count(alt),
    "dilim": lambda i, s, b, ss=None: s[b:ss],
    "təkrar": lambda i, s, n: s * _tam_yoxla(n, "təkrar"),
    "tərs": lambda i, s: s[::-1],
    "doldur": lambda i, s, n, c=" ": s.ljust(n, c),
    "solDoldur": lambda i, s, n, c=" ": s.rjust(n, c),
    "sağDoldur": lambda i, s, n, c=" ": s.ljust(n, c),
    "mərkəz": lambda i, s, n, c=" ": s.center(n, c),
    "boşdur": lambda i, s: len(s) == 0,
    "yalnızBoşluq": lambda i, s: len(s) > 0 and s.isspace(),
    "rəqəmdir": lambda i, s: len(s) > 0 and all(E.rəqəmdir(c) for c in s),
    "hərfdir": lambda i, s: len(s) > 0 and all(E.hərfdir(c) for c in s),
    "müqayisə": lambda i, s, d: E.müqayisə(s, d),
    "müqayisəHərfsiz": lambda i, s, d: E.müqayisə(E.kiçiyə(s), E.kiçiyə(d)),
    "normalizasiya": lambda i, s: __import__(
        "unicodedata").normalize("NFC", s),
    "latınla": lambda i, s: E.latınla(s),
    "URLKodla": lambda i, s: urllib.parse.quote(s, safe=""),
    "URLAç": lambda i, s: urllib.parse.unquote(s),
    "base64Kodla": lambda i, s: base64.b64encode(
        s.encode("utf-8")).decode("ascii"),
    "base64Aç": lambda i, s: base64.b64decode(s).decode("utf-8"),
    "HTMLQaç": lambda i, s: html.escape(s),
    "formatla": _m_formatla,
    "mətnƏt": lambda i, s: s,
    "klonla": lambda i, s: s,
    "tamƏt": lambda i, s: int(s.strip()),
    "saitdir": lambda i, s: len(s) == 1 and E.saitdir(s),
    "samitdir": lambda i, s: len(s) == 1 and E.samitdir(s),
    "qalınSait": lambda i, s: len(s) == 1 and E.qalın_saitdir(s),
    "incəSait": lambda i, s: len(s) == 1 and E.incə_saitdir(s),
}


# ── Siyahı metodları ───────────────────────────────────────────────────

def _s_sil(i, s, indeks):
    return s.pop(_indeks(s, _tam_yoxla(indeks, "sil")))


def _s_sonunu_sil(i, s):
    if not s:
        raise _xəta("BoşKolleksiyaXətası", "boş siyahıdan element silinmir",
                    "ALQ-R014")
    return s.pop()


def _s_sil_dəyər(i, s, dəyər):
    for j, x in enumerate(s):
        if i._bərabərdir(x, dəyər):
            s.pop(j)
            return True
    return False


def _s_yığ(i, s, başlanğıc, f):
    nəticə = başlanğıc
    for x in s:
        nəticə = _çağır(i, f, nəticə, x)
    return nəticə


def _s_qrupla(i, s, f):
    nəticə: dict[Any, list] = {}
    for x in s:
        nəticə.setdefault(_çağır(i, f, x), []).append(x)
    return nəticə


def _s_təkrarsız(i, s):
    nəticə: list[Any] = []
    for x in s:
        if not any(i._bərabərdir(x, y) for y in nəticə):
            nəticə.append(x)
    return nəticə


def _s_düzlə(i, s):
    nəticə: list[Any] = []
    for x in s:
        if isinstance(x, list):
            nəticə.extend(x)
        else:
            nəticə.append(x)
    return nəticə


def _s_tap(i, s, f):
    for x in s:
        if _çağır(i, f, x) is True:
            return x
    return None


def _s_tap_indeks(i, s, f):
    for j, x in enumerate(s):
        if _çağır(i, f, x) is True:
            return j
    return None


def _s_indeks(i, s, dəyər):
    for j, x in enumerate(s):
        if i._bərabərdir(x, dəyər):
            return j
    return None


def _s_sırala(i, s, müqayisə=None):
    if müqayisə is None:
        s.sort(key=_sıralama_açarı)
    else:
        import functools
        s.sort(key=functools.cmp_to_key(
            lambda a, b: _çağır(i, müqayisə, a, b)))
    return None


def _s_orta(i, s):
    if not s:
        raise _xəta("BoşKolleksiyaXətası", "boş siyahının ortası yoxdur",
                    "ALQ-R014")
    return sum(s) / len(s)


_SIYAHI: dict[str, Callable] = {
    "əlavə": lambda i, s, x: (s.append(x), None)[1],
    "əlavəHamısı": lambda i, s, k: (
        s.extend(i._iterasiya(k, None)), None)[1],
    "daxilEt": lambda i, s, j, x: (s.insert(j, x), None)[1],
    "sil": _s_sil,
    "silDəyər": _s_sil_dəyər,
    "silHamısı": lambda i, s, d: (
        s.__setitem__(slice(None),
                      [x for x in s if not i._bərabərdir(x, d)]), None)[1],
    "sonunuSil": _s_sonunu_sil,
    "təmizlə": lambda i, s: (s.clear(), None)[1],
    "sırala": _s_sırala,
    "sıralaAçar": lambda i, s, f: (s.sort(
        key=lambda x: _sıralama_açarı(_çağır(i, f, x))), None)[1],
    "qarışdır": lambda i, s: (_random.shuffle(s), None)[1],
    "tərsinəÇevir": lambda i, s: (s.reverse(), None)[1],
    "sıralanmış": lambda i, s, f=None: (
        sorted(s, key=_sıralama_açarı) if f is None else
        sorted(s, key=lambda x: _sıralama_açarı(_çağır(i, f, x)))),
    "tərs": lambda i, s: list(reversed(s)),
    "dilim": lambda i, s, b, ss=None: s[b:ss],
    "çevir": lambda i, s, f: [_çağır(i, f, x) for x in s],
    "filtr": lambda i, s, f: [x for x in s if _çağır(i, f, x) is True],
    "yığ": _s_yığ,
    "yığSağdan": lambda i, s, b, f: _s_yığ(i, list(reversed(s)), b, f),
    "düzlə": _s_düzlə,
    "düzləÇevir": lambda i, s, f: _s_düzlə(
        i, [_çağır(i, f, x) for x in s]),
    "təkrarsız": _s_təkrarsız,
    "birləşdir": lambda i, s, d: s + list(i._iterasiya(d, None)),
    "qrupla": _s_qrupla,
    "hissələrə": lambda i, s, n: [s[j:j + n] for j in range(0, len(s), n)],
    "pəncərə": lambda i, s, n: [s[j:j + n]
                                for j in range(0, len(s) - n + 1)],
    "zip": lambda i, s, d: [tuple(t) for t in
                            zip(s, i._iterasiya(d, None))],
    "nömrələ": lambda i, s: [(j, x) for j, x in enumerate(s)],
    "uzunluq": lambda i, s: len(s),
    "boşdur": lambda i, s: len(s) == 0,
    "ehtiva": lambda i, s, d: any(i._bərabərdir(x, d) for x in s),
    "tap": _s_tap,
    "tapİndeks": _s_tap_indeks,
    "indeks": _s_indeks,
    "sonİndeks": lambda i, s, d: next(
        (j for j in range(len(s) - 1, -1, -1)
         if i._bərabərdir(s[j], d)), None),
    "say": lambda i, s, d: sum(1 for x in s if i._bərabərdir(x, d)),
    "sayŞərt": lambda i, s, f: sum(1 for x in s
                                   if _çağır(i, f, x) is True),
    "hamısı": lambda i, s, f: all(_çağır(i, f, x) is True for x in s),
    "hərHansı": lambda i, s, f: any(_çağır(i, f, x) is True for x in s),
    "heçBiri": lambda i, s, f: not any(_çağır(i, f, x) is True for x in s),
    "ilk": lambda i, s: s[0] if s else None,
    "son": lambda i, s: s[-1] if s else None,
    "minimum": lambda i, s: min(s, key=_sıralama_açarı) if s else None,
    "maksimum": lambda i, s: max(s, key=_sıralama_açarı) if s else None,
    "cəm": lambda i, s: sum(s) if s else 0,
    "orta": _s_orta,
    "hərBiri": lambda i, s, f: ([_çağır(i, f, x) for x in s], None)[1],
    "klonla": lambda i, s: list(s),
    "al": lambda i, s, j, standart=None: (
        s[j] if isinstance(j, int) and -len(s) <= j < len(s) else standart),
    "mətnƏt": lambda i, s: mətnə(s, i),
    "siyahıyaÇevir": lambda i, s: list(s),
}


# ── Lüğət metodları ────────────────────────────────────────────────────

def _l_al(i, l, açar, standart=None):
    return l.get(açar, standart)


def _l_al_və_ya_qoy(i, l, açar, yaradıcı):
    if açar not in l:
        l[açar] = _çağır(i, yaradıcı)
    return l[açar]


def _l_yenilə(i, l, açar, f):
    if açar not in l:
        raise _xəta("AçarXətası", f"`{mətnə(açar, i)}` açarı yoxdur",
                    "ALQ-R003")
    l[açar] = _çağır(i, f, l[açar])
    return l[açar]


def _l_çevir(i, l, f):
    nəticə: dict[Any, Any] = {}
    for a, d in list(l.items()):
        cüt = _çağır(i, f, a, d)
        if isinstance(cüt, (tuple, list)) and len(cüt) == 2:
            nəticə[cüt[0]] = cüt[1]
        else:
            nəticə[a] = cüt
    return nəticə


_LÜĞƏT: dict[str, Callable] = {
    "al": _l_al,
    "qoy": lambda i, l, a, d: (l.__setitem__(a, d), None)[1],
    "sil": lambda i, l, a: l.pop(a, None),
    "təmizlə": lambda i, l: (l.clear(), None)[1],
    "ehtiva": lambda i, l, a: a in l,
    "ehtivaDəyər": lambda i, l, d: any(i._bərabərdir(x, d)
                                       for x in l.values()),
    "uzunluq": lambda i, l: len(l),
    "boşdur": lambda i, l: len(l) == 0,
    "açarlar": lambda i, l: list(l.keys()),
    "dəyərlər": lambda i, l: list(l.values()),
    "cütlər": lambda i, l: [(a, d) for a, d in l.items()],
    "birləşdir": lambda i, l, d: {**l, **d},
    "çevir": _l_çevir,
    "filtr": lambda i, l, f: {a: d for a, d in l.items()
                              if _çağır(i, f, a, d) is True},
    "hərBiri": lambda i, l, f: ([_çağır(i, f, a, d)
                                 for a, d in list(l.items())], None)[1],
    "alVəYaQoy": _l_al_və_ya_qoy,
    "yenilə": _l_yenilə,
    "tərsÇevir": lambda i, l: {d: a for a, d in l.items()},
    "klonla": lambda i, l: dict(l),
    "mətnƏt": lambda i, l: mətnə(l, i),
}


# ── Dəst metodları ─────────────────────────────────────────────────────

_DƏST: dict[str, Callable] = {
    "əlavə": lambda i, s, x: (s.add(x), None)[1],
    "sil": lambda i, s, x: (s.discard(x), None)[1],
    "ehtiva": lambda i, s, x: x in s,
    "uzunluq": lambda i, s: len(s),
    "boşdur": lambda i, s: len(s) == 0,
    "təmizlə": lambda i, s: (s.clear(), None)[1],
    "birləşmə": lambda i, s, d: s | d,
    "kəsişmə": lambda i, s, d: s & d,
    "fərq": lambda i, s, d: s - d,
    "simmetrikFərq": lambda i, s, d: s ^ d,
    "altDəstdir": lambda i, s, d: s <= d,
    "üstDəstdir": lambda i, s, d: s >= d,
    "kəsişmir": lambda i, s, d: s.isdisjoint(d),
    "siyahıyaÇevir": lambda i, s: sorted(s, key=_sıralama_açarı),
    "çevir": lambda i, s, f: {_çağır(i, f, x) for x in s},
    "filtr": lambda i, s, f: {x for x in s if _çağır(i, f, x) is True},
    "klonla": lambda i, s: set(s),
    "mətnƏt": lambda i, s: mətnə(s, i),
}


# ── Ədəd / məntiq / kortej / diapazon ──────────────────────────────────

_TAM: dict[str, Callable] = {
    "mətnƏt": lambda i, n: mətnə(n, i),
    "mütləq": lambda i, n: abs(n),
    "işarə": lambda i, n: (0 if n == 0 else (1 if n > 0 else -1)),
    "cütdür": lambda i, n: n % 2 == 0,
    "təkdir": lambda i, n: n % 2 != 0,
    "kvadrat": lambda i, n: n * n,
    "onluğaÇevir": lambda i, n: float(n),
    "ikilik": lambda i, n: format(n, "b"),
    "onaltılıq": lambda i, n: format(n, "x"),
    "sıraSayı": lambda i, n: _sıra_sayı(n),
    "yazıyla": lambda i, n: _yazıyla(n),
}

_ONLUQ: dict[str, Callable] = {
    "mətnƏt": lambda i, n: mətnə(n, i),
    "mütləq": lambda i, n: abs(n),
    "yuvarlaqlaşdır": lambda i, n, r=0: (round(n, r) if r else round(n)),
    "aşağıYuvarlaq": lambda i, n: math.floor(n),
    "yuxarıYuvarlaq": lambda i, n: math.ceil(n),
    "kəs": lambda i, n: int(n),
    "tamƏt": lambda i, n: int(n),
    "tamdır": lambda i, n: float(n).is_integer(),
    "sonludur": lambda i, n: math.isfinite(n),
    "ədəddir": lambda i, n: not math.isnan(n),
}

_MƏNTİQ: dict[str, Callable] = {
    "mətnƏt": lambda i, b: "doğru" if b else "yanlış",
    "tamƏt": lambda i, b: 1 if b else 0,
}

_KORTEJ: dict[str, Callable] = {
    "uzunluq": lambda i, t: len(t),
    "siyahıyaÇevir": lambda i, t: list(t),
    "mətnƏt": lambda i, t: mətnə(t, i),
    "ehtiva": lambda i, t, d: any(i._bərabərdir(x, d) for x in t),
}

_DIAPAZON: dict[str, Callable] = {
    "siyahıyaÇevir": lambda i, d: list(d),
    "uzunluq": lambda i, d: len(d),
    "ehtiva": lambda i, d, x: x in d,
    "mətnƏt": lambda i, d: repr(d),
    "çevir": lambda i, d, f: [_çağır(i, f, x) for x in d],
    "filtr": lambda i, d, f: [x for x in d if _çağır(i, f, x) is True],
    "cəm": lambda i, d: sum(d),
}

_GENERATOR: dict[str, Callable] = {
    "növbəti": lambda i, g: g.növbəti(),
    "bitdi": lambda i, g: g.bitdi(),
    "bağla": lambda i, g: (g.bağla(), None)[1],
    "siyahıyaÇevir": lambda i, g: g.siyahıyaÇevir(),
    # Sonsuz generatorlar üçün təhlükəsiz metodlar
    "ilk": lambda i, g, n: g.ilk(n),
    "çevir": lambda i, g, f: _gen_çevir(i, g, f),
    "filtr": lambda i, g, f: _gen_filtr(i, g, f),
    "atla": lambda i, g, n: _gen_atla(i, g, n),
    "tap": lambda i, g, f: _gen_tap(i, g, f),
    "hərBiri": lambda i, g, f: ([_çağır(i, f, x) for x in g], None)[1],
    "cəm": lambda i, g: sum(g),
    "uzunluq": lambda i, g: sum(1 for _ in g),
}


def _gen_çevir(icraçı, g, f):
    from .deyerler import AlqorGenerator
    return AlqorGenerator(iter(_çağır(icraçı, f, x) for x in g))


def _gen_filtr(icraçı, g, f):
    from .deyerler import AlqorGenerator
    return AlqorGenerator(
        iter(x for x in g if _çağır(icraçı, f, x) is True))


def _gen_atla(icraçı, g, n):
    from .deyerler import AlqorGenerator

    def axın():
        atlanan = 0
        for x in g:
            if atlanan < n:
                atlanan += 1
                continue
            yield x
    return AlqorGenerator(axın())


def _gen_tap(icraçı, g, f):
    for x in g:
        if _çağır(icraçı, f, x) is True:
            return x
    return None

_BAYT: dict[str, Callable] = {
    "uzunluq": lambda i, b: len(b),
    "mətnƏt": lambda i, b: b.decode("utf-8", "replace"),
    "siyahıyaÇevir": lambda i, b: list(b),
    "base64Kodla": lambda i, b: base64.b64encode(b).decode("ascii"),
}

_ELEMENT: dict[str, Callable] = {
    "HTML": lambda i, e: e.HTML(i),
    "mətn": lambda i, e: e.mətn(i),
    "mətnƏt": lambda i, e: e.HTML(i),
    "tap": lambda i, e, teq: e.tap(teq),
    "atribut": lambda i, e, ad, standart=None: e.atribut(ad, standart),
    "uzunluq": lambda i, e: len(e.uşaqlar),
    "uşaqSayı": lambda i, e: len(e.uşaqlar),
    "boşdur": lambda i, e: len(e.uşaqlar) == 0,
}

_GƏLƏCƏK: dict[str, Callable] = {
    "al": lambda i, g, limit=None: i.gözlə(g, None),
    "başlat": lambda i, g: g.başlat(),
    "bitdi": lambda i, g: g.bitdimi,
    "uğurludur": lambda i, g: g.uğurludurmu,
    "mətnƏt": lambda i, g: repr(g),
}

_LƏĞV: dict[str, Callable] = {
    "ləğvEt": lambda i, n: (n.ləğvEt(), None)[1],
    "ləğvolunub": lambda i, n: n.ləğvolunub,
    "gözlə": lambda i, n, s=None: n.gözlə(s),
    "yoxla": lambda i, n: _ləğv_yoxla(n),
}


def _ləğv_yoxla(n):
    if n.ləğvolunub:
        raise _xəta("Xəta", "əməliyyat ləğv edildi", "ALQ-R021")
    return None


_CƏDVƏLLƏR: dict[type, dict[str, Callable]] = {
    Element: _ELEMENT,
    Gələcək: _GƏLƏCƏK,
    LəğvNişanı: _LƏĞV,
    str: _MƏTN,
    list: _SIYAHI,
    dict: _LÜĞƏT,
    set: _DƏST,
    int: _TAM,
    float: _ONLUQ,
    bool: _MƏNTİQ,
    tuple: _KORTEJ,
    bytes: _BAYT,
}


# ── Azərbaycan dilinə xas köməkçilər ───────────────────────────────────

_BİRLƏR = ["", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi",
           "səkkiz", "doqquz"]
_ONLAR = ["", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş",
          "səksən", "doxsan"]
_SIRA = {1: "birinci", 2: "ikinci", 3: "üçüncü", 4: "dördüncü",
         5: "beşinci", 6: "altıncı", 7: "yeddinci", 8: "səkkizinci",
         9: "doqquzuncu", 10: "onuncu"}


def _sıra_sayı(n: int) -> str:
    return _SIRA.get(n, f"{n}-ci")


def _yazıyla(n: int) -> str:
    if n == 0:
        return "sıfır"
    if n < 0:
        return "mənfi " + _yazıyla(-n)
    hissələr: list[str] = []
    if n >= 1000:
        min_ = n // 1000
        hissələr.append(("" if min_ == 1 else _yazıyla(min_) + " ") + "min")
        n %= 1000
    if n >= 100:
        y = n // 100
        hissələr.append(("" if y == 1 else _BİRLƏR[y] + " ") + "yüz")
        n %= 100
    if n >= 10:
        hissələr.append(_ONLAR[n // 10])
        n %= 10
    if n > 0:
        hissələr.append(_BİRLƏR[n])
    return " ".join(h for h in hissələr if h).strip()


# ═══════════════════════════════════════════════════════════════════════
#  Sadalama metodları
# ═══════════════════════════════════════════════════════════════════════

def sadalama_metodu(e: Sadalama, ad: str) -> Any:
    if ad == "hamısı":
        return Daxili("hamısı",
                      lambda: [e.variantlar[a] for a in e.sıra])
    if ad == "adla":
        return Daxili("adla", lambda a: e.variantlar.get(a), 1, 1)
    if ad == "dəyərlə":
        def dəyərlə(d):
            for a in e.sıra:
                v = e.variantlar[a]
                if isinstance(v, SadalamaDəyəri) and v.dəyər == d:
                    return v
            return None
        return Daxili("dəyərlə", dəyərlə, 1, 1)
    if ad == "sayı":
        return Daxili("sayı", lambda: len(e.sıra))
    return None


def sadalama_dəyər_metodu(v: SadalamaDəyəri, ad: str) -> Any:
    if ad == "sıra":
        return Daxili("sıra", lambda: v.sıra_nömrəsi)
    if ad == "dəyər":
        return Daxili("dəyər", lambda: v.dəyər)
    if ad == "adı":
        return Daxili("adı", lambda: v.ad)
    if ad == "mətnƏt":
        return Daxili("mətnƏt", lambda: v.ad)
    return None


# ═══════════════════════════════════════════════════════════════════════
#  3. MODULLAR
# ═══════════════════════════════════════════════════════════════════════

def _modulları_qur(icraçı) -> dict[str, Modul]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    # ── riyaziyyat ──────────────────────────────────────────
    riyaziyyat = Modul("riyaziyyat", {
        "Pİ": math.pi, "PI": math.pi, "E": math.e, "TAU": math.tau,
        "QIZILNİSBƏT": (1 + 5 ** 0.5) / 2,
        "SONSUZ": math.inf, "ƏDƏDDEYİL": math.nan,
        "mütləq": D("mütləq", abs, 1, 1),
        "işarə": D("işarə", lambda x: 0 if x == 0 else (1 if x > 0 else -1),
                   1, 1),
        "kök": D("kök", lambda x: math.sqrt(x) if x >= 0 else math.nan, 1, 1),
        "kubKök": D("kubKök", lambda x: math.copysign(
            abs(x) ** (1 / 3), x), 1, 1),
        "qüvvət": D("qüvvət", lambda a, b: a ** b, 2, 2),
        "eksp": D("eksp", math.exp, 1, 1),
        "loq": D("loq", math.log, 1, 2),
        "loq10": D("loq10", math.log10, 1, 1),
        "loq2": D("loq2", math.log2, 1, 1),
        "loqƏsas": D("loqƏsas", lambda x, b: math.log(x, b), 2, 2),
        "yuvarlaqlaşdır": D("yuvarlaqlaşdır",
                            lambda x, r=0: round(x, r) if r else round(x),
                            1, 2),
        "aşağıYuvarlaq": D("aşağıYuvarlaq", math.floor, 1, 1),
        "yuxarıYuvarlaq": D("yuxarıYuvarlaq", math.ceil, 1, 1),
        "kəs": D("kəs", math.trunc, 1, 1),
        "min": D("min", lambda *a: min(a, key=_sıralama_açarı), 1),
        "maks": D("maks", lambda *a: max(a, key=_sıralama_açarı), 1),
        "məhdudla": D("məhdudla", lambda x, a, b: max(a, min(b, x)), 3, 3),
        "sin": D("sin", math.sin, 1, 1), "kos": D("kos", math.cos, 1, 1),
        "tan": D("tan", math.tan, 1, 1),
        "arksin": D("arksin", math.asin, 1, 1),
        "arkkos": D("arkkos", math.acos, 1, 1),
        "arktan": D("arktan", math.atan, 1, 1),
        "arktan2": D("arktan2", math.atan2, 2, 2),
        "hipsin": D("hipsin", math.sinh, 1, 1),
        "hipkos": D("hipkos", math.cosh, 1, 1),
        "hiptan": D("hiptan", math.tanh, 1, 1),
        "dərəcəyə": D("dərəcəyə", math.degrees, 1, 1),
        "radiana": D("radiana", math.radians, 1, 1),
        "ƏBOB": D("ƏBOB", math.gcd, 2),
        "ƏKOB": D("ƏKOB", math.lcm, 2),
        "faktorial": D("faktorial", math.factorial, 1, 1),
        "sadədir": D("sadədir", lambda n: _sadədir(n), 1, 1),
        "sadəBölənlər": D("sadəBölənlər", _sadə_bölənlər, 1, 1),
        "modul": D("modul", lambda a, b: a % b, 2, 2),
        "modQüvvət": D("modQüvvət", lambda a, b, m: pow(a, b, m), 3, 3),
        "ədəddirmi": D("ədəddirmi", lambda x: isinstance(x, (int, float))
                       and not isinstance(x, bool), 1, 1),
        "sonludur": D("sonludur", math.isfinite, 1, 1),
        "tamdır": D("tamdır", lambda x: float(x).is_integer(), 1, 1),
        "orta": D("orta", lambda k: sum(k) / len(k) if k else 0.0, 1, 1),
        "median": D("median", _median, 1, 1),
        "moda": D("moda", _moda, 1, 1),
        "dispersiya": D("dispersiya", _dispersiya, 1, 1),
        "standartKənarlaşma": D("standartKənarlaşma",
                                lambda k: math.sqrt(_dispersiya(k)), 1, 1),
    })

    # ── mətn (modul səviyyəli) ──────────────────────────────
    mətn_modulu = Modul("mətn", {
        "formatla": D("formatla",
                      lambda s, *a: _m_formatla(icraçı, s, *a), 1),
        "yerliƏdəd": D("yerliƏdəd", _yerli_ədəd, 1, 2),
        "yerliPul": D("yerliPul",
                      lambda n: _yerli_ədəd(n, 2) + " ₼", 1, 1),
        "yerliFaiz": D("yerliFaiz",
                       lambda n: _yerli_ədəd(n * 100, 1) + " %", 1, 1),
        "yazıylaƏdəd": D("yazıylaƏdəd", _yazıyla, 1, 1),
        "sıraSayı": D("sıraSayı", _sıra_sayı, 1, 1),
        "saitdir": D("saitdir", lambda c: E.saitdir(c), 1, 1),
        "samitdir": D("samitdir", lambda c: E.samitdir(c), 1, 1),
        "qalınSait": D("qalınSait", lambda c: E.qalın_saitdir(c), 1, 1),
        "incəSait": D("incəSait", lambda c: E.incə_saitdir(c), 1, 1),
        "şəkilçi": D("şəkilçi", _şəkilçi, 2, 2),
        "böyüyə": D("böyüyə", E.böyüyə, 1, 1),
        "kiçiyə": D("kiçiyə", E.kiçiyə, 1, 1),
        "müqayisə": D("müqayisə", E.müqayisə, 2, 2),
        "əlifba": E.KICIK,
    })

    # ── təsadüfi ────────────────────────────────────────────
    təsadüfi = Modul("təsadüfi", {
        "tam": D("tam", lambda a, b: _random.randint(a, b), 2, 2),
        "onluq": D("onluq", lambda a=0.0, b=1.0: _random.uniform(a, b),
                   0, 2),
        "məntiq": D("məntiq", lambda: _random.random() < 0.5),
        "seç": D("seç", lambda k: _random.choice(
            list(icraçı._iterasiya(k, None))), 1, 1),
        "seçN": D("seçN", lambda k, n: _random.sample(
            list(icraçı._iterasiya(k, None)), n), 2, 2),
        "qarışdır": D("qarışdır",
                      lambda s: (_random.shuffle(s), None)[1], 1, 1),
        "mətn": D("mətn", lambda n: "".join(
            _random.choice(E.KICIK) for _ in range(n)), 1, 1),
        "UUID": D("UUID", lambda: str(__import__("uuid").uuid4())),
        "toxum": D("toxum", lambda n: (_random.seed(n), None)[1], 1, 1),
    })

    # ── vaxt ────────────────────────────────────────────────
    AYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun",
             "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
    GÜNLƏR = ["bazar ertəsi", "çərşənbə axşamı", "çərşənbə",
              "cümə axşamı", "cümə", "şənbə", "bazar"]

    vaxt = Modul("vaxt", {
        "möhür": D("möhür", lambda: int(_time.time())),
        "möhürMs": D("möhürMs", lambda: int(_time.time() * 1000)),
        "indi": D("indi", lambda: _time.strftime("%Y-%m-%dT%H:%M:%S")),
        "bugün": D("bugün", lambda: _time.strftime("%Y-%m-%d")),
        "formatla": D("formatla", _vaxt_formatla, 1, 2),
        "azərbaycanca": D("azərbaycanca", lambda: _azərbaycanca_tarix(
            AYLAR, GÜNLƏR)),
        "ayAdı": D("ayAdı", lambda n: AYLAR[n - 1], 1, 1),
        "ayAdıBaş": D("ayAdıBaş", lambda n: E.baş_böyük(AYLAR[n - 1]), 1, 1),
        "günAdı": D("günAdı", lambda n: GÜNLƏR[n - 1], 1, 1),
        "ayAdları": D("ayAdları", lambda: list(AYLAR)),
        "günAdları": D("günAdları", lambda: list(GÜNLƏR)),
        "gözlə": D("gözlə", lambda ms: (_time.sleep(ms / 1000), None)[1],
                   1, 1),
        "gözləSaniyə": D("gözləSaniyə",
                         lambda s: (_time.sleep(s), None)[1], 1, 1),
        "ölç": D("ölç", lambda: _time.perf_counter()),
        "limitlə": D("limitlə", lambda ms, g: _vaxt_limitlə(
            icraçı, ms, g), 2, 2),
    })

    # ── fayl ────────────────────────────────────────────────
    def fayl_oxu(yol):
        try:
            return Path(yol).read_text(encoding="utf-8")
        except FileNotFoundError:
            raise _xəta("FaylTapılmadıXətası",
                        f'"{yol}" faylı tapılmadı', "ALQ-R009")
        except PermissionError:
            raise _xəta("İcazəXətası",
                        f'"{yol}" faylını oxumaq icazəsi yoxdur',
                        "ALQ-R012")
        except UnicodeDecodeError:
            raise _xəta("KodlaşdırmaXətası",
                        f'"{yol}" faylı UTF-8 deyil', "ALQ-L001")

    def fayl_yaz(yol, məzmun):
        try:
            Path(yol).write_text(mətnə(məzmun, icraçı), encoding="utf-8",
                                 newline="\n")
        except PermissionError:
            raise _xəta("İcazəXətası",
                        f'"{yol}" faylına yazmaq icazəsi yoxdur',
                        "ALQ-R012")
        return None

    def fayl_əlavə(yol, məzmun):
        with open(yol, "a", encoding="utf-8", newline="\n") as f:
            f.write(mətnə(məzmun, icraçı))
        return None

    fayl = Modul("fayl", {
        "oxu": D("oxu", fayl_oxu, 1, 1),
        "yaz": D("yaz", fayl_yaz, 2, 2),
        "əlavəEt": D("əlavəEt", fayl_əlavə, 2, 2),
        "oxuSətirlər": D("oxuSətirlər",
                         lambda y: fayl_oxu(y).split("\n"), 1, 1),
        "oxuBayt": D("oxuBayt", lambda y: Path(y).read_bytes(), 1, 1),
        "yazBayt": D("yazBayt",
                     lambda y, b: (Path(y).write_bytes(bytes(b)), None)[1],
                     2, 2),
        "vardır": D("vardır", lambda y: Path(y).is_file(), 1, 1),
        "sil": D("sil", lambda y: (Path(y).unlink(missing_ok=True),
                                   None)[1], 1, 1),
        "kopyala": D("kopyala", lambda a, b: (
            __import__("shutil").copy2(a, b), None)[1], 2, 2),
        "köçür": D("köçür", lambda a, b: (
            __import__("shutil").move(a, b), None)[1], 2, 2),
        "adDəyiş": D("adDəyiş", lambda a, b: (Path(a).rename(b), None)[1],
                     2, 2),
        "ölçü": D("ölçü", lambda y: Path(y).stat().st_size, 1, 1),
        "MIMETipi": D("MIMETipi", lambda y: __import__(
            "mimetypes").guess_type(y)[0] or "application/octet-stream",
                      1, 1),
    })

    qovluq = Modul("qovluq", {
        "yarat": D("yarat", lambda y: (Path(y).mkdir(exist_ok=True),
                                       None)[1], 1, 1),
        "yaratDərin": D("yaratDərin", lambda y: (
            Path(y).mkdir(parents=True, exist_ok=True), None)[1], 1, 1),
        "sil": D("sil", lambda y: (Path(y).rmdir(), None)[1], 1, 1),
        "silDərin": D("silDərin", lambda y: (
            __import__("shutil").rmtree(y, ignore_errors=True), None)[1],
                      1, 1),
        "vardır": D("vardır", lambda y: Path(y).is_dir(), 1, 1),
        "siyahı": D("siyahı", lambda y=".": sorted(
            p.name for p in Path(y).iterdir()), 0, 1),
        "axtar": D("axtar", lambda y, n: sorted(
            str(p) for p in Path(y).rglob(n)), 2, 2),
        "cari": D("cari", lambda: os.getcwd()),
        "dəyiş": D("dəyiş", lambda y: (os.chdir(y), None)[1], 1, 1),
        "ev": D("ev", lambda: str(Path.home())),
        "müvəqqəti": D("müvəqqəti",
                       lambda: __import__("tempfile").gettempdir()),
    })

    yol_modulu = Modul("yol", {
        "birləşdir": D("birləşdir",
                       lambda *p: str(Path(*p)).replace("\\", "/"), 1),
        "mütləq": D("mütləq", lambda p: str(Path(p).resolve()), 1, 1),
        "qovluq": D("qovluq", lambda p: str(Path(p).parent), 1, 1),
        "fayl": D("fayl", lambda p: Path(p).name, 1, 1),
        "ad": D("ad", lambda p: Path(p).stem, 1, 1),
        "uzantı": D("uzantı", lambda p: Path(p).suffix, 1, 1),
        "normalizə": D("normalizə",
                       lambda p: os.path.normpath(p).replace("\\", "/"),
                       1, 1),
        "nisbi": D("nisbi", lambda a, b: os.path.relpath(b, a).replace(
            "\\", "/"), 2, 2),
        "ayırıcı": "/",
    })

    # ── json ────────────────────────────────────────────────
    def json_oxu(m_):
        try:
            return _json.loads(m_)
        except _json.JSONDecodeError as x:
            raise _xəta("JSONXətası",
                        f"JSON formatı pozulub (sətir {x.lineno}): {x.msg}",
                        "ALQ-R005")

    def json_yaz(x, gözəl=False):
        return _json.dumps(_json_hazırla(x, icraçı), ensure_ascii=False,
                           indent=2 if gözəl else None)

    json_modulu = Modul("json", {
        "oxu": D("oxu", json_oxu, 1, 1),
        "yaz": D("yaz", lambda x: json_yaz(x), 1, 1),
        "yazGözəl": D("yazGözəl", lambda x: json_yaz(x, True), 1, 1),
        "faylOxu": D("faylOxu", lambda y: json_oxu(fayl_oxu(y)), 1, 1),
        "faylYaz": D("faylYaz",
                     lambda y, x: fayl_yaz(y, json_yaz(x, True)), 2, 2),
    })

    # ── naxış (requlyar ifadələr) ───────────────────────────
    def naxış_qur(n, bayraqlar=""):
        f = 0
        if "i" in bayraqlar:
            f |= _re.IGNORECASE
        if "m" in bayraqlar:
            f |= _re.MULTILINE
        if "s" in bayraqlar:
            f |= _re.DOTALL
        if "x" in bayraqlar:
            f |= _re.VERBOSE
        return _Naxış(_re.compile(n, f))

    naxış = Modul("naxış", {
        "qur": D("qur", naxış_qur, 1, 2),
        "uyğundur": D("uyğundur",
                      lambda n, s: _re.search(n, s) is not None, 2, 2),
        "tap": D("tap", lambda n, s: (
            _re.search(n, s).group(0) if _re.search(n, s) else None), 2, 2),
        "hamısınıTap": D("hamısınıTap",
                         lambda n, s: _re.findall(n, s), 2, 2),
        "əvəz": D("əvəz", lambda n, s, y: _re.sub(n, y, s), 3, 3),
        "böl": D("böl", lambda n, s: _re.split(n, s), 2, 2),
    })

    # ── sistem ──────────────────────────────────────────────
    sistem = Modul("sistem", {
        "arqumentlər": D("arqumentlər", lambda: list(sys.argv[1:])),
        "mühit": D("mühit", lambda a, s=None: os.environ.get(a, s), 1, 2),
        "mühitQoy": D("mühitQoy",
                      lambda a, d: (os.environ.__setitem__(a, d), None)[1],
                      2, 2),
        "platforma": D("platforma", lambda: _platforma()),
        "memarlıq": D("memarlıq",
                      lambda: __import__("platform").machine().lower()),
        "nüvəSayı": D("nüvəSayı", lambda: os.cpu_count() or 1),
        "istifadəçi": D("istifadəçi",
                        lambda: os.environ.get("USERNAME")
                        or os.environ.get("USER") or ""),
        "hostAdı": D("hostAdı",
                     lambda: __import__("socket").gethostname()),
        "dayan": D("dayan", lambda k=0: (_ for _ in ()).throw(
            DayanmaSiqnalı(k)), 0, 1),
    })

    # ── konsol ──────────────────────────────────────────────
    def _rəng(mətn_, kod):
        return f"\033[{kod}m{mətn_}\033[0m"

    konsol = Modul("konsol", {
        "qırmızı": D("qırmızı", lambda s: _rəng(s, "31"), 1, 1),
        "yaşıl": D("yaşıl", lambda s: _rəng(s, "32"), 1, 1),
        "sarı": D("sarı", lambda s: _rəng(s, "33"), 1, 1),
        "mavi": D("mavi", lambda s: _rəng(s, "34"), 1, 1),
        "qalın": D("qalın", lambda s: _rəng(s, "1"), 1, 1),
        "altXətt": D("altXətt", lambda s: _rəng(s, "4"), 1, 1),
        "təmizlə": D("təmizlə",
                     lambda: (sys.stdout.write("\033[2J\033[H"), None)[1]),
        "cədvəl": D("cədvəl",
                    lambda b, s: (_cədvəl(icraçı, b, s), None)[1], 2, 2),
        "soruş": D("soruş", lambda s="": input(s), 0, 1),
        "təsdiqlə": D("təsdiqlə", lambda s: E.kiçiyə(
            input(s + " (hə/yox) ").strip()) in ("hə", "he", "bəli", "h"),
                      1, 1),
    })

    # ── jurnal ──────────────────────────────────────────────
    jurnal = Modul("jurnal", {
        "debaq": D("debaq", lambda *a: _jurnal(icraçı, "DEBAQ", a), 1),
        "info": D("info", lambda *a: _jurnal(icraçı, "İNFO", a), 1),
        "xəbərdarlıq": D("xəbərdarlıq",
                         lambda *a: _jurnal(icraçı, "XƏBƏRDARLIQ", a), 1),
        "xəta": D("xəta", lambda *a, **k: _jurnal(icraçı, "XƏTA", a), 1),
        "kritik": D("kritik", lambda *a: _jurnal(icraçı, "KRİTİK", a), 1),
    })

    # ── test ────────────────────────────────────────────────
    def t_bərabər(a, b, mesaj=""):
        if not icraçı._bərabərdir(a, b):
            raise _xəta("İddiaXətası",
                        mesaj or f"gözlənilən {mətnə(b, icraçı)}, "
                                f"alınan {mətnə(a, icraçı)}", "ALQ-R007")
        return None

    test = Modul("test", {
        "bərabər": D("bərabər", t_bərabər, 2, 3),
        "bərabərDeyil": D("bərabərDeyil", lambda a, b, m="": (
            None if not icraçı._bərabərdir(a, b)
            else (_ for _ in ()).throw(_xəta("İddiaXətası",
                                             m or "dəyərlər bərabərdir",
                                             "ALQ-R007"))), 2, 3),
        "doğru": D("doğru", lambda ş, m="": (
            None if ş is True
            else (_ for _ in ()).throw(_xəta("İddiaXətası",
                                             m or "doğru gözlənilirdi",
                                             "ALQ-R007"))), 1, 2),
        "yanlış": D("yanlış", lambda ş, m="": (
            None if ş is False
            else (_ for _ in ()).throw(_xəta("İddiaXətası",
                                             m or "yanlış gözlənilirdi",
                                             "ALQ-R007"))), 1, 2),
        "təxminən": D("təxminən", lambda a, b, dəqiqlik=1e-9: (
            None if abs(a - b) <= dəqiqlik
            else (_ for _ in ()).throw(_xəta("İddiaXətası",
                                             f"{a} ≉ {b}", "ALQ-R007"))),
                      2, 3),
    })

    # ── paralel ─────────────────────────────────────────────
    def _gələcəklər(k) -> list:
        return [x for x in icraçı._iterasiya(k, None)]

    def p_hamısı(k):
        """Hamısını paralel işlədir, nəticələri sıra ilə qaytarır."""
        siyahı = _gələcəklər(k)
        for g in siyahı:
            if isinstance(g, Gələcək):
                g.başlat()
        return [icraçı.gözlə(g) for g in siyahı]

    def p_hamısı_nəticə(k):
        """Xətalara dözümlü: hər element üçün (uğurlu, dəyər|mesaj)."""
        siyahı = _gələcəklər(k)
        for g in siyahı:
            if isinstance(g, Gələcək):
                g.başlat()
        nəticə = []
        for g in siyahı:
            try:
                nəticə.append((True, icraçı.gözlə(g)))
            except AlqorXəta as x:
                nəticə.append((False, x.mesaj))
        return nəticə

    def p_ilk_bitən(k):
        import time as _t
        siyahı = [g for g in _gələcəklər(k)]
        for g in siyahı:
            if isinstance(g, Gələcək):
                g.başlat()
        while True:
            for g in siyahı:
                if not isinstance(g, Gələcək):
                    return g
                if g.bitdimi:
                    return icraçı.gözlə(g)
            _t.sleep(0.001)

    def p_ilk_uğurlu(k):
        import time as _t
        siyahı = [g for g in _gələcəklər(k)]
        for g in siyahı:
            if isinstance(g, Gələcək):
                g.başlat()
        qalan = list(siyahı)
        son_xəta = None
        while qalan:
            for g in list(qalan):
                if not isinstance(g, Gələcək):
                    return g
                if not g.bitdimi:
                    continue
                qalan.remove(g)
                if g.uğurludurmu:
                    return icraçı.gözlə(g)
                son_xəta = g.xəta_al()
            _t.sleep(0.001)
        if son_xəta is not None:
            raise son_xəta
        raise _xəta("Xəta", "heç bir əməliyyat uğurlu olmadı", "ALQ-R021")

    def p_məhdud(n, k):
        """Eyni anda ən çox `n` əməliyyat."""
        siyahı = _gələcəklər(k)
        nəticə = []
        for i in range(0, len(siyahı), max(1, n)):
            dəstə = siyahı[i:i + max(1, n)]
            for g in dəstə:
                if isinstance(g, Gələcək):
                    g.başlat()
            nəticə.extend(icraçı.gözlə(g) for g in dəstə)
        return nəticə

    def p_çevir(k, f):
        gələcəklər = [_çağır(icraçı, f, x)
                      for x in icraçı._iterasiya(k, None)]
        return p_hamısı(gələcəklər)

    def p_çağır(*a):
        """`gözlə paralel(f1(), f2())` — kortej qaytarır."""
        return tuple(p_hamısı(list(a)))

    paralel = Modul("paralel", {
        "hamısı": D("hamısı", p_hamısı, 1, 1),
        "hamısıNəticə": D("hamısıNəticə", p_hamısı_nəticə, 1, 1),
        "ilkBitən": D("ilkBitən", p_ilk_bitən, 1, 1),
        "ilkUğurlu": D("ilkUğurlu", p_ilk_uğurlu, 1, 1),
        "məhdud": D("məhdud", p_məhdud, 2, 2),
        "çevir": D("çevir", p_çevir, 2, 2),
    }, çağırışçı=D("paralel", p_çağır, 1))

    # ── sap (həqiqi paralellik) ─────────────────────────────
    def s_başlat(f, *a):
        return Gələcək(lambda: _çağır(icraçı, f, *a), "sap").başlat()

    def s_hovuz_xəritələ(f, k, ölçü=4):
        gələcəklər = [Gələcək(lambda x=x: _çağır(icraçı, f, x), "sap")
                      for x in icraçı._iterasiya(k, None)]
        return p_məhdud(ölçü, gələcəklər)

    sap = Modul("sap", {
        "başlat": D("başlat", s_başlat, 1),
        "xəritələ": D("xəritələ", s_hovuz_xəritələ, 2, 3),
        "nüvəSayı": D("nüvəSayı", lambda: os.cpu_count() or 1),
        "gözlə": D("gözlə", lambda ms: (_time.sleep(ms / 1000), None)[1],
                   1, 1),
    })

    return {
        "paralel": paralel, "sap": sap,
        "riyaziyyat": riyaziyyat, "mətn": mətn_modulu,
        "təsadüfi": təsadüfi, "vaxt": vaxt, "fayl": fayl,
        "qovluq": qovluq, "yol": yol_modulu, "json": json_modulu,
        "naxış": naxış, "sistem": sistem, "konsol": konsol,
        "jurnal": jurnal, "test": test,
    }


# ── Modul köməkçiləri ──────────────────────────────────────────────────

class _Naxış:
    def __init__(self, derlənmiş):
        self.r = derlənmiş


def _vaxt_limitlə(icraçı, ms, gələcək):
    """`gözlə vaxt.limitlə(5000, uzunƏməliyyat())`"""
    if not isinstance(gələcək, Gələcək):
        return gələcək
    gələcək.başlat()
    try:
        return gələcək.al(ms / 1000)
    except TimeoutError:
        raise _xəta("VaxtBitdiXətası",
                    f"əməliyyat {ms} ms limitini aşdı", "ALQ-R011")


def _platforma() -> str:
    p = sys.platform
    if p.startswith("linux"):
        return "linux"
    if p == "darwin":
        return "macos"
    if p.startswith("win"):
        return "windows"
    return p


def _sadədir(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def _sadə_bölənlər(n: int) -> list[int]:
    nəticə: list[int] = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            nəticə.append(d)
            n //= d
        d += 1
    if n > 1:
        nəticə.append(n)
    return nəticə


def _median(k) -> float:
    s = sorted(k)
    n = len(s)
    if n == 0:
        raise _xəta("BoşKolleksiyaXətası", "boş kolleksiyanın medianı yoxdur",
                    "ALQ-R014")
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _moda(k):
    from collections import Counter
    if not k:
        raise _xəta("BoşKolleksiyaXətası", "boş kolleksiyanın modası yoxdur",
                    "ALQ-R014")
    return Counter(k).most_common(1)[0][0]


def _dispersiya(k) -> float:
    if not k:
        return 0.0
    o = sum(k) / len(k)
    return sum((x - o) ** 2 for x in k) / len(k)


def _yerli_ədəd(n, rəqəm=None) -> str:
    """Azərbaycan formatı: minlik ayırıcı boşluq, onluq ayırıcı vergül."""
    if rəqəm is None:
        rəqəm = 0 if float(n) == int(n) else 2
    s = f"{float(n):,.{rəqəm}f}"
    tam, _, kəsr = s.partition(".")
    tam = tam.replace(",", " ")
    return f"{tam},{kəsr}" if kəsr else tam


def _şəkilçi(söz: str, şəkilçi: str) -> str:
    """Ahəng qanununa uyğun şəkilçi birləşdirmə (sadələşdirilmiş)."""
    saitlər = [c for c in E.kiçiyə(söz) if E.saitdir(c)]
    qalın = bool(saitlər) and E.qalın_saitdir(saitlər[-1])
    cədvəl = {
        "lar": "lar" if qalın else "lər",
        "lər": "lar" if qalın else "lər",
        "da": "da" if qalın else "də",
        "dan": "dan" if qalın else "dən",
        "a": "a" if qalın else "ə",
    }
    return söz + cədvəl.get(şəkilçi, şəkilçi)


def _vaxt_formatla(format: str, möhür=None) -> str:
    t = _time.localtime(möhür) if möhür else _time.localtime()
    çevirmə = [("YYYY", "%Y"), ("MM", "%m"), ("DD", "%d"),
               ("HH", "%H"), ("mm", "%M"), ("ss", "%S")]
    f = format
    for a, b in çevirmə:
        f = f.replace(a, b)
    return _time.strftime(f, t)


def _azərbaycanca_tarix(aylar, günlər) -> str:
    t = _time.localtime()
    return (f"{t.tm_mday} {aylar[t.tm_mon - 1]} {t.tm_year}, "
            f"{günlər[t.tm_wday]}")


def _json_hazırla(x: Any, icraçı) -> Any:
    if isinstance(x, Nümunə):
        return {a: _json_hazırla(d, icraçı) for a, d in x.sahələr.items()}
    if isinstance(x, SadalamaDəyəri):
        return x.ad
    if isinstance(x, dict):
        return {str(a): _json_hazırla(d, icraçı) for a, d in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_hazırla(e, icraçı) for e in x]
    if isinstance(x, set):
        return [_json_hazırla(e, icraçı) for e in x]
    if isinstance(x, AlqorDiapazon):
        return list(x)
    if isinstance(x, bytes):
        return base64.b64encode(x).decode("ascii")
    return x


def _cədvəl(icraçı, başlıqlar, sətirlər) -> None:
    hamısı = [[mətnə(h, icraçı) for h in başlıqlar]] + [
        [mətnə(c, icraçı) for c in s] for s in sətirlər]
    enlər = [max(len(s[i]) for s in hamısı) for i in range(len(hamısı[0]))]
    ayırıcı = "─┼─".join("─" * e for e in enlər)
    for j, s in enumerate(hamısı):
        icraçı.çıxış(" │ ".join(h.ljust(e) for h, e in zip(s, enlər)))
        if j == 0:
            icraçı.çıxış(ayırıcı)


def _jurnal(icraçı, səviyyə: str, arqumentlər) -> None:
    vaxt_ = _time.strftime("%H:%M:%S")
    mesaj = " ".join(mətnə(a, icraçı) for a in arqumentlər)
    print(f"[{vaxt_}] {səviyyə}: {mesaj}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════
#  Modul yükləmə
# ═══════════════════════════════════════════════════════════════════════

_KEŞ: dict[str, Modul] = {}


def modul_yüklə(icraçı, ad: str, yer=None) -> Modul:
    """`gətir X` — standart modul və ya yerli fayl."""
    if ad in _KEŞ:
        return _KEŞ[ad]

    # Standart kitabxana
    if icraçı.qlobal.var(ad):
        dəyər = icraçı.qlobal.al(ad)
        if isinstance(dəyər, Modul):
            return dəyər

    # Yerli fayl
    if ad.endswith((".alqor", ".alq")) or ad.startswith((".", "/")):
        return _fayldan_modul(icraçı, ad, yer)

    raise AlqorXəta("ArqumentXətası",
                    f"`{ad}` modulu tapılmadı", yer, "ALQ-M001")


def _fayldan_modul(icraçı, yol: str, yer=None) -> Modul:
    from .lekser import Lekser
    from .menbe import Mənbə
    from .parser import Parser
    from .xeta import XətaToplayıcı

    p = Path(yol)
    if not p.exists():
        for uzantı in (".alqor", ".alq"):
            if Path(yol + uzantı).exists():
                p = Path(yol + uzantı)
                break
    if not p.exists():
        raise AlqorXəta("ArqumentXətası",
                        f'"{yol}" modul faylı tapılmadı', yer, "ALQ-M001")

    x = XətaToplayıcı()
    s = Mənbə.fayldan(p, x)
    if s is None:
        raise AlqorXəta("ArqumentXətası",
                        f'"{yol}" oxunmadı', yer, "ALQ-M001")
    tokenlər = Lekser(s, x).leksə()
    ağac = Parser(tokenlər, s, x).ayır()
    if not x.uğurludur():
        raise AlqorXəta("ArqumentXətası",
                        f'"{p.name}" modulunda {len(x.xətalar)} xəta var',
                        yer, "ALQ-M009")

    alt = icraçı.qlobal.alt()
    icraçı._elanları_qaldır(ağac.gövdə, alt)
    for c in ağac.gövdə:
        if not icraçı._elandır(c):
            icraçı._cümlə(c, alt)

    modul = Modul(p.stem, dict(alt.adlar))
    _KEŞ[yol] = modul
    return modul
