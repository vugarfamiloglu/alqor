# Alqor kompilyatoru — iş vəziyyəti

> Etalon implementasiya, **Python 3.12**. Sonra Rust-a köçürüləcək.
> Son yenilənmə: 5 oktyabr 2026

---

## Hazır olan

| Fayl | Nə edir | Vəziyyət |
|---|---|---|
| `alqor/__init__.py` | Paket | ✅ |
| `alqor/elifba.py` | 32 hərf, **az-AZ böyük/kiçik qaydaları**, əlifba sırası (collation), ahəng qanunu köməkçiləri, latınlaşdırma | ✅ sınaqdan keçdi |
| `alqor/homoqlif.py` | ~120 oxşar simvolun aşkarlanması və düzəldilməsi (kiril, yunan, `ä`→`ə`, görünməz simvollar, ağıllı dırnaqlar) | ✅ sınaqdan keçdi |
| `alqor/acar_sozler.py` | **105 sərt açar söz**, 12 kontekstli söz, 10 çox sözlü birləşmə, 60 ASCII əvəzləyici (avtomatik yaradılır) | ✅ sınaqdan keçdi |

### Təsdiqlənmiş nəticələr

```
böyüyə("ışıq") → "IŞIQ"      (Python standartı: "IŞIK"  ✖)
böyüyə("i")    → "İ"         (Python standartı: "I"     ✖)
kiçiyə("I")    → "ı"         (Python standartı: "i"     ✖)

Əlifba sırası:
  Alqor  : ağac, çay, ev, əlif, göl, ışıq, ilk, şam, zəfər   ✓
  Python : ağac, ev, göl, ilk, zəfər, çay, ışıq, şam, əlif   ✖

kanonikləşdir("eger")        → ("əgər", ASCII idi)
kanonikləşdir("ne qeder ki") → ("nə qədər ki", ASCII idi)
kanonikləşdir("yas")         → None   ← identifikatorda çevrilmə YOXDUR ✓
```

---

## Növbəti addımlar (sıra ilə)

| # | Fayl | Məzmun |
|---|---|---|
| 1 | `alqor/menbe.py` | `Mənbə` sinfi: UTF-8 oxuma (ALQ-L001), BOM, **NFC normalizasiya**, CRLF→LF, homoqlif düzəlişi, sətir/sütun xəritəsi |
| 2 | `alqor/xeta.py` | `Diaqnostika`, `XətaToplayıcı`, çərçivəli hesabat çapı (`┌─ │ ^^^ = kömək:`) |
| 3 | `alqor/token.py` | `Növ` enum, `Token`, `Yer`, `MətnParçası` / `KodParçası` (şablon mətn) |
| 4 | `alqor/lekser.py` | Əsas lekser |
| 5 | `alqor.py` | CLI: `tokenler`, `yoxla`, `herf`, `versiya` |
| 6 | `sinaq/` | `unittest` — xarici asılılıq yoxdur |

---

## ⚠ MÜTLƏQ: stdout kodlaşdırması

Bu maşında Python-un standart çıxışı **cp1251**-dir və Azərbaycan hərflərini
çap edə bilmir (`UnicodeEncodeError`). Hər giriş nöqtəsinin **ilk sətri**:

