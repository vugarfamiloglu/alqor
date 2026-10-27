//! `verilənlər` — verilənlər bazası (modullar/verilenler.py), SQLite
//! (`rusqlite`, paketlə qurulan SQLite).
//!
//! Python ilə eyni API: `bağlan`, `icra`, `sorğu`, `birSətir`,
//! `birDəyər`, `skript`, `tranzaksiya` (iç-içə — SAVEPOINT), sorğu
//! qurucusu (`cədvəl(…).harada(…).al()`), `miqrasiyaEt`. PostgreSQL /
//! MySQL və ORM (`verilənlər.Model`) hələ yalnız Python icraçısındadır.

use super::deyerler::*;
use super::elave::*;
use super::icraci::İcraçı;
use rusqlite::types::{Value, ValueRef};
use std::cell::{Cell, RefCell};
use std::path::{Path, PathBuf};
use std::rc::Rc;

fn x_(m: impl Into<String>) -> Siqnal {
    xəta("VerilənlərXətası", m, "ALQ-R013")
}

enum SX {
    Məhdudiyyət(String),
    Sürücü(String),
}

fn sx(e: rusqlite::Error) -> SX {
    match &e {
        rusqlite::Error::SqliteFailure(f, m) => {
            let msg = m.clone().unwrap_or_else(|| f.to_string());
            if f.code == rusqlite::ErrorCode::ConstraintViolation {
                SX::Məhdudiyyət(msg)
            } else {
                SX::Sürücü(msg)
            }
        }
        rusqlite::Error::SqlInputError { error, msg, .. } => {
            if error.code == rusqlite::ErrorCode::ConstraintViolation {
                SX::Məhdudiyyət(msg.clone())
            } else {
                SX::Sürücü(msg.clone())
            }
        }
        rusqlite::Error::MultipleStatement => SX::Sürücü("You can only execute one statement at a time.".into()),
        rusqlite::Error::InvalidParameterCount(s, g) => SX::Sürücü(format!(
            "Incorrect number of bindings supplied. The current statement uses {}, and there are {} supplied.",
            g, s
        )),
        x => SX::Sürücü(x.to_string()),
    }
}

#[derive(Default)]
struct Nəticə_ {
    sütunlar: Vec<String>,
    sətirlər: Vec<Vec<D>>,
    say: i64,
    son_id: Option<i64>,
}

impl Nəticə_ {
    fn lüğətlər(&self) -> Vec<D> {
        self.sətirlər.iter().map(|s| lüğət_s(self.sütunlar.iter().cloned().zip(s.iter().cloned()).collect())).collect()
    }
}

/// `$1` → `?1`; mətn literalları toxunulmur
fn dollar(sql: &str) -> String {
    let c: Vec<char> = sql.chars().collect();
    let mut n = String::new();
    let mut i = 0;
    while i < c.len() {
        let x = c[i];
        if x == '\'' || x == '"' {
            let mut j = i + 1;
            loop {
                match c[j.min(c.len())..].iter().position(|y| *y == x) {
                    Some(k) => {
                        j += k;
                        if j + 1 < c.len() && c[j + 1] == x {
                            j += 2;
                            continue;
                        }
                        break;
                    }
                    None => {
                        j = c.len() - 1;
                        break;
                    }
                }
            }
            n.extend(&c[i..=j.min(c.len() - 1)]);
            i = j + 1;
            continue;
        }
        if x == '$' && i + 1 < c.len() && c[i + 1].is_ascii_digit() {
            let mut j = i + 1;
            while j < c.len() && c[j].is_ascii_digit() {
                j += 1;
            }
            n.push('?');
            n.extend(&c[i + 1..j]);
            i = j;
            continue;
        }
        n.push(x);
        i += 1;
    }
    n
}

