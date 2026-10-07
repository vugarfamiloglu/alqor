"""Əlavə modullar üçün ortaq köməkçilər (Alqor funksiyasını çağırmaq …)."""

from __future__ import annotations

from typing import Any

from ..deyerler import AlqorXəta, tip_adı


def çağır(icraçı, f: Any, *arqumentlər: Any, **adlı: Any) -> Any:
    """Alqor funksiyasını çağırır; `asinxron funksiya`-nın `Gələcək`
    nəticəsini gözləyib həll edir (kitabxana kodu sinxrondur)."""
    from ..korutin import Gələcək
    n = icraçı._çağır(f, list(arqumentlər), adlı, None)
    while isinstance(n, Gələcək):
        n = n.al()
    return n


def çağırılandır(f: Any) -> bool:
    from ..deyerler import Çağırılan, Nümunə
    return isinstance(f, Çağırılan) or (
        isinstance(f, Nümunə) and f.sinif.metod_tap("çağır") is not None)


def funksiya_tələb(f: Any, ad: str) -> Any:
    if not çağırılandır(f):
        raise AlqorXəta("TipXətası",
                        f"`{ad}` funksiya gözləyir, `{tip_adı(f)}` gəlib",
                        None, "ALQ-T001")
    return f


def müsbət_ədəd(x: Any, ad: str, sıfır: bool = False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or \
            x < 0 or (x == 0 and not sıfır) or x != x:
        raise AlqorXəta("ArqumentXətası",
                        f"`{ad}` müsbət ədəd olmalıdır, `{x!r}` gəlib",
                        None, "ALQ-T004")
    return float(x)
