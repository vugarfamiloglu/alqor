"""
Alqor Studio — mənbə mətninin quruluş təhlili.

Redaktordakı kod çox vaxt YARIMÇIQDIR: istifadəçi yazır, fayl hələ
ayrılmır. Ona görə Studio-nun "ağıllı" əməliyyatları (vidjet skeleti,
ASCII çevrilməsi) parserdən asılı olmamalıdır. Bu modul mətni sətir
və girinti səviyyəsində oxuyur:

  • `xəritə(mətn)`        hər simvol üçün: kod / mətn literalı / şərh
  • `komponentləri_tap()` `komponent` blokları, üzvləri, `göstər()`
  • `vidjet_çağırışları()` `vidjet.ad(...)` çağırışlarının yerləri

Girinti qaydası: blokun `son`-u onu açan sətirlə eyni girintidədir.
Studio özü avtomatik girinti verdiyi üçün bu qayda praktikada həmişə
ödənir, parser isə ehtiyat yoxlama kimi sonradan işləyir.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════
#  Simvol xəritəsi — kod / mətn / şərh
# ═══════════════════════════════════════════════════════════════════════

KOD = 0
MƏTN = 1
ŞƏRH = 2


def _ad_simvoludur(c: str) -> bool:
    return c.isalnum() or c == "_"


def xəritə(m: str) -> bytearray:
    """
    Hər simvolun növü: `KOD`, `MƏTN` (literal, interpolyasiya daxil)
    və ya `ŞƏRH`. Bağlanmamış literal sətrin sonunda bitir — yazılma
    anında qalan bütün fayl "mətn" sayılmasın.
    """
    n = len(m)
    x = bytearray(n)
    i = 0
    while i < n:
        c = m[i]
        if c == "/" and m.startswith("//", i):
            j = m.find("\n", i)
            j = n if j < 0 else j
            x[i:j] = bytes([ŞƏRH]) * (j - i)
            i = j
            continue
        if c == "/" and m.startswith("/*", i):
            j = _blok_şərhin_sonu(m, i)
            x[i:j] = bytes([ŞƏRH]) * (j - i)
            i = j
            continue
        if c == '"' or (c in "xb" and m.startswith('"', i + 1)
                        and (i == 0 or not _ad_simvoludur(m[i - 1]))):
            j = mətnin_sonu(m, i)
            x[i:j] = bytes([MƏTN]) * (j - i)
            i = j
            continue
        if c == "`":
            j = m.find("`", i + 1)
            sətir_sonu = m.find("\n", i)
            if j < 0 or (0 <= sətir_sonu < j):
                j = i
            x[i:j + 1] = bytes([MƏTN]) * (j + 1 - i)
            i = j + 1
            continue
        i += 1
    return x


def _blok_şərhin_sonu(m: str, i: int) -> int:
    """`/* … */` — iç-içə şərhlər dəstəklənir."""
    dərinlik = 0
    n = len(m)
    while i < n:
        if m.startswith("/*", i):
            dərinlik += 1
            i += 2
        elif m.startswith("*/", i):
            dərinlik -= 1
            i += 2
            if dərinlik == 0:
                return i
        else:
            i += 1
    return n


def mətnin_sonu(m: str, i: int) -> int:
    """
    `i`-də başlayan mətn literalının sonu (daxil deyil).
    Formalar: `"…"`, `\"\"\"…\"\"\"`, `x"…"` (xam), `b"…"` (bayt).
    """
    n = len(m)
    xam = m[i] == "x"
    if m[i] in "xb":
        i += 1
    üçlü = m.startswith('"""', i)
    i += 3 if üçlü else 1
    while i < n:
        c = m[i]
        if üçlü and m.startswith('"""', i):
            return i + 3
        if not üçlü and c == '"':
            return i + 1
        if not üçlü and c == "\n":
            return i                    # bağlanmamış — sətirdə bitir
        if not xam and c == "\\":
            i += 2
            continue
        if not xam and c == "{":
            i = _interpolyasiya_sonu(m, i + 1)
            continue
        i += 1
    return n


def _interpolyasiya_sonu(m: str, i: int) -> int:
    """`{` daxilindəki kodun sonu — `}`-dan sonrakı indeks."""
    n = len(m)
    dərinlik = 1
    while i < n:
        c = m[i]
        if c == '"':
            i = mətnin_sonu(m, i)
            continue
        if c == "\n":
            return i
        if c == "{":
            dərinlik += 1
        elif c == "}":
            dərinlik -= 1
            if dərinlik == 0:
                return i + 1
        i += 1
    return n


# ═══════════════════════════════════════════════════════════════════════
#  Sətirlər
# ═══════════════════════════════════════════════════════════════════════

def girinti(sətir: str) -> int:
    return len(sətir) - len(sətir.lstrip(" \t"))


def boşdur(sətir: str) -> bool:
    return not sətir.strip()