fn dəyər(d: &D) -> Nəticə<Value> {
    Ok(match d {
        D::Boş => Value::Null,
        D::M(b) => Value::Integer(*b as i64),
        D::T(i) => Value::Integer(*i),
        D::BT(_) => return Err(xəta("DaşmaXətası", "Python int too large to convert to SQLite INTEGER", "ALQ-R001")),
        D::O(f) => Value::Real(*f),
        D::S(s) => Value::Text(s.to_string()),
        D::Bayt(b) => Value::Blob(b.to_vec()),
        x => {
            return Err(x_(format!(
                "`{}` bazaya yazıla bilmir — mətn, ədəd, məntiq, bayt və ya boş olmalıdır",
                tip_adı(x)
            )))
        }
    })
}

fn sütun_d(v: ValueRef) -> D {
    match v {
        ValueRef::Null => D::Boş,
        ValueRef::Integer(i) => D::T(i),
        ValueRef::Real(f) => D::O(f),
        ValueRef::Text(t) => D::str(String::from_utf8_lossy(t).to_string()),
        ValueRef::Blob(b) => D::Bayt(Rc::new(b.to_vec())),
    }
}

/// Birinci `;`-dən sonra (mətn/şərh xaricində) başqa cümlə varmı?
fn birdən_çox(sql: &str) -> bool {
    let c: Vec<char> = sql.chars().collect();
    let mut i = 0;
    let boşluq_şərh = |mut i: usize| -> usize {
        loop {
            while i < c.len() && c[i].is_whitespace() {
                i += 1;
            }
            if i + 1 < c.len() && c[i] == '-' && c[i + 1] == '-' {
                while i < c.len() && c[i] != '\n' {
                    i += 1;
                }
            } else if i + 1 < c.len() && c[i] == '/' && c[i + 1] == '*' {
                i += 2;
                while i + 1 < c.len() && !(c[i] == '*' && c[i + 1] == '/') {
                    i += 1;
                }
                i = (i + 2).min(c.len());
            } else {
                return i;
            }
        }
    };
    let tetik = sql.to_lowercase().contains("trigger");
    while i < c.len() {
        match c[i] {
            q @ ('\'' | '"' | '`') => {
                i += 1;
                while i < c.len() {
                    if c[i] == q {
                        if i + 1 < c.len() && c[i + 1] == q {
                            i += 2;
                            continue;
                        }
                        break;
                    }
                    i += 1;
                }
                i += 1;
            }
            '[' => {
                while i < c.len() && c[i] != ']' {
                    i += 1;
                }
                i += 1;
            }
            '-' | '/' => {
                let j = boşluq_şərh(i);
                i = if j == i { i + 1 } else { j };
            }
            ';' => {
                if tetik {
                    return false;
                }
                let mut j = i + 1;
                loop {
                    let k = boşluq_şərh(j);
                    if k < c.len() && c[k] == ';' {
                        j = k + 1;
                        continue;
                    }
                    return k < c.len();
                }
            }
            _ => i += 1,
        }
    }
    false
}

/// Python sqlite3: `rowcount` yalnız DML üçün
fn dml(sql: &str) -> bool {
    let s = sql.trim_start().to_lowercase();
    ["insert", "update", "delete", "replace"].iter().any(|k| s.starts_with(k))
}

fn ad_doğrudur(h: &str) -> bool {
    let mut c = h.chars();
    match c.next() {
        Some(x) if (x.is_alphabetic() || x == '_') => c.all(|y| y.is_alphanumeric() || y == '_'),
        _ => false,
    }
}

fn ad_(x: &D, nə: &str) -> Nəticə<String> {
    if let D::S(s) = x {
        if s.split('.').all(ad_doğrudur) {
            return Ok(s.split('.').map(|h| format!("\"{}\"", h)).collect::<Vec<_>>().join("."));
        }
    }
    Err(x_(format!("yanlış {} adı: {}", nə, py_repr(x))))
}

/// Ünvanda parol `***` ilə əvəzlənir
pub fn gizli_ünvan(u: &str) -> String {
    let a = super::mod_http::urlsplit(u);
    let Some((istifadəçi, _)) = a.netloc.rsplit_once('@') else { return u.to_string() };
    let Some((_, parol)) = istifadəçi.split_once(':') else { return u.to_string() };
    let n = a.netloc.replacen(&format!(":{}@", parol), ":***@", 1);
    u.replacen(&a.netloc, &n, 1)
}

