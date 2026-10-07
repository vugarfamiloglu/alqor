"""
Alqor — Lekser.

Mənbə mətnini token axınına çevirir.

Əsas xüsusiyyətlər:
  • Çox sözlü açar sözlər burada birləşdirilir (`nə qədər ki` → bir token)
  • ASCII açar sözlər kanonik formaya salınır (`eger` → `əgər`) + ALQ-L020
  • Şablon mətnlər rekursiv leksə edilir (`"Salam, {ad}!"`)
  • Yeni sətir ifadə ayırıcısıdır, mötərizə daxilində udulur
"""

from __future__ import annotations
import unicodedata

from . import acar_sozler as AS
from .elifba import (ad_başlanğıcı_ola_bilər, ad_davamı_ola_bilər,
                     hərfdir, rəqəmdir)
from .menbe import Mənbə
from .token import (ACANLAR, BAGLAYANLAR, IFADE_BITIREN_LITERALLAR,
                    IFADE_BITIREN_OP, OPERATORLAR_1,
                    OPERATORLAR_2, OPERATORLAR_3, KodParçası, MətnParçası,
                    Növ, Parça, Token, Yer)
from .xeta import XətaToplayıcı, mesaj

TAM_HEDD = 2 ** 63            # işarəsiz hədd (unary `-` ayrıca operatordur)

# ═══════════════════════════════════════════════════════════════════════
#  Kontekst yığını — yeni sətir udulmasını idarə edir
# ═══════════════════════════════════════════════════════════════════════
#
#  Problem: mötərizə içində yeni sətirlər udulur ki, çoxsətirli arqument
#  siyahısı işləsin. Amma arqument kimi verilən anonim funksiyanın GÖVDƏSİ
#  də mötərizə içindədir — orada yeni sətir ifadə ayırıcısıdır:
#
#      s.qrup("/api", funksiya(q)
#          q.al("/a", idarəedici)      ← bu sətir ayrılmalıdır!
#          q.al("/b", idarəedici)
#      son)
#
#  Həll: tək dərinlik sayğacı yerinə KONTEKST YIĞINI.
#    • `(` `[` `{`        → MÖTƏRİZƏ yığ
#    • `)` `]` `}`        → ən yaxın MÖTƏRİZƏ-yə qədər boşalt (özünü sağaldır)
#    • blok açan açar söz → BLOK yığ
#    • `son`              → ən yaxın BLOK-u götür (MÖTƏRİZƏ-dən keçmir)
#
#  Qayda: yeni sətir YALNIZ yığın boş olanda, və ya təpədə BLOK olanda
#  emissiya olunur.

MÖTƏRİZƏ = "mötərizə"
BLOK = "blok"

#  `son` ilə bitdiyi ETİBARLI olan blok açanları.
#  `qurucu` və `xassə` qəsdən yoxdur — onların qısa (gövdəsiz) forması var,
#  həm də gövdələri həmişə `sinif` blokunun içindədir.
BLOK_ACANLAR = frozenset({
    "funksiya", "metod", "silinsin", "blok",
    "sinif", "struktur", "interfeys", "sadalama", "modul", "obyekt",
    "qarışıq", "komponent", "mağaza", "genişlət",
    "əgər", "varsa", "yoxdursa", "seç",
    "nə qədər ki", "həmişə", "təkrarla", "hər",
    "cəhd et", "təmin", "istifadə",
})

QACIS = {
    "n": "\n", "r": "\r", "t": "\t", "0": "\0",
    "\\": "\\", '"': '"', "'": "'", "`": "`",
    "e": "\x1b", "{": "{", "}": "}",
}

DIRNAQ = chr(34)         # "
APOSTROF = chr(39)       # '
QRAVIS = chr(96)         # `
TERS_KESIK = chr(92)     # \

ONALTILIQ = "0123456789abcdefABCDEF"
IKILIK = "01"
SEKKIZLIK = "01234567"

# Birləşən işarələr (char literalında qrafem klasteri üçün)
_BIRLESEN = ("Mn", "Mc", "Me")


