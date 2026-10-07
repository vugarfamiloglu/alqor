"""
Alqor Studio — vizual dizayner (sürüklə-burax düzülüş).

Komponentin `göstər()`-indəki vidjet ağacı (`vidjet.sütun(məzmun: [...])`
və içindəkilər) qutular şəklində göstərilir. Paletdən element sürüklənib
istənilən konteynerin istənilən yerinə buraxılır, mövcud element başqa
yerə (başqa konteynerə də) daşınır və ya silinir — hər əməliyyat KODU
dəyişir, kod həqiqətin yeganə mənbəyi olaraq qalır.

Düyünlər yolla tanınır: `[]` kök, `[0, 2]` — kökün 1-ci uşağının 3-cü
uşağı. Konteyner — `məzmun:` arqumenti (və ya ilk mövqeli arqumenti)
siyahı (`[...]`) olan çağırışdır.

Bütün funksiyalar saf funksiyadır: mətn alır, yeni mətn qaytarır.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .qurulus import (KOD, Komponent, Mətn, girinti, komponent_tap,
                      komponentləri_tap, uyğun_bağlayan)
from .skelet import SkeletXətası, vidjet_əlavə_et

GİRİNTİ = 4
ÜFÜQİ = {"sətir", "düyməQrupu", "alətlərPaneli", "tor", "avatarQrupu"}
_VİDJET = re.compile(r"vidjet\s*\.\s*([^\W\d]\w*)\s*\(")
_ADLI = re.compile(r"([^\W\d]\w*)\s*:(?!:)")
_XÜLASƏ_ARQ = ("mətn", "etiket", "başlıq", "ad", "dəyər", "ikon")


class DizaynXətası(SkeletXətası):
    pass


@dataclass
class Düyün:
    baş: int                          # elementin (siyahıdakı) başlanğıcı
    son: int                          # sonu (daxil deyil)
    ad: str | None = None             # vidjet adı; None — başqa ifadə
    siyahı: tuple[int, int] | None = None   # `[` və `]` mövqeyi
    uşaqlar: list["Düyün"] = field(default_factory=list)
    xülasə: str = ""
    ad_başı: int = 0

    def lüğət(self, yol: list[int], t: Mətn) -> dict:
        from alqor.vidjet import BEYNƏLXALQ_ADLAR
        d = {"yol": yol, "ad": self.ad,
             "beynəlxalqAd": BEYNƏLXALQ_ADLAR.get(self.ad or "", self.ad),
             "mövqe": self.ad_başı or self.baş, "xülasə": self.xülasə,
             "sətir": t.sətir_nömrəsi(self.baş) + 1,
             "konteyner": self.siyahı is not None}
        if self.siyahı is not None:
            d["istiqamət"] = "üfüqi" if self.ad in ÜFÜQİ else "şaquli"
            d["uşaqlar"] = [u.lüğət(yol + [i], t)
                            for i, u in enumerate(self.uşaqlar)]
        return d


# ═══════════════════════════════════════════════════════════════════════
#  Təhlil
# ═══════════════════════════════════════════════════════════════════════

def _böl(t: Mətn, baş: int, son: int) -> list[tuple[int, int, int]]:
    """
    `baş..son` aralığını üst səviyyə vergüllərə görə bölür:
    (blokun başı — öndəki şərhlər daxil, kodun başı, son).
    """
    hissələr: list[tuple[int, int]] = []
    dərinlik = 0
    b = baş
    m, x = t.mətn, t.x
    for j in range(baş, son):
        if x[j] != KOD:
            continue
        c = m[j]
        if c in "([{":
            dərinlik += 1
        elif c in ")]}":
            dərinlik -= 1
        elif c == "," and dərinlik == 0:
            hissələr.append((b, j))
            b = j + 1
    hissələr.append((b, son))
    n = []
    for a, e in hissələr:
        while a < e and m[a].isspace():
            a += 1
        blok = a
        while a < e:                     # öndəki şərhlər elementə aiddir
            if m[a].isspace():
                a += 1
            elif m.startswith(("//", "/*"), a):
                a = _şərhi_keç(t, a)
            else:
                break
        while e > a and m[e - 1].isspace():
            e -= 1
        if e > a:
            n.append((blok, a, e))
    return n


def _şərhi_keç(t: Mətn, i: int) -> int:
    """Şərh simvollarını (`//…` və ya `/*…*/`) keçir."""
    m = t.mətn
    if m.startswith("//", i):
        j = m.find("\n", i)
        return len(m) if j < 0 else j
    if m.startswith("/*", i):
        j = m.find("*/", i + 2)
        return len(m) if j < 0 else j + 2
    return i + 1


def _literal(m: str) -> str | None:
    m = m.strip()
    if len(m) >= 2 and m[0] == '"' and m[-1] == '"' and '"' not in m[1:-1] \
            and "{" not in m:
        return m[1:-1]
    return None


def _düyün(t: Mətn, baş: int, son: int, kod: int | None = None) -> Düyün:
    m = t.mətn
    kod = baş if kod is None else kod
    a = _VİDJET.match(m, kod)
    if not a:
        mətn = " ".join(m[kod:son].split())
        return Düyün(baş, son, None,
                     xülasə=mətn if len(mətn) <= 40 else mətn[:39] + "…")
    açan = a.end() - 1
    bağlayan = uyğun_bağlayan(t, açan)
    d = Düyün(baş, son, a.group(1), ad_başı=a.start(1))
    if bağlayan is None:
        return d
    for i, (_, ab, ae) in enumerate(_böl(t, açan + 1, bağlayan)):
        ad = None
        vb = ab
        x = _ADLI.match(m, ab)
        if x:
            ad = x.group(1)
            vb = x.end()
            while vb < ae and m[vb].isspace():
                vb += 1
        if (ad == "məzmun" or (ad is None and i == 0)) and \
                vb < ae and m[vb] == "[":
            sb = uyğun_bağlayan(t, vb)
            if sb is not None and d.siyahı is None:
                d.siyahı = (vb, sb)
                d.uşaqlar = [_düyün(t, eb, ee, ek)
                             for eb, ek, ee in _böl(t, vb + 1, sb)]
        elif ad in _XÜLASƏ_ARQ and not d.xülasə:
            d.xülasə = _literal(m[vb:ae]) or ""
        elif ad is None and i == 0 and not d.xülasə:
            d.xülasə = _literal(m[vb:ae]) or ""
    return d


def _komponent(t: Mətn, kursor: int | None, ad: str | None) -> Komponent:
    if ad:
        for k in komponentləri_tap(t):
            if k.ad == ad:
                return k
        raise DizaynXətası(f"`{ad}` komponenti tapılmadı")
    k = komponent_tap(t, kursor) if kursor is not None else None
    if k is None:
        hamısı = komponentləri_tap(t)
        if not hamısı:
            raise DizaynXətası("Faylda komponent yoxdur — paletdən element "
                               "əlavə edin, iskelet avtomatik yaranacaq")
        k = hamısı[0]
    return k


def kök(t: Mətn, k: Komponent) -> Düyün | None:
    """`göstər()`-in `qaytar` etdiyi ən xarici vidjet çağırışı."""
    g = k.göstər()
    if g is None:
        return None
    baş = t.başlar[g.baş]
    son_sətir = min(g.son, len(t.sətirlər) - 1)
    son = t.başlar[son_sətir] + len(t.sətirlər[son_sətir])
    for a in _VİDJET.finditer(t.mətn, baş, son):
        if t.x[a.start()] != KOD:
            continue
        if a.start() > 0 and t.mətn[a.start() - 1] == ".":
            continue
        bağlayan = uyğun_bağlayan(t, a.end() - 1)
        if bağlayan is None:
            return None
        return _düyün(t, a.start(), bağlayan + 1)
    return None


def ağac(mətn: str, kursor: int | None = None,
         komponent: str | None = None) -> dict:
    t = Mətn(mətn)
    k = _komponent(t, kursor, komponent)
    r = kök(t, k)
    return {"komponent": k.ad,
            "komponentlər": [x.ad for x in komponentləri_tap(t)],
            "kök": r.lüğət([], t) if r is not None else None}


# ═══════════════════════════════════════════════════════════════════════
#  Əməliyyatlar
# ═══════════════════════════════════════════════════════════════════════

def _tap(r: Düyün, yol: list[int]) -> Düyün:
    d = r
    for i in yol:
        if d.siyahı is None or not 0 <= i < len(d.uşaqlar):
            raise DizaynXətası("element tapılmadı — kod dəyişib, yenidən "
                               "cəhd edin")
        d = d.uşaqlar[i]
    return d


def _ayır(t: Mətn, d: Düyün) -> str:
    """Elementin mətni, ilk sütunu 0 olmaqla (daxili girinti saxlanır)."""
    m = t.mətn
    s = t.sətir_nömrəsi(d.baş)
    sütun = d.baş - t.başlar[s]
    sətirlər = m[d.baş:d.son].split("\n")
    n = [sətirlər[0]]
    for x in sətirlər[1:]:
        k = min(sütun, girinti(x)) if x.strip() else len(x)
        n.append(x[k:])
    return "\n".join(n)


def _siyahı_mətni(t: Mətn, konteyner: Düyün, elementlər: list[str]) -> str:
    """`[...]` yenidən yazılır: hər element ayrı sətirdə."""
    açan = konteyner.siyahı[0]
    g = girinti(t.sətirlər[t.sətir_nömrəsi(açan)])
    if not elementlər:
        return "[]"
    iç = " " * (g + GİRİNTİ)
    hissələr = []
    for i, e in enumerate(elementlər):
        e = e.replace("\n", "\n" + iç)
        hissələr.append(iç + e + ("," if i < len(elementlər) - 1 else ""))
    return "[\n" + "\n".join(hissələr) + "\n" + " " * g + "]"


def _siyahını_yaz(mətn: str, konteyner: Düyün, elementlər: list[str]
                  ) -> str:
    t = Mətn(mətn)
    a, b = konteyner.siyahı
    return mətn[:a] + _siyahı_mətni(t, konteyner, elementlər) + mətn[b + 1:]


def _kök(mətn: str, komponent: str | None) -> tuple[Mətn, Düyün]:
    t = Mətn(mətn)
    k = _komponent(t, None, komponent)
    r = kök(t, k)
    if r is None:
        raise DizaynXətası("`göstər()` vidjet çağırışı qaytarmır — "
                           "dizayner `vidjet.sütun(məzmun: [...])` kimi kök "
                           "element tələb edir")
    return t, r


def _nəticə(mətn: str, mesaj: str, komponent: str | None,
            yol: list[int] | None) -> dict:
    kursor = 0
    if yol is not None:
        try:
            _, r = _kök(mətn, komponent)
            kursor = _tap(r, yol).baş
        except DizaynXətası:
            pass
    return {"mətn": mətn, "kursor": kursor, "mesaj": mesaj, "yol": yol}


def sil(mətn: str, yol: list[int], komponent: str | None = None) -> dict:
    if not yol:
        raise DizaynXətası("kök element silinə bilməz")
    t, r = _kök(mətn, komponent)
    ana = _tap(r, yol[:-1])
    d = _tap(r, yol)
    elementlər = [_ayır(t, u) for u in ana.uşaqlar if u is not d]
    yeni = _siyahını_yaz(mətn, ana, elementlər)
    return _nəticə(yeni, f"`{d.ad or 'element'}` silindi", komponent, None)


def köçür(mətn: str, mənbə: list[int], hədəf: list[int], indeks: int,
          komponent: str | None = None) -> dict:
    """
    `mənbə` elementini `hədəf` konteynerinin `indeks` yerinə daşıyır
    (`indeks` — daşımadan ƏVVƏLKİ siyahıya görə).
    """
    if not mənbə:
        raise DizaynXətası("kök element daşına bilməz")
    if hədəf[:len(mənbə)] == mənbə:
        raise DizaynXətası("element öz içinə daşına bilməz")
    t, r = _kök(mətn, komponent)
    d = _tap(r, mənbə)
    k = _tap(r, hədəf)
    if k.siyahı is None:
        raise DizaynXətası(f"`{k.ad}` konteyner deyil")
    ana_yol, i = mənbə[:-1], mənbə[-1]
    indeks = max(0, min(indeks, len(k.uşaqlar)))
    if ana_yol == hədəf:
        if indeks in (i, i + 1):
            return _nəticə(mətn, "yer dəyişmədi", komponent, mənbə)
        elementlər = [_ayır(t, u) for u in k.uşaqlar]
        e = elementlər.pop(i)
        yeni_i = indeks - 1 if indeks > i else indeks
        elementlər.insert(yeni_i, e)
        yeni = _siyahını_yaz(mətn, k, elementlər)
        return _nəticə(yeni, f"`{d.ad or 'element'}` daşındı", komponent,
                       hədəf + [yeni_i])
    # 1. Mənbədən çıxar
    e = _ayır(t, d)
    ana = _tap(r, ana_yol)
    mətn2 = _siyahını_yaz(mətn, ana,
                          [_ayır(t, u) for u in ana.uşaqlar if u is not d])
    # 2. Hədəf yolu — mənbənin sonrakı qardaşlarının içindədirsə sürüşür
    hədəf2 = list(hədəf)
    if hədəf2[:len(ana_yol)] == ana_yol and len(hədəf2) > len(ana_yol) \
            and hədəf2[len(ana_yol)] > i:
        hədəf2[len(ana_yol)] -= 1
    t2, r2 = _kök(mətn2, komponent)
    k2 = _tap(r2, hədəf2)
    elementlər = [_ayır(t2, u) for u in k2.uşaqlar]
    elementlər.insert(indeks, e)
    yeni = _siyahını_yaz(mətn2, k2, elementlər)
    return _nəticə(yeni, f"`{d.ad or 'element'}` daşındı", komponent,
                   hədəf2 + [indeks])


def əlavə_et(mətn: str, vidjet: str, hədəf: list[int], indeks: int,
             komponent: str | None = None) -> dict:
    """
    Paletdən buraxılan element: əvvəlcə skelet onu (vəziyyət, metod,
    idxal ilə birlikdə) kökün sonuna yazır, sonra dizayner yerinə daşıyır.
    """
    t = Mətn(mətn)
    k = _komponent(t, None, komponent)
    əvvəl = kök(t, k)
    say = len(əvvəl.uşaqlar) if əvvəl is not None and \
        əvvəl.siyahı is not None else None
    n = vidjet_əlavə_et(mətn, vidjet, t.başlar[k.baş])
    t2, r = _kök(n.mətn, k.ad)
    if r.siyahı is None or not r.uşaqlar:
        return {"mətn": n.mətn, "kursor": n.kursor, "mesaj": n.mesaj,
                "yol": None}
    yeni_yol = [len(r.uşaqlar) - 1]
    if say is None or len(r.uşaqlar) != say + 1:
        # Kök dəyişdi (məs. sütuna büküldü) — yer seçimi mənasızdır
        return _nəticə(n.mətn, n.mesaj, k.ad, yeni_yol)
    if hədəf == [] and indeks >= say:
        return _nəticə(n.mətn, n.mesaj, k.ad, yeni_yol)
    q = köçür(n.mətn, yeni_yol, hədəf, indeks, k.ad)
    q["mesaj"] = n.mesaj
    return q
