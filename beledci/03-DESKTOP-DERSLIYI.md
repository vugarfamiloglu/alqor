# Alqor Bələdçisi — 4. Desktop Dərsliyi

> Bu dərslikdə quraşdırıcısı olan, Linux-da işləyən desktop tətbiq quracağıq:
> **Mətn Redaktoru**.

---

## 4.1 Necə işləyir?

Alqor desktop tətbiqləri **yerli pəncərə + veb texnologiyası** modelindən istifadə edir:

```
┌──────────────────────────────────────┐
│  Yerli pəncərə (GTK)                 │
│  ┌────────────────────────────────┐  │
│  │  WebKitGTK görünüşü            │  │
│  │  ← interfeys (Alqor → HTML)    │  │
│  └────────────────────────────────┘  │
│         ↕ birbaşa çağırış            │
│  Alqor yerli kodu                    │
│  ← fayl, şəbəkə, proses, hər şey     │
└──────────────────────────────────────┘
```

| | Alqor | Electron |
|---|---|---|
| Binar ölçüsü | ~8 MB | ~120 MB |
| RAM istifadəsi | ~50 MB | ~200 MB |
| Başlama vaxtı | ~0.2 s | ~2 s |
| Brauzer motoru | sistemin WebKitGTK-sı | öz Chromium-u |

**Ən vacibi:** interfeys kodu veb versiyası ilə **eynidir**.

---

## 4.2 Layihə yaratmaq

```bash
alqor yeni mətn-redaktoru --şablon desktop
cd mətn-redaktoru
alqor işlət
```

Pəncərə açılır. Kodu dəyişdirin — pəncərə avtomatik yenilənir.

---

## 4.3 İlk pəncərə

`mənbə/əsas.alqor`:
```alqor
gətir pəncərə

funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Mətn Redaktoru", 1000, 700)

    p.məzmun(
        <div sinif="tətbiq">
            <h1>Salam, dünya!</h1>
        </div>
    )

    p.göstər()
    pəncərə.işlət()
son
```

---

## 4.4 Üslub

`statik/üslub.css`:
```css
:root {
    --fon: #ffffff;
    --mətn: #1a1a1a;
    --kənar: #d0d0d0;
    --vurğu: #c0392b;
}

@media (prefers-color-scheme: dark) {
    :root {
        --fon: #1e1e1e;
        --mətn: #e8e8e8;
        --kənar: #3a3a3a;
    }
}

body {
    margin: 0;
    font-family: system-ui, sans-serif;
    background: var(--fon);
    color: var(--mətn);
}

.redaktor {
    width: 100%;
    height: calc(100vh - 40px);
    border: none;
    outline: none;
    padding: 16px;
    font-family: "JetBrains Mono", monospace;
    font-size: 14px;
    background: var(--fon);
    color: var(--mətn);
    resize: none;
}

.statusZolağı {
    height: 24px;
    padding: 4px 12px;
    border-top: 1px solid var(--kənar);
    font-size: 12px;
    display: flex;
    justify-content: space-between;
}
```

---

## 4.5 Tam redaktor komponenti