// ═══════════════════════════════════════════════════════════════════════
//  Bağlantı
// ═══════════════════════════════════════════════════════════════════════

pub struct Bağlantı {
    ünvan: String,
    c: RefCell<Option<rusqlite::Connection>>,
    tranzaksiyada: Cell<usize>,
    son_id: Cell<Option<i64>>,
}

impl Bağlantı {
    fn icra_xam(&self, sql: &str, p: &[Value]) -> Result<Nəticə_, SX> {
        let c = self.c.borrow();
        let c = c.as_ref().unwrap();
        let sql_ = dollar(sql);
        if birdən_çox(&sql_) {
            return Err(SX::Sürücü("You can only execute one statement at a time.".into()));
        }
        let mut st = c.prepare(&sql_).map_err(sx)?;
        let gözlənilən = st.parameter_count();
        if gözlənilən != p.len() {
            return Err(SX::Sürücü(format!(
                "Incorrect number of bindings supplied. The current statement uses {}, and there are {} supplied.",
                gözlənilən,
                p.len()
            )));
        }
        let sütunlar: Vec<String> = st.column_names().iter().map(|s| s.to_string()).collect();
        let n_sütun = sütunlar.len();
        let mut n = Nəticə_ { say: -1, ..Default::default() };
        let mut sətirlər = st.query(rusqlite::params_from_iter(p.iter())).map_err(sx)?;
        let mut hamısı = vec![];
        while let Some(r) = sətirlər.next().map_err(sx)? {
            hamısı.push((0..n_sütun).map(|k| sütun_d(r.get_ref(k).unwrap())).collect());
        }
        drop(sətirlər);
        if dml(sql) {
            n.say = c.changes() as i64;
        }
        let id = c.last_insert_rowid();
        n.son_id = if id != 0 { Some(id) } else { None };
        if n_sütun > 0 {
            n.sütunlar = sütunlar;
            n.sətirlər = hamısı;
        }
        Ok(n)
    }

    fn icra(&self, sql: &D, p: &[D]) -> Nəticə<Nəticə_> {
        if self.c.borrow().is_none() {
            return Err(x_("bağlantı bağlanıb"));
        }
        let D::S(sql) = sql else { return Err(xəta("TipXətası", "SQL mətn olmalıdır", "ALQ-T001")) };
        let mut v = vec![];
        for x in p {
            v.push(dəyər(x)?);
        }
        match self.icra_xam(sql, &v) {
            Ok(n) => {
                if let Some(i) = n.son_id {
                    self.son_id.set(Some(i));
                }
                Ok(n)
            }
            Err(SX::Məhdudiyyət(m)) => Err(xəta("MəhdudiyyətXətası", format!("məhdudiyyət pozuldu: {}", m), "ALQ-R013")),
            Err(SX::Sürücü(m)) => {
                let k: String = sql.trim().chars().take(200).collect();
                Err(x_(format!("{} — SQL: {}", m, k)))
            }
        }
    }

    fn əmr(&self, sql: &str) -> Nəticə<()> {
        self.icra(&D::s(sql), &[]).map(|_| ())
    }

    fn skript(&self, sql: &str) -> Result<(), SX> {
        let c = self.c.borrow();
        let c = c.as_ref().unwrap();
        if !c.is_autocommit() {
            let _ = c.execute_batch("COMMIT");
        }
        c.execute_batch(sql).map_err(sx)
    }

    fn tranzaksiya(&self, f: &mut dyn FnMut() -> Nəticə) -> Nəticə {
        let iç = self.tranzaksiyada.get() > 0;
        let ad_ = format!("alqor_{}", self.tranzaksiyada.get());
        self.əmr(&if iç { format!("SAVEPOINT {}", ad_) } else { "BEGIN".into() })?;
        self.tranzaksiyada.set(self.tranzaksiyada.get() + 1);
        match f() {
            Ok(n) => {
                self.tranzaksiyada.set(self.tranzaksiyada.get() - 1);
                self.əmr(&if iç { format!("RELEASE SAVEPOINT {}", ad_) } else { "COMMIT".into() })?;
                Ok(n)
            }
            Err(e) => {
                self.tranzaksiyada.set(self.tranzaksiyada.get() - 1);
                let _ = self.əmr(&if iç { format!("ROLLBACK TO SAVEPOINT {}", ad_) } else { "ROLLBACK".into() });
                if iç {
                    let _ = self.əmr(&format!("RELEASE SAVEPOINT {}", ad_));
                }
                Err(e)
            }
        }
    }

