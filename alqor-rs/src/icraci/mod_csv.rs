//! `csv` — CSV oxuma və yazma (modullar/csv_.py). Python `csv` modulunun
//! oxuyucusu (`strict=True`), yazıcısı (`QUOTE_MINIMAL`) və `Sniffer`-i
//! eyni alqoritmlə yazılıb.

use super::deyerler::*;
use super::elave::*;
use super::icraci::İcraçı;
use std::collections::HashMap;
use std::rc::Rc;

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("CSVXətası", m, "ALQ-R005")
}

// ── Sniffer ────────────────────────────────────────────────────────────

/// `_guess_quote_and_delimiter` — dırnaqlı sahələrin ətrafındakı simvol.
fn dırnaq_ayırıcı(data: &str, ayırıcılar: &str) -> Option<char> {
    // Python regex-lərinin sadə qarşılığı: hər dırnaqlı sahəni tapırıq,
    // əvvəl/sonrakı simvola baxırıq (dörd naxış ardıcıllıqla yoxlanılır).
    let c: Vec<char> = data.chars().collect();
    let n = c.len();
    let söz = |x: char| x.is_alphanumeric() || x == '_';
    let ayırıcı_ola_bilər = |x: char| !söz(x) && x != '\n' && x != '"' && x != '\'';
    // (dırnaq, ayırıcı, boşluq) — hər naxış üçün uyğunluqlar
    let mut naxışlar: [Vec<(char, Option<char>, bool)>; 4] = Default::default();
    for (nö, uyğun) in naxışlar.iter_mut().enumerate() {
        let mut i = 0;
        while i < n {
            // dırnağın başlanğıcı
            let (başla, ayr, boşluq) = match nö {
                0 | 2 => {
                    if !ayırıcı_ola_bilər(c[i]) {
                        i += 1;
                        continue;
                    }
                    let d = c[i];
                    let mut j = i + 1;
                    let mut b = false;
                    if j < n && c[j] == ' ' {
                        b = true;
                        j += 1;
                    }
                    if j >= n || (c[j] != '"' && c[j] != '\'') {
                        // boşluqsuz cəhd
                        if b && i + 1 < n && (c[i + 1] == '"' || c[i + 1] == '\'') {
                            (i + 1, Some(d), false)
                        } else {
                            i += 1;
                            continue;
                        }
                    } else {
                        (j, Some(d), b)
                    }
                }
                _ => {
                    if !(i == 0 || c[i - 1] == '\n') || (c[i] != '"' && c[i] != '\'') {
                        i += 1;
                        continue;
                    }
                    (i, None, false)
                }
            };
            let q = c[başla];
            // gövdə: (qq | qeyri-q)*
            let mut j = başla + 1;
            loop {
                if j + 1 < n && c[j] == q && c[j + 1] == q {
                    j += 2;
                } else if j < n && c[j] != q {
                    j += 1;
                } else {
                    break;
                }
            }
            if j >= n || c[j] != q {
                i += 1;
                continue;
            }
            let son = j + 1;
            let ok = match nö {
                0 => son < n && Some(c[son]) == ayr,
                1 => son < n && ayırıcı_ola_bilər(c[son]),
                2 => son >= n || c[son] == '\n',
                _ => son >= n || c[son] == '\n',
            };
            if !ok {
                i += 1;
                continue;
            }
            match nö {
                1 => {
                    let d = c[son];
                    let b = son + 1 < n && c[son + 1] == ' ';
                    uyğun.push((q, Some(d), b));
                    i = son + 1 + b as usize;
                }
                0 => {
                    uyğun.push((q, ayr, boşluq));
                    i = son + 1;
                }
                _ => {
                    uyğun.push((q, ayr, boşluq));
                    i = son;
                }
            }
        }
        if !uyğun.is_empty() {
            break;
        }
    }
    let uyğun = naxışlar.iter().find(|v| !v.is_empty())?;
    let mut sayğac: Vec<(char, usize)> = vec![];
    for (_, d, _) in uyğun {
        if let Some(d) = d {
            if ayırıcılar.contains(*d) {
                match sayğac.iter_mut().find(|(x, _)| x == d) {
                    Some(x) => x.1 += 1,
                    None => sayğac.push((*d, 1)),
                }
            }
        }
    }
    let mut ən: Option<(char, usize)> = None;
    for (d, s) in sayğac {
        if ən.map(|(_, e)| s > e).unwrap_or(true) {
            ən = Some((d, s));
        }
    }
    match ən {
        Some(('\n', _)) | None => None,
        Some((d, _)) => Some(d),
    }
}