```python
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

Bu olmadan dil öz xəta mesajını çap edə bilmir. Rust versiyasında da
Windows konsolu üçün eyni problem var (`SetConsoleOutputCP(65001)`).

---

## Lekser üçün artıq verilmiş qərarlar

### Çox sözlü açar sözlər lekserdə birləşdirilir
Maksimal-udma ilə bir `ACAR` tokenə çevrilir, kanonik forma boşluqla saxlanır:
`nə qədər ki`, `digər hallarda`, `yoxsa əgər`, `əks halda`, `davam et`,
`cəhd et`, `ixrac et`, `əvəz et`, `və ya`, `boş deyil`.
Cədvəl: `acar_sozler.COX_SOZLU_INDEKS` (ilk sözə görə indeksli).

### Yeni sətir udulması (Spes. § 1.11)
`SETIR_SONU` tokeni **yalnız** mötərizə dərinliyi 0 olanda emissiya olunur.
Əlavə olaraq, son emissiya olunmuş token operatordursa (`)`, `]`, `}`,
`!`, `++`, `--`, `?` istisna) və ya `acar_sozler.DAVAM_ACAR_SOZLERI`
dəstindədirsə, sətir sonu udulur.
Parser `SETIR_SONU` yığınlarını boş ifadə kimi atlayır.

### Şablon mətnlər rekursiv leksə edilir
`"Salam, {ad}!"` → bir `METN` tokeni, `parçalar` sahəsində
`[MətnParçası("Salam, "), KodParçası(tokenlər=[AD "ad"], format=None),
MətnParçası("!")]`. Lekser `{` görəndə özünü rekursiv çağırır və uyğun `}`-a
qədər oxuyur. Format spesifikatoru (`{x:.2}`) `:`-dan sonra xam mətn kimi
saxlanır.

### `oxu` və `yaz` açar söz DEYİL
`xassə sahə: onluq  oxu ... son` konstruksiyası onları tələb edir, amma
`yaz("salam")` funksiya çağırışıdır. Həll: **kontekstli söz** — lekser `AD`
buraxır, parser mövqeyə görə tanıyır. Eyni qayda: `vəziyyət`, `hesablanan`,
`əməl`, `hadisə`, `göstər`, `sınaq`, `ölç`, `sil`, `panika`, `eynidir`.

---

## 🔴 İmplementasiyanın açdığı SPESİFİKASİYA PROBLEMLƏRİ

Bunlar sənədlərdə hələ düzəldilməyib — koda başlamazdan əvvəl qərar lazımdır.

### 1. `gətir ...dan` — şəkilçi token ola bilmir ❗ciddi

Spesifikasiya § 8.3 belə yazır:
```alqor
gətir riyaziyyatdan {Pİ, kök}
```
Amma `riyaziyyatdan` **bir identifikator tokenidir** — lekser `-dan`
şəkilçisini ayıra bilməz. Ayırmağa çalışsa, `meydan` adlı modul sınar.
EBNF qrammatikası isə ayrı `"dan"` tokeni gözləyir — ziddiyyət.

**Təklif olunan həll** (nöqtə-mötərizə seçimi):
```alqor
gətir riyaziyyat                      // bütöv modul
gətir riyaziyyat kimi r               // ləqəblə
gətir riyaziyyat.{Pİ, kök}            // seçmə        ← YENİ
gətir riyaziyyat.{kök kimi k}         // ləqəbli seçmə ← YENİ
gətir riyaziyyat.*                    // hamısı       ← YENİ
gətir "./riyazi.alqor".{kvadrat}      // yerli fayldan ← YENİ
```
Qısa, qeyri-ikimənalı, klaviatura üçün rahat, şəkilçi yoxdur.
Dəyişməli: `spesifikasiya/08-MODULLAR-VE-PAKETLER.md`, `qrammatika.ebnf`,
`beledci/01-DIL-DERSLIYI.md` (Dərs 14), `acar_sozler.py`-dan `dan`/`dən` silinib.

### 2. `içində deyil` və `tipidir deyil` toqquşur

`içində` for-each bağlayıcısıdır (`hər x üçün s içində`). `içində deyil`
çox sözlü operator kimi birləşdirilsə, parser üçün ikimənalılıq yaranır.

**Həll (artıq tətbiq olunub):** ikisi də spesifikasiyadan çıxarılır, əvəzinə
```alqor
əgər deyil (x içindədir s) onda ... son
əgər deyil (x tipidir Mətn) onda ... son
```
`boş deyil` saxlanılır — toqquşması yoxdur və təbii oxunur.
Dəyişməli: `spesifikasiya/01` § 1.6, `spesifikasiya/02` § 2.9, `03` § 3.3.7.

### 3. Mühit dəyişənlərində Azərbaycan hərfləri işləmir

`ALQOR_RƏNG`, `ALQOR_HƏDƏF` kimi adlar shell-də (xüsusən Windows-da) təyin
oluna bilmir. **Həll:** hamısı ASCII olmalıdır —
`ALQOR_RENG`, `ALQOR_HEDEF`, `ALQOR_YOL`, `ALQOR_PAKETLER`, `ALQOR_JURNAL`,
`ALQOR_DIL`, `ALQOR_SAP`.
Dəyişməli: `spesifikasiya/13-ALET-ZENCIRI.md` § 13.13.

### 4. `hər x üçün siyahı içində` — söz sırası hələ açıqdır

Qrammatik cəhətdən tam təbii deyil (təbii forma "siyahıdakı hər x üçün"-dür,
amma `-dakı` şəkilçisi açar söz ola bilmir — bax problem №1).
Alternativ: `siyahı içində hər x üçün`.
Parser yazılanda ikisi də sınanıb qərar verilməlidir.

### 5. Kiçik dəqiqləşdirmələr

- `hal 1 → ...` oxu: lekser həm `→` (U+2192), həm `->` qəbul edir; parser
  `hal` kontekstində ikisini də eyni sayır.
- Tam ədəd diapazonu: 64 bit işarəli, aşılarsa `ALQ-L007`.
- NFC normalizasiyası və homoqlif düzəlişi mövqeləri dəyişə bilər
  (görünməz simvol silinəndə). Xəta hesabatı **düzəldilmiş** mətnə görə
  verilir — ALQ-L014 xəbərdarlığı istifadəçini bundan xəbərdar edir.

---

## İşə salmaq

```bash
cd alqorc
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); \
  from alqor import elifba as E; print(E.böyüyə('ışıq'), E.kiçiyə('İ'))"
```
