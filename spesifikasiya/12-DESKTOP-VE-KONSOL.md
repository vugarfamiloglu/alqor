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
alqor işlət salam.alqor          # dərhal işlət (VM)
alqor qur salam.alqor            # binar yarat
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

    seç arq.dəyər("əməliyyat")
        hal "topla" → yaz(cəm(arq.siyahı("ədədlər")))
        hal "çıx" → ...
    son
son
```

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

konsol.qırmızı("Xəta!")
konsol.yaşıl("Uğurlu")
konsol.sarı("Xəbərdarlıq")
konsol.mavi("Məlumat")
konsol.qalın("Vacib")
konsol.altXətt("Vurğulanmış")
konsol.rəng("mətn", ön: "qırmızı", arxa: "ağ")

konsol.təmizlə()
konsol.kursor(5, 10)
konsol.ölçü() -> kortej[tam, tam]
```

### İnteraktiv elementlər
```alqor
dəyişən ad = konsol.soruş("Adınız: ")
dəyişən parol = konsol.parolSoruş("Parol: ")
dəyişən razı = konsol.təsdiqlə("Davam edilsin?")
dəyişən seçim = konsol.seç("Rəng seçin:", ["Qırmızı", "Yaşıl", "Mavi"])
dəyişən çoxlu = konsol.çoxSeç("Nə lazımdır?", ["A", "B", "C"])

// İrəliləyiş göstəricisi
dəyişən p = konsol.irəliləyiş(100, "Yüklənir")
hər i üçün 1..100 içində
    p.yenilə(i)
    emal(i)
son
p.bitir()

// Fırlanan göstərici
dəyişən f = konsol.fırlanan("İşlənir...")
gözlə uzunƏməliyyat()
f.dayandır("Bitdi ✓")

// Cədvəl
konsol.cədvəl(
    ["Ad", "Yaş", "Şəhər"],
    [["Aysel", "24", "Bakı"], ["Rəşad", "31", "Gəncə"]]
)
```

---

## 12.2 Desktop tətbiqləri

### Arxitektura
Alqor desktop tətbiqləri **WebKitGTK** əsaslı yerli pəncərədə işləyir:
- İnterfeys: Alqor komponentləri → HTML/CSS (brauzerdəki ilə **eyni kod**)
- Məntiq: yerli kod (tam sistem girişi: fayl, şəbəkə, proses)
- Nəticə: tək fayllı binar, Electron-dan **~10 dəfə kiçik**

### Ən sadə pəncərə
```alqor
gətir pəncərə

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Mənim Proqramım", 800, 600)

    p.məzmun(
        <div sinif="əsas">
            <h1>Salam, dünya!</h1>
            <button klik={() => yaz("Basıldı")}>Bas mənə</button>
        </div>
    )

    p.göstər()
    pəncərə.işlət()
son
```

### Pəncərə xassələri
```alqor
p.başlıq("Yeni başlıq")
p.ölçü(1024, 768)
p.minimumÖlçü(400, 300)
p.maksimumÖlçü(1920, 1080)
p.mərkəzə()
p.tamEkran(doğru)
p.maksimumlaşdır()
p.minimumlaşdır()
p.dəyişdirilə(yanlış)
p.həmişəÜstdə(doğru)
p.şəffaflıq(0.95)
p.çərçivəsiz(doğru)
p.ikon("statik/ikon.png")
p.mövzu("qaranlıq")              // işıqlı | qaranlıq | sistem
p.bağla()

// Hadisələr
p.hadisə("bağlanır", funksiya(h)
    əgər dəyişiklikVar onda
        h.ləğvEt()               // bağlanmanı dayandır
        saxlaməyiSoruş()
    son
son)
p.hadisə("ölçüDəyişdi", (en, hündürlük) => ...)
p.hadisə("fokus", ...)
```