/// `_guess_delimiter` — tezliklərin ardıcıllığı.
fn tezlik_ayırıcı(data: &str, ayırıcılar: &str) -> Option<char> {
    let data: Vec<&str> = data.split('\n').filter(|s| !s.is_empty()).collect();
    let parça = 10.min(data.len());
    let mut iterasiya = 0;
    // simvol → (tezlik → say), daxil olma sırası ilə
    let mut tezlik: Vec<Vec<(usize, usize)>> = vec![vec![]; 127];
    let mut modlar: Vec<Option<(usize, i64)>> = vec![None; 127];
    let mut seçilən: Vec<(char, (usize, i64))> = vec![];
    let (mut başla, mut son) = (0usize, parça);
    while başla < data.len() {
        iterasiya += 1;
        for sətir in &data[başla..son.min(data.len())] {
            let mut say = [0usize; 127];
            for ch in sətir.chars() {
                if (ch as u32) < 127 {
                    say[ch as usize] += 1;
                }
            }
            for k in 0..127 {
                let mf = &mut tezlik[k];
                match mf.iter_mut().find(|(f, _)| *f == say[k]) {
                    Some(x) => x.1 += 1,
                    None => mf.push((say[k], 1)),
                }
            }
        }
        for k in 0..127 {
            let items = &tezlik[k];
            if items.is_empty() || (items.len() == 1 && items[0].0 == 0) {
                continue;
            }
            if items.len() > 1 {
                let mut ən = 0;
                for (j, x) in items.iter().enumerate() {
                    if x.1 > items[ən].1 {
                        ən = j;
                    }
                }
                let qalan: usize = items.iter().enumerate().filter(|(j, _)| *j != ən).map(|(_, x)| x.1).sum();
                modlar[k] = Some((items[ən].0, items[ən].1 as i64 - qalan as i64));
            } else {
                modlar[k] = Some((items[0].0, items[0].1 as i64));
            }
        }
        let cəmi = (parça * iterasiya).min(data.len()) as f64;
        let mut ardıcıllıq = 1.0f64;
        while seçilən.is_empty() && ardıcıllıq >= 0.9 {
            for (k, m) in modlar.iter().enumerate() {
                if let Some(v) = m {
                    if v.0 > 0 && v.1 > 0 && (v.1 as f64 / cəmi) >= ardıcıllıq && ayırıcılar.contains(k as u8 as char) {
                        let ch = k as u8 as char;
                        match seçilən.iter_mut().find(|(c, _)| *c == ch) {
                            Some(x) => x.1 = *v,
                            None => seçilən.push((ch, *v)),
                        }
                    }
                }
            }
            ardıcıllıq -= 0.01;
        }
        if seçilən.len() == 1 {
            return Some(seçilən[0].0);
        }
        başla = son;
        son += parça;
    }
    if seçilən.is_empty() {
        return None;
    }
    if seçilən.len() > 1 {
        for d in [',', '\t', ';', ' ', ':'] {
            if seçilən.iter().any(|(c, _)| *c == d) {
                return Some(d);
            }
        }
    }
    let mut v: Vec<((usize, i64), char)> = seçilən.iter().map(|(c, v)| (*v, *c)).collect();
    v.sort();
    v.last().map(|x| x.1)
}

