# Alqor — Bölmə 1: Leksik Quruluş

> Alqor Dil Spesifikasiyası, versiya 1.0 (layihə)
> Bu bölmə mənbə faylın hərflərdən tokenlərə necə çevrildiyini təyin edir.

---

## 1.1 Mənbə faylı

| Xüsusiyyət | Qayda |
|---|---|
| Kodlaşdırma | **Yalnız UTF-8**. Başqa kodlaşdırma `ALQ-L001` xətası verir. |
| BOM | İcazəlidir, oxunarkən atılır. |
| Normalizasiya | Fayl oxunan kimi **NFC** formasına salınır. |
| Sətir sonu | `LF` (`\n`) və ya `CRLF` (`\r\n`) — ikisi də qəbul olunur, daxildə `LF`-ə çevrilir. |
| Fayl uzantısı | `.alq` (köhnə `.alqor` da tanınır) |
| Giriş nöqtəsi | `əsas.alq` faylındakı `funksiya əsas()` funksiyası |
| Maksimum sətir uzunluğu | Məhdudiyyət yoxdur, `alqorfmt` 100 simvolda bölür |

### Shebang
Faylın **ilk** sətri `#!` ilə başlayırsa, bütün sətir şərh kimi atılır:

```
#!/usr/bin/env alqor
yaz("Salam")
```

---

## 1.2 Əlifba

Alqor mənbə kodunda icazəli simvollar:

### Kiçik hərflər (32 ədəd)
```
a b c ç d e ə f g ğ h x ı i j k q l m n o ö p r s ş t u ü v y z
```

### Böyük hərflər (32 ədəd)
```
A B C Ç D E Ə F G Ğ H X I İ J K Q L M N O Ö P R S Ş T U Ü V Y Z
```

### Azərbaycan əlifbasının rəsmi sırası
Bu sıra `siyahı.sırala()` və `mətn.müqayisə()` əməliyyatlarında istifadə olunur
(Unicode-un öz sırası **yanlışdır**, ona görə dilin daxilində `az-AZ` collation cədvəli var):

```
A a  B b  C c  Ç ç  D d  E e  Ə ə  F f  G g  Ğ ğ  H h  X x
I ı  İ i  J j  K k  Q q  L l  M m  N n  O o  Ö ö  P p  R r
S s  Ş ş  T t  U u  Ü ü  V v  Y y  Z z
```

### Unicode kod nöqtələri (texniki arayış)

| Hərf | Kod | Hərf | Kod |
|---|---|---|---|
| ə | `U+0259` | Ə | `U+018F` |
| ı | `U+0131` | I | `U+0049` |
| i | `U+0069` | İ | `U+0130` |
| ö | `U+00F6` | Ö | `U+00D6` |
| ü | `U+00FC` | Ü | `U+00DC` |
| ç | `U+00E7` | Ç | `U+00C7` |
| ş | `U+015F` | Ş | `U+015E` |
| ğ | `U+011F` | Ğ | `U+011E` |

---

## 1.3 Böyük/kiçik hərf çevrilməsi (kritik)

Alqor **standart Unicode çevrilməsindən istifadə etmir**. Azərbaycan dilinin `i`/`ı` qaydası fərqlidir:

| Əməliyyat | Standart Unicode | **Alqor (`az-AZ`)** |
|---|---|---|
| `"i".böyüyə()` | `"I"` ❌ | `"İ"` ✅ |
| `"ı".böyüyə()` | `"I"` ✅ | `"I"` ✅ |
| `"I".kiçiyə()` | `"i"` ❌ | `"ı"` ✅ |
| `"İ".kiçiyə()` | `"i̇"` ❌ | `"i"` ✅ |
| `"IŞIQ".kiçiyə()` | `"ışıq"` | `"ışıq"` ✅ |
| `"ışıq".böyüyə()` | `"IŞIQ"` ✅ | `"IŞIQ"` ✅ |

> **Qayda:** Açar sözlər **həmişə kiçik hərflə** yazılır və **hərfə həssasdır**.
> Bu, yuxarıdakı çevrilmə mürəkkəbliyinin kompilyatorun nüvəsinə sızmasının qarşısını alır.

---

## 1.4 Homoqlif qoruması

Aşağıdakı simvollar Azərbaycan hərflərinə oxşayır, amma fərqlidir. Lekser onları aşkarlayıb **avtomatik düzəldir** və xəbərdarlıq verir:

| Yanlış simvol | Kod | Düzgün | Kod |
|---|---|---|---|
| `ä` (a-umlaut) | `U+00E4` | `ə` | `U+0259` |
| `ǝ` (turned e) | `U+01DD` | `ə` | `U+0259` |
| `е` (kiril e) | `U+0435` | `e` | `U+0065` |
| `о` (kiril o) | `U+043E` | `o` | `U+006F` |
| `с` (kiril s) | `U+0441` | `c` | `U+0063` |
| `ѕ` (kiril dze) | `U+0455` | `s` | `U+0073` |
| `ş` parçalanmış | `s`+`U+0327` | `ş` | `U+015F` |
| `ğ` parçalanmış | `g`+`U+0306` | `ğ` | `U+011F` |
| `ı` nöqtəsiz-i var. | `U+0131` | — | düzdür |

Nümunə xəbərdarlıq:
```
⚠ ALQ-L014  əsas.alq:7:11
   "yaş" sözündə gizli simvol aşkarlandı: 'ä' (U+00E4)
   Avtomatik düzəliş: 'ä' → 'ə' (U+0259)
   Bu xəbərdarlığı söndürmək üçün: // alqor: homoqlif-yoxlama söndür
```

---

## 1.5 İdentifikatorlar

### Qaydalar
1. İlk simvol: **hərf** (yuxarıdakı 64 hərfdən biri) və ya `_`
2. Sonrakı simvollar: hərf, rəqəm (`0-9`) və ya `_`
3. Açar söz ola bilməz
4. Uzunluq məhdudiyyəti yoxdur
5. Hərfə həssasdır: `Say` ≠ `say` ≠ `SAY`

### Düzgün identifikatorlar
```
ad          yaş          _gizli        tələbə_adı
İstifadəçi  ümumiMəbləğ  sayğac2       Şəbəkə_Bağlantısı
ölçü        ƏnBöyükDəyər qiymət_USD    __daxili__
```

### Yanlış identifikatorlar
```
2ad         ← rəqəmlə başlayır
əgər        ← açar sözdür
ad-soyad    ← defis icazəli deyil
ümumi məbləğ ← boşluq icazəli deyil
qiymət$     ← $ icazəli deyil
```

### Adlandırma konvensiyası (məcburi deyil, `alqorlint` tövsiyə edir)

| Element | Üslub | Nümunə |
|---|---|---|
| Dəyişən, parametr | `kiçikDəvəQutusu` | `istifadəçiAdı`, `ümumiMəbləğ` |
| Funksiya, metod | `kiçikDəvəQutusu` | `məbləğHesabla()`, `faylOxu()` |
| Sabit | `BÖYÜK_ALT_XƏTT` | `MAKSİMUM_SAY`, `PİSAYI` |
| Sinif, interfeys, sadalama | `BöyükDəvəQutusu` | `İstifadəçi`, `ŞəbəkəXətası` |
| Modul, fayl adı | `kiçik-defis` | `verilənlər-bazası.alq` |
| Gizli üzv | `_` ilə başlayır | `_daxiliVəziyyət` |

---

## 1.6 Açar sözlər (qorunan sözlər)

Bu **91** söz identifikator kimi istifadə oluna bilməz.

### Elan
```
dəyişən    sabit      funksiya   sinif      struktur
interfeys  sadalama   modul      tip        qurucu
metod      xassə      statik     mücərrəd   açıq
gizli      qorunan    sabitdir   genişlət
```

### İdarəetmə
```
əgər       onda       yoxsa      əks        halda
son        seç        hal        digər      hallarda
nə         qədər      ki         hər        üçün
içində     təkrarla   dəfə       dayan      davam
et         keç
```

### Funksiya və axın
```
qaytar     gətir      ixrac      kimi
asinxron   gözlə      paralel    gecikdir   generator
ver
```

### Xəta idarəetməsi
```
cəhd       tut        nəhayət    at         təmin
```

### Obyekt
```
özü        üst        yeni       miras      tətbiq
əvəz       silinsin
```

### Məntiq və müqayisə
```
və         ya         deyil      tipidir    içindədir
boşdur     varsa
```

### Literal
```
doğru      yanlış     boş
```

### Tip adları
```
tam        onluq      mətn       məntiq     simvol
bayt       siyahı     lüğət      dəst       kortej
istənilən  heç        funksiyaTipi
```

### Modifikator və köməkçi
```
dəyişməz   yalnız     oxunan     global     lokal
sınaq      iddia      sil        ölç
```

