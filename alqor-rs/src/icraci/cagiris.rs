//! Çağırışlar, funksiyalar, generatorlar, iterasiya, tiplər (icraci.py davamı).

use super::deyerler::*;
use super::icraci::{İcraçı, İter, STEK_HƏDDİ};
#[cfg(not(target_arch = "wasm32"))]
use super::icraci::KORUTİN_STEKİ;
use super::muhit::Mühit;
use crate::aac::{self, Cümlə, Tip, İfadə};
use crate::xeta::Yer;
use std::rc::Rc;

// ═══════════════════════════════════════════════════════════════════════
//  Sərbəst köməkçilər
// ═══════════════════════════════════════════════════════════════════════

/// Dilin və kitabxanaların öz annotasiyaları — bəzəyici kimi axtarılmır
pub const DAXİLİ_ANNOTASİYALAR: &[&str] = &[
    "sınaq", "sınaqQrupu", "sınaqVerilənlər", "sınaqdan_keçməyib",
    "əvvəl", "sonra", "atla", "yaddaşla", "saf", "daxili", "xaric",
    "quyruqRekursiya", "köhnəlmiş", "xarici", "tənbəl", "statik",
    "yalnızHədəf", "əgərHədəf", "əgərKompilyasiya",
    "cədvəl", "sütun", "açar", "əlaqə", "keçici", "API",
    "json", "jsonAtla", "jsonStandart",
];

fn istifadəçi_annotasiyası(a: &[aac::Annotasiya]) -> bool {
    a.iter().any(|a| !DAXİLİ_ANNOTASİYALAR.contains(&a.ad.as_str()))
}

/// Elanın bəzəyici ola biləcək annotasiyası varmı (VM bunları ağac
/// icraçısına ötürür)
pub fn bəzəyici_ola_bilər(c: &Cümlə) -> bool {
    match c {
        Cümlə::Funksiya(f) | Cümlə::Metod(f) => istifadəçi_annotasiyası(&f.bəzəyicilər),
        Cümlə::Sinif(s) => {
            istifadəçi_annotasiyası(&s.bəzəyicilər)
                || s.üzvlər.iter().any(bəzəyici_ola_bilər)
        }
        _ => false,
    }
}

/// `ifadə?` (§ 7.5): `Uğur(d)` → `d`; `Uğursuz(...)` və `boş` funksiyadan
/// dərhal qaytarılır
pub fn yayma(d: D) -> Nəticə {
    match &d {
        D::Boş => Err(Siqnal::Qaytar(D::Boş)),
        D::SD(v) if &*v.ad == "Uğursuz" || &*v.ad == "Xəta" => Err(Siqnal::Qaytar(d)),
        D::SD(v) if &*v.ad == "Uğur" && !v.sahələr.is_empty() => Ok(v.sahələr.get_index(0).unwrap().1.clone()),
        D::Nümunə(n) if &*n.sinif.ad == "Xəta" => Err(Siqnal::Qaytar(d)),
        _ => Ok(d),
    }
}

/// `f(**lüğət)` — lüğətin cütləri adlı arqument olur
pub fn adlı_yay(d: &D, adlı: &mut Adlı, yer: Yer) -> Nəticə<()> {
    let xəta = || {
        Err(xəta_yer(
            "TipXətası",
            format!("`**` yalnız mətn açarlı lüğətə tətbiq olunur, `{}` verilib", tip_adı(d)),
            Some(yer),
            "ALQ-T081",
        ))
    };
    let D::Lüğət(l) = d else { return xəta() };
    let l = l.borrow();
    if !l.iter().all(|(k, _)| matches!(k.0, D::S(_))) {
        return xəta();
    }
    for (k, v) in l.iter() {
        if let D::S(s) = &k.0 {
            adlı_qoy(adlı, ad(s), v.clone());
        }
    }
    Ok(())
}

pub fn elandır(c: &Cümlə) -> bool {
    matches!(
        c,
        Cümlə::Funksiya(_)
            | Cümlə::Sinif(_)
            | Cümlə::İnterfeys { .. }
            | Cümlə::Sadalama { .. }
            | Cümlə::Qarışıq { .. }
            | Cümlə::TipAliası { .. }
            | Cümlə::İdxal { .. }
    )
}

/// Blok üçün yeni əhatə — yalnız blok ad elan edirsə yaradılır. Ad elan
/// etməyən blokda boş alt əhatə ilə üst əhatə arasında fərq yoxdur.
#[inline]
pub fn əhatə(g: &[Cümlə], m: &Mühit) -> Mühit {
    let lazım = g.iter().any(|c| {
        matches!(
            c,
            Cümlə::DəyişənElanı { .. }
                | Cümlə::Funksiya(_)
                | Cümlə::Sinif(_)
                | Cümlə::İnterfeys { .. }
                | Cümlə::Sadalama { .. }
                | Cümlə::Qarışıq { .. }
                | Cümlə::TipAliası { .. }
                | Cümlə::Modul { .. }
                | Cümlə::İdxal { .. }
                | Cümlə::Global(..)
                | Cümlə::Yoxdursa { .. }
        )
    });
    if lazım {
        m.alt()
    } else {
        m.clone()
    }
}

pub fn standart_dəyər(t: Option<&Tip>) -> D {
    match t {
        Some(Tip::Ad { yol, ixtiyari: false, .. }) => match yol.join(".").as_str() {
            "tam" => D::T(0),
            "onluq" => D::O(0.0),
            "mətn" => D::s(""),
            "məntiq" => D::M(false),
            "siyahı" => D::siyahı(vec![]),
            "lüğət" => D::lüğət(Lüğət::default()),
            "dəst" => D::dəst(Dəst::default()),
            "bayt" => D::Bayt(Rc::new(vec![])),
            _ => D::Boş,
        },
        _ => D::Boş,
    }
}

/// Strukturlar dəyər tipidir — kopyalanır.
#[inline]
pub fn dəyər_kopyası(d: D) -> D {
    if let D::Nümunə(n) = &d {
        if n.sinif.quruluş == "struktur" {
            return D::Nümunə(n.klonla());
        }
    }
    d
}

/// `tam` → `onluq` implisit genişlənməsi.
#[inline]
pub fn genişlət(d: D, t: Option<&Tip>) -> D {
    if let Some(Tip::Ad { yol, .. }) = t {
        if yol.len() == 1 && yol[0] == "onluq" {
            if let Some(f) = match &d {
                D::T(_) | D::BT(_) => d.onluq(),
                _ => None,
            } {
                return D::O(f);
            }
        }
    }
    d
}

