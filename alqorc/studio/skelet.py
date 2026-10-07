"""
Alqor Studio — vidjet skeleti: iki klikdə işləyən kod.

İstifadəçi tələbi: paletdən əlavə edilmiş elementin üzərinə iki dəfə
klikləndikdə o elementin işləməsi üçün lazım olan BÜTÜN kod redaktora
yazılır:

  1. `gətir vidjet` sətri (yoxdursa)
  2. `vəziyyət` sahəsi — komponentin digər vəziyyətlərinin yanına
  3. hadisə idarəedicisi (`metod …Dəyişdi`) — `göstər()`-dən əvvələ
  4. vidjet çağırışının özü — `göstər()`-in JSX-inə və ya
     `məzmun: [...]` siyahısına
  5. faylda komponent yoxdursa — komponent iskeleti (+ `əsas()`)

Adlar təkrarlanmır: `sahə1`, `sahə2`, … Kataloqdakı sabit adlar
(`şifrə`, `axtar`, `göndər` …) mövcud üzvlə toqquşursa nömrələnir.

Məlumat mənbəyi `alqor.vidjet.KATALOQ`-dur — skelet mətnləri orada
saxlanılır, burada yalnız onların FAYLA YERLƏŞDİRİLMƏSİ həll olunur.

Bütün funksiyalar saf funksiyadır: mətn alır, yeni mətn qaytarır.
Redaktor nəticəni bir geri-al addımı kimi tətbiq edir.
"""

from __future__ import annotations
import inspect
import re
from dataclasses import dataclass, field

from alqor import vidjet as V
from alqor.acar_sozler import ACAR_SOZLER

from .qurulus import (KOD, Komponent, Mətn, boşdur, girinti, komponent_tap,
                      komponentləri_tap, sinif_adları, uyğun_bağlayan,
                      vidjet_çağırışları, çağırış_tap)

GİRİNTİ = 4
_AD = re.compile(r"^[^\W\d]\w*$")
_ÖZÜ_İSTİNADI = re.compile(r"\bözü\s*\.\s*([^\W\d]\w*)")


class SkeletXətası(Exception):
    """İstifadəçiyə göstəriləcək xəta (Azərbaycan dilində)."""


@dataclass
class Nəticə:
    mətn: str
    kursor: int
    yeni_sətirlər: list[tuple[int, int]]     # 1-dən, daxil
    mesaj: str
    əlavələr: list[str] = field(default_factory=list)
    dəyişdi: bool = True

    def lüğət(self) -> dict:
        return {"mətn": self.mətn, "kursor": self.kursor,
                "yeniSətirlər": [list(a) for a in self.yeni_sətirlər],
                "mesaj": self.mesaj, "əlavələr": self.əlavələr,
                "dəyişdi": self.dəyişdi}


# ═══════════════════════════════════════════════════════════════════════
#  Kataloqdan hazırlıq
# ═══════════════════════════════════════════════════════════════════════

# Kataloq nümunəsinin özündə olmayan, amma skeletin mənalı işləməsi
# üçün lazım olan əlavə arqumentlər
ƏLAVƏ_ARQUMENTLƏR: dict[str, str] = {
    "xəbərdarlıq": "bağlana: doğru",
}


def _düzəlt(kod: str) -> str:
    # Kataloq skeletlərinin tip yoxlamasından keçdiyini
    # `sinaq/test_vidjet.py` təmin edir — burada düzəliş lazım deyil
    return kod


def məlumat(ad: str) -> V.Məlumat:
    for m in V.KATALOQ:
        if m.ad == ad:
            return m
    from alqor.elifba import latınla
    sadə = latınla(ad).lower()
    yaxın = [m.ad for m in V.KATALOQ
             if sadə and (sadə in latınla(m.ad).lower()
                          or latınla(m.ad).lower() in sadə)]
    əlavə = f" Oxşarlar: {', '.join(yaxın[:5])}" if yaxın else ""
    raise SkeletXətası(f"`{ad}` vidjeti yoxdur.{əlavə}")


def _parametrlər(ad: str) -> list[str]:
    f = getattr(V, ad, None)
    if f is None:
        return []
    return list(inspect.signature(f).parameters)[1:]


def ad_düzgündür(ad: str) -> bool:
    return bool(_AD.match(ad)) and ad not in ACAR_SOZLER


def _baza_adı(vidjet_adı: str) -> str:
    return V._standart_ad(vidjet_adı)


def _şablon_adları(m: V.Məlumat) -> list[str]:
    """`{ad}` daşıyan bütün ad şablonları: `{ad}`, `{ad}Dəyişdi` …"""
    mətn = "\n".join((m.vəziyyət, m.skelet, m.nümunə))
    adlar = re.findall(r"(?:vəziyyət|metod)\s+([\w{}]+)", mətn)
    adlar += re.findall(r"özü\.([\w{}]+)", mətn)
    nəticə: list[str] = []
    for a in adlar:
        if "{ad}" in a and a not in nəticə:
            nəticə.append(a)
    return nəticə


def _ad_lazımdır(m: V.Məlumat) -> bool:
    """Vidjetin komponentə yazılacaq vəziyyəti/idarəedicisi varmı."""
    return bool(m.skelet or m.vəziyyət)


def ad_seç(m: V.Məlumat, mövcud: set[str], istək: str | None = None) -> str:
    """
    Təkrarlanmayan ad: `sahə1`, `sahə2` … İstifadəçi ad veribsə əvvəlcə
    o yoxlanılır, sonra `ad2`, `ad3` …
    """
    if istək and not ad_düzgündür(istək):
        raise SkeletXətası(f"`{istək}` düzgün ad deyil")
    şablonlar = _şablon_adları(m)
    baza = istək or _baza_adı(m.ad)
    namizədlər = [istək] if istək else []
    namizədlər += [f"{baza}{n}" for n in range(2 if istək else 1, 10000)]
    for ad in namizədlər:
        if not any(ş.replace("{ad}", ad) in mövcud for ş in şablonlar):
            return ad
    raise SkeletXətası("boş ad tapılmadı")         # praktikada olmur


