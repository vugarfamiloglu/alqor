# Alqor kompilyatoru — iş vəziyyəti

> Etalon implementasiya, **Python 3.12**. Son yenilənmə: 6 oktyabr 2026

**Mərhələ 1–5 BİTDİ** — dil nüvəsi tamamdır:
lekser · parser · interpretator · standart kitabxana · REPL ·
**JSX** · **tənbəl generatorlar** · **asinxron icra** ·
**statik tip yoxlayıcı** · **veb server + şablon** · **desktop**

**600 sınaq keçir.** 7 nümunə proqramın **hamısı** ayrılır, tip
yoxlamasından keçir və icra olunur.

---

## Fayl quruluşu

```
alqorc/
├── alqorc.py            CLI: işlət / söhbət / tokenlər / yoxla / hərf / sırala
├── sina.py              sınaq işlədicisi
├── alqor/
│   ├── elifba.py         az-AZ hərf qaydaları, əlifba sırası, ahəng qanunu
│   ├── homoqlif.py       oxşar simvolların aşkarlanması
│   ├── acar_sozler.py    açar sözlər + tip adları + aliaslar
│   ├── token.py          Token, Yer, şablon parçaları, operator cədvəli
│   ├── xeta.py           Diaqnostika, çərçivəli hesabat
│   ├── menbe.py          UTF-8 → NFC → LF → homoqlif → mövqe xəritəsi
│   ├── lekser.py         lekser (kontekst yığını ilə)
│   ├── aac.py            abstrakt sintaksis ağacı — 70+ qovşaq
│   ├── parser.py         rekursiv enmə + prioritet dırmaşması
│   ├── deyerler.py       icra dəyərləri, Mühit, Sinif, Nümunə, Sadalama
│   ├── icraci.py         ağac gəzən interpretator
│   ├── kitabxana.py      standart kitabxana (16 modul, ~330 funksiya)
│   ├── sohbet.py         interaktiv rejim (REPL) — 18 meta-əmr
│   ├── parser_jsx.py     JSX oxuyucusu
│   ├── korutin.py        Korutin, Gələcək, LəğvNişanı
│   ├── tipler.py         tip təsviri və uyğunluq qaydaları
│   ├── tipyoxlayici.py   statik tip yoxlayıcı
│   ├── sablon.py         `.alqorhtml` şablon mühərriki
│   ├── veb.py            HTTP server, marşrutlar, sessiya, ara proqramlar
│   └── pencere.py        desktop: pəncərə, menyu, dialoq, hadisə dövrü
└── sinaq/
    ├── test_elifba.py        (31)
    ├── test_menbe.py         (34)
    ├── test_lekser.py        (70)
    ├── test_icraci.py        (150)  parser + interpretator + JSX
    ├── test_sohbet.py        (45)   REPL
    ├── test_korutin.py       (43)   generatorlar + asinxron
    ├── test_tipyoxlayici.py  (83)   tip yoxlayıcı
    ├── test_veb.py           (69)   server + marşrut + şablon
    └── test_pencere.py       (75)   pəncərə + menyu + dialoq + komponent
```

## İşə salmaq

```bash
cd alqorc

python alqorc.py söhbət                          # interaktiv rejim
python alqorc.py tip ../numuneler                # tip yoxlaması
python alqorc.py işlət fayl.alqor --tip          # icradan əvvəl yoxla
python sina.py --nümunələr                       # 600 sınaq + nümunələr
python alqorc.py işlət ../numuneler/02-dovrler.alqor
python alqorc.py işlət ../numuneler/04-siniflər.alqor
python alqorc.py tokenlər ../numuneler/01-salam.alqor
python alqorc.py yoxla ../numuneler
python alqorc.py hərf "ışıq İmran"

# Veb server
python alqorc.py işlət ../numuneler/05-veb-server.alqor          # port 8080
python alqorc.py işlət ../numuneler/05-veb-server.alqor -- sınaq # port açmadan

# Desktop tətbiq
python alqorc.py işlət ../numuneler/06-desktop.alqor             # pəncərə açır
python alqorc.py işlət ../numuneler/06-desktop.alqor -- sınaq    # başsız
```

---

## İşləyən dil xüsusiyyətləri