class Mətn:
    """Mətn + xəritə + sətir başlanğıcları — bir dəfə hesablanır."""

    def __init__(self, mətn: str):
        self.mətn = mətn
        self.x = xəritə(mətn)
        self.sətirlər = mətn.split("\n")
        self.başlar: list[int] = []
        yer = 0
        for s in self.sətirlər:
            self.başlar.append(yer)
            yer += len(s) + 1

    def sətir_nömrəsi(self, mövqe: int) -> int:
        """Simvol indeksi → sətir indeksi (0-dan)."""
        from bisect import bisect_right
        return max(0, bisect_right(self.başlar, mövqe) - 1)

    def kod_sətiridir(self, i: int) -> bool:
        """Sətrin ilk dolu simvolu koddur (şərh və ya literal deyil)."""
        s = self.sətirlər[i]
        g = girinti(s)
        if g >= len(s):
            return False
        return self.x[self.başlar[i] + g] == KOD

    def şərh_sətiridir(self, i: int) -> bool:
        s = self.sətirlər[i]
        g = girinti(s)
        if g >= len(s):
            return False
        return self.x[self.başlar[i] + g] == ŞƏRH

    def kod_hissəsi(self, i: int) -> str:
        """Sətrin yalnız kod simvolları (literal və şərh boşluqla)."""
        b = self.başlar[i]
        s = self.sətirlər[i]
        return "".join(c if self.x[b + j] == KOD else " "
                       for j, c in enumerate(s))

    def ilk_söz(self, i: int) -> str:
        if not self.kod_sətiridir(i):
            return ""
        a = _SÖZ.match(self.sətirlər[i].lstrip(" \t"))
        return a.group(0) if a else ""


_SÖZ = re.compile(r"[^\W\d]\w*")


# ═══════════════════════════════════════════════════════════════════════
#  Komponentlər
# ═══════════════════════════════════════════════════════════════════════

_GÖRÜNÜŞ = r"(?:(?:açıq|gizli|qorunan|ixrac|ixrac\s+et)\s+)*"
_KOMPONENT = re.compile(r"^\s*" + _GÖRÜNÜŞ + r"komponent\s+([^\W\d]\w*)")
_SİNİF_ADI = re.compile(
    r"^\s*" + _GÖRÜNÜŞ + r"(?:mücərrəd\s+|son\s+)?"
    r"(?:sinif|struktur|komponent|mağaza|interfeys|sadalama|obyekt)"
    r"\s+([^\W\d]\w*)")

_DƏYİŞDİRİCİ = (r"(?:(?:açıq|gizli|qorunan|statik|mücərrəd|son|tənbəl|"
                r"asinxron|generator|sabit|əvəz\s+et)\s+)*")
_ÜZV = re.compile(
    r"^" + _DƏYİŞDİRİCİ +
    r"(vəziyyət|hesablanan|hadisə|metod|əməl|xassə|göstər|qurucu|"
    r"silinsin)\b\s*([^\W\d]\w*)?")
_XASSƏ_PARAMETRİ = re.compile(r"\bxassə\s+([^\W\d]\w*)")


@dataclass
class Üzv:
    növ: str                      # vəziyyət | metod | göstər | ...
    ad: str
    baş: int                      # sətir indeksi
    son: int                      # son sətir indeksi (daxil)
    adlar: list[str] = field(default_factory=list)


@dataclass
class Komponent:
    ad: str
    baş: int                      # `komponent` sətri
    son: int | None               # `son` sətri (bağlanmayıbsa None)
    girinti: int
    üzv_girintisi: int
    üzvlər: list[Üzv] = field(default_factory=list)

    @property
    def gövdə_sonu(self) -> int:
        """Gövdənin bitdiyi sətir (daxil deyil)."""
        return self.son if self.son is not None else -1

    def üzv(self, növ: str) -> list[Üzv]:
        return [u for u in self.üzvlər if u.növ == növ]

    def göstər(self) -> Üzv | None:
        g = self.üzv("göstər")
        return g[0] if g else None

    def adlar(self) -> set[str]:
        a: set[str] = set()
        for u in self.üzvlər:
            if u.ad:
                a.add(u.ad)
            a.update(u.adlar)
        return a


def komponentləri_tap(t: Mətn) -> list[Komponent]:
    nəticə: list[Komponent] = []
    sətirlər = t.sətirlər
    i = 0
    while i < len(sətirlər):
        if not t.kod_sətiridir(i):
            i += 1
            continue
        a = _KOMPONENT.match(sətirlər[i])
        if not a:
            i += 1
            continue
        g = girinti(sətirlər[i])
        son = _son_tap(t, i, g)
        k = Komponent(a.group(1), i, son, g, g + 4)
        _üzvləri_tap(t, k)
        nəticə.append(k)
        i = (son if son is not None else len(sətirlər)) + 1
    return nəticə


