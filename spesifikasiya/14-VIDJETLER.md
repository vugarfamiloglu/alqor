# Alqor — Bölmə 14: Vidjetlər (`vidjet` modulu)

> Hazır interfeys elementləri: düymə, form sahələri, cədvəl, tərəqqi
> çubuğu, nişanlar, modal və s. **Bir mənbə — iki hədəf:** eyni kod
> həm desktop pəncərəsində (`pəncərə`, § 12), həm də brauzerdə
> (`veb`, § 11) işləyir.
>
> Etalon implementasiya: `alqorc/alqor/vidjet.py`. § 14.7 arayışı
> koddan avtomatik qurulur (`python -m alqor.vidjet_arayis --yaz`).

---

## 14.1 Prinsip

Hər vidjet **funksiyadır** və `Element` (JSX ağacı) qaytarır:

```alqor
gətir vidjet

dəyişən d = vidjet.düymə(mətn: "Yadda saxla", növ: "əsas")
// d — <button class="v-düymə v-düymə--əsas ...">Yadda saxla</button>
```

Vidjet çağırışı JSX ilə eyni yerdə işlənir və onunla qarışdırıla bilər:

```alqor
qaytar <div>
    <h1>Qeydiyyat</h1>
    {vidjet.sahə(etiket: "Ad", ad: "ad")}
</div>
```

Qaydalar:

1. **Bütün parametrlər adlıdır** (`mətn: "…"`) və ixtiyaridir. Ardıcıl
   arqumentlər də qəbul olunur, amma oxunaqlılıq üçün adlı forma
   tövsiyə edilir; `alqorfmt` ona çevirir.
2. **Mətn avtomatik qaçışdan keçir.** `vidjet.mətn(məzmun: "<b>")`
   ekranda `<b>` yazır — HTML kimi şərh olunmur.
3. **Hadisə idarəedicisi funksiyadır** — adətən komponentin metodu
   (`klik: özü.saxla`) və ya lambda (`klik: () => özü.say += 1`).
4. **Növ və ölçü kimi sabit seçimlər yoxlanılır.** `növ: "qırmızı"`
   `ArqumentXətası` (ALQ-R013) atır və icazəli dəyərləri sadalayır.
5. CSS sinifləri `v-` prefikslidir — istifadəçinin öz üslubu ilə
   toqquşmur.

---

## 14.2 Komponentlə istifadə

Vidjetlər adətən `komponent` daxilində işlənir: `vəziyyət` sahəsi
dəyişəndə `göstər()` yenidən çağırılır və ekran yenilənir.

```alqor
gətir vidjet
gətir pəncərə
gətir veb

komponent Qeydiyyat
    vəziyyət ad: mətn = ""
    vəziyyət razıdır: məntiq = yanlış
    vəziyyət göndərildi: məntiq = yanlış

    metod adDəyişdi(dəyər: mətn)
        özü.ad = dəyər
    son

    metod razılıqDəyişdi(dəyər: məntiq)
        özü.razıdır = dəyər
    son

    metod göndər()
        özü.göndərildi = doğru
    son

    göstər()
        əgər özü.göndərildi onda
            qaytar vidjet.xəbərdarlıq(növ: "uğur",
                                      mətn: "Xoş gəldiniz, {özü.ad}!")
        son
        qaytar vidjet.form(başlıq: "Qeydiyyat", məzmun: [
            vidjet.sahə(etiket: "Ad", ad: "ad", dəyər: özü.ad,
                        dəyişdi: özü.adDəyişdi, tələb: doğru),
            vidjet.qeyd(etiket: "Qaydalarla razıyam", ad: "razı",
                        işarələnmiş: özü.razıdır,
                        dəyişdi: özü.razılıqDəyişdi),
            vidjet.düymə(mətn: "Göndər", klik: özü.göndər,
                         söndürülmüş: deyil özü.razıdır)
        ])
    son
son
```

### 14.2.1 Desktop

```alqor
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Qeydiyyat", 420, 360)
    p.məzmun(<Qeydiyyat />)
    p.göstər()
    pəncərə.işlət()
son
```

`pəncərə` vidjet üslubunu hər pəncərəyə özü qoşur.

### 14.2.2 Veb — interaktiv komponent

```alqor
funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.komponent("/", Qeydiyyat, başlıq: "Qeydiyyat")
    s.dinlə(8080)
son
```

`s.komponent(yol, mənbə, başlıq?, üslub?)`:

| Parametr | İzah |
|---|---|
| `yol` | `/` ilə başlamalıdır; bir yola bir komponent |
| `mənbə` | komponent sinfi və ya nümunə qaytaran funksiya: `() => yeni Panel(10)` · `() => <Panel say={10} />` |
| `başlıq` | səhifənin `<title>`-ı |
| `üslub` | əlavə CSS (vidjet üslubundan sonra gəlir) |

Davranış:

* **Hər brauzer sessiyası öz nümunəsini alır.** Sessiya
  `alqor_komponent` kukisi ilə tanınır (`HttpOnly`, `SameSite=Strict`).
  Bir istifadəçinin `vəziyyət` dəyişikliyi digərinə görünmür.
* Sessiyalar yaddaşda saxlanılır: bir qoşma üçün ən çoxu **1000**,
  son fəaliyyətdən **2 saat** sonra atılır. Köhnəlmiş sessiyadan gələn
  hadisəyə server `{"yenidən": doğru}` cavabı verir və brauzer
  səhifəni yenidən yükləyir.
* Ara proqramlar (`s.ara(...)`) komponent səhifəsinə və hadisələrinə
  də tətbiq olunur — giriş yoxlaması komponenti qoruyur.
* Komponent statik fayllardan sonra, marşrutlardan əvvəl yoxlanılır.

### 14.2.3 Veb — statik səhifə

