# Alqor — Bölmə 9: Asinxron və Paralel Proqramlaşdırma

---

## 9.1 Model

Alqor iki ayrı mexanizm təklif edir:

| Mexanizm | Nə üçün | Açar sözlər |
|---|---|---|
| **Asinxron** (`asinxron`/`gözlə`) | Giriş-çıxış gözləməsi: şəbəkə, fayl, verilənlər bazası | tək ipdə, hadisə dövrü |
| **Paralel** (`sap`) | CPU-intensiv hesablama | həqiqi çoxnüvəli icra |

---

## 9.2 `asinxron` və `gözlə`

```alqor
asinxron funksiya məlumatAl(url: mətn) -> mətn
    dəyişən cavab = gözlə http.al(url)
    qaytar cavab.mətn()
son

asinxron funksiya əsas()
    dəyişən m = gözlə məlumatAl("https://vuqar.pro/alqor/api/istifadəçilər")
    yaz(m)
son
```

### Qaydalar
- `gözlə` yalnız `asinxron` funksiya daxilində işlənir (`ALQ-P013`).
- `asinxron` funksiya `Gələcək[T]` qaytarır.
- `gözlə` `Gələcək[T]`-ni `T`-yə açır.
- `əsas()` də `asinxron` ola bilər.

```alqor
asinxron funksiya f() -> tam
    qaytar 42
son

dəyişən g: Gələcək[tam] = f()     // hələ icra olunmayıb
dəyişən n: tam = gözlə g          // indi icra olunur və gözlənir
```

---

## 9.3 Paralel icra

```alqor
asinxron funksiya nümunə()
    // Ardıcıl — 3 saniyə
    dəyişən a = gözlə gecikmə(1000)
    dəyişən b = gözlə gecikmə(1000)
    dəyişən c = gözlə gecikmə(1000)

    // Paralel — 1 saniyə
    dəyişən (x, y, z) = gözlə paralel(
        gecikmə(1000),
        gecikmə(1000),
        gecikmə(1000)
    )
son
```

### `paralel` modulunun funksiyaları

```alqor
gətir paralel

// Hamısını gözlə
dəyişən nəticələr = gözlə paralel.hamısı([f1(), f2(), f3()])

// Hamısını gözlə, xətalara dözümlü
dəyişən nəticələr = gözlə paralel.hamısıNəticə([f1(), f2()])
// → [Uğur(...), Xəta(...)]

// İlk bitəni götür, qalanları ləğv et
dəyişən ilk = gözlə paralel.ilkBitən([f1(), f2()])

// İlk uğurlu olanı
dəyişən ilkUğur = gözlə paralel.ilkUğurlu([f1(), f2()])

// Məhdud paralellik (eyni anda maksimum 5)
dəyişən hamısı = gözlə paralel.məhdud(5, sorğular)

// Siyahı üzərində paralel çevirmə
dəyişən cavablar = gözlə paralel.çevir(urllər, (u) => http.al(u))
```

---

## 9.4 Vaxt və gecikmə

```alqor
gətir vaxt

gözlə vaxt.gözlə(1000)                 // 1 saniyə gözlə (ms)
gözlə vaxt.gözləSaniyə(1.5)

// Vaxt məhdudiyyəti
dəyişən n = gözlə vaxt.limitlə(5000, uzunƏməliyyat())
// 5 saniyədən çox çəkərsə VaxtBitdiXətası

// Təkrarlanan
dəyişən taymer = vaxt.interval(1000, () => yaz("hər saniyə"))
taymer.dayandır()

// Bir dəfəlik gecikmə
vaxt.sonra(3000, () => yaz("3 saniyə sonra"))
```

---

## 9.5 Ləğvetmə

```alqor
dəyişən ləğv = yeni LəğvNişanı()

asinxron funksiya uzunİş(nişan: LəğvNişanı)
    hər i üçün 1..1000 içində
        nişan.yoxla()                   // ləğv olunubsa LəğvXətası atır
        gözlə addım(i)
    son
son

// Başqa yerdən:
ləğv.ləğvEt()

// Və ya avtomatik vaxt ilə:
dəyişən ləğv = LəğvNişanı.vaxtla(5000)
```

---

## 9.6 Saplar (həqiqi paralellik)

```alqor
gətir sap

// Sap yaratmaq
dəyişən s = sap.başlat(funksiya()
    yaz("Paralel sapda işləyir")
    qaytar ağırHesablama()
son)

dəyişən nəticə = s.gözlə()

// Sap hovuzu
dəyişən hovuz = sap.hovuz(ölçü: 4)
dəyişən nəticələr = hovuz.xəritələ(verilənlər, (x) => emal(x))
hovuz.bağla()

// Nüvə sayı
yaz(sap.nüvəSayı())
```

