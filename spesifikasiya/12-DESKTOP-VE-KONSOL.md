# Alqor — Bölmə 12: Desktop və Konsol Tətbiqləri

---

## 12.1 Konsol tətbiqləri

### Ən sadə proqram
```alqor
funksiya əsas()
    yaz("Adınızı daxil edin:")
    dəyişən ad = oxu()
    yaz("Salam, {ad}!")
son
```

```bash
alqor işlət salam.alq          # dərhal işlət (VM)
alqor qur salam.alq            # binar yarat
./salam                          # işlət
```

### Əmr sətri arqumentləri
```alqor
gətir konsol

funksiya əsas()
    dəyişən arq = konsol.arqumentlər()
        .proqram("hesabla")
        .versiya("1.0.0")
        .təsvir("Riyazi hesablayıcı")
        .parametr("əməliyyat", "Əməliyyat: topla | çıx")
        .parametr("ədədlər", "Ədədlər", çoxlu: doğru)
        .bayraq("--ətraflı", "-ə", "Ətraflı çıxış")
        .seçim("--format", "-f", "Çıxış formatı", standart: "mətn")
        .təhlil()

    əgər arq.bayraq("--ətraflı") onda
        yaz("Ətraflı rejim")
    son

    dəyişən ədədlər = arq.siyahı("ədədlər").çevir((x) => onluqƏt(x, 0))
    seç arq.dəyər("əməliyyat")
        hal "topla" → yaz(ədədlər.cəm())
        hal "çıx" → yaz(ədədlər[0] - ədədlər[1..].cəm())
        digər hallarda → yaz("Naməlum əməliyyat")
    son
son
```

Təhlilçi proqramın **öz** arqumentlərini oxuyur (`alqor işlət f.alq
-- topla 2 3` → `["topla", "2", "3"]`; `sistem.arqumentlər()` də eynidir).
`--` sonrakı hər şeyi mövqeli sayır; `--format=json` və `-f json` eynidir.
`--kömək` köməyi çap edib proqramı 0 kodu ilə, səhv arqument isə xəta
və istifadə qaydasını stderr-ə çap edib **3** kodu ilə bitirir (§ 13.16).

Avtomatik yaradılan kömək:
```
$ hesabla --kömək
hesabla 1.0.0
Riyazi hesablayıcı

İSTİFADƏ:
    hesabla [SEÇİMLƏR] <əməliyyat> <ədədlər>...

ARQUMENTLƏR:
    <əməliyyat>    Əməliyyat: topla | çıx
    <ədədlər>...   Ədədlər

SEÇİMLƏR:
    -ə, --ətraflı          Ətraflı çıxış
    -f, --format <FORMAT>  Çıxış formatı [standart: mətn]
    -k, --kömək            Bu köməyi göstər
    -v, --versiya          Versiyanı göstər
```

### Rəngli çıxış
```alqor
gətir konsol

yaz(konsol.qırmızı("Xəta!"))
yaz(konsol.yaşıl("Uğurlu"), konsol.sarı("Xəbərdarlıq"))
yaz(konsol.mavi("Məlumat"), konsol.boz("İkinci dərəcəli"))
yaz(konsol.qalın("Vacib"), konsol.altXətt("Vurğulanmış"))
yaz(konsol.rəng("mətn", ön: "qırmızı", arxa: "ağ", qalın: doğru))

konsol.təmizlə()
konsol.kursor(5, 10)                    // sətir, sütun
dəyişən (en, hündürlük) = konsol.ölçü()
əgər konsol.terminaldır() onda ... son  // çıxış boruya gedirmi?
```

Rəng funksiyaları **mətn qaytarır** (çap etmir) — birləşdirilə bilər.
Rənglər: `qara` `qırmızı` `yaşıl` `sarı` `mavi` `bənövşəyi` `firuzəyi`
`ağ` `boz`. `NO_COLOR` mühit dəyişəni təyin olunubsa rəng kodları
buraxılır; Windows 10+ konsolunda ANSI avtomatik aktivləşir.

