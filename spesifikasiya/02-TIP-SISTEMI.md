# Alqor — Bölmə 2: Tip Sistemi

> Alqor **tədrici (gradual) tipli** dildir: tip yazmaq ixtiyaridir, amma yazılan hər tip yoxlanılır.

---

## 2.1 Tədrici tiplərin iş prinsipi

```alqor
dəyişən a = 5                    // tip çıxarılır → tam
dəyişən b: tam = 5               // tip açıq yazılıb → tam
dəyişən c: istənilən = 5         // tip yoxlaması söndürülüb
```

| Rejim | Davranış | Nə vaxt |
|---|---|---|
| **Çıxarılmış** | Kompilyator tipi özü tapır və yoxlayır | Standart |
| **Açıq** | Yazdığınız tip yoxlanılır | Böyük layihələrdə |
| **`istənilən`** | Yoxlama yoxdur, icra zamanı həll olunur | Dinamik verilənlər, JSON |

### Sərtlik səviyyələri
`layihe.alqor` faylında:

```toml
[tip]
rejim = "normal"      # "sərbəst" | "normal" | "sərt"
```

| Rejim | Qayda |
|---|---|
| `sərbəst` | Tiplər yalnız yazılanda yoxlanır, qalan hər şey `istənilən` |
| `normal` | Çıxarma + yoxlama, `istənilən`-ə keçid sərbəst (standart) |
| `sərt` | Bütün açıq funksiya imzalarında tip məcburidir, implicit `istənilən` qadağan |

---

## 2.2 Əsas tiplər

| Tip | Mənası | Ölçü | Standart dəyər | Nümunə |
|---|---|---|---|---|
| `tam` | tam ədəd | 64 bit | `0` | `42`, `-7` |
| `onluq` | onluq kəsr | 64 bit IEEE754 | `0.0` | `3.14` |
| `məntiq` | məntiqi | 1 bayt | `yanlış` | `doğru` |
| `mətn` | UTF-8 mətn | dəyişkən | `""` | `"Salam"` |
| `simvol` | bir qrafem | dəyişkən | `` ` ` `` | `` `ə` `` |
| `bayt` | işarəsiz bayt | 8 bit | `0` | `0xFF` |
| `heç` | dəyər yoxdur | 0 | — | funksiya qaytarmır |
| `istənilən` | hər hansı tip | — | `boş` | dinamik |

### Dəqiq ölçülü ədədlər (`riyaziyyat` modulu)
```alqor
gətir riyaziyyat

dəyişən a: riyaziyyat.tam8 = 127
dəyişən b: riyaziyyat.tam16 = 32767
dəyişən c: riyaziyyat.tam32 = 2147483647
dəyişən d: riyaziyyat.tam64 = 9223372036854775807
dəyişən e: riyaziyyat.işarəsiz8 = 255
dəyişən f: riyaziyyat.işarəsiz32 = 4294967295
dəyişən g: riyaziyyat.onluq32 = 3.14
dəyişən h: riyaziyyat.böyükTam = 10 ** 100      // hüdudsuz
dəyişən i: riyaziyyat.onluqDəqiq = 19.99        // pul üçün (onluq kəsrsiz)
```

---

## 2.3 Kompozit tiplər

### 2.3.1 Siyahı — `siyahı[T]`
Sıralanmış, dəyişdirilə bilən, indeksli kolleksiya.

```alqor
dəyişən ədədlər: siyahı[tam] = [1, 2, 3]
dəyişən adlar: siyahı[mətn] = ["Aysel", "Rəşad"]
dəyişən matris: siyahı[siyahı[tam]] = [[1, 2], [3, 4]]
dəyişən qarışıq: siyahı[istənilən] = [1, "iki", doğru]

// İndeksləmə — 0-dan başlayır
yaz(ədədlər[0])        // 1
yaz(ədədlər[-1])       // 3  (sondan)

// Dilimləmə
yaz(ədədlər[0..1])     // [1, 2]
yaz(ədədlər[1..])      // [2, 3]
yaz(ədədlər[..1])      // [1, 2]
```

