//! Standart kitabxana — qlobal funksiyalar və modul yükləmə (kitabxana.py).

use super::cagiris::*;
use super::deyerler::*;
use super::eded::{onluq_oxu, tam_oxu};
use super::icraci::İcraçı;
use super::metodlar::{cəmlə, ilk_min, sırala_açarla};
use crate::xeta::Yer;
use std::path::{Path, PathBuf};
use std::rc::Rc;

pub fn tam_yoxla(d: &D, ad: &str) -> Nəticə<D> {
    if d.tamdır() {
        return Ok(d.clone());
    }
    Err(xəta("TipXətası", format!("`{}` tam ədəd gözləyir, `{}` gəlib", ad, tip_adı(d)), "ALQ-T004"))
}

pub fn mətn_yoxla(d: &D, ad: &str) -> Nəticə<Rc<str>> {
    match d {
        D::S(s) => Ok(s.clone()),
        _ => Err(xəta("TipXətası", format!("`{}` mətn gözləyir, `{}` gəlib", ad, tip_adı(d)), "ALQ-T004")),
    }
}

/// Mövqeli və ya adlı arqument
pub fn arq_al(a: &[D], adlı: &Adlı, k: usize, ad_: &str) -> Option<D> {
    if let Some(d) = a.get(k) {
        return Some(d.clone());
    }
    adlı.iter().find(|(x, _)| &**x == ad_).map(|x| x.1.clone())
}

pub fn oxu(i: &İcraçı, soruş: Option<&D>) -> Nəticə<String> {
    if let Some(s) = soruş {
        let s = mətnə(i, s)?;
        if !s.is_empty() {
            i.yaz_xam(&s);
        }
    }
    match i.sətir_oxu() {
        Some(s) => Ok(s),
        None => Err(xəta("GirişÇıxışXətası", "girişin sonu — oxunacaq məlumat qalmadı", "ALQ-R009")),
    }
}

fn yaz_birləşdir(i: &İcraçı, a: &[D]) -> Nəticə<String> {
    let mut h = Vec::with_capacity(a.len());
    for x in a {
        h.push(mətnə(i, x)?);
    }
    Ok(h.join(" "))
}

