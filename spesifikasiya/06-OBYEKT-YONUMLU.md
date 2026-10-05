# Alqor — Bölmə 6: Obyekt Yönümlü Proqramlaşdırma

---

## 6.1 Sinif

### Sintaksis
```
[açıq|gizli] [mücərrəd] sinif <Ad>[[generiklər]] [miras <Baza>] [tətbiq <İnterfeys>, ...]
    <üzvlər>
son
```

### Sadə sinif
```alqor
sinif İnsan
    xassə ad: mətn
    xassə yaş: tam

    qurucu(ad: mətn, yaş: tam)
        özü.ad = ad
        özü.yaş = yaş
    son

    metod salamla()
        yaz("Salam, mən {özü.ad}")
    son

    metod yaşArtır()
        özü.yaş += 1
    son
son

dəyişən a = yeni İnsan("Aysel", 24)
a.salamla()                            // Salam, mən Aysel
a.yaşArtır()
yaz(a.yaş)                             // 25
```

---

## 6.2 Xassələr (sahələr)

```alqor
sinif Məhsul
    xassə ad: mətn                           // açıq (standart)
    açıq xassə qiymət: onluq
    gizli xassə _anbarKodu: mətn             // yalnız sinif daxilində
    qorunan xassə yaradılmaTarixi: Tarix     // sinif + varislər

    statik xassə ümumiSay: tam = 0           // sinifə məxsus
    sabit xassə VERGİ: onluq = 0.18          // dəyişməz

    xassə endirim: onluq = 0.0               // standart dəyər
son
```

### Hesablanan xassələr
```alqor
sinif Düzbucaqlı
    xassə en: onluq
    xassə hündürlük: onluq

    xassə sahə: onluq
        oxu
            qaytar özü.en * özü.hündürlük
        son
    son

    xassə perimetr: onluq
        oxu qaytar 2 * (özü.en + özü.hündürlük) son
    son

    xassə diaqonal: onluq
        oxu
            qaytar riyaziyyat.kök(özü.en ** 2 + özü.hündürlük ** 2)
        son
        yaz(dəyər)
            // nisbəti saxlayaraq ölçünü dəyişir
            dəyişən nisbət = dəyər / özü.diaqonal
            özü.en *= nisbət
            özü.hündürlük *= nisbət
        son
    son
son

dəyişən d = yeni Düzbucaqlı(3, 4)
yaz(d.sahə)              // 12.0    — metod kimi çağırılmır
d.diaqonal = 10          // yazıcı işə düşür
```

### Tənbəl xassələr
```alqor
sinif Konfiqurasiya
    tənbəl xassə verilənlər: lüğət[mətn, istənilən]
        qaytar json.oxu(fayl.oxu("config.json"))
    son
son
// `verilənlər`-ə ilk müraciətdə hesablanır, sonra keşlənir
```

---

## 6.3 Qurucu (constructor)

```alqor
sinif Nöqtə
    xassə x: onluq
    xassə y: onluq

    // Əsas qurucu
    qurucu(x: onluq, y: onluq)
        özü.x = x
        özü.y = y
    son

    // Adlı qurucu
    qurucu sıfır()
        özü.x = 0
        özü.y = 0
    son

    qurucu qütb(radius: onluq, bucaq: onluq)
        özü.x = radius * riyaziyyat.kos(bucaq)
        özü.y = radius * riyaziyyat.sin(bucaq)
    son
son

dəyişən a = yeni Nöqtə(3, 4)
dəyişən b = yeni Nöqtə.sıfır()
dəyişən c = yeni Nöqtə.qütb(5, 0.927)
```

### Qısa qurucu (avtomatik mənimsətmə)
```alqor
sinif İnsan
    qurucu(açıq xassə ad: mətn, açıq xassə yaş: tam)
    // gövdə lazım deyil — xassələr avtomatik yaradılır və mənimsədilir
son
```

### Dağıdıcı
```alqor
sinif Fayl
    gizli xassə _tutacaq: tam

    silinsin()
        sistem.faylBağla(özü._tutacaq)
    son
son
```
`silinsin()` obyekt zibil yığıcı tərəfindən silinərkən çağırılır.
**Determinist təmizləmə üçün `gecikdir` və ya `istifadə` bloku üstündür:**

```alqor
istifadə f = fayl.aç("a.txt")
    yaz(f.oxu())
son                      // blokun sonunda f.bağla() avtomatik çağırılır
```

---

## 6.4 Metodlar

