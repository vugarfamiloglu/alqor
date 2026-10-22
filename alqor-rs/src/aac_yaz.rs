//! AAC-nin kanonik mətn çapı (`alqor-rs aac`). Python tərəfi:
//! `alqor/rs/muqayise.py` — `aac_çapı()` eyni mətni verməlidir.
//!
//! Format: hər qovşaq bir sətir (`[sahə: ]Növ sətir:sütun+uzunluq atributlar`),
//! uşaqlar iki boşluq dərində. `None` sahələr çap olunmur; siyahılar
//! həmişə `sahə: [n]` başlığı ilə çap olunur.

use crate::aac::*;
use crate::xeta::Yer;

/// Mətnin sabit dırnaqlanması (Python ilə eyni qayda).
pub fn q(s: &str) -> String {
    let mut n = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => n.push_str("\\\""),
            '\\' => n.push_str("\\\\"),
            '\n' => n.push_str("\\n"),
            '\r' => n.push_str("\\r"),
            '\t' => n.push_str("\\t"),
            c if (c as u32) < 0x20 || c as u32 == 0x7f => n.push_str(&format!("\\u{{{:x}}}", c as u32)),
            c => n.push(c),
        }
    }
    n.push('"');
    n
}

fn oq(s: &Option<String>) -> String {
    s.as_deref().map(q).unwrap_or_else(|| "-".into())
}

fn qs(v: &[String]) -> String {
    format!("[{}]", v.iter().map(|s| q(s)).collect::<Vec<_>>().join(", "))
}

fn y(y: &Yer) -> String {
    format!("{}:{}+{}", y.sətir(), y.sütun(), y.uzunluq)
}

struct Yazıcı {
    ç: String,
    d: usize,
}

impl Yazıcı {
    fn s(&mut self, l: &str, t: &str) {
        for _ in 0..self.d {
            self.ç.push_str("  ");
        }
        if !l.is_empty() {
            self.ç.push_str(l);
            self.ç.push_str(": ");
        }
        self.ç.push_str(t);
        self.ç.push('\n');
    }

    fn iç(&mut self, f: impl FnOnce(&mut Self)) {
        self.d += 1;
        f(self);
        self.d -= 1;
    }

    fn siyahı<T>(&mut self, l: &str, v: &[T], f: impl Fn(&mut Self, &T)) {
        self.s(l, &format!("[{}]", v.len()));
        self.iç(|w| {
            for x in v {
                f(w, x);
            }
        });
    }

    fn gövdə(&mut self, l: &str, g: &[Cümlə]) {
        self.siyahı(l, g, |w, c| w.cümlə("", c));
    }

    fn ogövdə(&mut self, l: &str, g: &Option<Gövdə>) {
        if let Some(g) = g {
            self.gövdə(l, g);
        }
    }

    fn oifadə(&mut self, l: &str, e: &Option<E>) {
        if let Some(e) = e {
            self.ifadə(l, e);
        }
    }

    fn ifadələr(&mut self, l: &str, v: &[E]) {
        self.siyahı(l, v, |w, e| w.ifadə("", e));
    }

    fn otip(&mut self, l: &str, t: &Option<Tip>) {
        if let Some(t) = t {
            self.tip(l, t);
        }
    }

