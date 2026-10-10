# Alqor Bələdçisi — 2. Dil Dərsliyi

> Sıfırdan başlayaraq addım-addım. Hər bölmədə nümunə və tapşırıq var.

---

## Dərs 1 — Ekrana yazmaq

```alqor
yaz("Salam, dünya!")
```

### Bir neçə dəyər
```alqor
yaz("Ad:", "Aysel", "Yaş:", 24)
// Ad: Aysel Yaş: 24
```

### Yeni sətirsiz
```alqor
yazSətirsiz("Yüklənir")
yazSətirsiz(".")
yazSətirsiz(".")
yaz(".")
// Yüklənir...
```

### Xəta axınına
```alqor
yazXəta("Bu stderr-ə gedir")
```

**Tapşırıq:** Öz adınızı və yaşınızı bir sətirdə ekrana yazın.

---

## Dərs 2 — Dəyişənlər

```alqor
dəyişən ad = "Aysel"
dəyişən yaş = 24

yaz(ad)
yaz(yaş)

yaş = 25                     // dəyişdirmək olar
yaz(yaş)
```

### Sabitlər
```alqor
sabit Pİ = 3.14159
Pİ = 3                       // ✖ XƏTA: sabiti dəyişmək olmaz
```

### Tipi açıq yazmaq
```alqor
dəyişən ad: mətn = "Aysel"
dəyişən yaş: tam = 24
dəyişən boy: onluq = 1.68
dəyişən tələbədir: məntiq = doğru
```

### Əsas tiplər

| Tip | Nədir | Nümunə |
|---|---|---|
| `tam` | tam ədəd | `42`, `-7`, `0` |
| `onluq` | onluq kəsr | `3.14`, `-0.5` |
| `mətn` | hərf və sözlər | `"Salam"` |
| `məntiq` | doğru/yanlış | `doğru`, `yanlış` |
| `boş` | heç nə | `boş` |

**Tapşırıq:** Üç dəyişən yaradın — adınız, yaşınız, boyunuz — və hamısını yazın.

---

## Dərs 3 — Mətnlərlə iş

### Birləşdirmə
```alqor
dəyişən ad = "Aysel"
dəyişən soyad = "Məmmədova"

yaz(ad + " " + soyad)                  // Aysel Məmmədova
```

### İnterpolyasiya (daha rahat)
```alqor
yaz("Tam ad: {ad} {soyad}")
yaz("Gələn il {yaş + 1} olacaqsan")    // ifadə də olar
```

### Faydalı metodlar
```alqor
dəyişən m = "  Salam, Dünya  "

yaz(m.kəs())                 // "Salam, Dünya"  (boşluqları silir)
yaz(m.böyüyə())              // "  SALAM, DÜNYA  "
yaz(m.kiçiyə())              // "  salam, dünya  "
yaz(m.uzunluq())             // 17
yaz(m.əvəz("Dünya", "Bakı")) // "  Salam, Bakı  "
yaz(m.ehtiva("Salam"))       // doğru
yaz(m.kəs().böl(", "))       // ["Salam", "Dünya"]
```

### ⚠ Azərbaycan hərfləri düzgün işləyir
```alqor
yaz("ışıq".böyüyə())         // IŞIQ   ✓  (standart Unicode "IŞIK" verərdi)
yaz("İmran".kiçiyə())        // imran  ✓
yaz("I".kiçiyə())            // ı      ✓
```

**Tapşırıq:** İstifadəçidən ad alın və onu böyük hərflərlə geri yazın.

---

## Dərs 4 — Ədədlərlə iş

```alqor
yaz(5 + 3)                   // 8
yaz(5 - 3)                   // 2
yaz(5 * 3)                   // 15
yaz(7 / 2)                   // 3.5      ← həmişə onluq
yaz(7 ~/ 2)                  // 3        ← tam bölmə
yaz(7 % 3)                   // 1        ← qalıq
yaz(2 ** 10)                 // 1024     ← qüvvət
```

