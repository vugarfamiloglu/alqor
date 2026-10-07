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

Cəmi **118 vidjet**, 6 kateqoriya. Bütün parametrlər adlıdır və ixtiyaridir.

### 14.7.1 Form və düymələr — Forms (`form`, 40)

#### `vidjet.düymə` — Button

Basıla bilən düymə.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.ikonDüymə` — Icon Button

Yalnız ikondan ibarət düymə.

| Parametr | Standart | İzah |
|---|---|---|
| `ikon` | `""` | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `klik` | — | basıldıqda çağırılır |
| `başlıq` | — | üzərinə gələndə ipucu və ekran oxuyucusu üçün ad — ikon düymədə vacibdir |
| `növ` | `"sakit"` | `düymə` ilə eyni növlər |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `kimlik` | — | HTML `id` atributu |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.düyməQrupu` — Button Group

Yanaşı duran düymələr.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.düyməQrupu(məzmun: [
    vidjet.düymə(mətn: "Bəli"),
    vidjet.düymə(mətn: "Xeyr", növ: "ikinci")
])
```

#### `vidjet.əlaqə` — Link

Keçid (link).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `ünvan` | `"#"` | keçid ünvanı (`href`) |
| `klik` | — | verilibsə keçid əvəzinə idarəedici işləyir |
| `yeniNişan` | `yanlış` | ünvanı yeni nişanda açır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.əlaqə(mətn: "Ətraflı", ünvan: "/haqqında")
```

#### `vidjet.sahə` — Text Field

Mətn sahəsi.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.parol` — Password Field

Şifrə sahəsi.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.ədəd` — Number Field

Ədəd sahəsi.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.axtarış` — Search Field

Axtarış sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `ad` | `"axtarış"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `yer` | `"Axtar…"` | boş sahədə görünən ipucu (`placeholder`) |
| `dəyər` | — | cari dəyər |
| `yazıldı` | — | hər düymə basışında çağırılır — cari mətni alır |
| `göndərildi` | — | form göndəriləndə (Enter) çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.çoxsətirli` — Textarea

Çoxsətirli mətn sahəsi.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.seçim` — Select

Açılan siyahı.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.qeyd` — Checkbox

İşarələmə qutusu.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | `""` | qutunun yanındakı mətn |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `işarələnmiş` | `yanlış` | işarəli vəziyyət |
| `dəyişdi` | — | işarələnəndə/götürüləndə çağırılır — `doğru`/`yanlış` alır |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.açar` — Switch

Yandır/söndür açarı.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | `""` | açarın yanındakı mətn |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `yanıq` | `yanlış` | açarın yanılı vəziyyəti |
| `dəyişdi` | — | yandırılanda/söndürüləndə çağırılır — `doğru`/`yanlış` alır |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.radioQrupu` — Radio Group

Bir variantın seçimi.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.sürüşdürücü` — Slider

Sürüşdürülən dəyər.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.tarix` — Date Picker

Tarix seçimi.

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
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.vaxt` — Time Picker

Vaxt seçimi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"vaxt"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | `"14:30"` formatında |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.vaxt(etiket: "Saat", ad: "vaxt")
```

#### `vidjet.rəng` — Color Picker

Rəng seçimi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"rəng"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | `"#3366cc"` | `"#rrggbb"` formatında |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.rəng(etiket: "Rəng", ad: "rəng")
```

#### `vidjet.faylSahəsi` — File Upload

Fayl yükləmə sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"fayl"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `növlər` | — | qəbul edilən fayl növləri: `[".png", "image/*"]` |
| `çoxlu` | `yanlış` | bir neçə fayl seçməyə icazə verir |
| `dəyişdi` | — | fayl seçiləndə çağırılır — faylın adını alır |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.faylSahəsi(etiket: "Şəkil", ad: "faylSahəsi",
                  növlər: ["image/*"])
```

#### `vidjet.form` — Form

Form qabı.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `göndərildi` | — | form göndəriləndə (Enter) çağırılır |
| `başlıq` | — | formun üstündəki başlıq |
| `sıx` | `yanlış` | sahələr arası məsafəni azaldır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.sahəDəsti` — Fieldset

Qruplaşdırılmış sahələr.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | qrupun adı (`<legend>`) |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.sahəDəsti(başlıq: "Ünvan", məzmun: [
    vidjet.sahə(etiket: "Şəhər", ad: "şəhər")
])
```

#### `vidjet.etiket` — Label

Sahə etiketi.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | etiketin mətni |
| `sahəsi` | — | etiketin bağlandığı sahənin `ad`-ı |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.etiket(mətn: "Ad", sahəsi: "ad")
```

#### `vidjet.reytinq` — Rating

Ulduzla qiymətləndirmə.