### Sapların ünsiyyəti — kanallar (ətraflı: § 9.13)
```alqor
dəyişən kanal = yeni Kanal[tam](tutum: 10)

sap.başlat(funksiya()
    hər i üçün 1..5 içində
        kanal.göndər(i)
    son
    kanal.bağla()
son)

hər dəyər üçün kanal içində
    yaz("Alındı: {dəyər}")
son
```

### Paylaşılan vəziyyət
```alqor
dəyişən kilid = yeni Kilid()
dəyişən sayğac = 0

funksiya artır()
    kilid.tut()
    gecikdir kilid.burax()
    sayğac += 1
son

// Və ya qısa:
funksiya artır2()
    kilid.ilə(funksiya()
        sayğac += 1
    son)
son

// Atomik tiplər (kilidsiz)
dəyişən atomSayğac = yeni Atomik[tam](0)
atomSayğac.artır()
yaz(atomSayğac.oxu())
```

### Digər sinxronizasiya alətləri
```alqor
yeni Kilid()                    // qarşılıqlı istisna (mutex)
yeni OxuYazKilidi()             // bir yazıcı / çox oxucu
yeni Semafor(5)                 // sayğaclı semafor
yeni Baryer(4)                  // 4 sap görüşənə qədər gözlə
yeni Hadisə()                   // siqnal gözləmə
```

---

## 9.7 Axınlar (stream)

```alqor
gətir axın

// Asinxron iterasiya
asinxron funksiya oxu()
    hər sətir üçün fayl.axınOxu("böyük.txt") içində gözlə
        yaz(sətir)
    son
son

// Axın generatoru
asinxron generator funksiya saylar() -> tam
    hər i üçün 1..10 içində
        gözlə vaxt.gözlə(100)
        ver i
    son
son

// Axın əməliyyatları
dəyişən nəticə = gözlə saylar()
    .filtr((x) => x % 2 == 0)
    .çevir((x) => x * 10)
    .topla()
```

---

## 9.8 Hadisə dövrü

```alqor
gətir dövr

// Növbəti iterasiyada icra et
dövr.növbəti(() => yaz("sonra"))

// Mikro tapşırıq
dövr.mikro(() => yaz("daha tez"))

// Hadisə dövrünü əl ilə idarə etmək (ixtisaslaşmış hallar)
dövr.işlət()
dövr.bir_addım()
dövr.dayandır()
```

---

## 9.9 Hədəflər üzrə fərqlər

| Xüsusiyyət | Native (Linux) | Veb (brauzer) | WASM |
|---|---|---|---|
| `asinxron`/`gözlə` | ✓ | ✓ | ✓ |
| `sap` | ✓ (OS sapları) | ✓ (Web Worker) | ✓ (wasm threads) |
| `Kanal` | ✓ | ✓ (postMessage) | ✓ |
| `Kilid`, `Atomik` | ✓ | ✓ (SharedArrayBuffer) | ✓ |
| `fayl` G/Ç | ✓ | ✖ (`brauzer.fayl` istifadə edin) | məhdud |
| Bloklayan çağırış | ✓ | ✖ | ✖ |

Kompilyator hədəfə uyğun olmayan API işlədildikdə `ALQ-T070` verir.

---

## 9.10 Asinxron xəta idarəetməsi

```alqor
asinxron funksiya risk()
    cəhd et
        dəyişən c = gözlə http.al("https://nümunə.az")
        yaz(c.mətn())
    tut (x: ŞəbəkəXətası)
        yaz("Şəbəkə problemi: {x.mesaj}")
    tut (x: VaxtBitdiXətası)
        yaz("Vaxt bitdi")
    nəhayət
        yaz("bitdi")
    son
son

// Paralel əməliyyatlarda
dəyişən nəticələr = gözlə paralel.hamısıNəticə([f1(), f2(), f3()])
hər n üçün nəticələr içində
    seç n
        hal Uğur(d) → yaz("OK: {d}")
        hal Xəta(x) → yaz("Xəta: {x.mesaj}")
    son
son
```

> **Diqqət:** `gözlə` edilməyən `Gələcək` xəta atsa, `ALQ-R020` xəbərdarlığı verilir:
> "Gözlənilməyən gələcəkdə tutulmamış xəta".

---

## 9.12 Aktyorlar

