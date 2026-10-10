# Alqor — Bölmə 8: Modullar və Paketlər

---

## 8.1 Modul anlayışı

**Hər `.alq` faylı bir moduldur.** Modul adı fayl adından gəlir:

```
riyazi-alətlər.alq   →   modul adı: riyazi_alətlər
şəbəkə/http.alq      →   modul adı: şəbəkə.http
```

---

## 8.2 İxrac — `ixrac et`

Standart olaraq **hər şey gizlidir**. Yalnız `ixrac et` ilə işarələnən üzvlər kənardan görünür.

```alqor
// riyazi.alq

ixrac et sabit Pİ = 3.14159265358979

ixrac et funksiya kvadrat(x: onluq) -> onluq
    qaytar x * x
son

ixrac et sinif Vektor
    ...
son

funksiya daxiliKöməkçi()          // ixrac olunmur — gizli
    ...
son

// Toplu ixrac
ixrac et {kvadrat, kub, kök}

// Standart ixrac (modulun əsas elementi)
ixrac et standart funksiya hesabla() ... son

// Yenidən ixrac
ixrac et {topla, çıx} riyazi.əsasdan
ixrac et * riyazi.həndəsədən
```

---

## 8.3 İdxal — `gətir`

### Bütöv modul
```alqor
gətir riyaziyyat

yaz(riyaziyyat.Pİ)
yaz(riyaziyyat.kök(16))
```

### Ləqəblə
```alqor
gətir riyaziyyat kimi r

yaz(r.Pİ)
```

### Seçmə idxal
```alqor
gətir riyaziyyat.{Pİ, kök, qüvvət}

yaz(Pİ)
yaz(kök(16))
```

### Ləqəbli seçmə idxal
```alqor
gətir riyaziyyat.{kök kimi kvadratKök, Pİ kimi PI}
```

### Hamısını idxal (tövsiyə olunmur)
```alqor
gətir riyaziyyat.*
```

> **Niyə `riyaziyyatdan` deyil?**
> Azərbaycan dilinin təbii forması `riyaziyyatdan gətir {kök}` olardı.
> Amma `-dan` şəkilçisi söz**ə yapışır** və lekser üçün `riyaziyyatdan`
> **bir identifikator tokenidir** — şəkilçini ayırmaq mümkün deyil.
> Ayırmağa çalışsaq, `meydan`, `qazan`, `vətən` kimi adlı modullar sınar.
>
> Ona görə seçmə idxal **nöqtə-mötərizə** sintaksisi ilə yazılır:
> `gətir riyaziyyat.{kök}`. Qısa, qeyri-ikimənalı, şəkilçisiz.
> Bu, dilin aqqlütinativ təbiətinin kompilyator dizaynına birbaşa
> təsir etdiyi yerlərdən biridir.

### Standart idxal
```alqor
gətir riyazi.standart kimi hesabla   // `ixrac et standart` elementi
```

### Yerli fayldan
```alqor
gətir "./köməkçilər.alq" kimi k
gətir "../ortaq/model.alq" kimi model
gətir "./alt_qovluq/" kimi alt    // qovluğun `indeks.alq` faylı
```

### Paketdən
```alqor
gətir veb                         // standart kitabxana
gətir @şirkət/analitika           // ad fəzalı paket
gətir tarix_alətləri              // alqorhub paketi
```

### Şərti idxal
```alqor
@əgərHədəf("veb")
gətir brauzer

@əgərHədəf("desktop")
gətir pəncərə
```

### Dinamik idxal (asinxron)
```alqor
asinxron funksiya yüklə()
    dəyişən modul = gözlə gətirDinamik("./ağır-modul.alq")
    modul.işlət()
son
```

---

## 8.4 Modul daxilində `modul` bloku

Bir faylda bir neçə ad fəzası:

```alqor
// həndəsə.alq

ixrac et modul ikiÖlçülü
    ixrac et sinif Nöqtə
        xassə x: onluq
        xassə y: onluq
    son
son

ixrac et modul üçÖlçülü
    ixrac et sinif Nöqtə
        xassə x: onluq
        xassə y: onluq
        xassə z: onluq
    son
son
```

