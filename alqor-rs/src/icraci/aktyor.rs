//! Aktyorlar (spes. § 9.12) və kanallar (§ 9.13).
//!
//! Python icraçısı (`korutin.py`, `icraci.py`) ilə eyni semantika: aktyorun
//! xaricdən çağırılan metodu poçta mesaj kimi düşür, tənbəl `Gələcək`
//! qaytarır; mesajlar gəliş sırası ilə — nəticə gözlənəndə, xassə
//! oxunanda və ya proqramın sonunda — emal olunur.

use super::deyerler::*;
use super::elave::{obyekt, veri};
use super::icraci::İcraçı;
use crate::xeta::Yer;
use std::cell::{Cell, RefCell};
use std::collections::VecDeque;
use std::rc::Rc;

// ═══════════════════════════════════════════════════════════════════════
//  Aktyor poçtu
// ═══════════════════════════════════════════════════════════════════════

#[derive(Default)]
pub struct AktyorPoçtu {
    pub poçt: RefCell<VecDeque<Rc<Mesaj>>>,
    /// Aktyor hazırda mesaj emal edirmi (> 0) — onda `özü.metod()` birbaşadır
    pub emal: Cell<usize>,
}

pub struct Mesaj {
    pub metod: Rc<Funksiya>,
    pub arqumentlər: RefCell<Option<(Vec<D>, Adlı)>>,
    pub yer: Option<Yer>,
    pub bitdi: Cell<bool>,
    pub nəticə: RefCell<Option<Nəticə>>,
    pub gözlənildi: Cell<bool>,
}

impl İcraçı {
    /// Mesajı poçta qoyur; nəticə — tənbəl `Gələcək`.
    pub fn aktyora_göndər(&self, n: &Rc<Nümunə>, metod: Rc<Funksiya>, args: Vec<D>, adlı: Adlı, yer: Option<Yer>) -> D {
        let p = n.aktyor.as_ref().expect("aktyor nümunəsi");
        let mesaj = Rc::new(Mesaj {
            metod: metod.clone(),
            arqumentlər: RefCell::new(Some((args, adlı))),
            yer,
            bitdi: Cell::new(false),
            nəticə: RefCell::new(None),
            gözlənildi: Cell::new(false),
        });
        if p.poçt.borrow().is_empty() && !self.aktyorlar.borrow().iter().any(|a| Rc::ptr_eq(a, n)) {
            self.aktyorlar.borrow_mut().push(n.clone());
        }
        p.poçt.borrow_mut().push_back(mesaj.clone());
        let n2 = n.clone();
        let ad_ = format!("{}.{}", n.sinif.ad, metod.ad);
        D::Gələcək(Gələcək::yeni(&ad_, move |i| {
            mesaj.gözlənildi.set(true);
            i.poçtu_boşalt(&n2, Some(&mesaj))?;
            mesaj.nəticə.borrow().clone().unwrap_or(Ok(D::Boş))
        }))
    }

    /// Mesajları gəliş sırası ilə emal edir (`qədər` daxil).
    pub fn poçtu_boşalt(&self, n: &Rc<Nümunə>, qədər: Option<&Rc<Mesaj>>) -> Nəticə<()> {
        let Some(p) = &n.aktyor else { return Ok(()) };
        loop {
            if qədər.is_some_and(|m| m.bitdi.get()) {
                return Ok(());
            }
            let Some(m) = p.poçt.borrow_mut().pop_front() else { return Ok(()) };
            let (args, adlı) = m.arqumentlər.borrow_mut().take().unwrap_or_default();
            p.emal.set(p.emal.get() + 1);
            let mut r = self.funksiya_çağır(&m.metod.bağla(D::Nümunə(n.clone())), args, adlı, m.yer);
            if let Ok(D::Gələcək(g)) = &r {
                r = g.al(self);
            }
            p.emal.set(p.emal.get() - 1);
            m.bitdi.set(true);
            match r {
                Ok(d) => *m.nəticə.borrow_mut() = Some(Ok(d)),
                Err(Siqnal::Xəta(x)) => {
                    *m.nəticə.borrow_mut() = Some(Err(Siqnal::Xəta(x)));
                    self.xətalı_mesajlar.borrow_mut().push(m.clone());
                }
                // `dayan()` və digər axın siqnalları proqramı dayandırır
                Err(s) => return Err(s),
            }
        }
    }

