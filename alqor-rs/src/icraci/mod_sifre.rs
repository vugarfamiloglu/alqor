//! `şifrə` — kriptoqrafiya (modullar/sifre.py): heşlər, HMAC, scrypt parol
//! heşi, AES-256-GCM, JWT (HS256/384/512), təsadüfi baytlar, UUID.

use super::deyerler::*;
use super::elave::*;
use super::icraci::İcraçı;
use hmac::Mac;
use std::rc::Rc;

pub const ALQORİTMLƏR: &[&str] =
    &["md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha3_256", "sha3_512", "blake2b", "blake2s"];

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("ŞifrələməXətası", m, "ALQ-R005")
}

fn jwt_x(m: impl Into<String>) -> Siqnal {
    xəta("JWTXətası", m, "ALQ-R005")
}

/// hashlib.new(ad, b).digest()
pub fn heş_bayt(ad_: &str, b: &[u8]) -> Option<Vec<u8>> {
    use sha2::Digest;
    Some(match ad_ {
        "md5" => md5::Md5::digest(b).to_vec(),
        "sha1" => sha1::Sha1::digest(b).to_vec(),
        "sha224" => sha2::Sha224::digest(b).to_vec(),
        "sha256" => sha2::Sha256::digest(b).to_vec(),
        "sha384" => sha2::Sha384::digest(b).to_vec(),
        "sha512" => sha2::Sha512::digest(b).to_vec(),
        "sha3_224" => sha3::Sha3_224::digest(b).to_vec(),
        "sha3_256" => sha3::Sha3_256::digest(b).to_vec(),
        "sha3_384" => sha3::Sha3_384::digest(b).to_vec(),
        "sha3_512" => sha3::Sha3_512::digest(b).to_vec(),
        "blake2b" => blake2::Blake2b512::digest(b).to_vec(),
        "blake2s" => blake2::Blake2s256::digest(b).to_vec(),
        _ => return None,
    })
}

pub fn hmac_bayt(ad_: &str, açar: &[u8], m: &[u8]) -> Option<Vec<u8>> {
    macro_rules! h {
        ($t:ty) => {{
            let mut x = <hmac::Hmac<$t> as Mac>::new_from_slice(açar).ok()?;
            x.update(m);
            x.finalize().into_bytes().to_vec()
        }};
    }
    Some(match ad_ {
        "md5" => h!(md5::Md5),
        "sha1" => h!(sha1::Sha1),
        "sha224" => h!(sha2::Sha224),
        "sha256" => h!(sha2::Sha256),
        "sha384" => h!(sha2::Sha384),
        "sha512" => h!(sha2::Sha512),
        "sha3_224" => h!(sha3::Sha3_224),
        "sha3_256" => h!(sha3::Sha3_256),
        "sha3_384" => h!(sha3::Sha3_384),
        "sha3_512" => h!(sha3::Sha3_512),
        "blake2b" => {
            let mut x = <hmac::SimpleHmac<blake2::Blake2b512> as Mac>::new_from_slice(açar).ok()?;
            x.update(m);
            x.finalize().into_bytes().to_vec()
        }
        "blake2s" => {
            let mut x = <hmac::SimpleHmac<blake2::Blake2s256> as Mac>::new_from_slice(açar).ok()?;
            x.update(m);
            x.finalize().into_bytes().to_vec()
        }
        _ => return None,
    })
}

fn heş(x: &D, alq: &D) -> Nəticə<String> {
    let a = py_s(alq).to_lowercase().replace('-', "");
    let a = match a.as_str() {
        "sha3256" => "sha3_256".to_string(),
        "sha3512" => "sha3_512".to_string(),
        _ => a,
    };
    if !ALQORİTMLƏR.contains(&a.as_str()) {
        return Err(xəta("DəyərXətası", format!("`{}` tanınmır — {}", a, ALQORİTMLƏR.join(", ")), "ALQ-T001"));
    }
    Ok(hex(&heş_bayt(&a, &bayt(x, "heş")?).unwrap()))
}

