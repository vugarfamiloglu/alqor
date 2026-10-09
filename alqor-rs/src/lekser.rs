//! Lekser (lekser.py-ın birə-bir köçürməsi).

use crate::acar;
use crate::elifba::{ad_başlanğıcı, ad_davamı, hərfdir, rəqəmdir};
use crate::xeta::{mənbə_id, Mənbə, XətaToplayıcı, Yer};
use num_bigint::BigInt;
use std::rc::Rc;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Növ {
    Tam,
    Onluq,
    Mətn,
    Simvol,
    Bayt,
    Ad,
    Acar,
    Op,
    Jsx,
    SətirSonu,
    FaylSonu,
    Sənəd,
    Direktiv,
}

#[derive(Clone, Debug)]
pub enum Parça {
    Mətn(String),
    Kod(Vec<Token>, Option<String>),
}

#[derive(Clone, Debug)]
pub struct Token {
    pub növ: Növ,
    pub s: String,          // AD/ACAR/OP/METN/SIMVOL dəyəri
    pub tam: Option<BigInt>,
    pub onluq: f64,
    pub bayt: Vec<u8>,
    pub jsx: (usize, usize),
    pub yer: Yer,
    pub xam: String,
    pub parçalar: Option<Vec<Parça>>,
}

impl Token {
    pub fn yeni(növ: Növ, s: &str, yer: Yer) -> Token {
        Token { növ, s: s.to_string(), tam: None, onluq: 0.0, bayt: vec![], jsx: (0, 0), yer,
                xam: String::new(), parçalar: None }
    }
    pub fn acardır(&self, h: &[&str]) -> bool {
        self.növ == Növ::Acar && h.contains(&self.s.as_str())
    }
    pub fn opdur(&self, h: &[&str]) -> bool {
        self.növ == Növ::Op && h.contains(&self.s.as_str())
    }
    pub fn literaldır(&self) -> bool {
        matches!(self.növ, Növ::Tam | Növ::Onluq | Növ::Mətn | Növ::Simvol | Növ::Bayt)
    }
    pub fn sadə_mətndir(&self) -> bool {
        self.növ == Növ::Mətn
            && !self.parçalar.as_ref().map(|p| p.iter().any(|x| matches!(x, Parça::Kod(..)))).unwrap_or(false)
    }
    pub fn göstər(&self) -> String {
        match self.növ {
            Növ::SətirSonu => "sətir sonu".into(),
            Növ::FaylSonu => "fayl sonu".into(),
            Növ::Tam => self.tam.as_ref().map(|t| t.to_string()).unwrap_or_default(),
            Növ::Onluq => format!("{}", self.onluq),
            _ => self.s.clone(),
        }
    }
}

const OP3: &[&str] = &["**=", "~/=", "<<=", ">>=", ">>>", "..<", "...", "??=", "<=>"];
const OP2: &[&str] = &["+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "==", "!=", "<=", ">=",
    "&&", "||", "<<", ">>", "**", "~/", "??", "?.", "?=", "..", "->", "=>", "|>", "++", "--"];
const OP1: &[&str] = &["+", "-", "*", "/", "%", "=", "<", ">", "!", "&", "|", "^", "~", "?", ".",
    ",", ";", ":", "@", "#", "(", ")", "[", "]", "{", "}", "→"];
pub const IFADE_BITIREN_OP: &[&str] = &[")", "]", "}", "!", "++", "--", "?"];
pub const IFADE_BITIREN_LIT: &[&str] = &["doğru", "yanlış", "boş", "özü", "üst", "sonsuz", "ƏdədDeyil"];

#[derive(Clone, Copy, PartialEq)]
enum Kontekst {
    Mötərizə,
    Blok,
}

pub struct Lekser<'a> {
    pub s: Rc<Mənbə>,
    pub m: Vec<char>,
    pub n: usize,
    pub i: usize,
    pub x: &'a mut XətaToplayıcı,
    mid: u32,
    yığın: Vec<Kontekst>,
    pub ascii_xəbərdarlığı: bool,
    tab_verildi: bool,
}

fn op_tap(m: &[char], i: usize) -> Option<&'static str> {
    for cədvəl in [OP3, OP2, OP1] {
        for op in cədvəl {
            let uz = op.chars().count();
            if i + uz <= m.len() && m[i..i + uz].iter().copied().eq(op.chars()) {
                return Some(op);
            }
        }
    }
    None
}

