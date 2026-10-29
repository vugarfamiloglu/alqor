//! AAC → bayt-kod kompilyatoru.
//!
//! Ad həlli: funksiya daxilində elan olunan hər ad ya **yuvaya** (sürətli,
//! nömrələnmiş yerli dəyişən), ya da **Mühit**-ə (ağac icraçısı ilə eyni
//! adlı əhatə zənciri) düşür. Ad Mühit-də saxlanılır, əgər o, adla axtarıla
//! bilən yerdə işlənirsə: iç funksiya/lambda gövdəsində, ağac icraçısına
//! ötürülən cümlədə/ifadədə, tip adlarında (`tipidir`, `yeni`). Bu adlar
//! əvvəlcə məlum olmadığı üçün kompilyasiya sabit nöqtəyə qədər təkrarlanır.
//!
//! Dəstəklənməyən konstruksiyalar ya ağac icraçısına ötürülür (`Ötür`),
//! ya da bütün funksiya ağac icraçısında qalır (`Dəstəkləmir`).

use super::emr::*;
use crate::aac::{self, Bağlama, BağlamaNöv, Cümlə, LiteralD, İfadə};
use crate::icraci::deyerler::{ad, Ad, FGövdə, D};
use crate::xeta::Yer;
use std::cell::Cell;
use std::collections::{HashMap, HashSet};
use std::rc::Rc;

/// Funksiya VM-də işləyə bilməz (ağac icraçısında qalır)
#[derive(Debug)]
pub struct Dəstəkləmir;

type K<T = ()> = Result<T, Dəstəkləmir>;

struct Əhatə {
    /// (ad, yuva) — `None`: Mühit-də
    adlar: Vec<(Ad, Option<u32>)>,
    mühitli: bool,
}

struct DövrK {
    etiket: Option<String>,
    dayan: Vec<usize>,
    davam: Vec<usize>,
    mühit: u32,
    iter: u32,
    cəhd: usize,
}

/// Kompilyasiya mənbəyi
pub enum Mənbə<'a> {
    /// `generator` — gövdə korutində işləyir: parametrlər əvvəlcədən Mühit-də
    /// bağlanıb (ağac icraçısının `parametrləri_bağla`-sı), son ifadə dəyəri yoxdur
    Funksiya { ad: &'a str, parametrlər: &'a Rc<Vec<aac::Parametr>>, gövdə: &'a FGövdə, generator: bool },
    Kök(&'a [Cümlə]),
}

struct Kompilyator<'r> {
    əmrlər: Vec<Əmr>,
    yerlər: Vec<Yer>,
    sabitlər: Vec<D>,
    adlar: Vec<Ad>,
    ad_xəritə: HashMap<Ad, u32>,
    tiplər: Vec<aac::Tip>,
    xətalar: Vec<(String, String, &'static str)>,
    cümlələr: Vec<Cümlə>,
    ifadələr: Vec<aac::E>,
    alt: Vec<AltFunksiya>,
    tutmalar: Vec<aac::Tutma>,
    bölgələr: Vec<Bölgə>,
    yuva_adları: Vec<Ad>,
    yuva_üst: Vec<Option<u32>>,
    keş_sayı: usize,
    əhatələr: Vec<Əhatə>,
    dövrlər: Vec<DövrK>,
    /// Açıq `cəhd` kontekstləri: `nəhayət` varmı
    cəhdlər: Vec<bool>,
    mühit: u32,
    iter: u32,
    r: &'r HashSet<String>,
    lazım: HashSet<String>,
    kök: bool,
    cəhd_sayı: u32,
    gecikdir_var: bool,
    sabit_var: bool,
    çağırış_keş_sayı: u32,
    üzv_keş_sayı: u32,
    /// İrəli keçidlərin hədəfləri (birləşdirmə bu nöqtələrdən keçə bilməz)
    keçid_hədəfləri: HashSet<u32>,
    param_yuvaları: Option<Vec<u32>>,
    gövdə_pc: u32,
}

// ═══════════════════════════════════════════════════════════════════════
//  Ad toplama (Debug çapından — yeni AAC qovşaqlarına qarşı dayanıqlı)
// ═══════════════════════════════════════════════════════════════════════

/// Alt ağacda rast gəlinən bütün mətnləri (adlar daxil) toplayır.
/// Artıq ad yığmaq təhlükəsizdir — yalnız həmin dəyişənlər yavaşlayır.
fn adları_topla<T: std::fmt::Debug>(x: &T, n: &mut HashSet<String>) {
    let s = format!("{:?}", x);
    let b = s.as_bytes();
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'"' {
            let mut j = i + 1;
            let mut t = String::new();
            let mut qaçış = false;
            let başla = j;
            while j < b.len() {
                if qaçış {
                    qaçış = false;
                } else if b[j] == b'\\' {
                    qaçış = true;
                } else if b[j] == b'"' {
                    break;
                }
                j += 1;
            }
            t.push_str(&s[başla..j.min(b.len())]);
            if !t.contains('\\') {
                n.insert(t);
            }
            i = j + 1;
        } else {
            i += 1;
        }
    }
    if s.contains("Özü(") || s.contains("Üst(") {
        n.insert("özü".into());
        n.insert("__sinif__".into());
    }
}

fn bağlama_adları(b: &Bağlama, n: &mut Vec<String>) {
    match &b.növ {
        BağlamaNöv::Ad(a) | BağlamaNöv::Qalan(a) => n.push(a.clone()),
        BağlamaNöv::Atma => {}
        BağlamaNöv::Kortej(alt) => {
            for x in alt {
                bağlama_adları(x, n);
            }
        }
        BağlamaNöv::Obyekt(s) => {
            for (a, alt) in s {
                match alt {
                    None => n.push(a.clone()),
                    Some(x) => bağlama_adları(x, n),
                }
            }
        }
    }
}

/// Blokun birbaşa elan etdiyi adlar (ağac icraçısının `əhatə`-si ilə eyni)
fn blok_adları(g: &[Cümlə], n: &mut Vec<String>) -> K {
    for c in g {
        match c {
            Cümlə::DəyişənElanı { bağlamalar, .. } => {
                for b in bağlamalar {
                    bağlama_adları(b, n);
                }
            }
            Cümlə::Funksiya(f) => n.push(f.ad.clone()),
            Cümlə::Sinif(s) => n.push(s.ad.clone()),
            Cümlə::İnterfeys { ad, .. }
            | Cümlə::Sadalama { ad, .. }
            | Cümlə::Qarışıq { ad, .. }
            | Cümlə::TipAliası { ad, .. }
            | Cümlə::Modul { ad, .. } => n.push(ad.clone()),
            Cümlə::Yoxdursa { bağlamalar, .. } => {
                for b in bağlamalar.iter().flat_map(|(b, _)| b.iter()) {
                    bağlama_adları(b, n);
                }
            }
            Cümlə::İdxal { yol, ləqəb, elementlər, hamısı, .. } => {
                if *hamısı {
                    return Err(Dəstəkləmir);
                }
                if !elementlər.is_empty() {
                    for e in elementlər {
                        n.push(e.ləqəb.clone().unwrap_or_else(|| e.ad.clone()));
                    }
                } else if let Some(l) = ləqəb {
                    n.push(l.clone());
                } else if let Some(y) = yol.last() {
                    n.push(y.clone());
                } else {
                    return Err(Dəstəkləmir);
                }
            }
            Cümlə::Global(..) => return Err(Dəstəkləmir),
            // Müqavilələr (§ 5.13) — funksiya ağac icraçısında qalır
            Cümlə::Tələb(..) | Cümlə::Zəmanət(..) => return Err(Dəstəkləmir),
            _ => {}
        }
    }
    Ok(())
}

fn kiçik_tam(e: &aac::E) -> Option<i32> {
    use num_traits::ToPrimitive;
    match &**e {
        İfadə::Literal(_, LiteralD::Tam(b)) => b.to_i32(),
        _ => None,
    }
}

fn onluq_tipidir(t: Option<&aac::Tip>) -> bool {
    matches!(t, Some(aac::Tip::Ad { yol, .. }) if yol.len() == 1 && yol[0] == "onluq")
}

/// Gövdədə (iç funksiyalar xaric) `gecikdir` varmı
fn gecikdir_axtar<T: std::fmt::Debug>(x: &T) -> bool {
    format!("{:?}", x).contains("Gecikdir(")
}

impl<'r> Kompilyator<'r> {
    fn yeni(r: &'r HashSet<String>, kök: bool) -> Self {
        Kompilyator {
            əmrlər: vec![],
            yerlər: vec![],
            sabitlər: vec![],
            adlar: vec![],
            ad_xəritə: HashMap::new(),
            tiplər: vec![],
            xətalar: vec![],
            cümlələr: vec![],
            ifadələr: vec![],
            alt: vec![],
            tutmalar: vec![],
            bölgələr: vec![],
            yuva_adları: vec![],
            yuva_üst: vec![],
            keş_sayı: 0,
            əhatələr: vec![],
            dövrlər: vec![],
            cəhdlər: vec![],
            mühit: 0,
            iter: 0,
            r,
            lazım: HashSet::new(),
            kök,
            cəhd_sayı: 0,
            gecikdir_var: false,
            sabit_var: false,
            çağırış_keş_sayı: 0,
            üzv_keş_sayı: 0,
            keçid_hədəfləri: HashSet::new(),
            param_yuvaları: None,
            gövdə_pc: 0,
        }
    }

