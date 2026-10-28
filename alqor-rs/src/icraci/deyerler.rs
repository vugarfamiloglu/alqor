//! İcra zamanı dəyərlər (deyerler.py): dəyər modeli, xətalar, siqnallar,
//! açarlar, `tip_adı` və `mətnə`.

use super::icraci::İcraçı;
use super::muhit::Mühit;
use crate::aac;
use crate::xeta::Yer;
use indexmap::{IndexMap, IndexSet};
use num_bigint::BigInt;
use num_traits::{ToPrimitive, Zero};
use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hash, Hasher};
use std::rc::Rc;

pub type Ad = Rc<str>;

// ═══════════════════════════════════════════════════════════════════════
//  Sürətli heş (FxHash)
// ═══════════════════════════════════════════════════════════════════════

#[derive(Default, Clone, Copy)]
pub struct FxHasher {
    h: u64,
}

const FX_K: u64 = 0x517cc1b727220a95;

impl Hasher for FxHasher {
    #[inline]
    fn write(&mut self, bytes: &[u8]) {
        let mut b = bytes;
        while b.len() >= 8 {
            let v = u64::from_le_bytes([b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]]);
            self.h = (self.h.rotate_left(5) ^ v).wrapping_mul(FX_K);
            b = &b[8..];
        }
        for &x in b {
            self.h = (self.h.rotate_left(5) ^ x as u64).wrapping_mul(FX_K);
        }
    }
    #[inline]
    fn write_u64(&mut self, v: u64) {
        self.h = (self.h.rotate_left(5) ^ v).wrapping_mul(FX_K);
    }
    #[inline]
    fn write_usize(&mut self, v: usize) {
        self.write_u64(v as u64)
    }
    #[inline]
    fn finish(&self) -> u64 {
        self.h
    }
}

pub type Fx = BuildHasherDefault<FxHasher>;
pub type FxMap<K, V> = HashMap<K, V, Fx>;
pub type Lüğət = IndexMap<Açar, D, Fx>;
pub type Dəst = IndexSet<Açar, Fx>;
pub type Sahələr = IndexMap<Ad, D, Fx>;

thread_local! {
    static ADLAR: RefCell<std::collections::HashSet<Rc<str>, Fx>> = RefCell::new(Default::default());
}

/// Adı internləşdirir (təkrar ayırmaların qarşısını alır).
pub fn ad(s: &str) -> Ad {
    ADLAR.with(|a| {
        let mut a = a.borrow_mut();
        if let Some(x) = a.get(s) {
            return x.clone();
        }
        let r: Rc<str> = Rc::from(s);
        a.insert(r.clone());
        r
    })
}

// ═══════════════════════════════════════════════════════════════════════
//  Xəta və siqnallar
// ═══════════════════════════════════════════════════════════════════════

#[derive(Clone, Debug)]
pub struct AlqorXəta {
    pub tip: Ad,
    pub mesaj: String,
    pub yer: Option<Yer>,
    pub kod: String,
    pub dəyər: Option<D>,
}

impl std::fmt::Debug for D {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", py_repr(self))
    }
}

pub enum Siqnal {
    Xəta(Box<AlqorXəta>),
    Qaytar(D),
    Dayan(Option<Ad>),
    Davam(Option<Ad>),
    Ver(D),
    Dayanma(D),
    /// `wasm32` generator təkrarında hədəf `ver`-ə çatıldı
    GenVer(D),
}

impl Clone for Siqnal {
    fn clone(&self) -> Self {
        match self {
            Siqnal::Xəta(x) => Siqnal::Xəta(x.clone()),
            Siqnal::Qaytar(d) => Siqnal::Qaytar(d.clone()),
            Siqnal::Dayan(e) => Siqnal::Dayan(e.clone()),
            Siqnal::Davam(e) => Siqnal::Davam(e.clone()),
            Siqnal::Ver(d) => Siqnal::Ver(d.clone()),
            Siqnal::Dayanma(d) => Siqnal::Dayanma(d.clone()),
            Siqnal::GenVer(d) => Siqnal::GenVer(d.clone()),
        }
    }
}

pub type Nəticə<T = D> = Result<T, Siqnal>;

pub fn xəta(tip: &str, mesaj: impl Into<String>, kod: &str) -> Siqnal {
    Siqnal::Xəta(Box::new(AlqorXəta {
        tip: ad(tip),
        mesaj: mesaj.into(),
        yer: None,
        kod: kod.to_string(),
        dəyər: None,
    }))
}

pub fn xəta_yer(tip: &str, mesaj: impl Into<String>, yer: Option<Yer>, kod: &str) -> Siqnal {
    Siqnal::Xəta(Box::new(AlqorXəta {
        tip: ad(tip),
        mesaj: mesaj.into(),
        yer,
        kod: kod.to_string(),
        dəyər: None,
    }))
}

/// Kitabxana xətasına çağırış yerini əlavə edir (yer yoxdursa).
pub fn yer_qoy<T>(n: Nəticə<T>, yer: Option<Yer>) -> Nəticə<T> {
    match n {
        Err(Siqnal::Xəta(mut x)) => {
            if x.yer.is_none() && yer.is_some() {
                x.yer = yer;
            }
            Err(Siqnal::Xəta(x))
        }
        n => n,
    }
}

pub const XETA_AGACI: &[(&str, &str)] = &[
    ("Atılan", ""),
    ("Xəta", "Atılan"),
    ("ArqumentXətası", "Xəta"),
    ("TipXətası", "ArqumentXətası"),
    ("DəyərXətası", "ArqumentXətası"),
    ("DiapazonXətası", "ArqumentXətası"),
    ("ÇevrilməXətası", "Xəta"),
    ("RiyaziXəta", "Xəta"),
    ("BölməXətası", "RiyaziXəta"),
    ("DaşmaXətası", "RiyaziXəta"),
    ("KolleksiyaXətası", "Xəta"),
    ("İndeksXətası", "KolleksiyaXətası"),
    ("AçarXətası", "KolleksiyaXətası"),
    ("BoşKolleksiyaXətası", "KolleksiyaXətası"),
    ("GirişÇıxışXətası", "Xəta"),
    ("FaylTapılmadıXətası", "GirişÇıxışXətası"),
    ("İcazəXətası", "GirişÇıxışXətası"),
    ("ŞəbəkəXətası", "Xəta"),
    ("BağlantıXətası", "ŞəbəkəXətası"),
    ("VaxtBitdiXətası", "ŞəbəkəXətası"),
    ("HTTPXətası", "ŞəbəkəXətası"),
    ("FormatXətası", "Xəta"),
    ("JSONXətası", "FormatXətası"),
    ("CSVXətası", "FormatXətası"),
    ("TOMLXətası", "FormatXətası"),
    ("YAMLXətası", "FormatXətası"),
    ("XMLXətası", "FormatXətası"),
    ("SıxmaXətası", "FormatXətası"),
    ("KodlaşdırmaXətası", "FormatXətası"),
    ("KonfiqXətası", "Xəta"),
    ("ŞifrələməXətası", "Xəta"),
    ("JWTXətası", "ŞifrələməXətası"),
    ("VerilənlərXətası", "Xəta"),
    ("MəhdudiyyətXətası", "VerilənlərXətası"),
    ("BoşDəyərXətası", "Xəta"),
    ("VaxtXətası", "Xəta"),
    ("KritikXəta", "Atılan"),
    ("YaddaşBitdiXətası", "KritikXəta"),
    ("StekDaşmaXətası", "KritikXəta"),
    ("İddiaXətası", "KritikXəta"),
    ("DaxiliXəta", "KritikXəta"),
];

