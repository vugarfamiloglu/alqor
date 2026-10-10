//! Operatorlar: hesab, müqayisə, bərabərlik; ədəd oxuma.

use super::deyerler::*;
use super::icraci::İcraçı;
use crate::xeta::Yer;
use num_bigint::BigInt;
use num_integer::Integer;
use num_traits::{FromPrimitive, Signed, ToPrimitive, Zero};
use std::cmp::Ordering;
use std::rc::Rc;

fn operator_metodu(op: &str) -> Option<&'static str> {
    Some(match op {
        "+" => "topla",
        "-" => "çıx",
        "*" => "vur",
        "/" => "böl",
        "%" => "qalıq",
        "**" => "qüvvət",
        _ => return None,
    })
}

pub fn onluqdan_tam(f: f64) -> Nəticə {
    if !f.is_finite() {
        return Err(xəta("ÇevrilməXətası", "sonsuz və ya ƏdədDeyil tam ədədə çevrilmir", "ALQ-R005"));
    }
    let t = f.trunc();
    if t.abs() < 9.2e18 {
        Ok(D::T(t as i64))
    } else {
        Ok(D::tam(BigInt::from_f64(t).unwrap_or_default()))
    }
}

/// Python `int(str, əsas)`
pub fn tam_oxu(s: &str, əsas: u32) -> Option<D> {
    let s = s.trim();
    let (mənfi, mut t) = match s.as_bytes().first() {
        Some(b'-') => (true, &s[1..]),
        Some(b'+') => (false, &s[1..]),
        _ => (false, s),
    };
    let ön = |t: &str, p: &str| t.len() >= 2 && t[..2].eq_ignore_ascii_case(p);
    if əsas == 16 && ön(t, "0x") || əsas == 2 && ön(t, "0b") || əsas == 8 && ön(t, "0o") {
        t = &t[2..];
    }
    if t.is_empty() || t.starts_with('_') || t.ends_with('_') || t.contains("__") {
        return None;
    }
    let t: String = t.chars().filter(|c| *c != '_').collect();
    if !t.chars().all(|c| c.is_digit(əsas)) {
        return None;
    }
    let n = BigInt::parse_bytes(t.as_bytes(), əsas)?;
    Some(D::tam(if mənfi { -n } else { n }))
}

/// Python `float(str)`
pub fn onluq_oxu(s: &str) -> Option<f64> {
    let t: String = s.trim().chars().filter(|c| *c != '_').collect();
    let l = t.to_ascii_lowercase();
    let l2 = l.trim_start_matches(['+', '-']);
    if l2 == "inf" || l2 == "infinity" {
        return Some(if l.starts_with('-') { f64::NEG_INFINITY } else { f64::INFINITY });
    }
    if l2 == "nan" {
        return Some(f64::NAN);
    }
    let b = t.as_bytes();
    let mut i = 0;
    if i < b.len() && (b[i] == b'+' || b[i] == b'-') {
        i += 1;
    }
    let r0 = i;
    while i < b.len() && b[i].is_ascii_digit() {
        i += 1;
    }
    let mut rəq = i - r0;
    if i < b.len() && b[i] == b'.' {
        i += 1;
        let r1 = i;
        while i < b.len() && b[i].is_ascii_digit() {
            i += 1;
        }
        rəq += i - r1;
    }
    if rəq == 0 {
        return None;
    }
    if i < b.len() && (b[i] == b'e' || b[i] == b'E') {
        i += 1;
        if i < b.len() && (b[i] == b'+' || b[i] == b'-') {
            i += 1;
        }
        let r2 = i;
        while i < b.len() && b[i].is_ascii_digit() {
            i += 1;
        }
        if i == r2 {
            return None;
        }
    }
    if i != b.len() {
        return None;
    }
    t.parse().ok()
}

fn böyük(d: &D) -> BigInt {
    d.böyük_tam().unwrap_or_default()
}

