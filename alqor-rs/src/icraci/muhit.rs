//! Mühit (əhatə dairəsi) — adların dəyərlərə bağlanması.

use super::deyerler::{xəta, Ad, FxMap, Nəticə, D};
use std::cell::RefCell;
use std::rc::Rc;

pub struct Giriş {
    pub ad: Ad,
    pub d: D,
    pub sabit: bool,
}

pub struct MühitD {
    pub adlar: RefCell<Vec<Giriş>>,
    indeks: RefCell<Option<FxMap<Ad, usize>>>,
    pub qloballar: RefCell<Vec<Ad>>,
    pub üst: Option<Mühit>,
}

pub type Mühit = Rc<MühitD>;

const İNDEKS_HƏDDİ: usize = 12;

#[inline]
fn eyni_ad(a: &Ad, b: &str) -> bool {
    a.len() == b.len() && (std::ptr::eq(a.as_ptr(), b.as_ptr()) || **a == *b)
}

impl MühitD {
    pub fn yeni(üst: Option<Mühit>) -> Mühit {
        Rc::new(MühitD {
            adlar: RefCell::new(Vec::new()),
            indeks: RefCell::new(None),
            qloballar: RefCell::new(Vec::new()),
            üst,
        })
    }

    #[inline]
    fn tap(&self, ad: &str) -> Option<usize> {
        if let Some(ix) = &*self.indeks.borrow() {
            return ix.get(ad).copied();
        }
        let a = self.adlar.borrow();
        a.iter().position(|g| eyni_ad(&g.ad, ad))
    }

    pub fn burada_al(&self, ad: &str) -> Option<D> {
        self.tap(ad).map(|i| self.adlar.borrow()[i].d.clone())
    }

    pub fn al(&self, ad: &str) -> Nəticə {
        let mut m = self;
        loop {
            if let Some(i) = m.tap(ad) {
                return Ok(m.adlar.borrow()[i].d.clone());
            }
            match &m.üst {
                Some(ü) => m = ü,
                None => {
                    return Err(xəta("ArqumentXətası", format!("`{}` təyin edilməyib", ad), "ALQ-T022"))
                }
            }
        }
    }

    pub fn var(&self, ad: &str) -> bool {
        let mut m = self;
        loop {
            if m.tap(ad).is_some() {
                return true;
            }
            match &m.üst {
                Some(ü) => m = ü,
                None => return false,
            }
        }
    }

    /// Yeni ad yaradır (cari əhatədə).
    pub fn elan(&self, ad: Ad, d: D, sabit: bool) {
        if let Some(i) = self.tap(&ad) {
            let mut a = self.adlar.borrow_mut();
            a[i].d = d;
            if sabit {
                a[i].sabit = true;
            }
            return;
        }
        let mut a = self.adlar.borrow_mut();
        a.push(Giriş { ad: ad.clone(), d, sabit });
        let n = a.len();
        let mut ix = self.indeks.borrow_mut();
        match &mut *ix {
            Some(m) => {
                m.insert(ad, n - 1);
            }
            None if n > İNDEKS_HƏDDİ => {
                *ix = Some(a.iter().enumerate().map(|(i, g)| (g.ad.clone(), i)).collect());
            }
            None => {}
        }
    }

    /// Mövcud ada yeni dəyər verir — yuxarı əhatələrdə axtarır.
    pub fn təyin(&self, ad: &str, d: D) -> Nəticə<()> {
        if !self.qloballar.borrow().is_empty() && self.qloballar.borrow().iter().any(|g| eyni_ad(g, ad)) {
            let mut kök = self;
            while let Some(ü) = &kök.üst {
                kök = ü;
            }
            if let Some(i) = kök.tap(ad) {
                if kök.adlar.borrow()[i].sabit {
                    return Err(sabit_xətası(ad));
                }
                kök.adlar.borrow_mut()[i].d = d;
            } else {
                kök.elan(super::deyerler::ad(ad), d, false);
            }
            return Ok(());
        }
        let mut m = self;
        loop {
            if let Some(i) = m.tap(ad) {
                let mut a = m.adlar.borrow_mut();
                if a[i].sabit {
                    return Err(sabit_xətası(ad));
                }
                a[i].d = d;
                return Ok(());
            }
            match &m.üst {
                Some(ü) => m = ü,
                None => {
                    return Err(xəta("ArqumentXətası", format!("`{}` təyin edilməyib", ad), "ALQ-T022"))
                }
            }
        }
    }

    pub fn alt(self: &Mühit) -> Mühit {
        MühitD::yeni(Some(self.clone()))
    }

    pub fn hamısı(&self) -> Vec<(Ad, D)> {
        self.adlar.borrow().iter().map(|g| (g.ad.clone(), g.d.clone())).collect()
    }
}

fn sabit_xətası(ad: &str) -> super::deyerler::Siqnal {
    xəta("ArqumentXətası", format!("`{}` sabitdir, dəyişdirilə bilməz", ad), "ALQ-T020")
}