Hadisə lazım deyilsə, vidjet ağacı adi HTML cavabı kimi qaytarıla
bilər. Bu halda idarəedicilər (`klik:` …) **nəzərə alınmır**:

```alqor
s.al("/hesabat", funksiya(sorğu)
    qaytar veb.html(vidjet.səhifə(başlıq: "Hesabat", məzmun: [
        vidjet.başlıq(mətn: "Aylıq hesabat"),
        vidjet.cədvəl(sütunlar: ["Ay", "Gəlir"], sətirlər: verilənlər)
    ]))
son)
```

---

## 14.3 Hadisələr

### 14.3.1 Hadisə adları

Vidjetlər aşağıdakı hadisələri parametr kimi qəbul edir (§ 14.7-də hər
vidjetin öz siyahısı var). JSX elementlərində isə `pəncərə` modulunun
15 hadisəsinin hamısı işlənə bilər (§ 12).

| Hadisə | DOM | İdarəedici nə alır |
|---|---|---|
| `klik` | `click` | düymənin `value`-su varsa onu (nişan, səhifə nömrəsi, sətir indeksi), yoxsa heç nə |
| `dəyişdi` | `change` | sahənin dəyəri: mətn; `qeyd`/`açar` üçün `doğru`/`yanlış` |
| `yazıldı` | `input` | sahənin cari mətni — hər düymə basışında |
| `göndərildi` | `submit` | heç nə |
| `bağlandı` | `click` (✕) | heç nə |
| `sətirKlik` | `click` | sətrin indeksi (0-dan, mətn kimi) |

**Dəyər həmişə mətndir** (`qeyd`/`açar` istisna) — HTML sahəsi mətn
saxlayır. Ədədə çevirmək idarəedicinin işidir:

```alqor
metod səhifəSeçildi(dəyər: mətn)
    özü.səhifə = tamƏt(dəyər, 1)
son
```

İdarəedici parametrsiz də yazıla bilər — dəyər ötürülməsə də çağırılır:
`metod sil()` həm `klik: özü.sil`, həm də dəyərli hadisə ilə işləyir.

### 14.3.2 Yeniləmə semantikası

Hər hadisədən sonra:

1. İdarəedici serverdə (desktopda əsas sapda) icra olunur.
2. Komponentin `göstər()` metodu yenidən çağırılır, hesablanan
   xassələrin keşi təmizlənir.
3. Yeni HTML brauzerə göndərilir və mövcud DOM-a **yamaqla** tətbiq
   olunur — əvəzlənmir:
   * düyünlər yerində qalır, ona görə **fokus, kursor mövqeyi və
     sürüşdürmə** itmir;
   * fokusdakı sahənin dəyərinə toxunulmur — istifadəçi yazmağa davam
     edir;
   * `yığcam`-ın (`<details>`) açıq/qapalı vəziyyəti istifadəçiyə
     məxsusdur.
4. Bir sorğu gedərkən gələn hadisələr **növbəyə** düşür, atılmır.
   Eyni sahənin dəyər hadisələri birləşdirilir və göndərmə anında
   sahənin **son** dəyəri oxunur — sürətlə yazılan mətn tam çatır.

Hadisə açarları (`data-a-klik="n3h2"`) hər göstərmədə yenilənir. Silinmiş
elementdən gələn köhnə açar idarəedici çağırmır — yalnız ekranı yeniləyir.

---

## 14.4 Üslub sistemi

### 14.4.1 Funksiyalar

| Funksiya | Qaytarır | İstifadə |
|---|---|---|
| `vidjet.üslub()` | `mətn` | vidjet CSS-i — öz şablonunuza qoşmaq üçün |
| `vidjet.üslublar()` | `Element` | `<style>` elementi — `<head>` daxilinə |
| `vidjet.səhifə(başlıq?, məzmun?, dil?, əlavəÜslub?)` | `Element` | tam HTML sənədi: `<meta>`, üslub, `<body>` |

Desktopda (`pəncərə`) və `s.komponent(...)`-də üslub avtomatik qoşulur.

### 14.4.2 Tema dəyişənləri

Rənglər CSS dəyişənləri ilə verilir. Qaranlıq rejim əməliyyat sisteminin
ayarına (`prefers-color-scheme`) avtomatik uyğunlaşır.

| Dəyişən | Açıq | Qaranlıq | Məna |
|---|---|---|---|
| `--v-fon` | `#fff` | `#1c1c1f` | səhifə fonu |
| `--v-mətn` | `#17171a` | `#f1f1f4` | əsas mətn |
| `--v-kənar` | `#d7d7db` | `#3a3a40` | çərçivələr |
| `--v-sönük` | `#6c6c75` | `#9a9aa3` | ikinci dərəcəli mətn |
| `--v-vurgu` | `#0b6bcb` | `#4c9ef0` | əsas düymə, keçid, fokus |
| `--v-vurgu-mətn` | `#fff` | `#0b1620` | vurğu fonundakı mətn |
| `--v-üst` | `#f4f4f6` | `#26262b` | panel və ikinci düymə fonu |
| `--v-uğur` | `#167c3c` | `#4ac776` | uğur |
| `--v-xəbərdarlıq` | `#9a6700` | `#e3b341` | xəbərdarlıq |
| `--v-təhlükə` | `#c0392b` | `#ff7b72` | təhlükə, xəta |
| `--v-radius` | `8px` | | künc radiusu |
| `--v-kölgə` | | | kart və modal kölgəsi |

Temanı dəyişmək üçün dəyişənləri yenidən təyin etmək kifayətdir:

```alqor
p.üslub(x":root{--v-vurgu:#7c3aed;--v-radius:4px}")
s.komponent("/", Panel, üslub: x":root{--v-vurgu:#7c3aed}")
```

CSS-də `{…}` olduğu üçün **xam mətn** (`x"…"`) işlənir — adi mətndə
`{…}` interpolyasiyadır.