```alqor
gətir pəncərə
gətir pəncərə.dialoq
gətir fayl

komponent Redaktor
    vəziyyət məzmun: mətn = ""
    vəziyyət faylYolu: mətn? = boş
    vəziyyət dəyişib: məntiq = yanlış

    hesablanan başlıq: mətn
        dəyişən ad = əgər özü.faylYolu boş deyil onda
            yol.fayl(özü.faylYolu!)
        yoxsa
            "Adsız"
        son
        qaytar əgər özü.dəyişib onda "● {ad}" yoxsa ad son
    son

    hesablanan statistika: mətn
        dəyişən sətirlər = uzunluq(özü.məzmun.sətirlər())
        dəyişən sözlər = uzunluq(özü.məzmun.sözlər())
        dəyişən simvollar = özü.məzmun.uzunluq()
        qaytar "{sətirlər} sətir · {sözlər} söz · {simvollar} simvol"
    son

    metod yeni()
        əgər deyil özü.saxlanmasınıSoruş() onda qaytar son
        özü.məzmun = ""
        özü.faylYolu = boş
        özü.dəyişib = yanlış
    son

    metod aç()
        əgər deyil özü.saxlanmasınıSoruş() onda qaytar son

        varsa yol = dialoq.faylAç(
            başlıq: "Fayl aç",
            filtrlər: [
                ("Mətn faylları", ["txt", "md", "alqor"]),
                ("Bütün fayllar", ["*"])
            ]
        ) onda
            cəhd et
                özü.məzmun = fayl.oxu(yol)
                özü.faylYolu = yol
                özü.dəyişib = yanlış
            tut (x: Xəta)
                dialoq.xəta("Xəta", "Fayl oxunmadı: {x.mesaj}")
            son
        son
    son

    metod saxla() -> məntiq
        əgər özü.faylYolu boşdur onda
            qaytar özü.fərqliSaxla()
        son
        cəhd et
            fayl.yaz(özü.faylYolu!, özü.məzmun)
            özü.dəyişib = yanlış
            qaytar doğru
        tut (x: Xəta)
            dialoq.xəta("Xəta", "Fayl yazılmadı: {x.mesaj}")
            qaytar yanlış
        son
    son

    metod fərqliSaxla() -> məntiq
        varsa yol = dialoq.faylSaxla(standartAd: "adsız.txt") onda
            özü.faylYolu = yol
            qaytar özü.saxla()
        son
        qaytar yanlış
    son

    metod saxlanmasınıSoruş() -> məntiq
        əgər deyil özü.dəyişib onda qaytar doğru son

        seç dialoq.üçVariant(
            "Dəyişikliklər saxlanılsın?",
            "Saxlanmamış dəyişiklikləriniz var.",
            ["Saxla", "Saxlama", "Ləğv et"]
        )
            hal "Saxla" → qaytar özü.saxla()
            hal "Saxlama" → qaytar doğru
            digər hallarda → qaytar yanlış
        son
    son

    göstər()
        qaytar <div sinif="tətbiq">
            <textarea
                sinif="redaktor"
                dəyər={özü.məzmun}
                dəyişdi={(d) => blok
                    özü.məzmun = d
                    özü.dəyişib = doğru
                son}
                yerTutucu="Yazmağa başlayın..." />

            <div sinif="statusZolağı">
                <span>{özü.başlıq}</span>
                <span>{özü.statistika}</span>
            </div>
        </div>
    son
son
```

---

## 4.6 Menyu

```alqor
funksiya əsas()
    dəyişən p = yeni pəncərə.Pəncərə("Mətn Redaktoru", 1000, 700)
    dəyişən r = yeni Redaktor()

    p.menyu([
        pəncərə.menyu("Fayl", [
            pəncərə.element("Yeni", qısayol: "Ctrl+N", klik: r.yeni),
            pəncərə.element("Aç...", qısayol: "Ctrl+O", klik: r.aç),
            pəncərə.ayırıcı(),
            pəncərə.element("Saxla", qısayol: "Ctrl+S", klik: r.saxla),
            pəncərə.element("Fərqli saxla...", qısayol: "Ctrl+Shift+S",
                            klik: r.fərqliSaxla),
            pəncərə.ayırıcı(),
            pəncərə.element("Çıxış", qısayol: "Ctrl+Q", klik: () => p.bağla())
        ]),

        pəncərə.menyu("Redaktə", [
            pəncərə.element("Geri al", qısayol: "Ctrl+Z"),
            pəncərə.element("İrəli al", qısayol: "Ctrl+Shift+Z"),
            pəncərə.ayırıcı(),
            pəncərə.element("Kəs", qısayol: "Ctrl+X"),
            pəncərə.element("Kopyala", qısayol: "Ctrl+C"),
            pəncərə.element("Yapışdır", qısayol: "Ctrl+V"),
            pəncərə.ayırıcı(),
            pəncərə.element("Tap...", qısayol: "Ctrl+F", klik: tapDialoqu)
        ]),

        pəncərə.menyu("Görünüş", [
            pəncərə.seçimElement("Qaranlıq mövzu", seçilib: yanlış,
                                 klik: (s) => p.mövzu(əgər s onda "qaranlıq"
                                                      yoxsa "işıqlı" son)),
            pəncərə.element("Tam ekran", qısayol: "F11",
                            klik: () => p.tamEkran(doğru))
        ]),

        pəncərə.menyu("Kömək", [
            pəncərə.element("Haqqında", klik: funksiya()
                dialoq.məlumat("Mətn Redaktoru",
                               "Versiya 1.0.0\nAlqor dilində yazılıb")
            son)
        ])
    ])

    // Bağlanmazdan əvvəl soruş
    p.hadisə("bağlanır", funksiya(h)
        əgər deyil r.saxlanmasınıSoruş() onda
            h.ləğvEt()
        son
    son)

    p.məzmun(<Redaktor />)
    p.göstər()
    pəncərə.işlət()
son
```