| Sahə | Vəziyyət |
|---|---|
| Dəyişənlər, sabitlər, `dəyişməz` | ✅ |
| Dağıtma (kortej, siyahı, obyekt, `...qalan`) | ✅ |
| Bütün operatorlar + 19 səviyyəli prioritet | ✅ |
| Şablon mətnlər + format spesifikatorları | ✅ |
| `əgər` / `varsa` / `yoxdursa` (cümlə və ifadə) | ✅ |
| `seç` + naxış uyğunlaşdırma (literal, diapazon, tip, kortej, siyahı, obyekt) | ✅ |
| Bütün dövrlər + etiketlər + `yoxsa` bloku + filtr | ✅ |
| Funksiyalar: standart dəyər, adlı arqument, variadic, yayma | ✅ |
| Lambda (`=>`), anonim funksiya, qapanma | ✅ |
| Rekursiya + `@yaddaşla` memoizasiya | ✅ |
| Siniflər, miras, polimorfizm, `üst(...)`, `üst.metod()` | ✅ |
| Mücərrəd siniflər + tətbiq yoxlaması | ✅ |
| Hesablanan xassələr (`oxu`/`yaz`), tənbəl xassələr | ✅ |
| Struktur (dəyər semantikası), sadalama, qarışıq, interfeys | ✅ |
| Operator yükləmə (`topla`, `bərabərdir`, `müqayisə`, `mətnƏt`...) | ✅ |
| `genişlət` — mövcud tiplərə metod əlavə | ✅ |
| Xətalar: `cəhd et`/`tut`/`nəhayət`, iyerarxiya, `təmin`, `iddia` | ✅ |
| `gecikdir`, `istifadə` (resurs idarəetməsi) | ✅ |
| İxtiyari tiplər: `?`, `??`, `?.`, `!`, `boşdur` | ✅ |
| Kolleksiya qurmaları (siyahı, lüğət, dəst, generator) | ✅ |
| Modullar: `modul` bloku, `gətir`, seçmə idxal, yerli fayl | ✅ |
| Tip çevirmələri: `kimi`, `kimi?`, implisit `tam`→`onluq` | ✅ |
| Standart kitabxana: 13 modul | ✅ |
| `generator` / `ver` | ⚠ sadələşdirilmiş (tənbəl deyil) |
| `asinxron` / `gözlə` | ⚠ sinxron icra olunur |
| **REPL** (`söhbət`) — çoxsətirli, 18 meta-əmr, tarixçə, tamamlama | ✅ |
| **JSX** — atributlar, komponentlər, parça, HTML qaçışı | ✅ |
| **Tənbəl generatorlar** — sonsuz generatorlar işləyir | ✅ |
| **Asinxron** — `Gələcək`, `paralel`, `sap`, `LəğvNişanı` | ✅ |
| **Statik tip yoxlayıcı** — 3 rejim, axın daralması, 25 xəta kodu | ✅ |

---

## Təsdiqlənmiş nəticələr

```
böyüyə("ışıq") → "IŞIQ"      (Python standartı: "IŞIK"  ✖)
böyüyə("i")    → "İ"         (Python standartı: "I"     ✖)
kiçiyə("I")    → "ı"         (Python standartı: "i"     ✖)

Əlifba sırası:
  Alqor  : ağac, çay, ev, əlif, göl, ışıq, ilk, şam, zəfər   ✓
  Python : ağac, ev, göl, ilk, zəfər, çay, ışıq, şam, əlif   ✖

"ASCII".kiçiyə() → "ascıı"   ← az-AZ qaydası ilə I → ı. Düzgündür.
```

---

## Kodun açdığı SPESİFİKASİYA PROBLEMLƏRİ

### Lekser mərhələsində tapılanlar (düzəldilib)

| # | Problem | Həll |
|---|---|---|
| 1 | `gətir riyaziyyatdan {kök}` — `-dan` şəkilçisi ayrı token ola bilməz (`meydan` adlı modul sınardı) | `gətir riyaziyyat.{kök}` |
| 2 | `içində deyil` for-each bağlayıcısı ilə toqquşur | silindi → `deyil (x içindədir s)` |
| 3 | `ALQOR_RƏNG` POSIX-də mümkün deyil | adlar ASCII, dəyərlər azərbaycanca |
| 4 | Windows konsolu cp1251 — alət öz xəta mesajını çap edə bilmir | axınlar məcburi UTF-8 (stdin də!) |
| 5 | `şablon` ehtiyat sözü `veb.şablon()` ilə toqquşur | ehtiyat siyahısı 4 sözə daraldıldı |
| 6 | Tire (`—`) səhvən homoqlif sayılırdı | durğu işarələri cədvəldən çıxarıldı |

### Parser və interpretator mərhələsində tapılanlar (düzəldilib)