    /// Proqramın sonu: qalan mesajlar emal olunur; heç kimin gözləmədiyi
    /// mesajdakı xəta tutulmamış xəta kimi atılır.
    pub fn aktyorları_boşalt(&self) -> Nəticə<()> {
        loop {
            let n = {
                let mut a = self.aktyorlar.borrow_mut();
                if a.is_empty() {
                    break;
                }
                a.remove(0)
            };
            self.poçtu_boşalt(&n, None)?;
        }
        let xətalılar = self.xətalı_mesajlar.borrow().clone();
        for m in xətalılar {
            if !m.gözlənildi.get() {
                if let Some(Err(x)) = &*m.nəticə.borrow() {
                    return Err(x.clone());
                }
            }
        }
        Ok(())
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Kanal
// ═══════════════════════════════════════════════════════════════════════

#[derive(Default)]
pub struct Kanal {
    pub növbə: RefCell<VecDeque<D>>,
    pub bağlı: Cell<bool>,
}

impl Kanal {
    /// Növbəti dəyər; bağlanıb boşdursa `None`. Boşdur və bağlanmayıbsa —
    /// tək axınlı icraçıda göndərə biləcək kimsə yoxdur: dalan.
    pub fn al(&self) -> Nəticə<Option<D>> {
        if let Some(x) = self.növbə.borrow_mut().pop_front() {
            return Ok(Some(x));
        }
        if self.bağlı.get() {
            return Ok(None);
        }
        Err(xəta("DalanXətası", "kanal boşdur və ona göndərən yoxdur — dalan", "ALQ-R018"))
    }
}

pub fn kanal_yarat() -> D {
    obyekt(
        "Kanal",
        Rc::new(Kanal::default()),
        |k| format!("<kanal {} element{}>", k.növbə.borrow().len(), if k.bağlı.get() { ", bağlı" } else { "" }),
        |_, k| {
            let k1 = k.clone();
            let k2 = k.clone();
            let k3 = k.clone();
            let k4 = k.clone();
            let k5 = k.clone();
            let k6 = k.clone();
            let k7 = k.clone();
            vec![
                (
                    "göndər",
                    daxili("göndər", 1, Some(1), move |_, a, _| {
                        if k1.bağlı.get() {
                            return Err(xəta("KanalXətası", "bağlanmış kanala göndərmək olmaz", "ALQ-R019"));
                        }
                        k1.növbə.borrow_mut().push_back(a[0].clone());
                        Ok(D::Boş)
                    }),
                ),
                ("al", daxili("al", 0, Some(0), move |_, _, _| Ok(k2.al()?.unwrap_or(D::Boş)))),
                ("cəhdAl", daxili("cəhdAl", 0, Some(0), move |_, _, _| Ok(k3.növbə.borrow_mut().pop_front().unwrap_or(D::Boş)))),
                (
                    "bağla",
                    daxili("bağla", 0, Some(0), move |_, _, _| {
                        k4.bağlı.set(true);
                        Ok(D::Boş)
                    }),
                ),
                ("bağlıdır", daxili("bağlıdır", 0, Some(0), move |_, _, _| Ok(D::M(k5.bağlı.get())))),
                ("boşdur", daxili("boşdur", 0, Some(0), move |_, _, _| Ok(D::M(k6.növbə.borrow().is_empty())))),
                ("uzunluq", daxili("uzunluq", 0, Some(0), move |_, _, _| Ok(D::T(k7.növbə.borrow().len() as i64)))),
            ]
        },
    )
}

/// `uzunluq(k)` və dövr üçün
pub fn kanal(d: &D) -> Option<Rc<Kanal>> {
    veri::<Kanal>(d)
}