### 2.3.2 Lüğət — `lüğət[A, D]`
Açar-dəyər cütləri. Əlavə olunma sırasını saxlayır.

```alqor
dəyişən yaşlar: lüğət[mətn, tam] = {"Aysel": 24, "Rəşad": 31}

yaz(yaşlar["Aysel"])          // 24
yaz(yaşlar.al("Yoxdur", 0))   // 0  (standart dəyərlə)
yaşlar["Nigar"] = 28          // əlavə

əgər "Aysel" içindədir yaşlar onda
    yaz("var")
son
```

Açar tipi `tam`, `mətn`, `simvol`, `məntiq`, `kortej` və ya `dəyişməz` sinif ola bilər.

### 2.3.3 Dəst — `dəst[T]`
Təkrarsız elementlər, sırasız.

```alqor
dəyişən rənglər: dəst[mətn] = dəst("qırmızı", "mavi")
rənglər.əlavə("yaşıl")
rənglər.əlavə("mavi")         // təsir yoxdur — artıq var

yaz(uzunluq(rənglər))         // 3
yaz(rənglər.birləşmə(digər))  // ∪
yaz(rənglər.kəsişmə(digər))   // ∩
yaz(rənglər.fərq(digər))      // \
```

### 2.3.4 Kortej — `kortej[T1, T2, ...]`
Sabit uzunluqlu, fərqli tipli elementlər.

```alqor
dəyişən nöqtə: kortej[tam, tam] = (3, 4)
dəyişən qeyd: kortej[mətn, tam, məntiq] = ("Aysel", 24, doğru)

yaz(nöqtə.0)                  // 3
yaz(nöqtə.1)                  // 4

// Dağıtma (destructuring)
dəyişən x, y = nöqtə
dəyişən ad, yaş, _ = qeyd     // _ = atılır
```

### 2.3.5 Funksiya tipi — `funksiyaTipi(...) -> T`

```alqor
dəyişən əməliyyat: funksiyaTipi(tam, tam) -> tam = funksiya(a, b) qaytar a + b son
dəyişən çağır: funksiyaTipi() -> heç = funksiya() yaz("salam") son

yaz(əməliyyat(3, 4))          // 7
```

---

## 2.4 İxtiyari tiplər (nullable)

`?` işarəsi tipin `boş` ola biləcəyini bildirir.

```alqor
dəyişən ad: mətn = "Aysel"
dəyişən soyad: mətn? = boş        // ixtiyari

ad = boş                          // ✖ ALQ-T012 — `mətn` boş ola bilməz
soyad = boş                       // ✓
```

### İxtiyari dəyərlə iş

```alqor
dəyişən istifadəçi: İstifadəçi? = tap(id)

// 1. Boş yoxlaması
əgər istifadəçi boş deyil onda
    yaz(istifadəçi.ad)            // burada tip `İstifadəçi`-yə daralır
son

// 2. Təhlükəsiz çağırış
yaz(istifadəçi?.ad)               // boşdursa → boş

// 3. Boş-birləşdirmə
dəyişən ad = istifadəçi?.ad ?? "Qonaq"

// 4. Boşdursa mənimsət
istifadəçi ?= yeni İstifadəçi("Qonaq")

// 5. Zəncirvari
yaz(sifariş?.müştəri?.ünvan?.şəhər ?? "naməlum")

// 6. Məcburi açma (riskli — boşdursa xəta atır)
yaz(istifadəçi!.ad)

// 7. varsa-bağlama
varsa i = istifadəçi onda
    yaz(i.ad)                     // i tipi: İstifadəçi
yoxsa
    yaz("tapılmadı")
son
```

---

## 2.5 Birləşmə tipləri (union)

```alqor
dəyişən nəticə: tam | mətn = 5
nəticə = "xəta"                   // ✓ ikisi də icazəlidir

seç tipi nəticə
    hal tam
        yaz("ədəd: {nəticə}")
    hal mətn
        yaz("mətn: {nəticə}")
son
```

`T?` əslində `T | heç` üçün qısaltmadır.