### İnteraktiv elementlər
```alqor
dəyişən ad = konsol.soruş("Adınız: ", standart: "Qonaq")
dəyişən parol = konsol.parolSoruş("Parol: ")      // simvollar görünmür
dəyişən razı = konsol.təsdiqlə("Davam edilsin?", standart: doğru)
dəyişən rəng = konsol.seç("Rəng seçin:", ["Qırmızı", "Yaşıl", "Mavi"])
dəyişən lazım = konsol.çoxSeç("Nə lazımdır?", ["A", "B", "C"])
```

| Funksiya | Davranış |
|---|---|
| `soruş(sual?, standart?)` | boş cavabda `standart` |
| `parolSoruş(sual?)` | terminalda əks-səda yoxdur |
| `təsdiqlə(sual, standart?)` | `hə`/`bəli`/`h` → `doğru`, `yox`/`xeyr` → `yanlış`; başqa cavabda təkrar soruşur |
| `seç(sual, seçimlər)` | nömrəli siyahı; nömrə və ya ad ilə seçilir, **elementi** qaytarır |
| `çoxSeç(sual, seçimlər)` | `1,3` və ya `1 3`; elementlərin siyahısı (boş ola bilər) |

Hamısı `oxu()` kimi proqramın giriş axınını işlədir — sınaqda cavablar
əvvəlcədən verilə bilər. Giriş bitibsə `GirişÇıxışXətası` (ALQ-R009).

```alqor
// İrəliləyiş zolağı
dəyişən p = konsol.irəliləyiş(100, "Yüklənir")
hər i üçün 1..100 içində
    emal(i)
    p.artır()                    // və ya p.yenilə(i)
son
p.bitir("Hazırdır ✓")
// Yüklənir ████████████░░░░░░░░░░░░░░░░  45% (45/100)

// Fırlanan göstərici
dəyişən f = konsol.fırlanan("İşlənir...")
gözlə uzunƏməliyyat()
f.mətnDəyiş("Yazılır...")
f.dayandır("Bitdi ✓")

// Cədvəl
konsol.cədvəl(
    ["Ad", "Yaş", "Şəhər"],
    [["Aysel", 24, "Bakı"], ["Rəşad", 31, "Gəncə"]]
)
// Ad    │ Yaş │ Şəhər
// ──────┼─────┼──────
// Aysel │ 24  │ Bakı
```

`irəliləyiş` və `fırlanan` terminalda eyni sətri yeniləyir. Çıxış fayla
və ya boruya yönəldilibsə animasiya olmur, yalnız yekun sətir yazılır.

---

## 12.2 Desktop tətbiqləri (`pəncərə` modulu)

### 12.2.1 Arxitektura — yerli server + yerli pəncərə

İnterfeys komponentlərin `göstər()` metodunun qaytardığı JSX-dir; JSX
HTML-ə çevrilir (`veb` modulu ilə **eyni kod**). Desktop tətbiqi üçün
ayrı düzülüş mühərriki yoxdur: HTML-i `127.0.0.1`-də təsadüfi portda
qalxan yerli server verir, onu isə yerli pəncərə göstərir (Tauri modeli).
Məntiq yerli koddur — fayl, şəbəkə, proses tam əlçatandır.

**Aparıcı** (pəncərəni açan) bu sıra ilə seçilir:

| # | Aparıcı | Şərt |
|---|---|---|
| 1 | `pywebview` | quraşdırılıbsa — həqiqi yerli pəncərə (WebKitGTK / WebView2) |
| 2 | Chrome / Edge / Brave / Chromium `--app=` | **standart** — çərçivəsiz tətbiq pəncərəsi, asılılıq yoxdur |
| 3 | sistem brauzeri | son çarə — adi nişanda |
| 4 | başsız | `ALQOR_BASSIZ=1`, `--başsız` bayrağı, ekransız Linux (`DISPLAY`/`WAYLAND_DISPLAY` yoxdur), CI |

