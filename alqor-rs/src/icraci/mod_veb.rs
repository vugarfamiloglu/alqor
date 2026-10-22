//! `veb` — HTTP server və marşrutlaşdırma (veb.py, § 11).
//!
//! Marşrutlar (`/istifadəçi/:id`, `:ad?`, `*joker`), qruplar, ara
//! proqramlar (`jurnal`, `CORS`, `sıxma`, `təhlükəsizlikBaşlıqları`,
//! `sessiya`, `sürətLimiti`), statik fayllar, şablonlar (`.alqorhtml`),
//! JSX/JSON cavabları, kukilər, sessiyalar və port açmadan sınaq
//! müştərisi (`veb.sınaq.server`).
//!
//! Rust icraçısı tək saplıdır: server sorğuları ardıcıl idarə edir və
//! hər cavabdan sonra bağlantını bağlayır (`Connection: close`).
//! `komponent` və `soket` (WebSocket) hələ yalnız Python icraçısındadır.

use super::deyerler::*;
use super::elave::*;
use super::icraci::İcraçı;
use super::mod_kodlasdirma::{parse_qs, quote, unquote};
use indexmap::IndexMap;
use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::rc::{Rc, Weak};

const MAKS_GÖVDƏ: usize = 16 * 1024 * 1024;
const SESSİYA_KUKİSİ: &str = "alqor_sessiya";

fn vəziyyət_mətni(k: i64) -> &'static str {
    match k {
        200 => "OK",
        201 => "Created",
        204 => "No Content",
        301 => "Moved Permanently",
        302 => "Found",
        304 => "Not Modified",
        400 => "Bad Request",
        401 => "Unauthorized",
        403 => "Forbidden",
        404 => "Not Found",
        405 => "Method Not Allowed",
        409 => "Conflict",
        413 => "Payload Too Large",
        422 => "Unprocessable Content",
        429 => "Too Many Requests",
        500 => "Internal Server Error",
        503 => "Service Unavailable",
        _ => "",
    }
}

fn metod_adı(m: &str) -> String {
    match m {
        "GET" => "AL",
        "POST" => "GÖNDƏR",
        "PUT" => "YENİLƏ",
        "PATCH" => "YAMAQ",
        "DELETE" => "SİL",
        "HEAD" => "BAŞLIQ",
        "OPTIONS" => "SEÇİMLƏR",
        x => x,
    }
    .to_string()
}

fn qaç(m: &str) -> String {
    m.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}

/// Python `json.JSONDecodeError` mətni
pub fn json_xəta_mətni(m: &str, msg: &str, pos: usize) -> String {
    let c: Vec<char> = m.chars().collect();
    let önü = &c[..pos.min(c.len())];
    let sətir = önü.iter().filter(|x| **x == '\n').count() + 1;
    let sütun = match önü.iter().rposition(|x| *x == '\n') {
        Some(k) => pos - k,
        None => pos + 1,
    };
    format!("{}: line {} column {} (char {})", msg, sətir, sütun, pos)
}

// ═══════════════════════════════════════════════════════════════════════
//  Cavab
// ═══════════════════════════════════════════════════════════════════════

pub struct CavabV {
    pub vəziyyət: Cell<i64>,
    pub başlıqlar: RefCell<IndexMap<String, String>>,
    pub gövdə: RefCell<Vec<u8>>,
    pub kukilər: RefCell<Vec<String>>,
}

impl CavabV {
    pub fn yeni(gövdə: Vec<u8>, vəziyyət: i64, tip: &str) -> Rc<CavabV> {
        let mut b = IndexMap::new();
        b.insert("Content-Type".to_string(), tip.to_string());
        Rc::new(CavabV {
            vəziyyət: Cell::new(vəziyyət),
            başlıqlar: RefCell::new(b),
            gövdə: RefCell::new(gövdə),
            kukilər: RefCell::new(vec![]),
        })
    }
    fn mətn(g: Vec<u8>, k: i64) -> Rc<CavabV> {
        CavabV::yeni(g, k, "text/plain; charset=utf-8")
    }
    pub fn başlıq_qoy(&self, a: &str, d: &str) {
        self.başlıqlar.borrow_mut().insert(a.to_string(), d.to_string());
    }
    fn başlıq_al(&self, a: &str) -> Option<String> {
        let a = a.to_lowercase();
        if a == "set-cookie" && !self.kukilər.borrow().is_empty() {
            return Some(self.kukilər.borrow().join(", "));
        }
        self.başlıqlar.borrow().iter().find(|(k, _)| k.to_lowercase() == a).map(|(_, v)| v.clone())
    }
    fn başlıq_var(&self, a: &str) -> bool {
        self.başlıqlar.borrow().contains_key(a)
    }
    fn kuki(&self, ad_: &str, dəyər: &str, müddət: Option<i64>, yol: &str, yalnız_http: bool, təhlükəsiz: bool, eyni_sayt: &str) {
        let mut h = vec![format!("{}={}", ad_, quote(dəyər, "/")), format!("Path={}", yol), format!("SameSite={}", eyni_sayt)];
        if let Some(m) = müddət {
            h.push(format!("Max-Age={}", m));
        }
        if yalnız_http {
            h.push("HttpOnly".into());
        }
        if təhlükəsiz {
            h.push("Secure".into());
        }
        self.kukilər.borrow_mut().push(h.join("; "));
    }
}

pub fn cavab_d(c: Rc<CavabV>) -> D {
    obyekt("istənilən", c, |c| format!("<cavab {} {} bayt>", c.vəziyyət.get(), c.gövdə.borrow().len()), |w, v| {
        vec![
            ("kod", metod_ö(w, v, "kod", 1, Some(1), |_, c, ö, a, _| {
                c.vəziyyət.set(py_int(&a[0], "kod")?);
                Ok(ö)
            })),
            ("başlıq", metod_ö(w, v, "başlıq", 1, Some(2), |_, c, ö, a, _| {
                if a.len() == 1 {
                    return Ok(c.başlıq_al(&py_s(&a[0])).map(D::str).unwrap_or(D::Boş));
                }
                c.başlıq_qoy(&py_s(&a[0]), &py_s(&a[1]));
                Ok(ö)
            })),
            ("kuki", metod_ö(w, v, "kuki", 2, Some(2), |_, c, ö, a, adlı| {
                let n = imza("kuki", a, adlı, &["ad", "dəyər", "müddət", "yol", "yalnızHTTP", "təhlükəsiz", "eyniSayt"])?;
                let müddət = var(&n, 2).filter(|x| !x.boşdur()).map(|x| py_int(&x, "kuki")).transpose()?;
                c.kuki(
                    &py_s(&al(&n, 0)),
                    &py_s(&al(&n, 1)),
                    müddət,
                    &var(&n, 3).map(|x| py_s(&x)).unwrap_or("/".into()),
                    var(&n, 4).map(|x| doğrudur(&x)).unwrap_or(true),
                    var(&n, 5).map(|x| doğrudur(&x)).unwrap_or(false),
                    &var(&n, 6).map(|x| py_s(&x)).unwrap_or("Lax".into()),
                );
                Ok(ö)
            })),
            ("kukiSil", metod_ö(w, v, "kukiSil", 1, Some(2), |_, c, ö, a, adlı| {
                let n = imza("kukiSil", a, adlı, &["a", "yol"])?;
                let yol = var(&n, 1).map(|x| py_s(&x)).unwrap_or("/".into());
                c.kukilər.borrow_mut().push(format!("{}=; Path={}; Max-Age=0", py_s(&al(&n, 0)), yol));
                Ok(ö)
            })),
            ("vəziyyət", metod(v, "vəziyyət", 0, Some(0), |_, c, _, _| Ok(D::T(c.vəziyyət.get())))),
            ("mətnƏt", metod(v, "mətnƏt", 0, Some(0), |_, c, _, _| Ok(D::str(String::from_utf8_lossy(&c.gövdə.borrow()).to_string())))),
            ("json", metod(v, "json", 0, Some(0), |_, c, _, _| {
                let m = String::from_utf8_lossy(&c.gövdə.borrow()).to_string();
                super::modullar::json_oxu_mövqe(&m)
                    .map_err(|(msg, pos)| xəta("JSONXətası", json_xəta_mətni(&m, &msg, pos), "ALQ-R005"))
            })),
            ("uzunluq", metod(v, "uzunluq", 0, Some(0), |_, c, _, _| Ok(D::T(c.gövdə.borrow().len() as i64)))),
            ("uğurludur", metod(v, "uğurludur", 0, Some(0), |_, c, _, _| Ok(D::M((200..400).contains(&c.vəziyyət.get()))))),
        ]
    })
}