@dataclass
class Hazır:
    """Fayla yerləşdirilməyə hazır skelet hissələri (sıfır girinti)."""
    ad: str
    vəziyyətlər: list[tuple[str, str]]          # (ad, sətir)
    metodlar: list[tuple[str, list[str]]]       # (ad, sətirlər)
    çağırış: str

    def təyin_olunanlar(self) -> list[str]:
        return [a for a, _ in self.vəziyyətlər] + [a for a, _ in
                                                   self.metodlar]


def _hissələrə_böl(kod: str) -> tuple[list[tuple[str, str]],
                                      list[tuple[str, list[str]]]]:
    vəziyyətlər: list[tuple[str, str]] = []
    metodlar: list[tuple[str, list[str]]] = []
    cari: list[str] | None = None
    for s in kod.split("\n"):
        if cari is not None:
            cari.append(s)
            if s.strip() == "son" and girinti(s) == 0:
                cari = None
            continue
        a = re.match(r"vəziyyət\s+([^\W\d]\w*)", s)
        if a:
            vəziyyətlər.append((a.group(1), s))
            continue
        a = re.match(r"metod\s+([^\W\d]\w*)", s)
        if a:
            cari = [s]
            metodlar.append((a.group(1), cari))
    return vəziyyətlər, metodlar


def _sabit_adları_nömrələ(skelet: str, çağırış: str, vəziyyətlər: list[str],
                          metodlar: list[str], ad: str,
                          mövcud: set[str]) -> tuple[str, str]:
    """
    Kataloqdakı sabit adlar mövcud üzvlə toqquşursa nömrələnir. Kök
    birlikdə dəyişir: `şifrə` + `şifrəDəyişdi` → `şifrə2` +
    `şifrə2Dəyişdi` (`şifrəDəyişdi2` yox).
    """
    təyin = vəziyyətlər + metodlar
    tutulmuş = set(mövcud)
    görülmüş: set[str] = set()
    for a in təyin:
        if ad in a or a in görülmüş:
            continue
        # Kök — bu adın başlandığı vəziyyət adı (yoxdursa özü)
        kök = next((v for v in vəziyyətlər if a.startswith(v)), a)
        ailə = [b for b in təyin if b.startswith(kök) and ad not in b]
        görülmüş.update(ailə)
        if not any(b in tutulmuş for b in ailə):
            continue
        n = 2
        while any(kök + str(n) + b[len(kök):] in tutulmuş for b in ailə):
            n += 1
        yeni = f"{kök}{n}"
        tutulmuş.update(yeni + b[len(kök):] for b in ailə)
        sonluqlar = "|".join(re.escape(b[len(kök):]) for b in ailə)
        naxış = re.compile(
            rf"(?<!\w){re.escape(kök)}(?=(?:{sonluqlar})(?!\w))")
        skelet = naxış.sub(yeni, skelet)
        çağırış = naxış.sub(yeni, çağırış)
    return skelet, çağırış


def hazırla(m: V.Məlumat, ad: str, mövcud: set[str],
            adları_dəyiş: bool = True) -> Hazır:
    """
    Skeleti `ad` ilə doldurur. `adları_dəyiş` — kataloqdakı SABİT adlar
    (`şifrə`, `axtar` …) mövcud üzvlə toqquşursa nömrələnir.
    """
    hissə = "\n\n".join(h for h in (m.vəziyyət, m.skelet) if h)
    skelet = _düzəlt(hissə.replace("{ad}", ad))
    çağırış = _düzəlt(m.nümunə.replace("{ad}", ad))

    vəziyyətlər, metodlar = _hissələrə_böl(skelet)
    if adları_dəyiş:
        skelet, çağırış = _sabit_adları_nömrələ(
            skelet, çağırış, [a for a, _ in vəziyyətlər],
            [a for a, _ in metodlar], ad, mövcud)
        vəziyyətlər, metodlar = _hissələrə_böl(skelet)

    # Nümunədə istifadə olunmayan idarəedicini uyğun hadisəyə bağla
    # (`xəbərdarlıq` → `bağlandı:`, `cədvəl` → `sətirKlik:`)
    parametrlər = _parametrlər(m.ad)
    istifadəsiz = [a for a, _ in metodlar
                   if not re.search(rf"özü\.{re.escape(a)}(?!\w)", çağırış)]
    əlavələr: list[str] = []
    for h in m.hadisələr:
        if not istifadəsiz:
            break
        if h in parametrlər and not re.search(rf"(?<!\w){h}\s*:", çağırış):
            əlavələr.append(f"{h}: özü.{istifadəsiz.pop(0)}")
    if m.ad in ƏLAVƏ_ARQUMENTLƏR:
        p = ƏLAVƏ_ARQUMENTLƏR[m.ad]
        if not re.search(rf"(?<!\w){p.split(':')[0]}\s*:", çağırış):
            əlavələr.insert(0, p)
    if əlavələr:
        # Çağırış adətən ~12 sütun girintidə yerləşir
        çağırış = arqument_əlavə_et(çağırış, əlavələr, əsas_sütun=12)
    return Hazır(ad, vəziyyətlər, metodlar, çağırış)


def arqument_əlavə_et(çağırış: str, arqumentlər: list[str],
                      əsas_sütun: int = 0, hiza: int | None = None) -> str:
    """
    Çağırış mətninin sonuncu `)`-dan əvvəl arqument əlavə edir.
    `əsas_sütun` — mətnin ilk sətrinin redaktordakı sütunu. Sətir 79
    simvolu keçərsə arqumentlər yeni sətrə, `hiza` sütununa keçir.
    """
    son = çağırış.rstrip().rfind(")")
    if son < 0:
        return çağırış
    əvvəl = çağırış[:son].rstrip()
    sıra = ", ".join(arqumentlər)
    boş = əvvəl.endswith("(")
    son_sətir = əvvəl.split("\n")[-1]
    if əsas_sütun + len(son_sətir) + len(sıra) + 3 <= 79:
        return əvvəl + ("" if boş else ", ") + sıra + çağırış[son:]
    if hiza is None:
        hiza = (girinti(son_sətir) if "\n" in əvvəl
                else əvvəl.find("(") + 1)
    return (əvvəl + ("" if boş else ",") + "\n" + " " * hiza + sıra
            + çağırış[son:])


