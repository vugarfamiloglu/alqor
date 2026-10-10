"""
Alqor → JavaScript kompilyatoru.

AAC-ni (`alqor/aac.py`) ES2020 JavaScript-ə çevirir. Nəticə `icra.js`
icra mühiti ilə birlikdə tək fayl olur və həm Node.js-də, həm də
brauzerdə işləyir:

    alqor qur --hədəf js  proqram.alq     → qurma/proqram.js   (node)
    alqor qur --hədəf veb proqram.alq     → qurma/veb/index.html
    alqor işlət --js proqram.alq          → node ilə dərhal işlədir

Semantika Python interpretatoru ilə eynidir (`sinaq/test_js.py` hər iki
icranın çıxışını müqayisə edir). `tam` → BigInt, `onluq` → number.

İnterfeys proqramları da (komponentlər, `vidjet`, `pəncərə`) brauzerdə
serversiz işləyir: `veb_səhifəsi` onları statik sayta çevirir (§ 13.14).
Dəstəklənməyən modullar (`veb`, `csv`, `verilənlər`, ...) kompilyasiya
xətası verir.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import aac as A

KÖK = Path(__file__).resolve().parent
İCRA_JS = KÖK / "icra.js"

#  JS hədəfində olan standart modullar (icra.js → `modullar`)
DƏSTƏKLƏNƏN_MODULLAR = frozenset({
    "riyaziyyat", "mətn", "təsadüfi", "vaxt", "json", "naxış", "sistem",
    "jurnal", "paralel", "fayl", "qovluq", "yol", "konsol",
    "vidjet", "pəncərə", "pəncərə.dialoq", "pəncərə.sınaq", "http",
})

#  icra.js-ə əlavə qoşulan modullar: proqram onları idxal edəndə
#  (`Kompilyator.lazımi`) uyğun JS faylı nəticəyə daxil edilir.
ƏLAVƏ_MODULLAR = ("vidjet", "pəncərə", "http", "veb")

#  Python-da olan, JS-də olmayan modullar — aydın xəta üçün
DƏSTƏKLƏNMƏYƏN_MODULLAR = frozenset({
    "veb", "test", "sap",
    "csv", "ffi", "html", "keş", "kodlaşdırma", "konfiq",
    "lokalizasiya", "növbə", "pdf", "planlayıcı", "poçt", "pul", "qrafik",
    "sıxma", "toml", "validasiya", "verilənlər", "xml", "yaml", "şifrə",
    "şəbəkə", "şəkil",
})

JS_AYRILMIŞ = frozenset("""
break case catch class const continue debugger default delete do else
enum export extends false finally for function if import in instanceof
new null return super switch this throw true try typeof var void while
with yield let static implements interface package private protected
public await arguments eval undefined NaN Infinity async of get set
""".split())

SADƏ_TİPLƏR = frozenset({
    "tam", "onluq", "mətn", "simvol", "məntiq", "bayt", "siyahı",
    "lüğət", "dəst", "kortej", "istənilən", "heç", "boş",
})

MƏNTİQİ_OPLAR = frozenset({"==", "!=", "<", ">", "<=", ">=", "və",
                           "və ya", "&&", "||"})

İKİLİ_FUNKSİYALAR = {
    "+": "add", "-": "sub", "*": "mul", "/": "div", "~/": "idiv",
    "%": "mod", "**": "pow", "==": "eq", "!=": "ne", "<": "lt",
    ">": "gt", "<=": "le", ">=": "ge", "<=>": "cmp3",
}
BİT_OPLARI = frozenset({"&", "|", "^", "<<", ">>", ">>>"})


class KompilyasiyaXətası(Exception):
    def __init__(self, mesaj: str, yer=None):
        super().__init__(mesaj)
        self.mesaj = mesaj
        self.yer = yer

    def __str__(self) -> str:
        if self.yer is not None:
            return f"{self.yer}: {self.mesaj}"
        return self.mesaj


def _js_mətn(s: str) -> str:
    return json.dumps(s, ensure_ascii=False).replace(" ", "\\u2028") \
        .replace(" ", "\\u2029")


# ═══════════════════════════════════════════════════════════════════════
#  Əhatə dairələri
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class AdM:
    js: str
    sabit: bool = False
    elan_edilib: bool = False


@dataclass
class FunksiyaK:
    """Bir JS funksiyasının kompilyasiya konteksti."""
    növ: str                       # proqram | funksiya | metod | blok | ...
    generator: bool = False
    temp_say: int = 0
    tempər: list[str] = field(default_factory=list)
    dövrlər: list[tuple[str | None, str, str | None]] = field(
        default_factory=list)
    gecikdir: bool = False
    sinif_js: str | None = None    # `üst` üçün Sinif dəyişəni
    özü: bool = False              # `özü` mövcuddur


class Əhatə:
    def __init__(self, üst: "Əhatə | None", fk: FunksiyaK):
        self.üst = üst
        self.fk = fk
        self.adlar: dict[str, AdM] = {}


# ═══════════════════════════════════════════════════════════════════════
#  Kompilyator
# ═══════════════════════════════════════════════════════════════════════

class Kompilyator:
    def __init__(self, əsas_yol: Path | None = None,
                 fayl_oxu=None):
        self.əsas_yol = əsas_yol
        self.ad_sayı: dict[str, int] = {}
        self.etiket_sayı = 0
        self.spec_say = 0
        self.speclər: list[str] = []
        self.fayl_modulları: dict[str, str] = {}      # açar → JS
        self._yüklənən: set[str] = set()
        self.fayl_oxu = fayl_oxu
        self.əh: Əhatə | None = None
        self.fk: FunksiyaK | None = None
        self.lazımi: set[str] = set()      # ƏLAVƏ_MODULLAR-dan işlənənlər
        self.interfeys = False             # proqram `pəncərə` idxal edir

    # ── Adlar ─────────────────────────────────────────────────────────

    def _yeni_js_ad(self, ad: str) -> str:
        əsas = ad + "$" if ad in JS_AYRILMIŞ else ad
        n = self.ad_sayı.get(əsas, 0)
        self.ad_sayı[əsas] = n + 1
        return əsas if n == 0 else f"{əsas}${n}"

    def _etiket(self, ön: str = "L") -> str:
        self.etiket_sayı += 1
        return f"${ön}{self.etiket_sayı}"

    def _temp(self) -> str:
        fk = self.fk
        fk.temp_say += 1
        t = f"$t{fk.temp_say}"
        fk.tempər.append(t)
        return t

    def _qeyd(self, ad: str, sabit: bool = False) -> AdM:
        """Cari əhatədə adı qabaqcadan qeyd edir (elan hələ yoxdur)."""
        m = self.əh.adlar.get(ad)
        if m is None:
            m = AdM(self._yeni_js_ad(ad), sabit)
            self.əh.adlar[ad] = m
        return m

    def _tap(self, ad: str) -> AdM | None:
        e = self.əh
        while e is not None:
            m = e.adlar.get(ad)
            if m is not None and (m.elan_edilib or e.fk is not self.fk):
                return m
            e = e.üst
        return None

    def _ad_js(self, ad: str) -> str:
        m = self._tap(ad)
        if m is not None:
            return m.js
        return f"$.qad({_js_mətn(ad)})"

    def _əhatə(self, fk: FunksiyaK | None = None) -> Əhatə:
        return Əhatə(self.əh, fk or self.fk)

    # ── Qabaqcadan tarama ─────────────────────────────────────────────

    @staticmethod
    def _bağlama_adları(b: A.Bağlama | None) -> list[str]:
        if b is None or b.növ == "atma":
            return []
        if b.növ in ("ad", "qalan"):
            return [b.ad]
        if b.növ == "kortej":
            return [a for x in b.alt for a in Kompilyator._bağlama_adları(x)]
        if b.növ == "obyekt":
            n: list[str] = []
            for ad, alt in b.sahələr:
                n.extend([ad] if alt is None
                         else Kompilyator._bağlama_adları(alt))
            return n
        return []

    def _elan_adları(self, c: A.Cümlə) -> list[tuple[str, bool]]:
        if isinstance(c, A.DəyişənElanı):
            sabit = c.növ in ("sabit", "dəyişməz")
            return [(a, sabit) for b in c.bağlamalar
                    for a in self._bağlama_adları(b)]
        if isinstance(c, (A.FunksiyaElanı, A.SinifElanı, A.InterfeysElanı,
                          A.SadalamaElanı, A.QarışıqElanı, A.TipAliası,
                          A.ModulElanı)):
            return [(c.ad, False)]
        if isinstance(c, A.İdxal):
            if c.hamısı:
                return [(a, False) for a in self._idxal_hamısı_adları(c)]
            if c.elementlər:
                return [(e.ləqəb or e.ad, False) for e in c.elementlər]
            return [(self._idxal_adı(c), False)]
        if isinstance(c, A.Yoxdursa):
            return [(a, False) for b, _ in c.bağlamalar
                    for a in self._bağlama_adları(b)]
        return []

    def _tara(self, gövdə: list[A.Cümlə]) -> None:
        for c in gövdə:
            for ad, sabit in self._elan_adları(c):
                m = self._qeyd(ad)
                m.sabit = m.sabit or sabit

    # ═══════════════════════════════════════════════════════════════════
    #  Proqram
    # ═══════════════════════════════════════════════════════════════════

    def proqram(self, ağac: A.Proqram) -> str:
        """Proqram funksiyasının mətni: `function () {...}`."""
        fk = FunksiyaK("proqram")
        self.fk = fk
        self.əh = Əhatə(None, fk)
        self.interfeys = any(
            isinstance(c, A.İdxal) and c.mətn_yolu is None and c.yol and
            c.yol[0] == "pəncərə" for c in ağac.gövdə)
        gövdə = self._yuxarı_səviyyə(ağac.gövdə)
        əsas = self.əh.adlar.get("əsas")
        son = f"return typeof {əsas.js} === \"function\" ? {əsas.js} : null;" \
            if əsas is not None else "return null;"
        return ("function () {\n" + self._tempər_elanı(fk) +
                "\n".join(gövdə) + "\n" + son + "\n}")

    def _yuxarı_səviyyə(self, gövdə: list[A.Cümlə]) -> list[str]:
        """Proqram/modul gövdəsi: elanlar əvvəl qaldırılır."""
        self._tara(gövdə)
        n: list[str] = []
        qaldırılan: list[A.Cümlə] = []
        for növlər in ((A.İdxal,), (A.FunksiyaElanı,),
                       (A.SinifElanı, A.SadalamaElanı, A.InterfeysElanı,
                        A.QarışıqElanı)):
            for c in gövdə:
                if isinstance(c, növlər):
                    qaldırılan.append(c)
        # Funksiyalar bir-birinə istinad edə bilsin: əvvəl hamısı elan
        for c in qaldırılan:
            n.extend(self._cümlə(c))
        for c in gövdə:
            if not any(c is q for q in qaldırılan):
                n.extend(self._cümlə(c))
        return n

    @staticmethod
    def _tempər_elanı(fk: FunksiyaK) -> str:
        return f"let {', '.join(fk.tempər)};\n" if fk.tempər else ""

    # ═══════════════════════════════════════════════════════════════════
    #  Bloklar və cümlələr
    # ═══════════════════════════════════════════════════════════════════

    def _blok(self, gövdə: list[A.Cümlə] | None, yeni: bool = True
              ) -> str:
        """`{ ... }` — yeni əhatə dairəsi."""
        if gövdə is None:
            return "{}"
        köhnə = self.əh
        if yeni:
            self.əh = self._əhatə()
        try:
            self._tara(gövdə)
            sətirlər: list[str] = []
            for c in gövdə:
                sətirlər.extend(self._cümlə(c))
        finally:
            self.əh = köhnə
        return "{\n" + "\n".join(sətirlər) + "\n}"

    def _cümlə(self, c: A.Cümlə) -> list[str]:
        f = getattr(self, "_c_" + type(c).__name__, None)
        if f is None:
            raise KompilyasiyaXətası(
                f"`{type(c).__name__}` JS hədəfində dəstəklənmir",
                getattr(c, "yer", None))
        n = f(c)
        return n if isinstance(n, list) else [n]

    # ── İfadə cümləsi ─────────────────────────────────────────────────

    def _c_İfadəCümləsi(self, c: A.İfadəCümləsi) -> str:
        return self._ifadə(c.ifadə) + ";"

    # ── Dəyişən elanı və bağlama ──────────────────────────────────────

    def _c_DəyişənElanı(self, c: A.DəyişənElanı) -> list[str]:
        n: list[str] = []
        if not c.dəyərlər:
            for b in c.bağlamalar:
                n.extend(self._bağla(b, self._standart(b.tip), True))
            return n
        if len(c.bağlamalar) == 1:
            if len(c.dəyərlər) == 1:
                d = self._ifadə(c.dəyərlər[0])
            else:
                d = "[" + ", ".join(self._ifadə(x) for x in c.dəyərlər) + "]"
            return self._bağla(c.bağlamalar[0], d, True)
        if len(c.dəyərlər) == 1:
            t = self._temp()
            n.append(f"{t} = {self._ifadə(c.dəyərlər[0])};")
            n.extend(self._çoxlu_bağla(c.bağlamalar, t, True))
            return n
        if len(c.dəyərlər) != len(c.bağlamalar):
            return [f"throw $.xəta(\"ArqumentXətası\", "
                    f"{_js_mətn(f'{len(c.bağlamalar)} ad, {len(c.dəyərlər)} dəyər — saylar uyğun gəlmir')}, "
                    f"\"ALQ-T001\");"]
        tempər = []
        for d in c.dəyərlər:
            t = self._temp()
            n.append(f"{t} = {self._ifadə(d)};")
            tempər.append(t)
        for b, t in zip(c.bağlamalar, tempər):
            n.extend(self._bağla(b, t, True))
        return n

    @staticmethod
    def _tip_adı(t) -> str | None:
        if isinstance(t, A.TipAdı):
            return t.tam_ad + ("?" if t.ixtiyari else "")
        return None

    def _standart(self, t) -> str:
        ad = self._tip_adı(t)
        return f"$.standartDəyər({_js_mətn(ad)})" if ad else "null"

    def _bağla(self, b: A.Bağlama, dəyər: str, elan: bool,
               kopya: bool = True) -> list[str]:
        if b.növ == "atma":
            return [f"{dəyər};"] if not re.fullmatch(r"[$\w]+", dəyər) \
                else []
        if b.növ in ("ad", "qalan"):
            if b.növ == "ad":
                t = self._tip_adı(b.tip)
                if t in ("onluq", "onluq?"):
                    dəyər = f"$.genişlət({dəyər}, \"onluq\")"
                if kopya:
                    dəyər = f"$.kp({dəyər})"
            return [self._ada_yaz(b.ad, dəyər, elan)]
        if b.növ == "kortej":
            t = self._temp()
            return [f"{t} = {dəyər};"] + self._çoxlu_bağla(b.alt, t, elan)
        if b.növ == "obyekt":
            t = self._temp()
            n = [f"{t} = {dəyər};"]
            for ad, alt in b.sahələr:
                sahə = f"$.üzv({t}, {_js_mətn(ad)})"
                if alt is None:
                    n.append(self._ada_yaz(ad, sahə, elan))
                else:
                    n.extend(self._bağla(alt, sahə, elan))
            return n
        raise KompilyasiyaXətası(f"naməlum bağlama: {b.növ}", b.yer)

    def _çoxlu_bağla(self, bağlamalar: list[A.Bağlama], dəyər: str,
                     elan: bool) -> list[str]:
        qalan = next((i for i, b in enumerate(bağlamalar)
                      if b.növ == "qalan"), -1)
        t = self._temp()
        n = [f"{t} = $.dağıt({dəyər}, {len(bağlamalar)}, {qalan});"]
        for i, b in enumerate(bağlamalar):
            n.extend(self._bağla(b, f"{t}[{i}]", elan))
        return n

    def _ada_yaz(self, ad: str, dəyər: str, elan: bool) -> str:
        if elan:
            m = self.əh.adlar.get(ad)
            if m is None:
                m = self._qeyd(ad)
            if not m.elan_edilib:
                m.elan_edilib = True
                return f"let {m.js} = {dəyər};"
            return f"{m.js} = {dəyər};"
        return self._ad_mənimsət(ad, dəyər) + ";"

    def _ad_mənimsət(self, ad: str, dəyər: str) -> str:
        m = self._tap(ad)
        if m is None:
            return f"$.qQoy({_js_mətn(ad)}, {dəyər})"
        if m.sabit:
            return f"({dəyər}, $.sabitXəta({_js_mətn(ad)}))"
        return f"({m.js} = {dəyər})"

    # ── Şərtlər ───────────────────────────────────────────────────────

    def _c_Şərt(self, c: A.Şərt) -> str:
        hissələr = []
        for i, (şərt, gövdə) in enumerate(c.budaqlar):
            ön = "if" if i == 0 else "else if"
            hissələr.append(f"{ön} ({self._şərt(şərt)}) {self._blok(gövdə)}")
        if c.yoxsa is not None:
            hissələr.append("else " + self._blok(c.yoxsa))
        return " ".join(hissələr)

    def _c_Varsa(self, c: A.Varsa) -> str:
        etiket = self._etiket("V")
        köhnə = self.əh
        self.əh = self._əhatə()
        try:
            yoxsa = (self._blok_xarici(c.yoxsa, köhnə)
                     if c.yoxsa is not None else "")
            n = [f"{etiket}: {{"]
            for bağlama, ifadə in c.bağlamalar:
                t = self._temp()
                n.append(f"{t} = {self._ifadə(ifadə)};")
                n.append(f"if ({t} === null || {t} === false) "
                         f"{{ {yoxsa} break {etiket}; }}")
                if bağlama is not None:
                    n.extend(self._bağla(bağlama, t, True))
            self._tara(c.gövdə)
            for x in c.gövdə:
                n.extend(self._cümlə(x))
            n.append("}")
        finally:
            self.əh = köhnə
        return "\n".join(n)

    def _blok_xarici(self, gövdə, əhatə: Əhatə) -> str:
        """Bloku verilmiş (xarici) əhatədə kompilyasiya edir."""
        köhnə = self.əh
        self.əh = əhatə
        try:
            return self._blok(gövdə)
        finally:
            self.əh = köhnə

    def _c_Yoxdursa(self, c: A.Yoxdursa) -> list[str]:
        etiket = self._etiket("Y")
        n: list[str] = []
        # Bağlamalar cari əhatədə elan olunur
        for b, _ in c.bağlamalar:
            for ad in self._bağlama_adları(b):
                m = self._qeyd(ad)
                if not m.elan_edilib:
                    m.elan_edilib = True
                    n.append(f"let {m.js} = null;")
        gövdə = self._blok(c.gövdə)
        n.append(f"{etiket}: {{")
        for bağlama, ifadə in c.bağlamalar:
            t = self._temp()
            n.append(f"{t} = {self._ifadə(ifadə)};")
            n.append(f"if ({t} === null || {t} === false) "
                     f"{{ {gövdə} break {etiket}; }}")
            if bağlama is not None:
                n.extend(self._bağla(bağlama, t, True))
        n.append("}")
        return n

    # ── Seç ───────────────────────────────────────────────────────────

    def _c_Seç(self, c: A.Seç) -> list[str]:
        etiket = self._etiket("S")
        v = self._temp()
        k = self._temp()
        n = [f"{etiket}: {{",
             f"{v} = {self._ifadə(c.ifadə) if c.ifadə is not None else 'null'};",
             f"{k} = 0;"]
        for hal in c.hallar:
            köhnə = self.əh
            self.əh = self._əhatə()
            try:
                adlar: list[str] = []
                for nx in hal.naxışlar:
                    self._naxış_adları(nx, c, adlar)
                elanlar = []
                for ad in dict.fromkeys(adlar):
                    m = self._qeyd(ad)
                    m.elan_edilib = True
                    elanlar.append(m.js)
                şərtlər = [self._naxış(nx, v, c) for nx in hal.naxışlar]
                if hal.mühafizə is not None:
                    q = self._şərt(hal.mühafizə)
                    şərtlər = [f"({s} && {q})" for s in şərtlər]
                uyğun = " || ".join(şərtlər) or "false"
                gövdə_sətir: list[str] = []
                self._tara(hal.gövdə)
                for x in hal.gövdə:
                    gövdə_sətir.extend(self._cümlə(x))
            finally:
                self.əh = köhnə
            son = f"{k} = 1;" if hal.keç else f"break {etiket};"
            n.append("{")
            if elanlar:
                n.append(f"let {', '.join(elanlar)};")
            n.append(f"if ({k} === 0 ? ({uyğun}) : ({k} === 1 && "
                     f"(({uyğun}), true))) {{")
            n.extend(gövdə_sətir)
            n.append(son)
            n.append("}")
            n.append("}")
        if c.digər is not None:
            n.append(self._blok(c.digər))
        n.append("}")
        return n

    def _naxış_adları(self, nx: A.Naxış, seç: A.Seç,
                      adlar: list[str]) -> None:
        if nx.növ == "ad" and seç.ifadə is not None:
            adlar.append(nx.dəyər)
        elif nx.növ in ("kortej", "siyahı"):
            for a in nx.alt:
                self._naxış_adları(a, seç, adlar)
            if nx.qalan:
                adlar.append(nx.qalan)
        elif nx.növ == "obyekt":
            for a in nx.alt:
                self._naxış_adları(a, seç, adlar)
            for ad, alt in nx.sahələr:
                if alt is None:
                    adlar.append(ad)
                else:
                    self._naxış_adları(alt, seç, adlar)

    def _naxış(self, nx: A.Naxış, v: str, seç: A.Seç) -> str:
        if nx.növ == "atma":
            return "true"
        if nx.növ == "literal":
            return f"$.eq({self._ifadə(nx.dəyər)}, {v})"
        if nx.növ == "şərt":
            return self._şərt(nx.dəyər)
        if nx.növ == "diapazon":
            return (f"$.naxışDiapazon({v}, {self._ifadə(nx.dəyər)}, "
                    f"{self._ifadə(nx.diapazon_son)}, "
                    f"{'true' if nx.diapazon_xaric else 'false'})")
        if nx.növ == "tip":
            return f"$.tipUyğun({v}, {self._tip_spec(nx.tip)})"
        if nx.növ == "ad":
            if seç.ifadə is None:
                return f"$.ş({self._ad_js(nx.dəyər)})"
            js = self.əh.adlar[nx.dəyər].js
            return (f"(({v} instanceof $.SDəyər && {v}.ad === "
                    f"{_js_mətn(nx.dəyər)}) || ({js} = {v}, true))")
        if nx.növ == "kortej":
            t = self._temp()
            alt = [self._naxış(a, f"{t}[{i}]", seç)
                   for i, a in enumerate(nx.alt)]
            return ("((" + t + f" = $.naxışKortej({v}, {len(nx.alt)})) "
                    "!== null" + "".join(" && " + x for x in alt) + ")")
        if nx.növ == "siyahı":
            t = self._temp()
            alt = [self._naxış(a, f"{t}[{i}]", seç)
                   for i, a in enumerate(nx.alt)]
            qalan = ""
            if nx.qalan:
                js = self.əh.adlar[nx.qalan].js
                qalan = f" && ({js} = {t}.slice({len(nx.alt)}), true)"
            return ("((" + t + f" = $.naxışSiyahı({v}, {len(nx.alt)}, "
                    f"{'true' if nx.qalan else 'false'})) !== null" +
                    "".join(" && " + x for x in alt) + qalan + ")")
        if nx.növ == "obyekt":
            yol = nx.tip.yol if isinstance(nx.tip, A.TipAdı) else []
            hədəf = f"() => {self._ad_js(yol[0])}" if yol else "null"
            hissələr = [f"$.naxışObyekt({v}, {json.dumps(yol, ensure_ascii=False)}, {hədəf})"]
            for i, a in enumerate(nx.alt):
                t = self._temp()
                hissələr.append(
                    f"(({t} = $.sdSahə({v}, {i})) === $.ATLA || "
                    f"({t} !== $.YOX && {self._naxış(a, t, seç)}))")
            for ad, alt in nx.sahələr:
                sahə = f"$.üzv({v}, {_js_mətn(ad)})"
                if alt is None:
                    js = self.əh.adlar[ad].js
                    hissələr.append(f"({js} = {sahə}, true)")
                else:
                    t = self._temp()
                    hissələr.append(f"({t} = {sahə}, {self._naxış(alt, t, seç)})")
            return "(" + " && ".join(hissələr) + ")"
        return "false"

    # ── Dövrlər ───────────────────────────────────────────────────────

    def _dövr(self, etiket: str | None, js: str, bayraq: str | None,
              gövdə) -> str:
        self.fk.dövrlər.append((etiket, js, bayraq))
        try:
            return self._blok(gövdə)
        finally:
            self.fk.dövrlər.pop()

    def _c_NəQədərKi(self, c: A.NəQədərKi) -> str:
        L = self._etiket()
        return f"{L}: while ({self._şərt(c.şərt)}) " + \
            self._dövr(c.etiket, L, None, c.gövdə)

    def _c_Həmişə(self, c: A.Həmişə) -> str:
        L = self._etiket()
        return f"{L}: for (;;) " + self._dövr(c.etiket, L, None, c.gövdə)

    def _c_TəkrarlaNəQədər(self, c: A.TəkrarlaNəQədər) -> str:
        L = self._etiket()
        gövdə = self._dövr(c.etiket, L, None, c.gövdə)
        return f"{L}: do {gövdə} while ({self._şərt(c.şərt)});"

    def _c_Təkrarla(self, c: A.Təkrarla) -> str:
        L = self._etiket()
        n = self._temp()
        i = self._temp()
        köhnə = self.əh
        self.əh = self._əhatə()
        try:
            sayğac = ""
            if c.sayğac:
                sayğac = self._ada_yaz(c.sayğac, i, True)
            gövdə = self._dövr(c.etiket, L, None, c.gövdə)
        finally:
            self.əh = köhnə
        return (f"{n} = $.təkrarSay({self._ifadə(c.say)});\n"
                f"{L}: for ({i} = 1n; {i} <= {n}; {i}++) {{ {sayğac} "
                f"{gövdə} }}")

    def _c_Hər(self, c: A.Hər) -> list[str]:
        L = self._etiket()
        mənbə = self._temp()
        e = self._temp()
        bayraq = self._temp() if c.yoxsa is not None else None
        n = [f"{mənbə} = {self._ifadə(c.mənbə)};"]
        if c.addım is not None:
            n.append(f"{mənbə} = $.addımla({mənbə}, {self._ifadə(c.addım)});")
        if bayraq:
            n.append(f"{bayraq} = false;")
        çoxlu = len(c.bağlamalar) >= 2
        indeks = self._temp() if çoxlu else None
        if indeks:
            n.append(f"{indeks} = 0n;")
        köhnə = self.əh
        self.əh = self._əhatə()
        try:
            for b in c.bağlamalar:
                for ad in self._bağlama_adları(b):
                    self._qeyd(ad)
            iç: list[str] = []
            if c.asinxron:
                iç.append(f"{e} = $.gözlə({e});")
            if çoxlu:
                adlar = [self.əh.adlar[a] for b in c.bağlamalar
                         for a in self._bağlama_adları(b)]
                for m in adlar:
                    m.elan_edilib = True
                if adlar:
                    iç.append(f"let {', '.join(dict.fromkeys(m.js for m in adlar))};")
                lüğət = self._çoxlu_bağla(
                    c.bağlamalar, f"new $.Kortej([{e}, $.ind({mənbə}, {e})])",
                    False)
                digər = self._bağla(c.bağlamalar[0], f"{indeks}", False)
                qalan = c.bağlamalar[1:]
                if len(qalan) == 1:
                    digər += self._bağla(qalan[0], e, False)
                else:
                    digər += self._çoxlu_bağla(qalan, e, False)
                iç.append(f"if ({mənbə} instanceof $.Lüğət) {{ "
                          + " ".join(lüğət) + " } else { "
                          + " ".join(digər) + " }")
                iç.append(f"{indeks}++;")
            else:
                iç.extend(self._bağla(c.bağlamalar[0], e, True))
            if c.şərt is not None:
                iç.append(f"if (!{self._şərt(c.şərt)}) continue {L};")
            gövdə = self._dövr(c.etiket, L, bayraq, c.gövdə)
        finally:
            self.əh = köhnə
        n.append(f"{L}: for (let {e}_ of $.iter({mənbə})) {{ {e} = {e}_;")
        n.extend(iç)
        n.append(gövdə)
        n.append("}")
        if c.yoxsa is not None:
            n.append(f"if (!{bayraq}) {self._blok(c.yoxsa)}")
        return n

    def _dövr_tap(self, etiket: str | None):
        for d in reversed(self.fk.dövrlər):
            if etiket is None or d[0] == etiket:
                return d
        return None

    def _c_Dayan(self, c: A.Dayan) -> str:
        d = self._dövr_tap(c.etiket)
        if d is None:
            return ("throw $.xəta(\"DaxiliXəta\", "
                    "\"`dayan` dövrdən kənarda işlənib\");")
        if d[2]:
            return f"{{ {d[2]} = true; break {d[1]}; }}"
        return f"break {d[1]};"

    def _c_DavamEt(self, c: A.DavamEt) -> str:
        d = self._dövr_tap(c.etiket)
        if d is None:
            return ("throw $.xəta(\"DaxiliXəta\", "
                    "\"`davam` dövrdən kənarda işlənib\");")
        return f"continue {d[1]};"

    # ── Funksiya axını ────────────────────────────────────────────────

    def _c_Qaytar(self, c: A.Qaytar) -> str:
        if self.fk.növ == "proqram":
            return "return null;"
        if self.fk.generator:
            return "return;"
        if not c.dəyərlər:
            return "return null;"
        if len(c.dəyərlər) == 1:
            return f"return {self._ifadə(c.dəyərlər[0])};"
        return ("return new $.Kortej([" +
                ", ".join(self._ifadə(d) for d in c.dəyərlər) + "]);")

    def _c_Ver(self, c: A.Ver) -> str:
        d = self._ifadə(c.dəyər) if c.dəyər is not None else "null"
        if self.fk.generator:
            return f"yield {d};"
        if self.fk.növ in ("blok", "funksiya", "metod"):
            return f"return {d};"
        return ("throw $.xəta(\"DaxiliXəta\", "
                "\"`ver` yalnız generator və ya blok daxilində işlənir\");")

    def _c_Keç(self, c: A.Keç) -> list[str]:
        return []

    def _c_DayanNöqtəsi(self, c) -> str:
        return "$.P.yaz(\"⏸ dayanNöqtəsi — debaq hələ qoşulmayıb\");"

    def _c_MetodElanı(self, c) -> str:
        return ("throw $.xəta(\"DaxiliXəta\", "
                "\"icra olunmayan qovşaq: MetodElanı\");")

    def _c_Global(self, c) -> list[str]:
        return []

    def _c_Bitiş(self, c) -> list[str]:
        return []

    def _c_İxracSiyahısı(self, c) -> list[str]:
        return []

    def _c_Başlanğıc(self, c: A.Başlanğıc) -> str:
        return self._blok(c.gövdə)

    def _c_Artırma(self, c: A.Artırma) -> str:
        d = "1n" if c.op == "++" else "-1n"
        return self._mənimsət_js(
            c.hədəf, lambda cari: f"$.inc({cari}, {d})") + ";"

    # ── Xətalar ───────────────────────────────────────────────────────

    def _c_At(self, c: A.At) -> str:
        if c.ifadə is None:
            return ("throw $.xəta(\"Xəta\", "
                    "\"təkrar atılacaq xəta yoxdur\");")
        return f"throw $.at({self._ifadə(c.ifadə)});"

    def _c_Cəhd(self, c: A.Cəhd) -> str:
        n = ["try " + self._blok(c.gövdə)]
        if c.tutmalar:
            x = self._temp()
            T = self._etiket("T")
            n.append("catch ($e) {")
            n.append("if ($e instanceof $.Dayanma || $e instanceof $.Yayılan) "
                     "throw $e;")
            n.append(f"{x} = $.xətaya($e);")
            n.append(f"{T}: {{")
            for t in c.tutmalar:
                köhnə = self.əh
                self.əh = self._əhatə()
                try:
                    if t.tiplər:
                        uyğun = " || ".join(
                            f"$.xətaUyğun({x}.tip, {_js_mətn(tp.tam_ad if isinstance(tp, A.TipAdı) else '')})"
                            for tp in t.tiplər)
                    else:
                        uyğun = "true"
                    iç = []
                    if t.ad:
                        iç.append(self._ada_yaz(
                            t.ad, f"$.xətaObyekti({x})", True))
                    mühafizə = (self._şərt(t.mühafizə)
                                if t.mühafizə is not None else "true")
                    self._tara(t.gövdə)
                    gövdə = []
                    for y in t.gövdə:
                        gövdə.extend(self._cümlə(y))
                finally:
                    self.əh = köhnə
                n.append(f"if ({uyğun}) {{ " + " ".join(iç) +
                         f" if ({mühafizə}) {{\n" + "\n".join(gövdə) +
                         f"\nbreak {T}; }} }}")
            n.append(f"throw {x};")
            n.append("}")
            n.append("}")
        if c.nəhayət is not None:
            n.append("finally " + self._blok(c.nəhayət))
        elif not c.tutmalar:
            n.append("finally {}")
        return "\n".join(n)

    def _c_İddia(self, c: A.İddia) -> str:
        mesaj = (f"$.mətnə({self._ifadə(c.mesaj)})" if c.mesaj is not None
                 else '"iddia pozuldu"')
        return (f"if (!{self._şərt(c.şərt)}) throw $.xəta(\"İddiaXətası\", "
                f"{mesaj}, \"ALQ-R007\");")

    def _c_Təmin(self, c: A.Təmin) -> str:
        return f"if (!{self._şərt(c.şərt)}) {self._blok(c.gövdə)}"

    def _c_Gecikdir(self, c: A.Gecikdir) -> str:
        if self.fk.növ in ("funksiya", "metod"):
            self.fk.gecikdir = True
            return f"$gec.push(() => {self._ifadə(c.ifadə)});"
        return self._ifadə(c.ifadə) + ";"

    def _c_İstifadə(self, c: A.İstifadə) -> str:
        köhnə = self.əh
        self.əh = self._əhatə()
        try:
            r = self._temp()
            n = [f"{r} = [];", "try {"]
            for ad, ifadə in c.bağlamalar:
                n.append(self._ada_yaz(ad, self._ifadə(ifadə), True))
                n.append(f"{r}.push({self.əh.adlar[ad].js});")
            n.append(self._blok(c.gövdə))
            n.append(f"}} finally {{ for (const $r of {r}.reverse()) "
                     "$.resursBağla($r); }")
        finally:
            self.əh = köhnə
        return "{\n" + "\n".join(n) + "\n}"

    # ═══════════════════════════════════════════════════════════════════
    #  Funksiyalar
    # ═══════════════════════════════════════════════════════════════════

    def _spec(self, ad: str, parametrlər: list[A.Parametr]) -> str:
        mövqeli = [p for p in parametrlər if not p.variadic
                   and not p.adlı_variadic and not p.yalnız_adlı]
        adlı = [p for p in parametrlər if p.yalnız_adlı]
        v = next((p.ad for p in parametrlər if p.variadic), None)
        kv = next((p.ad for p in parametrlər if p.adlı_variadic), None)
        o = {"ad": ad, "p": [p.ad for p in mövqeli],
             "st": [p.standart is not None for p in mövqeli],
             "v": v, "k": [p.ad for p in adlı],
             "kst": [p.standart is not None for p in adlı], "kv": kv}
        self.spec_say += 1
        js = f"$S{self.spec_say}"
        self.speclər.append(f"const {js} = {json.dumps(o, ensure_ascii=False)};")
        return js

    def _funksiya(self, ad: str, parametrlər: list[A.Parametr],
                  gövdə, *, növ: str = "funksiya", generator=False,
                  asinxron=False, özü=False, sinif_js=None,
                  yaddaşla=False, qısa_qurucu=False,
                  saymadan=False) -> str:
        """`$.ad(function (...$a) {...}, "ad", "funksiya", n)` ifadəsi."""
        fk = FunksiyaK(növ, generator=generator,
                       sinif_js=sinif_js or (self.fk.sinif_js if self.fk else None),
                       özü=özü or (self.fk.özü if self.fk else False))
        köhnə_fk, köhnə_əh = self.fk, self.əh
        self.fk = fk
        self.əh = Əhatə(köhnə_əh, fk)
        try:
            n: list[str] = []
            if özü:
                n.append("const özü = this;")
            if parametrlər:
                spec = self._spec(ad, parametrlər)
                sıra = ([p for p in parametrlər if not p.variadic
                         and not p.adlı_variadic and not p.yalnız_adlı] +
                        [p for p in parametrlər if p.yalnız_adlı] +
                        [p for p in parametrlər if p.variadic] +
                        [p for p in parametrlər if p.adlı_variadic])
                jsl = []
                for p in sıra:
                    m = self._qeyd(p.ad)
                    m.elan_edilib = True
                    jsl.append(m.js)
                n.append(f"let [{', '.join(jsl)}] = $.bağla($a, {spec});")
                for p, js in zip(sıra, jsl):
                    if p.standart is not None:
                        n.append(f"if ({js} === $.YOX) {js} = "
                                 f"{self._ifadə(p.standart)};")
                    if not (p.variadic or p.adlı_variadic or p.yalnız_adlı):
                        t = self._tip_adı(p.tip)
                        if t in ("onluq", "onluq?"):
                            n.append(f"{js} = $.genişlət({js}, \"onluq\");")
                        n.append(f"{js} = $.kp({js});")
                if qısa_qurucu:
                    for p, js in zip(sıra, jsl):
                        if p.xassə_görünüşü:
                            n.append(f"özü.f.set({_js_mətn(p.ad)}, {js});")
            else:
                n.append(f"if ($a.length) $.bağla($a, {self._spec(ad, [])});")
            # Gövdə
            gövdə_sətir: list[str] = []
            if isinstance(gövdə, list):
                self._tara(gövdə)
                for i, c in enumerate(gövdə):
                    son = i == len(gövdə) - 1
                    if (son and not generator and isinstance(c, A.İfadəCümləsi)
                            and not isinstance(c.ifadə,
                                               (A.Mənimsətmə, A.Çağırış))):
                        gövdə_sətir.append(f"return {self._ifadə(c.ifadə)};")
                    else:
                        gövdə_sətir.extend(self._cümlə(c))
                if not generator:
                    gövdə_sətir.append("return null;")
            else:
                gövdə_sətir.append(f"return {self._ifadə(gövdə)};")
            gövdə_js = "\n".join(gövdə_sətir)
            if fk.gecikdir:
                gövdə_js = ("const $gec = [];\ntry {\n" + gövdə_js +
                            "\n} finally { $.gecikmişləri($gec); }")
            if self._yaymadır(gövdə):
                gövdə_js = ("try {\n" + gövdə_js + "\n} catch ($y) { "
                            "if ($y instanceof $.Yayılan) return $y.d; "
                            "throw $y; }")
            temp = self._tempər_elanı(fk)
            if generator:
                daxili = (f"return new $.Gen((function* () {{\n{temp}"
                          f"{gövdə_js}\n}}).call(this));")
                gövdə_js = daxili
                temp = ""
            n_js = "\n".join(n)
            if saymadan:
                bədən = f"{temp}{n_js}\n{gövdə_js}"
            else:
                bədən = (f"if (++$.V.d > {1000}) $.stek();\ntry {{\n{temp}"
                         f"{n_js}\n{gövdə_js}\n}} finally {{ $.V.d--; }}")
            f = f"function (...$a) {{\n{bədən}\n}}"
            if asinxron and not generator:
                f = (f"function (...$a) {{ const $f = {f}; const $ö = this; "
                     f"return new $.Gələcək(() => $f.apply($ö, $a), "
                     f"{_js_mətn(ad)}); }}")
            pSay = len([p for p in parametrlər])
            nəticə = f"$.ad({f}, {_js_mətn(ad)}, \"funksiya\", {pSay})"
            if yaddaşla:
                nəticə = f"$.yaddaşla({nəticə})"
            return nəticə
        finally:
            self.fk, self.əh = köhnə_fk, köhnə_əh

    @staticmethod
    def _yaymadır(gövdə) -> bool:
        """Gövdədə (iç funksiyalar xaric) `x?` varmı?"""
        tapıldı = False

        def gəz(q):
            nonlocal tapıldı
            if tapıldı:
                return
            if isinstance(q, A.Yayma):
                tapıldı = True
                return
            if isinstance(q, (A.Lambda, A.FunksiyaElanı, A.SinifElanı,
                              A.MetodElanı)):
                return
            if isinstance(q, list):
                for x in q:
                    gəz(x)
                return
            if isinstance(q, tuple):
                for x in q:
                    gəz(x)
                return
            if hasattr(q, "__dataclass_fields__"):
                for ad in q.__dataclass_fields__:
                    if ad != "yer":
                        gəz(getattr(q, ad))
        gəz(gövdə)
        return tapıldı

    def _c_FunksiyaElanı(self, c: A.FunksiyaElanı) -> str:
        annot = [a.ad for a in c.annotasiyalar]
        f = self._funksiya(c.ad, c.parametrlər, c.gövdə,
                           generator=c.generator, asinxron=c.asinxron,
                           yaddaşla="yaddaşla" in annot)
        return self._ada_yaz(c.ad, f, True)

    # ── Siniflər ──────────────────────────────────────────────────────

    def _tip_ref(self, t) -> str:
        """Tip adını dəyər kimi həll edir: `modul.Sinif`."""
        if isinstance(t, A.TipAdı):
            js = self._ad_js(t.yol[0])
            for h in t.yol[1:]:
                js = f"$.üzv({js}, {_js_mətn(h)})"
            return js
        raise KompilyasiyaXətası("sadə tip adı gözlənilirdi",
                                 getattr(t, "yer", None))

    def _tip_spec(self, t) -> str:
        if isinstance(t, A.TipBirləşmə):
            return "{v: [" + ", ".join(self._tip_spec(v)
                                       for v in t.variantlar) + "]}"
        if isinstance(t, A.TipAdı):
            ad = t.tam_ad
            i = "true" if t.ixtiyari else "false"
            if ad in SADƏ_TİPLƏR:
                return f"{{a: {_js_mətn(ad)}, i: {i}}}"
            return f"{{a: {_js_mətn(ad)}, i: {i}, h: () => {self._tip_ref(t)}}}"
        return "{}"

    def _c_SinifElanı(self, c: A.SinifElanı) -> str:
        S = self._etiket("C")
        baza = self._tip_ref(c.baza) if c.baza is not None else "null"
        baza_adı = c.baza.tam_ad if isinstance(c.baza, A.TipAdı) else ""
        qarışıqlar = "[" + ", ".join(self._tip_ref(q)
                                     for q in c.qarışıqlar) + "]"
        interfeyslər = json.dumps([t.tam_ad for t in c.interfeyslər
                                   if isinstance(t, A.TipAdı)],
                                  ensure_ascii=False)
        o = (f"{{ad: {_js_mətn(c.ad)}, baza: {baza}, bazaAdı: "
             f"{_js_mətn(baza_adı)}, quruluş: {_js_mətn(c.quruluş)}, "
             f"mücərrəd: {'true' if c.mücərrəd else 'false'}, "
             f"son: {'true' if c.son else 'false'}, "
             f"interfeyslər: {interfeyslər}, qarışıqlar: {qarışıqlar}}}")
        gövdə = self._sinif_üzvləri(S, c.üzvlər)
        return self._ada_yaz(c.ad, f"$.sinif({o}, ({S}) => {{\n{gövdə}\n}})",
                             True)

    def _sinif_üzvləri(self, S: str, üzvlər: list[A.Cümlə]) -> str:
        fk = FunksiyaK("sinif", sinif_js=S)
        köhnə_fk, köhnə_əh = self.fk, self.əh
        self.fk = fk
        self.əh = Əhatə(köhnə_əh, fk)
        n: list[str] = []
        try:
            for ü in üzvlər:
                if isinstance(ü, A.XassəElanı):
                    annot = [a.ad for a in ü.annotasiyalar]
                    if ü.oxu_gövdəsi is not None:
                        f = self._funksiya(ü.ad, [], ü.oxu_gövdəsi,
                                           növ="metod", özü=True,
                                           sinif_js=S)
                        n.append(f"{S}.hesablananlar.set({_js_mətn(ü.ad)}, {f});")
                        if ü.tənbəl or "tənbəl" in annot:
                            n.append(f"{S}.tənbəllər.add({_js_mətn(ü.ad)});")
                        if ü.yaz_gövdəsi is not None:
                            p = A.Parametr(ü.yer, ü.yaz_parametri or "dəyər")
                            f = self._funksiya(ü.ad, [p], ü.yaz_gövdəsi,
                                               növ="metod", özü=True,
                                               sinif_js=S)
                            n.append(f"{S}.yazıcılar.set({_js_mətn(ü.ad)}, {f});")
                    elif ü.statik:
                        d = (self._ifadə(ü.standart)
                             if ü.standart is not None else "null")
                        n.append(f"{S}.statiklər.set({_js_mətn(ü.ad)}, {d});")
                    else:
                        if ü.standart is not None:
                            thunk = self._thunk(ü.standart)
                        else:
                            thunk = "null"
                        t = self._tip_adı(ü.tip)
                        n.append(f"{S}.xassələr.push([{_js_mətn(ü.ad)}, "
                                 f"{thunk}, {_js_mətn(t) if t else 'null'}]);")
                elif isinstance(ü, A.MetodElanı):
                    if ü.mücərrəd or ü.gövdə is None:
                        n.append(f"{S}.mücərrədlər.add({_js_mətn(ü.ad)});")
                        continue
                    annot = [a.ad for a in ü.annotasiyalar]
                    f = self._funksiya(ü.ad, ü.parametrlər, ü.gövdə,
                                       növ="metod", özü=True, sinif_js=S,
                                       generator=ü.generator,
                                       asinxron=ü.asinxron,
                                       yaddaşla="yaddaşla" in annot)
                    hədəf = "statiklər" if ü.statik else "metodlar"
                    n.append(f"{S}.{hədəf}.set({_js_mətn(ü.ad)}, {f});")
                elif isinstance(ü, A.QurucuElanı):
                    f = self._funksiya(ü.ad or "<qurucu>", ü.parametrlər,
                                       ü.gövdə, növ="metod", özü=True,
                                       sinif_js=S, qısa_qurucu=True)
                    n.append(f"{S}.quruculər.set({_js_mətn(ü.ad or '')}, {f});")
                elif isinstance(ü, A.DağıdıcıElanı):
                    continue
                else:
                    self._tara([ü])
                    n.extend(self._cümlə(ü))
        finally:
            self.fk, self.əh = köhnə_fk, köhnə_əh
        return "\n".join(n)

    def _thunk(self, ifadə: A.İfadə) -> str:
        fk = FunksiyaK("thunk", sinif_js=self.fk.sinif_js)
        köhnə_fk, köhnə_əh = self.fk, self.əh
        self.fk = fk
        self.əh = Əhatə(köhnə_əh, fk)
        try:
            d = self._ifadə(ifadə)
            return f"() => {{ {self._tempər_elanı(fk)}return {d}; }}"
        finally:
            self.fk, self.əh = köhnə_fk, köhnə_əh

    def _c_InterfeysElanı(self, c: A.InterfeysElanı) -> str:
        S = self._etiket("C")
        n = []
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı):
                if ü.mücərrəd or ü.gövdə is None:
                    n.append(f"{S}.mücərrədlər.add({_js_mətn(ü.ad)});")
                else:
                    f = self._funksiya(ü.ad, ü.parametrlər, ü.gövdə,
                                       növ="metod", özü=True, sinif_js=S)
                    n.append(f"{S}.metodlar.set({_js_mətn(ü.ad)}, {f});")
        o = (f"{{ad: {_js_mətn(c.ad)}, quruluş: \"interfeys\", "
             "mücərrəd: true}")
        return self._ada_yaz(
            c.ad, f"$.sinif({o}, ({S}) => {{\n" + "\n".join(n) + "\n})", True)

    def _c_QarışıqElanı(self, c: A.QarışıqElanı) -> str:
        S = self._etiket("C")
        gövdə = self._sinif_üzvləri(S, c.üzvlər)
        o = f"{{ad: {_js_mətn(c.ad)}, quruluş: \"qarışıq\"}}"
        return self._ada_yaz(c.ad, f"$.sinif({o}, ({S}) => {{\n{gövdə}\n}})",
                             True)

    def _c_SadalamaElanı(self, c: A.SadalamaElanı) -> str:
        qurucu_p = [p.ad for ü in c.üzvlər if isinstance(ü, A.QurucuElanı)
                    for p in ü.parametrlər]
        variantlar = []
        for v in c.variantlar:
            h = [f"ad: {_js_mətn(v.ad)}"]
            if v.parametrlər:
                h.append("p: " + json.dumps([p.ad for p in v.parametrlər],
                                            ensure_ascii=False))
            else:
                if v.dəyər is not None:
                    h.append(f"d: {self._thunk(v.dəyər)}")
                if c.əsas_tip is not None:
                    h.append("auto: true")
                if v.arqumentlər:
                    s = []
                    for j, arq in enumerate(v.arqumentlər):
                        ad = qurucu_p[j] if j < len(qurucu_p) else f"_{j}"
                        s.append(f"[{_js_mətn(ad)}, {self._ifadə(arq.dəyər)}]")
                    h.append("s: [" + ", ".join(s) + "]")
            variantlar.append("{" + ", ".join(h) + "}")
        metodlar = []
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                f = self._funksiya(ü.ad, ü.parametrlər, ü.gövdə, növ="metod",
                                   özü=True)
                metodlar.append(f"{_js_mətn(ü.ad)}: {f}")
        return self._ada_yaz(
            c.ad, f"$.sadalama({_js_mətn(c.ad)}, [" + ", ".join(variantlar) +
            "], {" + ", ".join(metodlar) + "})", True)

    def _c_TipAliası(self, c: A.TipAliası) -> str:
        try:
            hədəf = self._tip_ref(c.tip) if isinstance(c.tip, A.TipAdı) \
                and c.tip.tam_ad not in SADƏ_TİPLƏR else "null"
        except KompilyasiyaXətası:
            hədəf = "null"
        return self._ada_yaz(
            c.ad, f"new $.TipAlias({_js_mətn(c.ad)}, {hədəf})", True)

    def _c_Genişlətmə(self, c: A.Genişlətmə) -> list[str]:
        ad = c.tip.tam_ad if isinstance(c.tip, A.TipAdı) else ""
        n = []
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                f = self._funksiya(ü.ad, ü.parametrlər, ü.gövdə, növ="metod",
                                   özü=True)
                n.append(f"$.genişlətmə({_js_mətn(ad)}, {_js_mətn(ü.ad)}, {f});")
        return n

    def _c_ModulElanı(self, c: A.ModulElanı) -> str:
        fk = FunksiyaK("blok")
        köhnə_fk, köhnə_əh = self.fk, self.əh
        self.fk = fk
        self.əh = Əhatə(köhnə_əh, fk)
        try:
            gövdə = self._yuxarı_səviyyə(c.gövdə)
            üzvlər = ", ".join(f"[{_js_mətn(a)}, {m.js}]"
                               for a, m in self.əh.adlar.items()
                               if m.elan_edilib)
            js = (f"(() => {{\n{self._tempər_elanı(fk)}" +
                  "\n".join(gövdə) +
                  f"\nreturn new $.Modul({_js_mətn(c.ad)}, new Map([{üzvlər}]));\n}})()")
        finally:
            self.fk, self.əh = köhnə_fk, köhnə_əh
        return self._ada_yaz(c.ad, js, True)

    # ── İdxal ─────────────────────────────────────────────────────────

    @staticmethod
    def _idxal_adı(c: A.İdxal) -> str:
        if c.ləqəb:
            return c.ləqəb
        if c.yol:
            return c.yol[-1]
        return Path(c.mətn_yolu or "modul").stem

    def _idxal_hamısı_adları(self, c: A.İdxal) -> list[str]:
        ad = c.mətn_yolu or ".".join(c.yol)
        if ad in DƏSTƏKLƏNƏN_MODULLAR:
            return _std_üzvlər(ad)
        yol = self._fayl_yolu(c)
        if yol is not None:
            return self._fayl_üst_adları(yol)
        return []

    def _fayl_yolu(self, c: A.İdxal) -> Path | None:
        ad = c.mətn_yolu or ".".join(c.yol)
        baza = (Path(c.yer.mənbə.yol).resolve().parent
                if c.yer is not None and getattr(c.yer, "mənbə", None)
                is not None and getattr(c.yer.mənbə, "yol", None)
                else (self.əsas_yol.parent if self.əsas_yol else Path.cwd()))
        if ad.endswith((".alq", ".alqor")) or ad.startswith((".", "/")):
            p = Path(ad)
            if not p.is_absolute():
                p = baza / p
            if not p.exists():
                for u in (".alq", ".alqor"):
                    if Path(str(p) + u).exists():
                        p = Path(str(p) + u)
                        break
            return p.resolve() if p.exists() else None
        from ..paketler import paket_tap
        t = paket_tap(ad, baza)
        return t.resolve() if t is not None else None

    def _fayl_ağacı(self, yol: Path) -> A.Proqram:
        from ..lekser import Lekser
        from ..menbe import Mənbə
        from ..parser import Parser
        from ..xeta import XətaToplayıcı
        x = XətaToplayıcı()
        s = Mənbə.fayldan(yol, x)
        if s is None:
            raise KompilyasiyaXətası(f'"{yol}" oxunmadı')
        ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        if not x.uğurludur():
            raise KompilyasiyaXətası(
                f'"{yol.name}" modulunda {len(x.xətalar)} xəta var:\n'
                + x.hesabat(False))
        return ağac

    def _fayl_üst_adları(self, yol: Path) -> list[str]:
        ağac = self._fayl_ağacı(yol)
        return [a for c in ağac.gövdə for a, _ in self._elan_adları(c)]

    def _fayl_modulu(self, yol: Path) -> str:
        açar = str(yol)
        if açar in self.fayl_modulları or açar in self._yüklənən:
            return açar
        self._yüklənən.add(açar)
        ağac = self._fayl_ağacı(yol)
        fk = FunksiyaK("blok")
        köhnə_fk, köhnə_əh = self.fk, self.əh
        self.fk = fk
        self.əh = Əhatə(None, fk)
        try:
            gövdə = self._yuxarı_səviyyə(ağac.gövdə)
            qoy = "\n".join(f"$M.üzvlər.set({_js_mətn(a)}, {m.js});"
                            for a, m in self.əh.adlar.items()
                            if m.elan_edilib)
            js = (f"$.faylQeyd({_js_mətn(açar)}, {_js_mətn(yol.stem)}, "
                  f"($M) => {{\n{self._tempər_elanı(fk)}" +
                  "\n".join(gövdə) + f"\n{qoy}\n}});")
        finally:
            self.fk, self.əh = köhnə_fk, köhnə_əh
        self.fayl_modulları[açar] = js
        return açar

    def _c_İdxal(self, c: A.İdxal) -> list[str]:
        ad = c.mətn_yolu or ".".join(c.yol)
        kök = ad.split(".")[0]
        if c.mətn_yolu is None and kök == "veb" and self.interfeys:
            # İnterfeys proqramının veb budağı (`-- veb` arqumenti) — statik
            # saytda server yoxdur, `veb.*` çağırışı icra xətası verir
            self.lazımi.add("veb")
            modul = f"$.modul({_js_mətn(ad)})"
        elif c.mətn_yolu is None and (ad in DƏSTƏKLƏNƏN_MODULLAR):
            if kök in ƏLAVƏ_MODULLAR:
                self.lazımi.add(kök)
            modul = f"$.modul({_js_mətn(ad)})"
        elif c.mətn_yolu is None and (kök in DƏSTƏKLƏNMƏYƏN_MODULLAR):
            raise KompilyasiyaXətası(
                f"`{ad}` modulu JS hədəfində dəstəklənmir — bu proqramı "
                "Python icraçısı ilə işlədin (`alqor işlət`)", c.yer)
        else:
            yol = self._fayl_yolu(c)
            if yol is None:
                return [f"throw $.xəta(\"ArqumentXətası\", "
                        f"{_js_mətn(f'`{ad}` modulu tapılmadı')}, \"ALQ-M001\");"]
            açar = self._fayl_modulu(yol)
            modul = f"$.faylModul({_js_mətn(açar)})"
        if c.hamısı:
            t = self._temp()
            n = [f"{t} = {modul};"]
            for a in self._idxal_hamısı_adları(c):
                n.append(self._ada_yaz(
                    a, f"$.idxalElement({t}, {_js_mətn(ad)}, {_js_mətn(a)})",
                    True))
            return n
        if c.elementlər:
            t = self._temp()
            n = [f"{t} = {modul};"]
            for e in c.elementlər:
                n.append(self._ada_yaz(
                    e.ləqəb or e.ad,
                    f"$.idxalElement({t}, {_js_mətn(ad)}, {_js_mətn(e.ad)})",
                    True))
            return n
        return [self._ada_yaz(self._idxal_adı(c), modul, True)]

    # ═══════════════════════════════════════════════════════════════════
    #  İfadələr
    # ═══════════════════════════════════════════════════════════════════

    def _ifadə(self, e: A.İfadə) -> str:
        f = getattr(self, "_e_" + type(e).__name__, None)
        if f is None:
            raise KompilyasiyaXətası(
                f"`{type(e).__name__}` ifadəsi JS hədəfində dəstəklənmir",
                getattr(e, "yer", None))
        return f(e)

    @staticmethod
    def _məntiqidir(e: A.İfadə) -> bool:
        if isinstance(e, A.İkili) and e.op in MƏNTİQİ_OPLAR:
            return True
        if isinstance(e, A.TəkOperand) and e.op in ("deyil", "!"):
            return True
        if isinstance(e, A.Literal) and e.növ == "məntiq":
            return True
        return isinstance(e, (A.TipYoxlama, A.Üzvlük, A.BoşYoxlama))

    def _şərt(self, e: A.İfadə) -> str:
        if self._məntiqidir(e):
            return self._ifadə(e)
        return f"$.ş({self._ifadə(e)})"

    # ── Literallar ────────────────────────────────────────────────────

    def _e_Literal(self, e: A.Literal) -> str:
        d = e.dəyər
        if d is None:
            return "null"
        if d is True:
            return "true"
        if d is False:
            return "false"
        if isinstance(d, int):
            return f"{d}n"
        if isinstance(d, float):
            if d != d:
                return "NaN"
            if d in (float("inf"), float("-inf")):
                return "Infinity" if d > 0 else "-Infinity"
            return f"({d!r})"
        if isinstance(d, bytes):
            return f"new $.Bayt(Uint8Array.of({', '.join(map(str, d))}))"
        return _js_mətn(str(d))

    def _e_ŞablonMətn(self, e: A.ŞablonMətn) -> str:
        h = []
        for p in e.parçalar:
            if isinstance(p, A.MətnHissəsi):
                h.append(_js_mətn(p.dəyər))
            elif p.format:
                h.append(f"$.formatla({self._ifadə(p.ifadə)}, "
                         f"{_js_mətn(p.format)})")
            else:
                h.append(f"$.mətnə({self._ifadə(p.ifadə)})")
        if not h:
            return '""'
        return "(" + " + ".join(h if isinstance(e.parçalar[0], A.MətnHissəsi)
                                else ['""'] + h) + ")"

    def _e_Ad(self, e: A.Ad) -> str:
        return self._ad_js(e.ad)

    def _e_Özü(self, e: A.Özü) -> str:
        return "özü" if self.fk.özü else "$.qad(\"özü\")"

    def _e_Üst(self, e: A.Üst) -> str:
        if not (self.fk.özü and self.fk.sinif_js):
            return "$.qad(\"özü\")"
        return f"new $.Üst(özü, {self.fk.sinif_js})"

    # ── Operatorlar ───────────────────────────────────────────────────

    def _e_İkili(self, e: A.İkili) -> str:
        op = e.op
        if op in ("və", "&&"):
            return f"({self._şərt(e.sol)} ? {self._şərt(e.sağ)} : false)"
        if op in ("və ya", "||"):
            return f"({self._şərt(e.sol)} ? true : {self._şərt(e.sağ)})"
        if op == "??":
            t = self._temp()
            return (f"(({t} = {self._ifadə(e.sol)}) === null ? "
                    f"{self._ifadə(e.sağ)} : {t})")
        sol, sağ = self._ifadə(e.sol), self._ifadə(e.sağ)
        return self._ikili_js(op, sol, sağ)

    @staticmethod
    def _ikili_js(op: str, sol: str, sağ: str) -> str:
        f = İKİLİ_FUNKSİYALAR.get(op)
        if f:
            return f"$.{f}({sol}, {sağ})"
        if op in BİT_OPLARI:
            return f"$.bit({_js_mətn(op)}, {sol}, {sağ})"
        raise KompilyasiyaXətası(f"naməlum operator `{op}`")

    def _e_TəkOperand(self, e: A.TəkOperand) -> str:
        if e.op in ("deyil", "!"):
            return f"!{self._şərt(e.operand)}"
        d = self._ifadə(e.operand)
        if e.op == "-":
            if isinstance(e.operand, A.Literal) and \
                    isinstance(e.operand.dəyər, (int, float)) and \
                    not isinstance(e.operand.dəyər, bool):
                return f"(-{d})"
            return f"$.neg({d})"
        if e.op == "+":
            return d
        if e.op == "~":
            return f"$.bnot({d})"
        raise KompilyasiyaXətası(f"naməlum tək operator `{e.op}`", e.yer)

    # ── Mənimsətmə ────────────────────────────────────────────────────

    def _mənimsət_js(self, hədəf: A.İfadə, dəyər_f) -> str:
        """
        Hədəfə yazır. `dəyər_f(cari)` yeni dəyəri qaytarır; `cari`
        hədəfin indiki dəyəridir (lazım olsa).
        """
        if isinstance(hədəf, A.Ad):
            cari = self._ad_js(hədəf.ad)
            return self._ad_mənimsət(hədəf.ad, f"$.kp({dəyər_f(cari)})")
        if isinstance(hədəf, A.Üzv):
            o = self._temp()
            v = self._temp()
            cari = f"$.üzv({self._ifadə(hədəf.obyekt)}, {_js_mətn(hədəf.ad)})"
            return (f"({v} = {dəyər_f(cari)}, {o} = {self._ifadə(hədəf.obyekt)}, "
                    f"$.üzvQoy({o}, {_js_mətn(hədəf.ad)}, {v}), {v})")
        if isinstance(hədəf, A.İndeks):
            o, i, v = self._temp(), self._temp(), self._temp()
            cari = f"$.ind({self._ifadə(hədəf.obyekt)}, {self._ifadə(hədəf.indeks)})"
            return (f"({v} = {dəyər_f(cari)}, {o} = {self._ifadə(hədəf.obyekt)}, "
                    f"{i} = {self._ifadə(hədəf.indeks)}, $.indQoy({o}, {i}, {v}), {v})")
        if isinstance(hədəf, A.KortejLiteralı):
            t = self._temp()
            el = self._temp()
            h = [f"{t} = {dəyər_f(None)}", f"{el} = $.siyahıya({t})"]
            for j, alt in enumerate(hədəf.elementlər):
                h.append(f"({el}.length > {j} ? "
                         f"{self._mənimsət_js(alt, lambda _c, j=j: f'{el}[{j}]')} : null)")
            return "(" + ", ".join(h) + f", {t})"
        return ("$.xətaAt(\"ArqumentXətası\", "
                "\"bu ifadəyə mənimsətmə mümkün deyil\", \"ALQ-T001\")")

    def _e_Mənimsətmə(self, e: A.Mənimsətmə) -> str:
        if len(e.hədəflər) > 1 or len(e.dəyərlər) > 1:
            tempər = []
            h = []
            for d in e.dəyərlər:
                t = self._temp()
                h.append(f"{t} = {self._ifadə(d)}")
                tempər.append(t)
            if len(tempər) == 1:
                t = self._temp()
                h.append(f"{t} = $.dağıt({tempər[0]}, {len(e.hədəflər)}, -1)")
                tempər = [f"{t}[{i}]" for i in range(len(e.hədəflər))]
            elif len(tempər) != len(e.hədəflər):
                return ("$.xətaAt(\"ArqumentXətası\", "
                        "\"mənimsətmədə saylar uyğun gəlmir\", \"ALQ-T001\")")
            for hd, t in zip(e.hədəflər, tempər):
                h.append(self._mənimsət_js(hd, lambda _c, t=t: t))
            return "(" + ", ".join(h) + ", null)"
        hədəf = e.hədəflər[0]
        dəyər = self._ifadə(e.dəyərlər[0])
        if e.op == "=":
            return self._mənimsət_js(hədəf, lambda _c: dəyər)
        if e.op in ("??=", "?="):
            t = self._temp()
            cari = self._ifadə(hədəf)
            return (f"(({t} = $.təhlükəsiz(() => {cari})) !== null ? {t} : "
                    f"{self._mənimsət_js(hədəf, lambda _c: dəyər)})")
        op = e.op[:-1]
        return self._mənimsət_js(
            hədəf, lambda cari: self._ikili_js(op, cari, dəyər))

    # ── Müraciət ──────────────────────────────────────────────────────

    def _e_Üzv(self, e: A.Üzv) -> str:
        if isinstance(e.obyekt, A.Üst) and self.fk.sinif_js and self.fk.özü:
            return f"$.üstMetod({self.fk.sinif_js}, özü, {_js_mətn(e.ad)})"
        o = self._ifadə(e.obyekt)
        if e.təhlükəsiz:
            return f"$.üzv({o}, {_js_mətn(e.ad)}, true)"
        return f"$.üzv({o}, {_js_mətn(e.ad)})"

    def _e_İndeks(self, e: A.İndeks) -> str:
        return f"$.ind({self._ifadə(e.obyekt)}, {self._ifadə(e.indeks)})"

    def _e_Dilim(self, e: A.Dilim) -> str:
        b = self._ifadə(e.başlanğıc) if e.başlanğıc is not None else "null"
        s = self._ifadə(e.son) if e.son is not None else "null"
        return (f"$.dilim({self._ifadə(e.obyekt)}, {b}, {s}, "
                f"{'true' if e.xaric else 'false'})")

    def _arqumentlər(self, arqumentlər: list[A.Arqument]) -> list[str]:
        n: list[str] = []
        adlı: list[str] = []
        for a in arqumentlər:
            d = self._ifadə(a.dəyər)
            if a.yayma:
                n.append(f"...$.siyahıya({d})")
            elif a.ad:
                adlı.append(f"{_js_mətn(a.ad)}: {d}")
            else:
                n.append(d)
        if adlı:
            n.append("new $.Adlı({" + ", ".join(adlı) + "})")
        return n

    def _e_Çağırış(self, e: A.Çağırış) -> str:
        arq = self._arqumentlər(e.arqumentlər)
        f = e.funksiya
        if isinstance(f, A.Üzv) and not isinstance(f.obyekt, A.Üst):
            o = self._ifadə(f.obyekt)
            hissə = ", ".join([_js_mətn(f.ad)] + arq)
            if f.təhlükəsiz:
                t = self._temp()
                return f"(({t} = {o}) === null ? null : $.çm({t}, {hissə}))"
            return f"$.çm({o}, {hissə})"
        return f"$.ç({', '.join([self._ifadə(f)] + arq)})"

    def _e_Yeni(self, e: A.Yeni) -> str:
        arq = self._arqumentlər(e.arqumentlər)
        q = _js_mətn(e.qurucu) if e.qurucu else "null"
        return f"$.yeni({', '.join([self._tip_ref(e.tip), q] + arq)})"

    def _e_Çevirmə(self, e: A.Çevirmə) -> str:
        h = e.tip.tam_ad if isinstance(e.tip, A.TipAdı) else ""
        f = "çevirT" if e.təhlükəsiz else "çevir"
        return f"$.{f}({self._ifadə(e.ifadə)}, {_js_mətn(h)})"

    def _e_TipYoxlama(self, e: A.TipYoxlama) -> str:
        return f"$.tipUyğun({self._ifadə(e.ifadə)}, {self._tip_spec(e.tip)})"

    def _e_Üzvlük(self, e: A.Üzvlük) -> str:
        return f"$.üzvlük({self._ifadə(e.element)}, {self._ifadə(e.kolleksiya)})"

    def _e_BoşYoxlama(self, e: A.BoşYoxlama) -> str:
        op = "!==" if e.inkar else "==="
        return f"({self._ifadə(e.ifadə)} {op} null)"

    def _e_Boru(self, e: A.Boru) -> str:
        return f"$.boru({self._ifadə(e.dəyər)}, {self._ifadə(e.funksiya)})"

    def _e_MəcburiAçma(self, e: A.MəcburiAçma) -> str:
        return f"$.açMəcburi({self._ifadə(e.ifadə)})"

    def _e_Yayma(self, e: A.Yayma) -> str:
        return f"$.yay({self._ifadə(e.ifadə)})"

    def _e_Gözlə(self, e: A.Gözlə) -> str:
        return f"$.gözlə({self._ifadə(e.ifadə)})"

    # ── Kolleksiyalar ─────────────────────────────────────────────────

    def _e_SiyahıLiteralı(self, e: A.SiyahıLiteralı) -> str:
        yaymalar = e.yaymalar or [False] * len(e.elementlər)
        return "[" + ", ".join(
            (f"...$.siyahıya({self._ifadə(x)})" if y else self._ifadə(x))
            for x, y in zip(e.elementlər, yaymalar)) + "]"

    def _e_LüğətLiteralı(self, e: A.LüğətLiteralı) -> str:
        h = []
        for a, d in zip(e.açarlar, e.dəyərlər):
            if a is None:
                h.append(f"[$.YOX, {self._ifadə(d)}]")
            else:
                h.append(f"[{self._ifadə(a)}, {self._ifadə(d)}]")
        return "$.lüğətLit([" + ", ".join(h) + "])"

    def _e_DəstLiteralı(self, e: A.DəstLiteralı) -> str:
        return ("new $.Dəst([" +
                ", ".join(self._ifadə(x) for x in e.elementlər) + "])")

    def _e_KortejLiteralı(self, e: A.KortejLiteralı) -> str:
        return ("new $.Kortej([" +
                ", ".join(self._ifadə(x) for x in e.elementlər) + "])")

    def _e_Diapazon(self, e: A.Diapazon) -> str:
        a = self._ifadə(e.addım) if e.addım is not None else "null"
        return (f"$.diapazon({self._ifadə(e.başlanğıc)}, {self._ifadə(e.son)}, "
                f"{a}, {'true' if e.xaric else 'false'})")

    def _iç_funksiya(self, növ: str, qur) -> str:
        """İçəridə yeni funksiya konteksti ilə IIFE qurur."""
        fk = FunksiyaK(növ, sinif_js=self.fk.sinif_js, özü=self.fk.özü)
        köhnə_fk, köhnə_əh = self.fk, self.əh
        self.fk = fk
        self.əh = Əhatə(köhnə_əh, fk)
        try:
            gövdə = qur()
            return f"(() => {{\n{self._tempər_elanı(fk)}{gövdə}\n}})()"
        finally:
            self.fk, self.əh = köhnə_fk, köhnə_əh

    def _e_Qurma(self, e: A.Qurma) -> str:
        def qur() -> str:
            mənbə = self._ifadə(e.mənbə)
            r = self._temp()
            x = self._temp()
            başlanğıc = "new $.Lüğət()" if e.növ == "lüğət" else "[]"
            n = [f"{r} = {başlanğıc};",
                 f"for (const {x}_ of $.iter({mənbə})) {{"]
            köhnə = self.əh
            self.əh = self._əhatə()
            try:
                for a in self._bağlama_adları(e.bağlama):
                    self._qeyd(a)
                n.extend(self._bağla(e.bağlama, f"{x}_", True))
                if e.şərt is not None:
                    n.append(f"if (!{self._şərt(e.şərt)}) continue;")
                if e.növ == "lüğət":
                    n.append(f"{r}.qoy({self._ifadə(e.ifadə)}, "
                             f"{self._ifadə(e.dəyər_ifadəsi)});")
                else:
                    n.append(f"{r}.push({self._ifadə(e.ifadə)});")
            finally:
                self.əh = köhnə
            n.append("}")
            if e.növ == "dəst":
                n.append(f"return new $.Dəst({r});")
            elif e.növ == "generator":
                n.append(f"return new $.Gen({r}[Symbol.iterator]());")
            else:
                n.append(f"return {r};")
            return "\n".join(n)
        return self._iç_funksiya("qurma", qur)

    def _e_ŞərtIfadəsi(self, e: A.ŞərtIfadəsi) -> str:
        n = ""
        for şərt, d in e.budaqlar:
            n += f"{self._şərt(şərt)} ? {self._ifadə(d)} : "
        n += self._ifadə(e.yoxsa) if e.yoxsa is not None else "null"
        return f"({n})"

    def _e_BlokIfadəsi(self, e: A.BlokIfadəsi) -> str:
        def qur() -> str:
            self._tara(e.gövdə)
            n = []
            for c in e.gövdə:
                n.extend(self._cümlə(c))
            n.append("return null;")
            return "\n".join(n)
        return self._iç_funksiya("blok", qur)

    def _e_Lambda(self, e: A.Lambda) -> str:
        f = self._funksiya("<lambda>", e.parametrlər, e.gövdə,
                           generator=e.generator, asinxron=e.asinxron)
        if e.tutmalar:
            # `[x] (...) => ...` — tutulan adlar yaradılma anında kopyalanır
            adlar = [self._ad_js(a) for a in e.tutmalar]
            return (f"(({', '.join(adlar)}) => {f})"
                    f"({', '.join(adlar)})")
        return f

    # ── JSX ───────────────────────────────────────────────────────────

    def _e_JSXElement(self, e: A.JSXElement) -> str:
        atr = []
        for a in e.atributlar:
            if a.yayma:
                atr.append(f"{{y: true, d: {self._ifadə(a.dəyər)}}}")
            else:
                d = "true" if a.dəyər is None else self._ifadə(a.dəyər)
                atr.append(f"{{a: {_js_mətn(a.ad)}, d: {d}}}")
        uşaqlar = self._jsx_uşaqlar(e.uşaqlar)
        hədəf = "void 0"
        if e.komponentdir:
            hissələr = e.ad.split(".")
            hədəf = self._ad_js(hissələr[0])
            for h in hissələr[1:]:
                hədəf = f"$.üzv({hədəf}, {_js_mətn(h)})"
        return (f"$.jsx({_js_mətn(e.ad)}, {hədəf}, [{', '.join(atr)}], "
                f"[{', '.join(uşaqlar)}])")

    def _e_JSXParça(self, e: A.JSXParça) -> str:
        return f"$.jsx(\"\", void 0, [], [{', '.join(self._jsx_uşaqlar(e.uşaqlar))}])"

    def _jsx_uşaqlar(self, uşaqlar) -> list[str]:
        return [_js_mətn(u.dəyər) if isinstance(u, A.JSXMətn)
                else self._ifadə(u) for u in uşaqlar]


# ═══════════════════════════════════════════════════════════════════════
#  Standart modul üzvləri (`gətir riyaziyyat.*` üçün)
# ═══════════════════════════════════════════════════════════════════════

_STD_ÜZVLƏR: dict[str, list[str]] | None = None


def _std_üzvlər(ad: str) -> list[str]:
    global _STD_ÜZVLƏR
    if _STD_ÜZVLƏR is None:
        mətn = İCRA_JS.read_text(encoding="utf-8")
        _STD_ÜZVLƏR = {}
        for m in re.finditer(r'modullar\["([^"]+)"\] = \(\) => new Modul\('
                             r'"[^"]+", \{(.*?)\n\}', mətn, re.S):
            _STD_ÜZVLƏR[m.group(1)] = re.findall(
                r'^\s*"([^"]+)":', m.group(2), re.M) + re.findall(
                r', "([^"]+)": ', m.group(2))
    return list(dict.fromkeys(_STD_ÜZVLƏR.get(ad, [])))


# ═══════════════════════════════════════════════════════════════════════
#  İctimai API
# ═══════════════════════════════════════════════════════════════════════

def icra_mühiti(lazımi: set[str] | frozenset[str] | None = None) -> str:
    """icra.js və (lazım olsa) əlavə modullar: vidjet, pəncərə, http."""
    n = [İCRA_JS.read_text(encoding="utf-8")]
    for ad in əlavə_sırası(lazımi or ()):
        n.append(əlavə_modul(ad))
    return "\n".join(n)


def əlavə_sırası(lazımi) -> list[str]:
    adlar = set(lazımi)
    if "veb" in adlar:
        adlar.add("pəncərə")
    return [a for a in ƏLAVƏ_MODULLAR if a in adlar]


def əlavə_modul(ad: str) -> str:
    if ad == "vidjet":
        from .vidjet_cevir import vidjet_modulu
        return vidjet_modulu()
    if ad == "pəncərə":
        return (KÖK / "pencere.js").read_text(encoding="utf-8")
    if ad == "http":
        return (KÖK / "http.js").read_text(encoding="utf-8")
    if ad == "veb":
        return VEB_QARALAMA
    raise KeyError(ad)


# `veb` serveri brauzerdə yoxdur: interfeys proqramının veb budağı
# kompilyasiya olunur, amma çağırılanda aydın xəta verir.
VEB_QARALAMA = """(function ($) {
const yox = a => $.D(a, 0, null, () => { throw $.xəta("ArqumentXətası",
  "`veb." + a + "` JS hədəfində (brauzerdə) dəstəklənmir — veb serveri üçün " +
  "proqramı Python ilə işlədin (`alqor işlət`, `alqor yerləşdir --server`)", "ALQ-M002"); });
const ü = {};
for (const a of ["Server", "mətn", "html", "json", "boş", "yönləndir", "yönləndirDaimi",
  "xəta", "fayl", "yüklə", "şablon", "şablonQovluğu", "jurnal", "CORS", "sıxma",
  "təhlükəsizlikBaşlıqları", "sessiya", "sürətLimiti", "boşPort"]) ü[a] = yox(a);
ü["sınaq"] = new $.Modul("veb.sınaq", { "server": yox("sınaq.server") });
$.modulQeyd("veb", () => new $.Modul("veb", ü));
})($);
"""


def kompilyasiya(ağac: A.Proqram, əsas_yol: Path | None = None) -> str:
    """Proqramı `$.işlət(...)`-ə verilə bilən funksiya mətninə çevirir.

    Qaytarır: icra mühiti olmadan, yalnız proqram hissəsi (speclər,
    fayl modulları və `const $proqram = function () {...};`).
    """
    return kompilyasiya_tam(ağac, əsas_yol)[0]


def kompilyasiya_tam(ağac: A.Proqram, əsas_yol: Path | None = None
                     ) -> tuple[str, set[str]]:
    """(proqram JS-i, lazım olan əlavə modullar)."""
    k = Kompilyator(əsas_yol)
    proqram = k.proqram(ağac)
    js = ("\n".join(k.speclər) + "\n" +
          "\n".join(k.fayl_modulları.values()) + "\n" +
          f"const $proqram = {proqram};\n")
    return js, k.lazımi


def node_faylı(ağac: A.Proqram, əsas_yol: Path | None = None) -> str:
    """Node.js ilə işləyən tam fayl."""
    js, lazımi = kompilyasiya_tam(ağac, əsas_yol)
    return ("#!/usr/bin/env node\n" + icra_mühiti(lazımi) + "\n" + js +
            "if (typeof require !== \"undefined\" && require.main === module) {\n"
            "  $.P.arqumentlər = process.argv.slice(2);\n"
            "  process.exitCode = $.işlət($proqram);\n"
            "} else if (typeof module !== \"undefined\") {\n"
            "  module.exports = { $, $proqram };\n"
            "}\n")


VEB_ŞABLON = """<!doctype html>
<html lang="az">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{başlıq}</title>
<style>
  :root {{ color-scheme: light dark; --fon: #fbfaf7; --mətn: #1d1d1f;
          --xəta: #b3261e; --kənar: #d9d6cf; --giriş: #1a5fb4; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --fon: #17181a; --mətn: #e8e6e3; --xəta: #ff8a80; --kənar: #34363a; --giriş: #8ab4f8; }}
  }}
  body {{ margin: 0; background: var(--fon); color: var(--mətn);
         font: 15px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  header {{ padding: 12px 16px; border-bottom: 1px solid var(--kənar);
           font-family: system-ui, sans-serif; font-weight: 600; }}
  #çıxış {{ margin: 0; padding: 16px; white-space: pre-wrap; word-break: break-word; }}
  .xəta {{ color: var(--xəta); }}
  .giriş {{ color: var(--giriş); }}
</style>
</head>
<body>
<header>{başlıq}</header>
<pre id="çıxış"></pre>
<script>
{icra}
{proqram}
(function () {{
  const çıxış = document.getElementById("çıxış");
  function əlavə(s, sinif) {{
    const span = document.createElement("span");
    if (sinif) span.className = sinif;
    span.textContent = s;
    çıxış.appendChild(span);
  }}
  $.işlət($proqram, {{
    yaz: s => əlavə(s + "\\n"),
    yazSətirsiz: s => əlavə(s),
    yazXəta: s => əlavə(s + "\\n", "xəta"),
    oxu: () => {{
      const c = prompt(çıxış.textContent.split("\\n").pop() || "");
      if (c !== null) əlavə(c + "\\n", "giriş");
      return c;
    }},
  }});
}})();
</script>
</body>
</html>
"""


İNTERFEYS_ŞABLON = """<!DOCTYPE html>
<html lang="az">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{başlıq}</title>
<style>{üslub}</style>
</head>
<body>
<nav id="alqor-menyu" class="menyu-sətri" hidden></nav>
<main id="alqor-kök"></main>
<script>
{icra}
{proqram}
(function () {{
{nüvə}
 try {{ const t = new URLSearchParams(location.search).get("tema");
  if (t === "qaranlıq" || t === "işıqlı") document.documentElement.dataset.tema = t; }}
 catch (e) {{}}
 window.$alqorYamaq = yamaq;
 const kök = document.getElementById("alqor-kök");
 const menyu = document.getElementById("alqor-menyu");
 const qaç = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
 let bağlı = false;
 // Hadisə serverə yox, birbaşa icra mühitinə gedir (pencere.py-dəki
 // `/_alqor/hadise` sorğusunun qarşılığı)
 async function göndər(id, dəyər) {{
  if (bağlı) return;
  const n = $.UI.hadisə(id, dəyər === undefined ? null : dəyər);
  if (n.xəta) {{ kök.innerHTML = '<pre id="alqor-xəta">' + qaç(n.xəta) + "</pre>"; return; }}
  if (n.bağlı) {{ bağlı = true; return; }}
  if (n.üslub !== undefined) {{
   const ü = document.getElementById("alqor-pəncərə-üslubu");
   if (ü && ü.textContent !== n.üslub) ü.textContent = n.üslub;
  }}
  if (n.html !== undefined) yamaq(kök, n.html);
  if (n.menyu !== undefined && menyu) {{ menyu.innerHTML = n.menyu; menyu.hidden = !n.menyu; }}
  if (n.başlıq) document.title = n.başlıq;
 }}
 alqorBağla(göndər);
 // Menyu qısayolları
 document.addEventListener("keydown", function (h) {{
  const hissələr = [];
  if (h.ctrlKey) hissələr.push("ctrl");
  if (h.metaKey) hissələr.push("meta");
  if (h.altKey) hissələr.push("alt");
  if (h.shiftKey) hissələr.push("shift");
  const a = h.key.toLowerCase();
  if (["control", "meta", "alt", "shift"].includes(a)) return;
  hissələr.push(a);
  const t = document.querySelector('[data-a-qisayol="' + hissələr.join("+") + '"]');
  if (t) {{ h.preventDefault(); göndər(t.getAttribute("data-a-klik")); }}
 }});
 // Konsol çıxışı (`yaz`) brauzer konsoluna gedir; pəncərə açılmayıbsa
 // səhifədə göstərilir
 const çıxış = [];
 $.işlət($proqram, {{
  yaz: s => {{ çıxış.push(s + "\\n"); console.log(s); }},
  yazSətirsiz: s => {{ çıxış.push(s); console.log(s); }},
  yazXəta: s => {{ çıxış.push(s + "\\n"); console.error(s); }},
  xəta: e => {{ console.error(e); $.UI.xətanıGöstər(e); }},
 }});
 if (!kök.firstChild && çıxış.length) {{
  const p = document.createElement("pre");
  p.style.cssText = "margin:0;white-space:pre-wrap;font-family:ui-monospace,monospace";
  p.textContent = çıxış.join("");
  kök.appendChild(p);
 }}
}})();
</script>
</body>
</html>
"""


def veb_səhifəsi(ağac: A.Proqram, başlıq: str = "Alqor",
                 əsas_yol: Path | None = None) -> str:
    """Brauzerdə serversiz işləyən tək HTML səhifə.

    `pəncərə` idxal edən proqram interfeys səhifəsi alır (menyu sətri,
    `#alqor-kök`, vidjet üslubu, hadisələr) — qalanları konsol səhifəsi.
    """
    import html
    js, lazımi = kompilyasiya_tam(ağac, əsas_yol)
    proqram = js.replace("</script", "<\\/script")
    icra = icra_mühiti(lazımi).replace("</script", "<\\/script")
    if "pəncərə" in lazımi:
        from ..pencere import NÜVƏ_SKRİPTİ, ÜSLUB
        from ..vidjet import ÜSLUB as VİDJET_ÜSLUBU
        return İNTERFEYS_ŞABLON.format(
            başlıq=html.escape(başlıq),
            üslub=(ÜSLUB + VİDJET_ÜSLUBU).replace("</style", "<\\/style"),
            icra=icra, proqram=proqram, nüvə=NÜVƏ_SKRİPTİ)
    return VEB_ŞABLON.format(başlıq=html.escape(başlıq), icra=icra,
                             proqram=proqram)


def mətndən(kod: str, ad: str = "<yaddaş>") -> str:
    """Mənbə mətnini birbaşa node faylına çevirir (sınaqlar üçün)."""
    from ..lekser import Lekser
    from ..menbe import Mənbə
    from ..parser import Parser
    from ..xeta import XətaToplayıcı
    x = XətaToplayıcı()
    s = Mənbə.mətndən(kod, ad, x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise KompilyasiyaXətası("ayırma xətası:\n" + x.hesabat(False))
    return node_faylı(ağac)
