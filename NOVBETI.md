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

İstifadəçi **Windows** (ilk növbədə), **Linux** və ya **macOS**-da bir
quraşdırıcı ilə Alqor-u qurur, Studio-da və ya terminalda kod yazır, proqramı
**kompilyasiya edib** (tək fayllı tətbiq / quraşdırıcı) paylaşır və ya
**vebə yerləşdirir**. Aşağıdakı sıra bu yolu açan işlərdir.

## 🗺 Yol xəritəsi (növbə ilə)

### Mərhələ 1 — Windows: "endir → qur → yaz → işlət" ⬜
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

### Mərhələ 2 — Kompilyasiya: proqramı paylaşmaq ⬜
5. **`alqor qur --exe`** — istifadəçinin proqramı Alqor quraşdırılmamış
   kompüterdə işləyən **tək `.exe`** (Windows), Linux binarı və macOS
   `.app` olur (daxili icra mühiti ilə).
6. **Studio-da "Qur" düyməsi** — hədəf seçimi: `.exe`, quraşdırıcı,
   veb səhifə (JS), Node.js; nəticə qovluğu açılır.
7. `alqor qur --quraşdırıcı` — istifadəçi layihəsi üçün öz Windows
   quraşdırıcısı (bu gün zip + PowerShell → həqiqi `.exe`).

### Mərhələ 3 — Vebə yerləşdirmə ⬜
8. **`alqor yerləşdir`**:
   - statik / brauzer proqramları (JS hədəfi ✅) → GitHub Pages,
     Netlify, Cloudflare Pages üçün hazır qovluq;
   - `veb` serverli tətbiqlər → avtomatik `Dockerfile` + `alqor
     yerləşdir --docker`; Render / Fly.io / VPS üçün addım-addım bələdçi.
9. **JS hədəfini genişləndirmək**: `vidjet` və komponentlər brauzerdə
   (veb tətbiqləri serversiz işləsin), `http` müştərisi (`fetch`).
10. **Onlayn sınaq meydançası** (`alqor.az/meydança`) — JS hədəfi ilə
    brauzerdə quraşdırmadan kod yazıb işlətmək.

### Mərhələ 4 — Linux və macOS quraşdırıcıları ⬜
11. `.deb`, `.rpm`, `.AppImage` — Mərhələ 1-dəki kimi CLI əmrləri
    PATH-da (`/usr/bin/alqor`), Studio, fayl əlaqəsi.
12. macOS `.pkg` (+ `.dmg`) — `/usr/local/bin/alqor`, Apple Silicon və
    Intel; həqiqi Mac-da yoxlama (CI `macos-latest`).
13. İmza: Windows Authenticode, macOS notarizasiya — **sertifikat
    tələb edir, sahibin qərarıdır** (imzasız da işləyir, xəbərdarlıqla).

### Mərhələ 5 — Ekosistem ⬜
14. **alqorhub ictimai server** (`hub.alqor.az`) — `alqor pm əlavə`
    başqalarının paketlərini tapsın.
15. **VS Code genişlənməsi** Marketplace-də (`.vsix` CI-da qurulur).
16. **Sənəd saytı** `alqor.az` — spesifikasiya, bələdçilər, API.

### Mərhələ 6 — Rust kompilyatoru (sürət və tək binar) 🟡
17. `alqor-rs/`: lekser + AAC hazırdır; parser, icraçı, standart
    kitabxana. Sınaq: Python etalonu ilə eyni çıxış (JS hədəfindəki
    müqayisə qoşqusu ilə). Sonra: native binar və WASM.

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
