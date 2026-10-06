"""
Alqor — İnterfeys sintaksisi (JSX) parseri.

Problem: JSX mətn məzmununda istənilən simvol qanunidir —
`<button>−</button>`, `<p>5 < 10</p>`. Lekser kontekstsizdir və bunları
tanınmayan simvol kimi bildirir.

Həll: parser `<` görəndə MƏNBƏ MƏTNİNİ birbaşa oxuyur. Onun `Mənbə`
obyektinə girişi var, ona görə xam skan edə bilir. Daxildəki `{ifadə}`
hissələri üçün həmin ofsetdən yeni `Lekser` qurulur — beləliklə mövqelər
düzgün qalır və xəta mesajları dəqiq yer göstərir.

Lekser rejimlərinə ehtiyac qalmır.
"""

from __future__ import annotations

from . import aac as A
from .elifba import ad_davamı_ola_bilər, ad_başlanğıcı_ola_bilər
from .token import Növ, Token

BOŞLUQ = " \t\n\r"
AD_ƏLAVƏ = "-."

DIRNAQ = chr(34)         # "
APOSTROF = chr(39)       # '
QRAVIS = chr(96)         # `
TERS_KESIK = chr(92)     # \


class JSXXətası(Exception):
    """Daxili — parserin öz bərpa mexanizminə ötürülür."""


# ═══════════════════════════════════════════════════════════════════════
#  Giriş nöqtəsi
# ═══════════════════════════════════════════════════════════════════════

def jsx_oxu(p) -> A.İfadə:
    """
    `Növ.JSX` tokenini AAC-yə çevirir.

    Lekser elementi artıq xam skan edib `(baş, son)` ofsetlərini tokenə
    yazmışdır — biz yalnız həmin aralığı ayırırıq. Daxildəki `{ifadə}`
    hissələri üçün həmin ofsetdən yeni `Lekser` qurulur, ona görə xəta
    mesajları faylın dəqiq yerini göstərir.
    """
    tok = p._al()
    baş, son = tok.dəyər
    return _Oxuyucu(p, baş, son).element()


# ═══════════════════════════════════════════════════════════════════════
#  Xam skan edici
# ═══════════════════════════════════════════════════════════════════════