pub fn sabit_müq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut f = 0u8;
    for (x, y) in a.iter().zip(b) {
        f |= x ^ y;
    }
    f == 0
}

const LN: u8 = 15;
const RR: u32 = 8;
const PP: u32 = 1;

fn scrypt_(parol: &[u8], duz: &[u8], ln: u8, r: u32, p: u32, n: usize) -> Option<Vec<u8>> {
    let pr = scrypt::Params::new(ln, r, p, n.max(10)).ok()?;
    let mut ç = vec![0u8; n];
    scrypt::scrypt(parol, duz, &pr, &mut ç).ok()?;
    Some(ç)
}

pub fn parol_heş(parol: &[u8]) -> String {
    let duz = təsadüfi_bayt(16);
    let h = scrypt_(parol, &duz, LN, RR, PP, 32).unwrap();
    format!("$scrypt$ln={},r={},p={}${}${}", LN, RR, PP, b64(&duz, B64, false), b64(&h, B64, false))
}

pub fn parol_yoxla(parol: &[u8], saxlanmış: &str) -> bool {
    let h: Vec<&str> = saxlanmış.split('$').collect();
    if h.len() != 5 || h[1] != "scrypt" {
        return false;
    }
    let mut p = std::collections::HashMap::new();
    for x in h[2].split(',') {
        let c: Vec<&str> = x.split('=').collect();
        if c.len() != 2 {
            return false;
        }
        p.insert(c[0], c[1]);
    }
    let al_ = |k: &str| -> Option<i64> { p.get(k)?.trim().parse::<i64>().ok() };
    let (Some(ln), Some(r), Some(pp)) = (al_("ln"), al_("r"), al_("p")) else { return false };
    if !((1..=22).contains(&ln) && (1..=32).contains(&r) && (1..=16).contains(&pp)) {
        return false;
    }
    // maxmem=256 MB (Python hashlib.scrypt həddi)
    if 128u64 * r as u64 * ((1u64 << ln) + pp as u64 + 2) > 256 * 1024 * 1024 {
        return false;
    }
    let (Ok(duz), Ok(hh)) = (b64_aç(&dolğu_əlavə(h[3]), false, false), b64_aç(&dolğu_əlavə(h[4]), false, false)) else {
        return false;
    };
    if hh.is_empty() {
        return false;
    }
    match scrypt_(parol, &duz, ln as u8, r as u32, pp as u32, hh.len()) {
        Some(y) => sabit_müq(&y, &hh),
        None => false,
    }
}

fn açar_(a: &D) -> Nəticə<Vec<u8>> {
    match a {
        D::Bayt(b) => {
            if b.len() != 32 {
                return Err(x_(format!("açar 32 bayt olmalıdır ({} bayt verilib) — `şifrə.açarYarat()` işlədin", b.len())));
            }
            Ok(b.to_vec())
        }
        D::S(_) => Err(x_("açar mətn ola bilməz — `şifrə.açarYarat()` və ya paroldan: `şifrə.parolAçarı(parol, duz)`")),
        x => Err(xəta("TipXətası", format!("açar bayt olmalıdır, `{}` gəlib", tip_adı(x)), "ALQ-T001")),
    }
}

pub fn gcm_şifrələ(açar: &[u8], nonce: &[u8], açıq: &[u8], əlavə: &[u8]) -> Vec<u8> {
    use aes_gcm::aead::{Aead, KeyInit, Payload};
    let c = aes_gcm::Aes256Gcm::new_from_slice(açar).unwrap();
    c.encrypt(aes_gcm::Nonce::from_slice(nonce), Payload { msg: açıq, aad: əlavə }).unwrap()
}

pub fn gcm_aç(açar: &[u8], nonce: &[u8], şifrəli_etiket: &[u8], əlavə: &[u8]) -> Nəticə<Vec<u8>> {
    use aes_gcm::aead::{Aead, KeyInit, Payload};
    let c = aes_gcm::Aes256Gcm::new_from_slice(açar).unwrap();
    c.decrypt(aes_gcm::Nonce::from_slice(nonce), Payload { msg: şifrəli_etiket, aad: əlavə })
        .map_err(|_| x_("şifrəli məlumat dəyişdirilib və ya açar yanlışdır"))
}

