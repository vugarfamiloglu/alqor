//! `xml` — XML oxuma, axtarış və yazma (modullar/xml_.py, _duyun.py).
//!
//! Oxuyucu Python `xml.etree` (expat) ilə eyni ağacı və eyni xəta
//! mesajlarını (sətir/sütun daxil) verir. `<!ENTITY>` rədd edilir.

use super::deyerler::*;
use super::elave::*;
use indexmap::IndexMap;
use std::cell::RefCell;
use std::rc::{Rc, Weak};

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("XMLXətası", m, "ALQ-R005")
}

// ═══════════════════════════════════════════════════════════════════════
//  Düyün
// ═══════════════════════════════════════════════════════════════════════

#[derive(Clone)]
pub enum Uşaq {
    Mətn(String),
    D(Rc<Düyün>),
}

pub struct Düyün {
    pub ad: String,
    pub atr: RefCell<IndexMap<String, String>>,
    pub uşaq: RefCell<Vec<Uşaq>>,
    pub valideyn: RefCell<Weak<Düyün>>,
    obyekt: RefCell<Weak<Obyekt>>,
}

impl Düyün {
    pub fn yeni(ad: &str, atr: IndexMap<String, String>) -> Rc<Düyün> {
        Rc::new(Düyün {
            ad: ad.into(),
            atr: RefCell::new(atr),
            uşaq: RefCell::new(vec![]),
            valideyn: RefCell::new(Weak::new()),
            obyekt: RefCell::new(Weak::new()),
        })
    }
    pub fn əlavə(self: &Rc<Self>, u: Uşaq) {
        if let Uşaq::D(d) = &u {
            *d.valideyn.borrow_mut() = Rc::downgrade(self);
        }
        self.uşaq.borrow_mut().push(u);
    }
    fn elementlər(&self) -> Vec<Rc<Düyün>> {
        self.uşaq.borrow().iter().filter_map(|u| if let Uşaq::D(d) = u { Some(d.clone()) } else { None }).collect()
    }
    fn mətn(&self) -> String {
        let mut n = String::new();
        fn gəz(d: &Düyün, n: &mut String) {
            for u in d.uşaq.borrow().iter() {
                match u {
                    Uşaq::Mətn(s) => n.push_str(s),
                    Uşaq::D(x) if x.ad != "script" && x.ad != "style" => gəz(x, n),
                    _ => {}
                }
            }
        }
        gəz(self, &mut n);
        n
    }
    fn nəsillər(&self, v: &mut Vec<Rc<Düyün>>) {
        for u in self.elementlər() {
            v.push(u.clone());
            u.nəsillər(v);
        }
    }
    pub fn xml(&self, gözəl: bool, ind: usize) -> String {
        let atr: String = self.atr.borrow().iter().map(|(a, v)| format!(" {}=\"{}\"", a, atr_qaç(v))).collect();
        let uşaq = self.uşaq.borrow();
        if uşaq.is_empty() {
            return format!("<{}{}/>", self.ad, atr);
        }
        let yalnız_element = uşaq.iter().all(|u| matches!(u, Uşaq::D(_)));
        if gözəl && yalnız_element {
            let ön = "  ".repeat(ind + 1);
            let iç: String = uşaq
                .iter()
                .map(|u| match u {
                    Uşaq::D(d) => format!("\n{}{}", ön, d.xml(true, ind + 1)),
                    _ => unreachable!(),
                })
                .collect();
            return format!("<{}{}>{}\n{}</{}>", self.ad, atr, iç, "  ".repeat(ind), self.ad);
        }
        let iç: String = uşaq
            .iter()
            .map(|u| match u {
                Uşaq::Mətn(s) => mətn_qaç(s),
                Uşaq::D(d) => d.xml(gözəl, ind + 1),
            })
            .collect();
        format!("<{}{}>{}</{}>", self.ad, atr, iç, self.ad)
    }
    fn html(&self) -> String {
        let atr: String = self
            .atr
            .borrow()
            .iter()
            .map(|(a, v)| if v.is_empty() { format!(" {}", a) } else { format!(" {}=\"{}\"", a, atr_qaç(v)) })
            .collect();
        let xam = self.ad == "script" || self.ad == "style";
        let iç: String = self
            .uşaq
            .borrow()
            .iter()
            .map(|u| match u {
                Uşaq::Mətn(s) => if xam { s.clone() } else { mətn_qaç(s) },
                Uşaq::D(d) => d.html(),
            })
            .collect();
        format!("<{}{}>{}</{}>", self.ad, atr, iç, self.ad)
    }
    fn lüğət(&self) -> D {
        let mut n: IndexMap<String, D> = IndexMap::new();
        for (a, v) in self.atr.borrow().iter() {
            n.insert(format!("@{}", a), D::str(v.clone()));
        }
        for u in self.elementlər() {
            let d = u.lüğət();
            match n.get_mut(&u.ad) {
                Some(D::Siyahı(l)) => l.borrow_mut().push(d),
                Some(x) => {
                    let köhnə = x.clone();
                    *x = D::siyahı(vec![köhnə, d]);
                }
                None => {
                    n.insert(u.ad.clone(), d);
                }
            }
        }
        let mətn: String = self.uşaq.borrow().iter().filter_map(|u| if let Uşaq::Mətn(s) = u { Some(s.as_str()) } else { None }).collect();
        let mətn = mətn.trim().to_string();
        if n.is_empty() {
            return D::str(mətn);
        }
        if !mətn.is_empty() {
            n.insert("#mətn".into(), D::str(mətn));
        }
        lüğət_s(n.into_iter().collect())
    }
}