### Riyaziyyat modulu
```alqor
gətir riyaziyyat kimi r

yaz(r.kök(16))               // 4.0
yaz(r.mütləq(-5))            // 5
yaz(r.yuvarlaqlaşdır(3.7))   // 4
yaz(r.aşağıYuvarlaq(3.7))    // 3
yaz(r.maks(1, 5, 3))         // 5
yaz(r.Pİ)                    // 3.14159...
```

### Mətndən ədədə
```alqor
dəyişən m = "42"
dəyişən n = tamƏt(m)
yaz(n + 8)                   // 50
```

**Tapşırıq:** İki ədəd alın və cəmini, fərqini, hasilini, nisbətini yazın.

---

## Dərs 5 — Şərtlər

```alqor
dəyişən yaş = oxuTam("Yaşınız: ")

əgər yaş >= 18 onda
    yaz("Yetkinsiniz")
son
```

### Əks hal
```alqor
əgər yaş >= 18 onda
    yaz("Yetkinsiniz")
yoxsa
    yaz("Yetkin deyilsiniz")
son
```

### Çoxlu şərt
```alqor
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

### Müqayisə operatorları

| Operator | Mənası |
|---|---|
| `==` | bərabərdir |
| `!=` | bərabər deyil |
| `<` `>` | kiçik / böyük |
| `<=` `>=` | kiçik-bərabər / böyük-bərabər |

### Məntiqi operatorlar
```alqor
əgər yaş >= 18 və vətəndaşdır onda
    yaz("Səs verə bilərsiniz")
son

əgər admin və ya moderator onda
    yaz("İcazəniz var")
son

əgər deyil aktivdir onda
    yaz("Hesab bağlıdır")
son
```

**Tapşırıq:** İstifadəçidən ədəd alın. Müsbət, mənfi və ya sıfır olduğunu yazın.

---

## Dərs 6 — Çoxvariantlı seçim

```alqor
dəyişən gün = oxuTam("Həftənin günü (1-7): ")

seç gün
    hal 1 → yaz("Bazar ertəsi")
    hal 2 → yaz("Çərşənbə axşamı")
    hal 3 → yaz("Çərşənbə")
    hal 4 → yaz("Cümə axşamı")
    hal 5 → yaz("Cümə")
    hal 6, 7 → yaz("Həftəsonu")
    digər hallarda → yaz("Yanlış gün")
son
```

### Diapazonla
```alqor
seç bal
    hal 90..100 → yaz("Əla")
    hal 70..<90 → yaz("Yaxşı")
    digər hallarda → yaz("Zəif")
son
```

**Tapşırıq:** Ay nömrəsindən (1-12) fəsli tapan proqram yazın.

---

## Dərs 7 — Dövrlər

### Diapazon üzərində
```alqor
hər i üçün 1..5 içində
    yaz("Rəqəm: {i}")
son
```

### Addımla
```alqor
hər i üçün 1..10 addım 2 içində
    yaz(i)                   // 1, 3, 5, 7, 9
son
```

### Tərsinə
```alqor
hər i üçün 10..1 içində
    yaz(i)                   // 10, 9, ..., 1
son
```

### Şərtli dövr
```alqor
dəyişən i = 1
nə qədər ki i <= 5
    yaz(i)
    i += 1
son
```

### Sayla təkrar
```alqor
təkrarla 3 dəfə
    yaz("Salam")
son
```

### Sonsuz dövr
```alqor
həmişə
    dəyişən əmr = oxu("Əmr: ")
    əgər əmr == "çıx" onda
        dayan
    son
    yaz("Əmr: {əmr}")
son
```

### `dayan` və `davam et`
```alqor
hər i üçün 1..10 içində
    əgər i == 5 onda
        davam et             // 5-i atla
    son
    əgər i > 8 onda
        dayan                // dövrü bitir
    son
    yaz(i)                   // 1 2 3 4 6 7 8
son
```

**Tapşırıq:** 1-dən 100-ə qədər bütün cüt ədədlərin cəmini hesablayın.

---

## Dərs 8 — Siyahılar

```alqor
dəyişən meyvələr = ["alma", "armud", "üzüm"]

