"""
Alqor — `alqorpm`: paket meneceri (Spesifikasiya § 8.9).

    alqorpm başlat                     layihe.alq yarat (cari qovluqda)
    alqorpm əlavə veb@^2.1             asılılıq əlavə et və quraşdır
    alqorpm əlavə --inkişaf sınaq_köməkçi
    alqorpm əlavə yerli --yol ../yerli
    alqorpm əlavə util --qit https://github.com/a/b --teq v1.0
    alqorpm sil veb
    alqorpm yüklə [--istehsal]         alqor.kilid-ə görə hamısını quraşdır
    alqorpm yenilə [ad]                kilidi yenidən həll et
    alqorpm siyahı | ağac              quraşdırılmışlar
    alqorpm axtar json | məlumat veb   alqorhub-da axtar / paket haqqında
    alqorpm yoxla                      təhlükəsizlik auditi (+ geri çəkilənlər)
    alqorpm paketlə                    .tar.gz yarat (yayımlamadan yoxlamaq)
    alqorpm yayımla                    alqorhub-a göndər
    alqorpm qeydiyyat | giriş | çıxış  alqorhub hesabı
    alqorpm geri-çək ad@1.0.1          versiyanı geri çək (silinmir)
    alqorpm versiya patch|minor|major  layihə versiyasını artır
    alqorpm işlət <skript>             [skriptlər] bölməsindən
    alqorpm təmizlə                    yerli keşi təmizlə

Depo ünvanı: `--depo URL` › `ALQORHUB` mühit dəyişəni › `layihe.alq`
`[alqorpm] depo` › `~/.alq/ayarlar.json` › https://hub.alqor.vuqar.pro.
Paketlər `paketlər/<ad>/`-a açılır; yüklənən arxivlər SHA256 ilə
yoxlanır və `~/.alq/keş/` qovluğunda saxlanır.
"""

from __future__ import annotations

import getpass
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layihe import MANİFEST, oxu as manifest_oxu
from .paketler import (Aralıq, Versiya, VersiyaXətası, ad_yoxla,
                       layihə_kökü)

STANDART_DEPO = "https://hub.alqor.vuqar.pro"
KİLİD = "alqor.kilid"
MAKS_ARXİV = 50 * 1024 * 1024
_SABİT_ZAMAN = 1577836800                       # 2020-01-01 — təkrarlanan arxiv
_İSTİSNA = {"paketlər", "qurma", ".git", ".hg", ".svn", "__pycache__",
            "node_modules", ".alq", ".idea", ".vscode"}


class PMXətası(Exception):
    def __init__(self, mesaj: str, kod: str = "ALQ-M007"):
        super().__init__(mesaj)
        self.kod = kod


def ev() -> Path:
    return Path(os.environ.get("ALQOR_EV") or Path.home() / ".alq")


def keş_qovluğu() -> Path:
    return ev() / "keş"


# ═══════════════════════════════════════════════════════════════════════
#  Depo müştərisi (alqorhub HTTP API)
# ═══════════════════════════════════════════════════════════════════════

class Depo:
    def __init__(self, ünvan: str, nişan: str | None = None):
        self.ünvan = ünvan.rstrip("/")
        self.nişan = nişan
        self._meta: dict[str, dict] = {}

    def _url(self, yol: str) -> str:
        yol, _, sorğu = yol.partition("?")
        return self.ünvan + "/api/" + "/".join(
            urllib.parse.quote(h, safe="@") for h in yol.split("/")) + \
            (f"?{sorğu}" if sorğu else "")

    def _sorğu(self, üsul: str, yol: str, gövdə: bytes | None = None,
               növ: str = "application/json", tam_url: str | None = None
               ) -> tuple[int, bytes]:
        url = tam_url or self._url(yol)
        r = urllib.request.Request(url, data=gövdə, method=üsul)
        r.add_header("User-Agent", "alqorpm/1")
        r.add_header("Accept", "application/json")
        if gövdə is not None:
            r.add_header("Content-Type", növ)
        if self.nişan:
            r.add_header("Authorization", f"Bearer {self.nişan}")
        try:
            with urllib.request.urlopen(r, timeout=60) as c:
                return c.status, c.read()
        except urllib.error.HTTPError as x:
            return x.code, x.read()
        except (urllib.error.URLError, OSError) as x:
            raise PMXətası(f"alqorhub-a qoşulmaq olmadı ({self.ünvan}): "
                           f"{getattr(x, 'reason', x)}", "ALQ-M001")

    def _json(self, üsul: str, yol: str, gövdə: Any = None,
              gözlə: tuple[int, ...] = (200,)) -> Any:
        data = None if gövdə is None else json.dumps(
            gövdə, ensure_ascii=False).encode("utf-8")
        kod, b = self._sorğu(üsul, yol, data)
        try:
            d = json.loads(b or b"null")
        except ValueError:
            d = {"xəta": b[:200].decode("utf-8", "replace")}
        if kod not in gözlə:
            mesaj = d.get("xəta") if isinstance(d, dict) else None
            raise PMXətası(mesaj or f"alqorhub {kod} qaytardı",
                           "ALQ-M001" if kod == 404 else "ALQ-M007")
        return d

    def meta(self, ad: str) -> dict:
        if ad not in self._meta:
            try:
                self._meta[ad] = self._json("GET", f"paket/{ad}")
            except PMXətası as x:
                raise PMXətası(f"`{ad}` paketi alqorhub-da tapılmadı"
                               if x.kod == "ALQ-M001" and "qoşulmaq" not in
                               str(x) else str(x), x.kod)
        return self._meta[ad]

    def versiyalar(self, ad: str, geri_çəkilənlər: bool = False
                   ) -> dict[Versiya, dict]:
        n = {}
        for v, m in (self.meta(ad).get("versiyalar") or {}).items():
            if m.get("geri_çəkilib") and not geri_çəkilənlər:
                continue
            try:
                n[Versiya.oxu(v)] = m
            except VersiyaXətası:
                continue
        return n

    def endir(self, ad: str, versiya: str) -> bytes:
        kod, b = self._sorğu("GET", f"paket/{ad}/{versiya}/fayl")
        if kod != 200:
            raise PMXətası(f"`{ad}@{versiya}` endirilmədi ({kod})")
        return b

    def axtar(self, q: str) -> list[dict]:
        return self._json("GET", "paketlər?q=" + urllib.parse.quote(q)
                          ).get("nəticə", []) if q is not None else []

    def yayımla(self, ad: str, versiya: str, arxiv: bytes) -> dict:
        kod, b = self._sorğu("PUT", f"paket/{ad}/{versiya}", arxiv,
                             "application/gzip")
        d = json.loads(b or b"{}") if b[:1] in (b"{", b"[") else {}
        if kod not in (200, 201):
            raise PMXətası(d.get("xəta") or f"yayımlanmadı ({kod})")
        return d

    def xəbərdarlıqlar(self) -> list[dict]:
        return self._json("GET", "xəbərdarlıqlar")