Seçilmiş aparıcı `pəncərə.aparıcı()` ilə oxunur; `pəncərə.başsızdır()`
başsız rejimi bildirir.

**Hadisələr əsas sapda işləyir.** Brauzer hadisəni `/_alqor/hadise`-yə
göndərir; server sapı işi növbəyə qoyub cavab gözləyir, növbəni isə
`pəncərə.işlət()` — əsas sap — boşaldır. Nəticə: idarəedicilər
arasında vəziyyət yarışı olmur, `dialoq.*` isə tkinter-in tələb etdiyi
kimi əsas sapdan çağırılır.

**Təhlükəsizlik.** Yerli server yalnız `127.0.0.1`-də dinləyir,
`Host` başlığı `127.0.0.1:<port>` və ya `localhost:<port>` olmalıdır
(DNS rebinding), hadisə sorğusunda `Origin` varsa öz mənbəyi olmalıdır
(başqa saytın göndərdiyi sorğu 403 alır).

### 12.2.2 Ən sadə pəncərə

```alqor
gətir pəncərə

komponent Sayğac
    vəziyyət say: tam = 0

    göstər()
        qaytar <div>
            <h1>{özü.say}</h1>
            <button klik={() => özü.say += 1}>Artır</button>
        </div>
    son
son

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Sayğac", 320, 240)
    p.məzmun(<Sayğac />)
    p.göstər()
    pəncərə.işlət()           // bütün pəncərələr bağlanana qədər
son
```

`p.məzmun(...)` üç formada verilir:

| Forma | Davranış |
|---|---|
| `<Komponent />` | `vəziyyət` dəyişəndə `göstər()` yenidən çağırılır |
| `() => <p>{x}</p>` | hər hadisədən sonra funksiya yenidən çağırılır |
| `<h1>Salam</h1>` | sabit məzmun |

Hazır elementlər üçün `vidjet` modulu: § 14.

### 12.2.3 `pəncərə.Pəncərə` metodları

`yeni pəncərə.Pəncərə(başlıq = "Alqor", en = 800, hündürlük = 600)`

| Metod | İzah |
|---|---|
| `başlıq()` / `başlıq(mətn)` | oxuyur / təyin edir |
| `məzmun(d)` | məzmun (yuxarıdakı üç forma) |
| `menyu([…])` | menyu sətri (§ 12.2.5) |
| `üslub(CSS)` | əlavə CSS — standart və vidjet üslubundan sonra |
| `ölç(en, hündürlük)` | ölçü |
| `mərkəzə()` | ekranın ortasında açılır |
| `ölçüsüSabit()` | ölçü dəyişdirilə bilmir |
| `bağlananda(f)` | pəncərə bağlanarkən çağırılır |
| `göstər()` | pəncərəni açır; blok etmir |
| `bağla()` | bağlayır |
| `açıqdır()` | `məntiq` |
| `yenilə()` | məzmunu yenidən göstərməyə məcbur edir |
| `gözlə()` | bu pəncərə bağlanana qədər gözləyir |
| `ünvan()` | yerli serverin ünvanı (`http://127.0.0.1:…`) |
| `HTML()` / `səhifə()` | kökün HTML-i / tam sənəd — sınaq üçün |

Metodlar (`göstər`, `bağla`, `gözlə` istisna) `özü`-nü qaytarır —
zəncirlənir: `p.ölç(900, 700).mərkəzə().göstər()`.

Modul funksiyaları: `pəncərə.işlət()`, `pəncərə.dayandır()`,
`pəncərə.pəncərələr()`, `pəncərə.aparıcı()`, `pəncərə.başsızdır()`,
`pəncərə.bildiriş(başlıq, mesaj?)`.

