//! Standart modullar: riyaziyyat, mətn, təsadüfi, vaxt, fayl, qovluq, yol,
//! json, naxış, sistem, jurnal, paralel, sap (konsol — konsol.rs).

use super::cagiris::*;
use super::deyerler::*;
use super::eded::ədəd_müq;
use super::icraci::İcraçı;
use super::kitabxana::{mətn_yoxla, tam_yoxla};
use super::metodlar::{ilk_min, sıra_sayı, yazıyla};
use crate::elifba as E;
use num_bigint::BigInt;
use num_integer::Integer;
use num_traits::{Signed, ToPrimitive, Zero};
use std::cmp::Ordering;
use std::path::{Path, PathBuf};
use std::rc::Rc;

// ═══════════════════════════════════════════════════════════════════════
//  Mersenne Twister (Python `random` ilə eyni ardıcıllıq)
// ═══════════════════════════════════════════════════════════════════════

pub struct MT {
    mt: [u32; 624],
    i: usize,
}

impl MT {
    fn init(s: u32) -> MT {
        let mut mt = [0u32; 624];
        mt[0] = s;
        for i in 1..624 {
            mt[i] = 1812433253u32.wrapping_mul(mt[i - 1] ^ (mt[i - 1] >> 30)).wrapping_add(i as u32);
        }
        MT { mt, i: 624 }
    }
    pub fn toxum(key: &[u32]) -> MT {
        let mut m = MT::init(19650218);
        let n = 624;
        let (mut i, mut j) = (1usize, 0usize);
        let mut k = n.max(key.len());
        while k > 0 {
            m.mt[i] = (m.mt[i] ^ (m.mt[i - 1] ^ (m.mt[i - 1] >> 30)).wrapping_mul(1664525))
                .wrapping_add(key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= n {
                m.mt[0] = m.mt[n - 1];
                i = 1;
            }
            if j >= key.len() {
                j = 0;
            }
            k -= 1;
        }
        k = n - 1;
        while k > 0 {
            m.mt[i] = (m.mt[i] ^ (m.mt[i - 1] ^ (m.mt[i - 1] >> 30)).wrapping_mul(1566083941)).wrapping_sub(i as u32);
            i += 1;
            if i >= n {
                m.mt[0] = m.mt[n - 1];
                i = 1;
            }
            k -= 1;
        }
        m.mt[0] = 0x80000000;
        m
    }
    pub fn tamdan(n: &BigInt) -> MT {
        let n = n.abs();
        let mut key: Vec<u32> = n.to_u32_digits().1;
        if key.is_empty() {
            key.push(0);
        }
        MT::toxum(&key)
    }
    pub fn təsadüfi() -> MT {
        let x = super::platforma::entropiya();
        MT::toxum(&[x as u32, (x >> 32) as u32, (x >> 64) as u32, (x >> 96) as u32])
    }
    pub fn növbəti(&mut self) -> u32 {
        if self.i >= 624 {
            for k in 0..624 {
                let y = (self.mt[k] & 0x80000000) | (self.mt[(k + 1) % 624] & 0x7fffffff);
                let mut v = self.mt[(k + 397) % 624] ^ (y >> 1);
                if y & 1 != 0 {
                    v ^= 0x9908b0df;
                }
                self.mt[k] = v;
            }
            self.i = 0;
        }
        let mut y = self.mt[self.i];
        self.i += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }
    pub fn random(&mut self) -> f64 {
        let a = (self.növbəti() >> 5) as f64;
        let b = (self.növbəti() >> 6) as f64;
        (a * 67108864.0 + b) / 9007199254740992.0
    }
    pub fn bitlər(&mut self, k: u64) -> BigInt {
        if k <= 32 {
            return BigInt::from(self.növbəti() >> (32 - k));
        }
        let mut söz = vec![];
        let mut q = k;
        while q > 0 {
            let r = self.növbəti();
            söz.push(if q < 32 { r >> (32 - q) } else { r });
            q = q.saturating_sub(32);
        }
        BigInt::from_slice(num_bigint::Sign::Plus, &söz)
    }
    pub fn aşağı(&mut self, n: &BigInt) -> BigInt {
        if n.is_zero() {
            return BigInt::zero();
        }
        let k = n.bits();
        loop {
            let r = self.bitlər(k);
            if &r < n {
                return r;
            }
        }
    }
    pub fn aşağı_us(&mut self, n: usize) -> usize {
        self.aşağı(&BigInt::from(n)).to_usize().unwrap()
    }
    pub fn qarışdır(&mut self, v: &mut [D]) {
        for i in (1..v.len()).rev() {
            let j = self.aşağı_us(i + 1);
            v.swap(i, j);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Köməkçilər
// ═══════════════════════════════════════════════════════════════════════

type F = Box<dyn Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə>;

fn D_(a: &str, min: usize, maks: Option<usize>, f: F) -> D {
    D::Daxili(Rc::new(Daxili { ad: ad(a), f, min, maks }))
}

fn ədəd(d: &D, ad_: &str) -> Nəticə<f64> {
    match d {
        D::T(_) | D::BT(_) | D::O(_) | D::M(_) => Ok(d.onluq().unwrap()),
        _ => Err(xəta("TipXətası", format!("`{}` ədəd gözləyir, `{}` gəlib", ad_, tip_adı(d)), "ALQ-T004")),
    }
}

fn riyazi_xəta() -> Siqnal {
    xəta("RiyaziXəta", "riyazi tətbiq sahəsindən kənar dəyər", "ALQ-R001")
}

fn r1(a: &str, f: fn(f64) -> f64) -> D {
    let n = a.to_string();
    D_(a, 1, Some(1), Box::new(move |_, x, _| {
        let v = ədəd(&x[0], &n)?;
        let r = f(v);
        if r.is_nan() && !v.is_nan() {
            return Err(riyazi_xəta());
        }
        Ok(D::O(r))
    }))
}

pub fn yerli_ədəd(n: f64, rəqəm: Option<usize>) -> String {
    let r = rəqəm.unwrap_or(if n.fract() == 0.0 { 0 } else { 2 });
    let s = super::format::qrupla(&format!("{:.*}", r, n), ',');
    match s.split_once('.') {
        Some((t, k)) => format!("{},{}", t.replace(',', "\u{a0}"), k),
        None => s.replace(',', "\u{a0}"),
    }
}

fn şəkilçi(söz: &str, ş: &str) -> String {
    let saitlər: Vec<char> = E::kiçiyə(söz).chars().filter(|c| E::saitdir(*c)).collect();
    let qalın = saitlər.last().map(|c| E::qalın(*c)).unwrap_or(false);
    let r = match ş {
        "lar" | "lər" => if qalın { "lar" } else { "lər" },
        "da" => if qalın { "da" } else { "də" },
        "dan" => if qalın { "dan" } else { "dən" },
        "a" => if qalın { "a" } else { "ə" },
        x => x,
    };
    format!("{söz}{r}")
}

fn sadədir(n: &BigInt) -> bool {
    if n < &BigInt::from(2) {
        return false;
    }
    if n < &BigInt::from(4) {
        return true;
    }
    if n.is_even() {
        return false;
    }
    let mut i = BigInt::from(3);
    while &(&i * &i) <= n {
        if (n % &i).is_zero() {
            return false;
        }
        i += 2;
    }
    true
}

fn sıralı_ədədlər(i: &İcraçı, k: &D) -> Nəticə<Vec<D>> {
    let mut s = i.siyahıya(k, None)?;
    s.sort_by(|a, b| ədəd_müq(a, b).unwrap_or(Ordering::Equal));
    Ok(s)
}

fn py_sum(i: &İcraçı, a: &[D]) -> Nəticə {
    let mut s = D::T(0);
    for x in a {
        s = i.ikili_hesabla("+", &s, x, None)?;
    }
    Ok(s)
}

fn dispersiya(i: &İcraçı, k: &D) -> Nəticə<f64> {
    let s = i.siyahıya(k, None)?;
    if s.is_empty() {
        return Ok(0.0);
    }
    let o = i.ikili_hesabla("/", &py_sum(i, &s)?, &D::T(s.len() as i64), None)?.onluq().unwrap_or(0.0);
    let mut c = 0.0;
    for x in &s {
        let v = x.onluq().unwrap_or(0.0) - o;
        c += v * v;
    }
    Ok(c / s.len() as f64)
}

// ── Vaxt ───────────────────────────────────────────────────────────────

pub struct YerliVaxt {
    pub il: i32,
    pub ay: u32,
    pub gün: u32,
    pub saat: u32,
    pub dəq: u32,
    pub san: u32,
    pub həftə_günü: u32, // 0 = bazar ertəsi
}

pub fn yerli_vaxt(möhür: Option<i64>) -> YerliVaxt {
    let t = möhür.unwrap_or_else(|| super::platforma::indi_san() as i64);
    let (il, ay, gün, saat, dəq, san, həftə_günü) = super::platforma::yerli_vaxt(t);
    YerliVaxt { il, ay, gün, saat, dəq, san, həftə_günü }
}

pub fn vaxt_formatla(f: &str, möhür: Option<i64>) -> String {
    let t = yerli_vaxt(möhür);
    f.replace("YYYY", &format!("{:04}", t.il))
        .replace("MM", &format!("{:02}", t.ay))
        .replace("DD", &format!("{:02}", t.gün))
        .replace("HH", &format!("{:02}", t.saat))
        .replace("mm", &format!("{:02}", t.dəq))
        .replace("ss", &format!("{:02}", t.san))
}

const AYLAR: [&str; 12] =
    ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const GÜNLƏR: [&str; 7] = ["bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə", "bazar"];

fn möhür() -> f64 {
    super::platforma::indi_san()
}

fn yat(ms: f64) {
    super::platforma::yat(ms)
}

// ── Fayl ───────────────────────────────────────────────────────────────

fn fayl_oxu(y: &str) -> Nəticə<String> {
    match std::fs::read(y) {
        Ok(b) => match String::from_utf8(b) {
            Ok(s) => Ok(s.replace("\r\n", "\n").replace('\r', "\n")),
            Err(_) => Err(xəta("KodlaşdırmaXətası", format!("\"{}\" faylı UTF-8 deyil", y), "ALQ-L001")),
        },
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            Err(xəta("FaylTapılmadıXətası", format!("\"{}\" faylı tapılmadı", y), "ALQ-R009"))
        }
        Err(e) if e.kind() == std::io::ErrorKind::PermissionDenied => {
            Err(xəta("İcazəXətası", format!("\"{}\" faylını oxumaq icazəsi yoxdur", y), "ALQ-R012"))
        }
        Err(e) => Err(xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009")),
    }
}

fn io_xəta(e: std::io::Error, y: &str) -> Siqnal {
    match e.kind() {
        std::io::ErrorKind::NotFound => xəta("FaylTapılmadıXətası", format!("\"{}\" faylı tapılmadı", y), "ALQ-R009"),
        std::io::ErrorKind::PermissionDenied => xəta("İcazəXətası", format!("\"{}\" icazə yoxdur", y), "ALQ-R012"),
        _ => xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"),
    }
}

fn fayl_yaz(i: &İcraçı, y: &str, m: &D) -> Nəticə {
    let s = mətnə(i, m)?;
    match std::fs::write(y, s) {
        Ok(()) => Ok(D::Boş),
        Err(e) if e.kind() == std::io::ErrorKind::PermissionDenied => {
            Err(xəta("İcazəXətası", format!("\"{}\" faylına yazmaq icazəsi yoxdur", y), "ALQ-R012"))
        }
        Err(e) => Err(io_xəta(e, y)),
    }
}

/// Python `os.path.normpath`
pub fn normpath(p: &str) -> String {
    if p.is_empty() {
        return ".".into();
    }
    let mütləq = p.starts_with('/');
    let mut h: Vec<&str> = vec![];
    for x in p.split('/') {
        match x {
            "" | "." => {}
            ".." => {
                if !h.is_empty() && *h.last().unwrap() != ".." {
                    h.pop();
                } else if !mütləq {
                    h.push("..");
                }
            }
            x => h.push(x),
        }
    }
    let s = h.join("/");
    let s = if mütləq { format!("/{s}") } else { s };
    if s.is_empty() {
        ".".into()
    } else {
        s
    }
}

fn yol_adı(p: &str) -> String {
    let p = p.trim_end_matches('/');
    p.rsplit('/').next().unwrap_or("").to_string()
}

fn yol_uzantı(p: &str) -> String {
    let a = yol_adı(p);
    match a.rfind('.') {
        Some(k) if k > 0 && k < a.len() - 1 => a[k..].to_string(),
        _ => String::new(),
    }
}

fn yol_qovluq(p: &str) -> String {
    let p2 = p.trim_end_matches('/');
    match p2.rfind('/') {
        Some(0) => "/".into(),
        Some(k) => p2[..k].to_string(),
        None => ".".into(),
    }
}

fn nisbi(baza: &str, hədəf: &str) -> String {
    let abs = |p: &str| {
        let q = if p.starts_with('/') {
            p.to_string()
        } else {
            format!("{}/{}", std::env::current_dir().map(|d| d.display().to_string()).unwrap_or_default(), p)
        };
        normpath(&q)
    };
    let (a, b) = (abs(baza), abs(hədəf));
    let a: Vec<&str> = a.split('/').filter(|x| !x.is_empty()).collect();
    let b: Vec<&str> = b.split('/').filter(|x| !x.is_empty()).collect();
    let ortaq = a.iter().zip(b.iter()).take_while(|(x, y)| x == y).count();
    let mut h: Vec<&str> = vec![".."; a.len() - ortaq];
    h.extend(&b[ortaq..]);
    if h.is_empty() {
        ".".into()
    } else {
        h.join("/")
    }
}

// ── JSON ───────────────────────────────────────────────────────────────

struct JsonOxu<'a> {
    s: &'a [u8],
    m: &'a str,
    i: usize,
}

impl<'a> JsonOxu<'a> {
    fn xəta(&self, msg: &str) -> Siqnal {
        let s = self.m.as_bytes()[..self.i.min(self.m.len())].iter().filter(|b| **b == b'\n').count() + 1;
        xəta("JSONXətası", format!("JSON formatı pozulub (sətir {}): {}", s, msg), "ALQ-R005")
    }
    fn boşluq(&mut self) {
        while self.i < self.s.len() && b" \t\n\r".contains(&self.s[self.i]) {
            self.i += 1;
        }
    }
    fn dəyər(&mut self) -> Nəticə {
        self.boşluq();
        let Some(&c) = self.s.get(self.i) else { return Err(self.xəta("Expecting value")) };
        match c {
            b'{' => {
                self.i += 1;
                let mut l = Lüğət::default();
                self.boşluq();
                if self.s.get(self.i) == Some(&b'}') {
                    self.i += 1;
                    return Ok(D::lüğət(l));
                }
                loop {
                    self.boşluq();
                    if self.s.get(self.i) != Some(&b'"') {
                        return Err(self.xəta("Expecting property name enclosed in double quotes"));
                    }
                    let k = self.mətn()?;
                    self.boşluq();
                    if self.s.get(self.i) != Some(&b':') {
                        return Err(self.xəta("Expecting ':' delimiter"));
                    }
                    self.i += 1;
                    let v = self.dəyər()?;
                    l.insert(Açar(D::str(k)), v);
                    self.boşluq();
                    match self.s.get(self.i) {
                        Some(b',') => self.i += 1,
                        Some(b'}') => {
                            self.i += 1;
                            return Ok(D::lüğət(l));
                        }
                        _ => return Err(self.xəta("Expecting ',' delimiter")),
                    }
                }
            }
            b'[' => {
                self.i += 1;
                let mut a = vec![];
                self.boşluq();
                if self.s.get(self.i) == Some(&b']') {
                    self.i += 1;
                    return Ok(D::siyahı(a));
                }
                loop {
                    a.push(self.dəyər()?);
                    self.boşluq();
                    match self.s.get(self.i) {
                        Some(b',') => self.i += 1,
                        Some(b']') => {
                            self.i += 1;
                            return Ok(D::siyahı(a));
                        }
                        _ => return Err(self.xəta("Expecting ',' delimiter")),
                    }
                }
            }
            b'"' => Ok(D::str(self.mətn()?)),
            _ => {
                let r = &self.m[self.i..];
                for (söz, d) in [("true", D::M(true)), ("false", D::M(false)), ("null", D::Boş), ("NaN", D::O(f64::NAN)), ("Infinity", D::O(f64::INFINITY)), ("-Infinity", D::O(f64::NEG_INFINITY))] {
                    if r.starts_with(söz) {
                        self.i += söz.len();
                        return Ok(d);
                    }
                }
                let b = self.s;
                let mut j = self.i;
                if j < b.len() && b[j] == b'-' {
                    j += 1;
                }
                let r0 = j;
                if j < b.len() && b[j] == b'0' {
                    j += 1;
                } else {
                    while j < b.len() && b[j].is_ascii_digit() {
                        j += 1;
                    }
                }
                if j == r0 {
                    return Err(self.xəta("Expecting value"));
                }
                let mut onluq = false;
                if j + 1 < b.len() && b[j] == b'.' && b[j + 1].is_ascii_digit() {
                    onluq = true;
                    j += 1;
                    while j < b.len() && b[j].is_ascii_digit() {
                        j += 1;
                    }
                }
                if j < b.len() && (b[j] == b'e' || b[j] == b'E') {
                    let mut k = j + 1;
                    if k < b.len() && (b[k] == b'+' || b[k] == b'-') {
                        k += 1;
                    }
                    if k < b.len() && b[k].is_ascii_digit() {
                        while k < b.len() && b[k].is_ascii_digit() {
                            k += 1;
                        }
                        onluq = true;
                        j = k;
                    }
                }
                let t = &self.m[self.i..j];
                self.i = j;
                if onluq {
                    Ok(D::O(t.parse().unwrap_or(0.0)))
                } else {
                    Ok(D::tam(t.parse::<BigInt>().unwrap_or_default()))
                }
            }
        }
    }
    fn mətn(&mut self) -> Nəticə<String> {
        self.i += 1;
        let mut n: Vec<u16> = vec![];
        let mut out = String::new();
        loop {
            let Some(&c) = self.s.get(self.i) else { return Err(self.xəta("Unterminated string starting at")) };
            match c {
                b'"' => {
                    self.i += 1;
                    if !n.is_empty() {
                        out.push_str(&String::from_utf16_lossy(&n));
                    }
                    return Ok(out);
                }
                b'\\' => {
                    let e = *self.s.get(self.i + 1).unwrap_or(&0);
                    self.i += 2;
                    let ch = match e {
                        b'"' => '"',
                        b'\\' => '\\',
                        b'/' => '/',
                        b'b' => '\u{8}',
                        b'f' => '\u{c}',
                        b'n' => '\n',
                        b'r' => '\r',
                        b't' => '\t',
                        b'u' => {
                            let h = self.m.get(self.i..self.i + 4).unwrap_or("");
                            let v = u16::from_str_radix(h, 16).map_err(|_| self.xəta("Invalid \\uXXXX escape"))?;
                            self.i += 4;
                            n.push(v);
                            continue;
                        }
                        _ => return Err(self.xəta("Invalid \\escape")),
                    };
                    if !n.is_empty() {
                        out.push_str(&String::from_utf16_lossy(&n));
                        n.clear();
                    }
                    out.push(ch);
                }
                c if c < 0x20 => return Err(self.xəta("Invalid control character at")),
                _ => {
                    if !n.is_empty() {
                        out.push_str(&String::from_utf16_lossy(&n));
                        n.clear();
                    }
                    let rest = &self.m[self.i..];
                    let ch = rest.chars().next().unwrap();
                    out.push(ch);
                    self.i += ch.len_utf8();
                }
            }
        }
    }
}

/// Python `json.loads` xətası kimi: (mesaj, simvol mövqeyi)
pub fn json_oxu_mövqe(m: &str) -> Result<D, (String, usize)> {
    let mut p = JsonOxu { s: m.as_bytes(), m, i: 0 };
    let r = p.dəyər().and_then(|d| {
        p.boşluq();
        if p.i < m.len() {
            return Err(p.xəta("Extra data"));
        }
        Ok(d)
    });
    r.map_err(|e| {
        let mesaj = match e {
            Siqnal::Xəta(x) => x.mesaj.split_once("): ").map(|(_, b)| b.to_string()).unwrap_or(x.mesaj),
            _ => String::new(),
        };
        (mesaj, m.char_indices().take_while(|(b, _)| *b < p.i).count())
    })
}

pub fn json_oxu(m: &str) -> Nəticə {
    let mut p = JsonOxu { s: m.as_bytes(), m, i: 0 };
    let d = p.dəyər()?;
    p.boşluq();
    if p.i < m.len() {
        return Err(p.xəta("Extra data"));
    }
    Ok(d)
}

fn json_mətn(s: &str) -> String {
    let mut r = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => r.push_str("\\\""),
            '\\' => r.push_str("\\\\"),
            '\n' => r.push_str("\\n"),
            '\r' => r.push_str("\\r"),
            '\t' => r.push_str("\\t"),
            '\u{8}' => r.push_str("\\b"),
            '\u{c}' => r.push_str("\\f"),
            c if (c as u32) < 0x20 => r.push_str(&format!("\\u{:04x}", c as u32)),
            c => r.push(c),
        }
    }
    r.push('"');
    r
}

pub fn json_yaz(i: &İcraçı, d: &D, gözəl: bool, dər: usize) -> Nəticə<String> {
    let ara = if gözəl { format!("\n{}", "  ".repeat(dər + 1)) } else { String::new() };
    let son = if gözəl { format!("\n{}", "  ".repeat(dər)) } else { String::new() };
    let ayır = if gözəl { format!(",{ara}") } else { ", ".into() };
    Ok(match d {
        D::Boş => "null".into(),
        D::M(b) => if *b { "true".into() } else { "false".into() },
        D::T(_) | D::BT(_) => py_repr(d),
        D::O(f) => {
            if f.is_nan() {
                "NaN".into()
            } else if f.is_infinite() {
                if *f > 0.0 { "Infinity".into() } else { "-Infinity".into() }
            } else {
                onluq_repr(*f)
            }
        }
        D::S(s) => json_mətn(s),
        D::SD(s) => json_mətn(&s.ad),
        D::Bayt(b) => json_mətn(&super::metodlar::base64_kodla(b)),
        D::Siyahı(_) | D::Kortej(_) | D::Dəst(_) | D::Diapazon(_) => {
            let el = i.siyahıya(d, None)?;
            if el.is_empty() {
                return Ok("[]".into());
            }
            let mut h = vec![];
            for x in &el {
                h.push(json_yaz(i, x, gözəl, dər + 1)?);
            }
            format!("[{ara}{}{son}]", h.join(&ayır))
        }
        D::Lüğət(_) | D::Nümunə(_) => {
            let c: Vec<(String, D)> = match d {
                D::Lüğət(l) => l.borrow().iter().map(|(k, v)| (py_str_sadə(&k.0), v.clone())).collect(),
                D::Nümunə(n) => n.sahələr.borrow().iter().map(|(k, v)| (k.to_string(), v.clone())).collect(),
                _ => unreachable!(),
            };
            if c.is_empty() {
                return Ok("{}".into());
            }
            let mut h = vec![];
            for (k, v) in &c {
                h.push(format!("{}: {}", json_mətn(k), json_yaz(i, v, gözəl, dər + 1)?));
            }
            format!("{{{ara}{}{son}}}", h.join(&ayır))
        }
        x => {
            return Err(xəta(
                "TipXətası",
                format!("Object of type {} is not JSON serializable", tip_adı(x)),
                "ALQ-T001",
            ))
        }
    })
}

// ── Naxış (requlyar ifadələr) ──────────────────────────────────────────

pub fn naxış_qur(n: &str, bayraqlar: &str) -> Nəticə<Rc<fancy_regex::Regex>> {
    let mut ön = String::new();
    for (b, f) in [('i', 'i'), ('m', 'm'), ('s', 's'), ('x', 'x')] {
        if bayraqlar.contains(b) {
            ön.push(f);
        }
    }
    let n = n.replace("\\Z", "\\z");
    let n = if ön.is_empty() { n } else { format!("(?{ön}){n}") };
    fancy_regex::Regex::new(&n)
        .map(Rc::new)
        .map_err(|e| xəta("FormatXətası", format!("naxış səhvdir: {e}"), "ALQ-R005"))
}

fn re_əvəz_mətni(y: &str) -> String {
    let c: Vec<char> = y.chars().collect();
    let mut r = String::new();
    let mut k = 0;
    while k < c.len() {
        if c[k] == '$' {
            r.push_str("$$");
        } else if c[k] == '\\' && k + 1 < c.len() {
            let n = c[k + 1];
            if n.is_ascii_digit() {
                let mut j = k + 1;
                let mut s = String::new();
                while j < c.len() && c[j].is_ascii_digit() && s.len() < 2 {
                    s.push(c[j]);
                    j += 1;
                }
                r.push_str(&format!("${{{s}}}"));
                k = j;
                continue;
            } else if n == 'g' && k + 2 < c.len() && c[k + 2] == '<' {
                if let Some(e) = c[k + 3..].iter().position(|x| *x == '>') {
                    let ad: String = c[k + 3..k + 3 + e].iter().collect();
                    r.push_str(&format!("${{{ad}}}"));
                    k = k + 4 + e;
                    continue;
                }
            } else {
                let x = match n {
                    'n' => Some('\n'),
                    't' => Some('\t'),
                    'r' => Some('\r'),
                    '\\' => Some('\\'),
                    _ => None,
                };
                if let Some(x) = x {
                    r.push(x);
                    k += 2;
                    continue;
                }
            }
            r.push(c[k]);
        } else {
            r.push(c[k]);
        }
        k += 1;
    }
    r
}

fn re_xəta(e: fancy_regex::Error) -> Siqnal {
    xəta("FormatXətası", format!("naxış xətası: {e}"), "ALQ-R005")
}

pub fn re_hamısı(r: &fancy_regex::Regex, s: &str) -> Nəticə {
    let mut n = vec![];
    for m in r.captures_iter(s) {
        let m = m.map_err(re_xəta)?;
        let g = m.len();
        if g == 1 {
            n.push(D::s(m.get(0).unwrap().as_str()));
        } else if g == 2 {
            n.push(D::s(m.get(1).map(|x| x.as_str()).unwrap_or("")));
        } else {
            n.push(D::kortej((1..g).map(|k| D::s(m.get(k).map(|x| x.as_str()).unwrap_or(""))).collect()));
        }
    }
    Ok(D::siyahı(n))
}

pub fn re_böl(r: &fancy_regex::Regex, s: &str) -> Nəticə {
    let mut n = vec![];
    let mut son = 0;
    for m in r.captures_iter(s) {
        let m = m.map_err(re_xəta)?;
        let t = m.get(0).unwrap();
        if t.start() == t.end() && (t.start() == 0 || t.start() == s.len()) && t.start() == son && t.start() == 0 {
            continue;
        }
        n.push(D::s(&s[son..t.start()]));
        for k in 1..m.len() {
            n.push(m.get(k).map(|x| D::s(x.as_str())).unwrap_or(D::Boş));
        }
        son = t.end();
    }
    n.push(D::s(&s[son..]));
    Ok(D::siyahı(n))
}

// ═══════════════════════════════════════════════════════════════════════
//  Modulların qurulması
// ═══════════════════════════════════════════════════════════════════════

fn m(ad_: &str, üzvlər: Vec<(&str, D)>) -> Rc<Modul> {
    Modul::yeni(ad_, üzvlər)
}

pub fn modulları_qur(_i: &İcraçı) -> Vec<(&'static str, Rc<Modul>)> {
    vec![
        ("paralel", paralel()),
        ("sap", sap()),
        ("riyaziyyat", riyaziyyat()),
        ("mətn", mətn_modulu()),
        ("təsadüfi", təsadüfi()),
        ("vaxt", vaxt()),
        ("fayl", fayl()),
        ("qovluq", qovluq()),
        ("yol", yol()),
        ("json", json()),
        ("naxış", naxış()),
        ("sistem", sistem()),
        ("konsol", super::konsol::modul()),
        ("jurnal", jurnal()),
        ("test", test_modulu()),
        #[cfg(not(target_arch = "wasm32"))]
        ("veb", super::mod_veb::qur()),
    ]
}

fn riyaziyyat() -> Rc<Modul> {
    use std::f64::consts as C;
    m("riyaziyyat", vec![
        ("Pİ", D::O(C::PI)),
        ("PI", D::O(C::PI)),
        ("E", D::O(C::E)),
        ("TAU", D::O(C::TAU)),
        ("QIZILNİSBƏT", D::O((1.0 + 5f64.sqrt()) / 2.0)),
        ("SONSUZ", D::O(f64::INFINITY)),
        ("ƏDƏDDEYİL", D::O(f64::NAN)),
        ("mütləq", D_("mütləq", 1, Some(1), Box::new(|_, a, _| match &a[0] {
            D::T(_) | D::BT(_) => Ok(D::tam(a[0].böyük_tam().unwrap().abs())),
            D::M(b) => Ok(D::T(*b as i64)),
            x => Ok(D::O(ədəd(x, "mütləq")?.abs())),
        }))),
        ("işarə", D_("işarə", 1, Some(1), Box::new(|_, a, _| {
            Ok(D::T(match ədəd_müq(&a[0], &D::T(0)) {
                Some(Ordering::Greater) => 1,
                Some(Ordering::Less) => -1,
                _ => 0,
            }))
        }))),
        ("kök", D_("kök", 1, Some(1), Box::new(|_, a, _| {
            let v = ədəd(&a[0], "kök")?;
            Ok(D::O(if v >= 0.0 { v.sqrt() } else { f64::NAN }))
        }))),
        ("kubKök", D_("kubKök", 1, Some(1), Box::new(|_, a, _| {
            let v = ədəd(&a[0], "kubKök")?;
            Ok(D::O(v.abs().powf(1.0 / 3.0).copysign(v)))
        }))),
        ("qüvvət", D_("qüvvət", 2, Some(2), Box::new(|i, a, _| i.ikili_hesabla("**", &a[0], &a[1], None)))),
        ("eksp", r1("eksp", f64::exp)),
        ("loq", D_("loq", 1, Some(2), Box::new(|_, a, _| {
            let v = ədəd(&a[0], "loq")?;
            if v <= 0.0 {
                return Err(riyazi_xəta());
            }
            match a.get(1) {
                None => Ok(D::O(v.ln())),
                Some(b) => Ok(D::O(v.ln() / ədəd(b, "loq")?.ln())),
            }
        }))),
        ("loq10", D_("loq10", 1, Some(1), Box::new(|_, a, _| {
            let v = ədəd(&a[0], "loq10")?;
            if v <= 0.0 {
                return Err(riyazi_xəta());
            }
            Ok(D::O(v.log10()))
        }))),
        ("loq2", D_("loq2", 1, Some(1), Box::new(|_, a, _| {
            let v = ədəd(&a[0], "loq2")?;
            if v <= 0.0 {
                return Err(riyazi_xəta());
            }
            Ok(D::O(v.log2()))
        }))),
        ("loqƏsas", D_("loqƏsas", 2, Some(2), Box::new(|_, a, _| {
            let (x, b) = (ədəd(&a[0], "loqƏsas")?, ədəd(&a[1], "loqƏsas")?);
            if x <= 0.0 || b <= 0.0 {
                return Err(riyazi_xəta());
            }
            Ok(D::O(x.ln() / b.ln()))
        }))),
        ("yuvarlaqlaşdır", D_("yuvarlaqlaşdır", 1, Some(2), Box::new(|_, a, _| {
            let r = a.get(1).and_then(|r| r.i64()).filter(|r| *r != 0);
            match &a[0] {
                D::T(_) | D::BT(_) => Ok(a[0].clone()),
                x => super::metodlar::yuvarla(ədəd(x, "yuvarlaqlaşdır")?, r),
            }
        }))),
        ("aşağıYuvarlaq", D_("aşağıYuvarlaq", 1, Some(1), Box::new(|_, a, _| match &a[0] {
            D::T(_) | D::BT(_) => Ok(a[0].clone()),
            x => super::eded::onluqdan_tam(ədəd(x, "aşağıYuvarlaq")?.floor()),
        }))),
        ("yuxarıYuvarlaq", D_("yuxarıYuvarlaq", 1, Some(1), Box::new(|_, a, _| match &a[0] {
            D::T(_) | D::BT(_) => Ok(a[0].clone()),
            x => super::eded::onluqdan_tam(ədəd(x, "yuxarıYuvarlaq")?.ceil()),
        }))),
        ("kəs", D_("kəs", 1, Some(1), Box::new(|_, a, _| match &a[0] {
            D::T(_) | D::BT(_) => Ok(a[0].clone()),
            x => super::eded::onluqdan_tam(ədəd(x, "kəs")?),
        }))),
        ("min", D_("min", 1, None, Box::new(|_, a, _| Ok(ilk_min(&a, false))))),
        ("maks", D_("maks", 1, None, Box::new(|_, a, _| Ok(ilk_min(&a, true))))),
        ("məhdudla", D_("məhdudla", 3, Some(3), Box::new(|_, a, _| {
            let ki = ilk_min(&[a[2].clone(), a[0].clone()], false);
            Ok(ilk_min(&[a[1].clone(), ki], true))
        }))),
        ("sin", r1("sin", f64::sin)),
        ("kos", r1("kos", f64::cos)),
        ("tan", r1("tan", f64::tan)),
        ("arksin", r1("arksin", f64::asin)),
        ("arkkos", r1("arkkos", f64::acos)),
        ("arktan", r1("arktan", f64::atan)),
        ("arktan2", D_("arktan2", 2, Some(2), Box::new(|_, a, _| Ok(D::O(ədəd(&a[0], "arktan2")?.atan2(ədəd(&a[1], "arktan2")?)))))),
        ("hipsin", r1("hipsin", f64::sinh)),
        ("hipkos", r1("hipkos", f64::cosh)),
        ("hiptan", r1("hiptan", f64::tanh)),
        ("dərəcəyə", r1("dərəcəyə", f64::to_degrees)),
        ("radiana", r1("radiana", f64::to_radians)),
        ("ƏBOB", D_("ƏBOB", 2, None, Box::new(|_, a, _| {
            let mut g = BigInt::zero();
            for x in &a {
                g = g.gcd(&tam_yoxla(x, "ƏBOB")?.böyük_tam().unwrap());
            }
            Ok(D::tam(g))
        }))),
        ("ƏKOB", D_("ƏKOB", 2, None, Box::new(|_, a, _| {
            let mut l = BigInt::from(1);
            for x in &a {
                let y = tam_yoxla(x, "ƏKOB")?.böyük_tam().unwrap();
                if y.is_zero() {
                    return Ok(D::T(0));
                }
                l = l.lcm(&y);
            }
            Ok(D::tam(l.abs()))
        }))),
        ("faktorial", D_("faktorial", 1, Some(1), Box::new(|_, a, _| {
            let n = tam_yoxla(&a[0], "faktorial")?.böyük_tam().unwrap();
            if n.is_negative() {
                return Err(xəta("DəyərXətası", "faktorial mənfi ədəd üçün təyin olunmayıb", "ALQ-R005"));
            }
            let n = n.to_u64().unwrap_or(0);
            let mut r = BigInt::from(1);
            for k in 2..=n {
                r *= k;
            }
            Ok(D::tam(r))
        }))),
        ("sadədir", D_("sadədir", 1, Some(1), Box::new(|_, a, _| Ok(D::M(sadədir(&a[0].böyük_tam().unwrap_or_default())))))),
        ("sadəBölənlər", D_("sadəBölənlər", 1, Some(1), Box::new(|_, a, _| {
            let mut n = a[0].böyük_tam().unwrap_or_default();
            let mut r = vec![];
            let mut d = BigInt::from(2);
            while &d * &d <= n {
                while (&n % &d).is_zero() {
                    r.push(D::tam(d.clone()));
                    n /= &d;
                }
                d += 1;
            }
            if n > BigInt::from(1) {
                r.push(D::tam(n));
            }
            Ok(D::siyahı(r))
        }))),
        ("modul", D_("modul", 2, Some(2), Box::new(|_, a, _| {
            if a[0].tamdır() && a[1].tamdır() {
                let (x, y) = (a[0].böyük_tam().unwrap(), a[1].böyük_tam().unwrap());
                if y.is_zero() {
                    return Err(xəta("BölməXətası", "sıfıra bölmək olmaz", "ALQ-R001"));
                }
                return Ok(D::tam(x.mod_floor(&y)));
            }
            let (x, y) = (ədəd(&a[0], "modul")?, ədəd(&a[1], "modul")?);
            let r = x % y;
            Ok(D::O(if r != 0.0 && (r < 0.0) != (y < 0.0) { r + y } else { r }))
        }))),
        ("modQüvvət", D_("modQüvvət", 3, Some(3), Box::new(|_, a, _| {
            let (x, e, md) = (a[0].böyük_tam().unwrap_or_default(), a[1].böyük_tam().unwrap_or_default(), a[2].böyük_tam().unwrap_or_default());
            if md.is_zero() {
                return Err(xəta("DəyərXətası", "modul sıfır ola bilməz", "ALQ-R005"));
            }
            Ok(D::tam(x.modpow(&e, &md).mod_floor(&md)))
        }))),
        ("ədəddirmi", D_("ədəddirmi", 1, Some(1), Box::new(|_, a, _| Ok(D::M(a[0].ədəddir()))))),
        ("sonludur", D_("sonludur", 1, Some(1), Box::new(|_, a, _| Ok(D::M(ədəd(&a[0], "sonludur")?.is_finite()))))),
        ("tamdır", D_("tamdır", 1, Some(1), Box::new(|_, a, _| {
            let v = ədəd(&a[0], "tamdır")?;
            Ok(D::M(v.is_finite() && v.fract() == 0.0))
        }))),
        ("orta", D_("orta", 1, Some(1), Box::new(|i, a, _| {
            let s = i.siyahıya(&a[0], None)?;
            if s.is_empty() {
                return Ok(D::O(0.0));
            }
            let c = py_sum(i, &s)?;
            i.ikili_hesabla("/", &c, &D::T(s.len() as i64), None)
        }))),
        ("median", D_("median", 1, Some(1), Box::new(|i, a, _| {
            let s = sıralı_ədədlər(i, &a[0])?;
            let n = s.len();
            if n == 0 {
                return Err(xəta("BoşKolleksiyaXətası", "boş kolleksiyanın medianı yoxdur", "ALQ-R014"));
            }
            if n % 2 == 1 {
                return Ok(D::O(s[n / 2].onluq().unwrap_or(0.0)));
            }
            let c = i.ikili_hesabla("+", &s[n / 2 - 1], &s[n / 2], None)?;
            i.ikili_hesabla("/", &c, &D::T(2), None)
        }))),
        ("moda", D_("moda", 1, Some(1), Box::new(|i, a, _| {
            let s = i.siyahıya(&a[0], None)?;
            if s.is_empty() {
                return Err(xəta("BoşKolleksiyaXətası", "boş kolleksiyanın modası yoxdur", "ALQ-R014"));
            }
            let mut say: indexmap::IndexMap<Açar, usize> = Default::default();
            for x in s {
                *say.entry(Açar::yeni(x)?).or_insert(0) += 1;
            }
            let mut ən = None;
            let mut n = 0;
            for (k, c) in say {
                if c > n {
                    n = c;
                    ən = Some(k.0);
                }
            }
            Ok(ən.unwrap_or(D::Boş))
        }))),
        ("dispersiya", D_("dispersiya", 1, Some(1), Box::new(|i, a, _| Ok(D::O(dispersiya(i, &a[0])?))))),
        ("standartKənarlaşma", D_("standartKənarlaşma", 1, Some(1), Box::new(|i, a, _| Ok(D::O(dispersiya(i, &a[0])?.sqrt()))))),
    ])
}

fn mətn_modulu() -> Rc<Modul> {
    let tək = |f: fn(char) -> bool| -> F {
        Box::new(move |_, a, _| {
            let s = mətn_yoxla(&a[0], "simvol")?;
            let mut c = s.chars();
            Ok(D::M(match (c.next(), c.next()) {
                (Some(x), None) => f(x),
                _ => false,
            }))
        })
    };
    m("mətn", vec![
        ("formatla", D_("formatla", 1, None, Box::new(|i, a, _| super::metodlar::metod_çağır(i, &a[0], "formatla", a[1..].to_vec(), vec![])))),
        ("yerliƏdəd", D_("yerliƏdəd", 1, Some(2), Box::new(|_, a, _| {
            let r = a.get(1).and_then(|r| r.i64()).map(|r| r.max(0) as usize);
            Ok(D::str(yerli_ədəd(ədəd(&a[0], "yerliƏdəd")?, r)))
        }))),
        ("yerliPul", D_("yerliPul", 1, Some(1), Box::new(|_, a, _| Ok(D::str(yerli_ədəd(ədəd(&a[0], "yerliPul")?, Some(2)) + " ₼"))))),
        ("yerliFaiz", D_("yerliFaiz", 1, Some(1), Box::new(|_, a, _| Ok(D::str(yerli_ədəd(ədəd(&a[0], "yerliFaiz")? * 100.0, Some(1)) + " %"))))),
        ("yazıylaƏdəd", D_("yazıylaƏdəd", 1, Some(1), Box::new(|_, a, _| Ok(D::str(yazıyla(&tam_yoxla(&a[0], "yazıylaƏdəd")?.böyük_tam().unwrap())))))),
        ("sıraSayı", D_("sıraSayı", 1, Some(1), Box::new(|_, a, _| Ok(D::str(sıra_sayı(&a[0])))))),
        ("saitdir", D_("saitdir", 1, Some(1), tək(E::saitdir))),
        ("samitdir", D_("samitdir", 1, Some(1), tək(|c| E::hərfdir(c) && !E::saitdir(c)))),
        ("qalınSait", D_("qalınSait", 1, Some(1), tək(E::qalın))),
        ("incəSait", D_("incəSait", 1, Some(1), tək(E::incə))),
        ("şəkilçi", D_("şəkilçi", 2, Some(2), Box::new(|_, a, _| Ok(D::str(şəkilçi(&mətn_yoxla(&a[0], "şəkilçi")?, &mətn_yoxla(&a[1], "şəkilçi")?)))))),
        ("böyüyə", D_("böyüyə", 1, Some(1), Box::new(|_, a, _| Ok(D::str(E::böyüyə(&mətn_yoxla(&a[0], "böyüyə")?)))))),
        ("kiçiyə", D_("kiçiyə", 1, Some(1), Box::new(|_, a, _| Ok(D::str(E::kiçiyə(&mətn_yoxla(&a[0], "kiçiyə")?)))))),
        ("müqayisə", D_("müqayisə", 2, Some(2), Box::new(|_, a, _| Ok(D::T(E::müqayisə(&mətn_yoxla(&a[0], "müqayisə")?, &mətn_yoxla(&a[1], "müqayisə")?) as i64))))),
        ("əlifba", D::s(E::KICIK)),
    ])
}

fn təsadüfi() -> Rc<Modul> {
    m("təsadüfi", vec![
        ("tam", D_("tam", 2, Some(2), Box::new(|i, a, _| {
            let (x, y) = (tam_yoxla(&a[0], "tam")?.böyük_tam().unwrap(), tam_yoxla(&a[1], "tam")?.böyük_tam().unwrap());
            let n = &y - &x + 1;
            if n <= BigInt::zero() {
                return Err(xəta("DəyərXətası", "boş diapazon", "ALQ-R005"));
            }
            Ok(D::tam(x + i.təsadüfi.borrow_mut().aşağı(&n)))
        }))),
        ("onluq", D_("onluq", 0, Some(2), Box::new(|i, a, _| {
            let x = a.first().map(|d| ədəd(d, "onluq")).transpose()?.unwrap_or(0.0);
            let y = a.get(1).map(|d| ədəd(d, "onluq")).transpose()?.unwrap_or(1.0);
            Ok(D::O(x + (y - x) * i.təsadüfi.borrow_mut().random()))
        }))),
        ("məntiq", D_("məntiq", 0, Some(0), Box::new(|i, _, _| Ok(D::M(i.təsadüfi.borrow_mut().random() < 0.5))))),
        ("seç", D_("seç", 1, Some(1), Box::new(|i, a, _| {
            let s = i.siyahıya(&a[0], None)?;
            if s.is_empty() {
                return Err(xəta("BoşKolleksiyaXətası", "boş kolleksiyadan seçmək olmaz", "ALQ-R014"));
            }
            let k = i.təsadüfi.borrow_mut().aşağı_us(s.len());
            Ok(s[k].clone())
        }))),
        ("seçN", D_("seçN", 2, Some(2), Box::new(|i, a, _| {
            let mut pool = i.siyahıya(&a[0], None)?;
            let n = pool.len();
            let k = a[1].i64().unwrap_or(0);
            if k < 0 || k as usize > n {
                return Err(xəta("DəyərXətası", "nümunə kolleksiyadan böyükdür", "ALQ-R005"));
            }
            let k = k as usize;
            let mut setsize = 21usize;
            if k > 5 {
                let x = ((3 * k) as f64).ln() / 4f64.ln();
                setsize += 4usize.pow(x.ceil() as u32);
            }
            let mut r = Vec::with_capacity(k);
            let mut mt = i.təsadüfi.borrow_mut();
            if n <= setsize {
                for j in 0..k {
                    let x = mt.aşağı_us(n - j);
                    r.push(pool[x].clone());
                    pool[x] = pool[n - j - 1].clone();
                }
            } else {
                let mut seçilən = std::collections::HashSet::new();
                for _ in 0..k {
                    let mut x = mt.aşağı_us(n);
                    while seçilən.contains(&x) {
                        x = mt.aşağı_us(n);
                    }
                    seçilən.insert(x);
                    r.push(pool[x].clone());
                }
            }
            Ok(D::siyahı(r))
        }))),
        ("qarışdır", D_("qarışdır", 1, Some(1), Box::new(|i, a, _| {
            if let D::Siyahı(l) = &a[0] {
                let mut v = l.borrow().clone();
                i.təsadüfi.borrow_mut().qarışdır(&mut v);
                *l.borrow_mut() = v;
            }
            Ok(D::Boş)
        }))),
        ("mətn", D_("mətn", 1, Some(1), Box::new(|i, a, _| {
            let h: Vec<char> = E::KICIK.chars().collect();
            let n = a[0].i64().unwrap_or(0);
            let mut s = String::new();
            for _ in 0..n.max(0) {
                s.push(h[i.təsadüfi.borrow_mut().aşağı_us(h.len())]);
            }
            Ok(D::str(s))
        }))),
        ("UUID", D_("UUID", 0, Some(0), Box::new(|i, _, _| {
            let mut mt = i.təsadüfi.borrow_mut();
            let mut b = [0u8; 16];
            for x in b.iter_mut() {
                *x = (mt.növbəti() & 0xff) as u8;
            }
            b[6] = (b[6] & 0x0f) | 0x40;
            b[8] = (b[8] & 0x3f) | 0x80;
            let h: String = b.iter().map(|x| format!("{:02x}", x)).collect();
            Ok(D::str(format!("{}-{}-{}-{}-{}", &h[0..8], &h[8..12], &h[12..16], &h[16..20], &h[20..])))
        }))),
        ("toxum", D_("toxum", 1, Some(1), Box::new(|i, a, _| {
            let n = match &a[0] {
                D::T(_) | D::BT(_) | D::M(_) => a[0].böyük_tam().unwrap(),
                x => BigInt::from(ptr_id(x)),
            };
            *i.təsadüfi.borrow_mut() = MT::tamdan(&n);
            Ok(D::Boş)
        }))),
    ])
}

fn vaxt() -> Rc<Modul> {
    m("vaxt", vec![
        ("möhür", D_("möhür", 0, Some(0), Box::new(|_, _, _| Ok(D::T(möhür() as i64))))),
        ("möhürMs", D_("möhürMs", 0, Some(0), Box::new(|_, _, _| Ok(D::T((möhür() * 1000.0) as i64))))),
        ("indi", D_("indi", 0, Some(0), Box::new(|_, _, _| Ok(D::str(vaxt_formatla("YYYY-MM-DDTHH:mm:ss", None)))))),
        ("bugün", D_("bugün", 0, Some(0), Box::new(|_, _, _| Ok(D::str(vaxt_formatla("YYYY-MM-DD", None)))))),
        ("formatla", D_("formatla", 1, Some(2), Box::new(|_, a, _| {
            let f = mətn_yoxla(&a[0], "formatla")?;
            let m = a.get(1).and_then(|x| x.onluq()).filter(|x| *x != 0.0).map(|x| x as i64);
            Ok(D::str(vaxt_formatla(&f, m)))
        }))),
        ("azərbaycanca", D_("azərbaycanca", 0, Some(0), Box::new(|_, _, _| {
            let t = yerli_vaxt(None);
            Ok(D::str(format!("{} {} {}, {}", t.gün, AYLAR[t.ay as usize - 1], t.il, GÜNLƏR[t.həftə_günü as usize])))
        }))),
        ("ayAdı", D_("ayAdı", 1, Some(1), Box::new(|_, a, _| ad_al(&AYLAR, &a[0]).map(D::s)))),
        ("ayAdıBaş", D_("ayAdıBaş", 1, Some(1), Box::new(|_, a, _| ad_al(&AYLAR, &a[0]).map(|s| D::str(E::baş_böyük(s)))))),
        ("günAdı", D_("günAdı", 1, Some(1), Box::new(|_, a, _| ad_al(&GÜNLƏR, &a[0]).map(D::s)))),
        ("ayAdları", D_("ayAdları", 0, Some(0), Box::new(|_, _, _| Ok(D::siyahı(AYLAR.iter().map(|s| D::s(s)).collect()))))),
        ("günAdları", D_("günAdları", 0, Some(0), Box::new(|_, _, _| Ok(D::siyahı(GÜNLƏR.iter().map(|s| D::s(s)).collect()))))),
        ("gözlə", D_("gözlə", 1, Some(1), Box::new(|i, a, _| {
            i.boşalt();
            yat(ədəd(&a[0], "gözlə")?);
            Ok(D::Boş)
        }))),
        ("gözləSaniyə", D_("gözləSaniyə", 1, Some(1), Box::new(|i, a, _| {
            i.boşalt();
            yat(ədəd(&a[0], "gözləSaniyə")? * 1000.0);
            Ok(D::Boş)
        }))),
        ("ölç", D_("ölç", 0, Some(0), Box::new(|i, _, _| Ok(D::O(super::platforma::monoton_san() - i.ölçü_başlanğıc))))),
        ("limitlə", D_("limitlə", 2, Some(2), Box::new(|i, a, _| i.gözlə(a[1].clone(), None)))),
    ])
}

fn ad_al(c: &[&'static str], n: &D) -> Nəticə<&'static str> {
    let k = n.i64().unwrap_or(0) - 1;
    let k = if k < 0 { k + c.len() as i64 } else { k };
    c.get(k as usize).copied().ok_or_else(|| xəta("İndeksXətası", "list index out of range", "ALQ-R002"))
}

fn fayl() -> Rc<Modul> {
    m("fayl", vec![
        ("oxu", D_("oxu", 1, Some(1), Box::new(|_, a, _| Ok(D::str(fayl_oxu(&mətn_yoxla(&a[0], "oxu")?)?))))),
        ("yaz", D_("yaz", 2, Some(2), Box::new(|i, a, _| fayl_yaz(i, &mətn_yoxla(&a[0], "yaz")?, &a[1])))),
        ("əlavəEt", D_("əlavəEt", 2, Some(2), Box::new(|i, a, _| {
            use std::io::Write;
            let y = mətn_yoxla(&a[0], "əlavəEt")?;
            let s = mətnə(i, &a[1])?;
            let mut f = std::fs::OpenOptions::new().append(true).create(true).open(&*y).map_err(|e| io_xəta(e, &y))?;
            f.write_all(s.as_bytes()).map_err(|e| io_xəta(e, &y))?;
            Ok(D::Boş)
        }))),
        ("oxuSətirlər", D_("oxuSətirlər", 1, Some(1), Box::new(|_, a, _| {
            let s = fayl_oxu(&mətn_yoxla(&a[0], "oxuSətirlər")?)?;
            Ok(D::siyahı(s.split('\n').map(D::s).collect()))
        }))),
        ("oxuBayt", D_("oxuBayt", 1, Some(1), Box::new(|_, a, _| {
            let y = mətn_yoxla(&a[0], "oxuBayt")?;
            std::fs::read(&*y).map(|b| D::Bayt(Rc::new(b))).map_err(|e| io_xəta(e, &y))
        }))),
        ("yazBayt", D_("yazBayt", 2, Some(2), Box::new(|i, a, _| {
            let y = mətn_yoxla(&a[0], "yazBayt")?;
            let b: Vec<u8> = match &a[1] {
                D::Bayt(b) => b.to_vec(),
                x => i.siyahıya(x, None)?.iter().map(|d| d.i64().unwrap_or(0) as u8).collect(),
            };
            std::fs::write(&*y, b).map_err(|e| io_xəta(e, &y))?;
            Ok(D::Boş)
        }))),
        ("vardır", D_("vardır", 1, Some(1), Box::new(|_, a, _| Ok(D::M(Path::new(&*mətn_yoxla(&a[0], "vardır")?).is_file()))))),
        ("sil", D_("sil", 1, Some(1), Box::new(|_, a, _| {
            let _ = std::fs::remove_file(&*mətn_yoxla(&a[0], "sil")?);
            Ok(D::Boş)
        }))),
        ("kopyala", D_("kopyala", 2, Some(2), Box::new(|_, a, _| {
            let (x, y) = (mətn_yoxla(&a[0], "kopyala")?, mətn_yoxla(&a[1], "kopyala")?);
            let mut h = PathBuf::from(&*y);
            if h.is_dir() {
                h = h.join(Path::new(&*x).file_name().unwrap_or_default());
            }
            std::fs::copy(&*x, h).map_err(|e| io_xəta(e, &x))?;
            Ok(D::Boş)
        }))),
        ("köçür", D_("köçür", 2, Some(2), Box::new(|_, a, _| {
            let (x, y) = (mətn_yoxla(&a[0], "köçür")?, mətn_yoxla(&a[1], "köçür")?);
            std::fs::rename(&*x, &*y).map_err(|e| io_xəta(e, &x))?;
            Ok(D::Boş)
        }))),
        ("adDəyiş", D_("adDəyiş", 2, Some(2), Box::new(|_, a, _| {
            let (x, y) = (mətn_yoxla(&a[0], "adDəyiş")?, mətn_yoxla(&a[1], "adDəyiş")?);
            std::fs::rename(&*x, &*y).map_err(|e| io_xəta(e, &x))?;
            Ok(D::Boş)
        }))),
        ("ölçü", D_("ölçü", 1, Some(1), Box::new(|_, a, _| {
            let y = mətn_yoxla(&a[0], "ölçü")?;
            std::fs::metadata(&*y).map(|m| D::T(m.len() as i64)).map_err(|e| io_xəta(e, &y))
        }))),
        ("MIMETipi", D_("MIMETipi", 1, Some(1), Box::new(|_, a, _| {
            let u = yol_uzantı(&mətn_yoxla(&a[0], "MIMETipi")?).to_lowercase();
            Ok(D::s(match u.as_str() {
                ".html" | ".htm" => "text/html",
                ".txt" | ".alq" => "text/plain",
                ".css" => "text/css",
                ".js" => "text/javascript",
                ".json" => "application/json",
                ".png" => "image/png",
                ".jpg" | ".jpeg" => "image/jpeg",
                ".gif" => "image/gif",
                ".svg" => "image/svg+xml",
                ".pdf" => "application/pdf",
                ".csv" => "text/csv",
                ".xml" => "application/xml",
                ".zip" => "application/zip",
                _ => "application/octet-stream",
            }))
        }))),
    ])
}

fn qovluq() -> Rc<Modul> {
    m("qovluq", vec![
        ("yarat", D_("yarat", 1, Some(1), Box::new(|_, a, _| {
            let y = mətn_yoxla(&a[0], "yarat")?;
            match std::fs::create_dir(&*y) {
                Ok(()) => Ok(D::Boş),
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists && Path::new(&*y).is_dir() => Ok(D::Boş),
                Err(e) => Err(io_xəta(e, &y)),
            }
        }))),
        ("yaratDərin", D_("yaratDərin", 1, Some(1), Box::new(|_, a, _| {
            let y = mətn_yoxla(&a[0], "yaratDərin")?;
            std::fs::create_dir_all(&*y).map_err(|e| io_xəta(e, &y))?;
            Ok(D::Boş)
        }))),
        ("sil", D_("sil", 1, Some(1), Box::new(|_, a, _| {
            let y = mətn_yoxla(&a[0], "sil")?;
            std::fs::remove_dir(&*y).map_err(|e| io_xəta(e, &y))?;
            Ok(D::Boş)
        }))),
        ("silDərin", D_("silDərin", 1, Some(1), Box::new(|_, a, _| {
            let _ = std::fs::remove_dir_all(&*mətn_yoxla(&a[0], "silDərin")?);
            Ok(D::Boş)
        }))),
        ("vardır", D_("vardır", 1, Some(1), Box::new(|_, a, _| Ok(D::M(Path::new(&*mətn_yoxla(&a[0], "vardır")?).is_dir()))))),
        ("siyahı", D_("siyahı", 0, Some(1), Box::new(|_, a, _| {
            let y = match a.first() {
                Some(x) => mətn_yoxla(x, "siyahı")?.to_string(),
                None => ".".into(),
            };
            let mut v: Vec<String> = std::fs::read_dir(&y)
                .map_err(|e| io_xəta(e, &y))?
                .filter_map(|e| e.ok().map(|e| e.file_name().to_string_lossy().to_string()))
                .collect();
            v.sort();
            Ok(D::siyahı(v.into_iter().map(D::str).collect()))
        }))),
        ("axtar", D_("axtar", 2, Some(2), Box::new(|_, a, _| {
            let (y, n) = (mətn_yoxla(&a[0], "axtar")?, mətn_yoxla(&a[1], "axtar")?);
            let mut r = vec![];
            fn gəz(p: &Path, n: &str, r: &mut Vec<String>) {
                if let Ok(d) = std::fs::read_dir(p) {
                    for e in d.flatten() {
                        let q = e.path();
                        if uyğun(&e.file_name().to_string_lossy(), n) {
                            r.push(q.display().to_string());
                        }
                        if q.is_dir() {
                            gəz(&q, n, r);
                        }
                    }
                }
            }
            gəz(Path::new(&*y), &n, &mut r);
            r.sort();
            Ok(D::siyahı(r.into_iter().map(D::str).collect()))
        }))),
        ("cari", D_("cari", 0, Some(0), Box::new(|_, _, _| Ok(D::str(std::env::current_dir().map(|d| d.display().to_string()).unwrap_or_default()))))),
        ("dəyiş", D_("dəyiş", 1, Some(1), Box::new(|_, a, _| {
            let y = mətn_yoxla(&a[0], "dəyiş")?;
            std::env::set_current_dir(&*y).map_err(|e| io_xəta(e, &y))?;
            Ok(D::Boş)
        }))),
        ("ev", D_("ev", 0, Some(0), Box::new(|_, _, _| Ok(D::str(std::env::var("HOME").unwrap_or_default()))))),
        ("müvəqqəti", D_("müvəqqəti", 0, Some(0), Box::new(|_, _, _| Ok(D::str(std::env::temp_dir().display().to_string().trim_end_matches('/').to_string()))))),
    ])
}

/// Sadə glob (`*`, `?`)
fn uyğun(s: &str, n: &str) -> bool {
    let s: Vec<char> = s.chars().collect();
    let n: Vec<char> = n.chars().collect();
    fn u(s: &[char], n: &[char]) -> bool {
        match n.first() {
            None => s.is_empty(),
            Some('*') => (0..=s.len()).any(|k| u(&s[k..], &n[1..])),
            Some('?') => !s.is_empty() && u(&s[1..], &n[1..]),
            Some(c) => s.first() == Some(c) && u(&s[1..], &n[1..]),
        }
    }
    u(&s, &n)
}

fn yol() -> Rc<Modul> {
    let bir = |a: &'static str, f: fn(&str) -> String| D_(a, 1, Some(1), Box::new(move |_, x, _| Ok(D::str(f(&mətn_yoxla(&x[0], a)?)))));
    m("yol", vec![
        ("birləşdir", D_("birləşdir", 1, None, Box::new(|_, a, _| {
            let mut p = String::new();
            for x in &a {
                let s = mətn_yoxla(x, "birləşdir")?;
                if s.starts_with('/') {
                    p = s.to_string();
                } else if p.is_empty() || p.ends_with('/') {
                    p.push_str(&s);
                } else {
                    p.push('/');
                    p.push_str(&s);
                }
            }
            // Path(...) normallaşdırması: təkrar `/` və `.` silinir
            let mut h: Vec<&str> = p.split('/').filter(|x| !x.is_empty() && *x != ".").collect();
            if h.is_empty() {
                h.push(".");
            }
            let r = h.join("/");
            Ok(D::str(if p.starts_with('/') { format!("/{}", r.trim_start_matches('.')) } else { r }))
        }))),
        ("mütləq", bir("mütləq", |p| {
            let q = std::fs::canonicalize(p).map(|x| x.display().to_string()).unwrap_or_else(|_| {
                let c = std::env::current_dir().map(|d| d.display().to_string()).unwrap_or_default();
                normpath(&if p.starts_with('/') { p.to_string() } else { format!("{c}/{p}") })
            });
            q
        })),
        ("qovluq", bir("qovluq", yol_qovluq)),
        ("fayl", bir("fayl", yol_adı)),
        ("ad", bir("ad", |p| {
            let a = yol_adı(p);
            let u = yol_uzantı(p);
            a[..a.len() - u.len()].to_string()
        })),
        ("uzantı", bir("uzantı", yol_uzantı)),
        ("normalizə", bir("normalizə", normpath)),
        ("nisbi", D_("nisbi", 2, Some(2), Box::new(|_, a, _| Ok(D::str(nisbi(&mətn_yoxla(&a[0], "nisbi")?, &mətn_yoxla(&a[1], "nisbi")?)))))),
        ("ayırıcı", D::s("/")),
    ])
}

fn json() -> Rc<Modul> {
    m("json", vec![
        ("oxu", D_("oxu", 1, Some(1), Box::new(|_, a, _| json_oxu(&mətn_yoxla(&a[0], "oxu")?)))),
        ("yaz", D_("yaz", 1, Some(1), Box::new(|i, a, _| Ok(D::str(json_yaz(i, &a[0], false, 0)?))))),
        ("yazGözəl", D_("yazGözəl", 1, Some(1), Box::new(|i, a, _| Ok(D::str(json_yaz(i, &a[0], true, 0)?))))),
        ("faylOxu", D_("faylOxu", 1, Some(1), Box::new(|_, a, _| json_oxu(&fayl_oxu(&mətn_yoxla(&a[0], "faylOxu")?)?)))),
        ("faylYaz", D_("faylYaz", 2, Some(2), Box::new(|i, a, _| {
            let s = json_yaz(i, &a[1], true, 0)?;
            fayl_yaz(i, &mətn_yoxla(&a[0], "faylYaz")?, &D::str(s))
        }))),
    ])
}

fn naxış() -> Rc<Modul> {
    m("naxış", vec![
        ("qur", D_("qur", 1, Some(2), Box::new(|_, a, _| {
            let b = match a.get(1) {
                Some(x) => mətn_yoxla(x, "qur")?.to_string(),
                None => String::new(),
            };
            Ok(D::Naxış(naxış_qur(&mətn_yoxla(&a[0], "qur")?, &b)?))
        }))),
        ("uyğundur", D_("uyğundur", 2, Some(2), Box::new(|_, a, _| {
            let r = naxış_qur(&mətn_yoxla(&a[0], "uyğundur")?, "")?;
            Ok(D::M(r.is_match(&mətn_yoxla(&a[1], "uyğundur")?).map_err(re_xəta)?))
        }))),
        ("tap", D_("tap", 2, Some(2), Box::new(|_, a, _| {
            let r = naxış_qur(&mətn_yoxla(&a[0], "tap")?, "")?;
            let s = mətn_yoxla(&a[1], "tap")?;
            Ok(match r.find(&s).map_err(re_xəta)? {
                Some(m) => D::s(m.as_str()),
                None => D::Boş,
            })
        }))),
        ("hamısınıTap", D_("hamısınıTap", 2, Some(2), Box::new(|_, a, _| {
            let r = naxış_qur(&mətn_yoxla(&a[0], "hamısınıTap")?, "")?;
            re_hamısı(&r, &mətn_yoxla(&a[1], "hamısınıTap")?)
        }))),
        ("əvəz", D_("əvəz", 3, Some(3), Box::new(|_, a, _| {
            let r = naxış_qur(&mətn_yoxla(&a[0], "əvəz")?, "")?;
            let s = mətn_yoxla(&a[1], "əvəz")?;
            let y = re_əvəz_mətni(&mətn_yoxla(&a[2], "əvəz")?);
            let n = r.try_replacen(&s, 0, y.as_str()).map_err(re_xəta)?;
            Ok(D::str(n.to_string()))
        }))),
        ("böl", D_("böl", 2, Some(2), Box::new(|_, a, _| {
            let r = naxış_qur(&mətn_yoxla(&a[0], "böl")?, "")?;
            re_böl(&r, &mətn_yoxla(&a[1], "böl")?)
        }))),
    ])
}

fn sistem() -> Rc<Modul> {
    m("sistem", vec![
        ("arqumentlər", D_("arqumentlər", 0, Some(0), Box::new(|i, _, _| {
            Ok(D::siyahı(i.proqram_arqumentləri.borrow().iter().map(|s| D::s(s)).collect()))
        }))),
        ("mühit", D_("mühit", 1, Some(2), Box::new(|_, a, _| {
            let k = mətn_yoxla(&a[0], "mühit")?;
            Ok(match std::env::var(&*k) {
                Ok(v) => D::str(v),
                Err(_) => a.get(1).cloned().unwrap_or(D::Boş),
            })
        }))),
        ("mühitQoy", D_("mühitQoy", 2, Some(2), Box::new(|_, a, _| {
            super::platforma::mühit_qoy(&mətn_yoxla(&a[0], "mühitQoy")?, &mətn_yoxla(&a[1], "mühitQoy")?);
            Ok(D::Boş)
        }))),
        ("platforma", D_("platforma", 0, Some(0), Box::new(|_, _, _| {
            Ok(D::s(match std::env::consts::OS {
                "linux" => "linux",
                "macos" => "macos",
                "windows" => "windows",
                x => x,
            }))
        }))),
        ("memarlıq", D_("memarlıq", 0, Some(0), Box::new(|_, _, _| Ok(D::s(std::env::consts::ARCH))))),
        ("nüvəSayı", D_("nüvəSayı", 0, Some(0), Box::new(|_, _, _| Ok(D::T(std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1) as i64))))),
        ("istifadəçi", D_("istifadəçi", 0, Some(0), Box::new(|_, _, _| {
            Ok(D::str(std::env::var("USERNAME").or_else(|_| std::env::var("USER")).unwrap_or_default()))
        }))),
        ("hostAdı", D_("hostAdı", 0, Some(0), Box::new(|_, _, _| {
            Ok(D::str(super::platforma::host_adı()))
        }))),
        ("dayan", D_("dayan", 0, Some(1), Box::new(|_, a, _| Err(Siqnal::Dayanma(a.first().cloned().unwrap_or(D::T(0))))))),
    ])
}

fn jurnal() -> Rc<Modul> {
    let s = |səviyyə: &'static str| -> F {
        Box::new(move |i, a, _| {
            let t = yerli_vaxt(None);
            let mut h = vec![];
            for x in &a {
                h.push(mətnə(i, x)?);
            }
            i.xəta_yaz(&format!("[{:02}:{:02}:{:02}] {}: {}", t.saat, t.dəq, t.san, səviyyə, h.join(" ")));
            Ok(D::Boş)
        })
    };
    m("jurnal", vec![
        ("debaq", D_("debaq", 1, None, s("DEBAQ"))),
        ("info", D_("info", 1, None, s("İNFO"))),
        ("xəbərdarlıq", D_("xəbərdarlıq", 1, None, s("XƏBƏRDARLIQ"))),
        ("xəta", D_("xəta", 1, None, s("XƏTA"))),
        ("kritik", D_("kritik", 1, None, s("KRİTİK"))),
    ])
}

fn başlat_hamısı(i: &İcraçı, s: &[D]) {
    for g in s {
        if let D::Gələcək(g) = g {
            g.başlat(i);
        }
    }
}

fn p_hamısı(i: &İcraçı, k: &D) -> Nəticə<Vec<D>> {
    let s = i.siyahıya(k, None)?;
    başlat_hamısı(i, &s);
    let mut r = vec![];
    for g in s {
        r.push(i.gözlə(g, None)?);
    }
    Ok(r)
}

fn paralel() -> Rc<Modul> {
    let md = Modul::yeni("paralel", vec![
        ("hamısı", D_("hamısı", 1, Some(1), Box::new(|i, a, _| Ok(D::siyahı(p_hamısı(i, &a[0])?))))),
        ("hamısıNəticə", D_("hamısıNəticə", 1, Some(1), Box::new(|i, a, _| {
            let s = i.siyahıya(&a[0], None)?;
            başlat_hamısı(i, &s);
            let mut r = vec![];
            for g in s {
                r.push(match i.gözlə(g, None) {
                    Ok(d) => D::kortej(vec![D::M(true), d]),
                    Err(Siqnal::Xəta(x)) => D::kortej(vec![D::M(false), D::str(x.mesaj.clone())]),
                    Err(x) => return Err(x),
                });
            }
            Ok(D::siyahı(r))
        }))),
        ("ilkBitən", D_("ilkBitən", 1, Some(1), Box::new(|i, a, _| {
            let s = i.siyahıya(&a[0], None)?;
            başlat_hamısı(i, &s);
            match s.into_iter().next() {
                Some(g) => i.gözlə(g, None),
                None => Ok(D::Boş),
            }
        }))),
        ("ilkUğurlu", D_("ilkUğurlu", 1, Some(1), Box::new(|i, a, _| {
            let s = i.siyahıya(&a[0], None)?;
            başlat_hamısı(i, &s);
            let mut son = None;
            for g in s {
                match i.gözlə(g, None) {
                    Ok(d) => return Ok(d),
                    Err(Siqnal::Xəta(x)) => son = Some(x),
                    Err(x) => return Err(x),
                }
            }
            match son {
                Some(x) => Err(Siqnal::Xəta(x)),
                None => Err(xəta("Xəta", "heç bir əməliyyat uğurlu olmadı", "ALQ-R021")),
            }
        }))),
        ("məhdud", D_("məhdud", 2, Some(2), Box::new(|i, a, _| Ok(D::siyahı(p_hamısı(i, &a[1])?))))),
        ("çevir", D_("çevir", 2, Some(2), Box::new(|i, a, _| {
            let mut g = vec![];
            for x in i.siyahıya(&a[0], None)? {
                g.push(i.çağır(&a[1], vec![x], vec![], None)?);
            }
            Ok(D::siyahı(p_hamısı(i, &D::siyahı(g))?))
        }))),
    ]);
    let üzvlər = std::mem::take(&mut *md.üzvlər.borrow_mut());
    Rc::new(Modul {
        ad: std::cell::RefCell::new(ad("paralel")),
        üzvlər: std::cell::RefCell::new(üzvlər),
        çağırışçı: Some(D_("paralel", 1, None, Box::new(|i, a, _| Ok(D::kortej(p_hamısı(i, &D::siyahı(a))?))))),
    })
}

fn sap() -> Rc<Modul> {
    m("sap", vec![
        ("başlat", D_("başlat", 1, None, Box::new(|i, a, _| {
            let f = a[0].clone();
            let rest = a[1..].to_vec();
            let g = Gələcək::yeni("sap", move |i| i.çağır(&f, rest, vec![], None));
            g.başlat(i);
            Ok(D::Gələcək(g))
        }))),
        ("xəritələ", D_("xəritələ", 2, Some(3), Box::new(|i, a, _| {
            let mut r = vec![];
            for x in i.siyahıya(&a[1], None)? {
                r.push(i.çağır(&a[0], vec![x], vec![], None)?);
            }
            Ok(D::siyahı(r))
        }))),
        ("nüvəSayı", D_("nüvəSayı", 0, Some(0), Box::new(|_, _, _| Ok(D::T(std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1) as i64))))),
        ("gözlə", D_("gözlə", 1, Some(1), Box::new(|i, a, _| {
            i.boşalt();
            yat(ədəd(&a[0], "gözlə")?);
            Ok(D::Boş)
        }))),
    ])
}

