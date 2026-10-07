# Alqor — Bölmə 10: Standart Kitabxana

---

## 10.1 `nüvə` — avtomatik idxal olunur

Bu modul hər faylda `gətir` olmadan əlçatandır.

### Giriş / Çıxış
```alqor
yaz(...)                        // ekrana yaz, sonda yeni sətir
yazSətirsiz(...)                // yeni sətirsiz
yazXəta(...)                    // stderr-ə yaz
oxu() -> mətn                   // bir sətir oxu
oxu("Adınız: ") -> mətn         // soruşaraq oxu
oxuTam("Yaş: ") -> tam          // ədəd oxu (yanlışdırsa təkrar soruş)
oxuOnluq("Qiymət: ") -> onluq
oxuMəntiq("Razısınız? ") -> məntiq
oxuHamısı() -> mətn             // stdin-dən hamısını oxu
```

### Tip və çevirmə
```alqor
tip(x) -> mətn                  // "tam", "mətn", "siyahı[tam]" ...
tamƏt(x, standart?) -> tam
onluqƏt(x, standart?) -> onluq
mətnƏt(x) -> mətn
məntiqƏt(x) -> məntiq
simvolƏt(kod: tam) -> simvol
kodƏt(s: simvol) -> tam
```

### Kolleksiya köməkçiləri
```alqor
uzunluq(x) -> tam               // mətn, siyahı, lüğət, dəst, kortej
boşdur(x) -> məntiq
diapazon(son) -> Diapazon
diapazon(başlanğıc, son, addım?) -> Diapazon
sırala(kolleksiya, açar?) -> siyahı
tərs(kolleksiya) -> siyahı
cəm(kolleksiya) -> tam | onluq
minimum(...) -> T
maksimum(...) -> T
nömrələ(kolleksiya) -> siyahı[kortej[tam, T]]
zip(a, b) -> siyahı[kortej]
```

### Digər
```alqor
eynidir(a, b) -> məntiq         // istinad identikliyi
heş(x) -> tam
klonla(x) -> T                  // dərin kopya
çap(x)                          // debaq üçün strukturlu çap
ölç(funksiya)                   // icra müddətini ölç
dayan(kod: tam = 0)             // proqramı bitir
panika(mesaj: mətn)
```

---

## 10.2 `mətn`

### Metodlar
```alqor
dəyişən m = "Salam, Dünya"

m.uzunluq() -> tam                        // 12 (qrafem sayı)
m.baytUzunluğu() -> tam                   // UTF-8 bayt sayı
m.böyüyə() -> mətn                        // "SALAM, DÜNYA"  (az-AZ qaydası)
m.kiçiyə() -> mətn                        // "salam, dünya"
m.başBöyük() -> mətn                      // "Salam, dünya"
m.hərSözBöyük() -> mətn                   // "Salam, Dünya"
m.kəs() -> mətn                           // başdan-sondan boşluq sil
m.başKəs() / m.sonKəs() -> mətn
m.əvəz("a", "e") -> mətn                  // bütün uyğunluqları
m.əvəzİlk("a", "e") -> mətn
m.böl(", ") -> siyahı[mətn]               // ["Salam", "Dünya"]
m.böl() -> siyahı[mətn]                   // boşluqlara görə
m.böl("", 3) -> siyahı[mətn]              // maksimum 3 hissə
m.sətirlər() -> siyahı[mətn]
m.simvollar() -> siyahı[simvol]
m.baytlar() -> siyahı[bayt]
m.sözlər() -> siyahı[mətn]
m.birləşdir(siyahı) -> mətn               // ", ".birləşdir(["a","b"]) → "a, b"
m.ehtiva("Dün") -> məntiq
m.başlayır("Sal") -> məntiq
m.bitir("ya") -> məntiq
m.tap("Dün") -> tam?                      // indeks və ya boş
m.sonTap("a") -> tam?
m.hamısınıTap("a") -> siyahı[tam]
m.say("a") -> tam
m.dilim(0, 5) -> mətn                     // "Salam"
m.təkrar(3) -> mətn
m.tərs() -> mətn
m.doldur(20) -> mətn                      // sağa boşluq
m.solDoldur(20, "0") -> mətn
m.sağDoldur(20, "0") -> mətn
m.mərkəz(20) -> mətn
m.boşdur() -> məntiq
m.yalnızBoşluq() -> məntiq
m.rəqəmdir() -> məntiq
m.hərfdir() -> məntiq
m.müqayisə(digər) -> tam                  // az-AZ collation
m.müqayisəHərfsiz(digər) -> tam
m.normalizasiya() -> mətn                 // NFC
m.latınla() -> mətn                       // "ə"→"e", "ş"→"s" (URL üçün)
m.URLKodla() -> mətn
m.URLAç() -> mətn
m.base64Kodla() -> mətn
m.base64Aç() -> mətn
m.HTMLQaç() -> mətn
```

