# Alqor — Bölmə 5: Funksiyalar

---

## 5.1 Funksiya elanı

### Sintaksis
```
[açıq|gizli] [asinxron] funksiya <ad>[[generiklər]]([parametrlər]) [-> <qaytarma tipi>]
    <gövdə>
son
```

### Nümunələr
```alqor
funksiya salamla()
    yaz("Salam!")
son

funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son

funksiya yaz3Dəfə(mesaj: mətn)
    təkrarla 3 dəfə
        yaz(mesaj)
    son
son
```

### Qaytarma tipi
- Yazılmayıbsa kompilyator çıxarır.
- Heç nə qaytarmırsa tip `heç`-dir.
- `-> heç` açıq yazmaq olar.

```alqor
funksiya a() -> tam qaytar 5 son       // açıq
funksiya b() qaytar 5 son              // çıxarılır → tam
funksiya c() yaz("x") son              // → heç
```

---

## 5.2 Parametrlər

### Standart dəyərlər
```alqor
funksiya salamla(ad: mətn = "dünya", nida: mətn = "!")
    yaz("Salam, {ad}{nida}")
son

salamla()                    // Salam, dünya!
salamla("Aysel")             // Salam, Aysel!
salamla("Aysel", "?")        // Salam, Aysel?
```
Standart dəyərli parametrlər **sonda** olmalıdır (`ALQ-P020`).

### Adlı arqumentlər
```alqor
funksiya qur(en: tam, hündürlük: tam, rəng: mətn = "ağ", kölgə: məntiq = yanlış)
    ...
son

qur(100, 200)
qur(en: 100, hündürlük: 200)
qur(hündürlük: 200, en: 100)           // sıra önəmli deyil
qur(100, 200, kölgə: doğru)            // qarışıq
qur(kölgə: doğru, 100, 200)            // ✖ mövqeli arqument adlıdan sonra olmaz
```

### Yalnız adlı parametrlər
`*` ayırıcısından sonrakılar mütləq adla verilməlidir:
```alqor
funksiya göndər(mesaj: mətn, *, təcili: məntiq = yanlış, təkrar: tam = 1)
    ...
son

göndər("salam", təcili: doğru)         // ✓
göndər("salam", doğru)                 // ✖ ALQ-T004
```

### Dəyişkən sayda parametr (variadic)
```alqor
funksiya cəm(...ədədlər: tam) -> tam
    dəyişən nəticə = 0
    hər ə üçün ədədlər içində
        nəticə += ə
    son
    qaytar nəticə
son

yaz(cəm(1, 2, 3))                      // 6
yaz(cəm())                             // 0
yaz(cəm(...[1, 2, 3, 4]))              // 10  (yayma)
```

### Adlı dəyişkən parametrlər
```alqor
funksiya qur(**xassələr: lüğət[mətn, istənilən])
    hər açar, dəyər üçün xassələr içində
        yaz("{açar} = {dəyər}")
    son
son

qur(en: 100, rəng: "qırmızı")
```

### Ötürmə semantikası

| Tip | Ötürülmə |
|---|---|
| `tam`, `onluq`, `məntiq`, `simvol`, `kortej`, `struktur`, `sadalama` | **dəyər** (kopya) |
| `mətn`, `siyahı`, `lüğət`, `dəst`, `sinif` | **istinad** |

```alqor
funksiya dəyiş(s: siyahı[tam])
    s.əlavə(99)              // çağıranda da görünür
son

funksiya dəyişməz(s: dəyişməz siyahı[tam])
    s.əlavə(99)              // ✖ ALQ-T021
son
```

---

## 5.3 Qaytarma

```alqor
funksiya mütləq(x: tam) -> tam
    əgər x < 0 onda
        qaytar -x
    son
    qaytar x
son

// Dəyərsiz qaytarma (erkən çıxış)
funksiya yoxla(x: tam)
    əgər x < 0 onda
        qaytar
    son
    yaz(x)
son

// Çoxlu dəyər (kortej)
funksiya böl(a: tam, b: tam) -> kortej[tam, tam]
    qaytar (a ~/ b, a % b)
son

dəyişən tam, qalıq = böl(17, 5)        // 3, 2
```

