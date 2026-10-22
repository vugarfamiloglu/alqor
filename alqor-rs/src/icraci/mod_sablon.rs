//! Şablon mühərriki (`.alqorhtml`, sablon.py). `{{ }}` və `{% %}`
//! daxilindəki ifadələr həqiqi Alqor ifadələridir — Rust lekseri və
//! parseri ilə ayrılır, icraçı ilə qiymətləndirilir.

use super::deyerler::*;
use super::elave::py_s;
use super::icraci::İcraçı;
use super::muhit::Mühit;
use crate::aac::E;
use std::cell::RefCell;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::rc::Rc;

pub struct ŞablonXətası {
    pub mesaj: String,
    pub fayl: String,
    pub sətir: usize,
}

impl std::fmt::Display for ŞablonXətası {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if self.fayl.is_empty() {
            write!(f, "{}", self.mesaj)
        } else {
            write!(f, "{} ({}:{})", self.mesaj, self.fayl, self.sətir)
        }
    }
}

fn sx(m: impl Into<String>, fayl: &str, sətir: usize) -> ŞablonXətası {
    ŞablonXətası { mesaj: m.into(), fayl: fayl.into(), sətir }
}

type Ş<T> = Result<T, Şx>;

/// Şablon xətası və ya icraçı siqnalı (məs. `dayan`)
pub enum Şx {
    Ş(ŞablonXətası),
    S(Siqnal),
}

impl From<ŞablonXətası> for Şx {
    fn from(x: ŞablonXətası) -> Şx {
        Şx::Ş(x)
    }
}

#[derive(Clone)]
enum Q {
    Mətn(String),
    Dəyər { ifadə: String, filtrlər: Vec<(String, Vec<String>)>, xam: bool, sətir: usize, fayl: String },
    Blok(Rc<RefCell<Blok>>),
    Daxil { yol: String },
}

struct Blok {
    növ: String,
    arqument: String,
    gövdə: Vec<Q>,
    yoxsa: Option<Vec<Q>>,
    sətir: usize,
    fayl: String,
}

pub struct Şablon {
    qovşaqlar: Vec<Q>,
    genişlət: Option<String>,
    bloklar: HashMap<String, Vec<Q>>,
    ad: String,
    qovluq: Option<PathBuf>,
}

// ── Ayırıcı ────────────────────────────────────────────────────────────

enum Parça {
    Dəyər(String),
    Əmr(String),
    Şərh,
}

/// `\{\{(.*?)\}\}|\{%(.*?)%\}|\{#(.*?)#\}` (DOTALL) — (başlanğıc, son, parça)
fn parçalar(m: &str) -> Vec<(usize, usize, Parça)> {
    let mut n = vec![];
    let b = m.as_bytes();
    let mut k = 0;
    while k + 1 < b.len() {
        if b[k] == b'{' {
            let (son_işarə, növ) = match b[k + 1] {
                b'{' => ("}}", 0),
                b'%' => ("%}", 1),
                b'#' => ("#}", 2),
                _ => {
                    k += 1;
                    continue;
                }
            };
            if let Some(j) = m[k + 2..].find(son_işarə) {
                let iç = m[k + 2..k + 2 + j].to_string();
                let son = k + 2 + j + 2;
                n.push((
                    k,
                    son,
                    match növ {
                        0 => Parça::Dəyər(iç),
                        1 => Parça::Əmr(iç),
                        _ => Parça::Şərh,
                    },
                ));
                k = son;
                continue;
            }
        }
        k += 1;
    }
    n
}

fn sitatı_çıxar(m: &str) -> String {
    let m = m.trim();
    let c: Vec<char> = m.chars().collect();
    if c.len() >= 2 && c[0] == c[c.len() - 1] && (c[0] == '"' || c[0] == '\'') {
        return c[1..c.len() - 1].iter().collect();
    }
    m.to_string()
}