### 12.2.4 Yerli dialoqlar

```alqor
gətir pəncərə.dialoq       // alt modul — `dialoq.*` kimi əlçatandır

dialoq.məlumat("Başlıq", "Mesaj")
dialoq.xəbərdarlıq("Diqqət", "Nəsə düz deyil")
dialoq.xəta("Xəta", "Əməliyyat alınmadı")
dəyişən bəli = dialoq.təsdiqlə("Silinsin?", "Bu geri qaytarıla bilməz")
dəyişən ad = dialoq.soruş("Ad", "Adınızı yazın", "Qonaq")

dəyişən yol = dialoq.faylAç(
    süzgəclər: {"Mətn faylları": ["*.txt", "*.md"], "Hamısı": "*.*"})
dəyişən yollar = dialoq.faylAçHamısı()
dəyişən hara = dialoq.faylSaxla(standartAd: "sənəd.txt")
dəyişən qovluq = dialoq.qovluqSeç()
dəyişən rəng = dialoq.rəngSeç("#3366cc")
```

| Funksiya | Qaytarır |
|---|---|
| `məlumat` / `xəbərdarlıq` / `xəta` `(başlıq, mesaj?)` | `heç` |
| `təsdiqlə(başlıq, mesaj?)` | `məntiq` |
| `soruş(başlıq, mesaj?, standart?)` | `mətn?` — ləğv edilsə `boş` |
| `faylAç(süzgəclər?, qovluq?)` | `mətn?` |
| `faylAçHamısı(süzgəclər?, qovluq?)` | `siyahı[mətn]` |
| `faylSaxla(standartAd?, süzgəclər?, qovluq?)` | `mətn?` |
| `qovluqSeç(qovluq?)` | `mətn?` |
| `rəngSeç(standart?)` | `mətn?` — `"#rrggbb"` |

`süzgəclər` — `{ad: naxış}` və ya `[[ad, naxış], …]`; naxış mətn və ya
mətn siyahısıdır.

Dialoqlar Python-un `tkinter` modulu ilə açılır. `tkinter` yoxdursa
(Linux-da `python3-tk` paketi) və ya başsız rejimdə cavablar
`pəncərə.sınaq.cavablar([…])` növbəsindən götürülür — dialoqlu kod da
sınanır (§ 12.2.7).

### 12.2.5 Menyu

```alqor
p.menyu([
    pəncərə.menyu("Fayl", [
        pəncərə.element("Yeni", qısayol: "Ctrl+N", klik: özü.yeniFayl),
        pəncərə.element("Saxla", qısayol: "Ctrl+S", klik: özü.saxla),
        pəncərə.ayırıcı(),
        pəncərə.element("Çıxış", qısayol: "Ctrl+Q", klik: () => p.bağla())
    ]),
    pəncərə.menyu("Görünüş", [
        pəncərə.element("Qaranlıq rejim", işarələnmiş: doğru,
                        klik: özü.rejimiDəyiş),
        pəncərə.element("Tam ekran", söndürülmüş: doğru)
    ])
])
```

`pəncərə.element(ad, qısayol?, klik?, söndürülmüş?, işarələnmiş?)`.
`klik` verilməyən element sönük göstərilir. Qısayollar pəncərə fokusda
olanda işləyir; yazılış rejistrdən asılı deyil (`Ctrl+Shift+S` =
`ctrl+shift+s`).

### 12.2.6 Sistem bildirişləri

```alqor
pəncərə.bildiriş("Yükləmə bitdi", "3 fayl saxlanıldı")
```

Linux: `notify-send`; macOS: AppleScript; Windows: PowerShell toast.
Heç biri mümkün olmasa səssizcə ötürülür.

### 12.2.7 Sınaq — pəncərə açmadan

