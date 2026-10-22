"""
Alqor — `alqorlint`: statik təhlil (linter). Spesifikasiya § 13.4.

    alqor lint .                     # və ya ./alqorlint .
    alqor lint --düzəlt .            # avtomatik düzəldilənləri düzəlt
    alqor lint --sərtlik sərt .
    alqor lint --qaydalar            # bütün qaydalar
    alqor lint --json .

Tip yoxlayıcısının tapdıqlarına (`alqor yoxla`) ƏLAVƏ olaraq üslub,
mürəkkəblik, təhlükəsizlik, performans və əlçatanlıq qaydaları yoxlanır.
Kodlar `ALQ-Y…` ilə başlayır; hər qaydanın oxunaqlı adı da var
(`istifadəsiz-idxal`) — konfiqurasiyada ikisi də işlənə bilər.

Konfiqurasiya (`layihe.alq`):

    [lint]
    sərtlik = "normal"            # sərbəst | normal | sərt
    söndür = ["uzun-sətir"]       # ad, kod və ya "kateqoriya-*"
    xəta = ["təhlükəsizlik-*"]    # xəbərdarlığı xətaya qaldır
    maks_funksiya_sətri = 50
    maks_dərinlik = 4
    maks_sətir = 100
    maks_parametr = 6

Söndürmə şərhləri:

    dəyişən parol = "test"        // lint: söndür gizli-açar
    // alqor: lint-söndür adlandırma-*      (bütün fayl üçün)
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Iterator

from . import aac as A
from .lekser import Lekser
from .menbe import Mənbə
from .parser import Parser
from .token import Yer
from .xeta import Diaqnostika, Səviyyə, XətaToplayıcı


# ═══════════════════════════════════════════════════════════════════════
#  Qaydalar
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Qayda:
    kod: str
    ad: str
    kateqoriya: str
    səviyyə: str            # "xəta" | "xəbərdarlıq" | "məlumat"
    təsvir: str
    düzəldilir: bool = False


QAYDALAR: list[Qayda] = [
    # İstifadəsiz
    Qayda("ALQ-Y001", "istifadəsiz-dəyişən", "istifadəsiz", "xəbərdarlıq",
          "elan olunub, heç yerdə işlənməyən dəyişən və ya parametr"),
    Qayda("ALQ-Y002", "istifadəsiz-idxal", "istifadəsiz", "xəbərdarlıq",
          "`gətir` ilə idxal olunub, işlənməyən modul", True),
    Qayda("ALQ-Y003", "istifadəsiz-funksiya", "istifadəsiz", "məlumat",
          "heç yerdə çağırılmayan, ixrac olunmayan funksiya"),
    # Adlandırma
    Qayda("ALQ-Y010", "adlandırma-dəyişən", "adlandırma", "xəbərdarlıq",
          "dəyişən, parametr və funksiya adları kiçikDəvəQutusu olmalıdır"),
    Qayda("ALQ-Y011", "adlandırma-tip", "adlandırma", "xəbərdarlıq",
          "sinif, struktur, interfeys, sadalama adları BöyükDəvəQutusu"),
    Qayda("ALQ-Y012", "adlandırma-sabit", "adlandırma", "məlumat",
          "modul səviyyəsində sabitlər BÖYÜK_ALT_XƏTT ilə yazılır"),
    Qayda("ALQ-Y013", "adlandırma-fayl", "adlandırma", "məlumat",
          "fayl adları kiçik hərf və defislə: `verilənlər-bazası.alq`"),
    Qayda("ALQ-Y014", "kölgələmə", "adlandırma", "xəbərdarlıq",
          "daxili blokda xarici adı kölgələyən elan"),
    # Mürəkkəblik
    Qayda("ALQ-Y020", "dərin-iç-içəlik", "mürəkkəblik", "xəbərdarlıq",
          "bloklar çox dərin iç-içədir (maks_dərinlik)"),
    Qayda("ALQ-Y021", "uzun-funksiya", "mürəkkəblik", "xəbərdarlıq",
          "funksiya çox uzundur (maks_funksiya_sətri)"),
    Qayda("ALQ-Y022", "çox-parametr", "mürəkkəblik", "xəbərdarlıq",
          "funksiyanın parametrləri çoxdur (maks_parametr)"),
    Qayda("ALQ-Y023", "uzun-sətir", "mürəkkəblik", "məlumat",
          "sətir çox uzundur (maks_sətir)"),
    # Potensial xəta
    Qayda("ALQ-Y030", "şərtdə-mənimsətmə", "potensial-xəta", "xəta",
          "şərtdə `=` — çox güman ki `==` nəzərdə tutulub"),
    Qayda("ALQ-Y031", "boş-tut", "potensial-xəta", "xəbərdarlıq",
          "boş `tut` bloku xətanı səssizcə udur"),
    Qayda("ALQ-Y032", "özünə-mənimsətmə", "potensial-xəta", "xəbərdarlıq",
          "`x = x` heç nə etmir"),
    Qayda("ALQ-Y033", "özü-ilə-müqayisə", "potensial-xəta", "xəbərdarlıq",
          "`x == x` həmişə eyni nəticəni verir"),
    Qayda("ALQ-Y034", "sabit-şərt", "potensial-xəta", "xəbərdarlıq",
          "şərt həmişə doğru və ya həmişə yanlışdır"),
    Qayda("ALQ-Y035", "əlçatmaz-kod", "potensial-xəta", "xəbərdarlıq",
          "`qaytar`/`at`/`dayan`/`davam et`-dən sonrakı kod heç vaxt "
          "işləmir"),
    Qayda("ALQ-Y036", "təkrar-açar", "potensial-xəta", "xəta",
          "lüğət literalında eyni açar iki dəfə"),
    Qayda("ALQ-Y037", "təkrar-hal", "potensial-xəta", "xəbərdarlıq",
          "`seç` daxilində eyni `hal` iki dəfə"),
    Qayda("ALQ-Y038", "boş-blok", "potensial-xəta", "məlumat",
          "gövdəsi boş `əgər` / dövr"),
    Qayda("ALQ-Y039", "deyil-prioriteti", "potensial-xəta", "xəbərdarlıq",
          "`deyil a == b` = `deyil (a == b)` — mötərizə yazın"),
    # Performans
    Qayda("ALQ-Y040", "dövrdə-mətn-birləşdirmə", "performans",
          "xəbərdarlıq",
          "dövrdə `mətn +=` — hissələri siyahıya yığıb `birləşdir` işlədin"),
    Qayda("ALQ-Y041", "indeksli-dövr", "performans", "məlumat",
          "`hər i üçün 0..<s.uzunluq()` — `hər x üçün s içində` daha "
          "sadədir"),
    # Təhlükəsizlik
    Qayda("ALQ-Y050", "gizli-açar", "təhlükəsizlik", "xəbərdarlıq",
          "kodda parol / token / açar — mühit dəyişəni işlədin"),
    Qayda("ALQ-Y051", "sql-birləşdirmə", "təhlükəsizlik", "xəta",
          "SQL sorğusu mətn birləşdirmə ilə qurulub — parametrlər "
          "işlədin (SQL inyeksiyası)"),
    Qayda("ALQ-Y052", "xam-html", "təhlükəsizlik", "xəbərdarlıq",
          "şablonda `| xam` — qaçışsız HTML (XSS riski)"),
    Qayda("ALQ-Y053", "əmr-birləşdirmə", "təhlükəsizlik", "xəta",
          "sistem əmri mətn birləşdirmə ilə qurulub (əmr inyeksiyası)"),
    # Üslub
    Qayda("ALQ-Y060", "qarışıq-prioritet", "üslub", "xəbərdarlıq",
          "`və` ilə `və ya` (və ya `??`) mötərizəsiz qarışıb"),
    Qayda("ALQ-Y061", "gətir-ulduz", "üslub", "xəbərdarlıq",
          "`gətir modul.*` adları gizli gətirir — açıq siyahı yazın"),
    Qayda("ALQ-Y062", "məntiqlə-müqayisə", "üslub", "xəbərdarlıq",
          "`x == doğru` əvəzinə `x`, `x == yanlış` əvəzinə `deyil x`", True),
    Qayda("ALQ-Y063", "boşla-müqayisə", "üslub", "məlumat",
          "`x == boş` əvəzinə `x boşdur`", True),
    # Əlçatanlıq
    Qayda("ALQ-Y070", "şəkil-alt", "əlçatanlıq", "xəbərdarlıq",
          "`<img>` / `vidjet.şəkil` alternativ mətnsiz"),
    Qayda("ALQ-Y071", "mətnsiz-düymə", "əlçatanlıq", "xəbərdarlıq",
          "düymədə nə mətn, nə də `aria-label` var"),
    Qayda("ALQ-Y072", "etiketsiz-sahə", "əlçatanlıq", "məlumat",
          "`<input>` üçün `aria-label` və ya `id` (etiket) yoxdur"),
]
QAYDA_ADI = {q.ad: q for q in QAYDALAR}
QAYDA_KODU = {q.kod: q for q in QAYDALAR}

STANDART_AYAR = {
    "sərtlik": "normal", "söndür": [], "xəta": [],
    "maks_funksiya_sətri": 50, "maks_dərinlik": 4, "maks_sətir": 100,
    "maks_parametr": 6,
}


# ═══════════════════════════════════════════════════════════════════════
#  Nəticə
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Tapıntı:
    qayda: Qayda
    yer: Yer | None
    qeyd: str
    köməklər: list[str] = field(default_factory=list)
    düzəliş: tuple[int, int, str] | None = None    # (başlanğıc, son, yeni)
    səviyyə: str = ""

    def diaqnostika(self) -> Diaqnostika:
        s = {"xəta": Səviyyə.XETA, "xəbərdarlıq": Səviyyə.XEBERDARLIQ,
             "məlumat": Səviyyə.MELUMAT}[self.səviyyə or
                                         self.qayda.səviyyə]
        k = list(self.köməklər)
        if self.düzəliş:
            k.append("`alqor lint --düzəlt` avtomatik düzəldir")
        k.append(f"söndürmək: // lint: söndür {self.qayda.ad}")
        return Diaqnostika(self.qayda.kod,
                           f"{self.qayda.təsvir[0].upper()}"
                           f"{self.qayda.təsvir[1:]} [{self.qayda.ad}]",
                           self.yer, s, self.qeyd, k)

    def lüğət(self) -> dict:
        d: dict[str, Any] = {"kod": self.qayda.kod, "ad": self.qayda.ad,
                             "kateqoriya": self.qayda.kateqoriya,
                             "səviyyə": self.səviyyə or self.qayda.səviyyə,
                             "mesaj": self.qeyd}
        if self.yer is not None:
            s, c = self.yer.mənbə.sətir_sütun(self.yer.başlanğıc)
            d.update({"sətir": s, "sütun": c, "uzunluq": self.yer.uzunluq})
        if self.düzəliş:
            d["düzəldilir"] = True
        return d


# ═══════════════════════════════════════════════════════════════════════
#  AST gəzintisi
# ═══════════════════════════════════════════════════════════════════════

def uşaqlar(q: Any) -> Iterator[Any]:
    """Qovşağın bütün alt qovşaqları (dataclass sahələri üzrə)."""
    if not is_dataclass(q):
        return
    for f in fields(q):
        if f.name == "yer":
            continue
        yield from _açıl(getattr(q, f.name))


def _açıl(v: Any) -> Iterator[Any]:
    if is_dataclass(v) and not isinstance(v, type):
        yield v
    elif isinstance(v, (list, tuple)):
        for e in v:
            yield from _açıl(e)


def hamısı(q: Any) -> Iterator[Any]:
    yield q
    for u in uşaqlar(q):
        yield from hamısı(u)


_BLOK_SAHƏLƏRİ = ("gövdə", "yoxsa", "nəhayət", "digər")


def _bloklar(c: Any) -> list[list]:
    """Cümlənin daxili cümlə blokları."""
    n = []
    for ad in _BLOK_SAHƏLƏRİ:
        v = getattr(c, ad, None)
        if isinstance(v, list) and (not v or isinstance(v[0], A.Cümlə)):
            n.append(v)
    if isinstance(c, A.Şərt):
        n.extend(g for _, g in c.budaqlar)
    if isinstance(c, A.Seç):
        n.extend(h.gövdə for h in c.hallar)
    if isinstance(c, A.Cəhd):
        n.extend(t.gövdə for t in c.tutmalar)
    return n


# ═══════════════════════════════════════════════════════════════════════
#  Yoxlayıcı
# ═══════════════════════════════════════════════════════════════════════

_KİÇİK_DƏVƏ = re.compile(r"^_*[a-zəıöüğşçi][A-Za-zƏəIıİiÖöÜüĞğŞşÇç0-9]*$")
_BÖYÜK_DƏVƏ = re.compile(r"^_*[A-ZƏIİÖÜĞŞÇ][A-Za-zƏəIıİiÖöÜüĞğŞşÇç0-9]*$")
_BÖYÜK_SABİT = re.compile(r"^_*[A-ZƏIİÖÜĞŞÇ][A-ZƏIİÖÜĞŞÇ0-9_]*$")
_GİZLİ_AD = re.compile(
    r"(parol|şifrə|sifre|password|passwd|secret|sirr|token|api_?açar|"
    r"api_?key|apiAçar|apiKey|gizliAçar|accessKey|privateKey)", re.I)
_GİZLİ_DƏYƏR = re.compile(
    r"(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|sk_live_[0-9a-zA-Z]{8,}"
    r"|ghp_[0-9A-Za-z]{30,}|xox[baprs]-[0-9A-Za-z-]{10,}|AIza[0-9A-Za-z_-]{30,})")
_SQL_METODLARI = {"sorğu", "icra", "birSətir", "birDəyər", "skript"}
_SQL_SÖZLƏRİ = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|WHERE|FROM)\b",
                          re.I)
_ƏMR_METODLARI = {("sistem", "əmr"), ("sistem", "icra"), ("sistem", "qabıq")}


class Yoxlayıcı:
    def __init__(self, mənbə: Mənbə, ağac: Any, ayar: dict,
                 yol: str = ""):
        self.s = mənbə
        self.ağac = getattr(ağac, "gövdə", ağac)
        self.ayar = ayar
        self.yol = yol
        self.tapıntılar: list[Tapıntı] = []
        self.mətn: str = mənbə.mətn

    # ── Köməkçilər ────────────────────────────────────────────────────
    def bildir(self, ad: str, yer: Yer | None, qeyd: str,
               *köməklər: str, düzəliş=None) -> None:
        self.tapıntılar.append(Tapıntı(QAYDA_ADI[ad], yer, qeyd,
                                       list(köməklər), düzəliş))

    def _ad_yeri(self, q: Any, ad: str) -> Yer | None:
        """Elanın içində adın özünün yeri (xətt yalnız adın altında)."""
        y = getattr(q, "yer", None)
        if y is None:
            return None
        parça = self.mətn[y.başlanğıc:y.son]
        m = re.search(rf"(?<![\w]){re.escape(ad)}(?![\w])", parça)
        if m is None:
            return y
        return Yer(self.s, y.başlanğıc + m.start(), len(ad))

    def _aralıq(self, q: Any) -> tuple[int, int] | None:
        """İfadənin bütün mətn aralığı (ikili ifadənin `yer`-i yalnız
        operatordur — alt qovşaqlar da nəzərə alınır)."""
        b = e = None
        for x in hamısı(q):
            y = getattr(x, "yer", None)
            if isinstance(y, Yer) and y.mənbə is self.s:
                b = y.başlanğıc if b is None else min(b, y.başlanğıc)
                e = y.son if e is None else max(e, y.son)
        if b is None:
            return None
        # bağlanan mötərizələri tamamla: `al(1)`, `l["a"]`
        dəyişdi = True
        while dəyişdi and e < len(self.mətn):
            dəyişdi = False
            for aç, bağ in ("()", "[]", "{}"):
                if self.mətn[e:e + 1] == bağ and self.mətn.count(
                        aç, b, e) > self.mətn.count(bağ, b, e):
                    e += 1
                    dəyişdi = True
        return b, e

    def _tam_yer(self, q: Any) -> Yer | None:
        a = self._aralıq(q)
        return Yer(self.s, a[0], a[1] - a[0]) if a else None

    def _mətn(self, q: Any) -> str:
        a = self._aralıq(q)
        return self.mətn[a[0]:a[1]] if a else ""

    def _mötərizəlidir(self, q: Any) -> bool:
        a = self._aralıq(q)
        if a is None:
            return False
        i = a[0] - 1
        while i >= 0 and self.mətn[i] in " \t":
            i -= 1
        return i >= 0 and self.mətn[i] == "("

    # ── İşlət ─────────────────────────────────────────────────────────
    def _məntiqdir(self, q: Any) -> bool:
        """İfadə həmişə `məntiq`-dirmi? (`x == doğru` sadələşdirməsi
        yalnız onda təhlükəsizdir — `istənilən` dəyərdə mənası fərqlidir)"""
        if isinstance(q, A.İkili):
            return q.op in ("==", "!=", "<", ">", "<=", ">=", "və", "və ya",
                            "&&", "||")
        if isinstance(q, A.TəkOperand):
            return q.op in ("deyil", "!")
        if isinstance(q, (A.BoşYoxlama, A.Üzvlük, A.TipYoxlama)):
            return True
        if isinstance(q, A.Ad):
            return q.ad in self.məntiq_adları
        return False

    def işlət(self) -> list[Tapıntı]:
        self.məntiq_adları: set[str] = set()
        for q in hamısı_siyahı(self.ağac):
            if isinstance(q, A.DəyişənElanı):
                for b, d in zip(q.bağlamalar, q.dəyərlər or [None] *
                                len(q.bağlamalar)):
                    t = getattr(b, "tip", None)
                    if b.ad and ((isinstance(t, A.TipAdı) and t.yol ==
                                  ["məntiq"] and not t.ixtiyari) or
                                 (t is None and isinstance(d, A.Literal) and
                                  d.növ == "məntiq")):
                        self.məntiq_adları.add(b.ad)
            elif isinstance(q, A.Parametr) and isinstance(q.tip, A.TipAdı) \
                    and q.tip.yol == ["məntiq"] and not q.tip.ixtiyari:
                self.məntiq_adları.add(q.ad)
        self._istifadəsiz_idxal_və_funksiya()
        self._fayl_adı()
        self._sətirlər()
        self._blok_gəz(self.ağac, 0, None, qlobal=True)
        for q in hamısı_siyahı(self.ağac):
            self._qovşaq(q)
        return self.tapıntılar

    # ── İstifadəsiz idxal / funksiya ──────────────────────────────────
    def _istifadəsiz_idxal_və_funksiya(self) -> None:
        istifadə: set[str] = set()
        for q in hamısı_siyahı(self.ağac):
            if isinstance(q, A.Ad):
                istifadə.add(q.ad)
            elif isinstance(q, A.JSXElement):
                istifadə.add(q.ad.split(".")[0])
            elif isinstance(q, A.TipAdı) and q.yol:
                istifadə.add(q.yol[0])
            elif isinstance(q, A.Annotasiya):
                istifadə.add(q.ad.split(".")[0])
            elif isinstance(q, A.İxracSiyahısı):
                istifadə.update(e.ad for e in q.elementlər)
        # şablon mətnlərindəki adlar (`"{x}"` artıq Ad qovşağıdır) və
        # sinif bazaları TipAdı-dır — yuxarıda nəzərə alınıb
        for c in self.ağac:
            if isinstance(c, A.İdxal):
                if c.hamısı or c.elementlər:
                    adlar = [(e.ləqəb or e.ad) for e in c.elementlər]
                    if c.hamısı:
                        yol = ("python:" if c.python else "") + \
                            ".".join(c.yol)
                        self.bildir("gətir-ulduz", c.yer,
                                    f"`gətir {yol}.*`",
                                    "lazım olan adları açıq yazın: "
                                    f"`gətir {yol}.{{a, b}}`")
                        continue
                    if all(a not in istifadə for a in adlar):
                        self._idxal_bildir(c, ", ".join(adlar))
                    continue
                ad = c.ləqəb or (Path(c.mətn_yolu).stem if c.mətn_yolu
                                 else c.yol[-1] if c.yol else "")
                if ad and ad not in istifadə and not ad.startswith("_"):
                    self._idxal_bildir(c, ad)
            elif isinstance(c, A.FunksiyaElanı):
                if (c.ad not in istifadə and c.ad != "əsas" and not c.ixrac
                        and c.görünüş not in ("açıq",)
                        and not c.ad.startswith("_") and not c.annotasiyalar):
                    self.bildir("istifadəsiz-funksiya",
                                self._ad_yeri(c, c.ad),
                                f"`{c.ad}` heç yerdə çağırılmır")

    def _idxal_bildir(self, c: A.İdxal, ad: str) -> None:
        y = c.yer
        b = self.mətn.rfind("\n", 0, y.başlanğıc) + 1
        son = self.mətn.find("\n", y.son)
        son = len(self.mətn) if son < 0 else son + 1
        sətir = self.mətn[b:son]
        düzəliş = None
        if re.fullmatch(r"\s*(gətir|getir)\s+[^;\n]*?(//[^\n]*)?\n?", sətir):
            düzəliş = (b, son, "")
        self.bildir("istifadəsiz-idxal", y, f"`{ad}` işlənmir",
                    "lazım deyilsə sətri silin", düzəliş=düzəliş)

    # ── Fayl və sətir səviyyəsi ───────────────────────────────────────
    def _fayl_adı(self) -> None:
        if not self.yol:
            return
        ad = Path(self.yol).stem
        if not re.fullmatch(r"[a-zəıöüğşç0-9]+(-[a-zəıöüğşç0-9]+)*", ad) \
                and not re.fullmatch(r"\d+-[a-zəıöüğşç0-9-]+", ad):
            self.bildir("adlandırma-fayl", None,
                        f"`{Path(self.yol).name}` → "
                        f"`{_defisli(ad)}{Path(self.yol).suffix}`")

    def _sətirlər(self) -> None:
        maks = int(self.ayar["maks_sətir"])
        ofs = 0
        for sətir in self.mətn.split("\n"):
            if len(sətir.rstrip()) > maks:
                self.bildir("uzun-sətir", Yer(self.s, ofs + maks,
                                              len(sətir) - maks),
                            f"{len(sətir)} simvol (maks {maks})")
            if re.search(r"\|\s*xam\s*(\}\}|\|)", sətir):
                i = sətir.find("xam")
                self.bildir("xam-html", Yer(self.s, ofs + i, 3),
                            "qaçışsız çıxış",
                            "yalnız etibarlı HTML üçün; istifadəçi "
                            "məlumatını heç vaxt `| xam` ilə çıxarmayın")
            ofs += len(sətir) + 1

    # ── Bloklar: dərinlik, əlçatmaz kod, uzunluq ─────────────────────
    def _blok_gəz(self, blok: list, dərinlik: int, funksiya: Any,
                  qlobal: bool = False) -> None:
        maks = int(self.ayar["maks_dərinlik"])
        for i, c in enumerate(blok):
            if isinstance(c, (A.Qaytar, A.At, A.Dayan, A.DavamEt)) and \
                    i + 1 < len(blok):
                növbəti = blok[i + 1]
                self.bildir("əlçatmaz-kod", növbəti.yer,
                            "bu cümlə heç vaxt işləmir")
            if isinstance(c, (A.FunksiyaElanı, A.MetodElanı,
                              A.QurucuElanı)):
                self._funksiya(c)
                if c.gövdə:
                    self._blok_gəz(c.gövdə, 0, c)
                continue
            if isinstance(c, (A.SinifElanı, A.InterfeysElanı,
                              A.QarışıqElanı, A.Genişlətmə)):
                self._blok_gəz(c.üzvlər, dərinlik, funksiya)
                continue
            if isinstance(c, A.SadalamaElanı):
                self._blok_gəz(c.üzvlər, dərinlik, funksiya)
                continue
            if isinstance(c, A.ModulElanı):
                self._blok_gəz(c.gövdə, dərinlik, funksiya, qlobal)
                continue
            if isinstance(c, A.DəyişənElanı) and c.növ == "sabit" and qlobal:
                for b in c.bağlamalar:
                    if b.ad and not _BÖYÜK_SABİT.match(b.ad) and \
                            not b.ad.startswith("_"):
                        self.bildir("adlandırma-sabit",
                                    self._ad_yeri(b, b.ad) or c.yer,
                                    f"`{b.ad}` → `{_böyük_sabit(b.ad)}`")
            bloklar = _bloklar(c)
            if bloklar and funksiya is not None and dərinlik + 1 > maks:
                self.bildir("dərin-iç-içəlik", c.yer,
                            f"dərinlik {dərinlik + 1} (maks {maks})",
                            "daxili hissəni ayrıca funksiyaya çıxarın və "
                            "ya erkən `qaytar` işlədin")
                continue                         # bir dəfə bildirmək bəs
            for b in bloklar:
                self._blok_gəz(b, dərinlik + 1, funksiya, False)
            # boş bloklar
            if isinstance(c, A.Şərt):
                for _, g in c.budaqlar:
                    if not g:
                        self.bildir("boş-blok", c.yer, "`əgər` gövdəsi boşdur")
            elif isinstance(c, (A.Hər, A.NəQədərKi, A.Təkrarla)) and \
                    not c.gövdə:
                self.bildir("boş-blok", c.yer, "dövr gövdəsi boşdur")
            if isinstance(c, (A.Hər, A.NəQədərKi, A.Həmişə, A.Təkrarla,
                              A.TəkrarlaNəQədər)):
                self._dövr(c)

    def _funksiya(self, f: Any) -> None:
        ad = getattr(f, "ad", None) or "qurucu"
        if isinstance(f, (A.FunksiyaElanı, A.MetodElanı)) and \
                not _KİÇİK_DƏVƏ.match(f.ad):
            self.bildir("adlandırma-dəyişən", self._ad_yeri(f, f.ad),
                        f"`{f.ad}` → `{_kiçik_dəvə(f.ad)}`")
        for p in f.parametrlər:
            if not _KİÇİK_DƏVƏ.match(p.ad):
                self.bildir("adlandırma-dəyişən", p.yer,
                            f"parametr `{p.ad}` → `{_kiçik_dəvə(p.ad)}`")
        maks_p = int(self.ayar["maks_parametr"])
        if len(f.parametrlər) > maks_p:
            self.bildir("çox-parametr", self._ad_yeri(f, ad),
                        f"{len(f.parametrlər)} parametr (maks {maks_p})",
                        "parametrləri struktura və ya lüğətə yığın")
        aralıq = self._aralıq(f) if f.gövdə else None
        if aralıq:
            b = self.s.sətir_sütun(aralıq[0])[0]
            s = self.s.sətir_sütun(max(aralıq[0], aralıq[1] - 1))[0] + 1
            maks = int(self.ayar["maks_funksiya_sətri"])
            if s - b + 1 > maks:
                self.bildir("uzun-funksiya", self._ad_yeri(f, ad),
                            f"`{ad}` {s - b + 1} sətirdir (maks {maks})",
                            "kiçik funksiyalara bölün")

    def _dövr(self, d: Any) -> None:
        for q in hamısı_siyahı(d.gövdə):
            if isinstance(q, A.Mənimsətmə) and q.op == "+=" and \
                    len(q.dəyərlər) == 1 and _mətndir(q.dəyərlər[0]):
                self.bildir("dövrdə-mətn-birləşdirmə", self._tam_yer(q),
                            "hər dövrdə yeni mətn yaranır",
                            "hissələri `siyahı.əlavə(…)` ilə yığıb sonda "
                            "`\"\".birləşdir(siyahı)` işlədin")
        if isinstance(d, A.Hər) and isinstance(d.mənbə, A.Diapazon):
            dp = d.mənbə
            son = dp.son
            if isinstance(dp.başlanğıc, A.Literal) and \
                    dp.başlanğıc.dəyər == 0 and isinstance(son, A.Çağırış) \
                    and isinstance(son.funksiya, A.Üzv) and \
                    son.funksiya.ad == "uzunluq" and dp.xaric:
                self.bildir("indeksli-dövr", d.mənbə.yer,
                            "indeks yalnız elementi almaq üçündürsə",
                            f"`hər x üçün {self._mətn(son.funksiya.obyekt)} "
                            "içində`; indeks də lazımdırsa "
                            "`hər (i, x) üçün s.nömrələ() içində`")

    # ── Ayrı-ayrı qovşaqlar ───────────────────────────────────────────
    def _qovşaq(self, q: Any) -> None:
        if isinstance(q, (A.Şərt,)):
            for ş, _ in q.budaqlar:
                self._şərt(ş, "əgər")
        elif isinstance(q, A.NəQədərKi):
            self._şərt(q.şərt, "nə qədər ki", dövr=True)
        elif isinstance(q, A.ŞərtIfadəsi):
            for ş, _ in q.budaqlar:
                self._şərt(ş, "əgər")
        elif isinstance(q, A.Cəhd):
            for t in q.tutmalar:
                if not t.gövdə:
                    self.bildir("boş-tut", t.yer or q.yer,
                                "xəta səssizcə udulur",
                                "ən azı jurnala yazın və ya `_` ilə "
                                "qəsdən udulduğunu bildirən şərh qoyun")
        elif isinstance(q, A.Mənimsətmə):
            # Yalnız sadə ad: `özü.x = özü.x` yazıcını (setter) işə salır
            if q.op == "=" and len(q.hədəflər) == 1 == len(q.dəyərlər) and \
                    isinstance(q.hədəflər[0], A.Ad) and \
                    _eyni(q.hədəflər[0], q.dəyərlər[0]):
                self.bildir("özünə-mənimsətmə", self._tam_yer(q),
                            "dəyər dəyişmir")
        elif isinstance(q, A.İkili):
            self._ikili(q)
        elif isinstance(q, A.TəkOperand) and q.op in ("deyil", "!") and \
                isinstance(q.operand, A.İkili) and \
                q.operand.op in ("==", "!=", "<", ">", "<=", ">=") and \
                not self._mötərizəlidir(q.operand) and q.op == "deyil":
            self.bildir("deyil-prioriteti", self._tam_yer(q),
                        "`deyil` bütün müqayisəyə aiddir",
                        "niyyəti açıq yazın: `deyil (a == b)` və ya "
                        "`a != b`")
        elif isinstance(q, A.LüğətLiteralı):
            görülən: dict[Any, Any] = {}
            for a in q.açarlar:
                if isinstance(a, A.Literal):
                    açar = (a.növ, a.dəyər)
                    if açar in görülən:
                        self.bildir("təkrar-açar", a.yer,
                                    f"`{a.dəyər}` açarı artıq var — "
                                    "əvvəlki dəyər itir")
                    görülən[açar] = a
        elif isinstance(q, A.Seç):
            görülən = {}
            for h in q.hallar:
                for n in h.naxışlar:
                    if n.növ == "literal" and h.mühafizə is None:
                        d = n.dəyər
                        if isinstance(d, A.Literal):
                            açar = (d.növ, repr(d.dəyər))
                        elif isinstance(d, (int, float, str, bool)):
                            açar = ("", repr(d))
                        else:
                            continue
                        if açar in görülən:
                            self.bildir("təkrar-hal", n.yer,
                                        "bu hal heç vaxt seçilmir")
                        görülən[açar] = n
        elif isinstance(q, A.DəyişənElanı):
            for b, d in zip(q.bağlamalar, q.dəyərlər or [None] *
                            len(q.bağlamalar)):
                if b.ad and q.növ != "sabit" and not _KİÇİK_DƏVƏ.match(b.ad) \
                        and not _BÖYÜK_SABİT.match(b.ad):
                    self.bildir("adlandırma-dəyişən",
                                self._ad_yeri(b, b.ad) or q.yer,
                                f"`{b.ad}` → `{_kiçik_dəvə(b.ad)}`")
                self._gizli(b.ad, d)
        elif isinstance(q, (A.SinifElanı, A.InterfeysElanı,
                            A.SadalamaElanı, A.TipAliası)):
            if not _BÖYÜK_DƏVƏ.match(q.ad):
                self.bildir("adlandırma-tip", self._ad_yeri(q, q.ad),
                            f"`{q.ad}` → `{_böyük_dəvə(q.ad)}`")
        elif isinstance(q, A.XassəElanı):
            self._gizli(q.ad, q.standart)
        elif isinstance(q, A.Çağırış):
            self._çağırış(q)
        elif isinstance(q, A.JSXElement):
            self._jsx(q)
        elif isinstance(q, A.Literal) and q.növ == "mətn" and \
                isinstance(q.dəyər, str) and _GİZLİ_DƏYƏR.search(q.dəyər):
            self.bildir("gizli-açar", q.yer,
                        "mətn məlum açar/token formatındadır",
                        "`mühit(\"AD\")` və ya konfiqurasiya faylı "
                        "işlədin; açar artıq paylaşılıbsa onu dəyişin")

    def _şərt(self, ş: Any, söz: str, dövr: bool = False) -> None:
        if isinstance(ş, A.Mənimsətmə) and ş.op == "=":
            self.bildir("şərtdə-mənimsətmə", self._tam_yer(ş),
                        "`=` mənimsətmədir",
                        "müqayisə üçün `==` yazın")
        elif isinstance(ş, A.Literal) and ş.növ in ("məntiq", "tam", "boş"):
            if dövr and ş.dəyər is True:
                return            # `nə qədər ki doğru` — qəsdən sonsuz dövr
            self.bildir("sabit-şərt", ş.yer,
                        f"`{söz}` şərti həmişə "
                        f"{'doğrudur' if ş.dəyər else 'yanlışdır'}")

    def _ikili(self, q: A.İkili) -> None:
        if q.op in ("==", "!=", "<", ">", "<=", ">=") and _eyni(q.sol, q.sağ) \
                and not isinstance(q.sol, A.Literal):
            self.bildir("özü-ilə-müqayisə", self._tam_yer(q),
                        f"nəticə həmişə "
                        f"{'doğru' if q.op in ('==', '<=', '>=') else 'yanlış'}")
        if q.op in ("==", "!="):
            for a, b in ((q.sol, q.sağ), (q.sağ, q.sol)):
                if isinstance(b, A.Literal) and b.növ == "məntiq" and \
                        not isinstance(a, A.Literal) and self._məntiqdir(a):
                    müsbət = (b.dəyər is True) == (q.op == "==")
                    a_m = self._mətn(a)
                    sadə = isinstance(a, (A.Ad, A.Üzv, A.Çağırış, A.İndeks))
                    yeni = a_m if müsbət else (
                        f"deyil {a_m}" if sadə else f"deyil ({a_m})")
                    tam = self._tam_yer(q)
                    self.bildir("məntiqlə-müqayisə", tam,
                                f"`{self._mətn(q)}` → `{yeni}`",
                                düzəliş=(tam.başlanğıc, tam.son, yeni)
                                if tam else None)
                    break
                if isinstance(b, A.Literal) and b.növ == "boş" and \
                        not isinstance(a, A.Literal):
                    a_m = self._mətn(a)
                    yeni = f"{a_m} boşdur" if q.op == "==" else \
                        f"{a_m} boş deyil"
                    sadə = isinstance(a, (A.Ad, A.Üzv, A.Çağırış, A.İndeks))
                    tam = self._tam_yer(q)
                    self.bildir("boşla-müqayisə", tam,
                                f"`{self._mətn(q)}` → `{yeni}`",
                                düzəliş=(tam.başlanğıc, tam.son, yeni)
                                if tam and sadə else None)
                    break
        qrup = {"və": "və", "&&": "və", "və ya": "və ya", "||": "və ya",
                "??": "??"}
        if q.op in qrup:
            for u in (q.sol, q.sağ):
                if isinstance(u, A.İkili) and u.op in qrup and \
                        qrup[u.op] != qrup[q.op] and \
                        not self._mötərizəlidir(u):
                    self.bildir("qarışıq-prioritet", self._tam_yer(u),
                                f"`{qrup[u.op]}` `{qrup[q.op]}` içində "
                                "mötərizəsiz",
                                f"mötərizə yazın: `({self._mətn(u)})`")

    def _gizli(self, ad: str | None, d: Any) -> None:
        if not ad or d is None or not _GİZLİ_AD.search(ad):
            return
        if isinstance(d, A.Literal) and d.növ == "mətn" and \
                isinstance(d.dəyər, str) and len(d.dəyər) >= 6 and \
                not d.dəyər.startswith(("http", "/", "$")) and \
                " " not in d.dəyər.strip():
            self.bildir("gizli-açar", d.yer,
                        f"`{ad}` kodun içində yazılıb",
                        f"`mühit(\"{_böyük_sabit(ad)}\")` işlədin")

    def _çağırış(self, q: A.Çağırış) -> None:
        f = q.funksiya
        if not isinstance(f, A.Üzv) or not q.arqumentlər:
            if isinstance(f, A.Üzv) and f.ad == "şəkil" and \
                    isinstance(f.obyekt, A.Ad) and f.obyekt.ad == "vidjet":
                self._vidjet_şəkil(q)
            return
        ilk = q.arqumentlər[0].dəyər
        if f.ad in _SQL_METODLARI and _dinamik_mətn(ilk) and \
                _SQL_SÖZLƏRİ.search(self._mətn(ilk)):
            self.bildir("sql-birləşdirmə", self._tam_yer(ilk),
                        "dəyərlər sorğu mətninə qoşulub",
                        'parametr işlədin: `b.sorğu("… WHERE ad = ?", ad)`')
        if isinstance(f.obyekt, A.Ad) and (f.obyekt.ad, f.ad) in \
                _ƏMR_METODLARI and _dinamik_mətn(ilk):
            self.bildir("əmr-birləşdirmə", ilk.yer,
                        "əmr mətninə dəyişən qoşulub",
                        "əmri arqument siyahısı kimi verin və ya dəyəri "
                        "yoxlayın")
        if f.ad == "şəkil" and isinstance(f.obyekt, A.Ad) and \
                f.obyekt.ad == "vidjet":
            self._vidjet_şəkil(q)

    def _vidjet_şəkil(self, q: A.Çağırış) -> None:
        adlı = {a.ad for a in q.arqumentlər if a.ad}
        mövqeli = [a for a in q.arqumentlər if not a.ad]
        if "alternativ" not in adlı and len(mövqeli) < 2:
            self.bildir("şəkil-alt", q.yer, "`alternativ:` verilməyib",
                        'ekran oxuyucular üçün: `alternativ: "Loqo"` '
                        '(bəzəkdirsə `alternativ: ""` yazın)')

    def _jsx(self, q: A.JSXElement) -> None:
        atr = {a.ad.lower() for a in q.atributlar if not a.yayma}
        yayma = any(a.yayma for a in q.atributlar)
        if yayma:
            return
        if q.ad == "img" and "alt" not in atr:
            self.bildir("şəkil-alt", q.yer, "`<img>` `alt` atributsuz",
                        '`alt="…"` əlavə edin (bəzəkdirsə `alt=""`)')
        if q.ad == "button" and not ({"aria-label", "title"} & atr):
            mətnli = any((isinstance(u, A.JSXMətn) and u.dəyər.strip()) or
                         not isinstance(u, A.JSXMətn) for u in q.uşaqlar)
            if not mətnli:
                self.bildir("mətnsiz-düymə", q.yer,
                            "ekran oxuyucu bu düyməni adlandıra bilmir",
                            "mətn və ya `aria-label` əlavə edin")
        if q.ad in ("input", "textarea", "select") and \
                not ({"aria-label", "id", "aria-labelledby", "title"} & atr):
            növ = next((a.dəyər for a in q.atributlar if a.ad == "type"),
                       None)
            if not (isinstance(növ, A.Literal) and növ.dəyər in (
                    "hidden", "submit", "button")):
                self.bildir("etiketsiz-sahə", q.yer,
                            f"`<{q.ad}>` üçün etiket yoxdur",
                            "`id` verib `<label for=…>` yazın və ya "
                            "`aria-label` əlavə edin")


def hamısı_siyahı(blok: list) -> Iterator[Any]:
    for c in blok:
        yield from hamısı(c)


def _eyni(a: Any, b: Any) -> bool:
    if isinstance(a, A.Ad) and isinstance(b, A.Ad):
        return a.ad == b.ad
    if isinstance(a, A.Üzv) and isinstance(b, A.Üzv):
        return a.ad == b.ad and _eyni(a.obyekt, b.obyekt)
    if isinstance(a, A.Özü) and isinstance(b, A.Özü):
        return True
    return False


def _mətndir(q: Any) -> bool:
    return isinstance(q, A.ŞablonMətn) or (
        isinstance(q, A.Literal) and q.növ == "mətn")


def _dinamik_mətn(q: Any) -> bool:
    """Dəyişən qoşulmuş mətn: interpolyasiya və ya `+` ilə birləşdirmə."""
    if isinstance(q, A.ŞablonMətn):
        return any(isinstance(p, A.KodHissəsi) for p in q.parçalar)
    if isinstance(q, A.İkili) and q.op == "+":
        return (_mətndir(q.sol) or _mətndir(q.sağ) or
                _dinamik_mətn(q.sol) or _dinamik_mətn(q.sağ))
    return False


def _sözlər(ad: str) -> list[str]:
    ad = ad.strip("_")
    hissələr = re.split(r"[_\-\s]+", ad)
    n = []
    for h in hissələr:
        n.extend(re.findall(r"[A-ZƏIİÖÜĞŞÇ]+(?![a-zəıöüğşçi])|"
                            r"[A-ZƏIİÖÜĞŞÇ]?[a-zəıöüğşçi0-9]+|\d+", h) or [h])
    return [x for x in n if x]


def _az_kiçik(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def _az_böyük(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def _kiçik_dəvə(ad: str) -> str:
    s = _sözlər(ad)
    if not s:
        return ad
    return _az_kiçik(s[0]) + "".join(
        _az_böyük(x[0]) + _az_kiçik(x[1:]) for x in s[1:])


def _böyük_dəvə(ad: str) -> str:
    return "".join(_az_böyük(x[0]) + _az_kiçik(x[1:]) for x in _sözlər(ad))


def _böyük_sabit(ad: str) -> str:
    return "_".join(_az_böyük(x) for x in _sözlər(ad))


def _defisli(ad: str) -> str:
    return "-".join(_az_kiçik(x) for x in _sözlər(ad))


# ═══════════════════════════════════════════════════════════════════════
#  Konfiqurasiya, söndürmə, səviyyələr
# ═══════════════════════════════════════════════════════════════════════

def ayar_oxu(başlanğıc: Path | str = ".") -> dict:
    ayar = dict(STANDART_AYAR)
    try:
        from .layihe import tap
        l = tap(başlanğıc)
    except Exception:                                   # noqa: BLE001
        l = None
    if l is not None and isinstance(l.məlumat.get("lint"), dict):
        ayar.update(l.məlumat["lint"])
    return ayar


def _uyğundur(q: Qayda, naxışlar: list[str]) -> bool:
    for n in naxışlar or []:
        n = str(n)
        if n in (q.ad, q.kod, q.kateqoriya) or fnmatch.fnmatch(q.ad, n) or \
                fnmatch.fnmatch(q.kateqoriya + "-x", n) or \
                fnmatch.fnmatch(q.kod, n):
            return True
    return False


_SƏTİR_SÖNDÜR = re.compile(r"//\s*lint:\s*söndür\s+([^\n]+)")
_FAYL_SÖNDÜR = re.compile(r"//\s*alqor:\s*lint-söndür\s+([^\n]+)")


def süz(tapıntılar: list[Tapıntı], mətn: str, mənbə: Mənbə,
        ayar: dict) -> list[Tapıntı]:
    sərtlik = ayar.get("sərtlik", "normal")
    fayl_söndür = [x.strip() for m in _FAYL_SÖNDÜR.finditer(mətn)
                   for x in re.split(r"[,\s]+", m.group(1)) if x.strip()]
    sətirlər = mətn.split("\n")
    n = []
    görülən = set()
    for t in tapıntılar:
        q = t.qayda
        if _uyğundur(q, ayar.get("söndür", [])) or \
                _uyğundur(q, fayl_söndür):
            continue
        if t.yer is not None:
            s = mənbə.sətir_sütun(t.yer.başlanğıc)[0]
            m = _SƏTİR_SÖNDÜR.search(sətirlər[s - 1]) if s <= len(
                sətirlər) else None
            if m is None and s >= 2:
                əvvəl = sətirlər[s - 2].strip()
                if əvvəl.startswith("//"):
                    m = _SƏTİR_SÖNDÜR.search(əvvəl)
            if m and _uyğundur(q, [x for x in re.split(r"[,\s]+",
                                                       m.group(1)) if x]):
                continue
        səviyyə = q.səviyyə
        if sərtlik == "sərbəst":
            if q.kateqoriya not in ("potensial-xəta", "təhlükəsizlik") or \
                    səviyyə == "məlumat":
                continue
        elif sərtlik == "sərt" and səviyyə == "məlumat":
            səviyyə = "xəbərdarlıq"
        if _uyğundur(q, ayar.get("xəta", [])):
            səviyyə = "xəta"
        açar = (q.kod, t.yer.başlanğıc if t.yer else t.qeyd)
        if açar in görülən:
            continue
        görülən.add(açar)
        t.səviyyə = səviyyə
        n.append(t)
    n.sort(key=lambda t: (t.yer.başlanğıc if t.yer else -1, t.qayda.kod))
    return n


# ═══════════════════════════════════════════════════════════════════════
#  Fayl təhlili
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class FaylNəticəsi:
    yol: str
    mənbə: Mənbə | None
    tapıntılar: list[Tapıntı]
    sintaksis: XətaToplayıcı


def mətni_yoxla(mətn: str, yol: str = "<mətn>", ayar: dict | None = None,
                tip_rejimi: str = "normal") -> FaylNəticəsi:
    ayar = {**STANDART_AYAR, **(ayar or {})}
    x = XətaToplayıcı()
    s = Mənbə.mətndən(mətn, yol, x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        return FaylNəticəsi(yol, s, [], x)
    y = Yoxlayıcı(s, ağac, ayar, yol if yol != "<mətn>" else "")
    tapıntılar = y.işlət()
    # Tip yoxlayıcısından: istifadəsiz adlar və kölgələmə
    try:
        from .tipyoxlayici import tipləri_yoxla
        t = XətaToplayıcı()
        tipləri_yoxla(ağac, t, tip_rejimi)
        for d in t.siyahı:
            ad = {"ALQ-T024": "istifadəsiz-dəyişən",
                  "ALQ-T026": "kölgələmə"}.get(d.kod)
            if ad:
                tapıntılar.append(Tapıntı(QAYDA_ADI[ad], d.yer, d.qeyd,
                                          list(d.köməklər)))
    except Exception:                                   # noqa: BLE001
        pass
    return FaylNəticəsi(yol, s, süz(tapıntılar, s.mətn, s, ayar), x)


def düzəlt(mətn: str, tapıntılar: list[Tapıntı]) -> tuple[str, int]:
    """Düzəldilə bilən tapıntıları tətbiq edir (üst-üstə düşənlər atlanır)."""
    düzəlişlər = sorted({t.düzəliş for t in tapıntılar if t.düzəliş},
                        key=lambda d: d[0], reverse=True)
    son = len(mətn) + 1
    say = 0
    for b, e, yeni in düzəlişlər:
        if e > son:
            continue
        mətn = mətn[:b] + yeni + mətn[e:]
        son = b
        say += 1
    return mətn, say


# ═══════════════════════════════════════════════════════════════════════
#  Əmr sətri
# ═══════════════════════════════════════════════════════════════════════

KÖMƏK = """alqorlint — Alqor statik təhlil (linter)