    fn tip(&mut self, l: &str, t: &Tip) {
        match t {
            Tip::Ad { yer, yol, arqumentlər, ixtiyari } => {
                self.s(l, &format!("TipAd {} yol={} ixtiyari={}", y(yer), q(&yol.join(".")), ixtiyari));
                self.iç(|w| w.siyahı("arqumentlər", arqumentlər, |w, t| w.tip("", t)));
            }
            Tip::Birləşmə { yer, variantlar } => {
                self.s(l, &format!("TipBirləşmə {}", y(yer)));
                self.iç(|w| w.siyahı("variantlar", variantlar, |w, t| w.tip("", t)));
            }
            Tip::Kortej { yer, elementlər, ixtiyari } => {
                self.s(l, &format!("TipKortej {} ixtiyari={}", y(yer), ixtiyari));
                self.iç(|w| w.siyahı("elementlər", elementlər, |w, t| w.tip("", t)));
            }
            Tip::Funksiya { yer, parametrlər, qaytarma, ixtiyari } => {
                self.s(l, &format!("TipFunksiya {} ixtiyari={}", y(yer), ixtiyari));
                self.iç(|w| {
                    w.siyahı("parametrlər", parametrlər, |w, t| w.tip("", t));
                    if let Some(t) = qaytarma {
                        w.tip("qaytarma", t);
                    }
                });
            }
        }
    }

    fn bağlama(&mut self, l: &str, b: &Bağlama) {
        let n = match &b.növ {
            BağlamaNöv::Ad(a) => format!("növ=ad ad={}", q(a)),
            BağlamaNöv::Atma => "növ=atma".into(),
            BağlamaNöv::Qalan(a) => format!("növ=qalan ad={}", q(a)),
            BağlamaNöv::Kortej(_) => "növ=kortej".into(),
            BağlamaNöv::Obyekt(_) => "növ=obyekt".into(),
        };
        self.s(l, &format!("Bağlama {} {}", y(&b.yer), n));
        self.iç(|w| {
            match &b.növ {
                BağlamaNöv::Kortej(alt) => w.siyahı("alt", alt, |w, b| w.bağlama("", b)),
                BağlamaNöv::Obyekt(sahələr) => w.siyahı("sahələr", sahələr, |w, (a, b)| {
                    w.s("", &format!("Sahə ad={}", q(a)));
                    if let Some(b) = b {
                        w.iç(|w| w.bağlama("bağlama", b));
                    }
                }),
                _ => {}
            }
            w.otip("tip", &b.tip);
        });
    }

    fn parametr(&mut self, l: &str, p: &Parametr) {
        self.s(
            l,
            &format!(
                "Parametr {} ad={} variadic={} adlı_variadic={} yalnız_adlı={} xassə_görünüşü={}",
                y(&p.yer),
                q(&p.ad),
                p.variadic,
                p.adlı_variadic,
                p.yalnız_adlı,
                oq(&p.xassə_görünüşü)
            ),
        );
        self.iç(|w| {
            w.otip("tip", &p.tip);
            w.oifadə("standart", &p.standart);
        });
    }

    fn parametrlər(&mut self, l: &str, v: &[Parametr]) {
        self.siyahı(l, v, |w, p| w.parametr("", p));
    }

    fn arqumentlər(&mut self, l: &str, v: &[Arqument]) {
        self.siyahı(l, v, |w, a| {
            w.s("", &format!("Arqument ad={} yayma={}", oq(&a.ad), a.yayma));
            w.iç(|w| w.ifadə("dəyər", &a.dəyər));
        });
    }

    fn naxış(&mut self, l: &str, n: &Naxış) {
        match n {
            Naxış::Atma => self.s(l, "Naxış atma"),
            Naxış::Literal(e) => {
                self.s(l, "Naxış literal");
                self.iç(|w| w.ifadə("dəyər", e));
            }
            Naxış::Şərt(e) => {
                self.s(l, "Naxış şərt");
                self.iç(|w| w.ifadə("dəyər", e));
            }
            Naxış::Ad(a) => self.s(l, &format!("Naxış ad {}", q(a))),
            Naxış::Tip(t) => {
                self.s(l, "Naxış tip");
                self.iç(|w| w.tip("tip", t));
            }
            Naxış::Diapazon(b, s, x) => {
                self.s(l, &format!("Naxış diapazon xaric={}", x));
                self.iç(|w| {
                    w.ifadə("başlanğıc", b);
                    w.ifadə("son", s);
                });
            }
            Naxış::Kortej(alt) => {
                self.s(l, "Naxış kortej");
                self.iç(|w| w.siyahı("alt", alt, |w, n| w.naxış("", n)));
            }
            Naxış::Siyahı(alt, qalan) => {
                self.s(l, &format!("Naxış siyahı qalan={}", oq(qalan)));
                self.iç(|w| w.siyahı("alt", alt, |w, n| w.naxış("", n)));
            }
            Naxış::Obyekt(tip, alt, sahələr) => {
                self.s(l, "Naxış obyekt");
                self.iç(|w| {
                    w.otip("tip", tip);
                    w.siyahı("alt", alt, |w, n| w.naxış("", n));
                    w.siyahı("sahələr", sahələr, |w, (a, n)| {
                        w.s("", &format!("Sahə ad={}", q(a)));
                        if let Some(n) = n {
                            w.iç(|w| w.naxış("naxış", n));
                        }
                    });
                });
            }
        }
    }