```alqor
pəncərə.sınaq.cavablar([doğru, "/tmp/a.txt"])   // dialoq cavabları
dəyişən s = pəncərə.sınaq.aç(p)
s.klik("Artır")                  // düymə mətni, `ad`, `kimlik` və ya etiket
s.yaz("ad", "Aysel")             // sahəyə yazır (`dəyişdi` hadisəsi)
s.hadisə("ikiKlik", "Sil")       // istənilən hadisə
iddia s.ehtiva("Aysel")
iddia pəncərə.sınaq.jurnal()[0][0] == "təsdiqlə"
```

### 12.2.8 Planlaşdırılan (v1.x)

Aşağıdakılar spesifikasiyanın hədəfidir, etalon implementasiyada hələ
yoxdur:

| Xüsusiyyət | Qeyd |
|---|---|
| `p.tamEkran()`, `p.maksimumlaşdır()`, `p.minimumlaşdır()`, `p.həmişəÜstdə()`, `p.şəffaflıq()`, `p.ikon()` | pywebview aparıcısı tələb olunur |
| `p.minimumÖlçü()`, `p.maksimumÖlçü()` | |
| `p.hadisə("bağlanır", h => h.ləğvEt())` | hazırda `bağlananda(f)` bağlanmanı dayandıra bilmir |
| Sistem treyi (`pəncərə.trey`) | |
| Qlobal qısayollar (`pəncərə.qlobalQısayol`) | |

---

## 12.3 Paketləmə və quraşdırıcı

```bash
alqor paketlə --hədəf deb
alqor paketlə --hədəf appimage
alqor paketlə --hədəf flatpak
alqor paketlə --hədəf rpm
alqor paketlə --hədəf targz
alqor paketlə --hədəf windows-nsis      # çarpaz-kompilyasiya
alqor paketlə --hədəf macos-dmg
alqor paketlə --hamısı
```

### `.deb` paketi
`layihe.alq`:
```toml
[paketləmə.deb]
ad = "menim-proqramim"
bölmə = "utils"
prioritet = "optional"
memarlıq = "amd64"
asılılıqlar = ["libwebkit2gtk-4.1-0", "libgtk-3-0"]
təsvir = "Nümunə Alqor desktop tətbiqi"
qoruyucu = "Vüqar Qənbərov <vuqar@nümunə.az>"
masaüstü_faylı = doğru              # .desktop faylı yaradılır
menyu_kateqoriya = "Utility"
```

Nəticə:
```
qurma/paket/menim-proqramim_1.0.0_amd64.deb
```
Quraşdırma: `sudo apt install ./menim-proqramim_1.0.0_amd64.deb`

### `.AppImage`
Tək fayl, heç nə quraşdırmaq lazım deyil, bütün Linux distributivlərində işləyir:
```
qurma/paket/MenimProqramim-1.0.0-x86_64.AppImage
```

### Avtomatik yeniləmə
```alqor
gətir yeniləmə

asinxron funksiya yoxla()
    dəyişən y = gözlə yeniləmə.yoxla("https://nümunə.az/yeniləmə.json")
    əgər y.vardır onda
        əgər dialoq.təsdiqlə("Yenilik var", "Versiya {y.versiya} yüklənsin?") onda
            gözlə y.yüklə((faiz) => p.irəliləyiş(faiz))
            yeniləmə.quraşdırVəYenidənBaşlat()
        son
    son
son
```

---

## 12.4 Eyni kod, üç hədəf

Komponent bir dəfə yazılır; hədəfi yalnız onu "quraşdıran" bir neçə
sətir müəyyən edir.

