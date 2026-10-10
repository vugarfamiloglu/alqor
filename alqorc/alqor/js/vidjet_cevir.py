"""
`vidjet` modulunun JS hədəfi üçün avtomatik çevrilməsi.

Vidjet konstruktorları (`alqor/vidjet.py`, `alqor/vidjet_elave.py`) təmiz
funksiyalardır: arqumentlərdən `Element` ağacı qururlar. Onları JS-ə əl ilə
köçürmək iki nüsxə saxlamaq deməkdir — biri dəyişəndə o biri geri qalır,
HTML fərqlənir və üslublar pozulur. Ona görə bu modul Python mənbəyini
(`ast`) birbaşa JavaScript-ə çevirir: JS hədəfi həmişə Python ilə eyni
HTML-i qurur (`sinaq/test_js.py` bunu müqayisə edir).

Çevirici ümumi Python kompilyatoru DEYİL — yalnız vidjet fayllarında
işlənən alt çoxluğu bilir. Naməlum konstruksiya `ÇevirməXətası` verir,
yəni vidjet faylında yeni sintaksis işlənəndə sınaq dərhal xəbər verir.

Dəyərlərin JS qarşılığı Alqor JS icra mühiti ilə eynidir:
  None → null, bool → boolean, int → BigInt, float → number,
  str → string, list/tuple → Array, dict → Lüğət, set → Set
"""

from __future__ import annotations

import ast
import functools
import json
from pathlib import Path

KÖK = Path(__file__).resolve().parent.parent
FAYLLAR = (KÖK / "vidjet.py", KÖK / "vidjet_elave.py")

JS_AYRILMIŞ = frozenset("""
break case catch class const continue debugger default delete do else
enum export extends false finally for function if import in instanceof
new null return super switch this throw true try typeof var void while
with yield let static implements interface package private protected
public await arguments eval undefined NaN Infinity async of
""".split())

# Çevrilməyən (yalnız Python tərəfində mənası olan) üst səviyyə adlar
_ATLANAN = frozenset({
    "KATALOQ", "ƏLAVƏ_KATALOQ", "ƏLAVƏLƏR", "ƏLAVƏ_ADLAR",
    "BEYNƏLXALQ_ADLAR", "_KATALOQ_XƏRİTƏSİ", "VİDJETLƏR", "ÜSLUB",
    "ƏLAVƏ_ÜSLUB", "ƏSAS_ÜSLUB", "KATEQORİYALAR", "KATEQORİYA_BEYNƏLXALQ",
})

# Əl ilə yazılmış JS qarşılığı olan funksiyalar (`vidjet_komekci.js`)
_ƏL_İLƏ = frozenset({"işarəliMətn"})

# İdxal olunan adlar → JS köməkçisi
_İDXAL = {"mətnə": "$mətnə", "böyüyə": "$böyüyə", "KICIK": "$KICIK"}

# Python daxili funksiyası → JS köməkçisi
_DAXİLİ = {
    "isinstance": None, "str": "$str", "int": "$int", "float": "$float",
    "len": "$len", "max": None, "min": None, "abs": "$abs",
    "enumerate": None, "range": "$range", "list": "$list",
    "tuple": "$list", "dict": "$dictƏt", "set": "$set",
    "frozenset": "$set", "any": "$any", "all": "$all", "sum": "$sum",
    "callable": "$callable", "bool": "$t", "repr": "$repr",
    "sorted": "$sorted", "reversed": "$reversed", "chr": "$chr",
    "round": "$round",
}

_TİPLƏR = {
    "int": "int", "float": "float", "str": "str", "list": "list",
    "tuple": "tuple", "dict": "dict", "set": "set", "frozenset": "set",
    "bool": "bool", "bytes": "bytes", "Element": "Element",
    "Nümunə": "Nümunə",
}

_İKİLİ = {
    ast.Add: "$add", ast.Sub: "$sub", ast.Mult: "$mul", ast.Div: "$div",
    ast.FloorDiv: "$fdiv", ast.Mod: "$mod", ast.Pow: "$pow",
}

_MÜQAYİSƏ = {
    ast.Lt: "$lt", ast.Gt: "$gt", ast.LtE: "$le", ast.GtE: "$ge",
}


class ÇevirməXətası(Exception):
    pass


def _js_mətn(s: str) -> str:
    return json.dumps(s, ensure_ascii=False).replace(" ", "\\u2028") \
        .replace(" ", "\\u2029")


