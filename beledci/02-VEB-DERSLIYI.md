# Alqor Bələdçisi — 3. Veb Dərsliyi

> Bu dərslikdə sıfırdan tam işlək veb tətbiq quracağıq: **Qeyd Dəftəri**.
> Verilənlər bazası, autentifikasiya, API və canlı interfeys — hamısı Alqor-da.

---

## 3.1 Layihəni yaratmaq

```bash
alqor yeni qeyd-dəftəri --şablon veb
cd qeyd-dəftəri
alqor veb inkişaf
```

Brauzerdə `http://localhost:8080` açılır və **kod dəyişdikcə avtomatik yenilənir**.

### Yaranan quruluş
```
qeyd-dəftəri/
├── layihe.alqor
├── mənbə/
│   ├── server.alqor       ← server kodu
│   ├── müştəri.alqor      ← brauzer kodu
│   └── ortaq/
│       └── model.alqor    ← hər ikisində işləyən kod
├── şablon/
│   └── əsas.alqorhtml
└── statik/
    └── üslub.css
```

---

## 3.2 İlk server

`mənbə/server.alqor`:
```alqor
gətir veb

funksiya əsas()
    dəyişən s = yeni veb.Server()

    s.al("/", funksiya(sorğu)
        qaytar veb.mətn("Salam, dünya!")
    son)

    yaz("Server: http://localhost:8080")
    s.dinlə(8080)
son
```

```bash
alqor işlət
```

---

## 3.3 HTML qaytarmaq

```alqor
s.al("/", funksiya(sorğu)
    qaytar veb.html("""
        <!DOCTYPE html>
        <html lang="az">
        <head><meta charset="UTF-8"><title>Qeyd Dəftəri</title></head>
        <body>
            <h1>Qeyd Dəftərim</h1>
        </body>
        </html>
    """)
son)
```

---

## 3.4 Şablonlar

`şablon/əsas.alqorhtml`:
```html
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ başlıq }}</title>
    <link rel="stylesheet" href="/statik/üslub.css">
</head>
<body>
    <h1>{{ başlıq }}</h1>

    <form method="GÖNDƏR" action="/qeyd">
        <input name="mətn" placeholder="Yeni qeyd..." required>
        <button type="submit">Əlavə et</button>
    </form>

    <ul class="qeydlər">
    {% hər q üçün qeydlər içində %}
        <li>
            <span>{{ q.mətn }}</span>
            <small>{{ q.tarix | format("DD.MM.YYYY HH:mm") }}</small>
            <a href="/sil/{{ q.id }}">Sil</a>
        </li>
    {% yoxsa %}
        <li class="boş">Hələ qeyd yoxdur</li>
    {% son %}
    </ul>
</body>
</html>
```

`server.alqor`:
```alqor
s.al("/", funksiya(sorğu)
    qaytar veb.şablon("əsas.alqorhtml", {
        "başlıq": "Qeyd Dəftərim",
        "qeydlər": qeydlər
    })
son)
```

> **Təhlükəsizlik:** `{{ }}` içindəki hər şey avtomatik HTML-qaçış edilir.
> Yəni istifadəçi `<script>` yazsa belə, kod kimi işləməyəcək.

---

## 3.5 Model və verilənlər bazası

`mənbə/ortaq/model.alqor`:
```alqor
ixrac et sinif Qeyd
    xassə id: tam = 0
    xassə mətn: mətn = ""
    xassə tarix: Zaman = vaxt.indi()
    xassə bitib: məntiq = yanlış

    metod qısaMətn() -> mətn
        əgər özü.mətn.uzunluq() > 50 onda
            qaytar özü.mətn.dilim(0, 50) + "..."
        son
        qaytar özü.mətn
    son
son

ixrac et funksiya yoxla(q: Qeyd) -> siyahı[mətn]
    dəyişən xətalar: siyahı[mətn] = []
    əgər q.mətn.kəs() == "" onda
        xətalar.əlavə("Qeyd boş ola bilməz")
    son
    əgər q.mətn.uzunluq() > 1000 onda
        xətalar.əlavə("Qeyd 1000 simvoldan uzun ola bilməz")
    son
    qaytar xətalar
son
```

> Bu fayl **həm serverdə, həm brauzerdə** işləyir. Validasiya bir dəfə yazılır,
> iki yerdə işləyir: brauzerdə dərhal cavab üçün, serverdə təhlükəsizlik üçün.

