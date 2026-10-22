//! Bayt-kod kompilyatoru və virtual maşın.
//!
//! Funksiya gövdələri ilk çağırışda bayt-koda çevrilir (`kompilyator`) və
//! `masin`-da icra olunur. VM-in dəstəkləmədiyi funksiyalar (generatorlar,
//! `global` və s.) şəffaf şəkildə ağac icraçısında qalır; ayrı-ayrı
//! cümlələr də ağac icraçısına ötürülə bilər. `ALQOR_VM=0` VM-i söndürür,
//! `ALQOR_VM_HESABAT=1` icradan sonra hesabat çap edir.

pub mod emr;
pub mod kompilyator;
pub mod masin;

use crate::icraci::deyerler::{FGövdə, Funksiya, FxMap};
use emr::Kod;
use std::cell::{Cell, RefCell};
use std::rc::Rc;

thread_local! {
    static AKTİV: Cell<Option<bool>> = const { Cell::new(None) };
    static KEŞ: RefCell<FxMap<usize, Option<Rc<Kod>>>> = RefCell::new(FxMap::default());
    static SAY: RefCell<Hesabat> = RefCell::new(Hesabat::default());
    static HESABAT: bool = std::env::var("ALQOR_VM_HESABAT").map(|v| v == "1").unwrap_or(false);
}

#[derive(Default)]
struct Hesabat {
    vm_funksiya: usize,
    ağac_funksiya: usize,
    vm_çağırış: u64,
    ağac_çağırış: u64,
    ağac_adları: Vec<String>,
    generator_çağırış: u64,
    kök_vm: bool,
}

fn hesabat_aktiv() -> bool {
    HESABAT.with(|h| *h)
}

/// VM aktivdirmi (standart: bəli; `ALQOR_VM=0` və ya `--vm yox` söndürür)
pub fn aktiv() -> bool {
    AKTİV.with(|a| match a.get() {
        Some(x) => x,
        None => {
            let x = !matches!(std::env::var("ALQOR_VM").as_deref(), Ok("0") | Ok("yox") | Ok("false"));
            a.set(Some(x));
            x
        }
    })
}

pub fn aktiv_et(x: bool) {
    AKTİV.with(|a| a.set(Some(x)));
}

fn gövdə_açarı(g: &FGövdə) -> usize {
    match g {
        FGövdə::Blok(b) => Rc::as_ptr(b) as usize,
        FGövdə::İfadə(e) => Rc::as_ptr(e) as *const u8 as usize,
    }
}

fn parametrlər_eynidir(a: &[crate::aac::Parametr], b: &[crate::aac::Parametr]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(x, y)| {
            x.ad == y.ad
                && x.variadic == y.variadic
                && x.adlı_variadic == y.adlı_variadic
                && x.yalnız_adlı == y.yalnız_adlı
                && x.xassə_görünüşü == y.xassə_görünüşü
                && format!("{:?}", x.tip) == format!("{:?}", y.tip)
                && match (&x.standart, &y.standart) {
                    (None, None) => true,
                    (Some(p), Some(q)) => Rc::ptr_eq(p, q),
                    _ => false,
                }
        })
}

/// Funksiyanın bayt-kodu (VM-də işləyə bilmirsə `None`).
pub fn kod_tap(f: &Funksiya) -> Option<Rc<Kod>> {
    if !aktiv() {
        return None;
    }
    if f.generator {
        if hesabat_aktiv() {
            SAY.with(|s| s.borrow_mut().generator_çağırış += 1);
        }
        return None;
    }
    let açar = gövdə_açarı(&f.gövdə);
    let k = KEŞ.with(|k| k.borrow().get(&açar).cloned());
    let k = match k {
        Some(k) => k,
        None => {
            let k = kompilyator::kompilyasiya(&kompilyator::Mənbə::Funksiya {
                ad: &f.ad,
                parametrlər: &f.parametrlər,
                gövdə: &f.gövdə,
            })
            .ok()
            .map(Rc::new);
            if let Some(k) = &k {
                kod_çap(k);
            }
            if hesabat_aktiv() {
                SAY.with(|s| {
                    let mut s = s.borrow_mut();
                    if k.is_some() {
                        s.vm_funksiya += 1;
                    } else {
                        s.ağac_funksiya += 1;
                        s.ağac_adları.push(f.ad.to_string());
                    }
                });
            }
            KEŞ.with(|c| c.borrow_mut().insert(açar, k.clone()));
            k
        }
    };
    let k = k.filter(|k| match &k.parametrlər {
        Some(p) => Rc::ptr_eq(p, &f.parametrlər) || parametrlər_eynidir(p, &f.parametrlər),
        None => false,
    });
    if hesabat_aktiv() {
        SAY.with(|s| {
            let mut s = s.borrow_mut();
            if k.is_some() {
                s.vm_çağırış += 1;
            } else {
                s.ağac_çağırış += 1;
            }
        });
    }
    k
}

/// Keşdən tapılan VM çağırışını hesabata əlavə edir
pub fn vm_çağırışı_say() {
    if hesabat_aktiv() {
        SAY.with(|s| s.borrow_mut().vm_çağırış += 1);
    }
}

/// Proqramın yuxarı səviyyəsi üçün bayt-kod
pub fn kök_kodu(gövdə: &[crate::aac::Cümlə]) -> Option<Kod> {
    if !aktiv() {
        return None;
    }
    let k = kompilyator::kompilyasiya(&kompilyator::Mənbə::Kök(gövdə)).ok();
    if let Some(k) = &k {
        kod_çap(k);
    }
    if hesabat_aktiv() {
        SAY.with(|s| s.borrow_mut().kök_vm = k.is_some());
    }
    k
}

/// `ALQOR_VM_HESABAT=1`: VM əhatəsi haqqında hesabat (stderr)
pub fn hesabat_çap() {
    if !hesabat_aktiv() {
        return;
    }
    if !aktiv() {
        eprintln!("[vm] söndürülüb — bütün kod ağac icraçısında");
        return;
    }
    SAY.with(|s| {
        let s = s.borrow();
        eprintln!(
            "[vm] yuxarı səviyyə: {} | funksiyalar: VM {}, ağac {} | çağırışlar: VM {}, ağac {}, generator {}{}",
            if s.kök_vm { "VM" } else { "ağac" },
            s.vm_funksiya,
            s.ağac_funksiya,
            s.vm_çağırış,
            s.ağac_çağırış,
            s.generator_çağırış,
            if s.ağac_adları.is_empty() { String::new() } else { format!(" | ağacda: {}", s.ağac_adları.join(", ")) }
        );
    });
}

/// `ALQOR_VM_KOD=1`: kompilyasiya olunmuş bayt-kodu stderr-ə çap edir
fn kod_çap(k: &Kod) {
    thread_local! {
        static Ç: bool = std::env::var("ALQOR_VM_KOD").map(|v| v == "1").unwrap_or(false);
    }
    if !Ç.with(|c| *c) {
        return;
    }
    eprintln!("── {} ({:?}, {} yuva, adlar {:?})", k.ad, k.növ, k.yuva_sayı, k.yuva_adları);
    for (i, ə) in k.əmrlər.iter().enumerate() {
        eprintln!("{:5} {:?}", i, ə);
    }
    for b in &k.bölgələr {
        eprintln!("  bölgə {:?}", b);
    }
}
