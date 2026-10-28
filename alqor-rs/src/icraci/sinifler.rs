//! Siniflər, sadalamalar, üzv müraciəti, modul idxalı.

use super::cagiris::*;
use super::deyerler::*;
use super::icraci::İcraçı;
use super::muhit::Mühit;
use crate::aac::{self, Cümlə, Tip};
use crate::xeta::Yer;
use std::cell::RefCell;
use std::rc::Rc;

fn annot(a: &[String], əlavə: &[&str]) -> Annot {
    let var = |x: &str| a.iter().any(|s| s == x) || əlavə.contains(&x);
    Annot { yaddaşla: var("yaddaşla"), tənbəl: var("tənbəl"), statik: var("statik") }
}

fn funksiya(ad_: &str, p: Rc<Vec<aac::Parametr>>, g: aac::Gövdə, m: &Mühit, asinxron: bool, generator: bool, sinif: Option<Rc<Sinif>>, a: Annot) -> Rc<Funksiya> {
    Rc::new(Funksiya {
        ad: ad(ad_),
        parametrlər: p,
        gövdə: FGövdə::Blok(g),
        mühit: m.clone(),
        asinxron,
        generator,
        özü: None,
        sinif,
        annot: a,
        yaddaş: if a.yaddaşla { Some(Default::default()) } else { None },
        bəzənmiş: None,
    })
}

