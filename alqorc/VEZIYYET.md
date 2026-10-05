# Alqor kompilyatoru — iş vəziyyəti

> Etalon implementasiya, **Python 3.12**. Sonra Rust-a köçürüləcək.
> Son yenilənmə: 5 oktyabr 2026

**Mərhələ 1 (lekser) BİTDİ.** 135 sınaq, 7 nümunə proqram — hamısı keçir.

---

## Fayl quruluşu

```
alqorc/
├── alqorc.py            CLI
├── sina.py              sınaq işlədicisi
├── alqor/
│   ├── elifba.py         az-AZ hərf qaydaları, əlifba sırası, ahəng qanunu
│   ├── homoqlif.py       oxşar simvolların aşkarlanması
│   ├── acar_sozler.py    açar söz cədvəli
│   ├── token.py          Token, Yer, şablon mətn parçaları
│   ├── xeta.py           Diaqnostika, XətaToplayıcı, çərçivəli hesabat
│   ├── menbe.py          UTF-8, NFC, sətir/sütun xəritəsi
│   └── lekser.py         lekser
└── sinaq/
    ├── test_elifba.py    (31 sınaq)
    ├── test_menbe.py     (34 sınaq)
    └── test_lekser.py    (70 sınaq)
```

## İşə salmaq

```bash
cd alqorc

python sina.py --nümunələr              # bütün sınaqlar + nümunələr
python alqorc.py tokenlər ../numuneler/01-salam.alqor
python alqorc.py yoxla ../numuneler
python alqorc.py hərf "ışıq İmran"
python alqorc.py sırala zəfər ağac çay ışıq ilk
```

---

## Təsdiqlənmiş nəticələr

```
böyüyə("ışıq") → "IŞIQ"      (Python standartı: "IŞIK"  ✖)
böyüyə("i")    → "İ"         (Python standartı: "I"     ✖)
kiçiyə("I")    → "ı"         (Python standartı: "i"     ✖)
böyüyə("imran")→ "İMRAN"     (Python standartı: "IMRAN" ✖)

Əlifba sırası:
  Alqor  : ağac, çay, ev, əlif, göl, ışıq, ilk, şam, zəfər   ✓
  Python : ağac, ev, göl, ilk, zəfər, çay, ışıq, şam, əlif   ✖

kanonikləşdir("eger")        → ("əgər", ASCII idi)
kanonikləşdir("ne qeder ki") → ("nə qədər ki", ASCII idi)
kanonikləşdir("yas")         → None   ← identifikatorda çevrilmə YOXDUR ✓

7 nümunə proqram: 1658 token, xəta yoxdur
```

---

## Lekserin verdiyi qərarlar (həyata keçirilib)

### Çox sözlü açar sözlər lekserdə birləşdirilir
Maksimal udma ilə bir `ACAR` tokenə çevrilir, kanonik forma boşluqla
saxlanılır: `nə qədər ki`, `digər hallarda`, `yoxsa əgər`, `əks halda`
(→ `yoxsa`), `davam et`, `cəhd et`, `ixrac et`, `əvəz et`, `və ya`,
`boş deyil`.

Birləşmə yalnız **eyni sətirdə** baş verir. Bu, bu konstruksiyanın
düzgün oxunmasını təmin edir:
```alqor
yoxsa                    ← `yoxsa` (else)
    əgər x onda ... son  ← ayrıca `əgər`
```

**Vacib sıra:** `QISA_ALIAS` (`davam` → `davam et`) birləşmə cəhdindən
**SONRA** tətbiq olunur (`AS.tamamla()`). Əks halda `davam` dərhal
`davam et`-ə çevrilir və lekser `davam` + `et` birləşməsini artıq tapa
bilmir (indeks ilk SÖZƏ görədir).

### Yeni sətir udulması
`SETIR_SONU` emissiya olunmur, əgər:
- mötərizə dərinliyi > 0, və ya
- son token operatordur (`)`, `]`, `}`, `!`, `++`, `--`, `?` istisna), və ya
- son token `DAVAM_ACAR_SOZLERI` dəstindədir (`və`, `və ya`, `kimi`,
  `onda`, `üçün`, `içində`, `miras` …)

