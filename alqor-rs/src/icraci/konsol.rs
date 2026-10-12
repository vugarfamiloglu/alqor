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
    super::platforma::terminaldır()
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
        if let Some((x, y)) = super::platforma::terminal_ölçüsü() {
            c = c.or(Some(x));
            l = l.or(Some(y));
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
        ("arqumentlər", d("arqumentlər", 0, Some(0), Box::new(|i, _, _| Ok(arqumentlər(i))))),
    ])
}

// ── konsol.arqumentlər() — zəncirlənən təhlilçi ────────────────────────

struct ArqParametr {
    ad: String,
    izah: String,
    çoxlu: bool,
    ixtiyari: bool,
}

struct ArqSeçim {
    uzun: String,
    qısa: String,
    izah: String,
    standart: Option<String>,
    bayraqdır: bool,
}

impl ArqSeçim {
    fn ad(&self) -> String {
        self.uzun.trim_start_matches('-').to_string()
    }
}

#[derive(Default)]
struct ArqVəziyyət {
    proqram: String,
    versiya: String,
    təsvir: String,
    parametrlər: Vec<ArqParametr>,
    seçimlər: Vec<ArqSeçim>,
}

impl ArqVəziyyət {
    fn istifadə(&self) -> String {
        let mut h = vec![self.proqram.clone()];
        if !self.seçimlər.is_empty() {
            h.push("[SEÇİMLƏR]".into());
        }
        for p in &self.parametrlər {
            let a = format!("<{}>{}", p.ad, if p.çoxlu { "..." } else { "" });
            h.push(if p.ixtiyari { format!("[{a}]") } else { a });
        }
        h.join(" ")
    }
    fn kömək(&self) -> String {
        let sol_düz = |s: &str, en: usize| format!("{}{}", s, " ".repeat(en.saturating_sub(s.chars().count())));
        let mut s = vec![];
        s.push(if self.versiya.is_empty() { self.proqram.clone() } else { format!("{} {}", self.proqram, self.versiya) });
        if !self.təsvir.is_empty() {
            s.push(self.təsvir.clone());
        }
        s.push(String::new());
        s.push("İSTİFADƏ:".into());
        s.push(format!("    {}", self.istifadə()));
        if !self.parametrlər.is_empty() {
            s.push(String::new());
            s.push("ARQUMENTLƏR:".into());
            let adlar: Vec<String> =
                self.parametrlər.iter().map(|p| format!("<{}>{}", p.ad, if p.çoxlu { "..." } else { "" })).collect();
            let en = adlar.iter().map(|a| a.chars().count()).max().unwrap_or(0);
            for (a, p) in adlar.iter().zip(&self.parametrlər) {
                s.push(format!("    {}  {}", sol_düz(a, en), p.izah).trim_end().to_string());
            }
        }
        s.push(String::new());
        s.push("SEÇİMLƏR:".into());
        let daxili = |o: &ArqSeçim| o.uzun == "--kömək" || o.uzun == "--versiya";
        let sıra: Vec<&ArqSeçim> =
            self.seçimlər.iter().filter(|o| !daxili(o)).chain(self.seçimlər.iter().filter(|o| daxili(o))).collect();
        let sol: Vec<String> = sıra
            .iter()
            .map(|o| {
                let mut a = if o.qısa.is_empty() { format!("    {}", o.uzun) } else { format!("{}, {}", o.qısa, o.uzun) };
                if !o.bayraqdır {
                    a += &format!(" <{}>", E::böyüyə(&o.ad()));
                }
                a
            })
            .collect();
        let en = sol.iter().map(|a| a.chars().count()).max().unwrap_or(0);
        for (a, o) in sol.iter().zip(&sıra) {
            let mut izah = o.izah.clone();
            if let Some(st) = &o.standart {
                izah += &format!(" [standart: {st}]");
            }
            s.push(format!("    {}  {}", sol_düz(a, en), izah).trim_end().to_string());
        }
        s.join("\n")
    }
    fn tap(&self, ad: &str) -> Option<&ArqSeçim> {
        self.seçimlər.iter().find(|o| ad == o.uzun || (!o.qısa.is_empty() && ad == o.qısa))
    }
}

