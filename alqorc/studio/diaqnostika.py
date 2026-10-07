"""
Alqor Studio — diaqnostika: lekser + parser + tip yoxlayıcı.

Redaktor yazılan kodu (saxlanmamış mətni) bura göndərir; cavab
`sətir`/`sütun` (1-dən) + mesaj + kod siyahısıdır. Redaktor onları
dalğalı xətt və "Problemlər" siyahısı kimi göstərir.
"""

from __future__ import annotations
from typing import Any

from alqor.lekser import Lekser
from alqor.menbe import Mənbə
from alqor.parser import Parser
from alqor.xeta import Diaqnostika, Səviyyə, XətaToplayıcı

TİP_REJİMLƏRİ = ("sərbəst", "normal", "sərt")


def _lüğət(d: Diaqnostika) -> dict[str, Any]:
    n: dict[str, Any] = {
        "kod": d.kod,
        "mesaj": d.mesaj,
        "səviyyə": d.səviyyə.adı,
        "qeyd": d.qeyd,
        "köməklər": list(d.köməklər),
        "sətir": 1, "sütun": 1, "sonSətir": 1, "sonSütun": 2,
        "başlanğıc": 0, "uzunluq": 0,
    }
    if d.yer is not None:
        m = d.yer.mənbə
        sətir, sütun = m.sətir_sütun(d.yer.başlanğıc)
        uz = max(1, d.yer.uzunluq)
        son_sətir, son_sütun = m.sətir_sütun(d.yer.başlanğıc + uz)
        n.update(sətir=sətir, sütun=sütun, sonSətir=son_sətir,
                 sonSütun=son_sütun, başlanğıc=d.yer.başlanğıc,
                 uzunluq=uz)
    return n


def yoxla(mətn: str, ad: str = "fayl.alq", rejim: str = "normal",
          tip: bool = True) -> dict[str, Any]:
    """
    Mətni yoxlayır. Leksik/sintaktik xəta yoxdursa tip yoxlaması da
    aparılır (`alqorc.py yoxla` ilə eyni ardıcıllıq).
    """
    if rejim not in TİP_REJİMLƏRİ:
        rejim = "normal"
    x = XətaToplayıcı()
    mərhələ = "lekser"
    try:
        s = Mənbə.mətndən(mətn, ad, x)
        tokenlər = Lekser(s, x).leksə()
        mərhələ = "parser"
        ağac = Parser(tokenlər, s, x).ayır()
        if tip and x.uğurludur():
            mərhələ = "tip"
            from alqor.tipyoxlayici import tipləri_yoxla
            tipləri_yoxla(ağac, x, rejim)
    except RecursionError:
        x.xəta("ALQ-S001", f"{mərhələ}: iç-içəlik çox dərindir")
    except Exception as xəta:                       # noqa: BLE001
        # Alətin daxili xətası redaktoru sındırmamalıdır
        x.əlavə(Diaqnostika(
            "ALQ-S000",
            f"{mərhələ} daxili xəta verdi: {type(xəta).__name__}: {xəta}",
            None, Səviyyə.MELUMAT))
    siyahı = [_lüğət(d) for d in x._sıralı()]
    return {
        "diaqnostikalar": siyahı,
        "xəta": len(x.xətalar),
        "xəbərdarlıq": len(x.xəbərdarlıqlar),
        "ascii": sum(1 for d in x.siyahı if d.kod == "ALQ-L020"),
        "mərhələ": mərhələ,
    }


def ascii_düzəlt(mətn: str) -> tuple[str, int]:
    """
    Bütün ASCII açar sözləri kanonik formaya çevirir (`eger` → `əgər`).
    Lekserin özü hansı tokenin ASCII yazıldığını bilir, ona görə
    identifikatorlara və mətnlərə toxunulmur.
    """
    from alqor.acar_sozler import ASCII_ALIAS
    x = XətaToplayıcı()
    s = Mənbə.mətndən(mətn, "<studio>", x)
    if s.mətn != mətn:
        # NFC/CRLF dəyişikliyi — mövqelər uyğun gəlmir, toxunmuruq
        return mətn, 0
    Lekser(s, x, ascii_xəbərdarlığı=True).leksə()
    əvəzlər: list[tuple[int, int, str]] = []
    for d in x.siyahı:
        if d.kod != "ALQ-L020" or d.yer is None:
            continue
        yazılan = mətn[d.yer.başlanğıc:d.yer.son]
        kanonik = ASCII_ALIAS.get(" ".join(yazılan.split()))
        if kanonik:
            əvəzlər.append((d.yer.başlanğıc, d.yer.uzunluq, kanonik))
    nəticə = mətn
    for baş, uz, k in sorted(əvəzlər, reverse=True):
        nəticə = nəticə[:baş] + k + nəticə[baş + uz:]
    return nəticə, len(əvəzlər)
