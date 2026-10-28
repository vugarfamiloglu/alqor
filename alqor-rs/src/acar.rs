//! Açar sözlər (acar_sozler.py).

use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

const ELAN: &[&str] = &["dəyişən", "sabit", "dəyişməz", "funksiya", "sinif", "struktur",
    "interfeys", "sadalama", "modul", "obyekt", "qarışıq", "tip", "qurucu", "silinsin",
    "metod", "xassə", "genişlət", "komponent", "mağaza"];
const MODIFIKATOR: &[&str] = &["açıq", "gizli", "qorunan", "statik", "mücərrəd", "son",
    "tənbəl", "global", "asinxron", "generator"];
const SERT: &[&str] = &["əgər", "onda", "yoxsa", "əks", "halda", "varsa", "yoxdursa", "seç",
    "hal", "digər", "hallarda", "keç"];
const DOVR: &[&str] = &["nə", "qədər", "ki", "həmişə", "təkrarla", "dəfə", "hər", "üçün",
    "içində", "addım", "dayan", "davam", "et"];
const AXIN: &[&str] = &["qaytar", "ver", "gözlə", "gecikdir", "istifadə", "blok"];
const XETA: &[&str] = &["cəhd", "tut", "nəhayət", "at", "iddia", "təmin", "bərpa"];
const OBYEKT: &[&str] = &["özü", "üst", "yeni", "miras", "tətbiq", "ilə", "əvəz"];
const MODUL: &[&str] = &["gətir", "ixrac", "kimi", "standart"];
const MENTIQ: &[&str] = &["və", "ya", "deyil", "içindədir", "tipidir", "boşdur"];
const LITERAL: &[&str] = &["doğru", "yanlış", "boş", "sonsuz", "ƏdədDeyil"];
const KOMEKCI: &[&str] = &["dayanNöqtəsi"];

pub const TIP_ADLARI: &[&str] = &["tam", "onluq", "mətn", "məntiq", "simvol", "bayt", "siyahı",
    "lüğət", "dəst", "kortej", "funksiyaTipi", "istənilən", "heç"];

pub const COX_SOZLU: &[&[&str]] = &[
    &["nə", "qədər", "ki"], &["digər", "hallarda"], &["yoxsa", "əgər"], &["əks", "halda"],
    &["davam", "et"], &["cəhd", "et"], &["ixrac", "et"], &["əvəz", "et"], &["və", "ya"],
    &["boş", "deyil"],
];

pub const DAVAM_ACAR: &[&str] = &["və", "və ya", "deyil", "kimi", "tipidir", "içindədir",
    "yeni", "gətir", "at", "ver", "gözlə", "iddia", "miras", "tətbiq", "ilə", "üçün", "addım",
    "onda", "hal"];

pub const BLOK_ACANLAR: &[&str] = &["funksiya", "metod", "silinsin", "blok", "sinif",
    "struktur", "interfeys", "sadalama", "modul", "obyekt", "qarışıq", "komponent", "mağaza",
    "genişlət", "əgər", "varsa", "yoxdursa", "seç", "nə qədər ki", "həmişə", "təkrarla", "hər",
    "cəhd et", "təmin", "istifadə"];

pub const EHTIYAT: &[&str] = &["aktyor", "ömür", "təsir"];

pub struct Cədvəl {
    pub acarlar: HashSet<&'static str>,
    pub ascii: HashMap<String, &'static str>,
}

pub fn cədvəl() -> &'static Cədvəl {
    static C: OnceLock<Cədvəl> = OnceLock::new();
    C.get_or_init(|| {
        let mut acarlar = HashSet::new();
        for q in [ELAN, MODIFIKATOR, SERT, DOVR, AXIN, XETA, OBYEKT, MODUL, MENTIQ, LITERAL, KOMEKCI] {
            for s in q {
                acarlar.insert(*s);
            }
        }
        let mut ascii = HashMap::new();
        for s in acarlar.iter() {
            let a = crate::elifba::latınla(s);
            if a != *s {
                ascii.insert(a, *s);
            }
        }
        Cədvəl { acarlar, ascii }
    })
}

/// (kanonik forma, ascii idi)
pub fn kanonikləşdir(söz: &str) -> Option<(&'static str, bool)> {
    let c = cədvəl();
    if let Some(s) = c.acarlar.get(söz) {
        return Some((s, false));
    }
    c.ascii.get(söz).map(|s| (*s, true))
}

pub fn tamamla(k: &str) -> String {
    match k {
        "davam" => "davam et".into(),
        "əks halda" => "yoxsa".into(),
        _ => k.into(),
    }
}
