//! Bayt-kod maşını (interpretator dövrü).

use super::emr::*;
use crate::icraci::cagiris::*;
use crate::icraci::deyerler::*;
use crate::icraci::icraci::{dilim_tətbiq, dilim_uzunluğu, İcraçı, İter};
use crate::icraci::muhit::{sabit_xətası, Mühit};
use crate::xeta::Yer;
use std::cell::RefCell;
use std::rc::Rc;

struct VmIter {
    it: İter,
    lüğət: Option<Rc<RefCell<Lüğət>>>,
    indeks: i64,
}

/// Bir çağırışın çərçivəsi
struct Çərçivə<'f> {
    yuvalar: Vec<Option<D>>,
    sabitlər: Vec<bool>,
    yığın: Vec<D>,
    baza: Mühit,
    mühitlər: Vec<Mühit>,
    iterlər: Vec<VmIter>,
    arqlar: Vec<(Vec<D>, Adlı)>,
    cəhdlər: Vec<Option<Siqnal>>,
    // parametrlər
    f: Option<&'f Rc<Funksiya>>,
    args: std::vec::IntoIter<D>,
    adlı: Adlı,
    çağırış_yeri: Option<Yer>,
}

impl<'f> Çərçivə<'f> {
    fn yeni(kod: &Kod, baza: Mühit) -> Self {
        Çərçivə {
            yuvalar: vec![None; kod.yuva_sayı],
            sabitlər: if kod.sabit_var { vec![false; kod.yuva_sayı] } else { vec![] },
            yığın: Vec::with_capacity(16),
            baza,
            mühitlər: vec![],
            iterlər: vec![],
            arqlar: vec![],
            cəhdlər: (0..kod.cəhd_sayı).map(|_| None).collect(),
            f: None,
            args: Vec::new().into_iter(),
            adlı: vec![],
            çağırış_yeri: None,
        }
    }

    #[inline(always)]
    fn m(&self) -> &Mühit {
        self.mühitlər.last().unwrap_or(&self.baza)
    }

