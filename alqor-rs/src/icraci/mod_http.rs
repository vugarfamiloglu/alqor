//! `http` — HTTP müştərisi (modullar/http_.py). `ureq` + rustls.
//!
//! Bütün funksiyalar `Gələcək` qaytarır (`gözlə` ilə həll olunur). 4xx/5xx
//! cavablar xəta deyil; bağlantı problemi — `BağlantıXətası`, vaxtın
//! bitməsi — `VaxtBitdiXətası`. Yalnız `http://` və `https://`.

use super::deyerler::*;
use super::elave::*;
use super::icraci::İcraçı;
use super::mod_kodlasdirma::{quote, quote_plus};
use std::cell::RefCell;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::time::Duration;

pub const İSTİFADƏÇİ_AGENTİ: &str = concat!("Alqor-http/", env!("CARGO_PKG_VERSION"));

fn x_(tip: &str, m: impl Into<String>) -> Siqnal {
    xəta(tip, m, "ALQ-R010")
}

fn metod_adı(m: &str) -> Option<&'static str> {
    Some(match m {
        "AL" | "GET" => "GET",
        "GÖNDƏR" | "POST" => "POST",
        "YENİLƏ" | "PUT" => "PUT",
        "YAMAQ" | "PATCH" => "PATCH",
        "SİL" | "DELETE" => "DELETE",
        "BAŞLIQ" | "HEAD" => "HEAD",
        "SEÇİMLƏR" | "OPTIONS" => "OPTIONS",
        _ => return None,
    })
}

/// Python `f"{x:g}"`
pub fn g_format(x: f64) -> String {
    if x == 0.0 {
        return "0".into();
    }
    let e = x.abs().log10().floor() as i32;
    if !(-5..6).contains(&e) {
        let s = format!("{:.5e}", x);
        let (m, ex) = s.split_once('e').unwrap();
        let m = if m.contains('.') { m.trim_end_matches('0').trim_end_matches('.') } else { m };
        let ex: i32 = ex.parse().unwrap();
        return format!("{}e{}{:02}", m, if ex < 0 { '-' } else { '+' }, ex.abs());
    }
    let r = (5 - e).max(0) as usize;
    let s = format!("{:.*}", r, x);
    if s.contains('.') {
        s.trim_end_matches('0').trim_end_matches('.').to_string()
    } else {
        s
    }
}

// ── URL ────────────────────────────────────────────────────────────────

pub struct Ayrılmış {
    pub sxem: String,
    pub netloc: String,
    pub yol: String,
    pub sorğu: String,
    pub fraq: String,
}

/// `urllib.parse.urlsplit`
pub fn urlsplit(url: &str) -> Ayrılmış {
    let mut q = url;
    let mut sxem = String::new();
    if let Some(k) = q.find(':') {
        let s = &q[..k];
        if !s.is_empty()
            && s.chars().next().unwrap().is_ascii_alphabetic()
            && s.chars().all(|c| c.is_ascii_alphanumeric() || "+-.".contains(c))
        {
            sxem = s.to_lowercase();
            q = &q[k + 1..];
        }
    }
    let mut netloc = String::new();
    if let Some(r) = q.strip_prefix("//") {
        let son = r.find(['/', '?', '#']).unwrap_or(r.len());
        netloc = r[..son].to_string();
        q = &r[son..];
    }
    let (q, fraq) = match q.split_once('#') {
        Some((a, b)) => (a, b.to_string()),
        None => (q, String::new()),
    };
    let (yol, sorğu) = match q.split_once('?') {
        Some((a, b)) => (a.to_string(), b.to_string()),
        None => (q.to_string(), String::new()),
    };
    Ayrılmış { sxem, netloc, yol, sorğu, fraq }
}

