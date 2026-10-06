"""
Spesifikasiya § 14-ün arayış hissəsini `vidjet` modulunun özündən qurur.

Vidjet siyahısı, parametrlər, standart dəyərlər, hadisələr, nümunələr və
kod skeletləri koddan götürülür — sənəd kodla aralana bilməz. Əl ilə
yazılan yalnız parametr izahlarıdır (`İZAHLAR`); yeni parametr əlavə
edilib izahı yazılmasa, `sinaq/test_vidjet.py` sınır.

    python -m alqor.vidjet_arayis            # arayışı çap edir
    python -m alqor.vidjet_arayis --yaz      # spesifikasiyanı yeniləyir
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

from . import vidjet as V

SƏNƏD = (Path(__file__).resolve().parent.parent.parent
         / "spesifikasiya" / "14-VIDJETLER.md")
BAŞLANĞIC = "<!-- ARAYIŞ BAŞLANĞICI: vidjet_arayis.py yaradır, əl ilə " \
            "dəyişməyin -->"
SON = "<!-- ARAYIŞ SONU -->"

# ── Parametr izahları ──────────────────────────────────────────────────
# Ümumi izah; vidjetə xas fərq `XÜSUSİ`-dədir.

İZAHLAR: dict[str, str] = {
    "məzmun": "uşaq element(lər) — tək element və ya siyahı",
    "etiket": "sahənin üstündəki görünən ad",
    "ad": "sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır",
    "mətn": "görünən mətn",
    "dəyər": "cari dəyər",
    "dəyişdi": "dəyər dəyişəndə çağırılır — yeni dəyəri alır",
    "yazıldı": "hər düymə basışında çağırılır — cari mətni alır",
    "söndürülmüş": "`doğru` olduqda element sönükdür, hadisə getmir",
    "başlıq": "başlıq mətni",
    "kömək": "sahənin altında kiçik izah mətni",
    "klik": "basıldıqda çağırılır",
    "növ": "rəng növü",
    "ölçü": "`kiçik` · `orta` · `böyük`",
    "xəta": "doluysa sahə qırmızı çərçivə alır, mətn altda görünür "
            "(`kömək`-i əvəzləyir)",
    "tələb": "məcburi sahə — etiketin yanında `*`",
    "maksimum": "ən böyük dəyər",
    "minimum": "ən kiçik dəyər",
    "ikon": "ikon kimi işlənən simvol (məs. `\"✕\"`, `\"⚙\"`)",
    "yer": "boş sahədə görünən ipucu (`placeholder`)",
    "bağlandı": "bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə "
                "düymə görünmür",
    "boşluq": "uşaqlar arası məsafə — ədəd piksel sayılır, mətn "
              "olduğu kimi (`\"1rem\"`)",
    "kimlik": "HTML `id` atributu",
    "sətirlər": "sətir sayı",
    "altMətn": "başlığın altında sönük izah",
    "elementlər": "elementlərin siyahısı",
    "mənbə": "şəklin ünvanı (URL və ya yol)",
    "pillə": "bir addımda dəyişmə miqdarı",
    "göndərildi": "form göndəriləndə (Enter) çağırılır",
    "seçimlər": "`[\"a\", \"b\"]` · `{\"az\": \"Azərbaycan\"}` · "
                "`[[\"az\", \"Azərbaycan\"]]`",
    "altlıq": "aşağı hissə — adətən düymələr",
    "sütunlar": "sütun sayı",
    "en": "en — ədəd piksel sayılır",
    "hündürlük": "hündürlük — ədəd piksel sayılır",
    "düzləndir": "`başlanğıc` · `mərkəz` · `son` · `ara` · `ətraf` · "
                 "`bərabər` · `dolu`",
    "cari": "seçili element",
    "görünür": "`yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə "
               "olunur",
    "tərəf": "hansı tərəfdə",
    "gözləyir": "fırlanan göstərir və düyməni söndürür (sorğu gedərkən)",
    "tamEn": "düymə bütün eni tutur",
    "əlavəSinif": "əlavə CSS sinfi",
    "ünvan": "keçid ünvanı (`href`)",
    "yeniNişan": "ünvanı yeni nişanda açır",
    "oxunaqlı": "yalnız oxunur, dəyişdirilmir",
    "boşEtiket": "siyahının əvvəlində boş dəyərli seçim (məs. "
                 "`\"Seçin…\"`)",
    "işarələnmiş": "işarəli vəziyyət",
    "yanıq": "açarın yanılı vəziyyəti",
    "üfüqi": "seçimləri bir sətirdə düzür",
    "dəyəriGöstər": "sürüşdürücünün yanında cari dəyəri göstərir",
    "növlər": "qəbul edilən fayl növləri: `[\".png\", \"image/*\"]`",
    "çoxlu": "bir neçə fayl seçməyə icazə verir",
    "sıx": "sahələr arası məsafəni azaldır",
    "sahəsi": "etiketin bağlandığı sahənin `ad`-ı",
    "səviyyə": "`1`–`6` (`<h1>`–`<h6>`)",
    "sönük": "boz, ikinci dərəcəli mətn",
    "qalın": "qalın şrift",
    "bağlana": "bağlama düyməsi (✕) göstərir",
    "boşMətn": "sətir olmayanda göstərilən mətn",
    "zolaqlı": "cüt sətirlərin fonu fərqlənir",
    "çərçivəli": "bütün xanaların çərçivəsi",
    "sətirKlik": "sətir basıldıqda çağırılır — sətrin indeksini (0-dan, "
                 "mətn kimi) alır",
    "nömrəli": "nömrəli siyahı (`<ol>`)",
    "işarəsiz": "siyahı işarələri gizlənir",
    "cütlər": "ad → dəyər lüğəti",
    "dil": "proqramlaşdırma dili (`data-dil` atributu)",
    "alternativ": "şəkil yüklənməyəndə və ekran oxuyucusu üçün mətn",
    "yuvarlaq": "dairəvi kəsim",
    "hərəkət": "altda göstərilən element — adətən düymə",
    "faizGöstər": "faizi rəqəmlə göstərir",
    "qeyriMüəyyən": "müddəti bilinməyən iş — hərəkətli zolaq",
    "dəyişmə": "dəyişmə faizi: müsbət ▲ yaşıl, mənfi ▼ qırmızı",
    "kənar": "çərçivə xətti",
    "fon": "fon rəngi (CSS dəyəri)",
    "şaquli": "şaquli düzləndirmə (`düzləndir` ilə eyni dəyərlər)",
    "sarı": "yer çatmayanda uşaqlar növbəti sətrə keçir",
    "alətlər": "başlığın sağında element(lər) — adətən düymələr",
    "sağ": "sağ küncdəki element(lər)",
    "açılmış": "ilkin vəziyyətdə açıqdır",
    "səhifə": "cari səhifə (1-dən)",
    "cəmi": "səhifələrin sayı",
    "adlar": "addımların adları",
    "yollar": "`[[ünvan, ad], …]` — sonuncu cari səhifədir",
}

XÜSUSİ: dict[tuple[str, str], str] = {
    ("ikonDüymə", "başlıq"): "üzərinə gələndə ipucu və ekran oxuyucusu "
                             "üçün ad — ikon düymədə vacibdir",
    ("düymə", "növ"): "`əsas` · `ikinci` · `sakit` · `təhlükə` · `uğur` · "
                      "`xəbərdarlıq` · `əlaqə`",
    ("ikonDüymə", "növ"): "`düymə` ilə eyni növlər",
    ("nişan", "növ"): "`düymə` ilə eyni növlər",
    ("tərəqqi", "növ"): "dolğunun rəngi — `düymə` ilə eyni növlər",
    ("xəbərdarlıq", "növ"): "`uğur` · `xəbərdarlıq` · `təhlükə` · "
                            "`məlumat`",
    ("bildirişQutusu", "növ"): "`uğur` · `xəbərdarlıq` · `təhlükə` · "
                               "`məlumat`",
    ("statistika", "dəyər"): "əsas rəqəm (mətn kimi göstərilir)",
    ("statistika", "etiket"): "rəqəmin üstündəki ad",
    ("tərəqqi", "etiket"): "zolağın üstündəki ad",
    ("tərəqqi", "dəyər"): "`0`–`maksimum`; həddən kənar dəyər kəsilir",
    ("halqaTərəqqi", "dəyər"): "`0`–`maksimum`",
    ("halqaTərəqqi", "ölçü"): "diametr, piksel",
    ("halqaTərəqqi", "mətn"): "ortadakı mətn; verilməyibsə faiz",
    ("fırlanan", "mətn"): "fırlananın yanındakı mətn",
    ("skeletYüklənmə", "en"): "sətirlərin eni",
    ("mətn", "məzmun"): "abzas mətni",
    ("kod", "məzmun"): "kod mətni — HTML qaçışı avtomatikdir",
    ("sitat", "mənbə"): "sitatın müəllifi / mənbəyi",
    ("avatar", "ad"): "tam ad — şəkil yoxdursa baş hərflər göstərilir "
                      "(`Aysel Məmmədova` → `AM`)",
    ("avatar", "mənbə"): "şəkil ünvanı (ixtiyari)",
    ("ayırıcı", "mətn"): "xəttin ortasında mətn (ixtiyari)",
    ("boşBaxış", "ikon"): "böyük simvol",
    ("boşBaxış", "mətn"): "izah mətni",
    ("cədvəl", "sütunlar"): "başlıqlar: `[\"Ad\", \"Yaş\"]` və ya "
                            "`[[\"ad\", \"Ad\"], …]` (açar → başlıq)",
    ("cədvəl", "sətirlər"): "siyahı siyahısı, lüğət siyahısı və ya "
                            "obyekt siyahısı",
    ("siyahı", "elementlər"): "mətn və ya element siyahısı",
    ("naviqasiya", "elementlər"): "orta hissədəki element(lər) — "
                                  "adətən `əlaqə`",
    ("naviqasiya", "başlıq"): "sol küncdə tətbiqin adı",
    ("nişanlar", "elementlər"): "nişanlar (`seçimlər` formatında)",
    ("nişanlar", "klik"): "nişan basıldıqda çağırılır — nişanın "
                          "dəyərini alır",
    ("nişanlar", "məzmun"): "nişan sətrinin altındakı gövdə",
    ("nişanlar", "cari"): "seçili nişanın dəyəri; verilməyibsə birincisi",
    ("səhifələmə", "klik"): "səhifə basıldıqda çağırılır — səhifə "
                            "nömrəsini mətn kimi alır",
    ("çörəkQırıntıları", "klik"): "qırıntı basıldıqda çağırılır — "
                                  "ünvanı alır",
    ("addımlar", "cari"): "cari addım (1-dən); əvvəlkilər ✓ ilə",
    ("kart", "klik"): "verilibsə bütün kart basılandır",
    ("kart", "altMətn"): "başlığın altında sönük mətn",
    ("tor", "sütunlar"): "sütun sayı",
    ("tor", "minimum"): "verilibsə sütun sayı avtomatikdir: hər sütun "
                        "ən azı bu endədir",
    ("qutu", "boşluq"): "daxili boşluq (`padding`)",
    ("boşluq", "hündürlük"): "boş sahənin hündürlüyü",
    ("sətir", "düzləndir"): "üfüqi düzləndirmə: `başlanğıc` · `mərkəz` · "
                            "`son` · `ara` · `ətraf` · `bərabər`",
    ("sütun", "düzləndir"): "uşaqların eni: `dolu` (tam en) · "
                            "`başlanğıc` · `mərkəz` · `son`",
    ("modal", "ölçü"): "pəncərənin eni: `kiçik` · `orta` · `böyük`",
    ("yanPanel", "tərəf"): "`sol` · `sağ`",
    ("ipucu", "tərəf"): "`üst` · `alt` · `sol` · `sağ`",
    ("ipucu", "mətn"): "ipucunun mətni",
    ("ipucu", "məzmun"): "üzərinə gəlinəcək element",
    ("bildirişQutusu", "mətn"): "bildirişin mətni",
    ("xəbərdarlıq", "bağlandı"): "`bağlana: doğru` olduqda ✕ basılanda "
                                 "çağırılır",
    ("form", "başlıq"): "formun üstündəki başlıq",
    ("sahəDəsti", "başlıq"): "qrupun adı (`<legend>`)",
    ("etiket", "mətn"): "etiketin mətni",
    ("radioQrupu", "dəyər"): "seçili seçimin dəyəri",
    ("seçim", "dəyər"): "seçili seçimin dəyəri",
    ("qeyd", "etiket"): "qutunun yanındakı mətn",
    ("açar", "etiket"): "açarın yanındakı mətn",
    ("qeyd", "dəyişdi"): "işarələnəndə/götürüləndə çağırılır — "
                         "`doğru`/`yanlış` alır",
    ("açar", "dəyişdi"): "yandırılanda/söndürüləndə çağırılır — "
                         "`doğru`/`yanlış` alır",
    ("sürüşdürücü", "dəyişdi"): "sürüşdürərkən çağırılır — dəyəri mətn "
                                "kimi alır",
    ("ədəd", "dəyişdi"): "dəyər dəyişəndə çağırılır — mətn kimi alır "
                         "(`tamƏt`/`onluqƏt` ilə çevirin)",
    ("tarix", "dəyər"): "`\"2026-10-06\"` formatında",
    ("tarix", "minimum"): "ən erkən tarix (`\"YYYY-AA-GG\"`)",
    ("tarix", "maksimum"): "ən gec tarix (`\"YYYY-AA-GG\"`)",
    ("vaxt", "dəyər"): "`\"14:30\"` formatında",
    ("rəng", "dəyər"): "`\"#rrggbb\"` formatında",
    ("faylSahəsi", "dəyişdi"): "fayl seçiləndə çağırılır — faylın adını "
                               "alır",
    ("panel", "başlıq"): "panelin başlıq zolağı",
    ("bölmə", "başlıq"): "bölmənin başlığı (`<h2>`)",
    ("əlaqə", "klik"): "verilibsə keçid əvəzinə idarəedici işləyir",
    ("düymə", "mətn"): "düymənin yazısı",
}

KATEQORİYA_ADLARI = {
    V.FORM: "Form və düymələr",
    V.GÖSTƏRMƏ: "Göstərmə",
    V.VƏZİYYƏT: "Vəziyyət göstəriciləri",
    V.DÜZÜLÜŞ: "Düzülüş",
    V.NAVİQASİYA: "Naviqasiya",
    V.ÜST_QAT: "Üst qat",
}

BÖLMƏ_NÖMRƏSİ = {k: i for i, k in enumerate(V.KATEQORİYALAR, start=1)}


def parametrlər(vidjet_adı: str) -> list[tuple[str, object]]:
    """`[(ad, standart), ...]` — birinci parametr (`icraçı`) atılır."""
    imza = inspect.signature(getattr(V, vidjet_adı))
    return [(p.name, p.default)
            for p in list(imza.parameters.values())[1:]]


def izah(vidjet_adı: str, parametr: str) -> str | None:
    return XÜSUSİ.get((vidjet_adı, parametr)) or İZAHLAR.get(parametr)


def _standart(d: object) -> str:
    if d is None:
        return "—"
    if d is True:
        return "`doğru`"
    if d is False:
        return "`yanlış`"
    if isinstance(d, str):
        return f'`"{d}"`' if d else '`""`'
    return f"`{d}`"


def _blok(kod: str) -> list[str]:
    return ["```alqor", *kod.split("\n"), "```"]


def arayış() -> str:
    """§ 14.7 — bütün vidjetlərin arayışı (Markdown)."""
    s: list[str] = [BAŞLANĞIC, ""]
    s.append("## 14.7 Vidjet arayışı")
    s.append("")
    s.append(f"Cəmi **{len(V.KATALOQ)} vidjet**, "
             f"{len(V.KATEQORİYALAR)} kateqoriya. Bütün parametrlər "
             "adlıdır və ixtiyaridir.")
    s.append("")
    for k in V.KATEQORİYALAR:
        üzvlər = [m for m in V.KATALOQ if m.kateqoriya == k]
        n = BÖLMƏ_NÖMRƏSİ[k]
        s.append(f"### 14.7.{n} {KATEQORİYA_ADLARI[k]} "
                 f"(`{k}`, {len(üzvlər)})")
        s.append("")
        for m in üzvlər:
            s.append(f"#### `vidjet.{m.ad}` — {m.izah}")
            s.append("")
            s.append("| Parametr | Standart | İzah |")
            s.append("|---|---|---|")
            for ad, d in parametrlər(m.ad):
                s.append(f"| `{ad}` | {_standart(d)} | "
                         f"{izah(m.ad, ad) or ''} |")
            s.append("")
            if m.hadisələr:
                s.append("Hadisələr: " + " · ".join(
                    f"`{h}`" for h in m.hadisələr))
                s.append("")
            s.extend(_blok(m.nümunə.replace("{ad}", _ad(m.ad))))
            s.append("")
            sk = V.skelet(None, m.ad)
            if sk:
                s.append("Kod skeleti (IDE-də iki klik):")
                s.append("")
                s.extend(_blok(sk))
                s.append("")
    s.append(SON)
    return "\n".join(s)


def _ad(vidjet_adı: str) -> str:
    return V._standart_ad(vidjet_adı)


def sənədi_yenilə(yol: Path = SƏNƏD) -> bool:
    """Arayışı sənədə yazır. Dəyişiklik olubsa `True`."""
    mətn = yol.read_text(encoding="utf-8")
    b = mətn.index(BAŞLANĞIC)
    s = mətn.index(SON) + len(SON)
    yeni = mətn[:b] + arayış() + mətn[s:]
    if yeni == mətn:
        return False
    yol.write_text(yeni, encoding="utf-8")
    return True


def sənəddəki_arayış(yol: Path = SƏNƏD) -> str:
    mətn = yol.read_text(encoding="utf-8")
    return mətn[mətn.index(BAŞLANĞIC):mətn.index(SON) + len(SON)]


if __name__ == "__main__":
    if "--yaz" in sys.argv:
        print("yeniləndi" if sənədi_yenilə() else "dəyişiklik yoxdur")
    else:
        print(arayış())
