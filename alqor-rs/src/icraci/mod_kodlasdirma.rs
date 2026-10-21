//! `kodlaşdırma` — Base64, hex, URL, HTML, UTF-8 (modullar/kodlasdirma.py).

use super::deyerler::*;
use super::elave::*;
use std::rc::Rc;

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("FormatXətası", m, "ALQ-R005")
}

fn bayt_(x: &D, ad_: &str) -> Nəticə<Vec<u8>> {
    if let D::Siyahı(l) = x {
        let l = l.borrow();
        if l.iter().all(|b| matches!(b, D::T(_) | D::M(_))) {
            let mut v = vec![];
            for b in l.iter() {
                let n = b.i64().unwrap();
                if !(0..256).contains(&n) {
                    return Err(xəta("DəyərXətası", "bytes must be in range(0, 256)", "ALQ-R005"));
                }
                v.push(n as u8);
            }
            return Ok(v);
        }
    }
    bayt(x, ad_)
}

fn mətn_(b: Vec<u8>, ad_: &str) -> Nəticə {
    utf8(b).map(D::str).map_err(|_| x_(format!("`{}`: nəticə UTF-8 mətn deyil — baytı `…Aç` funksiyası ilə alın", ad_)))
}

pub fn b64_aç_py(m: &D, url: bool) -> Nəticə<Vec<u8>> {
    let s = match m {
        D::Bayt(b) => String::from_utf8_lossy(b).to_string(),
        x => py_s(x),
    };
    let s: String = s.split_whitespace().collect();
    let s = dolğu_əlavə(&s);
    let r = if url {
        b64_aç(&s, true, false)
    } else {
        // validate=True: `[A-Za-z0-9+/]*={0,2}`
        let t = s.trim_end_matches('=');
        if s.len() - t.len() > 2 || !t.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'+' || c == b'/') {
            Err(())
        } else {
            b64_aç(&s, false, false)
        }
    };
    r.map_err(|_| x_("Base64 formatı pozulub"))
}

pub fn hex_aç(m: &str) -> Nəticə<Vec<u8>> {
    let s: String = m.split_whitespace().collect();
    let b = s.as_bytes();
    if b.len() % 2 != 0 {
        return Err(x_("hex formatı pozulub (0-9, a-f cütləri gözlənilir)"));
    }
    let mut r = vec![];
    for c in b.chunks(2) {
        let h = std::str::from_utf8(c).ok().and_then(|h| u8::from_str_radix(h, 16).ok());
        match h {
            Some(x) if c.iter().all(|x| x.is_ascii_hexdigit()) => r.push(x),
            _ => return Err(x_("hex formatı pozulub (0-9, a-f cütləri gözlənilir)")),
        }
    }
    Ok(r)
}

/// `urllib.parse.quote(s, safe)`
pub fn quote(s: &str, safe: &str) -> String {
    let mut r = String::new();
    for &b in s.as_bytes() {
        if b.is_ascii_alphanumeric() || b"_.-~".contains(&b) || safe.as_bytes().contains(&b) {
            r.push(b as char);
        } else {
            r.push_str(&format!("%{:02X}", b));
        }
    }
    r
}

/// `quote_plus` (boşluq → `+`)
pub fn quote_plus(s: &str, safe: &str) -> String {
    quote(s, &format!("{safe} ")).replace(' ', "+")
}

/// `urllib.parse.unquote_to_bytes`
pub fn unquote_bayt(s: &str) -> Vec<u8> {
    let b = s.as_bytes();
    let mut r = vec![];
    let mut k = 0;
    while k < b.len() {
        if b[k] == b'%' && k + 2 < b.len() {
            let h = &b[k + 1..k + 3];
            if h.iter().all(|x| x.is_ascii_hexdigit()) {
                r.push(u8::from_str_radix(std::str::from_utf8(h).unwrap(), 16).unwrap());
                k += 3;
                continue;
            }
        }
        r.push(b[k]);
        k += 1;
    }
    r
}

