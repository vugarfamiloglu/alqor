"""
Alqor Studio — paletdəki vidjet miniatürləri.

Hər vidjet nümunə dəyərlərlə HƏQİQİ `vidjet` modulu ilə qurulur və
HTML-ə çevrilir — miniatür önbaxışdakı görünüşün eynisidir. Studio
onu kiçildilmiş halda (Shadow DOM içində, vidjet üslubu ilə) göstərir.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


def _boş(*_):
    """Miniatürdə ✕ / klik görünsün deyə — heç nə etmir."""


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
        # ── Əlavə elementlər ──
        "reytinq": {"dəyər": 4},
        "seqmentli": {"seçimlər": ["Gün", "Həftə", "Ay"], "dəyər": "Həftə"},
        "çipSeçimi": {"seçimlər": ["Alqor", "Python", "Rust"],
                      "seçilənlər": ["Alqor"]},
        "teqSahəsi": {"etiket": "Teqlər", "teqlər": ["veb", "api"],
                      "silindi": _boş},
        "təsdiqKodu": {"etiket": "SMS kodu", "dəyər": "4821"},
        "telefon": {"etiket": "Telefon", "dəyər": "50 123 45 67"},
        "ePoçt": {"etiket": "E-poçt"},
        "keçidSahəsi": {"etiket": "Sayt"},
        "pulSahəsi": {"etiket": "Məbləğ", "dəyər": "25.50"},
        "tarixAralığı": {"etiket": "Dövr", "başlanğıc": "2026-10-01",
                         "bitmə": "2026-10-07"},
        "tarixVaxt": {"etiket": "Görüş", "dəyər": "2026-10-07T09:30"},
        "ay": {"etiket": "Ay", "dəyər": "2026-10"},
        "sayğac": {"etiket": "Say", "dəyər": 3},
        "avtoTamamlama": {"etiket": "Şəhər", "yer": "Bakı…"},
        "faylSürüklə": {"etiket": "Sənəd yüklə"},
        "keçidDüyməsi": {"mətn": "Qalın", "ikon": "B", "basılı": True},
        "açılanMenyu": {"mətn": "Əməliyyatlar"},
        "bölünmüşDüymə": {"mətn": "Saxla"},
        "üzənDüymə": {"ikon": "+"},
        "çip": {"mətn": "Alqor", "növ": "əsas", "silindi": _boş},
        "ikon": {"simvol": "⚙", "ölçü": 32},
        "klaviş": {"düymələr": ["Ctrl", "Shift", "F"]},
        "vaxtXətti": {"elementlər": [["2024", "Başlanğıc"],
                                     ["2026", "1.0 buraxılışı"]]},
        "ağac": {"elementlər": [["mənbə", ["əsas.alq"]], "README.md"]},
        "siyahıQrupu": {"elementlər": [["Profil", "Ad, şəkil"],
                                       ["Təhlükəsizlik", "Şifrə"]],
                        "klik": _boş, "seçili": "Profil"},
        "avatarQrupu": {"adlar": ["Aysel Ə", "Kamran R", "Nərmin H",
                                  "Elşən Q", "Leyla M", "Murad S"],
                        "maksimum": 4},
        "göstərici": {"etiket": "Disk", "dəyər": 72, "yuxarı": 80},
        "qiymətKartı": {"plan": "Pro", "qiymət": "19 ₼",
                        "xüsusiyyətlər": ["10 layihə", "Dəstək"],
                        "seçilmiş": True},
        "xüsusiyyətSiyahısı": {"elementlər": ["Sürətli", "Pulsuz",
                                              "Azərbaycanca"]},
        "rəy": {"mətn": "Çox rahatdır!", "ad": "Aysel Əliyeva",
                "reytinqi": 5},
        "qəhrəman": {"başlıq": "Alqor", "altMətn": "Azərbaycan dilində",
                     "hərəkətlər": [d("düymə", mətn="Başla")]},
        "səhifəAltlığı": {"mətn": "© 2026 Alqor",
                          "keçidlər": [["#", "Haqqında"], ["#", "Əlaqə"]]},
        "qeydQutusu": {"başlıq": "Məsləhət", "mətn": "Ctrl+S ilə saxlayın"},
        "elanZolağı": {"mətn": "Yeni versiya çıxıb!"},
        "təqvim": {"il": 2026, "ayı": 10, "seçili": "2026-10-07"},
        "sütunQrafiki": {"dəyərlər": [12, 19, 7, 15, 10],
                         "etiketlər": ["Y", "F", "M", "A", "M"],
                         "hündürlük": 110},
        "xəttQrafiki": {"dəyərlər": [3, 8, 5, 12, 9, 14],
                        "hündürlük": 100},
        "dairəQrafiki": {"dəyərlər": [50, 30, 20],
                         "etiketlər": ["Veb", "Mobil", "PC"]},
        "kiçikQrafik": {"dəyərlər": [3, 5, 4, 8, 6, 9, 7, 11]},
        "video": {"poster": _ŞƏKİL},
        "audio": {},
        "yerləşdirmə": {"hündürlük": 60},
        "qalereya": {"şəkillər": [_ŞƏKİL] * 3},
        "karusel": {"slaydlar": [[_ŞƏKİL, "Bakı"], [_ŞƏKİL, "Şəki"]]},
        "işarəliMətn": {"mətn": "## Başlıq\n\n**Qalın** və `kod`"},
        "profilKartı": {"ad": "Aysel Əliyeva", "vəzifə": "Proqramçı"},
        "bildirişNişanı": {"say": 3},
        "yüklənməÖrtüyü": {"məzmun": d("mətn", məzmun="Məzmun…")},
        "nəticə": {"növ": "uğur", "başlıq": "Hazırdır"},
        "şifrəGücü": {"şifrə": "Alqor2026!"},
        "konteyner": {"məzmun": d("mətn", məzmun="Konteyner")},
        "mərkəz": {"məzmun": d("nişan", mətn="Orta"), "hündürlük": 50},
        "ikiSütun": {"sol": d("nişan", mətn="Sol"),
                     "sağ": d("nişan", mətn="Sağ")},
        "nisbət": {"məzmun": d("şəkil", mənbə=_ŞƏKİL), "forma": "4/1"},
        "sürüşmə": {"məzmun": d("mətn", məzmun="Uzun məzmun…"),
                    "hündürlük": 50},
        "tətbiqQabığı": {"başlıq": d("mətn", məzmun="Tətbiq"),
                         "yan": d("mətn", məzmun="Menyu"),
                         "məzmun": d("mətn", məzmun="Məzmun")},
        "yanNaviqasiya": {"elementlər": ["Ana", "Hesabatlar"],
                          "cari": "Ana"},
        "alətlərPaneli": {"məzmun": [d("ikonDüymə", ikon="B"),
                                     d("ikonDüymə", ikon="I"),
                                     d("ikonDüymə", ikon="U")]},
        "açılanPanel": {"düymə": "Filtr"},
        "təsdiqDialoqu": {"başlıq": "Silinsin?", "mətn": "Geri qaytarılmır",
                          "təhlükəli": True},
        "altVərəq": {"başlıq": "Paylaş", "məzmun": "…"},
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