---

## 2.6 Tip aliasları

```alqor
tip Yaş = tam
tip Koordinat = kortej[onluq, onluq]
tip İdarəedici = funksiyaTipi(Sorğu) -> Cavab
tip Nəticə[T] = T | Xəta

dəyişən a: Yaş = 24
dəyişən b: Koordinat = (40.4093, 49.8671)
```

---

## 2.7 Generiklər

```alqor
// Generik funksiya
funksiya ilk[T](siyahı: siyahı[T]) -> T?
    əgər uzunluq(siyahı) == 0 onda
        qaytar boş
    son
    qaytar siyahı[0]
son

// Generik sinif
sinif Qutu[T]
    gizli xassə dəyər: T

    qurucu(dəyər: T)
        özü.dəyər = dəyər
    son

    metod al() -> T
        qaytar özü.dəyər
    son
son

dəyişən q = yeni Qutu[mətn]("salam")
yaz(q.al())
```

### Məhdudiyyətlər
```alqor
funksiya ənBöyük[T: Müqayisəedilən](siyahı: siyahı[T]) -> T?
    ...
son

funksiya birləşdir[T: Çapedilən və Klonlanan](a: T, b: T) -> mətn
    ...
son
```

---

## 2.8 Tip çevrilməsi

### Avtomatik (implicit) — yalnız genişlənmə

| Mənbə | Hədəf | İcazə |
|---|---|---|
| `tam` | `onluq` | ✓ |
| `tam8` | `tam16` → `tam32` → `tam64` | ✓ |
| `simvol` | `mətn` | ✓ |
| `T` | `T?` | ✓ |
| `T` | `istənilən` | ✓ |
| `onluq` | `tam` | ✖ — itki olar |
| `mətn` | `tam` | ✖ |

### Açıq (explicit) — `kimi` operatoru

```alqor
dəyişən a = 3.9 kimi tam              // 3    (kəsilir, yuvarlaqlaşmır)
dəyişən b = 42 kimi mətn              // "42"
dəyişən c = "42" kimi tam             // 42
dəyişən d = "abc" kimi tam            // ✖ ÇevrilməXətası atır
dəyişən e = "abc" kimi? tam           // boş  (təhlükəsiz forma)
dəyişən f = doğru kimi tam            // 1
dəyişən g = 0 kimi məntiq             // ✖ icazə verilmir (açıq yazın)
```

### Çevirmə funksiyaları

```alqor
tamƏt("42")             // 42
tamƏt("abc")            // ✖ xəta
tamƏt("abc", 0)         // 0  (standart dəyərlə)
tamƏt("1F", əsas: 16)   // 31
onluqƏt("3.14")         // 3.14
mətnƏt(42)              // "42"
məntiqƏt("doğru")       // doğru
```

---

## 2.9 Tip yoxlaması və daralma

```alqor
// tipidir operatoru
əgər x tipidir mətn onda
    yaz(x.uzunluq())       // x burada `mətn` kimi tanınır
son

əgər deyil (x tipidir tam) onda
    qaytar
son
// bu nöqtədən sonra x → tam

// tip() funksiyası
yaz(tip(42))               // "tam"
yaz(tip("a"))              // "mətn"
yaz(tip([1,2]))            // "siyahı[tam]"
yaz(tip(boş))              // "heç"
```

### Axın əsaslı daralma (flow narrowing)
Kompilyator şərtlərdən tipi avtomatik daraldır:

```alqor
funksiya emal(dəyər: tam | mətn | boş)
    əgər dəyər boşdur onda
        qaytar                     // dəyər: heç
    son
    // dəyər: tam | mətn

    əgər dəyər tipidir tam onda
        yaz(dəyər + 1)             // dəyər: tam
        qaytar
    son
    // dəyər: mətn
    yaz(dəyər.böyüyə())
son
```

---

## 2.10 Dəyər və istinad semantikası