/// `urllib.parse.unquote` (UTF-8, `replace`)
pub fn unquote(s: &str) -> String {
    if !s.contains('%') {
        return s.to_string();
    }
    String::from_utf8_lossy(&unquote_bayt(s)).to_string()
}

pub fn unquote_plus(s: &str) -> String {
    unquote(&s.replace('+', " "))
}

/// `urllib.parse.parse_qsl(m, keep_blank_values)`
pub fn parse_qsl(m: &str, boşlar: bool) -> Vec<(String, String)> {
    let mut r = vec![];
    for p in m.split('&') {
        if p.is_empty() {
            continue;
        }
        let (a, d) = match p.split_once('=') {
            Some((a, d)) => (a, d),
            None => {
                if !boşlar {
                    continue;
                }
                (p, "")
            }
        };
        if d.is_empty() && !boşlar {
            continue;
        }
        r.push((unquote_plus(a), unquote_plus(d)));
    }
    r
}

/// `parse_qs` — açar → dəyərlər (sıra saxlanılır)
pub fn parse_qs(m: &str, boşlar: bool) -> indexmap::IndexMap<String, Vec<String>> {
    let mut n: indexmap::IndexMap<String, Vec<String>> = Default::default();
    for (a, d) in parse_qsl(m, boşlar) {
        n.entry(a).or_default().push(d);
    }
    n
}

pub fn html_qaç(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;").replace('\'', "&#x27;")
}

const ADLI: &[(&str, &str)] = &[
    ("amp", "&"), ("lt", "<"), ("gt", ">"), ("quot", "\""), ("apos", "'"), ("nbsp", "\u{a0}"),
    ("copy", "©"), ("reg", "®"), ("trade", "™"), ("euro", "€"), ("hellip", "…"), ("mdash", "—"),
    ("ndash", "–"), ("laquo", "«"), ("raquo", "»"), ("lsquo", "‘"), ("rsquo", "’"), ("ldquo", "“"),
    ("rdquo", "”"), ("bull", "•"), ("middot", "·"), ("deg", "°"), ("plusmn", "±"), ("times", "×"),
    ("divide", "÷"), ("sect", "§"), ("para", "¶"), ("cent", "¢"), ("pound", "£"), ("yen", "¥"),
    ("larr", "←"), ("rarr", "→"), ("uarr", "↑"), ("darr", "↓"), ("harr", "↔"), ("iexcl", "¡"),
    ("iquest", "¿"), ("shy", "\u{ad}"), ("frac12", "½"), ("frac14", "¼"), ("frac34", "¾"),
    ("ouml", "ö"), ("Ouml", "Ö"), ("uuml", "ü"), ("Uuml", "Ü"), ("ccedil", "ç"), ("Ccedil", "Ç"),
    ("auml", "ä"), ("Auml", "Ä"), ("eacute", "é"), ("Eacute", "É"), ("egrave", "è"), ("aacute", "á"),
    ("szlig", "ß"), ("ensp", "\u{2002}"), ("emsp", "\u{2003}"), ("thinsp", "\u{2009}"),
    ("hearts", "♥"), ("check", "✓"), ("infin", "∞"), ("ne", "≠"), ("le", "≤"), ("ge", "≥"),
];