enum TəhlilXətası {
    Arq(String),
    Siqnal(Siqnal),
}

fn arq_təhlil(i: &İcraçı, v: &ArqVəziyyət, xam: &[String]) -> Result<D, TəhlilXətası> {
    let mut dəyərlər: IndexMap<String, D> = IndexMap::new();
    let mut bayraqlar: Vec<String> = vec![];
    let mut mövqeli: Vec<String> = vec![];
    let mut k = 0;
    let mut yalnız = false;
    while k < xam.len() {
        let a = &xam[k];
        k += 1;
        if yalnız || !a.starts_with('-') || a == "-" {
            mövqeli.push(a.clone());
            continue;
        }
        if a == "--" {
            yalnız = true;
            continue;
        }
        let (ad_, bərabər, dəyər) = match a.split_once('=') {
            Some((x, y)) => (x.to_string(), true, y.to_string()),
            None => (a.clone(), false, String::new()),
        };
        let Some(o) = v.tap(&ad_) else { return Err(TəhlilXətası::Arq(format!("naməlum seçim `{ad_}`"))) };
        if o.uzun == "--kömək" {
            i.yaz(&v.kömək());
            return Err(TəhlilXətası::Siqnal(Siqnal::Dayanma(D::T(0))));
        }
        if o.uzun == "--versiya" {
            i.yaz(&format!("{} {}", v.proqram, v.versiya));
            return Err(TəhlilXətası::Siqnal(Siqnal::Dayanma(D::T(0))));
        }
        if o.bayraqdır {
            if bərabər {
                return Err(TəhlilXətası::Arq(format!("`{}` dəyər qəbul etmir", o.uzun)));
            }
            if !bayraqlar.contains(&o.ad()) {
                bayraqlar.push(o.ad());
            }
            continue;
        }
        let dəyər = if bərabər {
            dəyər
        } else {
            if k >= xam.len() {
                return Err(TəhlilXətası::Arq(format!("`{}` üçün dəyər lazımdır", o.uzun)));
            }
            k += 1;
            xam[k - 1].clone()
        };
        dəyərlər.insert(o.ad(), D::str(dəyər));
    }
    for o in &v.seçimlər {
        if !o.bayraqdır && !dəyərlər.contains_key(&o.ad()) {
            if let Some(st) = &o.standart {
                dəyərlər.insert(o.ad(), D::s(st));
            }
        }
    }
    for p in &v.parametrlər {
        if p.çoxlu {
            if mövqeli.is_empty() && !p.ixtiyari {
                return Err(TəhlilXətası::Arq(format!("<{}> lazımdır", p.ad)));
            }
            dəyərlər.insert(p.ad.clone(), D::siyahı(mövqeli.drain(..).map(D::str).collect()));
        } else if !mövqeli.is_empty() {
            dəyərlər.insert(p.ad.clone(), D::str(mövqeli.remove(0)));
        } else if !p.ixtiyari {
            return Err(TəhlilXətası::Arq(format!("<{}> lazımdır", p.ad)));
        }
    }
    if let Some(m) = mövqeli.first() {
        return Err(TəhlilXətası::Arq(format!("artıq arqument: `{m}`")));
    }
    Ok(arq_nəticəsi(Rc::new(dəyərlər), Rc::new(bayraqlar)))
}

