# Alqor Bələdçisi — 3. Veb Dərsliyi

> Bu dərslikdə **Kitab rəfi** saytını qururuq: səhifələr və şablonlar,
> form, giriş/çıxış, JSON API, statik fayllar və brauzerdə canlı
> axtarış.
>
> Yekun proqram: [`numuneler/10-kitab-refi/`](../numuneler/10-kitab-refi/esas.alq).
> Bu səhifədəki hər tam proqram və şablon avtomatik sınaqlarla
> yoxlanılır.

**Lazım olan:** Python 3.12+. Veb server Alqor-un içindədir —
əlavə heç nə quraşdırılmır.

---

## 3.1 İlk server

```alqor
// addım 1 — salam
gətir veb

funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.al("/", (sorğu) => veb.mətn("Salam, dünya!"))
    s.dinlə(8080)
son
```

```powershell
python alqorc.py işlət salam.alq
```

Brauzerdə `http://127.0.0.1:8080` açın. Dayandırmaq: `Ctrl+C`.

| Sətir | Nə edir |
|---|---|
| `yeni veb.Server()` | server yaradır |
| `s.al("/", …)` | `GET /` sorğusu gələndə funksiyanı çağırır |
| `veb.mətn(…)` | cavab: düz mətn |
| `s.dinlə(8080)` | portu açır və sorğuları gözləyir |

Metodlar HTTP metodlarına uyğundur: `al` (GET), `göndər` (POST),
`yenilə` (PUT), `yamaq` (PATCH), `sil` (DELETE), `hamısı` (istənilən).

---

## 3.2 Marşrutlar və parametrlər

```alqor
// addım 2 — parametrlər
gətir veb

funksiya əsas()
    dəyişən s = yeni veb.Server()

    // /salam/Aysel → "Salam, Aysel!"
    s.al("/salam/:ad", (sorğu) =>
        veb.mətn("Salam, {sorğu.parametr("ad")}!"))

    // /axtar?söz=kür&səhifə=2
    s.al("/axtar", funksiya(sorğu)
        dəyişən söz = sorğu.sorğuParametr("söz", "")
        dəyişən səhifə = tamƏt(sorğu.sorğuParametr("səhifə", "1"), 1)
        qaytar veb.json({"söz": söz, "səhifə": səhifə})
    son)

    s.dinlə(8080)
son
```

| Naxış | Uyğun gəlir | Parametr |
|---|---|---|
| `/kitab/:nömrə` | `/kitab/7` | `nömrə` = `"7"` |
| `/səhifə/:ad?` | `/səhifə` və `/səhifə/haqqında` | ixtiyari |
| `/fayl/*yol` | `/fayl/a/b/c.txt` | `yol` = `"a/b/c.txt"` |

Parametr həmişə **mətndir** — ədəd lazımdırsa `tamƏt(…, standart)`.

Cavab növləri:

| Funksiya | Cavab |
|---|---|
| `veb.mətn(m)` | `text/plain` |
| `veb.html(h)` | `text/html` — mətn və ya JSX |
| `veb.json(d)` | `application/json` |
| `veb.şablon(fayl, verilənlər)` | şablondan HTML (§ 3.3) |
| `veb.yönləndir(ünvan)` | 302 |
| `veb.xəta(kod, mesaj)` | xəta səhifəsi |
| `veb.boş()` | 204 |
| `veb.fayl(yol)` / `veb.yüklə(yol)` | fayl / endirmə |

Hər cavabın kodu dəyişdirilə bilər: `veb.json(…).kod(201)`,
başlıq əlavə edilə bilər: `.başlıq("X-Ad", "dəyər")`.

---

## 3.3 Şablonlar: `.alqorhtml`

HTML-i koda yazmaq əvəzinə şablon faylı işlədək. Layihənin quruluşu:

```
kitab-rəfi/
├── esas.alq
├── sablonlar/
│   ├── esas.alqorhtml       ← ümumi çərçivə
│   └── siyahi.alqorhtml     ← kitab siyahısı
└── statik/
    └── üslub.css
```

**Ümumi çərçivə** — hər səhifədə təkrarlanan hissə:

```alqorhtml
<!-- fayl: sablonlar/esas.alqorhtml -->
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <title>{% blok başlıq %}Kitab rəfi{% son %}</title>
    <link rel="stylesheet" href="/statik/üslub.css">
</head>
<body>
    <nav><a href="/">Kitab rəfi</a></nav>
    <main>{% blok məzmun %}{% son %}</main>
    <footer>{{ kitabSayı }} kitab</footer>
</body>
</html>
```

