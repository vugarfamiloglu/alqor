# Alqor Bələdçisi — 8. Vidjet Dərsliyi

> `vidjet` modulu — 57 hazır interfeys elementi: düymə, sahə, cədvəl,
> tərəqqi çubuğu, nişanlar, modal… Hamısı **eyni kodla** desktopda
> (`pəncərə`) və brauzerdə (`veb`) işləyir, açıq və qaranlıq rejimə
> özü uyğunlaşır.
>
> Bütün elementlərin parametrləri: [spesifikasiya § 14.7](../spesifikasiya/14-VIDJETLER.md).
> Canlı nümunə: [`numuneler/08-vidjetler.alq`](../numuneler/08-vidjetler.alq).

---

## 8.1 Vidjet nədir?

Vidjet — `Element` (JSX ağacı) qaytaran funksiyadır. Onu JSX-in
istifadə olunduğu hər yerdə işlətmək olar:

```alqor
// addım 1 — ilk vidjetlər
gətir vidjet
gətir pəncərə

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Vidjetlər", 420, 300)
    p.məzmun(vidjet.sütun(məzmun: [
        vidjet.başlıq(mətn: "Salam!", altMətn: "İlk vidjetlərim"),
        vidjet.xəbərdarlıq(növ: "uğur", mətn: "Hər şey hazırdır"),
        vidjet.düymə(mətn: "Bas mənə", klik: () => yaz("basıldı"))
    ]))
    p.göstər()
    pəncərə.işlət()
son
```

Üç qayda:

1. **Parametrlər adlıdır**: `vidjet.düymə(mətn: "…", növ: "təhlükə")`.
   Sıra əhəmiyyət daşımır, verilməyən parametr standart dəyərini alır.
2. **Sabit seçimlər yoxlanılır.** `növ: "qırmızı"` yazsanız xəta
   mesajı icazəli dəyərləri sadalayır.
3. **Mətn qaçışdan keçir.** `vidjet.mətn(məzmun: "<b>")` ekranda `<b>`
   göstərir — istifadəçi mətni təhlükəsizdir.

---

## 8.2 Kateqoriyalar

| Kateqoriya | Vidjetlər |
|---|---|
| **form** | `düymə` `ikonDüymə` `düyməQrupu` `əlaqə` `sahə` `parol` `ədəd` `axtarış` `çoxsətirli` `seçim` `qeyd` `açar` `radioQrupu` `sürüşdürücü` `tarix` `vaxt` `rəng` `faylSahəsi` `form` `sahəDəsti` `etiket` |
| **göstərmə** | `başlıq` `mətn` `nişan` `xəbərdarlıq` `kart` `cədvəl` `siyahı` `təsvirSiyahısı` `kod` `sitat` `şəkil` `avatar` `ayırıcı` `boşBaxış` |
| **vəziyyət** | `tərəqqi` `halqaTərəqqi` `fırlanan` `skeletYüklənmə` `statistika` |
| **düzülüş** | `qutu` `sətir` `sütun` `tor` `boşluq` `panel` `bölmə` |
| **naviqasiya** | `naviqasiya` `nişanlar` `yığcam` `səhifələmə` `addımlar` `çörəkQırıntıları` |
| **üst qat** | `modal` `yanPanel` `ipucu` `bildirişQutusu` |

Proqramdan da oxumaq olar: `vidjet.kateqoriyalar()`,
`vidjet.kataloq("form")`.

---

## 8.3 Düymələr

```alqor
// parça
vidjet.düyməQrupu(məzmun: [
    vidjet.düymə(mətn: "Yadda saxla", növ: "əsas", klik: özü.saxla),
    vidjet.düymə(mətn: "Ləğv et", növ: "ikinci", klik: özü.ləğvEt)
])
vidjet.düymə(mətn: "Sil", növ: "təhlükə", ikon: "✕", ölçü: "kiçik")
vidjet.düymə(mətn: "Göndərilir…", gözləyir: özü.göndərilir)
vidjet.düymə(mətn: "Bütün en", tamEn: doğru)
vidjet.ikonDüymə(ikon: "⚙", başlıq: "Ayarlar", klik: özü.ayarlar)
vidjet.əlaqə(mətn: "Ətraflı", ünvan: "https://alqor.az", yeniNişan: doğru)
```