| # | Problem | Həll |
|---|---|---|
| 7 | **`xassə mətn: mətn` işləmirdi** — tip adları açar söz idi, halbuki `mətn`, `tam`, `say` Azərbaycan dilində ən təbii sahə adlarıdır | Tip adları **öncədən elan olunmuş identifikator** oldu (Go `int`, Rust `i32` kimi). 105 → 92 açar söz |
| 8 | **Mötərizə içində çoxsətirli anonim funksiya ayrılmırdı** — `s.qrup("/a", funksiya(q) … son)` | Lekserdə tək dərinlik sayğacı yerinə **kontekst yığını** (MÖTƏRİZƏ / BLOK). Yeni sətir yalnız təpədə BLOK olanda emissiya olunur |
| 9 | **Qısa qurucu sinfin `son`-unu udurdu** | Qısa forma = `xassə` parametri var + gövdə boş |
| 10 | **`içində`-dən sonra yeni sətir udulurdu** → dövr gövdəsindəki `əgər` filtr kimi oxunurdu | `içində` DAVAM_ACAR_SOZLERI-dən çıxarıldı |
| 11 | **`tip(x)` funksiyası `tip Ad = ...` aliası ilə toqquşurdu** | `tip` kontekstli: `tip AD =` elandır, qalan hallarda funksiya |
| 12 | `yeni X(...).üzv()` ayrılmırdı | `yeni`-dən sonra postfiks zənciri davam edir |
| 13 | `[1..3]` dilim yerinə Diapazon kimi oxunurdu | İndeks mövqeyində prioritet 8-dən başlanır |
| 14 | `a?.metod()` ixtiyari zənciri çağırışa yayılmırdı | `_e_çağırış`-da ixtiyari üzv yoxlanılır |
| 15 | EOF-da `oxu()` boş sətir qaytarıb `həmişə` dövrünü sonsuz fırladırdı | `GirişÇıxışXətası` atır (Python `input()` kimi) |
| 16 | Struktur dəyərlə kopyalanmırdı | Mənimsətmə və arqument ötürülməsində `klonla()` |
| 17 | `onluq` parametrə `3` verildikdə `3` qalırdı | İmplisit genişlənmə `tam` → `onluq` |
| 18 | Python `RecursionError` bizim `StekDaşmaXətası`-dan əvvəl baş verirdi | `setrecursionlimit(30000)`, STEK_HƏDDİ = 1000 |
| 19 | `genişlət mətn` daxilində `__sinif__` AttributeError verirdi | Daxili tiplərdə `sinif` sahəsi yoxdur — yoxlanılır |

### REPL mərhələsində tapılanlar (düzəldilib)

| # | Problem | Həll |
|---|---|---|
| 20 | **`1 ~/ 0` leksik xəta verirdi** — `"" in "xXbBoO"` Python-da **doğru** qaytarır, ona görə sətir sonundaki `0` onaltılıq prefiks sayılırdı | Üzvlük yoxlamaları kortejlə: `in ("x", "X", ...)`. `_gör()` sənədləşməsinə xəbərdarlıq əlavə edildi |
| 21 | `_` son nəticə dəyişəni ola bilməz — o, atma tokenidir (OP) | `nəticə` dəyişəni işlədilir |
| 22 | Üzv adında ASCII yazılanda (`siyahı.cem()`) səbəb izah olunmurdu | Xəta mesajı düzgün adı təklif edir və ASCII çevrilməsinin yalnız açar sözlərə aid olduğunu izah edir |

---

## Tip yoxlayıcı — dizayn qərarları

**Əsas prinsip:** yanlış xəbərdarlıq verən yoxlayıcı heç yoxlayıcıdan
pisdir. Ona görə `istənilən` və naməlum tiplər bütün yoxlamaları keçir —
yalnız ƏMİN OLDUĞUMUZ halda xəta bildirilir.

7 nümunə proqramda **0 yanlış xəbərdarlıq** (yalnız `veb`/`pəncərə`
modullarının yoxluğu bildirilir — bu, doğrudur).

| Rejim | Davranış |
|---|---|
| `sərbəst` | Yalnız açıq yazılmış tiplər yoxlanılır |
| `normal` | Çıxarma + yoxlama (standart) |
| `sərt` | Açıq funksiya imzaları məcburi, naməlum üzvlər xətadır |

Rejim `layihe.alqor` → `[tip] rejim`, və ya `--rejim` bayrağı ilə.

