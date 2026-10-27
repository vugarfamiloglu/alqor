//! `toml` — TOML oxuma və yazma (modullar/toml_.py). Oxuyucu Python
//! `tomllib`-in (3.13) alqoritmi və xəta mesajları ilə yazılıb.

use super::deyerler::*;
use super::elave::*;
use num_bigint::BigInt;
use std::collections::{HashMap, HashSet};
use std::rc::Rc;

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("TOMLXətası", m, "ALQ-R005")
}

type Açar_ = Vec<String>;

fn açar_repr(k: &[String]) -> String {
    py_repr(&D::kortej(k.iter().map(|s| D::s(s)).collect()))
}

#[derive(Default)]
struct Bayraq {
    bayraqlar: HashSet<u8>,
    rekursiv: HashSet<u8>,
    iç: HashMap<String, Bayraq>,
}

const DONMUŞ: u8 = 0;
const AÇIQ: u8 = 1;

#[derive(Default)]
struct Bayraqlar {
    b: HashMap<String, Bayraq>,
    gözləyən: Vec<(Açar_, u8)>,
}

impl Bayraqlar {
    fn gözləyənə(&mut self, k: Açar_, f: u8) {
        if !self.gözləyən.iter().any(|(a, b)| *a == k && *b == f) {
            self.gözləyən.push((k, f));
        }
    }
    fn gözləyəni_bitir(&mut self) {
        for (k, f) in std::mem::take(&mut self.gözləyən) {
            self.qoy(&k, f, false);
        }
    }
    fn hamısını_sil(&mut self, k: &[String]) {
        let mut c = &mut self.b;
        for x in &k[..k.len() - 1] {
            match c.get_mut(x) {
                Some(n) => c = &mut n.iç,
                None => return,
            }
        }
        c.remove(&k[k.len() - 1]);
    }
    fn qoy(&mut self, k: &[String], f: u8, rekursiv: bool) {
        let mut c = &mut self.b;
        for x in &k[..k.len() - 1] {
            c = &mut c.entry(x.clone()).or_default().iç;
        }
        let n = c.entry(k[k.len() - 1].clone()).or_default();
        if rekursiv {
            n.rekursiv.insert(f);
        } else {
            n.bayraqlar.insert(f);
        }
    }
    fn var(&self, k: &[String], f: u8) -> bool {
        if k.is_empty() {
            return false;
        }
        let mut c = &self.b;
        for x in &k[..k.len() - 1] {
            match c.get(x) {
                None => return false,
                Some(n) => {
                    if n.rekursiv.contains(&f) {
                        return true;
                    }
                    c = &n.iç;
                }
            }
        }
        match c.get(&k[k.len() - 1]) {
            Some(n) => n.bayraqlar.contains(&f) || n.rekursiv.contains(&f),
            None => false,
        }
    }
}

fn a(s: &str) -> Açar {
    Açar(D::s(s))
}

/// `get_or_create_nest`
fn yuva(kök: &D, k: &[String], siyahılar: bool) -> Result<D, ()> {
    let mut c = kök.clone();
    for x in k {
        let D::Lüğət(l) = &c else { return Err(()) };
        let n = {
            let mut l = l.borrow_mut();
            l.entry(a(x)).or_insert_with(|| D::lüğət(Lüğət::default())).clone()
        };
        c = n;
        if siyahılar {
            if let D::Siyahı(s) = &c {
                let son = s.borrow().last().cloned();
                c = son.ok_or(())?;
            }
        }
        if !matches!(c, D::Lüğət(_)) {
            return Err(());
        }
    }
    Ok(c)
}

struct P {
    s: Vec<char>,
}