    fn miqrasiya(&self, qovluq: &str) -> Nəticə {
        let q = PathBuf::from(qovluq);
        if !q.is_dir() {
            return Err(xəta("FaylTapılmadıXətası", format!("\"{}\" qovluğu tapılmadı", qovluq), "ALQ-R009"));
        }
        self.əmr("CREATE TABLE IF NOT EXISTS _alqor_miqrasiyalar (ad TEXT PRIMARY KEY, vaxt TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")?;
        let olan: Vec<String> = self
            .icra(&D::s("SELECT ad FROM _alqor_miqrasiyalar"), &[])?
            .sətirlər
            .iter()
            .map(|s| py_s(&s[0]))
            .collect();
        let mut fayllar: Vec<PathBuf> = std::fs::read_dir(&q)
            .map(|d| d.flatten().map(|e| e.path()).filter(|p| p.extension().map(|e| e == "sql").unwrap_or(false)).collect())
            .unwrap_or_default();
        fayllar.sort();
        let mut tətbiq = vec![];
        for f in fayllar {
            let ad_ = f.file_name().map(|x| x.to_string_lossy().to_string()).unwrap_or_default();
            if olan.contains(&ad_) {
                continue;
            }
            if !ad_.chars().all(|c| c.is_alphanumeric() || "_.-".contains(c)) || ad_.is_empty() {
                return Err(x_(format!("miqrasiya faylının adı yanlışdır: {}", ad_)));
            }
            let sql = std::fs::read_to_string(&f).map_err(|e| xəta("GirişÇıxışXətası", e.to_string(), "ALQ-R009"))?;
            let sql = sql.trim().trim_end_matches(';');
            let skript = format!("BEGIN;\n{};\nINSERT INTO _alqor_miqrasiyalar (ad) VALUES ('{}');\nCOMMIT;", sql, ad_);
            if let Err(e) = self.skript(&skript) {
                let _ = self.icra_xam("ROLLBACK", &[]);
                let m = match e {
                    SX::Məhdudiyyət(m) | SX::Sürücü(m) => m,
                };
                return Err(x_(format!("miqrasiya {}: {}", ad_, m)));
            }
            tətbiq.push(D::str(ad_));
        }
        Ok(D::siyahı(tətbiq))
    }
}

fn parametrlər(a: &[D]) -> Vec<D> {
    a[1..].to_vec()
}