fn url_yoxla(url: &D) -> Nəticə<String> {
    let D::S(u) = url else {
        return Err(xəta("TipXətası", format!("URL mətn olmalıdır, `{}` gəlib", tip_adı(url)), "ALQ-T001"));
    };
    let p = urlsplit(u);
    if (p.sxem != "http" && p.sxem != "https") || p.netloc.is_empty() {
        return Err(xəta("DəyərXətası", format!("`{}` — yalnız http:// və https:// ünvanlarına icazə var", u), "ALQ-T001"));
    }
    let (istifadəçi, hp) = match p.netloc.rsplit_once('@') {
        Some((a, b)) => (Some(a.to_string()), b.to_string()),
        None => (None, p.netloc.clone()),
    };
    let (host, port) = if hp.starts_with('[') {
        match hp.find(']') {
            Some(k) => (hp[..=k].to_string(), hp[k + 1..].strip_prefix(':').map(String::from)),
            None => (hp.clone(), None),
        }
    } else {
        match hp.rsplit_once(':') {
            Some((h, p)) => (h.to_string(), Some(p.to_string())),
            None => (hp.clone(), None),
        }
    };
    let host = host.to_lowercase();
    let host = if host.is_ascii() { host } else { idna::domain_to_ascii(&host).unwrap_or(host) };
    let port = match port.filter(|p| !p.is_empty()) {
        Some(p) => match p.parse::<u16>() {
            Ok(n) => Some(n),
            Err(_) => {
                return Err(xəta("DəyərXətası", format!("Port could not be cast to integer value as {}", str_repr(&p)), "ALQ-R005"))
            }
        },
        None => None,
    };
    let mut netloc = host;
    if let Some(n) = port.filter(|n| *n != 0) {
        netloc = format!("{netloc}:{n}");
    }
    if let Some(i) = istifadəçi {
        let (a, b) = i.split_once(':').unwrap_or((&i, ""));
        netloc = format!("{a}:{b}@{netloc}");
    }
    let yol = quote(&p.yol, "/%:@!$&'()*+,;=-._~");
    let sorğu = quote(&p.sorğu, "=&%:@!$'()*+,;/?-._~");
    let mut r = format!("{}://{}{}", p.sxem, netloc, yol);
    if !sorğu.is_empty() {
        r.push('?');
        r.push_str(&sorğu);
    }
    if !p.fraq.is_empty() {
        r.push('#');
        r.push_str(&p.fraq);
    }
    Ok(r)
}

/// `urlencode(cütlər)` (quote_plus)
pub fn urlencode(c: &[(String, String)]) -> String {
    c.iter().map(|(a, d)| format!("{}={}", quote_plus(a, ""), quote_plus(d, ""))).collect::<Vec<_>>().join("&")
}

// ── Cavab ──────────────────────────────────────────────────────────────

pub struct Cavab {
    pub kod: u16,
    pub başlıqlar: Vec<(String, String)>,
    pub gövdə: Vec<u8>,
    pub url: String,
}

impl Cavab {
    fn başlıq(&self, a: &str) -> Option<String> {
        self.başlıqlar.iter().find(|(k, _)| k == a).map(|(_, v)| v.clone())
    }
    pub fn mətn(&self) -> String {
        let növ = self.başlıq("content-type").unwrap_or_default();
        let mut k = "utf-8".to_string();
        if let Some(i) = növ.rfind("charset=") {
            k = növ[i + 8..].split(';').next().unwrap_or("").trim().to_lowercase();
        }
        match k.as_str() {
            "latin-1" | "latin1" | "iso-8859-1" | "iso8859-1" => self.gövdə.iter().map(|&b| b as char).collect(),
            "ascii" | "us-ascii" => self.gövdə.iter().map(|&b| if b < 128 { b as char } else { '\u{fffd}' }).collect(),
            "windows-1254" | "cp1254" => super::mod_csv::cp1254(&self.gövdə),
            _ => String::from_utf8_lossy(&self.gövdə).to_string(),
        }
    }
    fn uğurlu(&self) -> bool {
        (200..300).contains(&self.kod)
    }
    fn yoxla(&self) -> Nəticə<()> {
        if !self.uğurlu() {
            let parça: String = self.mətn().chars().take(200).collect();
            let son = if parça.is_empty() { String::new() } else { format!(": {}", parça) };
            return Err(x_("HTTPXətası", format!("{} — {}{}", self.kod, self.url, son)));
        }
        Ok(())
    }
}