impl P {
    fn get(&self, p: usize) -> Option<char> {
        self.s.get(p).copied()
    }
    fn starts(&self, p: usize, t: &str) -> bool {
        let mut k = p;
        for c in t.chars() {
            if self.get(k) != Some(c) {
                return false;
            }
            k += 1;
        }
        true
    }
    fn err(&self, pos: usize, msg: &str) -> Siqnal {
        let yer = if pos >= self.s.len() {
            "end of document".to_string()
        } else {
            let sətir = self.s[..pos].iter().filter(|c| **c == '\n').count() + 1;
            let sütun = if sətir == 1 { pos + 1 } else { pos - self.s[..pos].iter().rposition(|c| *c == '\n').unwrap() };
            format!("line {}, column {}", sətir, sütun)
        };
        x_(format!("TOML pozulub: {} (at {})", msg, yer))
    }
    fn skip(&self, mut p: usize, ch: &str) -> usize {
        while let Some(c) = self.get(p) {
            if !ch.contains(c) {
                break;
            }
            p += 1;
        }
        p
    }
    fn skip_bare(&self, mut p: usize) -> usize {
        while let Some(c) = self.get(p) {
            if !bare(c) {
                break;
            }
            p += 1;
        }
        p
    }
    fn skip_until(&self, pos: usize, gözlə: &str, qadağan: fn(char) -> bool, eof_xəta: bool) -> Nəticə<usize> {
        let g: Vec<char> = gözlə.chars().collect();
        let mut yeni = None;
        let mut k = pos;
        while k + g.len() <= self.s.len() {
            if self.s[k..k + g.len()] == g[..] {
                yeni = Some(k);
                break;
            }
            k += 1;
        }
        let yeni = match yeni {
            Some(y) => y,
            None => {
                if eof_xəta {
                    return Err(self.err(self.s.len(), &format!("Expected {}", str_repr(gözlə))));
                }
                self.s.len()
            }
        };
        for k in pos..yeni {
            if qadağan(self.s[k]) {
                return Err(self.err(k, &format!("Found invalid character {}", str_repr(&self.s[k].to_string()))));
            }
        }
        Ok(yeni)
    }
    fn skip_comment(&self, p: usize) -> Nəticə<usize> {
        if self.get(p) == Some('#') {
            return self.skip_until(p + 1, "\n", qadağan_tək, false);
        }
        Ok(p)
    }
    fn skip_ws_comments(&self, mut p: usize) -> Nəticə<usize> {
        loop {
            let əvvəl = p;
            p = self.skip(p, " \t\n");
            p = self.skip_comment(p)?;
            if p == əvvəl {
                return Ok(p);
            }
        }
    }

    fn key(&self, pos: usize) -> Nəticə<(usize, Açar_)> {
        let (mut pos, h) = self.key_part(pos)?;
        let mut k = vec![h];
        pos = self.skip(pos, " \t");
        loop {
            if self.get(pos) != Some('.') {
                return Ok((pos, k));
            }
            pos = self.skip(pos + 1, " \t");
            let (p2, h) = self.key_part(pos)?;
            k.push(h);
            pos = self.skip(p2, " \t");
        }
    }
    fn key_part(&self, pos: usize) -> Nəticə<(usize, String)> {
        match self.get(pos) {
            Some(c) if bare(c) => {
                let p = self.skip_bare(pos);
                Ok((p, self.s[pos..p].iter().collect()))
            }
            Some('\'') => self.literal(pos),
            Some('"') => self.basic(pos + 1, false),
            _ => Err(self.err(pos, "Invalid initial character for a key part")),
        }
    }
    fn literal(&self, pos: usize) -> Nəticə<(usize, String)> {
        let başla = pos + 1;
        let p = self.skip_until(başla, "'", qadağan_tək, true)?;
        Ok((p + 1, self.s[başla..p].iter().collect()))
    }
    fn multiline(&self, pos: usize, literal: bool) -> Nəticə<(usize, String)> {
        let mut pos = pos + 3;
        if self.get(pos) == Some('\n') {
            pos += 1;
        }
        let (mut pos, mut r, delim) = if literal {
            let son = self.skip_until(pos, "'''", qadağan_çox, true)?;
            (son + 3, self.s[pos..son].iter().collect::<String>(), '\'')
        } else {
            let (p, r) = self.basic(pos, true)?;
            (p, r, '"')
        };
        if self.get(pos) != Some(delim) {
            return Ok((pos, r));
        }
        pos += 1;
        if self.get(pos) != Some(delim) {
            r.push(delim);
            return Ok((pos, r));
        }
        pos += 1;
        r.push(delim);
        r.push(delim);
        Ok((pos, r))
    }
    fn basic(&self, mut pos: usize, multi: bool) -> Nəticə<(usize, String)> {
        let qadağan: fn(char) -> bool = if multi { qadağan_çox } else { qadağan_tək };
        let mut r = String::new();
        let mut başla = pos;
        loop {
            let Some(c) = self.get(pos) else { return Err(self.err(pos, "Unterminated string")) };
            if c == '"' {
                if !multi {
                    r.extend(&self.s[başla..pos]);
                    return Ok((pos + 1, r));
                }
                if self.starts(pos, "\"\"\"") {
                    r.extend(&self.s[başla..pos]);
                    return Ok((pos + 3, r));
                }
                pos += 1;
                continue;
            }
            if c == '\\' {
                r.extend(&self.s[başla..pos]);
                let (p, e) = self.escape(pos, multi)?;
                r.push_str(&e);
                pos = p;
                başla = pos;
                continue;
            }
            if qadağan(c) {
                return Err(self.err(pos, &format!("Illegal character {}", str_repr(&c.to_string()))));
            }
            pos += 1;
        }
    }
    fn escape(&self, pos: usize, multi: bool) -> Nəticə<(usize, String)> {
        let id: String = self.s[pos..(pos + 2).min(self.s.len())].iter().collect();
        let mut pos = pos + 2;
        if multi && (id == "\\ " || id == "\\\t" || id == "\\\n") {
            if id != "\\\n" {
                pos = self.skip(pos, " \t");
                match self.get(pos) {
                    None => return Ok((pos, String::new())),
                    Some('\n') => pos += 1,
                    Some(_) => return Err(self.err(pos, "Unescaped '\\' in a string")),
                }
            }
            pos = self.skip(pos, " \t\n");
            return Ok((pos, String::new()));
        }
        if id == "\\u" {
            return self.hex(pos, 4);
        }
        if id == "\\U" {
            return self.hex(pos, 8);
        }
        let r = match id.as_str() {
            "\\b" => "\u{8}",
            "\\t" => "\t",
            "\\n" => "\n",
            "\\f" => "\u{c}",
            "\\r" => "\r",
            "\\\"" => "\"",
            "\\\\" => "\\",
            _ => return Err(self.err(pos, "Unescaped '\\' in a string")),
        };
        Ok((pos, r.to_string()))
    }
    fn hex(&self, pos: usize, n: usize) -> Nəticə<(usize, String)> {
        let h: String = self.s[pos..(pos + n).min(self.s.len())].iter().collect();
        if h.chars().count() != n || !h.chars().all(|c| c.is_ascii_hexdigit()) {
            return Err(self.err(pos, "Invalid hex value"));
        }
        let pos = pos + n;
        let v = u32::from_str_radix(&h, 16).unwrap();
        match char::from_u32(v) {
            Some(c) => Ok((pos, c.to_string())),
            None => Err(self.err(pos, "Escaped character is not a Unicode scalar value")),
        }
    }