İSTİFADƏ:
    alqor lint [seçimlər] <fayl|qovluq>...

SEÇİMLƏR:
    --düzəlt              avtomatik düzəldilənləri faylda düzəlt
    --sərtlik S           sərbəst | normal | sərt (`layihe.alq` → [lint])
    --söndür a,b          qaydaları söndür (ad, kod, "kateqoriya-*")
    --json                maşın oxunaqlı çıxış
    --qaydalar            bütün qaydaların siyahısı
    --xəbərdarlıq-xətadır xəbərdarlıq da çıxış kodunu 1 edir
"""


def qaydalar_mətni() -> str:
    n = []
    kat = None
    for q in QAYDALAR:
        if q.kateqoriya != kat:
            kat = q.kateqoriya
            n.append(f"\n{kat.upper()}")
        n.append(f"  {q.kod}  {q.ad:<26} {q.səviyyə:<12}"
                 f"{' [düzəldilir]' if q.düzəldilir else ''}\n"
                 f"            {q.təsvir}")
    return "\n".join(n).lstrip("\n")


def əsas(arqumentlər: list[str]) -> int:
    from .alqorfmt import faylları_tap
    arq = list(arqumentlər)
    if not arq or "--kömək" in arq or "-k" in arq:
        print(KÖMƏK)
        return 0 if arq else 3
    if "--qaydalar" in arq:
        print(qaydalar_mətni())
        return 0
    ayar = ayar_oxu(".")
    yollar: list[str] = []
    düzəlt_ = json_ = xx = False
    i = 0
    while i < len(arq):
        a = arq[i]
        if a in ("--düzəlt", "--duzelt", "--fix"):
            düzəlt_ = True
        elif a == "--json":
            json_ = True
        elif a in ("--xəbərdarlıq-xətadır", "--werror"):
            xx = True
        elif a in ("--sərtlik", "--sertlik") and i + 1 < len(arq):
            ayar["sərtlik"] = arq[i + 1]
            i += 1
        elif a in ("--sərt", "--sert"):
            ayar["sərtlik"] = "sərt"
        elif a in ("--söndür", "--sondur") and i + 1 < len(arq):
            ayar["söndür"] = list(ayar.get("söndür", [])) + \
                arq[i + 1].split(",")
            i += 1
        elif a.startswith("-"):
            print(f"✖ naməlum seçim: {a}", file=sys.stderr)
            return 3
        else:
            yollar.append(a)
        i += 1
    if ayar.get("sərtlik") not in ("sərbəst", "normal", "sərt"):
        print("✖ sərtlik: sərbəst | normal | sərt", file=sys.stderr)
        return 3
    fayllar = faylları_tap(yollar or ["."])
    if not fayllar:
        print("✖ yoxlanacaq .alq faylı tapılmadı", file=sys.stderr)
        return 4
    hamısı_: list[dict] = []
    xəta = xəbərdarlıq = məlumat = düzəldilən = 0
    for p in fayllar:
        mətn = p.read_text(encoding="utf-8")
        n = mətni_yoxla(mətn, str(p), ayar)
        if not n.sintaksis.uğurludur():
            print(f"── {p} " + "─" * max(0, 56 - len(str(p))))
            n.sintaksis.çap()
            xəta += len(n.sintaksis.xətalar)
            continue
        if düzəlt_ and any(t.düzəliş for t in n.tapıntılar):
            yeni, say = düzəlt(mətn, n.tapıntılar)
            # Düzəliş kodu pozmamalıdır — yenidən ayrılır
            yoxla = mətni_yoxla(yeni, str(p), ayar)
            if yoxla.sintaksis.uğurludur():
                p.write_text(yeni, encoding="utf-8")
                düzəldilən += say
                n = yoxla
        for t in n.tapıntılar:
            if t.səviyyə == "xəta":
                xəta += 1
            elif t.səviyyə == "xəbərdarlıq":
                xəbərdarlıq += 1
            else:
                məlumat += 1
        if json_:
            hamısı_.extend({"fayl": str(p), **t.lüğət()}
                           for t in n.tapıntılar)
        elif n.tapıntılar:
            print(f"── {p} " + "─" * max(0, 56 - len(str(p))))
            for t in n.tapıntılar:
                print(t.diaqnostika().formatla())
                print()
    if json_:
        print(json.dumps(hamısı_, ensure_ascii=False, indent=2))
    else:
        if düzəldilən:
            print(f"🔧 {düzəldilən} problem avtomatik düzəldildi")
        if xəta or xəbərdarlıq or məlumat:
            print(f"{len(fayllar)} fayl: {xəta} xəta, {xəbərdarlıq} "
                  f"xəbərdarlıq, {məlumat} məlumat")
        else:
            print(f"✓ {len(fayllar)} fayl yoxlandı, problem yoxdur")
    return 1 if xəta or (xx and xəbərdarlıq) else 0


if __name__ == "__main__":                              # pragma: no cover
    sys.exit(əsas(sys.argv[1:]))

