"""
Alqor — makrolar (spes. § 5.12).

Makro TOKEN səviyyəsində açılır: çağırış (`ad!(…)`) makro gövdəsinin
tokenləri ilə əvəz olunur, parametrlər arqumentlərin tokenləri ilə
dəyişdirilir və nəticə adi kod kimi təhlil olunur. Ona görə açılmış kod
bütün icraçılarda (Python, Rust, JS) eynidir və heç bir icraçı makronu
ayrıca tanımalı deyil.

Gigiyena: makro gövdəsində elan olunan adlar (`dəyişən`, `hər`, `tut`,
iç `funksiya`) hər açılışda `ad$mN` formasına salınır — çağıranın eyni
adlı dəyişənləri ilə toqquşmur. `$` istifadəçi kodunda yazıla bilməz.

Bu modulun məntiqi `alqor-rs/src/makro.rs`-də bayt-bayt təkrarlanır:
iki parser eyni AAC qurmalıdır.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .token import KodParçası, Növ, Token, Yer

# Bir faylda açılışların həddi — özünü çağıran makrolara qarşı
AÇILIŞ_HƏDDİ = 10000

ELAN_SÖZLƏRİ = ("dəyişən", "sabit", "dəyişməz")


@dataclass
class Makro:
    ad: str
    parametrlər: list[str]
    blok: str | None              # `iş: blok` — blok parametrinin adı
    ifadədir: bool                # `makro ad(x) = ifadə`
    tokenlər: list[Token]
    yerlilər: frozenset[str]
    yer: Yer


@dataclass
class MakroVəziyyəti:
    """Bir faylın (və onun interpolyasiya alt-parserlərinin) makroları."""
    makrolar: dict[str, Makro] = field(default_factory=dict)
    açılış: int = 0
    # `gətir "fayl.alq"` ilə oxunmuş fayllar (dövri idxala qarşı)
    oxunmuş: set[str] = field(default_factory=set)


def _sətir_sonudur(t: Token | None) -> bool:
    return t is None or t.növ in (Növ.SETIR_SONU, Növ.FAYL_SONU)


def yerli_adlar(tokenlər: list[Token]) -> frozenset[str]:
    """Gövdədə elan olunan adlar: `dəyişən a, b`, `hər x üçün`, `tut (x)`,
    `funksiya f`."""
    n = len(tokenlər)
    adlar: set[str] = set()
    for i, t in enumerate(tokenlər):
        if t.növ is not Növ.ACAR:
            continue
        if t.dəyər in ELAN_SÖZLƏRİ:
            j = i + 1
            while j < n and not _sətir_sonudur(tokenlər[j]) \
                    and not tokenlər[j].opdur("="):
                tj, əv = tokenlər[j], tokenlər[j - 1]
                if tj.növ is Növ.AD and (j == i + 1
                                         or əv.opdur(",", "(", "[")):
                    adlar.add(tj.dəyər)
                j += 1
        elif t.dəyər == "hər":
            j = i + 1
            while j < n and not _sətir_sonudur(tokenlər[j]) \
                    and not tokenlər[j].acardır("üçün"):
                tj, əv = tokenlər[j], tokenlər[j - 1]
                if tj.növ is Növ.AD and (j == i + 1 or əv.opdur(",", "(")):
                    adlar.add(tj.dəyər)
                j += 1
        elif t.dəyər == "tut":
            j = i + 1
            if j < n and tokenlər[j].opdur("("):
                j += 1
            if j < n and tokenlər[j].növ is Növ.AD:
                adlar.add(tokenlər[j].dəyər)
        elif t.dəyər == "funksiya":
            if i + 1 < n and tokenlər[i + 1].növ is Növ.AD:
                adlar.add(tokenlər[i + 1].dəyər)
    return frozenset(adlar)


class MakroXətası(Exception):
    def __init__(self, kod: str, mesaj: str, yer: Yer, qeyd: str = "",
                 *köməklər: str):
        super().__init__(mesaj)
        self.kod, self.mesaj, self.yer = kod, mesaj, yer
        self.qeyd, self.köməklər = qeyd, köməklər


def əvəzlə(m: Makro, tokenlər: list[Token], arqumentlər: dict[str, list[Token]],
           adlar: dict[str, str], blok: list[Token] | None) -> list[Token]:
    """Gövdə tokenlərində parametrləri və yerli adları dəyişdirir."""
    n: list[Token] = []
    say = len(tokenlər)
    for k, t in enumerate(tokenlər):
        əv = tokenlər[k - 1] if k > 0 else None
        nö = tokenlər[k + 1] if k + 1 < say else None
        if t.növ is Növ.AD and not (əv is not None and əv.opdur(".", "?.")):
            # Adlı arqumentin etiketi: `f(ad: …)`
            etiket = (nö is not None and nö.opdur(":") and əv is not None
                      and əv.opdur("(", ","))
            if m.blok is not None and t.dəyər == m.blok:
                if not (_sətir_sonudur(əv) and _sətir_sonudur(nö)):
                    raise MakroXətası(
                        "ALQ-P035", "Blok parametri yalnız ayrıca sətirdə "
                        "işlənə bilər", t.yer,
                        f"`{t.dəyər}` cümlə kimi yazılmalıdır",
                        f"`{t.dəyər}` sətrində başqa heç nə olmasın")
                n.extend(blok or [])
                continue
            if t.dəyər in arqumentlər and not etiket:
                arq = arqumentlər[t.dəyər]
                if len(arq) == 1:
                    n.append(arq[0])
                else:
                    n.append(Token(Növ.OP, "(", t.yer, "("))
                    n.extend(arq)
                    n.append(Token(Növ.OP, ")", t.yer, ")"))
                continue
            if t.dəyər in adlar and not etiket:
                n.append(replace(t, dəyər=adlar[t.dəyər]))
                continue
        if t.növ is Növ.METN and t.parçalar and any(
                isinstance(p, KodParçası) for p in t.parçalar):
            parçalar = [KodParçası(əvəzlə(m, list(p.tokenlər), arqumentlər,
                                          adlar, None), p.format)
                        if isinstance(p, KodParçası) else p
                        for p in t.parçalar]
            n.append(replace(t, parçalar=parçalar))
            continue
        n.append(t)
    return n


def aç(m: Makro, arqumentlər: list[list[Token]], blok: list[Token] | None,
       yer: Yer, nömrə: int) -> list[Token]:
    """Bir çağırışın açılmış tokenləri."""
    if len(arqumentlər) != len(m.parametrlər):
        raise MakroXətası(
            "ALQ-P033", "Makro arqumentlərinin sayı uyğun deyil", yer,
            f"`{m.ad}!` {len(m.parametrlər)} arqument gözləyir, "
            f"{len(arqumentlər)} verilib")
    adlar = {a: f"{a}$m{nömrə}" for a in sorted(m.yerlilər)
             if a not in m.parametrlər and a != m.blok}
    gövdə = əvəzlə(m, m.tokenlər, dict(zip(m.parametrlər, arqumentlər)),
                   adlar, blok)
    if m.ifadədir:
        return ([Token(Növ.OP, "(", yer, "(")] + gövdə
                + [Token(Növ.OP, ")", yer, ")")])
    # Cümlə makrosu: baş və sondakı boş sətirlər atılır — açılış çağırışın
    # yerindəki cümlənin özü olur
    b, s = 0, len(gövdə)
    while b < s and gövdə[b].növ is Növ.SETIR_SONU:
        b += 1
    while s > b and gövdə[s - 1].növ is Növ.SETIR_SONU:
        s -= 1
    if b == s:
        return [Token(Növ.ACAR, "keç", yer, "keç")]
    return gövdə[b:s]