**Tutulan 25 xəta kodu:** ALQ-T001 (tip uyğunsuzluğu), T002 (naməlum
tip), T003/T004 (arqument sayı/tipi), T005 (qaytarma), T006 (naməlum
üzv + ASCII təklifi), T007 (şərt `məntiq` olmalıdır), T008 (operator),
T009 (indeks/iterasiya), T012 (`boş` mənimsətmə), T013 (yoxlanmamış
ixtiyari), T014 (çevrilmə), T015 (lazımsız yoxlama), T020 (sabit),
T022 (təyin edilməmiş + oxşar ad təklifi), T023 (təkrar elan),
T024 (istifadəsiz), T025 (çatılmayan kod), T026 (kölgələmə),
T031 (`seç` tamlığı), T040 (qaytarma yolu), T052 (mücərrəd),
T053 (komponent), T080 (sərt rejim), P008/P009 (dövr), P013 (`gözlə`),
M001/M002 (modul).

**Axın əsaslı daralma:**

```alqor
əgər x tipidir mətn onda
    yaz(x.böyüyə())           // x burada `mətn`

əgər a boşdur onda qaytar son
yaz(a.böyüyə())               // a burada ixtiyari deyil

varsa d = tap() onda
    yaz(d.böyüyə())           // d burada açılmış
```

`deyil (...)`, `və`, `və ya`, `== boş`, `!= boş`, və **çıxan budaqdan
sonra əks daralma** dəstəklənir.

---

## `veb` modulu — nə işləyir

| Sahə | Vəziyyət |
|---|---|
| Marşrutlar | `al` `göndər` `yenilə` `yamaq` `sil` `hamısı` |
| Naxışlar | `/i/:id` · `/m/:slug?` (ixtiyari) · `/f/*yol` (joker) |
| Qruplar | `s.qrup("/api", funksiya(q) … son)` |
| Ara proqramlar | qlobal + marşruta xas; `növbəti(sorğu)` zənciri |
| Hazır ara proqramlar | `jurnal` `CORS` `sıxma` `təhlükəsizlikBaşlıqları` `sessiya` `sürətLimiti` |
| Cavablar | `mətn` `html` `json` `boş` `yönləndir` `xəta` `fayl` `yüklə` `şablon` |
| Sorğu | parametrlər, sorğu sətri, başlıqlar, kukilər, JSON, form, IP |
| Sessiya | kuki əsaslı, yaddaşda; `al` `qoy` `sil` `təmizlə` `ehtiva` |
| Statik fayllar | MIME təyini + qovluqdan qaçmanın qarşısının alınması |
| Şablonlar | `.alqorhtml` — `{{ ifadə }}` `{% əgər %}` `{% hər %}` `{% blok %}` `{% genişlət %}` `{% daxilEt %}` |
| Şablon filtrləri | `böyüyə` `kiçiyə` `kəs` `uzunluq` `yuvarlaqlaşdır` `pul` `format` `standart` `tərs` `latınla` `URLKodla` `xam` |
| Təhlükəsizlik | avtomatik HTML qaçışı; yolda `../` rədd edilir |
| Sınaq | `veb.sınaq.server(s)` — port açmadan sorğu göndərir |

Şablon içindəki `{{ … }}` **həqiqi Alqor ifadəsidir** — eyni lekser,
parser və interpretator işləyir, ayrı şablon dili yoxdur.

---

## `pəncərə` modulu — desktop

**Arxitektura: yerli server + yerli pəncərə (Tauri modeli).**
Komponentin `göstər()` metodu JSX qaytarır, JSX isə artıq HTML-ə
çevrilir — deməli desktop üçün ayrı düzülüş mühərriki lazım deyil.
HTML-i `127.0.0.1`-dəki yerli server verir, onu yerli pəncərə göstərir.

Aparıcı bu sıra ilə seçilir:

| # | Aparıcı | Şərt |
|---|---|---|
| 1 | `pywebview` | quraşdırılıbsa — həqiqi yerli pəncərə |
| 2 | Chrome/Edge/Brave `--app=` | **standart** — asılılıq yoxdur |
| 3 | Sistem brauzeri | son çarə |
| 4 | Başsız | `ALQOR_BASSIZ=1`, `--başsız`, ekransız Linux, CI |

**Hadisələr əsas sapda işləyir.** Brauzer `/_alqor/hadise`-yə POST
göndərir, server sapı işi növbəyə qoyub cavab gözləyir, növbəni isə
`pəncərə.işlət()` — əsas sap — boşaldır. Nəticə: idarəedicilər arasında
vəziyyət yarışı olmur və `dialoq.*` tkinter dialoqlarını əsas sapdan
çağırır (tkinter bunu tələb edir).