| Parametr | Standart | İzah |
|---|---|---|
| `dəyər` | `0` | cari dəyər |
| `maksimum` | `5` | ən böyük dəyər |
| `klik` | — | basıldıqda çağırılır |
| `etiket` | — | sahənin üstündəki görünən ad |
| `söndürülmüş` | `yanlış` | `doğru` olduqda element sönükdür, hadisə getmir |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.reytinq(dəyər: özü.reytinq, klik: özü.reytinqSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət reytinq: tam = 0

metod reytinqSeçildi(dəyər: mətn)
    özü.reytinq = tamƏt(dəyər, 0)
son
```

#### `vidjet.seqmentli` — Segmented Control

Seqmentli seçim (bir neçə düymədən biri).

| Parametr | Standart | İzah |
|---|---|---|
| `seçimlər` | — | `["a", "b"]` · `{"az": "Azərbaycan"}` · `[["az", "Azərbaycan"]]` |
| `dəyər` | — | cari dəyər |
| `klik` | — | basıldıqda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.seqmentli(seçimlər: ["Gün", "Həftə", "Ay"],
                 dəyər: özü.seqmentli, klik: özü.seqmentliSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət seqmentli: mətn = "Gün"

metod seqmentliSeçildi(dəyər: mətn)
    özü.seqmentli = dəyər
son
```

#### `vidjet.çipSeçimi` — Chip Select

Çiplərlə çoxlu seçim.

| Parametr | Standart | İzah |
|---|---|---|
| `seçimlər` | — | `["a", "b"]` · `{"az": "Azərbaycan"}` · `[["az", "Azərbaycan"]]` |
| `seçilənlər` | — | seçilmiş dəyərlərin siyahısı |
| `klik` | — | basıldıqda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.çipSeçimi(seçimlər: ["Alqor", "Python", "Rust"],
                 seçilənlər: özü.çipSeçimi, klik: özü.çipSeçimiDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət çipSeçimi: siyahı[mətn] = []

metod çipSeçimiDəyişdi(dəyər: mətn)
    əgər dəyər içindədir özü.çipSeçimi onda
        özü.çipSeçimi = özü.çipSeçimi.filtr((x) => x != dəyər)
    yoxsa
        özü.çipSeçimi = özü.çipSeçimi + [dəyər]
    son
son
```

#### `vidjet.teqSahəsi` — Tag Input

Teq daxil etmə sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `teqlər` | — | göstərilən teqlərin siyahısı |
| `əlavəEdildi` | — | Enter basıldıqda çağırılır — yeni teqi alır |
| `silindi` | — | ✕ basıldıqda çağırılır — silinən dəyəri alır |
| `yer` | `"Yazın və Enter basın"` | boş sahədə görünən ipucu (`placeholder`) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `əlavəEdildi` · `silindi`

```alqor
vidjet.teqSahəsi(etiket: "Teqlər", teqlər: özü.teqSahəsi,
                 əlavəEdildi: özü.teqSahəsiƏlavə,
                 silindi: özü.teqSahəsiSil)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət teqSahəsi: siyahı[mətn] = []

metod teqSahəsiƏlavə(dəyər: mətn)
    əgər dəyər.kəs() != "" onda
        özü.teqSahəsi = özü.teqSahəsi + [dəyər.kəs()]
    son
son

metod teqSahəsiSil(dəyər: mətn)
    özü.teqSahəsi = özü.teqSahəsi.filtr((x) => x != dəyər)
son
```

#### `vidjet.təsdiqKodu` — OTP Input

Təsdiq kodu (OTP) sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `uzunluq` | `6` | simvol sayı |
| `dəyər` | — | cari dəyər |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.təsdiqKodu(etiket: "SMS kodu", uzunluq: 6,
                  dəyişdi: özü.təsdiqKoduDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət təsdiqKodu: mətn = ""

metod təsdiqKoduDəyişdi(dəyər: mətn)
    özü.təsdiqKodu = dəyər
son
```

#### `vidjet.telefon` — Phone Field

Telefon nömrəsi sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"telefon"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `ölkəKodu` | `"+994"` | nömrənin önündəki ölkə kodu |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.telefon(etiket: "Telefon", dəyişdi: özü.telefonDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət telefon: mətn = ""

metod telefonDəyişdi(dəyər: mətn)
    özü.telefon = dəyər
son
```

#### `vidjet.ePoçt` — Email Field

E-poçt sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"epoçt"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `yer` | `"ad@nümunə.az"` | boş sahədə görünən ipucu (`placeholder`) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `tələb` | `yanlış` | məcburi sahə — etiketin yanında `*` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.ePoçt(etiket: "E-poçt", dəyişdi: özü.ePoçtDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət ePoçt: mətn = ""

metod ePoçtDəyişdi(dəyər: mətn)
    özü.ePoçt = dəyər
son
```

#### `vidjet.keçidSahəsi` — URL Field

URL (veb ünvan) sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"ünvan"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `yer` | `"https://"` | boş sahədə görünən ipucu (`placeholder`) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.keçidSahəsi(etiket: "Sayt", dəyişdi: özü.keçidSahəsiDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət keçidSahəsi: mətn = ""

metod keçidSahəsiDəyişdi(dəyər: mətn)
    özü.keçidSahəsi = dəyər
son
```

#### `vidjet.pulSahəsi` — Currency Field

Məbləğ (valyuta) sahəsi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"məbləğ"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `valyuta` | `"₼"` | sahənin sonundakı valyuta işarəsi |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `kömək` | — | sahənin altında kiçik izah mətni |
| `xəta` | — | doluysa sahə qırmızı çərçivə alır, mətn altda görünür (`kömək`-i əvəzləyir) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.pulSahəsi(etiket: "Məbləğ", valyuta: "₼",
                 dəyişdi: özü.pulSahəsiDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət pulSahəsi: onluq = 0.0

metod pulSahəsiDəyişdi(dəyər: mətn)
    özü.pulSahəsi = onluqƏt(dəyər, 0.0)
son
```

#### `vidjet.tarixAralığı` — Date Range Picker

Tarix aralığı.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `başlanğıc` | — | başlanğıc tarixi (`"2026-10-01"`) |
| `bitmə` | — | son tarix |
| `başlanğıcDəyişdi` | — | başlanğıc tarixi dəyişəndə çağırılır |
| `bitməDəyişdi` | — | son tarix dəyişəndə çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `başlanğıcDəyişdi` · `bitməDəyişdi`

```alqor
vidjet.tarixAralığı(etiket: "Dövr",
                    başlanğıcDəyişdi: özü.tarixAralığıBaşlanğıc,
                    bitməDəyişdi: özü.tarixAralığıBitmə)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət tarixAralığıBaş: mətn = ""
vəziyyət tarixAralığıSon: mətn = ""

metod tarixAralığıBaşlanğıc(dəyər: mətn)
    özü.tarixAralığıBaş = dəyər
son

metod tarixAralığıBitmə(dəyər: mətn)
    özü.tarixAralığıSon = dəyər
son
```

#### `vidjet.tarixVaxt` — Date Time Picker

Tarix və vaxt seçimi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"tarixVaxt"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.tarixVaxt(etiket: "Görüş", dəyişdi: özü.tarixVaxtDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət tarixVaxt: mətn = ""

metod tarixVaxtDəyişdi(dəyər: mətn)
    özü.tarixVaxt = dəyər
son
```

#### `vidjet.ay` — Month Picker

Ay seçimi.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"ay"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `dəyər` | — | cari dəyər |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.ay(etiket: "Ay", dəyişdi: özü.ayDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət ay: mətn = ""

metod ayDəyişdi(dəyər: mətn)
    özü.ay = dəyər
son
```

#### `vidjet.sayğac` — Number Stepper

Artır/azalt sayğacı (stepper).

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `dəyər` | `0` | cari dəyər |
| `minimum` | `0` | ən kiçik dəyər |
| `maksimum` | `99` | ən böyük dəyər |
| `pillə` | `1` | bir addımda dəyişmə miqdarı |
| `klik` | — | basıldıqda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.sayğac(etiket: "Say", dəyər: özü.sayğac,
              klik: özü.sayğacDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət sayğac: tam = 1

metod sayğacDəyişdi(dəyər: mətn)
    özü.sayğac = tamƏt(dəyər, 0)
son
```

#### `vidjet.avtoTamamlama` — Autocomplete

Təklifli sahə (autocomplete).

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"seçim"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `təkliflər` | — | yazarkən təklif olunan dəyərlər |
| `dəyər` | — | cari dəyər |
| `yer` | — | boş sahədə görünən ipucu (`placeholder`) |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `yazıldı` | — | hər düymə basışında çağırılır — cari mətni alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi` · `yazıldı`

```alqor
vidjet.avtoTamamlama(etiket: "Şəhər",
                     təkliflər: ["Bakı", "Gəncə", "Şəki"],
                     dəyişdi: özü.avtoTamamlamaDəyişdi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət avtoTamamlama: mətn = ""

metod avtoTamamlamaDəyişdi(dəyər: mətn)
    özü.avtoTamamlama = dəyər
son
```

#### `vidjet.faylSürüklə` — Dropzone

Fayl sürükləmə sahəsi (dropzone).

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | — | sahənin üstündəki görünən ad |
| `ad` | `"fayl"` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `növlər` | — | qəbul edilən fayl növləri: `[".png", "image/*"]` |
| `çoxlu` | `yanlış` | bir neçə fayl seçməyə icazə verir |
| `dəyişdi` | — | dəyər dəyişəndə çağırılır — yeni dəyəri alır |
| `mətn` | `"Faylı bura sürükləyin və ya seçin"` | görünən mətn |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `dəyişdi`

```alqor
vidjet.faylSürüklə(etiket: "Sənəd yüklə",
                   dəyişdi: özü.faylSürükləSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət faylSürüklə: mətn = ""

metod faylSürükləSeçildi(dəyər: mətn)
    özü.faylSürüklə = dəyər
son
```

#### `vidjet.keçidDüyməsi` — Toggle Button

Basılı qalan düymə (toggle).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `basılı` | `yanlış` | `doğru` — düymə basılı vəziyyətdədir |
| `klik` | — | basıldıqda çağırılır |
| `ikon` | — | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.keçidDüyməsi(mətn: "Qalın", ikon: "B",
                    basılı: özü.keçidDüyməsi, klik: özü.keçidDüyməsiDəyiş)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət keçidDüyməsi: məntiq = yanlış

metod keçidDüyməsiDəyiş()
    özü.keçidDüyməsi = deyil özü.keçidDüyməsi
son
```

#### `vidjet.açılanMenyu` — Dropdown Menu

Açılan menyu (dropdown).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `"Menyu"` | görünən mətn |
| `elementlər` | — | elementlərin siyahısı |
| `klik` | — | basıldıqda çağırılır |
| `növ` | `"ikinci"` | rəng növü |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.açılanMenyu(mətn: "Əməliyyatlar",
                   elementlər: ["Redaktə", "Kopyala", "Sil"],
                   klik: özü.açılanMenyuSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
metod açılanMenyuSeçildi(dəyər: mətn)
    // dəyər — seçilən menyu elementi
son
```

#### `vidjet.bölünmüşDüymə` — Split Button

Bölünmüş düymə (əsas əməl + menyu).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `klik` | — | basıldıqda çağırılır |
| `elementlər` | — | elementlərin siyahısı |
| `seçildi` | — | menyudan seçim edildikdə çağırılır — seçilən dəyəri alır |
| `növ` | `"əsas"` | rəng növü |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik` · `seçildi`

```alqor
vidjet.bölünmüşDüymə(mətn: "Saxla", klik: özü.bölünmüşDüyməSaxla,
                     elementlər: ["Kimi saxla", "Hamısını"],
                     seçildi: özü.bölünmüşDüyməSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
metod bölünmüşDüyməSaxla()
    // əsas əməl
son

metod bölünmüşDüyməSeçildi(dəyər: mətn)
    // menyudan seçim
son
```

#### `vidjet.üzənDüymə` — Floating Action Button

Üzən əməliyyat düyməsi (FAB).

| Parametr | Standart | İzah |
|---|---|---|
| `ikon` | `"+"` | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `başlıq` | `"Əlavə et"` | başlıq mətni |
| `klik` | — | basıldıqda çağırılır |
| `tərəf` | `"sağ"` | hansı tərəfdə |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.üzənDüymə(ikon: "+", başlıq: "Yeni",
                 klik: özü.üzənDüyməBasıldı)
```

Kod skeleti (IDE-də iki klik):

```alqor
metod üzənDüyməBasıldı()
    // …
son
```

### 14.7.2 Göstərmə — Data Display (`göstərmə`, 42)

#### `vidjet.başlıq` — Heading

Başlıq (h1–h6).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `səviyyə` | `1` | `1`–`6` (`<h1>`–`<h6>`) |
| `altMətn` | — | başlığın altında sönük izah |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.başlıq(mətn: "Tapşırıqlar", səviyyə: 1,
              altMətn: "Bugünkü işlər")
```

#### `vidjet.mətn` — Text

Abzas.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | `""` | abzas mətni |
| `sönük` | `yanlış` | boz, ikinci dərəcəli mətn |
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |
| `qalın` | `yanlış` | qalın şrift |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.mətn(məzmun: "Salam, dünya!")
```

#### `vidjet.nişan` — Badge

Kiçik nişan (badge).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `növ` | `"ikinci"` | `düymə` ilə eyni növlər |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.nişan(mətn: "Yeni", növ: "uğur")
```

#### `vidjet.xəbərdarlıq` — Alert

Bildiriş qutusu.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `növ` | `"xəbərdarlıq"` | `uğur` · `xəbərdarlıq` · `təhlükə` · `məlumat` |
| `başlıq` | — | başlıq mətni |
| `bağlana` | `yanlış` | bağlama düyməsi (✕) göstərir |
| `bağlandı` | — | `bağlana: doğru` olduqda ✕ basılanda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.kart` — Card

Kart qabı.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altlıq` | — | aşağı hissə — adətən düymələr |
| `altMətn` | — | başlığın altında sönük mətn |
| `klik` | — | verilibsə bütün kart basılandır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.kart(başlıq: "Hesabat", məzmun: [
    vidjet.mətn(məzmun: "Məzmun")
])
```

#### `vidjet.cədvəl` — Table

Məlumat cədvəli.

| Parametr | Standart | İzah |
|---|---|---|
| `sütunlar` | — | başlıqlar: `["Ad", "Yaş"]` və ya `[["ad", "Ad"], …]` (açar → başlıq) |
| `sətirlər` | — | siyahı siyahısı, lüğət siyahısı və ya obyekt siyahısı |
| `boşMətn` | `"Məlumat yoxdur"` | sətir olmayanda göstərilən mətn |
| `zolaqlı` | `doğru` | cüt sətirlərin fonu fərqlənir |
| `çərçivəli` | `yanlış` | bütün xanaların çərçivəsi |
| `sətirKlik` | — | sətir basıldıqda çağırılır — sətrin indeksini (0-dan, mətn kimi) alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.siyahı` — List

Sadalama siyahısı.

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | mətn və ya element siyahısı |
| `nömrəli` | `yanlış` | nömrəli siyahı (`<ol>`) |
| `işarəsiz` | `yanlış` | siyahı işarələri gizlənir |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.siyahı(elementlər: ["bir", "iki", "üç"])
```

#### `vidjet.təsvirSiyahısı` — Description List

Açar–dəyər siyahısı.

| Parametr | Standart | İzah |
|---|---|---|
| `cütlər` | — | ad → dəyər lüğəti |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.təsvirSiyahısı(cütlər: {"Ad": "Əli", "Yaş": 30})
```

#### `vidjet.kod` — Code Block

Kod bloku.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | `""` | kod mətni — HTML qaçışı avtomatikdir |
| `dil` | — | proqramlaşdırma dili (`data-dil` atributu) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.kod(məzmun: "yaz(\"salam\")", dil: "alqor")
```

#### `vidjet.sitat` — Blockquote

Sitat.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `mənbə` | — | sitatın müəllifi / mənbəyi |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.sitat(mətn: "Bilik gücdür", mənbə: "Atalar sözü")
```

#### `vidjet.şəkil` — Image

Şəkil.

| Parametr | Standart | İzah |
|---|---|---|
| `mənbə` | `""` | şəklin ünvanı (URL və ya yol) |
| `alternativ` | `""` | şəkil yüklənməyəndə və ekran oxuyucusu üçün mətn |
| `en` | — | en — ədəd piksel sayılır |
| `hündürlük` | — | hündürlük — ədəd piksel sayılır |
| `yuvarlaq` | `yanlış` | dairəvi kəsim |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.şəkil(mənbə: "/statik/logo.png",
             alternativ: "Loqo", en: 120)
```

#### `vidjet.avatar` — Avatar

İstifadəçi avatarı.

| Parametr | Standart | İzah |
|---|---|---|
| `ad` | `""` | tam ad — şəkil yoxdursa baş hərflər göstərilir (`Aysel Məmmədova` → `AM`) |
| `mənbə` | — | şəkil ünvanı (ixtiyari) |
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.avatar(ad: "Aysel Məmmədova")
```

#### `vidjet.ayırıcı` — Divider

Ayırıcı xətt.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | — | xəttin ortasında mətn (ixtiyari) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.ayırıcı(mətn: "və ya")
```

#### `vidjet.boşBaxış` — Empty State

Boş vəziyyət.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `"Heç nə yoxdur"` | başlıq mətni |
| `mətn` | — | izah mətni |
| `ikon` | `"○"` | böyük simvol |
| `hərəkət` | — | altda göstərilən element — adətən düymə |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.boşBaxış(başlıq: "Tapşırıq yoxdur",
                mətn: "Yeni tapşırıq əlavə edin")
```

#### `vidjet.çip` — Chip

Çip (silinə bilən teq).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `növ` | `"ikinci"` | rəng növü |
| `silindi` | — | ✕ basıldıqda çağırılır — silinən dəyəri alır |
| `ikon` | — | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `silindi`

```alqor
vidjet.çip(mətn: "Alqor", növ: "əsas")
```

#### `vidjet.ikon` — Icon

İkon (simvol).

| Parametr | Standart | İzah |
|---|---|---|
| `simvol` | `"★"` | göstərilən simvol və ya emoji |
| `ölçü` | `20` | `kiçik` · `orta` · `böyük` |
| `başlıq` | — | başlıq mətni |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.ikon(simvol: "⚙", ölçü: 24, başlıq: "Ayarlar")
```

#### `vidjet.klaviş` — Kbd

Klaviatura düyməsi.

| Parametr | Standart | İzah |
|---|---|---|
| `düymələr` | — | düymə adları, məs. `["Ctrl", "S"]` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.klaviş(düymələr: ["Ctrl", "S"])
```

#### `vidjet.vaxtXətti` — Timeline

Vaxt xətti (timeline).

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | elementlərin siyahısı |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.vaxtXətti(elementlər: [
    ["2024", "Başlanğıc", "Layihə yaradıldı"],
    ["2026", "1.0", "İlk buraxılış"]
])
```

#### `vidjet.ağac` — Tree View

Ağac görünüşü (fayl ağacı).

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | elementlərin siyahısı |
| `açılmış` | `doğru` | ilkin vəziyyətdə açıqdır |
| `klik` | — | basıldıqda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.ağac(elementlər: [
    ["mənbə", ["əsas.alq", "model.alq"]],
    "README.md"
], klik: özü.ağacSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət ağac: mətn = ""

metod ağacSeçildi(dəyər: mətn)
    özü.ağac = dəyər
son
```

#### `vidjet.siyahıQrupu` — List Group

Klikləyən sətirli siyahı.

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | elementlərin siyahısı |
| `klik` | — | basıldıqda çağırılır |
| `seçili` | — | seçilmiş elementin dəyəri |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.siyahıQrupu(elementlər: [
    ["Profil", "Ad, şəkil"], ["Təhlükəsizlik", "Şifrə"]
], seçili: özü.siyahıQrupu, klik: özü.siyahıQrupuSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət siyahıQrupu: mətn = ""

metod siyahıQrupuSeçildi(dəyər: mətn)
    özü.siyahıQrupu = dəyər
son
```

#### `vidjet.avatarQrupu` — Avatar Group

Avatar qrupu.

| Parametr | Standart | İzah |
|---|---|---|
| `adlar` | — | addımların adları |
| `maksimum` | `4` | ən böyük dəyər |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.avatarQrupu(adlar: ["Aysel Əliyeva", "Kamran Rəhimov",
                           "Nərmin Həsənova"])
```

#### `vidjet.göstərici` — Meter

Ölçü göstəricisi (meter).

| Parametr | Standart | İzah |
|---|---|---|
| `dəyər` | `0` | cari dəyər |
| `minimum` | `0` | ən kiçik dəyər |
| `maksimum` | `100` | ən böyük dəyər |
| `etiket` | — | sahənin üstündəki görünən ad |
| `aşağı` | — | bu dəyərdən aşağı — sarı |
| `yuxarı` | — | bu dəyərdən yuxarı — xəbərdarlıq rəngi |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.göstərici(etiket: "Disk", dəyər: 72, yuxarı: 80)
```

#### `vidjet.qiymətKartı` — Pricing Card

Qiymət planı kartı.

| Parametr | Standart | İzah |
|---|---|---|
| `plan` | `"Əsas"` | planın adı |
| `qiymət` | `"0 ₼"` | qiymət mətni, məs. `"19 ₼"` |
| `dövr` | `"/ ay"` | qiymətin dövrü, məs. `"/ ay"` |
| `xüsusiyyətlər` | — | planın xüsusiyyətləri (siyahı) |
| `düyməMətni` | `"Seç"` | düymənin yazısı |
| `klik` | — | basıldıqda çağırılır |
| `seçilmiş` | `yanlış` | `doğru` — vurğulanmış (tövsiyə olunan) kart |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.qiymətKartı(plan: "Pro", qiymət: "19 ₼",
                   xüsusiyyətlər: ["10 layihə", "Dəstək"],
                   klik: özü.qiymətKartıSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
metod qiymətKartıSeçildi(dəyər: mətn)
    // dəyər — plan adı
son
```

#### `vidjet.xüsusiyyətSiyahısı` — Feature List

İşarəli xüsusiyyət siyahısı.

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | elementlərin siyahısı |
| `işarə` | `"✓"` | hər sətrin önündəki işarə |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.xüsusiyyətSiyahısı(elementlər: ["Sürətli", "Pulsuz"])
```

#### `vidjet.rəy` — Testimonial

Müştəri rəyi (testimonial).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `vəzifə` | — | adın altında sönük mətn (vəzifə, rol) |
| `reytinqi` | — | ulduz sayı (0–5) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.rəy(mətn: "Çox rahatdır!", ad: "Aysel Əliyeva",
           vəzifə: "Dizayner", reytinqi: 5)
```

#### `vidjet.qəhrəman` — Hero

Böyük giriş bölməsi (hero).

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `altMətn` | — | başlığın altında sönük izah |
| `hərəkətlər` | — | düymə(lər) — tək element və ya siyahı |
| `mərkəzdə` | `doğru` | mətn ortaya düzlənsin |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.qəhrəman(başlıq: "Alqor ilə proqramlaşdır",
                altMətn: "Azərbaycan dilində",
                hərəkətlər: [vidjet.düymə(mətn: "Başla")])
```

#### `vidjet.səhifəAltlığı` — Footer

Səhifə altlığı (footer).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `keçidlər` | — | `[[ünvan, mətn], …]` cütləri |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.səhifəAltlığı(mətn: "© 2026 Alqor",
                     keçidlər: [["/haqqında", "Haqqında"]])
```

#### `vidjet.qeydQutusu` — Callout

Diqqət çəkən qeyd (callout).

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | başlıq mətni |
| `mətn` | `""` | görünən mətn |
| `növ` | `"məlumat"` | rəng növü |
| `ikon` | — | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.qeydQutusu(başlıq: "Məsləhət",
                  mətn: "Ctrl+S ilə saxlayın")
```

#### `vidjet.elanZolağı` — Banner

Səhifə üstü elan zolağı (banner).

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `növ` | `"məlumat"` | rəng növü |
| `hərəkət` | — | altda göstərilən element — adətən düymə |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `bağlandı`

```alqor
vidjet.elanZolağı(mətn: "Yeni versiya çıxıb!",
                  növ: "məlumat")
```

#### `vidjet.təqvim` — Calendar

Aylıq təqvim.

| Parametr | Standart | İzah |
|---|---|---|
| `il` | `2026` | il |
| `ayı` | `1` | ay nömrəsi (1–12) |
| `seçili` | — | seçilmiş elementin dəyəri |
| `klik` | — | basıldıqda çağırılır |
| `qeydlilər` | — | nöqtə ilə işarələnən tarixlər |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.təqvim(il: 2026, ayı: 10, seçili: özü.təqvim,
              klik: özü.təqvimSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət təqvim: mətn = ""

metod təqvimSeçildi(dəyər: mətn)
    // gün: "2026-10-07"; ay keçidi: "2026-11"
    özü.təqvim = dəyər
son
```

#### `vidjet.sütunQrafiki` — Bar Chart

Sütun qrafiki (bar chart).

| Parametr | Standart | İzah |
|---|---|---|
| `dəyərlər` | — | ədədlər siyahısı |
| `etiketlər` | — | hər dəyərin adı (dəyərlərlə eyni sırada) |
| `başlıq` | — | başlıq mətni |
| `hündürlük` | `160` | hündürlük — ədəd piksel sayılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.sütunQrafiki(başlıq: "Satış",
                    dəyərlər: [12, 19, 7, 15],
                    etiketlər: ["Y", "F", "M", "A"])
```

#### `vidjet.xəttQrafiki` — Line Chart

Xətt qrafiki (line chart).

| Parametr | Standart | İzah |
|---|---|---|
| `dəyərlər` | — | ədədlər siyahısı |
| `etiketlər` | — | hər dəyərin adı (dəyərlərlə eyni sırada) |
| `başlıq` | — | başlıq mətni |
| `hündürlük` | `160` | hündürlük — ədəd piksel sayılır |
| `sahəli` | `doğru` | xəttin altı rənglə dolsun |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.xəttQrafiki(başlıq: "Ziyarət",
                   dəyərlər: [3, 8, 5, 12, 9],
                   etiketlər: ["B.e", "Ç.a", "Ç", "C.a", "C"])
```

#### `vidjet.dairəQrafiki` — Pie Chart

Dairə qrafiki (pie / donut).

| Parametr | Standart | İzah |
|---|---|---|
| `dəyərlər` | — | ədədlər siyahısı |
| `etiketlər` | — | hər dəyərin adı (dəyərlərlə eyni sırada) |
| `başlıq` | — | başlıq mətni |
| `halqa` | `doğru` | `doğru` — ortası boş (donut) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.dairəQrafiki(dəyərlər: [50, 30, 20],
                    etiketlər: ["Veb", "Mobil", "Desktop"])
```

#### `vidjet.kiçikQrafik` — Sparkline

Kiçik xətt qrafiki (sparkline).

| Parametr | Standart | İzah |
|---|---|---|
| `dəyərlər` | — | ədədlər siyahısı |
| `en` | `100` | en — ədəd piksel sayılır |
| `hündürlük` | `28` | hündürlük — ədəd piksel sayılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.kiçikQrafik(dəyərlər: [3, 5, 4, 8, 6, 9])
```

#### `vidjet.video` — Video

Video oynadıcı.

| Parametr | Standart | İzah |
|---|---|---|
| `mənbə` | `""` | şəklin ünvanı (URL və ya yol) |
| `poster` | — | video başlamazdan əvvəl görünən şəkil |
| `idarəetmə` | `doğru` | oynat/dayandır idarələri görünsün |
| `avtomatik` | `yanlış` | səhifə açılanda özü oynasın (səssiz) |
| `səssiz` | `yanlış` | səs bağlı başlasın |
| `təkrar` | `yanlış` | bitəndə yenidən başlasın |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.video(mənbə: "/media/təqdimat.mp4")
```

#### `vidjet.audio` — Audio

Audio oynadıcı.

| Parametr | Standart | İzah |
|---|---|---|
| `mənbə` | `""` | şəklin ünvanı (URL və ya yol) |
| `idarəetmə` | `doğru` | oynat/dayandır idarələri görünsün |
| `təkrar` | `yanlış` | bitəndə yenidən başlasın |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.audio(mənbə: "/media/mahnı.mp3")
```

#### `vidjet.yerləşdirmə` — Embed

Xarici məzmun (embed, iframe).

| Parametr | Standart | İzah |
|---|---|---|
| `ünvan` | `""` | keçid ünvanı (`href`) |
| `başlıq` | `"Yerləşdirilmiş məzmun"` | başlıq mətni |
| `hündürlük` | `315` | hündürlük — ədəd piksel sayılır |
| `nisbət` | — | en/hündürlük nisbəti — `"16/9"`, `"1:2"` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.yerləşdirmə(ünvan: "https://www.openstreetmap.org/export/embed.html", nisbət: "16/9")
```

#### `vidjet.qalereya` — Image Gallery

Şəkil qalereyası.

| Parametr | Standart | İzah |
|---|---|---|
| `şəkillər` | — | şəkil ünvanları və ya `[ünvan, izah]` cütləri |
| `sütunlar` | `3` | sütun sayı |
| `klik` | — | basıldıqda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.qalereya(şəkillər: ["/şəkil/1.jpg", "/şəkil/2.jpg",
                           "/şəkil/3.jpg"], sütunlar: 3)
```

#### `vidjet.karusel` — Carousel

Slayd göstəricisi (carousel).

| Parametr | Standart | İzah |
|---|---|---|
| `slaydlar` | — | şəkil ünvanı, `[ünvan, başlıq]` və ya element |
| `cari` | `0` | seçili element |
| `klik` | — | basıldıqda çağırılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.karusel(slaydlar: [["/şəkil/1.jpg", "Bakı"],
                          ["/şəkil/2.jpg", "Şəki"]],
               cari: özü.karusel, klik: özü.karuselKeç)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət karusel: tam = 0

metod karuselKeç(dəyər: mətn)
    özü.karusel = tamƏt(dəyər, 0)
son
```

#### `vidjet.işarəliMətn` — Markdown

Markdown işarələməli mətn.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | görünən mətn |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.işarəliMətn(mətn: "## Başlıq\n\n**Qalın** mətn")
```

#### `vidjet.profilKartı` — Profile Card

Profil kartı.

| Parametr | Standart | İzah |
|---|---|---|
| `ad` | `""` | sahənin adı (`name`/`id`); sınaq sürücüsü də bununla tapır |
| `vəzifə` | — | adın altında sönük mətn (vəzifə, rol) |
| `mənbə` | — | şəklin ünvanı (URL və ya yol) |
| `hərəkətlər` | — | düymə(lər) — tək element və ya siyahı |
| `statistika` | — | `{"Layihə": 12}` — ad → rəqəm |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.profilKartı(ad: "Aysel Əliyeva", vəzifə: "Proqramçı",
                   statistika: {"Layihə": 12, "İzləyici": 340})
```

#### `vidjet.bildirişNişanı` — Notification Badge

Saylı bildiriş ikonu.

| Parametr | Standart | İzah |
|---|---|---|
| `ikon` | `"🔔"` | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `say` | `0` | nişandakı rəqəm; 0 olduqda gizlənir |
| `klik` | — | basıldıqda çağırılır |
| `maksimum` | `99` | ən böyük dəyər |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.bildirişNişanı(say: özü.bildirişNişanı, klik: özü.bildirişNişanıAç)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət bildirişNişanı: tam = 3

metod bildirişNişanıAç()
    özü.bildirişNişanı = 0
son
```

### 14.7.3 Vəziyyət göstəriciləri — Feedback (`vəziyyət`, 8)

#### `vidjet.tərəqqi` — Progress Bar

Tərəqqi çubuğu.

| Parametr | Standart | İzah |
|---|---|---|
| `dəyər` | `0` | `0`–`maksimum`; həddən kənar dəyər kəsilir |
| `maksimum` | `100` | ən böyük dəyər |
| `etiket` | — | zolağın üstündəki ad |
| `faizGöstər` | `doğru` | faizi rəqəmlə göstərir |
| `növ` | `"əsas"` | dolğunun rəngi — `düymə` ilə eyni növlər |
| `qeyriMüəyyən` | `yanlış` | müddəti bilinməyən iş — hərəkətli zolaq |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.tərəqqi(dəyər: özü.tərəqqi, maksimum: 100,
               etiket: "Yüklənir")
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət tərəqqi: tam = 0
```

#### `vidjet.halqaTərəqqi` — Circular Progress

Halqa şəklində tərəqqi.

| Parametr | Standart | İzah |
|---|---|---|
| `dəyər` | `0` | `0`–`maksimum` |
| `maksimum` | `100` | ən böyük dəyər |
| `ölçü` | `64` | diametr, piksel |
| `mətn` | — | ortadakı mətn; verilməyibsə faiz |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.halqaTərəqqi(dəyər: özü.halqaTərəqqi, ölçü: 80)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət halqaTərəqqi: tam = 0
```

#### `vidjet.fırlanan` — Spinner

Gözləmə göstəricisi.

| Parametr | Standart | İzah |
|---|---|---|
| `ölçü` | `"orta"` | `kiçik` · `orta` · `böyük` |
| `mətn` | — | fırlananın yanındakı mətn |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.fırlanan(mətn: "Yüklənir…")
```

#### `vidjet.skeletYüklənmə` — Skeleton

Yüklənmə skeleti.

| Parametr | Standart | İzah |
|---|---|---|
| `sətirlər` | `3` | sətir sayı |
| `en` | — | sətirlərin eni |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.skeletYüklənmə(sətirlər: 3)
```

#### `vidjet.statistika` — Stat

Rəqəmli göstərici.

| Parametr | Standart | İzah |
|---|---|---|
| `etiket` | `""` | rəqəmin üstündəki ad |
| `dəyər` | `""` | əsas rəqəm (mətn kimi göstərilir) |
| `dəyişmə` | — | dəyişmə faizi: müsbət ▲ yaşıl, mənfi ▼ qırmızı |
| `ikon` | — | ikon kimi işlənən simvol (məs. `"✕"`, `"⚙"`) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.statistika(etiket: "Satış", dəyər: "1 240 ₼",
                  dəyişmə: 12)
```

#### `vidjet.yüklənməÖrtüyü` — Loading Overlay

Məzmunun üstündə yüklənmə.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `yüklənir` | `doğru` | `doğru` — örtük və fırlanan görünür |
| `mətn` | `"Yüklənir…"` | görünən mətn |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.yüklənməÖrtüyü(yüklənir: özü.yüklənməÖrtüyü, məzmun: [])
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət yüklənməÖrtüyü: məntiq = doğru
```

#### `vidjet.nəticə` — Result

Nəticə səhifəsi (uğur, xəta, 404).

| Parametr | Standart | İzah |
|---|---|---|
| `növ` | `"uğur"` | rəng növü |
| `başlıq` | `""` | başlıq mətni |
| `mətn` | — | görünən mətn |
| `hərəkətlər` | — | düymə(lər) — tək element və ya siyahı |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.nəticə(növ: "uğur", başlıq: "Sifariş qəbul olundu",
              mətn: "Təşəkkür edirik!")
```

#### `vidjet.şifrəGücü` — Password Strength

Şifrənin gücü göstəricisi.

| Parametr | Standart | İzah |
|---|---|---|
| `şifrə` | `""` | yoxlanılan şifrə |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.şifrəGücü(şifrə: özü.şifrəGücü)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət şifrəGücü: mətn = ""
```

### 14.7.4 Düzülüş — Layout (`düzülüş`, 13)

#### `vidjet.qutu` — Box

Sadə qab.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `boşluq` | — | daxili boşluq (`padding`) |
| `kənar` | `yanlış` | çərçivə xətti |
| `fon` | — | fon rəngi (CSS dəyəri) |
| `kimlik` | — | HTML `id` atributu |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.qutu(boşluq: 16, kənar: doğru, məzmun: [])
```

#### `vidjet.sətir` — Row

Üfüqi düzülüş.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `boşluq` | `8` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `düzləndir` | `"başlanğıc"` | üfüqi düzləndirmə: `başlanğıc` · `mərkəz` · `son` · `ara` · `ətraf` · `bərabər` |
| `şaquli` | `"mərkəz"` | şaquli düzləndirmə (`düzləndir` ilə eyni dəyərlər) |
| `sarı` | `doğru` | yer çatmayanda uşaqlar növbəti sətrə keçir |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.sətir(boşluq: 8, düzləndir: "ara", məzmun: [])
```

#### `vidjet.sütun` — Column

Şaquli düzülüş.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `boşluq` | `8` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `düzləndir` | `"dolu"` | uşaqların eni: `dolu` (tam en) · `başlanğıc` · `mərkəz` · `son` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.sütun(boşluq: 12, məzmun: [])
```

#### `vidjet.tor` — Grid

Tor (grid) düzülüşü.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `sütunlar` | `2` | sütun sayı |
| `boşluq` | `12` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `minimum` | — | verilibsə sütun sayı avtomatikdir: hər sütun ən azı bu endədir |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.tor(sütunlar: 3, boşluq: 12, məzmun: [])
```

#### `vidjet.boşluq` — Spacer

Şaquli boşluq.

| Parametr | Standart | İzah |
|---|---|---|
| `hündürlük` | `16` | boş sahənin hündürlüyü |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.boşluq(hündürlük: 24)
```

#### `vidjet.panel` — Panel

Başlıqlı panel.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | panelin başlıq zolağı |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `alətlər` | — | başlığın sağında element(lər) — adətən düymələr |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.panel(başlıq: "Ayarlar", məzmun: [])
```

#### `vidjet.bölmə` — Section

Səhifə bölməsi.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | bölmənin başlığı (`<h2>`) |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altMətn` | — | başlığın altında sönük izah |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.bölmə(başlıq: "Haqqında", məzmun: [])
```

#### `vidjet.konteyner` — Container

Mərkəzlənmiş en məhdud qab.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `en` | `1100` | en — ədəd piksel sayılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.konteyner(en: 960, məzmun: [])
```

#### `vidjet.mərkəz` — Center

Məzmunu ortaya qoyur.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `hündürlük` | — | hündürlük — ədəd piksel sayılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.mərkəz(hündürlük: 200, məzmun: [])
```

#### `vidjet.ikiSütun` — Split Layout

İki sütunlu düzülüş (split).

| Parametr | Standart | İzah |
|---|---|---|
| `sol` | — | sol sütunun məzmunu |
| `sağ` | — | sağ küncdəki element(lər) |
| `nisbət` | `"1:1"` | en/hündürlük nisbəti — `"16/9"`, `"1:2"` |
| `boşluq` | `16` | uşaqlar arası məsafə — ədəd piksel sayılır, mətn olduğu kimi (`"1rem"`) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.ikiSütun(nisbət: "1:2", sol: [], sağ: [])
```

#### `vidjet.nisbət` — Aspect Ratio

Sabit en/hündürlük nisbəti.

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `forma` | `"16/9"` | en/hündürlük nisbəti, məs. `"16/9"`, `"1/1"` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.nisbət(forma: "16/9", məzmun: [])
```

#### `vidjet.sürüşmə` — Scroll Area

Sürüşən sahə (scroll area).

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `hündürlük` | `240` | hündürlük — ədəd piksel sayılır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.sürüşmə(hündürlük: 240, məzmun: [])
```

#### `vidjet.tətbiqQabığı` — App Shell

Tətbiq skeleti: başlıq, yan, məzmun.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | — | başlıq mətni |
| `yan` | — | yan panelin məzmunu |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altlıq` | — | aşağı hissə — adətən düymələr |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.tətbiqQabığı(başlıq: vidjet.başlıq(mətn: "Tətbiq"),
                    yan: [], məzmun: [])
```

### 14.7.5 Naviqasiya — Navigation (`naviqasiya`, 8)

#### `vidjet.naviqasiya` — Navbar

Üst naviqasiya sətri.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | sol küncdə tətbiqin adı |
| `elementlər` | — | orta hissədəki element(lər) — adətən `əlaqə` |
| `sağ` | — | sağ küncdəki element(lər) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.naviqasiya(başlıq: "Tətbiqim", elementlər: [
    vidjet.əlaqə(mətn: "Ana səhifə", ünvan: "/")
])
```

#### `vidjet.nişanlar` — Tabs

Nişanlar (tabs).

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | nişanlar (`seçimlər` formatında) |
| `cari` | — | seçili nişanın dəyəri; verilməyibsə birincisi |
| `klik` | — | nişan basıldıqda çağırılır — nişanın dəyərini alır |
| `məzmun` | — | nişan sətrinin altındakı gövdə |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.yığcam` — Accordion

Açılıb-yığılan bölmə.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `açılmış` | `yanlış` | ilkin vəziyyətdə açıqdır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.yığcam(başlıq: "Ətraflı", açılmış: yanlış,
              məzmun: [])
```

#### `vidjet.səhifələmə` — Pagination

Səhifələrə bölmə.

| Parametr | Standart | İzah |
|---|---|---|
| `səhifə` | `1` | cari səhifə (1-dən) |
| `cəmi` | `1` | səhifələrin sayı |
| `klik` | — | səhifə basıldıqda çağırılır — səhifə nömrəsini mətn kimi alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.addımlar` — Stepper

Addım göstəricisi.

| Parametr | Standart | İzah |
|---|---|---|
| `adlar` | — | addımların adları |
| `cari` | `1` | cari addım (1-dən); əvvəlkilər ✓ ilə |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.addımlar(adlar: ["Ad", "Ünvan", "Təsdiq"],
                cari: özü.addımlar)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət addımlar: tam = 1
```

#### `vidjet.çörəkQırıntıları` — Breadcrumb

Yol göstəricisi.

| Parametr | Standart | İzah |
|---|---|---|
| `yollar` | — | `[[ünvan, ad], …]` — sonuncu cari səhifədir |
| `klik` | — | qırıntı basıldıqda çağırılır — ünvanı alır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.çörəkQırıntıları(yollar: [
    ["/", "Ana səhifə"], ["/mal", "Mallar"]
])
```

#### `vidjet.yanNaviqasiya` — Sidebar Nav

Yan menyu (sidebar).

| Parametr | Standart | İzah |
|---|---|---|
| `elementlər` | — | elementlərin siyahısı |
| `cari` | — | seçili element |
| `klik` | — | basıldıqda çağırılır |
| `başlıq` | — | başlıq mətni |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `klik`

```alqor
vidjet.yanNaviqasiya(elementlər: ["Ana", "Hesabatlar",
                                  "Ayarlar"],
                     cari: özü.yanNaviqasiya, klik: özü.yanNaviqasiyaSeçildi)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət yanNaviqasiya: mətn = "Ana"

metod yanNaviqasiyaSeçildi(dəyər: mətn)
    özü.yanNaviqasiya = dəyər
son
```

#### `vidjet.alətlərPaneli` — Toolbar

Alətlər paneli (toolbar).

| Parametr | Standart | İzah |
|---|---|---|
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.alətlərPaneli(məzmun: [
    vidjet.ikonDüymə(ikon: "B", başlıq: "Qalın"),
    vidjet.ikonDüymə(ikon: "I", başlıq: "Maili")
])
```

### 14.7.6 Üst qat — Overlays (`üst qat`, 7)

#### `vidjet.modal` — Modal

Modal pəncərə.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `altlıq` | — | aşağı hissə — adətən düymələr |
| `görünür` | `doğru` | `yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə olunur |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |
| `ölçü` | `"orta"` | pəncərənin eni: `kiçik` · `orta` · `böyük` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.yanPanel` — Drawer

Yan panel (drawer).

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `görünür` | `doğru` | `yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə olunur |
| `tərəf` | `"sağ"` | `sol` · `sağ` |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

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

#### `vidjet.ipucu` — Tooltip

Üzərinə gələndə görünən izah.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | ipucunun mətni |
| `məzmun` | — | üzərinə gəlinəcək element |
| `tərəf` | `"üst"` | `üst` · `alt` · `sol` · `sağ` |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.ipucu(mətn: "Silinəcək",
             məzmun: vidjet.ikonDüymə(ikon: "✕"))
```

#### `vidjet.bildirişQutusu` — Toast

Küncdə görünən bildiriş.

| Parametr | Standart | İzah |
|---|---|---|
| `mətn` | `""` | bildirişin mətni |
| `növ` | `"məlumat"` | `uğur` · `xəbərdarlıq` · `təhlükə` · `məlumat` |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `bağlandı`

```alqor
vidjet.bildirişQutusu(mətn: "Saxlanıldı", növ: "uğur")
```

#### `vidjet.açılanPanel` — Popover

Açılan panel (popover).

| Parametr | Standart | İzah |
|---|---|---|
| `düymə` | `"Ətraflı"` | açan düymənin mətni və ya elementi |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `açılmış` | `yanlış` | ilkin vəziyyətdə açıqdır |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

```alqor
vidjet.açılanPanel(düymə: "Filtr", məzmun: [])
```

#### `vidjet.təsdiqDialoqu` — Confirm Dialog

Təsdiq dialoqu.

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `"Əminsiniz?"` | başlıq mətni |
| `mətn` | `""` | görünən mətn |
| `görünür` | `doğru` | `yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə olunur |
| `təsdiqləndi` | — | təsdiq düyməsi basıldıqda çağırılır |
| `ləğvEdildi` | — | ləğv və ya bağlama zamanı çağırılır |
| `təsdiqMətni` | `"Bəli"` | təsdiq düyməsinin yazısı |
| `ləğvMətni` | `"Xeyr"` | ləğv düyməsinin yazısı |
| `təhlükəli` | `yanlış` | `doğru` — təsdiq düyməsi qırmızı (silmə kimi əməllər) |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `təsdiqləndi` · `ləğvEdildi`

```alqor
vidjet.təsdiqDialoqu(başlıq: "Silinsin?",
                     mətn: "Bu əməl geri qaytarılmır.",
                     görünür: özü.təsdiqDialoqu, təhlükəli: doğru,
                     təsdiqləndi: özü.təsdiqDialoquBəli,
                     ləğvEdildi: özü.təsdiqDialoquXeyr)
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət təsdiqDialoqu: məntiq = yanlış

metod təsdiqDialoquBəli()
    özü.təsdiqDialoqu = yanlış
    // silmə əməli
son

metod təsdiqDialoquXeyr()
    özü.təsdiqDialoqu = yanlış
son
```

#### `vidjet.altVərəq` — Bottom Sheet

Aşağıdan açılan panel (bottom sheet).

| Parametr | Standart | İzah |
|---|---|---|
| `başlıq` | `""` | başlıq mətni |
| `məzmun` | — | uşaq element(lər) — tək element və ya siyahı |
| `görünür` | `doğru` | `yanlış` olduqda heç nə göstərilmir — vəziyyətlə idarə olunur |
| `bağlandı` | — | bağlama düyməsi (✕) basıldıqda çağırılır; verilməyibsə düymə görünmür |
| `üslub` | — | görünüş: `{"rəng": …, "fon": …, "kənar": …, "künc": 8, "şrift": 18, "qalın": doğru}` — bax § 14.8 |

Hadisələr: `bağlandı`

```alqor
vidjet.altVərəq(başlıq: "Paylaş", görünür: özü.altVərəq,
                bağlandı: özü.altVərəqBağla, məzmun: [])
```

Kod skeleti (IDE-də iki klik):

```alqor
vəziyyət altVərəq: məntiq = yanlış

metod altVərəqBağla()
    özü.altVərəq = yanlış
son
```

<!-- ARAYIŞ SONU -->

---

## 14.8 Görünüş — `üslub:`

Hər vidjet əlavə olaraq `üslub:` parametrini qəbul edir:

```alqor
vidjet.düymə(mətn: "Saxla", növ: "əsas",
             üslub: {"fon": "#16a34a", "rəng": "#fff", "künc": 20,
                     "kənar": "2px solid #14532d", "şrift": 17,
                     "qalın": doğru})

vidjet.sahə(etiket: "Ad", ad: "ad",
            üslub: {"kənarRəngi": "#0b6bcb", "en": 320})
```

| Açar | CSS | Qeyd |
|---|---|---|
| `rəng` | `color` | mətnin rəngi |
| `fon` | `background` | |
| `kənar` | `border` | `"2px solid #333"` |
| `kənarRəngi` | `border-color` | |
| `künc` | `border-radius` | ədəd → piksel |
| `şrift` | `font-size` | ədəd → piksel |
| `şriftAiləsi` | `font-family` | |
| `qalın` / `kursiv` | `font-weight` / `font-style` | `doğru` / `yanlış` |
| `qalınlıq` | `font-weight` | `400`, `700` … |
| `en`, `hündürlük`, `minEn`, `maksEn` | ölçülər | ədəd → piksel; vidjetin **bütövünə** |
| `boşluq` | `padding` | |
| `xaricBoşluq` | `margin` | vidjetin **bütövünə** |
| `düzləndir` | `text-align` | `sol` · `orta` · `sağ` · `iki tərəf` |
| `şəffaflıq` | `opacity` | `0`–`1` |
| `kölgə` | `box-shadow` | |

Form sahələrində (`sahə`, `seçim`, `çoxsətirli` …) rəng, fon, kənar,
künc və şrift **sahənin özünə** (`input`), ölçülər və `xaricBoşluq`
etiketlə birlikdə bütövə aiddir. Naməlum açar `ArqumentXətası` verir.
Dəyərdə `;` `{` `}` `<` `>`, `url(`, `expression`, `javascript` olarsa
rədd edilir — üslub CSS-dən kənara çıxa bilməz.

Alqor Studio-nun **Xüsusiyyətlər** paneli bu parametri vizual redaktə
edir (§ 13.9).

---

## 14.9 Təhlükəsizlik

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

## 14.10 Sınaq

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

## 14.11 Xəta kodları

| Kod | Nə vaxt |
|---|---|
| ALQ-R013 | icazəsiz `növ` / `ölçü` / `tərəf`; olmayan vidjet adı (`skelet`, `nümunə`); olmayan kateqoriya; təkrarlanan komponent yolu |
| ALQ-T004 | `cütlər` / `sətirlər` lüğət və ya cüt siyahısı deyil |
| ALQ-T008 | hadisə parametrinə funksiya olmayan dəyər verilib |
| ALQ-T053 | komponentdə `göstər()` yoxdur; `s.komponent`-ə komponent olmayan dəyər verilib |
