# Alqor — vəziyyət və növbəti işlər

> Yeni sessiyada işə buradan başlayın. İş birbaşa `main` budağında
> aparılır; hər addımdan sonra commit + push.
> Sınaq: `cd alqorc && python sina.py --nümunələr` (1110 sınaq keçir).
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
- `alqorfmt` (formatlayıcı), `alqorls` (LSP: layihə üzrə keçid/istinad/ad
  dəyişmə, iş sahəsi simvolları, kod linzaları, semantik rənglər),
  `alqor dap` (debaqçı) + VS Code genişlənməsi (`redaktor/vscode/`, F5 debaq)
- `qur` → tək fayllı `.pyz` paketi; `qur --quraşdırıcı` → `.deb`, Windows
  (zip + Inno Setup `.iss`), macOS `.app`; `qur --studio` → Alqor Studio-nun
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

## 🟡 Yarımçıq qalanlar

Hazırda yoxdur. Qeyd: Windows/macOS quraşdırıcıları Linux-da yaradılır və
quruluşu sınanır — həqiqi Windows/macOS-da əl ilə yoxlamaq lazımdır;
`.AppImage`, `.rpm`, `.dmg` hələ yoxdur.

## ⬜ Heç başlanmayanlar (növbə ilə)

1. **JS/WASM backend** — brauzerdə Python olmadan işləmək
2. **alqorpm + alqorhub** — paket meneceri və paket deposu
3. **alqorlint** — linter
4. **Rust-a köçürmə** — istehsal kompilyatoru

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