### Yerli dialoqlar
```alqor
gətir pəncərə.dialoq

dialoq.məlumat("Başlıq", "Mesaj")
dialoq.xəbərdarlıq("Diqqət", "Nəsə düz deyil")
dialoq.xəta("Xəta", "Əməliyyat alınmadı")
dəyişən təsdiq = dialoq.təsdiqlə("Silinsin?", "Bu geri qaytarıla bilməz")

dəyişən yol = dialoq.faylAç(
    başlıq: "Fayl seçin",
    filtrlər: [("Mətn faylları", ["txt", "md"]), ("Hamısı", ["*"])]
)
dəyişən yollar = dialoq.faylAçÇoxlu()
dəyişən saxla = dialoq.faylSaxla(standartAd: "sənəd.txt")
dəyişən qovluq = dialoq.qovluqSeç()
dəyişən rəng = dialoq.rəngSeç()
```

### Menyu
```alqor
p.menyu([
    pəncərə.menyu("Fayl", [
        pəncərə.element("Yeni", qısayol: "Ctrl+N", klik: yeniFayl),
        pəncərə.element("Aç...", qısayol: "Ctrl+O", klik: faylAç),
        pəncərə.element("Saxla", qısayol: "Ctrl+S", klik: saxla),
        pəncərə.ayırıcı(),
        pəncərə.element("Çıxış", qısayol: "Ctrl+Q", klik: () => p.bağla())
    ]),
    pəncərə.menyu("Redaktə", [
        pəncərə.element("Geri al", qısayol: "Ctrl+Z"),
        pəncərə.element("İrəli al", qısayol: "Ctrl+Shift+Z")
    ]),
    pəncərə.menyu("Kömək", [
        pəncərə.element("Haqqında", klik: haqqında)
    ])
])
```

### Sistem treyi
```alqor
dəyişən trey = pəncərə.trey("statik/ikon.png")
trey.məsləhət("Proqram işləyir")
trey.menyu([
    pəncərə.element("Göstər", klik: () => p.göstər()),
    pəncərə.element("Çıxış", klik: () => pəncərə.dayandır())
])
trey.hadisə("klik", () => p.göstər())
```

### Sistem bildirişləri
```alqor
pəncərə.bildiriş("Başlıq", "Mesaj", ikon: "statik/ikon.png")
```

### Qlobal qısayollar
```alqor
pəncərə.qlobalQısayol("Ctrl+Shift+A", funksiya()
    p.göstər()
son)
```

### Yerli sistemə giriş
```alqor
// Desktop tətbiqində bütün standart kitabxana əlçatandır
gətir fayl
gətir sistem
gətir proses

dəyişən m = fayl.oxu("/etc/hostname")
sistem.əmr("notify-send 'Salam'")
proses.başlat("firefox", ["https://alqor.az"])
```

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
`layihe.alqor`:
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

```alqor
// ortaq/interfeys.alqor
komponent TapşırıqSiyahısı
    vəziyyət tapşırıqlar: siyahı[Tapşırıq] = []

    göstər()
        qaytar <div sinif="siyahı">
            {özü.tapşırıqlar.çevir((t) =>
                <div sinif="tapşırıq">{t.mətn}</div>
            )}
        </div>
    son
son
```

```alqor
// veb.alqor
gətir veb.ön
ön.quraşdır(TapşırıqSiyahısı, "#kök")
```

```alqor
// desktop.alqor
gətir pəncərə
dəyişən p = yeni pəncərə.Pəncərə("Tapşırıqlar", 600, 800)
p.məzmun(<TapşırıqSiyahısı />)
p.göstər()
```

```alqor
// konsol.alqor
hər t üçün tapşırıqlar içində
    yaz("• {t.mətn}")
son
```

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

## 12.6 Mobil (gələcək — v2.0)

| Platforma | Yanaşma |
|---|---|
| Android | WASM + Capacitor qabığı, və ya yerli ARM binarı |
| iOS | WASM + WKWebView |

v1.0 üçün planlaşdırılmayıb.