pub fn cavab_obyekti(c: Cavab) -> D {
    obyekt("httpCavabı", Rc::new(c), |c| format!("<http cavabı {}>", c.kod), |w, v| {
        vec![
            ("kod", metod(v, "kod", 0, Some(0), |_, c, _, _| Ok(D::T(c.kod as i64)))),
            ("uğurlu", metod(v, "uğurlu", 0, Some(0), |_, c, _, _| Ok(D::M(c.uğurlu())))),
            ("yoxla", metod_ö(w, v, "yoxla", 0, Some(0), |_, c, ö, _, _| {
                c.yoxla()?;
                Ok(ö)
            })),
            ("mətn", metod(v, "mətn", 0, Some(0), |_, c, _, _| Ok(D::str(c.mətn())))),
            ("json", metod(v, "json", 0, Some(0), |_, c, _, _| {
                super::modullar::json_oxu(&c.mətn()).map_err(|e| match e {
                    Siqnal::Xəta(x) => {
                        // "JSON formatı pozulub (sətir N): msg" → "cavab JSON deyil (sətir N): msg"
                        let m = x.mesaj.replacen("JSON formatı pozulub", "cavab JSON deyil", 1);
                        xəta("JSONXətası", m, "ALQ-R005")
                    }
                    s => s,
                })
            })),
            ("bayt", metod(v, "bayt", 0, Some(0), |_, c, _, _| Ok(D::Bayt(Rc::new(c.gövdə.clone()))))),
            ("başlıq", metod(v, "başlıq", 1, Some(2), |_, c, a, _| {
                Ok(c.başlıq(&py_s(&a[0]).to_lowercase()).map(D::str).unwrap_or_else(|| a.get(1).cloned().unwrap_or(D::Boş)))
            })),
            ("başlıqlar", metod(v, "başlıqlar", 0, Some(0), |_, c, _, _| {
                Ok(lüğət_s(c.başlıqlar.iter().map(|(a, b)| (a.clone(), D::str(b.clone()))).collect()))
            })),
            ("url", metod(v, "url", 0, Some(0), |_, c, _, _| Ok(D::str(c.url.clone())))),
        ]
    })
}

// ── Sorğu ──────────────────────────────────────────────────────────────

#[derive(Clone)]
pub struct SorğuV {
    pub metod: &'static str,
    pub url: String,
    pub başlıqlar: Vec<(String, String)>,
    pub parametrlər: Vec<(String, String)>,
    pub gövdə: Option<Vec<u8>>,
    pub vaxt: f64,
    pub yönləndir: bool,
}

