"""
Alqor Studio — komponentin canlı önbaxışı.

AYRICA PROSESDƏ işləyir (istifadəçi kodu sonsuz dövrə düşsə Studio
dayanmasın):

    python onbaxis.py <fayl.alq> [KomponentAdı]

Fayldakı elanlar (sinif, komponent, funksiya, `gətir`, üst-səviyyə
dəyişənlər) icra olunur, `əsas()` İSƏ ÇAĞIRILMIR. Sonra seçilmiş
komponent `pəncərə` modulunun öz serverində göstərilir — düymələr,
sahələr və vəziyyət həqiqi tətbiqdəki kimi işləyir. Studio həmin
ünvanı önbaxış çərçivəsində (iframe) açır.

Prosesin ilk çıxış sətri JSON-dur:
    {"ünvan": "http://127.0.0.1:PORT/?p=0", "komponent": "Ad", ...}
və ya
    {"xəta": "…"}
"""

from __future__ import annotations
import json
import os
import sys
import threading
import time
from pathlib import Path

for _axın in (sys.stdout, sys.stderr):
    try:
        _axın.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alqor import aac as A                                  # noqa: E402
from alqor.deyerler import AlqorXəta                        # noqa: E402
from alqor.lekser import Lekser                             # noqa: E402
from alqor.menbe import Mənbə                               # noqa: E402
from alqor.parser import Parser                             # noqa: E402
from alqor.xeta import XətaToplayıcı                        # noqa: E402

# Önbaxış elementi vurğulamaq üçün əlavə üslub
ÖNBAXIŞ_ÜSLUBU = """
#alqor-kök{padding:16px}
"""


def _bildir(d: dict) -> None:
    print(json.dumps(d, ensure_ascii=False), flush=True)


def komponentlər(ağac: A.Proqram) -> list[str]:
    return [c.ad for c in ağac.gövdə
            if isinstance(c, A.SinifElanı) and c.quruluş == "komponent"]


def element_qur(yol: Path, ad: str | None = None):
    """Faylı yükləyir, komponentin elementini qurur.

    Qaytarır: (icraçı, element, komponent adı, bütün komponentlər)."""
    from alqor.icraci import İcraçı

    x = XətaToplayıcı()
    s = Mənbə.fayldan(yol, x)
    if s is None:
        raise ValueError(x.hesabat(rəngli=False))
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise ValueError(x.hesabat(rəngli=False))
    adlar = komponentlər(ağac)
    if not adlar:
        raise LookupError("Bu faylda `komponent` yoxdur — önbaxış yalnız "
                          "komponentlər üçündür")
    if ad and ad not in adlar:
        raise LookupError(f"`{ad}` komponenti tapılmadı. "
                          f"Mövcud: {', '.join(adlar)}")
    ad = ad or adlar[0]

    # Proqramın öz `yaz(...)` çıxışı önbaxışı pozmasın
    icraçı = İcraçı(çıxış=lambda m: print(m, file=sys.stderr))
    icraçı.əsas_qovluq = yol.resolve().parent
    m = icraçı.qlobal
    icraçı._elanları_qaldır(ağac.gövdə, m)
    for c in ağac.gövdə:
        # Yalnız elan xarakterli cümlələr — yan təsirli kod (yaz, server
        # qaldırmaq …) icra olunmur
        if isinstance(c, (A.İdxal, A.DəyişənElanı, A.TipAliası)):
            icraçı._cümlə(c, m)

    # `<Ad />` elementini həmin mühitdə qururuq
    x2 = XətaToplayıcı()
    s2 = Mənbə.mətndən(f"dəyişən studioÖnbaxışı = <{ad} />\n",
                       "<önbaxış>", x2)
    for c in Parser(Lekser(s2, x2).leksə(), s2, x2).ayır().gövdə:
        icraçı._cümlə(c, m)
    element = m.al("studioÖnbaxışı")
    return icraçı, element, ad, adlar


