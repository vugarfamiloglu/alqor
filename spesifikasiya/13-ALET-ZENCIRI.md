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
~/.alq/                # istifadəçi keşi və paketlər
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

### Etalon implementasiyada vəziyyət

Python etalonunda CLI `python alqorc.py <əmr>` kimi çağırılır. Hər əmrin
ASCII ləqəbi var (`işlət` = `islet` = `run`) — Windows konsolunda
Azərbaycan hərfləri yazmaq çətin olanda.

| Əmr | Vəziyyət |
|---|---|
| `işlət <fayl> [--tip] [-- arq…]` | ✅ |
| `yoxla <fayl\|qovluq>` | ✅ leksik + sintaktik + tip |
| `tip <fayl\|qovluq> [--rejim]` | ✅ |
| `söhbət` | ✅ (§ 13.7) |
| `tokenlər <fayl>` | ✅ diaqnostika üçün |
| `hərf <mətn>`, `sırala <söz>…` | ✅ az-AZ hərf qaydaları |
| `versiya`, `kömək` | ✅ |
| `format` (`alqorfmt`) | ✅ § 13.3 |
| `studio` | ✅ Alqor Studio (§ 13.9) |
| `ls [--stdio]` | ✅ LSP serveri (§ 13.8) |
| `dap` | ✅ Debaqçı — Debug Adapter Protocol (§ 13.8) |
| `yeni <ad> [--şablon konsol\|veb\|desktop\|kitabxana]` | ✅ hər şablonun işləyən sınaqları var |
| `işlət` (fayl olmadan — layihənin giriş nöqtəsi) | ✅ |
| `sına [yol] [--filtr] [--sənəd] [--ətraflı]` | ✅ § 13.5 |
| `sənəd [yol] [--format html\|markdown] [--çıxış]` | ✅ § 13.6 |
| `qur [--tip]` | ✅ `qurma/<ad>.pyz` — aşağıya baxın |
| `təmizlə` | ✅ yalnız layihə daxilindəki `qurma/` |

Repo kökündəki `alqor.cmd` (Windows) və `alqor` (Linux/macOS) bu
əmrləri `alqor yeni …` kimi çağırmağa imkan verir.

**`qur` etalon implementasiyada.** Maşın koduna kompilyator hələ
yoxdur. `alqor qur` Python *zipapp* yaradır: `qurma/<ad>.pyz` faylının
içində icra mühiti və layihənin faylları (mənbə, şablon, statik) var;
`sınaq/`, `sənəd/`, `qurma/` daxil edilmir. İlk işə salınmada layihə
faylları keş qovluğuna açılır (`ALQOR_KES` ilə dəyişdirilir).
`python ad.pyz` (Windows) və ya `./ad.pyz` (Linux/macOS) ilə işləyir.
`--tip` — paketdən əvvəl tip yoxlaması. Aşağıdakı `--hədəf` seçimləri
yerli kompilyatorla gələcək.
| `paketlə`, `yerləşdir` | planlaşdırılır |

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

### Təhlükəsizlik zəmanəti

Formatlayıcı **proqramın mənasını dəyişə bilməz**. Format edilmiş mətn
yenidən leksə və ayrılır; token axını (ASCII açar sözlərin kanonik
forması istisna), JSX məzmunu və sintaksis ağacı (mövqelər nəzərə
alınmadan) orijinalla eyni olmalıdır. Fərq çıxarsa fayl **toxunulmaz
qalır** və xəta bildirilir. Sintaksis xətası olan fayl format edilmir.

### Girinti alqoritmi

Girinti açar söz sayğacından deyil, **parserdən** gəlir: parser hər
tokenin neçə blok gövdəsinin içində olduğunu qeyd edir. Mötərizə
içindəki çoxsətirli bloklar (arqument kimi verilən `funksiya`, siyahıdakı
`əgər … yoxsa … son`) eyni mötərizədəki qonşu sətrə nisbətən
girintilənir. Davam sətirlərinin əl ilə hizalanması qorunur, amma
açan sətirdən ən azı bir pillə dərin olmalıdır.