pub fn diapazon_yarat(b: D, s: D, a: Option<D>, xaric: bool) -> Nəticə {
    let (Some(b), Some(s)) = (b.i64(), s.i64()) else {
        return Err(xəta("DaşmaXətası", "diapazon hədləri çox böyükdür", "ALQ-R002"));
    };
    let a = match a {
        None | Some(D::Boş) => {
            if s >= b {
                1
            } else {
                -1
            }
        }
        Some(D::T(a)) => a,
        Some(D::M(x)) => x as i64,
        Some(x) => {
            return Err(xəta(
                "TipXətası",
                format!("diapazon addımı tam ədəd olmalıdır, `{}` gəlib", tip_adı(&x)),
                "ALQ-T001",
            ))
        }
    };
    if a == 0 {
        return Err(xəta("ArqumentXətası", "diapazon addımı 0 ola bilməz", "ALQ-R002"));
    }
    Ok(D::Diapazon(Rc::new(Diapazon { başlanğıc: b, son: s, addım: a, xaric })))
}

pub fn tutma_uyğundur(t: &aac::Tutma, x: &AlqorXəta) -> bool {
    if t.tiplər.is_empty() {
        return true;
    }
    t.tiplər.iter().any(|tp| xəta_uyğundur(&x.tip, &tp.tam_ad()))
}

pub fn xəta_obyekti(x: &AlqorXəta) -> D {
    if let Some(d) = &x.dəyər {
        return d.clone();
    }
    let s = Rc::new(Sinif::yeni(&x.tip, None, "sinif"));
    let n = Nümunə::yeni(s);
    {
        let mut f = n.sahələr.borrow_mut();
        f.insert(ad("mesaj"), D::str(x.mesaj.clone()));
        f.insert(ad("kod"), if x.kod.is_empty() { D::Boş } else { D::str(x.kod.clone()) });
        f.insert(ad("tip"), D::S(x.tip.clone()));
    }
    D::Nümunə(Rc::new(n))
}

pub fn indeks_tam(i: &D, yer: Option<Yer>) -> Nəticə<i64> {
    match i {
        D::T(x) => Ok(*x),
        D::M(b) => Ok(*b as i64),
        D::BT(_) => Ok(i64::MAX),
        _ => Err(xəta_yer(
            "TipXətası",
            format!("indeks tam ədəd olmalıdır, `{}` gəlib", tip_adı(i)),
            yer,
            "ALQ-T009",
        )),
    }
}

pub fn indeks_həll(j: i64, n: usize) -> Option<usize> {
    let n = n as i64;
    let k = if j < 0 { j + n } else { j };
    if k >= 0 && k < n {
        Some(k as usize)
    } else {
        None
    }
}

pub fn indeks_xətası(i: &D, n: usize, yer: Option<Yer>) -> Siqnal {
    xəta_yer(
        "İndeksXətası",
        format!("indeks {} diapazondan kənardır (uzunluq {})", py_str_sadə(i), n),
        yer,
        "ALQ-R002",
    )
}

/// Python `str()` ədədlər üçün (f-string-də `{indeks}`)
pub fn py_str_sadə(d: &D) -> String {
    match d {
        D::M(true) => "True".into(),
        D::M(false) => "False".into(),
        D::Boş => "None".into(),
        D::S(s) => s.to_string(),
        _ => py_repr(d),
    }
}

fn yaddaş_açarı(d: &D) -> YaddaşAçarı {
    match d {
        D::Boş => YaddaşAçarı::Boş,
        D::M(b) => YaddaşAçarı::T(*b as i64),
        D::T(i) => YaddaşAçarı::T(*i),
        D::BT(b) => YaddaşAçarı::BT((**b).clone()),
        D::O(f) => {
            if f.fract() == 0.0 && f.abs() < 9e18 {
                YaddaşAçarı::T(*f as i64)
            } else {
                YaddaşAçarı::O(f.to_bits())
            }
        }
        D::S(s) => YaddaşAçarı::S(s.clone()),
        x => YaddaşAçarı::İd(ptr_id(x)),
    }
}

pub fn adlı_qoy(adlı: &mut Adlı, a: Ad, d: D) {
    if let Some(x) = adlı.iter_mut().find(|(k, _)| **k == *a) {
        x.1 = d;
    } else {
        adlı.push((a, d));
    }
}

pub fn adlı_götür(adlı: &mut Adlı, a: &str) -> Option<D> {
    let i = adlı.iter().position(|(k, _)| &**k == a)?;
    Some(adlı.remove(i).1)
}

// ═══════════════════════════════════════════════════════════════════════
//  Çağırışlar
// ═══════════════════════════════════════════════════════════════════════

impl İcraçı {
    // ── Sorğu (§ 4.13) ─────────────────────────────────────────────────

