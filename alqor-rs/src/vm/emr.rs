//! Bayt-kod əmrləri və kompilyasiya olunmuş funksiya (`Kod`).
//!
//! Yığın maşını: ifadələr operand yığınında hesablanır, yerli dəyişənlər
//! nömrələnmiş yuvalardadır, bağlanan (closure) dəyişənlər isə ağac
//! icraçısının `Mühit` zəncirində qalır (bax: `kompilyator.rs`).

use crate::aac;
use crate::icraci::deyerler::{Ad, D};
use crate::xeta::Yer;
use std::cell::Cell;
use std::rc::Rc;

/// İkili operator
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Op {
    Topla,
    Çıx,
    Vur,
    Böl,
    TamBöl,
    Qalıq,
    Kiçik,
    Böyük,
    KiçikBərabər,
    BöyükBərabər,
    Bərabər,
    Fərqli,
    /// Digər operatorlar — mətn kimi (`adlar` hovuzunda indeks)
    Digər(u32),
}

impl Op {
    pub fn yeni(s: &str, ad_indeksi: impl FnOnce() -> u32) -> Op {
        match s {
            "+" => Op::Topla,
            "-" => Op::Çıx,
            "*" => Op::Vur,
            "/" => Op::Böl,
            "~/" => Op::TamBöl,
            "%" => Op::Qalıq,
            "<" => Op::Kiçik,
            ">" => Op::Böyük,
            "<=" => Op::KiçikBərabər,
            ">=" => Op::BöyükBərabər,
            "==" => Op::Bərabər,
            "!=" => Op::Fərqli,
            _ => Op::Digər(ad_indeksi()),
        }
    }
    pub fn mətn(self) -> &'static str {
        match self {
            Op::Topla => "+",
            Op::Çıx => "-",
            Op::Vur => "*",
            Op::Böl => "/",
            Op::TamBöl => "~/",
            Op::Qalıq => "%",
            Op::Kiçik => "<",
            Op::Böyük => ">",
            Op::KiçikBərabər => "<=",
            Op::BöyükBərabər => ">=",
            Op::Bərabər => "==",
            Op::Fərqli => "!=",
            Op::Digər(_) => "",
        }
    }
}