```alqor
// interfeys.alq
gətir vidjet

komponent TapşırıqSiyahısı
    vəziyyət tapşırıqlar: siyahı[mətn] = ["Süd al", "Hesabatı yaz"]
    vəziyyət yeniTapşırıq: mətn = ""

    metod yazıldı(dəyər: mətn)
        özü.yeniTapşırıq = dəyər
    son

    metod əlavəEt()
        əgər özü.yeniTapşırıq.kəs() != "" onda
            özü.tapşırıqlar = özü.tapşırıqlar + [özü.yeniTapşırıq]
            özü.yeniTapşırıq = ""
        son
    son

    göstər()
        qaytar vidjet.sütun(məzmun: [
            vidjet.siyahı(elementlər: özü.tapşırıqlar),
            vidjet.sətir(məzmun: [
                vidjet.sahə(ad: "yeniTapşırıq", dəyər: özü.yeniTapşırıq,
                            yazıldı: özü.yazıldı),
                vidjet.düymə(mətn: "Əlavə et", klik: özü.əlavəEt)
            ])
        ])
    son
son
```

```alqor
// desktop
dəyişən p = yeni pəncərə.Pəncərə("Tapşırıqlar", 400, 500)
p.məzmun(<TapşırıqSiyahısı />)
p.göstər()
pəncərə.işlət()
```

```alqor
// veb — hər brauzer sessiyası öz siyahısını alır (§ 14.2.2)
dəyişən s = yeni veb.Server()
s.komponent("/", TapşırıqSiyahısı, başlıq: "Tapşırıqlar")
s.dinlə(8080)
```

```alqor
// konsol — eyni sinif, interfeyssiz
dəyişən t = yeni TapşırıqSiyahısı()
hər x üçün t.tapşırıqlar içində
    yaz("• {x}")
son
```

Hədəf əmr sətrindən seçilə bilər (bax: `numuneler/08-vidjetler.alq`):

```alqor
funksiya əsas(arqumentlər: siyahı[mətn])
    əgər "veb" içindədir arqumentlər onda
        vebServeri()
    yoxsa
        desktop()
    son
son
```

Brauzerdə serversiz işləyən (JS/WASM) hədəf — Mərhələ 6, planlaşdırılır.

---

## 12.5 Platformaya xas kod

```alqor
@yalnızHədəf("linux")
funksiya linuxƏməliyyat()
    sistem.əmr("systemctl --user status")
son

@yalnızHədəf("veb")
funksiya brauzerƏməliyyat()
    brauzer.yerliYaddaş.qoy("a", "b")
son

// İcra zamanı yoxlama
əgər sistem.platforma() == "linux" onda
    ...
son
```

---

## 12.6 Formalar — vizual dizayner (`.forma`)

Delphi-dəki `.dfm` + `.pas` cütü kimi: pəncərənin **görünüşü** ayrı
faylda (`Ad.forma`), **kodu** adi `.alq` faylındadır. Alqor Studio-nun
vizual dizayneri forma faylını yazır; kod faylına yalnız yeni hadisə
metodunun boş skeletini əlavə edir, yazdığınız koda toxunmur.

```
mənbə/
  Əsas.forma      görünüş: obyektlər, xassələr, yerləşmə
  Əsas.alq        kod: komponent Əsas — hadisə metodları, məntiq
```

Eyni qovluqdakı `Əsas.forma` `komponent Əsas`-a birləşir:

```
// Əsas.forma
forma Əsas
    başlıq = "Tələbə qeydiyyatı"
    en = 640
    hündürlük = 480

    obyekt AdSahəsi: sahə
        etiket = "Ad"
        ad = "ad"
    son
    obyekt Saxla: düymə
        mətn = "Saxla"
        klik = Saxla_klik
    son
    obyekt Nəticə: mətn
        məzmun = "Hələ heç nə yoxdur"
    son
son
```

```alqor
// Əsas.alq
gətir pəncərə

komponent Əsas
    əməl Saxla_klik()
        özü.Nəticə.məzmun = "Salam, {özü.AdSahəsi.dəyər}!"
    son
son

funksiya əsas()
    pəncərə.formaAç(Əsas)        // formanın başlığı və ölçüsü ilə
    pəncərə.işlət()
son
```

### 12.6.1 Format