```alqor
gətir həndəsə

dəyişən a = yeni həndəsə.ikiÖlçülü.Nöqtə()
dəyişən b = yeni həndəsə.üçÖlçülü.Nöqtə()
```

---

## 8.5 Modulun ilkinləşdirilməsi

```alqor
// verilənlər.alq

dəyişən _bağlantı: Bağlantı?

// Modul ilk dəfə idxal olunanda bir dəfə işləyir
başlanğıc
    _bağlantı = Bağlantı.aç(sistem.mühit("DB_URL"))
    jurnal.info("Verilənlər bazası bağlandı")
son

// Proqram bitəndə işləyir
bitiş
    _bağlantı?.bağla()
son
```

---

## 8.6 Dövri asılılıqlar

Alqor dövri idxalı **aşkarlayır və xəta verir** (`ALQ-M005`):

```
✖ ALQ-M005  Dövri modul asılılığı
   a.alq → b.alq → c.alq → a.alq

   = kömək: ortaq hissəni ayrıca modula çıxarın
```

Həlli: interfeysi ayrıca modula çıxarmaq, və ya `gətirDinamik()` istifadə etmək.

---

## 8.7 Paket quruluşu

```
mənim-layihəm/
├── layihe.alq              # paket manifesti
├── alqor.kilid               # dəqiq versiya kilidi (avtomatik)
├── mənbə/
│   ├── əsas.alq            # giriş nöqtəsi
│   ├── model/
│   │   ├── indeks.alq      # `gətir ./model` bunu yükləyir
│   │   ├── istifadəçi.alq
│   │   └── sifariş.alq
│   └── xidmət/
│       └── auth.alq
├── sınaq/
│   ├── istifadəçi_sınaq.alq
│   └── auth_sınaq.alq
├── statik/                   # veb üçün statik fayllar
│   ├── üslub.css
│   └── şəkil/
├── sənəd/
├── paketlər/                 # asılılıqlar (alqorpm yükləyir)
└── qurma/                    # kompilyasiya nəticələri
    ├── linux-x64/
    ├── veb/
    └── paket/
```

---

## 8.8 `layihe.alq` — manifest faylı

Format TOML-a bənzəyir, amma iki fərqi var: **açarlar Azərbaycan hərfli
ola bilər** (`açarSözlər`, `sərt_boş` — TOML 1.0-da qadağandır) və
məntiqi dəyərlər `doğru`/`yanlış` yazılır (`true`/`false` da qəbul
olunur). Dəstəklənən: `[bölmə]`, `[bölmə.alt]`, mətn (`"…"`, `'…'`),
tam və onluq ədəd, massiv (çoxsətirli də), sətirdaxili cədvəl `{ … }`,
dırnaqlı açar, `#` şərhi. Xəta mesajı sətir nömrəsini göstərir.