| `növ` | Görünüş |
|---|---|
| `əsas` | vurğu rəngi — səhifənin əsas əməliyyatı |
| `ikinci` | boz fon |
| `sakit` | fonsuz |
| `təhlükə` / `uğur` / `xəbərdarlıq` | qırmızı / yaşıl / sarı |
| `əlaqə` | keçid kimi |

`gözləyir: doğru` — düymədə fırlanan göstərilir və düymə söndürülür;
uzun əməliyyat zamanı ikinci klikin qarşısını alır.

---

## 8.4 Form sahələri və hadisələr

Sahənin **dəyəri vəziyyətdən gəlir**, dəyişikliyi isə hadisə ilə
vəziyyətə qayıdır:

```alqor
// addım 2 — qeydiyyat forması
gətir vidjet
gətir pəncərə

komponent Qeydiyyat
    vəziyyət ad: mətn = ""
    vəziyyət yaş: tam = 18
    vəziyyət şəhər: mətn = "Bakı"
    vəziyyət xəbərlər: məntiq = doğru
    vəziyyət nəticə: mətn = ""

    metod adDəyişdi(dəyər: mətn)
        özü.ad = dəyər
    son

    metod yaşDəyişdi(dəyər: mətn)
        // Sahələr həmişə MƏTN göndərir — ədədə çeviririk
        özü.yaş = tamƏt(dəyər, 18)
    son

    metod şəhərDəyişdi(dəyər: mətn)
        özü.şəhər = dəyər
    son

    metod xəbərlərDəyişdi(dəyər: məntiq)
        // Qutucuq və açar isə `doğru` / `yanlış` göndərir
        özü.xəbərlər = dəyər
    son

    metod göndər()
        özü.nəticə = "{özü.ad}, {özü.yaş}, {özü.şəhər}"
    son

    göstər()
        qaytar vidjet.form(başlıq: "Qeydiyyat", göndərildi: özü.göndər,
                           məzmun: [
            vidjet.sahə(etiket: "Ad", ad: "ad", dəyər: özü.ad,
                        tələb: doğru, dəyişdi: özü.adDəyişdi,
                        xəta: əgər özü.ad == "" onda "Ad lazımdır"
                              yoxsa boş son),
            vidjet.ədəd(etiket: "Yaş", ad: "yaş", dəyər: özü.yaş,
                        minimum: 1, maksimum: 120,
                        dəyişdi: özü.yaşDəyişdi),
            vidjet.seçim(etiket: "Şəhər", ad: "şəhər", dəyər: özü.şəhər,
                         seçimlər: ["Bakı", "Gəncə", "Sumqayıt"],
                         dəyişdi: özü.şəhərDəyişdi),
            vidjet.açar(etiket: "Xəbərlər göndərilsin", ad: "xəbərlər",
                        yanıq: özü.xəbərlər,
                        dəyişdi: özü.xəbərlərDəyişdi),
            vidjet.düymə(mətn: "Göndər", klik: özü.göndər,
                         söndürülmüş: özü.ad == ""),
            vidjet.mətn(məzmun: özü.nəticə, sönük: doğru)
        ])
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Qeydiyyat", 420, 560)
    p.məzmun(<Qeydiyyat />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.yaz("ad", "Aysel")
    s.yaz("yaş", "24")
    s.klik("Göndər")
    təmin s.ehtiva("Aysel, 24, Bakı") yoxsa
        yaz("gözlənilməz nəticə")
    son
son
```

