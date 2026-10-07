# Alqor kompilyatoru — iş vəziyyəti

> Etalon implementasiya, **Python 3.12**. Son yenilənmə: 6 oktyabr 2026

**Mərhələ 1–5 BİTDİ** — dil nüvəsi tamamdır:
lekser · parser · interpretator · standart kitabxana · REPL ·
**JSX** · **tənbəl generatorlar** · **asinxron icra** ·
**statik tip yoxlayıcı** · **veb server + şablon** · **desktop** ·
**118 hazır vidjet** (veb və desktopda interaktiv) · **`konsol`** ·
**Alqor Studio (IDE)**

**1048 sınaq keçir** (Studio-nun 5 brauzer sınağı Playwright ilə
ayrıca). 10 nümunə proqramın **hamısı** ayrılır, tip yoxlamasından
keçir və icra olunur. Bələdçinin 3 dərsliyindəki hər tam proqram
avtomatik icra olunur (`test_beledci.py`).

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
│   ├── pencere.py        desktop: pəncərə, menyu, dialoq, hadisə dövrü;
│   │                     brauzer nüvəsi (DOM yamağı + hadisə növbəsi)
│   ├── vidjet.py         118 hazır interfeys elementi + IDE kataloqu (+ vidjet_elave.py)
│   ├── vidjet_arayis.py  spesifikasiya § 14.7-ni koddan qurur
│   ├── konsol.py         rəng, sual-cavab, irəliləyiş, arqumentlər
│   ├── alqorfmt.py       formatlayıcı (§ 13.3) — `alqorfmt.py` / `format`
│   ├── alqorls.py        LSP serveri (§ 13.8) — `alqor ls --stdio`
│   ├── modullar/         əlavə standart modullar (§ 10.17), tənbəl yüklənir
│   ├── qrammatika.py     VS Code TextMate qrammatikası (açar sözlərdən)
│   ├── layihe.py         `layihe.alq` parseri + `yeni` şablonları
│   ├── sinaqci.py        `test` modulu + `sına` işlədicisi
│   ├── senedci.py        `sənəd` — HTML/Markdown API sənədi
│   └── qurucu.py         `qur` — tək fayllı `.pyz` paket
├── studio/               Alqor Studio — IDE (README.md-yə baxın)
└── sinaq/
    ├── test_elifba.py        (31)
    ├── test_menbe.py         (34)
    ├── test_lekser.py        (70)
    ├── test_icraci.py        (150)  parser + interpretator + JSX
    ├── test_sohbet.py        (45)   REPL
    ├── test_korutin.py       (43)   generatorlar + asinxron
    ├── test_tipyoxlayici.py  (83)   tip yoxlayıcı
    ├── test_veb.py           (69)   server + marşrut + şablon
    ├── test_pencere.py       (84)   pəncərə + menyu + dialoq + CSRF
    ├── test_vidjet.py        (129)  vidjetlər + kataloq + § 14 sinxronu
    ├── test_konsol.py        (25)   konsol + zəncir + açar söz etiketi
    ├── test_studio.py        (78)   IDE: skelet, API, təhlükəsizlik, UI
    ├── test_beledci.py       (3)    dərsliklərdəki bütün kod işləyir
    ├── test_alqorfmt.py      (32)   formatlayıcı + doğrulama + CLI
    ├── test_alqorls.py       (36)   LSP: protokol, naviqasiya, tamamlama, qrammatika
    ├── test_modullar.py      (48)   12 modul: format, şifrə (NIST), http, verilənlər, şəbəkə
    └── test_layihe.py        (27)   manifest, yeni, sına, sənəd, qur
```

## İşə salmaq

```bash
cd alqorc

python alqorc.py söhbət                          # interaktiv rejim
python alqorc.py tip ../numuneler                # tip yoxlaması
python alqorc.py işlət fayl.alq --tip          # icradan əvvəl yoxla
python sina.py --nümunələr                       # 1048 sınaq + nümunələr
python alqorc.py işlət ../numuneler/02-dovrler.alq
python alqorc.py işlət ../numuneler/04-siniflər.alq
python alqorc.py tokenlər ../numuneler/01-salam.alq
python alqorc.py yoxla ../numuneler
python alqorc.py hərf "ışıq İmran"

