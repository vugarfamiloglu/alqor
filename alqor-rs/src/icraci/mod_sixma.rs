//! `sıxma` — gzip, zlib, zip, tar (modullar/sixma.py).
//!
//! Deflate: `miniz_oxide` (saf Rust). Açılan məlumat Python ilə eynidir;
//! sıxılmış baytlar isə zlib-dən fərqli ola bilər (eyni dərəcədə
//! etibarlıdır, hər iki tərəf bir-birininkini açır).

use super::deyerler::*;
use super::elave::*;
use std::path::{Path, PathBuf};
use std::rc::Rc;

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("SıxmaXətası", m, "ALQ-R005")
}

fn tapılmadı(y: &str) -> Siqnal {
    xəta("FaylTapılmadıXətası", format!("\"{}\" tapılmadı", y), "ALQ-R009")
}

// ── deflate / gzip / zlib ──────────────────────────────────────────────

pub fn deflate(b: &[u8], s: u8) -> Vec<u8> {
    miniz_oxide::deflate::compress_to_vec(b, s.min(10))
}

pub fn gzip_sıx(b: &[u8], s: i64) -> Vec<u8> {
    let s = if s < 0 { 6 } else { s.min(9) as u8 };
    let xfl = if s == 9 { 2 } else if s == 1 { 4 } else { 0 };
    let mut n = vec![0x1f, 0x8b, 8, 0, 0, 0, 0, 0, xfl, 255];
    n.extend(deflate(b, s));
    n.extend(crc32(b).to_le_bytes());
    n.extend((b.len() as u32).to_le_bytes());
    n
}

/// Xam deflate axını: (açılmış, işlənən bayt sayı)
pub fn inflate_xam(b: &[u8]) -> Result<(Vec<u8>, usize), String> {
    use miniz_oxide::inflate::stream::{inflate, InflateState};
    use miniz_oxide::{DataFormat, MZError, MZFlush, MZStatus};
    let mut st = InflateState::new_boxed(DataFormat::Raw);
    let mut ç = vec![0u8; (b.len() * 4).max(1024)];
    let mut yazılan = 0;
    let mut oxunan = 0;
    loop {
        let r = inflate(&mut st, &b[oxunan..], &mut ç[yazılan..], MZFlush::None);
        oxunan += r.bytes_consumed;
        yazılan += r.bytes_written;
        match r.status {
            Ok(MZStatus::StreamEnd) => {
                ç.truncate(yazılan);
                return Ok((ç, oxunan));
            }
            Ok(_) | Err(MZError::Buf) => {
                if yazılan == ç.len() {
                    ç.resize(ç.len() * 2, 0);
                } else if oxunan >= b.len() {
                    return Err("Compressed file ended before the end-of-stream marker was reached".into());
                } else if r.bytes_consumed == 0 && r.bytes_written == 0 {
                    return Err("invalid data".into());
                }
            }
            Err(_) => return Err("invalid block type".into()),
        }
    }
}

fn py_bayt_repr(b: &[u8]) -> String {
    py_repr(&D::Bayt(Rc::new(b.to_vec())))
}

pub fn gzip_aç_xam(b: &[u8]) -> Result<Vec<u8>, String> {
    let mut n = vec![];
    let mut k = 0;
    let mut ilk = true;
    while k < b.len() {
        let q = &b[k..];
        if q.len() < 2 || q[0] != 0x1f || q[1] != 0x8b {
            if !ilk && q.iter().all(|x| *x == 0) {
                break;
            }
            return Err(format!("Not a gzipped file ({})", py_bayt_repr(&q[..q.len().min(2)])));
        }
        if q.len() < 10 {
            return Err("Compressed file ended before the end-of-stream marker was reached".into());
        }
        if q[2] != 8 {
            return Err("Unknown compression method".into());
        }
        let fl = q[3];
        let mut p = 10;
        let son = || "Compressed file ended before the end-of-stream marker was reached".to_string();
        if fl & 4 != 0 {
            if q.len() < p + 2 {
                return Err(son());
            }
            p += 2 + u16::from_le_bytes([q[p], q[p + 1]]) as usize;
        }
        for bayraq in [8u8, 16] {
            if fl & bayraq != 0 {
                while p < q.len() && q[p] != 0 {
                    p += 1;
                }
                p += 1;
            }
        }
        if fl & 2 != 0 {
            p += 2;
        }
        if p > q.len() {
            return Err(son());
        }
        let (a, oxunan) = inflate_xam(&q[p..])?;
        p += oxunan;
        if q.len() < p + 8 {
            return Err(son());
        }
        let crc = u32::from_le_bytes([q[p], q[p + 1], q[p + 2], q[p + 3]]);
        let ölçü = u32::from_le_bytes([q[p + 4], q[p + 5], q[p + 6], q[p + 7]]);
        if crc != crc32(&a) {
            return Err(format!("CRC check failed {:#x} != {:#x}", crc, crc32(&a)));
        }
        if ölçü != a.len() as u32 {
            return Err("Incorrect length of data produced".into());
        }
        n.extend(a);
        k += p + 8;
        ilk = false;
    }
    Ok(n)
}