fn şifrələ(v: &D, a: &D, ə: &D) -> Nəticə<Vec<u8>> {
    let nonce = təsadüfi_bayt(12);
    let açar = açar_(a)?;
    let ş = gcm_şifrələ(&açar, &nonce, &bayt(v, "şifrələ")?, &bayt(ə, "şifrələ")?);
    let mut n = vec![1u8];
    n.extend(nonce);
    n.extend(ş);
    Ok(n)
}

fn şifrə_aç(v: &D, a: &D, ə: &D) -> Nəticə<Vec<u8>> {
    let b = match v {
        D::S(s) => b64_aç(&dolğu_əlavə(s), false, false).map_err(|_| x_("şifrəli mətn base64 deyil"))?,
        x => bayt(x, "şifrəAç")?,
    };
    if b.len() < 29 || b[0] != 1 {
        return Err(x_("bu, `şifrə.şifrələ` ilə şifrələnmiş məlumat deyil"));
    }
    let açar = açar_(a)?;
    gcm_aç(&açar, &b[1..13], &b[13..], &bayt(ə, "şifrəAç")?)
}

// ── JWT ────────────────────────────────────────────────────────────────

fn b64url(b: &[u8]) -> String {
    b64(b, B64URL, false)
}

fn b64url_aç(s: &str) -> Result<Vec<u8>, ()> {
    b64_aç(&dolğu_əlavə(s), true, false)
}

/// `_json(x)`: nümunə → lüğət, lüğət açarları `str()`
fn jwt_json(d: &D) -> D {
    match d {
        D::Nümunə(_) | D::Lüğət(_) => {
            let mut l = Lüğət::default();
            for (a, v) in cütlər(d).unwrap() {
                l.insert(Açar(D::str(py_s(&a))), jwt_json(&v));
            }
            D::lüğət(l)
        }
        D::Siyahı(l) => D::siyahı(l.borrow().iter().map(jwt_json).collect()),
        D::Kortej(k) => D::siyahı(k.iter().map(jwt_json).collect()),
        x => x.clone(),
    }
}

fn jwt_yarat(i: &İcraçı, n: &[Option<D>]) -> Nəticə<String> {
    let alq = var(n, 3).map(|x| py_s(&x)).unwrap_or("HS256".into());
    if !["HS256", "HS384", "HS512"].contains(&alq.as_str()) {
        return Err(xəta("DəyərXətası", "alqoritm HS256, HS384 və ya HS512 olmalıdır", "ALQ-T001"));
    }
    let mut yük = jwt_json(&al(n, 0));
    let D::Lüğət(l) = &yük else {
        return Err(xəta("TipXətası", "JWT verilənləri lüğət olmalıdır", "ALQ-T001"));
    };
    if let Some(m) = var(n, 2).filter(|x| !x.boşdur()) {
        let m = py_int(&m, "tokenYarat")?;
        let indi = super::platforma::indi_san() as i64;
        let mut y = l.borrow().clone();
        y.insert(Açar(D::s("iat")), D::T(indi));
        y.insert(Açar(D::s("exp")), D::T(indi + m));
        yük = D::lüğət(y);
    }
    let baş = b64url(format!("{{\"alg\":\"{}\",\"typ\":\"JWT\"}}", alq).as_bytes());
    let gövdə = b64url(json_dumps(i, &yük, true, false)?.as_bytes());
    let imza = hmac_bayt(&format!("sha{}", &alq[2..]), &bayt(&al(n, 1), "JWTYarat")?, format!("{baş}.{gövdə}").as_bytes()).unwrap();
    Ok(format!("{baş}.{gövdə}.{}", b64url(&imza)))
}

