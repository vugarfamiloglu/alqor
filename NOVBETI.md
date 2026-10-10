# Alqor — vəziyyət və növbəti işlər

> Yeni sessiyada işə buradan başlayın. İş birbaşa `main` budağında
> aparılır; hər addımdan sonra commit + push.
> Sınaq: `cd alqorc && python sina.py --nümunələr` (1219 sınaq keçir).
> Studio brauzer sınaqları Playwright ilə: `python -m unittest sinaq.test_studio`.

## ✅ Hazır olanlar

**Dil nüvəsi** (`alqorc/alqor/`)
- Lekser, parser, tip yoxlayıcısı (3 rejim), icraçı, REPL (`alqor söhbət`)
- Azərbaycan əlifbası, ASCII → kanonik açar sözlər, homoqlif qoruması
- Asinxronluq (`gözlə`, `paralel`, `sap`), sinif/komponent/interfeys/sadalama

**Standart kitabxana**
- json, fayl, qovluq, yol, vaxt, riyaziyyat, təsadüfi, naxış, sistem,
  konsol, jurnal, test, paralel, sap
- veb (server, marşrutlar, şablonlar, sessiya, CORS, komponentlər)
- pəncərə (desktop), vidjet — **118 element** (veb + desktop, `üslub:`)
- `alqorc/alqor/modullar/` (tənbəl yüklənir): kodlaşdırma, csv, toml, yaml,
  xml, html, konfiq, sıxma, şifrə (AES-256-GCM, scrypt, JWT → `tokenYarat`),
  http (WebSocket də: `http.vebSoket`, server `s.soket`), şəbəkə (TCP/UDP), verilənlər (SQLite, PostgreSQL, MySQL/MariaDB, ORM `Model`, sorğu qurucusu, tranzaksiya,
  miqrasiya), pul (dəqiq pul hesabı, valyuta, operatorlar), keş (yaddaş,
  fayl, Redis), növbə (fon işləri), planlayıcı (cron), validasiya (sxemlər;
  telefon, FİN, VÖEN, IBAN, kart), lokalizasiya (tərcümə, cəm formaları,
  tarix/ədəd formatı), poçt (SMTP, əlavələr), şəkil (PNG/JPEG/GIF/BMP/PPM,
  filtrlər, çəkmə), qrafik (SVG diaqramlar), pdf (TrueType alt dəsti,
  cədvəllər, şəkillər), ffi (C kitabxanaları)

**Alətlər**
- `alqor işlət / yoxla / tip / format / yeni / sına / sənəd / qur / təmizlə / studio / ls / dap`
- `alqorpm` (paket meneceri: semver aralıqları, həlledici, `alqor.kilid`,
  SHA256, yol/qit asılılıqları, audit) + `alqorhub` (paket deposu serveri,
  veb səhifələr, API); `gətir paket` `paketlər/`-dan yüklənir
- `alqorlint` (35 qayda: istifadəsiz, adlandırma, mürəkkəblik, potensial
  xəta, performans, təhlükəsizlik, üslub, əlçatanlıq; `--düzəlt`, LSP-də
  və Studio-da görünür)
- `alqorfmt` (formatlayıcı), `alqorls` (LSP: layihə üzrə keçid/istinad/ad
  dəyişmə, iş sahəsi simvolları, kod linzaları, semantik rənglər),
  `alqor dap` (debaqçı) + VS Code genişlənməsi (`redaktor/vscode/`, F5 debaq)
- `qur` → tək fayllı `.pyz` paketi; `qur --quraşdırıcı` → `.deb`, `.rpm`,
  `.AppImage`, Windows (zip + Inno Setup `.iss`), macOS `.app` və `.dmg`; `qur --studio` → Alqor Studio-nun
  quraşdırıcıları (`.alq` əlaqəsi, menyu/masaüstü ikonu, `--python-daxil`)

**Alqor Studio** (`alqorc/studio/`)
- Redaktor, Azərbaycan klaviaturası, diaqnostika, F5 icra, F6 önbaxış
- Element paleti: 118 element, miniatürlər (açıq/qaranlıq tema),
  beynəlxalq adlar (Button, Breadcrumb …), iki klikdə işləyən kod
- Xüsusiyyətlər paneli: mətn, növ, rəng, fon, kənar, künc, şrift …
  → kod avtomatik yazılır, önbaxış canlı yenilənir (Studio temasını izləyir)