# ═══════════════════════════════════════════════════════════════════════
#  Sətir düzəlişləri
# ═══════════════════════════════════════════════════════════════════════

YENİ = "yeni"
ÇAĞIRIŞ = "çağırış"


@dataclass
class _Düzəliş:
    baş: int                      # sətir indeksi
    silinən: int
    yeni: list[str]
    etiketlər: list[str | None]
    sıra: int = 0


class _Redaktə:
    def __init__(self, t: Mətn):
        self.t = t
        self.düzəlişlər: list[_Düzəliş] = []

    def əlavə(self, baş: int, sətirlər: list[str], silinən: int = 0,
              etiketlər: list[str | None] | None = None,
              öndə: bool = False) -> None:
        """`öndə` — eyni sətrə düşən digər əlavələrdən əvvələ."""
        if etiketlər is None:
            etiketlər = [YENİ] * len(sətirlər)
        sıra = len(self.düzəlişlər)
        self.düzəlişlər.append(_Düzəliş(baş, silinən, sətirlər, etiketlər,
                                        -1000 + sıra if öndə else sıra))

    def tətbiq_et(self) -> tuple[str, int | None, list[tuple[int, int]]]:
        sətirlər = list(self.t.sətirlər)
        etiketlər: list[str | None] = [None] * len(sətirlər)
        for d in sorted(self.düzəlişlər, key=lambda d: (d.baş, d.sıra),
                        reverse=True):
            sətirlər[d.baş:d.baş + d.silinən] = d.yeni
            etiketlər[d.baş:d.baş + d.silinən] = d.etiketlər
        # Yan-yana iki boş sətir (biri yenidirsə) birə endirilir
        son_s: list[str] = []
        son_e: list[str | None] = []
        for s, e in zip(sətirlər, etiketlər):
            if (boşdur(s) and son_s and boşdur(son_s[-1])
                    and (e or son_e[-1])):
                if e == ÇAĞIRIŞ:
                    son_e[-1] = e
                continue
            son_s.append(s.rstrip() if e else s)
            son_e.append(e)
        mətn = "\n".join(son_s)
        kursor = None
        mövqe = 0
        aralıqlar: list[tuple[int, int]] = []
        for i, (s, e) in enumerate(zip(son_s, son_e)):
            if e == ÇAĞIRIŞ and kursor is None:
                kursor = mövqe + girinti(s)
            if e and not boşdur(s):
                if aralıqlar and aralıqlar[-1][1] == i:
                    aralıqlar[-1] = (aralıqlar[-1][0], i + 1)
                else:
                    aralıqlar.append((i + 1, i + 1))
            mövqe += len(s) + 1
        return mətn, kursor, aralıqlar


def _girintilə(sətirlər: list[str], g: int) -> list[str]:
    boşluq = " " * g
    return [boşluq + s if s.strip() else "" for s in sətirlər]


def _çağırış_sətirləri(çağırış: str, g: int, jsx: bool = False,
                       vergül: bool = False) -> list[str]:
    """Çağırış mətnini `g` girintisi ilə sətirlərə bölür."""
    hissələr = çağırış.split("\n")
    if jsx:
        hissələr = (["{" + hissələr[0]]
                    + [" " + h if h.strip() else h for h in hissələr[1:]])
        hissələr[-1] += "}"
    if vergül:
        hissələr[-1] += ","
    return _girintilə(hissələr, g)


def _çağırış_etiketləri(n: int) -> list[str | None]:
    return [ÇAĞIRIŞ] + [YENİ] * (n - 1)


# ═══════════════════════════════════════════════════════════════════════
#  `gətir` sətirləri
# ═══════════════════════════════════════════════════════════════════════

_GƏTİR = re.compile(r"^(?:gətir|getir)\s+([^\W\d][\w.]*)")


def idxal_olunub(t: Mətn, modul: str) -> bool:
    for i, s in enumerate(t.sətirlər):
        if t.kod_sətiridir(i):
            a = _GƏTİR.match(s.strip())
            if a and a.group(1).split(".")[0] == modul:
                return True
    return False


def _idxal_bölməsi(t: Mətn) -> tuple[int | None, int | None]:
    """(sonuncu üst-səviyyə `gətir` sətri, ilk başqa kod sətri)"""
    son_gətir = None
    for i, s in enumerate(t.sətirlər):
        if boşdur(s) or not t.kod_sətiridir(i):
            continue
        if girinti(s) == 0 and _GƏTİR.match(s):
            son_gətir = i
            continue
        return son_gətir, i
    return son_gətir, None


def _son_dolu_sətir(t: Mətn) -> int:
    for i in range(len(t.sətirlər) - 1, -1, -1):
        if not boşdur(t.sətirlər[i]):
            return i
    return -1


def _idxal_düzəlişi(r: _Redaktə, modullar: list[str]) -> list[str]:
    lazım = [m for m in modullar if not idxal_olunub(r.t, m)]
    if not lazım:
        return []
    sətirlər = [f"gətir {m}" for m in lazım]
    son_gətir, ilk_kod = _idxal_bölməsi(r.t)
    if son_gətir is not None:
        r.əlavə(son_gətir + 1, sətirlər, öndə=True)
    elif ilk_kod is not None:
        r.əlavə(ilk_kod, sətirlər + [""], öndə=True)
    else:
        son = _son_dolu_sətir(r.t)
        r.əlavə(son + 1, ([""] if son >= 0 else []) + sətirlər, öndə=True)
    return lazım


# ═══════════════════════════════════════════════════════════════════════
#  Komponent daxilinə yerləşdirmə
# ═══════════════════════════════════════════════════════════════════════