### Çox sözlü açar söz birləşmələri

Bunlar **lekser səviyyəsində bir tokenə birləşdirilir** (maksimal udma).
Kanonik forma tək boşluqla saxlanılır. Birləşmə yalnız **eyni sətirdə**
baş verir — yeni sətir onu kəsir (bu, `yoxsa` + yeni sətir + `əgər`
konstruksiyasının `yoxsa əgər` kimi oxunmasının qarşısını alır).

| Birləşmə | Mənası | Kanonik nəticə |
|---|---|---|
| `yoxsa əgər` | else if | `yoxsa əgər` |
| `əks halda` | else (uzun forma) | `yoxsa` ← alias |
| `nə qədər ki` | while | `nə qədər ki` |
| `davam et` | continue | `davam et` |
| `cəhd et` | try | `cəhd et` |
| `digər hallarda` | default case | `digər hallarda` |
| `ixrac et` | export | `ixrac et` |
| `əvəz et` | override | `əvəz et` |
| `və ya` | logical or | `və ya` |
| `boş deyil` | is not null | `boş deyil` |

> **`içində deyil` və `tipidir deyil` YOXDUR.**
> `içində` for-each bağlayıcısıdır (`hər x üçün s içində`), ona görə
> `içində deyil` birləşməsi parser üçün ikimənalılıq yaradırdı.
> İnkar üçün mötərizə ilə `deyil` işlənir:
> ```alqor
> əgər deyil (x içindədir siyahı) onda ... son
> əgər deyil (x tipidir mətn) onda ... son
> ```
> `boşdur` / `boş deyil` cütü saxlanılır — onların toqquşması yoxdur.

---

## 1.7 ASCII əvəzləyiciləri

İstifadəçinin klaviaturasında Azərbaycan düzümü olmaya bilər. Kompilyator ASCII variantı **qəbul edir**, amma `ALQ-L020` xəbərdarlığı verir və `alqorfmt` bir əmrlə hamısını düzəldir.

| Kanonik | ASCII | Kanonik | ASCII |
|---|---|---|---|
| `əgər` | `eger` | `dəyişən` | `deyisen` |
| `əks halda` | `eks halda` | `nə qədər ki` | `ne qeder ki` |
| `hər` | `her` | `üçün` | `ucun` |
| `içində` | `icinde` | `təkrarla` | `tekrarla` |
| `və` | `ve` | `və ya` | `ve ya` |
| `cəhd et` | `cehd et` | `nəhayət` | `nehayet` |
| `özü` | `ozu` | `mətn` | `metn` |
| `məntiq` | `mentiq` | `siyahı` | `siyahi` |
| `lüğət` | `luget` | `dəst` | `dest` |
| `mücərrəd` | `mucerred` | `əvəz et` | `evez et` |
| `qədər` | `qeder` | `dəfə` | `defe` |
| `istənilən` | `istenilen` | `tətbiq` | `tetbiq` |
| `genişlət` | `genislet` | `dəyişməz` | `deyismez` |

### Çevrilmə qaydası
```
ə → e    ı → i    ö → o    ü → u    ç → c    ş → s    ğ → g    İ → I
```

> ⚠ Bu **yalnız açar sözlərə** aiddir. İdentifikatorlarda və mətn literallarında
> ASCII çevrilməsi aparılmır — `yaş` və `yas` **fərqli** dəyişənlərdir.

### Redaktor giriş metodu (Alqor Studio)

**1. Avtomatik söz çevrilməsi** — yazarkən tanınan ASCII açar söz dərhal kanonik formaya keçir:
```
istifadəçi yazır:  eger x > 5 onda
ekranda görünür:   əgər x > 5 onda
```

**2. Kompozisiya düyməsi** — `;` prefiksi:

| Yazırsan | Alırsan | Yazırsan | Alırsan |
|---|---|---|---|
| `;e` | `ə` | `;E` | `Ə` |
| `;i` | `ı` | `;I` | `İ` |
| `;o` | `ö` | `;O` | `Ö` |
| `;u` | `ü` | `;U` | `Ü` |
| `;c` | `ç` | `;C` | `Ç` |
| `;s` | `ş` | `;S` | `Ş` |
| `;g` | `ğ` | `;G` | `Ğ` |
| `;;` | `;` | | |

**3. Hərf paneli** — redaktorun altında klikləməli düymələr: `ə ı ğ ş ç ö ü İ`

---

## 1.8 Şərhlər

