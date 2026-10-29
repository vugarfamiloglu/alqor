//! Bayt-kod maşını (interpretator dövrü).

use super::emr::*;
use crate::icraci::cagiris::*;
use crate::icraci::deyerler::*;
use crate::icraci::icraci::{dilim_tətbiq, dilim_uzunluğu, İcraçı, İter, STEK_HƏDDİ};
use crate::icraci::muhit::{sabit_xətası, Mühit};
use crate::xeta::Yer;
use std::cell::{RefCell, UnsafeCell};
use std::ops::{Index, IndexMut};
use std::rc::Rc;

struct VmIter {
    it: İter,
    lüğət: Option<Rc<RefCell<Lüğət>>>,
    indeks: i64,
}

/// Nadir istifadə olunan çərçivə sahələri (lazım olanda yaradılır)
struct Əlavə<'f> {
    arqlar: Vec<(Vec<D>, Adlı)>,
    cəhdlər: Vec<Option<Siqnal>>,
    sabitlər: Vec<bool>,
    f: Option<&'f Rc<Funksiya>>,
    args: std::vec::IntoIter<D>,
    adlı: Adlı,
    çağırış_yeri: Option<Yer>,
}

/// Paylaşılan dəyər anbarı: hər çərçivənin yuvaları və operand yığını
/// ardıcıl yerləşir (LIFO). Korutin daxilində yaradılan çərçivələr (dayandırıla
/// bilər) öz ayrıca anbarından istifadə edir.
type Anbar = Vec<Option<D>>;

thread_local! {
    static ANBAR: UnsafeCell<Anbar> = UnsafeCell::new(Vec::with_capacity(4096));
}

/// Çərçivənin yuvaları (anbarda `bünövrə..bünövrə+n`)
struct Yuvalar {
    st: *mut Anbar,
    bünövrə: usize,
}

impl Index<usize> for Yuvalar {
    type Output = Option<D>;
    #[inline(always)]
    fn index(&self, i: usize) -> &Option<D> {
        unsafe { (&*self.st).get_unchecked(self.bünövrə + i) }
    }
}

impl IndexMut<usize> for Yuvalar {
    #[inline(always)]
    fn index_mut(&mut self, i: usize) -> &mut Option<D> {
        unsafe { (&mut *self.st).get_unchecked_mut(self.bünövrə + i) }
    }
}

/// Operand yığını (anbarda `alt..`)
struct Yığın {
    st: *mut Anbar,
    alt: usize,
}

impl Yığın {
    #[inline(always)]
    #[allow(clippy::mut_from_ref)]
    fn v(&self) -> &mut Anbar {
        unsafe { &mut *self.st }
    }
    #[inline(always)]
    fn push(&mut self, d: D) {
        self.v().push(Some(d));
    }
    #[inline(always)]
    fn pop(&mut self) -> Option<D> {
        let v = self.v();
        if v.len() > self.alt {
            v.pop().flatten()
        } else {
            None
        }
    }
    #[inline(always)]
    fn len(&self) -> usize {
        self.v().len() - self.alt
    }
    #[inline(always)]
    fn last(&self) -> Option<&D> {
        let v = self.v();
        if v.len() > self.alt {
            v.last().and_then(|x| x.as_ref())
        } else {
            None
        }
    }
    #[inline(always)]
    fn last_mut(&mut self) -> Option<&mut D> {
        let alt = self.alt;
        let v = self.v();
        if v.len() > alt {
            v.last_mut().and_then(|x| x.as_mut())
        } else {
            None
        }
    }
    fn clear(&mut self) {
        let alt = self.alt;
        self.v().truncate(alt);
    }
    fn truncate(&mut self, k: usize) {
        let alt = self.alt;
        self.v().truncate(alt + k);
    }
    /// Yalnız buraxılacaq resursu olmayan dəyərlər üçün
    unsafe fn set_len(&mut self, k: usize) {
        let alt = self.alt;
        self.v().set_len(alt + k);
    }
    fn split_off(&mut self, k: usize) -> Vec<D> {
        let alt = self.alt;
        self.v().drain(alt + k..).map(|x| x.unwrap_or(D::Boş)).collect()
    }
    fn extend(&mut self, it: impl IntoIterator<Item = D>) {
        let v = self.v();
        for d in it {
            v.push(Some(d));
        }
    }
    /// `k`-cı elementi götürür (yerində `None` qalır)
    #[inline(always)]
    fn götür(&mut self, k: usize) -> D {
        let alt = self.alt;
        self.v()[alt + k].take().unwrap_or(D::Boş)
    }
}

impl Index<usize> for Yığın {
    type Output = D;
    #[inline(always)]
    fn index(&self, k: usize) -> &D {
        match &self.v()[self.alt + k] {
            Some(d) => d,
            None => unreachable!("boş operand"),
        }
    }
}

/// Bir çağırışın çərçivəsi
struct Çərçivə<'f> {
    yuvalar: Yuvalar,
    yığın: Yığın,
    st: *mut Anbar,
    bünövrə: usize,
    _özəl: Option<Box<Anbar>>,
    baza: Mühit,
    mühitlər: Vec<Mühit>,
    iterlər: Vec<VmIter>,
    əl: Option<Box<Əlavə<'f>>>,
}

impl Drop for Çərçivə<'_> {
    fn drop(&mut self) {
        unsafe { (*self.st).truncate(self.bünövrə) };
    }
}

impl<'f> Çərçivə<'f> {
    #[inline(always)]
    fn yeni(i: &İcraçı, kod: &Kod, baza: Mühit) -> Self {
        Self::anbarda(i, kod, baza, None)
    }

    /// `ana` — çağıranın anbarı (eyni icra kontekstində iç-içə çərçivə)
    #[inline(always)]
    fn anbarda(i: &İcraçı, kod: &Kod, baza: Mühit, ana: Option<*mut Anbar>) -> Self {
        let mut özəl = None;
        let st: *mut Anbar = if let Some(a) = ana {
            a
        } else if i.ver.get().is_null() {
            ANBAR.with(|a| a.get())
        } else {
            let mut b: Box<Anbar> = Box::new(Vec::with_capacity(kod.yuva_sayı + 16));
            let p = &mut *b as *mut Anbar;
            özəl = Some(b);
            p
        };
        let v = unsafe { &mut *st };
        let bünövrə = v.len();
        for _ in 0..kod.yuva_sayı {
            v.push(None);
        }
        Çərçivə {
            yuvalar: Yuvalar { st, bünövrə },
            yığın: Yığın { st, alt: bünövrə + kod.yuva_sayı },
            st,
            bünövrə,
            _özəl: özəl,
            baza,
            mühitlər: vec![],
            iterlər: vec![],
            əl: None,
        }
    }