    // ── Köməkçilər ────────────────────────────────────────────────────

    fn əmr(&mut self, ə: Əmr, yer: Yer) -> usize {
        self.əmrlər.push(ə);
        self.yerlər.push(yer);
        self.əmrlər.len() - 1
    }

    fn e(&mut self, ə: Əmr) -> usize {
        self.əmr(ə, Yer::default())
    }

    fn pc(&self) -> u32 {
        self.əmrlər.len() as u32
    }

    fn yamaq(&mut self, i: usize, h: u32) {
        self.keçid_hədəfləri.insert(h);
        match &mut self.əmrlər[i] {
            Əmr::Atla(x)
            | Əmr::YanlışsaAtla(x)
            | Əmr::ŞərtAtla(x)
            | Əmr::BoşDeyilsəAtla(x)
            | Əmr::BoşsaAtla(x)
            | Əmr::İterNövbəti(x)
            | Əmr::İterLüğətCüt(x)
            | Əmr::DiapazonDeyilsəAtla(x)
            | Əmr::ParamAl(_, x)
            | Əmr::ParamAdlı(_, x)
            | Əmr::MetodAl(_, _, x, _)
            | Əmr::Sayğac(_, _, x)
            | Əmr::TutmaYoxla(_, _, x)
            | Əmr::Qaç(x, _, _)
            | Əmr::MüqAtla(_, x, _)
            | Əmr::ŞərtT(_, _, x, _)
            | Əmr::DoğrusaAtla(x)
            | Əmr::İterGeri(x)
            | Əmr::SayğacGeri(_, _, x)
            | Əmr::ŞərtYT(_, _, _, x, _)
            | Əmr::ŞərtYY(_, _, _, x, _) => *x = h,
            _ => unreachable!("yamaq: keçid əmri deyil"),
        }
    }

    fn ad_i(&mut self, a: &str) -> u32 {
        let a = ad(a);
        if let Some(i) = self.ad_xəritə.get(&a) {
            return *i;
        }
        self.adlar.push(a.clone());
        let i = self.adlar.len() as u32 - 1;
        self.ad_xəritə.insert(a, i);
        i
    }

    fn sabit(&mut self, d: D) -> u32 {
        self.sabitlər.push(d);
        self.sabitlər.len() as u32 - 1
    }

    fn tip(&mut self, t: &aac::Tip) -> u32 {
        adları_topla(t, &mut self.lazım);
        self.tiplər.push(t.clone());
        self.tiplər.len() as u32 - 1
    }

    fn xəta(&mut self, tip: &str, mesaj: impl Into<String>, kod: &'static str, yer: Yer) {
        self.xətalar.push((tip.to_string(), mesaj.into(), kod));
        let i = self.xətalar.len() as u32 - 1;
        self.əmr(Əmr::Xəta(i), yer);
    }

    fn keş(&mut self) -> u32 {
        self.keş_sayı += 1;
        self.keş_sayı as u32 - 1
    }

    fn üzv_keşi(&mut self) -> u32 {
        self.üzv_keş_sayı += 1;
        self.üzv_keş_sayı - 1
    }

    fn çağırış_keşi(&mut self) -> u32 {
        self.çağırış_keş_sayı += 1;
        self.çağırış_keş_sayı - 1
    }

    fn gizli_yuva(&mut self) -> u32 {
        self.yuva_adları.push(ad(""));
        self.yuva_üst.push(None);
        self.yuva_adları.len() as u32 - 1
    }

    // ── Əhatələr ──────────────────────────────────────────────────────

    /// Yeni statik əhatə; adlardan biri Mühit-dədirsə `MühitAç` yazılır.
    fn əhatə_aç(&mut self, adlar: &[String]) {
        let mühitli = adlar.iter().any(|a| self.r.contains(a.as_str()));
        if mühitli {
            self.e(Əmr::MühitAç);
            self.mühit += 1;
        }
        self.əhatələr.push(Əhatə { adlar: vec![], mühitli });
    }

    fn əhatə_bağla(&mut self) {
        let ə = self.əhatələr.pop().unwrap();
        if ə.mühitli {
            self.e(Əmr::MühitBağla);
            self.mühit -= 1;
        }
    }

    fn kök_əhatəsi(&self) -> bool {
        self.kök && self.əhatələr.len() == 1
    }

    /// Adın yuvası (yerli dəyişəndirsə)
    fn həll(&self, a: &str) -> Option<u32> {
        if self.r.contains(a) {
            return None;
        }
        for ə in self.əhatələr.iter().rev() {
            if let Some((_, y)) = ə.adlar.iter().rev().find(|(x, _)| &**x == a) {
                return *y;
            }
        }
        None
    }

    fn ad_oxu(&mut self, a: &str, yer: Yer) {
        match self.həll(a) {
            Some(y) => {
                self.əmr(Əmr::YuvaAl(y), yer);
            }
            None => {
                let i = self.ad_i(a);
                let k = self.keş();
                self.əmr(Əmr::AdAl(i, k), yer);
            }
        }
    }

    fn ad_yaz(&mut self, a: &str, yer: Yer) {
        match self.həll(a) {
            Some(y) => {
                // Hesab nəticəsini birbaşa yuvaya yaz (araya keçid düşmürsə)
                if !self.keçid_hədəfləri.contains(&self.pc()) {
                    let birləşmiş = match self.əmrlər.last() {
                        Some(Əmr::İkili(o)) => Some(Əmr::İkiliQ(*o, y)),
                        Some(Əmr::İkiliT(o, n)) => Some(Əmr::İkiliTQ(*o, *n, y)),
                        Some(Əmr::İkiliYT(o, x, n)) => Some(Əmr::İkiliYTQ(*o, *x, *n, y)),
                        Some(Əmr::İkiliYY(o, x, z)) => Some(Əmr::İkiliYYQ(*o, *x, *z, y)),
                        _ => None,
                    };
                    if let Some(ə) = birləşmiş {
                        *self.əmrlər.last_mut().unwrap() = ə;
                        return;
                    }
                }
                self.əmr(Əmr::YuvaQoy(y), yer);
            }
            None => {
                let i = self.ad_i(a);
                let k = self.keş();
                self.əmr(Əmr::AdQoy(i, k), yer);
            }
        }
    }

    /// Cari əhatədə ad elan edir (dəyər yığındadır).
    fn ad_elan(&mut self, a: &str, sabit: bool, yer: Yer) -> K {
        self.ad_elan_yuva(a, sabit, yer).map(|_| ())
    }

    /// `ad_elan`; ad yuvaya düşübsə onun nömrəsi
    fn ad_elan_yuva(&mut self, a: &str, sabit: bool, yer: Yer) -> K<Option<u32>> {
        if sabit {
            self.sabit_var = true;
        }
        let mühitdə = self.kök_əhatəsi() || self.r.contains(a);
        if mühitdə {
            if !self.kök_əhatəsi() && !self.əhatələr.last().unwrap().mühitli {
                return Err(Dəstəkləmir);
            }
            let i = self.ad_i(a);
            self.əmr(if sabit { Əmr::AdElanSabit(i) } else { Əmr::AdElan(i) }, yer);
            self.əhatələr.last_mut().unwrap().adlar.push((ad(a), None));
            return Ok(None);
        }
        let mövcud = self.əhatələr.last().unwrap().adlar.iter().rev().find(|(x, _)| &**x == a).map(|(_, y)| *y);
        let y = match mövcud {
            Some(Some(y)) => y,
            _ => {
                let üst = self.həll(a);
                self.yuva_adları.push(ad(a));
                self.yuva_üst.push(üst);
                let y = self.yuva_adları.len() as u32 - 1;
                self.əhatələr.last_mut().unwrap().adlar.push((ad(a), Some(y)));
                y
            }
        };
        let birləşə_bilər = !self.keçid_hədəfləri.contains(&self.pc());
        let q = y | ELAN_BİTİ;
        // [hesab, Kopya] + elan → bir əmr (Q-əmrləri özləri kopyalayır)
        let n = self.əmrlər.len();
        if !sabit && birləşə_bilər && n >= 2 && matches!(self.əmrlər[n - 1], Əmr::Kopya) && !self.keçid_hədəfləri.contains(&(n as u32 - 1)) {
            let birləşmiş = match &self.əmrlər[n - 2] {
                Əmr::İkili(o) => Some(Əmr::İkiliQ(*o, q)),
                Əmr::İkiliT(o, k) => Some(Əmr::İkiliTQ(*o, *k, q)),
                Əmr::İkiliYT(o, x, k) => Some(Əmr::İkiliYTQ(*o, *x, *k, q)),
                Əmr::İkiliYY(o, x, z) => Some(Əmr::İkiliYYQ(*o, *x, *z, q)),
                _ => None,
            };
            if let Some(ə) = birləşmiş {
                self.əmrlər.pop();
                self.yerlər.pop();
                self.əmrlər[n - 2] = ə;
                return Ok(Some(y));
            }
        }
        let birləşmiş = match self.əmrlər.last() {
            _ if sabit || !birləşə_bilər => None,
            Some(Əmr::Kopya) => Some(Əmr::YuvaElanK(y)),
            Some(Əmr::İkili(o)) => Some(Əmr::İkiliQ(*o, q)),
            Some(Əmr::İkiliT(o, n)) => Some(Əmr::İkiliTQ(*o, *n, q)),
            Some(Əmr::İkiliYT(o, x, n)) => Some(Əmr::İkiliYTQ(*o, *x, *n, q)),
            Some(Əmr::İkiliYY(o, x, z)) => Some(Əmr::İkiliYYQ(*o, *x, *z, q)),
            _ => None,
        };
        if let Some(ə) = birləşmiş {
            *self.əmrlər.last_mut().unwrap() = ə;
        } else {
            self.əmr(if sabit { Əmr::YuvaElanSabit(y) } else { Əmr::YuvaElan(y) }, yer);
        }
        Ok(Some(y))
    }

