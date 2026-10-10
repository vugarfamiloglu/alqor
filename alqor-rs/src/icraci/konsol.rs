//! `konsol` modulu (konsol.py).

use super::deyerler::*;
use super::icraci::İcraçı;
use super::kitabxana::arq_al;
use crate::elifba as E;
use indexmap::IndexMap;
use std::cell::{Cell, RefCell};
use std::rc::Rc;

type F = Box<dyn Fn(&İcraçı, Vec<D>, Adlı) -> Nəticə>;

fn d(a: &str, min: usize, maks: Option<usize>, f: F) -> D {
    D::Daxili(Rc::new(Daxili { ad: ad(a), f, min, maks }))
}

const RƏNGLƏR: [(&str, i64); 9] = [
    ("qara", 30), ("qırmızı", 31), ("yaşıl", 32), ("sarı", 33), ("mavi", 34), ("bənövşəyi", 35), ("firuzəyi", 36), ("ağ", 37), ("boz", 90),
];

fn terminaldır() -> bool {
    unsafe { libc::isatty(1) == 1 }
}

fn boya(i: &İcraçı, m: &D, kodlar: &[i64]) -> Nəticə<String> {
    let s = mətnə(i, m)?;
    if kodlar.is_empty() || std::env::var_os("NO_COLOR").is_some_and(|v| !v.is_empty()) {
        return Ok(s);
    }
    let k: Vec<String> = kodlar.iter().map(|x| x.to_string()).collect();
    Ok(format!("\x1b[{}m{}\x1b[0m", k.join(";"), s))
}

fn rəng_kodu(i: &İcraçı, a: &D, sahə: &str) -> Nəticə<i64> {
    let a = E::kiçiyə(&mətnə(i, a)?);
    match RƏNGLƏR.iter().find(|(n, _)| *n == a) {
        Some((_, k)) => Ok(*k),
        None => Err(xəta(
            "ArqumentXətası",
            format!(
                "`{}` {} rəngi yoxdur. İcazəli: {}",
                a,
                sahə,
                RƏNGLƏR.iter().map(|x| x.0).collect::<Vec<_>>().join(", ")
            ),
            "ALQ-R013",
        )),
    }
}

fn oxu(i: &İcraçı, sual: &str) -> Nəticə<String> {
    if !sual.is_empty() {
        i.yaz_xam(sual);
    }
    match i.sətir_oxu() {
        Some(s) => Ok(s),
        None => Err(xəta("GirişÇıxışXətası", "girişin sonu — oxunacaq məlumat qalmadı", "ALQ-R009")),
    }
}

fn seçimlər(d: &D) -> Nəticə<Vec<D>> {
    let l = match d {
        D::Siyahı(l) => l.borrow().clone(),
        D::Kortej(k) => k.to_vec(),
        _ => vec![],
    };
    if l.is_empty() {
        return Err(xəta("ArqumentXətası", "seçimlər boş olmayan siyahı olmalıdır", "ALQ-R013"));
    }
    Ok(l)
}

fn göstər(i: &İcraçı, sual: &D, l: &[D]) -> Nəticə<()> {
    if !sual.boşdur() {
        let s = mətnə(i, sual)?;
        if !s.is_empty() {
            i.yaz(&s);
        }
    }
    for (k, e) in l.iter().enumerate() {
        let s = format!("  {}) {}", k + 1, mətnə(i, e)?);
        i.yaz(&s);
    }
    Ok(())
}

fn rəqəmdir(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_ascii_digit())
}

/// Python `round()` — yarımda cüt
fn yuvarla(x: f64) -> i64 {
    let f = x.floor();
    if x - f == 0.5 {
        if f as i64 % 2 == 0 { f as i64 } else { f as i64 + 1 }
    } else {
        x.round() as i64
    }
}

fn obyekt(tip: &'static str, üzvlər: Vec<(&'static str, D)>, mətn: Option<Box<dyn Fn() -> String>>) -> D {
    D::Obyekt(Rc::new(Obyekt { tip, üzvlər: üzvlər.into_iter().collect::<IndexMap<_, _, Fx>>(), mətn }))
}

struct İrəliləyiş {
    cəmi: Cell<i64>,
    mətn: String,
    cari: Cell<i64>,
    bitib: Cell<bool>,
}

impl İrəliləyiş {
    fn sətir(&self) -> String {
        let n = (self.cari.get() as f64 / self.cəmi.get() as f64).min(1.0);
        let dolu = yuvarla(n * 28.0).clamp(0, 28) as usize;
        let baş = if self.mətn.is_empty() { String::new() } else { format!("{} ", self.mətn) };
        format!("{}{}{} {:>3}% ({}/{})", baş, "█".repeat(dolu), "░".repeat(28 - dolu), yuvarla(n * 100.0), self.cari.get(), self.cəmi.get())
    }
}