/// `html.unescape` (ən çox işlənən adlı varlıqlar + rəqəmli)
pub fn html_aç(s: &str) -> String {
    if !s.contains('&') {
        return s.to_string();
    }
    let mut r = String::new();
    let mut q = s;
    while let Some(k) = q.find('&') {
        r.push_str(&q[..k]);
        let t = &q[k + 1..];
        if let Some(n) = t.strip_prefix('#') {
            let (hexdir, rəq) = match n.strip_prefix(['x', 'X']) {
                Some(h) => (true, h),
                None => (false, n),
            };
            let son = rəq.find(|c: char| !(if hexdir { c.is_ascii_hexdigit() } else { c.is_ascii_digit() })).unwrap_or(rəq.len());
            if son > 0 {
                let v = u32::from_str_radix(&rəq[..son], if hexdir { 16 } else { 10 }).unwrap_or(0xFFFD);
                let c = if (0xD800..=0xDFFF).contains(&v) || v > 0x10FFFF || v == 0 {
                    '\u{FFFD}'
                } else if (0x80..=0x9f).contains(&v) {
                    // Windows-1252 əvəzləri
                    let w = [
                        '€', '\u{81}', '‚', 'ƒ', '„', '…', '†', '‡', 'ˆ', '‰', 'Š', '‹', 'Œ', '\u{8d}', 'Ž',
                        '\u{8f}', '\u{90}', '‘', '’', '“', '”', '•', '–', '—', '˜', '™', 'š', '›', 'œ', '\u{9d}',
                        'ž', 'Ÿ',
                    ];
                    w[(v - 0x80) as usize]
                } else {
                    char::from_u32(v).unwrap_or('\u{FFFD}')
                };
                r.push(c);
                let mut i = 1 + (n.len() - rəq.len()) + son;
                if t[i..].starts_with(';') {
                    i += 1;
                }
                q = &t[i..];
                continue;
            }
        } else {
            let son = t.find(|c: char| !c.is_ascii_alphanumeric()).unwrap_or(t.len());
            let ad_ = &t[..son];
            if let Some((_, v)) = ADLI.iter().find(|(a, _)| *a == ad_) {
                r.push_str(v);
                let mut i = son;
                if t[i..].starts_with(';') {
                    i += 1;
                }
                q = &t[i..];
                continue;
            }
        }
        r.push('&');
        q = t;
    }
    r.push_str(q);
    r
}

fn az_ascii(c: char) -> Option<char> {
    Some(match c {
        'ə' | 'Ə' => 'e',
        'ı' | 'I' | 'İ' => 'i',
        'ö' | 'Ö' => 'o',
        'ü' | 'Ü' => 'u',
        'ç' | 'Ç' => 'c',
        'ş' | 'Ş' => 's',
        'ğ' | 'Ğ' => 'g',
        _ => return None,
    })
}

pub fn slug(m: &str, ayırıcı: &str) -> String {
    let s: String = m.chars().map(|c| az_ascii(c).unwrap_or(c)).collect::<String>().to_lowercase();
    let mut r = String::new();
    let mut ara = false;
    for c in s.chars() {
        if c.is_ascii_lowercase() || c.is_ascii_digit() {
            if ara {
                r.push_str(ayırıcı);
                ara = false;
            }
            r.push(c);
        } else {
            ara = true;
        }
    }
    if ara {
        r.push_str(ayırıcı);
    }
    // Python `.strip(ayırıcı)` — simvollar dəsti
    let ç: Vec<char> = ayırıcı.chars().collect();
    r.trim_matches(|c| ç.contains(&c)).to_string()
}

fn sadə(d: &D) -> String {
    match d {
        D::M(true) => "doğru".into(),
        D::M(false) => "yanlış".into(),
        x => py_s(x),
    }
}

pub fn sorğu_kodla(l: &D) -> Nəticə<String> {
    let c = match l {
        D::Lüğət(_) => cütlər(l).unwrap(),
        _ => return Err(xəta("TipXətası", "`sorğuKodla` lüğət gözləyir", "ALQ-T001")),
    };
    let mut h = vec![];
    for (a, d) in c {
        let a = py_s(&a);
        match &d {
            D::Siyahı(_) | D::Kortej(_) => {
                let el: Vec<D> = match &d {
                    D::Siyahı(l) => l.borrow().clone(),
                    D::Kortej(k) => k.to_vec(),
                    _ => unreachable!(),
                };
                for x in el {
                    h.push(format!("{}={}", quote(&a, ""), quote(&sadə(&x), "")));
                }
            }
            D::Boş => {}
            x => h.push(format!("{}={}", quote(&a, ""), quote(&sadə(x), ""))),
        }
    }
    Ok(h.join("&"))
}