### Formatlaşdırma
```alqor
mətn.formatla("Salam, {}!", "Dünya")
mətn.formatla("{1} {0}", "dünya", "salam")
mətn.yerliƏdəd(1234.56) -> "1 234,56"      // Azərbaycan formatı
mətn.yerliPul(1234.56) -> "1 234,56 ₼"
mətn.yerliFaiz(0.185) -> "18,5 %"
```

### Azərbaycan dilinə xas
```alqor
mətn.hecalara("salam") -> ["sa", "lam"]
mətn.saitdir(`a`) -> məntiq
mətn.samitdir(`s`) -> məntiq
mətn.qalınSait(`a`) -> məntiq              // a, ı, o, u
mətn.incəSait(`ə`) -> məntiq               // e, ə, i, ö, ü
mətn.şəkilçi("kitab", "lar") -> "kitablar" // ahəng qanununa uyğun
mətn.hallandır("kitab", "yönlük") -> "kitaba"
mətn.yazıylaƏdəd(125) -> "yüz iyirmi beş"
mətn.sıraSayı(3) -> "üçüncü"
```

---

## 10.3 `siyahı`

```alqor
dəyişən s = [3, 1, 4, 1, 5]

// Dəyişdirən
s.əlavə(9)                      // sona əlavə
s.əlavəHamısı([2, 6])
s.daxilEt(0, 7)                 // indeksə daxil et
s.sil(2)                        // indeksə görə sil → silinən dəyər
s.silDəyər(1)                   // ilk tapılan dəyəri sil
s.silHamısı(1)                  // bütün uyğunluqları sil
s.sonunuSil() -> T              // pop
s.təmizlə()
s.sırala()                      // yerində sırala
s.sırala((a, b) => b <=> a)     // azalan
s.sıralaAçar((x) => x.yaş)
s.qarışdır()
s.tərsinəÇevir()

// Dəyişdirməyən (yeni siyahı qaytarır)
s.sıralanmış() -> siyahı
s.tərs() -> siyahı
s.dilim(1, 3) -> siyahı
s.çevir((x) => x * 2) -> siyahı
s.filtr((x) => x > 2) -> siyahı
s.yığ(0, (a, b) => a + b) -> T
s.yığSağdan(0, (a, b) => a + b) -> T
s.düzlə() -> siyahı              // iç-içə siyahıları açır
s.düzləÇevir((x) => [x, x]) -> siyahı
s.təkrarsız() -> siyahı
s.birləşdir(digər) -> siyahı
s.qrupla((x) => x % 2) -> lüğət
s.hissələrə(2) -> siyahı[siyahı] // [[3,1],[4,1],[5]]
s.pəncərə(3) -> siyahı[siyahı]   // sürüşən pəncərə
s.zip(digər) -> siyahı[kortej]
s.nömrələ() -> siyahı[kortej[tam, T]]

// Sorğu
s.uzunluq() -> tam
s.boşdur() -> məntiq
s.ehtiva(4) -> məntiq
s.tap((x) => x > 3) -> T?
s.tapİndeks((x) => x > 3) -> tam?
s.indeks(4) -> tam?
s.sonİndeks(1) -> tam?
s.say(1) -> tam
s.sayŞərt((x) => x > 2) -> tam
s.hamısı((x) => x > 0) -> məntiq
s.hərHansı((x) => x > 4) -> məntiq
s.heçBiri((x) => x > 10) -> məntiq
s.ilk() -> T?
s.son() -> T?
s.minimum() -> T?
s.maksimum() -> T?
s.cəm() -> T
s.orta() -> onluq
s.hərBiri((x) => yaz(x))
s.klonla() -> siyahı
```

---

## 10.4 `lüğət`

```alqor
dəyişən l = {"a": 1, "b": 2}

l.al("a") -> D?
l.al("z", 0) -> D                // standart dəyərlə
l.qoy("c", 3)
l.sil("a") -> D?
l.təmizlə()
l.ehtiva("a") -> məntiq
l.ehtivaDəyər(1) -> məntiq
l.uzunluq() -> tam
l.boşdur() -> məntiq
l.açarlar() -> siyahı[A]
l.dəyərlər() -> siyahı[D]
l.cütlər() -> siyahı[kortej[A, D]]
l.birləşdir(digər) -> lüğət
l.çevir((a, d) => (a, d * 2)) -> lüğət
l.filtr((a, d) => d > 1) -> lüğət
l.hərBiri((a, d) => yaz("{a}={d}"))
l.alVəYaQoy("x", () => hesabla()) -> D
l.yenilə("a", (köhnə) => köhnə + 1)
l.tərsÇevir() -> lüğət           // açar↔dəyər
l.klonla() -> lüğət
```

