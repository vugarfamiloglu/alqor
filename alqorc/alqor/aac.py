"""
Alqor — AAC (Abstrakt Anlayış Ağacı / abstract syntax tree).

Parserin çıxışı. Hər qovşağın mənbə faylındaki yeri (`yer`) var ki,
interpretator və tip yoxlayıcı dəqiq xəta mesajı verə bilsin.

Adlandırma: qovşaq adları spesifikasiyadaki konstruksiya adları ilə
eynidir — `Şərt`, `NəQədərKi`, `Hər`, `Cəhd` və s.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .token import Yer


# ═══════════════════════════════════════════════════════════════════════
#  Baza
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Qovşaq:
    yer: Yer

    @property
    def adı(self) -> str:
        return type(self).__name__


@dataclass
class İfadə(Qovşaq):
    """Dəyər verən qovşaq."""


@dataclass
class Cümlə(Qovşaq):
    """İcra olunan qovşaq."""


# ═══════════════════════════════════════════════════════════════════════
#  Tip ifadələri
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TipAdı(Qovşaq):
    """`tam`, `mətn`, `İstifadəçi`, `modul.Tip`"""
    yol: list[str]
    arqumentlər: list["TipQovşağı"] = field(default_factory=list)
    ixtiyari: bool = False                 # `T?`

    @property
    def tam_ad(self) -> str:
        return ".".join(self.yol)


@dataclass
class TipBirləşmə(Qovşaq):
    """`tam | mətn | boş`"""
    variantlar: list["TipQovşağı"]


@dataclass
class TipKortej(Qovşaq):
    """`kortej[tam, mətn]` qısa forması: `(tam, mətn)`"""
    elementlər: list["TipQovşağı"]
    ixtiyari: bool = False


@dataclass
class TipFunksiya(Qovşaq):
    """`funksiyaTipi(tam, tam) -> tam`"""
    parametrlər: list["TipQovşağı"]
    qaytarma: "TipQovşağı | None" = None
    ixtiyari: bool = False


TipQovşağı = TipAdı | TipBirləşmə | TipKortej | TipFunksiya


# ═══════════════════════════════════════════════════════════════════════
#  İfadələr — literallar
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Literal(İfadə):
    """`42`, `3.14`, `"salam"`, `` `ə` ``, `doğru`, `boş`"""
    dəyər: Any
    növ: str = ""          # "tam" | "onluq" | "mətn" | "simvol" |
                           # "bayt" | "məntiq" | "boş"


@dataclass
class ŞablonMətn(İfadə):
    """`"Salam, {ad}!"` — parçalardan qurulur."""
    parçalar: list["MətnHissəsi | KodHissəsi"]


@dataclass
class MətnHissəsi:
    dəyər: str


@dataclass
class KodHissəsi:
    ifadə: İfadə
    format: str | None = None


@dataclass
class Ad(İfadə):
    """İdentifikator istinadı."""
    ad: str


@dataclass
class Özü(İfadə):
    pass


@dataclass
class Üst(İfadə):
    pass


# ═══════════════════════════════════════════════════════════════════════
#  İfadələr — operatorlar
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class İkili(İfadə):
    """`a + b`, `x və y`, `a == b`"""
    sol: İfadə
    op: str
    sağ: İfadə


@dataclass
class TəkOperand(İfadə):
    """`-x`, `deyil x`, `~x`"""
    op: str
    operand: İfadə


@dataclass
class Mənimsətmə(İfadə):
    """`a = 1`, `a += 1`, `a, b = b, a`"""
    hədəflər: list[İfadə]
    op: str
    dəyərlər: list[İfadə]


@dataclass
class Artırma(Cümlə):
    """`i++`, `i--` — yalnız müstəqil cümlə kimi."""
    hədəf: İfadə
    op: str


@dataclass
class Çevirmə(İfadə):
    """`x kimi tam`, `x kimi? tam`"""
    ifadə: İfadə
    tip: TipQovşağı
    təhlükəsiz: bool = False


@dataclass
class TipYoxlama(İfadə):
    """`x tipidir mətn`"""
    ifadə: İfadə
    tip: TipQovşağı


@dataclass
class Üzvlük(İfadə):
    """`x içindədir siyahı`"""
    element: İfadə
    kolleksiya: İfadə


@dataclass
class BoşYoxlama(İfadə):
    """`x boşdur`, `x boş deyil`"""
    ifadə: İfadə
    inkar: bool = False        # True → `boş deyil`


@dataclass
class Boru(İfadə):
    """`dəyər |> funksiya`"""
    dəyər: İfadə
    funksiya: İfadə


@dataclass
class Diapazon(İfadə):
    """`1..5`, `1..<5`, `1..10 addım 2`"""
    başlanğıc: İfadə
    son: İfadə
    addım: İfadə | None = None
    xaric: bool = False        # `..<`


# ═══════════════════════════════════════════════════════════════════════
#  İfadələr — müraciət
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Arqument:
    dəyər: İfadə
    ad: str | None = None      # adlı arqument
    yayma: bool = False        # `...siyahı`
    adlı_yayma: bool = False   # `**lüğət`


@dataclass
class Çağırış(İfadə):
    funksiya: İfadə
    arqumentlər: list[Arqument] = field(default_factory=list)


@dataclass
class Üzv(İfadə):
    """`obyekt.ad`, `obyekt?.ad`, `kortej.0`"""
    obyekt: İfadə
    ad: str
    təhlükəsiz: bool = False


@dataclass
class İndeks(İfadə):
    """`siyahı[0]`, `lüğət["açar"]`"""
    obyekt: İfadə
    indeks: İfadə


@dataclass
class Dilim(İfadə):
    """`siyahı[1..3]`, `siyahı[1..]`, `siyahı[..2]`"""
    obyekt: İfadə
    başlanğıc: İfadə | None
    son: İfadə | None
    xaric: bool = False


@dataclass
class MəcburiAçma(İfadə):
    """`x!` — ixtiyari dəyəri məcburi açır."""
    ifadə: İfadə


@dataclass
class Yayma(İfadə):
    """`nəticə?` — `Nəticə` tipində xətanı yuxarı ötürür."""
    ifadə: İfadə


@dataclass
class Yeni(İfadə):
    """`yeni Sinif(...)`, `yeni Nöqtə.qütb(...)`"""
    tip: TipQovşağı
    qurucu: str | None = None
    arqumentlər: list[Arqument] = field(default_factory=list)


@dataclass
class Gözlə(İfadə):
    ifadə: İfadə


# ═══════════════════════════════════════════════════════════════════════
#  İfadələr — kolleksiyalar
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SiyahıLiteralı(İfadə):
    elementlər: list[İfadə]
    yaymalar: list[bool] = field(default_factory=list)


@dataclass
class LüğətLiteralı(İfadə):
    açarlar: list[İfadə | None]          # None → yayma (`...digər`)
    dəyərlər: list[İfadə]


@dataclass
class DəstLiteralı(İfadə):
    elementlər: list[İfadə]


@dataclass
class KortejLiteralı(İfadə):
    elementlər: list[İfadə]


@dataclass
class SorğuBəndi(Qovşaq):
    """
    Sorğu bəndi (spes. § 4.13).

    növ: "hər" | "harada" | "dəyişən" | "sırala" | "qrupla" | "seç" |
         "ilk" | "atla"
    """
    növ: str
    bağlama: "Bağlama | None" = None
    ifadə: İfadə | None = None
    açarlar: list[tuple[İfadə, bool]] = field(default_factory=list)
    fərqli: bool = False


@dataclass
class Sorğu(İfadə):
    """`sorğu hər x üçün s içində  harada …  sırala …  seç …  son`"""
    bəndlər: list[SorğuBəndi]


@dataclass
class Qurma(İfadə):
    """
    `[x * x üçün x içində 1..10 əgər x % 2 == 0]`

    növ: "siyahı" | "lüğət" | "dəst" | "generator"
    """
    növ: str
    ifadə: İfadə
    dəyər_ifadəsi: İfadə | None       # lüğət üçün dəyər hissəsi
    bağlama: "Bağlama"
    mənbə: İfadə
    şərt: İfadə | None = None


# ═══════════════════════════════════════════════════════════════════════
#  İfadələr — blok şəklində
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ŞərtIfadəsi(İfadə):
    """`əgər a onda 1 yoxsa 2 son` — dəyər verən forma."""
    budaqlar: list[tuple[İfadə, İfadə]]
    yoxsa: İfadə | None = None


@dataclass
class BlokIfadəsi(İfadə):
    """`blok ... ver x ... son`"""
    gövdə: list[Cümlə]


@dataclass
class Lambda(İfadə):
    """`(x) => x * 2`, `funksiya(x) qaytar x*2 son`"""
    parametrlər: list["Parametr"]
    gövdə: list[Cümlə] | İfadə
    asinxron: bool = False
    generator: bool = False
    tutmalar: list[str] = field(default_factory=list)
    qaytarma_tipi: TipQovşağı | None = None


# ═══════════════════════════════════════════════════════════════════════
#  İnterfeys sintaksisi (JSX)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class JSXAtribut:
    """`sinif="qutu"`, `klik={özü.bas}`, `aktiv`, `{...xassələr}`"""
    ad: str
    dəyər: "İfadə | None" = None        # None → məntiqi `doğru`
    yayma: bool = False                 # `{...obyekt}`


@dataclass
class JSXMətn:
    """Element daxilindəki xam mətn."""
    dəyər: str


@dataclass
class JSXElement(İfadə):
    """`<div sinif="a">{mətn}</div>`, `<Sayğac />`"""
    ad: str                             # "div" | "Sayğac" | "nax.Düymə"
    atributlar: list[JSXAtribut] = field(default_factory=list)
    uşaqlar: list["İfadə | JSXMətn"] = field(default_factory=list)

    @property
    def komponentdir(self) -> bool:
        """Böyük hərflə başlayan ad komponent istinadıdır."""
        ilk = self.ad.split(".")[0][:1]
        return ilk != "" and ilk == ilk.upper() and ilk.isalpha()


@dataclass
class JSXParça(İfadə):
    """`<>...</>` — sarğısız qrup."""
    uşaqlar: list["İfadə | JSXMətn"] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
#  Bağlamalar (dağıtma)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Bağlama(Qovşaq):
    """
    Dəyişən elanının sol tərəfi.

    növ: "ad" | "atma" | "qalan" | "kortej" | "obyekt"
    """
    növ: str
    ad: str | None = None
    alt: list["Bağlama"] = field(default_factory=list)
    sahələr: list[tuple[str, "Bağlama | None"]] = field(default_factory=list)
    tip: TipQovşağı | None = None


# ═══════════════════════════════════════════════════════════════════════
#  Parametrlər
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Parametr(Qovşaq):
    ad: str
    tip: TipQovşağı | None = None
    standart: İfadə | None = None
    variadic: bool = False          # `...ədədlər`
    adlı_variadic: bool = False     # `**xassələr`
    yalnız_adlı: bool = False       # `*`-dan sonra
    xassə_görünüşü: str | None = None   # qısa qurucu: `açıq xassə ad`


# ═══════════════════════════════════════════════════════════════════════
#  Cümlələr — elanlar
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Annotasiya(Qovşaq):
    ad: str
    arqumentlər: list[Arqument] = field(default_factory=list)


@dataclass
class DəyişənElanı(Cümlə):
    """`dəyişən a = 1`, `sabit B: tam = 2`, `dəyişməz C = []`"""
    növ: str                        # "dəyişən" | "sabit" | "dəyişməz"
    bağlamalar: list[Bağlama]
    dəyərlər: list[İfadə] = field(default_factory=list)
    görünüş: str | None = None
    ixrac: bool = False


@dataclass
class FunksiyaElanı(Cümlə):
    ad: str
    parametrlər: list[Parametr]
    gövdə: list[Cümlə]
    qaytarma_tipi: TipQovşağı | None = None
    asinxron: bool = False
    generator: bool = False
    generiklər: list[tuple[str, TipQovşağı | None]] = field(
        default_factory=list)
    annotasiyalar: list[Annotasiya] = field(default_factory=list)
    görünüş: str | None = None
    ixrac: bool = False
    sənəd: str | None = None


@dataclass
class XassəElanı(Cümlə):
    ad: str
    tip: TipQovşağı | None = None
    standart: İfadə | None = None
    görünüş: str | None = None
    statik: bool = False
    sabit: bool = False
    tənbəl: bool = False
    oxu_gövdəsi: list[Cümlə] | None = None
    yaz_gövdəsi: list[Cümlə] | None = None
    yaz_parametri: str | None = None
    annotasiyalar: list[Annotasiya] = field(default_factory=list)
    sənəd: str | None = None


@dataclass
class MetodElanı(Cümlə):
    ad: str
    parametrlər: list[Parametr]
    gövdə: list[Cümlə] | None          # None → mücərrəd
    qaytarma_tipi: TipQovşağı | None = None
    görünüş: str | None = None
    statik: bool = False
    mücərrəd: bool = False
    son: bool = False
    əvəz: bool = False
    asinxron: bool = False
    generator: bool = False
    generiklər: list[tuple[str, TipQovşağı | None]] = field(
        default_factory=list)
    annotasiyalar: list[Annotasiya] = field(default_factory=list)
    sənəd: str | None = None


@dataclass
class QurucuElanı(Cümlə):
    parametrlər: list[Parametr]
    gövdə: list[Cümlə]
    ad: str | None = None              # adlı qurucu
    görünüş: str | None = None


@dataclass
class DağıdıcıElanı(Cümlə):
    gövdə: list[Cümlə]


@dataclass
class SinifElanı(Cümlə):
    ad: str
    üzvlər: list[Cümlə]
    baza: TipQovşağı | None = None
    interfeyslər: list[TipQovşağı] = field(default_factory=list)
    qarışıqlar: list[TipQovşağı] = field(default_factory=list)
    generiklər: list[tuple[str, TipQovşağı | None]] = field(
        default_factory=list)
    mücərrəd: bool = False
    son: bool = False
    görünüş: str | None = None
    ixrac: bool = False
    annotasiyalar: list[Annotasiya] = field(default_factory=list)
    sənəd: str | None = None
    quruluş: str = "sinif"             # "sinif" | "struktur" | "obyekt"


@dataclass
class InterfeysElanı(Cümlə):
    ad: str
    üzvlər: list[Cümlə]
    bazalar: list[TipQovşağı] = field(default_factory=list)
    generiklər: list[tuple[str, TipQovşağı | None]] = field(
        default_factory=list)
    görünüş: str | None = None
    ixrac: bool = False
    sənəd: str | None = None


@dataclass
class SadalamaVariantı(Qovşaq):
    ad: str
    dəyər: İfadə | None = None
    arqumentlər: list[Arqument] = field(default_factory=list)
    parametrlər: list[Parametr] = field(default_factory=list)


@dataclass
class SadalamaElanı(Cümlə):
    ad: str
    variantlar: list[SadalamaVariantı]
    üzvlər: list[Cümlə] = field(default_factory=list)
    əsas_tip: TipQovşağı | None = None
    generiklər: list[tuple[str, TipQovşağı | None]] = field(
        default_factory=list)
    görünüş: str | None = None
    ixrac: bool = False
    sənəd: str | None = None


@dataclass
class QarışıqElanı(Cümlə):
    ad: str
    üzvlər: list[Cümlə]
    görünüş: str | None = None
    ixrac: bool = False


@dataclass
class Genişlətmə(Cümlə):
    """`genişlət mətn ... son`"""
    tip: TipQovşağı
    üzvlər: list[Cümlə]


@dataclass
class TipAliası(Cümlə):
    ad: str
    tip: TipQovşağı
    generiklər: list[tuple[str, TipQovşağı | None]] = field(
        default_factory=list)
    görünüş: str | None = None
    ixrac: bool = False


@dataclass
class ModulElanı(Cümlə):
    ad: str
    gövdə: list[Cümlə]
    görünüş: str | None = None
    ixrac: bool = False
    # `@sınaqQrupu("…") modul …` — sınaq işlədicisi oxuyur
    annotasiyalar: list[Annotasiya] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
#  Cümlələr — idarəetmə
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class İfadəCümləsi(Cümlə):
    ifadə: İfadə


@dataclass
class Şərt(Cümlə):
    """`əgər ... onda ... yoxsa əgər ... yoxsa ... son`"""
    budaqlar: list[tuple[İfadə, list[Cümlə]]]
    yoxsa: list[Cümlə] | None = None


@dataclass
class Varsa(Cümlə):
    """`varsa i = tap() onda ... yoxsa ... son`"""
    bağlamalar: list[tuple[Bağlama | None, İfadə]]
    gövdə: list[Cümlə]
    yoxsa: list[Cümlə] | None = None


@dataclass
class Yoxdursa(Cümlə):
    """`yoxdursa i = tap() onda qaytar son`"""
    bağlamalar: list[tuple[Bağlama | None, İfadə]]
    gövdə: list[Cümlə]


@dataclass
class Hal(Qovşaq):
    naxışlar: list["Naxış"]
    gövdə: list[Cümlə]
    mühafizə: İfadə | None = None      # `hal x əgər x > 5`
    keç: bool = False


@dataclass
class Seç(Cümlə):
    ifadə: İfadə | None               # None → şərtli `seç`
    hallar: list[Hal]
    digər: list[Cümlə] | None = None
    tipə_görə: bool = False            # `seç tipi x`


@dataclass
class Naxış(Qovşaq):
    """
    növ: "literal" | "ad" | "atma" | "tip" | "diapazon"
         | "kortej" | "siyahı" | "obyekt"
         | "şərt" (ifadəsiz `seç`-də: `hal yaş < 13`)
    """
    növ: str
    dəyər: Any = None
    tip: TipQovşağı | None = None
    alt: list["Naxış"] = field(default_factory=list)
    sahələr: list[tuple[str, "Naxış | None"]] = field(default_factory=list)
    qalan: str | None = None
    diapazon_son: Any = None
    diapazon_xaric: bool = False


@dataclass
class NəQədərKi(Cümlə):
    şərt: İfadə
    gövdə: list[Cümlə]
    etiket: str | None = None


@dataclass
class Həmişə(Cümlə):
    gövdə: list[Cümlə]
    etiket: str | None = None


@dataclass
class Təkrarla(Cümlə):
    """`təkrarla 5 dəfə`, `təkrarla i, 5 dəfə`"""
    say: İfadə
    gövdə: list[Cümlə]
    sayğac: str | None = None
    etiket: str | None = None


@dataclass
class TəkrarlaNəQədər(Cümlə):
    """`təkrarla ... nə qədər ki şərt` — şərti sonda yoxlayan dövr."""
    gövdə: list[Cümlə]
    şərt: İfadə
    etiket: str | None = None


@dataclass
class Hər(Cümlə):
    """`hər i, x üçün siyahı addım 2 içində əgər şərt ... yoxsa ... son`"""
    bağlamalar: list[Bağlama]
    mənbə: İfadə
    gövdə: list[Cümlə]
    addım: İfadə | None = None
    şərt: İfadə | None = None
    yoxsa: list[Cümlə] | None = None
    asinxron: bool = False             # `içində gözlə`
    etiket: str | None = None


@dataclass
class Dayan(Cümlə):
    etiket: str | None = None


@dataclass
class DavamEt(Cümlə):
    etiket: str | None = None


@dataclass
class Qaytar(Cümlə):
    dəyərlər: list[İfadə] = field(default_factory=list)


@dataclass
class Ver(Cümlə):
    """`ver x` — generatorda dəyər verir, blokda bloku bitirir."""
    dəyər: İfadə | None = None


@dataclass
class At(Cümlə):
    ifadə: İfadə | None = None         # None → tutulmuş xətanı yenidən at


@dataclass
class Tutma(Qovşaq):
    gövdə: list[Cümlə]
    ad: str | None = None
    tiplər: list[TipQovşağı] = field(default_factory=list)
    mühafizə: İfadə | None = None


@dataclass
class Cəhd(Cümlə):
    gövdə: list[Cümlə]
    tutmalar: list[Tutma] = field(default_factory=list)
    nəhayət: list[Cümlə] | None = None


@dataclass
class İddia(Cümlə):
    şərt: İfadə
    mesaj: İfadə | None = None


@dataclass
class Təmin(Cümlə):
    şərt: İfadə
    gövdə: list[Cümlə]


@dataclass
class Gecikdir(Cümlə):
    ifadə: İfadə


@dataclass
class İstifadə(Cümlə):
    bağlamalar: list[tuple[str, İfadə]]
    gövdə: list[Cümlə]


@dataclass
class Keç(Cümlə):
    pass


@dataclass
class DayanNöqtəsi(Cümlə):
    pass


@dataclass
class Global(Cümlə):
    adlar: list[str]


# ═══════════════════════════════════════════════════════════════════════
#  Cümlələr — modullar
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class İdxalElementi:
    ad: str
    ləqəb: str | None = None


@dataclass
class İdxal(Cümlə):
    """
    `gətir riyaziyyat`
    `gətir riyaziyyat kimi r`
    `gətir riyaziyyat.{kök, Pİ}`
    `gətir riyaziyyat.*`
    `gətir "./yerli.alq" kimi y`
    `gətir python:numpy kimi np`       (Python kitabxanası, § 8.14)
    """
    yol: list[str]
    mətn_yolu: str | None = None       # `"./fayl.alq"` forması
    ləqəb: str | None = None
    elementlər: list[İdxalElementi] = field(default_factory=list)
    hamısı: bool = False               # `.*`
    python: bool = False               # `python:` prefiksi


@dataclass
class İxracSiyahısı(Cümlə):
    """`ixrac et {a, b}`"""
    elementlər: list[İdxalElementi]


@dataclass
class Başlanğıc(Cümlə):
    gövdə: list[Cümlə]


@dataclass
class Bitiş(Cümlə):
    gövdə: list[Cümlə]


# ═══════════════════════════════════════════════════════════════════════
#  Proqram
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Proqram(Qovşaq):
    gövdə: list[Cümlə]
    modul_sənədi: str | None = None
    direktivlər: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
#  Ağacın çapı — sazlama üçün
# ═══════════════════════════════════════════════════════════════════════

def göstər(q: Any, girinti: int = 0, açar: str | None = None) -> str:
    """AAC-ni oxunaqlı ağac kimi formatlayır."""
    boş = "  " * girinti
    ön = f"{açar}: " if açar else ""

    if isinstance(q, (Qovşaq, Arqument, MətnHissəsi, KodHissəsi,
                      İdxalElementi)):
        sahələr = []
        for ad, dəyər in vars(q).items():
            if ad == "yer":
                continue
            if dəyər is None or dəyər == [] or dəyər is False:
                continue
            sahələr.append((ad, dəyər))

        başlıq = type(q).__name__
        sadələr = [(a, d) for a, d in sahələr
                   if isinstance(d, (str, int, float, bool, bytes))]
        mürəkkəblər = [(a, d) for a, d in sahələr
                       if not isinstance(d, (str, int, float, bool, bytes))]

        xülasə = " ".join(f"{a}={d!r}" for a, d in sadələr)
        sətirlər = [f"{boş}{ön}{başlıq}" + (f"  {xülasə}" if xülasə else "")]
        for a, d in mürəkkəblər:
            sətirlər.append(göstər(d, girinti + 1, a))
        return "\n".join(sətirlər)

    if isinstance(q, list):
        if not q:
            return f"{boş}{ön}[]"
        sətirlər = [f"{boş}{ön}["]
        for element in q:
            sətirlər.append(göstər(element, girinti + 1))
        sətirlər.append(f"{boş}]")
        return "\n".join(sətirlər)

    if isinstance(q, tuple):
        sətirlər = [f"{boş}{ön}("]
        for element in q:
            sətirlər.append(göstər(element, girinti + 1))
        sətirlər.append(f"{boş})")
        return "\n".join(sətirlər)

    return f"{boş}{ön}{q!r}"
