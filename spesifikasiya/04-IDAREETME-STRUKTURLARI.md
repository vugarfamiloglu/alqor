# Alqor — Bölmə 4: İdarəetmə Strukturları

---

## 4.1 Şərt — `əgər`

### Sintaksis
```
əgər <şərt> onda
    <gövdə>
[yoxsa əgər <şərt> onda
    <gövdə>]...
[yoxsa
    <gövdə>]
son
```

### Nümunələr
```alqor
əgər yaş >= 18 onda
    yaz("Yetkin")
son

əgər yaş >= 18 onda
    yaz("Yetkin")
yoxsa
    yaz("Uşaq")
son

əgər bal >= 90 onda
    yaz("Əla")
yoxsa əgər bal >= 70 onda
    yaz("Yaxşı")
yoxsa əgər bal >= 50 onda
    yaz("Kafi")
yoxsa
    yaz("Qeyri-kafi")
son
```

### `əks halda` — uzun forma
`yoxsa` ilə tamamilə eynidir, oxunaqlılıq üçün:
```alqor
əgər x > 0 onda
    yaz("müsbət")
əks halda
    yaz("müsbət deyil")
son
```

### Tək sətirlik forma
```alqor
əgər x > 0 onda yaz("müsbət") son
əgər x > 0 onda yaz("müsbət") yoxsa yaz("mənfi") son
```

### İfadə kimi
```alqor
dəyişən nəticə = əgər x > 0 onda "müsbət" yoxsa "mənfi" son
```

### `varsa` — ixtiyari dəyərin bağlanması
```alqor
varsa istifadəçi = tapİstifadəçi(id) onda
    yaz(istifadəçi.ad)            // istifadəçi burada boş deyil
yoxsa
    yaz("Tapılmadı")
son

// Çoxlu bağlama
varsa a = tap1(), b = tap2() onda
    yaz(a, b)                      // ikisi də boş deyilsə
son

// Əlavə şərtlə
varsa i = tapİstifadəçi(id), i.aktivdir onda
    yaz("aktiv istifadəçi")
son
```

### `yoxdursa` — erkən çıxış
```alqor
funksiya emal(id: tam)
    yoxdursa istifadəçi = tapİstifadəçi(id) onda
        yaz("tapılmadı")
        qaytar                     // bu blok mütləq çıxmalıdır
    son
    // istifadəçi burada görünür və boş deyil
    yaz(istifadəçi.ad)
son
```

### Şərt tipi
Şərt **mütləq `məntiq`** olmalıdır:
```alqor
əgər 1 onda ... son              // ✖ ALQ-T007
əgər siyahı onda ... son         // ✖ ALQ-T007
əgər uzunluq(siyahı) > 0 onda ... son    // ✓
əgər siyahı boş deyil onda ... son       // ✓
```

---

## 4.2 Çoxvariantlı seçim — `seç`

### Sintaksis
```
seç <ifadə>
    hal <naxış>[, <naxış>]...
        <gövdə>
    ...
    [digər hallarda
        <gövdə>]
son
```

### Əsas istifadə
```alqor
seç gün
    hal 1
        yaz("Bazar ertəsi")
    hal 2
        yaz("Çərşənbə axşamı")
    hal 6, 7
        yaz("Həftəsonu")
    digər hallarda
        yaz("Naməlum gün")
son
```

> **Keçid yoxdur** — hər `hal` avtomatik bitir. Qəsdən keçid üçün `keç` açar sözü:
> ```alqor
> hal 1
>     yaz("bir")
>     keç            // növbəti hala keçir
> hal 2
>     yaz("iki")
> ```

### Qısa ox forması
```alqor
seç gün
    hal 1 → yaz("Bazar ertəsi")
    hal 6, 7 → yaz("Həftəsonu")
    digər hallarda → yaz("İş günü")
son
```

### Diapazonla
```alqor
seç bal
    hal 90..100 → yaz("Əla")
    hal 70..<90 → yaz("Yaxşı")
    hal 50..<70 → yaz("Kafi")
    digər hallarda → yaz("Qeyri-kafi")
son
```

### Şərtli `seç` (ifadəsiz)
```alqor
seç
    hal yaş < 13 → yaz("uşaq")
    hal yaş < 20 → yaz("yeniyetmə")
    hal yaş < 65 → yaz("yetkin")
    digər hallarda → yaz("ahıl")
son
```