def _komponent_istinadları(t: Mətn, k: Komponent) -> set[str]:
    son = k.son if k.son is not None else len(t.sətirlər) - 1
    parça = "\n".join(t.kod_hissəsi(i) for i in range(k.baş, son + 1))
    return set(_ÖZÜ_İSTİNADI.findall(parça))


def _vəziyyətləri_yerləşdir(r: _Redaktə, k: Komponent,
                            vəziyyətlər: list[str]) -> None:
    if not vəziyyətlər:
        return
    sətirlər = _girintilə(vəziyyətlər, k.üzv_girintisi)
    mövcud = k.üzv("vəziyyət")
    if mövcud:
        r.əlavə(mövcud[-1].son + 1, sətirlər)
    else:
        r.əlavə(k.baş + 1, sətirlər + [""])


def _metodların_yeri(t: Mətn, k: Komponent) -> int:
    g = k.göstər()
    if g is not None:
        yer = g.baş
        # `göstər()`-in üstündəki şərh ona aiddir
        while (yer - 1 > k.baş and t.şərh_sətiridir(yer - 1)
               and girinti(t.sətirlər[yer - 1]) == k.üzv_girintisi):
            yer -= 1
        return yer
    return _gövdənin_sonu(t, k)


def _gövdənin_sonu(t: Mətn, k: Komponent) -> int:
    if k.son is not None:
        return k.son
    if k.üzvlər:
        return k.üzvlər[-1].son + 1
    return k.baş + 1


def _metodları_yerləşdir(r: _Redaktə, k: Komponent,
                         metodlar: list[list[str]], yer: int) -> None:
    if not metodlar:
        return
    sətirlər: list[str] = []
    for m in metodlar:
        sətirlər += [""] + _girintilə(m, k.üzv_girintisi)
    sətirlər.append("")
    if yer == k.baş + 1:
        sətirlər = sətirlər[1:]          # başlığın dərhal altında boşluq yox
    r.əlavə(yer, sətirlər)


def _göstər_sətirləri(çağırış: str, g: int) -> list[str]:
    """Yeni `göstər()` — vidjet `sütun` qabında."""
    return (_girintilə(["göstər()"], g)
            + _girintilə(["qaytar vidjet.sütun(boşluq: 12, məzmun: ["],
                         g + GİRİNTİ)
            + _çağırış_sətirləri(çağırış, g + 2 * GİRİNTİ)
            + _girintilə(["])", ], g + GİRİNTİ)
            + _girintilə(["son"], g))


def _göstər_sətirlərinin_etiketləri(n: int) -> list[str | None]:
    return [YENİ, YENİ, ÇAĞIRIŞ] + [YENİ] * (n - 3)


def _son_kod_simvolu(t: Mətn, son: int, baş: int = 0) -> int | None:
    """`son` mövqeyindən geriyə ilk boşluq olmayan KOD simvolu."""
    for j in range(son - 1, baş - 1, -1):
        if t.x[j] == KOD and not t.mətn[j].isspace():
            return j
    return None


def _növbəti_kod_simvolu(t: Mətn, baş: int) -> int | None:
    for j in range(baş, len(t.mətn)):
        if t.x[j] == KOD and not t.mətn[j].isspace():
            return j
    return None


def _sütun(t: Mətn, mövqe: int) -> tuple[int, int]:
    s = t.sətir_nömrəsi(mövqe)
    return s, mövqe - t.başlar[s]


def _vergüllə(t: Mətn, mövqe: int) -> tuple[int, str]:
    """`mövqe`-dəki simvoldan sonra vergül qoyulmuş sətir."""
    s, sütun = _sütun(t, mövqe)
    mətn = t.sətirlər[s]
    return s, mətn[:sütun + 1] + "," + mətn[sütun + 1:]