impl SorğuV {
    pub fn yeni(metod: &D, url: &D) -> Nəticə<SorğuV> {
        let m = py_s(metod);
        let Some(md) = metod_ad_böyük(&m) else {
            return Err(xəta("DəyərXətası", format!("`{}` HTTP metodu deyil — AL, GÖNDƏR, YENİLƏ, YAMAQ, SİL", m), "ALQ-T001"));
        };
        Ok(SorğuV { metod: md, url: url_yoxla(url)?, başlıqlar: vec![], parametrlər: vec![], gövdə: None, vaxt: 30.0, yönləndir: true })
    }
    fn başlıq_qoy(&mut self, a: String, d: String) {
        match self.başlıqlar.iter_mut().find(|(k, _)| *k == a) {
            Some(x) => x.1 = d,
            None => self.başlıqlar.push((a, d)),
        }
    }
    fn başlıq_varsa(&mut self, a: &str, d: &str) {
        if !self.başlıqlar.iter().any(|(k, _)| k == a) {
            self.başlıqlar.push((a.into(), d.into()));
        }
    }
    fn gövdə_qoy(&mut self, i: &İcraçı, x: &D) -> Nəticə<()> {
        match x {
            D::Bayt(b) => {
                self.gövdə = Some(b.to_vec());
                self.başlıq_varsa("Content-Type", "application/octet-stream");
            }
            D::S(s) => {
                self.gövdə = Some(s.as_bytes().to_vec());
                self.başlıq_varsa("Content-Type", "text/plain; charset=utf-8");
            }
            D::Boş => self.gövdə = None,
            x => self.json_qoy(i, x)?,
        }
        Ok(())
    }
    fn json_qoy(&mut self, i: &İcraçı, x: &D) -> Nəticə<()> {
        self.gövdə = Some(json_dumps(i, &json_hazırla(x), false, false)?.into_bytes());
        self.başlıq_qoy("Content-Type".into(), "application/json; charset=utf-8".into());
        Ok(())
    }
    fn forma_qoy(&mut self, l: &D) -> Nəticə<()> {
        let c = cütlər(l).ok_or_else(|| xəta("TipXətası", format!("`forma` lüğət gözləyir, `{}` gəlib", tip_adı(l)), "ALQ-T001"))?;
        let c: Vec<(String, String)> = c.iter().map(|(a, d)| (py_s(a), py_s(d))).collect();
        self.gövdə = Some(urlencode(&c).into_bytes());
        self.başlıq_qoy("Content-Type".into(), "application/x-www-form-urlencoded".into());
        Ok(())
    }
    fn vaxt_qoy(&mut self, ms: &D) -> Nəticə<()> {
        self.vaxt = (py_int(ms, "vaxtLimiti")? as f64 / 1000.0).max(0.001);
        Ok(())
    }
    pub fn tam_url(&self) -> String {
        if self.parametrlər.is_empty() {
            return self.url.clone();
        }
        let ay = if self.url.contains('?') { "&" } else { "?" };
        format!("{}{}{}", self.url, ay, urlencode(&self.parametrlər))
    }

    /// Sorğunu göndərir. `hədəf` — gövdə fayla yazılır (irəliləyiş ilə).
    pub fn icra(&self, i: &İcraçı, hədəf: Option<(&Path, Option<&D>)>) -> Nəticə<Cavab> {
        let agent = ureq::AgentBuilder::new()
            .redirects(if self.yönləndir { 10 } else { 0 })
            .timeout_connect(Duration::from_secs_f64(self.vaxt))
            .timeout_read(Duration::from_secs_f64(self.vaxt))
            .timeout_write(Duration::from_secs_f64(self.vaxt))
            .user_agent(İSTİFADƏÇİ_AGENTİ)
            .build();
        let mut r = agent.request(self.metod, &self.tam_url()).set("Accept-Encoding", "identity");
        let mut tip_var = false;
        for (a, d) in &self.başlıqlar {
            if a.eq_ignore_ascii_case("content-type") {
                tip_var = true;
            }
            r = r.set(a, d);
        }
        if self.gövdə.is_some() && !tip_var {
            r = r.set("Content-Type", "application/x-www-form-urlencoded");
        }
        let n = match &self.gövdə {
            Some(b) => r.send_bytes(b),
            None => r.call(),
        };
        let cavab = match n {
            Ok(c) => c,
            Err(ureq::Error::Status(_, c)) => return self.oxu(i, c, None),
            Err(ureq::Error::Transport(t)) => return Err(self.nəqliyyat_xətası(&t)),
        };
        self.oxu(i, cavab, hədəf)
    }

