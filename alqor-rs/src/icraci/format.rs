//! Şablon mətnlərində format (`{x:.2f}`) — Python format mini-dili.

use super::deyerler::*;
use super::eded::tam_oxu;
use super::icraci::İcraçı;
use num_bigint::BigInt;
use num_traits::{Signed, ToPrimitive};

pub fn formatla(i: &İcraçı, d: &D, f: Option<&str>) -> Nəticə<String> {
    let f = match f {
        None | Some("") => return mətnə(i, d),
        Some(f) => f,
    };
    let r = if f.ends_with(",az") {
        python_float(d).map(|n| {
            let əsas = if n.fract() == 0.0 { qrupla(&format!("{:.0}", n), ',') } else { qrupla(&format!("{:.2}", n), ',') };
            əsas.replace(',', "\u{a0}").replace('.', ",")
        })
    } else if f == "," {
        py_format(d, ",")
    } else if f.len() > 1 && f.starts_with('.') && f[1..].bytes().all(|b| b.is_ascii_digit()) {
        let p: usize = f[1..].parse().unwrap_or(6);
        python_float(d).map(|n| sabit(n, p))
    } else if matches!(f, "x" | "X" | "b" | "o") {
        python_int(d).and_then(|n| py_format(&D::tam(n), f))
    } else {
        py_format(d, f)
    };
    match r {
        Some(s) => Ok(s),
        None => mətnə(i, d),
    }
}

/// Python `float(x)`
fn python_float(d: &D) -> Option<f64> {
    match d {
        D::S(s) => super::eded::onluq_oxu(s),
        _ => d.onluq(),
    }
}

/// Python `int(x)`
fn python_int(d: &D) -> Option<BigInt> {
    match d {
        D::O(f) if f.is_finite() => num_traits::FromPrimitive::from_f64(f.trunc()),
        D::S(s) => tam_oxu(s, 10).and_then(|x| x.böyük_tam()),
        _ => d.böyük_tam(),
    }
}

pub fn qrupla(s: &str, ayırıcı: char) -> String {
    let (mənfi, s) = match s.strip_prefix('-') {
        Some(x) => (true, x),
        None => (false, s),
    };
    let (tam, qalan) = match s.find(|c: char| !c.is_ascii_digit()) {
        Some(i) => (&s[..i], &s[i..]),
        None => (s, ""),
    };
    let mut n = String::new();
    for (k, c) in tam.chars().enumerate() {
        if k > 0 && (tam.len() - k) % 3 == 0 {
            n.push(ayırıcı);
        }
        n.push(c);
    }
    format!("{}{}{}", if mənfi { "-" } else { "" }, n, qalan)
}

fn sabit(x: f64, p: usize) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf".into() } else { "-inf".into() };
    }
    format!("{:.*}", p, x)
}

fn eksp(x: f64, p: usize) -> String {
    let s = format!("{:.*e}", p, x);
    let (m, e) = s.split_once('e').unwrap();
    let e: i32 = e.parse().unwrap();
    format!("{}e{}{:02}", m, if e < 0 { '-' } else { '+' }, e.abs())
}

fn ümumi(x: f64, p: usize, alt: bool, repr_növ: bool) -> String {
    let p = p.max(1);
    if x == 0.0 {
        let z = if alt { format!("0.{}", "0".repeat(p - 1)) } else if repr_növ { "0.0".into() } else { "0".into() };
        return z;
    }
    let s = format!("{:.*e}", p - 1, x);
    let e: i32 = s.split_once('e').unwrap().1.parse().unwrap();
    if e >= -4 && e < p as i32 {
        let mut s = format!("{:.*}", (p as i32 - 1 - e).max(0) as usize, x);
        if !alt && s.contains('.') {
            s = s.trim_end_matches('0').trim_end_matches('.').to_string();
        }
        if repr_növ && !s.contains('.') {
            s.push_str(".0");
        }
        s
    } else {
        let mut s = eksp(x, p - 1);
        if !alt {
            let (m, ex) = s.split_once('e').unwrap();
            let m = if m.contains('.') { m.trim_end_matches('0').trim_end_matches('.') } else { m };
            s = format!("{}e{}", m, ex);
        }
        s
    }
}