impl<'a> Lekser<'a> {
    pub fn yeni(s: Rc<Mənbə>, x: &'a mut XətaToplayıcı) -> Lekser<'a> {
        let m = s.mətn.clone();
        let n = m.len();
        let mid = mənbə_id(&s);
        Lekser { s, m, n, i: 0, x, mid, yığın: vec![], ascii_xəbərdarlığı: true, tab_verildi: false }
    }

    pub fn yer(&self, b: usize, uz: usize) -> Yer {
        Yer { mənbə: self.mid, başlanğıc: b as u32, uzunluq: uz as u32 }
    }

    fn gör(&self, irəli: usize) -> Option<char> {
        self.m.get(self.i + irəli).copied()
    }

    fn başlayır(&self, i: usize, s: &str) -> bool {
        let mut j = i;
        for c in s.chars() {
            if self.m.get(j) != Some(&c) {
                return false;
            }
            j += 1;
        }
        true
    }

    fn parça(&self, b: usize, s: usize) -> String {
        self.m[b..s.min(self.n)].iter().collect()
    }

    pub fn leksə(&mut self) -> Vec<Token> {
        let mut t = vec![];
        if self.başlayır(0, "#!") {
            self.i = self.m.iter().position(|c| *c == '\n').map(|p| p + 1).unwrap_or(self.n);
        }
        while self.i < self.n {
            if self.x.dolubmu() {
                break;
            }
            self.token_oxu(&mut t, false);
        }
        self.sətir_sonu(&mut t);
        t.push(Token::yeni(Növ::FaylSonu, "", self.yer(self.n, 0)));
        t
    }

    pub fn token_oxu(&mut self, h: &mut Vec<Token>, interpolyasiyada: bool) {
        if self.boşluq_atla(interpolyasiyada) {
            return;
        }
        if self.i >= self.n {
            return;
        }
        let c = self.m[self.i];
        let baş = self.i;
        if c == '\n' {
            self.i += 1;
            if !interpolyasiyada {
                self.sətir_sonu(h);
            }
            return;
        }
        if c == '/' && matches!(self.gör(1), Some('/') | Some('*')) {
            self.şərh_oxu(h);
            return;
        }
        if (c == 'x' || c == 'b') && self.gör(1) == Some('"') {
            self.i += 1;
            self.mətn_oxu(h, baş, c == 'x', c == 'b');
            return;
        }
        if c == '"' || c == '\'' {
            self.mətn_oxu(h, baş, false, false);
            return;
        }
        if c == '`' {
            self.simvol_oxu(h);
            return;
        }
        if rəqəmdir(c) {
            self.ədəd_oxu(h);
            return;
        }
        if ad_başlanğıcı(c) {
            self.ad_oxu(h);
            return;
        }
        if c == '<' && self.jsx_başlayır(h) {
            self.jsx_oxu(h);
            return;
        }
        if self.op_oxu(h) {
            return;
        }
        self.i += 1;
        let y = self.yer(baş, 1);
        self.x.xəta("ALQ-L002", "Tanınmayan simvol", Some(y),
            &format!("'{}' (U+{:04X})", c, c as u32),
            &["bu simvol Alqor kodunda istifadə oluna bilməz",
              "mətn literalı daxilində istifadə etmək istəyirsinizsə dırnaq içinə alın: \"...\""]);
    }

    fn boşluq_atla(&mut self, interp: bool) -> bool {
        let baş = self.i;
        let sətir_başı = baş == 0 || self.m[baş - 1] == '\n';
        let (mut boşluq, mut tab) = (false, false);
        while self.i < self.n {
            let c = self.m[self.i];
            if c == ' ' {
                boşluq = true;
            } else if c == '\t' {
                tab = true;
            } else if c == '\n' && interp {
            } else {
                break;
            }
            self.i += 1;
        }
        if sətir_başı && boşluq && tab && !self.tab_verildi {
            self.tab_verildi = true;
            let y = self.yer(baş, self.i - baş);
            self.x.xəbərdarlıq("ALQ-L012", "Girintidə boşluq və tab qarışıq işlənib", Some(y),
                "girintidə hər ikisi işlənib", &["Alqor standartı: 4 boşluq, tabulyasiya yox"]);
        }
        self.i > baş
    }

    fn son_əhəmiyyətli(h: &[Token]) -> Option<&Token> {
        h.iter().rev().find(|t| t.növ != Növ::Sənəd && t.növ != Növ::Direktiv)
    }

    fn sətir_sonu(&mut self, h: &mut Vec<Token>) {
        if self.yığın.last() == Some(&Kontekst::Mötərizə) {
            return;
        }
        let son = match Self::son_əhəmiyyətli(h) {
            None => return,
            Some(t) => t,
        };
        if son.növ == Növ::SətirSonu {
            return;
        }
        if son.növ == Növ::Op && !IFADE_BITIREN_OP.contains(&son.s.as_str()) && !Self::ulduz_idxalı(h, son) {
            return;
        }
        if son.növ == Növ::Acar && acar::DAVAM_ACAR.contains(&son.s.as_str()) {
            return;
        }
        if self.növbəti_zəncir() {
            return;
        }
        h.push(Token::yeni(Növ::SətirSonu, "", self.yer(self.i, 0)));
    }

    fn ulduz_idxalı(h: &[Token], son: &Token) -> bool {
        if son.s != "*" {
            return false;
        }
        let a: Vec<&Token> = h[h.len().saturating_sub(3)..].iter().filter(|t| t.növ != Növ::SətirSonu).collect();
        a.len() >= 2 && a[a.len() - 2].növ == Növ::Op && a[a.len() - 2].s == "."
    }

    fn növbəti_zəncir(&self) -> bool {
        let mut i = self.i;
        while i < self.n {
            let c = self.m[i];
            if " \t\r\n".contains(c) {
                i += 1;
                continue;
            }
            if self.başlayır(i, "//") {
                match self.m[i..].iter().position(|c| *c == '\n') {
                    None => return false,
                    Some(p) => {
                        i += p + 1;
                        continue;
                    }
                }
            }
            break;
        }
        if self.başlayır(i, "?.") {
            i += 2;
        } else if i < self.n && self.m[i] == '.' && !self.başlayır(i, "..") {
            i += 1;
        } else {
            return false;
        }
        i < self.n && (self.m[i].is_alphabetic() || self.m[i] == '_')
    }

    fn üzv_mövqeyi(h: &[Token]) -> bool {
        Self::son_əhəmiyyətli(h).map(|t| t.opdur(&[".", "?."])).unwrap_or(false)
    }

    fn şərh_oxu(&mut self, h: &mut Vec<Token>) {
        let baş = self.i;
        if self.gör(1) == Some('*') {
            self.i += 2;
            let mut d = 1;
            while self.i < self.n && d > 0 {
                if self.başlayır(self.i, "/*") {
                    d += 1;
                    self.i += 2;
                } else if self.başlayır(self.i, "*/") {
                    d -= 1;
                    self.i += 2;
                } else {
                    self.i += 1;
                }
            }
            if d > 0 {
                let y = self.yer(baş, 2);
                self.x.xəta("ALQ-L004", "Bağlanmamış şərh bloku", Some(y),
                    "burada açılıb, heç yerdə bağlanmayıb", &["`*/` əlavə edin"]);
            }
            return;
        }
        self.i += 2;
        let modul_sənədi = self.gör(0) == Some('!');
        let sənəd = self.gör(0) == Some('/');
        if modul_sənədi || sənəd {
            self.i += 1;
        }
        let son = self.m[self.i..].iter().position(|c| *c == '\n').map(|p| p + self.i).unwrap_or(self.n);
        let mut məzmun = self.parça(self.i, son);
        self.i = son;
        if sənəd || modul_sənədi {
            if məzmun.starts_with(' ') {
                məzmun.remove(0);
            }
            let mut t = Token::yeni(Növ::Sənəd, məzmun.trim_end(), self.yer(baş, self.i - baş));
            t.xam = self.parça(baş, self.i);
            h.push(t);
            return;
        }
        let s = məzmun.trim();
        if let Some(əmr) = s.strip_prefix("alqor:") {
            let əmr = əmr.trim().to_string();
            let sadə = crate::elifba::latınla(&əmr);
            if sadə.starts_with("ascii-xeberdarliq") && sadə.contains("sondur") {
                self.ascii_xəbərdarlığı = false;
            } else if sadə.starts_with("xeta-sondur") {
                if let Some(k) = əmr.split_whitespace().last() {
                    self.x.söndür(k);
                }
            }
            h.push(Token::yeni(Növ::Direktiv, &əmr, self.yer(baş, self.i - baş)));
        }
    }

    fn ad_oxu(&mut self, h: &mut Vec<Token>) {
        let baş = self.i;
        while self.i < self.n && ad_davamı(self.m[self.i]) {
            self.i += 1;
        }
        let söz = self.parça(baş, self.i);
        let uz = self.i - baş;
        let (kanonik, ascii_idi) = match acar::kanonikləşdir(&söz) {
            None => {
                if acar::EHTIYAT.contains(&söz.as_str()) && !Self::üzv_mövqeyi(h) {
                    let y = self.yer(baş, uz);
                    self.x.xəbərdarlıq("ALQ-L016", "Ehtiyat söz identifikator kimi işlənib", Some(y),
                        &format!("'{}' gələcək versiyada açar söz ola bilər", söz),
                        &["başqa ad seçmək tövsiyə olunur"]);
                }
                let mut t = Token::yeni(Növ::Ad, &söz, self.yer(baş, uz));
                t.xam = söz;
                h.push(t);
                return;
            }
            Some(k) => k,
        };
        if let Some((kanon, son, ascii_var)) = self.çox_sözlü(kanonik) {
            self.i = son;
            if ascii_var && self.ascii_xəbərdarlığı {
                self.ascii_xəbərdarlıq(baş, self.i - baş, &kanon);
            }
            self.yığını_yenilə(&kanon);
            let mut t = Token::yeni(Növ::Acar, &kanon, self.yer(baş, self.i - baş));
            t.xam = self.parça(baş, self.i);
            h.push(t);
            return;
        }
        let kanonik = acar::tamamla(kanonik);
        if ascii_idi && self.ascii_xəbərdarlığı {
            self.ascii_xəbərdarlıq(baş, uz, &kanonik);
        }
        self.yığını_yenilə(&kanonik);
        let mut t = Token::yeni(Növ::Acar, &kanonik, self.yer(baş, uz));
        t.xam = söz;
        h.push(t);
    }

    fn çox_sözlü(&self, ilk: &str) -> Option<(String, usize, bool)> {
        let mut naxışlar: Vec<&&[&str]> = acar::COX_SOZLU.iter().filter(|p| p[0] == ilk).collect();
        naxışlar.sort_by_key(|p| std::cmp::Reverse(p.len()));
        for naxış in naxışlar {
            let mut mövqe = self.i;
            let mut ascii_var = false;
            let mut uğur = true;
            for gözlənilən in &naxış[1..] {
                let mut j = mövqe;
                while j < self.n && (self.m[j] == ' ' || self.m[j] == '\t') {
                    j += 1;
                }
                let mut k = j;
                while k < self.n && ad_davamı(self.m[k]) {
                    k += 1;
                }
                if k == j {
                    uğur = false;
                    break;
                }
                let söz = self.parça(j, k);
                match acar::kanonikləşdir(&söz) {
                    Some((kanon, a)) if kanon == *gözlənilən => {
                        ascii_var |= a;
                        mövqe = k;
                    }
                    _ => {
                        uğur = false;
                        break;
                    }
                }
            }
            if uğur {
                return Some((acar::tamamla(&naxış.join(" ")), mövqe, ascii_var));
            }
        }
        None
    }

    fn yığını_yenilə(&mut self, a: &str) {
        if acar::BLOK_ACANLAR.contains(&a) {
            self.yığın.push(Kontekst::Blok);
        } else if a == "son" && self.yığın.last() == Some(&Kontekst::Blok) {
            self.yığın.pop();
        }
    }

    fn ascii_xəbərdarlıq(&mut self, baş: usize, uz: usize, kanonik: &str) {
        let yazılan = self.parça(baş, baş + uz);
        let y = self.yer(baş, uz);
        self.x.xəbərdarlıq("ALQ-L020", "Açar söz ASCII formada yazılıb", Some(y),
            &format!("'{}' → '{}'", yazılan, kanonik),
            &[&format!("kanonik forma: {}", kanonik), "hamısını birdən düzəltmək: alqorfmt --ascii-düzəlt ."]);
    }

    // ── Ədədlər ───────────────────────────────────────────────────────

    fn ədəd_oxu(&mut self, h: &mut Vec<Token>) {
        let baş = self.i;
        if self.m[self.i] == '0' && matches!(self.gör(1), Some('x' | 'X' | 'b' | 'B' | 'o' | 'O')) {
            let hərf = self.gör(1).unwrap();
            self.i += 2;
            let (icazəli, əsas): (&str, u32) = match hərf {
                'x' | 'X' => ("0123456789abcdefABCDEF", 16),
                'b' | 'B' => ("01", 2),
                _ => ("01234567", 8),
            };
            let rb = self.i;
            while self.i < self.n && (icazəli.contains(self.m[self.i]) || self.m[self.i] == '_') {
                self.i += 1;
            }
            let rəqəmlər: String = self.parça(rb, self.i).replace('_', "");
            if rəqəmlər.is_empty() {
                let y = self.yer(baş, self.i - baş);
                self.x.xəta("ALQ-L006", "Yanlış ədəd literalı", Some(y),
                    &format!("`0{}` prefiksindən sonra rəqəm yoxdur", hərf), &[]);
                let mut t = Token::yeni(Növ::Tam, "", y);
                t.tam = Some(BigInt::from(0));
                h.push(t);
                return;
            }
            self.ədəddən_sonra(baş);
            let d = BigInt::parse_bytes(rəqəmlər.as_bytes(), əsas).unwrap_or_default();
            self.hədd(&d, baş);
            let mut t = Token::yeni(Növ::Tam, "", self.yer(baş, self.i - baş));
            t.tam = Some(d);
            t.xam = self.parça(baş, self.i);
            h.push(t);
            return;
        }
        self.rəqəmlər_atla();
        let mut onluq = false;
        let kortej_indeksi = baş > 0 && self.m[baş - 1] == '.' && !(baş > 1 && self.m[baş - 2] == '.');
        if kortej_indeksi {
        } else if self.gör(0) == Some('.') && self.gör(1).map(rəqəmdir).unwrap_or(false) {
            onluq = true;
            self.i += 1;
            self.rəqəmlər_atla();
        } else if self.gör(0) == Some('.') && self.gör(1) != Some('.')
            && !self.gör(1).map(hərfdir).unwrap_or(false) && self.gör(1) != Some('_') {
            let y = self.yer(baş, self.i + 1 - baş);
            let q = self.parça(baş, self.i);
            self.x.xəta("ALQ-L006", "Yanlış ədəd literalı", Some(y),
                &format!("`{}.` — nöqtədən sonra rəqəm olmalıdır", q),
                &[&format!("onluq ədəd: `{}.0`", q)]);
            self.i += 1;
            onluq = true;
        }
        if matches!(self.gör(0), Some('e' | 'E')) {
            let mut j = self.i + 1;
            if j < self.n && (self.m[j] == '+' || self.m[j] == '-') {
                j += 1;
            }
            if j < self.n && rəqəmdir(self.m[j]) {
                onluq = true;
                self.i = j;
                self.rəqəmlər_atla();
            }
        }
        let xam = self.parça(baş, self.i);
        self.ədəddən_sonra(baş);
        let təmiz = xam.replace('_', "");
        if onluq {
            let mut t = Token::yeni(Növ::Onluq, "", self.yer(baş, self.i - baş));
            t.onluq = təmiz.trim_end_matches('.').parse::<f64>().unwrap_or(0.0);
            t.xam = xam;
            h.push(t);
        } else {
            let d: BigInt = təmiz.parse().unwrap_or_default();
            self.hədd(&d, baş);
            let mut t = Token::yeni(Növ::Tam, "", self.yer(baş, self.i - baş));
            t.tam = Some(d);
            t.xam = xam;
            h.push(t);
        }
    }

    fn rəqəmlər_atla(&mut self) {
        while self.i < self.n && (rəqəmdir(self.m[self.i]) || self.m[self.i] == '_') {
            self.i += 1;
        }
    }

    fn ədəddən_sonra(&mut self, baş: usize) {
        if self.i < self.n && hərfdir(self.m[self.i]) {
            let pis = self.i;
            while self.i < self.n && ad_davamı(self.m[self.i]) {
                self.i += 1;
            }
            let y = self.yer(baş, self.i - baş);
            let q = self.parça(pis, self.i);
            self.x.xəta("ALQ-L006", "Yanlış ədəd literalı", Some(y), "ədədlə identifikator birləşib",
                &["ədəd ilə ad arasında boşluq və ya operator lazımdır",
                  &format!("'{}' hissəsi gözlənilmirdi", q)]);
        }
    }

    fn hədd(&mut self, d: &BigInt, baş: usize) {
        if *d > BigInt::from(1u64 << 63) {
            let y = self.yer(baş, self.i - baş);
            self.x.xəta("ALQ-L007", "Ədəd diapazondan kənardır", Some(y),
                &format!("{} — 64 bit `tam` tipinə sığmır", d), &["maksimum: 9_223_372_036_854_775_807"]);
        }
    }

    // ── Mətnlər ───────────────────────────────────────────────────────

    fn mətn_oxu(&mut self, h: &mut Vec<Token>, tam_baş: usize, xam: bool, bayt: bool) {
        let sitat = self.m[self.i];
        let üçqat = self.başlayır(self.i, &sitat.to_string().repeat(3));
        let bağ: String = if üçqat { sitat.to_string().repeat(3) } else { sitat.to_string() };
        self.i += bağ.chars().count();
        let mut parçalar: Vec<Parça> = vec![];
        let mut bufer = String::new();
        let mut bitdi = false;
        while self.i < self.n {
            let c = self.m[self.i];
            if self.başlayır(self.i, &bağ) {
                self.i += bağ.chars().count();
                bitdi = true;
                break;
            }
            if c == '\n' && !üçqat {
                break;
            }
            if xam {
                bufer.push(c);
                self.i += 1;
                continue;
            }
            if c == '\\' {
                let q = self.qaçış_oxu();
                bufer.push_str(&q);
                continue;
            }
            if c == '{' && !bayt {
                if !bufer.is_empty() {
                    parçalar.push(Parça::Mətn(std::mem::take(&mut bufer)));
                }
                self.i += 1;
                let p = self.interpolyasiya_oxu();
                parçalar.push(p);
                continue;
            }
            bufer.push(c);
            self.i += 1;
        }
        if !bufer.is_empty() {
            parçalar.push(Parça::Mətn(bufer));
        }
        let yer = self.yer(tam_baş, self.i - tam_baş);
        if !bitdi {
            let y = self.yer(tam_baş, (self.i - tam_baş).min(bağ.chars().count()));
            let son = format!("sonda `{}` əlavə edin", bağ);
            let mut k: Vec<&str> = vec![&son];
            if !üçqat {
                k.push("çoxsətirli mətn üçün `\"\"\"` istifadə edin");
            }
            self.x.xəta("ALQ-L003", "Bağlanmamış mətn literalı", Some(y), "bu mətn bağlanmayıb", &k);
        }
        if üçqat {
            let g = self.girinti_tap(tam_baş);
            parçalar = çoxsətirli_düzəlt(parçalar, &g);
        }
        let mətn: String = parçalar.iter().filter_map(|p| if let Parça::Mətn(s) = p { Some(s.as_str()) } else { None }).collect();
        if bayt {
            let mut t = Token::yeni(Növ::Bayt, "", yer);
            t.bayt = mətn.into_bytes();
            t.xam = self.parça(tam_baş, self.i);
            h.push(t);
            return;
        }
        let mut t = Token::yeni(Növ::Mətn, &mətn, yer);
        t.xam = self.parça(tam_baş, self.i);
        t.parçalar = Some(parçalar);
        h.push(t);
    }

    fn girinti_tap(&self, tam_baş: usize) -> String {
        let bağ = self.i.saturating_sub(3);
        let mut j = bağ;
        let mut tapıldı = None;
        while j > tam_baş {
            j -= 1;
            if self.m[j] == '\n' {
                tapıldı = Some(j);
                break;
            }
        }
        match tapıldı {
            None => String::new(),
            Some(sb) => {
                let p = self.parça(sb + 1, bağ);
                if p.trim().is_empty() { p } else { String::new() }
            }
        }
    }

    fn qaçış_oxu(&mut self) -> String {
        let baş = self.i;
        self.i += 1;
        if self.i >= self.n {
            return String::new();
        }
        let c = self.m[self.i];
        self.i += 1;
        let sadə = match c {
            'n' => Some("\n"), 'r' => Some("\r"), 't' => Some("\t"), '0' => Some("\0"),
            '\\' => Some("\\"), '"' => Some("\""), '\'' => Some("'"), '`' => Some("`"),
            'e' => Some("\x1b"), '{' => Some("{"), '}' => Some("}"), _ => None,
        };
        if let Some(s) = sadə {
            return s.into();
        }
        if c == 'u' {
            if self.gör(0) != Some('{') {
                let y = self.yer(baş, self.i - baş);
                self.x.xəta("ALQ-L005", "Yanlış qaçış ardıcıllığı", Some(y), "`\\u` ardınca `{` gəlməlidir", &["nümunə: \\u{259} → ə"]);
                return String::new();
            }
            self.i += 1;
            let rb = self.i;
            while self.i < self.n && self.m[self.i].is_ascii_hexdigit() {
                self.i += 1;
            }
            let r = self.parça(rb, self.i);
            if self.gör(0) == Some('}') {
                self.i += 1;
            }
            let kod = u32::from_str_radix(&r, 16).ok();
            return match kod.and_then(char::from_u32) {
                Some(ch) => ch.to_string(),
                None => {
                    let y = self.yer(baş, self.i - baş);
                    self.x.xəta("ALQ-L008", "Yanlış Unicode kod nöqtəsi", Some(y), "etibarlı Unicode deyil", &[]);
                    String::new()
                }
            };
        }
        if c == 'x' {
            let rb = self.i;
            while self.i < self.n && self.i - rb < 2 && self.m[self.i].is_ascii_hexdigit() {
                self.i += 1;
            }
            let r = self.parça(rb, self.i);
            if r.chars().count() != 2 {
                let y = self.yer(baş, self.i - baş);
                self.x.xəta("ALQ-L005", "Yanlış qaçış ardıcıllığı", Some(y), "`\\x` ardınca iki onaltılıq rəqəm gəlməlidir", &[]);
                return String::new();
            }
            return char::from_u32(u32::from_str_radix(&r, 16).unwrap()).unwrap().to_string();
        }
        let y = self.yer(baş, 2);
        self.x.xəta("ALQ-L005", "Yanlış qaçış ardıcıllığı", Some(y), &format!("`\\{}` tanınmayan qaçışdır", c),
            &["tərs kəsiyin özü üçün: \\\\"]);
        c.to_string()
    }

    fn interpolyasiya_oxu(&mut self) -> Parça {
        let baş = self.i;
        let mut yerli: Vec<Token> = vec![];
        let mut d: i32 = 0;
        while self.i < self.n {
            self.boşluq_atla(true);
            if self.i >= self.n {
                break;
            }
            let c = self.m[self.i];
            if d == 0 && c == '}' {
                self.i += 1;
                return Parça::Kod(yerli, None);
            }
            if d == 0 && c == ':' {
                self.i += 1;
                let fb = self.i;
                while self.i < self.n && self.m[self.i] != '}' && self.m[self.i] != '\n' {
                    self.i += 1;
                }
                let f = self.parça(fb, self.i);
                if self.gör(0) == Some('}') {
                    self.i += 1;
                    return Parça::Kod(yerli, Some(f));
                }
                break;
            }
            if c == '\n' {
                break;
            }
            let əvvəl = yerli.len();
            let köhnə = self.i;
            self.token_oxu(&mut yerli, true);
            if self.i == köhnə {
                self.i += 1;
            }
            for t in &yerli[əvvəl..] {
                if t.növ == Növ::Op {
                    if "([{".contains(t.s.as_str()) && t.s.len() == 1 {
                        d += 1;
                    } else if ")]}".contains(t.s.as_str()) && t.s.len() == 1 {
                        d -= 1;
                    }
                }
            }
        }
        let y = self.yer(baş - 1, 1);
        self.x.xəta("ALQ-L011", "Bağlanmamış interpolyasiya", Some(y), "burada açılıb, `}` ilə bağlanmayıb",
            &["nümunə: \"Salam, {ad}!\"", "fiqurlu mötərizənin özü üçün: \\{ və \\}"]);
        Parça::Kod(yerli, None)
    }

    fn simvol_oxu(&mut self, h: &mut Vec<Token>) {
        let baş = self.i;
        self.i += 1;
        if self.i >= self.n {
            self.simvol_xətası(baş);
            return;
        }
        let d = if self.m[self.i] == '\\' {
            self.qaçış_oxu()
        } else {
            let mut p = self.m[self.i].to_string();
            self.i += 1;
            while self.i < self.n && birləşən(self.m[self.i]) {
                p.push(self.m[self.i]);
                self.i += 1;
            }
            p
        };
        if self.gör(0) != Some('`') {
            self.simvol_xətası(baş);
            return;
        }
        self.i += 1;
        let mut t = Token::yeni(Növ::Simvol, &d, self.yer(baş, self.i - baş));
        t.xam = self.parça(baş, self.i);
        h.push(t);
    }

    fn simvol_xətası(&mut self, baş: usize) {
        let y = self.yer(baş, (self.i - baş).max(1));
        self.x.xəta("ALQ-L017", "Bağlanmamış simvol literalı", Some(y), "simvol literalı ` ilə bağlanmalıdır",
            &["nümunə: `ə`  `\\n`  `A`"]);
    }

    // ── JSX ───────────────────────────────────────────────────────────

    fn jsx_başlayır(&self, h: &[Token]) -> bool {
        let n = self.gör(1);
        if !(n == Some('>') || n == Some('/') || n.map(ad_başlanğıcı).unwrap_or(false)) {
            return false;
        }
        match Self::son_əhəmiyyətli(h) {
            None => true,
            Some(son) => match son.növ {
                Növ::Ad | Növ::Tam | Növ::Onluq | Növ::Mətn | Növ::Simvol | Növ::Bayt | Növ::Jsx => false,
                Növ::Op => !IFADE_BITIREN_OP.contains(&son.s.as_str()),
                Növ::Acar => !IFADE_BITIREN_LIT.contains(&son.s.as_str()),
                _ => true,
            },
        }
    }

    fn jsx_oxu(&mut self, h: &mut Vec<Token>) {
        let baş = self.i;
        match self.jsx_sonu(baş) {
            None => {
                let y = self.yer(baş, 1);
                self.x.xəta("ALQ-P031", "İnterfeys elementi bağlanmayıb", Some(y), "burada açılıb",
                    &["bağlayan teq əlavə edin: </ad>", "öz-bağlanan element: <ad />"]);
                self.i += 1;
                h.push(Token::yeni(Növ::Op, "<", self.yer(baş, 1)));
            }
            Some(son) => {
                self.i = son;
                let mut t = Token::yeni(Növ::Jsx, "", self.yer(baş, son - baş));
                t.jsx = (baş, son);
                t.xam = self.parça(baş, son);
                h.push(t);
            }
        }
    }

    fn jsx_sonu(&self, baş: usize) -> Option<usize> {
        let mut i = baş;
        let mut d: i32 = 0;
        while i < self.n {
            let c = self.m[i];
            if c == '<' {
                let n = self.m.get(i + 1).copied();
                if !(n == Some('/') || n == Some('>') || n.map(ad_başlanğıcı).unwrap_or(false)) {
                    if d == 0 {
                        return None;
                    }
                    i += 1;
                    continue;
                }
                if n == Some('/') {
                    let y = self.m[i..].iter().position(|c| *c == '>')? + i;
                    i = y + 1;
                    d -= 1;
                    if d == 0 {
                        return Some(i);
                    }
                    if d < 0 {
                        return None;
                    }
                    continue;
                }
                let (yi, öz) = self.jsx_teqi(i)?;
                i = yi;
                if !öz {
                    d += 1;
                } else if d == 0 {
                    return Some(i);
                }
                continue;
            }
            if c == '{' && d > 0 {
                i = self.jsx_fiqurlu(i)?;
                continue;
            }
            if d == 0 {
                return None;
            }
            i += 1;
        }
        None
    }

    fn jsx_teqi(&self, mut i: usize) -> Option<(usize, bool)> {
        i += 1;
        if i < self.n && self.m[i] == '>' {
            return Some((i + 1, false));
        }
        while i < self.n {
            let c = self.m[i];
            if c == '"' || c == '\'' {
                i = self.jsx_literal(i);
                continue;
            }
            if c == '{' {
                i = self.jsx_fiqurlu(i)?;
                continue;
            }
            if c == '/' && self.m.get(i + 1) == Some(&'>') {
                return Some((i + 2, true));
            }
            if c == '>' {
                return Some((i + 1, false));
            }
            i += 1;
        }
        None
    }

    fn jsx_fiqurlu(&self, mut i: usize) -> Option<usize> {
        let mut d = 0;
        while i < self.n {
            let c = self.m[i];
            if c == '"' || c == '\'' || c == '`' {
                i = self.jsx_literal(i);
                continue;
            }
            if "([{".contains(c) {
                d += 1;
            } else if ")]}".contains(c) {
                d -= 1;
                if d == 0 {
                    return Some(i + 1);
                }
            }
            i += 1;
        }
        None
    }

    pub fn jsx_literal(&self, mut i: usize) -> usize {
        let sitat = self.m[i];
        let üç: String = sitat.to_string().repeat(3);
        if self.başlayır(i, &üç) {
            let mut j = i + 3;
            while j + 3 <= self.n {
                if self.başlayır(j, &üç) {
                    return j + 3;
                }
                j += 1;
            }
            return self.n;
        }
        i += 1;
        while i < self.n {
            if self.m[i] == '\\' {
                i += 2;
                continue;
            }
            if self.m[i] == sitat {
                return i + 1;
            }
            i += 1;
        }
        i
    }

    fn op_oxu(&mut self, h: &mut Vec<Token>) -> bool {
        let baş = self.i;
        if let Some(op) = op_tap(&self.m, self.i) {
            let uz = op.chars().count();
            self.i += uz;
            if op == "(" || op == "[" || op == "{" {
                self.yığın.push(Kontekst::Mötərizə);
            } else if op == ")" || op == "]" || op == "}" {
                while let Some(k) = self.yığın.pop() {
                    if k == Kontekst::Mötərizə {
                        break;
                    }
                }
            }
            let mut t = Token::yeni(Növ::Op, op, self.yer(baş, uz));
            t.xam = op.to_string();
            h.push(t);
            return true;
        }
        false
    }
}

fn birləşən(c: char) -> bool {
    // Unicode birləşən işarələr (Mn/Mc/Me) — əsas diapazonlar
    matches!(c as u32, 0x0300..=0x036F | 0x1AB0..=0x1AFF | 0x1DC0..=0x1DFF | 0x20D0..=0x20FF | 0xFE20..=0xFE2F)
}

fn çoxsətirli_düzəlt(parçalar: Vec<Parça>, girinti: &str) -> Vec<Parça> {
    let mut n = vec![];
    let mut ilk = true;
    for p in parçalar {
        match p {
            Parça::Kod(..) => {
                n.push(p);
                ilk = false;
            }
            Parça::Mətn(mut m) => {
                if ilk && m.starts_with('\n') {
                    m.remove(0);
                }
                if !girinti.is_empty() {
                    let mut s: Vec<String> = m.split('\n').map(|x| x.to_string()).collect();
                    if ilk && s[0].starts_with(girinti) {
                        s[0] = s[0][girinti.len()..].to_string();
                    }
                    for x in s.iter_mut().skip(1) {
                        if x.starts_with(girinti) {
                            *x = x[girinti.len()..].to_string();
                        }
                    }
                    m = s.join("\n");
                }
                n.push(Parça::Mətn(m));
                ilk = false;
            }
        }
    }
    n
}