    fn nəqliyyat_xətası(&self, t: &ureq::Transport) -> Siqnal {
        let mətn = t.to_string();
        let io = std::error::Error::source(t).and_then(|e| e.downcast_ref::<std::io::Error>());
        let vaxt = matches!(io.map(|e| e.kind()), Some(std::io::ErrorKind::TimedOut) | Some(std::io::ErrorKind::WouldBlock))
            || mətn.contains("timed out");
        if vaxt {
            return xəta(
                "VaxtBitdiXətası",
                format!("{}: {} s ərzində cavab gəlmədi", self.url, g_format(self.vaxt)),
                "ALQ-R010",
            );
        }
        let səbəb = match t.kind() {
            ureq::ErrorKind::Dns => "[Errno -2] Name or service not known".to_string(),
            ureq::ErrorKind::ConnectionFailed if mətn.contains("refused") => match io.filter(|e| e.raw_os_error().is_some()) {
                Some(e) => super::mod_sebeke::os_xəta_mətni(e),
                None if cfg!(windows) => "[WinError 10061] No connection could be made because the target machine actively refused it".to_string(),
                None => "[Errno 111] Connection refused".to_string(),
            },
            _ if mətn.to_lowercase().contains("certificate") || mətn.contains("tls") || mətn.contains("TLS") => {
                return x_("BağlantıXətası", format!("{}: TLS sertifikatı yoxlanmadı ({})", self.url, mətn));
            }
            _ if mətn.contains("Unexpected EOF") || mətn.contains("closed") => {
                "Remote end closed connection without response".to_string()
            }
            _ => match io {
                Some(e) => e.to_string(),
                None => mətn,
            },
        };
        x_("BağlantıXətası", format!("{}: {}", self.url, səbəb))
    }

    fn oxu(&self, i: &İcraçı, c: ureq::Response, hədəf: Option<(&Path, Option<&D>)>) -> Nəticə<Cavab> {
        let kod = c.status();
        let url = c.get_url().to_string();
        let mut başlıqlar: Vec<(String, String)> = vec![];
        for a in c.headers_names() {
            let a = a.to_lowercase();
            if let Some(v) = c.all(&a).last() {
                if !başlıqlar.iter().any(|(k, _)| *k == a) {
                    başlıqlar.push((a.clone(), v.to_string()));
                }
            }
        }
        let mut oxuyucu = c.into_reader();
        let Some((yol, irəliləyiş)) = hədəf.filter(|_| (200..300).contains(&kod)) else {
            let mut g = vec![];
            if self.metod != "HEAD" {
                oxuyucu.read_to_end(&mut g).map_err(|e| x_("BağlantıXətası", format!("{}: {}", self.url, e)))?;
            }
            return Ok(Cavab { kod, başlıqlar, gövdə: g, url });
        };
        let ümumi: u64 = başlıqlar.iter().find(|(k, _)| k == "content-length").and_then(|(_, v)| v.parse().ok()).unwrap_or(0);
        let ad = yol.file_name().map(|x| x.to_string_lossy().to_string()).unwrap_or_default();
        let müvəqqəti = yol.with_file_name(format!("{}.yüklənir", ad));
        let mut nəticə = (|| -> Nəticə<()> {
            let io = |e: std::io::Error| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009");
            let mut f = std::fs::File::create(&müvəqqəti).map_err(io)?;
            let mut alınan = 0u64;
            let mut son_faiz: i64 = -1;
            let mut blok = vec![0u8; 64 * 1024];
            loop {
                let n = oxuyucu.read(&mut blok).map_err(|e| x_("BağlantıXətası", format!("{}: {}", self.url, e)))?;
                if n == 0 {
                    break;
                }
                f.write_all(&blok[..n]).map_err(io)?;
                alınan += n as u64;
                if let Some(ç) = irəliləyiş {
                    if ümumi > 0 {
                        let faiz = (alınan * 100 / ümumi) as i64;
                        if faiz != son_faiz {
                            son_faiz = faiz;
                            çağır(i, ç, vec![D::T(faiz)])?;
                        }
                    }
                }
            }
            drop(f);
            std::fs::rename(&müvəqqəti, yol).map_err(io)?;
            if let Some(ç) = irəliləyiş {
                if son_faiz != 100 {
                    çağır(i, ç, vec![D::T(100)])?;
                }
            }
            Ok(())
        })();
        if müvəqqəti.exists() {
            let _ = std::fs::remove_file(&müvəqqəti);
        }
        nəticə = nəticə.and(Ok(()));
        nəticə?;
        Ok(Cavab { kod, başlıqlar, gövdə: vec![], url })
    }
}

fn metod_ad_böyük(m: &str) -> Option<&'static str> {
    metod_adı(&m.to_uppercase())
}