---

## 4.7 Dialoqlar

```alqor
gətir pəncərə.dialoq

dialoq.məlumat("Başlıq", "Mesaj")
dialoq.xəbərdarlıq("Diqqət", "Nəsə düz deyil")
dialoq.xəta("Xəta", "Əməliyyat alınmadı")

dəyişən təsdiq = dialoq.təsdiqlə("Silinsin?", "Geri qaytarıla bilməz")
dəyişən variant = dialoq.üçVariant("Başlıq", "Mesaj", ["Hə", "Yox", "Ləğv"])

dəyişən yol = dialoq.faylAç(filtrlər: [("Şəkillər", ["png", "jpg"])])
dəyişən yollar = dialoq.faylAçÇoxlu()
dəyişən saxla = dialoq.faylSaxla(standartAd: "sənəd.txt")
dəyişən qovluq = dialoq.qovluqSeç()
dəyişən rəng = dialoq.rəngSeç()
dəyişən mətn = dialoq.mətnSoruş("Ad", "Faylın adı:", standart: "yeni.txt")
```

---

## 4.8 Sistem treyi və bildirişlər

```alqor
dəyişən trey = pəncərə.trey("statik/ikon.png")
trey.məsləhət("Mətn Redaktoru")
trey.menyu([
    pəncərə.element("Göstər", klik: () => p.göstər()),
    pəncərə.element("Gizlət", klik: () => p.gizlət()),
    pəncərə.ayırıcı(),
    pəncərə.element("Çıxış", klik: () => pəncərə.dayandır())
])

// Bildiriş
pəncərə.bildiriş("Saxlanıldı", "Fayl uğurla yazıldı")
```

---

## 4.9 Qlobal qısayollar

```alqor
pəncərə.qlobalQısayol("Ctrl+Alt+N", funksiya()
    p.göstər()
    r.yeni()
son)
```

---

## 4.10 Konfiqurasiya saxlamaq

```alqor
gətir konfiq

dəyişən k = konfiq.istifadəçi("mətn-redaktoru")
// Linux-da: ~/.config/mətn-redaktoru/konfiq.toml

k.qoy("mövzu", "qaranlıq")
k.qoy("şriftÖlçüsü", 14)
k.qoy("sonFayllar", ["a.txt", "b.txt"])
k.saxla()

dəyişən mövzu = k.al("mövzu", "işıqlı")
dəyişən ölçü = k.alTam("şriftÖlçüsü", 12)
```

---

## 4.11 Yerli sistemə tam giriş

Veb tətbiqlərindən fərqli olaraq, desktop tətbiqində **hər şeyə** çıxış var:

```alqor
gətir fayl
gətir sistem
gətir proses

// Fayl sistemi
dəyişən fayllar = qovluq.siyahı(qovluq.ev())

// Xarici proses
proses.başlat("xdg-open", [yol])          // faylı sistem proqramı ilə aç
dəyişən çıxış = sistem.əmr("git status")

// Mühit
yaz(sistem.istifadəçi())
yaz(sistem.platforma())

// Buferə kopyalamaq
pəncərə.panoyaYaz("mətn")
dəyişən m = pəncərə.panodanOxu()

// Faylı izləmək
qovluq.izlə("/home/v/sənədlər", funksiya(hadisə, yol)
    yaz("{hadisə}: {yol}")
son)
```