fn ayırıcı_tap(mətn: &str, ayırıcı: &str) -> Nəticə<char> {
    if ayırıcı != "avto" {
        let mut c = ayırıcı.chars();
        return match (c.next(), c.next()) {
            (Some(x), None) => Ok(x),
            _ => Err(xəta("DəyərXətası", "`ayırıcı` bir simvol olmalıdır (və ya \"avto\")", "ALQ-T001")),
        };
    }
    let nümunə = sətirlərə(mətn).into_iter().take(20).collect::<Vec<_>>().join("\n");
    let nümunə = nümunə.replace("\r\n", "\n").replace('\r', "\n");
    let a = ",;\t|";
    Ok(dırnaq_ayırıcı(&nümunə, a).or_else(|| tezlik_ayırıcı(&nümunə, a)).unwrap_or(','))
}

/// Python `str.splitlines()` (sətir sonları atılır)
pub fn sətirlərə(s: &str) -> Vec<String> {
    let mut n = vec![];
    let mut cari = String::new();
    let mut it = s.chars().peekable();
    while let Some(c) = it.next() {
        match c {
            '\n' | '\x0b' | '\x0c' | '\x1c' | '\x1d' | '\x1e' | '\u{85}' | '\u{2028}' | '\u{2029}' => {
                n.push(std::mem::take(&mut cari));
            }
            '\r' => {
                if it.peek() == Some(&'\n') {
                    it.next();
                }
                n.push(std::mem::take(&mut cari));
            }
            c => cari.push(c),
        }
    }
    if !cari.is_empty() {
        n.push(cari);
    }
    n
}

// ── Oxuyucu ────────────────────────────────────────────────────────────

#[derive(PartialEq, Clone, Copy)]
enum V {
    SətirBaşı,
    SahəBaşı,
    Sahədə,
    Dırnaqda,
    DırnaqdaDırnaq,
    CrNl,
}

pub fn oxu_xam(mətn: &str, ayr: char) -> Nəticə<Vec<Vec<String>>> {
    // StringIO(newline=""): sətirlər terminatorları ilə
    let mut sətirlər: Vec<String> = vec![];
    let mut cari = String::new();
    let mut it = mətn.chars().peekable();
    while let Some(c) = it.next() {
        cari.push(c);
        if c == '\n' {
            sətirlər.push(std::mem::take(&mut cari));
        } else if c == '\r' {
            if it.peek() == Some(&'\n') {
                cari.push(it.next().unwrap());
            }
            sətirlər.push(std::mem::take(&mut cari));
        }
    }
    if !cari.is_empty() {
        sətirlər.push(cari);
    }
    let q = '"';
    let mut n = vec![];
    let mut st = V::SətirBaşı;
    let mut sahələr: Vec<String> = vec![];
    let mut sahə = String::new();
    let mut sahə_var = false;
    let mut k = 0;
    loop {
        if k >= sətirlər.len() {
            if sahə_var && !sahə.is_empty() || st == V::Dırnaqda {
                return Err(x_("CSV pozulub: unexpected end of data"));
            }
            break;
        }
        let sətir: Vec<char> = sətirlər[k].chars().collect();
        k += 1;
        let mut simvollar: Vec<Option<char>> = sətir.into_iter().map(Some).collect();
        simvollar.push(None); // EOL
        for c in simvollar {
            if c == Some('\0') {
                return Err(x_("CSV pozulub: line contains NUL"));
            }
            let nl = matches!(c, Some('\n') | Some('\r'));
            let eol = c.is_none();
            macro_rules! saxla {
                () => {{
                    sahələr.push(std::mem::take(&mut sahə));
                    sahə_var = false;
                }};
            }
            let mut st2 = st;
            if st2 == V::SətirBaşı {
                if eol {
                    continue;
                } else if nl {
                    st = V::CrNl;
                    continue;
                }
                st2 = V::SahəBaşı;
            }
            match st2 {
                V::SahəBaşı => {
                    if nl || eol {
                        saxla!();
                        st = if eol { V::SətirBaşı } else { V::CrNl };
                    } else if c == Some(q) {
                        st = V::Dırnaqda;
                        sahə_var = true;
                    } else if c == Some(ayr) {
                        saxla!();
                        st = V::SahəBaşı;
                    } else {
                        sahə.push(c.unwrap());
                        sahə_var = true;
                        st = V::Sahədə;
                    }
                }
                V::Sahədə => {
                    if nl || eol {
                        saxla!();
                        st = if eol { V::SətirBaşı } else { V::CrNl };
                    } else if c == Some(ayr) {
                        saxla!();
                        st = V::SahəBaşı;
                    } else {
                        sahə.push(c.unwrap());
                    }
                }
                V::Dırnaqda => {
                    if eol {
                    } else if c == Some(q) {
                        st = V::DırnaqdaDırnaq;
                    } else {
                        sahə.push(c.unwrap());
                    }
                }
                V::DırnaqdaDırnaq => {
                    if c == Some(q) {
                        sahə.push(q);
                        st = V::Dırnaqda;
                    } else if c == Some(ayr) {
                        saxla!();
                        st = V::SahəBaşı;
                    } else if nl || eol {
                        saxla!();
                        st = if eol { V::SətirBaşı } else { V::CrNl };
                    } else {
                        return Err(x_(format!("CSV pozulub: '{}' expected after '{}'", ayr, q)));
                    }
                }
                V::CrNl => {
                    if nl {
                    } else if eol {
                        st = V::SətirBaşı;
                    } else {
                        return Err(x_(
                            "CSV pozulub: new-line character seen in unquoted field - do you need to open the file with newline=''?",
                        ));
                    }
                }
                V::SətirBaşı => unreachable!(),
            }
        }
        if st == V::SətirBaşı {
            n.push(std::mem::take(&mut sahələr));
        }
    }
    Ok(n)
}

