//! Daxili tiplərin metodları (kitabxana.py: _MƏTN, _SIYAHI, _LÜĞƏT ...).

use super::deyerler::*;
use super::eded::{dəst_op, sıra_müq};
use super::icraci::İcraçı;
use crate::elifba as E;
use num_bigint::BigInt;
use num_traits::{Signed, ToPrimitive, Zero};
use std::cmp::Ordering;
use std::rc::Rc;

const MƏTN: &[&str] = &[
    "uzunluq", "baytUzunluğu", "böyüyə", "kiçiyə", "başBöyük", "hərSözBöyük", "kəs", "başKəs", "sonKəs", "əvəz",
    "əvəzİlk", "böl", "sətirlər", "simvollar", "sözlər", "baytlar", "birləşdir", "ehtiva", "başlayır", "bitir", "tap",
    "sonTap", "hamısınıTap", "say", "dilim", "təkrar", "tərs", "doldur", "solDoldur", "sağDoldur", "mərkəz", "boşdur",
    "yalnızBoşluq", "rəqəmdir", "hərfdir", "müqayisə", "müqayisəHərfsiz", "normalizasiya", "latınla", "URLKodla",
    "URLAç", "base64Kodla", "base64Aç", "HTMLQaç", "formatla", "mətnƏt", "klonla", "tamƏt", "saitdir", "samitdir",
    "qalınSait", "incəSait",
];
const SİYAHI: &[&str] = &[
    "əlavə", "əlavəHamısı", "daxilEt", "sil", "silDəyər", "silHamısı", "sonunuSil", "təmizlə", "sırala", "sıralaAçar",
    "qarışdır", "tərsinəÇevir", "sıralanmış", "tərs", "dilim", "çevir", "filtr", "yığ", "yığSağdan", "düzlə",
    "düzləÇevir", "təkrarsız", "birləşdir", "qrupla", "hissələrə", "pəncərə", "zip", "nömrələ", "uzunluq", "boşdur",
    "ehtiva", "tap", "tapİndeks", "indeks", "sonİndeks", "say", "sayŞərt", "hamısı", "hərHansı", "heçBiri", "ilk",
    "son", "minimum", "maksimum", "cəm", "orta", "hərBiri", "klonla", "al", "mətnƏt", "siyahıyaÇevir",
];
const LÜĞƏT: &[&str] = &[
    "al", "qoy", "sil", "təmizlə", "ehtiva", "ehtivaDəyər", "uzunluq", "boşdur", "açarlar", "dəyərlər", "cütlər",
    "birləşdir", "çevir", "filtr", "hərBiri", "alVəYaQoy", "yenilə", "tərsÇevir", "klonla", "mətnƏt",
];
const DƏST: &[&str] = &[
    "əlavə", "sil", "ehtiva", "uzunluq", "boşdur", "təmizlə", "birləşmə", "kəsişmə", "fərq", "simmetrikFərq",
    "altDəstdir", "üstDəstdir", "kəsişmir", "siyahıyaÇevir", "çevir", "filtr", "klonla", "mətnƏt",
];
const TAM: &[&str] =
    &["mətnƏt", "mütləq", "işarə", "cütdür", "təkdir", "kvadrat", "onluğaÇevir", "ikilik", "onaltılıq", "sıraSayı", "yazıyla"];
const ONLUQ: &[&str] = &[
    "mətnƏt", "mütləq", "yuvarlaqlaşdır", "aşağıYuvarlaq", "yuxarıYuvarlaq", "kəs", "tamƏt", "tamdır", "sonludur", "ədəddir",
];
const MƏNTİQ: &[&str] = &["mətnƏt", "tamƏt"];
const KORTEJ: &[&str] = &["uzunluq", "siyahıyaÇevir", "mətnƏt", "ehtiva"];
const DİAPAZON: &[&str] = &["siyahıyaÇevir", "uzunluq", "ehtiva", "mətnƏt", "çevir", "filtr", "cəm"];
const GENERATOR: &[&str] =
    &["növbəti", "bitdi", "bağla", "siyahıyaÇevir", "ilk", "çevir", "filtr", "atla", "tap", "hərBiri", "cəm", "uzunluq"];
const BAYT: &[&str] = &["uzunluq", "mətnƏt", "siyahıyaÇevir", "base64Kodla"];
const ELEMENT: &[&str] = &["HTML", "mətn", "mətnƏt", "tap", "atribut", "uzunluq", "uşaqSayı", "boşdur"];
const GƏLƏCƏK: &[&str] = &["al", "başlat", "bitdi", "uğurludur", "mətnƏt"];
const LƏĞV: &[&str] = &["ləğvEt", "ləğvolunub", "gözlə", "yoxla"];

pub fn metod_adları(o: &D) -> &'static [&'static str] {
    match o {
        D::S(_) => MƏTN,
        D::Siyahı(_) => SİYAHI,
        D::Lüğət(_) => LÜĞƏT,
        D::Dəst(_) => DƏST,
        D::T(_) | D::BT(_) => TAM,
        D::O(_) => ONLUQ,
        D::M(_) => MƏNTİQ,
        D::Kortej(_) => KORTEJ,
        D::Diapazon(_) => DİAPAZON,
        D::Gen(_) => GENERATOR,
        D::Bayt(_) => BAYT,
        D::Element(_) => ELEMENT,
        D::Gələcək(_) => GƏLƏCƏK,
        D::LəğvNişanı(_) => LƏĞV,
        _ => &[],
    }
}

pub fn sürətli_tipdir(o: &D) -> bool {
    matches!(o, D::S(_) | D::Siyahı(_) | D::Lüğət(_) | D::Dəst(_) | D::T(_) | D::O(_) | D::Kortej(_) | D::Gen(_))
}

pub fn metod_var(o: &D, a: &str) -> bool {
    metod_adları(o).contains(&a)
}

fn arq(a: &[D], i: usize) -> Nəticə<D> {
    a.get(i).cloned().ok_or_else(|| xəta("ArqumentXətası", "metod üçün arqument çatmır", "ALQ-T003"))
}
fn ixt(a: &[D], i: usize) -> Option<D> {
    match a.get(i) {
        None | Some(D::Boş) => None,
        Some(d) => Some(d.clone()),
    }
}
fn mətn(d: &D) -> Nəticə<Rc<str>> {
    match d {
        D::S(s) => Ok(s.clone()),
        _ => Err(xəta("TipXətası", format!("mətn gözlənilirdi, `{}` gəlib", tip_adı(d)), "ALQ-T004")),
    }
}
fn tam(d: &D, ad: &str) -> Nəticə<i64> {
    match d {
        D::T(i) => Ok(*i),
        D::M(b) => Ok(*b as i64),
        _ => Err(xəta("TipXətası", format!("`{}` tam ədəd gözləyir, `{}` gəlib", ad, tip_adı(d)), "ALQ-T004")),
    }
}
fn ç(i: &İcraçı, f: &D, a: Vec<D>) -> Nəticə {
    i.çağır(f, a, vec![], None)
}
fn doğru(d: &D) -> bool {
    matches!(d, D::M(true))
}
fn uz(n: usize) -> D {
    D::T(n as i64)
}

