"""
`lokalizasiya` — çoxdilli tətbiqlər: tərcümələr, cəm formaları, ədəd,
tarix və nisbi vaxt formatı (§ 10.17).

    gətir lokalizasiya

    // dillər/az.json, dillər/en.json … (JSON, TOML və ya YAML)
    dəyişən t = lokalizasiya.yüklə("dillər", standart: "az")

    // və ya birbaşa (Alqor mətnində `\\{` — interpolyasiya olmasın deyə):
    dəyişən t = lokalizasiya.yarat({
        "az": {"salam": "Salam, \\{ad}!",
               "mesaj": {"bir": "\\{say} yeni mesaj", "digər": "\\{say} yeni mesaj"},
               "menyu": {"fayl": "Fayl"}},
        "en": {"salam": "Hello, \\{ad}!",
               "mesaj": {"bir": "\\{say} new message", "digər": "\\{say} new messages"}},
    }, standart: "az")

    yaz(t.t("salam", {"ad": "Aysel"}))            // Salam, Aysel!
    yaz(t.dil("en").t("mesaj", say: 3))           // 3 new messages
    yaz(t.t("menyu.fayl"))                        // nöqtə ilə iç-içə açar

    lokalizasiya.ədəd(1234567.891, dil: "az")     // "1 234 567,891"
    lokalizasiya.tarix("2026-10-07", dil: "az", növ: "uzun")
                                                  // "7 oktyabr 2026"
    lokalizasiya.nisbiVaxt(-90, dil: "az")        // "1 dəqiqə əvvəl"
    lokalizasiya.siyahı(["alma", "armud", "heyva"])   // "alma, armud və heyva"

Tərcümə tapılmasa ardıcıllıqla axtarılır: `az-AZ` → `az` → standart dil;
heç yerdə yoxdursa açarın özü qaytarılır (və `çatışmayanlar()`-a düşür).
Cəm formaları CLDR kateqoriyaları ilə: `sıfır bir iki az çox digər`
(ingiliscə `zero one two few many other` adları da qəbul edilir).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..deyerler import AlqorXəta, Daxili, mətnə

DİLLƏR: dict[str, dict] = {
    "az": {
        "ad": "Azərbaycan dili", "min": " ", "kəsr": ",",
        "aylar": ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
                  "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"],
        "günlər": ["bazar ertəsi", "çərşənbə axşamı", "çərşənbə",
                   "cümə axşamı", "cümə", "şənbə", "bazar"],
        "uzun": "{g} {ay} {il}", "tam": "{il}, {g} {ay}, {hg}",
        "qısa": "{gg}.{aa}.{il}", "və": "və",
        "vahidlər": {"saniyə": "saniyə", "dəqiqə": "dəqiqə", "saat": "saat",
                     "gün": "gün", "həftə": "həftə", "ay": "ay", "il": "il"},
        "əvvəl": "{n} {v} əvvəl", "sonra": "{n} {v} sonra",
        "indi": "indicə",
    },
    "tr": {
        "ad": "Türkçe", "min": ".", "kəsr": ",",
        "aylar": ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran",
                  "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"],
        "günlər": ["pazartesi", "salı", "çarşamba", "perşembe", "cuma",
                   "cumartesi", "pazar"],
        "uzun": "{g} {ay} {il}", "tam": "{g} {ay} {il} {hg}",
        "qısa": "{gg}.{aa}.{il}", "və": "ve",
        "vahidlər": {"saniyə": "saniye", "dəqiqə": "dakika", "saat": "saat",
                     "gün": "gün", "həftə": "hafta", "ay": "ay", "il": "yıl"},
        "əvvəl": "{n} {v} önce", "sonra": "{n} {v} sonra", "indi": "şimdi",
    },
    "en": {
        "ad": "English", "min": ",", "kəsr": ".",
        "aylar": ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December"],
        "günlər": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                   "Saturday", "Sunday"],
        "uzun": "{ay} {g}, {il}", "tam": "{hg}, {ay} {g}, {il}",
        "qısa": "{aa}/{gg}/{il}", "və": "and",
        "vahidlər": {"saniyə": ("second", "seconds"),
                     "dəqiqə": ("minute", "minutes"),
                     "saat": ("hour", "hours"), "gün": ("day", "days"),
                     "həftə": ("week", "weeks"), "ay": ("month", "months"),
                     "il": ("year", "years")},
        "əvvəl": "{n} {v} ago", "sonra": "in {n} {v}", "indi": "just now",
    },
    "ru": {
        "ad": "Русский", "min": " ", "kəsr": ",",
        "aylar": ["января", "февраля", "марта", "апреля", "мая", "июня",
                  "июля", "августа", "сентября", "октября", "ноября",
                  "декабря"],
        "günlər": ["понедельник", "вторник", "среда", "четверг", "пятница",
                   "суббота", "воскресенье"],
        "uzun": "{g} {ay} {il} г.", "tam": "{hg}, {g} {ay} {il} г.",
        "qısa": "{gg}.{aa}.{il}", "və": "и",
        "vahidlər": {"saniyə": ("секунду", "секунды", "секунд"),
                     "dəqiqə": ("минуту", "минуты", "минут"),
                     "saat": ("час", "часа", "часов"),
                     "gün": ("день", "дня", "дней"),
                     "həftə": ("неделю", "недели", "недель"),
                     "ay": ("месяц", "месяца", "месяцев"),
                     "il": ("год", "года", "лет")},
        "əvvəl": "{n} {v} назад", "sonra": "через {n} {v}",
        "indi": "только что",
    },
}

_KATEQORİYA = {"zero": "sıfır", "one": "bir", "two": "iki", "few": "az",
               "many": "çox", "other": "digər"}


def _əsas(dil: str) -> str:
    return str(dil).replace("_", "-").split("-")[0].lower()


def cəm_kateqoriyası(dil: str, n: Any) -> str:
    """CLDR cəm qaydaları (sadələşdirilmiş, tam ədədlər üçün dəqiq)."""
    d = _əsas(dil)
    try:
        tam = float(n).is_integer()
        i = abs(int(n))
    except (TypeError, ValueError):
        return "digər"
    if d in ("ru", "uk", "be", "sr", "hr", "bs"):
        if not tam:
            return "digər"
        if i % 10 == 1 and i % 100 != 11:
            return "bir"
        if 2 <= i % 10 <= 4 and not 12 <= i % 100 <= 14:
            return "az"
        return "çox"
    if d == "pl":
        if i == 1 and tam:
            return "bir"
        if 2 <= i % 10 <= 4 and not 12 <= i % 100 <= 14:
            return "az"
        return "çox"
    if d in ("ar",):
        if i == 0:
            return "sıfır"
        if i == 1:
            return "bir"
        if i == 2:
            return "iki"
        if 3 <= i % 100 <= 10:
            return "az"
        if 11 <= i % 100 <= 99:
            return "çox"
        return "digər"
    if d in ("ja", "zh", "ko", "fa", "id", "th", "vi"):
        return "digər"
    if d == "fr":
        return "bir" if i in (0, 1) else "digər"
    # az, tr, en, de, es, it … — "bir" yalnız 1 üçün
    return "bir" if i == 1 and tam else "digər"


def _profil(dil: str) -> dict:
    return DİLLƏR.get(_əsas(dil), DİLLƏR["en"])


def ədəd(x: Any, dil: str = "az", rəqəm: Any = None) -> str:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise AlqorXəta("TipXətası", "`ədəd` ədəd gözləyir", None,
                        "ALQ-T001")
    p = _profil(dil)
    if rəqəm is not None:
        s = f"{abs(x):.{int(rəqəm)}f}"
    elif isinstance(x, int):
        s = str(abs(x))
    else:
        s = repr(abs(float(x)))
        if "e" in s:
            s = f"{abs(x):f}".rstrip("0").rstrip(".")
        if s.endswith(".0"):
            s = s[:-2]
    tam, _, kəsr = s.partition(".")
    qruplar = []
    while len(tam) > 3:
        qruplar.insert(0, tam[-3:])
        tam = tam[:-3]
    qruplar.insert(0, tam)
    # Azərbaycan/rus üslubunda 4 rəqəmli ədədlər qruplaşdırılmır: 1234
    if _əsas(dil) in ("az", "ru") and len(qruplar) == 2 and \
            len(qruplar[0]) == 1:
        qruplar = [qruplar[0] + qruplar[1]]
    n = p["min"].join(qruplar) + (p["kəsr"] + kəsr if kəsr else "")
    return ("-" if x < 0 else "") + n


def faiz(x: Any, dil: str = "az", rəqəm: Any = 0) -> str:
    n = ədəd(float(x) * 100, dil, rəqəm)
    d = _əsas(dil)
    if d == "tr":
        return "%" + n
    if d in ("az", "ru", "fr", "de"):
        return n + " %"
    return n + "%"


def _tarix(x: Any) -> datetime:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return datetime.fromtimestamp(x)
    s = str(x).strip().rstrip("Z")
    try:
        return datetime.fromisoformat(s.replace(" ", "T"))
    except ValueError:
        try:
            d = date.fromisoformat(s)
            return datetime(d.year, d.month, d.day)
        except ValueError:
            raise AlqorXəta("FormatXətası",
                            f"`{x}` tarix kimi oxunmadı (ISO gözlənilir)",
                            None, "ALQ-R005")


def tarix(x: Any = None, dil: str = "az", növ: str = "uzun",
          saat: Any = False) -> str:
    t = datetime.now() if x is None else _tarix(x)
    p = _profil(dil)
    if növ not in ("uzun", "tam", "qısa"):
        raise AlqorXəta("ArqumentXətası",
                        '`növ` "uzun", "tam" və ya "qısa" olmalıdır', None,
                        "ALQ-T004")
    n = p[növ].format(g=t.day, gg=f"{t.day:02d}", aa=f"{t.month:02d}",
                      ay=p["aylar"][t.month - 1], il=t.year,
                      hg=p["günlər"][t.weekday()])
    if saat:
        n += f", {t.hour:02d}:{t.minute:02d}" if _əsas(dil) != "en" else \
            f", {(t.hour % 12) or 12}:{t.minute:02d} " \
            f"{'AM' if t.hour < 12 else 'PM'}"
    return n


def _vahid_adı(dil: str, vahid: str, n: int) -> str:
    v = _profil(dil)["vahidlər"][vahid]
    if isinstance(v, str):
        return v
    k = cəm_kateqoriyası(dil, n)
    if len(v) == 2:
        return v[0] if k == "bir" else v[1]
    return v[0] if k == "bir" else (v[1] if k == "az" else v[2])


def nisbi_vaxt(saniyə: Any, dil: str = "az") -> str:
    """Mənfi — keçmiş, müsbət — gələcək. Vaxt mətni də verilə bilər
    (indiki andan fərq hesablanır)."""
    if isinstance(saniyə, str):
        saniyə = (_tarix(saniyə) - datetime.now()).total_seconds()
    if isinstance(saniyə, bool) or not isinstance(saniyə, (int, float)):
        raise AlqorXəta("TipXətası", "`nisbiVaxt` saniyə və ya tarix "
                        "gözləyir", None, "ALQ-T001")
    p = _profil(dil)
    a = abs(saniyə)
    if a < 10:
        return p["indi"]
    for vahid, ölçü in (("il", 365 * 86400), ("ay", 30 * 86400),
                        ("həftə", 7 * 86400), ("gün", 86400),
                        ("saat", 3600), ("dəqiqə", 60), ("saniyə", 1)):
        if a >= ölçü:
            n = int(a // ölçü)
            break
    şablon = p["əvvəl"] if saniyə < 0 else p["sonra"]
    return şablon.format(n=n, v=_vahid_adı(dil, vahid, n))


def siyahı_mətni(s: Any, dil: str = "az", bağlayıcı: Any = None) -> str:
    if not isinstance(s, list):
        raise AlqorXəta("TipXətası", "`siyahı` siyahı gözləyir", None,
                        "ALQ-T001")
    e = [mətnə(x) for x in s]
    və = bağlayıcı if bağlayıcı is not None else _profil(dil)["və"]
    if len(e) <= 1:
        return "".join(e)
    if _əsas(dil) == "en" and len(e) > 2 and bağlayıcı is None:
        return ", ".join(e[:-1]) + f", {və} " + e[-1]
    return ", ".join(e[:-1]) + f" {və} " + e[-1]


# ── Tərcümə kataloqu ──────────────────────────────────────────────────

class Tərcümələr:
    ALQOR_TİP_ADI = "tərcümələr"

    def __init__(self, kataloq: dict, standart: str = "az",
                 dil: str | None = None, çatışmayan: set | None = None):
        self.kataloq = kataloq
        self.standart = standart
        self.cari = dil or standart
        self.çatışmayan = çatışmayan if çatışmayan is not None else set()

    def __repr__(self) -> str:
        return f"<tərcümələr {self.cari} ({', '.join(self.kataloq)})>"

    def zəncir(self) -> list[str]:
        n = []
        d = str(self.cari).replace("_", "-")
        hissələr = d.split("-")
        for i in range(len(hissələr), 0, -1):
            n.append("-".join(hissələr[:i]))
        n.append(self.standart)
        return [x for i, x in enumerate(n) if x not in n[:i]]

    def _tap(self, açar: str) -> tuple[Any, str] | None:
        for d in self.zəncir():
            c: Any = self.kataloq.get(d)
            if c is None:
                continue
            if açar in c:
                return c[açar], d
            for h in açar.split("."):
                if isinstance(c, dict) and h in c:
                    c = c[h]
                else:
                    c = None
                    break
            if c is not None:
                return c, d
        return None

    def t(self, açar: Any, parametrlər: Any = None, **adlı: Any) -> str:
        açar = str(açar)
        p = dict(parametrlər) if isinstance(parametrlər, dict) else {}
        p.update(adlı)
        x = self._tap(açar)
        if x is None:
            self.çatışmayan.add(f"{self.cari}:{açar}")
            return açar
        dəyər, dil = x
        if isinstance(dəyər, dict):
            say = p.get("say", p.get("n"))
            k = cəm_kateqoriyası(dil, say if say is not None else 0)
            forma = None
            if say is not None and int(say) == 0 and "sıfır" in dəyər or \
                    say is not None and int(say) == 0 and "zero" in dəyər:
                forma = dəyər.get("sıfır", dəyər.get("zero"))
            if forma is None:
                ters = {v: a for a, v in _KATEQORİYA.items()}
                forma = dəyər.get(k, dəyər.get(ters.get(k, ""),
                                  dəyər.get("digər", dəyər.get("other"))))
            if forma is None:
                self.çatışmayan.add(f"{self.cari}:{açar}")
                return açar
            dəyər = forma
        if not isinstance(dəyər, str):
            return mətnə(dəyər)

        def əvəz(m: re.Match) -> str:
            ad, _, fmt = m.group(1).partition(":")
            if ad not in p:
                return m.group(0)
            v = p[ad]
            if fmt == "ədəd" and isinstance(v, (int, float)):
                return ədəd(v, dil)
            if fmt == "tarix":
                return tarix(v, dil)
            return mətnə(v)
        return re.sub(r"\{([^{}]+)\}", əvəz, dəyər)

    def dil(self, kod: Any) -> "Tərcümələr":
        return Tərcümələr(self.kataloq, self.standart, str(kod),
                          self.çatışmayan)

    def var(self, açar: Any) -> bool:
        return self._tap(str(açar)) is not None

    def əlavə(self, dil: Any, l: Any) -> None:
        if not isinstance(l, dict):
            raise AlqorXəta("TipXətası", "`əlavə` lüğət gözləyir", None,
                            "ALQ-T001")
        self.kataloq.setdefault(str(dil), {}).update(l)


Tərcümələr.ALQOR_METODLARI = {
    "t": lambda i, x, a, p=None, **k: x.t(a, p, **k),
    "dil": lambda i, x, kod: x.dil(kod),
    "cari": lambda i, x: x.cari,
    "dillər": lambda i, x: list(x.kataloq),
    "var": lambda i, x, a: x.var(a),
    "əlavə": lambda i, x, d, l: x.əlavə(d, l),
    "çatışmayanlar": lambda i, x: sorted(x.çatışmayan),
    "ədəd": lambda i, x, n, rəqəm=None: ədəd(n, x.cari, rəqəm),
    "tarix": lambda i, x, t=None, növ="uzun", saat=False:
        tarix(t, x.cari, növ, saat),
    "nisbiVaxt": lambda i, x, s: nisbi_vaxt(s, x.cari),
}


def _fayl_oxu(p: Path) -> dict:
    mətn = p.read_text(encoding="utf-8")
    try:
        if p.suffix == ".json":
            return json.loads(mətn)
        if p.suffix == ".toml":
            from .toml_ import oxu
            return oxu(mətn)
        if p.suffix in (".yaml", ".yml"):
            from .yaml_ import oxu
            return oxu(mətn)
    except AlqorXəta:
        raise
    except ValueError as x:
        raise AlqorXəta("FormatXətası", f"{p.name}: {x}", None, "ALQ-R005")
    return {}


def yüklə(qovluq: Any = "dillər", standart: Any = "az") -> Tərcümələr:
    q = Path(str(qovluq))
    if not q.is_dir():
        raise AlqorXəta("FaylTapılmadıXətası",
                        f'"{qovluq}" qovluğu tapılmadı', None, "ALQ-R009")
    kataloq: dict = {}
    for p in sorted(q.iterdir()):
        if p.suffix in (".json", ".toml", ".yaml", ".yml") and p.is_file():
            d = _fayl_oxu(p)
            if not isinstance(d, dict):
                raise AlqorXəta("FormatXətası",
                                f"{p.name}: kök lüğət olmalıdır", None,
                                "ALQ-R005")
            kataloq.setdefault(p.stem, {}).update(d)
    return Tərcümələr(kataloq, str(standart))


def yarat(kataloq: Any, standart: Any = "az") -> Tərcümələr:
    if not isinstance(kataloq, dict) or not all(
            isinstance(v, dict) for v in kataloq.values()):
        raise AlqorXəta("TipXətası", '`yarat` {"dil": {açar: mətn}} '
                        "lüğəti gözləyir", None, "ALQ-T001")
    return Tərcümələr({str(a): dict(v) for a, v in kataloq.items()},
                      str(standart))


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    return {
        "yarat": D("yarat", yarat, 1, 2),
        "yüklə": D("yüklə", yüklə, 0, 2),
        "ədəd": D("ədəd", ədəd, 1, 3),
        "faiz": D("faiz", faiz, 1, 3),
        "tarix": D("tarix", tarix, 0, 4),
        "nisbiVaxt": D("nisbiVaxt", nisbi_vaxt, 1, 2),
        "siyahı": D("siyahı", siyahı_mətni, 1, 3),
        "cəmKateqoriyası": D("cəmKateqoriyası",
                             lambda dil, n: cəm_kateqoriyası(dil, n), 2, 2),
        "aylar": D("aylar", lambda dil="az": list(_profil(dil)["aylar"]),
                   0, 1),
        "günlər": D("günlər", lambda dil="az": list(_profil(dil)["günlər"]),
                    0, 1),
        "dillər": D("dillər", lambda: {k: v["ad"]
                                        for k, v in DİLLƏR.items()}),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F
    m, e, b, i = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ, T.TAM
    Tr = T.Sadə("tərcümələr")
    return {
        "yarat": F(T.Lüğət(m, e), m, qaytarır=Tr, standart=1),
        "yüklə": F(m, m, qaytarır=Tr, standart=2),
        "ədəd": F(e, m, i, qaytarır=m, standart=2),
        "faiz": F(e, m, i, qaytarır=m, standart=2),
        "tarix": F(e, m, m, b, qaytarır=m, standart=4),
        "nisbiVaxt": F(e, m, qaytarır=m, standart=1),
        "siyahı": F(T.Siyahı(), m, m, qaytarır=m, standart=2),
        "cəmKateqoriyası": F(m, e, qaytarır=m),
        "aylar": F(m, qaytarır=T.Siyahı(m), standart=1),
        "günlər": F(m, qaytarır=T.Siyahı(m), standart=1),
        "dillər": F(qaytarır=T.Lüğət(m, m)),
    }


def obyekt_tipləri() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    m, e, b, i = T.MƏTN, T.İSTƏNİLƏN, T.MƏNTİQ, T.TAM
    Tr = T.Sadə("tərcümələr")
    return {"tərcümələr": {
        "t": Fsərbəst(m),
        "dil": F(m, qaytarır=Tr), "cari": F(qaytarır=m),
        "dillər": F(qaytarır=T.Siyahı(m)), "var": F(m, qaytarır=b),
        "əlavə": F(m, T.Lüğət(m, e), qaytarır=T.HEÇ),
        "çatışmayanlar": F(qaytarır=T.Siyahı(m)),
        "ədəd": F(e, i, qaytarır=m, standart=1),
        "tarix": F(e, m, b, qaytarır=m, standart=3),
        "nisbiVaxt": F(e, qaytarır=m),
    }}