fn çevir(d: &str) -> D {
    let b = d.as_bytes();
    let rəq = |s: &[u8]| !s.is_empty() && s.iter().all(|c| c.is_ascii_digit());
    let t = d.strip_prefix('-').unwrap_or(d);
    if rəq(t.as_bytes()) {
        return D::tam(d.parse::<num_bigint::BigInt>().unwrap());
    }
    // ^-?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$
    let (əsas, us) = match t.find(['e', 'E']) {
        Some(k) => (&t[..k], Some(&t[k + 1..])),
        None => (t, None),
    };
    let əsas_ok = match əsas.split_once('.') {
        Some((a, b)) => (rəq(a.as_bytes()) && b.bytes().all(|c| c.is_ascii_digit())) || (a.is_empty() && rəq(b.as_bytes())),
        None => rəq(əsas.as_bytes()),
    };
    let us_ok = match us {
        None => true,
        Some(u) => rəq(u.strip_prefix(['+', '-']).unwrap_or(u).as_bytes()),
    };
    if əsas_ok && us_ok && !b.is_empty() {
        return D::O(d.parse().unwrap_or(0.0));
    }
    match d {
        "doğru" | "true" => D::M(true),
        "yanlış" | "false" => D::M(false),
        "" => D::Boş,
        _ => D::s(d),
    }
}

pub fn oxu(mətn: &D, ayırıcı: &str, başlıq: bool, çev: bool) -> Nəticə {
    let D::S(m) = mətn else {
        return Err(xəta("TipXətası", format!("`csv.oxu` mətn gözləyir, `{}` gəlib", tip_adı(mətn)), "ALQ-T001"));
    };
    let m = m.trim_start_matches('\u{feff}');
    let a = ayırıcı_tap(m, ayırıcı)?;
    let sətirlər: Vec<Vec<String>> = oxu_xam(m, a)?.into_iter().filter(|s| !s.is_empty()).collect();
    let sətirlər: Vec<Vec<D>> = sətirlər
        .into_iter()
        .enumerate()
        .map(|(i, s)| {
            if çev && (i > 0 || !başlıq) {
                s.iter().map(|x| çevir(x)).collect()
            } else {
                s.into_iter().map(D::str).collect()
            }
        })
        .collect();
    if !başlıq {
        return Ok(D::siyahı(sətirlər.into_iter().map(D::siyahı).collect()));
    }
    if sətirlər.is_empty() {
        return Ok(D::siyahı(vec![]));
    }
    let adlar: Vec<String> = sətirlər[0].iter().map(|x| py_s(x).trim().to_string()).collect();
    let mut təkrar: Vec<&String> = adlar.iter().filter(|x| adlar.iter().filter(|y| y == x).count() > 1).collect();
    təkrar.sort();
    təkrar.dedup();
    if !təkrar.is_empty() {
        return Err(x_(format!(
            "başlıqda təkrarlanan sütun: {}",
            təkrar.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", ")
        )));
    }
    let mut n = vec![];
    for (k, s) in sətirlər[1..].iter().enumerate() {
        if s.len() > adlar.len() {
            return Err(x_(format!("{}-ci sətirdə {} sahə var, başlıqda {}", k + 2, s.len(), adlar.len())));
        }
        let mut l = Lüğət::default();
        for (j, a) in adlar.iter().enumerate() {
            let d = s.get(j).cloned().unwrap_or(if çev { D::Boş } else { D::s("") });
            l.insert(Açar(D::str(a.clone())), d);
        }
        n.push(D::lüğət(l));
    }
    Ok(D::siyahı(n))
}