```toml
[paket]
ad = "mənim-layihəm"
versiya = "1.0.0"
təsvir = "Nümunə Alqor layihəsi"
müəllif = ["Vüqar Qənbərov <vuqar@nümunə.az>"]
lisenziya = "MIT"
depo = "https://github.com/istifadəçi/mənim-layihəm"
sənəd = "https://vuqar.pro/hub/paket/mənim-layihəm"
açarSözlər = ["veb", "api"]
alqor_versiya = ">=1.0.0"

[qurma]
giriş = "mənbə/əsas.alq"
hədəf = ["linux-x64", "veb"]      # linux-x64 | linux-arm64 | veb | wasm | windows-x64 | macos-arm64
çıxış = "qurma/"
optimallaşdırma = 2                # 0=yox 1=sürətli 2=balanslı 3=maksimum
simvollar = yanlış                 # debaq simvolları
statik = doğru                     # statik bağlama (asılılıqsız binar)
sıxılma = doğru

[tip]
rejim = "normal"                   # sərbəst | normal | sərt
sərt_boş = doğru                   # ixtiyari tiplər məcburi yoxlanır

[icra]
stek_dərinliyi = 8192
zibil_yığıcı = "nəsilli"           # istinad | nəsilli | yoxdur
yaddaş_limiti = "512MB"

[asılılıqlar]
veb = "2.1"
verilənlər = "^3.0"                # 3.x.x
json = "~1.4.2"                    # 1.4.x
"@şirkət/analitika" = "1.0"
yerli_paket = { yol = "../yerli" }
qit_paket = { qit = "https://github.com/a/b", teq = "v1.0" }

[inkişaf_asılılıqları]
sınaq_köməkçi = "1.0"

[sınaq]
qovluq = "sınaq/"
örtük_minimum = 80

[veb]
port = 8080
host = "0.0.0.0"
statik_qovluq = "statik/"
canlı_yeniləmə = doğru

[desktop]
pəncərə_başlıq = "Mənim Proqramım"
en = 1024
hündürlük = 768
ikon = "statik/ikon.png"
dəyişdirilə_bilən = doğru

[paketləmə]
deb = { ad = "menim-layihem", asılılıqlar = ["libwebkit2gtk-4.1-0"] }
appimage = { kateqoriya = "Utility" }
flatpak = { id = "az.numune.MenimLayihem" }
docker = { baza = "debian:bookworm-slim" }

[skriptlər]
başlat = "alqor işlət mənbə/əsas.alq"
qur = "alqor qur --buraxılış"
sınaq = "alqortest"
format = "alqorfmt ."
```

---

## 8.9 `alqorpm` — paket meneceri ✅

```bash
alqorpm başlat                      # yeni layihə yarat
alqorpm əlavə veb                   # paket əlavə et
alqorpm əlavə veb@2.1               # konkret versiya
alqorpm əlavə --inkişaf sınaq_köməkçi
alqorpm sil veb                     # paket sil
alqorpm yüklə                       # layihe.alq-dakı hamısını yüklə
alqorpm yenilə                      # asılılıqları yenilə
alqorpm yenilə veb                  # bir paketi yenilə
alqorpm siyahı                      # quraşdırılmışları göstər
alqorpm ağac                        # asılılıq ağacı
alqorpm axtar json                  # alqorhub-da axtar
alqorpm məlumat veb                 # paket haqqında
alqorpm təmizlə                     # keşi təmizlə
alqorpm yoxla                       # təhlükəsizlik auditi
alqorpm yayımla                     # alqorhub-a göndər
alqorpm giriş                       # alqorhub hesabına giriş
```

Əlavə əmrlər: `alqorpm paketlə` (arxivi yayımlamadan yoxlamaq),
`alqorpm qeydiyyat` / `çıxış`, `alqorpm geri-çək ad@1.0.1` (versiya
silinmir, yeni layihələr onu seçmir), `alqorpm versiya patch|minor|major`,
`alqorpm işlət <skript>` (`[skriptlər]` bölməsi). `alqor pm …` də eynidir.

Yol və qit asılılıqları:

```bash
alqorpm əlavə yerli --yol ../yerli
alqorpm əlavə util --qit https://github.com/a/b --teq v1.0
```

**Kilid faylı** (`alqor.kilid`) hər paketin dəqiq versiyasını, mənbəyini
və arxivin SHA256 həzmini saxlayır; `alqorpm yüklə` başqa kompüterdə də
eyni versiyaları quraşdırır, həzm uyğun gəlməsə `ALQ-M010` verir.
Ziddiyyətli tələblər (`b` → `a ^1`, `c` → `a ^2`) kimin nəyi tələb
etdiyini göstərən `ALQ-M007` ilə bitir.

**Depo ünvanı**: `--depo URL` › `ALQORHUB` › `layihe.alq` `[alqorpm] depo`
› `~/.alq/ayarlar.json` › `https://vuqar.pro/hub`.

### `alqorhub` — paket deposu ✅

```bash
alqor hub --qovluq hub-məlumat --port 8790 --admin aysel
```