    /// Bəndlər yazıldığı sıra ilə işləyir. Hər sətir — öz mühiti və «cari
    /// element» (son `hər`-in elementi, `qrupla`-dan sonra `(açar, qrup)`).
    pub fn e_sorğu(&self, bəndlər: &[aac::SorğuBəndi], m: &Mühit) -> Nəticə {
        let mut sətirlər: Vec<(Mühit, D)> = vec![(m.clone(), D::Boş)];
        let mut nəticə: Option<Vec<D>> = None;
        for b in bəndlər {
            let yer = Some(b.yer);
            let ifadə = || b.ifadə.as_ref().expect("sorğu bəndinin ifadəsi");
            match b.növ.as_str() {
                "hər" => {
                    let mut yeni = vec![];
                    for (mm, _) in &sətirlər {
                        let mənbə = self.ifadə(ifadə(), mm)?;
                        let mut it = self.iterasiya(&mənbə, yer)?;
                        while let Some(el) = it.növbəti(self, yer)? {
                            let alt = mm.alt();
                            self.bağla(b.bağlama.as_ref().unwrap(), el.clone(), &alt, true, false)?;
                            yeni.push((alt, el));
                        }
                    }
                    sətirlər = yeni;
                }
                "harada" => {
                    let mut yeni = vec![];
                    for (mm, el) in sətirlər {
                        if self.məntiq(ifadə(), &mm)? {
                            yeni.push((mm, el));
                        }
                    }
                    sətirlər = yeni;
                }
                "dəyişən" => {
                    let mut yeni = vec![];
                    for (mm, el) in sətirlər {
                        let alt = mm.alt();
                        let d = self.ifadə(ifadə(), &mm)?;
                        self.bağla(b.bağlama.as_ref().unwrap(), d, &alt, true, false)?;
                        yeni.push((alt, el));
                    }
                    sətirlər = yeni;
                }
                "sırala" => {
                    let mut açarlı = Vec::with_capacity(sətirlər.len());
                    for s in sətirlər {
                        let mut k = Vec::with_capacity(b.açarlar.len());
                        for (e, _) in &b.açarlar {
                            k.push(self.ifadə(e, &s.0)?);
                        }
                        açarlı.push((k, s));
                    }
                    açarlı.sort_by(|x, y| {
                        for ((ka, kb), (_, az)) in x.0.iter().zip(y.0.iter()).zip(b.açarlar.iter()) {
                            let r = super::eded::sıra_müq(ka, kb);
                            if r != std::cmp::Ordering::Equal {
                                return if *az { r.reverse() } else { r };
                            }
                        }
                        std::cmp::Ordering::Equal
                    });
                    sətirlər = açarlı.into_iter().map(|x| x.1).collect();
                }
                "qrupla" => {
                    let mut qruplar: indexmap::IndexMap<Açar, Vec<D>, Fx> = Default::default();
                    for (mm, el) in &sətirlər {
                        let k = yer_qoy(Açar::yeni(self.ifadə(ifadə(), mm)?), yer)?;
                        qruplar.entry(k).or_default().push(el.clone());
                    }
                    sətirlər = vec![];
                    for (k, q) in qruplar {
                        let alt = m.alt();
                        let cüt = D::kortej(vec![k.0, D::siyahı(q)]);
                        self.bağla(b.bağlama.as_ref().unwrap(), cüt.clone(), &alt, true, false)?;
                        sətirlər.push((alt, cüt));
                    }
                }
                "seç" => {
                    let mut v = Vec::with_capacity(sətirlər.len());
                    for (mm, _) in &sətirlər {
                        v.push(self.ifadə(ifadə(), mm)?);
                    }
                    if b.fərqli {
                        let mut görülən = Dəst::default();
                        let mut t = vec![];
                        for x in v {
                            if görülən.insert(yer_qoy(Açar::yeni(x.clone()), yer)?) {
                                t.push(x);
                            }
                        }
                        v = t;
                    }
                    nəticə = Some(v);
                }
                n => {
                    // `ilk` / `atla`
                    let say = self.ifadə(ifadə(), m)?;
                    let say = match say {
                        D::T(k) if k >= 0 => k as usize,
                        _ => {
                            return Err(xəta_yer(
                                "TipXətası",
                                format!("`{}` mənfi olmayan tam ədəd gözləyir, `{}` gəlib", n, mətnə(self, &say)?),
                                yer,
                                "ALQ-T083",
                            ))
                        }
                    };
                    let kəs = |uz: usize| -> (usize, usize) {
                        if n == "ilk" { (0, say.min(uz)) } else { (say.min(uz), uz) }
                    };
                    if let Some(v) = &mut nəticə {
                        let (a, z) = kəs(v.len());
                        *v = v[a..z].to_vec();
                    } else {
                        let (a, z) = kəs(sətirlər.len());
                        sətirlər = sətirlər.drain(a..z).collect();
                    }
                }
            }
        }
        Ok(D::siyahı(match nəticə {
            Some(v) => v,
            None => sətirlər.into_iter().map(|x| x.1).collect(),
        }))
    }

    // ── Bəzəyicilər (§ 5.11) ─────────────────────────────────────────

    /// Elanın istifadəçi bəzəyiciləri (mənbədəki sıra ilə). Mühitdə
    /// tapılmayan adlar və daxili annotasiyalar məlumat olaraq qalır.
    pub fn bəzəyicilər(&self, annot: &[aac::Annotasiya], m: &Mühit) -> Nəticə<Vec<D>> {
        let mut v = vec![];
        for a in annot {
            if DAXİLİ_ANNOTASİYALAR.contains(&a.ad.as_str()) {
                continue;
            }
            let Ok(d) = m.al(&a.ad) else { continue };
            if a.arqumentlər.is_empty() {
                v.push(d);
            } else {
                let yer = a.arqumentlər[0].dəyər.yer();
                let (arq, adlı) = self.arqumentlər(&a.arqumentlər, m, yer)?;
                v.push(self.çağır(&d, arq, adlı, Some(yer))?);
            }
        }
        Ok(v)
    }

    /// `@a @b f` → `a(b(f))`
    pub fn bəzəyiciləri_tətbiq_et(&self, mut d: D, bəzəyicilər: &[D]) -> Nəticə {
        for b in bəzəyicilər.iter().rev() {
            d = self.çağır(b, vec![d], vec![], None)?;
        }
        Ok(d)
    }

    pub fn bəzə_ad(&self, ad_: &str, annot: &[aac::Annotasiya], m: &Mühit) -> Nəticə<()> {
        let b = self.bəzəyicilər(annot, m)?;
        if b.is_empty() {
            return Ok(());
        }
        let d = m.al(ad_)?;
        let d = self.bəzəyiciləri_tətbiq_et(d, &b)?;
        m.təyin(ad_, d)
    }

    /// Funksiya və sinif elanına bəzəyiciləri tətbiq edir.
    pub fn bəzə(&self, c: &Cümlə, m: &Mühit) -> Nəticə<()> {
        match c {
            Cümlə::Funksiya(f) if !f.bəzəyicilər.is_empty() => self.bəzə_ad(&f.ad, &f.bəzəyicilər, m),
            Cümlə::Sinif(s) if !s.bəzəyicilər.is_empty() && s.quruluş != "obyekt" => {
                self.bəzə_ad(&s.ad, &s.bəzəyicilər, m)
            }
            _ => Ok(()),
        }
    }

    pub fn arqumentlər(&self, arq: &[aac::Arqument], m: &Mühit, yer: Yer) -> Nəticə<(Vec<D>, Adlı)> {
        let mut a = Vec::with_capacity(arq.len());
        let mut adlı: Adlı = vec![];
        for x in arq {
            let d = self.ifadə(&x.dəyər, m)?;
            if x.yayma {
                let mut it = self.iterasiya(&d, Some(yer))?;
                while let Some(e) = it.növbəti(self, Some(yer))? {
                    a.push(e);
                }
            } else if x.adlı_yayma {
                adlı_yay(&d, &mut adlı, yer)?;
            } else if let Some(n) = &x.ad {
                adlı_qoy(&mut adlı, ad(n), d);
            } else {
                a.push(d);
            }
        }
        Ok((a, adlı))
    }

