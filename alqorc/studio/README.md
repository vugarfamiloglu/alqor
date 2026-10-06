# Alqor Studio

> Alqor dili üçün masaüstü inkişaf mühiti. Python 3.12 standart
> kitabxanası + əl ilə yazılmış HTML/CSS/JS. Xarici asılılıq, CDN,
> npm yoxdur — tam oflayn işləyir.

```bash
cd alqorc
python alqorc.py studio                 # cari qovluq — pəncərə açılır
python alqorc.py studio ../numuneler    # istənilən layihə qovluğu
python alqorc.py studio . --port 8765   # sabit port
python alqorc.py studio . --başsız      # pəncərəsiz: ünvanı çap edir
python alqorc.py studio . --sınaq       # özünü yoxlayıb çıxır (CI)
```

Ekransız Linux-da (`DISPLAY` yoxdursa) və ya `ALQOR_BASSIZ=1` ilə
Studio avtomatik başsız rejimə keçir: ünvanı (nişanla birlikdə) çap
edir və Ctrl+C-yə qədər işləyir. Ünvanı istənilən brauzerdə açmaq olar.

---

## Əsas xüsusiyyət — iki klikdə işləyən kod

Paletdən hazır element (form sahəsi, düymə, tərəqqi çubuğu, cədvəl,
nişanlar, modal …) seçilir:

| Əməl | Nəticə |
|---|---|
| **bir klik** | `vidjet.…(…)` çağırışı kursora qoyulur (adı təkrarlanmır) |
| **iki klik** | işləməsi üçün lazım olan **bütün** kod yazılır |
| redaktora **sürükləmək** | iki klik kimi — buraxılan yerə |
| redaktorda `vidjet.ad(…)` üzərinə **iki klik** | çatışmayan vəziyyət, idarəedici və hadisə bağlantısı yazılır |
| "Fayldakı elementlər" siyahısında **iki klik** | eyni — ⚡ işarəli elementlər yarımçıqdır |

İki klik nə yazır (məsələn `sahə`):

```alqor
gətir vidjet                                   ← yoxdursa əlavə olunur

komponent Panel
    vəziyyət ad: mətn = ""
    vəziyyət sahə1: mətn = ""                  ← vəziyyətlərin yanına

    metod sahə1Dəyişdi(dəyər: mətn)            ← göstər()-dən əvvələ
        özü.sahə1 = dəyər
    son

    göstər()
        qaytar vidjet.sütun(məzmun: [
            …,
            vidjet.sahə(etiket: "Ad", ad: "sahə1",     ← məzmun siyahısına
                        dəyər: özü.sahə1, dəyişdi: özü.sahə1Dəyişdi)
        ])
    son
son
```

Qaydalar (`skelet.py`):

- **Hansı komponent** — kursorun içində olduğu, yoxsa birincisi.
  Faylda komponent yoxdursa `komponent Tətbiq` iskeleti qurulur; fayl
  boşdursa həm də `əsas()` + `pəncərə` əlavə olunur ki, F5 dərhal
  işləsin.
- **Çağırış hara** — kursor `göstər()`-in içində boş sətirdədirsə
  ora; yoxsa JSX-də kök teqin bağlanışından əvvəl (`{…}` ilə), və ya
  `məzmun: [...]` siyahısının sonuna (vergül avtomatik), və ya
  qaytarılan ifadə `vidjet.sütun(...)` qabına bükülür. `göstər()`
  yoxdursa yaradılır.
- **Adlar təkrarlanmır** — `sahə1`, `sahə2`, …; kataloqdakı sabit adlar
  (`şifrə`, `axtar`, `göndər`) toqquşanda kökü ilə birlikdə nömrələnir:
  `şifrə2` + `şifrə2Dəyişdi`.
- **Nümunədə işlənməyən idarəedici** uyğun hadisəyə bağlanır:
  `cədvəl` → `sətirKlik: özü.sətirBasıldı`, `xəbərdarlıq` →
  `bağlana: doğru, bağlandı: özü.xəbərdarlığıBağla`.
- **Mövcud çağırışı tamamlama** — `özü.x…` istinadlarından (və ya
  `ad: "x"` arqumentindən) skelet adı çıxarılır, yalnız ÇATIŞMAYAN
  üzvlər yazılır; çağırış heç nəyə bağlanmayıbsa `dəyər:`/`dəyişdi:`
  arqumentləri də əlavə olunur. İkinci dəfə — "Hər şey yerindədir".

