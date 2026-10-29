//! Ölçü vahidləri (spes. § 3.8) — `alqorc/alqor/vahidler.py`-nin təkrarı.
//!
//! Kəmiyyət = ədəd + vahid; kitabxana obyekti (`kəmiyyət`) kimi saxlanılır.

use super::deyerler::*;
use super::elave::{obyekt, veri};
use super::icraci::İcraçı;
use crate::xeta::Yer;
use std::rc::Rc;

/// ad → (SI əmsalı, ölçü: uzunluq, kütlə, vaxt, verilənlər)
pub const VAHİDLƏR: &[(&str, f64, [i32; 4])] = &[
    ("mm", 0.001, [1, 0, 0, 0]),
    ("sm", 0.01, [1, 0, 0, 0]),
    ("dm", 0.1, [1, 0, 0, 0]),
    ("m", 1.0, [1, 0, 0, 0]),
    ("km", 1000.0, [1, 0, 0, 0]),
    ("düym", 0.0254, [1, 0, 0, 0]),
    ("fut", 0.3048, [1, 0, 0, 0]),
    ("mil", 1609.344, [1, 0, 0, 0]),
    ("ha", 10000.0, [2, 0, 0, 0]),
    ("ml", 0.000001, [3, 0, 0, 0]),
    ("l", 0.001, [3, 0, 0, 0]),
    ("mq", 0.000001, [0, 1, 0, 0]),
    ("q", 0.001, [0, 1, 0, 0]),
    ("kq", 1.0, [0, 1, 0, 0]),
    ("ton", 1000.0, [0, 1, 0, 0]),
    ("ms", 0.001, [0, 0, 1, 0]),
    ("san", 1.0, [0, 0, 1, 0]),
    ("dəq", 60.0, [0, 0, 1, 0]),
    ("saat", 3600.0, [0, 0, 1, 0]),
    ("gün", 86400.0, [0, 0, 1, 0]),
    ("həftə", 604800.0, [0, 0, 1, 0]),
    ("B", 1.0, [0, 0, 0, 1]),
    ("KB", 1024.0, [0, 0, 0, 1]),
    ("MB", 1048576.0, [0, 0, 0, 1]),
    ("GB", 1073741824.0, [0, 0, 0, 1]),
    ("TB", 1099511627776.0, [0, 0, 0, 1]),
];

const ÜST: [(char, char); 11] = [
    ('0', '⁰'), ('1', '¹'), ('2', '²'), ('3', '³'), ('4', '⁴'), ('5', '⁵'),
    ('6', '⁶'), ('7', '⁷'), ('8', '⁸'), ('9', '⁹'), ('-', '⁻'),
];

fn tap(ad: &str) -> Option<&'static (&'static str, f64, [i32; 4])> {
    VAHİDLƏR.iter().find(|v| v.0 == ad)
}

pub fn vahiddir(ad: &str) -> bool {
    tap(ad).is_some()
}

#[derive(Clone, Debug, Default)]
pub struct Vahid {
    pub hissələr: Vec<(String, i32)>,
}

impl Vahid {
    /// Hissələri toplayır: eyni ad — qüvvətlər cəmlənir (sıra ilk
    /// görünməyə görə), sıfır qüvvətlər atılır.
    pub fn birləşdir(siyahılar: &[&[(String, i32)]]) -> Vahid {
        let mut sıra: Vec<(String, i32)> = vec![];
        for s in siyahılar {
            for (a, n) in s.iter() {
                match sıra.iter_mut().find(|x| &x.0 == a) {
                    Some(x) => x.1 += n,
                    None => sıra.push((a.clone(), *n)),
                }
            }
        }
        Vahid { hissələr: sıra.into_iter().filter(|x| x.1 != 0).collect() }
    }

    pub fn qüvvət(&self, n: i32) -> Vahid {
        let h: Vec<(String, i32)> = self.hissələr.iter().map(|(a, k)| (a.clone(), k * n)).collect();
        Vahid::birləşdir(&[&h])
    }

