"""
AAC-nin kanonik mətn çapı — `alqor-rs aac` (alqor-rs/src/aac_yaz.rs) ilə
EYNİ mətn. Diferensial müqayisə üçündür (`muqayise.py aac`).

Rust AAC-si interpretatorun ehtiyacı olan sahələri saxlayır (görünüş,
generiklər, sənəd, qaytarma tipi və s. yoxdur) — çap yalnız ortaq
sahələri göstərir.
"""

from __future__ import annotations

from .. import aac as A


def _q(s: str) -> str:
    n = ['"']
    for c in s:
        if c == '"':
            n.append('\\"')
        elif c == "\\":
            n.append("\\\\")
        elif c == "\n":
            n.append("\\n")
        elif c == "\r":
            n.append("\\r")
        elif c == "\t":
            n.append("\\t")
        elif ord(c) < 0x20 or ord(c) == 0x7f:
            n.append("\\u{%x}" % ord(c))
        else:
            n.append(c)
    n.append('"')
    return "".join(n)


def _oq(s) -> str:
    return "-" if s is None else _q(s)


def _qs(v) -> str:
    return "[" + ", ".join(_q(s) for s in v) + "]"


def _b(x) -> str:
    return "true" if x else "false"


def _y(yer) -> str:
    return f"{yer.sətir}:{yer.sütun}+{yer.uzunluq}"


def _f64(x: float) -> str:
    """Rust `{:?}` formatı (f64)."""
    if x != x:
        return "NaN"
    if x in (float("inf"), float("-inf")):
        return "inf" if x > 0 else "-inf"
    r = repr(x)
    if "e" in r:
        m, e = r.split("e")
        return f"{m}e{int(e)}"
    return r


class _İç:
    def __init__(self, w: "_Yazıcı"):
        self.w = w

    def __enter__(self):
        self.w.d += 1

    def __exit__(self, *_):
        self.w.d -= 1


