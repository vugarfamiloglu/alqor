# Alqor — Bölmə 7: Xəta İdarəetməsi

---

## 7.1 `cəhd et` / `tut` / `nəhayət`

### Sintaksis
```
cəhd et
    <gövdə>
[tut [(<ad>: <XətaTipi>)]
    <gövdə>]...
[nəhayət
    <gövdə>]
son
```

### Əsas istifadə
```alqor
cəhd et
    dəyişən n = tamƏt(oxu())
    yaz("Ədəd: {n}")
tut (x: ÇevrilməXətası)
    yaz("Bu ədəd deyil: {x.mesaj}")
son
```

### Bir neçə xəta tipi
```alqor
cəhd et
    dəyişən m = fayl.oxu("verilən.txt")
    dəyişən v = json.oxu(m)
    emal(v)
tut (x: FaylTapılmadıXətası)
    yaz("Fayl yoxdur: {x.yol}")
tut (x: JSONXətası)
    yaz("Format pozulub, sətir {x.sətir}")
tut (x: Xəta)
    yaz("Naməlum xəta: {x.mesaj}")
nəhayət
    yaz("Bu blok həmişə işləyir")
son
```

### Qruplaşdırılmış tutma
```alqor
cəhd et
    riskli()
tut (x: ŞəbəkəXətası | VaxtBitdiXətası)
    yaz("Bağlantı problemi")
son
```

### Şərtli tutma
```alqor
cəhd et
    sorğu()
tut (x: HTTPXətası) əgər x.kod == 404
    yaz("Tapılmadı")
tut (x: HTTPXətası) əgər x.kod >= 500
    yaz("Server xətası")
tut (x: HTTPXətası)
    yaz("Digər HTTP xətası: {x.kod}")
son
```

### Dəyişənsiz tutma
```alqor
cəhd et
    riskli()
tut
    yaz("Nəsə alınmadı")
son
```

### İfadə kimi
```alqor
dəyişən n = cəhd et
    ver tamƏt(giriş)
tut
    ver 0
son
```

---

## 7.2 `at` — xəta atmaq

```alqor
at Xəta("Nəsə səhv getdi")
at ArqumentXətası("Yaş mənfi ola bilməz: {yaş}")
at ŞəbəkəXətası("Bağlantı kəsildi", kod: 503)

// Tutulmuş xətanı yenidən atmaq
cəhd et
    riskli()
tut (x: Xəta)
    jurnal.xəta(x)
    at                      // eyni xətanı yenidən at
son

// Səbəb zənciri ilə
cəhd et
    aşağıSəviyyə()
tut (x: Xəta)
    at VerilənlərXətası("Verilən yüklənmədi", səbəb: x)
son
```

---

## 7.3 Xəta iyerarxiyası

```
Atılan
├── Xəta                          (bərpa oluna bilən)
│   ├── ArqumentXətası
│   │   ├── TipXətası
│   │   ├── DəyərXətası
│   │   └── DiapazonXətası
│   ├── ÇevrilməXətası
│   ├── RiyaziXəta
│   │   ├── BölməXətası
│   │   ├── DaşmaXətası
│   │   └── DəqiqlikXətası
│   ├── KolleksiyaXətası
│   │   ├── İndeksXətası
│   │   ├── AçarXətası
│   │   └── BoşKolleksiyaXətası
│   ├── GirişÇıxışXətası
│   │   ├── FaylTapılmadıXətası
│   │   ├── İcazəXətası
│   │   ├── DiskDoluXətası
│   │   └── FaylMəşğulXətası
│   ├── ŞəbəkəXətası
│   │   ├── BağlantıXətası
│   │   ├── VaxtBitdiXətası
│   │   ├── DNSXətası
│   │   └── HTTPXətası
│   ├── FormatXətası
│   │   ├── JSONXətası
│   │   ├── XMLXətası
│   │   └── KodlaşdırmaXətası
│   ├── VerilənlərBazasıXətası
│   │   ├── SorğuXətası
│   │   ├── ƏlaqəXətası
│   │   └── TranzaksiyaXətası
│   ├── BoşDəyərXətası
│   ├── PythonXətası              (Python kitabxanaları, § 8.14)
│   ├── VaxtXətası
│   └── İcazəsizXəta
│
└── KritikXəta                    (bərpa oluna bilməz, tutulmamalıdır)
    ├── YaddaşBitdiXətası
    ├── StekDaşmaXətası
    ├── İddiaXətası
    └── DaxiliXəta
```

