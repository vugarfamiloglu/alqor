"""
Alqor — İnterpretator (ağac gəzən icraçı).

AAC-ni birbaşa icra edir. Kompilyasiya mərhələsi yoxdur —
`alqor işlət proqram.alq` dərhal nəticə verir.
"""

from __future__ import annotations
import math
import sys
import threading
from typing import Any

from . import aac as A
from .deyerler import (AlqorDiapazon, AlqorGenerator, AlqorXəta, BağlıMetod,
                       Element,
                       Çağırılan, Daxili, DavamSiqnalı, DayanmaSiqnalı,
                       DayanSiqnalı, Funksiya, Modul, Mühit, Nümunə,
                       QaytarSiqnalı, Sadalama, SadalamaDəyəri, Sinif,
                       VerSiqnalı, mətnə, tip_adı, xəta_uyğundur)
from .elifba import böyüyə, kiçiyə
from .korutin import Gələcək, Korutin, LəğvNişanı
from .token import Yer

# Hər Alqor çağırışı ~10 Python kadrı tutur, ona görə Python limitini
# də qaldırırıq. Yoxsa RecursionError bizim `StekDaşmaXətası`-dan əvvəl
# baş verir və Azərbaycan dilində mesaj verilmir.
STEK_HƏDDİ = 1000
_PYTHON_LİMİTİ = 30000