```alqor
// Tək sətirlik şərh

/* Çox sətirli
   şərh */

/* Şərhlər /* iç-içə */ ola bilər */

/// Sənəd şərhi — `alqordoc` bunu oxuyur
/// Növbəti elan üçün sənədləşmədir.

//! Modul səviyyəsində sənəd şərhi (faylın əvvəlində)
```

### Kompilyator direktivləri
Şərh `alqor:` ilə başlayırsa, kompilyatora göstəriş sayılır:

```alqor
// alqor: homoqlif-yoxlama söndür
// alqor: ascii-xəbərdarlıq söndür
// alqor: istifadəsiz-dəyişən icazə ver
// alqor: hədəf veb
// alqor: versiya 1.0
```

---

## 1.9 Literallar

### 1.9.1 Tam ədəd (`tam`)

```alqor
0
42
-17
1_000_000          // alt xətt ayırıcı (oxunaqlılıq üçün)
0x1F               // onaltılıq → 31
0X1f               // eyni
0b1010             // ikilik → 10
0o755              // səkkizlik → 493
```

| Xüsusiyyət | Dəyər |
|---|---|
| Ölçü | 64 bit işarəli |
| Diapazon | `-9_223_372_036_854_775_808` ... `9_223_372_036_854_775_807` |
| Daşma | İcra zamanı `DaşmaXətası` (buraxılış rejimində dövrə vurur — `--daşma-yoxla` ilə idarə olunur) |
| Böyük ədədlər | `böyükTam` tipi (`riyaziyyat` modulunda, hüdudsuz) |

### 1.9.2 Onluq ədəd (`onluq`)

```alqor
3.14
0.5
.5                 // XƏTA — nöqtədən əvvəl rəqəm olmalıdır
5.                 // XƏTA (ALQ-L006) — nöqtədən sonra rəqəm olmalıdır
5.mətnƏt()         // düzgün — tam ədədin metodu (nöqtədən sonra ad)
t.1.0              // düzgün — iç-içə kortej indeksi (onluq ədəd deyil)
5.0                // düzgün
1.5e3              // 1500.0
2.5E-4             // 0.00025
1_234.567_8        // ayırıcı ilə
sonsuz             // +∞
-sonsuz            // -∞
ƏdədDeyil          // NaN
```

| Xüsusiyyət | Dəyər |
|---|---|
| Format | IEEE 754 ikiqat dəqiqlik (64 bit) |
| Onluq ayırıcı | **Həmişə nöqtə (`.`)**, vergül deyil |
| Göstərmə | `yaz()` yerli formatda göstərə bilər: `vaxt.formatla()` |

> **Qeyd:** Azərbaycan dilində onluq ayırıcı vergüldür (`3,14`), amma kodda **nöqtə**dir,
> çünki vergül arqument ayırıcısıdır. `yaz(3,14)` → iki arqument, `yaz(3.14)` → bir ədəd.
> Göstərmə zamanı yerli format `mətn.yerliƏdəd(3.14)` → `"3,14"` ilə alınır.

### 1.9.3 Mətn (`mətn`)

#### Sadə mətn
```alqor
"Salam, dünya!"
'Tək dırnaq da olar'
""                 // boş mətn
```

#### Qaçış ardıcıllıqları

| Ardıcıllıq | Mənası |
|---|---|
| `\n` | yeni sətir |
| `\r` | karetka qayıtması |
| `\t` | tabulyasiya |
| `\\` | tərs kəsik |
| `\"` | ikiqat dırnaq |
| `\'` | tək dırnaq |
| `\0` | sıfır simvolu |
| `\e` | escape (`U+001B`) |
| `\u{259}` | Unicode kod nöqtəsi → `ə` |
| `\x41` | onaltılıq bayt → `A` |
| `\{` | sol fiqurlu mötərizə (interpolyasiyadan qaçmaq) |

#### Şablon mətn (interpolyasiya)
```alqor
dəyişən ad = "Aysel"
dəyişən yaş = 24

yaz("Salam, {ad}! Sən {yaş} yaşındasan.")
// Salam, Aysel! Sən 24 yaşındasan.

yaz("Gələn il {yaş + 1} olacaqsan.")      // ifadə də olar
yaz("Qiymət: {qiymət:.2}")                 // format spesifikatoru
yaz("Fiqurlu mötərizə: \{ belə \}")        // qaçış
```

**Format spesifikatorları:**

