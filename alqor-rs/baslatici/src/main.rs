//! Alqor tətbiq başladıcısı — `alqor qur --exe` nəticəsinin başı.
//!
//! Fayl quruluşu: [bu proqram][yük][izləyici]
//!   yük      = "ALQPAK01" | u32 sayı | u32 ad_uz | ad | u32 id_uz | id |
//!              u32 giriş_uz | giriş | (u32 yol_uz | yol | u64 ölçü |
//!              u64 sıxılmış | raw deflate)*
//!   izləyici = u64 yükün başlanğıcı | "ALQORPAK"
//!
//! İlk işə salınmada yük `%LOCALAPPDATA%\Alqor\tetbiqler\<ad>-<id>\`
//! qovluğuna açılır, sonra `python\python.exe tətbiq.pyz arqumentlər…`
//! işlədilir. Növbəti dəfələr yalnız işə salınır.
#![cfg_attr(feature = "pencere", windows_subsystem = "windows")]

use std::env;
use std::fs::{self, File};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::process::{exit, Command};

const SEHR: &[u8; 8] = b"ALQPAK01";
const İZ: &[u8; 8] = b"ALQORPAK";

fn u32_oxu(b: &[u8], i: &mut usize) -> io::Result<u32> {
    let s = b.get(*i..*i + 4).ok_or(io::ErrorKind::UnexpectedEof)?;
    *i += 4;
    Ok(u32::from_le_bytes(s.try_into().unwrap()))
}

fn u64_oxu(b: &[u8], i: &mut usize) -> io::Result<u64> {
    let s = b.get(*i..*i + 8).ok_or(io::ErrorKind::UnexpectedEof)?;
    *i += 8;
    Ok(u64::from_le_bytes(s.try_into().unwrap()))
}

fn mətn_oxu(b: &[u8], i: &mut usize) -> io::Result<String> {
    let n = u32_oxu(b, i)? as usize;
    let s = b.get(*i..*i + n).ok_or(io::ErrorKind::UnexpectedEof)?;
    *i += n;
    String::from_utf8(s.to_vec()).map_err(|_| io::ErrorKind::InvalidData.into())
}

struct Yük {
    ad: String,
    id: String,
    giriş: String,
    məlumat: Vec<u8>,
    başlanğıc: usize,
    say: u32,
}

fn yükü_oxu(exe: &Path) -> io::Result<Yük> {
    let mut f = File::open(exe)?;
    let uz = f.seek(SeekFrom::End(0))?;
    if uz < 16 {
        return Err(io::ErrorKind::InvalidData.into());
    }
    f.seek(SeekFrom::End(-16))?;
    let mut iz = [0u8; 16];
    f.read_exact(&mut iz)?;
    if &iz[8..] != İZ {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "yük tapılmadı"));
    }
    let baş = u64::from_le_bytes(iz[..8].try_into().unwrap());
    f.seek(SeekFrom::Start(baş))?;
    let mut məlumat = Vec::with_capacity((uz - baş) as usize);
    f.take(uz - 16 - baş).read_to_end(&mut məlumat)?;
    if !məlumat.starts_with(SEHR) {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "yük pozulub"));
    }
    let mut i = 8;
    let say = u32_oxu(&məlumat, &mut i)?;
    let ad = mətn_oxu(&məlumat, &mut i)?;
    let id = mətn_oxu(&məlumat, &mut i)?;
    let giriş = mətn_oxu(&məlumat, &mut i)?;
    Ok(Yük { ad, id, giriş, məlumat, başlanğıc: i, say })
}