### Son ifadənin avtomatik qaytarılması
Funksiyanın son ifadəsi `qaytar`-sızdırsa və dəyər verirsə, avtomatik qaytarılır:
```alqor
funksiya ikiqat(x: tam) -> tam
    x * 2                    // `qaytar x * 2` ilə eynidir
son
```

### Açar söz adlı arqumentin etiketi kimi

Arqument siyahısında `etiket:` formasında **tək sözlü açar söz** də
etiket ola bilər — `açar_söz :` heç bir ifadənin başlanğıcı olmadığı
üçün qeyri-müəyyənlik yaranmır:

```alqor
konsol.seçim("--format", "-f", "Format", standart: "mətn")
konsol.təsdiqlə("Davam edilsin?", standart: doğru)
```

Çoxsözlü açar sözlər (`və ya`, `digər hallarda`) etiket ola bilməz.
Alqor-da yazılan funksiyanın parametri isə açar söz ola bilməz — bu
imkan əsasən kitabxana funksiyaları üçündür.

---

## 5.4 Anonim funksiyalar və lambda

### Tam forma
```alqor
dəyişən topla = funksiya(a: tam, b: tam) -> tam
    qaytar a + b
son

yaz(topla(3, 4))             // 7
```

### Ox forması (qısa)
```alqor
dəyişən ikiqat = (x) => x * 2
dəyişən topla = (a, b) => a + b
dəyişən salam = () => yaz("salam")
dəyişən tək = x => x * 2               // tək parametrdə mötərizə ixtiyari

// Tipli
dəyişən böl: funksiyaTipi(tam, tam) -> onluq = (a: tam, b: tam) => a / b

// Çoxsətirli ox funksiyası
dəyişən emal = (x) => blok
    dəyişən y = x * 2
    ver y + 1
son
```

**Gövdə kimi tək mənimsətmə.** Ox funksiyasının gövdəsi bir mənimsətmə
və ya `++`/`--` ola bilər; nəticəsi `heç`-dir. İnterfeys
idarəedicilərinin ən təbii formasıdır:

```alqor
<button klik={() => özü.say += 1}>Artır</button>
vidjet.düymə(mətn: "Sıfırla", klik: () => özü.say = 0)
dəyişən növbəti = () => sayğac++
```

Vergüllü mənimsətmə (`a, b = b, a`) arqument siyahısı ilə qarışdığı
üçün yalnız `blok` formasında yazılır.

### Dərhal çağırılan funksiya
```alqor
dəyişən nəticə = (funksiya() qaytar 42 son)()
dəyişən n2 = ((() => 42))()
```

---

## 5.5 Birinci dərəcəli funksiyalar

```alqor
// Funksiya arqument kimi
funksiya tətbiq(f: funksiyaTipi(tam) -> tam, x: tam) -> tam
    qaytar f(x)
son

yaz(tətbiq((x) => x * 2, 5))           // 10

// Funksiya qaytaran funksiya
funksiya vurucu(n: tam) -> funksiyaTipi(tam) -> tam
    qaytar (x) => x * n
son

dəyişən üçəVur = vurucu(3)
yaz(üçəVur(5))                         // 15

// Funksiya istinadı
dəyişən f = yaz
f("salam")

// Metod istinadı
dəyişən m = mətn.böyüyə
yaz(m("salam"))                        // SALAM
```

### Standart yüksək dərəcəli funksiyalar
```alqor
siyahı.çevir((x) => x * 2)             // map
siyahı.filtr((x) => x > 5)             // filter
siyahı.yığ(0, (a, b) => a + b)         // reduce/fold
siyahı.hərBiri((x) => yaz(x))          // forEach
siyahı.tap((x) => x > 5)               // find
siyahı.hamısı((x) => x > 0)            // all
siyahı.hər_hansı((x) => x > 0)         // any
siyahı.sırala((a, b) => a <=> b)       // sort
siyahı.qrupla((x) => x % 3)            // groupBy
```

