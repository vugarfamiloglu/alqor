"""
Alqor — redaktorlar üçün sintaksis qrammatikası.

Açar söz siyahıları `acar_sozler`-dən götürülür, ona görə qrammatika
dillə həmişə uzlaşır. Yaradılan fayllar:

    redaktor/vscode/syntaxes/alqor.tmLanguage.json   TextMate qrammatikası
    redaktor/vscode/language-configuration.json      şərh, mötərizə, girinti

Yeniləmək:

    python -m alqor.qrammatika --yaz

`sinaq/test_alqorls.py` faylların bu modulun çıxışı ilə eyni olduğunu
yoxlayır.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import acar_sozler as AS
from .elifba import latınla

KÖK = Path(__file__).resolve().parent.parent.parent
VSCODE = KÖK / "redaktor" / "vscode"
QRAMMATİKA = VSCODE / "syntaxes" / "alqor.tmLanguage.json"
KONFİQ = VSCODE / "language-configuration.json"

HƏRF = r"\p{L}\p{N}_"
AD = r"[\p{L}_][\p{L}\p{N}_]*"


def _formalar(sözlər, ascii: bool = True) -> list[str]:
    """Kanonik + ASCII formalar, uzundan qısaya (alternativ sırası)."""
    n = set()
    for s in sözlər:
        n.add(s)
        if ascii:
            n.add(latınla(s))
    return sorted(n, key=lambda s: (-len(s), s))


def _söz(sözlər, ascii: bool = True) -> str:
    alt = "|".join(s.replace(" ", r"\s+")
                   for s in _formalar(sözlər, ascii))
    return rf"(?<![{HƏRF}])(?:{alt})(?![{HƏRF}])"


def textmate() -> dict:
    # `AS.MODUL` və `AS.OBYEKT` siyahıları modulda sonradan eyni adlı
    # sətir sabitləri ilə kölgələnir — ona görə burada açıq yazılıb
    idarə = AS.SERT + AS.DOVR + AS.AXIN + AS.XETA + ["son"]
    modul = ["gətir", "ixrac", "kimi", "standart"]
    obyekt = ["yeni", "miras", "tətbiq", "ilə", "əvəz"]
    assert set(modul + obyekt) <= AS.ACAR_SOZLER
    elan_açarları = ["funksiya", "metod", "komponent"]
    tip_açarları = ["sinif", "struktur", "interfeys", "sadalama",
                    "obyekt", "qarışıq", "tip", "modul", "mağaza"]

    def mətn(ad: str, baş: str, son: str, interpolyasiya: bool) -> dict:
        p: list[dict] = [{"name": "constant.character.escape.alqor",
                          "match": r"\\(?:u\{[0-9A-Fa-f]+\}|.)"}]
        if interpolyasiya:
            p.append({"include": "#interpolyasiya"})
        return {"name": ad, "begin": baş, "end": son, "patterns": p}

    return {
        "$schema": "https://raw.githubusercontent.com/martinring/"
                   "tmlanguage/master/tmlanguage.json",
        "name": "Alqor",
        "scopeName": "source.alqor",
        "fileTypes": ["alqor"],
        "patterns": [{"include": "#ifadə"}],
        "repository": {
            "ifadə": {"patterns": [
                {"include": "#şərh"},
                {"include": "#mətn"},
                {"include": "#annotasiya"},
                {"include": "#elan"},
                {"include": "#ədəd"},
                {"include": "#açar"},
                {"include": "#operator"},
                {"include": "#çağırış"},
            ]},
            "şərh": {"patterns": [
                {"name": "comment.line.documentation.alqor",
                 "match": r"//[/!].*$"},
                {"name": "comment.line.directive.alqor",
                 "match": r"//\s*alqor:.*$"},
                {"name": "comment.line.double-slash.alqor",
                 "match": r"//.*$"},
                {"name": "comment.block.alqor", "begin": r"/\*",
                 "end": r"\*/", "patterns": [{"include": "#blok-şərh"}]},
            ]},
            "blok-şərh": {"patterns": [
                {"name": "comment.block.alqor", "begin": r"/\*",
                 "end": r"\*/", "patterns": [{"include": "#blok-şərh"}]},
            ]},
            "mətn": {"patterns": [
                mətn("string.quoted.triple.raw.alqor", r'x"""', r'"""',
                     False) | {"patterns": []},
                mətn("string.quoted.double.raw.alqor", r'x"', r'"', False)
                | {"patterns": []},
                mətn("string.quoted.double.bytes.alqor", r'b"', r'"',
                     False),
                mətn("string.quoted.triple.alqor", r'"""', r'"""', True),
                mətn("string.quoted.double.alqor", r'"', r'"', True),
                {"name": "string.quoted.other.char.alqor",
                 "match": r"`(?:\\.|[^`\\])`"},
            ]},
            "interpolyasiya": {
                "name": "meta.interpolation.alqor",
                "begin": r"\{", "end": r"\}",
                "beginCaptures": {"0": {
                    "name": "punctuation.section.interpolation.begin.alqor"}},
                "endCaptures": {"0": {
                    "name": "punctuation.section.interpolation.end.alqor"}},
                "patterns": [{"include": "#ifadə"}],
            },
            "annotasiya": {"name": "entity.name.decorator.alqor",
                           "match": rf"@{AD}"},
            "elan": {"patterns": [
                {"match": rf"({_söz(elan_açarları)})\s+({AD})",
                 "captures": {"1": {"name": "storage.type.function.alqor"},
                              "2": {"name": "entity.name.function.alqor"}}},
                {"match": rf"({_söz(tip_açarları)})\s+({AD})",
                 "captures": {"1": {"name": "storage.type.class.alqor"},
                              "2": {"name": "entity.name.type.alqor"}}},
            ]},
            "ədəd": {"name": "constant.numeric.alqor",
                     "match": r"(?<![\p{L}\p{N}_])(?:0[xX][0-9A-Fa-f_]+"
                              r"|0[bB][01_]+|\d[\d_]*(?:\.\d[\d_]*)?"
                              r"(?:[eE][+-]?\d+)?)"},
            "açar": {"patterns": [
                # Kontekstli sözlər — yalnız konstruksiyanın mövqeyində
                # (§ 5.12, § 5.13, § 9.12, § 13.5, § 4.13)
                {"name": "keyword.control.alqor",
                 "match": r"^[\t ]*(?:tələb|zəmanət|gözlənilir)"
                          r"(?=[\t ]+[^\s=.\[(,:])"},
                {"name": "keyword.control.alqor",
                 "match": r'^[\t ]*sınaq(?=[\t ]+")'},
                {"name": "storage.type.alqor",
                 "match": r"^[\t ]*(?:makro|aktyor)(?=[\t ]+[\p{L}_])"},
                {"name": "keyword.control.alqor",
                 "match": r"(?<![\p{L}\p{N}_])sorğu"
                          r"(?=[\t ]+(?:hər|her)(?![\p{L}\p{N}_]))"},
                {"name": "keyword.control.alqor", "match": _söz(idarə)},
                {"name": "keyword.control.import.alqor",
                 "match": _söz(modul)},
                {"name": "storage.type.alqor", "match": _söz(AS.ELAN)},
                {"name": "storage.modifier.alqor",
                 "match": _söz(AS.MODIFIKATOR)},
                {"name": "keyword.operator.word.alqor",
                 "match": _söz(AS.MENTIQ)},
                {"name": "constant.language.alqor",
                 "match": _söz(AS.LITERAL)},
                {"name": "variable.language.alqor",
                 "match": _söz(["özü", "üst"])},
                {"name": "keyword.other.alqor", "match": _söz(obyekt
                                                              + AS.KOMEKCI)},
                {"name": "support.type.primitive.alqor",
                 # Tip adları açar söz deyil — ASCII forması yoxdur
                 "match": _söz(AS.TIP_ADLARI, ascii=False)},
            ]},
            "operator": {"patterns": [
                {"name": "keyword.operator.arrow.alqor",
                 "match": r"->|=>|→"},
                {"name": "keyword.operator.alqor",
                 "match": r"\?\?|\?\.|\.\.=?|\*\*|[-+*/%]=?|==|!=|<=|>="
                          r"|[<>=|&^~!?]"},
            ]},
            "çağırış": {"match": rf"({AD})\s*(?=\()",
                        "captures": {"1": {
                            "name": "entity.name.function.call.alqor"}}},
        },
    }


# Blok açan sözlər — Enter-dən sonra girinti
_BLOK_AÇAN = ["funksiya", "metod", "sinif", "struktur", "interfeys",
              "sadalama", "modul", "komponent", "qurucu", "obyekt",
              "mağaza", "əgər", "yoxsa", "hər", "nə qədər ki", "həmişə",
              "təkrarla", "cəhd et", "tut", "nəhayət", "seç", "başlanğıc",
              "bitiş", "hal", "digər hallarda", "aktyor", "sınaq"]
_MODİFİKATORLAR = ["açıq", "gizli", "qorunan", "statik", "son",
                   "asinxron", "generator", "ixrac et", "əvəz", "tənbəl"]
_BLOK_BAĞLAYAN = ["son", "yoxsa", "tut", "nəhayət"]


def _alt(sözlər) -> str:
    return "|".join(s.replace(" ", r"\s+") for s in _formalar(sözlər))


def _rx(ifadə: str) -> dict:
    return {"pattern": ifadə, "flags": "u"}


def dil_konfiqurasiyası() -> dict:
    mod = rf"(?:(?:{_alt(_MODİFİKATORLAR)})\s+)*"
    return {
        "comments": {"lineComment": "//", "blockComment": ["/*", "*/"]},
        "brackets": [["{", "}"], ["[", "]"], ["(", ")"]],
        "autoClosingPairs": [
            {"open": "{", "close": "}"}, {"open": "[", "close": "]"},
            {"open": "(", "close": ")"},
            {"open": '"', "close": '"', "notIn": ["string", "comment"]},
            {"open": "`", "close": "`", "notIn": ["string", "comment"]},
        ],
        "surroundingPairs": [["{", "}"], ["[", "]"], ["(", ")"],
                             ['"', '"'], ["`", "`"]],
        # VS Code bu ifadələri JavaScript RegExp kimi qurur — `\p{L}`
        # üçün `u` bayrağı lazımdır
        "wordPattern": _rx(r"[\p{L}_][\p{L}\p{N}_]*|-?\d+(?:\.\d+)?"),
        "indentationRules": {
            # Bir sətirlik formalar (`hal 1 → …`, `… son`) və gövdəsiz
            # mücərrəd metod girinti açmır
            "increaseIndentPattern": _rx(
                rf"^\s*{mod}(?:{_alt(_BLOK_AÇAN)})(?![\p{{L}}\p{{N}}_])"
                r"(?!.*(?:→|=>|\bson\s*$|\bqaytar\b))"
                r"(?!.*\bmücərrəd\b)(?!.*\bxassə(?![\p{L}\p{N}_])).*$"
                r"|^\s*(?:oxu|yaz)\s*$"
                r"|\siçində\s+hər\s.*\süçün\b(?!.*\bson\s*$).*$"),
            "decreaseIndentPattern": _rx(
                rf"^\s*(?:{_alt(_BLOK_BAĞLAYAN)})(?![\p{{L}}\p{{N}}_])"),
        },
        "folding": {"offSide": False},
    }


def _json(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2) + "\n"


def fayllar() -> dict[Path, str]:
    return {QRAMMATİKA: _json(textmate()),
            KONFİQ: _json(dil_konfiqurasiyası())}


def yaz() -> list[Path]:
    dəyişən = []
    for yol, məzmun in fayllar().items():
        if not yol.exists() or yol.read_text(encoding="utf-8") != məzmun:
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_text(məzmun, encoding="utf-8")
            dəyişən.append(yol)
    return dəyişən


if __name__ == "__main__":
    if "--yaz" in sys.argv:
        for y in yaz():
            print(f"✓ {y}")
    else:
        print(_json(textmate()))
