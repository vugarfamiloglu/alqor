//! İnterpretator (icraci.py) — AAC-ni birbaşa icra edir.

use super::deyerler::*;
use super::muhit::{Mühit, MühitD};
use crate::aac::{self, Bağlama, BağlamaNöv, Cümlə, LiteralD, Naxış, Tip, İfadə};
use crate::xeta::Yer;
use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::io::{BufRead, Write};
use std::path::PathBuf;
use std::rc::Rc;

pub const STEK_HƏDDİ: usize = 1000;
pub const KORUTİN_STEKİ: usize = 64 * 1024 * 1024;

pub type Yielder = corosensei::Yielder<(), D>;

pub enum Çıxış {
    Std(std::io::BufWriter<std::io::Stdout>),
    Yaddaş(Vec<String>),
}

pub struct İcraçı {
    pub qlobal: Mühit,
    pub çıxış: RefCell<Çıxış>,
    pub giriş: RefCell<Option<std::io::BufReader<std::io::Stdin>>>,
    pub giriş_növbəsi: RefCell<Option<std::collections::VecDeque<String>>>,
    pub proqram_arqumentləri: RefCell<Vec<String>>,
    pub əsas_qovluq: RefCell<Option<PathBuf>>,
    pub dərinlik: Cell<usize>,
    pub gecikdirilmiş: RefCell<Vec<Vec<(aac::E, Mühit)>>>,
    pub ver: Cell<*const Yielder>,
    pub genişlətmələr: RefCell<FxMap<String, FxMap<Ad, Rc<Funksiya>>>>,
    pub fayl_modulları: RefCell<HashMap<PathBuf, Rc<Modul>>>,
    pub təsadüfi: RefCell<super::modullar::MT>,
    pub ölçü_başlanğıc: std::time::Instant,
}

/// İterator
pub enum İter {
    Siyahı(Rc<RefCell<Vec<D>>>, usize),
    Vec(std::vec::IntoIter<D>),
    Diapazon(i64, i64, i64),
    Gen(Rc<Generator>),
    Nümunə(D, i64, i64),
}

impl İter {
    pub fn növbəti(&mut self, i: &İcraçı, yer: Option<Yer>) -> Nəticə<Option<D>> {
        match self {
            İter::Siyahı(l, k) => {
                let l = l.borrow();
                if *k < l.len() {
                    *k += 1;
                    Ok(Some(l[*k - 1].clone()))
                } else {
                    Ok(None)
                }
            }
            İter::Vec(v) => Ok(v.next()),
            İter::Diapazon(c, h, a) => {
                if (*a > 0 && *c < *h) || (*a < 0 && *c > *h) {
                    let x = *c;
                    *c = c.saturating_add(*a);
                    if *c == x {
                        *h = x;
                    }
                    Ok(Some(D::T(x)))
                } else {
                    Ok(None)
                }
            }
            İter::Gen(g) => g.növbəti(i),
            İter::Nümunə(d, n, k) => {
                if *k < *n {
                    *k += 1;
                    let d = d.clone();
                    Ok(Some(i.indeks_al(&d, &D::T(*k - 1), yer)?))
                } else {
                    Ok(None)
                }
            }
        }
    }
    pub fn hamısı(mut self, i: &İcraçı, yer: Option<Yer>) -> Nəticə<Vec<D>> {
        if let İter::Vec(v) = self {
            return Ok(v.collect());
        }
        let mut n = vec![];
        while let Some(x) = self.növbəti(i, yer)? {
            n.push(x);
        }
        Ok(n)
    }
}

impl Generator {
    pub fn yeni(m: GenMənbə) -> Rc<Generator> {
        Rc::new(Generator { mənbə: RefCell::new(m), bitdi: Cell::new(false), korutin_bitdi: Cell::new(false) })
    }

    /// Növbəti dəyər; bitibsə `None`.
    pub fn növbəti(self: &Rc<Self>, i: &İcraçı) -> Nəticə<Option<D>> {
        if self.bitdi.get() {
            return Ok(None);
        }
        let r = self.xam_növbəti(i);
        if let Ok(None) = r {
            self.bitdi.set(true);
        }
        r
    }

    fn xam_növbəti(self: &Rc<Self>, i: &İcraçı) -> Nəticə<Option<D>> {
        let mut m = match self.mənbə.try_borrow_mut() {
            Ok(m) => m,
            Err(_) => return Err(xəta("Xəta", "generator artıq icra olunur", "ALQ-R014")),
        };
        match &mut *m {
            GenMənbə::Korutin(co, _) => {
                if self.korutin_bitdi.get() {
                    return Ok(None);
                }
                let saxla = (i.ver.get(), i.dərinlik.get(), i.gecikdirilmiş.take());
                let r = co.resume(());
                i.ver.set(saxla.0);
                i.dərinlik.set(saxla.1);
                *i.gecikdirilmiş.borrow_mut() = saxla.2;
                match r {
                    corosensei::CoroutineResult::Yield(d) => Ok(Some(d)),
                    corosensei::CoroutineResult::Return(r) => {
                        self.korutin_bitdi.set(true);
                        r.map(|_| None)
                    }
                }
            }
            GenMənbə::Siyahı(it) => Ok(it.next()),
            GenMənbə::Çevir(g, f) => {
                let (g, f) = (g.clone(), f.clone());
                drop(m);
                match g.növbəti(i)? {
                    Some(x) => Ok(Some(i.çağır(&f, vec![x], vec![], None)?)),
                    None => Ok(None),
                }
            }
            GenMənbə::Filtr(g, f) => {
                let (g, f) = (g.clone(), f.clone());
                drop(m);
                loop {
                    match g.növbəti(i)? {
                        Some(x) => {
                            if let D::M(true) = i.çağır(&f, vec![x.clone()], vec![], None)? {
                                return Ok(Some(x));
                            }
                        }
                        None => return Ok(None),
                    }
                }
            }
            GenMənbə::Atla(g, n, atlanan) => {
                let g = g.clone();
                loop {
                    match g.növbəti(i)? {
                        Some(x) => {
                            if bool_lt_i(*atlanan, n) {
                                *atlanan += 1;
                                continue;
                            }
                            return Ok(Some(x));
                        }
                        None => return Ok(None),
                    }
                }
            }
            GenMənbə::Bitdi => Ok(None),
        }
    }

    pub fn bağla(&self) {
        if let Ok(mut m) = self.mənbə.try_borrow_mut() {
            *m = GenMənbə::Bitdi;
        }
        self.bitdi.set(true);
    }
}

fn bool_lt_i(a: i64, n: &D) -> bool {
    match n {
        D::T(x) => a < *x,
        D::O(x) => (a as f64) < *x,
        D::M(b) => a < *b as i64,
        D::BT(b) => num_bigint::BigInt::from(a) < **b,
        _ => false,
    }
}

impl Gələcək {
    pub fn yeni(ad_: &str, f: impl FnOnce(&İcraçı) -> Nəticə + 'static) -> Rc<Gələcək> {
        Rc::new(Gələcək { ad: ad(ad_), iş: RefCell::new(Some(Box::new(f))), nəticə: RefCell::new(None) })
    }
    pub fn başlat(&self, i: &İcraçı) {
        if self.nəticə.borrow().is_some() {
            return;
        }
        let iş = self.iş.borrow_mut().take();
        if let Some(f) = iş {
            let köhnə = i.ver.replace(std::ptr::null());
            let r = f(i);
            i.ver.set(köhnə);
            *self.nəticə.borrow_mut() = Some(r);
        }
    }
    pub fn al(&self, i: &İcraçı) -> Nəticə {
        if self.nəticə.borrow().is_none() {
            let iş = self.iş.borrow_mut().take();
            if let Some(f) = iş {
                let r = f(i);
                *self.nəticə.borrow_mut() = Some(r);
            }
        }
        match &*self.nəticə.borrow() {
            Some(r) => r.clone(),
            None => Ok(D::Boş),
        }
    }
    pub fn bitdi(&self) -> bool {
        self.nəticə.borrow().is_some()
    }
    pub fn uğurlu(&self) -> bool {
        matches!(&*self.nəticə.borrow(), Some(Ok(_)))
    }
}

fn cümlə_adı(c: &Cümlə) -> &'static str {
    match c {
        Cümlə::Metod(_) => "MetodElanı",
        Cümlə::Xassə(_) => "XassəElanı",
        Cümlə::Qurucu(_) => "QurucuElanı",
        Cümlə::Dağıdıcı(..) => "DağıdıcıElanı",
        _ => "Cümlə",
    }
}

