## Alqor 2.3

Azərbaycan dilində proqramlaşdırma dili: dil, **Alqor Studio** IDE, paket meneceri,
linter, formatlayıcı, debaqçı və oflayn sənədlər. Hər quraşdırıcıda Python daxildir,
əlavə heç nə lazım deyil.

### Yeniliklər

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

### Quraşdırma

**Windows** — `AlqorQurasdirici-*.exe`: endirin və işə salın (idarəçi hüququ lazım deyil).
Başlat menyusunda **Alqor Studio**, **Alqor terminalı**, **Alqor sənədləri** yaranır.
Quraşdırmasız variant: `…-windows-portativ.zip`.

**Linux**
- Debian / Ubuntu: `sudo apt install ./alqor_*_amd64.deb` (ARM üçün `arm64`)
- İstənilən distribusiya, sudo-suz: `tar xzf alqor-*-linux-x86_64.tar.gz && ./alqor-*/qurasdir.sh`

**macOS** — `Alqor-*-macos-aarch64.dmg` (Apple Silicon) və ya `…-x86_64.dmg` (Intel):
«Alqor Studio»-nu Applications qovluğuna sürükləyin, ilk dəfə sağ klik → Open.
Terminal əmrləri üçün `.tar.gz` arxivindəki `qurasdir.sh` skriptini işlədin.

**alqor-rs** (sürətli icraçı; konsol proqramları üçün) — `alqor-rs-*-<platforma>` arxivləri:
`alqor-rs işlət proqram.alq`. Veb, pəncərə və vidjet modulları üçün əsas quraşdırıcını istifadə edin.

**WebAssembly** — `alqor-wasm-*.zip`: brauzerdə Alqor icraçısı (`index.html` nümunədir).

Faylların yoxlama cəmləri `SHA256SUMS.txt` faylındadır.

Sənədlər və nümunələr: https://vuqar.pro/alqor · Paketlər: https://vuqar.pro/hub
