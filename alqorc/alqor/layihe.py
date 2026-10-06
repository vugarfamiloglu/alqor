"""
Alqor — layihə: `layihe.alqor` manifesti və `alqor yeni` şablonları.

Spesifikasiya § 8.8, § 13.2.

NİYƏ ÖZ PARSERİMİZ?
───────────────────
`layihe.alqor` TOML-a bənzəyir, amma TOML 1.0 deyil: açarlar
Azərbaycan hərfli ola bilər (`açarSözlər`, `sərt_boş`) və məntiqi
dəyərlər `doğru`/`yanlış` yazılır. Python-un `tomllib` modulu ikisini
də rədd edir. Bu modul həmin alt çoxluğu oxuyur:

    # şərh
    [bölmə]                 [bölmə.alt]
    açar = "mətn"           açar = 'mətn'
    açar = 42               açar = 3.14
    açar = doğru            açar = true
    açar = ["a", "b"]       (çoxsətirli də ola bilər)
    açar = { yol = "../x" } "dırnaqlı açar" = 1
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANİFEST = "layihe.alqor"


class ManifestXətası(Exception):
    def __init__(self, mesaj: str, sətir: int = 0):
        super().__init__(f"{MANİFEST}:{sətir}: {mesaj}" if sətir
                         else f"{MANİFEST}: {mesaj}")
        self.sətir = sətir


# ═══════════════════════════════════════════════════════════════════════
#  Manifest parseri
# ═══════════════════════════════════════════════════════════════════════

_AÇAR = re.compile(r'\s*("(?:[^"\\]|\\.)*"|[^\s=\[\]{},"\']+)\s*')


def oxu(mətn: str) -> dict[str, Any]:
    nəticə: dict[str, Any] = {}
    cari = nəticə
    sətirlər = mətn.splitlines()
    i = 0
    while i < len(sətirlər):
        n = i + 1
        sətir = _şərhsiz(sətirlər[i]).strip()
        i += 1
        if not sətir:
            continue
        if sətir.startswith("["):
            if not sətir.endswith("]") or sətir.startswith("[["):
                raise ManifestXətası(f"bölmə başlığı yanlışdır: {sətir}", n)
            yol = [_açar_adı(h.strip(), n)
                   for h in sətir[1:-1].split(".")]
            cari = nəticə
            for h in yol:
                cari = cari.setdefault(h, {})
                if not isinstance(cari, dict):
                    raise ManifestXətası(f"`{h}` bölmə deyil", n)
            continue
        if "=" not in sətir:
            raise ManifestXətası(f"`açar = dəyər` gözlənilirdi: {sətir}", n)
        açar_xam, dəyər_xam = sətir.split("=", 1)
        açar = _açar_adı(açar_xam.strip(), n)
        dəyər_xam = dəyər_xam.strip()
        # Çoxsətirli massiv: mötərizələr balanslaşana qədər oxu
        while _balanssızdır(dəyər_xam):
            if i >= len(sətirlər):
                raise ManifestXətası("bağlanmamış `[` və ya `{`", n)
            dəyər_xam += " " + _şərhsiz(sətirlər[i]).strip()
            i += 1
        dəyər, qalan = _dəyər(dəyər_xam, n)
        if qalan.strip():
            raise ManifestXətası(f"artıq simvollar: {qalan.strip()}", n)
        if açar in cari:
            raise ManifestXətası(f"`{açar}` təkrar təyin olunub", n)
        cari[açar] = dəyər
    return nəticə


def _şərhsiz(s: str) -> str:
    """Dırnaq xaricindəki `#`-dan sonrasını atır."""
    sitat = ""
    i = 0
    while i < len(s):
        c = s[i]
        if sitat:
            if c == "\\" and sitat == '"':
                i += 2
                continue
            if c == sitat:
                sitat = ""
        elif c in "\"'":
            sitat = c
        elif c == "#":
            return s[:i]
        i += 1
    return s


def _balanssızdır(s: str) -> bool:
    dərinlik = 0
    sitat = ""
    i = 0
    while i < len(s):
        c = s[i]
        if sitat:
            if c == "\\" and sitat == '"':
                i += 2
                continue
            if c == sitat:
                sitat = ""
        elif c in "\"'":
            sitat = c
        elif c in "[{":
            dərinlik += 1
        elif c in "]}":
            dərinlik -= 1
        i += 1
    return dərinlik > 0


def _açar_adı(s: str, n: int) -> str:
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return _mətn_aç(s[1:-1])
    if not s or any(c.isspace() for c in s) or any(c in s for c in "=[]{}"):
        raise ManifestXətası(f"açar adı yanlışdır: `{s}`", n)
    return s


def _mətn_aç(s: str) -> str:
    return (s.replace('\\"', '"').replace("\\n", "\n")
            .replace("\\t", "\t").replace("\\\\", "\\"))


DOĞRU = ("doğru", "dogru", "true")
YANLIŞ = ("yanlış", "yanlis", "false")


def _dəyər(s: str, n: int) -> tuple[Any, str]:
    s = s.lstrip()
    if not s:
        raise ManifestXətası("dəyər gözlənilirdi", n)
    c = s[0]
    if c == '"':
        m = re.match(r'"((?:[^"\\]|\\.)*)"', s)
        if not m:
            raise ManifestXətası("bağlanmamış mətn", n)
        return _mətn_aç(m.group(1)), s[m.end():]
    if c == "'":
        j = s.find("'", 1)
        if j < 0:
            raise ManifestXətası("bağlanmamış mətn", n)
        return s[1:j], s[j + 1:]
    if c == "[":
        siyahı: list[Any] = []
        qalan = s[1:].lstrip()
        while not qalan.startswith("]"):
            d, qalan = _dəyər(qalan, n)
            siyahı.append(d)
            qalan = qalan.lstrip()
            if qalan.startswith(","):
                qalan = qalan[1:].lstrip()
            elif not qalan.startswith("]"):
                raise ManifestXətası("massivdə `,` və ya `]` gözlənilirdi",
                                     n)
        return siyahı, qalan[1:]
    if c == "{":
        cədvəl: dict[str, Any] = {}
        qalan = s[1:].lstrip()
        while not qalan.startswith("}"):
            m = _AÇAR.match(qalan)
            if not m or "=" not in qalan:
                raise ManifestXətası("cədvəldə `açar = dəyər` gözlənilirdi",
                                     n)
            açar = _açar_adı(m.group(1), n)
            qalan = qalan[m.end():]
            if not qalan.startswith("="):
                raise ManifestXətası("cədvəldə `=` gözlənilirdi", n)
            d, qalan = _dəyər(qalan[1:], n)
            cədvəl[açar] = d
            qalan = qalan.lstrip()
            if qalan.startswith(","):
                qalan = qalan[1:].lstrip()
        return cədvəl, qalan[1:]
    m = re.match(r"[^\s,\]}]+", s)
    söz = m.group(0) if m else ""
    qalan = s[len(söz):]
    if söz in DOĞRU:
        return True, qalan
    if söz in YANLIŞ:
        return False, qalan
    try:
        return int(söz.replace("_", "")), qalan
    except ValueError:
        pass
    try:
        return float(söz.replace("_", "")), qalan
    except ValueError:
        pass
    raise ManifestXətası(f"dəyər tanınmadı: `{söz}` (mətn dırnaqda "
                         "yazılır)", n)


# ═══════════════════════════════════════════════════════════════════════
#  Layihə
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Layihə:
    kök: Path
    məlumat: dict[str, Any] = field(default_factory=dict)

    def _al(self, bölmə: str, açar: str, standart: Any) -> Any:
        b = self.məlumat.get(bölmə)
        if isinstance(b, dict) and açar in b:
            return b[açar]
        return standart

    @property
    def ad(self) -> str:
        return str(self._al("paket", "ad", self.kök.name))

    @property
    def versiya(self) -> str:
        return str(self._al("paket", "versiya", "0.1.0"))

    @property
    def təsvir(self) -> str:
        return str(self._al("paket", "təsvir", ""))

    @property
    def giriş(self) -> Path:
        return self.kök / str(self._al("qurma", "giriş",
                                       "mənbə/əsas.alqor"))

    @property
    def çıxış(self) -> Path:
        return self.kök / str(self._al("qurma", "çıxış", "qurma/"))

    @property
    def tip_rejimi(self) -> str:
        return str(self._al("tip", "rejim", "normal"))

    @property
    def sınaq_qovluğu(self) -> Path:
        for ad in ("sınaq", "sinaq", "test"):
            if (self.kök / ad).is_dir():
                return self.kök / ad
        return self.kök / "sınaq"

    @property
    def sənəd_qovluğu(self) -> Path:
        return self.kök / "sənəd"


def tap(başlanğıc: Path | str = ".") -> Layihə | None:
    """`layihe.alqor`-u cari və yuxarı qovluqlarda axtarır."""
    p = Path(başlanğıc).resolve()
    if p.is_file():
        p = p.parent
    for q in (p, *p.parents):
        m = q / MANİFEST
        if m.is_file():
            return Layihə(q, oxu(m.read_text(encoding="utf-8")))
    return None


# ═══════════════════════════════════════════════════════════════════════
#  `alqor yeni` — şablonlar
# ═══════════════════════════════════════════════════════════════════════

ŞABLONLAR = ("konsol", "veb", "desktop", "kitabxana")

_MANİFEST_ŞABLONU = '''\
[paket]
ad = "{ad}"
versiya = "0.1.0"
təsvir = "{təsvir}"
lisenziya = "MIT"

[qurma]
giriş = "mənbə/əsas.alqor"
çıxış = "qurma/"

[tip]
rejim = "normal"                   # sərbəst | normal | sərt

[format]
girinti = 4
ascii_düzəlt = doğru
'''

_ƏSAS = {
    "konsol": '''\
// {ad} — konsol proqramı
//
//   alqor işlət                 proqramı işə salır
//   alqor sına                  sınaqları işlədir

gətir konsol

/// Adı verilən insanı salamlayır.
///
/// ```alqor
/// yaz(salamla("Aysel"))     // Salam, Aysel!
/// ```
ixrac et funksiya salamla(ad: mətn) -> mətn
    qaytar "Salam, {{ad}}!"
son

funksiya əsas()
    dəyişən ad = konsol.soruş("Adınız: ", standart: "dünya")
    yaz(konsol.yaşıl(salamla(ad)))
son
''',
    "veb": '''\
// {ad} — veb server
//
//   alqor işlət                 http://127.0.0.1:8080
//   alqor sına                  sınaqları işlədir

gətir veb
gətir vidjet

/// Serverin bütün marşrutları. Sınaqlar da bunu çağırır.
ixrac et funksiya serverQur() -> istənilən
    dəyişən s = yeni veb.Server()
    s.ara(veb.təhlükəsizlikBaşlıqları())

    s.al("/", (sorğu) => veb.html(vidjet.səhifə(başlıq: "{ad}", məzmun: [
        vidjet.başlıq(mətn: "{ad}", altMətn: "Alqor ilə yazılıb"),
        vidjet.əlaqə(mətn: "API nümunəsi", ünvan: "/api/salam/dünya")
    ])))

    s.al("/api/salam/:ad", (sorğu) =>
        veb.json({{"salam": sorğu.parametr("ad")}}))

    qaytar s
son

funksiya əsas()
    dəyişən s = serverQur()
    s.ara(veb.jurnal())
    s.dinlə(8080)
son
''',
    "desktop": '''\
// {ad} — desktop tətbiqi
//
//   alqor işlət                 pəncərəni açır
//   alqor sına                  sınaqları pəncərə açmadan işlədir

gətir pəncərə
gətir vidjet

ixrac et komponent Tətbiq
    vəziyyət say: tam = 0

    göstər()
        qaytar vidjet.sütun(boşluq: 16, məzmun: [
            vidjet.başlıq(mətn: "{ad}"),
            vidjet.statistika(etiket: "Basılma", dəyər: "{{özü.say}}"),
            vidjet.sətir(məzmun: [
                vidjet.düymə(mətn: "Artır", klik: () => özü.say += 1),
                vidjet.düymə(mətn: "Sıfırla", növ: "ikinci",
                             klik: () => özü.say = 0)
            ])
        ])
    son
son

/// Pəncərəni qurur — sınaqlar da bunu işlədir.
ixrac et funksiya pəncərəQur() -> istənilən
    dəyişən p = yeni pəncərə.Pəncərə("{ad}", 420, 320)
    p.məzmun(<Tətbiq />)
    qaytar p
son

funksiya əsas()
    dəyişən p = pəncərəQur()
    p.mərkəzə().göstər()
    pəncərə.işlət()
son
''',
    "kitabxana": '''\
//! {ad} — Alqor kitabxanası.
//!
//! Başqa layihələr `gətir {ad}` ilə istifadə edir.

/// İki ədədin cəmi.
///
/// ```alqor
/// yaz(topla(2, 3))     // 5
/// ```
ixrac et funksiya topla(a: tam, b: tam) -> tam
    qaytar a + b
son

/// Siyahının orta qiyməti; boş siyahıda `boş`.
ixrac et funksiya orta(s: siyahı[onluq]) -> onluq?
    əgər uzunluq(s) == 0 onda
        qaytar boş
    son
    qaytar s.cəm() / uzunluq(s)
son
''',
}

_SINAQ = {
    "konsol": '''\
gətir test
gətir "../mənbə/əsas.alqor" kimi proqram

@sınaq("salamla adı yerləşdirir")
funksiya salamlama()
    test.bərabər(proqram.salamla("Aysel"), "Salam, Aysel!")
son
''',
    "veb": '''\
gətir test
gətir veb
gətir "../mənbə/əsas.alqor" kimi proqram

@sınaq("ana səhifə açılır")
funksiya anaSəhifə()
    dəyişən c = veb.sınaq.server(proqram.serverQur()).al("/")
    test.bərabər(c.vəziyyət(), 200)
son

@sınaq("API salamlayır")
funksiya apiSalam()
    dəyişən c = veb.sınaq.server(proqram.serverQur()).al("/api/salam/Aysel")
    test.bərabər(c.json()["salam"], "Aysel")
son
''',
    "desktop": '''\
gətir test
gətir pəncərə
gətir "../mənbə/əsas.alqor" kimi proqram

@sınaq("düymə sayğacı artırır")
funksiya sayğac()
    dəyişən s = pəncərə.sınaq.aç(proqram.pəncərəQur())
    s.klik("Artır")
    s.klik("Artır")
    test.doğru(s.ehtiva(">2<"))
    s.klik("Sıfırla")
    test.doğru(s.ehtiva(">0<"))
son
''',
    "kitabxana": '''\
gətir test
gətir "../mənbə/əsas.alqor" kimi proqram

@sınaq
funksiya toplama()
    test.bərabər(proqram.topla(2, 3), 5)
son

@sınaq("boş siyahının ortası yoxdur")
funksiya boşOrta()
    test.boş(proqram.orta([]))
son

@sınaqVerilənlər([[[1.0, 2.0, 3.0], 2.0], [[5.0], 5.0]])
funksiya ortaQiymət(s: siyahı[onluq], gözlənilən: onluq)
    test.bərabər(proqram.orta(s), gözlənilən)
son
''',
}

_GITIGNORE = "qurma/\nsənəd/\n__pycache__/\n"

_README = '''\
# {ad}

{təsvir}

```bash
alqor işlət        # işə sal
alqor sına         # sınaqlar
alqor format .     # kodu format et
alqor sənəd        # sənəd/ qovluğuna API sənədi
alqor qur          # qurma/{ad}.pyz — tək fayllı paket
```
'''

_TƏSVİRLƏR = {
    "konsol": "Konsol proqramı",
    "veb": "Veb server",
    "desktop": "Desktop tətbiqi",
    "kitabxana": "Alqor kitabxanası",
}


def yarat(qovluq: Path, ad: str, şablon: str = "konsol") -> list[Path]:
    """Yeni layihə yaradır. Yaradılan faylların siyahısını qaytarır."""
    if şablon not in ŞABLONLAR:
        raise ValueError(f"`{şablon}` şablonu yoxdur. İcazəli: "
                         f"{', '.join(ŞABLONLAR)}")
    if not ad or any(c in ad for c in '/\\:*?"<>|') or ad in (".", ".."):
        raise ValueError(f"layihə adı yanlışdır: `{ad}`")
    if qovluq.exists() and any(qovluq.iterdir()):
        raise ValueError(f"`{qovluq}` qovluğu boş deyil")
    təsvir = _TƏSVİRLƏR[şablon]
    fayllar = {
        MANİFEST: _MANİFEST_ŞABLONU.format(ad=ad, təsvir=təsvir),
        "mənbə/əsas.alqor": _ƏSAS[şablon].format(ad=ad),
        "sınaq/əsas_sınaq.alqor": _SINAQ[şablon],
        ".gitignore": _GITIGNORE,
        "README.md": _README.format(ad=ad, təsvir=təsvir),
    }
    yaradılan: list[Path] = []
    for nisbi, məzmun in fayllar.items():
        yol = qovluq / nisbi
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(məzmun, encoding="utf-8")
        yaradılan.append(yol)
    return yaradılan
