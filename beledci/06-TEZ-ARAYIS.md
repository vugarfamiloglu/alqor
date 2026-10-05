# Alqor Bələdçisi — 7. Tez Arayış (Cheat Sheet)

> Bir səhifəlik xülasə. Çap edib masanızda saxlaya bilərsiniz.

---

## Əsaslar

```alqor
// Şərh
/* Blok şərh */
/// Sənəd şərhi

yaz("Salam")                   // çıxış
dəyişən ad = oxu("Ad: ")       // giriş
dəyişən n = oxuTam("Say: ")
```

## Dəyişənlər

```alqor
dəyişən a = 5                  // dəyişə bilər
sabit B = 5                    // dəyişməz bağlama
dəyişməz C = [1,2]             // dərin dəyişməz
dəyişən d: tam = 5             // açıq tip
dəyişən x, y = 1, 2            // çoxlu
dəyişən p, q = (3, 4)          // dağıtma
```

## Tiplər

```
tam  onluq  mətn  məntiq  simvol  bayt
siyahı[T]  lüğət[A,D]  dəst[T]  kortej[A,B]
T?  (ixtiyari)   A|B  (birləşmə)   istənilən   heç
```

## Operatorlar

```
+  -  *  /  ~/  %  **              hesab (~/ = tam bölmə)
== != <  >  <= >= <=>              müqayisə
və  və ya  deyil     (&& || !)     məntiq
&  |  ^  ~  << >> >>>              bit
=  += -= *= /= %= **= ??=          mənimsətmə
?? ?. ?= !                         boş ilə iş
.. ..<  addım                      diapazon
... içindədir  tipidir  kimi  |>   xüsusi
```

**Prioritet (yuxarıdan):**
`() [] .` → `yeni` → `**` → tək `- deyil ~` → `kimi` → `* / ~/ %` →
`+ -` → `<< >>` → `& ^ |` → `..` → `< > <= >=` → `== !=` →
`və` → `və ya` → `??` → `|>` → `=`

## Şərtlər

```alqor
əgər şərt onda
    ...
yoxsa əgər şərt onda
    ...
yoxsa                          // və ya: əks halda
    ...
son

// İfadə kimi
dəyişən x = əgər a onda 1 yoxsa 2 son

// İxtiyari bağlama
varsa i = tap() onda ... yoxsa ... son
yoxdursa i = tap() onda qaytar son
```

## Seçim

```alqor
seç dəyər
    hal 1 → yaz("bir")
    hal 2, 3 → yaz("iki və ya üç")
    hal 10..20 → yaz("onluq")
    hal x əgər x > 100 → yaz("böyük")
    digər hallarda → yaz("digər")
son

seç tipi x
    hal tam → ...
    hal mətn → ...
son
```

## Dövrlər

```alqor
hər x üçün siyahı içində ... son
hər i, x üçün siyahı içində ... son
hər a, d üçün lüğət içində ... son
hər i üçün 1..10 içində ... son
hər i üçün 1..10 addım 2 içində ... son
hər x üçün s içində əgər x > 5 ... son

nə qədər ki şərt ... son
həmişə ... son
təkrarla 5 dəfə ... son
təkrarla i, 5 dəfə ... son

dayan            davam et
dayan etiket     davam et etiket
```

## Funksiyalar

```alqor
funksiya ad(a: tam, b: tam = 0) -> tam
    qaytar a + b
son

funksiya çox(...ədədlər: tam) -> tam ... son
funksiya adlı(*, açar: mətn) ... son

dəyişən f = (x) => x * 2
dəyişən g = funksiya(x) qaytar x * 2 son

asinxron funksiya h() -> tam ... son
generator funksiya g() -> tam ... ver x ... son
```

## Siniflər

```alqor
sinif Ad miras Baza tətbiq İnterfeys
    açıq xassə a: tam
    gizli xassə _b: mətn
    statik xassə say: tam = 0

    xassə hesablanan: tam
        oxu qaytar özü.a * 2 son
        yaz(dəyər) özü.a = dəyər ~/ 2 son
    son

    qurucu(a: tam)
        üst()
        özü.a = a
    son

    metod f() ... son
    statik metod g() ... son
    əvəz et metod h() ... son
    mücərrəd metod i()
son

struktur Nöqtə                 // dəyər tipi
    xassə x: onluq
son

interfeys Çapedilən
    metod mətnƏt() -> mətn
son

sadalama Rəng
    QIRMIZI
    YAŞIL
son

obyektJurnal ... son           // tək nüsxə
genişlət mətn ... son          // mövcud tipə metod əlavə
```

## Xətalar

```alqor
cəhd et
    ...
tut (x: TipXətası)
    ...
tut (x: Xəta) əgər x.kod == 404
    ...
nəhayət
    ...
son

at Xəta("mesaj")
iddia şərt, "mesaj"
təmin şərt yoxsa at Xəta("...") son
gecikdir təmizlə()
istifadə f = fayl.aç("a") ... son
```

## Modullar

```alqor
gətir riyaziyyat
gətir riyaziyyat kimi r
gətir riyaziyyat.{kök, Pİ}
gətir riyaziyyat.{kök kimi k}
gətir "./yerli.alqor" kimi y

ixrac et funksiya f() ... son
ixrac et {a, b}
```