    fn əl(&mut self) -> &mut Əlavə<'f> {
        self.əl.get_or_insert_with(|| {
            Box::new(Əlavə {
                arqlar: vec![],
                cəhdlər: vec![],
                sabitlər: vec![],
                f: None,
                args: Vec::new().into_iter(),
                adlı: vec![],
                çağırış_yeri: None,
            })
        })
    }

    fn cəhd(&mut self, id: u32) -> &mut Option<Siqnal> {
        let ə = self.əl();
        if ə.cəhdlər.len() <= id as usize {
            ə.cəhdlər.resize_with(id as usize + 1, || None);
        }
        &mut ə.cəhdlər[id as usize]
    }

    #[inline]
    fn sabitdir(&self, y: usize) -> bool {
        match &self.əl {
            Some(ə) => ə.sabitlər.get(y).copied().unwrap_or(false),
            None => false,
        }
    }

    fn sabit_qoy(&mut self, y: usize) {
        let ə = self.əl();
        if ə.sabitlər.len() <= y {
            ə.sabitlər.resize(y + 1, false);
        }
        ə.sabitlər[y] = true;
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
    let mut ç = çərçivə_qur(i, kod, f, f.özü.as_ref(), None);
    if args.len() > kod.mövqeli_say && !kod.variadic_var {
        return Err(xəta_yer(
            "ArqumentXətası",
            format!("`{}` ən çox {} mövqeli arqument qəbul edir, {} verilib", f.ad, kod.mövqeli_say, args.len()),
            yer,
            "ALQ-T003",
        ));
    }
    {
        let ə = ç.əl();
        ə.f = Some(f);
        ə.args = args.into_iter();
        ə.adlı = adlı;
        ə.çağırış_yeri = yer;
    }
    icra_gecikdirli(i, kod, &mut ç, 0)
}