    pub fn əmsal(&self) -> f64 {
        let mut e = 1.0f64;
        for (a, n) in &self.hissələr {
            e *= tap(a).unwrap().1.powf(*n as f64);
        }
        e
    }

    pub fn ölçü(&self) -> [i32; 4] {
        let mut ö = [0; 4];
        for (a, n) in &self.hissələr {
            for (i, x) in tap(a).unwrap().2.iter().enumerate() {
                ö[i] += x * n;
            }
        }
        ö
    }

    pub fn boşdur(&self) -> bool {
        self.hissələr.is_empty()
    }

    pub fn mətn(&self) -> String {
        fn yaz(a: &str, n: i32) -> String {
            if n == 1 {
                return a.to_string();
            }
            let üst: String = n
                .to_string()
                .chars()
                .map(|c| ÜST.iter().find(|x| x.0 == c).map(|x| x.1).unwrap_or(c))
                .collect();
            format!("{}{}", a, üst)
        }
        let surət: Vec<String> = self.hissələr.iter().filter(|x| x.1 > 0).map(|(a, n)| yaz(a, *n)).collect();
        let məxrəc: Vec<String> = self.hissələr.iter().filter(|x| x.1 < 0).map(|(a, n)| yaz(a, -n)).collect();
        let mut s = surət.join("·");
        if s.is_empty() && !məxrəc.is_empty() {
            s = "1".into();
        }
        if !məxrəc.is_empty() {
            s.push('/');
            s.push_str(&məxrəc.join("·"));
        }
        s
    }
}

/// `"km/saat"`, `"m/san²"`, `"kq·m"` → `Vahid`
pub fn təhlil_et(mətn: &str) -> Result<Vahid, String> {
    let s: String = mətn.chars().filter(|c| *c != ' ').collect();
    if s.is_empty() {
        return Err("vahid boşdur".into());
    }
    let mut hissələr: Vec<(String, i32)> = vec![];
    for (i, qisim) in s.split('/').enumerate() {
        if i > 1 {
            return Err(format!("`{}` — yalnız bir `/` ola bilər", mətn));
        }
        if qisim == "1" && i == 0 {
            continue;
        }
        let qisim = qisim.replace('*', "·");
        for p in qisim.split('·') {
            let mut ad: Vec<char> = p.chars().collect();
            let mut üst = String::new();
            while let Some(c) = ad.last() {
                match ÜST.iter().find(|x| x.1 == *c) {
                    Some(x) => {
                        üst.insert(0, x.0);
                        ad.pop();
                    }
                    None => break,
                }
            }
            let mut ad: String = ad.into_iter().collect();
            if let Some(k) = ad.find('^') {
                üst = ad[k + 1..].to_string();
                ad.truncate(k);
            }
            if !vahiddir(&ad) {
                return Err(format!("`{}` naməlum vahiddir", ad));
            }
            let n: i32 = if üst.is_empty() {
                1
            } else {
                üst.parse().map_err(|_| format!("`{}` — qüvvət tam ədəd olmalıdır", p))?
            };
            hissələr.push((ad, if i == 1 { -n } else { n }));
        }
    }
    Ok(Vahid::birləşdir(&[&hissələr]))
}

pub struct Kəmiyyət {
    pub dəyər: D,
    pub vahid: Vahid,
}

fn ədəd_mətni(d: &D) -> String {
    match d {
        D::O(f) => onluq_mətn(*f),
        D::T(n) => n.to_string(),
        D::BT(n) => n.to_string(),
        D::M(true) => "doğru".into(),
        D::M(false) => "yanlış".into(),
        _ => String::new(),
    }
}

pub fn kəmiyyət(d: &D) -> Option<Rc<Kəmiyyət>> {
    veri::<Kəmiyyət>(d)
}