    fn array(&self, pos: usize) -> Nəticə<(usize, D)> {
        let mut pos = self.skip_ws_comments(pos + 1)?;
        let mut a = vec![];
        if self.get(pos) == Some(']') {
            return Ok((pos + 1, D::siyahı(a)));
        }
        loop {
            let (p, v) = self.value(pos)?;
            a.push(v);
            pos = self.skip_ws_comments(p)?;
            match self.get(pos) {
                Some(']') => return Ok((pos + 1, D::siyahı(a))),
                Some(',') => {}
                _ => return Err(self.err(pos, "Unclosed array")),
            }
            pos = self.skip_ws_comments(pos + 1)?;
            if self.get(pos) == Some(']') {
                return Ok((pos + 1, D::siyahı(a)));
            }
        }
    }
    fn inline_table(&self, pos: usize) -> Nəticə<(usize, D)> {
        let mut pos = self.skip(pos + 1, " \t");
        let kök = D::lüğət(Lüğət::default());
        let mut fl = Bayraqlar::default();
        if self.get(pos) == Some('}') {
            return Ok((pos + 1, kök));
        }
        loop {
            let (p, key, value) = self.kv(pos)?;
            pos = p;
            let (valideyn, kök_ad) = (&key[..key.len() - 1], &key[key.len() - 1]);
            if fl.var(&key, DONMUŞ) {
                return Err(self.err(pos, &format!("Cannot mutate immutable namespace {}", açar_repr(&key))));
            }
            let nest = yuva(&kök, valideyn, false).map_err(|_| self.err(pos, "Cannot overwrite a value"))?;
            let D::Lüğət(l) = &nest else { unreachable!() };
            if l.borrow().contains_key(&a(kök_ad)) {
                return Err(self.err(pos, &format!("Duplicate inline table key {}", str_repr(kök_ad))));
            }
            let qab = matches!(value, D::Lüğət(_) | D::Siyahı(_));
            l.borrow_mut().insert(a(kök_ad), value);
            pos = self.skip(pos, " \t");
            match self.get(pos) {
                Some('}') => return Ok((pos + 1, kök)),
                Some(',') => {}
                _ => return Err(self.err(pos, "Unclosed inline table")),
            }
            if qab {
                fl.qoy(&key, DONMUŞ, true);
            }
            pos = self.skip(pos + 1, " \t");
        }
    }
    fn kv(&self, pos: usize) -> Nəticə<(usize, Açar_, D)> {
        let (pos, key) = self.key(pos)?;
        if self.get(pos) != Some('=') {
            return Err(self.err(pos, "Expected '=' after a key in a key/value pair"));
        }
        let pos = self.skip(pos + 1, " \t");
        let (pos, v) = self.value(pos)?;
        Ok((pos, key, v))
    }
    fn value(&self, pos: usize) -> Nəticə<(usize, D)> {
        let c = self.get(pos);
        match c {
            Some('"') => {
                if self.starts(pos, "\"\"\"") {
                    return self.multiline(pos, false).map(|(p, s)| (p, D::str(s)));
                }
                return self.basic(pos + 1, false).map(|(p, s)| (p, D::str(s)));
            }
            Some('\'') => {
                if self.starts(pos, "'''") {
                    return self.multiline(pos, true).map(|(p, s)| (p, D::str(s)));
                }
                return self.literal(pos).map(|(p, s)| (p, D::str(s)));
            }
            Some('t') if self.starts(pos, "true") => return Ok((pos + 4, D::M(true))),
            Some('f') if self.starts(pos, "false") => return Ok((pos + 5, D::M(false))),
            Some('[') => return self.array(pos),
            Some('{') => return self.inline_table(pos),
            _ => {}
        }
        if let Some((son, r)) = self.datetime(pos) {
            return match r {
                Some(s) => Ok((son, D::str(s))),
                None => Err(self.err(pos, "Invalid date or datetime")),
            };
        }
        if let Some((son, s)) = self.localtime(pos) {
            return Ok((son, D::str(s)));
        }
        if let Some((son, d)) = self.number(pos) {
            return Ok((son, d));
        }
        let üç: String = self.s[pos..(pos + 3).min(self.s.len())].iter().collect();
        if üç == "inf" || üç == "nan" {
            return Ok((pos + 3, D::O(if üç == "inf" { f64::INFINITY } else { f64::NAN })));
        }
        let dörd: String = self.s[pos..(pos + 4).min(self.s.len())].iter().collect();
        match dörd.as_str() {
            "-inf" => return Ok((pos + 4, D::O(f64::NEG_INFINITY))),
            "+inf" => return Ok((pos + 4, D::O(f64::INFINITY))),
            "-nan" | "+nan" => return Ok((pos + 4, D::O(f64::NAN))),
            _ => {}
        }
        Err(self.err(pos, "Invalid value"))
    }