```alqor
sinif Kalkulyator
    gizli xassə _nəticə: onluq = 0

    metod əlavə(x: onluq) -> Kalkulyator
        özü._nəticə += x
        qaytar özü                        // zəncirləmə üçün
    son

    metod çıx(x: onluq) -> Kalkulyator
        özü._nəticə -= x
        qaytar özü
    son

    metod nəticə() -> onluq
        qaytar özü._nəticə
    son

    statik metod yarat() -> Kalkulyator
        qaytar yeni Kalkulyator()
    son

    gizli metod _daxili()
        ...
    son
son

yaz(Kalkulyator.yarat().əlavə(5).çıx(2).nəticə())   // 3.0
```

### Xüsusi metodlar (operator yükləməsi)

| Metod | Operator / İstifadə |
|---|---|
| `mətnƏt()` | `"{obyekt}"`, `yaz(obyekt)` |
| `bərabərdir(digər)` | `==`, `!=` |
| `müqayisə(digər)` | `<`, `>`, `<=`, `>=`, `<=>`, `sırala()` |
| `heş()` | lüğət açarı, dəst elementi |
| `klonla()` | `.klonla()` |
| `topla(digər)` | `+` |
| `çıx(digər)` | `-` |
| `vur(digər)` | `*` |
| `böl(digər)` | `/` |
| `qalıq(digər)` | `%` |
| `qüvvət(digər)` | `**` |
| `əks()` | tək operandlı `-` |
| `al(indeks)` | `obyekt[i]` oxuma |
| `qoy(indeks, dəyər)` | `obyekt[i] = x` yazma |
| `uzunluq()` | `uzunluq(obyekt)` |
| `ehtiva(element)` | `içindədir` |
| `iterator()` | `hər ... içində` |
| `çağır(...)` | `obyekt(...)` — funksiya kimi çağırış |

```alqor
sinif Vektor
    xassə x: onluq
    xassə y: onluq

    qurucu(açıq xassə x: onluq, açıq xassə y: onluq)

    metod topla(d: Vektor) -> Vektor
        qaytar yeni Vektor(özü.x + d.x, özü.y + d.y)
    son

    metod vur(k: onluq) -> Vektor
        qaytar yeni Vektor(özü.x * k, özü.y * k)
    son

    metod bərabərdir(d: Vektor) -> məntiq
        qaytar özü.x == d.x və özü.y == d.y
    son

    metod mətnƏt() -> mətn
        qaytar "({özü.x}, {özü.y})"
    son
son

dəyişən a = yeni Vektor(1, 2)
dəyişən b = yeni Vektor(3, 4)
yaz(a + b)               // (4.0, 6.0)
yaz(a * 2)               // (2.0, 4.0)
yaz(a == b)              // yanlış
```

---

## 6.5 `özü` və `üst`

```alqor
sinif Baza
    metod salam()
        yaz("Baza salam")
    son
son

sinif Törəmə miras Baza
    əvəz et metod salam()
        üst.salam()                  // baza metodunu çağır
        yaz("Törəmə salam")
    son

    metod digər()
        özü.salam()                  // öz metodunu çağır
    son
son
```

`özü` metod daxilində obyektə istinaddır. **Həmişə açıq yazılmalıdır** —
`ad` və `özü.ad` fərqli şeylərdir (`ALQ-T050` lokal dəyişən kölgələməsi).

---

## 6.6 Miras

```alqor
sinif Heyvan
    xassə ad: mətn

    qurucu(ad: mətn)
        özü.ad = ad
    son

    metod səs() -> mətn
        qaytar "..."
    son

    metod təqdim()
        yaz("{özü.ad}: {özü.səs()}")
    son
son

sinif İt miras Heyvan
    qurucu(ad: mətn)
        üst(ad)                      // baza qurucusunu çağır (ilk sətirdə)
    son

    əvəz et metod səs() -> mətn
        qaytar "Hav-hav"
    son
son

sinif Pişik miras Heyvan
    qurucu(ad: mətn)
        üst(ad)
    son

    əvəz et metod səs() -> mətn
        qaytar "Miyav"
    son
son

dəyişən heyvanlar: siyahı[Heyvan] = [yeni İt("Bozo"), yeni Pişik("Pamuk")]
hər h üçün heyvanlar içində
    h.təqdim()               // polimorfizm
son
// Bozo: Hav-hav
// Pamuk: Miyav
```