    // ── Bağlama (dağıtma) ─────────────────────────────────────────────

    /// Yığındakı dəyəri bağlamaya elan edir.
    fn bağla(&mut self, b: &Bağlama, sabit: bool) -> K {
        match &b.növ {
            BağlamaNöv::Atma => {
                self.e(Əmr::At);
            }
            BağlamaNöv::Ad(a) => {
                if onluq_tipidir(b.tip.as_ref()) {
                    self.e(Əmr::Genişlət);
                }
                self.e(Əmr::Kopya);
                self.ad_elan(a, sabit, b.yer)?;
            }
            BağlamaNöv::Qalan(a) => self.ad_elan(a, sabit, b.yer)?,
            BağlamaNöv::Kortej(alt) => self.çoxlu_bağla(alt, sabit, b.yer)?,
            BağlamaNöv::Obyekt(sahələr) => {
                for (a, alt) in sahələr {
                    self.e(Əmr::Dup);
                    let i = self.ad_i(a);
                    self.əmr(Əmr::ÜzvAlXam(i), b.yer);
                    match alt {
                        None => self.ad_elan(a, sabit, b.yer)?,
                        Some(alt) => self.bağla(alt, sabit)?,
                    }
                }
                self.e(Əmr::At);
            }
        }
        Ok(())
    }

    fn çoxlu_bağla(&mut self, bağlamalar: &[Bağlama], sabit: bool, yer: Yer) -> K {
        let qalan = bağlamalar.iter().position(|b| matches!(b.növ, BağlamaNöv::Qalan(_)));
        self.əmr(Əmr::Dağıt(bağlamalar.len() as u32, qalan.map(|x| x as u32).unwrap_or(u32::MAX)), yer);
        for b in bağlamalar {
            self.bağla(b, sabit)?;
        }
        Ok(())
    }

    // ── Bloklar ───────────────────────────────────────────────────────

    /// Yeni əhatədə blok (`əlavə` — əhatəyə əvvəlcədən bağlanan adlar)
    fn blok_əhatəli(&mut self, g: &[Cümlə], əlavə: &[String]) -> K {
        let mut adlar = əlavə.to_vec();
        blok_adları(g, &mut adlar)?;
        self.əhatə_aç(&adlar);
        for c in g {
            self.cümlə(c)?;
        }
        self.əhatə_bağla();
        Ok(())
    }

    fn blok(&mut self, g: &[Cümlə]) -> K {
        self.blok_əhatəli(g, &[])
    }

    fn ötür(&mut self, c: &Cümlə) {
        adları_topla(c, &mut self.lazım);
        self.cümlələr.push(c.clone());
        let i = self.cümlələr.len() as u32 - 1;
        self.əmr(Əmr::Ötür(i), c.yer());
    }

    fn ötür_ifadə(&mut self, e: &aac::E) {
        adları_topla(e, &mut self.lazım);
        self.ifadələr.push(e.clone());
        let i = self.ifadələr.len() as u32 - 1;
        self.əmr(Əmr::Ötürİfadə(i), e.yer());
    }

    /// Dayan/davam/qaytar `nəhayət` blokundan keçirmi
    fn nəhayətdən_keçir(&self, dərinlik: usize) -> bool {
        self.cəhdlər[dərinlik..].iter().any(|x| *x)
    }

    fn dövr_başla(&mut self, etiket: &Option<String>) {
        self.dövrlər.push(DövrK {
            etiket: etiket.clone(),
            dayan: vec![],
            davam: vec![],
            mühit: self.mühit,
            iter: self.iter,
            cəhd: self.cəhdlər.len(),
        });
    }