Məlumat mənbəyi `alqor.vidjet.KATALOQ`-dur. Sınaq: kataloqdakı 57
vidjetin hər biri dörd fərqli fayl formasına İKİ DƏFƏ əlavə olunur və
nəticə həm ayrılır, həm də tip yoxlamasından xətasız keçir.

> **Qeyd:** kataloqda bəzi skeletlər `vəziyyət x: tamEn = 0` yazır —
> belə tip yoxdur (ALQ-T002). Studio yerləşdirmə zamanı bunu `tam`-a
> düzəldir; `vidjet.py`-də də düzəldilməlidir.

---

## Redaktor

Öz yazdığımız yüngül redaktor (`statik/redaktor.js`): şəffaf
`<textarea>` + altında rənglənmiş `<pre>`.

- Rəngləmə (`statik/dil.js`): açar sözlər (`acar_sozler.py`-dən),
  tip adları, kontekstli sözlər (`vəziyyət`, `göstər`), mətnlər +
  `{…}` interpolyasiya, `x"…"` / `x"""…"""` xam mətnlər, `//` və
  iç-içə `/* */` şərhlər, ədədlər, JSX teqləri və atributları.
  ASCII yazılmış açar söz nöqtəli xətlə göstərilir.
- Avtomatik girinti: blok açanlardan sonra (`funksiya`, `əgər … onda`,
  `cəhd et`, `hər … içində`, `göstər()`, açıq mötərizə, açıq JSX teqi
  …) +4; `son`, `yoxsa`, `tut`, `nəhayət`, `əks halda` yazılanda sətir
  açan blokun səviyyəsinə qayıdır. Tab = 4 boşluq, Shift+Tab geri.
- Öz geri al / irəli al yığını (Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z) —
  skelet əlavəsi bir addımdır.
- Axtar / əvəzlə (Ctrl+F, Ctrl+H): böyük-kiçik hərf, müntəzəm ifadə.
- Diaqnostika yazarkən (450 ms gecikmə ilə): lekser + parser + tip
  yoxlayıcı; dalğalı xətt, sətir nömrəsində işarə, "Problemlər"
  siyahısı (Azərbaycan dilində mesaj + kod + kömək), klik → sətrə keçid.

### Azərbaycan klaviaturası (spesifikasiya § 1.7)

| Qat | Necə | Söndürmək |
|---|---|---|
| 1. ASCII açar söz | `eger` + boşluq → `əgər` (mətn, şərh və `x.ve` üzv adında yox) | üst sətirdə **ASCII→az** |
| 2. `;` tərkibi | `;e`→ə `;i`→ı `;I`→İ `;o`→ö `;u`→ü `;c`→ç `;s`→ş `;g`→ğ, `;;`→`;` | üst sətirdə **;e→ə** |
| 3. Hərf paneli | redaktorun altında `ə ı ğ ş ç ö ü İ …` düymələri | — |
| (kompilyator) | ASCII yazılış ALQ-L020 xəbərdarlığı ilə qəbul olunur | — |

Bütün faylı birdən düzəltmək: **eger→əgər** düyməsi (lekserin
özünün ASCII kimi tanıdığı tokenlər — identifikatorlara toxunulmur).

---

## Qalan imkanlar

- **Layihə paneli** — fayl ağacı, yarat / adını dəyiş / sil, bir neçə
  nişan, saxlanmamış nişan `●` ilə.
- **İcra** (F5) — fayl `alqorc.py işlət` ilə AYRICA prosesdə işləyir;
  çıxış Server-Sent Events ilə axır (stderr qırmızı, `fayl.alqor:12:5`
  yerləri klikləməli), `giriş ›` sahəsi `oxu()`-ya sətir göndərir,
  "Dayandır" (Shift+F5) proses qrupunu öldürür.
- **Canlı önbaxış** (F6) — faylda `komponent` varsa, o, ayrıca
  prosesdə `pəncərə` modulunun öz serverində göstərilir (`əsas()`
  çağırılmır). Düymələr, sahələr, vəziyyət həqiqi tətbiqdəki kimi
  işləyir. Saxlayanda yenilənir.