### SQLite ilə
```alqor
gətir verilənlər

dəyişən b: verilənlər.Bağlantı

asinxron funksiya bazanıHazırla()
    b = gözlə verilənlər.bağlan("sqlite://./qeydlər.db")
    gözlə b.icra("""
        CREATE TABLE IF NOT EXISTS qeydlər (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mətn TEXT NOT NULL,
            tarix TEXT NOT NULL,
            bitib INTEGER DEFAULT 0
        )
    """)
son

asinxron funksiya qeydləriAl() -> siyahı[Qeyd]
    dəyişən sətirlər = gözlə b.sorğu("SELECT * FROM qeydlər ORDER BY tarix DESC")
    qaytar sətirlər.çevir(funksiya(s)
        dəyişən q = yeni Qeyd()
        q.id = s["id"]
        q.mətn = s["mətn"]
        q.tarix = vaxt.ISO(s["tarix"])
        q.bitib = s["bitib"] == 1
        qaytar q
    son)
son

asinxron funksiya qeydƏlavə(mətn: mətn)
    gözlə b.icra(
        "INSERT INTO qeydlər (mətn, tarix) VALUES ($1, $2)",
        mətn, vaxt.indi().ISO()
    )
son
```

> **Diqqət:** Həmişə `$1`, `$2` parametrləri istifadə edin.
> Mətni birbaşa SQL-ə birləşdirmək SQL inyeksiyasına yol açır —
> `alqorlint` bunu xəta kimi göstərir.

---

## 3.6 Forma qəbul etmək

```alqor
s.göndər("/qeyd", asinxron funksiya(sorğu)
    dəyişən f = sorğu.form()
    dəyişən q = yeni Qeyd()
    q.mətn = f["mətn"] ?? ""

    dəyişən xətalar = model.yoxla(q)
    əgər deyil boşdur(xətalar) onda
        qaytar veb.şablon("əsas.alqorhtml", {
            "başlıq": "Qeyd Dəftərim",
            "qeydlər": gözlə qeydləriAl(),
            "xətalar": xətalar
        }).kod(400)
    son

    gözlə qeydƏlavə(q.mətn)
    qaytar veb.yönləndir("/")
son)
```

---

## 3.7 REST API

```alqor
s.qrup("/api", funksiya(q)

    q.al("/qeyd", asinxron funksiya(sorğu)
        qaytar veb.json(gözlə qeydləriAl())
    son)

    q.al("/qeyd/:id", asinxron funksiya(sorğu)
        dəyişən id = tamƏt(sorğu.parametr("id"))
        dəyişən q = gözlə qeydTap(id)
        əgər q boşdur onda
            qaytar veb.json({"xəta": "Tapılmadı"}).kod(404)
        son
        qaytar veb.json(q)
    son)

    q.göndər("/qeyd", asinxron funksiya(sorğu)
        dəyişən v = sorğu.json()
        dəyişən q = yeni Qeyd()
        q.mətn = v["mətn"] ?? ""

        dəyişən xətalar = model.yoxla(q)
        əgər deyil boşdur(xətalar) onda
            qaytar veb.json({"xətalar": xətalar}).kod(422)
        son

        gözlə qeydƏlavə(q.mətn)
        qaytar veb.json(q).kod(201)
    son)

    q.sil("/qeyd/:id", asinxron funksiya(sorğu)
        gözlə qeydSil(tamƏt(sorğu.parametr("id")))
        qaytar veb.boş(204)
    son)
son)
```

Yoxlama:
```bash
curl http://localhost:8080/api/qeyd
curl -X POST http://localhost:8080/api/qeyd -d '{"mətn":"Süd al"}'
```

---

## 3.8 Ara proqramlar

```alqor
funksiya əsas()
    dəyişən s = yeni veb.Server()

    s.ara(veb.jurnal())                       // sorğuları logla
    s.ara(veb.sıxma())                        // gzip
    s.ara(veb.CORS(mənbələr: ["*"]))
    s.ara(veb.sürətLimiti(100, "1dəq"))       // dəqiqədə 100 sorğu
    s.ara(veb.təhlükəsizlikBaşlıqları())
    s.ara(veb.sessiya(gizli: sistem.mühit("SESSIYA_AÇARI")))
    s.ara(veb.CSRF())

    s.statik("/statik", "statik/")

    // ... marşrutlar

    s.dinlə(8080)
son
```