/// Bir bayt-kod əmri. Hər əmrin mənbə yeri `Kod::yerlər`-dədir (eyni indeks).
#[derive(Clone, Debug)]
pub enum Əmr {
    // ── Yığın ──────────────────────────────────────────────────────────
    Sabit(u32),
    Tam(i64),
    Boş,
    Məntiq(bool),
    At,
    Dup,
    // ── Yuvalar (yerli dəyişənlər) ─────────────────────────────────────
    YuvaAl(u32),
    YuvaQoy(u32),
    YuvaElan(u32),
    YuvaElanSabit(u32),
    // ── Adlar (Mühit zənciri) ──────────────────────────────────────────
    /// (ad, keş)
    AdAl(u32, u32),
    AdQoy(u32, u32),
    AdElan(u32),
    AdElanSabit(u32),
    MühitAç,
    MühitBağla,
    /// `dəyər_kopyası` (strukturlar dəyər tipidir)
    Kopya,
    /// `tam` → `onluq` (tip annotasiyası `onluq`)
    Genişlət,
    // ── Hesab ──────────────────────────────────────────────────────────
    İkili(Op),
    /// "-", "+", "~"
    Tək(u8),
    /// Yığının başı `məntiq` olmalıdır (əks halda TipXətası)
    MəntiqYoxla,
    Deyil,
    // ── Keçidlər ───────────────────────────────────────────────────────
    Atla(u32),
    /// Yığından `məntiq` götürür (yoxlanılmış), yanlışdırsa keçir
    YanlışsaAtla(u32),
    /// Yoxlayıb götürür: `məntiq` deyilsə xəta, yanlışdırsa keçir
    ŞərtAtla(u32),
    /// `??`: baş boş deyilsə saxla və keç, əks halda götür
    BoşDeyilsəAtla(u32),
    /// `?.`: baş boşdursa saxla və keç, əks halda götür
    BoşsaAtla(u32),
    /// Dövrdən çıxış: (hədəf, mühit dərinliyi, iterator dərinliyi)
    Qaç(u32, u32, u32),
    /// Siqnal (dayan/davam/qaytar) `nəhayət` bloklarından keçməlidir
    SiqnalDayan(Option<u32>),
    SiqnalDavam(Option<u32>),
    SiqnalQaytar,
    Qaytar,
    // ── Çağırışlar ─────────────────────────────────────────────────────
    Çağır(u32),
    ArqYeni,
    ArqMövqe,
    ArqAdlı(u32),
    ArqYay,
    ÇağırArq,
    /// (ad, təhlükəsiz, boş halında keçid)
    MetodAl(u32, bool, u32),
    MetodÇağır(u32, u32),
    MetodÇağırArq(u32),
    // ── Üzv və indeks ──────────────────────────────────────────────────
    ÜzvAl(u32, bool),
    ÜzvAlXam(u32),
    ÜzvQoy(u32),
    İndeksAl,
    İndeksQoy,
    /// (başlanğıc var, son var, xaric)
    Dilim(bool, bool, bool),
    /// Dilimlənən dəyərin tipini yoxlayır (hədlər hesablanmazdan əvvəl)
    DilimYoxla,
    // ── Kolleksiyalar ──────────────────────────────────────────────────
    Siyahı(u32),
    SiyahıYeni,
    SiyahıƏlavə,
    SiyahıYay,
    LüğətYeni,
    LüğətQoy,
    LüğətYay,
    DəstYeni,
    DəstƏlavə,
    Kortej(u32),
    /// Format spesifikatoru (`sabitlər`-də mətn) və ya `u32::MAX`
    Formatla(u32),
    Birləşdir(u32),
    /// (addım var, xaric)
    Diapazon(bool, bool),
    // ── Digər ifadələr ─────────────────────────────────────────────────
    /// (hədəf tip adı, təhlükəsiz)
    Çevir(u32, bool),
    /// `tiplər` hovuzunda indeks
    TipYoxla(u32),
    Üzvlük,
    BoşYoxla(bool),
    Boru,
    MəcburiAç,
    Yayma,
    /// (qurucu adı və ya u32::MAX) — yığında tip dəyəri, arqumentlər `ArqYeni` ilə
    Yeni(u32),
    /// `tip_dəyəri` (`tiplər` hovuzunda indeks)
    TipDəyəri(u32),
    Gözlə,
    ÜstQur,
    /// `alt_funksiyalar` hovuzunda indeks
    Lambda(u32),
    // ── Cümlələr ───────────────────────────────────────────────────────
    /// Hazır xəta (`xətalar` hovuzu)
    Xəta(u32),
    AtXəta,
    /// (mesaj var)
    İddia(bool),
    /// `++`/`--`: (artırma?) — yığında cari dəyər
    Artır(bool),
    /// Ağac icraçısına ötürülən cümlə (`cümlələr` hovuzu)
    Ötür(u32),
    /// Ağac icraçısına ötürülən ifadə (`ifadələr` hovuzu)
    Ötürİfadə(u32),
    // ── Dövrlər ────────────────────────────────────────────────────────
    İterAç,
    /// (son keçid)
    İterNövbəti(u32),
    İterBağla,
    İterİndeks,
    /// Lüğət üzərində dövr deyilsə keç
    İterLüğətCüt(u32),
    /// Diapazon deyilsə addım kodunu keç
    DiapazonDeyilsəAtla(u32),
    DiapazonAddım,
    /// `təkrarla` sayını yoxlayır
    TəkrarSay,
    /// (yuva, son keçid): yuva += 1, yuva > limit yuvası → keç
    Sayğac(u32, u32, u32),
    // ── Dağıtma ────────────────────────────────────────────────────────
    /// (elementlərin sayı, `...qalan` mövqeyi və ya u32::MAX)
    Dağıt(u32, u32),
    /// Çoxlu mənimsətmə: (hədəf sayı, dəyər sayı)
    Paketlə(u32, u32),
    /// `standart_dəyər` — `tiplər` hovuzunda indeks və ya u32::MAX
    StandartDəyər(u32),
    // ── Cəhd ───────────────────────────────────────────────────────────
    CəhdTəmizlə(u32),
    /// (cəhd id, tutma indeksi, növbəti tutma)
    TutmaYoxla(u32, u32, u32),
    XətaObyekti(u32),
    NəhayətSon(u32),
    // ── Qurma (comprehension) ──────────────────────────────────────────
    QurmaƏlavə(u32),
    QurmaLüğət(u32),
    AçarYoxla,
    /// (yuva, növ: 0 siyahı, 1 dəst, 2 generator, 3 lüğət)
    QurmaSon(u32, u8),
    // ── Parametrlər ────────────────────────────────────────────────────
    /// (parametr indeksi, tapılanda keçid)
    ParamAl(u32, u32),
    ParamAdlı(u32, u32),
    ParamVariadic,
    ParamAdlıVariadic,
    ParamSon,
    XassəQoy(u32),
}

