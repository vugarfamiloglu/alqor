"""
Alqor Studio — Xüsusiyyətlər paneli.

Redaktordakı `vidjet.ad(...)` çağırışının arqumentlərini oxuyur və
dəyişir. Panel hər parametri uyğun sahə ilə göstərir (mətn, ədəd,
seçim, rəng, bayraq); dəyişiklik koda yazılır, önbaxış dərhal yenilənir.

    oxu(mətn, kursor)  → {"ad", "parametrlər": [...], "üslub": {...}}
    qoy(mətn, kursor, ad, dəyər) → {"mətn", "kursor"}

`ad` — parametr adı (`"mətn"`, `"növ"`) və ya üslub açarı
(`"üslub.fon"`). `dəyər` — JSON dəyəri (mətn, ədəd, məntiq); `None`
arqumenti silir (vidjet standart dəyəri işlədir).

Yalnız sadə literallar (mətn, ədəd, `doğru`/`yanlış`, `boş`) panelda
redaktə olunur; ifadələr (`özü.ad`, `[...]`, `(x) => …`) olduğu kimi
göstərilir və toxunulmur — panel istifadəçinin kodunu pozmur.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any

from . import qurulus as Q


class XüsusiyyətXətası(ValueError):
    pass


# ── Parametr növləri ──────────────────────────────────────────────────

HADİSƏLƏR = {"klik", "dəyişdi", "yazıldı", "göndərildi", "bağlandı",
             "sətirKlik", "hərəkət"}
İFADƏLƏR = {"məzmun", "elementlər", "sütunlar", "sətirlər", "seçimlər",
            "cütlər", "adlar", "yollar", "alətlər", "altlıq", "sağ",
            "üslub"}
RƏNGLƏR = {"fon", "rəng"}


def _seçimlər(vidjet: str, parametr: str) -> list[str] | None:
    from alqor import vidjet as V
    if parametr == "ölçü" and vidjet in ("düymə",):
        return list(V.ÖLÇÜLƏR)
    if parametr == "növ":
        if vidjet in ("xəbərdarlıq", "bildirişQutusu"):
            return ["məlumat", "uğur", "xəbərdarlıq", "təhlükə"]
        return list(V.NÖVLƏR)
    if parametr == "düzləndir":
        return ["başlanğıc", "orta", "son", "uzat"]
    if parametr == "tərəf":
        return (["sol", "sağ"] if vidjet == "yanPanel"
                else ["yuxarı", "aşağı", "sol", "sağ"])
    if parametr == "səviyyə":
        return [1, 2, 3, 4, 5, 6]
    return None


ÜSLUB_SAHƏLƏRİ: list[dict] = [
    {"ad": "rəng", "növ": "rəng", "izah": "Mətnin rəngi"},
    {"ad": "fon", "növ": "rəng", "izah": "Fon rəngi"},
    {"ad": "kənar", "növ": "mətn", "izah": "Kənar (border), məs. 2px solid #333"},
    {"ad": "kənarRəngi", "növ": "rəng", "izah": "Kənarın rəngi"},
    {"ad": "künc", "növ": "ədəd", "izah": "Künc yuvarlaqlığı, px"},
    {"ad": "şrift", "növ": "ədəd", "izah": "Şrift ölçüsü, px"},
    {"ad": "qalın", "növ": "məntiq", "izah": "Qalın yazı"},
    {"ad": "kursiv", "növ": "məntiq", "izah": "Maili yazı"},
    {"ad": "şriftAiləsi", "növ": "mətn", "izah": "Şrift, məs. Georgia"},
    {"ad": "en", "növ": "ədəd", "izah": "En, px"},
    {"ad": "hündürlük", "növ": "ədəd", "izah": "Hündürlük, px"},
    {"ad": "boşluq", "növ": "ədəd", "izah": "Daxili boşluq (padding), px"},
    {"ad": "xaricBoşluq", "növ": "ədəd", "izah": "Xarici boşluq (margin), px"},
    {"ad": "düzləndir", "növ": "seçim", "izah": "Mətnin düzlənməsi",
     "seçimlər": ["sol", "orta", "sağ", "iki tərəf"]},
    {"ad": "şəffaflıq", "növ": "aralıq", "izah": "Şəffaflıq 0–1"},
    {"ad": "kölgə", "növ": "mətn", "izah": "Kölgə, məs. 0 2px 8px #0003"},
]


# ── Arqumentlərin ayrılması ───────────────────────────────────────────

@dataclass
class Arq:
    ad: str | None                # mövqeli arqument üçün None
    baş: int                      # arqumentin (adın) başlanğıcı
    son: int                      # arqumentin sonu (vergülsüz)
    dəyər_baş: int
    dəyər: str                    # dəyərin mənbə mətni


_AD_ARQ = re.compile(r"\s*([^\W\d][\w]*)\s*:(?!:)")


def arqumentlər(t: Q.Mətn, açan: int, bağlayan: int) -> list[Arq]:
    """`(`…`)` arasındakı ən üst səviyyə arqumentlər."""
    m = t.mətn
    n: list[Arq] = []
    dərinlik = 0
    baş = açan + 1
    for i in range(açan + 1, bağlayan + 1):
        c = m[i] if i < bağlayan else ","
        if i < bağlayan and t.x[i] != Q.KOD:
            continue
        if c in "([{":
            dərinlik += 1
        elif c in ")]}":
            dərinlik -= 1
        elif c == "," and dərinlik == 0:
            parça = m[baş:i]
            if parça.strip():
                sol = baş + len(parça) - len(parça.lstrip())
                sağ = baş + len(parça.rstrip())
                a = _AD_ARQ.match(m, sol)
                if a and a.end() <= sağ:
                    dbaş = a.end()
                    while dbaş < sağ and m[dbaş] in " \t\n":
                        dbaş += 1
                    n.append(Arq(a.group(1), sol, sağ, dbaş, m[dbaş:sağ]))
                else:
                    n.append(Arq(None, sol, sağ, sol, m[sol:sağ]))
            baş = i + 1
    return n


# ── Literallar ────────────────────────────────────────────────────────

_ƏDƏD = re.compile(r"^-?\d+(\.\d+)?$")


def literal_oxu(s: str) -> tuple[bool, Any]:
    """(sadədir, dəyər). Sadə deyilsə dəyər None."""
    s = s.strip()
    if s in ("doğru", "dogru"):
        return True, True
    if s in ("yanlış", "yanlis"):
        return True, False
    if s == "boş":
        return True, None
    if _ƏDƏD.match(s):
        return True, float(s) if "." in s else int(s)
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"' and "\n" not in s:
        iç = s[1:-1]
        # Interpolyasiya `{x}` — ifadədir, panel toxunmur
        if re.search(r"(?<!\\)\{", iç):
            return False, None
        try:
            return True, _qaçışları_aç(iç)
        except ValueError:
            return False, None
    return False, None


def _qaçışları_aç(s: str) -> str:
    n = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            q = s[i + 1]
            əvəz = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "{": "{",
                    "}": "}", "r": "\r", "'": "'", "0": "\0"}.get(q)
            if əvəz is None:
                raise ValueError(q)
            n.append(əvəz)
            i += 2
            continue
        if c == '"':
            raise ValueError(c)
        n.append(c)
        i += 1
    return "".join(n)


def literal_yaz(d: Any) -> str:
    if d is True:
        return "doğru"
    if d is False:
        return "yanlış"
    if d is None:
        return "boş"
    if isinstance(d, (int, float)):
        if isinstance(d, float) and d.is_integer():
            d = int(d)
        return str(d)
    if isinstance(d, str):
        q = (d.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
             .replace("\t", "\\t").replace("{", "\\{").replace("}", "\\}"))
        return f'"{q}"'
    raise XüsusiyyətXətası(f"bu dəyər panelda yazıla bilməz: {d!r}")


# ── Üslub lüğəti ──────────────────────────────────────────────────────

def üslub_oxu(mətn: str) -> dict[str, Any] | None:
    """`{"fon": "#fff", "künc": 8}` → lüğət; sadə deyilsə None."""
    s = mətn.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    t = Q.Mətn(s)
    cütlər = arqumentlər(t, 0, len(s) - 1)
    n: dict[str, Any] = {}
    for c in cütlər:
        a = re.match(r'^"([^"\\]+)"\s*:\s*(.*)$', c.dəyər if c.ad is None
                     else f'"{c.ad}": {c.dəyər}', re.S)
        if not a:
            return None
        sadə, d = literal_oxu(a.group(2))
        if not sadə:
            return None
        n[a.group(1)] = d
    return n


def üslub_yaz(l: dict[str, Any]) -> str:
    return "{" + ", ".join(f'"{a}": {literal_yaz(d)}'
                           for a, d in l.items()) + "}"


# ── Oxu ───────────────────────────────────────────────────────────────

def _çağırış(mətn: str, kursor: int):
    t = Q.Mətn(mətn)
    ç = Q.çağırış_tap(t, kursor)
    if ç is None:
        raise XüsusiyyətXətası("kursor `vidjet.…(…)` çağırışının "
                               "içində deyil")
    if ç.son is None:
        raise XüsusiyyətXətası(f"`vidjet.{ç.ad}(` mötərizəsi bağlanmayıb")
    return t, ç


def oxu(mətn: str, kursor: int) -> dict:
    from alqor import vidjet as V
    from alqor import vidjet_arayis as AR

    t, ç = _çağırış(mətn, kursor)
    if ç.ad not in V.VİDJETLƏR:
        raise XüsusiyyətXətası(f"`{ç.ad}` adlı vidjet yoxdur")
    arqlar = {a.ad: a for a in arqumentlər(t, ç.açan, ç.son) if a.ad}
    imza = inspect.signature(getattr(V, ç.ad))
    parametrlər = []
    for p in list(imza.parameters.values())[1:]:
        if p.name == "üslub":
            continue
        a = arqlar.get(p.name)
        standart = p.default
        if p.name in HADİSƏLƏR:
            növ = "hadisə"
        elif p.name in İFADƏLƏR:
            növ = "ifadə"
        elif _seçimlər(ç.ad, p.name):
            növ = "seçim"
        elif isinstance(standart, bool):
            növ = "məntiq"
        elif isinstance(standart, (int, float)):
            növ = "ədəd"
        elif p.name in RƏNGLƏR:
            növ = "rəng"
        else:
            növ = "mətn"
        sadə, dəyər = literal_oxu(a.dəyər) if a else (True, None)
        parametrlər.append({
            "ad": p.name, "növ": növ, "izah": AR.izah(ç.ad, p.name) or "",
            "seçimlər": _seçimlər(ç.ad, p.name),
            "standart": standart if isinstance(
                standart, (str, int, float, bool)) else None,
            "verilib": a is not None,
            "sadə": sadə and növ not in ("hadisə", "ifadə"),
            "dəyər": dəyər if a else None,
            "ifadə": a.dəyər if a else None,
        })
    ü = arqlar.get("üslub")
    üslub = üslub_oxu(ü.dəyər) if ü else {}
    return {
        "ad": ç.ad, "beynəlxalqAd": V.BEYNƏLXALQ_ADLAR[ç.ad],
        "mövqe": ç.ad_başı,
        "sətir": t.sətir_nömrəsi(ç.baş) + 1,
        "parametrlər": parametrlər,
        "üslub": üslub,                  # None — ifadədir, redaktə olunmur
        "üslubİfadə": ü.dəyər if ü and üslub is None else None,
        "üslubSahələri": ÜSLUB_SAHƏLƏRİ,
    }


# ── Yaz ───────────────────────────────────────────────────────────────

def _sil(m: str, a: Arq, hamısı: list[Arq]) -> str:
    i = hamısı.index(a)
    if len(hamısı) == 1:
        return m[:a.baş] + m[a.son:]
    if i > 0:
        # Əvvəlki arqumentin sonundan bu arqumentin sonuna qədər
        return m[:hamısı[i - 1].son] + m[a.son:]
    return m[:a.baş] + m[hamısı[1].baş:]


def _əlavə(m: str, t: Q.Mətn, ç, hamısı: list[Arq], yeni: str) -> str:
    if not hamısı:
        return m[:ç.açan + 1] + yeni + m[ç.açan + 1:]
    son = hamısı[-1]
    çox_sətirli = "\n" in m[ç.açan:ç.son]
    if çox_sətirli:
        sətir_başı = m.rfind("\n", 0, son.baş) + 1
        girinti = m[sətir_başı:son.baş]
        if girinti.strip():                 # `(a: 1,` — eyni sətirdə
            girinti = " " * (son.baş - sətir_başı)
        return m[:son.son] + ",\n" + girinti + yeni + m[son.son:]
    return m[:son.son] + ", " + yeni + m[son.son:]


def qoy(mətn: str, kursor: int, ad: str, dəyər: Any) -> dict:
    from alqor import vidjet as V

    t, ç = _çağırış(mətn, kursor)
    hamısı = arqumentlər(t, ç.açan, ç.son)
    adlılar = {a.ad: a for a in hamısı if a.ad}

    if ad.startswith("üslub."):
        açar = ad[len("üslub."):]
        if açar not in V.ÜSLUB_AÇARLARI and açar not in ("qalın", "kursiv"):
            raise XüsusiyyətXətası(f"`{açar}` üslub açarı deyil")
        mövcud = adlılar.get("üslub")
        l = üslub_oxu(mövcud.dəyər) if mövcud else {}
        if l is None:
            raise XüsusiyyətXətası("`üslub` ifadədir — redaktorda dəyişin")
        if dəyər is None or dəyər == "":
            l.pop(açar, None)
        else:
            l[açar] = dəyər
        ad, dəyər = "üslub", (None if not l else _Xam(üslub_yaz(l)))

    imza = inspect.signature(getattr(V, ç.ad))
    if ad not in list(imza.parameters)[1:]:
        raise XüsusiyyətXətası(f"`{ç.ad}` vidjetinin `{ad}` parametri yoxdur")
    if ad in HADİSƏLƏR or (ad in İFADƏLƏR and ad != "üslub"):
        raise XüsusiyyətXətası(f"`{ad}` ifadədir — redaktorda dəyişin")
    mövcud = adlılar.get(ad)
    if mövcud is not None and ad != "üslub" \
            and not literal_oxu(mövcud.dəyər)[0]:
        raise XüsusiyyətXətası(f"`{ad}` ifadədir — redaktorda dəyişin")

    m = mətn
    if dəyər is None:
        if mövcud is None:
            return {"mətn": mətn, "kursor": ç.ad_başı, "dəyişdi": False}
        m = _sil(m, mövcud, hamısı)
    else:
        mətn_d = dəyər.s if isinstance(dəyər, _Xam) else literal_yaz(dəyər)
        if mövcud is not None:
            m = m[:mövcud.dəyər_baş] + mətn_d + m[mövcud.son:]
        else:
            m = _əlavə(m, t, ç, hamısı, f"{ad}: {mətn_d}")
    return {"mətn": m, "kursor": ç.ad_başı, "dəyişdi": m != mətn}


class _Xam:
    """Artıq Alqor sintaksisində olan dəyər (üslub lüğəti)."""

    def __init__(self, s: str):
        self.s = s