fn boru_ilə_böl(m: &str) -> Vec<String> {
    let c: Vec<char> = m.chars().collect();
    let mut h = vec![];
    let mut cari = String::new();
    let mut dər = 0i32;
    let mut sitat: Option<char> = None;
    let mut i = 0;
    while i < c.len() {
        let x = c[i];
        if let Some(q) = sitat {
            cari.push(x);
            if x == '\\' && i + 1 < c.len() {
                cari.push(c[i + 1]);
                i += 2;
                continue;
            }
            if x == q {
                sitat = None;
            }
            i += 1;
            continue;
        }
        if x == '"' || x == '\'' {
            sitat = Some(x);
            cari.push(x);
        } else if "([{".contains(x) {
            dər += 1;
            cari.push(x);
        } else if ")]}".contains(x) {
            dər -= 1;
            cari.push(x);
        } else if x == '|' && dər == 0 && c.get(i + 1) != Some(&'|') {
            h.push(std::mem::take(&mut cari));
        } else {
            cari.push(x);
        }
        i += 1;
    }
    h.push(cari);
    h
}

fn filtri_ayır(f: &str) -> (String, Vec<String>) {
    let Some((ad_, qalan)) = f.split_once('(') else { return (f.to_string(), vec![]) };
    let arq = match qalan.rsplit_once(')') {
        Some((a, _)) => a,
        None => qalan,
    };
    if arq.trim().is_empty() {
        return (ad_.trim().to_string(), vec![]);
    }
    (ad_.trim().to_string(), arq.split(',').map(|a| sitatı_çıxar(a.trim())).collect())
}

fn dəyəri_ayır(xam: &str, sətir: usize, fayl: &str) -> Q {
    let h = boru_ilə_böl(xam);
    let ifadə = h[0].trim().to_string();
    let mut filtrlər = vec![];
    let mut xam_ = false;
    for f in &h[1..] {
        let f = f.trim();
        if f.is_empty() {
            continue;
        }
        if f == "xam" {
            xam_ = true;
            continue;
        }
        filtrlər.push(filtri_ayır(f));
    }
    Q::Dəyər { ifadə, filtrlər, xam: xam_, sətir, fayl: fayl.into() }
}