class Lekser:
    def __init__(self, mənbə: Mənbə, toplayıcı: XətaToplayıcı,
                 ascii_xəbərdarlığı: bool = True):
        self.s = mənbə
        self.m = mənbə.mətn
        self.n = len(self.m)
        self.i = 0
        self.x = toplayıcı
        self.ascii_xəbərdarlığı = ascii_xəbərdarlığı
        self.yığın: list[str] = []        # MÖTƏRİZƏ / BLOK kontekstləri
        self.direktivlər: dict[str, str] = {}
        self._tab_xəbərdarlığı_verildi = False

    # ═══════════════════════════════════════════════════════════════════
    #  Giriş nöqtəsi
    # ═══════════════════════════════════════════════════════════════════

    def leksə(self) -> list[Token]:
        tokenlər: list[Token] = []
        self._shebang_atla()

        while self.i < self.n:
            if self.x.dolubmu():
                break
            self._token_oxu(tokenlər)

        self._sətir_sonu(tokenlər)
        tokenlər.append(Token(Növ.FAYL_SONU, None,
                              self.s.yer(self.n, 0)))
        return tokenlər

    # ═══════════════════════════════════════════════════════════════════
    #  Bir addım
    # ═══════════════════════════════════════════════════════════════════

    def _token_oxu(self, hədəf: list[Token],
                   interpolyasiyada: bool = False) -> None:
        if self._boşluq_atla(interpolyasiyada):
            return
        if self.i >= self.n:
            return

        c = self.m[self.i]
        baş = self.i

        # ── Yeni sətir ──────────────────────────────────────────
        if c == "\n":
            self.i += 1
            if not interpolyasiyada:
                self._sətir_sonu(hədəf)
            return

        # ── Şərhlər ─────────────────────────────────────────────
        if c == "/" and self._gör(1) in ("/", "*"):
            self._şərh_oxu(hədəf)
            return

        # ── Prefiksli mətnlər: x"..." və b"..." ─────────────────
        if c in "xb" and self._gör(1) == '"':
            self.i += 1
            self._mətn_oxu(hədəf, baş, xam=(c == "x"), bayt=(c == "b"))
            return

        # ── Mətn literalları ────────────────────────────────────
        if c in "\"'":
            self._mətn_oxu(hədəf, baş)
            return

        # ── Simvol literalı ─────────────────────────────────────
        if c == "`":
            self._simvol_oxu(hədəf)
            return

        # ── Ədədlər ─────────────────────────────────────────────
        if rəqəmdir(c):
            self._ədəd_oxu(hədəf)
            return

        # ── Ad / açar söz ───────────────────────────────────────
        if ad_başlanğıcı_ola_bilər(c):
            self._ad_oxu(hədəf)
            return

        # ── İnterfeys sintaksisi (JSX) ──────────────────────────
        #  `<` ifadə mövqeyindədirsə, element xam skan edilir.
        if c == "<" and self._jsx_başlayır(hədəf):
            self._jsx_oxu(hədəf)
            return

        # ── Operatorlar ─────────────────────────────────────────
        if self._op_oxu(hədəf):
            return

        # ── Tanınmayan simvol ───────────────────────────────────
        self.i += 1
        ad = _unicode_adı(c)
        self.x.xəta("ALQ-L002", mesaj("ALQ-L002"),
                    self.s.yer(baş, 1),
                    f"'{c}' (U+{ord(c):04X}, {ad})",
                    "bu simvol Alqor kodunda istifadə oluna bilməz",
                    "mətn literalı daxilində istifadə etmək istəyirsinizsə "
                    'dırnaq içinə alın: "..."')

    # ═══════════════════════════════════════════════════════════════════
    #  Boşluq və sətir sonu
    # ═══════════════════════════════════════════════════════════════════

    def _boşluq_atla(self, interpolyasiyada: bool = False) -> bool:
        """Boşluq/tab atlayır. Nəsə atlanıbsa True."""
        baş = self.i
        sətir_başıdır = baş == 0 or (baş > 0 and self.m[baş - 1] == "\n")
        boşluq = tab = False

        while self.i < self.n:
            c = self.m[self.i]
            if c == " ":
                boşluq = True
            elif c == "\t":
                tab = True
            elif c == "\n" and interpolyasiyada:
                pass                      # interpolyasiya daxilində adi boşluq
            else:
                break
            self.i += 1

        if (sətir_başıdır and boşluq and tab
                and not self._tab_xəbərdarlığı_verildi):
            self._tab_xəbərdarlığı_verildi = True
            self.x.xəbərdarlıq(
                "ALQ-L012", mesaj("ALQ-L012"),
                self.s.yer(baş, self.i - baş),
                "girintidə hər ikisi işlənib",
                "Alqor standartı: 4 boşluq, tabulyasiya yox",
                "düzəltmək: alqorfmt .")
        return self.i > baş

    def _sətir_sonu(self, hədəf: list[Token]) -> None:
        """
        SETIR_SONU emissiya edir — udulma qaydaları ilə (Spes. § 1.11).
        """
        # Yığın boş deyilsə və təpədə MÖTƏRİZƏ varsa — yeni sətir udulur
        if self.yığın and self.yığın[-1] == MÖTƏRİZƏ:
            return
        son = self._son_əhəmiyyətli(hədəf)
        if son is None:
            return                                    # faylın başı
        if son.növ is Növ.SETIR_SONU:
            return                                    # təkrar yox
        if son.növ is Növ.OP and son.dəyər not in IFADE_BITIREN_OP:
            return                                    # operatorla bitib
        if son.növ is Növ.ACAR and son.dəyər in AS.DAVAM_ACAR_SOZLERI:
            return
        if self._növbəti_sətir_zəncirdir():
            return                                    # `.metod()` zənciri
        hədəf.append(Token(Növ.SETIR_SONU, None, self.s.yer(self.i, 0)))

    def _növbəti_sətir_zəncirdir(self) -> bool:
        """
        Növbəti əhəmiyyətli sətir `.ad` və ya `?.ad` ilə başlayırmı?
        Belədirsə ifadə davam edir (Spes. § 1.11):

            dəyişən a = konsol.arqumentlər()
                .proqram("hesabla")
                .təhlil()

        Boş və yalnız şərhdən ibarət sətirlər ötürülür. `..` (diapazon)
        və `...` (yayma) ilə başlayan sətir zəncir deyil.
        """
        m, i, n = self.m, self.i, self.n
        while i < n:
            c = m[i]
            if c in " \t\r\n":
                i += 1
                continue
            if m.startswith("//", i):
                j = m.find("\n", i)
                if j == -1:
                    return False
                i = j + 1
                continue
            break
        if m.startswith("?.", i):
            i += 2
        elif i < n and m[i] == "." and not m.startswith("..", i):
            i += 1
        else:
            return False
        return i < n and (m[i].isalpha() or m[i] == "_")

    @staticmethod
    def _son_əhəmiyyətli(hədəf: list[Token]) -> Token | None:
        for t in reversed(hədəf):
            if t.növ not in (Növ.SENED, Növ.DIREKTIV):
                return t
        return None

    def _üzv_mövqeyidir(self, hədəf: list[Token]) -> bool:
        """Bu ad `.` və ya `?.`-dan sonra gəlirmi (obyekt üzvüdür)?"""
        son = self._son_əhəmiyyətli(hədəf)
        return son is not None and son.opdur(".", "?.")

    def _shebang_atla(self) -> None:
        if self.m.startswith("#!"):
            yer = self.m.find("\n")
            self.i = self.n if yer == -1 else yer + 1

    # ═══════════════════════════════════════════════════════════════════
    #  Şərhlər
    # ═══════════════════════════════════════════════════════════════════

    def _şərh_oxu(self, hədəf: list[Token]) -> None:
        baş = self.i
        if self._gör(1) == "*":
            self._blok_şərhi(baş)
            return

        # // ilə başlayan
        self.i += 2
        modul_sənədi = self._gör(0) == "!"
        sənəd = self._gör(0) == "/"
        if modul_sənədi or sənəd:
            self.i += 1

        sətir_sonu = self.m.find("\n", self.i)
        if sətir_sonu == -1:
            sətir_sonu = self.n
        məzmun = self.m[self.i:sətir_sonu]
        self.i = sətir_sonu

        if sənəd or modul_sənədi:
            # Yalnız bir aparıcı boşluq atılır — sənəddəki kod
            # nümunələrinin girintisi qorunmalıdır
            if məzmun.startswith(" "):
                məzmun = məzmun[1:]
            hədəf.append(Token(Növ.SENED, məzmun.rstrip(),
                               self.s.yer(baş, self.i - baş),
                               xam=self.m[baş:self.i]))
            return

        sıyrılmış = məzmun.strip()
        if sıyrılmış.startswith("alqor:"):
            əmr = sıyrılmış[6:].strip()
            self._direktiv(əmr, self.s.yer(baş, self.i - baş))
            hədəf.append(Token(Növ.DIREKTIV, əmr,
                               self.s.yer(baş, self.i - baş)))

    def _blok_şərhi(self, baş: int) -> None:
        self.i += 2
        dərinlik = 1
        while self.i < self.n and dərinlik > 0:
            if self.m.startswith("/*", self.i):
                dərinlik += 1
                self.i += 2
            elif self.m.startswith("*/", self.i):
                dərinlik -= 1
                self.i += 2
            else:
                self.i += 1
        if dərinlik > 0:
            self.x.xəta("ALQ-L004", mesaj("ALQ-L004"),
                        self.s.yer(baş, 2),
                        "burada açılıb, heç yerdə bağlanmayıb",
                        "`*/` əlavə edin",
                        "şərh blokları iç-içə ola bilər — "
                        "hər `/*` üçün bir `*/` lazımdır")

    def _direktiv(self, əmr: str, yer: Yer) -> None:
        self.direktivlər[əmr] = əmr
        sadə = əmr.replace("ə", "e").replace("ı", "i").replace("ö", "o") \
                  .replace("ü", "u").replace("ç", "c").replace("ş", "s") \
                  .replace("ğ", "g")
        if sadə.startswith("ascii-xeberdarliq") and "sondur" in sadə:
            self.ascii_xəbərdarlığı = False
        elif sadə.startswith("xeta-sondur"):
            kod = əmr.split()[-1]
            self.x.söndür(kod)

    # ═══════════════════════════════════════════════════════════════════
    #  Ad və açar sözlər
    # ═══════════════════════════════════════════════════════════════════

    def _ad_oxu(self, hədəf: list[Token]) -> None:
        baş = self.i
        while self.i < self.n and ad_davamı_ola_bilər(self.m[self.i]):
            self.i += 1
        söz = self.m[baş:self.i]

        kanonik, ascii_idi = AS.kanonikləşdir(söz)

        if kanonik is None:
            # Ehtiyat sözlər: yalnız müstəqil ad mövqeyində xəbərdarlıq.
            # `veb.makro` kimi üzv adında xəbərdarlıq verilmir — orada
            # ad həmişə obyektin öz üzvüdür, dilin açar sözü ola bilməz.
            if söz in AS.EHTIYAT and not self._üzv_mövqeyidir(hədəf):
                self.x.xəbərdarlıq(
                    "ALQ-L016", mesaj("ALQ-L016"),
                    self.s.yer(baş, len(söz)),
                    f"'{söz}' gələcək versiyada açar söz ola bilər",
                    "başqa ad seçmək tövsiyə olunur")
            hədəf.append(Token(Növ.AD, söz, self.s.yer(baş, len(söz)),
                               xam=söz))
            return

        # ── Çox sözlü birləşmə cəhdi ────────────────────────────
        birləşmə = self._çox_sözlü_cəhd(kanonik)
        if birləşmə is not None:
            kanon, son_mövqe, ascii_var = birləşmə
            self.i = son_mövqe
            if ascii_var and self.ascii_xəbərdarlığı:
                self._ascii_xəbərdarlıq(baş, self.i - baş, kanon)
            self._yığını_yenilə(kanon)
            hədəf.append(Token(Növ.ACAR, kanon,
                               self.s.yer(baş, self.i - baş),
                               xam=self.m[baş:self.i],
                               ascii_idi=ascii_var))
            return

        # Birləşmə olmadı — qısa aliasları indi tətbiq et (`davam` → `davam et`)
        kanonik = AS.tamamla(kanonik)

        if ascii_idi and self.ascii_xəbərdarlığı:
            self._ascii_xəbərdarlıq(baş, len(söz), kanonik)

        self._yığını_yenilə(kanonik)
        hədəf.append(Token(Növ.ACAR, kanonik,
                           self.s.yer(baş, len(söz)),
                           xam=söz, ascii_idi=ascii_idi))

    def _çox_sözlü_cəhd(self, ilk: str):
        """
        `nə` görəndə `qədər ki`-ni axtarır.

        Qaytarır: (kanonik, yeni_mövqe, ascii_var) | None
        Yalnız EYNİ SƏTİRDƏ axtarır — yeni sətir birləşməni kəsir.
        """
        naxışlar = AS.COX_SOZLU_INDEKS.get(ilk)
        if not naxışlar:
            return None

        for naxış in naxışlar:                 # uzundan qısaya
            mövqe = self.i
            ascii_var = False
            uğur = True
            for gözlənilən in naxış[1:]:
                # Yalnız boşluq/tab atla, yeni sətir YOX
                j = mövqe
                while j < self.n and self.m[j] in " \t":
                    j += 1
                k = j
                while k < self.n and ad_davamı_ola_bilər(self.m[k]):
                    k += 1
                if k == j:
                    uğur = False
                    break
                söz = self.m[j:k]
                kanon, ascii_idi = AS.kanonikləşdir(söz)
                if kanon != gözlənilən:
                    uğur = False
                    break
                ascii_var = ascii_var or ascii_idi
                mövqe = k
            if uğur:
                return AS.tamamla(" ".join(naxış)), mövqe, ascii_var
        return None

    def _yığını_yenilə(self, acar: str) -> None:
        """Blok açan açar sözləri və `son`-u kontekst yığınında izləyir."""
        if acar in BLOK_ACANLAR:
            self.yığın.append(BLOK)
        elif acar == "son":
            # Yalnız BLOK götür — MÖTƏRİZƏ-dən keçmirik
            if self.yığın and self.yığın[-1] == BLOK:
                self.yığın.pop()

    def _ascii_xəbərdarlıq(self, baş: int, uz: int, kanonik: str) -> None:
        yazılan = self.m[baş:baş + uz]
        self.x.xəbərdarlıq(
            "ALQ-L020", mesaj("ALQ-L020"),
            self.s.yer(baş, uz),
            f"'{yazılan}' → '{kanonik}'",
            f"kanonik forma: {kanonik}",
            "hamısını birdən düzəltmək: alqorfmt --ascii-düzəlt .",
            "bu xəbərdarlığı söndürmək: // alqor: ascii-xeberdarliq sondur")

    # ═══════════════════════════════════════════════════════════════════
    #  Ədədlər
    # ═══════════════════════════════════════════════════════════════════

    def _ədəd_oxu(self, hədəf: list[Token]) -> None:
        baş = self.i

        # ── Prefiksli formalar ──────────────────────────────────
        if (self.m[self.i] == "0"
                and self._gör(1) in ("x", "X", "b", "B", "o", "O")):
            növ_hərfi = self._gör(1)
            self.i += 2
            if növ_hərfi in "xX":
                icazəli, əsas, ad = ONALTILIQ, 16, "onaltılıq"
            elif növ_hərfi in "bB":
                icazəli, əsas, ad = IKILIK, 2, "ikilik"
            else:
                icazəli, əsas, ad = SEKKIZLIK, 8, "səkkizlik"

            rəqəm_başı = self.i
            while self.i < self.n and (self.m[self.i] in icazəli
                                       or self.m[self.i] == "_"):
                self.i += 1
            rəqəmlər = self.m[rəqəm_başı:self.i].replace("_", "")
            if not rəqəmlər:
                self.x.xəta("ALQ-L006", mesaj("ALQ-L006"),
                            self.s.yer(baş, self.i - baş),
                            f"`0{növ_hərfi}` prefiksindən sonra "
                            f"{ad} rəqəm yoxdur",
                            f"nümunə: 0{növ_hərfi}"
                            f"{'1F' if əsas == 16 else '101' if əsas == 2 else '755'}")
                hədəf.append(Token(Növ.TAM, 0, self.s.yer(baş, self.i - baş)))
                return
            self._ədəddən_sonra_yoxla(baş)
            dəyər = int(rəqəmlər, əsas)
            self._hədd_yoxla(dəyər, baş)
            hədəf.append(Token(Növ.TAM, dəyər,
                               self.s.yer(baş, self.i - baş),
                               xam=self.m[baş:self.i]))
            return

        # ── Onluq ───────────────────────────────────────────────
        self._rəqəmlər_atla()
        onluqdur = False

        # Kəsr hissəsi — `..` diapazonu ilə qarışdırmamaq üçün
        # nöqtədən sonra MÜTLƏQ rəqəm olmalıdır
        # `t.1.0` — kortej indeksindən sonrakı nöqtə kəsr deyil
        kortej_indeksi = (baş > 0 and self.m[baş - 1] == "."
                          and not (baş > 1 and self.m[baş - 2] == "."))
        if kortej_indeksi:
            pass
        elif (self._gör(0) == "." and rəqəmdir(self._gör(1))):
            onluqdur = True
            self.i += 1
            self._rəqəmlər_atla()
        elif (self._gör(0) == "." and self._gör(1) != "."
              and not hərfdir(self._gör(1) or " ")
              and self._gör(1) != "_"):
            # `5.` — § 1.9.2: nöqtədən sonra rəqəm olmalıdır. `5.mətnƏt()`
            # (metod), `1..3` (diapazon), `t.0` (kortej indeksi) toxunulmur
            self.x.xəta("ALQ-L006", mesaj("ALQ-L006"),
                        self.s.yer(baş, self.i + 1 - baş),
                        f"`{self.m[baş:self.i]}.` — nöqtədən sonra rəqəm "
                        "olmalıdır",
                        f"onluq ədəd: `{self.m[baş:self.i]}.0`")
            self.i += 1
            onluqdur = True

        # Eksponent
        if self._gör(0) in ("e", "E"):
            j = self.i + 1
            if j < self.n and self.m[j] in "+-":
                j += 1
            if j < self.n and rəqəmdir(self.m[j]):
                onluqdur = True
                self.i = j
                self._rəqəmlər_atla()

        xam = self.m[baş:self.i]
        self._ədəddən_sonra_yoxla(baş)
        təmiz = xam.replace("_", "")

        if onluqdur:
            hədəf.append(Token(Növ.ONLUQ, float(təmiz),
                               self.s.yer(baş, self.i - baş), xam=xam))
        else:
            dəyər = int(təmiz)
            self._hədd_yoxla(dəyər, baş)
            hədəf.append(Token(Növ.TAM, dəyər,
                               self.s.yer(baş, self.i - baş), xam=xam))

    def _rəqəmlər_atla(self) -> None:
        while self.i < self.n and (rəqəmdir(self.m[self.i])
                                   or self.m[self.i] == "_"):
            self.i += 1

    def _ədəddən_sonra_yoxla(self, baş: int) -> None:
        """`5abc` kimi yazılışı tutur."""
        if self.i < self.n and hərfdir(self.m[self.i]):
            pis_baş = self.i
            while self.i < self.n and ad_davamı_ola_bilər(self.m[self.i]):
                self.i += 1
            self.x.xəta("ALQ-L006", mesaj("ALQ-L006"),
                        self.s.yer(baş, self.i - baş),
                        "ədədlə identifikator birləşib",
                        "ədəd ilə ad arasında boşluq və ya operator lazımdır",
                        f"'{self.m[pis_baş:self.i]}' hissəsi gözlənilmirdi")

    def _hədd_yoxla(self, dəyər: int, baş: int) -> None:
        if dəyər > TAM_HEDD:
            self.x.xəta("ALQ-L007", mesaj("ALQ-L007"),
                        self.s.yer(baş, self.i - baş),
                        f"{dəyər} — 64 bit `tam` tipinə sığmır",
                        "maksimum: 9_223_372_036_854_775_807",
                        "daha böyük ədədlər üçün: riyaziyyat.böyükTam")

    # ═══════════════════════════════════════════════════════════════════
    #  Mətn literalları
    # ═══════════════════════════════════════════════════════════════════

    def _mətn_oxu(self, hədəf: list[Token], tam_baş: int,
                  xam: bool = False, bayt: bool = False) -> None:
        sitat = self.m[self.i]
        # Üçqat dırnaq prefikslərlə də işləyir: `x"""…"""` CSS, SQL və
        # HTML yerləşdirmək üçün yeganə təhlükəsiz formadır — nə qaçış,
        # nə interpolyasiya emal olunur, `{display:flex}` korlanmır.
        üçqat = self.m.startswith(sitat * 3, self.i)
        bağlayıcı = sitat * 3 if üçqat else sitat
        self.i += len(bağlayıcı)

        parçalar: list[Parça] = []
        bufer: list[str] = []
        bitdi = False

        while self.i < self.n:
            c = self.m[self.i]

            # ── Bağlanış ────────────────────────────────────────
            if self.m.startswith(bağlayıcı, self.i):
                self.i += len(bağlayıcı)
                bitdi = True
                break

            # ── Tək sətirli mətndə yeni sətir qadağandır ────────
            if c == "\n" and not üçqat:
                break

            # ── Xam mətn: qaçış yoxdur, interpolyasiya yoxdur ───
            if xam:
                bufer.append(c)
                self.i += 1
                continue

            # ── Qaçış ───────────────────────────────────────────
            if c == "\\":
                bufer.append(self._qaçış_oxu())
                continue

            # ── İnterpolyasiya ──────────────────────────────────
            if c == "{" and not bayt:
                if bufer:
                    parçalar.append(MətnParçası("".join(bufer)))
                    bufer = []
                self.i += 1
                parçalar.append(self._interpolyasiya_oxu(tam_baş))
                continue

            bufer.append(c)
            self.i += 1

        if bufer:
            parçalar.append(MətnParçası("".join(bufer)))

        yer = self.s.yer(tam_baş, self.i - tam_baş)

        if not bitdi:
            self.x.xəta("ALQ-L003", mesaj("ALQ-L003"),
                        self.s.yer(tam_baş, min(self.i - tam_baş,
                                                len(bağlayıcı))),
                        "bu mətn bağlanmayıb",
                        f"sonda `{bağlayıcı}` əlavə edin",
                        *(["çoxsətirli mətn üçün `\"\"\"` istifadə edin"]
                          if not üçqat else []))

        if üçqat:
            parçalar = _çoxsətirli_düzəlt(parçalar,
                                          self._girinti_tap(tam_baş))

        mətn = "".join(p.dəyər for p in parçalar
                       if isinstance(p, MətnParçası))

        if bayt:
            try:
                dəyər = mətn.encode("utf-8")
            except UnicodeEncodeError:
                dəyər = b""
            hədəf.append(Token(Növ.BAYT, dəyər, yer,
                               xam=self.m[tam_baş:self.i]))
            return

        hədəf.append(Token(Növ.METN, mətn, yer,
                           xam=self.m[tam_baş:self.i],
                           parçalar=parçalar, çoxsətirli=üçqat))

    def _girinti_tap(self, tam_baş: int) -> str:
        """Bağlayan `\"\"\"`-un olduğu sətrin girintisi."""
        bağ = self.i - 3
        sətir_başı = self.m.rfind("\n", tam_baş, bağ)
        if sətir_başı == -1:
            return ""
        prefiks = self.m[sətir_başı + 1:bağ]
        return prefiks if prefiks.strip() == "" else ""

    def _qaçış_oxu(self) -> str:
        baş = self.i
        self.i += 1                                   # `\`
        if self.i >= self.n:
            return ""
        c = self.m[self.i]
        self.i += 1

        if c in QACIS:
            return QACIS[c]

        # \u{259}
        if c == "u":
            if self._gör(0) != "{":
                self.x.xəta("ALQ-L005", mesaj("ALQ-L005"),
                            self.s.yer(baş, self.i - baş),
                            "`\\u` ardınca `{` gəlməlidir",
                            "nümunə: \\u{259} → ə")
                return ""
            self.i += 1
            rəqəm_başı = self.i
            while self.i < self.n and self.m[self.i] in ONALTILIQ:
                self.i += 1
            rəqəmlər = self.m[rəqəm_başı:self.i]
            if self._gör(0) == "}":
                self.i += 1
            if not rəqəmlər:
                self.x.xəta("ALQ-L008", mesaj("ALQ-L008"),
                            self.s.yer(baş, self.i - baş),
                            "kod nöqtəsi boşdur", "nümunə: \\u{259} → ə")
                return ""
            kod = int(rəqəmlər, 16)
            if kod > 0x10FFFF or 0xD800 <= kod <= 0xDFFF:
                self.x.xəta("ALQ-L008", mesaj("ALQ-L008"),
                            self.s.yer(baş, self.i - baş),
                            f"U+{kod:04X} etibarlı Unicode deyil",
                            "icazəli diapazon: U+0000 … U+10FFFF "
                            "(surroqatlar istisna)")
                return ""
            return chr(kod)

        # \x41
        if c == "x":
            rəqəm_başı = self.i
            while (self.i < self.n and self.i - rəqəm_başı < 2
                   and self.m[self.i] in ONALTILIQ):
                self.i += 1
            rəqəmlər = self.m[rəqəm_başı:self.i]
            if len(rəqəmlər) != 2:
                self.x.xəta("ALQ-L005", mesaj("ALQ-L005"),
                            self.s.yer(baş, self.i - baş),
                            "`\\x` ardınca iki onaltılıq rəqəm gəlməlidir",
                            "nümunə: \\x41 → A")
                return ""
            return chr(int(rəqəmlər, 16))

        self.x.xəta("ALQ-L005", mesaj("ALQ-L005"),
                    self.s.yer(baş, 2),
                    f"`\\{c}` tanınmayan qaçışdır",
                    "icazəli: \\n \\r \\t \\\\ \\\" \\' \\0 \\e "
                    "\\{ \\} \\u{...} \\xHH",
                    "tərs kəsiyin özü üçün: \\\\")
        return c

    def _interpolyasiya_oxu(self, mətn_başı: int) -> KodParçası:
        """`{` oxunduqdan sonra çağırılır, uyğun `}`-a qədər oxuyur."""
        baş = self.i
        yerli: list[Token] = []
        dərinlik = 0
        format: str | None = None

        while self.i < self.n:
            self._boşluq_atla(interpolyasiyada=True)
            if self.i >= self.n:
                break
            c = self.m[self.i]

            if dərinlik == 0 and c == "}":
                self.i += 1
                return KodParçası(yerli, format)

            if dərinlik == 0 and c == ":":
                self.i += 1
                f_başı = self.i
                while self.i < self.n and self.m[self.i] not in "}\n":
                    self.i += 1
                format = self.m[f_başı:self.i]
                if self._gör(0) == "}":
                    self.i += 1
                    return KodParçası(yerli, format)
                break

            if c == "\n":
                break

            əvvəl = len(yerli)
            köhnə_i = self.i
            self._token_oxu(yerli, interpolyasiyada=True)
            if self.i == köhnə_i:
                self.i += 1                          # ilişməyə qarşı
            for t in yerli[əvvəl:]:
                if t.növ is Növ.OP:
                    if t.dəyər in ACANLAR:
                        dərinlik += 1
                    elif t.dəyər in BAGLAYANLAR:
                        dərinlik -= 1

        self.x.xəta("ALQ-L011", mesaj("ALQ-L011"),
                    self.s.yer(baş - 1, 1),
                    "burada açılıb, `}` ilə bağlanmayıb",
                    "nümunə: \"Salam, {ad}!\"",
                    "fiqurlu mötərizənin özü üçün: \\{ və \\}")
        return KodParçası(yerli, format)

    # ═══════════════════════════════════════════════════════════════════
    #  Simvol literalı
    # ═══════════════════════════════════════════════════════════════════

    def _simvol_oxu(self, hədəf: list[Token]) -> None:
        baş = self.i
        self.i += 1                                   # açan `
        if self.i >= self.n:
            self._simvol_xətası(baş)
            return

        if self.m[self.i] == "\\":
            dəyər = self._qaçış_oxu()
        else:
            # Bir qrafem klasteri: baza + birləşən işarələr
            parça = [self.m[self.i]]
            self.i += 1
            while (self.i < self.n
                   and unicodedata.category(self.m[self.i]) in _BIRLESEN):
                parça.append(self.m[self.i])
                self.i += 1
            dəyər = "".join(parça)

        if self._gör(0) != "`":
            self._simvol_xətası(baş)
            return
        self.i += 1
        hədəf.append(Token(Növ.SIMVOL, dəyər,
                           self.s.yer(baş, self.i - baş),
                           xam=self.m[baş:self.i]))

    def _simvol_xətası(self, baş: int) -> None:
        self.x.xəta("ALQ-L017", mesaj("ALQ-L017"),
                    self.s.yer(baş, max(1, self.i - baş)),
                    "simvol literalı `` ` `` ilə bağlanmalıdır",
                    "nümunə: `ə`  `\\n`  `A`",
                    "bir simvoldan çox üçün mətn literalı: \"...\"")

    # ═══════════════════════════════════════════════════════════════════
    #  İnterfeys sintaksisi (JSX) — xam skan
    # ═══════════════════════════════════════════════════════════════════
    #
    #  Niyə lekserdə? JSX mətn məzmununda istənilən simvol qanunidir:
    #      <p>5 < 10 — bu normaldır</p>
    #  Lekser kontekstsiz işləsəydi, `—` ALQ-L002, apostrof isə
    #  bağlanmamış mətn xətası verərdi. Ona görə `<` ifadə mövqeyində
    #  görünəndə element BALANSLI TEQ UYĞUNLAŞDIRMASI ilə xam skan
    #  edilir və bir `Növ.JSX` tokeni kimi buraxılır. Parser (parser_jsx)
    #  həmin aralığı öz oxuyucusu ilə ayırır.

    def _jsx_başlayır(self, hədəf: list[Token]) -> bool:
        """
        `<` müqayisə operatorudur, yoxsa JSX elementinin başlanğıcı?

        Qayda: əvvəlki token İFADƏ BİTİRƏ BİLİRSƏ, `<` müqayisədir
        (`a < b`). Bitirə bilmirsə, JSX-dir (`qaytar <div>`, `f(<p/>)`).
        """
        növbəti = self._gör(1)
        if not (növbəti == ">" or növbəti == "/"
                or ad_başlanğıcı_ola_bilər(növbəti)):
            return False

        son = self._son_əhəmiyyətli(hədəf)
        if son is None:
            return True
        if son.növ in (Növ.AD, Növ.TAM, Növ.ONLUQ, Növ.METN,
                       Növ.SIMVOL, Növ.BAYT, Növ.JSX):
            return False
        if son.növ is Növ.OP:
            return son.dəyər not in IFADE_BITIREN_OP
        if son.növ is Növ.ACAR:
            return son.dəyər not in IFADE_BITIREN_LITERALLAR
        return True

    def _jsx_oxu(self, hədəf: list[Token]) -> None:
        """Elementi xam skan edib bir JSX tokeni emissiya edir."""
        baş = self.i
        son = self._jsx_sonunu_tap(baş)
        if son is None:
            self.x.xəta(
                "ALQ-P031", "İnterfeys elementi bağlanmayıb",
                self.s.yer(baş, 1), "burada açılıb",
                "bağlayan teq əlavə edin: </ad>",
                "öz-bağlanan element: <ad />")
            self.i += 1
            hədəf.append(Token(Növ.OP, "<", self.s.yer(baş, 1), xam="<"))
            return
        self.i = son
        hədəf.append(Token(Növ.JSX, (baş, son),
                           self.s.yer(baş, son - baş),
                           xam=self.m[baş:son]))

    def _jsx_sonunu_tap(self, baş: int) -> int | None:
        """Balanslı teq uyğunlaşdırması ilə elementin son ofseti."""
        i = baş
        dərinlik = 0
        while i < self.n:
            c = self.m[i]

            if c == "<":
                # `5 < 10` kimi mətn: `<`-dan sonra hərf/`/`/`>` yoxdursa
                # bu teq deyil, adi mətndir
                növbəti = self.m[i + 1] if i + 1 < self.n else ""
                if not (növbəti in ("/", ">")
                        or ad_başlanğıcı_ola_bilər(növbəti)):
                    if dərinlik == 0:
                        return None
                    i += 1
                    continue
                if növbəti == "/":
                    yer = self.m.find(">", i)
                    if yer == -1:
                        return None
                    i = yer + 1
                    dərinlik -= 1
                    if dərinlik == 0:
                        return i
                    if dərinlik < 0:
                        return None
                    continue

                nəticə = self._jsx_teqi_atla(i)
                if nəticə is None:
                    return None
                i, öz_bağlanan = nəticə
                if not öz_bağlanan:
                    dərinlik += 1
                elif dərinlik == 0:
                    return i
                continue

            if c == "{" and dərinlik > 0:
                nəticə = self._jsx_fiqurlu_atla(i)
                if nəticə is None:
                    return None
                i = nəticə
                continue

            if dərinlik == 0:
                return None
            i += 1
        return None

    def _jsx_teqi_atla(self, i: int):
        """`<` mövqeyindən teqin sonunu keçir → (yeni_i, öz_bağlanan)."""
        i += 1
        if i < self.n and self.m[i] == ">":
            return i + 1, False
        while i < self.n:
            c = self.m[i]
            if c == DIRNAQ or c == APOSTROF:
                i = self._jsx_literalı_atla(i)
                continue
            if c == "{":
                nəticə = self._jsx_fiqurlu_atla(i)
                if nəticə is None:
                    return None
                i = nəticə
                continue
            if c == "/" and i + 1 < self.n and self.m[i + 1] == ">":
                return i + 2, True
            if c == ">":
                return i + 1, False
            i += 1
        return None

    def _jsx_fiqurlu_atla(self, i: int) -> int | None:
        dərinlik = 0
        while i < self.n:
            c = self.m[i]
            if c in (DIRNAQ, APOSTROF, QRAVIS):
                i = self._jsx_literalı_atla(i)
                continue
            if c in "([{":
                dərinlik += 1
            elif c in ")]}":
                dərinlik -= 1
                if dərinlik == 0:
                    return i + 1
            i += 1
        return None

    def _jsx_literalı_atla(self, i: int) -> int:
        sitat = self.m[i]
        if self.m.startswith(sitat * 3, i):
            son = self.m.find(sitat * 3, i + 3)
            return self.n if son == -1 else son + 3
        i += 1
        while i < self.n:
            if self.m[i] == TERS_KESIK:
                i += 2
                continue
            if self.m[i] == sitat:
                return i + 1
            i += 1
        return i

    # ═══════════════════════════════════════════════════════════════════
    #  Operatorlar
    # ═══════════════════════════════════════════════════════════════════

    def _op_oxu(self, hədəf: list[Token]) -> bool:
        baş = self.i
        for cədvəl in (OPERATORLAR_3, OPERATORLAR_2, OPERATORLAR_1):
            uz = len(cədvəl[0])
            parça = self.m[self.i:self.i + uz]
            if parça in cədvəl:
                self.i += uz
                if parça in ACANLAR:
                    self.yığın.append(MÖTƏRİZƏ)
                elif parça in BAGLAYANLAR:
                    # Ən yaxın MÖTƏRİZƏ-yə qədər boşalt — bu, `son`-suz
                    # qalmış BLOK qeydlərini də təmizləyir (özünü sağaldır)
                    while self.yığın:
                        if self.yığın.pop() == MÖTƏRİZƏ:
                            break
                hədəf.append(Token(Növ.OP, parça,
                                   self.s.yer(baş, uz), xam=parça))
                return True
        return False

    # ═══════════════════════════════════════════════════════════════════
    #  Köməkçi
    # ═══════════════════════════════════════════════════════════════════

    def _gör(self, irəli: int = 0) -> str:
        """
        Mövqedən `irəli` qədər irəlidəki simvol, sonda isə boş sətir.

        DİQQƏT: nəticəni `in "abc"` ilə yoxlamayın — Python-da
        `"" in "abc"` DOĞRU qaytarır və sətrin sonunda yanlış nəticə
        verir. Kortej işlədin: `in ("a", "b", "c")`.
        """
        j = self.i + irəli
        return self.m[j] if j < self.n else ""