yaz(meyvələr[0])             // alma
yaz(meyvələr[-1])            // üzüm (sondan)
yaz(uzunluq(meyvələr))       // 3
```

### Dəyişdirmək
```alqor
meyvələr.əlavə("nar")                  // sona
meyvələr.daxilEt(0, "ərik")            // əvvələ
meyvələr.sil(1)                        // indeksə görə
meyvələr.silDəyər("üzüm")              // dəyərə görə
meyvələr.sırala()
meyvələr.tərsinəÇevir()
```

### Gəzmək
```alqor
hər m üçün meyvələr içində
    yaz(m)
son

hər i, m üçün meyvələr içində
    yaz("{i + 1}. {m}")
son
```

### Güclü metodlar
```alqor
dəyişən ədədlər = [3, 1, 4, 1, 5, 9, 2, 6]

yaz(ədədlər.cəm())                          // 31
yaz(ədədlər.orta())                         // 3.875
yaz(ədədlər.maksimum())                     // 9
yaz(ədədlər.minimum())                      // 1
yaz(ədədlər.sıralanmış())                   // [1,1,2,3,4,5,6,9]
yaz(ədədlər.təkrarsız())                    // [3,1,4,5,9,2,6]
yaz(ədədlər.filtr((x) => x > 3))            // [4,5,9,6]
yaz(ədədlər.çevir((x) => x * 2))            // [6,2,8,2,10,18,4,12]
yaz(ədədlər.ehtiva(5))                      // doğru
yaz(ədədlər.tap((x) => x > 4))              // 5
yaz(ədədlər.hamısı((x) => x > 0))           // doğru
yaz(ədədlər.hərHansı((x) => x > 8))         // doğru
```

### Siyahı qurma
```alqor
dəyişən kvadratlar = [x * x üçün x içində 1..10]
dəyişən cütlər = [x üçün x içində 1..20 əgər x % 2 == 0]
```

**Tapşırıq:** 10 ədədlik siyahı yaradın. Ən böyüyünü, ən kiçiyini və ortasını tapın.

---

## Dərs 9 — Lüğətlər

```alqor
dəyişən yaşlar = {"Aysel": 24, "Rəşad": 31, "Nigar": 28}

yaz(yaşlar["Aysel"])                   // 24
yaşlar["Tural"] = 35                   // əlavə
yaşlar.sil("Rəşad")                    // silmək

yaz(yaşlar.ehtiva("Nigar"))            // doğru
yaz(yaşlar.açarlar())                  // ["Aysel", "Nigar", "Tural"]
yaz(yaşlar.dəyərlər())                 // [24, 28, 35]
yaz(uzunluq(yaşlar))                   // 3
```

### Gəzmək
```alqor
hər ad, yaş üçün yaşlar içində
    yaz("{ad} — {yaş} yaş")
son
```

### Təhlükəsiz oxumaq
```alqor
yaz(yaşlar["Yoxdur"])                  // ✖ xəta atır
yaz(yaşlar.al("Yoxdur", 0))            // 0 — standart dəyər
```

**Tapşırıq:** Mətn verilir. Hər hərfin neçə dəfə təkrarlandığını lüğətə yığın.

---

## Dərs 10 — Funksiyalar

```alqor
funksiya salamla()
    yaz("Salam!")
son

salamla()
```

### Parametrlərlə
```alqor
funksiya salamla(ad: mətn)
    yaz("Salam, {ad}!")
son

salamla("Aysel")
```

### Dəyər qaytaran
```alqor
funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son

dəyişən n = topla(3, 4)
yaz(n)                       // 7
```

### Standart dəyərlər
```alqor
funksiya salamla(ad: mətn = "dünya")
    yaz("Salam, {ad}!")
son

salamla()                    // Salam, dünya!
salamla("Aysel")             // Salam, Aysel!
```

### Adlı arqumentlər
```alqor
funksiya qur(en: tam, hündürlük: tam, rəng: mətn = "ağ")
    yaz("{en}x{hündürlük}, {rəng}")
son

qur(hündürlük: 200, en: 100)           // sıra önəmli deyil
qur(100, 200, rəng: "qırmızı")
```

### Çoxlu dəyər qaytarmaq
```alqor
funksiya böl(a: tam, b: tam) -> kortej[tam, tam]
    qaytar (a ~/ b, a % b)