| Spesifikator | Nəticə |
|---|---|
| `{x:.2}` | 2 onluq rəqəm → `3.14` |
| `{x:5}` | 5 simvol enində, sağa düzülmüş |
| `{x:<5}` | 5 simvol enində, sola düzülmüş |
| `{x:^5}` | mərkəzə düzülmüş |
| `{x:05}` | sıfırla doldurulmuş → `00042` |
| `{x:x}` | onaltılıq |
| `{x:b}` | ikilik |
| `{x:,}` | minlik ayırıcı → `1,000,000` |
| `{x:,az}` | Azərbaycan formatı → `1 000 000` |

#### Çox sətirli mətn
```alqor
dəyişən şeir = """
Mən bir dilin
yaradıcısıyam.
"""
```
Açan `"""`-dan sonrakı ilk yeni sətir atılır. Bağlayan `"""`-un girintisi bütün
sətirlərdən çıxılır.

#### Xam mətn (qaçışsız)
```alqor
dəyişən yol = x"C:\yeni\test\fayl.txt"     // \n, \t qaçış sayılmır
dəyişən naxış = x"\d+\.\d+"                // requlyar ifadə üçün ideal
```

#### Bayt mətn
```alqor
dəyişən verilən = b"ABC"                    // [65, 66, 67] baytları
```

### 1.9.4 Simvol (`simvol`)
```alqor
dəyişən hərf: simvol = `ə`
dəyişən yeniSətir: simvol = `\n`
```
Bir **Unicode qrafem klasteri** saxlayır (kod nöqtəsi deyil — emoji və birləşmiş
hərflər düzgün işləyir).

### 1.9.5 Məntiqi (`məntiq`)
```alqor
doğru
yanlış
```
Bunlar **yeganə** məntiqi dəyərlərdir. `0`, `""`, `boş` avtomatik `yanlış`-a
çevrilmir — şərt yerində məntiqi tip tələb olunur (`ALQ-T007`).

### 1.9.6 Boş (`boş`)
```alqor
boş
```
Dəyərin olmaması. Yalnız **ixtiyari** (`?`) tiplərə mənimsədilə bilər.

### 1.9.7 Siyahı
```alqor
[]                              // boş
[1, 2, 3]
["a", "b", "c"]
[1, 2, 3,]                      // sonda vergül icazəlidir
[
    "çoxsətirli",
    "siyahı",
]
[[1, 2], [3, 4]]                // iç-içə
```

### 1.9.8 Lüğət
```alqor
{}                              // boş lüğət — qeyd: boş dəst üçün dəst() işlədin
{"ad": "Aysel", "yaş": 24}
{1: "bir", 2: "iki"}
{
    "şəhər": "Bakı",
    "ölkə": "Azərbaycan",
}
```

### 1.9.9 Dəst
```alqor
dəst()                          // boş dəst
dəst(1, 2, 3)
{1, 2, 3}                       // qısa forma (açar-dəyər cütü olmayanda dəst)
```

### 1.9.10 Kortej
```alqor
(1, "iki", doğru)
()                              // boş kortej
(5,)                            // tək elementli kortej (vergül vacibdir)
```

### 1.9.11 Diapazon
```alqor
1..5         // 1, 2, 3, 4, 5      (daxil olmaqla)
1..<5        // 1, 2, 3, 4         (son daxil deyil)
0..<uzunluq(siyahı)
10..1        // tərs: 10, 9, ..., 1
1..10 addım 2 // 1, 3, 5, 7, 9
`a`..`e`     // simvol diapazonu
```

---

## 1.10 Operatorlar və durğu işarələri

### Tam token siyahısı
```
+   -   *   /   ~/  %   **
=   +=  -=  *=  /=  ~/= %=  **=
==  !=  <   >   <=  >=  <=>
&&  ||  !              (və / və ya / deyil simvol variantları)
&   |   ^   ~   <<  >>
?   ??  ?.  ?=  ?:
.   ..  ..< ...  ->  =>  |>
(   )   [   ]   {   }
,   ;   :   @   #   _
++  --
```

