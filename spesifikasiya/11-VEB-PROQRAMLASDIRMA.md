# Alqor — Bölmə 11: Veb Proqramlaşdırma

> Bir dil, üç tərəf: **server**, **ön tərəf** (brauzer) və **paylaşılan model**.

---

## 11.1 Veb layihənin quruluşu

```
veb-layihəm/
├── layihe.alq
├── mənbə/
│   ├── server.alq          # server tərəfi  → native binar
│   ├── müştəri.alq         # brauzer tərəfi → JS/WASM
│   ├── ortaq/                # hər iki tərəfdə işləyən kod
│   │   └── model.alq
│   └── səhifə/
│       ├── əsas.alq
│       └── haqqında.alq
├── statik/
│   ├── üslub.css
│   └── şəkil/
└── şablon/
    └── əsas.html
```

---

## 11.2 HTTP server

### Ən sadə server
```alqor
gətir veb

funksiya əsas()
    dəyişən server = yeni veb.Server()

    server.al("/", funksiya(sorğu)
        qaytar veb.mətn("Salam, dünya!")
    son)

    server.dinlə(8080)
    yaz("Server işləyir: http://localhost:8080")
son
```

### Marşrutlar
```alqor
server.al("/", idarəedici)                    // GET
server.göndər("/qeyd", idarəedici)            // POST
server.yenilə("/istifadəçi/:id", idarəedici)  // PUT
server.yamaq("/istifadəçi/:id", idarəedici)   // PATCH
server.sil("/istifadəçi/:id", idarəedici)     // DELETE
server.hamısı("/*", idarəedici)               // bütün metodlar

// Parametrli marşrutlar
server.al("/istifadəçi/:id", funksiya(sorğu)
    dəyişən id = sorğu.parametr("id")
    qaytar veb.json({"id": id})
son)

// İxtiyari parametr
server.al("/məqalə/:slug?", ...)

// Joker
server.al("/fayl/*yol", ...)

// Marşrut qrupları
server.qrup("/api/v1", funksiya(q)
    q.al("/istifadəçilər", istifadəçiSiyahı)
    q.göndər("/istifadəçilər", istifadəçiYarat)
    q.al("/istifadəçilər/:id", istifadəçiGöstər)
son)
```

### Sorğu obyekti
```alqor
sorğu.metod() -> mətn                 // "AL", "GÖNDƏR"
sorğu.yol() -> mətn                   // "/istifadəçi/5"
sorğu.tamURL() -> mətn
sorğu.parametr("id") -> mətn?         // marşrut parametri
sorğu.sorğuParametr("axtar") -> mətn? // ?axtar=...
sorğu.sorğuParametrHamısı() -> lüğət
sorğu.başlıq("Accept") -> mətn?
sorğu.başlıqlar() -> lüğət
sorğu.gövdə() -> mətn
sorğu.json() -> istənilən
sorğu.form() -> lüğət[mətn, mətn]
sorğu.fayl("sənəd") -> YüklənmişFayl?
sorğu.kuki("sessiya") -> mətn?
sorğu.IP() -> mətn
sorğu.istifadəçiAgenti() -> mətn
sorğu.sessiya() -> Sessiya
sorğu.istifadəçi() -> İstifadəçi?     // auth ara proqramından
```

### Cavab
```alqor
veb.mətn("Salam")                              // text/plain
veb.html("<h1>Salam</h1>")                     // text/html
veb.json({"ad": "Aysel"})                      // application/json
veb.fayl("/yol/sənəd.pdf")                     // fayl göndər
veb.yüklə("/yol/a.zip", "ad.zip")              // yükləmə kimi
veb.yönləndir("/giriş")                        // 302
veb.yönləndirDaimi("/yeni")                    // 301
veb.boş(204)
veb.xəta(404, "Tapılmadı")
veb.şablon("səhifə.html", {"ad": "Aysel"})

// Zəncirləmə
veb.json(verilənlər)
    .kod(201)
    .başlıq("X-Ümumi", "100")
    .kuki("sessiya", token, müddət: 3600, yalnızHTTP: doğru, təhlükəsiz: doğru)
```