/// Kəmiyyət dəyəri (vahidsiz nəticə adi ədəd olur)
pub fn yarat(dəyər: D, vahid: Vahid) -> D {
    if vahid.boşdur() {
        return dəyər;
    }
    obyekt(
        "kəmiyyət",
        Rc::new(Kəmiyyət { dəyər, vahid }),
        |k| format!("{} {}", ədəd_mətni(&k.dəyər), k.vahid.mətn()),
        |_, k| {
            let k1 = k.clone();
            let k2 = k.clone();
            let k3 = k.clone();
            vec![
                ("dəyər", daxili("dəyər", 0, Some(0), move |_, _, _| Ok(k1.dəyər.clone()))),
                ("vahid", daxili("vahid", 0, Some(0), move |_, _, _| Ok(D::s(&k2.vahid.mətn())))),
                (
                    "çevir",
                    daxili("çevir", 1, Some(1), move |i, a, _| {
                        let h = match &a[0] {
                            D::S(s) => s.to_string(),
                            x => return Err(xəta("TipXətası", format!("vahid mətn olmalıdır, `{}` gəlib", tip_adı(x)), "ALQ-T084")),
                        };
                        i.kəmiyyəti_çevir(&yarat_məcburi(k3.dəyər.clone(), k3.vahid.clone()), &h, None)
                    }),
                ),
            ]
        },
    )
}

fn yarat_məcburi(dəyər: D, vahid: Vahid) -> D {
    yarat(dəyər, vahid)
}

/// `mənbə`-dəki dəyəri `hədəf`-ə çevirən vurğu (eyni vahid — `None`)
fn nisbət(mənbə: &Vahid, hədəf: &Vahid) -> Option<f64> {
    if mənbə.mətn() == hədəf.mətn() {
        return None;
    }
    Some(mənbə.əmsal() / hədəf.əmsal())
}

fn vahid_xətası(mesaj: String, yer: Option<Yer>) -> Siqnal {
    xəta_yer("VahidXətası", mesaj, yer, "ALQ-T084")
}

fn əməl_adı(op: &str) -> Option<&'static str> {
    Some(match op {
        "+" => "toplanmır",
        "-" => "çıxılmır",
        "%" => "bölünmür",
        "<" | ">" | "<=" | ">=" | "<=>" => "müqayisə olunmur",
        _ => return None,
    })
}

impl İcraçı {
    pub fn e_vahidli_ədəd(&self, d: D, vahid: &str, yer: Yer) -> Nəticə {
        let v = təhlil_et(vahid).map_err(|m| vahid_xətası(m, Some(yer)))?;
        Ok(yarat(d, v))
    }

    pub fn kəmiyyət_var(a: &D, b: &D) -> bool {
        matches!(a, D::Obyekt(o) if o.tip == "kəmiyyət") || matches!(b, D::Obyekt(o) if o.tip == "kəmiyyət")
    }