pub fn gzip_aç(b: &[u8]) -> Nəticə<Vec<u8>> {
    gzip_aç_xam(b).map_err(|e| x_(format!("gzip məlumatı pozulub: {}", e)))
}

pub fn zlib_sıx(b: &[u8], s: i64) -> Vec<u8> {
    let s = if s < 0 { 6 } else { s.min(9) as u8 };
    miniz_oxide::deflate::compress_to_vec_zlib(b, s)
}

pub fn zlib_aç(b: &[u8]) -> Nəticə<Vec<u8>> {
    let e = |m: &str| x_(format!("zlib məlumatı pozulub: Error -3 while decompressing data: {}", m));
    if b.len() < 2 || b[0] & 0x0f != 8 || ((b[0] as u16) << 8 | b[1] as u16) % 31 != 0 {
        if b.len() < 2 {
            return Err(x_("zlib məlumatı pozulub: Error -5 while decompressing data: incomplete or truncated stream"));
        }
        return Err(e("incorrect header check"));
    }
    match inflate_xam(&b[2..]) {
        Ok((a, _)) => Ok(a),
        Err(m) if m.starts_with("Compressed") => {
            Err(x_("zlib məlumatı pozulub: Error -5 while decompressing data: incomplete or truncated stream"))
        }
        Err(m) => Err(e(&m)),
    }
}

// ── Yollar ─────────────────────────────────────────────────────────────

/// Python `str(Path(x))`
pub fn py_yol(s: &str) -> String {
    if s.is_empty() {
        return ".".into();
    }
    let mütləq = s.starts_with('/');
    let h: Vec<&str> = s.split('/').filter(|x| !x.is_empty() && *x != ".").collect();
    let r = h.join("/");
    if mütləq {
        format!("/{r}")
    } else if r.is_empty() {
        ".".into()
    } else {
        r
    }
}

fn mütləq(p: &Path) -> PathBuf {
    if let Ok(c) = std::fs::canonicalize(p) {
        return c;
    }
    let cari = std::env::current_dir().unwrap_or_default();
    let tam = if p.is_absolute() { p.to_path_buf() } else { cari.join(p) };
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
    // Mövcud ən uzun hissəni kanonikləşdir (simvolik keçidlər)
    n
}

fn hədəf(qovluq: &Path, ad_: &str) -> Nəticə<PathBuf> {
    let b = ad_.as_bytes();
    if ad_.starts_with('/') || ad_.starts_with('\\') || (b.len() > 1 && b[1] == b':') {
        return Err(x_(format!("arxivdə mütləq yol var: {}", str_repr(ad_))));
    }
    let y = mütləq(&qovluq.join(ad_));
    if y != qovluq && !y.starts_with(qovluq) {
        return Err(x_(format!("arxivdəki yol qovluqdan kənara çıxır: {}", str_repr(ad_))));
    }
    Ok(y)
}