#[derive(Clone, Debug)]
pub enum BölgəNöv {
    /// Dövr gövdəsi: (etiket, dayan hədəfi, davam hədəfi)
    Dövr(Option<Ad>, u32, u32),
    /// `cəhd` gövdəsi: (id, tutma kodu, nəhayət kodu, nəhayət var)
    Cəhd(u32, u32, u32, bool),
    /// `tut` blokları (yalnız `nəhayət` olanda): (id, nəhayət kodu)
    Tutma(u32, u32),
    /// Xəta → `boş` (funksiyanın son ifadəsi)
    XətaBoş(u32),
}

#[derive(Clone, Debug)]
pub struct Bölgə {
    pub başla: u32,
    pub son: u32,
    pub növ: BölgəNöv,
    pub mühit: u32,
    pub iter: u32,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum KodNövü {
    /// Blok gövdəli funksiya
    Blok,
    /// İfadə gövdəli lambda
    İfadə,
    /// Proqramın yuxarı səviyyəsi
    Kök,
}

/// Lambda / iç funksiya şablonu
pub struct AltFunksiya {
    pub ad: Ad,
    pub parametrlər: Rc<Vec<aac::Parametr>>,
    pub gövdə: crate::icraci::deyerler::FGövdə,
    pub asinxron: bool,
    pub generator: bool,
    pub yaddaşla: bool,
}

/// Kompilyasiya olunmuş funksiya gövdəsi
pub struct Kod {
    pub ad: String,
    pub növ: KodNövü,
    pub əmrlər: Vec<Əmr>,
    pub yerlər: Vec<Yer>,
    pub sabitlər: Vec<D>,
    pub adlar: Vec<Ad>,
    pub tiplər: Vec<aac::Tip>,
    pub xətalar: Vec<(String, String, &'static str)>,
    pub cümlələr: Vec<aac::Cümlə>,
    pub ifadələr: Vec<aac::E>,
    pub alt_funksiyalar: Vec<AltFunksiya>,
    pub tutmalar: Vec<aac::Tutma>,
    pub bölgələr: Vec<Bölgə>,
    pub yuva_sayı: usize,
    pub yuva_adları: Vec<Ad>,
    /// Eyni adlı xarici yuva (yuva hələ təyin olunmayıbsa)
    pub yuva_üst: Vec<Option<u32>>,
    /// "özü" və "__sinif__" yuvaları (yerlidirsə)
    pub özü_yuvası: Option<u32>,
    pub sinif_yuvası: Option<u32>,
    /// Funksiya səviyyəsində Mühit yaradılır
    pub funksiya_mühiti: bool,
    pub cəhd_sayı: usize,
    pub gecikdir_var: bool,
    pub keşlər: Vec<Cell<(usize, u32)>>,
    /// Mövqeli parametrlərin sayı və `...variadic` varmı
    pub mövqeli_say: usize,
    pub variadic_var: bool,
    pub sabit_var: bool,
    /// Parametr siyahısı (uyğunluq yoxlaması üçün)
    pub parametrlər: Option<Rc<Vec<aac::Parametr>>>,
    /// Gövdəni yaşadır
    pub _gövdə: Option<crate::icraci::deyerler::FGövdə>,
}