impl İcraçı {
    pub fn c_sinif(&self, c: &aac::SinifE, m: &Mühit) -> Nəticə<()> {
        let mut baza = None;
        if let Some(b) = &c.baza {
            let bd = self.tip_dəyəri(b, m)?;
            let D::Sinif(bs) = bd else {
                return Err(xəta_yer("TipXətası", format!("`{}` sinif deyil", b.tam_ad()), Some(c.yer), "ALQ-T002"));
            };
            if bs.son {
                return Err(xəta_yer(
                    "TipXətası",
                    format!("`{}` `son` sinifdir, miras alına bilməz", bs.ad),
                    Some(c.yer),
                    "ALQ-T055",
                ));
            }
            baza = Some(bs);
        }
        let quruluş: &'static str = match c.quruluş.as_str() {
            "struktur" => "struktur",
            "obyekt" => "obyekt",
            "komponent" => "komponent",
            "mağaza" => "mağaza",
            "aktyor" => "aktyor",
            _ => "sinif",
        };
        let mut s = Sinif::yeni(&c.ad, baza, quruluş);
        s.mücərrəd = c.mücərrəd;
        s.son = c.son;
        s.mühit = Some(m.clone());
        s.interfeyslər = c.interfeyslər.iter().filter(|t| matches!(t, Tip::Ad { .. })).map(|t| t.tam_ad()).collect();
        let s = Rc::new(s);
        for q in &c.qarışıqlar {
            if let D::Sinif(qd) = self.tip_dəyəri(q, m)? {
                s.metodlar.borrow_mut().extend(qd.metodlar.borrow().iter().map(|(k, v)| (k.clone(), v.clone())));
                s.statiklər.borrow_mut().extend(qd.statiklər.borrow().iter().map(|(k, v)| (k.clone(), v.clone())));
                s.xassələr.borrow_mut().extend(qd.xassələr.borrow().iter().cloned());
            }
        }
        self.sinif_üzvlərini_qur(&s, &c.üzvlər, m)?;
        if !c.mücərrəd {
            let mut tələb: Vec<Ad> = vec![];
            let mut cari = Some(s.clone());
            while let Some(x) = cari {
                tələb.extend(x.mücərrəd_metodlar.borrow().iter().cloned());
                cari = x.baza.clone();
            }
            let mut ç: Vec<String> = tələb.iter().filter(|a| s.metod_tap(a).is_none()).map(|a| a.to_string()).collect();
            ç.sort();
            ç.dedup();
            if !ç.is_empty() {
                return Err(xəta_yer(
                    "TipXətası",
                    format!("`{}` mücərrəd metodları tətbiq etmir: {}", s.ad, ç.join(", ")),
                    Some(c.yer),
                    "ALQ-T053",
                ));
            }
        }
        if quruluş == "obyekt" {
            let n = self.nümunə_yarat(&s, None, vec![], vec![], Some(c.yer))?;
            m.elan(ad(&c.ad), n, false);
        } else {
            m.elan(ad(&c.ad), D::Sinif(s), false);
            if !self.qaldırılır.get() && !c.bəzəyicilər.is_empty() {
                self.bəzə_ad(&c.ad, &c.bəzəyicilər, m)?;
            }
        }
        Ok(())
    }

    pub fn sinif_üzvlərini_qur(&self, s: &Rc<Sinif>, üzvlər: &[Cümlə], m: &Mühit) -> Nəticə<()> {
        for ü in üzvlər {
            match ü {
                Cümlə::Xassə(x) => {
                    let a = annot(&x.annotasiyalar, &[]);
                    if let Some(oxu) = &x.oxu {
                        let a = if x.tənbəl { annot(&x.annotasiyalar, &["tənbəl"]) } else { a };
                        s.hesablananlar.borrow_mut().insert(
                            ad(&x.ad),
                            funksiya(&x.ad, Rc::new(vec![]), oxu.clone(), m, false, false, None, a),
                        );
                        if !x.tənbəl {
                            if let Some(yaz) = &x.yaz {
                                let p = aac::Parametr {
                                    yer: x.yer,
                                    ad: x.yaz_parametri.clone().unwrap_or("dəyər".into()),
                                    tip: None,
                                    standart: None,
                                    variadic: false,
                                    adlı_variadic: false,
                                    yalnız_adlı: false,
                                    xassə_görünüşü: None,
                                };
                                s.yazıcılar.borrow_mut().insert(
                                    ad(&x.ad),
                                    funksiya(&x.ad, Rc::new(vec![p]), yaz.clone(), m, false, false, None, Annot::default()),
                                );
                            }
                        }
                    } else if x.statik {
                        let d = match &x.standart {
                            Some(e) => self.ifadə(e, m)?,
                            None => D::Boş,
                        };
                        s.statiklər.borrow_mut().insert(ad(&x.ad), d);
                    } else {
                        s.xassələr.borrow_mut().push(x.clone());
                    }
                }
                Cümlə::Metod(f) => {
                    if f.mücərrəd {
                        s.mücərrəd_metodlar.borrow_mut().push(ad(&f.ad));
                        continue;
                    }
                    let a = annot(&f.annotasiyalar, if f.statik { &["statik"] } else { &[] });
                    let ff = funksiya(&f.ad, f.parametrlər.clone(), f.gövdə.clone().unwrap_or_default(), m, f.asinxron, f.generator, Some(s.clone()), a);
                    let bəzəyicilər = self.bəzəyicilər(&f.bəzəyicilər, m)?;
                    if f.statik {
                        let d = self.bəzəyiciləri_tətbiq_et(D::Funksiya(ff), &bəzəyicilər)?;
                        s.statiklər.borrow_mut().insert(ad(&f.ad), d);
                    } else if !bəzəyicilər.is_empty() {
                        let metod = ff.clone();
                        let ad_ = f.ad.clone();
                        let sərbəst = super::deyerler::daxili(&f.ad, 0, None, move |i, args, adlı| {
                            let mut args = args.into_iter();
                            let Some(özü) = args.next() else {
                                return Err(xəta_yer(
                                    "ArqumentXətası",
                                    format!("`{}` metodu `özü` arqumenti olmadan çağırıldı", ad_),
                                    None,
                                    "ALQ-R022",
                                ));
                            };
                            i.funksiya_çağır(&metod.bağla(özü), args.collect(), adlı, None)
                        });
                        let hədəf = self.bəzəyiciləri_tətbiq_et(sərbəst, &bəzəyicilər)?;
                        let mut b = funksiya(&f.ad, f.parametrlər.clone(), Default::default(), m, false, false, Some(s.clone()), a);
                        Rc::get_mut(&mut b).unwrap().bəzənmiş = Some(hədəf);
                        s.metodlar.borrow_mut().insert(ad(&f.ad), b);
                    } else {
                        s.metodlar.borrow_mut().insert(ad(&f.ad), ff);
                    }
                }
                Cümlə::Qurucu(q) => {
                    let a = q.ad.clone().unwrap_or_default();
                    let f = funksiya(
                        if a.is_empty() { "<qurucu>" } else { &a },
                        q.parametrlər.clone(),
                        q.gövdə.clone(),
                        m,
                        false,
                        false,
                        Some(s.clone()),
                        Annot::default(),
                    );
                    s.quruculər.borrow_mut().insert(ad(&a), f);
                }
                Cümlə::Dağıdıcı(..) => {}
                _ => self.cümlə(ü, m)?,
            }
        }
        Ok(())
    }

    pub fn c_interfeys(&self, a: &str, üzvlər: &[Cümlə], m: &Mühit) -> Nəticə<()> {
        let mut s = Sinif::yeni(a, None, "interfeys");
        s.mücərrəd = true;
        s.mühit = Some(m.clone());
        let s = Rc::new(s);
        for ü in üzvlər {
            if let Cümlə::Metod(f) = ü {
                if f.mücərrəd || f.gövdə.is_none() {
                    s.mücərrəd_metodlar.borrow_mut().push(ad(&f.ad));
                } else {
                    let ff = funksiya(&f.ad, f.parametrlər.clone(), f.gövdə.clone().unwrap(), m, false, false, Some(s.clone()), Annot::default());
                    s.metodlar.borrow_mut().insert(ad(&f.ad), ff);
                }
            }
        }
        m.elan(ad(a), D::Sinif(s), false);
        Ok(())
    }

    pub fn c_qarışıq(&self, a: &str, üzvlər: &[Cümlə], m: &Mühit) -> Nəticə<()> {
        let mut s = Sinif::yeni(a, None, "qarışıq");
        s.mühit = Some(m.clone());
        let s = Rc::new(s);
        self.sinif_üzvlərini_qur(&s, üzvlər, m)?;
        m.elan(ad(a), D::Sinif(s), false);
        Ok(())
    }

    pub fn c_sadalama(&self, a: &str, variantlar: &[aac::SadalamaVariantı], üzvlər: &[Cümlə], əsas_tip: Option<&Tip>, m: &Mühit) -> Nəticə<()> {
        let e = Rc::new(Sadalama {
            ad: ad(a),
            variantlar: Default::default(),
            metodlar: Default::default(),
            sıra: Default::default(),
        });
        let mut növbəti = D::T(0);
        for (i, v) in variantlar.iter().enumerate() {
            let mut dəyər = D::Boş;
            if let Some(x) = &v.dəyər {
                dəyər = self.ifadə(x, m)?;
                if dəyər.tamdır() {
                    növbəti = self.ikili_hesabla("+", &dəyər, &D::T(1), None)?;
                }
            } else if əsas_tip.is_some() {
                dəyər = növbəti.clone();
                növbəti = self.ikili_hesabla("+", &növbəti, &D::T(1), None)?;
            }
            let mut sahələr = Sahələr::default();
            if !v.arqumentlər.is_empty() {
                let qp: Vec<&aac::Parametr> = üzvlər
                    .iter()
                    .filter_map(|ü| if let Cümlə::Qurucu(q) = ü { Some(q) } else { None })
                    .flat_map(|q| q.parametrlər.iter())
                    .collect();
                for (j, x) in v.arqumentlər.iter().enumerate() {
                    let n = if j < qp.len() { qp[j].ad.clone() } else { format!("_{j}") };
                    let d = self.ifadə(&x.dəyər, m)?;
                    sahələr.insert(ad(&n), d);
                }
            }
            if !v.parametrlər.is_empty() {
                e.variantlar.borrow_mut().insert(
                    ad(&v.ad),
                    D::Variant(Rc::new(VariantQurucusu {
                        sadalama: e.clone(),
                        ad: ad(&v.ad),
                        parametrlər: v.parametrlər.iter().map(|p| ad(&p.ad)).collect(),
                        sıra: i as i64,
                    })),
                );
            } else {
                e.variantlar.borrow_mut().insert(
                    ad(&v.ad),
                    D::SD(Rc::new(SadalamaDəyəri { sadalama: e.clone(), ad: ad(&v.ad), sıra_nömrəsi: i as i64, dəyər, sahələr })),
                );
            }
            e.sıra.borrow_mut().push(ad(&v.ad));
        }
        for ü in üzvlər {
            if let Cümlə::Metod(f) = ü {
                if let Some(g) = &f.gövdə {
                    let ff = funksiya(&f.ad, f.parametrlər.clone(), g.clone(), m, false, false, None, Annot::default());
                    e.metodlar.borrow_mut().insert(ad(&f.ad), ff);
                }
            }
        }
        m.elan(ad(a), D::Sadalama(e), false);
        Ok(())
    }

    pub fn c_genişlətmə(&self, t: &Tip, üzvlər: &[Cümlə], m: &Mühit) -> Nəticə<()> {
        let a = if let Tip::Ad { .. } = t { t.tam_ad() } else { String::new() };
        for ü in üzvlər {
            if let Cümlə::Metod(f) = ü {
                if let Some(g) = &f.gövdə {
                    let ff = funksiya(&f.ad, f.parametrlər.clone(), g.clone(), m, false, false, None, Annot::default());
                    self.genişlətmələr.borrow_mut().entry(a.clone()).or_default().insert(ad(&f.ad), ff);
                }
            }
        }
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    pub fn c_idxal(&self, yer: Yer, yol: &[String], mətn_yolu: Option<&str>, ləqəb: Option<&str>, elementlər: &[aac::İdxalElementi], hamısı: bool, m: &Mühit) -> Nəticə<()> {
        let a = match mətn_yolu {
            Some(s) => s.to_string(),
            None => yol.join("."),
        };
        let md = super::kitabxana::modul_yüklə(self, &a, Some(yer))?;
        if hamısı {
            for (k, v) in md.üzvlər.borrow().iter() {
                m.elan(k.clone(), v.clone(), false);
            }
            return Ok(());
        }
        if !elementlər.is_empty() {
            for e in elementlər {
                let d = md.üzvlər.borrow().get(e.ad.as_str()).cloned();
                match d {
                    None => {
                        return Err(xəta_yer(
                            "ArqumentXətası",
                            format!("`{}` modulunda `{}` ixracı yoxdur", a, e.ad),
                            Some(yer),
                            "ALQ-M002",
                        ))
                    }
                    Some(d) => m.elan(ad(e.ləqəb.as_deref().unwrap_or(&e.ad)), d, false),
                }
            }
            return Ok(());
        }
        let n = match ləqəb {
            Some(l) => l.to_string(),
            None => match yol.last() {
                Some(y) => y.clone(),
                None => md.adı().to_string(),
            },
        };
        m.elan(ad(&n), D::Modul(md), false);
        Ok(())
    }

    // ── Obyekt yaratma ────────────────────────────────────────────────

    pub fn nümunə_yarat(&self, s: &Rc<Sinif>, qurucu_adı: Option<&str>, args: Vec<D>, adlı: Adlı, yer: Option<Yer>) -> Nəticə {
        if s.mücərrəd {
            return Err(xəta_yer(
                "TipXətası",
                format!("`{}` mücərrəd sinifdir — ondan obyekt yaradıla bilməz", s.ad),
                yer,
                "ALQ-T052",
            ));
        }
        let n = Rc::new(Nümunə::yeni(s.clone()));
        let mühit = s.mühit.clone().unwrap_or_else(|| self.qlobal.clone());
        for x in s.bütün_xassələr() {
            let d = match &x.standart {
                Some(e) => genişlət(self.ifadə(e, &mühit)?, x.tip.as_ref()),
                None => standart_dəyər(x.tip.as_ref()),
            };
            n.sahələr.borrow_mut().insert(ad(&x.ad), d);
        }
        let d = D::Nümunə(n.clone());
        match s.qurucu_tap(qurucu_adı.unwrap_or("")) {
            Some(q) => {
                // Aktyorun qurucusu onun daxilində işləyir: `özü.metod()` birbaşadır
                if let Some(p) = &n.aktyor {
                    p.emal.set(p.emal.get() + 1);
                }
                let r = self.funksiya_çağır(&q.bağla(d.clone()), args, adlı, yer);
                if let Some(p) = &n.aktyor {
                    p.emal.set(p.emal.get() - 1);
                }
                r?;
            }
            None => {
                if !args.is_empty() || !adlı.is_empty() {
                    if s.quruluş == "struktur" && !adlı.is_empty() && args.is_empty() {
                        for (k, v) in adlı {
                            n.sahələr.borrow_mut().insert(k, v);
                        }
                    } else {
                        return Err(xəta_yer(
                            "ArqumentXətası",
                            format!("`{}` sinfində qurucu yoxdur, amma arqument verilib", s.ad),
                            yer,
                            "ALQ-T003",
                        ));
                    }
                }
            }
        }
        Ok(d)
    }

    // ── Üzv müraciəti ─────────────────────────────────────────────────

    pub fn üzv_al(&self, o: &D, a: &str, yer: Option<Yer>) -> Nəticə {
        match o {
            D::Üst(u) => {
                let Some(baza) = &u.1.baza else {
                    return Err(xəta_yer("TipXətası", "baza sinif yoxdur", yer, "ALQ-T012"));
                };
                match baza.metod_tap(a) {
                    Some(f) => Ok(D::Funksiya(f.bağla(u.0.clone()))),
                    None => Err(xəta_yer(
                        "ArqumentXətası",
                        format!("baza sinifdə `{}` metodu yoxdur", a),
                        yer,
                        "ALQ-T006",
                    )),
                }
            }
            D::Nümunə(n) => self.nümunə_üzvü(o, n, a, yer),
            D::Sinif(s) => {
                if let Some(d) = s.statik_tap(a) {
                    return Ok(d);
                }
                if s.quruculər.borrow().contains_key(a) {
                    return Ok(D::QurucuIst(Rc::new((s.clone(), ad(a)))));
                }
                Err(xəta_yer("ArqumentXətası", format!("`{}` sinfində statik `{}` yoxdur", s.ad, a), yer, "ALQ-T006"))
            }
            D::Sadalama(e) => {
                if let Some(v) = e.variantlar.borrow().get(a) {
                    return Ok(v.clone());
                }
                if let Some(f) = e.metodlar.borrow().get(a) {
                    return Ok(D::Funksiya(f.clone()));
                }
                if let Some(d) = super::metodlar::sadalama_metodu(e, a) {
                    return Ok(d);
                }
                Err(xəta_yer("ArqumentXətası", format!("`{}` sadalamasında `{}` yoxdur", e.ad, a), yer, "ALQ-T061"))
            }
            D::SD(v) => {
                if let Some(d) = v.sahələr.get(a) {
                    return Ok(d.clone());
                }
                if let Some(f) = v.sadalama.metodlar.borrow().get(a) {
                    return Ok(D::Funksiya(f.bağla(o.clone())));
                }
                if let Some(d) = super::metodlar::sadalama_dəyər_metodu(v, a) {
                    return Ok(d);
                }
                Err(xəta_yer("ArqumentXətası", format!("`{}` variantında `{}` yoxdur", v.ad, a), yer, "ALQ-T006"))
            }
            D::Modul(md) => {
                if let Some(d) = md.üzvlər.borrow().get(a) {
                    return Ok(d.clone());
                }
                Err(xəta_yer("ArqumentXətası", format!("`{}` modulunda `{}` yoxdur", md.adı(), a), yer, "ALQ-M002"))
            }
            D::Element(e) if matches!(a, "ad" | "atributlar" | "uşaqlar") => Ok(match a {
                "ad" => D::S(e.ad.clone()),
                "atributlar" => e.atributlar.clone(),
                _ => e.uşaqlar.clone(),
            }),
            // Funksiyanın adı — bəzəyicilər üçün (`f.ad`)
            D::Funksiya(f) if a == "ad" => Ok(D::s(&f.ad)),
            D::Daxili(f) if a == "ad" => Ok(D::s(&f.ad)),
            D::Metod(f) if a == "ad" => Ok(D::s(&f.ad)),
            D::Kortej(k) if !a.is_empty() && a.bytes().all(|b| b.is_ascii_digit()) => {
                let i: usize = a.parse().unwrap_or(usize::MAX);
                if i >= k.len() {
                    return Err(xəta_yer("İndeksXətası", format!("kortejdə {} indeksi yoxdur", i), yer, "ALQ-R002"));
                }
                Ok(k[i].clone())
            }
            D::Obyekt(ob) => match ob.üzvlər.get(a) {
                Some(d) => Ok(d.clone()),
                None => Err(self.üzv_xətası(o, a, yer)),
            },
            _ => match self.daxili_metod(o, a) {
                Some(d) => Ok(d),
                None => Err(self.üzv_xətası(o, a, yer)),
            },
        }
    }

    /// `obyekt.ad` — daxili tip metodu (genişlətmələr üstündür)
    pub fn daxili_metod(&self, o: &D, a: &str) -> Option<D> {
        let tip = tip_kökü(o);
        if let Some(g) = self.genişlətmələr.borrow().get(&tip) {
            if let Some(f) = g.get(a) {
                return Some(D::Metod(Rc::new(BağlıMetod { ad: ad(a), obyekt: o.clone(), f: MetodF::Genişlətmə(f.clone()) })));
            }
        }
        if super::metodlar::metod_var(o, a) {
            return Some(D::Metod(Rc::new(BağlıMetod { ad: ad(a), obyekt: o.clone(), f: MetodF::Daxili })));
        }
        None
    }

    fn üzv_xətası(&self, o: &D, a: &str, yer: Option<Yer>) -> Siqnal {
        let mut mesaj = format!("`{}` tipində `{}` üzvü yoxdur", tip_adı(o), a);
        let mut üzvlər: Vec<String> = vec![];
        if let Some(g) = self.genişlətmələr.borrow().get(&tip_kökü(o)) {
            üzvlər.extend(g.keys().map(|k| k.to_string()));
        }
        üzvlər.extend(super::metodlar::metod_adları(o).iter().map(|s| s.to_string()));
        if let D::Obyekt(ob) = o {
            üzvlər.extend(ob.üzvlər.keys().map(|s| s.to_string()));
        }
        üzvlər.sort();
        üzvlər.dedup();
        for ü in &üzvlər {
            if crate::elifba::latınla(ü) == a && ü != a {
                mesaj += &format!(
                    " — `{}` demək istəyirdiniz? ASCII çevrilməsi yalnız AÇAR SÖZLƏRƏ aiddir, üzv adlarına yox",
                    ü
                );
                return xəta_yer("ArqumentXətası", mesaj, yer, "ALQ-T006");
            }
        }
        let ön: String = a.chars().take(3).collect();
        let yaxın: Vec<&String> = üzvlər.iter().filter(|ü| ü.starts_with(&ön)).take(3).collect();
        if !yaxın.is_empty() {
            mesaj += &format!(" — bəlkə: {}", yaxın.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", "));
        }
        xəta_yer("ArqumentXətası", mesaj, yer, "ALQ-T006")
    }

    fn nümunə_üzvü(&self, o: &D, n: &Rc<Nümunə>, a: &str, yer: Option<Yer>) -> Nəticə {
        if let Some(p) = &n.aktyor {
            if p.emal.get() == 0 {
                if let Some(f) = n.sinif.metod_tap(a) {
                    let n2 = n.clone();
                    return Ok(daxili(&f.ad.clone(), 0, None, move |i, args, adlı| {
                        Ok(i.aktyora_göndər(&n2, f.clone(), args, adlı, None))
                    }));
                }
                // Xassəni oxumazdan əvvəl gözləyən mesajlar emal olunur
                self.poçtu_boşalt(n, None)?;
            }
        }
        if let Some(d) = n.sahələr.borrow().get(a) {
            return Ok(d.clone());
        }
        if let Some(h) = n.sinif.hesablanan_tap(a) {
            if h.annot.tənbəl {
                if let Some(d) = n.keş.borrow().get(a) {
                    return Ok(d.clone());
                }
                let d = self.funksiya_çağır(&h.bağla(o.clone()), vec![], vec![], yer)?;
                n.keş.borrow_mut().insert(ad(a), d.clone());
                return Ok(d);
            }
            return self.funksiya_çağır(&h.bağla(o.clone()), vec![], vec![], yer);
        }
        if let Some(f) = n.sinif.metod_tap(a) {
            return Ok(D::Funksiya(f.bağla(o.clone())));
        }
        if let Some(d) = n.sinif.statik_tap(a) {
            return Ok(d);
        }
        if let Some(d) = self.daxili_metod(o, a) {
            return Ok(d);
        }
        Err(xəta_yer("ArqumentXətası", format!("`{}` tipində `{}` üzvü yoxdur", n.sinif.ad, a), yer, "ALQ-T006"))
    }

    pub fn üzv_qoy(&self, o: &D, a: &str, d: D, yer: Option<Yer>) -> Nəticə<()> {
        match o {
            D::Nümunə(n) => {
                if n.aktyor.as_ref().is_some_and(|p| p.emal.get() == 0) {
                    self.poçtu_boşalt(n, None)?;
                }
                if let Some(y) = n.sinif.yazıcı_tap(a) {
                    self.funksiya_çağır(&y.bağla(o.clone()), vec![d], vec![], yer)?;
                    return Ok(());
                }
                if n.sinif.hesablanan_tap(a).is_some() {
                    return Err(xəta_yer("ArqumentXətası", format!("`{}` yalnız oxunan xassədir", a), yer, "ALQ-T020"));
                }
                n.sahələr.borrow_mut().insert(ad(a), d);
                Ok(())
            }
            D::Sinif(s) => {
                s.statiklər.borrow_mut().insert(ad(a), d);
                Ok(())
            }
            D::Modul(md) => {
                md.üzvlər.borrow_mut().insert(ad(a), d);
                Ok(())
            }
            _ => Err(xəta_yer(
                "ArqumentXətası",
                format!("`{}` tipinin üzvü dəyişdirilə bilməz", tip_adı(o)),
                yer,
                "ALQ-T021",
            )),
        }
    }
}

#[allow(dead_code)]
fn _istifadə(_: RefCell<()>) {}