---

## 5.6 Qapanmalar (closure)

```alqor
funksiya sayğacYarat() -> funksiyaTipi() -> tam
    dəyişən say = 0
    qaytar funksiya() -> tam
        say += 1                        // xarici `say`-ı tutur
        qaytar say
    son
son

dəyişən s = sayğacYarat()
yaz(s())                 // 1
yaz(s())                 // 2
yaz(s())                 // 3

dəyişən s2 = sayğacYarat()
yaz(s2())                // 1  — müstəqil vəziyyət
```

### Tutma qaydası
- Qapanma dəyişəni **istinadla** tutur.
- Kopya ilə tutmaq üçün `tut` siyahısı:
```alqor
dəyişən i = 10
dəyişən f = [tut i] () => i * 2        // i-nin o andakı dəyəri
i = 20
yaz(f())                                // 20 yox, 20... → tutulmuş dəyər: 10 → 20
```

### Dövrdə qapanma tələsi
```alqor
dəyişən funksiyalar = []
hər i üçün 1..3 içində
    funksiyalar.əlavə(() => i)
son
// Alqor-da hər iterasiya `i` üçün yeni bağlama yaradır:
yaz(funksiyalar[0]())    // 1  ✓ (JavaScript `var` tələsi burada yoxdur)
```

---

## 5.7 Rekursiya

```alqor
funksiya faktorial(n: tam) -> tam
    əgər n <= 1 onda
        qaytar 1
    son
    qaytar n * faktorial(n - 1)
son

// Quyruq rekursiyası (optimallaşdırılır)
@quyruqRekursiya
funksiya cəm(n: tam, toplam: tam = 0) -> tam
    əgər n == 0 onda
        qaytar toplam
    son
    qaytar cəm(n - 1, toplam + n)
son

// Qarşılıqlı rekursiya
funksiya cütdür(n: tam) -> məntiq
    əgər n == 0 onda qaytar doğru son
    qaytar təkdir(n - 1)
son

funksiya təkdir(n: tam) -> məntiq
    əgər n == 0 onda qaytar yanlış son
    qaytar cütdür(n - 1)
son
```

Stek dərinliyi standart **8192**-dir. Aşılırsa `StekDaşmaXətası`.
Dəyişdirmək: `layihe.alq` → `[icra] stek_dərinliyi = 16384`.

---

## 5.8 Generatorlar

```alqor
generator funksiya fibonaççi() -> tam
    dəyişən a = 0, b = 1
    həmişə
        ver a                 // dəyər ver və dayan
        a, b = b, a + b
    son
son

hər f üçün fibonaççi() içində
    əgər f > 100 onda dayan son
    yaz(f)
son

// Sonlu generator
generator funksiya saylar(n: tam) -> tam
    hər i üçün 1..n içində
        ver i
    son
son

// Generatoru əl ilə idarə etmək
dəyişən g = saylar(3)
yaz(g.növbəti())         // 1
yaz(g.növbəti())         // 2
yaz(g.bitdi())           // yanlış
```

---

## 5.9 Asinxron funksiyalar

```alqor
asinxron funksiya məlumatAl(url: mətn) -> mətn
    dəyişən cavab = gözlə http.al(url)
    qaytar cavab.mətn()
son

asinxron funksiya əsas()
    dəyişən m = gözlə məlumatAl("https://alqor.vuqar.pro/api")
    yaz(m)
son
```