### Öz ara proqramınız
```alqor
s.ara(asinxron funksiya(sorğu, növbəti)
    dəyişən başlanğıc = vaxt.möhürMs()
    dəyişən cavab = gözlə növbəti(sorğu)
    dəyişən müddət = vaxt.möhürMs() - başlanğıc
    jurnal.info("{sorğu.metod()} {sorğu.yol()} — {cavab.kod()} — {müddət}ms")
    qaytar cavab
son)
```

---

## 3.9 Autentifikasiya

```alqor
gətir veb.auth
gətir şifrə

s.göndər("/qeydiyyat", asinxron funksiya(sorğu)
    dəyişən f = sorğu.form()

    əgər gözlə istifadəçiVar(f["email"]) onda
        qaytar veb.json({"xəta": "Bu email artıq qeydiyyatdadır"}).kod(409)
    son

    gözlə b.icra(
        "INSERT INTO istifadəçilər (email, parol_heş) VALUES ($1, $2)",
        f["email"], şifrə.parolHeş(f["parol"])
    )
    qaytar veb.yönləndir("/giriş")
son)

s.göndər("/giriş", asinxron funksiya(sorğu)
    dəyişən f = sorğu.form()
    dəyişən i = gözlə istifadəçiTap(f["email"])

    əgər i boşdur və ya deyil şifrə.parolYoxla(f["parol"], i.parolHeş) onda
        qaytar veb.şablon("giriş.alqorhtml", {
            "xəta": "Email və ya parol yanlışdır"
        }).kod(401)
    son

    sorğu.sessiya().qoy("istifadəçiId", i.id)
    qaytar veb.yönləndir("/")
son)

s.göndər("/çıxış", funksiya(sorğu)
    sorğu.sessiya().təmizlə()
    qaytar veb.yönləndir("/giriş")
son)

// Qoruyucu
funksiya girişTələbOlunur(sorğu, növbəti)
    əgər sorğu.sessiya().al("istifadəçiId") boşdur onda
        qaytar veb.yönləndir("/giriş")
    son
    qaytar növbəti(sorğu)
son

s.al("/panel", [girişTələbOlunur], panelSəhifəsi)
```

> Parollar heç vaxt düz mətnlə saxlanmır. `şifrə.parolHeş()` Argon2id istifadə edir.

---

## 3.10 Brauzer tərəfi (interaktiv interfeys)

`mənbə/müştəri.alqor`:
```alqor
gətir veb.ön
gətir "./ortaq/model.alqor" kimi model

komponent QeydSiyahısı
    vəziyyət qeydlər: siyahı[model.Qeyd] = []
    vəziyyət yeniMətn: mətn = ""
    vəziyyət yüklənir: məntiq = doğru
    vəziyyət xəta: mətn? = boş

    asinxron metod quraşdırıldı()
        gözlə özü.yüklə()
    son

    asinxron metod yüklə()
        özü.yüklənir = doğru
        cəhd et
            dəyişən c = gözlə http.al("/api/qeyd")
            özü.qeydlər = c.json()
        tut (x: Xəta)
            özü.xəta = "Qeydlər yüklənmədi"
        nəhayət
            özü.yüklənir = yanlış
        son
    son

    asinxron metod əlavəEt()
        dəyişən q = yeni model.Qeyd()
        q.mətn = özü.yeniMətn

        dəyişən xətalar = model.yoxla(q)      // brauzerdə dərhal yoxlama
        əgər deyil boşdur(xətalar) onda
            özü.xəta = xətalar[0]
            qaytar
        son

        gözlə http.göndər("/api/qeyd", gövdə: {"mətn": özü.yeniMətn})
        özü.yeniMətn = ""
        özü.xəta = boş
        gözlə özü.yüklə()
    son

    asinxron metod sil(id: tam)
        gözlə http.sil("/api/qeyd/{id}")
        gözlə özü.yüklə()
    son

    göstər()
        qaytar <div sinif="qeyd-siyahı">
            <h1>Qeyd Dəftərim</h1>

            {əgər özü.xəta boş deyil onda
                <div sinif="xəta">{özü.xəta}</div>
            son}

            <div sinif="forma">
                <input
                    dəyər={özü.yeniMətn}
                    dəyişdi={(d) => özü.yeniMətn = d}
                    yerTutucu="Yeni qeyd..."
                    düyməBasıldı={(h) => əgər h.açar == "Enter" onda özü.əlavəEt() son} />
                <button klik={özü.əlavəEt}>Əlavə et</button>
            </div>

            {əgər özü.yüklənir onda
                <p>Yüklənir...</p>
            yoxsa
                <ul>
                    {özü.qeydlər.çevir((q) =>
                        <li açar={q.id}>
                            <span>{q.mətn}</span>
                            <button klik={() => özü.sil(q.id)}>Sil</button>
                        </li>
                    )}
                </ul>
            son}
        </div>
    son
son

ön.quraşdır(QeydSiyahısı, "#kök")
```

