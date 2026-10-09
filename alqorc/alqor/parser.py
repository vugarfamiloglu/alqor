"""
Alqor — Parser.

Token axınını AAC-yə çevirir.

Üsul:
  • Cümlələr və elanlar üçün rekursiv enmə (recursive descent)
  • İfadələr üçün prioritet dırmaşması (precedence climbing / Pratt)
  • Xətadan sonra bərpa: növbəti cümlə sərhədinə qədər atlanır,
    beləliklə bir keçiddə bir çox xəta bildirilir
"""

from __future__ import annotations

from . import acar_sozler as AS
from . import aac as A
from .token import Növ, Token, Yer
from .xeta import XətaToplayıcı

# ═══════════════════════════════════════════════════════════════════════
#  Operator prioritetləri (Spesifikasiya § 3.4)
#  Böyük rəqəm = daha sıx bağlayır
# ═══════════════════════════════════════════════════════════════════════

#  op → (prioritet, sağdan_assosiativ)
PRIORITET: dict[str, tuple[int, bool]] = {
    "|>": (1, False),
    "??": (2, True),
    "və ya": (3, False), "||": (3, False),
    "və": (4, False), "&&": (4, False),
    "==": (5, False), "!=": (5, False),
    "<": (6, False), ">": (6, False), "<=": (6, False), ">=": (6, False),
    "<=>": (6, False),
    "içindədir": (6, False), "tipidir": (6, False),
    "boşdur": (6, False), "boş deyil": (6, False),
    "..": (7, False), "..<": (7, False),
    "|": (8, False),
    "^": (9, False),
    "&": (10, False),
    "<<": (11, False), ">>": (11, False), ">>>": (11, False),
    "+": (12, False), "-": (12, False),
    "*": (13, False), "/": (13, False), "~/": (13, False), "%": (13, False),
    "kimi": (14, False), "kimi?": (14, False),
    # 15 = tək operandlı (unary)
    "**": (16, True),
}

TƏK_OPERATORLAR = ("-", "+", "!", "~")
TƏK_ACARLAR = ("deyil",)

MƏNİMSƏTMƏ_OPLARI = (
    "=", "+=", "-=", "*=", "/=", "~/=", "%=", "**=",
    "&=", "|=", "^=", "<<=", ">>=", "??=", "?=",
)

#  Tip adları açar söz DEYİL — öncədən elan olunmuş identifikatorlardır
#  (bax: acar_sozler.TIP_ADLARI). Parser onları adi `AD` tokeni kimi görür,
#  ona görə `xassə mətn: mətn` işləyir.
TİP_ADLARI = AS.TIP_ADLARI

GÖRÜNÜŞLƏR = frozenset({"açıq", "gizli", "qorunan"})

#  Sinif gövdəsində üzv elanını başladan açar sözlər.
#  Qurucunun qısa formasını tam formadan ayırmaq üçün lazımdır.
SINIF_UZV_ACARLARI = (
    "metod", "xassə", "qurucu", "silinsin", "statik", "mücərrəd",
    "tənbəl", "əvəz et", "açıq", "gizli", "qorunan",
    "sinif", "struktur", "interfeys", "sadalama", "funksiya",
)

# Sənəd şərhi ilə elan açar sözü arasında ola bilən sözlər
SƏNƏD_MODİFİKATORLARI = frozenset({
    "ixrac et", "ixrac", "et", "açıq", "gizli", "qorunan", "statik",
    "mücərrəd", "asinxron", "tənbəl", "standart", "son", "əvəz et",
})
# Sənədi daşıyan elanlar
ELAN_AÇARLARI = frozenset({
    "funksiya", "metod", "sinif", "struktur", "interfeys", "sadalama",
    "modul", "komponent", "qurucu", "xassə", "sabit", "dəyişən",
    "dəyişməz", "tip", "obyekt", "qarışıq", "mağaza", "genişlət",
})

# Blokun bitdiyini bildirən açar sözlər
BLOK_SONLARI = frozenset({
    "son", "yoxsa", "yoxsa əgər", "hal", "digər hallarda",
    "tut", "nəhayət",
})

# `son <növ>` formasında icazəli növlər
SON_NÖVLƏRİ = frozenset({
    "əgər", "funksiya", "sinif", "metod", "seç", "təkrarla", "hər",
    "cəhd", "nə qədər ki", "modul", "interfeys", "sadalama", "struktur",
    "qurucu", "xassə", "həmişə", "blok", "istifadə", "genişlət",
    "komponent", "mağaza", "obyekt", "qarışıq",
})

OX_FORMALARI = ("→", "->")


class ParserXətası(Exception):
    """Daxili — bərpa mexanizmi üçün."""


