# Alqor kompilyatoru — iş vəziyyəti

> Etalon implementasiya, **Python 3.12**. Son yenilənmə: 5 oktyabr 2026

**Mərhələ 1–4 BİTDİ** (lekser, parser, interpretator, standart kitabxana)
**+ `alqor söhbət` (REPL) tam hazırdır.**

**304 sınaq keçir.** 7 nümunə proqramın hamısı ayrılır, 5-i icra olunur
(05 veb modulunu, 06 JSX-i gözləyir).

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
│   ├── kitabxana.py      standart kitabxana (13 modul, ~250 funksiya)
│   └── sohbet.py         interaktiv rejim (REPL) — 18 meta-əmr
└── sinaq/
    ├── test_elifba.py    (31)
    ├── test_menbe.py     (34)
    ├── test_lekser.py    (70)
    ├── test_icraci.py    (124)  parser + interpretator
    └── test_sohbet.py    (45)   REPL
```

## İşə salmaq

```bash
cd alqorc

python alqorc.py söhbət                          # interaktiv rejim
python sina.py --nümunələr                       # 304 sınaq + nümunələr
python alqorc.py işlət ../numuneler/02-dovrler.alqor
python alqorc.py işlət ../numuneler/04-siniflər.alqor
python alqorc.py tokenlər ../numuneler/01-salam.alqor
python alqorc.py yoxla ../numuneler
python alqorc.py hərf "ışıq İmran"
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
| JSX interfeys sintaksisi | ✖ Mərhələ 2b |
| Tip yoxlayıcı (statik) | ✖ Mərhələ 5 |

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

## 🟡 AÇIQ QALAN MƏSƏLƏLƏR

### 1. JSX mətn məzmunu kontekstsiz leksə oluna bilmir ❗

```alqor
<button klik={özü.azalt}>-</button>
```
JSX mətn uşağında istənilən simvol qanunidir, amma lekser kontekstsizdir.

**Həll yolu (Mərhələ 2b):** parser `<` görəndə mənbə mətnini birbaşa
oxuyur (onun `Mənbə` obyektinə girişi var), JSX elementini xam skan edir,
daxildəki `{ifadə}` üçün həmin ofsetdən yeni `Lekser` qurur, sonra
token indeksini elementin sonuna sürüşdürür. Lekser rejimlərinə ehtiyac
qalmır.

### 2. `hər x üçün siyahı içində` söz sırası

Qrammatik cəhətdən tam təbii deyil (təbii forma "siyahıdakı hər x üçün",
amma `-dakı` şəkilçisi açar söz ola bilmir — problem №1 ilə eyni səbəb).
Lekser və parser hazırda yalnız bu formanı dəstəkləyir. Alternativ
`siyahı içində hər x üçün` da əlavə edilə bilər.

### 3. Tənbəl generatorlar

`ver` hazırda bütün dəyərləri əvvəlcədən yığır — sonsuz generatorlar
(`fibonaççi()`) işləmir. Düzgün həll: Python `yield`-i ilə korutin, və ya
icraçının davamlılıq (continuation) üslubunda yazılması.

### 4. `asinxron` / `gözlə`

Sintaksis ayrılır, amma `gözlə` sinxron icra edir. Hadisə dövrü
Mərhələ 3b-də.

### 5. `5.` yazılışı

Spesifikasiya § 1.9.2 bunu xəta adlandırır, lekser isə `TAM(5)` + `OP(.)`
buraxır (çünki `5.mətnƏt()` işləməlidir). Spesifikasiya düzəldilməlidir.

---

## Növbəti addımlar

| # | İş | Həcm |
|---|---|---|
| 1 | **Mərhələ 5 — tip yoxlayıcı** (tədrici tiplər, axın daralması) | ~1200 sətir |
| 2 | Mərhələ 2b — JSX (yuxarıdaki yanaşma ilə) | ~400 sətir |
| 3 | Tənbəl generatorlar + hadisə dövrü | ~500 sətir |
| 4 | `veb` modulu (server) — 05 nümunəsini işlətmək üçün | ~800 sətir |
| 5 | Mərhələ 6 — JS transpilyator | böyük |
| 6 | Rust-a köçürmə (istehsal kompilyatoru) | çox böyük |

Mühit vəziyyəti (Rust, Zig, WSL): [../MUHIT.md](../MUHIT.md)