/// Çərçivə: funksiya Mühit-i, `özü` və `__sinif__`
#[inline(always)]
fn çərçivə_qur<'f>(i: &İcraçı, kod: &Kod, f: &Rc<Funksiya>, özü: Option<&D>, ana: Option<*mut Anbar>) -> Çərçivə<'f> {
    let mut ç = Çərçivə::anbarda(i, kod, f.mühit.clone(), ana);
    if kod.funksiya_mühiti {
        let n = f.parametrlər.len() + if özü.is_some() { 2 } else { 0 };
        ç.mühitlər.push(f.mühit.alt_tutumla(n));
    }
    let sinif = match özü {
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
    ç
}

#[inline(always)]
fn icra_gecikdirli(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə, pc: usize) -> Nəticə {
    if !kod.gecikdir_var {
        return icra(i, kod, ç, pc);
    }
    i.gecikdirilmiş.borrow_mut().push(vec![]);
    let r = icra(i, kod, ç, pc);
    let gecikmiş = i.gecikdirilmiş.borrow_mut().pop().unwrap_or_default();
    for (e, mm) in gecikmiş.iter().rev() {
        match i.ifadə(e, mm) {
            Ok(_) | Err(Siqnal::Xəta(_)) => {}
            Err(x) => return Err(x),
        }
    }
    r
}

/// Sürətli çağırış: sadə parametrli VM funksiyası, arqumentlər birbaşa
/// çağıranın yığınından yuvalara köçürülür (`funksiya_çağır` ilə eyni
/// semantika). Uyğun deyilsə `None`.
#[allow(clippy::too_many_arguments)]
fn sürətli_çağır(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə, f: &Rc<Funksiya>, özü: Option<&D>, n: usize, keş: u32, yer: Yer) -> Option<Nəticə> {
    if f.asinxron || f.generator || f.yaddaş.is_some() {
        return None;
    }
    let açar = match &f.gövdə {
        FGövdə::Blok(b) => Rc::as_ptr(b) as usize,
        FGövdə::İfadə(e) => Rc::as_ptr(e) as *const u8 as usize,
    };
    let keş = &kod.çağırış_keşləri[keş as usize];
    let hədəf = match &*keş.borrow() {
        Some((a, k)) if *a == açar && Rc::ptr_eq(k.parametrlər.as_ref()?, &f.parametrlər) => Some(k.clone()),
        _ => None,
    };
    let hədəf = match hədəf {
        Some(k) => {
            super::vm_çağırışı_say();
            k
        }
        None => {
            let k = super::kod_tap(f)?;
            *keş.borrow_mut() = Some((açar, k.clone()));
            k
        }
    };
    let py = hədəf.param_yuvaları.as_ref()?;
    if py.len() != n {
        return None;
    }
    let d = i.dərinlik.get() + 1;
    if d > STEK_HƏDDİ {
        return Some(Err(xəta_yer(
            "StekDaşmaXətası",
            format!("çağırış dərinliyi {} həddini aşdı — sonsuz rekursiya?", STEK_HƏDDİ),
            Some(yer),
            "ALQ-R010",
        )));
    }
    let k = ç.yığın.len() - n;
    let mut yeni = çərçivə_qur(i, &hədəf, f, özü, Some(ç.st));
    for (j, y) in py.iter().enumerate() {
        let d = ç.yığın.götür(k + j);
        yeni.yuvalar[*y as usize] = Some(dəyər_kopyası(d));
    }
    i.dərinlik.set(d);
    let r = icra_gecikdirli(i, &hədəf, &mut yeni, hədəf.gövdə_pc as usize);
    i.dərinlik.set(i.dərinlik.get() - 1);
    Some(r)
}

/// Generator gövdəsi (korutin daxilində): parametrlər artıq `m`-də bağlanıb
#[cfg(not(target_arch = "wasm32"))]
pub fn generator_işlət(i: &İcraçı, kod: &Kod, f: &Rc<Funksiya>, m: Mühit) -> Nəticə<()> {
    let mut ç = Çərçivə::yeni(i, kod, f.mühit.clone());
    ç.mühitlər.push(m);
    match icra(i, kod, &mut ç, kod.gövdə_pc as usize) {
        Ok(_) | Err(Siqnal::Qaytar(_)) | Err(Siqnal::Dayan(_)) => Ok(()),
        Err(x) => Err(x),
    }
}

/// Proqramın yuxarı səviyyəsi (qlobal əhatədə)
pub fn kök_işlət(i: &İcraçı, kod: &Kod) -> Nəticə<()> {
    let mut ç = Çərçivə::yeni(i, kod, i.qlobal.clone());
    icra(i, kod, &mut ç, 0).map(|_| ())
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
            if ç.sabitdir(u as usize) {
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

/// Tam ədədlər üçün sürətli yol (ağac icraçısının `ikili_hesabla`-sı ilə eyni nəticə)
#[inline(always)]
fn tam_op(op: Op, x: i64, y: i64) -> Option<D> {
    match op {
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
        Op::Böl if y != 0 && x.abs() < (1 << 53) && y.abs() < (1 << 53) => Some(D::O(x as f64 / y as f64)),
        _ => None,
    }
}

/// Müqayisə operatoru (yalnız müqayisələr üçün çağırılır)
#[inline(always)]
fn müq(op: Op, x: i64, y: i64) -> bool {
    match op {
        Op::Kiçik => x < y,
        Op::Böyük => x > y,
        Op::KiçikBərabər => x <= y,
        Op::BöyükBərabər => x >= y,
        Op::Bərabər => x == y,
        _ => x != y,
    }
}

/// Ümumi ikili əməliyyat (onluq sürətli yolu + `ikili_hesabla`)
#[inline(never)]
fn ikili_ümumi(i: &İcraçı, kod: &Kod, op: Op, a: &D, b: &D, pc: usize) -> Nəticə {
    if let (D::T(x), D::T(y)) = (a, b) {
        if let Some(r) = tam_op(op, *x, *y) {
            return Ok(r);
        }
    } else if let (D::O(x), D::O(y)) = (a, b) {
        let (x, y) = (*x, *y);
        let r = match op {
            Op::Topla => Some(D::O(x + y)),
            Op::Çıx => Some(D::O(x - y)),
            Op::Vur => Some(D::O(x * y)),
            Op::Böl if y != 0.0 => Some(D::O(x / y)),
            // NaN: ağac icraçısında müqayisə `0` sayılır — ümumi yola burax
            _ if x.is_nan() || y.is_nan() => None,
            Op::Kiçik => Some(D::M(x < y)),
            Op::Böyük => Some(D::M(x > y)),
            Op::KiçikBərabər => Some(D::M(x <= y)),
            Op::BöyükBərabər => Some(D::M(x >= y)),
            _ => None,
        };
        if let Some(r) = r {
            return Ok(r);
        }
    }
    i.ikili_hesabla(op.mətn(), a, b, Some(kod.yerlər[pc]))
}

/// `YuvaQoy` semantikası (kopya + sabit/təyin olunmamış yoxlaması)
#[inline(always)]
fn yuvaya(kod: &Kod, ç: &mut Çərçivə, y: u32, d: D) -> Nəticə<()> {
    let d = dəyər_kopyası(d);
    if y & ELAN_BİTİ != 0 {
        ç.yuvalar[(y & !ELAN_BİTİ) as usize] = Some(d);
        return Ok(());
    }
    let yi = y as usize;
    if ç.yuvalar[yi].is_some() && (!kod.sabit_var || !ç.sabitdir(yi)) {
        ç.yuvalar[yi] = Some(d);
        Ok(())
    } else {
        yuva_yaz(kod, ç, y, d)
    }
}

/// Yuvanın dəyəri (təyin olunmayıbsa xarici ad)
#[inline]
fn yuva_oxu(kod: &Kod, ç: &Çərçivə, y: u32) -> Nəticə {
    match &ç.yuvalar[y as usize] {
        Some(d) => Ok(d.clone()),
        None => yuva_boş_al(kod, ç, y),
    }
}

/// Tez-tez çağırılan daxili metodlar (`metodlar::metod_çağır` ilə eyni nəticə).
/// Yığında `[obyekt, _, 1, arqumentlər...]`, `fi` — bayrağın indeksi.
#[inline]
fn tez_metod(kod: u8, ç: &mut Çərçivə, fi: usize, n: usize) -> Option<Nəticə> {
    let o = &ç.yığın[fi - 2];
    match (kod, o) {
        (1, D::Siyahı(l)) if n >= 1 => {
            let l = l.clone();
            let x = ç.yığın.götür(fi + 1);
            l.borrow_mut().push(x);
            Some(Ok(D::Boş))
        }
        (2, D::Siyahı(l)) if n == 0 => Some(Ok(D::T(l.borrow().len() as i64))),
        (2, D::Lüğət(l)) if n == 0 => Some(Ok(D::T(l.borrow().len() as i64))),
        (3, D::Lüğət(l)) if n == 1 || n == 2 => {
            let l = l.clone();
            let st = if n == 2 { ç.yığın[fi + 2].clone() } else { D::Boş };
            let k = match Açar::yeni(ç.yığın.götür(fi + 1)) {
                Ok(k) => k,
                Err(e) => return Some(Err(e)),
            };
            let r = l.borrow().get(&k).cloned().unwrap_or(st);
            Some(Ok(r))
        }
        (4, D::Lüğət(l)) if n >= 2 => {
            let l = l.clone();
            let k = match Açar::yeni(ç.yığın.götür(fi + 1)) {
                Ok(k) => k,
                Err(e) => return Some(Err(e)),
            };
            let v = ç.yığın.götür(fi + 2);
            l.borrow_mut().insert(k, v);
            Some(Ok(D::Boş))
        }
        _ => None,
    }
}

#[cold]
fn boş_üzv_xətası(a: &str, yer: Yer) -> Siqnal {
    xəta_yer("BoşDəyərXətası", format!("`boş` dəyərdə `{}` üzvü yoxdur", a), Some(yer), "ALQ-R004")
}

/// `üzv_al` + sinif üzrə sahə indeksi keşi
#[inline]
fn üzv_al_keşli(i: &İcraçı, kod: &Kod, k: u32, o: &D, a: &Ad, yer: Yer) -> Nəticə {
    if let D::Nümunə(n) = o {
        if n.aktyor.is_some() {
            return i.üzv_al(o, a, Some(yer));
        }
        let keş = &kod.üzv_keşləri[k as usize];
        if let Some((s, idx, _)) = &*keş.borrow() {
            if Rc::ptr_eq(s, &n.sinif) {
                if let Some((açar, v)) = n.sahələr.borrow().get_index(*idx as usize) {
                    if eyni_ad(açar, a) {
                        return Ok(v.clone());
                    }
                }
            }
        }
        let r = i.üzv_al(o, a, Some(yer))?;
        if let Some(idx) = n.sahələr.borrow().get_index_of(&**a) {
            *keş.borrow_mut() = Some((n.sinif.clone(), idx as u32, None));
        }
        return Ok(r);
    }
    i.üzv_al(o, a, Some(yer))
}

/// `üzv_qoy` + keş (yazıcısı və hesablananı olmayan mövcud sahələr üçün)
fn üzv_qoy_keşli(i: &İcraçı, kod: &Kod, k: u32, o: &D, a: &Ad, d: D, yer: Yer) -> Nəticə<()> {
    if let D::Nümunə(n) = o {
        if n.aktyor.is_some() {
            return i.üzv_qoy(o, a, d, Some(yer));
        }
        let keş = &kod.üzv_keşləri[k as usize];
        if let Some((s, idx, _)) = &*keş.borrow() {
            if Rc::ptr_eq(s, &n.sinif) {
                if let Some((açar, v)) = n.sahələr.borrow_mut().get_index_mut(*idx as usize) {
                    if eyni_ad(açar, a) {
                        *v = d;
                        return Ok(());
                    }
                }
            }
        }
        i.üzv_qoy(o, a, d, Some(yer))?;
        if n.sinif.yazıcı_tap(a).is_none() && n.sinif.hesablanan_tap(a).is_none() {
            if let Some(idx) = n.sahələr.borrow().get_index_of(&**a) {
                *keş.borrow_mut() = Some((n.sinif.clone(), idx as u32, None));
            }
        }
        return Ok(());
    }
    i.üzv_qoy(o, a, d, Some(yer))
}

/// Nümunənin metodu (`nümunə_üzvü` sırası: sahə → hesablanan → metod), keşli
#[inline]
fn metod_tap_keşli(kod: &Kod, k: u32, n: &Rc<Nümunə>, a: &Ad) -> Option<Rc<Funksiya>> {
    // Aktyorun metodu mesajdır — ümumi yol (`üzv_al`)
    if n.aktyor.is_some() || n.sahələr.borrow().contains_key(&**a) {
        return None;
    }
    let keş = &kod.üzv_keşləri[k as usize];
    if let Some((s, _, Some(f))) = &*keş.borrow() {
        if Rc::ptr_eq(s, &n.sinif) {
            return Some(f.clone());
        }
    }
    if n.sinif.hesablanan_tap(a).is_some() {
        return None;
    }
    let f = n.sinif.metod_tap(a)?;
    *keş.borrow_mut() = Some((n.sinif.clone(), 0, Some(f.clone())));
    Some(f)
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
                if let Some(ə) = &mut ç.əl {
                    ə.arqlar.clear();
                }
                ç.mühitlər.truncate(b.mühit as usize);
                ç.iterlər.truncate(b.iter as usize);
                *ç.cəhd(*id) = Some(s);
                return Ok(h);
            }
            BölgəNöv::Tutma(id, fin) => {
                ç.yığın.clear();
                if let Some(ə) = &mut ç.əl {
                    ə.arqlar.clear();
                }
                ç.mühitlər.truncate(b.mühit as usize);
                ç.iterlər.truncate(b.iter as usize);
                *ç.cəhd(*id) = Some(s);
                return Ok(*fin);
            }
            BölgəNöv::XətaBoş(h) => {
                if !matches!(s, Siqnal::Xəta(_)) {
                    continue;
                }
                ç.yığın.clear();
                if let Some(ə) = &mut ç.əl {
                    ə.arqlar.clear();
                }
                ç.mühitlər.truncate(b.mühit as usize);
                ç.iterlər.truncate(b.iter as usize);
                ç.yığın.push(D::Boş);
                return Ok(*h);
            }
        };
        ç.yığın.clear();
        if let Some(ə) = &mut ç.əl {
                    ə.arqlar.clear();
                }
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
        bəzənmiş: None,
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

fn icra(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə, başla: usize) -> Nəticə {
    let əmrlər = &kod.əmrlər[..];
    let mut pc: usize = başla;
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
                    Əmr::YuvaElanK(y) => {
                        let d = dəyər_kopyası(ç.pop());
                        ç.yuvalar[*y as usize] = Some(d);
                    }
                    Əmr::MüqAtla(op, h, doğrusa) => {
                        let n = ç.yığın.len();
                        if let (D::T(x), D::T(y)) = (&ç.yığın[n - 2], &ç.yığın[n - 1]) {
                            let b = müq(*op, *x, *y);
                            unsafe {
                                ç.yığın.set_len(n - 2);
                            }
                            if b == *doğrusa {
                                pc = *h as usize;
                            }
                            continue;
                        }
                        let b = ç.pop();
                        let a = ç.pop();
                        match t!(ikili_ümumi(i, kod, *op, &a, &b, pc - 1), 'x) {
                            D::M(b) => {
                                if b == *doğrusa {
                                    pc = *h as usize;
                                }
                            }
                            d => break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]),
                        }
                    }
                    Əmr::ŞərtT(op, n, h, doğrusa) => {
                        if let Some(D::T(x)) = ç.yığın.last() {
                            let b = müq(*op, *x, *n as i64);
                            ç.yığın.pop();
                            if b == *doğrusa {
                                pc = *h as usize;
                            }
                            continue;
                        }
                        let a = ç.pop();
                        match t!(ikili_ümumi(i, kod, *op, &a, &D::T(*n as i64), pc - 1), 'x) {
                            D::M(b) => {
                                if b == *doğrusa {
                                    pc = *h as usize;
                                }
                            }
                            d => break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]),
                        }
                    }
                    Əmr::DoğrusaAtla(h) => match ç.pop() {
                        D::M(true) => pc = *h as usize,
                        D::M(false) => {}
                        d => break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]),
                    },
                    Əmr::İkiliT(op, n) => {
                        if let Some(D::T(x)) = ç.yığın.last() {
                            if let Some(r) = tam_op(*op, *x, *n as i64) {
                                *ç.yığın.last_mut().unwrap() = r;
                                continue;
                            }
                        }
                        let a = ç.pop();
                        let r = t!(ikili_ümumi(i, kod, *op, &a, &D::T(*n as i64), pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::İkiliQ(op, h) => {
                        let n = ç.yığın.len();
                        if let (D::T(x), D::T(y)) = (&ç.yığın[n - 2], &ç.yığın[n - 1]) {
                            if let Some(r) = tam_op(*op, *x, *y) {
                                unsafe {
                                    ç.yığın.set_len(n - 2);
                                }
                                t!(yuvaya(kod, ç, *h, r), 'x);
                                continue;
                            }
                        }
                        let b = ç.pop();
                        let a = ç.pop();
                        let r = t!(ikili_ümumi(i, kod, *op, &a, &b, pc - 1), 'x);
                        t!(yuvaya(kod, ç, *h, r), 'x);
                    }
                    Əmr::İkiliTQ(op, n, h) => {
                        if let Some(D::T(x)) = ç.yığın.last() {
                            if let Some(r) = tam_op(*op, *x, *n as i64) {
                                ç.yığın.pop();
                                t!(yuvaya(kod, ç, *h, r), 'x);
                                continue;
                            }
                        }
                        let a = ç.pop();
                        let r = t!(ikili_ümumi(i, kod, *op, &a, &D::T(*n as i64), pc - 1), 'x);
                        t!(yuvaya(kod, ç, *h, r), 'x);
                    }
                    Əmr::İkiliYTQ(op, y, n, h) => {
                        let r = match &ç.yuvalar[*y as usize] {
                            Some(D::T(x)) => tam_op(*op, *x, *n as i64),
                            _ => None,
                        };
                        let r = match r {
                            Some(r) => r,
                            None => {
                                let a = t!(yuva_oxu(kod, ç, *y), 'x);
                                t!(ikili_ümumi(i, kod, *op, &a, &D::T(*n as i64), pc - 1), 'x)
                            }
                        };
                        t!(yuvaya(kod, ç, *h, r), 'x);
                    }
                    Əmr::İkiliYYQ(op, y, y2, h) => {
                        let r = match (&ç.yuvalar[*y as usize], &ç.yuvalar[*y2 as usize]) {
                            (Some(D::T(x)), Some(D::T(z))) => tam_op(*op, *x, *z),
                            _ => None,
                        };
                        let r = match r {
                            Some(r) => r,
                            None => {
                                let a = t!(yuva_oxu(kod, ç, *y), 'x);
                                let b = t!(yuva_oxu(kod, ç, *y2), 'x);
                                t!(ikili_ümumi(i, kod, *op, &a, &b, pc - 1), 'x)
                            }
                        };
                        t!(yuvaya(kod, ç, *h, r), 'x);
                    }
                    Əmr::YuvaQoy(y) => {
                        let d = dəyər_kopyası(ç.pop());
                        let yi = *y as usize;
                        if ç.yuvalar[yi].is_some() && (!kod.sabit_var || !ç.sabitdir(yi)) {
                            ç.yuvalar[yi] = Some(d);
                        } else {
                            t!(yuva_yaz(kod, ç, *y, d), 'x);
                        }
                    }
                    Əmr::YuvaElan(y) => {
                        let d = ç.pop();
                        ç.yuvalar[*y as usize] = Some(d);
                    }
                    Əmr::AdAl(a, k) => {
                        let d = t!(ad_al(kod, ç.m(), &kod.adlar[*a as usize], *k), 'x);
                        ç.yığın.push(d);
                    }
                    Əmr::AdQoy(a, k) => {
                        let d = dəyər_kopyası(ç.pop());
                        t!(ad_qoy(kod, ç.m(), &kod.adlar[*a as usize], *k, d), 'x);
                    }
                    Əmr::Kopya => {
                        if let Some(D::Nümunə(n)) = ç.yığın.last() {
                            if n.sinif.quruluş == "struktur" {
                                let d = ç.pop();
                                ç.yığın.push(dəyər_kopyası(d));
                            }
                        }
                    }
                    Əmr::İkili(op) => {
                        let n = ç.yığın.len();
                        if let (D::T(x), D::T(y)) = (&ç.yığın[n - 2], &ç.yığın[n - 1]) {
                            if let Some(r) = tam_op(*op, *x, *y) {
                                // Hər iki operand tam ədəddir — buraxılacaq resurs yoxdur
                                unsafe {
                                    ç.yığın.set_len(n - 2);
                                }
                                ç.yığın.push(r);
                                continue;
                            }
                        }
                        let b = ç.pop();
                        let a = ç.pop();
                        let r = t!(ikili_ümumi(i, kod, *op, &a, &b, pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::İkiliYT(op, y, n) => {
                        if let Some(D::T(x)) = &ç.yuvalar[*y as usize] {
                            if let Some(r) = tam_op(*op, *x, *n as i64) {
                                ç.yığın.push(r);
                                continue;
                            }
                        }
                        let a = t!(yuva_oxu(kod, ç, *y), 'x);
                        let r = t!(ikili_ümumi(i, kod, *op, &a, &D::T(*n as i64), pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::İkiliYY(op, y, y2) => {
                        if let (Some(D::T(x)), Some(D::T(z))) = (&ç.yuvalar[*y as usize], &ç.yuvalar[*y2 as usize]) {
                            if let Some(r) = tam_op(*op, *x, *z) {
                                ç.yığın.push(r);
                                continue;
                            }
                        }
                        let a = t!(yuva_oxu(kod, ç, *y), 'x);
                        let b = t!(yuva_oxu(kod, ç, *y2), 'x);
                        let r = t!(ikili_ümumi(i, kod, *op, &a, &b, pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::ŞərtYT(op, y, n, h, doğrusa) => {
                        if let Some(D::T(x)) = &ç.yuvalar[*y as usize] {
                            if müq(*op, *x, *n as i64) == *doğrusa {
                                pc = *h as usize;
                            }
                            continue;
                        }
                        let a = t!(yuva_oxu(kod, ç, *y), 'x);
                        match t!(ikili_ümumi(i, kod, *op, &a, &D::T(*n as i64), pc - 1), 'x) {
                            D::M(b) => {
                                if b == *doğrusa {
                                    pc = *h as usize;
                                }
                            }
                            d => break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]),
                        }
                    }
                    Əmr::ŞərtYY(op, y, y2, h, doğrusa) => {
                        if let (Some(D::T(x)), Some(D::T(z))) = (&ç.yuvalar[*y as usize], &ç.yuvalar[*y2 as usize]) {
                            if müq(*op, *x, *z) == *doğrusa {
                                pc = *h as usize;
                            }
                            continue;
                        }
                        let a = t!(yuva_oxu(kod, ç, *y), 'x);
                        let b = t!(yuva_oxu(kod, ç, *y2), 'x);
                        match t!(ikili_ümumi(i, kod, *op, &a, &b, pc - 1), 'x) {
                            D::M(b) => {
                                if b == *doğrusa {
                                    pc = *h as usize;
                                }
                            }
                            d => break 'x məntiq_xətası(&d, kod.yerlər[pc - 1]),
                        }
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
                    Əmr::Qaç(h, m, it) => {
                        ç.mühitlər.truncate(*m as usize);
                        ç.iterlər.truncate(*it as usize);
                        ç.yığın.clear();
                        pc = *h as usize;
                    }
                    Əmr::Qaytar => return Ok(ç.pop()),
                    Əmr::Çağır(n, keş) => {
                        let fi = ç.yığın.len() - *n as usize - 1;
                        if let D::Funksiya(fr) = &ç.yığın[fi] {
                            let fr = fr.clone();
                            let özü = fr.özü.clone();
                            if let Some(r) = sürətli_çağır(i, kod, ç, &fr, özü.as_ref(), *n as usize, *keş, kod.yerlər[pc - 1]) {
                                let r = t!(r, 'x);
                                ç.yığın.truncate(fi);
                                ç.yığın.push(r);
                                continue;
                            }
                        }
                        let k = ç.yığın.len() - *n as usize;
                        let args = ç.yığın.split_off(k);
                        let f = ç.pop();
                        let r = t!(i.çağır(&f, args, vec![], Some(kod.yerlər[pc - 1])), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::MetodAl(a, təhlükəsiz, h, k) => {
                        let o = ç.pop();
                        let a = &kod.adlar[*a as usize];
                        if o.boşdur() {
                            if *təhlükəsiz {
                                ç.yığın.push(D::Boş);
                                pc = *h as usize;
                                continue;
                            }
                            break 'x boş_üzv_xətası(a, kod.yerlər[pc - 1]);
                        }
                        if let D::Nümunə(nm) = &o {
                            if let Some(f) = metod_tap_keşli(kod, *k, nm, a) {
                                ç.yığın.push(o);
                                ç.yığın.push(D::Funksiya(f));
                                ç.yığın.push(D::T(2));
                                continue;
                            }
                        }
                        if crate::icraci::metodlar::sürətli_tipdir(&o) && !i.genişlətmə_var(&o, a) && crate::icraci::metodlar::metod_var(&o, a) {
                            ç.yığın.push(o);
                            ç.yığın.push(D::Boş);
                            ç.yığın.push(D::T(1));
                        } else {
                            let f = t!(i.üzv_al(&o, a, Some(kod.yerlər[pc - 1])), 'x);
                            ç.yığın.push(f);
                            // Alıcı çağırış bitənə qədər yaşamalıdır: kitabxana
                            // obyektlərinin zəncirlənən metodları özlərinə zəif
                            // istinad saxlayır (`veb.mətn(..).kod(201)`)
                            ç.yığın.push(o);
                            ç.yığın.push(D::T(0));
                        }
                    }
                    Əmr::MetodÇağır(a, n, keş, tez) => {
                        let fi = ç.yığın.len() - *n as usize - 1;
                        if *tez != 0 {
                            if let D::T(1) = &ç.yığın[fi] {
                                if let Some(r) = tez_metod(*tez, ç, fi, *n as usize) {
                                    let r = t!(yer_qoy(r, Some(kod.yerlər[pc - 1])), 'x);
                                    ç.yığın.truncate(fi - 2);
                                    ç.yığın.push(r);
                                    continue;
                                }
                            }
                        }
                        if let D::T(2) = &ç.yığın[fi] {
                            if let (D::Funksiya(fr), o) = (&ç.yığın[fi - 1], &ç.yığın[fi - 2]) {
                                let (fr, o) = (fr.clone(), o.clone());
                                if let Some(r) = sürətli_çağır(i, kod, ç, &fr, Some(&o), *n as usize, *keş, kod.yerlər[pc - 1]) {
                                    let r = t!(r, 'x);
                                    ç.yığın.truncate(fi - 2);
                                    ç.yığın.push(r);
                                    continue;
                                }
                            }
                        }
                        let k = ç.yığın.len() - *n as usize;
                        let args = ç.yığın.split_off(k);
                        let r = t!(metod_çağır(i, kod, ç, *a, args, vec![], pc - 1), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::ÜzvAl(a, təhlükəsiz, k) => {
                        let o = ç.pop();
                        let a = &kod.adlar[*a as usize];
                        if o.boşdur() {
                            if *təhlükəsiz {
                                ç.yığın.push(D::Boş);
                                continue;
                            }
                            break 'x boş_üzv_xətası(a, kod.yerlər[pc - 1]);
                        }
                        let r = t!(üzv_al_keşli(i, kod, *k, &o, a, kod.yerlər[pc - 1]), 'x);
                        ç.yığın.push(r);
                    }
                    Əmr::İndeksQoy => {
                        let x = ç.pop();
                        let o = ç.pop();
                        let d = ç.pop();
                        if let (D::Siyahı(l), D::T(j)) = (&o, &x) {
                            let mut l = l.borrow_mut();
                            let n = l.len() as i64;
                            let k = if *j < 0 { *j + n } else { *j };
                            if k >= 0 && k < n {
                                l[k as usize] = d;
                                continue;
                            }
                        }
                        t!(i.indeks_qoy(&o, x, d, Some(kod.yerlər[pc - 1])), 'x);
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
                    Əmr::İterGeri(h) => {
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
                            İter::Siyahı(l, k) => {
                                let l = l.borrow();
                                if *k < l.len() {
                                    *k += 1;
                                    Some(l[*k - 1].clone())
                                } else {
                                    None
                                }
                            }
                            it => t!(it.növbəti(i, yer), 'x),
                        };
                        if let Some(x) = x {
                            ç.iterlər.last_mut().unwrap().indeks += 1;
                            ç.yığın.push(x);
                            pc = *h as usize;
                        }
                    }
                    Əmr::SayğacGeri(y, hədd, h) => {
                        let (Some(D::T(c)), Some(D::T(n))) = (&ç.yuvalar[*y as usize], &ç.yuvalar[*hədd as usize]) else {
                            unreachable!()
                        };
                        let (c, n) = (*c + 1, *n);
                        ç.yuvalar[*y as usize] = Some(D::T(c));
                        if c <= n {
                            pc = *h as usize;
                        }
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
                    Əmr::ParamAl(pi, h) => {
                        let f = ç.əl().f.unwrap();
                        let p = &f.parametrlər[*pi as usize];
                        if let Some(d) = ç.əl().args.next() {
                            ç.yığın.push(d);
                            pc = *h as usize;
                        } else if let Some(d) = (!ç.əl().adlı.is_empty()).then(|| adlı_götür(&mut ç.əl().adlı, &p.ad)).flatten() {
                            ç.yığın.push(d);
                            pc = *h as usize;
                        } else if p.standart.is_none() {
                            break 'x xəta_yer(
                                "ArqumentXətası",
                                format!("`{}` üçün `{}` arqumenti verilməyib", f.ad, p.ad),
                                ç.əl().çağırış_yeri,
                                "ALQ-T003",
                            );
                        }
                    }
                    ə => match soyuq(i, kod, ç, ə, pc) {
                        Ok(None) => {}
                        Ok(Some(h)) => pc = h,
                        Err(s) => break 'x s,
                    },
                }
            }
        };
        let _ = cari;
        match siqnal_emal(kod, ç, s, (pc - 1) as u32) {
            Ok(h) => pc = h as usize,
            Err(s) => {
                return match (kod.növ, s) {
                    (KodNövü::Blok, Siqnal::Qaytar(d)) | (KodNövü::Blok, Siqnal::Ver(d)) => Ok(d),
                    (KodNövü::İfadə, Siqnal::Qaytar(d)) => Ok(d),
                    (_, s) => Err(s),
                }
            }
        }
    }
}

fn metod_çağır(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə, a: u32, args: Vec<D>, adlı: Adlı, pc: usize) -> Nəticə {
    let flag = ç.pop();
    let y = ç.pop();
    let x = ç.pop();
    let yer = Some(kod.yerlər[pc]);
    match (flag, y) {
        (D::T(1), _) => yer_qoy(crate::icraci::metodlar::metod_çağır(i, &x, &kod.adlar[a as usize], args, adlı), yer),
        (D::T(2), D::Funksiya(f)) => i.funksiya_çağır(&f.bağla(x), args, adlı, yer),
        _ => i.çağır(&x, args, adlı, yer),
    }
}

/// Nadir əmrlər — `icra`-nın stek çərçivəsini kiçik saxlamaq üçün ayrıca.
/// `Some(pc)` — keçid.
#[inline(never)]
fn soyuq(i: &İcraçı, kod: &Kod, ç: &mut Çərçivə, ə: &Əmr, pc: usize) -> Result<Option<usize>, Siqnal> {
    match ə {
            Əmr::YuvaElanSabit(y) => {
                let d = ç.pop();
                ç.yuvalar[*y as usize] = Some(d);
                ç.sabit_qoy(*y as usize);
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
            Əmr::Genişlət => {
                let d = ç.pop();
                let d = match &d {
                    D::T(_) | D::BT(_) => D::O(d.onluq().unwrap()),
                    _ => d,
                };
                ç.yığın.push(d);
            }
            Əmr::Tək(k) => {
                let d = ç.pop();
                let op = match k {
                    0 => "-",
                    1 => "+",
                    _ => "~",
                };
                let r = (i.tək_dəyər(kod.yerlər[pc - 1], op, d))?;
                ç.yığın.push(r);
            }
            Əmr::BoşDeyilsəAtla(h) => {
                if matches!(ç.yığın.last(), Some(D::Boş) | None) {
                    ç.yığın.pop();
                } else {
                    return Ok(Some(*h as usize));
                }
            }
            Əmr::BoşsaAtla(h) => {
                if matches!(ç.yığın.last(), Some(D::Boş) | None) {
                    return Ok(Some(*h as usize));
                } else {
                    ç.yığın.pop();
                }
            }
            Əmr::SiqnalDayan(e) => return Err(Siqnal::Dayan(e.map(|k| kod.adlar[k as usize].clone()))),
            Əmr::SiqnalDavam(e) => return Err(Siqnal::Davam(e.map(|k| kod.adlar[k as usize].clone()))),
            Əmr::SiqnalQaytar => {
                let d = ç.pop();
                return Err(Siqnal::Qaytar(d));
            }
            Əmr::ArqYeni => ç.əl().arqlar.push((vec![], vec![])),
            Əmr::ArqMövqe => {
                let d = ç.pop();
                ç.əl().arqlar.last_mut().unwrap().0.push(d);
            }
            Əmr::ArqAdlı(a) => {
                let d = ç.pop();
                adlı_qoy(&mut ç.əl().arqlar.last_mut().unwrap().1, kod.adlar[*a as usize].clone(), d);
            }
            Əmr::ArqYay => {
                let d = ç.pop();
                let yer = Some(kod.yerlər[pc - 1]);
                let mut it = (i.iterasiya(&d, yer))?;
                while let Some(e) = (it.növbəti(i, yer))? {
                    ç.əl().arqlar.last_mut().unwrap().0.push(e);
                }
            }
            Əmr::ÇağırArq => {
                let (args, adlı) = ç.əl().arqlar.pop().unwrap();
                let f = ç.pop();
                let r = (i.çağır(&f, args, adlı, Some(kod.yerlər[pc - 1])))?;
                ç.yığın.push(r);
            }
            Əmr::MetodÇağırArq(a) => {
                let (args, adlı) = ç.əl().arqlar.pop().unwrap();
                let r = (metod_çağır(i, kod, ç, *a, args, adlı, pc - 1))?;
                ç.yığın.push(r);
            }
            Əmr::ÜzvAlXam(a) => {
                let o = ç.pop();
                let r = (i.üzv_al(&o, &kod.adlar[*a as usize], Some(kod.yerlər[pc - 1])))?;
                ç.yığın.push(r);
            }
            Əmr::ÜzvQoy(a, k) => {
                let o = ç.pop();
                let d = ç.pop();
                üzv_qoy_keşli(i, kod, *k, &o, &kod.adlar[*a as usize], d, kod.yerlər[pc - 1])?;
            }
            Əmr::İndeksQoy => {
                let x = ç.pop();
                let o = ç.pop();
                let d = ç.pop();
                (i.indeks_qoy(&o, x, d, Some(kod.yerlər[pc - 1])))?;
            }
            Əmr::DilimYoxla => {
                let o = ç.yığın.last().cloned().unwrap_or(D::Boş);
                (dilim_uzunluğu(&o, kod.yerlər[pc - 1]))?;
            }
            Əmr::Dilim(b, s, xaric) => {
                let sd = if *s { Some(ç.pop()) } else { None };
                let bd = if *b { Some(ç.pop()) } else { None };
                let o = ç.pop();
                let yer = kod.yerlər[pc - 1];
                let n = (dilim_uzunluğu(&o, yer))?;
                let r = (dilim_tətbiq(&o, n, bd, sd, *xaric, yer))?;
                ç.yığın.push(r);
            }
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
                let mut it = (i.iterasiya(&d, yer))?;
                while let Some(x) = (it.növbəti(i, yer))? {
                    l.borrow_mut().push(x);
                }
            }
            Əmr::LüğətYeni => ç.yığın.push(D::lüğət(Lüğət::default())),
            Əmr::LüğətQoy => {
                let k = ç.pop();
                let v = ç.pop();
                let k = (yer_qoy(Açar::yeni(k), Some(kod.yerlər[pc - 1])))?;
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
                        return Err(xəta_yer("TipXətası", "`...` lüğətdə lüğət gözləyir", Some(kod.yerlər[pc - 1]), "ALQ-T001"))
                    }
                }
            }
            Əmr::DəstYeni => ç.yığın.push(D::dəst(Dəst::default())),
            Əmr::DəstƏlavə => {
                let d = ç.pop();
                let k = (yer_qoy(Açar::yeni(d), Some(kod.yerlər[pc - 1])))?;
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
                let s = (crate::icraci::format::formatla(i, &d, f))?;
                ç.yığın.push(D::str(s));
            }
            Əmr::Birləşdir(n) => {
                let k = ç.yığın.len() - *n as usize;
                let mut s = String::new();
                for j in k..ç.yığın.len() {
                    if let D::S(x) = &ç.yığın[j] {
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
                    return Err(x);
                }
                let kod_ = |d: D| match d {
                    D::S(x) => D::T(x.chars().next().unwrap() as i64),
                    d => d,
                };
                let r = (yer_qoy(diapazon_yarat(kod_(b), kod_(s), a, *xaric), Some(yer)))?;
                ç.yığın.push(r);
            }
            Əmr::Çevir(h, təhlükəsiz) => {
                let d = ç.pop();
                let r = match i.çevir(&d, &kod.adlar[*h as usize], Some(kod.yerlər[pc - 1])) {
                    Err(Siqnal::Xəta(_)) if *təhlükəsiz => D::Boş,
                    r => (r)?,
                };
                ç.yığın.push(r);
            }
            Əmr::TipYoxla(k) => {
                let d = ç.pop();
                let r = (i.tip_uyğundur(&d, &kod.tiplər[*k as usize], ç.m()))?;
                ç.yığın.push(D::M(r));
            }
            Əmr::Üzvlük => {
                let k = ç.pop();
                let el = ç.pop();
                let r = (i.üzvlük(&el, &k, Some(kod.yerlər[pc - 1])))?;
                ç.yığın.push(D::M(r));
            }
            Əmr::BoşYoxla(inkar) => {
                let d = ç.pop();
                ç.yığın.push(D::M(d.boşdur() != *inkar));
            }
            Əmr::Boru => {
                let f = ç.pop();
                let d = ç.pop();
                let r = (i.çağır(&f, vec![d], vec![], Some(kod.yerlər[pc - 1])))?;
                ç.yığın.push(r);
            }
            Əmr::MəcburiAç => {
                if matches!(ç.yığın.last(), Some(D::Boş) | None) {
                    return Err(xəta_yer(
                        "BoşDəyərXətası",
                        "`!` operatoru `boş` dəyərə tətbiq edildi",
                        Some(kod.yerlər[pc - 1]),
                        "ALQ-R004",
                    ));
                }
            }
            Əmr::Yayma => {
                let d = ç.pop();
                ç.yığın.push(crate::icraci::cagiris::yayma(d)?);
            }
            Əmr::TipDəyəri(k) => {
                let h = (i.tip_dəyəri(&kod.tiplər[*k as usize], ç.m()))?;
                ç.yığın.push(h);
            }
            Əmr::Yeni(q) => {
                let (a, adlı) = ç.əl().arqlar.pop().unwrap();
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
                let r = (r)?;
                ç.yığın.push(r);
            }
            Əmr::Gözlə => {
                let d = ç.pop();
                let r = (i.gözlə(d, Some(kod.yerlər[pc - 1])))?;
                ç.yığın.push(r);
            }
            Əmr::ÜstQur => {
                let s = ç.pop();
                let özü = ç.pop();
                match s {
                    D::Sinif(s) => ç.yığın.push(D::Üst(Rc::new((özü, s)))),
                    _ => return Err(xəta("TipXətası", "baza sinif yoxdur", "ALQ-T012")),
                }
            }
            Əmr::Lambda(k) => {
                let f = funksiya_yarat(kod, ç, *k);
                ç.yığın.push(f);
            }
            Əmr::Xəta(k) => {
                let (tip, mesaj, kod_) = &kod.xətalar[*k as usize];
                return Err(xəta_yer(tip, mesaj.clone(), Some(kod.yerlər[pc - 1]), kod_));
            }
            Əmr::AtXəta => {
                let d = ç.pop();
                let yer = Some(kod.yerlər[pc - 1]);
                if let D::Nümunə(n) = &d {
                    let mesaj = match n.sahə("mesaj") {
                        Some(x) => (mətnə(i, &x))?,
                        None => String::new(),
                    };
                    return Err(Siqnal::Xəta(Box::new(AlqorXəta {
                        tip: n.sinif.ad.clone(),
                        mesaj,
                        yer,
                        kod: String::new(),
                        dəyər: Some(d.clone()),
                    })));
                }
                let mesaj = (mətnə(i, &d))?;
                return Err(Siqnal::Xəta(Box::new(AlqorXəta { tip: ad("Xəta"), mesaj, yer, kod: String::new(), dəyər: Some(d) })));
            }
            Əmr::İddia(var) => {
                let mesaj = if *var {
                    let d = ç.pop();
                    (mətnə(i, &d))?
                } else {
                    "iddia pozuldu".into()
                };
                return Err(xəta_yer("İddiaXətası", mesaj, Some(kod.yerlər[pc - 1]), "ALQ-R007"));
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
                let r = (r)?;
                ç.yığın.push(r);
            }
            Əmr::Ötür(k) => {
                let m = ç.m().clone();
                (i.cümlə(&kod.cümlələr[*k as usize], &m))?;
            }
            Əmr::Ötürİfadə(k) => {
                let m = ç.m().clone();
                let r = (i.ifadə(&kod.ifadələr[*k as usize], &m))?;
                ç.yığın.push(r);
            }
            Əmr::İterAç => {
                let d = ç.pop();
                let lüğət = if let D::Lüğət(l) = &d { Some(l.clone()) } else { None };
                let it = (i.iterasiya(&d, Some(kod.yerlər[pc - 1])))?;
                ç.iterlər.push(VmIter { it, lüğət, indeks: 0 });
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
                    None => return Ok(Some(*h as usize)),
                    Some(l) => {
                        let el = ç.pop();
                        let v = l.borrow().get(&Açar(el.clone())).cloned();
                        match v {
                            Some(v) => ç.yığın.push(D::kortej(vec![el, v])),
                            None => {
                                let s = (mətnə(i, &el))?;
                                return Err(xəta_yer(
                                    "AçarXətası",
                                    format!("lüğətdə `{}` açarı yoxdur", s),
                                    Some(kod.yerlər[pc - 1]),
                                    "ALQ-R003",
                                ));
                            }
                        }
                    }
                }
            }
            Əmr::DiapazonDeyilsəAtla(h) => {
                if !matches!(ç.yığın.last(), Some(D::Diapazon(_))) {
                    return Ok(Some(*h as usize));
                }
            }
            Əmr::DiapazonAddım => {
                let a = ç.pop();
                let r = ç.pop();
                let D::Diapazon(r) = r else { unreachable!() };
                let d = (diapazon_yarat(D::T(r.başlanğıc), D::T(r.son), Some(a), r.xaric))?;
                ç.yığın.push(d);
            }
            Əmr::TəkrarSay => {
                let s = ç.pop();
                let n = match &s {
                    D::T(n) => *n,
                    D::BT(_) => i64::MAX,
                    _ => {
                        return Err(xəta_yer(
                            "TipXətası",
                            format!("`təkrarla` tam ədəd gözləyir, `{}` gəlib", tip_adı(&s)),
                            Some(kod.yerlər[pc - 1]),
                            "ALQ-T001",
                        ))
                    }
                };
                ç.yığın.push(D::T(n));
            }
            Əmr::Dağıt(n, q) => {
                let d = ç.pop();
                let yer = Some(kod.yerlər[pc - 1]);
                let el = match i.iterasiya(&d, yer).and_then(|it| it.hamısı(i, yer)) {
                    Ok(v) => v,
                    Err(Siqnal::Xəta(_)) => {
                        return Err(xəta_yer("TipXətası", format!("`{}` dağıtıla bilməz", tip_adı(&d)), yer, "ALQ-T001"))
                    }
                    Err(x) => return Err(x),
                };
                let n = *n as usize;
                if *q == u32::MAX {
                    if el.len() != n {
                        return Err(xəta_yer(
                            "ArqumentXətası",
                            format!("{} ad gözlənilirdi, {} dəyər var", n, el.len()),
                            yer,
                            "ALQ-T001",
                        ));
                    }
                    ç.yığın.extend(el.into_iter().rev());
                } else {
                    let q = *q as usize;
                    let sonra = n - q - 1;
                    if el.len() < q + sonra {
                        return Err(xəta_yer("ArqumentXətası", "dağıtma üçün element çatmır", yer, "ALQ-T001"));
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
                    let it = (i.iterasiya(&d, yer))?;
                    (it.hamısı(i, yer))?
                } else {
                    let k = ç.yığın.len() - *nv as usize;
                    ç.yığın.split_off(k)
                };
                if v.len() != *nt as usize {
                    return Err(xəta_yer("ArqumentXətası", "mənimsətmədə sayllar uyğun gəlmir", yer, "ALQ-T001"));
                }
                ç.yığın.extend(v.into_iter().rev());
            }
            Əmr::StandartDəyər(k) => {
                let t = if *k == u32::MAX { None } else { Some(&kod.tiplər[*k as usize]) };
                ç.yığın.push(standart_dəyər(t));
            }
            Əmr::CəhdTəmizlə(id) => *ç.cəhd(*id) = None,
            Əmr::TutmaYoxla(id, ti, h) => {
                let uyğun = match &*ç.cəhd(*id) {
                    Some(Siqnal::Xəta(x)) => tutma_uyğundur(&kod.tutmalar[*ti as usize], x),
                    _ => false,
                };
                if !uyğun {
                    return Ok(Some(*h as usize));
                }
            }
            Əmr::XətaObyekti(id) => {
                let d = match &*ç.cəhd(*id) {
                    Some(Siqnal::Xəta(x)) => xəta_obyekti(x),
                    _ => D::Boş,
                };
                ç.yığın.push(d);
            }
            Əmr::NəhayətSon(id) => {
                if let Some(s) = ç.cəhd(*id).take() {
                    return Err(s);
                }
            }
            Əmr::QurmaƏlavə(y) => {
                let d = ç.pop();
                if let Some(D::Siyahı(l)) = &ç.yuvalar[*y as usize] {
                    l.borrow_mut().push(d);
                }
            }
            Əmr::QurmaLüğət(y) => {
                let v = ç.pop();
                let k = ç.pop();
                let k = (yer_qoy(Açar::yeni(k), Some(kod.yerlər[pc - 1])))?;
                if let Some(D::Lüğət(l)) = &ç.yuvalar[*y as usize] {
                    l.borrow_mut().insert(k, v);
                }
            }
            Əmr::AçarYoxla => {
                let k = ç.yığın.last().cloned().unwrap_or(D::Boş);
                (yer_qoy(Açar::yeni(k), Some(kod.yerlər[pc - 1])))?;
            }
            Əmr::QurmaSon(y, növ) => {
                let d = ç.yuvalar[*y as usize].take().unwrap_or(D::Boş);
                let r = match (növ, &d) {
                    (1, D::Siyahı(l)) => {
                        let v = std::mem::take(&mut *l.borrow_mut());
                        let mut s = Dəst::default();
                        for x in v {
                            s.insert((yer_qoy(Açar::yeni(x), Some(kod.yerlər[pc - 1])))?);
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
            Əmr::ParamAdlı(pi, h) => {
                let f = ç.əl().f.unwrap();
                let p = &f.parametrlər[*pi as usize];
                if let Some(d) = adlı_götür(&mut ç.əl().adlı, &p.ad) {
                    ç.yığın.push(d);
                    return Ok(Some(*h as usize));
                } else if p.standart.is_none() {
                    return Err(xəta_yer(
                        "ArqumentXətası",
                        format!("`{}` üçün `{}` adlı arqumenti məcburidir", f.ad, p.ad),
                        ç.əl().çağırış_yeri,
                        "ALQ-T003",
                    ));
                }
            }
            Əmr::ParamVariadic => {
                let v: Vec<D> = std::mem::take(&mut ç.əl().args).collect();
                ç.yığın.push(D::siyahı(v));
            }
            Əmr::ParamAdlıVariadic => {
                let mut l = Lüğət::default();
                for (k, d) in ç.əl().adlı.drain(..) {
                    l.insert(Açar(D::S(k)), d);
                }
                ç.yığın.push(D::lüğət(l));
            }
            Əmr::ParamSon => {
                if !ç.əl().adlı.is_empty() {
                    let f = ç.əl().f.unwrap();
                    let mut a: Vec<String> = ç.əl().adlı.iter().map(|(k, _)| k.to_string()).collect();
                    a.sort();
                    return Err(xəta_yer(
                        "ArqumentXətası",
                        format!("`{}` naməlum adlı arqument: {}", f.ad, a.join(", ")),
                        ç.əl().çağırış_yeri,
                        "ALQ-T004",
                    ));
                }
            }
            Əmr::XassəQoy(a) => {
                let d = ç.pop();
                if let Some(D::Nümunə(n)) = &ç.əl().f.unwrap().özü {
                    n.sahələr.borrow_mut().insert(kod.adlar[*a as usize].clone(), d);
                }
            }
        Əmr::İkiliDigər(k) => {
            let b = ç.pop();
            let a = ç.pop();
            let r = i.ikili_hesabla(&kod.adlar[*k as usize], &a, &b, Some(kod.yerlər[pc - 1]))?;
            ç.yığın.push(r);
        }
        _ => unreachable!(),
    }
    Ok(None)
}