class _Oxuyucu:
    def __init__(self, parser, baş: int, son: int | None = None):
        self.p = parser
        self.m = parser.s.mətn
        self.n = son if son is not None else len(self.m)
        self.i = baş

    # ── Köməkçilər ────────────────────────────────────────────────────

    def _c(self, irəli: int = 0) -> str:
        j = self.i + irəli
        return self.m[j] if j < self.n else ""

    def _boşluq_atla(self) -> None:
        while self.i < self.n and self.m[self.i] in BOŞLUQ:
            self.i += 1

    def _xəta(self, mesaj: str, qeyd: str = "", *köməklər: str) -> None:
        self.p.x.xəta("ALQ-P031", mesaj, self.p.s.yer(min(self.i, self.n - 1), 1),
                      qeyd, *köməklər)
        raise JSXXətası()

    def _ad_oxu(self) -> str:
        baş = self.i
        if not (self.i < self.n and ad_başlanğıcı_ola_bilər(self.m[self.i])):
            self._xəta("Element adı gözlənilirdi",
                       "`<` işarəsindən sonra ad olmalıdır",
                       "nümunə: <div>, <Sayğac />, <nax.Düymə />")
        while self.i < self.n and (ad_davamı_ola_bilər(self.m[self.i])
                                   or self.m[self.i] in AD_ƏLAVƏ):
            self.i += 1
        return self.m[baş:self.i]

    # ── Element ───────────────────────────────────────────────────────

    def element(self) -> A.İfadə:
        yer = self.p.s.yer(self.i, 1)
        if self._c() != "<":
            self._xəta("`<` gözlənilirdi")
        self.i += 1

        # Parça: <> ... </>
        if self._c() == ">":
            self.i += 1
            uşaqlar = self.uşaqlar_oxu("")
            return A.JSXParça(yer, uşaqlar)

        ad = self._ad_oxu()
        atributlar = self.atributlar_oxu(ad)

        # Öz-bağlanan: <Ad />
        if self._c() == "/":
            self.i += 1
            if self._c() != ">":
                self._xəta("`/>` gözlənilirdi",
                           "öz-bağlanan element belə bitir: `/>`")
            self.i += 1
            return A.JSXElement(yer, ad, atributlar, [])

        if self._c() != ">":
            self._xəta("`>` gözlənilirdi",
                       f"`<{ad}` açılışı bağlanmayıb")
        self.i += 1

        uşaqlar = self.uşaqlar_oxu(ad)
        return A.JSXElement(yer, ad, atributlar, uşaqlar)

    # ── Atributlar ────────────────────────────────────────────────────

    def atributlar_oxu(self, element_adı: str) -> list[A.JSXAtribut]:
        nəticə: list[A.JSXAtribut] = []
        while True:
            self._boşluq_atla()
            c = self._c()
            if c in ("", "/", ">"):
                break

            # Yayma: {...obyekt}
            if c == "{":
                baş = self.i + 1
                son = self._fiqurlu_sonu(self.i)
                içi = self.m[baş:son].strip()
                if not içi.startswith("..."):
                    self._xəta("Atribut adı gözlənilirdi",
                               "`{...obyekt}` yayma sintaksisi istisna "
                               "olmaqla, atributlar adla yazılır")
                ofs = baş + self.m[baş:son].index("...") + 3
                ifadə = self._ifadə_oxu(ofs, son)
                nəticə.append(A.JSXAtribut("", ifadə, yayma=True))
                self.i = son + 1
                continue

            if not ad_başlanğıcı_ola_bilər(c):
                self._xəta(f"`<{element_adı}` daxilində gözlənilməyən "
                           f"simvol: `{c}`",
                           "atribut adı, `/>` və ya `>` gözlənilirdi")

            ad = self._ad_oxu()
            self._boşluq_atla()

            if self._c() != "=":
                # Dəyərsiz atribut → məntiqi `doğru`
                nəticə.append(A.JSXAtribut(ad, None))
                continue

            self.i += 1
            self._boşluq_atla()
            nəticə.append(A.JSXAtribut(ad, self._atribut_dəyəri(ad)))
        return nəticə

    def _atribut_dəyəri(self, ad: str) -> A.İfadə:
        c = self._c()
        yer = self.p.s.yer(self.i, 1)

        if c in (DIRNAQ, APOSTROF):
            # Dəyəri ALQOR MƏTN LİTERALI kimi ayırırıq ki,
            # interpolyasiya işləsin: sinif="düymə-{özü.rəng}"
            baş = self.i
            self.i += 1
            while self.i < self.n and self.m[self.i] != c:
                if self.m[self.i] == TERS_KESIK:
                    self.i += 1
                self.i += 1
            if self.i >= self.n:
                self._xəta("Atribut dəyəri bağlanmayıb",
                           f"`{ad}=` dəyəri {c} ilə bağlanmalıdır")
            self.i += 1
            return self._ifadə_oxu(baş, self.i)

        if c == "{":
            baş = self.i + 1
            son = self._fiqurlu_sonu(self.i)
            ifadə = self._ifadə_oxu(baş, son)
            self.i = son + 1
            return ifadə

        self._xəta(f"`{ad}` atributunun dəyəri gözlənilirdi",
                   'dəyər `"mətn"` və ya `{ifadə}` formasında olur')
        raise JSXXətası()     # çatılmır

    # ── Uşaqlar ───────────────────────────────────────────────────────

    def uşaqlar_oxu(self, açan_ad: str) -> list:
        uşaqlar: list = []
        mətn_başı = self.i

        while True:
            if self.i >= self.n:
                self._xəta(
                    f"`<{açan_ad}>` bağlanmayıb",
                    "fayl bitdi",
                    f"`</{açan_ad}>` əlavə edin")

            c = self.m[self.i]

            if c == "<":
                # Mətn daxilində sadə `<` (məs. `5 < 10`)
                növbəti = self._c(1)
                if not (növbəti in ("/", ">")
                        or ad_başlanğıcı_ola_bilər(növbəti)):
                    self.i += 1
                    continue
                self._mətni_əlavə(uşaqlar, mətn_başı, self.i)
                if növbəti == "/":
                    self.i += 2
                    bağlayan = "" if self._c() == ">" else self._ad_oxu()
                    self._boşluq_atla()
                    if self._c() != ">":
                        self._xəta("`>` gözlənilirdi",
                                   f"`</{bağlayan}` bağlanmayıb")
                    self.i += 1
                    if bağlayan != açan_ad:
                        self.p.x.xəta(
                            "ALQ-P032", "Bağlayan teq uyğun gəlmir",
                            self.p.s.yer(self.i - len(bağlayan) - 3,
                                         len(bağlayan) + 3),
                            f"`<{açan_ad}>` açılıb, `</{bağlayan}>` bağlanıb",
                            f"düzgün forma: `</{açan_ad}>`")
                    return uşaqlar
                uşaqlar.append(self.element())
                mətn_başı = self.i
                continue

            if c == "{":
                self._mətni_əlavə(uşaqlar, mətn_başı, self.i)
                baş = self.i + 1
                son = self._fiqurlu_sonu(self.i)
                if self.m[baş:son].strip():
                    uşaqlar.append(self._ifadə_oxu(baş, son))
                self.i = son + 1
                mətn_başı = self.i
                continue

            self.i += 1

    def _mətni_əlavə(self, uşaqlar: list, baş: int, son: int) -> None:
        xam = self.m[baş:son]
        if not xam:
            return
        mətn = _mətni_səliqəyə_sal(xam)
        if mətn:
            uşaqlar.append(A.JSXMətn(mətn))

    # ── Mötərizə uyğunlaşdırma ────────────────────────────────────────

    def _fiqurlu_sonu(self, açan: int) -> int:
        """
        `{` mövqeyindən uyğun `}` indeksini tapır.
        İç-içə mötərizələri və mətn literallarını nəzərə alır.
        """
        i = açan + 1
        dərinlik = 1
        while i < self.n:
            c = self.m[i]
            if c in (DIRNAQ, APOSTROF, chr(96)):
                i = self._literalı_atla(i)
                continue
            if c in "([{":
                dərinlik += 1
            elif c in ")]}":
                dərinlik -= 1
                if dərinlik == 0:
                    return i
            elif c == "/" and i + 1 < self.n and self.m[i + 1] == "/":
                while i < self.n and self.m[i] != "\n":
                    i += 1
                continue
            i += 1
        self.i = açan
        self._xəta("`{` bağlanmayıb",
                   "JSX daxilindəki ifadə `}` ilə bitməlidir",
                   "fiqurlu mötərizənin özü üçün mətn literalı işlədin")
        return açan

    def _literalı_atla(self, i: int) -> int:
        sitat = self.m[i]
        if self.m.startswith(sitat * 3, i):
            son = self.m.find(sitat * 3, i + 3)
            return self.n if son == -1 else son + 3
        i += 1
        while i < self.n:
            if self.m[i] == "\\":
                i += 2
                continue
            if self.m[i] == sitat:
                return i + 1
            i += 1
        return i

    # ── Daxili ifadənin ayrılması ─────────────────────────────────────

    def _ifadə_oxu(self, baş: int, son: int) -> A.İfadə:
        """
        `[baş, son)` aralığındaki mətni ifadə kimi ayırır.

        Mövqelər qorunur — xəta mesajları faylın düzgün yerini göstərir.
        """
        from .lekser import Lekser
        from .parser import Parser, ParserXətası

        lekser = Lekser(self.p.s, self.p.x, ascii_xəbərdarlığı=False)
        lekser.i = baş
        tokenlər: list[Token] = []
        qoruyucu = 0
        while lekser.i < son and qoruyucu < 100_000:
            köhnə = lekser.i
            lekser._token_oxu(tokenlər, interpolyasiyada=True)
            if lekser.i == köhnə:
                lekser.i += 1
            qoruyucu += 1

        tokenlər = [t for t in tokenlər if t.növ is not Növ.SETIR_SONU]
        tokenlər.append(Token(Növ.FAYL_SONU, None, self.p.s.yer(son, 0)))

        if len(tokenlər) == 1:
            return A.Literal(self.p.s.yer(baş, 0), None, "boş")

        alt = Parser(tokenlər, self.p.s, self.p.x)
        try:
            nəticə = alt._ifadə()
        except ParserXətası:
            return A.Literal(self.p.s.yer(baş, 0), None, "boş")
        # Bütün tokenlər istifadə olunmalıdır. Əks halda `{a + b c}`
        # və ya `{() => x += 1}` (köhnə qrammatika) səssizcə kəsilirdi.
        qalan = alt._bax()
        if qalan.növ is not Növ.FAYL_SONU:
            alt._xəta("ALQ-P001", "Gözlənilməyən token",
                      f"`{alt._göstər(qalan)}` burada gözlənilmirdi",
                      "`{…}` daxilində tək ifadə olmalıdır")
        return nəticə


# ═══════════════════════════════════════════════════════════════════════
#  Mətn uşaqlarının səliqəyə salınması
# ═══════════════════════════════════════════════════════════════════════

def _mətni_səliqəyə_sal(xam: str) -> str:
    """
    JSX qaydası: yeni sətir ehtiva edən tam boşluq hissələri atılır,
    qalan boşluq ardıcıllıqları bir boşluğa yığılır.

        <div>
            Salam
        </div>              → "Salam"

        <span>a</span> <span>b</span>   → aradaki boşluq qalır
    """
    if not xam.strip():
        return "" if "\n" in xam else " "

    sətirlər = xam.split("\n")
    if len(sətirlər) == 1:
        return xam

    hissələr: list[str] = []
    for j, sətir in enumerate(sətirlər):
        s = sətir.strip() if j > 0 else sətir.rstrip()
        if j == 0:
            s = sətir.strip() if sətir.strip() else ""
        if s:
            hissələr.append(s)
    return " ".join(hissələr)
