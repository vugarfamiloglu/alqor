//! Platformadan asılı köməkçilər: vaxt, terminal, mühit.
//! `wasm32` hədəfində (brauzer) vaxt JS-dən gəlir, terminal/fayl yoxdur.

#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "alqor")]
extern "C" {
    /// JS: `Date.now()` (ms)
    fn alqor_indi_ms() -> f64;
    /// JS: `performance.now()` (ms)
    fn alqor_monoton_ms() -> f64;
    /// JS: yerli saat qurşağı sürüşməsi (dəqiqə, `-new Date().getTimezoneOffset()`)
    fn alqor_qursaq_deq() -> f64;
}

/// UNIX vaxtı (saniyə)
pub fn indi_san() -> f64 {
    #[cfg(target_arch = "wasm32")]
    unsafe {
        alqor_indi_ms() / 1000.0
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
    }
}

/// Monoton saat (saniyə)
pub fn monoton_san() -> f64 {
    #[cfg(target_arch = "wasm32")]
    unsafe {
        alqor_monoton_ms() / 1000.0
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        use std::sync::OnceLock;
        static B: OnceLock<std::time::Instant> = OnceLock::new();
        B.get_or_init(std::time::Instant::now).elapsed().as_secs_f64()
    }
}

/// Təsadüfi toxum üçün entropiya
pub fn entropiya() -> u128 {
    let t = (indi_san() * 1e9) as u128;
    #[cfg(not(target_arch = "wasm32"))]
    {
        t ^ ((std::process::id() as u128) << 64)
    }
    #[cfg(target_arch = "wasm32")]
    {
        t ^ ((monoton_san() * 1e6) as u128) << 64
    }
}

/// (il, ay, gün, saat, dəqiqə, saniyə, həftə günü: 0 = bazar ertəsi)
pub fn yerli_vaxt(t: i64) -> (i32, u32, u32, u32, u32, u32, u32) {
    #[cfg(not(target_arch = "wasm32"))]
    {
        let t = t as libc::time_t;
        let mut tm: libc::tm = unsafe { std::mem::zeroed() };
        #[cfg(unix)]
        unsafe {
            libc::localtime_r(&t, &mut tm);
        }
        #[cfg(windows)]
        unsafe {
            libc::localtime_s(&mut tm, &t);
        }
        (
            tm.tm_year + 1900,
            (tm.tm_mon + 1) as u32,
            tm.tm_mday as u32,
            tm.tm_hour as u32,
            tm.tm_min as u32,
            tm.tm_sec as u32,
            ((tm.tm_wday + 6) % 7) as u32,
        )
    }
    #[cfg(target_arch = "wasm32")]
    {
        let t = t + unsafe { alqor_qursaq_deq() } as i64 * 60;
        mülki(t)
    }
}

/// UNIX vaxtından təqvim (UTC) — Howard Hinnant alqoritmi
#[allow(dead_code)]
pub fn mülki(t: i64) -> (i32, u32, u32, u32, u32, u32, u32) {
    let gün = t.div_euclid(86400);
    let s = t.rem_euclid(86400);
    let z = gün + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    // 1970-01-01 cümə axşamı idi (bazar ertəsi = 0 → 3)
    let hg = (gün + 3).rem_euclid(7);
    (y as i32, m as u32, d as u32, (s / 3600) as u32, (s % 3600 / 60) as u32, (s % 60) as u32, hg as u32)
}

pub fn terminaldır() -> bool {
    #[cfg(not(target_arch = "wasm32"))]
    unsafe {
        libc::isatty(1) == 1
    }
    #[cfg(target_arch = "wasm32")]
    false
}

pub fn terminal_ölçüsü() -> Option<(i64, i64)> {
    #[cfg(unix)]
    {
        let mut w: libc::winsize = unsafe { std::mem::zeroed() };
        if unsafe { libc::ioctl(1, libc::TIOCGWINSZ, &mut w) } == 0 && w.ws_col > 0 {
            return Some((w.ws_col as i64, w.ws_row as i64));
        }
        None
    }
    #[cfg(not(unix))]
    {
        let ədəd = |a: &str| std::env::var(a).ok().and_then(|v| v.trim().parse::<i64>().ok());
        match (ədəd("COLUMNS"), ədəd("LINES")) {
            (Some(e), Some(h)) if e > 0 => Some((e, h)),
            _ => None,
        }
    }
}

pub fn host_adı() -> String {
    #[cfg(windows)]
    {
        std::env::var("COMPUTERNAME").unwrap_or_else(|_| "localhost".into())
    }
    #[cfg(unix)]
    {
        let mut b = [0u8; 256];
        unsafe {
            libc::gethostname(b.as_mut_ptr() as *mut libc::c_char, b.len());
        }
        let n = b.iter().position(|x| *x == 0).unwrap_or(0);
        String::from_utf8_lossy(&b[..n]).to_string()
    }
    #[cfg(target_arch = "wasm32")]
    "localhost".into()
}

pub fn yat(ms: f64) {
    #[cfg(not(target_arch = "wasm32"))]
    if ms > 0.0 {
        std::thread::sleep(std::time::Duration::from_secs_f64(ms / 1000.0));
    }
    #[cfg(target_arch = "wasm32")]
    let _ = ms;
}

pub fn mühit_qoy(a: &str, d: &str) {
    #[cfg(not(target_arch = "wasm32"))]
    std::env::set_var(a, d);
    #[cfg(target_arch = "wasm32")]
    let _ = (a, d);
}
