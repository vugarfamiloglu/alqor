# Alqor

**Azərbaycan dilində proqramlaşdırma dili.**
Veb, desktop və konsol tətbiqləri üçün. Linux əsaslı.

```alqor
yaz("Adınızı daxil edin:")
dəyişən ad = oxu()

yaz("Yaşınızı daxil edin:")
dəyişən yaş = oxuTam()

əgər yaş >= 18 onda
    yaz("{ad}, siz yetkinsiniz.")
yoxsa
    yaz("{ad}, siz hələ yetkin deyilsiniz.")
son
```

---

## Layihənin vəziyyəti

| | |
|---|---|
| Mərhələ | **0 — Spesifikasiya** (kod yazılmayıb) |
| Versiya | 1.0 (layihə sənədi) |
| Tarix | 5 oktyabr 2026 |

---

## Dilin kimliyi

| Element | Ad |
|---|---|
| Dil | **Alqor** |
| Fayl uzantısı | `.alqor` (qısa: `.alq`) |
| CLI | `alqor` |
| Kompilyator | `alqorc` |
| İcra mühiti (VM) | `alqorvm` |
| Paket meneceri | `alqorpm` |
| Paket deposu | `alqorhub` |
| Formatter | `alqorfmt` |
| Linter | `alqorlint` |
| LSP serveri | `alqorls` |
| Test işlədici | `alqortest` |
| Sənəd generatoru | `alqordoc` |
| Redaktor / IDE | **Alqor Studio** |

> **Ad haqqında:** *Alqor* — Azərbaycan dilindəki "**alqoritm**" sözünün kökündən.
> `q` hərfi Azərbaycan latın əlifbasının imzasıdır və adı ingilis dilindəki
> `algor`-dan ayırır. Tam ASCII-təmizdir: `alqor`.

---

## Qərar verilmiş dizayn prinsipləri

| Məsələ | Qərar |
|---|---|
| **Əlifba** | Tam Azərbaycan latın əlifbası (`ə ı ğ ş ç ö ü İ`) |
| **Klaviatura** | Üç qatlı həll: redaktorda avtomatik çevirmə + `;` kompozisiyası + kompilyatorda ASCII qəbulu (xəbərdarlıqla) |
| **Tip sistemi** | Tədrici (gradual) — tip ixtiyari, yazılarsa yoxlanır |
| **Bloklar** | Açar sözlü (`əgər ... onda ... son`), girintidən asılı deyil |
| **Hədəflər** | Konsol, veb (JS/WASM), desktop (WebKitGTK), native ELF |
| **Paketləmə** | `.deb`, `.AppImage`, `.flatpak`, Docker, statik veb bundle |
| **Platforma** | Linux əsaslı, çarpaz-kompilyasiya ilə Windows/macOS |
| **Xəta mesajları** | Tam Azərbaycan dilində, düzəliş təklifi ilə |
| **İnkişaf sırası** | Platformadan asılı olmayan hissələr əvvəl |

---

## Sənədlər

### Dil Spesifikasiyası — `spesifikasiya/`