def _göstərə_yerləşdir(r: _Redaktə, k: Komponent, çağırış: str,
                       kursor: int | None) -> None:
    """Vidjet çağırışını `göstər()`-in qaytardığı ifadəyə qoyur."""
    t = r.t
    g = k.göstər()
    assert g is not None
    bağlı = g.son > g.baş and t.ilk_söz(g.son) == "son"
    gövdə_sonu = g.son if bağlı else g.son + 1
    gövdə_girintisi = k.üzv_girintisi + GİRİNTİ
    for j in range(g.baş + 1, gövdə_sonu):
        if t.kod_sətiridir(j):
            gövdə_girintisi = girinti(t.sətirlər[j])
            break

    # Sonuncu `qaytar` sətri
    q = None
    for j in range(g.baş + 1, gövdə_sonu):
        if (t.ilk_söz(j) == "qaytar"
                and girinti(t.sətirlər[j]) == gövdə_girintisi):
            q = j
    if q is None:
        # Gövdədə `qaytar` yoxdur — yenisini yazırıq
        sətirlər = _göstər_sətirləri(çağırış, k.üzv_girintisi)[1:-1]
        r.əlavə(gövdə_sonu, sətirlər,
                etiketlər=[YENİ, ÇAĞIRIŞ] + [YENİ] * (len(sətirlər) - 2))
        return

    qaytar_sətri = t.sətirlər[q]
    baş = t.başlar[q] + qaytar_sətri.index("qaytar") + len("qaytar")
    son = t.başlar[gövdə_sonu - 1] + len(t.sətirlər[gövdə_sonu - 1])
    ilk = _növbəti_kod_simvolu(t, baş)
    if ilk is None or ilk >= son:
        return
    jsx = t.mətn[ilk] == "<"

    # 1. Kursor göstər() daxilində boş sətirdədirsə — oraya
    if kursor is not None and _kursora_yerləşdir(r, çağırış, kursor, q,
                                                 gövdə_sonu, ilk, jsx):
        return

    # 2. JSX — kök teqin bağlanışından əvvəl
    if jsx:
        for j in range(gövdə_sonu - 1, q - 1, -1):
            if not t.kod_sətiridir(j) and j != q:
                continue
            s = t.sətirlər[j]
            if s.lstrip().startswith("</") and j != q:
                g_j = girinti(s) + GİRİNTİ
                yeni = _çağırış_sətirləri(çağırış, g_j, jsx=True)
                r.əlavə(j, yeni, etiketlər=_çağırış_etiketləri(len(yeni)))
                return
            i = s.rfind("</")
            if i > 0 and (j != q or i > s.index("qaytar")):
                yeni = ([s[:i].rstrip()]
                        + _çağırış_sətirləri(çağırış,
                                             girinti(s) + GİRİNTİ,
                                             jsx=True)
                        + [" " * girinti(s) + s[i:]])
                r.əlavə(j, yeni, silinən=1,
                        etiketlər=[None] + _çağırış_etiketləri(
                            len(yeni) - 2) + [None])
                return
            break

    # 3. `məzmun: [ … ]` siyahısı
    for a in re.finditer(r"\bməzmun\s*:\s*\[", t.mətn[baş:son]):
        açan = baş + a.end() - 1
        if t.x[baş + a.start()] != KOD:
            continue
        bağlayan = uyğun_bağlayan(t, açan)
        if bağlayan is None or bağlayan > son:
            continue
        _siyahıya_yerləşdir(r, çağırış, açan, bağlayan)
        return

    # 4. Başqa ifadə — `vidjet.sütun(...)` qabına bükülür
    ifadə_sətirləri = [t.sətirlər[j] for j in range(q, gövdə_sonu)]
    qi = girinti(qaytar_sətri)
    ilk_sətir = t.mətn[ilk:t.başlar[q] + len(qaytar_sətri)]
    son_kod = _son_kod_simvolu(t, son, ilk)
    yeni = [" " * qi + "qaytar vidjet.sütun(boşluq: 12, məzmun: ["]
    if len(ifadə_sətirləri) == 1:
        yeni.append(" " * (qi + GİRİNTİ) + ilk_sətir.rstrip() + ",")
    else:
        _, vergüllü = _vergüllə(t, son_kod) if son_kod is not None \
            else (0, ifadə_sətirləri[-1])
        yeni.append(" " * (qi + GİRİNTİ) + ilk_sətir.rstrip())
        yeni += ifadə_sətirləri[1:-1]
        yeni.append(vergüllü)
    çağ = _çağırış_sətirləri(çağırış, qi + GİRİNTİ)
    yeni += çağ + [" " * qi + "])"]
    etiketlər: list[str | None] = [YENİ] + [None] * (
        len(yeni) - len(çağ) - 2) + _çağırış_etiketləri(len(çağ)) + [YENİ]
    r.əlavə(q, yeni, silinən=gövdə_sonu - q, etiketlər=etiketlər)


def _son_elementin_başı(t: Mətn, açan: int, son: int) -> int:
    """Siyahının sonuncu elementinin ilk simvolu (dərinlik 0 vergüldən)."""
    dərinlik = 0
    baş = açan + 1
    for j in range(açan + 1, son + 1):
        if t.x[j] != KOD:
            continue
        c = t.mətn[j]
        if c in "([{":
            dərinlik += 1
        elif c in ")]}":
            dərinlik -= 1
        elif c == "," and dərinlik == 0 and j < son:
            baş = j + 1
    n = _növbəti_kod_simvolu(t, baş)
    return n if n is not None and n <= son else son


def _siyahıya_yerləşdir(r: _Redaktə, çağırış: str, açan: int,
                        bağlayan: int) -> None:
    t = r.t
    s_açan, _ = _sütun(t, açan)
    s_bağ, sütun_bağ = _sütun(t, bağlayan)
    açan_girintisi = girinti(t.sətirlər[s_açan])
    son = _son_kod_simvolu(t, bağlayan, açan + 1)
    bağlayan_sətir_başındadır = not t.sətirlər[s_bağ][:sütun_bağ].strip()

    if son is None:
        # Boş siyahı: `[]` → `[\n    çağırış\n]`
        if s_açan == s_bağ:
            sətir = t.sətirlər[s_açan]
            _, sütun_açan = _sütun(t, açan)
            yeni = ([sətir[:sütun_açan + 1]]
                    + _çağırış_sətirləri(çağırış,
                                         açan_girintisi + GİRİNTİ)
                    + [" " * açan_girintisi + sətir[sütun_bağ:]])
            r.əlavə(s_açan, yeni, silinən=1,
                    etiketlər=[None] + _çağırış_etiketləri(
                        len(yeni) - 2) + [None])
        else:
            g = girinti(t.sətirlər[s_bağ]) + GİRİNTİ \
                if bağlayan_sətir_başındadır else açan_girintisi + GİRİNTİ
            yeni = _çağırış_sətirləri(çağırış, g)
            r.əlavə(s_bağ if bağlayan_sətir_başındadır else s_açan + 1,
                    yeni, etiketlər=_çağırış_etiketləri(len(yeni)))
        return

    s_son, _ = _sütun(t, son)
    vergül_lazım = t.mətn[son] != ","
    s_element, _ = _sütun(t, _son_elementin_başı(t, açan, son))
    element_girintisi = (girinti(t.sətirlər[s_element])
                         if s_element != s_açan
                         else açan_girintisi + GİRİNTİ)
    if bağlayan_sətir_başındadır and s_son != s_bağ:
        if vergül_lazım:
            _, vergüllü = _vergüllə(t, son)
            r.əlavə(s_son, [vergüllü], silinən=1, etiketlər=[None])
        yeni = _çağırış_sətirləri(çağırış, element_girintisi)
        r.əlavə(s_bağ, yeni, etiketlər=_çağırış_etiketləri(len(yeni)))
        return

    # `]` sonuncu elementlə eyni sətirdədir: `…("a")])`
    sətir = t.sətirlər[s_bağ]
    _, sütun_son = _sütun(t, son)
    baş_hissə = sətir[:sütun_son + 1] + ("," if vergül_lazım else "")
    if s_son != s_bağ:
        # Sonuncu element başqa sətirdədir, `]` isə nəyinsə arxasında
        if vergül_lazım:
            _, vergüllü = _vergüllə(t, son)
            r.əlavə(s_son, [vergüllü], silinən=1, etiketlər=[None])
        baş_hissə = sətir[:sütun_bağ].rstrip()
        yeni = ([baş_hissə] if baş_hissə.strip() else []) \
            + _çağırış_sətirləri(çağırış, element_girintisi) \
            + [" " * açan_girintisi + sətir[sütun_bağ:]]
        etiketlər = ([None] if baş_hissə.strip() else []) \
            + _çağırış_etiketləri(len(yeni) - 1
                                  - (1 if baş_hissə.strip() else 0)) \
            + [None]
        r.əlavə(s_bağ, yeni, silinən=1, etiketlər=etiketlər)
        return
    yeni = ([baş_hissə]
            + _çağırış_sətirləri(çağırış, element_girintisi)
            + [" " * açan_girintisi + sətir[sütun_bağ:]])
    r.əlavə(s_bağ, yeni, silinən=1,
            etiketlər=[None] + _çağırış_etiketləri(len(yeni) - 2)
            + [None])