/// Python dilimi `s[b:e]` (None → sərhəd)
fn py_dilim(n: usize, b: Option<D>, e: Option<D>) -> (usize, usize) {
    let n = n as i64;
    let norm = |x: i64| if x < 0 { (x + n).max(0) } else { x.min(n) };
    let b = b.and_then(|x| x.i64()).map(norm).unwrap_or(0);
    let e = e.and_then(|x| x.i64()).map(norm).unwrap_or(n);
    if b >= e {
        (0, 0)
    } else {
        (b as usize, e as usize)
    }
}

pub fn sırala_açarla(i: &İcraçı, el: Vec<D>, f: Option<&D>) -> Nəticə<Vec<D>> {
    let mut c = Vec::with_capacity(el.len());
    for x in el {
        let k = match f {
            Some(f) => ç(i, f, vec![x.clone()])?,
            None => x.clone(),
        };
        c.push((k, x));
    }
    c.sort_by(|a, b| sıra_müq(&a.0, &b.0));
    Ok(c.into_iter().map(|x| x.1).collect())
}

pub fn ilk_min(a: &[D], böyük: bool) -> D {
    let mut ən = a[0].clone();
    for x in &a[1..] {
        let r = sıra_müq(x, &ən);
        if (böyük && r == Ordering::Greater) || (!böyük && r == Ordering::Less) {
            ən = x.clone();
        }
    }
    ən
}

pub fn cəmlə(i: &İcraçı, a: &[D], başlanğıc: D) -> Nəticə {
    let mut s = başlanğıc;
    for x in a {
        if !x.ədəddir() {
            return Err(xəta("TipXətası", format!("ədəd gözlənilirdi, `{}` gəlib", tip_adı(x)), "ALQ-T004"));
        }
        s = i.ikili_hesabla("+", &s, x, None)?;
    }
    Ok(s)
}

/// Python `sum()` (yoxlamasız)
fn py_sum(i: &İcraçı, a: &[D]) -> Nəticə {
    let mut s = D::T(0);
    for x in a {
        s = i.ikili_hesabla("+", &s, x, None)?;
    }
    Ok(s)
}

fn boşluq_kəs(s: &str, c: Option<&str>, sol: bool, sağ: bool) -> String {
    let at = |ch: char| match c {
        Some(c) => c.contains(ch),
        None => ch.is_whitespace(),
    };
    let mut r = s;
    if sol {
        r = r.trim_start_matches(at);
    }
    if sağ {
        r = r.trim_end_matches(at);
    }
    r.to_string()
}

pub fn py_böl(s: &str, ayırıcı: Option<&str>, maks: i64) -> Nəticə<Vec<String>> {
    match ayırıcı {
        None => {
            let mut r = vec![];
            let mut t = s.trim_start();
            while !t.is_empty() {
                if maks >= 0 && r.len() as i64 == maks {
                    r.push(t.trim_end().to_string());
                    break;
                }
                match t.find(char::is_whitespace) {
                    None => {
                        r.push(t.to_string());
                        break;
                    }
                    Some(k) => {
                        r.push(t[..k].to_string());
                        t = t[k..].trim_start();
                    }
                }
            }
            Ok(r)
        }
        Some("") => Err(xəta("DəyərXətası", "boş ayırıcı", "ALQ-R005")),
        Some(a) => {
            if maks < 0 {
                Ok(s.split(a).map(|x| x.to_string()).collect())
            } else {
                Ok(s.splitn(maks as usize + 1, a).map(|x| x.to_string()).collect())
            }
        }
    }
}

fn simvol_say(s: &str) -> usize {
    s.chars().count()
}

fn doldur_sağ(s: &str, n: i64, c: &str) -> String {
    let k = (n - simvol_say(s) as i64).max(0) as usize;
    format!("{}{}", s, c.repeat(k))
}
fn doldur_sol(s: &str, n: i64, c: &str) -> String {
    let k = (n - simvol_say(s) as i64).max(0) as usize;
    format!("{}{}", c.repeat(k), s)
}
fn mərkəz(s: &str, n: i64, c: &str) -> String {
    let u = simvol_say(s) as i64;
    if n <= u {
        return s.to_string();
    }
    let marj = n - u;
    let sol = marj / 2 + (marj & n & 1);
    format!("{}{}{}", c.repeat(sol as usize), s, c.repeat((marj - sol) as usize))
}

fn simvol_indeksi(s: &str, bayt: usize) -> i64 {
    s[..bayt].chars().count() as i64
}

pub fn url_kodla(s: &str) -> String {
    let mut r = String::new();
    for b in s.as_bytes() {
        if b.is_ascii_alphanumeric() || b"_.-~".contains(b) {
            r.push(*b as char);
        } else {
            r.push_str(&format!("%{:02X}", b));
        }
    }
    r
}

pub fn url_aç(s: &str) -> String {
    let b = s.as_bytes();
    let mut r = vec![];
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'%' && i + 2 < b.len() + 0 && i + 2 <= b.len() - 1 {
            if let Ok(x) = u8::from_str_radix(&s[i + 1..i + 3], 16) {
                r.push(x);
                i += 3;
                continue;
            }
        }
        r.push(b[i]);
        i += 1;
    }
    String::from_utf8_lossy(&r).to_string()
}

const B64: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

pub fn base64_kodla(b: &[u8]) -> String {
    let mut r = String::new();
    for c in b.chunks(3) {
        let n = (c[0] as u32) << 16 | (*c.get(1).unwrap_or(&0) as u32) << 8 | *c.get(2).unwrap_or(&0) as u32;
        r.push(B64[(n >> 18) as usize & 63] as char);
        r.push(B64[(n >> 12) as usize & 63] as char);
        r.push(if c.len() > 1 { B64[(n >> 6) as usize & 63] as char } else { '=' });
        r.push(if c.len() > 2 { B64[n as usize & 63] as char } else { '=' });
    }
    r
}

