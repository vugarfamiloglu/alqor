"""
Alqor — Şablon mühərriki (`.alqorhtml`).

Spesifikasiya § 11.3. Sintaksis:

    {{ ifadə }}                 dəyər — HTML-qaçış AVTOMATİKDİR
    {{ ifadə | filtr }}         filtrlə
    {{ ifadə | xam }}           qaçışsız (diqqətli olun — XSS)
    {% əgər şərt %} … {% yoxsa %} … {% son %}
    {% hər x üçün siyahı içində %} … {% yoxsa %} … {% son %}
    {% daxilEt "altbilgi.alqorhtml" %}
    {% genişlət "əsas.alqorhtml" %}
    {% blok məzmun %} … {% son %}
    {# şərh #}

`{{ }}` və `{% %}` daxilindəki ifadələr HƏQİQİ Alqor ifadələridir —
lekser və parser ilə ayrılır, interpretator ilə qiymətləndirilir.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .deyerler import AlqorXəta, Element, Mühit, mətnə, tip_adı

# ═══════════════════════════════════════════════════════════════════════
#  Tokenləşdirmə
# ═══════════════════════════════════════════════════════════════════════

_PARÇA = re.compile(
    r"\{\{(?P<dəyər>.*?)\}\}"
    r"|\{%(?P<əmr>.*?)%\}"
    r"|\{#(?P<şərh>.*?)#\}",
    re.DOTALL)


@dataclass
class Mətn:
    dəyər: str


@dataclass
class Dəyər:
    ifadə: str
    filtrlər: list[tuple[str, list[str]]] = field(default_factory=list)
    xam: bool = False
    sətir: int = 1
    # Miras zamanı blok uşaq şablondan gəlir, göstərən isə valideyndir —
    # xəta mesajı ifadənin HƏQİQİ faylını göstərməlidir
    fayl: str = ""


@dataclass
class Blok:
    """`əgər`, `hər`, `blok` — gövdəsi olan konstruksiyalar."""
    növ: str
    arqument: str
    gövdə: list[Any] = field(default_factory=list)
    yoxsa: list[Any] | None = None
    sətir: int = 1
    fayl: str = ""


@dataclass
class Daxil:
    yol: str
    sətir: int = 1


class ŞablonXətası(Exception):
    def __init__(self, mesaj: str, fayl: str = "", sətir: int = 0):
        super().__init__(mesaj)
        self.mesaj = mesaj
        self.fayl = fayl
        self.sətir = sətir

    def __str__(self) -> str:
        yer = f" ({self.fayl}:{self.sətir})" if self.fayl else ""
        return f"{self.mesaj}{yer}"


# ═══════════════════════════════════════════════════════════════════════
#  Filtrlər
# ═══════════════════════════════════════════════════════════════════════

def _f_kəs(dəyər: Any, n: str = "100") -> str:
    m = str(dəyər)
    hədd = int(n)
    return m if len(m) <= hədd else m[:hədd] + "…"


def _f_yuvarlaqlaşdır(dəyər: Any, n: str = "0") -> str:
    r = int(n)
    return f"{float(dəyər):.{r}f}" if r else str(round(float(dəyər)))


def _f_pul(dəyər: Any) -> str:
    from .kitabxana import _yerli_ədəd
    return _yerli_ədəd(dəyər, 2) + " ₼"


def _f_format(dəyər: Any, naxış: str = "DD.MM.YYYY") -> str:
    from .kitabxana import _vaxt_formatla
    if isinstance(dəyər, (int, float)):
        return _vaxt_formatla(naxış, dəyər)
    return str(dəyər)


FİLTRLƏR: dict[str, Any] = {
    "böyüyə": lambda d, *a: __import__(
        "alqor.elifba", fromlist=["böyüyə"]).böyüyə(str(d)),
    "kiçiyə": lambda d, *a: __import__(
        "alqor.elifba", fromlist=["kiçiyə"]).kiçiyə(str(d)),
    "başBöyük": lambda d, *a: __import__(
        "alqor.elifba", fromlist=["baş_böyük"]).baş_böyük(str(d)),
    "kəs": _f_kəs,
    "uzunluq": lambda d, *a: str(len(d)) if hasattr(d, "__len__") else "0",
    "yuvarlaqlaşdır": _f_yuvarlaqlaşdır,
    "pul": _f_pul,
    "format": _f_format,
    "standart": lambda d, s="": str(d) if d not in (None, "") else s,
    "tərs": lambda d, *a: str(d)[::-1],
    "latınla": lambda d, *a: __import__(
        "alqor.elifba", fromlist=["latınla"]).latınla(str(d)),
    "URLKodla": lambda d, *a: __import__(
        "urllib.parse", fromlist=["quote"]).quote(str(d), safe=""),
}


# ═══════════════════════════════════════════════════════════════════════
#  HTML qaçışı
# ═══════════════════════════════════════════════════════════════════════

def html_qaç(m: str) -> str:
    return (m.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;")
             .replace("'", "&#39;"))


# ═══════════════════════════════════════════════════════════════════════
#  Ayırıcı
# ═══════════════════════════════════════════════════════════════════════

BLOK_AÇANLAR = ("əgər", "eger", "hər", "her", "blok")
BLOK_SONU = ("son",)
BLOK_YOXSA = ("yoxsa", "əks halda", "eks halda")


def ayır(mətn: str, fayl: str = "<şablon>") -> tuple[list, str | None,
                                                     dict[str, list]]:
    """
    Şablonu ayırır.

    Qaytarır: (qovşaqlar, genişlədilən_şablon, bloklar)
    """
    qovşaqlar, genişlət, bloklar, _ = _ayır_axını(mətn, fayl, 0)
    return qovşaqlar, genişlət, bloklar


def _ayır_axını(mətn: str, fayl: str, başlanğıc: int):
    """Rekursiv ayırma. (qovşaqlar, genişlət, bloklar, son_mövqe)"""
    qovşaqlar: list[Any] = []
    bloklar: dict[str, list] = {}
    genişlət: str | None = None
    yığın: list[Blok] = []
    mövqe = başlanğıc

    def hədəf() -> list:
        if yığın:
            son = yığın[-1]
            return son.yoxsa if son.yoxsa is not None else son.gövdə
        return qovşaqlar

    for uyğun in _PARÇA.finditer(mətn, başlanğıc):
        əvvəl = mətn[mövqe:uyğun.start()]
        if əvvəl:
            hədəf().append(Mətn(əvvəl))
        mövqe = uyğun.end()
        sətir = mətn.count("\n", 0, uyğun.start()) + 1

        if uyğun.group("şərh") is not None:
            continue

        if uyğun.group("dəyər") is not None:
            d = _dəyəri_ayır(uyğun.group("dəyər"), sətir)
            d.fayl = fayl
            hədəf().append(d)
            continue

        əmr = uyğun.group("əmr").strip()
        if not əmr:
            continue
        söz = əmr.split(None, 1)
        ad = söz[0]
        arqument = söz[1].strip() if len(söz) > 1 else ""

        if ad in BLOK_AÇANLAR:
            normal = {"eger": "əgər", "her": "hər"}.get(ad, ad)
            yeni = Blok(normal, arqument, sətir=sətir, fayl=fayl)
            hədəf().append(yeni)
            yığın.append(yeni)
            continue

        if ad in ("yoxsa", "eks") or əmr in BLOK_YOXSA:
            if not yığın:
                raise ŞablonXətası(
                    "`{% yoxsa %}` uyğun bloku yoxdur", fayl, sətir)
            yığın[-1].yoxsa = []
            continue

        if ad in BLOK_SONU:
            if not yığın:
                raise ŞablonXətası(
                    "`{% son %}` uyğun bloku yoxdur", fayl, sətir)
            bitən = yığın.pop()
            if bitən.növ == "blok":
                bloklar[bitən.arqument.strip()] = bitən.gövdə
            continue

        if ad in ("daxilEt", "daxilet"):
            hədəf().append(Daxil(_sitatı_çıxar(arqument), sətir))
            continue

        if ad in ("genişlət", "genislet"):
            genişlət = _sitatı_çıxar(arqument)
            continue

        raise ŞablonXətası(
            f"Naməlum şablon əmri: `{ad}`", fayl, sətir)

    if yığın:
        açıq = yığın[-1]
        raise ŞablonXətası(
            f"`{{% {açıq.növ} %}}` bağlanmayıb — `{{% son %}}` lazımdır",
            fayl, açıq.sətir)

    qalan = mətn[mövqe:]
    if qalan:
        qovşaqlar.append(Mətn(qalan))
    return qovşaqlar, genişlət, bloklar, len(mətn)


def _dəyəri_ayır(xam: str, sətir: int) -> Dəyər:
    hissələr = _boru_ilə_böl(xam)
    ifadə = hissələr[0].strip()
    filtrlər: list[tuple[str, list[str]]] = []
    xam_rejim = False

    for f in hissələr[1:]:
        f = f.strip()
        if not f:
            continue
        if f == "xam":
            xam_rejim = True
            continue
        ad, arqumentlər = _filtri_ayır(f)
        filtrlər.append((ad, arqumentlər))

    return Dəyər(ifadə, filtrlər, xam_rejim, sətir)


def _boru_ilə_böl(mətn: str) -> list[str]:
    """`|` ilə bölür, amma mətn literalı və mötərizə daxilində yox."""
    hissələr: list[str] = []
    cari: list[str] = []
    dərinlik = 0
    sitat = ""
    i = 0
    while i < len(mətn):
        c = mətn[i]
        if sitat:
            cari.append(c)
            if c == "\\" and i + 1 < len(mətn):
                cari.append(mətn[i + 1])
                i += 2
                continue
            if c == sitat:
                sitat = ""
            i += 1
            continue
        if c in ('"', "'"):
            sitat = c
            cari.append(c)
        elif c in "([{":
            dərinlik += 1
            cari.append(c)
        elif c in ")]}":
            dərinlik -= 1
            cari.append(c)
        elif c == "|" and dərinlik == 0 and mətn[i:i + 2] != "||":
            hissələr.append("".join(cari))
            cari = []
        else:
            cari.append(c)
        i += 1
    hissələr.append("".join(cari))
    return hissələr


def _filtri_ayır(f: str) -> tuple[str, list[str]]:
    if "(" not in f:
        return f, []
    ad, qalan = f.split("(", 1)
    arq = qalan.rsplit(")", 1)[0]
    if not arq.strip():
        return ad.strip(), []
    return ad.strip(), [_sitatı_çıxar(a.strip())
                        for a in arq.split(",")]


def _sitatı_çıxar(m: str) -> str:
    m = m.strip()
    if len(m) >= 2 and m[0] == m[-1] and m[0] in ('"', "'"):
        return m[1:-1]
    return m


# ═══════════════════════════════════════════════════════════════════════
#  Şablon
# ═══════════════════════════════════════════════════════════════════════

class Şablon:
    __slots__ = ("qovşaqlar", "genişlət", "bloklar", "ad", "qovluq")

    def __init__(self, mətn: str, ad: str = "<şablon>",
                 qovluq: Path | None = None):
        self.ad = ad
        self.qovluq = qovluq
        self.qovşaqlar, self.genişlət, self.bloklar = ayır(mətn, ad)

    @classmethod
    def fayldan(cls, yol: str | Path,
                qovluq: Path | None = None) -> "Şablon":
        p = Path(yol)
        if not p.exists() and qovluq is not None:
            p = qovluq / yol
        if not p.exists():
            raise ŞablonXətası(f'"{yol}" şablonu tapılmadı')
        return cls(p.read_text(encoding="utf-8"), p.name,
                   qovluq or p.parent)

    def göstər(self, icraçı, verilənlər: dict[str, Any]) -> str:
        return Göstərici(icraçı, self).göstər(verilənlər)


# ═══════════════════════════════════════════════════════════════════════
#  Göstərici
# ═══════════════════════════════════════════════════════════════════════

class Göstərici:
    def __init__(self, icraçı, şablon: Şablon):
        self.i = icraçı
        self.ş = şablon
        # Əvvəllər bir lüğət idi: `{% blok məzmun %}` ilə `{{ məzmun }}`
        # eyni açarı yazır, blokun yerinə ifadə ağacı düşürdü
        self._bloklar: dict[str, list] = {}
        self._ağaclar: dict[str, Any] = {}

    def göstər(self, verilənlər: dict[str, Any]) -> str:
        mühit = self.i.qlobal.alt()
        for ad, dəyər in verilənlər.items():
            mühit.elan(str(ad), dəyər)

        # Miras: valideyn şablon göstərilir, bloklar əvəzlənir
        if self.ş.genişlət:
            valideyn = self._şablonu_yüklə(self.ş.genişlət)
            g = Göstərici(self.i, valideyn)
            g._bloklar = dict(self.ş.bloklar)
            return g._qovşaqları_göstər(valideyn.qovşaqlar, mühit)

        return self._qovşaqları_göstər(self.ş.qovşaqlar, mühit)

    def _şablonu_yüklə(self, yol: str) -> Şablon:
        return Şablon.fayldan(yol, self.ş.qovluq)

    # ── Qovşaqlar ─────────────────────────────────────────────────────

    def _qovşaqları_göstər(self, qovşaqlar: list, m: Mühit) -> str:
        hissələr: list[str] = []
        for q in qovşaqlar:
            hissələr.append(self._qovşaq(q, m))
        return "".join(hissələr)

    def _qovşaq(self, q: Any, m: Mühit) -> str:
        if isinstance(q, Mətn):
            return q.dəyər

        if isinstance(q, Dəyər):
            return self._dəyər(q, m)

        if isinstance(q, Daxil):
            alt = self._şablonu_yüklə(q.yol)
            g = Göstərici(self.i, alt)
            g._bloklar = self._bloklar
            return g._qovşaqları_göstər(alt.qovşaqlar, m)

        if isinstance(q, Blok):
            if q.növ == "əgər":
                return self._əgər(q, m)
            if q.növ == "hər":
                return self._hər(q, m)
            if q.növ == "blok":
                gövdə = self._bloklar.get(q.arqument.strip(), q.gövdə)
                return self._qovşaqları_göstər(gövdə, m)
        return ""

    def _dəyər(self, q: Dəyər, m: Mühit) -> str:
        dəyər = self._qiymətləndir(q.ifadə, m, q.sətir, q.fayl)

        for ad, arqumentlər in q.filtrlər:
            filtr = FİLTRLƏR.get(ad)
            if filtr is None:
                raise ŞablonXətası(
                    f"Naməlum filtr: `{ad}`\n"
                    f"İcazəli filtrlər: {', '.join(sorted(FİLTRLƏR))}",
                    q.fayl or self.ş.ad, q.sətir)
            try:
                dəyər = filtr(dəyər, *arqumentlər)
            except Exception as x:              # noqa: BLE001
                raise ŞablonXətası(
                    f"`{ad}` filtri alınmadı: {x}",
                    q.fayl or self.ş.ad, q.sətir)

        # `boş` HTML-ə "boş" kimi yazılmamalıdır — səhifədə görünməsin.
        # Açıq göstərmək lazımsa: `{{ a | standart("—") }}`.
        if dəyər is None:
            return ""
        if isinstance(dəyər, Element):
            return dəyər.HTML(self.i)
        mətn = mətnə(dəyər, self.i)
        return mətn if q.xam else html_qaç(mətn)

    def _əgər(self, q: Blok, m: Mühit) -> str:
        şərt = self._qiymətləndir(q.arqument, m, q.sətir, q.fayl)
        if not isinstance(şərt, bool):
            # Şablonda rahatlıq üçün boşluq/sıfır da yanlış sayılır
            şərt = self._doğrudur(şərt)
        if şərt:
            return self._qovşaqları_göstər(q.gövdə, m)
        if q.yoxsa is not None:
            return self._qovşaqları_göstər(q.yoxsa, m)
        return ""

    @staticmethod
    def _doğrudur(dəyər: Any) -> bool:
        if dəyər is None or dəyər is False:
            return False
        if isinstance(dəyər, (str, list, dict, set, tuple)):
            return len(dəyər) > 0
        if isinstance(dəyər, (int, float)):
            return dəyər != 0
        return True

    def _hər(self, q: Blok, m: Mühit) -> str:
        # `x üçün siyahı içində` və ya `a, b üçün lüğət içində`
        adlar, mənbə_ifadəsi = self._hər_başlığı(q)
        mənbə = self._qiymətləndir(mənbə_ifadəsi, m, q.sətir, q.fayl)

        try:
            elementlər = list(self.i._iterasiya(mənbə, None))
        except AlqorXəta as x:
            raise ŞablonXətası(
                f"`hər` üzərində dövr qurulmur: {x.mesaj}",
                q.fayl or self.ş.ad, q.sətir)

        if not elementlər and q.yoxsa is not None:
            return self._qovşaqları_göstər(q.yoxsa, m)

        hissələr: list[str] = []
        lüğətdir = isinstance(mənbə, dict)
        for indeks, element in enumerate(elementlər):
            alt = m.alt()
            if len(adlar) == 1:
                alt.elan(adlar[0], element)
            elif lüğətdir:
                alt.elan(adlar[0], element)
                alt.elan(adlar[1], mənbə[element])
            else:
                alt.elan(adlar[0], indeks)
                if len(adlar) > 1:
                    alt.elan(adlar[1], element)
            alt.elan("_indeks", indeks)
            alt.elan("_sayı", len(elementlər))
            alt.elan("_ilkdir", indeks == 0)
            alt.elan("_sondur", indeks == len(elementlər) - 1)
            hissələr.append(self._qovşaqları_göstər(q.gövdə, alt))
        return "".join(hissələr)

    def _hər_başlığı(self, q: Blok) -> tuple[list[str], str]:
        xam = q.arqument
        for üçün in (" üçün ", " ucun "):
            if üçün in xam:
                sol, sağ = xam.split(üçün, 1)
                break
        else:
            raise ŞablonXətası(
                "`hər` başlığı belə olmalıdır: "
                "`{% hər x üçün siyahı içində %}`",
                q.fayl or self.ş.ad, q.sətir)

        adlar = [a.strip() for a in sol.split(",") if a.strip()]
        mənbə = sağ
        for içində in (" içində", " icinde"):
            if mənbə.endswith(içində):
                mənbə = mənbə[:-len(içində)]
                break
        else:
            raise ŞablonXətası(
                "`hər` başlığının sonunda `içində` olmalıdır",
                q.fayl or self.ş.ad, q.sətir)
        if not adlar:
            raise ŞablonXətası("`hər` üçün dəyişən adı yoxdur",
                               q.fayl or self.ş.ad, q.sətir)
        return adlar, mənbə.strip()

    # ── İfadənin qiymətləndirilməsi ───────────────────────────────────

    def _qiymətləndir(self, ifadə: str, m: Mühit, sətir: int,
                      fayl: str = "") -> Any:
        """
        Şablon daxilindəki ifadə HƏQİQİ Alqor ifadəsidir — lekser və
        parser ilə ayrılır, interpretator ilə qiymətləndirilir.
        """
        ifadə = ifadə.strip()
        if not ifadə:
            return ""

        fayl = fayl or self.ş.ad
        ağac = self._ifadə_ağacı(ifadə, sətir, fayl)
        try:
            return self.i._ifadə(ağac, m)
        except AlqorXəta as x:
            raise ŞablonXətası(
                f"`{{{{ {ifadə} }}}}` qiymətləndirilmədi: {x.mesaj}",
                fayl, sətir)

    def _ifadə_ağacı(self, ifadə: str, sətir: int, fayl: str = ""):
        if ifadə in self._ağaclar:
            return self._ağaclar[ifadə]

        from .lekser import Lekser
        from .menbe import Mənbə
        from .parser import Parser, ParserXətası
        from .token import Növ
        from .xeta import XətaToplayıcı

        x = XətaToplayıcı()
        fayl = fayl or self.ş.ad
        s = Mənbə.mətndən(ifadə, f"{fayl}:{sətir}", x)
        tokenlər = Lekser(s, x, ascii_xəbərdarlığı=False).leksə()
        p = Parser(tokenlər, s, x)
        try:
            ağac = p._ifadə()
            # `{{ a b }}` — artıq tokenlər səssizcə atılmamalıdır
            while p._bax().növ is Növ.SETIR_SONU:
                p._al()
            if p._bax().növ is not Növ.FAYL_SONU:
                p._xəta("ALQ-P001", "Gözlənilməyən token",
                        f"`{p._göstər(p._bax())}` burada gözlənilmirdi")
        except ParserXətası:
            ağac = None
        if ağac is None or not x.uğurludur():
            ilk = x.xətalar[0].mesaj if x.xətalar else "sintaksis xətası"
            qeyd = x.xətalar[0].qeyd if x.xətalar else ""
            raise ŞablonXətası(
                f"`{{{{ {ifadə} }}}}` ayrılmadı: {ilk}"
                + (f" — {qeyd}" if qeyd else ""), fayl, sətir)
        self._ağaclar[ifadə] = ağac
        return ağac


# ═══════════════════════════════════════════════════════════════════════
#  Keş
# ═══════════════════════════════════════════════════════════════════════

_ŞABLON_KEŞİ: dict[str, tuple[float, Şablon]] = {}


def şablonu_yüklə(yol: str | Path, qovluq: Path | None = None,
                  keşlə: bool = True) -> Şablon:
    """Faylı yükləyir; dəyişmə vaxtına görə keşləyir."""
    p = Path(yol)
    if not p.exists() and qovluq is not None:
        p = qovluq / yol
    if not p.exists():
        raise ŞablonXətası(f'"{yol}" şablonu tapılmadı')

    açar = str(p.resolve())
    vaxt = p.stat().st_mtime
    if keşlə and açar in _ŞABLON_KEŞİ:
        köhnə_vaxt, ş = _ŞABLON_KEŞİ[açar]
        if köhnə_vaxt == vaxt:
            return ş

    ş = Şablon(p.read_text(encoding="utf-8"), p.name,
               qovluq or p.parent)
    if keşlə:
        _ŞABLON_KEŞİ[açar] = (vaxt, ş)
    return ş


def keşi_təmizlə() -> None:
    _ŞABLON_KEŞİ.clear()
