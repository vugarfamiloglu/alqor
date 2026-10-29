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
| **Desktop tətbiqlər** | Pəncərəli proqramlar — menyu, dialoq, 118 hazır element |
| **Kitabxanalar** | Başqalarının istifadə edəcəyi paketlər |

Hamısı **eyni dildə**, eyni sintaksislə.

---

## 1.2 Quraşdırma

Alqor-un hazırkı versiyası Python üzərində işləyən etalon
implementasiyadır. Lazım olan yeganə şey **Python 3.12 və ya yenisi**.

### Windows

1. [python.org/downloads](https://www.python.org/downloads/) ünvanından
   Python 3.12+ yükləyin. Quraşdırarkən **"Add python.exe to PATH"**
   qutusunu işarələyin.
2. Alqor-u yükləyin (Git varsa):
   ```powershell
   git clone https://github.com/vugarfamiloglu/alqor.git
   cd alqor
   ```
3. Yoxlayın:
   ```powershell
   .\alqor.cmd versiya
   ```

`alqor` əmrini istənilən qovluqdan işlətmək üçün `alqor` qovluğunu
PATH-a əlavə edin: **Başlat → "mühit dəyişənləri" → Path → Yeni →**
qovluğun tam yolu. Bundan sonra yeni PowerShell pəncərəsində sadəcə
`alqor versiya` yazmaq kifayətdir.

> WSL **lazım deyil** — Alqor Windows-da birbaşa işləyir. Konsol
> kodlaşdırması (cp1251) avtomatik UTF-8-ə keçirilir.

### Linux və macOS

```bash
git clone https://github.com/vugarfamiloglu/alqor.git
cd alqor
./alqor versiya
echo 'export PATH="$PATH:'"$(pwd)"'"' >> ~/.bashrc     # alqor əmri hər yerdə
```

Python yoxdursa: `sudo apt install python3` (Ubuntu/Debian),
`sudo dnf install python3` (Fedora), `brew install python` (macOS).
Desktop dialoqları üçün Linux-da: `sudo apt install python3-tk`.

### Yoxlama

```
$ alqor versiya
Alqor 2.5.1
Etalon implementasiya — Python 3.12.3
```

> **Gələcək:** `apt install alqor`, `brew install alqor` və Windows
> quraşdırıcısı — paket meneceri və quraşdırıcı generatoru hazır
> olanda.

---

## 1.3 Alqor Studio (redaktor)

Kod yazmaq üçün hazır redaktor:

```bash
alqor studio                  # cari qovluğu açır
alqor studio mənim-layihəm    # başqa qovluğu
```

Windows-da sadəcə `Studio-ac.cmd` faylına iki dəfə klikləyin.

**Niyə Alqor Studio?**
- Azərbaycan hərflərini avtomatik yazır (`eger` yazırsınız → `əgər`
  olur; `;e` → `ə`)
- Xətaları yazdıqca göstərir — Azərbaycan dilində
- **F5** — proqramı işə salır, **F6** — interfeysin canlı önbaxışı
- **Ctrl+Shift+F** — kodu səliqəyə salır
- Elementlər panelində 118 hazır element: **iki klik** — işləməsi üçün
  lazım olan kod özü yazılır
- **Xüsusiyyətlər** paneli — elementin mətnini, rəngini, kənarını,
  şriftini kod yazmadan dəyişin, önbaxışda dərhal görünür

---

## 1.4 İlk proqramınız

### Addım 1 — Fayl yaradın
`salam.alq` adlı fayl yaradın:

```alqor
yaz("Salam, dünya!")
```

### Addım 2 — İşə salın
```bash
alqor işlət salam.alq
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
alqor işlət server.alq
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

## 1.6½ İnteraktiv rejim — dili dərhal sınayın

Fayl yaratmadan dili sınamaq üçün:

```bash
alqor söhbət
```

```
alqor> 2 + 2
4  // tam

alqor> "ışıq".böyüyə()
"IŞIQ"  // mətn

alqor> hər i üçün 1..3 içində
  ...     yaz("Rəqəm: {i}")
  ... son
Rəqəm: 1
Rəqəm: 2
Rəqəm: 3
```

Bloklar avtomatik davam edir — `onda`, `içində` yazıb Enter basın,
`  ...` sətri görünəcək. `son` yazanda kod işləyəcək.

Faydalı əmrlər:

| Əmr | Nə edir |
|---|---|
| `:kömək` | bütün əmrlər |
| `:hərflər` | Azərbaycan hərfləri və ASCII qarşılıqları |
| `:tip <ifadə>` | ifadənin tipi |
| `:siyahı` | təyin etdiyiniz adlar |
| `:yüklə <fayl>` | faylı seansa yüklə |
| `:çıx` | çıxış (Ctrl+D də işləyir) |

> Son nəticə `nəticə` dəyişənində saxlanılır:
> `alqor> 10 * 5` → `50`, sonra `alqor> nəticə + 1` → `51`

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
├── layihe.alq          ← layihənin parametrləri
├── mənbə/
│   └── əsas.alq        ← kodunuz buradadır
├── sınaq/
│   └── əsas_sınaq.alq  ← sınaqlar (`alqor sına`)
├── README.md
└── .gitignore
```

### Şablonlar
```bash
alqor yeni mənim-saytım --şablon veb
alqor yeni mənim-tətbiqim --şablon desktop
alqor yeni mənim-kitabxanam --şablon kitabxana
```

Hər şablonun hazır sınaqları var — `alqor sına` ilk gündən yaşıl
nəticə verir.

### Sınaq yazmaq

```alqor
gətir test
gətir "../mənbə/əsas.alq" kimi proqram

@sınaq("salamla adı yerləşdirir")
funksiya salamlama()
    test.bərabər(proqram.salamla("Aysel"), "Salam, Aysel!")
son
```

```
$ alqor sına

  sınaq/əsas_sınaq.alq
    ✓ salamla adı yerləşdirir                    0.1ms

  Nəticə: 1 uğurlu, 0 uğursuz, 0 xəta, 0 atlanmış
```

---

## 1.8 Faydalı əmrlər

| Əmr | Nə edir |
|---|---|
| `alqor işlət [fayl]` | Proqramı işə salır (layihədə fayl lazım deyil) |
| `alqor söhbət` | **İnteraktiv rejim (REPL)** — dili sınamağın ən tez yolu |
| `alqor yeni <ad>` | Yeni layihə |
| `alqor sına` | Sınaqları işlədir (`--sənəd` — sənəddəki nümunələri də) |
| `alqor format .` | Kodu səliqəyə salır (`--yoxla` — yalnız yoxlayır) |
| `alqor yoxla .` | Xətaları tapır (tiplər də daxil), işə salmadan |
| `alqor sənəd` | `///` şərhlərindən HTML sənəd (`sənəd/indeks.html`) |
| `alqor qur` | `qurma/<ad>.pyz` — tək fayllı paket, başqa kompüterdə `python ad.pyz` |
| `alqor studio` | Alqor Studio |
| `alqor kömək` | Bütün əmrlər |

---

## 1.9 Kömək almaq

| Mənbə | Ünvan |
|---|---|
| Mənbə kodu və sənədlər | [github.com/vugarfamiloglu/alqor](https://github.com/vugarfamiloglu/alqor) |
| Spesifikasiya | `spesifikasiya/` qovluğu |
| Bu bələdçi | `beledci/` qovluğu |

Xəta kodlarının izahı: [6. Xəta Lüğəti](05-XETA-LUGETI.md).

---

**Növbəti:** [2. Dil Dərsliyi](01-DIL-DERSLIYI.md) — addım-addım öyrənmə
