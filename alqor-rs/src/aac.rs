//! Abstrakt sintaksis ağacı (aac.py ilə eyni quruluş).

use crate::xeta::Yer;
use num_bigint::BigInt;
use std::rc::Rc;

pub type E = Rc<İfadə>;
pub type Gövdə = Rc<Vec<Cümlə>>;

#[derive(Debug, Clone)]
pub enum Tip {
    Ad { yer: Yer, yol: Vec<String>, arqumentlər: Vec<Tip>, ixtiyari: bool },
    Birləşmə { yer: Yer, variantlar: Vec<Tip> },
    Kortej { yer: Yer, elementlər: Vec<Tip>, ixtiyari: bool },
    Funksiya { yer: Yer, parametrlər: Vec<Tip>, qaytarma: Option<Box<Tip>>, ixtiyari: bool },
}

impl Tip {
    pub fn tam_ad(&self) -> String {
        match self {
            Tip::Ad { yol, .. } => yol.join("."),
            _ => String::new(),
        }
    }
    pub fn ixtiyaridir(&self) -> bool {
        match self {
            Tip::Ad { ixtiyari, .. } | Tip::Kortej { ixtiyari, .. } | Tip::Funksiya { ixtiyari, .. } => *ixtiyari,
            _ => false,
        }
    }
    pub fn yer(&self) -> Yer {
        match self {
            Tip::Ad { yer, .. } | Tip::Birləşmə { yer, .. } | Tip::Kortej { yer, .. } | Tip::Funksiya { yer, .. } => *yer,
        }
    }
}

#[derive(Debug, Clone)]
pub enum LiteralD {
    Tam(BigInt),
    Onluq(f64),
    Mətn(Rc<str>),
    Simvol(Rc<str>),
    Bayt(Rc<Vec<u8>>),
    Məntiq(bool),
    Boş,
}

#[derive(Debug, Clone)]
pub enum ŞablonHissə {
    Mətn(String),
    Kod(E, Option<String>),
}

#[derive(Debug, Clone)]
pub struct Arqument {
    pub dəyər: E,
    pub ad: Option<String>,
    pub yayma: bool,
}

#[derive(Debug, Clone)]
pub struct Parametr {
    pub yer: Yer,
    pub ad: String,
    pub tip: Option<Tip>,
    pub standart: Option<E>,
    pub variadic: bool,
    pub adlı_variadic: bool,
    pub yalnız_adlı: bool,
    pub xassə_görünüşü: Option<String>,
}

#[derive(Debug, Clone)]
pub enum BağlamaNöv {
    Ad(String),
    Atma,
    Qalan(String),
    Kortej(Vec<Bağlama>),
    Obyekt(Vec<(String, Option<Bağlama>)>),
}

#[derive(Debug, Clone)]
pub struct Bağlama {
    pub yer: Yer,
    pub növ: BağlamaNöv,
    pub tip: Option<Tip>,
}

#[derive(Debug, Clone)]
pub enum JSXUşaq {
    Mətn(String),
    İfadə(E),
}

#[derive(Debug, Clone)]
pub struct JSXAtribut {
    pub ad: String,
    pub dəyər: Option<E>,
    pub yayma: bool,
}

#[derive(Debug, Clone)]
pub enum LambdaGövdə {
    Blok(Gövdə),
    İfadə(E),
}

#[derive(Debug)]
pub enum İfadə {
    Literal(Yer, LiteralD),
    Şablon(Yer, Vec<ŞablonHissə>),
    Ad(Yer, Rc<str>),
    Özü(Yer),
    Üst(Yer),
    İkili(Yer, E, String, E),
    Tək(Yer, String, E),
    Mənimsətmə(Yer, Vec<E>, String, Vec<E>),
    Çevirmə(Yer, E, Tip, bool),
    TipYoxlama(Yer, E, Tip),
    Üzvlük(Yer, E, E),
    BoşYoxlama(Yer, E, bool),
    Boru(Yer, E, E),
    Diapazon(Yer, E, E, Option<E>, bool),
    Çağırış(Yer, E, Vec<Arqument>),
    Üzv(Yer, E, Rc<str>, bool),
    İndeks(Yer, E, E),
    Dilim(Yer, E, Option<E>, Option<E>, bool),
    MəcburiAçma(Yer, E),
    Yayma(Yer, E),
    Yeni(Yer, Tip, Option<String>, Vec<Arqument>),
    Gözlə(Yer, E),
    Siyahı(Yer, Vec<E>, Vec<bool>),
    Lüğət(Yer, Vec<Option<E>>, Vec<E>),
    Dəst(Yer, Vec<E>),
    Kortej(Yer, Vec<E>),
    Qurma { yer: Yer, növ: String, ifadə: E, dəyər_ifadəsi: Option<E>, bağlama: Bağlama, mənbə: E, şərt: Option<E> },
    ŞərtIfadəsi(Yer, Vec<(E, E)>, Option<E>),
    Blok(Yer, Gövdə),
    Lambda { yer: Yer, parametrlər: Rc<Vec<Parametr>>, gövdə: LambdaGövdə, asinxron: bool, generator: bool },
    JSXElement(Yer, String, Vec<JSXAtribut>, Vec<JSXUşaq>),
    JSXParça(Yer, Vec<JSXUşaq>),
}