class İcraçı:
    def __init__(self, çıxış=None, giriş=None):
        from .kitabxana import qlobal_mühit
        self.qlobal = qlobal_mühit(self)
        # Bir yazı ilə (mətn + sətir sonu): paralel `gözlə`-də sətirlər qarışmasın
        self.çıxış = çıxış or (lambda s: print(s + "\n", end=""))
        self.giriş = giriş or input
        self.proqram_arqumentləri: list[str] = []
        # Əsas skriptin qovluğu — şablonlar və nisbi yollar buna görə
        # həll olunur, cari iş qovluğuna görə yox
        self.əsas_qovluq = None
        # Vəziyyət SAP-YERLİDİR: korutinlər və `paralel(...)` ayrı
        # saplarda işləyir, ona görə dərinlik sayğacı, `gecikdir`
        # yığını və cari korutin hər sapda müstəqil olmalıdır.
        self._yerli = _SapYerli()
        self.yığın: list[str] = []
        # Debaqçı (`alqor dap`): hər cümlədən əvvəl `cümlə(c, m)`,
        # funksiyaya girib-çıxanda `daxil(f, m)` / `çıx()` çağırılır
        self.izləyici = None
        if sys.getrecursionlimit() < _PYTHON_LİMİTİ:
            sys.setrecursionlimit(_PYTHON_LİMİTİ)

    # ═══════════════════════════════════════════════════════════════════
    #  Giriş nöqtəsi
    # ═══════════════════════════════════════════════════════════════════

    def işlət(self, ağac: A.Proqram, arqumentlər: list[str] | None = None
              ) -> int:
        m = self.qlobal
        # `sistem.arqumentlər()` və `konsol.arqumentlər()` buradan oxuyur
        self.proqram_arqumentləri = list(arqumentlər or [])
        try:
            # 1. Elanları qeydiyyata al (funksiya/sinif irəli istinad etsin)
            self._elanları_qaldır(ağac.gövdə, m)
            # 2. Qalan cümlələri icra et
            for c in ağac.gövdə:
                if not self._elandır(c):
                    self._cümlə(c, m)
            # 3. `əsas()` varsa çağır
            if m.var("əsas"):
                əsas = m.al("əsas")
                if isinstance(əsas, Çağırılan):
                    arq = [list(arqumentlər or [])] \
                        if self._əsas_arqument_alır(əsas) else []
                    nəticə = əsas.çağır(self, arq, {}, None)
                    # `asinxron funksiya əsas()` — nəticəsi gözlənilir
                    if isinstance(nəticə, Gələcək):
                        nəticə = nəticə.al()
                    if isinstance(nəticə, int) and not isinstance(nəticə, bool):
                        return nəticə
            return 0
        except DayanmaSiqnalı as s:
            return s.kod
        except QaytarSiqnalı:
            return 0

    @staticmethod
    def _əsas_arqument_alır(əsas: Any) -> bool:
        return isinstance(əsas, Funksiya) and len(əsas.parametrlər) > 0

    @staticmethod
    def _elandır(c: A.Cümlə) -> bool:
        return isinstance(c, (A.FunksiyaElanı, A.SinifElanı,
                              A.InterfeysElanı, A.SadalamaElanı,
                              A.QarışıqElanı, A.TipAliası, A.İdxal))

    def _elanları_qaldır(self, gövdə: list[A.Cümlə], m: Mühit) -> None:
        """Funksiya və siniflər qarşılıqlı istinad edə bilsin."""
        # `gətir` əvvəl — `sinif X miras modul.Y` modulun sinfini görsün
        for c in gövdə:
            if isinstance(c, A.İdxal):
                self._cümlə(c, m)
        for c in gövdə:
            if isinstance(c, A.FunksiyaElanı):
                self._cümlə(c, m)
        for c in gövdə:
            if isinstance(c, (A.SinifElanı, A.SadalamaElanı,
                              A.InterfeysElanı, A.QarışıqElanı)):
                self._cümlə(c, m)

    # ═══════════════════════════════════════════════════════════════════
    #  Cümlələr
    # ═══════════════════════════════════════════════════════════════════

    def _blok(self, gövdə: list[A.Cümlə], m: Mühit) -> None:
        for c in gövdə:
            self._cümlə(c, m)

    def _cümlə(self, c: A.Cümlə, m: Mühit) -> None:
        if self.izləyici is not None:
            self.izləyici.cümlə(c, m)
        işləyici = _CÜMLƏLƏR.get(type(c))
        if işləyici is None:
            raise AlqorXəta("DaxiliXəta",
                            f"icra olunmayan qovşaq: {type(c).__name__}",
                            getattr(c, "yer", None))
        işləyici(self, c, m)

    # ── İfadə cümləsi ─────────────────────────────────────────────────

    def _c_ifadə(self, c: A.İfadəCümləsi, m: Mühit) -> None:
        self._ifadə(c.ifadə, m)

    # ── Dəyişən elanı ─────────────────────────────────────────────────

    def _c_dəyişən(self, c: A.DəyişənElanı, m: Mühit) -> None:
        sabit = c.növ in ("sabit", "dəyişməz")

        if not c.dəyərlər:
            for b in c.bağlamalar:
                self._bağla(b, self._standart_dəyər(b), m, elan=True,
                            sabit=sabit)
            return

        if len(c.bağlamalar) == 1:
            dəyər = (self._ifadə(c.dəyərlər[0], m) if len(c.dəyərlər) == 1
                     else [self._ifadə(d, m) for d in c.dəyərlər])
            self._bağla(c.bağlamalar[0], dəyər, m, elan=True, sabit=sabit)
            return

        if len(c.dəyərlər) == 1:
            dəyər = self._ifadə(c.dəyərlər[0], m)
            self._çoxlu_bağla(c.bağlamalar, dəyər, m, elan=True,
                              sabit=sabit, yer=c.yer)
            return

        if len(c.dəyərlər) != len(c.bağlamalar):
            raise AlqorXəta(
                "ArqumentXətası",
                f"{len(c.bağlamalar)} ad, {len(c.dəyərlər)} dəyər — "
                "saylar uyğun gəlmir", c.yer, "ALQ-T001")
        dəyərlər = [self._ifadə(d, m) for d in c.dəyərlər]
        for b, d in zip(c.bağlamalar, dəyərlər):
            self._bağla(b, d, m, elan=True, sabit=sabit)

    @staticmethod
    def _standart_dəyər(b: A.Bağlama) -> Any:
        t = b.tip
        if isinstance(t, A.TipAdı) and not t.ixtiyari:
            return {"tam": 0, "onluq": 0.0, "mətn": "", "məntiq": False,
                    "siyahı": [], "lüğət": {}, "dəst": set(),
                    "bayt": b""}.get(t.tam_ad, None)
        return None

    # ── Dəyər semantikası və tip genişlənməsi ─────────────────────────

    @staticmethod
    def _dəyər_kopyası(dəyər: Any) -> Any:
        """
        Strukturlar DƏYƏR tipidir (Spes. § 6.9) — mənimsətmə və arqument
        ötürülməsində kopyalanır. Siniflər istinadla ötürülür.
        """
        if isinstance(dəyər, Nümunə) and dəyər.sinif.quruluş == "struktur":
            return dəyər.klonla()
        return dəyər

    @staticmethod
    def _genişlət(dəyər: Any, tip: Any) -> Any:
        """
        İmplisit genişlənmə (Spes. § 2.8): `tam` → `onluq`.
        `onluq` elan olunmuş yerə `3` verilsə, `3.0` olur.
        """
        if (isinstance(tip, A.TipAdı) and tip.tam_ad == "onluq"
                and isinstance(dəyər, int) and not isinstance(dəyər, bool)):
            return float(dəyər)
        return dəyər

    # ── Bağlama (dağıtma) ─────────────────────────────────────────────

    def _bağla(self, b: A.Bağlama, dəyər: Any, m: Mühit,
               elan: bool = False, sabit: bool = False) -> None:
        if b.növ == "atma":
            return
        if b.növ == "ad":
            dəyər = self._dəyər_kopyası(self._genişlət(dəyər, b.tip))
            if elan:
                m.elan(b.ad, dəyər, sabit)
            else:
                m.təyin(b.ad, dəyər)
            return
        if b.növ == "qalan":
            if elan:
                m.elan(b.ad, dəyər, sabit)
            else:
                m.təyin(b.ad, dəyər)
            return
        if b.növ == "kortej":
            self._çoxlu_bağla(b.alt, dəyər, m, elan, sabit, b.yer)
            return
        if b.növ == "obyekt":
            for ad, alt in b.sahələr:
                sahə = self._üzv_al(dəyər, ad, b.yer)
                if alt is None:
                    if elan:
                        m.elan(ad, sahə, sabit)
                    else:
                        m.təyin(ad, sahə)
                else:
                    self._bağla(alt, sahə, m, elan, sabit)
            return
        raise AlqorXəta("DaxiliXəta", f"naməlum bağlama: {b.növ}", b.yer)

    def _çoxlu_bağla(self, bağlamalar: list[A.Bağlama], dəyər: Any,
                     m: Mühit, elan: bool, sabit: bool,
                     yer: Yer | None) -> None:
        try:
            elementlər = list(self._iterasiya(dəyər, yer))
        except AlqorXəta:
            raise AlqorXəta("TipXətası",
                            f"`{tip_adı(dəyər)}` dağıtıla bilməz", yer,
                            "ALQ-T001")

        qalan_indeks = next((i for i, b in enumerate(bağlamalar)
                             if b.növ == "qalan"), None)

        if qalan_indeks is None:
            if len(elementlər) != len(bağlamalar):
                raise AlqorXəta(
                    "ArqumentXətası",
                    f"{len(bağlamalar)} ad gözlənilirdi, "
                    f"{len(elementlər)} dəyər var", yer, "ALQ-T001")
            for b, d in zip(bağlamalar, elementlər):
                self._bağla(b, d, m, elan, sabit)
            return

        əvvəl = bağlamalar[:qalan_indeks]
        sonra = bağlamalar[qalan_indeks + 1:]
        if len(elementlər) < len(əvvəl) + len(sonra):
            raise AlqorXəta("ArqumentXətası",
                            "dağıtma üçün element çatmır", yer, "ALQ-T001")
        for b, d in zip(əvvəl, elementlər[:len(əvvəl)]):
            self._bağla(b, d, m, elan, sabit)
        orta = elementlər[len(əvvəl):len(elementlər) - len(sonra)]
        self._bağla(bağlamalar[qalan_indeks], orta, m, elan, sabit)
        for b, d in zip(sonra, elementlər[len(elementlər) - len(sonra):]):
            self._bağla(b, d, m, elan, sabit)

    # ── Şərt ──────────────────────────────────────────────────────────

    def _c_şərt(self, c: A.Şərt, m: Mühit) -> None:
        for şərt, gövdə in c.budaqlar:
            if self._məntiq(şərt, m):
                self._blok(gövdə, m.alt())
                return
        if c.yoxsa is not None:
            self._blok(c.yoxsa, m.alt())

    def _c_varsa(self, c: A.Varsa, m: Mühit) -> None:
        alt = m.alt()
        for bağlama, ifadə in c.bağlamalar:
            dəyər = self._ifadə(ifadə, alt)
            if dəyər is None or dəyər is False:
                if c.yoxsa is not None:
                    self._blok(c.yoxsa, m.alt())
                return
            if bağlama is not None:
                self._bağla(bağlama, dəyər, alt, elan=True)
        self._blok(c.gövdə, alt)

    def _c_yoxdursa(self, c: A.Yoxdursa, m: Mühit) -> None:
        hamısı_var = True
        for bağlama, ifadə in c.bağlamalar:
            dəyər = self._ifadə(ifadə, m)
            if dəyər is None or dəyər is False:
                hamısı_var = False
                break
            if bağlama is not None:
                self._bağla(bağlama, dəyər, m, elan=True)
        if not hamısı_var:
            self._blok(c.gövdə, m.alt())

    # ── Seç ───────────────────────────────────────────────────────────

    def _c_seç(self, c: A.Seç, m: Mühit) -> None:
        dəyər = self._ifadə(c.ifadə, m) if c.ifadə is not None else None
        başla = None

        for i, hal in enumerate(c.hallar):
            alt = m.alt()
            if self._hal_uyğundur(hal, c, dəyər, alt):
                başla = i
                break

        if başla is None:
            if c.digər is not None:
                self._blok(c.digər, m.alt())
            return

        # `keç` zənciri
        i = başla
        while i < len(c.hallar):
            hal = c.hallar[i]
            alt = m.alt()
            self._hal_uyğundur(hal, c, dəyər, alt)      # bağlamaları qur
            self._blok(hal.gövdə, alt)
            if not hal.keç:
                return
            i += 1
        if c.digər is not None:
            self._blok(c.digər, m.alt())

    def _hal_uyğundur(self, hal: A.Hal, seç: A.Seç, dəyər: Any,
                      m: Mühit) -> bool:
        for naxış in hal.naxışlar:
            if self._naxış_uyğunlaşdır(naxış, dəyər, seç, m):
                if hal.mühafizə is None or self._məntiq(hal.mühafizə, m):
                    return True
        return False

    def _naxış_uyğunlaşdır(self, n: A.Naxış, dəyər: Any, seç: A.Seç,
                           m: Mühit) -> bool:
        if n.növ == "atma":
            return True

        if n.növ == "literal":
            return self._bərabərdir(self._ifadə(n.dəyər, m), dəyər)

        if n.növ == "şərt":
            return self._məntiq(n.dəyər, m)

        if n.növ == "diapazon":
            b = self._ifadə(n.dəyər, m)
            s = self._ifadə(n.diapazon_son, m)
            if not isinstance(dəyər, (int, float)) or isinstance(dəyər, bool):
                return False
            return b <= dəyər < s if n.diapazon_xaric else b <= dəyər <= s

        if n.növ == "tip":
            return self._tip_uyğundur(dəyər, n.tip, m)

        if n.növ == "ad":
            # Şərtsiz `seç`-də ad sabit kimi, əks halda bağlama kimi
            if seç.ifadə is None:
                return bool(self._dəyər_doğrudur(m.al(n.dəyər)))
            # Sadalama variantı yoxlaması
            if isinstance(dəyər, SadalamaDəyəri) and dəyər.ad == n.dəyər:
                return True
            m.elan(n.dəyər, dəyər)
            return True

        if n.növ == "kortej":
            if not isinstance(dəyər, (tuple, list)):
                return False
            if len(dəyər) != len(n.alt):
                return False
            return all(self._naxış_uyğunlaşdır(alt, d, seç, m)
                       for alt, d in zip(n.alt, dəyər))

        if n.növ == "siyahı":
            if not isinstance(dəyər, list):
                return False
            if n.qalan is None:
                if len(dəyər) != len(n.alt):
                    return False
                return all(self._naxış_uyğunlaşdır(alt, d, seç, m)
                           for alt, d in zip(n.alt, dəyər))
            if len(dəyər) < len(n.alt):
                return False
            for alt, d in zip(n.alt, dəyər[:len(n.alt)]):
                if not self._naxış_uyğunlaşdır(alt, d, seç, m):
                    return False
            m.elan(n.qalan, dəyər[len(n.alt):])
            return True

        if n.növ == "obyekt":
            tip_yolu = n.tip.yol if isinstance(n.tip, A.TipAdı) else []
            if not self._obyekt_naxışı_uyğundur(dəyər, tip_yolu, m):
                return False
            for i, alt in enumerate(n.alt):
                if isinstance(dəyər, SadalamaDəyəri):
                    sahələr = list(dəyər.sahələr.values())
                    if i >= len(sahələr):
                        return False
                    if not self._naxış_uyğunlaşdır(alt, sahələr[i], seç, m):
                        return False
            for ad, alt in n.sahələr:
                sahə = self._üzv_al(dəyər, ad, n.yer)
                if alt is None:
                    m.elan(ad, sahə)
                elif not self._naxış_uyğunlaşdır(alt, sahə, seç, m):
                    return False
            return True

        return False

    def _obyekt_naxışı_uyğundur(self, dəyər: Any, yol: list[str],
                                m: Mühit) -> bool:
        if not yol:
            return True
        if isinstance(dəyər, SadalamaDəyəri):
            return dəyər.ad == yol[-1] or (
                len(yol) >= 2 and dəyər.sadalama.ad == yol[-2]
                and dəyər.ad == yol[-1])
        if isinstance(dəyər, Nümunə):
            try:
                hədəf = m.al(yol[0])
            except AlqorXəta:
                return False
            return isinstance(hədəf, Sinif) and dəyər.sinif.alt_sinifdirmi(hədəf)
        return False

    # ── Dövrlər ───────────────────────────────────────────────────────

    def _c_nə_qədər_ki(self, c: A.NəQədərKi, m: Mühit) -> None:
        while self._məntiq(c.şərt, m):
            if self._dövr_gövdəsi(c.gövdə, m.alt(), c.etiket):
                break

    def _c_həmişə(self, c: A.Həmişə, m: Mühit) -> None:
        while True:
            if self._dövr_gövdəsi(c.gövdə, m.alt(), c.etiket):
                break

    def _c_təkrarla(self, c: A.Təkrarla, m: Mühit) -> None:
        say = self._ifadə(c.say, m)
        if not isinstance(say, int) or isinstance(say, bool):
            raise AlqorXəta("TipXətası",
                            f"`təkrarla` tam ədəd gözləyir, "
                            f"`{tip_adı(say)}` gəlib", c.yer, "ALQ-T001")
        for i in range(1, say + 1):
            alt = m.alt()
            if c.sayğac:
                alt.elan(c.sayğac, i)
            if self._dövr_gövdəsi(c.gövdə, alt, c.etiket):
                break

    def _c_təkrarla_nə_qədər(self, c: A.TəkrarlaNəQədər, m: Mühit) -> None:
        while True:
            if self._dövr_gövdəsi(c.gövdə, m.alt(), c.etiket):
                break
            if not self._məntiq(c.şərt, m):
                break

    def _c_hər(self, c: A.Hər, m: Mühit) -> None:
        mənbə = self._ifadə(c.mənbə, m)
        if c.addım is not None and isinstance(mənbə, AlqorDiapazon):
            addım = self._ifadə(c.addım, m)
            mənbə = AlqorDiapazon(mənbə.başlanğıc, mənbə.son, addım,
                                  mənbə.xaric)

        # Çoxlu bağlama semantikası (Spes. § 4.5):
        #   lüğət + 2 bağlama  → (açar, dəyər)
        #   digər + 2+ bağlama → (indeks, element...)
        #   1 bağlama          → element
        lüğətdir = isinstance(mənbə, dict)
        çoxlu = len(c.bağlamalar) >= 2

        dayandı = False
        for indeks, element in enumerate(self._iterasiya(mənbə, c.yer)):
            if c.asinxron:
                element = self.gözlə(element, c.yer)
            alt = m.alt()
            if çoxlu and lüğətdir:
                self._dövr_bağla(c.bağlamalar,
                                 (element, mənbə[element]), alt, c.yer)
            elif çoxlu:
                self._bağla(c.bağlamalar[0], indeks, alt, elan=True)
                qalan = c.bağlamalar[1:]
                if len(qalan) == 1:
                    self._bağla(qalan[0], element, alt, elan=True)
                else:
                    self._çoxlu_bağla(qalan, element, alt, True, False,
                                      c.yer)
            else:
                self._bağla(c.bağlamalar[0], element, alt, elan=True)
            if c.şərt is not None and not self._məntiq(c.şərt, alt):
                continue
            try:
                self._blok(c.gövdə, alt)
            except DayanSiqnalı as s:
                if s.etiket and s.etiket != c.etiket:
                    raise
                dayandı = True
                break
            except DavamSiqnalı as s:
                if s.etiket and s.etiket != c.etiket:
                    raise
                continue

        if not dayandı and c.yoxsa is not None:
            self._blok(c.yoxsa, m.alt())

    def _dövr_bağla(self, bağlamalar: list[A.Bağlama], element: Any,
                    m: Mühit, yer: Yer | None) -> None:
        if len(bağlamalar) == 1:
            self._bağla(bağlamalar[0], element, m, elan=True)
            return
        self._çoxlu_bağla(bağlamalar, element, m, True, False, yer)

    def _dövr_gövdəsi(self, gövdə: list[A.Cümlə], m: Mühit,
                      etiket: str | None) -> bool:
        """True qaytarırsa dövr dayandırılmalıdır."""
        try:
            self._blok(gövdə, m)
        except DayanSiqnalı as s:
            if s.etiket and s.etiket != etiket:
                raise
            return True
        except DavamSiqnalı as s:
            if s.etiket and s.etiket != etiket:
                raise
        return False

    def _c_dayan(self, c: A.Dayan, m: Mühit) -> None:
        raise DayanSiqnalı(c.etiket)

    def _c_davam(self, c: A.DavamEt, m: Mühit) -> None:
        raise DavamSiqnalı(c.etiket)

    # ── Funksiya axını ────────────────────────────────────────────────

    def _c_qaytar(self, c: A.Qaytar, m: Mühit) -> None:
        if not c.dəyərlər:
            raise QaytarSiqnalı(None)
        if len(c.dəyərlər) == 1:
            raise QaytarSiqnalı(self._ifadə(c.dəyərlər[0], m))
        raise QaytarSiqnalı(tuple(self._ifadə(d, m) for d in c.dəyərlər))

    def _c_ver(self, c: A.Ver, m: Mühit) -> None:
        dəyər = self._ifadə(c.dəyər, m) if c.dəyər is not None else None
        # Generator gövdəsindəyiksə — korutini dayandırıb dəyəri ver.
        # Əks halda `ver` blok ifadəsini dəyərlə bitirir.
        ver = self._yerli.ver
        if ver is not None:
            ver(dəyər)
            return
        raise VerSiqnalı(dəyər)

    def _c_keç(self, c: A.Keç, m: Mühit) -> None:
        pass

    def _c_dayan_nöqtəsi(self, c: A.DayanNöqtəsi, m: Mühit) -> None:
        self.çıxış("⏸ dayanNöqtəsi — debaq hələ qoşulmayıb")

    def _c_global(self, c: A.Global, m: Mühit) -> None:
        for ad in c.adlar:
            m.qloballar.add(ad)

    # ── Xətalar ───────────────────────────────────────────────────────

    def _c_at(self, c: A.At, m: Mühit) -> None:
        if c.ifadə is None:
            raise AlqorXəta("Xəta", "təkrar atılacaq xəta yoxdur", c.yer)
        dəyər = self._ifadə(c.ifadə, m)
        if isinstance(dəyər, Nümunə):
            mesaj = mətnə(dəyər.sahələr.get("mesaj", ""), self)
            raise AlqorXəta(dəyər.sinif.ad, mesaj, c.yer, dəyər=dəyər)
        if isinstance(dəyər, AlqorXəta):
            raise dəyər
        raise AlqorXəta("Xəta", mətnə(dəyər, self), c.yer, dəyər=dəyər)

    def _c_cəhd(self, c: A.Cəhd, m: Mühit) -> None:
        try:
            try:
                self._blok(c.gövdə, m.alt())
            except AlqorXəta as x:
                for tutma in c.tutmalar:
                    if not self._tutma_uyğundur(tutma, x):
                        continue
                    alt = m.alt()
                    if tutma.ad:
                        alt.elan(tutma.ad, self._xəta_obyekti(x))
                    if (tutma.mühafizə is not None
                            and not self._məntiq(tutma.mühafizə, alt)):
                        continue
                    self._blok(tutma.gövdə, alt)
                    return
                raise
        finally:
            if c.nəhayət is not None:
                self._blok(c.nəhayət, m.alt())

    def _tutma_uyğundur(self, tutma: A.Tutma, x: AlqorXəta) -> bool:
        if not tutma.tiplər:
            return True
        for t in tutma.tiplər:
            ad = t.tam_ad if isinstance(t, A.TipAdı) else ""
            if xəta_uyğundur(x.tip, ad):
                return True
        return False

    def _xəta_obyekti(self, x: AlqorXəta) -> Any:
        if x.dəyər is not None:
            return x.dəyər
        s = Sinif(x.tip)
        n = Nümunə(s)
        n.sahələr["mesaj"] = x.mesaj
        n.sahələr["kod"] = x.kod or None
        n.sahələr["tip"] = x.tip
        return n

    def _c_iddia(self, c: A.İddia, m: Mühit) -> None:
        if self._məntiq(c.şərt, m):
            return
        mesaj = (mətnə(self._ifadə(c.mesaj, m), self)
                 if c.mesaj is not None else "iddia pozuldu")
        raise AlqorXəta("İddiaXətası", mesaj, c.yer, "ALQ-R007")

    def _c_təmin(self, c: A.Təmin, m: Mühit) -> None:
        if not self._məntiq(c.şərt, m):
            self._blok(c.gövdə, m.alt())

    def _c_gecikdir(self, c: A.Gecikdir, m: Mühit) -> None:
        yığın = self._yerli.gecikdirilmiş
        if yığın:
            yığın[-1].append((c.ifadə, m))
        else:
            self._ifadə(c.ifadə, m)

    def _c_istifadə(self, c: A.İstifadə, m: Mühit) -> None:
        alt = m.alt()
        açıqlar: list[Any] = []
        xəta: BaseException | None = None
        try:
            for ad, ifadə in c.bağlamalar:
                dəyər = self._ifadə(ifadə, alt)
                # Kontekst meneceri protokolu (Python `with`, § 8.14)
                aç = getattr(type(dəyər), "alqor_kontekst_aç", None)
                bağlanan = aç(dəyər, c.yer) if aç is not None \
                    else NotImplemented
                alt.elan(ad, dəyər if bağlanan is NotImplemented
                         else bağlanan)
                açıqlar.append(dəyər)
            self._blok(c.gövdə, alt)
        except BaseException as x:
            xəta = x
            raise
        finally:
            for dəyər in reversed(açıqlar):
                self._bağla_resurs(dəyər, c.yer, xəta)

    def _bağla_resurs(self, dəyər: Any, yer: Yer | None,
                      xəta: BaseException | None = None) -> None:
        bağla_k = getattr(type(dəyər), "alqor_kontekst_bağla", None)
        if bağla_k is not None:
            bağla_k(dəyər, xəta, yer)
            return
        if isinstance(dəyər, Nümunə):
            metod = dəyər.sinif.metod_tap("bağla")
            if metod is not None:
                self.funksiya_çağır(metod.bağla(dəyər), [], {}, yer)
                return
        bağla = getattr(dəyər, "bağla", None) or getattr(dəyər, "close", None)
        if callable(bağla):
            bağla()

    # ── Elanlar ───────────────────────────────────────────────────────

    def _c_funksiya(self, c: A.FunksiyaElanı, m: Mühit) -> None:
        f = Funksiya(c.ad, c.parametrlər, c.gövdə, m, c.asinxron,
                     c.generator,
                     annotasiyalar=[a.ad for a in c.annotasiyalar])
        if "yaddaşla" in f.annotasiyalar:
            f.yaddaş = {}
        m.elan(c.ad, f)

    def _c_sinif(self, c: A.SinifElanı, m: Mühit) -> None:
        baza = None
        if c.baza is not None:
            baza_dəyəri = self._tip_dəyəri(c.baza, m)
            if not isinstance(baza_dəyəri, Sinif):
                raise AlqorXəta("TipXətası",
                                f"`{c.baza.tam_ad}` sinif deyil", c.yer,
                                "ALQ-T002")
            if baza_dəyəri.son:
                raise AlqorXəta("TipXətası",
                                f"`{baza_dəyəri.ad}` `son` sinifdir, "
                                "miras alına bilməz", c.yer, "ALQ-T055")
            baza = baza_dəyəri

        s = Sinif(c.ad, baza, mücərrəd=c.mücərrəd, son=c.son,
                  quruluş=c.quruluş, mühit=m,
                  annotasiyalar=list(c.annotasiyalar),
                  interfeyslər=[t.tam_ad for t in c.interfeyslər
                                if isinstance(t, A.TipAdı)])

        # Qarışıqları tətbiq et
        for q in c.qarışıqlar:
            qd = self._tip_dəyəri(q, m)
            if isinstance(qd, Sinif):
                s.metodlar.update(qd.metodlar)
                s.statiklər.update(qd.statiklər)
                s.xassələr.extend(qd.xassələr)

        self._sinif_üzvlərini_qur(s, c.üzvlər, m)

        # Mücərrəd metodların tətbiqini yoxla
        if not c.mücərrəd:
            çatışmayan = self._çatışmayan_mücərrədlər(s)
            if çatışmayan:
                raise AlqorXəta(
                    "TipXətası",
                    f"`{s.ad}` mücərrəd metodları tətbiq etmir: "
                    + ", ".join(sorted(çatışmayan)), c.yer, "ALQ-T053")

        # `Ad.forma` — komponentin vizual dizayner faylı
        if c.quruluş == "komponent":
            from . import forma
            yol = forma.komponent_üçün(
                c.ad, getattr(getattr(c.yer, "mənbə", None), "yol", None))
            if yol is not None:
                forma.birləşdir(self, s, yol, c.yer)

        if c.quruluş == "obyekt":
            m.elan(c.ad, self.nümunə_yarat(s, None, [], {}, c.yer))
        else:
            m.elan(c.ad, s)

    def _sinif_üzvlərini_qur(self, s: Sinif, üzvlər: list[A.Cümlə],
                             m: Mühit) -> None:
        for ü in üzvlər:
            if isinstance(ü, A.XassəElanı):
                annot = [a.ad for a in ü.annotasiyalar]
                if ü.oxu_gövdəsi is not None and ü.tənbəl:
                    s.hesablananlar[ü.ad] = Funksiya(
                        ü.ad, [], ü.oxu_gövdəsi, m,
                        annotasiyalar=annot + ["tənbəl"])
                elif ü.oxu_gövdəsi is not None:
                    s.hesablananlar[ü.ad] = Funksiya(
                        ü.ad, [], ü.oxu_gövdəsi, m, annotasiyalar=annot)
                    if ü.yaz_gövdəsi is not None:
                        p = A.Parametr(ü.yer, ü.yaz_parametri or "dəyər")
                        s.yazıcılar[ü.ad] = Funksiya(
                            ü.ad, [p], ü.yaz_gövdəsi, m)
                elif ü.statik:
                    s.statiklər[ü.ad] = (self._ifadə(ü.standart, m)
                                         if ü.standart is not None else None)
                else:
                    s.xassələr.append(ü)
            elif isinstance(ü, A.MetodElanı):
                if ü.mücərrəd:
                    s.mücərrəd_metodlar.add(ü.ad)
                    continue
                annot = [a.ad for a in ü.annotasiyalar]
                if ü.statik:
                    annot.append("statik")
                f = Funksiya(ü.ad, ü.parametrlər, ü.gövdə or [], m,
                             ü.asinxron, ü.generator, sinif=s,
                             annotasiyalar=annot)
                if ü.statik:
                    s.statiklər[ü.ad] = f
                else:
                    s.metodlar[ü.ad] = f
            elif isinstance(ü, A.QurucuElanı):
                f = Funksiya(ü.ad or "<qurucu>", ü.parametrlər, ü.gövdə, m,
                             sinif=s)
                s.quruculər[ü.ad or ""] = f
            elif isinstance(ü, A.DağıdıcıElanı):
                s.dağıdıcı = Funksiya("silinsin", [], ü.gövdə, m, sinif=s)
            else:
                self._cümlə(ü, m)

    @staticmethod
    def _çatışmayan_mücərrədlər(s: Sinif) -> set[str]:
        tələb: set[str] = set()
        zəncir: list[Sinif] = []
        cari: Sinif | None = s
        while cari is not None:
            zəncir.append(cari)
            cari = cari.baza
        for c in zəncir:
            tələb |= c.mücərrəd_metodlar
        return {ad for ad in tələb if s.metod_tap(ad) is None}

    def _c_interfeys(self, c: A.InterfeysElanı, m: Mühit) -> None:
        s = Sinif(c.ad, mücərrəd=True, quruluş="interfeys", mühit=m)
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı):
                if ü.mücərrəd or ü.gövdə is None:
                    s.mücərrəd_metodlar.add(ü.ad)
                else:
                    s.metodlar[ü.ad] = Funksiya(
                        ü.ad, ü.parametrlər, ü.gövdə, m, sinif=s)
        m.elan(c.ad, s)

    def _c_qarışıq(self, c: A.QarışıqElanı, m: Mühit) -> None:
        s = Sinif(c.ad, quruluş="qarışıq", mühit=m)
        self._sinif_üzvlərini_qur(s, c.üzvlər, m)
        m.elan(c.ad, s)

    def _c_sadalama(self, c: A.SadalamaElanı, m: Mühit) -> None:
        e = Sadalama(c.ad)
        növbəti_dəyər = 0
        for i, v in enumerate(c.variantlar):
            dəyər: Any = None
            if v.dəyər is not None:
                dəyər = self._ifadə(v.dəyər, m)
                if isinstance(dəyər, int) and not isinstance(dəyər, bool):
                    növbəti_dəyər = dəyər + 1
            elif c.əsas_tip is not None:
                dəyər = növbəti_dəyər
                növbəti_dəyər += 1

            sahələr: dict[str, Any] = {}
            if v.arqumentlər:
                # Zəngin sadalama: dəyərlər qurucu parametrlərinə uyğun
                qurucu_p = [p for ü in c.üzvlər
                            if isinstance(ü, A.QurucuElanı)
                            for p in ü.parametrlər]
                for j, arq in enumerate(v.arqumentlər):
                    ad = (qurucu_p[j].ad if j < len(qurucu_p)
                          else f"_{j}")
                    sahələr[ad] = self._ifadə(arq.dəyər, m)
            if v.parametrlər:
                # Cəbri sadalama — variant çağırışla yaradılır
                sahələr = {}

            sd = SadalamaDəyəri(e, v.ad, i, dəyər, sahələr)
            if v.parametrlər:
                e.variantlar[v.ad] = _VariantQurucusu(e, v, i)  # type: ignore
            else:
                e.variantlar[v.ad] = sd
            e.sıra.append(v.ad)

        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                e.metodlar[ü.ad] = Funksiya(ü.ad, ü.parametrlər, ü.gövdə, m)
        m.elan(c.ad, e)

    def _c_tip_aliası(self, c: A.TipAliası, m: Mühit) -> None:
        m.elan(c.ad, _TipAliası(c.ad, c.tip))

    def _c_genişlətmə(self, c: A.Genişlətmə, m: Mühit) -> None:
        from .kitabxana import genişlətmə_qeyd
        ad = c.tip.tam_ad if isinstance(c.tip, A.TipAdı) else ""
        for ü in c.üzvlər:
            if isinstance(ü, A.MetodElanı) and ü.gövdə is not None:
                genişlətmə_qeyd(ad, ü.ad,
                                Funksiya(ü.ad, ü.parametrlər, ü.gövdə, m))

    def _c_modul(self, c: A.ModulElanı, m: Mühit) -> None:
        alt = m.alt()
        self._elanları_qaldır(c.gövdə, alt)
        for cümlə in c.gövdə:
            if not self._elandır(cümlə):
                self._cümlə(cümlə, alt)
        m.elan(c.ad, Modul(c.ad, dict(alt.adlar)))

    def _c_idxal(self, c: A.İdxal, m: Mühit) -> None:
        if c.python:
            self._python_idxal(c, m)
            return
        from .kitabxana import modul_yüklə
        ad = c.mətn_yolu or ".".join(c.yol)
        modul = modul_yüklə(self, ad, c.yer)

        if c.hamısı:
            for a, d in modul.üzvlər.items():
                m.elan(a, d)
            return
        if c.elementlər:
            for e in c.elementlər:
                if e.ad not in modul.üzvlər:
                    raise AlqorXəta(
                        "ArqumentXətası",
                        f"`{ad}` modulunda `{e.ad}` ixracı yoxdur",
                        c.yer, "ALQ-M002")
                m.elan(e.ləqəb or e.ad, modul.üzvlər[e.ad])
            return
        m.elan(c.ləqəb or (c.yol[-1] if c.yol else modul.ad), modul)

    def _python_idxal(self, c: A.İdxal, m: Mühit) -> None:
        """`gətir python:numpy kimi np` (§ 8.14)."""
        from . import python_korpu as P
        from .kitabxana import _idxal_bazası
        ad = ".".join(c.yol)
        modul = P.modul_yüklə(ad, c.yer, _idxal_bazası(self, c.yer))
        if c.hamısı:
            for a, d in P.hamısı(modul).items():
                m.elan(a, d)
            return
        if c.elementlər:
            for e in c.elementlər:
                m.elan(e.ləqəb or e.ad, P.üzv(modul, ad, e.ad, c.yer))
            return
        m.elan(c.ləqəb or c.yol[-1], modul)

    def _c_ixrac_siyahısı(self, c: A.İxracSiyahısı, m: Mühit) -> None:
        pass

    def _c_başlanğıc(self, c: A.Başlanğıc, m: Mühit) -> None:
        self._blok(c.gövdə, m.alt())

    def _c_bitiş(self, c: A.Bitiş, m: Mühit) -> None:
        pass

    def _c_artırma(self, c: A.Artırma, m: Mühit) -> None:
        cari = self._ifadə(c.hədəf, m)
        if not isinstance(cari, (int, float)) or isinstance(cari, bool):
            raise AlqorXəta("TipXətası",
                            f"`{c.op}` ədəd gözləyir, "
                            f"`{tip_adı(cari)}` gəlib", c.yer, "ALQ-T008")
        yeni = cari + (1 if c.op == "++" else -1)
        self._mənimsət(c.hədəf, yeni, m)

    # ═══════════════════════════════════════════════════════════════════
    #  İfadələr
    # ═══════════════════════════════════════════════════════════════════

    def _ifadə(self, e: A.İfadə, m: Mühit) -> Any:
        işləyici = _İFADƏLƏR.get(type(e))
        if işləyici is None:
            raise AlqorXəta("DaxiliXəta",
                            f"hesablanmayan qovşaq: {type(e).__name__}",
                            getattr(e, "yer", None))
        return işləyici(self, e, m)

    def _e_literal(self, e: A.Literal, m: Mühit) -> Any:
        return e.dəyər

    def _e_şablon(self, e: A.ŞablonMətn, m: Mühit) -> str:
        hissələr: list[str] = []
        for p in e.parçalar:
            if isinstance(p, A.MətnHissəsi):
                hissələr.append(p.dəyər)
            else:
                dəyər = self._ifadə(p.ifadə, m)
                hissələr.append(self._formatla(dəyər, p.format))
        return "".join(hissələr)

    def _formatla(self, dəyər: Any, format: str | None) -> str:
        if not format:
            return mətnə(dəyər, self)
        try:
            if format.endswith(",az"):
                n = float(dəyər)
                əsas = f"{n:,.0f}" if n == int(n) else f"{n:,.2f}"
                return (əsas.replace(",", " ")
                             .replace(".", ","))
            if format == ",":
                return f"{dəyər:,}"
            if format.startswith(".") and format[1:].isdigit():
                return f"{float(dəyər):.{int(format[1:])}f}"
            if format in ("x", "X", "b", "o"):
                return format_spec_tam(dəyər, format)
            return format_spec_ümumi(dəyər, format)
        except (ValueError, TypeError):
            return mətnə(dəyər, self)

    def _e_ad(self, e: A.Ad, m: Mühit) -> Any:
        return m.al(e.ad)

    def _e_özü(self, e: A.Özü, m: Mühit) -> Any:
        return m.al("özü")

    def _e_üst(self, e: A.Üst, m: Mühit) -> Any:
        return _Üst(m.al("özü"), m.al("__sinif__"))

    # ── Operatorlar ───────────────────────────────────────────────────

    def _e_ikili(self, e: A.İkili, m: Mühit) -> Any:
        op = e.op

        # Qısa qapanma
        if op in ("və", "&&"):
            return (self._məntiq(e.sağ, m)
                    if self._məntiq(e.sol, m) else False)
        if op in ("və ya", "||"):
            return (True if self._məntiq(e.sol, m)
                    else self._məntiq(e.sağ, m))
        if op == "??":
            sol = self._ifadə(e.sol, m)
            return self._ifadə(e.sağ, m) if sol is None else sol

        sol = self._ifadə(e.sol, m)
        sağ = self._ifadə(e.sağ, m)
        return self._ikili_hesabla(op, sol, sağ, e.yer)

    def _ikili_hesabla(self, op: str, sol: Any, sağ: Any,
                       yer: Yer | None) -> Any:
        # Bərabərlik
        if op == "==":
            return self._bərabərdir(sol, sağ)
        if op == "!=":
            return not self._bərabərdir(sol, sağ)

        # Nümunə operator yükləməsi
        if isinstance(sol, Nümunə):
            metod_adı = _OPERATOR_METODLARI.get(op)
            if metod_adı:
                metod = sol.sinif.metod_tap(metod_adı)
                if metod is not None:
                    return self.funksiya_çağır(metod.bağla(sol), [sağ], {},
                                               yer)

        # Kitabxana obyektlərinin operatorları (məs. `pul`):
        # `alqor_operator(op, digər, sağdadır)` → nəticə / NotImplemented
        n = _kitabxana_operatoru(op, sol, sağ)
        if n is not NotImplemented:
            return n

        # Müqayisə
        if op in ("<", ">", "<=", ">=", "<=>"):
            return self._müqayisə(op, sol, sağ, yer)

        # Mətn
        if isinstance(sol, str) and not isinstance(sol, bool):
            if op == "+":
                if not isinstance(sağ, str):
                    raise AlqorXəta(
                        "TipXətası",
                        f"`mətn` və `{tip_adı(sağ)}` toplanmır", yer,
                        "ALQ-T008")
                return sol + sağ
            if op == "*":
                if not isinstance(sağ, int) or isinstance(sağ, bool):
                    raise AlqorXəta("TipXətası",
                                    "mətn yalnız tam ədədə vurula bilər",
                                    yer, "ALQ-T008")
                return sol * sağ

        # Kolleksiya
        if isinstance(sol, list) and op == "+":
            if not isinstance(sağ, list):
                raise AlqorXəta("TipXətası",
                                f"`siyahı` və `{tip_adı(sağ)}` toplanmır",
                                yer, "ALQ-T008")
            return sol + sağ
        if isinstance(sol, list) and op == "*" and isinstance(sağ, int):
            return sol * sağ
        if isinstance(sol, set) and op in ("|", "&", "-", "^"):
            if not isinstance(sağ, set):
                raise AlqorXəta("TipXətası", "dəst əməliyyatı dəst tələb edir",
                                yer, "ALQ-T008")
            return {"|": sol | sağ, "&": sol & sağ,
                    "-": sol - sağ, "^": sol ^ sağ}[op]

        # Ədədi
        if not self._ədəddir(sol) or not self._ədəddir(sağ):
            raise AlqorXəta(
                "TipXətası",
                f"`{op}` operatoru `{tip_adı(sol)}` və `{tip_adı(sağ)}` "
                "tiplərinə tətbiq edilmir", yer, "ALQ-T008")

        if op == "+":
            return sol + sağ
        if op == "-":
            return sol - sağ
        if op == "*":
            return sol * sağ
        if op == "/":
            if sağ == 0:
                if isinstance(sol, float) or isinstance(sağ, float):
                    return math.inf if sol > 0 else (
                        -math.inf if sol < 0 else math.nan)
                raise AlqorXəta("BölməXətası", "sıfıra bölmək olmaz", yer,
                                "ALQ-R001")
            return sol / sağ
        if op == "~/":
            if sağ == 0:
                raise AlqorXəta("BölməXətası", "sıfıra bölmək olmaz", yer,
                                "ALQ-R001")
            nəticə = abs(sol) // abs(sağ)
            return int(nəticə if (sol >= 0) == (sağ >= 0) else -nəticə)
        if op == "%":
            if sağ == 0:
                raise AlqorXəta("BölməXətası", "sıfıra bölmək olmaz", yer,
                                "ALQ-R001")
            return math.fmod(sol, sağ) if isinstance(sol, float) \
                else int(math.fmod(sol, sağ))
        if op == "**":
            return sol ** sağ
        if op in ("&", "|", "^", "<<", ">>", ">>>"):
            if isinstance(sol, float) or isinstance(sağ, float):
                raise AlqorXəta("TipXətası",
                                "bit əməliyyatları tam ədəd tələb edir",
                                yer, "ALQ-T008")
            if op == "&":
                return sol & sağ
            if op == "|":
                return sol | sağ
            if op == "^":
                return sol ^ sağ
            if op == "<<":
                return sol << sağ
            if op == ">>":
                return sol >> sağ
            return (sol % (1 << 64)) >> sağ

        raise AlqorXəta("DaxiliXəta", f"naməlum operator `{op}`", yer)

    @staticmethod
    def _ədəddir(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _müqayisə(self, op: str, sol: Any, sağ: Any,
                  yer: Yer | None) -> Any:
        if isinstance(sol, Nümunə):
            metod = sol.sinif.metod_tap("müqayisə")
            if metod is not None:
                n = self.funksiya_çağır(metod.bağla(sol), [sağ], {}, yer)
                return self._müqayisə_nəticəsi(op, n)

        if isinstance(sol, str) and isinstance(sağ, str):
            from .elifba import sıralama_açarı
            a, b = sıralama_açarı(sol), sıralama_açarı(sağ)
            n = -1 if a < b else (1 if a > b else 0)
            return self._müqayisə_nəticəsi(op, n)

        if isinstance(sol, set) and isinstance(sağ, set):
            if op == "<=":
                return sol <= sağ
            if op == ">=":
                return sol >= sağ
            if op == "<":
                return sol < sağ
            if op == ">":
                return sol > sağ

        if not (self._ədəddir(sol) and self._ədəddir(sağ)):
            raise AlqorXəta(
                "TipXətası",
                f"`{tip_adı(sol)}` və `{tip_adı(sağ)}` müqayisə edilmir",
                yer, "ALQ-T008")
        n = -1 if sol < sağ else (1 if sol > sağ else 0)
        return self._müqayisə_nəticəsi(op, n)

    @staticmethod
    def _müqayisə_nəticəsi(op: str, n: int) -> Any:
        if op == "<=>":
            return n
        return {"<": n < 0, ">": n > 0, "<=": n <= 0, ">=": n >= 0}[op]

    def _bərabərdir(self, sol: Any, sağ: Any) -> bool:
        if isinstance(sol, Nümunə):
            metod = sol.sinif.metod_tap("bərabərdir")
            if metod is not None:
                return bool(self.funksiya_çağır(metod.bağla(sol), [sağ], {}))
        if isinstance(sol, bool) != isinstance(sağ, bool):
            if isinstance(sol, bool) or isinstance(sağ, bool):
                return False
        if isinstance(sol, float) and sol != sol:
            return False
        try:
            return bool(sol == sağ)
        except Exception:
            return sol is sağ

    def _e_tək(self, e: A.TəkOperand, m: Mühit) -> Any:
        if e.op == "deyil" or e.op == "!":
            return not self._məntiq(e.operand, m)
        dəyər = self._ifadə(e.operand, m)
        if e.op == "-":
            if isinstance(dəyər, Nümunə):
                metod = dəyər.sinif.metod_tap("əks")
                if metod is not None:
                    return self.funksiya_çağır(metod.bağla(dəyər), [], {})
            n = _kitabxana_operatoru("əks", dəyər, None)
            if n is not NotImplemented:
                return n
            if not self._ədəddir(dəyər):
                raise AlqorXəta("TipXətası",
                                f"`-` `{tip_adı(dəyər)}` tipinə tətbiq "
                                "edilmir", e.yer, "ALQ-T008")
            return -dəyər
        if e.op == "+":
            return dəyər
        if e.op == "~":
            if not isinstance(dəyər, int) or isinstance(dəyər, bool):
                raise AlqorXəta("TipXətası", "`~` tam ədəd tələb edir",
                                e.yer, "ALQ-T008")
            return ~dəyər
        raise AlqorXəta("DaxiliXəta", f"naməlum tək operator `{e.op}`", e.yer)

    def _e_mənimsətmə(self, e: A.Mənimsətmə, m: Mühit) -> Any:
        if len(e.hədəflər) > 1 or len(e.dəyərlər) > 1:
            dəyərlər = [self._ifadə(d, m) for d in e.dəyərlər]
            if len(dəyərlər) == 1:
                dəyərlər = list(self._iterasiya(dəyərlər[0], e.yer))
            if len(dəyərlər) != len(e.hədəflər):
                raise AlqorXəta("ArqumentXətası",
                                "mənimsətmədə sayllar uyğun gəlmir",
                                e.yer, "ALQ-T001")
            for h, d in zip(e.hədəflər, dəyərlər):
                self._mənimsət(h, d, m)
            return None

        hədəf = e.hədəflər[0]
        if e.op == "=":
            dəyər = self._ifadə(e.dəyərlər[0], m)
        elif e.op in ("??=", "?="):
            cari = self._ifadə_təhlükəsiz(hədəf, m)
            if cari is not None:
                return cari
            dəyər = self._ifadə(e.dəyərlər[0], m)
        else:
            cari = self._ifadə(hədəf, m)
            dəyər = self._ikili_hesabla(e.op[:-1], cari,
                                        self._ifadə(e.dəyərlər[0], m), e.yer)
        self._mənimsət(hədəf, dəyər, m)
        return dəyər

    def _ifadə_təhlükəsiz(self, e: A.İfadə, m: Mühit) -> Any:
        try:
            return self._ifadə(e, m)
        except AlqorXəta:
            return None

    def _mənimsət(self, hədəf: A.İfadə, dəyər: Any, m: Mühit) -> None:
        if isinstance(hədəf, A.Ad):
            m.təyin(hədəf.ad, self._dəyər_kopyası(dəyər))
            return
        if isinstance(hədəf, A.Üzv):
            obyekt = self._ifadə(hədəf.obyekt, m)
            self._üzv_qoy(obyekt, hədəf.ad, dəyər, hədəf.yer)
            return
        if isinstance(hədəf, A.İndeks):
            obyekt = self._ifadə(hədəf.obyekt, m)
            indeks = self._ifadə(hədəf.indeks, m)
            self._indeks_qoy(obyekt, indeks, dəyər, hədəf.yer)
            return
        if isinstance(hədəf, A.KortejLiteralı):
            dəyərlər = list(self._iterasiya(dəyər, hədəf.yer))
            for h, d in zip(hədəf.elementlər, dəyərlər):
                self._mənimsət(h, d, m)
            return
        raise AlqorXəta("ArqumentXətası",
                        "bu ifadəyə mənimsətmə mümkün deyil",
                        getattr(hədəf, "yer", None), "ALQ-T001")

    # ── Üzv və indeks ─────────────────────────────────────────────────

    def _e_üzv(self, e: A.Üzv, m: Mühit) -> Any:
        obyekt = self._ifadə(e.obyekt, m)
        if obyekt is None:
            if e.təhlükəsiz:
                return None
            raise AlqorXəta("BoşDəyərXətası",
                            f"`boş` dəyərdə `{e.ad}` üzvü yoxdur",
                            e.yer, "ALQ-R004")
        return self._üzv_al(obyekt, e.ad, e.yer)

    def _üzv_al(self, obyekt: Any, ad: str, yer: Yer | None) -> Any:
        if isinstance(obyekt, _Üst):
            baza = obyekt.sinif.baza
            if baza is None:
                raise AlqorXəta("TipXətası", "baza sinif yoxdur", yer,
                                "ALQ-T012")
            metod = baza.metod_tap(ad)
            if metod is None:
                raise AlqorXəta("ArqumentXətası",
                                f"baza sinifdə `{ad}` metodu yoxdur", yer,
                                "ALQ-T006")
            return metod.bağla(obyekt.nümunə)

        if isinstance(obyekt, Nümunə):
            return self._nümunə_üzvü(obyekt, ad, yer)

        if isinstance(obyekt, Sinif):
            var, dəyər = obyekt.statik_tap(ad)
            if var:
                # Kitabxana sinfinin üzvü çağıran ALT sinfi bilməlidir
                # (`İstifadəçi.tap(5)` → `verilənlər.Model.tap`)
                bağla = getattr(dəyər, "alqor_bağla", None)
                return bağla(obyekt, None) if bağla else dəyər
            if ad in obyekt.quruculər:
                return _QurucuİstinadI(obyekt, ad)
            raise AlqorXəta("ArqumentXətası",
                            f"`{obyekt.ad}` sinfində statik `{ad}` yoxdur",
                            yer, "ALQ-T006")

        if isinstance(obyekt, Sadalama):
            if ad in obyekt.variantlar:
                return obyekt.variantlar[ad]
            if ad in obyekt.metodlar:
                return obyekt.metodlar[ad]
            from .kitabxana import sadalama_metodu
            m = sadalama_metodu(obyekt, ad)
            if m is not None:
                return m
            raise AlqorXəta("ArqumentXətası",
                            f"`{obyekt.ad}` sadalamasında `{ad}` yoxdur",
                            yer, "ALQ-T061")

        if isinstance(obyekt, SadalamaDəyəri):
            if ad in obyekt.sahələr:
                return obyekt.sahələr[ad]
            if ad in obyekt.sadalama.metodlar:
                return obyekt.sadalama.metodlar[ad].bağla(obyekt)
            from .kitabxana import sadalama_dəyər_metodu
            mm = sadalama_dəyər_metodu(obyekt, ad)
            if mm is not None:
                return mm
            raise AlqorXəta("ArqumentXətası",
                            f"`{obyekt.ad}` variantında `{ad}` yoxdur",
                            yer, "ALQ-T006")

        if isinstance(obyekt, Modul):
            if ad in obyekt.üzvlər:
                return obyekt.üzvlər[ad]
            raise AlqorXəta("ArqumentXətası",
                            f"`{obyekt.ad}` modulunda `{ad}` yoxdur", yer,
                            "ALQ-M002")

        if isinstance(obyekt, Element) and ad in ("ad", "atributlar",
                                                   "uşaqlar"):
            return getattr(obyekt, ad)

        if isinstance(obyekt, tuple) and ad.isdigit():
            i = int(ad)
            if i >= len(obyekt):
                raise AlqorXəta("İndeksXətası",
                                f"kortejdə {i} indeksi yoxdur", yer,
                                "ALQ-R002")
            return obyekt[i]

        from .kitabxana import daxili_metod
        metod = daxili_metod(self, obyekt, ad)
        if metod is not None:
            return metod

        # Python obyektinin dinamik xassələri (`forma.FormaObyekti`)
        üzv = getattr(obyekt, "alqor_üzv", None)
        if üzv is not None:
            return üzv(self, ad, yer)

        raise self._üzv_xətası(obyekt, ad, yer)

    @staticmethod
    def _üzv_xətası(obyekt: Any, ad: str, yer: Yer | None) -> AlqorXəta:
        """
        Tapılmayan üzv üçün xəta — ASCII yazılış təklifi ilə.

        `siyahı.cem()` yazılıbsa, `cəm()` təklif olunur. Bu, ASCII
        çevrilməsinin YALNIZ açar sözlərə aid olduğunu izah edir.
        """
        from .elifba import latınla
        from .kitabxana import mövcud_üzvlər

        x = AlqorXəta("ArqumentXətası",
                      f"`{tip_adı(obyekt)}` tipində `{ad}` üzvü yoxdur",
                      yer, "ALQ-T006")
        üzvlər = mövcud_üzvlər(obyekt)
        # Dəqiq ASCII uyğunluğu
        for ü in üzvlər:
            if latınla(ü) == ad and ü != ad:
                x.mesaj += (f" — `{ü}` demək istəyirdiniz?"
                            " ASCII çevrilməsi yalnız AÇAR SÖZLƏRƏ"
                            " aiddir, üzv adlarına yox")
                return x
        # Yaxın ad
        yaxın = [ü for ü in üzvlər if ü.startswith(ad[:3])][:3]
        if yaxın:
            x.mesaj += f" — bəlkə: {', '.join(yaxın)}"
        return x

    def _nümunə_üzvü(self, n: Nümunə, ad: str, yer: Yer | None) -> Any:
        if ad in n.sahələr:
            return n.sahələr[ad]

        hesablanan = n.sinif.hesablanan_tap(ad)
        if hesablanan is not None:
            if "tənbəl" in hesablanan.annotasiyalar:
                if ad not in n._keş:
                    n._keş[ad] = self.funksiya_çağır(
                        hesablanan.bağla(n), [], {}, yer)
                return n._keş[ad]
            return self.funksiya_çağır(hesablanan.bağla(n), [], {}, yer)

        metod = n.sinif.metod_tap(ad)
        if metod is not None:
            return metod.bağla(n)

        var, dəyər = n.sinif.statik_tap(ad)
        if var:
            bağla = getattr(dəyər, "alqor_bağla", None)
            return bağla(n.sinif, n) if bağla else dəyər

        from .kitabxana import daxili_metod
        g = daxili_metod(self, n, ad)
        if g is not None:
            return g

        raise AlqorXəta("ArqumentXətası",
                        f"`{n.sinif.ad}` tipində `{ad}` üzvü yoxdur", yer,
                        "ALQ-T006")

    def _üzv_qoy(self, obyekt: Any, ad: str, dəyər: Any,
                 yer: Yer | None) -> None:
        if isinstance(obyekt, Nümunə):
            yazıcı = obyekt.sinif.yazıcı_tap(ad)
            if yazıcı is not None:
                self.funksiya_çağır(yazıcı.bağla(obyekt), [dəyər], {}, yer)
                return
            if obyekt.sinif.hesablanan_tap(ad) is not None:
                raise AlqorXəta("ArqumentXətası",
                                f"`{ad}` yalnız oxunan xassədir", yer,
                                "ALQ-T020")
            obyekt.sahələr[ad] = dəyər
            return
        if isinstance(obyekt, Sinif):
            obyekt.statiklər[ad] = dəyər
            return
        if isinstance(obyekt, Modul):
            obyekt.üzvlər[ad] = dəyər
            return
        qoy = getattr(obyekt, "alqor_üzv_qoy", None)
        if qoy is not None:
            qoy(self, ad, dəyər, yer)
            return
        raise AlqorXəta("ArqumentXətası",
                        f"`{tip_adı(obyekt)}` tipinin üzvü dəyişdirilə "
                        "bilməz", yer, "ALQ-T021")

    def _e_indeks(self, e: A.İndeks, m: Mühit) -> Any:
        obyekt = self._ifadə(e.obyekt, m)
        indeks = self._ifadə(e.indeks, m)
        return self._indeks_al(obyekt, indeks, e.yer)

    def _indeks_al(self, obyekt: Any, indeks: Any, yer: Yer | None) -> Any:
        if isinstance(obyekt, Nümunə):
            metod = obyekt.sinif.metod_tap("al")
            if metod is not None:
                return self.funksiya_çağır(metod.bağla(obyekt), [indeks],
                                           {}, yer)

        if isinstance(obyekt, dict):
            if indeks in obyekt:
                return obyekt[indeks]
            raise AlqorXəta("AçarXətası",
                            f"lüğətdə `{mətnə(indeks, self)}` açarı yoxdur",
                            yer, "ALQ-R003")

        f = getattr(type(obyekt), "alqor_indeks", None)
        if f is not None:
            return f(obyekt, self, indeks, yer)

        if isinstance(obyekt, (list, str, tuple, bytes)):
            if not isinstance(indeks, int) or isinstance(indeks, bool):
                raise AlqorXəta("TipXətası",
                                f"indeks tam ədəd olmalıdır, "
                                f"`{tip_adı(indeks)}` gəlib", yer,
                                "ALQ-T009")
            n = len(obyekt)
            i = indeks + n if indeks < 0 else indeks
            if not 0 <= i < n:
                raise AlqorXəta(
                    "İndeksXətası",
                    f"indeks {indeks} diapazondan kənardır "
                    f"(uzunluq {n})", yer, "ALQ-R002")
            return obyekt[i]

        raise AlqorXəta("TipXətası",
                        f"`{tip_adı(obyekt)}` indekslənə bilməz", yer,
                        "ALQ-T009")

    def _indeks_qoy(self, obyekt: Any, indeks: Any, dəyər: Any,
                    yer: Yer | None) -> None:
        if isinstance(obyekt, Nümunə):
            metod = obyekt.sinif.metod_tap("qoy")
            if metod is not None:
                self.funksiya_çağır(metod.bağla(obyekt), [indeks, dəyər],
                                    {}, yer)
                return
        if isinstance(obyekt, dict):
            obyekt[indeks] = dəyər
            return
        f = getattr(type(obyekt), "alqor_indeks_qoy", None)
        if f is not None:
            f(obyekt, self, indeks, dəyər, yer)
            return
        if isinstance(obyekt, list):
            n = len(obyekt)
            i = indeks + n if isinstance(indeks, int) and indeks < 0 \
                else indeks
            if not isinstance(i, int) or not 0 <= i < n:
                raise AlqorXəta("İndeksXətası",
                                f"indeks {indeks} diapazondan kənardır "
                                f"(uzunluq {n})", yer, "ALQ-R002")
            obyekt[i] = dəyər
            return
        if isinstance(obyekt, str):
            raise AlqorXəta("TipXətası",
                            "`mətn` dəyişməzdir — simvolu dəyişmək olmaz",
                            yer, "ALQ-T021")
        raise AlqorXəta("TipXətası",
                        f"`{tip_adı(obyekt)}` indekslə dəyişdirilə bilməz",
                        yer, "ALQ-T009")

    def _e_dilim(self, e: A.Dilim, m: Mühit) -> Any:
        obyekt = self._ifadə(e.obyekt, m)
        f = getattr(type(obyekt), "alqor_dilim", None)
        if f is not None:
            b = None if e.başlanğıc is None else self._ifadə(e.başlanğıc, m)
            s = None if e.son is None else self._ifadə(e.son, m)
            return f(obyekt, self, b, s, not e.xaric, e.yer)
        if not isinstance(obyekt, (list, str, tuple, bytes)):
            raise AlqorXəta("TipXətası",
                            f"`{tip_adı(obyekt)}` dilimlənə bilməz", e.yer,
                            "ALQ-T009")
        n = len(obyekt)
        b = 0 if e.başlanğıc is None else self._ifadə(e.başlanğıc, m)
        s = n if e.son is None else self._ifadə(e.son, m)
        if not isinstance(b, int) or not isinstance(s, int):
            raise AlqorXəta("TipXətası", "dilim hədləri tam ədəd olmalıdır",
                            e.yer, "ALQ-T009")
        if b < 0:
            b += n
        if s < 0:
            s += n
        if e.son is not None and not e.xaric:
            s += 1
        return obyekt[max(0, b):min(n, s)]

    # ── Çağırışlar ────────────────────────────────────────────────────

    def _e_çağırış(self, e: A.Çağırış, m: Mühit) -> Any:
        # İxtiyari zəncir: `a?.metod()` — `a` boşdursa bütün zəncir boşdur
        if isinstance(e.funksiya, A.Üzv) and e.funksiya.təhlükəsiz:
            if self._ifadə(e.funksiya.obyekt, m) is None:
                return None
        funksiya = self._ifadə(e.funksiya, m)
        arqumentlər: list[Any] = []
        adlı: dict[str, Any] = {}
        for a in e.arqumentlər:
            dəyər = self._ifadə(a.dəyər, m)
            if a.yayma:
                arqumentlər.extend(self._iterasiya(dəyər, e.yer))
            elif a.ad:
                adlı[a.ad] = dəyər
            else:
                arqumentlər.append(dəyər)
        return self._çağır(funksiya, arqumentlər, adlı, e.yer)

    def _çağır(self, funksiya: Any, arqumentlər: list, adlı: dict,
               yer: Yer | None) -> Any:
        # `üst(...)` — baza sinfin qurucusunu çağırır
        if isinstance(funksiya, _Üst):
            baza = funksiya.sinif.baza
            if baza is None:
                raise AlqorXəta("TipXətası",
                                "`üst(...)` baza sinfi olmayan sinifdə "
                                "işlənib", yer, "ALQ-P012")
            qurucu = self._qurucu_tap(baza, "")
            if qurucu is None:
                # Baza qurucusu yoxdursa — sadəcə xassə standartları qalır
                return None
            return self.funksiya_çağır(qurucu.bağla(funksiya.nümunə),
                                       arqumentlər, adlı, yer)
        if isinstance(funksiya, _QurucuİstinadI):
            return self.nümunə_yarat(funksiya.sinif, funksiya.ad,
                                     arqumentlər, adlı, yer)
        if isinstance(funksiya, _VariantQurucusu):
            return funksiya.yarat(self, arqumentlər, adlı)
        if isinstance(funksiya, Modul) and funksiya.çağırışçı is not None:
            return funksiya.çağırışçı.çağır(self, arqumentlər, adlı, yer)
        if isinstance(funksiya, Çağırılan):
            return funksiya.çağır(self, arqumentlər, adlı, yer)
        if isinstance(funksiya, Nümunə):
            metod = funksiya.sinif.metod_tap("çağır")
            if metod is not None:
                return self.funksiya_çağır(metod.bağla(funksiya),
                                           arqumentlər, adlı, yer)
        raise AlqorXəta("TipXətası",
                        f"`{tip_adı(funksiya)}` çağırıla bilməz", yer,
                        "ALQ-T008")

    def funksiya_çağır(self, f: Funksiya, arqumentlər: list, adlı: dict,
                       yer: Yer | None = None) -> Any:
        # `asinxron funksiya` dərhal `Gələcək` qaytarır — gövdə yalnız
        # `gözlə` (və ya `paralel`) ilə işə düşür.
        if f.asinxron and not f.generator:
            sinxron = Funksiya(
                f.ad, f.parametrlər, f.gövdə, f.mühit, False,
                f.generator, f.özü, f.sinif, f.annotasiyalar, None)
            return Gələcək(
                lambda: self.funksiya_çağır(sinxron, arqumentlər, adlı,
                                            yer),
                f.ad)

        if f.yaddaş is not None and not adlı:
            açar = tuple(
                x if isinstance(x, (int, float, str, bool, type(None)))
                else id(x) for x in arqumentlər)
            if açar in f.yaddaş:
                return f.yaddaş[açar]

        self._yerli.dərinlik += 1
        if self._yerli.dərinlik > STEK_HƏDDİ:
            self._yerli.dərinlik -= 1
            raise AlqorXəta(
                "StekDaşmaXətası",
                f"çağırış dərinliyi {STEK_HƏDDİ} həddini aşdı — "
                "sonsuz rekursiya?", yer, "ALQ-R010")

        try:
            m = f.mühit.alt()
            if f.özü is not None:
                m.elan("özü", f.özü)
                # Genişlətmədə `özü` daxili tip ola bilər (mətn, siyahı...)
                # — onların `sinif` sahəsi yoxdur.
                sinif = f.sinif or getattr(f.özü, "sinif", None)
                if sinif is not None:
                    m.elan("__sinif__", sinif)
            elif f.sinif is not None:
                m.elan("__sinif__", f.sinif)

            self._parametrləri_bağla(f, arqumentlər, adlı, m, yer)

            if f.generator:
                return AlqorGenerator(self._korutin_qur(f, m))

            izləyici = self.izləyici
            if izləyici is not None:
                izləyici.daxil(f, m)

            if isinstance(f.gövdə, list):
                self._yerli.gecikdirilmiş.append([])
                try:
                    try:
                        self._blok(f.gövdə, m)
                        nəticə = self._son_ifadənin_dəyəri(f, m)
                    except QaytarSiqnalı as s:
                        nəticə = s.dəyər
                    except VerSiqnalı as s:
                        # `() => blok ... ver x son` — gövdə blokdur
                        nəticə = s.dəyər
                finally:
                    gecikmiş = self._yerli.gecikdirilmiş.pop()
                    for ifadə, mm in reversed(gecikmiş):
                        try:
                            self._ifadə(ifadə, mm)
                        except AlqorXəta:
                            pass
            else:
                nəticə = self._ifadə(f.gövdə, m)

            if f.yaddaş is not None and not adlı:
                f.yaddaş[açar] = nəticə
            return nəticə
        finally:
            self._yerli.dərinlik -= 1
            if self.izləyici is not None and not f.generator:
                self.izləyici.çıx(f)

    def _son_ifadənin_dəyəri(self, f: Funksiya, m: Mühit) -> Any:
        """`qaytar`-sız son ifadə avtomatik qaytarılır (Spes. § 5.3)."""
        if not isinstance(f.gövdə, list) or not f.gövdə:
            return None
        son = f.gövdə[-1]
        if isinstance(son, A.İfadəCümləsi) and not isinstance(
                son.ifadə, (A.Mənimsətmə, A.Çağırış)):
            try:
                return self._ifadə(son.ifadə, m)
            except AlqorXəta:
                return None
        return None

    def _korutin_qur(self, f: Funksiya, m: Mühit) -> Korutin:
        """
        Generator gövdəsini TƏNBƏL korutinə çevirir.

        Gövdə ayrıca sapda işləyir; `ver` icranı dayandırır. Beləliklə
        sonsuz generatorlar da işləyir.
        """
        gövdə = f.gövdə

        def işlədici(ver) -> None:
            köhnə = self._yerli.ver
            self._yerli.ver = ver
            try:
                self._blok(gövdə, m)        # type: ignore[arg-type]
            except QaytarSiqnalı:
                pass
            except DayanSiqnalı:
                pass
            finally:
                self._yerli.ver = köhnə

        return Korutin(işlədici, f.ad)

    def _parametrləri_bağla(self, f: Funksiya, arqumentlər: list,
                            adlı: dict, m: Mühit,
                            yer: Yer | None) -> None:
        mövqeli = [p for p in f.parametrlər
                   if not p.variadic and not p.adlı_variadic
                   and not p.yalnız_adlı]
        variadic = next((p for p in f.parametrlər if p.variadic), None)
        adlı_variadic = next((p for p in f.parametrlər if p.adlı_variadic),
                             None)
        yalnız_adlı = [p for p in f.parametrlər if p.yalnız_adlı]

        if len(arqumentlər) > len(mövqeli) and variadic is None:
            raise AlqorXəta(
                "ArqumentXətası",
                f"`{f.ad}` ən çox {len(mövqeli)} mövqeli arqument qəbul "
                f"edir, {len(arqumentlər)} verilib", yer, "ALQ-T003")

        for i, p in enumerate(mövqeli):
            if i < len(arqumentlər):
                dəyər = arqumentlər[i]
            elif p.ad in adlı:
                dəyər = adlı.pop(p.ad)
            elif p.standart is not None:
                dəyər = self._ifadə(p.standart, m)
            else:
                raise AlqorXəta(
                    "ArqumentXətası",
                    f"`{f.ad}` üçün `{p.ad}` arqumenti verilməyib", yer,
                    "ALQ-T003")
            m.elan(p.ad, self._dəyər_kopyası(self._genişlət(dəyər, p.tip)))

        for p in yalnız_adlı:
            if p.ad in adlı:
                m.elan(p.ad, adlı.pop(p.ad))
            elif p.standart is not None:
                m.elan(p.ad, self._ifadə(p.standart, m))
            else:
                raise AlqorXəta(
                    "ArqumentXətası",
                    f"`{f.ad}` üçün `{p.ad}` adlı arqumenti məcburidir",
                    yer, "ALQ-T003")

        if variadic is not None:
            m.elan(variadic.ad, list(arqumentlər[len(mövqeli):]))

        if adlı_variadic is not None:
            m.elan(adlı_variadic.ad, dict(adlı))
            adlı = {}

        if adlı:
            naməlum = ", ".join(sorted(adlı))
            raise AlqorXəta("ArqumentXətası",
                            f"`{f.ad}` naməlum adlı arqument: {naməlum}",
                            yer, "ALQ-T004")

        # Qısa qurucu: `açıq xassə ad: mətn`
        if f.özü is not None:
            for p in f.parametrlər:
                if p.xassə_görünüşü and m.var(p.ad):
                    f.özü.sahələr[p.ad] = m.al(p.ad)

    # ── Obyekt yaratma ────────────────────────────────────────────────

    def nümunə_yarat(self, s: Sinif, qurucu_adı: str | None,
                     arqumentlər: list, adlı: dict,
                     yer: Yer | None) -> Nümunə:
        if s.mücərrəd:
            raise AlqorXəta(
                "TipXətası",
                f"`{s.ad}` mücərrəd sinifdir — ondan obyekt yaradıla bilməz",
                yer, "ALQ-T052")

        n = Nümunə(s)

        # Xassələrin standart dəyərləri
        for x in s.bütün_xassələr():
            if x.standart is not None:
                n.sahələr[x.ad] = self._genişlət(
                    self._ifadə(x.standart, s.mühit or self.qlobal), x.tip)
            else:
                n.sahələr[x.ad] = self._xassə_standartı(x)

        if s.forma is not None or (s.baza is not None
                                   and s.quruluş == "komponent"):
            from . import forma
            forma.nümunəyə_qoş(n)

        qurucu = self._qurucu_tap(s, qurucu_adı or "")
        if qurucu is not None:
            self.funksiya_çağır(qurucu.bağla(n), arqumentlər, adlı, yer)
        elif arqumentlər or adlı:
            # Struktur üçün adlı sahə ilkinləşdirməsi
            if s.quruluş == "struktur" and adlı and not arqumentlər:
                for a, d in adlı.items():
                    n.sahələr[a] = d
            else:
                raise AlqorXəta(
                    "ArqumentXətası",
                    f"`{s.ad}` sinfində qurucu yoxdur, amma arqument "
                    "verilib", yer, "ALQ-T003")
        return n

    @staticmethod
    def _xassə_standartı(x: A.XassəElanı) -> Any:
        t = x.tip
        if isinstance(t, A.TipAdı) and not t.ixtiyari:
            return {"tam": 0, "onluq": 0.0, "mətn": "", "məntiq": False,
                    "siyahı": [], "lüğət": {}, "dəst": set(),
                    "bayt": b""}.get(t.tam_ad, None)
        return None

    @staticmethod
    def _qurucu_tap(s: Sinif, ad: str) -> Funksiya | None:
        cari: Sinif | None = s
        while cari is not None:
            if ad in cari.quruculər:
                return cari.quruculər[ad]
            cari = cari.baza
        return None

    def _e_yeni(self, e: A.Yeni, m: Mühit) -> Any:
        hədəf = self._tip_dəyəri(e.tip, m)
        arqumentlər: list[Any] = []
        adlı: dict[str, Any] = {}
        for a in e.arqumentlər:
            dəyər = self._ifadə(a.dəyər, m)
            if a.yayma:
                arqumentlər.extend(self._iterasiya(dəyər, e.yer))
            elif a.ad:
                adlı[a.ad] = dəyər
            else:
                arqumentlər.append(dəyər)

        if isinstance(hədəf, Sinif):
            return self.nümunə_yarat(hədəf, e.qurucu, arqumentlər, adlı,
                                     e.yer)
        if isinstance(hədəf, Çağırılan):
            return hədəf.çağır(self, arqumentlər, adlı, e.yer)
        raise AlqorXəta("TipXətası",
                        f"`yeni` sinif gözləyir, `{tip_adı(hədəf)}` gəlib",
                        e.yer, "ALQ-T002")

    def _tip_dəyəri(self, t: A.TipQovşağı, m: Mühit) -> Any:
        if isinstance(t, A.TipAdı):
            dəyər: Any = m.al(t.yol[0])
            for hissə in t.yol[1:]:
                dəyər = self._üzv_al(dəyər, hissə, t.yer)
            if isinstance(dəyər, _TipAliası):
                return self._tip_dəyəri(dəyər.hədəf, m)
            return dəyər
        raise AlqorXəta("TipXətası", "sadə tip adı gözlənilirdi",
                        getattr(t, "yer", None), "ALQ-T002")

    # ── Tip əməliyyatları ─────────────────────────────────────────────

    def _e_çevirmə(self, e: A.Çevirmə, m: Mühit) -> Any:
        dəyər = self._ifadə(e.ifadə, m)
        hədəf = e.tip.tam_ad if isinstance(e.tip, A.TipAdı) else ""
        try:
            return self._çevir(dəyər, hədəf, e.yer)
        except AlqorXəta:
            if e.təhlükəsiz:
                return None
            raise

    def _çevir(self, dəyər: Any, hədəf: str, yer: Yer | None) -> Any:
        f = getattr(type(dəyər), "alqor_çevir", None)
        if f is not None:
            n = f(dəyər, hədəf, yer)
            if n is not NotImplemented:
                return n
        if hədəf == "tam":
            if isinstance(dəyər, bool):
                return 1 if dəyər else 0
            if isinstance(dəyər, int):
                return dəyər
            if isinstance(dəyər, float):
                return int(dəyər)
            if isinstance(dəyər, str):
                try:
                    return int(dəyər.strip())
                except ValueError:
                    raise AlqorXəta(
                        "ÇevrilməXətası",
                        f'"{dəyər}" tam ədədə çevrilə bilmir', yer,
                        "ALQ-R005")
        elif hədəf == "onluq":
            if isinstance(dəyər, bool):
                return 1.0 if dəyər else 0.0
            if isinstance(dəyər, (int, float)):
                return float(dəyər)
            if isinstance(dəyər, str):
                try:
                    return float(dəyər.strip())
                except ValueError:
                    raise AlqorXəta(
                        "ÇevrilməXətası",
                        f'"{dəyər}" onluq ədədə çevrilə bilmir', yer,
                        "ALQ-R005")
        elif hədəf == "mətn":
            return mətnə(dəyər, self)
        elif hədəf == "məntiq":
            if isinstance(dəyər, bool):
                return dəyər
            if isinstance(dəyər, str):
                k = kiçiyə(dəyər.strip())
                if k in ("doğru", "dogru", "true", "1"):
                    return True
                if k in ("yanlış", "yanlis", "false", "0"):
                    return False
            raise AlqorXəta("ÇevrilməXətası",
                            "məntiqi tipə açıq çevirmə tələb olunur", yer,
                            "ALQ-R005")
        elif hədəf == "siyahı":
            return list(self._iterasiya(dəyər, yer))
        elif hədəf == "dəst":
            return set(self._iterasiya(dəyər, yer))
        raise AlqorXəta("ÇevrilməXətası",
                        f"`{tip_adı(dəyər)}` → `{hədəf}` çevrilməsi "
                        "mümkün deyil", yer, "ALQ-T014")

    def _e_tip_yoxlama(self, e: A.TipYoxlama, m: Mühit) -> bool:
        return self._tip_uyğundur(self._ifadə(e.ifadə, m), e.tip, m)

    def _tip_uyğundur(self, dəyər: Any, t: A.TipQovşağı, m: Mühit) -> bool:
        if isinstance(t, A.TipBirləşmə):
            return any(self._tip_uyğundur(dəyər, v, m) for v in t.variantlar)
        if not isinstance(t, A.TipAdı):
            return False
        ad = t.tam_ad
        if dəyər is None:
            return ad in ("heç", "boş") or t.ixtiyari
        if t.ixtiyari and dəyər is None:
            return True

        sadə = {
            "tam": lambda x: isinstance(x, int) and not isinstance(x, bool),
            "onluq": lambda x: isinstance(x, float),
            "mətn": lambda x: isinstance(x, str),
            "simvol": lambda x: isinstance(x, str) and len(x) <= 2,
            "məntiq": lambda x: isinstance(x, bool),
            "bayt": lambda x: isinstance(x, bytes),
            "siyahı": lambda x: isinstance(x, list),
            "lüğət": lambda x: isinstance(x, dict),
            "dəst": lambda x: isinstance(x, set),
            "kortej": lambda x: isinstance(x, tuple),
            "istənilən": lambda x: True,
            "heç": lambda x: x is None,
        }
        if ad in sadə:
            return sadə[ad](dəyər)

        try:
            hədəf = self._tip_dəyəri(t, m)
        except AlqorXəta:
            return False
        if isinstance(hədəf, Sinif):
            if isinstance(dəyər, Nümunə):
                if dəyər.sinif.alt_sinifdirmi(hədəf):
                    return True
                return hədəf.ad in dəyər.sinif.interfeyslər
            return False
        if isinstance(hədəf, Sadalama):
            return (isinstance(dəyər, SadalamaDəyəri)
                    and dəyər.sadalama is hədəf)
        if isinstance(hədəf, _TipAliası):
            return self._tip_uyğundur(dəyər, hədəf.hədəf, m)
        return False

    def _e_üzvlük(self, e: A.Üzvlük, m: Mühit) -> bool:
        element = self._ifadə(e.element, m)
        kolleksiya = self._ifadə(e.kolleksiya, m)
        if isinstance(kolleksiya, Nümunə):
            metod = kolleksiya.sinif.metod_tap("ehtiva")
            if metod is not None:
                return bool(self.funksiya_çağır(metod.bağla(kolleksiya),
                                                [element], {}, e.yer))
        if isinstance(kolleksiya, dict):
            return element in kolleksiya
        f = getattr(type(kolleksiya), "alqor_ehtiva", None)
        if f is not None:
            return f(kolleksiya, element, e.yer)
        if isinstance(kolleksiya, (list, set, tuple, str, AlqorDiapazon)):
            return element in kolleksiya
        raise AlqorXəta("TipXətası",
                        f"`içindədir` `{tip_adı(kolleksiya)}` tipinə "
                        "tətbiq edilmir", e.yer, "ALQ-T008")

    def _e_boş_yoxlama(self, e: A.BoşYoxlama, m: Mühit) -> bool:
        dəyər = self._ifadə(e.ifadə, m)
        boşdur = dəyər is None
        return (not boşdur) if e.inkar else boşdur

    def _e_boru(self, e: A.Boru, m: Mühit) -> Any:
        dəyər = self._ifadə(e.dəyər, m)
        funksiya = self._ifadə(e.funksiya, m)
        return self._çağır(funksiya, [dəyər], {}, e.yer)

    def _e_məcburi_açma(self, e: A.MəcburiAçma, m: Mühit) -> Any:
        dəyər = self._ifadə(e.ifadə, m)
        if dəyər is None:
            raise AlqorXəta("BoşDəyərXətası",
                            "`!` operatoru `boş` dəyərə tətbiq edildi",
                            e.yer, "ALQ-R004")
        return dəyər

    def _e_yayma(self, e: A.Yayma, m: Mühit) -> Any:
        dəyər = self._ifadə(e.ifadə, m)
        if isinstance(dəyər, Nümunə) and dəyər.sinif.ad == "Xəta":
            raise QaytarSiqnalı(dəyər)
        return dəyər

    def _e_gözlə(self, e: A.Gözlə, m: Mühit) -> Any:
        dəyər = self._ifadə(e.ifadə, m)
        return self.gözlə(dəyər, e.yer)

    def gözlə(self, dəyər: Any, yer: Yer | None = None) -> Any:
        """`Gələcək`-i həll edir; adi dəyər olduğu kimi qaytarılır."""
        if isinstance(dəyər, Gələcək):
            try:
                return dəyər.al()
            except TimeoutError as x:
                raise AlqorXəta("VaxtBitdiXətası", str(x), yer,
                                "ALQ-R011")
        if isinstance(dəyər, (list, tuple)) and any(
                isinstance(d, Gələcək) for d in dəyər):
            for d in dəyər:
                if isinstance(d, Gələcək):
                    d.başlat()
            nəticə = [self.gözlə(d, yer) for d in dəyər]
            return tuple(nəticə) if isinstance(dəyər, tuple) else nəticə
        return dəyər

    # ── Kolleksiyalar ─────────────────────────────────────────────────

    def _e_siyahı(self, e: A.SiyahıLiteralı, m: Mühit) -> list:
        nəticə: list[Any] = []
        yaymalar = e.yaymalar or [False] * len(e.elementlər)
        for element, yayma in zip(e.elementlər, yaymalar):
            dəyər = self._ifadə(element, m)
            if yayma:
                nəticə.extend(self._iterasiya(dəyər, e.yer))
            else:
                nəticə.append(dəyər)
        return nəticə

    def _e_lüğət(self, e: A.LüğətLiteralı, m: Mühit) -> dict:
        nəticə: dict[Any, Any] = {}
        for açar, dəyər_ifadəsi in zip(e.açarlar, e.dəyərlər):
            dəyər = self._ifadə(dəyər_ifadəsi, m)
            if açar is None:
                if not isinstance(dəyər, dict):
                    raise AlqorXəta("TipXətası",
                                    "`...` lüğətdə lüğət gözləyir", e.yer,
                                    "ALQ-T001")
                nəticə.update(dəyər)
            else:
                nəticə[self._açar(self._ifadə(açar, m), e.yer)] = dəyər
        return nəticə

    @staticmethod
    def _açar(dəyər: Any, yer: Yer | None) -> Any:
        try:
            hash(dəyər)
        except TypeError:
            raise AlqorXəta("TipXətası",
                            f"`{tip_adı(dəyər)}` lüğət açarı ola bilməz",
                            yer, "ALQ-T001")
        return dəyər

    def _e_dəst(self, e: A.DəstLiteralı, m: Mühit) -> set:
        return {self._açar(self._ifadə(x, m), e.yer) for x in e.elementlər}

    def _e_kortej(self, e: A.KortejLiteralı, m: Mühit) -> tuple:
        return tuple(self._ifadə(x, m) for x in e.elementlər)

    def _e_diapazon(self, e: A.Diapazon, m: Mühit) -> AlqorDiapazon:
        b = self._ifadə(e.başlanğıc, m)
        s = self._ifadə(e.son, m)
        a = self._ifadə(e.addım, m) if e.addım is not None else None
        for ad, d in (("başlanğıc", b), ("son", s)):
            if not isinstance(d, int) or isinstance(d, bool):
                if isinstance(d, str) and len(d) == 1:
                    continue
                raise AlqorXəta("TipXətası",
                                f"diapazonun {ad} hissəsi tam ədəd "
                                f"olmalıdır, `{tip_adı(d)}` gəlib", e.yer,
                                "ALQ-T001")
        if isinstance(b, str):
            return AlqorDiapazon(ord(b), ord(s), a, e.xaric)
        return AlqorDiapazon(b, s, a, e.xaric)

    def _e_qurma(self, e: A.Qurma, m: Mühit) -> Any:
        mənbə = self._ifadə(e.mənbə, m)
        nəticə_siyahı: list[Any] = []
        nəticə_lüğət: dict[Any, Any] = {}

        for element in self._iterasiya(mənbə, e.yer):
            alt = m.alt()
            self._bağla(e.bağlama, element, alt, elan=True)
            if e.şərt is not None and not self._məntiq(e.şərt, alt):
                continue
            if e.növ == "lüğət":
                açar = self._açar(self._ifadə(e.ifadə, alt), e.yer)
                nəticə_lüğət[açar] = self._ifadə(e.dəyər_ifadəsi, alt)
            else:
                nəticə_siyahı.append(self._ifadə(e.ifadə, alt))

        if e.növ == "lüğət":
            return nəticə_lüğət
        if e.növ == "dəst":
            return set(nəticə_siyahı)
        if e.növ == "generator":
            return AlqorGenerator(iter(nəticə_siyahı))
        return nəticə_siyahı

    # ── İnterfeys sintaksisi (JSX) ────────────────────────────────────

    def _e_jsx(self, e: A.JSXElement, m: Mühit) -> Any:
        atributlar = self._jsx_atributlar(e.atributlar, m)
        uşaqlar = self._jsx_uşaqlar(e.uşaqlar, m)
        if e.komponentdir:
            return self._komponent_göstər(e.ad, atributlar, uşaqlar,
                                          e.yer, m)
        return Element(e.ad, atributlar, uşaqlar)

    def _e_jsx_parça(self, e: A.JSXParça, m: Mühit) -> Element:
        return Element("", {}, self._jsx_uşaqlar(e.uşaqlar, m))

    def _jsx_atributlar(self, atributlar, m: Mühit) -> dict:
        nəticə: dict[str, Any] = {}
        for a in atributlar:
            if a.yayma:
                dəyər = self._ifadə(a.dəyər, m)
                if isinstance(dəyər, dict):
                    nəticə.update({str(k): v for k, v in dəyər.items()})
                elif isinstance(dəyər, Nümunə):
                    nəticə.update(dəyər.sahələr)
                else:
                    raise AlqorXəta(
                        "TipXətası",
                        f"`{{...}}` yayması lüğət və ya obyekt gözləyir, "
                        f"`{tip_adı(dəyər)}` gəlib",
                        getattr(a.dəyər, "yer", None), "ALQ-T001")
            elif a.dəyər is None:
                nəticə[a.ad] = True
            else:
                nəticə[a.ad] = self._ifadə(a.dəyər, m)
        return nəticə

    def _jsx_uşaqlar(self, uşaqlar, m: Mühit) -> list:
        nəticə: list[Any] = []
        for u in uşaqlar:
            if isinstance(u, A.JSXMətn):
                nəticə.append(u.dəyər)
                continue
            dəyər = self._ifadə(u, m)
            if dəyər is None or dəyər is False:
                continue
            if isinstance(dəyər, (list, tuple)):
                nəticə.extend(x for x in dəyər
                              if x is not None and x is not False)
            else:
                nəticə.append(dəyər)
        return nəticə

    def _komponent_göstər(self, ad: str, atributlar: dict,
                          uşaqlar: list, yer: Yer | None,
                          m: Mühit) -> Any:
        """
        Böyük hərflə başlayan JSX adı komponent istinadıdır.

        Sinif/komponent  → nümunə yaradılır, `göstər()` çağırılır
        Funksiya         → adlı arqumentlərlə çağırılır
        """
        hissələr = ad.split(".")
        try:
            hədəf: Any = m.al(hissələr[0])
        except AlqorXəta:
            raise AlqorXəta(
                "ArqumentXətası",
                f"`<{ad} />` komponenti tapılmadı", yer, "ALQ-T022",
            )
        for h in hissələr[1:]:
            hədəf = self._üzv_al(hədəf, h, yer)

        if isinstance(hədəf, Sinif):
            qurucu = self._qurucu_tap(hədəf, "")
            if qurucu is not None and qurucu.parametrlər:
                n = self.nümunə_yarat(hədəf, None, [], atributlar, yer)
            else:
                n = self.nümunə_yarat(hədəf, None, [], {}, yer)
                for a, d in atributlar.items():
                    n.sahələr[a] = d
            if uşaqlar:
                n.sahələr.setdefault("uşaqlar", uşaqlar)

            göstər = hədəf.metod_tap("göstər")
            if göstər is None:
                raise AlqorXəta(
                    "TipXətası",
                    f"`{hədəf.ad}` komponentində `göstər()` metodu yoxdur",
                    yer, "ALQ-T053",
                )
            nəticə = self.funksiya_çağır(göstər.bağla(n), [], {}, yer)
            if isinstance(nəticə, Element):
                # Ağac hansı nümunədən gəldiyini xatırlasın: `pəncərə`
                # vəziyyət dəyişəndə `göstər()`-i yenidən çağırır.
                nəticə.komponent = n
            return nəticə

        if isinstance(hədəf, Çağırılan):
            adlı = dict(atributlar)
            if uşaqlar:
                adlı.setdefault("uşaqlar", uşaqlar)
            return hədəf.çağır(self, [], adlı, yer)

        raise AlqorXəta(
            "TipXətası",
            f"`<{ad} />` sinif və ya funksiya olmalıdır, "
            f"`{tip_adı(hədəf)}` gəlib", yer, "ALQ-T008")

    # ── Blok şəklində ifadələr ────────────────────────────────────────

    def _e_şərt_ifadəsi(self, e: A.ŞərtIfadəsi, m: Mühit) -> Any:
        for şərt, dəyər in e.budaqlar:
            if self._məntiq(şərt, m):
                return self._ifadə(dəyər, m)
        if e.yoxsa is not None:
            return self._ifadə(e.yoxsa, m)
        return None

    def _e_blok_ifadəsi(self, e: A.BlokIfadəsi, m: Mühit) -> Any:
        try:
            self._blok(e.gövdə, m.alt())
        except VerSiqnalı as s:
            return s.dəyər
        return None

    def _e_lambda(self, e: A.Lambda, m: Mühit) -> Funksiya:
        mühit = m
        if e.tutmalar:
            mühit = m.alt()
            for ad in e.tutmalar:
                mühit.elan(ad, m.al(ad))
        return Funksiya("<lambda>", e.parametrlər, e.gövdə, mühit,
                        e.asinxron, e.generator)

    # ═══════════════════════════════════════════════════════════════════
    #  Köməkçilər
    # ═══════════════════════════════════════════════════════════════════

    def _məntiq(self, e: A.İfadə, m: Mühit) -> bool:
        dəyər = self._ifadə(e, m)
        if not isinstance(dəyər, bool):
            raise AlqorXəta(
                "TipXətası",
                f"şərt `məntiq` tipi olmalıdır, `{tip_adı(dəyər)}` gəlib",
                getattr(e, "yer", None), "ALQ-T007")
        return dəyər

    @staticmethod
    def _dəyər_doğrudur(dəyər: Any) -> bool:
        if not isinstance(dəyər, bool):
            raise AlqorXəta("TipXətası",
                            f"şərt `məntiq` olmalıdır, "
                            f"`{tip_adı(dəyər)}` gəlib", None, "ALQ-T007")
        return dəyər

    def _iterasiya(self, dəyər: Any, yer: Yer | None):
        if isinstance(dəyər, Nümunə):
            metod = dəyər.sinif.metod_tap("iterator")
            if metod is not None:
                return self._iterasiya(
                    self.funksiya_çağır(metod.bağla(dəyər), [], {}, yer),
                    yer)
            if dəyər.sinif.metod_tap("uzunluq") and \
                    dəyər.sinif.metod_tap("al"):
                n = self.funksiya_çağır(
                    dəyər.sinif.metod_tap("uzunluq").bağla(dəyər), [], {})
                return (self._indeks_al(dəyər, i, yer) for i in range(n))
        if isinstance(dəyər, AlqorGenerator):
            return iter(dəyər)
        if isinstance(dəyər, dict):
            return iter(list(dəyər.keys()))
        if isinstance(dəyər, (list, tuple, set, str, bytes, AlqorDiapazon)):
            return iter(dəyər)
        if isinstance(dəyər, Sadalama):
            return iter([dəyər.variantlar[a] for a in dəyər.sıra])
        f = getattr(type(dəyər), "alqor_iterasiya", None)
        if f is not None:
            return f(dəyər, yer)
        raise AlqorXəta("TipXətası",
                        f"`{tip_adı(dəyər)}` üzərində dövr qurulmur", yer,
                        "ALQ-T009")


# ═══════════════════════════════════════════════════════════════════════
#  Köməkçi daxili tiplər
# ═══════════════════════════════════════════════════════════════════════

class _SapYerli(threading.local):
    """
    Hər sapda müstəqil icra vəziyyəti.

    Korutin gövdəsi və `paralel(...)` ayrı saplarda işləyir. Dərinlik
    sayğacı, `gecikdir` yığını və cari `ver` funksiyası sap başına
    saxlanılmalıdır, yoxsa bir sap digərinin vəziyyətini pozar.
    """

    def __init__(self):
        self.dərinlik: int = 0
        self.gecikdirilmiş: list[list[tuple[A.İfadə, Mühit]]] = []
        self.ver = None


class _Üst:
    __slots__ = ("nümunə", "sinif")

    def __init__(self, nümunə: Any, sinif: Any):
        self.nümunə = nümunə
        self.sinif = sinif


class _QurucuİstinadI:
    __slots__ = ("sinif", "ad")

    def __init__(self, sinif: Sinif, ad: str):
        self.sinif = sinif
        self.ad = ad


class _TipAliası:
    __slots__ = ("ad", "hədəf")

    def __init__(self, ad: str, hədəf: A.TipQovşağı):
        self.ad = ad
        self.hədəf = hədəf

    def __repr__(self) -> str:
        return f"<tip {self.ad}>"


class _VariantQurucusu:
    """Cəbri sadalama variantı: `Nəticə.Uğur(5)`"""

    def __init__(self, sadalama: Sadalama, variant: A.SadalamaVariantı,
                 sıra: int):
        self.sadalama = sadalama
        self.variant = variant
        self.sıra = sıra

    def yarat(self, icraçı: İcraçı, arqumentlər: list,
              adlı: dict) -> SadalamaDəyəri:
        sahələr: dict[str, Any] = {}
        for i, p in enumerate(self.variant.parametrlər):
            if i < len(arqumentlər):
                sahələr[p.ad] = arqumentlər[i]
            elif p.ad in adlı:
                sahələr[p.ad] = adlı[p.ad]
            else:
                sahələr[p.ad] = None
        return SadalamaDəyəri(self.sadalama, self.variant.ad, self.sıra,
                              None, sahələr)

    def __repr__(self) -> str:
        return f"<variant {self.sadalama.ad}.{self.variant.ad}>"


# ── Format köməkçiləri ─────────────────────────────────────────────────

def format_spec_tam(dəyər: Any, spec: str) -> str:
    n = int(dəyər)
    return {"x": f"{n:x}", "X": f"{n:X}",
            "b": f"{n:b}", "o": f"{n:o}"}[spec]


def format_spec_ümumi(dəyər: Any, spec: str) -> str:
    return format(dəyər, spec)


# ── Operator → metod uyğunluğu (Spesifikasiya § 6.4) ───────────────────

def _kitabxana_operatoru(op: str, sol: Any, sağ: Any) -> Any:
    f = getattr(type(sol), "alqor_operator", None)
    if f is not None:
        n = f(sol, op, sağ, False)
        if n is not NotImplemented:
            return n
    f = getattr(type(sağ), "alqor_operator", None)
    if f is not None and op != "əks":
        return f(sağ, op, sol, True)
    return NotImplemented


_OPERATOR_METODLARI = {
    "+": "topla", "-": "çıx", "*": "vur", "/": "böl",
    "%": "qalıq", "**": "qüvvət",
}


# ═══════════════════════════════════════════════════════════════════════
#  Dispetçer cədvəlləri
# ═══════════════════════════════════════════════════════════════════════

_CÜMLƏLƏR: dict[type, Any] = {
    A.İfadəCümləsi: İcraçı._c_ifadə,
    A.DəyişənElanı: İcraçı._c_dəyişən,
    A.Şərt: İcraçı._c_şərt,
    A.Varsa: İcraçı._c_varsa,
    A.Yoxdursa: İcraçı._c_yoxdursa,
    A.Seç: İcraçı._c_seç,
    A.NəQədərKi: İcraçı._c_nə_qədər_ki,
    A.Həmişə: İcraçı._c_həmişə,
    A.Təkrarla: İcraçı._c_təkrarla,
    A.TəkrarlaNəQədər: İcraçı._c_təkrarla_nə_qədər,
    A.Hər: İcraçı._c_hər,
    A.Dayan: İcraçı._c_dayan,
    A.DavamEt: İcraçı._c_davam,
    A.Qaytar: İcraçı._c_qaytar,
    A.Ver: İcraçı._c_ver,
    A.At: İcraçı._c_at,
    A.Cəhd: İcraçı._c_cəhd,
    A.İddia: İcraçı._c_iddia,
    A.Təmin: İcraçı._c_təmin,
    A.Gecikdir: İcraçı._c_gecikdir,
    A.İstifadə: İcraçı._c_istifadə,
    A.Keç: İcraçı._c_keç,
    A.DayanNöqtəsi: İcraçı._c_dayan_nöqtəsi,
    A.Global: İcraçı._c_global,
    A.FunksiyaElanı: İcraçı._c_funksiya,
    A.SinifElanı: İcraçı._c_sinif,
    A.InterfeysElanı: İcraçı._c_interfeys,
    A.QarışıqElanı: İcraçı._c_qarışıq,
    A.SadalamaElanı: İcraçı._c_sadalama,
    A.TipAliası: İcraçı._c_tip_aliası,
    A.Genişlətmə: İcraçı._c_genişlətmə,
    A.ModulElanı: İcraçı._c_modul,
    A.İdxal: İcraçı._c_idxal,
    A.İxracSiyahısı: İcraçı._c_ixrac_siyahısı,
    A.Başlanğıc: İcraçı._c_başlanğıc,
    A.Bitiş: İcraçı._c_bitiş,
    A.Artırma: İcraçı._c_artırma,
}

_İFADƏLƏR: dict[type, Any] = {
    A.Literal: İcraçı._e_literal,
    A.ŞablonMətn: İcraçı._e_şablon,
    A.Ad: İcraçı._e_ad,
    A.Özü: İcraçı._e_özü,
    A.Üst: İcraçı._e_üst,
    A.İkili: İcraçı._e_ikili,
    A.TəkOperand: İcraçı._e_tək,
    A.Mənimsətmə: İcraçı._e_mənimsətmə,
    A.Çağırış: İcraçı._e_çağırış,
    A.Üzv: İcraçı._e_üzv,
    A.İndeks: İcraçı._e_indeks,
    A.Dilim: İcraçı._e_dilim,
    A.Yeni: İcraçı._e_yeni,
    A.Çevirmə: İcraçı._e_çevirmə,
    A.TipYoxlama: İcraçı._e_tip_yoxlama,
    A.Üzvlük: İcraçı._e_üzvlük,
    A.BoşYoxlama: İcraçı._e_boş_yoxlama,
    A.Boru: İcraçı._e_boru,
    A.MəcburiAçma: İcraçı._e_məcburi_açma,
    A.Yayma: İcraçı._e_yayma,
    A.Gözlə: İcraçı._e_gözlə,
    A.SiyahıLiteralı: İcraçı._e_siyahı,
    A.LüğətLiteralı: İcraçı._e_lüğət,
    A.DəstLiteralı: İcraçı._e_dəst,
    A.KortejLiteralı: İcraçı._e_kortej,
    A.Diapazon: İcraçı._e_diapazon,
    A.Qurma: İcraçı._e_qurma,
    A.ŞərtIfadəsi: İcraçı._e_şərt_ifadəsi,
    A.BlokIfadəsi: İcraçı._e_blok_ifadəsi,
    A.Lambda: İcraçı._e_lambda,
    A.JSXElement: İcraçı._e_jsx,
    A.JSXParça: İcraçı._e_jsx_parça,
}