Çoxsətirli mətn (`"""…"""`, `x"""…"""`) və JSX daxili yalnız bütöv
sürüşdürülür — dəyəri dəyişmir. Sətir sonu şərhlərinin hizalanması
qorunur; yalnız şərhdən ibarət sətir növbəti kod sətrinin girintisini
alır.

### Etalon implementasiyada vəziyyət

| Qayda | Vəziyyət |
|---|---|
| Girinti, operator/vergül boşluqları, mötərizə daxili | ✅ |
| ASCII → kanonik açar söz (standart; `--ascii-saxla` söndürür) | ✅ |
| `--homoqlif-düzəlt` (bayraqsız homoqlifli fayl rədd edilir) | ✅ |
| Boş sətirlər (ən çox 2), sətir sonu boşluqları, `LF`, BOM, NFC, tab | ✅ |
| `--yoxla` (kod 1 — format lazımdır), `--fərq` | ✅ |
| 100 simvoldan uzun sətirləri bölmək | planlaşdırılır — hazırda toxunulmur |
| Çoxsətirli siyahılara sondakı vergül | planlaşdırılır |
| `layihe.alq` → `[format]` | planlaşdırılır |

Çıxış kodları: `0` — uğurlu / format lazım deyil, `1` — `--yoxla`
rejimində format lazımdır, `2` — format edilə bilməyən fayl var
(sintaksis xətası), `3` — yanlış istifadə.

Alqor Studio-da **Ctrl+Shift+F** eyni formatlayıcını çağırır.

Konfiqurasiya — `layihe.alq`:
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
alqortest sınaq/auth_sınaq.alq # bir fayl
alqortest --filtr "istifadəçi"   # ada görə
alqortest --örtük                # kod örtüyü hesabatı
alqortest --izlə                 # dəyişiklikdə yenidən işlət
alqortest --paralel 4
alqortest --təkrar 100           # flaky test axtarışı
```

Çıxış:
```
  Alqor Test 1.0.0

  sınaq/riyazi_sınaq.alq
    ✓ toplama düzgündür                        0.3ms
    ✓ bölmə sıfıra xəta atır                   0.1ms
    ✗ kvadrat kök mənfi ədəddə                 0.2ms

      Gözlənilən: ƏdədDeyil
      Alınan:     0.0
      sınaq/riyazi_sınaq.alq:24:5

  sınaq/mətn_sınaq.alq
    ✓ böyük hərf azərbaycan qaydası ilə         0.1ms
    ✓ "ışıq".böyüyə() == "IŞIQ"                 0.1ms

  Nəticə: 4 uğurlu, 1 uğursuz, 0 atlanmış      1.2s
  Örtük:  87.3% (1243/1424 sətir)
```

---

### Etalon implementasiyada vəziyyət

`alqor sına` (və ya `alqortest`): yol verilməsə layihənin `sınaq/`
qovluğu; qovluqda `sınaq/`, `sinaq/`, `test/` altındakı və adı
`_sınaq.alq` ilə bitən fayllar. Hər fayl ayrı interpretatorda işləyir.

| Xüsusiyyət | Vəziyyət |
|---|---|
| `@sınaq`, `@sınaq("ad")`, `@sınaqVerilənlər([...])` | ✅ |
| `@sınaqQrupu("ad") modul …` + `@əvvəl` / `@sonra` | ✅ |
| `@atla("səbəb")` | ✅ |
| `--filtr söz`, `--sənəd`, `--ətraflı` (uğursuz sınağın `yaz` çıxışı) | ✅ |
| Uğursuz təsdiqin yeri (`fayl:sətir:sütun`) | ✅ |
| Çıxış kodu: 0 — hamısı uğurlu, 1 — uğursuz/xəta var, 4 — sınaq yoxdur | ✅ |
| `--örtük`, `--izlə`, `--paralel`, `--təkrar`, `test.saxta` | planlaşdırılır |

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

Sənəddəki nümunə kodlar **test kimi də işlədilir** (`alqor sına --sənəd`):
hər ```` ```alqor ```` bloku faylın adları əlçatan olan ayrıca proqram kimi
icra olunur.