    fn funksiya(&mut self, l: &str, növ: &str, f: &Funksiya) {
        self.s(
            l,
            &format!(
                "{} {} ad={} asinxron={} generator={} statik={} mücərrəd={} annotasiyalar={}",
                növ,
                y(&f.yer),
                q(&f.ad),
                f.asinxron,
                f.generator,
                f.statik,
                f.mücərrəd,
                qs(&f.annotasiyalar)
            ),
        );
        self.iç(|w| {
            w.parametrlər("parametrlər", &f.parametrlər);
            w.ogövdə("gövdə", &f.gövdə);
        });
    }

    fn cümlə(&mut self, l: &str, c: &Cümlə) {
        use Cümlə as C;
        match c {
            C::İfadə(yer, e) => {
                self.s(l, &format!("İfadəCümləsi {}", y(yer)));
                self.iç(|w| w.ifadə("ifadə", e));
            }
            C::DəyişənElanı { yer, növ, bağlamalar, dəyərlər } => {
                self.s(l, &format!("DəyişənElanı {} növ={}", y(yer), q(növ)));
                self.iç(|w| {
                    w.siyahı("bağlamalar", bağlamalar, |w, b| w.bağlama("", b));
                    w.ifadələr("dəyərlər", dəyərlər);
                });
            }
            C::Funksiya(f) => self.funksiya(l, "Funksiya", f),
            C::Metod(f) => self.funksiya(l, "Metod", f),
            C::Xassə(x) => {
                self.s(
                    l,
                    &format!(
                        "Xassə {} ad={} statik={} tənbəl={} yaz_parametri={} annotasiyalar={}",
                        y(&x.yer),
                        q(&x.ad),
                        x.statik,
                        x.tənbəl,
                        oq(&x.yaz_parametri),
                        qs(&x.annotasiyalar)
                    ),
                );
                self.iç(|w| {
                    w.otip("tip", &x.tip);
                    w.oifadə("standart", &x.standart);
                    w.ogövdə("oxu", &x.oxu);
                    w.ogövdə("yaz", &x.yaz);
                });
            }
            C::Qurucu(k) => {
                self.s(l, &format!("Qurucu {} ad={}", y(&k.yer), oq(&k.ad)));
                self.iç(|w| {
                    w.parametrlər("parametrlər", &k.parametrlər);
                    w.gövdə("gövdə", &k.gövdə);
                });
            }
            C::Dağıdıcı(yer, g) => {
                self.s(l, &format!("Dağıdıcı {}", y(yer)));
                self.iç(|w| w.gövdə("gövdə", g));
            }
            C::Sinif(s) => {
                self.s(
                    l,
                    &format!(
                        "Sinif {} ad={} quruluş={} mücərrəd={} son={}",
                        y(&s.yer),
                        q(&s.ad),
                        q(&s.quruluş),
                        s.mücərrəd,
                        s.son
                    ),
                );
                self.iç(|w| {
                    w.otip("baza", &s.baza);
                    w.siyahı("interfeyslər", &s.interfeyslər, |w, t| w.tip("", t));
                    w.siyahı("qarışıqlar", &s.qarışıqlar, |w, t| w.tip("", t));
                    w.gövdə("üzvlər", &s.üzvlər);
                });
            }
            C::İnterfeys { yer, ad, üzvlər } => {
                self.s(l, &format!("İnterfeys {} ad={}", y(yer), q(ad)));
                self.iç(|w| w.gövdə("üzvlər", üzvlər));
            }
            C::Sadalama { yer, ad, variantlar, üzvlər, əsas_tip } => {
                self.s(l, &format!("Sadalama {} ad={}", y(yer), q(ad)));
                self.iç(|w| {
                    w.otip("əsas_tip", əsas_tip);
                    w.siyahı("variantlar", variantlar, |w, v| {
                        w.s("", &format!("Variant {} ad={}", y(&v.yer), q(&v.ad)));
                        w.iç(|w| {
                            w.oifadə("dəyər", &v.dəyər);
                            w.arqumentlər("arqumentlər", &v.arqumentlər);
                            w.parametrlər("parametrlər", &v.parametrlər);
                        });
                    });
                    w.gövdə("üzvlər", üzvlər);
                });
            }
            C::Qarışıq { yer, ad, üzvlər } => {
                self.s(l, &format!("Qarışıq {} ad={}", y(yer), q(ad)));
                self.iç(|w| w.gövdə("üzvlər", üzvlər));
            }
            C::Genişlətmə { yer, tip, üzvlər } => {
                self.s(l, &format!("Genişlətmə {}", y(yer)));
                self.iç(|w| {
                    w.tip("tip", tip);
                    w.gövdə("üzvlər", üzvlər);
                });
            }
            C::TipAliası { yer, ad, tip } => {
                self.s(l, &format!("TipAliası {} ad={}", y(yer), q(ad)));
                self.iç(|w| w.tip("tip", tip));
            }
            C::Modul { yer, ad, gövdə } => {
                self.s(l, &format!("Modul {} ad={}", y(yer), q(ad)));
                self.iç(|w| w.gövdə("gövdə", gövdə));
            }
            C::Şərt { yer, budaqlar, yoxsa } => {
                self.s(l, &format!("Şərt {}", y(yer)));
                self.iç(|w| {
                    w.siyahı("budaqlar", budaqlar, |w, (ş, g)| {
                        w.s("", "Budaq");
                        w.iç(|w| {
                            w.ifadə("şərt", ş);
                            w.gövdə("gövdə", g);
                        });
                    });
                    w.ogövdə("yoxsa", yoxsa);
                });
            }
            C::Varsa { yer, bağlamalar, gövdə, yoxsa } => {
                self.s(l, &format!("Varsa {}", y(yer)));
                self.iç(|w| {
                    w.varsa_bağlamaları(bağlamalar);
                    w.gövdə("gövdə", gövdə);
                    w.ogövdə("yoxsa", yoxsa);
                });
            }
            C::Yoxdursa { yer, bağlamalar, gövdə } => {
                self.s(l, &format!("Yoxdursa {}", y(yer)));
                self.iç(|w| {
                    w.varsa_bağlamaları(bağlamalar);
                    w.gövdə("gövdə", gövdə);
                });
            }
            C::Seç { yer, ifadə, hallar, digər } => {
                self.s(l, &format!("Seç {}", y(yer)));
                self.iç(|w| {
                    w.oifadə("ifadə", ifadə);
                    w.siyahı("hallar", hallar, |w, h| {
                        w.s("", &format!("Hal keç={}", h.keç));
                        w.iç(|w| {
                            w.siyahı("naxışlar", &h.naxışlar, |w, n| w.naxış("", n));
                            w.oifadə("mühafizə", &h.mühafizə);
                            w.gövdə("gövdə", &h.gövdə);
                        });
                    });
                    w.ogövdə("digər", digər);
                });
            }
            C::NəQədərKi { yer, şərt, gövdə, etiket } => {
                self.s(l, &format!("NəQədərKi {} etiket={}", y(yer), oq(etiket)));
                self.iç(|w| {
                    w.ifadə("şərt", şərt);
                    w.gövdə("gövdə", gövdə);
                });
            }
            C::Həmişə { yer, gövdə, etiket } => {
                self.s(l, &format!("Həmişə {} etiket={}", y(yer), oq(etiket)));
                self.iç(|w| w.gövdə("gövdə", gövdə));
            }
            C::Təkrarla { yer, say, gövdə, sayğac, etiket } => {
                self.s(l, &format!("Təkrarla {} sayğac={} etiket={}", y(yer), oq(sayğac), oq(etiket)));
                self.iç(|w| {
                    w.ifadə("say", say);
                    w.gövdə("gövdə", gövdə);
                });
            }
            C::TəkrarlaNəQədər { yer, gövdə, şərt, etiket } => {
                self.s(l, &format!("TəkrarlaNəQədər {} etiket={}", y(yer), oq(etiket)));
                self.iç(|w| {
                    w.gövdə("gövdə", gövdə);
                    w.ifadə("şərt", şərt);
                });
            }
            C::Hər { yer, bağlamalar, mənbə, gövdə, addım, şərt, yoxsa, asinxron, etiket } => {
                self.s(l, &format!("Hər {} asinxron={} etiket={}", y(yer), asinxron, oq(etiket)));
                self.iç(|w| {
                    w.siyahı("bağlamalar", bağlamalar, |w, b| w.bağlama("", b));
                    w.ifadə("mənbə", mənbə);
                    w.oifadə("addım", addım);
                    w.oifadə("şərt", şərt);
                    w.gövdə("gövdə", gövdə);
                    w.ogövdə("yoxsa", yoxsa);
                });
            }
            C::Dayan(yer, e) => self.s(l, &format!("Dayan {} etiket={}", y(yer), oq(e))),
            C::DavamEt(yer, e) => self.s(l, &format!("DavamEt {} etiket={}", y(yer), oq(e))),
            C::Qaytar(yer, d) => {
                self.s(l, &format!("Qaytar {}", y(yer)));
                self.iç(|w| w.ifadələr("dəyərlər", d));
            }
            C::Ver(yer, d) => {
                self.s(l, &format!("Ver {}", y(yer)));
                self.iç(|w| w.oifadə("dəyər", d));
            }
            C::At(yer, d) => {
                self.s(l, &format!("At {}", y(yer)));
                self.iç(|w| w.oifadə("ifadə", d));
            }
            C::Cəhd { yer, gövdə, tutmalar, nəhayət } => {
                self.s(l, &format!("Cəhd {}", y(yer)));
                self.iç(|w| {
                    w.gövdə("gövdə", gövdə);
                    w.siyahı("tutmalar", tutmalar, |w, t| {
                        w.s("", &format!("Tutma ad={}", oq(&t.ad)));
                        w.iç(|w| {
                            w.siyahı("tiplər", &t.tiplər, |w, t| w.tip("", t));
                            w.oifadə("mühafizə", &t.mühafizə);
                            w.gövdə("gövdə", &t.gövdə);
                        });
                    });
                    w.ogövdə("nəhayət", nəhayət);
                });
            }
            C::İddia(yer, ş, m) => {
                self.s(l, &format!("İddia {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("şərt", ş);
                    w.oifadə("mesaj", m);
                });
            }
            C::Təmin(yer, ş, g) => {
                self.s(l, &format!("Təmin {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("şərt", ş);
                    w.gövdə("gövdə", g);
                });
            }
            C::Gecikdir(yer, e) => {
                self.s(l, &format!("Gecikdir {}", y(yer)));
                self.iç(|w| w.ifadə("ifadə", e));
            }
            C::İstifadə(yer, b, g) => {
                self.s(l, &format!("İstifadə {}", y(yer)));
                self.iç(|w| {
                    w.siyahı("bağlamalar", b, |w, (a, e)| {
                        w.s("", &format!("Cüt ad={}", q(a)));
                        w.iç(|w| w.ifadə("ifadə", e));
                    });
                    w.gövdə("gövdə", g);
                });
            }
            C::Keç(yer) => self.s(l, &format!("Keç {}", y(yer))),
            C::DayanNöqtəsi(yer) => self.s(l, &format!("DayanNöqtəsi {}", y(yer))),
            C::Global(yer, adlar) => self.s(l, &format!("Global {} adlar={}", y(yer), qs(adlar))),
            C::İdxal { yer, yol, mətn_yolu, ləqəb, elementlər, hamısı, python } => {
                self.s(
                    l,
                    &format!(
                        "İdxal {} yol={} mətn_yolu={} ləqəb={} hamısı={} python={}",
                        y(yer),
                        qs(yol),
                        oq(mətn_yolu),
                        oq(ləqəb),
                        hamısı,
                        python
                    ),
                );
                self.iç(|w| {
                    w.siyahı("elementlər", elementlər, |w, e| {
                        w.s("", &format!("Element ad={} ləqəb={}", q(&e.ad), oq(&e.ləqəb)))
                    })
                });
            }
            C::İxracSiyahısı(yer) => self.s(l, &format!("İxracSiyahısı {}", y(yer))),
            C::Başlanğıc(yer, g) => {
                self.s(l, &format!("Başlanğıc {}", y(yer)));
                self.iç(|w| w.gövdə("gövdə", g));
            }
            C::Bitiş(yer, g) => {
                self.s(l, &format!("Bitiş {}", y(yer)));
                self.iç(|w| w.gövdə("gövdə", g));
            }
            C::Artırma(yer, e, op) => {
                self.s(l, &format!("Artırma {} op={}", y(yer), q(op)));
                self.iç(|w| w.ifadə("hədəf", e));
            }
        }
    }

