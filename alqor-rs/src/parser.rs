//! Parser (parser.py-ın birə-bir köçürməsi): token axını → AAC.
//!
//! Cümlələr üçün rekursiv enmə, ifadələr üçün prioritet dırmaşması.
//! Xətadan sonra bərpa: növbəti cümlə sərhədinə qədər atlanır.

use crate::aac::{
    self as A, Arqument, Bağlama, BağlamaNöv, Cümlə, Hal, LambdaGövdə, LiteralD, Naxış, Parametr, Tip,
    Tutma, İdxalElementi, İfadə, E,
};
use crate::lekser::{Növ, Parça, Token};
use crate::makro as M;
use crate::xeta::{mənbə_id, Mənbə, XətaToplayıcı, Yer};
use std::rc::Rc;

/// Daxili — bərpa mexanizmi üçün (Python: `ParserXətası`).
pub struct PX;
pub type N<T> = Result<T, PX>;

/// op → (prioritet, sağdan_assosiativ). Böyük rəqəm = daha sıx bağlayır.
pub fn prioritet(op: &str) -> Option<(i32, bool)> {
    Some(match op {
        "|>" => (1, false),
        "??" => (2, true),
        "və ya" | "||" => (3, false),
        "və" | "&&" => (4, false),
        "==" | "!=" => (5, false),
        "<" | ">" | "<=" | ">=" | "<=>" | "içindədir" | "tipidir" | "boşdur" | "boş deyil" => (6, false),
        ".." | "..<" => (7, false),
        "|" => (8, false),
        "^" => (9, false),
        "&" => (10, false),
        "<<" | ">>" | ">>>" => (11, false),
        "+" | "-" => (12, false),
        "*" | "/" | "~/" | "%" => (13, false),
        "kimi" | "kimi?" => (14, false),
        "**" => (16, true),
        _ => return None,
    })
}

const TƏK_OPERATORLAR: &[&str] = &["-", "+", "!", "~"];
const MƏNİMSƏTMƏ_OPLARI: &[&str] = &[
    "=", "+=", "-=", "*=", "/=", "~/=", "%=", "**=", "&=", "|=", "^=", "<<=", ">>=", "??=", "?=",
];
const GÖRÜNÜŞLƏR: &[&str] = &["açıq", "gizli", "qorunan"];
const SINIF_UZV_ACARLARI: &[&str] = &[
    "metod", "xassə", "qurucu", "silinsin", "statik", "mücərrəd", "tənbəl", "əvəz et", "açıq", "gizli",
    "qorunan", "sinif", "struktur", "interfeys", "sadalama", "funksiya",
];
const BLOK_SONLARI: &[&str] = &["son", "yoxsa", "yoxsa əgər", "hal", "digər hallarda", "tut", "nəhayət"];
const SON_NÖVLƏRİ: &[&str] = &[
    "əgər", "funksiya", "sinif", "metod", "seç", "təkrarla", "hər", "cəhd", "nə qədər ki", "modul",
    "interfeys", "sadalama", "struktur", "qurucu", "xassə", "həmişə", "blok", "istifadə", "genişlət",
    "komponent", "mağaza", "obyekt", "qarışıq",
];
const OX_FORMALARI: &[&str] = &["→", "->"];
const DÖVR_ACARLARI: &[&str] = &["hər", "nə qədər ki", "təkrarla", "həmişə"];

/// Python `float.__repr__` (xəta mesajları üçün).
pub fn py_onluq(x: f64) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf".into() } else { "-inf".into() };
    }
    if x == 0.0 {
        return if x.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    let e = format!("{:e}", x);
    let (m, üs) = e.split_once('e').unwrap();
    let üs: i32 = üs.parse().unwrap();
    let (işarə, m) = match m.strip_prefix('-') {
        Some(r) => ("-", r),
        None => ("", m),
    };
    let rəqəmlər: String = m.chars().filter(|c| *c != '.').collect();
    if (-4..16).contains(&üs) {
        let n = rəqəmlər.len() as i32;
        let s = if üs < 0 {
            format!("0.{}{}", "0".repeat((-üs - 1) as usize), rəqəmlər)
        } else if üs + 1 >= n {
            format!("{}{}.0", rəqəmlər, "0".repeat((üs + 1 - n) as usize))
        } else {
            let (a, b) = rəqəmlər.split_at((üs + 1) as usize);
            format!("{}.{}", a, b)
        };
        format!("{}{}", işarə, s)
    } else {
        let mant = if rəqəmlər.len() > 1 { format!("{}.{}", &rəqəmlər[..1], &rəqəmlər[1..]) } else { rəqəmlər };
        format!("{}{}e{}{:02}", işarə, mant, if üs < 0 { '-' } else { '+' }, üs.abs())
    }
}

/// Python `bytes.__repr__`.
pub fn py_bayt(b: &[u8]) -> String {
    let dırnaq = if b.contains(&b'\'') && !b.contains(&b'"') { '"' } else { '\'' };
    let mut s = format!("b{}", dırnaq);
    for &c in b {
        match c {
            b'\\' => s.push_str("\\\\"),
            b'\t' => s.push_str("\\t"),
            b'\n' => s.push_str("\\n"),
            b'\r' => s.push_str("\\r"),
            _ if c as char == dırnaq => {
                s.push('\\');
                s.push(dırnaq)
            }
            0x20..=0x7e => s.push(c as char),
            _ => s.push_str(&format!("\\x{:02x}", c)),
        }
    }
    s.push(dırnaq);
    s
}

/// Python-da `str(tok.dəyər)`.
pub fn dəyər_mətni(t: &Token) -> String {
    match t.növ {
        Növ::SətirSonu | Növ::FaylSonu => "None".into(),
        Növ::Tam => t.tam.as_ref().map(|x| x.to_string()).unwrap_or_default(),
        Növ::Onluq => py_onluq(t.onluq),
        Növ::Bayt => py_bayt(&t.bayt),
        Növ::Jsx => format!("({}, {})", t.jsx.0, t.jsx.1),
        _ => t.s.clone(),
    }
}

/// Modifikatorlar (`açıq statik metod …`).
#[derive(Default)]
struct Mod {
    görünüş: Option<String>,
    statik: bool,
    mücərrəd: bool,
    son: bool,
    tənbəl: bool,
    əvəz: bool,
    asinxron: bool,
    generator: bool,
    sabit: bool,
}

fn gövdə(v: Vec<Cümlə>) -> A::Gövdə {
    Rc::new(v)
}

fn lit(yer: Yer, d: LiteralD) -> E {
    Rc::new(İfadə::Literal(yer, d))
}

pub struct Parser<'a> {
    pub t: Vec<Token>,
    pub s: Rc<Mənbə>,
    pub x: &'a mut XətaToplayıcı,
    pub i: usize,
    pub mid: u32,
    /// Makrolar (§ 5.12) — interpolyasiya alt-parserləri ilə paylaşılır
    pub makro: M::MakroVəziyyəti,
    /// Son şəkilçili diapazon (§ 4.14) — `hər … üçün` onda `içində` istəmir
    şəkilçili: Option<E>,
    /// Müqavilələr (§ 5.13): növbəti cümlə funksiya gövdəsinin əvvəlindədirmi
    müqavilə_icazəsi: bool,
    /// Cari funksiya generatordurmu — `zəmanət` orada olmaz
    müqavilə_generator: bool,
}

/// Şəkilçili diapazon (§ 4.14): `1-dən 10-a qədər` ≡ `1..10`
const ÇIXIŞLIQ_ŞƏKİLÇİLƏRİ: &[&str] = &["dan", "dən", "ndan", "ndən", "den", "nden"];
const YÖNLÜK_ŞƏKİLÇİLƏRİ: &[&str] = &["a", "ə", "ya", "yə", "na", "nə", "e", "ye", "ne"];
/// Şəkilçili cümlə (§ 4.14): `"Vüqar" adlar-a əlavə et` ≡ `adlar.əlavə("Vüqar")` —
/// təsirlik, yönlük, yerlik, çıxışlıq hallar
const DİGƏR_HAL_ŞƏKİLÇİLƏRİ: &[&str] =
    &["ı", "i", "u", "ü", "nı", "ni", "nu", "nü", "yı", "yi", "yu", "yü", "da", "də", "nda", "ndə", "de", "nde"];

fn hal_şəkilçisidir(s: &str) -> bool {
    DİGƏR_HAL_ŞƏKİLÇİLƏRİ.contains(&s) || YÖNLÜK_ŞƏKİLÇİLƏRİ.contains(&s) || ÇIXIŞLIQ_ŞƏKİLÇİLƏRİ.contains(&s)
}