fn bağlantı_d(b: Rc<Bağlantı>) -> D {
    obyekt("bağlantı", b, |b| format!("<bağlantı {}>", gizli_ünvan(&b.ünvan)), |_, v| {
        vec![
            ("sorğu", metod(v, "sorğu", 1, None, |_, b, a, _| Ok(D::siyahı(b.icra(&a[0], &parametrlər(&a))?.lüğətlər())))),
            ("birSətir", metod(v, "birSətir", 1, None, |_, b, a, _| {
                Ok(b.icra(&a[0], &parametrlər(&a))?.lüğətlər().into_iter().next().unwrap_or(D::Boş))
            })),
            ("birDəyər", metod(v, "birDəyər", 1, None, |_, b, a, _| {
                Ok(b.icra(&a[0], &parametrlər(&a))?.sətirlər.first().and_then(|s| s.first().cloned()).unwrap_or(D::Boş))
            })),
            ("icra", metod(v, "icra", 1, None, |_, b, a, _| Ok(D::T(b.icra(&a[0], &parametrlər(&a))?.say)))),
            ("skript", metod(v, "skript", 1, Some(1), |_, b, a, _| {
                if b.c.borrow().is_none() {
                    return Err(x_("bağlantı bağlanıb"));
                }
                match b.skript(&py_s(&a[0])) {
                    Ok(()) => Ok(D::Boş),
                    Err(SX::Məhdudiyyət(m)) => Err(xəta("MəhdudiyyətXətası", format!("məhdudiyyət pozuldu: {}", m), "ALQ-R013")),
                    Err(SX::Sürücü(m)) => Err(x_(m)),
                }
            })),
            ("sonId", metod(v, "sonId", 0, Some(0), |_, b, _, _| Ok(b.son_id.get().map(D::T).unwrap_or(D::Boş)))),
            ("tranzaksiya", metod(v, "tranzaksiya", 1, Some(1), |i, b, a, _| {
                let bd = bağlantı_d_paylaşılan(b);
                let f = a[0].clone();
                b.tranzaksiya(&mut || çağır(i, &f, vec![bd.clone()]))
            })),
            ("cədvəl", metod(v, "cədvəl", 1, Some(1), |_, b, a, _| {
                Ok(qurucu_d(Rc::new(QurucuV {
                    b: b.clone(),
                    cədvəl: ad_(&a[0], "cədvəl")?,
                    sütunlar: "*".into(),
                    şərtlər: vec![],
                    sıra: vec![],
                    limit: None,
                    atla: None,
                })))
            })),
            ("cədvəllər", metod(v, "cədvəllər", 0, Some(0), |_, b, _, _| {
                let n = b.icra(&D::s("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"), &[])?;
                Ok(D::siyahı(n.sətirlər.into_iter().map(|mut s| s.remove(0)).collect()))
            })),
            ("sütunlar", metod(v, "sütunlar", 1, Some(1), |_, b, a, _| {
                let c = ad_(&a[0], "cədvəl")?;
                let n = b.icra(&D::str(format!("PRAGMA table_info({})", c)), &[])?;
                let mut r = vec![];
                for s in n.lüğətlər() {
                    let g = |k: &str| l_al(&s, k).unwrap_or(D::Boş);
                    r.push(lüğət(vec![
                        ("ad", g("name")),
                        ("tip", g("type")),
                        ("boşOlaBilər", D::M(!doğrudur(&g("notnull")))),
                        ("açar", D::M(doğrudur(&g("pk")))),
                    ]));
                }
                Ok(D::siyahı(r))
            })),
            ("miqrasiyaEt", metod(v, "miqrasiyaEt", 1, Some(1), |_, b, a, _| b.miqrasiya(&py_s(&a[0])))),
            ("bağla", metod(v, "bağla", 0, Some(0), |_, b, _, _| {
                b.c.borrow_mut().take();
                Ok(D::Boş)
            })),
        ]
    })
}

thread_local! {
    static OBYEKTLƏR: RefCell<Vec<(std::rc::Weak<Bağlantı>, std::rc::Weak<Obyekt>)>> = RefCell::new(vec![]);
}

/// Eyni bağlantının Alqor obyekti (tranzaksiya funksiyasına ötürülür)
fn bağlantı_d_paylaşılan(b: &Rc<Bağlantı>) -> D {
    let tapılan = OBYEKTLƏR.with(|o| {
        o.borrow().iter().find(|(x, _)| x.upgrade().map(|x| Rc::ptr_eq(&x, b)).unwrap_or(false)).and_then(|(_, ob)| ob.upgrade())
    });
    match tapılan {
        Some(o) => D::Obyekt(o),
        None => bağlantı_d(b.clone()),
    }
}

// ── Sorğu qurucusu ─────────────────────────────────────────────────────

#[derive(Clone)]
struct QurucuV {
    b: Rc<Bağlantı>,
    cədvəl: String,
    sütunlar: String,
    şərtlər: Vec<(String, String, Vec<D>)>,
    sıra: Vec<String>,
    limit: Option<i64>,
    atla: Option<i64>,
}