son

dəyişən tam, qalıq = böl(17, 5)
yaz("{tam} tam, {qalıq} qalıq")        // 3 tam, 2 qalıq
```

### Kiçik funksiyalar (lambda)
```alqor
dəyişən ikiqat = (x) => x * 2
yaz(ikiqat(21))                        // 42

yaz([1,2,3].çevir((x) => x * 10))      // [10, 20, 30]
```

**Tapşırıq:** Ədədin sadə olub-olmadığını yoxlayan funksiya yazın.

---

## Dərs 11 — Xətalarla işləmək

```alqor
cəhd et
    dəyişən n = tamƏt(oxu("Ədəd daxil edin: "))
    yaz("İki qatı: {n * 2}")
tut (x: ÇevrilməXətası)
    yaz("Bu ədəd deyil!")
son
```

### Bir neçə xəta növü
```alqor
cəhd et
    dəyişən m = fayl.oxu("məlumat.txt")
    yaz(m)
tut (x: FaylTapılmadıXətası)
    yaz("Fayl yoxdur")
tut (x: İcazəXətası)
    yaz("İcazəniz yoxdur")
nəhayət
    yaz("Bu həmişə işləyir")
son
```

### Öz xətanızı atmaq
```alqor
funksiya yaşQoy(yaş: tam)
    əgər yaş < 0 onda
        at ArqumentXətası("Yaş mənfi ola bilməz: {yaş}")
    son
    yaz("Yaş: {yaş}")
son
```

### `boş` ilə iş
```alqor
dəyişən ad: mətn? = boş

əgər ad boş deyil onda
    yaz(ad.böyüyə())
son

yaz(ad ?? "Qonaq")                     // boşdursa "Qonaq"
yaz(ad?.uzunluq())                     // boşdursa boş
```

**Tapşırıq:** İstifadəçidən ədəd alın, düzgün daxil edilənə qədər təkrar soruşun.

---

## Dərs 12 — Siniflər

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

    metod yaşArtır()
        özü.yaş += 1
    son
son

dəyişən a = yeni İnsan("Aysel", 24)
a.təqdim()
a.yaşArtır()
yaz(a.yaş)                   // 25
```

### Qısa yazılış
```alqor
sinif İnsan
    qurucu(açıq xassə ad: mətn, açıq xassə yaş: tam)

    metod təqdim()
        yaz("Mən {özü.ad}")
    son
son
```

### Miras
```alqor
sinif Tələbə miras İnsan
    xassə universitet: mətn

    qurucu(ad: mətn, yaş: tam, universitet: mətn)
        üst(ad, yaş)
        özü.universitet = universitet
    son

    əvəz et metod təqdim()
        üst.təqdim()
        yaz("{özü.universitet}-də oxuyuram.")
    son
son
```

### Hesablanan xassə
```alqor
sinif Düzbucaqlı
    qurucu(açıq xassə en: onluq, açıq xassə hündürlük: onluq)

    xassə sahə: onluq
        oxu qaytar özü.en * özü.hündürlük son
    son
son

dəyişən d = yeni Düzbucaqlı(3, 4)
yaz(d.sahə)                  // 12.0  — mötərizə yoxdur!
```

**Tapşırıq:** `BankHesabı` sinfi yazın — balans, `yatır()`, `çıxar()`, `göstər()`.

---

## Dərs 13 — Fayllarla iş

```alqor
gətir fayl

// Yazmaq
fayl.yaz("qeyd.txt", "Salam, dünya!")

// Oxumaq
dəyişən m = fayl.oxu("qeyd.txt")
yaz(m)

// Sətir-sətir
hər sətir üçün fayl.oxuSətirlər("qeyd.txt") içində
    yaz(sətir)
son

// Əlavə etmək
fayl.əlavəEt("qeyd.txt", "\nYeni sətir")

// Yoxlamaq
əgər fayl.vardır("qeyd.txt") onda
    yaz("Fayl var, ölçüsü: {fayl.ölçü("qeyd.txt")} bayt")
son
```

**Tapşırıq:** Mətn faylındakı sətirlərin və sözlərin sayını hesablayın.

---

## Dərs 14 — Modullar

