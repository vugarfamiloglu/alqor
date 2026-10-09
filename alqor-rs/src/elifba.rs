//! Azərbaycan əlifbası: hərf sinifləri, böyük/kiçik, sıralama (elifba.py).

pub const KICIK: &str = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz";
pub const BOYUK: &str = "ABCÇDEƏFGĞHXIİJKQLMNOÖPRSŞTUÜVYZ";

pub fn kiçik_mövqe(c: char) -> Option<usize> {
    KICIK.chars().position(|x| x == c)
}
pub fn böyük_mövqe(c: char) -> Option<usize> {
    BOYUK.chars().position(|x| x == c)
}
pub fn hərfdir(c: char) -> bool {
    kiçik_mövqe(c).is_some() || böyük_mövqe(c).is_some()
}
pub fn rəqəmdir(c: char) -> bool {
    c.is_ascii_digit()
}
pub fn ad_başlanğıcı(c: char) -> bool {
    hərfdir(c) || c == '_'
}
pub fn ad_davamı(c: char) -> bool {
    hərfdir(c) || rəqəmdir(c) || c == '_'
}
pub fn saitdir(c: char) -> bool {
    "aeəıioöuüAEƏIİOÖUÜ".contains(c)
}
pub fn qalın(c: char) -> bool {
    "aıouAIOU".contains(c)
}
pub fn incə(c: char) -> bool {
    "eəiöüEƏİÖÜ".contains(c)
}

pub fn böyüyə(s: &str) -> String {
    let b: Vec<char> = BOYUK.chars().collect();
    s.chars()
        .flat_map(|c| match kiçik_mövqe(c) {
            Some(i) => vec![b[i]],
            None => c.to_uppercase().collect(),
        })
        .collect()
}
pub fn kiçiyə(s: &str) -> String {
    let k: Vec<char> = KICIK.chars().collect();
    s.chars()
        .flat_map(|c| match böyük_mövqe(c) {
            Some(i) => vec![k[i]],
            None => c.to_lowercase().collect(),
        })
        .collect()
}
pub fn baş_böyük(s: &str) -> String {
    let mut it = s.chars();
    match it.next() {
        None => String::new(),
        Some(c) => böyüyə(&c.to_string()) + &kiçiyə(it.as_str()),
    }
}
pub fn hər_söz_böyük(s: &str) -> String {
    let mut n = String::new();
    let mut yeni = true;
    for c in s.chars() {
        if hərfdir(c) {
            n.push_str(&if yeni { böyüyə(&c.to_string()) } else { kiçiyə(&c.to_string()) });
            yeni = false;
        } else {
            n.push(c);
            yeni = true;
        }
    }
    n
}

/// (sinif, mövqe, böyükdür)
pub fn hərf_açarı(c: char) -> (u32, u32, u32) {
    if let Some(i) = kiçik_mövqe(c) {
        return (1, i as u32, 0);
    }
    if let Some(i) = böyük_mövqe(c) {
        return (1, i as u32, 1);
    }
    (0, c as u32, 0)
}

pub fn müqayisə(a: &str, b: &str) -> std::cmp::Ordering {
    let x: Vec<(u32, u32, u32)> = a.chars().map(hərf_açarı).collect();
    let y: Vec<(u32, u32, u32)> = b.chars().map(hərf_açarı).collect();
    let əsas_x: Vec<(u32, u32)> = x.iter().map(|t| (t.0, t.1)).collect();
    let əsas_y: Vec<(u32, u32)> = y.iter().map(|t| (t.0, t.1)).collect();
    əsas_x.cmp(&əsas_y).then_with(|| {
        let ix: Vec<u32> = x.iter().map(|t| t.2).collect();
        let iy: Vec<u32> = y.iter().map(|t| t.2).collect();
        ix.cmp(&iy)
    })
}

/// Yalnız əsas açar (sıralama üçün — `_sıralama_açarı`).
pub fn əsas_açar(a: &str) -> Vec<(u32, u32)> {
    a.chars().map(hərf_açarı).map(|t| (t.0, t.1)).collect()
}

pub fn latınla(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            'ə' => 'e', 'Ə' => 'E', 'ı' => 'i', 'İ' => 'I', 'ö' => 'o', 'Ö' => 'O',
            'ü' => 'u', 'Ü' => 'U', 'ç' => 'c', 'Ç' => 'C', 'ş' => 's', 'Ş' => 'S',
            'ğ' => 'g', 'Ğ' => 'G', c => c,
        })
        .collect()
}