pub fn ayır(m: &str, fayl: &str) -> Result<(Vec<Q>, Option<String>, HashMap<String, Vec<Q>>), ŞablonXətası> {
    let mut qovşaqlar: Vec<Q> = vec![];
    let mut bloklar: HashMap<String, Vec<Q>> = HashMap::new();
    let mut genişlət = None;
    let mut yığın: Vec<Rc<RefCell<Blok>>> = vec![];
    let mut mövqe = 0;
    fn hədəfə(yığın: &[Rc<RefCell<Blok>>], qovşaqlar: &mut Vec<Q>, q: Q) {
        match yığın.last() {
            Some(b) => {
                let mut b = b.borrow_mut();
                match b.yoxsa.as_mut() {
                    Some(y) => y.push(q),
                    None => b.gövdə.push(q),
                }
            }
            None => qovşaqlar.push(q),
        }
    }
    for (başla, son, p) in parçalar(m) {
        let əvvəl = &m[mövqe..başla];
        if !əvvəl.is_empty() {
            hədəfə(&yığın, &mut qovşaqlar, Q::Mətn(əvvəl.to_string()));
        }
        mövqe = son;
        let sətir = m[..başla].matches('\n').count() + 1;
        match p {
            Parça::Şərh => continue,
            Parça::Dəyər(d) => {
                hədəfə(&yığın, &mut qovşaqlar, dəyəri_ayır(&d, sətir, fayl));
                continue;
            }
            Parça::Əmr(ə) => {
                let ə = ə.trim();
                if ə.is_empty() {
                    continue;
                }
                let (ad_, arqument) = match ə.split_once(char::is_whitespace) {
                    Some((a, b)) => (a, b.trim().to_string()),
                    None => (ə, String::new()),
                };
                if ["əgər", "eger", "hər", "her", "blok"].contains(&ad_) {
                    let normal = match ad_ {
                        "eger" => "əgər",
                        "her" => "hər",
                        x => x,
                    };
                    let b = Rc::new(RefCell::new(Blok {
                        növ: normal.into(),
                        arqument,
                        gövdə: vec![],
                        yoxsa: None,
                        sətir,
                        fayl: fayl.into(),
                    }));
                    hədəfə(&yığın, &mut qovşaqlar, Q::Blok(b.clone()));
                    yığın.push(b);
                    continue;
                }
                if ad_ == "yoxsa" || ad_ == "eks" || ["yoxsa", "əks halda", "eks halda"].contains(&ə) {
                    match yığın.last() {
                        None => return Err(sx("`{% yoxsa %}` uyğun bloku yoxdur", fayl, sətir)),
                        Some(b) => b.borrow_mut().yoxsa = Some(vec![]),
                    }
                    continue;
                }
                if ad_ == "son" {
                    match yığın.pop() {
                        None => return Err(sx("`{% son %}` uyğun bloku yoxdur", fayl, sətir)),
                        Some(b) => {
                            let b = b.borrow();
                            if b.növ == "blok" {
                                bloklar.insert(b.arqument.trim().to_string(), b.gövdə.clone());
                            }
                        }
                    }
                    continue;
                }
                if ad_ == "daxilEt" || ad_ == "daxilet" {
                    hədəfə(&yığın, &mut qovşaqlar, Q::Daxil { yol: sitatı_çıxar(&arqument) });
                    continue;
                }
                if ad_ == "genişlət" || ad_ == "genislet" {
                    genişlət = Some(sitatı_çıxar(&arqument));
                    continue;
                }
                return Err(sx(format!("Naməlum şablon əmri: `{}`", ad_), fayl, sətir));
            }
        }
    }
    if let Some(b) = yığın.last() {
        let b = b.borrow();
        return Err(sx(format!("`{{% {} %}}` bağlanmayıb — `{{% son %}}` lazımdır", b.növ), fayl, b.sətir));
    }
    let qalan = &m[mövqe..];
    if !qalan.is_empty() {
        qovşaqlar.push(Q::Mətn(qalan.to_string()));
    }
    Ok((qovşaqlar, genişlət, bloklar))
}

impl Şablon {
    pub fn yeni(m: &str, ad_: &str, qovluq: Option<PathBuf>) -> Result<Şablon, ŞablonXətası> {
        let (qovşaqlar, genişlət, bloklar) = ayır(m, ad_)?;
        Ok(Şablon { qovşaqlar, genişlət, bloklar, ad: ad_.into(), qovluq })
    }
}

/// `şablonu_yüklə(yol, qovluq)` (dəyişmə vaxtına görə keş)
pub fn yüklə(yol: &str, qovluq: Option<&Path>) -> Result<Rc<Şablon>, ŞablonXətası> {
    thread_local! {
        static KEŞ: RefCell<HashMap<PathBuf, (std::time::SystemTime, Rc<Şablon>)>> = RefCell::new(HashMap::new());
    }
    let mut p = PathBuf::from(yol);
    if !p.exists() {
        if let Some(q) = qovluq {
            p = q.join(yol);
        }
    }
    if !p.exists() {
        return Err(sx(format!("\"{}\" şablonu tapılmadı", yol), "", 0));
    }
    let açar = std::fs::canonicalize(&p).unwrap_or(p.clone());
    let vaxt = std::fs::metadata(&p).and_then(|m| m.modified()).unwrap_or(std::time::UNIX_EPOCH);
    if let Some(ş) = KEŞ.with(|k| k.borrow().get(&açar).filter(|(v, _)| *v == vaxt).map(|(_, ş)| ş.clone())) {
        return Ok(ş);
    }
    let mətn = std::fs::read(&p).ok().and_then(|b| String::from_utf8(b).ok()).ok_or_else(|| sx(format!("\"{}\" oxunmadı", yol), "", 0))?;
    let ad_ = p.file_name().map(|x| x.to_string_lossy().to_string()).unwrap_or_default();
    let qov = qovluq.map(Path::to_path_buf).or_else(|| p.parent().map(Path::to_path_buf));
    let ş = Rc::new(Şablon::yeni(&mətn, &ad_, qov)?);
    KEŞ.with(|k| k.borrow_mut().insert(açar, (vaxt, ş.clone())));
    Ok(ş)
}