## Asinxron

```alqor
asinxron funksiya f() -> tam ... son
dəyişən x = gözlə f()
dəyişən (a, b) = gözlə paralel(f1(), f2())
dəyişən hamısı = gözlə paralel.hamısı([f1(), f2()])
gözlə vaxt.gözlə(1000)
```

## Siyahı metodları

```
əlavə  daxilEt  sil  silDəyər  sonunuSil  təmizlə
sırala  qarışdır  tərsinəÇevir
sıralanmış  tərs  dilim  çevir  filtr  yığ  düzlə
təkrarsız  birləşdir  qrupla  hissələrə  zip  nömrələ
uzunluq  boşdur  ehtiva  tap  tapİndeks  indeks  say
hamısı  hərHansı  heçBiri  ilk  son  minimum  maksimum
cəm  orta  hərBiri  klonla
```

## Mətn metodları

```
uzunluq  böyüyə  kiçiyə  başBöyük  hərSözBöyük
kəs  başKəs  sonKəs  əvəz  əvəzİlk  böl  birləşdir
sətirlər  simvollar  sözlər  baytlar
ehtiva  başlayır  bitir  tap  sonTap  say
dilim  təkrar  tərs  doldur  solDoldur  mərkəz
boşdur  rəqəmdir  hərfdir  müqayisə  normalizasiya
latınla  URLKodla  base64Kodla  HTMLQaç
```

## Lüğət metodları

```
al  qoy  sil  təmizlə  ehtiva  ehtivaDəyər
uzunluq  boşdur  açarlar  dəyərlər  cütlər
birləşdir  çevir  filtr  hərBiri  alVəYaQoy  yenilə
```

## Çevirmə

```alqor
tamƏt("42")        onluqƏt("3.14")    mətnƏt(42)
məntiqƏt("doğru")  x kimi tam         x kimi? tam
tip(x)             uzunluq(x)         klonla(x)
```

## Mətn formatı

```alqor
"Salam, {ad}!"
"{qiymət:.2}"          // 2 onluq
"{say:05}"             // 00042
"{n:,}"                // 1,000,000
"{n:,az}"              // 1 000 000
"{n:x}" "{n:b}"        // onaltılıq, ikilik
"{m:<10}" "{m:>10}" "{m:^10}"   // düzülmə
```

## Annotasiyalar

```
@sınaq  @köhnəlmiş("...")  @daxili  @saf  @yaddaşla
@quyruqRekursiya  @yalnızHədəf("veb")  @json("ad")
@cədvəl("ad")  @açar  @API("/yol")
```

## CLI əmrləri

```bash
alqor yeni <ad> [--şablon veb|desktop|kitabxana]
alqor işlət [fayl] [--izlə]
alqor qur [--hədəf veb|linux-x64|...] [--buraxılış]
alqor yoxla                 # sürətli xəta yoxlaması
alqor sına [--örtük]
alqor format
alqor söhbət                # REPL
alqor paketlə --hədəf deb|appimage|flatpak
alqor yerləşdir --növ docker|systemd|statik
alqorpm əlavə|sil|yüklə|yenilə|axtar <paket>
alqorfmt [--yoxla] [--ascii-düzəlt] .
alqorlint [--düzəlt] .
```

## Azərbaycan hərfləri (redaktorda)

```
;e → ə    ;i → ı    ;o → ö    ;u → ü
;c → ç    ;s → ş    ;g → ğ    ;I → İ
;E → Ə    ;C → Ç    ;S → Ş    ;G → Ğ

Avtomatik: eger→əgər, deyisen→dəyişən, ucun→üçün, ...
```

## Veb — ən qısa server

```alqor
gətir veb
dəyişən s = yeni veb.Server()
s.al("/", (q) => veb.mətn("Salam"))
s.dinlə(8080)
```

## Desktop — ən qısa pəncərə

```alqor
gətir pəncərə
dəyişən p = yeni pəncərə.Pəncərə("Ad", 800, 600)
p.məzmun(<h1>Salam</h1>)
p.göstər()
pəncərə.işlət()
```

---

## Açar sözlərin tam siyahısı

```
dəyişən sabit dəyişməz funksiya sinif struktur interfeys
sadalama modul obyekt qarışıq tip qurucu silinsin metod
xassə genişlət komponent mağaza

açıq gizli qorunan statik mücərrəd son tənbəl global
asinxron generator

əgər onda yoxsa əks halda varsa yoxdursa
seç hal digər hallarda keç

nə qədər ki həmişə təkrarla dəfə hər üçün içində addım
dayan davam et

qaytar ver gözlə paralel gecikdir istifadə blok
cəhd tut nəhayət at iddia təmin bərpa
özü üst yeni miras tətbiq ilə əvəz

gətir ixrac kimi dan standart başlanğıc bitiş
və ya deyil içindədir tipidir boşdur eynidir
doğru yanlış boş sonsuz ƏdədDeyil

tam onluq mətn məntiq simvol bayt siyahı lüğət
dəst kortej funksiyaTipi istənilən heç

vəziyyət hadisə hesablanan əməl göstər
sınaq dayanNöqtəsi ölç sil
```