impl<'a> Parser<'a> {
    pub fn yeni(tokenlər: Vec<Token>, s: Rc<Mənbə>, x: &'a mut XətaToplayıcı) -> Parser<'a> {
        let t: Vec<Token> =
            tokenlər.into_iter().filter(|t| !matches!(t.növ, Növ::Direktiv | Növ::Sənəd)).collect();
        let mid = mənbə_id(&s);
        Parser { t, s, x, i: 0, mid, makro: M::MakroVəziyyəti::default(), şəkilçili: None, müqavilə_icazəsi: false, müqavilə_generator: false }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Token axını
    // ═══════════════════════════════════════════════════════════════

    pub fn bax(&self, irəli: isize) -> &Token {
        let n = self.t.len() as isize;
        let mut j = (self.i as isize + irəli).min(n - 1);
        if j < 0 {
            j += n;
        }
        &self.t[j as usize]
    }

    pub fn al(&mut self) -> Token {
        let tok = self.t[self.i].clone();
        if self.i < self.t.len() - 1 {
            self.i += 1;
        }
        tok
    }

    fn sonudur(&self) -> bool {
        self.bax(0).növ == Növ::FaylSonu
    }

    fn acar(&self, h: &[&str]) -> bool {
        self.bax(0).acardır(h)
    }

    fn acar_i(&self, irəli: isize, h: &[&str]) -> bool {
        self.bax(irəli).acardır(h)
    }

    fn op(&self, h: &[&str]) -> bool {
        self.bax(0).opdur(h)
    }

    fn op_i(&self, irəli: isize, h: &[&str]) -> bool {
        self.bax(irəli).opdur(h)
    }

    fn növ(&self, irəli: isize) -> Növ {
        self.bax(irəli).növ
    }

    fn qəbul_acar(&mut self, h: &[&str]) -> Option<Token> {
        if self.acar(h) {
            Some(self.al())
        } else {
            None
        }
    }

    fn qəbul_op(&mut self, h: &[&str]) -> Option<Token> {
        if self.op(h) {
            Some(self.al())
        } else {
            None
        }
    }

    fn tələb_op(&mut self, op: &str, kontekst: &str) -> N<Token> {
        if self.op(&[op]) {
            return Ok(self.al());
        }
        let k = format!("kontekst: {}", kontekst);
        let köməklər: Vec<&str> = if kontekst.is_empty() { vec![] } else { vec![&k] };
        self.xəta("ALQ-P001", &format!("`{}` gözlənilirdi", op), &format!("burada `{}` olmalıdır", op), &köməklər);
        Err(PX)
    }

    fn tələb_acar(&mut self, acar: &str) -> N<Token> {
        if self.acar(&[acar]) {
            return Ok(self.al());
        }
        let mesaj = format!("`{}` gözlənilirdi", acar);
        let kod = match acar {
            "onda" => "ALQ-P004",
            "son" => "ALQ-P002",
            _ => "ALQ-P001",
        };
        let köməklər: &[&str] = match acar {
            "onda" => &["şərtdən sonra `onda` yazılmalıdır: `əgər x > 5 onda`"],
            "son" => &["blok `son` ilə bitməlidir", "girinti bloku bitirmir — Alqor-da `son` lazımdır"],
            _ => &[],
        };
        self.xəta(kod, &mesaj, &format!("`{}` çatışmır", acar), köməklər);
        Err(PX)
    }

    fn tələb_ad(&mut self, nə: &str) -> N<String> {
        let tok = self.bax(0).clone();
        if tok.növ == Növ::Ad {
            return Ok(self.al().s);
        }
        if tok.növ == Növ::Acar {
            self.xəta(
                "ALQ-L010",
                "Açar söz identifikator kimi istifadə edilə bilməz",
                &format!("`{}` açar sözdür", tok.s),
                &[&format!("başqa {} seçin", nə)],
            );
            return Err(PX);
        }
        self.xəta("ALQ-P001", &format!("{} gözlənilirdi", nə), &format!("`{}` gözlənilmirdi", göstər(&tok)), &[]);
        Err(PX)
    }

    // ── Ayırıcılar ────────────────────────────────────────────────

    fn ayırıcı_atla(&mut self) {
        while self.növ(0) == Növ::SətirSonu || self.op(&[";"]) {
            self.al();
        }
    }

    fn cümlə_bitibmi(&self) -> bool {
        matches!(self.növ(0), Növ::SətirSonu | Növ::FaylSonu) || self.op(&[";"]) || self.acar(BLOK_SONLARI)
    }

    fn cümlə_sonu(&mut self) -> N<()> {
        if self.cümlə_bitibmi() {
            self.ayırıcı_atla();
            return Ok(());
        }
        let tok = self.bax(0).clone();
        self.xəta(
            "ALQ-P001",
            "Gözlənilməyən token",
            &format!("`{}` burada gözlənilmirdi", göstər(&tok)),
            &["cümlələr yeni sətirdə və ya `;` ilə ayrılır"],
        );
        Err(PX)
    }

    fn son_tələb(&mut self, növ: Option<&str>) -> N<()> {
        self.ayırıcı_atla();
        self.tələb_acar("son")?;
        if növ.is_some() && self.acar(&[növ.unwrap()]) {
            self.al();
        } else if self.növ(0) == Növ::Acar && SON_NÖVLƏRİ.contains(&self.bax(0).s.as_str()) {
            let yazılan = self.al().s;
            if let Some(n) = növ {
                if yazılan != n {
                    let yer = self.bax(-1).yer;
                    self.x.xəbərdarlıq(
                        "ALQ-P017",
                        "Blok bağlanışı uyğun deyil",
                        Some(yer),
                        &format!("`son {}` yazılıb", yazılan),
                        &[&format!("gözlənilən: `son {}` və ya sadəcə `son`", n)],
                    );
                }
            }
        }
        Ok(())
    }

    // ── Xəta ──────────────────────────────────────────────────────

    pub fn xəta(&mut self, kod: &str, mesaj: &str, qeyd: &str, köməklər: &[&str]) {
        let tok = self.bax(0);
        let mut yer = tok.yer;
        if matches!(tok.növ, Növ::SətirSonu | Növ::FaylSonu) && self.i > 0 {
            let əvvəl = &self.t[self.i - 1];
            yer = Yer { mənbə: self.mid, başlanğıc: əvvəl.yer.son(), uzunluq: 1 };
        }
        self.x.xəta(kod, mesaj, Some(yer), qeyd, köməklər);
    }

    fn yer(&self, b: usize, uz: usize) -> Yer {
        Yer { mənbə: self.mid, başlanğıc: b as u32, uzunluq: uz as u32 }
    }

    fn bərpa(&mut self) {
        let mut dərinlik = 0;
        while !self.sonudur() {
            let tok = self.bax(0);
            if tok.növ == Növ::Op {
                if matches!(tok.s.as_str(), "(" | "[" | "{") {
                    dərinlik += 1;
                } else if matches!(tok.s.as_str(), ")" | "]" | "}") {
                    if dərinlik == 0 {
                        self.al();
                        continue;
                    }
                    dərinlik -= 1;
                }
            }
            if dərinlik == 0 {
                if tok.növ == Növ::SətirSonu {
                    self.ayırıcı_atla();
                    return;
                }
                if tok.acardır(BLOK_SONLARI) {
                    return;
                }
            }
            self.al();
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Giriş nöqtəsi
    // ═══════════════════════════════════════════════════════════════

    pub fn ayır(&mut self) -> A::Proqram {
        let mut gövdə = vec![];
        self.ayırıcı_atla();
        while !self.sonudur() {
            if self.x.dolubmu() {
                break;
            }
            match self.üst_səviyyə() {
                Ok(c) => gövdə.push(c),
                Err(PX) => self.bərpa(),
            }
            self.ayırıcı_atla();
        }
        A::Proqram { gövdə }
    }

    fn üst_səviyyə(&mut self) -> N<Cümlə> {
        if self.acar(&["gətir"]) {
            return self.idxal();
        }
        if self.acar(&["ixrac et"]) {
            return self.ixrac();
        }
        let tok = self.bax(0);
        if tok.növ == Növ::Ad && (tok.s == "başlanğıc" || tok.s == "bitiş") && self.növ(1) == Növ::SətirSonu {
            let başlanğıc = tok.s == "başlanğıc";
            let yer = self.al().yer;
            let g = self.blok(&[]);
            self.son_tələb(None)?;
            return Ok(if başlanğıc { Cümlə::Başlanğıc(yer, gövdə(g)) } else { Cümlə::Bitiş(yer, gövdə(g)) });
        }
        self.cümlə()
    }

    // ═══════════════════════════════════════════════════════════════
    //  Modullar
    // ═══════════════════════════════════════════════════════════════

    fn idxal_elementləri(&mut self, nə: &str) -> N<Vec<İdxalElementi>> {
        let mut elementlər = vec![];
        while !self.op(&["}"]) {
            self.ayırıcı_atla();
            let ad = self.tələb_ad(nə)?;
            let mut ləqəb = None;
            if self.qəbul_acar(&["kimi"]).is_some() {
                ləqəb = Some(self.tələb_ad("ləqəb")?);
            }
            elementlər.push(İdxalElementi { ad, ləqəb });
            self.ayırıcı_atla();
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
            self.ayırıcı_atla();
        }
        Ok(elementlər)
    }

    fn idxal(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let mut mətn_yolu = None;
        let mut yol = vec![];
        // `gətir python:numpy` — Python kitabxanası (§ 8.14); `python`
        // yalnız ardınca `:` gələndə prefiksdir
        let python = self.növ(0) == Növ::Ad && self.bax(0).s == "python" && self.op_i(1, &[":"]);
        if python {
            self.al();
            self.al();
        }
        if !python && self.növ(0) == Növ::Mətn {
            mətn_yolu = Some(self.al().s);
        } else {
            yol.push(self.tələb_ad("modul adı")?);
            while self.op(&["."]) && self.növ(1) == Növ::Ad {
                self.al();
                yol.push(self.al().s);
            }
        }
        let mut elementlər = vec![];
        let mut hamısı = false;
        let mut ləqəb = None;
        if self.op(&["."]) {
            self.al();
            if self.op(&["*"]) {
                self.al();
                hamısı = true;
            } else if self.op(&["{"]) {
                self.al();
                elementlər = self.idxal_elementləri("ixrac adı")?;
                self.tələb_op("}", "seçmə idxal")?;
            } else {
                self.xəta(
                    "ALQ-P001",
                    "`{` və ya `*` gözlənilirdi",
                    "seçmə idxal: `gətir riyaziyyat.{kök, Pİ}`",
                    &["hamısını idxal: `gətir riyaziyyat.*`"],
                );
                return Err(PX);
            }
        }
        if self.qəbul_acar(&["kimi"]).is_some() {
            ləqəb = Some(self.tələb_ad("ləqəb")?);
        }
        self.cümlə_sonu()?;
        if let Some(m) = &mətn_yolu {
            self.makroları_gətir(m);
        }
        Ok(Cümlə::İdxal { yer, yol, mətn_yolu, ləqəb, elementlər, hamısı, python })
    }

    // ═══════════════════════════════════════════════════════════════
    //  Ölçü vahidləri (§ 3.8)
    // ═══════════════════════════════════════════════════════════════

    /// `5 km`, `90 km/saat`, `9.8 m/san^2` — ədəddən sonra eyni sətirdə
    /// vahid adı. Mürəkkəb vahidin hissələri boşluqsuz yazılır.
    fn vahid_quyruğu(&mut self, ədəd: E) -> E {
        use crate::icraci::vahid::vahiddir;
        let t = self.bax(0).clone();
        if t.növ != Növ::Ad || !vahiddir(&t.s) {
            return ədəd;
        }
        let mut mətn = self.al().s;
        let mut son = t.yer.son();
        loop {
            let a = self.bax(0).clone();
            let b = self.bax(1).clone();
            if a.opdur(&["/", "*", "·"]) && a.yer.başlanğıc == son && b.növ == Növ::Ad && b.yer.başlanğıc == a.yer.son() && vahiddir(&b.s) {
                self.al();
                self.al();
                mətn.push_str(if a.s == "/" { "/" } else { "·" });
                mətn.push_str(&b.s);
                son = b.yer.son();
                continue;
            }
            if a.opdur(&["^"]) && a.yer.başlanğıc == son && b.növ == Növ::Tam && b.yer.başlanğıc == a.yer.son() {
                self.al();
                self.al();
                mətn.push('^');
                mətn.push_str(&b.tam.clone().unwrap_or_default().to_string());
                son = b.yer.son();
                continue;
            }
            break;
        }
        let yer = ədəd.yer();
        Rc::new(İfadə::VahidliƏdəd(yer, ədəd, mətn))
    }

    // ═══════════════════════════════════════════════════════════════
    //  Sorğu (§ 4.13)
    // ═══════════════════════════════════════════════════════════════

    fn sorğu(&mut self) -> N<E> {
        let yer = self.al().yer;
        let mut bəndlər = vec![self.sorğu_hər()?];
        let mut seçildi = false;
        loop {
            self.ayırıcı_atla();
            if self.acar(&["son"]) || self.sonudur() {
                break;
            }
            let b = self.sorğu_bəndi()?;
            if seçildi && b.növ != "ilk" && b.növ != "atla" {
                self.x.xəta(
                    "ALQ-P037",
                    "`seç`-dən sonra yalnız `ilk` və `atla` gələ bilər",
                    Some(b.yer),
                    &format!("`{}` `seç`-dən sonradır", b.növ),
                    &["`seç` bəndini sona keçirin"],
                );
            }
            seçildi = seçildi || b.növ == "seç";
            bəndlər.push(b);
            // Tək sətirdə: növbəti bənd ayırıcısız gələ bilər
            if !self.sorğu_bəndi_başlayır() && !self.acar(&["son"]) {
                self.cümlə_sonu()?;
            }
        }
        self.son_tələb(None)?;
        Ok(Rc::new(İfadə::Sorğu(yer, bəndlər)))
    }

    fn sorğu_bənd(yer: Yer, növ: &str, bağlama: Option<Bağlama>, ifadə: Option<E>) -> A::SorğuBəndi {
        A::SorğuBəndi { yer, növ: növ.into(), bağlama, ifadə, açarlar: vec![], fərqli: false }
    }

    fn sorğu_bəndi_başlayır(&self) -> bool {
        let t = self.bax(0);
        t.acardır(&["hər", "dəyişən", "seç"])
            || (t.növ == Növ::Ad && matches!(t.s.as_str(), "harada" | "sırala" | "qrupla" | "ilk" | "atla"))
    }

    fn sorğu_hər(&mut self) -> N<A::SorğuBəndi> {
        let yer = self.tələb_acar("hər")?.yer;
        let bağlama = self.bağlama()?;
        self.tələb_acar("üçün")?;
        let mənbə = self.ifadə(0)?;
        self.tələb_acar("içində")?;
        Ok(Self::sorğu_bənd(yer, "hər", Some(bağlama), Some(mənbə)))
    }

    fn sorğu_bəndi(&mut self) -> N<A::SorğuBəndi> {
        let tok = self.bax(0).clone();
        let yer = tok.yer;
        if tok.acardır(&["hər"]) {
            return self.sorğu_hər();
        }
        if tok.acardır(&["dəyişən"]) {
            self.al();
            let bağlama = self.bağlama()?;
            self.tələb_op("=", "sorğuda `dəyişən`")?;
            let e = self.ifadə(0)?;
            return Ok(Self::sorğu_bənd(yer, "dəyişən", Some(bağlama), Some(e)));
        }
        if tok.acardır(&["seç"]) {
            self.al();
            let mut fərqli = false;
            if self.növ(0) == Növ::Ad
                && self.bax(0).s == "fərqli"
                && !self.op_i(1, &[".", "(", "[", "?."])
                && !matches!(self.növ(1), Növ::SətirSonu | Növ::FaylSonu)
            {
                self.al();
                fərqli = true;
            }
            let e = self.ifadə(0)?;
            let mut b = Self::sorğu_bənd(yer, "seç", None, Some(e));
            b.fərqli = fərqli;
            return Ok(b);
        }
        let söz = if tok.növ == Növ::Ad { tok.s.as_str() } else { "" };
        match söz {
            "harada" | "ilk" | "atla" => {
                self.al();
                let e = self.ifadə(0)?;
                Ok(Self::sorğu_bənd(yer, söz, None, Some(e)))
            }
            "sırala" => {
                self.al();
                let mut açarlar = vec![];
                loop {
                    let e = self.ifadə(0)?;
                    let mut azalan = false;
                    if self.növ(0) == Növ::Ad && (self.bax(0).s == "azalan" || self.bax(0).s == "artan") {
                        azalan = self.al().s == "azalan";
                    }
                    açarlar.push((e, azalan));
                    if self.qəbul_op(&[","]).is_none() {
                        break;
                    }
                }
                let mut b = Self::sorğu_bənd(yer, "sırala", None, None);
                b.açarlar = açarlar;
                Ok(b)
            }
            "qrupla" => {
                self.al();
                let açar = self.ifadə(0)?;
                let t = self.bax(0).clone();
                if !(t.növ == Növ::Ad && t.s == "olaraq") {
                    self.xəta(
                        "ALQ-P037",
                        "`olaraq` gözlənilirdi",
                        &format!("`{}` gözlənilmirdi", göstər(&t)),
                        &["qruplama: `qrupla i.şəhər olaraq (şəhər, adamlar)`"],
                    );
                    return Err(PX);
                }
                self.al();
                let bağlama = self.bağlama()?;
                Ok(Self::sorğu_bənd(yer, "qrupla", Some(bağlama), Some(açar)))
            }
            _ => {
                self.xəta(
                    "ALQ-P037",
                    "Sorğu bəndi gözlənilirdi",
                    &format!("`{}` sorğu bəndi deyil", göstər(&tok)),
                    &["bəndlər: hər, harada, dəyişən, sırala, qrupla, seç, ilk, atla"],
                );
                Err(PX)
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Makrolar (§ 5.12)
    // ═══════════════════════════════════════════════════════════════

    /// `makro ad(…)` — `makro` kontekstli sözdür
    fn makro_elanıdır(&self) -> bool {
        let t = self.bax(0);
        t.növ == Növ::Ad && t.s == "makro" && self.növ(1) == Növ::Ad && self.op_i(2, &["("])
    }

    fn makro_çağırışı(&self) -> Option<M::Makro> {
        let t = self.bax(0);
        if t.növ == Növ::Ad && self.op_i(1, &["!"]) && self.op_i(2, &["("]) {
            return self.makro.makrolar.get(&t.s).cloned();
        }
        None
    }

    fn makro_elanı(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad_yer = self.bax(0).yer;
        let ad = self.tələb_ad("makro adı")?;
        self.tələb_op("(", "makro parametrləri")?;
        let mut parametrlər: Vec<String> = vec![];
        let mut blok: Option<String> = None;
        self.ayırıcı_atla();
        while !self.op(&[")"]) {
            let p_yer = self.bax(0).yer;
            let p = self.tələb_ad("parametr adı")?;
            if let Some(b) = &blok {
                self.x.xəta(
                    "ALQ-P035",
                    "Blok parametri sonuncu olmalıdır",
                    Some(p_yer),
                    &format!("`{}`-dan sonra `{}` gəlib", b, p),
                    &[],
                );
            }
            if self.qəbul_op(&[":"]).is_some() && !self.acar(&["blok"]) {
                // Səhv tip — bildirilir, parametr adi parametr sayılır
                let g = göstər(&self.bax(0).clone());
                self.xəta(
                    "ALQ-P035",
                    "Makro parametrinin tipi yalnız `blok` ola bilər",
                    &format!("`{}` yazılıb", g),
                    &["blok arqumenti: `iş: blok`"],
                );
                self.tip()?;
                parametrlər.push(p);
            } else if self.qəbul_acar(&["blok"]).is_some() {
                blok = Some(p);
            } else if parametrlər.contains(&p) {
                self.x.xəta("ALQ-P035", "Parametr adı təkrarlanır", Some(p_yer), &format!("`{}` artıq var", p), &[]);
            } else {
                parametrlər.push(p);
            }
            self.ayırıcı_atla();
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
            self.ayırıcı_atla();
        }
        self.tələb_op(")", "makro parametrləri")?;
        let (tokenlər, ifadədir);
        if self.qəbul_op(&["="]).is_some() {
            if let Some(b) = &blok {
                self.x.xəta(
                    "ALQ-P034",
                    "İfadə makrosunun blok parametri ola bilməz",
                    Some(ad_yer),
                    &format!("`{}: blok` yalnız cümlə makrosunda", b),
                    &["gövdəni `son` ilə bitən blok kimi yazın"],
                );
            }
            let b = self.i;
            self.ifadə(0)?;
            tokenlər = self.t[b..self.i].to_vec();
            ifadədir = true;
            self.cümlə_sonu()?;
        } else {
            let b = self.i;
            self.blok(&[]);
            tokenlər = self.t[b..self.i].to_vec();
            ifadədir = false;
            self.son_tələb(Some("makro"))?;
        }
        let yerlilər = M::yerli_adlar(&tokenlər);
        self.makro.makrolar.insert(
            ad.clone(),
            M::Makro { ad, parametrlər, blok, ifadədir, tokenlər, yerlilər, yer: ad_yer },
        );
        Ok(Cümlə::Keç(yer))
    }

    /// `(a, f(b, c), [d])` — token səviyyəsində bölünür
    fn makro_arqumentləri(&mut self) -> N<Vec<Vec<Token>>> {
        self.tələb_op("(", "makro arqumentləri")?;
        let mut arqumentlər: Vec<Vec<Token>> = vec![];
        let mut cari: Vec<Token> = vec![];
        let mut dərinlik = 0i32;
        loop {
            let t = self.bax(0).clone();
            if t.növ == Növ::FaylSonu {
                self.tələb_op(")", "makro arqumentləri")?;
            }
            if t.opdur(&["(", "[", "{"]) {
                dərinlik += 1;
            } else if t.opdur(&[")", "]", "}"]) {
                if dərinlik == 0 && t.s == ")" {
                    self.al();
                    break;
                }
                dərinlik -= 1;
            } else if t.opdur(&[","]) && dərinlik == 0 {
                self.al();
                arqumentlər.push(std::mem::take(&mut cari));
                continue;
            }
            if t.növ != Növ::SətirSonu {
                cari.push(t);
            }
            self.al();
        }
        if !cari.is_empty() || !arqumentlər.is_empty() {
            arqumentlər.push(cari);
        }
        if arqumentlər.iter().any(|a| a.is_empty()) {
            self.xəta("ALQ-P005", "İfadə gözlənilirdi", "makro arqumenti boşdur", &[]);
            return Err(PX);
        }
        Ok(arqumentlər)
    }

    /// Çağırışı (`ad!(…)` və blokunu) açılmış tokenlərlə əvəz edir
    fn makro_aç(&mut self, m: &M::Makro, ifadədə: bool) -> N<()> {
        let başla = self.i;
        let yer = self.al().yer;
        self.al();
        let arqumentlər = self.makro_arqumentləri()?;
        let mut blok: Option<Vec<Token>> = None;
        if m.blok.is_some() {
            if ifadədə {
                self.x.xəta(
                    "ALQ-P034",
                    "Cümlə makrosu ifadə kimi işlənə bilməz",
                    Some(yer),
                    &format!("`{}!` blok qəbul edir", m.ad),
                    &["makronu ayrıca sətirdə çağırın"],
                );
                return Err(PX);
            }
            // Blokun sərhədini tapmaq üçün onu təhlil edirik — xətalar
            // açılmış kodda bir dəfə bildirilsin deyə geri qaytarılır
            let b = self.i;
            let anlıq = self.x.anlıq();
            self.blok(&[]);
            self.x.geri_qaytar(anlıq);
            blok = Some(self.t[b..self.i].to_vec());
            self.son_tələb(None)?;
        }
        if !m.ifadədir && ifadədə {
            self.x.xəta(
                "ALQ-P034",
                "Cümlə makrosu ifadə kimi işlənə bilməz",
                Some(yer),
                &format!("`{}!` cümlə makrosudur", m.ad),
                &["makronu ayrıca sətirdə çağırın"],
            );
            return Err(PX);
        }
        self.makro.açılış += 1;
        if self.makro.açılış > M::AÇILIŞ_HƏDDİ {
            self.x.xəta(
                "ALQ-P036",
                "Makro açılışlarının sayı həddi aşdı",
                Some(yer),
                &format!("{} açılış", M::AÇILIŞ_HƏDDİ),
                &["makro özünü sonsuz çağırırmı?"],
            );
            return Err(PX);
        }
        let mut yeni = match M::aç(m, &arqumentlər, blok.as_ref(), yer, self.makro.açılış) {
            Ok(v) => v,
            Err(x) => {
                let k: Vec<&str> = x.köməklər.iter().map(|s| s.as_str()).collect();
                self.x.xəta(x.kod, &x.mesaj, Some(x.yer), &x.qeyd, &k);
                return Err(PX);
            }
        };
        if !ifadədə {
            yeni.push(Token::yeni(Növ::SətirSonu, "", yer));
        }
        self.t.splice(başla..self.i, yeni);
        self.i = başla;
        Ok(())
    }

    /// `gətir "fayl.alq"` — faylın makroları bu faylda da işlənir
    fn makroları_gətir(&mut self, mətn_yolu: &str) {
        use std::path::{Path, PathBuf};
        let baza: PathBuf = match &self.s.yol {
            Some(y) => std::fs::canonicalize(y)
                .ok()
                .and_then(|p| p.parent().map(|q| q.to_path_buf()))
                .unwrap_or_else(|| y.parent().map(|q| q.to_path_buf()).unwrap_or_default()),
            None => std::env::current_dir().unwrap_or_default(),
        };
        let mut p = PathBuf::from(mətn_yolu);
        if !p.is_absolute() {
            p = baza.join(p);
        }
        if !p.exists() {
            for uzantı in [".alq", ".alqor"] {
                let q = PathBuf::from(format!("{}{}", p.display(), uzantı));
                if q.exists() {
                    p = q;
                    break;
                }
            }
        }
        if !Path::new(&p).is_file() {
            return;
        }
        let açar = std::fs::canonicalize(&p).unwrap_or(p.clone()).display().to_string();
        if self.makro.oxunmuş.contains(&açar) {
            return;
        }
        self.makro.oxunmuş.insert(açar);
        let Ok(mətn) = std::fs::read_to_string(&p) else { return };
        if !mətn.contains("makro") {
            return;
        }
        let ad = p.file_name().map(|s| s.to_string_lossy().to_string()).unwrap_or_default();
        let s = Mənbə::yeni(&ad, &mətn, Some(p.clone()));
        let mut x = XətaToplayıcı::yeni();
        let t = crate::lekser::Lekser::yeni(s.clone(), &mut x).leksə();
        let mut alt = Parser::yeni(t, s, &mut x);
        alt.makro.oxunmuş = std::mem::take(&mut self.makro.oxunmuş);
        alt.ayır();
        self.makro.oxunmuş = std::mem::take(&mut alt.makro.oxunmuş);
        for (ad, mk) in std::mem::take(&mut alt.makro.makrolar) {
            self.makro.makrolar.entry(ad).or_insert(mk);
        }
    }

    fn ixrac(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        if self.op(&["{"]) {
            self.al();
            self.idxal_elementləri("ad")?;
            self.tələb_op("}", "")?;
            self.cümlə_sonu()?;
            return Ok(Cümlə::İxracSiyahısı(yer));
        }
        self.qəbul_acar(&["standart"]);
        let c = self.cümlə()?;
        let ixrac_olar = matches!(
            c,
            Cümlə::DəyişənElanı { .. }
                | Cümlə::Funksiya(_)
                | Cümlə::Sinif(_)
                | Cümlə::İnterfeys { .. }
                | Cümlə::Sadalama { .. }
                | Cümlə::Qarışıq { .. }
                | Cümlə::TipAliası { .. }
                | Cümlə::Modul { .. }
        );
        if !ixrac_olar {
            self.xəta("ALQ-P018", "Bu elan ixrac edilə bilməz", "`ixrac et` yalnız elanlardan əvvəl gəlir", &[]);
        }
        Ok(c)
    }

    // ═══════════════════════════════════════════════════════════════
    //  Cümlələr
    // ═══════════════════════════════════════════════════════════════

    fn blok(&mut self, dayan_acarları: &[&str]) -> Vec<Cümlə> {
        let mut gövdə = vec![];
        self.ayırıcı_atla();
        while !self.sonudur() && !self.acar(dayan_acarları) && !self.acar(BLOK_SONLARI) {
            if self.x.dolubmu() {
                break;
            }
            match self.cümlə() {
                Ok(c) => gövdə.push(c),
                Err(PX) => self.bərpa(),
            }
            self.ayırıcı_atla();
        }
        gövdə
    }

    fn annotasiyaları_qoy(c: Cümlə, annot: Vec<A::Annotasiya>) -> Cümlə {
        let adlar: Vec<String> = annot.iter().map(|a| a.ad.clone()).collect();
        match c {
            Cümlə::Funksiya(mut f) => {
                let f_ = Rc::make_mut(&mut f);
                f_.annotasiyalar = adlar;
                f_.bəzəyicilər = annot;
                Cümlə::Funksiya(f)
            }
            Cümlə::Metod(mut f) => {
                let f_ = Rc::make_mut(&mut f);
                f_.annotasiyalar = adlar;
                f_.bəzəyicilər = annot;
                Cümlə::Metod(f)
            }
            Cümlə::Xassə(mut x) => {
                Rc::make_mut(&mut x).annotasiyalar = adlar;
                Cümlə::Xassə(x)
            }
            Cümlə::Sinif(mut s) => {
                let s_ = Rc::make_mut(&mut s);
                s_.annotasiyalar = adlar;
                s_.bəzəyicilər = annot;
                Cümlə::Sinif(s)
            }
            c => c,
        }
    }

    fn cümlə(&mut self) -> N<Cümlə> {
        // Makro: elan və cümlə çağırışı (§ 5.12)
        while let Some(m) = self.makro_çağırışı() {
            if m.ifadədir {
                break;
            }
            self.makro_aç(&m, false)?;
        }
        if self.makro_elanıdır() {
            return self.makro_elanı();
        }
        let müqavilə_icazəsi = std::mem::replace(&mut self.müqavilə_icazəsi, false);
        if self.növ(0) == Növ::Ad && matches!(self.bax(0).s.as_str(), "tələb" | "zəmanət") && self.gözlənti_başlayır() {
            return self.müqavilə(müqavilə_icazəsi);
        }
        // `aktyor Ad` (§ 9.12) — `aktyor` kontekstli sözdür
        if self.növ(0) == Növ::Ad
            && self.bax(0).s == "aktyor"
            && self.növ(1) == Növ::Ad
            && (matches!(self.növ(2), Növ::SətirSonu | Növ::FaylSonu)
                || self.acar_i(2, &["miras", "tətbiq", "ilə"])
                || self.op_i(2, &["["]))
        {
            let m = self.modifikatorlar();
            return self.sinif_elanı(&m, "aktyor");
        }

        let tok = self.bax(0).clone();

        // Etiketli dövr: `xarici: hər ...`
        if tok.növ == Növ::Ad && self.op_i(1, &[":"]) && self.acar_i(2, DÖVR_ACARLARI) {
            let etiket = self.al().s;
            self.al();
            return self.dövr(Some(etiket));
        }

        // Annotasiyalar
        let mut annotasiyalar = vec![];
        while self.op(&["@"]) {
            annotasiyalar.push(self.annotasiya()?);
            self.ayırıcı_atla();
        }
        if !annotasiyalar.is_empty() {
            let c = self.cümlə()?;
            return Ok(Self::annotasiyaları_qoy(c, annotasiyalar));
        }

        if self.elan_başlanğıcıdır() {
            return self.elan();
        }
        if tok.növ == Növ::Ad && tok.s == "sınaq" && self.bax(1).növ == Növ::Mətn {
            return self.sınaq();
        }
        if tok.növ == Növ::Ad && tok.s == "gözlənilir" && self.gözlənti_başlayır() {
            return self.gözlənti();
        }
        if tok.növ != Növ::Acar {
            return self.ifadə_cümləsi();
        }

        match tok.s.as_str() {
            "əgər" => self.şərt(),
            "varsa" => self.varsa(),
            "yoxdursa" => self.yoxdursa(),
            "seç" => self.seç(),
            "hər" | "nə qədər ki" | "təkrarla" | "həmişə" => self.dövr(None),
            "dayan" | "davam et" => {
                let yer = self.al().yer;
                let etiket = if self.növ(0) == Növ::Ad { Some(self.al().s) } else { None };
                self.cümlə_sonu()?;
                Ok(if tok.s == "dayan" { Cümlə::Dayan(yer, etiket) } else { Cümlə::DavamEt(yer, etiket) })
            }
            "qaytar" => {
                let yer = self.al().yer;
                let mut dəyərlər = vec![];
                if !self.cümlə_bitibmi() {
                    dəyərlər.push(self.ifadə(0)?);
                    while self.qəbul_op(&[","]).is_some() {
                        dəyərlər.push(self.ifadə(0)?);
                    }
                }
                self.cümlə_sonu()?;
                Ok(Cümlə::Qaytar(yer, dəyərlər))
            }
            "ver" | "at" => {
                let yer = self.al().yer;
                let d = if self.cümlə_bitibmi() { None } else { Some(self.ifadə(0)?) };
                self.cümlə_sonu()?;
                Ok(if tok.s == "ver" { Cümlə::Ver(yer, d) } else { Cümlə::At(yer, d) })
            }
            "cəhd et" => self.cəhd(),
            "iddia" => {
                let yer = self.al().yer;
                let şərt = self.ifadə(0)?;
                let mesaj = if self.qəbul_op(&[","]).is_some() { Some(self.ifadə(0)?) } else { None };
                self.cümlə_sonu()?;
                Ok(Cümlə::İddia(yer, şərt, mesaj))
            }
            "təmin" => {
                let yer = self.al().yer;
                let şərt = self.ifadə(0)?;
                self.tələb_acar("yoxsa")?;
                let g = self.blok(&[]);
                self.son_tələb(None)?;
                Ok(Cümlə::Təmin(yer, şərt, gövdə(g)))
            }
            "gecikdir" => {
                let yer = self.al().yer;
                let i = self.ifadə(0)?;
                self.cümlə_sonu()?;
                Ok(Cümlə::Gecikdir(yer, i))
            }
            "istifadə" => self.istifadə(),
            "keç" => {
                let yer = self.al().yer;
                self.cümlə_sonu()?;
                Ok(Cümlə::Keç(yer))
            }
            "dayanNöqtəsi" => {
                let yer = self.al().yer;
                self.cümlə_sonu()?;
                Ok(Cümlə::DayanNöqtəsi(yer))
            }
            "global" => {
                let yer = self.al().yer;
                let mut adlar = vec![self.tələb_ad("ad")?];
                while self.qəbul_op(&[","]).is_some() {
                    adlar.push(self.tələb_ad("ad")?);
                }
                self.cümlə_sonu()?;
                Ok(Cümlə::Global(yer, adlar))
            }
            "gətir" => self.idxal(),
            "ixrac et" => self.ixrac(),
            _ => self.ifadə_cümləsi(),
        }
    }

    /// `@ad` və ya `@ad(arqumentlər)`
    fn annotasiya(&mut self) -> N<A::Annotasiya> {
        self.al();
        let ad = dəyər_mətni(self.bax(0));
        self.al();
        let arqumentlər = if self.op(&["("]) { self.arqumentlər()? } else { vec![] };
        Ok(A::Annotasiya { ad, arqumentlər })
    }

    // ── Müqavilələr (§ 5.13) ───────────────────────────────────────

    /// Funksiya gövdəsini oxuyur; əvvəlindəki `tələb`/`zəmanət` cümlələrinə icazə verir.
    fn funksiya_gövdəsi(&mut self, generator: bool) -> Vec<Cümlə> {
        let köhnə = (self.müqavilə_icazəsi, self.müqavilə_generator);
        self.müqavilə_icazəsi = true;
        self.müqavilə_generator = generator;
        let g = self.blok(&[]);
        (self.müqavilə_icazəsi, self.müqavilə_generator) = köhnə;
        g
    }

    /// `tələb şərt[, mesaj]` — ön şərt; `zəmanət şərt[, mesaj]` — son şərt.
    fn müqavilə(&mut self, icazə: bool) -> N<Cümlə> {
        let söz = self.bax(0).s.clone();
        if !icazə {
            self.xəta(
                "ALQ-P041",
                &format!("`{}` yalnız funksiyanın əvvəlində yazıla bilər", söz),
                "müqavilə funksiya və ya metod gövdəsinin ilk cümlələridir",
                &["`tələb` və `zəmanət` cümlələrini gövdənin başına köçürün"],
            );
            return Err(PX);
        }
        if söz == "zəmanət" && self.müqavilə_generator {
            self.xəta(
                "ALQ-P041",
                "`zəmanət` generator funksiyada ola bilməz",
                "generatorun tək bir nəticəsi yoxdur",
                &[],
            );
            return Err(PX);
        }
        let yer = self.al().yer;
        let b = self.bax(0).yer.başlanğıc as usize;
        let şərt = self.ifadə(0)?;
        let son = &self.t[self.i - 1].yer;
        let s = (son.başlanğıc + son.uzunluq) as usize;
        let mətn = if s > b && s <= self.s.mətn.len() { self.s.mətn[b..s].iter().collect() } else { String::new() };
        let mesaj = if self.qəbul_op(&[","]).is_some() { Some(self.ifadə(0)?) } else { None };
        self.cümlə_sonu()?;
        self.müqavilə_icazəsi = true;
        Ok(if söz == "tələb" { Cümlə::Tələb(yer, şərt, mesaj, mətn) } else { Cümlə::Zəmanət(yer, şərt, mesaj, mətn) })
    }

    // ── Sınaq (§ 13.5) ─────────────────────────────────────────────

    /// `sınaq "ad" … son` — `sınaq` kontekstli sözdür.
    fn sınaq(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.bax(0).clone();
        let mətn = if ad.sadə_mətndir() {
            ad.s.clone()
        } else {
            let mut s = String::new();
            for p in ad.parçalar.iter().flatten() {
                match p {
                    Parça::Mətn(m) => s.push_str(m),
                    Parça::Kod(..) => {
                        self.xəta("ALQ-P040", "Sınağın adı sabit mətn olmalıdır", "adda `{…}` interpolyasiyası ola bilməz", &[]);
                        return Err(PX);
                    }
                }
            }
            s
        };
        self.al();
        let g = self.blok(&[]);
        self.son_tələb(None)?;
        Ok(Cümlə::Sınaq(yer, mətn, gövdə(g)))
    }

    /// `gözlənilir` ardınca ifadə gəlirsə cümlədir; `gözlənilir = 1`, `gözlənilir.x` adi addır.
    fn gözlənti_başlayır(&self) -> bool {
        let n = self.bax(1);
        if matches!(n.növ, Növ::SətirSonu | Növ::FaylSonu) {
            return false;
        }
        !(n.opdur(&[".", "?.", "[", ",", ":", ";", "++", "--"])
            || n.opdur(MƏNİMSƏTMƏ_OPLARI)
            || n.acardır(&["içində"])
            || n.acardır(BLOK_SONLARI))
    }

    /// `gözlənilir şərt` və `gözlənilir xəta [Tip]: ifadə`.
    fn gözlənti(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let (mut xəta, mut xəta_tipi) = (false, None);
        let t = self.bax(0);
        if t.növ == Növ::Ad && t.s == "xəta" && (self.op_i(1, &[":"]) || (self.bax(1).növ == Növ::Ad && self.op_i(2, &[":"]))) {
            self.al();
            xəta = true;
            if !self.op(&[":"]) {
                xəta_tipi = Some(self.al().s);
            }
            self.tələb_op(":", "gözlənti")?;
        }
        let b = self.bax(0).yer.başlanğıc as usize;
        let ifadə = self.ifadə(0)?;
        let son = &self.t[self.i - 1].yer;
        let s = (son.başlanğıc + son.uzunluq) as usize;
        let mətn = if s > b && s <= self.s.mətn.len() { self.s.mətn[b..s].iter().collect() } else { String::new() };
        self.cümlə_sonu()?;
        Ok(Cümlə::Gözlənti { yer, ifadə, mətn, xəta, xəta_tipi })
    }

    /// Cümlə `OBYEKT-şəkilçi FEL [et]` ilə bitirsə — (obyektin ilk tokeni, felin indeksi).
    fn şəkilçili_cümlə_quyruğu(&self) -> Option<(usize, usize)> {
        let (mut dərinlik, mut j) = (0i32, self.i);
        loop {
            let t = &self.t[j];
            if t.növ == Növ::FaylSonu {
                break;
            }
            if t.opdur(&["(", "[", "{"]) {
                dərinlik += 1;
            } else if t.opdur(&[")", "]", "}"]) {
                dərinlik -= 1;
            } else if dərinlik <= 0 && (t.növ == Növ::SətirSonu || t.opdur(&[";"]) || t.acardır(BLOK_SONLARI)) {
                break;
            }
            j += 1;
        }
        if dərinlik != 0 || j == 0 {
            return None;
        }
        let mut k = j - 1;
        if k > self.i && self.t[k].acardır(&["et"]) {
            k -= 1;
        }
        let fel = k;
        if k < self.i + 3 || self.t[fel].növ != Növ::Ad {
            return None;
        }
        let (ş, tire, ad) = (&self.t[k - 1], &self.t[k - 2], &self.t[k - 3]);
        let son = |t: &Token| t.yer.başlanğıc + t.yer.uzunluq;
        if !(matches!(ş.növ, Növ::Ad | Növ::Acar)
            && hal_şəkilçisidir(&ş.s)
            && tire.opdur(&["-"])
            && ad.növ == Növ::Ad
            && son(ad) == tire.yer.başlanğıc
            && son(tire) == ş.yer.başlanğıc)
        {
            return None;
        }
        let mut b = k - 3;
        while b >= self.i + 2 && self.t[b - 1].opdur(&["."]) && self.t[b - 2].növ == Növ::Ad {
            b -= 2;
        }
        Some((b, fel))
    }

    /// `[arqumentlər] OBYEKT-şəkilçi FEL [et]` → `OBYEKT.FEL(…)`.
    fn şəkilçili_cümlə(&mut self, b: usize, fel: usize) -> N<Cümlə> {
        let yer = self.bax(0).yer;
        let mut arqumentlər = Vec::new();
        if self.i < b {
            // Arqumentlər obyektə qədər oxunur — obyekt müvəqqəti sətir sonu
            // ilə əvəz olunur ki ifadə ona keçməsin
            let obyekt_tokeni = self.t[b].clone();
            self.t[b] = Token::yeni(Növ::SətirSonu, "\n", obyekt_tokeni.yer);
            let mut oxu = |p: &mut Self| -> N<()> {
                arqumentlər.push(Arqument { dəyər: p.ifadə(0)?, ad: None, yayma: false, adlı_yayma: false });
                while p.qəbul_op(&[","]).is_some() {
                    arqumentlər.push(Arqument { dəyər: p.ifadə(0)?, ad: None, yayma: false, adlı_yayma: false });
                }
                Ok(())
            };
            let r = oxu(self);
            self.t[b] = obyekt_tokeni;
            r?;
            if self.i != b {
                self.xəta(
                    "ALQ-P039",
                    "Şəkilçili cümlə təhlil olunmadı",
                    "obyektdən əvvəl yalnız vergüllə ayrılmış arqumentlər ola bilər",
                    &["məs.: `\"Vüqar\" adlar-a əlavə et`"],
                );
                return Err(PX);
            }
        }
        let mut obyekt: E = Rc::new(İfadə::Ad(self.t[b].yer, self.t[b].s.as_str().into()));
        let mut k = b + 2;
        while k + 2 < fel {
            obyekt = Rc::new(İfadə::Üzv(self.t[k - 1].yer, obyekt, self.t[k].s.as_str().into(), false));
            k += 2;
        }
        let f = self.t[fel].clone();
        let çağırış = Rc::new(İfadə::Çağırış(
            f.yer,
            Rc::new(İfadə::Üzv(f.yer, obyekt, f.s.as_str().into(), false)),
            arqumentlər,
        ));
        while self.i <= fel {
            self.al();
        }
        self.qəbul_acar(&["et"]);
        self.cümlə_sonu()?;
        Ok(Cümlə::İfadə(yer, çağırış))
    }

    fn ifadə_cümləsi(&mut self) -> N<Cümlə> {
        let yer = self.bax(0).yer;
        if let Some((b, fel)) = self.şəkilçili_cümlə_quyruğu() {
            return self.şəkilçili_cümlə(b, fel);
        }
        let ifadə = self.ifadə(0)?;

        if self.acar(&["içində"]) && self.acar_i(1, &["hər"]) {
            return self.içində_hər(yer, ifadə);
        }
        if self.op(&["++", "--"]) {
            let op = self.al().s;
            self.cümlə_sonu()?;
            return Ok(Cümlə::Artırma(yer, ifadə, op));
        }
        if self.op(MƏNİMSƏTMƏ_OPLARI) || self.op(&[","]) {
            let mut hədəflər = vec![ifadə.clone()];
            while self.qəbul_op(&[","]).is_some() {
                hədəflər.push(self.ifadə(0)?);
            }
            if !self.op(MƏNİMSƏTMƏ_OPLARI) {
                if hədəflər.len() > 1 {
                    self.xəta(
                        "ALQ-P001",
                        "Mənimsətmə gözlənilirdi",
                        "vergüllə ayrılmış hədəflərdən sonra `=` olmalıdır",
                        &[],
                    );
                    return Err(PX);
                }
                self.cümlə_sonu()?;
                return Ok(Cümlə::İfadə(yer, ifadə));
            }
            let op = self.al().s;
            let mut dəyərlər = vec![self.ifadə(0)?];
            while self.qəbul_op(&[","]).is_some() {
                dəyərlər.push(self.ifadə(0)?);
            }
            self.cümlə_sonu()?;
            return Ok(Cümlə::İfadə(yer, Rc::new(İfadə::Mənimsətmə(yer, hədəflər, op, dəyərlər))));
        }
        self.cümlə_sonu()?;
        Ok(Cümlə::İfadə(yer, ifadə))
    }

    // ── Şərt ──────────────────────────────────────────────────────

    fn şərt(&mut self) -> N<Cümlə> {
        let yer = self.bax(0).yer;
        let mut budaqlar = vec![];
        self.al();
        let ş = self.ifadə(0)?;
        self.tələb_acar("onda")?;
        let g = self.blok(&[]);
        budaqlar.push((ş, gövdə(g)));
        let mut yoxsa = None;
        loop {
            if self.acar(&["yoxsa əgər"]) {
                self.al();
                let ş = self.ifadə(0)?;
                self.tələb_acar("onda")?;
                let g = self.blok(&[]);
                budaqlar.push((ş, gövdə(g)));
                continue;
            }
            if self.acar(&["yoxsa"]) {
                self.al();
                if self.acar(&["əgər"]) {
                    self.al();
                    let ş = self.ifadə(0)?;
                    self.tələb_acar("onda")?;
                    let g = self.blok(&[]);
                    budaqlar.push((ş, gövdə(g)));
                    continue;
                }
                yoxsa = Some(gövdə(self.blok(&[])));
            }
            break;
        }
        self.son_tələb(Some("əgər"))?;
        Ok(Cümlə::Şərt { yer, budaqlar, yoxsa })
    }

    fn varsa_bağlamaları(&mut self) -> N<Vec<(Option<Bağlama>, E)>> {
        let mut b = vec![];
        loop {
            if self.növ(0) == Növ::Ad && self.op_i(1, &["="]) {
                let ad_tok = self.al();
                self.al();
                let bağ = Bağlama { yer: ad_tok.yer, növ: BağlamaNöv::Ad(ad_tok.s), tip: None };
                b.push((Some(bağ), self.ifadə(0)?));
            } else {
                b.push((None, self.ifadə(0)?));
            }
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
        }
        Ok(b)
    }

    fn varsa(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let bağlamalar = self.varsa_bağlamaları()?;
        self.tələb_acar("onda")?;
        let g = gövdə(self.blok(&[]));
        let mut yoxsa = None;
        if self.qəbul_acar(&["yoxsa"]).is_some() {
            yoxsa = Some(gövdə(self.blok(&[])));
        }
        self.son_tələb(None)?;
        Ok(Cümlə::Varsa { yer, bağlamalar, gövdə: g, yoxsa })
    }

    fn yoxdursa(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let bağlamalar = self.varsa_bağlamaları()?;
        self.tələb_acar("onda")?;
        let g = gövdə(self.blok(&[]));
        self.son_tələb(None)?;
        Ok(Cümlə::Yoxdursa { yer, bağlamalar, gövdə: g })
    }

    // ── Seç ───────────────────────────────────────────────────────

    fn seç(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let mut tipə_görə = false;
        if self.növ(0) == Növ::Ad && self.bax(0).s == "tipi" {
            self.al();
            tipə_görə = true;
        }
        let mut ifadə = None;
        if !(self.növ(0) == Növ::SətirSonu || self.acar(&["hal"])) {
            ifadə = Some(self.ifadə(0)?);
        }
        self.ayırıcı_atla();
        let mut hallar = vec![];
        let mut digər = None;
        loop {
            self.ayırıcı_atla();
            if self.acar(&["hal"]) {
                hallar.push(self.hal(tipə_görə, ifadə.is_none())?);
                continue;
            }
            if self.acar(&["digər hallarda"]) {
                self.al();
                if self.op(OX_FORMALARI) {
                    self.al();
                    let c = self.cümlə()?;
                    digər = Some(gövdə(vec![c]));
                } else {
                    digər = Some(gövdə(self.blok(&["hal", "digər hallarda"])));
                }
                continue;
            }
            break;
        }
        self.son_tələb(Some("seç"))?;
        if hallar.is_empty() && digər.is_none() {
            self.x.xəbərdarlıq("ALQ-P019", "`seç` boşdur", Some(yer), "heç bir `hal` yoxdur", &[]);
        }
        Ok(Cümlə::Seç { yer, ifadə, hallar, digər })
    }

    fn hal(&mut self, tipə_görə: bool, şərtli: bool) -> N<Hal> {
        self.al();
        let şərt_oxu = şərtli && !tipə_görə;
        let mut naxışlar = vec![if şərt_oxu { self.şərt_naxışı()? } else { self.naxış(tipə_görə)? }];
        while self.qəbul_op(&[","]).is_some() {
            naxışlar.push(if şərt_oxu { self.şərt_naxışı()? } else { self.naxış(tipə_görə)? });
        }
        let mut mühafizə = None;
        if self.qəbul_acar(&["əgər"]).is_some() {
            mühafizə = Some(self.ifadə(0)?);
        }
        let mut g = if self.op(OX_FORMALARI) {
            self.al();
            vec![self.cümlə()?]
        } else {
            self.blok(&["hal", "digər hallarda"])
        };
        let mut keç = false;
        if matches!(g.last(), Some(Cümlə::Keç(_))) {
            keç = true;
            g.pop();
        }
        Ok(Hal { naxışlar, gövdə: gövdə(g), mühafizə, keç })
    }

    fn şərt_naxışı(&mut self) -> N<Naxış> {
        let tok = self.bax(0);
        if tok.opdur(&["_"]) || (tok.növ == Növ::Ad && tok.s == "_") {
            self.al();
            return Ok(Naxış::Atma);
        }
        Ok(Naxış::Şərt(self.ifadə(0)?))
    }

    fn naxış_siyahısı(&mut self, bağlayan: &str) -> N<Vec<Naxış>> {
        let mut alt = vec![];
        while !self.op(&[bağlayan]) {
            alt.push(self.naxış(false)?);
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
        }
        Ok(alt)
    }

    fn naxış(&mut self, tipə_görə: bool) -> N<Naxış> {
        let tok = self.bax(0).clone();
        let yer = tok.yer;

        if tok.opdur(&["_"]) {
            self.al();
            return Ok(Naxış::Atma);
        }
        if tipə_görə {
            return Ok(Naxış::Tip(self.tip()?));
        }
        if tok.literaldır() || tok.acardır(&["doğru", "yanlış", "boş"]) {
            let ilk = self.əsas_ifadə()?;
            if self.op(&["..", "..<"]) {
                let xaric = self.al().s == "..<";
                let son = self.əsas_ifadə()?;
                return Ok(Naxış::Diapazon(ilk, son, xaric));
            }
            return Ok(Naxış::Literal(ilk));
        }
        if tok.opdur(&["-"]) && matches!(self.növ(1), Növ::Tam | Növ::Onluq) {
            return Ok(Naxış::Literal(self.tək_operand()?));
        }
        if tok.opdur(&["("]) {
            self.al();
            let alt = self.naxış_siyahısı(")")?;
            self.tələb_op(")", "kortej naxışı")?;
            return Ok(Naxış::Kortej(alt));
        }
        if tok.opdur(&["["]) {
            self.al();
            let mut alt = vec![];
            let mut qalan = None;
            while !self.op(&["]"]) {
                if self.op(&["..."]) {
                    self.al();
                    qalan = Some(self.tələb_ad("qalan adı")?);
                    break;
                }
                alt.push(self.naxış(false)?);
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
            }
            self.tələb_op("]", "siyahı naxışı")?;
            return Ok(Naxış::Siyahı(alt, qalan));
        }
        if tok.növ == Növ::Ad || (tok.növ == Növ::Acar && crate::acar::TIP_ADLARI.contains(&tok.s.as_str())) {
            let mut yol = vec![self.al().s];
            while self.op(&["."]) && self.növ(1) == Növ::Ad {
                self.al();
                yol.push(self.al().s);
            }
            let tip_adı = |yol: Vec<String>| Tip::Ad { yer, yol, arqumentlər: vec![], ixtiyari: false };
            if self.op(&["("]) {
                self.al();
                let alt = self.naxış_siyahısı(")")?;
                self.tələb_op(")", "")?;
                return Ok(Naxış::Obyekt(Some(tip_adı(yol)), alt, vec![]));
            }
            if self.op(&["{"]) {
                self.al();
                let mut sahələr = vec![];
                while !self.op(&["}"]) {
                    self.ayırıcı_atla();
                    let ad = self.tələb_ad("sahə adı")?;
                    let mut alt_naxış = None;
                    if self.qəbul_op(&[":"]).is_some() {
                        alt_naxış = Some(self.naxış(false)?);
                    }
                    sahələr.push((ad, alt_naxış));
                    self.ayırıcı_atla();
                    if self.qəbul_op(&[","]).is_none() {
                        break;
                    }
                    self.ayırıcı_atla();
                }
                self.tələb_op("}", "")?;
                return Ok(Naxış::Obyekt(Some(tip_adı(yol)), vec![], sahələr));
            }
            if yol.len() > 1 || tok.növ == Növ::Acar {
                return Ok(Naxış::Tip(tip_adı(yol)));
            }
            return Ok(Naxış::Ad(yol.pop().unwrap().into()));
        }
        self.xəta(
            "ALQ-P001",
            "Naxış gözlənilirdi",
            &format!("`{}` naxış ola bilməz", göstər(&tok)),
            &["naxışlar: literal, `_`, ad, `(a, b)`, `[ilk, ...qalan]`, `Tip{sahə}`, diapazon"],
        );
        Err(PX)
    }

    // ── Dövrlər ───────────────────────────────────────────────────

    fn dövr(&mut self, etiket: Option<String>) -> N<Cümlə> {
        let acar = self.bax(0).s.clone();
        if acar == "nə qədər ki" {
            let yer = self.al().yer;
            let şərt = self.ifadə(0)?;
            let g = self.blok(&[]);
            self.son_tələb(Some("nə qədər ki"))?;
            return Ok(Cümlə::NəQədərKi { yer, şərt, gövdə: gövdə(g), etiket });
        }
        if acar == "həmişə" {
            let yer = self.al().yer;
            let g = self.blok(&[]);
            self.son_tələb(Some("həmişə"))?;
            return Ok(Cümlə::Həmişə { yer, gövdə: gövdə(g), etiket });
        }
        if acar == "təkrarla" {
            let yer = self.al().yer;
            if self.növ(0) == Növ::SətirSonu {
                let g = self.blok(&["nə qədər ki"]);
                self.ayırıcı_atla();
                if self.qəbul_acar(&["nə qədər ki"]).is_some() {
                    let şərt = self.ifadə(0)?;
                    self.cümlə_sonu()?;
                    return Ok(Cümlə::TəkrarlaNəQədər { yer, gövdə: gövdə(g), şərt, etiket });
                }
                self.son_tələb(Some("təkrarla"))?;
                return Ok(Cümlə::Təkrarla {
                    yer,
                    say: lit(yer, LiteralD::Tam(1.into())),
                    gövdə: gövdə(g),
                    sayğac: None,
                    etiket,
                });
            }
            let mut sayğac = None;
            if self.növ(0) == Növ::Ad && self.op_i(1, &[","]) {
                sayğac = Some(self.al().s);
                self.al();
            }
            let say = self.ifadə(0)?;
            self.tələb_acar("dəfə")?;
            let g = self.blok(&[]);
            self.son_tələb(Some("təkrarla"))?;
            return Ok(Cümlə::Təkrarla { yer, say, gövdə: gövdə(g), sayğac, etiket });
        }

        // `hər`
        let yer = self.al().yer;
        let mut bağlamalar = vec![self.bağlama()?];
        while self.qəbul_op(&[","]).is_some() {
            bağlamalar.push(self.bağlama()?);
        }
        self.tələb_acar("üçün")?;
        let mənbə = self.ifadə(0)?;
        let mut addım = None;
        if self.qəbul_acar(&["addım"]).is_some() {
            addım = Some(self.ifadə(0)?);
        }
        // `hər i üçün 1-dən 10-a qədər` — `içində` yazılmaya bilər
        let şəkilçili = self.şəkilçili.as_ref().is_some_and(|d| Rc::ptr_eq(d, &mənbə));
        if !şəkilçili || self.acar(&["içində"]) {
            self.tələb_acar("içində")?;
        }
        let asinxron = self.qəbul_acar(&["gözlə"]).is_some();
        let mut şərt = None;
        if self.qəbul_acar(&["əgər"]).is_some() {
            şərt = Some(self.ifadə(0)?);
        }
        let g = self.blok(&["yoxsa"]);
        let mut yoxsa = None;
        if self.qəbul_acar(&["yoxsa"]).is_some() {
            yoxsa = Some(gövdə(self.blok(&[])));
        }
        self.son_tələb(Some("hər"))?;
        Ok(Cümlə::Hər { yer, bağlamalar, mənbə, gövdə: gövdə(g), addım, şərt, yoxsa, asinxron, etiket })
    }

    fn içində_hər(&mut self, yer: Yer, mənbə: E) -> N<Cümlə> {
        self.tələb_acar("içində")?;
        self.al();
        let mut bağlamalar = vec![self.bağlama()?];
        while self.qəbul_op(&[","]).is_some() {
            bağlamalar.push(self.bağlama()?);
        }
        let üçün_sətir = self.bax(0).yer.sətir();
        self.tələb_acar("üçün")?;
        let mut şərt = None;
        if self.acar(&["əgər"]) && self.bax(0).yer.sətir() == üçün_sətir {
            self.al();
            şərt = Some(self.ifadə(0)?);
        }
        let g = self.blok(&["yoxsa"]);
        let mut yoxsa = None;
        if self.qəbul_acar(&["yoxsa"]).is_some() {
            yoxsa = Some(gövdə(self.blok(&[])));
        }
        self.son_tələb(Some("hər"))?;
        Ok(Cümlə::Hər {
            yer,
            bağlamalar,
            mənbə,
            gövdə: gövdə(g),
            addım: None,
            şərt,
            yoxsa,
            asinxron: false,
            etiket: None,
        })
    }

    // ── Cəhd / istifadə ───────────────────────────────────────────

    fn cəhd(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let g = self.blok(&["tut", "nəhayət"]);
        let mut tutmalar = vec![];
        while self.acar(&["tut"]) {
            self.al();
            let mut ad = None;
            let mut tiplər = vec![];
            if self.op(&["("]) {
                self.al();
                ad = Some(self.tələb_ad("xəta dəyişəni")?);
                if self.qəbul_op(&[":"]).is_some() {
                    tiplər.push(self.tip()?);
                    while self.qəbul_op(&["|"]).is_some() {
                        tiplər.push(self.tip()?);
                    }
                }
                self.tələb_op(")", "`tut` bəndi")?;
            } else if self.növ(0) == Növ::Ad
                && (matches!(self.növ(1), Növ::SətirSonu | Növ::FaylSonu) || self.acar_i(1, &["əgər"]))
            {
                ad = Some(self.al().s);
            }
            let mut mühafizə = None;
            if self.qəbul_acar(&["əgər"]).is_some() {
                mühafizə = Some(self.ifadə(0)?);
            }
            let t_gövdə = self.blok(&["tut", "nəhayət"]);
            tutmalar.push(Tutma { gövdə: gövdə(t_gövdə), ad, tiplər, mühafizə });
        }
        let mut nəhayət = None;
        if self.qəbul_acar(&["nəhayət"]).is_some() {
            nəhayət = Some(gövdə(self.blok(&[])));
        }
        self.son_tələb(Some("cəhd"))?;
        if tutmalar.is_empty() && nəhayət.is_none() {
            self.x.xəbərdarlıq(
                "ALQ-P020",
                "`cəhd et` bloku xətanı tutmur",
                Some(yer),
                "`tut` və ya `nəhayət` yoxdur",
                &["ən azı bir `tut` bəndi əlavə edin"],
            );
        }
        Ok(Cümlə::Cəhd { yer, gövdə: gövdə(g), tutmalar, nəhayət })
    }

    fn istifadə(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let mut bağlamalar = vec![];
        loop {
            let ad = self.tələb_ad("resurs adı")?;
            self.tələb_op("=", "`istifadə` bloku")?;
            bağlamalar.push((ad, self.ifadə(0)?));
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
        }
        let g = self.blok(&[]);
        self.son_tələb(Some("istifadə"))?;
        Ok(Cümlə::İstifadə(yer, bağlamalar, gövdə(g)))
    }

    // ═══════════════════════════════════════════════════════════════
    //  Elanlar
    // ═══════════════════════════════════════════════════════════════

    fn elan_başlanğıcıdır(&self) -> bool {
        let tok = self.bax(0);
        if tok.növ != Növ::Acar {
            return false;
        }
        let a = tok.s.as_str();
        if matches!(
            a,
            "dəyişən" | "sabit" | "dəyişməz" | "funksiya" | "sinif" | "struktur" | "interfeys" | "sadalama"
                | "modul" | "obyekt" | "qarışıq" | "qurucu" | "silinsin" | "metod" | "xassə" | "genişlət"
                | "komponent" | "mağaza" | "asinxron" | "generator" | "mücərrəd" | "tənbəl" | "əvəz et"
                | "statik"
        ) {
            return true;
        }
        if a == "tip" {
            return self.növ(1) == Növ::Ad && self.op_i(2, &["="]);
        }
        if GÖRÜNÜŞLƏR.contains(&a) {
            return true;
        }
        if a == "son" {
            return self.acar_i(1, &["sinif", "metod", "funksiya"]);
        }
        false
    }

    fn modifikatorlar(&mut self) -> Mod {
        let mut m = Mod::default();
        loop {
            let tok = self.bax(0);
            if tok.növ != Növ::Acar {
                break;
            }
            let a = tok.s.as_str();
            if GÖRÜNÜŞLƏR.contains(&a) {
                m.görünüş = Some(a.to_string());
            } else if a == "statik" {
                m.statik = true;
            } else if a == "mücərrəd" {
                m.mücərrəd = true;
            } else if a == "tənbəl" {
                m.tənbəl = true;
            } else if a == "əvəz et" {
                m.əvəz = true;
            } else if a == "asinxron" {
                m.asinxron = true;
            } else if a == "generator" {
                m.generator = true;
            } else if a == "son" && self.acar_i(1, &["sinif", "metod", "funksiya"]) {
                m.son = true;
            } else if a == "sabit" && self.acar_i(1, &["xassə"]) {
                m.sabit = true;
            } else {
                break;
            }
            self.al();
        }
        m
    }

    fn elan(&mut self) -> N<Cümlə> {
        let m = self.modifikatorlar();
        let tok = self.bax(0).clone();
        if tok.növ != Növ::Acar {
            self.xəta("ALQ-P001", "Elan gözlənilirdi", "modifikatorlardan sonra elan olmalıdır", &[]);
            return Err(PX);
        }
        let a = tok.s.as_str();
        match a {
            "dəyişən" | "sabit" | "dəyişməz" => self.dəyişən_elanı(),
            "funksiya" => self.funksiya_elanı(&m),
            "metod" => self.metod_elanı(&m),
            "xassə" => self.xassə_elanı(&m),
            "qurucu" => self.qurucu_elanı(),
            "silinsin" => {
                let yer = self.al().yer;
                self.tələb_op("(", "")?;
                self.tələb_op(")", "")?;
                let g = self.blok(&[]);
                self.son_tələb(None)?;
                Ok(Cümlə::Dağıdıcı(yer, gövdə(g)))
            }
            "sinif" | "struktur" | "obyekt" | "komponent" | "mağaza" => self.sinif_elanı(&m, a),
            "interfeys" => self.interfeys_elanı(),
            "sadalama" => self.sadalama_elanı(),
            "qarışıq" => {
                let yer = self.al().yer;
                let ad = self.tələb_ad("qarışıq adı")?;
                let üzvlər = self.sinif_üzvləri();
                self.son_tələb(Some("qarışıq"))?;
                Ok(Cümlə::Qarışıq { yer, ad, üzvlər })
            }
            "genişlət" => {
                let yer = self.al().yer;
                let tip = self.tip()?;
                let üzvlər = self.sinif_üzvləri();
                self.son_tələb(Some("genişlət"))?;
                Ok(Cümlə::Genişlətmə { yer, tip, üzvlər })
            }
            "tip" => {
                let yer = self.al().yer;
                let ad = self.tələb_ad("tip adı")?;
                self.generiklər()?;
                self.tələb_op("=", "tip aliası")?;
                let tip = self.tip()?;
                self.cümlə_sonu()?;
                Ok(Cümlə::TipAliası { yer, ad, tip })
            }
            "modul" => {
                let yer = self.al().yer;
                let ad = self.tələb_ad("modul adı")?;
                let g = self.blok(&[]);
                self.son_tələb(Some("modul"))?;
                Ok(Cümlə::Modul { yer, ad, gövdə: gövdə(g) })
            }
            _ => {
                self.xəta("ALQ-P001", "Elan gözlənilirdi", &format!("`{}` elan başlada bilməz", a), &[]);
                Err(PX)
            }
        }
    }

    fn dəyişən_elanı(&mut self) -> N<Cümlə> {
        let tok = self.al();
        let növ = tok.s.clone();
        let mut bağlamalar = vec![];
        let mut dəyərlər = vec![];

        let mut ilk = self.bağlama()?;
        if self.qəbul_op(&[":"]).is_some() {
            ilk.tip = Some(self.tip()?);
        }
        // Fərdi forma: `dəyişən a = 0, b = 1`
        if self.op(&["="]) {
            self.al();
            bağlamalar.push(ilk);
            dəyərlər.push(self.ifadə(0)?);
            while self.qəbul_op(&[","]).is_some() {
                let mut b = self.bağlama()?;
                if self.qəbul_op(&[":"]).is_some() {
                    b.tip = Some(self.tip()?);
                }
                self.tələb_op("=", "çoxlu dəyişən elanı")?;
                bağlamalar.push(b);
                dəyərlər.push(self.ifadə(0)?);
            }
            self.cümlə_sonu()?;
            return Ok(Cümlə::DəyişənElanı { yer: tok.yer, növ, bağlamalar, dəyərlər });
        }
        // Ortaq forma: `dəyişən a, b = 1, 2`
        bağlamalar.push(ilk);
        while self.qəbul_op(&[","]).is_some() {
            bağlamalar.push(self.bağlama()?);
        }
        if self.qəbul_op(&[":"]).is_some() {
            let tip = self.tip()?;
            for b in bağlamalar.iter_mut() {
                if b.tip.is_none() {
                    b.tip = Some(tip.clone());
                }
            }
        }
        if self.qəbul_op(&["="]).is_some() {
            dəyərlər.push(self.ifadə(0)?);
            while self.qəbul_op(&[","]).is_some() {
                dəyərlər.push(self.ifadə(0)?);
            }
        }
        if (növ == "sabit" || növ == "dəyişməz") && dəyərlər.is_empty() {
            self.xəta(
                "ALQ-P021",
                &format!("`{}` mütləq ilkinləşdirilməlidir", növ),
                "dəyər verilməyib",
                &[&format!("nümunə: {} A = 5", növ)],
            );
        }
        self.cümlə_sonu()?;
        Ok(Cümlə::DəyişənElanı { yer: tok.yer, növ, bağlamalar, dəyərlər })
    }

    fn bağlama(&mut self) -> N<Bağlama> {
        let tok = self.bax(0).clone();
        let yer = tok.yer;
        let b = |növ| Ok(Bağlama { yer, növ, tip: None });
        if tok.opdur(&["_"]) {
            self.al();
            return b(BağlamaNöv::Atma);
        }
        if tok.opdur(&["..."]) {
            self.al();
            let ad = self.tələb_ad("ad")?;
            return b(BağlamaNöv::Qalan(ad));
        }
        if tok.opdur(&["("]) {
            self.al();
            let mut alt = vec![];
            while !self.op(&[")"]) {
                alt.push(self.bağlama()?);
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
            }
            self.tələb_op(")", "dağıtma")?;
            return b(BağlamaNöv::Kortej(alt));
        }
        if tok.opdur(&["{"]) {
            self.al();
            let mut sahələr = vec![];
            while !self.op(&["}"]) {
                self.ayırıcı_atla();
                let ad = self.tələb_ad("sahə adı")?;
                let mut alt_b = None;
                if self.qəbul_op(&[":"]).is_some() {
                    alt_b = Some(self.bağlama()?);
                }
                sahələr.push((ad, alt_b));
                self.ayırıcı_atla();
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
                self.ayırıcı_atla();
            }
            self.tələb_op("}", "obyekt dağıtması")?;
            return b(BağlamaNöv::Obyekt(sahələr));
        }
        let ad = self.tələb_ad("dəyişən adı")?;
        b(BağlamaNöv::Ad(ad))
    }

    /// Generik parametrlər: `[T]`, `[T: Müqayisəedilən, U]` (AAC-də saxlanmır).
    fn generiklər(&mut self) -> N<Vec<(String, Option<Tip>)>> {
        if !self.op(&["["]) {
            return Ok(vec![]);
        }
        self.al();
        let mut nəticə = vec![];
        while !self.op(&["]"]) {
            let ad = self.tələb_ad("generik parametr")?;
            let mut məhdudiyyət = None;
            if self.qəbul_op(&[":"]).is_some() {
                məhdudiyyət = Some(self.tip()?);
                while self.qəbul_acar(&["və"]).is_some() {
                    self.tip()?;
                }
            }
            nəticə.push((ad, məhdudiyyət));
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
        }
        self.tələb_op("]", "generik parametrlər")?;
        Ok(nəticə)
    }

    fn parametrlər(&mut self) -> N<Vec<Parametr>> {
        self.tələb_op("(", "parametr siyahısı")?;
        let mut nəticə: Vec<Parametr> = vec![];
        let mut yalnız_adlı = false;
        self.ayırıcı_atla();
        while !self.op(&[")"]) {
            self.ayırıcı_atla();
            if self.op(&["*"]) && (self.op_i(1, &[","]) || self.op_i(1, &[")"])) {
                self.al();
                yalnız_adlı = true;
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
                continue;
            }
            let yer = self.bax(0).yer;
            let mut variadic = false;
            let mut adlı_variadic = false;
            if self.qəbul_op(&["..."]).is_some() {
                variadic = true;
            } else if self.qəbul_op(&["**"]).is_some() {
                adlı_variadic = true;
            }
            let mut xassə_görünüşü = None;
            if self.növ(0) == Növ::Acar
                && GÖRÜNÜŞLƏR.contains(&self.bax(0).s.as_str())
                && self.acar_i(1, &["xassə"])
            {
                xassə_görünüşü = Some(self.al().s);
                self.al();
            } else if self.acar(&["xassə"]) {
                xassə_görünüşü = Some("açıq".to_string());
                self.al();
            }
            let ad = self.tələb_ad("parametr adı")?;
            let tip = if self.qəbul_op(&[":"]).is_some() { Some(self.tip()?) } else { None };
            let standart = if self.qəbul_op(&["="]).is_some() { Some(self.ifadə(0)?) } else { None };
            nəticə.push(Parametr { yer, ad, tip, standart, variadic, adlı_variadic, yalnız_adlı, xassə_görünüşü });
            self.ayırıcı_atla();
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
            self.ayırıcı_atla();
        }
        self.tələb_op(")", "parametr siyahısı")?;

        let mut standart_görüldü = false;
        for p in &nəticə {
            if p.variadic || p.adlı_variadic || p.yalnız_adlı {
                continue;
            }
            if p.standart.is_some() {
                standart_görüldü = true;
            } else if standart_görüldü {
                self.x.xəta(
                    "ALQ-P020",
                    "Standart dəyərli parametr standartsızdan əvvəl gələ bilməz",
                    Some(p.yer),
                    &format!("`{}` parametrinin standart dəyəri yoxdur", p.ad),
                    &["standart dəyərli parametrləri sona keçirin"],
                );
            }
        }
        if nəticə.len() > 1 {
            for (i, p) in nəticə[..nəticə.len() - 1].iter().enumerate() {
                // `...a, **b` icazəlidir: adlı variadic sonda qala bilər
                if p.variadic && !nəticə[i + 1..].iter().all(|q| q.adlı_variadic) {
                    self.x.xəta(
                        "ALQ-P021",
                        "Variadic parametr sonuncu olmalıdır",
                        Some(p.yer),
                        &format!("`...{}` ortadadır", p.ad),
                        &[],
                    );
                }
            }
        }
        Ok(nəticə)
    }

    fn funksiya_elanı(&mut self, m: &Mod) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.tələb_ad("funksiya adı")?;
        self.generiklər()?;
        let parametrlər = self.parametrlər()?;
        if self.qəbul_op(&["->"]).is_some() {
            self.tip()?;
        }
        let g = self.funksiya_gövdəsi(m.generator);
        self.son_tələb(Some("funksiya"))?;
        Ok(Cümlə::Funksiya(Rc::new(A::Funksiya {
            yer,
            ad,
            parametrlər: Rc::new(parametrlər),
            gövdə: Some(gövdə(g)),
            asinxron: m.asinxron,
            generator: m.generator,
            annotasiyalar: vec![],
            bəzəyicilər: vec![],
            statik: false,
            mücərrəd: false,
        })))
    }

    fn metod(yer: Yer, ad: String, p: Vec<Parametr>, g: Option<A::Gövdə>, m: &Mod, mücərrəd: bool) -> Cümlə {
        Cümlə::Metod(Rc::new(A::Funksiya {
            yer,
            ad,
            parametrlər: Rc::new(p),
            gövdə: g,
            asinxron: m.asinxron,
            generator: m.generator,
            annotasiyalar: vec![],
            bəzəyicilər: vec![],
            statik: m.statik,
            mücərrəd,
        }))
    }

    fn metod_elanı(&mut self, m: &Mod) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.tələb_ad("metod adı")?;
        self.generiklər()?;
        let parametrlər = self.parametrlər()?;
        if self.qəbul_op(&["->"]).is_some() {
            self.tip()?;
        }
        if m.mücərrəd {
            self.cümlə_sonu()?;
            return Ok(Self::metod(yer, ad, parametrlər, None, m, true));
        }
        let g = self.funksiya_gövdəsi(m.generator);
        self.son_tələb(Some("metod"))?;
        Ok(Self::metod(yer, ad, parametrlər, Some(gövdə(g)), m, false))
    }

    fn xassə_elanı(&mut self, m: &Mod) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.tələb_ad("xassə adı")?;
        let tip = if self.qəbul_op(&[":"]).is_some() { Some(self.tip()?) } else { None };
        let standart = if self.qəbul_op(&["="]).is_some() { Some(self.ifadə(0)?) } else { None };
        let xassə = |standart, tənbəl, oxu, yaz, yaz_parametri| {
            Ok(Cümlə::Xassə(Rc::new(A::Xassə {
                yer,
                ad: ad.clone(),
                tip: tip.clone(),
                standart,
                statik: m.statik,
                tənbəl,
                oxu,
                yaz,
                yaz_parametri,
                annotasiyalar: vec![],
            })))
        };

        // Aksessorlar — `oxu` / `yaz` kontekstli sözlərdir
        if self.növ(0) == Növ::SətirSonu {
            let mut baxış = 1;
            while self.növ(baxış) == Növ::SətirSonu {
                baxış += 1;
            }
            let nd = self.bax(baxış);
            if nd.növ == Növ::Ad && (nd.s == "oxu" || nd.s == "yaz") {
                let mut oxu = None;
                let mut yaz = None;
                let mut yaz_parametri = None;
                self.ayırıcı_atla();
                while self.növ(0) == Növ::Ad && (self.bax(0).s == "oxu" || self.bax(0).s == "yaz") {
                    let hansı = self.al().s;
                    if hansı == "yaz" && self.op(&["("]) {
                        self.al();
                        yaz_parametri = Some(self.tələb_ad("parametr")?);
                        self.tələb_op(")", "")?;
                    }
                    let g = self.blok(&[]);
                    self.son_tələb(None)?;
                    if hansı == "oxu" {
                        oxu = Some(gövdə(g));
                    } else {
                        yaz = Some(gövdə(g));
                    }
                    self.ayırıcı_atla();
                }
                self.son_tələb(Some("xassə"))?;
                return xassə(standart, m.tənbəl, oxu, yaz, yaz_parametri);
            }
        }
        // Tənbəl xassə: `tənbəl xassə x: T  <gövdə>  son`
        if m.tənbəl && standart.is_none() {
            let g = self.blok(&[]);
            self.son_tələb(Some("xassə"))?;
            return xassə(None, true, Some(gövdə(g)), None, None);
        }
        self.cümlə_sonu()?;
        xassə(standart, m.tənbəl, None, None, None)
    }

    fn qurucu_elanı(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let mut ad = None;
        if self.növ(0) == Növ::Ad {
            ad = Some(self.al().s);
        }
        let parametrlər = self.parametrlər()?;
        let qısa_ola_bilər = parametrlər.iter().any(|p| p.xassə_görünüşü.as_deref().is_some_and(|s| !s.is_empty()));
        let qurucu = |p: Vec<Parametr>, g: Vec<Cümlə>, ad| {
            Ok(Cümlə::Qurucu(Rc::new(A::Qurucu { yer, ad, parametrlər: Rc::new(p), gövdə: gövdə(g) })))
        };

        // Qısa forma: GİRİNTİ həll edir (spesifikasiya § 6.3.1)
        if qısa_ola_bilər && self.növ(0) == Növ::SətirSonu {
            let mut j = self.i;
            while self.t[j].növ == Növ::SətirSonu || self.t[j].opdur(&[";"]) {
                j += 1;
            }
            let növbəti = &self.t[j];
            if növbəti.növ == Növ::FaylSonu || növbəti.yer.sütun() <= yer.sütun() {
                if növbəti.acardır(&["son"]) && növbəti.yer.sütun() == yer.sütun() {
                    self.ayırıcı_atla();
                    self.son_tələb(Some("qurucu"))?;
                }
                return qurucu(parametrlər, vec![], ad);
            }
        }

        let g = self.blok(SINIF_UZV_ACARLARI);
        if !g.is_empty() {
            if !self.acar(&["son"]) {
                self.xəta(
                    "ALQ-P002",
                    "`son` gözlənilirdi",
                    "qurucunun gövdəsi bağlanmayıb",
                    &["gövdəsi olan qurucu `son` ilə bitməlidir"],
                );
                return Err(PX);
            }
            self.son_tələb(Some("qurucu"))?;
        } else if qısa_ola_bilər {
            // Qısa forma — `son` sinfə məxsusdur
        } else if self.acar(&["son"]) {
            self.son_tələb(Some("qurucu"))?;
        }
        qurucu(parametrlər, g, ad)
    }

    fn sinif_üzvləri(&mut self) -> Vec<Cümlə> {
        let mut üzvlər = vec![];
        self.ayırıcı_atla();
        while !self.sonudur() && !self.acar(&["son"]) {
            if self.x.dolubmu() {
                break;
            }
            if let Err(PX) = self.sinif_üzvü(&mut üzvlər) {
                self.bərpa();
            }
            self.ayırıcı_atla();
        }
        üzvlər
    }

    fn sinif_üzvü(&mut self, üzvlər: &mut Vec<Cümlə>) -> N<()> {
        if self.op(&["@"]) {
            let mut annotasiyalar = vec![];
            while self.op(&["@"]) {
                annotasiyalar.push(self.annotasiya()?);
                self.ayırıcı_atla();
            }
            let ü = self.elan()?;
            üzvlər.push(Self::annotasiyaları_qoy(ü, annotasiyalar));
        } else if self.elan_başlanğıcıdır() {
            üzvlər.push(self.elan()?);
        } else if let Some(ü) = self.komponent_üzvü()? {
            üzvlər.push(ü);
        } else {
            let tok = self.bax(0).clone();
            self.xəta(
                "ALQ-P022",
                "Sinif üzvü gözlənilirdi",
                &format!("`{}` burada ola bilməz", göstər(&tok)),
                &["icazəli üzvlər: xassə, metod, qurucu, silinsin, statik üzvlər"],
            );
            return Err(PX);
        }
        Ok(())
    }

    /// `vəziyyət`, `hesablanan`, `əməl`, `hadisə`, `göstər`.
    fn komponent_üzvü(&mut self) -> N<Option<Cümlə>> {
        let tok = self.bax(0);
        if tok.növ != Növ::Ad {
            return Ok(None);
        }
        let a = tok.s.clone();
        let xassə = |yer, ad, tip, standart, oxu, annot: &[&str]| {
            Cümlə::Xassə(Rc::new(A::Xassə {
                yer,
                ad,
                tip,
                standart,
                statik: false,
                tənbəl: false,
                oxu,
                yaz: None,
                yaz_parametri: None,
                annotasiyalar: annot.iter().map(|s| s.to_string()).collect(),
            }))
        };
        match a.as_str() {
            "vəziyyət" => {
                let yer = self.al().yer;
                let ad = self.tələb_ad("vəziyyət adı")?;
                let tip = if self.qəbul_op(&[":"]).is_some() { Some(self.tip()?) } else { None };
                let standart = if self.qəbul_op(&["="]).is_some() { Some(self.ifadə(0)?) } else { None };
                self.cümlə_sonu()?;
                Ok(Some(xassə(yer, ad, tip, standart, None, &["vəziyyət"])))
            }
            "hadisə" => {
                let yer = self.al().yer;
                let ad = self.tələb_ad("hadisə adı")?;
                self.cümlə_sonu()?;
                Ok(Some(xassə(yer, ad, None, None, None, &["hadisə"])))
            }
            "hesablanan" => {
                let yer = self.al().yer;
                let ad = self.tələb_ad("hesablanan xassə adı")?;
                let tip = if self.qəbul_op(&[":"]).is_some() { Some(self.tip()?) } else { None };
                let g = self.blok(&[]);
                self.son_tələb(None)?;
                Ok(Some(xassə(yer, ad, tip, None, Some(gövdə(g)), &[])))
            }
            "əməl" | "göstər" => {
                let yer = self.al().yer;
                let (ad, parametrlər) = if a == "göstər" {
                    if self.op(&["("]) {
                        self.al();
                        self.tələb_op(")", "")?;
                    }
                    ("göstər".to_string(), vec![])
                } else {
                    let ad = self.tələb_ad("əməl adı")?;
                    (ad, self.parametrlər()?)
                };
                if self.qəbul_op(&["->"]).is_some() {
                    self.tip()?;
                }
                let g = self.blok(&[]);
                self.son_tələb(None)?;
                Ok(Some(Self::metod(yer, ad, parametrlər, Some(gövdə(g)), &Mod::default(), false)))
            }
            _ => Ok(None),
        }
    }

    fn sinif_elanı(&mut self, m: &Mod, quruluş: &str) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.tələb_ad(&format!("{} adı", quruluş))?;
        self.generiklər()?;
        let mut baza = None;
        let mut interfeyslər = vec![];
        let mut qarışıqlar = vec![];
        if self.qəbul_acar(&["miras"]).is_some() {
            baza = Some(self.tip()?);
            if quruluş == "struktur" {
                self.x.xəta(
                    "ALQ-T060",
                    "`struktur` miras ala bilməz",
                    Some(yer),
                    "strukturlar dəyər tipidir",
                    &["miras üçün `sinif` istifadə edin"],
                );
            }
        }
        if self.qəbul_acar(&["tətbiq"]).is_some() {
            interfeyslər.push(self.tip()?);
            while self.qəbul_op(&[","]).is_some() {
                interfeyslər.push(self.tip()?);
            }
        }
        if self.qəbul_acar(&["ilə"]).is_some() {
            qarışıqlar.push(self.tip()?);
            while self.qəbul_op(&[","]).is_some() {
                qarışıqlar.push(self.tip()?);
            }
        }
        let üzvlər = self.sinif_üzvləri();
        let son_növ = if SON_NÖVLƏRİ.contains(&quruluş) { quruluş } else { "sinif" };
        self.son_tələb(Some(son_növ))?;
        Ok(Cümlə::Sinif(Rc::new(A::SinifE {
            yer,
            ad,
            üzvlər,
            baza,
            interfeyslər,
            qarışıqlar,
            mücərrəd: m.mücərrəd,
            son: m.son,
            quruluş: quruluş.to_string(),
            annotasiyalar: vec![],
            bəzəyicilər: vec![],
        })))
    }

    fn interfeys_elanı(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.tələb_ad("interfeys adı")?;
        self.generiklər()?;
        if self.qəbul_acar(&["miras"]).is_some() {
            self.tip()?;
            while self.qəbul_op(&[","]).is_some() {
                self.tip()?;
            }
        }
        let mut üzvlər = vec![];
        self.ayırıcı_atla();
        while !self.sonudur() && !self.acar(&["son"]) {
            if let Err(PX) = self.interfeys_üzvü(&mut üzvlər) {
                self.bərpa();
            }
            self.ayırıcı_atla();
        }
        self.son_tələb(Some("interfeys"))?;
        Ok(Cümlə::İnterfeys { yer, ad, üzvlər })
    }

    fn interfeys_üzvü(&mut self, üzvlər: &mut Vec<Cümlə>) -> N<()> {
        if self.acar(&["metod"]) {
            let m_yer = self.al().yer;
            let m_ad = self.tələb_ad("metod adı")?;
            self.generiklər()?;
            let p = self.parametrlər()?;
            if self.qəbul_op(&["->"]).is_some() {
                self.tip()?;
            }
            if self.növ(0) == Növ::SətirSonu {
                self.cümlə_sonu()?;
                üzvlər.push(Self::metod(m_yer, m_ad, p, None, &Mod::default(), true));
            } else {
                let g = self.blok(&[]);
                self.son_tələb(Some("metod"))?;
                üzvlər.push(Self::metod(m_yer, m_ad, p, Some(gövdə(g)), &Mod::default(), false));
            }
        } else if self.acar(&["xassə"]) {
            let m = self.modifikatorlar();
            üzvlər.push(self.xassə_elanı(&m)?);
        } else {
            self.xəta("ALQ-P022", "İnterfeys üzvü gözlənilirdi", "yalnız `metod` və `xassə` ola bilər", &[]);
            return Err(PX);
        }
        Ok(())
    }

    fn sadalama_elanı(&mut self) -> N<Cümlə> {
        let yer = self.al().yer;
        let ad = self.tələb_ad("sadalama adı")?;
        self.generiklər()?;
        let əsas_tip = if self.qəbul_op(&[":"]).is_some() { Some(self.tip()?) } else { None };
        let mut variantlar = vec![];
        let mut üzvlər = vec![];
        self.ayırıcı_atla();
        while !self.sonudur() && !self.acar(&["son"]) {
            if self.elan_başlanğıcıdır() || self.op(&["@"]) {
                üzvlər = self.sinif_üzvləri();
                break;
            }
            if let Err(PX) = self.variant(&mut variantlar) {
                self.bərpa();
            }
            self.ayırıcı_atla();
        }
        self.son_tələb(Some("sadalama"))?;
        Ok(Cümlə::Sadalama { yer, ad, variantlar, üzvlər, əsas_tip })
    }

    fn variant(&mut self, variantlar: &mut Vec<A::SadalamaVariantı>) -> N<()> {
        let v_yer = self.bax(0).yer;
        let v_ad = self.tələb_ad("variant adı")?;
        let mut dəyər = None;
        let mut arqumentlər = vec![];
        let mut parametrlər = vec![];
        if self.qəbul_op(&["="]).is_some() {
            dəyər = Some(self.ifadə(0)?);
        } else if self.op(&["("]) {
            if self.variant_parametrlidir() {
                parametrlər = self.parametrlər()?;
            } else {
                arqumentlər = self.arqumentlər()?;
            }
        }
        variantlar.push(A::SadalamaVariantı { yer: v_yer, ad: v_ad, dəyər, arqumentlər, parametrlər });
        self.cümlə_sonu()
    }

    /// `(ad: Tip)` formasını `(dəyər, dəyər)`-dən ayırır.
    fn variant_parametrlidir(&self) -> bool {
        let mut j = self.i + 1;
        let mut dərinlik = 0;
        while j < self.t.len() {
            let tok = &self.t[j];
            if tok.növ == Növ::Op {
                match tok.s.as_str() {
                    "(" | "[" | "{" => dərinlik += 1,
                    ")" | "]" | "}" => {
                        if dərinlik == 0 {
                            return false;
                        }
                        dərinlik -= 1;
                    }
                    ":" if dərinlik == 0 => return true,
                    _ => {}
                }
            }
            j += 1;
        }
        false
    }

    // ═══════════════════════════════════════════════════════════════
    //  Tiplər
    // ═══════════════════════════════════════════════════════════════

    pub fn tip(&mut self) -> N<Tip> {
        let yer = self.bax(0).yer;
        let ilk = self.tip_əsas()?;
        if !self.op(&["|"]) {
            return Ok(ilk);
        }
        let mut variantlar = vec![ilk];
        while self.qəbul_op(&["|"]).is_some() {
            variantlar.push(self.tip_əsas()?);
        }
        Ok(Tip::Birləşmə { yer, variantlar })
    }

    fn tip_əsas(&mut self) -> N<Tip> {
        let tok = self.bax(0).clone();
        let yer = tok.yer;

        if tok.acardır(&["funksiyaTipi"])
            || (tok.növ == Növ::Ad && tok.s == "funksiyaTipi" && self.op_i(1, &["("]))
        {
            self.al();
            self.tələb_op("(", "funksiya tipi")?;
            let mut parametrlər = vec![];
            while !self.op(&[")"]) {
                parametrlər.push(self.tip()?);
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
            }
            self.tələb_op(")", "")?;
            let qaytarma = if self.qəbul_op(&["->"]).is_some() { Some(Box::new(self.tip()?)) } else { None };
            let ixtiyari = self.qəbul_op(&["?"]).is_some();
            return Ok(Tip::Funksiya { yer, parametrlər, qaytarma, ixtiyari });
        }

        if tok.opdur(&["("]) {
            self.al();
            let mut ilk = self.tip()?;
            if self.op(&[","]) {
                let mut elementlər = vec![ilk];
                while self.qəbul_op(&[","]).is_some() {
                    if self.op(&[")"]) {
                        break;
                    }
                    elementlər.push(self.tip()?);
                }
                self.tələb_op(")", "kortej tipi")?;
                let ixtiyari = self.qəbul_op(&["?"]).is_some();
                return Ok(Tip::Kortej { yer, elementlər, ixtiyari });
            }
            self.tələb_op(")", "")?;
            if self.qəbul_op(&["?"]).is_some() {
                if let Tip::Ad { ixtiyari, .. } = &mut ilk {
                    *ixtiyari = true;
                }
            }
            return Ok(ilk);
        }

        if tok.növ == Növ::Ad || (tok.növ == Növ::Acar && crate::acar::TIP_ADLARI.contains(&tok.s.as_str())) {
            let mut yol = vec![self.al().s];
            while self.op(&["."]) && self.növ(1) == Növ::Ad {
                self.al();
                yol.push(self.al().s);
            }
            let mut arqumentlər = vec![];
            if self.op(&["["]) {
                self.al();
                while !self.op(&["]"]) {
                    arqumentlər.push(self.tip()?);
                    if self.qəbul_op(&[","]).is_none() {
                        break;
                    }
                }
                self.tələb_op("]", "generik tip arqumentləri")?;
            }
            let ixtiyari = self.qəbul_op(&["?"]).is_some();
            return Ok(Tip::Ad { yer, yol, arqumentlər, ixtiyari });
        }

        self.xəta(
            "ALQ-T002",
            "Naməlum tip",
            &format!("`{}` tip adı deyil", göstər(&tok)),
            &[
                "əsas tiplər: tam, onluq, mətn, məntiq, simvol, bayt",
                "kolleksiyalar: siyahı[T], lüğət[A,D], dəst[T], kortej[A,B]",
            ],
        );
        Err(PX)
    }

    // ═══════════════════════════════════════════════════════════════
    //  İfadələr — prioritet dırmaşması
    // ═══════════════════════════════════════════════════════════════

    pub fn ifadə(&mut self, min_p: i32) -> N<E> {
        let mut sol = self.tək_operand()?;
        loop {
            if self.şəkilçi(ÇIXIŞLIQ_ŞƏKİLÇİLƏRİ) {
                if prioritet("..").unwrap().0 < min_p {
                    break;
                }
                sol = self.şəkilçili_diapazon(sol)?;
                continue;
            }
            if self.şəkilçi(YÖNLÜK_ŞƏKİLÇİLƏRİ) && self.bax(2).acardır(&["qədər"]) {
                break;
            }
            let tok = self.bax(0);
            let Some(mut op) = binar_op(tok) else { break };
            let (p, sağdan) = prioritet(&op).unwrap();
            if p < min_p {
                break;
            }
            let yer = tok.yer;
            self.al();
            if op == "kimi" && self.op(&["?"]) {
                self.al();
                op = "kimi?".into();
            }
            let növbəti_min = if sağdan { p } else { p + 1 };
            let yeni = match op.as_str() {
                "kimi" | "kimi?" => İfadə::Çevirmə(yer, sol, self.tip()?, op == "kimi?"),
                "tipidir" => İfadə::TipYoxlama(yer, sol, self.tip()?),
                "içindədir" => İfadə::Üzvlük(yer, sol, self.ifadə(növbəti_min)?),
                "boşdur" => İfadə::BoşYoxlama(yer, sol, false),
                "boş deyil" => İfadə::BoşYoxlama(yer, sol, true),
                ".." | "..<" => {
                    let son = self.ifadə(növbəti_min)?;
                    let mut addım = None;
                    if self.qəbul_acar(&["addım"]).is_some() {
                        addım = Some(self.ifadə(növbəti_min)?);
                    }
                    İfadə::Diapazon(yer, sol, son, addım, op == "..<")
                }
                "|>" => İfadə::Boru(yer, sol, self.ifadə(növbəti_min)?),
                _ => {
                    let sağ = self.ifadə(növbəti_min)?;
                    İfadə::İkili(yer, sol, op, sağ)
                }
            };
            sol = Rc::new(yeni);
        }
        Ok(sol)
    }

    /// `-` sol tərəfə və şəkilçiyə bitişikdir: `1-dən`, `n-ə`.
    fn şəkilçi(&self, şəkilçilər: &[&str]) -> bool {
        let tire = self.bax(0);
        if !tire.opdur(&["-"]) || self.i == 0 {
            return false;
        }
        let ş = self.bax(1);
        let əvvəlki = &self.t[self.i - 1];
        matches!(ş.növ, Növ::Ad | Növ::Acar)
            && şəkilçilər.contains(&ş.s.as_str())
            && əvvəlki.yer.başlanğıc + əvvəlki.yer.uzunluq == tire.yer.başlanğıc
            && tire.yer.başlanğıc + tire.yer.uzunluq == ş.yer.başlanğıc
    }

    /// `A-dən B-ə qədər` — hər iki uc daxil, addım ±1 (§ 4.14).
    fn şəkilçili_diapazon(&mut self, başlanğıc: E) -> N<E> {
        let yer = self.al().yer;
        self.al();
        let son = self.ifadə(prioritet("..").unwrap().0 + 1)?;
        if !self.şəkilçi(YÖNLÜK_ŞƏKİLÇİLƏRİ) {
            self.xəta(
                "ALQ-P038",
                "Diapazonun sonu gözlənilirdi",
                "`A-dən B-ə qədər` formasında `B-ə` yazılmalıdır",
                &["məs.: `1-dən 10-a qədər`"],
            );
            return Err(PX);
        }
        self.al();
        self.al();
        self.tələb_acar("qədər")?;
        let d = Rc::new(İfadə::Diapazon(yer, başlanğıc, son, None, false));
        self.şəkilçili = Some(d.clone());
        Ok(d)
    }

    fn tək_operand(&mut self) -> N<E> {
        let tok = self.bax(0).clone();
        if tok.növ == Növ::Op && TƏK_OPERATORLAR.contains(&tok.s.as_str()) {
            let yer = self.al().yer;
            return Ok(Rc::new(İfadə::Tək(yer, tok.s, self.tək_operand()?)));
        }
        if tok.acardır(&["deyil"]) {
            // § 3.4: `deyil a == b` → `deyil (a == b)`
            let yer = self.al().yer;
            return Ok(Rc::new(İfadə::Tək(yer, "deyil".into(), self.ifadə(5)?)));
        }
        if tok.acardır(&["gözlə"]) {
            let yer = self.al().yer;
            return Ok(Rc::new(İfadə::Gözlə(yer, self.tək_operand()?)));
        }
        if tok.acardır(&["yeni"]) {
            let y = self.yeni_ifadə()?;
            return self.postfiks_davam(y);
        }
        self.qüvvət()
    }

    fn qüvvət(&mut self) -> N<E> {
        let sol = self.postfiks()?;
        if self.op(&["**"]) {
            let yer = self.al().yer;
            return Ok(Rc::new(İfadə::İkili(yer, sol, "**".into(), self.tək_operand()?)));
        }
        Ok(sol)
    }

    fn yeni_ifadə(&mut self) -> N<E> {
        let yer = self.al().yer;
        let tip = self.tip_əsas()?;
        let mut qurucu = None;
        if self.op(&["."]) && self.növ(1) == Növ::Ad {
            self.al();
            qurucu = Some(self.al().s);
        }
        let arqumentlər = if self.op(&["("]) { self.arqumentlər()? } else { vec![] };
        Ok(Rc::new(İfadə::Yeni(yer, tip, qurucu, arqumentlər)))
    }

    fn postfiks(&mut self) -> N<E> {
        let e = self.əsas_ifadə()?;
        self.postfiks_davam(e)
    }

    fn postfiks_davam(&mut self, mut ifadə: E) -> N<E> {
        loop {
            let tok = self.bax(0).clone();
            if tok.opdur(&[".", "?."]) {
                let təhlükəsiz = tok.s == "?.";
                let yer = self.al().yer;
                let nd = self.bax(0);
                if matches!(nd.növ, Növ::Tam | Növ::Ad | Növ::Acar) {
                    let ad = dəyər_mətni(nd);
                    self.al();
                    ifadə = Rc::new(İfadə::Üzv(yer, ifadə, ad.into(), təhlükəsiz));
                    continue;
                }
                self.xəta(
                    "ALQ-P001",
                    "Üzv adı gözlənilirdi",
                    "`.`-dan sonra ad və ya kortej indeksi olmalıdır",
                    &[],
                );
                return Err(PX);
            }
            if tok.opdur(&["("]) {
                let a = self.arqumentlər()?;
                ifadə = Rc::new(İfadə::Çağırış(tok.yer, ifadə, a));
                continue;
            }
            if tok.opdur(&["["]) {
                let yer = self.al().yer;
                if self.op(&["..", "..<"]) {
                    let xaric = self.al().s == "..<";
                    let son = if self.op(&["]"]) { None } else { Some(self.ifadə(0)?) };
                    self.tələb_op("]", "dilim")?;
                    ifadə = Rc::new(İfadə::Dilim(yer, ifadə, None, son, xaric));
                    continue;
                }
                // Diapazon prioriteti 7-dir; 8-dən başlayırıq ki `[1..3]` dilim olsun
                let indeks = self.ifadə(8)?;
                if self.op(&["..", "..<"]) {
                    let xaric = self.al().s == "..<";
                    let son = if self.op(&["]"]) { None } else { Some(self.ifadə(0)?) };
                    self.tələb_op("]", "dilim")?;
                    ifadə = Rc::new(İfadə::Dilim(yer, ifadə, Some(indeks), son, xaric));
                    continue;
                }
                self.tələb_op("]", "indeksləmə")?;
                ifadə = Rc::new(İfadə::İndeks(yer, ifadə, indeks));
                continue;
            }
            if tok.opdur(&["!"]) {
                let yer = self.al().yer;
                ifadə = Rc::new(İfadə::MəcburiAçma(yer, ifadə));
                continue;
            }
            if tok.opdur(&["?"]) && !self.op_i(1, &["?"]) {
                let yer = self.al().yer;
                ifadə = Rc::new(İfadə::Yayma(yer, ifadə));
                continue;
            }
            break;
        }
        Ok(ifadə)
    }

    fn arqumentlər(&mut self) -> N<Vec<Arqument>> {
        self.tələb_op("(", "arqument siyahısı")?;
        let mut nəticə: Vec<Arqument> = vec![];
        self.ayırıcı_atla();
        while !self.op(&[")"]) {
            self.ayırıcı_atla();
            if self.qəbul_op(&["..."]).is_some() {
                nəticə.push(Arqument { dəyər: self.ifadə(0)?, ad: None, yayma: true, adlı_yayma: false });
            } else if self.qəbul_op(&["**"]).is_some() {
                nəticə.push(Arqument { dəyər: self.ifadə(0)?, ad: None, yayma: false, adlı_yayma: true });
            } else if etiket_ola_bilər(self.bax(0)) && self.op_i(1, &[":"]) {
                let ad = self.al().s;
                self.al();
                nəticə.push(Arqument { dəyər: self.ifadə(0)?, ad: Some(ad), yayma: false, adlı_yayma: false });
            } else {
                nəticə.push(Arqument { dəyər: self.ifadə(0)?, ad: None, yayma: false, adlı_yayma: false });
            }
            self.ayırıcı_atla();
            if self.qəbul_op(&[","]).is_none() {
                break;
            }
            self.ayırıcı_atla();
        }
        self.tələb_op(")", "arqument siyahısı")?;

        let mut adlı_görüldü = false;
        for a in &nəticə {
            if a.ad.as_deref().is_some_and(|s| !s.is_empty()) || a.adlı_yayma {
                adlı_görüldü = true;
            } else if adlı_görüldü && !a.yayma {
                self.x.xəta(
                    "ALQ-P022",
                    "Mövqeli arqument adlıdan sonra gələ bilməz",
                    Some(a.dəyər.yer()),
                    "",
                    &["mövqeli arqumentləri əvvələ keçirin"],
                );
            }
        }
        Ok(nəticə)
    }

    // ═══════════════════════════════════════════════════════════════
    //  Əsas ifadələr
    // ═══════════════════════════════════════════════════════════════

    fn əsas_ifadə(&mut self) -> N<E> {
        while let Some(m) = self.makro_çağırışı() {
            self.makro_aç(&m, true)?;
        }
        let tok = self.bax(0).clone();
        let yer = tok.yer;
        // `sorğu hər x üçün … içində` — `sorğu` kontekstli sözdür
        if tok.növ == Növ::Ad && tok.s == "sorğu" && self.acar_i(1, &["hər"]) {
            return self.sorğu();
        }
        match tok.növ {
            Növ::Tam => {
                self.al();
                return Ok(self.vahid_quyruğu(lit(yer, LiteralD::Tam(tok.tam.clone().unwrap_or_default()))));
            }
            Növ::Onluq => {
                self.al();
                return Ok(self.vahid_quyruğu(lit(yer, LiteralD::Onluq(tok.onluq))));
            }
            Növ::Simvol => {
                self.al();
                return Ok(lit(yer, LiteralD::Simvol(tok.s.as_str().into())));
            }
            Növ::Bayt => {
                self.al();
                return Ok(lit(yer, LiteralD::Bayt(Rc::new(tok.bayt.clone()))));
            }
            Növ::Mətn => return self.mətn(),
            _ => {}
        }
        if tok.növ == Növ::Acar {
            match tok.s.as_str() {
                "doğru" | "yanlış" => {
                    self.al();
                    return Ok(lit(yer, LiteralD::Məntiq(tok.s == "doğru")));
                }
                "boş" => {
                    self.al();
                    return Ok(lit(yer, LiteralD::Boş));
                }
                "sonsuz" => {
                    self.al();
                    return Ok(lit(yer, LiteralD::Onluq(f64::INFINITY)));
                }
                "ƏdədDeyil" => {
                    self.al();
                    return Ok(lit(yer, LiteralD::Onluq(f64::NAN)));
                }
                "özü" => {
                    self.al();
                    return Ok(Rc::new(İfadə::Özü(yer)));
                }
                "üst" => {
                    self.al();
                    return Ok(Rc::new(İfadə::Üst(yer)));
                }
                "əgər" => return self.şərt_ifadəsi(),
                "seç" => {
                    let s = self.seç()?;
                    return Ok(Rc::new(İfadə::Blok(s.yer(), gövdə(vec![s]))));
                }
                "blok" => {
                    self.al();
                    let g = self.blok(&[]);
                    self.son_tələb(Some("blok"))?;
                    return Ok(Rc::new(İfadə::Blok(yer, gövdə(g))));
                }
                "cəhd et" => {
                    let c = self.cəhd()?;
                    return Ok(Rc::new(İfadə::Blok(yer, gövdə(vec![c]))));
                }
                "funksiya" | "asinxron" | "generator" => return self.anonim_funksiya(),
                _ => {}
            }
        }
        // Lambda: `x => ...`
        if tok.növ == Növ::Ad && self.op_i(1, &["=>"]) {
            let p_yer = self.bax(0).yer;
            let ad = self.al().s;
            self.al();
            let p = Parametr {
                yer: p_yer,
                ad,
                tip: None,
                standart: None,
                variadic: false,
                adlı_variadic: false,
                yalnız_adlı: false,
                xassə_görünüşü: None,
            };
            return self.lambda_gövdəsi(yer, vec![p]);
        }
        if tok.opdur(&["("]) {
            return self.mötərizə();
        }
        if tok.opdur(&["["]) {
            return self.siyahı();
        }
        if tok.opdur(&["{"]) {
            return self.fiqurlu();
        }
        if tok.növ == Növ::Acar && tok.s == "tip" {
            self.al();
            return Ok(Rc::new(İfadə::Ad(yer, tok.s.as_str().into())));
        }
        if tok.növ == Növ::Ad {
            self.al();
            return Ok(Rc::new(İfadə::Ad(yer, tok.s.as_str().into())));
        }
        if tok.növ == Növ::Jsx {
            return crate::parser_jsx::jsx_oxu(self);
        }
        if tok.növ == Növ::Acar {
            self.xəta("ALQ-P005", "İfadə gözlənilirdi", &format!("`{}` açar sözü ifadə ola bilməz", tok.s), &[]);
            return Err(PX);
        }
        self.xəta("ALQ-P005", "İfadə gözlənilirdi", &format!("`{}` gözlənilmirdi", göstər(&tok)), &[]);
        Err(PX)
    }

    fn mətn(&mut self) -> N<E> {
        let tok = self.al();
        let yer = tok.yer;
        if tok.sadə_mətndir() {
            return Ok(lit(yer, LiteralD::Mətn(tok.s.as_str().into())));
        }
        let mut hissələr = vec![];
        for p in tok.parçalar.unwrap_or_default() {
            match p {
                Parça::Mətn(s) => hissələr.push(A::ŞablonHissə::Mətn(s)),
                Parça::Kod(tokenlər, format) => {
                    let mut t = tokenlər;
                    t.push(Token::yeni(Növ::FaylSonu, "", yer));
                    let əvvəl = self.x.siyahı.len();
                    let ifadə = {
                        let mut alt = Parser::yeni(t, self.s.clone(), &mut *self.x);
                        alt.makro = std::mem::take(&mut self.makro);
                        let r = match alt.ifadə(0) {
                            Ok(e) => {
                                let qalan = alt.bax(0).clone();
                                if qalan.növ != Növ::FaylSonu {
                                    alt.xəta(
                                        "ALQ-P001",
                                        "Gözlənilməyən token",
                                        &format!("`{}` burada gözlənilmirdi", göstər(&qalan)),
                                        &["`{…}` daxilində tək ifadə olmalıdır"],
                                    );
                                }
                                e
                            }
                            Err(PX) => lit(yer, LiteralD::Mətn("".into())),
                        };
                        self.makro = std::mem::take(&mut alt.makro);
                        r
                    };
                    // CSS, JSON, regex kimi mətnlərdə `{` interpolyasiya sayılır
                    for d in self.x.siyahı[əvvəl..].iter_mut() {
                        d.köməklər.push(
                            "adi mətndə `{…}` interpolyasiyadır; fiqurlu mötərizə lazımdırsa xam mətn yazın: x\"…\" və ya x\"\"\"…\"\"\"".into(),
                        );
                    }
                    hissələr.push(A::ŞablonHissə::Kod(ifadə, format));
                }
            }
        }
        Ok(Rc::new(İfadə::Şablon(yer, hissələr)))
    }

    fn şərt_ifadəsi(&mut self) -> N<E> {
        let yer = self.al().yer;
        let mut budaqlar = vec![];
        let ş = self.ifadə(0)?;
        self.tələb_acar("onda")?;
        budaqlar.push((ş, self.budaq_ifadəsi()?));
        let mut yoxsa = None;
        loop {
            self.ayırıcı_atla();
            if self.acar(&["yoxsa əgər"]) {
                self.al();
                let ş = self.ifadə(0)?;
                self.tələb_acar("onda")?;
                budaqlar.push((ş, self.budaq_ifadəsi()?));
                continue;
            }
            if self.acar(&["yoxsa"]) {
                self.al();
                self.ayırıcı_atla();
                if self.acar(&["əgər"]) {
                    self.al();
                    let ş = self.ifadə(0)?;
                    self.tələb_acar("onda")?;
                    budaqlar.push((ş, self.budaq_ifadəsi()?));
                    continue;
                }
                yoxsa = Some(self.budaq_ifadəsi()?);
            }
            break;
        }
        self.ayırıcı_atla();
        self.tələb_acar("son")?;
        if self.acar(&["əgər"]) {
            self.al();
        }
        Ok(Rc::new(İfadə::ŞərtIfadəsi(yer, budaqlar, yoxsa)))
    }

    fn budaq_ifadəsi(&mut self) -> N<E> {
        self.ayırıcı_atla();
        self.ifadə(0)
    }

    fn anonim_funksiya(&mut self) -> N<E> {
        let yer = self.bax(0).yer;
        let asinxron = self.qəbul_acar(&["asinxron"]).is_some();
        let generator = self.qəbul_acar(&["generator"]).is_some();
        self.tələb_acar("funksiya")?;
        let parametrlər = self.parametrlər()?;
        if self.qəbul_op(&["->"]).is_some() {
            self.tip()?;
        }
        let g = self.blok(&[]);
        self.son_tələb(Some("funksiya"))?;
        Ok(Rc::new(İfadə::Lambda {
            yer,
            parametrlər: Rc::new(parametrlər),
            gövdə: LambdaGövdə::Blok(gövdə(g)),
            asinxron,
            generator,
        }))
    }

    fn lambda_gövdəsi(&mut self, yer: Yer, parametrlər: Vec<Parametr>) -> N<E> {
        let lambda = |g| {
            Ok(Rc::new(İfadə::Lambda {
                yer,
                parametrlər: Rc::new(parametrlər),
                gövdə: g,
                asinxron: false,
                generator: false,
            }))
        };
        if self.acar(&["blok"]) {
            self.al();
            let g = self.blok(&[]);
            self.son_tələb(Some("blok"))?;
            return lambda(LambdaGövdə::Blok(gövdə(g)));
        }
        let b_yer = self.bax(0).yer;
        let ifadə = self.ifadə(0)?;
        // Tək mənimsətmə gövdə ola bilər: `klik: () => özü.say += 1`
        if self.op(MƏNİMSƏTMƏ_OPLARI) {
            let op = self.al().s;
            let dəyər = self.ifadə(0)?;
            let m = Rc::new(İfadə::Mənimsətmə(b_yer, vec![ifadə], op, vec![dəyər]));
            return lambda(LambdaGövdə::Blok(gövdə(vec![Cümlə::İfadə(b_yer, m)])));
        }
        if self.op(&["++", "--"]) {
            let op = self.al().s;
            return lambda(LambdaGövdə::Blok(gövdə(vec![Cümlə::Artırma(b_yer, ifadə, op)])));
        }
        lambda(LambdaGövdə::İfadə(ifadə))
    }

    /// `(` mövqeyindən: bu lambda parametr siyahısıdırmı?
    fn lambda_mı(&self) -> bool {
        let mut j = self.i + 1;
        let mut dərinlik = 0;
        while j < self.t.len() {
            let tok = &self.t[j];
            if tok.növ == Növ::Op {
                match tok.s.as_str() {
                    "(" | "[" | "{" => dərinlik += 1,
                    ")" | "]" | "}" => {
                        if dərinlik == 0 {
                            let mut k = j + 1;
                            while k < self.t.len() && self.t[k].növ == Növ::SətirSonu {
                                k += 1;
                            }
                            return k < self.t.len() && self.t[k].opdur(&["=>", "->"]);
                        }
                        dərinlik -= 1;
                    }
                    _ => {}
                }
            } else if tok.növ == Növ::FaylSonu {
                return false;
            }
            j += 1;
        }
        false
    }

    fn mötərizə(&mut self) -> N<E> {
        if self.lambda_mı() {
            let yer = self.bax(0).yer;
            let parametrlər = self.parametrlər()?;
            if self.qəbul_op(&["->"]).is_some() {
                self.tip()?;
            }
            self.tələb_op("=>", "ox funksiyası")?;
            return self.lambda_gövdəsi(yer, parametrlər);
        }
        let yer = self.al().yer;
        self.ayırıcı_atla();
        if self.op(&[")"]) {
            self.al();
            return Ok(Rc::new(İfadə::Kortej(yer, vec![])));
        }
        let ilk = self.ifadə(0)?;
        self.ayırıcı_atla();
        if self.acar(&["üçün"]) {
            return self.qurma_quyruğu(yer, "generator", ilk, None, ")");
        }
        if self.op(&[","]) {
            let mut elementlər = vec![ilk];
            while self.qəbul_op(&[","]).is_some() {
                self.ayırıcı_atla();
                if self.op(&[")"]) {
                    break;
                }
                elementlər.push(self.ifadə(0)?);
                self.ayırıcı_atla();
            }
            self.tələb_op(")", "kortej")?;
            return Ok(Rc::new(İfadə::Kortej(yer, elementlər)));
        }
        self.tələb_op(")", "mötərizə")?;
        Ok(ilk)
    }

    fn siyahı(&mut self) -> N<E> {
        let yer = self.al().yer;
        self.ayırıcı_atla();
        if self.op(&["]"]) {
            self.al();
            return Ok(Rc::new(İfadə::Siyahı(yer, vec![], vec![])));
        }
        if self.op(&["..."]) {
            let mut elementlər = vec![];
            let mut yaymalar = vec![];
            while !self.op(&["]"]) {
                self.ayırıcı_atla();
                yaymalar.push(self.qəbul_op(&["..."]).is_some());
                elementlər.push(self.ifadə(0)?);
                self.ayırıcı_atla();
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
                self.ayırıcı_atla();
            }
            self.tələb_op("]", "siyahı")?;
            return Ok(Rc::new(İfadə::Siyahı(yer, elementlər, yaymalar)));
        }
        let ilk = self.ifadə(0)?;
        self.ayırıcı_atla();
        if self.acar(&["üçün"]) {
            return self.qurma_quyruğu(yer, "siyahı", ilk, None, "]");
        }
        let mut elementlər = vec![ilk];
        let mut yaymalar = vec![false];
        while self.qəbul_op(&[","]).is_some() {
            self.ayırıcı_atla();
            if self.op(&["]"]) {
                break;
            }
            yaymalar.push(self.qəbul_op(&["..."]).is_some());
            elementlər.push(self.ifadə(0)?);
            self.ayırıcı_atla();
        }
        self.tələb_op("]", "siyahı")?;
        Ok(Rc::new(İfadə::Siyahı(yer, elementlər, yaymalar)))
    }

    /// Lüğət cütü və ya yayma (`...digər`).
    fn lüğət_cütü(&mut self, açarlar: &mut Vec<Option<E>>, dəyərlər: &mut Vec<E>) -> N<()> {
        if self.qəbul_op(&["..."]).is_some() {
            açarlar.push(None);
            dəyərlər.push(self.ifadə(0)?);
        } else {
            let a = self.ifadə(0)?;
            self.tələb_op(":", "lüğət")?;
            açarlar.push(Some(a));
            dəyərlər.push(self.ifadə(0)?);
        }
        Ok(())
    }

    fn fiqurlu(&mut self) -> N<E> {
        let yer = self.al().yer;
        self.ayırıcı_atla();
        if self.op(&["}"]) {
            self.al();
            return Ok(Rc::new(İfadə::Lüğət(yer, vec![], vec![])));
        }
        if self.op(&["..."]) {
            let mut açarlar = vec![];
            let mut dəyərlər = vec![];
            while !self.op(&["}"]) {
                self.ayırıcı_atla();
                self.lüğət_cütü(&mut açarlar, &mut dəyərlər)?;
                self.ayırıcı_atla();
                if self.qəbul_op(&[","]).is_none() {
                    break;
                }
                self.ayırıcı_atla();
            }
            self.tələb_op("}", "lüğət")?;
            return Ok(Rc::new(İfadə::Lüğət(yer, açarlar, dəyərlər)));
        }
        let ilk = self.ifadə(0)?;
        self.ayırıcı_atla();
        if self.op(&[":"]) {
            self.al();
            let ilk_dəyər = self.ifadə(0)?;
            self.ayırıcı_atla();
            if self.acar(&["üçün"]) {
                return self.qurma_quyruğu(yer, "lüğət", ilk, Some(ilk_dəyər), "}");
            }
            let mut açarlar = vec![Some(ilk)];
            let mut dəyərlər = vec![ilk_dəyər];
            while self.qəbul_op(&[","]).is_some() {
                self.ayırıcı_atla();
                if self.op(&["}"]) {
                    break;
                }
                self.lüğət_cütü(&mut açarlar, &mut dəyərlər)?;
                self.ayırıcı_atla();
            }
            self.tələb_op("}", "lüğət")?;
            return Ok(Rc::new(İfadə::Lüğət(yer, açarlar, dəyərlər)));
        }
        if self.acar(&["üçün"]) {
            return self.qurma_quyruğu(yer, "dəst", ilk, None, "}");
        }
        let mut elementlər = vec![ilk];
        while self.qəbul_op(&[","]).is_some() {
            self.ayırıcı_atla();
            if self.op(&["}"]) {
                break;
            }
            elementlər.push(self.ifadə(0)?);
            self.ayırıcı_atla();
        }
        self.tələb_op("}", "dəst")?;
        Ok(Rc::new(İfadə::Dəst(yer, elementlər)))
    }

    fn qurma_quyruğu(
        &mut self,
        yer: Yer,
        növ: &str,
        ifadə: E,
        dəyər_ifadəsi: Option<E>,
        bağlayan: &str,
    ) -> N<E> {
        self.tələb_acar("üçün")?;
        let bağlama = self.bağlama()?;
        self.tələb_acar("içində")?;
        let mənbə = self.ifadə(0)?;
        let mut şərt = None;
        if self.qəbul_acar(&["əgər"]).is_some() {
            şərt = Some(self.ifadə(0)?);
        }
        self.ayırıcı_atla();
        self.tələb_op(bağlayan, "kolleksiya qurması")?;
        Ok(Rc::new(İfadə::Qurma { yer, növ: növ.into(), ifadə, dəyər_ifadəsi, bağlama, mənbə, şərt }))
    }

    /// JSX üçün: mənbədə `[b, b+uz)` yeri.
    pub fn mənbə_yeri(&self, b: usize, uz: usize) -> Yer {
        self.yer(b, uz)
    }
}

fn binar_op(tok: &Token) -> Option<String> {
    if matches!(tok.növ, Növ::Op | Növ::Acar) && prioritet(&tok.s).is_some() {
        return Some(tok.s.clone());
    }
    None
}

/// Adlı arqumentin etiketi: ad və ya TƏK SÖZLÜ açar söz.
fn etiket_ola_bilər(tok: &Token) -> bool {
    tok.növ == Növ::Ad || (tok.növ == Növ::Acar && !tok.s.contains(' '))
}

/// Xəta mesajlarında tokenin göstərilməsi (Python: `_göstər`).
pub fn göstər(tok: &Token) -> String {
    match tok.növ {
        Növ::SətirSonu => "sətir sonu".into(),
        Növ::FaylSonu => "fayl sonu".into(),
        _ => dəyər_mətni(tok),
    }
}

/// Mətni AAC-yə çevirir.
pub fn ayır(s: Rc<Mənbə>, x: &mut XətaToplayıcı) -> A::Proqram {
    let t = crate::lekser::Lekser::yeni(s.clone(), x).leksə();
    Parser::yeni(t, s, x).ayır()
}
