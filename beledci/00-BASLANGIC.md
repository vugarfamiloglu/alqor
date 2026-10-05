# Alqor Bələdçisi — 1. Başlanğıc

> Xoş gəlmisiniz! Bu bələdçi sizi heç nə bilmədiyiniz nöqtədən tam işlək
> veb və desktop proqramlar yazdığınız nöqtəyə aparacaq. Tamamilə Azərbaycan dilində.

---

## 1.1 Alqor nədir?

**Alqor** — tamamilə Azərbaycan dilində yazılan proqramlaşdırma dilidir.

```alqor
yaz("Adınızı daxil edin:")
dəyişən ad = oxu()

yaz("Yaşınızı daxil edin:")
dəyişən yaş = oxuTam()

əgər yaş >= 18 onda
    yaz("{ad}, siz yetkinsiniz.")
yoxsa
    yaz("{ad}, siz hələ yetkin deyilsiniz.")
son
```

Bu kodda **bir dənə də ingilis sözü yoxdur**. `if` yox — `əgər`. `print` yox — `yaz`.
Və `ə`, `ı`, `ş` hərfləri tam işləyir.

### Nə yaza bilərsiniz?

| Növ | Nümunə |
|---|---|
| **Konsol proqramları** | Hesablayıcılar, fayl emalı, avtomatlaşdırma skriptləri |
| **Veb saytlar və API-lər** | Onlayn mağaza, bloq, REST API |
| **Desktop tətbiqlər** | Quraşdırıcısı olan (`.deb`, `.AppImage`) proqramlar |
| **Kitabxanalar** | Başqalarının istifadə edəcəyi paketlər |

Hamısı **eyni dildə**, eyni sintaksislə.

---

## 1.2 Quraşdırma

### Linux (tövsiyə olunan)

```bash
curl -fsSL https://alqor.az/qur | sh
```

Və ya paket meneceri ilə:
```bash
# Ubuntu / Debian
sudo apt install alqor

# Fedora
sudo dnf install alqor

# Arch
yay -S alqor
```

### Yoxlama
```bash
alqor versiya
```
```
Alqor 1.0.0 (linux-x64)
Kompilyator: alqorc 1.0.0
```

### Windows istifadəçiləri üçün
Alqor Linux əsaslıdır. Windows-da işləmək üçün:
1. **WSL quraşdırın** (tövsiyə olunan):
   ```powershell
   wsl --install
   ```
   Kompüter yenidən başlayacaq, sonra Ubuntu açılacaq. Orada yuxarıdakı əmri işlədin.
2. Və ya **Alqor Studio**-nun Windows versiyasını yükləyin — içində hazır mühit var.

### macOS
```bash
brew install alqor
```

---

## 1.3 Alqor Studio (redaktor)

Kod yazmaq üçün hazır redaktor:

```bash
alqor studio
```

Və ya ayrıca yükləyin: `https://alqor.az/studio`

**Niyə Alqor Studio?**
- Azərbaycan hərflərini avtomatik yazır (`eger` yazırsınız → `əgər` olur)
- Nəticəni **yan paneldə canlı** göstərir — hər dəyişiklikdə yenilənir
- Xəta mesajları Azərbaycan dilində, düzəliş təklifi ilə
- Bir klikdə quraşdırıcı yaradır

> VS Code istifadə edirsinizsə: `Alqor` genişləndirməsini quraşdırın.

---

## 1.4 İlk proqramınız

### Addım 1 — Fayl yaradın
`salam.alqor` adlı fayl yaradın:

```alqor
yaz("Salam, dünya!")
```

### Addım 2 — İşə salın
```bash
alqor işlət salam.alqor
```

```
Salam, dünya!
```

**Təbriklər!** İlk Alqor proqramınızı yazdınız.

---

## 1.5 Azərbaycan hərflərini necə yazmaq?

Bu, çox vacib praktik məsələdir. **Üç yolunuz var:**

### Yol 1 — Avtomatik çevirmə (ən rahat)
Alqor Studio-da sadəcə ASCII yazın, redaktor özü çevirsin:

| Siz yazırsınız | Ekranda görünür |
|---|---|
| `eger` | `əgər` |
| `deyisen` | `dəyişən` |
| `ne qeder ki` | `nə qədər ki` |
| `ucun` | `üçün` |

### Yol 2 — Kompozisiya düyməsi
`;` sonra hərf:

| Yazırsınız | Alırsınız |
|---|---|
| `;e` | `ə` |
| `;i` | `ı` |
| `;o` | `ö` |
| `;u` | `ü` |
| `;c` | `ç` |
| `;s` | `ş` |
| `;g` | `ğ` |
| `;I` | `İ` |

### Yol 3 — Azərbaycan klaviatura düzümü
Linux-da sistem parametrlərindən:
**Parametrlər → Klaviatura → Dillər → Azərbaycan dili əlavə et**

Keçid: `Super + Boşluq`

### Yol 4 — ASCII yazın, sonra düzəldin
Kompilyator ASCII açar sözləri **qəbul edir** (xəbərdarlıqla), sonra bir əmrlə düzəldin:
```bash
alqorfmt --ascii-düzəlt .
```

> ⚠ **Diqqət:** Bu yalnız **açar sözlərə** aiddir. Dəyişən adlarında və
> mətnlərdə `yaş` və `yas` **fərqli** şeylərdir.

---

## 1.6 10 dəqiqəlik tur

### Dəyişənlər
```alqor
dəyişən ad = "Aysel"              // mətn
dəyişən yaş = 24                  // tam ədəd
dəyişən boy = 1.68                // onluq ədəd
dəyişən tələbədir = doğru         // məntiqi
dəyişən heçnə = boş               // dəyər yoxdur

sabit Pİ = 3.14159                // dəyişməz
```