impl İcraçı {
    pub fn yeni() -> &'static İcraçı {
        let i = Box::leak(Box::new(İcraçı {
            qlobal: MühitD::yeni(None),
            çıxış: RefCell::new(Çıxış::Std(std::io::BufWriter::with_capacity(1 << 16, std::io::stdout()))),
            giriş: RefCell::new(None),
            giriş_növbəsi: RefCell::new(None),
            proqram_arqumentləri: RefCell::new(vec![]),
            əsas_qovluq: RefCell::new(None),
            dərinlik: Cell::new(0),
            gecikdirilmiş: RefCell::new(vec![]),
            ver: Cell::new(std::ptr::null()),
            genişlətmələr: Default::default(),
            fayl_modulları: Default::default(),
            təsadüfi: RefCell::new(super::modullar::MT::təsadüfi()),
            ölçü_başlanğıc: std::time::Instant::now(),
        }));
        super::kitabxana::qlobal_qur(i);
        i
    }

    pub fn statik(&self) -> &'static İcraçı {
        unsafe { &*(self as *const İcraçı) }
    }

    // ── Giriş / çıxış ─────────────────────────────────────────────────

    pub fn yaz(&self, s: &str) {
        match &mut *self.çıxış.borrow_mut() {
            Çıxış::Std(w) => {
                let _ = w.write_all(s.as_bytes());
                let _ = w.write_all(b"\n");
            }
            Çıxış::Yaddaş(v) => v.push(s.to_string()),
        }
    }

    pub fn yaz_xam(&self, s: &str) {
        match &mut *self.çıxış.borrow_mut() {
            Çıxış::Std(w) => {
                let _ = w.write_all(s.as_bytes());
                let _ = w.flush();
            }
            Çıxış::Yaddaş(v) => v.push(s.to_string()),
        }
    }

    pub fn boşalt(&self) {
        if let Çıxış::Std(w) = &mut *self.çıxış.borrow_mut() {
            let _ = w.flush();
        }
    }

    pub fn xəta_yaz(&self, s: &str) {
        self.boşalt();
        eprintln!("{s}");
    }

    /// Bir sətir oxuyur; girişin sonunda `None`.
    pub fn sətir_oxu(&self) -> Option<String> {
        if let Some(n) = &mut *self.giriş_növbəsi.borrow_mut() {
            return Some(n.pop_front().unwrap_or_default());
        }
        self.boşalt();
        let mut g = self.giriş.borrow_mut();
        if g.is_none() {
            *g = Some(std::io::BufReader::new(std::io::stdin()));
        }
        let mut s = String::new();
        match g.as_mut().unwrap().read_line(&mut s) {
            Ok(0) | Err(_) => None,
            Ok(_) => {
                if s.ends_with('\n') {
                    s.pop();
                    if s.ends_with('\r') {
                        s.pop();
                    }
                }
                Some(s)
            }
        }
    }

    pub fn hamısını_oxu(&self) -> String {
        self.boşalt();
        let mut g = self.giriş.borrow_mut();
        if g.is_none() {
            *g = Some(std::io::BufReader::new(std::io::stdin()));
        }
        let mut s = String::new();
        let _ = std::io::Read::read_to_string(g.as_mut().unwrap(), &mut s);
        s
    }

    // ═══════════════════════════════════════════════════════════════════
    //  Giriş nöqtəsi
    // ═══════════════════════════════════════════════════════════════════

    /// Proqramı icra edir; çıxış kodu və ya tutulmamış xəta.
    pub fn işlət(&self, gövdə: &[Cümlə], arqumentlər: Vec<String>) -> Result<i32, Box<AlqorXəta>> {
        *self.proqram_arqumentləri.borrow_mut() = arqumentlər.clone();
        let m = self.qlobal.clone();
        let r = (|| -> Nəticə<i32> {
            self.elanları_qaldır(gövdə, &m)?;
            for c in gövdə {
                if !elandır(c) {
                    self.cümlə(c, &m)?;
                }
            }
            if let Some(əsas) = m.burada_al("əsas") {
                if çağırıla_bilən(&əsas) || matches!(əsas, D::Nümunə(_) | D::Modul(_)) {
                    let çağırılan = matches!(əsas, D::Funksiya(_) | D::Daxili(_) | D::Metod(_) | D::Sinif(_) | D::XətaSinfi(_));
                    if çağırılan {
                        let arq = match &əsas {
                            D::Funksiya(f) if !f.parametrlər.is_empty() => {
                                vec![D::siyahı(arqumentlər.iter().map(|s| D::s(s)).collect())]
                            }
                            _ => vec![],
                        };
                        let mut n = self.çağır(&əsas, arq, vec![], None)?;
                        if let D::Gələcək(g) = &n {
                            n = g.al(self)?;
                        }
                        if let D::T(k) = n {
                            return Ok(k as i32);
                        }
                        if let D::BT(b) = &n {
                            use num_traits::ToPrimitive;
                            return Ok((b.as_ref() % 256u32).to_i32().unwrap_or(1));
                        }
                    }
                }
            }
            Ok(0)
        })();
        self.boşalt();
        match r {
            Ok(k) => Ok(k),
            Err(Siqnal::Dayanma(k)) => Ok(match k {
                D::T(k) => k as i32,
                D::Boş => 0,
                D::M(b) => b as i32,
                x => {
                    let s = mətnə(self, &x).unwrap_or_default();
                    self.xəta_yaz(&s);
                    1
                }
            }),
            Err(Siqnal::Qaytar(_)) => Ok(0),
            Err(Siqnal::Xəta(x)) => Err(x),
            Err(Siqnal::Dayan(_)) | Err(Siqnal::Davam(_)) | Err(Siqnal::Ver(_)) => Err(Box::new(AlqorXəta {
                tip: ad("DaxiliXəta"),
                mesaj: "dövr və ya blok xaricində axın siqnalı".into(),
                yer: None,
                kod: String::new(),
                dəyər: None,
            })),
        }
    }

    pub fn elanları_qaldır(&self, gövdə: &[Cümlə], m: &Mühit) -> Nəticə<()> {
        for c in gövdə {
            if let Cümlə::İdxal { .. } = c {
                self.cümlə(c, m)?;
            }
        }
        for c in gövdə {
            if let Cümlə::Funksiya(_) = c {
                self.cümlə(c, m)?;
            }
        }
        for c in gövdə {
            if matches!(c, Cümlə::Sinif(_) | Cümlə::Sadalama { .. } | Cümlə::İnterfeys { .. } | Cümlə::Qarışıq { .. }) {
                self.cümlə(c, m)?;
            }
        }
        Ok(())
    }

    // ═══════════════════════════════════════════════════════════════════
    //  Cümlələr
    // ═══════════════════════════════════════════════════════════════════

    #[inline]
    pub fn blok(&self, gövdə: &[Cümlə], m: &Mühit) -> Nəticə<()> {
        for c in gövdə {
            self.cümlə(c, m)?;
        }
        Ok(())
    }

    pub fn cümlə(&self, c: &Cümlə, m: &Mühit) -> Nəticə<()> {
        match c {
            Cümlə::İfadə(_, e) => {
                self.ifadə(e, m)?;
                Ok(())
            }
            Cümlə::DəyişənElanı { yer, növ, bağlamalar, dəyərlər } => {
                self.c_dəyişən(*yer, növ, bağlamalar, dəyərlər, m)
            }
            Cümlə::Şərt { budaqlar, yoxsa, .. } => {
                for (ş, g) in budaqlar {
                    if self.məntiq(ş, m)? {
                        return self.blok(g, &m.alt());
                    }
                }
                if let Some(y) = yoxsa {
                    self.blok(y, &m.alt())?;
                }
                Ok(())
            }
            Cümlə::Varsa { bağlamalar, gövdə, yoxsa, .. } => {
                let alt = m.alt();
                for (b, e) in bağlamalar {
                    let d = self.ifadə(e, &alt)?;
                    if matches!(d, D::Boş | D::M(false)) {
                        if let Some(y) = yoxsa {
                            self.blok(y, &m.alt())?;
                        }
                        return Ok(());
                    }
                    if let Some(b) = b {
                        self.bağla(b, d, &alt, true, false)?;
                    }
                }
                self.blok(gövdə, &alt)
            }
            Cümlə::Yoxdursa { bağlamalar, gövdə, .. } => {
                let mut hamısı = true;
                for (b, e) in bağlamalar {
                    let d = self.ifadə(e, m)?;
                    if matches!(d, D::Boş | D::M(false)) {
                        hamısı = false;
                        break;
                    }
                    if let Some(b) = b {
                        self.bağla(b, d, m, true, false)?;
                    }
                }
                if !hamısı {
                    self.blok(gövdə, &m.alt())?;
                }
                Ok(())
            }
            Cümlə::Seç { yer, ifadə, hallar, digər } => self.c_seç(*yer, ifadə.as_ref(), hallar, digər.as_ref(), m),
            Cümlə::NəQədərKi { şərt, gövdə, etiket, .. } => {
                while self.məntiq(şərt, m)? {
                    if self.dövr_gövdəsi(gövdə, &m.alt(), etiket)? {
                        break;
                    }
                }
                Ok(())
            }
            Cümlə::Həmişə { gövdə, etiket, .. } => {
                loop {
                    if self.dövr_gövdəsi(gövdə, &m.alt(), etiket)? {
                        break;
                    }
                }
                Ok(())
            }
            Cümlə::Təkrarla { yer, say, gövdə, sayğac, etiket } => {
                let s = self.ifadə(say, m)?;
                let n = match &s {
                    D::T(n) => *n,
                    D::BT(_) => i64::MAX,
                    _ => {
                        return Err(xəta_yer(
                            "TipXətası",
                            format!("`təkrarla` tam ədəd gözləyir, `{}` gəlib", tip_adı(&s)),
                            Some(*yer),
                            "ALQ-T001",
                        ))
                    }
                };
                let sayğac = sayğac.as_ref().map(|s| ad(s));
                let mut i = 1;
                while i <= n {
                    let alt = m.alt();
                    if let Some(s) = &sayğac {
                        alt.elan(s.clone(), D::T(i), false);
                    }
                    if self.dövr_gövdəsi(gövdə, &alt, etiket)? {
                        break;
                    }
                    i += 1;
                }
                Ok(())
            }
            Cümlə::TəkrarlaNəQədər { gövdə, şərt, etiket, .. } => {
                loop {
                    if self.dövr_gövdəsi(gövdə, &m.alt(), etiket)? {
                        break;
                    }
                    if !self.məntiq(şərt, m)? {
                        break;
                    }
                }
                Ok(())
            }
            Cümlə::Hər { yer, bağlamalar, mənbə, gövdə, addım, şərt, yoxsa, asinxron, etiket } => {
                self.c_hər(*yer, bağlamalar, mənbə, gövdə, addım.as_ref(), şərt.as_ref(), yoxsa.as_ref(), *asinxron, etiket, m)
            }
            Cümlə::Dayan(_, e) => Err(Siqnal::Dayan(e.as_ref().map(|s| ad(s)))),
            Cümlə::DavamEt(_, e) => Err(Siqnal::Davam(e.as_ref().map(|s| ad(s)))),
            Cümlə::Qaytar(_, dəyərlər) => {
                if dəyərlər.is_empty() {
                    return Err(Siqnal::Qaytar(D::Boş));
                }
                if dəyərlər.len() == 1 {
                    return Err(Siqnal::Qaytar(self.ifadə(&dəyərlər[0], m)?));
                }
                let mut v = Vec::with_capacity(dəyərlər.len());
                for d in dəyərlər {
                    v.push(self.ifadə(d, m)?);
                }
                Err(Siqnal::Qaytar(D::kortej(v)))
            }
            Cümlə::Ver(_, d) => {
                let d = match d {
                    Some(e) => self.ifadə(e, m)?,
                    None => D::Boş,
                };
                let v = self.ver.get();
                if !v.is_null() {
                    let saxla = (self.dərinlik.get(), self.gecikdirilmiş.take());
                    unsafe { (*v).suspend(d) };
                    self.ver.set(v);
                    self.dərinlik.set(saxla.0);
                    *self.gecikdirilmiş.borrow_mut() = saxla.1;
                    return Ok(());
                }
                Err(Siqnal::Ver(d))
            }
            Cümlə::At(yer, e) => {
                let e = match e {
                    None => return Err(xəta_yer("Xəta", "təkrar atılacaq xəta yoxdur", Some(*yer), "")),
                    Some(e) => e,
                };
                let d = self.ifadə(e, m)?;
                if let D::Nümunə(n) = &d {
                    let mesaj = match n.sahə("mesaj") {
                        Some(x) => mətnə(self, &x)?,
                        None => String::new(),
                    };
                    return Err(Siqnal::Xəta(Box::new(AlqorXəta {
                        tip: n.sinif.ad.clone(),
                        mesaj,
                        yer: Some(*yer),
                        kod: String::new(),
                        dəyər: Some(d.clone()),
                    })));
                }
                let mesaj = mətnə(self, &d)?;
                Err(Siqnal::Xəta(Box::new(AlqorXəta {
                    tip: ad("Xəta"),
                    mesaj,
                    yer: Some(*yer),
                    kod: String::new(),
                    dəyər: Some(d),
                })))
            }
            Cümlə::Cəhd { gövdə, tutmalar, nəhayət, .. } => self.c_cəhd(gövdə, tutmalar, nəhayət.as_ref(), m),
            Cümlə::İddia(yer, ş, mesaj) => {
                if self.məntiq(ş, m)? {
                    return Ok(());
                }
                let mesaj = match mesaj {
                    Some(e) => {
                        let d = self.ifadə(e, m)?;
                        mətnə(self, &d)?
                    }
                    None => "iddia pozuldu".into(),
                };
                Err(xəta_yer("İddiaXətası", mesaj, Some(*yer), "ALQ-R007"))
            }
            Cümlə::Təmin(_, ş, gövdə) => {
                if !self.məntiq(ş, m)? {
                    self.blok(gövdə, &m.alt())?;
                }
                Ok(())
            }
            Cümlə::Gecikdir(_, e) => {
                let mut y = self.gecikdirilmiş.borrow_mut();
                if let Some(son) = y.last_mut() {
                    son.push((e.clone(), m.clone()));
                    return Ok(());
                }
                drop(y);
                self.ifadə(e, m)?;
                Ok(())
            }
            Cümlə::İstifadə(yer, bağlamalar, gövdə) => {
                let alt = m.alt();
                let mut açıqlar = vec![];
                let mut r = Ok(());
                for (a, e) in bağlamalar {
                    match self.ifadə(e, &alt) {
                        Ok(d) => {
                            alt.elan(ad(a), d.clone(), false);
                            açıqlar.push(d);
                        }
                        Err(x) => {
                            r = Err(x);
                            break;
                        }
                    }
                }
                if r.is_ok() {
                    r = self.blok(gövdə, &alt);
                }
                for d in açıqlar.iter().rev() {
                    let b = self.bağla_resurs(d, Some(*yer));
                    if b.is_err() {
                        return b;
                    }
                }
                r
            }
            Cümlə::Keç(_) | Cümlə::İxracSiyahısı(_) | Cümlə::Bitiş(..) => Ok(()),
            Cümlə::DayanNöqtəsi(_) => {
                self.yaz("⏸ dayanNöqtəsi — debaq hələ qoşulmayıb");
                Ok(())
            }
            Cümlə::Global(_, adlar) => {
                for a in adlar {
                    m.qloballar.borrow_mut().push(ad(a));
                }
                Ok(())
            }
            Cümlə::Funksiya(f) => {
                let annot = Annot {
                    yaddaşla: f.annotasiyalar.iter().any(|a| a == "yaddaşla"),
                    tənbəl: false,
                    statik: false,
                };
                let ff = Funksiya {
                    ad: ad(&f.ad),
                    parametrlər: f.parametrlər.clone(),
                    gövdə: FGövdə::Blok(f.gövdə.clone().unwrap_or_default()),
                    mühit: m.clone(),
                    asinxron: f.asinxron,
                    generator: f.generator,
                    özü: None,
                    sinif: None,
                    annot,
                    yaddaş: if annot.yaddaşla { Some(Default::default()) } else { None },
                };
                m.elan(ad(&f.ad), D::Funksiya(Rc::new(ff)), false);
                Ok(())
            }
            Cümlə::Sinif(s) => self.c_sinif(s, m),
            Cümlə::İnterfeys { ad: a, üzvlər, .. } => self.c_interfeys(a, üzvlər, m),
            Cümlə::Qarışıq { ad: a, üzvlər, .. } => self.c_qarışıq(a, üzvlər, m),
            Cümlə::Sadalama { ad: a, variantlar, üzvlər, əsas_tip, .. } => {
                self.c_sadalama(a, variantlar, üzvlər, əsas_tip.as_ref(), m)
            }
            Cümlə::TipAliası { ad: a, tip, .. } => {
                m.elan(ad(a), D::TipAliası(Rc::new((ad(a), tip.clone()))), false);
                Ok(())
            }
            Cümlə::Genişlətmə { tip, üzvlər, .. } => self.c_genişlətmə(tip, üzvlər, m),
            Cümlə::Modul { ad: a, gövdə, .. } => {
                let alt = m.alt();
                self.elanları_qaldır(gövdə, &alt)?;
                for c in gövdə.iter() {
                    if !elandır(c) {
                        self.cümlə(c, &alt)?;
                    }
                }
                let üzvlər = alt.hamısı().into_iter().collect();
                let md = Rc::new(Modul { ad: RefCell::new(ad(a)), üzvlər: RefCell::new(üzvlər), çağırışçı: None });
                m.elan(ad(a), D::Modul(md), false);
                Ok(())
            }
            Cümlə::İdxal { yer, yol, mətn_yolu, ləqəb, elementlər, hamısı } => {
                self.c_idxal(*yer, yol, mətn_yolu.as_deref(), ləqəb.as_deref(), elementlər, *hamısı, m)
            }
            Cümlə::Başlanğıc(_, g) => self.blok(g, &m.alt()),
            Cümlə::Artırma(yer, hədəf, op) => {
                let cari = self.ifadə(hədəf, m)?;
                let yeni = match &cari {
                    D::T(_) | D::BT(_) | D::O(_) => {
                        self.ikili_hesabla(if op == "++" { "+" } else { "-" }, &cari, &D::T(1), Some(*yer))?
                    }
                    _ => {
                        return Err(xəta_yer(
                            "TipXətası",
                            format!("`{}` ədəd gözləyir, `{}` gəlib", op, tip_adı(&cari)),
                            Some(*yer),
                            "ALQ-T008",
                        ))
                    }
                };
                self.mənimsət(hədəf, yeni, m)
            }
            Cümlə::Metod(_) | Cümlə::Xassə(_) | Cümlə::Qurucu(_) | Cümlə::Dağıdıcı(..) => Err(xəta_yer(
                "DaxiliXəta",
                format!("icra olunmayan qovşaq: {}", cümlə_adı(c)),
                Some(c.yer()),
                "",
            )),
        }
    }

    fn c_dəyişən(&self, yer: Yer, növ: &str, bağlamalar: &[Bağlama], dəyərlər: &[aac::E], m: &Mühit) -> Nəticə<()> {
        let sabit = növ == "sabit" || növ == "dəyişməz";
        if dəyərlər.is_empty() {
            for b in bağlamalar {
                let d = standart_dəyər(b.tip.as_ref());
                self.bağla(b, d, m, true, sabit)?;
            }
            return Ok(());
        }
        if bağlamalar.len() == 1 {
            let d = if dəyərlər.len() == 1 {
                self.ifadə(&dəyərlər[0], m)?
            } else {
                let mut v = vec![];
                for e in dəyərlər {
                    v.push(self.ifadə(e, m)?);
                }
                D::siyahı(v)
            };
            return self.bağla(&bağlamalar[0], d, m, true, sabit);
        }
        if dəyərlər.len() == 1 {
            let d = self.ifadə(&dəyərlər[0], m)?;
            return self.çoxlu_bağla(bağlamalar, d, m, true, sabit, Some(yer));
        }
        if dəyərlər.len() != bağlamalar.len() {
            return Err(xəta_yer(
                "ArqumentXətası",
                format!("{} ad, {} dəyər — saylar uyğun gəlmir", bağlamalar.len(), dəyərlər.len()),
                Some(yer),
                "ALQ-T001",
            ));
        }
        let mut v = vec![];
        for e in dəyərlər {
            v.push(self.ifadə(e, m)?);
        }
        for (b, d) in bağlamalar.iter().zip(v) {
            self.bağla(b, d, m, true, sabit)?;
        }
        Ok(())
    }

    // ── Bağlama (dağıtma) ─────────────────────────────────────────────

    pub fn bağla(&self, b: &Bağlama, d: D, m: &Mühit, elan: bool, sabit: bool) -> Nəticə<()> {
        match &b.növ {
            BağlamaNöv::Atma => Ok(()),
            BağlamaNöv::Ad(a) => {
                let d = dəyər_kopyası(genişlət(d, b.tip.as_ref()));
                if elan {
                    m.elan(ad(a), d, sabit);
                    Ok(())
                } else {
                    m.təyin(a, d)
                }
            }
            BağlamaNöv::Qalan(a) => {
                if elan {
                    m.elan(ad(a), d, sabit);
                    Ok(())
                } else {
                    m.təyin(a, d)
                }
            }
            BağlamaNöv::Kortej(alt) => self.çoxlu_bağla(alt, d, m, elan, sabit, Some(b.yer)),
            BağlamaNöv::Obyekt(sahələr) => {
                for (a, alt) in sahələr {
                    let sahə = self.üzv_al(&d, a, Some(b.yer))?;
                    match alt {
                        None => {
                            if elan {
                                m.elan(ad(a), sahə, sabit);
                            } else {
                                m.təyin(a, sahə)?;
                            }
                        }
                        Some(alt) => self.bağla(alt, sahə, m, elan, sabit)?,
                    }
                }
                Ok(())
            }
        }
    }

    pub fn çoxlu_bağla(&self, bağlamalar: &[Bağlama], d: D, m: &Mühit, elan: bool, sabit: bool, yer: Option<Yer>) -> Nəticə<()> {
        let el = match self.iterasiya(&d, yer).and_then(|it| it.hamısı(self, yer)) {
            Ok(v) => v,
            Err(Siqnal::Xəta(_)) => {
                return Err(xəta_yer("TipXətası", format!("`{}` dağıtıla bilməz", tip_adı(&d)), yer, "ALQ-T001"))
            }
            Err(x) => return Err(x),
        };
        let qalan = bağlamalar.iter().position(|b| matches!(b.növ, BağlamaNöv::Qalan(_)));
        match qalan {
            None => {
                if el.len() != bağlamalar.len() {
                    return Err(xəta_yer(
                        "ArqumentXətası",
                        format!("{} ad gözlənilirdi, {} dəyər var", bağlamalar.len(), el.len()),
                        yer,
                        "ALQ-T001",
                    ));
                }
                for (b, x) in bağlamalar.iter().zip(el) {
                    self.bağla(b, x, m, elan, sabit)?;
                }
                Ok(())
            }
            Some(q) => {
                let əvvəl = &bağlamalar[..q];
                let sonra = &bağlamalar[q + 1..];
                if el.len() < əvvəl.len() + sonra.len() {
                    return Err(xəta_yer("ArqumentXətası", "dağıtma üçün element çatmır", yer, "ALQ-T001"));
                }
                for (b, x) in əvvəl.iter().zip(el.iter()) {
                    self.bağla(b, x.clone(), m, elan, sabit)?;
                }
                let orta = el[əvvəl.len()..el.len() - sonra.len()].to_vec();
                self.bağla(&bağlamalar[q], D::siyahı(orta), m, elan, sabit)?;
                for (b, x) in sonra.iter().zip(el[el.len() - sonra.len()..].iter()) {
                    self.bağla(b, x.clone(), m, elan, sabit)?;
                }
                Ok(())
            }
        }
    }

    // ── Seç ───────────────────────────────────────────────────────────

    fn c_seç(&self, yer: Yer, ifadə: Option<&aac::E>, hallar: &[aac::Hal], digər: Option<&aac::Gövdə>, m: &Mühit) -> Nəticə<()> {
        let d = match ifadə {
            Some(e) => self.ifadə(e, m)?,
            None => D::Boş,
        };
        let şərtli = ifadə.is_none();
        let mut başla = None;
        for (i, hal) in hallar.iter().enumerate() {
            let alt = m.alt();
            if self.hal_uyğundur(hal, şərtli, &d, &alt, yer)? {
                başla = Some(i);
                break;
            }
        }
        let Some(mut i) = başla else {
            if let Some(g) = digər {
                self.blok(g, &m.alt())?;
            }
            return Ok(());
        };
        while i < hallar.len() {
            let hal = &hallar[i];
            let alt = m.alt();
            self.hal_uyğundur(hal, şərtli, &d, &alt, yer)?;
            self.blok(&hal.gövdə, &alt)?;
            if !hal.keç {
                return Ok(());
            }
            i += 1;
        }
        if let Some(g) = digər {
            self.blok(g, &m.alt())?;
        }
        Ok(())
    }

    fn hal_uyğundur(&self, hal: &aac::Hal, şərtli: bool, d: &D, m: &Mühit, yer: Yer) -> Nəticə<bool> {
        for n in &hal.naxışlar {
            if self.naxış_uyğunlaşdır(n, d, şərtli, m, yer)? {
                match &hal.mühafizə {
                    None => return Ok(true),
                    Some(g) => {
                        if self.məntiq(g, m)? {
                            return Ok(true);
                        }
                    }
                }
            }
        }
        Ok(false)
    }

    fn naxış_uyğunlaşdır(&self, n: &Naxış, d: &D, şərtli: bool, m: &Mühit, yer: Yer) -> Nəticə<bool> {
        match n {
            Naxış::Atma => Ok(true),
            Naxış::Literal(e) => {
                let x = self.ifadə(e, m)?;
                self.bərabərdir(&x, d)
            }
            Naxış::Şərt(e) => self.məntiq(e, m),
            Naxış::Diapazon(b, s, xaric) => {
                let b = self.ifadə(b, m)?;
                let s = self.ifadə(s, m)?;
                if !d.ədəddir() {
                    return Ok(false);
                }
                let r1 = self.müqayisə("<=", &b, d, Some(yer))?;
                if !matches!(r1, D::M(true)) {
                    return Ok(false);
                }
                let r2 = self.müqayisə(if *xaric { "<" } else { "<=" }, d, &s, Some(yer))?;
                Ok(matches!(r2, D::M(true)))
            }
            Naxış::Tip(t) => self.tip_uyğundur(d, t, m),
            Naxış::Ad(a) => {
                if şərtli {
                    let x = m.al(a)?;
                    return match x {
                        D::M(b) => Ok(b),
                        x => Err(xəta(
                            "TipXətası",
                            format!("şərt `məntiq` olmalıdır, `{}` gəlib", tip_adı(&x)),
                            "ALQ-T007",
                        )),
                    };
                }
                if let D::SD(s) = d {
                    if *s.ad == **a {
                        return Ok(true);
                    }
                }
                m.elan(a.clone(), d.clone(), false);
                Ok(true)
            }
            Naxış::Kortej(alt) => {
                let el: Vec<D> = match d {
                    D::Kortej(k) => k.to_vec(),
                    D::Siyahı(l) => l.borrow().clone(),
                    _ => return Ok(false),
                };
                if el.len() != alt.len() {
                    return Ok(false);
                }
                for (a, x) in alt.iter().zip(el.iter()) {
                    if !self.naxış_uyğunlaşdır(a, x, şərtli, m, yer)? {
                        return Ok(false);
                    }
                }
                Ok(true)
            }
            Naxış::Siyahı(alt, qalan) => {
                let el = match d {
                    D::Siyahı(l) => l.borrow().clone(),
                    _ => return Ok(false),
                };
                match qalan {
                    None => {
                        if el.len() != alt.len() {
                            return Ok(false);
                        }
                        for (a, x) in alt.iter().zip(el.iter()) {
                            if !self.naxış_uyğunlaşdır(a, x, şərtli, m, yer)? {
                                return Ok(false);
                            }
                        }
                        Ok(true)
                    }
                    Some(q) => {
                        if el.len() < alt.len() {
                            return Ok(false);
                        }
                        for (a, x) in alt.iter().zip(el.iter()) {
                            if !self.naxış_uyğunlaşdır(a, x, şərtli, m, yer)? {
                                return Ok(false);
                            }
                        }
                        m.elan(ad(q), D::siyahı(el[alt.len()..].to_vec()), false);
                        Ok(true)
                    }
                }
            }
            Naxış::Obyekt(tip, alt, sahələr) => {
                let yol: Vec<String> = match tip {
                    Some(Tip::Ad { yol, .. }) => yol.clone(),
                    _ => vec![],
                };
                if !self.obyekt_naxışı_uyğundur(d, &yol, m) {
                    return Ok(false);
                }
                for (i, a) in alt.iter().enumerate() {
                    if let D::SD(s) = d {
                        let Some((_, x)) = s.sahələr.get_index(i) else { return Ok(false) };
                        if !self.naxış_uyğunlaşdır(a, x, şərtli, m, yer)? {
                            return Ok(false);
                        }
                    }
                }
                for (a, alt) in sahələr {
                    let sahə = self.üzv_al(d, a, Some(yer))?;
                    match alt {
                        None => m.elan(ad(a), sahə, false),
                        Some(alt) => {
                            if !self.naxış_uyğunlaşdır(alt, &sahə, şərtli, m, yer)? {
                                return Ok(false);
                            }
                        }
                    }
                }
                Ok(true)
            }
        }
    }

    fn obyekt_naxışı_uyğundur(&self, d: &D, yol: &[String], m: &Mühit) -> bool {
        if yol.is_empty() {
            return true;
        }
        match d {
            D::SD(s) => {
                let n = yol.len();
                *s.ad == *yol[n - 1] || (n >= 2 && *s.sadalama.ad == *yol[n - 2] && *s.ad == *yol[n - 1])
            }
            D::Nümunə(x) => match m.al(&yol[0]) {
                Ok(D::Sinif(h)) => x.sinif.alt_sinifdirmi(&h),
                _ => false,
            },
            _ => false,
        }
    }

    // ── Dövrlər ───────────────────────────────────────────────────────

    /// `true` qaytarırsa dövr dayandırılmalıdır.
    #[inline]
    fn dövr_gövdəsi(&self, gövdə: &[Cümlə], m: &Mühit, etiket: &Option<String>) -> Nəticə<bool> {
        match self.blok(gövdə, m) {
            Ok(()) => Ok(false),
            Err(Siqnal::Dayan(e)) => {
                if let Some(e) = &e {
                    if etiket.as_deref() != Some(&**e) {
                        return Err(Siqnal::Dayan(Some(e.clone())));
                    }
                }
                Ok(true)
            }
            Err(Siqnal::Davam(e)) => {
                if let Some(e) = &e {
                    if etiket.as_deref() != Some(&**e) {
                        return Err(Siqnal::Davam(Some(e.clone())));
                    }
                }
                Ok(false)
            }
            Err(x) => Err(x),
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn c_hər(
        &self,
        yer: Yer,
        bağlamalar: &[Bağlama],
        mənbə: &aac::E,
        gövdə: &aac::Gövdə,
        addım: Option<&aac::E>,
        şərt: Option<&aac::E>,
        yoxsa: Option<&aac::Gövdə>,
        asinxron: bool,
        etiket: &Option<String>,
        m: &Mühit,
    ) -> Nəticə<()> {
        let mut mənbə = self.ifadə(mənbə, m)?;
        if let (Some(a), D::Diapazon(r)) = (addım, &mənbə) {
            let a = self.ifadə(a, m)?;
            let r = diapazon_yarat(D::T(r.başlanğıc), D::T(r.son), Some(a), r.xaric)?;
            mənbə = r;
        }
        let lüğət = if let D::Lüğət(l) = &mənbə { Some(l.clone()) } else { None };
        let çoxlu = bağlamalar.len() >= 2;
        let mut dayandı = false;
        let mut it = self.iterasiya(&mənbə, Some(yer))?;
        let mut indeks: i64 = 0;
        // Sadə hal: tək ad bağlaması
        let sadə_ad = if bağlamalar.len() == 1 {
            match &bağlamalar[0].növ {
                BağlamaNöv::Ad(a) if bağlamalar[0].tip.is_none() => Some(ad(a)),
                _ => None,
            }
        } else {
            None
        };
        while let Some(mut el) = it.növbəti(self, Some(yer))? {
            if asinxron {
                el = self.gözlə(el, Some(yer))?;
            }
            let alt = m.alt();
            if let Some(a) = &sadə_ad {
                alt.elan(a.clone(), dəyər_kopyası(el), false);
            } else if çoxlu && lüğət.is_some() {
                let l = lüğət.as_ref().unwrap();
                let v = l.borrow().get(&Açar(el.clone())).cloned();
                let v = match v {
                    Some(v) => v,
                    None => {
                        return Err(xəta_yer("AçarXətası", format!("lüğətdə `{}` açarı yoxdur", mətnə(self, &el)?), Some(yer), "ALQ-R003"))
                    }
                };
                let cüt = D::kortej(vec![el, v]);
                if bağlamalar.len() == 1 {
                    self.bağla(&bağlamalar[0], cüt, &alt, true, false)?;
                } else {
                    self.çoxlu_bağla(bağlamalar, cüt, &alt, true, false, Some(yer))?;
                }
            } else if çoxlu {
                self.bağla(&bağlamalar[0], D::T(indeks), &alt, true, false)?;
                let qalan = &bağlamalar[1..];
                if qalan.len() == 1 {
                    self.bağla(&qalan[0], el, &alt, true, false)?;
                } else {
                    self.çoxlu_bağla(qalan, el, &alt, true, false, Some(yer))?;
                }
            } else {
                self.bağla(&bağlamalar[0], el, &alt, true, false)?;
            }
            indeks += 1;
            if let Some(ş) = şərt {
                if !self.məntiq(ş, &alt)? {
                    continue;
                }
            }
            if self.dövr_gövdəsi(gövdə, &alt, etiket)? {
                dayandı = true;
                break;
            }
        }
        if !dayandı {
            if let Some(y) = yoxsa {
                self.blok(y, &m.alt())?;
            }
        }
        Ok(())
    }

    // ── Xətalar ───────────────────────────────────────────────────────

    fn c_cəhd(&self, gövdə: &aac::Gövdə, tutmalar: &[aac::Tutma], nəhayət: Option<&aac::Gövdə>, m: &Mühit) -> Nəticə<()> {
        let mut r = self.blok(gövdə, &m.alt());
        if let Err(Siqnal::Xəta(x)) = r {
            let mut tutuldu = None;
            for t in tutmalar {
                if !tutma_uyğundur(t, &x) {
                    continue;
                }
                let alt = m.alt();
                if let Some(a) = &t.ad {
                    alt.elan(ad(a), xəta_obyekti(&x), false);
                }
                if let Some(g) = &t.mühafizə {
                    match self.məntiq(g, &alt) {
                        Ok(true) => {}
                        Ok(false) => continue,
                        Err(e) => {
                            tutuldu = Some(Err(e));
                            break;
                        }
                    }
                }
                tutuldu = Some(self.blok(&t.gövdə, &alt));
                break;
            }
            r = tutuldu.unwrap_or(Err(Siqnal::Xəta(x)));
        }
        if let Some(n) = nəhayət {
            let f = self.blok(n, &m.alt());
            if f.is_err() {
                return f;
            }
        }
        r
    }

    fn bağla_resurs(&self, d: &D, yer: Option<Yer>) -> Nəticə<()> {
        match d {
            D::Nümunə(n) => {
                if let Some(f) = n.sinif.metod_tap("bağla") {
                    self.funksiya_çağır(&f.bağla(d.clone()), vec![], vec![], yer)?;
                }
                Ok(())
            }
            D::Gen(g) => {
                g.bağla();
                Ok(())
            }
            _ => Ok(()),
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  İfadələr
    // ═══════════════════════════════════════════════════════════════════

    pub fn ifadə(&self, e: &İfadə, m: &Mühit) -> Nəticə {
        match e {
            İfadə::Literal(_, l) => Ok(match l {
                LiteralD::Tam(b) => {
                    use num_traits::ToPrimitive;
                    match b.to_i64() {
                        Some(i) => D::T(i),
                        None => D::BT(Rc::new(b.clone())),
                    }
                }
                LiteralD::Onluq(f) => D::O(*f),
                LiteralD::Mətn(s) | LiteralD::Simvol(s) => D::S(s.clone()),
                LiteralD::Bayt(b) => D::Bayt(b.clone()),
                LiteralD::Məntiq(b) => D::M(*b),
                LiteralD::Boş => D::Boş,
            }),
            İfadə::Ad(_, a) => m.al(a),
            İfadə::İkili(yer, sol, op, sağ) => {
                match op.as_str() {
                    "və" | "&&" => {
                        return Ok(D::M(if self.məntiq(sol, m)? { self.məntiq(sağ, m)? } else { false }))
                    }
                    "və ya" | "||" => {
                        return Ok(D::M(if self.məntiq(sol, m)? { true } else { self.məntiq(sağ, m)? }))
                    }
                    "??" => {
                        let s = self.ifadə(sol, m)?;
                        return if s.boşdur() { self.ifadə(sağ, m) } else { Ok(s) };
                    }
                    _ => {}
                }
                let a = self.ifadə(sol, m)?;
                let b = self.ifadə(sağ, m)?;
                // Sürətli yol: kiçik tamlar
                if let (D::T(x), D::T(y)) = (&a, &b) {
                    let (x, y) = (*x, *y);
                    match op.as_str() {
                        "+" => {
                            if let Some(r) = x.checked_add(y) {
                                return Ok(D::T(r));
                            }
                        }
                        "-" => {
                            if let Some(r) = x.checked_sub(y) {
                                return Ok(D::T(r));
                            }
                        }
                        "*" => {
                            if let Some(r) = x.checked_mul(y) {
                                return Ok(D::T(r));
                            }
                        }
                        "<" => return Ok(D::M(x < y)),
                        ">" => return Ok(D::M(x > y)),
                        "<=" => return Ok(D::M(x <= y)),
                        ">=" => return Ok(D::M(x >= y)),
                        "==" => return Ok(D::M(x == y)),
                        "!=" => return Ok(D::M(x != y)),
                        _ => {}
                    }
                }
                self.ikili_hesabla(op, &a, &b, Some(*yer))
            }
            İfadə::Çağırış(yer, f, arqumentlər) => self.e_çağırış(*yer, f, arqumentlər, m),
            İfadə::Üzv(yer, obyekt, a, təhlükəsiz) => {
                let o = self.ifadə(obyekt, m)?;
                if o.boşdur() {
                    if *təhlükəsiz {
                        return Ok(D::Boş);
                    }
                    return Err(xəta_yer(
                        "BoşDəyərXətası",
                        format!("`boş` dəyərdə `{}` üzvü yoxdur", a),
                        Some(*yer),
                        "ALQ-R004",
                    ));
                }
                self.üzv_al(&o, a, Some(*yer))
            }
            İfadə::İndeks(yer, o, i) => {
                let o = self.ifadə(o, m)?;
                let i = self.ifadə(i, m)?;
                self.indeks_al(&o, &i, Some(*yer))
            }
            İfadə::Şablon(_, parçalar) => {
                let mut s = String::new();
                for p in parçalar {
                    match p {
                        aac::ŞablonHissə::Mətn(t) => s.push_str(t),
                        aac::ŞablonHissə::Kod(e, f) => {
                            let d = self.ifadə(e, m)?;
                            s.push_str(&super::format::formatla(self, &d, f.as_deref())?);
                        }
                    }
                }
                Ok(D::str(s))
            }
            İfadə::Özü(_) => m.al("özü"),
            İfadə::Üst(_) => {
                let özü = m.al("özü")?;
                match m.al("__sinif__")? {
                    D::Sinif(s) => Ok(D::Üst(Rc::new((özü, s)))),
                    _ => Err(xəta("TipXətası", "baza sinif yoxdur", "ALQ-T012")),
                }
            }
            İfadə::Tək(yer, op, e) => self.e_tək(*yer, op, e, m),
            İfadə::Mənimsətmə(yer, hədəflər, op, dəyərlər) => self.e_mənimsətmə(*yer, hədəflər, op, dəyərlər, m),
            İfadə::Çevirmə(yer, e, t, təhlükəsiz) => {
                let d = self.ifadə(e, m)?;
                let h = t.tam_ad();
                match self.çevir(&d, &h, Some(*yer)) {
                    Err(Siqnal::Xəta(_)) if *təhlükəsiz => Ok(D::Boş),
                    r => r,
                }
            }
            İfadə::TipYoxlama(_, e, t) => {
                let d = self.ifadə(e, m)?;
                Ok(D::M(self.tip_uyğundur(&d, t, m)?))
            }
            İfadə::Üzvlük(yer, e, k) => {
                let el = self.ifadə(e, m)?;
                let k = self.ifadə(k, m)?;
                Ok(D::M(self.üzvlük(&el, &k, Some(*yer))?))
            }
            İfadə::BoşYoxlama(_, e, inkar) => {
                let d = self.ifadə(e, m)?;
                Ok(D::M(d.boşdur() != *inkar))
            }
            İfadə::Boru(yer, d, f) => {
                let d = self.ifadə(d, m)?;
                let f = self.ifadə(f, m)?;
                self.çağır(&f, vec![d], vec![], Some(*yer))
            }
            İfadə::Diapazon(yer, b, s, a, xaric) => {
                let b = self.ifadə(b, m)?;
                let s = self.ifadə(s, m)?;
                let a = match a {
                    Some(a) => Some(self.ifadə(a, m)?),
                    None => None,
                };
                for (n, d) in [("başlanğıc", &b), ("son", &s)] {
                    let ok = d.tamdır() || matches!(d, D::S(x) if x.chars().count() == 1);
                    if !ok {
                        return Err(xəta_yer(
                            "TipXətası",
                            format!("diapazonun {} hissəsi tam ədəd olmalıdır, `{}` gəlib", n, tip_adı(d)),
                            Some(*yer),
                            "ALQ-T001",
                        ));
                    }
                }
                let kod = |d: D| match d {
                    D::S(x) => D::T(x.chars().next().unwrap() as i64),
                    d => d,
                };
                yer_qoy(diapazon_yarat(kod(b), kod(s), a, *xaric), Some(*yer))
            }
            İfadə::Dilim(yer, o, b, s, xaric) => self.e_dilim(*yer, o, b.as_ref(), s.as_ref(), *xaric, m),
            İfadə::MəcburiAçma(yer, e) => {
                let d = self.ifadə(e, m)?;
                if d.boşdur() {
                    return Err(xəta_yer(
                        "BoşDəyərXətası",
                        "`!` operatoru `boş` dəyərə tətbiq edildi",
                        Some(*yer),
                        "ALQ-R004",
                    ));
                }
                Ok(d)
            }
            İfadə::Yayma(_, e) => {
                let d = self.ifadə(e, m)?;
                if let D::Nümunə(n) = &d {
                    if &*n.sinif.ad == "Xəta" {
                        return Err(Siqnal::Qaytar(d));
                    }
                }
                Ok(d)
            }
            İfadə::Yeni(yer, t, qurucu, arqumentlər) => {
                let h = self.tip_dəyəri(t, m)?;
                let (a, adlı) = self.arqumentlər(arqumentlər, m, *yer)?;
                match &h {
                    D::Sinif(s) => self.nümunə_yarat(s, qurucu.as_deref(), a, adlı, Some(*yer)),
                    D::Funksiya(_) | D::Daxili(_) | D::Metod(_) | D::XətaSinfi(_) => self.çağır(&h, a, adlı, Some(*yer)),
                    _ => Err(xəta_yer(
                        "TipXətası",
                        format!("`yeni` sinif gözləyir, `{}` gəlib", tip_adı(&h)),
                        Some(*yer),
                        "ALQ-T002",
                    )),
                }
            }
            İfadə::Gözlə(yer, e) => {
                let d = self.ifadə(e, m)?;
                self.gözlə(d, Some(*yer))
            }
            İfadə::Siyahı(yer, el, yaymalar) => {
                let mut n = Vec::with_capacity(el.len());
                for (i, e) in el.iter().enumerate() {
                    let d = self.ifadə(e, m)?;
                    if yaymalar.get(i).copied().unwrap_or(false) {
                        let mut it = self.iterasiya(&d, Some(*yer))?;
                        while let Some(x) = it.növbəti(self, Some(*yer))? {
                            n.push(x);
                        }
                    } else {
                        n.push(d);
                    }
                }
                Ok(D::siyahı(n))
            }
            İfadə::Lüğət(yer, açarlar, dəyərlər) => {
                let mut n = Lüğət::default();
                for (a, d) in açarlar.iter().zip(dəyərlər.iter()) {
                    let d = self.ifadə(d, m)?;
                    match a {
                        None => match &d {
                            D::Lüğət(l) => {
                                for (k, v) in l.borrow().iter() {
                                    n.insert(k.clone(), v.clone());
                                }
                            }
                            _ => {
                                return Err(xəta_yer("TipXətası", "`...` lüğətdə lüğət gözləyir", Some(*yer), "ALQ-T001"))
                            }
                        },
                        Some(a) => {
                            let k = self.ifadə(a, m)?;
                            let k = yer_qoy(Açar::yeni(k), Some(*yer))?;
                            n.insert(k, d);
                        }
                    }
                }
                Ok(D::lüğət(n))
            }
            İfadə::Dəst(yer, el) => {
                let mut n = Dəst::default();
                for e in el {
                    let d = self.ifadə(e, m)?;
                    n.insert(yer_qoy(Açar::yeni(d), Some(*yer))?);
                }
                Ok(D::dəst(n))
            }
            İfadə::Kortej(_, el) => {
                let mut n = Vec::with_capacity(el.len());
                for e in el {
                    n.push(self.ifadə(e, m)?);
                }
                Ok(D::kortej(n))
            }
            İfadə::Qurma { yer, növ, ifadə, dəyər_ifadəsi, bağlama, mənbə, şərt } => {
                let mənbə = self.ifadə(mənbə, m)?;
                let mut siyahı = vec![];
                let mut lüğət = Lüğət::default();
                let mut it = self.iterasiya(&mənbə, Some(*yer))?;
                while let Some(el) = it.növbəti(self, Some(*yer))? {
                    let alt = m.alt();
                    self.bağla(bağlama, el, &alt, true, false)?;
                    if let Some(ş) = şərt {
                        if !self.məntiq(ş, &alt)? {
                            continue;
                        }
                    }
                    if növ == "lüğət" {
                        let k = self.ifadə(ifadə, &alt)?;
                        let k = yer_qoy(Açar::yeni(k), Some(*yer))?;
                        let v = match dəyər_ifadəsi {
                            Some(e) => self.ifadə(e, &alt)?,
                            None => D::Boş,
                        };
                        lüğət.insert(k, v);
                    } else {
                        siyahı.push(self.ifadə(ifadə, &alt)?);
                    }
                }
                match növ.as_str() {
                    "lüğət" => Ok(D::lüğət(lüğət)),
                    "dəst" => {
                        let mut d = Dəst::default();
                        for x in siyahı {
                            d.insert(yer_qoy(Açar::yeni(x), Some(*yer))?);
                        }
                        Ok(D::dəst(d))
                    }
                    "generator" => Ok(D::Gen(Generator::yeni(GenMənbə::Siyahı(siyahı.into_iter())))),
                    _ => Ok(D::siyahı(siyahı)),
                }
            }
            İfadə::ŞərtIfadəsi(_, budaqlar, yoxsa) => {
                for (ş, d) in budaqlar {
                    if self.məntiq(ş, m)? {
                        return self.ifadə(d, m);
                    }
                }
                match yoxsa {
                    Some(y) => self.ifadə(y, m),
                    None => Ok(D::Boş),
                }
            }
            İfadə::Blok(_, gövdə) => match self.blok(gövdə, &m.alt()) {
                Ok(()) => Ok(D::Boş),
                Err(Siqnal::Ver(d)) => Ok(d),
                Err(x) => Err(x),
            },
            İfadə::Lambda { parametrlər, gövdə, asinxron, generator, .. } => Ok(D::Funksiya(Rc::new(Funksiya {
                ad: ad("<lambda>"),
                parametrlər: parametrlər.clone(),
                gövdə: match gövdə {
                    aac::LambdaGövdə::Blok(g) => FGövdə::Blok(g.clone()),
                    aac::LambdaGövdə::İfadə(e) => FGövdə::İfadə(e.clone()),
                },
                mühit: m.clone(),
                asinxron: *asinxron,
                generator: *generator,
                özü: None,
                sinif: None,
                annot: Annot::default(),
                yaddaş: None,
            }))),
            İfadə::JSXElement(yer, a, atributlar, uşaqlar) => self.e_jsx(*yer, a, atributlar, uşaqlar, m),
            İfadə::JSXParça(_, uşaqlar) => {
                let u = self.jsx_uşaqlar(uşaqlar, m)?;
                Ok(D::Element(Rc::new(Element { ad: ad(""), atributlar: D::lüğət(Lüğət::default()), uşaqlar: D::siyahı(u) })))
            }
        }
    }

    fn e_tək(&self, yer: Yer, op: &str, e: &aac::E, m: &Mühit) -> Nəticə {
        if op == "deyil" || op == "!" {
            return Ok(D::M(!self.məntiq(e, m)?));
        }
        let d = self.ifadə(e, m)?;
        match op {
            "-" => {
                if let D::Nümunə(n) = &d {
                    if let Some(f) = n.sinif.metod_tap("əks") {
                        return self.funksiya_çağır(&f.bağla(d.clone()), vec![], vec![], None);
                    }
                }
                match &d {
                    D::T(i) => Ok(match i.checked_neg() {
                        Some(r) => D::T(r),
                        None => D::tam(-num_bigint::BigInt::from(*i)),
                    }),
                    D::BT(b) => Ok(D::tam(-(**b).clone())),
                    D::O(f) => Ok(D::O(-f)),
                    _ => Err(xəta_yer(
                        "TipXətası",
                        format!("`-` `{}` tipinə tətbiq edilmir", tip_adı(&d)),
                        Some(yer),
                        "ALQ-T008",
                    )),
                }
            }
            "+" => Ok(d),
            "~" => match &d {
                D::T(i) => Ok(D::T(!i)),
                D::BT(b) => Ok(D::tam(-(**b).clone() - 1)),
                _ => Err(xəta_yer("TipXətası", "`~` tam ədəd tələb edir", Some(yer), "ALQ-T008")),
            },
            _ => Err(xəta_yer("DaxiliXəta", format!("naməlum tək operator `{}`", op), Some(yer), "")),
        }
    }

    fn e_mənimsətmə(&self, yer: Yer, hədəflər: &[aac::E], op: &str, dəyərlər: &[aac::E], m: &Mühit) -> Nəticə {
        if hədəflər.len() > 1 || dəyərlər.len() > 1 {
            let mut v = vec![];
            for d in dəyərlər {
                v.push(self.ifadə(d, m)?);
            }
            if v.len() == 1 {
                let it = self.iterasiya(&v[0], Some(yer))?;
                v = it.hamısı(self, Some(yer))?;
            }
            if v.len() != hədəflər.len() {
                return Err(xəta_yer("ArqumentXətası", "mənimsətmədə sayllar uyğun gəlmir", Some(yer), "ALQ-T001"));
            }
            for (h, d) in hədəflər.iter().zip(v) {
                self.mənimsət(h, d, m)?;
            }
            return Ok(D::Boş);
        }
        let hədəf = &hədəflər[0];
        let d = if op == "=" {
            self.ifadə(&dəyərlər[0], m)?
        } else if op == "??=" || op == "?=" {
            let cari = match self.ifadə(hədəf, m) {
                Ok(d) => d,
                Err(Siqnal::Xəta(_)) => D::Boş,
                Err(x) => return Err(x),
            };
            if !cari.boşdur() {
                return Ok(cari);
            }
            self.ifadə(&dəyərlər[0], m)?
        } else {
            let cari = self.ifadə(hədəf, m)?;
            let sağ = self.ifadə(&dəyərlər[0], m)?;
            self.ikili_hesabla(&op[..op.len() - 1], &cari, &sağ, Some(yer))?
        };
        self.mənimsət(hədəf, d.clone(), m)?;
        Ok(d)
    }

    pub fn mənimsət(&self, hədəf: &İfadə, d: D, m: &Mühit) -> Nəticə<()> {
        match hədəf {
            İfadə::Ad(_, a) => m.təyin(a, dəyər_kopyası(d)),
            İfadə::Üzv(yer, o, a, _) => {
                let o = self.ifadə(o, m)?;
                self.üzv_qoy(&o, a, d, Some(*yer))
            }
            İfadə::İndeks(yer, o, i) => {
                let o = self.ifadə(o, m)?;
                let i = self.ifadə(i, m)?;
                self.indeks_qoy(&o, i, d, Some(*yer))
            }
            İfadə::Kortej(yer, el) => {
                let v = self.iterasiya(&d, Some(*yer))?.hamısı(self, Some(*yer))?;
                for (h, x) in el.iter().zip(v) {
                    self.mənimsət(h, x, m)?;
                }
                Ok(())
            }
            _ => Err(xəta_yer("ArqumentXətası", "bu ifadəyə mənimsətmə mümkün deyil", Some(hədəf.yer()), "ALQ-T001")),
        }
    }

    // ── İndeks və dilim ───────────────────────────────────────────────

    pub fn indeks_al(&self, o: &D, i: &D, yer: Option<Yer>) -> Nəticə {
        match o {
            D::Siyahı(l) => {
                let j = indeks_tam(i, yer)?;
                let l = l.borrow();
                match indeks_həll(j, l.len()) {
                    Some(k) => Ok(l[k].clone()),
                    None => Err(indeks_xətası(i, l.len(), yer)),
                }
            }
            D::Lüğət(l) => {
                let k = match Açar::yeni(i.clone()) {
                    Ok(k) => k,
                    Err(x) => return Err(x),
                };
                if let Some(v) = l.borrow().get(&k) {
                    return Ok(v.clone());
                }
                Err(xəta_yer("AçarXətası", format!("lüğətdə `{}` açarı yoxdur", mətnə(self, i)?), yer, "ALQ-R003"))
            }
            D::Nümunə(n) => {
                if let Some(f) = n.sinif.metod_tap("al") {
                    return self.funksiya_çağır(&f.bağla(o.clone()), vec![i.clone()], vec![], yer);
                }
                Err(xəta_yer("TipXətası", format!("`{}` indekslənə bilməz", tip_adı(o)), yer, "ALQ-T009"))
            }
            D::S(s) => {
                let j = indeks_tam(i, yer)?;
                if s.is_ascii() {
                    return match indeks_həll(j, s.len()) {
                        Some(k) => Ok(D::s(&s[k..k + 1])),
                        None => Err(indeks_xətası(i, s.len(), yer)),
                    };
                }
                let n = s.chars().count();
                match indeks_həll(j, n) {
                    Some(k) => Ok(D::str(s.chars().nth(k).unwrap().to_string())),
                    None => Err(indeks_xətası(i, n, yer)),
                }
            }
            D::Kortej(k) => {
                let j = indeks_tam(i, yer)?;
                match indeks_həll(j, k.len()) {
                    Some(x) => Ok(k[x].clone()),
                    None => Err(indeks_xətası(i, k.len(), yer)),
                }
            }
            D::Bayt(b) => {
                let j = indeks_tam(i, yer)?;
                match indeks_həll(j, b.len()) {
                    Some(x) => Ok(D::T(b[x] as i64)),
                    None => Err(indeks_xətası(i, b.len(), yer)),
                }
            }
            _ => Err(xəta_yer("TipXətası", format!("`{}` indekslənə bilməz", tip_adı(o)), yer, "ALQ-T009")),
        }
    }

    pub fn indeks_qoy(&self, o: &D, i: D, d: D, yer: Option<Yer>) -> Nəticə<()> {
        match o {
            D::Nümunə(n) if n.sinif.metod_tap("qoy").is_some() => {
                let f = n.sinif.metod_tap("qoy").unwrap();
                self.funksiya_çağır(&f.bağla(o.clone()), vec![i, d], vec![], yer)?;
                Ok(())
            }
            D::Lüğət(l) => {
                let k = Açar::yeni(i)?;
                l.borrow_mut().insert(k, d);
                Ok(())
            }
            D::Siyahı(l) => {
                let n = l.borrow().len();
                let k = match &i {
                    D::T(j) => indeks_həll(*j, n),
                    D::M(b) => indeks_həll(*b as i64, n),
                    _ => None,
                };
                match k {
                    Some(k) => {
                        l.borrow_mut()[k] = d;
                        Ok(())
                    }
                    None => Err(xəta_yer(
                        "İndeksXətası",
                        format!("indeks {} diapazondan kənardır (uzunluq {})", py_str_sadə(&i), n),
                        yer,
                        "ALQ-R002",
                    )),
                }
            }
            D::S(_) => Err(xəta_yer("TipXətası", "`mətn` dəyişməzdir — simvolu dəyişmək olmaz", yer, "ALQ-T021")),
            _ => Err(xəta_yer("TipXətası", format!("`{}` indekslə dəyişdirilə bilməz", tip_adı(o)), yer, "ALQ-T009")),
        }
    }


    fn e_dilim(&self, yer: Yer, o: &aac::E, b: Option<&aac::E>, s: Option<&aac::E>, xaric: bool, m: &Mühit) -> Nəticə {
        let o = self.ifadə(o, m)?;
        let n = match &o {
            D::Siyahı(l) => l.borrow().len(),
            D::S(x) => x.chars().count(),
            D::Kortej(k) => k.len(),
            D::Bayt(x) => x.len(),
            _ => {
                return Err(xəta_yer("TipXətası", format!("`{}` dilimlənə bilməz", tip_adı(&o)), Some(yer), "ALQ-T009"))
            }
        } as i64;
        let son_verilib = s.is_some();
        let bd = match b {
            Some(e) => self.ifadə(e, m)?,
            None => D::T(0),
        };
        let sd = match s {
            Some(e) => self.ifadə(e, m)?,
            None => D::T(n),
        };
        let (Some(mut bi), Some(mut si)) = (bd.i64(), sd.i64()) else {
            return Err(xəta_yer("TipXətası", "dilim hədləri tam ədəd olmalıdır", Some(yer), "ALQ-T009"));
        };
        if bi < 0 {
            bi += n;
        }
        if si < 0 {
            si += n;
        }
        if son_verilib && !xaric {
            si += 1;
        }
        let a = bi.max(0).min(n) as usize;
        let z = si.min(n).max(0) as usize;
        let (a, z) = if a > z { (0, 0) } else { (a, z) };
        Ok(match &o {
            D::Siyahı(l) => D::siyahı(l.borrow()[a..z].to_vec()),
            D::Kortej(k) => D::kortej(k[a..z].to_vec()),
            D::Bayt(x) => D::Bayt(Rc::new(x[a..z].to_vec())),
            D::S(x) => D::str(x.chars().skip(a).take(z - a).collect()),
            _ => D::Boş,
        })
    }
}