    #[inline(always)]
    fn pop(&mut self) -> D {
        match self.yığın.pop() {
            Some(d) => d,
            None => D::Boş,
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Giriş nöqtələri
// ═══════════════════════════════════════════════════════════════════════

/// Funksiya gövdəsini VM-də icra edir (`funksiya_gövdəsi`-nin əvəzi).
pub fn gövdə_işlət(i: &İcraçı, f: &Rc<Funksiya>, kod: &Kod, args: Vec<D>, adlı: Adlı, yer: Option<Yer>) -> Nəticə {
    let mut ç = Çərçivə::yeni(kod, f.mühit.clone());
    if kod.funksiya_mühiti {
        let n = f.parametrlər.len() + if f.özü.is_some() { 2 } else { 0 };
        ç.mühitlər.push(f.mühit.alt_tutumla(n));
    }
    // özü və __sinif__
    let sinif = match &f.özü {
        Some(özü) => {
            elan_ad_və_ya_yuva(&mut ç, kod.özü_yuvası, "özü", özü.clone());
            f.sinif.clone().or_else(|| match özü {
                D::Nümunə(n) => Some(n.sinif.clone()),
                _ => None,
            })
        }
        None => f.sinif.clone(),
    };
    if let Some(s) = sinif {
        elan_ad_və_ya_yuva(&mut ç, kod.sinif_yuvası, "__sinif__", D::Sinif(s));
    }
    if args.len() > kod.mövqeli_say && !kod.variadic_var {
        return Err(xəta_yer(
            "ArqumentXətası",
            format!("`{}` ən çox {} mövqeli arqument qəbul edir, {} verilib", f.ad, kod.mövqeli_say, args.len()),
            yer,
            "ALQ-T003",
        ));
    }
    ç.f = Some(f);
    ç.args = args.into_iter();
    ç.adlı = adlı;
    ç.çağırış_yeri = yer;
    if !kod.gecikdir_var {
        return icra(i, kod, &mut ç);
    }
    i.gecikdirilmiş.borrow_mut().push(vec![]);
    let r = icra(i, kod, &mut ç);
    let gecikmiş = i.gecikdirilmiş.borrow_mut().pop().unwrap_or_default();
    for (e, mm) in gecikmiş.iter().rev() {
        match i.ifadə(e, mm) {
            Ok(_) | Err(Siqnal::Xəta(_)) => {}
            Err(x) => return Err(x),
        }
    }
    r
}

/// Proqramın yuxarı səviyyəsi (qlobal əhatədə)
pub fn kök_işlət(i: &İcraçı, kod: &Kod) -> Nəticə<()> {
    let mut ç = Çərçivə::yeni(kod, i.qlobal.clone());
    icra(i, kod, &mut ç).map(|_| ())
}

fn elan_ad_və_ya_yuva(ç: &mut Çərçivə, yuva: Option<u32>, a: &str, d: D) {
    match yuva {
        Some(y) => ç.yuvalar[y as usize] = Some(d),
        None => ç.m().elan(ad(a), d, false),
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Köməkçilər
// ═══════════════════════════════════════════════════════════════════════

#[inline]
fn eyni_ad(a: &Ad, b: &Ad) -> bool {
    Rc::ptr_eq(a, b) || **a == **b
}

/// Təyin olunmamış yuvanın oxunması: xarici eyniadlı yuva və ya Mühit
fn yuva_boş_al(kod: &Kod, ç: &Çərçivə, y: u32) -> Nəticə {
    let mut cari = kod.yuva_üst[y as usize];
    while let Some(u) = cari {
        if let Some(d) = &ç.yuvalar[u as usize] {
            return Ok(d.clone());
        }
        cari = kod.yuva_üst[u as usize];
    }
    ç.m().al(&kod.yuva_adları[y as usize])
}

fn yuva_yaz(kod: &Kod, ç: &mut Çərçivə, y: u32, d: D) -> Nəticə<()> {
    let mut cari = Some(y);
    while let Some(u) = cari {
        if ç.yuvalar[u as usize].is_some() {
            if !ç.sabitlər.is_empty() && ç.sabitlər[u as usize] {
                return Err(sabit_xətası(&kod.yuva_adları[u as usize]));
            }
            ç.yuvalar[u as usize] = Some(d);
            return Ok(());
        }
        cari = kod.yuva_üst[u as usize];
    }
    ç.m().təyin(&kod.yuva_adları[y as usize], d)
}

fn ad_al(kod: &Kod, m: &Mühit, a: &Ad, k: u32) -> Nəticə {
    if m.üst.is_none() {
        let keş = &kod.keşlər[k as usize];
        let (p, idx) = keş.get();
        if p == Rc::as_ptr(m) as usize {
            let adlar = m.adlar.borrow();
            if let Some(g) = adlar.get(idx as usize) {
                if eyni_ad(&g.ad, a) {
                    return Ok(g.d.clone());
                }
            }
        }
        let d = m.al(a)?;
        if let Some(idx) = m.indeks(a) {
            keş.set((Rc::as_ptr(m) as usize, idx as u32));
        }
        return Ok(d);
    }
    m.al(a)
}

fn ad_qoy(kod: &Kod, m: &Mühit, a: &Ad, k: u32, d: D) -> Nəticə<()> {
    if m.üst.is_none() {
        let keş = &kod.keşlər[k as usize];
        let (p, idx) = keş.get();
        if p == Rc::as_ptr(m) as usize {
            let mut adlar = m.adlar.borrow_mut();
            if let Some(g) = adlar.get_mut(idx as usize) {
                if eyni_ad(&g.ad, a) {
                    if g.sabit {
                        return Err(sabit_xətası(a));
                    }
                    g.d = d;
                    return Ok(());
                }
            }
        }
        m.təyin(a, d)?;
        if let Some(idx) = m.indeks(a) {
            keş.set((Rc::as_ptr(m) as usize, idx as u32));
        }
        return Ok(());
    }
    m.təyin(a, d)
}

fn məntiq_xətası(d: &D, yer: Yer) -> Siqnal {
    xəta_yer(
        "TipXətası",
        format!("şərt `məntiq` tipi olmalıdır, `{}` gəlib", tip_adı(d)),
        Some(yer),
        "ALQ-T007",
    )
}

/// Siqnalı bölgələr cədvəli ilə emal edir: yeni `pc` və ya funksiyadan çıxış.
fn siqnal_emal(kod: &Kod, ç: &mut Çərçivə, s: Siqnal, pc: u32) -> Result<u32, Siqnal> {
    for b in &kod.bölgələr {
        if pc < b.başla || pc >= b.son {
            continue;
        }
        let hədəf = match &b.növ {
            BölgəNöv::Dövr(et, dayan, davam) => {
                let uyğun = |e: &Option<Ad>| match e {
                    None => true,
                    Some(e) => et.as_deref() == Some(&**e),
                };
                match &s {
                    Siqnal::Dayan(e) if uyğun(e) => *dayan,
                    Siqnal::Davam(e) if uyğun(e) => *davam,
                    _ => continue,
                }
            }
            BölgəNöv::Cəhd(id, tutma, fin, nəh) => {
                let h = if matches!(s, Siqnal::Xəta(_)) {
                    *tutma
                } else if *nəh {
                    *fin
                } else {
                    continue;
                };
                ç.yığın.clear();
                ç.arqlar.clear();
                ç.mühitlər.truncate(b.mühit as usize);
                ç.iterlər.truncate(b.iter as usize);
                ç.cəhdlər[*id as usize] = Some(s);
                return Ok(h);
            }
            BölgəNöv::Tutma(id, fin) => {
                ç.yığın.clear();
                ç.arqlar.clear();
                ç.mühitlər.truncate(b.mühit as usize);
                ç.iterlər.truncate(b.iter as usize);
                ç.cəhdlər[*id as usize] = Some(s);
                return Ok(*fin);
            }
            BölgəNöv::XətaBoş(h) => {
                if !matches!(s, Siqnal::Xəta(_)) {
                    continue;
                }
                ç.yığın.clear();
                ç.arqlar.clear();
                ç.mühitlər.truncate(b.mühit as usize);
                ç.iterlər.truncate(b.iter as usize);
                ç.yığın.push(D::Boş);
                return Ok(*h);
            }
        };
        ç.yığın.clear();
        ç.arqlar.clear();
        ç.mühitlər.truncate(b.mühit as usize);
        ç.iterlər.truncate(b.iter as usize);
        return Ok(hədəf);
    }
    Err(s)
}

fn funksiya_yarat(kod: &Kod, ç: &Çərçivə, idx: u32) -> D {
    let a = &kod.alt_funksiyalar[idx as usize];
    let annot = Annot { yaddaşla: a.yaddaşla, tənbəl: false, statik: false };
    D::Funksiya(Rc::new(Funksiya {
        ad: a.ad.clone(),
        parametrlər: a.parametrlər.clone(),
        gövdə: a.gövdə.clone(),
        mühit: ç.m().clone(),
        asinxron: a.asinxron,
        generator: a.generator,
        özü: None,
        sinif: None,
        annot,
        yaddaş: if a.yaddaşla { Some(Default::default()) } else { None },
    }))
}

// ═══════════════════════════════════════════════════════════════════════
//  İcra dövrü
// ═══════════════════════════════════════════════════════════════════════

macro_rules! t {
    ($e:expr, $l:lifetime) => {
        match $e {
            Ok(v) => v,
            Err(s) => break $l s,
        }
    };
}

fn icra(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə) -> Nəticə {
    let əmrlər = &kod.əmrlər[..];
    let mut pc: usize = 0;
    loop {
        let cari = pc;
        let s: Siqnal = 'x: {
            loop {
                let ə = unsafe { əmrlər.get_unchecked(pc) };
                pc += 1;
                match ə {
                    Əmr::Sabit(k) => ç.yığın.push(kod.sabitlər[*k as usize].clone()),
                    Əmr::Tam(n) => ç.yığın.push(D::T(*n)),
                    Əmr::Boş => ç.yığın.push(D::Boş),
                    Əmr::Məntiq(b) => ç.yığın.push(D::M(*b)),
                    Əmr::At => {
                        ç.yığın.pop();
                    }
                    Əmr::Dup => {
                        let d = ç.yığın.last().cloned().unwrap_or(D::Boş);
                        ç.yığın.push(d);
                    }
                    Əmr::YuvaAl(y) => {
                        let d = match &ç.yuvalar[*y as usize] {
                            Some(d) => d.clone(),
                            None => t!(yuva_boş_al(kod, ç, *y), 'x),
                        };
                        ç.yığın.push(d);
                    }
                    Əmr::YuvaQoy(y) => {
                        let d = ç.pop();
                        let yi = *y as usize;
                        if ç.yuvalar[yi].is_some() && (ç.sabitlər.is_empty() || !ç.sabitlər[yi]) {
                            ç.yuvalar[yi] = Some(d);
                        } else {
                            t!(yuva_yaz(kod, ç, *y, d), 'x);
                        }
                    }
                    Əmr::YuvaElan(y) => {
                        let d = ç.pop();
                        ç.yuvalar[*y as usize] = Some(d);
                    }
                    Əmr::YuvaElanSabit(y) => {
                        let d = ç.pop();
                        ç.yuvalar[*y as usize] = Some(d);
                        ç.sabitlər[*y as usize] = true;
                    }
                    Əmr::AdAl(a, k) => {
                        let d = t!(ad_al(kod, ç.m(), &kod.adlar[*a as usize], *k), 'x);
                        ç.yığın.push(d);
                    }
                    Əmr::AdQoy(a, k) => {
                        let d = ç.pop();
                        t!(ad_qoy(kod, ç.m(), &kod.adlar[*a as usize], *k, d), 'x);
                    }
                    Əmr::AdElan(a) => {
                        let d = ç.pop();
                        ç.m().elan(kod.adlar[*a as usize].clone(), d, false);
                    }
                    Əmr::AdElanSabit(a) => {
                        let d = ç.pop();
                        ç.m().elan(kod.adlar[*a as usize].clone(), d, true);
                    }
                    Əmr::MühitAç => {
                        let m = ç.m().alt();
                        ç.mühitlər.push(m);
                    }
                    Əmr::MühitBağla => {
                        ç.mühitlər.pop();
                    }
                    Əmr::Kopya => {
                        if let Some(D::Nümunə(n)) = ç.yığın.last() {
                            if n.sinif.quruluş == "struktur" {
                                let d = ç.pop();
                                ç.yığın.push(dəyər_kopyası(d));
                            }
                        }
                    }
                    Əmr::Genişlət => {
                        let d = ç.pop();
                        let d = match &d {
                            D::T(_) | D::BT(_) => D::O(d.onluq().unwrap()),
                            _ => d,
                        };
                        ç.yığın.push(d);
                    }
                    Əmr::İkili(op) => {
                        let b = ç.pop();
                        let a = ç.pop();
                        if let (D::T(x), D::T(y)) = (&a, &b) {
                            let (x, y) = (*x, *y);
                            let r = match op {
                                Op::Topla => x.checked_add(y).map(D::T),
                                Op::Çıx => x.checked_sub(y).map(D::T),
                                Op::Vur => x.checked_mul(y).map(D::T),
                                Op::Kiçik => Some(D::M(x < y)),
                                Op::Böyük => Some(D::M(x > y)),
                                Op::KiçikBərabər => Some(D::M(x <= y)),
                                Op::BöyükBərabər => Some(D::M(x >= y)),
                                Op::Bərabər => Some(D::M(x == y)),
                                Op::Fərqli => Some(D::M(x != y)),
                                Op::Qalıq if y != 0 && x.abs() < (1 << 53) && y.abs() < (1 << 53) => Some(D::T(x % y)),
                                Op::TamBöl if y != 0 => x.checked_div(y).map(D::T),
                                Op::Böl if y != 0 && x.abs() < (1 << 53) && y.abs() < (1 << 53) => {
                                    Some(D::O(x as f64 / y as f64))
                                }
                                _ => None,
                            };
                            if let Some(r) = r {
                                ç.yığın.push(r);
                                continue;
                            }
                        } else if let (D::O(x), D::O(y)) = (&a, &b) {
                            let (x, y) = (*x, *y);
                            let r = match op {
                                Op::Topla => Some(D::O(x + y)),
                                Op::Çıx => Some(D::O(x - y)),
                                Op::Vur => Some(D::O(x * y)),
                                Op::Böl if y != 0.0 => Some(D::O(x / y)),
                                Op::Kiçik => Some(D::M(x < y)),
                                Op::Böyük => Some(D::M(x > y)),
                                Op::KiçikBərabər => Some(D::M(x <= y)),
                                Op::BöyükBərabər => Some(D::M(x >= y)),
                                _ => None,
                            };
                            if let Some(r) = r {
                                ç.yığın.push(r);
                                continue;
                            }
                        }
                        let o = match op {
                            Op::Digər(k) => &*kod.adlar[*k as usize],
                            o => o.mətn(),
                        };
                        let r = t!(i.ikili_hesabla(o, &a, &b, Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::Tək(k) => {
                        let d = ç.pop();
                        let op = match k {
                            0 => "-",
                            1 => "+",
                            _ => "~",
                        };
                        let r = t!(i.tək_dəyər(kod.yerlər[pc - 1], op, d), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::MəntiqYoxla => {
                        if !matches!(ç.yığın.last(), Some(D::M(_))) {
                            let d = ç.pop();
                            break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]);
                        }
                    }
                    Əmr::Deyil => {
                        if let Some(D::M(b)) = ç.yığın.last_mut() {
                            *b = !*b;
                        }
                    }
                    Əmr::Atla(h) => pc = *h as usize,
                    Əmr::YanlışsaAtla(h) => {
                        if let Some(D::M(false)) = ç.yığın.pop() {
                            pc = *h as usize;
                        }
                    }
                    Əmr::ŞərtAtla(h) => match ç.pop() {
                        D::M(true) => {}
                        D::M(false) => pc = *h as usize,
                        d => break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]),
                    },
                    Əmr::BoşDeyilsəAtla(h) => {
                        if matches!(ç.yığın.last(), Some(D::Boş) | None) {
                            ç.yığın.pop();
                        } else {
                            pc = *h as usize;
                        }
                    }
                    Əmr::BoşsaAtla(h) => {
                        if matches!(ç.yığın.last(), Some(D::Boş) | None) {
                            pc = *h as usize;
                        } else {
                            ç.yığın.pop();
                        }
                    }
                    Əmr::Qaç(h, m, it) => {
                        ç.mühitlər.truncate(*m as usize);
                        ç.iterlər.truncate(*it as usize);
                        ç.yığın.clear();
                        pc = *h as usize;
                    }
                    Əmr::SiqnalDayan(e) => break 'x Siqnal::Dayan(e.map(|k| kod.adlar[k as usize].clone())),
                    Əmr::SiqnalDavam(e) => break 'x Siqnal::Davam(e.map(|k| kod.adlar[k as usize].clone())),
                    Əmr::SiqnalQaytar => {
                        let d = ç.pop();
                        break 'x Siqnal::Qaytar(d);
                    }
                    Əmr::Qaytar => return Ok(ç.pop()),
                    // ── Çağırışlar ──────────────────────────────────────
                    Əmr::Çağır(n) => {
                        let k = ç.yığın.len() - *n as usize;
                        let args = ç.yığın.split_off(k);
                        let f = ç.pop();
                        let r = t!(i.çağır(&f, args, vec![], Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::ArqYeni => ç.arqlar.push((vec![], vec![])),
                    Əmr::ArqMövqe => {
                        let d = ç.pop();
                        ç.arqlar.last_mut().unwrap().0.push(d);
                    }
                    Əmr::ArqAdlı(a) => {
                        let d = ç.pop();
                        adlı_qoy(&mut ç.arqlar.last_mut().unwrap().1, kod.adlar[*a as usize].clone(), d);
                    }
                    Əmr::ArqYay => {
                        let d = ç.pop();
                        let yer = Some(kod.yerlər[pc - 1]);
                        let mut it = t!(i.iterasiya(&d, yer), 'x);
                        while let Some(e) = t!(it.növbəti(i, yer), 'x) {
                            ç.arqlar.last_mut().unwrap().0.push(e);
                        }
                    }
                    Əmr::ÇağırArq => {
                        let (args, adlı) = ç.arqlar.pop().unwrap();
                        let f = ç.pop();
                        let r = t!(i.çağır(&f, args, adlı, Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::MetodAl(a, təhlükəsiz, h) => {
                        let o = ç.pop();
                        let a = &kod.adlar[*a as usize];
                        if o.boşdur() {
                            if *təhlükəsiz {
                                ç.yığın.push(D::Boş);
                                pc = *h as usize;
                                continue;
                            }
                            break 'x xəta_yer(
                                "BoşDəyərXətası",
                                format!("`boş` dəyərdə `{}` üzvü yoxdur", a),
                                Some(kod.yerlər[pc - 1]),
                                "ALQ-R004",
                            );
                        }
                        if crate::icraci::metodlar::sürətli_tipdir(&o) && !i.genişlətmə_var(&o, a) && crate::icraci::metodlar::metod_var(&o, a) {
                            ç.yığın.push(o);
                            ç.yığın.push(D::T(1));
                        } else {
                            let f = t!(i.üzv_al(&o, a, Some(kod.yerlər[pc - 1])), 'x);
                            ç.yığın.push(f);
                            ç.yığın.push(D::T(0));
                        }
                    }
                    Əmr::MetodÇağır(a, n) => {
                        let k = ç.yığın.len() - *n as usize;
                        let args = ç.yığın.split_off(k);
                        let r = t!(metod_çağır(i, kod, ç, *a, args, vec![], pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::MetodÇağırArq(a) => {
                        let (args, adlı) = ç.arqlar.pop().unwrap();
                        let r = t!(metod_çağır(i, kod, ç, *a, args, adlı, pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    // ── Üzv və indeks ───────────────────────────────────
                    Əmr::ÜzvAl(a, təhlükəsiz) => {
                        let o = ç.pop();
                        let a = &kod.adlar[*a as usize];
                        if o.boşdur() {
                            if *təhlükəsiz {
                                ç.yığın.push(D::Boş);
                                continue;
                            }
                            break 'x xəta_yer(
                                "BoşDəyərXətası",
                                format!("`boş` dəyərdə `{}` üzvü yoxdur", a),
                                Some(kod.yerlər[pc - 1]),
                                "ALQ-R004",
                            );
                        }
                        let r = t!(i.üzv_al(&o, a, Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::ÜzvAlXam(a) => {
                        let o = ç.pop();
                        let r = t!(i.üzv_al(&o, &kod.adlar[*a as usize], Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::ÜzvQoy(a) => {
                        let o = ç.pop();
                        let d = ç.pop();
                        t!(i.üzv_qoy(&o, &kod.adlar[*a as usize], d, Some(kod.yerlər[pc - 1])), 'x);
                    }
                    Əmr::İndeksAl => {
                        let x = ç.pop();
                        let o = ç.pop();
                        if let (D::Siyahı(l), D::T(j)) = (&o, &x) {
                            let l = l.borrow();
                            let n = l.len() as i64;
                            let k = if *j < 0 { *j + n } else { *j };
                            if k >= 0 && k < n {
                                let d = l[k as usize].clone();
                                drop(l);
                                ç.yığın.push(d);
                                continue;
                            }
                        }
                        let r = t!(i.indeks_al(&o, &x, Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::İndeksQoy => {
                        let x = ç.pop();
                        let o = ç.pop();
                        let d = ç.pop();
                        t!(i.indeks_qoy(&o, x, d, Some(kod.yerlər[pc - 1])), 'x);
                    }
                    Əmr::DilimYoxla => {
                        let o = ç.yığın.last().cloned().unwrap_or(D::Boş);
                        t!(dilim_uzunluğu(&o, kod.yerlər[pc - 1]), 'x);
                    }
                    Əmr::Dilim(b, s, xaric) => {
                        let sd = if *s { Some(ç.pop()) } else { None };
                        let bd = if *b { Some(ç.pop()) } else { None };
                        let o = ç.pop();
                        let yer = kod.yerlər[pc - 1];
                        let n = t!(dilim_uzunluğu(&o, yer), 'x);
                        let r = t!(dilim_tətbiq(&o, n, bd, sd, *xaric, yer), 'x);
                        ç.yığın.push(r);
                    }
                    // ── Kolleksiyalar ───────────────────────────────────
                    Əmr::Siyahı(n) => {
                        let k = ç.yığın.len() - *n as usize;
                        let v = ç.yığın.split_off(k);
                        ç.yığın.push(D::siyahı(v));
                    }
                    Əmr::SiyahıYeni => ç.yığın.push(D::siyahı(vec![])),
                    Əmr::SiyahıƏlavə => {
                        let d = ç.pop();
                        if let Some(D::Siyahı(l)) = ç.yığın.last() {
                            l.borrow_mut().push(d);
                        }
                    }
                    Əmr::SiyahıYay => {
                        let d = ç.pop();
                        let yer = Some(kod.yerlər[pc - 1]);
                        let Some(D::Siyahı(l)) = ç.yığın.last().cloned() else { unreachable!() };
                        let mut it = t!(i.iterasiya(&d, yer), 'x);
                        while let Some(x) = t!(it.növbəti(i, yer), 'x) {
                            l.borrow_mut().push(x);
                        }
                    }
                    Əmr::LüğətYeni => ç.yığın.push(D::lüğət(Lüğət::default())),
                    Əmr::LüğətQoy => {
                        let k = ç.pop();
                        let v = ç.pop();
                        let k = t!(yer_qoy(Açar::yeni(k), Some(kod.yerlər[pc - 1])), 'x);
                        if let Some(D::Lüğət(l)) = ç.yığın.last() {
                            l.borrow_mut().insert(k, v);
                        }
                    }
                    Əmr::LüğətYay => {
                        let d = ç.pop();
                        match &d {
                            D::Lüğət(x) => {
                                if let Some(D::Lüğət(l)) = ç.yığın.last() {
                                    let x: Vec<(Açar, D)> = x.borrow().iter().map(|(k, v)| (k.clone(), v.clone())).collect();
                                    let mut l = l.borrow_mut();
                                    for (k, v) in x {
                                        l.insert(k, v);
                                    }
                                }
                            }
                            _ => {
                                break 'x xəta_yer("TipXətası", "`...` lüğətdə lüğət gözləyir", Some(kod.yerlər[pc - 1]), "ALQ-T001")
                            }
                        }
                    }
                    Əmr::DəstYeni => ç.yığın.push(D::dəst(Dəst::default())),
                    Əmr::DəstƏlavə => {
                        let d = ç.pop();
                        let k = t!(yer_qoy(Açar::yeni(d), Some(kod.yerlər[pc - 1])), 'x);
                        if let Some(D::Dəst(l)) = ç.yığın.last() {
                            l.borrow_mut().insert(k);
                        }
                    }
                    Əmr::Kortej(n) => {
                        let k = ç.yığın.len() - *n as usize;
                        let v = ç.yığın.split_off(k);
                        ç.yığın.push(D::kortej(v));
                    }
                    Əmr::Formatla(f) => {
                        let d = ç.pop();
                        let f = if *f == u32::MAX { None } else { kod.sabitlər[*f as usize].mətn_al() };
                        let s = t!(crate::icraci::format::formatla(i, &d, f), 'x);
                        ç.yığın.push(D::str(s));
                    }
                    Əmr::Birləşdir(n) => {
                        let k = ç.yığın.len() - *n as usize;
                        let mut s = String::new();
                        for d in &ç.yığın[k..] {
                            if let D::S(x) = d {
                                s.push_str(x);
                            }
                        }
                        ç.yığın.truncate(k);
                        ç.yığın.push(D::str(s));
                    }
                    Əmr::Diapazon(addım, xaric) => {
                        let a = if *addım { Some(ç.pop()) } else { None };
                        let s = ç.pop();
                        let b = ç.pop();
                        let yer = kod.yerlər[pc - 1];
                        let mut xəta = None;
                        for (n, d) in [("başlanğıc", &b), ("son", &s)] {
                            let ok = d.tamdır() || matches!(d, D::S(x) if x.chars().count() == 1);
                            if !ok {
                                xəta = Some(xəta_yer(
                                    "TipXətası",
                                    format!("diapazonun {} hissəsi tam ədəd olmalıdır, `{}` gəlib", n, tip_adı(d)),
                                    Some(yer),
                                    "ALQ-T001",
                                ));
                                break;
                            }
                        }
                        if let Some(x) = xəta {
                            break 'x x;
                        }
                        let kod_ = |d: D| match d {
                            D::S(x) => D::T(x.chars().next().unwrap() as i64),
                            d => d,
                        };
                        let r = t!(yer_qoy(diapazon_yarat(kod_(b), kod_(s), a, *xaric), Some(yer)), 'x);
                        ç.yığın.push(r);
                    }
                    // ── Digər ifadələr ──────────────────────────────────
                    Əmr::Çevir(h, təhlükəsiz) => {
                        let d = ç.pop();
                        let r = match i.çevir(&d, &kod.adlar[*h as usize], Some(kod.yerlər[pc - 1])) {
                            Err(Siqnal::Xəta(_)) if *təhlükəsiz => D::Boş,
                            r => t!(r, 'x),
                        };
                        ç.yığın.push(r);
                    }
                    Əmr::TipYoxla(k) => {
                        let d = ç.pop();
                        let r = t!(i.tip_uyğundur(&d, &kod.tiplər[*k as usize], ç.m()), 'x);
                        ç.yığın.push(D::M(r));
                    }
                    Əmr::Üzvlük => {
                        let k = ç.pop();
                        let el = ç.pop();
                        let r = t!(i.üzvlük(&el, &k, Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(D::M(r));
                    }
                    Əmr::BoşYoxla(inkar) => {
                        let d = ç.pop();
                        ç.yığın.push(D::M(d.boşdur() != *inkar));
                    }
                    Əmr::Boru => {
                        let f = ç.pop();
                        let d = ç.pop();
                        let r = t!(i.çağır(&f, vec![d], vec![], Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::MəcburiAç => {
                        if matches!(ç.yığın.last(), Some(D::Boş) | None) {
                            break 'x xəta_yer(
                                "BoşDəyərXətası",
                                "`!` operatoru `boş` dəyərə tətbiq edildi",
                                Some(kod.yerlər[pc - 1]),
                                "ALQ-R004",
                            );
                        }
                    }
                    Əmr::Yayma => {
                        if let Some(D::Nümunə(n)) = ç.yığın.last() {
                            if &*n.sinif.ad == "Xəta" {
                                let d = ç.pop();
                                break 'x Siqnal::Qaytar(d);
                            }
                        }
                    }
                    Əmr::TipDəyəri(k) => {
                        let h = t!(i.tip_dəyəri(&kod.tiplər[*k as usize], ç.m()), 'x);
                        ç.yığın.push(h);
                    }
                    Əmr::Yeni(q) => {
                        let (a, adlı) = ç.arqlar.pop().unwrap();
                        let h = ç.pop();
                        let yer = Some(kod.yerlər[pc - 1]);
                        let r = match &h {
                            D::Sinif(s) => {
                                let q = if *q == u32::MAX { None } else { Some(&*kod.adlar[*q as usize]) };
                                i.nümunə_yarat(s, q, a, adlı, yer)
                            }
                            D::Funksiya(_) | D::Daxili(_) | D::Metod(_) | D::XətaSinfi(_) => i.çağır(&h, a, adlı, yer),
                            _ => Err(xəta_yer(
                                "TipXətası",
                                format!("`yeni` sinif gözləyir, `{}` gəlib", tip_adı(&h)),
                                yer,
                                "ALQ-T002",
                            )),
                        };
                        let r = t!(r, 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::Gözlə => {
                        let d = ç.pop();
                        let r = t!(i.gözlə(d, Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::ÜstQur => {
                        let s = ç.pop();
                        let özü = ç.pop();
                        match s {
                            D::Sinif(s) => ç.yığın.push(D::Üst(Rc::new((özü, s)))),
                            _ => break 'x xəta("TipXətası", "baza sinif yoxdur", "ALQ-T012"),
                        }
                    }
                    Əmr::Lambda(k) => {
                        let f = funksiya_yarat(kod, ç, *k);
                        ç.yığın.push(f);
                    }
                    // ── Cümlələr ────────────────────────────────────────
                    Əmr::Xəta(k) => {
                        let (tip, mesaj, kod_) = &kod.xətalar[*k as usize];
                        break 'x xəta_yer(tip, mesaj.clone(), Some(kod.yerlər[pc - 1]), kod_);
                    }
                    Əmr::AtXəta => {
                        let d = ç.pop();
                        let yer = Some(kod.yerlər[pc - 1]);
                        if let D::Nümunə(n) = &d {
                            let mesaj = match n.sahə("mesaj") {
                                Some(x) => t!(mətnə(i, &x), 'x),
                                None => String::new(),
                            };
                            break 'x Siqnal::Xəta(Box::new(AlqorXəta {
                                tip: n.sinif.ad.clone(),
                                mesaj,
                                yer,
                                kod: String::new(),
                                dəyər: Some(d.clone()),
                            }));
                        }
                        let mesaj = t!(mətnə(i, &d), 'x);
                        break 'x Siqnal::Xəta(Box::new(AlqorXəta { tip: ad("Xəta"), mesaj, yer, kod: String::new(), dəyər: Some(d) }));
                    }
                    Əmr::İddia(var) => {
                        let mesaj = if *var {
                            let d = ç.pop();
                            t!(mətnə(i, &d), 'x)
                        } else {
                            "iddia pozuldu".into()
                        };
                        break 'x xəta_yer("İddiaXətası", mesaj, Some(kod.yerlər[pc - 1]), "ALQ-R007");
                    }
                    Əmr::Artır(artır) => {
                        let cari = ç.pop();
                        let yer = Some(kod.yerlər[pc - 1]);
                        let r = match &cari {
                            D::T(_) | D::BT(_) | D::O(_) => i.ikili_hesabla(if *artır { "+" } else { "-" }, &cari, &D::T(1), yer),
                            _ => Err(xəta_yer(
                                "TipXətası",
                                format!("`{}` ədəd gözləyir, `{}` gəlib", if *artır { "++" } else { "--" }, tip_adı(&cari)),
                                yer,
                                "ALQ-T008",
                            )),
                        };
                        let r = t!(r, 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::Ötür(k) => {
                        let m = ç.m().clone();
                        t!(i.cümlə(&kod.cümlələr[*k as usize], &m), 'x);
                    }
                    Əmr::Ötürİfadə(k) => {
                        let m = ç.m().clone();
                        let r = t!(i.ifadə(&kod.ifadələr[*k as usize], &m), 'x);
                        ç.yığın.push(r);
                    }
                    // ── Dövrlər ─────────────────────────────────────────
                    Əmr::İterAç => {
                        let d = ç.pop();
                        let lüğət = if let D::Lüğət(l) = &d { Some(l.clone()) } else { None };
                        let it = t!(i.iterasiya(&d, Some(kod.yerlər[pc - 1])), 'x);
                        ç.iterlər.push(VmIter { it, lüğət, indeks: 0 });
                    }
                    Əmr::İterNövbəti(h) => {
                        let yer = Some(kod.yerlər[pc - 1]);
                        let it = ç.iterlər.last_mut().unwrap();
                        let x = match &mut it.it {
                            İter::Diapazon(c, son, a) => {
                                if (*a > 0 && *c < *son) || (*a < 0 && *c > *son) {
                                    let x = *c;
                                    *c = c.saturating_add(*a);
                                    if *c == x {
                                        *son = x;
                                    }
                                    Some(D::T(x))
                                } else {
                                    None
                                }
                            }
                            it => t!(it.növbəti(i, yer), 'x),
                        };
                        match x {
                            Some(x) => {
                                ç.iterlər.last_mut().unwrap().indeks += 1;
                                ç.yığın.push(x);
                            }
                            None => pc = *h as usize,
                        }
                    }
                    Əmr::İterBağla => {
                        ç.iterlər.pop();
                    }
                    Əmr::İterİndeks => {
                        let n = ç.iterlər.last().unwrap().indeks - 1;
                        ç.yığın.push(D::T(n));
                    }
                    Əmr::İterLüğətCüt(h) => {
                        let l = ç.iterlər.last().unwrap().lüğət.clone();
                        match l {
                            None => pc = *h as usize,
                            Some(l) => {
                                let el = ç.pop();
                                let v = l.borrow().get(&Açar(el.clone())).cloned();
                                match v {
                                    Some(v) => ç.yığın.push(D::kortej(vec![el, v])),
                                    None => {
                                        let s = t!(mətnə(i, &el), 'x);
                                        break 'x xəta_yer(
                                            "AçarXətası",
                                            format!("lüğətdə `{}` açarı yoxdur", s),
                                            Some(kod.yerlər[pc - 1]),
                                            "ALQ-R003",
                                        );
                                    }
                                }
                            }
                        }
                    }
                    Əmr::DiapazonDeyilsəAtla(h) => {
                        if !matches!(ç.yığın.last(), Some(D::Diapazon(_))) {
                            pc = *h as usize;
                        }
                    }
                    Əmr::DiapazonAddım => {
                        let a = ç.pop();
                        let r = ç.pop();
                        let D::Diapazon(r) = r else { unreachable!() };
                        let d = t!(diapazon_yarat(D::T(r.başlanğıc), D::T(r.son), Some(a), r.xaric), 'x);
                        ç.yığın.push(d);
                    }
                    Əmr::TəkrarSay => {
                        let s = ç.pop();
                        let n = match &s {
                            D::T(n) => *n,
                            D::BT(_) => i64::MAX,
                            _ => {
                                break 'x xəta_yer(
                                    "TipXətası",
                                    format!("`təkrarla` tam ədəd gözləyir, `{}` gəlib", tip_adı(&s)),
                                    Some(kod.yerlər[pc - 1]),
                                    "ALQ-T001",
                                )
                            }
                        };
                        ç.yığın.push(D::T(n));
                    }
                    Əmr::Sayğac(y, hədd, h) => {
                        let (Some(D::T(c)), Some(D::T(n))) = (&ç.yuvalar[*y as usize], &ç.yuvalar[*hədd as usize]) else {
                            unreachable!()
                        };
                        let (c, n) = (*c + 1, *n);
                        ç.yuvalar[*y as usize] = Some(D::T(c));
                        if c > n {
                            pc = *h as usize;
                        }
                    }
                    // ── Dağıtma ─────────────────────────────────────────
                    Əmr::Dağıt(n, q) => {
                        let d = ç.pop();
                        let yer = Some(kod.yerlər[pc - 1]);
                        let el = match i.iterasiya(&d, yer).and_then(|it| it.hamısı(i, yer)) {
                            Ok(v) => v,
                            Err(Siqnal::Xəta(_)) => {
                                break 'x xəta_yer("TipXətası", format!("`{}` dağıtıla bilməz", tip_adı(&d)), yer, "ALQ-T001")
                            }
                            Err(x) => break 'x x,
                        };
                        let n = *n as usize;
                        if *q == u32::MAX {
                            if el.len() != n {
                                break 'x xəta_yer(
                                    "ArqumentXətası",
                                    format!("{} ad gözlənilirdi, {} dəyər var", n, el.len()),
                                    yer,
                                    "ALQ-T001",
                                );
                            }
                            ç.yığın.extend(el.into_iter().rev());
                        } else {
                            let q = *q as usize;
                            let sonra = n - q - 1;
                            if el.len() < q + sonra {
                                break 'x xəta_yer("ArqumentXətası", "dağıtma üçün element çatmır", yer, "ALQ-T001");
                            }
                            let m = el.len();
                            ç.yığın.extend(el[m - sonra..].iter().rev().cloned());
                            ç.yığın.push(D::siyahı(el[q..m - sonra].to_vec()));
                            ç.yığın.extend(el[..q].iter().rev().cloned());
                        }
                    }
                    Əmr::Paketlə(nt, nv) => {
                        let yer = Some(kod.yerlər[pc - 1]);
                        let v = if *nv == 1 {
                            let d = ç.pop();
                            let it = t!(i.iterasiya(&d, yer), 'x);
                            t!(it.hamısı(i, yer), 'x)
                        } else {
                            let k = ç.yığın.len() - *nv as usize;
                            ç.yığın.split_off(k)
                        };
                        if v.len() != *nt as usize {
                            break 'x xəta_yer("ArqumentXətası", "mənimsətmədə sayllar uyğun gəlmir", yer, "ALQ-T001");
                        }
                        ç.yığın.extend(v.into_iter().rev());
                    }
                    Əmr::StandartDəyər(k) => {
                        let t = if *k == u32::MAX { None } else { Some(&kod.tiplər[*k as usize]) };
                        ç.yığın.push(standart_dəyər(t));
                    }
                    // ── Cəhd ────────────────────────────────────────────
                    Əmr::CəhdTəmizlə(id) => ç.cəhdlər[*id as usize] = None,
                    Əmr::TutmaYoxla(id, ti, h) => {
                        let uyğun = match &ç.cəhdlər[*id as usize] {
                            Some(Siqnal::Xəta(x)) => tutma_uyğundur(&kod.tutmalar[*ti as usize], x),
                            _ => false,
                        };
                        if !uyğun {
                            pc = *h as usize;
                        }
                    }
                    Əmr::XətaObyekti(id) => {
                        let d = match &ç.cəhdlər[*id as usize] {
                            Some(Siqnal::Xəta(x)) => xəta_obyekti(x),
                            _ => D::Boş,
                        };
                        ç.yığın.push(d);
                    }
                    Əmr::NəhayətSon(id) => {
                        if let Some(s) = ç.cəhdlər[*id as usize].take() {
                            break 'x s;
                        }
                    }
                    // ── Qurma ───────────────────────────────────────────
                    Əmr::QurmaƏlavə(y) => {
                        let d = ç.pop();
                        if let Some(D::Siyahı(l)) = &ç.yuvalar[*y as usize] {
                            l.borrow_mut().push(d);
                        }
                    }
                    Əmr::QurmaLüğət(y) => {
                        let v = ç.pop();
                        let k = ç.pop();
                        let k = t!(yer_qoy(Açar::yeni(k), Some(kod.yerlər[pc - 1])), 'x);
                        if let Some(D::Lüğət(l)) = &ç.yuvalar[*y as usize] {
                            l.borrow_mut().insert(k, v);
                        }
                    }
                    Əmr::AçarYoxla => {
                        let k = ç.yığın.last().cloned().unwrap_or(D::Boş);
                        t!(yer_qoy(Açar::yeni(k), Some(kod.yerlər[pc - 1])), 'x);
                    }
                    Əmr::QurmaSon(y, növ) => {
                        let d = ç.yuvalar[*y as usize].take().unwrap_or(D::Boş);
                        let r = match (növ, &d) {
                            (1, D::Siyahı(l)) => {
                                let v = std::mem::take(&mut *l.borrow_mut());
                                let mut s = Dəst::default();
                                for x in v {
                                    s.insert(t!(yer_qoy(Açar::yeni(x), Some(kod.yerlər[pc - 1])), 'x));
                                }
                                D::dəst(s)
                            }
                            (2, D::Siyahı(l)) => {
                                let v = std::mem::take(&mut *l.borrow_mut());
                                D::Gen(Generator::yeni(GenMənbə::Siyahı(v.into_iter())))
                            }
                            _ => d,
                        };
                        ç.yığın.push(r);
                    }
                    // ── Parametrlər ─────────────────────────────────────
                    Əmr::ParamAl(pi, h) => {
                        let f = ç.f.unwrap();
                        let p = &f.parametrlər[*pi as usize];
                        if let Some(d) = ç.args.next() {
                            ç.yığın.push(d);
                            pc = *h as usize;
                        } else if let Some(d) = (!ç.adlı.is_empty()).then(|| adlı_götür(&mut ç.adlı, &p.ad)).flatten() {
                            ç.yığın.push(d);
                            pc = *h as usize;
                        } else if p.standart.is_none() {
                            break 'x xəta_yer(
                                "ArqumentXətası",
                                format!("`{}` üçün `{}` arqumenti verilməyib", f.ad, p.ad),
                                ç.çağırış_yeri,
                                "ALQ-T003",
                            );
                        }
                    }
                    Əmr::ParamAdlı(pi, h) => {
                        let f = ç.f.unwrap();
                        let p = &f.parametrlər[*pi as usize];
                        if let Some(d) = adlı_götür(&mut ç.adlı, &p.ad) {
                            ç.yığın.push(d);
                            pc = *h as usize;
                        } else if p.standart.is_none() {
                            break 'x xəta_yer(
                                "ArqumentXətası",
                                format!("`{}` üçün `{}` adlı arqumenti məcburidir", f.ad, p.ad),
                                ç.çağırış_yeri,
                                "ALQ-T003",
                            );
                        }
                    }
                    Əmr::ParamVariadic => {
                        let v: Vec<D> = std::mem::take(&mut ç.args).collect();
                        ç.yığın.push(D::siyahı(v));
                    }
                    Əmr::ParamAdlıVariadic => {
                        let mut l = Lüğət::default();
                        for (k, d) in ç.adlı.drain(..) {
                            l.insert(Açar(D::S(k)), d);
                        }
                        ç.yığın.push(D::lüğət(l));
                    }
                    Əmr::ParamSon => {
                        if !ç.adlı.is_empty() {
                            let f = ç.f.unwrap();
                            let mut a: Vec<String> = ç.adlı.iter().map(|(k, _)| k.to_string()).collect();
                            a.sort();
                            break 'x xəta_yer(
                                "ArqumentXətası",
                                format!("`{}` naməlum adlı arqument: {}", f.ad, a.join(", ")),
                                ç.çağırış_yeri,
                                "ALQ-T004",
                            );
                        }
                    }
                    Əmr::XassəQoy(a) => {
                        let d = ç.pop();
                        if let Some(D::Nümunə(n)) = &ç.f.unwrap().özü {
                            n.sahələr.borrow_mut().insert(kod.adlar[*a as usize].clone(), d);
                        }
                    }
                }
            }
        };
        let _ = cari;
        match siqnal_emal(kod, ç, s, (pc - 1) as u32) {
            Ok(h) => pc = h as usize,
            Err(s) => {
                return match (kod.növ, s) {
                    (KodNövü::Blok, Siqnal::Qaytar(d)) | (KodNövü::Blok, Siqnal::Ver(d)) => Ok(d),
                    (_, s) => Err(s),
                }
            }
        }
    }
}

fn metod_çağır(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə, a: u32, args: Vec<D>, adlı: Adlı, pc: usize) -> Nəticə {
    let flag = ç.pop();
    let x = ç.pop();
    let yer = Some(kod.yerlər[pc]);
    if let D::T(1) = flag {
        yer_qoy(crate::icraci::metodlar::metod_çağır(i, &x, &kod.adlar[a as usize], args, adlı), yer)
    } else {
        i.çağır(&x, args, adlı, yer)
    }
}
