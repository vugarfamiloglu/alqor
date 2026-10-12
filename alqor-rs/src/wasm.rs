//! WebAssembly ixracları (`wasm32-unknown-unknown`, asılılıqsız C ABI).
//!
//! JS tərəfi (bax: `wasm/alqor.js`):
//!   1. `alqor_ayir(n)` ilə yaddaş ayırıb mənbəni və girişi (UTF-8) yazır;
//!   2. `alqor_islet(m, mn, g, gn)` çağırır — nəticə JSON-un göstəricisi;
//!   3. `alqor_netice_uzunlugu()` ilə uzunluğu oxuyur, `alqor_azad` ilə
//!      yaddaşı qaytarır.
//!
//! Nəticə: `{"stdout": "...", "stderr": "...", "kod": 0}`.

use std::cell::RefCell;

thread_local! {
    static NƏTİCƏ: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
}

#[export_name = "alqor_ayir"]
pub extern "C" fn ayır(n: usize) -> *mut u8 {
    let mut v = Vec::<u8>::with_capacity(n.max(1));
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}

/// # Safety
/// `p` `alqor_ayir(n)` ilə ayrılmış olmalıdır.
#[export_name = "alqor_azad"]
pub unsafe extern "C" fn azad(p: *mut u8, n: usize) {
    drop(Vec::from_raw_parts(p, 0, n.max(1)));
}

unsafe fn mətn(p: *const u8, n: usize) -> String {
    if n == 0 {
        return String::new();
    }
    String::from_utf8_lossy(std::slice::from_raw_parts(p, n)).into_owned()
}

fn json_mətn(s: &str, ç: &mut String) {
    ç.push('"');
    for c in s.chars() {
        match c {
            '"' => ç.push_str("\\\""),
            '\\' => ç.push_str("\\\\"),
            '\n' => ç.push_str("\\n"),
            '\r' => ç.push_str("\\r"),
            '\t' => ç.push_str("\\t"),
            c if (c as u32) < 0x20 => ç.push_str(&format!("\\u{:04x}", c as u32)),
            c => ç.push(c),
        }
    }
    ç.push('"');
}

/// Mənbəni icra edir. `giriş` — `\n` ilə ayrılmış sətirlər (`oxu()` üçün).
///
/// # Safety
/// Göstəricilər etibarlı UTF-8 bufer olmalıdır.
#[export_name = "alqor_islet"]
pub unsafe extern "C" fn işlət(m: *const u8, mn: usize, g: *const u8, gn: usize) -> *const u8 {
    let mənbə = mətn(m, mn);
    let giriş = mətn(g, gn);
    let mut sətirlər: Vec<String> = giriş.split('\n').map(|s| s.trim_end_matches('\r').to_string()).collect();
    if giriş.ends_with('\n') || giriş.is_empty() {
        sətirlər.pop();
    }
    let n = crate::işlət_mətn("proqram.alq", &mənbə, &sətirlər, vec![]);
    let mut ç = String::from("{\"stdout\": ");
    json_mətn(&n.stdout, &mut ç);
    ç.push_str(", \"stderr\": ");
    json_mətn(&n.stderr, &mut ç);
    ç.push_str(&format!(", \"kod\": {}}}", n.kod));
    NƏTİCƏ.with(|r| {
        *r.borrow_mut() = ç.into_bytes();
        r.borrow().as_ptr()
    })
}

#[export_name = "alqor_netice_uzunlugu"]
pub extern "C" fn nəticə_uzunluğu() -> usize {
    NƏTİCƏ.with(|r| r.borrow().len())
}

/// Versiya mətni (`alqor_netice_uzunlugu` ilə oxunur)
#[export_name = "alqor_versiya"]
pub extern "C" fn versiya() -> *const u8 {
    NƏTİCƏ.with(|r| {
        *r.borrow_mut() = env!("CARGO_PKG_VERSION").as_bytes().to_vec();
        r.borrow().as_ptr()
    })
}
