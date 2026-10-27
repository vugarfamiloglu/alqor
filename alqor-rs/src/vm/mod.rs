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
                generator: false,
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

/// Generator gövdəsi üçün bayt-kod (korutində icra olunur)
#[cfg(not(target_arch = "wasm32"))]
pub fn generator_kodu(f: &Funksiya) -> Option<Rc<Kod>> {
    if !aktiv() {
        return None;
    }
    let açar = gövdə_açarı(&f.gövdə) | 1;
    let k = KEŞ.with(|k| k.borrow().get(&açar).cloned());
    let k = match k {
        Some(k) => k,
        None => {
            let k = kompilyator::kompilyasiya(&kompilyator::Mənbə::Funksiya {
                ad: &f.ad,
                parametrlər: &f.parametrlər,
                gövdə: &f.gövdə,
                generator: true,
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
    k.filter(|k| match &k.parametrlər {
        Some(p) => Rc::ptr_eq(p, &f.parametrlər) || parametrlər_eynidir(p, &f.parametrlər),
        None => false,
    })
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

#[cfg(test)]
mod sinaq {
    use super::*;

    /// Eyni mənbəni ağac icraçısı və VM ilə icra edir; nəticələr eyni olmalıdır.
    fn müqayisə(mənbə: &str) -> String {
        let işlət = |vm: bool| {
            aktiv_et(vm);
            let n = crate::işlət_mətn("sınaq.alq", mənbə, &[], vec![]);
            (n.stdout, n.stderr, n.kod)
        };
        let ağac = işlət(false);
        let vm = işlət(true);
        assert_eq!(ağac, vm, "ağac icraçısı ilə VM fərqlidir:\n{mənbə}");
        vm.0
    }

    /// Kodun VM-də kompilyasiya olunduğunu yoxlayır
    fn kompilyasiya_olunur(mənbə: &str) {
        let m = crate::xeta::Mənbə::yeni("k.alq", mənbə, None);
        let mut x = crate::xeta::XətaToplayıcı::yeni();
        let p = crate::parser::ayır(m, &mut x);
        assert!(x.uğurludur());
        assert!(kompilyator::kompilyasiya(&kompilyator::Mənbə::Kök(&p.gövdə)).is_ok());
    }

    #[test]
    fn hesab_və_rekursiya() {
        let ç = müqayisə("funksiya fib(n)\n    əgər n < 2 onda qaytar n son\n    qaytar fib(n - 1) + fib(n - 2)\nson\nyaz(fib(15), 7 / 2, 7 ~/ 2, -7 % 3, 2 ** 70, 1.5 * 2)\n");
        assert_eq!(ç, "610 3.5 3 -1 1180591620717411303424 3.0\n");
    }

    #[test]
    fn dövr_dəyişənini_tutan_bağlamalar() {
        let ç = müqayisə("dəyişən fs = []\nhər i üçün 0..<3 içində\n    dəyişən k = i * 10\n    fs.əlavə(() => i + k)\nson\nyaz(fs.çevir((f) => f()))\n");
        assert_eq!(ç, "[0, 11, 22]\n");
    }

    #[test]
    fn etiketli_dayan_davam_və_yoxsa() {
        let ç = müqayisə(
            "funksiya f()\n    dəyişən n = []\n    xarici: hər i üçün 1..3 içində\n        hər j üçün 1..3 içində\n            əgər j == 2 onda davam xarici son\n            əgər i == 3 onda dayan xarici son\n            n.əlavə(\"{i}{j}\")\n        son\n    son\n    hər x üçün [1] içində\n    yoxsa\n        n.əlavə(\"y\")\n    son\n    qaytar n\nson\nyaz(f())\n",
        );
        assert_eq!(ç, "[\"11\", \"21\", \"y\"]\n");
    }

    #[test]
    fn xətalar_və_nəhayət() {
        let ç = müqayisə(
            "funksiya f(x)\n    cəhd et\n        əgər x == 1 onda qaytar \"bir\" son\n        at Xəta(\"x\")\n    tut e\n        qaytar \"tut {e.mesaj}\"\n    nəhayət\n        yaz(\"n{x}\")\n    son\nson\nyaz(f(1), f(2))\n",
        );
        assert_eq!(ç, "n1\nn2\nbir tut x\n");
    }

    #[test]
    fn stek_həddi_xətası() {
        // 1000 çağırış dərinliyi üçün böyük stek (CLI kimi)
        std::thread::Builder::new()
            .stack_size(256 << 20)
            .spawn(|| {
                aktiv_et(true);
                let n = crate::işlət_mətn("s.alq", "funksiya d(n) qaytar d(n + 1) son\nd(0)\n", &[], vec![]);
                assert_eq!(n.kod, 1);
                assert!(n.stderr.contains("ALQ-R010"), "{}", n.stderr);
                müqayisə("funksiya d(n) qaytar d(n + 1) son\nd(0)\n");
            })
            .unwrap()
            .join()
            .unwrap();
    }

    #[test]
    fn arqumentlər() {
        let ç = müqayisə(
            "funksiya f(a, b = a * 2, *, c = 7) qaytar \"{a} {b} {c}\" son\nfunksiya v(a, ...q) qaytar \"{a} {q}\" son\nfunksiya k(x, **d) qaytar \"{x} {d}\" son\nyaz(f(1), f(1, 2, c: 3), v(1, 2, 3), k(1, p: 2))\nf()\n",
        );
        assert!(ç.starts_with("1 2 7 1 2 3 1 [2, 3] 1 {\"p\": 2}\n"));
    }

    #[test]
    fn siniflər_və_generatorlar() {
        müqayisə(
            "sinif A\n    xassə x: tam = 1\n    metod al() qaytar özü.x son\nson\nsinif B miras A\n    metod al() qaytar üst.al() + 1 son\nson\nyaz(B().al())\ngenerator funksiya g(n)\n    hər i üçün 0..<n içində\n        ver i * i\n    son\nson\nyaz(g(4).siyahıyaÇevir())\n",
        );
    }

    #[test]
    fn adi_kod_vmdə_kompilyasiya_olunur() {
        kompilyasiya_olunur("dəyişən x = 1\nhər i üçün 0..3 içində\n    x += i\nson\nseç x\n    hal 7 → yaz(x)\nson\n");
    }
}