pub fn base64_aç(s: &str) -> Nəticə<Vec<u8>> {
    let mut r = vec![];
    let mut buf = 0u32;
    let mut n = 0;
    for c in s.bytes() {
        if c == b'=' || c.is_ascii_whitespace() {
            continue;
        }
        let v = match B64.iter().position(|x| *x == c) {
            Some(v) => v as u32,
            None => return Err(xəta("KodlaşdırmaXətası", "base64 formatı pozulub", "ALQ-L001")),
        };
        buf = buf << 6 | v;
        n += 6;
        if n >= 8 {
            n -= 8;
            r.push((buf >> n) as u8);
            buf &= (1 << n) - 1;
        }
    }
    Ok(r)
}

fn mətn_formatla(i: &İcraçı, s: &str, a: &[D]) -> Nəticə<String> {
    let mut n = s.to_string();
    for (k, d) in a.iter().enumerate() {
        let m = mətnə(i, d)?;
        n = n.replacen("{}", &m, 1);
        n = n.replace(&format!("{{{k}}}"), &m);
    }
    Ok(n)
}

pub fn yazıyla(n: &BigInt) -> String {
    const BİR: [&str; 10] = ["", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz"];
    const ON: [&str; 10] = ["", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan"];
    if n.is_zero() {
        return "sıfır".into();
    }
    if n.is_negative() {
        return format!("mənfi {}", yazıyla(&-n));
    }
    let mut n = n.clone();
    let mut h: Vec<String> = vec![];
    let min = BigInt::from(1000);
    if n >= min {
        let m = &n / &min;
        h.push(if m == BigInt::from(1) { "min".into() } else { format!("{} min", yazıyla(&m)) });
        n %= &min;
    }
    let n = n.to_i64().unwrap();
    let mut n = n;
    if n >= 100 {
        let y = (n / 100) as usize;
        h.push(if y == 1 { "yüz".into() } else { format!("{} yüz", BİR[y]) });
        n %= 100;
    }
    if n >= 10 {
        h.push(ON[(n / 10) as usize].into());
        n %= 10;
    }
    if n > 0 {
        h.push(BİR[n as usize].into());
    }
    h.retain(|x| !x.is_empty());
    h.join(" ").trim().to_string()
}

pub fn sıra_sayı(n: &D) -> String {
    let s = ["", "birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yeddinci", "səkkizinci", "doqquzuncu", "onuncu"];
    match n.i64() {
        Some(k) if (1..=10).contains(&k) => s[k as usize].into(),
        _ => format!("{}-ci", py_repr(n)),
    }
}

/// Python `round(x, r)` onluq üçün
pub fn yuvarla(x: f64, r: Option<i64>) -> Nəticə {
    match r {
        None | Some(0) if r.is_none() => {
            if !x.is_finite() {
                return Err(xəta("ÇevrilməXətası", "sonsuz və ya ƏdədDeyil tam ədədə çevrilmir", "ALQ-R005"));
            }
            let s = format!("{:.0}", x);
            Ok(D::tam(s.parse::<BigInt>().unwrap_or_default()))
        }
        Some(r) => {
            if !x.is_finite() {
                return Ok(D::O(x));
            }
            if r >= 0 {
                let s = format!("{:.*}", r.min(400) as usize, x);
                Ok(D::O(s.parse().unwrap_or(x)))
            } else {
                let p = 10f64.powi((-r) as i32);
                let y = x / p;
                let s = format!("{:.0}", y);
                Ok(D::O(s.parse::<f64>().unwrap_or(0.0) * p))
            }
        }
        None => unreachable!(),
    }
}

pub fn metod_çağır(i: &İcraçı, o: &D, a: &str, args: Vec<D>, _adlı: Adlı) -> Nəticə {
    let g = &args;
    match o {
        D::S(s) => mətn_metodu(i, s, a, g),
        D::Siyahı(l) => siyahı_metodu(i, o, l, a, g),
        D::Lüğət(l) => lüğət_metodu(i, l, a, g),
        D::Dəst(s) => {
            let el = || dəst_sırası(&s.borrow());
            Ok(match a {
                "əlavə" => {
                    let k = Açar::yeni(arq(g, 0)?)?;
                    s.borrow_mut().insert(k);
                    D::Boş
                }
                "sil" => {
                    if let Ok(k) = Açar::yeni(arq(g, 0)?) {
                        s.borrow_mut().shift_remove(&k);
                    }
                    D::Boş
                }
                "ehtiva" => D::M(Açar::yeni(arq(g, 0)?).map(|k| s.borrow().contains(&k)).unwrap_or(false)),
                "uzunluq" => uz(s.borrow().len()),
                "boşdur" => D::M(s.borrow().is_empty()),
                "təmizlə" => {
                    s.borrow_mut().clear();
                    D::Boş
                }
                "birləşmə" | "kəsişmə" | "fərq" | "simmetrikFərq" => {
                    let D::Dəst(d) = arq(g, 0)? else {
                        return Err(xəta("TipXətası", "dəst əməliyyatı dəst tələb edir", "ALQ-T008"));
                    };
                    let op = match a {
                        "birləşmə" => "|",
                        "kəsişmə" => "&",
                        "fərq" => "-",
                        _ => "^",
                    };
                    let r = dəst_op(op, &s.borrow(), &d.borrow());
                    D::dəst(r)
                }
                "altDəstdir" | "üstDəstdir" => {
                    let op = if a == "altDəstdir" { "<=" } else { ">=" };
                    return i.müqayisə(op, o, &arq(g, 0)?, None);
                }
                "kəsişmir" => {
                    let D::Dəst(d) = arq(g, 0)? else { return Ok(D::M(true)) };
                    let d = d.borrow();
                    D::M(!s.borrow().iter().any(|k| d.contains(k)))
                }
                "siyahıyaÇevir" => D::siyahı(sırala_açarla(i, el(), None)?),
                "çevir" | "filtr" => {
                    let f = arq(g, 0)?;
                    let mut r = Dəst::default();
                    for x in el() {
                        let y = ç(i, &f, vec![x.clone()])?;
                        if a == "çevir" {
                            r.insert(Açar::yeni(y)?);
                        } else if doğru(&y) {
                            r.insert(Açar(x));
                        }
                    }
                    D::dəst(r)
                }
                "klonla" => D::dəst(s.borrow().clone()),
                "mətnƏt" => D::str(mətnə(i, o)?),
                _ => return Err(yoxdur(o, a)),
            })
        }
        D::T(_) | D::BT(_) => {
            let n = o.böyük_tam().unwrap();
            Ok(match a {
                "mətnƏt" => D::str(mətnə(i, o)?),
                "mütləq" => D::tam(n.abs()),
                "işarə" => D::T(if n.is_zero() { 0 } else if n.is_positive() { 1 } else { -1 }),
                "cütdür" => D::M((&n % 2u8).is_zero()),
                "təkdir" => D::M(!(&n % 2u8).is_zero()),
                "kvadrat" => D::tam(&n * &n),
                "onluğaÇevir" => D::O(o.onluq().unwrap()),
                "ikilik" => D::str(if n.is_negative() { format!("-{}", n.abs().to_str_radix(2)) } else { n.to_str_radix(2) }),
                "onaltılıq" => D::str(if n.is_negative() { format!("-{}", n.abs().to_str_radix(16)) } else { n.to_str_radix(16) }),
                "sıraSayı" => D::str(sıra_sayı(o)),
                "yazıyla" => D::str(yazıyla(&n)),
                _ => return Err(yoxdur(o, a)),
            })
        }
        D::O(x) => {
            let x = *x;
            Ok(match a {
                "mətnƏt" => D::str(mətnə(i, o)?),
                "mütləq" => D::O(x.abs()),
                "yuvarlaqlaşdır" => {
                    let r = ixt(g, 0).and_then(|r| r.i64()).filter(|r| *r != 0);
                    return yuvarla(x, r);
                }
                "aşağıYuvarlaq" => return super::eded::onluqdan_tam(x.floor()),
                "yuxarıYuvarlaq" => return super::eded::onluqdan_tam(x.ceil()),
                "kəs" | "tamƏt" => return super::eded::onluqdan_tam(x),
                "tamdır" => D::M(x.is_finite() && x.fract() == 0.0),
                "sonludur" => D::M(x.is_finite()),
                "ədəddir" => D::M(!x.is_nan()),
                _ => return Err(yoxdur(o, a)),
            })
        }
        D::M(b) => Ok(match a {
            "mətnƏt" => D::s(if *b { "doğru" } else { "yanlış" }),
            "tamƏt" => D::T(*b as i64),
            _ => return Err(yoxdur(o, a)),
        }),
        D::Kortej(k) => Ok(match a {
            "uzunluq" => uz(k.len()),
            "siyahıyaÇevir" => D::siyahı(k.to_vec()),
            "mətnƏt" => D::str(mətnə(i, o)?),
            "ehtiva" => {
                let d = arq(g, 0)?;
                let mut r = false;
                for x in k.iter() {
                    if i.bərabərdir(x, &d)? {
                        r = true;
                        break;
                    }
                }
                D::M(r)
            }
            _ => return Err(yoxdur(o, a)),
        }),
        D::Diapazon(r) => {
            let el = || -> Vec<D> { (0..r.uzunluq()).map(|k| D::T(r.al(k))).collect() };
            Ok(match a {
                "siyahıyaÇevir" => D::siyahı(el()),
                "uzunluq" => D::T(r.uzunluq()),
                "ehtiva" => return Ok(D::M(i.üzvlük(&arq(g, 0)?, o, None)?)),
                "mətnƏt" => D::str(py_str(o)),
                "çevir" => {
                    let f = arq(g, 0)?;
                    let mut v = vec![];
                    for x in el() {
                        v.push(ç(i, &f, vec![x])?);
                    }
                    D::siyahı(v)
                }
                "filtr" => {
                    let f = arq(g, 0)?;
                    let mut v = vec![];
                    for x in el() {
                        if doğru(&ç(i, &f, vec![x.clone()])?) {
                            v.push(x);
                        }
                    }
                    D::siyahı(v)
                }
                "cəm" => py_sum(i, &el())?,
                _ => return Err(yoxdur(o, a)),
            })
        }
        D::Gen(gn) => generator_metodu(i, gn, a, g),
        D::Bayt(b) => Ok(match a {
            "uzunluq" => uz(b.len()),
            "mətnƏt" => D::str(String::from_utf8_lossy(b).to_string()),
            "siyahıyaÇevir" => D::siyahı(b.iter().map(|x| D::T(*x as i64)).collect()),
            "base64Kodla" => D::str(base64_kodla(b)),
            _ => return Err(yoxdur(o, a)),
        }),
        D::Element(e) => Ok(match a {
            "HTML" | "mətnƏt" => D::str(element_html(i, e)?),
            "mətn" => D::str(element_mətn(i, e)?),
            "tap" => {
                let t = arq(g, 0)?;
                fn tap(e: &Rc<Element>, t: &D) -> Option<D> {
                    if let D::S(s) = t {
                        if *e.ad == **s {
                            return Some(D::Element(e.clone()));
                        }
                    }
                    for u in e.uşaqlar() {
                        if let D::Element(x) = &u {
                            if let Some(r) = tap(x, t) {
                                return Some(r);
                            }
                        }
                    }
                    None
                }
                tap(e, &t).unwrap_or(D::Boş)
            }
            "atribut" => {
                let k = arq(g, 0)?;
                let st = ixt(g, 1).unwrap_or(D::Boş);
                match Açar::yeni(k) {
                    Ok(k) => e.atributlar().borrow().get(&k).cloned().unwrap_or(st),
                    Err(_) => st,
                }
            }
            "uzunluq" | "uşaqSayı" => uz(e.uşaqlar().len()),
            "boşdur" => D::M(e.uşaqlar().is_empty()),
            _ => return Err(yoxdur(o, a)),
        }),
        D::Gələcək(gl) => Ok(match a {
            "al" => return gl.al(i),
            "başlat" => {
                gl.başlat(i);
                o.clone()
            }
            "bitdi" => D::M(gl.bitdi()),
            "uğurludur" => D::M(gl.uğurlu()),
            "mətnƏt" => D::str(py_str(o)),
            _ => return Err(yoxdur(o, a)),
        }),
        D::LəğvNişanı(n) => Ok(match a {
            "ləğvEt" => {
                n.set(true);
                D::Boş
            }
            "ləğvolunub" => D::M(n.get()),
            "gözlə" => D::M(n.get()),
            "yoxla" => {
                if n.get() {
                    return Err(xəta("Xəta", "əməliyyat ləğv edildi", "ALQ-R021"));
                }
                D::Boş
            }
            _ => return Err(yoxdur(o, a)),
        }),
        _ => Err(yoxdur(o, a)),
    }
}

fn yoxdur(o: &D, a: &str) -> Siqnal {
    xəta("ArqumentXətası", format!("`{}` tipində `{}` üzvü yoxdur", tip_adı(o), a), "ALQ-T006")
}

fn mətn_metodu(i: &İcraçı, s: &Rc<str>, a: &str, g: &[D]) -> Nəticə {
    let o = D::S(s.clone());
    Ok(match a {
        "uzunluq" => uz(simvol_say(s)),
        "baytUzunluğu" => uz(s.len()),
        "böyüyə" => D::str(E::böyüyə(s)),
        "kiçiyə" => D::str(E::kiçiyə(s)),
        "başBöyük" => D::str(E::baş_böyük(s)),
        "hərSözBöyük" => D::str(E::hər_söz_böyük(s)),
        "kəs" | "başKəs" | "sonKəs" => {
            let c = match ixt(g, 0) {
                Some(c) => Some(mətn(&c)?),
                None => None,
            };
            D::str(boşluq_kəs(s, c.as_deref(), a != "sonKəs", a != "başKəs"))
        }
        "əvəz" => {
            let (x, y) = (mətn(&arq(g, 0)?)?, mətn(&arq(g, 1)?)?);
            D::str(py_əvəz(s, &x, &y, -1))
        }
        "əvəzİlk" => {
            let (x, y) = (mətn(&arq(g, 0)?)?, mətn(&arq(g, 1)?)?);
            D::str(py_əvəz(s, &x, &y, 1))
        }
        "böl" => {
            let ay = match ixt(g, 0) {
                Some(x) => Some(mətn(&x)?),
                None => None,
            };
            let maks = ixt(g, 1).and_then(|x| x.i64()).unwrap_or(-1);
            D::siyahı(py_böl(s, ay.as_deref(), if ay.is_some() { maks } else { -1 })?.into_iter().map(D::str).collect())
        }
        "sətirlər" => D::siyahı(s.split('\n').map(D::s).collect()),
        "simvollar" => D::siyahı(s.chars().map(|c| D::str(c.to_string())).collect()),
        "sözlər" => D::siyahı(py_böl(s, None, -1)?.into_iter().map(D::str).collect()),
        "baytlar" => D::siyahı(s.bytes().map(|b| D::T(b as i64)).collect()),
        "birləşdir" => {
            let el = i.siyahıya(&arq(g, 0)?, None)?;
            let mut h = vec![];
            for x in &el {
                h.push(mətnə(i, x)?);
            }
            D::str(h.join(s))
        }
        "ehtiva" => D::M(s.contains(&*mətn(&arq(g, 0)?)?)),
        "başlayır" => D::M(s.starts_with(&*mətn(&arq(g, 0)?)?)),
        "bitir" => D::M(s.ends_with(&*mətn(&arq(g, 0)?)?)),
        "tap" => match s.find(&*mətn(&arq(g, 0)?)?) {
            Some(k) => D::T(simvol_indeksi(s, k)),
            None => D::Boş,
        },
        "sonTap" => match s.rfind(&*mətn(&arq(g, 0)?)?) {
            Some(k) => D::T(simvol_indeksi(s, k)),
            None => D::Boş,
        },
        "hamısınıTap" => {
            let x = mətn(&arq(g, 0)?)?;
            if x.is_empty() {
                D::siyahı((0..=simvol_say(s)).map(|k| D::T(k as i64)).collect())
            } else {
                D::siyahı(s.match_indices(&*x).map(|(k, _)| D::T(simvol_indeksi(s, k))).collect())
            }
        }
        "say" => {
            let x = mətn(&arq(g, 0)?)?;
            if x.is_empty() {
                uz(simvol_say(s) + 1)
            } else {
                uz(s.matches(&*x).count())
            }
        }
        "dilim" => {
            let c: Vec<char> = s.chars().collect();
            let (b, e) = py_dilim(c.len(), ixt(g, 0), ixt(g, 1));
            D::str(c[b..e].iter().collect())
        }
        "təkrar" => D::str(s.repeat(tam(&arq(g, 0)?, "təkrar")?.max(0) as usize)),
        "tərs" => D::str(s.chars().rev().collect()),
        "doldur" | "sağDoldur" | "solDoldur" | "mərkəz" => {
            let n = tam(&arq(g, 0)?, a)?;
            let c = match ixt(g, 1) {
                Some(c) => mətn(&c)?.to_string(),
                None => " ".into(),
            };
            D::str(match a {
                "solDoldur" => doldur_sol(s, n, &c),
                "mərkəz" => mərkəz(s, n, &c),
                _ => doldur_sağ(s, n, &c),
            })
        }
        "boşdur" => D::M(s.is_empty()),
        "yalnızBoşluq" => D::M(!s.is_empty() && s.chars().all(char::is_whitespace)),
        "rəqəmdir" => D::M(!s.is_empty() && s.chars().all(E::rəqəmdir)),
        "hərfdir" => D::M(!s.is_empty() && s.chars().all(E::hərfdir)),
        "müqayisə" => D::T(E::müqayisə(s, &mətn(&arq(g, 0)?)?) as i64),
        "müqayisəHərfsiz" => D::T(E::müqayisə(&E::kiçiyə(s), &E::kiçiyə(&mətn(&arq(g, 0)?)?)) as i64),
        "normalizasiya" => {
            use unicode_normalization::UnicodeNormalization;
            D::str(s.nfc().collect())
        }
        "latınla" => D::str(E::latınla(s)),
        "URLKodla" => D::str(url_kodla(s)),
        "URLAç" => D::str(url_aç(s)),
        "base64Kodla" => D::str(base64_kodla(s.as_bytes())),
        "base64Aç" => {
            let b = base64_aç(s)?;
            match String::from_utf8(b) {
                Ok(x) => D::str(x),
                Err(_) => return Err(xəta("KodlaşdırmaXətası", "UTF-8 deyil", "ALQ-L001")),
            }
        }
        "HTMLQaç" => D::str(html_qaç(s)),
        "formatla" => D::str(mətn_formatla(i, s, g)?),
        "mətnƏt" | "klonla" => o,
        "tamƏt" => match super::eded::tam_oxu(s, 10) {
            Some(n) => n,
            None => return Err(xəta("ÇevrilməXətası", format!("\"{}\" tam ədəd deyil", s), "ALQ-R005")),
        },
        "saitdir" | "samitdir" | "qalınSait" | "incəSait" => {
            let mut c = s.chars();
            let (Some(x), None) = (c.next(), c.next()) else { return Ok(D::M(false)) };
            D::M(match a {
                "saitdir" => E::saitdir(x),
                "samitdir" => E::hərfdir(x) && !E::saitdir(x),
                "qalınSait" => E::qalın(x),
                _ => E::incə(x),
            })
        }
        _ => return Err(yoxdur(&o, a)),
    })
}

fn py_əvəz(s: &str, a: &str, b: &str, say: i64) -> String {
    if a.is_empty() {
        // Python: hər simvolun arasına
        let mut r = String::new();
        let mut k = 0;
        for c in s.chars() {
            if say < 0 || k < say {
                r.push_str(b);
                k += 1;
            }
            r.push(c);
        }
        if say < 0 || k < say {
            r.push_str(b);
        }
        return r;
    }
    if say < 0 {
        s.replace(a, b)
    } else {
        s.replacen(a, b, say as usize)
    }
}

fn siyahı_metodu(i: &İcraçı, o: &D, l: &Rc<std::cell::RefCell<Vec<D>>>, a: &str, g: &[D]) -> Nəticə {
    let kopya = || l.borrow().clone();
    Ok(match a {
        "əlavə" => {
            let x = arq(g, 0)?;
            l.borrow_mut().push(x);
            D::Boş
        }
        "əlavəHamısı" => {
            let el = i.siyahıya(&arq(g, 0)?, None)?;
            l.borrow_mut().extend(el);
            D::Boş
        }
        "daxilEt" => {
            let j = tam(&arq(g, 0)?, "daxilEt")?;
            let x = arq(g, 1)?;
            let mut v = l.borrow_mut();
            let n = v.len() as i64;
            let k = if j < 0 { (j + n).max(0) } else { j.min(n) };
            v.insert(k as usize, x);
            D::Boş
        }
        "sil" => {
            let j = tam(&arq(g, 0)?, "sil")?;
            let n = l.borrow().len();
            match super::cagiris::indeks_həll(j, n) {
                Some(k) => l.borrow_mut().remove(k),
                None => {
                    return Err(xəta("İndeksXətası", format!("indeks {} diapazondan kənardır (uzunluq {})", j, n), "ALQ-R002"))
                }
            }
        }
        "silDəyər" => {
            let d = arq(g, 0)?;
            let v = kopya();
            for (k, x) in v.iter().enumerate() {
                if i.bərabərdir(x, &d)? {
                    l.borrow_mut().remove(k);
                    return Ok(D::M(true));
                }
            }
            D::M(false)
        }
        "silHamısı" => {
            let d = arq(g, 0)?;
            let mut q = vec![];
            for x in kopya() {
                if !i.bərabərdir(&x, &d)? {
                    q.push(x);
                }
            }
            *l.borrow_mut() = q;
            D::Boş
        }
        "sonunuSil" => match l.borrow_mut().pop() {
            Some(x) => x,
            None => return Err(xəta("BoşKolleksiyaXətası", "boş siyahıdan element silinmir", "ALQ-R014")),
        },
        "təmizlə" => {
            l.borrow_mut().clear();
            D::Boş
        }
        "sırala" => {
            let q = match ixt(g, 0) {
                None => sırala_açarla(i, kopya(), None)?,
                Some(f) => {
                    let mut v = kopya();
                    let mut xəta_ = None;
                    v.sort_by(|x, y| {
                        if xəta_.is_some() {
                            return Ordering::Equal;
                        }
                        match ç(i, &f, vec![x.clone(), y.clone()]) {
                            Ok(r) => match super::eded::ədəd_müq(&r, &D::T(0)) {
                                Some(o) => o,
                                None => Ordering::Equal,
                            },
                            Err(e) => {
                                xəta_ = Some(e);
                                Ordering::Equal
                            }
                        }
                    });
                    if let Some(e) = xəta_ {
                        return Err(e);
                    }
                    v
                }
            };
            *l.borrow_mut() = q;
            D::Boş
        }
        "sıralaAçar" => {
            let f = arq(g, 0)?;
            let q = sırala_açarla(i, kopya(), Some(&f))?;
            *l.borrow_mut() = q;
            D::Boş
        }
        "qarışdır" => {
            let mut v = kopya();
            i.təsadüfi.borrow_mut().qarışdır(&mut v);
            *l.borrow_mut() = v;
            D::Boş
        }
        "tərsinəÇevir" => {
            l.borrow_mut().reverse();
            D::Boş
        }
        "sıralanmış" => D::siyahı(sırala_açarla(i, kopya(), ixt(g, 0).as_ref())?),
        "tərs" => D::siyahı(kopya().into_iter().rev().collect()),
        "dilim" => {
            let v = kopya();
            let (b, e) = py_dilim(v.len(), ixt(g, 0), ixt(g, 1));
            D::siyahı(v[b..e].to_vec())
        }
        "çevir" => {
            let f = arq(g, 0)?;
            let mut r = vec![];
            for x in kopya() {
                r.push(ç(i, &f, vec![x])?);
            }
            D::siyahı(r)
        }
        "filtr" => {
            let f = arq(g, 0)?;
            let mut r = vec![];
            for x in kopya() {
                if doğru(&ç(i, &f, vec![x.clone()])?) {
                    r.push(x);
                }
            }
            D::siyahı(r)
        }
        "yığ" | "yığSağdan" => {
            let mut n = arq(g, 0)?;
            let f = arq(g, 1)?;
            let mut v = kopya();
            if a == "yığSağdan" {
                v.reverse();
            }
            for x in v {
                n = ç(i, &f, vec![n, x])?;
            }
            n
        }
        "düzlə" => D::siyahı(düzlə(kopya())),
        "düzləÇevir" => {
            let f = arq(g, 0)?;
            let mut r = vec![];
            for x in kopya() {
                r.push(ç(i, &f, vec![x])?);
            }
            D::siyahı(düzlə(r))
        }
        "təkrarsız" => {
            let mut r: Vec<D> = vec![];
            for x in kopya() {
                let mut var = false;
                for y in &r {
                    if i.bərabərdir(&x, y)? {
                        var = true;
                        break;
                    }
                }
                if !var {
                    r.push(x);
                }
            }
            D::siyahı(r)
        }
        "birləşdir" => {
            let mut v = kopya();
            v.extend(i.siyahıya(&arq(g, 0)?, None)?);
            D::siyahı(v)
        }
        "qrupla" => {
            let f = arq(g, 0)?;
            let mut r = Lüğət::default();
            for x in kopya() {
                let k = Açar::yeni(ç(i, &f, vec![x.clone()])?)?;
                match r.get(&k) {
                    Some(D::Siyahı(s)) => s.borrow_mut().push(x),
                    _ => {
                        r.insert(k, D::siyahı(vec![x]));
                    }
                }
            }
            D::lüğət(r)
        }
        "hissələrə" => {
            let n = tam(&arq(g, 0)?, "hissələrə")?.max(1) as usize;
            D::siyahı(kopya().chunks(n).map(|c| D::siyahı(c.to_vec())).collect())
        }
        "pəncərə" => {
            let n = tam(&arq(g, 0)?, "pəncərə")?;
            let v = kopya();
            if n <= 0 || n as usize > v.len() {
                if n <= 0 {
                    return Ok(D::siyahı((0..=v.len()).map(|_| D::siyahı(vec![])).collect::<Vec<_>>().into_iter().take(v.len() + 1 - 0).collect()));
                }
                D::siyahı(vec![])
            } else {
                D::siyahı(v.windows(n as usize).map(|c| D::siyahı(c.to_vec())).collect())
            }
        }
        "zip" => {
            let b = i.siyahıya(&arq(g, 0)?, None)?;
            D::siyahı(kopya().into_iter().zip(b).map(|(x, y)| D::kortej(vec![x, y])).collect())
        }
        "nömrələ" => D::siyahı(kopya().into_iter().enumerate().map(|(k, x)| D::kortej(vec![D::T(k as i64), x])).collect()),
        "uzunluq" => uz(l.borrow().len()),
        "boşdur" => D::M(l.borrow().is_empty()),
        "ehtiva" => {
            let d = arq(g, 0)?;
            for x in kopya() {
                if i.bərabərdir(&x, &d)? {
                    return Ok(D::M(true));
                }
            }
            D::M(false)
        }
        "tap" | "tapİndeks" => {
            let f = arq(g, 0)?;
            for (k, x) in kopya().into_iter().enumerate() {
                if doğru(&ç(i, &f, vec![x.clone()])?) {
                    return Ok(if a == "tap" { x } else { D::T(k as i64) });
                }
            }
            D::Boş
        }
        "indeks" => {
            let d = arq(g, 0)?;
            for (k, x) in kopya().into_iter().enumerate() {
                if i.bərabərdir(&x, &d)? {
                    return Ok(D::T(k as i64));
                }
            }
            D::Boş
        }
        "sonİndeks" => {
            let d = arq(g, 0)?;
            for (k, x) in kopya().into_iter().enumerate().rev() {
                if i.bərabərdir(&x, &d)? {
                    return Ok(D::T(k as i64));
                }
            }
            D::Boş
        }
        "say" => {
            let d = arq(g, 0)?;
            let mut n = 0;
            for x in kopya() {
                if i.bərabərdir(&x, &d)? {
                    n += 1;
                }
            }
            D::T(n)
        }
        "sayŞərt" | "hamısı" | "hərHansı" | "heçBiri" => {
            let f = arq(g, 0)?;
            let mut n = 0;
            for x in kopya() {
                let r = doğru(&ç(i, &f, vec![x])?);
                match a {
                    "hamısı" if !r => return Ok(D::M(false)),
                    "hərHansı" if r => return Ok(D::M(true)),
                    "heçBiri" if r => return Ok(D::M(false)),
                    _ => {}
                }
                if r {
                    n += 1;
                }
            }
            match a {
                "sayŞərt" => D::T(n),
                "hamısı" => D::M(true),
                "hərHansı" => D::M(false),
                _ => D::M(true),
            }
        }
        "ilk" => l.borrow().first().cloned().unwrap_or(D::Boş),
        "son" => l.borrow().last().cloned().unwrap_or(D::Boş),
        "minimum" | "maksimum" => {
            let v = kopya();
            if v.is_empty() {
                D::Boş
            } else {
                ilk_min(&v, a == "maksimum")
            }
        }
        "cəm" => {
            let v = kopya();
            if v.is_empty() {
                D::T(0)
            } else {
                py_sum(i, &v)?
            }
        }
        "orta" => {
            let v = kopya();
            if v.is_empty() {
                return Err(xəta("BoşKolleksiyaXətası", "boş siyahının ortası yoxdur", "ALQ-R014"));
            }
            let s = py_sum(i, &v)?;
            return i.ikili_hesabla("/", &s, &uz(v.len()), None);
        }
        "hərBiri" => {
            let f = arq(g, 0)?;
            for x in kopya() {
                ç(i, &f, vec![x])?;
            }
            D::Boş
        }
        "klonla" | "siyahıyaÇevir" => D::siyahı(kopya()),
        "al" => {
            let st = ixt(g, 1).unwrap_or(D::Boş);
            match arq(g, 0)? {
                D::T(j) => super::cagiris::indeks_həll(j, l.borrow().len()).map(|k| l.borrow()[k].clone()).unwrap_or(st),
                D::M(b) => super::cagiris::indeks_həll(b as i64, l.borrow().len()).map(|k| l.borrow()[k].clone()).unwrap_or(st),
                _ => st,
            }
        }
        "mətnƏt" => D::str(mətnə(i, o)?),
        _ => return Err(yoxdur(o, a)),
    })
}

fn düzlə(v: Vec<D>) -> Vec<D> {
    let mut r = vec![];
    for x in v {
        match &x {
            D::Siyahı(l) => r.extend(l.borrow().iter().cloned()),
            _ => r.push(x),
        }
    }
    r
}

fn lüğət_metodu(i: &İcraçı, l: &Rc<std::cell::RefCell<Lüğət>>, a: &str, g: &[D]) -> Nəticə {
    let o = D::Lüğət(l.clone());
    let cütlər = || -> Vec<(D, D)> { l.borrow().iter().map(|(k, v)| (k.0.clone(), v.clone())).collect() };
    Ok(match a {
        "al" => {
            let st = ixt(g, 1).unwrap_or(D::Boş);
            let k = Açar::yeni(arq(g, 0)?)?;
            l.borrow().get(&k).cloned().unwrap_or(st)
        }
        "qoy" => {
            let k = Açar::yeni(arq(g, 0)?)?;
            l.borrow_mut().insert(k, arq(g, 1)?);
            D::Boş
        }
        "sil" => {
            let k = Açar::yeni(arq(g, 0)?)?;
            l.borrow_mut().shift_remove(&k).unwrap_or(D::Boş)
        }
        "təmizlə" => {
            l.borrow_mut().clear();
            D::Boş
        }
        "ehtiva" => D::M(Açar::yeni(arq(g, 0)?).map(|k| l.borrow().contains_key(&k)).unwrap_or(false)),
        "ehtivaDəyər" => {
            let d = arq(g, 0)?;
            for (_, v) in cütlər() {
                if i.bərabərdir(&v, &d)? {
                    return Ok(D::M(true));
                }
            }
            D::M(false)
        }
        "uzunluq" => uz(l.borrow().len()),
        "boşdur" => D::M(l.borrow().is_empty()),
        "açarlar" => D::siyahı(l.borrow().keys().map(|k| k.0.clone()).collect()),
        "dəyərlər" => D::siyahı(l.borrow().values().cloned().collect()),
        "cütlər" => D::siyahı(cütlər().into_iter().map(|(k, v)| D::kortej(vec![k, v])).collect()),
        "birləşdir" => {
            let mut r = l.borrow().clone();
            if let D::Lüğət(d) = arq(g, 0)? {
                for (k, v) in d.borrow().iter() {
                    r.insert(k.clone(), v.clone());
                }
            }
            D::lüğət(r)
        }
        "çevir" => {
            let f = arq(g, 0)?;
            let mut r = Lüğət::default();
            for (k, v) in cütlər() {
                let c = ç(i, &f, vec![k.clone(), v])?;
                let el = match &c {
                    D::Kortej(x) if x.len() == 2 => Some((x[0].clone(), x[1].clone())),
                    D::Siyahı(x) if x.borrow().len() == 2 => {
                        let x = x.borrow();
                        Some((x[0].clone(), x[1].clone()))
                    }
                    _ => None,
                };
                match el {
                    Some((a, b)) => r.insert(Açar::yeni(a)?, b),
                    None => r.insert(Açar(k), c),
                };
            }
            D::lüğət(r)
        }
        "filtr" => {
            let f = arq(g, 0)?;
            let mut r = Lüğət::default();
            for (k, v) in cütlər() {
                if doğru(&ç(i, &f, vec![k.clone(), v.clone()])?) {
                    r.insert(Açar(k), v);
                }
            }
            D::lüğət(r)
        }
        "hərBiri" => {
            let f = arq(g, 0)?;
            for (k, v) in cütlər() {
                ç(i, &f, vec![k, v])?;
            }
            D::Boş
        }
        "alVəYaQoy" => {
            let k = Açar::yeni(arq(g, 0)?)?;
            if !l.borrow().contains_key(&k) {
                let d = ç(i, &arq(g, 1)?, vec![])?;
                l.borrow_mut().insert(k.clone(), d);
            }
            l.borrow().get(&k).cloned().unwrap_or(D::Boş)
        }
        "yenilə" => {
            let kd = arq(g, 0)?;
            let k = Açar::yeni(kd.clone())?;
            let cari = l.borrow().get(&k).cloned();
            let Some(cari) = cari else {
                return Err(xəta("AçarXətası", format!("`{}` açarı yoxdur", mətnə(i, &kd)?), "ALQ-R003"));
            };
            let d = ç(i, &arq(g, 1)?, vec![cari])?;
            l.borrow_mut().insert(k, d.clone());
            d
        }
        "tərsÇevir" => {
            let mut r = Lüğət::default();
            for (k, v) in cütlər() {
                r.insert(Açar::yeni(v)?, k);
            }
            D::lüğət(r)
        }
        "klonla" => D::lüğət(l.borrow().clone()),
        "mətnƏt" => D::str(mətnə(i, &o)?),
        _ => return Err(yoxdur(&o, a)),
    })
}

fn generator_metodu(i: &İcraçı, gn: &Rc<Generator>, a: &str, g: &[D]) -> Nəticə {
    let o = D::Gen(gn.clone());
    Ok(match a {
        "növbəti" => match gn.növbəti(i)? {
            Some(x) => x,
            None => return Err(xəta("KolleksiyaXətası", "generator bitdi — daha dəyər yoxdur", "ALQ-R014")),
        },
        "bitdi" => D::M(gn.bitdi.get()),
        "bağla" => {
            gn.bağla();
            D::Boş
        }
        "siyahıyaÇevir" => {
            let mut v = vec![];
            while let Some(x) = gn.növbəti(i)? {
                v.push(x);
            }
            D::siyahı(v)
        }
        "ilk" => {
            let n = arq(g, 0)?;
            let mut v = vec![];
            while let Some(x) = gn.növbəti(i)? {
                if super::eded::ədəd_müq(&uz(v.len()), &n).map(|o| o != Ordering::Less).unwrap_or(true) {
                    break;
                }
                v.push(x);
            }
            D::siyahı(v)
        }
        "çevir" => D::Gen(Generator::yeni(GenMənbə::Çevir(gn.clone(), arq(g, 0)?))),
        "filtr" => D::Gen(Generator::yeni(GenMənbə::Filtr(gn.clone(), arq(g, 0)?))),
        "atla" => D::Gen(Generator::yeni(GenMənbə::Atla(gn.clone(), arq(g, 0)?, 0))),
        "tap" => {
            let f = arq(g, 0)?;
            while let Some(x) = gn.növbəti(i)? {
                if doğru(&ç(i, &f, vec![x.clone()])?) {
                    return Ok(x);
                }
            }
            D::Boş
        }
        "hərBiri" => {
            let f = arq(g, 0)?;
            while let Some(x) = gn.növbəti(i)? {
                ç(i, &f, vec![x])?;
            }
            D::Boş
        }
        "cəm" => {
            let mut v = vec![];
            while let Some(x) = gn.növbəti(i)? {
                v.push(x);
            }
            py_sum(i, &v)?
        }
        "uzunluq" => {
            let mut n = 0;
            while gn.növbəti(i)?.is_some() {
                n += 1;
            }
            D::T(n)
        }
        _ => return Err(yoxdur(&o, a)),
    })
}

// ── Sadalama metodları ─────────────────────────────────────────────────

pub fn sadalama_metodu(e: &Rc<Sadalama>, a: &str) -> Option<D> {
    let e = e.clone();
    Some(match a {
        "hamısı" => daxili("hamısı", 0, Some(0), move |_, _, _| {
            let v = e.variantlar.borrow();
            Ok(D::siyahı(e.sıra.borrow().iter().filter_map(|x| v.get(x).cloned()).collect()))
        }),
        "adla" => daxili("adla", 1, Some(1), move |_, a, _| {
            Ok(match &a[0] {
                D::S(s) => e.variantlar.borrow().get(&**s).cloned().unwrap_or(D::Boş),
                _ => D::Boş,
            })
        }),
        "dəyərlə" => daxili("dəyərlə", 1, Some(1), move |_, a, _| {
            for x in e.sıra.borrow().iter() {
                if let Some(D::SD(v)) = e.variantlar.borrow().get(x) {
                    if py_eq(&v.dəyər, &a[0]) && matches!(v.dəyər, D::M(_)) == matches!(a[0], D::M(_)) || py_eq(&v.dəyər, &a[0]) {
                        return Ok(D::SD(v.clone()));
                    }
                }
            }
            Ok(D::Boş)
        }),
        "sayı" => daxili("sayı", 0, Some(0), move |_, _, _| Ok(uz(e.sıra.borrow().len()))),
        _ => return None,
    })
}

pub fn sadalama_dəyər_metodu(v: &Rc<SadalamaDəyəri>, a: &str) -> Option<D> {
    let v = v.clone();
    Some(match a {
        "sıra" => daxili("sıra", 0, Some(0), move |_, _, _| Ok(D::T(v.sıra_nömrəsi))),
        "dəyər" => daxili("dəyər", 0, Some(0), move |_, _, _| Ok(v.dəyər.clone())),
        "adı" => daxili("adı", 0, Some(0), move |_, _, _| Ok(D::S(v.ad.clone()))),
        "mətnƏt" => daxili("mətnƏt", 0, Some(0), move |_, _, _| Ok(D::S(v.ad.clone()))),
        _ => return None,
    })
}

#[allow(dead_code)]
fn _istifadə(_: BigInt) {}
