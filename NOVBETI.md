# Alqor — vəziyyət və növbəti işlər

> Yeni sessiyada işə buradan başlayın. İş birbaşa `main` budağında
> aparılır; hər addımdan sonra commit + push.
> Sınaq: `cd alqorc && python sina.py --nümunələr` (1051 sınaq keçir).
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
  http, şəbəkə (TCP/UDP), verilənlər (SQLite, sorğu qurucusu, tranzaksiya,
  miqrasiya)

**Alətlər**
- `alqor işlət / yoxla / tip / format / yeni / sına / sənəd / qur / təmizlə / studio / ls / dap`
- `alqorfmt` (formatlayıcı), `alqorls` (LSP: layihə üzrə keçid/istinad/ad
  dəyişmə, iş sahəsi simvolları, kod linzaları, semantik rənglər),
  `alqor dap` (debaqçı) + VS Code genişlənməsi (`redaktor/vscode/`, F5 debaq)
- `qur` → tək fayllı `.pyz` paketi

**Alqor Studio** (`alqorc/studio/`)
- Redaktor, Azərbaycan klaviaturası, diaqnostika, F5 icra, F6 önbaxış
- Element paleti: 118 element, miniatürlər (açıq/qaranlıq tema),
  beynəlxalq adlar (Button, Breadcrumb …), iki klikdə işləyən kod
- Xüsusiyyətlər paneli: mətn, növ, rəng, fon, kənar, künc, şrift …
  → kod avtomatik yazılır, önbaxış canlı yenilənir (Studio temasını izləyir)
- Avtomatik tamamlama və imza ipucu (`alqorls`)
- Debaq: dayanma nöqtələri, addımlar, yığın, dəyişənlər, ifadə hesablama

**Tip yoxlayıcısı**: generiklərin çıxarılması, modul tipləri annotasiyada, `sərt` rejim tam əhatə ilə

**Sənədlər**: spesifikasiya (§ 1–14), bələdçi dərslikləri, 10 nümunə proqram

## 🟡 Yarımçıq qalanlar

| İş | Nə qalıb |
|---|---|
| Alqor Studio | sürüklə-burax düzülüş (vizual dizayner) yoxdur |
| http | WebSocket yoxdur |
| verilənlər | yalnız SQLite — PostgreSQL/MySQL sürücüsü və ORM modelləri (`@cədvəl`, `Model`) yoxdur |
| qur | yalnız `.pyz` — quraşdırıcı yoxdur |
| Dil məsələləri | `hər x üçün siyahı içində` söz sırası; `5.` yazılışı spesifikasiya ilə uyğun deyil (bax `alqorc/VEZIYYET.md`) |

## ⬜ Heç başlanmayanlar (növbə ilə)

1. **Standart kitabxana, qalan modullar**: keş, növbə, planlayıcı,
   validasiya, pul, lokalizasiya, poçt → sonra şəkil, qrafik (fayla),
   pdf, ffi
2. **Quraşdırıcı generatoru** — `.exe` (Windows), `.deb`/`.rpm`/AppImage
   (Linux), `.dmg` (macOS)
3. **Alqor Studio — quraşdırıcılı Desktop tətbiqi** (istifadəçi tələbi):
   Başlat menyusu, masaüstü ikonu, `.alq` faylları Studio ilə açılır,
   Python daxildə
4. **JS/WASM backend** — brauzerdə Python olmadan işləmək
5. **alqorpm + alqorhub** — paket meneceri və paket deposu
6. **alqorlint** — linter
7. **Rust-a köçürmə** — istehsal kompilyatoru

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