def _kursora_yerləşdir(r: _Redaktə, çağırış: str, kursor: int, q: int,
                       gövdə_sonu: int, ilk: int, jsx: bool) -> bool:
    """Kursor `qaytar` ifadəsinin içində BOŞ sətirdədirsə — oraya."""
    t = r.t
    s = t.sətir_nömrəsi(kursor)
    if not (q < s < gövdə_sonu) or not boşdur(t.sətirlər[s]):
        return False
    # Kursora qədər açıq qalan mötərizələr
    yığın: list[str] = []
    for j in range(ilk, t.başlar[s]):
        if t.x[j] != KOD:
            continue
        c = t.mətn[j]
        if c in "([{":
            yığın.append(c)
        elif c in ")]}" and yığın:
            yığın.pop()
    g = len(t.sətirlər[s])
    if g == 0:
        for j in range(s + 1, gövdə_sonu):
            if not boşdur(t.sətirlər[j]):
                g = girinti(t.sətirlər[j])
                if t.sətirlər[j].lstrip()[:1] in ("]", ")", "<"):
                    if t.sətirlər[j].lstrip().startswith("</") or \
                            t.sətirlər[j].lstrip()[:1] in "])":
                        g += GİRİNTİ
                break
    if yığın and yığın[-1] == "[":
        əvvəlki = _son_kod_simvolu(t, t.başlar[s], ilk)
        sonrakı = _növbəti_kod_simvolu(t, t.başlar[s])
        if əvvəlki is not None and t.mətn[əvvəlki] not in "[,":
            sətir_no, vergüllü = _vergüllə(t, əvvəlki)
            r.əlavə(sətir_no, [vergüllü], silinən=1, etiketlər=[None])
        vergül = sonrakı is not None and t.mətn[sonrakı] not in "],"
        yeni = _çağırış_sətirləri(çağırış, g, vergül=vergül)
        r.əlavə(s, yeni, silinən=1,
                etiketlər=_çağırış_etiketləri(len(yeni)))
        return True
    if jsx and not yığın:
        yeni = _çağırış_sətirləri(çağırış, g, jsx=True)
        r.əlavə(s, yeni, silinən=1,
                etiketlər=_çağırış_etiketləri(len(yeni)))
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════
#  Komponent iskeleti — faylda komponent yoxdursa
# ═══════════════════════════════════════════════════════════════════════

def _boş_sinif_adı(t: Mətn, baza: str = "Tətbiq") -> str:
    tutulmuş = sinif_adları(t)
    if baza not in tutulmuş:
        return baza
    n = 2
    while f"{baza}{n}" in tutulmuş:
        n += 1
    return f"{baza}{n}"


def _iskelet(ad: str, h: Hazır) -> tuple[list[str], list[str | None]]:
    sətirlər = [f"komponent {ad}"]
    etiketlər: list[str | None] = [YENİ]
    for _, v in h.vəziyyətlər:
        sətirlər += _girintilə([v], GİRİNTİ)
    if h.vəziyyətlər:
        sətirlər.append("")
    for _, m in h.metodlar:
        sətirlər += _girintilə(m, GİRİNTİ) + [""]
    etiketlər += [YENİ] * (len(sətirlər) - 1)
    göstər = _göstər_sətirləri(h.çağırış, GİRİNTİ)
    sətirlər += göstər + ["son"]
    etiketlər += _göstər_sətirlərinin_etiketləri(len(göstər)) + [YENİ]
    return sətirlər, etiketlər


def _əsas_funksiya(ad: str) -> list[str]:
    return [
        "funksiya əsas()",
        f'    dəyişən p = yeni pəncərə.Pəncərə("{ad}", 800, 600)',
        f"    p.məzmun(<{ad} />)",
        "    p.göstər()",
        "    pəncərə.işlət()",
        "son",
    ]


# ═══════════════════════════════════════════════════════════════════════
#  Əsas əməliyyatlar
# ═══════════════════════════════════════════════════════════════════════

def _mesaj(vidjet_adı: str, əlavələr: list[str], idxallar: list[str],
           çağırış_əlavə: bool = True) -> str:
    hissələr = []
    if çağırış_əlavə:
        hissələr.append(f"`{vidjet_adı}` əlavə edildi")
    if əlavələr:
        hissələr.append("yazıldı: " + ", ".join(əlavələr))
    if idxallar:
        hissələr.append(", ".join(f"`gətir {m}`" for m in idxallar))
    return " · ".join(hissələr) if hissələr else "Hər şey yerindədir"