# Veb server
python alqorc.py işlət ../numuneler/05-veb-server.alq          # port 8080
python alqorc.py işlət ../numuneler/05-veb-server.alq -- sınaq # port açmadan

# Desktop tətbiq
python alqorc.py işlət ../numuneler/06-desktop.alq             # pəncərə açır
python alqorc.py işlət ../numuneler/06-desktop.alq -- sınaq    # başsız

# Hazır vidjetlər — eyni kod hər üç hədəfdə
python alqorc.py işlət ../numuneler/08-vidjetler.alq           # desktop
python alqorc.py işlət ../numuneler/08-vidjetler.alq -- veb    # veb :8081
python alqorc.py işlət ../numuneler/08-vidjetler.alq -- sınaq  # başsız
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
| Aparıcı nöqtə ilə çoxsətirli zəncir (`.metod()` yeni sətirdə) | ✅ |
| Açar söz adlı arqument etiketi (`standart:`, `sinif:`) | ✅ |
| Ox funksiyasında mənimsətmə (`() => özü.say += 1`) | ✅ |
| `tut x` — istənilən xətanı bağlayır | ✅ |
| Qısa qurucudan sonra üzvlər (girinti qaydası, § 6.3.1) | ✅ |

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

Rejim `layihe.alq` → `[tip] rejim`, və ya `--rejim` bayrağı ilə.

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

## `vidjet` modulu — hazır elementlər

**Bir mənbə, iki hədəf.** Hər vidjet `Element` (JSX ağacı) qaytarır;
həmin ağacı `veb` brauzerə HTML kimi, `pəncərə` isə desktop
pəncərəsinə göstərir. Form, cədvəl, tərəqqi çubuğu — hamısı hər iki
hədəfdə eyni kodla işləyir.

| Kateqoriya | Vidjetlər |
|---|---|
| **form** (21) | `düymə` `ikonDüymə` `düyməQrupu` `əlaqə` `sahə` `parol` `ədəd` `axtarış` `çoxsətirli` `seçim` `qeyd` `açar` `radioQrupu` `sürüşdürücü` `tarix` `vaxt` `rəng` `faylSahəsi` `form` `sahəDəsti` `etiket` |
| **göstərmə** (14) | `başlıq` `mətn` `nişan` `xəbərdarlıq` `kart` `cədvəl` `siyahı` `təsvirSiyahısı` `kod` `sitat` `şəkil` `avatar` `ayırıcı` `boşBaxış` |
| **vəziyyət** (5) | `tərəqqi` `halqaTərəqqi` `fırlanan` `skeletYüklənmə` `statistika` |
| **düzülüş** (7) | `qutu` `sətir` `sütun` `tor` `boşluq` `panel` `bölmə` |
| **naviqasiya** (6) | `naviqasiya` `nişanlar` `yığcam` `səhifələmə` `addımlar` `çörəkQırıntıları` |
| **üst qat** (4) | `modal` `yanPanel` `ipucu` `bildirişQutusu` |

Üslub: `vidjet.üslub()` CSS mətni, `vidjet.üslublar()` `<style>`
elementi, `vidjet.səhifə(...)` tam HTML sənədi. Desktopda `pəncərə`
üslubu özü əlavə edir. Açıq/qaranlıq rejim CSS dəyişənləri ilə.

### IDE kataloqu — iki klikdə kod

`vidjet.kataloq()` hər elementin adını, kateqoriyasını, hadisələrini,
istifadə nümunəsini və **kod skeletini** qaytarır. Alqor Studio bunu
oxuyacaq: paletdən element əlavə edilir, üzərinə iki dəfə
klikləndikdə `vidjet.skelet(ad, dəyişənAdı)` qaytardığı kod redaktora
yazılır və element dərhal işləyir.

```
vidjet.skelet("sahə", "istifadəçiAdı")
→ vəziyyət istifadəçiAdı: mətn = ""
→
→ metod istifadəçiAdıDəyişdi(dəyər: mətn)
→     özü.istifadəçiAdı = dəyər
→ son
```