### Ekrana yazmaq
```alqor
yaz("Salam")
yaz("Ad:", ad, "Yaş:", yaş)
yaz("Salam, {ad}! Sən {yaş} yaşındasan.")     // interpolyasiya
```

### Klaviaturadan oxumaq
```alqor
dəyişən ad = oxu("Adınız: ")
dəyişən yaş = oxuTam("Yaşınız: ")
dəyişən razı = oxuMəntiq("Razısınız? ")
```

### Şərt
```alqor
əgər yaş >= 18 onda
    yaz("Yetkin")
yoxsa əgər yaş >= 13 onda
    yaz("Yeniyetmə")
yoxsa
    yaz("Uşaq")
son
```

### Dövr
```alqor
// 1-dən 5-ə qədər
hər i üçün 1..5 içində
    yaz("Rəqəm: {i}")
son

// Siyahı üzərində
dəyişən meyvələr = ["alma", "armud", "üzüm"]
hər m üçün meyvələr içində
    yaz(m)
son

// Şərtlə
dəyişən i = 0
nə qədər ki i < 5
    yaz(i)
    i += 1
son

// Sayla
təkrarla 3 dəfə
    yaz("Salam")
son
```

### Funksiya
```alqor
funksiya salamla(ad: mətn)
    yaz("Salam, {ad}!")
son

funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son

salamla("Aysel")
yaz(topla(3, 4))              // 7
```

### Siyahı
```alqor
dəyişən s = [3, 1, 4, 1, 5]

s.əlavə(9)                    // sona əlavə
yaz(s[0])                     // 3
yaz(uzunluq(s))               // 6
yaz(s.sıralanmış())           // [1, 1, 3, 4, 5, 9]
yaz(s.cəm())                  // 23
yaz(s.filtr((x) => x > 3))    // [4, 5, 9]
```

### Lüğət
```alqor
dəyişən yaşlar = {"Aysel": 24, "Rəşad": 31}

yaz(yaşlar["Aysel"])          // 24
yaşlar["Nigar"] = 28

hər ad, yaş üçün yaşlar içində
    yaz("{ad}: {yaş}")
son
```

### Sinif
```alqor
sinif İnsan
    xassə ad: mətn
    xassə yaş: tam

    qurucu(ad: mətn, yaş: tam)
        özü.ad = ad
        özü.yaş = yaş
    son

    metod təqdim()
        yaz("Mən {özü.ad}, {özü.yaş} yaşım var.")
    son
son

dəyişən a = yeni İnsan("Aysel", 24)
a.təqdim()
```

### Xəta idarəetməsi
```alqor
cəhd et
    dəyişən n = tamƏt(oxu("Ədəd: "))
    yaz("İki qatı: {n * 2}")
tut (x: ÇevrilməXətası)
    yaz("Bu ədəd deyil!")
son
```

### Veb server (5 sətir!)
```alqor
gətir veb

dəyişən s = yeni veb.Server()
s.al("/", (sorğu) => veb.mətn("Salam, dünya!"))
s.dinlə(8080)
```

```bash
alqor işlət server.alqor
# http://localhost:8080 açın
```

### Desktop pəncərə
```alqor
gətir pəncərə

dəyişən p = yeni pəncərə.Pəncərə("Mənim Proqramım", 800, 600)
p.məzmun(<h1>Salam, dünya!</h1>)
p.göstər()
pəncərə.işlət()
```

---

## 1.7 Layihə yaratmaq

Tək fayldan böyük bir şey yazanda layihə qurun:

```bash
alqor yeni mənim-layihəm
cd mənim-layihəm
alqor işlət
```

Yaranan quruluş:
```
mənim-layihəm/
├── layihe.alqor          ← layihənin parametrləri
├── mənbə/
│   └── əsas.alqor        ← kodunuz buradadır
├── sınaq/
└── .gitignore
```

### Şablonlar
```bash
alqor yeni mənim-saytım --şablon veb
alqor yeni mənim-tətbiqim --şablon desktop
alqor yeni mənim-kitabxanam --şablon kitabxana
```

---

## 1.8 Faydalı əmrlər

| Əmr | Nə edir |
|---|---|
| `alqor işlət` | Proqramı dərhal işə salır |
| `alqor işlət --izlə` | Kod dəyişəndə avtomatik yenidən işlədir |
| `alqor qur` | Binar fayl yaradır |
| `alqor sına` | Testləri işlədir |
| `alqor format` | Kodu səliqəyə salır |
| `alqor yoxla` | Xətaları tapır (sürətli) |
| `alqor söhbət` | İnteraktiv rejim (REPL) |
| `alqor paketlə` | Quraşdırıcı yaradır |
| `alqor kömək` | Kömək |

---

## 1.9 Kömək almaq

| Mənbə | Ünvan |
|---|---|
| Sənədlər | `alqor.az/sened` |
| Xəta kodları lüğəti | `alqor.az/xeta` |
| Paketlər | `alqorhub.az` |
| İcma forumu | `forum.alqor.az` |
| Mənbə kodu | `github.com/alqor-dili/alqor` |

Terminal daxilində:
```bash
alqor kömək əgər             # dil konstruksiyası haqqında
alqor kömək siyahı.filtr     # funksiya haqqında
alqor kömək ALQ-T001         # xəta kodu haqqında
```

---

**Növbəti:** [2. Dil Dərsliyi](01-DIL-DERSLIYI.md) — addım-addım öyrənmə