---

## 3.11 Real vaxt yeniləmə (WebSocket)

### Server
```alqor
s.soket("/canlı", funksiya(soket)
    soket.hadisə("qoşuldu", funksiya()
        soket.otağaQoşul("qeydlər")
    son)
son)

// Qeyd əlavə olunanda hamıya bildir
asinxron funksiya qeydƏlavə(mətn: mətn)
    gözlə b.icra("INSERT INTO qeydlər (mətn, tarix) VALUES ($1, $2)", mətn, ...)
    s.otağaYayımla("qeydlər", {"hadisə": "yeni", "mətn": mətn})
son
```

### Brauzer
```alqor
dəyişən soket = veb.soketBağlan("/canlı")
soket.hadisə("mesaj", funksiya(m)
    özü.yüklə()                 // yeni qeyd gəldi, siyahını yenilə
son)
```

---

## 3.12 Testlər

`sınaq/api_sınaq.alqor`:
```alqor
gətir test
gətir veb.sınaq

@sınaq
asinxron funksiya qeydSiyahısıBoşdur()
    dəyişən s = veb.sınaq.server(əsasServer())
    dəyişən c = gözlə s.al("/api/qeyd")

    test.bərabər(c.kod(), 200)
    test.bərabər(c.json(), [])
son

@sınaq
asinxron funksiya qeydƏlavəEdilir()
    dəyişən s = veb.sınaq.server(əsasServer())
    dəyişən c = gözlə s.göndər("/api/qeyd", gövdə: {"mətn": "Test"})

    test.bərabər(c.kod(), 201)
    test.bərabər(c.json()["mətn"], "Test")
son

@sınaq
asinxron funksiya boşQeydRəddEdilir()
    dəyişən s = veb.sınaq.server(əsasServer())
    dəyişən c = gözlə s.göndər("/api/qeyd", gövdə: {"mətn": ""})

    test.bərabər(c.kod(), 422)
son
```

```bash
alqortest --örtük
```

---

## 3.13 Buraxılış və yerləşdirmə

```bash
alqor qur --hədəf veb --buraxılış
```

Nəticə:
```
qurma/veb/
├── server                 # 8.2 MB statik Linux binarı
├── public/
│   ├── index.html
│   ├── tətbiq.js          # 42 KB (kiçildilmiş)
│   └── statik/
└── Dockerfile
```

### Serverə atmaq
```bash
scp -r qurma/veb/ istifadəçi@server:/opt/qeyd-dəftəri/
ssh istifadəçi@server
cd /opt/qeyd-dəftəri && ./server
```

### systemd xidməti
```bash
alqor yerləşdir --növ systemd
```
Yaranır: `/etc/systemd/system/qeyd-dəftəri.service`
```bash
sudo systemctl enable --now qeyd-dəftəri
```

### Docker
```bash
alqor yerləşdir --növ docker
docker run -p 8080:8080 qeyd-dəftəri:1.0.0
```

### Statik hostinq (yalnız ön tərəf)
```bash
alqor qur --hədəf veb --yalnız-ön
# qurma/veb/public/ qovluğunu Netlify, Vercel və ya GitHub Pages-ə atın
```

> **Vacib:** Serverin Alqor bilməsinə **ehtiyac yoxdur**. Çıxış adi ELF binarı
> və adi HTML/JS fayllarıdır. İstənilən hostinq, istənilən server işlədir.

---

## 3.14 Performans məsləhətləri

| Məsləhət | Niyə |
|---|---|
| `alqor qur --buraxılış` | Optimallaşdırma + kiçiltmə |
| `s.ara(veb.sıxma())` | gzip/brotli |
| `s.ara(veb.keş())` | Statik fayllar üçün keş başlıqları |
| Verilənlər bazasında indeks | Sorğu sürəti |
| `paralel.hamısı()` | Müstəqil sorğuları paralel işlət |
| `@yaddaşla` | Təkrarlanan hesablamaları keşlə |
| WASM backend | Ağır hesablamalar üçün |

---

**Növbəti:** [4. Desktop Dərsliyi](03-DESKTOP-DERSLIYI.md)