impl İfadə {
    pub fn yer(&self) -> Yer {
        use İfadə::*;
        match self {
            Literal(y, ..) | Şablon(y, ..) | Ad(y, ..) | Özü(y) | Üst(y) | İkili(y, ..) | Tək(y, ..)
            | Mənimsətmə(y, ..) | Çevirmə(y, ..) | TipYoxlama(y, ..) | Üzvlük(y, ..) | BoşYoxlama(y, ..)
            | Boru(y, ..) | Diapazon(y, ..) | Çağırış(y, ..) | Üzv(y, ..) | İndeks(y, ..) | Dilim(y, ..)
            | MəcburiAçma(y, ..) | Yayma(y, ..) | Yeni(y, ..) | Gözlə(y, ..) | Siyahı(y, ..) | Lüğət(y, ..)
            | Dəst(y, ..) | Kortej(y, ..) | ŞərtIfadəsi(y, ..) | Blok(y, ..) | JSXElement(y, ..)
            | JSXParça(y, ..) => *y,
            Qurma { yer, .. } | Lambda { yer, .. } => *yer,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Annotasiya {
    pub ad: String,
    pub arqumentlər: Vec<Arqument>,
}

#[derive(Debug, Clone)]
pub struct Funksiya {
    pub yer: Yer,
    pub ad: String,
    pub parametrlər: Rc<Vec<Parametr>>,
    pub gövdə: Option<Gövdə>,
    pub asinxron: bool,
    pub generator: bool,
    pub annotasiyalar: Vec<String>,
    // metodlar üçün
    pub statik: bool,
    pub mücərrəd: bool,
}

#[derive(Debug, Clone)]
pub struct Xassə {
    pub yer: Yer,
    pub ad: String,
    pub tip: Option<Tip>,
    pub standart: Option<E>,
    pub statik: bool,
    pub tənbəl: bool,
    pub oxu: Option<Gövdə>,
    pub yaz: Option<Gövdə>,
    pub yaz_parametri: Option<String>,
    pub annotasiyalar: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct Qurucu {
    pub yer: Yer,
    pub ad: Option<String>,
    pub parametrlər: Rc<Vec<Parametr>>,
    pub gövdə: Gövdə,
}

#[derive(Debug, Clone)]
pub struct SinifE {
    pub yer: Yer,
    pub ad: String,
    pub üzvlər: Vec<Cümlə>,
    pub baza: Option<Tip>,
    pub interfeyslər: Vec<Tip>,
    pub qarışıqlar: Vec<Tip>,
    pub mücərrəd: bool,
    pub son: bool,
    pub quruluş: String,
}

#[derive(Debug, Clone)]
pub struct SadalamaVariantı {
    pub yer: Yer,
    pub ad: String,
    pub dəyər: Option<E>,
    pub arqumentlər: Vec<Arqument>,
    pub parametrlər: Vec<Parametr>,
}

#[derive(Debug, Clone)]
pub struct Hal {
    pub naxışlar: Vec<Naxış>,
    pub gövdə: Gövdə,
    pub mühafizə: Option<E>,
    pub keç: bool,
}

#[derive(Debug, Clone)]
pub enum Naxış {
    Atma,
    Literal(E),
    Şərt(E),
    Ad(Rc<str>),
    Tip(Tip),
    Diapazon(E, E, bool),
    Kortej(Vec<Naxış>),
    Siyahı(Vec<Naxış>, Option<String>),
    Obyekt(Option<Tip>, Vec<Naxış>, Vec<(String, Option<Naxış>)>),
}

#[derive(Debug, Clone)]
pub struct Tutma {
    pub gövdə: Gövdə,
    pub ad: Option<String>,
    pub tiplər: Vec<Tip>,
    pub mühafizə: Option<E>,
}

#[derive(Debug, Clone)]
pub struct İdxalElementi {
    pub ad: String,
    pub ləqəb: Option<String>,
}

#[derive(Debug, Clone)]
pub enum Cümlə {
    İfadə(Yer, E),
    DəyişənElanı { yer: Yer, növ: String, bağlamalar: Vec<Bağlama>, dəyərlər: Vec<E> },
    Funksiya(Rc<Funksiya>),
    Metod(Rc<Funksiya>),
    Xassə(Rc<Xassə>),
    Qurucu(Rc<Qurucu>),
    Dağıdıcı(Yer, Gövdə),
    Sinif(Rc<SinifE>),
    İnterfeys { yer: Yer, ad: String, üzvlər: Vec<Cümlə> },
    Sadalama { yer: Yer, ad: String, variantlar: Vec<SadalamaVariantı>, üzvlər: Vec<Cümlə>, əsas_tip: Option<Tip> },
    Qarışıq { yer: Yer, ad: String, üzvlər: Vec<Cümlə> },
    Genişlətmə { yer: Yer, tip: Tip, üzvlər: Vec<Cümlə> },
    TipAliası { yer: Yer, ad: String, tip: Tip },
    Modul { yer: Yer, ad: String, gövdə: Gövdə },
    Şərt { yer: Yer, budaqlar: Vec<(E, Gövdə)>, yoxsa: Option<Gövdə> },
    Varsa { yer: Yer, bağlamalar: Vec<(Option<Bağlama>, E)>, gövdə: Gövdə, yoxsa: Option<Gövdə> },
    Yoxdursa { yer: Yer, bağlamalar: Vec<(Option<Bağlama>, E)>, gövdə: Gövdə },
    Seç { yer: Yer, ifadə: Option<E>, hallar: Vec<Hal>, digər: Option<Gövdə> },
    NəQədərKi { yer: Yer, şərt: E, gövdə: Gövdə, etiket: Option<String> },
    Həmişə { yer: Yer, gövdə: Gövdə, etiket: Option<String> },
    Təkrarla { yer: Yer, say: E, gövdə: Gövdə, sayğac: Option<String>, etiket: Option<String> },
    TəkrarlaNəQədər { yer: Yer, gövdə: Gövdə, şərt: E, etiket: Option<String> },
    Hər { yer: Yer, bağlamalar: Vec<Bağlama>, mənbə: E, gövdə: Gövdə, addım: Option<E>, şərt: Option<E>,
          yoxsa: Option<Gövdə>, asinxron: bool, etiket: Option<String> },
    Dayan(Yer, Option<String>),
    DavamEt(Yer, Option<String>),
    Qaytar(Yer, Vec<E>),
    Ver(Yer, Option<E>),
    At(Yer, Option<E>),
    Cəhd { yer: Yer, gövdə: Gövdə, tutmalar: Vec<Tutma>, nəhayət: Option<Gövdə> },
    İddia(Yer, E, Option<E>),
    Təmin(Yer, E, Gövdə),
    Gecikdir(Yer, E),
    İstifadə(Yer, Vec<(String, E)>, Gövdə),
    Keç(Yer),
    DayanNöqtəsi(Yer),
    Global(Yer, Vec<String>),
    İdxal { yer: Yer, yol: Vec<String>, mətn_yolu: Option<String>, ləqəb: Option<String>,
            elementlər: Vec<İdxalElementi>, hamısı: bool },
    İxracSiyahısı(Yer),
    Başlanğıc(Yer, Gövdə),
    Bitiş(Yer, Gövdə),
    Artırma(Yer, E, String),
}

impl Cümlə {
    pub fn yer(&self) -> Yer {
        use Cümlə::*;
        match self {
            İfadə(y, _) | Dağıdıcı(y, _) | Dayan(y, _) | DavamEt(y, _) | Qaytar(y, _) | Ver(y, _) | At(y, _)
            | İddia(y, ..) | Təmin(y, ..) | Gecikdir(y, _) | İstifadə(y, ..) | Keç(y) | DayanNöqtəsi(y)
            | Global(y, _) | İxracSiyahısı(y) | Başlanğıc(y, _) | Bitiş(y, _) | Artırma(y, ..) => *y,
            Funksiya(f) | Metod(f) => f.yer,
            Xassə(x) => x.yer,
            Qurucu(q) => q.yer,
            Sinif(s) => s.yer,
            DəyişənElanı { yer, .. } | İnterfeys { yer, .. } | Sadalama { yer, .. } | Qarışıq { yer, .. }
            | Genişlətmə { yer, .. } | TipAliası { yer, .. } | Modul { yer, .. } | Şərt { yer, .. }
            | Varsa { yer, .. } | Yoxdursa { yer, .. } | Seç { yer, .. } | NəQədərKi { yer, .. }
            | Həmişə { yer, .. } | Təkrarla { yer, .. } | TəkrarlaNəQədər { yer, .. } | Hər { yer, .. }
            | Cəhd { yer, .. } | İdxal { yer, .. } => *yer,
        }
    }
}

pub struct Proqram {
    pub gövdə: Vec<Cümlə>,
}
