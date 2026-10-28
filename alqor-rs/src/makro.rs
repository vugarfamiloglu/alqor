//! Makrolar (spes. § 5.12) — token səviyyəsində açılış.
//!
//! `alqorc/alqor/makro.py`-nin tam təkrarı: hər iki parser eyni tokenləri
//! və eyni AAC-ni qurmalıdır.

use crate::lekser::{Növ, Parça, Token};
use crate::xeta::Yer;
use std::collections::{BTreeSet, HashMap, HashSet};

/// Bir faylda açılışların həddi — özünü çağıran makrolara qarşı
pub const AÇILIŞ_HƏDDİ: usize = 10000;

const ELAN_SÖZLƏRİ: &[&str] = &["dəyişən", "sabit", "dəyişməz"];

#[derive(Clone, Debug)]
pub struct Makro {
    pub ad: String,
    pub parametrlər: Vec<String>,
    /// `iş: blok` — blok parametrinin adı
    pub blok: Option<String>,
    /// `makro ad(x) = ifadə`
    pub ifadədir: bool,
    pub tokenlər: Vec<Token>,
    pub yerlilər: BTreeSet<String>,
    pub yer: Yer,
}

#[derive(Default, Debug)]
pub struct MakroVəziyyəti {
    pub makrolar: HashMap<String, Makro>,
    pub açılış: usize,
    /// `gətir "fayl.alq"` ilə oxunmuş fayllar (dövri idxala qarşı)
    pub oxunmuş: HashSet<String>,
}

pub struct MakroXətası {
    pub kod: &'static str,
    pub mesaj: String,
    pub yer: Yer,
    pub qeyd: String,
    pub köməklər: Vec<String>,
}

fn sətir_sonudur(t: Option<&Token>) -> bool {
    match t {
        None => true,
        Some(t) => matches!(t.növ, Növ::SətirSonu | Növ::FaylSonu),
    }
}

/// Gövdədə elan olunan adlar: `dəyişən a, b`, `hər x üçün`, `tut (x)`,
/// `funksiya f`.
pub fn yerli_adlar(t: &[Token]) -> BTreeSet<String> {
    let n = t.len();
    let mut adlar = BTreeSet::new();
    for i in 0..n {
        if t[i].növ != Növ::Acar {
            continue;
        }
        let s = t[i].s.as_str();
        if ELAN_SÖZLƏRİ.contains(&s) {
            let mut j = i + 1;
            while j < n && !sətir_sonudur(Some(&t[j])) && !t[j].opdur(&["="]) {
                if t[j].növ == Növ::Ad && (j == i + 1 || t[j - 1].opdur(&[",", "(", "["])) {
                    adlar.insert(t[j].s.clone());
                }
                j += 1;
            }
        } else if s == "hər" {
            let mut j = i + 1;
            while j < n && !sətir_sonudur(Some(&t[j])) && !t[j].acardır(&["üçün"]) {
                if t[j].növ == Növ::Ad && (j == i + 1 || t[j - 1].opdur(&[",", "("])) {
                    adlar.insert(t[j].s.clone());
                }
                j += 1;
            }
        } else if s == "tut" {
            let mut j = i + 1;
            if j < n && t[j].opdur(&["("]) {
                j += 1;
            }
            if j < n && t[j].növ == Növ::Ad {
                adlar.insert(t[j].s.clone());
            }
        } else if s == "funksiya" && i + 1 < n && t[i + 1].növ == Növ::Ad {
            adlar.insert(t[i + 1].s.clone());
        }
    }
    adlar
}

fn op(s: &str, yer: Yer) -> Token {
    let mut t = Token::yeni(Növ::Op, s, yer);
    t.xam = s.to_string();
    t
}