    fn varsa_bağlamaları(&mut self, b: &[(Option<Bağlama>, E)]) {
        self.siyahı("bağlamalar", b, |w, (b, e)| {
            w.s("", "Cüt");
            w.iç(|w| {
                if let Some(b) = b {
                    w.bağlama("bağlama", b);
                }
                w.ifadə("ifadə", e);
            });
        });
    }

    fn uşaqlar(&mut self, v: &[JSXUşaq]) {
        self.siyahı("uşaqlar", v, |w, u| match u {
            JSXUşaq::Mətn(s) => w.s("", &format!("Mətn {}", q(s))),
            JSXUşaq::İfadə(e) => w.ifadə("", e),
        });
    }

    fn ifadə(&mut self, l: &str, e: &İfadə) {
        use İfadə as I;
        match e {
            I::Literal(yer, d) => {
                let d = match d {
                    LiteralD::Tam(n) => format!("tam {}", n),
                    LiteralD::Onluq(x) => format!("onluq {:?}", x),
                    LiteralD::Mətn(s) => format!("mətn {}", q(s)),
                    LiteralD::Simvol(s) => format!("simvol {}", q(s)),
                    LiteralD::Bayt(b) => format!("bayt {:?}", b),
                    LiteralD::Məntiq(b) => format!("məntiq {}", b),
                    LiteralD::Boş => "boş".into(),
                };
                self.s(l, &format!("Literal {} {}", y(yer), d));
            }
            I::Şablon(yer, h) => {
                self.s(l, &format!("Şablon {}", y(yer)));
                self.iç(|w| {
                    w.siyahı("parçalar", h, |w, p| match p {
                        ŞablonHissə::Mətn(s) => w.s("", &format!("Mətn {}", q(s))),
                        ŞablonHissə::Kod(e, f) => {
                            w.s("", &format!("Kod format={}", oq(f)));
                            w.iç(|w| w.ifadə("ifadə", e));
                        }
                    })
                });
            }
            I::Ad(yer, a) => self.s(l, &format!("Ad {} {}", y(yer), q(a))),
            I::Özü(yer) => self.s(l, &format!("Özü {}", y(yer))),
            I::Üst(yer) => self.s(l, &format!("Üst {}", y(yer))),
            I::İkili(yer, a, op, b) => {
                self.s(l, &format!("İkili {} op={}", y(yer), q(op)));
                self.iç(|w| {
                    w.ifadə("sol", a);
                    w.ifadə("sağ", b);
                });
            }
            I::Tək(yer, op, a) => {
                self.s(l, &format!("Tək {} op={}", y(yer), q(op)));
                self.iç(|w| w.ifadə("operand", a));
            }
            I::Mənimsətmə(yer, h, op, d) => {
                self.s(l, &format!("Mənimsətmə {} op={}", y(yer), q(op)));
                self.iç(|w| {
                    w.ifadələr("hədəflər", h);
                    w.ifadələr("dəyərlər", d);
                });
            }
            I::Çevirmə(yer, a, t, th) => {
                self.s(l, &format!("Çevirmə {} təhlükəsiz={}", y(yer), th));
                self.iç(|w| {
                    w.ifadə("ifadə", a);
                    w.tip("tip", t);
                });
            }
            I::TipYoxlama(yer, a, t) => {
                self.s(l, &format!("TipYoxlama {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("ifadə", a);
                    w.tip("tip", t);
                });
            }
            I::Üzvlük(yer, a, b) => {
                self.s(l, &format!("Üzvlük {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("element", a);
                    w.ifadə("kolleksiya", b);
                });
            }
            I::BoşYoxlama(yer, a, inkar) => {
                self.s(l, &format!("BoşYoxlama {} inkar={}", y(yer), inkar));
                self.iç(|w| w.ifadə("ifadə", a));
            }
            I::Boru(yer, a, b) => {
                self.s(l, &format!("Boru {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("dəyər", a);
                    w.ifadə("funksiya", b);
                });
            }
            I::Diapazon(yer, b, s, addım, xaric) => {
                self.s(l, &format!("Diapazon {} xaric={}", y(yer), xaric));
                self.iç(|w| {
                    w.ifadə("başlanğıc", b);
                    w.ifadə("son", s);
                    w.oifadə("addım", addım);
                });
            }
            I::Çağırış(yer, f, a) => {
                self.s(l, &format!("Çağırış {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("funksiya", f);
                    w.arqumentlər("arqumentlər", a);
                });
            }
            I::Üzv(yer, o, ad, th) => {
                self.s(l, &format!("Üzv {} ad={} təhlükəsiz={}", y(yer), q(ad), th));
                self.iç(|w| w.ifadə("obyekt", o));
            }
            I::İndeks(yer, o, i) => {
                self.s(l, &format!("İndeks {}", y(yer)));
                self.iç(|w| {
                    w.ifadə("obyekt", o);
                    w.ifadə("indeks", i);
                });
            }
            I::Dilim(yer, o, b, s, xaric) => {
                self.s(l, &format!("Dilim {} xaric={}", y(yer), xaric));
                self.iç(|w| {
                    w.ifadə("obyekt", o);
                    w.oifadə("başlanğıc", b);
                    w.oifadə("son", s);
                });
            }
            I::MəcburiAçma(yer, a) => {
                self.s(l, &format!("MəcburiAçma {}", y(yer)));
                self.iç(|w| w.ifadə("ifadə", a));
            }
            I::Yayma(yer, a) => {
                self.s(l, &format!("Yayma {}", y(yer)));
                self.iç(|w| w.ifadə("ifadə", a));
            }
            I::Yeni(yer, t, qurucu, a) => {
                self.s(l, &format!("Yeni {} qurucu={}", y(yer), oq(qurucu)));
                self.iç(|w| {
                    w.tip("tip", t);
                    w.arqumentlər("arqumentlər", a);
                });
            }
            I::Gözlə(yer, a) => {
                self.s(l, &format!("Gözlə {}", y(yer)));
                self.iç(|w| w.ifadə("ifadə", a));
            }
            I::Siyahı(yer, el, yay) => {
                self.s(l, &format!("Siyahı {} yaymalar={:?}", y(yer), yay));
                self.iç(|w| w.ifadələr("elementlər", el));
            }
            I::Lüğət(yer, a, d) => {
                self.s(l, &format!("Lüğət {}", y(yer)));
                self.iç(|w| {
                    w.siyahı("açarlar", a, |w, e| match e {
                        Some(e) => w.ifadə("", e),
                        None => w.s("", "-"),
                    });
                    w.ifadələr("dəyərlər", d);
                });
            }
            I::Dəst(yer, el) => {
                self.s(l, &format!("Dəst {}", y(yer)));
                self.iç(|w| w.ifadələr("elementlər", el));
            }
            I::Kortej(yer, el) => {
                self.s(l, &format!("Kortej {}", y(yer)));
                self.iç(|w| w.ifadələr("elementlər", el));
            }
            I::Qurma { yer, növ, ifadə, dəyər_ifadəsi, bağlama, mənbə, şərt } => {
                self.s(l, &format!("Qurma {} növ={}", y(yer), q(növ)));
                self.iç(|w| {
                    w.ifadə("ifadə", ifadə);
                    w.oifadə("dəyər_ifadəsi", dəyər_ifadəsi);
                    w.bağlama("bağlama", bağlama);
                    w.ifadə("mənbə", mənbə);
                    w.oifadə("şərt", şərt);
                });
            }
            I::ŞərtIfadəsi(yer, b, yoxsa) => {
                self.s(l, &format!("ŞərtIfadəsi {}", y(yer)));
                self.iç(|w| {
                    w.siyahı("budaqlar", b, |w, (ş, d)| {
                        w.s("", "Budaq");
                        w.iç(|w| {
                            w.ifadə("şərt", ş);
                            w.ifadə("dəyər", d);
                        });
                    });
                    w.oifadə("yoxsa", yoxsa);
                });
            }
            I::Blok(yer, g) => {
                self.s(l, &format!("Blok {}", y(yer)));
                self.iç(|w| w.gövdə("gövdə", g));
            }
            I::Lambda { yer, parametrlər, gövdə, asinxron, generator } => {
                self.s(l, &format!("Lambda {} asinxron={} generator={}", y(yer), asinxron, generator));
                self.iç(|w| {
                    w.parametrlər("parametrlər", parametrlər);
                    match gövdə {
                        LambdaGövdə::Blok(g) => w.gövdə("gövdə", g),
                        LambdaGövdə::İfadə(e) => w.ifadə("ifadə", e),
                    }
                });
            }
            I::JSXElement(yer, ad, atr, u) => {
                self.s(l, &format!("JSXElement {} ad={}", y(yer), q(ad)));
                self.iç(|w| {
                    w.siyahı("atributlar", atr, |w, a| {
                        w.s("", &format!("Atribut ad={} yayma={}", q(&a.ad), a.yayma));
                        w.iç(|w| w.oifadə("dəyər", &a.dəyər));
                    });
                    w.uşaqlar(u);
                });
            }
            I::JSXParça(yer, u) => {
                self.s(l, &format!("JSXParça {}", y(yer)));
                self.iç(|w| w.uşaqlar(u));
            }
        }
    }
}

/// Proqramın kanonik çapı.
pub fn çap(p: &Proqram) -> String {
    let mut w = Yazıcı { ç: String::new(), d: 0 };
    w.gövdə("Proqram", &p.gövdə);
    w.ç
}