| Sahə | Vəziyyət |
|---|---|
| Pəncərə | `başlıq` `məzmun` `üslub` `ölç` `mərkəzə` `ölçüsüSabit` `göstər` `bağla` `gözlə` `yenilə` `ünvan` |
| Məzmun | sabit element · `<Komponent />` (vəziyyət dəyişəndə özü yenilənir) · funksiya |
| Menyu | `pəncərə.menyu` `element` `ayırıcı`; qısayollar, işarə, sönük element |
| Hadisələr | 15 hadisə: `klik` `ikiKlik` `dəyişdi` `yazıldı` `göndərildi` `fokus` … |
| Dialoqlar | `təsdiqlə` `xəbərdarlıq` `məlumat` `xəta` `soruş` `faylAç` `faylAçHamısı` `faylSaxla` `qovluqSeç` `rəngSeç` |
| Bildiriş | `notify-send` (Linux) · AppleScript (macOS) · toast (Windows) |
| Sınaq | `pəncərə.sınaq.aç(p)` — pəncərə açmadan düymə basır, HTML oxuyur |

Dialoqlar tkinter ilə işləyir (standart kitabxana). `python3-tk`
quraşdırılmayıbsa və ya başsız rejimdədirsə `pəncərə.sınaq.cavablar([…])`
növbəsindən cavab götürülür — buna görə dialoqlu kod da sınanıla bilir.

---

## 🟡 AÇIQ QALAN MƏSƏLƏLƏR

### 1. `hər x üçün siyahı içində` söz sırası

Qrammatik cəhətdən tam təbii deyil (təbii forma "siyahıdakı hər x üçün",
amma `-dakı` şəkilçisi açar söz ola bilmir — `gətir ...dan` ilə eyni
səbəb). Lekser və parser hazırda yalnız bu formanı dəstəkləyir.
Alternativ `siyahı içində hər x üçün` da əlavə edilə bilər.

### 2. `5.` yazılışı

Spesifikasiya § 1.9.2 bunu xəta adlandırır, lekser isə `TAM(5)` + `OP(.)`
buraxır (çünki `5.mətnƏt()` işləməlidir). Spesifikasiya düzəldilməlidir.

### 3. Tip yoxlayıcısının əhatəsi

Standart kitabxananın ~280 funksiyasından təxminən 200-ü imzalıdır.
Qalanlar `?` (naməlum) qaytarır — bu, YANLIŞ XƏBƏRDARLIQ vermir, sadəcə
həmin yerlərdə yoxlama aparılmır. `sərt` rejimdə naməlum üzvlər xəta
sayılır, ona görə həmin rejim hələ tam istifadəyə hazır deyil.

### 4. Generiklər tam yoxlanılmır

`funksiya ilk[T](s: siyahı[T]) -> T?` ayrılır və `T` generik parametr
kimi tanınır, amma tip arqumentləri çıxarılmır — `T` hər şeyə uyğun
gəlir. Düzgün həll: unifikasiya alqoritmi.

---

## Növbəti addımlar

| # | İş | Həcm |
|---|---|---|
| 1 | **`vidjet`** — hazır UI elementləri (veb + desktop, tək mənbə) | ~900 sətir |
| 2 | `alqorfmt` (formatter + `--ascii-düzəlt`) | ~400 sətir |
| 3 | `alqor yeni` / `qur` / `sına` / `sənəd` əmrləri | ~500 sətir |
| 4 | `alqorls` (LSP serveri → VS Code) | ~700 sətir |
| 5 | Qalan standart kitabxana modulları (`http`, `verilənlər`, …) | böyük |
| 6 | `alqor qur` → installer (`.deb`/`.rpm`/AppImage/`.exe`) | böyük |
| 7 | Mərhələ 6 — JS/WASM transpilyator | böyük |
| 8 | `alqorpm` + `alqorhub` (paket meneceri və reyestr) | böyük |
| 9 | **Alqor Studio** (redaktor) — vidjet paleti + iki klikdə kod | böyük |
| 10 | Rust-a köçürmə (istehsal kompilyatoru) | çox böyük |

### `vidjet` və Alqor Studio — tələb

İstifadəçi tələbi: hazır elementlər (form, düymə, tərəqqi çubuğu,
cədvəl, nişan, modal…) **həm veb, həm desktop** üçün eyni mənbədən
işləməlidir. Alqor Studio-da element əlavə edildikdən sonra **üzərinə
iki dəfə klikləmək** o elementin işləməsi üçün lazım olan kodu
(hadisə idarəedicisi, vəziyyət sahəsi, `gətir` sətri) avtomatik
yazmalıdır. Hər vidjetin yanında bu "kod skeleti" şablonu saxlanılır.

Mühit vəziyyəti (Rust, Zig, WSL): [../MUHIT.md](../MUHIT.md)