def vidjet_əlavə_et(mətn: str, vidjet_adı: str, kursor: int | None = None,
                    dəyişən_adı: str | None = None) -> Nəticə:
    """
    Paletdən iki klik: vidjet + onun işləməsi üçün lazım olan HƏR ŞEY.
    """
    m = məlumat(vidjet_adı)
    t = Mətn(mətn)
    r = _Redaktə(t)
    k = komponent_tap(t, kursor)
    əlavələr: list[str] = []
    idxallar = ["vidjet"]

    if k is None:
        h = hazırla(m, ad_seç(m, set(), dəyişən_adı), set())
        komp_adı = _boş_sinif_adı(t)
        sətirlər, etiketlər = _iskelet(komp_adı, h)
        son_gətir, ilk_kod = _idxal_bölməsi(t)
        if ilk_kod is None:
            # Fayl boşdur (yalnız `gətir` və şərh) — işə salına bilən
            # tətbiq qururuq: komponent + `əsas()` pəncərəsi
            idxallar.append("pəncərə")
            əsas = _əsas_funksiya(komp_adı)
            sətirlər = [""] + sətirlər + [""] + əsas
            etiketlər = [YENİ] + etiketlər + [YENİ] * (len(əsas) + 1)
            son = _son_dolu_sətir(t)
            r.əlavə(son + 1, sətirlər, etiketlər=etiketlər)
            əlavələr.append(f"komponent {komp_adı}")
            əlavələr.append("funksiya əsas")
        else:
            r.əlavə(ilk_kod, sətirlər + [""], etiketlər=etiketlər + [YENİ])
            əlavələr.append(f"komponent {komp_adı}")
        əlavələr += [f"vəziyyət {a}" for a, _ in h.vəziyyətlər]
        əlavələr += [f"metod {a}" for a, _ in h.metodlar]
    else:
        mövcud = k.adlar() | _komponent_istinadları(t, k)
        h = hazırla(m, ad_seç(m, mövcud, dəyişən_adı), mövcud)
        _vəziyyətləri_yerləşdir(r, k, [v for _, v in h.vəziyyətlər])
        if k.göstər() is not None:
            _metodları_yerləşdir(r, k, [b for _, b in h.metodlar],
                                 _metodların_yeri(t, k))
            _göstərə_yerləşdir(r, k, h.çağırış, kursor)
        else:
            yer = _gövdənin_sonu(t, k)
            _metodları_yerləşdir(r, k, [b for _, b in h.metodlar], yer)
            göstər = _göstər_sətirləri(h.çağırış, k.üzv_girintisi)
            r.əlavə(yer, [""] + göstər,
                    etiketlər=[YENİ] + _göstər_sətirlərinin_etiketləri(
                        len(göstər)))
            əlavələr.append("göstər()")
        əlavələr = ([f"vəziyyət {a}" for a, _ in h.vəziyyətlər]
                    + [f"metod {a}" for a, _ in h.metodlar] + əlavələr)

    əlavə_idxallar = _idxal_düzəlişi(r, idxallar)
    yeni, yeni_kursor, aralıqlar = r.tətbiq_et()
    return Nəticə(yeni, yeni_kursor if yeni_kursor is not None else 0,
                  aralıqlar, _mesaj(m.ad, əlavələr, əlavə_idxallar),
                  əlavələr + [f"gətir {a}" for a in əlavə_idxallar])


def nümunə_hazırla(mətn: str, vidjet_adı: str,
                   kursor: int | None = None) -> str:
    """
    Paletdən BİR klik: yalnız çağırış mətni, təkrarlanmayan adla.
    Sonra çağırışın üzərinə iki klik `çağırışı_tamamla()`-nı işlədir.
    """
    m = məlumat(vidjet_adı)
    t = Mətn(mətn)
    k = komponent_tap(t, kursor)
    mövcud: set[str] = set()
    if k is not None:
        mövcud = k.adlar() | _komponent_istinadları(t, k)
    return hazırla(m, ad_seç(m, mövcud), mövcud).çağırış


def _çağırış_istinadları(t: Mətn, baş: int, son: int) -> list[str]:
    parça = "".join(c if t.x[baş + i] == KOD else " "
                    for i, c in enumerate(t.mətn[baş:son]))
    return _ÖZÜ_İSTİNADI.findall(parça)


def _adı_çıxar(m: V.Məlumat, istinadlar: list[str],
               çağırış: str) -> str | None:
    """Mövcud çağırışdakı `özü.x…` istinadlarından skelet adını tapır."""
    şablonlar = sorted(_şablon_adları(m),
                       key=lambda ş: len(ş.replace("{ad}", "")),
                       reverse=True)
    for ş in şablonlar:
        ön, son = ş.split("{ad}", 1)
        for i in istinadlar:
            if (i.startswith(ön) and i.endswith(son)
                    and len(i) > len(ön) + len(son)):
                ad = i[len(ön):len(i) - len(son)] if son else i[len(ön):]
                if ad_düzgündür(ad):
                    return ad
    a = re.search(r'(?<!\w)ad\s*:\s*"([^"{}\\]+)"', çağırış)
    if a and ad_düzgündür(a.group(1)) and "{ad}" in m.nümunə:
        return a.group(1)
    return None


@dataclass
class _Təhlil:
    """Mövcud çağırışın vəziyyəti — nə çatışmır."""
    m: V.Məlumat
    k: Komponent | None
    h: Hazır | None
    vəziyyətlər: list[tuple[str, str]]
    metodlar: list[tuple[str, list[str]]]
    arqumentlər: list[str]


def _təhlil_et(t: Mətn, ç) -> _Təhlil:
    m = məlumat(ç.ad)
    k = None
    for kk in komponentləri_tap(t):
        son = kk.son if kk.son is not None else len(t.sətirlər)
        if kk.baş <= t.sətir_nömrəsi(ç.baş) <= son:
            k = kk
    if k is None or not _ad_lazımdır(m):
        return _Təhlil(m, k, None, [], [], [])
    son = (ç.son + 1) if ç.son is not None else len(t.mətn)
    çağırış = t.mətn[ç.baş:son]
    istinadlar = _çağırış_istinadları(t, ç.baş, son)
    təyin = k.adlar()
    ad = _adı_çıxar(m, istinadlar, çağırış)
    if ad is None:
        ad = ad_seç(m, təyin | _komponent_istinadları(t, k))
    h = hazırla(m, ad, təyin, adları_dəyiş=not istinadlar)
    vəziyyətlər = [(a, v) for a, v in h.vəziyyətlər if a not in təyin]
    metodlar = [(a, b) for a, b in h.metodlar if a not in təyin]
    arqumentlər: list[str] = []
    if not istinadlar:
        for p, d in re.findall(r"(?<![\w.])([^\W\d]\w*)\s*:\s*(özü\.\w+)",
                               h.çağırış):
            if not re.search(rf"(?<![\w.]){re.escape(p)}\s*:", çağırış):
                arqumentlər.append(f"{p}: {d}")
        if not arqumentlər:
            # Çağırış özü heç nəyə bağlanmayıb və bağlana da bilmir —
            # yaradılan üzvlər istifadəsiz qalardı
            vəziyyətlər, metodlar = [], []
    return _Təhlil(m, k, h, vəziyyətlər, metodlar, arqumentlər)