**Səhifə** — çərçivəni genişləndirir və `məzmun` blokunu doldurur:

```alqorhtml
<!-- fayl: sablonlar/siyahi.alqorhtml -->
{% genişlət "esas.alqorhtml" %}

{% blok məzmun %}
<h1>Kitablar</h1>
<ul>
    {% hər k üçün kitablar içində %}
        <li><a href="/kitab/{{ k.nömrə }}">{{ k.ad }}</a>
            — {{ k.müəllif }}, {{ k.il }}</li>
    {% yoxsa %}
        <li>Rəf boşdur.</li>
    {% son %}
</ul>
{% son %}
```

**Kod:**

```alqor
// addım 3 — şablon
gətir veb

sinif Kitab
    qurucu(açıq xassə nömrə: tam, açıq xassə ad: mətn,
           açıq xassə müəllif: mətn, açıq xassə il: tam)
son

dəyişən kitablar = [
    yeni Kitab(1, "Əli və Nino", "Qurban Səid", 1937),
    yeni Kitab(2, "Dəli Kür", "İsmayıl Şıxlı", 1967)
]

funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.şablonQovluğu("sablonlar")
    s.al("/", (sorğu) => veb.şablon("siyahi.alqorhtml", {
        "kitablar": kitablar,
        "kitabSayı": uzunluq(kitablar)
    }))
    s.dinlə(8080)
son
```

Şablon sintaksisi:

| Yazılış | Mənası |
|---|---|
| `{{ ifadə }}` | dəyər — **HTML qaçışı avtomatikdir** (XSS-dən qoruyur) |
| `{{ ifadə \| filtr }}` | filtrlə: `böyüyə`, `kiçiyə`, `kəs(20)`, `uzunluq`, `pul`, `standart("—")`, `format`… |
| `{{ ifadə \| xam }}` | qaçışsız — yalnız etibar etdiyiniz HTML üçün |
| `{% əgər şərt %} … {% yoxsa %} … {% son %}` | şərt |
| `{% hər x üçün s içində %} … {% yoxsa %} … {% son %}` | dövr; `yoxsa` — siyahı boşdursa |
| `{% genişlət "f" %}` + `{% blok ad %} … {% son %}` | miras |
| `{% daxilEt "f" %}` | başqa şablonu daxil edir |
| `{# şərh #}` | şərh |

`{{ }}` daxilindəki ifadə **həqiqi Alqor ifadəsidir**: `{{ k.ad.böyüyə() }}`,
`{{ uzunluq(kitablar) > 0 }}`. Lüğətin açarı nöqtə ilə yox, `["ad"]` və
ya `.al("ad", "")` ilə alınır.

Dövr daxilində `_indeks`, `_sayı`, `_ilkdir`, `_sondur` dəyişənləri
əlçatandır.

---

## 3.4 Statik fayllar

```alqor
// parça
s.statik("/statik", "statik")
```

`/statik/üslub.css` → `statik/üslub.css` faylı. MIME tipi avtomatik
təyin olunur. `../` ilə qovluqdan çıxmaq cəhdləri rədd edilir.

Yollar (`"sablonlar"`, `"statik"`) **proqram faylının qovluğuna**
nisbətəndir — proqramı hansı qovluqdan işə salmağınızdan asılı deyil.

---

## 3.5 Form qəbul etmək

```alqorhtml
<!-- fayl: sablonlar/yeni.alqorhtml -->
{% genişlət "esas.alqorhtml" %}

{% blok məzmun %}
<h1>Yeni kitab</h1>
{% əgər xətalar %}
    <ul class="xətalar">
        {% hər x üçün xətalar içində %}<li>{{ x }}</li>{% son %}
    </ul>
{% son %}
<form method="post" action="/yeni">
    <label>Ad <input name="ad" value="{{ forma.al("ad", "") }}"></label>
    <label>Müəllif <input name="müəllif" value="{{ forma.al("müəllif", "") }}"></label>
    <label>İl <input name="il" value="{{ forma.al("il", "") }}"></label>
    <button>Əlavə et</button>
</form>
{% son %}
```