| Sənəd | Məzmun |
|---|---|
| [01 — Leksik Quruluş](spesifikasiya/01-LEKSIK-QURULUS.md) | Əlifba, Unicode, identifikatorlar, açar sözlər, literallar, ASCII əvəzləyiciləri, şərhlər |
| [02 — Tip Sistemi](spesifikasiya/02-TIP-SISTEMI.md) | Əsas və kompozit tiplər, ixtiyari tiplər, generiklər, çevirmə, dəyişməzlik |
| [03 — Dəyişənlər və Operatorlar](spesifikasiya/03-DEYISENLER-VE-OPERATORLAR.md) | Elan, əhatə dairəsi, bütün operatorlar, prioritet cədvəli, ifadələr |
| [04 — İdarəetmə Strukturları](spesifikasiya/04-IDAREETME-STRUKTURLARI.md) | `əgər`, `seç`, dövrlər, naxış uyğunlaşdırma, `gecikdir` |
| [05 — Funksiyalar](spesifikasiya/05-FUNKSIYALAR.md) | Parametrlər, lambda, qapanma, generatorlar, annotasiyalar |
| [06 — Obyekt Yönümlü](spesifikasiya/06-OBYEKT-YONUMLU.md) | Siniflər, miras, interfeys, struktur, sadalama, genişləndirmə |
| [07 — Xəta İdarəetməsi](spesifikasiya/07-XETA-IDAREETMESI.md) | `cəhd et`, xəta iyerarxiyası, `Nəticə` tipi, resurs idarəetməsi |
| [08 — Modullar və Paketlər](spesifikasiya/08-MODULLAR-VE-PAKETLER.md) | `gətir`/`ixrac et`, paket quruluşu, `layihe.alqor`, `alqorpm` |
| [09 — Asinxron və Paralel](spesifikasiya/09-ASINXRON-VE-PARALEL.md) | `asinxron`/`gözlə`, saplar, kanallar, axınlar |
| [10 — Standart Kitabxana](spesifikasiya/10-STANDART-KITABXANA.md) | Bütün modullar və funksiyalar |
| [11 — Veb Proqramlaşdırma](spesifikasiya/11-VEB-PROQRAMLASDIRMA.md) | Server, marşrutlar, şablonlar, komponentlər, təhlükəsizlik |
| [12 — Desktop və Konsol](spesifikasiya/12-DESKTOP-VE-KONSOL.md) | Pəncərələr, menyular, dialoqlar, paketləmə |
| [13 — Alət Zənciri](spesifikasiya/13-ALET-ZENCIRI.md) | CLI, formatter, linter, test, LSP, IDE, CI/CD |
| [Qrammatika (EBNF)](spesifikasiya/qrammatika.ebnf) | Rəsmi formal qrammatika |
| [Açar Sözlər](spesifikasiya/acar-sozler.md) | Tam siyahı + ASCII + beynəlxalq qarşılıqlar |

### İstifadəçi Bələdçisi — `beledci/`

| Sənəd | Kimə lazımdır |
|---|---|
| [1 — Başlanğıc](beledci/00-BASLANGIC.md) | Hamıya: quraşdırma, ilk proqram, 10 dəqiqəlik tur |
| [2 — Dil Dərsliyi](beledci/01-DIL-DERSLIYI.md) | Yeni başlayanlara: 17 dərs, tapşırıqlarla |
| [3 — Veb Dərsliyi](beledci/02-VEB-DERSLIYI.md) | Tam veb tətbiq quranlara |
| [4 — Desktop Dərsliyi](beledci/03-DESKTOP-DERSLIYI.md) | Quraşdırıcılı proqram yazanlara |
| [5 — Köçürmə Bələdçisi](beledci/04-KOCURME-BELEDCISI.md) | Python/JS/C#/PHP bilənlərə |
| [6 — Xəta Lüğəti](beledci/05-XETA-LUGETI.md) | Xəta ilə qarşılaşanlara |
| [7 — Tez Arayış](beledci/06-TEZ-ARAYIS.md) | Hamıya: bir səhifəlik xülasə |

---

## Texniki arxitektura (planlaşdırılan)

```
   mənbə.alqor (UTF-8)
        │
        ▼
 ┌──────────────────┐
 │ 1. NORMALLAŞDIR  │  NFC, BOM, homoqlif aşkarlanması
 └────────┬─────────┘
          ▼
 ┌──────────────────┐
 │ 2. LEKSER        │  Azərbaycan əlifba cədvəli, az-AZ hərf qaydaları
 └────────┬─────────┘
          ▼
 ┌──────────────────┐
 │ 3. PARSER        │  Rekursiv enmə + Pratt; Azərbaycanca xətalar
 └────────┬─────────┘
          ▼
 ┌──────────────────┐
 │ 4. SEMANTİK      │  Ad həlli, tədrici tip yoxlaması, axın daralması
 └────────┬─────────┘
          ▼
 ┌──────────────────┐
 │ 5. IR + OPT      │  SSA-bənzər aralıq forma
 └────────┬─────────┘
          ▼
   ┌──────┴──────┬──────────┬──────────┐
   ▼             ▼          ▼          ▼
 BYTECODE      NATIVE       JS        WASM
 (alqorvm)   (Cranelift)  (brauzer)  (hər yer)
             ELF/.deb/
             .AppImage
```