// ── Yazıcı ─────────────────────────────────────────────────────────────

fn dəyər(d: &D) -> String {
    match d {
        D::Boş => String::new(),
        D::M(true) => "doğru".into(),
        D::M(false) => "yanlış".into(),
        x => py_s(x),
    }
}

fn sətir_yaz(ç: &mut String, sahələr: &[String], ayr: char) {
    let tək = sahələr.len() == 1;
    for (k, s) in sahələr.iter().enumerate() {
        if k > 0 {
            ç.push(ayr);
        }
        let dırnaq = s.chars().any(|c| c == ayr || c == '"' || c == '\n' || c == '\r') || (tək && s.is_empty());
        if dırnaq {
            ç.push('"');
            ç.push_str(&s.replace('"', "\"\""));
            ç.push('"');
        } else {
            ç.push_str(s);
        }
    }
    ç.push('\n');
}

pub fn yaz(i: &İcraçı, n: &[Option<D>]) -> Nəticə<String> {
    let sətirlər = al(n, 0);
    let D::Siyahı(l) = &sətirlər else {
        return Err(xəta("TipXətası", format!("`csv.yaz` siyahı gözləyir, `{}` gəlib", tip_adı(&sətirlər)), "ALQ-T001"));
    };
    let sətirlər = l.borrow().clone();
    let mut ayr = var(n, 1).map(|x| py_s(&x)).unwrap_or(",".into());
    if ayr == "avto" {
        ayr = ",".into();
    }
    let ayr = {
        let mut c = ayr.chars();
        match (c.next(), c.next()) {
            (Some(x), None) => x,
            _ => return Err(xəta("TipXətası", "\"delimiter\" must be a 1-character string", "ALQ-T001")),
        }
    };
    let sütunlar = var(n, 2).filter(|x| doğrudur(x));
    let başlıq = var(n, 3).map(|x| doğrudur(&x)).unwrap_or(true);
    let bom = var(n, 4).map(|x| doğrudur(&x)).unwrap_or(false);
    let mut ç = String::new();
    let lüğətlər = !sətirlər.is_empty() && sətirlər.iter().all(|s| matches!(s, D::Lüğət(_)));
    if lüğətlər || sütunlar.is_some() {
        let mut adlar: Vec<D> = match &sütunlar {
            Some(s) => i.siyahıya(s, None)?,
            None => vec![],
        };
        if adlar.is_empty() {
            for s in &sətirlər {
                for a in i.siyahıya(s, None)? {
                    if !adlar.iter().any(|x| py_eq(x, &a)) {
                        adlar.push(a);
                    }
                }
            }
        }
        if başlıq {
            sətir_yaz(&mut ç, &adlar.iter().map(py_s).collect::<Vec<_>>(), ayr);
        }
        for s in &sətirlər {
            let h: Vec<String> = match s {
                D::Lüğət(l) => {
                    let l = l.borrow();
                    adlar.iter().map(|a| Açar::yeni(a.clone()).ok().and_then(|k| l.get(&k).cloned()).unwrap_or(D::Boş)).map(|d| dəyər(&d)).collect()
                }
                x => i.siyahıya(x, None)?.iter().map(dəyər).collect(),
            };
            sətir_yaz(&mut ç, &h, ayr);
        }
    } else {
        for s in &sətirlər {
            let el = match s {
                D::Siyahı(l) => l.borrow().clone(),
                D::Kortej(k) => k.to_vec(),
                _ => return Err(xəta("TipXətası", "`csv.yaz` sətirləri lüğət və ya siyahı olmalıdır", "ALQ-T001")),
            };
            sətir_yaz(&mut ç, &el.iter().map(dəyər).collect::<Vec<_>>(), ayr);
        }
    }
    Ok(format!("{}{}", if bom { "\u{feff}" } else { "" }, ç))
}