### Qaydalar
- **Tək miras** — yalnız bir baza sinif. Çoxlu davranış üçün interfeys.
- `əvəz et` **məcburidir** — unutsanız `ALQ-T051`.
- `qurucu`-da `üst(...)` birinci ifadə olmalıdır.
- Metod bağlanması **virtualdır** (dinamik dispetçerləşmə).
- `son` modifikatoru mirası bağlayır:
```alqor
son sinif Tamamlanmış ... son        // bundan miras alınmaz
son metod dəyişməz() ... son         // bu metod əvəz edilməz
```

---

## 6.7 Mücərrəd siniflər

```alqor
mücərrəd sinif Fiqur
    mücərrəd metod sahə() -> onluq           // gövdəsiz
    mücərrəd metod perimetr() -> onluq

    metod təsvir()                            // adi metod
        yaz("Sahə: {özü.sahə()}, Perimetr: {özü.perimetr()}")
    son
son

sinif Dairə miras Fiqur
    xassə radius: onluq
    qurucu(açıq xassə radius: onluq)

    əvəz et metod sahə() -> onluq
        qaytar riyaziyyat.Pİ * özü.radius ** 2
    son

    əvəz et metod perimetr() -> onluq
        qaytar 2 * riyaziyyat.Pİ * özü.radius
    son
son

dəyişən f = yeni Fiqur()          // ✖ ALQ-T052 — mücərrəd sinif yaradılmaz
dəyişən d = yeni Dairə(5)         // ✓
```

---

## 6.8 İnterfeyslər

```alqor
interfeys Çapedilən
    metod mətnƏt() -> mətn
son

interfeys Müqayisəedilən[T]
    metod müqayisə(digər: T) -> tam
son

interfeys Saxlanıla_bilən
    metod yaddaşaYaz(yol: mətn)
    metod yaddaşdanOxu(yol: mətn)

    // Standart tətbiq (ixtiyari)
    metod ehtiyatNüsxə()
        özü.yaddaşaYaz("ehtiyat.dat")
    son
son

sinif Sənəd tətbiq Çapedilən, Saxlanıla_bilən
    xassə başlıq: mətn
    qurucu(açıq xassə başlıq: mətn)

    metod mətnƏt() -> mətn
        qaytar "Sənəd: {özü.başlıq}"
    son

    metod yaddaşaYaz(yol: mətn)
        fayl.yaz(yol, özü.başlıq)
    son

    metod yaddaşdanOxu(yol: mətn)
        özü.başlıq = fayl.oxu(yol)
    son
son
```

### İnterfeys mirası
```alqor
interfeys Oxunan
    metod oxu() -> mətn
son

interfeys Yazılan
    metod yaz(m: mətn)
son

interfeys OxunanYazılan miras Oxunan, Yazılan
son
```

### İnterfeys tipi kimi istifadə
```alqor
funksiya çapEt(x: Çapedilən)
    yaz(x.mətnƏt())
son

dəyişən siyahı: siyahı[Çapedilən] = [sənəd1, sənəd2]
```

---

## 6.9 Strukturlar (dəyər tipləri)

```alqor
struktur Nöqtə
    xassə x: onluq
    xassə y: onluq
son

dəyişən a = Nöqtə(x: 1, y: 2)      // `yeni` lazım deyil
dəyişən b = a                       // KOPYA yaradılır
b.x = 99
yaz(a.x)                            // 1 — dəyişmədi
```

| Xüsusiyyət | `sinif` | `struktur` |
|---|---|---|
| Semantika | istinad | dəyər (kopya) |
| Miras | ✓ | ✖ |
| İnterfeys tətbiqi | ✓ | ✓ |
| Metodlar | ✓ | ✓ |
| Qurucu | ✓ | avtomatik |
| Yaddaş | heap | stek |
| Standart `==` | identiklik | sahə-sahə |
| `boş` ola bilər | ✓ (`?` ilə) | ✓ (`?` ilə) |

Strukturlar kiçik, dəyişməz verilənlər üçündür: koordinat, rəng, tarix, pul.

---

## 6.10 Sadalama (enum)

### Sadə sadalama
```alqor
sadalama Rəng
    QIRMIZI
    YAŞIL
    MAVİ
son

dəyişən r = Rəng.QIRMIZI
yaz(r)                        // QIRMIZI
yaz(r.sıra())                 // 0
yaz(Rəng.hamısı())            // [QIRMIZI, YAŞIL, MAVİ]
yaz(Rəng.adla("MAVİ"))        // Rəng.MAVİ
```

### Dəyərli sadalama
```alqor
sadalama Status: tam
    GÖZLƏYİR = 0
    İCRADA = 1
    BİTDİ = 2
    XƏTA = -1
son

yaz(Status.BİTDİ.dəyər())     // 2
yaz(Status.dəyərlə(1))        // Status.İCRADA
```