Rəsmi depo `https://vuqar.pro/hub` alt ünvanında işləyir. Bunun üçün
`--önək /hub`: səhifə linkləri və API-nin qaytardığı arxiv ünvanları
önəklə qurulur; reverse proxy önəki silsə də, saxlasa da işləyir.
`X-Forwarded-Proto` / `X-Forwarded-Host` başlıqları nəzərə alınır:

```bash
alqor hub --qovluq /srv/alqorhub --host 127.0.0.1 --port 8790 --önək /hub
```

```nginx
location /hub/ {
    proxy_pass http://127.0.0.1:8790/hub/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 12m;
}
```

Xarici asılılıqsız server (SQLite + fayllar): veb səhifələr (axtarış,
README, versiyalar), JSON API (`/api/paketlər`, `/api/paket/<ad>`,
`/api/paket/<ad>/<versiya>/fayl`, `PUT` ilə yayım, `geri-çək`, `sahib`,
`qeydiyyat`, `giriş`, `xəbərdarlıqlar`). Qaydalar: versiya dəyişməzdir
(təkrar yayım 409), ilk yayımlayan sahibdir, arxivdəki manifest URL ilə
üst-üstə düşməlidir, `..`/keçid/cihaz faylı rədd edilir, parollar scrypt
ilə saxlanır.

### Versiya sintaksisi

| Yazılış | Mənası |
|---|---|
| `=1.2.3` | dəqiq bu versiya |
| `1.2.3`, `1.2` | `^` kimi (uyğun yeniləmələr) |
| `^1.2.3` | `>=1.2.3 <2.0.0` (uyğun yeniləmələr) |
| `~1.2.3` | `>=1.2.3 <1.3.0` (yalnız yamaqlar) |
| `>=1.2` | bu və daha yuxarı |
| `1.2.*` | `1.2.x` |
| `*` | istənilən |
| `1.0 \|\| 2.0` | ya biri, ya digəri |

---

## 8.10 Ad həlli sırası

`gətir X` ifadəsi belə axtarır:

1. Standart kitabxana modulları (`nüvə`, `mətn`, `riyaziyyat`, ...)
2. Layihənin `mənbə/` qovluğu
3. `paketlər/` qovluğu (yerli asılılıqlar)
4. Qlobal keş: `~/.alq/paketlər/`
5. Sistem: `/usr/lib/alqor/paketlər/`

Tapılmasa: `ALQ-M001`.

---

## 8.11 Ad münaqişələri

```alqor
gətir riyaziyyat.{kök}
gətir həndəsə.{kök}              // ✖ ALQ-M006 ad münaqişəsi

// Həlli:
gətir riyaziyyat.{kök kimi riyaziKök}
gətir həndəsə.{kök kimi həndəsiKök}

// Və ya:
gətir riyaziyyat
gətir həndəsə
yaz(riyaziyyat.kök(16))
yaz(həndəsə.kök(düyün))
```

---

## 8.12 Görünüş

| Modifikator | Görünür |
|---|---|
| (yoxdur) | yalnız həmin fayl |
| `ixrac et` | idxal edən hər kəs |
| `ixrac et modul` | yalnız eyni paket daxilində |

```alqor
ixrac et modul funksiya daxiliAPI()     // paket daxilində açıq, kənarda gizli
    ...
son
```

---

## 8.13 Modul xəta kodları

| Kod | Mesaj |
|---|---|
| `ALQ-M001` | Modul tapılmadı |
| `ALQ-M002` | Modulda belə ixrac yoxdur |
| `ALQ-M003` | İxrac olunmayan üzvə müraciət |
| `ALQ-M004` | Yanlış modul yolu |
| `ALQ-M005` | Dövri modul asılılığı |
| `ALQ-M006` | İdxalda ad münaqişəsi |
| `ALQ-M007` | Versiya uyğunsuzluğu |
| `ALQ-M008` | `layihe.alq` tapılmadı |
| `ALQ-M009` | `layihe.alq` formatı pozulub |
| `ALQ-M010` | Paket imzası doğrulanmadı |
| `ALQ-M011` | ⚠ İstifadə olunmayan idxal |
| `ALQ-M012` | ⚠ `gətir *` tövsiyə olunmur |