    pub fn kəmiyyət_hesabla(&self, op: &str, a: &D, b: &D, yer: Option<Yer>) -> Nəticə {
        let ka = kəmiyyət(a);
        let kb = kəmiyyət(b);
        let va = ka.as_ref().map(|k| k.vahid.clone()).unwrap_or_default();
        let vb = kb.as_ref().map(|k| k.vahid.clone()).unwrap_or_default();
        let ad_ = |v: &Vahid| {
            let s = v.mətn();
            if s.is_empty() {
                "ədəd".to_string()
            } else {
                s
            }
        };
        if let Some(ə) = əməl_adı(op) {
            let (Some(ka), Some(kb)) = (&ka, &kb) else {
                return Err(vahid_xətası(format!("`{}` və `{}` {} — ölçülər uyğun deyil", ad_(&va), ad_(&vb), ə), yer));
            };
            if va.ölçü() != vb.ölçü() {
                return Err(vahid_xətası(format!("`{}` və `{}` {} — ölçülər uyğun deyil", ad_(&va), ad_(&vb), ə), yer));
            }
            let bd = match nisbət(&vb, &va) {
                None => kb.dəyər.clone(),
                Some(r) => self.ikili_hesabla("*", &kb.dəyər, &D::O(r), yer)?,
            };
            let n = self.ikili_hesabla(op, &ka.dəyər, &bd, yer)?;
            return Ok(if op.starts_with('<') || op.starts_with('>') { n } else { yarat(n, va) });
        }
        let dəyər = |k: &Option<Rc<Kəmiyyət>>, x: &D| k.as_ref().map(|k| k.dəyər.clone()).unwrap_or_else(|| x.clone());
        match op {
            "*" => {
                let n = self.ikili_hesabla("*", &dəyər(&ka, a), &dəyər(&kb, b), yer)?;
                self.kəmiyyət_sadələşdir(n, Vahid::birləşdir(&[&va.hissələr, &vb.hissələr]))
            }
            "/" => {
                let n = self.ikili_hesabla("/", &dəyər(&ka, a), &dəyər(&kb, b), yer)?;
                let tərs = vb.qüvvət(-1);
                self.kəmiyyət_sadələşdir(n, Vahid::birləşdir(&[&va.hissələr, &tərs.hissələr]))
            }
            "**" if ka.is_some() && kb.is_none() && matches!(b, D::T(_)) => {
                let D::T(k) = b else { unreachable!() };
                let n = self.ikili_hesabla("**", &dəyər(&ka, a), b, yer)?;
                self.kəmiyyət_sadələşdir(n, va.qüvvət(*k as i32))
            }
            _ => Err(vahid_xətası(
                format!("`{}` operatoru `{}` və `{}` üçün tətbiq edilmir", op, tip_adı(a), tip_adı(b)),
                yer,
            )),
        }
    }

    /// Ölçüsüz nəticə adi ədəd olur (`km/m` → ×1000)
    fn kəmiyyət_sadələşdir(&self, n: D, v: Vahid) -> Nəticə {
        if v.boşdur() {
            return Ok(n);
        }
        if v.ölçü().iter().all(|x| *x == 0) {
            return self.ikili_hesabla("*", &n, &D::O(v.əmsal()), None);
        }
        Ok(yarat(n, v))
    }

    pub fn kəmiyyət_bərabər(a: &D, b: &D) -> bool {
        match (kəmiyyət(a), kəmiyyət(b)) {
            (Some(x), Some(y)) if x.vahid.ölçü() == y.vahid.ölçü() => {
                let si = |k: &Kəmiyyət| match &k.dəyər {
                    D::T(n) => *n as f64,
                    D::O(f) => *f,
                    D::M(m) => *m as i64 as f64,
                    D::BT(b) => {
                        use num_traits::ToPrimitive;
                        b.to_f64().unwrap_or(f64::NAN)
                    }
                    _ => f64::NAN,
                } * k.vahid.əmsal();
                si(&x) == si(&y)
            }
            _ => false,
        }
    }

    /// `x kimi m`, `x.çevir("km/saat")`; ədəd → kəmiyyət
    pub fn kəmiyyəti_çevir(&self, d: &D, hədəf: &str, yer: Option<Yer>) -> Nəticə {
        let v = təhlil_et(hədəf).map_err(|m| vahid_xətası(m, yer))?;
        let Some(k) = kəmiyyət(d) else {
            if !d.ədəddir() {
                return Err(vahid_xətası(format!("`{}` vahidə çevrilmir", tip_adı(d)), yer));
            }
            return Ok(obyekt_yarat(d.clone(), v));
        };
        if k.vahid.ölçü() != v.ölçü() {
            return Err(vahid_xətası(
                format!("`{}` `{}` vahidinə çevrilmir — ölçülər uyğun deyil", k.vahid.mətn(), v.mətn()),
                yer,
            ));
        }
        let n = match nisbət(&k.vahid, &v) {
            None => k.dəyər.clone(),
            Some(r) => self.ikili_hesabla("*", &k.dəyər, &D::O(r), yer)?,
        };
        Ok(obyekt_yarat(n, v))
    }
}

/// Vahidi boş olmayan kəmiyyət (çevirmədə vahid həmişə var)
fn obyekt_yarat(n: D, v: Vahid) -> D {
    yarat(n, v)
}