Fayl sonunda SETIR_SONU **qəsdən** emissiya olunur — son ifadə də bitməlidir.

### Şablon mətnlər rekursiv leksə edilir
`"Salam, {ad}!"` → bir `METN` tokeni, `parçalar` sahəsində
`[MətnParçası("Salam, "), KodParçası([AD ad]), MətnParçası("!")]`.
İnterpolyasiya **yerində** leksə olunur, ona görə mövqelər düzgündür.
Format spesifikatoru (`{q:.2}`) `:`-dan sonra xam mətn kimi saxlanılır.

### `oxu`, `yaz` və digərləri açar söz DEYİL
`xassə sahə: onluq  oxu ... son` konstruksiyası onları tələb edir, amma
`yaz("salam")` funksiya çağırışıdır. Həll: **kontekstli söz** — lekser
`AD` buraxır, parser mövqeyə görə tanıyır. Eyni qayda: `vəziyyət`,
`hesablanan`, `əməl`, `hadisə`, `göstər`, `sınaq`, `ölç`, `sil`,
`panika`, `eynidir`.

### Ehtiyat sözlər yalnız müstəqil mövqedə xəbərdarlıq verir
`veb.makro(5)` — xəbərdarlıq yoxdur (`.`-dan sonra ad obyektin üzvüdür,
dilin açar sözü ola bilməz). `dəyişən makro = 5` — ALQ-L016.

### Diapazon və onluq ədəd qarışmır
`1..5` → `TAM(1) OP(..) TAM(5)`. Nöqtədən sonra **mütləq rəqəm** olmalıdır
ki, kəsr hissəsi sayılsın. Bu sayədə `5.mətnƏt()` də işləyir.

---

## 🔴 Kodun açdığı problemlər — HƏLL OLUNDU

### 1. `gətir riyaziyyatdan {kök}` işləmirdi ✅

`riyaziyyatdan` **bir identifikator tokenidir** — `-dan` şəkilçisini lekser
ayıra bilməz (`meydan`, `qazan`, `vətən` adlı modullar sınardı).

**Həll:** nöqtə-mötərizə sintaksisi
```alqor
gətir riyaziyyat                      // bütöv
gətir riyaziyyat kimi r               // ləqəb
gətir riyaziyyat.{Pİ, kök}            // seçmə
gətir riyaziyyat.{kök kimi k}         // ləqəbli seçmə
gətir riyaziyyat.*                    // hamısı
gətir "./riyazi.alqor".{kvadrat}      // yerli fayl
```
Dəyişdirilib: `spesifikasiya/08`, `qrammatika.ebnf`, `beledci/01`,
`beledci/05`, `beledci/06`, `acar-sozler.md`. `dan`/`dən` açar söz
siyahısından silinib.

### 2. `içində deyil` və `tipidir deyil` toqquşurdu ✅

`içində` for-each bağlayıcısıdır. **Həll:** ikisi də silindi, əvəzinə
```alqor
əgər deyil (x içindədir siyahı) onda ... son
əgər deyil (x tipidir mətn) onda ... son
```
`boşdur` / `boş deyil` cütü saxlanıldı.
Dəyişdirilib: `spesifikasiya/01` § 1.6, `02` § 2.9, `03` § 3.3.7,
`acar-sozler.md`, `qrammatika.ebnf`.

### 3. Mühit dəyişənlərində Azərbaycan hərfləri işləmir ✅

POSIX mühit dəyişəni adları yalnız `[A-Za-z_][A-Za-z0-9_]*` ola bilər.
**Həll:** adlar ASCII (`ALQOR_RENG`, `ALQOR_HEDEF`, `ALQOR_DIL`, …),
dəyərlər Azərbaycan dilində (`ALQOR_RENG=həmişə`).
Dəyişdirilib: `spesifikasiya/13` § 13.13.

### 4. Konsol kodlaşdırması ✅