// ── Filtrlər ───────────────────────────────────────────────────────────

const FİLTRLƏR: &[&str] =
    &["böyüyə", "kiçiyə", "başBöyük", "kəs", "uzunluq", "yuvarlaqlaşdır", "pul", "format", "standart", "tərs", "latınla", "URLKodla"];

fn int_(s: &str) -> Result<i64, String> {
    s.trim().replace('_', "").parse::<i64>().map_err(|_| format!("invalid literal for int() with base 10: {}", str_repr(s)))
}

fn float_(d: &D) -> Result<f64, String> {
    match d {
        D::T(_) | D::BT(_) | D::O(_) | D::M(_) => Ok(d.onluq().unwrap()),
        D::S(s) => s.trim().parse::<f64>().map_err(|_| format!("could not convert string to float: {}", str_repr(s))),
        D::Boş => Err("float() argument must be a string or a real number, not 'NoneType'".into()),
        x => Err(format!("float() argument must be a string or a real number, not '{}'", tip_adı(x))),
    }
}

/// Python `round(x)` (yarımda cüt)
fn round_(x: f64) -> f64 {
    let r = x.round();
    if (x - x.trunc()).abs() == 0.5 {
        2.0 * (x / 2.0).round()
    } else {
        r
    }
}

fn filtr(ad_: &str, d: D, a: &[String]) -> Result<D, String> {
    let s = || py_s(&d);
    Ok(match ad_ {
        "böyüyə" => D::str(crate::elifba::böyüyə(&s())),
        "kiçiyə" => D::str(crate::elifba::kiçiyə(&s())),
        "başBöyük" => D::str(crate::elifba::baş_böyük(&s())),
        "kəs" => {
            let m = s();
            let hədd = int_(a.first().map(String::as_str).unwrap_or("100"))?;
            let n = m.chars().count() as i64;
            if n <= hədd {
                D::str(m)
            } else {
                let k = if hədd >= 0 { hədd } else { (n + hədd).max(0) } as usize;
                D::str(m.chars().take(k).collect::<String>() + "…")
            }
        }
        "uzunluq" => D::str(
            match &d {
                D::S(x) => x.chars().count(),
                D::Siyahı(l) => l.borrow().len(),
                D::Lüğət(l) => l.borrow().len(),
                D::Dəst(l) => l.borrow().len(),
                D::Kortej(k) => k.len(),
                D::Bayt(b) => b.len(),
                _ => 0,
            }
            .to_string(),
        ),
        "yuvarlaqlaşdır" => {
            let r = int_(a.first().map(String::as_str).unwrap_or("0"))?;
            let f = float_(&d)?;
            if r != 0 {
                D::str(format!("{:.*}", r.max(0) as usize, f))
            } else {
                D::str(format!("{}", round_(f) as i64))
            }
        }
        "pul" => D::str(super::modullar::yerli_ədəd(float_(&d)?, Some(2)) + " ₼"),
        "format" => match &d {
            D::T(_) | D::O(_) | D::BT(_) | D::M(_) => {
                let n = a.first().cloned().unwrap_or("DD.MM.YYYY".into());
                let m = d.onluq().unwrap();
                D::str(super::modullar::vaxt_formatla(&n, if m != 0.0 { Some(m as i64) } else { None }))
            }
            _ => D::str(s()),
        },
        "standart" => match &d {
            D::Boş => D::str(a.first().cloned().unwrap_or_default()),
            D::S(x) if x.is_empty() => D::str(a.first().cloned().unwrap_or_default()),
            _ => D::str(s()),
        },
        "tərs" => D::str(s().chars().rev().collect()),
        "latınla" => D::str(crate::elifba::latınla(&s())),
        "URLKodla" => D::str(super::mod_kodlasdirma::quote(&s(), "")),
        _ => unreachable!(),
    })
}