### Paralel icra
```alqor
asinxron funksiya hamısınıAl()
    // Ardıcıl — yavaş
    dəyişən a = gözlə al("/a")
    dəyişən b = gözlə al("/b")

    // Paralel — sürətli
    dəyişən (x, y) = gözlə paralel(al("/a"), al("/b"))

    // Siyahı üzərində paralel
    dəyişən hamısı = gözlə paralel.hamısı(
        [al("/a"), al("/b"), al("/c")]
    )

    // İlk bitəni götür
    dəyişən ilk = gözlə paralel.ilkBitən([al("/a"), al("/b")])
son
```

Ətraflı: `09-ASINXRON.md`

---

## 5.10 Annotasiyalar

```alqor
@sınaq
funksiya toplamaTesti()
    iddia topla(2, 2) == 4
son

@köhnəlmiş("Əvəzinə yeniFunksiya() istifadə edin")
funksiya köhnəFunksiya()
    ...
son

@daxili                       // inline optimallaşdırma
funksiya kiçik(x: tam) -> tam qaytar x + 1 son

@xaric                        // inline etmə
funksiya böyük() ... son

@saf                          // yan təsiri yoxdur — nəticə keşlənə bilər
funksiya kvadrat(x: tam) -> tam qaytar x * x son

@yaddaşla                     // avtomatik memoizasiya
funksiya fib(n: tam) -> tam
    əgər n < 2 onda qaytar n son
    qaytar fib(n-1) + fib(n-2)
son

@quyruqRekursiya              // quyruq rekursiyası tələb et
@sınaqdan_keçməyib            // örtük hesabatından çıxar
@xarici("C", "printf")        // xarici funksiya bağlaması
@yalnızHədəf("veb")           // yalnız veb hədəfində kompilyasiya olunur
```

---

## 5.11 Funksiya yükləmə (overloading)

Alqor **ad yükləməsini dəstəkləmir**. Əvəzinə:
- Standart dəyərlər
- Birləşmə tipləri
- Generiklər

```alqor
// ✖ Belə olmaz
funksiya çap(x: tam) ... son
funksiya çap(x: mətn) ... son        // ALQ-T023 təkrar elan

// ✓ Belə olar
funksiya çap(x: tam | mətn)
    seç tipi x
        hal tam → yaz("ədəd: {x}")
        hal mətn → yaz("mətn: {x}")
    son
son

// ✓ Və ya generik
funksiya çap[T: Çapedilən](x: T)
    yaz(x.mətnƏt())
son
```

---

## 5.12 Giriş nöqtəsi

```alqor
// əsas.alq
funksiya əsas()
    yaz("Proqram başladı")
son
```

### Arqumentlərlə
```alqor
funksiya əsas(arqumentlər: siyahı[mətn])
    yaz("Arqument sayı: {uzunluq(arqumentlər)}")
    hər a üçün arqumentlər içində
        yaz(a)
    son
son
```

### Çıxış kodu ilə
```alqor
funksiya əsas() -> tam
    əgər xətaVar onda
        qaytar 1             // çıxış kodu 1
    son
    qaytar 0
son
```

### Asinxron giriş
```alqor
asinxron funksiya əsas()
    gözlə serveriBaşlat()
son
```

> Faylda `əsas()` yoxdursa, modul səviyyəsindəki ifadələr yuxarıdan aşağı icra olunur
> (skript rejimi).

---

## 5.13 Funksiya xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-P020` | Standart dəyərli parametr standartsızdan əvvəl gələ bilməz |
| `ALQ-P021` | Variadic parametr sonuncu olmalıdır |
| `ALQ-P022` | Mövqeli arqument adlıdan sonra |
| `ALQ-T003` | Arqument sayı uyğun deyil |
| `ALQ-T004` | Arqument tipi uyğun deyil |
| `ALQ-T005` | Qaytarma tipi uyğun deyil |
| `ALQ-T040` | Bütün yollarda `qaytar` yoxdur |
| `ALQ-T041` | `ver` yalnız generatorda |
| `ALQ-T042` | `@quyruqRekursiya` tələbi ödənmir |
| `ALQ-R010` | Stek daşması |