pub fn qlobal_qur(i: &İcraçı) {
    let m = i.qlobal.clone();
    let d = |a: &str, min: usize, maks: Option<usize>, f: Box<dyn Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə>| {
        m.elan(ad(a), D::Daxili(Rc::new(Daxili { ad: ad(a), f, min, maks })), false);
    };

    d("yaz", 0, None, Box::new(|i, a, _| {
        let s = yaz_birləşdir(i, &a)?;
        i.yaz(&s);
        Ok(D::Boş)
    }));
    d("yazSətirsiz", 0, None, Box::new(|i, a, _| {
        let s = yaz_birləşdir(i, &a)?;
        i.yaz_xam(&s);
        Ok(D::Boş)
    }));
    d("yazXəta", 0, None, Box::new(|i, a, _| {
        let s = yaz_birləşdir(i, &a)?;
        i.xəta_yaz(&s);
        Ok(D::Boş)
    }));
    d("oxu", 0, Some(1), Box::new(|i, a, _| Ok(D::str(oxu(i, a.first())?))));
    d("oxuTam", 0, Some(2), Box::new(|i, a, _| loop {
        let m = oxu(i, a.first())?;
        if let Some(n) = tam_oxu(m.trim(), 10) {
            return Ok(n);
        }
        if let Some(D::M(false)) = a.get(1) {
            return Err(xəta("ÇevrilməXətası", format!("\"{}\" tam ədəd deyil", m), "ALQ-R005"));
        }
        i.yaz("Düzgün tam ədəd daxil edin.");
    }));
    d("oxuOnluq", 0, Some(1), Box::new(|i, a, _| loop {
        let m = oxu(i, a.first())?;
        if let Some(f) = onluq_oxu(&m.trim().replace(',', ".")) {
            return Ok(D::O(f));
        }
        i.yaz("Düzgün ədəd daxil edin.");
    }));
    d("oxuMəntiq", 0, Some(1), Box::new(|i, a, _| loop {
        let c = crate::elifba::kiçiyə(oxu(i, a.first())?.trim());
        if ["hə", "he", "bəli", "beli", "doğru", "dogru", "h", "b"].contains(&c.as_str()) {
            return Ok(D::M(true));
        }
        if ["yox", "xeyr", "yanlış", "yanlis", "y", "x"].contains(&c.as_str()) {
            return Ok(D::M(false));
        }
        i.yaz("`hə` və ya `yox` yazın.");
    }));
    d("oxuHamısı", 0, Some(0), Box::new(|i, _, _| Ok(D::str(i.hamısını_oxu()))));
    d("tip", 1, Some(1), Box::new(|_, a, _| Ok(D::str(tip_adı(&a[0])))));
    d("tamƏt", 1, Some(3), Box::new(|i, a, _| {
        let x = &a[0];
        let st = a.get(1).filter(|x| !x.boşdur()).cloned();
        let r = match x {
            D::M(b) => Some(D::T(*b as i64)),
            D::T(_) | D::BT(_) => Some(x.clone()),
            D::O(f) => super::eded::onluqdan_tam(*f).ok(),
            _ => {
                let s = py_str_sadə(x);
                let əsas = a.get(2).and_then(|d| d.i64()).unwrap_or(10) as u32;
                if (2..=36).contains(&əsas) { tam_oxu(&s, əsas) } else { None }
            }
        };
        match r {
            Some(r) => Ok(r),
            None => match st {
                Some(s) => Ok(s),
                None => Err(xəta("ÇevrilməXətası", format!("\"{}\" tam ədədə çevrilə bilmir", mətnə(i, x)?), "ALQ-R005")),
            },
        }
    }));
    d("onluqƏt", 1, Some(2), Box::new(|i, a, _| {
        let x = &a[0];
        let r = match x {
            D::S(s) => onluq_oxu(&s.trim().replace(',', ".")),
            _ => x.onluq(),
        };
        match r {
            Some(f) => Ok(D::O(f)),
            None => match a.get(1).filter(|x| !x.boşdur()) {
                Some(s) => Ok(s.clone()),
                None => Err(xəta("ÇevrilməXətası", format!("\"{}\" ədədə çevrilə bilmir", mətnə(i, x)?), "ALQ-R005")),
            },
        }
    }));
    d("mətnƏt", 1, Some(1), Box::new(|i, a, _| Ok(D::str(mətnə(i, &a[0])?))));
    d("məntiqƏt", 1, Some(1), Box::new(|i, a, _| i.çevir(&a[0], "məntiq", None)));
    d("simvolƏt", 1, Some(1), Box::new(|_, a, _| {
        let k = tam_yoxla(&a[0], "simvolƏt")?;
        match k.i64().and_then(|k| u32::try_from(k).ok()).and_then(char::from_u32) {
            Some(c) => Ok(D::str(c.to_string())),
            None => Err(xəta("DəyərXətası", "simvol kodu diapazondan kənardır", "ALQ-R005")),
        }
    }));
    d("kodƏt", 1, Some(1), Box::new(|_, a, _| {
        let s = mətn_yoxla(&a[0], "kodƏt")?;
        match s.chars().next() {
            Some(c) => Ok(D::T(c as i64)),
            None => Err(xəta("İndeksXətası", "boş mətn", "ALQ-R002")),
        }
    }));
    d("uzunluq", 1, Some(1), Box::new(|i, a, _| uzunluq(i, &a[0])));
    d("boşdur", 1, Some(1), Box::new(|i, a, _| {
        if a[0].boşdur() {
            return Ok(D::M(true));
        }
        let n = uzunluq(i, &a[0])?;
        Ok(D::M(matches!(n, D::T(0))))
    }));
    d("cəm", 1, Some(2), Box::new(|i, a, _| {
        let el = i.siyahıya(&a[0], None)?;
        for e in &el {
            if !e.ədəddir() {
                return Err(xəta("TipXətası", format!("ədəd gözlənilirdi, `{}` gəlib", tip_adı(e)), "ALQ-T004"));
            }
        }
        cəmlə(i, &el, a.get(1).cloned().unwrap_or(D::T(0)))
    }));
    for (n, böyük) in [("minimum", false), ("maksimum", true)] {
        d(n, 1, None, Box::new(move |i, a, _| {
            let k = if a.len() == 1 { i.siyahıya(&a[0], None)? } else { a };
            if k.is_empty() {
                return Err(xəta("BoşKolleksiyaXətası", format!("boş kolleksiyada {} yoxdur", n), "ALQ-R014"));
            }
            Ok(ilk_min(&k, böyük))
        }));
    }
    d("sırala", 1, Some(2), Box::new(|i, a, _| {
        let el = i.siyahıya(&a[0], None)?;
        Ok(D::siyahı(sırala_açarla(i, el, a.get(1).filter(|x| !x.boşdur()))?))
    }));
    d("tərs", 1, Some(1), Box::new(|i, a, _| {
        let mut el = i.siyahıya(&a[0], None)?;
        el.reverse();
        Ok(D::siyahı(el))
    }));
    d("nömrələ", 1, Some(1), Box::new(|i, a, _| {
        let el = i.siyahıya(&a[0], None)?;
        Ok(D::siyahı(el.into_iter().enumerate().map(|(k, x)| D::kortej(vec![D::T(k as i64), x])).collect()))
    }));
    d("zip", 1, None, Box::new(|i, a, _| {
        let mut s = vec![];
        for x in &a {
            s.push(i.siyahıya(x, None)?);
        }
        let n = s.iter().map(|x| x.len()).min().unwrap_or(0);
        Ok(D::siyahı((0..n).map(|k| D::kortej(s.iter().map(|x| x[k].clone()).collect())).collect()))
    }));
    d("diapazon", 1, Some(3), Box::new(|_, a, _| {
        if a.len() == 1 {
            let s = tam_yoxla(&a[0], "diapazon")?;
            return diapazon_yarat(D::T(0), s, None, true);
        }
        diapazon_yarat(a[0].clone(), a[1].clone(), a.get(2).cloned(), true)
    }));
    d("siyahı", 0, Some(1), Box::new(|i, a, _| match a.first() {
        None | Some(D::Boş) => Ok(D::siyahı(vec![])),
        Some(k) => Ok(D::siyahı(i.siyahıya(k, None)?)),
    }));
    d("dəst", 0, None, Box::new(|i, a, _| {
        let el = if a.len() == 1 && matches!(a[0], D::Siyahı(_) | D::Kortej(_) | D::Dəst(_) | D::Diapazon(_)) {
            i.siyahıya(&a[0], None)?
        } else {
            a
        };
        let mut s = Dəst::default();
        for x in el {
            s.insert(Açar::yeni(x)?);
        }
        Ok(D::dəst(s))
    }));
    d("lüğət", 0, Some(1), Box::new(|i, a, _| match a.first() {
        None | Some(D::Boş) => Ok(D::lüğət(Lüğət::default())),
        Some(D::Lüğət(l)) => Ok(D::lüğət(l.borrow().clone())),
        Some(k) => {
            let mut l = Lüğət::default();
            for c in i.siyahıya(k, None)? {
                let c = i.siyahıya(&c, None)?;
                if c.len() != 2 {
                    return Err(xəta("DəyərXətası", "lüğət elementi cüt olmalıdır", "ALQ-R005"));
                }
                l.insert(Açar::yeni(c[0].clone())?, c[1].clone());
            }
            Ok(D::lüğət(l))
        }
    }));
    d("kortej", 0, Some(1), Box::new(|i, a, _| match a.first() {
        None | Some(D::Boş) => Ok(D::kortej(vec![])),
        Some(k) => Ok(D::kortej(i.siyahıya(k, None)?)),
    }));
    d("klonla", 1, Some(1), Box::new(|_, a, _| Ok(klonla(&a[0]))));
    d("çap", 1, None, Box::new(|i, a, _| {
        for x in &a {
            let s = format!("{} = {}", tip_adı(x), mətnə(i, x)?);
            i.yaz(&s);
        }
        Ok(D::Boş)
    }));
    d("ölç", 1, Some(1), Box::new(|i, a, _| {
        let b = super::platforma::monoton_san();
        let n = i.çağır(&a[0], vec![], vec![], None)?;
        let ms = (super::platforma::monoton_san() - b) * 1000.0;
        i.yaz(&format!("⏱ {:.3} ms", ms));
        Ok(n)
    }));
    d("panika", 0, Some(1), Box::new(|i, a, _| {
        let m = match a.first() {
            Some(x) => mətnə(i, x)?,
            None => String::new(),
        };
        Err(xəta("KritikXəta", if m.is_empty() { "panika".to_string() } else { m }, "ALQ-R008"))
    }));
    d("dayan", 0, Some(1), Box::new(|_, a, _| {
        let k = match a.first() {
            Some(x) => tam_yoxla(x, "dayan")?,
            None => D::T(0),
        };
        Err(Siqnal::Dayanma(k))
    }));
    d("eynidir", 2, Some(2), Box::new(|_, a, _| Ok(D::M(eyni(&a[0], &a[1])))));
    d("heş", 1, Some(1), Box::new(|_, a, _| {
        use std::hash::{Hash, Hasher};
        if let D::Nümunə(_) = &a[0] {
            return Ok(D::T(ptr_id(&a[0]) as i64));
        }
        let k = Açar::yeni(a[0].clone())?;
        let mut h = FxHasher::default();
        k.hash(&mut h);
        Ok(D::T((h.finish() >> 1) as i64))
    }));
    d("LəğvNişanı", 0, Some(1), Box::new(|_, _, _| Ok(D::LəğvNişanı(Rc::new(std::cell::Cell::new(false))))));
    d("Gələcək", 1, Some(1), Box::new(|_, a, _| {
        let f = a[0].clone();
        Ok(D::Gələcək(Gələcək::yeni("<asinxron>", move |i| i.çağır(&f, vec![], vec![], None))))
    }));

    for (x, _) in XETA_AGACI {
        if *x != "Atılan" {
            m.elan(ad(x), D::XətaSinfi(ad(x)), false);
        }
    }
    for (a, md) in super::modullar::modulları_qur(i) {
        m.elan(ad(a), D::Modul(md), false);
    }
}