def _ad(a: str) -> str:
    return a + "$" if a in JS_AYRILMIŞ else a


def _sabit(d) -> str:
    if d is None:
        return "null"
    if d is True:
        return "true"
    if d is False:
        return "false"
    if isinstance(d, int):
        return f"{d}n"
    if isinstance(d, float):
        if d != d:
            return "NaN"
        if d in (float("inf"), float("-inf")):
            return "Infinity" if d > 0 else "-Infinity"
        return repr(d)
    if isinstance(d, str):
        return _js_mətn(d)
    raise ÇevirməXətası(f"sabit dəstəklənmir: {d!r}")


def _təyin_adları(hədəf: ast.AST) -> list[str]:
    if isinstance(hədəf, ast.Name):
        return [hədəf.id]
    if isinstance(hədəf, (ast.Tuple, ast.List)):
        return [a for e in hədəf.elts for a in _təyin_adları(e)]
    if isinstance(hədəf, ast.Starred):
        return _təyin_adları(hədəf.value)
    return []


class _Funksiya:
    """Bir funksiyanın yerli adları."""

    def __init__(self, düyün: ast.FunctionDef | ast.Lambda | None,
                 üst: "_Funksiya | None"):
        self.üst = üst
        self.adlar: set[str] = set()
        self.ləqəblər: dict[str, str] = {}      # `from . import vidjet as V`
        if düyün is not None:
            a = düyün.args
            for p in a.posonlyargs + a.args + a.kwonlyargs:
                self.adlar.add(p.arg)
            if a.vararg is not None:
                self.adlar.add(a.vararg.arg)
            if isinstance(düyün, ast.FunctionDef):
                self._tara(düyün.body)

    def _tara(self, gövdə: list[ast.stmt]) -> None:
        for c in gövdə:
            self._cümlə_adları(c)

    def _cümlə_adları(self, c: ast.stmt) -> None:
        if isinstance(c, ast.FunctionDef):
            self.adlar.add(c.name)
            return
        if isinstance(c, ast.Assign):
            for h in c.targets:
                self.adlar.update(_təyin_adları(h))
        elif isinstance(c, (ast.AnnAssign, ast.AugAssign)):
            self.adlar.update(_təyin_adları(c.target))
        elif isinstance(c, ast.For):
            self.adlar.update(_təyin_adları(c.target))
        elif isinstance(c, (ast.Import, ast.ImportFrom)):
            for a in c.names:
                self.ləqəblər[a.asname or a.name] = a.name
        elif isinstance(c, ast.Try):
            for h in c.handlers:
                if h.name:
                    self.adlar.add(h.name)
        for alt in ("body", "orelse", "finalbody"):
            for cc in getattr(c, alt, []) or []:
                self._cümlə_adları(cc)
        if isinstance(c, ast.Try):
            for h in c.handlers:
                for cc in h.body:
                    self._cümlə_adları(cc)

    def yerlidir(self, ad: str) -> bool:
        f: _Funksiya | None = self
        while f is not None:
            if ad in f.adlar:
                return True
            f = f.üst
        return False

    def ləqəb(self, ad: str) -> str | None:
        f: _Funksiya | None = self
        while f is not None:
            if ad in f.ləqəblər:
                return f.ləqəblər[ad]
            f = f.üst
        return None