fn irəliləyiş(i: &İcraçı, a: Vec<D>, adlı: Adlı) -> Nəticə {
    let cəmi = arq_al(&a, &adlı, 0, "cəmi").and_then(|x| x.onluq()).unwrap_or(1.0) as i64;
    let m = match arq_al(&a, &adlı, 1, "mətn") {
        Some(x) => mətnə(i, &x)?,
        None => String::new(),
    };
    let o = Rc::new(İrəliləyiş { cəmi: Cell::new(cəmi.max(1)), mətn: m, cari: Cell::new(0), bitib: Cell::new(false) });
    let terminal = terminaldır();
    let yenilə = {
        let o = o.clone();
        move |i: &İcraçı, n: i64| {
            o.cari.set(n.clamp(0, o.cəmi.get()));
            if terminal {
                i.yaz_xam(&format!("\r{}", o.sətir()));
            }
        }
    };
    let yenilə = Rc::new(yenilə);
    let (o1, o2, o3, o4, o5) = (o.clone(), o.clone(), o.clone(), o.clone(), o.clone());
    let (y1, y2) = (yenilə.clone(), yenilə.clone());
    let özü: Rc<RefCell<D>> = Rc::new(RefCell::new(D::Boş));
    let (ö1, ö2) = (özü.clone(), özü.clone());
    let ob = obyekt(
        "irəliləyiş",
        vec![
            ("yenilə", d("yenilə", 1, Some(1), Box::new(move |i, a, _| {
                y1(i, a[0].onluq().unwrap_or(0.0) as i64);
                Ok(ö1.borrow().clone())
            }))),
            ("artır", d("artır", 0, Some(1), Box::new(move |i, a, _| {
                let k = a.first().and_then(|x| x.onluq()).unwrap_or(1.0) as i64;
                y2(i, o1.cari.get() + k);
                Ok(ö2.borrow().clone())
            }))),
            ("bitir", d("bitir", 0, Some(1), Box::new(move |i, a, _| {
                if o2.bitib.get() {
                    return Ok(D::Boş);
                }
                o2.bitib.set(true);
                o2.cari.set(o2.cəmi.get());
                if terminal {
                    i.yaz_xam("\r\x1b[K");
                }
                let s = match a.first() {
                    Some(m) if !m.boşdur() => mətnə(i, m)?,
                    _ => o2.sətir(),
                };
                i.yaz(&s);
                Ok(D::Boş)
            }))),
            ("cari", d("cari", 0, Some(0), Box::new(move |_, _, _| Ok(D::T(o3.cari.get()))))),
            ("cəmi", d("cəmi", 0, Some(0), Box::new(move |_, _, _| Ok(D::T(o4.cəmi.get()))))),
            ("mətnƏt", d("mətnƏt", 0, Some(0), Box::new(move |_, _, _| Ok(D::str(o5.sətir()))))),
        ],
        None,
    );
    *özü.borrow_mut() = ob.clone();
    // dövr Rc-ni qırmaq lazım deyil (proqram ömrü qədər yaşayır)
    let _ = i;
    Ok(ob)
}

fn fırlanan(i: &İcraçı, a: Vec<D>, adlı: Adlı) -> Nəticə {
    let m = match arq_al(&a, &adlı, 0, "mətn") {
        Some(x) => mətnə(i, &x)?,
        None => String::new(),
    };
    let mətn = Rc::new(RefCell::new(m));
    let işləyir = Rc::new(Cell::new(true));
    let (m1, m2, i1, i2) = (mətn.clone(), mətn.clone(), işləyir.clone(), işləyir.clone());
    let özü: Rc<RefCell<D>> = Rc::new(RefCell::new(D::Boş));
    let ö = özü.clone();
    let ob = obyekt(
        "fırlanan",
        vec![
            ("mətnDəyiş", d("mətnDəyiş", 1, Some(1), Box::new(move |i, a, _| {
                *m1.borrow_mut() = mətnə(i, &a[0])?;
                Ok(ö.borrow().clone())
            }))),
            ("dayandır", d("dayandır", 0, Some(1), Box::new(move |i, a, _| {
                if !i1.get() {
                    return Ok(D::Boş);
                }
                i1.set(false);
                let s = match a.first() {
                    Some(x) if !x.boşdur() => mətnə(i, x)?,
                    _ => m2.borrow().clone(),
                };
                i.yaz(&s);
                Ok(D::Boş)
            }))),
            ("işləyir", d("işləyir", 0, Some(0), Box::new(move |_, _, _| Ok(D::M(i2.get()))))),
        ],
        None,
    );
    *özü.borrow_mut() = ob.clone();
    Ok(ob)
}

