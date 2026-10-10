//! `alqor-rs` — Alqor-un Rust implementasiyası.
//!
//!     alqor-rs işlət fayl.alq [-- arq…]
//!     alqor-rs tokenlər fayl.alq       (maşın üçün: sətir:sütun NÖV dəyər)
//!     alqor-rs aac fayl.alq [--diaq]   (AAC-nin kanonik çapı; `--diaq`:
//!                                       diaqnostikalar da stdout-a, maşın formatında)

mod aac;
mod aac_yaz;
mod acar;
mod elifba;
mod homoqlif;
mod icraci;
mod lekser;
mod parser;
mod parser_jsx;
mod xeta;

use std::process::ExitCode;
use std::rc::Rc;

fn oxu(yol: &str) -> Result<Rc<xeta::Mənbə>, String> {
    let mətn = std::fs::read(yol).map_err(|e| format!("{yol}: {e}"))?;
    let mətn = String::from_utf8(mətn).map_err(|_| format!("{yol}: UTF-8 deyil"))?;
    Ok(xeta::Mənbə::yeni(yol, &mətn, Some(yol.into())))
}

fn token_yaz(t: &lekser::Token, ç: &mut String) {
    use lekser::Növ::*;
    let n = match t.növ {
        Tam => "TAM", Onluq => "ONLUQ", Mətn => "METN", Simvol => "SIMVOL", Bayt => "BAYT",
        Ad => "AD", Acar => "ACAR", Op => "OP", Jsx => "JSX", SətirSonu => "SETIR_SONU",
        FaylSonu => "FAYL_SONU", Sənəd => "SENED", Direktiv => "DIREKTIV",
    };
    let d = match t.növ {
        Tam => t.tam.as_ref().map(|x| x.to_string()).unwrap_or_default(),
        Onluq => format!("{:?}", t.onluq),
        Bayt => format!("{:?}", t.bayt),
        Mətn => match &t.parçalar {
            Some(p) => p.iter().map(|x| match x {
                lekser::Parça::Mətn(s) => format!("{s:?}"),
                lekser::Parça::Kod(k, f) => format!("{{{} token{}}}", k.len(),
                    f.as_ref().map(|f| format!(":{f}")).unwrap_or_default()),
            }).collect::<Vec<_>>().join("+"),
            None => format!("{:?}", t.s),
        },
        Simvol | Sənəd | Direktiv => format!("{:?}", t.s),
        _ => t.s.clone(),
    };
    ç.push_str(&format!("{}:{} {} {}\n", t.yer.sətir(), t.yer.sütun(), n, d));
}

/// Diaqnostikalar maşın formatında (hesabat sırası ilə).
fn diaq_yaz(x: &xeta::XətaToplayıcı) -> String {
    let açar = |d: &&xeta::Diaqnostika| d.yer.map(|y| (1, y.başlanğıc)).unwrap_or((0, 0));
    let mut v: Vec<&xeta::Diaqnostika> = x.siyahı.iter().filter(|d| d.səviyyə == xeta::Səviyyə::Xəta).collect();
    v.sort_by_key(açar);
    let mut d: Vec<&xeta::Diaqnostika> = x.siyahı.iter().filter(|d| d.səviyyə != xeta::Səviyyə::Xəta).collect();
    d.sort_by_key(açar);
    v.extend(d);
    let mut ç = String::new();
    for d in v {
        let s = if d.səviyyə == xeta::Səviyyə::Xəta { "xəta" } else { "xəbərdarlıq" };
        let yer = d.yer.map(|y| format!("{}:{}+{}", y.sətir(), y.sütun(), y.uzunluq)).unwrap_or("-".into());
        let k: Vec<String> = d.köməklər.iter().map(|k| aac_yaz::q(k)).collect();
        ç.push_str(&format!("{} {} {} {} qeyd={} köməklər=[{}]\n", s, d.kod, yer, aac_yaz::q(&d.mesaj),
                            aac_yaz::q(&d.qeyd), k.join(", ")));
    }
    ç
}