struct Spec {
    doldur: char,
    düz: Option<char>,
    işarə: char,
    alt: bool,
    en: usize,
    qrup: Option<char>,
    dəq: Option<usize>,
    tip: Option<char>,
}

fn spec_oxu(s: &str) -> Option<Spec> {
    let c: Vec<char> = s.chars().collect();
    let mut i = 0;
    let mut sp = Spec { doldur: ' ', düz: None, işarə: '-', alt: false, en: 0, qrup: None, dəq: None, tip: None };
    let düzlər = ['<', '>', '=', '^'];
    if c.len() >= 2 && düzlər.contains(&c[1]) {
        sp.doldur = c[0];
        sp.düz = Some(c[1]);
        i = 2;
    } else if !c.is_empty() && düzlər.contains(&c[0]) {
        sp.düz = Some(c[0]);
        i = 1;
    }
    if i < c.len() && matches!(c[i], '+' | '-' | ' ') {
        sp.işarə = c[i];
        i += 1;
    }
    if i < c.len() && c[i] == 'z' {
        i += 1;
    }
    if i < c.len() && c[i] == '#' {
        sp.alt = true;
        i += 1;
    }
    if i < c.len() && c[i] == '0' {
        if sp.düz.is_none() {
            sp.doldur = '0';
            sp.düz = Some('=');
        }
        i += 1;
    }
    let b = i;
    while i < c.len() && c[i].is_ascii_digit() {
        i += 1;
    }
    if i > b {
        sp.en = c[b..i].iter().collect::<String>().parse().ok()?;
    }
    if i < c.len() && matches!(c[i], ',' | '_') {
        sp.qrup = Some(c[i]);
        i += 1;
    }
    if i < c.len() && c[i] == '.' {
        i += 1;
        let b = i;
        while i < c.len() && c[i].is_ascii_digit() {
            i += 1;
        }
        if i == b {
            return None;
        }
        sp.dəq = Some(c[b..i].iter().collect::<String>().parse().ok()?);
    }
    if i < c.len() {
        if !"bcdeEfFgGnosxX%".contains(c[i]) {
            return None;
        }
        sp.tip = Some(c[i]);
        i += 1;
    }
    if i != c.len() {
        return None;
    }
    Some(sp)
}

fn yerləşdir(s: &str, ön: &str, sp: &Spec, standart: char) -> String {
    let uz = ön.chars().count() + s.chars().count();
    if uz >= sp.en {
        return format!("{ön}{s}");
    }
    let boş = sp.en - uz;
    let d = |n: usize| sp.doldur.to_string().repeat(n);
    match sp.düz.unwrap_or(standart) {
        '<' => format!("{ön}{s}{}", d(boş)),
        '>' => format!("{}{ön}{s}", d(boş)),
        '=' => format!("{ön}{}{s}", d(boş)),
        _ => {
            let sol = boş / 2;
            format!("{}{ön}{s}{}", d(sol), d(boş - sol))
        }
    }
}