    fn rəqəmlər(&self, p: usize, n: usize) -> Option<u32> {
        let mut v = 0;
        for k in 0..n {
            let c = self.get(p + k)?;
            v = v * 10 + c.to_digit(10).filter(|_| c.is_ascii_digit())?;
        }
        Some(v)
    }
    /// `HH:MM:SS(.ffffff)?` — (son, saat, dəq, san, mikro)
    fn vaxt(&self, p: usize) -> Option<(usize, u32, u32, u32, Option<u32>)> {
        let s = self.rəqəmlər(p, 2)?;
        if self.get(p + 2) != Some(':') {
            return None;
        }
        let d = self.rəqəmlər(p + 3, 2)?;
        if self.get(p + 5) != Some(':') {
            return None;
        }
        let sn = self.rəqəmlər(p + 6, 2)?;
        // [01][0-9]|2[0-3], [0-5][0-9]
        if s > 23 || d > 59 || sn > 59 {
            return None;
        }
        let mut son = p + 8;
        let mut mikro = None;
        if self.get(son) == Some('.') && self.get(son + 1).map(|c| c.is_ascii_digit()).unwrap_or(false) {
            let mut k = son + 1;
            let mut r = String::new();
            while let Some(c) = self.get(k).filter(|c| c.is_ascii_digit()) {
                if r.len() < 6 {
                    r.push(c);
                }
                k += 1;
            }
            while r.len() < 6 {
                r.push('0');
            }
            mikro = Some(r.parse().unwrap());
            son = k;
        }
        Some((son, s, d, sn, mikro))
    }
    fn localtime(&self, p: usize) -> Option<(usize, String)> {
        let (son, s, d, sn, m) = self.vaxt(p)?;
        Some((son, vaxt_iso(s, d, sn, m.unwrap_or(0))))
    }
    /// `Some((son, None))` — naxış uyğundur, tarix etibarsızdır
    fn datetime(&self, p: usize) -> Option<(usize, Option<String>)> {
        let il = self.rəqəmlər(p, 4)?;
        if self.get(p + 4) != Some('-') {
            return None;
        }
        let ay = self.rəqəmlər(p + 5, 2)?;
        if self.get(p + 7) != Some('-') {
            return None;
        }
        let gün = self.rəqəmlər(p + 8, 2)?;
        if !(1..=12).contains(&ay) || !(1..=31).contains(&gün) {
            return None;
        }
        let tarix_ok = gün <= ay_günləri(il as i32, ay) && il >= 1;
        let tarix = format!("{:04}-{:02}-{:02}", il, ay, gün);
        let mut son = p + 10;
        let mut nəticə = tarix.clone();
        if let Some(c) = self.get(son) {
            if c == 'T' || c == 't' || c == ' ' {
                if let Some((v_son, s, d, sn, m)) = self.vaxt(son + 1) {
                    son = v_son;
                    let mut zona = String::new();
                    match self.get(son) {
                        Some('Z') | Some('z') => {
                            zona = "+00:00".into();
                            son += 1;
                        }
                        Some(işarə @ ('+' | '-')) => {
                            if let (Some(zs), Some(':'), Some(zd)) =
                                (self.rəqəmlər(son + 1, 2), self.get(son + 3), self.rəqəmlər(son + 4, 2))
                            {
                                if zs <= 23 && zd <= 59 {
                                    zona = if zs == 0 && zd == 0 { "+00:00".into() } else { format!("{}{:02}:{:02}", işarə, zs, zd) };
                                    son += 6;
                                }
                            }
                        }
                        _ => {}
                    }
                    nəticə = format!("{}T{}{}", tarix, vaxt_iso(s, d, sn, m.unwrap_or(0)), zona);
                }
            }
        }
        Some((son, if tarix_ok { Some(nəticə) } else { None }))
    }
    fn number(&self, p: usize) -> Option<(usize, D)> {
        let c = |k: usize| self.get(k);
        // 0x / 0b / 0o
        if c(p) == Some('0') {
            for (ön, baza, ok) in [('x', 16u32, (|ch: char| ch.is_ascii_hexdigit()) as fn(char) -> bool), ('b', 2, |ch| ch == '0' || ch == '1'), ('o', 8, |ch| ('0'..='7').contains(&ch))] {
                if c(p + 1) == Some(ön) && c(p + 2).map(ok).unwrap_or(false) {
                    let mut k = p + 3;
                    loop {
                        if c(k).map(ok).unwrap_or(false) {
                            k += 1;
                        } else if c(k) == Some('_') && c(k + 1).map(ok).unwrap_or(false) {
                            k += 2;
                        } else {
                            break;
                        }
                    }
                    let t: String = self.s[p + 2..k].iter().filter(|x| **x != '_').collect();
                    return Some((k, D::tam(BigInt::parse_bytes(t.as_bytes(), baza).unwrap())));
                }
            }
        }
        let rəq = |k: usize| c(k).map(|x| x.is_ascii_digit()).unwrap_or(false);
        let rəqəm_ardı = |mut k: usize| -> usize {
            // [0-9](?:_?[0-9])* — başlanğıc rəqəm artıq yoxlanılıb
            k += 1;
            loop {
                if rəq(k) {
                    k += 1;
                } else if c(k) == Some('_') && rəq(k + 1) {
                    k += 2;
                } else {
                    return k;
                }
            }
        };
        let mut k = p;
        if matches!(c(k), Some('+') | Some('-')) {
            k += 1;
        }
        if c(k) == Some('0') {
            k += 1;
        } else if c(k).map(|x| ('1'..='9').contains(&x)).unwrap_or(false) {
            k = rəqəm_ardı(k);
        } else {
            return None;
        }
        let tam_son = k;
        if c(k) == Some('.') && rəq(k + 1) {
            k = rəqəm_ardı(k + 1);
        }
        if matches!(c(k), Some('e') | Some('E')) {
            let mut j = k + 1;
            if matches!(c(j), Some('+') | Some('-')) {
                j += 1;
            }
            if rəq(j) {
                k = rəqəm_ardı(j);
            }
        }
        let t: String = self.s[p..k].iter().filter(|x| **x != '_').collect();
        if k == tam_son {
            Some((k, D::tam(t.parse::<BigInt>().unwrap())))
        } else {
            Some((k, D::O(t.parse::<f64>().unwrap())))
        }
    }