/// tam + onluq müqayisəsi (dəqiq)
pub fn ədəd_müq(a: &D, b: &D) -> Option<Ordering> {
    match (a, b) {
        (D::T(x), D::T(y)) => Some(x.cmp(y)),
        (D::O(x), D::O(y)) => x.partial_cmp(y),
        (D::O(_), _) => ədəd_müq(b, a).map(|o| o.reverse()),
        (_, D::O(f)) => {
            let f = *f;
            if f.is_nan() {
                return None;
            }
            if f.is_infinite() {
                return Some(if f > 0.0 { Ordering::Less } else { Ordering::Greater });
            }
            let x = böyük(a);
            if f.fract() == 0.0 {
                Some(x.cmp(&BigInt::from_f64(f).unwrap()))
            } else {
                let fl = BigInt::from_f64(f.floor()).unwrap();
                Some(if x <= fl { Ordering::Less } else { Ordering::Greater })
            }
        }
        _ => Some(böyük(a).cmp(&böyük(b))),
    }
}

/// Sıralama açarı müqayisəsi (`_sıralama_açarı`): ədədlər < mətnlər < digər
pub fn sıra_müq(a: &D, b: &D) -> Ordering {
    fn sinif(x: &D) -> u8 {
        match x {
            D::T(_) | D::BT(_) | D::O(_) | D::M(_) => 0,
            D::S(_) => 1,
            _ => 2,
        }
    }
    let (sa, sb) = (sinif(a), sinif(b));
    if sa != sb {
        return sa.cmp(&sb);
    }
    match sa {
        0 => ədəd_müq(a, b).unwrap_or(Ordering::Equal),
        1 => crate::elifba::əsas_açar(a.mətn_al().unwrap()).cmp(&crate::elifba::əsas_açar(b.mətn_al().unwrap())),
        _ => match (a, b) {
            (D::Kortej(x), D::Kortej(y)) => {
                for (p, q) in x.iter().zip(y.iter()) {
                    let r = sıra_müq(p, q);
                    if r != Ordering::Equal {
                        return r;
                    }
                }
                x.len().cmp(&y.len())
            }
            (D::Siyahı(x), D::Siyahı(y)) => {
                let (x, y) = (x.borrow(), y.borrow());
                for (p, q) in x.iter().zip(y.iter()) {
                    let r = sıra_müq(p, q);
                    if r != Ordering::Equal {
                        return r;
                    }
                }
                x.len().cmp(&y.len())
            }
            _ => ptr_id(a).cmp(&ptr_id(b)),
        },
    }
}

impl İcraçı {
    pub fn bərabərdir(&self, a: &D, b: &D) -> Nəticə<bool> {
        if let D::Nümunə(n) = a {
            if let Some(f) = n.sinif.metod_tap("bərabərdir") {
                let r = self.funksiya_çağır(&f.bağla(a.clone()), vec![b.clone()], vec![], None)?;
                return Ok(doğrudur(&r));
            }
        }
        if matches!(a, D::M(_)) != matches!(b, D::M(_)) {
            return Ok(false);
        }
        Ok(py_eq(a, b))
    }