fn jwt_oxu(n: &[Option<D>]) -> Nəticə {
    let t = py_s(&al(n, 0));
    let h: Vec<&str> = t.split('.').collect();
    let pozulub = || jwt_x("JWT formatı pozulub");
    if h.len() != 3 {
        return Err(pozulub());
    }
    let (baş, gövdə, imza) = (h[0], h[1], h[2]);
    let başlıq = b64url_aç(baş).map_err(|_| pozulub())?;
    let başlıq = String::from_utf8(başlıq).map_err(|_| pozulub())?;
    let başlıq = super::modullar::json_oxu(&başlıq).map_err(|_| pozulub())?;
    let alq = l_al(&başlıq, "alg").unwrap_or(D::Boş);
    let alq_s = match &alq {
        D::S(s) if ["HS256", "HS384", "HS512"].contains(&&**s) => s.to_string(),
        x => return Err(jwt_x(format!("JWT alqoritmi qəbul edilmir: {}", py_repr(x)))),
    };
    let gözlənilən =
        hmac_bayt(&format!("sha{}", &alq_s[2..]), &bayt(&al(n, 1), "JWTOxu")?, format!("{baş}.{gövdə}").as_bytes()).unwrap();
    let verilən = b64url_aç(imza).map_err(|_| jwt_x("JWT imzası pozulub"))?;
    if !sabit_müq(&gözlənilən, &verilən) {
        return Err(jwt_x("JWT imzası yanlışdır"));
    }
    let yük = b64url_aç(gövdə)
        .ok()
        .and_then(|b| String::from_utf8(b).ok())
        .and_then(|s| super::modullar::json_oxu(&s).ok())
        .ok_or_else(|| jwt_x("JWT verilənləri pozulub"))?;
    let indi = super::platforma::indi_san();
    let sürüşmə = var(n, 2).and_then(|x| x.onluq()).unwrap_or(0.0);
    let ədəd = |k: &str| match l_al(&yük, k) {
        Some(d @ (D::T(_) | D::BT(_) | D::O(_) | D::M(_))) => d.onluq(),
        _ => None,
    };
    if let Some(e) = ədəd("exp") {
        if indi > e + sürüşmə {
            return Err(jwt_x("JWT-nin müddəti bitib"));
        }
    }
    if let Some(e) = ədəd("nbf") {
        if indi + sürüşmə < e {
            return Err(jwt_x("JWT hələ qüvvədə deyil"));
        }
    }
    Ok(yük)
}

pub fn uuid4() -> String {
    let mut b = təsadüfi_bayt(16);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    let h = hex(&b);
    format!("{}-{}-{}-{}-{}", &h[0..8], &h[8..12], &h[12..16], &h[16..20], &h[20..])
}

pub fn token_urlsafe(n: usize) -> String {
    b64url(&təsadüfi_bayt(n))
}

fn n_(a: &[Option<D>], k: usize, std: i64) -> Nəticə<usize> {
    match var(a, k) {
        None => Ok(std as usize),
        Some(x) => {
            let v = py_int(&x, "təsadüfi")?;
            if v < 0 {
                return Err(xəta("DəyərXətası", "negative argument not allowed", "ALQ-R005"));
            }
            Ok(v as usize)
        }
    }
}