fn atr_qaç(v: &str) -> String {
    v.replace('&', "&amp;").replace('"', "&quot;").replace('<', "&lt;").replace('>', "&gt;")
}

fn mətn_qaç(v: &str) -> String {
    v.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}

// ── CSS seçicisi ───────────────────────────────────────────────────────

#[derive(Default, Debug)]
struct Şərt {
    teq: Option<String>,
    id: Option<String>,
    siniflər: Vec<String>,
    atr: Vec<(String, Option<String>, Option<String>)>,
}

fn söz(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn seçici_xətası(s: &str) -> Siqnal {
    xəta("DəyərXətası", format!("seçici başa düşülmədi: {}", str_repr(s)), "ALQ-T001")
}

/// `[\w-]+` və s. — (son mövqe)
fn oxu_söz(c: &[char], mut i: usize, əlavə: &str) -> usize {
    while i < c.len() && (söz(c[i]) || əlavə.contains(c[i])) {
        i += 1;
    }
    i
}

fn seçicini_ayır(seçici: &D) -> Nəticə<Vec<Vec<(char, Şərt)>>> {
    let s = match seçici {
        D::S(s) if !s.trim().is_empty() => s.to_string(),
        _ => return Err(xəta("DəyərXətası", "seçici boş ola bilməz", "ALQ-T001")),
    };
    let mut qruplar = vec![];
    for qrup in s.split(',') {
        let mut addımlar = vec![];
        let c: Vec<char> = qrup.trim().chars().collect();
        let mut i = 0;
        let mut əlaqə = ' ';
        while i < c.len() {
            if c[i] == '>' {
                əlaqə = '>';
                i += 1;
                while i < c.len() && c[i].is_whitespace() {
                    i += 1;
                }
                continue;
            }
            let başla = i;
            let mut ş = Şərt::default();
            let j = oxu_söz(&c, i, ":*-");
            if j > i {
                ş.teq = Some(c[i..j].iter().collect());
                i = j;
            }
            loop {
                if i >= c.len() {
                    break;
                }
                match c[i] {
                    '#' | '.' => {
                        let j = oxu_söz(&c, i + 1, "-");
                        if j == i + 1 {
                            break;
                        }
                        let ad_: String = c[i + 1..j].iter().collect();
                        if c[i] == '#' {
                            ş.id = Some(ad_);
                        } else {
                            ş.siniflər.push(ad_);
                        }
                        i = j;
                    }
                    '[' => {
                        let mut k = i + 1;
                        while k < c.len() && c[k].is_whitespace() {
                            k += 1;
                        }
                        let j = oxu_söz(&c, k, ":-");
                        if j == k {
                            break;
                        }
                        let ad_: String = c[k..j].iter().collect();
                        let mut k = j;
                        while k < c.len() && c[k].is_whitespace() {
                            k += 1;
                        }
                        let mut op = None;
                        let mut dəyər = None;
                        if k < c.len() && c[k] != ']' {
                            let o = if "~^$*|".contains(c[k]) && c.get(k + 1) == Some(&'=') {
                                k += 2;
                                format!("{}=", c[k - 2])
                            } else if c[k] == '=' {
                                k += 1;
                                "=".into()
                            } else {
                                break;
                            };
                            while k < c.len() && c[k].is_whitespace() {
                                k += 1;
                            }
                            let d: String = if k < c.len() && (c[k] == '"' || c[k] == '\'') {
                                let q = c[k];
                                let Some(e) = c[k + 1..].iter().position(|x| *x == q) else { break };
                                let d = c[k + 1..k + 1 + e].iter().collect();
                                k = k + 2 + e;
                                d
                            } else {
                                let b = k;
                                while k < c.len() && c[k] != ']' && !c[k].is_whitespace() {
                                    k += 1;
                                }
                                if k == b {
                                    break;
                                }
                                c[b..k].iter().collect()
                            };
                            while k < c.len() && c[k].is_whitespace() {
                                k += 1;
                            }
                            op = Some(o);
                            dəyər = Some(d);
                        }
                        if k >= c.len() || c[k] != ']' {
                            break;
                        }
                        ş.atr.push((ad_, op, dəyər));
                        i = k + 1;
                    }
                    _ => break,
                }
            }
            if i == başla {
                return Err(seçici_xətası(&s));
            }
            addımlar.push((əlaqə, ş));
            əlaqə = ' ';
            while i < c.len() && c[i].is_whitespace() {
                i += 1;
            }
        }
        qruplar.push(addımlar);
    }
    Ok(qruplar)
}

fn tək_uyğun(d: &Düyün, ş: &Şərt) -> bool {
    if let Some(t) = &ş.teq {
        if t != "*" && d.ad.to_lowercase() != t.to_lowercase() {
            return false;
        }
    }
    let atr = d.atr.borrow();
    if let Some(id) = &ş.id {
        if atr.get("id") != Some(id) {
            return false;
        }
    }
    if !ş.siniflər.is_empty() {
        let s: Vec<&str> = atr.get("class").map(|x| x.split_whitespace().collect()).unwrap_or_default();
        if !ş.siniflər.iter().all(|x| s.contains(&x.as_str())) {
            return false;
        }
    }
    for (ad_, op, dəyər) in &ş.atr {
        let Some(v) = atr.get(ad_) else { return false };
        let d = dəyər.clone().unwrap_or_default();
        let ok = match op.as_deref() {
            None => true,
            Some("=") => *v == d,
            Some("~=") => v.split_whitespace().any(|x| x == d),
            Some("^=") => v.starts_with(&d),
            Some("$=") => v.ends_with(&d),
            Some("*=") => v.contains(&d),
            Some("|=") => *v == d || v.starts_with(&format!("{}-", d)),
            _ => true,
        };
        if !ok {
            return false;
        }
    }
    true
}

fn uyğundur(d: &Rc<Düyün>, addımlar: &[(char, Şərt)]) -> bool {
    fn yoxla(d: Option<Rc<Düyün>>, i: usize, a: &[(char, Şərt)]) -> bool {
        let Some(d) = d else { return false };
        let (əlaqə, ş) = &a[i];
        if !tək_uyğun(&d, ş) {
            return false;
        }
        if i == 0 {
            return true;
        }
        if *əlaqə == '>' {
            return yoxla(d.valideyn.borrow().upgrade(), i - 1, a);
        }
        let mut v = d.valideyn.borrow().upgrade();
        while let Some(x) = v {
            if yoxla(Some(x.clone()), i - 1, a) {
                return true;
            }
            v = x.valideyn.borrow().upgrade();
        }
        false
    }
    !addımlar.is_empty() && yoxla(Some(d.clone()), addımlar.len() - 1, addımlar)
}

pub fn düyün_d(d: &Rc<Düyün>) -> D {
    if let Some(o) = d.obyekt.borrow().upgrade() {
        return D::Obyekt(o);
    }
    let o = obyekt("düyün", d.clone(), |d| format!("<{}>", d.ad), |w, v| {
        vec![
            ("ad", metod(v, "ad", 0, Some(0), |_, d, _, _| Ok(D::str(d.ad.clone())))),
            ("atribut", metod(v, "atribut", 1, Some(2), |_, d, a, _| {
                Ok(d.atr.borrow().get(&py_s(&a[0])).map(|x| D::str(x.clone())).unwrap_or_else(|| a.get(1).cloned().unwrap_or(D::Boş)))
            })),
            ("atributlar", metod(v, "atributlar", 0, Some(0), |_, d, _, _| {
                Ok(lüğət_s(d.atr.borrow().iter().map(|(a, b)| (a.clone(), D::str(b.clone()))).collect()))
            })),
            ("atributQoy", metod_ö(w, v, "atributQoy", 2, Some(2), |_, d, ö, a, _| {
                d.atr.borrow_mut().insert(py_s(&a[0]), py_s(&a[1]));
                Ok(ö)
            })),
            ("mətn", metod(v, "mətn", 0, Some(0), |_, d, _, _| Ok(D::str(d.mətn())))),
            ("uşaqlar", metod(v, "uşaqlar", 0, Some(0), |_, d, _, _| Ok(D::siyahı(d.elementlər().iter().map(düyün_d).collect())))),
            ("valideyn", metod(v, "valideyn", 0, Some(0), |_, d, _, _| {
                Ok(d.valideyn.borrow().upgrade().map(|x| düyün_d(&x)).unwrap_or(D::Boş))
            })),
            ("tap", metod(v, "tap", 1, Some(1), |_, d, a, _| {
                let q = seçicini_ayır(&a[0])?;
                let mut n = vec![];
                d.nəsillər(&mut n);
                Ok(n.iter().find(|x| q.iter().any(|g| uyğundur(x, g))).map(düyün_d).unwrap_or(D::Boş))
            })),
            ("tapHamısı", metod(v, "tapHamısı", 1, Some(1), |_, d, a, _| {
                let q = seçicini_ayır(&a[0])?;
                let mut n = vec![];
                d.nəsillər(&mut n);
                Ok(D::siyahı(n.iter().filter(|x| q.iter().any(|g| uyğundur(x, g))).map(düyün_d).collect()))
            })),
            ("əlavəEt", metod_ö(w, v, "əlavəEt", 1, Some(1), |_, d, ö, a, _| {
                match veri::<Düyün>(&a[0]) {
                    Some(u) => d.əlavə(Uşaq::D(u)),
                    None => d.əlavə(Uşaq::Mətn(py_s(&a[0]))),
                }
                Ok(ö)
            })),
            ("xml", metod(v, "xml", 0, Some(1), |_, d, a, adlı| {
                let n = imza("xml", a, adlı, &["gözəl"])?;
                Ok(D::str(d.xml(var(&n, 0).map(|x| doğrudur(&x)).unwrap_or(false), 0)))
            })),
            ("html", metod(v, "html", 0, Some(0), |_, d, _, _| Ok(D::str(d.html())))),
            ("lüğət", metod(v, "lüğət", 0, Some(0), |_, d, _, _| Ok(d.lüğət()))),
        ]
    });
    if let D::Obyekt(ob) = &o {
        *d.obyekt.borrow_mut() = Rc::downgrade(ob);
    }
    o
}

// ═══════════════════════════════════════════════════════════════════════
//  XML oxuyucu (expat davranışı)
// ═══════════════════════════════════════════════════════════════════════

struct Oxu<'a> {
    c: &'a [char],
    i: usize,
}

