//! Əlavə standart modullar (`alqorc/alqor/modullar/*.py`-ın Rust qarşılığı).
//!
//! Python-da olduğu kimi TƏNBƏL yüklənir: `gətir şifrə` yazılmayan
//! proqram `şifrə` modulunu qurmur. Hər modul öz faylındadır
//! (`mod_*.rs`) və `qur() -> Rc<Modul>` funksiyası verir.
//!
//! Bu faylda modulların ortaq köməkçiləri də var: arqumentlərin
//! (mövqeli + adlı) Python imzası kimi həlli, `bayt`/`mətn` yoxlamaları,
//! Python `str()` çevrilməsi, kitabxana obyektlərinin (`Obyekt`)
//! qurulması.

use super::deyerler::*;
use super::icraci::İcraçı;
use std::any::Any;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::{Rc, Weak};

// ═══════════════════════════════════════════════════════════════════════
//  Modul reyestri
// ═══════════════════════════════════════════════════════════════════════

/// Rust icraçısının dəstəklədiyi əlavə modullar (bu platformada).
pub fn adlar() -> Vec<&'static str> {
    #[allow(unused_mut)]
    let mut v = vec!["kodlaşdırma", "şifrə", "sıxma", "csv", "toml", "xml"];
    #[cfg(all(feature = "http", not(target_arch = "wasm32")))]
    v.push("http");
    #[cfg(not(target_arch = "wasm32"))]
    v.push("şəbəkə");
    #[cfg(all(feature = "sqlite", not(target_arch = "wasm32")))]
    v.push("verilənlər");
    v
}

/// Python-da olub bu platformada olmayan modullar — aydın xəta üçün.
/// Yalnız Python icraçısında olan modullar.
pub const PYTHON_YALNIZ: &[&str] = &[
    "pul", "validasiya", "lokalizasiya", "keş", "növbə", "konfiq", "yaml", "html",
    "planlayıcı", "poçt", "şəkil", "qrafik", "pdf", "ffi", "pəncərə", "vidjet", "verilənlər", "http", "şəbəkə",
];

const PLATFORMADA_YOX: &[&str] = &["http", "şəbəkə", "verilənlər"];

fn qur(i: &İcraçı, ad_: &str) -> Option<Nəticə<Rc<Modul>>> {
    let _ = i;
    Some(Ok(match ad_ {
        "kodlaşdırma" => super::mod_kodlasdirma::qur(),
        "şifrə" => super::mod_sifre::qur(),
        "sıxma" => super::mod_sixma::qur(),
        "csv" => super::mod_csv::qur(),
        "toml" => super::mod_toml::qur(),
        "xml" => super::mod_xml::qur(),
        #[cfg(all(feature = "http", not(target_arch = "wasm32")))]
        "http" => super::mod_http::qur(),
        #[cfg(not(target_arch = "wasm32"))]
        "şəbəkə" => super::mod_sebeke::qur(),
        #[cfg(all(feature = "sqlite", not(target_arch = "wasm32")))]
        "verilənlər" => super::mod_verilenler::qur(),
        x if PLATFORMADA_YOX.contains(&x) => {
            return Some(Err(xəta(
                "ArqumentXətası",
                format!("`{}` modulu bu platformada yoxdur", x),
                "ALQ-M001",
            )))
        }
        x if PYTHON_YALNIZ.contains(&x) => {
            return Some(Err(xəta(
                "ArqumentXətası",
                format!("`{}` modulu Rust icraçısında hələ yoxdur — `alqor işlət --motor py` işlədin", x),
                "ALQ-M001",
            )))
        }
        _ => return None,
    }))
}

thread_local! {
    static KEŞ: RefCell<HashMap<(usize, String), Rc<Modul>>> = RefCell::new(HashMap::new());
}

/// `gətir <ad>` — əlavə modul (hər icraçı üçün bir dəfə qurulur).
pub fn modul(i: &İcraçı, ad_: &str) -> Option<Nəticə<Rc<Modul>>> {
    let açar = (i as *const İcraçı as usize, ad_.to_string());
    if let Some(m) = KEŞ.with(|k| k.borrow().get(&açar).cloned()) {
        return Some(Ok(m));
    }
    let n = qur(i, ad_)?;
    if let Ok(m) = &n {
        KEŞ.with(|k| k.borrow_mut().insert(açar, m.clone()));
    }
    Some(n)
}