fn fayllar(i: &super::icraci::İcraçı, yollar: &D) -> Nəticə<Vec<(PathBuf, String)>> {
    let s = match yollar {
        D::Siyahı(l) => l.borrow().clone(),
        x => vec![x.clone()],
    };
    let _ = i;
    let mut n = vec![];
    for y in s {
        let ys = py_s(&y);
        let p = PathBuf::from(&ys);
        if !p.exists() {
            return Err(tapılmadı(&ys));
        }
        if p.is_dir() {
            let kök = mütləq(&p).parent().map(Path::to_path_buf).unwrap_or_default();
            let mut hamısı = vec![];
            fn gəz(p: &Path, v: &mut Vec<PathBuf>) {
                if let Ok(d) = std::fs::read_dir(p) {
                    for e in d.flatten() {
                        let q = e.path();
                        let sim = q.symlink_metadata().map(|m| m.file_type().is_symlink()).unwrap_or(false);
                        v.push(q.clone());
                        if q.is_dir() && !sim {
                            gəz(&q, v);
                        }
                    }
                }
            }
            gəz(&p, &mut hamısı);
            hamısı.sort_by(|a, b| {
                let x: Vec<_> = a.components().map(|c| c.as_os_str().to_owned()).collect();
                let y: Vec<_> = b.components().map(|c| c.as_os_str().to_owned()).collect();
                x.cmp(&y)
            });
            for f in hamısı {
                let sim = f.symlink_metadata().map(|m| m.file_type().is_symlink()).unwrap_or(false);
                if f.is_file() && !sim {
                    let r = mütləq(&f);
                    let ad_ = r.strip_prefix(&kök).unwrap_or(&r).to_string_lossy().replace('\\', "/");
                    n.push((f, ad_));
                }
            }
        } else {
            let ad_ = p.file_name().map(|x| x.to_string_lossy().to_string()).unwrap_or_default();
            n.push((p, ad_));
        }
    }
    Ok(n)
}

fn oxu(p: &Path) -> Nəticə<Vec<u8>> {
    std::fs::read(p).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))
}

fn yaz(p: &Path, b: &[u8]) -> Nəticə<()> {
    if let Some(q) = p.parent() {
        let _ = std::fs::create_dir_all(q);
    }
    std::fs::write(p, b).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))
}

// ── zip ────────────────────────────────────────────────────────────────

fn dos_vaxt(p: &Path) -> (u16, u16) {
    let t = std::fs::metadata(p)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let (il, ay, gün, saat, dəq, san, _) = super::platforma::yerli_vaxt(t);
    let il = (il.max(1980) - 1980) as u16;
    let tarix = il << 9 | (ay as u16) << 5 | gün as u16;
    let vaxt = (saat as u16) << 11 | (dəq as u16) << 5 | (san as u16 / 2);
    (vaxt, tarix)
}

pub struct ZipÜzv {
    pub ad: String,
    pub metod: u16,
    pub crc: u32,
    pub sıxılmış: u64,
    pub ölçü: u64,
    pub xarici: u32,
    pub ofset: u64,
}

impl ZipÜzv {
    fn qovluqdur(&self) -> bool {
        self.ad.ends_with('/')
    }
}

fn u16_(b: &[u8], k: usize) -> u16 {
    u16::from_le_bytes([b[k], b[k + 1]])
}
fn u32_(b: &[u8], k: usize) -> u32 {
    u32::from_le_bytes([b[k], b[k + 1], b[k + 2], b[k + 3]])
}