def hazırla(yol: Path, ad: str | None = None):
    """Faylı yükləyir, komponenti göstərməyə hazır pəncərə qaytarır."""
    from alqor import pencere as P
    from alqor import vidjet as V

    icraçı, element, ad, adlar = element_qur(yol, ad)
    p = P.Pəncərə(icraçı, f"{ad} — önbaxış", 800, 600)
    p.məzmun(element)
    p.üslub(V.ÜSLUB + ÖNBAXIŞ_ÜSLUBU)
    # İlk göstərmə xətasız olmalıdır
    p.kök_HTML()
    return icraçı, p, ad, adlar


def _əmrləri_oxu(t, p, yol: Path, ad: str) -> None:
    """
    Studio-dan gələn əmrlər (stdin, hər sətir bir əmr):

        yenilə      fayl yenidən oxunur, komponent təzədən qurulur —
                    proses və server qalır, ünvan dəyişmir. Xüsusiyyətlər
                    panelindəki hər dəyişiklik belə görünür (~50 ms).

    Hər əmrə bir JSON sətri ilə cavab verilir.
    """
    for sətir in sys.stdin:
        əmr = sətir.strip()
        if əmr != "yenilə":
            continue
        try:
            icraçı, element, _, adlar = element_qur(yol, ad)

            def dəyiş():
                köhnə = p._icraçı, p._məzmun
                # Yeni icraçı köhnə tətbiqi (server, növbə) paylaşır
                icraçı._pəncərə_tətbiqi = t
                p._icraçı = icraçı
                p.məzmun(element)
                try:
                    p.kök_HTML()         # xətalı versiya göstərilməsin
                except BaseException:
                    p._icraçı = köhnə[0]
                    p.məzmun(köhnə[1])
                    raise
            t.növbəyə(dəyiş)
            _bildir({"yeniləndi": True, "komponentlər": adlar})
        except (ValueError, LookupError) as x:
            _bildir({"xəta": str(x)})
        except AlqorXəta as x:
            _bildir({"xəta": f"{x.tip}: {x.mesaj}"})
        except RecursionError:
            _bildir({"xəta": "StekDaşmaXətası: çağırış dərinliyi həddi "
                             "aşıldı"})
        except BaseException as x:              # noqa: BLE001
            _bildir({"xəta": f"{type(x).__name__}: {x}"})


def _valideyni_izlə(valideyn: int) -> None:
    """Studio bağlananda önbaxış da bitsin."""
    while True:
        time.sleep(2)
        if os.getppid() != valideyn:
            os._exit(0)


def əsas(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        _bildir({"xəta": "fayl adı lazımdır"})
        return 3
    yol = Path(arqumentlər[0])
    ad = arqumentlər[1] if len(arqumentlər) > 1 else None
    try:
        icraçı, p, ad, adlar = hazırla(yol, ad)
    except (ValueError, LookupError) as x:
        _bildir({"xəta": str(x)})
        return 2
    except AlqorXəta as x:
        _bildir({"xəta": f"{x.tip}: {x.mesaj}"})
        return 1
    except RecursionError:
        _bildir({"xəta": "StekDaşmaXətası: çağırış dərinliyi həddi aşıldı"})
        return 1

    from alqor import pencere as P
    t = P.tətbiq(icraçı)
    # Pəncərə açılmır — yalnız server; çərçivəni Studio göstərir
    t.başsız = False
    p._açıqdır = True
    t._serveri_qaldır()
    _bildir({"ünvan": p.ünvan(), "komponent": ad, "komponentlər": adlar})
    threading.Thread(target=_valideyni_izlə, args=(os.getppid(),),
                     daemon=True).start()
    threading.Thread(target=_əmrləri_oxu, args=(t, p, yol, ad),
                     daemon=True).start()
    try:
        t.işlət()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(əsas(sys.argv[1:]))