fn sorğu_qur(i: &İcraçı, metod: &str, url: &D, adlı: &Adlı, icazəli: &[&str]) -> Nəticə<SorğuV> {
    let mut s = SorğuV::yeni(&D::s(metod), url)?;
    let mut json = None;
    let mut forma = None;
    let mut gövdə = None;
    for (k, d) in adlı {
        match &**k {
            "başlıqlar" => {
                if let Some(c) = cütlər(d) {
                    for (a, v) in c {
                        s.başlıq_qoy(py_s(&a), py_s(&v));
                    }
                }
            }
            "parametrlər" => {
                if let Some(c) = cütlər(d) {
                    for (a, v) in c {
                        s.parametrlər.push((py_s(&a), py_s(&v)));
                    }
                }
            }
            "json" => json = Some(d.clone()),
            "forma" => forma = Some(d.clone()),
            "gövdə" => gövdə = Some(d.clone()),
            "vaxtLimiti" => {
                if !d.boşdur() {
                    s.vaxt_qoy(d)?
                }
            }
            "yönləndir" => s.yönləndir = doğrudur(d),
            x if icazəli.contains(&x) => {}
            x => {
                return Err(xəta("ArqumentXətası", format!("`http` sorğusunun `{}` parametri yoxdur", x), "ALQ-T003"))
            }
        }
    }
    if let Some(j) = json.filter(|x| !x.boşdur()) {
        s.json_qoy(i, &j)?;
    } else if let Some(f) = forma.filter(|x| !x.boşdur()) {
        s.forma_qoy(&f)?;
    } else if let Some(g) = gövdə.filter(|x| !x.boşdur()) {
        s.gövdə_qoy(i, &g)?;
    }
    Ok(s)
}

fn gələcək(s: SorğuV) -> D {
    let ad_ = format!("http {} {}", s.metod, s.url);
    D::Gələcək(Gələcək::yeni(&ad_, move |i| Ok(cavab_obyekti(s.icra(i, None)?))))
}

fn sorğu_obyekti(s: SorğuV) -> D {
    obyekt("httpSorğusu", Rc::new(RefCell::new(s)), |s| format!("<httpSorğusu {} {}>", s.borrow().metod, s.borrow().url), |w, v| {
        vec![
            ("başlıq", metod_ö(w, v, "başlıq", 2, Some(2), |_, s, ö, a, _| {
                s.borrow_mut().başlıq_qoy(py_s(&a[0]), py_s(&a[1]));
                Ok(ö)
            })),
            ("parametr", metod_ö(w, v, "parametr", 2, Some(2), |_, s, ö, a, _| {
                s.borrow_mut().parametrlər.push((py_s(&a[0]), py_s(&a[1])));
                Ok(ö)
            })),
            ("gövdə", metod_ö(w, v, "gövdə", 1, Some(1), |i, s, ö, a, _| {
                s.borrow_mut().gövdə_qoy(i, &a[0])?;
                Ok(ö)
            })),
            ("json", metod_ö(w, v, "json", 1, Some(1), |i, s, ö, a, _| {
                s.borrow_mut().json_qoy(i, &a[0])?;
                Ok(ö)
            })),
            ("forma", metod_ö(w, v, "forma", 1, Some(1), |_, s, ö, a, _| {
                s.borrow_mut().forma_qoy(&a[0])?;
                Ok(ö)
            })),
            ("vaxtLimiti", metod_ö(w, v, "vaxtLimiti", 1, Some(1), |_, s, ö, a, _| {
                s.borrow_mut().vaxt_qoy(&a[0])?;
                Ok(ö)
            })),
            ("göndər", metod(v, "göndər", 0, Some(0), |_, s, _, _| Ok(gələcək(s.borrow().clone())))),
            ("url", metod(v, "url", 0, Some(0), |_, s, _, _| Ok(D::str(s.borrow().tam_url())))),
            ("metod", metod(v, "metod", 0, Some(0), |_, s, _, _| Ok(D::s(s.borrow().metod)))),
        ]
    })
}

fn mime(ad_: &str) -> &'static str {
    super::mod_veb_ortaq::mime_tipi(ad_).unwrap_or("application/octet-stream")
}