| Sətir | Mənası |
|---|---|
| `forma Ad … son` | fayl; `Ad` komponentin adı ilə eyni olmalıdır |
| `xassə = dəyər` | kökdə: `başlıq`, `en`, `hündürlük`, `düzülüş` (`"axın"` · `"sərbəst"`), `boşluq`, `mərkəzə`, `ölçüsüSabit` |
| `obyekt Ad: növ … son` | `növ` — vidjet adı (§ 14) və ya `kətan`; uşaq obyektlər konteynerin `məzmun`-u olur |
| `xassə = dəyər` (obyektdə) | vidjetin parametri; ortaq: `görünür`, `sol`, `yuxarı`, `en`, `hündürlük` |

Dəyər literaldır — mətn, ədəd, `doğru`/`yanlış`, `boş`, siyahı, lüğət,
kortej — və ya **ad**: hadisə xassəsində (`klik`, `dəyişdi` …)
komponentin metodu, başqa xassədə formadakı obyektin adı. Şablon mətn
(`"{x}"`) ola bilməz — dəyişən dəyər kodda verilir.

### 12.6.2 Yerləşmə

- **Axın** (standart): obyektlər yuxarıdan aşağı düzülür; `sütun`,
  `sətir`, `tor` konteynerləri ilə qruplaşdırılır. Pəncərə ölçüsü
  dəyişəndə və vebdə səliqəli qalır.
- **Sərbəst**: kökdə `düzülüş = "sərbəst"` və ya `kətan` konteyneri —
  obyektlər `sol`, `yuxarı`, `en`, `hündürlük` (piksel) ilə yerləşir.

### 12.6.3 Kodda forma obyektləri

- Hər obyekt komponentdə adı ilə sahədir: `özü.AdSahəsi`.
- Xassəni oxumaq və dəyişmək: `özü.Etiket1.mətn = "…"` — hadisədən
  sonra görünüş özü yenilənir.
- Giriş elementlərinin dəyəri (`dəyər`, `yanıq`, `işarələnmiş`,
  `seçili`, `seçilmiş`) istifadəçi yazdıqca avtomatik yenilənir.
- `özü.X.göstər()` / `özü.X.gizlət()` — `görünür` xassəsi;
  `özü.X.xassələr()` — bütün xassələr lüğət kimi.
- Hadisə metodu parametr alırsa, hadisənin dəyərini alır
  (`əməl AdDəyişdi(mətn)`).
- Komponentdə `göstər()` yoxdursa formanın özü göstərilir; varsa —
  komponentin öz `göstər()`-i (forma obyektləri yenə sahə kimi əlçatandır).

`pəncərə.formaAç(Komponent, göstər = doğru)` — formanın `başlıq`,
`en`, `hündürlük`, `mərkəzə`, `ölçüsüSabit` xassələri ilə pəncərə yaradır.

### 12.6.4 Xətalar

| Kod | Nə vaxt |
|---|---|
| `ALQ-F001` | forma faylında sintaksis xətası |
| `ALQ-F002` | eyni adlı iki obyekt |
| `ALQ-F003` | naməlum vidjet növü (yaxın ad təklif olunur) |
| `ALQ-F004` | ⚠ vidjetdə olmayan xassə — nəzərə alınmır |
| `ALQ-F005` | konteyner olmayan vidjetin içində obyekt |
| `ALQ-F006` | hadisənin göstərdiyi metod komponentdə yoxdur |
| `ALQ-F007` | `forma Ad` komponentin adı ilə uyğun gəlmir |

Forma xətaları proqram açılarkən (komponent elan olunanda) göstərilir,
hadisə baş verəndə yox.

## 12.7 Mobil (gələcək — v2.0)

| Platforma | Yanaşma |
|---|---|
| Android | WASM + Capacitor qabığı, və ya yerli ARM binarı |
| iOS | WASM + WKWebView |

v1.0 üçün planlaşdırılmayıb.