    pub fn e_çağırış(&self, yer: Yer, f: &aac::E, arq: &[aac::Arqument], m: &Mühit) -> Nəticə {
        if let İfadə::Üzv(üyer, obyekt, a, təhlükəsiz) = &**f {
            if *təhlükəsiz {
                if self.ifadə(obyekt, m)?.boşdur() {
                    return Ok(D::Boş);
                }
            }
            let o = self.ifadə(obyekt, m)?;
            if o.boşdur() {
                if *təhlükəsiz {
                    return Ok(D::Boş);
                }
                return Err(xəta_yer(
                    "BoşDəyərXətası",
                    format!("`boş` dəyərdə `{}` üzvü yoxdur", a),
                    Some(*üyer),
                    "ALQ-R004",
                ));
            }
            // Sürətli yol: daxili tipin metodu
            if super::metodlar::sürətli_tipdir(&o) && !self.genişlətmə_var(&o, a) && super::metodlar::metod_var(&o, a) {
                let (args, adlı) = self.arqumentlər(arq, m, yer)?;
                return yer_qoy(super::metodlar::metod_çağır(self, &o, a, args, adlı), Some(yer));
            }
            let func = self.üzv_al(&o, a, Some(*üyer))?;
            let (args, adlı) = self.arqumentlər(arq, m, yer)?;
            return self.çağır(&func, args, adlı, Some(yer));
        }
        let func = self.ifadə(f, m)?;
        let (args, adlı) = self.arqumentlər(arq, m, yer)?;
        self.çağır(&func, args, adlı, Some(yer))
    }

    pub fn genişlətmə_var(&self, o: &D, a: &str) -> bool {
        let g = self.genişlətmələr.borrow();
        if g.is_empty() {
            return false;
        }
        g.get(&tip_kökü(o)).map(|x| x.contains_key(a)).unwrap_or(false)
    }

    pub fn çağır(&self, f: &D, args: Vec<D>, adlı: Adlı, yer: Option<Yer>) -> Nəticə {
        match f {
            D::Funksiya(f) => self.funksiya_çağır(f, args, adlı, yer),
            D::Daxili(d) => {
                let n = args.len();
                if n < d.min || d.maks.map(|x| n > x).unwrap_or(false) {
                    let g = if d.maks == Some(d.min) {
                        d.min.to_string()
                    } else {
                        format!("{}–{}", d.min, d.maks.map(|x| x.to_string()).unwrap_or("∞".into()))
                    };
                    return Err(xəta_yer(
                        "ArqumentXətası",
                        format!("`{}` {} arqument gözləyir, {} verilib", d.ad, g, n),
                        yer,
                        "ALQ-T003",
                    ));
                }
                yer_qoy((d.f)(self, args, adlı), yer)
            }
            D::Metod(b) => match &b.f {
                MetodF::Daxili => yer_qoy(super::metodlar::metod_çağır(self, &b.obyekt, &b.ad, args, adlı), yer),
                MetodF::Genişlətmə(g) => {
                    yer_qoy(self.funksiya_çağır(&g.bağla(b.obyekt.clone()), args, vec![], None), yer)
                }
            },
            D::Sinif(s) => self.nümunə_yarat(s, None, args, adlı, yer),
            D::Üst(u) => {
                let Some(baza) = &u.1.baza else {
                    return Err(xəta_yer(
                        "TipXətası",
                        "`üst(...)` baza sinfi olmayan sinifdə işlənib",
                        yer,
                        "ALQ-P012",
                    ));
                };
                match baza.qurucu_tap("") {
                    None => Ok(D::Boş),
                    Some(q) => self.funksiya_çağır(&q.bağla(u.0.clone()), args, adlı, yer),
                }
            }
            D::QurucuIst(q) => self.nümunə_yarat(&q.0, Some(&q.1), args, adlı, yer),
            D::Variant(v) => {
                let mut s = Sahələr::default();
                for (i, p) in v.parametrlər.iter().enumerate() {
                    let d = if i < args.len() {
                        args[i].clone()
                    } else {
                        adlı.iter().find(|(k, _)| k == p).map(|x| x.1.clone()).unwrap_or(D::Boş)
                    };
                    s.insert(p.clone(), d);
                }
                Ok(D::SD(Rc::new(SadalamaDəyəri {
                    sadalama: v.sadalama.clone(),
                    ad: v.ad.clone(),
                    sıra_nömrəsi: v.sıra,
                    dəyər: D::Boş,
                    sahələr: s,
                })))
            }
            D::Modul(md) if md.çağırışçı.is_some() => self.çağır(md.çağırışçı.as_ref().unwrap(), args, adlı, yer),
            D::XətaSinfi(a) => {
                let s = Rc::new(Sinif::yeni(a, None, "sinif"));
                let n = Nümunə::yeni(s);
                {
                    let mut f = n.sahələr.borrow_mut();
                    let mesaj = match args.first() {
                        Some(x) => mətnə(self, x)?,
                        None => String::new(),
                    };
                    f.insert(ad("mesaj"), D::str(mesaj));
                    f.insert(ad("tip"), D::S(a.clone()));
                    let al = |k: &str| adlı.iter().find(|(x, _)| &**x == k).map(|x| x.1.clone()).unwrap_or(D::Boş);
                    f.insert(ad("kod"), al("kod"));
                    f.insert(ad("səbəb"), al("səbəb"));
                    for (k, v) in &adlı {
                        if !f.contains_key(k) {
                            f.insert(k.clone(), v.clone());
                        }
                    }
                }
                Ok(D::Nümunə(Rc::new(n)))
            }
            D::Nümunə(n) => match n.sinif.metod_tap("çağır") {
                Some(m) => self.funksiya_çağır(&m.bağla(f.clone()), args, adlı, yer),
                None => Err(xəta_yer("TipXətası", format!("`{}` çağırıla bilməz", tip_adı(f)), yer, "ALQ-T008")),
            },
            _ => Err(xəta_yer("TipXətası", format!("`{}` çağırıla bilməz", tip_adı(f)), yer, "ALQ-T008")),
        }
    }

    pub fn funksiya_çağır(&self, f: &Rc<Funksiya>, args: Vec<D>, adlı: Adlı, yer: Option<Yer>) -> Nəticə {
        if let Some(h) = &f.bəzənmiş {
            let mut a = Vec::with_capacity(args.len() + 1);
            if let Some(o) = &f.özü {
                a.push(o.clone());
            }
            a.extend(args);
            return self.çağır(h, a, adlı, yer);
        }
        if f.asinxron && !f.generator {
            let sinxron = Rc::new(Funksiya {
                ad: f.ad.clone(),
                parametrlər: f.parametrlər.clone(),
                gövdə: f.gövdə.clone(),
                mühit: f.mühit.clone(),
                asinxron: false,
                generator: false,
                özü: f.özü.clone(),
                sinif: f.sinif.clone(),
                annot: f.annot,
                yaddaş: None,
                bəzənmiş: None,
            });
            return Ok(D::Gələcək(Gələcək::yeni(&f.ad, move |i| i.funksiya_çağır(&sinxron, args, adlı, yer))));
        }
        let açar = match &f.yaddaş {
            Some(y) if adlı.is_empty() => {
                let a: Vec<YaddaşAçarı> = args.iter().map(yaddaş_açarı).collect();
                if let Some(d) = y.borrow().get(&a) {
                    return Ok(d.clone());
                }
                Some(a)
            }
            _ => None,
        };
        let d = self.dərinlik.get() + 1;
        if d > STEK_HƏDDİ {
            return Err(xəta_yer(
                "StekDaşmaXətası",
                format!("çağırış dərinliyi {} həddini aşdı — sonsuz rekursiya?", STEK_HƏDDİ),
                yer,
                "ALQ-R010",
            ));
        }
        self.dərinlik.set(d);
        let r = match crate::vm::kod_tap(f) {
            Some(k) => crate::vm::masin::gövdə_işlət(self, f, &k, args, adlı, yer),
            None => self.funksiya_gövdəsi(f, args, adlı, yer),
        };
        self.dərinlik.set(self.dərinlik.get() - 1);
        let r = r?;
        if let (Some(a), Some(y)) = (açar, &f.yaddaş) {
            y.borrow_mut().insert(a, r.clone());
        }
        Ok(r)
    }