**Qaydalar.** `///` sənədi elanın üstündə yazılır və `ixrac et`,
görünüş sözləri, annotasiyalar (`@sınaq`) aradan keçir. `//!` faylın
sənədidir. Faylda `ixrac et` varsa yalnız ixrac olunanlar, yoxdursa
`gizli` olmayan bütün yuxarı səviyyəli elanlar sənədləşdirilir; sinif
üzvləri də daxildir. İmza mənbədən olduğu kimi götürülür. Sənəd
mətnində Markdown alt çoxluğu: başlıq (`#`), siyahı, `kod`, **qalın**,
kod bloku.

| Seçim | Vəziyyət |
|---|---|
| HTML (standart, tək fayl, açıq/qaranlıq), `--format markdown` | ✅ |
| `--çıxış q` | ✅ (standart `sənəd/`) |
| `--server` (canlı önizləmə) | planlaşdırılır |

---

## 13.7 `alqor söhbət` — REPL

```
$ alqor söhbət
Alqor 1.0.0 — interaktiv rejim
Azərbaycan dilində proqramlaşdırma dili

  :kömək   bütün əmrlər
  :çıx     çıxış (Ctrl+D də işləyir)

alqor> 2 + 2
4  // tam

alqor> "ışıq".böyüyə()
"IŞIQ"  // mətn

alqor> funksiya ikiqat(x: tam) -> tam
  ...     qaytar x * 2
  ... son
  funksiya `ikiqat` təyin edildi

alqor> ikiqat(21)
42  // tam

alqor> nəticə + 1
43  // tam
```

### Davranış

| Xüsusiyyət | Təsvir |
|---|---|
| **Çoxsətirli giriş** | Blok açılanda `  ...` davam sətri görünür. Lekserin kontekst yığını açıq blokları izləyir |
| **İfadənin dəyəri** | Son ifadə avtomatik çap olunur, tipi ilə birlikdə (`4  // tam`) |
| **`nəticə`** | Son çap olunmuş dəyər bu dəyişəndə saxlanılır |
| **Vəziyyət** | Dəyişən, funksiya, sinif seans boyu yaşayır |
| **Xətadan bərpa** | Xəta seansı dayandırmır |
| **Ləğv etmək** | İki dəfə boş Enter, `:ləğv`, və ya Ctrl+C |
| **Tarixçə** | `~/.alq/tarixce` — yuxarı/aşağı oxlarla |
| **Tab tamamlama** | Açar sözlər, tip adları, elan olunmuş adlar, `:əmrlər` |
| **ASCII xəbərdarlığı** | `eger` yazsanız bir sətirlik xəbərdarlıq (`:ascii qapat` ilə söndürülür) |

### Meta-əmrlər

| Əmr | Təyinatı |
|---|---|
| `:kömək` `:k` `:?` | Bütün əmrlər və ipucları |
| `:çıx` `:q` | Söhbəti bitir |
| `:tip <ifadə>` `:t` | İfadənin tipini göstər |
| `:siyahı` `:s` | Təyin edilmiş adlar (funksiya/sinif/dəyişən qruplarında) |
| `:vaxt <ifadə>` `:v` | İcra müddətini ölç |
| `:yüklə <fayl>` | Faylı seansa yüklə |
| `:saxla <fayl>` | Seansı `.alq` faylı kimi saxla |
| `:tarixçə [n]` | Son n giriş |
| `:təmizlə` | Bütün dəyişənləri sil |
| `:tokenlər <kod>` | Lekserin çıxışı |
| `:aac <kod>` | Sintaksis ağacı |
| `:hərflər` | Azərbaycan hərfləri və ASCII qarşılıqları |
| `:əlifba` | 32 hərfli əlifba və sıralama |
| `:ascii aç\|qapat` | ASCII açar söz xəbərdarlığı |
| `:ləğv` | Yarımçıq girişi ləğv et |

> Hər meta-əmrin ASCII ləqəbi də var: `:komek`, `:cix`, `:siyahi`,
> `:temizle`, `:yukle`, `:tarixce`, `:herfler`, `:elifba`.

### Üzv adlarında ASCII təklifi

ASCII çevrilməsi **yalnız açar sözlərə** aiddir. Üzv adında ASCII
yazılsa, REPL düzgün adı təklif edir:

```
alqor> [1, 2, 3].cem()
✖ ALQ-T006  `siyahı[tam]` tipində `cem` üzvü yoxdur — `cəm` demək
            istəyirdiniz? ASCII çevrilməsi yalnız AÇAR SÖZLƏRƏ aiddir,
            üzv adlarına yox
```

