"""
Alqor — `konsol` modulu: terminal tətbiqləri.

Spesifikasiya § 12.1. Xarici asılılıq yoxdur.

GİRİŞ VƏ ÇIXIŞ İCRAÇIDAN KEÇİR
──────────────────────────────
Sual-cavab funksiyaları (`soruş`, `seç`, `təsdiqlə`…) `oxu()` kimi
icraçının giriş axınını işlədir — sınaqlarda cavablar əvvəlcədən
verilə bilir. Sətir çıxışı (`cədvəl`, `seç`-in siyahısı) `yaz()` kimi
icraçının çıxışına gedir.

TERMİNAL VƏ BORU
────────────────
`irəliləyiş` və `fırlanan` terminalda eyni sətri yeniləyir (`\\r`).
Çıxış fayla və ya boruya yönəldilibsə animasiya olmur — yalnız yekun
sətir yazılır, jurnal faylları zibillənmir.

RƏNG
────
`NO_COLOR` mühit dəyişəni (https://no-color.org) təyin olunubsa rəng
kodları buraxılmır. Windows 10+ konsolunda ANSI kodları avtomatik
aktivləşdirilir.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from typing import Any

from .deyerler import AlqorXəta, DayanmaSiqnalı, mətnə
from . import elifba as E

# ═══════════════════════════════════════════════════════════════════════
#  Rəng
# ═══════════════════════════════════════════════════════════════════════

RƏNGLƏR = {
    "qara": 30, "qırmızı": 31, "yaşıl": 32, "sarı": 33, "mavi": 34,
    "bənövşəyi": 35, "firuzəyi": 36, "ağ": 37, "boz": 90,
}

_windows_hazır = False


def _rəng_aktivdir() -> bool:
    global _windows_hazır
    if os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt" and not _windows_hazır:
        # Windows 10+: boş `os.system` çağırışı VT emulyasiyasını açır
        os.system("")
        _windows_hazır = True
    return True


def boya(mətn: Any, *kodlar: int, icraçı: Any = None) -> str:
    m = mətnə(mətn, icraçı)
    if not kodlar or not _rəng_aktivdir():
        return m
    return f"\033[{';'.join(str(k) for k in kodlar)}m{m}\033[0m"


def _rəng_kodu(ad: Any, sahə: str, icraçı: Any) -> int:
    a = E.kiçiyə(mətnə(ad, icraçı))
    if a not in RƏNGLƏR:
        raise AlqorXəta(
            "ArqumentXətası",
            f"`{a}` {sahə} rəngi yoxdur. İcazəli: {', '.join(RƏNGLƏR)}",
            kod="ALQ-R013")
    return RƏNGLƏR[a]


def rəng(icraçı, mətn: Any, ön: Any = None, arxa: Any = None,
         qalın: Any = False) -> str:
    kodlar: list[int] = []
    if qalın:
        kodlar.append(1)
    if ön is not None:
        kodlar.append(_rəng_kodu(ön, "ön", icraçı))
    if arxa is not None:
        kodlar.append(_rəng_kodu(arxa, "arxa", icraçı) + 10)
    return boya(mətn, *kodlar, icraçı=icraçı)


# ═══════════════════════════════════════════════════════════════════════
#  Terminal
# ═══════════════════════════════════════════════════════════════════════

def _terminaldır() -> bool:
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def _yaz_xam(m: str) -> None:
    sys.stdout.write(m)
    sys.stdout.flush()


def təmizlə(icraçı) -> None:
    if _terminaldır():
        _yaz_xam("\033[2J\033[H")


def kursor(icraçı, sətir: Any, sütun: Any = 1) -> None:
    if _terminaldır():
        _yaz_xam(f"\033[{int(sətir)};{int(sütun)}H")


def ölçü(icraçı) -> tuple[int, int]:
    """`(en, hündürlük)` — simvolla."""
    ö = shutil.get_terminal_size((80, 24))
    return (ö.columns, ö.lines)


# ═══════════════════════════════════════════════════════════════════════
#  Sual-cavab
# ═══════════════════════════════════════════════════════════════════════

def _oxu(icraçı, sual: str) -> str:
    if sual:
        _yaz_xam(sual)
    try:
        return icraçı.giriş()
    except EOFError:
        raise AlqorXəta("GirişÇıxışXətası",
                        "girişin sonu — oxunacaq məlumat qalmadı",
                        kod="ALQ-R009") from None


def soruş(icraçı, sual: Any = "", standart: Any = None) -> str:
    """Boş cavabda `standart` qaytarılır (verilibsə)."""
    s = mətnə(sual, icraçı)
    if standart is not None:
        s = f"{s}[{mətnə(standart, icraçı)}] " if s else \
            f"[{mətnə(standart, icraçı)}] "
    cavab = _oxu(icraçı, s)
    if not cavab.strip() and standart is not None:
        return mətnə(standart, icraçı)
    return cavab


def parolSoruş(icraçı, sual: Any = "Parol: ") -> str:
    """Terminalda yazılan simvollar görünmür."""
    s = mətnə(sual, icraçı)
    if sys.stdin.isatty() and icraçı.giriş is input:
        import getpass
        try:
            return getpass.getpass(s)
        except EOFError:
            pass
    return _oxu(icraçı, s)


BƏLİ = ("hə", "he", "bəli", "beli", "h", "b", "doğru", "dogru")
XEYR = ("yox", "xeyr", "y", "x", "yanlış", "yanlis")


def təsdiqlə(icraçı, sual: Any, standart: Any = None) -> bool:
    ipucu = "(hə/yox)" if standart is None else \
        ("(HƏ/yox)" if standart else "(hə/YOX)")
    while True:
        c = E.kiçiyə(_oxu(icraçı, f"{mətnə(sual, icraçı)} {ipucu} ")
                     .strip())
        if not c and standart is not None:
            return bool(standart)
        if c in BƏLİ:
            return True
        if c in XEYR:
            return False
        icraçı.çıxış("`hə` və ya `yox` yazın.")


def _seçimləri_göstər(icraçı, sual: Any, seçimlər: list) -> None:
    if sual is not None and mətnə(sual, icraçı):
        icraçı.çıxış(mətnə(sual, icraçı))
    for i, s in enumerate(seçimlər, start=1):
        icraçı.çıxış(f"  {i}) {mətnə(s, icraçı)}")


def _siyahı_yoxla(seçimlər: Any) -> list:
    if not isinstance(seçimlər, (list, tuple)) or not seçimlər:
        raise AlqorXəta("ArqumentXətası",
                        "seçimlər boş olmayan siyahı olmalıdır",
                        kod="ALQ-R013")
    return list(seçimlər)


def seç(icraçı, sual: Any, seçimlər: Any) -> Any:
    """Nömrə ilə seçim. Seçilmiş ELEMENTİ qaytarır."""
    s = _siyahı_yoxla(seçimlər)
    _seçimləri_göstər(icraçı, sual, s)
    while True:
        c = _oxu(icraçı, f"Seçin (1–{len(s)}): ").strip()
        if c.isdigit() and 1 <= int(c) <= len(s):
            return s[int(c) - 1]
        # Elementin adı ilə də seçmək olar
        for e in s:
            if E.kiçiyə(mətnə(e, icraçı)) == E.kiçiyə(c) and c:
                return e
        icraçı.çıxış(f"1 ilə {len(s)} arasında nömrə yazın.")


def çoxSeç(icraçı, sual: Any, seçimlər: Any) -> list:
    """`1,3` və ya `1 3` — seçilmiş elementlərin siyahısı (boş ola bilər)."""
    s = _siyahı_yoxla(seçimlər)
    _seçimləri_göstər(icraçı, sual, s)
    while True:
        c = _oxu(icraçı, "Nömrələr (məs. 1,3; boş — heç biri): ").strip()
        if not c:
            return []
        hissələr = [h for h in c.replace(",", " ").split() if h]
        if all(h.isdigit() and 1 <= int(h) <= len(s) for h in hissələr):
            görülən: list[int] = []
            for h in hissələr:
                if int(h) not in görülən:
                    görülən.append(int(h))
            return [s[n - 1] for n in görülən]
        icraçı.çıxış(f"1 ilə {len(s)} arasında nömrələr yazın.")


# ═══════════════════════════════════════════════════════════════════════
#  Cədvəl
# ═══════════════════════════════════════════════════════════════════════

def cədvəl(icraçı, başlıqlar: Any, sətirlər: Any) -> None:
    hamısı = [[mətnə(h, icraçı) for h in başlıqlar]] + [
        [mətnə(c, icraçı) for c in s] for s in sətirlər]
    sütun_sayı = max(len(s) for s in hamısı)
    for s in hamısı:
        s.extend([""] * (sütun_sayı - len(s)))
    enlər = [max(len(s[i]) for s in hamısı) for i in range(sütun_sayı)]
    ayırıcı = "─┼─".join("─" * e for e in enlər)
    for j, s in enumerate(hamısı):
        icraçı.çıxış(" │ ".join(h.ljust(e) for h, e in zip(s, enlər))
                     .rstrip())
        if j == 0:
            icraçı.çıxış(ayırıcı)


# ═══════════════════════════════════════════════════════════════════════
#  İrəliləyiş və fırlanan
# ═══════════════════════════════════════════════════════════════════════

class İrəliləyiş:
    """`konsol.irəliləyiş(100, "Yüklənir")` — tərəqqi zolağı."""

    ALQOR_TİP_ADI = "irəliləyiş"
    EN = 28

    def __init__(self, icraçı, cəmi: Any, mətn: Any = ""):
        self.icraçı = icraçı
        self.cəmi = max(1, int(cəmi))
        self.mətn = mətnə(mətn, icraçı)
        self.cari = 0
        self.bitib = False
        self._son_çəkmə = 0.0
        self._terminal = _terminaldır()

    def sətir(self) -> str:
        nisbət = min(1.0, self.cari / self.cəmi)
        dolu = round(nisbət * self.EN)
        zolaq = "█" * dolu + "░" * (self.EN - dolu)
        baş = f"{self.mətn} " if self.mətn else ""
        return (f"{baş}{zolaq} {nisbət * 100:3.0f}% "
                f"({self.cari}/{self.cəmi})")

    def _çək(self, məcburi: bool = False) -> None:
        if not self._terminal:
            return
        indi = time.monotonic()
        if not məcburi and indi - self._son_çəkmə < 0.05:
            return
        self._son_çəkmə = indi
        _yaz_xam("\r" + self.sətir())

    def yenilə(self, n: Any) -> "İrəliləyiş":
        self.cari = max(0, min(self.cəmi, int(n)))
        self._çək(self.cari >= self.cəmi)
        return self

    def artır(self, addım: Any = 1) -> "İrəliləyiş":
        return self.yenilə(self.cari + int(addım))

    def bitir(self, mesaj: Any = None) -> None:
        if self.bitib:
            return
        self.bitib = True
        self.cari = self.cəmi
        if self._terminal:
            _yaz_xam("\r\033[K")
        self.icraçı.çıxış(mətnə(mesaj, self.icraçı) if mesaj is not None
                          else self.sətir())

    ALQOR_METODLARI = {
        "yenilə": lambda i, o, n: o.yenilə(n),
        "artır": lambda i, o, a=1: o.artır(a),
        "bitir": lambda i, o, m=None: o.bitir(m),
        "cari": lambda i, o: o.cari,
        "cəmi": lambda i, o: o.cəmi,
        "mətnƏt": lambda i, o: o.sətir(),
    }


class Fırlanan:
    """`konsol.fırlanan("İşlənir…")` — müddəti bilinməyən iş."""

    ALQOR_TİP_ADI = "fırlanan"
    KADRLAR = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, icraçı, mətn: Any = ""):
        self.icraçı = icraçı
        self.mətn = mətnə(mətn, icraçı)
        self._dayan = threading.Event()
        self._sap: threading.Thread | None = None
        self.işləyir = True
        if _terminaldır():
            self._sap = threading.Thread(target=self._dövr, daemon=True,
                                         name="alqor-fırlanan")
            self._sap.start()

    def _dövr(self) -> None:
        i = 0
        while not self._dayan.wait(0.08):
            _yaz_xam(f"\r{self.KADRLAR[i % len(self.KADRLAR)]} "
                     f"{self.mətn}")
            i += 1

    def mətnDəyiş(self, mətn: Any) -> "Fırlanan":
        self.mətn = mətnə(mətn, self.icraçı)
        return self

    def dayandır(self, mesaj: Any = None) -> None:
        if not self.işləyir:
            return
        self.işləyir = False
        self._dayan.set()
        if self._sap is not None:
            self._sap.join(timeout=1)
            _yaz_xam("\r\033[K")
        self.icraçı.çıxış(mətnə(mesaj, self.icraçı) if mesaj is not None
                          else self.mətn)

    ALQOR_METODLARI = {
        "dayandır": lambda i, o, m=None: o.dayandır(m),
        "mətnDəyiş": lambda i, o, m: o.mətnDəyiş(m),
        "işləyir": lambda i, o: o.işləyir,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Əmr sətri arqumentləri
# ═══════════════════════════════════════════════════════════════════════

class _Parametr:
    __slots__ = ("ad", "izah", "çoxlu", "ixtiyari")

    def __init__(self, ad, izah, çoxlu, ixtiyari):
        self.ad, self.izah = ad, izah
        self.çoxlu, self.ixtiyari = çoxlu, ixtiyari


class _Seçim:
    __slots__ = ("uzun", "qısa", "izah", "standart", "bayraqdır")

    def __init__(self, uzun, qısa, izah, standart, bayraqdır):
        self.uzun, self.qısa, self.izah = uzun, qısa, izah
        self.standart, self.bayraqdır = standart, bayraqdır

    def ad(self) -> str:
        return self.uzun.lstrip("-")


class ArqumentXətası(Exception):
    pass


class Arqumentlər:
    """
    `konsol.arqumentlər()` — zəncirlənən təhlilçi.

        dəyişən a = konsol.arqumentlər()
            .proqram("hesabla").versiya("1.0")
            .parametr("ədədlər", "Ədədlər", çoxlu: doğru)
            .bayraq("--ətraflı", "-ə", "Ətraflı çıxış")
            .təhlil()
    """

    ALQOR_TİP_ADI = "arqumentlər"

    def __init__(self, icraçı):
        self.icraçı = icraçı
        self._proqram = "proqram"
        self._versiya = ""
        self._təsvir = ""
        self._parametrlər: list[_Parametr] = []
        self._seçimlər: list[_Seçim] = [
            _Seçim("--kömək", "-k", "Bu köməyi göstər", None, True)]

    # ── Quraşdırma ────────────────────────────────────────────────────

    def proqram(self, ad: Any) -> "Arqumentlər":
        self._proqram = mətnə(ad, self.icraçı)
        return self

    def versiya(self, v: Any) -> "Arqumentlər":
        self._versiya = mətnə(v, self.icraçı)
        if not any(s.uzun == "--versiya" for s in self._seçimlər):
            self._seçimlər.append(
                _Seçim("--versiya", "-v", "Versiyanı göstər", None, True))
        return self

    def təsvir(self, t: Any) -> "Arqumentlər":
        self._təsvir = mətnə(t, self.icraçı)
        return self

    def parametr(self, ad: Any, izah: Any = "", çoxlu: Any = False,
                 ixtiyari: Any = False) -> "Arqumentlər":
        if self._parametrlər and self._parametrlər[-1].çoxlu:
            raise AlqorXəta("ArqumentXətası",
                            "`çoxlu` parametrdən sonra parametr ola bilməz",
                            kod="ALQ-R013")
        self._parametrlər.append(_Parametr(
            mətnə(ad, self.icraçı), mətnə(izah, self.icraçı),
            bool(çoxlu), bool(ixtiyari)))
        return self

    def _seçim_əlavə(self, uzun, qısa, izah, standart, bayraqdır):
        u = mətnə(uzun, self.icraçı)
        if not u.startswith("--"):
            raise AlqorXəta("ArqumentXətası",
                            f"uzun ad `--` ilə başlamalıdır: `{u}`",
                            kod="ALQ-R013")
        q = mətnə(qısa, self.icraçı) if qısa else ""
        self._seçimlər.append(_Seçim(
            u, q, mətnə(izah, self.icraçı),
            None if standart is None else mətnə(standart, self.icraçı),
            bayraqdır))
        return self

    def bayraq(self, uzun: Any, qısa: Any = None,
               izah: Any = "") -> "Arqumentlər":
        return self._seçim_əlavə(uzun, qısa, izah, None, True)

    def seçim(self, uzun: Any, qısa: Any = None, izah: Any = "",
              standart: Any = None) -> "Arqumentlər":
        return self._seçim_əlavə(uzun, qısa, izah, standart, False)

    # ── Kömək ─────────────────────────────────────────────────────────

    def istifadə(self) -> str:
        hissələr = [self._proqram]
        if len(self._seçimlər) > 0:
            hissələr.append("[SEÇİMLƏR]")
        for p in self._parametrlər:
            ad = f"<{p.ad}>" + ("..." if p.çoxlu else "")
            hissələr.append(f"[{ad}]" if p.ixtiyari else ad)
        return " ".join(hissələr)

    def kömək(self) -> str:
        s: list[str] = []
        baş = self._proqram + (f" {self._versiya}" if self._versiya
                               else "")
        s.append(baş)
        if self._təsvir:
            s.append(self._təsvir)
        s += ["", "İSTİFADƏ:", f"    {self.istifadə()}"]
        if self._parametrlər:
            s += ["", "ARQUMENTLƏR:"]
            adlar = [f"<{p.ad}>" + ("..." if p.çoxlu else "")
                     for p in self._parametrlər]
            en = max(len(a) for a in adlar)
            for a, p in zip(adlar, self._parametrlər):
                s.append(f"    {a.ljust(en)}  {p.izah}".rstrip())
        s += ["", "SEÇİMLƏR:"]
        # İstifadəçinin seçimləri əvvəl, daxili `--kömək`/`--versiya` sonda
        daxili = ("--kömək", "--versiya")
        sıra = ([o for o in self._seçimlər if o.uzun not in daxili]
                + [o for o in self._seçimlər if o.uzun in daxili])
        sol = []
        for o in sıra:
            ad = (f"{o.qısa}, " if o.qısa else "    ") + o.uzun
            if not o.bayraqdır:
                ad += f" <{E.böyüyə(o.ad())}>"
            sol.append(ad)
        en = max(len(a) for a in sol)
        for a, o in zip(sol, sıra):
            izah = o.izah
            if o.standart is not None:
                izah += f" [standart: {o.standart}]"
            s.append(f"    {a.ljust(en)}  {izah}".rstrip())
        return "\n".join(s)

    # ── Təhlil ────────────────────────────────────────────────────────

    def _seçim_tap(self, ad: str) -> _Seçim | None:
        for o in self._seçimlər:
            if ad == o.uzun or (o.qısa and ad == o.qısa):
                return o
        return None

    def təhlil(self, arqumentlər: Any = None) -> "ArqNəticəsi":
        """
        `--kömək` köməyi çap edib proqramı 0 kodu ilə bitirir; səhv
        arqumentdə xəta və istifadə qaydası çap olunur, kod 3 (§ 13.16).
        """
        xam = list(arqumentlər) if arqumentlər is not None else \
            list(getattr(self.icraçı, "proqram_arqumentləri", []))
        try:
            return self._təhlil([mətnə(a, self.icraçı) for a in xam])
        except ArqumentXətası as x:
            print(f"xəta: {x}", file=sys.stderr)
            print(f"istifadə: {self.istifadə()}", file=sys.stderr)
            print(f"Ətraflı: {self._proqram} --kömək", file=sys.stderr)
            raise DayanmaSiqnalı(3) from None   # § 13.16: yanlış istifadə

    def _təhlil(self, xam: list[str]) -> "ArqNəticəsi":
        dəyərlər: dict[str, Any] = {}
        bayraqlar: set[str] = set()
        mövqeli: list[str] = []
        i = 0
        yalnız_mövqeli = False
        while i < len(xam):
            a = xam[i]
            i += 1
            if yalnız_mövqeli or not a.startswith("-") or a == "-":
                mövqeli.append(a)
                continue
            if a == "--":
                yalnız_mövqeli = True
                continue
            ad, bərabər, dəyər = a.partition("=")
            o = self._seçim_tap(ad)
            if o is None:
                raise ArqumentXətası(f"naməlum seçim `{ad}`")
            if o.uzun == "--kömək":
                self.icraçı.çıxış(self.kömək())
                raise DayanmaSiqnalı(0)
            if o.uzun == "--versiya":
                self.icraçı.çıxış(f"{self._proqram} {self._versiya}")
                raise DayanmaSiqnalı(0)
            if o.bayraqdır:
                if bərabər:
                    raise ArqumentXətası(f"`{o.uzun}` dəyər qəbul etmir")
                bayraqlar.add(o.ad())
                continue
            if not bərabər:
                if i >= len(xam):
                    raise ArqumentXətası(f"`{o.uzun}` üçün dəyər lazımdır")
                dəyər = xam[i]
                i += 1
            dəyərlər[o.ad()] = dəyər

        for o in self._seçimlər:
            if not o.bayraqdır and o.ad() not in dəyərlər \
                    and o.standart is not None:
                dəyərlər[o.ad()] = o.standart

        for p in self._parametrlər:
            if p.çoxlu:
                if not mövqeli and not p.ixtiyari:
                    raise ArqumentXətası(f"<{p.ad}> lazımdır")
                dəyərlər[p.ad] = list(mövqeli)
                mövqeli = []
            elif mövqeli:
                dəyərlər[p.ad] = mövqeli.pop(0)
            elif not p.ixtiyari:
                raise ArqumentXətası(f"<{p.ad}> lazımdır")
        if mövqeli:
            raise ArqumentXətası(f"artıq arqument: `{mövqeli[0]}`")
        return ArqNəticəsi(dəyərlər, bayraqlar)

    ALQOR_METODLARI = {
        "proqram": lambda i, o, a: o.proqram(a),
        "versiya": lambda i, o, v: o.versiya(v),
        "təsvir": lambda i, o, t: o.təsvir(t),
        "parametr": lambda i, o, a, izah="", çoxlu=False, ixtiyari=False:
            o.parametr(a, izah, çoxlu, ixtiyari),
        "bayraq": lambda i, o, u, q=None, izah="": o.bayraq(u, q, izah),
        "seçim": lambda i, o, u, q=None, izah="", standart=None:
            o.seçim(u, q, izah, standart),
        "təhlil": lambda i, o, a=None: o.təhlil(a),
        "kömək": lambda i, o: o.kömək(),
        "istifadə": lambda i, o: o.istifadə(),
    }


class ArqNəticəsi:
    ALQOR_TİP_ADI = "arqNəticəsi"

    def __init__(self, dəyərlər: dict[str, Any], bayraqlar: set[str]):
        self.dəyərlər = dəyərlər
        self.bayraqlar = bayraqlar

    @staticmethod
    def _ad(a: str) -> str:
        return a.lstrip("-")

    def bayraq(self, ad: str) -> bool:
        return self._ad(ad) in self.bayraqlar

    def dəyər(self, ad: str, standart: Any = None) -> Any:
        d = self.dəyərlər.get(self._ad(ad), standart)
        return d

    def siyahı(self, ad: str) -> list:
        d = self.dəyərlər.get(self._ad(ad))
        if d is None:
            return []
        return d if isinstance(d, list) else [d]

    ALQOR_METODLARI = {
        "bayraq": lambda i, o, a: o.bayraq(mətnə(a, i)),
        "dəyər": lambda i, o, a, s=None: o.dəyər(mətnə(a, i), s),
        "siyahı": lambda i, o, a: o.siyahı(mətnə(a, i)),
        "var": lambda i, o, a: (mətnə(a, i).lstrip("-") in o.dəyərlər
                                or o.bayraq(mətnə(a, i))),
        "hamısı": lambda i, o: {**o.dəyərlər,
                                **{b: True for b in o.bayraqlar}},
    }


# ═══════════════════════════════════════════════════════════════════════
#  Modul
# ═══════════════════════════════════════════════════════════════════════

def modul(icraçı, Modul, D):
    """`kitabxana.py` çağırır — `konsol` modulunu qurur."""
    def sadə(kod: int):
        return lambda s: boya(s, kod, icraçı=icraçı)

    return Modul("konsol", {
        # Rəng
        "qırmızı": D("qırmızı", sadə(31), 1, 1),
        "yaşıl": D("yaşıl", sadə(32), 1, 1),
        "sarı": D("sarı", sadə(33), 1, 1),
        "mavi": D("mavi", sadə(34), 1, 1),
        "boz": D("boz", sadə(90), 1, 1),
        "qalın": D("qalın", sadə(1), 1, 1),
        "altXətt": D("altXətt", sadə(4), 1, 1),
        "rəng": D("rəng", lambda m, ön=None, arxa=None, qalın=False:
                  rəng(icraçı, m, ön, arxa, qalın), 1, 4),
        # Terminal
        "təmizlə": D("təmizlə", lambda: təmizlə(icraçı)),
        "kursor": D("kursor", lambda s, c=1: kursor(icraçı, s, c), 1, 2),
        "ölçü": D("ölçü", lambda: ölçü(icraçı)),
        "terminaldır": D("terminaldır", _terminaldır),
        # Sual-cavab
        "soruş": D("soruş", lambda s="", standart=None:
                   soruş(icraçı, s, standart), 0, 2),
        "parolSoruş": D("parolSoruş", lambda s="Parol: ":
                        parolSoruş(icraçı, s), 0, 1),
        "təsdiqlə": D("təsdiqlə", lambda s, standart=None:
                      təsdiqlə(icraçı, s, standart), 1, 2),
        "seç": D("seç", lambda s, seçimlər: seç(icraçı, s, seçimlər), 2, 2),
        "çoxSeç": D("çoxSeç", lambda s, seçimlər:
                    çoxSeç(icraçı, s, seçimlər), 2, 2),
        # Göstəricilər
        "cədvəl": D("cədvəl", lambda b, s: cədvəl(icraçı, b, s), 2, 2),
        "irəliləyiş": D("irəliləyiş", lambda c, m="":
                        İrəliləyiş(icraçı, c, m), 1, 2),
        "fırlanan": D("fırlanan", lambda m="": Fırlanan(icraçı, m), 0, 1),
        # Arqumentlər
        "arqumentlər": D("arqumentlər", lambda: Arqumentlər(icraçı)),
    })
