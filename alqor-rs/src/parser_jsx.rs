//! İnterfeys sintaksisi (JSX) parseri (parser_jsx.py-ın köçürməsi).
//!
//! Lekser elementi xam skan edib bir `Növ::Jsx` tokeni buraxır; burada
//! həmin aralıq MƏNBƏ MƏTNİNDƏN birbaşa oxunur. Daxildəki `{ifadə}`
//! hissələri üçün həmin ofsetdən yeni `Lekser` qurulur — mövqelər düzgün qalır.

use crate::aac::{İfadə, JSXAtribut, JSXUşaq, LiteralD, E};
use crate::elifba::{ad_başlanğıcı, ad_davamı};
use crate::lekser::{Lekser, Növ, Token};
use crate::parser::{göstər, Parser, N, PX};
use std::rc::Rc;

const BOŞLUQ: &[char] = &[' ', '\t', '\n', '\r'];

/// Python `str.isspace()`.
fn py_boşluq(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

fn py_strip(s: &[char]) -> &[char] {
    let mut b = 0;
    let mut e = s.len();
    while b < e && py_boşluq(s[b]) {
        b += 1;
    }
    while e > b && py_boşluq(s[e - 1]) {
        e -= 1;
    }
    &s[b..e]
}

/// `Növ::Jsx` tokenini AAC-yə çevirir.
pub fn jsx_oxu(p: &mut Parser) -> N<E> {
    let tok = p.al();
    let (baş, son) = tok.jsx;
    let m = p.s.mətn.clone();
    let mut o = Oxuyucu { p, m, n: son, i: baş };
    o.element()
}

struct Oxuyucu<'p, 'a> {
    p: &'p mut Parser<'a>,
    m: Vec<char>,
    n: usize,
    i: usize,
}

impl<'p, 'a> Oxuyucu<'p, 'a> {
    // ── Köməkçilər ────────────────────────────────────────────────

    fn c(&self, irəli: usize) -> Option<char> {
        let j = self.i + irəli;
        if j < self.n {
            Some(self.m[j])
        } else {
            None
        }
    }

    fn boşluq_atla(&mut self) {
        while self.i < self.n && BOŞLUQ.contains(&self.m[self.i]) {
            self.i += 1;
        }
    }

    fn xəta<T>(&mut self, mesaj: &str, qeyd: &str, köməklər: &[&str]) -> N<T> {
        let yer = self.p.mənbə_yeri(self.i.min(self.n.saturating_sub(1)), 1);
        self.p.x.xəta("ALQ-P031", mesaj, Some(yer), qeyd, köməklər);
        Err(PX)
    }

    fn ad_başlanğıcı(c: Option<char>) -> bool {
        c.is_some_and(ad_başlanğıcı)
    }

    fn ad_oxu(&mut self) -> N<String> {
        let baş = self.i;
        if !(self.i < self.n && ad_başlanğıcı(self.m[self.i])) {
            self.xəta(
                "Element adı gözlənilirdi",
                "`<` işarəsindən sonra ad olmalıdır",
                &["nümunə: <div>, <Sayğac />, <nax.Düymə />"],
            )?;
        }
        while self.i < self.n && (ad_davamı(self.m[self.i]) || matches!(self.m[self.i], '-' | '.')) {
            self.i += 1;
        }
        Ok(self.m[baş..self.i].iter().collect())
    }

    // ── Element ───────────────────────────────────────────────────

    fn element(&mut self) -> N<E> {
        let yer = self.p.mənbə_yeri(self.i, 1);
        if self.c(0) != Some('<') {
            self.xəta("`<` gözlənilirdi", "", &[])?;
        }
        self.i += 1;

        // Parça: <> ... </>
        if self.c(0) == Some('>') {
            self.i += 1;
            let uşaqlar = self.uşaqlar_oxu("")?;
            return Ok(Rc::new(İfadə::JSXParça(yer, uşaqlar)));
        }

        let ad = self.ad_oxu()?;
        let atributlar = self.atributlar_oxu(&ad)?;

        // Öz-bağlanan: <Ad />
        if self.c(0) == Some('/') {
            self.i += 1;
            if self.c(0) != Some('>') {
                self.xəta("`/>` gözlənilirdi", "öz-bağlanan element belə bitir: `/>`", &[])?;
            }
            self.i += 1;
            return Ok(Rc::new(İfadə::JSXElement(yer, ad, atributlar, vec![])));
        }
        if self.c(0) != Some('>') {
            self.xəta("`>` gözlənilirdi", &format!("`<{}` açılışı bağlanmayıb", ad), &[])?;
        }
        self.i += 1;
        let uşaqlar = self.uşaqlar_oxu(&ad)?;
        Ok(Rc::new(İfadə::JSXElement(yer, ad, atributlar, uşaqlar)))
    }

    // ── Atributlar ────────────────────────────────────────────────

    fn atributlar_oxu(&mut self, element_adı: &str) -> N<Vec<JSXAtribut>> {
        let mut nəticə = vec![];
        loop {
            self.boşluq_atla();
            let c = self.c(0);
            let Some(c) = c else { break };
            if c == '/' || c == '>' {
                break;
            }

            // Yayma: {...obyekt}
            if c == '{' {
                let baş = self.i + 1;
                let son = self.fiqurlu_sonu(self.i)?;
                let parça: Vec<char> = self.m[baş..son].to_vec();
                if !py_strip(&parça).starts_with(&['.', '.', '.']) {
                    self.xəta(
                        "Atribut adı gözlənilirdi",
                        "`{...obyekt}` yayma sintaksisi istisna olmaqla, atributlar adla yazılır",
                        &[],
                    )?;
                }
                let ind = parça.windows(3).position(|w| w == ['.', '.', '.']).unwrap_or(0);
                let ofs = baş + ind + 3;
                let ifadə = self.ifadə_oxu(ofs, son);
                nəticə.push(JSXAtribut { ad: String::new(), dəyər: Some(ifadə), yayma: true });
                self.i = son + 1;
                continue;
            }

            if !ad_başlanğıcı(c) {
                self.xəta(
                    &format!("`<{}` daxilində gözlənilməyən simvol: `{}`", element_adı, c),
                    "atribut adı, `/>` və ya `>` gözlənilirdi",
                    &[],
                )?;
            }
            let ad = self.ad_oxu()?;
            self.boşluq_atla();
            if self.c(0) != Some('=') {
                nəticə.push(JSXAtribut { ad, dəyər: None, yayma: false });
                continue;
            }
            self.i += 1;
            self.boşluq_atla();
            let d = self.atribut_dəyəri(&ad)?;
            nəticə.push(JSXAtribut { ad, dəyər: Some(d), yayma: false });
        }
        Ok(nəticə)
    }

    fn atribut_dəyəri(&mut self, ad: &str) -> N<E> {
        let c = self.c(0);
        if let Some(q @ ('"' | '\'')) = c {
            // Dəyər ALQOR MƏTN LİTERALI kimi ayrılır — interpolyasiya işləsin
            let baş = self.i;
            self.i += 1;
            while self.i < self.n && self.m[self.i] != q {
                if self.m[self.i] == '\\' {
                    self.i += 1;
                }
                self.i += 1;
            }
            if self.i >= self.n {
                self.xəta(
                    "Atribut dəyəri bağlanmayıb",
                    &format!("`{}=` dəyəri {} ilə bağlanmalıdır", ad, q),
                    &[],
                )?;
            }
            self.i += 1;
            return Ok(self.ifadə_oxu(baş, self.i));
        }
        if c == Some('{') {
            let baş = self.i + 1;
            let son = self.fiqurlu_sonu(self.i)?;
            let ifadə = self.ifadə_oxu(baş, son);
            self.i = son + 1;
            return Ok(ifadə);
        }
        self.xəta(
            &format!("`{}` atributunun dəyəri gözlənilirdi", ad),
            "dəyər `\"mətn\"` və ya `{ifadə}` formasında olur",
            &[],
        )
    }

    // ── Uşaqlar ───────────────────────────────────────────────────

    fn uşaqlar_oxu(&mut self, açan_ad: &str) -> N<Vec<JSXUşaq>> {
        let mut uşaqlar = vec![];
        let mut mətn_başı = self.i;
        loop {
            if self.i >= self.n {
                self.xəta(
                    &format!("`<{}>` bağlanmayıb", açan_ad),
                    "fayl bitdi",
                    &[&format!("`</{}>` əlavə edin", açan_ad)],
                )?;
            }
            let c = self.m[self.i];
            if c == '<' {
                // Mətn daxilində sadə `<` (məs. `5 < 10`)
                let növbəti = self.c(1);
                if !(matches!(növbəti, Some('/' | '>')) || Self::ad_başlanğıcı(növbəti)) {
                    self.i += 1;
                    continue;
                }
                self.mətni_əlavə(&mut uşaqlar, mətn_başı, self.i);
                if növbəti == Some('/') {
                    self.i += 2;
                    let bağlayan = if self.c(0) == Some('>') { String::new() } else { self.ad_oxu()? };
                    self.boşluq_atla();
                    if self.c(0) != Some('>') {
                        self.xəta("`>` gözlənilirdi", &format!("`</{}` bağlanmayıb", bağlayan), &[])?;
                    }
                    self.i += 1;
                    if bağlayan != açan_ad {
                        let uz = bağlayan.chars().count();
                        let yer = self.p.mənbə_yeri(self.i - uz - 3, uz + 3);
                        self.p.x.xəta(
                            "ALQ-P032",
                            "Bağlayan teq uyğun gəlmir",
                            Some(yer),
                            &format!("`<{}>` açılıb, `</{}>` bağlanıb", açan_ad, bağlayan),
                            &[&format!("düzgün forma: `</{}>`", açan_ad)],
                        );
                    }
                    return Ok(uşaqlar);
                }
                let e = self.element()?;
                uşaqlar.push(JSXUşaq::İfadə(e));
                mətn_başı = self.i;
                continue;
            }
            if c == '{' {
                self.mətni_əlavə(&mut uşaqlar, mətn_başı, self.i);
                let baş = self.i + 1;
                let son = self.fiqurlu_sonu(self.i)?;
                if !py_strip(&self.m[baş..son]).is_empty() {
                    let e = self.ifadə_oxu(baş, son);
                    uşaqlar.push(JSXUşaq::İfadə(e));
                }
                self.i = son + 1;
                mətn_başı = self.i;
                continue;
            }
            self.i += 1;
        }
    }

    fn mətni_əlavə(&self, uşaqlar: &mut Vec<JSXUşaq>, baş: usize, son: usize) {
        let xam = &self.m[baş..son];
        if xam.is_empty() {
            return;
        }
        let mətn = mətni_səliqəyə_sal(xam);
        if !mətn.is_empty() {
            uşaqlar.push(JSXUşaq::Mətn(mətn));
        }
    }

    // ── Mötərizə uyğunlaşdırma ────────────────────────────────────

    /// `{` mövqeyindən uyğun `}` indeksini tapır.
    fn fiqurlu_sonu(&mut self, açan: usize) -> N<usize> {
        let mut i = açan + 1;
        let mut dərinlik = 1;
        while i < self.n {
            let c = self.m[i];
            if matches!(c, '"' | '\'' | '`') {
                i = self.literalı_atla(i);
                continue;
            }
            if matches!(c, '(' | '[' | '{') {
                dərinlik += 1;
            } else if matches!(c, ')' | ']' | '}') {
                dərinlik -= 1;
                if dərinlik == 0 {
                    return Ok(i);
                }
            } else if c == '/' && i + 1 < self.n && self.m[i + 1] == '/' {
                while i < self.n && self.m[i] != '\n' {
                    i += 1;
                }
                continue;
            }
            i += 1;
        }
        self.i = açan;
        self.xəta(
            "`{` bağlanmayıb",
            "JSX daxilindəki ifadə `}` ilə bitməlidir",
            &["fiqurlu mötərizənin özü üçün mətn literalı işlədin"],
        )
    }

    fn literalı_atla(&self, mut i: usize) -> usize {
        let sitat = self.m[i];
        let üç = |j: usize| j + 3 <= self.m.len() && self.m[j..j + 3].iter().all(|c| *c == sitat);
        if üç(i) {
            let mut j = i + 3;
            while j + 3 <= self.m.len() {
                if üç(j) {
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

    // ── Daxili ifadənin ayrılması ─────────────────────────────────

    /// `[baş, son)` aralığındakı mətni ifadə kimi ayırır.
    fn ifadə_oxu(&mut self, baş: usize, son: usize) -> E {
        let mut tokenlər: Vec<Token> = vec![];
        {
            let mut lekser = Lekser::yeni(self.p.s.clone(), &mut *self.p.x);
            lekser.ascii_xəbərdarlığı = false;
            lekser.i = baş;
            let mut qoruyucu = 0;
            while lekser.i < son && qoruyucu < 100_000 {
                let köhnə = lekser.i;
                lekser.token_oxu(&mut tokenlər, true);
                if lekser.i == köhnə {
                    lekser.i += 1;
                }
                qoruyucu += 1;
            }
        }
        tokenlər.retain(|t| t.növ != Növ::SətirSonu);
        tokenlər.push(Token::yeni(Növ::FaylSonu, "", self.p.mənbə_yeri(son, 0)));
        let boş_yer = self.p.mənbə_yeri(baş, 0);
        let boş = || Rc::new(İfadə::Literal(boş_yer, LiteralD::Boş));
        if tokenlər.len() == 1 {
            return boş();
        }
        let s = self.p.s.clone();
        let mut alt = Parser::yeni(tokenlər, s, &mut *self.p.x);
        let nəticə = match alt.ifadə(0) {
            Ok(e) => e,
            Err(PX) => return boş(),
        };
        // Bütün tokenlər istifadə olunmalıdır
        let qalan = alt.bax(0).clone();
        if qalan.növ != Növ::FaylSonu {
            alt.xəta(
                "ALQ-P001",
                "Gözlənilməyən token",
                &format!("`{}` burada gözlənilmirdi", göstər(&qalan)),
                &["`{…}` daxilində tək ifadə olmalıdır"],
            );
        }
        nəticə
    }
}

/// JSX qaydası: yeni sətir ehtiva edən tam boşluq hissələri atılır.
fn mətni_səliqəyə_sal(xam: &[char]) -> String {
    if py_strip(xam).is_empty() {
        return if xam.contains(&'\n') { String::new() } else { " ".into() };
    }
    let sətirlər: Vec<&[char]> = xam.split(|c| *c == '\n').collect();
    if sətirlər.len() == 1 {
        return xam.iter().collect();
    }
    let mut hissələr: Vec<String> = vec![];
    for sətir in &sətirlər {
        // İlk sətir də tam kəsilir (Python: `strip() if strip() else ""`)
        let s = py_strip(sətir);
        if !s.is_empty() {
            hissələr.push(s.iter().collect());
        }
    }
    hissələr.join(" ")
}
