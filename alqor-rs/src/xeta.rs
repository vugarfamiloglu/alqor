//! Mənbə faylları, mövqelər və diaqnostika (Python: menbe.py, xeta.py).

use std::cell::RefCell;
use std::collections::HashSet;
use std::rc::Rc;

/// Hazırlanmış mənbə mətni + sətir xəritəsi.
pub struct Mənbə {
    pub ad: String,
    pub yol: Option<std::path::PathBuf>,
    pub mətn: Vec<char>,
    sətir_başları: Vec<usize>,
}

impl Mənbə {
    pub fn yeni(ad: &str, mətn: &str, yol: Option<std::path::PathBuf>) -> Rc<Mənbə> {
        let hazır = hazırla(mətn);
        let mətn: Vec<char> = hazır.chars().collect();
        let mut başlar = vec![0];
        for (i, c) in mətn.iter().enumerate() {
            if *c == '\n' {
                başlar.push(i + 1);
            }
        }
        let m = Rc::new(Mənbə { ad: ad.to_string(), yol, mətn, sətir_başları: başlar });
        MƏNBƏLƏR.with(|q| q.borrow_mut().push(m.clone()));
        m
    }

    pub fn sətir_sütun(&self, mövqe: usize) -> (usize, usize) {
        let mövqe = mövqe.min(self.mətn.len());
        let i = match self.sətir_başları.binary_search(&mövqe) {
            Ok(i) => i,
            Err(i) => i - 1,
        };
        (i + 1, mövqe - self.sətir_başları[i] + 1)
    }

    pub fn sətir_mətni(&self, sətir: usize) -> String {
        if sətir < 1 || sətir > self.sətir_başları.len() {
            return String::new();
        }
        let b = self.sətir_başları[sətir - 1];
        let s = if sətir < self.sətir_başları.len() {
            self.sətir_başları[sətir] - 1
        } else {
            self.mətn.len()
        };
        let s: String = self.mətn[b..s.max(b)].iter().collect();
        s.trim_end_matches('\n').to_string()
    }

    pub fn parça(&self, b: usize, s: usize) -> String {
        self.mətn[b.min(self.mətn.len())..s.min(self.mətn.len())].iter().collect()
    }
}

thread_local! {
    static MƏNBƏLƏR: RefCell<Vec<Rc<Mənbə>>> = RefCell::new(Vec::new());
}

/// BOM, NFC, sətir sonları, homoqliflər (sadələşdirilmiş).
fn hazırla(mətn: &str) -> String {
    use unicode_normalization::UnicodeNormalization;
    let mut m = mətn.strip_prefix('\u{feff}').unwrap_or(mətn).to_string();
    if !unicode_normalization::is_nfc(&m) {
        m = m.nfc().collect();
    }
    if m.contains('\r') {
        m = m.replace("\r\n", "\n").replace('\r', "\n");
    }
    if homoqlif_söndürülüb(&m) {
        return m;
    }
    homoqlif_düzəlt(&m)
}

fn homoqlif_söndürülüb(m: &str) -> bool {
    for sətir in m.lines() {
        if let Some(i) = sətir.find("alqor:") {
            let s = sətir[i..].replace('ə', "e").replace('ö', "o").replace('ü', "u").replace('ğ', "g");
            if s.contains("homoqlif") && s.contains("sondur") {
                return true;
            }
        }
    }
    false
}