### Texnologiya seçimi

| Komponent | Texnologiya | Səbəb |
|---|---|---|
| Kompilyator nüvəsi | Rust | Dünyada ən yaxşı Unicode dəstəyi, tək statik binar, WASM hədəfi |
| Native backend | Cranelift → LLVM | Cranelift tez, Rust-nativ; LLVM sonra optimallaşdırma üçün |
| Veb backend | JS transpilyator + WASM | Brauzerdə heç nə quraşdırmadan işləsin |
| Desktop GUI | WebKitGTK (Tauri modeli) | Eyni UI kodu veb və desktopda |
| IDE | Tauri + CodeMirror 6 | Electron-dan 10× kiçik, Linux-nativ |
| LSP | tower-lsp | VS Code, Neovim, Zed dəstəyi |

---

## Yol xəritəsi

| Mərhələ | Nəticə | Vəziyyət |
|---|---|---|
| **0. Spesifikasiya** | Sintaksis sənədi, EBNF qrammatika, bələdçi | ✅ **Hazır** |
| 1. Lekser + Parser | Kod → AST, Azərbaycanca xətalar | ⬜ |
| 2. İnterpretator | `alqor işlət` işləyir — ilk canlı proqram | ⬜ |
| 3. Standart kitabxana | mətn, siyahı, lüğət, riyaziyyat, fayl, vaxt, json | ⬜ |
| 4. Tip yoxlayıcı | Tədrici tiplər | ⬜ |
| 5. Veb backend | JS/WASM çıxışı + `veb` freymvorku | ⬜ |
| 6. Native + paketləmə | ELF, `.deb`, `.AppImage` | ⬜ |
| 7. Desktop UI | WebKitGTK pəncərələr | ⬜ |
| 8. Alqor Studio | Canlı önizləməli IDE | ⬜ |
| 9. alqorpm + alqorhub | Paket ekosistemi | ⬜ |
| 10. Sənəd saytı | alqor.az | ⬜ |

---

## Layihə quruluşu

```
PROQRAMLASDIRMA DILI/
├── README.md                 ← bu fayl
├── spesifikasiya/            ← dilin rəsmi tərifi
│   ├── 01-LEKSIK-QURULUS.md
│   ├── 02-TIP-SISTEMI.md
│   ├── 03-DEYISENLER-VE-OPERATORLAR.md
│   ├── 04-IDAREETME-STRUKTURLARI.md
│   ├── 05-FUNKSIYALAR.md
│   ├── 06-OBYEKT-YONUMLU.md
│   ├── 07-XETA-IDAREETMESI.md
│   ├── 08-MODULLAR-VE-PAKETLER.md
│   ├── 09-ASINXRON-VE-PARALEL.md
│   ├── 10-STANDART-KITABXANA.md
│   ├── 11-VEB-PROQRAMLASDIRMA.md
│   ├── 12-DESKTOP-VE-KONSOL.md
│   ├── 13-ALET-ZENCIRI.md
│   ├── qrammatika.ebnf
│   └── acar-sozler.md
├── beledci/                  ← istifadəçi bələdçisi
│   ├── 00-BASLANGIC.md
│   ├── 01-DIL-DERSLIYI.md
│   ├── 02-VEB-DERSLIYI.md
│   ├── 03-DESKTOP-DERSLIYI.md
│   ├── 04-KOCURME-BELEDCISI.md
│   ├── 05-XETA-LUGETI.md
│   └── 06-TEZ-ARAYIS.md
└── numuneler/                ← nümunə proqramlar
```

---

## Növbəti addım

Spesifikasiya hazırdır. İmplementasiyaya başlamaq üçün:

1. **Rust alət zənciri** quraşdırılmalıdır (`rustup`)
2. **WSL** (Windows-da işləyiriksə) — Linux hədəfini real test etmək üçün
3. **Mərhələ 1** — lekser: Azərbaycan əlifba cədvəli, NFC normalizasiya,
   `az-AZ` hərf çevrilməsi, homoqlif aşkarlanması, token axını

Lekser və parser platformadan asılı deyil — WSL olmadan da Windows-da
yazıla və test edilə bilər.
