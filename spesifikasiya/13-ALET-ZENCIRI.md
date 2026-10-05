# Alqor — Bölmə 13: Alət Zənciri

---

## 13.1 Quraşdırma (Linux)

```bash
# Rəsmi quraşdırıcı
curl -fsSL https://alqor.az/qur | sh

# Debian / Ubuntu
sudo apt install alqor

# Arch
yay -S alqor

# Fedora
sudo dnf install alqor

# Mənbədən
git clone https://github.com/alqor-dili/alqor
cd alqor && make && sudo make install

# Versiya meneceri (bir neçə versiya yanaşı)
alqorup quraşdır 1.0.0
alqorup istifadə 1.0.0
alqorup siyahı
```

Quraşdırılan fayllar:
```
/usr/bin/alqor           # əsas CLI
/usr/bin/alqorc          # kompilyator
/usr/bin/alqorvm         # icra mühiti
/usr/bin/alqorfmt        # formatter
/usr/bin/alqorlint       # linter
/usr/bin/alqorls         # LSP serveri
/usr/bin/alqorpm         # paket meneceri
/usr/bin/alqortest       # test işlədici
/usr/bin/alqordoc        # sənəd generatoru
/usr/lib/alqor/          # standart kitabxana
~/.alqor/                # istifadəçi keşi və paketlər
```

---

## 13.2 `alqor` — əsas CLI

```bash
alqor yeni <ad>                  # yeni layihə yarat
alqor yeni <ad> --şablon veb     # şablonla (konsol | veb | desktop | kitabxana)
alqor işlət <fayl>               # kompilyasiyasız işlət (VM)
alqor işlət                      # layihənin giriş nöqtəsini işlət
alqor qur                        # kompilyasiya et
alqor sına                       # testləri işlət
alqor təmizlə                    # qurma nəticələrini sil
alqor yoxla                      # kompilyasiya etmədən yoxla (sürətli)
alqor format                     # kodu formatla
alqor sənəd                      # sənəd yarat
alqor söhbət                     # REPL başlat
alqor paketlə                    # quraşdırıcı yarat
alqor yerləşdir                  # yerləşdir
alqor versiya
alqor kömək <əmr>
```

### `alqor qur` seçimləri
```bash
alqor qur --hədəf linux-x64      # linux-x64 | linux-arm64 | veb | wasm
                                 # windows-x64 | macos-arm64
alqor qur --buraxılış            # optimallaşdırılmış
alqor qur --debaq                # debaq simvolları ilə
alqor qur --optimallaşdırma 3    # 0..3
alqor qur --statik               # asılılıqsız binar
alqor qur --kiçik                # minimum ölçü
alqor qur --çıxış ./bin/proqram
alqor qur --izlə                 # fayl dəyişəndə avtomatik yenidən qur
```

### `alqor işlət` seçimləri
```bash
alqor işlət --izlə               # dəyişiklikdə yenidən işlət
alqor işlət --profil             # performans profili
alqor işlət --iddia-saxla
alqor işlət -- arq1 arq2         # proqrama arqument ötür
```

---

## 13.3 `alqorfmt` — formatter

```bash
alqorfmt .                       # bütün faylları formatla
alqorfmt --yoxla .               # dəyişiklik lazımdırmı (CI üçün)
alqorfmt --fərq .                # fərqi göstər
alqorfmt --ascii-düzəlt .        # ASCII açar sözləri kanonik formaya çevir
alqorfmt --homoqlif-düzəlt .     # gizli simvolları düzəlt
```

### Standart qaydalar
| Qayda | Dəyər |
|---|---|
| Girinti | 4 boşluq |
| Maksimum sətir | 100 simvol |
| Operator ətrafı boşluq | var (`a + b`) |
| Vergüldən sonra boşluq | var |
| Mötərizə daxilində boşluq | yox (`f(a)`) |
| Sətir sonu | `LF` |
| Faylın sonu | bir boş sətir |
| Sondakı vergül | çoxsətirli siyahılarda var |
| Açar sözlər | kanonik Azərbaycan formasında |

Konfiqurasiya — `layihe.alqor`:
```toml
[format]
girinti = 4
maks_sətir = 100
sondakı_vergül = doğru
ascii_düzəlt = doğru
```

---

## 13.4 `alqorlint` — linter

```bash
alqorlint .
alqorlint --düzəlt .             # avtomatik düzəldiləni düzəlt
alqorlint --sərt .
```

### Yoxlamalar
| Kateqoriya | Nümunə |
|---|---|
| İstifadəsiz | istifadə olunmayan dəyişən, idxal, funksiya |
| Adlandırma | konvensiyaya uyğunluq |
| Mürəkkəblik | çox dərin iç-içəlik, çox uzun funksiya |
| Potensial xəta | müqayisədə `=` əvəzinə `==`, boş `tut` bloku |
| Performans | dövrdə mətn birləşdirmə, lazımsız kopya |
| Təhlükəsizlik | kodda gizli açar, SQL birləşdirmə, `\| xam` |
| Üslub | mötərizəsiz qarışıq prioritet, `gətir *` |
| Əlçatanlıq | veb komponentlərdə `alt` atributu yoxdur |