fn aç(y: &Yük, hədəf: &Path) -> io::Result<()> {
    let müvəqqəti = hədəf.with_extension(format!("yeni-{}", std::process::id()));
    if müvəqqəti.exists() {
        fs::remove_dir_all(&müvəqqəti)?;
    }
    fs::create_dir_all(&müvəqqəti)?;
    let b = &y.məlumat;
    let mut i = y.başlanğıc;
    for _ in 0..y.say {
        let yol = mətn_oxu(b, &mut i)?;
        let ölçü = u64_oxu(b, &mut i)? as usize;
        let sıxılmış = u64_oxu(b, &mut i)? as usize;
        let parça = b.get(i..i + sıxılmış).ok_or(io::ErrorKind::UnexpectedEof)?;
        i += sıxılmış;
        if yol.split(['/', '\\']).any(|h| h == ".." || h.is_empty()) {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "təhlükəli yol"));
        }
        let açılmış = if sıxılmış == ölçü {
            parça.to_vec()
        } else {
            miniz_oxide::inflate::decompress_to_vec(parça)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "açılmadı"))?
        };
        let p = müvəqqəti.join(&yol);
        if let Some(q) = p.parent() {
            fs::create_dir_all(q)?;
        }
        File::create(&p)?.write_all(&açılmış)?;
    }
    File::create(müvəqqəti.join(".hazir"))?.write_all(b"1")?;
    if hədəf.exists() {
        let _ = fs::remove_dir_all(hədəf);
    }
    match fs::rename(&müvəqqəti, hədəf) {
        Ok(()) => Ok(()),
        // Başqa nüsxə eyni anda açıbsa — onunku istifadə olunur
        Err(_) if hədəf.join(".hazir").exists() => {
            let _ = fs::remove_dir_all(&müvəqqəti);
            Ok(())
        }
        Err(e) => Err(e),
    }
}

fn keş_qovluğu() -> PathBuf {
    if let Ok(q) = env::var("ALQOR_KES") {
        return PathBuf::from(q);
    }
    let baza = env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .or_else(|| env::var_os("HOME").map(|h| PathBuf::from(h).join(".cache")))
        .unwrap_or_else(env::temp_dir);
    baza.join("Alqor").join("tetbiqler")
}

fn xəta(mesaj: &str) -> ! {
    #[cfg(all(windows, feature = "pencere"))]
    {
        mesaj_qutusu(mesaj);
    }
    eprintln!("✖ {}", mesaj);
    exit(1)
}

#[cfg(all(windows, feature = "pencere"))]
fn mesaj_qutusu(mesaj: &str) {
    #[link(name = "user32")]
    extern "system" {
        fn MessageBoxW(h: *mut u8, m: *const u16, b: *const u16, t: u32) -> i32;
    }
    let m: Vec<u16> = mesaj.encode_utf16().chain([0]).collect();
    let b: Vec<u16> = "Alqor".encode_utf16().chain([0]).collect();
    unsafe {
        MessageBoxW(std::ptr::null_mut(), m.as_ptr(), b.as_ptr(), 0x10);
    }
}

fn main() {
    let exe = env::current_exe().unwrap_or_else(|_| xəta("proqramın yolu tapılmadı"));
    let y = yükü_oxu(&exe).unwrap_or_else(|e| xəta(&format!("tətbiq paketi oxunmadı: {}", e)));
    let qovluq = keş_qovluğu().join(format!("{}-{}", y.ad, y.id));
    if !qovluq.join(".hazir").exists() {
        aç(&y, &qovluq).unwrap_or_else(|e| xəta(&format!("tətbiq açılmadı ({}): {}", qovluq.display(), e)));
    }
    let python = if cfg!(feature = "pencere") { "pythonw.exe" } else { "python.exe" };
    let python = if cfg!(windows) {
        qovluq.join("python").join(python)
    } else {
        qovluq.join("python").join("bin").join("python3")
    };
    let mut əmr = Command::new(&python);
    əmr.arg(qovluq.join(&y.giriş))
        .args(env::args_os().skip(1))
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1")
        .env("ALQOR_EXE", &exe);
    match əmr.status() {
        Ok(s) => exit(s.code().unwrap_or(1)),
        Err(e) => xəta(&format!("{} işə salınmadı: {}", python.display(), e)),
    }
}
