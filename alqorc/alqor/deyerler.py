"""
Alqor — İcra zamanı dəyərlər.

Alqor tipləri Python tiplərinə belə uyğunlaşır:

    tam      → int           siyahı  → list
    onluq    → float         lüğət   → dict
    mətn     → str           dəst    → set
    simvol   → str (1 qrafem) kortej → tuple
    məntiq   → bool          boş     → None
    bayt     → bytes

Funksiya, sinif və nümunələr üçün ayrıca siniflər var.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

from . import aac as A
from .token import Yer


# ═══════════════════════════════════════════════════════════════════════
#  İcra zamanı xətası
# ═══════════════════════════════════════════════════════════════════════

class AlqorXəta(Exception):
    """İstifadəçi kodundan atılan xəta (`at ...`) və ya daxili icra xətası."""

    def __init__(self, tip: str, mesaj: str, yer: Yer | None = None,
                 kod: str = "", dəyər: Any = None):
        super().__init__(mesaj)
        self.tip = tip               # "ArqumentXətası", "TipXətası" ...
        self.mesaj = mesaj
        self.yer = yer
        self.kod = kod
        self.dəyər = dəyər           # `at` ilə atılan obyekt
        self.yığın: list[str] = []

    def __str__(self) -> str:
        return f"{self.tip}: {self.mesaj}"


# ── Xəta iyerarxiyası (Spesifikasiya § 7.3) ────────────────────────────

XETA_AGACI: dict[str, str | None] = {
    "Atılan": None,
    "Xəta": "Atılan",
    "ArqumentXətası": "Xəta",
    "TipXətası": "ArqumentXətası",
    "DəyərXətası": "ArqumentXətası",
    "DiapazonXətası": "ArqumentXətası",
    "ÇevrilməXətası": "Xəta",
    "RiyaziXəta": "Xəta",
    "BölməXətası": "RiyaziXəta",
    "DaşmaXətası": "RiyaziXəta",
    "KolleksiyaXətası": "Xəta",
    "İndeksXətası": "KolleksiyaXətası",
    "AçarXətası": "KolleksiyaXətası",
    "BoşKolleksiyaXətası": "KolleksiyaXətası",
    "GirişÇıxışXətası": "Xəta",
    "FaylTapılmadıXətası": "GirişÇıxışXətası",
    "İcazəXətası": "GirişÇıxışXətası",
    "ŞəbəkəXətası": "Xəta",
    "BağlantıXətası": "ŞəbəkəXətası",
    "VaxtBitdiXətası": "ŞəbəkəXətası",
    "FormatXətası": "Xəta",
    "JSONXətası": "FormatXətası",
    "BoşDəyərXətası": "Xəta",
    "VaxtXətası": "Xəta",
    "KritikXəta": "Atılan",
    "YaddaşBitdiXətası": "KritikXəta",
    "StekDaşmaXətası": "KritikXəta",
    "İddiaXətası": "KritikXəta",
    "DaxiliXəta": "KritikXəta",
}


def xəta_uyğundur(atılan: str, tutulan: str) -> bool:
    """`atılan` xəta tipi `tutulan` tipinin alt növüdürmü?"""
    cari: str | None = atılan
    while cari is not None:
        if cari == tutulan:
            return True
        cari = XETA_AGACI.get(cari)
    return False


# ═══════════════════════════════════════════════════════════════════════
#  Axın idarəetmə siqnalları
# ═══════════════════════════════════════════════════════════════════════

class Siqnal(Exception):
    """Dövr/funksiya axınını idarə edən daxili siqnallar."""


class DayanSiqnalı(Siqnal):
    def __init__(self, etiket: str | None = None):
        self.etiket = etiket


class DavamSiqnalı(Siqnal):
    def __init__(self, etiket: str | None = None):
        self.etiket = etiket


class QaytarSiqnalı(Siqnal):
    def __init__(self, dəyər: Any = None):
        self.dəyər = dəyər


class VerSiqnalı(Siqnal):
    """`ver` — blok ifadəsini dəyərlə bitirir."""
    def __init__(self, dəyər: Any = None):
        self.dəyər = dəyər


class DayanmaSiqnalı(Siqnal):
    """`dayan(kod)` — proqramı bitirir."""
    def __init__(self, kod: int = 0):
        self.kod = kod


# ═══════════════════════════════════════════════════════════════════════
#  Mühit (əhatə dairəsi)
# ═══════════════════════════════════════════════════════════════════════

class Mühit:
    """Leksik əhatə dairəsi — adların dəyərlərə bağlanması."""

    __slots__ = ("adlar", "üst", "sabitlər", "qloballar")

    def __init__(self, üst: "Mühit | None" = None):
        self.adlar: dict[str, Any] = {}
        self.sabitlər: set[str] = set()
        self.qloballar: set[str] = set()
        self.üst = üst

    # ── Oxuma ─────────────────────────────────────────────────────────

    def al(self, ad: str) -> Any:
        m: Mühit | None = self
        while m is not None:
            if ad in m.adlar:
                return m.adlar[ad]
            m = m.üst
        raise AlqorXəta("ArqumentXətası",
                        f"`{ad}` təyin edilməyib", kod="ALQ-T022")

    def var(self, ad: str) -> bool:
        m: Mühit | None = self
        while m is not None:
            if ad in m.adlar:
                return True
            m = m.üst
        return False

    # ── Yazma ─────────────────────────────────────────────────────────

    def elan(self, ad: str, dəyər: Any, sabit: bool = False) -> None:
        """Yeni ad yaradır (cari əhatədə)."""
        self.adlar[ad] = dəyər
        if sabit:
            self.sabitlər.add(ad)

    def təyin(self, ad: str, dəyər: Any) -> None:
        """Mövcud ada yeni dəyər verir — yuxarı əhatələrdə axtarır."""
        if ad in self.qloballar:
            kök = self._kök()
            kök._yoxla_sabit(ad)
            kök.adlar[ad] = dəyər
            return
        m: Mühit | None = self
        while m is not None:
            if ad in m.adlar:
                m._yoxla_sabit(ad)
                m.adlar[ad] = dəyər
                return
            m = m.üst
        raise AlqorXəta("ArqumentXətası",
                        f"`{ad}` təyin edilməyib", kod="ALQ-T022")

    def _yoxla_sabit(self, ad: str) -> None:
        if ad in self.sabitlər:
            raise AlqorXəta("ArqumentXətası",
                            f"`{ad}` sabitdir, dəyişdirilə bilməz",
                            kod="ALQ-T020")

    def _kök(self) -> "Mühit":
        m = self
        while m.üst is not None:
            m = m.üst
        return m

    def alt(self) -> "Mühit":
        return Mühit(self)


# ═══════════════════════════════════════════════════════════════════════
#  Çağırıla bilən dəyərlər
# ═══════════════════════════════════════════════════════════════════════

class Çağırılan:
    """
    Funksiya kimi çağırıla bilən hər şeyin baza sinfi.

    Qeyd: burada `ad` sahəsi QƏSDƏN elan olunmur. Elan olunsaydı,
    `@dataclass` onu alt siniflərdə standart dəyərli sahə kimi görər və
    "non-default argument follows default argument" xətası verərdi.
    Hər alt sinif `ad`-ı özü təyin edir.
    """

    def çağır(self, icraçı, arqumentlər: list, adlı: dict,
              yer: Yer | None = None) -> Any:
        raise NotImplementedError

    @property
    def çağırıla_bilən_adı(self) -> str:
        return getattr(self, "ad", "<anonim>")


@dataclass
class Funksiya(Çağırılan):
    """İstifadəçi funksiyası və ya metodu."""
    ad: str
    parametrlər: list[A.Parametr]
    gövdə: list[A.Cümlə] | A.İfadə
    mühit: Mühit
    asinxron: bool = False
    generator: bool = False
    özü: Any = None                       # bağlı metod üçün
    sinif: Any = None                     # `üst` həlli üçün
    annotasiyalar: list[str] = field(default_factory=list)
    yaddaş: dict | None = None            # @yaddaşla keşi

    def bağla(self, nümunə: Any) -> "Funksiya":
        return Funksiya(self.ad, self.parametrlər, self.gövdə, self.mühit,
                        self.asinxron, self.generator, nümunə, self.sinif,
                        self.annotasiyalar, self.yaddaş)

    def çağır(self, icraçı, arqumentlər, adlı, yer=None):
        return icraçı.funksiya_çağır(self, arqumentlər, adlı, yer)

    def __repr__(self) -> str:
        return f"<funksiya {self.ad}>"


@dataclass
class Daxili(Çağırılan):
    """Standart kitabxananın funksiyası."""
    ad: str
    f: Callable
    min_arq: int = 0
    maks_arq: int | None = None
    icraçı_lazımdır: bool = False

    def çağır(self, icraçı, arqumentlər, adlı, yer=None):
        n = len(arqumentlər)
        if n < self.min_arq or (self.maks_arq is not None
                                and n > self.maks_arq):
            gözlənilən = (f"{self.min_arq}" if self.maks_arq == self.min_arq
                          else f"{self.min_arq}–"
                               f"{self.maks_arq if self.maks_arq is not None else '∞'}")
            raise AlqorXəta(
                "ArqumentXətası",
                f"`{self.ad}` {gözlənilən} arqument gözləyir, {n} verilib",
                yer, "ALQ-T003")
        if self.icraçı_lazımdır:
            return self.f(icraçı, *arqumentlər, **adlı)
        return self.f(*arqumentlər, **adlı)

    def __repr__(self) -> str:
        return f"<daxili {self.ad}>"


@dataclass
class BağlıMetod(Çağırılan):
    """Daxili tipin metodu: `"salam".böyüyə`"""
    ad: str
    obyekt: Any
    f: Callable

    def çağır(self, icraçı, arqumentlər, adlı, yer=None):
        return self.f(self.obyekt, *arqumentlər, **adlı)

    def __repr__(self) -> str:
        return f"<metod {self.ad}>"


# ═══════════════════════════════════════════════════════════════════════
#  Siniflər və nümunələr
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Sinif(Çağırılan):
    ad: str
    baza: "Sinif | None" = None
    metodlar: dict[str, Funksiya] = field(default_factory=dict)
    statiklər: dict[str, Any] = field(default_factory=dict)
    quruculər: dict[str, Funksiya] = field(default_factory=dict)
    xassələr: list[A.XassəElanı] = field(default_factory=list)
    hesablananlar: dict[str, Funksiya] = field(default_factory=dict)
    yazıcılar: dict[str, Funksiya] = field(default_factory=dict)
    dağıdıcı: Funksiya | None = None
    mücərrəd: bool = False
    son: bool = False
    quruluş: str = "sinif"                # "sinif" | "struktur" | "obyekt"
    mücərrəd_metodlar: set[str] = field(default_factory=set)
    interfeyslər: list[str] = field(default_factory=list)
    mühit: Mühit | None = None

    # ── Axtarış ───────────────────────────────────────────────────────

    def metod_tap(self, ad: str) -> Funksiya | None:
        s: Sinif | None = self
        while s is not None:
            if ad in s.metodlar:
                return s.metodlar[ad]
            s = s.baza
        return None

    def hesablanan_tap(self, ad: str) -> Funksiya | None:
        s: Sinif | None = self
        while s is not None:
            if ad in s.hesablananlar:
                return s.hesablananlar[ad]
            s = s.baza
        return None

    def yazıcı_tap(self, ad: str) -> Funksiya | None:
        s: Sinif | None = self
        while s is not None:
            if ad in s.yazıcılar:
                return s.yazıcılar[ad]
            s = s.baza
        return None

    def statik_tap(self, ad: str) -> tuple[bool, Any]:
        s: Sinif | None = self
        while s is not None:
            if ad in s.statiklər:
                return True, s.statiklər[ad]
            if ad in s.metodlar and "statik" in s.metodlar[ad].annotasiyalar:
                return True, s.metodlar[ad]
            s = s.baza
        return False, None

    def bütün_xassələr(self) -> list[A.XassəElanı]:
        zəncir: list[Sinif] = []
        s: Sinif | None = self
        while s is not None:
            zəncir.append(s)
            s = s.baza
        nəticə: list[A.XassəElanı] = []
        for s in reversed(zəncir):
            nəticə.extend(s.xassələr)
        return nəticə

    def alt_sinifdirmi(self, digər: "Sinif") -> bool:
        s: Sinif | None = self
        while s is not None:
            if s is digər:
                return True
            s = s.baza
        return False

    def çağır(self, icraçı, arqumentlər, adlı, yer=None):
        return icraçı.nümunə_yarat(self, None, arqumentlər, adlı, yer)

    def __repr__(self) -> str:
        return f"<{self.quruluş} {self.ad}>"


class Nümunə:
    """Sinif nümunəsi."""

    __slots__ = ("sinif", "sahələr", "_keş")

    def __init__(self, sinif: Sinif):
        self.sinif = sinif
        self.sahələr: dict[str, Any] = {}
        self._keş: dict[str, Any] = {}      # tənbəl xassələr

    def __repr__(self) -> str:
        return f"<{self.sinif.ad} nümunəsi>"

    def __eq__(self, digər: Any) -> bool:
        if not isinstance(digər, Nümunə):
            return NotImplemented
        if self.sinif.quruluş == "struktur" and digər.sinif is self.sinif:
            return self.sahələr == digər.sahələr
        return self is digər

    def __hash__(self) -> int:
        return id(self)

    def klonla(self) -> "Nümunə":
        yeni = Nümunə(self.sinif)
        yeni.sahələr = dict(self.sahələr)
        return yeni


# ═══════════════════════════════════════════════════════════════════════
#  Sadalama
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Sadalama:
    ad: str
    variantlar: dict[str, "SadalamaDəyəri"] = field(default_factory=dict)
    metodlar: dict[str, Funksiya] = field(default_factory=dict)
    sıra: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<sadalama {self.ad}>"


@dataclass
class SadalamaDəyəri:
    sadalama: Sadalama
    ad: str
    sıra_nömrəsi: int
    dəyər: Any = None
    sahələr: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.sahələr:
            içi = ", ".join(f"{a}={d!r}" for a, d in self.sahələr.items())
            return f"{self.ad}({içi})"
        return self.ad

    def __eq__(self, digər: Any) -> bool:
        if isinstance(digər, SadalamaDəyəri):
            return (self.sadalama is digər.sadalama
                    and self.ad == digər.ad
                    and self.sahələr == digər.sahələr)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((id(self.sadalama), self.ad))


# ═══════════════════════════════════════════════════════════════════════
#  İnterfeys elementi (JSX nəticəsi)
# ═══════════════════════════════════════════════════════════════════════

#  HTML-də özünü bağlayan teqlər
TƏK_TEQLƏR = frozenset({
    "br", "img", "input", "hr", "meta", "link", "area", "base",
    "col", "embed", "source", "track", "wbr",
})

#  Azərbaycan atribut adı → HTML atributu
ATRIBUT_XƏRİTƏSİ = {
    "sinif": "class", "üslub": "style", "dəyər": "value",
    "yerTutucu": "placeholder", "növ": "type", "başlıq": "title",
    "mənbə": "src", "ünvan": "href", "alt": "alt", "ad": "name",
    "id": "id", "açar": "key", "hədəf": "target", "en": "width",
    "hündürlük": "height", "söndürülüb": "disabled",
    "oxunan": "readonly", "tələbolunan": "required",
    "seçilib": "checked", "maksimum": "max", "minimum": "min",
}

#  Hadisə atributları — HTML-ə çıxarılmır, icra mühitində işlənir
HADİSƏ_ATRIBUTLARI = frozenset({
    "klik", "ikiKlik", "dəyişdi", "göndərildi", "fokus", "fokusGetdi",
    "düyməBasma", "düyməBuraxma", "siçanÜstdə", "siçanÇıxdı",
    "sürükləndi", "buraxıldı", "sürüşdü", "basıldı", "quraşdırıldı",
})


class Element:
    """`<div sinif="a">salam</div>` ifadəsinin nəticəsi."""

    __slots__ = ("ad", "atributlar", "uşaqlar", "komponent")

    def __init__(self, ad: str, atributlar: dict[str, Any] | None = None,
                 uşaqlar: list[Any] | None = None):
        self.ad = ad
        self.atributlar: dict[str, Any] = atributlar or {}
        self.uşaqlar: list[Any] = uşaqlar or []
        # Ağacı hansı komponent nümunəsi yaradıb — `pəncərə` modulu
        # vəziyyət dəyişəndə `göstər()`-i yenidən çağırmaq üçün buna
        # baxır. JSX olmayan elementlərdə `None` qalır.
        self.komponent: Any = None

    # ── HTML-ə çevirmə ────────────────────────────────────────────────

    def HTML(self, icraçı=None, girinti: int = 0) -> str:
        if self.ad == "":                       # parça <>...</>
            return "".join(_uşaq_html(u, icraçı, girinti)
                           for u in self.uşaqlar)

        atr = self._atributlar_html(icraçı)
        if self.ad in TƏK_TEQLƏR:
            return f"<{self.ad}{atr}>"
        içi = "".join(_uşaq_html(u, icraçı, girinti + 1)
                      for u in self.uşaqlar)
        return f"<{self.ad}{atr}>{içi}</{self.ad}>"

    def _atributlar_html(self, icraçı) -> str:
        hissələr: list[str] = []
        for ad, dəyər in self.atributlar.items():
            if ad in HADİSƏ_ATRIBUTLARI or callable(dəyər)                     or isinstance(dəyər, Çağırılan):
                continue
            html_adı = ATRIBUT_XƏRİTƏSİ.get(ad, ad)
            if dəyər is True:
                hissələr.append(f" {html_adı}")
            elif dəyər is False or dəyər is None:
                continue
            else:
                mətn = _html_qaç(mətnə(dəyər, icraçı))
                hissələr.append(f' {html_adı}="{mətn}"')
        return "".join(hissələr)

    # ── Kolleksiya kimi davranış ──────────────────────────────────────

    def atribut(self, ad: str, standart: Any = None) -> Any:
        return self.atributlar.get(ad, standart)

    def mətn(self, icraçı=None) -> str:
        """Bütün mətn uşaqlarını birləşdirir (teqsiz)."""
        hissələr: list[str] = []
        for u in self.uşaqlar:
            if isinstance(u, Element):
                hissələr.append(u.mətn(icraçı))
            elif isinstance(u, str):
                hissələr.append(u)
            else:
                hissələr.append(mətnə(u, icraçı))
        return "".join(hissələr)

    def tap(self, teq: str) -> "Element | None":
        if self.ad == teq:
            return self
        for u in self.uşaqlar:
            if isinstance(u, Element):
                nəticə = u.tap(teq)
                if nəticə is not None:
                    return nəticə
        return None

    def __len__(self) -> int:
        return len(self.uşaqlar)

    def __iter__(self):
        return iter(self.uşaqlar)

    def __eq__(self, digər: Any) -> bool:
        if not isinstance(digər, Element):
            return NotImplemented
        return (self.ad == digər.ad
                and self.atributlar == digər.atributlar
                and self.uşaqlar == digər.uşaqlar)

    def __repr__(self) -> str:
        return f"<{self.ad or 'parça'} {len(self.uşaqlar)} uşaq>"


def _uşaq_html(u: Any, icraçı, girinti: int) -> str:
    if isinstance(u, Element):
        return u.HTML(icraçı, girinti)
    if isinstance(u, str):
        return _html_qaç(u)
    if isinstance(u, (list, tuple)):
        return "".join(_uşaq_html(x, icraçı, girinti) for x in u)
    if u is None:
        return ""
    if u is True:
        return "doğru"
    if u is False:
        return ""
    return _html_qaç(mətnə(u, icraçı))


def _html_qaç(m: str) -> str:
    """XSS qoruması — bütün mətn məzmunu qaçış edilir (Spes. § 11.8)."""
    return (m.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;")
             .replace("'", "&#39;"))


# ═══════════════════════════════════════════════════════════════════════
#  Modul
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Modul:
    """
    Modul. Bəzi modullar həm də ÇAĞIRILA BİLİR — məsələn `paralel`:

        gözlə paralel(f1(), f2())        ← çağırış
        gözlə paralel.hamısı([...])      ← üzv

    Bunun üçün `çağırışçı` sahəsi təyin edilir.
    """
    ad: str
    üzvlər: dict[str, Any] = field(default_factory=dict)
    çağırışçı: Any = None

    def __repr__(self) -> str:
        return f"<modul {self.ad}>"


# ═══════════════════════════════════════════════════════════════════════
#  Diapazon
# ═══════════════════════════════════════════════════════════════════════

class AlqorDiapazon:
    """`1..5`, `1..<5`, `10..1`, `1..10 addım 2`"""

    __slots__ = ("başlanğıc", "son", "addım", "xaric")

    def __init__(self, başlanğıc: int, son: int, addım: int | None = None,
                 xaric: bool = False):
        self.başlanğıc = başlanğıc
        self.son = son
        self.xaric = xaric
        if addım is None:
            addım = 1 if son >= başlanğıc else -1
        if addım == 0:
            raise AlqorXəta("ArqumentXətası", "diapazon addımı 0 ola bilməz",
                            kod="ALQ-R002")
        self.addım = addım

    def __iter__(self):
        b, s, a = self.başlanğıc, self.son, self.addım
        if a > 0:
            hədd = s if self.xaric else s + 1
            return iter(range(b, hədd, a))
        hədd = s if self.xaric else s - 1
        return iter(range(b, hədd, a))

    def __len__(self) -> int:
        return len(list(iter(self)))

    def __contains__(self, x: Any) -> bool:
        return x in list(iter(self))

    def __repr__(self) -> str:
        nöqtə = "..<" if self.xaric else ".."
        a = f" addım {self.addım}" if abs(self.addım) != 1 else ""
        return f"{self.başlanğıc}{nöqtə}{self.son}{a}"


# ═══════════════════════════════════════════════════════════════════════
#  Generator
# ═══════════════════════════════════════════════════════════════════════

class AlqorGenerator:
    """
    `generator funksiya ... ver x ... son` nəticəsi.

    TƏNBƏLDİR — dəyərlər yalnız istənəndə hesablanır, ona görə sonsuz
    generatorlar işləyir. Daxilində `korutin.Korutin` (sap əsaslı
    korutin) və ya adi Python iteratoru ola bilər.
    """

    __slots__ = ("_mənbə", "_bitdi", "_keş")

    def __init__(self, mənbə):
        self._mənbə = mənbə
        self._bitdi = False
        self._keş: list[Any] | None = None

    # ── İterasiya ─────────────────────────────────────────────────────

    def __iter__(self):
        return self

    def __next__(self) -> Any:
        if self._bitdi:
            raise StopIteration
        try:
            return next(self._mənbə) if not hasattr(self._mənbə, "növbəti") \
                else self._mənbə.növbəti()
        except StopIteration:
            self._bitdi = True
            raise

    # ── Alqor API-si ──────────────────────────────────────────────────

    def növbəti(self) -> Any:
        try:
            return self.__next__()
        except StopIteration:
            raise AlqorXəta("KolleksiyaXətası",
                            "generator bitdi — daha dəyər yoxdur",
                            kod="ALQ-R014")

    def bitdi(self) -> bool:
        return self._bitdi

    def bağla(self) -> None:
        bağla = getattr(self._mənbə, "bağla", None)
        if callable(bağla):
            bağla()
        self._bitdi = True

    def siyahıyaÇevir(self) -> list:
        """DİQQƏT: sonsuz generatorda heç vaxt bitməz."""
        return list(self)

    def ilk(self, say: int) -> list:
        """İlk `say` dəyəri — sonsuz generatorlar üçün təhlükəsiz."""
        nəticə: list[Any] = []
        for dəyər in self:
            if len(nəticə) >= say:
                break
            nəticə.append(dəyər)
        return nəticə

    def __repr__(self) -> str:
        return f"<generator{' (bitdi)' if self._bitdi else ''}>"


# ═══════════════════════════════════════════════════════════════════════
#  Tip adları
# ═══════════════════════════════════════════════════════════════════════

def tip_adı(dəyər: Any) -> str:
    """`tip(x)` funksiyasının nəticəsi."""
    if dəyər is None:
        return "heç"
    if isinstance(dəyər, bool):
        return "məntiq"
    if isinstance(dəyər, int):
        return "tam"
    if isinstance(dəyər, float):
        return "onluq"
    if isinstance(dəyər, str):
        return "mətn"
    if isinstance(dəyər, bytes):
        return "bayt"
    if isinstance(dəyər, list):
        if dəyər:
            iç = {tip_adı(e) for e in dəyər}
            if len(iç) == 1:
                return f"siyahı[{iç.pop()}]"
            return "siyahı[istənilən]"
        return "siyahı"
    if isinstance(dəyər, dict):
        if dəyər:
            a = {tip_adı(k) for k in dəyər}
            d = {tip_adı(v) for v in dəyər.values()}
            if len(a) == 1 and len(d) == 1:
                return f"lüğət[{a.pop()}, {d.pop()}]"
        return "lüğət"
    if isinstance(dəyər, set):
        return "dəst"
    if isinstance(dəyər, tuple):
        return "kortej[" + ", ".join(tip_adı(e) for e in dəyər) + "]"
    if isinstance(dəyər, AlqorDiapazon):
        return "diapazon"
    if isinstance(dəyər, Nümunə):
        return dəyər.sinif.ad
    if isinstance(dəyər, Sinif):
        return f"sinif[{dəyər.ad}]"
    if isinstance(dəyər, SadalamaDəyəri):
        return dəyər.sadalama.ad
    if isinstance(dəyər, Sadalama):
        return f"sadalama[{dəyər.ad}]"
    if isinstance(dəyər, Modul):
        return f"modul[{dəyər.ad}]"
    if isinstance(dəyər, AlqorGenerator):
        return "generator"
    if isinstance(dəyər, Element):
        return "element"
    if type(dəyər).__name__ == "Gələcək":
        return "gələcək"
    if type(dəyər).__name__ == "LəğvNişanı":
        return "ləğvNişanı"
    if isinstance(dəyər, Çağırılan):
        return "funksiya"
    # Kitabxana obyektləri öz tip adını bildirə bilər (bax:
    # `kitabxana.daxili_metod` — `ALQOR_METODLARI` protokolu)
    ad = getattr(type(dəyər), "ALQOR_TİP_ADI", None)
    if ad:
        return ad
    return "istənilən"


# ═══════════════════════════════════════════════════════════════════════
#  Mətnə çevirmə — `yaz()` və interpolyasiya üçün
# ═══════════════════════════════════════════════════════════════════════

def mətnə(dəyər: Any, icraçı=None) -> str:
    if dəyər is None:
        return "boş"
    if dəyər is True:
        return "doğru"
    if dəyər is False:
        return "yanlış"
    if isinstance(dəyər, str):
        return dəyər
    if isinstance(dəyər, float):
        if dəyər != dəyər:
            return "ƏdədDeyil"
        if dəyər == float("inf"):
            return "sonsuz"
        if dəyər == float("-inf"):
            return "-sonsuz"
        if dəyər == int(dəyər) and abs(dəyər) < 1e16:
            return f"{dəyər:.1f}"
        return repr(dəyər)
    if isinstance(dəyər, int):
        return str(dəyər)
    if isinstance(dəyər, bytes):
        return "b\"" + dəyər.decode("utf-8", "replace") + "\""
    if isinstance(dəyər, list):
        return "[" + ", ".join(_daxili_mətn(e, icraçı) for e in dəyər) + "]"
    if isinstance(dəyər, tuple):
        if len(dəyər) == 1:
            return "(" + _daxili_mətn(dəyər[0], icraçı) + ",)"
        return "(" + ", ".join(_daxili_mətn(e, icraçı) for e in dəyər) + ")"
    if isinstance(dəyər, set):
        if not dəyər:
            return "dəst()"
        return "{" + ", ".join(_daxili_mətn(e, icraçı) for e in dəyər) + "}"
    if isinstance(dəyər, dict):
        if not dəyər:
            return "{}"
        return "{" + ", ".join(
            f"{_daxili_mətn(a, icraçı)}: {_daxili_mətn(d, icraçı)}"
            for a, d in dəyər.items()) + "}"
    if isinstance(dəyər, Element):
        return dəyər.HTML(icraçı)
    if isinstance(dəyər, Nümunə):
        if icraçı is not None:
            m = dəyər.sinif.metod_tap("mətnƏt")
            if m is not None:
                return mətnə(icraçı.funksiya_çağır(m.bağla(dəyər), [], {}),
                             icraçı)
        sahələr = ", ".join(f"{a}: {_daxili_mətn(d, icraçı)}"
                            for a, d in dəyər.sahələr.items())
        return f"{dəyər.sinif.ad}({sahələr})"
    return str(dəyər)


def _daxili_mətn(dəyər: Any, icraçı=None) -> str:
    """Kolleksiya daxilində mətnlər dırnaqda göstərilir."""
    if isinstance(dəyər, str):
        return '"' + dəyər.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return mətnə(dəyər, icraçı)