```toml
[lint]
sərtlik = "normal"        # sərbəst | normal | sərt
söndür = ["istifadəsiz-dəyişən"]
xəta = ["təhlükəsizlik-*"]
maks_funksiya_sətri = 50
maks_dərinlik = 4
```

---

## 13.5 `alqortest` — test işlədici

```bash
alqortest                        # bütün testlər
alqortest sınaq/auth_sınaq.alqor # bir fayl
alqortest --filtr "istifadəçi"   # ada görə
alqortest --örtük                # kod örtüyü hesabatı
alqortest --izlə                 # dəyişiklikdə yenidən işlət
alqortest --paralel 4
alqortest --təkrar 100           # flaky test axtarışı
```

Çıxış:
```
  Alqor Test 1.0.0

  sınaq/riyazi_sınaq.alqor
    ✓ toplama düzgündür                        0.3ms
    ✓ bölmə sıfıra xəta atır                   0.1ms
    ✗ kvadrat kök mənfi ədəddə                 0.2ms

      Gözlənilən: ƏdədDeyil
      Alınan:     0.0
      sınaq/riyazi_sınaq.alqor:24:5

  sınaq/mətn_sınaq.alqor
    ✓ böyük hərf azərbaycan qaydası ilə         0.1ms
    ✓ "ışıq".böyüyə() == "IŞIQ"                 0.1ms

  Nəticə: 4 uğurlu, 1 uğursuz, 0 atlanmış      1.2s
  Örtük:  87.3% (1243/1424 sətir)
```

---

## 13.6 `alqordoc` — sənəd generatoru

```bash
alqordoc                         # HTML sənəd yarat
alqordoc --format markdown
alqordoc --çıxış sənəd/
alqordoc --server                # canlı önizləmə ilə
```

Mənbə:
```alqor
/// Verilən radiusla dairənin sahəsini hesablayır.
///
/// # Parametrlər
/// - `radius`: Dairənin radiusu (müsbət olmalıdır)
///
/// # Qaytarır
/// Dairənin sahəsi
///
/// # Xətalar
/// `radius` mənfidirsə `ArqumentXətası` atır
///
/// # Nümunə
/// ```alqor
/// yaz(dairəSahəsi(5))    // 78.539...
/// ```
ixrac et funksiya dairəSahəsi(radius: onluq) -> onluq
    təmin radius >= 0 yoxsa
        at ArqumentXətası("Radius mənfi ola bilməz")
    son
    qaytar riyaziyyat.Pİ * radius ** 2
son
```

Sənəddəki nümunə kodlar **test kimi də işlədilir** (`alqortest --sənəd`).

---

## 13.7 `alqor söhbət` — REPL

```
$ alqor söhbət
Alqor 1.0.0 — interaktiv rejim. Kömək üçün :kömək

alqor> 2 + 2
4

alqor> dəyişən ad = "Aysel"
alqor> yaz("Salam, {ad}")
Salam, Aysel

alqor> funksiya ikiqat(x) qaytar x * 2 son
alqor> ikiqat(21)
42

alqor> :tip ikiqat
funksiyaTipi(tam) -> tam

