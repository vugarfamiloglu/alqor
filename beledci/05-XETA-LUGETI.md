# Alqor Bələdçisi — 6. Xəta Lüğəti

> Hər xəta kodunun mənası, səbəbi və həlli. Terminalda da baxa bilərsiniz:
> `alqor kömək ALQ-T001`

---

## Xəta kodu quruluşu

```
ALQ - T - 001
 │    │    │
 │    │    └── sıra nömrəsi
 │    └─────── mərhələ
 └──────────── dil prefiksi
```

| Hərf | Mərhələ | Nə vaxt aşkarlanır |
|---|---|---|
| `L` | Leksik | Mənbə mətni tokenlərə bölünərkən |
| `P` | Parser | Qrammatika yoxlanarkən |
| `T` | Tip | Semantik analiz zamanı |
| `M` | Modul | İdxal/ixrac həll olunarkən |
| `R` | İcra | Proqram işləyərkən |
| `S` | Təhlükəsizlik | Kod yoxlayıcısı (`alqorlint`) |

| Simvol | Mənası |
|---|---|
| ✖ | Xəta — kompilyasiya dayanır |
| ⚠ | Xəbərdarlıq — kompilyasiya davam edir |

---

## L — Leksik xətalar

### ✖ ALQ-L001 — Fayl UTF-8 deyil
**Səbəb:** Mənbə faylı başqa kodlaşdırmadadır (məsələn Windows-1254).
**Həll:**
```bash
iconv -f WINDOWS-1254 -t UTF-8 fayl.alq -o fayl-yeni.alq
```
Redaktorunuzda standart kodlaşdırmanı UTF-8 edin.

### ✖ ALQ-L002 — Tanınmayan simvol
**Səbəb:** Koda icazəsiz simvol düşüb (`$`, `§`, görünməz Unicode).
**Həll:** Simvolu silin. Görünməz simvol şübhəsi varsa: `alqorfmt --homoqlif-düzəlt .`

### ✖ ALQ-L003 — Bağlanmamış mətn literalı
```alqor
yaz("Salam, dünya)           // ✖
yaz("Salam, dünya")          // ✓
```

### ✖ ALQ-L005 — Yanlış qaçış ardıcıllığı
```alqor
yaz("C:\yeni\test")          // ✖ \y və \t qaçış deyil
yaz("C:\\yeni\\test")        // ✓
yaz(x"C:\yeni\test")         // ✓ xam mətn
```

### ✖ ALQ-L006 — Yanlış ədəd literalı
```alqor
dəyişən a = .5               // ✖ nöqtədən əvvəl rəqəm olmalıdır
dəyişən b = 5.               // ✖ nöqtədən sonra rəqəm olmalıdır
dəyişən c = 0.5              // ✓
dəyişən d = 5.0              // ✓
```

### ✖ ALQ-L010 — Açar söz identifikator kimi istifadə edilib
```alqor
dəyişən son = 5              // ✖ `son` açar sözdür
dəyişən sonuncu = 5          // ✓
```

### ⚠ ALQ-L014 — Homoqlif simvol aşkarlandı
**Səbəb:** `ə` əvəzinə `ä`, `e` əvəzinə kiril `е` və s.
**Həll:** Avtomatik düzəldilir. Söndürmək: `// alqor: homoqlif-yoxlama söndür`

### ⚠ ALQ-L020 — ASCII açar söz istifadə olunub
**Səbəb:** `eger` yazmısınız, `əgər` olmalıdır.
**Həll:** Kod işləyir, amma kanonik formaya keçirmək üçün:
```bash
alqorfmt --ascii-düzəlt .
```

---

## P — Parser xətaları

### ✖ ALQ-P002 — `son` gözlənilirdi
```alqor
əgər x > 5 onda
    yaz("böyük")
                             // ✖ `son` yoxdur
```

### ✖ ALQ-P004 — `onda` gözlənilirdi
```alqor
əgər x > 5                   // ✖
    yaz("böyük")
son

əgər x > 5 onda              // ✓
    yaz("böyük")
son
```

### ✖ ALQ-P008 / P009 — `dayan` / `davam et` dövrədən kənarda
Bu açar sözlər yalnız `hər`, `nə qədər ki`, `təkrarla`, `həmişə` daxilində işləyir.

### ✖ ALQ-P010 — `qaytar` funksiyadan kənarda
Modul səviyyəsində `qaytar` yazmaq olmaz.

### ✖ ALQ-P011 — `özü` metoddan kənarda
`özü` yalnız sinif metodunda işləyir.

### ✖ ALQ-P013 — `gözlə` asinxron olmayan funksiyada
```alqor
funksiya f()
    dəyişən x = gözlə al()           // ✖
son

asinxron funksiya f()                 // ✓
    dəyişən x = gözlə al()
son
```

### ✖ ALQ-P015 — `++`/`--` ifadə daxilində
```alqor
dəyişən b = i++              // ✖
i++                          // ✓
dəyişən b = i                // ✓
i += 1
```