- Avtomatik tamamlama və imza ipucu (`alqorls`)
- Debaq: dayanma nöqtələri, addımlar, yığın, dəyişənlər, ifadə hesablama
- Vizual dizayner (⊞ Dizayn): sürüklə-burax, daşı, sil — kod yenilənir
- IDE qabığı: ikonlu menyu sətri (9 menyu, alt menyular, Alt+hərf),
  kontekst menyular, əmr palitrası (Ctrl+Shift+P, fayl, `:` sətir, `@`
  simvol), fəaliyyət zolağı, layihədə axtarış/əvəzləmə, Struktur paneli,
  layihə üzrə istinadlar və ad dəyişmə, yerləşdirilən / üzən panellər

**Tip yoxlayıcısı**: generiklərin çıxarılması, modul tipləri annotasiyada, `sərt` rejim tam əhatə ilə

**Sənədlər**: spesifikasiya (§ 1–14), bələdçi dərslikləri, 10 nümunə proqram

## 🎯 Hədəf

İstifadəçi **Windows**-da bir
quraşdırıcı ilə Alqor-u qurur, Studio-da və ya terminalda kod yazır, proqramı
**kompilyasiya edib** (tək fayllı tətbiq / quraşdırıcı) paylaşır və ya
**vebə yerləşdirir**. Aşağıdakı sıra bu yolu açan işlərdir.

## 🗺 Yol xəritəsi (növbə ilə)

### Mərhələ 1 — Windows: "endir → qur → yaz → işlət" ✅ (həqiqi Windows-da CI yoxlaması gözlənilir)

Hazırdır: `alqor qur --alqor` → `AlqorQurasdirici-<v>.exe` (Inno Setup,
daxili Python 3.12, `alqor*` əmrləri PATH-da, `.alq` əlaqəsi, Başlat
menyusu, silmə), portativ zip, **oflayn sənəd mərkəzi** (`alqor
sənədlər`, Studio-da F1), `.github/workflows/buraxilis.yml` (teqdə qurur,
səssiz quraşdırıb yoxlayır, Releases-ə yükləyir). Wine altında
kompilyasiya, quraşdırma, PATH, `alqor islet` və silmə yoxlanılıb.

1. **Vahid Alqor quraşdırıcısı (`AlqorQurasdirici.exe`)** — Inno Setup
   ilə həqiqi `.exe`: daxili Python (həmişə), `alqor`, `alqorpm`,
   `alqorlint`, `alqorfmt`, `alqorls` əmrləri **PATH**-a, Alqor Studio,
   bələdçilər və nümunələr; `.alq` fayl əlaqəsi, Başlat menyusu,
   silmə proqramı, istifadəçi səviyyəsində (admin hüququ tələb etmir).
2. **Studio — ilk açılış**: "Yeni layihə" sehrbazı (konsol / veb /
   desktop şablonları), Sənədlər/Alqor qovluğu, nümunələr qalereyası.
3. **GitHub Actions**: hər push-da Windows + Linux + macOS-da sınaqlar;
   `v*` teqində quraşdırıcılar avtomatik qurulub **Releases**-ə yüklənir.
4. **Windows-da avtomatik tüstü sınağı**: CI quraşdırıcını səssiz qurur,
   `alqor yeni → işlət → qur` zəncirini yoxlayır, sonra silir.

### Mərhələ 2 — Kompilyasiya: proqramı paylaşmaq ✅

Hazırdır: `alqor qur --exe [fayl.alq]` → tək `.exe` (Rust başladıcısı
`alqor-rs/baslatici/` + sıxılmış Python + tətbiq; konsol/pəncərə avtomatik),
xətalı proqram qurulmur; Studio **İşlət → Qur** (`.exe`, veb, JS, `.pyz`,
quraşdırıcı, Ctrl+Shift+B). CI-da Python-suz PATH ilə `.exe` yoxlanır.

5. **`alqor qur --exe`** — istifadəçinin proqramı Alqor quraşdırılmamış
   kompüterdə işləyən **tək `.exe`** (Windows), Linux binarı və macOS
   `.app` olur (daxili icra mühiti ilə).
6. **Studio-da "Qur" düyməsi** — hədəf seçimi: `.exe`, quraşdırıcı,
   veb səhifə (JS), Node.js; nəticə qovluğu açılır.
7. `alqor qur --quraşdırıcı` — istifadəçi layihəsi üçün öz Windows
   quraşdırıcısı (bu gün zip + PowerShell → həqiqi `.exe`).