pub fn zip_üzvlər(b: &[u8]) -> Option<Vec<ZipÜzv>> {
    if b.len() < 22 {
        return None;
    }
    let mut e = None;
    let alt = b.len().saturating_sub(22 + 65535);
    let mut k = b.len() - 22;
    loop {
        if u32_(b, k) == 0x06054b50 {
            e = Some(k);
            break;
        }
        if k == alt {
            break;
        }
        k -= 1;
    }
    let e = e?;
    let say = u16_(b, e + 10) as usize;
    let mut p = u32_(b, e + 16) as usize;
    let mut n = vec![];
    for _ in 0..say {
        if p + 46 > b.len() || u32_(b, p) != 0x02014b50 {
            return None;
        }
        let bayraq = u16_(b, p + 8);
        let metod = u16_(b, p + 10);
        let crc = u32_(b, p + 16);
        let sıxılmış = u32_(b, p + 20) as u64;
        let ölçü = u32_(b, p + 24) as u64;
        let ad_u = u16_(b, p + 28) as usize;
        let əlavə_u = u16_(b, p + 30) as usize;
        let şərh_u = u16_(b, p + 32) as usize;
        let xarici = u32_(b, p + 38);
        let ofset = u32_(b, p + 42) as u64;
        if p + 46 + ad_u > b.len() {
            return None;
        }
        let ad_b = &b[p + 46..p + 46 + ad_u];
        let ad_ = if bayraq & 0x800 != 0 {
            String::from_utf8_lossy(ad_b).to_string()
        } else {
            // cp437 — ASCII hissə
            ad_b.iter().map(|&c| c as char).collect()
        };
        n.push(ZipÜzv { ad: ad_, metod, crc, sıxılmış, ölçü, xarici, ofset });
        p += 46 + ad_u + əlavə_u + şərh_u;
    }
    Some(n)
}

pub fn zip_üzv_oxu(b: &[u8], u: &ZipÜzv) -> Option<Vec<u8>> {
    let p = u.ofset as usize;
    if p + 30 > b.len() || u32_(b, p) != 0x04034b50 {
        return None;
    }
    let başla = p + 30 + u16_(b, p + 26) as usize + u16_(b, p + 28) as usize;
    let son = başla.checked_add(u.sıxılmış as usize)?;
    if son > b.len() {
        return None;
    }
    let v = &b[başla..son];
    let a = match u.metod {
        0 => v.to_vec(),
        8 => inflate_xam(v).ok()?.0,
        _ => return None,
    };
    if crc32(&a) != u.crc {
        return None;
    }
    Some(a)
}

pub fn zip_yaz(fayllar: &[(PathBuf, String)]) -> Nəticə<Vec<u8>> {
    let mut ç = vec![];
    let mut mərkəz = vec![];
    for (f, ad_) in fayllar {
        let v = oxu(f)?;
        let s = deflate(&v, 6);
        let crc = crc32(&v);
        let (vaxt, tarix) = dos_vaxt(f);
        let bayraq: u16 = if ad_.is_ascii() { 0 } else { 0x800 };
        let ofset = ç.len() as u32;
        ç.extend(0x04034b50u32.to_le_bytes());
        ç.extend(20u16.to_le_bytes());
        ç.extend(bayraq.to_le_bytes());
        ç.extend(8u16.to_le_bytes());
        ç.extend(vaxt.to_le_bytes());
        ç.extend(tarix.to_le_bytes());
        ç.extend(crc.to_le_bytes());
        ç.extend((s.len() as u32).to_le_bytes());
        ç.extend((v.len() as u32).to_le_bytes());
        ç.extend((ad_.len() as u16).to_le_bytes());
        ç.extend(0u16.to_le_bytes());
        ç.extend(ad_.as_bytes());
        ç.extend(&s);
        mərkəz.extend(0x02014b50u32.to_le_bytes());
        mərkəz.extend((0x0300u16 | 20).to_le_bytes());
        mərkəz.extend(20u16.to_le_bytes());
        mərkəz.extend(bayraq.to_le_bytes());
        mərkəz.extend(8u16.to_le_bytes());
        mərkəz.extend(vaxt.to_le_bytes());
        mərkəz.extend(tarix.to_le_bytes());
        mərkəz.extend(crc.to_le_bytes());
        mərkəz.extend((s.len() as u32).to_le_bytes());
        mərkəz.extend((v.len() as u32).to_le_bytes());
        mərkəz.extend((ad_.len() as u16).to_le_bytes());
        mərkəz.extend([0u8; 8]);
        mərkəz.extend((0o100644u32 << 16).to_le_bytes());
        mərkəz.extend(ofset.to_le_bytes());
        mərkəz.extend(ad_.as_bytes());
    }
    let m_ofset = ç.len() as u32;
    let n = fayllar.len() as u16;
    ç.extend(&mərkəz);
    ç.extend(0x06054b50u32.to_le_bytes());
    ç.extend([0u8; 4]);
    ç.extend(n.to_le_bytes());
    ç.extend(n.to_le_bytes());
    ç.extend((mərkəz.len() as u32).to_le_bytes());
    ç.extend(m_ofset.to_le_bytes());
    ç.extend(0u16.to_le_bytes());
    Ok(ç)
}