struct Xə(usize, &'static str);

fn ad_başı(c: char) -> bool {
    c.is_alphabetic() || c == '_' || c == ':'
}

fn ad_simvolu(c: char) -> bool {
    c.is_alphanumeric() || "_:.-\u{b7}".contains(c)
}

fn qadağan(c: char) -> bool {
    let k = c as u32;
    (k < 0x20 && !matches!(c, '\t' | '\n' | '\r')) || (0xFFFE..=0xFFFF).contains(&k)
}

impl<'a> Oxu<'a> {
    fn başlayır(&self, s: &str) -> bool {
        let mut k = self.i;
        for ch in s.chars() {
            if self.c.get(k) != Some(&ch) {
                return false;
            }
            k += 1;
        }
        true
    }
    fn boşluq(&mut self) {
        while self.i < self.c.len() && matches!(self.c[self.i], ' ' | '\t' | '\n' | '\r') {
            self.i += 1;
        }
    }
    fn ad(&mut self) -> Result<String, Xə> {
        let b = self.i;
        if self.i >= self.c.len() {
            return Err(Xə(b, "unclosed token"));
        }
        if !ad_başı(self.c[self.i]) {
            return Err(Xə(self.i, "not well-formed (invalid token)"));
        }
        while self.i < self.c.len() && ad_simvolu(self.c[self.i]) {
            self.i += 1;
        }
        Ok(self.c[b..self.i].iter().collect())
    }
    /// `&…;` — mövqe `&`-dadır
    fn varlıq(&mut self) -> Result<String, Xə> {
        let b = self.i;
        self.i += 1;
        if self.i < self.c.len() && self.c[self.i] == '#' {
            self.i += 1;
            let hex = self.i < self.c.len() && self.c[self.i] == 'x';
            if hex {
                self.i += 1;
            }
            let r = self.i;
            while self.i < self.c.len() && (if hex { self.c[self.i].is_ascii_hexdigit() } else { self.c[self.i].is_ascii_digit() }) {
                self.i += 1;
            }
            if self.i >= self.c.len() {
                return Err(Xə(b, "unclosed token"));
            }
            if self.i == r || self.c[self.i] != ';' {
                return Err(Xə(self.i, "not well-formed (invalid token)"));
            }
            let s: String = self.c[r..self.i].iter().collect();
            self.i += 1;
            let v = u32::from_str_radix(&s, if hex { 16 } else { 10 }).ok();
            return match v.and_then(char::from_u32).filter(|c| !qadağan(*c) && *c != '\0') {
                Some(c) => Ok(c.to_string()),
                None => Err(Xə(b, "reference to invalid character number")),
            };
        }
        let ad_ = match self.ad() {
            Ok(a) => a,
            Err(Xə(_, m)) if m == "unclosed token" => return Err(Xə(b, m)),
            Err(_) => return Err(Xə(b, "not well-formed (invalid token)")),
        };
        if self.i >= self.c.len() {
            return Err(Xə(b, "unclosed token"));
        }
        if self.c[self.i] != ';' {
            return Err(Xə(b, "not well-formed (invalid token)"));
        }
        self.i += 1;
        Ok(match ad_.as_str() {
            "lt" => "<",
            "gt" => ">",
            "amp" => "&",
            "quot" => "\"",
            "apos" => "'",
            _ => return Err(Xə(b, "undefined entity")),
        }
        .into())
    }
    /// Şərh, PI, DOCTYPE — atlanır. `Ok(true)` — nəsə atlandı.
    fn atla(&mut self) -> Result<bool, Xə> {
        let b = self.i;
        if self.başlayır("<!--") {
            self.i += 4;
            loop {
                if self.i + 2 >= self.c.len() + 0 && !self.başlayır("-->") {
                    if self.i >= self.c.len() {
                        return Err(Xə(b, "unclosed token"));
                    }
                }
                if self.başlayır("-->") {
                    self.i += 3;
                    return Ok(true);
                }
                if self.başlayır("--") {
                    return Err(Xə(self.i, "not well-formed (invalid token)"));
                }
                if self.i >= self.c.len() {
                    return Err(Xə(b, "unclosed token"));
                }
                self.i += 1;
            }
        }
        if self.başlayır("<?") {
            self.i += 2;
            loop {
                if self.i >= self.c.len() {
                    return Err(Xə(b, "unclosed token"));
                }
                if self.başlayır("?>") {
                    self.i += 2;
                    return Ok(true);
                }
                self.i += 1;
            }
        }
        if self.başlayır("<!DOCTYPE") {
            let mut dər = 0;
            loop {
                if self.i >= self.c.len() {
                    return Err(Xə(b, "unclosed token"));
                }
                match self.c[self.i] {
                    '[' => dər += 1,
                    ']' => dər -= 1,
                    '>' if dər == 0 => {
                        self.i += 1;
                        return Ok(true);
                    }
                    _ => {}
                }
                self.i += 1;
            }
        }
        Ok(false)
    }

    fn sənəd(&mut self) -> Result<Rc<Düyün>, Xə> {
        // Prolog
        loop {
            self.boşluq();
            if self.i >= self.c.len() {
                return Err(Xə(self.c.len(), "no element found"));
            }
            if self.c[self.i] != '<' {
                return Err(Xə(self.i, "syntax error"));
            }
            if !self.atla()? {
                break;
            }
        }
        let mut yığın: Vec<(Rc<Düyün>, String, Vec<(String, String)>)> = vec![];
        let mut mətn = String::new();
        let mut kök: Option<Rc<Düyün>> = None;
        let mut fəzalar: Vec<Vec<(String, String)>> = vec![];
        loop {
            if yığın.is_empty() && kök.is_some() {
                // Epiloq
                loop {
                    self.boşluq();
                    if self.i >= self.c.len() {
                        return Ok(kök.unwrap());
                    }
                    if self.c[self.i] == '<' && self.atla()? {
                        continue;
                    }
                    return Err(Xə(self.i, "junk after document element"));
                }
            }
            if self.i >= self.c.len() {
                return Err(Xə(self.c.len(), "no element found"));
            }
            let ch = self.c[self.i];
            if ch == '<' {
                if self.başlayır("<![CDATA[") {
                    let b = self.i;
                    self.i += 9;
                    loop {
                        if self.i >= self.c.len() {
                            return Err(Xə(b, "unclosed token"));
                        }
                        if self.başlayır("]]>") {
                            self.i += 3;
                            break;
                        }
                        mətn.push(self.c[self.i]);
                        self.i += 1;
                    }
                    continue;
                }
                if self.atla()? {
                    continue;
                }
                let b = self.i;
                if self.başlayır("</") {
                    self.i += 2;
                    let ad_b = self.i;
                    let ad_ = self.ad().map_err(|Xə(p, m)| if m == "unclosed token" { Xə(b, m) } else { Xə(p, m) })?;
                    self.boşluq();
                    if self.i >= self.c.len() {
                        return Err(Xə(b, "unclosed token"));
                    }
                    if self.c[self.i] != '>' {
                        return Err(Xə(self.i, "not well-formed (invalid token)"));
                    }
                    let (d, açıq, _) = yığın.last().unwrap().clone();
                    if açıq != ad_ {
                        return Err(Xə(ad_b, "mismatched tag"));
                    }
                    self.i += 1;
                    if !mətn.is_empty() {
                        d.əlavə(Uşaq::Mətn(std::mem::take(&mut mətn)));
                    }
                    yığın.pop();
                    fəzalar.pop();
                    continue;
                }
                // Başlanğıc teqi
                self.i += 1;
                let ad_ = self.ad().map_err(|Xə(p, m)| if m == "unclosed token" { Xə(b, m) } else { Xə(p, m) })?;
                let mut atr: Vec<(String, String)> = vec![];
                let boş;
                loop {
                    let əvvəl = self.i;
                    self.boşluq();
                    if self.i >= self.c.len() {
                        return Err(Xə(b, "unclosed token"));
                    }
                    if self.c[self.i] == '>' {
                        self.i += 1;
                        boş = false;
                        break;
                    }
                    if self.c[self.i] == '/' {
                        if self.c.get(self.i + 1) == Some(&'>') {
                            self.i += 2;
                            boş = true;
                            break;
                        }
                        if self.i + 1 >= self.c.len() {
                            return Err(Xə(b, "unclosed token"));
                        }
                        return Err(Xə(self.i, "not well-formed (invalid token)"));
                    }
                    if self.i == əvvəl {
                        return Err(Xə(self.i, "not well-formed (invalid token)"));
                    }
                    let a_b = self.i;
                    let a = self.ad().map_err(|Xə(p, m)| if m == "unclosed token" { Xə(b, m) } else { Xə(p, m) })?;
                    self.boşluq();
                    if self.i >= self.c.len() {
                        return Err(Xə(b, "unclosed token"));
                    }
                    if self.c[self.i] != '=' {
                        return Err(Xə(self.i, "not well-formed (invalid token)"));
                    }
                    self.i += 1;
                    self.boşluq();
                    if self.i >= self.c.len() {
                        return Err(Xə(b, "unclosed token"));
                    }
                    let q = self.c[self.i];
                    if q != '"' && q != '\'' {
                        return Err(Xə(self.i, "not well-formed (invalid token)"));
                    }
                    self.i += 1;
                    let mut v = String::new();
                    loop {
                        if self.i >= self.c.len() {
                            return Err(Xə(b, "unclosed token"));
                        }
                        let x = self.c[self.i];
                        if x == q {
                            self.i += 1;
                            break;
                        }
                        if x == '<' || qadağan(x) {
                            return Err(Xə(self.i, "not well-formed (invalid token)"));
                        }
                        if x == '&' {
                            v.push_str(&self.varlıq()?);
                            continue;
                        }
                        v.push(if matches!(x, '\n' | '\r' | '\t') { ' ' } else { x });
                        self.i += 1;
                    }
                    if atr.iter().any(|(k, _)| *k == a) {
                        return Err(Xə(a_b, "duplicate attribute"));
                    }
                    atr.push((a, v));
                }
                // Ad fəzaları
                let mut fəza = vec![];
                let mut adi_atr = IndexMap::new();
                for (a, v) in &atr {
                    if a == "xmlns" {
                        fəza.push((String::new(), v.clone()));
                    } else if let Some(p) = a.strip_prefix("xmlns:") {
                        fəza.push((p.to_string(), v.clone()));
                    }
                }
                fəzalar.push(fəza);
                let bağlı = |p: &str| p == "xml" || fəzalar.iter().rev().any(|f| f.iter().any(|(k, _)| k == p));
                let yerli = |a: &str| -> Result<String, ()> {
                    match a.split_once(':') {
                        Some((p, l)) => {
                            if bağlı(p) {
                                Ok(l.to_string())
                            } else {
                                Err(())
                            }
                        }
                        None => Ok(a.to_string()),
                    }
                };
                let teq = yerli(&ad_).map_err(|_| Xə(b, "unbound prefix"))?;
                for (a, v) in &atr {
                    if a == "xmlns" || a.starts_with("xmlns:") {
                        continue;
                    }
                    let l = yerli(a).map_err(|_| Xə(b, "unbound prefix"))?;
                    adi_atr.insert(l, v.clone());
                }
                let d = Düyün::yeni(&teq, adi_atr);
                if let Some((v, _, _)) = yığın.last() {
                    if !mətn.is_empty() {
                        v.əlavə(Uşaq::Mətn(std::mem::take(&mut mətn)));
                    }
                    v.əlavə(Uşaq::D(d.clone()));
                } else {
                    kök = Some(d.clone());
                }
                if boş {
                    fəzalar.pop();
                } else {
                    yığın.push((d, ad_, atr));
                }
                continue;
            }
            if ch == '&' {
                mətn.push_str(&self.varlıq()?);
                continue;
            }
            if self.başlayır("]]>") {
                return Err(Xə(self.i + 2, "not well-formed (invalid token)"));
            }
            if qadağan(ch) {
                return Err(Xə(self.i, "not well-formed (invalid token)"));
            }
            mətn.push(ch);
            self.i += 1;
        }
    }
}

pub fn oxu(m: &D) -> Nəticə {
    let D::S(s) = m else {
        return Err(xəta("TipXətası", format!("`xml.oxu` mətn gözləyir, `{}` gəlib", tip_adı(m)), "ALQ-T001"));
    };
    if s.to_lowercase().contains("<!entity") {
        return Err(x_("`<!ENTITY>` elanlarına icazə verilmir (təhlükəsizlik)"));
    }
    let t = s.trim_start_matches('\u{feff}').replace("\r\n", "\n").replace('\r', "\n");
    let c: Vec<char> = t.chars().collect();
    let mut o = Oxu { c: &c, i: 0 };
    match o.sənəd() {
        Ok(d) => Ok(düyün_d(&d)),
        Err(Xə(p, m)) => {
            let p = p.min(c.len());
            let sətir = c[..p].iter().filter(|x| **x == '\n').count() + 1;
            let sütun = match c[..p].iter().rposition(|x| *x == '\n') {
                Some(k) => p - k - 1,
                None => p,
            };
            Err(x_(format!("XML pozulub (sətir {}, sütun {}): {}", sətir, sütun + 1, m)))
        }
    }
}

// ── Yaratma ────────────────────────────────────────────────────────────

fn sadə(v: &D) -> String {
    match v {
        D::M(true) => "doğru".into(),
        D::M(false) => "yanlış".into(),
        D::Boş => String::new(),
        x => py_s(x),
    }
}

fn ad_doğrudur(a: &str) -> bool {
    let mut c = a.chars();
    match c.next() {
        Some(x) if x.is_alphabetic() || x == '_' => c.all(|y| y.is_alphanumeric() || "_.:-".contains(y)),
        _ => false,
    }
}

pub fn element(ad_: &D, atr: &D, uşaqlar: &D) -> Nəticə<Rc<Düyün>> {
    let a = match ad_ {
        D::S(s) if ad_doğrudur(s) => s.to_string(),
        x => return Err(xəta("DəyərXətası", format!("`{}` XML element adı deyil", py_s(x)), "ALQ-T001")),
    };
    let mut m = IndexMap::new();
    if let Some(c) = cütlər(atr) {
        for (k, v) in c {
            m.insert(py_s(&k), sadə(&v));
        }
    }
    let d = Düyün::yeni(&a, m);
    if uşaqlar.boşdur() {
        return Ok(d);
    }
    let el = match uşaqlar {
        D::Siyahı(l) => l.borrow().clone(),
        x => vec![x.clone()],
    };
    for u in el {
        match veri::<Düyün>(&u) {
            Some(x) => d.əlavə(Uşaq::D(x)),
            None => d.əlavə(Uşaq::Mətn(sadə(&u))),
        }
    }
    Ok(d)
}

fn lüğətdən(l: &D, kök: &str) -> Nəticə<Rc<Düyün>> {
    fn qur(ad_: &str, d: &D) -> Nəticə<Vec<Rc<Düyün>>> {
        let d = match d {
            D::Nümunə(_) => D::lüğət(cütlər(d).unwrap().into_iter().map(|(a, v)| (Açar(a), v)).collect()),
            x => x.clone(),
        };
        if let D::Siyahı(s) = &d {
            let mut n = vec![];
            for v in s.borrow().iter() {
                n.extend(qur(ad_, v)?);
            }
            return Ok(n);
        }
        let e = element(&D::s(ad_), &D::Boş, &D::Boş)?;
        if let D::Lüğət(_) = &d {
            for (a, v) in cütlər(&d).unwrap() {
                let a = py_s(&a);
                if let Some(x) = a.strip_prefix('@') {
                    e.atr.borrow_mut().insert(x.to_string(), sadə(&v));
                } else if a == "#mətn" {
                    e.əlavə(Uşaq::Mətn(sadə(&v)));
                } else {
                    for u in qur(&a, &v)? {
                        e.əlavə(Uşaq::D(u));
                    }
                }
            }
        } else if !d.boşdur() {
            e.əlavə(Uşaq::Mətn(sadə(&d)));
        }
        Ok(vec![e])
    }
    let mut n = qur(kök, l)?;
    if n.is_empty() {
        return Err(xəta("İndeksXətası", "list index out of range", "ALQ-R002"));
    }
    Ok(n.remove(0))
}

fn yaz(d: &D, gözəl: bool) -> Nəticə<String> {
    let x = match veri::<Düyün>(d) {
        Some(x) => x,
        None => lüğətdən(d, "kök")?,
    };
    Ok(format!("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{}\n", x.xml(gözəl, 0)))
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
    Modul::yeni("xml", vec![
        ("oxu", f("oxu", 1, Some(1), |_, a, _| oxu(&a[0]))),
        ("faylOxu", f("faylOxu", 1, Some(1), |_, a, _| oxu(&D::str(fayl_oxu(&py_s(&a[0]))?)))),
        ("yaz", f("yaz", 1, Some(2), |_, a, adlı| {
            let n = imza("yaz", a, adlı, &["d", "gözəl"])?;
            Ok(D::str(yaz(&al(&n, 0), var(&n, 1).map(|x| doğrudur(&x)).unwrap_or(true))?))
        })),
        ("faylYaz", f("faylYaz", 2, Some(2), |_, a, _| {
            let m = yaz(&a[1], true)?;
            std::fs::write(py_s(&a[0]), m).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
            Ok(D::Boş)
        })),
        ("element", f("element", 1, Some(3), |_, a, adlı| {
            let n = imza("element", a, adlı, &["ad", "atributlar", "uşaqlar"])?;
            Ok(düyün_d(&element(&al(&n, 0), &al(&n, 1), &al(&n, 2))?))
        })),
        ("lüğətə", f("lüğətə", 1, Some(1), |_, a, _| match veri::<Düyün>(&a[0]) {
            Some(d) => Ok(d.lüğət()),
            None => {
                let d = oxu(&a[0])?;
                Ok(veri::<Düyün>(&d).unwrap().lüğət())
            }
        })),
        ("lüğətdən", f("lüğətdən", 1, Some(2), |_, a, adlı| {
            let n = imza("lüğətdən", a, adlı, &["l", "kök"])?;
            let k = var(&n, 1).map(|x| py_s(&x)).unwrap_or("kök".into());
            Ok(düyün_d(&lüğətdən(&al(&n, 0), &k)?))
        })),
    ])
}