fn arq_nəticəsi(dəyərlər: Rc<IndexMap<String, D>>, bayraqlar: Rc<Vec<String>>) -> D {
    let ad_ = |s: &str| s.trim_start_matches('-').to_string();
    let (d1, d2, d3, d4) = (dəyərlər.clone(), dəyərlər.clone(), dəyərlər.clone(), dəyərlər.clone());
    let (b1, b2, b3) = (bayraqlar.clone(), bayraqlar.clone(), bayraqlar.clone());
    obyekt(
        "arqNəticəsi",
        vec![
            ("bayraq", d("bayraq", 1, Some(1), Box::new(move |i, a, _| Ok(D::M(b1.contains(&ad_(&mətnə(i, &a[0])?))))))),
            ("dəyər", d("dəyər", 1, Some(2), Box::new(move |i, a, _| {
                Ok(d1.get(&ad_(&mətnə(i, &a[0])?)).cloned().unwrap_or(a.get(1).cloned().unwrap_or(D::Boş)))
            }))),
            ("siyahı", d("siyahı", 1, Some(1), Box::new(move |i, a, _| {
                Ok(match d2.get(&ad_(&mətnə(i, &a[0])?)) {
                    None | Some(D::Boş) => D::siyahı(vec![]),
                    Some(D::Siyahı(l)) => D::Siyahı(l.clone()),
                    Some(x) => D::siyahı(vec![x.clone()]),
                })
            }))),
            ("var", d("var", 1, Some(1), Box::new(move |i, a, _| {
                let k = ad_(&mətnə(i, &a[0])?);
                Ok(D::M(d3.contains_key(&k) || b2.contains(&k)))
            }))),
            ("hamısı", d("hamısı", 0, Some(0), Box::new(move |_, _, _| {
                let mut l = Lüğət::default();
                for (k, v) in d4.iter() {
                    l.insert(Açar(D::s(k)), v.clone());
                }
                for b in b3.iter() {
                    l.insert(Açar(D::s(b)), D::M(true));
                }
                Ok(D::lüğət(l))
            }))),
        ],
        None,
    )
}