pub fn html_qaç(m: &str) -> String {
    m.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;").replace('\'', "&#39;")
}

// ── Göstərici ──────────────────────────────────────────────────────────

struct Göstərici<'a> {
    i: &'a İcraçı,
    ş: Rc<Şablon>,
    bloklar: Rc<HashMap<String, Vec<Q>>>,
    ağaclar: RefCell<HashMap<String, E>>,
}

fn doğrudur(d: &D) -> bool {
    match d {
        D::Boş | D::M(false) => false,
        D::S(s) => !s.is_empty(),
        D::Siyahı(l) => !l.borrow().is_empty(),
        D::Lüğət(l) => !l.borrow().is_empty(),
        D::Dəst(l) => !l.borrow().is_empty(),
        D::Kortej(k) => !k.is_empty(),
        D::T(n) => *n != 0,
        D::BT(_) => true,
        D::O(f) => *f != 0.0,
        _ => true,
    }
}

impl<'a> Göstərici<'a> {
    fn göstər(&self, verilənlər: Vec<(String, D)>) -> Ş<String> {
        let m = self.i.qlobal.alt();
        for (a, d) in verilənlər {
            m.elan(ad(&a), d, false);
        }
        if let Some(g) = &self.ş.genişlət {
            let valideyn = self.yüklə(g)?;
            let gö = Göstərici { i: self.i, ş: valideyn.clone(), bloklar: Rc::new(self.ş.bloklar.clone()), ağaclar: Default::default() };
            return gö.qovşaqlar(&valideyn.qovşaqlar, &m);
        }
        self.qovşaqlar(&self.ş.qovşaqlar, &m)
    }

    fn yüklə(&self, yol: &str) -> Ş<Rc<Şablon>> {
        Ok(yüklə(yol, self.ş.qovluq.as_deref())?)
    }

    fn qovşaqlar(&self, q: &[Q], m: &Mühit) -> Ş<String> {
        let mut s = String::new();
        for x in q {
            s.push_str(&self.qovşaq(x, m)?);
        }
        Ok(s)
    }

    fn qovşaq(&self, q: &Q, m: &Mühit) -> Ş<String> {
        match q {
            Q::Mətn(s) => Ok(s.clone()),
            Q::Dəyər { ifadə, filtrlər, xam, sətir, fayl } => self.dəyər(ifadə, filtrlər, *xam, *sətir, fayl, m),
            Q::Daxil { yol } => {
                let alt = self.yüklə(yol)?;
                let g = Göstərici { i: self.i, ş: alt.clone(), bloklar: self.bloklar.clone(), ağaclar: Default::default() };
                g.qovşaqlar(&alt.qovşaqlar, m)
            }
            Q::Blok(b) => {
                let b = b.borrow();
                match b.növ.as_str() {
                    "əgər" => {
                        let ş = self.qiymətləndir(&b.arqument, m, b.sətir, &b.fayl)?;
                        if doğrudur(&ş) {
                            self.qovşaqlar(&b.gövdə, m)
                        } else if let Some(y) = &b.yoxsa {
                            self.qovşaqlar(y, m)
                        } else {
                            Ok(String::new())
                        }
                    }
                    "hər" => self.hər(&b, m),
                    "blok" => {
                        let gövdə = self.bloklar.get(b.arqument.trim()).cloned().unwrap_or_else(|| b.gövdə.clone());
                        self.qovşaqlar(&gövdə, m)
                    }
                    _ => Ok(String::new()),
                }
            }
        }
    }

