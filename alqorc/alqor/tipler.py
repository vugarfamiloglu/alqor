"""
Alqor — Tip təsviri və tip üzərində əməliyyatlar.

Tədrici (gradual) tip sistemi: `istənilən` tipi bütün yoxlamaları
keçir. Bu, yalnız ƏMİN OLDUĞUMUZ hallarda xəta bildirməyə imkan verir —
yanlış xəbərdarlıq verən yoxlayıcı heç yoxlayıcıdan pisdir.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# ═══════════════════════════════════════════════════════════════════════
#  Baza
# ═══════════════════════════════════════════════════════════════════════

class Tip:
    """Bütün tiplərin baza sinfi."""

    def mətn(self) -> str:
        return "?"

    def __str__(self) -> str:
        return self.mətn()

    def __repr__(self) -> str:
        return f"Tip({self.mətn()})"


# ═══════════════════════════════════════════════════════════════════════
#  Sadə tiplər
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Sadə(Tip):
    ad: str

    def mətn(self) -> str:
        return self.ad


TAM = Sadə("tam")
ONLUQ = Sadə("onluq")
MƏTN = Sadə("mətn")
MƏNTİQ = Sadə("məntiq")
SİMVOL = Sadə("simvol")
BAYT = Sadə("bayt")
HEÇ = Sadə("heç")
ELEMENT = Sadə("element")
DİAPAZON = Sadə("diapazon")
MODUL = Sadə("modul")


@dataclass(frozen=True)
class İstənilən(Tip):
    """`istənilən` — tip yoxlaması söndürülür (tədrici tiplərin açarı)."""

    def mətn(self) -> str:
        return "istənilən"


İSTƏNİLƏN = İstənilən()


@dataclass(frozen=True)
class Naməlum(Tip):
    """
    Çıxarıla bilmədi. `istənilən`-dən fərqi: bu, bizim bilmədiyimizdir,
    istifadəçinin qərarı deyil. Davranış eynidir — xəta verilmir.
    """

    def mətn(self) -> str:
        return "?"


NAMƏLUM = Naməlum()


# ═══════════════════════════════════════════════════════════════════════
#  Kolleksiyalar
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Siyahı(Tip):
    element: Tip = NAMƏLUM

    def mətn(self) -> str:
        return (f"siyahı[{self.element.mətn()}]"
                if not isinstance(self.element, Naməlum) else "siyahı")


@dataclass(frozen=True)
class Lüğət(Tip):
    açar: Tip = NAMƏLUM
    dəyər: Tip = NAMƏLUM

    def mətn(self) -> str:
        if isinstance(self.açar, Naməlum):
            return "lüğət"
        return f"lüğət[{self.açar.mətn()}, {self.dəyər.mətn()}]"


@dataclass(frozen=True)
class Dəst(Tip):
    element: Tip = NAMƏLUM

    def mətn(self) -> str:
        return (f"dəst[{self.element.mətn()}]"
                if not isinstance(self.element, Naməlum) else "dəst")


@dataclass(frozen=True)
class Kortej(Tip):
    elementlər: tuple[Tip, ...] = ()

    def mətn(self) -> str:
        if not self.elementlər:
            return "kortej"
        return "kortej[" + ", ".join(e.mətn()
                                     for e in self.elementlər) + "]"


@dataclass(frozen=True)
class Generator(Tip):
    element: Tip = NAMƏLUM

    def mətn(self) -> str:
        return (f"generator[{self.element.mətn()}]"
                if not isinstance(self.element, Naməlum) else "generator")


@dataclass(frozen=True)
class Gələcək(Tip):
    nəticə: Tip = NAMƏLUM

    def mətn(self) -> str:
        return (f"gələcək[{self.nəticə.mətn()}]"
                if not isinstance(self.nəticə, Naməlum) else "gələcək")


# ═══════════════════════════════════════════════════════════════════════
#  Funksiya
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Parametr:
    ad: str
    tip: Tip = NAMƏLUM
    standartı_var: bool = False
    variadic: bool = False
    yalnız_adlı: bool = False


@dataclass(frozen=True)
class FunksiyaTipi(Tip):
    parametrlər: tuple[Parametr, ...] = ()
    qaytarma: Tip = NAMƏLUM
    asinxron: bool = False
    generator: bool = False

    def mətn(self) -> str:
        p = ", ".join(x.tip.mətn() for x in self.parametrlər)
        q = self.qaytarma.mətn()
        return f"funksiyaTipi({p}) -> {q}"

    @property
    def minimum_arqument(self) -> int:
        return sum(1 for p in self.parametrlər
                   if not p.standartı_var and not p.variadic
                   and not p.yalnız_adlı)

    @property
    def maksimum_arqument(self) -> int | None:
        if any(p.variadic for p in self.parametrlər):
            return None
        return sum(1 for p in self.parametrlər if not p.yalnız_adlı)


# ═══════════════════════════════════════════════════════════════════════
#  İstifadəçi tipləri
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SinifTipi(Tip):
    ad: str
    baza: "SinifTipi | None" = None
    sahələr: dict[str, Tip] = field(default_factory=dict)
    metodlar: dict[str, FunksiyaTipi] = field(default_factory=dict)
    statiklər: dict[str, Tip] = field(default_factory=dict)
    quruculər: dict[str, FunksiyaTipi] = field(default_factory=dict)
    interfeyslər: tuple[str, ...] = ()
    quruluş: str = "sinif"
    mücərrəd: bool = False

    def mətn(self) -> str:
        return self.ad

    def üzv(self, ad: str) -> Tip | None:
        s: SinifTipi | None = self
        while s is not None:
            if ad in s.sahələr:
                return s.sahələr[ad]
            if ad in s.metodlar:
                return s.metodlar[ad]
            if ad in s.statiklər:
                return s.statiklər[ad]
            s = s.baza
        return None

    def alt_tipdirmi(self, digər: "SinifTipi") -> bool:
        s: SinifTipi | None = self
        while s is not None:
            if s.ad == digər.ad:
                return True
            if digər.ad in s.interfeyslər:
                return True
            s = s.baza
        return False

    def __hash__(self) -> int:
        return hash(("sinif", self.ad))

    def __eq__(self, digər: Any) -> bool:
        return isinstance(digər, SinifTipi) and digər.ad == self.ad


@dataclass
class SadalamaTipi(Tip):
    ad: str
    variantlar: tuple[str, ...] = ()
    metodlar: dict[str, FunksiyaTipi] = field(default_factory=dict)

    def mətn(self) -> str:
        return self.ad

    def __hash__(self) -> int:
        return hash(("sadalama", self.ad))

    def __eq__(self, digər: Any) -> bool:
        return isinstance(digər, SadalamaTipi) and digər.ad == self.ad


@dataclass
class ModulTipi(Tip):
    ad: str
    üzvlər: dict[str, Tip] = field(default_factory=dict)
    çağırıla_bilir: bool = False

    def mətn(self) -> str:
        return f"modul[{self.ad}]"

    def __hash__(self) -> int:
        return hash(("modul", self.ad))

    def __eq__(self, digər: Any) -> bool:
        return isinstance(digər, ModulTipi) and digər.ad == self.ad


@dataclass(frozen=True)
class Generik(Tip):
    """Generik parametr: `T`."""
    ad: str

    def mətn(self) -> str:
        return self.ad


# ═══════════════════════════════════════════════════════════════════════
#  Birləşmə
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Birləşmə(Tip):
    variantlar: tuple[Tip, ...]

    def mətn(self) -> str:
        # `T | heç` → `T?`
        qalan = [v for v in self.variantlar if v != HEÇ]
        if len(qalan) == 1 and len(self.variantlar) == 2:
            return f"{qalan[0].mətn()}?"
        return " | ".join(v.mətn() for v in self.variantlar)

    @property
    def ixtiyaridir(self) -> bool:
        return HEÇ in self.variantlar


def birləşmə(*tiplər: Tip) -> Tip:
    """Təkrarları atıb birləşmə qurur; bir variant qalsa onu qaytarır."""
    yığım: list[Tip] = []
    for t in tiplər:
        if isinstance(t, İstənilən):
            return İSTƏNİLƏN
        if isinstance(t, Birləşmə):
            for v in t.variantlar:
                if v not in yığım:
                    yığım.append(v)
        elif isinstance(t, Naməlum):
            continue
        elif t not in yığım:
            yığım.append(t)
    if not yığım:
        return NAMƏLUM
    if len(yığım) == 1:
        return yığım[0]
    return Birləşmə(tuple(yığım))


def ixtiyari(t: Tip) -> Tip:
    """`T` → `T?`"""
    if isinstance(t, (İstənilən, Naməlum)):
        return t
    if t == HEÇ:
        return HEÇ
    if isinstance(t, Birləşmə) and t.ixtiyaridir:
        return t
    return birləşmə(t, HEÇ)


def açılmış(t: Tip) -> Tip:
    """`T?` → `T` (boş variantı çıxarır)."""
    if isinstance(t, Birləşmə):
        qalan = tuple(v for v in t.variantlar if v != HEÇ)
        if not qalan:
            return NAMƏLUM
        return qalan[0] if len(qalan) == 1 else Birləşmə(qalan)
    return t


def ixtiyaridir(t: Tip) -> bool:
    if t == HEÇ:
        return True
    return isinstance(t, Birləşmə) and t.ixtiyaridir


# ═══════════════════════════════════════════════════════════════════════
#  Uyğunluq (assignability)
# ═══════════════════════════════════════════════════════════════════════

#  İmplisit genişlənmə zənciri (Spesifikasiya § 2.8)
GENİŞLƏNMƏ: dict[Tip, tuple[Tip, ...]] = {
    TAM: (ONLUQ,),
    SİMVOL: (MƏTN,),
}


def uyğundur(mənbə: Tip, hədəf: Tip) -> bool:
    """
    `mənbə` tipindəki dəyər `hədəf` tipinə mənimsədilə bilərmi?

    Tədrici tiplərin qaydası: `istənilən` və `?` (naməlum) həmişə keçir.
    """
    if isinstance(mənbə, (İstənilən, Naməlum)):
        return True
    if isinstance(hədəf, (İstənilən, Naməlum)):
        return True
    if mənbə == hədəf:
        return True

    # Birləşmə hədəf: hər hansı variant uyğun gəlsə kifayətdir
    if isinstance(hədəf, Birləşmə):
        return any(uyğundur(mənbə, v) for v in hədəf.variantlar)

    # Birləşmə mənbə: BÜTÜN variantlar uyğun gəlməlidir
    if isinstance(mənbə, Birləşmə):
        return all(uyğundur(v, hədəf) for v in mənbə.variantlar)

    # İmplisit genişlənmə
    if mənbə in GENİŞLƏNMƏ and hədəf in GENİŞLƏNMƏ[mənbə]:
        return True

    # Kolleksiyalar — kovariant (sadələşdirilmiş)
    if isinstance(mənbə, Siyahı) and isinstance(hədəf, Siyahı):
        return uyğundur(mənbə.element, hədəf.element)
    if isinstance(mənbə, Dəst) and isinstance(hədəf, Dəst):
        return uyğundur(mənbə.element, hədəf.element)
    if isinstance(mənbə, Lüğət) and isinstance(hədəf, Lüğət):
        return (uyğundur(mənbə.açar, hədəf.açar)
                and uyğundur(mənbə.dəyər, hədəf.dəyər))
    if isinstance(mənbə, Kortej) and isinstance(hədəf, Kortej):
        if not hədəf.elementlər:
            return True
        if len(mənbə.elementlər) != len(hədəf.elementlər):
            return False
        return all(uyğundur(a, b) for a, b in
                   zip(mənbə.elementlər, hədəf.elementlər))
    if isinstance(mənbə, Generator) and isinstance(hədəf, Generator):
        return uyğundur(mənbə.element, hədəf.element)
    if isinstance(mənbə, Gələcək) and isinstance(hədəf, Gələcək):
        return uyğundur(mənbə.nəticə, hədəf.nəticə)

    # Siniflər — miras və interfeyslər
    if isinstance(mənbə, SinifTipi) and isinstance(hədəf, SinifTipi):
        return mənbə.alt_tipdirmi(hədəf)

    # Funksiyalar — sadələşdirilmiş (yalnız arqument sayı)
    if isinstance(mənbə, FunksiyaTipi) and isinstance(hədəf, FunksiyaTipi):
        if not hədəf.parametrlər:
            return True
        return len(mənbə.parametrlər) == len(hədəf.parametrlər)

    # Generik parametrlər hər şeyi qəbul edir
    if isinstance(hədəf, Generik) or isinstance(mənbə, Generik):
        return True

    return False


def birləşdir(a: Tip, b: Tip) -> Tip:
    """
    İki budağın tiplərini birləşdirir (`əgər` nəticəsi kimi).

    Eyni tiplər → həmin tip. Fərqli → birləşmə.
    """
    if a == b:
        return a
    if isinstance(a, Naməlum):
        return b
    if isinstance(b, Naməlum):
        return a
    if isinstance(a, İstənilən) or isinstance(b, İstənilən):
        return İSTƏNİLƏN
    # tam + onluq → onluq
    if {a, b} == {TAM, ONLUQ}:
        return ONLUQ
    if isinstance(a, Siyahı) and isinstance(b, Siyahı):
        return Siyahı(birləşdir(a.element, b.element))
    if isinstance(a, SinifTipi) and isinstance(b, SinifTipi):
        if a.alt_tipdirmi(b):
            return b
        if b.alt_tipdirmi(a):
            return a
    return birləşmə(a, b)


# ═══════════════════════════════════════════════════════════════════════
#  Köməkçi yoxlamalar
# ═══════════════════════════════════════════════════════════════════════

ƏDƏDLƏR = (TAM, ONLUQ)


def ədəddir(t: Tip) -> bool:
    return t in ƏDƏDLƏR


def naməlumdur(t: Tip) -> bool:
    """Yoxlamanı atlamalıyıqmı?"""
    return isinstance(t, (İstənilən, Naməlum, Generik))


def iterasiya_elementi(t: Tip) -> Tip:
    """`hər x üçün t içində` — `x`-in tipi."""
    if isinstance(t, Siyahı):
        return t.element
    if isinstance(t, Dəst):
        return t.element
    if isinstance(t, Lüğət):
        return t.açar
    if isinstance(t, Generator):
        return t.element
    if t == MƏTN:
        return SİMVOL
    if t == DİAPAZON:
        return TAM
    if isinstance(t, Kortej):
        if not t.elementlər:
            return NAMƏLUM
        nəticə = t.elementlər[0]
        for e in t.elementlər[1:]:
            nəticə = birləşdir(nəticə, e)
        return nəticə
    return NAMƏLUM


def iterasiya_oluna_bilir(t: Tip) -> bool:
    if naməlumdur(t):
        return True
    return (isinstance(t, (Siyahı, Dəst, Lüğət, Kortej, Generator,
                           SinifTipi, SadalamaTipi))
            or t in (MƏTN, DİAPAZON, BAYT, ELEMENT))


def indekslənə_bilir(t: Tip) -> bool:
    if naməlumdur(t):
        return True
    return (isinstance(t, (Siyahı, Lüğət, Kortej, SinifTipi))
            or t in (MƏTN, BAYT))


def indeks_nəticəsi(t: Tip) -> Tip:
    if isinstance(t, Siyahı):
        return t.element
    if isinstance(t, Lüğət):
        return t.dəyər
    if t == MƏTN:
        return SİMVOL
    if t == BAYT:
        return TAM
    if isinstance(t, Kortej):
        if not t.elementlər:
            return NAMƏLUM
        nəticə = t.elementlər[0]
        for e in t.elementlər[1:]:
            nəticə = birləşdir(nəticə, e)
        return nəticə
    return NAMƏLUM


def indeks_açarı(t: Tip) -> Tip:
    """İndeksin özünün gözlənilən tipi."""
    if isinstance(t, Lüğət):
        return t.açar
    if isinstance(t, (Siyahı, Kortej)) or t in (MƏTN, BAYT):
        return TAM
    return NAMƏLUM