| Kateqoriya | Tiplər | Semantika |
|---|---|---|
| **Dəyər** | `tam`, `onluq`, `məntiq`, `simvol`, `bayt`, `kortej`, `struktur`, `sadalama` | Kopyalanır |
| **İstinad** | `mətn`, `siyahı`, `lüğət`, `dəst`, `sinif` | İstinad ötürülür |

```alqor
// Dəyər
dəyişən a = 5
dəyişən b = a
b = 10
yaz(a)                     // 5 — dəyişmədi

// İstinad
dəyişən s1 = [1, 2, 3]
dəyişən s2 = s1
s2.əlavə(4)
yaz(s1)                    // [1, 2, 3, 4] — dəyişdi!

// Dərin kopya
dəyişən s3 = s1.klonla()
s3.əlavə(5)
yaz(s1)                    // [1, 2, 3, 4] — dəyişmədi
```

> `mətn` istinaddır, amma **dəyişməzdir** — hər əməliyyat yeni mətn qaytarır.

---

## 2.11 Dəyişməzlik

```alqor
dəyişən a = 5            // dəyişdirilə bilər
sabit B = 5              // dəyişdirilə bilməz (kompilyasiya vaxtı)
dəyişməz c = [1, 2, 3]   // istinad və məzmun dəyişməz

a = 10                   // ✓
B = 10                   // ✖ ALQ-T020
c.əlavə(4)               // ✖ ALQ-T021 — dəyişməz kolleksiya
```

| Açar söz | İstinad dəyişir? | Məzmun dəyişir? | Hesablanır |
|---|:---:|:---:|---|
| `dəyişən` | ✓ | ✓ | icra zamanı |
| `sabit` | ✖ | ✓ | icra zamanı (bir dəfə) |
| `dəyişməz` | ✖ | ✖ | icra zamanı (bir dəfə) |
| `sabit` + BÖYÜK ad | ✖ | ✖ | **kompilyasiya vaxtı** |

---

## 2.12 Standart dəyərlər və sıfır dəyəri

```alqor
dəyişən a: tam                 // 0
dəyişən b: onluq               // 0.0
dəyişən c: mətn                // ""
dəyişən d: məntiq              // yanlış
dəyişən e: siyahı[tam]         // []
dəyişən f: lüğət[mətn, tam]    // {}
dəyişən g: dəst[tam]           // dəst()
dəyişən h: mətn?               // boş
dəyişən i: İstifadəçi          // ✖ ALQ-T030 — sinif üçün standart dəyər yoxdur
```

---

## 2.13 Tip xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-T001` | Tip uyğunsuzluğu |
| `ALQ-T002` | Naməlum tip |
| `ALQ-T003` | Arqument sayı uyğun deyil |
| `ALQ-T004` | Arqument tipi uyğun deyil |
| `ALQ-T005` | Qaytarma tipi uyğun deyil |
| `ALQ-T006` | Bu tipdə belə üzv yoxdur |
| `ALQ-T007` | Şərt `məntiq` tipi olmalıdır |
| `ALQ-T008` | Operator bu tiplərə tətbiq edilmir |
| `ALQ-T009` | İndeksləmə bu tipdə mümkün deyil |
| `ALQ-T010` | Generik parametr həll olunmadı |
| `ALQ-T011` | Dövri tip asılılığı |
| `ALQ-T012` | `boş` bu tipə mənimsədilə bilməz |
| `ALQ-T013` | İxtiyari dəyər yoxlanmadan istifadə olunub |
| `ALQ-T014` | Çevrilmə mümkün deyil |
| `ALQ-T015` | Birləşmə tipi daraldılmayıb |
| `ALQ-T020` | Sabitə mənimsətmə |
| `ALQ-T021` | Dəyişməz kolleksiyanın dəyişdirilməsi |
| `ALQ-T022` | Təyin edilməmiş dəyişən |
| `ALQ-T023` | Təkrar elan |
| `ALQ-T024` | ⚠ İstifadə olunmayan dəyişən |
| `ALQ-T025` | ⚠ Çatılmayan kod |
| `ALQ-T030` | Standart dəyəri olmayan tip ilkinləşdirilməyib |
| `ALQ-T031` | `seç` bütün halları əhatə etmir |