class Çevirici:
    def __init__(self) -> None:
        self.funksiyalar: dict[str, ast.FunctionDef] = {}
        self.sabitlər: dict[str, ast.AST] = {}
        self.sıra: list[str] = []
        for yol in FAYLLAR:
            ağac = ast.parse(yol.read_text(encoding="utf-8"), str(yol))
            for c in ağac.body:
                if isinstance(c, ast.FunctionDef):
                    self._qeyd(c.name, c, self.funksiyalar)
                elif isinstance(c, (ast.Assign, ast.AnnAssign)):
                    hədəflər = (c.targets if isinstance(c, ast.Assign)
                                else [c.target])
                    if len(hədəflər) == 1 and \
                            isinstance(hədəflər[0], ast.Name) and \
                            c.value is not None:
                        ad = hədəflər[0].id
                        if ad not in _ATLANAN:
                            self._qeyd(ad, c.value, self.sabitlər)
        self.f: _Funksiya | None = None
        self.temp = 0

    def _qeyd(self, ad: str, d: ast.AST, cədvəl: dict) -> None:
        if ad in self.funksiyalar or ad in self.sabitlər:
            raise ÇevirməXətası(f"`{ad}` iki dəfə təyin edilib")
        cədvəl[ad] = d
        self.sıra.append(ad)

    # ── Asılılıqlar ───────────────────────────────────────────────────

    def lazımi(self, köklər: list[str]) -> list[str]:
        görülən: set[str] = set()
        növbə = list(köklər)
        while növbə:
            ad = növbə.pop()
            if ad in görülən:
                continue
            görülən.add(ad)
            if ad in _ƏL_İLƏ:
                continue
            d = self.funksiyalar.get(ad) or self.sabitlər.get(ad)
            if d is None:
                raise ÇevirməXətası(f"`{ad}` tapılmadı")
            yerli: set[str] = set()
            for x in ast.walk(d):
                if isinstance(x, (ast.FunctionDef, ast.Lambda)):
                    yerli.update(_Funksiya(x, None).adlar)
                elif isinstance(x, ast.comprehension):
                    yerli.update(_təyin_adları(x.target))
            for x in ast.walk(d):
                if isinstance(x, ast.Name) and x.id not in yerli and (
                        x.id in self.funksiyalar or x.id in self.sabitlər):
                    növbə.append(x.id)
                elif isinstance(x, ast.Attribute) and \
                        isinstance(x.value, ast.Name) and x.value.id == "V":
                    növbə.append(x.attr)
        return [a for a in self.sıra if a in görülən]

    # ── Üst səviyyə ───────────────────────────────────────────────────

    def çevir(self, köklər: list[str]) -> str:
        n: list[str] = []
        for ad in self.lazımi(köklər):
            if ad in _ƏL_İLƏ:
                continue
            if ad in self.funksiyalar:
                n.append(self._funksiya(self.funksiyalar[ad], üst=True))
            else:
                self.f = _Funksiya(None, None)
                n.append(f"const {_ad(ad)} = {self._ifadə(self.sabitlər[ad])};")
                self.f = None
        return "\n".join(n)

    def imza(self, ad: str) -> list[tuple[str, ast.AST | None]]:
        """Funksiyanın parametrləri (ad, standart) — `icraçı` xaric."""
        f = self.funksiyalar[ad]
        a = f.args
        p = a.args
        st: list[ast.AST | None] = [None] * (len(p) - len(a.defaults)) + \
            list(a.defaults)
        return [(x.arg, d) for x, d in zip(p, st)][1:]

    def standart_js(self, d: ast.AST | None) -> str:
        if d is None:
            return "undefined"
        köhnə = self.f
        self.f = _Funksiya(None, None)
        try:
            return self._ifadə(d)
        finally:
            self.f = köhnə

    # ── Funksiyalar ───────────────────────────────────────────────────

    def _funksiya(self, d: ast.FunctionDef, üst: bool = False) -> str:
        a = d.args
        if a.kwarg or a.kwonlyargs or a.posonlyargs:
            raise ÇevirməXətası(f"{d.name}: *arqumentlər dəstəklənmir")
        köhnə = self.f
        self.f = _Funksiya(d, köhnə)
        try:
            p = a.args
            st = [None] * (len(p) - len(a.defaults)) + list(a.defaults)
            parametrlər = []
            for x, s in zip(p, st):
                if s is None:
                    parametrlər.append(_ad(x.arg))
                else:
                    parametrlər.append(f"{_ad(x.arg)} = {self._ifadə(s)}")
            if a.vararg is not None:
                parametrlər.append("..." + _ad(a.vararg.arg))
            yerlilər = sorted(self.f.adlar - {x.arg for x in p}
                              - ({a.vararg.arg} if a.vararg else set()))
            gövdə = self._gövdə(_sənədsiz(d.body))
            elan = f"let {', '.join(_ad(y) for y in yerlilər)};\n" \
                if yerlilər else ""
        finally:
            self.f = köhnə
        mətn = (f"function {_ad(d.name)}({', '.join(parametrlər)}) {{\n"
                f"{elan}{gövdə}\n}}")
        return mətn if üst else f"{_ad(d.name)} = {mətn};"

    def _gövdə(self, cümlələr: list[ast.stmt]) -> str:
        return "\n".join(s for c in cümlələr for s in [self._cümlə(c)] if s)

    # ── Cümlələr ──────────────────────────────────────────────────────

    def _cümlə(self, c: ast.stmt) -> str:
        if isinstance(c, ast.Return):
            return "return " + (self._ifadə(c.value) if c.value is not None
                                else "null") + ";"
        if isinstance(c, ast.Expr):
            if isinstance(c.value, ast.Constant):
                return ""                         # sənəd sətri
            return self._ifadə(c.value) + ";"
        if isinstance(c, ast.If):
            s = f"if ({self._şərt(c.test)}) {{\n{self._gövdə(c.body)}\n}}"
            if c.orelse:
                s += f" else {{\n{self._gövdə(c.orelse)}\n}}"
            return s
        if isinstance(c, ast.For):
            if c.orelse:
                raise ÇevirməXətası("for-else dəstəklənmir")
            return (f"for ({self._hədəf_naxışı(c.target)} of "
                    f"$it({self._ifadə(c.iter)})) {{\n"
                    f"{self._gövdə(c.body)}\n}}")
        if isinstance(c, ast.While):
            return (f"while ({self._şərt(c.test)}) {{\n"
                    f"{self._gövdə(c.body)}\n}}")
        if isinstance(c, ast.Assign):
            d = self._ifadə(c.value)
            if len(c.targets) == 1:
                return self._təyin(c.targets[0], d) + ";"
            t = self._yeni_temp()
            return "{ const " + t + " = " + d + "; " + " ".join(
                self._təyin(h, t) + ";" for h in c.targets) + " }"
        if isinstance(c, ast.AnnAssign):
            if c.value is None:
                return ""
            return self._təyin(c.target, self._ifadə(c.value)) + ";"
        if isinstance(c, ast.AugAssign):
            op = _İKİLİ.get(type(c.op))
            if op is None:
                raise ÇevirməXətası(f"`{type(c.op).__name__}=` dəstəklənmir")
            h = c.target
            if isinstance(h, ast.Name):
                a = self._ad_js(h.id)
                return f"{a} = {op}({a}, {self._ifadə(c.value)});"
            if isinstance(h, ast.Subscript):
                o, i = self._yeni_temp(), self._yeni_temp()
                return (f"{{ const {o} = {self._ifadə(h.value)}, {i} = "
                        f"{self._ifadə(h.slice)}; $setInd({o}, {i}, "
                        f"{op}($ind({o}, {i}), {self._ifadə(c.value)})); }}")
            raise ÇevirməXətası("bu artırma hədəfi dəstəklənmir")
        if isinstance(c, ast.Raise):
            if c.exc is None:
                return "throw $son_xəta;"
            return f"throw {self._ifadə(c.exc)};"
        if isinstance(c, ast.Try):
            if c.orelse or c.finalbody:
                raise ÇevirməXətası("try-else/finally dəstəklənmir")
            e = self._yeni_temp()
            budaqlar = []
            for h in c.handlers:
                şərt = "true"
                if h.type is not None:
                    tiplər = (h.type.elts if isinstance(h.type, ast.Tuple)
                              else [h.type])
                    şərt = " || ".join(
                        f"$xətaUyğun({e}, {_js_mətn(ast.unparse(t))})"
                        for t in tiplər)
                bağ = f"{_ad(h.name)} = {e};\n" if h.name else ""
                budaqlar.append(f"if ({şərt}) {{\n{bağ}"
                                f"{self._gövdə(h.body)}\n}}")
            return (f"try {{\n{self._gövdə(c.body)}\n}} catch ({e}) {{\n"
                    + " else ".join(budaqlar) + f" else throw {e};\n}}")
        if isinstance(c, ast.Continue):
            return "continue;"
        if isinstance(c, ast.Break):
            return "break;"
        if isinstance(c, ast.Pass):
            return ""
        if isinstance(c, (ast.Import, ast.ImportFrom)):
            return ""
        if isinstance(c, ast.FunctionDef):
            return self._funksiya(c)
        raise ÇevirməXətası(
            f"{getattr(c, 'lineno', '?')}: `{type(c).__name__}` cümləsi "
            "dəstəklənmir")

    def _yeni_temp(self) -> str:
        self.temp += 1
        return f"$v{self.temp}"

    def _hədəf_naxışı(self, h: ast.AST) -> str:
        """`for` dövrü hədəfi (yerli adlar artıq elan olunub)."""
        if isinstance(h, ast.Name):
            return self._ad_js(h.id)
        if isinstance(h, (ast.Tuple, ast.List)):
            return "[" + ", ".join(self._hədəf_naxışı(e) for e in h.elts) + "]"
        raise ÇevirməXətası("dövr hədəfi dəstəklənmir")

    def _təyin(self, h: ast.AST, d: str) -> str:
        if isinstance(h, ast.Name):
            return f"{self._ad_js(h.id)} = {d}"
        if isinstance(h, (ast.Tuple, ast.List)):
            return (f"[{', '.join(self._hədəf_naxışı(e) for e in h.elts)}]"
                    f" = $açıl({d}, {len(h.elts)})")
        if isinstance(h, ast.Subscript):
            return (f"$setInd({self._ifadə(h.value)}, "
                    f"{self._ifadə(h.slice)}, {d})")
        raise ÇevirməXətası("təyinat hədəfi dəstəklənmir")

    # ── İfadələr ──────────────────────────────────────────────────────

    def _şərt(self, e: ast.AST) -> str:
        """Məntiqi kontekst: JS boolean qaytarır."""
        if isinstance(e, ast.BoolOp):
            op = " && " if isinstance(e.op, ast.And) else " || "
            return "(" + op.join(self._şərt(v) for v in e.values) + ")"
        if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
            return f"!{self._şərt(e.operand)}"
        if isinstance(e, ast.Compare):
            return self._ifadə(e)
        return f"$t({self._ifadə(e)})"

    def _ad_js(self, ad: str) -> str:
        return _ad(ad)

    def _ifadə(self, e: ast.AST) -> str:
        m = getattr(self, "_e_" + type(e).__name__, None)
        if m is None:
            raise ÇevirməXətası(
                f"{getattr(e, 'lineno', '?')}: `{type(e).__name__}` "
                "ifadəsi dəstəklənmir")
        return m(e)

    def _e_Constant(self, e: ast.Constant) -> str:
        return _sabit(e.value)

    def _e_Name(self, e: ast.Name) -> str:
        a = e.id
        if self.f is not None and self.f.yerlidir(a):
            return _ad(a)
        if a in self.funksiyalar or a in self.sabitlər:
            return _ad(a)
        if a in _İDXAL:
            return _İDXAL[a]
        raise ÇevirməXətası(f"{e.lineno}: `{a}` adı tanınmır")

    def _e_Attribute(self, e: ast.Attribute) -> str:
        if isinstance(e.value, ast.Name):
            l = self.f.ləqəb(e.value.id) if self.f else None
            if l == "vidjet" or e.value.id == "V":
                return _ad(e.attr)
            if e.value.id == "math":
                if e.attr == "pi":
                    return "Math.PI"
                return f"$math.{e.attr}"
        if isinstance(e.value, ast.Attribute) and e.attr == "__wrapped__":
            return self._ifadə(e.value)
        return f"$attr({self._ifadə(e.value)}, {_js_mətn(e.attr)})"

    def _e_BinOp(self, e: ast.BinOp) -> str:
        op = _İKİLİ.get(type(e.op))
        if op is None:
            raise ÇevirməXətası(f"{e.lineno}: `{type(e.op).__name__}` "
                                "operatoru dəstəklənmir")
        return f"{op}({self._ifadə(e.left)}, {self._ifadə(e.right)})"

    def _e_UnaryOp(self, e: ast.UnaryOp) -> str:
        if isinstance(e.op, ast.Not):
            return f"!{self._şərt(e.operand)}"
        if isinstance(e.op, ast.USub):
            return f"$neg({self._ifadə(e.operand)})"
        if isinstance(e.op, ast.UAdd):
            return self._ifadə(e.operand)
        raise ÇevirməXətası("tək operator dəstəklənmir")

    def _e_BoolOp(self, e: ast.BoolOp) -> str:
        # Python: `a or b` operandın özünü qaytarır
        f = "$or" if isinstance(e.op, ast.Or) else "$and"
        n = self._ifadə(e.values[-1])
        for v in reversed(e.values[:-1]):
            n = f"{f}({self._ifadə(v)}, () => {n})"
        return n

    def _e_Compare(self, e: ast.Compare) -> str:
        hissələr = []
        sol = e.left
        for op, sağ in zip(e.ops, e.comparators):
            hissələr.append(self._müqayisə(op, sol, sağ))
            sol = sağ
        return hissələr[0] if len(hissələr) == 1 else \
            "(" + " && ".join(hissələr) + ")"

    def _müqayisə(self, op, sol: ast.AST, sağ: ast.AST) -> str:
        a, b = self._ifadə(sol), self._ifadə(sağ)
        if isinstance(op, (ast.Is, ast.IsNot)):
            if isinstance(sağ, ast.Constant) and sağ.value is None:
                return f"({a} {'==' if isinstance(op, ast.Is) else '!='} null)"
            return f"({a} {'===' if isinstance(op, ast.Is) else '!=='} {b})"
        if isinstance(op, ast.Eq):
            return f"$eq({a}, {b})"
        if isinstance(op, ast.NotEq):
            return f"!$eq({a}, {b})"
        if isinstance(op, ast.In):
            return f"$in({a}, {b})"
        if isinstance(op, ast.NotIn):
            return f"!$in({a}, {b})"
        f = _MÜQAYİSƏ.get(type(op))
        if f is None:
            raise ÇevirməXətası("müqayisə dəstəklənmir")
        return f"{f}({a}, {b})"

    def _e_IfExp(self, e: ast.IfExp) -> str:
        return (f"({self._şərt(e.test)} ? {self._ifadə(e.body)} : "
                f"{self._ifadə(e.orelse)})")

    def _e_JoinedStr(self, e: ast.JoinedStr) -> str:
        hissələr = []
        for v in e.values:
            if isinstance(v, ast.Constant):
                hissələr.append(_js_mətn(v.value))
            else:
                hissələr.append(self._e_FormattedValue(v))
        if not hissələr:
            return '""'
        if len(hissələr) == 1:
            return hissələr[0]
        return "(" + " + ".join(hissələr) + ")"

    def _e_FormattedValue(self, e: ast.FormattedValue) -> str:
        d = self._ifadə(e.value)
        if e.conversion == ord("r"):
            d = f"$repr({d})"
        elif e.conversion not in (-1, ord("s")):
            raise ÇevirməXətası("f-mətn çevrilməsi dəstəklənmir")
        if e.format_spec is None:
            return f"$str({d})"
        return f"$fmt({d}, {self._ifadə(e.format_spec)})"

    def _e_List(self, e: ast.List) -> str:
        return "[" + ", ".join(self._element(x) for x in e.elts) + "]"

    _e_Tuple = _e_List

    def _element(self, x: ast.AST) -> str:
        if isinstance(x, ast.Starred):
            return f"...$it({self._ifadə(x.value)})"
        return self._ifadə(x)

    def _e_Set(self, e: ast.Set) -> str:
        return "new Set([" + ", ".join(self._element(x) for x in e.elts) + "])"

    def _e_Dict(self, e: ast.Dict) -> str:
        hissələr = []
        for k, v in zip(e.keys, e.values):
            if k is None:
                hissələr.append(f"...$items({self._ifadə(v)})")
            else:
                hissələr.append(f"[{self._ifadə(k)}, {self._ifadə(v)}]")
        return "$dict([" + ", ".join(hissələr) + "])"

    def _e_Subscript(self, e: ast.Subscript) -> str:
        if isinstance(e.slice, ast.Slice):
            s = e.slice
            if s.step is not None:
                raise ÇevirməXətası("addımlı dilim dəstəklənmir")
            a = self._ifadə(s.lower) if s.lower is not None else "null"
            b = self._ifadə(s.upper) if s.upper is not None else "null"
            return f"$dilim({self._ifadə(e.value)}, {a}, {b})"
        return f"$ind({self._ifadə(e.value)}, {self._ifadə(e.slice)})"

    def _comp(self, e, nəticə) -> str:
        köhnə = self.f
        f = _Funksiya(None, köhnə)
        for g in e.generators:
            f.adlar.update(_təyin_adları(g.target))
        self.f = f
        try:
            iç = nəticə()
            for g in reversed(e.generators):
                if g.is_async:
                    raise ÇevirməXətası("async comprehension")
                for şərt in reversed(g.ifs):
                    iç = f"if ({self._şərt(şərt)}) {{ {iç} }}"
                iç = (f"for (const {self._hədəf_naxışı(g.target)} of "
                      f"$it({self._ifadə(g.iter)})) {{ {iç} }}")
            return iç
        finally:
            self.f = köhnə

    def _e_ListComp(self, e) -> str:
        iç = self._comp(e, lambda: f"$r.push({self._ifadə(e.elt)});")
        return f"(() => {{ const $r = []; {iç} return $r; }})()"

    _e_GeneratorExp = _e_ListComp

    def _e_SetComp(self, e) -> str:
        return f"new Set({self._e_ListComp(e)})"

    def _e_DictComp(self, e) -> str:
        iç = self._comp(e, lambda: f"$r.push([{self._ifadə(e.key)}, "
                        f"{self._ifadə(e.value)}]);")
        return f"$dict((() => {{ const $r = []; {iç} return $r; }})())"

    def _e_Lambda(self, e: ast.Lambda) -> str:
        köhnə = self.f
        self.f = _Funksiya(e, köhnə)
        try:
            p = ", ".join(_ad(a.arg) for a in e.args.args)
            return f"(({p}) => {self._ifadə(e.body)})"
        finally:
            self.f = köhnə

    # ── Çağırışlar ────────────────────────────────────────────────────

    def _arqlar(self, arqlar: list[ast.AST]) -> list[str]:
        return [self._element(a) for a in arqlar]

    def _e_Call(self, e: ast.Call) -> str:
        f = e.func
        if isinstance(f, ast.Name):
            a = f.id
            yerli = self.f is not None and self.f.yerlidir(a)
            if not yerli and a in self.funksiyalar:
                return self._məlum_çağırış(a, e)
            if not yerli and a in _DAXİLİ:
                return self._daxili(a, e)
            if not yerli and a == "Element":
                arq = self._arqlar(e.args)
                return f"$El({', '.join(arq)})"
            if not yerli and a == "AlqorXəta":
                arq = self._arqlar(e.args)
                kod = [k for k in e.keywords if k.arg == "kod"]
                while len(arq) < 3:
                    arq.append("null")
                if kod:
                    arq = arq[:3] + [self._ifadə(kod[0].value)]
                return f"$alqorXəta({', '.join(arq)})"
            if not yerli and a in ("ValueError", "TypeError",
                                   "RuntimeError"):
                return f"$pyXəta({_js_mətn(a)})"
            if e.keywords:
                raise ÇevirməXətası(f"{e.lineno}: `{a}` adlı arqumentlə")
            return f"{self._ifadə(f)}({', '.join(self._arqlar(e.args))})"
        if isinstance(f, ast.Attribute):
            # `vidjet.x(...)`, `V.avatar.__wrapped__(...)`
            hədəf = f
            if hədəf.attr == "__wrapped__" and isinstance(hədəf.value,
                                                         ast.Attribute):
                hədəf = hədəf.value
            if isinstance(hədəf.value, ast.Name) and (
                    hədəf.value.id == "V" or (
                    self.f and self.f.ləqəb(hədəf.value.id) == "vidjet")):
                return self._məlum_çağırış(hədəf.attr, e)
            if isinstance(f.value, ast.Name) and f.value.id == "dict" and \
                    f.attr == "fromkeys":
                return f"$dictFromkeys({', '.join(self._arqlar(e.args))})"
            if isinstance(f.value, ast.Name) and f.value.id == "math":
                return f"$math.{f.attr}({', '.join(self._arqlar(e.args))})"
            # calendar.Calendar(firstweekday=0).monthdayscalendar(i, a)
            if f.attr == "monthdayscalendar":
                return f"$ayHəftələri({', '.join(self._arqlar(e.args))})"
            if e.keywords:
                raise ÇevirməXətası(f"{e.lineno}: metodda adlı arqument")
            arq = self._arqlar(e.args)
            return (f"$m({self._ifadə(f.value)}, {_js_mətn(f.attr)}"
                    + "".join(", " + x for x in arq) + ")")
        if e.keywords:
            raise ÇevirməXətası(f"{e.lineno}: adlı arqument")
        return f"{self._ifadə(f)}({', '.join(self._arqlar(e.args))})"

    def _məlum_çağırış(self, ad: str, e: ast.Call) -> str:
        d = self.funksiyalar.get(ad)
        if d is None:
            raise ÇevirməXətası(f"`{ad}` funksiyası tapılmadı")
        adlar = [p.arg for p in d.args.args]
        arq = self._arqlar(e.args)
        if any(isinstance(a, ast.Starred) for a in e.args):
            if e.keywords:
                raise ÇevirməXətası("yayma və adlı arqument birlikdə")
            return f"{_ad(ad)}({', '.join(arq)})"
        if e.keywords:
            arq = arq + ["undefined"] * (len(adlar) - len(arq))
            for k in e.keywords:
                if k.arg not in adlar:
                    raise ÇevirməXətası(f"`{ad}`: naməlum `{k.arg}`")
                arq[adlar.index(k.arg)] = self._ifadə(k.value)
            while arq and arq[-1] == "undefined":
                arq.pop()
        return f"{_ad(ad)}({', '.join(arq)})"

    def _daxili(self, a: str, e: ast.Call) -> str:
        arq = self._arqlar(e.args[:1] if a == "isinstance" else e.args)
        if a == "isinstance":
            t = e.args[1]
            tiplər = t.elts if isinstance(t, ast.Tuple) else [t]
            adlar = []
            for x in tiplər:
                if not isinstance(x, ast.Name) or x.id not in _TİPLƏR:
                    raise ÇevirməXətası(f"{e.lineno}: isinstance tipi")
                adlar.append(_TİPLƏR[x.id])
            return f"$isinstance({arq[0]}, {json.dumps(adlar)})"
        if a in ("max", "min"):
            f = "$max" if a == "max" else "$min"
            if len(arq) == 1:
                return f"{f}(...$it({arq[0]}))"
            return f"{f}({', '.join(arq)})"
        if a == "enumerate":
            başla = "0n"
            if len(arq) > 1:
                başla = arq[1]
            for k in e.keywords:
                if k.arg == "start":
                    başla = self._ifadə(k.value)
            return f"$enumerate({arq[0]}, {başla})"
        if e.keywords:
            raise ÇevirməXətası(f"{e.lineno}: `{a}` adlı arqumentlə")
        return f"{_DAXİLİ[a]}({', '.join(arq)})"