### Zəngin sadalama (metodlu)
```alqor
sadalama Planet
    MERKURİ(3.303e23, 2.4397e6)
    VENERA(4.869e24, 6.0518e6)
    YER(5.976e24, 6.37814e6)

    xassə kütlə: onluq
    xassə radius: onluq

    qurucu(kütlə: onluq, radius: onluq)
        özü.kütlə = kütlə
        özü.radius = radius
    son

    metod cazibə() -> onluq
        qaytar 6.67300E-11 * özü.kütlə / (özü.radius ** 2)
    son
son

yaz(Planet.YER.cazibə())
```

### Cəbri sadalama (variantlı)
```alqor
sadalama Nəticə[T]
    Uğur(dəyər: T)
    Xəta(mesaj: mətn, kod: tam)
son

funksiya böl(a: tam, b: tam) -> Nəticə[onluq]
    əgər b == 0 onda
        qaytar Nəticə.Xəta("Sıfıra bölmə", 400)
    son
    qaytar Nəticə.Uğur(a / b)
son

seç böl(10, 2)
    hal Nəticə.Uğur(d) → yaz("Nəticə: {d}")
    hal Nəticə.Xəta(m, k) → yaz("Xəta {k}: {m}")
son
```

---

## 6.11 Genişləndirmə (extension)

Mövcud tipə yeni metod əlavə etmək — mənbə kodunu dəyişmədən:

```alqor
genişlət mətn
    metod tərsÇevir() -> mətn
        qaytar özü.simvollar().tərs().birləşdir("")
    son

    metod palindromdur() -> məntiq
        qaytar özü == özü.tərsÇevir()
    son
son

yaz("salam".tərsÇevir())        // malas
yaz("kək".palindromdur())       // doğru

genişlət siyahı[tam]
    metod cəmi() -> tam
        qaytar özü.yığ(0, (a, b) => a + b)
    son
son

yaz([1, 2, 3].cəmi())           // 6
```

---

## 6.12 Qarışıq (mixin)

```alqor
qarışıq Loglanan
    metod log(mesaj: mətn)
        yaz("[{tip(özü)}] {mesaj}")
    son
son

qarışıq Sayılan
    statik xassə say: tam = 0

    metod qeydiyyat()
        özü.sinif.say += 1
    son
son

sinif Servis ilə Loglanan, Sayılan
    metod işlət()
        özü.log("işləyir")
        özü.qeydiyyat()
    son
son
```

---

## 6.13 Statik üzvlər və tək nüsxə (singleton)

```alqor
sinif Konfiqurasiya
    statik gizli xassə _nüsxə: Konfiqurasiya?

    statik metod nüsxə() -> Konfiqurasiya
        özü._nüsxə ?= yeni Konfiqurasiya()
        qaytar özü._nüsxə!
    son
son

// Və ya birbaşa:
obyekt Jurnal                    // tək nüsxəli obyekt
    xassə səviyyə: mətn = "info"

    metod yaz(m: mətn)
        yaz("[{özü.səviyyə}] {m}")
    son
son

Jurnal.yaz("başladı")            // `yeni` lazım deyil
```

---

## 6.14 Görünüş modifikatorları

| Modifikator | Görünür |
|---|---|
| `açıq` | hər yerdən (standart) |
| `qorunan` | sinif + varislər |
| `gizli` | yalnız həmin sinif daxilində |
| `modul` | yalnız həmin modul daxilində |

```alqor
sinif Bank
    açıq xassə ad: mətn
    qorunan xassə filial: mətn
    gizli xassə _parol: mətn
    modul xassə daxiliKod: tam
son
```

---

## 6.15 OOP xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-T050` | `özü` yazılmayıb — lokal dəyişən kölgələyir |
| `ALQ-T051` | `əvəz et` tələb olunur |
| `ALQ-T052` | Mücərrəd sinifdən obyekt yaradıla bilməz |
| `ALQ-T053` | Mücərrəd metod tətbiq edilməyib |
| `ALQ-T054` | İnterfeys metodu tətbiq edilməyib |
| `ALQ-T055` | `son` sinifdən miras alınmaz |
| `ALQ-T056` | `son` metod əvəz edilməz |
| `ALQ-T057` | `gizli` üzvə kənardan müraciət |
| `ALQ-T058` | `üst(...)` qurucunun ilk ifadəsi olmalıdır |
| `ALQ-T059` | Dövri miras |
| `ALQ-T060` | `struktur` miras ala bilməz |
| `ALQ-T061` | Sadalama variantı tapılmadı |