def _son_tap(t: Mətn, baş: int, g: int) -> int | None:
    """`baş` sətrindəki bloku bağlayan `son` — eyni girintidə."""
    for j in range(baş + 1, len(t.sətirlər)):
        s = t.sətirlər[j]
        if boşdur(s) or not t.kod_sətiridir(j):
            continue
        gj = girinti(s)
        if gj < g:
            return None                 # blok bağlanmadan girinti azaldı
        if gj == g:
            return j if t.ilk_söz(j) == "son" else None
    return None


def _üzvləri_tap(t: Mətn, k: Komponent) -> None:
    son = k.son if k.son is not None else len(t.sətirlər)
    # Üzv girintisi — gövdənin ilk kod sətrinin girintisi
    for j in range(k.baş + 1, son):
        if t.kod_sətiridir(j):
            k.üzv_girintisi = girinti(t.sətirlər[j])
            break
    cari: Üzv | None = None
    for j in range(k.baş + 1, son):
        s = t.sətirlər[j]
        if (t.kod_sətiridir(j) and girinti(s) == k.üzv_girintisi):
            a = _ÜZV.match(s.lstrip(" \t"))
            if a:
                növ = a.group(1)
                ad = "göstər" if növ == "göstər" else (a.group(2) or "")
                cari = Üzv(növ, ad, j, j)
                k.üzvlər.append(cari)
                continue
        if cari is not None:
            cari.son = j
    # Sondakı boş və şərh sətirləri üzvə aid deyil
    for u in k.üzvlər:
        while u.son > u.baş and (boşdur(t.sətirlər[u.son])
                                 or t.şərh_sətiridir(u.son)):
            u.son -= 1
        if u.növ == "qurucu":
            parça = "\n".join(t.kod_hissəsi(j)
                              for j in range(u.baş, u.son + 1))
            u.adlar = _XASSƏ_PARAMETRİ.findall(parça)


def sinif_adları(t: Mətn) -> set[str]:
    adlar: set[str] = set()
    for i, s in enumerate(t.sətirlər):
        if t.kod_sətiridir(i):
            a = _SİNİF_ADI.match(s)
            if a:
                adlar.add(a.group(1))
    return adlar


def komponent_tap(t: Mətn, kursor: int | None) -> Komponent | None:
    """Kursorun içində olduğu komponent, yoxsa birincisi."""
    hamısı = komponentləri_tap(t)
    if not hamısı:
        return None
    if kursor is not None:
        s = t.sətir_nömrəsi(kursor)
        for k in hamısı:
            son = k.son if k.son is not None else len(t.sətirlər)
            if k.baş <= s <= son:
                return k
    return hamısı[0]


# ═══════════════════════════════════════════════════════════════════════
#  Mötərizələr və vidjet çağırışları
# ═══════════════════════════════════════════════════════════════════════

CÜTLƏR = {"(": ")", "[": "]", "{": "}"}


def uyğun_bağlayan(t: Mətn, i: int) -> int | None:
    """`i`-dəki açan mötərizənin cütü (yalnız kod simvolları sayılır)."""
    m, x = t.mətn, t.x
    yığın: list[str] = []
    for j in range(i, len(m)):
        if x[j] != KOD:
            continue
        c = m[j]
        if c in CÜTLƏR:
            yığın.append(CÜTLƏR[c])
        elif c in ")]}":
            if not yığın or yığın[-1] != c:
                return None
            yığın.pop()
            if not yığın:
                return j
    return None


_VİDJET_ÇAĞIRIŞI = re.compile(r"\bvidjet\s*\.\s*([^\W\d]\w*)\s*\(")


@dataclass
class Çağırış:
    ad: str
    baş: int                      # `vidjet` sözünün mövqeyi
    ad_başı: int
    açan: int                     # `(` mövqeyi
    son: int | None               # `)` mövqeyi


def vidjet_çağırışları(t: Mətn) -> list[Çağırış]:
    nəticə: list[Çağırış] = []
    for a in _VİDJET_ÇAĞIRIŞI.finditer(t.mətn):
        if t.x[a.start()] != KOD:
            continue
        if a.start() > 0 and t.mətn[a.start() - 1] == ".":
            continue
        açan = a.end() - 1
        nəticə.append(Çağırış(a.group(1), a.start(), a.start(1), açan,
                              uyğun_bağlayan(t, açan)))
    return nəticə


def çağırış_tap(t: Mətn, kursor: int) -> Çağırış | None:
    """Kursoru əhatə edən ən içəridəki `vidjet.ad(...)` çağırışı."""
    ən_yaxşı: Çağırış | None = None
    for ç in vidjet_çağırışları(t):
        son = ç.son if ç.son is not None else ç.açan
        if ç.baş <= kursor <= son + 1:
            if ən_yaxşı is None or ç.baş > ən_yaxşı.baş:
                ən_yaxşı = ç
    return ən_yaxşı