def _sənədsiz(gövdə: list[ast.stmt]) -> list[ast.stmt]:
    if gövdə and isinstance(gövdə[0], ast.Expr) and \
            isinstance(gövdə[0].value, ast.Constant) and \
            isinstance(gövdə[0].value.value, str):
        return gövdə[1:]
    return gövdə


# ═══════════════════════════════════════════════════════════════════════
#  Modul
# ═══════════════════════════════════════════════════════════════════════

_KÖMƏKÇİLƏR = KÖK / "js" / "vidjet_komekci.js"

# Bütöv vidjeti `üslub:` ilə bəzəmək üçün lazım olan köməkçilər
_ÜSLUB_KÖKLƏRİ = ["üslub_css", "_əsas_idarə", "_stil_əlavə", "FORM_TEQLƏRİ"]


@functools.lru_cache(maxsize=1)
def vidjet_modulu() -> str:
    """`vidjet` modulunun tam JS mətni (icra.js-dən sonra qoşulur)."""
    from .. import vidjet as V
    ç = Çevirici()
    adlar = list(V.VİDJETLƏR)
    gövdə = ç.çevir(adlar + _ÜSLUB_KÖKLƏRİ)
    imzalar = []
    for ad in adlar:
        p = ç.imza(ad)
        imzalar.append(
            f"[{_js_mətn(ad)}, {_ad(ad)}, "
            f"{json.dumps([x for x, _ in p], ensure_ascii=False)}, "
            f"[{', '.join(ç.standart_js(d) for _, d in p)}]]")
    kataloq = json.dumps(V.kataloq(None, None), ensure_ascii=False)
    məlumat = (
        f"const $VİDJETLƏR = [\n" + ",\n".join(imzalar) + "];\n"
        f"const $KATALOQ = {kataloq};\n"
        f"const $KATEQORİYALAR = {json.dumps(list(V.KATEQORİYALAR), ensure_ascii=False)};\n"
        f"const $ÜSLUB = {_js_mətn(V.ÜSLUB)};\n"
        f"const $ƏSAS_ÜSLUB = {_js_mətn(V.ƏSAS_ÜSLUB)};\n")
    köməkçi = _KÖMƏKÇİLƏR.read_text(encoding="utf-8")
    return ("(function ($) {\n\"use strict\";\n" + köməkçi + "\n" + gövdə +
            "\n" + məlumat + "$vidjetQeyd();\n})($);\n")