    /// Dövrü bitirir: keçidləri yamaqlayır və bölgəni qeyd edir.
    fn dövr_bitir(&mut self, gövdə: (u32, u32), dayan: u32, davam: u32) {
        let d = self.dövrlər.pop().unwrap();
        for i in d.dayan {
            self.yamaq(i, dayan);
        }
        for i in d.davam {
            self.yamaq(i, davam);
        }
        self.bölgələr.push(Bölgə {
            başla: gövdə.0,
            son: gövdə.1,
            növ: BölgəNöv::Dövr(d.etiket.as_deref().map(ad), dayan, davam),
            mühit: d.mühit,
            iter: d.iter,
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    //  Cümlələr
    // ═══════════════════════════════════════════════════════════════════

    fn cümlə(&mut self, c: &Cümlə) -> K {
        match c {
            Cümlə::İfadə(_, e) => {
                if let İfadə::Mənimsətmə(yer, h, op, d) = &**e {
                    if self.mənimsətmə(e, *yer, h, op, d, false)? {
                        return Ok(());
                    }
                }
                self.ifadə(e)?;
                self.e(Əmr::At);
            }
            Cümlə::DəyişənElanı { yer, növ, bağlamalar, dəyərlər } => {
                let sabit = növ == "sabit" || növ == "dəyişməz";
                if dəyərlər.is_empty() {
                    for b in bağlamalar {
                        let t = match &b.tip {
                            Some(t) => {
                                self.tiplər.push(t.clone());
                                self.tiplər.len() as u32 - 1
                            }
                            None => u32::MAX,
                        };
                        self.e(Əmr::StandartDəyər(t));
                        self.bağla(b, sabit)?;
                    }
                } else if bağlamalar.len() == 1 {
                    if dəyərlər.len() == 1 {
                        self.ifadə(&dəyərlər[0])?;
                    } else {
                        for d in dəyərlər {
                            self.ifadə(d)?;
                        }
                        self.e(Əmr::Siyahı(dəyərlər.len() as u32));
                    }
                    self.bağla(&bağlamalar[0], sabit)?;
                } else if dəyərlər.len() == 1 {
                    self.ifadə(&dəyərlər[0])?;
                    self.çoxlu_bağla(bağlamalar, sabit, *yer)?;
                } else if dəyərlər.len() != bağlamalar.len() {
                    self.xəta(
                        "ArqumentXətası",
                        format!("{} ad, {} dəyər — saylar uyğun gəlmir", bağlamalar.len(), dəyərlər.len()),
                        "ALQ-T001",
                        *yer,
                    );
                } else {
                    let mut müv = vec![];
                    for d in dəyərlər {
                        self.ifadə(d)?;
                        müv.push(self.gizli_yuva());
                    }
                    for y in müv.iter().rev() {
                        self.e(Əmr::YuvaElan(*y));
                    }
                    for (b, y) in bağlamalar.iter().zip(müv) {
                        self.e(Əmr::YuvaAl(y));
                        self.bağla(b, sabit)?;
                    }
                }
            }
            Cümlə::Şərt { budaqlar, yoxsa, .. } => {
                let mut sonlar = vec![];
                for (ş, g) in budaqlar {
                    let j = self.şərt_atla(ş)?;
                    self.blok(g)?;
                    sonlar.push(self.e(Əmr::Atla(0)));
                    let h = self.pc();
                    self.yamaq(j, h);
                }
                if let Some(y) = yoxsa {
                    self.blok(y)?;
                }
                let h = self.pc();
                for j in sonlar {
                    self.yamaq(j, h);
                }
            }
            Cümlə::NəQədərKi { şərt, gövdə, etiket, .. } => {
                // Fırladılmış dövr: şərt sonda (hər iterasiyada bir keçid az)
                let giriş = self.e(Əmr::Atla(0));
                self.dövr_başla(etiket);
                let b = self.pc();
                self.blok(gövdə)?;
                let s = self.pc();
                self.yamaq(giriş, s);
                let j = self.şərt_keçid(şərt, true)?;
                self.yamaq(j, b);
                let son = self.pc();
                self.dövr_bitir((b, s), son, s);
            }
            Cümlə::Həmişə { gövdə, etiket, .. } => {
                let baş = self.pc();
                self.dövr_başla(etiket);
                self.blok(gövdə)?;
                let s = self.pc();
                self.e(Əmr::Atla(baş));
                let son = self.pc();
                self.dövr_bitir((baş, s), son, baş);
            }
            Cümlə::Təkrarla { yer, say, gövdə, sayğac, etiket } => {
                self.ifadə(say)?;
                self.əmr(Əmr::TəkrarSay, *yer);
                let hədd = self.gizli_yuva();
                let i = self.gizli_yuva();
                self.e(Əmr::YuvaElan(hədd));
                self.e(Əmr::Tam(0));
                self.e(Əmr::YuvaElan(i));
                let giriş = self.e(Əmr::Atla(0));
                self.dövr_başla(etiket);
                let b = self.pc();
                match sayğac {
                    Some(s) => {
                        let mut adlar = vec![s.clone()];
                        blok_adları(gövdə, &mut adlar)?;
                        self.əhatə_aç(&adlar);
                        self.e(Əmr::YuvaAl(i));
                        self.ad_elan(s, false, *yer)?;
                        for c in gövdə.iter() {
                            self.cümlə(c)?;
                        }
                        self.əhatə_bağla();
                    }
                    None => self.blok(gövdə)?,
                }
                let s = self.pc();
                self.yamaq(giriş, s);
                let j = self.e(Əmr::SayğacGeri(i, hədd, 0));
                self.yamaq(j, b);
                let son = self.pc();
                self.dövr_bitir((b, s), son, s);
            }
            Cümlə::TəkrarlaNəQədər { gövdə, şərt, etiket, .. } => {
                let baş = self.pc();
                self.dövr_başla(etiket);
                self.blok(gövdə)?;
                let s = self.pc();
                let j = self.şərt_keçid(şərt, true)?;
                self.yamaq(j, baş);
                let son = self.pc();
                self.dövr_bitir((baş, s), son, s);
            }
            Cümlə::Hər { yer, bağlamalar, mənbə, gövdə, addım, şərt, yoxsa, asinxron, etiket } => {
                self.hər(*yer, bağlamalar, mənbə, gövdə, addım.as_ref(), şərt.as_ref(), yoxsa.as_ref(), *asinxron, etiket)?;
            }
            Cümlə::Dayan(yer, e) | Cümlə::DavamEt(yer, e) => {
                let dayan = matches!(c, Cümlə::Dayan(..));
                let hədəf = self.dövrlər.iter().rposition(|d| match e {
                    None => true,
                    Some(e) => d.etiket.as_deref() == Some(e.as_str()),
                });
                let birbaşa = match hədəf {
                    Some(k) => !self.nəhayətdən_keçir(self.dövrlər[k].cəhd),
                    None => false,
                };
                if birbaşa {
                    let k = hədəf.unwrap();
                    let (m, it) = (self.dövrlər[k].mühit, self.dövrlər[k].iter);
                    let j = self.əmr(Əmr::Qaç(0, m, it), *yer);
                    if dayan {
                        self.dövrlər[k].dayan.push(j);
                    } else {
                        self.dövrlər[k].davam.push(j);
                    }
                } else {
                    let et = e.as_ref().map(|x| self.ad_i(x));
                    self.əmr(if dayan { Əmr::SiqnalDayan(et) } else { Əmr::SiqnalDavam(et) }, *yer);
                }
            }
            Cümlə::Qaytar(yer, dəyərlər) => {
                match dəyərlər.len() {
                    0 => {
                        self.e(Əmr::Boş);
                    }
                    1 => self.ifadə(&dəyərlər[0])?,
                    n => {
                        for d in dəyərlər {
                            self.ifadə(d)?;
                        }
                        self.e(Əmr::Kortej(n as u32));
                    }
                }
                if self.nəhayətdən_keçir(0) || self.kök {
                    self.əmr(Əmr::SiqnalQaytar, *yer);
                } else {
                    self.əmr(Əmr::Qaytar, *yer);
                }
            }
            Cümlə::At(yer, e) => match e {
                None => self.xəta("Xəta", "təkrar atılacaq xəta yoxdur", "", *yer),
                Some(e) => {
                    self.ifadə(e)?;
                    self.əmr(Əmr::AtXəta, *yer);
                }
            },
            Cümlə::Cəhd { gövdə, tutmalar, nəhayət, .. } => self.cəhd(gövdə, tutmalar, nəhayət.as_ref())?,
            // Sınaq bloku adi icrada atlanır; `gözlənilir` ağac icraçısına ötürülür
            Cümlə::Sınaq(..) => {}
            Cümlə::Gözlənti { .. } => self.ötür(c),
            Cümlə::İddia(yer, ş, mesaj) => {
                self.ifadə(ş)?;
                self.əmr(Əmr::MəntiqYoxla, ş.yer());
                let j = self.e(Əmr::YanlışsaAtla(0));
                let k = self.e(Əmr::Atla(0));
                let h = self.pc();
                self.yamaq(j, h);
                match mesaj {
                    Some(m) => {
                        self.ifadə(m)?;
                        self.əmr(Əmr::İddia(true), *yer);
                    }
                    None => {
                        self.əmr(Əmr::İddia(false), *yer);
                    }
                }
                let h = self.pc();
                self.yamaq(k, h);
            }
            Cümlə::Təmin(_, ş, gövdə) => {
                self.ifadə(ş)?;
                self.əmr(Əmr::MəntiqYoxla, ş.yer());
                self.e(Əmr::Deyil);
                let j = self.e(Əmr::YanlışsaAtla(0));
                self.blok(gövdə)?;
                let h = self.pc();
                self.yamaq(j, h);
            }
            Cümlə::Keç(_) | Cümlə::İxracSiyahısı(_) | Cümlə::Bitiş(..) => {}
            Cümlə::Başlanğıc(_, g) => self.blok(g)?,
            Cümlə::Artırma(yer, hədəf, op) => {
                if !self.hədəf_dəstəklənir(hədəf) {
                    self.ötür(c);
                    return Ok(());
                }
                self.ifadə(hədəf)?;
                self.əmr(Əmr::Artır(op == "++"), *yer);
                self.təyin(hədəf)?;
            }
            Cümlə::Funksiya(_) if crate::icraci::cagiris::bəzəyici_ola_bilər(c) => return Err(Dəstəkləmir),
            Cümlə::Funksiya(f) => {
                let yaddaşla = f.annotasiyalar.iter().any(|a| a == "yaddaşla");
                let i = self.alt_funksiya(
                    &f.ad,
                    f.parametrlər.clone(),
                    FGövdə::Blok(f.gövdə.clone().unwrap_or_default()),
                    f.asinxron,
                    f.generator,
                    yaddaşla,
                    c,
                );
                self.əmr(Əmr::Lambda(i), f.yer);
                self.ad_elan(&f.ad, false, f.yer)?;
            }
            Cümlə::Gecikdir(..) => {
                self.gecikdir_var = true;
                self.ötür(c);
            }
            Cümlə::Global(..) => return Err(Dəstəkləmir),
            Cümlə::İdxal { hamısı: true, .. } => return Err(Dəstəkləmir),
            Cümlə::Ver(..)
            | Cümlə::İstifadə(..)
            | Cümlə::DayanNöqtəsi(_)
            | Cümlə::Seç { .. }
            | Cümlə::Varsa { .. }
            | Cümlə::Yoxdursa { .. }
            | Cümlə::Sinif(_)
            | Cümlə::İnterfeys { .. }
            | Cümlə::Sadalama { .. }
            | Cümlə::Qarışıq { .. }
            | Cümlə::TipAliası { .. }
            | Cümlə::Genişlətmə { .. }
            | Cümlə::Modul { .. }
            | Cümlə::İdxal { .. }
            | Cümlə::Metod(_)
            | Cümlə::Xassə(_)
            | Cümlə::Qurucu(_)
            | Cümlə::Dağıdıcı(..) => {
                if gecikdir_axtar(c) {
                    self.gecikdir_var = true;
                }
                self.ötür(c);
            }
            #[allow(unreachable_patterns)]
            _ => return Err(Dəstəkləmir),
        }
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    fn alt_funksiya(
        &mut self,
        a: &str,
        parametrlər: Rc<Vec<aac::Parametr>>,
        gövdə: FGövdə,
        asinxron: bool,
        generator: bool,
        yaddaşla: bool,
        mənbə: &dyn std::fmt::Debug,
    ) -> u32 {
        adları_topla(&mənbə, &mut self.lazım);
        self.alt.push(AltFunksiya { ad: ad(a), parametrlər, gövdə, asinxron, generator, yaddaşla });
        self.alt.len() as u32 - 1
    }

    #[allow(clippy::too_many_arguments)]
    fn hər(
        &mut self,
        yer: Yer,
        bağlamalar: &[Bağlama],
        mənbə: &aac::E,
        gövdə: &aac::Gövdə,
        addım: Option<&aac::E>,
        şərt: Option<&aac::E>,
        yoxsa: Option<&aac::Gövdə>,
        asinxron: bool,
        etiket: &Option<String>,
    ) -> K {
        self.ifadə(mənbə)?;
        if let Some(a) = addım {
            let j = self.e(Əmr::DiapazonDeyilsəAtla(0));
            self.ifadə(a)?;
            self.əmr(Əmr::DiapazonAddım, yer);
            let h = self.pc();
            self.yamaq(j, h);
        }
        self.əmr(Əmr::İterAç, yer);
        self.iter += 1;
        // Fırladılmış dövr: növbəti element sonda alınır (`İterGeri`)
        let giriş = self.e(Əmr::Atla(0));
        let gövdə_başı = self.pc();
        if asinxron {
            self.əmr(Əmr::Gözlə, yer);
        }
        let mut adlar = vec![];
        for b in bağlamalar {
            bağlama_adları(b, &mut adlar);
        }
        blok_adları(gövdə, &mut adlar)?;
        self.əhatə_aç(&adlar);
        let sadə_ad = bağlamalar.len() == 1 && bağlamalar[0].tip.is_none() && matches!(bağlamalar[0].növ, BağlamaNöv::Ad(_));
        if sadə_ad {
            let BağlamaNöv::Ad(a) = &bağlamalar[0].növ else { unreachable!() };
            self.e(Əmr::Kopya);
            self.ad_elan(a, false, bağlamalar[0].yer)?;
        } else if bağlamalar.len() >= 2 {
            let j = self.əmr(Əmr::İterLüğətCüt(0), yer);
            self.çoxlu_bağla(bağlamalar, false, yer)?;
            let k = self.e(Əmr::Atla(0));
            let h = self.pc();
            self.yamaq(j, h);
            self.e(Əmr::İterİndeks);
            self.bağla(&bağlamalar[0], false)?;
            let qalan = &bağlamalar[1..];
            if qalan.len() == 1 {
                self.bağla(&qalan[0], false)?;
            } else {
                self.çoxlu_bağla(qalan, false, yer)?;
            }
            let h = self.pc();
            self.yamaq(k, h);
        } else {
            self.bağla(&bağlamalar[0], false)?;
        }
        let mut şərt_j = None;
        if let Some(ş) = şərt {
            şərt_j = Some(self.şərt_atla(ş)?);
        }
        self.dövr_başla(etiket);
        // Dövr bölgəsinin dərinlikləri: iterator daxil, iterasiya əhatəsi xaric
        self.dövrlər.last_mut().unwrap().mühit = self.mühit - self.əhatələr.last().unwrap().mühitli as u32;
        let b = self.pc();
        for c in gövdə.iter() {
            self.cümlə(c)?;
        }
        let s = self.pc();
        if let Some(j) = şərt_j {
            self.yamaq(j, s);
        }
        self.əhatə_bağla();
        let baş = self.pc();
        self.yamaq(giriş, baş);
        let geri = self.əmr(Əmr::İterGeri(0), yer);
        self.yamaq(geri, gövdə_başı);
        let son = self.pc();
        self.e(Əmr::İterBağla);
        let mut atla = None;
        if let Some(y) = yoxsa {
            // `yoxsa` iteratordan sonra
            self.iter -= 1;
            self.blok(y)?;
            self.iter += 1;
            atla = Some(self.e(Əmr::Atla(0)));
        }
        let dayan = self.pc();
        if atla.is_some() {
            self.e(Əmr::İterBağla);
        } else {
            // dayan: iterator hələ yığındadır — eyni `İterBağla`-ya keç
        }
        let dayan_hədəf = if atla.is_some() { dayan } else { son };
        let h = self.pc();
        if let Some(a) = atla {
            self.yamaq(a, h);
        }
        self.iter -= 1;
        self.dövr_bitir((b, s), dayan_hədəf, baş);
        Ok(())
    }

    fn cəhd(&mut self, gövdə: &aac::Gövdə, tutmalar: &[aac::Tutma], nəhayət: Option<&aac::Gövdə>) -> K {
        let id = self.cəhd_sayı;
        self.cəhd_sayı += 1;
        let nəh = nəhayət.is_some();
        let (mühit, iter) = (self.mühit, self.iter);
        self.cəhdlər.push(nəh);
        let b = self.pc();
        self.blok(gövdə)?;
        let s = self.pc();
        self.e(Əmr::CəhdTəmizlə(id));
        let mut fin_j = vec![self.e(Əmr::Atla(0))];
        let tutma_kodu = self.pc();
        for t in tutmalar {
            self.tutmalar.push(t.clone());
            let ti = self.tutmalar.len() as u32 - 1;
            let yox = self.e(Əmr::TutmaYoxla(id, ti, 0));
            let mut adlar = vec![];
            if let Some(a) = &t.ad {
                adlar.push(a.clone());
            }
            blok_adları(&t.gövdə, &mut adlar)?;
            self.əhatə_aç(&adlar);
            if let Some(a) = &t.ad {
                self.e(Əmr::XətaObyekti(id));
                self.ad_elan(a, false, Yer::default())?;
            }
            let mut mühafizə_j = None;
            if let Some(g) = &t.mühafizə {
                mühafizə_j = Some(self.şərt_atla(g)?);
            }
            self.e(Əmr::CəhdTəmizlə(id));
            for c in t.gövdə.iter() {
                self.cümlə(c)?;
            }
            let mühitli = self.əhatələr.last().unwrap().mühitli;
            self.əhatə_bağla();
            fin_j.push(self.e(Əmr::Atla(0)));
            if let Some(j) = mühafizə_j {
                // Mühafizə yanlışdır: əhatəni bağla, növbəti tutmaya keç
                let h = self.pc();
                self.yamaq(j, h);
                if mühitli {
                    self.e(Əmr::MühitBağla);
                }
            }
            let h = self.pc();
            self.yamaq(yox, h);
        }
        fin_j.push(self.e(Əmr::Atla(0)));
        let tutma_son = self.pc();
        self.cəhdlər.pop();
        let fin = self.pc();
        for j in fin_j {
            self.yamaq(j, fin);
        }
        if let Some(n) = nəhayət {
            self.blok(n)?;
        }
        self.e(Əmr::NəhayətSon(id));
        self.bölgələr.push(Bölgə { başla: b, son: s, növ: BölgəNöv::Cəhd(id, tutma_kodu, fin, nəh), mühit, iter });
        if nəh {
            self.bölgələr.push(Bölgə { başla: tutma_kodu, son: tutma_son, növ: BölgəNöv::Tutma(id, fin), mühit, iter });
        }
        Ok(())
    }

    // ═══════════════════════════════════════════════════════════════════
    //  Mənimsətmə
    // ═══════════════════════════════════════════════════════════════════

    fn hədəf_dəstəklənir(&self, h: &İfadə) -> bool {
        matches!(h, İfadə::Ad(..) | İfadə::Üzv(..) | İfadə::İndeks(..))
    }

    /// Yığındakı dəyəri hədəfə yazır (dəyər götürülür).
    fn təyin(&mut self, h: &İfadə) -> K {
        match h {
            İfadə::Ad(yer, a) => {
                // `YuvaQoy`/`AdQoy` dəyəri özləri kopyalayır
                self.ad_yaz(a, *yer);
            }
            İfadə::Üzv(yer, o, a, _) => {
                self.ifadə(o)?;
                let i = self.ad_i(a);
                let k = self.üzv_keşi();
                self.əmr(Əmr::ÜzvQoy(i, k), *yer);
            }
            İfadə::İndeks(yer, o, i) => {
                self.ifadə(o)?;
                self.ifadə(i)?;
                self.əmr(Əmr::İndeksQoy, *yer);
            }
            _ => return Err(Dəstəkləmir),
        }
        Ok(())
    }

    /// `false` — ağac icraçısına ötürülməlidir.
    fn mənimsətmə(&mut self, e: &aac::E, yer: Yer, hədəflər: &[aac::E], op: &str, dəyərlər: &[aac::E], dəyər_lazım: bool) -> K<bool> {
        if !hədəflər.iter().all(|h| self.hədəf_dəstəklənir(h)) || op == "??=" || op == "?=" {
            self.ötür_ifadə(e);
            if !dəyər_lazım {
                self.e(Əmr::At);
            }
            return Ok(true);
        }
        if hədəflər.len() > 1 || dəyərlər.len() > 1 {
            for d in dəyərlər {
                self.ifadə(d)?;
            }
            self.əmr(Əmr::Paketlə(hədəflər.len() as u32, dəyərlər.len() as u32), yer);
            for h in hədəflər {
                self.təyin(h)?;
            }
            if dəyər_lazım {
                self.e(Əmr::Boş);
            }
            return Ok(true);
        }
        let h = &hədəflər[0];
        if op == "=" {
            self.ifadə(&dəyərlər[0])?;
        } else {
            self.ikili(h, &op[..op.len() - 1], &dəyərlər[0], yer)?;
        }
        if dəyər_lazım {
            self.e(Əmr::Dup);
        }
        self.təyin(h)?;
        Ok(true)
    }

    // ═══════════════════════════════════════════════════════════════════
    //  İfadələr
    // ═══════════════════════════════════════════════════════════════════

    fn arqumentlər(&mut self, arq: &[aac::Arqument], yer: Yer) -> K<Option<u32>> {
        if arq.iter().any(|x| x.adlı_yayma) {
            return Err(Dəstəkləmir);
        }
        let sadə = arq.iter().all(|x| !x.yayma && x.ad.is_none());
        if sadə {
            for x in arq {
                self.ifadə(&x.dəyər)?;
            }
            return Ok(Some(arq.len() as u32));
        }
        self.e(Əmr::ArqYeni);
        for x in arq {
            self.ifadə(&x.dəyər)?;
            if x.yayma {
                self.əmr(Əmr::ArqYay, yer);
            } else if let Some(n) = &x.ad {
                let i = self.ad_i(n);
                self.e(Əmr::ArqAdlı(i));
            } else {
                self.e(Əmr::ArqMövqe);
            }
        }
        Ok(None)
    }

    fn ikili_əmr(&mut self, op: &str, yer: Yer) {
        match Op::yeni(op) {
            Some(o) => self.əmr(Əmr::İkili(o), yer),
            None => {
                let i = self.ad_i(op);
                self.əmr(Əmr::İkiliDigər(i), yer)
            }
        };
    }

    /// `sol op sağ` (yuva/sabit operandlar üçün birləşdirilmiş əmrlər)
    fn ikili(&mut self, sol: &aac::E, op: &str, sağ: &aac::E, yer: Yer) -> K {
        if let Some(o) = Op::yeni(op) {
            if let Some(y) = self.yuva_ifadəsi(sol) {
                if let Some(n) = kiçik_tam(sağ) {
                    self.əmr(Əmr::İkiliYT(o, y, n), yer);
                    return Ok(());
                }
                if let Some(y2) = self.yuva_ifadəsi(sağ) {
                    self.əmr(Əmr::İkiliYY(o, y, y2), yer);
                    return Ok(());
                }
            }
        }
        self.ifadə(sol)?;
        if let (Some(o), Some(n)) = (Op::yeni(op), kiçik_tam(sağ)) {
            self.əmr(Əmr::İkiliT(o, n), yer);
            return Ok(());
        }
        self.ifadə(sağ)?;
        self.ikili_əmr(op, yer);
        Ok(())
    }

    /// İfadə yerli yuvadırsa onun nömrəsi
    fn yuva_ifadəsi(&self, e: &aac::E) -> Option<u32> {
        match &**e {
            İfadə::Ad(_, a) => self.həll(a),
            _ => None,
        }
    }

    /// Şərti hesablayıb yanlışdırsa keçir; keçid əmrinin indeksi
    fn şərt_atla(&mut self, ş: &aac::E) -> K<usize> {
        self.şərt_keçid(ş, false)
    }

    /// Şərti hesablayıb `doğrusa`-ya bərabərdirsə keçir; keçid əmrinin indeksi
    fn şərt_keçid(&mut self, ş: &aac::E, doğrusa: bool) -> K<usize> {
        if let İfadə::İkili(yer, sol, op, sağ) = &**ş {
            if let Some(o) = Op::yeni(op).filter(|o| o.müqayisədir()) {
                if let Some(y) = self.yuva_ifadəsi(sol) {
                    if let Some(n) = kiçik_tam(sağ) {
                        return Ok(self.əmr(Əmr::ŞərtYT(o, y, n, 0, doğrusa), *yer));
                    }
                    if let Some(y2) = self.yuva_ifadəsi(sağ) {
                        return Ok(self.əmr(Əmr::ŞərtYY(o, y, y2, 0, doğrusa), *yer));
                    }
                }
                self.ifadə(sol)?;
                if let Some(n) = kiçik_tam(sağ) {
                    return Ok(self.əmr(Əmr::ŞərtT(o, n, 0, doğrusa), *yer));
                }
                self.ifadə(sağ)?;
                return Ok(self.əmr(Əmr::MüqAtla(o, 0, doğrusa), *yer));
            }
        }
        self.ifadə(ş)?;
        Ok(self.əmr(if doğrusa { Əmr::DoğrusaAtla(0) } else { Əmr::ŞərtAtla(0) }, ş.yer()))
    }

    fn ifadə(&mut self, e: &aac::E) -> K {
        match &**e {
            İfadə::Literal(_, l) => match l {
                LiteralD::Tam(b) => {
                    use num_traits::ToPrimitive;
                    match b.to_i64() {
                        Some(i) => {
                            self.e(Əmr::Tam(i));
                        }
                        None => {
                            let i = self.sabit(D::BT(Rc::new(b.clone())));
                            self.e(Əmr::Sabit(i));
                        }
                    }
                }
                LiteralD::Onluq(f) => {
                    let i = self.sabit(D::O(*f));
                    self.e(Əmr::Sabit(i));
                }
                LiteralD::Mətn(s) | LiteralD::Simvol(s) => {
                    let i = self.sabit(D::S(s.clone()));
                    self.e(Əmr::Sabit(i));
                }
                LiteralD::Bayt(b) => {
                    let i = self.sabit(D::Bayt(b.clone()));
                    self.e(Əmr::Sabit(i));
                }
                LiteralD::Məntiq(b) => {
                    self.e(Əmr::Məntiq(*b));
                }
                LiteralD::Boş => {
                    self.e(Əmr::Boş);
                }
            },
            İfadə::Şablon(_, parçalar) => {
                for p in parçalar {
                    match p {
                        aac::ŞablonHissə::Mətn(t) => {
                            let i = self.sabit(D::s(t));
                            self.e(Əmr::Sabit(i));
                        }
                        aac::ŞablonHissə::Kod(x, f) => {
                            self.ifadə(x)?;
                            let fi = match f {
                                Some(f) => self.sabit(D::s(f)),
                                None => u32::MAX,
                            };
                            self.əmr(Əmr::Formatla(fi), x.yer());
                        }
                    }
                }
                self.e(Əmr::Birləşdir(parçalar.len() as u32));
            }
            İfadə::Ad(yer, a) => self.ad_oxu(a, *yer),
            İfadə::Özü(yer) => self.ad_oxu("özü", *yer),
            İfadə::Üst(yer) => {
                self.ad_oxu("özü", *yer);
                self.ad_oxu("__sinif__", *yer);
                self.əmr(Əmr::ÜstQur, *yer);
            }
            İfadə::İkili(yer, sol, op, sağ) => match op.as_str() {
                "və" | "&&" => {
                    self.ifadə(sol)?;
                    self.əmr(Əmr::MəntiqYoxla, sol.yer());
                    let j = self.e(Əmr::YanlışsaAtla(0));
                    self.ifadə(sağ)?;
                    self.əmr(Əmr::MəntiqYoxla, sağ.yer());
                    let k = self.e(Əmr::Atla(0));
                    let h = self.pc();
                    self.yamaq(j, h);
                    self.e(Əmr::Məntiq(false));
                    let h = self.pc();
                    self.yamaq(k, h);
                }
                "və ya" | "||" => {
                    self.ifadə(sol)?;
                    self.əmr(Əmr::MəntiqYoxla, sol.yer());
                    let j = self.e(Əmr::YanlışsaAtla(0));
                    self.e(Əmr::Məntiq(true));
                    let k = self.e(Əmr::Atla(0));
                    let h = self.pc();
                    self.yamaq(j, h);
                    self.ifadə(sağ)?;
                    self.əmr(Əmr::MəntiqYoxla, sağ.yer());
                    let h = self.pc();
                    self.yamaq(k, h);
                }
                "??" => {
                    self.ifadə(sol)?;
                    let j = self.e(Əmr::BoşDeyilsəAtla(0));
                    self.ifadə(sağ)?;
                    let h = self.pc();
                    self.yamaq(j, h);
                }
                _ => self.ikili(sol, op, sağ, *yer)?,
            },
            İfadə::Tək(yer, op, x) => {
                if op == "deyil" || op == "!" {
                    self.ifadə(x)?;
                    self.əmr(Əmr::MəntiqYoxla, x.yer());
                    self.e(Əmr::Deyil);
                } else {
                    self.ifadə(x)?;
                    let k = match op.as_str() {
                        "-" => 0,
                        "+" => 1,
                        "~" => 2,
                        _ => {
                            self.e(Əmr::At);
                            self.xəta("DaxiliXəta", format!("naməlum tək operator `{}`", op), "", *yer);
                            return Ok(());
                        }
                    };
                    self.əmr(Əmr::Tək(k), *yer);
                }
            }
            İfadə::Mənimsətmə(yer, h, op, d) => {
                self.mənimsətmə(e, *yer, h, op, d, true)?;
            }
            İfadə::Çevirmə(yer, x, t, təhlükəsiz) => {
                self.ifadə(x)?;
                let i = self.ad_i(&t.tam_ad());
                self.əmr(Əmr::Çevir(i, *təhlükəsiz), *yer);
            }
            İfadə::TipYoxlama(yer, x, t) => {
                self.ifadə(x)?;
                let i = self.tip(t);
                self.əmr(Əmr::TipYoxla(i), *yer);
            }
            İfadə::Üzvlük(yer, x, k) => {
                self.ifadə(x)?;
                self.ifadə(k)?;
                self.əmr(Əmr::Üzvlük, *yer);
            }
            İfadə::BoşYoxlama(_, x, inkar) => {
                self.ifadə(x)?;
                self.e(Əmr::BoşYoxla(*inkar));
            }
            İfadə::Boru(yer, d, f) => {
                self.ifadə(d)?;
                self.ifadə(f)?;
                self.əmr(Əmr::Boru, *yer);
            }
            İfadə::Diapazon(yer, b, s, a, xaric) => {
                self.ifadə(b)?;
                self.ifadə(s)?;
                if let Some(a) = a {
                    self.ifadə(a)?;
                }
                self.əmr(Əmr::Diapazon(a.is_some(), *xaric), *yer);
            }
            İfadə::Çağırış(yer, f, arq) => {
                if let İfadə::Üzv(üyer, obyekt, a, təhlükəsiz) = &**f {
                    let mut boş_j = None;
                    if *təhlükəsiz {
                        self.ifadə(obyekt)?;
                        boş_j = Some(self.e(Əmr::BoşsaAtla(0)));
                    }
                    self.ifadə(obyekt)?;
                    let ai = self.ad_i(a);
                    let k = self.üzv_keşi();
                    let m = self.əmr(Əmr::MetodAl(ai, *təhlükəsiz, 0, k), *üyer);
                    match self.arqumentlər(arq, *yer)? {
                        Some(n) => {
                            let k = self.çağırış_keşi();
                            let tez = match a.as_ref() {
                                "əlavə" => 1,
                                "uzunluq" => 2,
                                "al" => 3,
                                "qoy" => 4,
                                _ => 0,
                            };
                            self.əmr(Əmr::MetodÇağır(ai, n, k, tez), *yer)
                        }
                        None => self.əmr(Əmr::MetodÇağırArq(ai), *yer),
                    };
                    let h = self.pc();
                    self.yamaq(m, h);
                    if let Some(j) = boş_j {
                        self.yamaq(j, h);
                    }
                } else {
                    self.ifadə(f)?;
                    match self.arqumentlər(arq, *yer)? {
                        Some(n) => {
                            let k = self.çağırış_keşi();
                            self.əmr(Əmr::Çağır(n, k), *yer)
                        }
                        None => self.əmr(Əmr::ÇağırArq, *yer),
                    };
                }
            }
            İfadə::Üzv(yer, o, a, təhlükəsiz) => {
                self.ifadə(o)?;
                let i = self.ad_i(a);
                let k = self.üzv_keşi();
                self.əmr(Əmr::ÜzvAl(i, *təhlükəsiz, k), *yer);
            }
            İfadə::İndeks(yer, o, i) => {
                self.ifadə(o)?;
                self.ifadə(i)?;
                self.əmr(Əmr::İndeksAl, *yer);
            }
            İfadə::Dilim(yer, o, b, s, xaric) => {
                self.ifadə(o)?;
                self.əmr(Əmr::DilimYoxla, *yer);
                if let Some(b) = b {
                    self.ifadə(b)?;
                }
                if let Some(s) = s {
                    self.ifadə(s)?;
                }
                self.əmr(Əmr::Dilim(b.is_some(), s.is_some(), *xaric), *yer);
            }
            İfadə::MəcburiAçma(yer, x) => {
                self.ifadə(x)?;
                self.əmr(Əmr::MəcburiAç, *yer);
            }
            İfadə::Yayma(yer, x) => {
                self.ifadə(x)?;
                self.əmr(Əmr::Yayma, *yer);
            }
            İfadə::Yeni(_, _, _, arq) if arq.iter().any(|x| x.adlı_yayma) => return Err(Dəstəkləmir),
            İfadə::Yeni(yer, t, qurucu, arq) => {
                let ti = self.tip(t);
                self.əmr(Əmr::TipDəyəri(ti), *yer);
                self.e(Əmr::ArqYeni);
                for x in arq {
                    self.ifadə(&x.dəyər)?;
                    if x.yayma {
                        self.əmr(Əmr::ArqYay, *yer);
                    } else if let Some(n) = &x.ad {
                        let i = self.ad_i(n);
                        self.e(Əmr::ArqAdlı(i));
                    } else {
                        self.e(Əmr::ArqMövqe);
                    }
                }
                let q = match qurucu {
                    Some(q) => self.ad_i(q),
                    None => u32::MAX,
                };
                self.əmr(Əmr::Yeni(q), *yer);
            }
            İfadə::Gözlə(yer, x) => {
                self.ifadə(x)?;
                self.əmr(Əmr::Gözlə, *yer);
            }
            İfadə::Siyahı(yer, el, yaymalar) => {
                if !yaymalar.iter().any(|x| *x) {
                    for x in el {
                        self.ifadə(x)?;
                    }
                    self.e(Əmr::Siyahı(el.len() as u32));
                } else {
                    self.e(Əmr::SiyahıYeni);
                    for (i, x) in el.iter().enumerate() {
                        self.ifadə(x)?;
                        if yaymalar.get(i).copied().unwrap_or(false) {
                            self.əmr(Əmr::SiyahıYay, *yer);
                        } else {
                            self.e(Əmr::SiyahıƏlavə);
                        }
                    }
                }
            }
            İfadə::Lüğət(yer, açarlar, dəyərlər) => {
                self.e(Əmr::LüğətYeni);
                for (a, d) in açarlar.iter().zip(dəyərlər.iter()) {
                    self.ifadə(d)?;
                    match a {
                        None => {
                            self.əmr(Əmr::LüğətYay, *yer);
                        }
                        Some(a) => {
                            self.ifadə(a)?;
                            self.əmr(Əmr::LüğətQoy, *yer);
                        }
                    }
                }
            }
            İfadə::Dəst(yer, el) => {
                self.e(Əmr::DəstYeni);
                for x in el {
                    self.ifadə(x)?;
                    self.əmr(Əmr::DəstƏlavə, *yer);
                }
            }
            İfadə::Kortej(_, el) => {
                for x in el {
                    self.ifadə(x)?;
                }
                self.e(Əmr::Kortej(el.len() as u32));
            }
            İfadə::Qurma { yer, növ, ifadə, dəyər_ifadəsi, bağlama, mənbə, şərt } => {
                let yuva = self.gizli_yuva();
                if növ == "lüğət" {
                    self.e(Əmr::LüğətYeni);
                } else {
                    self.e(Əmr::Siyahı(0));
                }
                self.e(Əmr::YuvaElan(yuva));
                self.ifadə(mənbə)?;
                self.əmr(Əmr::İterAç, *yer);
                self.iter += 1;
                let baş = self.pc();
                let növbəti = self.əmr(Əmr::İterNövbəti(0), *yer);
                let mut adlar = vec![];
                bağlama_adları(bağlama, &mut adlar);
                self.əhatə_aç(&adlar);
                self.bağla(bağlama, false)?;
                let mut şj = None;
                if let Some(ş) = şərt {
                    şj = Some(self.şərt_atla(ş)?);
                }
                if növ == "lüğət" {
                    self.ifadə(ifadə)?;
                    self.əmr(Əmr::AçarYoxla, *yer);
                    match dəyər_ifadəsi {
                        Some(d) => self.ifadə(d)?,
                        None => {
                            self.e(Əmr::Boş);
                        }
                    }
                    self.əmr(Əmr::QurmaLüğət(yuva), *yer);
                } else {
                    self.ifadə(ifadə)?;
                    self.e(Əmr::QurmaƏlavə(yuva));
                }
                let h = self.pc();
                if let Some(j) = şj {
                    self.yamaq(j, h);
                }
                self.əhatə_bağla();
                self.e(Əmr::Atla(baş));
                let son = self.pc();
                self.yamaq(növbəti, son);
                self.e(Əmr::İterBağla);
                self.iter -= 1;
                let n = match növ.as_str() {
                    "lüğət" => 3,
                    "dəst" => 1,
                    "generator" => 2,
                    _ => 0,
                };
                self.əmr(Əmr::QurmaSon(yuva, n), *yer);
            }
            İfadə::ŞərtIfadəsi(_, budaqlar, yoxsa) => {
                let mut sonlar = vec![];
                for (ş, d) in budaqlar {
                    let j = self.şərt_atla(ş)?;
                    self.ifadə(d)?;
                    sonlar.push(self.e(Əmr::Atla(0)));
                    let h = self.pc();
                    self.yamaq(j, h);
                }
                match yoxsa {
                    Some(y) => self.ifadə(y)?,
                    None => {
                        self.e(Əmr::Boş);
                    }
                }
                let h = self.pc();
                for j in sonlar {
                    self.yamaq(j, h);
                }
            }
            İfadə::Lambda { yer, parametrlər, gövdə, asinxron, generator } => {
                let g = match gövdə {
                    aac::LambdaGövdə::Blok(g) => FGövdə::Blok(g.clone()),
                    aac::LambdaGövdə::İfadə(x) => FGövdə::İfadə(x.clone()),
                };
                let i = self.alt_funksiya("<anonim>", parametrlər.clone(), g, *asinxron, *generator, false, &**e);
                self.əmr(Əmr::Lambda(i), *yer);
            }
            İfadə::Blok(..) | İfadə::JSXElement(..) | İfadə::JSXParça(..) | İfadə::Sorğu(..) | İfadə::VahidliƏdəd(..) => self.ötür_ifadə(e),
            #[allow(unreachable_patterns)]
            _ => self.ötür_ifadə(e),
        }
        Ok(())
    }

    // ═══════════════════════════════════════════════════════════════════
    //  Funksiya
    // ═══════════════════════════════════════════════════════════════════

    fn parametrlər(&mut self, ps: &[aac::Parametr]) -> K {
        let mövqeli: Vec<usize> = (0..ps.len()).filter(|&i| !ps[i].variadic && !ps[i].adlı_variadic && !ps[i].yalnız_adlı).collect();
        let mut sadə = mövqeli.len() == ps.len() && ps.iter().all(|p| p.xassə_görünüşü.is_none());
        let mut yuvalar = vec![];
        for &pi in &mövqeli {
            let p = &ps[pi];
            let j = self.e(Əmr::ParamAl(pi as u32, 0));
            if let Some(s) = &p.standart {
                self.ifadə(s)?;
            }
            let h = self.pc();
            self.yamaq(j, h);
            if onluq_tipidir(p.tip.as_ref()) {
                self.e(Əmr::Genişlət);
                sadə = false;
            }
            self.e(Əmr::Kopya);
            match self.ad_elan_yuva(&p.ad, false, p.yer)? {
                Some(y) => yuvalar.push(y),
                None => sadə = false,
            }
        }
        for (pi, p) in ps.iter().enumerate().filter(|(_, p)| p.yalnız_adlı) {
            let j = self.e(Əmr::ParamAdlı(pi as u32, 0));
            if let Some(s) = &p.standart {
                self.ifadə(s)?;
            }
            let h = self.pc();
            self.yamaq(j, h);
            self.ad_elan(&p.ad, false, p.yer)?;
        }
        if let Some(v) = ps.iter().find(|p| p.variadic) {
            self.e(Əmr::ParamVariadic);
            self.ad_elan(&v.ad, false, v.yer)?;
        }
        if let Some(v) = ps.iter().find(|p| p.adlı_variadic) {
            self.e(Əmr::ParamAdlıVariadic);
            self.ad_elan(&v.ad, false, v.yer)?;
        }
        self.e(Əmr::ParamSon);
        for p in ps.iter() {
            if p.xassə_görünüşü.is_some() {
                self.ad_oxu(&p.ad, p.yer);
                let i = self.ad_i(&p.ad);
                self.e(Əmr::XassəQoy(i));
            }
        }
        self.gövdə_pc = self.pc();
        if sadə {
            self.param_yuvaları = Some(yuvalar);
        }
        Ok(())
    }

    /// Funksiya gövdəsinin sonu: son ifadənin dəyəri (xəta → boş)
    fn son_ifadə(&mut self, g: &[Cümlə]) -> K {
        match g.last() {
            Some(Cümlə::İfadə(_, e)) if !matches!(&**e, İfadə::Mənimsətmə(..) | İfadə::Çağırış(..)) => {
                let b = self.pc();
                self.ifadə(e)?;
                let s = self.pc();
                self.bölgələr.push(Bölgə { başla: b, son: s, növ: BölgəNöv::XətaBoş(s), mühit: self.mühit, iter: self.iter });
            }
            _ => {
                self.e(Əmr::Boş);
            }
        }
        self.e(Əmr::Qaytar);
        Ok(())
    }

    fn bitir(self, ad_: &str, növ: KodNövü, parametrlər: Option<Rc<Vec<aac::Parametr>>>, gövdə: Option<FGövdə>, özü: (Option<u32>, Option<u32>), funksiya_mühiti: bool) -> Kod {
        let (mövqeli_say, variadic_var) = match &parametrlər {
            Some(ps) => (
                ps.iter().filter(|p| !p.variadic && !p.adlı_variadic && !p.yalnız_adlı).count(),
                ps.iter().any(|p| p.variadic),
            ),
            None => (0, false),
        };
        Kod {
            ad: ad_.to_string(),
            növ,
            əmrlər: self.əmrlər,
            yerlər: self.yerlər,
            sabitlər: self.sabitlər,
            adlar: self.adlar,
            tiplər: self.tiplər,
            xətalar: self.xətalar,
            cümlələr: self.cümlələr,
            ifadələr: self.ifadələr,
            alt_funksiyalar: self.alt,
            tutmalar: self.tutmalar,
            bölgələr: self.bölgələr,
            yuva_sayı: self.yuva_adları.len(),
            yuva_adları: self.yuva_adları,
            yuva_üst: self.yuva_üst,
            özü_yuvası: özü.0,
            sinif_yuvası: özü.1,
            funksiya_mühiti,
            cəhd_sayı: self.cəhd_sayı as usize,
            gecikdir_var: self.gecikdir_var,
            keşlər: (0..self.keş_sayı).map(|_| Cell::new((0, 0))).collect(),
            mövqeli_say,
            variadic_var,
            sabit_var: self.sabit_var,
            param_yuvaları: self.param_yuvaları,
            gövdə_pc: self.gövdə_pc,
            çağırış_keşləri: (0..self.çağırış_keş_sayı).map(|_| Default::default()).collect(),
            üzv_keşləri: (0..self.üzv_keş_sayı).map(|_| Default::default()).collect(),
            parametrlər,
            _gövdə: gövdə,
        }
    }
}

fn bir_dəfə(m: &Mənbə, r: &HashSet<String>) -> K<(Kod, HashSet<String>)> {
    match m {
        Mənbə::Kök(gövdə) => {
            let mut k = Kompilyator::yeni(r, true);
            k.əhatələr.push(Əhatə { adlar: vec![], mühitli: true });
            for c in gövdə.iter() {
                if !crate::icraci::cagiris::elandır(c) {
                    k.cümlə(c)?;
                }
            }
            k.e(Əmr::Boş);
            k.e(Əmr::Qaytar);
            let lazım = std::mem::take(&mut k.lazım);
            Ok((k.bitir("<kök>", KodNövü::Kök, None, None, (None, None), false), lazım))
        }
        Mənbə::Funksiya { ad: a, parametrlər, gövdə, generator } => {
            let mut k = Kompilyator::yeni(r, false);
            let mut adlar: Vec<String> = parametrlər.iter().map(|p| p.ad.clone()).collect();
            adlar.push("özü".into());
            adlar.push("__sinif__".into());
            if let FGövdə::Blok(g) = gövdə {
                blok_adları(g, &mut adlar)?;
            }
            let mühitli = adlar.iter().any(|a| r.contains(a.as_str()));
            if mühitli {
                k.mühit = 1;
            }
            k.əhatələr.push(Əhatə { adlar: vec![], mühitli });
            // özü və __sinif__ — yuva və ya Mühit
            let mut özü = (None, None);
            for (i, a) in ["özü", "__sinif__"].iter().enumerate() {
                if r.contains(*a) {
                    k.əhatələr[0].adlar.push((ad(a), None));
                } else {
                    k.yuva_adları.push(ad(a));
                    k.yuva_üst.push(None);
                    let y = k.yuva_adları.len() as u32 - 1;
                    k.əhatələr[0].adlar.push((ad(a), Some(y)));
                    if i == 0 {
                        özü.0 = Some(y);
                    } else {
                        özü.1 = Some(y);
                    }
                }
            }
            if *generator {
                for p in parametrlər.iter() {
                    k.əhatələr[0].adlar.push((ad(&p.ad), None));
                }
            } else {
                k.parametrlər(parametrlər)?;
            }
            let növ = match gövdə {
                FGövdə::Blok(g) => {
                    for c in g.iter() {
                        k.cümlə(c)?;
                    }
                    if *generator {
                        k.e(Əmr::Boş);
                        k.e(Əmr::Qaytar);
                        // korutində `gecikdir` ağac icraçısındakı kimi dərhal icra olunur
                        k.gecikdir_var = false;
                    } else {
                        k.son_ifadə(g)?;
                    }
                    KodNövü::Blok
                }
                FGövdə::İfadə(_) if *generator => {
                    k.e(Əmr::Boş);
                    k.e(Əmr::Qaytar);
                    KodNövü::Blok
                }
                FGövdə::İfadə(e) => {
                    k.ifadə(e)?;
                    k.e(Əmr::Qaytar);
                    KodNövü::İfadə
                }
            };
            let lazım = std::mem::take(&mut k.lazım);
            Ok((k.bitir(a, növ, Some((*parametrlər).clone()), Some((*gövdə).clone()), özü, mühitli), lazım))
        }
    }
}

/// Sabit nöqtəyə qədər kompilyasiya: Mühit-də saxlanılmalı adlar dəyişməyənə qədər.
pub fn kompilyasiya(m: &Mənbə) -> K<Kod> {
    let mut r: HashSet<String> = HashSet::new();
    if let Mənbə::Funksiya { parametrlər, generator: true, .. } = m {
        r.extend(parametrlər.iter().map(|p| p.ad.clone()));
        r.insert("özü".into());
        r.insert("__sinif__".into());
    }
    for _ in 0..6 {
        let (kod, lazım) = bir_dəfə(m, &r)?;
        if lazım.iter().all(|a| r.contains(a)) {
            return Ok(kod);
        }
        r.extend(lazım);
    }
    Err(Dəstəkləmir)
}