### 14.4.3 Sinif adları

Hər vidjetin kök sinfi `v-<ad>` formasındadır, variantlar BEM üslubunda:
`v-düymə--əsas`, `v-düymə--kiçik`, `v-giriş--xətalı`. Əlavə sinif
`düymə(əlavəSinif: "...")` ilə verilə bilər. Sinif adları sabit API
sayılır: kiçik versiyalarda dəyişmir.

---

## 14.5 Əlçatanlıq

* Sahələrin etiketi `<label for>` ilə bağlıdır; `tələb: doğru` sahəyə
  `required` verir.
* `tərəqqi`, `halqaTərəqqi` — `role="progressbar"` və `aria-valuenow`.
* `nişanlar` — `role="tablist"` / `role="tab"`; `modal` — `role="dialog"`;
  `xəbərdarlıq` — `role="alert"`; `fırlanan` — `role="status"`.
* `ikonDüymə(başlıq:)` ekran oxuyucusu üçün addır — ikon düymədə
  mütləq verilməlidir.
* `şəkil(alternativ:)` — şəkil yüklənməyəndə və ekran oxuyucusu üçün.

---

## 14.6 IDE kataloqu və kod skeletləri

Alqor Studio-nun element paleti `vidjet` modulunun özündən oxunur.

| Funksiya | Qaytarır |
|---|---|
| `vidjet.kataloq(kateqoriya?)` | `siyahı[lüğət]` — hər vidjet üçün `ad`, `kateqoriya`, `izah`, `nümunə`, `hadisələr`, `skelet`, `vəziyyət` |
| `vidjet.kateqoriyalar()` | `["form", "göstərmə", "vəziyyət", "düzülüş", "naviqasiya", "üst qat"]` |
| `vidjet.nümunə(ad, dəyişənAdı?)` | istifadə nümunəsi (mətn) |
| `vidjet.skelet(ad, dəyişənAdı?)` | elementin işləməsi üçün lazım olan kod (mətn) |

**İki klik qaydası.** Paletdən əlavə edilmiş elementin üzərinə iki dəfə
klikləndikdə Studio `vidjet.skelet(ad, dəyişənAdı)` qaytardığı kodu
komponentin gövdəsinə yazır: `vəziyyət` sahəsi + hadisə idarəedicisi.
Fayl başında `gətir vidjet` yoxdursa, o da əlavə olunur.

```alqor
vidjet.skelet("sahə", "istifadəçiAdı")
```

```alqor
vəziyyət istifadəçiAdı: mətn = ""

metod istifadəçiAdıDəyişdi(dəyər: mətn)
    özü.istifadəçiAdı = dəyər
son
```

Zəmanətlər (sınaqlarla yoxlanılır):

1. Kataloq **tək həqiqət mənbəyidir**: modulun ixrac etdiyi vidjet
   siyahısı, tip imzaları və bu bölmənin arayışı ondan qurulur.
   Kataloqda olub funksiyası olmayan vidjet modul yüklənərkən xəta verir.
2. Hər nümunə və hər skelet **ayrılır və tip yoxlamasından keçir** —
   IDE heç vaxt naməlum tip (ALQ-T002) olan kod yazmır.
3. `dəyişənAdı` verilməyibsə vidjetin adından təhlükəsiz ad düzəlir.

---

<!-- ARAYIŞ BAŞLANĞICI: vidjet_arayis.py yaradır, əl ilə dəyişməyin -->

## 14.7 Vidjet arayışı

Cəmi **57 vidjet**, 6 kateqoriya. Bütün parametrlər adlıdır və ixtiyaridir.

### 14.7.1 Form və düymələr (`form`, 21)

#### `vidjet.düymə` — Basıla bilən düymə

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | düymənin yazısı |
| `klik` | — | basıldıqda çağırılır |
| `növ` | `"əsas"` | `əsas` · `ikinci` · `sakit` · `təhlükə` · `uğur` · `xəbərdarlıq` · `əlaqə` |
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `gözləyir` | `yanlış` | fırlanan göstərir və düyməni söndürür (sorğu gedərkən) |
| `tamEn` | `yanlış` | düymə bütün eni tutur |
| `ikon` | — | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `kimlik` | — | HTML `id` atributu |
| `əlavəSinif` | — | əlavə CSS sinfi |

Hadisələr: `klik`

```alqor
vidjet.düymə(mətn: "Yadda saxla", növ: "əsas",
             klik: özü.düyməBasıldı)
```

Kod skeleti (IDE-də iki klik):

```alqor
metod düyməBasıldı()
    // Düymə basıldıqda bu kod işləyir
son
```

#### `vidjet.ikonDüymə` — Yalnız ikondan ibarət düymə

| Parametr | Standart | İzah |
|---|---|---|
| `ikon` | `""` | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `klik` | — | basıldıqda çağırılır |
| `başlıq` | — | üzərinə gələndə ipucu və ekran oxuyucusu üçün ad — ikon düymədə vacibdir |
| `növ` | `"sakit"` | `düymə` ilə eyni növlər |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `kimlik` | — | HTML `id` atributu |

Hadisələr: `klik`

```alqor
vidjet.ikonDüymə(ikon: "✕", başlıq: "Sil",
                 klik: özü.ikonDüyməBasıldı)
```

Kod skeleti (IDE-də iki klik):

```alqor
metod ikonDüyməBasıldı()
    // …
son
```

#### `vidjet.düyməQrupu` — Yanaşı duran düymələr

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |

```alqor
vidjet.düyməQrupu(məzmun: [
    vidjet.düymə(mətn: "Bəli"),
    vidjet.düymə(mətn: "Xeyr", növ: "ikinci")
])
```

