"""`verilənlər` sürücülərinin ortaq hissəsi: nəticə, xətalar, ünvan, parametrlər."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable


class SürücüXətası(Exception):
    """Baza xətası — `VerilənlərXətası`-na çevrilir."""


class MəhdudiyyətPozuldu(SürücüXətası):
    """Unikal/xarici açar/NOT NULL pozuntusu — `MəhdudiyyətXətası`."""


@dataclass
class Nəticə:
    sütunlar: list[str] = field(default_factory=list)
    sətirlər: list[tuple] = field(default_factory=list)
    say: int = -1                         # təsir edilən sətir sayı
    son_id: int | None = None

    def lüğətlər(self) -> list[dict]:
        return [dict(zip(self.sütunlar, s)) for s in self.sətirlər]


@dataclass
class Ünvan:
    sxem: str
    istifadəçi: str | None
    parol: str | None
    host: str
    port: int
    baza: str
    seçimlər: dict[str, str]


def ünvanı_ayır(ünvan: str, standart_port: int) -> Ünvan:
    u = urllib.parse.urlsplit(ünvan)
    q = dict(urllib.parse.parse_qsl(u.query))
    try:
        port = u.port or standart_port
    except ValueError:
        raise SürücüXətası(f"port yanlışdır: {ünvan}") from None
    return Ünvan(
        u.scheme,
        urllib.parse.unquote(u.username) if u.username else None,
        urllib.parse.unquote(u.password) if u.password is not None else None,
        u.hostname or "127.0.0.1", port,
        urllib.parse.unquote(u.path.lstrip("/")), q)


def gizli_ünvan(ünvan: str) -> str:
    """Jurnal/xəta mətnləri üçün — parol `***` ilə əvəzlənir."""
    u = urllib.parse.urlsplit(ünvan)
    if u.password is None:
        return ünvan
    netloc = u.netloc.replace(":" + u.password + "@", ":***@", 1)
    return urllib.parse.urlunsplit(u._replace(netloc=netloc))


def parametrləri_gəz(sql: str, əvəz: Callable[[str, int | None], str],
                     mysql: bool = False) -> str:
    """
    SQL-dəki `$n` və `?` yer tutucularını `əvəz(növ, n)` ilə əvəzləyir.
    Mətn literalları ('…'), sitatlı adlar ("…", `…`), şərhlər (`--`,
    `/* */`) və PostgreSQL dollar-mətnləri (`$$…$$`, `$teq$…$teq$`)
    toxunulmur. `növ` — "$" (nömrəli) və ya "?" (ardıcıl).
    """
    n: list[str] = []
    i, L = 0, len(sql)
    while i < L:
        c = sql[i]
        if c == "'" or c == '"' or (c == "`" and mysql):
            j = i + 1
            while j < L:
                if mysql and c != "`" and sql[j] == "\\":
                    j += 2
                    continue
                if sql[j] == c:
                    if j + 1 < L and sql[j + 1] == c:
                        j += 2
                        continue
                    break
                j += 1
            n.append(sql[i:j + 1])
            i = j + 1
            continue
        if sql.startswith("--", i) or (mysql and c == "#"):
            j = sql.find("\n", i)
            j = L if j < 0 else j
            n.append(sql[i:j])
            i = j
            continue
        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = L if j < 0 else j + 2
            n.append(sql[i:j])
            i = j
            continue
        if c == "$":
            j = i + 1
            while j < L and sql[j].isdigit():
                j += 1
            if j > i + 1:
                n.append(əvəz("$", int(sql[i + 1:j])))
                i = j
                continue
            # Dollar-mətn: $teq$ … $teq$
            k = i + 1
            while k < L and (sql[k].isalnum() or sql[k] == "_"):
                k += 1
            if k < L and sql[k] == "$" and not mysql:
                teq = sql[i:k + 1]
                son = sql.find(teq, k + 1)
                son = L if son < 0 else son + len(teq)
                n.append(sql[i:son])
                i = son
                continue
        if c == "?":
            n.append(əvəz("?", None))
            i += 1
            continue
        n.append(c)
        i += 1
    return "".join(n)