    fn funksiya_gövdəsi(&self, f: &Rc<Funksiya>, args: Vec<D>, adlı: Adlı, yer: Option<Yer>) -> Nəticə {
        let m = f.mühit.alt_tutumla(f.parametrlər.len() + if f.özü.is_some() { 2 } else { 0 });
        if let Some(özü) = &f.özü {
            m.elan(ad("özü"), özü.clone(), false);
            let sinif = f.sinif.clone().or_else(|| match özü {
                D::Nümunə(n) => Some(n.sinif.clone()),
                _ => None,
            });
            if let Some(s) = sinif {
                m.elan(ad("__sinif__"), D::Sinif(s), false);
            }
        } else if let Some(s) = &f.sinif {
            m.elan(ad("__sinif__"), D::Sinif(s.clone()), false);
        }
        #[cfg(target_arch = "wasm32")]
        let saxlanan = if f.generator { (args.clone(), adlı.clone()) } else { (vec![], vec![]) };
        self.parametrləri_bağla(f, args, adlı, &m, yer)?;
        if f.generator {
            #[cfg(target_arch = "wasm32")]
            return Ok(D::Gen(Generator::yeni(GenMənbə::Təkrar(Təkrar { f: f.clone(), args: saxlanan.0, adlı: saxlanan.1, verilən: 0 }))));
            #[cfg(not(target_arch = "wasm32"))]
            return Ok(D::Gen(self.korutin_qur(f, m)));
        }
        match &f.gövdə {
            // `(x) => f(x)?` — yayma siqnalı lambdadan qaytarılır
            FGövdə::İfadə(e) => match self.ifadə(e, &m) {
                Err(Siqnal::Qaytar(d)) => Ok(d),
                r => r,
            },
            FGövdə::Blok(g) => {
                self.gecikdirilmiş.borrow_mut().push(vec![]);
                let r = match self.blok(g, &m) {
                    Ok(()) => self.son_ifadənin_dəyəri(g, &m),
                    Err(Siqnal::Qaytar(d)) | Err(Siqnal::Ver(d)) => Ok(d),
                    Err(x) => Err(x),
                };
                let gecikmiş = self.gecikdirilmiş.borrow_mut().pop().unwrap_or_default();
                for (e, mm) in gecikmiş.iter().rev() {
                    match self.ifadə(e, mm) {
                        Ok(_) | Err(Siqnal::Xəta(_)) => {}
                        Err(x) => return Err(x),
                    }
                }
                // Müqavilə (§ 5.13): son şərtlər qaytarılan dəyərlə yoxlanır
                if let (Ok(d), Some(Cümlə::Tələb(..) | Cümlə::Zəmanət(..))) = (&r, g.first()) {
                    self.zəmanətləri_yoxla(g, d, &m)?;
                }
                r
            }
        }
    }

    fn son_ifadənin_dəyəri(&self, g: &[Cümlə], m: &Mühit) -> Nəticə {
        match g.last() {
            Some(Cümlə::İfadə(_, e)) if !matches!(&**e, İfadə::Mənimsətmə(..) | İfadə::Çağırış(..)) => {
                match self.ifadə(e, m) {
                    Ok(d) => Ok(d),
                    Err(Siqnal::Xəta(_)) => Ok(D::Boş),
                    Err(x) => Err(x),
                }
            }
            _ => Ok(D::Boş),
        }
    }

    /// `wasm32`: generator gövdəsini təzə əhatədə başdan işlədir.
    #[cfg(target_arch = "wasm32")]
    pub fn generator_gövdəsi(&self, f: &Rc<Funksiya>, args: Vec<D>, adlı: Adlı) -> Nəticə<()> {
        let m = f.mühit.alt();
        if let Some(özü) = &f.özü {
            m.elan(ad("özü"), özü.clone(), false);
            let sinif = f.sinif.clone().or_else(|| match özü {
                D::Nümunə(n) => Some(n.sinif.clone()),
                _ => None,
            });
            if let Some(s) = sinif {
                m.elan(ad("__sinif__"), D::Sinif(s), false);
            }
        } else if let Some(s) = &f.sinif {
            m.elan(ad("__sinif__"), D::Sinif(s.clone()), false);
        }
        self.parametrləri_bağla(f, args, adlı, &m, None)?;
        match &f.gövdə {
            FGövdə::Blok(g) => self.blok(g, &m),
            FGövdə::İfadə(_) => Ok(()),
        }
    }

    #[cfg(not(target_arch = "wasm32"))]
    fn korutin_qur(&self, f: &Rc<Funksiya>, m: Mühit) -> Rc<Generator> {
        let i = self.statik();
        let gövdə = match &f.gövdə {
            FGövdə::Blok(g) => g.clone(),
            FGövdə::İfadə(_) => Rc::new(vec![]),
        };
        let stek = corosensei::stack::DefaultStack::new(KORUTİN_STEKİ).expect("korutin steki");
        let vm = crate::vm::generator_kodu(f).map(|k| (k, f.clone()));
        let co = corosensei::Coroutine::with_stack(stek, move |y: &corosensei::Yielder<(), D>, ()| {
            i.ver.set(y as *const _);
            i.dərinlik.set(0);
            if let Some((k, f)) = &vm {
                return crate::vm::masin::generator_işlət(i, k, f, m.clone());
            }
            match i.blok(&gövdə, &m) {
                Ok(()) | Err(Siqnal::Qaytar(_)) | Err(Siqnal::Dayan(_)) => Ok(()),
                Err(x) => Err(x),
            }
        });
        Generator::yeni(GenMənbə::Korutin(Box::new(co), f.ad.clone()))
    }