---

## T — Tip xətaları

### ✖ ALQ-T001 — Tip uyğunsuzluğu
```alqor
dəyişən a: tam = "salam"     // ✖ mətn → tam
dəyişən b: tam = tamƏt("5")  // ✓
```

### ✖ ALQ-T003 — Arqument sayı uyğun deyil
```alqor
funksiya f(a: tam, b: tam) ... son
f(1)                         // ✖ 2 arqument lazımdır
```

### ✖ ALQ-T007 — Şərt `məntiq` tipi olmalıdır
```alqor
əgər 1 onda ... son                      // ✖
əgər siyahı onda ... son                 // ✖
əgər ad onda ... son                     // ✖

əgər x != 0 onda ... son                 // ✓
əgər deyil boşdur(siyahı) onda ... son   // ✓
əgər ad boş deyil onda ... son           // ✓
```

### ✖ ALQ-T008 — Operator bu tiplərə tətbiq edilmir
```alqor
yaz("Yaş: " + 24)            // ✖ mətn + tam
yaz("Yaş: {24}")             // ✓
yaz("Yaş: " + mətnƏt(24))    // ✓
```

### ✖ ALQ-T012 — `boş` bu tipə mənimsədilə bilməz
```alqor
dəyişən a: mətn = boş        // ✖
dəyişən b: mətn? = boş       // ✓
```

### ✖ ALQ-T013 — İxtiyari dəyər yoxlanmadan istifadə olunub
```alqor
dəyişən ad: mətn? = tap()
yaz(ad.uzunluq())                        // ✖

əgər ad boş deyil onda                   // ✓
    yaz(ad.uzunluq())
son
yaz(ad?.uzunluq())                       // ✓
yaz((ad ?? "").uzunluq())                // ✓
```

### ✖ ALQ-T020 — Sabitə mənimsətmə
```alqor
sabit A = 5
A = 10                       // ✖
```

### ✖ ALQ-T022 — Təyin edilməmiş dəyişən
```alqor
yaz(x)                       // ✖ `x` elan edilməyib
```
**Tez-tez olan səbəb:** `yaş` yazmısınız, `yas` çağırırsınız.
Dəyişən adlarında ASCII çevrilməsi yoxdur.

### ⚠ ALQ-T024 — İstifadə olunmayan dəyişən
```alqor
dəyişən x = 5                // ⚠ heç yerdə işlənmir
dəyişən _ = 5                // ✓ qəsdən atılıb
```

### ✖ ALQ-T031 — `seç` bütün halları əhatə etmir
Sadalama üzərində `seç` ya bütün variantları, ya da `digər hallarda` içərməlidir.

### ✖ ALQ-T050 — `özü` yazılmayıb
```alqor
sinif A
    xassə ad: mətn
    metod f()
        yaz(ad)              // ✖
        yaz(özü.ad)          // ✓
    son
son
```

### ✖ ALQ-T051 — `əvəz et` tələb olunur
```alqor
sinif B miras A
    metod f() ... son           // ✖ A-da `f` var
    əvəz et metod f() ... son   // ✓
son
```

### ✖ ALQ-T052 — Mücərrəd sinifdən obyekt yaradıla bilməz
```alqor
mücərrəd sinif Fiqur ... son
dəyişən f = yeni Fiqur()     // ✖
```

### ✖ ALQ-T054 — İnterfeys metodu tətbiq edilməyib
İnterfeysin bütün metodlarını yazmaq lazımdır.

### ✖ ALQ-T070 — Bu API hədəf platformada mövcud deyil
```alqor
// hədəf = veb
dəyişən m = fayl.oxu("a.txt")            // ✖ brauzerdə fayl sistemi yoxdur
dəyişən m = brauzer.faylSeç()            // ✓
```

---

## M — Modul xətaları

### ✖ ALQ-M001 — Modul tapılmadı
**Səbəblər:**
1. Paket quraşdırılmayıb → `alqorpm əlavə <paket>`
2. Yol səhvdir → nisbi yol `./` və ya `../` ilə başlamalıdır
3. Fayl adı səhvdir → fayl adları hərfə həssasdır

### ✖ ALQ-M002 — Modulda belə ixrac yoxdur
Həmin üzv `ixrac et` ilə işarələnməyib.

### ✖ ALQ-M005 — Dövri modul asılılığı
```
a.alq → b.alq → a.alq
```
**Həll:** Ortaq hissəni üçüncü modula çıxarın.

### ✖ ALQ-M006 — İdxalda ad münaqişəsi
```alqor
gətir riyaziyyat.{kök}
gətir həndəsə.{kök}                   // ✖

gətir həndəsə.{kök kimi həndəsiKök}   // ✓
```