Windows-da standart çıxış `cp1251`-dir və Azərbaycan hərflərini çap edə
bilmir — alət öz xəta mesajını göstərə bilmirdi (`UnicodeEncodeError`).
**Həll:** hər giriş nöqtəsi axınları UTF-8-ə keçirir.
Spesifikasiyaya yeni bölmə əlavə olundu: `13` § 13.15.

### 5. `şablon` ehtiyat sözü standart kitabxana ilə toqquşurdu ✅

`veb.şablon()` spesifikasiyada var, amma `şablon` ehtiyat siyahısında idi.
**Həll:** ehtiyat siyahısı 4 sözə qədər daraldıldı (`aktyor`, `ömür`,
`makro`, `təsir`) + üzv mövqeyində xəbərdarlıq verilmir.

### 6. Tire (`—`) səhvən homoqlif sayılırdı ✅

`// Nümunə 1 — Ən sadə proqram` sətrində `—` avtomatik `-`-ə çevrilirdi.
**Həll:** durğu işarələri (en/em dash, ağıllı dırnaqlar, `×`, `÷`)
homoqlif cədvəlindən çıxarıldı. Onlar şərhlərdə və mətn literallarında
qanunidir; kod mövqeyində görünsələr `ALQ-L002` verilir — bu, səssiz
"düzəliş"dən daha dürüstdür. Tam genişlikli çevrilmə yalnız hərf və
rəqəmlərə tətbiq olunur.

---

## 🟡 AÇIQ QALAN MƏSƏLƏLƏR

### 1. JSX mətn məzmunu kontekstsiz leksə oluna bilmir ❗

```alqor
<button klik={özü.azalt}>−</button>
```
`−` (MINUS SIGN) JSX mətn uşağıdır — orada istənilən simvol qanunidir.
Amma lekser kontekstsizdir və `ALQ-L002` verir.

**Həll yolu (Mərhələ 2):** TypeScript skanerindəki kimi **lekser rejimləri**.
Parser `<Ad ...>` açılışını gördükdən sonra lekseri `JSX_MƏTN` rejiminə
keçirir; `<` və `{` görənə qədər hər şey xam mətndir. Bu, parser ilə
sıx əlaqə tələb edir, ona görə parser yazılarkən həll olunacaq.

Müvəqqəti: `numuneler/06-desktop.alqor`-da `−` → `-`, `·` → `|` edildi.

### 2. `hər x üçün siyahı içində` — söz sırası

Qrammatik cəhətdən tam təbii deyil (təbii forma "siyahıdakı hər x üçün",
amma `-dakı` şəkilçisi açar söz ola bilmir — problem №1 ilə eyni səbəb).
Alternativ: `siyahı içində hər x üçün`.
Lekser hər ikisini dəstəkləyir (ikisi də sadəcə token ardıcıllığıdır) —
**qərar parser yazılarkən verilməlidir.**

### 3. `5.` yazılışı

Spesifikasiya § 1.9.2 bunu `ALQ-L006` xətası adlandırır, lekser isə
`TAM(5)` + `OP(.)` buraxır (çünki `5.mətnƏt()` və `nöqtə.0` işləməlidir).
Parser `.`-dan sonra ad və ya rəqəm gözləyəcək və öz xətasını verəcək.
Spesifikasiyanı buna uyğunlaşdırmaq lazımdır.

---

## Növbəti addımlar — Mərhələ 2 (parser)

| # | Fayl | Məzmun |
|---|---|---|
| 1 | `alqor/aac.py` | AAC (abstrakt sintaksis ağacı) qovşaqları |
| 2 | `alqor/parser.py` | Rekursiv enmə + Pratt (ifadələr üçün) |
| 3 | `alqor/parser_jsx.py` | Lekser rejimləri ilə JSX |
| 4 | `sinaq/test_parser.py` | |
| 5 | `alqorc.py` | `aac` əmri — ağacı göstərmək |

Prioritet sıra: ifadələr → ifadə prioriteti (19 səviyyə, `spesifikasiya/03`
§ 3.4) → cümlələr → elanlar → JSX.
