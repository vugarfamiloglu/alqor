"""
Paketlər: semantik versiyalar, versiya aralıqları və `gətir ad` üçün
paket axtarışı (Spesifikasiya § 8.9, § 8.10).

Axtarış sırası (`gətir tarix_alətləri`):
  1. standart kitabxana (çağıran tərəf yoxlayır)
  2. layihənin `mənbə/` qovluğu: `mənbə/ad.alq`, `mənbə/ad/indeks.alq`
  3. `paketlər/ad/` (alqorpm quraşdırır)
  4. qlobal: `$ALQOR_PAKETLER` və ya `~/.alq/paketlər/ad/`
  5. sistem: `/usr/lib/alqor/paketlər/ad/`

Paketin giriş faylı: `layihe.alq` → `[qurma] giriş`, yoxdursa
`mənbə/indeks.alq`, `mənbə/əsas.alq`, `indeks.alq`.
`gətir ad.alt` → paketin `mənbə/alt.alq` faylı.
"""

from __future__ import annotations

import os
import re
from functools import total_ordering
from pathlib import Path

MANİFEST_ADLARI = ("layihe.alq", "layihe.alqor")


# ═══════════════════════════════════════════════════════════════════════
#  Semantik versiya
# ═══════════════════════════════════════════════════════════════════════

class VersiyaXətası(ValueError):
    pass