// ═══════════════════════════════════════════════════════════════════════
//  Sorğu və sessiya
// ═══════════════════════════════════════════════════════════════════════

type Anbar = Rc<RefCell<IndexMap<String, D>>>;

pub struct SorğuV {
    metod: String,
    yol: String,
    sorğu_sətri: String,
    başlıqlar: IndexMap<String, String>,
    gövdə: Vec<u8>,
    parametrlər: RefCell<IndexMap<String, String>>,
    ip: String,
    server: Rc<ServerV>,
    sessiya: RefCell<Option<Anbar>>,
    json_keşi: RefCell<Option<D>>,
}

impl SorğuV {
    fn başlıq(&self, a: &str) -> Option<String> {
        self.başlıqlar.get(&a.to_lowercase()).cloned()
    }
    fn kuki(&self, ad_: &str) -> Option<String> {
        let xam = self.başlıq("cookie").unwrap_or_default();
        for p in xam.split(';') {
            if let Some((k, v)) = p.split_once('=') {
                if k.trim() == ad_ {
                    return Some(unquote(v.trim()));
                }
            }
        }
        None
    }
    fn anbar(&self) -> Anbar {
        if let Some(a) = self.sessiya.borrow().as_ref() {
            return a.clone();
        }
        let a = match self.kuki(SESSİYA_KUKİSİ).filter(|x| !x.is_empty()) {
            Some(k) => self.server.sessiyalar.borrow_mut().entry(k).or_insert_with(|| Rc::new(RefCell::new(IndexMap::new()))).clone(),
            None => Rc::new(RefCell::new(IndexMap::new())),
        };
        *self.sessiya.borrow_mut() = Some(a.clone());
        a
    }
}

fn sorğu_d(s: Rc<SorğuV>) -> D {
    obyekt("istənilən", s, |s| format!("<sorğu {} {}>", metod_adı(&s.metod), s.yol), |_, v| {
        let ikili = |ad_: &'static str, g: fn(&SorğuV, &str) -> Option<String>| {
            metod(v, ad_, 1, Some(2), move |_, s, a, _| {
                Ok(g(s, &py_s(&a[0])).map(D::str).unwrap_or_else(|| a.get(1).cloned().unwrap_or(D::Boş)))
            })
        };
        vec![
            ("metod", metod(v, "metod", 0, Some(0), |_, s, _, _| Ok(D::str(metod_adı(&s.metod))))),
            ("yol", metod(v, "yol", 0, Some(0), |_, s, _, _| Ok(D::str(s.yol.clone())))),
            ("tamURL", metod(v, "tamURL", 0, Some(0), |_, s, _, _| {
                let host = s.başlıq("host").unwrap_or("localhost".into());
                let q = if s.sorğu_sətri.is_empty() { String::new() } else { format!("?{}", s.sorğu_sətri) };
                Ok(D::str(format!("http://{}{}{}", host, s.yol, q)))
            })),
            ("IP", metod(v, "IP", 0, Some(0), |_, s, _, _| Ok(D::str(s.ip.clone())))),
            ("istifadəçiAgenti", metod(v, "istifadəçiAgenti", 0, Some(0), |_, s, _, _| Ok(D::str(s.başlıq("user-agent").unwrap_or_default())))),
            ("parametr", ikili("parametr", |s, a| s.parametrlər.borrow().get(a).cloned())),
            ("parametrlər", metod(v, "parametrlər", 0, Some(0), |_, s, _, _| {
                Ok(lüğət_s(s.parametrlər.borrow().iter().map(|(a, b)| (a.clone(), D::str(b.clone()))).collect()))
            })),
            ("sorğuParametr", ikili("sorğuParametr", |s, a| parse_qs(&s.sorğu_sətri, false).get(a).and_then(|v| v.first().cloned()))),
            ("sorğuParametrHamısı", metod(v, "sorğuParametrHamısı", 0, Some(0), |_, s, _, _| {
                Ok(lüğət_s(parse_qs(&s.sorğu_sətri, false).into_iter().map(|(a, b)| (a, D::str(b[0].clone()))).collect()))
            })),
            ("başlıq", ikili("başlıq", |s, a| s.başlıq(a))),
            ("başlıqlar", metod(v, "başlıqlar", 0, Some(0), |_, s, _, _| {
                Ok(lüğət_s(s.başlıqlar.iter().map(|(a, b)| (a.clone(), D::str(b.clone()))).collect()))
            })),
            ("kuki", ikili("kuki", |s, a| s.kuki(a))),
            ("gövdə", metod(v, "gövdə", 0, Some(0), |_, s, _, _| Ok(D::str(String::from_utf8_lossy(&s.gövdə).to_string())))),
            ("gövdəBayt", metod(v, "gövdəBayt", 0, Some(0), |_, s, _, _| Ok(D::Bayt(Rc::new(s.gövdə.clone()))))),
            ("json", metod(v, "json", 0, Some(0), |_, s, _, _| {
                if let Some(d) = s.json_keşi.borrow().as_ref() {
                    return Ok(d.clone());
                }
                if s.gövdə.is_empty() {
                    return Ok(D::Boş);
                }
                let m = match String::from_utf8(s.gövdə.clone()) {
                    Ok(m) => m,
                    Err(e) => {
                        let b = e.as_bytes();
                        let k = e.utf8_error().valid_up_to();
                        return Err(xəta(
                            "JSONXətası",
                            format!(
                                "sorğu gövdəsi JSON deyil: 'utf-8' codec can't decode byte 0x{:02x} in position {}: invalid start byte",
                                b[k], k
                            ),
                            "ALQ-R005",
                        ));
                    }
                };
                let d = super::modullar::json_oxu_mövqe(&m).map_err(|(msg, pos)| {
                    xəta("JSONXətası", format!("sorğu gövdəsi JSON deyil: {}", json_xəta_mətni(&m, &msg, pos)), "ALQ-R005")
                })?;
                if !d.boşdur() {
                    *s.json_keşi.borrow_mut() = Some(d.clone());
                }
                Ok(d)
            })),
            ("form", metod(v, "form", 0, Some(0), |_, s, _, _| {
                let m = String::from_utf8_lossy(&s.gövdə).to_string();
                Ok(lüğət_s(parse_qs(&m, false).into_iter().map(|(a, b)| (a, D::str(b[0].clone()))).collect()))
            })),
            ("sessiya", metod(v, "sessiya", 0, Some(0), |_, s, _, _| Ok(sessiya_d(s.clone())))),
            ("mətnƏt", metod(v, "mətnƏt", 0, Some(0), |_, s, _, _| Ok(D::str(format!("<sorğu {} {}>", metod_adı(&s.metod), s.yol))))),
        ]
    })
}

fn sessiya_d(s: Rc<SorğuV>) -> D {
    obyekt("istənilən", s, |s| format!("<sessiya {} açar>", s.anbar().borrow().len()), |_, v| {
        vec![
            ("al", metod(v, "al", 1, Some(2), |_, s, a, _| {
                Ok(s.anbar().borrow().get(&py_s(&a[0])).cloned().unwrap_or_else(|| a.get(1).cloned().unwrap_or(D::Boş)))
            })),
            ("qoy", metod(v, "qoy", 2, Some(2), |_, s, a, _| {
                let açar = match s.kuki(SESSİYA_KUKİSİ).filter(|x| !x.is_empty()) {
                    Some(k) => k,
                    None => {
                        let k = super::mod_sifre::token_urlsafe(24);
                        *s.server.yeni_sessiya.borrow_mut() = Some(k.clone());
                        k
                    }
                };
                let anbar = s.server.sessiyalar.borrow_mut().entry(açar).or_insert_with(|| Rc::new(RefCell::new(IndexMap::new()))).clone();
                anbar.borrow_mut().insert(py_s(&a[0]), a[1].clone());
                *s.sessiya.borrow_mut() = Some(anbar);
                Ok(D::Boş)
            })),
            ("sil", metod(v, "sil", 1, Some(1), |_, s, a, _| Ok(s.anbar().borrow_mut().shift_remove(&py_s(&a[0])).unwrap_or(D::Boş)))),
            ("təmizlə", metod(v, "təmizlə", 0, Some(0), |_, s, _, _| {
                if let Some(k) = s.kuki(SESSİYA_KUKİSİ).filter(|x| !x.is_empty()) {
                    s.server.sessiyalar.borrow_mut().remove(&k);
                }
                *s.sessiya.borrow_mut() = Some(Rc::new(RefCell::new(IndexMap::new())));
                Ok(D::Boş)
            })),
            ("ehtiva", metod(v, "ehtiva", 1, Some(1), |_, s, a, _| Ok(D::M(s.anbar().borrow().contains_key(&py_s(&a[0])))))),
        ]
    })
}

