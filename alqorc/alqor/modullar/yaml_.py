"""
`yaml` — YAML oxuma və yazma (§ 10.17).

    gətir yaml

    dəyişən k = yaml.faylOxu("docker-compose.yml")
    yaz(k["services"]["veb"]["ports"])

    yaml.faylYaz("çıxış.yaml", {"ad": "Alqor", "dillər": ["az", "en"]})

Asılılıqsız ayırıcı. Konfiqurasiya fayllarında işlənən YAML 1.2:

  • blok lüğət və siyahılar, `- açar: dəyər` yığcam forması
  • axın kolleksiyaları `[a, b]`, `{a: 1}` (bir neçə sətirdə də)
  • tək / qoşa dırnaqlı mətnlər, `|` və `>` blok mətnləri (`-` `+`)
  • ankor `&ad`, alias `*ad`, birləşmə `<<: *ad`
  • `---` ilə bir neçə sənəd (`yaml.oxuHamısı`)
  • core sxem: `null` `~`, `true` `false`, tam, onluq, `.inf`, `.nan`

Dəstəklənməyən: mürəkkəb açarlar (`? `), xüsusi teqlər (`!Sinif`
— nəzərə alınmır), çox sətirli dırnaqsız açarlar.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı


class YAMLXətası(Exception):
    pass


def _xəta(mesaj: str) -> AlqorXəta:
    return AlqorXəta("YAMLXətası", mesaj, None, "ALQ-R005")


# ═══════════════════════════════════════════════════════════════════════
#  Skalyarlar
# ═══════════════════════════════════════════════════════════════════════

_TAM = re.compile(r"^[-+]?[0-9]+$")
_TAM16 = re.compile(r"^0x[0-9a-fA-F]+$")
_TAM8 = re.compile(r"^0o[0-7]+$")
_ONLUQ = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")


def _çöz(s: str) -> Any:
    """Dırnaqsız skalyarın dəyəri (YAML 1.2 core sxemi)."""
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if _TAM.match(s):
        return int(s)
    if _TAM16.match(s):
        return int(s, 16)
    if _TAM8.match(s):
        return int(s[2:], 8)
    if _ONLUQ.match(s):
        return float(s)
    if s in (".inf", ".Inf", ".INF", "+.inf", "+.Inf", "+.INF"):
        return math.inf
    if s in ("-.inf", "-.Inf", "-.INF"):
        return -math.inf
    if s in (".nan", ".NaN", ".NAN"):
        return math.nan
    return s


_QAÇIŞ = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t",
          "n": "\n", "v": "\v", "f": "\f", "r": "\r", "e": "\x1b",
          " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
          "_": "\xa0", "L": " ", "P": " "}


def _qoşa_dırnaq(s: str, sətir: int) -> str:
    n: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 1
            if i >= len(s):
                break
            q = s[i]
            if q in _QAÇIŞ:
                n.append(_QAÇIŞ[q])
            elif q in "xuU":
                uz = {"x": 2, "u": 4, "U": 8}[q]
                kod = s[i + 1:i + 1 + uz]
                try:
                    n.append(chr(int(kod, 16)))
                except ValueError:
                    raise YAMLXətası(f"sətir {sətir}: yanlış qaçış "
                                     f"`\\{q}{kod}`")
                i += uz
            elif q == "\n":
                pass                            # sətir sonu davamı
            else:
                raise YAMLXətası(f"sətir {sətir}: naməlum qaçış `\\{q}`")
        else:
            n.append(c)
        i += 1
    return "".join(n)


def _qatla(hissələr: list[str]) -> str:
    """Dırnaqlı mətnin sətirlərini birləşdirir: boş sətir → `\\n`."""
    n = ""
    boş = 0
    for i, h in enumerate(hissələr):
        h = h.strip() if 0 < i < len(hissələr) - 1 else (
            h.rstrip() if i == 0 else h.lstrip())
        if i == 0:
            n = h
        elif h == "" and i < len(hissələr) - 1:
            boş += 1
        else:
            n += ("\n" * boş) if boş else " "
            n += h
            boş = 0
    return n


# ═══════════════════════════════════════════════════════════════════════
#  Ayırıcı
# ═══════════════════════════════════════════════════════════════════════

_BAŞLAYAN = " \t[{,:-"        # bu simvoldan sonra dırnaq mətn başladır


def _şərhi_at(s: str) -> str:
    """`#` şərhini atır (dırnaqlı mətndəki `#`-a toxunmur)."""
    dırnaq = None
    for i, c in enumerate(s):
        if dırnaq:
            if dırnaq == '"' and c == "\\":
                continue
            if c == dırnaq:
                if dırnaq == "'" and s[i + 1:i + 2] == "'":
                    continue
                dırnaq = None
        elif c in "\"'" and (i == 0 or s[i - 1] in _BAŞLAYAN):
            dırnaq = c
        elif c == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _açarı_ayır(s: str) -> tuple[str, str] | None:
    """`açar: dəyər` → (açar, dəyər); lüğət sətri deyilsə None."""
    if s.startswith(("[", "{")):
        return None
    if s[:1] in "\"'":
        q = s[0]
        i = 1
        while i < len(s):
            if s[i] == "\\" and q == '"':
                i += 2
                continue
            if s[i] == q:
                if q == "'" and s[i + 1:i + 2] == "'":
                    i += 2
                    continue
                break
            i += 1
        qalan = s[i + 1:].lstrip()
        if qalan.startswith(":") and (len(qalan) == 1
                                      or qalan[1] in " \t"):
            return s[:i + 1], qalan[1:].strip()
        return None
    for m in re.finditer(r":(\s|$)", s):
        return s[:m.start()].rstrip(), s[m.end():].strip()
    return None


class _Oxuyucu:
    def __init__(self, mətn: str):
        mətn = mətn.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
        if "\t" in "".join(re.findall(r"^[ \t]*", mətn, re.M)):
            for n, s in enumerate(mətn.split("\n"), 1):
                if re.match(r"^ *\t", s):
                    raise YAMLXətası(f"sətir {n}: girintidə TAB işlədilə "
                                     "bilməz — boşluq yazın")
        self.s = mətn.split("\n")
        self.i = 0
        self.ankorlar: dict[str, Any] = {}

    # ── Sətirlər ──────────────────────────────────────────────────────

    def _məzmun(self, j: int) -> tuple[int, str] | None:
        """(girinti, şərhsiz məzmun); boş/şərh sətri üçün None."""
        xam = self.s[j]
        c = _şərhi_at(xam)
        if not c.strip():
            return None
        return len(c) - len(c.lstrip(" ")), c.strip()

    def _növbəti(self) -> int | None:
        while self.i < len(self.s):
            if self._sənəd_sərhədi(self.i):
                return None
            if self._məzmun(self.i) is not None:
                return self.i
            self.i += 1
        return None

    def _sənəd_sərhədi(self, j: int) -> bool:
        x = self.s[j]
        return x.startswith(("---", "...")) and (
            len(x) == 3 or x[3] in " \t")

    # ── Sənədlər ──────────────────────────────────────────────────────

    def sənədlər(self) -> list[Any]:
        n: list[Any] = []
        başladı = False
        while self.i < len(self.s):
            x = self.s[self.i]
            if x.startswith("%"):
                self.i += 1
                continue
            if self._sənəd_sərhədi(self.i):
                if x.startswith("---"):
                    qalan = _şərhi_at(x[3:]).strip()
                    self.i += 1
                    if qalan:
                        n.append(self._sətirdaxili(qalan, self.i - 1, -1))
                        başladı = False
                        continue
                    n.append(self._düyün(-1))
                    başladı = False
                else:
                    self.i += 1
                continue
            if self._məzmun(self.i) is None:
                self.i += 1
                continue
            if başladı:
                raise YAMLXətası(f"sətir {self.i + 1}: gözlənilməz məzmun")
            n.append(self._düyün(-1))
            başladı = True
        return n or [None]

    # ── Bloklar ───────────────────────────────────────────────────────

    def _düyün(self, valideyn: int) -> Any:
        j = self._növbəti()
        if j is None:
            return None
        ind, c = self._məzmun(j)
        if ind <= valideyn:
            return None
        ankor, tag, c = self._xassələr(c)
        if ankor is not None or tag is not None:
            if not c:                       # `&a` öz sətrində, dəyər aşağıda
                self.s[j] = ""
                d = self._düyün(valideyn)
                return self._qeyd(ankor, self._teq(tag, d, j))
            self.s[j] = " " * ind + c
        if c == "-" or c.startswith(("- ", "-\t")):
            d = self._siyahı(ind)
        elif _açarı_ayır(c) is not None:
            d = self._lüğət(ind)
        else:
            self.i = j + 1
            d = self._sətirdaxili(c, j, valideyn)
        return self._qeyd(ankor, self._teq(tag, d, j))

    def _qeyd(self, ankor: str | None, d: Any) -> Any:
        if ankor is not None:
            self.ankorlar[ankor] = d
        return d

    @staticmethod
    def _xassələr(c: str) -> tuple[str | None, str | None, str]:
        ankor = tag = None
        while c[:1] in ("&", "!"):
            m = re.match(r"^([&!][^\s]*)\s*", c)
            söz = m.group(1)
            if söz[0] == "&":
                ankor = söz[1:]
            else:
                tag = söz
            c = c[m.end():]
        return ankor, tag, c

    @staticmethod
    def _teq(tag: str | None, d: Any, j: int) -> Any:
        if tag in (None, "!", "!!map", "!!seq"):
            return d
        if tag == "!!str":
            return "" if d is None else (
                d if isinstance(d, str) else _skalyar_mətni(d))
        if tag == "!!int":
            try:
                return int(d)
            except (TypeError, ValueError):
                raise YAMLXətası(f"sətir {j + 1}: `!!int` tam deyil")
        if tag == "!!float":
            try:
                return float(d)
            except (TypeError, ValueError):
                raise YAMLXətası(f"sətir {j + 1}: `!!float` ədəd deyil")
        if tag == "!!bool":
            return bool(d)
        if tag == "!!null":
            return None
        return d                                  # xüsusi teqlər

    def _lüğət(self, ind: int) -> dict:
        n: dict[Any, Any] = {}
        birləşmələr: list[dict] = []
        while True:
            j = self._növbəti()
            if j is None:
                break
            sind, c = self._məzmun(j)
            if sind < ind:
                break
            if sind > ind:
                raise YAMLXətası(f"sətir {j + 1}: gözlənilməz girinti")
            if c == "-" or c.startswith("- "):
                break
            ayrılmış = _açarı_ayır(c)
            if ayrılmış is None:
                raise YAMLXətası(f"sətir {j + 1}: `açar: dəyər` gözlənilirdi")
            açar_m, qalan = ayrılmış
            açar = self._açar(açar_m, j)
            self.i = j + 1
            d = self._dəyər(qalan, ind, j)
            if açar == "<<":
                for x in (d if isinstance(d, list) else [d]):
                    if not isinstance(x, dict):
                        raise YAMLXətası(f"sətir {j + 1}: `<<` lüğət "
                                         "gözləyir")
                    birləşmələr.append(x)
                continue
            if açar in n:
                raise YAMLXətası(f"sətir {j + 1}: `{açar}` açarı təkrarlanır")
            n[açar] = d
        for x in birləşmələr:
            for a, d in x.items():
                n.setdefault(a, d)
        return n

    def _açar(self, m: str, j: int) -> Any:
        if m[:1] == '"':
            return _qoşa_dırnaq(m[1:-1], j + 1)
        if m[:1] == "'":
            return m[1:-1].replace("''", "'")
        d = _çöz(m)
        # Lüğət açarları mətn olsun (`1: a` → "1") — JSON/TOML ilə uyğun
        return d if isinstance(d, str) else (
            m if d is not None else "")

    def _dəyər(self, qalan: str, ind: int, j: int) -> Any:
        """`açar:` və ya `-` sonrakı dəyər."""
        ankor, tag, qalan = self._xassələr(qalan)
        if not qalan:
            k = self._növbəti()
            if k is None:
                d = None
            else:
                kind, kc = self._məzmun(k)
                if kind > ind:
                    d = self._düyün(ind)
                elif kind == ind and (kc == "-" or kc.startswith("- ")):
                    d = self._siyahı(ind)
                else:
                    d = None
        else:
            d = self._sətirdaxili(qalan, j, ind)
        return self._qeyd(ankor, self._teq(tag, d, j))

    def _siyahı(self, ind: int) -> list:
        n: list[Any] = []
        while True:
            j = self._növbəti()
            if j is None:
                break
            sind, c = self._məzmun(j)
            if sind != ind or not (c == "-" or c.startswith(("- ", "-\t"))):
                if sind > ind:
                    raise YAMLXətası(f"sətir {j + 1}: gözlənilməz girinti")
                break
            qalan = c[1:].lstrip()
            if not qalan:
                self.i = j + 1
                n.append(self._dəyər_siyahı(ind, j))
                continue
            sürüşmə = len(c) - len(qalan)
            ankor, tag, iç = self._xassələr(qalan)
            yığcam = iç == "-" or iç.startswith("- ") or (
                _açarı_ayır(iç) is not None and iç[:1] not in "[{")
            if yığcam:
                # `- açar: d` / `- - a` → sətri girintili məzmuna çeviririk
                yeni_ind = ind + sürüşmə + (len(qalan) - len(iç))
                self.s[j] = " " * yeni_ind + iç
                d = (self._siyahı(yeni_ind) if iç.startswith("-")
                     else self._lüğət(yeni_ind))
                n.append(self._qeyd(ankor, self._teq(tag, d, j)))
            else:
                self.i = j + 1
                n.append(self._dəyər(qalan, ind, j))
        return n

    def _dəyər_siyahı(self, ind: int, j: int) -> Any:
        k = self._növbəti()
        if k is None:
            return None
        kind, _ = self._məzmun(k)
        return self._düyün(ind) if kind > ind else None

    # ── Sətirdaxili dəyərlər ──────────────────────────────────────────

    def _sətirdaxili(self, c: str, j: int, ind: int) -> Any:
        if c.startswith("*"):
            ad = c[1:].strip()
            if ad not in self.ankorlar:
                raise YAMLXətası(f"sətir {j + 1}: `*{ad}` ankoru tapılmadı")
            return self.ankorlar[ad]
        if c[:1] in "|>":
            return self._blok_mətni(c, j, ind)
        if c[:1] in "[{":
            mətn = c
            k = j + 1
            while not _balanslıdır(mətn):
                if k >= len(self.s):
                    raise YAMLXətası(f"sətir {j + 1}: `{c[0]}` bağlanmayıb")
                mətn += " " + _şərhi_at(self.s[k]).strip()
                k += 1
            self.i = max(self.i, k)
            d, son = _Axın(mətn, j + 1, self.ankorlar).dəyər(0)
            if mətn[son:].strip():
                raise YAMLXətası(f"sətir {j + 1}: axın kolleksiyasından "
                                 f"sonra artıq mətn: {mətn[son:].strip()!r}")
            return d
        if c[:1] in "\"'":
            return self._dırnaqlı(c, j)
        # Dırnaqsız — sonrakı daha girintili sətirlər davamdır
        hissələr = [c]
        k = self.i
        while k < len(self.s):
            if self._sənəd_sərhədi(k):
                break
            m = self._məzmun(k)
            if m is None:
                hissələr.append("")
                k += 1
                continue
            if m[0] <= ind or _açarı_ayır(m[1]) is not None \
                    or m[1].startswith("- "):
                break
            hissələr.append(m[1])
            k += 1
        while hissələr and hissələr[-1] == "":
            hissələr.pop()
        if len(hissələr) > 1:
            self.i = k
            return _qatla(hissələr)
        return _çöz(c)

    def _dırnaqlı(self, c: str, j: int) -> str:
        q = c[0]
        # Bağlanmayan dırnaqda şərh ola bilməz — `c` sətrin sonudur
        qalan = c[1:]
        hissələr: list[str] = []
        k = j
        while True:
            son = _dırnaq_sonu(qalan, q)
            if son is not None:
                hissələr.append(qalan[:son])
                artıq = _şərhi_at(qalan[son + 1:]).strip()
                if artıq:
                    raise YAMLXətası(f"sətir {k + 1}: dırnaqdan sonra "
                                     f"artıq mətn: {artıq!r}")
                break
            hissələr.append(qalan)
            k += 1
            if k >= len(self.s):
                raise YAMLXətası(f"sətir {j + 1}: `{q}` bağlanmayıb")
            qalan = self.s[k]
        self.i = max(self.i, k + 1)
        if q == "'":
            return _qatla(hissələr).replace("''", "'")
        if len(hissələr) == 1:
            return _qoşa_dırnaq(hissələr[0], j + 1)
        # `\` ilə bitən sətir — boşluqsuz davam
        birləşmiş = []
        for i, h in enumerate(hissələr):
            if h.endswith("\\") and not h.endswith("\\\\") \
                    and i < len(hissələr) - 1:
                birləşmiş.append(h[:-1] + "\x00")
            else:
                birləşmiş.append(h)
        n = _qatla(birləşmiş).replace("\x00 ", "").replace("\x00", "")
        return _qoşa_dırnaq(n, j + 1)

    def _blok_mətni(self, c: str, j: int, ind: int) -> str:
        m = re.match(r"^([|>])([-+]?)([1-9]?)([-+]?)\s*$", c)
        if not m:
            raise YAMLXətası(f"sətir {j + 1}: blok mətn başlığı yanlışdır: "
                             f"{c!r}")
        növ = m.group(1)
        kəsmə = m.group(2) or m.group(4)
        açıq = int(m.group(3)) if m.group(3) else None
        k = j + 1
        sətirlər: list[str] = []
        məzmun_ind = (max(ind, 0) + açıq) if açıq else None
        while k < len(self.s):
            x = self.s[k]
            if self._sənəd_sərhədi(k):
                break
            if x.strip() == "":
                sətirlər.append("")
                k += 1
                continue
            girinti = len(x) - len(x.lstrip(" "))
            if məzmun_ind is None:
                if girinti <= ind:
                    break
                məzmun_ind = girinti
            if girinti < məzmun_ind:
                break
            sətirlər.append(x[məzmun_ind:])
            k += 1
        self.i = k
        son_boş = 0
        while sətirlər and sətirlər[-1] == "":
            sətirlər.pop()
            son_boş += 1
        if növ == "|":
            mətn = "\n".join(sətirlər)
        else:
            mətn = _qatlanmış(sətirlər)
        if not sətirlər:
            return "" if kəsmə != "+" else "\n" * son_boş
        if kəsmə == "-":
            return mətn
        if kəsmə == "+":
            return mətn + "\n" * (son_boş + 1)
        return mətn + "\n"


def _qatlanmış(sətirlər: list[str]) -> str:
    """`>` blok mətni: adi sətirlər boşluqla birləşir, boş sətirlər və
    daha girintili sətirlər sətir sonunu saxlayır."""
    n: list[str] = []
    gözləyən = 0
    əvvəlki_xüsusi = False
    ilk = True
    for x in sətirlər:
        if x == "":
            gözləyən += 1
            continue
        xüsusi = x[0] in " \t"
        if ilk:
            n.append("\n" * gözləyən + x)
            ilk = False
        elif gözləyən == 0:
            n.append(("\n" if xüsusi or əvvəlki_xüsusi else " ") + x)
        else:
            k = gözləyən + (1 if xüsusi or əvvəlki_xüsusi else 0)
            n.append("\n" * k + x)
        gözləyən = 0
        əvvəlki_xüsusi = xüsusi
    return "".join(n)


def _dırnaq_sonu(s: str, q: str) -> int | None:
    i = 0
    while i < len(s):
        if q == '"' and s[i] == "\\":
            i += 2
            continue
        if s[i] == q:
            if q == "'" and s[i + 1:i + 2] == "'":
                i += 2
                continue
            return i
        i += 1
    return None


def _balanslıdır(s: str) -> bool:
    d = 0
    dırnaq = None
    i = 0
    while i < len(s):
        c = s[i]
        if dırnaq:
            if dırnaq == '"' and c == "\\":
                i += 2
                continue
            if c == dırnaq:
                dırnaq = None
        elif c in "\"'":
            dırnaq = c
        elif c in "[{":
            d += 1
        elif c in "]}":
            d -= 1
        i += 1
    return d <= 0


class _Axın:
    """`[a, {b: 1}]` axın kolleksiyaları."""

    def __init__(self, s: str, sətir: int, ankorlar: dict):
        self.s = s
        self.sətir = sətir
        self.ankorlar = ankorlar

    def _boşluq(self, i: int) -> int:
        while i < len(self.s) and self.s[i] in " \t":
            i += 1
        return i

    def dəyər(self, i: int) -> tuple[Any, int]:
        i = self._boşluq(i)
        if i >= len(self.s):
            return None, i
        c = self.s[i]
        if c == "[":
            n = []
            i += 1
            while True:
                i = self._boşluq(i)
                if i < len(self.s) and self.s[i] == "]":
                    return n, i + 1
                d, i = self._element(i)
                n.append(d)
                i = self._boşluq(i)
                if i < len(self.s) and self.s[i] == ",":
                    i += 1
                    continue
                if i < len(self.s) and self.s[i] == "]":
                    return n, i + 1
                raise YAMLXətası(f"sətir {self.sətir}: `,` və ya `]` "
                                 "gözlənilirdi")
        if c == "{":
            n: dict = {}
            i += 1
            while True:
                i = self._boşluq(i)
                if i < len(self.s) and self.s[i] == "}":
                    return n, i + 1
                a, i = self._skalyar(i, açar=True)
                i = self._boşluq(i)
                if i < len(self.s) and self.s[i] == ":":
                    d, i = self.dəyər(i + 1)
                else:
                    d = None
                n[a if isinstance(a, str) else _skalyar_mətni(a)] = d
                i = self._boşluq(i)
                if i < len(self.s) and self.s[i] == ",":
                    i += 1
                    continue
                if i < len(self.s) and self.s[i] == "}":
                    return n, i + 1
                raise YAMLXətası(f"sətir {self.sətir}: `,` və ya `}}` "
                                 "gözlənilirdi")
        return self._skalyar(i)

    def _element(self, i: int) -> tuple[Any, int]:
        """Siyahı elementi — `[a: 1]` tək cütlü lüğətdir."""
        d, j = self.dəyər(i)
        k = self._boşluq(j)
        if k < len(self.s) and self.s[k] == ":" and not isinstance(
                d, (list, dict)):
            v, k = self.dəyər(k + 1)
            return {d if isinstance(d, str) else _skalyar_mətni(d): v}, k
        return d, j

    def _skalyar(self, i: int, açar: bool = False) -> tuple[Any, int]:
        c = self.s[i]
        if c in "\"'":
            son = _dırnaq_sonu(self.s[i + 1:], c)
            if son is None:
                raise YAMLXətası(f"sətir {self.sətir}: `{c}` bağlanmayıb")
            xam = self.s[i + 1:i + 1 + son]
            d = (_qoşa_dırnaq(xam, self.sətir) if c == '"'
                 else xam.replace("''", "'"))
            return d, i + son + 2
        if c == "*":
            m = re.match(r"\*([^\s,\]}]+)", self.s[i:])
            ad = m.group(1)
            if ad not in self.ankorlar:
                raise YAMLXətası(f"sətir {self.sətir}: `*{ad}` ankoru "
                                 "tapılmadı")
            return self.ankorlar[ad], i + m.end()
        j = i
        while j < len(self.s):
            x = self.s[j]
            if x in ",]}[{":
                break
            if x == ":" and (j + 1 >= len(self.s)
                             or self.s[j + 1] in " ,]}"):
                break
            j += 1
        mətn = self.s[i:j].strip()
        return (mətn if açar else _çöz(mətn)), j


# ═══════════════════════════════════════════════════════════════════════
#  Yazma
# ═══════════════════════════════════════════════════════════════════════

_XÜSUSİ_BAŞ = set("-?:,[]{}#&*!|>'\"%@`")


def _skalyar_mətni(d: Any) -> str:
    if d is None:
        return "null"
    if d is True:
        return "true"
    if d is False:
        return "false"
    if isinstance(d, float):
        if math.isnan(d):
            return ".nan"
        if math.isinf(d):
            return ".inf" if d > 0 else "-.inf"
        return repr(d)
    return str(d)


def _dırnaq_lazımdır(s: str) -> bool:
    if s == "" or s != s.strip():
        return True
    if not isinstance(_çöz(s), str):
        return True                    # "true", "42", "null" — mətn qalsın
    if s[0] in _XÜSUSİ_BAŞ:
        return True
    if ": " in s or " #" in s or s.endswith(":"):
        return True
    if any(ord(c) < 0x20 for c in s):
        return True
    return s in ("yes", "no", "on", "off", "Yes", "No", "On", "Off",
                 "y", "n", "Y", "N")      # YAML 1.1 oxuyucuları üçün


def _mətn_yaz(s: str) -> str:
    if not _dırnaq_lazımdır(s):
        return s
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
        elif ord(c) < 0x20:
            n.append(f"\\x{ord(c):02x}")
        else:
            n.append(c)
    n.append('"')
    return "".join(n)


def _sadə(d: Any) -> str:
    if isinstance(d, str):
        return _mətn_yaz(d)
    if isinstance(d, (bool, int, float)) or d is None:
        return _skalyar_mətni(d)
    raise _xəta(f"`{tip_adı(d)}` YAML-a yazıla bilmir")


def _hazırla(x: Any) -> Any:
    if isinstance(x, Nümunə):
        return {a: _hazırla(d) for a, d in x.sahələr.items()}
    if isinstance(x, dict):
        return {(a if isinstance(a, str) else _skalyar_mətni(a)): _hazırla(d)
                for a, d in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_hazırla(d) for d in x]
    return x


def _blok(d: Any, ind: int, s: list[str]) -> None:
    """Dəyəri `s` sətirlərinə əlavə edir (başlıq sətri artıq yazılıb)."""
    boşluq = " " * ind
    if isinstance(d, dict):
        for a, v in d.items():
            açar = _mətn_yaz(a)
            _cüt(f"{boşluq}{açar}:", v, ind, s)
    elif isinstance(d, list):
        for v in d:
            if isinstance(v, dict) and v:
                ilk = True
                for a, x in v.items():
                    ön = f"{boşluq}- " if ilk else f"{boşluq}  "
                    _cüt(f"{ön}{_mətn_yaz(a)}:", x, ind + 2, s)
                    ilk = False
            elif isinstance(v, list) and v:
                s.append(f"{boşluq}-")
                _blok(v, ind + 2, s)
            else:
                _cüt(f"{boşluq}-", v, ind, s, tire=True)


def _cüt(başlıq: str, v: Any, ind: int, s: list[str],
         tire: bool = False) -> None:
    if isinstance(v, dict):
        if not v:
            s.append(f"{başlıq} {{}}")
        else:
            s.append(başlıq)
            _blok(v, ind + 2, s)
    elif isinstance(v, list):
        if not v:
            s.append(f"{başlıq} []")
        else:
            s.append(başlıq)
            # Lüğət daxilindəki siyahı açarla eyni girintidə yazılır
            _blok(v, ind + 2 if tire else ind, s)
    elif isinstance(v, str) and "\n" in v.rstrip("\n") \
            and not any(ord(c) < 0x20 and c != "\n" for c in v) \
            and v == v.rstrip(" ") and not v.startswith(" "):
        kəsmə = "" if v.endswith("\n") and not v.endswith("\n\n") else (
            "-" if not v.endswith("\n") else "+")
        s.append(f"{başlıq} |{kəsmə}")
        for x in v.rstrip("\n").split("\n") if kəsmə != "+" else \
                v[:-1].split("\n"):
            s.append(f"{' ' * (ind + 2)}{x}" if x else "")
    else:
        s.append(f"{başlıq} {_sadə(v)}")


def yaz(d: Any) -> str:
    d = _hazırla(d)
    if isinstance(d, (dict, list)) and d:
        s: list[str] = []
        _blok(d, 0, s)
        return "\n".join(s) + "\n"
    if isinstance(d, dict):
        return "{}\n"
    if isinstance(d, list):
        return "[]\n"
    return _sadə(d) + "\n"


# ═══════════════════════════════════════════════════════════════════════

def oxu_hamısı(mətn: str) -> list:
    if not isinstance(mətn, str):
        raise AlqorXəta("TipXətası",
                        f"`yaml.oxu` mətn gözləyir, `{tip_adı(mətn)}` gəlib",
                        None, "ALQ-T001")
    try:
        return _Oxuyucu(mətn).sənədlər()
    except YAMLXətası as x:
        raise _xəta(f"YAML pozulub: {x}")
    except RecursionError:
        raise _xəta("YAML çox dərin iç-içədir")


def oxu(mətn: str) -> Any:
    sənədlər = oxu_hamısı(mətn)
    if len(sənədlər) > 1:
        raise _xəta(f"faylda {len(sənədlər)} sənəd var — "
                    "`yaml.oxuHamısı` işlədin")
    return sənədlər[0]


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
        "oxuHamısı": D("oxuHamısı", oxu_hamısı, 1, 1),
        "yaz": D("yaz", yaz, 1, 1),
        "faylOxu": D("faylOxu", lambda y: oxu(_fayl_oxu(y)), 1, 1),
        "faylYaz": D("faylYaz", lambda y, d: (Path(y).write_text(
            yaz(d), encoding="utf-8", newline="\n"), None)[1], 2, 2),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e = T.MƏTN, T.İSTƏNİLƏN
    return {"oxu": F(m, qaytarır=e), "faylOxu": F(m, qaytarır=e),
            "oxuHamısı": F(m, qaytarır=T.Siyahı(e)),
            "yaz": F(e, qaytarır=m), "faylYaz": F(m, e, qaytarır=T.HEÇ)}