### Ara proqram (middleware)
```alqor
// Qlobal
server.ara(veb.jurnal())
server.ara(veb.CORS(mənbələr: ["https://nümunə.az"]))
server.ara(veb.sıxma())
server.ara(veb.sürətLimiti(100, "1dəq"))
server.ara(veb.təhlükəsizlikBaşlıqları())
server.ara(veb.sessiya(gizli: sistem.mühit("SESSIYA_AÇARI")))

// Öz ara proqramın
server.ara(asinxron funksiya(sorğu, növbəti)
    dəyişən başlanğıc = vaxt.möhürMs()
    dəyişən cavab = gözlə növbəti(sorğu)
    jurnal.info("{sorğu.metod()} {sorğu.yol()} — {vaxt.möhürMs() - başlanğıc}ms")
    qaytar cavab
son)

// Marşruta xas
server.al("/admin", [adminTələbOlunur], adminPanel)
```

### Statik fayllar
```alqor
server.statik("/statik", "statik/")
server.statik("/", "public/", indeks: "index.html")
```

### Xəta idarəedicisi
```alqor
server.xətaİdarəedicisi(funksiya(sorğu, xəta)
    jurnal.xəta("Sorğu xətası", xəta: xəta)
    qaytar veb.json({"xəta": xəta.mesaj}).kod(500)
son)

server.tapılmadı(funksiya(sorğu)
    qaytar veb.şablon("404.html").kod(404)
son)
```

---

## 11.3 Şablonlar

### `.alqorhtml` şablon faylı
```html
<!-- şablon/səhifə.alqorhtml -->
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <title>{{ başlıq }}</title>
</head>
<body>
    <h1>Salam, {{ ad }}!</h1>

    {% əgər istifadəçi.adminDir %}
        <a href="/admin">Admin panel</a>
    {% yoxsa %}
        <p>Adi istifadəçi</p>
    {% son %}

    <ul>
    {% hər m üçün məhsullar içində %}
        <li>{{ m.ad }} — {{ m.qiymət | pul }}</li>
    {% yoxsa %}
        <li>Məhsul yoxdur</li>
    {% son %}
    </ul>

    {% daxilEt "altbilgi.alqorhtml" %}
</body>
</html>
```

### Filtrlər
```
{{ ad | böyüyə }}
{{ qiymət | pul }}
{{ qiymət | yuvarlaqlaşdır(2) }}
{{ tarix | format("DD.MM.YYYY") }}
{{ mətn | kəs(100) }}
{{ html | xam }}              <!-- qaçışsız (diqqətli olun) -->
{{ siyahı | uzunluq }}
{{ ad | standart("Qonaq") }}
```

> **Təhlükəsizlik:** `{{ }}` içindəki hər şey avtomatik HTML-qaçış edilir.
> XSS üçün yalnız `| xam` təhlükəlidir.

### Şablon mirası
```html
<!-- əsas.alqorhtml -->
<html><body>
    {% blok məzmun %}{% son %}
</body></html>

<!-- səhifə.alqorhtml -->
{% genişlət "əsas.alqorhtml" %}
{% blok məzmun %}
    <h1>Səhifə məzmunu</h1>
{% son %}
```

---

## 11.4 Ön tərəf (brauzer)

Alqor kodu JavaScript/WASM-a kompilyasiya olunur və brauzerdə işləyir.

### DOM ilə iş
```alqor
gətir brauzer

dəyişən düymə = brauzer.tap("#göndər")
düymə.hadisə("klik", funksiya(h)
    brauzer.tap("#nəticə").mətn("Basıldı!")
son)

brauzer.tapHamısı(".element").hərBiri((e) => e.sinifƏlavə("aktiv"))

// Element yaratmaq
dəyişən div = brauzer.yarat("div")
div.sinif("qutu")
div.mətn("Salam")
brauzer.gövdə().əlavə(div)
```

### Komponent modeli
```alqor
gətir veb.ön

komponent Sayğac
    vəziyyət say: tam = 0

    metod artır()
        özü.say += 1                 // avtomatik yenidən render
    son

    göstər()
        qaytar <div sinif="sayğac">
            <h2>Say: {özü.say}</h2>
            <button klik={özü.artır}>Artır</button>
        </div>
    son
son

komponent Tətbiq
    göstər()
        qaytar <div>
            <h1>Mənim tətbiqim</h1>
            <Sayğac />
        </div>
    son
son

ön.quraşdır(Tətbiq, "#kök")
```

### Xassələr və hadisələr
```alqor
komponent Düymə
    xassə mətn: mətn
    xassə rəng: mətn = "mavi"
    hadisə basıldı

    göstər()
        qaytar <button
            sinif="düymə düymə-{özü.rəng}"
            klik={() => özü.basıldı.işəSal()}>
            {özü.mətn}
        </button>
    son
son

// İstifadə
<Düymə mətn="Göndər" rəng="yaşıl" basıldı={özü.göndər} />
```