### `riyazi.alq`
```alqor
ixrac et funksiya kvadrat(x: onluq) -> onluq
    qaytar x * x
son

ixrac et sabit Pİ = 3.14159

funksiya gizliKöməkçi()      // ixrac olunmur
    ...
son
```

### `əsas.alq`
```alqor
gətir "./riyazi.alq" kimi r

yaz(r.kvadrat(5))            // 25.0
yaz(r.Pİ)
```

Və ya:
```alqor
gətir "./riyazi.alq".{kvadrat, Pİ}

yaz(kvadrat(5))
```

---

## Dərs 15 — Testlər

### `sınaq/riyazi_sınaq.alq`
```alqor
gətir test
gətir "../mənbə/riyazi.alq".{kvadrat}

@sınaq
funksiya kvadratDüzgündür()
    test.bərabər(kvadrat(5), 25.0)
    test.bərabər(kvadrat(0), 0.0)
    test.bərabər(kvadrat(-3), 9.0)
son
```

```bash
alqortest
```

---

## Dərs 16 — Asinxron kod

```alqor
gətir http

asinxron funksiya əsas()
    dəyişən c = gözlə http.al("https://alqor.vuqar.pro/api/vaxt")
    yaz(c.mətn())
son
```

### Paralel
```alqor
asinxron funksiya əsas()
    // Ardıcıl — 3 saniyə
    dəyişən a = gözlə al("/a")
    dəyişən b = gözlə al("/b")
    dəyişən c = gözlə al("/c")

    // Paralel — 1 saniyə
    dəyişən (x, y, z) = gözlə paralel(al("/a"), al("/b"), al("/c"))
son
```

---

## Dərs 17 — Tam nümunə: Tapşırıq siyahısı

```alqor
gətir fayl
gətir json

sinif Tapşırıq
    qurucu(açıq xassə mətn: mətn, açıq xassə bitib: məntiq = yanlış)

    metod göstər(i: tam)
        dəyişən işarə = əgər özü.bitib onda "✓" yoxsa " " son
        yaz("{i + 1}. [{işarə}] {özü.mətn}")
    son
son

dəyişən tapşırıqlar: siyahı[Tapşırıq] = []
sabit FAYL = "tapşırıqlar.json"

funksiya yüklə()
    əgər fayl.vardır(FAYL) onda
        hər t üçün json.oxu(fayl.oxu(FAYL)) içində
            tapşırıqlar.əlavə(yeni Tapşırıq(t["mətn"], t["bitib"]))
        son
    son
son

funksiya saxla()
    fayl.yaz(FAYL, json.yaz(tapşırıqlar))
son

funksiya göstər()
    əgər boşdur(tapşırıqlar) onda
        yaz("Tapşırıq yoxdur.")
        qaytar
    son
    hər i, t üçün tapşırıqlar içində
        t.göstər(i)
    son
son

funksiya əsas()
    yüklə()

    həmişə
        yaz("")
        göstər()
        yaz("")
        yaz("1-Əlavə et  2-Bitir  3-Sil  4-Çıxış")
        dəyişən seçim = oxu("Seçiminiz: ")

        seç seçim
            hal "1"
                dəyişən m = oxu("Tapşırıq: ")
                tapşırıqlar.əlavə(yeni Tapşırıq(m))
                saxla()

            hal "2"
                dəyişən n = oxuTam("Nömrə: ") - 1
                əgər n >= 0 və n < uzunluq(tapşırıqlar) onda
                    tapşırıqlar[n].bitib = doğru
                    saxla()
                yoxsa
                    yaz("Yanlış nömrə")
                son

            hal "3"
                dəyişən n = oxuTam("Nömrə: ") - 1
                əgər n >= 0 və n < uzunluq(tapşırıqlar) onda
                    tapşırıqlar.sil(n)
                    saxla()
                son

            hal "4"
                yaz("Sağ olun!")
                dayan

            digər hallarda
                yaz("Yanlış seçim")
        son
    son
son
```

```bash
alqor işlət tapşırıq.alq
```

---

**Növbəti:** [3. Veb Dərsliyi](02-VEB-DERSLIYI.md)