---

## 7.4 Özəl xətalar

```alqor
sinif ÖdənişXətası miras Xəta
    xassə məbləğ: onluq
    xassə kart: mətn

    qurucu(mesaj: mətn, məbləğ: onluq, kart: mətn)
        üst(mesaj)
        özü.məbləğ = məbləğ
        özü.kart = kart
    son

    əvəz et metod mətnƏt() -> mətn
        qaytar "Ödəniş alınmadı: {özü.mesaj} ({özü.məbləğ} AZN)"
    son
son

at ÖdənişXətası("Balans kifayət etmir", 150.0, "****1234")
```

### Xəta sinfinin standart üzvləri

| Üzv | Tip | Mənası |
|---|---|---|
| `mesaj` | `mətn` | İzah |
| `kod` | `tam?` | Rəqəmli kod |
| `səbəb` | `Xəta?` | Alt xəta |
| `yığın()` | `siyahı[Kadr]` | Çağırış yığını |
| `yer()` | `mətn` | `fayl:sətir:sütun` |
| `mətnƏt()` | `mətn` | Oxunaqlı təsvir |

---

## 7.5 `Nəticə` tipi (xətasız yanaşma)

İstisna atmaq əvəzinə nəticəni dəyər kimi qaytarmaq:

```alqor
gətir nəticə

funksiya böl(a: tam, b: tam) -> Nəticə[onluq, mətn]
    əgər b == 0 onda
        qaytar Xəta("Sıfıra bölmə")
    son
    qaytar Uğur(a / b)
son

// İstifadə 1 — seç
seç böl(10, 2)
    hal Uğur(d) → yaz("Nəticə: {d}")
    hal Xəta(m) → yaz("Xəta: {m}")
son

// İstifadə 2 — metodlar
dəyişən n = böl(10, 0)
yaz(n.uğurludur())              // yanlış
yaz(n.dəyərVəYa(0.0))           // 0.0
yaz(n.çevir((x) => x * 2))      // Xəta saxlanılır

// İstifadə 3 — `?` yayma operatoru
funksiya hesabla() -> Nəticə[onluq, mətn]
    dəyişən a = böl(10, 2)?      // Xəta olsa dərhal qaytarır
    dəyişən b = böl(a, 5)?
    qaytar Uğur(a + b)
son

// İstisnaya çevirmək
dəyişən d = böl(10, 0).aç()     // Xəta olsa `at` edir
```

---

## 7.6 `İxtiyari` tipi

```alqor
funksiya tap(id: tam) -> İstifadəçi?
    ...
son

dəyişən i = tap(5)
əgər i boş deyil onda
    yaz(i.ad)
son

// Zəncir
yaz(tap(5)?.ünvan?.şəhər ?? "naməlum")
```

---

## 7.7 `gecikdir` və resurs idarəetməsi

```alqor
funksiya emal()
    dəyişən f = fayl.aç("a.txt")
    gecikdir f.bağla()                // mütləq icra olunur

    dəyişən b = verilənlər.bağlan()
    gecikdir b.bağla()                // tərs sırada: əvvəl b, sonra f

    cəhd et
        işlə(f, b)
    tut (x: Xəta)
        jurnal.xəta(x)
    son
son
```

### `istifadə` bloku
```alqor
istifadə f = fayl.aç("a.txt")
    yaz(f.oxu())
son                                   // f.bağla() avtomatik

istifadə f = fayl.aç("a.txt"), b = verilənlər.bağlan()
    ...
son
```