alqor> :yüklə mənim-fayl.alqor
alqor> :siyahı
alqor> :təmizlə
alqor> :çıx
```

Əmrlər: `:kömək` `:tip` `:yüklə` `:siyahı` `:təmizlə` `:vaxt` `:sənəd` `:çıx`

---

## 13.8 `alqorls` — LSP serveri

Dəstəklənən redaktorlar: **Alqor Studio**, VS Code, Neovim, Zed, Helix, Emacs, Sublime.

| Xüsusiyyət | Dəstək |
|---|---|
| Sintaksis vurğulama | ✓ |
| Avtotamamlama | ✓ (kontekstli, sənədlə) |
| Təyinata get | ✓ |
| İstinadları tap | ✓ |
| Ad dəyişdirmə | ✓ (bütün layihədə) |
| Hover sənədi | ✓ (Azərbaycan dilində) |
| Diaqnostika | ✓ (yazarkən) |
| Sürətli düzəlişlər | ✓ (`ə` çatışmır, idxal əlavə et...) |
| Kod formatlaması | ✓ |
| Kod linzaları | ✓ (istinad sayı, test işlət) |
| Sənəd sxemi | ✓ |
| Semantik rənglər | ✓ |
| Debaq (DAP) | ✓ |
| Azərbaycan klaviatura köməyi | ✓ (xüsusi genişləndirmə) |

---

## 13.9 Alqor Studio — IDE

```
┌─────────────────────────────────────────────────────────────────┐
│ Fayl  Redaktə  Görünüş  Qurma  Alətlər  Kömək    [▶] [⏸] [📦]  │
├──────────────┬─────────────────────────┬────────────────────────┤
│ 📁 LAYİHƏ    │  əsas.alqor        ×    │  CANLI ÖNİZLƏMƏ        │
│              │                         │  ┌──────────────────┐  │
│ ▼ mənbə/     │ 1  gətir veb            │  │                  │  │
│   əsas.alqor │ 2                       │  │  Salam, dünya!   │  │
│   model.alq  │ 3  funksiya əsas()      │  │                  │  │
│ ▼ sınaq/     │ 4      dəyişən s =      │  │  [Bas mənə]      │  │
│   test.alqor │ 5          yeni Server()│  │                  │  │
│ ▶ statik/    │ 6      s.dinlə(8080)    │  └──────────────────┘  │
│   layihe.alq │ 7  son                  │  🔄 Avtomatik yenilənir │
│              │                         │                        │
│              │ ⌨ ə ı ğ ş ç ö ü İ       ├────────────────────────┤
│              │ AZ klaviatura: AÇIQ     │  TERMİNAL              │
│              │                         │  $ alqor işlət         │
├──────────────┴─────────────────────────┤  Server: :8080         │
│ ⚠ PROBLEMLƏR (1)                       │  ✓ Kompilyasiya 0.3s   │
│ ALQ-T024 sətir 4: `s` istifadə olunmur │                        │
└────────────────────────────────────────┴────────────────────────┘
```

### Əsas xüsusiyyətlər
| Xüsusiyyət | Təsvir |
|---|---|
| **Canlı önizləmə** | Veb / desktop / konsol çıxışı yan paneldə, hər dəyişiklikdə yenilənir |
| **Azərbaycan klaviaturası** | Avtomatik çevirmə, `;` kompozisiya, hərf paneli |
| **Tam Azərbaycan interfeysi** | Menyular, mesajlar, sənədlər |
| **Sıfır konfiqurasiya debaq** | Breakpoint, addım-addım, dəyişən izləmə |
| **Vizual qurucu** | Desktop UI-ni sürüklə-burax ilə düzəltmək |
| **Bir klikdə paketləmə** | `.deb`, `.AppImage`, veb bundle |
| **Daxili terminal** | |
| **Git inteqrasiyası** | |
| **Dərslik rejimi** | Yeni başlayanlar üçün addım-addım təlimlər |

Texnologiya: Tauri + CodeMirror 6. Ölçü: ~15 MB (Electron ekvivalenti ~150 MB).

---

## 13.10 Debaq

```bash
alqor debaq əsas.alqor
```

```alqor
// Kodda breakpoint
dayanNöqtəsi

// Debaq çapı
çap(dəyişən)                 // strukturlu, tiplərlə
çap!(ifadə)                  // ifadəni və nəticəsini çap edir
                             // → "x + y = 15"
```

```
alqor-debaq> davam
alqor-debaq> addım            # bir sətir irəli
alqor-debaq> içəri            # funksiyaya gir
alqor-debaq> çıx              # funksiyadan çıx
alqor-debaq> dəyişənlər       # cari əhatədəki dəyişənlər
alqor-debaq> yığın            # çağırış yığını
alqor-debaq> çap x
alqor-debaq> qoy x = 5
alqor-debaq> dayanNöqtəsi əsas.alqor:42
alqor-debaq> sil 1
```

---

## 13.11 Profil və performans

```bash
alqor profil əsas.alqor
alqor profil --yaddaş
alqor profil --alov-qrafiki     # flame graph
```

```
  Funksiya                    Çağırış    Ümumi      Öz
  ────────────────────────────────────────────────────────
  hesablaHamısı()                   1   1.243s    0.012s
    emal()                      10000   1.180s    0.890s
      çevir()                   10000   0.290s    0.290s
    yaz()                         100   0.051s    0.051s
```

---

## 13.12 CI/CD

`.github/workflows/alqor.yml`:
```yaml
name: Alqor CI
on: [push, pull_request]
jobs:
  yoxla:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: alqor-dili/quraşdır@v1
        with:
          versiya: '1.0.0'
      - run: alqorfmt --yoxla .
      - run: alqorlint .
      - run: alqor yoxla
      - run: alqortest --örtük
      - run: alqor qur --buraxılış
      - run: alqor paketlə --hədəf deb
```

---

## 13.13 Mühit dəyişənləri

| Dəyişən | Təyinatı |
|---|---|
| `ALQOR_YOL` | Standart kitabxana yolu |
| `ALQOR_PAKETLƏR` | Paket keşi qovluğu |
| `ALQOR_HƏDƏF` | Standart kompilyasiya hədəfi |
| `ALQOR_JURNAL` | Jurnal səviyyəsi |
| `ALQOR_RƏNG` | `həmişə` / `heçvaxt` / `avto` |
| `ALQOR_DİL` | Mesaj dili (`az` standart, `en` ikinci) |
| `ALQOR_SAP` | Kompilyator sap sayı |
| `ALQORHUB_TOKEN` | Paket yayımlama tokeni |

---

## 13.14 Çıxış kodları

| Kod | Mənası |
|---|---|
| `0` | Uğurlu |
| `1` | İcra zamanı xəta |
| `2` | Kompilyasiya xətası |
| `3` | Yanlış əmr sətri istifadəsi |
| `4` | Fayl tapılmadı |
| `5` | Paket xətası |
| `101` | Panika |
| `130` | İstifadəçi tərəfindən dayandırıldı (Ctrl+C) |