/// Azərbaycan hərflərinə oxşar yad simvolları düzəldir (ä → ə və s.).
fn homoqlif_düzəlt(m: &str) -> String {
    let mut n = String::with_capacity(m.len());
    for c in m.chars() {
        match crate::homoqlif::homoqlif_əvəz(c) {
            Some(e) => n.push_str(e),
            None => n.push(c),
        }
    }
    n
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Yer {
    pub mənbə: u32,
    pub başlanğıc: u32,
    pub uzunluq: u32,
}

impl Yer {
    pub fn mənbə(&self) -> Option<Rc<Mənbə>> {
        MƏNBƏLƏR.with(|q| q.borrow().get(self.mənbə as usize).cloned())
    }
    pub fn son(&self) -> u32 {
        self.başlanğıc + self.uzunluq
    }
    pub fn sətir(&self) -> usize {
        self.mənbə().map(|m| m.sətir_sütun(self.başlanğıc as usize).0).unwrap_or(0)
    }
    pub fn sütun(&self) -> usize {
        self.mənbə().map(|m| m.sətir_sütun(self.başlanğıc as usize).1).unwrap_or(0)
    }
    pub fn göstər(&self) -> String {
        match self.mənbə() {
            Some(m) => {
                let (s, st) = m.sətir_sütun(self.başlanğıc as usize);
                format!("{}:{}:{}", m.ad, s, st)
            }
            None => "?".into(),
        }
    }
}

pub fn mənbə_id(m: &Rc<Mənbə>) -> u32 {
    MƏNBƏLƏR.with(|q| {
        q.borrow().iter().position(|x| Rc::ptr_eq(x, m)).unwrap_or(0) as u32
    })
}

// ═══════════════════════════════════════════════════════════════════════
//  Diaqnostika
// ═══════════════════════════════════════════════════════════════════════

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Səviyyə {
    Xəta,
    Xəbərdarlıq,
}

#[derive(Clone, Debug)]
pub struct Diaqnostika {
    pub kod: String,
    pub mesaj: String,
    pub yer: Option<Yer>,
    pub səviyyə: Səviyyə,
    pub qeyd: String,
    pub köməklər: Vec<String>,
}

fn rəngli() -> bool {
    match std::env::var("ALQOR_RENG").unwrap_or_default().to_lowercase().as_str() {
        "həmişə" | "hemise" | "always" | "1" => true,
        "heçvaxt" | "hecvaxt" | "never" | "0" => false,
        _ => {
            if std::env::var("NO_COLOR").is_ok() {
                return false;
            }
            use std::io::IsTerminal;
            std::io::stderr().is_terminal()
        }
    }
}

fn boya(m: &str, kod: &str, aktiv: bool) -> String {
    if aktiv {
        format!("\x1b[{}m{}\x1b[0m", kod, m)
    } else {
        m.to_string()
    }
}

impl Diaqnostika {
    pub fn formatla(&self, r: Option<bool>) -> String {
        let r = r.unwrap_or_else(rəngli);
        let (işarə, rəng) = match self.səviyyə {
            Səviyyə::Xəta => ("✖", "31"),
            Səviyyə::Xəbərdarlıq => ("⚠", "33"),
        };
        let mut s = vec![format!(
            "{}  {}",
            boya(&format!("{} {}", işarə, self.kod), rəng, r),
            boya(&self.mesaj, "1", r)
        )];
        if let Some(y) = self.yer {
            if let Some(m) = y.mənbə() {
                let (sn, sütun) = m.sətir_sütun(y.başlanğıc as usize);
                let (mətn, sütun) = tab_aç(&m.sətir_mətni(sn), sütun);
                let w = sn.to_string().chars().count();
                let boş = " ".repeat(w);
                let düz = boya("│", "90", r);
                let uz = (y.uzunluq as usize).max(1);
                let qalan = (mətn.chars().count() as i64 - (sütun as i64 - 1)).max(1) as usize;
                let uz = uz.min(qalan);
                let mut xətt = " ".repeat(sütun - 1) + &boya(&"^".repeat(uz), rəng, r);
                if !self.qeyd.is_empty() {
                    xətt += &format!(" {}", boya(&self.qeyd, rəng, r));
                }
                s.push(format!("  {}{} {}", boş, boya("┌─", "90", r), boya(&y.göstər(), "1", r)));
                s.push(format!("  {}{}", boş, düz));
                s.push(format!("  {}{} {}", boya(&sn.to_string(), "90", r), düz, mətn));
                s.push(format!("  {}{} {}", boş, düz, xətt));
                s.push(format!("  {}{}", boş, düz));
            }
        }
        for k in &self.köməklər {
            s.push(format!("  {} {}", boya("= kömək:", "90", r), k));
        }
        s.push(format!("  {} alqor.vuqar.pro/xeta/{}", boya("= sənəd:", "90", r), self.kod));
        s.join("\n")
    }
}

fn tab_aç(m: &str, sütun: usize) -> (String, usize) {
    if !m.contains('\t') {
        return (m.to_string(), sütun);
    }
    let mut n = String::new();
    let mut uz = 0;
    let mut yeni = sütun;
    for (i, c) in m.chars().enumerate() {
        if c == '\t' {
            let əlavə = 4 - (uz % 4);
            n.push_str(&" ".repeat(əlavə));
            uz += əlavə;
            if i + 1 < sütun {
                yeni += əlavə - 1;
            }
        } else {
            n.push(c);
            uz += 1;
        }
    }
    (n, yeni)
}

#[derive(Default)]
pub struct XətaToplayıcı {
    pub siyahı: Vec<Diaqnostika>,
    söndürülmüş: HashSet<String>,
    görülənlər: HashSet<String>,
    təkrar: usize,
}

impl XətaToplayıcı {
    pub fn yeni() -> Self {
        Self::default()
    }
    pub fn söndür(&mut self, kod: &str) {
        self.söndürülmüş.insert(kod.to_string());
    }
    pub fn əlavə(&mut self, d: Diaqnostika) {
        if self.söndürülmüş.contains(&d.kod) {
            return;
        }
        let açar = format!("{}|{}|{}|{:?}|{:?}", d.kod, d.mesaj, d.qeyd, d.səviyyə,
                           d.yer.map(|y| (y.mənbə, y.başlanğıc)));
        if self.görülənlər.contains(&açar) {
            if d.səviyyə == Səviyyə::Xəta {
                self.təkrar += 1;
            }
            return;
        }
        self.görülənlər.insert(açar);
        self.siyahı.push(d);
    }
    pub fn xəta(&mut self, kod: &str, mesaj: &str, yer: Option<Yer>, qeyd: &str, köməklər: &[&str]) {
        self.əlavə(Diaqnostika {
            kod: kod.into(),
            mesaj: mesaj.into(),
            yer,
            səviyyə: Səviyyə::Xəta,
            qeyd: qeyd.into(),
            köməklər: köməklər.iter().map(|s| s.to_string()).collect(),
        });
    }
    pub fn xəbərdarlıq(&mut self, kod: &str, mesaj: &str, yer: Option<Yer>, qeyd: &str, köməklər: &[&str]) {
        self.əlavə(Diaqnostika {
            kod: kod.into(),
            mesaj: mesaj.into(),
            yer,
            səviyyə: Səviyyə::Xəbərdarlıq,
            qeyd: qeyd.into(),
            köməklər: köməklər.iter().map(|s| s.to_string()).collect(),
        });
    }
    pub fn xəta_sayı(&self) -> usize {
        self.siyahı.iter().filter(|d| d.səviyyə == Səviyyə::Xəta).count()
    }
    pub fn uğurludur(&self) -> bool {
        self.xəta_sayı() == 0
    }
    pub fn dolubmu(&self) -> bool {
        self.xəta_sayı() + self.təkrar >= 100
    }
    pub fn hesabat(&self, r: Option<bool>) -> String {
        let açar = |d: &&Diaqnostika| d.yer.map(|y| (1, y.başlanğıc)).unwrap_or((0, 0));
        let mut x: Vec<&Diaqnostika> = self.siyahı.iter().filter(|d| d.səviyyə == Səviyyə::Xəta).collect();
        x.sort_by_key(açar);
        let mut d: Vec<&Diaqnostika> = self.siyahı.iter().filter(|d| d.səviyyə != Səviyyə::Xəta).collect();
        d.sort_by_key(açar);
        x.extend(d);
        x.iter().map(|d| d.formatla(r)).collect::<Vec<_>>().join("\n\n")
    }
    pub fn çap(&self) {
        let r = rəngli();
        let h = self.hesabat(Some(r));
        if !h.is_empty() {
            eprintln!("{}\n", h);
        }
        let x = self.xəta_sayı();
        let xb = self.siyahı.len() - x;
        if x == 0 && xb == 0 {
            eprintln!("{}", boya("✓ Xəta yoxdur", "32", r));
            return;
        }
        let mut h = vec![];
        if x > 0 {
            h.push(boya(&format!("{} xəta", x), "31", r));
        }
        if xb > 0 {
            h.push(boya(&format!("{} xəbərdarlıq", xb), "33", r));
        }
        eprintln!("{}", h.join(", "));
    }
}