/// Python `format(dəyər, spec)`; uyğunsuzluqda `None`.
pub fn py_format(d: &D, spec: &str) -> Option<String> {
    let sp = spec_oxu(spec)?;
    match d {
        D::S(s) => {
            if !matches!(sp.tip, None | Some('s')) || sp.işarə != '-' || sp.alt || sp.düz == Some('=') || sp.qrup.is_some() {
                if sp.düz == Some('=') && sp.doldur == '0' && sp.işarə == '-' && !sp.alt && sp.qrup.is_none() && matches!(sp.tip, None | Some('s')) {
                    // `0` bayrağı mətndə: sola düzləndirmə
                } else {
                    return None;
                }
            }
            let s: String = match sp.dəq {
                Some(p) => s.chars().take(p).collect(),
                None => s.to_string(),
            };
            let sp2 = Spec { düz: if sp.düz == Some('=') { Some('<') } else { sp.düz }, ..sp };
            Some(yerləşdir(&s, "", &sp2, '<'))
        }
        D::T(_) | D::BT(_) | D::M(_) => {
            let n = d.böyük_tam()?;
            match sp.tip {
                None | Some('d') | Some('n') | Some('b') | Some('o') | Some('x') | Some('X') | Some('c') => {
                    if sp.dəq.is_some() {
                        return None;
                    }
                    let mənfi = n.is_negative();
                    let m = n.abs();
                    let (mut gövdə, prefiks) = match sp.tip {
                        Some('b') => (m.to_str_radix(2), "0b"),
                        Some('o') => (m.to_str_radix(8), "0o"),
                        Some('x') => (m.to_str_radix(16), "0x"),
                        Some('X') => (m.to_str_radix(16).to_uppercase(), "0X"),
                        Some('c') => (char::from_u32(m.to_u32()?)?.to_string(), ""),
                        _ => (m.to_string(), ""),
                    };
                    if let Some(q) = sp.qrup {
                        if matches!(sp.tip, Some('b') | Some('o') | Some('x') | Some('X')) {
                            if q == ',' {
                                return None;
                            }
                            let c: Vec<char> = gövdə.chars().collect();
                            let mut n = String::new();
                            for (k, ch) in c.iter().enumerate() {
                                if k > 0 && (c.len() - k) % 4 == 0 {
                                    n.push('_');
                                }
                                n.push(*ch);
                            }
                            gövdə = n;
                        } else {
                            gövdə = qrupla(&gövdə, q);
                        }
                    }
                    let mut ön = String::from(if mənfi {
                        "-"
                    } else if sp.işarə == '+' {
                        "+"
                    } else if sp.işarə == ' ' {
                        " "
                    } else {
                        ""
                    });
                    if sp.alt {
                        ön.push_str(prefiks);
                    }
                    Some(yerləşdir(&gövdə, &ön, &sp, '>'))
                }
                _ => onluq_format(n.to_f64()?, &sp),
            }
        }
        D::O(f) => {
            if matches!(sp.tip, Some('d') | Some('b') | Some('o') | Some('x') | Some('X') | Some('c')) {
                return None;
            }
            onluq_format(*f, &sp)
        }
        _ => None,
    }
}

fn onluq_format(x: f64, sp: &Spec) -> Option<String> {
    let mənfi = x.is_sign_negative() && !x.is_nan();
    let m = x.abs();
    let böyük = matches!(sp.tip, Some('E') | Some('F') | Some('G'));
    let mut gövdə = if !m.is_finite() {
        let s = if m.is_nan() { "nan" } else { "inf" };
        let s = if böyük { s.to_uppercase() } else { s.to_string() };
        if sp.tip == Some('%') {
            format!("{s}%")
        } else {
            s
        }
    } else {
        match sp.tip {
            Some('f') | Some('F') => sabit(m, sp.dəq.unwrap_or(6)),
            Some('%') => format!("{}%", sabit(m * 100.0, sp.dəq.unwrap_or(6))),
            Some('e') | Some('E') => {
                let s = eksp(m, sp.dəq.unwrap_or(6));
                if böyük {
                    s.to_uppercase()
                } else {
                    s
                }
            }
            Some('g') | Some('G') | Some('n') => {
                let s = ümumi(m, sp.dəq.unwrap_or(6), sp.alt, false);
                if böyük {
                    s.to_uppercase()
                } else {
                    s
                }
            }
            _ => match sp.dəq {
                None => onluq_repr(m),
                Some(p) => ümumi(m, p, sp.alt, true),
            },
        }
    };
    if let Some(q) = sp.qrup {
        let (t, qalan) = match gövdə.find(|c: char| !c.is_ascii_digit()) {
            Some(i) => (gövdə[..i].to_string(), gövdə[i..].to_string()),
            None => (gövdə.clone(), String::new()),
        };
        gövdə = qrupla(&t, q) + &qalan;
    }
    let ön = if mənfi {
        "-"
    } else if sp.işarə == '+' {
        "+"
    } else if sp.işarə == ' ' {
        " "
    } else {
        ""
    };
    Some(yerləşdir(&gövdə, ön, sp, '>'))
}