#[allow(dead_code)]
fn _istifadə() -> Option<f64> {
    Some(0f64).and_then(|x: f64| x.to_f64())
}

// ── test (sinaqci.py: təsdiqlər) ───────────────────────────────────────

fn uğursuz(m: String) -> Siqnal {
    xəta("İddiaXətası", m, "ALQ-R007")
}

fn mesaj_al(i: &İcraçı, a: &[D], k: usize) -> Nəticə<Option<String>> {
    match a.get(k) {
        Some(x) => {
            let s = mətnə(i, x)?;
            Ok(if s.is_empty() { None } else { Some(s) })
        }
        None => Ok(None),
    }
}

fn xəta_adı(d: &D) -> Nəticə<String> {
    match d {
        D::S(s) => Ok(s.to_string()),
        D::Sinif(s) => Ok(s.ad.to_string()),
        D::XətaSinfi(a) => Ok(a.to_string()),
        _ => Err(xəta("ArqumentXətası", "xəta tipi gözlənilirdi (məs. `ArqumentXətası`)", "ALQ-R013")),
    }
}

pub fn test_modulu() -> Rc<Modul> {
    m("test", vec![
        ("bərabər", D_("bərabər", 2, Some(3), Box::new(|i, a, _| {
            if !i.bərabərdir(&a[0], &a[1])? {
                let m = match mesaj_al(i, &a, 2)? {
                    Some(m) => m,
                    None => format!("gözlənilən: {}\n      alınan:     {}", mətnə(i, &a[1])?, mətnə(i, &a[0])?),
                };
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("bərabərDeyil", D_("bərabərDeyil", 2, Some(3), Box::new(|i, a, _| {
            if i.bərabərdir(&a[0], &a[1])? {
                let m = match mesaj_al(i, &a, 2)? {
                    Some(m) => m,
                    None => format!("{} gözlənilməyən dəyərdir", mətnə(i, &a[0])?),
                };
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("doğru", D_("doğru", 1, Some(2), Box::new(|i, a, _| {
            if !matches!(a[0], D::M(true)) {
                let m = mesaj_al(i, &a, 1)?.map(Ok).unwrap_or_else(|| mətnə(i, &a[0]).map(|s| format!("doğru gözlənilirdi, alınan: {s}")))?;
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("yanlış", D_("yanlış", 1, Some(2), Box::new(|i, a, _| {
            if !matches!(a[0], D::M(false)) {
                let m = mesaj_al(i, &a, 1)?.map(Ok).unwrap_or_else(|| mətnə(i, &a[0]).map(|s| format!("yanlış gözlənilirdi, alınan: {s}")))?;
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("boş", D_("boş", 1, Some(2), Box::new(|i, a, _| {
            if !a[0].boşdur() {
                let m = mesaj_al(i, &a, 1)?.map(Ok).unwrap_or_else(|| mətnə(i, &a[0]).map(|s| format!("boş gözlənilirdi, alınan: {s}")))?;
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("boşDeyil", D_("boşDeyil", 1, Some(2), Box::new(|i, a, _| {
            if a[0].boşdur() {
                return Err(uğursuz(mesaj_al(i, &a, 1)?.unwrap_or("dəyər boşdur".into())));
            }
            Ok(D::Boş)
        }))),
        ("ehtiva", D_("ehtiva", 2, Some(3), Box::new(|i, a, _| {
            let var = matches!(i.üzvlük(&a[1], &a[0], None), Ok(true));
            if !var {
                let m = match mesaj_al(i, &a, 2)? {
                    Some(m) => m,
                    None => format!("{} içində {} yoxdur", mətnə(i, &a[0])?, mətnə(i, &a[1])?),
                };
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("atır", D_("atır", 1, Some(3), Box::new(|i, a, _| {
            let tip = a.get(1).filter(|x| !x.boşdur()).cloned();
            match i.çağır(&a[0], vec![], vec![], None) {
                Err(Siqnal::Xəta(x)) => {
                    if let Some(t) = &tip {
                        let ad_ = xəta_adı(t)?;
                        if !xəta_uyğundur(&x.tip, &ad_) {
                            let m = match mesaj_al(i, &a, 2)? {
                                Some(m) => m,
                                None => format!("{} gözlənilirdi, {} atıldı: {}", ad_, x.tip, x.mesaj),
                            };
                            return Err(uğursuz(m));
                        }
                    }
                    Ok(xəta_obyekti(&x))
                }
                Err(s) => Err(s),
                Ok(_) => {
                    let m = match mesaj_al(i, &a, 2)? {
                        Some(m) => m,
                        None => match &tip {
                            Some(t) => format!("{} gözlənilirdi, atılmadı", xəta_adı(t)?),
                            None => "xəta gözlənilirdi, atılmadı".into(),
                        },
                    };
                    Err(uğursuz(m))
                }
            }
        }))),
        ("atmır", D_("atmır", 1, Some(2), Box::new(|i, a, _| match i.çağır(&a[0], vec![], vec![], None) {
            Err(Siqnal::Xəta(x)) => Err(uğursuz(
                mesaj_al(i, &a, 1)?.unwrap_or_else(|| format!("xəta gözlənilmirdi: {}: {}", x.tip, x.mesaj)),
            )),
            r => r,
        }))),
        ("təxminən", D_("təxminən", 2, Some(4), Box::new(|i, a, _| {
            let d = a.get(2).cloned().unwrap_or(D::O(1e-9));
            let fərq = i.ikili_hesabla("-", &a[0], &a[1], None)?;
            let fərq = match fərq.onluq() {
                Some(f) => f.abs(),
                None => 0.0,
            };
            if fərq > d.onluq().unwrap_or(1e-9) {
                let m = match mesaj_al(i, &a, 3)? {
                    Some(m) => m,
                    None => format!("{} ≉ {} (dəqiqlik {})", mətnə(i, &a[0])?, mətnə(i, &a[1])?, mətnə(i, &d)?),
                };
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("uyğun", D_("uyğun", 2, Some(3), Box::new(|i, a, _| {
            let (s, n) = (mətnə(i, &a[0])?, mətnə(i, &a[1])?);
            let r = naxış_qur(&n, "")?;
            if !r.is_match(&s).map_err(re_xəta)? {
                let m = match mesaj_al(i, &a, 2)? {
                    Some(m) => m,
                    None => format!("{} `{}` naxışına uyğun deyil", str_repr(&s), n),
                };
                return Err(uğursuz(m));
            }
            Ok(D::Boş)
        }))),
        ("uğursuz", D_("uğursuz", 0, Some(1), Box::new(|i, a, _| {
            let m = match a.first() {
                Some(x) => mətnə(i, x)?,
                None => "sınaq uğursuz oldu".into(),
            };
            Err(uğursuz(m))
        }))),
    ])
}