| Hadisə | Nə vaxt | Dəyər |
|---|---|---|
| `dəyişdi` | sahədən çıxanda, seçim/qutucuq dəyişəndə | mətn; `qeyd`/`açar` üçün `məntiq` |
| `yazıldı` | **hər hərfdə** | mətn |
| `klik` | basılanda | düymənin dəyəri (nişan adı, səhifə nömrəsi) |
| `göndərildi` | formda Enter | — |

**`dəyişdi` yoxsa `yazıldı`?** Axtarış kimi canlı reaksiya lazımdırsa
`yazıldı`; adi form üçün `dəyişdi` (az sorğu).

`seçimlər` üç formada verilir:

```alqor
// parça
vidjet.seçim(seçimlər: ["Bakı", "Gəncə"])          // dəyər = mətn
vidjet.seçim(seçimlər: {"az": "Azərbaycan", "tr": "Türkiyə"})
vidjet.seçim(seçimlər: [["az", "Azərbaycan"], ["tr", "Türkiyə"]])
```

---

## 8.5 Məlumat göstərmək

```alqor
// parça
vidjet.cədvəl(
    sütunlar: [["ad", "Ad"], ["vəzifə", "Vəzifə"], ["əmək", "Əmək haqqı"]],
    sətirlər: özü.işçilər,           // obyekt, lüğət və ya siyahı siyahısı
    sətirKlik: özü.işçiSeçildi,      // basılan sətrin indeksi (0-dan)
    boşMətn: "Hələ işçi yoxdur")

vidjet.statistika(etiket: "Satış", dəyər: "12 400 ₼", dəyişmə: 8)
vidjet.nişan(mətn: "yeni", növ: "uğur")
vidjet.avatar(ad: "Aysel Məmmədova")         // şəkil yoxdursa: "AM"
vidjet.təsvirSiyahısı(cütlər: {"Plan": "Komanda", "Vəziyyət": "Aktiv"})
vidjet.kod(məzmun: "yaz(\"salam\")", dil: "alqor")
vidjet.boşBaxış(başlıq: "Nəticə yoxdur", mətn: "Süzgəci dəyişin",
                hərəkət: vidjet.düymə(mətn: "Sıfırla", klik: özü.sıfırla))
```

Cədvəlin xanasına vidjet də qoymaq olar — sətirləri siyahı kimi
qurun: `[t.ad, vidjet.nişan(mətn: "aktiv")]`.

---

## 8.6 Gözləmə və tərəqqi

```alqor
// parça
vidjet.tərəqqi(dəyər: özü.yüklənən, maksimum: 100, etiket: "Yüklənir")
vidjet.tərəqqi(qeyriMüəyyən: doğru)              // müddəti bilinmir
vidjet.halqaTərəqqi(dəyər: 72, ölçü: 80)
vidjet.fırlanan(mətn: "Məlumat gətirilir…")
vidjet.skeletYüklənmə(sətirlər: 4)               // yer tutucu
```

---

## 8.7 Düzülüş

| Vidjet | Nə edir |
|---|---|
| `sütun` | uşaqlar alt-alta; standart olaraq tam en tutur |
| `sətir` | uşaqlar yan-yana; yer çatmasa növbəti sətrə keçir |
| `tor` | `sütunlar: 3` sütunlu tor; `minimum: 220` — avtomatik sütun sayı |
| `qutu` | daxili boşluq, çərçivə, fon |
| `panel` | başlıq zolağı + gövdə; `alətlər:` sağ küncdə düymələr |
| `bölmə` | başlıq + mətn bölməsi |
| `boşluq` | şaquli boş yer |

```alqor
// parça
vidjet.sətir(düzləndir: "ara", məzmun: [
    vidjet.başlıq(mətn: "Hesabat", səviyyə: 2),
    vidjet.düymə(mətn: "Yüklə", növ: "ikinci")
])

vidjet.tor(minimum: 220, boşluq: 16, məzmun: [
    vidjet.kart(başlıq: "Gəlir", məzmun: [vidjet.mətn(məzmun: "12 400 ₼")]),
    vidjet.kart(başlıq: "Xərc", məzmun: [vidjet.mətn(məzmun: "8 100 ₼")])
])
```

