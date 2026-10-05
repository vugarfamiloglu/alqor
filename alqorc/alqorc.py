#!/usr/bin/env python3
"""
Alqor — əmr sətri aləti (etalon implementasiya).

    python alqorc.py tokenlər <fayl>     tokenləri göstər
    python alqorc.py yoxla <fayl>        xətaları yoxla
    python alqorc.py hərf <mətn>         az-AZ hərf çevrilməsi
    python alqorc.py sırala <söz>...     Azərbaycan əlifba sırası
    python alqorc.py versiya
    python alqorc.py kömək
"""

from __future__ import annotations
import sys
from pathlib import Path

# ── KRİTİK: Windows konsolu standart olaraq cp1251-dir və Azərbaycan
#    hərflərini çap edə bilmir. Bu olmadan dil öz xəta mesajını göstərə bilmir.
for _axın in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _axın.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).parent))

from alqor import VERSIYA, elifba                      # noqa: E402
from alqor.lekser import Lekser, faylı_leksə, leksə    # noqa: E402
from alqor.menbe import Mənbə                          # noqa: E402
from alqor.token import KodParçası, MətnParçası, Növ    # noqa: E402
from alqor.xeta import XətaToplayıcı                   # noqa: E402

PROQRAM = "alqor"


# ═══════════════════════════════════════════════════════════════════════
#  Əmrlər
# ═══════════════════════════════════════════════════════════════════════