/// Bütün dəstəklənən modullar (əsas + əlavə) — `alqor-rs modullar`.
pub fn bütün_adlar() -> Vec<&'static str> {
    let mut v = vec![
        "paralel", "sap", "riyaziyyat", "mətn", "təsadüfi", "vaxt", "fayl", "qovluq", "yol", "json", "naxış",
        "sistem", "konsol", "jurnal", "test",
    ];
    #[cfg(not(target_arch = "wasm32"))]
    v.push("veb");
    v.extend(adlar());
    v
}

// ═══════════════════════════════════════════════════════════════════════
//  Arqumentlər
// ═══════════════════════════════════════════════════════════════════════

pub type F = Box<dyn Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə>;

pub fn f(a: &str, min: usize, maks: Option<usize>, f: impl Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə + 'static) -> D {
    daxili(a, min, maks, f)
}

/// Python imzası kimi: mövqeli arqumentlər, sonra adlılar. Naməlum
/// adlı arqument — xəta.
pub fn imza(fad: &str, a: Vec<D>, adlı: Adlı, adlar: &[&str]) -> Nəticə<Vec<Option<D>>> {
    let mut n: Vec<Option<D>> = vec![None; adlar.len().max(a.len())];
    for (k, d) in a.into_iter().enumerate() {
        n[k] = Some(d);
    }
    for (k, d) in adlı {
        match adlar.iter().position(|x| **x == *k) {
            Some(p) => {
                if n[p].is_some() {
                    return Err(xəta(
                        "ArqumentXətası",
                        format!("`{}`: `{}` arqumenti iki dəfə verilib", fad, k),
                        "ALQ-T003",
                    ));
                }
                n[p] = Some(d)
            }
            None => {
                return Err(xəta(
                    "ArqumentXətası",
                    format!("`{}` funksiyasının `{}` parametri yoxdur", fad, k),
                    "ALQ-T003",
                ))
            }
        }
    }
    Ok(n)
}

/// `None` → `boş` (Python-da standart dəyər `None` olan parametrlər).
pub fn al(n: &[Option<D>], k: usize) -> D {
    n.get(k).cloned().flatten().unwrap_or(D::Boş)
}

pub fn var(n: &[Option<D>], k: usize) -> Option<D> {
    n.get(k).cloned().flatten()
}

// ═══════════════════════════════════════════════════════════════════════
//  Tip yoxlamaları və çevirmələr
// ═══════════════════════════════════════════════════════════════════════

/// `_bayt(x, ad)` — mətn (UTF-8) və ya bayt.
pub fn bayt(x: &D, ad_: &str) -> Nəticə<Vec<u8>> {
    match x {
        D::Bayt(b) => Ok(b.to_vec()),
        D::S(s) => Ok(s.as_bytes().to_vec()),
        _ => Err(xəta("TipXətası", format!("`{}` mətn və ya bayt gözləyir, `{}` gəlib", ad_, tip_adı(x)), "ALQ-T001")),
    }
}

/// Python `str(x)`.
pub fn py_s(d: &D) -> String {
    match d {
        D::O(f) => onluq_repr_py(*f),
        D::Lüğət(_) | D::Siyahı(_) | D::Kortej(_) | D::Dəst(_) => py_repr_dərin(d),
        _ => super::cagiris::py_str_sadə(d),
    }
}

/// Python float repr (`inf`, `nan` daxil)
pub fn onluq_repr_py(f: f64) -> String {
    if f.is_nan() {
        "nan".into()
    } else if f.is_infinite() {
        if f > 0.0 { "inf".into() } else { "-inf".into() }
    } else {
        onluq_repr(f)
    }
}