`düzləndir`: `başlanğıc` · `mərkəz` · `son` · `ara` (kənarlara) ·
`ətraf` · `bərabər` · `dolu`. `boşluq`: ədəd piksel sayılır,
mətn olduğu kimi (`"1.5rem"`).

---

## 8.8 Naviqasiya

```alqor
// addım 3 — nişanlar və səhifələmə
gətir vidjet
gətir pəncərə

komponent Panel
    vəziyyət nişan: mətn = "Ümumi"
    vəziyyət səhifə: tam = 1

    göstər()
        qaytar vidjet.sütun(məzmun: [
            vidjet.naviqasiya(başlıq: "Mənim tətbiqim", sağ: [
                vidjet.avatar(ad: "Aysel Məmmədova", ölçü: "kiçik")]),
            vidjet.nişanlar(elementlər: ["Ümumi", "Hesabatlar"],
                            cari: özü.nişan,
                            klik: (d) => özü.nişan = d),
            vidjet.mətn(məzmun: "Seçilib: {özü.nişan}"),
            vidjet.səhifələmə(səhifə: özü.səhifə, cəmi: 9,
                              klik: (d) => özü.səhifə = tamƏt(d, 1)),
            vidjet.addımlar(adlar: ["Səbət", "Ünvan", "Ödəniş"], cari: 2),
            vidjet.yığcam(başlıq: "Ətraflı", məzmun: [
                vidjet.mətn(məzmun: "Gizli məzmun")])
        ])
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Panel", 640, 480)
    p.məzmun(<Panel />)
    dəyişən s = pəncərə.sınaq.aç(p)
    s.klik("Hesabatlar")
    s.klik("2")
    təmin s.ehtiva("Seçilib: Hesabatlar") yoxsa
        yaz("nişan dəyişmədi")
    son
son
```

Bir idarəedici bir neçə düyməyə bağlıdır (nişanlar, səhifə nömrələri)
— **hansının basıldığı** idarəediciyə dəyər kimi gəlir.

---

## 8.9 Üst qat: modal, yan panel, ipucu

Üst qat vidjetləri `göstər()`-də **həmişə** yazılır, görünməsi isə
vəziyyətlə idarə olunur:

```alqor
// parça
vəziyyət açıqdır: məntiq = yanlış

göstər()
    qaytar vidjet.sütun(məzmun: [
        vidjet.düymə(mətn: "Ayarlar", klik: () => özü.açıqdır = doğru),
        vidjet.yanPanel(başlıq: "Ayarlar", görünür: özü.açıqdır,
                        tərəf: "sağ",
                        bağlandı: () => özü.açıqdır = yanlış,
                        məzmun: [vidjet.açar(etiket: "Qaranlıq rejim")]),
        vidjet.ipucu(mətn: "Fayl 2 MB-dan böyük olmamalıdır",
                     məzmun: vidjet.nişan(mətn: "?"))
    ])
son
```

`bağlandı:` verildikdə küncdə ✕ düyməsi görünür. `modal`-ın `altlıq:`
parametri aşağı düymə sırasıdır — tam nümunə: tapşırıq menecerinin
silmə təsdiqi (bələdçi § 4.7).

---

## 8.10 Üslub və tema

Vidjetlərin rəngləri CSS dəyişənləridir — bir neçə sətirlə bütün
tətbiqin görünüşü dəyişir:

```alqor
// parça — desktop
p.üslub(x"""
:root {
    --v-vurgu: #7c3aed;
    --v-radius: 4px;
}
""")
```

```alqor
// parça — veb
s.komponent("/", Panel, üslub: x":root{--v-vurgu:#7c3aed}")
```