### Mərhələ 3 — Vebə yerləşdirmə 🟡
8. ✅ **`alqor yerləşdir`** (spes. § 13.2, sənəd mərkəzində «Vebə
   yerləşdirmə»; Studio: *İşlət → Qur: vebə yerləşdir*):
   - `gətir veb` olmayan proqram → statik sayt (`index.html`, `404.html`,
     `.nojekyll`): Netlify Drop, GitHub Pages (`--çıxış docs`),
     Cloudflare Pages; `konsol` modulu JS hədəfinə əlavə olundu;
   - `veb` serverli tətbiq → `tetbiq.pyz` + `Dockerfile`; `dinlə`
     `PORT` / `ALQOR_HOST` oxuyur; Render / Fly.io / VPS addımları
     `YERLESDIR.md`-də.
9. ✅ **JS hədəfi: interfeys brauzerdə** (spes. § 13.14):
   - komponentlər (`vəziyyət`, hesablananlar, props, uşaq komponentlər)
     və `pəncərə` (`Pəncərə`, `məzmun`, menyu + qısayollar, `üslub`,
     dialoqlar → `confirm`/`prompt`) brauzerdə serversiz işləyir; DOM
     Python pəncərəsinin `yamaq()` nüvəsi ilə yenilənir;
   - `vidjet` (118 element) Python mənbəyindən avtomatik JS-ə çevrilir
     (`alqor/js/vidjet_cevir.py`) — HTML Python ilə eynidir (müqayisə
     sınağı); `http` müştərisi (brauzerdə sinxron XHR, Node.js-də
     `fetch` uşaq prosesdə);
   - `alqor yerləşdir`: `gətir pəncərə` olan proqram statik sayt olur
     (nümunələr 06, 08, 09); Playwright sınaqları Chromium-da;
   - qalıb: fayl dialoqları brauzerdə (File System Access API),
     `http.faylYüklə`/`vebSoket`, bir neçə pəncərənin eyni anda
     göstərilməsi (bu gün sonuncu açılan göstərilir).
10. **Onlayn sınaq meydançası** (`alqor.vuqar.pro`) — JS hədəfi ilə
    brauzerdə quraşdırmadan kod yazıb işlətmək.

### Mərhələ 4 — Rust kompilyatoru (sürət və tək binar) 🟡
17. `alqor-rs/`: lekser ✅ və parser ✅ — Python etalonu ilə eyni tokenlər
    və eyni AAC (`python -m alqor.rs.muqayise tokenlər|aac [--korpus]`);
    icraçı yarımçıq (dəyərlər, mühit, ifadələr), standart kitabxana yoxdur. Sınaq: Python etalonu ilə eyni çıxış (JS hədəfindəki
    müqayisə qoşqusu ilə). Sonra: native binar və WASM.

### Sonraya saxlanılıb ⏸
- **Ekosistem** — [alqor.vuqar.pro](https://alqor.vuqar.pro): paket deposu
  (alqorhub), sənəd saytı, VS Code Marketplace.
- **Linux və macOS quraşdırıcıları** — generatorlar kodda qalır
  (`.deb`, `.rpm`, `.AppImage`, `.dmg`), amma hələlik prioritet deyil.

✅ Bu sessiyada hazır olanlar: JS hədəfi (`alqor işlət --js`,
`alqor qur --hədəf js|veb`, spes. § 13.14), ifadəsiz `seç`-də şərt halları.

## Qeydlər

- Fayl sonluğu **`.alq`**-dır (`salam.alq`, manifest `layihe.alq`). Köhnə
  `.alqor` faylları və `layihe.alqor` hələ də tanınır.

- Alqor adlarında `W` hərfi ola bilməz (Azərbaycan əlifbasında yoxdur):
  `JWTYarat` → `tokenYarat`, `markdown` → `işarəliMətn`.
- Yeni standart modul: `alqorc/alqor/modullar/<ad>.py` (`qur`, `tiplər`,
  istəyə görə `obyekt_tipləri`) + `modullar/__init__.py` → `QEYD`.
- Yeni vidjet: `alqorc/alqor/vidjet_elave.py` (funksiya, `ƏLAVƏ_KATALOQ`,
  `ƏLAVƏ_ADLAR`, CSS) + `alqorc/alqor/vidjet_arayis.py` (izahlar) +
  `alqorc/studio/miniatur.py` (nümunə) → `python -m alqor.vidjet_arayis --yaz`.