---

## 10.5 `dəst`

```alqor
dəyişən d = dəst(1, 2, 3)

d.əlavə(4)
d.sil(1)
d.ehtiva(2) -> məntiq
d.uzunluq() -> tam
d.təmizlə()
d.birləşmə(digər) -> dəst        // ∪
d.kəsişmə(digər) -> dəst         // ∩
d.fərq(digər) -> dəst            // \
d.simmetrikFərq(digər) -> dəst   // △
d.altDəstdir(digər) -> məntiq    // ⊆
d.üstDəstdir(digər) -> məntiq    // ⊇
d.kəsişmir(digər) -> məntiq
d.siyahıyaÇevir() -> siyahı
```

---

## 10.6 `riyaziyyat`

```alqor
gətir riyaziyyat kimi r

// Sabitlər
r.Pİ            // 3.14159265358979
r.E             // 2.71828182845905
r.TAU           // 2π
r.QIZILNİSBƏT   // 1.618...
r.SONSUZ
r.ƏDƏDDEYİL

// Əsas
r.mütləq(-5) -> 5
r.işarə(-5) -> -1
r.kök(16) -> 4.0
r.kubKök(27) -> 3.0
r.qüvvət(2, 10) -> 1024
r.eksp(1) -> 2.718
r.loq(100) -> 4.605             // təbii
r.loq10(100) -> 2.0
r.loq2(8) -> 3.0
r.loqƏsas(8, 2) -> 3.0

// Yuvarlaqlaşdırma
r.yuvarlaqlaşdır(3.7) -> 4
r.yuvarlaqlaşdır(3.456, 2) -> 3.46
r.aşağıYuvarlaq(3.7) -> 3        // floor
r.yuxarıYuvarlaq(3.2) -> 4       // ceil
r.kəs(3.7) -> 3                  // trunc

// Müqayisə
r.min(1, 2, 3) -> 1
r.maks(1, 2, 3) -> 3
r.məhdudla(dəyər, min, maks) -> T

// Triqonometriya (radian)
r.sin(x)  r.kos(x)  r.tan(x)
r.arksin(x)  r.arkkos(x)  r.arktan(x)  r.arktan2(y, x)
r.hipsin(x)  r.hipkos(x)  r.hiptan(x)
r.dərəcəyə(radian) -> onluq
r.radiana(dərəcə) -> onluq

// Tam ədədlər
r.ƏBOB(12, 18) -> 6              // ən böyük ortaq bölən
r.ƏKOB(4, 6) -> 12               // ən kiçik ortaq bölünən
r.faktorial(5) -> 120
r.sadədir(17) -> doğru
r.sadəBölənlər(12) -> [2, 2, 3]
r.modul(-7, 3) -> 2              // riyazi modul (həmişə müsbət)
r.modQüvvət(2, 10, 1000) -> 24

// Yoxlama
r.ədəddirmi(x) -> məntiq
r.sonludur(x) -> məntiq
r.tamdır(3.0) -> doğru

// Statistika
r.orta([1,2,3]) -> 2.0
r.median([1,2,3,4]) -> 2.5
r.moda([1,1,2]) -> 1
r.dispersiya([1,2,3]) -> onluq
r.standartKənarlaşma([1,2,3]) -> onluq

// Dəqiq hesablamalar (pul üçün)
r.onluqDəqiq("19.99") + r.onluqDəqiq("0.01")  // dəqiq 20.00
```

---

## 10.7 `təsadüfi`

```alqor
gətir təsadüfi kimi t

t.tam(1, 100) -> tam             // 1..100 daxil
t.onluq() -> onluq               // 0.0..1.0
t.onluq(1.0, 10.0) -> onluq
t.məntiq() -> məntiq
t.seç([1,2,3]) -> T
t.seçN([1,2,3], 2) -> siyahı
t.qarışdır(siyahı)
t.mətn(10) -> mətn               // təsadüfi 10 simvol
t.UUID() -> mətn
t.toxum(42)                      // təkrarlanan nəticə üçün
t.təhlükəsizBaytlar(32) -> siyahı[bayt]   // kriptoqrafik
```

---

## 10.8 `vaxt`

