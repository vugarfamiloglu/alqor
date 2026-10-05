# Alqor — Bölmə 3: Dəyişənlər, Operatorlar və İfadələr

---

## 3.1 Dəyişən elanı

### Sintaksis
```
dəyişən <ad> [: <tip>] [= <ifadə>]
sabit    <ad> [: <tip>] = <ifadə>
dəyişməz <ad> [: <tip>] = <ifadə>
```

### Nümunələr
```alqor
dəyişən ad = "Aysel"                  // tip çıxarılır: mətn
dəyişən yaş: tam = 24                 // açıq tip
dəyişən boşdur: mətn?                 // boş ilə ilkinləşir
dəyişən a, b, c = 1, 2, 3             // çoxlu elan
dəyişən x = 0, y = 0                  // ayrı-ayrı dəyərlər

sabit Pİ = 3.14159                    // sabit
sabit MAKS_İSTİFADƏÇİ: tam = 1000
dəyişməz SABİT_SİYAHI = [1, 2, 3]     // məzmunu da dəyişməz
```

### Dağıtma (destructuring)
```alqor
// Kortejdən
dəyişən x, y = (3, 4)

// Siyahıdan
dəyişən birinci, ikinci, ...qalan = [1, 2, 3, 4, 5]
// birinci = 1, ikinci = 2, qalan = [3, 4, 5]

// Lüğətdən
dəyişən {ad, yaş} = {"ad": "Aysel", "yaş": 24}

// Obyektdən
dəyişən {ad: istifadəçiAdı, email} = istifadəçi

// Atma
dəyişən _, ikinci = (1, 2)

// Dəyişdirmə
a, b = b, a
```

---

## 3.2 Əhatə dairəsi (scope)

```alqor
dəyişən qlobal = 1                    // modul səviyyəsi

funksiya nümunə()
    dəyişən lokal = 2                 // funksiya səviyyəsi

    əgər doğru onda
        dəyişən blokDaxili = 3        // blok səviyyəsi
        yaz(qlobal, lokal, blokDaxili)   // ✓ hamısı görünür
    son

    yaz(blokDaxili)                   // ✖ ALQ-T022
son
```

### Qaydalar
1. **Leksik əhatə** — daxili blok xarici bloku görür, əksi yox.
2. **Kölgələmə (shadowing)** icazəlidir, amma `alqorlint` xəbərdarlıq verir:
   ```alqor
   dəyişən x = 1
   əgər doğru onda
       dəyişən x = 2      // ⚠ ALQ-T026 xarici `x`-i kölgələyir
   son
   ```
3. **İstifadədən əvvəl elan** məcburidir (hoisting yoxdur) — funksiyalar istisna.
4. `global` açar sözü ilə qlobal dəyişənə yazmaq olar:
   ```alqor
   dəyişən sayğac = 0
   funksiya artır()
       global sayğac
       sayğac += 1
   son
   ```

---

## 3.3 Operatorlar — tam cədvəl

### 3.3.1 Hesab operatorları

| Operator | Əməliyyat | Nümunə | Nəticə |
|---|---|---|---|
| `+` | toplama | `5 + 3` | `8` |
| `-` | çıxma | `5 - 3` | `2` |
| `*` | vurma | `5 * 3` | `15` |
| `/` | bölmə (həmişə `onluq`) | `7 / 2` | `3.5` |
| `~/` | tam bölmə | `7 ~/ 2` | `3` |
| `%` | qalıq | `7 % 3` | `1` |
| `**` | qüvvət | `2 ** 10` | `1024` |
| `-` (tək) | əks işarə | `-5` | `-5` |
| `+` (tək) | müsbət işarə | `+5` | `5` |

**Qeydlər:**
- `/` ilə `0`-a bölmə → `BölməXətası`. `onluq` üçün `sonsuz` qaytarır.
- `%` nəticəsinin işarəsi **bölünənin** işarəsidir: `-7 % 3` → `-1`.
- Riyazi qalıq üçün `riyaziyyat.modul(-7, 3)` → `2`.
- `**` sağa assosiativdir: `2 ** 3 ** 2` = `2 ** 9` = `512`.

### 3.3.2 Mətn operatorları

| Operator | Əməliyyat | Nümunə | Nəticə |
|---|---|---|---|
| `+` | birləşdirmə | `"Sa" + "lam"` | `"Salam"` |
| `*` | təkrar | `"ab" * 3` | `"ababab"` |
| `[i]` | simvol | `"salam"[0]` | `` `s` `` |
| `[a..b]` | dilim | `"salam"[1..3]` | `"ala"` |

```alqor
yaz("Salam" + ", " + "dünya")     // Salam, dünya
yaz("-" * 20)                     // --------------------
```

> `+` operatoru **avtomatik tip çevirmir**. `"yaş: " + 24` → ✖ `ALQ-T008`.
> Düzgün: `"yaş: {24}"` və ya `"yaş: " + mətnƏt(24)`.

