#!/usr/bin/env python3
"""
Alqor — sınaq işlədicisi.

    python sina.py              bütün sınaqlar
    python sina.py -v           ətraflı
    python sina.py elifba       yalnız elifba sınaqları
    python sina.py --nümunələr  nümunə proqramları da yoxlayır
"""

import sys
import unittest
from pathlib import Path

for _axın in (sys.stdout, sys.stderr):
    try:
        _axın.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

KÖK = Path(__file__).parent
sys.path.insert(0, str(KÖK))


def nümunələri_yoxla() -> int:
    """Bütün `numuneler/*.alqor` fayllarını leksə edir."""
    from alqor.lekser import faylı_leksə

    qovluq = KÖK.parent / "numuneler"
    if not qovluq.exists():
        print("⚠ nümunələr qovluğu tapılmadı")
        return 0

    fayllar = sorted(qovluq.glob("*.alqor"))
    print(f"\n── Nümunə proqramlar ({len(fayllar)}) " + "─" * 30)

    xəta_sayı = 0
    for f in fayllar:
        tokenlər, x = faylı_leksə(f)
        if x.uğurludur():
            xb = len(x.xəbərdarlıqlar)
            qeyd = f"  ({xb} xəbərdarlıq)" if xb else ""
            print(f"  ✓ {f.name:<28} {len(tokenlər):>5} token{qeyd}")
        else:
            xəta_sayı += 1
            print(f"  ✖ {f.name:<28} {len(x.xətalar)} xəta")
            for d in x.xətalar:
                print(f"      {d.kod}  {d.mesaj}  ({d.yer})")
    return xəta_sayı


def əsas() -> int:
    arq = sys.argv[1:]
    ətraflı = "-v" in arq or "--ətraflı" in arq
    nümunələr = "--nümunələr" in arq or "--numuneler" in arq
    süzgəc = [a for a in arq if not a.startswith("-")]

    yükləyici = unittest.TestLoader()
    if süzgəc:
        dəst = unittest.TestSuite()
        for ad in süzgəc:
            modul = ad if ad.startswith("test_") else f"test_{ad}"
            dəst.addTests(yükləyici.loadTestsFromName(f"sinaq.{modul}"))
    else:
        dəst = yükləyici.discover(str(KÖK / "sinaq"), top_level_dir=str(KÖK))

    nəticə = unittest.TextTestRunner(
        verbosity=2 if ətraflı else 1,
        stream=sys.stdout).run(dəst)

    nümunə_xətası = nümunələri_yoxla() if nümunələr else 0

    print()
    if nəticə.wasSuccessful() and nümunə_xətası == 0:
        say = nəticə.testsRun
        print(f"✓ {say} sınaq keçdi")
        return 0
    print(f"✖ {len(nəticə.failures)} uğursuz, {len(nəticə.errors)} xəta, "
          f"{nümunə_xətası} nümunə problemi")
    return 1


if __name__ == "__main__":
    sys.exit(əsas())