    fn parametrləri_bağla(&self, f: &Funksiya, args: Vec<D>, mut adlı: Adlı, m: &Mühit, yer: Option<Yer>) -> Nəticə<()> {
        let ps = &f.parametrlər;
        let mövqeli_say = ps.iter().filter(|p| !p.variadic && !p.adlı_variadic && !p.yalnız_adlı).count();
        let variadic = ps.iter().find(|p| p.variadic);
        let adlı_variadic = ps.iter().find(|p| p.adlı_variadic);
        if args.len() > mövqeli_say && variadic.is_none() {
            return Err(xəta_yer(
                "ArqumentXətası",
                format!("`{}` ən çox {} mövqeli arqument qəbul edir, {} verilib", f.ad, mövqeli_say, args.len()),
                yer,
                "ALQ-T003",
            ));
        }
        let n = args.len();
        let mut args = args.into_iter();
        let mut i = 0;
        for p in ps.iter().filter(|p| !p.variadic && !p.adlı_variadic && !p.yalnız_adlı) {
            let d = if i < n {
                args.next().unwrap()
            } else if let Some(d) = (!adlı.is_empty()).then(|| adlı_götür(&mut adlı, &p.ad)).flatten() {
                d
            } else if let Some(s) = &p.standart {
                self.ifadə(s, m)?
            } else {
                return Err(xəta_yer(
                    "ArqumentXətası",
                    format!("`{}` üçün `{}` arqumenti verilməyib", f.ad, p.ad),
                    yer,
                    "ALQ-T003",
                ));
            };
            i += 1;
            m.elan(ad(&p.ad), dəyər_kopyası(genişlət(d, p.tip.as_ref())), false);
        }
        for p in ps.iter().filter(|p| p.yalnız_adlı) {
            let d = if let Some(d) = adlı_götür(&mut adlı, &p.ad) {
                d
            } else if let Some(s) = &p.standart {
                self.ifadə(s, m)?
            } else {
                return Err(xəta_yer(
                    "ArqumentXətası",
                    format!("`{}` üçün `{}` adlı arqumenti məcburidir", f.ad, p.ad),
                    yer,
                    "ALQ-T003",
                ));
            };
            m.elan(ad(&p.ad), d, false);
        }
        if let Some(v) = variadic {
            m.elan(ad(&v.ad), D::siyahı(args.collect()), false);
        }
        if let Some(v) = adlı_variadic {
            let mut l = Lüğət::default();
            for (k, d) in adlı.drain(..) {
                l.insert(Açar(D::S(k)), d);
            }
            m.elan(ad(&v.ad), D::lüğət(l), false);
        }
        if !adlı.is_empty() {
            let mut a: Vec<String> = adlı.iter().map(|(k, _)| k.to_string()).collect();
            a.sort();
            return Err(xəta_yer(
                "ArqumentXətası",
                format!("`{}` naməlum adlı arqument: {}", f.ad, a.join(", ")),
                yer,
                "ALQ-T004",
            ));
        }
        if let Some(D::Nümunə(n)) = &f.özü {
            for p in ps.iter() {
                if p.xassə_görünüşü.is_some() {
                    if let Ok(d) = m.al(&p.ad) {
                        n.sahələr.borrow_mut().insert(ad(&p.ad), d);
                    }
                }
            }
        }
        Ok(())
    }

    // ── Gözlə ─────────────────────────────────────────────────────────

    pub fn gözlə(&self, d: D, yer: Option<Yer>) -> Nəticə {
        match &d {
            D::Gələcək(g) => g.al(self),
            D::Siyahı(l) => {
                let v = l.borrow().clone();
                if !v.iter().any(|x| matches!(x, D::Gələcək(_))) {
                    return Ok(d);
                }
                for x in &v {
                    if let D::Gələcək(g) = x {
                        g.başlat(self);
                    }
                }
                let mut n = vec![];
                for x in v {
                    n.push(self.gözlə(x, yer)?);
                }
                Ok(D::siyahı(n))
            }
            D::Kortej(k) => {
                if !k.iter().any(|x| matches!(x, D::Gələcək(_))) {
                    return Ok(d);
                }
                for x in k.iter() {
                    if let D::Gələcək(g) = x {
                        g.başlat(self);
                    }
                }
                let mut n = vec![];
                for x in k.iter() {
                    n.push(self.gözlə(x.clone(), yer)?);
                }
                Ok(D::kortej(n))
            }
            _ => Ok(d),
        }
    }

    // ── JSX ───────────────────────────────────────────────────────────

    pub fn jsx_uşaqlar(&self, uşaqlar: &[aac::JSXUşaq], m: &Mühit) -> Nəticə<Vec<D>> {
        let mut n = vec![];
        for u in uşaqlar {
            match u {
                aac::JSXUşaq::Mətn(s) => n.push(D::s(s)),
                aac::JSXUşaq::İfadə(e) => {
                    let d = self.ifadə(e, m)?;
                    match &d {
                        D::Boş | D::M(false) => {}
                        D::Siyahı(l) => {
                            for x in l.borrow().iter() {
                                if !matches!(x, D::Boş | D::M(false)) {
                                    n.push(x.clone());
                                }
                            }
                        }
                        D::Kortej(l) => {
                            for x in l.iter() {
                                if !matches!(x, D::Boş | D::M(false)) {
                                    n.push(x.clone());
                                }
                            }
                        }
                        _ => n.push(d),
                    }
                }
            }
        }
        Ok(n)
    }

    pub fn e_jsx(&self, yer: Yer, a: &str, atributlar: &[aac::JSXAtribut], uşaqlar: &[aac::JSXUşaq], m: &Mühit) -> Nəticə {
        let mut atr = Lüğət::default();
        for x in atributlar {
            if x.yayma {
                let d = match &x.dəyər {
                    Some(e) => self.ifadə(e, m)?,
                    None => D::Boş,
                };
                match &d {
                    D::Lüğət(l) => {
                        for (k, v) in l.borrow().iter() {
                            let k = match &k.0 {
                                D::S(s) => s.to_string(),
                                o => py_str_sadə(o),
                            };
                            atr.insert(Açar(D::str(k)), v.clone());
                        }
                    }
                    D::Nümunə(n) => {
                        for (k, v) in n.sahələr.borrow().iter() {
                            atr.insert(Açar(D::S(k.clone())), v.clone());
                        }
                    }
                    _ => {
                        return Err(xəta_yer(
                            "TipXətası",
                            format!("`{{...}}` yayması lüğət və ya obyekt gözləyir, `{}` gəlib", tip_adı(&d)),
                            x.dəyər.as_ref().map(|e| e.yer()),
                            "ALQ-T001",
                        ))
                    }
                }
            } else {
                let d = match &x.dəyər {
                    None => D::M(true),
                    Some(e) => self.ifadə(e, m)?,
                };
                atr.insert(Açar(D::s(&x.ad)), d);
            }
        }
        let uş = self.jsx_uşaqlar(uşaqlar, m)?;
        let ilk = a.split('.').next().unwrap_or("").chars().next();
        let komponent = match ilk {
            Some(c) => c.is_alphabetic() && c.to_uppercase().collect::<String>() == c.to_string(),
            None => false,
        };
        if !komponent {
            return Ok(D::Element(Rc::new(Element { ad: ad(a), atributlar: D::lüğət(atr), uşaqlar: D::siyahı(uş) })));
        }
        self.komponent_göstər(a, atr, uş, Some(yer), m)
    }

