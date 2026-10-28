## Alqor 2.4.0

Azərbaycan dilində proqramlaşdırma dili: dil, **Alqor Studio** IDE, paket meneceri,
linter, formatlayıcı, debaqçı və oflayn sənədlər. Hər quraşdırıcıda Python və sürətli
Rust icraçısı daxildir, əlavə heç nə lazım deyil.

### 2.4-ün yenilikləri

**Python kitabxanaları birbaşa Alqor-da**
- `gətir python:statistics kimi st`, `gətir python:collections.{Counter}` — istənilən Python
  paketi (PyPI) Alqor kodunda işləyir
- Ədəd, mətn, siyahı, lüğət, dəst, kortej iki tərəfə avtomatik çevrilir; Alqor funksiyaları
  Python-a ötürülə bilir; Python xətaları `cəhd et / tut` ilə tutulur (`PythonXətası`)
- `alqor python qur requests` — paket layihənin `python_paketlər/` qovluğuna; `alqor python
  siyahı | sil`; `layihe.alq`-da `[python]` asılılıqları; `alqor qur` paketləri daxil edir

**Sürətli Rust icraçısı (bytecode virtual maşın)**
- Kod bytecode-a çevrilir və virtual maşında işləyir: Python icraçısından təxminən 100 dəfə,
  əvvəlki Rust icraçısından 1.5–3 dəfə sürətli (məsələn, `fib` 7.5 s → 0.08 s)
- Rust icraçısında yeni modullar: `veb` server (marşrutlar, şablonlar, sessiyalar), `http`,
  `şəbəkə`, `verilənlər` (SQLite), `şifrə`, `kodlaşdırma`, `sıxma`, `csv`, `toml`, `xml`
- `alqor işlət --motor rs` — Rust icraçısı ilə; `--motor avto` — proqramın modulları Rust-da
  varsa Rust, yoxdursa Python (standart hələ `py`; `ALQOR_MOTOR=avto` ilə dəyişmək olar)
- Rust icraçısı bütün quraşdırıcılara daxildir (`bin/alqor-rs`)

### Düzəlişlər
- Windows: `veb` serverində statik fayl yolları, bağlantı xətalarının mətni, pəncərə serverinin
  rədd edilən sorğulara cavabı
- `.rpm` paketlərinə yeni rpm versiyalarının tələb etdiyi yük həzmləri əlavə olundu
- `alqorpm`: depo ünvanı veb səhifə qaytaranda xam HTML yox, aydın xəta mesajı

## 2.3.1-də düzəlişlər

- **Studio: öz kontekst menyusu hər yerdə.** Sağ klik artıq heç yerdə brauzerin menyusunu açmır:
  xoş gəldin ekranında yeni fayl, forma və layihə, şablondan layihə, faylı açmaq və işlətmək;
  giriş sahələrində kəs, kopyala, yapışdır; qalan yerlərdə əmr palitrası, tema və kömək
- **Forma dizayneri:** `.forma` açıq olanda soldakı «Elementlər» paleti formaya obyekt əlavə edir
  (əvvəl forma faylına kod yazıb onu pozurdu); önbaxış formanı öz kodu ilə göstərir və dəyişəndə yenilənir
- **Xoş gəldin ekranı:** «Qısayollar» siyahısının düzülüşü düzəldi
- **Windows:** `yol.qovluq` da digər `yol` funksiyaları kimi `/` qaytarır
- Paralel `gözlə` zamanı `yaz` sətirlərinin qarışması aradan qalxdı

## 2.3-ün yenilikləri

**Vizual forma dizayneri (Delphi üslubu)**
- Pəncərəni `.forma` faylında sürüklə-burax ilə qurun, kod `.alq` faylında qalır
- Palitra, kətan, Struktur ağacı, inspektor (Xüsusiyyətlər / Hadisələr)
- Hadisəyə iki klik edəndə `.alq` faylında `əməl` yaranır; Alt+F12 Kod ilə Dizayn arasında keçir
- Axın (standart) və sərbəst düzülüş, hizalama, geri al / təkrarla
- `alqor yeni --şablon desktop` və Studio-nun «Yeni layihə → Desktop» şablonu formadan başlayır

**Verilənlər bazası formada**
- `VerilənlərBazası` və `Sorğu` komponentləri; vidjetlər `mənbə` + `sütun` ilə bazaya bağlanır, `naviqator`
- Cədvəl redaktoru və `.sxem` faylları: SQLite, PostgreSQL, MySQL
- Bazaya tətbiq edəndə yalnız çatışmayan cədvəl və sütunlar əlavə olunur, heç nə silinmir
- Mövcud bazadan idxal; «Cədvəldən forma yarat» — bir klikdə CRUD forması
- Terminalda: `alqor sxem fayl.sxem sql | model | tətbiq ÜNVAN`, `alqor sxem idxal ÜNVAN`

**Eyni forma vebdə**
- `ALQOR_VEB=1` ilə forma brauzerdə açılır; hər istifadəçinin öz sessiyası olur
- `alqor yerləşdir` forma layihəsini server və Docker paketinə çevirir

**Paylama**
- `alqor qur --exe`: tək `.exe` (Python daxil)
- `alqor qur --alqor --platforma windows|linux|macos`: quraşdırıcılar
- `alqor yerləşdir`: statik sayt və Docker
- JS hədəfi: `alqor işlət --js`, `alqor qur --hədəf js|veb`; brauzerdə komponent, vidjet, pəncərə və http
- **alqor-rs**: Rust icraçısı, Python icraçısından 20–40 dəfə sürətli; WebAssembly paketi

**Digər**
- Paket deposu: `alqorpm` standart olaraq https://vuqar.pro/hub istifadə edir; öz deponuz üçün `alqor hub`
- Xəta mesajlarında sənəd linki: `vuqar.pro/alqor/xeta/<KOD>`
- Studio: «Haqqında» pəncərəsi, qruplara bölünmüş klaviatura qısayolları

## Quraşdırma

**Windows** — `AlqorQurasdirici-*.exe`: endirin və işə salın (idarəçi hüququ lazım deyil).
Başlat menyusunda **Alqor Studio**, **Alqor terminalı**, **Alqor sənədləri** yaranır.
Quraşdırmasız variant: `…-windows-portativ.zip`.

**Linux**
- Debian / Ubuntu: `sudo apt install ./alqor_*_amd64.deb` (ARM üçün `arm64`)
- İstənilən distribusiya, sudo-suz: `tar xzf alqor-*-linux-x86_64.tar.gz && ./alqor-*/qurasdir.sh`

**macOS** — `Alqor-*-macos-aarch64.dmg` (Apple Silicon) və ya `…-x86_64.dmg` (Intel):
«Alqor Studio»-nu Applications qovluğuna sürükləyin, ilk dəfə sağ klik → Open.
Terminal əmrləri üçün `.tar.gz` arxivindəki `qurasdir.sh` skriptini işlədin.

**alqor-rs** (yalnız sürətli icraçı, quraşdırıcısız) — `alqor-rs-*-<platforma>` arxivləri:
`alqor-rs işlət proqram.alq`. Pəncərə, vidjet və Python kitabxanaları üçün əsas quraşdırıcını istifadə edin.

**WebAssembly** — `alqor-wasm-*.zip`: brauzerdə Alqor icraçısı (`index.html` nümunədir).

Faylların yoxlama cəmləri `SHA256SUMS.txt` faylındadır.

Sənədlər və nümunələr: https://vuqar.pro/alqor · Paketlər: https://vuqar.pro/hub