fn zip_aç_obyekt(arxiv: &str) -> Nəticə<(Vec<u8>, Vec<ZipÜzv>)> {
    let b = match std::fs::read(arxiv) {
        Ok(b) => b,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Err(tapılmadı(arxiv)),
        Err(e) => return Err(xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009")),
    };
    match zip_üzvlər(&b) {
        Some(u) => Ok((b, u)),
        None => Err(x_(format!("\"{}\" zip arxivi deyil və ya pozulub", arxiv))),
    }
}

// ── tar ────────────────────────────────────────────────────────────────

pub struct TarÜzv {
    pub ad: String,
    pub tip: u8,
    pub ölçü: u64,
    pub verilən: Vec<u8>,
}

impl TarÜzv {
    fn fayldır(&self) -> bool {
        matches!(self.tip, b'0' | 0 | b'7')
    }
    fn qovluqdur(&self) -> bool {
        self.tip == b'5'
    }
}

fn oktal(b: &[u8]) -> u64 {
    if !b.is_empty() && b[0] & 0x80 != 0 {
        let mut v = 0u64;
        for x in &b[1..] {
            v = v << 8 | *x as u64;
        }
        return v;
    }
    let s: String = b.iter().take_while(|c| **c != 0).map(|c| *c as char).collect();
    u64::from_str_radix(s.trim(), 8).unwrap_or(0)
}

fn c_mətn(b: &[u8]) -> String {
    let s: Vec<u8> = b.iter().take_while(|c| **c != 0).copied().collect();
    String::from_utf8_lossy(&s).to_string()
}

pub fn tar_üzvlər(b: &[u8]) -> Option<Vec<TarÜzv>> {
    let mut n = vec![];
    let mut k = 0;
    let mut uzun_ad: Option<String> = None;
    let mut pax_ad: Option<String> = None;
    while k + 512 <= b.len() {
        let h = &b[k..k + 512];
        if h.iter().all(|x| *x == 0) {
            break;
        }
        // Yoxlama cəmi
        let cəm: u64 = h.iter().enumerate().map(|(i, x)| if (148..156).contains(&i) { 32 } else { *x as u64 }).sum();
        if oktal(&h[148..156]) != cəm {
            return None;
        }
        let tip = h[156];
        let ölçü = oktal(&h[124..136]);
        let başla = k + 512;
        let son = başla.checked_add(ölçü as usize)?;
        if son > b.len() {
            return None;
        }
        let v = b[başla..son].to_vec();
        k = başla + ((ölçü as usize + 511) / 512) * 512;
        match tip {
            b'L' => {
                uzun_ad = Some(c_mətn(&v));
                continue;
            }
            b'x' => {
                let s = String::from_utf8_lossy(&v).to_string();
                for sətir in s.lines() {
                    if let Some((_, kv)) = sətir.split_once(' ') {
                        if let Some(p) = kv.strip_prefix("path=") {
                            pax_ad = Some(p.to_string());
                        }
                    }
                }
                continue;
            }
            b'g' => continue,
            _ => {}
        }
        let mut ad_ = c_mətn(&h[0..100]);
        if &h[257..262] == b"ustar" {
            let ön = c_mətn(&h[345..500]);
            if !ön.is_empty() {
                ad_ = format!("{}/{}", ön, ad_);
            }
        }
        if let Some(u) = uzun_ad.take() {
            ad_ = u;
        }
        if let Some(p) = pax_ad.take() {
            ad_ = p;
        }
        if tip == b'5' {
            ad_ = ad_.trim_end_matches('/').to_string();
        }
        n.push(TarÜzv { ad: ad_, tip, ölçü: if tip == b'5' { 0 } else { ölçü }, verilən: v });
    }
    Some(n)
}

fn tar_başlıq(ad_: &str, ölçü: u64, mtime: u64, tip: u8, rejim: u32) -> Vec<u8> {
    let mut h = vec![0u8; 512];
    let mut pax = vec![];
    let ad_b = ad_.as_bytes();
    if ad_b.len() > 100 || !ad_.is_ascii() {
        // PAX uzun ad
        let qeyd = |k: &str, v: &str| {
            let mut n = k.len() + v.len() + 3;
            let mut s = format!("{} {}={}\n", n, k, v);
            while s.len() != n {
                n = s.len();
                s = format!("{} {}={}\n", n, k, v);
            }
            s
        };
        let məzmun = qeyd("path", ad_);
        let mut x = tar_başlıq("././@PaxHeader", məzmun.len() as u64, 0, b'x', 0o644);
        x.extend(məzmun.as_bytes());
        x.resize(x.len().div_ceil(512) * 512, 0);
        pax = x;
    }
    let qısa: Vec<u8> = ad_b.iter().take(100).copied().collect();
    h[..qısa.len()].copy_from_slice(&qısa);
    let yaz = |h: &mut Vec<u8>, k: usize, u: usize, v: u64| {
        let s = format!("{:0w$o}\0", v, w = u - 1);
        h[k..k + u].copy_from_slice(&s.as_bytes()[..u]);
    };
    yaz(&mut h, 100, 8, rejim as u64);
    yaz(&mut h, 108, 8, 0);
    yaz(&mut h, 116, 8, 0);
    yaz(&mut h, 124, 12, ölçü);
    yaz(&mut h, 136, 12, mtime);
    h[148..156].copy_from_slice(b"        ");
    h[156] = tip;
    h[257..263].copy_from_slice(b"ustar\0");
    h[263..265].copy_from_slice(b"00");
    let cəm: u64 = h.iter().map(|x| *x as u64).sum();
    let s = format!("{:06o}\0 ", cəm);
    h[148..156].copy_from_slice(s.as_bytes());
    pax.extend(h);
    pax
}

pub fn tar_yaz(fayllar: &[(PathBuf, String)]) -> Nəticə<Vec<u8>> {
    let mut ç = vec![];
    for (f, ad_) in fayllar {
        let v = oxu(f)?;
        let mt = std::fs::metadata(f)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs())
            .unwrap_or(0);
        ç.extend(tar_başlıq(ad_, v.len() as u64, mt, b'0', 0o644));
        ç.extend(&v);
        ç.resize(ç.len().div_ceil(512) * 512, 0);
    }
    ç.extend(vec![0u8; 1024]);
    ç.resize(ç.len().div_ceil(10240) * 10240, 0);
    Ok(ç)
}