| Dəyişən | Nə idarə edir |
|---|---|
| `--v-vurgu` | əsas düymə, keçid, fokus, seçili nişan |
| `--v-fon` / `--v-mətn` | səhifə fonu / mətn |
| `--v-üst` | panel, ikinci düymə fonu |
| `--v-kənar` | çərçivələr |
| `--v-uğur` / `--v-xəbərdarlıq` / `--v-təhlükə` | vəziyyət rəngləri |
| `--v-radius` | künclərin yuvarlaqlığı |

Qaranlıq rejim əməliyyat sisteminin ayarı ilə avtomatik işləyir.
`x"…"` — xam mətn: CSS-in `{ }` mötərizələri interpolyasiya sayılmasın.

Vebdə statik səhifə (hadisəsiz) lazımdırsa — `vidjet.səhifə(...)`
üslubu daxil olan tam HTML sənədi qaytarır:

```alqor
// parça
s.al("/haqqında", (sorğu) => veb.html(vidjet.səhifə(
    başlıq: "Haqqında",
    məzmun: [vidjet.başlıq(mətn: "Kitab rəfi"),
             vidjet.mətn(məzmun: "Alqor ilə yazılıb.")])))
```

---

## 8.11 Alqor Studio: iki klikdə kod

Studio-nun **Elementlər** panelində 57 vidjetin hamısı var:

* **Bir klik** — vidjet çağırışı kursorun yerinə yazılır.
* **İki klik** (və ya redaktora sürükləmək) — elementin işləməsi üçün
  lazım olan **hər şey** yazılır:
  - faylın başına `gətir vidjet` (yoxdursa),
  - komponentə `vəziyyət` sahəsi,
  - hadisə idarəedicisi (`metod ...Dəyişdi`),
  - `göstər()`-ə vidjet çağırışı.
* Redaktordakı mövcud `vidjet.sahə(...)` çağırışına iki klik — yalnız
  çatışmayanları əlavə edir.

Eyni məlumatı koddan da almaq olar:

```alqor
// addım 4 — kataloq
gətir vidjet

funksiya əsas()
    yaz(vidjet.skelet("sahə", "istifadəçiAdı"))
    yaz(uzunluq(vidjet.kataloq()), "vidjet")
son
```

```
vəziyyət istifadəçiAdı: mətn = ""

metod istifadəçiAdıDəyişdi(dəyər: mətn)
    özü.istifadəçiAdı = dəyər
son
57 vidjet
```

Studio-nu açmaq: Windows-da `Studio-ac.cmd`-ə iki klik, və ya
`python alqorc.py studio <layihə qovluğu>`.

---

## 8.12 Sınaq

Vidjetli interfeysi pəncərə açmadan sınamaq üçün `pəncərə.sınaq.aç`
(desktop) və `veb.sınaq.server` (veb) işlədilir — bax: bələdçi § 4.11
və § 3.10. Sürücü elementləri **görünən mətni**, `ad`-ı, `kimlik`-i
və ya etiketi ilə tapır: `s.klik("Göndər")`, `s.yaz("ad", "Aysel")`,
`s.klik("Süd al")` (cədvəl sətri).

---

## 8.13 Tez-tez rast gəlinən xətalar

| Xəta | Səbəb | Həll |
|---|---|---|
| `` `növ` sahəsi `qırmızı` yoxdur `` | icazəsiz növ | mesaj icazəli dəyərləri sadalayır |
| Sahəyə yazılan geri qayıdır | `dəyər:` verilib, `dəyişdi:` yox | idarəedicidə vəziyyəti yeniləyin |
| Yaş sahəsi `"24"` mətni verir | sahələr mətn göndərir | `tamƏt(dəyər, standart)` |
| Modal bağlanmır | `görünür:` sabit `doğru`-dur | vəziyyətlə idarə edin, `bağlandı:` verin |
| `ALQ-T008 klik atributu funksiya olmalıdır` | `klik: özü.saxla()` — mötərizə ilə çağırılıb | `klik: özü.saxla` |
| Sütundakı element dar qalır | `sütun(düzləndir: "başlanğıc")` | standart `dolu` işlədin |