## 13.8 `alqorls` — LSP serveri

```bash
alqor ls --stdio         # redaktor özü işə salır (JSON-RPC, stdin/stdout)
```

Asılılıqsız, LSP 3.17 alt çoxluğu (`alqorc/alqor/alqorls.py`). Analiz
`alqor yoxla` ilə eynidir: mənbə → lekser → parser → tip yoxlayıcısı.
Tip yoxlayıcısı **qeyd rejimində** işləyir — hər ad istifadəsinin hansı
elana bağlandığını və hər `a.b` ifadəsinin tipini yadda saxlayır.

| Xüsusiyyət | Vəziyyət |
|---|---|
| Diaqnostika (yazarkən) — leksik, sintaksis, tip; `ALQ-*` kodu ilə | ✅ |
| Avtotamamlama: `x.` → modul / sinif / mətn / siyahı üzvləri | ✅ |
| Avtotamamlama: açar sözlər, şablonlar (`funksiya …`, `əgər …`), adlar, `gətir` → modullar | ✅ |
| Hover: imza, tip, `///` sənəd şərhi, vidjet izahı | ✅ |
| İmza köməyi (`f(` → parametrlər, aktiv parametr) | ✅ |
| Təyinata get — dəyişən, funksiya, sinif, metod, qısa qurucunun sahəsi | ✅ |
| İstinadları tap, ad dəyişdirmə (açar söz / yanlış ad / daxili ad rədd edilir) | ✅ |
| Sənəd sxemi (sinif → qurucu, metod, xassə) | ✅ |
| Formatlama (`alqorfmt`) | ✅ |
| Sürətli düzəlişlər: `eger` → `əgər`, "bəlkə: `uzunluq`", hamısını düzəlt | ✅ |
| Yarımçıq kod: xətalı sətirlər boşluqla əvəz olunub yenidən analiz edilir — hover/tamamlama işləməyə davam edir | ✅ |
| Layihə üzrə: `gətir "./x.alq"` elanına keçid, istinadlar və ad dəyişmə bütün iş sahəsində (`{f kimi g}` ləqəbi yerli qalır) | ✅ |
| İş sahəsi simvolları (Ctrl+T) — `tpl` → `topla` | ✅ |
| Kod linzaları: üst səviyyə funksiya/sinif üstündə "N istinad"; `@sınaq` üstündə "▶ Sına" | ✅ |
| Semantik rənglər: sinif, funksiya, metod, xassə, parametr, modul, sadalama; `sabit` → readonly, daxili → defaultLibrary | ✅ |
| DAP (debaq) — `alqor dap`: dayanma nöqtələri (şərtli), `stopOnEntry`, next / stepIn / stepOut / pause, çağırış yığını, yerli və qlobal dəyişənlər (siyahı, lüğət, nümunə açılır), ifadə hesablama; çıxış `output` hadisəsidir | ✅ |

Fayl idxalı tip yoxlayıcısında da görünür: `gətir "./x.alq" kimi m`
faylı ayrıca ayrılıb yoxlanır (keşlənir, dövri idxal qorunur), onun qlobal
elanları `m`-in üzvləri olur — `m.yoxdur` → ALQ-M002, tapılmayan fayl →
ALQ-M001.

Redaktorlar:

| Redaktor | Necə |
|---|---|
| **VS Code** | `redaktor/vscode/` — qrammatika + LSP müştərisi (`npx @vscode/vsce package`) |
| Neovim, Helix | `alqor ls --stdio` — nümunə konfiqurasiya `redaktor/vscode/README.md`-də |
| Alqor Studio | öz analizi (`/api/yoxla`); tamamlama `alqorls`-a keçiriləcək ⏳ |

TextMate qrammatikası və `language-configuration.json` açar söz
siyahısından yaradılır (`python -m alqor.qrammatika --yaz`); sınaq
onların köhnəlmədiyini yoxlayır.