Kataloq **tək həqiqət mənbəyidir**: modulun ixrac etdiyi vidjetlərin
siyahısı, tip imzaları və sınaqlar hamısı ondan qurulur. Sınaqlar hər
nümunənin və hər skeletin həqiqətən ayrıldığını yoxlayır.

---

### Spesifikasiya § 12–14 və bələdçi yazılarkən tapılanlar (düzəldilib)

Sənəd yazmaq üçün hər nümunəni işlətdik — kod sənədlə uyğun gəlmədikdə
kodu düzəltdik (və ya spesifikasiyanı, əgər o səhv idisə).

| # | Problem | Həll |
|---|---|---|
| 23 | **Vebdə vidjet hadisələri işləmirdi** — düymə görünür, `klik` səssizcə atılırdı | `s.komponent(yol, Sinif)` — sessiya başına nümunə |
| 24 | **Yazarkən fokus və hərflər itirdi** (desktop və veb) — kök `innerHTML` ilə əvəzlənir, sorğu gedərkən hadisələr atılırdı | DOM yamağı + hadisə növbəsi; gözləyən sahəyə yamaq toxunmur |
| 25 | Desktopda vidjetlər üslubsuz idi | `pəncərə` vidjet CSS-ini qoşur |
| 26 | **CSRF** — istənilən sayt `text/plain` POST ilə yerli serverdə düymə basa bilərdi; DNS rebinding | `Origin` + `Host` yoxlaması; vebdə JSON + `SameSite=Strict` |
| 27 | Statik fayl: `str.startswith` qonşu qovluğu (`statik-gizli`) keçirirdi; 404 hücum yolunu əks etdirirdi | `is_relative_to`; `..`, `\`, `//`, NUL 400 alır |
| 28 | IDE skeletləri `tamEn` tipi yazırdı (toplu ad dəyişikliyi) | düzəldildi; skeletlər tip yoxlamasından keçir |
| 29 | Qısa qurucudan sonra `göstər()` gövdəyə düşür, `son` sinfi bağlayırdı | girinti qaydası (§ 6.3.1) |
| 30 | JSX `{…}`, mətn `"{…}"` və şablon `{{ … }}` artıq tokenləri səssizcə atırdı | xəta + CSS üçün xam mətn məsləhəti |
| 31 | `sistem.arqumentlər()` `["işlət", "fayl.alq", …]` qaytarırdı | proqramın öz arqumentləri |
| 32 | `konsol.soruş` `input()`-u birbaşa çağırırdı — sınaqda işləmirdi | icraçının giriş axını |
| 33 | `tut x` — `x` gövdənin ilk cümləsi sayılırdı | istənilən xətanı bağlayır |
| 34 | Şablonda uşaq blokun xətası valideynin faylı ilə bildirilirdi; blok və ifadə keşi toqquşurdu | qovşaq faylı daşıyır; iki keş |
| 35 | Sınaq sürücüsü qutucuğa `"doğru"` mətni göndərirdi; cədvəl sətrini tapa bilmirdi | brauzer kimi `məntiq`; başlanğıc uyğunluğu |
| 36 | `cədvəl(sətirKlik:)` hansı sətrin basıldığını ötürmürdü | sətir indeksi |
| 37 | Spesifikasiya `veb.ön`, `p.ölçü`, `faylAçÇoxlu`, WebKitGTK təsvir edirdi | § 12 həqiqi API ilə; olmayanlar "planlaşdırılır" |
| 38 | `gətir "./x.alq"` prosesin cari qovluğuna nisbətən axtarılırdı | idxal edən fayla nisbətən; keş icraçıya bağlı |
| 39 | `ixrac et` olan elanın `///` sənədi itirdi; `//!` ilk `///` ilə birləşirdi; sənəddəki kodun girintisi silinirdi | sənəd elan açar sözünə bağlanır |
| 40 | `@annotasiya modul …` səssizcə atılırdı | `ModulElanı.annotasiyalar` |
| 41 | Kitabxana funksiyasının xətası yersiz çap olunurdu | çağırışın yeri qoşulur |
| 42 | `işlət f.alq -- --tip` tip yoxlamasını işə salırdı | `--`-dan sonrası proqramındır |