```alqor
gətir vaxt

// İndiki vaxt
vaxt.indi() -> Zaman
vaxt.bugün() -> Tarix
vaxt.möhür() -> tam              // Unix timestamp (saniyə)
vaxt.möhürMs() -> tam

// Yaratma
vaxt.tarix(2026, 10, 5) -> Tarix
vaxt.zaman(2026, 10, 5, 14, 30, 0) -> Zaman
vaxt.oxu("2026-10-05", "YYYY-MM-DD") -> Tarix
vaxt.ISO("2026-10-05T14:30:00Z") -> Zaman

// Zaman obyektinin üzvləri
z.il()  z.ay()  z.gün()  z.saat()  z.dəqiqə()  z.saniye()  z.millisaniyə()
z.həftəGünü() -> tam             // 1=B.e., 7=Bazar
z.ilinGünü() -> tam
z.həftə() -> tam
z.rüb() -> tam

// Formatlaşdırma
z.formatla("DD.MM.YYYY") -> "05.10.2026"
z.formatla("YYYY-MM-DD HH:mm:ss")
z.ISO() -> "2026-10-05T14:30:00Z"
z.azərbaycanca() -> "5 oktyabr 2026, bazar"
z.qısa() -> "05.10.2026"
z.nisbi() -> "2 saat əvvəl"

// Hesablama
z.əlavə(gün: 5, saat: 3) -> Zaman
z.çıx(ay: 1) -> Zaman
z.fərq(digər) -> Müddət
z.əvvəldir(digər) -> məntiq
z.sonradır(digər) -> məntiq
z.arasındadır(a, b) -> məntiq

// Müddət
vaxt.müddət(saat: 2, dəqiqə: 30)
m.saniyəyə() -> tam
m.insanÜçün() -> "2 saat 30 dəqiqə"

// Zaman qurşağı
vaxt.qurşaq("Asia/Baku")
z.qurşağaÇevir("UTC") -> Zaman

// Gözləmə
gözlə vaxt.gözlə(1000)
```

### Azərbaycan dilində ay və gün adları
```alqor
vaxt.ayAdı(10) -> "oktyabr"
vaxt.ayAdıBaş(10) -> "Oktyabr"
vaxt.günAdı(1) -> "bazar ertəsi"
vaxt.günAdıQısa(1) -> "B.e."
vaxt.ayAdları() -> ["yanvar", "fevral", ..., "dekabr"]
vaxt.bayramdır(tarix) -> məntiq          // Azərbaycan rəsmi bayramları
```

---

## 10.9 `fayl` və `qovluq`

```alqor
gətir fayl
gətir qovluq
gətir yol

// Fayl oxuma/yazma
fayl.oxu("a.txt") -> mətn
fayl.oxuBayt("a.bin") -> siyahı[bayt]
fayl.oxuSətirlər("a.txt") -> siyahı[mətn]
fayl.yaz("a.txt", "məzmun")
fayl.yazBayt("a.bin", baytlar)
fayl.əlavəEt("a.txt", "yeni sətir\n")

// Axın (böyük fayllar üçün)
istifadə f = fayl.aç("böyük.txt", "oxu")
    hər sətir üçün f.sətirlər() içində
        yaz(sətir)
    son
son

// Rejimlər: "oxu" | "yaz" | "əlavə" | "oxu-yaz"

// Fayl əməliyyatları
fayl.vardır("a.txt") -> məntiq
fayl.sil("a.txt")
fayl.kopyala("a.txt", "b.txt")
fayl.köçür("a.txt", "b.txt")
fayl.adDəyiş("a.txt", "b.txt")
fayl.ölçü("a.txt") -> tam
fayl.dəyişməVaxtı("a.txt") -> Zaman
fayl.icazə("a.txt") -> mətn       // "rw-r--r--"
fayl.icazəQoy("a.txt", "755")
fayl.sahib("a.txt") -> mətn
fayl.simvolikKeçid("a", "b")
fayl.MIMETipi("a.png") -> "image/png"
fayl.heş("a.txt", "sha256") -> mətn

// Qovluq
qovluq.yarat("yeni")
qovluq.yaratDərin("a/b/c")
qovluq.sil("yeni")
qovluq.silDərin("a")
qovluq.vardır("a") -> məntiq
qovluq.siyahı("a") -> siyahı[mətn]
qovluq.siyahıDərin("a") -> siyahı[mətn]
qovluq.axtar("a", "*.alq") -> siyahı[mətn]
qovluq.cari() -> mətn
qovluq.dəyiş("/home")
qovluq.ev() -> mətn
qovluq.müvəqqəti() -> mətn
qovluq.izlə("a", (hadisə, yol) => yaz("{hadisə}: {yol}"))

// Yol
yol.birləşdir("a", "b", "c.txt") -> "a/b/c.txt"
yol.mütləq("a.txt") -> "/home/v/a.txt"
yol.qovluq("/a/b/c.txt") -> "/a/b"
yol.fayl("/a/b/c.txt") -> "c.txt"
yol.ad("/a/b/c.txt") -> "c"
yol.uzantı("/a/b/c.txt") -> ".txt"
yol.normalizə("a/./b/../c") -> "a/c"
yol.nisbi("/a/b", "/a/b/c") -> "c"
yol.ayırıcı -> "/"
```