### ✖ ALQ-M013 — Python paketi tapılmadı
```
`numpy` Python paketi tapılmadı — `alqor python qur numpy` ilə quraşdırın
```
**Həll:** layihə qovluğunda `alqor python qur <paket>` (paket
`python_paketlər/` qovluğuna düşür). İdxal adı pip adından fərqlənə
bilər — mesaj düzgün adı göstərir (`yaml` → `pyyaml`, `PIL` → `pillow`).

### ✖ ALQ-M014 — Python istisnası (`PythonXətası`)
Python kodu istisna atıb. `x.pythonTipi` istisnanın sinfidir:
```alqor
cəhd et
    json.loads(mətn)
tut (x: PythonXətası) əgər x.pythonTipi == "JSONDecodeError"
    yaz("JSON pozulub")
son
```

### ✖ ALQ-M015 — Python kitabxanaları bu hədəfdə işləmir
`gətir python:…` yalnız əsas (Python) icraçısında işləyir: `alqor işlət`,
`alqor qur` (.pyz / .exe). `--js`, veb hədəfi və `alqor-rs` dəstəkləmir.

---

## R — İcra xətaları

### ✖ ALQ-R001 — Sıfıra bölmə
```alqor
yaz(10 ~/ 0)                 // ✖ BölməXətası
yaz(10.0 / 0.0)              // sonsuz (onluqda icazəlidir)
```

### ✖ ALQ-R002 — İndeks diapazondan kənar
```alqor
dəyişən s = [1, 2, 3]
yaz(s[5])                    // ✖ İndeksXətası
yaz(s.al(5, 0))              // ✓ standart dəyərlə
```

### ✖ ALQ-R003 — Lüğətdə açar yoxdur
```alqor
yaz(l["yoxdur"])             // ✖ AçarXətası
yaz(l.al("yoxdur", 0))       // ✓
```

### ✖ ALQ-R004 — Boş dəyərə müraciət
`!` operatoru ilə boş dəyəri açmağa cəhd etmisiniz.

### ✖ ALQ-R006 — Tam ədəd daşması
64 bit hüdudu aşılıb. `riyaziyyat.böyükTam` istifadə edin.

### ✖ ALQ-R009 — Fayl tapılmadı
```alqor
əgər fayl.vardır(yol) onda   // ✓ əvvəlcə yoxlayın
    dəyişən m = fayl.oxu(yol)
son
```

### ✖ ALQ-R010 — Stek daşması
Sonsuz rekursiya. Çıxış şərtini yoxlayın, və ya `@quyruqRekursiya` işlədin.

### ✖ ALQ-R018 — Kilid dalanı (deadlock)
İki sap bir-birinin kilidini gözləyir. Kilidləri həmişə eyni sırada tutun.

---

## S — Təhlükəsizlik xəbərdarlıqları

### ✖ ALQ-S001 — Kodda gizli açar aşkarlandı
```alqor
sabit API_AÇARI = "sk_live_abc123"       // ✖
sabit API_AÇARI = sistem.mühit("API_AÇARI")   // ✓
```

### ✖ ALQ-S002 — SQL birləşdirmə
```alqor
b.sorğu("SELECT * FROM i WHERE ad = '" + ad + "'")   // ✖ SQL inyeksiya
b.sorğu("SELECT * FROM i WHERE ad = $1", ad)         // ✓
```

### ⚠ ALQ-S003 — `| xam` filtri XSS riski yaradır
Şablonda `{{ x | xam }}` HTML qaçışını söndürür. Yalnız özünüzün yaratdığı
etibarlı HTML üçün işlədin.

### ⚠ ALQ-S004 — Zəif heş alqoritmi
`md5`, `sha1` parol üçün yararsızdır. `şifrə.parolHeş()` istifadə edin.

### ⚠ ALQ-S005 — HTTPS olmadan həssas məlumat
Parol və tokenlər yalnız HTTPS üzərindən göndərilməlidir.

---

## Xəta mesajını oxumaq

```
✖ ALQ-T008  Operator `+` bu tiplərə tətbiq edilmir
  ┌─ əsas.alq:12:15
  │
12│     yaz("Yaş: " + yaş)
  │          ───────┬─────
  │                 │
  │                 └─ `mətn` və `tam` toplanmır
  │
  = kömək: interpolyasiya istifadə edin: "Yaş: {yaş}"
  = kömək: və ya çevirin: "Yaş: " + mətnƏt(yaş)
  = sənəd: vuqar.pro/alqor/xeta/ALQ-T008
```

| Hissə | Mənası |
|---|---|
| `✖ ALQ-T008` | Kod və səviyyə |
| `əsas.alq:12:15` | Fayl : sətir : sütun |
| Kod parçası | Problemli yer altından xətlə |
| `= kömək:` | Düzəliş təklifi |
| `= sənəd:` | Ətraflı izah |

---

## Bütün xəbərdarlıqları xətaya çevirmək

```toml
[lint]
xəbərdarlıq_xətadır = doğru
```
və ya:
```bash
alqor qur --xəbərdarlıq-xətadır
```

---

**Növbəti:** [7. Tez Arayış](06-TEZ-ARAYIS.md)