def çağırışı_tamamla(mətn: str, kursor: int) -> Nəticə:
    """
    Redaktorda `vidjet.ad(...)` çağırışının üzərinə iki klik: çatışmayan
    vəziyyət, idarəedici, hadisə bağlantısı və `gətir vidjet` yazılır.
    """
    t = Mətn(mətn)
    ç = çağırış_tap(t, kursor)
    if ç is None:
        raise SkeletXətası(
            "Kursor `vidjet.…(…)` çağırışının üzərində deyil")
    th = _təhlil_et(t, ç)
    r = _Redaktə(t)
    əlavələr: list[str] = []
    if th.k is not None and th.h is not None:
        _vəziyyətləri_yerləşdir(r, th.k, [v for _, v in th.vəziyyətlər])
        _metodları_yerləşdir(r, th.k, [b for _, b in th.metodlar],
                             _metodların_yeri(t, th.k))
        əlavələr += [f"vəziyyət {a}" for a, _ in th.vəziyyətlər]
        əlavələr += [f"metod {a}" for a, _ in th.metodlar]
        if th.arqumentlər and ç.son is not None:
            s, sütun = _sütun(t, ç.son)
            sətir = t.sətirlər[s]
            baş_s, b = _sütun(t, ç.baş)
            if baş_s == s:
                hissələr = arqument_əlavə_et(
                    sətir[b:sütun + 1], th.arqumentlər,
                    əsas_sütun=b).split("\n")
                hissələr = ([sətir[:b] + hissələr[0]]
                            + [" " * b + h for h in hissələr[1:]])
            else:
                hissələr = arqument_əlavə_et(
                    sətir[:sütun + 1], th.arqumentlər,
                    hiza=girinti(sətir)).split("\n")
            hissələr[-1] += sətir[sütun + 1:]
            r.əlavə(s, hissələr, silinən=1,
                    etiketlər=[YENİ] * len(hissələr))
            əlavələr += [a.split(":")[0] + ":" for a in th.arqumentlər]
    elif th.k is None and _ad_lazımdır(th.m):
        idx = _idxal_düzəlişi(r, ["vidjet"])
        yeni, _, aralıqlar = r.tətbiq_et()
        return Nəticə(yeni, kursor, aralıqlar,
                      "Çağırış komponentin içində deyil — vəziyyət və "
                      "idarəedici yalnız `komponent` daxilində yazılır"
                      + ("" if not idx else " · `gətir vidjet`"),
                      [f"gətir {a}" for a in idx], bool(idx))
    idx = _idxal_düzəlişi(r, ["vidjet"])
    if not r.düzəlişlər:
        return Nəticə(mətn, kursor, [], "Hər şey yerindədir — "
                      f"`{th.m.ad}` işləməyə hazırdır", [], False)
    yeni, _, aralıqlar = r.tətbiq_et()
    # Kursor eyni çağırışın üzərində qalsın: əvvəlinə əlavə olunan
    # sətirlərin uzunluğu qədər sürüşür
    sürüşmə = 0
    ç_sətri = t.sətir_nömrəsi(ç.baş)
    for d in r.düzəlişlər:
        if d.baş <= ç_sətri and d.silinən == 0:
            sürüşmə += sum(len(s) + 1 for s in d.yeni)
    gözlənən = ç.baş + sürüşmə
    yeni_t = Mətn(yeni)
    namizədlər = [c.baş for c in vidjet_çağırışları(yeni_t)
                  if c.ad == ç.ad]
    if namizədlər:
        gözlənən = min(namizədlər, key=lambda b: abs(b - gözlənən))
    yeni_kursor = gözlənən + (kursor - ç.baş)
    return Nəticə(yeni, yeni_kursor, aralıqlar,
                  _mesaj(th.m.ad, əlavələr, idx, çağırış_əlavə=False),
                  əlavələr + [f"gətir {a}" for a in idx])


def _beynəlxalq(ad: str) -> str:
    from alqor.vidjet import BEYNƏLXALQ_ADLAR
    return BEYNƏLXALQ_ADLAR.get(ad, ad)


def elementlər(mətn: str) -> list[dict]:
    """Fayldakı vidjet çağırışları və hər birində nəyin çatışmadığı."""
    t = Mətn(mətn)
    nəticə: list[dict] = []
    for ç in vidjet_çağırışları(t):
        s, sütun = _sütun(t, ç.baş)
        try:
            th = _təhlil_et(t, ç)
        except SkeletXətası:
            nəticə.append({"ad": ç.ad, "sətir": s + 1, "sütun": sütun + 1,
                           "mövqe": ç.ad_başı, "naməlum": True,
                           "çatışmır": [], "komponent": None})
            continue
        çatışmır = ([a for a, _ in th.vəziyyətlər]
                    + [a for a, _ in th.metodlar]
                    + [a.split(":")[0] + ":" for a in th.arqumentlər])
        nəticə.append({
            "ad": ç.ad, "sətir": s + 1, "sütun": sütun + 1,
            "beynəlxalqAd": _beynəlxalq(ç.ad),
            "mövqe": ç.ad_başı, "naməlum": False, "çatışmır": çatışmır,
            "komponent": th.k.ad if th.k else None,
            "kateqoriya": th.m.kateqoriya,
        })
    return nəticə