```alqor
// parça
funksiya yoxlaKitab(d: lüğət[mətn, istənilən]) -> siyahı[mətn]
    dəyişən xətalar: siyahı[mətn] = []
    əgər mətnƏt(d.al("ad", "")).kəs() == "" onda
        xətalar.əlavə("Ad boş ola bilməz")
    son
    dəyişən il = tamƏt(mətnƏt(d.al("il", "")), -1)
    əgər il < 0 və ya il > 2100 onda
        xətalar.əlavə("İl 0 ilə 2100 arasında ədəd olmalıdır")
    son
    qaytar xətalar
son

// serverQur() içində:
s.al("/yeni", (sorğu) => veb.şablon("yeni.alqorhtml",
    {"forma": {}, "xətalar": [], "kitabSayı": uzunluq(kitablar)}))

s.göndər("/yeni", funksiya(sorğu)
    dəyişən f = sorğu.form()
    dəyişən xətalar = yoxlaKitab(f)
    əgər uzunluq(xətalar) > 0 onda
        // Form yenidən göstərilir — yazılanlar itmir
        qaytar veb.şablon("yeni.alqorhtml", {"forma": f,
            "xətalar": xətalar, "kitabSayı": uzunluq(kitablar)}).kod(422)
    son
    dəyişən k = yeni Kitab(uzunluq(kitablar) + 1, f["ad"],
                           f["müəllif"], tamƏt(f["il"], 0))
    kitablar = kitablar + [k]
    qaytar veb.yönləndir("/kitab/{k.nömrə}")
son)
```

Üç qayda:

1. **Uğurlu POST-dan sonra yönləndirin** (`veb.yönləndir`). Yoxsa
   istifadəçi səhifəni yeniləyəndə form ikinci dəfə göndərilir.
2. **Xəta olanda formu yazılanlarla qaytarın** və 422 kodu verin.
3. **Brauzerə güvənməyin** — yoxlamanı həmişə serverdə edin.

`sorğu.form()` — `application/x-www-form-urlencoded` və
`multipart/form-data` gövdəsini lüğətə çevirir.

---

## 3.6 Sessiya: giriş və çıxış

Sessiya — bir brauzerə aid, sorğular arasında yadda qalan məlumat:

```alqor
// parça
s.ara(veb.sessiya())          // sessiyanı aktivləşdirir

s.göndər("/giriş", funksiya(sorğu)
    dəyişən parol = sistem.mühit("KITAB_PAROL") ?? "alqor"
    əgər sorğu.form().al("parol", "") == parol onda
        sorğu.sessiya().qoy("admin", doğru)
        qaytar veb.yönləndir("/")
    son
    qaytar veb.xəta(401, "Parol yanlışdır")
son)

s.göndər("/çıxış", funksiya(sorğu)
    sorğu.sessiya().təmizlə()
    qaytar veb.yönləndir("/")
son)

funksiya adminDir(sorğu: istənilən) -> məntiq
    qaytar sorğu.sessiya().al("admin", yanlış) == doğru
son
```

Sessiya metodları: `al(ad, standart)`, `qoy(ad, dəyər)`, `sil(ad)`,
`ehtiva(ad)`, `təmizlə()`. Məlumat serverin yaddaşındadır, brauzerdə
yalnız təsadüfi açar (`HttpOnly` kuki) saxlanılır.

> **Parolu koda yazmayın.** Mühit dəyişənindən oxuyun:
> `$env:KITAB_PAROL = "…"` (PowerShell) və ya `export KITAB_PAROL=…`.

---

## 3.7 JSON API

```alqor
// parça — serverQur() içində
s.qrup("/api", funksiya(q)
    q.al("/kitablar", (sorğu) => veb.json(
        kitablar.çevir((k) => {"nömrə": k.nömrə, "ad": k.ad})))

    q.al("/kitablar/:nömrə", funksiya(sorğu)
        dəyişən n = tamƏt(sorğu.parametr("nömrə"), 0)
        hər k üçün kitablar içində
            əgər k.nömrə == n onda
                qaytar veb.json({"nömrə": k.nömrə, "ad": k.ad})
            son
        son
        qaytar veb.json({"xəta": "tapılmadı"}).kod(404)
    son)

    q.göndər("/kitablar", yalnızAdmin, funksiya(sorğu)
        dəyişən d = sorğu.json()
        dəyişən xətalar = yoxlaKitab(d)
        əgər uzunluq(xətalar) > 0 onda
            qaytar veb.json({"xətalar": xətalar}).kod(422)
        son
        // … əlavə et …
        qaytar veb.json({"nömrə": 3}).kod(201)
    son)
son)
```