    pub fn ikili_hesabla(&self, op: &str, a: &D, b: &D, yer: Option<Yer>) -> Nəticə {
        match op {
            "==" => return Ok(D::M(self.bərabərdir(a, b)?)),
            "!=" => return Ok(D::M(!self.bərabərdir(a, b)?)),
            _ => {}
        }
        if let D::Nümunə(n) = a {
            if let Some(m) = operator_metodu(op) {
                if let Some(f) = n.sinif.metod_tap(m) {
                    return self.funksiya_çağır(&f.bağla(a.clone()), vec![b.clone()], vec![], yer);
                }
            }
        }
        if matches!(op, "<" | ">" | "<=" | ">=" | "<=>") {
            return self.müqayisə(op, a, b, yer);
        }
        match a {
            D::S(x) => {
                if op == "+" {
                    return match b {
                        D::S(y) => {
                            let mut s = String::with_capacity(x.len() + y.len());
                            s.push_str(x);
                            s.push_str(y);
                            Ok(D::str(s))
                        }
                        _ => Err(xəta_yer("TipXətası", format!("`mətn` və `{}` toplanmır", tip_adı(b)), yer, "ALQ-T008")),
                    };
                }
                if op == "*" {
                    return match b {
                        D::T(n) => Ok(D::str(x.repeat((*n).max(0) as usize))),
                        _ => Err(xəta_yer("TipXətası", "mətn yalnız tam ədədə vurula bilər", yer, "ALQ-T008")),
                    };
                }
            }
            D::Siyahı(x) => {
                if op == "+" {
                    return match b {
                        D::Siyahı(y) => {
                            let mut v = x.borrow().clone();
                            v.extend(y.borrow().iter().cloned());
                            Ok(D::siyahı(v))
                        }
                        _ => Err(xəta_yer("TipXətası", format!("`siyahı` və `{}` toplanmır", tip_adı(b)), yer, "ALQ-T008")),
                    };
                }
                if op == "*" {
                    if let Some(n) = b.i64() {
                        let x = x.borrow();
                        let mut v = Vec::new();
                        for _ in 0..n.max(0) {
                            v.extend(x.iter().cloned());
                        }
                        return Ok(D::siyahı(v));
                    }
                }
            }
            D::Dəst(x) if matches!(op, "|" | "&" | "-" | "^") => {
                let D::Dəst(y) = b else {
                    return Err(xəta_yer("TipXətası", "dəst əməliyyatı dəst tələb edir", yer, "ALQ-T008"));
                };
                return Ok(D::dəst(dəst_op(op, &x.borrow(), &y.borrow())));
            }
            _ => {}
        }
        if !a.ədəddir() || !b.ədəddir() {
            return Err(xəta_yer(
                "TipXətası",
                format!("`{}` operatoru `{}` və `{}` tiplərinə tətbiq edilmir", op, tip_adı(a), tip_adı(b)),
                yer,
                "ALQ-T008",
            ));
        }
        self.ədəd_op(op, a, b, yer)
    }