---

## 10.10 `json`

```alqor
gətir json

json.oxu('{"ad": "Aysel"}') -> istənilən
json.yaz(obyekt) -> mətn
json.yazGözəl(obyekt) -> mətn            // girintili
json.faylOxu("a.json") -> istənilən
json.faylYaz("a.json", obyekt)

// Tipli çevirmə
sinif İstifadəçi
    xassə ad: mətn
    xassə yaş: tam
son

dəyişən i = json.oxuTipli[İstifadəçi]('{"ad":"Aysel","yaş":24}')
dəyişən m = json.yaz(i)

// Annotasiyalarla idarə
sinif İstifadəçi
    @json("user_name")
    xassə ad: mətn

    @jsonAtla
    xassə gizliSahə: mətn

    @jsonStandart(18)
    xassə yaş: tam
son
```

---

## 10.11 `naxış` — requlyar ifadələr

```alqor
gətir naxış

dəyişən n = naxış.qur(x"(\d{3})-(\d{4})")

n.uyğundur("555-1234") -> məntiq
n.tap("tel: 555-1234") -> Uyğunluq?
n.hamısınıTap(mətn) -> siyahı[Uyğunluq]
n.əvəz(mətn, "XXX-XXXX") -> mətn
n.əvəzFunksiya(mətn, (u) => u.qrup(1)) -> mətn
n.böl(mətn) -> siyahı[mətn]

// Uyğunluq obyektі
u.mətn() -> mətn
u.başlanğıc() -> tam
u.son() -> tam
u.qrup(1) -> mətn?
u.adlıQrup("il") -> mətn?
u.qruplar() -> siyahı[mətn?]

// Bayraqlar
naxış.qur(x"abc", "i")          // hərfə həssas deyil
naxış.qur(x"^a", "m")           // çoxsətirli
naxış.qur(x"a.b", "s")          // nöqtə yeni sətri də tutur
naxış.qur(x"a b", "x")          // boşluqlar nəzərə alınmır

// Azərbaycan hərfləri dəstəklənir
naxış.qur(x"[əöüçşğıİ]+")
naxış.qur(x"\p{L}+")            // Unicode hərf sinfi
```

---

## 10.12 `şəbəkə` və `http`

```alqor
gətir http

// Sadə sorğular
dəyişən c = gözlə http.al("https://api.nümunə.az/istifadəçilər")
yaz(c.kod())                     // 200
yaz(c.mətn())
yaz(c.json())
yaz(c.başlıq("Content-Type"))

gözlə http.göndər("https://api.az/qeyd", gövdə: {"ad": "Aysel"})
gözlə http.yenilə(url, gövdə: ...)       // PUT
gözlə http.yamaq(url, gövdə: ...)        // PATCH
gözlə http.sil(url)

// Tam nəzarətlə
dəyişən sorğu = yeni http.Sorğu("GÖNDƏR", url)
sorğu.başlıq("Authorization", "Bearer {token}")
sorğu.başlıq("Accept", "application/json")
sorğu.gövdə(json.yaz(verilənlər))
sorğu.vaxtLimiti(5000)
dəyişən c = gözlə sorğu.göndər()

// Fayl yükləmə
gözlə http.faylYüklə(url, "yüklənən.zip", (faiz) => yaz("{faiz}%"))
gözlə http.faylGöndər(url, "sənəd.pdf")

// Cavab: c.kod(), c.uğurlu(), c.yoxla() (4xx/5xx → HTTPXətası),
//        c.mətn(), c.json(), c.bayt(), c.başlıq(ad), c.başlıqlar(), c.url()
// Xətalar: BağlantıXətası, VaxtBitdiXətası. Yalnız http(s):// — file:// yox.

// WebSocket (RFC 6455) — `ws://` və `wss://`
dəyişən sk = gözlə http.vebSoket("wss://nümunə.az/soket")   // başlıqlar, vaxtLimiti
sk.hadisə("mesaj", (m) => yaz(m))     // və ya hadisəsiz: sk.al(5000)
sk.hadisə("bağlandı", (kod, səbəb) => yaz("bağlandı {kod}"))
sk.göndər("salam")                    // mətn; bayt → ikili; siyahı/lüğət → JSON
sk.bağla()