class _Yazıcı:
    def __init__(self):
        self.ç: list[str] = []
        self.d = 0

    def s(self, l: str, t: str) -> None:
        self.ç.append("  " * self.d + (f"{l}: " if l else "") + t)

    def iç(self) -> _İç:
        return _İç(self)

    def siyahı(self, l, v, f) -> None:
        self.s(l, f"[{len(v)}]")
        with self.iç():
            for x in v:
                f(x)

    def gövdə(self, l, g) -> None:
        self.siyahı(l, g, lambda c: self.cümlə("", c))

    def ogövdə(self, l, g) -> None:
        if g is not None:
            self.gövdə(l, g)

    def oifadə(self, l, e) -> None:
        if e is not None:
            self.ifadə(l, e)

    def ifadələr(self, l, v) -> None:
        self.siyahı(l, v, lambda e: self.ifadə("", e))

    def otip(self, l, t) -> None:
        if t is not None:
            self.tip(l, t)

    def tiplər(self, l, v) -> None:
        self.siyahı(l, v, lambda t: self.tip("", t))

    # ── Tiplər, bağlamalar, parametrlər, naxışlar ─────────────────────

    def tip(self, l, t) -> None:
        if isinstance(t, A.TipAdı):
            self.s(l, f"TipAd {_y(t.yer)} yol={_q('.'.join(t.yol))} "
                      f"ixtiyari={_b(t.ixtiyari)}")
            with self.iç():
                self.tiplər("arqumentlər", t.arqumentlər)
        elif isinstance(t, A.TipBirləşmə):
            self.s(l, f"TipBirləşmə {_y(t.yer)}")
            with self.iç():
                self.tiplər("variantlar", t.variantlar)
        elif isinstance(t, A.TipKortej):
            self.s(l, f"TipKortej {_y(t.yer)} ixtiyari={_b(t.ixtiyari)}")
            with self.iç():
                self.tiplər("elementlər", t.elementlər)
        else:
            self.s(l, f"TipFunksiya {_y(t.yer)} ixtiyari={_b(t.ixtiyari)}")
            with self.iç():
                self.tiplər("parametrlər", t.parametrlər)
                self.otip("qaytarma", t.qaytarma)

    def bağlama(self, l, b) -> None:
        n = {"ad": f"növ=ad ad={_q(b.ad or '')}", "atma": "növ=atma",
             "qalan": f"növ=qalan ad={_q(b.ad or '')}",
             "kortej": "növ=kortej", "obyekt": "növ=obyekt"}[b.növ]
        self.s(l, f"Bağlama {_y(b.yer)} {n}")
        with self.iç():
            if b.növ == "kortej":
                self.siyahı("alt", b.alt, lambda x: self.bağlama("", x))
            elif b.növ == "obyekt":
                def sahə(c):
                    self.s("", f"Sahə ad={_q(c[0])}")
                    if c[1] is not None:
                        with self.iç():
                            self.bağlama("bağlama", c[1])
                self.siyahı("sahələr", b.sahələr, sahə)
            self.otip("tip", b.tip)

    def parametr(self, l, p) -> None:
        self.s(l, f"Parametr {_y(p.yer)} ad={_q(p.ad)} variadic={_b(p.variadic)}"
                  f" adlı_variadic={_b(p.adlı_variadic)}"
                  f" yalnız_adlı={_b(p.yalnız_adlı)}"
                  f" xassə_görünüşü={_oq(p.xassə_görünüşü)}")
        with self.iç():
            self.otip("tip", p.tip)
            self.oifadə("standart", p.standart)

    def parametrlər(self, l, v) -> None:
        self.siyahı(l, v, lambda p: self.parametr("", p))

    def bəzəyicilər(self, annotasiyalar) -> None:
        for a in annotasiyalar:
            if a.arqumentlər:
                self.arqumentlər(f"@{a.ad}", a.arqumentlər)

    def arqumentlər(self, l, v) -> None:
        def arq(a):
            self.s("", f"Arqument ad={_oq(a.ad)} yayma={_b(a.yayma)}"
                       f" adlı_yayma={_b(a.adlı_yayma)}")
            with self.iç():
                self.ifadə("dəyər", a.dəyər)
        self.siyahı(l, v, arq)

    def naxış(self, l, n) -> None:
        nv = n.növ
        if nv == "atma":
            self.s(l, "Naxış atma")
        elif nv in ("literal", "şərt"):
            self.s(l, f"Naxış {nv}")
            with self.iç():
                self.ifadə("dəyər", n.dəyər)
        elif nv == "ad":
            self.s(l, f"Naxış ad {_q(n.dəyər)}")
        elif nv == "tip":
            self.s(l, "Naxış tip")
            with self.iç():
                self.tip("tip", n.tip)
        elif nv == "diapazon":
            self.s(l, f"Naxış diapazon xaric={_b(n.diapazon_xaric)}")
            with self.iç():
                self.ifadə("başlanğıc", n.dəyər)
                self.ifadə("son", n.diapazon_son)
        elif nv == "kortej":
            self.s(l, "Naxış kortej")
            with self.iç():
                self.siyahı("alt", n.alt, lambda x: self.naxış("", x))
        elif nv == "siyahı":
            self.s(l, f"Naxış siyahı qalan={_oq(n.qalan)}")
            with self.iç():
                self.siyahı("alt", n.alt, lambda x: self.naxış("", x))
        else:
            self.s(l, "Naxış obyekt")
            with self.iç():
                self.otip("tip", n.tip)
                self.siyahı("alt", n.alt, lambda x: self.naxış("", x))

                def sahə(c):
                    self.s("", f"Sahə ad={_q(c[0])}")
                    if c[1] is not None:
                        with self.iç():
                            self.naxış("naxış", c[1])
                self.siyahı("sahələr", n.sahələr, sahə)

    # ── Cümlələr ──────────────────────────────────────────────────────

    def funksiya(self, l, növ, f, statik, mücərrəd) -> None:
        self.s(l, f"{növ} {_y(f.yer)} ad={_q(f.ad)} asinxron={_b(f.asinxron)}"
                  f" generator={_b(f.generator)} statik={_b(statik)}"
                  f" mücərrəd={_b(mücərrəd)}"
                  f" annotasiyalar={_qs(a.ad for a in f.annotasiyalar)}")
        with self.iç():
            self.bəzəyicilər(f.annotasiyalar)
            self.parametrlər("parametrlər", f.parametrlər)
            self.ogövdə("gövdə", f.gövdə)

    def cümlə(self, l, c) -> None:
        Y = _y(c.yer)
        t = type(c)
        if t is A.İfadəCümləsi:
            self.s(l, f"İfadəCümləsi {Y}")
            with self.iç():
                self.ifadə("ifadə", c.ifadə)
        elif t is A.DəyişənElanı:
            self.s(l, f"DəyişənElanı {Y} növ={_q(c.növ)}")
            with self.iç():
                self.siyahı("bağlamalar", c.bağlamalar,
                            lambda b: self.bağlama("", b))
                self.ifadələr("dəyərlər", c.dəyərlər)
        elif t is A.FunksiyaElanı:
            self.funksiya(l, "Funksiya", c, False, False)
        elif t is A.MetodElanı:
            self.funksiya(l, "Metod", c, c.statik, c.mücərrəd)
        elif t is A.XassəElanı:
            self.s(l, f"Xassə {Y} ad={_q(c.ad)} statik={_b(c.statik)}"
                      f" tənbəl={_b(c.tənbəl)}"
                      f" yaz_parametri={_oq(c.yaz_parametri)}"
                      f" annotasiyalar={_qs(a.ad for a in c.annotasiyalar)}")
            with self.iç():
                self.otip("tip", c.tip)
                self.oifadə("standart", c.standart)
                self.ogövdə("oxu", c.oxu_gövdəsi)
                self.ogövdə("yaz", c.yaz_gövdəsi)
        elif t is A.QurucuElanı:
            self.s(l, f"Qurucu {Y} ad={_oq(c.ad)}")
            with self.iç():
                self.parametrlər("parametrlər", c.parametrlər)
                self.gövdə("gövdə", c.gövdə)
        elif t is A.DağıdıcıElanı:
            self.s(l, f"Dağıdıcı {Y}")
            with self.iç():
                self.gövdə("gövdə", c.gövdə)
        elif t is A.SinifElanı:
            self.s(l, f"Sinif {Y} ad={_q(c.ad)} quruluş={_q(c.quruluş)}"
                      f" mücərrəd={_b(c.mücərrəd)} son={_b(c.son)}"
                      f" annotasiyalar={_qs(a.ad for a in c.annotasiyalar)}")
            with self.iç():
                self.bəzəyicilər(c.annotasiyalar)
                self.otip("baza", c.baza)
                self.tiplər("interfeyslər", c.interfeyslər)
                self.tiplər("qarışıqlar", c.qarışıqlar)
                self.gövdə("üzvlər", c.üzvlər)
        elif t is A.InterfeysElanı:
            self.s(l, f"İnterfeys {Y} ad={_q(c.ad)}")
            with self.iç():
                self.gövdə("üzvlər", c.üzvlər)
        elif t is A.SadalamaElanı:
            self.s(l, f"Sadalama {Y} ad={_q(c.ad)}")
            with self.iç():
                self.otip("əsas_tip", c.əsas_tip)

                def variant(v):
                    self.s("", f"Variant {_y(v.yer)} ad={_q(v.ad)}")
                    with self.iç():
                        self.oifadə("dəyər", v.dəyər)
                        self.arqumentlər("arqumentlər", v.arqumentlər)
                        self.parametrlər("parametrlər", v.parametrlər)
                self.siyahı("variantlar", c.variantlar, variant)
                self.gövdə("üzvlər", c.üzvlər)
        elif t is A.QarışıqElanı:
            self.s(l, f"Qarışıq {Y} ad={_q(c.ad)}")
            with self.iç():
                self.gövdə("üzvlər", c.üzvlər)
        elif t is A.Genişlətmə:
            self.s(l, f"Genişlətmə {Y}")
            with self.iç():
                self.tip("tip", c.tip)
                self.gövdə("üzvlər", c.üzvlər)
        elif t is A.TipAliası:
            self.s(l, f"TipAliası {Y} ad={_q(c.ad)}")
            with self.iç():
                self.tip("tip", c.tip)
        elif t is A.ModulElanı:
            self.s(l, f"Modul {Y} ad={_q(c.ad)}")
            with self.iç():
                self.gövdə("gövdə", c.gövdə)
        elif t is A.Şərt:
            self.s(l, f"Şərt {Y}")
            with self.iç():
                def budaq(b):
                    self.s("", "Budaq")
                    with self.iç():
                        self.ifadə("şərt", b[0])
                        self.gövdə("gövdə", b[1])
                self.siyahı("budaqlar", c.budaqlar, budaq)
                self.ogövdə("yoxsa", c.yoxsa)
        elif t in (A.Varsa, A.Yoxdursa):
            self.s(l, f"{t.__name__} {Y}")
            with self.iç():
                def cüt(b):
                    self.s("", "Cüt")
                    with self.iç():
                        if b[0] is not None:
                            self.bağlama("bağlama", b[0])
                        self.ifadə("ifadə", b[1])
                self.siyahı("bağlamalar", c.bağlamalar, cüt)
                self.gövdə("gövdə", c.gövdə)
                if t is A.Varsa:
                    self.ogövdə("yoxsa", c.yoxsa)
        elif t is A.Seç:
            self.s(l, f"Seç {Y}")
            with self.iç():
                self.oifadə("ifadə", c.ifadə)

                def hal(h):
                    self.s("", f"Hal keç={_b(h.keç)}")
                    with self.iç():
                        self.siyahı("naxışlar", h.naxışlar,
                                    lambda n: self.naxış("", n))
                        self.oifadə("mühafizə", h.mühafizə)
                        self.gövdə("gövdə", h.gövdə)
                self.siyahı("hallar", c.hallar, hal)
                self.ogövdə("digər", c.digər)
        elif t is A.NəQədərKi:
            self.s(l, f"NəQədərKi {Y} etiket={_oq(c.etiket)}")
            with self.iç():
                self.ifadə("şərt", c.şərt)
                self.gövdə("gövdə", c.gövdə)
        elif t is A.Həmişə:
            self.s(l, f"Həmişə {Y} etiket={_oq(c.etiket)}")
            with self.iç():
                self.gövdə("gövdə", c.gövdə)
        elif t is A.Təkrarla:
            self.s(l, f"Təkrarla {Y} sayğac={_oq(c.sayğac)}"
                      f" etiket={_oq(c.etiket)}")
            with self.iç():
                self.ifadə("say", c.say)
                self.gövdə("gövdə", c.gövdə)
        elif t is A.TəkrarlaNəQədər:
            self.s(l, f"TəkrarlaNəQədər {Y} etiket={_oq(c.etiket)}")
            with self.iç():
                self.gövdə("gövdə", c.gövdə)
                self.ifadə("şərt", c.şərt)
        elif t is A.Hər:
            self.s(l, f"Hər {Y} asinxron={_b(c.asinxron)}"
                      f" etiket={_oq(c.etiket)}")
            with self.iç():
                self.siyahı("bağlamalar", c.bağlamalar,
                            lambda b: self.bağlama("", b))
                self.ifadə("mənbə", c.mənbə)
                self.oifadə("addım", c.addım)
                self.oifadə("şərt", c.şərt)
                self.gövdə("gövdə", c.gövdə)
                self.ogövdə("yoxsa", c.yoxsa)
        elif t in (A.Dayan, A.DavamEt):
            self.s(l, f"{t.__name__} {Y} etiket={_oq(c.etiket)}")
        elif t is A.Qaytar:
            self.s(l, f"Qaytar {Y}")
            with self.iç():
                self.ifadələr("dəyərlər", c.dəyərlər)
        elif t is A.Ver:
            self.s(l, f"Ver {Y}")
            with self.iç():
                self.oifadə("dəyər", c.dəyər)
        elif t is A.At:
            self.s(l, f"At {Y}")
            with self.iç():
                self.oifadə("ifadə", c.ifadə)
        elif t is A.Cəhd:
            self.s(l, f"Cəhd {Y}")
            with self.iç():
                self.gövdə("gövdə", c.gövdə)

                def tutma(tm):
                    self.s("", f"Tutma ad={_oq(tm.ad)}")
                    with self.iç():
                        self.tiplər("tiplər", tm.tiplər)
                        self.oifadə("mühafizə", tm.mühafizə)
                        self.gövdə("gövdə", tm.gövdə)
                self.siyahı("tutmalar", c.tutmalar, tutma)
                self.ogövdə("nəhayət", c.nəhayət)
        elif t is A.İddia:
            self.s(l, f"İddia {Y}")
            with self.iç():
                self.ifadə("şərt", c.şərt)
                self.oifadə("mesaj", c.mesaj)
        elif t is A.Təmin:
            self.s(l, f"Təmin {Y}")
            with self.iç():
                self.ifadə("şərt", c.şərt)
                self.gövdə("gövdə", c.gövdə)
        elif t is A.Gecikdir:
            self.s(l, f"Gecikdir {Y}")
            with self.iç():
                self.ifadə("ifadə", c.ifadə)
        elif t is A.İstifadə:
            self.s(l, f"İstifadə {Y}")
            with self.iç():
                def cüt(b):
                    self.s("", f"Cüt ad={_q(b[0])}")
                    with self.iç():
                        self.ifadə("ifadə", b[1])
                self.siyahı("bağlamalar", c.bağlamalar, cüt)
                self.gövdə("gövdə", c.gövdə)
        elif t in (A.Keç, A.DayanNöqtəsi, A.İxracSiyahısı):
            self.s(l, f"{t.__name__} {Y}")
        elif t is A.Global:
            self.s(l, f"Global {Y} adlar={_qs(c.adlar)}")
        elif t is A.İdxal:
            self.s(l, f"İdxal {Y} yol={_qs(c.yol)} mətn_yolu={_oq(c.mətn_yolu)}"
                      f" ləqəb={_oq(c.ləqəb)} hamısı={_b(c.hamısı)}"
                      f" python={_b(c.python)}")
            with self.iç():
                self.siyahı("elementlər", c.elementlər, lambda e: self.s(
                    "", f"Element ad={_q(e.ad)} ləqəb={_oq(e.ləqəb)}"))
        elif t in (A.Başlanğıc, A.Bitiş):
            self.s(l, f"{t.__name__} {Y}")
            with self.iç():
                self.gövdə("gövdə", c.gövdə)
        elif t is A.Artırma:
            self.s(l, f"Artırma {Y} op={_q(c.op)}")
            with self.iç():
                self.ifadə("hədəf", c.hədəf)
        else:
            raise TypeError(f"naməlum cümlə: {t.__name__}")

    # ── İfadələr ──────────────────────────────────────────────────────

    def uşaqlar(self, v) -> None:
        def uşaq(u):
            if isinstance(u, A.JSXMətn):
                self.s("", f"Mətn {_q(u.dəyər)}")
            else:
                self.ifadə("", u)
        self.siyahı("uşaqlar", v, uşaq)

    def ifadə(self, l, e) -> None:
        Y = _y(e.yer)
        t = type(e)
        if t is A.Literal:
            n, d = e.növ, e.dəyər
            if n == "tam":
                x = f"tam {int(d)}"
            elif n == "onluq":
                x = f"onluq {_f64(d)}"
            elif n in ("mətn", "simvol"):
                x = f"{n} {_q(d)}"
            elif n == "bayt":
                x = "bayt [" + ", ".join(str(b) for b in d) + "]"
            elif n == "məntiq":
                x = f"məntiq {_b(d)}"
            else:
                x = "boş"
            self.s(l, f"Literal {Y} {x}")
        elif t is A.ŞablonMətn:
            self.s(l, f"Şablon {Y}")
            with self.iç():
                def parça(p):
                    if isinstance(p, A.MətnHissəsi):
                        self.s("", f"Mətn {_q(p.dəyər)}")
                    else:
                        self.s("", f"Kod format={_oq(p.format)}")
                        with self.iç():
                            self.ifadə("ifadə", p.ifadə)
                self.siyahı("parçalar", e.parçalar, parça)
        elif t is A.Ad:
            self.s(l, f"Ad {Y} {_q(e.ad)}")
        elif t in (A.Özü, A.Üst):
            self.s(l, f"{t.__name__} {Y}")
        elif t is A.İkili:
            self.s(l, f"İkili {Y} op={_q(e.op)}")
            with self.iç():
                self.ifadə("sol", e.sol)
                self.ifadə("sağ", e.sağ)
        elif t is A.TəkOperand:
            self.s(l, f"Tək {Y} op={_q(e.op)}")
            with self.iç():
                self.ifadə("operand", e.operand)
        elif t is A.Mənimsətmə:
            self.s(l, f"Mənimsətmə {Y} op={_q(e.op)}")
            with self.iç():
                self.ifadələr("hədəflər", e.hədəflər)
                self.ifadələr("dəyərlər", e.dəyərlər)
        elif t is A.Çevirmə:
            self.s(l, f"Çevirmə {Y} təhlükəsiz={_b(e.təhlükəsiz)}")
            with self.iç():
                self.ifadə("ifadə", e.ifadə)
                self.tip("tip", e.tip)
        elif t is A.TipYoxlama:
            self.s(l, f"TipYoxlama {Y}")
            with self.iç():
                self.ifadə("ifadə", e.ifadə)
                self.tip("tip", e.tip)
        elif t is A.Üzvlük:
            self.s(l, f"Üzvlük {Y}")
            with self.iç():
                self.ifadə("element", e.element)
                self.ifadə("kolleksiya", e.kolleksiya)
        elif t is A.BoşYoxlama:
            self.s(l, f"BoşYoxlama {Y} inkar={_b(e.inkar)}")
            with self.iç():
                self.ifadə("ifadə", e.ifadə)
        elif t is A.Boru:
            self.s(l, f"Boru {Y}")
            with self.iç():
                self.ifadə("dəyər", e.dəyər)
                self.ifadə("funksiya", e.funksiya)
        elif t is A.Diapazon:
            self.s(l, f"Diapazon {Y} xaric={_b(e.xaric)}")
            with self.iç():
                self.ifadə("başlanğıc", e.başlanğıc)
                self.ifadə("son", e.son)
                self.oifadə("addım", e.addım)
        elif t is A.Çağırış:
            self.s(l, f"Çağırış {Y}")
            with self.iç():
                self.ifadə("funksiya", e.funksiya)
                self.arqumentlər("arqumentlər", e.arqumentlər)
        elif t is A.Üzv:
            self.s(l, f"Üzv {Y} ad={_q(e.ad)} təhlükəsiz={_b(e.təhlükəsiz)}")
            with self.iç():
                self.ifadə("obyekt", e.obyekt)
        elif t is A.İndeks:
            self.s(l, f"İndeks {Y}")
            with self.iç():
                self.ifadə("obyekt", e.obyekt)
                self.ifadə("indeks", e.indeks)
        elif t is A.Dilim:
            self.s(l, f"Dilim {Y} xaric={_b(e.xaric)}")
            with self.iç():
                self.ifadə("obyekt", e.obyekt)
                self.oifadə("başlanğıc", e.başlanğıc)
                self.oifadə("son", e.son)
        elif t in (A.MəcburiAçma, A.Yayma, A.Gözlə):
            self.s(l, f"{t.__name__} {Y}")
            with self.iç():
                self.ifadə("ifadə", e.ifadə)
        elif t is A.Yeni:
            self.s(l, f"Yeni {Y} qurucu={_oq(e.qurucu)}")
            with self.iç():
                self.tip("tip", e.tip)
                self.arqumentlər("arqumentlər", e.arqumentlər)
        elif t is A.SiyahıLiteralı:
            self.s(l, f"Siyahı {Y} yaymalar=["
                      + ", ".join(_b(x) for x in e.yaymalar) + "]")
            with self.iç():
                self.ifadələr("elementlər", e.elementlər)
        elif t is A.LüğətLiteralı:
            self.s(l, f"Lüğət {Y}")
            with self.iç():
                def açar(a):
                    if a is None:
                        self.s("", "-")
                    else:
                        self.ifadə("", a)
                self.siyahı("açarlar", e.açarlar, açar)
                self.ifadələr("dəyərlər", e.dəyərlər)
        elif t in (A.DəstLiteralı, A.KortejLiteralı):
            self.s(l, f"{'Dəst' if t is A.DəstLiteralı else 'Kortej'} {Y}")
            with self.iç():
                self.ifadələr("elementlər", e.elementlər)
        elif t is A.Qurma:
            self.s(l, f"Qurma {Y} növ={_q(e.növ)}")
            with self.iç():
                self.ifadə("ifadə", e.ifadə)
                self.oifadə("dəyər_ifadəsi", e.dəyər_ifadəsi)
                self.bağlama("bağlama", e.bağlama)
                self.ifadə("mənbə", e.mənbə)
                self.oifadə("şərt", e.şərt)
        elif t is A.ŞərtIfadəsi:
            self.s(l, f"ŞərtIfadəsi {Y}")
            with self.iç():
                def budaq(b):
                    self.s("", "Budaq")
                    with self.iç():
                        self.ifadə("şərt", b[0])
                        self.ifadə("dəyər", b[1])
                self.siyahı("budaqlar", e.budaqlar, budaq)
                self.oifadə("yoxsa", e.yoxsa)
        elif t is A.BlokIfadəsi:
            self.s(l, f"Blok {Y}")
            with self.iç():
                self.gövdə("gövdə", e.gövdə)
        elif t is A.Lambda:
            self.s(l, f"Lambda {Y} asinxron={_b(e.asinxron)}"
                      f" generator={_b(e.generator)}")
            with self.iç():
                self.parametrlər("parametrlər", e.parametrlər)
                if isinstance(e.gövdə, list):
                    self.gövdə("gövdə", e.gövdə)
                else:
                    self.ifadə("ifadə", e.gövdə)
        elif t is A.JSXElement:
            self.s(l, f"JSXElement {Y} ad={_q(e.ad)}")
            with self.iç():
                def atribut(a):
                    self.s("", f"Atribut ad={_q(a.ad)} yayma={_b(a.yayma)}")
                    with self.iç():
                        self.oifadə("dəyər", a.dəyər)
                self.siyahı("atributlar", e.atributlar, atribut)
                self.uşaqlar(e.uşaqlar)
        elif t is A.JSXParça:
            self.s(l, f"JSXParça {Y}")
            with self.iç():
                self.uşaqlar(e.uşaqlar)
        else:
            raise TypeError(f"naməlum ifadə: {t.__name__}")


def aac_çapı(p) -> str:
    """Python AAC-sinin kanonik çapı (`alqor-rs aac` ilə eyni)."""
    w = _Yazıcı()
    w.gövdə("Proqram", p.gövdə)
    return "".join(s + "\n" for s in w.ç)


def diaq_çapı(x) -> str:
    """Diaqnostikalar maşın formatında (hesabat sırası ilə)."""
    ç = []
    for d in x._sıralı():
        s = "xəta" if d.xətadır else "xəbərdarlıq"
        yer = _y(d.yer) if d.yer is not None else "-"
        ç.append(f"{s} {d.kod} {yer} {_q(d.mesaj)} qeyd={_q(d.qeyd)} "
                 f"köməklər=[{', '.join(_q(k) for k in d.köməklər)}]")
    return "".join(s + "\n" for s in ç)