fn py_repr_dərin(d: &D) -> String {
    match d {
        D::O(f) => onluq_repr_py(*f),
        D::Siyahı(l) => format!("[{}]", l.borrow().iter().map(py_repr_dərin).collect::<Vec<_>>().join(", ")),
        D::Kortej(k) => {
            if k.len() == 1 {
                format!("({},)", py_repr_dərin(&k[0]))
            } else {
                format!("({})", k.iter().map(py_repr_dərin).collect::<Vec<_>>().join(", "))
            }
        }
        D::Lüğət(l) => format!(
            "{{{}}}",
            l.borrow().iter().map(|(k, v)| format!("{}: {}", py_repr_dərin(&k.0), py_repr_dərin(v))).collect::<Vec<_>>().join(", ")
        ),
        _ => py_repr(d),
    }
}

/// Python `int(x)` (ədəd və ya rəqəmli mətn)
pub fn py_int(x: &D, ad_: &str) -> Nəticə<i64> {
    match x {
        D::T(i) => Ok(*i),
        D::M(b) => Ok(*b as i64),
        D::O(f) if f.is_finite() => Ok(f.trunc() as i64),
        D::S(s) => s.trim().replace('_', "").parse::<i64>().map_err(|_| {
            xəta("DəyərXətası", format!("invalid literal for int() with base 10: {}", str_repr(s)), "ALQ-R005")
        }),
        _ => Err(xəta("TipXətası", format!("`{}` tam ədəd gözləyir, `{}` gəlib", ad_, tip_adı(x)), "ALQ-T004")),
    }
}

/// Python `float(x)`
pub fn py_float(x: &D, ad_: &str) -> Nəticə<f64> {
    match x {
        D::T(_) | D::BT(_) | D::O(_) | D::M(_) => Ok(x.onluq().unwrap()),
        D::S(s) => s.trim().parse::<f64>().map_err(|_| {
            xəta("DəyərXətası", format!("could not convert string to float: {}", str_repr(s)), "ALQ-R005")
        }),
        _ => Err(xəta("TipXətası", format!("`{}` ədəd gözləyir, `{}` gəlib", ad_, tip_adı(x)), "ALQ-T004")),
    }
}

/// Python truthiness
pub fn doğrudur(d: &D) -> bool {
    match d {
        D::Boş => false,
        D::M(b) => *b,
        D::T(i) => *i != 0,
        D::BT(_) => true,
        D::O(f) => *f != 0.0,
        D::S(s) => !s.is_empty(),
        D::Bayt(b) => !b.is_empty(),
        D::Siyahı(l) => !l.borrow().is_empty(),
        D::Lüğət(l) => !l.borrow().is_empty(),
        D::Dəst(l) => !l.borrow().is_empty(),
        D::Kortej(k) => !k.is_empty(),
        _ => true,
    }
}

pub fn lüğət(c: Vec<(&str, D)>) -> D {
    let mut l = Lüğət::default();
    for (a, d) in c {
        l.insert(Açar(D::s(a)), d);
    }
    D::lüğət(l)
}

pub fn lüğət_s(c: Vec<(String, D)>) -> D {
    let mut l = Lüğət::default();
    for (a, d) in c {
        l.insert(Açar(D::str(a)), d);
    }
    D::lüğət(l)
}

/// Lüğətdən mətn açarı ilə dəyər
pub fn l_al(d: &D, a: &str) -> Option<D> {
    match d {
        D::Lüğət(l) => l.borrow().get(&Açar(D::s(a))).cloned(),
        _ => None,
    }
}

/// Lüğət və ya nümunə → (açar mətni, dəyər) cütləri
pub fn cütlər(d: &D) -> Option<Vec<(D, D)>> {
    match d {
        D::Lüğət(l) => Some(l.borrow().iter().map(|(k, v)| (k.0.clone(), v.clone())).collect()),
        D::Nümunə(n) => Some(n.sahələr.borrow().iter().map(|(k, v)| (D::S(k.clone()), v.clone())).collect()),
        _ => None,
    }
}