    fn ədəd_op(&self, op: &str, a: &D, b: &D, yer: Option<Yer>) -> Nəticə {
        let onluq = matches!(a, D::O(_)) || matches!(b, D::O(_));
        let sıfır_xəta = || xəta_yer("BölməXətası", "sıfıra bölmək olmaz", yer, "ALQ-R001");
        match op {
            "+" | "-" | "*" => {
                if onluq {
                    let (x, y) = (a.onluq().unwrap(), b.onluq().unwrap());
                    return Ok(D::O(match op {
                        "+" => x + y,
                        "-" => x - y,
                        _ => x * y,
                    }));
                }
                if let (D::T(x), D::T(y)) = (a, b) {
                    let r = match op {
                        "+" => x.checked_add(*y),
                        "-" => x.checked_sub(*y),
                        _ => x.checked_mul(*y),
                    };
                    if let Some(r) = r {
                        return Ok(D::T(r));
                    }
                }
                let (x, y) = (böyük(a), böyük(b));
                Ok(D::tam(match op {
                    "+" => x + y,
                    "-" => x - y,
                    _ => x * y,
                }))
            }
            "/" => {
                let sıfır = match b {
                    D::O(f) => *f == 0.0,
                    _ => böyük(b).is_zero(),
                };
                if sıfır {
                    if onluq {
                        let x = a.onluq().unwrap();
                        return Ok(D::O(if x > 0.0 {
                            f64::INFINITY
                        } else if x < 0.0 {
                            f64::NEG_INFINITY
                        } else {
                            f64::NAN
                        }));
                    }
                    return Err(sıfır_xəta());
                }
                if !onluq {
                    if let (D::T(x), D::T(y)) = (a, b) {
                        if x.abs() < (1 << 53) && y.abs() < (1 << 53) {
                            return Ok(D::O(*x as f64 / *y as f64));
                        }
                    }
                    return Ok(D::O(böyük_böl(&böyük(a), &böyük(b))));
                }
                Ok(D::O(a.onluq().unwrap() / b.onluq().unwrap()))
            }
            "~/" => {
                let sıfır = match b {
                    D::O(f) => *f == 0.0,
                    _ => böyük(b).is_zero(),
                };
                if sıfır {
                    return Err(sıfır_xəta());
                }
                if onluq {
                    let (x, y) = (a.onluq().unwrap(), b.onluq().unwrap());
                    let n = (x.abs() / y.abs()).floor();
                    let n = if (x >= 0.0) == (y >= 0.0) { n } else { -n };
                    return onluqdan_tam(n);
                }
                if let (D::T(x), D::T(y)) = (a, b) {
                    if let Some(r) = x.checked_div(*y) {
                        return Ok(D::T(r));
                    }
                }
                let (x, y) = (böyük(a), böyük(b));
                Ok(D::tam(&x / &y))
            }
            "%" => {
                let sıfır = match b {
                    D::O(f) => *f == 0.0,
                    _ => böyük(b).is_zero(),
                };
                if sıfır {
                    return Err(sıfır_xəta());
                }
                if !onluq {
                    if let (D::T(x), D::T(y)) = (a, b) {
                        if x.abs() < (1 << 53) && y.abs() < (1 << 53) {
                            return Ok(D::T(x % y));
                        }
                    }
                    // Python: int(math.fmod(...)) — onluq dəqiqliyi ilə
                    let r = a.onluq().unwrap() % b.onluq().unwrap();
                    return onluqdan_tam(r);
                }
                let r = a.onluq().unwrap() % b.onluq().unwrap();
                if matches!(a, D::O(_)) {
                    Ok(D::O(r))
                } else {
                    onluqdan_tam(r)
                }
            }
            "**" => {
                if !onluq {
                    let y = böyük(b);
                    if !y.is_negative() {
                        let x = böyük(a);
                        let Some(e) = y.to_u32() else {
                            return Err(xəta_yer("DaşmaXətası", "qüvvət çox böyükdür", yer, "ALQ-R001"));
                        };
                        return Ok(D::tam(num_traits::pow(x, e as usize)));
                    }
                    let x = a.onluq().unwrap();
                    if x == 0.0 {
                        return Err(sıfır_xəta());
                    }
                    return Ok(D::O(x.powf(b.onluq().unwrap())));
                }
                let (x, y) = (a.onluq().unwrap(), b.onluq().unwrap());
                if x == 0.0 && y < 0.0 {
                    return Err(sıfır_xəta());
                }
                Ok(D::O(x.powf(y)))
            }
            "&" | "|" | "^" | "<<" | ">>" | ">>>" => {
                if onluq {
                    return Err(xəta_yer("TipXətası", "bit əməliyyatları tam ədəd tələb edir", yer, "ALQ-T008"));
                }
                let (x, y) = (böyük(a), böyük(b));
                Ok(D::tam(match op {
                    "&" => x & y,
                    "|" => x | y,
                    "^" => x ^ y,
                    "<<" => {
                        let n = y.to_usize().unwrap_or(0);
                        x << n
                    }
                    ">>" => {
                        let n = y.to_usize().unwrap_or(usize::MAX >> 1);
                        if n > 100000 {
                            if x.is_negative() {
                                BigInt::from(-1)
                            } else {
                                BigInt::zero()
                            }
                        } else {
                            x >> n
                        }
                    }
                    _ => {
                        let m = BigInt::from(1u8) << 64;
                        let x = x.mod_floor(&m);
                        x >> y.to_usize().unwrap_or(0).min(100000)
                    }
                }))
            }
            _ => Err(xəta_yer("DaxiliXəta", format!("naməlum operator `{}`", op), yer, "")),
        }
    }

