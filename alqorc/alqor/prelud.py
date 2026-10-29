"""
Alqor prelüdü — hər proqramdan əvvəl yüklənən Alqor kodu (spes. § 7.5).

Mətn bir yerdədir: Python icraçısı və JS kompilyatoru buradan oxuyur,
Rust icraçısı faylı `include_str!` ilə daxil edib üç dırnaqlı xam mətnin
sərhədləri arasındakı hissəni götürür (`alqor-rs/src/icraci/kitabxana.rs`).
"""

MƏTN = r'''
// Alqor prelüdü — hər proqramdan əvvəl yüklənir (spes. § 7.5).
// Python, Rust və JS icraçıları bu faylı eyni cür icra edir.

/// Əməliyyatın nəticəsi: `Uğur(dəyər)` və ya `Uğursuz(xəta)`.
sadalama Nəticə
    Uğur(dəyər: istənilən)
    Uğursuz(xəta: istənilən)

    metod uğurludur() -> məntiq
        seç özü
            hal Nəticə.Uğur(_) → qaytar doğru
            digər hallarda → qaytar yanlış
        son
    son

    metod uğursuzdur() -> məntiq
        qaytar deyil özü.uğurludur()
    son

    metod dəyərVəYa(əvəzi)
        seç özü
            hal Nəticə.Uğur(d) → qaytar d
            digər hallarda → qaytar əvəzi
        son
    son

    metod çevir(f)
        seç özü
            hal Nəticə.Uğur(d) → qaytar Nəticə.Uğur(f(d))
            digər hallarda → qaytar özü
        son
    son

    metod zəncirlə(f)
        seç özü
            hal Nəticə.Uğur(d) → qaytar f(d)
            digər hallarda → qaytar özü
        son
    son

    metod aç()
        seç özü
            hal Nəticə.Uğur(d) → qaytar d
            hal Nəticə.Uğursuz(x) → at NəticəXətası("uğursuz nəticə açıldı: {x}")
        son
    son
son

/// Uğurlu nəticə: `Uğur(5)` — `Nəticə.Uğur(5)`
funksiya Uğur(dəyər) -> Nəticə
    qaytar Nəticə.Uğur(dəyər)
son

/// Uğursuz nəticə: `Uğursuz("səbəb")` — `Nəticə.Uğursuz("səbəb")`
funksiya Uğursuz(xəta) -> Nəticə
    qaytar Nəticə.Uğursuz(xəta)
son
'''

_AĞAC = None


def ağac():
    """Prelüdün AAC-i (bir dəfə təhlil olunur)."""
    global _AĞAC
    if _AĞAC is None:
        from .lekser import Lekser
        from .menbe import Mənbə
        from .parser import Parser
        from .xeta import XətaToplayıcı
        x = XətaToplayıcı()
        s = Mənbə("<prelüd>", MƏTN)
        _AĞAC = Parser(Lekser(s, x).leksə(), s, x).ayır()
        if not x.uğurludur():
            raise RuntimeError("prelüd təhlil olunmadı:\n" + x.hesabat(False))
    return _AĞAC