fn multipart(yol: &Path, sahə: &str, əlavə: &D) -> Nəticə<(Vec<u8>, String)> {
    let sərhəd = format!("alqor-{}", hex(&təsadüfi_bayt(12)));
    let mut b: Vec<u8> = vec![];
    if let Some(c) = cütlər(əlavə) {
        for (a, d) in c {
            b.extend(format!("--{}\r\nContent-Disposition: form-data; name=\"{}\"\r\n\r\n{}\r\n", sərhəd, py_s(&a), py_s(&d)).as_bytes());
        }
    }
    let ad_ = yol.file_name().map(|x| x.to_string_lossy().to_string()).unwrap_or_default().replace('"', "");
    b.extend(
        format!(
            "--{}\r\nContent-Disposition: form-data; name=\"{}\"; filename*=UTF-8''{}; filename=\"{}\"\r\nContent-Type: {}\r\n\r\n",
            sərhəd,
            sahə,
            quote(&ad_, "/"),
            ad_,
            mime(&ad_)
        )
        .as_bytes(),
    );
    b.extend(std::fs::read(yol).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?);
    b.extend(b"\r\n");
    b.extend(format!("--{}--\r\n", sərhəd).as_bytes());
    Ok((b, format!("multipart/form-data; boundary={}", sərhəd)))
}

pub fn qur() -> Rc<Modul> {
    let m = |ad_: &'static str, metod_: &'static str| {
        f(ad_, 1, Some(1), move |i, a, adlı| Ok(gələcək(sorğu_qur(i, metod_, &a[0], &adlı, &[])?)))
    };
    Modul::yeni("http", vec![
        ("vebSoket", f("vebSoket", 1, Some(2), |_, _, _| {
            Err(xəta("ArqumentXətası", "`http.vebSoket` Rust icraçısında hələ yoxdur — `alqor işlət --motor py` işlədin", "ALQ-M002"))
        })),
        ("al", m("al", "GET")),
        ("göndər", m("göndər", "POST")),
        ("yenilə", m("yenilə", "PUT")),
        ("yamaq", m("yamaq", "PATCH")),
        ("sil", m("sil", "DELETE")),
        ("başlıq", m("başlıq", "HEAD")),
        ("Sorğu", f("Sorğu", 2, Some(2), |_, a, _| Ok(sorğu_obyekti(SorğuV::yeni(&a[0], &a[1])?)))),
        ("faylYüklə", f("faylYüklə", 2, Some(2), |i, a, mut adlı| {
            let irəliləyiş = super::cagiris::adlı_götür(&mut adlı, "irəliləyiş").filter(|x| !x.boşdur());
            let s = sorğu_qur(i, "GET", &a[0], &adlı, &[])?;
            let yol = PathBuf::from(py_s(&a[1]));
            let ad_ = format!("http yüklə {}", py_s(&a[0]));
            Ok(D::Gələcək(Gələcək::yeni(&ad_, move |i| {
                let c = s.icra(i, Some((&yol, irəliləyiş.as_ref())))?;
                c.yoxla()?;
                Ok(cavab_obyekti(c))
            })))
        })),
        ("faylGöndər", f("faylGöndər", 2, Some(2), |i, a, mut adlı| {
            let sahə = super::cagiris::adlı_götür(&mut adlı, "sahə").map(|x| py_s(&x)).unwrap_or("fayl".into());
            let əlavə = super::cagiris::adlı_götür(&mut adlı, "əlavə").unwrap_or(D::Boş);
            let ys = py_s(&a[1]);
            let p = PathBuf::from(&ys);
            if !p.is_file() {
                return Err(xəta("FaylTapılmadıXətası", format!("\"{}\" tapılmadı", ys), "ALQ-R009"));
            }
            let mut s = sorğu_qur(i, "POST", &a[0], &adlı, &[])?;
            let (g, növ) = multipart(&p, &sahə, &əlavə)?;
            s.gövdə = Some(g);
            s.başlıq_qoy("Content-Type".into(), növ);
            Ok(gələcək(s))
        })),
    ])
}