fn arqumentlər(_i: &İcraçı) -> D {
    let v = Rc::new(RefCell::new(ArqVəziyyət {
        proqram: "proqram".into(),
        seçimlər: vec![ArqSeçim { uzun: "--kömək".into(), qısa: "-k".into(), izah: "Bu köməyi göstər".into(), standart: None, bayraqdır: true }],
        ..Default::default()
    }));
    let özü: Rc<RefCell<D>> = Rc::new(RefCell::new(D::Boş));
    let qaytar = {
        let ö = özü.clone();
        move || ö.borrow().clone()
    };
    let qaytar = Rc::new(qaytar);
    let mətn_ = |i: &İcraçı, d: Option<&D>| -> Nəticə<String> {
        match d {
            Some(x) => mətnə(i, x),
            None => Ok(String::new()),
        }
    };
    let seçim_əlavə = |v: &Rc<RefCell<ArqVəziyyət>>, i: &İcraçı, a: &[D], adlı: &Adlı, bayraqdır: bool| -> Nəticə<()> {
        let u = mətnə(i, &arq_al(a, adlı, 0, "uzun").unwrap_or(D::Boş))?;
        if !u.starts_with("--") {
            return Err(xəta("ArqumentXətası", format!("uzun ad `--` ilə başlamalıdır: `{u}`"), "ALQ-R013"));
        }
        let q = match arq_al(a, adlı, 1, "qısa") {
            Some(x) if super::eded::doğrudur(&x) => mətnə(i, &x)?,
            _ => String::new(),
        };
        let izah = match arq_al(a, adlı, 2, "izah") {
            Some(x) => mətnə(i, &x)?,
            None => String::new(),
        };
        let standart = if bayraqdır {
            None
        } else {
            match arq_al(a, adlı, 3, "standart") {
                None | Some(D::Boş) => None,
                Some(x) => Some(mətnə(i, &x)?),
            }
        };
        v.borrow_mut().seçimlər.push(ArqSeçim { uzun: u, qısa: q, izah, standart, bayraqdır });
        Ok(())
    };
    let (v1, v2, v3, v4, v5, v6, v7, v8, v9) =
        (v.clone(), v.clone(), v.clone(), v.clone(), v.clone(), v.clone(), v.clone(), v.clone(), v.clone());
    let (q1, q2, q3, q4, q5, q6) = (qaytar.clone(), qaytar.clone(), qaytar.clone(), qaytar.clone(), qaytar.clone(), qaytar.clone());
    let ob = obyekt(
        "arqumentlər",
        vec![
            ("proqram", d("proqram", 1, Some(1), Box::new(move |i, a, _| {
                v1.borrow_mut().proqram = mətnə(i, &a[0])?;
                Ok(q1())
            }))),
            ("versiya", d("versiya", 1, Some(1), Box::new(move |i, a, _| {
                let mut v = v2.borrow_mut();
                v.versiya = mətnə(i, &a[0])?;
                if !v.seçimlər.iter().any(|s| s.uzun == "--versiya") {
                    v.seçimlər.push(ArqSeçim { uzun: "--versiya".into(), qısa: "-v".into(), izah: "Versiyanı göstər".into(), standart: None, bayraqdır: true });
                }
                drop(v);
                Ok(q2())
            }))),
            ("təsvir", d("təsvir", 1, Some(1), Box::new(move |i, a, _| {
                v3.borrow_mut().təsvir = mətnə(i, &a[0])?;
                Ok(q3())
            }))),
            ("parametr", d("parametr", 1, Some(4), Box::new(move |i, a, adlı| {
                if v4.borrow().parametrlər.last().map(|p| p.çoxlu).unwrap_or(false) {
                    return Err(xəta("ArqumentXətası", "`çoxlu` parametrdən sonra parametr ola bilməz", "ALQ-R013"));
                }
                let p = ArqParametr {
                    ad: mətnə(i, &a[0])?,
                    izah: mətn_(i, arq_al(&a, &adlı, 1, "izah").as_ref())?,
                    çoxlu: arq_al(&a, &adlı, 2, "çoxlu").map(|x| super::eded::doğrudur(&x)).unwrap_or(false),
                    ixtiyari: arq_al(&a, &adlı, 3, "ixtiyari").map(|x| super::eded::doğrudur(&x)).unwrap_or(false),
                };
                v4.borrow_mut().parametrlər.push(p);
                Ok(q4())
            }))),
            ("bayraq", d("bayraq", 1, Some(3), Box::new(move |i, a, adlı| {
                seçim_əlavə(&v5, i, &a, &adlı, true)?;
                Ok(q5())
            }))),
            ("seçim", d("seçim", 1, Some(4), Box::new(move |i, a, adlı| {
                seçim_əlavə(&v6, i, &a, &adlı, false)?;
                Ok(q6())
            }))),
            ("təhlil", d("təhlil", 0, Some(1), Box::new(move |i, a, _| {
                let xam: Vec<String> = match a.first() {
                    Some(x) if !x.boşdur() => {
                        let mut v = vec![];
                        for y in i.siyahıya(x, None)? {
                            v.push(mətnə(i, &y)?);
                        }
                        v
                    }
                    _ => i.proqram_arqumentləri.borrow().clone(),
                };
                let v = v7.borrow();
                match arq_təhlil(i, &v, &xam) {
                    Ok(d) => Ok(d),
                    Err(TəhlilXətası::Siqnal(s)) => Err(s),
                    Err(TəhlilXətası::Arq(m)) => {
                        i.xəta_yaz(&format!("xəta: {m}"));
                        i.xəta_yaz(&format!("istifadə: {}", v.istifadə()));
                        i.xəta_yaz(&format!("Ətraflı: {} --kömək", v.proqram));
                        Err(Siqnal::Dayanma(D::T(3)))
                    }
                }
            }))),
            ("kömək", d("kömək", 0, Some(0), Box::new(move |_, _, _| Ok(D::str(v8.borrow().kömək()))))),
            ("istifadə", d("istifadə", 0, Some(0), Box::new(move |_, _, _| Ok(D::str(v9.borrow().istifadə()))))),
        ],
        None,
    );
    *özü.borrow_mut() = ob.clone();
    ob
}
