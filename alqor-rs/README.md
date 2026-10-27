# alqor-rs — Alqor-un Rust implementasiyası

Lekser, parser və icraçı. Python etalonu (`alqorc/`) ilə eyni tokenləri,
eyni AAC-ni və eyni icra nəticəsini (stdout, ALQ kodlu xəta mesajları,
çıxış kodu) verir; bunu diferensial sınaqlar yoxlayır:

```bash
cd alqorc
python -m unittest sinaq.test_rs                      # hamısı
python -m alqor.rs.muqayise işlət --korpus|--parçalar # icra müqayisəsi
ALQOR_VM=0 python -m unittest sinaq.test_rs           # ağac icraçısı ilə
```

```bash
cargo build --release
./target/release/alqor-rs işlət proqram.alq [--vm yox] [-- arq…]
sh wasm/qur.sh                                         # WebAssembly paketi
```

## Bayt-kod maşını (`src/vm/`)

`işlət` standart olaraq **bayt-kod kompilyatoru + virtual maşın** ilə
işləyir; köhnə ağac gəzən icraçı (`src/icraci/`) etalon və ehtiyat yol
kimi qalır.

| Fayl | Məzmun |
|---|---|
| `vm/emr.rs` | Əmrlər (`Əmr`), bölgələr cədvəli, `Kod` (sabitlər hovuzu, adlar, yer cədvəli, keşlər) |
| `vm/kompilyator.rs` | AAC → bayt-kod: ad həlli, yuvalar, keçidlər, birləşdirilmiş əmrlər |
| `vm/masin.rs` | İcra dövrü, çərçivələr, siqnalların (xəta/dayan/qaytar) emalı |
| `vm/mod.rs` | Keş, `ALQOR_VM*` dəyişənləri, hesabat, Rust sınaqları |

**Necə işləyir.** Funksiya ilk çağırılanda gövdəsi bayt-koda çevrilir və
keşlənir (gövdə göstəricisi üzrə). Yığın maşınıdır: operandlar və yerli
yuvalar bir paylaşılan anbarda ardıcıl yerləşir (çağırışda ayırma yoxdur).

- **Ad həlli.** Funksiyada elan olunan ad ya nömrələnmiş **yuvaya** düşür
  (heş axtarışı yoxdur), ya da ağac icraçısının **Mühit** zəncirində qalır —
  əgər o, adla axtarıla bilən yerdə işlənirsə (iç funksiya/lambda, ağac
  icraçısına ötürülən cümlə, `tipidir`/`yeni` tip adları). Belə adlar
  əvvəlcədən məlum olmadığı üçün kompilyasiya sabit nöqtəyə qədər
  təkrarlanır. Bağlamalar (closure) beləcə ağac icraçısı ilə eyni Mühit
  obyektlərini paylaşır — iki icraçı arasında sərbəst çağırış mümkündür.
- **Qlobal adlar** keşlənir (Mühit indeksi dəyişmir).
- **Dövr gövdəsi** hər iterasiyada təzə əhatədir (bağlamalar dövr
  dəyişənini düzgün tutur); etiketli `dayan`/`davam`, `yoxsa` dəstəklənir.
- **Siqnallar** (`at`, `dayan`, `davam`, `qaytar`) bölgələr cədvəli ilə
  emal olunur: `cəhd`/`tut`/`nəhayət`, dövrlər, funksiyanın son ifadəsi.
  Çağırılan funksiyadan gələn siqnal da (ağac icraçısındakı kimi) çağıranın
  dövrünə/`cəhd`-inə çatır.
- **Birləşdirilmiş əmrlər**: `yuva ⊕ sabit`, `yuva ⊕ yuva`, müqayisə +
  keçid, `kopya + elan`; tam ədədlər üçün sürətli yol.
- **Keşlər**: çağırış yeri → hədəf kodu (sadə parametrli funksiyalara
  arqumentlər birbaşa yuvalara köçürülür), sinif → sahə indeksi / metod,
  tez-tez işlənən daxili metodlar (`əlavə`, `uzunluq`, `al`, `qoy`).
- **Generatorlar** korutin daxilində VM-də işləyir (wasm-da — ağac icraçısı).
- **Stek həddi** (`ALQ-R010`, 1000 çağırış) ağac icraçısı ilə eynidir.

**Ağac icraçısına ötürülənlər** (VM daxilində bir cümlə/ifadə kimi):
`seç`, `varsa`/`yoxdursa`, `gecikdir`, `istifadə`, `ver`, iç `sinif`/
`sadalama`/`modul`/`gətir`, `??=`, blok-ifadə, JSX. **Bütün funksiya ağac
icraçısında qalır**: `global` və `gətir … hamısı` olan funksiyalar.

### Diaqnostika

```bash
ALQOR_VM_HESABAT=1 alqor-rs işlət p.alq   # VM / ağac funksiya və çağırış sayları
ALQOR_VM_KOD=1 alqor-rs işlət p.alq       # bayt-kodun çapı
ALQOR_VM=0 alqor-rs işlət p.alq           # VM-siz (= --vm yox)
```

### Meyarlar (`meyar/`)

```bash
python3 meyar/olc.py            # ağac icraçısı və VM
python3 meyar/olc.py --python   # Python etalonu da (çox yavaşdır)
```

MEYAR_CƏDVƏLİ