### Vəziyyət idarəetməsi
```alqor
mağaza TətbiqVəziyyəti
    vəziyyət istifadəçi: İstifadəçi? = boş
    vəziyyət səbət: siyahı[Məhsul] = []

    hesablanan ümumiMəbləğ: onluq
        qaytar özü.səbət.yığ(0.0, (c, m) => c + m.qiymət)
    son

    əməl səbətəƏlavə(m: Məhsul)
        özü.səbət.əlavə(m)
    son

    asinxron əməl istifadəçiYüklə(id: tam)
        özü.istifadəçi = gözlə api.istifadəçiAl(id)
    son
son
```

### Marşrutlaşdırma (SPA)
```alqor
ön.marşrutlar([
    {yol: "/", komponent: ƏsasSəhifə},
    {yol: "/məhsul/:id", komponent: MəhsulSəhifəsi},
    {yol: "/səbət", komponent: Səbət, qoruma: girişTələbOlunur},
    {yol: "*", komponent: Səhifə404}
])

ön.get("/məhsul/5")
ön.geri()
```

### Brauzer API-ləri
```alqor
brauzer.yerliYaddaş.qoy("açar", "dəyər")
brauzer.yerliYaddaş.al("açar") -> mətn?
brauzer.sessiyaYaddaşı.qoy(...)
brauzer.kuki.al("sessiya")
brauzer.URL() -> mətn
brauzer.tarixçə.əlavə("/yeni-yol")
brauzer.məkan() -> Koordinat               // geolokasiya (icazə ilə)
brauzer.bildiriş("Başlıq", "Mesaj")
brauzer.panoyaKopyala("mətn")
brauzer.faylSeç() -> Fayl?
brauzer.çapEt()
brauzer.tamEkran()
brauzer.mövzu() -> "işıqlı" | "qaranlıq"
```

---

## 11.5 Paylaşılan kod (server + müştəri)

```alqor
// ortaq/model.alq — hər iki tərəfdə işləyir
ixrac et sinif Məhsul
    xassə id: tam
    xassə ad: mətn
    xassə qiymət: onluq

    metod formatlıQiymət() -> mətn
        qaytar mətn.yerliPul(özü.qiymət)
    son
son

ixrac et funksiya yoxla(m: Məhsul) -> siyahı[mətn]
    dəyişən xətalar = []
    əgər m.ad.kəs() == "" onda
        xətalar.əlavə("Ad boş ola bilməz")
    son
    əgər m.qiymət <= 0 onda
        xətalar.əlavə("Qiymət müsbət olmalıdır")
    son
    qaytar xətalar
son
```

> Eyni validasiya həm brauzerdə (dərhal cavab üçün), həm də serverdə
> (təhlükəsizlik üçün) işləyir — **kodu iki dəfə yazmağa ehtiyac yoxdur.**

### Tipli API çağırışları
```alqor
// server.alq
@API("/api/məhsul/:id")
asinxron funksiya məhsulAl(id: tam) -> Məhsul
    qaytar gözlə verilənlər.tap(id)
son

// müştəri.alq — avtomatik yaradılmış müştəri
dəyişən m: Məhsul = gözlə api.məhsulAl(5)
```

---

## 11.6 Real vaxt — WebSocket

```alqor
// Server
server.soket("/çat", funksiya(soket)
    soket.hadisə("qoşuldu", funksiya()
        yaz("Yeni istifadəçi")
        soket.otağaQoşul("ümumi")
    son)

    soket.hadisə("mesaj", funksiya(m)
        soket.otağaYayımla("ümumi", m)
    son)

    soket.hadisə("ayrıldı", funksiya()
        yaz("İstifadəçi çıxdı")
    son)
son)

// Müştəri
dəyişən soket = veb.soketBağlan("/çat")
soket.göndər("Salam hamıya!")
soket.hadisə("mesaj", (m) => yaz(m))
```

---

## 11.7 Autentifikasiya