`s.qrup(prefiks, f)` marşrutları bir prefiks altında toplayır. Status
kodları REST qaydası ilə: 200 oxundu · 201 yaradıldı · 204 silindi,
gövdə yoxdur · 401 giriş lazımdır · 404 tapılmadı · 422 verilənlər
yanlışdır.

---

## 3.8 Ara proqramlar

Ara proqram hər sorğudan əvvəl (və sonra) işləyən funksiyadır:

```alqor
// parça
s.ara(veb.jurnal())                     // hər sorğunu konsola yazır
s.ara(veb.təhlükəsizlikBaşlıqları())    // X-Frame-Options və s.
s.ara(veb.CORS(["https://sayt.az"]))    // başqa domendən API
s.ara(veb.sıxma())                      // gzip
s.ara(veb.sürətLimiti(100, "1dəq"))     // IP başına limit

// Öz ara proqramınız: (sorğu, növbəti) → cavab
dəyişən yalnızAdmin = funksiya(sorğu, növbəti)
    əgər deyil adminDir(sorğu) onda
        qaytar veb.json({"xəta": "giriş tələb olunur"}).kod(401)
    son
    qaytar növbəti(sorğu)               // zəncirdə növbəti
son
```

`s.ara(f)` hər marşruta, marşruta ikinci arqument kimi verilən isə
yalnız ona tətbiq olunur: `q.göndər("/kitablar", yalnızAdmin, f)`.

---

## 3.9 Canlı səhifə: komponent + vidjet

Axtarış sahəsinə yazdıqca nəticələrin dəyişməsini istəyirik — JavaScript
yazmadan. Desktop dərsliyindəki kimi komponent yazırıq və serverə
qoşuruq:

```alqor
// addım 4 — canlı axtarış
gətir veb
gətir vidjet

dəyişən kitablar = [
    {"ad": "Əli və Nino", "müəllif": "Qurban Səid"},
    {"ad": "Dəli Kür", "müəllif": "İsmayıl Şıxlı"},
    {"ad": "Ölülər", "müəllif": "Cəlil Məmmədquluzadə"}
]

komponent Axtarış
    vəziyyət söz: mətn = ""

    metod yazıldı(dəyər: mətn)
        özü.söz = dəyər
    son

    göstər()
        dəyişən s = özü.söz.kiçiyə()
        qaytar vidjet.sütun(boşluq: 16, məzmun: [
            vidjet.başlıq(mətn: "Axtarış"),
            vidjet.axtarış(ad: "söz", dəyər: özü.söz,
                           yazıldı: özü.yazıldı),
            vidjet.cədvəl(
                sütunlar: [["ad", "Ad"], ["müəllif", "Müəllif"]],
                sətirlər: kitablar.filtr((k) =>
                    s içindədir mətnƏt(k["ad"]).kiçiyə()),
                boşMətn: "Heç nə tapılmadı")
        ])
    son
son

funksiya əsas()
    dəyişən s = yeni veb.Server()
    s.komponent("/axtar", Axtarış, başlıq: "Axtarış")
    s.dinlə(8080)
son
```

Necə işləyir: Alqor səhifəni HTML kimi verir və kiçik bir skript qoşur.
Hər hərfdə skript hadisəni serverə göndərir, serverdə `yazıldı`
işləyir, `göstər()` yeni HTML qaytarır, skript isə səhifəni
**yamaqla** yeniləyir — sahədəki fokus və mətn itmir. Hər brauzer öz
`Axtarış` nümunəsini alır.

Hadisələr başqa saytlardan göndərilə bilməz (`Origin` yoxlanılır,
kuki `SameSite=Strict`). Ətraflı: spesifikasiya § 14.2.2.

---

## 3.10 Sınaq yazmaq

Port açmadan sorğu göndərmək olar:

```alqor
// parça
funksiya yoxla()
    dəyişən m = veb.sınaq.server(serverQur())

    dəyişən c = m.al("/")
    iddia c.vəziyyət() == 200
    iddia "Dəli Kür" içindədir c.mətnƏt()

    // Form göndərmək
    dəyişən FORM = {"Content-Type": "application/x-www-form-urlencoded"}
    c = m.göndər("/giriş", "parol=alqor", FORM)
    iddia c.vəziyyət() == 302

    // JSON göndərmək — lüğət avtomatik JSON olur
    c = m.göndər("/api/kitablar", {"ad": "Leyli və Məcnun", "il": 1536})
    iddia c.vəziyyət() == 201
    iddia c.json()["nömrə"] > 0
son
```