def əmr_tokenlər(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        çap_xəta("`tokenlər` əmri üçün fayl adı lazımdır")
        return 3
    yol = arqumentlər[0]
    ətraflı = "--ətraflı" in arqumentlər or "-e" in arqumentlər

    if yol == "-":
        tokenlər, x = leksə(sys.stdin.read(), "<stdin>")
    else:
        tokenlər, x = faylı_leksə(yol)

    if not tokenlər and not x.uğurludur():
        x.çap()
        return 2

    print(f"  {'YER':>9}  {'NÖV':<11} DƏYƏR")
    print("  " + "─" * 58)
    for t in tokenlər:
        _token_çap(t, ətraflı, girinti=2)
    print("  " + "─" * 58)
    print(f"  {len(tokenlər)} token")
    print()
    sys.stdout.flush()          # stderr ilə qarışmasın

    if x.siyahı:
        x.çap()
    return 0 if x.uğurludur() else 2


def _token_çap(t, ətraflı: bool, girinti: int) -> None:
    boş = " " * girinti
    if t.növ is Növ.SETIR_SONU:
        print(f"{boş}{'':>9}  ⏎ sətir sonu")
        return
    if t.növ is Növ.FAYL_SONU:
        print(f"{boş}{'':>9}  ⊣ fayl sonu")
        return

    yer = f"{t.yer.sətir}:{t.yer.sütun}"
    əlavə = ""
    if t.ascii_idi:
        əlavə = f"   ← ASCII: {t.xam!r}"
    if t.çoxsətirli:
        əlavə += "   (çoxsətirli)"

    print(f"{boş}{yer:>9}  {t.növ.name:<11} {t.dəyər!r}{əlavə}")

    if t.parçalar and any(isinstance(p, KodParçası) for p in t.parçalar):
        for p in t.parçalar:
            if isinstance(p, MətnParçası):
                print(f"{boş}{'':>9}    ├ mətn   {p.dəyər!r}")
            else:
                f = f"  format={p.format!r}" if p.format else ""
                print(f"{boş}{'':>9}    ├ kod{f}")
                for alt in p.tokenlər:
                    _token_çap(alt, ətraflı, girinti + 8)


def əmr_işlət(arqumentlər: list[str]) -> int:
    """Proqramı leksə → ayır → icra et."""
    from alqor.deyerler import AlqorXəta
    from alqor.icraci import İcraçı
    from alqor.lekser import Lekser
    from alqor.parser import Parser

    if not arqumentlər:
        çap_xəta("`işlət` əmri üçün fayl adı lazımdır")
        return 3

    yol = arqumentlər[0]
    proqram_arqumentləri = (arqumentlər[arqumentlər.index("--") + 1:]
                            if "--" in arqumentlər else [])

    x = XətaToplayıcı()
    if yol == "-":
        s = Mənbə.mətndən(sys.stdin.read(), "<stdin>", x)
    else:
        s = Mənbə.fayldan(yol, x)
    if s is None:
        x.çap()
        return 4

    tokenlər = Lekser(s, x).leksə()
    ağac = Parser(tokenlər, s, x).ayır()

    if not x.uğurludur():
        x.çap()
        return 2
    if x.xəbərdarlıqlar:
        x.çap()

    sys.stdout.flush()
    icraçı = İcraçı()
    try:
        return icraçı.işlət(ağac, proqram_arqumentləri)
    except AlqorXəta as xəta:
        _icra_xətası_çap(xəta, s)
        return 1
    except RecursionError:
        print("\n✖ StekDaşmaXətası: çağırış dərinliyi həddi aşıldı",
              file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⊣ dayandırıldı", file=sys.stderr)
        return 130


def _icra_xətası_çap(xəta, mənbə) -> None:
    from alqor.xeta import Diaqnostika, Səviyyə
    sys.stdout.flush()
    d = Diaqnostika(
        xəta.kod or "ALQ-R000",
        f"{xəta.tip}: {xəta.mesaj}",
        xəta.yer,
        Səviyyə.XETA,
        "burada baş verdi" if xəta.yer else "",
    )
    print(d.formatla(), file=sys.stderr)


def əmr_yoxla(arqumentlər: list[str]) -> int:
    from alqor.parser import Parser
    from alqor.lekser import Lekser
    if not arqumentlər:
        çap_xəta("`yoxla` əmri üçün fayl adı lazımdır")
        return 3

    ümumi_xəta = 0
    yollar: list[str] = []
    for a in arqumentlər:
        if a.startswith("-"):
            continue
        p = Path(a)
        if p.is_dir():
            yollar.extend(str(q) for q in sorted(p.rglob("*.alqor")))
            yollar.extend(str(q) for q in sorted(p.rglob("*.alq")))
        else:
            yollar.append(a)

    if not yollar:
        çap_xəta("yoxlanacaq fayl tapılmadı")
        return 4

    for yol in yollar:
        x = XətaToplayıcı()
        s = Mənbə.fayldan(yol, x)
        if s is not None:
            Parser(Lekser(s, x).leksə(), s, x).ayır()
        if x.siyahı:
            print(f"── {yol} " + "─" * max(0, 56 - len(yol)))
            x.çap()
            print()
        if not x.uğurludur():
            ümumi_xəta += 1

    toplam = len(yollar)
    if ümumi_xəta == 0:
        print(f"✓ {toplam} fayl yoxlanıldı, xəta yoxdur")
        return 0
    print(f"✖ {toplam} fayldan {ümumi_xəta}-də xəta var")
    return 2


def əmr_hərf(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        çap_xəta("`hərf` əmri üçün mətn lazımdır")
        return 3
    mətn = " ".join(arqumentlər)
    print(f"  giriş          : {mətn!r}")
    print(f"  böyüyə  (Alqor): {elifba.böyüyə(mətn)!r}")
    print(f"  böyüyə (Python): {mətn.upper()!r}")
    print(f"  kiçiyə  (Alqor): {elifba.kiçiyə(mətn)!r}")
    print(f"  kiçiyə (Python): {mətn.lower()!r}")
    print(f"  baş böyük      : {elifba.baş_böyük(mətn)!r}")
    print(f"  hər söz böyük  : {elifba.hər_söz_böyük(mətn)!r}")
    print(f"  latınla        : {elifba.latınla(mətn)!r}")

    fərq_b = elifba.böyüyə(mətn) != mətn.upper()
    fərq_k = elifba.kiçiyə(mətn) != mətn.lower()
    if fərq_b or fərq_k:
        print()
        print("  ⚠ Python-un standart çevrilməsi bu mətndə YANLIŞ nəticə verir.")
    return 0


def əmr_sırala(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        çap_xəta("`sırala` əmri üçün sözlər lazımdır")
        return 3
    print(f"  Alqor (az-AZ) : {elifba.sırala(arqumentlər)}")
    print(f"  Python        : {sorted(arqumentlər)}")
    print()
    print(f"  Əlifba sırası : {' '.join(elifba.KICIK)}")
    return 0


def əmr_söhbət(arqumentlər: list[str]) -> int:
    """İnteraktiv rejim (REPL)."""
    from alqor.sohbet import söhbət_başlat
    rəngli = None
    if "--rəngsiz" in arqumentlər or "--rengsiz" in arqumentlər:
        rəngli = False
    return söhbət_başlat(rəngli)


def əmr_versiya(_: list[str]) -> int:
    print(f"Alqor {VERSIYA}")
    print(f"Etalon implementasiya — Python {sys.version.split()[0]}")
    print(f"Platforma: {sys.platform}")
    print(f"Çıxış kodlaşdırması: {sys.stdout.encoding}")
    return 0


def əmr_kömək(_: list[str]) -> int:
    print(f"""Alqor {VERSIYA} — Azərbaycan dilində proqramlaşdırma dili

İSTİFADƏ:
    python alqorc.py <əmr> [arqumentlər]

ƏMRLƏR:
    işlət <fayl>         Proqramı icra edir
                         -- arq1 arq2    proqrama arqument ötürür
    tokenlər <fayl>      Faylı leksə edib tokenləri göstərir
                         --ətraflı / -e  əlavə məlumat
    söhbət               İnteraktiv rejim (REPL)
    yoxla <fayl|qovluq>  Leksik və sintaktik xətaları yoxlayır
    hərf <mətn>          az-AZ böyük/kiçik çevrilməsini göstərir
    sırala <söz>...      Azərbaycan əlifba sırası ilə sıralayır
    versiya              Versiya məlumatı
    kömək                Bu mətn

NÜMUNƏLƏR:
    python alqorc.py söhbət
    python alqorc.py işlət ../numuneler/02-dovrler.alqor
    python alqorc.py tokenlər ../numuneler/01-salam.alqor
    python alqorc.py yoxla ../numuneler
    python alqorc.py hərf "ışıq İmran"
    python alqorc.py sırala zəfər ağac çay ışıq ilk

MÜHİT DƏYİŞƏNLƏRİ:
    ALQOR_RENG=həmişə|heçvaxt|avto     rəngli çıxış

VƏZİYYƏT:
    Lekser, parser və interpretator hazırdır.
    Ətraflı: alqorc/VEZIYYET.md""")
    return 0


# ═══════════════════════════════════════════════════════════════════════
#  Dispetçer
# ═══════════════════════════════════════════════════════════════════════

ƏMRLƏR = {
    "işlət": əmr_işlət, "islet": əmr_işlət, "run": əmr_işlət,
    "tokenlər": əmr_tokenlər, "tokenler": əmr_tokenlər,
    "yoxla": əmr_yoxla,
    "söhbət": əmr_söhbət, "sohbet": əmr_söhbət, "repl": əmr_söhbət,
    "hərf": əmr_hərf, "herf": əmr_hərf,
    "sırala": əmr_sırala, "sirala": əmr_sırala,
    "versiya": əmr_versiya, "--versiya": əmr_versiya, "-v": əmr_versiya,
    "kömək": əmr_kömək, "komek": əmr_kömək,
    "--kömək": əmr_kömək, "--komek": əmr_kömək, "-k": əmr_kömək,
}


def çap_xəta(mesaj: str) -> None:
    print(f"✖ {mesaj}", file=sys.stderr)
    print(f"  `python alqorc.py kömək` yazın", file=sys.stderr)


def əsas(arqumentlər: list[str] | None = None) -> int:
    arq = list(sys.argv[1:] if arqumentlər is None else arqumentlər)
    if not arq:
        return əmr_kömək([])

    əmr = arq[0]
    işləyici = ƏMRLƏR.get(əmr)
    if işləyici is None:
        çap_xəta(f"naməlum əmr: {əmr!r}")
        oxşar = [a for a in ƏMRLƏR if a.startswith(əmr[:3])]
        if oxşar:
            print(f"  bəlkə: {', '.join(sorted(set(oxşar))[:3])}",
                  file=sys.stderr)
        return 3
    try:
        return işləyici(arq[1:])
    except KeyboardInterrupt:
        print("\n⊣ dayandırıldı", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(əsas())