/// `atılan` xəta tipi `tutulan` tipinin alt növüdürmü?
pub fn xəta_uyğundur(atılan: &str, tutulan: &str) -> bool {
    let mut cari = atılan;
    loop {
        if cari == tutulan {
            return true;
        }
        match XETA_AGACI.iter().find(|(a, _)| *a == cari) {
            Some((_, ü)) if !ü.is_empty() => cari = ü,
            _ => return false,
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Dəyər
// ═══════════════════════════════════════════════════════════════════════

#[derive(Clone)]
pub enum D {
    Boş,
    M(bool),
    T(i64),
    BT(Rc<BigInt>),
    O(f64),
    S(Rc<str>),
    Bayt(Rc<Vec<u8>>),
    Siyahı(Rc<RefCell<Vec<D>>>),
    Lüğət(Rc<RefCell<Lüğət>>),
    Dəst(Rc<RefCell<Dəst>>),
    Kortej(Rc<Vec<D>>),
    Diapazon(Rc<Diapazon>),
    Funksiya(Rc<Funksiya>),
    Daxili(Rc<Daxili>),
    Metod(Rc<BağlıMetod>),
    Sinif(Rc<Sinif>),
    Nümunə(Rc<Nümunə>),
    Sadalama(Rc<Sadalama>),
    SD(Rc<SadalamaDəyəri>),
    Variant(Rc<VariantQurucusu>),
    Modul(Rc<Modul>),
    Gen(Rc<Generator>),
    Gələcək(Rc<Gələcək>),
    Element(Rc<Element>),
    XətaSinfi(Ad),
    Üst(Rc<(D, Rc<Sinif>)>),
    QurucuIst(Rc<(Rc<Sinif>, Ad)>),
    TipAliası(Rc<(Ad, aac::Tip)>),
    Naxış(Rc<fancy_regex::Regex>),
    LəğvNişanı(Rc<Cell<bool>>),
    Obyekt(Rc<Obyekt>),
}

impl D {
    pub fn s(s: &str) -> D {
        D::S(Rc::from(s))
    }
    pub fn str(s: String) -> D {
        D::S(Rc::from(s))
    }
    pub fn siyahı(v: Vec<D>) -> D {
        D::Siyahı(Rc::new(RefCell::new(v)))
    }
    pub fn kortej(v: Vec<D>) -> D {
        D::Kortej(Rc::new(v))
    }
    pub fn lüğət(l: Lüğət) -> D {
        D::Lüğət(Rc::new(RefCell::new(l)))
    }
    pub fn dəst(l: Dəst) -> D {
        D::Dəst(Rc::new(RefCell::new(l)))
    }
    pub fn tam(b: BigInt) -> D {
        match b.to_i64() {
            Some(i) => D::T(i),
            None => D::BT(Rc::new(b)),
        }
    }
    pub fn boşdur(&self) -> bool {
        matches!(self, D::Boş)
    }
    /// tam (bool deyil)
    pub fn tamdır(&self) -> bool {
        matches!(self, D::T(_) | D::BT(_))
    }
    pub fn ədəddir(&self) -> bool {
        matches!(self, D::T(_) | D::BT(_) | D::O(_))
    }
    pub fn böyük_tam(&self) -> Option<BigInt> {
        match self {
            D::T(i) => Some(BigInt::from(*i)),
            D::BT(b) => Some((**b).clone()),
            D::M(b) => Some(BigInt::from(*b as i64)),
            _ => None,
        }
    }
    /// float(x) — Python çevrilməsi
    pub fn onluq(&self) -> Option<f64> {
        match self {
            D::T(i) => Some(*i as f64),
            D::BT(b) => Some(b.to_f64().unwrap_or(f64::INFINITY)),
            D::O(f) => Some(*f),
            D::M(b) => Some(if *b { 1.0 } else { 0.0 }),
            _ => None,
        }
    }
    pub fn i64(&self) -> Option<i64> {
        match self {
            D::T(i) => Some(*i),
            D::M(b) => Some(*b as i64),
            _ => None,
        }
    }
    pub fn mətn_al(&self) -> Option<&str> {
        match self {
            D::S(s) => Some(s),
            _ => None,
        }
    }
    pub fn eynidir(&self, b: &D) -> bool {
        eyni(self, b)
    }
}

/// `is` — eyni obyektdirmi (identiklik)
pub fn eyni(a: &D, b: &D) -> bool {
    use D::*;
    match (a, b) {
        (Boş, Boş) => true,
        (M(x), M(y)) => x == y,
        (T(x), T(y)) => x == y,
        (O(x), O(y)) => x.to_bits() == y.to_bits(),
        (S(x), S(y)) => Rc::ptr_eq(x, y) || x == y,
        (BT(x), BT(y)) => Rc::ptr_eq(x, y),
        (Bayt(x), Bayt(y)) => Rc::ptr_eq(x, y),
        (Siyahı(x), Siyahı(y)) => Rc::ptr_eq(x, y),
        (Lüğət(x), Lüğət(y)) => Rc::ptr_eq(x, y),
        (Dəst(x), Dəst(y)) => Rc::ptr_eq(x, y),
        (Kortej(x), Kortej(y)) => Rc::ptr_eq(x, y),
        (Diapazon(x), Diapazon(y)) => Rc::ptr_eq(x, y),
        (Funksiya(x), Funksiya(y)) => Rc::ptr_eq(x, y),
        (Daxili(x), Daxili(y)) => Rc::ptr_eq(x, y),
        (Metod(x), Metod(y)) => Rc::ptr_eq(x, y),
        (Sinif(x), Sinif(y)) => Rc::ptr_eq(x, y),
        (Nümunə(x), Nümunə(y)) => Rc::ptr_eq(x, y),
        (Sadalama(x), Sadalama(y)) => Rc::ptr_eq(x, y),
        (SD(x), SD(y)) => Rc::ptr_eq(x, y),
        (Variant(x), Variant(y)) => Rc::ptr_eq(x, y),
        (Modul(x), Modul(y)) => Rc::ptr_eq(x, y),
        (Gen(x), Gen(y)) => Rc::ptr_eq(x, y),
        (Gələcək(x), Gələcək(y)) => Rc::ptr_eq(x, y),
        (Element(x), Element(y)) => Rc::ptr_eq(x, y),
        (XətaSinfi(x), XətaSinfi(y)) => Rc::ptr_eq(x, y),
        (Üst(x), Üst(y)) => Rc::ptr_eq(x, y),
        (QurucuIst(x), QurucuIst(y)) => Rc::ptr_eq(x, y),
        (TipAliası(x), TipAliası(y)) => Rc::ptr_eq(x, y),
        (Naxış(x), Naxış(y)) => Rc::ptr_eq(x, y),
        (LəğvNişanı(x), LəğvNişanı(y)) => Rc::ptr_eq(x, y),
        (Obyekt(x), Obyekt(y)) => Rc::ptr_eq(x, y),
        _ => false,
    }
}

pub fn ptr_id(d: &D) -> usize {
    use D::*;
    match d {
        BT(x) => Rc::as_ptr(x) as usize,
        S(x) => Rc::as_ptr(x) as *const u8 as usize,
        Bayt(x) => Rc::as_ptr(x) as usize,
        Siyahı(x) => Rc::as_ptr(x) as usize,
        Lüğət(x) => Rc::as_ptr(x) as usize,
        Dəst(x) => Rc::as_ptr(x) as usize,
        Kortej(x) => Rc::as_ptr(x) as usize,
        Diapazon(x) => Rc::as_ptr(x) as usize,
        Funksiya(x) => Rc::as_ptr(x) as usize,
        Daxili(x) => Rc::as_ptr(x) as usize,
        Metod(x) => Rc::as_ptr(x) as usize,
        Sinif(x) => Rc::as_ptr(x) as usize,
        Nümunə(x) => Rc::as_ptr(x) as usize,
        Sadalama(x) => Rc::as_ptr(x) as usize,
        SD(x) => Rc::as_ptr(x) as usize,
        Variant(x) => Rc::as_ptr(x) as usize,
        Modul(x) => Rc::as_ptr(x) as usize,
        Gen(x) => Rc::as_ptr(x) as usize,
        Gələcək(x) => Rc::as_ptr(x) as usize,
        Element(x) => Rc::as_ptr(x) as usize,
        XətaSinfi(x) => Rc::as_ptr(x) as *const u8 as usize,
        Üst(x) => Rc::as_ptr(x) as usize,
        QurucuIst(x) => Rc::as_ptr(x) as usize,
        TipAliası(x) => Rc::as_ptr(x) as usize,
        Naxış(x) => Rc::as_ptr(x) as usize,
        LəğvNişanı(x) => Rc::as_ptr(x) as usize,
        Obyekt(x) => Rc::as_ptr(x) as usize,
        Boş => 1,
        M(b) => 2 + *b as usize,
        T(i) => *i as usize,
        O(f) => f.to_bits() as usize,
    }
}

// ── Diapazon ───────────────────────────────────────────────────────────

pub struct Diapazon {
    pub başlanğıc: i64,
    pub son: i64,
    pub addım: i64,
    pub xaric: bool,
}

impl Diapazon {
    pub fn hədd(&self) -> i64 {
        if self.addım > 0 {
            if self.xaric { self.son } else { self.son.saturating_add(1) }
        } else if self.xaric {
            self.son
        } else {
            self.son.saturating_sub(1)
        }
    }
    pub fn uzunluq(&self) -> i64 {
        let (b, h, a) = (self.başlanğıc as i128, self.hədd() as i128, self.addım as i128);
        if a > 0 {
            if h > b { ((h - b + a - 1) / a) as i64 } else { 0 }
        } else if b > h {
            ((b - h - a - 1) / -a) as i64
        } else {
            0
        }
    }
    pub fn al(&self, i: i64) -> i64 {
        self.başlanğıc + i * self.addım
    }
    pub fn ehtiva(&self, x: i64) -> bool {
        let d = x as i128 - self.başlanğıc as i128;
        let a = self.addım as i128;
        if d % a != 0 {
            return false;
        }
        let i = d / a;
        i >= 0 && i < self.uzunluq() as i128
    }
}

// ── Funksiyalar ────────────────────────────────────────────────────────

#[derive(Clone)]
pub enum FGövdə {
    Blok(aac::Gövdə),
    İfadə(aac::E),
}

#[derive(Clone, Copy, Default)]
pub struct Annot {
    pub yaddaşla: bool,
    pub tənbəl: bool,
    pub statik: bool,
}

pub type YaddaşKeşi = Rc<RefCell<FxMap<Vec<YaddaşAçarı>, D>>>;

#[derive(Clone, PartialEq, Eq, Hash)]
pub enum YaddaşAçarı {
    Boş,
    M(bool),
    T(i64),
    BT(BigInt),
    O(u64),
    S(Rc<str>),
    İd(usize),
}

pub struct Funksiya {
    pub ad: Ad,
    pub parametrlər: Rc<Vec<aac::Parametr>>,
    pub gövdə: FGövdə,
    pub mühit: Mühit,
    pub asinxron: bool,
    pub generator: bool,
    pub özü: Option<D>,
    pub sinif: Option<Rc<Sinif>>,
    pub annot: Annot,
    pub yaddaş: Option<YaddaşKeşi>,
    /// Bəzəyici ilə dəyişdirilmiş metod (§ 5.11): çağırılanda bu dəyər
    /// `özü` birinci arqument olmaqla çağırılır
    pub bəzənmiş: Option<D>,
}

impl Funksiya {
    pub fn bağla(&self, nümunə: D) -> Rc<Funksiya> {
        Rc::new(Funksiya {
            ad: self.ad.clone(),
            parametrlər: self.parametrlər.clone(),
            gövdə: self.gövdə.clone(),
            mühit: self.mühit.clone(),
            asinxron: self.asinxron,
            generator: self.generator,
            özü: Some(nümunə),
            sinif: self.sinif.clone(),
            annot: self.annot,
            yaddaş: self.yaddaş.clone(),
            bəzənmiş: self.bəzənmiş.clone(),
        })
    }
}

/// Adlı arqumentlər (sıra saxlanılır).
pub type Adlı = Vec<(Ad, D)>;

pub type DaxiliF = dyn Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə;

pub struct Daxili {
    pub ad: Ad,
    pub f: Box<DaxiliF>,
    pub min: usize,
    pub maks: Option<usize>,
}

pub fn daxili(
    ad_: &str,
    min: usize,
    maks: Option<usize>,
    f: impl Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə + 'static,
) -> D {
    D::Daxili(Rc::new(Daxili { ad: ad(ad_), f: Box::new(f), min, maks }))
}

pub enum MetodF {
    Daxili,
    Genişlətmə(Rc<Funksiya>),
}

/// Daxili tipin metodu: `"salam".böyüyə`
pub struct BağlıMetod {
    pub ad: Ad,
    pub obyekt: D,
    pub f: MetodF,
}

// ── Siniflər ───────────────────────────────────────────────────────────

pub struct Sinif {
    pub ad: Ad,
    pub baza: Option<Rc<Sinif>>,
    pub metodlar: RefCell<FxMap<Ad, Rc<Funksiya>>>,
    pub statiklər: RefCell<IndexMap<Ad, D, Fx>>,
    pub quruculər: RefCell<FxMap<Ad, Rc<Funksiya>>>,
    pub xassələr: RefCell<Vec<Rc<aac::Xassə>>>,
    pub hesablananlar: RefCell<FxMap<Ad, Rc<Funksiya>>>,
    pub yazıcılar: RefCell<FxMap<Ad, Rc<Funksiya>>>,
    pub mücərrəd: bool,
    pub son: bool,
    pub quruluş: &'static str,
    pub mücərrəd_metodlar: RefCell<Vec<Ad>>,
    pub interfeyslər: Vec<String>,
    pub mühit: Option<Mühit>,
}

impl Sinif {
    pub fn yeni(ad_: &str, baza: Option<Rc<Sinif>>, quruluş: &'static str) -> Sinif {
        Sinif {
            ad: ad(ad_),
            baza,
            metodlar: Default::default(),
            statiklər: Default::default(),
            quruculər: Default::default(),
            xassələr: Default::default(),
            hesablananlar: Default::default(),
            yazıcılar: Default::default(),
            mücərrəd: false,
            son: false,
            quruluş,
            mücərrəd_metodlar: Default::default(),
            interfeyslər: vec![],
            mühit: None,
        }
    }
    pub fn metod_tap(&self, ad: &str) -> Option<Rc<Funksiya>> {
        let mut s = Some(self);
        while let Some(c) = s {
            if let Some(f) = c.metodlar.borrow().get(ad) {
                return Some(f.clone());
            }
            s = c.baza.as_deref();
        }
        None
    }
    pub fn hesablanan_tap(&self, ad: &str) -> Option<Rc<Funksiya>> {
        let mut s = Some(self);
        while let Some(c) = s {
            if let Some(f) = c.hesablananlar.borrow().get(ad) {
                return Some(f.clone());
            }
            s = c.baza.as_deref();
        }
        None
    }
    pub fn yazıcı_tap(&self, ad: &str) -> Option<Rc<Funksiya>> {
        let mut s = Some(self);
        while let Some(c) = s {
            if let Some(f) = c.yazıcılar.borrow().get(ad) {
                return Some(f.clone());
            }
            s = c.baza.as_deref();
        }
        None
    }
    pub fn statik_tap(&self, ad: &str) -> Option<D> {
        let mut s = Some(self);
        while let Some(c) = s {
            if let Some(d) = c.statiklər.borrow().get(ad) {
                return Some(d.clone());
            }
            if let Some(f) = c.metodlar.borrow().get(ad) {
                if f.annot.statik {
                    return Some(D::Funksiya(f.clone()));
                }
            }
            s = c.baza.as_deref();
        }
        None
    }
    pub fn qurucu_tap(&self, ad: &str) -> Option<Rc<Funksiya>> {
        let mut s = Some(self);
        while let Some(c) = s {
            if let Some(f) = c.quruculər.borrow().get(ad) {
                return Some(f.clone());
            }
            s = c.baza.as_deref();
        }
        None
    }
    pub fn bütün_xassələr(&self) -> Vec<Rc<aac::Xassə>> {
        let mut zəncir = vec![];
        let mut s = Some(self);
        while let Some(c) = s {
            zəncir.push(c);
            s = c.baza.as_deref();
        }
        let mut n = vec![];
        for c in zəncir.iter().rev() {
            n.extend(c.xassələr.borrow().iter().cloned());
        }
        n
    }
    pub fn alt_sinifdirmi(&self, digər: &Rc<Sinif>) -> bool {
        let mut s = Some(self);
        while let Some(c) = s {
            if std::ptr::eq(c, Rc::as_ptr(digər)) {
                return true;
            }
            s = c.baza.as_deref();
        }
        false
    }
}

pub struct Nümunə {
    pub sinif: Rc<Sinif>,
    pub sahələr: RefCell<Sahələr>,
    pub keş: RefCell<FxMap<Ad, D>>,
}

impl Nümunə {
    pub fn yeni(sinif: Rc<Sinif>) -> Nümunə {
        Nümunə { sinif, sahələr: Default::default(), keş: Default::default() }
    }
    pub fn klonla(&self) -> Rc<Nümunə> {
        Rc::new(Nümunə {
            sinif: self.sinif.clone(),
            sahələr: RefCell::new(self.sahələr.borrow().clone()),
            keş: Default::default(),
        })
    }
    pub fn sahə(&self, a: &str) -> Option<D> {
        self.sahələr.borrow().get(a).cloned()
    }
}

// ── Sadalama ───────────────────────────────────────────────────────────

pub struct Sadalama {
    pub ad: Ad,
    pub variantlar: RefCell<IndexMap<Ad, D, Fx>>,
    pub metodlar: RefCell<FxMap<Ad, Rc<Funksiya>>>,
    pub sıra: RefCell<Vec<Ad>>,
}

pub struct SadalamaDəyəri {
    pub sadalama: Rc<Sadalama>,
    pub ad: Ad,
    pub sıra_nömrəsi: i64,
    pub dəyər: D,
    pub sahələr: Sahələr,
}

pub struct VariantQurucusu {
    pub sadalama: Rc<Sadalama>,
    pub ad: Ad,
    pub parametrlər: Vec<Ad>,
    pub sıra: i64,
}

// ── Modul ──────────────────────────────────────────────────────────────

pub struct Modul {
    pub ad: RefCell<Ad>,
    pub üzvlər: RefCell<IndexMap<Ad, D, Fx>>,
    pub çağırışçı: Option<D>,
}

impl Modul {
    pub fn yeni(ad_: &str, üzvlər: Vec<(&str, D)>) -> Rc<Modul> {
        Rc::new(Modul {
            ad: RefCell::new(ad(ad_)),
            üzvlər: RefCell::new(üzvlər.into_iter().map(|(a, d)| (ad(a), d)).collect()),
            çağırışçı: None,
        })
    }
    pub fn adı(&self) -> Ad {
        self.ad.borrow().clone()
    }
}

// ── Kitabxana obyekti (konsol.irəliləyiş və s.) ────────────────────────

pub struct Obyekt {
    pub tip: &'static str,
    pub üzvlər: IndexMap<&'static str, D, Fx>,
    pub mətn: Option<Box<dyn Fn() -> String>>,
    /// Kitabxana obyektinin daxili vəziyyəti (`elave::veri`)
    pub veri: Option<Rc<dyn std::any::Any>>,
}

// ── Element (JSX) ──────────────────────────────────────────────────────

pub struct Element {
    pub ad: Ad,
    pub atributlar: D, // lüğət
    pub uşaqlar: D,    // siyahı
}

impl Element {
    pub fn atributlar(&self) -> Rc<RefCell<Lüğət>> {
        match &self.atributlar {
            D::Lüğət(l) => l.clone(),
            _ => Rc::new(RefCell::new(Lüğət::default())),
        }
    }
    pub fn uşaqlar(&self) -> Vec<D> {
        match &self.uşaqlar {
            D::Siyahı(l) => l.borrow().clone(),
            _ => vec![],
        }
    }
}

// ── Generator və Gələcək ───────────────────────────────────────────────

#[cfg(not(target_arch = "wasm32"))]
pub type KorutinT = corosensei::Coroutine<(), D, Nəticə<()>, corosensei::stack::DefaultStack>;

/// `wasm32`-də stek dəyişdirmə yoxdur: generator gövdəsi hər `növbəti`-də
/// yenidən işlədilir, əvvəlki `ver`-lər (çıxış susdurularaq) keçilir.
#[cfg(target_arch = "wasm32")]
pub struct Təkrar {
    pub f: Rc<Funksiya>,
    pub args: Vec<D>,
    pub adlı: Adlı,
    pub verilən: usize,
}

pub enum GenMənbə {
    #[cfg(not(target_arch = "wasm32"))]
    Korutin(Box<KorutinT>, Ad),
    #[cfg(target_arch = "wasm32")]
    Təkrar(Təkrar),
    Siyahı(std::vec::IntoIter<D>),
    Çevir(Rc<Generator>, D),
    Filtr(Rc<Generator>, D),
    Atla(Rc<Generator>, D, i64),
    Bitdi,
}

pub struct Generator {
    pub mənbə: RefCell<GenMənbə>,
    pub bitdi: Cell<bool>,
    /// Korutin üçün: daxili bitmə (xəta artıq atılıb)
    pub korutin_bitdi: Cell<bool>,
}

pub struct Gələcək {
    pub ad: Ad,
    pub iş: RefCell<Option<Box<dyn FnOnce(&İcraçı) -> Nəticə>>>,
    pub nəticə: RefCell<Option<Nəticə>>,
}

// ═══════════════════════════════════════════════════════════════════════
//  Açar — lüğət/dəst açarı (Python heş və bərabərlik qaydaları)
// ═══════════════════════════════════════════════════════════════════════

#[derive(Clone)]
pub struct Açar(pub D);

impl Açar {
    pub fn yeni(d: D) -> Nəticə<Açar> {
        heşlənir(&d)?;
        Ok(Açar(d))
    }
}

fn heşlənir(d: &D) -> Nəticə<()> {
    match d {
        D::Siyahı(_) | D::Lüğət(_) | D::Dəst(_) | D::Element(_) => Err(xəta(
            "TipXətası",
            format!("`{}` lüğət açarı ola bilməz", tip_adı(d)),
            "ALQ-T001",
        )),
        D::Kortej(k) => {
            for x in k.iter() {
                heşlənir(x)?;
            }
            Ok(())
        }
        _ => Ok(()),
    }
}

/// Tam dəyərli onluq → tam (heş üçün)
fn ədəd_normal(d: &D) -> Option<Result<BigInt, f64>> {
    match d {
        D::M(b) => Some(Ok(BigInt::from(*b as i64))),
        D::T(i) => Some(Ok(BigInt::from(*i))),
        D::BT(b) => Some(Ok((**b).clone())),
        D::O(f) => {
            if f.is_finite() && f.fract() == 0.0 {
                Some(Ok(num_traits::FromPrimitive::from_f64(*f).unwrap_or_default()))
            } else {
                Some(Err(*f))
            }
        }
        _ => None,
    }
}

impl Hash for Açar {
    fn hash<H: Hasher>(&self, h: &mut H) {
        heş_yaz(&self.0, h)
    }
}

fn heş_yaz<H: Hasher>(d: &D, h: &mut H) {
    match d {
        D::T(i) => {
            0u8.hash(h);
            i.hash(h)
        }
        D::M(b) => {
            0u8.hash(h);
            (*b as i64).hash(h)
        }
        D::O(f) => {
            if f.is_finite() && f.fract() == 0.0 && f.abs() < 9.2e18 {
                0u8.hash(h);
                (*f as i64).hash(h)
            } else if f.is_finite() && f.fract() == 0.0 {
                1u8.hash(h);
            } else {
                2u8.hash(h);
                f.to_bits().hash(h)
            }
        }
        D::BT(_) => 1u8.hash(h),
        D::S(s) => {
            3u8.hash(h);
            s.hash(h)
        }
        D::Boş => 4u8.hash(h),
        D::Kortej(k) => {
            5u8.hash(h);
            for x in k.iter() {
                heş_yaz(x, h);
            }
        }
        D::SD(s) => {
            6u8.hash(h);
            (Rc::as_ptr(&s.sadalama) as usize).hash(h);
            s.ad.hash(h)
        }
        D::Bayt(b) => {
            7u8.hash(h);
            b.hash(h)
        }
        x => {
            8u8.hash(h);
            ptr_id(x).hash(h)
        }
    }
}

impl PartialEq for Açar {
    fn eq(&self, o: &Açar) -> bool {
        py_eq(&self.0, &o.0)
    }
}
impl Eq for Açar {}

/// Python `==` (iç-içə kolleksiyalar üçün; istifadəçi metodu çağırılmır)
pub fn py_eq(a: &D, b: &D) -> bool {
    use D::*;
    match (a, b) {
        (S(x), S(y)) => x == y,
        (Boş, Boş) => true,
        (T(x), T(y)) => x == y,
        (O(x), O(y)) => x == y,
        (M(x), M(y)) => x == y,
        (Siyahı(x), Siyahı(y)) => {
            if Rc::ptr_eq(x, y) {
                return true;
            }
            let (x, y) = (x.borrow(), y.borrow());
            x.len() == y.len() && x.iter().zip(y.iter()).all(|(p, q)| eyni(p, q) || py_eq(p, q))
        }
        (Kortej(x), Kortej(y)) => {
            x.len() == y.len() && x.iter().zip(y.iter()).all(|(p, q)| eyni(p, q) || py_eq(p, q))
        }
        (Lüğət(x), Lüğət(y)) => {
            if Rc::ptr_eq(x, y) {
                return true;
            }
            let (x, y) = (x.borrow(), y.borrow());
            x.len() == y.len()
                && x.iter().all(|(k, v)| y.get(k).map(|w| eyni(v, w) || py_eq(v, w)).unwrap_or(false))
        }
        (Dəst(x), Dəst(y)) => {
            if Rc::ptr_eq(x, y) {
                return true;
            }
            let (x, y) = (x.borrow(), y.borrow());
            x.len() == y.len() && x.iter().all(|k| y.contains(k))
        }
        (Bayt(x), Bayt(y)) => x == y,
        (Nümunə(x), Nümunə(y)) => {
            if Rc::ptr_eq(x, y) {
                return true;
            }
            if x.sinif.quruluş == "struktur" && Rc::ptr_eq(&x.sinif, &y.sinif) {
                let (p, q) = (x.sahələr.borrow(), y.sahələr.borrow());
                return p.len() == q.len()
                    && p.iter().all(|(k, v)| q.get(k).map(|w| py_eq(v, w)).unwrap_or(false));
            }
            false
        }
        (SD(x), SD(y)) => {
            Rc::ptr_eq(&x.sadalama, &y.sadalama)
                && x.ad == y.ad
                && x.sahələr.len() == y.sahələr.len()
                && x.sahələr.iter().all(|(k, v)| y.sahələr.get(k).map(|w| py_eq(v, w)).unwrap_or(false))
        }
        (Element(x), Element(y)) => {
            Rc::ptr_eq(x, y)
                || (x.ad == y.ad && py_eq(&x.atributlar, &y.atributlar) && py_eq(&x.uşaqlar, &y.uşaqlar))
        }
        (Diapazon(x), Diapazon(y)) => Rc::ptr_eq(x, y),
        _ => match (ədəd_normal(a), ədəd_normal(b)) {
            (Some(p), Some(q)) => match (p, q) {
                (Ok(p), Ok(q)) => p == q,
                (Err(p), Err(q)) => p == q,
                _ => false,
            },
            (None, None) => eyni(a, b),
            _ => false,
        },
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Tip adları
// ═══════════════════════════════════════════════════════════════════════

pub fn tip_adı(d: &D) -> String {
    match d {
        D::Boş => "heç".into(),
        D::M(_) => "məntiq".into(),
        D::T(_) | D::BT(_) => "tam".into(),
        D::O(_) => "onluq".into(),
        D::S(_) => "mətn".into(),
        D::Bayt(_) => "bayt".into(),
        D::Siyahı(l) => {
            let l = l.borrow();
            if l.is_empty() {
                return "siyahı".into();
            }
            let ilk = tip_adı(&l[0]);
            if l.iter().skip(1).all(|x| tip_adı(x) == ilk) {
                format!("siyahı[{ilk}]")
            } else {
                "siyahı[istənilən]".into()
            }
        }
        D::Lüğət(l) => {
            let l = l.borrow();
            if !l.is_empty() {
                let mut it = l.iter();
                let (k0, v0) = it.next().unwrap();
                let (a, b) = (tip_adı(&k0.0), tip_adı(v0));
                if l.iter().all(|(k, v)| tip_adı(&k.0) == a && tip_adı(v) == b) {
                    return format!("lüğət[{a}, {b}]");
                }
            }
            "lüğət".into()
        }
        D::Dəst(_) => "dəst".into(),
        D::Kortej(k) => format!("kortej[{}]", k.iter().map(tip_adı).collect::<Vec<_>>().join(", ")),
        D::Diapazon(_) => "diapazon".into(),
        D::Nümunə(n) => n.sinif.ad.to_string(),
        D::Sinif(s) => format!("sinif[{}]", s.ad),
        D::SD(s) => s.sadalama.ad.to_string(),
        D::Sadalama(s) => format!("sadalama[{}]", s.ad),
        D::Modul(m) => format!("modul[{}]", m.adı()),
        D::Gen(_) => "generator".into(),
        D::Element(_) => "element".into(),
        D::Gələcək(_) => "gələcək".into(),
        D::LəğvNişanı(_) => "ləğvNişanı".into(),
        D::Funksiya(_) | D::Daxili(_) | D::Metod(_) | D::XətaSinfi(_) | D::Variant(_) => "funksiya".into(),
        D::Obyekt(o) => o.tip.into(),
        _ => "istənilən".into(),
    }
}

/// `tip_adı` kökü ("siyahı[tam]" → "siyahı")
pub fn tip_kökü(d: &D) -> String {
    match d {
        D::Siyahı(_) => return "siyahı".into(),
        D::Lüğət(_) => return "lüğət".into(),
        D::Kortej(_) => return "kortej".into(),
        _ => {}
    }
    let t = tip_adı(d);
    match t.find('[') {
        Some(i) => t[..i].to_string(),
        None => t,
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Mətnə çevirmə
// ═══════════════════════════════════════════════════════════════════════

pub fn onluq_mətn(f: f64) -> String {
    if f.is_nan() {
        return "ƏdədDeyil".into();
    }
    if f == f64::INFINITY {
        return "sonsuz".into();
    }
    if f == f64::NEG_INFINITY {
        return "-sonsuz".into();
    }
    if f.fract() == 0.0 && f.abs() < 1e16 {
        return format!("{:.1}", f);
    }
    onluq_repr(f)
}

/// Python `repr(float)`
pub fn onluq_repr(f: f64) -> String {
    if f.is_nan() {
        return "nan".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "inf".into() } else { "-inf".into() };
    }
    if f == 0.0 {
        return if f.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    let e = format!("{:e}", f);
    let (m, ex) = e.split_once('e').unwrap();
    let ex: i32 = ex.parse().unwrap();
    let mənfi = m.starts_with('-');
    let rəq: String = m.chars().filter(|c| c.is_ascii_digit()).collect();
    let s = if (-4..16).contains(&ex) {
        if ex >= 0 {
            let e = ex as usize;
            if rəq.len() <= e + 1 {
                format!("{}{}.0", rəq, "0".repeat(e + 1 - rəq.len()))
            } else {
                format!("{}.{}", &rəq[..e + 1], &rəq[e + 1..])
            }
        } else {
            format!("0.{}{}", "0".repeat((-ex - 1) as usize), rəq)
        }
    } else {
        let mant = if rəq.len() > 1 { format!("{}.{}", &rəq[..1], &rəq[1..]) } else { rəq };
        format!("{}e{}{:02}", mant, if ex < 0 { '-' } else { '+' }, ex.abs())
    };
    if mənfi { format!("-{s}") } else { s }
}

/// Dəstin göstərilmə sırası (Python-da kiçik mənfi olmayan tamlar sıralı görünür).
pub fn dəst_sırası(d: &Dəst) -> Vec<D> {
    let el: Vec<D> = d.iter().map(|a| a.0.clone()).collect();
    if el.iter().all(|x| matches!(x, D::T(i) if *i >= 0 && *i < 1_000_000)) {
        let mut v = el;
        v.sort_by_key(|x| x.i64().unwrap());
        return v;
    }
    el
}

pub fn mətnə(i: &İcraçı, d: &D) -> Nəticə<String> {
    Ok(match d {
        D::Boş => "boş".into(),
        D::M(true) => "doğru".into(),
        D::M(false) => "yanlış".into(),
        D::S(s) => s.to_string(),
        D::O(f) => onluq_mətn(*f),
        D::T(n) => n.to_string(),
        D::BT(n) => n.to_string(),
        D::Bayt(b) => format!("b\"{}\"", String::from_utf8_lossy(b)),
        D::Siyahı(l) => {
            let l = l.borrow().clone();
            let mut h = Vec::with_capacity(l.len());
            for x in &l {
                h.push(daxili_mətn(i, x)?);
            }
            format!("[{}]", h.join(", "))
        }
        D::Kortej(k) => {
            if k.len() == 1 {
                format!("({},)", daxili_mətn(i, &k[0])?)
            } else {
                let mut h = vec![];
                for x in k.iter() {
                    h.push(daxili_mətn(i, x)?);
                }
                format!("({})", h.join(", "))
            }
        }
        D::Dəst(s) => {
            let el = dəst_sırası(&s.borrow());
            if el.is_empty() {
                return Ok("dəst()".into());
            }
            let mut h = vec![];
            for x in &el {
                h.push(daxili_mətn(i, x)?);
            }
            format!("{{{}}}", h.join(", "))
        }
        D::Lüğət(l) => {
            let c: Vec<(D, D)> = l.borrow().iter().map(|(k, v)| (k.0.clone(), v.clone())).collect();
            if c.is_empty() {
                return Ok("{}".into());
            }
            let mut h = vec![];
            for (k, v) in &c {
                h.push(format!("{}: {}", daxili_mətn(i, k)?, daxili_mətn(i, v)?));
            }
            format!("{{{}}}", h.join(", "))
        }
        D::Element(e) => element_html(i, e)?,
        D::Nümunə(n) => {
            if let Some(m) = n.sinif.metod_tap("mətnƏt") {
                let r = i.funksiya_çağır(&m.bağla(d.clone()), vec![], vec![], None)?;
                return mətnə(i, &r);
            }
            let c: Vec<(Ad, D)> = n.sahələr.borrow().iter().map(|(k, v)| (k.clone(), v.clone())).collect();
            let mut h = vec![];
            for (k, v) in &c {
                h.push(format!("{}: {}", k, daxili_mətn(i, v)?));
            }
            format!("{}({})", n.sinif.ad, h.join(", "))
        }
        _ => py_str(d),
    })
}

/// Kolleksiya daxilində mətnlər dırnaqda göstərilir.
pub fn daxili_mətn(i: &İcraçı, d: &D) -> Nəticə<String> {
    if let D::S(s) = d {
        return Ok(format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\"")));
    }
    mətnə(i, d)
}

/// Python `str()` — xüsusi obyektlər üçün
pub fn py_str(d: &D) -> String {
    match d {
        D::Funksiya(f) => format!("<funksiya {}>", f.ad),
        D::Daxili(f) => format!("<daxili {}>", f.ad),
        D::Metod(m) => format!("<metod {}>", m.ad),
        D::Sinif(s) => format!("<{} {}>", s.quruluş, s.ad),
        D::Sadalama(s) => format!("<sadalama {}>", s.ad),
        D::SD(s) => {
            if s.sahələr.is_empty() {
                s.ad.to_string()
            } else {
                let h: Vec<String> = s.sahələr.iter().map(|(a, d)| format!("{}={}", a, py_repr(d))).collect();
                format!("{}({})", s.ad, h.join(", "))
            }
        }
        D::Variant(v) => format!("<variant {}.{}>", v.sadalama.ad, v.ad),
        D::Modul(m) => format!("<modul {}>", m.adı()),
        D::Diapazon(r) => {
            let n = if r.xaric { "..<" } else { ".." };
            let a = if r.addım.abs() != 1 { format!(" addım {}", r.addım) } else { String::new() };
            format!("{}{}{}{}", r.başlanğıc, n, r.son, a)
        }
        D::Gen(g) => if g.bitdi.get() { "<generator (bitdi)>".into() } else { "<generator>".into() },
        D::Gələcək(g) => {
            let v = if g.nəticə.borrow().is_some() { "bitib" } else { "gözləyir" };
            format!("<gələcək {} ({})>", g.ad, v)
        }
        D::XətaSinfi(a) => format!("<xəta {}>", a),
        D::TipAliası(t) => format!("<tip {}>", t.0),
        D::Obyekt(o) => match &o.mətn {
            Some(f) => f(),
            None => format!("<{} obyekti>", o.tip),
        },
        D::Üst(_) => "<üst>".into(),
        D::QurucuIst(q) => format!("<qurucu {}.{}>", q.0.ad, q.1),
        D::Naxış(_) => "<naxış>".into(),
        D::LəğvNişanı(_) => "<ləğvNişanı>".into(),
        _ => py_repr(d),
    }
}

/// Python `repr()` (cəbri sadalama sahələri üçün)
pub fn py_repr(d: &D) -> String {
    match d {
        D::Boş => "None".into(),
        D::M(true) => "True".into(),
        D::M(false) => "False".into(),
        D::T(i) => i.to_string(),
        D::BT(b) => b.to_string(),
        D::O(f) => onluq_repr(*f),
        D::S(s) => str_repr(s),
        D::Siyahı(l) => format!("[{}]", l.borrow().iter().map(py_repr).collect::<Vec<_>>().join(", ")),
        D::Kortej(k) => {
            if k.len() == 1 {
                format!("({},)", py_repr(&k[0]))
            } else {
                format!("({})", k.iter().map(py_repr).collect::<Vec<_>>().join(", "))
            }
        }
        D::Lüğət(l) => format!(
            "{{{}}}",
            l.borrow().iter().map(|(k, v)| format!("{}: {}", py_repr(&k.0), py_repr(v))).collect::<Vec<_>>().join(", ")
        ),
        D::Dəst(s) => {
            let el = dəst_sırası(&s.borrow());
            if el.is_empty() {
                "set()".into()
            } else {
                format!("{{{}}}", el.iter().map(py_repr).collect::<Vec<_>>().join(", "))
            }
        }
        D::Bayt(b) => {
            let mut s = String::from("b'");
            for &c in b.iter() {
                match c {
                    b'\\' => s.push_str("\\\\"),
                    b'\'' => s.push_str("\\'"),
                    b'\n' => s.push_str("\\n"),
                    b'\r' => s.push_str("\\r"),
                    b'\t' => s.push_str("\\t"),
                    0x20..=0x7e => s.push(c as char),
                    _ => s.push_str(&format!("\\x{:02x}", c)),
                }
            }
            s.push('\'');
            s
        }
        D::Nümunə(n) => format!("<{} nümunəsi>", n.sinif.ad),
        D::Element(e) => {
            let ad = if e.ad.is_empty() { "parça".to_string() } else { e.ad.to_string() };
            format!("<{} {} uşaq>", ad, e.uşaqlar().len())
        }
        _ => py_str(d),
    }
}

pub fn str_repr(s: &str) -> String {
    let q = if s.contains('\'') && !s.contains('"') { '"' } else { '\'' };
    let mut n = String::new();
    n.push(q);
    for c in s.chars() {
        match c {
            '\\' => n.push_str("\\\\"),
            '\n' => n.push_str("\\n"),
            '\r' => n.push_str("\\r"),
            '\t' => n.push_str("\\t"),
            c if c == q => {
                n.push('\\');
                n.push(c)
            }
            c if (c as u32) < 0x20 || c as u32 == 0x7f => n.push_str(&format!("\\x{:02x}", c as u32)),
            c => n.push(c),
        }
    }
    n.push(q);
    n
}

// ── HTML ───────────────────────────────────────────────────────────────

pub const TƏK_TEQLƏR: &[&str] =
    &["br", "img", "input", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"];

pub fn atribut_html_adı(a: &str) -> &str {
    match a {
        "sinif" => "class",
        "üslub" => "style",
        "dəyər" => "value",
        "yerTutucu" => "placeholder",
        "növ" => "type",
        "başlıq" => "title",
        "mənbə" => "src",
        "ünvan" => "href",
        "alt" => "alt",
        "ad" => "name",
        "id" => "id",
        "açar" => "key",
        "hədəf" => "target",
        "en" => "width",
        "hündürlük" => "height",
        "söndürülüb" => "disabled",
        "oxunan" => "readonly",
        "tələbolunan" => "required",
        "seçilib" => "checked",
        "maksimum" => "max",
        "minimum" => "min",
        x => x,
    }
}

pub const HADİSƏ_ATRIBUTLARI: &[&str] = &[
    "klik", "ikiKlik", "dəyişdi", "göndərildi", "fokus", "fokusGetdi", "düyməBasma", "düyməBuraxma",
    "siçanÜstdə", "siçanÇıxdı", "sürükləndi", "buraxıldı", "sürüşdü", "basıldı", "quraşdırıldı",
];

pub fn html_qaç(m: &str) -> String {
    let mut n = String::with_capacity(m.len());
    for c in m.chars() {
        match c {
            '&' => n.push_str("&amp;"),
            '<' => n.push_str("&lt;"),
            '>' => n.push_str("&gt;"),
            '"' => n.push_str("&quot;"),
            '\'' => n.push_str("&#39;"),
            c => n.push(c),
        }
    }
    n
}

pub fn çağırıla_bilən(d: &D) -> bool {
    matches!(
        d,
        D::Funksiya(_) | D::Daxili(_) | D::Metod(_) | D::Sinif(_) | D::XətaSinfi(_) | D::Variant(_)
    )
}

pub fn element_html(i: &İcraçı, e: &Element) -> Nəticə<String> {
    let uşaqlar = e.uşaqlar();
    if e.ad.is_empty() {
        let mut s = String::new();
        for u in &uşaqlar {
            s.push_str(&uşaq_html(i, u)?);
        }
        return Ok(s);
    }
    let mut atr = String::new();
    let c: Vec<(D, D)> = e.atributlar().borrow().iter().map(|(k, v)| (k.0.clone(), v.clone())).collect();
    for (a, d) in &c {
        let a = mətnə(i, a)?;
        if HADİSƏ_ATRIBUTLARI.contains(&a.as_str()) || çağırıla_bilən(d) {
            continue;
        }
        let h = atribut_html_adı(&a);
        match d {
            D::M(true) => {
                atr.push(' ');
                atr.push_str(h)
            }
            D::M(false) | D::Boş => continue,
            _ => atr.push_str(&format!(" {}=\"{}\"", h, html_qaç(&mətnə(i, d)?))),
        }
    }
    if TƏK_TEQLƏR.contains(&&*e.ad) {
        return Ok(format!("<{}{}>", e.ad, atr));
    }
    let mut içi = String::new();
    for u in &uşaqlar {
        içi.push_str(&uşaq_html(i, u)?);
    }
    Ok(format!("<{}{}>{}</{}>", e.ad, atr, içi, e.ad))
}

fn uşaq_html(i: &İcraçı, u: &D) -> Nəticə<String> {
    Ok(match u {
        D::Element(e) => element_html(i, e)?,
        D::S(s) => html_qaç(s),
        D::Siyahı(l) => {
            let l = l.borrow().clone();
            let mut s = String::new();
            for x in &l {
                s.push_str(&uşaq_html(i, x)?);
            }
            s
        }
        D::Kortej(l) => {
            let mut s = String::new();
            for x in l.iter() {
                s.push_str(&uşaq_html(i, x)?);
            }
            s
        }
        D::Boş | D::M(false) => String::new(),
        D::M(true) => "doğru".into(),
        x => html_qaç(&mətnə(i, x)?),
    })
}

pub fn element_mətn(i: &İcraçı, e: &Element) -> Nəticə<String> {
    let mut s = String::new();
    for u in e.uşaqlar() {
        match &u {
            D::Element(x) => s.push_str(&element_mətn(i, x)?),
            D::S(x) => s.push_str(x),
            x => s.push_str(&mətnə(i, x)?),
        }
    }
    Ok(s)
}

pub fn sıfırdır(b: &BigInt) -> bool {
    b.is_zero()
}