# ═══════════════════════════════════════════════════════════════════════
#  Ayarlar və etimadnamələr
# ═══════════════════════════════════════════════════════════════════════

def _ayarlar() -> dict:
    try:
        return json.loads((ev() / "ayarlar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def depo_ünvanı(kök: Path | None, açıq: str | None = None) -> str:
    if açıq:
        return açıq
    if os.environ.get("ALQORHUB"):
        return os.environ["ALQORHUB"]
    if kök is not None:
        m = _manifest(kök)
        d = (m.get("alqorpm") or {}).get("depo")
        if d:
            return str(d)
    return str(_ayarlar().get("depo") or STANDART_DEPO)


def _etimadnamələr() -> dict:
    try:
        return json.loads((ev() / "etimadnamə.json").read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def nişan_al(ünvan: str) -> str | None:
    return os.environ.get("ALQORHUB_NISAN") or \
        _etimadnamələr().get(ünvan.rstrip("/"))


def nişan_yaz(ünvan: str, nişan: str | None) -> None:
    d = _etimadnamələr()
    if nişan is None:
        d.pop(ünvan.rstrip("/"), None)
    else:
        d[ünvan.rstrip("/")] = nişan
    p = ev() / "etimadnamə.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    try:
        p.chmod(0o600)
    except OSError:
        pass


# ═══════════════════════════════════════════════════════════════════════
#  Manifest: oxuma və mətni qoruyan redaktə
# ═══════════════════════════════════════════════════════════════════════

def _manifest(kök: Path) -> dict:
    try:
        return manifest_oxu((kök / MANİFEST).read_text(encoding="utf-8"))
    except OSError:
        return {}


def _açar(ad: str) -> str:
    return ad if re.fullmatch(r"[\w-]+", ad) else json.dumps(
        ad, ensure_ascii=False)


def _dəyər_mətni(d: Any) -> str:
    if isinstance(d, dict):
        return "{ " + ", ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}"
                                for k, v in d.items()) + " }"
    return json.dumps(str(d), ensure_ascii=False)


def manifest_qoy(kök: Path, bölmə: str, ad: str, dəyər: Any) -> None:
    """`[bölmə]` daxilində `ad = dəyər` sətrini yazır/əvəzləyir/silir
    (dəyər None), faylın qalan hissəsinə toxunmadan."""
    p = kök / MANİFEST
    sətirlər = p.read_text(encoding="utf-8").split("\n")
    baş = None
    for i, s in enumerate(sətirlər):
        if s.strip() == f"[{bölmə}]":
            baş = i
            break
    açar_re = re.compile(r"^\s*(" + re.escape(_açar(ad)) + "|" +
                         re.escape(json.dumps(ad, ensure_ascii=False)) +
                         r")\s*=")
    if baş is None:
        if dəyər is None:
            return
        while sətirlər and sətirlər[-1] == "":
            sətirlər.pop()
        sətirlər += ["", f"[{bölmə}]", f"{_açar(ad)} = {_dəyər_mətni(dəyər)}",
                     ""]
    else:
        son = len(sətirlər)
        for j in range(baş + 1, len(sətirlər)):
            if sətirlər[j].lstrip().startswith("["):
                son = j
                break
        yer = next((j for j in range(baş + 1, son)
                    if açar_re.match(sətirlər[j])), None)
        if dəyər is None:
            if yer is not None:
                del sətirlər[yer]
        elif yer is not None:
            sətirlər[yer] = f"{_açar(ad)} = {_dəyər_mətni(dəyər)}"
        else:
            daxil = son
            while daxil > baş + 1 and sətirlər[daxil - 1].strip() == "":
                daxil -= 1
            sətirlər.insert(daxil, f"{_açar(ad)} = {_dəyər_mətni(dəyər)}")
    p.write_text("\n".join(sətirlər), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
#  Kilid faylı
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Seçim:
    ad: str
    versiya: str
    mənbə: str                    # "depo:URL" | "yol:../x" | "qit:URL#commit"
    sha256: str = ""
    asılılıqlar: dict[str, str] = field(default_factory=dict)
    inkişaf: bool = False


def kilid_oxu(kök: Path) -> dict[str, Seçim]:
    try:
        d = manifest_oxu((kök / KİLİD).read_text(encoding="utf-8"))
    except (OSError, Exception):                        # noqa: BLE001
        return {}
    n = {}
    for ad, s in (d.get("paket") or {}).items():
        if isinstance(s, dict) and "versiya" in s:
            n[ad] = Seçim(ad, str(s["versiya"]), str(s.get("mənbə", "")),
                          str(s.get("sha256", "")),
                          dict(s.get("asılılıqlar") or {}),
                          bool(s.get("inkişaf", False)))
    return n


def kilid_yaz(kök: Path, seçimlər: dict[str, Seçim]) -> None:
    n = ["# alqorpm tərəfindən yaradılıb — əl ilə dəyişməyin",
         "versiya = 1", ""]
    for ad in sorted(seçimlər):
        s = seçimlər[ad]
        n += [f"[paket.{_açar(ad)}]",
              f"versiya = {json.dumps(s.versiya)}",
              f"mənbə = {json.dumps(s.mənbə, ensure_ascii=False)}"]
        if s.sha256:
            n.append(f'sha256 = "{s.sha256}"')
        if s.asılılıqlar:
            n.append("asılılıqlar = { " + ", ".join(
                f"{_açar(a)} = {json.dumps(v, ensure_ascii=False)}"
                for a, v in sorted(s.asılılıqlar.items())) + " }")
        if s.inkişaf:
            n.append("inkişaf = doğru")
        n.append("")
    (kök / KİLİD).write_text("\n".join(n), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
#  Asılılıqların həlli
# ═══════════════════════════════════════════════════════════════════════

def _spes(d: Any) -> dict:
    """Manifestdəki dəyər → {"növ": "depo"|"yol"|"qit", …}"""
    if isinstance(d, dict):
        if "yol" in d:
            return {"növ": "yol", "yol": str(d["yol"])}
        if "qit" in d:
            return {"növ": "qit", "qit": str(d["qit"]),
                    "teq": str(d.get("teq") or d.get("budaq") or "")}
        return {"növ": "depo", "aralıq": str(d.get("versiya", "*")),
                "depo": d.get("depo")}
    return {"növ": "depo", "aralıq": str(d)}


@dataclass
class Həll:
    seçimlər: dict[str, Seçim]
    qovluqlar: dict[str, Path]          # yol/qit mənbələri üçün hazır qovluq


class Həlledici:
    def __init__(self, kök: Path, depo: Depo, kilid: dict[str, Seçim],
                 aç: set[str] | None = None, çap=print):
        self.kök, self.depo, self.kilid = kök, depo, kilid
        self.aç = aç or set()              # kilidi nəzərə alınmayanlar
        self.çap = çap
        self._xarici: dict[str, tuple[dict, Path, str]] = {}

    def _xarici_hazırla(self, ad: str, s: dict, baza: Path
                        ) -> tuple[dict, Path, str]:
        """yol / qit mənbəyi → (manifest, qovluq, mənbə mətni)"""
        if ad in self._xarici:
            return self._xarici[ad]
        if s["növ"] == "yol":
            q = (baza / s["yol"]).resolve()
            if not (q / MANİFEST).is_file():
                raise PMXətası(f"`{ad}`: {q} qovluğunda {MANİFEST} yoxdur",
                               "ALQ-M008")
            mənbə = "yol:" + os.path.relpath(q, self.kök).replace("\\", "/")
        else:
            q = Path(tempfile.mkdtemp(prefix="alqorpm-qit-"))
            əmr = ["git", "clone", "--depth", "1", "-q"]
            if s.get("teq"):
                əmr += ["--branch", s["teq"]]
            try:
                subprocess.run(əmr + [s["qit"], str(q)], check=True,
                               capture_output=True, timeout=300)
                commit = subprocess.run(
                    ["git", "-C", str(q), "rev-parse", "HEAD"], check=True,
                    capture_output=True, text=True).stdout.strip()
            except FileNotFoundError:
                raise PMXətası("`git` tapılmadı — qit asılılıqları üçün "
                               "lazımdır")
            except subprocess.CalledProcessError as x:
                raise PMXətası(f"`{ad}`: git clone alınmadı: "
                               f"{x.stderr.decode('utf-8', 'replace')[:200]}")
            mənbə = f"qit:{s['qit']}#{commit}"
        m = _manifest(q)
        self._xarici[ad] = (m, q, mənbə)
        return self._xarici[ad]

    def həll_et(self, kök_asılılıqlar: dict[str, Any],
                inkişaf: dict[str, Any]) -> Həll:
        öyrənilən: dict[str, list[tuple[Aralıq, str]]] = {}
        for _ in range(100):
            try:
                return self._bir_dövr(kök_asılılıqlar, inkişaf, öyrənilən)
            except _YenidənBaşla:
                continue
        raise PMXətası("asılılıqlar həll olunmadı (çox ziddiyyət)")

    def _bir_dövr(self, kök_asılılıqlar, inkişaf, öyrənilən) -> Həll:
        tələblər: dict[str, list[tuple[Aralıq, str]]] = {
            a: list(v) for a, v in öyrənilən.items()}
        seçimlər: dict[str, Seçim] = {}
        qovluqlar: dict[str, Path] = {}
        növbə: list[tuple[str, Any, str, Path, bool]] = []
        for ad, d in kök_asılılıqlar.items():
            növbə.append((ad, d, "layihə", self.kök, False))
        for ad, d in inkişaf.items():
            növbə.append((ad, d, "layihə (inkişaf)", self.kök, True))
        while növbə:
            ad, d, kim, baza, ink = növbə.pop(0)
            ad_yoxla(ad)
            s = _spes(d)
            if s["növ"] != "depo":
                if ad in seçimlər:
                    if not ink:
                        seçimlər[ad].inkişaf = False
                    continue
                m, q, mənbə = self._xarici_hazırla(ad, s, baza)
                v = str((m.get("paket") or {}).get("versiya", "0.0.0"))
                ası = {**(m.get("asılılıqlar") or {})}
                seçimlər[ad] = Seçim(ad, v, mənbə, "", {
                    a: (x if isinstance(x, str) else json.dumps(x))
                    for a, x in ası.items()}, ink)
                qovluqlar[ad] = q
                for a, x in ası.items():
                    növbə.append((a, x, f"{ad}@{v}", q, ink))
                continue
            try:
                aralıq = Aralıq(s["aralıq"])
            except VersiyaXətası as x:
                raise PMXətası(f"`{ad}` ({kim}): {x}")
            tələblər.setdefault(ad, []).append((aralıq, kim))
            if ad in seçimlər:
                if not ink:
                    seçimlər[ad].inkişaf = False
                if seçimlər[ad].mənbə.startswith(("yol:", "qit:")):
                    continue
                cari = Versiya.oxu(seçimlər[ad].versiya)
                if not aralıq.uyğundur(cari):
                    # ziddiyyət: bu tələbi öyrən və yenidən başla
                    öyrənilən.setdefault(ad, []).append((aralıq, kim))
                    self._mümkündürmü(ad, tələblər[ad])
                    raise _YenidənBaşla()
                continue
            v, meta = self._seç(ad, tələblər[ad])
            ası = dict(meta.get("asılılıqlar") or {})
            seçimlər[ad] = Seçim(ad, str(v), "depo:" + self.depo.ünvan,
                                 meta.get("sha256", ""), ası, ink)
            for a, x in ası.items():
                növbə.append((a, x, f"{ad}@{v}", self.kök, ink))
        return Həll(seçimlər, qovluqlar)

    def _mümkündürmü(self, ad: str, t: list[tuple[Aralıq, str]]) -> None:
        if not any(all(a.uyğundur(v) for a, _ in t)
                   for v in self.depo.versiyalar(ad)):
            raise PMXətası(
                f"`{ad}` üçün hamını qane edən versiya yoxdur:\n" +
                "\n".join(f"    {kim} tələb edir: {a}" for a, kim in t),
                "ALQ-M007")

    def _seç(self, ad: str, t: list[tuple[Aralıq, str]]
             ) -> tuple[Versiya, dict]:
        kil = self.kilid.get(ad)
        if kil and ad not in self.aç and kil.mənbə.startswith("depo:"):
            v = Versiya.oxu(kil.versiya)
            if all(a.uyğundur(v) for a, _ in t):
                hamısı = self.depo.versiyalar(ad, geri_çəkilənlər=True)
                if v in hamısı:
                    return v, hamısı[v]
        mövcud = self.depo.versiyalar(ad)
        uyğun = [v for v in mövcud if all(a.uyğundur(v) for a, _ in t)]
        if not uyğun:
            if not mövcud:
                raise PMXətası(f"`{ad}` paketinin yayımlanmış versiyası yoxdur",
                               "ALQ-M001")
            raise PMXətası(
                f"`{ad}` üçün uyğun versiya yoxdur (mövcud: "
                f"{', '.join(map(str, sorted(mövcud)[-5:]))}):\n" +
                "\n".join(f"    {kim} tələb edir: {a}" for a, kim in t),
                "ALQ-M007")
        v = max(uyğun)
        return v, mövcud[v]


class _YenidənBaşla(Exception):
    pass


# ═══════════════════════════════════════════════════════════════════════
#  Arxivlər
# ═══════════════════════════════════════════════════════════════════════

def _istisnalar(kök: Path) -> list[str]:
    try:
        return [s.strip() for s in (kök / ".alqorpmignore").read_text(
            encoding="utf-8").splitlines() if s.strip() and
            not s.startswith("#")]
    except OSError:
        return []


def arxiv_yarat(kök: Path) -> tuple[bytes, dict]:
    """Layihəni yayım arxivinə yığır (təkrarlana bilən: sabit zaman)."""
    import fnmatch
    m = _manifest(kök)
    p = m.get("paket") or {}
    if not p.get("ad") or not p.get("versiya"):
        raise PMXətası(f"{MANİFEST}: [paket] ad və versiya lazımdır",
                       "ALQ-M009")
    ad_yoxla(str(p["ad"]))
    Versiya.oxu(str(p["versiya"]))
    naxışlar = _istisnalar(kök)
    fayllar = []
    for f in sorted(kök.rglob("*")):
        nisbi = f.relative_to(kök).as_posix()
        hissələr = nisbi.split("/")
        # kitabxananın kilidi onu işlədən layihəyə aid deyil
        if any(h in _İSTİSNA for h in hissələr) or nisbi == KİLİD:
            continue
        if any(fnmatch.fnmatch(nisbi, n) or fnmatch.fnmatch(hissələr[-1], n)
               or nisbi.startswith(n.rstrip("/") + "/") for n in naxışlar):
            continue
        if f.is_file() and not f.is_symlink():
            fayllar.append((nisbi, f))
    b = io.BytesIO()
    with gzip.GzipFile(fileobj=b, mode="wb", mtime=_SABİT_ZAMAN) as gz:
        with tarfile.open(fileobj=gz, mode="w",
                          format=tarfile.PAX_FORMAT) as t:
            for nisbi, f in fayllar:
                ti = tarfile.TarInfo("paket/" + nisbi)
                d = f.read_bytes()
                ti.size, ti.mtime = len(d), _SABİT_ZAMAN
                ti.mode = 0o755 if os.access(f, os.X_OK) and \
                    f.suffix not in (".alq", ".md") else 0o644
                t.addfile(ti, io.BytesIO(d))
    data = b.getvalue()
    if len(data) > MAKS_ARXİV:
        raise PMXətası(f"arxiv çox böyükdür ({len(data) // 1024} KB)")
    return data, m


def arxiv_aç(data: bytes, hədəf: Path) -> None:
    """Təhlükəsiz açma: mütləq yol, `..`, keçid, cihaz faylı rədd edilir."""
    if hədəf.exists():
        shutil.rmtree(hədəf)
    hədəf.mkdir(parents=True)
    kök = hədəf.resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        for m in t.getmembers():
            ad = m.name
            if not ad.startswith("paket/") or ".." in ad.split("/") or \
                    ad.startswith("/") or "\\" in ad:
                raise PMXətası(f"arxivdə şübhəli yol: {ad}", "ALQ-M010")
            if m.isdir():
                continue
            if not m.isfile():
                raise PMXətası(f"arxivdə icazəsiz fayl növü: {ad}",
                               "ALQ-M010")
            yol = (kök / ad[len("paket/"):]).resolve()
            if kök not in yol.parents:
                raise PMXətası(f"arxivdə şübhəli yol: {ad}", "ALQ-M010")
            yol.parent.mkdir(parents=True, exist_ok=True)
            yol.write_bytes(t.extractfile(m).read())
            if m.mode & 0o111:
                try:
                    yol.chmod(0o755)
                except OSError:
                    pass


def arxiv_manifesti(data: bytes) -> dict:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        for ad in (f"paket/{MANİFEST}", "paket/layihe.alqor"):
            try:
                return manifest_oxu(t.extractfile(ad).read().decode("utf-8"))
            except KeyError:
                continue
    raise PMXətası(f"arxivdə {MANİFEST} yoxdur", "ALQ-M008")


# ═══════════════════════════════════════════════════════════════════════
#  Quraşdırma
# ═══════════════════════════════════════════════════════════════════════

def _keşdən_və_ya_endir(depo: Depo, s: Seçim) -> bytes:
    keş = keş_qovluğu() / s.ad.replace("/", "%") / f"{s.versiya}.tar.gz"
    if keş.is_file():
        d = keş.read_bytes()
        if not s.sha256 or hashlib.sha256(d).hexdigest() == s.sha256:
            return d
    d = depo.endir(s.ad, s.versiya)
    h = hashlib.sha256(d).hexdigest()
    if s.sha256 and h != s.sha256:
        raise PMXətası(f"`{s.ad}@{s.versiya}`: SHA256 uyğun gəlmir — arxiv "
                       f"dəyişdirilib (gözlənilən {s.sha256[:12]}…, gələn "
                       f"{h[:12]}…)", "ALQ-M010")
    keş.parent.mkdir(parents=True, exist_ok=True)
    keş.write_bytes(d)
    return d


def _kopyala(mənbə: Path, hədəf: Path) -> None:
    if hədəf.exists():
        shutil.rmtree(hədəf)
    shutil.copytree(mənbə, hədəf, ignore=shutil.ignore_patterns(*_İSTİSNA))


def quraşdır(kök: Path, həll: Həll, depo: Depo, istehsal: bool = False,
             çap=print) -> int:
    paketlər = kök / "paketlər"
    paketlər.mkdir(exist_ok=True)
    vəziyyət_f = paketlər / ".alqorpm.json"
    try:
        əvvəlki = json.loads(vəziyyət_f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        əvvəlki = {}
    say = 0
    yeni_vəziyyət = {}
    for ad, s in sorted(həll.seçimlər.items()):
        if istehsal and s.inkişaf:
            continue
        hədəf = paketlər / ad
        açar = f"{s.versiya}|{s.mənbə}|{s.sha256}"
        yeni_vəziyyət[ad] = açar
        if əvvəlki.get(ad) == açar and hədəf.is_dir() and \
                not s.mənbə.startswith("yol:"):
            continue
        if s.mənbə.startswith("depo:"):
            arxiv_aç(_keşdən_və_ya_endir(depo, s), hədəf)
        else:
            _kopyala(həll.qovluqlar[ad], hədəf)
        çap(f"  + {ad}@{s.versiya}"
            + ("" if s.mənbə.startswith("depo:") else
               f"  ({s.mənbə.split('#')[0]})"))
        say += 1
    for ad in əvvəlki:
        if ad not in yeni_vəziyyət and (paketlər / ad).is_dir():
            shutil.rmtree(paketlər / ad)
            if ad.startswith("@"):
                try:
                    (paketlər / ad).parent.rmdir()
                except OSError:
                    pass
            çap(f"  - {ad}")
    vəziyyət_f.write_text(json.dumps(yeni_vəziyyət, ensure_ascii=False,
                                     indent=2), encoding="utf-8")
    for q in həll.qovluqlar.values():
        if q.name.startswith("alqorpm-qit-"):
            shutil.rmtree(q, ignore_errors=True)
    return say


# ═══════════════════════════════════════════════════════════════════════
#  Əmrlər
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Kontekst:
    kök: Path
    depo: Depo
    arq: list[str]
    bayraqlar: dict[str, Any]


def _kök_tələb() -> Path:
    k = layihə_kökü(Path.cwd())
    if k is None:
        raise PMXətası(f"{MANİFEST} tapılmadı — `alqorpm başlat` işlədin",
                       "ALQ-M008")
    return k


def _həll_və_quraşdır(kök: Path, depo: Depo, aç: set[str] | None = None,
                      istehsal: bool = False, kilidsiz: bool = False) -> None:
    m = _manifest(kök)
    kilid = {} if kilidsiz else kilid_oxu(kök)
    h = Həlledici(kök, depo, kilid, aç).həll_et(
        dict(m.get("asılılıqlar") or {}),
        dict(m.get("inkişaf_asılılıqları") or {}))
    kilid_yaz(kök, h.seçimlər)
    say = quraşdır(kök, h, depo, istehsal)
    print(f"✓ {len(h.seçimlər)} paket həll olundu, {say} quraşdırıldı "
          f"({KİLİD} yeniləndi)")


def ə_başlat(k: Kontekst) -> int:
    kök = Path.cwd()
    if (kök / MANİFEST).exists():
        print(f"ℹ {MANİFEST} artıq var")
        return 0
    ad = re.sub(r"[^\wəıöüğşç-]+", "-", kök.name.lower()).strip("-") or \
        "layihe"
    (kök / MANİFEST).write_text(
        f'[paket]\nad = "{ad}"\nversiya = "0.1.0"\ntəsvir = ""\n'
        'lisenziya = "MIT"\n\n[qurma]\ngiriş = "mənbə/əsas.alq"\n\n'
        "[asılılıqlar]\n", encoding="utf-8")
    print(f"✓ {MANİFEST} yaradıldı ({ad} 0.1.0)")
    return 0


def _ad_versiya(s: str) -> tuple[str, str | None]:
    if s.startswith("@"):
        q, _, v = s[1:].partition("@")
        return "@" + q, v or None
    a, _, v = s.partition("@")
    return a, v or None


def ə_əlavə(k: Kontekst) -> int:
    if not k.arq:
        raise PMXətası("paket adı lazımdır: alqorpm əlavə ad[@versiya]")
    bölmə = "inkişaf_asılılıqları" if k.bayraqlar.get("inkişaf") \
        else "asılılıqlar"
    for x in k.arq:
        ad, v = _ad_versiya(x)
        ad_yoxla(ad)
        if k.bayraqlar.get("yol"):
            dəyər: Any = {"yol": k.bayraqlar["yol"]}
        elif k.bayraqlar.get("qit"):
            dəyər = {"qit": k.bayraqlar["qit"]}
            if k.bayraqlar.get("teq"):
                dəyər["teq"] = k.bayraqlar["teq"]
        else:
            if v:
                Aralıq(v)
                dəyər = v
            else:
                son = max(k.depo.versiyalar(ad), default=None)
                if son is None:
                    raise PMXətası(f"`{ad}` paketinin versiyası yoxdur",
                                   "ALQ-M001")
                dəyər = f"^{son}"
        manifest_qoy(k.kök, bölmə, ad, dəyər)
        print(f"✓ {ad} = {_dəyər_mətni(dəyər)}  → [{bölmə}]")
    _həll_və_quraşdır(k.kök, k.depo, aç={_ad_versiya(x)[0] for x in k.arq})
    return 0


def ə_sil(k: Kontekst) -> int:
    if not k.arq:
        raise PMXətası("silinəcək paket adı lazımdır")
    m = _manifest(k.kök)
    for ad in k.arq:
        tapıldı = False
        for b in ("asılılıqlar", "inkişaf_asılılıqları"):
            if ad in (m.get(b) or {}):
                manifest_qoy(k.kök, b, ad, None)
                tapıldı = True
        if not tapıldı:
            raise PMXətası(f"`{ad}` asılılıqlarda yoxdur", "ALQ-M001")
        print(f"✓ {ad} silindi")
    _həll_və_quraşdır(k.kök, k.depo)
    return 0


def ə_yüklə(k: Kontekst) -> int:
    _həll_və_quraşdır(k.kök, k.depo, istehsal=bool(
        k.bayraqlar.get("istehsal")))
    return 0


def ə_yenilə(k: Kontekst) -> int:
    if k.arq:
        _həll_və_quraşdır(k.kök, k.depo, aç=set(k.arq))
    else:
        _həll_və_quraşdır(k.kök, k.depo, kilidsiz=True)
    return 0


def ə_siyahı(k: Kontekst) -> int:
    kilid = kilid_oxu(k.kök)
    if not kilid:
        print("(asılılıq yoxdur)")
        return 0
    m = _manifest(k.kök)
    birbaşa = set(m.get("asılılıqlar") or {}) | set(
        m.get("inkişaf_asılılıqları") or {})
    for ad in sorted(kilid):
        s = kilid[ad]
        işarə = "●" if ad in birbaşa else "○"
        əlavə = " (inkişaf)" if s.inkişaf else ""
        mənbə = "" if s.mənbə.startswith("depo:") else \
            f"  [{s.mənbə.split('#')[0]}]"
        quraşdırılıb = "" if (k.kök / "paketlər" / ad).is_dir() else \
            "  ⚠ quraşdırılmayıb"
        print(f"{işarə} {ad}@{s.versiya}{əlavə}{mənbə}{quraşdırılıb}")
    return 0


def ə_ağac(k: Kontekst) -> int:
    kilid = kilid_oxu(k.kök)
    m = _manifest(k.kök)
    p = m.get("paket") or {}
    print(f"{p.get('ad', k.kök.name)}@{p.get('versiya', '?')}")
    kökdəkilər = list(m.get("asılılıqlar") or {}) + list(
        m.get("inkişaf_asılılıqları") or {})

    def gəz(ad: str, prefiks: str, son: bool, yol: set) -> None:
        s = kilid.get(ad)
        ver = f"@{s.versiya}" if s else " (həll olunmayıb)"
        təkrar = " (dövri)" if ad in yol else ""
        print(f"{prefiks}{'└── ' if son else '├── '}{ad}{ver}{təkrar}")
        if not s or ad in yol:
            return
        uşaqlar = sorted(s.asılılıqlar)
        for i, u in enumerate(uşaqlar):
            gəz(u, prefiks + ("    " if son else "│   "),
                i == len(uşaqlar) - 1, yol | {ad})
    for i, ad in enumerate(kökdəkilər):
        gəz(ad, "", i == len(kökdəkilər) - 1, set())
    return 0


def ə_axtar(k: Kontekst) -> int:
    n = k.depo.axtar(" ".join(k.arq))
    if not n:
        print("heç nə tapılmadı")
    for x in n:
        print(f"{x['ad']}@{x.get('son') or '?'}  "
              f"{(x.get('təsvir') or '')[:70]}")
    return 0


def ə_məlumat(k: Kontekst) -> int:
    if not k.arq:
        raise PMXətası("paket adı lazımdır")
    m = k.depo.meta(k.arq[0])
    print(f"{m['ad']}  —  {m.get('təsvir') or ''}")
    for a in ("son", "lisenziya", "depo_url", "sahiblər", "endirmə"):
        if m.get(a):
            v = ", ".join(m[a]) if isinstance(m[a], list) else m[a]
            print(f"  {a}: {v}")
    vs = sorted(k.depo.versiyalar(k.arq[0], True), reverse=True)
    print("  versiyalar: " + ", ".join(
        f"{v}{' (geri çəkilib)' if m['versiyalar'][str(v)].get('geri_çəkilib') else ''}"
        for v in vs[:15]))
    son = m["versiyalar"].get(m.get("son") or "", {})
    if son.get("asılılıqlar"):
        print("  asılılıqlar: " + ", ".join(
            f"{a} {b}" for a, b in son["asılılıqlar"].items()))
    return 0


def ə_yoxla(k: Kontekst) -> int:
    kilid = kilid_oxu(k.kök)
    xəbər = k.depo.xəbərdarlıqlar()
    problem = 0
    for ad, s in sorted(kilid.items()):
        if not s.mənbə.startswith("depo:"):
            continue
        v = Versiya.oxu(s.versiya)
        for x in xəbər:
            if x.get("paket") == ad and Aralıq(x.get("aralıq", "*")
                                               ).uyğundur(v):
                problem += 1
                print(f"✖ {ad}@{s.versiya}  [{x.get('səviyyə', '?')}] "
                      f"{x.get('başlıq', '')}")
                if x.get("düzəlib"):
                    print(f"    düzəliş: {x['düzəlib']} — "
                          f"alqorpm yenilə {ad}")
        try:
            m = k.depo.meta(ad)
            if (m.get("versiyalar") or {}).get(s.versiya, {}).get(
                    "geri_çəkilib"):
                problem += 1
                print(f"⚠ {ad}@{s.versiya} geri çəkilib — "
                      f"alqorpm yenilə {ad}")
        except PMXətası:
            pass
    if not problem:
        print(f"✓ {len(kilid)} paket yoxlandı, problem yoxdur")
    return 1 if problem else 0


def ə_paketlə(k: Kontekst) -> int:
    data, m = arxiv_yarat(k.kök)
    p = m["paket"]
    hədəf = k.kök / "qurma" / f"{str(p['ad']).replace('/', '%')}-" \
                              f"{p['versiya']}.tar.gz"
    hədəf.parent.mkdir(exist_ok=True)
    hədəf.write_bytes(data)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        adlar = t.getnames()
    for a in adlar:
        print(f"  {a[len('paket/'):]}")
    print(f"✓ {hədəf.relative_to(k.kök)}  ({len(data) / 1024:.1f} KB, "
          f"{len(adlar)} fayl, sha256 {hashlib.sha256(data).hexdigest()[:16]}…)")
    return 0


def ə_yayımla(k: Kontekst) -> int:
    if not k.depo.nişan:
        raise PMXətası("əvvəlcə daxil olun: alqorpm giriş")
    m = _manifest(k.kök)
    for b in ("asılılıqlar", "inkişaf_asılılıqları"):
        for ad, d in (m.get(b) or {}).items():
            if _spes(d)["növ"] != "depo" and b == "asılılıqlar":
                raise PMXətası(f"`{ad}` yol/qit asılılığıdır — yayımlanan "
                               "paket yalnız depo paketlərindən asılı ola "
                               "bilər")
    data, m = arxiv_yarat(k.kök)
    p = m["paket"]
    if k.bayraqlar.get("sınaq"):
        print(f"✓ (sınaq) {p['ad']}@{p['versiya']} hazırdır, "
              f"{len(data) / 1024:.1f} KB — göndərilmədi")
        return 0
    n = k.depo.yayımla(str(p["ad"]), str(p["versiya"]), data)
    print(f"✓ {p['ad']}@{p['versiya']} yayımlandı → {k.depo.ünvan}"
          + (f"/paket/{p['ad']}" if not n.get("url") else f" {n['url']}"))
    return 0


def _hesab(k: Kontekst, yol: str) -> int:
    ad = k.bayraqlar.get("ad") or input("İstifadəçi adı: ").strip()
    parol = k.bayraqlar.get("parol") or os.environ.get("ALQORHUB_PAROL") \
        or getpass.getpass("Parol: ")
    d = Depo(k.depo.ünvan)._json("POST", yol, {"ad": ad, "parol": parol},
                                 gözlə=(200, 201))
    nişan_yaz(k.depo.ünvan, d["nişan"])
    print(f"✓ {ad} olaraq daxil oldunuz ({k.depo.ünvan})")
    return 0


def ə_giriş(k: Kontekst) -> int:
    if k.bayraqlar.get("nişan"):
        nişan_yaz(k.depo.ünvan, k.bayraqlar["nişan"])
        print("✓ nişan saxlandı")
        return 0
    return _hesab(k, "giriş")


def ə_qeydiyyat(k: Kontekst) -> int:
    return _hesab(k, "qeydiyyat")


def ə_çıxış(k: Kontekst) -> int:
    nişan_yaz(k.depo.ünvan, None)
    print(f"✓ {k.depo.ünvan} hesabından çıxdınız")
    return 0


def ə_geri_çək(k: Kontekst) -> int:
    if not k.arq:
        raise PMXətası("ad@versiya lazımdır")
    ad, v = _ad_versiya(k.arq[0])
    if not v:
        raise PMXətası("versiya lazımdır: alqorpm geri-çək ad@1.0.1")
    geri = not k.bayraqlar.get("geri-al")
    k.depo._json("POST", f"paket/{ad}/{v}/geri-çək", {"geri": geri})
    print(f"✓ {ad}@{v} " + ("geri çəkildi" if geri else "bərpa olundu"))
    return 0


def ə_versiya(k: Kontekst) -> int:
    m = _manifest(k.kök)
    cari = Versiya.oxu(str((m.get("paket") or {}).get("versiya", "0.0.0")))
    növ = k.arq[0] if k.arq else ""
    if növ in ("patch", "yamaq"):
        yeni = Versiya(cari.əsas, cari.kiçik, cari.yamaq + 1)
    elif növ in ("minor", "kiçik"):
        yeni = Versiya(cari.əsas, cari.kiçik + 1, 0)
    elif növ in ("major", "əsas"):
        yeni = Versiya(cari.əsas + 1, 0, 0)
    elif növ:
        yeni = Versiya.oxu(növ)
    else:
        print(cari)
        return 0
    manifest_qoy(k.kök, "paket", "versiya", str(yeni))
    print(f"✓ {cari} → {yeni}")
    return 0


def ə_işlət(k: Kontekst) -> int:
    skriptlər = _manifest(k.kök).get("skriptlər") or {}
    if not k.arq:
        for a, v in skriptlər.items():
            print(f"  {a}: {v}")
        return 0
    əmr = skriptlər.get(k.arq[0])
    if not əmr:
        raise PMXətası(f"`{k.arq[0]}` skripti [skriptlər]-də yoxdur")
    alqor = Path(__file__).resolve().parent.parent / "alqorc.py"
    bin_ = Path(tempfile.mkdtemp(prefix="alqorpm-bin-"))
    for ad, alt in (("alqor", ""), ("alqorfmt", "format"),
                    ("alqorlint", "lint"), ("alqortest", "sına"),
                    ("alqorpm", "pm")):
        if os.name == "nt":
            (bin_ / f"{ad}.cmd").write_text(
                f'@"{sys.executable}" "{alqor}" {alt} %*\r\n',
                encoding="utf-8")
        else:
            f = bin_ / ad
            f.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{alqor}" '
                         f'{alt} "$@"\n', encoding="utf-8")
            f.chmod(0o755)
    mühit = {**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}",
             "PYTHONIOENCODING": "utf-8"}
    try:
        return subprocess.run(str(əmr) + "".join(
            f" {a}" for a in k.arq[1:]), shell=True, cwd=k.kök,
            env=mühit).returncode
    finally:
        shutil.rmtree(bin_, ignore_errors=True)


def ə_təmizlə(k: Kontekst) -> int:
    q = keş_qovluğu()
    ölçü = sum(f.stat().st_size for f in q.rglob("*") if f.is_file()) \
        if q.is_dir() else 0
    shutil.rmtree(q, ignore_errors=True)
    print(f"✓ keş təmizləndi ({ölçü / 1024:.0f} KB)")
    return 0


ƏMRLƏR = {
    "başlat": (ə_başlat, False), "əlavə": (ə_əlavə, True),
    "sil": (ə_sil, True), "yüklə": (ə_yüklə, True),
    "yenilə": (ə_yenilə, True), "siyahı": (ə_siyahı, True),
    "ağac": (ə_ağac, True), "axtar": (ə_axtar, False),
    "məlumat": (ə_məlumat, False), "yoxla": (ə_yoxla, True),
    "paketlə": (ə_paketlə, True), "yayımla": (ə_yayımla, True),
    "giriş": (ə_giriş, False), "qeydiyyat": (ə_qeydiyyat, False),
    "çıxış": (ə_çıxış, False), "geri-çək": (ə_geri_çək, False),
    "versiya": (ə_versiya, True), "işlət": (ə_işlət, True),
    "təmizlə": (ə_təmizlə, False),
}
SİNONİMLƏR = {"elave": "əlavə", "add": "əlavə", "install": "yüklə",
              "yukle": "yüklə", "i": "yüklə", "remove": "sil",
              "yenile": "yenilə", "update": "yenilə", "siyahi": "siyahı",
              "list": "siyahı", "agac": "ağac", "tree": "ağac",
              "search": "axtar", "info": "məlumat", "melumat": "məlumat",
              "audit": "yoxla", "pack": "paketlə", "paketle": "paketlə",
              "publish": "yayımla", "yayimla": "yayımla", "login": "giriş",
              "giris": "giriş", "register": "qeydiyyat", "logout": "çıxış",
              "cixis": "çıxış", "yank": "geri-çək", "init": "başlat",
              "baslat": "başlat", "run": "işlət", "islet": "işlət",
              "temizle": "təmizlə", "version": "versiya"}
_DƏYƏRLİ = {"depo", "yol", "qit", "teq", "ad", "parol", "nişan"}


def əsas(arqumentlər: list[str]) -> int:
    if not arqumentlər or arqumentlər[0] in ("kömək", "--kömək", "-k",
                                             "help"):
        print(__doc__.strip().split("\n\n", 1)[1])
        return 0 if arqumentlər else 3
    əmr = SİNONİMLƏR.get(arqumentlər[0], arqumentlər[0])
    if əmr not in ƏMRLƏR:
        print(f"✖ naməlum alqorpm əmri: {arqumentlər[0]}", file=sys.stderr)
        return 3
    bayraqlar: dict[str, Any] = {}
    arq: list[str] = []
    i = 1
    while i < len(arqumentlər):
        a = arqumentlər[i]
        if a.startswith("--"):
            ad, _, v = a[2:].partition("=")
            ad = {"nisan": "nişan", "inkisaf": "inkişaf", "dev": "inkişaf",
                  "sinaq": "sınaq", "dry-run": "sınaq"}.get(ad, ad)
            if ad in _DƏYƏRLİ and not v and i + 1 < len(arqumentlər):
                v = arqumentlər[i + 1]
                i += 1
            bayraqlar[ad] = v or True
        else:
            arq.append(a)
        i += 1
    f, kök_lazım = ƏMRLƏR[əmr]
    try:
        kök = _kök_tələb() if kök_lazım else (layihə_kökü(Path.cwd()) or
                                               Path.cwd())
        ünvan = depo_ünvanı(kök if (kök / MANİFEST).is_file() else None,
                            bayraqlar.get("depo"))
        depo = Depo(ünvan, nişan_al(ünvan))
        return f(Kontekst(kök, depo, arq, bayraqlar))
    except PMXətası as x:
        print(f"✖ {x.kod}  {x}", file=sys.stderr)
        return 2
    except VersiyaXətası as x:
        print(f"✖ ALQ-M007  {x}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130