| Operator | Ad | Nümunə |
|---|---|---|
| `~/` | tam bölmə | `7 ~/ 2` → `3` |
| `**` | qüvvət | `2 ** 10` → `1024` |
| `<=>` | üçtərəfli müqayisə | `a <=> b` → `-1`, `0`, `1` |
| `??` | boş-birləşdirmə | `ad ?? "naməlum"` |
| `?.` | təhlükəsiz çağırış | `istifadəçi?.ad` |
| `?=` | boşdursa mənimsət | `ad ?= "standart"` |
| `..` | diapazon (daxil) | `1..5` |
| `..<` | diapazon (xaric) | `1..<5` |
| `...` | yayma / variadic | `funksiya cəm(...ədədlər)` |
| `->` | qaytarma tipi | `funksiya f() -> tam` |
| `=>` | ox funksiyası | `(x) => x * 2` |
| `\|>` | boru | `5 \|> ikiqat \|> yaz` |
| `@` | annotasiya | `@sınaq`, `@köhnəlmiş` |
| `_` | atılan dəyər | `dəyişən _, b = cüt` |

---

## 1.11 Ayırıcılar və ifadə sonu

- İfadə **yeni sətirdə** bitir. Nöqtəli vergül **lazım deyil**.
- Bir sətirdə bir neçə ifadə üçün `;` istifadə olunur: `a = 1; b = 2`
- Açılmamış `(`, `[`, `{` daxilində yeni sətir ifadəni bitirmir:
  ```alqor
  dəyişən cəm = topla(
      1,
      2,
      3
  )
  ```
- Sətir sonunda `+`, `və`, `və ya`, `,`, `.` kimi operator varsa, ifadə davam edir:
  ```alqor
  dəyişən uzun = birinciDəyər +
                 ikinciDəyər +
                 üçüncüDəyər
  ```
- Növbəti sətir `.ad` və ya `?.ad` ilə başlayırsa da ifadə davam edir —
  axıcı (zəncirlənən) API-lər üçün. Aradakı boş və şərh sətirləri
  ötürülür; `..` (diapazon) və `...` (yayma) ilə başlayan sətir zəncir
  sayılmır:
  ```alqor
  dəyişən a = konsol.arqumentlər()
      .proqram("hesabla")
      // şərh zənciri qırmır
      .bayraq("--ətraflı", "-ə", "Ətraflı çıxış")
      .təhlil()
  ```

---

## 1.12 Girinti və blok

- Girinti **semantik deyil** — kod işləməsinə təsir etmir.
- Bloklar `son` açar sözü ilə bitir.
- `alqorfmt` standartı: **4 boşluq**, tabulyasiya yox.
- İxtiyari tipli bağlanış oxunaqlılıq üçün icazəlidir:

```alqor
əgər x > 5 onda
    yaz("böyük")
son əgər                         // "son" ilə eynidir, oxunaqlılıq üçün
```

Dəstəklənən tipli bağlanışlar: `son əgər`, `son funksiya`, `son sinif`, `son metod`,
`son seç`, `son təkrarla`, `son hər`, `son cəhd`, `son nə qədər ki`, `son modul`,
`son interfeys`, `son sadalama`, `son struktur`.

---

## 1.13 Leksik xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-L001` | Fayl UTF-8 deyil |
| `ALQ-L002` | Tanınmayan simvol |
| `ALQ-L003` | Bağlanmamış mətn literalı |
| `ALQ-L004` | Bağlanmamış şərh bloku |
| `ALQ-L005` | Yanlış qaçış ardıcıllığı |
| `ALQ-L006` | Yanlış ədəd literalı |
| `ALQ-L007` | Ədəd diapazondan kənardır |
| `ALQ-L008` | Yanlış Unicode kod nöqtəsi |
| `ALQ-L009` | İdentifikator rəqəmlə başlaya bilməz |
| `ALQ-L010` | Açar söz identifikator kimi istifadə edilə bilməz |
| `ALQ-L011` | Bağlanmamış interpolyasiya `{` |
| `ALQ-L012` | Tabulyasiya və boşluq qarışdırılıb |
| `ALQ-L013` | Yanlış format spesifikatoru |
| `ALQ-L014` | ⚠ Homoqlif simvol aşkarlandı (xəbərdarlıq) |
| `ALQ-L015` | ⚠ Sətir sonunda boşluq (xəbərdarlıq) |
| `ALQ-L020` | ⚠ ASCII açar söz istifadə olunub (xəbərdarlıq) |

### Xəta mesajı formatı
```
✖ ALQ-L003  Bağlanmamış mətn literalı
  ┌─ əsas.alq:12:15
  │
12│     yaz("Salam, dünya)
  │         ^^^^^^^^^^^^^^ bu mətn bağlanmayıb
  │
  = kömək: sonda `"` əlavə edin
  = sənəd: alqor.vuqar.pro/xeta/ALQ-L003
```