- **Xoş gəldin ekranı** — "yeni layihə" şablonları (konsol / veb /
  desktop), layihədəki `.alqor` faylları, qısayollar.
- Qaranlıq / açıq tema, ölçüsü dəyişən panellər (yadda qalır), status
  sətri (sətir:sütun, UTF-8, ASCII sayı, xəta/xəbərdarlıq, tip rejimi).
- **Formatla** (Ctrl+Shift+F) — qarmaq hazırdır: `alqor.formatlayici`
  (və ya `alqor.alqorfmt`) modulu `formatla(mətn) -> mətn` ixrac etdiyi
  gün düymə işləməyə başlayır. Hələlik "formatlayıcı yoxdur" deyir.

### Qısayollar

| Düymə | Əməl |
|---|---|
| Ctrl+S | saxla |
| F5 / Shift+F5 | işlət / dayandır |
| F6 | önbaxış |
| F8 | növbəti problem |
| Ctrl+F / Ctrl+H | axtar / əvəzlə |
| Ctrl+/ | şərh et / aç |
| Ctrl+Z / Ctrl+Y | geri al / irəli al |
| Alt+N / Alt+W | yeni fayl / nişanı bağla |

---

## Arxitektura

```
Brauzer pəncərəsi (Chrome --app / pywebview)      Python (studio/)
┌──────────────────────────────────────┐   HTTP   ┌──────────────────────┐
│ statik/index.html                    │  JSON    │ server.py            │
│   studio.js   tətbiq, panellər       │ ───────▶ │   /api/*  (nişanla)  │
│   redaktor.js redaktor               │ ◀─────── │   layihe.py   fayllar│
│   dil.js      rəngləmə               │   SSE    │   skelet.py   iki klik│
│ <iframe> önbaxış ────────────────┐   │          │   diaqnostika.py     │
└──────────────────────────────────┼───┘          │   icra.py ──▶ alqorc.py işlət
                                   └─────────────▶│   onbaxis.py ──▶ pəncərə serveri
                                                  └──────────────────────┘
```

Pəncərə `alqor.pencere._pəncərəni_aç` ilə açılır (pywebview →
Chrome/Edge/Brave `--app=` → sistem brauzeri) — eyni aparıcı. Pəncərə
bağlananda (səhifə `/api/bagla` göndərir, nəbz kəsilir) server də bitir.

| Fayl | Məzmun |
|---|---|
| `qurulus.py` | kod/mətn/şərh xəritəsi, komponent və üzvlərin tapılması (yarımçıq kodda da işləyir) |
| `skelet.py` | vidjet əlavəsi, çağırışın tamamlanması, fayldakı elementlər |
| `klaviatura.py` | ASCII və `;` qaydaları (brauzer eyni cədvəli `/api/klaviatura`-dan alır) |
| `diaqnostika.py` | lekser + parser + tip yoxlayıcı → `sətir`/`sütun`; ASCII düzəlişi |
| `layihe.py` | layihə qovluğu ilə məhdud fayl əməliyyatları |
| `icra.py` | prosesi işlətmək, çıxışı yığmaq, stdin, dayandırmaq |
| `onbaxis.py` | önbaxış prosesi (birbaşa işlədilir) |
| `sablonlar.py` | konsol / veb / desktop şablonları |
| `server.py` | HTTP server, API marşrutları, pəncərə, `işə_sal()` |

### API

Bütün `/api/*` sorğuları `X-Alqor-Token` başlığı tələb edir (SSE üçün
`?t=`). POST gövdəsi `application/json`.