// Aşağı səviyyə TCP/UDP
gətir şəbəkə
dəyişən s = gözlə şəbəkə.TCPBağlan("nümunə.az", 80)
dəyişən d = şəbəkə.UDPSoket(5000)
```

---

## 10.13 `verilənlər` — verilənlər bazası

```alqor
gətir verilənlər

// Bağlantı
dəyişən b = gözlə verilənlər.bağlan("postgres://user:pass@localhost/db")
dəyişən b = gözlə verilənlər.bağlan("sqlite://./məlumat.db")
dəyişən b = gözlə verilənlər.bağlan("mysql://...")

// Sürücülər asılılıqsızdır: sqlite (+ "sqlite::yaddaş:"), PostgreSQL
// (protokol v3; SCRAM-SHA-256/md5; ?sslmode=disable|prefer|require|verify-full),
// MySQL/MariaDB (native və caching_sha2 parolu; ?ssl=true). Parametrlər
// ($1… və ya ?) SQL-ə yapışdırılmır. Funksiyalar sinxrondur, `gözlə` də işləyir.

// Sorğu
dəyişən sətirlər = gözlə b.sorğu("SELECT * FROM istifadəçilər WHERE yaş > $1", 18)
hər s üçün sətirlər içində
    yaz(s["ad"])
son

dəyişən bir = gözlə b.birSətir("SELECT * FROM istifadəçilər WHERE id = $1", 5)
dəyişən say = gözlə b.birDəyər("SELECT COUNT(*) FROM istifadəçilər")
gözlə b.icra("INSERT INTO istifadəçilər (ad) VALUES ($1)", "Aysel")

// Tranzaksiya
gözlə b.tranzaksiya(asinxron funksiya(t)
    gözlə t.icra("UPDATE hesab SET balans = balans - 100 WHERE id = 1")
    gözlə t.icra("UPDATE hesab SET balans = balans + 100 WHERE id = 2")
son)

// Sorğu qurucusu (ORM)
dəyişən istifadəçilər = gözlə b.cədvəl("istifadəçilər")
    .seç("ad", "email")
    .harada("yaş", ">", 18)
    .vəHarada("aktiv", "=", doğru)
    .sırala("ad")
    .limit(10)
    .al()

// Yaradılan sətir: b.cədvəl("t").əlavəEt({...}) -> id; şərtsiz yenilə/sil
// qadağandır (təsadüfən bütün cədvəli silməyin qarşısı alınır)

// Model (ORM) — bütün sürücülərdə işləyir
@cədvəl("istifadəçilər")                // yoxdursa — sinif adı
sinif İstifadəçi miras verilənlər.Model
    @açar                               // yoxdursa — `id` xassəsi
    xassə id: tam
    @sütun("tam_ad")                    // bazadakı sütunun adı fərqlidirsə
    xassə ad: mətn
    xassə poçt: mətn?
    @keçici                             // bazada saxlanılmır
    xassə seçilib: məntiq = yanlış
    @əlaqə(çox: Sifariş)                // Sifariş.istifadəçiId → id
    xassə sifarişlər: siyahı[Sifariş] = []
son
// @əlaqə(bir: İstifadəçi, açar: "istifadəçiId") — əks istiqamət

İstifadəçi.istifadəEt(b)                // və ya verilənlər.Model.istifadəEt(b)
İstifadəçi.cədvəlYarat()                // CREATE TABLE IF NOT EXISTS (tiplərdən)
dəyişən i = İstifadəçi.yarat({"ad": "Aysel"})   // INSERT, id doldurulur
i.ad = "Aysel Məmmədova"
i.saxla()                               // id 0/boş → INSERT, yoxsa UPDATE
dəyişən t = İstifadəçi.tap(5)           // nümunə və ya boş
dəyişən hamısı = İstifadəçi.harada("ad", "bənzər", "A%").sırala("ad").al()
İstifadəçi.hamısı(); İstifadəçi.say()
i.yüklə("sifarişlər")                   // əlaqəni doldurur və qaytarır
i.lüğət()                               // {"id": …, "ad": …}
i.sil()

// Miqrasiya: qovluqdakı 001_*.sql, 002_*.sql … ardıcıl, hər biri bir dəfə,
// tranzaksiyada (yarımçıq qalmır)
b.miqrasiyaEt("miqrasiyalar/")
```

---

## 10.14 `şifrə` — kriptoqrafiya

```alqor
gətir şifrə