fn ölçü() -> (i64, i64) {
    let env = |k: &str| std::env::var(k).ok().and_then(|v| v.parse::<i64>().ok()).filter(|v| *v > 0);
    let (mut c, mut l) = (env("COLUMNS"), env("LINES"));
    if c.is_none() || l.is_none() {
        let mut w: libc::winsize = unsafe { std::mem::zeroed() };
        if unsafe { libc::ioctl(1, libc::TIOCGWINSZ, &mut w) } == 0 && w.ws_col > 0 {
            c = c.or(Some(w.ws_col as i64));
            l = l.or(Some(w.ws_row as i64));
        }
    }
    (c.unwrap_or(80), l.unwrap_or(24))
}

pub fn modul() -> Rc<Modul> {
    let sadə = |a: &'static str, k: i64| d(a, 1, Some(1), Box::new(move |i, x, _| Ok(D::str(boya(i, &x[0], &[k])?))));
    Modul::yeni("konsol", vec![
        ("qırmızı", sadə("qırmızı", 31)),
        ("yaşıl", sadə("yaşıl", 32)),
        ("sarı", sadə("sarı", 33)),
        ("mavi", sadə("mavi", 34)),
        ("boz", sadə("boz", 90)),
        ("qalın", sadə("qalın", 1)),
        ("altXətt", sadə("altXətt", 4)),
        ("rəng", d("rəng", 1, Some(4), Box::new(|i, a, adlı| {
            let m = arq_al(&a, &adlı, 0, "mətn").unwrap_or(D::Boş);
            let ön = arq_al(&a, &adlı, 1, "ön").filter(|x| !x.boşdur());
            let arxa = arq_al(&a, &adlı, 2, "arxa").filter(|x| !x.boşdur());
            let qalın = arq_al(&a, &adlı, 3, "qalın").map(|x| super::eded::doğrudur(&x)).unwrap_or(false);
            let mut k = vec![];
            if qalın {
                k.push(1);
            }
            if let Some(ö) = ön {
                k.push(rəng_kodu(i, &ö, "ön")?);
            }
            if let Some(x) = arxa {
                k.push(rəng_kodu(i, &x, "arxa")? + 10);
            }
            Ok(D::str(boya(i, &m, &k)?))
        }))),
        ("təmizlə", d("təmizlə", 0, Some(0), Box::new(|i, _, _| {
            if terminaldır() {
                i.yaz_xam("\x1b[2J\x1b[H");
            }
            Ok(D::Boş)
        }))),
        ("kursor", d("kursor", 1, Some(2), Box::new(|i, a, _| {
            if terminaldır() {
                let s = a[0].onluq().unwrap_or(1.0) as i64;
                let c = a.get(1).and_then(|x| x.onluq()).unwrap_or(1.0) as i64;
                i.yaz_xam(&format!("\x1b[{};{}H", s, c));
            }
            Ok(D::Boş)
        }))),
        ("ölçü", d("ölçü", 0, Some(0), Box::new(|_, _, _| {
            let (c, l) = ölçü();
            Ok(D::kortej(vec![D::T(c), D::T(l)]))
        }))),
        ("terminaldır", d("terminaldır", 0, Some(0), Box::new(|_, _, _| Ok(D::M(terminaldır()))))),
        ("soruş", d("soruş", 0, Some(2), Box::new(|i, a, adlı| {
            let sual = arq_al(&a, &adlı, 0, "sual").unwrap_or(D::s(""));
            let st = arq_al(&a, &adlı, 1, "standart").filter(|x| !x.boşdur());
            let mut s = mətnə(i, &sual)?;
            if let Some(st) = &st {
                let m = mətnə(i, st)?;
                s = if s.is_empty() { format!("[{}] ", m) } else { format!("{}[{}] ", s, m) };
            }
            let c = oxu(i, &s)?;
            if c.trim().is_empty() {
                if let Some(st) = &st {
                    return Ok(D::str(mətnə(i, st)?));
                }
            }
            Ok(D::str(c))
        }))),
        ("parolSoruş", d("parolSoruş", 0, Some(1), Box::new(|i, a, adlı| {
            let s = match arq_al(&a, &adlı, 0, "sual") {
                Some(x) => mətnə(i, &x)?,
                None => "Parol: ".into(),
            };
            Ok(D::str(oxu(i, &s)?))
        }))),
        ("təsdiqlə", d("təsdiqlə", 1, Some(2), Box::new(|i, a, adlı| {
            let sual = mətnə(i, &arq_al(&a, &adlı, 0, "sual").unwrap_or(D::Boş))?;
            let st = arq_al(&a, &adlı, 1, "standart").filter(|x| !x.boşdur());
            let ipucu = match &st {
                None => "(hə/yox)",
                Some(x) if super::eded::doğrudur(x) => "(HƏ/yox)",
                _ => "(hə/YOX)",
            };
            loop {
                let c = E::kiçiyə(oxu(i, &format!("{} {} ", sual, ipucu))?.trim());
                if c.is_empty() {
                    if let Some(st) = &st {
                        return Ok(D::M(super::eded::doğrudur(st)));
                    }
                }
                if ["hə", "he", "bəli", "beli", "h", "b", "doğru", "dogru"].contains(&c.as_str()) {
                    return Ok(D::M(true));
                }
                if ["yox", "xeyr", "y", "x", "yanlış", "yanlis"].contains(&c.as_str()) {
                    return Ok(D::M(false));
                }
                i.yaz("`hə` və ya `yox` yazın.");
            }
        }))),
        ("seç", d("seç", 2, Some(2), Box::new(|i, a, _| {
            let l = seçimlər(&a[1])?;
            göstər(i, &a[0], &l)?;
            loop {
                let c = oxu(i, &format!("Seçin (1–{}): ", l.len()))?;
                let c = c.trim();
                if rəqəmdir(c) {
                    if let Ok(n) = c.parse::<usize>() {
                        if n >= 1 && n <= l.len() {
                            return Ok(l[n - 1].clone());
                        }
                    }
                }
                for e in &l {
                    if !c.is_empty() && E::kiçiyə(&mətnə(i, e)?) == E::kiçiyə(c) {
                        return Ok(e.clone());
                    }
                }
                i.yaz(&format!("1 ilə {} arasında nömrə yazın.", l.len()));
            }
        }))),
        ("çoxSeç", d("çoxSeç", 2, Some(2), Box::new(|i, a, _| {
            let l = seçimlər(&a[1])?;
            göstər(i, &a[0], &l)?;
            loop {
                let c = oxu(i, "Nömrələr (məs. 1,3; boş — heç biri): ")?;
                let c = c.trim();
                if c.is_empty() {
                    return Ok(D::siyahı(vec![]));
                }
                let h: Vec<String> = c.replace(',', " ").split_whitespace().map(|s| s.to_string()).collect();
                if h.iter().all(|x| rəqəmdir(x) && x.parse::<usize>().map(|n| n >= 1 && n <= l.len()).unwrap_or(false)) {
                    let mut g: Vec<usize> = vec![];
                    for x in &h {
                        let n: usize = x.parse().unwrap();
                        if !g.contains(&n) {
                            g.push(n);
                        }
                    }
                    return Ok(D::siyahı(g.into_iter().map(|n| l[n - 1].clone()).collect()));
                }
                i.yaz(&format!("1 ilə {} arasında nömrələr yazın.", l.len()));
            }
        }))),
        ("cədvəl", d("cədvəl", 2, Some(2), Box::new(|i, a, _| {
            let mut hamısı: Vec<Vec<String>> = vec![];
            let mut b = vec![];
            for x in i.siyahıya(&a[0], None)? {
                b.push(mətnə(i, &x)?);
            }
            hamısı.push(b);
            for s in i.siyahıya(&a[1], None)? {
                let mut r = vec![];
                for x in i.siyahıya(&s, None)? {
                    r.push(mətnə(i, &x)?);
                }
                hamısı.push(r);
            }
            let say = hamısı.iter().map(|r| r.len()).max().unwrap_or(0);
            for r in hamısı.iter_mut() {
                r.resize(say, String::new());
            }
            let en: Vec<usize> = (0..say).map(|k| hamısı.iter().map(|r| r[k].chars().count()).max().unwrap_or(0)).collect();
            for (j, r) in hamısı.iter().enumerate() {
                let s: Vec<String> = r.iter().zip(&en).map(|(h, e)| format!("{}{}", h, " ".repeat(e - h.chars().count()))).collect();
                i.yaz(s.join(" │ ").trim_end());
                if j == 0 {
                    i.yaz(&en.iter().map(|e| "─".repeat(*e)).collect::<Vec<_>>().join("─┼─"));
                }
            }
            Ok(D::Boş)
        }))),
        ("irəliləyiş", d("irəliləyiş", 1, Some(2), Box::new(irəliləyiş))),
        ("fırlanan", d("fırlanan", 0, Some(1), Box::new(fırlanan))),
        ("arqumentlər", d("arqumentlər", 0, Some(0), Box::new(|_, _, _| {
            Err(xəta("ArqumentXətası", "`konsol.arqumentlər` hələ dəstəklənmir", "ALQ-M002"))
        }))),
    ])
}