    fn dəyər(&self, ifadə: &str, filtrlər: &[(String, Vec<String>)], xam: bool, sətir: usize, fayl: &str, m: &Mühit) -> Ş<String> {
        let mut d = self.qiymətləndir(ifadə, m, sətir, fayl)?;
        let fayl_ = if fayl.is_empty() { self.ş.ad.as_str() } else { fayl };
        for (ad_, a) in filtrlər {
            if !FİLTRLƏR.contains(&ad_.as_str()) {
                let mut f: Vec<&str> = FİLTRLƏR.to_vec();
                f.sort();
                return Err(sx(format!("Naməlum filtr: `{}`\nİcazəli filtrlər: {}", ad_, f.join(", ")), fayl_, sətir).into());
            }
            d = filtr(ad_, d, a).map_err(|x| sx(format!("`{}` filtri alınmadı: {}", ad_, x), fayl_, sətir))?;
        }
        if d.boşdur() {
            return Ok(String::new());
        }
        if let D::Element(e) = &d {
            return element_html(self.i, e).map_err(Şx::S);
        }
        let s = mətnə(self.i, &d).map_err(Şx::S)?;
        Ok(if xam { s } else { html_qaç(&s) })
    }

    fn hər(&self, b: &Blok, m: &Mühit) -> Ş<String> {
        let fayl_ = if b.fayl.is_empty() { self.ş.ad.clone() } else { b.fayl.clone() };
        let xam = &b.arqument;
        let (sol, sağ) = match [" üçün ", " ucun "].iter().find_map(|ü| xam.split_once(ü)) {
            Some(x) => x,
            None => return Err(sx("`hər` başlığı belə olmalıdır: `{% hər x üçün siyahı içində %}`", &fayl_, b.sətir).into()),
        };
        let adlar: Vec<String> = sol.split(',').map(|a| a.trim().to_string()).filter(|a| !a.is_empty()).collect();
        let mənbə_ifadəsi = match [" içində", " icinde"].iter().find_map(|i| sağ.strip_suffix(i)) {
            Some(x) => x,
            None => return Err(sx("`hər` başlığının sonunda `içində` olmalıdır", &fayl_, b.sətir).into()),
        };
        if adlar.is_empty() {
            return Err(sx("`hər` üçün dəyişən adı yoxdur", &fayl_, b.sətir).into());
        }
        let mənbə = self.qiymətləndir(mənbə_ifadəsi.trim(), m, b.sətir, &b.fayl)?;
        let el = match self.i.siyahıya(&mənbə, None) {
            Ok(e) => e,
            Err(Siqnal::Xəta(x)) => return Err(sx(format!("`hər` üzərində dövr qurulmur: {}", x.mesaj), &fayl_, b.sətir).into()),
            Err(s) => return Err(Şx::S(s)),
        };
        if el.is_empty() {
            if let Some(y) = &b.yoxsa {
                return self.qovşaqlar(y, m);
            }
        }
        let mut s = String::new();
        let n = el.len();
        for (k, e) in el.into_iter().enumerate() {
            let alt = m.alt();
            if adlar.len() == 1 {
                alt.elan(ad(&adlar[0]), e, false);
            } else if let D::Lüğət(l) = &mənbə {
                let v = Açar::yeni(e.clone()).ok().and_then(|a| l.borrow().get(&a).cloned()).unwrap_or(D::Boş);
                alt.elan(ad(&adlar[0]), e, false);
                alt.elan(ad(&adlar[1]), v, false);
            } else {
                alt.elan(ad(&adlar[0]), D::T(k as i64), false);
                alt.elan(ad(&adlar[1]), e, false);
            }
            alt.elan(ad("_indeks"), D::T(k as i64), false);
            alt.elan(ad("_sayı"), D::T(n as i64), false);
            alt.elan(ad("_ilkdir"), D::M(k == 0), false);
            alt.elan(ad("_sondur"), D::M(k == n - 1), false);
            s.push_str(&self.qovşaqlar(&b.gövdə, &alt)?);
        }
        Ok(s)
    }