#### `vidjet.əlaqə` — Keçid (link)

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `ünvan` | `"#"` | keçid ünvanı (`href`) |
| `klik` | — | verilibsə keçid əvəzinə idarəedici işləyir |
| `yeniNişan` | `yanlış` | ünvanı yeni nişanda açır |

Hadisələr: `klik`

```alqor
vidjet.əlaqə(mətn: "Ətraflı", ünvan: "/haqqında")
```

#### `vidjet.sahə` — Mətn sahəsi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `yer` | — | boş sahədə görünən ipucu (`placeholder`) |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `yazıldı` | — | hər düymə basışında çağırılır — cari mətni alır |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `oxunaqlı` | `yanlış` | yalnız oxunur, dəyişdirilmir |

Hadisələr: `dəyişdi` · `yazıldı`

```alqor
vidjet.sahə(etiket: "Ad", ad: "sahə",
            dəyər: özü.sahə, dəyişdi: özü.sahəDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət sahə: mətn = ""

metod sahəDəyişdi(dəyər: mətn)
    özü.sahə = dəyər
son
```

#### `vidjet.parol` — Şifrə sahəsi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"şifrə"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `yer` | — | boş sahədə görünən ipucu (`placeholder`) |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.parol(etiket: "Şifrə", ad: "şifrə",
             dəyişdi: özü.şifrəDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət şifrə: mətn = ""

metod şifrəDəyişdi(dəyər: mətn)
    özü.şifrə = dəyər
son
```

#### `vidjet.ədəd` — Ədəd sahəsi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `minimum` | — | ən kiçik dəyər |
| `maksimum` | — | ən böyük dəyər |
| `pillə` | — | bir addımda dəyişmə miqdarı |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — mətn kimi alır (`tamƏt`/`onluqƏt` ilə çevirin) |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.ədəd(etiket: "Yaş", ad: "ədəd", minimum: 0,
            maksimum: 120, dəyişdi: özü.ədədDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət ədəd: tam = 0

metod ədədDəyişdi(dəyər: mətn)
    özü.ədəd = tamƏt(dəyər, 0)
son
```

#### `vidjet.axtarış` — Axtarış sahəsi

| Parametr | Standart | İzah |
|---|---|---|
| `ad` | `"axtarış"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `yer` | `"Axtar…"` | boş sahədə görünən ipucu (`placeholder`) |
| `dəyər` | — | cari dəyər |
| `yazıldı` | — | hər düymə basışında çağırılır — cari mətni alır |
| `göndərildi` | — | form göndəriləndə (Enter) çağırılır |

Hadisələr: `yazıldı` · `göndərildi`

```alqor
vidjet.axtarış(yazıldı: özü.axtar)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət sorğu: mətn = ""

metod axtar(sorğu: mətn)
    özü.sorğu = sorğu
son
```

#### `vidjet.çoxsətirli` — Çoxsətirli mətn sahəsi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `yer` | — | boş sahədə görünən ipucu (`placeholder`) |
| `sətirlər` | `4` | sətir sayı |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.çoxsətirli(etiket: "Qeyd", ad: "çoxsətirli",
                  sətirlər: 5, dəyişdi: özü.çoxsətirliDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət çoxsətirli: mətn = ""

metod çoxsətirliDəyişdi(dəyər: mətn)
    özü.çoxsətirli = dəyər
son
```

#### `vidjet.seçim` — Açılan siyahı

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `seçimlər` | — | `["a", "b"]` · `{"az": "Azərbaycan"}` · `[["az", "Azərbaycan"]]` |
| `dəyər` | — | seçili seçimin dəyəri |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `boşEtiket` | — | siyahının əvvəlində boş dəyərli seçim (məs. `"Seçin…"`) |

Hadisələr: `dəyişdi`

```alqor
vidjet.seçim(etiket: "Şəhər", ad: "seçim",
             seçimlər: ["Bakı", "Gəncə", "Sumqayıt"],
             dəyər: özü.seçim, dəyişdi: özü.seçimDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət seçim: mətn = ""

metod seçimDəyişdi(dəyər: mətn)
    özü.seçim = dəyər
son
```

#### `vidjet.qeyd` — İşarələmə qutusu

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | `""` | qutunun yanındakı mətn |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `işarələnmiş` | `yanlış` | işarəli vəziyyət |
| `dəyişdi` | — | işarələnəndə/götürüləndə çağırılır — `doğru`/`yanlış` alır |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `kömək` | — | sahənin altında kiçik izah mətni |

Hadisələr: `dəyişdi`

```alqor
vidjet.qeyd(etiket: "Qəbul edirəm", ad: "qeyd",
            işarələnmiş: özü.qeyd,
            dəyişdi: özü.qeydDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət qeyd: məntiq = yanlış

metod qeydDəyişdi(_dəyər: istənilən)
    özü.qeyd = deyil özü.qeyd
son
```