pub fn sorğu_aç(m: &str) -> D {
    let mut l = Lüğət::default();
    for (a, d) in parse_qs(m.trim_start_matches('?'), true) {
        let v = if d.len() == 1 { D::str(d[0].clone()) } else { D::siyahı(d.into_iter().map(D::str).collect()) };
        l.insert(Açar(D::str(a)), v);
    }
    D::lüğət(l)
}

pub fn qur() -> Rc<Modul> {
    Modul::yeni("kodlaşdırma", vec![
        ("base64Kodla", f("base64Kodla", 1, Some(1), |_, a, _| Ok(D::str(b64(&bayt_(&a[0], "base64Kodla")?, B64, true))))),
        ("base64Aç", f("base64Aç", 1, Some(1), |_, a, _| Ok(D::Bayt(Rc::new(b64_aç_py(&a[0], false)?))))),
        ("base64AçMətn", f("base64AçMətn", 1, Some(1), |_, a, _| mətn_(b64_aç_py(&a[0], false)?, "base64AçMətn"))),
        ("base64URLKodla", f("base64URLKodla", 1, Some(1), |_, a, _| Ok(D::str(b64(&bayt_(&a[0], "base64URLKodla")?, B64URL, false))))),
        ("base64URLAç", f("base64URLAç", 1, Some(1), |_, a, _| Ok(D::Bayt(Rc::new(b64_aç_py(&a[0], true)?))))),
        ("hexKodla", f("hexKodla", 1, Some(1), |_, a, _| Ok(D::str(hex(&bayt_(&a[0], "hexKodla")?))))),
        ("hexAç", f("hexAç", 1, Some(1), |_, a, _| Ok(D::Bayt(Rc::new(hex_aç(&py_s(&a[0]))?))))),
        ("urlKodla", f("urlKodla", 1, Some(1), |_, a, _| Ok(D::str(quote(&py_s(&a[0]), ""))))),
        ("urlAç", f("urlAç", 1, Some(1), |_, a, _| Ok(D::str(unquote(&py_s(&a[0])))))),
        ("yolKodla", f("yolKodla", 1, Some(1), |_, a, _| Ok(D::str(quote(&py_s(&a[0]), "/"))))),
        ("sorğuKodla", f("sorğuKodla", 1, Some(1), |_, a, _| Ok(D::str(sorğu_kodla(&a[0])?)))),
        ("sorğuAç", f("sorğuAç", 1, Some(1), |_, a, _| Ok(sorğu_aç(&py_s(&a[0]))))),
        ("htmlQaç", f("htmlQaç", 1, Some(1), |_, a, _| Ok(D::str(html_qaç(&py_s(&a[0])))))),
        ("htmlAç", f("htmlAç", 1, Some(1), |_, a, _| Ok(D::str(html_aç(&py_s(&a[0])))))),
        ("utf8Kodla", f("utf8Kodla", 1, Some(1), |_, a, _| Ok(D::Bayt(Rc::new(py_s(&a[0]).into_bytes()))))),
        ("utf8Aç", f("utf8Aç", 1, Some(1), |_, a, _| mətn_(bayt_(&a[0], "utf8Aç")?, "utf8Aç"))),
        ("baytlar", f("baytlar", 1, Some(1), |_, a, _| {
            Ok(D::siyahı(bayt_(&a[0], "baytlar")?.into_iter().map(|b| D::T(b as i64)).collect()))
        })),
        ("crc32", f("crc32", 1, Some(1), |_, a, _| Ok(D::T(crc32(&bayt_(&a[0], "crc32")?) as i64)))),
        ("slug", f("slug", 1, Some(2), |_, a, adlı| {
            let n = imza("slug", a, adlı, &["m", "ayırıcı"])?;
            let ay = var(&n, 1).map(|x| py_s(&x)).unwrap_or("-".into());
            Ok(D::str(slug(&py_s(&al(&n, 0)), &ay)))
        })),
    ])
}