/// Gövdə tokenlərində parametrləri və yerli adları dəyişdirir.
fn əvəzlə(
    m: &Makro,
    t: &[Token],
    arqumentlər: &HashMap<&str, &Vec<Token>>,
    adlar: &HashMap<String, String>,
    blok: Option<&Vec<Token>>,
) -> Result<Vec<Token>, MakroXətası> {
    let mut n = Vec::with_capacity(t.len());
    for k in 0..t.len() {
        let x = &t[k];
        let əv = if k > 0 { Some(&t[k - 1]) } else { None };
        let nö = t.get(k + 1);
        if x.növ == Növ::Ad && !əv.is_some_and(|e| e.opdur(&[".", "?."])) {
            // Adlı arqumentin etiketi: `f(ad: …)`
            let etiket = nö.is_some_and(|z| z.opdur(&[":"])) && əv.is_some_and(|e| e.opdur(&["(", ","]));
            if m.blok.as_deref() == Some(x.s.as_str()) {
                if !(sətir_sonudur(əv) && sətir_sonudur(nö)) {
                    return Err(MakroXətası {
                        kod: "ALQ-P035",
                        mesaj: "Blok parametri yalnız ayrıca sətirdə işlənə bilər".into(),
                        yer: x.yer,
                        qeyd: format!("`{}` cümlə kimi yazılmalıdır", x.s),
                        köməklər: vec![format!("`{}` sətrində başqa heç nə olmasın", x.s)],
                    });
                }
                if let Some(b) = blok {
                    n.extend(b.iter().cloned());
                }
                continue;
            }
            if !etiket {
                if let Some(arq) = arqumentlər.get(x.s.as_str()) {
                    if arq.len() == 1 {
                        n.push(arq[0].clone());
                    } else {
                        n.push(op("(", x.yer));
                        n.extend(arq.iter().cloned());
                        n.push(op(")", x.yer));
                    }
                    continue;
                }
                if let Some(yeni) = adlar.get(&x.s) {
                    let mut y = x.clone();
                    y.s = yeni.clone();
                    n.push(y);
                    continue;
                }
            }
        }
        if x.növ == Növ::Mətn {
            if let Some(p) = &x.parçalar {
                if p.iter().any(|q| matches!(q, Parça::Kod(..))) {
                    let mut parçalar = Vec::with_capacity(p.len());
                    for q in p {
                        parçalar.push(match q {
                            Parça::Kod(tk, f) => Parça::Kod(əvəzlə(m, tk, arqumentlər, adlar, None)?, f.clone()),
                            q => q.clone(),
                        });
                    }
                    let mut y = x.clone();
                    y.parçalar = Some(parçalar);
                    n.push(y);
                    continue;
                }
            }
        }
        n.push(x.clone());
    }
    Ok(n)
}

/// Bir çağırışın açılmış tokenləri.
pub fn aç(m: &Makro, arqumentlər: &[Vec<Token>], blok: Option<&Vec<Token>>, yer: Yer, nömrə: usize) -> Result<Vec<Token>, MakroXətası> {
    if arqumentlər.len() != m.parametrlər.len() {
        return Err(MakroXətası {
            kod: "ALQ-P033",
            mesaj: "Makro arqumentlərinin sayı uyğun deyil".into(),
            yer,
            qeyd: format!("`{}!` {} arqument gözləyir, {} verilib", m.ad, m.parametrlər.len(), arqumentlər.len()),
            köməklər: vec![],
        });
    }
    let adlar: HashMap<String, String> = m
        .yerlilər
        .iter()
        .filter(|a| !m.parametrlər.contains(a) && m.blok.as_deref() != Some(a.as_str()))
        .map(|a| (a.clone(), format!("{}$m{}", a, nömrə)))
        .collect();
    let arq: HashMap<&str, &Vec<Token>> = m.parametrlər.iter().map(|s| s.as_str()).zip(arqumentlər.iter()).collect();
    let gövdə = əvəzlə(m, &m.tokenlər, &arq, &adlar, blok)?;
    if m.ifadədir {
        let mut v = vec![op("(", yer)];
        v.extend(gövdə);
        v.push(op(")", yer));
        return Ok(v);
    }
    // Cümlə makrosu: baş və sondakı boş sətirlər atılır
    let (mut b, mut s) = (0, gövdə.len());
    while b < s && gövdə[b].növ == Növ::SətirSonu {
        b += 1;
    }
    while s > b && gövdə[s - 1].növ == Növ::SətirSonu {
        s -= 1;
    }
    if b == s {
        let mut k = Token::yeni(Növ::Acar, "keç", yer);
        k.xam = "keç".into();
        return Ok(vec![k]);
    }
    Ok(gövdə[b..s].to_vec())
}