fn tar_sıxma_növü(arxiv: &str) -> &'static str {
    let a = arxiv.to_lowercase();
    if a.ends_with(".gz") || a.ends_with(".tgz") {
        "gz"
    } else if a.ends_with(".bz2") || a.ends_with(".tbz") {
        "bz2"
    } else if a.ends_with(".xz") || a.ends_with(".txz") {
        "xz"
    } else {
        ""
    }
}

fn tar_obyekt(arxiv: &str) -> Nəticə<Vec<TarÜzv>> {
    let b = match std::fs::read(arxiv) {
        Ok(b) => b,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Err(tapılmadı(arxiv)),
        Err(e) => return Err(xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009")),
    };
    let pis = || x_(format!("\"{}\" tar arxivi deyil və ya pozulub", arxiv));
    let b = if b.starts_with(&[0x1f, 0x8b]) {
        gzip_aç_xam(&b).map_err(|_| pis())?
    } else if b.starts_with(b"BZh") || b.starts_with(&[0xfd, b'7', b'z', b'X', b'Z']) {
        return Err(x_("bz2/xz sıxılmış tar bu platformada dəstəklənmir — gzip (.tar.gz) işlədin"));
    } else {
        b
    };
    let u = tar_üzvlər(&b).ok_or_else(pis)?;
    if u.is_empty() && !b.iter().take(512).all(|x| *x == 0) {
        return Err(pis());
    }
    if b.is_empty() {
        return Err(pis());
    }
    Ok(u)
}

fn hədəf_qovluq(q: &D) -> PathBuf {
    let q = if q.boşdur() { ".".to_string() } else { py_s(q) };
    mütləq(Path::new(&q))
}

pub fn qur() -> Rc<Modul> {
    let bş = |v: Vec<u8>| D::Bayt(Rc::new(v));
    Modul::yeni("sıxma", vec![
        ("gzipSıx", f("gzipSıx", 1, Some(2), move |_, a, adlı| {
            let n = imza("gzipSıx", a, adlı, &["x", "s"])?;
            let s = var(&n, 1).map(|x| py_int(&x, "gzipSıx")).transpose()?.unwrap_or(9);
            Ok(bş(gzip_sıx(&bayt(&al(&n, 0), "gzipSıx")?, s)))
        })),
        ("gzipAç", f("gzipAç", 1, Some(1), move |_, a, _| Ok(bş(gzip_aç(&bayt(&a[0], "gzipAç")?)?)))),
        ("gzipAçMətn", f("gzipAçMətn", 1, Some(1), |_, a, _| {
            let b = gzip_aç(&bayt(&a[0], "gzipAç")?)?;
            utf8(b).map(D::str).map_err(|_| x_("açılan məlumat UTF-8 mətn deyil — `gzipAç` işlədin"))
        })),
        ("zlibSıx", f("zlibSıx", 1, Some(2), move |_, a, adlı| {
            let n = imza("zlibSıx", a, adlı, &["x", "s"])?;
            let s = var(&n, 1).map(|x| py_int(&x, "zlibSıx")).transpose()?.unwrap_or(9);
            Ok(bş(zlib_sıx(&bayt(&al(&n, 0), "zlibSıx")?, s)))
        })),
        ("zlibAç", f("zlibAç", 1, Some(1), move |_, a, _| Ok(bş(zlib_aç(&bayt(&a[0], "zlibAç")?)?)))),
        ("faylSıx", f("faylSıx", 1, Some(1), |_, a, _| {
            let y = py_s(&a[0]);
            let p = PathBuf::from(&y);
            if !p.is_file() {
                return Err(tapılmadı(&y));
            }
            let h = format!("{}.gz", py_yol(&y));
            yaz(Path::new(&h), &gzip_sıx(&oxu(&p)?, 9))?;
            Ok(D::str(h))
        })),
        ("faylAç", f("faylAç", 1, Some(1), |_, a, _| {
            let y = py_s(&a[0]);
            let py = py_yol(&y);
            let ad_ = py.rsplit('/').next().unwrap_or("");
            let şəkilçi = match ad_.rfind('.') {
                Some(k) if k > 0 => &ad_[k..],
                _ => "",
            };
            if şəkilçi != ".gz" {
                return Err(x_(format!("\"{}\" `.gz` faylı deyil", y)));
            }
            let h = py[..py.len() - 3].to_string();
            let b = match std::fs::read(&y) {
                Ok(b) => b,
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Err(tapılmadı(&y)),
                Err(e) => return Err(xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009")),
            };
            let a = gzip_aç_xam(&b).map_err(|e| x_(format!("gzip faylı pozulub: {}", e)))?;
            yaz(Path::new(&h), &a)?;
            Ok(D::str(h))
        })),
        ("zipYarat", f("zipYarat", 2, Some(2), |i, a, _| {
            let f_ = fayllar(i, &a[1])?;
            let b = zip_yaz(&f_)?;
            yaz(Path::new(&*py_s(&a[0])), &b)?;
            Ok(D::T(f_.len() as i64))
        })),
        ("zipAç", f("zipAç", 1, Some(2), |_, a, adlı| {
            let n = imza("zipAç", a, adlı, &["arxiv", "qovluq"])?;
            let arxiv = py_s(&al(&n, 0));
            let q = hədəf_qovluq(&al(&n, 1));
            let (b, üzvlər) = zip_aç_obyekt(&arxiv)?;
            let mut h = vec![];
            for u in &üzvlər {
                h.push(hədəf(&q, &u.ad)?);
                if (u.xarici >> 16) & 0o170000 == 0o120000 {
                    return Err(x_(format!("arxivdə simvolik keçid var: {}", str_repr(&u.ad))));
                }
            }
            std::fs::create_dir_all(&q).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
            for (u, y) in üzvlər.iter().zip(&h) {
                if u.qovluqdur() {
                    let _ = std::fs::create_dir_all(y);
                    continue;
                }
                let v = zip_üzv_oxu(&b, u).ok_or_else(|| x_(format!("\"{}\" zip arxivi deyil və ya pozulub", arxiv)))?;
                yaz(y, &v)?;
            }
            Ok(D::siyahı(üzvlər.iter().filter(|u| !u.qovluqdur()).map(|u| D::str(u.ad.clone())).collect()))
        })),
        ("zipSiyahı", f("zipSiyahı", 1, Some(1), |_, a, _| {
            let (_, üzvlər) = zip_aç_obyekt(&py_s(&a[0]))?;
            Ok(D::siyahı(
                üzvlər
                    .iter()
                    .map(|u| {
                        lüğət(vec![
                            ("ad", D::str(u.ad.clone())),
                            ("ölçü", D::T(u.ölçü as i64)),
                            ("sıxılmış", D::T(u.sıxılmış as i64)),
                            ("qovluq", D::M(u.qovluqdur())),
                        ])
                    })
                    .collect(),
            ))
        })),
        ("zipOxu", f("zipOxu", 2, Some(2), move |_, a, _| {
            let arxiv = py_s(&a[0]);
            let ad_ = py_s(&a[1]);
            let (b, üzvlər) = zip_aç_obyekt(&arxiv)?;
            match üzvlər.iter().rev().find(|u| u.ad == ad_) {
                Some(u) => Ok(bş(zip_üzv_oxu(&b, u).ok_or_else(|| x_(format!("\"{}\" zip arxivi deyil və ya pozulub", arxiv)))?)),
                None => Err(x_(format!("\"{}\" arxivdə yoxdur", ad_))),
            }
        })),
        ("tarYarat", f("tarYarat", 2, Some(2), |i, a, _| {
            let arxiv = py_s(&a[0]);
            let f_ = fayllar(i, &a[1])?;
            let b = tar_yaz(&f_)?;
            let b = match tar_sıxma_növü(&arxiv) {
                "gz" => gzip_sıx(&b, 9),
                "" => b,
                _ => return Err(x_("bz2/xz sıxılmış tar bu platformada dəstəklənmir — gzip (.tar.gz) işlədin")),
            };
            yaz(Path::new(&arxiv), &b)?;
            Ok(D::T(f_.len() as i64))
        })),
        ("tarAç", f("tarAç", 1, Some(2), |_, a, adlı| {
            let n = imza("tarAç", a, adlı, &["arxiv", "qovluq"])?;
            let q = hədəf_qovluq(&al(&n, 1));
            let üzvlər = tar_obyekt(&py_s(&al(&n, 0)))?;
            let mut h = vec![];
            for u in &üzvlər {
                h.push(hədəf(&q, &u.ad)?);
                if matches!(u.tip, b'1' | b'2' | b'3' | b'4' | b'6') {
                    return Err(x_(format!("arxivdə icazəsiz üzv (keçid/cihaz): {}", str_repr(&u.ad))));
                }
            }
            std::fs::create_dir_all(&q).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
            for (u, y) in üzvlər.iter().zip(&h) {
                if u.qovluqdur() {
                    let _ = std::fs::create_dir_all(y);
                } else if u.fayldır() {
                    yaz(y, &u.verilən)?;
                }
            }
            Ok(D::siyahı(üzvlər.iter().filter(|u| u.fayldır()).map(|u| D::str(u.ad.clone())).collect()))
        })),
        ("tarSiyahı", f("tarSiyahı", 1, Some(1), |_, a, _| {
            let üzvlər = tar_obyekt(&py_s(&a[0]))?;
            Ok(D::siyahı(
                üzvlər
                    .iter()
                    .map(|u| {
                        lüğət(vec![
                            ("ad", D::str(u.ad.clone())),
                            ("ölçü", D::T(u.ölçü as i64)),
                            ("qovluq", D::M(u.qovluqdur())),
                        ])
                    })
                    .collect(),
            ))
        })),
    ])
}