    fn qiymətləndir(&self, ifadə: &str, m: &Mühit, sətir: usize, fayl: &str) -> Ş<D> {
        let ifadə = ifadə.trim();
        if ifadə.is_empty() {
            return Ok(D::s(""));
        }
        let fayl = if fayl.is_empty() { self.ş.ad.clone() } else { fayl.to_string() };
        let ağac = self.ağac(ifadə, sətir, &fayl)?;
        match self.i.ifadə(&ağac, m) {
            Ok(d) => Ok(d),
            Err(Siqnal::Xəta(x)) => {
                Err(sx(format!("`{{{{ {} }}}}` qiymətləndirilmədi: {}", ifadə, x.mesaj), &fayl, sətir).into())
            }
            Err(s) => Err(Şx::S(s)),
        }
    }

    fn ağac(&self, ifadə: &str, sətir: usize, fayl: &str) -> Ş<E> {
        if let Some(a) = self.ağaclar.borrow().get(ifadə) {
            return Ok(a.clone());
        }
        let mut x = crate::xeta::XətaToplayıcı::yeni();
        let s = crate::xeta::Mənbə::yeni(&format!("{}:{}", fayl, sətir), ifadə, None);
        let t = {
            let mut l = crate::lekser::Lekser::yeni(s.clone(), &mut x);
            l.ascii_xəbərdarlığı = false;
            l.leksə()
        };
        let ağac = {
            let mut p = crate::parser::Parser::yeni(t, s, &mut x);
            match p.ifadə(0) {
                Ok(a) => {
                    while p.bax(0).növ == crate::lekser::Növ::SətirSonu {
                        p.al();
                    }
                    if p.bax(0).növ != crate::lekser::Növ::FaylSonu {
                        let g = crate::parser::göstər(p.bax(0));
                        p.xəta("ALQ-P001", "Gözlənilməyən token", &format!("`{}` burada gözlənilmirdi", g), &[]);
                    }
                    Some(a)
                }
                Err(_) => None,
            }
        };
        let xətalar: Vec<&crate::xeta::Diaqnostika> = x.siyahı.iter().filter(|d| d.səviyyə == crate::xeta::Səviyyə::Xəta).collect();
        match ağac {
            Some(a) if xətalar.is_empty() => {
                self.ağaclar.borrow_mut().insert(ifadə.to_string(), a.clone());
                Ok(a)
            }
            _ => {
                let ilk = xətalar.first().map(|d| d.mesaj.clone()).unwrap_or("sintaksis xətası".into());
                let qeyd = xətalar.first().map(|d| d.qeyd.clone()).unwrap_or_default();
                let q = if qeyd.is_empty() { String::new() } else { format!(" — {}", qeyd) };
                Err(sx(format!("`{{{{ {} }}}}` ayrılmadı: {}{}", ifadə, ilk, q), fayl, sətir).into())
            }
        }
    }
}

/// Şablonu göstərir. `Err(Ok(x))` — şablon xətası, `Err(Err(s))` — siqnal.
pub fn göstər(i: &İcraçı, ş: Rc<Şablon>, verilənlər: Vec<(String, D)>) -> Result<String, Result<ŞablonXətası, Siqnal>> {
    let g = Göstərici { i, ş, bloklar: Rc::new(HashMap::new()), ağaclar: Default::default() };
    g.göstər(verilənlər).map_err(|e| match e {
        Şx::Ş(x) => Ok(x),
        Şx::S(s) => Err(s),
    })
}