pub fn qur() -> Rc<Modul> {
    let bş = |v: Vec<u8>| D::Bayt(Rc::new(v));
    Modul::yeni("şifrə", vec![
        ("heş", f("heş", 1, Some(2), |_, a, adlı| {
            let n = imza("heş", a, adlı, &["x", "alqoritm"])?;
            Ok(D::str(heş(&al(&n, 0), &var(&n, 1).unwrap_or(D::s("sha256")))?))
        })),
        ("HMAC", f("HMAC", 2, Some(3), |_, a, adlı| {
            let n = imza("HMAC", a, adlı, &["mesaj", "açar", "alqoritm"])?;
            let alq = var(&n, 2).map(|x| py_s(&x).to_lowercase()).unwrap_or("sha256".into());
            let (açar, m) = (bayt(&al(&n, 1), "HMAC")?, bayt(&al(&n, 0), "HMAC")?);
            match hmac_bayt(&alq, &açar, &m) {
                Some(h) => Ok(D::str(hex(&h))),
                None => Err(xəta("DəyərXətası", format!("unsupported hash type {}", alq), "ALQ-R005")),
            }
        })),
        ("parolHeş", f("parolHeş", 1, Some(1), |_, a, _| Ok(D::str(parol_heş(&bayt(&a[0], "parolHeş")?))))),
        ("parolYoxla", f("parolYoxla", 2, Some(2), move |_, a, _| {
            let p = bayt(&a[0], "parolYoxla")?;
            Ok(D::M(parol_yoxla(&p, &py_s(&a[1]))))
        })),
        ("parolAçarı", f("parolAçarı", 2, Some(2), move |_, a, _| {
            let p = bayt(&a[0], "parolAçarı")?;
            let d = bayt(&a[1], "parolAçarı")?;
            Ok(bş(scrypt_(&p, &d, LN, RR, PP, 32).unwrap()))
        })),
        ("açarYarat", f("açarYarat", 0, Some(0), move |_, _, _| Ok(bş(təsadüfi_bayt(32))))),
        ("şifrələ", f("şifrələ", 2, Some(3), move |_, a, adlı| {
            let n = imza("şifrələ", a, adlı, &["verilən", "açar", "əlavə"])?;
            Ok(bş(şifrələ(&al(&n, 0), &al(&n, 1), &var(&n, 2).unwrap_or(D::Bayt(Rc::new(vec![]))))?))
        })),
        ("şifrəAç", f("şifrəAç", 2, Some(3), move |_, a, adlı| {
            let n = imza("şifrəAç", a, adlı, &["verilən", "açar", "əlavə"])?;
            Ok(bş(şifrə_aç(&al(&n, 0), &al(&n, 1), &var(&n, 2).unwrap_or(D::Bayt(Rc::new(vec![]))))?))
        })),
        ("şifrəAçMətn", f("şifrəAçMətn", 2, Some(3), |_, a, adlı| {
            let n = imza("şifrəAçMətn", a, adlı, &["v", "a", "e"])?;
            let b = şifrə_aç(&al(&n, 0), &al(&n, 1), &var(&n, 2).unwrap_or(D::Bayt(Rc::new(vec![]))))?;
            utf8(b).map(D::str).map_err(|_| x_("açılan məlumat UTF-8 mətn deyil — `şifrəAç` işlədin"))
        })),
        ("təsadüfiBayt", f("təsadüfiBayt", 0, Some(1), move |_, a, adlı| {
            let n = imza("təsadüfiBayt", a, adlı, &["n"])?;
            Ok(bş(təsadüfi_bayt(n_(&n, 0, 32)?)))
        })),
        ("təsadüfiMətn", f("təsadüfiMətn", 0, Some(1), |_, a, adlı| {
            let n = imza("təsadüfiMətn", a, adlı, &["n"])?;
            let k = n_(&n, 0, 32)?;
            Ok(D::str(token_urlsafe(k).chars().take(k).collect()))
        })),
        ("UUID", f("UUID", 0, Some(0), |_, _, _| Ok(D::str(uuid4())))),
        ("bərabərdir", f("bərabərdir", 2, Some(2), |_, a, _| {
            Ok(D::M(sabit_müq(&bayt(&a[0], "bərabərdir")?, &bayt(&a[1], "bərabərdir")?)))
        })),
        ("tokenYarat", f("tokenYarat", 2, Some(2), |i, a, adlı| {
            let n = imza("tokenYarat", a, adlı, &["verilənlər", "açar", "müddət", "alqoritm"])?;
            Ok(D::str(jwt_yarat(i, &n)?))
        })),
        ("tokenOxu", f("tokenOxu", 2, Some(2), |_, a, adlı| {
            let n = imza("tokenOxu", a, adlı, &["token", "açar", "sürüşmə"])?;
            jwt_oxu(&n)
        })),
        ("alqoritmlər", D::siyahı(ALQORİTMLƏR.iter().map(|s| D::s(s)).collect())),
    ])
}