| Marşrut | Gövdə → cavab |
|---|---|
| `GET /api/melumat` | layihə adı, versiya, şablonlar, tip rejimi |
| `GET /api/agac` | fayl ağacı |
| `GET /api/kataloq` | vidjet kateqoriyaları və kataloq |
| `GET /api/klaviatura` | ASCII + `;` cədvəli, açar sözlər, tiplər |
| `POST /api/fayl/oxu` · `yaz` · `yarat` · `adlandir` · `sil` | `{yol, mətn?, növ?, yeni?}` |
| `POST /api/vidjet/elave` | `{mətn, vidjet, kursor?, ad?}` → `{mətn, kursor, yeniSətirlər, mesaj}` |
| `POST /api/vidjet/numune` | `{mətn, vidjet, kursor?}` → `{kod}` |
| `POST /api/vidjet/tamamla` | `{mətn, kursor}` → `{mətn, kursor, dəyişdi, mesaj}` |
| `POST /api/vidjet/elementler` | `{mətn}` → fayldakı çağırışlar + çatışmayanlar |
| `POST /api/yoxla` | `{mətn, ad, rejim?}` → diaqnostikalar |
| `POST /api/ascii-duzelt` · `formatla` | `{mətn}` → `{mətn}` |
| `POST /api/islet` | `{yol, arqumentlər?, tip?}` → `{id}` |
| `GET /api/islet/axin?id=&t=` | SSE: `çıxış` / `xəta` / `bitdi` hadisələri |
| `POST /api/islet/giris` · `dayandir` | `{id, mətn?}` |
| `POST /api/onbaxis` · `onbaxis/dayandir` | `{yol, komponent?}` → `{ünvan}` və ya `{xəta}` |
| `POST /api/sablon` | `{növ, ad}` → yeni layihə qovluğu |

### Təhlükəsizlik

- Server yalnız `127.0.0.1`-ə bağlanır, port təsadüfidir.
- Hər işə salınmada yeni təsadüfi **nişan** (192 bit); nişansız API
  sorğusu 401. Nişan pəncərə ünvanındadır, səhifə onu `sessionStorage`-a
  köçürüb ünvandan silir.
- `Host` başlığı yalnız `127.0.0.1:PORT` / `localhost:PORT` — DNS
  rebinding hücumu işləmir.
- POST yalnız `application/json` (sadə HTML formaları göndərə bilmir).
- Fayl yolları: `..`, mütləq yol, sürücü hərfi, NUL rədd edilir; sonra
  `Path.resolve()` + `is_relative_to(kök)` (sətir `startswith` YOX —
  `layihə-gizli` qonşu qovluğu sınaqla yoxlanılır). Kənara aparan
  simvolik keçidlər ağacda göstərilmir və açılmır.
- İnterfeys CSP ilə verilir: yalnız öz skriptləri, `eval` yoxdur.

---

## Sınaqlar

```bash
cd alqorc
python -m unittest sinaq.test_studio -v
```

`sinaq/test_studio.py` — nişan və Host, fayl API-nin layihə ilə
məhdudlaşması (10 qaçış cəhdi × 4 əməliyyat, simvolik keçid, prefiks
hiyləsi), diaqnostikanın sətir/sütunu, skelet (boş fayl, komponentsiz
fayl, JSX komponent, `məzmun` siyahısı, təkrar adlar, sabit ad
toqquşması, `gətir vidjet`, kursor yeri, 57 vidjet × 4 forma × 2 dəfə
tip yoxlaması), tamamlama, klaviatura qaydaları, `01-salam.alqor`-un
SSE ilə işlədilməsi (stdin daxil), dayandırma, önbaxış, şablonlar,
`studio --sınaq`.

**Brauzer sınaqları** (Playwright quraşdırılıbsa, yoxsa atlanır):
yazarkən ASCII/`;` çevrilməsi və girinti, geri al, paletdən iki klik,
redaktorda çağırış üzərinə iki klik, diaqnostika xətti.

```bash
pip install playwright        # brauzer artıq varsa `playwright install` lazım deyil
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python -m unittest sinaq.test_studio.Brauzer
```

---

## Məhdudiyyətlər

- Redaktor bütün mətni hər dəyişiklikdə yenidən rəngləyir — bir neçə
  min sətrə qədər rahatdır, çox böyük fayllar üçün nəzərdə tutulmayıb.
  Sətir bükülməsi yoxdur (üfüqi sürüşdürmə).
- Skelet yerləşdirməsi girintiyə əsaslanır: blokun `son`-u onu açan
  sətirlə eyni girintidə olmalıdır (Studio-nun öz girintisi bunu təmin
  edir).
- Önbaxış üst-səviyyə ifadə cümlələrini (`yaz(...)`, server qaldırmaq)
  icra etmir — yalnız elanlar, `gətir` və dəyişənlər.
- Avtomatik tamamlama (autocomplete) və formatlayıcı hələ yoxdur.