### Tipə görə seçim
```alqor
seç tipi dəyər
    hal tam → yaz("ədəd: {dəyər}")
    hal mətn → yaz("mətn: {dəyər}")
    hal siyahı[tam] → yaz("siyahı, {uzunluq(dəyər)} element")
    hal boş → yaz("dəyər yoxdur")
    digər hallarda → yaz("naməlum tip")
son
```

### Naxış uyğunlaşdırma (pattern matching)
```alqor
seç nöqtə
    hal (0, 0) → yaz("başlanğıc")
    hal (x, 0) → yaz("X oxunda: {x}")
    hal (0, y) → yaz("Y oxunda: {y}")
    hal (x, y) əgər x == y → yaz("diaqonalda")
    hal (x, y) → yaz("({x}, {y})")
son

// Siyahı naxışı
seç siyahı
    hal [] → yaz("boş")
    hal [tək] → yaz("bir element: {tək}")
    hal [ilk, ...qalan] → yaz("ilk: {ilk}, qalan: {uzunluq(qalan)}")
son

// Obyekt naxışı
seç hadisə
    hal Klik{x, y} → yaz("klik ({x},{y})")
    hal DüyməBasma{kod: 27} → yaz("Escape")
    hal DüyməBasma{kod} → yaz("düymə {kod}")
son
```

### Tamlıq yoxlaması
`sadalama` və ya `məntiq` üzərində `seç` bütün halları əhatə etməlidir,
yoxsa `digər hallarda` tələb olunur (`ALQ-T031`).

### İfadə kimi
```alqor
dəyişən ad = seç gün
    hal 1 → "Bazar ertəsi"
    hal 2 → "Çərşənbə axşamı"
    digər hallarda → "Digər"
son
```

---

## 4.3 Şərtli dövr — `nə qədər ki`

### Sintaksis
```
nə qədər ki <şərt>
    <gövdə>
son
```

```alqor
dəyişən i = 1
nə qədər ki i <= 5
    yaz("Rəqəm: {i}")
    i += 1
son
```

### Sonsuz dövr
```alqor
nə qədər ki doğru
    dəyişən əmr = oxu()
    əgər əmr == "çıx" onda
        dayan
    son
son
```
Qısa forma:
```alqor
həmişə
    ...
son
```

### Şərti sonda yoxlayan dövr (do-while)
```alqor
təkrarla
    yaz("Ən azı bir dəfə işləyir")
nə qədər ki şərt
```

---

## 4.4 Sayğaclı dövr — `təkrarla`

```alqor
təkrarla 5 dəfə
    yaz("Salam")
son

// Sayğac dəyişəni ilə
təkrarla i, 5 dəfə
    yaz("Təkrar {i}")       // 1, 2, 3, 4, 5
son
```

---

## 4.5 Kolleksiya dövrü — `hər ... üçün ... içində`

### Sintaksis
```
hər <bağlama> üçün <ifadə> içində
    <gövdə>
son
```

### Siyahı üzərində
```alqor
dəyişən meyvələr = ["alma", "armud", "üzüm"]

hər meyvə üçün meyvələr içində
    yaz(meyvə)
son
```

### İndekslə
```alqor
hər i, meyvə üçün meyvələr içində
    yaz("{i}: {meyvə}")      // 0: alma, 1: armud, 2: üzüm
son
```

### Diapazon üzərində
```alqor
hər i üçün 1..5 içində
    yaz(i)                   // 1, 2, 3, 4, 5
son

hər i üçün 0..<10 içində
    yaz(i)                   // 0..9
son

hər i üçün 10..1 içində
    yaz(i)                   // 10, 9, ..., 1
son

hər i üçün 1..10 addım 2 içində
    yaz(i)                   // 1, 3, 5, 7, 9
son
```

### Lüğət üzərində
```alqor
dəyişən yaşlar = {"Aysel": 24, "Rəşad": 31}

hər açar üçün yaşlar içində
    yaz(açar)                             // Aysel, Rəşad
son

hər açar, dəyər üçün yaşlar içində
    yaz("{açar}: {dəyər}")
son

hər dəyər üçün yaşlar.dəyərlər() içində
    yaz(dəyər)
son
```

### Mətn üzərində
```alqor
hər hərf üçün "salam" içində
    yaz(hərf)                             // s, a, l, a, m
son
```

### Dağıtma ilə
```alqor
dəyişən cütlər = [(1, "bir"), (2, "iki")]
hər (ədəd, ad) üçün cütlər içində
    yaz("{ədəd} = {ad}")
son
```

### Filtrlə
```alqor
hər x üçün ədədlər içində əgər x % 2 == 0
    yaz(x)                                // yalnız cütlər
son
```

