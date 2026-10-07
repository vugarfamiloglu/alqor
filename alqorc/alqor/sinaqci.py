"""
Alqor — `test` modulu və sınaq işlədicisi (`alqor sına`).

Spesifikasiya § 10.16, § 13.5.

    gətir test

    @sınaq("toplama düzgündür")
    funksiya toplama()
        test.bərabər(topla(2, 2), 4)
    son

    @sınaqVerilənlər([[1, 1], [2, 4], [3, 9]])
    funksiya kvadratlar(x: tam, gözlənilən: tam)
        test.bərabər(x * x, gözlənilən)
    son

    @sınaqQrupu("Rəf")
    modul rəfSınaqları
        @əvvəl
        funksiya hazırla() … son        // hər sınaqdan əvvəl
        @sınaq
        funksiya əlavə() … son
    son

Sənəddəki nümunələr də sınanır (`alqor sına --sənəd`): `///` şərhindəki
```` ```alqor ```` blokları ayrıca proqram kimi icra olunur.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import aac as A
from .deyerler import (AlqorXəta, DayanmaSiqnalı, Modul, Nümunə, Sinif,
                       mətnə, xəta_uyğundur)

# ═══════════════════════════════════════════════════════════════════════
#  `test` modulu — təsdiqlər
# ═══════════════════════════════════════════════════════════════════════


def _uğursuz(mesaj: str) -> AlqorXəta:
    return AlqorXəta("İddiaXətası", mesaj, kod="ALQ-R007")


def _xəta_adı(tip: Any) -> str:
    """`ArqumentXətası` (daxili), istifadəçi sinfi və ya mətn."""
    if isinstance(tip, str):
        return tip
    if isinstance(tip, Sinif):
        return tip.ad
    ad = getattr(tip, "ad", None)
    if isinstance(ad, str):
        return ad
    raise AlqorXəta("ArqumentXətası",
                    "xəta tipi gözlənilirdi (məs. `ArqumentXətası`)",
                    kod="ALQ-R013")


def test_modulu(icraçı, Modul_, D) -> Modul:
    def m(s: Any) -> str:
        return mətnə(s, icraçı)

    def bərabər(a, b, mesaj=""):
        if not icraçı._bərabərdir(a, b):
            raise _uğursuz(mesaj or f"gözlənilən: {m(b)}\n"
                                    f"      alınan:     {m(a)}")

    def bərabərDeyil(a, b, mesaj=""):
        if icraçı._bərabərdir(a, b):
            raise _uğursuz(mesaj or f"{m(a)} gözlənilməyən dəyərdir")

    def doğru(ş, mesaj=""):
        if ş is not True:
            raise _uğursuz(mesaj or f"doğru gözlənilirdi, alınan: {m(ş)}")

    def yanlış(ş, mesaj=""):
        if ş is not False:
            raise _uğursuz(mesaj or f"yanlış gözlənilirdi, alınan: {m(ş)}")

    def boş(d, mesaj=""):
        if d is not None:
            raise _uğursuz(mesaj or f"boş gözlənilirdi, alınan: {m(d)}")

    def boşDeyil(d, mesaj=""):
        if d is None:
            raise _uğursuz(mesaj or "dəyər boşdur")

    def ehtiva(kolleksiya, element, mesaj=""):
        try:
            var = element in kolleksiya
        except TypeError:
            var = False
        if not var:
            raise _uğursuz(mesaj or f"{m(kolleksiya)} içində {m(element)} "
                                    "yoxdur")

    def atır(f, tip=None, mesaj=""):
        try:
            icraçı._çağır(f, [], {}, None)
        except AlqorXəta as x:
            if tip is None or xəta_uyğundur(x.tip, _xəta_adı(tip)):
                return icraçı._xəta_obyekti(x)
            raise _uğursuz(mesaj or f"{_xəta_adı(tip)} gözlənilirdi, "
                                    f"{x.tip} atıldı: {x.mesaj}")
        raise _uğursuz(mesaj or (f"{_xəta_adı(tip)} gözlənilirdi"
                                 if tip is not None
                                 else "xəta gözlənilirdi") + ", atılmadı")

    def atmır(f, mesaj=""):
        try:
            return icraçı._çağır(f, [], {}, None)
        except AlqorXəta as x:
            raise _uğursuz(mesaj or f"xəta gözlənilmirdi: "
                                    f"{x.tip}: {x.mesaj}")

    def təxminən(a, b, dəqiqlik=1e-9, mesaj=""):
        if abs(a - b) > dəqiqlik:
            raise _uğursuz(mesaj or f"{m(a)} ≉ {m(b)} "
                                    f"(dəqiqlik {m(dəqiqlik)})")

    def uyğun(mətn, naxış, mesaj=""):
        if re.search(m(naxış), m(mətn)) is None:
            raise _uğursuz(mesaj or f"{m(mətn)!r} `{m(naxış)}` naxışına "
                                    "uyğun deyil")

    def uğursuz(mesaj="sınaq uğursuz oldu"):
        raise _uğursuz(m(mesaj))

    return Modul_("test", {
        "bərabər": D("bərabər", bərabər, 2, 3),
        "bərabərDeyil": D("bərabərDeyil", bərabərDeyil, 2, 3),
        "doğru": D("doğru", doğru, 1, 2),
        "yanlış": D("yanlış", yanlış, 1, 2),
        "boş": D("boş", boş, 1, 2),
        "boşDeyil": D("boşDeyil", boşDeyil, 1, 2),
        "ehtiva": D("ehtiva", ehtiva, 2, 3),
        "atır": D("atır", atır, 1, 3),
        "atmır": D("atmır", atmır, 1, 2),
        "təxminən": D("təxminən", təxminən, 2, 4),
        "uyğun": D("uyğun", uyğun, 2, 3),
        "uğursuz": D("uğursuz", uğursuz, 0, 1),
    })


# ═══════════════════════════════════════════════════════════════════════
#  Sınaq işlədicisi
# ═══════════════════════════════════════════════════════════════════════

UĞURLU, UĞURSUZ, XƏTA, ATLANMIŞ = "uğurlu", "uğursuz", "xəta", "atlanmış"


@dataclass
class Nəticə:
    ad: str
    vəziyyət: str
    müddət: float = 0.0               # saniyə
    mesaj: str = ""
    yer: str = ""
    çıxış: list[str] = field(default_factory=list)


@dataclass
class FaylNəticəsi:
    yol: Path
    nəticələr: list[Nəticə] = field(default_factory=list)
    xəta: str = ""                    # fayl ayrılmadı / yüklənmədi


@dataclass
class _Sınaq:
    ad: str
    funksiya: Any
    arqumentlər: list = field(default_factory=list)
    əvvəl: list = field(default_factory=list)
    sonra: list = field(default_factory=list)
    atla: str | None = None


def _annotasiya(elan: Any, ad: str) -> A.Annotasiya | None:
    for a in getattr(elan, "annotasiyalar", []) or []:
        if a.ad == ad:
            return a
    return None


def _arqument(icraçı, a: A.Annotasiya, standart: Any = None) -> Any:
    if not a.arqumentlər:
        return standart
    return icraçı._ifadə(a.arqumentlər[0].dəyər, icraçı.qlobal)


def _sınaqları_topla(icraçı, ağac: A.Proqram) -> list[_Sınaq]:
    sınaqlar: list[_Sınaq] = []

    def funksiyalar(gövdə: list, mühit_al: Callable[[str], Any],
                    prefiks: str, əvvəl: list, sonra: list) -> None:
        for c in gövdə:
            if not isinstance(c, A.FunksiyaElanı):
                continue
            s = _annotasiya(c, "sınaq")
            v = _annotasiya(c, "sınaqVerilənlər")
            if s is None and v is None:
                continue
            ad = c.ad
            if s is not None and s.arqumentlər:
                ad = mətnə(_arqument(icraçı, s), icraçı)
            atla = _annotasiya(c, "atla")
            səbəb = None
            if atla is not None:
                səbəb = mətnə(_arqument(icraçı, atla, "atlanıb"), icraçı)
            f = mühit_al(c.ad)
            if v is not None:
                verilənlər = _arqument(icraçı, v, [])
                for i, sıra in enumerate(verilənlər or []):
                    arq = list(sıra) if isinstance(sıra, (list, tuple)) \
                        else [sıra]
                    göstəriş = ", ".join(mətnə(x, icraçı) for x in arq)
                    sınaqlar.append(_Sınaq(f"{prefiks}{ad} [{göstəriş}]",
                                           f, arq, əvvəl, sonra, səbəb))
            else:
                sınaqlar.append(_Sınaq(prefiks + ad, f, [], əvvəl, sonra,
                                       səbəb))

    funksiyalar(ağac.gövdə, icraçı.qlobal.al, "", [], [])

    for c in ağac.gövdə:
        if not isinstance(c, A.ModulElanı):
            continue
        q = _annotasiya(c, "sınaqQrupu")
        modul = icraçı.qlobal.al(c.ad) if icraçı.qlobal.var(c.ad) else None
        if not isinstance(modul, Modul):
            continue
        qrup = (mətnə(_arqument(icraçı, q, c.ad), icraçı)
                if q is not None else c.ad)
        əvvəl, sonra = [], []
        for e in c.gövdə:
            if isinstance(e, A.FunksiyaElanı):
                if _annotasiya(e, "əvvəl"):
                    əvvəl.append(modul.üzvlər[e.ad])
                if _annotasiya(e, "sonra"):
                    sonra.append(modul.üzvlər[e.ad])
        funksiyalar(c.gövdə, lambda a, mod=modul: mod.üzvlər[a],
                    f"{qrup} › ", əvvəl, sonra)
    return sınaqlar


def _ayır(mətn: str, ad: str, yol: Path | None = None):
    from .lekser import Lekser
    from .menbe import Mənbə
    from .parser import Parser
    from .xeta import XətaToplayıcı

    x = XətaToplayıcı()
    m = Mənbə.mətndən(mətn, ad, x)
    m.yol = yol
    ağac = Parser(Lekser(m, x, ascii_xəbərdarlığı=False).leksə(), m,
                  x).ayır()
    return ağac, x


def _bir_sınaq(icraçı, s: _Sınaq) -> Nəticə:
    if s.atla is not None:
        return Nəticə(s.ad, ATLANMIŞ, mesaj=s.atla)
    çıxış: list[str] = []
    köhnə = icraçı.çıxış
    icraçı.çıxış = çıxış.append
    baş = time.perf_counter()
    try:
        for f in s.əvvəl:
            icraçı._çağır(f, [], {}, None)
        try:
            icraçı._çağır(s.funksiya, list(s.arqumentlər), {}, None)
        finally:
            for f in s.sonra:
                icraçı._çağır(f, [], {}, None)
        return Nəticə(s.ad, UĞURLU, time.perf_counter() - baş,
                      çıxış=çıxış)
    except AlqorXəta as x:
        vəziyyət = UĞURSUZ if x.tip == "İddiaXətası" else XƏTA
        mesaj = x.mesaj if vəziyyət == UĞURSUZ else f"{x.tip}: {x.mesaj}"
        return Nəticə(s.ad, vəziyyət, time.perf_counter() - baş, mesaj,
                      str(x.yer) if x.yer else "", çıxış)
    except DayanmaSiqnalı as d:
        return Nəticə(s.ad, XƏTA, time.perf_counter() - baş,
                      f"sınaq `dayan({d.kod})` çağırdı", çıxış=çıxış)
    except RecursionError:
        return Nəticə(s.ad, XƏTA, time.perf_counter() - baş,
                      "StekDaşmaXətası: rekursiya çox dərindir", çıxış=çıxış)
    finally:
        icraçı.çıxış = köhnə


def faylı_sına(yol: Path, filtr: str = "") -> FaylNəticəsi:
    from .icraci import İcraçı

    nəticə = FaylNəticəsi(yol)
    try:
        mətn = yol.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as x:
        nəticə.xəta = f"oxunmadı: {x}"
        return nəticə
    ağac, x = _ayır(mətn, yol.name, yol.resolve())
    if not x.uğurludur():
        ilk = x.xətalar[0]
        nəticə.xəta = f"{ilk.kod}: {ilk.mesaj} ({ilk.yer})"
        return nəticə

    çıxış: list[str] = []
    icraçı = İcraçı(çıxış=çıxış.append, giriş=lambda: "")
    icraçı.əsas_qovluq = yol.resolve().parent
    try:
        icraçı.işlət(ağac, [])
    except AlqorXəta as e:
        nəticə.xəta = f"fayl yüklənmədi — {e.tip}: {e.mesaj} ({e.yer})"
        return nəticə

    try:
        sınaqlar = _sınaqları_topla(icraçı, ağac)
    except AlqorXəta as e:
        nəticə.xəta = f"annotasiya qiymətləndirilmədi — {e.tip}: {e.mesaj}"
        return nəticə
    for s in sınaqlar:
        if filtr and filtr.casefold() not in s.ad.casefold():
            continue
        nəticə.nəticələr.append(_bir_sınaq(icraçı, s))
    return nəticə


# ── Sənəddəki nümunələr ───────────────────────────────────────────────

_SƏNƏD_BLOKU = re.compile(r"```alqor\n(.*?)```", re.S)


def sənəd_nümunələri(yol: Path) -> list[tuple[str, str]]:
    """`///` şərhlərindəki ```alqor blokları → [(ad, kod)]."""
    ağac, x = _ayır(yol.read_text(encoding="utf-8"), yol.name,
                    yol.resolve())
    if not x.uğurludur():
        return []
    nəticə: list[tuple[str, str]] = []

    def gəz(gövdə: list, prefiks: str = "") -> None:
        for c in gövdə:
            ad = getattr(c, "ad", None)
            sənəd = getattr(c, "sənəd", None)
            if isinstance(ad, str) and sənəd:
                for i, kod in enumerate(_SƏNƏD_BLOKU.findall(sənəd), 1):
                    nəticə.append((f"{prefiks}{ad} — nümunə {i}", kod))
            if isinstance(c, (A.SinifElanı, A.ModulElanı)):
                gəz(getattr(c, "üzvlər", None) or getattr(c, "gövdə", []),
                    f"{prefiks}{ad}.")

    gəz(ağac.gövdə)
    return nəticə


def sənədi_sına(yol: Path) -> FaylNəticəsi:
    """Hər nümunə faylın ixrac etdiyi adlarla birlikdə icra olunur."""
    from .icraci import İcraçı

    from .kitabxana import _fayldan_modul

    nəticə = FaylNəticəsi(yol)
    for ad, kod in sənəd_nümunələri(yol):
        ağac, x = _ayır(kod, f"{yol.name} [{ad}]", yol.resolve())
        baş = time.perf_counter()
        if not x.uğurludur():
            ilk = x.xətalar[0]
            nəticə.nəticələr.append(Nəticə(
                ad, XƏTA, 0.0, f"nümunə ayrılmadı: {ilk.mesaj}"))
            continue
        çıxış: list[str] = []
        icraçı = İcraçı(çıxış=çıxış.append, giriş=lambda: "")
        icraçı.əsas_qovluq = yol.resolve().parent
        try:
            # Faylın adları nümunənin mühitində hazırdır
            modul = _fayldan_modul(icraçı, str(yol.resolve()))
            for a, d in modul.üzvlər.items():
                icraçı.qlobal.elan(a, d)
            icraçı.işlət(ağac, [])
            nəticə.nəticələr.append(Nəticə(
                ad, UĞURLU, time.perf_counter() - baş, çıxış=çıxış))
        except AlqorXəta as e:
            v = UĞURSUZ if e.tip == "İddiaXətası" else XƏTA
            nəticə.nəticələr.append(Nəticə(
                ad, v, time.perf_counter() - baş, f"{e.tip}: {e.mesaj}",
                çıxış=çıxış))
    return nəticə


# ── Fayllar ───────────────────────────────────────────────────────────

def sınaq_faylları(yollar: list[Path]) -> list[Path]:
    """
    Qovluqda: `*_sınaq.alq`, `*_sinaq.alq`, `*_test.alq` və
    `sınaq/` (`sinaq/`, `test/`) qovluğundakı bütün `.alq` faylları.
    """
    nəticə: list[Path] = []
    for p in yollar:
        if p.is_file():
            nəticə.append(p)
            continue
        if not p.is_dir():
            continue
        for f in sorted([*p.rglob("*.alq"), *p.rglob("*.alqor")]):
            nisbi = f.relative_to(p).parts
            if any(h.startswith(".") or h in ("qurma", "paketlər")
                   for h in nisbi):
                continue
            sınaq_qovluğundadır = p.name in ("sınaq", "sinaq", "test") \
                or any(h in ("sınaq", "sinaq", "test") for h in nisbi[:-1])
            if sınaq_qovluğundadır or f.stem.endswith(
                    ("_sınaq", "_sinaq", "_test")):
                nəticə.append(f)
    return nəticə


# ── Hesabat ───────────────────────────────────────────────────────────

İŞARƏLƏR = {UĞURLU: "✓", UĞURSUZ: "✗", XƏTA: "✖", ATLANMIŞ: "○"}


def hesabat(fayllar: list[FaylNəticəsi], kök: Path | None = None,
            ətraflı: bool = False) -> tuple[list[str], dict[str, int]]:
    say = {UĞURLU: 0, UĞURSUZ: 0, XƏTA: 0, ATLANMIŞ: 0}
    s: list[str] = []
    for f in fayllar:
        ad = str(f.yol)
        if kök is not None:
            try:
                ad = str(f.yol.resolve().relative_to(kök))
            except ValueError:
                pass
        s.append(f"  {ad}")
        if f.xəta:
            s.append(f"    ✖ {f.xəta}")
            say[XƏTA] += 1
            s.append("")
            continue
        if not f.nəticələr:
            s.append("    (sınaq yoxdur)")
        for n in f.nəticələr:
            say[n.vəziyyət] += 1
            müddət = f"{n.müddət * 1000:.1f}ms"
            sol = f"    {İŞARƏLƏR[n.vəziyyət]} {n.ad}"
            s.append(f"{sol.ljust(56)} {müddət:>9}")
            if n.vəziyyət in (UĞURSUZ, XƏTA):
                for sətir in n.mesaj.splitlines():
                    s.append(f"        {sətir}")
                if n.yer:
                    s.append(f"        {n.yer}")
                if n.çıxış and ətraflı:
                    s.append("        çıxış:")
                    s.extend(f"          {c}" for c in n.çıxış)
            elif n.vəziyyət == ATLANMIŞ and n.mesaj:
                s.append(f"        atlanıb: {n.mesaj}")
        s.append("")
    return s, say