    fn sənəd(&self) -> Nəticə<D> {
        let kök = D::lüğət(Lüğət::default());
        let mut fl = Bayraqlar::default();
        let mut başlıq: Açar_ = vec![];
        let mut pos = 0;
        loop {
            pos = self.skip(pos, " \t");
            let Some(ch) = self.get(pos) else { break };
            if ch == '\n' {
                pos += 1;
                continue;
            }
            if bare(ch) || ch == '"' || ch == '\'' {
                pos = self.key_value_rule(pos, &kök, &mut fl, &başlıq)?;
                pos = self.skip(pos, " \t");
            } else if ch == '[' {
                fl.gözləyəni_bitir();
                if self.get(pos + 1) == Some('[') {
                    let (p, k) = self.list_rule(pos, &kök, &mut fl)?;
                    pos = p;
                    başlıq = k;
                } else {
                    let (p, k) = self.dict_rule(pos, &kök, &mut fl)?;
                    pos = p;
                    başlıq = k;
                }
                pos = self.skip(pos, " \t");
            } else if ch != '#' {
                return Err(self.err(pos, "Invalid statement"));
            }
            pos = self.skip_comment(pos)?;
            match self.get(pos) {
                None => break,
                Some('\n') => pos += 1,
                Some(_) => return Err(self.err(pos, "Expected newline or end of document after a statement")),
            }
        }
        Ok(kök)
    }
    fn dict_rule(&self, pos: usize, kök: &D, fl: &mut Bayraqlar) -> Nəticə<(usize, Açar_)> {
        let pos = self.skip(pos + 1, " \t");
        let (pos, key) = self.key(pos)?;
        if fl.var(&key, AÇIQ) || fl.var(&key, DONMUŞ) {
            return Err(self.err(pos, &format!("Cannot declare {} twice", açar_repr(&key))));
        }
        fl.qoy(&key, AÇIQ, false);
        yuva(kök, &key, true).map_err(|_| self.err(pos, "Cannot overwrite a value"))?;
        if self.get(pos) != Some(']') {
            return Err(self.err(pos, "Expected ']' at the end of a table declaration"));
        }
        Ok((pos + 1, key))
    }
    fn list_rule(&self, pos: usize, kök: &D, fl: &mut Bayraqlar) -> Nəticə<(usize, Açar_)> {
        let pos = self.skip(pos + 2, " \t");
        let (pos, key) = self.key(pos)?;
        if fl.var(&key, DONMUŞ) {
            return Err(self.err(pos, &format!("Cannot mutate immutable namespace {}", açar_repr(&key))));
        }
        fl.hamısını_sil(&key);
        fl.qoy(&key, AÇIQ, false);
        let ok = (|| -> Result<(), ()> {
            let c = yuva(kök, &key[..key.len() - 1], true)?;
            let D::Lüğət(l) = &c else { return Err(()) };
            let son = &key[key.len() - 1];
            let mövcud = l.borrow().get(&a(son)).cloned();
            match mövcud {
                Some(D::Siyahı(s)) => s.borrow_mut().push(D::lüğət(Lüğət::default())),
                Some(_) => return Err(()),
                None => {
                    l.borrow_mut().insert(a(son), D::siyahı(vec![D::lüğət(Lüğət::default())]));
                }
            }
            Ok(())
        })();
        ok.map_err(|_| self.err(pos, "Cannot overwrite a value"))?;
        if !self.starts(pos, "]]") {
            return Err(self.err(pos, "Expected ']]' at the end of an array declaration"));
        }
        Ok((pos + 2, key))
    }
    fn key_value_rule(&self, pos: usize, kök: &D, fl: &mut Bayraqlar, başlıq: &Açar_) -> Nəticə<usize> {
        let (pos, key, value) = self.kv(pos)?;
        let (valideyn, son) = (&key[..key.len() - 1], &key[key.len() - 1]);
        let mut mütləq_valideyn = başlıq.clone();
        mütləq_valideyn.extend(valideyn.iter().cloned());
        for i in 1..key.len() {
            let mut ck = başlıq.clone();
            ck.extend(key[..i].iter().cloned());
            if fl.var(&ck, AÇIQ) {
                return Err(self.err(pos, &format!("Cannot redefine namespace {}", açar_repr(&ck))));
            }
            fl.gözləyənə(ck, AÇIQ);
        }
        if fl.var(&mütləq_valideyn, DONMUŞ) {
            return Err(self.err(pos, &format!("Cannot mutate immutable namespace {}", açar_repr(&mütləq_valideyn))));
        }
        let nest = yuva(kök, &mütləq_valideyn, true).map_err(|_| self.err(pos, "Cannot overwrite a value"))?;
        let D::Lüğət(l) = &nest else { unreachable!() };
        if l.borrow().contains_key(&a(son)) {
            return Err(self.err(pos, "Cannot overwrite a value"));
        }
        if matches!(value, D::Lüğət(_) | D::Siyahı(_)) {
            let mut tam = başlıq.clone();
            tam.extend(key.iter().cloned());
            fl.qoy(&tam, DONMUŞ, true);
        }
        l.borrow_mut().insert(a(son), value);
        Ok(pos)
    }
}