fn main() -> ExitCode {
    let a: Vec<String> = std::env::args().skip(1).collect();
    let əmr = a.first().map(String::as_str).unwrap_or("kömək");
    match əmr {
        "tokenlər" | "tokenler" if a.len() >= 2 => {
            let m = match oxu(&a[1]) { Ok(m) => m, Err(e) => { eprintln!("xəta: {e}"); return ExitCode::from(4); } };
            let mut x = xeta::XətaToplayıcı::yeni();
            let t = lekser::Lekser::yeni(m, &mut x).leksə();
            let mut ç = String::new();
            for k in &t { token_yaz(k, &mut ç); }
            print!("{ç}");
            if !x.uğurludur() { eprint!("{}", x.hesabat(Some(false))); return ExitCode::from(2); }
            ExitCode::SUCCESS
        }
        "aac" if a.len() >= 2 => {
            let m = match oxu(&a[1]) { Ok(m) => m, Err(e) => { eprintln!("xəta: {e}"); return ExitCode::from(4); } };
            let mut x = xeta::XətaToplayıcı::yeni();
            let p = parser::ayır(m, &mut x);
            let mut ç = aac_yaz::çap(&p);
            if a.iter().any(|s| s == "--diaq") {
                ç.push_str("## diaqnostika\n");
                ç.push_str(&diaq_yaz(&x));
            }
            print!("{ç}");
            if !x.siyahı.is_empty() { eprintln!("{}", x.hesabat(None)); }
            if !x.uğurludur() { return ExitCode::from(2); }
            ExitCode::SUCCESS
        }
        "işlət" | "islet" | "run" if a.len() >= 2 => işlət(&a[1..]),
        "versiya" | "--versiya" => { println!("alqor-rs {}", env!("CARGO_PKG_VERSION")); ExitCode::SUCCESS }
        _ => {
            println!("istifadə: alqor-rs tokenlər <fayl> | alqor-rs aac <fayl> [--diaq]");
            ExitCode::from(3)
        }
    }
}

/// `alqor-rs işlət fayl.alq [-- arq…]` — Python `alqor işlət` ilə eyni davranış.
fn işlət(a: &[String]) -> ExitCode {
    let a = a.to_vec();
    // Dərin rekursiya üçün böyük stek; mənbə reyestri sap-yerlidir
    let sap = std::thread::Builder::new().stack_size(1 << 30).spawn(move || işlət_sapda(&a));
    let k = match sap {
        Ok(s) => s.join().unwrap_or(101),
        Err(_) => 101,
    };
    ExitCode::from((k & 0xff) as u8)
}

fn işlət_sapda(a: &[String]) -> i32 {
    let (öz, arqumentlər): (Vec<String>, Vec<String>) = match a.iter().position(|x| x == "--") {
        Some(k) => (a[..k].to_vec(), a[k + 1..].to_vec()),
        None => (a.to_vec(), vec![]),
    };
    let Some(yol) = öz.iter().find(|x| !x.starts_with("--") || *x == "-").cloned() else {
        eprintln!("xəta: `işlət` əmri üçün fayl adı lazımdır");
        return 3;
    };
    let m = if yol == "-" {
        let mut s = String::new();
        let _ = std::io::Read::read_to_string(&mut std::io::stdin(), &mut s);
        xeta::Mənbə::yeni("<stdin>", &s, None)
    } else {
        match oxu(&yol) {
            Ok(m) => m,
            Err(e) => {
                eprintln!("✖ {e}");
                return 4;
            }
        }
    };
    let mut x = xeta::XətaToplayıcı::yeni();
    let ağac = parser::ayır(m, &mut x);
    if !x.uğurludur() {
        x.çap();
        return 2;
    }
    if !x.siyahı.is_empty() {
        x.çap();
    }
    let ağac: &'static aac::Proqram = Box::leak(Box::new(ağac));
    let i = icraci::İcraçı::yeni();
    if yol != "-" {
        *i.əsas_qovluq.borrow_mut() = std::fs::canonicalize(&yol).ok().and_then(|p| p.parent().map(|p| p.to_path_buf()));
    }
    match i.işlət(&ağac.gövdə, arqumentlər) {
        Ok(k) => k,
        Err(x) => {
            i.boşalt();
            let d = xeta::Diaqnostika {
                kod: if x.kod.is_empty() { "ALQ-R000".into() } else { x.kod.clone() },
                mesaj: format!("{}: {}", x.tip, x.mesaj),
                yer: x.yer,
                səviyyə: xeta::Səviyyə::Xəta,
                qeyd: if x.yer.is_some() { "burada baş verdi".into() } else { String::new() },
                köməklər: vec![],
            };
            eprintln!("{}", d.formatla(None));
            1
        }
    }
}