    pub fn müqayisə(&self, op: &str, a: &D, b: &D, yer: Option<Yer>) -> Nəticə {
        if let D::Nümunə(n) = a {
            if let Some(f) = n.sinif.metod_tap("müqayisə") {
                let r = self.funksiya_çağır(&f.bağla(a.clone()), vec![b.clone()], vec![], yer)?;
                let k = match &r {
                    D::T(x) => x.signum(),
                    D::O(x) => {
                        if *x < 0.0 {
                            -1
                        } else if *x > 0.0 {
                            1
                        } else {
                            0
                        }
                    }
                    _ => 0,
                };
                if op == "<=>" {
                    return Ok(r);
                }
                return Ok(müq_nəticə(op, k));
            }
        }
        if let (D::S(x), D::S(y)) = (a, b) {
            let k = match crate::elifba::müqayisə(x, y) {
                Ordering::Less => -1,
                Ordering::Greater => 1,
                Ordering::Equal => 0,
            };
            return Ok(müq_nəticə(op, k));
        }
        if let (D::Dəst(x), D::Dəst(y)) = (a, b) {
            let (x, y) = (x.borrow(), y.borrow());
            let alt = x.iter().all(|k| y.contains(k));
            let üst = y.iter().all(|k| x.contains(k));
            match op {
                "<=" => return Ok(D::M(alt)),
                ">=" => return Ok(D::M(üst)),
                "<" => return Ok(D::M(alt && x.len() < y.len())),
                ">" => return Ok(D::M(üst && x.len() > y.len())),
                _ => {}
            }
        }
        if !a.ədəddir() || !b.ədəddir() {
            return Err(xəta_yer(
                "TipXətası",
                format!("`{}` və `{}` müqayisə edilmir", tip_adı(a), tip_adı(b)),
                yer,
                "ALQ-T008",
            ));
        }
        let k = match ədəd_müq(a, b) {
            Some(Ordering::Less) => -1,
            Some(Ordering::Greater) => 1,
            _ => 0,
        };
        Ok(müq_nəticə(op, k))
    }
}

fn müq_nəticə(op: &str, k: i64) -> D {
    match op {
        "<=>" => D::T(k),
        "<" => D::M(k < 0),
        ">" => D::M(k > 0),
        "<=" => D::M(k <= 0),
        _ => D::M(k >= 0),
    }
}

pub fn doğrudur(d: &D) -> bool {
    match d {
        D::M(b) => *b,
        D::Boş => false,
        D::T(i) => *i != 0,
        D::O(f) => *f != 0.0,
        D::S(s) => !s.is_empty(),
        D::Siyahı(l) => !l.borrow().is_empty(),
        D::Lüğət(l) => !l.borrow().is_empty(),
        D::Dəst(l) => !l.borrow().is_empty(),
        D::Kortej(l) => !l.is_empty(),
        _ => true,
    }
}

pub fn dəst_op(op: &str, x: &Dəst, y: &Dəst) -> Dəst {
    let mut r = Dəst::default();
    match op {
        "|" => {
            r.extend(x.iter().cloned());
            r.extend(y.iter().cloned());
        }
        "&" => r.extend(x.iter().filter(|k| y.contains(*k)).cloned()),
        "-" => r.extend(x.iter().filter(|k| !y.contains(*k)).cloned()),
        _ => {
            r.extend(x.iter().filter(|k| !y.contains(*k)).cloned());
            r.extend(y.iter().filter(|k| !x.contains(*k)).cloned());
        }
    }
    r
}

/// Böyük tamların dəqiq bölünməsi (təxmini)
fn böyük_böl(x: &BigInt, y: &BigInt) -> f64 {
    match (x.to_f64(), y.to_f64()) {
        (Some(a), Some(b)) if a.is_finite() && b.is_finite() => a / b,
        _ => {
            let q = x / y;
            q.to_f64().unwrap_or(f64::INFINITY)
        }
    }
}

pub fn tam_dəyər(d: &D) -> Option<BigInt> {
    d.böyük_tam()
}

#[allow(dead_code)]
pub fn rc_tam(b: BigInt) -> D {
    D::BT(Rc::new(b))
}