## 🟡 AÇIQ QALAN MƏSƏLƏLƏR

### 1. `hər x üçün siyahı içində` söz sırası

Qrammatik cəhətdən tam təbii deyil (təbii forma "siyahıdakı hər x üçün",
amma `-dakı` şəkilçisi açar söz ola bilmir — `gətir ...dan` ilə eyni
səbəb). Lekser və parser hazırda yalnız bu formanı dəstəkləyir.
Alternativ `siyahı içində hər x üçün` da əlavə edilə bilər.

### 2. `5.` yazılışı

Spesifikasiya § 1.9.2 bunu xəta adlandırır, lekser isə `TAM(5)` + `OP(.)`
buraxır (çünki `5.mətnƏt()` işləməlidir). Spesifikasiya düzəldilməlidir.

### ✅ Həll olundu (3–5)

- **Tip yoxlayıcısının əhatəsi** — icrada olan hər modul üzvünün, daxili
  tip metodunun və kitabxana obyektinin imzası var; `sərt` rejim real
  kodda yanlış xəta vermir. `SərtRejimƏhatəsi` sınağı bunu qoruyur.
- **Generiklər** — `f[T](…)` çağırışında `T` unifikasiya ilə çıxarılır,
  ziddiyyət ALQ-T004, lambda parametrləri kontekstdən tip alır.
- **Modul tipləri annotasiyada** — `pəncərə.Pəncərə`, `http.Sorğu`.

---

## Növbəti addımlar

| # | İş | Həcm |
|---|---|---|
| ✅ | Spesifikasiya § 14, § 12–13 uzlaşması, 3 dərslik, Alqor Studio | — |
| ✅ | `alqorfmt` — parserdən girinti, doğrulama zəmanəti, Studio-da Ctrl+Shift+F | — |
| ✅ | `yeni` (4 şablon) / `sına` / `sənəd` / `qur` (`.pyz`) / `təmizlə` | — |
| ✅ | `alqorls` (LSP) + VS Code genişlənməsi, TextMate qrammatikası | — |
| ◐ | Standart kitabxana: ✅ kodlaşdırma, csv, toml, yaml, xml, html, konfiq, sıxma, şifrə, http, şəbəkə, verilənlər; qalır: şəkil, poçt, keş, növbə, planlayıcı, validasiya, lokalizasiya, pul, qrafik, pdf, ffi | böyük |
| 6 | `alqor qur` → installer (`.deb`/`.rpm`/AppImage/`.exe`) | böyük |
| 6a | **Alqor Studio — installerli Desktop tətbiqi** (istifadəçi tələbi): Windows `.exe` quraşdırıcı (Başlat menyusu, masaüstü ikonu, `.alq` faylları Studio ilə açılır), Linux `.deb`/AppImage, macOS `.dmg`; Python daxildədir — ayrıca quraşdırmaq lazım deyil | böyük |
| 7 | Mərhələ 6 — JS/WASM transpilyator | böyük |
| 8 | `alqorpm` + `alqorhub` (paket meneceri və reyestr) | böyük |
| ✅ | Alqor Studio: vidjet miniatürləri, Xüsusiyyətlər paneli (üslub, mətn, növ …), canlı önbaxış | — |
| 9 | Alqor Studio: avtomatik tamamlama (alqorls-dan), sürüklə-burax düzülüş | orta |
| 10 | Rust-a köçürmə (istehsal kompilyatoru) | çox böyük |

### `vidjet` və Alqor Studio — tələb

İstifadəçi tələbi: hazır elementlər (form, düymə, tərəqqi çubuğu,
cədvəl, nişan, modal…) **həm veb, həm desktop** üçün eyni mənbədən
işləməlidir. Alqor Studio-da element əlavə edildikdən sonra **üzərinə
iki dəfə klikləmək** o elementin işləməsi üçün lazım olan kodu
(hadisə idarəedicisi, vəziyyət sahəsi, `gətir` sətri) avtomatik
yazmalıdır. Hər vidjetin yanında bu "kod skeleti" şablonu saxlanılır.

Mühit vəziyyəti (Rust, Zig, WSL): [../MUHIT.md](../MUHIT.md)