```alqor
gətir veb.auth

server.ara(auth.sessiya(gizli: sistem.mühit("AÇAR")))

server.göndər("/giriş", asinxron funksiya(sorğu)
    dəyişən f = sorğu.form()
    dəyişən i = gözlə İstifadəçi.tapEmail(f["email"])

    əgər i boşdur və ya deyil şifrə.parolYoxla(f["parol"], i.parolHeş) onda
        qaytar veb.json({"xəta": "Yanlış məlumat"}).kod(401)
    son

    sorğu.sessiya().qoy("istifadəçiId", i.id)
    qaytar veb.yönləndir("/panel")
son)

// Qoruyucu
funksiya girişTələbOlunur(sorğu, növbəti)
    əgər sorğu.sessiya().al("istifadəçiId") boşdur onda
        qaytar veb.yönləndir("/giriş")
    son
    qaytar növbəti(sorğu)
son

server.al("/panel", [girişTələbOlunur], panel)

// JWT
dəyişən token = auth.tokenYarat({"id": i.id}, müddət: "7g")
server.ara(auth.token(gizli: AÇAR))
```

---

## 11.8 Təhlükəsizlik (standart olaraq aktiv)

| Qoruma | Mexanizm |
|---|---|
| XSS | Şablonlarda avtomatik HTML qaçış |
| SQL inyeksiya | Parametrli sorğular məcburi |
| CSRF | `veb.CSRF()` ara proqramı, formalarda avtomatik token |
| Klikcacking | `X-Frame-Options: DENY` |
| MIME sniffing | `X-Content-Type-Options: nosniff` |
| HTTPS | `veb.HTTPSMəcburi()` |
| Sürət limiti | `veb.sürətLimiti()` |
| Parol | Argon2id, düz mətn saxlanması qadağandır |
| Sessiya | `HttpOnly`, `Secure`, `SameSite=Lax` standart |
| Gizli açarlar | Yalnız mühit dəyişənlərindən; kodda tapılsa `ALQ-S001` |

---

## 11.9 Kompilyasiya və yerləşdirmə

```bash
# İnkişaf — canlı yeniləmə ilə
alqor veb inkişaf
# → http://localhost:8080, kod dəyişəndə brauzer avtomatik yenilənir

# Buraxılış
alqor qur --hədəf veb --buraxılış
```

Nəticə:
```
qurma/veb/
├── server                    # statik Linux binarı (asılılıqsız)
├── public/
│   ├── index.html
│   ├── tətbiq.js             # kiçildilmiş
│   ├── tətbiq.wasm           # ağır hesablamalar üçün
│   └── statik/
└── Dockerfile
```

### Yerləşdirmə variantları
```bash
alqor yerləşdir --növ statik     # Netlify, Vercel, GitHub Pages
alqor yerləşdir --növ docker     # Docker image
alqor yerləşdir --növ systemd    # Linux serverdə xidmət
alqor yerləşdir --növ nginx      # nginx konfiqurasiyası ilə birlikdə
```

**Serverin Alqor bilməsinə ehtiyac yoxdur** — çıxış adi ELF binarıdır,
və ya adi HTML/JS/WASM fayllarıdır. İstənilən hostinq işlədir.

---

## 11.10 Nümunə: tam veb tətbiq

```alqor
// mənbə/server.alq
gətir veb
gətir verilənlər

sinif Tapşırıq
    xassə id: tam
    xassə mətn: mətn
    xassə bitib: məntiq = yanlış
son

dəyişən tapşırıqlar: siyahı[Tapşırıq] = []
dəyişən növbətiId = 1

funksiya əsas()
    dəyişən s = yeni veb.Server()

    s.ara(veb.jurnal())
    s.statik("/statik", "statik/")

    s.al("/", funksiya(sorğu)
        qaytar veb.şablon("siyahı.alqorhtml", {"tapşırıqlar": tapşırıqlar})
    son)

    s.al("/api/tapşırıq", funksiya(sorğu)
        qaytar veb.json(tapşırıqlar)
    son)

    s.göndər("/api/tapşırıq", funksiya(sorğu)
        dəyişən v = sorğu.json()
        dəyişən t = yeni Tapşırıq()
        t.id = növbətiId
        t.mətn = v["mətn"]
        növbətiId += 1
        tapşırıqlar.əlavə(t)
        qaytar veb.json(t).kod(201)
    son)

    s.sil("/api/tapşırıq/:id", funksiya(sorğu)
        dəyişən id = tamƏt(sorğu.parametr("id"))
        tapşırıqlar = tapşırıqlar.filtr((t) => t.id != id)
        qaytar veb.boş(204)
    son)

    yaz("Server: http://localhost:8080")
    s.dinlə(8080)
son
```