### Tərsinə
```alqor
hər x üçün siyahı.tərs() içində
    yaz(x)
son
```

---

## 4.6 Dövr idarəetməsi

### `dayan` — dövrdən çıx
```alqor
hər x üçün 1..100 içində
    əgər x > 10 onda
        dayan
    son
    yaz(x)
son
```

### `davam et` — növbəti iterasiyaya keç
```alqor
hər x üçün 1..10 içində
    əgər x % 2 == 0 onda
        davam et
    son
    yaz(x)                   // yalnız tək ədədlər
son
```

### Etiketli dövrlər
```alqor
xarici: hər i üçün 1..3 içində
    daxili: hər j üçün 1..3 içində
        əgər i * j > 4 onda
            dayan xarici         // xarici dövrdən çıx
        son
        əgər j == 2 onda
            davam et daxili
        son
        yaz("{i} × {j}")
    son
son
```

### `yoxsa` bloku (dövr tam bitdikdə)
```alqor
hər x üçün siyahı içində
    əgər x == axtarılan onda
        yaz("tapıldı")
        dayan
    son
yoxsa
    yaz("tapılmadı")          // `dayan` olmadan bitibsə işləyir
son
```

---

## 4.7 Kolleksiya qurma (comprehension)

```alqor
// Siyahı
dəyişən kvadratlar = [x * x üçün x içində 1..10]
dəyişən cütlər = [x üçün x içində 1..20 əgər x % 2 == 0]
dəyişən matris = [[i * j üçün j içində 1..3] üçün i içində 1..3]

// Lüğət
dəyişən kvadratLüğət = {x: x * x üçün x içində 1..5}

// Dəst
dəyişən təkrarsız = {x % 3 üçün x içində 1..10}

// Generator (tənbəl)
dəyişən tənbəl = (x * x üçün x içində 1..1_000_000)
```

---

## 4.8 `keç` və boş ifadə

```alqor
funksiya hələYazılmayıb()
    keç                       // heç nə etmir, yer tutucu
son

əgər şərt onda
    keç                       // qəsdən boş
yoxsa
    yaz("işlədi")
son
```

---

## 4.9 `iddia` — təsdiq

```alqor
iddia yaş > 0
iddia yaş > 0, "Yaş müsbət olmalıdır"
iddia uzunluq(siyahı) == 5, "Gözlənilən 5, gələn {uzunluq(siyahı)}"
```

Yanlışdırsa `İddiaXətası` atır. `--buraxılış` rejimində iddialar silinir
(`--iddia-saxla` ilə saxlanılır).

---

## 4.10 `təmin` — şərt zəmanəti

```alqor
funksiya böl(a: tam, b: tam) -> onluq
    təmin b != 0 yoxsa
        at ArqumentXətası("Sıfıra bölmək olmaz")
    son
    qaytar a / b
son
```

`təmin` buraxılış rejimində də qalır — istifadəçi girişinin yoxlanması üçündür.

---

## 4.11 Gecikmə — `gecikdir`

Blokdan çıxarkən icra olunacaq kod (resursların bağlanması üçün):

```alqor
funksiya faylOxu(yol: mətn) -> mətn
    dəyişən f = fayl.aç(yol)
    gecikdir f.bağla()        // funksiya necə bitsə də işləyəcək

    əgər f.ölçü() == 0 onda
        qaytar ""             // f.bağla() burada işləyir
    son
    qaytar f.oxu()            // və burada da
son
```

Bir neçə `gecikdir` tərs sırada (LIFO) işləyir.

---

## 4.12 İdarəetmə strukturlarının xülasəsi

| Konstruksiya | Açar sözlər | Bağlanış |
|---|---|---|
| Şərt | `əgər` `onda` `yoxsa əgər` `yoxsa` / `əks halda` | `son` |
| İxtiyari bağlama | `varsa` `onda` `yoxsa` | `son` |
| Erkən çıxış | `yoxdursa` `onda` | `son` |
| Çoxvariantlı | `seç` `hal` `digər hallarda` `keç` | `son` |
| Şərtli dövr | `nə qədər ki` | `son` |
| Sonsuz dövr | `həmişə` | `son` |
| Sayğaclı dövr | `təkrarla` `dəfə` | `son` |
| Kolleksiya dövrü | `hər` `üçün` `içində` `addım` | `son` |
| Dövr nəzarəti | `dayan` `davam et` | — |
| Boş ifadə | `keç` | — |
| Təsdiq | `iddia` `təmin` | — |
| Təmizləmə | `gecikdir` | — |