// ═══════════════════════════════════════════════════════════════════════
//  Marşrut
// ═══════════════════════════════════════════════════════════════════════

pub struct Marşrut {
    metod: String,
    naxış: String,
    idarəedici: D,
    ara: Vec<D>,
    rx: fancy_regex::Regex,
    adlar: Vec<String>,
}

fn ad_başı(c: char) -> bool {
    c.is_ascii_alphabetic() || "ƏəİıĞğŞşÇçÖöÜü_".contains(c)
}

fn söz(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// `/istifadəçi/:id` → `^/istifadəçi/([^/]+)/?$` (+ parametr adları)
fn naxışı_çevir(n: &str) -> (String, Vec<String>) {
    let c: Vec<char> = n.chars().collect();
    let mut r: Vec<String> = vec!["^".into()];
    let mut adlar = vec![];
    let mut i = 0;
    while i < c.len() {
        if c[i] == ':' && i + 1 < c.len() && ad_başı(c[i + 1]) {
            let mut j = i + 2;
            while j < c.len() && söz(c[j]) {
                j += 1;
            }
            let ad_: String = c[i + 1..j].iter().collect();
            if j < c.len() && c[j] == '?' {
                if r.last().map(|x| x == "/").unwrap_or(false) {
                    r.pop();
                }
                r.push("(?:/([^/]+))?".into());
                j += 1;
            } else {
                r.push("([^/]+)".into());
            }
            adlar.push(ad_);
            i = j;
            continue;
        }
        if c[i] == '*' {
            let mut j = i + 1;
            if j < c.len() && ad_başı(c[j]) {
                j += 1;
                while j < c.len() && söz(c[j]) {
                    j += 1;
                }
                adlar.push(c[i + 1..j].iter().collect());
                r.push("(.*)".into());
            } else {
                r.push(".*".into());
            }
            i = j;
            continue;
        }
        let ch = c[i].to_string();
        r.push(if c[i] == '/' { "/".into() } else { fancy_regex::escape(&ch).to_string() });
        i += 1;
    }
    r.push("/?$".into());
    (r.concat(), adlar)
}

impl Marşrut {
    fn yeni(metod: &str, naxış: &str, idarəedici: D, ara: Vec<D>) -> Nəticə<Rc<Marşrut>> {
        let (rx, adlar) = naxışı_çevir(naxış);
        let rx = fancy_regex::Regex::new(&rx).map_err(|e| xəta("FormatXətası", format!("marşrut naxışı səhvdir: {e}"), "ALQ-R005"))?;
        Ok(Rc::new(Marşrut { metod: metod.into(), naxış: naxış.into(), idarəedici, ara, rx, adlar }))
    }
    fn yol_uyğundur(&self, yol: &str) -> bool {
        matches!(self.rx.is_match(yol), Ok(true))
    }
    fn uyğundur(&self, metod: &str, yol: &str) -> Option<IndexMap<String, String>> {
        if self.metod != "*" && self.metod != metod {
            return None;
        }
        let u = self.rx.captures(yol).ok()??;
        let mut n = IndexMap::new();
        for (k, a) in self.adlar.iter().enumerate() {
            if let Some(m) = u.get(k + 1) {
                n.insert(a.clone(), unquote(m.as_str()));
            }
        }
        Some(n)
    }
}

/// `(idarəedici)` və ya `([ara1, ara2], idarəedici)`
fn idarəedicini_ayır(a: &[D]) -> (D, Vec<D>) {
    if a.len() == 1 {
        return (a[0].clone(), vec![]);
    }
    if a.len() >= 2 {
        if let D::Siyahı(l) = &a[0] {
            return (a[1].clone(), l.borrow().clone());
        }
    }
    match a.split_last() {
        Some((s, q)) => (s.clone(), q.to_vec()),
        None => (D::Boş, vec![]),
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Server
// ═══════════════════════════════════════════════════════════════════════

pub struct ServerV {
    marşrutlar: RefCell<Vec<Rc<Marşrut>>>,
    ara: RefCell<Vec<D>>,
    statik: RefCell<Vec<(String, PathBuf, String)>>,
    xəta_idarəedicisi: RefCell<D>,
    tapılmadı: RefCell<D>,
    sessiyalar: RefCell<HashMap<String, Anbar>>,
    yeni_sessiya: RefCell<Option<String>>,
    dur: Cell<bool>,
    öz: RefCell<Weak<ServerV>>,
}

thread_local! {
    static ŞABLON_QOVLUĞU: RefCell<HashMap<usize, PathBuf>> = RefCell::new(HashMap::new());
}

/// Nisbi qovluq skriptin qovluğuna nisbətən həll olunur.
pub fn qovluğu_həll(i: &İcraçı, q: &str) -> PathBuf {
    let q = PathBuf::from(q);
    if q.is_absolute() {
        return q;
    }
    let Some(kök) = i.əsas_qovluq.borrow().clone() else { return q };
    let n = kök.join(&q);
    if n.exists() || !q.exists() {
        n
    } else {
        q
    }
}

fn şablon_qovluğu(i: &İcraçı) -> PathBuf {
    let q = ŞABLON_QOVLUĞU.with(|s| s.borrow().get(&(i as *const İcraçı as usize)).cloned());
    qovluğu_həll(i, &q.map(|p| p.to_string_lossy().to_string()).unwrap_or("şablon".into()))
}

fn şablon_qovluğunu_təyin_et(i: &İcraçı, q: &str) {
    ŞABLON_QOVLUĞU.with(|s| s.borrow_mut().insert(i as *const İcraçı as usize, PathBuf::from(q)));
}

/// İdarəedicinin nəticəsi → cavab
pub fn cavaba_çevir(i: &İcraçı, n: D) -> Nəticə<Rc<CavabV>> {
    if let Some(c) = veri::<CavabV>(&n) {
        return Ok(c);
    }
    Ok(match &n {
        D::Boş => CavabV::yeni(vec![], 204, "text/plain; charset=utf-8"),
        D::Element(e) => CavabV::yeni(element_html(i, e)?.into_bytes(), 200, "text/html; charset=utf-8"),
        D::S(s) => {
            let tip = if s.trim_start().starts_with('<') { "text/html; charset=utf-8" } else { "text/plain; charset=utf-8" };
            CavabV::yeni(s.as_bytes().to_vec(), 200, tip)
        }
        D::Lüğət(_) | D::Siyahı(_) | D::Kortej(_) | D::T(_) | D::BT(_) | D::O(_) | D::M(_) | D::Nümunə(_) => json_cavab(i, &n)?,
        x => CavabV::mətn(mətnə(i, x)?.into_bytes(), 200),
    })
}

/// `_json_hazırla` (kitabxana.py): sadalama → ad, bayt → base64, diapazon → siyahı
fn json_hazırla_veb(i: &İcraçı, d: &D) -> Nəticə {
    Ok(match d {
        D::Nümunə(_) | D::Lüğət(_) => {
            let mut l = Lüğət::default();
            for (a, v) in cütlər(d).unwrap() {
                let a = match a {
                    D::S(_) => a,
                    x => D::str(py_s(&x)),
                };
                l.insert(Açar(a), json_hazırla_veb(i, &v)?);
            }
            D::lüğət(l)
        }
        D::SD(s) => D::S(s.ad.clone()),
        D::Siyahı(_) | D::Kortej(_) | D::Dəst(_) | D::Diapazon(_) => {
            let mut v = vec![];
            for x in i.siyahıya(d, None)? {
                v.push(json_hazırla_veb(i, &x)?);
            }
            D::siyahı(v)
        }
        D::Bayt(b) => D::str(b64(b, B64, true)),
        x => x.clone(),
    })
}

fn json_cavab(i: &İcraçı, d: &D) -> Nəticə<Rc<CavabV>> {
    let g = json_dumps(i, &json_hazırla_veb(i, d)?, false, false)?;
    Ok(CavabV::yeni(g.into_bytes(), 200, "application/json; charset=utf-8"))
}

/// `yol_təhlükəlidir` — NUL, `\`, `.`/`..` seqmenti, daxili boş seqment
pub fn yol_təhlükəlidir(yol: &str) -> bool {
    if yol.is_empty() || yol.contains('\0') || yol.contains('\\') {
        return true;
    }
    let s: Vec<&str> = yol.split('/').collect();
    for (k, x) in s.iter().enumerate() {
        if *x == "." || *x == ".." {
            return true;
        }
        if x.is_empty() && k > 0 && k < s.len() - 1 {
            return true;
        }
    }
    false
}

type Nüvə = Rc<dyn Fn(&İcraçı, D) -> Nəticə<Rc<CavabV>>>;

impl ServerV {
    fn yeni() -> Rc<ServerV> {
        let s = Rc::new(ServerV {
            marşrutlar: RefCell::new(vec![]),
            ara: RefCell::new(vec![]),
            statik: RefCell::new(vec![]),
            xəta_idarəedicisi: RefCell::new(D::Boş),
            tapılmadı: RefCell::new(D::Boş),
            sessiyalar: RefCell::new(HashMap::new()),
            yeni_sessiya: RefCell::new(None),
            dur: Cell::new(false),
            öz: RefCell::new(Weak::new()),
        });
        *s.öz.borrow_mut() = Rc::downgrade(&s);
        s
    }

    fn idarə_et(&self, i: &İcraçı, sorğu: D) -> Nəticə<Rc<CavabV>> {
        let s = veri::<SorğuV>(&sorğu).unwrap();
        if yol_təhlükəlidir(&s.yol) {
            return Ok(CavabV::mətn("400 Yol etibarsızdır".as_bytes().to_vec(), 400));
        }
        let zəncir = self.ara.borrow().clone();
        let öz = self.öz.borrow().upgrade().unwrap();
        let nüvə: Nüvə = Rc::new(move |i, s| öz.marşrutu_tap(i, s));
        zənciri_işlət(i, Rc::new(zəncir), 0, nüvə, sorğu)
    }

    fn marşrutu_tap(&self, i: &İcraçı, sorğu: D) -> Nəticə<Rc<CavabV>> {
        let s = veri::<SorğuV>(&sorğu)
            .ok_or_else(|| xəta("TipXətası", format!("`növbəti` sorğu gözləyir, `{}` gəlib", tip_adı(&sorğu)), "ALQ-T001"))?;
        if let Some(c) = self.statik_cavab(&s) {
            return Ok(c);
        }
        let mut yol_var = false;
        let marşrutlar = self.marşrutlar.borrow().clone();
        for m in marşrutlar {
            let Some(p) = m.uyğundur(&s.metod, &s.yol) else {
                if m.yol_uyğundur(&s.yol) {
                    yol_var = true;
                }
                continue;
            };
            *s.parametrlər.borrow_mut() = p;
            if !m.ara.is_empty() {
                let m2 = m.clone();
                let nüvə: Nüvə = Rc::new(move |i, s| cavaba_çevir(i, çağır(i, &m2.idarəedici, vec![s])?));
                return zənciri_işlət(i, Rc::new(m.ara.clone()), 0, nüvə, sorğu);
            }
            return cavaba_çevir(i, çağır(i, &m.idarəedici, vec![sorğu])?);
        }
        if yol_var {
            return Ok(CavabV::mətn("405 Metod icazəli deyil".as_bytes().to_vec(), 405));
        }
        let t = self.tapılmadı.borrow().clone();
        if !t.boşdur() {
            return cavaba_çevir(i, çağır(i, &t, vec![sorğu])?);
        }
        Ok(self.c404(&s))
    }

    fn c404(&self, s: &SorğuV) -> Rc<CavabV> {
        let sətirlər: String =
            self.marşrutlar.borrow().iter().map(|m| format!("<li><code>{}</code> {}</li>", m.metod, m.naxış)).collect();
        let html = format!(
            "<!DOCTYPE html><html lang='az'><head><meta charset='utf-8'><title>404 — Tapılmadı</title><style>body{{font-family:system-ui;max-width:42rem;margin:3rem auto;padding:0 1rem;line-height:1.6}}code{{background:#f4f4f5;padding:.1rem .3rem;border-radius:3px}}h1{{font-size:1.5rem}}</style></head><body><h1>404 — <code>{}</code> tapılmadı</h1><p>Bu serverdə belə marşrut yoxdur.</p><h2>Mövcud marşrutlar</h2><ul>{}</ul><p style='color:#71717a'>Alqor inkişaf serveri</p></body></html>",
            qaç(&s.yol),
            sətirlər
        );
        CavabV::yeni(html.into_bytes(), 404, "text/html; charset=utf-8")
    }

    fn statik_cavab(&self, s: &SorğuV) -> Option<Rc<CavabV>> {
        if s.metod != "GET" && s.metod != "HEAD" {
            return None;
        }
        for (prefiks, qovluq, indeks) in self.statik.borrow().iter() {
            if !prefiks.is_empty() && !s.yol.starts_with(&format!("{}/", prefiks)) && s.yol != *prefiks {
                continue;
            }
            let mut nisbi = s.yol[prefiks.len()..].trim_start_matches('/').to_string();
            if nisbi.is_empty() && !indeks.is_empty() {
                nisbi = indeks.clone();
            }
            if nisbi.is_empty() {
                continue;
            }
            let kök = mütləq_yol(qovluq);
            let mut hədəf = mütləq_yol(&qovluq.join(&nisbi));
            if hədəf != kök && !hədəf.starts_with(&kök) {
                return Some(CavabV::mətn(b"403 Forbidden".to_vec(), 403));
            }
            if hədəf.is_dir() && !indeks.is_empty() {
                hədəf = hədəf.join(indeks);
            }
            if !hədəf.is_file() {
                continue;
            }
            let ad_ = hədəf.to_string_lossy().to_string();
            let mut tip = super::mod_veb_ortaq::mime_tipi(&ad_).unwrap_or("application/octet-stream").to_string();
            if tip.starts_with("text/") || tip == "application/javascript" || tip == "application/json" {
                tip += "; charset=utf-8";
            }
            let b = std::fs::read(&hədəf).ok()?;
            let c = CavabV::yeni(b, 200, &tip);
            c.başlıq_qoy("Cache-Control", "public, max-age=3600");
            return Some(c);
        }
        None
    }

    fn alqor_xətası(&self, i: &İcraçı, sorğu: &D, x: &AlqorXəta) -> Nəticə<Rc<CavabV>> {
        let s = veri::<SorğuV>(sorğu).unwrap();
        let id = self.xəta_idarəedicisi.borrow().clone();
        if !id.boşdur() {
            match çağır(i, &id, vec![sorğu.clone(), super::cagiris::xəta_obyekti(x)]).and_then(|n| cavaba_çevir(i, n)) {
                Ok(c) => return Ok(c),
                Err(Siqnal::Xəta(_)) => {}
                Err(e) => return Err(e),
            }
        }
        let yer = x.yer.map(|y| format!(" ({})", y.göstər())).unwrap_or_default();
        let mesaj = format!("{}: {}{}", x.tip, x.mesaj, yer);
        i.boşalt();
        i.xəta_yaz(&format!("✖ {} {} → {}", metod_adı(&s.metod), s.yol, mesaj));
        let html = format!(
            "<!DOCTYPE html><html lang='az'><head><meta charset='utf-8'><title>500 — Server xətası</title><style>body{{font-family:system-ui;max-width:48rem;margin:3rem auto;padding:0 1rem;line-height:1.6}}pre{{background:#18181b;color:#fafafa;padding:1rem;border-radius:6px;overflow-x:auto}}</style></head><body><h1>500 — Server xətası</h1><pre>{}</pre><p><code>{} {}</code></p></body></html>",
            qaç(&mesaj),
            metod_adı(&s.metod),
            qaç(&s.yol)
        );
        Ok(CavabV::yeni(html.into_bytes(), 500, "text/html; charset=utf-8"))
    }

    /// Sorğunu qurub idarə edir; sessiya kukisini əlavə edir.
    fn sorğunu_işlət(&self, i: &İcraçı, sorğu: D) -> Nəticə<Rc<CavabV>> {
        *self.yeni_sessiya.borrow_mut() = None;
        let c = match self.idarə_et(i, sorğu.clone()) {
            Ok(c) => c,
            Err(Siqnal::Xəta(x)) => self.alqor_xətası(i, &sorğu, &x)?,
            Err(e) => return Err(e),
        };
        if let Some(y) = self.yeni_sessiya.borrow_mut().take() {
            c.kuki(SESSİYA_KUKİSİ, &y, Some(86400), "/", true, false, "Lax");
        }
        Ok(c)
    }
}

fn mütləq_yol(p: &Path) -> PathBuf {
    if let Ok(c) = std::fs::canonicalize(p) {
        return c;
    }
    let tam = if p.is_absolute() { p.to_path_buf() } else { std::env::current_dir().unwrap_or_default().join(p) };
    let mut n = PathBuf::new();
    for c in tam.components() {
        match c {
            std::path::Component::ParentDir => {
                n.pop();
            }
            std::path::Component::CurDir => {}
            x => n.push(x.as_os_str()),
        }
    }
    n
}

fn zənciri_işlət(i: &İcraçı, zəncir: Rc<Vec<D>>, k: usize, nüvə: Nüvə, sorğu: D) -> Nəticə<Rc<CavabV>> {
    if k >= zəncir.len() {
        return nüvə(i, sorğu);
    }
    let ara = zəncir[k].clone();
    let (z2, n2) = (zəncir.clone(), nüvə.clone());
    let növbəti = daxili("növbəti", 1, Some(1), move |i, a, _| {
        Ok(cavab_d(zənciri_işlət(i, z2.clone(), k + 1, n2.clone(), a[0].clone())?))
    });
    cavaba_çevir(i, çağır(i, &ara, vec![sorğu, növbəti])?)
}

fn sorğu_qur(sv: &Rc<ServerV>, metod: &str, yol: &str, sorğu_sətri: &str, başlıqlar: &[(String, String)], gövdə: Vec<u8>, ip: &str) -> D {
    let mut b = IndexMap::new();
    for (k, v) in başlıqlar {
        b.insert(k.to_lowercase(), v.clone());
    }
    sorğu_d(Rc::new(SorğuV {
        metod: metod.into(),
        yol: yol.into(),
        sorğu_sətri: sorğu_sətri.into(),
        başlıqlar: b,
        gövdə,
        parametrlər: RefCell::new(IndexMap::new()),
        ip: ip.into(),
        server: sv.clone(),
        sessiya: RefCell::new(None),
        json_keşi: RefCell::new(None),
    }))
}

// ── Dinləmə ────────────────────────────────────────────────────────────

fn http_tarix() -> String {
    let t = super::platforma::indi_san() as i64;
    let (il, ay, gün, saat, dəq, san, hg) = super::platforma::mülki(t);
    const G: [&str; 7] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const A: [&str; 12] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    format!("{}, {:02} {} {} {:02}:{:02}:{:02} GMT", G[hg as usize % 7], gün, A[(ay as usize + 11) % 12], il, saat, dəq, san)
}

fn göndər(axın: &mut std::net::TcpStream, metod: &str, c: &CavabV) {
    let k = c.vəziyyət.get();
    let mut b = format!("HTTP/1.1 {} {}\r\nServer: Alqor \r\nDate: {}\r\n", k, vəziyyət_mətni(k), http_tarix());
    for (a, d) in c.başlıqlar.borrow().iter() {
        b.push_str(&format!("{}: {}\r\n", a, d));
    }
    for x in c.kukilər.borrow().iter() {
        b.push_str(&format!("Set-Cookie: {}\r\n", x));
    }
    let g = c.gövdə.borrow();
    b.push_str(&format!("Content-Length: {}\r\nConnection: close\r\n\r\n", g.len()));
    let _ = axın.write_all(b.as_bytes());
    if metod != "HEAD" {
        let _ = axın.write_all(&g);
    }
    let _ = axın.flush();
}

/// Bir HTTP sorğusunu oxuyur: (metod, yol, başlıqlar, gövdə) və ya cavab kodu
fn sorğu_oxu(axın: &mut std::net::TcpStream) -> Result<(String, String, Vec<(String, String)>, Vec<u8>), i64> {
    let _ = axın.set_read_timeout(Some(std::time::Duration::from_secs(30)));
    let mut b: Vec<u8> = vec![];
    let mut blok = [0u8; 8192];
    let son = loop {
        if let Some(k) = b.windows(4).position(|w| w == b"\r\n\r\n") {
            break k;
        }
        if b.len() > 65536 {
            return Err(431);
        }
        let n = axın.read(&mut blok).map_err(|_| 0)?;
        if n == 0 {
            return Err(0);
        }
        b.extend_from_slice(&blok[..n]);
    };
    let baş = String::from_utf8_lossy(&b[..son]).to_string();
    let mut sətirlər = baş.split("\r\n");
    let birinci = sətirlər.next().unwrap_or("");
    let h: Vec<&str> = birinci.split_whitespace().collect();
    if h.len() != 3 || !h[2].starts_with("HTTP/") {
        return Err(400);
    }
    let mut başlıqlar = vec![];
    for s in sətirlər {
        if let Some((a, d)) = s.split_once(':') {
            başlıqlar.push((a.trim().to_string(), d.trim().to_string()));
        }
    }
    let uzunluq: usize = başlıqlar
        .iter()
        .find(|(a, _)| a.eq_ignore_ascii_case("content-length"))
        .and_then(|(_, d)| d.parse().ok())
        .unwrap_or(0);
    if uzunluq > MAKS_GÖVDƏ {
        return Err(413);
    }
    let mut gövdə = b[son + 4..].to_vec();
    while gövdə.len() < uzunluq {
        let n = axın.read(&mut blok).map_err(|_| 0)?;
        if n == 0 {
            break;
        }
        gövdə.extend_from_slice(&blok[..n]);
    }
    gövdə.truncate(uzunluq);
    Ok((h[0].to_string(), h[1].to_string(), başlıqlar, gövdə))
}

fn dinlə(i: &İcraçı, sv: &Rc<ServerV>, port: &D, host: &D) -> Nəticə {
    let port = match std::env::var("PORT").ok().filter(|x| !x.is_empty()).or_else(|| std::env::var("ALQOR_PORT").ok().filter(|x| !x.is_empty())) {
        Some(p) => py_int(&D::str(p), "dinlə")?,
        None => py_int(port, "dinlə")?,
    };
    let host = std::env::var("ALQOR_HOST").ok().filter(|x| !x.is_empty()).unwrap_or_else(|| py_s(host));
    let l = match std::net::TcpListener::bind((host.as_str(), port as u16)) {
        Ok(l) => l,
        Err(e) => {
            let s = e.to_string();
            let s = s.split(" (os error").next().unwrap_or(&s).to_string();
            return Err(xəta("ŞəbəkəXətası", format!("{}:{} dinlənilə bilmədi — {}. Port məşğuldurmu?", host, port, s), "ALQ-R013"));
        }
    };
    i.yaz(&format!("✓ Alqor veb serveri: http://{}:{}", host, port));
    i.yaz(&format!("  {} marşrut, {} ara proqram", sv.marşrutlar.borrow().len(), sv.ara.borrow().len()));
    i.yaz("  Dayandırmaq üçün Ctrl+C");
    i.boşalt();
    sv.dur.set(false);
    for axın in l.incoming() {
        let Ok(mut axın) = axın else { continue };
        let ip = axın.peer_addr().map(|a| a.ip().to_string()).unwrap_or_default();
        let (metod, xam_yol, başlıqlar, gövdə) = match sorğu_oxu(&mut axın) {
            Ok(x) => x,
            Err(0) => continue,
            Err(k) => {
                let c = CavabV::mətn(format!("{} {}", k, vəziyyət_mətni(k)).into_bytes(), k);
                göndər(&mut axın, "GET", &c);
                continue;
            }
        };
        let a = super::mod_http::urlsplit(&xam_yol);
        let yol = {
            let y = unquote(&a.yol);
            if y.is_empty() { "/".to_string() } else { y }
        };
        let sorğu = sorğu_qur(sv, &metod, &yol, &a.sorğu, &başlıqlar, gövdə, &ip);
        let c = sv.sorğunu_işlət(i, sorğu)?;
        göndər(&mut axın, &metod, &c);
        i.boşalt();
        if sv.dur.get() {
            break;
        }
    }
    Ok(D::Boş)
}

// ── Sınaq müştərisi ────────────────────────────────────────────────────

struct Müştəri {
    server: Rc<ServerV>,
    kukilər: RefCell<IndexMap<String, String>>,
}

fn müştəri_sorğusu(i: &İcraçı, m: &Müştəri, metod: &str, yol: &D, gövdə: D, başlıqlar: D) -> Nəticə {
    let yol = py_s(yol);
    let a = super::mod_http::urlsplit(&yol);
    let mut b: Vec<(String, String)> = vec![("Host".into(), "sınaq".into())];
    if !m.kukilər.borrow().is_empty() {
        let k: Vec<String> = m.kukilər.borrow().iter().map(|(a, d)| format!("{}={}", a, d)).collect();
        b.push(("Cookie".into(), k.join("; ")));
    }
    let qoy = |b: &mut Vec<(String, String)>, a: String, d: String| match b.iter_mut().find(|(k, _)| *k == a) {
        Some(x) => x.1 = d,
        None => b.push((a, d)),
    };
    if let D::Lüğət(_) = &başlıqlar {
        for (a, d) in cütlər(&başlıqlar).unwrap() {
            qoy(&mut b, py_s(&a), py_s(&d));
        }
    }
    let mut xam = vec![];
    if !gövdə.boşdur() {
        if matches!(gövdə, D::Lüğət(_) | D::Siyahı(_)) {
            xam = json_dumps(i, &json_hazırla_veb(i, &gövdə)?, false, false)?.into_bytes();
            if !b.iter().any(|(k, _)| k == "Content-Type") {
                b.push(("Content-Type".into(), "application/json".into()));
            }
        } else {
            xam = mətnə(i, &gövdə)?.into_bytes();
        }
    }
    let y = unquote(&a.yol);
    let y = if y.is_empty() { "/".to_string() } else { y };
    let sorğu = sorğu_qur(&m.server, metod, &y, &a.sorğu, &b, xam, "127.0.0.1");
    let c = m.server.sorğunu_işlət(i, sorğu)?;
    for k in c.kukilər.borrow().iter() {
        let ad_dəyər = k.split(';').next().unwrap_or("");
        if let Some((a, d)) = ad_dəyər.split_once('=') {
            if d.is_empty() {
                m.kukilər.borrow_mut().shift_remove(a);
            } else {
                m.kukilər.borrow_mut().insert(a.to_string(), d.to_string());
            }
        }
    }
    Ok(cavab_d(c))
}

fn müştəri_d(server: Rc<ServerV>) -> D {
    let m = Rc::new(Müştəri { server, kukilər: RefCell::new(IndexMap::new()) });
    obyekt("istənilən", m, |_| "<sınaq müştərisi>".into(), |_, v| {
        let gövdəsiz = |ad_: &'static str, metod_: &'static str| {
            metod(v, ad_, 1, Some(2), move |i, m, a, adlı| {
                let n = imza(ad_, a, adlı, &["yol", "başlıqlar"])?;
                müştəri_sorğusu(i, m, metod_, &al(&n, 0), D::Boş, al(&n, 1))
            })
        };
        let gövdəli = |ad_: &'static str, metod_: &'static str| {
            metod(v, ad_, 1, Some(3), move |i, m, a, adlı| {
                let n = imza(ad_, a, adlı, &["yol", "gövdə", "başlıqlar"])?;
                müştəri_sorğusu(i, m, metod_, &al(&n, 0), al(&n, 1), al(&n, 2))
            })
        };
        vec![
            ("al", gövdəsiz("al", "GET")),
            ("göndər", gövdəli("göndər", "POST")),
            ("yenilə", gövdəli("yenilə", "PUT")),
            ("yamaq", gövdəli("yamaq", "PATCH")),
            ("sil", gövdəsiz("sil", "DELETE")),
        ]
    })
}

// ── Server və qrup obyektləri ──────────────────────────────────────────

fn marşrut_əlavə(sv: &ServerV, prefiks: &str, ara_əvvəl: &[D], metod: &str, a: &[D]) -> Nəticə<()> {
    let naxış = format!("{}{}", prefiks, py_s(&a[0]));
    let (id, mut ara) = idarəedicini_ayır(&a[1..]);
    let mut tam = ara_əvvəl.to_vec();
    tam.append(&mut ara);
    sv.marşrutlar.borrow_mut().push(Marşrut::yeni(metod, &naxış, id, tam)?);
    Ok(())
}

struct QrupV {
    server: Rc<ServerV>,
    prefiks: String,
    ara: RefCell<Vec<D>>,
}

fn qrup_d(q: Rc<QrupV>) -> D {
    obyekt("istənilən", q, |q| format!("<qrup {}>", if q.prefiks.is_empty() { "/" } else { &q.prefiks }), |w, v| {
        let m = |ad_: &'static str, h: &'static str| {
            metod_ö(w, v, ad_, 2, None, move |_, q, ö, a, _| {
                let ara = q.ara.borrow().clone();
                marşrut_əlavə(&q.server, &q.prefiks, &ara, h, &a)?;
                Ok(ö)
            })
        };
        vec![
            ("al", m("al", "GET")),
            ("göndər", m("göndər", "POST")),
            ("yenilə", m("yenilə", "PUT")),
            ("yamaq", m("yamaq", "PATCH")),
            ("sil", m("sil", "DELETE")),
            ("hamısı", m("hamısı", "*")),
            ("qrup", metod_ö(w, v, "qrup", 2, Some(2), |i, q, ö, a, _| {
                let alt = Rc::new(QrupV {
                    server: q.server.clone(),
                    prefiks: format!("{}{}", q.prefiks, py_s(&a[0])).trim_end_matches('/').to_string(),
                    ara: RefCell::new(q.ara.borrow().clone()),
                });
                çağır(i, &a[1], vec![qrup_d(alt)])?;
                Ok(ö)
            })),
            ("ara", metod_ö(w, v, "ara", 1, Some(1), |_, q, ö, a, _| {
                q.ara.borrow_mut().push(a[0].clone());
                Ok(ö)
            })),
        ]
    })
}

fn yalnız_py(ad_: &str) -> Siqnal {
    xəta(
        "ArqumentXətası",
        format!("`{}` Rust icraçısında hələ yoxdur — `alqor işlət --motor py` işlədin", ad_),
        "ALQ-M002",
    )
}

fn server_d(sv: Rc<ServerV>) -> D {
    obyekt("istənilən", sv, |s| format!("<server {} marşrut>", s.marşrutlar.borrow().len()), |w, v| {
        let m = |ad_: &'static str, h: &'static str| {
            metod_ö(w, v, ad_, 2, None, move |_, s, ö, a, _| {
                marşrut_əlavə(s, "", &[], h, &a)?;
                Ok(ö)
            })
        };
        vec![
            ("al", m("al", "GET")),
            ("göndər", m("göndər", "POST")),
            ("yenilə", m("yenilə", "PUT")),
            ("yamaq", m("yamaq", "PATCH")),
            ("sil", m("sil", "DELETE")),
            ("hamısı", m("hamısı", "*")),
            ("qrup", metod_ö(w, v, "qrup", 2, Some(2), |i, s, ö, a, _| {
                let q = Rc::new(QrupV {
                    server: s.öz.borrow().upgrade().unwrap(),
                    prefiks: py_s(&a[0]).trim_end_matches('/').to_string(),
                    ara: RefCell::new(vec![]),
                });
                çağır(i, &a[1], vec![qrup_d(q)])?;
                Ok(ö)
            })),
            ("ara", metod_ö(w, v, "ara", 1, Some(1), |_, s, ö, a, _| {
                s.ara.borrow_mut().push(a[0].clone());
                Ok(ö)
            })),
            ("statik", metod_ö(w, v, "statik", 2, Some(3), |i, s, ö, a, adlı| {
                let n = imza("statik", a, adlı, &["p", "q", "indeks"])?;
                let indeks = var(&n, 2).map(|x| py_s(&x)).unwrap_or_default();
                s.statik.borrow_mut().push((
                    py_s(&al(&n, 0)).trim_end_matches('/').to_string(),
                    qovluğu_həll(i, &py_s(&al(&n, 1))),
                    indeks,
                ));
                Ok(ö)
            })),
            ("şablonQovluğu", metod_ö(w, v, "şablonQovluğu", 1, Some(1), |i, _, ö, a, _| {
                şablon_qovluğunu_təyin_et(i, &py_s(&a[0]));
                Ok(ö)
            })),
            ("komponent", metod(v, "komponent", 2, Some(4), |_, _, _, _| Err(yalnız_py("server.komponent")))),
            ("soket", metod(v, "soket", 2, Some(2), |_, _, _, _| Err(yalnız_py("server.soket (WebSocket)")))),
            ("xətaİdarəedicisi", metod_ö(w, v, "xətaİdarəedicisi", 1, Some(1), |_, s, ö, a, _| {
                *s.xəta_idarəedicisi.borrow_mut() = a[0].clone();
                Ok(ö)
            })),
            ("tapılmadı", metod_ö(w, v, "tapılmadı", 1, Some(1), |_, s, ö, a, _| {
                *s.tapılmadı.borrow_mut() = a[0].clone();
                Ok(ö)
            })),
            ("dinlə", metod(v, "dinlə", 0, Some(2), |i, s, a, adlı| {
                let n = imza("dinlə", a, adlı, &["port", "host"])?;
                dinlə(i, s, &var(&n, 0).unwrap_or(D::T(8080)), &var(&n, 1).unwrap_or(D::s("127.0.0.1")))
            })),
            ("dayandır", metod(v, "dayandır", 0, Some(0), |_, s, _, _| {
                s.dur.set(true);
                Ok(D::Boş)
            })),
            ("marşrutlar", metod(v, "marşrutlar", 0, Some(0), |_, s, _, _| {
                Ok(D::siyahı(
                    s.marşrutlar.borrow().iter().map(|m| D::siyahı(vec![D::str(m.metod.clone()), D::str(m.naxış.clone())])).collect(),
                ))
            })),
            ("mətnƏt", metod(v, "mətnƏt", 0, Some(0), |_, s, _, _| Ok(D::str(format!("<server {} marşrut>", s.marşrutlar.borrow().len()))))),
        ]
    })
}

// ── Ara proqramlar ─────────────────────────────────────────────────────

fn ara(ad_: &'static str, f: impl Fn(&İcraçı, D, D) -> Nəticə<Rc<CavabV>> + 'static) -> D {
    daxili(ad_, 2, Some(2), move |i, a, _| Ok(cavab_d(f(i, a[0].clone(), a[1].clone())?)))
}

fn növbəti(i: &İcraçı, n: &D, s: &D) -> Nəticə<Rc<CavabV>> {
    cavaba_çevir(i, çağır(i, n, vec![s.clone()])?)
}

fn sorğu_v(s: &D) -> Nəticə<Rc<SorğuV>> {
    veri::<SorğuV>(s).ok_or_else(|| xəta("TipXətası", format!("sorğu gözlənilirdi, `{}` gəlib", tip_adı(s)), "ALQ-T001"))
}

/// `_müddəti_saniyəyə("1dəq")`
fn müddət_saniyə(d: &D) -> f64 {
    if let Some(f) = d.onluq().filter(|_| !matches!(d, D::M(_))) {
        return f;
    }
    let m = py_s(d).trim().to_lowercase();
    for (v, ç) in [("saat", 3600.0), ("san", 1.0), ("dəq", 60.0), ("deq", 60.0), ("gün", 86400.0), ("gun", 86400.0), ("dq", 60.0), ("s/", 3600.0), ("s", 1.0)] {
        if let Some(r) = m.strip_suffix(v) {
            let r = r.trim();
            let r = if r.is_empty() { "1" } else { r };
            return r.parse::<f64>().map(|x| x * ç).unwrap_or(60.0);
        }
    }
    m.parse::<f64>().unwrap_or(60.0)
}

fn ara_jurnal() -> D {
    ara("jurnal", |i, s, n| {
        let başla = super::platforma::monoton_san();
        let c = növbəti(i, &n, &s)?;
        let ms = (super::platforma::monoton_san() - başla) * 1000.0;
        let k = c.vəziyyət.get();
        let rəng = if k < 400 { "\x1b[32m" } else if k >= 500 { "\x1b[31m" } else { "\x1b[33m" };
        let sv = sorğu_v(&s)?;
        i.yaz(&format!("{}{}\x1b[0m {:<7} {:<32} {:7.2} ms  {} bayt", rəng, k, metod_adı(&sv.metod), sv.yol, ms, c.gövdə.borrow().len()));
        i.boşalt();
        Ok(c)
    })
}

fn siyahı_və_ya(d: &D, std: &str) -> String {
    match d {
        D::Siyahı(l) => l.borrow().iter().map(py_s).collect::<Vec<_>>().join(", "),
        D::Boş => std.into(),
        x if !doğrudur(x) => std.into(),
        x => py_s(x),
    }
}

fn ara_cors(mənbələr: D, metodlar: D) -> D {
    let icazəli = siyahı_və_ya(&mənbələr, "*");
    let im = match &metodlar {
        D::Siyahı(_) => siyahı_və_ya(&metodlar, ""),
        _ => "GET, POST, PUT, PATCH, DELETE, OPTIONS".into(),
    };
    ara("CORS", move |i, s, n| {
        let sv = sorğu_v(&s)?;
        let c = if sv.metod == "OPTIONS" { CavabV::mətn(vec![], 204) } else { növbəti(i, &n, &s)? };
        c.başlıq_qoy("Access-Control-Allow-Origin", &icazəli);
        c.başlıq_qoy("Access-Control-Allow-Methods", &im);
        c.başlıq_qoy("Access-Control-Allow-Headers", "Content-Type, Authorization");
        Ok(c)
    })
}

fn ara_sıxma(minimum: i64) -> D {
    ara("sıxma", move |i, s, n| {
        let c = növbəti(i, &n, &s)?;
        let sv = sorğu_v(&s)?;
        let qəbul = sv.başlıq("accept-encoding").unwrap_or_default();
        let tip = c.başlıqlar.borrow().get("Content-Type").cloned().unwrap_or_default();
        let olar = tip.starts_with("text/") || tip.contains("json") || tip.contains("javascript") || tip.contains("svg");
        if qəbul.contains("gzip") && olar && c.gövdə.borrow().len() as i64 >= minimum && !c.başlıq_var("Content-Encoding") {
            let g = super::mod_sixma::gzip_sıx(&c.gövdə.borrow(), 6);
            *c.gövdə.borrow_mut() = g;
            c.başlıq_qoy("Content-Encoding", "gzip");
            c.başlıq_qoy("Vary", "Accept-Encoding");
        }
        Ok(c)
    })
}

fn ara_təhlükəsizlik() -> D {
    ara("təhlükəsizlikBaşlıqları", |i, s, n| {
        let c = növbəti(i, &n, &s)?;
        c.başlıq_qoy("X-Content-Type-Options", "nosniff");
        c.başlıq_qoy("X-Frame-Options", "DENY");
        c.başlıq_qoy("Referrer-Policy", "strict-origin-when-cross-origin");
        c.başlıq_qoy("X-XSS-Protection", "0");
        Ok(c)
    })
}

fn ara_sürət(say: i64, pəncərə: f64) -> D {
    let qeydlər: RefCell<HashMap<String, Vec<f64>>> = RefCell::new(HashMap::new());
    ara("sürətLimiti", move |i, s, n| {
        let indi = super::platforma::indi_san();
        let sv = sorğu_v(&s)?;
        {
            let mut q = qeydlər.borrow_mut();
            let mut v: Vec<f64> = q.get(&sv.ip).cloned().unwrap_or_default().into_iter().filter(|t| indi - t < pəncərə).collect();
            if v.len() as i64 >= say {
                q.insert(sv.ip.clone(), v);
                let c = CavabV::mətn(b"429 Too Many Requests".to_vec(), 429);
                c.başlıq_qoy("Retry-After", &(pəncərə as i64).to_string());
                return Ok(c);
            }
            v.push(indi);
            q.insert(sv.ip.clone(), v);
        }
        növbəti(i, &n, &s)
    })
}

// ── Cavab qurucuları ───────────────────────────────────────────────────

fn c_html(i: &İcraçı, d: &D) -> Nəticə<Rc<CavabV>> {
    let mut g = match d {
        D::Element(e) => element_html(i, e)?,
        x => mətnə(i, x)?,
    };
    let k = g.trim_start();
    if k.chars().take(5).collect::<String>().to_lowercase() == "<html" {
        g = format!("<!DOCTYPE html>\n{}", g);
    }
    Ok(CavabV::yeni(g.into_bytes(), 200, "text/html; charset=utf-8"))
}

fn c_fayl(i: &İcraçı, yol: &str, ad_: &str) -> Nəticə<Rc<CavabV>> {
    let p = qovluğu_həll(i, yol);
    if !p.is_file() {
        return Err(xəta("FaylTapılmadıXətası", format!("\"{}\" faylı tapılmadı", yol), "ALQ-R009"));
    }
    let tip = super::mod_veb_ortaq::mime_tipi(&p.to_string_lossy()).unwrap_or("application/octet-stream");
    let b = std::fs::read(&p).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
    let c = CavabV::yeni(b, 200, tip);
    if !ad_.is_empty() {
        c.başlıq_qoy("Content-Disposition", &format!("attachment; filename=\"{}\"", ad_));
    }
    Ok(c)
}

fn c_şablon(i: &İcraçı, yol: &str, verilənlər: &D) -> Nəticə<Rc<CavabV>> {
    let v: Vec<(String, D)> = match verilənlər {
        D::Boş => vec![],
        D::Lüğət(_) | D::Nümunə(_) => cütlər(verilənlər).unwrap().into_iter().map(|(a, d)| (py_s(&a), d)).collect(),
        x => {
            return Err(xəta("TipXətası", format!("şablon verilənləri lüğət olmalıdır, `{}` gəlib", tip_adı(x)), "ALQ-T004"))
        }
    };
    let q = şablon_qovluğu(i);
    let nəticə = super::mod_sablon::yüklə(yol, Some(&q)).map_err(Ok).and_then(|ş| super::mod_sablon::göstər(i, ş, v));
    match nəticə {
        Ok(h) => Ok(CavabV::yeni(h.into_bytes(), 200, "text/html; charset=utf-8")),
        Err(Ok(x)) => Err(xəta("FormatXətası", format!("şablon xətası: {}", x), "ALQ-R005")),
        Err(Err(s)) => Err(s),
    }
}

fn boş_port(b: i64) -> i64 {
    for p in b..b + 50 {
        if std::net::TcpListener::bind(("127.0.0.1", p as u16)).is_ok() {
            return p;
        }
    }
    b
}

pub fn qur() -> Rc<Modul> {
    let c = |ad_: &'static str, f: fn(&İcraçı, &D) -> Nəticə<Rc<CavabV>>| {
        daxili(ad_, 1, Some(1), move |i, a, _| Ok(cavab_d(f(i, &a[0])?)))
    };
    let sınaq = Modul::yeni("veb.sınaq", vec![(
        "server",
        daxili("server", 1, Some(1), |_, a, _| {
            let sv = veri::<ServerV>(&a[0])
                .ok_or_else(|| xəta("TipXətası", format!("`veb.sınaq.server` server gözləyir, `{}` gəlib", tip_adı(&a[0])), "ALQ-T001"))?;
            Ok(müştəri_d(sv))
        }),
    )]);
    Modul::yeni("veb", vec![
        ("Server", daxili("Server", 0, Some(0), |_, _, _| Ok(server_d(ServerV::yeni())))),
        ("mətn", c("mətn", |i, d| Ok(CavabV::mətn(mətnə(i, d)?.into_bytes(), 200)))),
        ("html", c("html", c_html)),
        ("json", c("json", json_cavab)),
        ("boş", daxili("boş", 0, Some(1), |_, a, _| {
            let k = match a.first() {
                Some(x) => py_int(x, "boş")?,
                None => 204,
            };
            Ok(cavab_d(CavabV::mətn(vec![], k)))
        })),
        ("yönləndir", c("yönləndir", |_, u| {
            let c = CavabV::mətn(vec![], 302);
            c.başlıq_qoy("Location", &py_s(u));
            Ok(c)
        })),
        ("yönləndirDaimi", c("yönləndirDaimi", |_, u| {
            let c = CavabV::mətn(vec![], 301);
            c.başlıq_qoy("Location", &py_s(u));
            Ok(c)
        })),
        ("xəta", daxili("xəta", 1, Some(2), |_, a, _| {
            let k = py_int(&a[0], "xəta")?;
            let m = a.get(1).map(py_s).unwrap_or_default();
            let m = if m.is_empty() {
                let v = vəziyyət_mətni(k);
                if v.is_empty() { "Xəta".to_string() } else { v.to_string() }
            } else {
                m
            };
            Ok(cavab_d(CavabV::mətn(m.into_bytes(), k)))
        })),
        ("fayl", c("fayl", |i, y| c_fayl(i, &py_s(y), ""))),
        ("yüklə", daxili("yüklə", 1, Some(2), |i, a, _| {
            let y = py_s(&a[0]);
            let ad_ = a.get(1).map(py_s).filter(|x| !x.is_empty()).unwrap_or_else(|| {
                Path::new(&y).file_name().map(|x| x.to_string_lossy().to_string()).unwrap_or_default()
            });
            Ok(cavab_d(c_fayl(i, &y, &ad_)?))
        })),
        ("şablon", daxili("şablon", 1, Some(2), |i, a, adlı| {
            let n = imza("şablon", a, adlı, &["yol", "verilənlər"])?;
            Ok(cavab_d(c_şablon(i, &py_s(&al(&n, 0)), &al(&n, 1))?))
        })),
        ("şablonQovluğu", daxili("şablonQovluğu", 1, Some(1), |i, a, _| {
            şablon_qovluğunu_təyin_et(i, &py_s(&a[0]));
            Ok(D::Boş)
        })),
        ("jurnal", daxili("jurnal", 0, Some(0), |_, _, _| Ok(ara_jurnal()))),
        ("CORS", daxili("CORS", 0, Some(2), |_, a, adlı| {
            let n = imza("CORS", a, adlı, &["mənbələr", "metodlar"])?;
            Ok(ara_cors(al(&n, 0), al(&n, 1)))
        })),
        ("sıxma", daxili("sıxma", 0, Some(1), |_, a, adlı| {
            let n = imza("sıxma", a, adlı, &["minimum"])?;
            Ok(ara_sıxma(var(&n, 0).map(|x| py_int(&x, "sıxma")).transpose()?.unwrap_or(512)))
        })),
        ("təhlükəsizlikBaşlıqları", daxili("təhlükəsizlikBaşlıqları", 0, Some(0), |_, _, _| Ok(ara_təhlükəsizlik()))),
        ("sessiya", daxili("sessiya", 0, Some(1), |_, _, _| Ok(ara("sessiya", |i, s, n| növbəti(i, &n, &s))))),
        ("sürətLimiti", daxili("sürətLimiti", 0, Some(2), |_, a, adlı| {
            let n = imza("sürətLimiti", a, adlı, &["say", "pəncərə"])?;
            let say = var(&n, 0).map(|x| py_int(&x, "sürətLimiti")).transpose()?.unwrap_or(100);
            Ok(ara_sürət(say, müddət_saniyə(&var(&n, 1).unwrap_or(D::s("1dəq")))))
        })),
        ("boşPort", daxili("boşPort", 0, Some(1), |_, a, _| {
            let b = match a.first() {
                Some(x) => py_int(x, "boşPort")?,
                None => 8080,
            };
            Ok(D::T(boş_port(b)))
        })),
        ("sınaq", D::Modul(sınaq)),
    ])
}
