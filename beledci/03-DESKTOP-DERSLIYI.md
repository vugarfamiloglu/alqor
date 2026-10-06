# Alqor Bələdçisi — 4. Desktop Dərsliyi

> Bu dərslikdə sıfırdan **tapşırıq meneceri** qururuq: form, siyahı,
> süzgəc, təsdiq pəncərəsi, menyu, fayla saxlama. Sonda eyni kodu
> brauzerdə də açırıq.
>
> Yekun proqram: [`numuneler/09-tapsiriqlar.alqor`](../numuneler/09-tapsiriqlar.alqor).
> Bu səhifədəki hər tam proqram avtomatik sınaqlarla yoxlanılır.

**Lazım olanlar:** Python 3.12+ və Chrome, Edge, Brave və ya Chromium
brauzerlərindən biri. Başqa heç nə quraşdırmaq lazım deyil.

---

## 4.1 Necə işləyir?

Alqor desktop tətbiqi iki hissədən ibarətdir:

```
┌──────────────────────┐   HTML    ┌───────────────────────────┐
│ Sizin Alqor kodunuz  │ ────────▶ │ Pəncərə (Chrome --app,    │
│ + yerli server       │ ◀──────── │ ünvan zolağı yoxdur)      │
│ 127.0.0.1:<port>     │  hadisə   │                           │
└──────────────────────┘           └───────────────────────────┘
```

1. Komponentin `göstər()` metodu interfeysi təsvir edir.
2. Alqor onu HTML-ə çevirir və kompüterinizdə yerli server qaldırır
   (yalnız sizin kompüterinizdən əlçatandır).
3. Pəncərə həmin səhifəni göstərir. Düymə basılanda hadisə serverə
   gedir, sizin metodunuz işləyir, ekran yenilənir.

Pəncərəni nə açır — **aparıcı** — avtomatik seçilir: `pywebview`
quraşdırılıbsa o, yoxsa Chrome/Edge/Brave-in tətbiq rejimi, o da yoxsa
adi brauzer nişanı. Server olmayan mühitdə (CI, sınaq) heç nə açılmır —
buna **başsız rejim** deyilir.

---

## 4.2 İlk pəncərə

`salam.alqor` faylı yaradın:

```alqor
// addım 1 — ilk pəncərə
gətir pəncərə

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Salam", 360, 200)
    p.məzmun(<h1>Salam, dünya!</h1>)
    p.göstər()
    pəncərə.işlət()
son
```

İşlədin:

```powershell
cd alqor\alqorc
python alqorc.py işlət salam.alqor
```

| Sətir | Nə edir |
|---|---|
| `yeni pəncərə.Pəncərə("Salam", 360, 200)` | başlıq, en, hündürlük |
| `p.məzmun(...)` | pəncərədə nə görünəcək — JSX |
| `p.göstər()` | pəncərəni açır (proqramı dayandırmır) |
| `pəncərə.işlət()` | bütün pəncərələr bağlanana qədər gözləyir və hadisələri işləyir |

> `pəncərə.işlət()`-i unutsanız proqram dərhal bitir və pəncərə
> bağlanır.

---

## 4.3 Komponent və vəziyyət

Sabit mətn darıxdırıcıdır. **Komponent** — öz vəziyyəti olan interfeys
hissəsidir. `vəziyyət` sahəsi dəyişəndə ekran özü yenilənir:

```alqor
// addım 2 — sayğac
gətir pəncərə

komponent Sayğac
    vəziyyət say: tam = 0

    göstər()
        qaytar <div>
            <h1>{özü.say}</h1>
            <button klik={() => özü.say += 1}>Artır</button>
            <button klik={() => özü.say = 0}>Sıfırla</button>
        </div>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Sayğac", 300, 200)
    p.məzmun(<Sayğac />)
    p.göstər()
    pəncərə.işlət()
son
```

Diqqət edin:

* `klik={…}` — düymə basılanda nə olsun. Burada qısa ox funksiyası
  (`() => …`) işlənir.
* `{özü.say}` — JSX daxilində `{…}` ifadədir.
* `yenilə()`, `göstər()` kimi heç nə çağırmırıq — `özü.say` dəyişdi,
  ekran yeniləndi.

---

## 4.4 Hazır elementlər: `vidjet`

HTML-i əl ilə yazmaq əvəzinə `vidjet` modulunun 57 hazır elementindən
istifadə edək — üslubu, rəngləri və qaranlıq rejimi hazırdır:

```alqor
// addım 3 — form
gətir pəncərə
gətir vidjet

sinif Tapşırıq
    qurucu(açıq xassə ad: mətn,
           açıq xassə vacib: məntiq,
           açıq xassə bitib: məntiq)
son

komponent Menecer
    vəziyyət tapşırıqlar: siyahı[Tapşırıq] = []
    vəziyyət yeniAd: mətn = ""
    vəziyyət vacibdir: məntiq = yanlış
    vəziyyət xəta: mətn = ""

    metod adYazıldı(dəyər: mətn)
        özü.yeniAd = dəyər
        özü.xəta = ""
    son

    metod vaciblikDəyişdi(dəyər: məntiq)
        özü.vacibdir = dəyər
    son

    metod əlavəEt()
        dəyişən ad = özü.yeniAd.kəs()
        əgər ad == "" onda
            özü.xəta = "Tapşırığın adını yazın"
            qaytar
        son
        özü.tapşırıqlar = özü.tapşırıqlar + [
            yeni Tapşırıq(ad, özü.vacibdir, yanlış)]
        özü.yeniAd = ""
        özü.vacibdir = yanlış
    son

    göstər()
        qaytar vidjet.sütun(boşluq: 16, məzmun: [
            vidjet.başlıq(mətn: "Tapşırıqlar"),
            vidjet.form(göndərildi: özü.əlavəEt, məzmun: [
                vidjet.sətir(şaquli: "son", məzmun: [
                    vidjet.sahə(etiket: "Yeni tapşırıq", ad: "yeniAd",
                                dəyər: özü.yeniAd, xəta: özü.xəta,
                                yer: "Nə etmək lazımdır?",
                                yazıldı: özü.adYazıldı),
                    vidjet.qeyd(etiket: "Vacib", ad: "vacib",
                                işarələnmiş: özü.vacibdir,
                                dəyişdi: özü.vaciblikDəyişdi),
                    vidjet.düymə(mətn: "Əlavə et", klik: özü.əlavəEt)
                ])
            ]),
            vidjet.siyahı(elementlər:
                özü.tapşırıqlar.çevir((t) => t.ad))
        ])
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Tapşırıqlar", 560, 640)
    p.məzmun(<Menecer />)
    p.göstər()
    pəncərə.işlət()
son
```

Burada üç vacib qayda var:

**1. Vidjetin parametrləri adlıdır.** `vidjet.sahə(etiket: "…", ad: "…")`
— sıranı yadda saxlamaq lazım deyil. Bütün parametrlər: spesifikasiya
§ 14.7.

**2. Hadisə idarəedicisi dəyəri alır.**

| Hadisə | Nə vaxt | İdarəedici alır |
|---|---|---|
| `yazıldı` | hər hərfdə | sahənin mətni |
| `dəyişdi` | sahədən çıxanda / qutucuq dəyişəndə | mətn; qutucuq üçün `doğru`/`yanlış` |
| `klik` | basılanda | düymənin dəyəri (varsa) |
| `göndərildi` | formda Enter basılanda | heç nə |

**3. Sahənin dəyəri vəziyyətdən gəlir.** `dəyər: özü.yeniAd` və
`özü.yeniAd = ""` — əlavə etdikdən sonra sahə özü təmizlənir.

> **Niyə `yeniAd`, `ad` yox?** `yeni` Alqor-da açar sözdür
> (`yeni Tapşırıq(...)`), ona görə dəyişən adı ola bilməz. Eyni ilə
> `seç`, `hal`, `son`, `tip` deyil, `sinif`. Kompilyator belə hallarda
> `ALQ-L010` xətası verir və başqa ad seçməyi təklif edir.

---

## 4.5 Siyahını cədvəldə göstərmək

Sadə siyahı əvəzinə cədvəl və vəziyyət nişanı qoyaq. Sətrə klik
tapşırığı bitmiş/aktiv edir:

```alqor
// parça — Menecer komponentinə əlavə edin
metod sətirSeçildi(dəyər: mətn)
    // Cədvəl basılan sətrin indeksini (0-dan, mətn kimi) verir
    dəyişən t = özü.tapşırıqlar[tamƏt(dəyər, 0)]
    t.bitib = deyil t.bitib
    özü.tapşırıqlar = özü.tapşırıqlar      // ekranı yenilə
son
```

`göstər()`-dəki `vidjet.siyahı(...)` sətrini bununla əvəz edin:

```alqor
// parça
göstər()
    qaytar əgər uzunluq(özü.tapşırıqlar) == 0 onda
        vidjet.boşBaxış(başlıq: "Tapşırıq yoxdur",
                        mətn: "Yuxarıdan yenisini əlavə edin")
    yoxsa
        vidjet.cədvəl(
            sütunlar: ["Tapşırıq", "Vəziyyət"],
            sətirlər: özü.tapşırıqlar.çevir((t) => [
                əgər t.vacib onda "★ {t.ad}" yoxsa t.ad son,
                əgər t.bitib onda
                    vidjet.nişan(mətn: "bitib", növ: "uğur")
                yoxsa
                    vidjet.nişan(mətn: "aktiv")
                son
            ]),
            sətirKlik: özü.sətirSeçildi)
    son
son
```

İki yeni şey:

* **`əgər … onda … yoxsa … son` ifadədir** — dəyər qaytarır, ona görə
  cədvəlin xanasına birbaşa yazılır.
* **`özü.tapşırıqlar = özü.tapşırıqlar`** — `t.bitib` obyektin içində
  dəyişdi, amma `vəziyyət` sahəsinin özü yox. Sahəni yenidən mənimsətmək
  ekrana "yenilən" deyir.

---

## 4.6 Süzgəc: hesablanan xassə və nişanlar

"Hamısı / Aktiv / Bitmiş" nişanları əlavə edək. Göstəriləcək siyahı
**hesablanan xassədir** — hər dəfə vəziyyətdən hesablanır:

```alqor
// parça
vəziyyət süzgəc: mətn = "Hamısı"

hesablanan görünənlər: siyahı[Tapşırıq]
    seç özü.süzgəc
        hal "Aktiv" → qaytar özü.tapşırıqlar.filtr((t) => deyil t.bitib)
        hal "Bitmiş" → qaytar özü.tapşırıqlar.filtr((t) => t.bitib)
        digər hallarda → qaytar özü.tapşırıqlar
    son
son

hesablanan bitmişSayı: tam
    qaytar özü.tapşırıqlar.filtr((t) => t.bitib).uzunluq()
son

metod süzgəcSeçildi(dəyər: mətn)
    özü.süzgəc = dəyər
son
```

```alqor
// parça — göstər() içində
vidjet.nişanlar(elementlər: ["Hamısı", "Aktiv", "Bitmiş"],
                cari: özü.süzgəc, klik: özü.süzgəcSeçildi)
```

İndi cədvəldə `özü.tapşırıqlar` yerinə `özü.görünənlər` yazın. Diqqət:
`sətirSeçildi` də indeksi **görünən** siyahıda axtarmalıdır —
`özü.görünənlər[tamƏt(dəyər, 0)]`.

Tərəqqi zolağı da əlavə edək:

```alqor
// parça — göstər() içində
vidjet.tərəqqi(dəyər: özü.bitmişSayı,
               maksimum: maksimum(1, uzunluq(özü.tapşırıqlar)),
               növ: "uğur")
```

---

## 4.7 Təsdiq pəncərəsi: `modal`

Bitmişləri silməzdən əvvəl soruşaq. Modal həmişə `göstər()`-də yazılır,
amma yalnız `görünür: doğru` olanda görünür:

```alqor
// parça
vəziyyət soruşulur: məntiq = yanlış

metod bitmişləriSil()
    özü.tapşırıqlar = özü.tapşırıqlar.filtr((t) => deyil t.bitib)
    özü.soruşulur = yanlış
son

göstər()
    qaytar vidjet.sütun(məzmun: [
        vidjet.düymə(mətn: "Bitmişləri sil", növ: "təhlükə",
                     söndürülmüş: özü.bitmişSayı == 0,
                     klik: () => özü.soruşulur = doğru),
        vidjet.modal(başlıq: "Bitmiş tapşırıqlar silinsin?",
                     görünür: özü.soruşulur,
                     bağlandı: () => özü.soruşulur = yanlış,
                     məzmun: [vidjet.mətn(
                         məzmun: "{özü.bitmişSayı} tapşırıq silinəcək.")],
                     altlıq: [
                         vidjet.düymə(mətn: "Ləğv et", növ: "ikinci",
                                      klik: () => özü.soruşulur = yanlış),
                         vidjet.düymə(mətn: "Sil", növ: "təhlükə",
                                      klik: özü.bitmişləriSil)
                     ])
    ])
son
```

`bağlandı:` verildikdə modalın küncündə ✕ düyməsi görünür.

---

## 4.8 Menyu və qısayollar

Menyu pəncərəyə aiddir, komponentə yox. Menyudan komponentin metodunu
çağırmaq üçün komponent nümunəsini **özümüz yaradırıq**:

```alqor
// parça — əsas() funksiyası
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Tapşırıqlar", 560, 640)
    dəyişən menecer = yeni Menecer()
    p.məzmun(menecer)                // <Menecer /> əvəzinə
    p.menyu([
        pəncərə.menyu("Fayl", [
            pəncərə.element("Aç…", qısayol: "Ctrl+O",
                            klik: () => menecer.aç()),
            pəncərə.element("Saxla…", qısayol: "Ctrl+S",
                            klik: () => menecer.saxla()),
            pəncərə.ayırıcı(),
            pəncərə.element("Çıxış", qısayol: "Ctrl+Q",
                            klik: () => p.bağla())
        ])
    ])
    p.mərkəzə().göstər()
    pəncərə.işlət()
son
```

Qısayollar pəncərə fokusda olanda işləyir. `pəncərə.element`-in
`söndürülmüş: doğru` və `işarələnmiş: doğru` parametrləri də var.

---

## 4.9 Fayla saxlamaq: dialoqlar və JSON

```alqor
// parça — faylın başına
gətir pəncərə.dialoq
gətir json
```

```alqor
// parça — Menecer daxilində
metod saxla()
    dəyişən yol = dialoq.faylSaxla(standartAd: "tapşırıqlar.json",
                                   süzgəclər: {"JSON": "*.json"})
    əgər yol boşdur onda
        qaytar                   // istifadəçi "Ləğv et" basdı
    son
    json.faylYaz(yol, özü.tapşırıqlar.çevir(lüğətə))
    pəncərə.bildiriş("Saxlanıldı", yol)
son

metod aç()
    dəyişən yol = dialoq.faylAç(süzgəclər: {"JSON": "*.json"})
    əgər yol boşdur onda
        qaytar
    son
    cəhd et
        özü.tapşırıqlar = json.faylOxu(yol).çevir(lüğətdən)
    tut x
        dialoq.xəta("Fayl oxunmadı", x.mesaj)
    son
son
```

`lüğətə` və `lüğətdən` — obyekti JSON-a uyğun lüğətə və geri çevirən
iki kiçik funksiya:

```alqor
// parça — faylın səviyyəsində
funksiya lüğətə(t: Tapşırıq) -> lüğət[mətn, istənilən]
    qaytar {"ad": t.ad, "vacib": t.vacib, "bitib": t.bitib}
son

funksiya lüğətdən(l: lüğət[mətn, istənilən]) -> Tapşırıq
    qaytar yeni Tapşırıq(l["ad"], l["vacib"] == doğru, l["bitib"] == doğru)
son
```

Bütün dialoqlar:

| Funksiya | Qaytarır |
|---|---|
| `dialoq.məlumat(başlıq, mesaj)` / `xəbərdarlıq` / `xəta` | — |
| `dialoq.təsdiqlə(başlıq, mesaj)` | `doğru` / `yanlış` |
| `dialoq.soruş(başlıq, mesaj, standart)` | mətn və ya `boş` |
| `dialoq.faylAç(süzgəclər?)` / `faylAçHamısı` | yol / yolların siyahısı |
| `dialoq.faylSaxla(standartAd?, süzgəclər?)` | yol və ya `boş` |
| `dialoq.qovluqSeç()` / `dialoq.rəngSeç()` | yol / `"#rrggbb"` |

> **Linux:** dialoqlar üçün `python3-tk` paketi lazımdır
> (`sudo apt install python3-tk`). Windows və macOS-da Python ilə gəlir.

---

## 4.10 Üslub və tema

Rənglər CSS dəyişənləridir. Pəncərəyə öz üslubunuzu əlavə edin:

```alqor
// parça
p.üslub(x":root{--v-vurgu:#7c3aed;--v-radius:12px}")
```

`x"…"` — **xam mətn**: adi mətndə `{…}` interpolyasiyadır, CSS-in
fiqurlu mötərizələri isə olduğu kimi qalmalıdır. Qaranlıq rejim
əməliyyat sisteminin ayarına avtomatik uyğunlaşır. Bütün dəyişənlər:
spesifikasiya § 14.4.

---

## 4.11 Sınaq yazmaq

Pəncərə açmadan düymə basmaq, sahəyə yazmaq və nəticəni yoxlamaq olar.
Bu, həm avtomatik sınaqlar, həm də CI üçündür:

```alqor
// parça — yoxlama funksiyası
funksiya yoxla()
    dəyişən p = yeni pəncərə.Pəncərə("Tapşırıqlar")
    p.məzmun(<Menecer />)
    dəyişən s = pəncərə.sınaq.aç(p)

    s.klik("Əlavə et")
    iddia s.ehtiva("Tapşırığın adını yazın")

    s.hadisə("yazıldı", "yeniAd", "Süd al")
    s.klik("Əlavə et")
    s.klik("Süd al")                       // cədvəl sətri
    iddia s.ehtiva("bitib")

    // Dialoqun cavabını əvvəlcədən veririk
    pəncərə.sınaq.cavablar(["/tmp/t.json"])
    s.klik("Saxla…")
    iddia pəncərə.sınaq.jurnal()[0][0] == "faylSaxla"
son
```

| Metod | Nə edir |
|---|---|
| `s.klik(mətn)` | düymə, menyu elementi, cədvəl sətri — mətni, `ad`-ı və ya `kimlik`-i ilə |
| `s.yaz(ad, dəyər)` | sahəyə yazır (`dəyişdi`); qutucuğa `doğru`/`yanlış` |
| `s.hadisə(ad, nişan, dəyər)` | istənilən hadisə: `"yazıldı"`, `"ikiKlik"`… |
| `s.ehtiva(mətn)` | ekranda belə mətn varmı |
| `s.HTML()` / `s.mətn()` | ekranın HTML-i / mətni |

---

## 4.12 Eyni kod — vebdə

Komponent heç nə bilmir harada işlədiyini. Onu veb serverə qoşaq:

```alqor
// parça
gətir veb

funksiya vebServeri()
    dəyişən s = yeni veb.Server()
    s.komponent("/", Menecer, başlıq: "Tapşırıqlar")
    s.dinlə(8082)
son
```

Brauzerdə `http://127.0.0.1:8082` açın — eyni interfeys, eyni
davranış. Hər brauzer (sessiya) öz tapşırıq siyahısını alır. Menyu və
fayl dialoqları desktopa xasdır; vebdə onların əvəzinə düymələr
işlədilir.

Hədəfi əmr sətrindən seçmək üçün:

```alqor
// parça
funksiya əsas(arqumentlər: siyahı[mətn])
    əgər "veb" içindədir arqumentlər onda
        vebServeri()
    yoxsa
        desktop()
    son
son
```

```powershell
python alqorc.py işlət tapşırıqlar.alqor            # desktop
python alqorc.py işlət tapşırıqlar.alqor -- veb     # veb
```

---

## 4.13 Yekun proqram

Bütün hissələr bir yerdə: [`numuneler/09-tapsiriqlar.alqor`](../numuneler/09-tapsiriqlar.alqor).

```powershell
python alqorc.py işlət ..\numuneler\09-tapsiriqlar.alqor
python alqorc.py işlət ..\numuneler\09-tapsiriqlar.alqor -- veb
python alqorc.py işlət ..\numuneler\09-tapsiriqlar.alqor -- sınaq
```

Və ya Windows-da `Desktop-ac.cmd`-ə iki dəfə klik (06 nümunəsini açır).

---

## 4.14 Tez-tez rast gəlinən xətalar

| Xəta | Səbəb | Həll |
|---|---|---|
| `ALQ-L010 'yeni' açar sözdür` | dəyişən adı açar sözdür (`yeni`, `seç`, `son`, `tip`…) | başqa ad: `yeniAd`, `seçildi` |
| Ekran yenilənmir | obyektin içi dəyişdi, `vəziyyət` sahəsi yox | `özü.siyahı = özü.siyahı` |
| CSS mətnində `ALQ-P005` (kömək: "adi mətndə `{…}` interpolyasiyadır") | adi mətndə `{…}` interpolyasiyadır | xam mətn: `x"…"` |
| Pəncərə dərhal bağlanır | `pəncərə.işlət()` çağırılmayıb | `p.göstər()`-dən sonra əlavə edin |
| `ALQ-T053 göstər() metodu yoxdur` | `komponent`-də `göstər()` yazılmayıb | — |
| `` `növ` sahəsi `qırmızı` yoxdur `` | vidjet növü səhvdir | xəta mesajı icazəli dəyərləri sadalayır |
| Linux-da dialoq açılmır | `tkinter` yoxdur | `sudo apt install python3-tk` |

---

## 4.15 Paketləmə (planlaşdırılır)

`alqor paketlə --hədəf deb | appimage | windows-nsis` əmrləri
(spesifikasiya § 12.3) hələ hazırlanır. Hazırda tətbiq Python ilə
`alqorc.py işlət` vasitəsilə işlədilir.