---|---|
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
│ 📁 LAYİHƏ    │  əsas.alq        ×    │  CANLI ÖNİZLƏMƏ        │
│              │                         │  ┌──────────────────┐  │
│ ▼ mənbə/     │ 1  gətir veb            │  │                  │  │
│   əsas.alq │ 2                       │  │  Salam, dünya!   │  │
│   model.alq  │ 3  funksiya əsas()      │  │                  │  │
│ ▼ sınaq/     │ 4      dəyişən s =      │  │  [Bas mənə]      │  │
│   test.alq │ 5          yeni Server()│  │                  │  │
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
| **Vidjet paleti** | 118 element (beynəlxalq adlarla: Button, Breadcrumb …), hər biri əsl görünüşündə miniatürlə; iki klik işləyən kodu yazır ✅ |
| **Xüsusiyyətlər paneli** | Seçilmiş elementin mətni, növü, ölçüsü və görünüşü (rəng, fon, kənar, künc, şrift… — `üslub:`, § 14.8); dəyişiklik koda yazılır, önbaxış dərhal yenilənir ✅ |
| **Vizual qurucu** | Desktop UI-ni sürüklə-burax ilə düzəltmək |
| **Bir klikdə paketləmə** | `.deb`, `.AppImage`, veb bundle |
| **Daxili terminal** | |
| **Git inteqrasiyası** | |
| **Dərslik rejimi** | Yeni başlayanlar üçün addım-addım təlimlər |

Texnologiya: Tauri + CodeMirror 6. Ölçü: ~15 MB (Electron ekvivalenti ~150 MB).

---

## 13.10 Debaq

```bash
alqor debaq əsas.alq
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
alqor-debaq> dayanNöqtəsi əsas.alq:42
alqor-debaq> sil 1
```

---

## 13.11 Profil və performans

```bash
alqor profil əsas.alq
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
| `ALQOR_PAKETLER` | Paket keşi qovluğu |
| `ALQOR_HEDEF` | Standart kompilyasiya hədəfi |
| `ALQOR_JURNAL` | Jurnal səviyyəsi |
| `ALQOR_RENG` | `həmişə` / `heçvaxt` / `avto` |
| `ALQOR_DIL` | Mesaj dili (`az` standart, `en` ikinci) |
| `ALQOR_SAP` | Kompilyator sap sayı |
| `ALQORHUB_TOKEN` | Paket yayımlama tokeni |
| `ALQOR_BASSIZ` | `1` — `pəncərə` pəncərə açmır (CI, sınaq; § 12.2.1) |
| `NO_COLOR` | təyin olunubsa `konsol` rəng kodları çap etmir ([no-color.org](https://no-color.org)) |

Etalon implementasiyada hazırda `ALQOR_RENG`, `ALQOR_BASSIZ` və
`NO_COLOR` oxunur; qalanları kompilyator və paket meneceri ilə gələcək.

> **Niyə adlar ASCII-dir?**
> `ALQOR_RƏNG` kimi ad shell-də təyin oluna bilmir — POSIX mühit dəyişəni
> adları yalnız `[A-Za-z_][A-Za-z0-9_]*` ola bilər, Windows `set` əmri isə
> UTF-8 adları ümumiyyətlə qəbul etmir. Dəyişən **adları** ASCII-dir,
> **dəyərləri** isə Azərbaycan dilindədir (`ALQOR_RENG=həmişə`).

---

## 13.15 Konsol kodlaşdırması (vacib)

Alqor alətləri işə düşərkən standart çıxışı məcburi **UTF-8**-ə keçirir.

Səbəb: Windows-da Python/`cmd.exe`/PowerShell standart çıxış kodlaşdırması
sistemin kod səhifəsidir (məs. `cp1251`, `cp857`). Belə olanda alət öz
Azərbaycan dilindəki xəta mesajını **çap edə bilmir** və `UnicodeEncodeError`
ilə dayanır.

| Platforma | Tədbir |
|---|---|
| Linux / macOS | `LANG`/`LC_ALL` UTF-8 deyilsə, `C.UTF-8` qəbul edilir |
| Windows | `SetConsoleOutputCP(65001)` + axınlar UTF-8-ə keçirilir |
| Python etalonu | `sys.stdout.reconfigure(encoding="utf-8")` |

`ALQOR_KODLASMA=sistem` ilə bu davranış söndürülə bilər (tövsiyə olunmur).

---

## 13.16 Çıxış kodları

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