const OPERATORLAR: &[&str] = &["=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "NOT LIKE", "IN", "NOT IN", "IS", "IS NOT", "bənzər", "içində"];

impl QurucuV {
    fn harada(&self, sütun: &D, op: &D, d: &D, bağ: &str) -> Nəticə<QurucuV> {
        let mut n = self.clone();
        let o = py_s(op);
        let o = if o.is_ascii() { o.to_uppercase() } else { o };
        let o = match o.as_str() {
            "BƏNZƏR" | "bənzər" => "LIKE".to_string(),
            "içində" | "İÇİNDƏ" => "IN".to_string(),
            _ => o,
        };
        if !OPERATORLAR.contains(&o.as_str()) {
            return Err(x_(format!("operator tanınmır: {} — =, !=, <, <=, >, >=, LIKE, IN, IS", py_repr(op))));
        }
        let s = ad_(sütun, "sütun")?;
        let (parça, p) = if o == "IN" || o == "NOT IN" {
            let siyahı = match d {
                D::Siyahı(l) => l.borrow().clone(),
                D::Kortej(k) => k.to_vec(),
                D::Dəst(x) => dəst_sırası(&x.borrow()),
                x => vec![x.clone()],
            };
            if siyahı.is_empty() {
                ((if o == "IN" { "0 = 1" } else { "1 = 1" }).to_string(), vec![])
            } else {
                (format!("{} {} ({})", s, o, vec!["?"; siyahı.len()].join(", ")), siyahı)
            }
        } else if d.boşdur() && (o == "=" || o == "IS") {
            (format!("{} IS NULL", s), vec![])
        } else if d.boşdur() && (o == "!=" || o == "<>" || o == "IS NOT") {
            (format!("{} IS NOT NULL", s), vec![])
        } else {
            for x in [d] {
                dəyər(x)?;
            }
            (format!("{} {} ?", s, o), vec![d.clone()])
        };
        for x in &p {
            dəyər(x)?;
        }
        n.şərtlər.push((bağ.into(), parça, p));
        Ok(n)
    }
    fn harada_sql(&self) -> (String, Vec<D>) {
        if self.şərtlər.is_empty() {
            return (String::new(), vec![]);
        }
        let mut h = vec![];
        let mut p = vec![];
        for (k, (bağ, parça, x)) in self.şərtlər.iter().enumerate() {
            h.push(if k == 0 { parça.clone() } else { format!("{} {}", bağ, parça) });
            p.extend(x.iter().cloned());
        }
        (format!(" WHERE {}", h.join(" ")), p)
    }
    fn sql(&self) -> (String, Vec<D>) {
        let (h, p) = self.harada_sql();
        let mut s = format!("SELECT {} FROM {}{}", self.sütunlar, self.cədvəl, h);
        if !self.sıra.is_empty() {
            s += &format!(" ORDER BY {}", self.sıra.join(", "));
        }
        if self.limit.is_some() || self.atla.is_some() {
            s += &format!(" LIMIT {}", self.limit.unwrap_or(-1));
            if let Some(a) = self.atla {
                s += &format!(" OFFSET {}", a);
            }
        }
        (s, p)
    }
    fn al(&self) -> Nəticə<Vec<D>> {
        let (s, p) = self.sql();
        Ok(self.b.icra(&D::str(s), &p)?.lüğətlər())
    }
    fn əlavə_et(&self, i: &İcraçı, l: &D) -> Nəticə {
        let l = match l {
            D::Nümunə(_) => D::lüğət(cütlər(l).unwrap().into_iter().map(|(a, d)| (Açar(a), d)).collect()),
            x => x.clone(),
        };
        if let D::Siyahı(s) = &l {
            let el = s.borrow().clone();
            if el.is_empty() {
                return Ok(D::Boş);
            }
            let öz = self.clone();
            return self.b.tranzaksiya(&mut || {
                let mut son = D::Boş;
                for x in &el {
                    son = öz.əlavə_et(i, x)?;
                }
                Ok(son)
            });
        }
        let c = match &l {
            D::Lüğət(_) => cütlər(&l).unwrap(),
            _ => vec![],
        };
        if c.is_empty() {
            return Err(x_("`əlavəEt` boş olmayan lüğət gözləyir"));
        }
        let mut adlar = vec![];
        for (a, _) in &c {
            adlar.push(ad_(a, "sütun")?);
        }
        let sql = format!("INSERT INTO {} ({}) VALUES ({})", self.cədvəl, adlar.join(", "), vec!["?"; c.len()].join(", "));
        let v: Vec<D> = c.into_iter().map(|(_, d)| d).collect();
        Ok(self.b.icra(&D::str(sql), &v)?.son_id.map(D::T).unwrap_or(D::Boş))
    }
}

fn qurucu_d(q: Rc<QurucuV>) -> D {
    obyekt("sorğuQurucusu", q, |q| format!("<sorğuQurucusu {}>", q.cədvəl), |_, v| {
        let h = |ad_: &'static str, bağ: &'static str| {
            metod(v, ad_, 2, Some(3), move |_, q, a, _| {
                Ok(qurucu_d(Rc::new(q.harada(&a[0], &a[1], &a.get(2).cloned().unwrap_or(D::Boş), bağ)?)))
            })
        };
        vec![
            ("seç", metod(v, "seç", 0, None, |_, q, a, _| {
                let mut n = (**q).clone();
                let mut h = vec![];
                for x in &a {
                    h.push(ad_(x, "sütun")?);
                }
                n.sütunlar = if h.is_empty() { "*".into() } else { h.join(", ") };
                Ok(qurucu_d(Rc::new(n)))
            })),
            ("harada", h("harada", "AND")),
            ("vəHarada", h("vəHarada", "AND")),
            ("yaHarada", h("yaHarada", "OR")),
            ("sırala", metod(v, "sırala", 1, Some(2), |_, q, a, _| {
                let mut n = (**q).clone();
                let i = match a.get(1).map(py_s).unwrap_or("artan".into()).to_lowercase().as_str() {
                    "artan" | "asc" => "ASC",
                    "azalan" | "desc" => "DESC",
                    _ => return Err(x_("istiqamət `artan` və ya `azalan` olmalıdır")),
                };
                n.sıra.push(format!("{} {}", ad_(&a[0], "sütun")?, i));
                Ok(qurucu_d(Rc::new(n)))
            })),
            ("limit", metod(v, "limit", 1, Some(1), |_, q, a, _| {
                let mut n = (**q).clone();
                n.limit = Some(py_int(&a[0], "limit")?);
                Ok(qurucu_d(Rc::new(n)))
            })),
            ("atla", metod(v, "atla", 1, Some(1), |_, q, a, _| {
                let mut n = (**q).clone();
                n.atla = Some(py_int(&a[0], "atla")?);
                Ok(qurucu_d(Rc::new(n)))
            })),
            ("al", metod(v, "al", 0, Some(0), |_, q, _, _| Ok(D::siyahı(q.al()?)))),
            ("ilk", metod(v, "ilk", 0, Some(0), |_, q, _, _| {
                let mut n = (**q).clone();
                n.limit = Some(1);
                Ok(n.al()?.into_iter().next().unwrap_or(D::Boş))
            })),
            ("say", metod(v, "say", 0, Some(0), |_, q, _, _| {
                let (h, p) = q.harada_sql();
                let n = q.b.icra(&D::str(format!("SELECT COUNT(*) FROM {}{}", q.cədvəl, h)), &p)?;
                Ok(n.sətirlər[0][0].clone())
            })),
            ("əlavəEt", metod(v, "əlavəEt", 1, Some(1), |i, q, a, _| q.əlavə_et(i, &a[0]))),
            ("yenilə", metod(v, "yenilə", 1, Some(1), |_, q, a, _| {
                let c = match &a[0] {
                    D::Lüğət(_) => cütlər(&a[0]).unwrap(),
                    _ => vec![],
                };
                if c.is_empty() {
                    return Err(x_("`yenilə` boş olmayan lüğət gözləyir"));
                }
                if q.şərtlər.is_empty() {
                    return Err(x_("`yenilə` şərtsiz bütün sətirləri dəyişərdi — `harada(…)` əlavə edin"));
                }
                let (h, p) = q.harada_sql();
                let mut t = vec![];
                for (a, _) in &c {
                    t.push(format!("{} = ?", ad_(a, "sütun")?));
                }
                let mut v: Vec<D> = c.into_iter().map(|(_, d)| d).collect();
                v.extend(p);
                Ok(D::T(q.b.icra(&D::str(format!("UPDATE {} SET {}{}", q.cədvəl, t.join(", "), h)), &v)?.say))
            })),
            ("sil", metod(v, "sil", 0, Some(0), |_, q, _, _| {
                if q.şərtlər.is_empty() {
                    return Err(x_("`sil` şərtsiz bütün cədvəli silərdi — `harada(…)` əlavə edin"));
                }
                let (h, p) = q.harada_sql();
                Ok(D::T(q.b.icra(&D::str(format!("DELETE FROM {}{}", q.cədvəl, h)), &p)?.say))
            })),
            ("sql", metod(v, "sql", 0, Some(0), |_, q, _, _| Ok(D::str(q.sql().0)))),
        ]
    })
}

fn sqlite_aç(ünvan: &str, yol: &str) -> Nəticə {
    let c = if yol == ":memory:" { rusqlite::Connection::open_in_memory() } else { rusqlite::Connection::open(yol) };
    let c = c.map_err(|e| {
        let m = match sx(e) {
            SX::Məhdudiyyət(m) | SX::Sürücü(m) => m,
        };
        x_(format!("{}: bağlantı alınmadı — {}", ünvan, m))
    })?;
    let _ = c.execute_batch("PRAGMA foreign_keys = ON");
    let b = Rc::new(Bağlantı { ünvan: ünvan.into(), c: RefCell::new(Some(c)), tranzaksiyada: Cell::new(0), son_id: Cell::new(None) });
    let d = bağlantı_d(b.clone());
    if let D::Obyekt(o) = &d {
        OBYEKTLƏR.with(|x| {
            let mut x = x.borrow_mut();
            x.retain(|(a, _)| a.strong_count() > 0);
            x.push((Rc::downgrade(&b), Rc::downgrade(o)));
        });
    }
    Ok(d)
}

fn bağlan(ü: &D) -> Nəticə {
    let D::S(ünvan) = ü else { return Err(xəta("TipXətası", "bağlantı ünvanı mətn olmalıdır", "ALQ-T001")) };
    let ünvan: &str = ünvan;
    if ["sqlite::yaddaş:", "sqlite::memory:", ":yaddaş:"].contains(&ünvan) {
        return sqlite_aç(ünvan, ":memory:");
    }
    if let Some(yol) = ünvan.strip_prefix("sqlite://") {
        if yol.is_empty() {
            return Err(x_("sqlite yolu boşdur: sqlite://./ad.db"));
        }
        if let Some(q) = Path::new(yol).parent() {
            if !q.as_os_str().is_empty() {
                let _ = std::fs::create_dir_all(q);
            }
        }
        return sqlite_aç(ünvan, yol);
    }
    if (ünvan.ends_with(".db") || ünvan.ends_with(".sqlite") || ünvan.ends_with(".sqlite3")) && !ünvan.contains("://") {
        return sqlite_aç(ünvan, ünvan);
    }
    let sxem = ünvan.split("://").next().filter(|_| ünvan.contains("://")).unwrap_or("");
    if ["postgres", "postgresql", "mysql", "mariadb"].contains(&sxem) {
        return Err(xəta(
            "BağlantıXətası",
            format!("{}: {} sürücüsü Rust icraçısında hələ yoxdur — `alqor işlət --motor py` işlədin", gizli_ünvan(ünvan), sxem),
            "ALQ-R013",
        ));
    }
    Err(x_(format!(
        "bağlantı ünvanı tanınmadı: {} (sqlite://yol.db, postgres://…, mysql://…)",
        str_repr(&gizli_ünvan(ünvan))
    )))
}

pub fn qur() -> Rc<Modul> {
    Modul::yeni("verilənlər", vec![
        ("bağlan", f("bağlan", 1, Some(1), |_, a, _| bağlan(&a[0]))),
        ("Model", f("Model", 0, None, |_, _, _| {
            Err(xəta("ArqumentXətası", "`verilənlər.Model` (ORM) Rust icraçısında hələ yoxdur — `alqor işlət --motor py` işlədin", "ALQ-M002"))
        })),
    ])
}