pub fn uzunluq(i: &İcraçı, x: &D) -> Nəticə {
    if let D::Nümunə(n) = x {
        if let Some(f) = n.sinif.metod_tap("uzunluq") {
            return i.funksiya_çağır(&f.bağla(x.clone()), vec![], vec![], None);
        }
    }
    Ok(D::T(match x {
        D::S(s) => s.chars().count(),
        D::Siyahı(l) => l.borrow().len(),
        D::Lüğət(l) => l.borrow().len(),
        D::Dəst(l) => l.borrow().len(),
        D::Kortej(l) => l.len(),
        D::Bayt(l) => l.len(),
        D::Diapazon(r) => return Ok(D::T(r.uzunluq())),
        _ => {
            return Err(xəta("TipXətası", format!("`{}` tipinin uzunluğu yoxdur", tip_adı(x)), "ALQ-T006"))
        }
    } as i64))
}

pub fn klonla(x: &D) -> D {
    match x {
        D::Nümunə(n) => D::Nümunə(n.klonla()),
        D::Siyahı(l) => D::siyahı(l.borrow().iter().map(klonla).collect()),
        D::Lüğət(l) => D::lüğət(l.borrow().iter().map(|(k, v)| (Açar(klonla(&k.0)), klonla(v))).collect()),
        D::Dəst(s) => D::dəst(s.borrow().clone()),
        D::Kortej(k) => D::kortej(k.iter().map(klonla).collect()),
        _ => x.clone(),
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Modul yükləmə
// ═══════════════════════════════════════════════════════════════════════

pub fn modul_yüklə(i: &İcraçı, a: &str, yer: Option<Yer>) -> Nəticə<Rc<Modul>> {
    if let Some(D::Modul(m)) = i.qlobal.burada_al(a) {
        return Ok(m);
    }
    if a.contains('.') && !a.ends_with(".alq") && !a.ends_with(".alqor") {
        let h: Vec<&str> = a.split('.').collect();
        if let Some(mut cari) = i.qlobal.burada_al(h[0]) {
            let mut ok = true;
            for x in &h[1..] {
                let n = match &cari {
                    D::Modul(m) => m.üzvlər.borrow().get(*x).cloned(),
                    _ => None,
                };
                match n {
                    Some(n) => cari = n,
                    None => {
                        ok = false;
                        break;
                    }
                }
            }
            if ok {
                if let D::Modul(m) = cari {
                    return Ok(m);
                }
            }
        }
    }
    if let Some(m) = super::elave::modul(i, a) {
        return yer_qoy(m, yer);
    }
    if a.ends_with(".alq") || a.ends_with(".alqor") || a.starts_with('.') || a.starts_with('/') {
        return fayldan_modul(i, a, yer);
    }
    Err(xəta_yer("ArqumentXətası", format!("`{}` modulu tapılmadı", a), yer, "ALQ-M001"))
}

fn fayldan_modul(i: &İcraçı, yol: &str, yer: Option<Yer>) -> Nəticə<Rc<Modul>> {
    let baza: Option<PathBuf> = yer
        .and_then(|y| y.mənbə())
        .and_then(|m| m.yol.clone())
        .and_then(|p| std::fs::canonicalize(p).ok())
        .and_then(|p| p.parent().map(Path::to_path_buf))
        .or_else(|| i.əsas_qovluq.borrow().clone());
    let mut p = PathBuf::from(yol);
    if !p.is_absolute() {
        if let Some(b) = &baza {
            p = b.join(p);
        }
    }
    if !p.exists() {
        for u in [".alq", ".alqor"] {
            let q = PathBuf::from(format!("{}{}", p.display(), u));
            if q.exists() {
                p = q;
                break;
            }
        }
    }
    if !p.exists() {
        return Err(xəta_yer("ArqumentXətası", format!("\"{}\" modul faylı tapılmadı", yol), yer, "ALQ-M001"));
    }
    let p = std::fs::canonicalize(&p).unwrap_or(p);
    if let Some(m) = i.fayl_modulları.borrow().get(&p) {
        return Ok(m.clone());
    }
    let mətn = match std::fs::read(&p).ok().and_then(|b| String::from_utf8(b).ok()) {
        Some(m) => m,
        None => return Err(xəta_yer("ArqumentXətası", format!("\"{}\" oxunmadı", yol), yer, "ALQ-M001")),
    };
    let ad_ = p.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
    let mənbə = crate::xeta::Mənbə::yeni(&ad_, &mətn, Some(p.clone()));
    let mut x = crate::xeta::XətaToplayıcı::yeni();
    let ağac = crate::parser::ayır(mənbə, &mut x);
    if !x.uğurludur() {
        let fayl = p.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
        return Err(xəta_yer(
            "ArqumentXətası",
            format!("\"{}\" modulunda {} xəta var", fayl, x.xəta_sayı()),
            yer,
            "ALQ-M009",
        ));
    }
    let ağac: &'static crate::aac::Proqram = Box::leak(Box::new(ağac));
    let alt = i.qlobal.alt();
    i.elanları_qaldır(&ağac.gövdə, &alt)?;
    for c in &ağac.gövdə {
        if !elandır(c) {
            i.cümlə(c, &alt)?;
        } else {
            i.bəzə(c, &alt)?;
        }
    }
    let stem = p.file_stem().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
    let m = Rc::new(Modul { ad: std::cell::RefCell::new(ad(&stem)), üzvlər: std::cell::RefCell::new(alt.hamısı().into_iter().collect()), çağırışçı: None });
    i.fayl_modulları.borrow_mut().insert(p, m.clone());
    Ok(m)
}