#### `vidjet.açar` — Yandır/söndür açarı

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | `""` | açarın yanındakı mətn |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `yanıq` | `yanlış` | açarın yanılı vəziyyəti |
| `dəyişdi` | — | yandırılanda/söndürüləndə çağırılır — `doğru`/`yanlış` alır |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.açar(etiket: "Bildirişlər", ad: "açar",
            yanıq: özü.açar, dəyişdi: özü.açarDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət açar: məntiq = yanlış

metod açarDəyişdi(_dəyər: istənilən)
    özü.açar = deyil özü.açar
son
```

#### `vidjet.radioQrupu` — Bir variantın seçimi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `seçimlər` | — | `["a", "b"]` · `{"az": "Azərbaycan"}` · `[["az", "Azərbaycan"]]` |
| `dəyər` | — | seçili seçimin dəyəri |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `üfüqi` | `yanlış` | seçimləri bir sətirdə düzür |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |

Hadisələr: `dəyişdi`

```alqor
vidjet.radioQrupu(etiket: "Ödəniş", ad: "radioQrupu",
                  seçimlər: ["Nağd", "Kart"],
                  dəyər: özü.radioQrupu,
                  dəyişdi: özü.radioQrupuDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət radioQrupu: mətn = ""

metod radioQrupuDəyişdi(dəyər: mətn)
    özü.radioQrupu = dəyər
son
```

#### `vidjet.sürüşdürücü` — Sürüşdürülən dəyər

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | `0` | cari dəyər |
| `minimum` | `0` | ən kiçik dəyər |
| `maksimum` | `100` | ən böyük dəyər |
| `pillə` | `1` | bir addımda dəyişmə miqdarı |
| `dəyişdi` | — | sürüşdürərkən çağırılır — dəyəri mətn kimi alır |
| `dəyəriGöstər` | `doğru` | sürüşdürücünün yanında cari dəyəri göstərir |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.sürüşdürücü(etiket: "Səs", ad: "sürüşdürücü",
                   dəyər: özü.sürüşdürücü,
                   dəyişdi: özü.sürüşdürücüDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət sürüşdürücü: tam = 50

metod sürüşdürücüDəyişdi(dəyər: mətn)
    özü.sürüşdürücü = tamƏt(dəyər, 0)
son
```

#### `vidjet.tarix` — Tarix seçimi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"tarix"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | `"2026-10-06"` formatında |
| `minimum` | — | ən erkən tarix (`"YYYY-AA-GG"`) |
| `maksimum` | — | ən gec tarix (`"YYYY-AA-GG"`) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.tarix(etiket: "Doğum tarixi", ad: "tarix",
             dəyişdi: özü.tarixDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət tarix: mətn = ""

metod tarixDəyişdi(dəyər: mətn)
    özü.tarix = dəyər
son
```

#### `vidjet.vaxt` — Vaxt seçimi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"vaxt"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | `"14:30"` formatında |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |

Hadisələr: `dəyişdi`

```alqor
vidjet.vaxt(etiket: "Saat", ad: "vaxt")
```

#### `vidjet.rəng` — Rəng seçimi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"rəng"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | `"#3366cc"` | `"#rrggbb"` formatında |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |

Hadisələr: `dəyişdi`

```alqor
vidjet.rəng(etiket: "Rəng", ad: "rəng")
```

#### `vidjet.faylSahəsi` — Fayl yükləmə sahəsi

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"fayl"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `növlər` | — | qəbul edilən fayl növləri: `[".png", "image/*"]` |
| `çoxlu` | `yanlış` | bir neçə fayl seçməyə icazə verir |
| `dəyişdi` | — | fayl seçiləndə çağırılır — faylın adını alır |
| `kömək` | — | sahənin altında kiçik izah mətni |

Hadisələr: `dəyişdi`

```alqor
vidjet.faylSahəsi(etiket: "Şəkil", ad: "faylSahəsi",
                  növlər: ["image/*"])
```

#### `vidjet.form` — Form qabı

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `göndərildi` | — | form göndəriləndə (Enter) çağırılır |
| `başlıq` | — | formun üstündəki başlıq |
| `sıx` | `yanlış` | sahələr arası məsafəni azaldır |

Hadisələr: `göndərildi`

```alqor
vidjet.form(başlıq: "Qeydiyyat",
            göndərildi: özü.göndər, məzmun: [
    vidjet.sahə(etiket: "Ad", ad: "ad"),
    vidjet.düymə(mətn: "Göndər")
])
```

Kod skeleti (IDE-də iki klik):

```alqor
metod göndər()
    // Formun məlumatlarını işlə
son
```

#### `vidjet.sahəDəsti` — Qruplaşdırılmış sahələr

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | qrupun adı (`<legend>`) |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |

```alqor
vidjet.sahəDəsti(başlıq: "Ünvan", məzmun: [
    vidjet.sahə(etiket: "Şəhər", ad: "şəhər")
])
```

#### `vidjet.etiket` — Sahə etiketi

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | etiketin mətni |
| `sahəsi` | — | etiketin bağlandığı sahənin `ad`-ı |

```alqor
vidjet.etiket(mətn: "Ad", sahəsi: "ad")
```

### 14.7.2 Göstərmə (`göstərmə`, 14)

#### `vidjet.başlıq` — Başlıq (h1–h6)

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `səviyyə` | `1` | `1`–`6` (`<h1>`–`<h6>`) |
| `altMətn` | — | başlığın altında sönük izah |

```alqor
vidjet.başlıq(mətn: "Tapşırıqlar", səviyyə: 1,
              altMətn: "Bugünkü işlər")
```

#### `vidjet.mətn` — Abzas

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | `""` | abzas mətni |
| `sönük` | `yanlış` | boz, ikinci dərəcəli mətn |
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |
| `qalın` | `yanlış` | qalın şrift |

```alqor
vidjet.mətn(məzmun: "Salam, dünya!")
```

#### `vidjet.nişan` — Kiçik nişan (badge)

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `növ` | `"ikinci"` | `düymə` ilə eyni növlər |

```alqor
vidjet.nişan(mətn: "Yeni", növ: "uğur")
```

#### `vidjet.xəbərdarlıq` — Bildiriş qutusu

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `növ` | `"xəbərdarlıq"` | `uğur` · `xəbərdarlıq` · `təhlükə` · `məlumat` |
| `başlıq` | — | başlıq mətni |
| `bağlana` | `yanlış` | bağlama düyməsi (✕) göstərir |
| `bağlandı` | — | `bağlana: doğru` olduqda ✕ basılanda çağırılır |

Hadisələr: `bağlandı`

```alqor
vidjet.xəbərdarlıq(mətn: "Yadda saxlanıldı",
                   növ: "uğur")
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət xəbərdarlıqGörünür: məntiq = doğru

metod xəbərdarlığıBağla()
    özü.xəbərdarlıqGörünür = yanlış
son
```

#### `vidjet.kart` — Kart qabı

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altlıq` | — | aşağı hissə — adətən düymələr |
| `altMətn` | — | başlığın altında sönük mətn |
| `klik` | — | verilibsə bütün kart basılandır |

Hadisələr: `klik`

```alqor
vidjet.kart(başlıq: "Hesabat", məzmun: [
    vidjet.mətn(məzmun: "Məzmun")
])
```

#### `vidjet.cədvəl` — Məlumat cədvəli

| Parametr | Standart | İzah |
|---|---|---|
| `sütunlar` | — | başlıqlar: `["Ad", "Yaş"]` və ya `[["ad", "Ad"], …]` (açar → başlıq) |
| `sətirlər` | — | siyahı siyahısı, lüğət siyahısı və ya obyekt siyahısı |
| `boşMətn` | `"Məlumat yoxdur"` | sətir olmayanda göstərilən mətn |
| `zolaqlı` | `doğru` | cüt sətirlərin fonu fərqlənir |
| `çərçivəli` | `yanlış` | bütün xanaların çərçivəsi |
| `sətirKlik` | — | sətir basıldıqda çağırılır — sətrin indeksini (0-dan, mətn kimi) alır |

Hadisələr: `sətirKlik`

```alqor
vidjet.cədvəl(
    sütunlar: [["ad", "Ad"], ["yaş", "Yaş"]],
    sətirlər: özü.cədvəl)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət cədvəl: siyahı[istənilən] = []

metod sətirBasıldı()
    // Sətir seçildi
son
```

#### `vidjet.siyahı` — Sadalama siyahısı

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | mətn və ya element siyahısı |
| `nömrəli` | `yanlış` | nömrəli siyahı (`<ol>`) |
| `işarəsiz` | `yanlış` | siyahı işarələri gizlənir |

```alqor
vidjet.siyahı(elementlər: ["bir", "iki", "üç"])
```

#### `vidjet.təsvirSiyahısı` — Açar–dəyər siyahısı

| Parametr | Standart | İzah |
|---|---|---|
| `cütlər` | — | ad → dəyər lüğəti |

```alqor
vidjet.təsvirSiyahısı(cütlər: {"Ad": "Əli", "Yaş": 30})
```

#### `vidjet.kod` — Kod bloku

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | `""` | kod mətni — HTML qaçışı avtomatikdir |
| `dil` | — | proqramlaşdırma dili (`data-dil` atributu) |

```alqor
vidjet.kod(məzmun: "yaz(\"salam\")", dil: "alqor")
```

#### `vidjet.sitat` — Sitat

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `mənbə` | — | sitatın müəllifi / mənbəyi |

```alqor
vidjet.sitat(mətn: "Bilik gücdür", mənbə: "Atalar sözü")
```

#### `vidjet.şəkil` — Şəkil

| Parametr | Standart | İzah |
|---|---|---|
| `mənbə` | `""` | şəklin ünvanı (URL və ya yol) |
| `alternativ` | `""` | şəkil yüklənməyəndə və ekran oxuyucusu üçün mətn |
| `en` | — | en — ədəd piksel sayılır |
| `hündürlük` | — | hündürlük — ədəd piksel sayılır |
| `yuvarlaq` | `yanlış` | dairəvi kəsim |

```alqor
vidjet.şəkil(mənbə: "/statik/logo.png",
             alternativ: "Loqo", en: 120)
```

#### `vidjet.avatar` — İstifadəçi avatarı

| Parametr | Standart | İzah |
|---|---|---|
| `ad` | `""` | tam ad — şəkil yoxdursa baş hərflər göstərilir (`Aysel Məmmədova` → `AM`) |
| `mənbə` | — | şəkil ünvanı (ixtiyari) |
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |

```alqor
vidjet.avatar(ad: "Aysel Məmmədova")
```

#### `vidjet.ayırıcı` — Ayırıcı xətt

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | — | xəttin ortasında mətn (ixtiyari) |

```alqor
vidjet.ayırıcı(mətn: "və ya")
```

#### `vidjet.boşBaxış` — Boş vəziyyət

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `"Heç nə yoxdur"` | başlıq mətni |
| `mətn` | — | izah mətni |
| `ikon` | `"○"` | böyük simvol |
| `hərəkət` | — | altda göstərilən element — adətən düymə |

```alqor
vidjet.boşBaxış(başlıq: "Tapşırıq yoxdur",
                mətn: "Yeni tapşırıq əlavə edin")
```

### 14.7.3 Vəziyyət göstəriciləri (`vəziyyət`, 5)

#### `vidjet.tərəqqi` — Tərəqqi çubuğu

| Parametr | Standart | İzah |
|---|---|---|
| `dəyər` | `0` | `0`–`maksimum`; həddən kənar dəyər kəsilir |
| `maksimum` | `100` | ən böyük dəyər |
| `etiket` | — | zolağın üstündəki ad |
| `faizGöstər` | `doğru` | faizi rəqəmlə göstərir |
| `növ` | `"əsas"` | dolğunun rəngi — `düymə` ilə eyni növlər |
| `qeyriMüəyyən` | `yanlış` | müddəti bilinməyən iş — hərəkətli zolaq |

```alqor
vidjet.tərəqqi(dəyər: özü.tərəqqi, maksimum: 100,
               etiket: "Yüklənir")
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət tərəqqi: tam = 0
```

#### `vidjet.halqaTərəqqi` — Halqa şəklində tərəqqi

| Parametr | Standart | İzah |
|---|---|---|
| `dəyər` | `0` | `0`–`maksimum` |
| `maksimum` | `100` | ən böyük dəyər |
| `ölçü` | `64` | diametr, piksel |
| `mətn` | — | ortadakı mətn; verilməyibsə faiz |

```alqor
vidjet.halqaTərəqqi(dəyər: özü.halqaTərəqqi, ölçü: 80)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət halqaTərəqqi: tam = 0
```

#### `vidjet.fırlanan` — Gözləmə göstəricisi

| Parametr | Standart | İzah |
|---|---|---|
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |
| `mətn` | — | fırlananın yanındakı mətn |

```alqor
vidjet.fırlanan(mətn: "Yüklənir…")
```

#### `vidjet.skeletYüklənmə` — Yüklənmə skeleti

| Parametr | Standart | İzah |
|---|---|---|
| `sətirlər` | `3` | sətir sayı |
| `en` | — | sətirlərin eni |

```alqor
vidjet.skeletYüklənmə(sətirlər: 3)
```

#### `vidjet.statistika` — Rəqəmli göstərici

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | `""` | rəqəmin üstündəki ad |
| `dəyər` | `""` | əsas rəqəm (mətn kimi göstərilir) |
| `dəyişmə` | — | dəyişmə faizi: müsbət ▲ yaşıl, mənfi ▼ qırmızı |
| `ikon` | — | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |

```alqor
vidjet.statistika(etiket: "Satış", dəyər: "1 240 ₼",
                  dəyişmə: 12)
```

### 14.7.4 Düzülüş (`düzülüş`, 7)

#### `vidjet.qutu` — Sadə qab

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `boşluq` | — | daxili boşluq (`padding`) |
| `kənar` | `yanlış` | çərçivə xətti |
| `fon` | — | fon rəngi (CSS dəyəri) |
| `kimlik` | — | HTML `id` atributu |

```alqor
vidjet.qutu(boşluq: 16, kənar: doğru, məzmun: [])
```

#### `vidjet.sətir` — Üfüqi düzülüş

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `boşluq` | `8` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `düzləndir` | `"başlanğıc"` | üfüqi düzləndirmə: `başlanğıc` · `mərkəz` · `son` · `ara` · `ətraf` · `bərabər` |
| `şaquli` | `"mərkəz"` | şaquli düzləndirmə (`düzləndir` ilə eyni dəyərlər) |
| `sarı` | `doğru` | yer çatmayanda uşaqlar növbəti sətrə keçir |

```alqor
vidjet.sətir(boşluq: 8, düzləndir: "ara", məzmun: [])
```

#### `vidjet.sütun` — Şaquli düzülüş

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `boşluq` | `8` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `düzləndir` | `"dolu"` | uşaqların eni: `dolu` (tam en) · `başlanğıc` · `mərkəz` · `son` |

```alqor
vidjet.sütun(boşluq: 12, məzmun: [])
```

#### `vidjet.tor` — Tor (grid) düzülüşü

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `sütunlar` | `2` | sütun sayı |
| `boşluq` | `12` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `minimum` | — | verilibsə sütun sayı avtomatikdir: hər sütun ən azı bu endədir |

```alqor
vidjet.tor(sütunlar: 3, boşluq: 12, məzmun: [])
```

#### `vidjet.boşluq` — Şaquli boşluq

| Parametr | Standart | İzah |
|---|---|---|
| `hündürlük` | `16` | boş sahənin hündürlüyü |

```alqor
vidjet.boşluq(hündürlük: 24)
```

#### `vidjet.panel` — Başlıqlı panel

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | panelin başlıq zolağı |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `alətlər` | — | başlığın sağında element(lər) — adətən düymələr |

```alqor
vidjet.panel(başlıq: "Ayarlar", məzmun: [])
```

#### `vidjet.bölmə` — Səhifə bölməsi

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | bölmənin başlığı (`<h2>`) |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altMətn` | — | başlığın altında sönük izah |

```alqor
vidjet.bölmə(başlıq: "Haqqında", məzmun: [])
```

### 14.7.5 Naviqasiya (`naviqasiya`, 6)

#### `vidjet.naviqasiya` — Üst naviqasiya sətri

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | sol küncdə tətbiqin adı |
| `elementlər` | — | orta hissədəki element(lər) — adətən `əlaqə` |
| `sağ` | — | sağ küncdəki element(lər) |

```alqor
vidjet.naviqasiya(başlıq: "Tətbiqim", elementlər: [
    vidjet.əlaqə(mətn: "Ana səhifə", ünvan: "/")
])
```

#### `vidjet.nişanlar` — Nişanlar (tabs)

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | nişanlar (`seçimlər` formatında) |
| `cari` | — | seçili nişanın dəyəri; verilməyibsə birincisi |
| `klik` | — | nişan basıldıqda çağırılır — nişanın dəyərini alır |
| `məzmun` | — | nişan sətrinin altındakı gövdə |

Hadisələr: `klik`

```alqor
vidjet.nişanlar(elementlər: ["Ümumi", "Ayarlar"],
                cari: özü.nişanlar, klik: özü.nişanlarSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət nişanlar: mətn = "Ümumi"

metod nişanlarSeçildi(dəyər: mətn)
    özü.nişanlar = dəyər
son
```

#### `vidjet.yığcam` — Açılıb-yığılan bölmə

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `açılmış` | `yanlış` | ilkin vəziyyətdə açıqdır |

```alqor
vidjet.yığcam(başlıq: "Ətraflı", açılmış: yanlış,
              məzmun: [])
```

#### `vidjet.səhifələmə` — Səhifələrə bölmə

| Parametr | Standart | İzah |
|---|---|---|
| `səhifə` | `1` | cari səhifə (1-dən) |
| `cəmi` | `1` | səhifələrin sayı |
| `klik` | — | səhifə basıldıqda çağırılır — səhifə nömrəsini mətn kimi alır |

Hadisələr: `klik`

```alqor
vidjet.səhifələmə(səhifə: özü.səhifələmə, cəmi: 10,
                  klik: özü.səhifələməDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət səhifələmə: tam = 1

metod səhifələməDəyişdi(dəyər: mətn)
    özü.səhifələmə = tamƏt(dəyər, 1)
son
```

#### `vidjet.addımlar` — Addım göstəricisi

| Parametr | Standart | İzah |
|---|---|---|
| `adlar` | — | addımların adları |
| `cari` | `1` | cari addım (1-dən); əvvəlkilər ✓ ilə |

```alqor
vidjet.addımlar(adlar: ["Ad", "Ünvan", "Təsdiq"],
                cari: özü.addımlar)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət addımlar: tam = 1
```

#### `vidjet.çörəkQırıntıları` — Yol göstəricisi

| Parametr | Standart | İzah |
|---|---|---|
| `yollar` | — | `[[ünvan, ad], …]` — sonuncu cari səhifədir |
| `klik` | — | qırıntı basıldıqda çağırılır — ünvanı alır |

Hadisələr: `klik`

```alqor
vidjet.çörəkQırıntıları(yollar: [
    ["/", "Ana səhifə"], ["/mal", "Mallar"]
])
```

### 14.7.6 Üst qat (`üst qat`, 4)

#### `vidjet.modal` — Modal pəncərə

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altlıq` | — | aşağı hissə — adətən düymələr |
| `görünür` | `doğru` | `yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə olunur |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |
| `ölçü` | `"orta"` | pəncərənin eni: `kiçik` · `orta` · `böyük` |

Hadisələr: `bağlandı`

```alqor
vidjet.modal(başlıq: "Təsdiq", görünür: özü.modal,
             bağlandı: özü.modalBağla, məzmun: [])
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət modal: məntiq = yanlış

metod modalBağla()
    özü.modal = yanlış
son
```

#### `vidjet.yanPanel` — Yan panel (drawer)

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `görünür` | `doğru` | `yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə olunur |
| `tərəf` | `"sağ"` | `sol` · `sağ` |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |

Hadisələr: `bağlandı`

```alqor
vidjet.yanPanel(başlıq: "Menyu", görünür: özü.yanPanel,
                bağlandı: özü.yanPanelBağla, məzmun: [])
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət yanPanel: məntiq = yanlış

metod yanPanelBağla()
    özü.yanPanel = yanlış
son
```

#### `vidjet.ipucu` — Üzərinə gələndə görünən izah

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | ipucunun mətni |
| `məzmun` | — | üzərinə gəlinəcək element |
| `tərəf` | `"üst"` | `üst` · `alt` · `sol` · `sağ` |

```alqor
vidjet.ipucu(mətn: "Silinəcək",
             məzmun: vidjet.ikonDüymə(ikon: "✕"))
```

#### `vidjet.bildirişQutusu` — Küncdə görünən bildiriş

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | bildirişin mətni |
| `növ` | `"məlumat"` | `uğur` · `xəbərdarlıq` · `təhlükə` · `məlumat` |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |

Hadisələr: `bağlandı`

```alqor
vidjet.bildirişQutusu(mətn: "Saxlanıldı", növ: "uğur")
```

<!-- ARAYIŞ SONU -->

---

## 14.8 Təhlükəsizlik

| Təhlükə | Qoruma |
|---|---|
| XSS — istifadəçi mətni HTML kimi | bütün mətn və atributlar qaçışdan keçir |
| Başqa saytın hadisə göndərməsi (CSRF) | `Origin` başlığı `Host` ilə eyni olmalıdır; vebdə gövdə `application/json` olmalıdır (kənar sayt CORS ön-yoxlamasına məcbur olur); sessiya kukisi `SameSite=Strict` |
| DNS rebinding (desktop) | yerli server yalnız `Host: 127.0.0.1:<port>` / `localhost:<port>` qəbul edir |
| Başqa istifadəçinin vəziyyəti | sessiya açarı 192 bitlik təsadüfi dəyərdir; nümunələr ayrıdır |
| Yaddaşın doldurulması | qoşma başına 1000 sessiya, 2 saat ömür |

`vidjet.kod`, `vidjet.mətn` və s. **heç vaxt** xam HTML qəbul etmir.
Xam HTML lazımdırsa JSX-də elementlər açıq yazılır.

---

## 14.9 Sınaq

Vidjetli interfeys pəncərə açmadan və port açmadan sınanır:

```alqor
// Desktop
dəyişən s = pəncərə.sınaq.aç(p)
s.yaz("axtarış", "rəşad")           // `ad` və ya etiketlə tapır
s.klik("İşçini sil")                 // düymə mətni ilə
iddia s.ehtiva("Silinsin?")

// Veb
dəyişən m = veb.sınaq.server(server)
dəyişən c = m.al("/")
iddia c.vəziyyət() == 200
```

Sürücü (`pəncərə.sınaq.aç`) metodları: `klik(nişan, dəyər?)`,
`yaz(nişan, dəyər)`, `hadisə(ad, nişan?, dəyər?)`, `ehtiva(parça)`,
`HTML()`, `mətn()`, `başlıq()`, `menyu()`, `dialoqlar()`, `bağla()`.

---

## 14.10 Xəta kodları

| Kod | Nə vaxt |
|---|---|
| ALQ-R013 | icazəsiz `növ` / `ölçü` / `tərəf`; olmayan vidjet adı (`skelet`, `nümunə`); olmayan kateqoriya; təkrarlanan komponent yolu |
| ALQ-T004 | `cütlər` / `sətirlər` lüğət və ya cüt siyahısı deyil |
| ALQ-T008 | hadisə parametrinə funksiya olmayan dəyər verilib |
| ALQ-T053 | komponentdə `göstər()` yoxdur; `s.komponent`-ə komponent olmayan dəyər verilib |