/// Windows-1254 (türk/az) → Unicode
pub fn cp1254(b: &[u8]) -> String {
    const Y: [char; 32] = [
        '€', '\u{81}', '‚', 'ƒ', '„', '…', '†', '‡', 'ˆ', '‰', 'Š', '‹', 'Œ', '\u{8d}', '\u{8e}', '\u{8f}', '\u{90}',
        '‘', '’', '“', '”', '•', '–', '—', '˜', '™', 'š', '›', 'œ', '\u{9d}', '\u{9e}', 'Ÿ',
    ];
    b.iter()
        .map(|&x| match x {
            0x80..=0x9f => Y[(x - 0x80) as usize],
            0xd0 => 'Ğ',
            0xdd => 'İ',
            0xde => 'Ş',
            0xf0 => 'ğ',
            0xfd => 'ı',
            0xfe => 'ş',
            x => x as char,
        })
        .collect()
}

fn fayl_oxu(y: &str) -> Nəticə<String> {
    match std::fs::read(y) {
        Ok(b) => {
            let b = b.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(&b).to_vec();
            Ok(match String::from_utf8(b) {
                Ok(s) => s,
                Err(e) => cp1254(e.as_bytes()),
            })
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            Err(xəta("FaylTapılmadıXətası", format!("\"{}\" faylı tapılmadı", y), "ALQ-R009"))
        }
        Err(e) => Err(xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009")),
    }
}

fn oxu_arq(i: &İcraçı, mətn: D, n: &[Option<D>]) -> Nəticə {
    let _ = i;
    let ayr = var(n, 1).map(|x| py_s(&x)).unwrap_or(",".into());
    let başlıq = var(n, 2).map(|x| doğrudur(&x)).unwrap_or(true);
    let çev = var(n, 3).map(|x| doğrudur(&x)).unwrap_or(false);
    oxu(&mətn, &ayr, başlıq, çev)
}

pub fn qur() -> Rc<Modul> {
    let _: HashMap<(), ()> = HashMap::new();
    Modul::yeni("csv", vec![
        ("oxu", f("oxu", 1, Some(1), |i, a, adlı| {
            let n = imza("oxu", a, adlı, &["mətn", "ayırıcı", "başlıq", "çevir"])?;
            oxu_arq(i, al(&n, 0), &n)
        })),
        ("yaz", f("yaz", 1, Some(1), |i, a, adlı| {
            let n = imza("yaz", a, adlı, &["sətirlər", "ayırıcı", "sütunlar", "başlıq", "bom"])?;
            Ok(D::str(yaz(i, &n)?))
        })),
        ("faylOxu", f("faylOxu", 1, Some(1), |i, a, adlı| {
            let n = imza("faylOxu", a, adlı, &["y", "ayırıcı", "başlıq", "çevir"])?;
            let m = fayl_oxu(&py_s(&al(&n, 0)))?;
            oxu_arq(i, D::str(m), &n)
        })),
        ("faylYaz", f("faylYaz", 2, Some(2), |i, a, adlı| {
            let mut a = a;
            let y = a.remove(0);
            let n = imza("faylYaz", a, adlı, &["sətirlər", "ayırıcı", "sütunlar", "başlıq", "bom"])?;
            let m = yaz(i, &n)?;
            let y = py_s(&y);
            std::fs::write(&y, m).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
            Ok(D::Boş)
        })),
    ])
}
