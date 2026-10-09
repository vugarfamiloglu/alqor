//! `alqor-rs` — Alqor-un Rust implementasiyası.
//!
//!     alqor-rs işlət fayl.alq [-- arq…]
//!     alqor-rs tokenlər fayl.alq       (maşın üçün: sətir:sütun NÖV dəyər)

mod aac;
mod acar;
mod elifba;
mod homoqlif;
mod lekser;
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
        "versiya" | "--versiya" => { println!("alqor-rs {}", env!("CARGO_PKG_VERSION")); ExitCode::SUCCESS }
        _ => {
            println!("istifadə: alqor-rs tokenlər <fayl>");
            ExitCode::from(3)
        }
    }
}