şifrə.heş("mətn") -> mətn                         // sha256, hex
şifrə.heş("mətn", "sha512") -> mətn               // + sha1, sha3_256, blake2b …
şifrə.HMAC("mesaj", "açar") -> mətn
şifrə.parolHeş("parol") -> mətn                   // "$scrypt$…" (duzlu)
şifrə.parolYoxla("parol", heş) -> məntiq          // sabit zamanlı
şifrə.açarYarat() -> bayt                         // 32 bayt
şifrə.parolAçarı(parol, duz) -> bayt              // paroldan AES açarı
şifrə.şifrələ(verilən, açar) -> bayt              // AES-256-GCM
şifrə.şifrəAç(şifrəli, açar) -> bayt              // dəyişdirilibsə xəta
şifrə.şifrəAçMətn(şifrəli, açar) -> mətn
şifrə.təsadüfiBayt(32) -> bayt
şifrə.təsadüfiMətn(32) -> mətn                    // URL-təhlükəsiz
şifrə.UUID() -> mətn
şifrə.bərabərdir(a, b) -> məntiq                  // sabit zamanlı müqayisə
şifrə.tokenYarat(verilənlər, açar, müddət: 3600) -> mətn    // JWT HS256
şifrə.tokenOxu(token, açar) -> lüğət              // imza + exp yoxlanılır
```

Qeydlər:

- **Ad:** `JWTYarat` yox, `tokenYarat` — Azərbaycan əlifbasında `W`
  yoxdur, ona görə Alqor adlarında da işlənə bilməz (§ 1.2).
- **Parol heşi:** etalon implementasiyada scrypt (N=2¹⁵, r=8, p=1);
  Python-un standart kitabxanasında Argon2 yoxdur. Format özünü
  təsvir edir, ona görə gələcəkdə Argon2id-ə keçid köhnə heşləri
  pozmur.
- **Şifrəli format:** `01 | nonce(12) | şifrəli | etiket(16)`.
- `tokenOxu` yalnız `HS256/384/512` qəbul edir — `alg: none` rədd
  edilir. Xətalar: `ŞifrələməXətası`, `JWTXətası`.

---

## 10.15 `sistem`

```alqor
gətir sistem

sistem.arqumentlər() -> siyahı[mətn]
sistem.mühit("YOL") -> mətn?
sistem.mühitQoy("AÇAR", "dəyər")
sistem.mühitHamısı() -> lüğət[mətn, mətn]
sistem.platforma() -> "linux" | "windows" | "macos" | "veb"
sistem.memarlıq() -> "x64" | "arm64"
sistem.nüvəSayı() -> tam
sistem.yaddaş() -> kortej[tam, tam]       // (istifadə olunan, ümumi)
sistem.istifadəçi() -> mətn
sistem.hostAdı() -> mətn
sistem.işləməMüddəti() -> Müddət
sistem.dayan(kod: tam)
sistem.əmr("ls -la") -> mətn              // xarici əmr işlət
sistem.proses("ls", ["-la"]) -> Proses
```

---

## 10.16 `test`

```alqor
gətir test

@sınaq
funksiya toplamaDüzgündür()
    test.bərabər(topla(2, 2), 4)
    test.bərabər(topla(-1, 1), 0, "sıfır alınmalıdır")
son

@sınaq("Boş siyahı 0 qaytarır")
funksiya boşSiyahı()
    test.bərabər(cəm([]), 0)
son

// Təsdiqlər
test.bərabər(a, b)
test.bərabərDeyil(a, b)
test.doğru(şərt)
test.yanlış(şərt)
test.boş(dəyər)
test.boşDeyil(dəyər)
test.ehtiva(kolleksiya, element)
test.atır(() => risk(), ArqumentXətası)
test.atmır(() => təhlükəsiz())
test.təxminən(3.14159, 3.14, dəqiqlik: 0.01)
test.uyğun(mətn, naxış)
test.uğursuz("səbəb")                     // sınağı dərhal uğursuz edir

// `test.atır` tutulan xətanı qaytarır — mesajını yoxlamaq olar
dəyişən x = test.atır(() => böl(1, 0), BölməXətası)
test.ehtiva(x.mesaj, "sıfır")

// Atlamaq
@atla("hələ yazılmayıb")
@sınaq
funksiya gələcək() ... son

// Qruplaşdırma
@sınaqQrupu("İstifadəçi testləri")
modul istifadəçiTestləri
    @əvvəl
    funksiya hazırla() ... son

    @sonra
    funksiya təmizlə() ... son

    @sınaq
    funksiya yaratma() ... son
son

// Parametrli testlər
@sınaqVerilənlər([(1, 1), (2, 4), (3, 9)])
funksiya kvadratTesti(giriş: tam, gözlənilən: tam)
    test.bərabər(kvadrat(giriş), gözlənilən)