# ═══════════════════════════════════════════════════════════════════════
#  Çoxsətirli mətnin girintisinin silinməsi
# ═══════════════════════════════════════════════════════════════════════

def _çoxsətirli_düzəlt(parçalar: list[Parça], girinti: str) -> list[Parça]:
    """
    `\"\"\"` mətnlərində:
      • açan sərhəddən sonrakı ilk yeni sətri atır
      • bağlayan sərhədin girintisini bütün sətirlərdən çıxarır
    """
    if not parçalar:
        return parçalar

    nəticə: list[Parça] = []
    ilkdir = True
    for p in parçalar:
        if not isinstance(p, MətnParçası):
            nəticə.append(p)
            ilkdir = False
            continue

        mətn = p.dəyər
        if ilkdir and mətn.startswith("\n"):
            mətn = mətn[1:]
        if girinti:
            sətirlər = mətn.split("\n")
            if ilkdir and sətirlər and sətirlər[0].startswith(girinti):
                sətirlər[0] = sətirlər[0][len(girinti):]
            for k in range(1, len(sətirlər)):
                if sətirlər[k].startswith(girinti):
                    sətirlər[k] = sətirlər[k][len(girinti):]
            mətn = "\n".join(sətirlər)
        nəticə.append(MətnParçası(mətn))
        ilkdir = False

    # Sonuncu parçanın sonundaki girinti qalığını təmizlə
    if nəticə and isinstance(nəticə[-1], MətnParçası):
        son = nəticə[-1].dəyər
        if son.endswith("\n"):
            pass
        nəticə[-1] = MətnParçası(son)
    return nəticə


def _unicode_adı(c: str) -> str:
    try:
        return unicodedata.name(c)
    except ValueError:
        return "adsız simvol"


# ═══════════════════════════════════════════════════════════════════════
#  Rahat funksiyalar
# ═══════════════════════════════════════════════════════════════════════

def leksə(mətn: str, ad: str = "<yaddaş>") -> tuple[list[Token],
                                                    XətaToplayıcı]:
    """Mətni leksə edir — sınaqlar və REPL üçün."""
    x = XətaToplayıcı()
    s = Mənbə.mətndən(mətn, ad, x)
    return Lekser(s, x).leksə(), x


def faylı_leksə(yol) -> tuple[list[Token], XətaToplayıcı]:
    x = XətaToplayıcı()
    s = Mənbə.fayldan(yol, x)
    if s is None:
        return [], x
    return Lekser(s, x).leksə(), x