---

## 4.12 Quraşdırıcı yaratmaq

`layihe.alqor`:
```toml
[paket]
ad = "metn-redaktoru"
versiya = "1.0.0"
təsvir = "Sadə və sürətli mətn redaktoru"
müəllif = ["Vüqar Qənbərov <vuqar@nümunə.az>"]
lisenziya = "MIT"

[desktop]
pəncərə_başlıq = "Mətn Redaktoru"
en = 1000
hündürlük = 700
ikon = "statik/ikon.png"

[paketləmə.deb]
bölmə = "editors"
memarlıq = "amd64"
asılılıqlar = ["libwebkit2gtk-4.1-0", "libgtk-3-0"]
masaüstü_faylı = doğru
menyu_kateqoriya = "Utility;TextEditor"

[paketləmə.appimage]
kateqoriya = "Utility"

[paketləmə.flatpak]
id = "az.numune.MetnRedaktoru"
```

### Paketləmə
```bash
alqor paketlə --hədəf deb
alqor paketlə --hədəf appimage
alqor paketlə --hədəf flatpak
alqor paketlə --hamısı
```

Nəticə:
```
qurma/paket/
├── metn-redaktoru_1.0.0_amd64.deb         (9.1 MB)
├── MetnRedaktoru-1.0.0-x86_64.AppImage    (11.3 MB)
└── az.numune.MetnRedaktoru.flatpak        (10.7 MB)
```

### Quraşdırma
```bash
# Debian / Ubuntu
sudo apt install ./metn-redaktoru_1.0.0_amd64.deb

# AppImage — quraşdırmaq lazım deyil
chmod +x MetnRedaktoru-1.0.0-x86_64.AppImage
./MetnRedaktoru-1.0.0-x86_64.AppImage

# Flatpak
flatpak install az.numune.MetnRedaktoru.flatpak
```

Quraşdırıldıqdan sonra proqram sistem menyusunda görünür.

---

## 4.13 Windows üçün çarpaz-kompilyasiya

```bash
alqor paketlə --hədəf windows-nsis
```
Nəticə: `qurma/paket/MetnRedaktoru-1.0.0-setup.exe`

> Windows-da WebView2 istifadə olunur (Windows 10/11-də hazır var).

---

## 4.14 Avtomatik yeniləmə

```alqor
gətir yeniləmə

asinxron funksiya yeniləməYoxla()
    cəhd et
        dəyişən y = gözlə yeniləmə.yoxla("https://nümunə.az/yenilik.json")

        əgər deyil y.vardır onda qaytar son

        əgər dialoq.təsdiqlə(
            "Yenilik var",
            "Versiya {y.versiya} mövcuddur. İndi yüklənsin?"
        ) onda
            dəyişən irəli = pəncərə.irəliləyişDialoqu("Yüklənir...")
            gözlə y.yüklə((faiz) => irəli.yenilə(faiz))
            irəli.bağla()

            əgər dialoq.təsdiqlə("Hazırdır", "Proqram yenidən başladılsın?") onda
                yeniləmə.quraşdırVəYenidənBaşlat()
            son
        son
    tut (x: Xəta)
        jurnal.xəbərdarlıq("Yeniləmə yoxlanmadı: {x.mesaj}")
    son
son
```

---

## 4.15 Eyni koddan üç tətbiq

```
mətn-redaktoru/
├── mənbə/
│   ├── ortaq/
│   │   └── redaktor.alqor      ← komponent (interfeys + məntiq)
│   ├── desktop.alqor           ← pəncərə.Pəncərə(...)
│   ├── veb.alqor               ← ön.quraşdır(...)
│   └── konsol.alqor            ← terminal versiyası
```

```bash
alqor qur --giriş mənbə/desktop.alqor --hədəf linux-x64
alqor qur --giriş mənbə/veb.alqor --hədəf veb
alqor qur --giriş mənbə/konsol.alqor --hədəf linux-x64
```

**Bir interfeys kodu — üç platforma.**

---

**Növbəti:** [5. Köçürmə Bələdçisi](04-KOCURME-BELEDCISI.md)