fn bare(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '-' || c == '_'
}

fn qadağan_tək(c: char) -> bool {
    ((c as u32) < 32 && c != '\t') || c as u32 == 127
}

fn qadağan_çox(c: char) -> bool {
    ((c as u32) < 32 && c != '\t' && c != '\n') || c as u32 == 127
}

fn vaxt_iso(s: u32, d: u32, sn: u32, m: u32) -> String {
    if m == 0 {
        format!("{:02}:{:02}:{:02}", s, d, sn)
    } else {
        format!("{:02}:{:02}:{:02}.{:06}", s, d, sn, m)
    }
}

fn ay_günləri(il: i32, ay: u32) -> u32 {
    match ay {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        _ => {
            if (il % 4 == 0 && il % 100 != 0) || il % 400 == 0 {
                29
            } else {
                28
            }
        }
    }
}

pub fn oxu(m: &D) -> Nəticə {
    let D::S(s) = m else {
        return Err(xəta("TipXətası", format!("`toml.oxu` mətn gözləyir, `{}` gəlib", tip_adı(m)), "ALQ-T001"));
    };
    let s = s.trim_start_matches('\u{feff}').replace("\r\n", "\n");
    P { s: s.chars().collect() }.sənəd()
}

// ── Yazma ──────────────────────────────────────────────────────────────