Aktyor öz vəziyyətini qoruyan obyektdir: ona xaricdən edilən hər metod
çağırışı **mesajdır**. Mesaj aktyorun poçtuna düşür, çağırana dərhal
`Gələcək` qayıdır; mesajlar **gəliş sırası ilə, bir-bir** emal olunur.
Ona görə aktyorun vəziyyəti heç vaxt eyni anda iki yerdən dəyişdirilmir —
kilidə ehtiyac yoxdur.

```alqor
aktyor Bank
    xassə balans = 0

    metod yatır(məbləğ: tam) -> tam
        özü.balans += məbləğ
        qaytar özü.balans
    son

    metod çək(məbləğ: tam) -> tam
        əgər məbləğ > özü.balans onda
            at Xəta("balans çatmır")
        son
        özü.balans -= məbləğ
        qaytar özü.balans
    son
son

dəyişən hesab = Bank()
hesab.yatır(100)                    // mesaj — cavab gözlənilmir
dəyişən g = hesab.çək(30)           // Gələcək[tam]
yaz(gözlə g)                        // 70
```

### Qaydalar

- `aktyor Ad … son` sinif kimi yazılır: `xassə`, `metod`, `qurucu`,
  `miras`, `tətbiq`. `aktyor` kontekstli sözdür.
- Xaricdən `obyekt.metod(…)` → mesaj, nəticə `Gələcək[T]`. Aktyorun öz
  daxilində (`özü.metod()`, qurucu və mesaj emal olunarkən) çağırış
  birbaşadır.
- Mesajlar **tənbəl** emal olunur: nəticə gözlənəndə (`gözlə`), aktyorun
  xassəsi xaricdən oxunanda və ya yazılanda, və proqramın sonunda. Hər
  halda əvvəlki mesajlar əvvəl emal olunur (FIFO).
- Mesajda atılan xəta onun `Gələcək`-i gözlənəndə atılır. Heç kimin
  gözləmədiyi mesajdakı xəta proqramın sonunda tutulmamış xəta olur.
- Aktyorun metodu başqa aktyora mesaj göndərə bilər; mesajlar hər
  aktyorun öz poçtunda sıralanır.
- Bu model bütün icraçılarda (`--motor py|rs`, `--js`) eyni nəticə verir.

---

## 9.13 Kanallar

`Kanal` — saplar və aktyorlar arasında FIFO mesaj növbəsi.

```alqor
dəyişən k = Kanal()                     // və ya yeni Kanal[tam](tutum: 10)
k.göndər(1)
k.göndər(2)
k.bağla()

hər x üçün k içində                     // bağlanıb boşalana qədər
    yaz(x)
son
```

| Metod | Mənası |
|---|---|
| `göndər(x)` | Növbənin sonuna əlavə edir; bağlanmış kanalda `KanalXətası` (`ALQ-R019`) |
| `al()` | Növbəti dəyər; kanal bağlanıb boşdursa `boş`. Boşdursa və bağlanmayıbsa göndərən sapı gözləyir |
| `cəhdAl()` | Gözləmədən: növbəti dəyər və ya `boş` |
| `bağla()` | Yeni göndərmələri bağlayır; qalan dəyərlər oxuna bilər |
| `bağlıdır()`, `boşdur()`, `uzunluq()` | Vəziyyət |

- Boş və bağlanmamış kanaldan oxuyanda göndərə biləcək başqa sap yoxdursa
  — **dalan**: `DalanXətası` (`ALQ-R018`).
- `tutum` dolu olanda göndərən **sap** oxuyanı gözləyir (Python
  icraçısında). Tək axınlı icraçılarda (Rust, JS) `sap.başlat` dərhal
  işlədiyi üçün növbə genişlənir — nəticə eynidir.
- Xəta tipləri: `ParalellikXətası` → `KanalXətası`, `DalanXətası`.

---

## 9.11 Asinxron xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-P013` | `gözlə` asinxron olmayan funksiyada |
| `ALQ-T070` | Bu API hədəf platformada mövcud deyil |
| `ALQ-T071` | `Gələcək` gözlənilmədən istifadə olunub |
| `ALQ-R011` | Vaxt bitdi |
| `ALQ-R017` | Paralel giriş münaqişəsi (data race) |
| `ALQ-R018` | Kilid dalanı (deadlock) aşkarlandı |
| `ALQ-R019` | Bağlanmış kanala göndərmə |
| `ALQ-R020` | ⚠ Gözlənilməyən gələcəkdə tutulmamış xəta |
| `ALQ-R021` | Əməliyyat ləğv edildi |