`istifadə` blokunda işlənən tip `Bağlanıla_bilən` interfeysini tətbiq etməlidir:
```alqor
interfeys Bağlanıla_bilən
    metod bağla()
son
```

---

## 7.8 Panika və bərpa

```alqor
// Bərpa olunmayan vəziyyət
panika("Bu heç vaxt baş verməməlidir")

// Üst səviyyədə panikanı tutmaq (yalnız server/xidmət üçün)
bərpa
    riskliModul.işlət()
tut (p: Panika)
    jurnal.kritik("Panika: {p.mesaj}")
    yenidənBaşlat()
son
```

---

## 7.9 Xəta jurnalı

```alqor
gətir jurnal

jurnal.səviyyə("sazlama")          // sazlama | info | xəbərdarlıq | xəta | kritik

jurnal.sazlama("Dəyişən x = {x}")
jurnal.info("Server başladı")
jurnal.xəbərdarlıq("Yaddaş 80% dolub")
jurnal.xəta("Sorğu alınmadı", xəta: x)
jurnal.kritik("Verilənlər bazası əlçatmazdır")

// Fayla yazmaq
jurnal.fayl("/var/log/proqram.log")
jurnal.format("json")             // mətn | json | rəngli
```

---

## 7.10 Tutulmamış xəta

Xəta heç yerdə tutulmasa, proqram dayanır və hesabat verilir:

```
✖ Tutulmamış xəta: FaylTapılmadıXətası
  Mesaj: "verilən.txt" faylı tapılmadı
  Yol:   /home/vuqar/layihe/verilən.txt

  Çağırış yığını:
    1. fayl.oxu(yol: mətn)              fayl.alq:142:9
    2. konfiqYüklə()                     konfiq.alq:18:21
    3. başlat()                          əsas.alq:7:5
    4. əsas()                            əsas.alq:3:1

  Səbəb: GirişÇıxışXətası — ENOENT (2)

  = kömək: faylın mövcudluğunu `fayl.vardır(yol)` ilə yoxlayın
  = sənəd: vuqar.pro/alqor/xeta/FaylTapılmadıXətası
```

Çıxış kodu: `1` (və ya xətanın `kod` dəyəri).

---

## 7.11 Xəta idarəetməsi üslubu

| Vəziyyət | Tövsiyə |
|---|---|
| Gözlənilən uğursuzluq (fayl yoxdur, giriş pisdir) | `Nəticə[T, X]` və ya `T?` |
| Proqramçı səhvi (yanlış arqument) | `at ArqumentXətası(...)` |
| Xarici sistem xətası (şəbəkə, disk) | `at` + çağıran tutur |
| Bərpa olunmayan vəziyyət | `panika(...)` |
| Daxili invariant | `iddia` |
| İstifadəçi girişinin yoxlanması | `təmin` |

---

## 7.12 İcra zamanı xəta kodları

| Kod | Xəta |
|---|---|
| `ALQ-R001` | Sıfıra bölmə |
| `ALQ-R002` | İndeks diapazondan kənar |
| `ALQ-R003` | Lüğətdə açar yoxdur |
| `ALQ-R004` | Boş dəyərə müraciət |
| `ALQ-R005` | Tip çevrilməsi alınmadı |
| `ALQ-R006` | Tam ədəd daşması |
| `ALQ-R007` | İddia pozuldu |
| `ALQ-R008` | Yaddaş bitdi |
| `ALQ-R009` | Fayl tapılmadı |
| `ALQ-R010` | Stek daşması |
| `ALQ-R011` | Vaxt bitdi |
| `ALQ-R012` | İcazə yoxdur |
| `ALQ-R013` | Şəbəkə əlçatmazdır |
| `ALQ-R014` | Boş kolleksiyada əməliyyat |
| `ALQ-R015` | Dövri istinad aşkarlandı |
| `ALQ-R016` | Bağlanmış resursdan istifadə |
| `ALQ-R017` | Paralel giriş münaqişəsi |
