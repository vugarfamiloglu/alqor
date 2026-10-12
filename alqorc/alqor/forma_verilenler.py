"""
Formada verilənlər bazası (§ 12.6.5) — Delphi-dəki TDatabase / TTable /
TDataSource / TDBNavigator modeli.

    obyekt Baza1: VerilənlərBazası       // görünməyən komponent
        növ = "sqlite"
        fayl = "mekteb.db"
        sxem = "mekteb.sxem"             // cədvəllər avtomatik yaradılır
    son
    obyekt Tələbələr: Sorğu              // cədvəl + cari sətir (kursor)
        baza = Baza1
        cədvəl = "tələbələr"
        sırala = "ad"
    son
    obyekt Siyahı: cədvəl                // vidjet — sətirlər sorğudan
        mənbə = Tələbələr
    son
    obyekt AdSahəsi: sahə                // cari sətrin `ad` sütunu
        etiket = "Ad"
        mənbə = Tələbələr
        sütun = "ad"
    son
    obyekt Nav: naviqator                // ⏮ ◀ ▶ ⏭ ＋ 🗑 💾 ↻
        mənbə = Tələbələr
    son

Kodda: `özü.Tələbələr.cari["ad"]`, `özü.Tələbələr.növbəti()`,
`özü.Baza1.sorğu("SELECT …")`, `özü.Baza1.cədvəl("tələbələr").al()`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .deyerler import AlqorXəta, Daxili, Element, mətnə
from .forma import FormaObyekti, İstinad, ObyektTəsviri


def _xəta(mesaj: str, kod: str = "ALQ-R013") -> AlqorXəta:
    return AlqorXəta("VerilənlərXətası", mesaj, None, kod)


class GörünməyənKomponent(FormaObyekti):
    """Formada görünməyən, kodla işlədilən komponent."""

    #  xassə → (standart, izah) — dizayner bunlardan inspektor qurur
    XASSƏLƏR: dict[str, tuple[Any, str]] = {}
    METODLAR: dict[str, str] = {}             # ad → izah (dizayner üçün)

    def __init__(self, t: ObyektTəsviri, sahib: Any):
        super().__init__(t, sahib)
        self._icazəli = list(self.XASSƏLƏR)
        self.qovluq: Path = Path.cwd()

    def x(self, ad: str) -> Any:
        if ad in self.xassələr:
            return self.xassələr[ad]
        return self.XASSƏLƏR.get(ad, (None, ""))[0]

    def alqor_üzv(self, icraçı, ad: str, yer) -> Any:
        if ad in self.XASSƏLƏR or ad in ("ad", "növ"):
            return super().alqor_üzv(icraçı, ad, yer) \
                if ad in self.xassələr or ad in ("ad", "növ") \
                else self.XASSƏLƏR[ad][0]
        return self.üzv(icraçı, ad, yer)

    def üzv(self, icraçı, ad: str, yer) -> Any:
        raise AlqorXəta("ArqumentXətası",
                        f"`{self.ad}` ({self.növ}) komponentində `{ad}` "
                        "yoxdur", yer, "ALQ-T006")

    def alqor_üzv_qoy(self, icraçı, ad: str, dəyər: Any, yer) -> None:
        if ad not in self.XASSƏLƏR:
            raise AlqorXəta("ArqumentXətası",
                            f"`{self.növ}` komponentinin `{ad}` xassəsi "
                            "yoxdur", yer, "ALQ-T006")
        self.xassələr[ad] = dəyər
        self.dəyişdi(ad)

    def dəyişdi(self, ad: str) -> None:
        pass


# ═══════════════════════════════════════════════════════════════════════
#  VerilənlərBazası
# ═══════════════════════════════════════════════════════════════════════

class VerilənlərBazası(GörünməyənKomponent):
    ALQOR_TİP_ADI = "VerilənlərBazası"
    XASSƏLƏR = {
        "növ": ("sqlite", "sqlite · postgres · mysql"),
        "fayl": ("məlumat.db", "SQLite faylı (forma qovluğuna görə)"),
        "host": ("localhost", "server (postgres, mysql)"),
        "port": (None, "port; boşdursa standart (5432 / 3306)"),
        "baza": ("", "bazanın adı (postgres, mysql)"),
        "istifadəçi": ("", "istifadəçi adı"),
        "parolMühiti": ("", "parolu saxlayan mühit dəyişəni — parol "
                        "forma faylına yazılmır"),
        "ünvan": ("", "tam ünvan (verilibsə yuxarıdakıları əvəzləyir); "
                  "məs. postgres://u@host/baza"),
        "sxem": ("", "`.sxem` faylı — çatışmayan cədvəllər yaradılır"),
    }
    METODLAR = {
        "sorğu": "SQL sorğusu → sətirlər (lüğət siyahısı)",
        "birSətir": "ilk sətir və ya boş", "birDəyər": "ilk dəyər",
        "icra": "INSERT/UPDATE/DELETE → dəyişən sətir sayı",
        "cədvəl": "sorğu qurucusu: .harada(…).sırala(…).al()",
        "tranzaksiya": "funksiya xəta atsa hamısı geri qaytarılır",
        "bağlantı": "verilənlər.bağlan(…) obyektinin özü",
    }

    def __init__(self, t, sahib):
        super().__init__(t, sahib)
        self._b: Any = None

    def ünvan(self) -> str:
        if self.x("ünvan"):
            return str(self.x("ünvan"))
        növ = str(self.x("növ") or "sqlite").lower()
        if növ == "sqlite":
            fayl = str(self.x("fayl") or "məlumat.db")
            if fayl.startswith(":"):
                return "sqlite::yaddaş:"
            yol = Path(fayl)
            if not yol.is_absolute():
                yol = self.qovluq / yol
            return f"sqlite://{yol}"
        if növ not in ("postgres", "mysql"):
            raise _xəta(f"`{self.ad}.növ` sqlite, postgres və ya mysql "
                        f"olmalıdır, `{növ}` verilib")
        from urllib.parse import quote
        parol = ""
        if self.x("parolMühiti"):
            parol = os.environ.get(str(self.x("parolMühiti")), "")
        istifadəçi = quote(str(self.x("istifadəçi") or ""), safe="")
        hesab = istifadəçi + (":" + quote(parol, safe="") if parol else "")
        port = self.x("port") or (5432 if növ == "postgres" else 3306)
        return (f"{növ}://{hesab + '@' if hesab else ''}"
                f"{self.x('host') or 'localhost'}:{port}/"
                f"{self.x('baza') or ''}")

    def bağlantı(self) -> Any:
        if self._b is None:
            from .modullar.verilenler import bağlan
            self._b = bağlan(self.ünvan())
            if self.x("sxem"):
                self.sxemi_tətbiq_et()
        return self._b

    def sxem(self):
        from . import sxem as S
        from .xeta import XətaToplayıcı
        if not self.x("sxem"):
            return None
        yol = Path(str(self.x("sxem")))
        if not yol.is_absolute():
            yol = self.qovluq / yol
        if not yol.is_file():
            raise _xəta(f"`{self.ad}.sxem`: `{yol.name}` faylı tapılmadı",
                        "ALQ-D006")
        x = XətaToplayıcı()
        s = S.fayldan(yol, x)
        if s is None:
            raise AlqorXəta("SintaksisXətası", f"`{yol.name}` sxemində xəta:"
                            "\n\n" + x.hesabat(False), None, "ALQ-D001")
        return s

    def sxemi_tətbiq_et(self) -> list[str]:
        from . import sxem as S
        s = self.sxem()
        return S.tətbiq_et(self._b, s) if s is not None else []

    def dəyişdi(self, ad: str) -> None:
        if self._b is not None:
            self._b.bağla()
            self._b = None

    def üzv(self, icraçı, ad: str, yer) -> Any:
        if ad == "bağlantı":
            return Daxili("bağlantı", self.bağlantı, 0, 0)
        if ad == "sxemTətbiqEt":
            return Daxili("sxemTətbiqEt",
                          lambda: (self.bağlantı(), self.sxemi_tətbiq_et())[1],
                          0, 0)
        from .kitabxana import daxili_metod
        m = daxili_metod(icraçı, self.bağlantı(), ad)
        if m is None:
            return super().üzv(icraçı, ad, yer)
        return m


# ═══════════════════════════════════════════════════════════════════════
#  Sorğu — cədvəl + kursor (cari sətir) + redaktə buferi
# ═══════════════════════════════════════════════════════════════════════

class Sorğu(GörünməyənKomponent):
    ALQOR_TİP_ADI = "Sorğu"
    XASSƏLƏR = {
        "baza": (None, "VerilənlərBazası komponenti"),
        "cədvəl": ("", "cədvəlin adı"),
        "süzgəc": ({}, "bərabərlik şərtləri: {\"sinif\": 5}"),
        "sırala": ("", "sıralama sütunu"),
        "azalan": (False, "azalan sıra"),
        "limit": (None, "ən çox neçə sətir"),
    }
    METODLAR = {
        "yenilə": "sətirləri bazadan yenidən oxuyur",
        "ilk": "ilk sətrə keç", "əvvəlki": "əvvəlki sətrə keç",
        "növbəti": "növbəti sətrə keç", "son": "son sətrə keç",
        "keç": "N-ci sətrə keç (0-dan)",
        "əlavəEt": "yeni boş sətir (saxla() ilə yazılır)",
        "saxla": "cari sətrin dəyişikliklərini bazaya yazır",
        "sil": "cari sətri bazadan silir",
        "ləğvEt": "saxlanmamış dəyişiklikləri atır",
        "dəyər": "cari sətrin sütunu", "dəyiş": "cari sətrin sütununu dəyiş",
    }

    def __init__(self, t, sahib):
        super().__init__(t, sahib)
        self.sətirlər: list[dict] = []
        self.indeks = 0
        self.bufer: dict[str, Any] = {}
        self.yeni = False
        self.açıq = False

    # ── köməkçilər ────────────────────────────────────────────────────
    def baza(self) -> VerilənlərBazası:
        b = self.x("baza")
        if isinstance(b, İstinad):
            b = self.sahib.sahələr.get(b.ad)
        if not isinstance(b, VerilənlərBazası):
            raise _xəta(f"`{self.ad}.baza` VerilənlərBazası komponenti "
                        "olmalıdır", "ALQ-D007")
        return b

    def _cədvəl(self) -> str:
        c = self.x("cədvəl")
        if not c:
            raise _xəta(f"`{self.ad}.cədvəl` verilməyib", "ALQ-D007")
        return str(c)

    def açar(self) -> str:
        try:
            s = self.baza().sxem()
        except AlqorXəta:
            s = None
        if s is not None:
            c = s.cədvəl(self._cədvəl())
            if c is not None and c.açar() is not None:
                return c.açar().ad
        for x in self.baza().bağlantı().sütunlar(self._cədvəl()):
            if x.get("açar"):
                return x["ad"]
        return "id"

    def sütunlar(self) -> list[str]:
        try:
            s = self.baza().sxem()
        except AlqorXəta:
            s = None
        if s is not None and s.cədvəl(self._cədvəl()) is not None:
            return [f.ad for f in s.cədvəl(self._cədvəl()).sahələr]
        return [x["ad"] for x in
                self.baza().bağlantı().sütunlar(self._cədvəl())]

    def aç(self) -> None:
        if not self.açıq:
            self.yenilə()

    def yenilə(self) -> None:
        from .modullar.verilenler import Qurucu
        q = Qurucu(self.baza().bağlantı(), self._cədvəl())
        süzgəc = self.x("süzgəc") or {}
        if isinstance(süzgəc, dict):
            for k, v in süzgəc.items():
                q = q.harada(str(k), "=", v)
        if self.x("sırala"):
            q = q.sırala(str(self.x("sırala")),
                         "azalan" if self.x("azalan") else "artan")
        if self.x("limit"):
            q = q.limit(int(self.x("limit")))
        self.sətirlər = q.al()
        self.açıq = True
        self.bufer, self.yeni = {}, False
        self.indeks = max(0, min(self.indeks, len(self.sətirlər) - 1))

    def cari(self) -> dict | None:
        self.aç()
        if self.yeni:
            return dict(self.bufer)
        if not self.sətirlər:
            return None
        return {**self.sətirlər[self.indeks], **self.bufer}

    def dəyər(self, sütun: str) -> Any:
        c = self.cari()
        return None if c is None else c.get(str(sütun))

    def _sxem_sahəsi(self, sütun: str):
        try:
            s = self.baza().sxem()
        except AlqorXəta:
            return None
        c = s.cədvəl(self._cədvəl()) if s is not None else None
        return c.sahə(sütun) if c is not None else None

    def dəyiş(self, sütun: str, dəyər: Any) -> None:
        self.aç()
        if not self.sətirlər and not self.yeni:
            self.əlavə_et()
        f = self._sxem_sahəsi(str(sütun))
        if f is not None and isinstance(dəyər, str):
            dəyər = _çevir(dəyər, f.tip)
        self.bufer[str(sütun)] = dəyər

    def keç(self, i: int) -> None:
        self.aç()
        self.bufer, self.yeni = {}, False
        if self.sətirlər:
            self.indeks = max(0, min(int(i), len(self.sətirlər) - 1))

    def əlavə_et(self) -> None:
        self.aç()
        self.yeni = True
        self.bufer = {}
        try:
            s = self.baza().sxem()
            c = s.cədvəl(self._cədvəl()) if s else None
            if c is not None:
                for f in c.sahələr:
                    if f.standart_var:
                        self.bufer[f.ad] = f.standart
        except AlqorXəta:
            pass

    def saxla(self) -> Any:
        from .modullar.verilenler import Qurucu
        self.aç()
        b = self.baza().bağlantı()
        açar = self.açar()
        if self.yeni:
            sətir = {k: v for k, v in self.bufer.items() if k != açar}
            yeni_id = Qurucu(b, self._cədvəl()).əlavə_et(sətir)
            self.yenilə()
            for i, s in enumerate(self.sətirlər):
                if s.get(açar) == yeni_id:
                    self.indeks = i
                    break
            return yeni_id
        if not self.bufer or not self.sətirlər:
            return None
        id_ = self.sətirlər[self.indeks].get(açar)
        Qurucu(b, self._cədvəl()).harada(açar, "=", id_).yenilə(
            {k: v for k, v in self.bufer.items() if k != açar})
        self.yenilə()
        return id_

    def sil(self) -> None:
        from .modullar.verilenler import Qurucu
        self.aç()
        if self.yeni:
            self.bufer, self.yeni = {}, False
            return
        if not self.sətirlər:
            return
        açar = self.açar()
        id_ = self.sətirlər[self.indeks].get(açar)
        Qurucu(self.baza().bağlantı(), self._cədvəl()).harada(
            açar, "=", id_).sil()
        self.yenilə()

    def dəyişdi(self, ad: str) -> None:
        self.açıq = False

    def üzv(self, icraçı, ad: str, yer) -> Any:
        sadə = {
            "cari": lambda: self.cari(),
            "sətirlər": lambda: (self.aç(), list(self.sətirlər))[1],
            "say": lambda: (self.aç(), len(self.sətirlər))[1],
            "indeks": lambda: self.indeks,
            "boşdur": lambda: (self.aç(), not self.sətirlər)[1],
            "yenidir": lambda: self.yeni,
            "dəyişib": lambda: bool(self.bufer) or self.yeni,
        }
        if ad in sadə:
            return sadə[ad]()
        n = len(self.sətirlər)
        metodlar = {
            "yenilə": (lambda: self.yenilə(), 0, 0),
            "ilk": (lambda: self.keç(0), 0, 0),
            "son": (lambda: (self.aç(), self.keç(len(self.sətirlər) - 1)), 0, 0),
            "əvvəlki": (lambda: self.keç(self.indeks - 1), 0, 0),
            "növbəti": (lambda: self.keç(self.indeks + 1), 0, 0),
            "keç": (lambda i: self.keç(i), 1, 1),
            "əlavəEt": (lambda: self.əlavə_et(), 0, 0),
            "saxla": (lambda: self.saxla(), 0, 0),
            "sil": (lambda: self.sil(), 0, 0),
            "ləğvEt": (lambda: (self.bufer.clear(),
                                setattr(self, "yeni", False)), 0, 0),
            "dəyər": (lambda s: self.dəyər(s), 1, 1),
            "dəyiş": (lambda s, d: self.dəyiş(s, d), 2, 2),
            "sütunlar": (lambda: self.sütunlar(), 0, 0),
        }
        _ = n
        if ad in metodlar:
            f, a, b = metodlar[ad]

            def sarğı(*arq, _f=f):
                r = _f(*arq)
                return r if ad in ("saxla", "dəyər", "sütunlar") else None
            return Daxili(f"{self.ad}.{ad}", sarğı, a, b)
        return super().üzv(icraçı, ad, yer)


def _çevir(m: str, tip: str) -> Any:
    """Giriş sahəsindən gələn mətn → sxemdəki tip (alınmasa mətn qalır)."""
    t = m.strip()
    if t == "" and tip in ("tam", "onluq", "tarix", "tarixVaxt"):
        return None
    try:
        if tip == "tam":
            return int(t)
        if tip == "onluq":
            return float(t.replace(",", "."))
    except ValueError:
        return m
    if tip == "məntiq":
        return t.lower() in ("doğru", "true", "1", "hə", "on", "bəli")
    return m


KOMPONENTLƏR: dict[str, type[GörünməyənKomponent]] = {
    "VerilənlərBazası": VerilənlərBazası,
    "Sorğu": Sorğu,
}


# ═══════════════════════════════════════════════════════════════════════
#  Bağlama (forma.göstər çağırır)
# ═══════════════════════════════════════════════════════════════════════

#  Göstərici vidjetlər üçün dəyər xassəsi (sahə yoxdursa)
_GÖSTƏRİCİ = ("dəyər", "mətn", "məzmun")


def bağla(icraçı, o: FormaObyekti, sorğu: Sorğu, adlı: dict,
          hadisələr: list[str], dəyər_xassəsi: str | None,
          idarəedici) -> None:
    """Vidjetin arqumentlərini sorğunun cari sətri ilə doldurur."""
    if o.növ == "cədvəl":
        sorğu.aç()
        sütunlar = o.xassələr.get("sütunlar")
        if not sütunlar:
            açarlar = sorğu.sütunlar()
            sütunlar = [[a, a] for a in açarlar]
        adlı.setdefault("sütunlar", sütunlar)
        adlı["sətirlər"] = list(sorğu.sətirlər)
        istifadəçi = adlı.get("sətirKlik")

        def seç(dəyər=None, *_):
            try:
                sorğu.keç(int(str(dəyər)))
            except (TypeError, ValueError):
                pass
            if istifadəçi is not None:
                istifadəçi.çağır(icraçı, [dəyər], {})
        adlı["sətirKlik"] = Daxili(f"{o.ad}.sətirKlik", seç, 0, 1)
        return
    sütun = o.xassələr.get("sütun")
    if not sütun:
        return
    sütun = str(sütun)
    dəyər = sorğu.dəyər(sütun)
    if dəyər_xassəsi is not None:
        adlı[dəyər_xassəsi] = dəyər
        for h in ("yazıldı", "dəyişdi"):
            if h not in hadisələr:
                continue
            istifadəçi = adlı.get(h)

            def yaz(d=None, *_, _i=istifadəçi):
                sorğu.dəyiş(sütun, d)
                if _i is not None:
                    _i.çağır(icraçı, [d], {})
            adlı[h] = Daxili(f"{o.ad}.{h}", yaz, 0, 1)
        return
    for p in _GÖSTƏRİCİ:
        if p in o._icazəli:
            adlı[p] = "" if dəyər is None else mətnə(dəyər, icraçı)
            return


def sətri_işarələ(e: Element, indeks: int) -> None:
    """Cədvəl vidjetində cari sətrin vurğulanması."""
    def gəz(x):
        if not isinstance(x, Element):
            return None
        if x.ad == "tbody":
            return x
        for u in x.uşaqlar:
            r = gəz(u)
            if r is not None:
                return r
        return None
    tbody = gəz(e)
    if tbody is None:
        return
    sətirlər = [u for u in tbody.uşaqlar if isinstance(u, Element)]
    if 0 <= indeks < len(sətirlər):
        tr = sətirlər[indeks]
        tr.atributlar["class"] = ((tr.atributlar.get("class") or "") +
                                  " a-sətir--cari").strip()
        tr.atributlar["aria-selected"] = "true"
        tr.atributlar["style"] = ("background:color-mix(in srgb,"
                                  "var(--a-vurğu,#2563eb) 14%,transparent)")


_NAV_DÜYMƏLƏRİ = [
    ("ilk", "⏮", "İlk"), ("əvvəlki", "◀", "Əvvəlki"),
    ("növbəti", "▶", "Növbəti"), ("son", "⏭", "Son"),
    ("əlavəEt", "＋", "Yeni"), ("sil", "🗑", "Sil"),
    ("saxla", "💾", "Saxla"), ("ləğvEt", "↶", "Ləğv et"),
    ("yenilə", "↻", "Yenilə"),
]


def naviqator(icraçı, o: FormaObyekti, sorğu: Sorğu | None) -> Element:
    """Delphi TDBNavigator: sorğunun sətirləri arasında gəzmək."""
    from . import vidjet as V
    seçilmiş = o.xassələr.get("düymələr")
    düymələr = []
    for ad, ikon, izah in _NAV_DÜYMƏLƏRİ:
        if seçilmiş and ad not in seçilmiş:
            continue

        def işlə(*_, _ad=ad):
            if sorğu is None:
                return
            {"ilk": lambda: sorğu.keç(0),
             "son": lambda: (sorğu.aç(), sorğu.keç(len(sorğu.sətirlər) - 1)),
             "əvvəlki": lambda: sorğu.keç(sorğu.indeks - 1),
             "növbəti": lambda: sorğu.keç(sorğu.indeks + 1),
             "əlavəEt": sorğu.əlavə_et, "sil": sorğu.sil,
             "saxla": sorğu.saxla,
             "ləğvEt": lambda: (sorğu.bufer.clear(),
                                setattr(sorğu, "yeni", False)),
             "yenilə": sorğu.yenilə}[_ad]()
        e = V.düymə(icraçı, mətn=ikon, növ="ikinci", ölçü="kiçik",
                    klik=Daxili(f"{o.ad}.{ad}", işlə, 0, 1))
        e.atributlar["title"] = izah
        e.atributlar["aria-label"] = izah
        e.atributlar["data-nav"] = ad
        düymələr.append(e)
    if sorğu is not None:
        sorğu.aç()
        mövqe = ("yeni" if sorğu.yeni else
                 f"{sorğu.indeks + 1} / {len(sorğu.sətirlər)}"
                 if sorğu.sətirlər else "0 / 0")
        düymələr.append(Element("span", {"class": "a-nav-mövqe",
                                         "style": "margin-left:8px;"
                                         "opacity:.7"}, [mövqe]))
    return V.sətir(icraçı, məzmun=düymələr, boşluq=4)


# ═══════════════════════════════════════════════════════════════════════
#  «Cədvəldən forma yarat» sehrbazı (Delphi Database Form Wizard)
# ═══════════════════════════════════════════════════════════════════════

#  Sxem tipi → giriş vidjeti
_GİRİŞ_VİDJETİ = {"tam": "ədəd", "onluq": "ədəd", "mətn": "sahə",
                  "məntiq": "açar", "tarix": "tarix",
                  "tarixVaxt": "tarixVaxt", "bayt": None}


def _obyekt_adı(söz: str) -> str:
    from .elifba import böyüyə
    hissələr = [h for h in str(söz).split("_") if h]
    return "".join(böyüyə(h[:1]) + h[1:] for h in hissələr) or "Sahə"


def crud_obyektləri(sxem: Any, cədvəl: str, baza: str = "Baza1",
                    mövcud: set[str] | None = None) -> list[ObyektTəsviri]:
    """Cədvəl üçün hazır redaktə forması: Sorğu, siyahı, hər sahə üçün
    giriş elementi və naviqator. `mövcud` — formadakı adlar (təkrarsız)."""
    c = sxem.cədvəl(cədvəl)
    if c is None:
        raise ValueError(f"`{cədvəl}` cədvəli sxemdə yoxdur")
    adlar = set(mövcud or ())

    def ad(təklif: str) -> str:
        n, i = təklif, 2
        while n in adlar:
            n, i = f"{təklif}{i}", i + 1
        adlar.add(n)
        return n

    sorğu = ad(_obyekt_adı(cədvəl))
    n = [ObyektTəsviri(sorğu, "Sorğu", {
        "baza": İstinad(baza), "cədvəl": cədvəl,
        **({"sırala": c.sahələr[1].ad} if len(c.sahələr) > 1 else {})})]
    n.append(ObyektTəsviri(ad(sorğu + "Siyahısı"), "cədvəl",
                           {"mənbə": İstinad(sorğu)}))
    sahələr = []
    for f in c.sahələr:
        if f.açar:
            continue
        növ = _GİRİŞ_VİDJETİ.get(f.tip)
        if növ is None:
            continue
        from .elifba import böyüyə
        etiket = f.ad.replace("_", " ")
        x: dict[str, Any] = {"etiket": böyüyə(etiket[:1]) + etiket[1:]}
        if növ != "açar":
            x["ad"] = f.ad
        x["mənbə"] = İstinad(sorğu)
        x["sütun"] = f.ad
        if f.məcburi and növ in ("sahə", "ədəd", "tarix", "tarixVaxt"):
            x["tələb"] = True
        sahələr.append(ObyektTəsviri(ad(_obyekt_adı(f.ad) + "Sahəsi"),
                                     növ, x))
    n.append(ObyektTəsviri(ad(sorğu + "Sahələri"), "tor",
                           {"sütunlar": 2}, sahələr))
    n.append(ObyektTəsviri(ad(sorğu + "Naviqator"), "naviqator",
                           {"mənbə": İstinad(sorğu)}))
    return n