Sınaq müştərisi kukiləri yadda saxlayır — giriş etdikdən sonrakı
sorğular admin kimi gedir. Metodlar: `al`, `göndər`, `yenilə`,
`yamaq`, `sil`; cavab: `vəziyyət()`, `mətnƏt()`, `json()`,
`başlıq(ad)`.

---

## 3.11 Xətalar

```alqor
// parça
s.tapılmadı((sorğu) => veb.html("<h1>Səhifə tapılmadı</h1>").kod(404))

s.xətaİdarəedicisi(funksiya(sorğu, x)
    jurnal.xəta(x.mesaj)
    qaytar veb.html("<h1>Bağışlayın, xəta baş verdi</h1>").kod(500)
son)
```

İnkişaf zamanı Alqor xəta mesajını və yerini səhifədə göstərir.

---

## 3.12 Yekun proqram və işə salma

Bütün hissələr bir yerdə: [`numuneler/10-kitab-refi/esas.alq`](../numuneler/10-kitab-refi/esas.alq).

```powershell
cd alqor\alqorc
python alqorc.py işlət ..\numuneler\10-kitab-refi\esas.alq            # :8083
python alqorc.py işlət ..\numuneler\10-kitab-refi\esas.alq -- sınaq   # 16 yoxlama
```

Windows-da: `.\Brauzerde-ac.cmd 10`.

**Bir əmrlə internetə** — layihə qovluğunda:

```powershell
alqor yerləşdir          # qurma\yerləşdir\: tetbiq.pyz + Dockerfile + YERLESDIR.md
```

Paket Render, Fly.io və ya Docker olan istənilən serverdə işləyir.
`s.dinlə(8080)` kodda qalır: platforma `PORT` mühit dəyişənini verəndə
server həmin portda açılır, `ALQOR_HOST=0.0.0.0` isə onu xaricə açır
(Dockerfile ikisini də özü qurur). Addımlar: oflayn sənədlərdə
«Vebə yerləşdirmə» səhifəsi.

**Linux serverdə daimi işlətmək** (systemd):

```ini
# /etc/systemd/system/kitab-refi.service
[Unit]
Description=Kitab rəfi
After=network.target

[Service]
WorkingDirectory=/srv/alqor/alqorc
ExecStart=/usr/bin/python3 alqorc.py işlət /srv/kitab-refi/esas.alq
Environment=PYTHONIOENCODING=utf-8
Environment=KITAB_PAROL=…
Restart=on-failure
User=www-data

[Install]
WantedBy=multi-user.target
```

İnternetə açarkən qarşısına HTTPS üçün nginx və ya Caddy qoyun —
Alqor serveri `127.0.0.1`-də qalsın.

---

## 3.13 Tez-tez rast gəlinən xətalar

| Xəta | Səbəb | Həll |
|---|---|---|
| `forma.ad` — `lüğət` tipində `ad` üzvü yoxdur | lüğət açarı nöqtə ilə alınmır | `forma.al("ad", "")` |
| `"... şablonu tapılmadı"` | şablon qovluğu təyin edilməyib | `s.şablonQovluğu("sablonlar")` |
| Form ikinci dəfə göndərilir | POST-dan sonra HTML qaytarılıb | `veb.yönləndir(…)` |
| `{{ … }}` ayrılmadı | şablon ifadəsi Alqor sintaksisindədir | xəta mesajı fayl və sətri göstərir |
| `{:8080 dinlənilə bilmədi — Port məşğuldurmu?}` | port artıq istifadədədir | başqa port və ya `veb.boşPort()` |
| Sessiya işləmir | `veb.sessiya()` ara proqramı qoşulmayıb | `s.ara(veb.sessiya())` |

---

## 3.14 Planlaşdırılır

* `verilənlər` modulu (SQLite) — hazırda məlumat yaddaşda saxlanılır
  və ya `json.faylYaz` ilə fayla yazılır.
* WebSocket — canlı səhifələr üçün indi `s.komponent` işlədilir.
* `alqor yeni --şablon veb` — layihə skeleti.
