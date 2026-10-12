//! Alqor dilinin Rust implementasiyası: lekser, parser, icraçı.
//!
//! `işlət_mətn` — mənbə mətnini icra edib (stdout, stderr, çıxış kodu)
//! qaytarır; `wasm32` hədəfində JS-ə ixrac olunur (`wasm` modulu).

pub mod aac;
pub mod aac_yaz;
pub mod acar;
pub mod elifba;
pub mod homoqlif;
pub mod icraci;
pub mod lekser;
pub mod parser;
pub mod parser_jsx;
pub mod xeta;

#[cfg(target_arch = "wasm32")]
pub mod wasm;

/// İcra nəticəsi
pub struct Nəticə {
    pub stdout: String,
    pub stderr: String,
    pub kod: i32,
}

/// Mənbəni yaddaşda icra edir (fayl sistemi və terminal tələb etmir).
/// `giriş` — `oxu()` üçün sətirlər, `arqumentlər` — `sistem.arqumentlər()`.
pub fn işlət_mətn(ad: &str, mənbə: &str, giriş: &[String], arqumentlər: Vec<String>) -> Nəticə {
    let m = xeta::Mənbə::yeni(ad, mənbə, None);
    let mut x = xeta::XətaToplayıcı::yeni();
    let ağac = parser::ayır(m, &mut x);
    let mut stderr = String::new();
    if !x.uğurludur() {
        stderr.push_str(&x.çap_mətni(false));
        return Nəticə { stdout: String::new(), stderr, kod: 2 };
    }
    if !x.siyahı.is_empty() {
        stderr.push_str(&x.çap_mətni(false));
    }
    let ağac: &'static aac::Proqram = Box::leak(Box::new(ağac));
    let i = icraci::İcraçı::yeni();
    *i.çıxış.borrow_mut() = icraci::icraci::Çıxış::Mətn(String::new());
    *i.giriş_növbəsi.borrow_mut() = Some(giriş.iter().cloned().collect());
    *i.giriş_sonlu.borrow_mut() = true;
    *i.xəta_çıxışı.borrow_mut() = Some(String::new());
    let kod = match i.işlət(&ağac.gövdə, arqumentlər) {
        Ok(k) => k,
        Err(e) => {
            let d = xeta::Diaqnostika {
                kod: if e.kod.is_empty() { "ALQ-R000".into() } else { e.kod.clone() },
                mesaj: format!("{}: {}", e.tip, e.mesaj),
                yer: e.yer,
                səviyyə: xeta::Səviyyə::Xəta,
                qeyd: if e.yer.is_some() { "burada baş verdi".into() } else { String::new() },
                köməklər: vec![],
            };
            if let Some(s) = &mut *i.xəta_çıxışı.borrow_mut() {
                s.push_str(&d.formatla(Some(false)));
                s.push('\n');
            }
            1
        }
    };
    let stdout = match std::mem::replace(&mut *i.çıxış.borrow_mut(), icraci::icraci::Çıxış::Mətn(String::new())) {
        icraci::icraci::Çıxış::Mətn(s) => s,
        _ => String::new(),
    };
    stderr.push_str(&i.xəta_çıxışı.borrow_mut().take().unwrap_or_default());
    Nəticə { stdout, stderr, kod }
}