fn açar_yaz(a: &D) -> String {
    let a = py_s(a);
    if !a.is_empty() && a.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-') {
        a
    } else {
        mətn_yaz(&a)
    }
}

fn mətn_yaz(s: &str) -> String {
    let mut n = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => n.push_str("\\\""),
            '\\' => n.push_str("\\\\"),
            '\n' => n.push_str("\\n"),
            '\t' => n.push_str("\\t"),
            '\r' => n.push_str("\\r"),
            c if (c as u32) < 0x20 || c as u32 == 0x7f => n.push_str(&format!("\\u{:04X}", c as u32)),
            c => n.push(c),
        }
    }
    n.push('"');
    n
}

fn sadələşdir(i: &super::icraci::İcraçı, d: &D) -> Nəticə {
    Ok(match d {
        D::Nümunə(_) | D::Lüğət(_) => {
            let nümunə = matches!(d, D::Nümunə(_));
            let mut l = Lüğət::default();
            for (a, v) in cütlər(d).unwrap() {
                if !nümunə && v.boşdur() {
                    continue;
                }
                l.insert(Açar(a), sadələşdir(i, &v)?);
            }
            D::lüğət(l)
        }
        D::Siyahı(_) | D::Kortej(_) | D::Dəst(_) => {
            let mut v = vec![];
            for x in i.siyahıya(d, None)? {
                v.push(sadələşdir(i, &x)?);
            }
            D::siyahı(v)
        }
        x => x.clone(),
    })
}