### 3.3.3 Müqayisə operatorları

| Operator | Əməliyyat |
|---|---|
| `==` | bərabərdir |
| `!=` | bərabər deyil |
| `<` | kiçikdir |
| `>` | böyükdür |
| `<=` | kiçik və ya bərabərdir |
| `>=` | böyük və ya bərabərdir |
| `<=>` | üçtərəfli müqayisə → `-1`, `0`, `1` |

```alqor
yaz(5 == 5)             // doğru
yaz("a" < "b")          // doğru  (Azərbaycan əlifba sırası ilə)
yaz("ə" < "f")          // doğru  (ə hərfi e-dən sonra, f-dən əvvəl)
yaz([1,2] == [1,2])     // doğru  (məzmuna görə)
yaz(5 <=> 3)            // 1
```

**Bərabərlik semantikası:**

| Tip | `==` davranışı |
|---|---|
| `tam`, `onluq`, `məntiq`, `simvol` | dəyərə görə |
| `mətn` | məzmuna görə (NFC normalizasiya edilmiş) |
| `siyahı`, `lüğət`, `dəst`, `kortej` | element-element, dərin |
| `sinif` | `bərabərdir()` metodu varsa onu, yoxsa identikliyi |
| `boş` | `boş == boş` → `doğru` |
| `ƏdədDeyil` | `ƏdədDeyil == ƏdədDeyil` → `yanlış` (IEEE754) |

İdentiklik üçün: `eynidir(a, b)`.

### 3.3.4 Məntiqi operatorlar

| Azərbaycanca | Simvol | Əməliyyat |
|---|---|---|
| `və` | `&&` | VƏ (qısa qapanma) |
| `və ya` | `\|\|` | VƏ YA (qısa qapanma) |
| `deyil` | `!` | İNKAR |

```alqor
əgər yaş >= 18 və vətəndaşdır onda ... son
əgər admin və ya moderator onda ... son
əgər deyil aktivdir onda ... son
əgər !(a və b) onda ... son
```

**Qısa qapanma:** `yanlış və f()` → `f()` çağırılmır. `doğru və ya f()` → `f()` çağırılmır.

### 3.3.5 Bit operatorları

| Operator | Əməliyyat | Nümunə | Nəticə |
|---|---|---|---|
| `&` | bit VƏ | `0b1100 & 0b1010` | `0b1000` |
| `\|` | bit VƏ YA | `0b1100 \| 0b1010` | `0b1110` |
| `^` | bit XOR | `0b1100 ^ 0b1010` | `0b0110` |
| `~` | bit İNKAR | `~0b1100` | `...11110011` |
| `<<` | sola sürüşmə | `1 << 4` | `16` |
| `>>` | sağa sürüşmə (işarəli) | `-16 >> 2` | `-4` |
| `>>>` | sağa sürüşmə (işarəsiz) | `-16 >>> 28` | `15` |

### 3.3.6 Mənimsətmə operatorları

| Operator | Ekvivalent |
|---|---|
| `=` | mənimsətmə |
| `+=` | `a = a + b` |
| `-=` | `a = a - b` |
| `*=` | `a = a * b` |
| `/=` | `a = a / b` |
| `~/=` | `a = a ~/ b` |
| `%=` | `a = a % b` |
| `**=` | `a = a ** b` |
| `&=` `\|=` `^=` `<<=` `>>=` | bit əməliyyatları |
| `??=` / `?=` | `a = a ?? b` (yalnız boşdursa) |

```alqor
dəyişən i = 0
i += 1                 // 1
i++                    // 2   (yalnız ifadə kimi, dəyər qaytarmır)
i--                    // 1
```

> `++` və `--` **yalnız müstəqil ifadə** kimi işlənir. `b = i++` → ✖ `ALQ-P015`.

### 3.3.7 Xüsusi operatorlar

```alqor
// Boş-birləşdirmə
dəyişən ad = gələnAd ?? "Qonaq"

// Təhlükəsiz çağırış
dəyişən şəhər = istifadəçi?.ünvan?.şəhər

// Məcburi açma
dəyişən mütləq = istifadəçi!.ad

// Üzvlük
əgər 3 içindədir [1,2,3] onda ... son
əgər "a" içindədir "salam" onda ... son
əgər "x" içində deyil lüğət onda ... son

// Tip yoxlaması
əgər x tipidir mətn onda ... son
əgər x tipidir deyil tam onda ... son

// Tip çevrilməsi
dəyişən n = "42" kimi tam
dəyişən m = "abc" kimi? tam     // təhlükəsiz → boş

// Diapazon
hər i üçün 1..10 içində ... son

// Yayma
dəyişən hamısı = [...birinci, ...ikinci]
dəyişən birləşik = {...varsayılan, ...xüsusi}
çağır(...arqumentlər)

// Boru
dəyişən nəticə = verilənlər
    |> təmizlə
    |> çevir
    |> sırala
// ekvivalent: sırala(çevir(təmizlə(verilənlər)))
```