    fn komponent_göstər(&self, a: &str, atr: Lüğət, uş: Vec<D>, yer: Option<Yer>, m: &Mühit) -> Nəticə {
        let hissələr: Vec<&str> = a.split('.').collect();
        let mut h = match m.al(hissələr[0]) {
            Ok(d) => d,
            Err(Siqnal::Xəta(_)) => {
                return Err(xəta_yer("ArqumentXətası", format!("`<{} />` komponenti tapılmadı", a), yer, "ALQ-T022"))
            }
            Err(x) => return Err(x),
        };
        for x in &hissələr[1..] {
            h = self.üzv_al(&h, x, yer)?;
        }
        let adlı: Adlı = atr.iter().map(|(k, v)| (ad(k.0.mətn_al().unwrap_or("")), v.clone())).collect();
        match &h {
            D::Sinif(s) => {
                let q = s.qurucu_tap("");
                let n = if q.map(|q| !q.parametrlər.is_empty()).unwrap_or(false) {
                    self.nümunə_yarat(s, None, vec![], adlı, yer)?
                } else {
                    let n = self.nümunə_yarat(s, None, vec![], vec![], yer)?;
                    if let D::Nümunə(x) = &n {
                        for (k, v) in adlı {
                            x.sahələr.borrow_mut().insert(k, v);
                        }
                    }
                    n
                };
                if !uş.is_empty() {
                    if let D::Nümunə(x) = &n {
                        let mut f = x.sahələr.borrow_mut();
                        if !f.contains_key("uşaqlar") {
                            f.insert(ad("uşaqlar"), D::siyahı(uş));
                        }
                    }
                }
                let Some(g) = s.metod_tap("göstər") else {
                    return Err(xəta_yer(
                        "TipXətası",
                        format!("`{}` komponentində `göstər()` metodu yoxdur", s.ad),
                        yer,
                        "ALQ-T053",
                    ));
                };
                self.funksiya_çağır(&g.bağla(n), vec![], vec![], yer)
            }
            D::Funksiya(_) | D::Daxili(_) | D::Metod(_) | D::XətaSinfi(_) => {
                let mut adlı = adlı;
                if !uş.is_empty() && !adlı.iter().any(|(k, _)| &**k == "uşaqlar") {
                    adlı.push((ad("uşaqlar"), D::siyahı(uş)));
                }
                self.çağır(&h, vec![], adlı, yer)
            }
            _ => Err(xəta_yer(
                "TipXətası",
                format!("`<{} />` sinif və ya funksiya olmalıdır, `{}` gəlib", a, tip_adı(&h)),
                yer,
                "ALQ-T008",
            )),
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  Köməkçilər
    // ═══════════════════════════════════════════════════════════════════

    #[inline]
    pub fn məntiq(&self, e: &İfadə, m: &Mühit) -> Nəticə<bool> {
        match self.ifadə(e, m)? {
            D::M(b) => Ok(b),
            d => Err(xəta_yer(
                "TipXətası",
                format!("şərt `məntiq` tipi olmalıdır, `{}` gəlib", tip_adı(&d)),
                Some(e.yer()),
                "ALQ-T007",
            )),
        }
    }

    pub fn iterasiya(&self, d: &D, yer: Option<Yer>) -> Nəticə<İter> {
        Ok(match d {
            D::Nümunə(n) => {
                if let Some(f) = n.sinif.metod_tap("iterator") {
                    let r = self.funksiya_çağır(&f.bağla(d.clone()), vec![], vec![], yer)?;
                    return self.iterasiya(&r, yer);
                }
                if let (Some(u), Some(_)) = (n.sinif.metod_tap("uzunluq"), n.sinif.metod_tap("al")) {
                    let k = self.funksiya_çağır(&u.bağla(d.clone()), vec![], vec![], None)?;
                    let k = k.i64().unwrap_or(0);
                    return Ok(İter::Nümunə(d.clone(), k, 0));
                }
                return Err(xəta_yer("TipXətası", format!("`{}` üzərində dövr qurulmur", tip_adı(d)), yer, "ALQ-T009"));
            }
            D::Gen(g) => İter::Gen(g.clone()),
            D::Obyekt(_) if super::aktyor::kanal(d).is_some() => İter::Kanal(super::aktyor::kanal(d).unwrap()),
            D::Lüğət(l) => İter::Vec(l.borrow().keys().map(|k| k.0.clone()).collect::<Vec<_>>().into_iter()),
            D::Siyahı(l) => İter::Siyahı(l.clone(), 0),
            D::Kortej(k) => İter::Vec(k.to_vec().into_iter()),
            D::Dəst(s) => İter::Vec(dəst_sırası(&s.borrow()).into_iter()),
            D::S(s) => İter::Vec(s.chars().map(|c| D::str(c.to_string())).collect::<Vec<_>>().into_iter()),
            D::Bayt(b) => İter::Vec(b.iter().map(|x| D::T(*x as i64)).collect::<Vec<_>>().into_iter()),
            D::Diapazon(r) => İter::Diapazon(r.başlanğıc, r.hədd(), r.addım),
            D::Sadalama(s) => {
                let v = s.variantlar.borrow();
                İter::Vec(s.sıra.borrow().iter().filter_map(|a| v.get(a).cloned()).collect::<Vec<_>>().into_iter())
            }
            _ => return Err(xəta_yer("TipXətası", format!("`{}` üzərində dövr qurulmur", tip_adı(d)), yer, "ALQ-T009")),
        })
    }

    pub fn siyahıya(&self, d: &D, yer: Option<Yer>) -> Nəticə<Vec<D>> {
        if let D::Siyahı(l) = d {
            return Ok(l.borrow().clone());
        }
        self.iterasiya(d, yer)?.hamısı(self, yer)
    }

    // ── Tip əməliyyatları ─────────────────────────────────────────────

    pub fn tip_dəyəri(&self, t: &Tip, m: &Mühit) -> Nəticə {
        match t {
            Tip::Ad { yol, yer, .. } => {
                let mut d = m.al(&yol[0])?;
                for h in &yol[1..] {
                    d = self.üzv_al(&d, h, Some(*yer))?;
                }
                if let D::TipAliası(a) = &d {
                    return self.tip_dəyəri(&a.1, m);
                }
                Ok(d)
            }
            _ => Err(xəta_yer("TipXətası", "sadə tip adı gözlənilirdi", Some(t.yer()), "ALQ-T002")),
        }
    }

    pub fn tip_uyğundur(&self, d: &D, t: &Tip, m: &Mühit) -> Nəticə<bool> {
        match t {
            Tip::Birləşmə { variantlar, .. } => {
                for v in variantlar {
                    if self.tip_uyğundur(d, v, m)? {
                        return Ok(true);
                    }
                }
                Ok(false)
            }
            Tip::Ad { ixtiyari, .. } => {
                let a = t.tam_ad();
                if d.boşdur() {
                    return Ok(a == "heç" || a == "boş" || *ixtiyari);
                }
                let sadə = match a.as_str() {
                    "tam" => Some(d.tamdır()),
                    "onluq" => Some(matches!(d, D::O(_))),
                    "mətn" => Some(matches!(d, D::S(_))),
                    "simvol" => Some(matches!(d, D::S(s) if s.chars().count() <= 2)),
                    "məntiq" => Some(matches!(d, D::M(_))),
                    "bayt" => Some(matches!(d, D::Bayt(_))),
                    "siyahı" => Some(matches!(d, D::Siyahı(_))),
                    "lüğət" => Some(matches!(d, D::Lüğət(_))),
                    "dəst" => Some(matches!(d, D::Dəst(_))),
                    "kortej" => Some(matches!(d, D::Kortej(_))),
                    "istənilən" => Some(true),
                    "heç" => Some(false),
                    _ => None,
                };
                if let Some(s) = sadə {
                    return Ok(s);
                }
                let h = match self.tip_dəyəri(t, m) {
                    Ok(h) => h,
                    Err(Siqnal::Xəta(_)) => return Ok(false),
                    Err(x) => return Err(x),
                };
                Ok(match (&h, d) {
                    (D::Sinif(s), D::Nümunə(n)) => n.sinif.alt_sinifdirmi(s) || n.sinif.interfeyslər.iter().any(|i| **i == *s.ad),
                    (D::Sadalama(s), D::SD(v)) => Rc::ptr_eq(s, &v.sadalama),
                    _ => false,
                })
            }
            _ => Ok(false),
        }
    }

    pub fn çevir(&self, d: &D, h: &str, yer: Option<Yer>) -> Nəticə {
        if super::vahid::vahiddir(h) && (super::vahid::kəmiyyət(d).is_some() || d.ədəddir()) {
            return self.kəmiyyəti_çevir(d, h, yer);
        }
        match h {
            "tam" => match d {
                D::M(b) => return Ok(D::T(*b as i64)),
                D::T(_) | D::BT(_) => return Ok(d.clone()),
                D::O(f) => return super::eded::onluqdan_tam(*f),
                D::S(s) => {
                    return match super::eded::tam_oxu(s.trim(), 10) {
                        Some(n) => Ok(n),
                        None => Err(xəta_yer("ÇevrilməXətası", format!("\"{}\" tam ədədə çevrilə bilmir", s), yer, "ALQ-R005")),
                    }
                }
                _ => {}
            },
            "onluq" => match d {
                D::M(b) => return Ok(D::O(if *b { 1.0 } else { 0.0 })),
                D::T(_) | D::BT(_) | D::O(_) => return Ok(D::O(d.onluq().unwrap())),
                D::S(s) => {
                    return match super::eded::onluq_oxu(s.trim()) {
                        Some(f) => Ok(D::O(f)),
                        None => Err(xəta_yer("ÇevrilməXətası", format!("\"{}\" onluq ədədə çevrilə bilmir", s), yer, "ALQ-R005")),
                    }
                }
                _ => {}
            },
            "mətn" => return Ok(D::str(mətnə(self, d)?)),
            "məntiq" => {
                if let D::M(_) = d {
                    return Ok(d.clone());
                }
                if let D::S(s) = d {
                    let k = crate::elifba::kiçiyə(s.trim());
                    if ["doğru", "dogru", "true", "1"].contains(&k.as_str()) {
                        return Ok(D::M(true));
                    }
                    if ["yanlış", "yanlis", "false", "0"].contains(&k.as_str()) {
                        return Ok(D::M(false));
                    }
                }
                return Err(xəta_yer("ÇevrilməXətası", "məntiqi tipə açıq çevirmə tələb olunur", yer, "ALQ-R005"));
            }
            "siyahı" => return Ok(D::siyahı(self.siyahıya(d, yer)?)),
            "dəst" => {
                let mut s = Dəst::default();
                for x in self.siyahıya(d, yer)? {
                    s.insert(Açar::yeni(x)?);
                }
                return Ok(D::dəst(s));
            }
            _ => {}
        }
        Err(xəta_yer(
            "ÇevrilməXətası",
            format!("`{}` → `{}` çevrilməsi mümkün deyil", tip_adı(d), h),
            yer,
            "ALQ-T014",
        ))
    }

    pub fn üzvlük(&self, el: &D, k: &D, yer: Option<Yer>) -> Nəticə<bool> {
        match k {
            D::Nümunə(n) => {
                if let Some(f) = n.sinif.metod_tap("ehtiva") {
                    let r = self.funksiya_çağır(&f.bağla(k.clone()), vec![el.clone()], vec![], yer)?;
                    return Ok(matches!(r, D::M(true)));
                }
            }
            D::Lüğət(l) => {
                return Ok(match Açar::yeni(el.clone()) {
                    Ok(a) => l.borrow().contains_key(&a),
                    Err(_) => false,
                })
            }
            D::Dəst(s) => {
                return Ok(match Açar::yeni(el.clone()) {
                    Ok(a) => s.borrow().contains(&a),
                    Err(_) => false,
                })
            }
            D::Siyahı(l) => return Ok(l.borrow().iter().any(|x| eyni(x, el) || py_eq(x, el))),
            D::Kortej(l) => return Ok(l.iter().any(|x| eyni(x, el) || py_eq(x, el))),
            D::S(s) => {
                return match el {
                    D::S(e) => Ok(s.contains(&**e)),
                    _ => Err(xəta_yer("TipXətası", "`içindədir` mətndə mətn gözləyir", yer, "ALQ-T008")),
                }
            }
            D::Diapazon(r) => {
                return Ok(match el {
                    D::T(x) => r.ehtiva(*x),
                    D::M(b) => r.ehtiva(*b as i64),
                    D::O(f) if f.fract() == 0.0 && f.abs() < 9e18 => r.ehtiva(*f as i64),
                    _ => false,
                })
            }
            _ => {}
        }
        Err(xəta_yer(
            "TipXətası",
            format!("`içindədir` `{}` tipinə tətbiq edilmir", tip_adı(k)),
            yer,
            "ALQ-T008",
        ))
    }
}