_VERSİYA = re.compile(
    r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$")


@total_ordering
class Versiya:
    __slots__ = ("əsas", "kiçik", "yamaq", "ön")

    def __init__(self, əsas: int, kiçik: int = 0, yamaq: int = 0,
                 ön: tuple = ()):
        self.əsas, self.kiçik, self.yamaq, self.ön = əsas, kiçik, yamaq, ön

    @classmethod
    def oxu(cls, s: str) -> "Versiya":
        m = _VERSİYA.match(str(s).strip())
        if not m:
            raise VersiyaXətası(f"`{s}` semantik versiya deyil "
                                "(məs. 1.2.3)")
        ön = tuple(int(x) if x.isdigit() else x
                   for x in m.group(4).split(".")) if m.group(4) else ()
        return cls(int(m.group(1)), int(m.group(2) or 0),
                   int(m.group(3) or 0), ön)

    def _açar(self):
        # ön-buraxılış (1.0.0-beta) əsas buraxılışdan kiçikdir
        ön = tuple((0, x, "") if isinstance(x, int) else (1, 0, x)
                   for x in self.ön)
        return (self.əsas, self.kiçik, self.yamaq, 0 if self.ön else 1, ön)

    def __eq__(self, o) -> bool:
        return isinstance(o, Versiya) and self._açar() == o._açar()

    def __lt__(self, o: "Versiya") -> bool:
        return self._açar() < o._açar()

    def __hash__(self) -> int:
        return hash(self._açar())

    def __str__(self) -> str:
        s = f"{self.əsas}.{self.kiçik}.{self.yamaq}"
        return s + ("-" + ".".join(map(str, self.ön)) if self.ön else "")

    __repr__ = __str__


def _müqayisə(op: str, v: Versiya, h: Versiya) -> bool:
    return {"=": v == h, ">": v > h, ">=": v >= h, "<": v < h,
            "<=": v <= h}[op]


class Aralıq:
    """
    Versiya aralığı: `1.2.3`, `^1.2.3`, `~1.2.3`, `>=1.2 <2`, `1.2.*`,
    `*`, `1.0 || 2.0`. Çılpaq `1.2` → `^1.2` kimi (spes. § 8.9 nümunəsi:
    `veb = "2.1"` uyğun yeniləmələri qəbul edir); dəqiq versiya üçün `=1.2.3`.
    """

    def __init__(self, mətn: str):
        self.mətn = str(mətn).strip() or "*"
        self.variantlar: list[list[tuple[str, Versiya]]] = []
        for hissə in self.mətn.split("||"):
            şərtlər: list[tuple[str, Versiya]] = []
            for t in re.split(r"[\s,]+", hissə.strip()):
                if t:
                    şərtlər.extend(self._token(t))
            self.variantlar.append(şərtlər)

    @staticmethod
    def _token(t: str) -> list[tuple[str, Versiya]]:
        if t in ("*", "x", "X", "latest", "ən-son"):
            return []
        m = re.match(r"^(\^|~|>=|<=|>|<|=)?(.*)$", t)
        op, v = m.group(1) or "", m.group(2)
        if re.search(r"(^|\.)[*xX]$", v):            # 1.2.* / 1.x
            hissələr = [h for h in v.split(".") if h not in ("*", "x", "X")]
            if not hissələr:
                return []
            b = Versiya.oxu(".".join(hissələr))
            son = Versiya(b.əsas + 1, 0, 0) if len(hissələr) == 1 else \
                Versiya(b.əsas, b.kiçik + 1, 0)
            return [(">=", b), ("<", son)]
        try:
            b = Versiya.oxu(v)
        except VersiyaXətası:
            raise VersiyaXətası(f"versiya aralığı anlaşılmadı: `{t}`")
        say = len(v.lstrip("v").split("-")[0].split("."))
        if op in ("^", ""):                    # çılpaq "2.1" də `^` kimi
            if b.əsas > 0:
                son = Versiya(b.əsas + 1, 0, 0)
            elif b.kiçik > 0 or say < 3:
                son = Versiya(0, b.kiçik + 1, 0)
            else:
                son = Versiya(0, 0, b.yamaq + 1)
            return [(">=", b), ("<", son)]
        if op == "~":
            son = Versiya(b.əsas + 1, 0, 0) if say == 1 else \
                Versiya(b.əsas, b.kiçik + 1, 0)
            return [(">=", b), ("<", son)]
        return [(op, b)]

    def uyğundur(self, v: Versiya | str) -> bool:
        v = v if isinstance(v, Versiya) else Versiya.oxu(v)
        for şərtlər in self.variantlar:
            if not all(_müqayisə(op, v, h) for op, h in şərtlər):
                continue
            # ön-buraxılışlar yalnız aralıq özü ön-buraxılış adlayanda
            if v.ön and not any(h.ön and (h.əsas, h.kiçik, h.yamaq) ==
                                (v.əsas, v.kiçik, v.yamaq)
                                for _, h in şərtlər):
                continue
            return True
        return False

    def ən_yaxşı(self, versiyalar) -> Versiya | None:
        uyğun = [v for v in versiyalar if self.uyğundur(v)]
        return max(uyğun) if uyğun else None

    def __str__(self) -> str:
        return self.mətn


def ad_yoxla(ad: str) -> str:
    """Paket adı: kiçik hərf, rəqəm, `_`, `-`; istəyə görə `@sahə/ad`."""
    if not re.fullmatch(r"(@[a-zəıöüğşç0-9][a-zəıöüğşç0-9_-]*/)?"
                        r"[a-zəıöüğşç][a-zəıöüğşç0-9_-]{0,63}", ad or ""):
        raise VersiyaXətası(
            f"`{ad}` yanlış paket adıdır — kiçik hərf, rəqəm, `_`, `-` "
            "(məs. `tarix_alətləri`, `@şirkət/analitika`)")
    return ad


# ═══════════════════════════════════════════════════════════════════════
#  Paket axtarışı
# ═══════════════════════════════════════════════════════════════════════

def qlobal_qovluq() -> Path:
    return Path(os.environ.get("ALQOR_PAKETLER") or
                Path.home() / ".alq" / "paketlər")


def layihə_kökü(başlanğıc: Path) -> Path | None:
    p = başlanğıc.resolve()
    if p.is_file():
        p = p.parent
    for q in (p, *p.parents):
        if any((q / m).is_file() for m in MANİFEST_ADLARI):
            return q
    return None


def paket_girişi(qovluq: Path) -> Path | None:
    """Quraşdırılmış paketin giriş faylı."""
    for m in MANİFEST_ADLARI:
        if (qovluq / m).is_file():
            try:
                from .layihe import oxu
                d = oxu((qovluq / m).read_text(encoding="utf-8"))
                g = (d.get("qurma") or {}).get("giriş")
                if g and (qovluq / g).is_file():
                    return qovluq / g
            except Exception:                           # noqa: BLE001
                pass
            break
    for nisbi in ("mənbə/indeks.alq", "mənbə/əsas.alq", "indeks.alq"):
        if (qovluq / nisbi).is_file():
            return qovluq / nisbi
    return None


def paket_tap(ad: str, baza: Path | None) -> Path | None:
    """`gətir ad` / `gətir ad.alt` üçün fayl yolu (tapılmasa None)."""
    if not ad or ad.startswith((".", "/")) or ad.endswith((".alq",
                                                            ".alqor")):
        return None
    if ad.startswith("@"):
        əsas, alt = ad, []
        if "." in ad.split("/", 1)[-1]:
            q, _, a = ad.rpartition(".")
            əsas, alt = q, a.split("/")
    else:
        əsas, *alt = ad.split(".")
    kök = layihə_kökü(baza) if baza is not None else None
    namizədlər: list[Path] = []
    if kök is not None:
        mənbə = kök / "mənbə"
        if not alt:
            namizədlər += [mənbə / f"{əsas}.alq", mənbə / əsas / "indeks.alq"]
        namizədlər.append(kök / "paketlər" / əsas)
    namizədlər += [qlobal_qovluq() / əsas,
                   Path("/usr/lib/alqor/paketlər") / əsas]
    for n in namizədlər:
        if n.is_file():
            return n
        if n.is_dir():
            if alt:
                f = n / "mənbə" / Path(*alt).with_suffix(".alq")
                if f.is_file():
                    return f
                continue
            g = paket_girişi(n)
            if g is not None:
                return g
    return None