---

## 3.4 Operator prioriteti

Yuxarıdan aşağı — **yüksəkdən alçağa**:

| # | Operatorlar | Assosiativlik |
|---|---|---|
| 1 | `()` `[]` `.` `?.` `!` (postfiks) — çağırış, indeks, üzv | soldan |
| 2 | `yeni` | sağdan |
| 3 | `**` | **sağdan** |
| 4 | `-` `+` `deyil` `!` `~` (tək operandlı) | sağdan |
| 5 | `kimi` `kimi?` | soldan |
| 6 | `*` `/` `~/` `%` | soldan |
| 7 | `+` `-` | soldan |
| 8 | `<<` `>>` `>>>` | soldan |
| 9 | `&` | soldan |
| 10 | `^` | soldan |
| 11 | `\|` | soldan |
| 12 | `..` `..<` | yoxdur |
| 13 | `<` `>` `<=` `>=` `<=>` `içindədir` `tipidir` | soldan |
| 14 | `==` `!=` | soldan |
| 15 | `və` `&&` | soldan |
| 16 | `və ya` `\|\|` | soldan |
| 17 | `??` | sağdan |
| 18 | `\|>` | soldan |
| 19 | `= += -= *= /= ~/= %= **= ??=` | **sağdan** |

### Nümunələr
```alqor
2 + 3 * 4            // 14   (* əvvəl)
(2 + 3) * 4          // 20
2 ** 3 ** 2          // 512  (sağdan: 2 ** 9)
-2 ** 2              // -4   (** əvvəl, sonra işarə)
a və b və ya c       // (a və b) və ya c
deyil a == b         // deyil (a == b)   — diqqət!
a ?? b ?? c          // a ?? (b ?? c)
```

> **Tövsiyə:** `alqorlint` qarışıq prioritetlərdə mötərizə tələb edir.

---

## 3.5 İfadələr

Alqor-da **demək olar ki, hər şey ifadədir** — dəyər qaytarır.

### Şərt ifadəsi
```alqor
dəyişən status = əgər yaş >= 18 onda "yetkin" yoxsa "uşaq" son

dəyişən qiymət = əgər bal >= 90 onda
    "Əla"
yoxsa əgər bal >= 70 onda
    "Yaxşı"
yoxsa
    "Kafi"
son
```

### Seçim ifadəsi
```alqor
dəyişən ad = seç gün
    hal 1 → "Bazar ertəsi"
    hal 2 → "Çərşənbə axşamı"
    hal 6, 7 → "Həftəsonu"
    digər hallarda → "Naməlum"
son
```

### Blok ifadəsi
```alqor
dəyişən nəticə = blok
    dəyişən a = ağırHesablama()
    dəyişən b = digərHesablama()
    ver a + b                 // `ver` bloku dəyərlə bitirir
son
```

### Cəhd ifadəsi
```alqor
dəyişən dəyər = cəhd et
    ver tamƏt(giriş)
tut (x: ÇevrilməXətası)
    ver 0
son
```

---

## 3.6 Sabit qatlanması (constant folding)

Kompilyasiya vaxtı hesablanan ifadələr:

```alqor
sabit SANİYƏ_GÜNDƏ = 60 * 60 * 24        // kompilyasiya vaxtı → 86400
sabit MESAJ = "Versiya " + "1.0"          // → "Versiya 1.0"

// Kompilyasiya vaxtı şərt
@əgərKompilyasiya(hədəf == "veb")
funksiya yüklə()
    ...
son
```

---

## 3.7 İfadə xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-P001` | Gözlənilməyən token |
| `ALQ-P002` | `son` gözlənilirdi |
| `ALQ-P003` | Bağlanmamış mötərizə |
| `ALQ-P004` | `onda` gözlənilirdi |
| `ALQ-P005` | İfadə gözlənilirdi |
| `ALQ-P006` | `yoxsa` `əgər`-siz işlənib |
| `ALQ-P007` | `hal` `seç`-dən kənarda |
| `ALQ-P008` | `dayan` dövrədən kənarda |
| `ALQ-P009` | `davam et` dövrədən kənarda |
| `ALQ-P010` | `qaytar` funksiyadan kənarda |
| `ALQ-P011` | `özü` metoddan kənarda |
| `ALQ-P012` | `üst` miras olmayan sinifdə |
| `ALQ-P013` | `gözlə` asinxron olmayan funksiyada |
| `ALQ-P014` | Çox sözlü açar söz yarımçıqdır |
| `ALQ-P015` | `++`/`--` ifadə daxilində istifadə edilə bilməz |
| `ALQ-P016` | Mötərizə tələb olunur (qarışıq prioritet) |