son

// Saxta obyektlər (planlaşdırılır)
dəyişən saxta = test.saxta[VerilənlərBazası]()
saxta.gözlə("tap").qaytarsın(istifadəçi)
test.yoxla(saxta.çağırıldı("tap", 1))
```

Çalışdırma: `alqortest` və ya `alqortest sınaq/istifadəçi_sınaq.alq`

---

## 10.17 Digər modullar

Etalon implementasiyada hər modul `alqorc/alqor/modullar/` daxilində
ayrıca fayldır və yalnız `gətir` olunanda yüklənir. Faylın başındakı
sənəd modulun tam arayışıdır.

| Modul | Təyinatı | Vəziyyət |
|---|---|---|
| `jurnal` | Loglama | ✅ |
| `kodlaşdırma` | Base64, hex, URL, sorğu sətri, HTML, UTF-8, CRC32, `slug` | ✅ |
| `csv` | CSV oxuma/yazma — `ayırıcı: "avto"`, `çevir:`, Excel üçün `bom:` | ✅ |
| `toml` | TOML 1.0 oxuma + yazma | ✅ |
| `yaml` | YAML 1.2 (bloklar, axın, `\|` `>`, ankor/alias, `<<`, çox sənəd) | ✅ |
| `xml` | XML → `düyün` ağacı, CSS seçicisi, lüğətə/lüğətdən; `<!ENTITY>` rədd edilir | ✅ |
| `html` | HTML ayırıcı (`tap`, `tapHamısı`), `mətnə`, XSS `təmizlə` | ✅ |
| `konfiq` | TOML/YAML/JSON/ENV/INI, fayl birləşdirmə, mühit dəyişəni ilə əvəzləmə | ✅ |
| `sıxma` | gzip, zlib, zip, tar (zip-slip və keçid hücumlarına qarşı yoxlama) | ✅ |
| `şifrə` | Bölmə 10.14 | ✅ |
| `http`, `şəbəkə` | Bölmə 10.12 (WebSocket daxil) | ✅ |
| `verilənlər` | Bölmə 10.13 (SQLite, PostgreSQL, MySQL; ORM) | ✅ |
| `şəkil` | Şəkil emalı (ölçü dəyişmə, format çevirmə) | ⏳ |
| `poçt` | E-poçt göndərmə (SMTP) | ⏳ |
| `keş` | Yaddaş və Redis keşi | ⏳ |
| `növbə` | İş növbələri | ⏳ |
| `planlayıcı` | Cron tipli tapşırıqlar | ⏳ |
| `validasiya` | Giriş yoxlaması | ⏳ |
| `lokalizasiya` | Çoxdilli dəstək | ⏳ |
| `pul` | Dəqiq pul hesablamaları və valyuta | ⏳ |
| `qrafik` | Diaqram və qrafiklər | ⏳ |
| `pdf` | PDF yaratma | ⏳ |
| `ffi` | C kitabxanaları ilə əlaqə | ⏳ |
| `veb` | Veb freymvork (Bölmə 11) | ✅ |
| `pəncərə` | Desktop GUI (Bölmə 12) | ✅ |

### `düyün` — XML və HTML ağacı

```alqor
gətir html

dəyişən s = html.oxu(mətn)
dəyişən başlıq = s.tap("title")?.mətn() ?? "başlıqsız"
hər a üçün s.tapHamısı("nav > a[href]") içində
    yaz(a.mətn(), a.atribut("href"))
son
```

Metodlar: `ad()`, `atribut(ad, standart?)`, `atributlar()`,
`atributQoy(ad, d)`, `mətn()`, `uşaqlar()`, `valideyn()`, `tap(seçici)`
→ `düyün?`, `tapHamısı(seçici)`, `əlavəEt(u)`, `xml(gözəl?)`, `html()`,
`lüğət()`. Seçici: `teq`, `.sinif`, `#id`, `[atr]`, `[atr=d]`
(`^=` `$=` `*=` `~=` `|=`), nəsil, `>`, `,`.

### Yeni xəta tipləri

`CSVXətası`, `TOMLXətası`, `YAMLXətası`, `XMLXətası`, `SıxmaXətası`,
`KodlaşdırmaXətası` — hamısı `FormatXətası`-nın alt növüdür;
`KonfiqXətası`, `ŞifrələməXətası` (→ `JWTXətası`), `VerilənlərXətası`
(→ `MəhdudiyyətXətası`) — `Xəta`-nın; `HTTPXətası` — `ŞəbəkəXətası`-nın.
