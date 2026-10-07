"""
Alqor Studio — paletdəki vidjet miniatürləri.

Hər vidjet nümunə dəyərlərlə HƏQİQİ `vidjet` modulu ilə qurulur və
HTML-ə çevrilir — miniatür önbaxışdakı görünüşün eynisidir. Studio
onu kiçildilmiş halda (Shadow DOM içində, vidjet üslubu ilə) göstərir.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


def _nümunələr(V, i) -> dict[str, dict[str, Any]]:
    d = lambda ad, **k: getattr(V, ad)(i, **k)          # noqa: E731
    return {
        "düymə": {"mətn": "Yadda saxla"},
        "ikonDüymə": {"ikon": "✕", "başlıq": "Sil", "növ": "ikinci"},
        "düyməQrupu": {"məzmun": [d("düymə", mətn="Bəli"),
                                  d("düymə", mətn="Xeyr", növ="ikinci")]},
        "əlaqə": {"mətn": "Ətraflı oxu", "ünvan": "#"},
        "sahə": {"etiket": "Ad", "yer": "Aysel"},
        "parol": {"etiket": "Şifrə", "yer": "••••••"},
        "ədəd": {"etiket": "Yaş", "dəyər": 25},
        "axtarış": {"yer": "Axtar…"},
        "çoxsətirli": {"etiket": "Qeyd", "yer": "Mətn…", "sətirlər": 2},
        "seçim": {"etiket": "Şəhər", "seçimlər": ["Bakı", "Gəncə"],
                  "dəyər": "Bakı"},
        "qeyd": {"etiket": "Razıyam", "işarələnmiş": True},
        "açar": {"etiket": "Bildirişlər", "yanıq": True},
        "radioQrupu": {"etiket": "Növ", "seçimlər": ["A", "B"],
                       "dəyər": "A", "üfüqi": True},
        "sürüşdürücü": {"etiket": "Səs", "dəyər": 60},
        "tarix": {"etiket": "Tarix", "dəyər": "2026-10-07"},
        "vaxt": {"etiket": "Vaxt", "dəyər": "09:30"},
        "rəng": {"etiket": "Rəng", "dəyər": "#0b6bcb"},
        "faylSahəsi": {"etiket": "Fayl"},
        "form": {"məzmun": [d("sahə", etiket="E-poçt"),
                            d("düymə", mətn="Göndər")]},
        "sahəDəsti": {"başlıq": "Ünvan",
                      "məzmun": [d("sahə", etiket="Şəhər")]},
        "etiket": {"mətn": "Etiket"},
        "başlıq": {"mətn": "Başlıq", "səviyyə": 2},
        "mətn": {"məzmun": "Adi mətn paraqrafı"},
        "nişan": {"mətn": "Yeni", "növ": "uğur"},
        "xəbərdarlıq": {"mətn": "Uğurla saxlanıldı", "növ": "uğur"},
        "kart": {"başlıq": "Kart", "məzmun": d("mətn", məzmun="Məzmun")},
        "cədvəl": {"sütunlar": ["Ad", "Bal"],
                   "sətirlər": [["Aysel", 95], ["Kamran", 88]]},
        "siyahı": {"elementlər": ["Birinci", "İkinci", "Üçüncü"]},
        "təsvirSiyahısı": {"cütlər": [["Ad", "Aysel"], ["Yaş", "25"]]},
        "kod": {"məzmun": 'yaz("Salam")'},
        "sitat": {"mətn": "Bilik gücdür.", "mənbə": "Bekon"},
        "şəkil": {"mənbə": _ŞƏKİL, "alternativ": "şəkil", "en": 120,
                  "hündürlük": 60},
        "avatar": {"ad": "Aysel Əliyeva"},
        "ayırıcı": {"mətn": "və ya"},
        "boşBaxış": {"başlıq": "Heç nə yoxdur", "ikon": "📭"},
        "tərəqqi": {"dəyər": 65, "faizGöstər": True},
        "halqaTərəqqi": {"dəyər": 70, "ölçü": 56},
        "fırlanan": {"mətn": "Yüklənir…"},
        "skeletYüklənmə": {"sətirlər": 3},
        "statistika": {"etiket": "Satış", "dəyər": "1 240",
                       "dəyişmə": "+12%"},
        "qutu": {"məzmun": d("mətn", məzmun="Qutu"), "boşluq": 12,
                 "kənar": True},
        "sətir": {"məzmun": [d("nişan", mətn="A"), d("nişan", mətn="B"),
                             d("nişan", mətn="C")]},
        "sütun": {"məzmun": [d("nişan", mətn="A"), d("nişan", mətn="B")]},
        "tor": {"məzmun": [d("nişan", mətn=str(n)) for n in range(1, 5)],
                "sütunlar": 2},
        "boşluq": {"hündürlük": 8},
        "panel": {"başlıq": "Panel", "məzmun": d("mətn", məzmun="Məzmun")},
        "bölmə": {"başlıq": "Bölmə", "məzmun": d("mətn", məzmun="…")},
        "naviqasiya": {"başlıq": "Alqor",
                       "elementlər": [["Ana", "#"], ["Haqqında", "#"]]},
        "nişanlar": {"elementlər": ["Ümumi", "Ayarlar"], "cari": 0},
        "yığcam": {"başlıq": "Ətraflı", "məzmun": "…", "açılmış": False},
        "səhifələmə": {"səhifə": 2, "cəmi": 5},
        "addımlar": {"adlar": ["Səbət", "Ödəniş", "Hazır"], "cari": 1},
        "çörəkQırıntıları": {"yollar": [["Ana", "#"], ["Kitablar", "#"],
                                       ["Roman", None]]},
        "modal": {"başlıq": "Təsdiq", "məzmun": "Silinsin?",
                  "görünür": True},
        "yanPanel": {"başlıq": "Menyu", "məzmun": "…", "görünür": True},
        "ipucu": {"mətn": "İpucu", "məzmun": d("düymə", mətn="?",
                                               növ="ikinci")},
        "bildirişQutusu": {"mətn": "Saxlanıldı", "növ": "uğur"},
    }


_ŞƏKİL = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'"
          " viewBox='0 0 120 60'><rect width='120' height='60' fill='%23dbeafe'"
          "/><circle cx='30' cy='22' r='9' fill='%23fbbf24'/><path d='M0 60 "
          "L45 28 L75 50 L95 36 L120 60Z' fill='%2393c5fd'/></svg>")


@lru_cache(maxsize=1)
def hamısı() -> dict[str, str]:
    """{vidjet adı: HTML}. Uğursuz olan vidjet sadəcə buraxılır."""
    from alqor import vidjet as V
    from alqor.icraci import İcraçı

    i = İcraçı(çıxış=lambda *_: None)
    try:
        nümunələr = _nümunələr(V, i)
    except Exception:                                   # noqa: BLE001
        nümunələr = {}
    n: dict[str, str] = {}
    for ad in V.VİDJETLƏR:
        try:
            e = getattr(V, ad)(i, **nümunələr.get(ad, {}))
            n[ad] = e.HTML(i)
        except Exception:                               # noqa: BLE001
            continue
    return n


def üslub() -> str:
    from alqor import vidjet as V
    return V.ÜSLUB