fn dəyər_yaz(d: &D) -> Nəticə<String> {
    Ok(match d {
        D::M(b) => if *b { "true".into() } else { "false".into() },
        D::T(_) | D::BT(_) => py_repr(d),
        D::O(f) => {
            if f.is_nan() {
                "nan".into()
            } else if f.is_infinite() {
                if *f > 0.0 { "inf".into() } else { "-inf".into() }
            } else {
                onluq_repr(*f)
            }
        }
        D::S(s) => mətn_yaz(s),
        D::Siyahı(l) => {
            let mut h = vec![];
            for x in l.borrow().iter() {
                h.push(dəyər_yaz(x)?);
            }
            format!("[{}]", h.join(", "))
        }
        D::Lüğət(l) => {
            let mut h = vec![];
            for (a, v) in l.borrow().iter() {
                h.push(format!("{} = {}", açar_yaz(&a.0), dəyər_yaz(v)?));
            }
            format!("{{{}}}", h.join(", "))
        }
        D::Boş => return Err(x_("TOML-da `boş` dəyər yoxdur — açarı buraxın")),
        x => return Err(x_(format!("`{}` TOML-a yazıla bilmir", tip_adı(x)))),
    })
}

fn cədvəl_siyahısı(d: &D) -> bool {
    match d {
        D::Siyahı(l) => {
            let l = l.borrow();
            !l.is_empty() && l.iter().all(|x| matches!(x, D::Lüğət(_)))
        }
        _ => false,
    }
}

fn cədvəl_yaz(l: &D, yol: &[String], s: &mut Vec<String>) -> Nəticə<()> {
    let c = cütlər(l).unwrap();
    for (a, d) in &c {
        if !matches!(d, D::Lüğət(_)) && !cədvəl_siyahısı(d) {
            s.push(format!("{} = {}", açar_yaz(a), dəyər_yaz(d)?));
        }
    }
    for (a, d) in &c {
        if let D::Lüğət(alt_l) = d {
            let mut alt = yol.to_vec();
            alt.push(açar_yaz(a));
            let dəyərlər: Vec<D> = alt_l.borrow().values().cloned().collect();
            if dəyərlər.iter().any(|x| !matches!(x, D::Lüğət(_)) && !cədvəl_siyahısı(x)) || dəyərlər.is_empty() {
                if !s.is_empty() {
                    s.push(String::new());
                }
                s.push(format!("[{}]", alt.join(".")));
            }
            cədvəl_yaz(d, &alt, s)?;
        } else if cədvəl_siyahısı(d) {
            let mut alt = yol.to_vec();
            alt.push(açar_yaz(a));
            let D::Siyahı(el) = d else { unreachable!() };
            for x in el.borrow().iter() {
                if !s.is_empty() {
                    s.push(String::new());
                }
                s.push(format!("[[{}]]", alt.join(".")));
                cədvəl_yaz(x, &alt, s)?;
            }
        }
    }
    Ok(())
}

pub fn yaz(i: &super::icraci::İcraçı, l: &D) -> Nəticə<String> {
    let l = sadələşdir(i, l)?;
    if !matches!(l, D::Lüğət(_)) {
        return Err(xəta("TipXətası", format!("`toml.yaz` lüğət gözləyir, `{}` gəlib", tip_adı(&l)), "ALQ-T001"));
    }
    let mut s = vec![];
    cədvəl_yaz(&l, &[], &mut s)?;
    Ok(s.join("\n") + "\n")
}

fn fayl_oxu(y: &str) -> Nəticə<String> {
    match std::fs::read(y) {
        Ok(b) => String::from_utf8(b).map_err(|_| xəta("KodlaşdırmaXətası", format!("\"{}\" faylı UTF-8 deyil", y), "ALQ-L001")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            Err(xəta("FaylTapılmadıXətası", format!("\"{}\" faylı tapılmadı", y), "ALQ-R009"))
        }
        Err(e) => Err(xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009")),
    }
}

pub fn qur() -> Rc<Modul> {
    Modul::yeni("toml", vec![
        ("oxu", f("oxu", 1, Some(1), |_, a, _| oxu(&a[0]))),
        ("yaz", f("yaz", 1, Some(1), |i, a, _| Ok(D::str(yaz(i, &a[0])?)))),
        ("faylOxu", f("faylOxu", 1, Some(1), |_, a, _| oxu(&D::str(fayl_oxu(&py_s(&a[0]))?)))),
        ("faylYaz", f("faylYaz", 2, Some(2), |i, a, _| {
            let m = yaz(i, &a[1])?;
            std::fs::write(py_s(&a[0]), m).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
            Ok(D::Boş)
        })),
    ])
}