class Parser:
    def __init__(self, tokenlər: list[Token], mənbə,
                 toplayıcı: XətaToplayıcı):
        self.t = [x for x in tokenlər if x.növ is not Növ.DIREKTIV]
        self.sənədlər = {}          # mövqe → sənəd mətni
        self.modul_sənədi: str | None = None
        self._sənədləri_topla(tokenlər)
        self.t = [x for x in self.t if x.növ is not Növ.SENED]
        self.s = mənbə
        self.x = toplayıcı
        self.i = 0
        self.direktivlər = [x.dəyər for x in tokenlər
                            if x.növ is Növ.DIREKTIV]
        # `alqorfmt` üçün: hər tokenin hansı BLOK DƏRİNLİYİNDƏ istehlak
        # olunduğu (mənbə ofseti → dərinlik). Adi ayırmada söndürülüb.
        self.dərinlik = 0
        self.dərinlik_qeydi: dict[int, int] | None = None

    def _sənədləri_topla(self, tokenlər: list[Token]) -> None:
        """
        `///` şərhlərini növbəti elanla, `//!` şərhlərini fayl ilə
        əlaqələndirir.

        Sənəd həm ilk tokenə, həm də `ixrac et`, görünüş sözləri və
        annotasiyalardan (`@sınaq`) sonrakı ELAN AÇAR SÖZÜNƏ bağlanır —
        elan ayrıcıları mövqeni həmin açar sözdən götürür.
        """
        yığım: list[str] = []
        modul: list[str] = []
        for j, tok in enumerate(tokenlər):
            if tok.növ is Növ.SENED:
                if (tok.xam or "").startswith("//!"):
                    modul.append(tok.dəyər)
                else:
                    yığım.append(tok.dəyər)
            elif tok.növ in (Növ.SETIR_SONU, Növ.DIREKTIV):
                continue
            elif yığım:
                mətn = "\n".join(yığım)
                yığım = []
                self.sənədlər[tok.yer.başlanğıc] = mətn
                for k in range(j, min(j + 60, len(tokenlər))):
                    t = tokenlər[k]
                    if t.növ is Növ.ACAR and t.dəyər in ELAN_AÇARLARI:
                        self.sənədlər.setdefault(t.yer.başlanğıc, mətn)
                        break
                    if t.növ is Növ.ACAR and t.dəyər not in \
                            SƏNƏD_MODİFİKATORLARI:
                        break
        if modul:
            self.modul_sənədi = "\n".join(modul).strip("\n")

    # ═══════════════════════════════════════════════════════════════════
    #  Token axını
    # ═══════════════════════════════════════════════════════════════════

    def _bax(self, irəli: int = 0) -> Token:
        j = min(self.i + irəli, len(self.t) - 1)
        return self.t[j]

    def _al(self) -> Token:
        tok = self.t[self.i]
        if (self.dərinlik_qeydi is not None
                and tok.növ is not Növ.SETIR_SONU):
            # Sətir sonu növbəti sətrin ilk tokeni ilə eyni ofsetdədir
            self.dərinlik_qeydi.setdefault(tok.yer.başlanğıc, self.dərinlik)
        if self.i < len(self.t) - 1:
            self.i += 1
        return tok

    def _sonudur(self) -> bool:
        return self._bax().növ is Növ.FAYL_SONU

    def _acar(self, *hansı: str, irəli: int = 0) -> bool:
        return self._bax(irəli).acardır(*hansı)

    def _op(self, *hansı: str, irəli: int = 0) -> bool:
        return self._bax(irəli).opdur(*hansı)

    def _qəbul_acar(self, *hansı: str) -> Token | None:
        if self._acar(*hansı):
            return self._al()
        return None

    def _qəbul_op(self, *hansı: str) -> Token | None:
        if self._op(*hansı):
            return self._al()
        return None

    def _tələb_op(self, op: str, kontekst: str = "") -> Token:
        if self._op(op):
            return self._al()
        self._xəta("ALQ-P001", f"`{op}` gözlənilirdi",
                   f"burada `{op}` olmalıdır",
                   *( [f"kontekst: {kontekst}"] if kontekst else [] ))
        raise ParserXətası()

    def _tələb_acar(self, acar: str, kod: str = "ALQ-P001") -> Token:
        if self._acar(acar):
            return self._al()
        mesaj = {"onda": "`onda` gözlənilirdi",
                 "son": "`son` gözlənilirdi"}.get(acar,
                                                  f"`{acar}` gözlənilirdi")
        kod = {"onda": "ALQ-P004", "son": "ALQ-P002"}.get(acar, kod)
        köməklər = {
            "onda": ["şərtdən sonra `onda` yazılmalıdır: "
                     "`əgər x > 5 onda`"],
            "son": ["blok `son` ilə bitməlidir",
                    "girinti bloku bitirmir — Alqor-da `son` lazımdır"],
        }.get(acar, [])
        self._xəta(kod, mesaj, f"`{acar}` çatışmır", *köməklər)
        raise ParserXətası()

    def _tələb_ad(self, nə: str = "ad") -> str:
        tok = self._bax()
        if tok.növ is Növ.AD:
            return self._al().dəyər
        if tok.növ is Növ.ACAR:
            self._xəta("ALQ-L010",
                       "Açar söz identifikator kimi istifadə edilə bilməz",
                       f"`{tok.dəyər}` açar sözdür",
                       f"başqa {nə} seçin")
            raise ParserXətası()
        self._xəta("ALQ-P001", f"{nə} gözlənilirdi",
                   f"`{self._göstər(tok)}` gözlənilmirdi")
        raise ParserXətası()

    @staticmethod
    def _göstər(tok: Token) -> str:
        if tok.növ is Növ.SETIR_SONU:
            return "sətir sonu"
        if tok.növ is Növ.FAYL_SONU:
            return "fayl sonu"
        return str(tok.dəyər)

    # ── Ayırıcılar ────────────────────────────────────────────────────

    def _ayırıcı_atla(self) -> None:
        """Sətir sonlarını və `;` işarələrini atlayır."""
        while (self._bax().növ is Növ.SETIR_SONU or self._op(";")):
            self._al()

    def _cümlə_sonu(self) -> None:
        """Cümlədən sonra ayırıcı gözləyir."""
        if (self._bax().növ in (Növ.SETIR_SONU, Növ.FAYL_SONU)
                or self._op(";")
                or self._bax().acardır(*BLOK_SONLARI)):
            self._ayırıcı_atla()
            return
        tok = self._bax()
        self._xəta("ALQ-P001", "Gözlənilməyən token",
                   f"`{self._göstər(tok)}` burada gözlənilmirdi",
                   "cümlələr yeni sətirdə və ya `;` ilə ayrılır")
        raise ParserXətası()

    def _son_tələb(self, növ: str | None = None) -> None:
        self._ayırıcı_atla()
        self._tələb_acar("son")
        if növ and self._acar(növ):
            self._al()
        elif self._bax().növ is Növ.ACAR and self._bax().dəyər in SON_NÖVLƏRİ:
            # `son əgər` tipli bağlanış — növ uyğun gəlməsə də qəbul edilir,
            # amma xəbərdarlıq verilir
            yazılan = self._al().dəyər
            if növ and yazılan != növ:
                self.x.xəbərdarlıq(
                    "ALQ-P017", "Blok bağlanışı uyğun deyil",
                    self._bax(-1).yer, f"`son {yazılan}` yazılıb",
                    f"gözlənilən: `son {növ}` və ya sadəcə `son`")

    # ── Xəta ──────────────────────────────────────────────────────────

    def _xəta(self, kod: str, mesaj: str, qeyd: str = "",
              *köməklər: str) -> None:
        tok = self._bax()
        yer = tok.yer
        if tok.növ in (Növ.SETIR_SONU, Növ.FAYL_SONU) and self.i > 0:
            əvvəl = self.t[self.i - 1]
            yer = Yer(self.s, əvvəl.yer.son, 1)
        self.x.xəta(kod, mesaj, yer, qeyd, *köməklər)

    def _bərpa(self) -> None:
        """Növbəti cümlə sərhədinə atla."""
        dərinlik = 0
        while not self._sonudur():
            tok = self._bax()
            if tok.növ is Növ.OP:
                if tok.dəyər in "([{":
                    dərinlik += 1
                elif tok.dəyər in ")]}":
                    if dərinlik == 0:
                        self._al()
                        continue
                    dərinlik -= 1
            if dərinlik == 0:
                if tok.növ is Növ.SETIR_SONU:
                    self._ayırıcı_atla()
                    return
                if tok.acardır(*BLOK_SONLARI):
                    return
            self._al()

    # ═══════════════════════════════════════════════════════════════════
    #  Giriş nöqtəsi
    # ═══════════════════════════════════════════════════════════════════

    def ayır(self) -> A.Proqram:
        başlanğıc = self._bax().yer
        gövdə: list[A.Cümlə] = []
        self._ayırıcı_atla()

        while not self._sonudur():
            if self.x.dolubmu():
                break
            try:
                c = self._üst_səviyyə()
                if c is not None:
                    gövdə.append(c)
            except ParserXətası:
                self._bərpa()
            self._ayırıcı_atla()

        return A.Proqram(başlanğıc, gövdə,
                         modul_sənədi=self.modul_sənədi,
                         direktivlər=self.direktivlər)

    def _üst_səviyyə(self) -> A.Cümlə | None:
        if self._acar("gətir"):
            return self._idxal()
        if self._acar("ixrac et"):
            return self._ixrac()
        # `başlanğıc` / `bitiş` kontekstlidir: yalnız ardınca yeni sətir
        # gələndə blok açar sözüdür. `dəyişən başlanğıc = 5` adi koddur.
        tok = self._bax()
        if (tok.növ is Növ.AD and tok.dəyər in ("başlanğıc", "bitiş")
                and self._bax(1).növ is Növ.SETIR_SONU):
            yer = self._al().yer
            gövdə = self._blok()
            self._son_tələb()
            return (A.Başlanğıc(yer, gövdə) if tok.dəyər == "başlanğıc"
                    else A.Bitiş(yer, gövdə))
        return self._cümlə()

    # ═══════════════════════════════════════════════════════════════════
    #  Modullar
    # ═══════════════════════════════════════════════════════════════════

    def _idxal(self) -> A.İdxal:
        yer = self._al().yer                     # `gətir`

        mətn_yolu = None
        yol: list[str] = []
        if self._bax().növ is Növ.METN:
            mətn_yolu = self._al().dəyər
        else:
            yol.append(self._tələb_ad("modul adı"))
            while self._op(".") and self._bax(1).növ is Növ.AD:
                self._al()
                yol.append(self._al().dəyər)

        elementlər: list[A.İdxalElementi] = []
        hamısı = False
        ləqəb = None

        # `.{...}` və ya `.*`
        if self._op("."):
            self._al()
            if self._op("*"):
                self._al()
                hamısı = True
            elif self._op("{"):
                self._al()
                while not self._op("}"):
                    self._ayırıcı_atla()
                    ad = self._tələb_ad("ixrac adı")
                    lq = None
                    if self._qəbul_acar("kimi"):
                        lq = self._tələb_ad("ləqəb")
                    elementlər.append(A.İdxalElementi(ad, lq))
                    self._ayırıcı_atla()
                    if not self._qəbul_op(","):
                        break
                    self._ayırıcı_atla()
                self._tələb_op("}", "seçmə idxal")
            else:
                self._xəta("ALQ-P001", "`{` və ya `*` gözlənilirdi",
                           "seçmə idxal: `gətir riyaziyyat.{kök, Pİ}`",
                           "hamısını idxal: `gətir riyaziyyat.*`")
                raise ParserXətası()

        if self._qəbul_acar("kimi"):
            ləqəb = self._tələb_ad("ləqəb")

        self._cümlə_sonu()
        return A.İdxal(yer, yol, mətn_yolu, ləqəb, elementlər, hamısı)

    def _ixrac(self) -> A.Cümlə:
        yer = self._al().yer                     # `ixrac et`

        if self._op("{"):
            self._al()
            elementlər: list[A.İdxalElementi] = []
            while not self._op("}"):
                self._ayırıcı_atla()
                ad = self._tələb_ad()
                lq = None
                if self._qəbul_acar("kimi"):
                    lq = self._tələb_ad("ləqəb")
                elementlər.append(A.İdxalElementi(ad, lq))
                self._ayırıcı_atla()
                if not self._qəbul_op(","):
                    break
                self._ayırıcı_atla()
            self._tələb_op("}")
            self._cümlə_sonu()
            return A.İxracSiyahısı(yer, elementlər)

        standart = bool(self._qəbul_acar("standart"))
        c = self._cümlə()
        if hasattr(c, "ixrac"):
            c.ixrac = True
        else:
            self._xəta("ALQ-P018", "Bu elan ixrac edilə bilməz",
                       "`ixrac et` yalnız elanlardan əvvəl gəlir")
        return c

    # ═══════════════════════════════════════════════════════════════════
    #  Cümlələr
    # ═══════════════════════════════════════════════════════════════════

    def _blok(self, *dayan_acarları: str) -> list[A.Cümlə]:
        """Blokun gövdəsini oxuyur — terminatora qədər."""
        dayanlar = set(dayan_acarları) | BLOK_SONLARI
        gövdə: list[A.Cümlə] = []
        self._ayırıcı_atla()
        self.dərinlik += 1
        try:
            while (not self._sonudur()
                   and not self._bax().acardır(*dayanlar)):
                if self.x.dolubmu():
                    break
                try:
                    c = self._cümlə()
                    if c is not None:
                        gövdə.append(c)
                except ParserXətası:
                    self._bərpa()
                self._ayırıcı_atla()
        finally:
            self.dərinlik -= 1
        return gövdə

    def _cümlə(self) -> A.Cümlə | None:
        tok = self._bax()

        # ── Etiketli dövr: `xarici: hər ...` ────────────────────
        if (tok.növ is Növ.AD and self._op(":", irəli=1)
                and self._bax(2).acardır("hər", "nə qədər ki",
                                         "təkrarla", "həmişə")):
            etiket = self._al().dəyər
            self._al()                                  # `:`
            return self._dövr(etiket)

        # ── Annotasiyalar ───────────────────────────────────────
        annotasiyalar: list[A.Annotasiya] = []
        while self._op("@"):
            annotasiyalar.append(self._annotasiya())
            self._ayırıcı_atla()

        if annotasiyalar:
            c = self._cümlə()
            if hasattr(c, "annotasiyalar"):
                c.annotasiyalar = annotasiyalar
            return c

        # ── Modifikatorlu elanlar ───────────────────────────────
        if self._elan_başlanğıcıdır():
            return self._elan()

        if tok.növ is not Növ.ACAR:
            return self._ifadə_cümləsi()

        acar = tok.dəyər

        if acar == "əgər":
            return self._şərt()
        if acar == "varsa":
            return self._varsa()
        if acar == "yoxdursa":
            return self._yoxdursa()
        if acar == "seç":
            return self._seç()
        if acar in ("hər", "nə qədər ki", "təkrarla", "həmişə"):
            return self._dövr(None)
        if acar == "dayan":
            yer = self._al().yer
            etiket = self._al().dəyər if self._bax().növ is Növ.AD else None
            self._cümlə_sonu()
            return A.Dayan(yer, etiket)
        if acar == "davam et":
            yer = self._al().yer
            etiket = self._al().dəyər if self._bax().növ is Növ.AD else None
            self._cümlə_sonu()
            return A.DavamEt(yer, etiket)
        if acar == "qaytar":
            yer = self._al().yer
            dəyərlər: list[A.İfadə] = []
            if not self._cümlə_bitibmi():
                dəyərlər.append(self._ifadə())
                while self._qəbul_op(","):
                    dəyərlər.append(self._ifadə())
            self._cümlə_sonu()
            return A.Qaytar(yer, dəyərlər)
        if acar == "ver":
            yer = self._al().yer
            dəyər = None if self._cümlə_bitibmi() else self._ifadə()
            self._cümlə_sonu()
            return A.Ver(yer, dəyər)
        if acar == "at":
            yer = self._al().yer
            ifadə = None if self._cümlə_bitibmi() else self._ifadə()
            self._cümlə_sonu()
            return A.At(yer, ifadə)
        if acar == "cəhd et":
            return self._cəhd()
        if acar == "iddia":
            yer = self._al().yer
            şərt = self._ifadə()
            mesaj = self._ifadə() if self._qəbul_op(",") else None
            self._cümlə_sonu()
            return A.İddia(yer, şərt, mesaj)
        if acar == "təmin":
            yer = self._al().yer
            şərt = self._ifadə()
            self._tələb_acar("yoxsa")
            gövdə = self._blok()
            self._son_tələb()
            return A.Təmin(yer, şərt, gövdə)
        if acar == "gecikdir":
            yer = self._al().yer
            ifadə = self._ifadə()
            self._cümlə_sonu()
            return A.Gecikdir(yer, ifadə)
        if acar == "istifadə":
            return self._istifadə()
        if acar == "keç":
            yer = self._al().yer
            self._cümlə_sonu()
            return A.Keç(yer)
        if acar == "dayanNöqtəsi":
            yer = self._al().yer
            self._cümlə_sonu()
            return A.DayanNöqtəsi(yer)
        if acar == "global":
            yer = self._al().yer
            adlar = [self._tələb_ad()]
            while self._qəbul_op(","):
                adlar.append(self._tələb_ad())
            self._cümlə_sonu()
            return A.Global(yer, adlar)
        if acar == "gətir":
            return self._idxal()
        if acar == "ixrac et":
            return self._ixrac()

        return self._ifadə_cümləsi()

    def _cümlə_bitibmi(self) -> bool:
        return (self._bax().növ in (Növ.SETIR_SONU, Növ.FAYL_SONU)
                or self._op(";")
                or self._bax().acardır(*BLOK_SONLARI))

    def _annotasiya(self) -> A.Annotasiya:
        yer = self._al().yer                      # `@`
        ad = self._bax().dəyər
        self._al()
        arqumentlər: list[A.Arqument] = []
        if self._op("("):
            arqumentlər = self._arqumentlər()
        return A.Annotasiya(yer, str(ad), arqumentlər)

    def _ifadə_cümləsi(self) -> A.Cümlə:
        yer = self._bax().yer
        ifadə = self._ifadə()

        # Alternativ dövr forması: `siyahı içində hər x üçün … son`
        if self._acar("içində") and self._acar("hər", irəli=1):
            return self._içində_hər(yer, ifadə)

        # `i++` / `i--`
        if self._op("++", "--"):
            op = self._al().dəyər
            self._cümlə_sonu()
            return A.Artırma(yer, ifadə, op)

        # Mənimsətmə
        if self._op(*MƏNİMSƏTMƏ_OPLARI) or self._op(","):
            hədəflər = [ifadə]
            while self._qəbul_op(","):
                hədəflər.append(self._ifadə())
            if not self._op(*MƏNİMSƏTMƏ_OPLARI):
                if len(hədəflər) > 1:
                    self._xəta("ALQ-P001", "Mənimsətmə gözlənilirdi",
                               "vergüllə ayrılmış hədəflərdən sonra "
                               "`=` olmalıdır")
                    raise ParserXətası()
                self._cümlə_sonu()
                return A.İfadəCümləsi(yer, ifadə)
            op = self._al().dəyər
            dəyərlər = [self._ifadə()]
            while self._qəbul_op(","):
                dəyərlər.append(self._ifadə())
            self._cümlə_sonu()
            return A.İfadəCümləsi(
                yer, A.Mənimsətmə(yer, hədəflər, op, dəyərlər))

        self._cümlə_sonu()
        return A.İfadəCümləsi(yer, ifadə)

    # ── Şərt ──────────────────────────────────────────────────────────

    def _şərt(self) -> A.Şərt:
        yer = self._bax().yer
        budaqlar: list[tuple[A.İfadə, list[A.Cümlə]]] = []

        self._al()                                   # `əgər`
        şərt = self._ifadə()
        self._tələb_acar("onda")
        gövdə = self._blok()
        budaqlar.append((şərt, gövdə))

        yoxsa: list[A.Cümlə] | None = None
        while True:
            if self._acar("yoxsa əgər"):
                self._al()
                ş = self._ifadə()
                self._tələb_acar("onda")
                budaqlar.append((ş, self._blok()))
                continue
            if self._acar("yoxsa"):
                self._al()
                # `yoxsa əgər` lekserdə birləşir, amma yeni sətir varsa
                # `yoxsa` + `əgər` ayrı gəlir — onu da else-if sayırıq
                if self._acar("əgər"):
                    self._al()
                    ş = self._ifadə()
                    self._tələb_acar("onda")
                    budaqlar.append((ş, self._blok()))
                    continue
                yoxsa = self._blok()
            break

        self._son_tələb("əgər")
        return A.Şərt(yer, budaqlar, yoxsa)

    def _varsa_bağlamaları(self):
        bağlamalar: list[tuple[A.Bağlama | None, A.İfadə]] = []
        while True:
            if (self._bax().növ is Növ.AD and self._op("=", irəli=1)):
                ad_tok = self._al()
                self._al()                           # `=`
                b = A.Bağlama(ad_tok.yer, "ad", ad_tok.dəyər)
                bağlamalar.append((b, self._ifadə()))
            else:
                bağlamalar.append((None, self._ifadə()))
            if not self._qəbul_op(","):
                break
        return bağlamalar

    def _varsa(self) -> A.Varsa:
        yer = self._al().yer
        bağlamalar = self._varsa_bağlamaları()
        self._tələb_acar("onda")
        gövdə = self._blok()
        yoxsa = None
        if self._qəbul_acar("yoxsa"):
            yoxsa = self._blok()
        self._son_tələb()
        return A.Varsa(yer, bağlamalar, gövdə, yoxsa)

    def _yoxdursa(self) -> A.Yoxdursa:
        yer = self._al().yer
        bağlamalar = self._varsa_bağlamaları()
        self._tələb_acar("onda")
        gövdə = self._blok()
        self._son_tələb()
        return A.Yoxdursa(yer, bağlamalar, gövdə)

    # ── Seç ───────────────────────────────────────────────────────────

    def _seç(self) -> A.Seç:
        yer = self._al().yer                         # `seç`
        tipə_görə = False
        if self._bax().növ is Növ.AD and self._bax().dəyər == "tipi":
            self._al()
            tipə_görə = True

        ifadə = None
        if not (self._bax().növ is Növ.SETIR_SONU or self._acar("hal")):
            ifadə = self._ifadə()

        self._ayırıcı_atla()
        hallar: list[A.Hal] = []
        digər: list[A.Cümlə] | None = None

        self.dərinlik += 1
        while True:
            self._ayırıcı_atla()
            if self._acar("hal"):
                hallar.append(self._hal(tipə_görə, ifadə is None))
                continue
            if self._acar("digər hallarda"):
                self._al()
                if self._op(*OX_FORMALARI):
                    self._al()
                    c = self._cümlə()
                    digər = [c] if c else []
                else:
                    digər = self._blok("hal", "digər hallarda")
                continue
            break
        self.dərinlik -= 1

        self._son_tələb("seç")
        if not hallar and digər is None:
            self.x.xəbərdarlıq("ALQ-P019", "`seç` boşdur", yer,
                               "heç bir `hal` yoxdur")
        return A.Seç(yer, ifadə, hallar, digər, tipə_görə)

    def _hal(self, tipə_görə: bool, şərtli: bool = False) -> A.Hal:
        yer = self._al().yer                         # `hal`
        oxu = self._şərt_naxışı if şərtli and not tipə_görə else \
            (lambda: self._naxış(tipə_görə))
        naxışlar = [oxu()]
        while self._qəbul_op(","):
            naxışlar.append(oxu())

        mühafizə = None
        if self._qəbul_acar("əgər"):
            mühafizə = self._ifadə()

        if self._op(*OX_FORMALARI):
            self._al()
            c = self._cümlə()
            gövdə = [c] if c else []
        else:
            gövdə = self._blok("hal", "digər hallarda")

        keç = False
        if gövdə and isinstance(gövdə[-1], A.Keç):
            keç = True
            gövdə = gövdə[:-1]

        return A.Hal(yer, naxışlar, gövdə, mühafizə, keç)

    def _şərt_naxışı(self) -> A.Naxış:
        """İfadəsiz `seç`: `hal yaş < 13 → ...` — hal şərtdir."""
        tok = self._bax()
        if tok.opdur("_") or (tok.növ is Növ.AD and tok.dəyər == "_"):
            self._al()
            return A.Naxış(tok.yer, "atma")
        return A.Naxış(tok.yer, "şərt", dəyər=self._ifadə())

    def _naxış(self, tipə_görə: bool) -> A.Naxış:
        tok = self._bax()
        yer = tok.yer

        if tok.opdur("_"):
            self._al()
            return A.Naxış(yer, "atma")

        if tipə_görə:
            return A.Naxış(yer, "tip", tip=self._tip())

        # Literal (və diapazon)
        if tok.literaldır() or tok.acardır("doğru", "yanlış", "boş"):
            ilk = self._əsas_ifadə()
            if self._op("..", "..<"):
                xaric = self._al().dəyər == "..<"
                son = self._əsas_ifadə()
                return A.Naxış(yer, "diapazon", dəyər=ilk,
                               diapazon_son=son, diapazon_xaric=xaric)
            if isinstance(tok, Token) and tok.opdur("-"):
                pass
            return A.Naxış(yer, "literal", dəyər=ilk)

        # Mənfi ədəd
        if tok.opdur("-") and self._bax(1).növ in (Növ.TAM, Növ.ONLUQ):
            ifadə = self._tək_operand()
            return A.Naxış(yer, "literal", dəyər=ifadə)

        # Kortej naxışı
        if tok.opdur("("):
            self._al()
            alt: list[A.Naxış] = []
            while not self._op(")"):
                alt.append(self._naxış(False))
                if not self._qəbul_op(","):
                    break
            self._tələb_op(")", "kortej naxışı")
            return A.Naxış(yer, "kortej", alt=alt)

        # Siyahı naxışı
        if tok.opdur("["):
            self._al()
            alt = []
            qalan = None
            while not self._op("]"):
                if self._op("..."):
                    self._al()
                    qalan = self._tələb_ad("qalan adı")
                    break
                alt.append(self._naxış(False))
                if not self._qəbul_op(","):
                    break
            self._tələb_op("]", "siyahı naxışı")
            return A.Naxış(yer, "siyahı", alt=alt, qalan=qalan)

        # Ad / tip / variant
        if tok.növ is Növ.AD or (tok.növ is Növ.ACAR
                                 and tok.dəyər in TİP_ADLARI):
            yol = [str(self._al().dəyər)]
            while self._op(".") and self._bax(1).növ is Növ.AD:
                self._al()
                yol.append(self._al().dəyər)

            if self._op("("):
                self._al()
                alt = []
                while not self._op(")"):
                    alt.append(self._naxış(False))
                    if not self._qəbul_op(","):
                        break
                self._tələb_op(")")
                return A.Naxış(yer, "obyekt",
                               tip=A.TipAdı(yer, yol), alt=alt)

            if self._op("{"):
                self._al()
                sahələr: list[tuple[str, A.Naxış | None]] = []
                while not self._op("}"):
                    self._ayırıcı_atla()
                    ad = self._tələb_ad("sahə adı")
                    alt_naxış = None
                    if self._qəbul_op(":"):
                        alt_naxış = self._naxış(False)
                    sahələr.append((ad, alt_naxış))
                    self._ayırıcı_atla()
                    if not self._qəbul_op(","):
                        break
                    self._ayırıcı_atla()
                self._tələb_op("}")
                return A.Naxış(yer, "obyekt",
                               tip=A.TipAdı(yer, yol), sahələr=sahələr)

            if len(yol) > 1 or tok.növ is Növ.ACAR:
                return A.Naxış(yer, "tip", tip=A.TipAdı(yer, yol))
            return A.Naxış(yer, "ad", dəyər=yol[0])

        self._xəta("ALQ-P001", "Naxış gözlənilirdi",
                   f"`{self._göstər(tok)}` naxış ola bilməz",
                   "naxışlar: literal, `_`, ad, `(a, b)`, `[ilk, ...qalan]`,"
                   " `Tip{sahə}`, diapazon")
        raise ParserXətası()

    # ── Dövrlər ───────────────────────────────────────────────────────

    def _dövr(self, etiket: str | None) -> A.Cümlə:
        acar = self._bax().dəyər
        if acar == "nə qədər ki":
            yer = self._al().yer
            şərt = self._ifadə()
            gövdə = self._blok()
            self._son_tələb("nə qədər ki")
            return A.NəQədərKi(yer, şərt, gövdə, etiket)

        if acar == "həmişə":
            yer = self._al().yer
            gövdə = self._blok()
            self._son_tələb("həmişə")
            return A.Həmişə(yer, gövdə, etiket)

        if acar == "təkrarla":
            yer = self._al().yer
            # `təkrarla ... nə qədər ki şərt` (do-while)
            if self._bax().növ is Növ.SETIR_SONU:
                gövdə = self._blok("nə qədər ki")
                self._ayırıcı_atla()
                if self._qəbul_acar("nə qədər ki"):
                    şərt = self._ifadə()
                    self._cümlə_sonu()
                    return A.TəkrarlaNəQədər(yer, gövdə, şərt, etiket)
                self._son_tələb("təkrarla")
                return A.Təkrarla(yer, A.Literal(yer, 1, "tam"),
                                  gövdə, None, etiket)
            sayğac = None
            if self._bax().növ is Növ.AD and self._op(",", irəli=1):
                sayğac = self._al().dəyər
                self._al()
            say = self._ifadə()
            self._tələb_acar("dəfə")
            gövdə = self._blok()
            self._son_tələb("təkrarla")
            return A.Təkrarla(yer, say, gövdə, sayğac, etiket)

        # `hər`
        yer = self._al().yer
        bağlamalar = [self._bağlama()]
        while self._qəbul_op(","):
            bağlamalar.append(self._bağlama())
        self._tələb_acar("üçün")
        mənbə = self._ifadə()

        addım = None
        if self._qəbul_acar("addım"):
            addım = self._ifadə()

        self._tələb_acar("içində")
        asinxron = bool(self._qəbul_acar("gözlə"))

        şərt = None
        if self._qəbul_acar("əgər"):
            şərt = self._ifadə()

        gövdə = self._blok("yoxsa")
        yoxsa = None
        if self._qəbul_acar("yoxsa"):
            yoxsa = self._blok()
        self._son_tələb("hər")
        return A.Hər(yer, bağlamalar, mənbə, gövdə, addım, şərt,
                     yoxsa, asinxron, etiket)

    def _içində_hər(self, yer, mənbə) -> A.Hər:
        """`mənbə içində hər x üçün [əgər şərt] … [yoxsa …] son` (§ 4.4)."""
        self._tələb_acar("içində")
        self._al()                                   # `hər`
        bağlamalar = [self._bağlama()]
        while self._qəbul_op(","):
            bağlamalar.append(self._bağlama())
        üçün = self._bax()
        self._tələb_acar("üçün")
        şərt = None
        # Filtr yalnız EYNİ sətirdə: növbəti sətirdəki `əgər` gövdədir
        if self._acar("əgər") and self._bax().yer.sətir == üçün.yer.sətir:
            self._al()
            şərt = self._ifadə()
        gövdə = self._blok("yoxsa")
        yoxsa = None
        if self._qəbul_acar("yoxsa"):
            yoxsa = self._blok()
        self._son_tələb("hər")
        return A.Hər(yer, bağlamalar, mənbə, gövdə, None, şərt, yoxsa,
                     False, None)

    # ── Cəhd / istifadə ───────────────────────────────────────────────

    def _cəhd(self) -> A.Cəhd:
        yer = self._al().yer                         # `cəhd et`
        gövdə = self._blok("tut", "nəhayət")
        tutmalar: list[A.Tutma] = []

        while self._acar("tut"):
            t_yer = self._al().yer
            ad = None
            tiplər: list[A.TipQovşağı] = []
            if self._op("("):
                self._al()
                ad = self._tələb_ad("xəta dəyişəni")
                if self._qəbul_op(":"):
                    tiplər.append(self._tip())
                    while self._qəbul_op("|"):
                        tiplər.append(self._tip())
                self._tələb_op(")", "`tut` bəndi")
            elif (self._bax().növ is Növ.AD
                  and (self._bax(1).növ in (Növ.SETIR_SONU, Növ.FAYL_SONU)
                       or self._acar("əgər", irəli=1))):
                # `tut x` — istənilən xətanı `x`-ə bağlayır. Əvvəllər `x`
                # səssizcə gövdənin ilk cümləsi sayılırdı.
                ad = self._al().dəyər
            mühafizə = None
            if self._qəbul_acar("əgər"):
                mühafizə = self._ifadə()
            t_gövdə = self._blok("tut", "nəhayət")
            tutmalar.append(A.Tutma(t_yer, t_gövdə, ad, tiplər, mühafizə))

        nəhayət = None
        if self._qəbul_acar("nəhayət"):
            nəhayət = self._blok()

        self._son_tələb("cəhd")
        if not tutmalar and nəhayət is None:
            self.x.xəbərdarlıq(
                "ALQ-P020", "`cəhd et` bloku xətanı tutmur", yer,
                "`tut` və ya `nəhayət` yoxdur",
                "ən azı bir `tut` bəndi əlavə edin")
        return A.Cəhd(yer, gövdə, tutmalar, nəhayət)

    def _istifadə(self) -> A.İstifadə:
        yer = self._al().yer
        bağlamalar: list[tuple[str, A.İfadə]] = []
        while True:
            ad = self._tələb_ad("resurs adı")
            self._tələb_op("=", "`istifadə` bloku")
            bağlamalar.append((ad, self._ifadə()))
            if not self._qəbul_op(","):
                break
        gövdə = self._blok()
        self._son_tələb("istifadə")
        return A.İstifadə(yer, bağlamalar, gövdə)

    # ═══════════════════════════════════════════════════════════════════
    #  Elanlar
    # ═══════════════════════════════════════════════════════════════════

    def _elan_başlanğıcıdır(self) -> bool:
        tok = self._bax()
        if tok.növ is not Növ.ACAR:
            return False
        a = tok.dəyər
        if a in ("dəyişən", "sabit", "dəyişməz", "funksiya", "sinif",
                 "struktur", "interfeys", "sadalama", "modul", "obyekt",
                 "qarışıq", "qurucu", "silinsin", "metod",
                 "xassə", "genişlət", "komponent", "mağaza",
                 "asinxron", "generator", "mücərrəd", "tənbəl",
                 "əvəz et", "statik"):
            return True
        if a == "tip":
            # `tip Ad = ...` elandır; `tip(x)` standart funksiyadır.
            # Bu, `tip` sözünün hər iki rolda işləməsinə imkan verir.
            return self._bax(1).növ is Növ.AD and self._op("=", irəli=2)
        if a in GÖRÜNÜŞLƏR:
            return True
        if a == "son":
            # `son sinif` / `son metod` — modifikator
            return self._bax(1).acardır("sinif", "metod", "funksiya")
        return False

    def _modifikatorlar(self) -> dict:
        m = {
            "görünüş": None, "statik": False, "mücərrəd": False,
            "son": False, "tənbəl": False, "əvəz": False,
            "asinxron": False, "generator": False, "sabit": False,
        }
        while True:
            tok = self._bax()
            if tok.növ is not Növ.ACAR:
                break
            a = tok.dəyər
            if a in GÖRÜNÜŞLƏR:
                m["görünüş"] = a
            elif a == "statik":
                m["statik"] = True
            elif a == "mücərrəd":
                m["mücərrəd"] = True
            elif a == "tənbəl":
                m["tənbəl"] = True
            elif a == "əvəz et":
                m["əvəz"] = True
            elif a == "asinxron":
                m["asinxron"] = True
            elif a == "generator":
                m["generator"] = True
            elif a == "son" and self._bax(1).acardır("sinif", "metod",
                                                      "funksiya"):
                m["son"] = True
            elif a == "sabit" and self._bax(1).acardır("xassə"):
                m["sabit"] = True
            else:
                break
            self._al()
        return m

    def _sənəd(self, yer: Yer) -> str | None:
        return self.sənədlər.get(yer.başlanğıc)

    def _elan(self) -> A.Cümlə:
        m = self._modifikatorlar()
        tok = self._bax()
        if tok.növ is not Növ.ACAR:
            self._xəta("ALQ-P001", "Elan gözlənilirdi",
                       "modifikatorlardan sonra elan olmalıdır")
            raise ParserXətası()

        a = tok.dəyər
        if a in ("dəyişən", "sabit", "dəyişməz"):
            return self._dəyişən_elanı(m)
        if a == "funksiya":
            return self._funksiya_elanı(m)
        if a == "metod":
            return self._metod_elanı(m)
        if a == "xassə":
            return self._xassə_elanı(m)
        if a == "qurucu":
            return self._qurucu_elanı(m)
        if a == "silinsin":
            yer = self._al().yer
            self._tələb_op("(")
            self._tələb_op(")")
            gövdə = self._blok()
            self._son_tələb()
            return A.DağıdıcıElanı(yer, gövdə)
        if a in ("sinif", "struktur", "obyekt", "komponent", "mağaza"):
            return self._sinif_elanı(m, a)
        if a == "interfeys":
            return self._interfeys_elanı(m)
        if a == "sadalama":
            return self._sadalama_elanı(m)
        if a == "qarışıq":
            yer = self._al().yer
            ad = self._tələb_ad("qarışıq adı")
            üzvlər = self._sinif_gövdəsi()
            self._son_tələb("qarışıq")
            return A.QarışıqElanı(yer, ad, üzvlər, m["görünüş"])
        if a == "genişlət":
            yer = self._al().yer
            tip = self._tip()
            üzvlər = self._sinif_gövdəsi()
            self._son_tələb("genişlət")
            return A.Genişlətmə(yer, tip, üzvlər)
        if a == "tip":
            yer = self._al().yer
            ad = self._tələb_ad("tip adı")
            generiklər = self._generiklər()
            self._tələb_op("=", "tip aliası")
            tip = self._tip()
            self._cümlə_sonu()
            return A.TipAliası(yer, ad, tip, generiklər, m["görünüş"])
        if a == "modul":
            yer = self._al().yer
            ad = self._tələb_ad("modul adı")
            gövdə = self._blok()
            self._son_tələb("modul")
            return A.ModulElanı(yer, ad, gövdə, m["görünüş"])

        self._xəta("ALQ-P001", "Elan gözlənilirdi",
                   f"`{a}` elan başlada bilməz")
        raise ParserXətası()

    def _dəyişən_elanı(self, m: dict) -> A.DəyişənElanı:
        tok = self._al()
        növ = tok.dəyər
        bağlamalar: list[A.Bağlama] = []
        dəyərlər: list[A.İfadə] = []

        ilk = self._bağlama()
        if self._qəbul_op(":"):
            ilk.tip = self._tip()

        # ── Fərdi forma: `dəyişən a = 0, b = 1` ─────────────────
        #  Hər adın öz dəyəri var. Ortaq formadan (`a, b = 1, 2`)
        #  ilk `=` işarəsinin yerinə görə ayrılır.
        if self._op("="):
            self._al()
            bağlamalar.append(ilk)
            dəyərlər.append(self._ifadə())
            while self._qəbul_op(","):
                b = self._bağlama()
                if self._qəbul_op(":"):
                    b.tip = self._tip()
                self._tələb_op("=", "çoxlu dəyişən elanı")
                bağlamalar.append(b)
                dəyərlər.append(self._ifadə())
            self._cümlə_sonu()
            return A.DəyişənElanı(tok.yer, növ, bağlamalar, dəyərlər,
                                  m["görünüş"])

        # ── Ortaq forma: `dəyişən a, b = 1, 2` / `a, b = kortej` ─
        bağlamalar.append(ilk)
        while self._qəbul_op(","):
            bağlamalar.append(self._bağlama())

        if self._qəbul_op(":"):
            tip = self._tip()
            for b in bağlamalar:
                if b.tip is None:
                    b.tip = tip

        if self._qəbul_op("="):
            dəyərlər.append(self._ifadə())
            while self._qəbul_op(","):
                dəyərlər.append(self._ifadə())

        if növ in ("sabit", "dəyişməz") and not dəyərlər:
            self._xəta("ALQ-P021",
                       f"`{növ}` mütləq ilkinləşdirilməlidir",
                       "dəyər verilməyib",
                       f"nümunə: {növ} A = 5")

        self._cümlə_sonu()
        return A.DəyişənElanı(tok.yer, növ, bağlamalar, dəyərlər,
                              m["görünüş"])

    def _bağlama(self) -> A.Bağlama:
        tok = self._bax()
        yer = tok.yer

        if tok.opdur("_"):
            self._al()
            return A.Bağlama(yer, "atma")

        if tok.opdur("..."):
            self._al()
            ad = self._tələb_ad()
            return A.Bağlama(yer, "qalan", ad)

        if tok.opdur("("):
            self._al()
            alt = []
            while not self._op(")"):
                alt.append(self._bağlama())
                if not self._qəbul_op(","):
                    break
            self._tələb_op(")", "dağıtma")
            return A.Bağlama(yer, "kortej", alt=alt)

        if tok.opdur("{"):
            self._al()
            sahələr: list[tuple[str, A.Bağlama | None]] = []
            while not self._op("}"):
                self._ayırıcı_atla()
                ad = self._tələb_ad("sahə adı")
                alt_b = None
                if self._qəbul_op(":"):
                    alt_b = self._bağlama()
                sahələr.append((ad, alt_b))
                self._ayırıcı_atla()
                if not self._qəbul_op(","):
                    break
                self._ayırıcı_atla()
            self._tələb_op("}", "obyekt dağıtması")
            return A.Bağlama(yer, "obyekt", sahələr=sahələr)

        ad = self._tələb_ad("dəyişən adı")
        b = A.Bağlama(yer, "ad", ad)
        # Fərdi tip: `dəyişən a: tam, b: mətn`
        if self._op(":") and not self._op(":", irəli=1):
            # `:`-dan sonra tip gəlirsə — amma ortaq tip halını
            # _dəyişən_elanı idarə edir, ona görə burada yalnız
            # vergüldən əvvəl gələn fərdi tipi tuturuq
            pass
        return b

    def _generiklər(self) -> list[tuple[str, A.TipQovşağı | None]]:
        if not self._op("["):
            return []
        # Generik parametrlər: `[T]`, `[T: Müqayisəedilən, U]`
        self._al()
        nəticə: list[tuple[str, A.TipQovşağı | None]] = []
        while not self._op("]"):
            ad = self._tələb_ad("generik parametr")
            məhdudiyyət = None
            if self._qəbul_op(":"):
                məhdudiyyət = self._tip()
                while self._qəbul_acar("və"):
                    self._tip()          # əlavə məhdudiyyətlər
            nəticə.append((ad, məhdudiyyət))
            if not self._qəbul_op(","):
                break
        self._tələb_op("]", "generik parametrlər")
        return nəticə

    def _parametrlər(self) -> list[A.Parametr]:
        self._tələb_op("(", "parametr siyahısı")
        nəticə: list[A.Parametr] = []
        yalnız_adlı = False
        self._ayırıcı_atla()

        while not self._op(")"):
            self._ayırıcı_atla()
            if self._op("*") and (self._op(",", irəli=1)
                                  or self._op(")", irəli=1)):
                self._al()
                yalnız_adlı = True
                if not self._qəbul_op(","):
                    break
                continue

            yer = self._bax().yer
            variadic = adlı_variadic = False
            if self._qəbul_op("..."):
                variadic = True
            elif self._qəbul_op("**"):
                adlı_variadic = True

            xassə_görünüşü = None
            if self._bax().növ is Növ.ACAR and self._bax().dəyər in GÖRÜNÜŞLƏR \
                    and self._bax(1).acardır("xassə"):
                xassə_görünüşü = self._al().dəyər
                self._al()
            elif self._acar("xassə"):
                xassə_görünüşü = "açıq"
                self._al()

            ad = self._tələb_ad("parametr adı")
            tip = self._tip() if self._qəbul_op(":") else None
            standart = self._ifadə() if self._qəbul_op("=") else None

            nəticə.append(A.Parametr(yer, ad, tip, standart, variadic,
                                     adlı_variadic, yalnız_adlı,
                                     xassə_görünüşü))
            self._ayırıcı_atla()
            if not self._qəbul_op(","):
                break
            self._ayırıcı_atla()

        self._tələb_op(")", "parametr siyahısı")

        # Yoxlama: standart dəyərli parametr standartsızdan əvvəl gəlməz
        standart_görüldü = False
        for p in nəticə:
            if p.variadic or p.adlı_variadic or p.yalnız_adlı:
                continue
            if p.standart is not None:
                standart_görüldü = True
            elif standart_görüldü:
                self.x.xəta(
                    "ALQ-P020",
                    "Standart dəyərli parametr standartsızdan əvvəl "
                    "gələ bilməz", p.yer,
                    f"`{p.ad}` parametrinin standart dəyəri yoxdur",
                    "standart dəyərli parametrləri sona keçirin")
        for p in nəticə[:-1]:
            if p.variadic:
                self.x.xəta("ALQ-P021",
                            "Variadic parametr sonuncu olmalıdır",
                            p.yer, f"`...{p.ad}` ortadadır")
        return nəticə

    def _funksiya_elanı(self, m: dict) -> A.FunksiyaElanı:
        yer = self._al().yer                         # `funksiya`
        ad = self._tələb_ad("funksiya adı")
        generiklər = self._generiklər()
        parametrlər = self._parametrlər()
        qaytarma = self._tip() if self._qəbul_op("->") else None
        gövdə = self._blok()
        self._son_tələb("funksiya")
        return A.FunksiyaElanı(
            yer, ad, parametrlər, gövdə, qaytarma,
            m["asinxron"], m["generator"], generiklər, [],
            m["görünüş"], False, self._sənəd(yer))

    def _metod_elanı(self, m: dict) -> A.MetodElanı:
        yer = self._al().yer                         # `metod`
        ad = self._tələb_ad("metod adı")
        generiklər = self._generiklər()
        parametrlər = self._parametrlər()
        qaytarma = self._tip() if self._qəbul_op("->") else None

        if m["mücərrəd"]:
            self._cümlə_sonu()
            return A.MetodElanı(yer, ad, parametrlər, None, qaytarma,
                                m["görünüş"], m["statik"], True,
                                m["son"], m["əvəz"], m["asinxron"],
                                m["generator"], generiklər, [],
                                self._sənəd(yer))

        gövdə = self._blok()
        self._son_tələb("metod")
        return A.MetodElanı(yer, ad, parametrlər, gövdə, qaytarma,
                            m["görünüş"], m["statik"], False, m["son"],
                            m["əvəz"], m["asinxron"], m["generator"],
                            generiklər, [], self._sənəd(yer))

    def _xassə_elanı(self, m: dict) -> A.XassəElanı:
        yer = self._al().yer                         # `xassə`
        ad = self._tələb_ad("xassə adı")
        tip = self._tip() if self._qəbul_op(":") else None
        standart = self._ifadə() if self._qəbul_op("=") else None

        oxu_gövdəsi = yaz_gövdəsi = None
        yaz_parametri = None

        # Aksessorlar — `oxu` / `yaz` kontekstli sözlərdir
        if self._bax().növ is Növ.SETIR_SONU:
            baxış = 1
            while self._bax(baxış).növ is Növ.SETIR_SONU:
                baxış += 1
            nd = self._bax(baxış)
            if nd.növ is Növ.AD and nd.dəyər in ("oxu", "yaz"):
                self._ayırıcı_atla()
                while self._bax().növ is Növ.AD and \
                        self._bax().dəyər in ("oxu", "yaz"):
                    hansı = self._al().dəyər
                    if hansı == "yaz" and self._op("("):
                        self._al()
                        yaz_parametri = self._tələb_ad("parametr")
                        self._tələb_op(")")
                    g = self._blok()
                    self._son_tələb()
                    if hansı == "oxu":
                        oxu_gövdəsi = g
                    else:
                        yaz_gövdəsi = g
                    self._ayırıcı_atla()
                self._son_tələb("xassə")
                return A.XassəElanı(
                    yer, ad, tip, standart, m["görünüş"], m["statik"],
                    m["sabit"], m["tənbəl"], oxu_gövdəsi, yaz_gövdəsi,
                    yaz_parametri, [], self._sənəd(yer))

        # Tənbəl xassə: `tənbəl xassə x: T  <gövdə>  son`
        if m["tənbəl"] and standart is None:
            g = self._blok()
            self._son_tələb("xassə")
            return A.XassəElanı(yer, ad, tip, None, m["görünüş"],
                                m["statik"], m["sabit"], True, g,
                                None, None, [], self._sənəd(yer))

        self._cümlə_sonu()
        return A.XassəElanı(yer, ad, tip, standart, m["görünüş"],
                            m["statik"], m["sabit"], m["tənbəl"],
                            None, None, None, [], self._sənəd(yer))

    def _qurucu_elanı(self, m: dict) -> A.QurucuElanı:
        yer = self._al().yer                         # `qurucu`
        ad = None
        if self._bax().növ is Növ.AD:
            ad = self._al().dəyər
        parametrlər = self._parametrlər()

        # İki forma var:
        #   qurucu(açıq xassə ad: mətn)         ← QISA: gövdə və `son` yoxdur
        #   qurucu(ad: mətn)  <gövdə>  son      ← TAM
        #
        # Ayırd etmə qaydası: qısa forma `xassə` parametri olan və gövdəsi
        # boş olan formadır. Bu qayda olmadan boş gövdəli qurucu sinfin
        # `son`-unu udurdu.
        qısa_ola_bilər = any(p.xassə_görünüşü for p in parametrlər)

        # Qısa formadan sonra başqa üzv gələndə (komponentdə `göstər()`,
        # `vəziyyət`…) yalnız açar sözə baxmaq kifayət etmir: `göstər()`
        # gövdədəki çağırış da ola bilər, `son` isə həm qurucunu, həm də
        # sinfi bağlaya bilər. Burada GİRİNTİ həll edir — insanın gözü
        # ilə gördüyü kimi (spesifikasiya § 6.3.1):
        #
        #   qurucu(xassə a: tam)      növbəti sətir qurucudan DƏRİN
        #       yaz(a)                deyilsə, gövdə yoxdur;
        #   son                       qurucu ilə EYNİ sütundakı `son`
        #                             qurucunundur, soldakı sinfin.
        if qısa_ola_bilər and self._bax().növ is Növ.SETIR_SONU:
            j = self.i
            while self.t[j].növ is Növ.SETIR_SONU or \
                    self.t[j].opdur(";"):
                j += 1
            növbəti = self.t[j]
            if növbəti.növ is Növ.FAYL_SONU or \
                    növbəti.yer.sütun <= yer.sütun:
                if növbəti.acardır("son") and \
                        növbəti.yer.sütun == yer.sütun:
                    self._ayırıcı_atla()
                    self._son_tələb("qurucu")
                return A.QurucuElanı(yer, parametrlər, [], ad,
                                     m["görünüş"])

        gövdə = self._blok(*SINIF_UZV_ACARLARI)

        if gövdə:
            # Gövdə var — `son` mütləqdir
            if not self._acar("son"):
                self._xəta("ALQ-P002", "`son` gözlənilirdi",
                           "qurucunun gövdəsi bağlanmayıb",
                           "gövdəsi olan qurucu `son` ilə bitməlidir")
                raise ParserXətası()
            self._son_tələb("qurucu")
        elif qısa_ola_bilər:
            # Qısa forma — `son` sinfə məxsusdur, toxunmuruq
            pass
        elif self._acar("son"):
            self._son_tələb("qurucu")

        return A.QurucuElanı(yer, parametrlər, gövdə, ad, m["görünüş"])

    def _sinif_gövdəsi(self) -> list[A.Cümlə]:
        self.dərinlik += 1
        try:
            return self._sinif_üzvləri()
        finally:
            self.dərinlik -= 1

    def _sinif_üzvləri(self) -> list[A.Cümlə]:
        üzvlər: list[A.Cümlə] = []
        self._ayırıcı_atla()
        while not self._sonudur() and not self._acar("son"):
            if self.x.dolubmu():
                break
            try:
                if self._op("@"):
                    annotasiyalar = []
                    while self._op("@"):
                        annotasiyalar.append(self._annotasiya())
                        self._ayırıcı_atla()
                    ü = self._elan()
                    if hasattr(ü, "annotasiyalar"):
                        ü.annotasiyalar = annotasiyalar
                    üzvlər.append(ü)
                elif self._elan_başlanğıcıdır():
                    üzvlər.append(self._elan())
                else:
                    # Komponent kontekstli sözləri: vəziyyət/hesablanan/...
                    ü = self._komponent_üzvü()
                    if ü is not None:
                        üzvlər.append(ü)
                    else:
                        tok = self._bax()
                        self._xəta("ALQ-P022", "Sinif üzvü gözlənilirdi",
                                   f"`{self._göstər(tok)}` burada ola bilməz",
                                   "icazəli üzvlər: xassə, metod, qurucu, "
                                   "silinsin, statik üzvlər")
                        raise ParserXətası()
            except ParserXətası:
                self._bərpa()
            self._ayırıcı_atla()
        return üzvlər

    def _komponent_üzvü(self) -> A.Cümlə | None:
        """`vəziyyət`, `hesablanan`, `əməl`, `hadisə`, `göstər`."""
        tok = self._bax()
        if tok.növ is not Növ.AD:
            return None
        a = tok.dəyər

        if a == "vəziyyət":
            yer = self._al().yer
            ad = self._tələb_ad("vəziyyət adı")
            tip = self._tip() if self._qəbul_op(":") else None
            standart = self._ifadə() if self._qəbul_op("=") else None
            self._cümlə_sonu()
            x = A.XassəElanı(yer, ad, tip, standart)
            x.annotasiyalar = [A.Annotasiya(yer, "vəziyyət")]
            return x

        if a == "hadisə":
            yer = self._al().yer
            ad = self._tələb_ad("hadisə adı")
            self._cümlə_sonu()
            x = A.XassəElanı(yer, ad, None, None)
            x.annotasiyalar = [A.Annotasiya(yer, "hadisə")]
            return x

        if a == "hesablanan":
            yer = self._al().yer
            ad = self._tələb_ad("hesablanan xassə adı")
            tip = self._tip() if self._qəbul_op(":") else None
            gövdə = self._blok()
            self._son_tələb()
            return A.XassəElanı(yer, ad, tip, None, None, False, False,
                                False, gövdə)

        if a in ("əməl", "göstər"):
            yer = self._al().yer
            if a == "göstər":
                ad = "göstər"
                if self._op("("):
                    self._al()
                    self._tələb_op(")")
                parametrlər: list[A.Parametr] = []
            else:
                ad = self._tələb_ad("əməl adı")
                parametrlər = self._parametrlər()
            qaytarma = self._tip() if self._qəbul_op("->") else None
            gövdə = self._blok()
            self._son_tələb()
            return A.MetodElanı(yer, ad, parametrlər, gövdə, qaytarma)

        return None

    def _sinif_elanı(self, m: dict, quruluş: str) -> A.SinifElanı:
        yer = self._al().yer
        ad = self._tələb_ad(f"{quruluş} adı")
        generiklər = self._generiklər()

        baza = None
        interfeyslər: list[A.TipQovşağı] = []
        qarışıqlar: list[A.TipQovşağı] = []

        if self._qəbul_acar("miras"):
            baza = self._tip()
            if quruluş == "struktur":
                self.x.xəta("ALQ-T060", "`struktur` miras ala bilməz",
                            yer, "strukturlar dəyər tipidir",
                            "miras üçün `sinif` istifadə edin")
        if self._qəbul_acar("tətbiq"):
            interfeyslər.append(self._tip())
            while self._qəbul_op(","):
                interfeyslər.append(self._tip())
        if self._qəbul_acar("ilə"):
            qarışıqlar.append(self._tip())
            while self._qəbul_op(","):
                qarışıqlar.append(self._tip())

        üzvlər = self._sinif_gövdəsi()
        son_növ = quruluş if quruluş in SON_NÖVLƏRİ else "sinif"
        self._son_tələb(son_növ)

        return A.SinifElanı(yer, ad, üzvlər, baza, interfeyslər,
                            qarışıqlar, generiklər, m["mücərrəd"],
                            m["son"], m["görünüş"], False, [],
                            self._sənəd(yer), quruluş)

    def _interfeys_elanı(self, m: dict) -> A.InterfeysElanı:
        yer = self._al().yer
        ad = self._tələb_ad("interfeys adı")
        generiklər = self._generiklər()
        bazalar: list[A.TipQovşağı] = []
        if self._qəbul_acar("miras"):
            bazalar.append(self._tip())
            while self._qəbul_op(","):
                bazalar.append(self._tip())

        üzvlər: list[A.Cümlə] = []
        self._ayırıcı_atla()
        self.dərinlik += 1
        while not self._sonudur() and not self._acar("son"):
            try:
                if self._acar("metod"):
                    m_yer = self._al().yer
                    m_ad = self._tələb_ad("metod adı")
                    gen = self._generiklər()
                    p = self._parametrlər()
                    q = self._tip() if self._qəbul_op("->") else None
                    if self._bax().növ is Növ.SETIR_SONU:
                        self._cümlə_sonu()
                        üzvlər.append(A.MetodElanı(m_yer, m_ad, p, None, q,
                                                   mücərrəd=True,
                                                   generiklər=gen))
                    else:
                        g = self._blok()
                        self._son_tələb("metod")
                        üzvlər.append(A.MetodElanı(m_yer, m_ad, p, g, q,
                                                   generiklər=gen))
                elif self._acar("xassə"):
                    üzvlər.append(self._xassə_elanı(self._modifikatorlar()))
                else:
                    self._xəta("ALQ-P022",
                               "İnterfeys üzvü gözlənilirdi",
                               "yalnız `metod` və `xassə` ola bilər")
                    raise ParserXətası()
            except ParserXətası:
                self._bərpa()
            self._ayırıcı_atla()

        self.dərinlik -= 1
        self._son_tələb("interfeys")
        return A.InterfeysElanı(yer, ad, üzvlər, bazalar, generiklər,
                                m["görünüş"], False, self._sənəd(yer))

    def _sadalama_elanı(self, m: dict) -> A.SadalamaElanı:
        yer = self._al().yer
        ad = self._tələb_ad("sadalama adı")
        generiklər = self._generiklər()
        əsas_tip = self._tip() if self._qəbul_op(":") else None

        variantlar: list[A.SadalamaVariantı] = []
        üzvlər: list[A.Cümlə] = []
        self._ayırıcı_atla()

        self.dərinlik += 1
        while not self._sonudur() and not self._acar("son"):
            if self._elan_başlanğıcıdır() or self._op("@"):
                # Variantlardan sonrakı üzvlər eyni dərinlikdədir
                self.dərinlik -= 1
                üzvlər = self._sinif_gövdəsi()
                self.dərinlik += 1
                break
            try:
                v_yer = self._bax().yer
                v_ad = self._tələb_ad("variant adı")
                dəyər = None
                arqumentlər: list[A.Arqument] = []
                parametrlər: list[A.Parametr] = []
                if self._qəbul_op("="):
                    dəyər = self._ifadə()
                elif self._op("("):
                    # `Uğur(dəyər: T)` → parametrli variant
                    # `MERKURİ(3.3e23, 2.4e6)` → arqumentli variant
                    if self._variant_parametrlidir():
                        parametrlər = self._parametrlər()
                    else:
                        arqumentlər = self._arqumentlər()
                variantlar.append(A.SadalamaVariantı(
                    v_yer, v_ad, dəyər, arqumentlər, parametrlər))
                self._cümlə_sonu()
            except ParserXətası:
                self._bərpa()
            self._ayırıcı_atla()

        self.dərinlik -= 1
        self._son_tələb("sadalama")
        return A.SadalamaElanı(yer, ad, variantlar, üzvlər, əsas_tip,
                               generiklər, m["görünüş"], False,
                               self._sənəd(yer))

    def _variant_parametrlidir(self) -> bool:
        """`(ad: Tip)` formasını `(dəyər, dəyər)`-dən ayırır."""
        j = self.i + 1
        dərinlik = 0
        while j < len(self.t):
            tok = self.t[j]
            if tok.növ is Növ.OP:
                if tok.dəyər in "([{":
                    dərinlik += 1
                elif tok.dəyər in ")]}":
                    if dərinlik == 0:
                        return False
                    dərinlik -= 1
                elif tok.dəyər == ":" and dərinlik == 0:
                    return True
                elif tok.dəyər == "," and dərinlik == 0:
                    pass
            j += 1
        return False

    # ═══════════════════════════════════════════════════════════════════
    #  Tiplər
    # ═══════════════════════════════════════════════════════════════════

    def _tip(self) -> A.TipQovşağı:
        yer = self._bax().yer
        ilk = self._tip_əsas()
        if not self._op("|"):
            return ilk
        variantlar = [ilk]
        while self._qəbul_op("|"):
            variantlar.append(self._tip_əsas())
        return A.TipBirləşmə(yer, variantlar)

    def _tip_əsas(self) -> A.TipQovşağı:
        tok = self._bax()
        yer = tok.yer

        # `funksiyaTipi` açar söz deyil, tip adıdır (AD tokeni)
        if (tok.acardır("funksiyaTipi") or (
                tok.növ is Növ.AD and tok.dəyər == "funksiyaTipi"
                and self._bax(1).opdur("("))):
            self._al()
            self._tələb_op("(", "funksiya tipi")
            parametrlər: list[A.TipQovşağı] = []
            while not self._op(")"):
                parametrlər.append(self._tip())
                if not self._qəbul_op(","):
                    break
            self._tələb_op(")")
            qaytarma = self._tip() if self._qəbul_op("->") else None
            ixtiyari = bool(self._qəbul_op("?"))
            return A.TipFunksiya(yer, parametrlər, qaytarma, ixtiyari)

        if tok.opdur("("):
            self._al()
            ilk = self._tip()
            if self._op(","):
                elementlər = [ilk]
                while self._qəbul_op(","):
                    if self._op(")"):
                        break
                    elementlər.append(self._tip())
                self._tələb_op(")", "kortej tipi")
                ixtiyari = bool(self._qəbul_op("?"))
                return A.TipKortej(yer, elementlər, ixtiyari)
            self._tələb_op(")")
            if self._qəbul_op("?") and isinstance(ilk, A.TipAdı):
                ilk.ixtiyari = True
            return ilk

        if tok.növ is Növ.AD or (tok.növ is Növ.ACAR
                                 and tok.dəyər in TİP_ADLARI):
            yol = [str(self._al().dəyər)]
            while self._op(".") and self._bax(1).növ is Növ.AD:
                self._al()
                yol.append(self._al().dəyər)

            arqumentlər: list[A.TipQovşağı] = []
            if self._op("["):
                self._al()
                while not self._op("]"):
                    arqumentlər.append(self._tip())
                    if not self._qəbul_op(","):
                        break
                self._tələb_op("]", "generik tip arqumentləri")

            ixtiyari = bool(self._qəbul_op("?"))
            return A.TipAdı(yer, yol, arqumentlər, ixtiyari)

        self._xəta("ALQ-T002", "Naməlum tip",
                   f"`{self._göstər(tok)}` tip adı deyil",
                   "əsas tiplər: tam, onluq, mətn, məntiq, simvol, bayt",
                   "kolleksiyalar: siyahı[T], lüğət[A,D], dəst[T], "
                   "kortej[A,B]")
        raise ParserXətası()

    # ═══════════════════════════════════════════════════════════════════
    #  İfadələr — prioritet dırmaşması
    # ═══════════════════════════════════════════════════════════════════

    def _ifadə(self, min_p: int = 0) -> A.İfadə:
        sol = self._tək_operand()

        while True:
            tok = self._bax()
            op = self._binar_op(tok)
            if op is None:
                break
            p, sağdan = PRIORITET[op]
            if p < min_p:
                break

            yer = tok.yer
            self._al()
            if op == "kimi" and self._op("?"):
                self._al()
                op = "kimi?"

            növbəti_min = p if sağdan else p + 1

            if op in ("kimi", "kimi?"):
                sol = A.Çevirmə(yer, sol, self._tip(), op == "kimi?")
            elif op == "tipidir":
                sol = A.TipYoxlama(yer, sol, self._tip())
            elif op == "içindədir":
                sol = A.Üzvlük(yer, sol, self._ifadə(növbəti_min))
            elif op == "boşdur":
                sol = A.BoşYoxlama(yer, sol, False)
            elif op == "boş deyil":
                sol = A.BoşYoxlama(yer, sol, True)
            elif op in ("..", "..<"):
                son = self._ifadə(növbəti_min)
                addım = None
                if self._qəbul_acar("addım"):
                    addım = self._ifadə(növbəti_min)
                sol = A.Diapazon(yer, sol, son, addım, op == "..<")
            elif op == "|>":
                sol = A.Boru(yer, sol, self._ifadə(növbəti_min))
            else:
                sol = A.İkili(yer, sol, op, self._ifadə(növbəti_min))

        return sol

    def _binar_op(self, tok: Token) -> str | None:
        if tok.növ is Növ.OP and tok.dəyər in PRIORITET:
            return tok.dəyər
        if tok.növ is Növ.ACAR and tok.dəyər in PRIORITET:
            return tok.dəyər
        return None

    def _tək_operand(self) -> A.İfadə:
        tok = self._bax()

        if tok.növ is Növ.OP and tok.dəyər in TƏK_OPERATORLAR:
            yer = self._al().yer
            return A.TəkOperand(yer, tok.dəyər, self._tək_operand())

        if tok.acardır(*TƏK_ACARLAR):
            # § 3.4: `deyil a == b` → `deyil (a == b)` — `deyil` müqayisədən
            # zəif, `və`-dən güclü bağlayır
            yer = self._al().yer
            return A.TəkOperand(yer, "deyil",
                                self._ifadə(PRIORITET["=="][0]))

        if tok.acardır("gözlə"):
            yer = self._al().yer
            return A.Gözlə(yer, self._tək_operand())

        if tok.acardır("yeni"):
            # `yeni X(...).üzv()` işləsin — postfiks zənciri davam edir
            return self._postfiks_davam(self._yeni())

        return self._qüvvət()

    def _qüvvət(self) -> A.İfadə:
        sol = self._postfiks()
        if self._op("**"):
            yer = self._al().yer
            return A.İkili(yer, sol, "**", self._tək_operand())
        return sol

    def _yeni(self) -> A.İfadə:
        yer = self._al().yer                         # `yeni`
        tip = self._tip_əsas()
        qurucu = None
        if self._op(".") and self._bax(1).növ is Növ.AD:
            self._al()
            qurucu = self._al().dəyər
        arqumentlər = self._arqumentlər() if self._op("(") else []
        return A.Yeni(yer, tip, qurucu, arqumentlər)

    def _postfiks(self) -> A.İfadə:
        return self._postfiks_davam(self._əsas_ifadə())

    def _postfiks_davam(self, ifadə: A.İfadə) -> A.İfadə:
        while True:
            tok = self._bax()

            if tok.opdur(".", "?."):
                təhlükəsiz = tok.dəyər == "?."
                yer = self._al().yer
                if self._bax().növ is Növ.TAM:
                    ifadə = A.Üzv(yer, ifadə, str(self._al().dəyər),
                                  təhlükəsiz)
                    continue
                nd = self._bax()
                if nd.növ in (Növ.AD, Növ.ACAR):
                    ifadə = A.Üzv(yer, ifadə, str(self._al().dəyər),
                                  təhlükəsiz)
                    continue
                self._xəta("ALQ-P001", "Üzv adı gözlənilirdi",
                           "`.`-dan sonra ad və ya kortej indeksi olmalıdır")
                raise ParserXətası()

            if tok.opdur("("):
                yer = tok.yer
                ifadə = A.Çağırış(yer, ifadə, self._arqumentlər())
                continue

            if tok.opdur("["):
                yer = self._al().yer
                # Dilim: `[..b]`
                if self._op("..", "..<"):
                    xaric = self._al().dəyər == "..<"
                    son = None if self._op("]") else self._ifadə()
                    self._tələb_op("]", "dilim")
                    ifadə = A.Dilim(yer, ifadə, None, son, xaric)
                    continue
                # Diapazon prioriteti 7-dir; 8-dən başlayırıq ki
                # `[1..3]` dilim olaraq tanınsın, Diapazon kimi yox
                indeks = self._ifadə(8)
                if self._op("..", "..<"):
                    xaric = self._al().dəyər == "..<"
                    son = None if self._op("]") else self._ifadə()
                    self._tələb_op("]", "dilim")
                    ifadə = A.Dilim(yer, ifadə, indeks, son, xaric)
                    continue
                self._tələb_op("]", "indeksləmə")
                ifadə = A.İndeks(yer, ifadə, indeks)
                continue

            if tok.opdur("!"):
                yer = self._al().yer
                ifadə = A.MəcburiAçma(yer, ifadə)
                continue

            if tok.opdur("?") and not self._op("?", irəli=1):
                # `nəticə?` — Nəticə yayma operatoru.
                # `a ? b : c` üçlü operatoru dildə yoxdur, ona görə
                # təkmənalıdır.
                yer = self._al().yer
                ifadə = A.Yayma(yer, ifadə)
                continue

            break

        return ifadə

    def _arqumentlər(self) -> list[A.Arqument]:
        self._tələb_op("(", "arqument siyahısı")
        nəticə: list[A.Arqument] = []
        self._ayırıcı_atla()

        while not self._op(")"):
            self._ayırıcı_atla()
            if self._qəbul_op("..."):
                nəticə.append(A.Arqument(self._ifadə(), None, True))
            elif (self._etiket_ola_bilər(self._bax())
                  and self._op(":", irəli=1)):
                ad = self._al().dəyər
                self._al()
                nəticə.append(A.Arqument(self._ifadə(), ad))
            else:
                nəticə.append(A.Arqument(self._ifadə()))
            self._ayırıcı_atla()
            if not self._qəbul_op(","):
                break
            self._ayırıcı_atla()

        self._tələb_op(")", "arqument siyahısı")

        adlı_görüldü = False
        for a in nəticə:
            if a.ad:
                adlı_görüldü = True
            elif adlı_görüldü and not a.yayma:
                self.x.xəta("ALQ-P022",
                            "Mövqeli arqument adlıdan sonra gələ bilməz",
                            a.dəyər.yer, "",
                            "mövqeli arqumentləri əvvələ keçirin")
        return nəticə

    # ═══════════════════════════════════════════════════════════════════
    #  Əsas ifadələr
    # ═══════════════════════════════════════════════════════════════════

    def _əsas_ifadə(self) -> A.İfadə:
        tok = self._bax()
        yer = tok.yer

        # ── Literallar ──────────────────────────────────────────
        if tok.növ is Növ.TAM:
            self._al()
            return A.Literal(yer, tok.dəyər, "tam")
        if tok.növ is Növ.ONLUQ:
            self._al()
            return A.Literal(yer, tok.dəyər, "onluq")
        if tok.növ is Növ.SIMVOL:
            self._al()
            return A.Literal(yer, tok.dəyər, "simvol")
        if tok.növ is Növ.BAYT:
            self._al()
            return A.Literal(yer, tok.dəyər, "bayt")
        if tok.növ is Növ.METN:
            return self._mətn()

        if tok.acardır("doğru"):
            self._al()
            return A.Literal(yer, True, "məntiq")
        if tok.acardır("yanlış"):
            self._al()
            return A.Literal(yer, False, "məntiq")
        if tok.acardır("boş"):
            self._al()
            return A.Literal(yer, None, "boş")
        if tok.acardır("sonsuz"):
            self._al()
            return A.Literal(yer, float("inf"), "onluq")
        if tok.acardır("ƏdədDeyil"):
            self._al()
            return A.Literal(yer, float("nan"), "onluq")

        if tok.acardır("özü"):
            self._al()
            return A.Özü(yer)
        if tok.acardır("üst"):
            self._al()
            return A.Üst(yer)

        # ── Blok şəklində ifadələr ──────────────────────────────
        if tok.acardır("əgər"):
            return self._şərt_ifadəsi()
        if tok.acardır("seç"):
            seç = self._seç()
            return self._seç_ifadəsinə(seç)
        if tok.acardır("blok"):
            self._al()
            gövdə = self._blok()
            self._son_tələb("blok")
            return A.BlokIfadəsi(yer, gövdə)
        if tok.acardır("cəhd et"):
            cəhd = self._cəhd()
            return A.BlokIfadəsi(yer, [cəhd])

        # ── Anonim funksiya ─────────────────────────────────────
        if tok.acardır("funksiya") or tok.acardır("asinxron") \
                or tok.acardır("generator"):
            return self._anonim_funksiya()

        # ── Lambda: `x => ...` ──────────────────────────────────
        if tok.növ is Növ.AD and self._op("=>", irəli=1):
            p_yer = self._bax().yer
            ad = self._al().dəyər
            self._al()                               # `=>`
            return self._lambda_gövdəsi(yer, [A.Parametr(p_yer, ad)])

        # ── Mötərizə / kortej / lambda ──────────────────────────
        if tok.opdur("("):
            return self._mötərizə()

        # ── Siyahı / siyahı qurması ─────────────────────────────
        if tok.opdur("["):
            return self._siyahı()

        # ── Lüğət / dəst / qurma ────────────────────────────────
        if tok.opdur("{"):
            return self._fiqurlu()

        # ── Kontekstli açar sözlər ifadə mövqeyində ad kimi işləyir
        #    (`tip(x)`, `xassə` adlı dəyişən və s.)
        if tok.növ is Növ.ACAR and tok.dəyər in ("tip",):
            self._al()
            return A.Ad(yer, str(tok.dəyər))

        # ── İdentifikator ───────────────────────────────────────
        if tok.növ is Növ.AD:
            self._al()
            return A.Ad(yer, tok.dəyər)

        # ── İnterfeys sintaksisi (JSX) ──────────────────────────
        #  Lekser elementi xam skan edib bir JSX tokeni buraxır.
        if tok.növ is Növ.JSX:
            from .parser_jsx import JSXXətası, jsx_oxu
            try:
                return jsx_oxu(self)
            except JSXXətası:
                raise ParserXətası()

        if tok.növ is Növ.ACAR:
            self._xəta("ALQ-P005", "İfadə gözlənilirdi",
                       f"`{tok.dəyər}` açar sözü ifadə ola bilməz")
            raise ParserXətası()

        self._xəta("ALQ-P005", "İfadə gözlənilirdi",
                   f"`{self._göstər(tok)}` gözlənilmirdi")
        raise ParserXətası()

    def _mətn(self) -> A.İfadə:
        tok = self._al()
        yer = tok.yer
        if tok.sadə_mətndir():
            return A.Literal(yer, tok.dəyər, "mətn")

        from .token import KodParçası, MətnParçası
        parçalar: list[A.MətnHissəsi | A.KodHissəsi] = []
        for p in (tok.parçalar or []):
            if isinstance(p, MətnParçası):
                parçalar.append(A.MətnHissəsi(p.dəyər))
            else:
                alt = Parser(list(p.tokenlər) + [
                    Token(Növ.FAYL_SONU, None, yer)], self.s, self.x)
                əvvəl = len(self.x.siyahı)
                try:
                    ifadə = alt._ifadə()
                    qalan = alt._bax()
                    if qalan.növ is not Növ.FAYL_SONU:
                        alt._xəta("ALQ-P001", "Gözlənilməyən token",
                                  f"`{alt._göstər(qalan)}` burada "
                                  "gözlənilmirdi",
                                  "`{…}` daxilində tək ifadə olmalıdır")
                except ParserXətası:
                    ifadə = A.Literal(yer, "", "mətn")
                # CSS, JSON, regex kimi mətnlərdə `{` interpolyasiya
                # sayılır — ən çox rast gəlinən çaşqınlıq
                for d in self.x.siyahı[əvvəl:]:
                    d.köməklər.append(
                        "adi mətndə `{…}` interpolyasiyadır; fiqurlu "
                        'mötərizə lazımdırsa xam mətn yazın: x"…" '
                        'və ya x"""…"""')
                parçalar.append(A.KodHissəsi(ifadə, p.format))
        return A.ŞablonMətn(yer, parçalar)

    def _şərt_ifadəsi(self) -> A.İfadə:
        yer = self._al().yer                         # `əgər`
        budaqlar: list[tuple[A.İfadə, A.İfadə]] = []
        şərt = self._ifadə()
        self._tələb_acar("onda")
        budaqlar.append((şərt, self._budaq_ifadəsi()))

        yoxsa = None
        while True:
            self._ayırıcı_atla()
            if self._acar("yoxsa əgər"):
                self._al()
                ş = self._ifadə()
                self._tələb_acar("onda")
                budaqlar.append((ş, self._budaq_ifadəsi()))
                continue
            if self._acar("yoxsa"):
                self._al()
                self._ayırıcı_atla()
                if self._acar("əgər"):
                    self._al()
                    ş = self._ifadə()
                    self._tələb_acar("onda")
                    budaqlar.append((ş, self._budaq_ifadəsi()))
                    continue
                yoxsa = self._budaq_ifadəsi()
            break

        self._ayırıcı_atla()
        self._tələb_acar("son")
        if self._acar("əgər"):
            self._al()
        return A.ŞərtIfadəsi(yer, budaqlar, yoxsa)

    def _budaq_ifadəsi(self) -> A.İfadə:
        """
        Şərt ifadəsinin budağı — birsətirli də, çoxsətirli də.

            əgər a onda b yoxsa c son          // birsətirli
            əgər a onda                         // çoxsətirli
                b
            yoxsa
                c
            son

        `əgər` lekserdə blok açdığı üçün çoxsətirli formada gövdədən
        əvvəl SETIR_SONU gəlir; konstruksiya `son` ilə bağlandığından
        onu atlamaq birmənalıdır.
        """
        self._ayırıcı_atla()
        # Budaq gövdədir: `alqorfmt` onu bir pillə içəri girintiləyir
        self.dərinlik += 1
        try:
            return self._ifadə()
        finally:
            self.dərinlik -= 1

    @staticmethod
    def _seç_ifadəsinə(seç: A.Seç) -> A.İfadə:
        """`seç` cümləsini ifadə kontekstində istifadə etmək."""
        return A.BlokIfadəsi(seç.yer, [seç])

    def _anonim_funksiya(self) -> A.İfadə:
        yer = self._bax().yer
        asinxron = bool(self._qəbul_acar("asinxron"))
        generator = bool(self._qəbul_acar("generator"))
        self._tələb_acar("funksiya")
        parametrlər = self._parametrlər()
        qaytarma = self._tip() if self._qəbul_op("->") else None
        gövdə = self._blok()
        self._son_tələb("funksiya")
        return A.Lambda(yer, parametrlər, gövdə, asinxron, generator,
                        [], qaytarma)

    def _lambda_gövdəsi(self, yer: Yer,
                        parametrlər: list[A.Parametr]) -> A.İfadə:
        if self._acar("blok"):
            self._al()
            gövdə = self._blok()
            self._son_tələb("blok")
            return A.Lambda(yer, parametrlər, gövdə)
        b_yer = self._bax().yer
        ifadə = self._ifadə()
        # Tək mənimsətmə gövdə ola bilər — UI idarəedicisinin ən təbii
        # forması: `klik: () => özü.say += 1`. Nəticəsi `heç`-dir.
        # Vergüllü mənimsətmə (`a, b = …`) arqument siyahısı ilə
        # qarışacağı üçün yalnız `blok` formasında yazılır.
        if self._op(*MƏNİMSƏTMƏ_OPLARI):
            op = self._al().dəyər
            dəyər = self._ifadə()
            return A.Lambda(yer, parametrlər, [A.İfadəCümləsi(
                b_yer, A.Mənimsətmə(b_yer, [ifadə], op, [dəyər]))])
        if self._op("++", "--"):
            op = self._al().dəyər
            return A.Lambda(yer, parametrlər,
                            [A.Artırma(b_yer, ifadə, op)])
        return A.Lambda(yer, parametrlər, ifadə)

    @staticmethod
    def _etiket_ola_bilər(tok: Token) -> bool:
        """
        Adlı arqumentin etiketi: ad və ya TƏK SÖZLÜ açar söz.

        `seçim(standart: "a")`, `vidjet.qutu(sinif: "x")` — arqument
        siyahısında `açar_söz :` heç bir ifadənin başlanğıcı ola
        bilmədiyi üçün qeyri-müəyyənlik yoxdur. Çoxsözlü açar sözlər
        (`və ya`, `digər hallarda`) etiket ola bilməz.
        """
        if tok.növ is Növ.AD:
            return True
        return (tok.növ is Növ.ACAR and isinstance(tok.dəyər, str)
                and " " not in tok.dəyər)

    def _lambda_mı(self) -> bool:
        """`(` mövqeyindən: bu lambda parametr siyahısıdırmı?"""
        j = self.i + 1
        dərinlik = 0
        while j < len(self.t):
            tok = self.t[j]
            if tok.növ is Növ.OP:
                if tok.dəyər in "([{":
                    dərinlik += 1
                elif tok.dəyər in ")]}":
                    if dərinlik == 0:
                        # `)` tapıldı — ardınca `=>` varmı?
                        k = j + 1
                        while (k < len(self.t)
                               and self.t[k].növ is Növ.SETIR_SONU):
                            k += 1
                        if k < len(self.t) and self.t[k].opdur("=>"):
                            return True
                        if k < len(self.t) and self.t[k].opdur("->"):
                            return True
                        return False
                    dərinlik -= 1
            elif tok.növ is Növ.FAYL_SONU:
                return False
            j += 1
        return False

    def _mötərizə(self) -> A.İfadə:
        if self._lambda_mı():
            yer = self._bax().yer
            parametrlər = self._parametrlər()
            if self._qəbul_op("->"):
                self._tip()
            self._tələb_op("=>", "ox funksiyası")
            return self._lambda_gövdəsi(yer, parametrlər)

        yer = self._al().yer                         # `(`
        self._ayırıcı_atla()

        if self._op(")"):
            self._al()
            return A.KortejLiteralı(yer, [])

        ilk = self._ifadə()
        self._ayırıcı_atla()

        # Generator qurması: `(x * x üçün x içində 1..10)`
        if self._acar("üçün"):
            return self._qurma_quyruğu(yer, "generator", ilk, None, ")")

        if self._op(","):
            elementlər = [ilk]
            while self._qəbul_op(","):
                self._ayırıcı_atla()
                if self._op(")"):
                    break
                elementlər.append(self._ifadə())
                self._ayırıcı_atla()
            self._tələb_op(")", "kortej")
            return A.KortejLiteralı(yer, elementlər)

        self._tələb_op(")", "mötərizə")
        return ilk

    def _siyahı(self) -> A.İfadə:
        yer = self._al().yer                         # `[`
        self._ayırıcı_atla()

        if self._op("]"):
            self._al()
            return A.SiyahıLiteralı(yer, [], [])

        if self._op("..."):
            elementlər, yaymalar = self._siyahı_elementləri()
            self._tələb_op("]", "siyahı")
            return A.SiyahıLiteralı(yer, elementlər, yaymalar)

        ilk = self._ifadə()
        self._ayırıcı_atla()

        if self._acar("üçün"):
            return self._qurma_quyruğu(yer, "siyahı", ilk, None, "]")

        elementlər = [ilk]
        yaymalar = [False]
        while self._qəbul_op(","):
            self._ayırıcı_atla()
            if self._op("]"):
                break
            if self._qəbul_op("..."):
                yaymalar.append(True)
            else:
                yaymalar.append(False)
            elementlər.append(self._ifadə())
            self._ayırıcı_atla()
        self._tələb_op("]", "siyahı")
        return A.SiyahıLiteralı(yer, elementlər, yaymalar)

    def _siyahı_elementləri(self):
        elementlər: list[A.İfadə] = []
        yaymalar: list[bool] = []
        while not self._op("]"):
            self._ayırıcı_atla()
            yaymalar.append(bool(self._qəbul_op("...")))
            elementlər.append(self._ifadə())
            self._ayırıcı_atla()
            if not self._qəbul_op(","):
                break
            self._ayırıcı_atla()
        return elementlər, yaymalar

    def _fiqurlu(self) -> A.İfadə:
        yer = self._al().yer                         # `{`
        self._ayırıcı_atla()

        if self._op("}"):
            self._al()
            return A.LüğətLiteralı(yer, [], [])

        if self._op("..."):
            açarlar: list[A.İfadə | None] = []
            dəyərlər: list[A.İfadə] = []
            while not self._op("}"):
                self._ayırıcı_atla()
                if self._qəbul_op("..."):
                    açarlar.append(None)
                    dəyərlər.append(self._ifadə())
                else:
                    a = self._ifadə()
                    self._tələb_op(":", "lüğət")
                    açarlar.append(a)
                    dəyərlər.append(self._ifadə())
                self._ayırıcı_atla()
                if not self._qəbul_op(","):
                    break
                self._ayırıcı_atla()
            self._tələb_op("}", "lüğət")
            return A.LüğətLiteralı(yer, açarlar, dəyərlər)

        ilk = self._ifadə()
        self._ayırıcı_atla()

        # Lüğət
        if self._op(":"):
            self._al()
            ilk_dəyər = self._ifadə()
            self._ayırıcı_atla()
            if self._acar("üçün"):
                return self._qurma_quyruğu(yer, "lüğət", ilk,
                                           ilk_dəyər, "}")
            açarlar = [ilk]
            dəyərlər = [ilk_dəyər]
            while self._qəbul_op(","):
                self._ayırıcı_atla()
                if self._op("}"):
                    break
                if self._qəbul_op("..."):
                    açarlar.append(None)
                    dəyərlər.append(self._ifadə())
                else:
                    a = self._ifadə()
                    self._tələb_op(":", "lüğət")
                    açarlar.append(a)
                    dəyərlər.append(self._ifadə())
                self._ayırıcı_atla()
            self._tələb_op("}", "lüğət")
            return A.LüğətLiteralı(yer, açarlar, dəyərlər)

        # Dəst qurması
        if self._acar("üçün"):
            return self._qurma_quyruğu(yer, "dəst", ilk, None, "}")

        # Dəst literalı
        elementlər = [ilk]
        while self._qəbul_op(","):
            self._ayırıcı_atla()
            if self._op("}"):
                break
            elementlər.append(self._ifadə())
            self._ayırıcı_atla()
        self._tələb_op("}", "dəst")
        return A.DəstLiteralı(yer, elementlər)

    def _qurma_quyruğu(self, yer: Yer, növ: str, ifadə: A.İfadə,
                       dəyər_ifadəsi: A.İfadə | None,
                       bağlayan: str) -> A.Qurma:
        self._tələb_acar("üçün")
        bağlama = self._bağlama()
        self._tələb_acar("içində")
        mənbə = self._ifadə()
        şərt = None
        if self._qəbul_acar("əgər"):
            şərt = self._ifadə()
        self._ayırıcı_atla()
        self._tələb_op(bağlayan, "kolleksiya qurması")
        return A.Qurma(yer, növ, ifadə, dəyər_ifadəsi, bağlama,
                       mənbə, şərt)


# ═══════════════════════════════════════════════════════════════════════
#  Rahat funksiyalar
# ═══════════════════════════════════════════════════════════════════════

def ayır(mətn: str, ad: str = "<yaddaş>"):
    """Mətni AAC-yə çevirir — sınaqlar və REPL üçün."""
    from .lekser import Lekser
    from .menbe import Mənbə

    x = XətaToplayıcı()
    s = Mənbə.mətndən(mətn, ad, x)
    tokenlər = Lekser(s, x).leksə()
    ağac = Parser(tokenlər, s, x).ayır()
    return ağac, x


def faylı_ayır(yol):
    from .lekser import Lekser
    from .menbe import Mənbə

    x = XətaToplayıcı()
    s = Mənbə.fayldan(yol, x)
    if s is None:
        return None, x
    tokenlər = Lekser(s, x).leksə()
    ağac = Parser(tokenlər, s, x).ayır()
    return ağac, x