/// `_json_hazırla(x)`: nümunə → lüğət (açarlar `str()`), kortej/dəst → siyahı
pub fn json_hazırla(d: &D) -> D {
    match d {
        D::Nümunə(_) | D::Lüğət(_) => {
            let mut l = Lüğət::default();
            for (a, v) in cütlər(d).unwrap() {
                let a = match a {
                    D::S(_) => a,
                    x => D::str(py_s(&x)),
                };
                l.insert(Açar(a), json_hazırla(&v));
            }
            D::lüğət(l)
        }
        D::Siyahı(l) => D::siyahı(l.borrow().iter().map(json_hazırla).collect()),
        D::Kortej(k) => D::siyahı(k.iter().map(json_hazırla).collect()),
        D::Dəst(s) => D::siyahı(dəst_sırası(&s.borrow()).iter().map(json_hazırla).collect()),
        x => x.clone(),
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  JSON (Python `json.dumps`)
// ═══════════════════════════════════════════════════════════════════════

/// Python `json.dumps(x, separators=…, ensure_ascii=…)` — `_json_hazırla`
/// çevrilməsi ilə (nümunə → lüğət, kortej/dəst → siyahı).
pub fn json_dumps(i: &İcraçı, d: &D, sıx: bool, ascii: bool) -> Nəticə<String> {
    let mut s = String::new();
    json_yaz(i, d, if sıx { (",", ":") } else { (", ", ": ") }, ascii, &mut s)?;
    Ok(s)
}

pub fn json_mətn(s: &str, ascii: bool, ç: &mut String) {
    ç.push('"');
    for c in s.chars() {
        match c {
            '"' => ç.push_str("\\\""),
            '\\' => ç.push_str("\\\\"),
            '\n' => ç.push_str("\\n"),
            '\r' => ç.push_str("\\r"),
            '\t' => ç.push_str("\\t"),
            '\u{8}' => ç.push_str("\\b"),
            '\u{c}' => ç.push_str("\\f"),
            c if (c as u32) < 0x20 => ç.push_str(&format!("\\u{:04x}", c as u32)),
            c if ascii && (c as u32) > 0x7e => {
                let mut b = [0u16; 2];
                for u in c.encode_utf16(&mut b) {
                    ç.push_str(&format!("\\u{:04x}", u));
                }
            }
            c => ç.push(c),
        }
    }
    ç.push('"');
}

fn json_yaz(i: &İcraçı, d: &D, ay: (&str, &str), ascii: bool, ç: &mut String) -> Nəticə<()> {
    match d {
        D::Boş => ç.push_str("null"),
        D::M(b) => ç.push_str(if *b { "true" } else { "false" }),
        D::T(_) | D::BT(_) => ç.push_str(&py_repr(d)),
        D::O(f) => ç.push_str(&if f.is_nan() {
            "NaN".to_string()
        } else if f.is_infinite() {
            if *f > 0.0 { "Infinity".into() } else { "-Infinity".into() }
        } else {
            onluq_repr(*f)
        }),
        D::S(s) => json_mətn(s, ascii, ç),
        D::SD(s) => json_mətn(&s.ad, ascii, ç),
        D::Siyahı(_) | D::Kortej(_) | D::Dəst(_) => {
            let el = i.siyahıya(d, None)?;
            ç.push('[');
            for (k, x) in el.iter().enumerate() {
                if k > 0 {
                    ç.push_str(ay.0);
                }
                json_yaz(i, x, ay, ascii, ç)?;
            }
            ç.push(']');
        }
        D::Lüğət(_) | D::Nümunə(_) => {
            ç.push('{');
            for (k, (a, v)) in cütlər(d).unwrap().iter().enumerate() {
                if k > 0 {
                    ç.push_str(ay.0);
                }
                let a = match a {
                    D::S(s) => s.to_string(),
                    D::M(true) => "true".into(),
                    D::M(false) => "false".into(),
                    D::Boş => "null".into(),
                    x => py_s(x),
                };
                json_mətn(&a, ascii, ç);
                ç.push_str(ay.1);
                json_yaz(i, v, ay, ascii, ç)?;
            }
            ç.push('}');
        }
        x => {
            return Err(xəta("TipXətası", format!("Object of type {} is not JSON serializable", tip_adı(x)), "ALQ-T001"))
        }
    }
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════
//  Kitabxana obyektləri
// ═══════════════════════════════════════════════════════════════════════

/// Obyekt qurucusu. `üzvlər` öz obyektinə zəif istinad alır (zəncirlənən
/// metodlar `özü`nü qaytarsın deyə).
pub fn obyekt<T: Any>(
    tip: &'static str,
    veri: Rc<T>,
    mətn: impl Fn(&T) -> String + 'static,
    üzvlər: impl FnOnce(&Weak<Obyekt>, &Rc<T>) -> Vec<(&'static str, D)>,
) -> D {
    let v2 = veri.clone();
    let o = Rc::new_cyclic(|w: &Weak<Obyekt>| {
        let ü = üzvlər(w, &veri);
        let v3 = veri.clone();
        Obyekt {
            tip,
            üzvlər: ü.into_iter().collect(),
            mətn: Some(Box::new(move || mətn(&v3))),
            veri: Some(v2 as Rc<dyn Any>),
        }
    });
    D::Obyekt(o)
}

/// Zəif istinaddan `D` (metod zəncirləri üçün)
pub fn özü(w: &Weak<Obyekt>) -> D {
    w.upgrade().map(D::Obyekt).unwrap_or(D::Boş)
}

/// Obyektin daxili vəziyyəti
pub fn veri<T: Any>(d: &D) -> Option<Rc<T>> {
    match d {
        D::Obyekt(o) => o.veri.clone().and_then(|v| v.downcast::<T>().ok()),
        _ => None,
    }
}

/// Metod: `(icraçı, arqumentlər, adlı)` + vəziyyət
pub fn metod<T: 'static>(
    v: &Rc<T>,
    ad_: &str,
    min: usize,
    maks: Option<usize>,
    g: impl Fn(&İcraçı, &Rc<T>, Vec<D>, Adlı) -> Nəticə + 'static,
) -> D {
    let v = v.clone();
    daxili(ad_, min, maks, move |i, a, adlı| g(i, &v, a, adlı))
}

/// Zəncirlənən metod: `özü`nü də alır
pub fn metod_ö<T: 'static>(
    w: &Weak<Obyekt>,
    v: &Rc<T>,
    ad_: &str,
    min: usize,
    maks: Option<usize>,
    g: impl Fn(&İcraçı, &Rc<T>, D, Vec<D>, Adlı) -> Nəticə + 'static,
) -> D {
    let v = v.clone();
    let w = w.clone();
    daxili(ad_, min, maks, move |i, a, adlı| g(i, &v, özü(&w), a, adlı))
}

/// Alqor funksiyasını çağırır; `Gələcək` nəticəsini gözləyir.
pub fn çağır(i: &İcraçı, f: &D, a: Vec<D>) -> Nəticə {
    let mut n = i.çağır(f, a, vec![], None)?;
    while let D::Gələcək(_) = n {
        n = i.gözlə(n, None)?;
    }
    Ok(n)
}

pub fn çağırılandır(d: &D) -> bool {
    match d {
        D::Nümunə(n) => n.sinif.metod_tap("çağır").is_some(),
        x => çağırıla_bilən(x),
    }
}

pub fn funksiya_tələb(f: &D, ad_: &str) -> Nəticə<D> {
    if !çağırılandır(f) {
        return Err(xəta("TipXətası", format!("`{}` funksiya gözləyir, `{}` gəlib", ad_, tip_adı(f)), "ALQ-T001"));
    }
    Ok(f.clone())
}

/// `müsbət_ədəd(x, ad, sıfır)`
pub fn müsbət_ədəd(x: &D, ad_: &str, sıfır: bool) -> Nəticə<f64> {
    let v = match x {
        D::T(_) | D::BT(_) | D::O(_) => x.onluq().unwrap(),
        _ => f64::NAN,
    };
    if v.is_nan() || v < 0.0 || (v == 0.0 && !sıfır) {
        return Err(xəta(
            "ArqumentXətası",
            format!("`{}` müsbət ədəd olmalıdır, `{}` gəlib", ad_, py_repr_dərin(x)),
            "ALQ-T004",
        ));
    }
    Ok(v)
}

/// Təhlükəsiz təsadüfi baytlar (`secrets.token_bytes`)
pub fn təsadüfi_bayt(n: usize) -> Vec<u8> {
    let mut b = vec![0u8; n];
    #[cfg(not(target_arch = "wasm32"))]
    if getrandom::fill(&mut b).is_ok() {
        return b;
    }
    let mut k = 0;
    while k < n {
        let e = super::platforma::entropiya().to_le_bytes();
        for x in e {
            if k < n {
                b[k] = x;
                k += 1;
            }
        }
    }
    b
}

pub fn hex(b: &[u8]) -> String {
    let mut s = String::with_capacity(b.len() * 2);
    for x in b {
        s.push_str(&format!("{:02x}", x));
    }
    s
}

pub const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
pub const B64URL: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

pub fn b64(b: &[u8], əlifba: &[u8; 64], dolğu: bool) -> String {
    let mut r = String::new();
    for c in b.chunks(3) {
        let n = (c[0] as u32) << 16 | (*c.get(1).unwrap_or(&0) as u32) << 8 | *c.get(2).unwrap_or(&0) as u32;
        r.push(əlifba[(n >> 18) as usize & 63] as char);
        r.push(əlifba[(n >> 12) as usize & 63] as char);
        if c.len() > 1 {
            r.push(əlifba[(n >> 6) as usize & 63] as char);
        } else if dolğu {
            r.push('=');
        }
        if c.len() > 2 {
            r.push(əlifba[n as usize & 63] as char);
        } else if dolğu {
            r.push('=');
        }
    }
    r
}

/// Ciddi base64 açılışı (Python `b64decode(validate=True)` / urlsafe).
/// `Err(())` — format pozulub.
pub fn b64_aç(s: &str, url: bool, ciddi: bool) -> Result<Vec<u8>, ()> {
    let mut r = vec![];
    let mut buf = 0u32;
    let mut n = 0;
    let mut dolğu = 0;
    let mut say = 0;
    for c in s.bytes() {
        if c == b'=' {
            dolğu += 1;
            continue;
        }
        let v = match c {
            b'A'..=b'Z' => c - b'A',
            b'a'..=b'z' => c - b'a' + 26,
            b'0'..=b'9' => c - b'0' + 52,
            b'+' if !url => 62,
            b'/' if !url => 63,
            b'-' if url => 62,
            b'_' if url => 63,
            _ => {
                if ciddi {
                    return Err(());
                }
                continue;
            }
        };
        if dolğu > 0 && ciddi {
            return Err(());
        }
        say += 1;
        buf = buf << 6 | v as u32;
        n += 6;
        if n >= 8 {
            n -= 8;
            r.push((buf >> n) as u8);
            buf &= (1 << n) - 1;
        }
    }
    if say % 4 == 1 {
        return Err(());
    }
    if ciddi && (say + dolğu) % 4 != 0 {
        return Err(());
    }
    Ok(r)
}

/// `(-len(s) % 4)` qədər `=` əlavə edir
pub fn dolğu_əlavə(s: &str) -> String {
    let k = (4 - s.len() % 4) % 4;
    format!("{}{}", s, "=".repeat(k))
}

pub fn utf8(b: Vec<u8>) -> Result<String, ()> {
    String::from_utf8(b).map_err(|_| ())
}

/// CRC-32 (zlib)
pub fn crc32(b: &[u8]) -> u32 {
    crc32_davam(0, b)
}

pub fn crc32_davam(c: u32, b: &[u8]) -> u32 {
    thread_local! {
        static C: [u32; 256] = {
            let mut t = [0u32; 256];
            for n in 0..256u32 {
                let mut c = n;
                for _ in 0..8 {
                    c = if c & 1 != 0 { 0xEDB88320 ^ (c >> 1) } else { c >> 1 };
                }
                t[n as usize] = c;
            }
            t
        };
    }
    C.with(|t| {
        let mut c = !c;
        for &x in b {
            c = t[((c ^ x as u32) & 0xff) as usize] ^ (c >> 8);
        }
        !c
    })
}
