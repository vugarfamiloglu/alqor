#!/usr/bin/env python3
"""
Alqor — əmr sətri aləti (etalon implementasiya).

    python alqorc.py tokenlər <fayl>     tokenləri göstər
    python alqorc.py yoxla <fayl>        xətaları yoxla
    python alqorc.py hərf <mətn>         az-AZ hərf çevrilməsi
    python alqorc.py sırala <söz>...     Azərbaycan əlifba sırası
    python alqorc.py versiya
    python alqorc.py kömək
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

# ── KRİTİK: Windows konsolu standart olaraq cp1251-dir və Azərbaycan
#    hərflərini çap edə bilmir. Bu olmadan dil öz xəta mesajını göstərə bilmir.
for _axın in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _axın.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).parent))

from alqor import VERSIYA, elifba                      # noqa: E402
from alqor.lekser import Lekser, faylı_leksə, leksə    # noqa: E402
from alqor.menbe import Mənbə                          # noqa: E402
from alqor.token import KodParçası, MətnParçası, Növ    # noqa: E402
from alqor.xeta import XətaToplayıcı                   # noqa: E402

PROQRAM = "alqor"


# ═══════════════════════════════════════════════════════════════════════
#  Əmrlər
# ═══════════════════════════════════════════════════════════════════════

def əmr_tokenlər(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        çap_xəta("`tokenlər` əmri üçün fayl adı lazımdır")
        return 3
    yol = arqumentlər[0]
    ətraflı = "--ətraflı" in arqumentlər or "-e" in arqumentlər

    if yol == "-":
        tokenlər, x = leksə(sys.stdin.read(), "<stdin>")
    else:
        tokenlər, x = faylı_leksə(yol)

    if not tokenlər and not x.uğurludur():
        x.çap()
        return 2

    print(f"  {'YER':>9}  {'NÖV':<11} DƏYƏR")
    print("  " + "─" * 58)
    for t in tokenlər:
        _token_çap(t, ətraflı, girinti=2)
    print("  " + "─" * 58)
    print(f"  {len(tokenlər)} token")
    print()
    sys.stdout.flush()          # stderr ilə qarışmasın

    if x.siyahı:
        x.çap()
    return 0 if x.uğurludur() else 2


def _token_çap(t, ətraflı: bool, girinti: int) -> None:
    boş = " " * girinti
    if t.növ is Növ.SETIR_SONU:
        print(f"{boş}{'':>9}  ⏎ sətir sonu")
        return
    if t.növ is Növ.FAYL_SONU:
        print(f"{boş}{'':>9}  ⊣ fayl sonu")
        return

    yer = f"{t.yer.sətir}:{t.yer.sütun}"
    əlavə = ""
    if t.ascii_idi:
        əlavə = f"   ← ASCII: {t.xam!r}"
    if t.çoxsətirli:
        əlavə += "   (çoxsətirli)"

    print(f"{boş}{yer:>9}  {t.növ.name:<11} {t.dəyər!r}{əlavə}")

    if t.parçalar and any(isinstance(p, KodParçası) for p in t.parçalar):
        for p in t.parçalar:
            if isinstance(p, MətnParçası):
                print(f"{boş}{'':>9}    ├ mətn   {p.dəyər!r}")
            else:
                f = f"  format={p.format!r}" if p.format else ""
                print(f"{boş}{'':>9}    ├ kod{f}")
                for alt in p.tokenlər:
                    _token_çap(alt, ətraflı, girinti + 8)


def _rejim_tap(arqumentlər: list[str]) -> str:
    """
    Tip rejimi: əmr sətri → `layihe.alq` → standart (`normal`).
    """
    for bayraq in ("--rejim", "--rejim=", "-r"):
        for i, a in enumerate(arqumentlər):
            if a == bayraq and i + 1 < len(arqumentlər):
                return arqumentlər[i + 1]
            if a.startswith("--rejim="):
                return a.split("=", 1)[1]

    layihə = Path("layihe.alq")
    if not layihə.exists():
        layihə = Path("..") / "layihe.alq"
    if layihə.exists():
        try:
            mətn = layihə.read_text(encoding="utf-8")
        except OSError:
            return "normal"
        tip_bölməsi = False
        for sətir in mətn.splitlines():
            s = sətir.strip()
            if s.startswith("["):
                tip_bölməsi = s == "[tip]"
                continue
            if tip_bölməsi and s.startswith("rejim"):
                hissə = s.split("=", 1)
                if len(hissə) == 2:
                    return hissə[1].strip().strip('"\'')
    return "normal"


def _tipləri_yoxla(ağac, mənbə, rejim: str):
    """Tip yoxlayıcısını işlədir, diaqnostika toplayıcısını qaytarır."""
    from alqor.tipyoxlayici import tipləri_yoxla
    t = XətaToplayıcı()
    try:
        tipləri_yoxla(ağac, t, rejim)
    except Exception as x:                      # noqa: BLE001
        # Tip yoxlayıcısının öz xətası proqramı dayandırmamalıdır
        print(f"⚠ tip yoxlayıcısı daxili xəta verdi: "
              f"{type(x).__name__}: {x}", file=sys.stderr)
    return t


def əmr_tip(arqumentlər: list[str]) -> int:
    """Yalnız tip yoxlaması."""
    from alqor.lekser import Lekser
    from alqor.parser import Parser

    if not arqumentlər:
        çap_xəta("`tip` əmri üçün fayl adı lazımdır")
        return 3

    rejim = _rejim_tap(arqumentlər)
    yollar = _faylları_topla(arqumentlər)
    if not yollar:
        çap_xəta("yoxlanacaq fayl tapılmadı")
        return 4

    ümumi_xəta = ümumi_xəbərdarlıq = 0
    for yol in yollar:
        x = XətaToplayıcı()
        s = Mənbə.fayldan(yol, x)
        if s is None:
            x.çap()
            ümumi_xəta += 1
            continue
        ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        if not x.uğurludur():
            print(f"── {yol} " + "─" * max(0, 52 - len(yol)))
            x.çap()
            ümumi_xəta += 1
            continue
        t = _tipləri_yoxla(ağac, s, rejim)
        if t.siyahı:
            print(f"── {yol} " + "─" * max(0, 52 - len(yol)))
            t.çap()
            print()
        ümumi_xəta += len(t.xətalar)
        ümumi_xəbərdarlıq += len(t.xəbərdarlıqlar)

    print(f"Rejim: {rejim}  ·  {len(yollar)} fayl")
    if ümumi_xəta == 0:
        print(f"✓ tip xətası yoxdur"
              + (f" ({ümumi_xəbərdarlıq} xəbərdarlıq)"
                 if ümumi_xəbərdarlıq else ""))
        return 0
    print(f"✖ {ümumi_xəta} tip xətası, {ümumi_xəbərdarlıq} xəbərdarlıq")
    return 2


#  Dəyər qəbul edən bayraqlar — onların dəyəri fayl adı sayılmamalıdır
DƏYƏRLİ_BAYRAQLAR = ("--rejim", "-r", "--hədəf", "--çıxış", "--format")


def _faylları_topla(arqumentlər: list[str]) -> list[str]:
    yollar: list[str] = []
    atla = False
    for a in arqumentlər:
        if atla:
            atla = False
            continue
        if a in DƏYƏRLİ_BAYRAQLAR:
            atla = True
            continue
        if a.startswith("-"):
            continue
        p = Path(a)
        if p.is_dir():
            yollar.extend(str(q) for q in sorted(p.rglob("*.alq")))
            yollar.extend(str(q) for q in sorted(p.rglob("*.alqor")))
        else:
            yollar.append(a)
    return yollar


def əmr_işlət(arqumentlər: list[str]) -> int:
    """Proqramı leksə → ayır → icra et."""
    from alqor.deyerler import AlqorXəta
    from alqor.icraci import İcraçı
    from alqor.lekser import Lekser
    from alqor.parser import Parser

    # `--`-dan sonrakılar proqramındır — alətin bayraqları deyil
    if "--" in arqumentlər:
        k = arqumentlər.index("--")
        öz, proqram_arqumentləri = arqumentlər[:k], arqumentlər[k + 1:]
    else:
        öz, proqram_arqumentləri = arqumentlər, []

    fayllar = [a for a in öz if not a.startswith("--") or a == "-"]
    if fayllar:
        yol = fayllar[0]
    else:
        # Fayl verilməyib — layihənin giriş nöqtəsi (`layihe.alq`)
        from alqor.layihe import ManifestXətası, tap
        try:
            layihə = tap(".")
        except ManifestXətası as x:
            çap_xəta(str(x))
            return 3
        if layihə is None:
            çap_xəta("`işlət` əmri üçün fayl adı lazımdır (və ya "
                     "`layihe.alq` olan qovluqda işlədin)")
            return 3
        yol = str(layihə.giriş)
    arqumentlər = öz

    x = XətaToplayıcı()
    if yol == "-":
        s = Mənbə.mətndən(sys.stdin.read(), "<stdin>", x)
    else:
        s = Mənbə.fayldan(yol, x)
    if s is None:
        x.çap()
        return 4

    tokenlər = Lekser(s, x).leksə()
    ağac = Parser(tokenlər, s, x).ayır()

    if not x.uğurludur():
        x.çap()
        return 2
    if x.xəbərdarlıqlar:
        x.çap()

    # `--js`: JavaScript-ə kompilyasiya edib node ilə işlət
    if "--js" in arqumentlər:
        return _js_işlət(ağac, yol, proqram_arqumentləri)

    # Tədrici tiplər: `işlət` standart olaraq tip yoxlamır.
    # `--tip` bayrağı ilə yoxlanır, xəta varsa icra dayandırılır.
    if "--tip" in arqumentlər or "--tip-yoxla" in arqumentlər:
        t = _tipləri_yoxla(ağac, s, _rejim_tap(arqumentlər))
        if t.siyahı:
            t.çap()
        if not t.uğurludur():
            return 2

    sys.stdout.flush()
    icraçı = İcraçı()
    if yol != "-":
        icraçı.əsas_qovluq = Path(yol).resolve().parent
    try:
        return icraçı.işlət(ağac, proqram_arqumentləri)
    except AlqorXəta as xəta:
        _icra_xətası_çap(xəta, s)
        return 1
    except RecursionError:
        print("\n✖ StekDaşmaXətası: çağırış dərinliyi həddi aşıldı",
              file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⊣ dayandırıldı", file=sys.stderr)
        return 130


def _js_işlət(ağac, yol: str, proqram_arqumentləri: list[str]) -> int:
    import subprocess
    import tempfile
    from alqor.js import KompilyasiyaXətası, node_faylı
    from alqor.js.muqayise import node_tap
    node = node_tap()
    if node is None:
        çap_xəta("`--js` üçün Node.js lazımdır (https://nodejs.org) — "
                 "və ya ALQOR_NODE mühit dəyişənində yolunu göstərin")
        return 4
    try:
        js = node_faylı(ağac, Path(yol).resolve() if yol != "-" else None)
    except KompilyasiyaXətası as x:
        çap_xəta(f"JS kompilyasiyası: {x}")
        return 2
    with tempfile.TemporaryDirectory() as q:
        f = Path(q) / "proqram.js"
        f.write_text(js, encoding="utf-8")
        sys.stdout.flush()
        return subprocess.call([node, "--stack-size=4000", str(f),
                                *proqram_arqumentləri])


def _alqor_windows(arqumentlər: list[str]) -> int:
    """`qur --alqor [çıxış] [--platforma windows|linux|macos] [--arx …]`
    — Alqor-un öz quraşdırıcısı."""
    from alqor import windows_paylama
    platforma = _seçim(arqumentlər, "--platforma") or "windows"
    arx = _seçim(arqumentlər, "--arx") or "x86_64"
    seçim_dəyərləri = {platforma, arx}
    sərbəst = [a for a in arqumentlər if not a.startswith("-")
               and a not in seçim_dəyərləri]
    çıxış = Path(sərbəst[0]) if sərbəst else Path("qurma")
    if platforma in ("linux", "macos"):
        from alqor import unix_paylama
        try:
            n = unix_paylama.qur(Path(__file__).resolve().parent,
                                 çıxış.resolve(), platforma, arx)
        except (OSError, RuntimeError, ValueError) as x:
            çap_xəta(f"{platforma} paylaması qurulmadı: {x}")
            return 4
        print(f"✓ Alqor {platforma} ({arx}) paylaması:")
        for p in n:
            print(f"  {p}")
        return 0
    if platforma != "windows":
        çap_xəta("`--platforma`: windows | linux | macos")
        return 3
    python_zip = os.environ.get("ALQOR_PYTHON_EMBED")
    try:
        n = windows_paylama.qur(
            Path(__file__).resolve().parent, çıxış.resolve(),
            python_zip=Path(python_zip) if python_zip else None)
    except (OSError, RuntimeError) as x:
        çap_xəta(f"Windows quraşdırıcısı qurulmadı: {x}")
        return 4
    print("✓ Alqor Windows paylaması:")
    for p in n:
        print(f"  {p}")
    if not any(p.suffix == ".exe" for p in n):
        print("  .exe üçün Inno Setup lazımdır (https://jrsoftware.org/isdl.php):"
              f"\n    iscc {n[-1].name}")
    return 0


def _js_qur(arqumentlər: list[str]) -> int:
    """`qur --hədəf js|veb [fayl] [--çıxış yol]`"""
    from alqor.js import KompilyasiyaXətası, node_faylı, veb_səhifəsi
    from alqor.lekser import Lekser
    from alqor.parser import Parser
    i = arqumentlər.index("--hədəf")
    hədəf = arqumentlər[i + 1] if i + 1 < len(arqumentlər) else ""
    if hədəf not in ("js", "veb", "node"):
        çap_xəta("`--hədəf` dəyəri: js | veb")
        return 3
    çıxış = None
    if "--çıxış" in arqumentlər:
        j = arqumentlər.index("--çıxış")
        çıxış = Path(arqumentlər[j + 1]) if j + 1 < len(arqumentlər) else None
    fayllar = _faylları_topla(arqumentlər)
    başlıq = None
    if fayllar:
        yol = Path(fayllar[0])
    else:
        layihə = _layihə(".")
        if layihə is None:
            çap_xəta("fayl adı verin və ya `layihe.alq` olan qovluqda "
                     "işlədin: alqor qur --hədəf js proqram.alq")
            return 3
        yol = Path(layihə.giriş)
        başlıq = getattr(layihə, "ad", None)
    x = XətaToplayıcı()
    s = Mənbə.fayldan(yol, x)
    if s is None:
        x.çap()
        return 4
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        x.çap()
        return 2
    try:
        if hədəf == "veb":
            mətn = veb_səhifəsi(ağac, başlıq or yol.stem, yol.resolve())
            çıxış = çıxış or Path("qurma") / "veb" / "index.html"
        else:
            mətn = node_faylı(ağac, yol.resolve())
            çıxış = çıxış or Path("qurma") / f"{yol.stem}.js"
    except KompilyasiyaXətası as e:
        çap_xəta(f"JS kompilyasiyası: {e}")
        return 2
    çıxış.parent.mkdir(parents=True, exist_ok=True)
    çıxış.write_text(mətn, encoding="utf-8")
    print(f"✓ {çıxış}  ({len(mətn.encode()) / 1024:.0f} KB)")
    if hədəf == "veb":
        print("  Brauzerdə açın: index.html")
    else:
        print(f"  İşlətmək: node {çıxış}")
    return 0


def _icra_xətası_çap(xəta, mənbə) -> None:
    from alqor.xeta import Diaqnostika, Səviyyə
    sys.stdout.flush()
    d = Diaqnostika(
        xəta.kod or "ALQ-R000",
        f"{xəta.tip}: {xəta.mesaj}",
        xəta.yer,
        Səviyyə.XETA,
        "burada baş verdi" if xəta.yer else "",
    )
    print(d.formatla(), file=sys.stderr)


def əmr_yoxla(arqumentlər: list[str]) -> int:
    from alqor.parser import Parser
    from alqor.lekser import Lekser
    if not arqumentlər:
        çap_xəta("`yoxla` əmri üçün fayl adı lazımdır")
        return 3

    ümumi_xəta = 0
    yollar = _faylları_topla(arqumentlər)

    if not yollar:
        çap_xəta("yoxlanacaq fayl tapılmadı")
        return 4

    rejim = _rejim_tap(arqumentlər)
    for yol in yollar:
        x = XətaToplayıcı()
        s = Mənbə.fayldan(yol, x)
        ağac = None
        if s is not None:
            ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
        # Leksik/sintaktik xəta yoxdursa, tipləri də yoxlayırıq
        if ağac is not None and x.uğurludur():
            for d in _tipləri_yoxla(ağac, s, rejim).siyahı:
                x.əlavə(d)
        if x.siyahı:
            print(f"── {yol} " + "─" * max(0, 56 - len(yol)))
            x.çap()
            print()
        if not x.uğurludur():
            ümumi_xəta += 1

    toplam = len(yollar)
    if ümumi_xəta == 0:
        print(f"✓ {toplam} fayl yoxlanıldı, xəta yoxdur")
        return 0
    print(f"✖ {toplam} fayldan {ümumi_xəta}-də xəta var")
    return 2


def əmr_format(arqumentlər: list[str]) -> int:
    """
    `alqorfmt` — spesifikasiya § 13.3.

        format <fayl|qovluq>...      faylları yerində format edir
        --yoxla                      dəyişmir; lazımdırsa kod 1 (CI)
        --fərq                       dəyişmir; fərqi göstərir
        --ascii-saxla                ASCII açar sözlərə toxunmur
        --homoqlif-düzəlt            gizli oxşar simvolları düzəldir
    """
    from alqor.alqorfmt import FormatXətası, faylları_tap, formatla

    bayraqlar = {a for a in arqumentlər if a.startswith("--")}
    naməlum = bayraqlar - {"--yoxla", "--fərq", "--ferq", "--ascii-saxla",
                           "--ascii-düzəlt", "--ascii-duzelt",
                           "--homoqlif-düzəlt", "--homoqlif-duzelt"}
    if naməlum:
        çap_xəta(f"naməlum seçim: {', '.join(sorted(naməlum))}")
        return 3
    yollar_arq = [a for a in arqumentlər if not a.startswith("--")]
    if not yollar_arq:
        çap_xəta("`format` əmri üçün fayl və ya qovluq lazımdır "
                 "(cari qovluq üçün: .)")
        return 3
    fayllar = faylları_tap(yollar_arq)
    if not fayllar:
        çap_xəta("format ediləcək .alq faylı tapılmadı")
        return 4

    yoxla = "--yoxla" in bayraqlar
    fərq = bool(bayraqlar & {"--fərq", "--ferq"})
    ascii_düzəlt = "--ascii-saxla" not in bayraqlar
    homoqlif = bool(bayraqlar & {"--homoqlif-düzəlt", "--homoqlif-duzelt"})

    dəyişən = xətalı = 0
    for yol in fayllar:
        try:
            köhnə = yol.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as x:
            print(f"✖ {yol}: oxunmadı ({x})", file=sys.stderr)
            xətalı += 1
            continue
        try:
            n = formatla(köhnə, yol.name, ascii_düzəlt=ascii_düzəlt,
                         homoqlif_düzəlt=homoqlif)
        except FormatXətası as x:
            print(f"✖ {yol}: {x}", file=sys.stderr)
            xətalı += 1
            continue
        if not n.dəyişdi:
            continue
        dəyişən += 1
        if fərq:
            print(n.fərq(köhnə, str(yol)), end="")
        elif yoxla:
            print(f"• {yol}: format lazımdır")
        else:
            yol.write_bytes(n.mətn.encode("utf-8"))
            əlavə = (f" ({n.ascii_düzəlişləri} ASCII açar söz)"
                     if n.ascii_düzəlişləri else "")
            print(f"✓ {yol}{əlavə}")

    toplam = len(fayllar)
    if yoxla or fərq:
        if dəyişən:
            print(f"{toplam} fayldan {dəyişən}-i format edilməlidir")
        else:
            print(f"✓ {toplam} fayl artıq formatdadır")
    else:
        print(f"{toplam} fayl yoxlanıldı, {dəyişən} format edildi")
    if xətalı:
        return 2
    return 1 if (yoxla and dəyişən) else 0


# ═══════════════════════════════════════════════════════════════════════
#  Layihə əmrləri: yeni, sına, sənəd, qur, təmizlə
# ═══════════════════════════════════════════════════════════════════════

def _seçim(arqumentlər: list[str], *adlar: str) -> str | None:
    """`--ad dəyər` və ya `--ad=dəyər`."""
    for i, a in enumerate(arqumentlər):
        for ad in adlar:
            if a == ad and i + 1 < len(arqumentlər):
                return arqumentlər[i + 1]
            if a.startswith(ad + "="):
                return a.split("=", 1)[1]
    return None


def _mövqeli(arqumentlər: list[str], *dəyərli: str) -> list[str]:
    """Bayraq olmayan arqumentlər (`--ad dəyər` cütü atlanır)."""
    nəticə: list[str] = []
    atla = False
    for a in arqumentlər:
        if atla:
            atla = False
            continue
        if a in dəyərli:
            atla = True
            continue
        if a.startswith("--"):
            continue
        nəticə.append(a)
    return nəticə


def _layihə(qovluq: str = "."):
    from alqor.layihe import ManifestXətası, tap
    try:
        return tap(qovluq)
    except ManifestXətası as x:
        çap_xəta(str(x))
        return None


def əmr_yeni(arqumentlər: list[str]) -> int:
    """`yeni <ad> [--şablon konsol|veb|desktop|kitabxana]`"""
    from alqor.layihe import ŞABLONLAR, yarat
    adlar = _mövqeli(arqumentlər, "--şablon", "--sablon")
    if not adlar:
        çap_xəta("layihə adı lazımdır: alqor yeni <ad> "
                 f"[--şablon {'|'.join(ŞABLONLAR)}]")
        return 3
    ad = adlar[0]
    şablon = _seçim(arqumentlər, "--şablon", "--sablon") or "konsol"
    qovluq = Path(ad)
    try:
        fayllar = yarat(qovluq, qovluq.name, şablon)
    except ValueError as x:
        çap_xəta(str(x))
        return 3
    print(f"✓ `{qovluq.name}` layihəsi yaradıldı ({şablon})")
    for f in fayllar:
        print(f"    {f.relative_to(qovluq)}")
    print(f"""
Növbəti addımlar:
    cd {qovluq}
    alqor işlət        # işə sal
    alqor sına         # sınaqlar""")
    return 0


def əmr_sına(arqumentlər: list[str]) -> int:
    """
    `sına [fayl|qovluq]... [--filtr söz] [--sənəd] [--ətraflı]`

    Yol verilməsə layihənin `sınaq/` qovluğu. `--sənəd` sənəd
    şərhlərindəki nümunələri də işlədir.
    """
    import time as _t
    from alqor import sinaqci as S

    yollar = [Path(a) for a in _mövqeli(arqumentlər, "--filtr")]
    filtr = _seçim(arqumentlər, "--filtr") or ""
    layihə = _layihə(str(yollar[0]) if yollar else ".")
    kök = layihə.kök if layihə else Path.cwd()
    if not yollar:
        yollar = [layihə.sınaq_qovluğu if layihə else Path(".")]
    fayllar = S.sınaq_faylları(yollar)

    print(f"\n  Alqor Sınaq {VERSIYA}\n")
    baş = _t.perf_counter()
    nəticələr = [S.faylı_sına(f, filtr) for f in fayllar]
    if "--sənəd" in arqumentlər or "--sened" in arqumentlər:
        mənbələr = ([layihə.giriş.parent] if layihə
                    else [Path(".")])
        from alqor.alqorfmt import faylları_tap
        for f in faylları_tap([str(m) for m in mənbələr]):
            n = S.sənədi_sına(f)
            if n.nəticələr:
                nəticələr.append(n)
    sətirlər, say = S.hesabat(nəticələr, kök.resolve(),
                              "--ətraflı" in arqumentlər)
    for sətir in sətirlər:
        print(sətir)
    müddət = _t.perf_counter() - baş
    if not fayllar and len(nəticələr) == 0:
        print("  Sınaq faylı tapılmadı (`sınaq/` qovluğu və ya "
              "`*_sınaq.alq`).")
        return 4
    xətalı = say["uğursuz"] + say["xəta"]
    print(f"  Nəticə: {say['uğurlu']} uğurlu, {say['uğursuz']} uğursuz, "
          f"{say['xəta']} xəta, {say['atlanmış']} atlanmış"
          f"      {müddət:.2f}s")
    return 1 if xətalı else 0


def əmr_sənəd(arqumentlər: list[str]) -> int:
    """`sənəd [fayl|qovluq]... [--format html|markdown] [--çıxış q]`"""
    from alqor import senedci
    from alqor.alqorfmt import faylları_tap

    yollar = _mövqeli(arqumentlər, "--format", "--çıxış", "--cixis")
    format_ = _seçim(arqumentlər, "--format") or "html"
    if format_ not in ("html", "markdown", "md"):
        çap_xəta("format `html` və ya `markdown` olmalıdır")
        return 3
    layihə = _layihə(yollar[0] if yollar else ".")
    if not yollar:
        if layihə is None:
            çap_xəta("fayl/qovluq verin və ya `layihe.alq` olan "
                     "qovluqda işlədin")
            return 3
        yollar = [str(layihə.giriş.parent)]
    çıxış = Path(_seçim(arqumentlər, "--çıxış", "--cixis")
                 or (layihə.sənəd_qovluğu if layihə else "sənəd"))
    başlıq = layihə.ad if layihə else Path(yollar[0]).resolve().stem

    sənədlər = []
    for f in faylları_tap(yollar):
        try:
            sənədlər.append(senedci.fayl_sənədi(f))
        except ValueError as x:
            print(f"✖ {x}", file=sys.stderr)
            return 2
    if not sənədlər:
        çap_xəta("sənədləşdiriləcək .alq faylı tapılmadı")
        return 4
    çıxış.mkdir(parents=True, exist_ok=True)
    if format_ == "html":
        hədəf = çıxış / "indeks.html"
        hədəf.write_text(senedci.html_sənəd(sənədlər, başlıq),
                         encoding="utf-8")
    else:
        hədəf = çıxış / "API.md"
        hədəf.write_text(senedci.markdown(sənədlər, başlıq),
                         encoding="utf-8")
    elementlər = sum(len(s.elementlər) for s in sənədlər)
    print(f"✓ {hədəf}  ({len(sənədlər)} fayl, {elementlər} element)")
    return 0


def _platformalar(arqumentlər: list[str]) -> tuple[str, ...] | None:
    from alqor.qurasdirici import PLATFORMALAR
    for i, a in enumerate(arqumentlər):
        if a.startswith("--platforma"):
            d = a.split("=", 1)[1] if "=" in a else (
                arqumentlər[i + 1] if i + 1 < len(arqumentlər) else "")
            p = tuple(x.strip() for x in d.split(",") if x.strip())
            pis = [x for x in p if x not in PLATFORMALAR]
            if pis or not p:
                çap_xəta(f"platforma: {', '.join(PLATFORMALAR)} "
                         f"(verilən: {d!r})")
                return None
            return p
    return PLATFORMALAR


def _formatlar(arqumentlər: list[str]) -> tuple[str, ...] | None | bool:
    """`--format deb,rpm,appimage,windows,app,dmg` → tuple; yoxdursa None;
    yanlışdırsa False."""
    from alqor.qurasdirici import FORMATLAR
    hamısı = {f for v in FORMATLAR.values() for f in v}
    for i, a in enumerate(arqumentlər):
        if a.startswith("--format"):
            d = a.split("=", 1)[1] if "=" in a else (
                arqumentlər[i + 1] if i + 1 < len(arqumentlər) else "")
            f = tuple(x.strip().lower() for x in d.split(",") if x.strip())
            if not f or any(x not in hamısı for x in f):
                çap_xəta(f"format: {', '.join(sorted(hamısı))} "
                         f"(verilən: {d!r})")
                return False
            return f
    return None


def _xəbərdar(mesaj: str) -> None:
    print(f"⚠ {mesaj}", file=sys.stderr)


def _quraşdırıcıları_çap(fayllar: list[Path]) -> None:
    for f in fayllar:
        try:
            g = f.relative_to(Path.cwd())
        except ValueError:
            g = f
        print(f"  ✓ {g}  ({f.stat().st_size / 1024:.0f} KB)")


def əmr_qur(arqumentlər: list[str]) -> int:
    """
    `qur [--tip]` — `qurma/<ad>.pyz` tək fayllı paket.
    `qur --quraşdırıcı [--platforma linux,windows,macos] [--python-daxil]`
    — həm də .deb, Windows (zip + Inno Setup), macOS .app.
    `qur --studio [çıxış]` — Alqor Studio-nun öz quraşdırıcıları.
    """
    from alqor import qurasdirici, qurucu
    from alqor.alqorfmt import faylları_tap

    if "--hədəf" in arqumentlər:
        return _js_qur(arqumentlər)
    if "--alqor" in arqumentlər:
        return _alqor_windows(arqumentlər)

    quraşdırıcı = bool({"--quraşdırıcı", "--qurasdirici"} & set(arqumentlər))
    python_daxil = "--python-daxil" in arqumentlər
    platformalar = _platformalar(arqumentlər)
    if platformalar is None:
        return 3
    formatlar = _formatlar(arqumentlər)
    if formatlar is False:
        return 3
    if formatlar:
        from alqor.qurasdirici import FORMATLAR
        # `--format dmg` tək verilibsə platforma avtomatik seçilir
        if not any(a.startswith("--platforma") for a in arqumentlər):
            platformalar = tuple(p for p, f in FORMATLAR.items()
                                 if set(f) & set(formatlar))
    kök = Path(__file__).resolve().parent
    if "--studio" in arqumentlər:
        dəyərlər = set()
        for i, a in enumerate(arqumentlər):
            if a in ("--platforma", "--format") and i + 1 < len(arqumentlər):
                dəyərlər.add(arqumentlər[i + 1])
        sərbəst = [a for a in arqumentlər if not a.startswith("-")
                   and a not in dəyərlər]
        çıxış = Path(sərbəst[0]) if sərbəst else Path("qurma")
        try:
            n = qurasdirici.studio(kök, çıxış.resolve(), platformalar,
                                   python_daxil, formatlar, _xəbərdar)
        except (OSError, RuntimeError) as x:
            çap_xəta(f"Studio quraşdırıcısı qurulmadı: {x}")
            return 4
        print("✓ Alqor Studio quraşdırıcıları:")
        _quraşdırıcıları_çap(n)
        return 0

    layihə = _layihə(".")
    tək_fayl = [a for a in _faylları_topla(arqumentlər)
                if a.endswith((".alq", ".alqor"))]
    if tək_fayl and "--exe" in arqumentlər:
        # `alqor qur --exe proqram.alq` — layihəsiz tək fayl
        from alqor.layihe import Layihə
        f = Path(tək_fayl[0]).resolve()
        if not f.is_file():
            çap_xəta(f"fayl tapılmadı: {tək_fayl[0]}")
            return 4
        layihə = Layihə(f.parent, {"paket": {"ad": f.stem},
                                   "qurma": {"giriş": f.name,
                                             "çıxış": "qurma/"}})
    if layihə is None:
        çap_xəta("`qur` `layihe.alq` olan qovluqda işlədilir "
                 "(yeni layihə: alqor yeni <ad>)")
        return 3
    if "--tip" in arqumentlər:
        from alqor.lekser import Lekser
        from alqor.parser import Parser
        xəta = 0
        for f in faylları_tap([str(layihə.giriş.parent)]):
            x = XətaToplayıcı()
            s = Mənbə.fayldan(f, x)
            ağac = Parser(Lekser(s, x).leksə(), s, x).ayır() if s else None
            if ağac is not None and x.uğurludur():
                t = _tipləri_yoxla(ağac, s, layihə.tip_rejimi)
                for d in t.siyahı:
                    x.əlavə(d)
            if not x.uğurludur():
                x.çap()
                xəta += 1
        if xəta:
            print(f"✖ {xəta} faylda xəta — paket qurulmadı")
            return 2
    if "--exe" in arqumentlər:
        from alqor import exe_qurucu
        konsol = (True if "--konsol" in arqumentlər else
                  False if {"--pəncərə", "--pencere"} & set(arqumentlər)
                  else None)
        try:
            exe = exe_qurucu.qur(layihə, Path(__file__).resolve().parent,
                                 konsol)
        except (OSError, RuntimeError) as x:
            çap_xəta(f".exe qurulmadı: {x}")
            return 4
        try:
            göstər = exe.relative_to(Path.cwd())
        except ValueError:
            göstər = exe
        print(f"✓ {göstər}  ({exe.stat().st_size / 1048576:.1f} MB)")
        print("  Bu faylı istənilən Windows 10/11 kompüterinə köçürüb işlədin —"
              " Alqor və ya Python lazım deyil.")
        return 0
    try:
        n = qurucu.qur(layihə, Path(__file__).resolve().parent)
    except FileNotFoundError as x:
        çap_xəta(str(x))
        return 4
    try:
        göstər = n.yol.relative_to(Path.cwd())
    except ValueError:
        göstər = n.yol
    print(f"✓ {göstər}  ({n.ölçü / 1024:.0f} KB, {n.fayl_sayı} fayl)")
    print(f"  İşlətmək: python {göstər}")
    if quraşdırıcı:
        try:
            t = qurasdirici.layihədən(layihə, n.yol, kök)
            fayllar = qurasdirici.qur(t, layihə.çıxış, platformalar,
                                      python_daxil, formatlar, _xəbərdar)
        except (OSError, RuntimeError) as x:
            çap_xəta(f"quraşdırıcı qurulmadı: {x}")
            return 4
        print("✓ Quraşdırıcılar:")
        _quraşdırıcıları_çap(fayllar)
    return 0


def əmr_təmizlə(arqumentlər: list[str]) -> int:
    from alqor import qurucu
    layihə = _layihə(".")
    if layihə is None:
        çap_xəta("`layihe.alq` tapılmadı")
        return 3
    try:
        silindi = qurucu.təmizlə(layihə)
    except ValueError as x:
        çap_xəta(str(x))
        return 3
    print(f"✓ {layihə.çıxış} silindi" if silindi
          else "Təmizləniləcək heç nə yoxdur")
    return 0


def əmr_hərf(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        çap_xəta("`hərf` əmri üçün mətn lazımdır")
        return 3
    mətn = " ".join(arqumentlər)
    print(f"  giriş          : {mətn!r}")
    print(f"  böyüyə  (Alqor): {elifba.böyüyə(mətn)!r}")
    print(f"  böyüyə (Python): {mətn.upper()!r}")
    print(f"  kiçiyə  (Alqor): {elifba.kiçiyə(mətn)!r}")
    print(f"  kiçiyə (Python): {mətn.lower()!r}")
    print(f"  baş böyük      : {elifba.baş_böyük(mətn)!r}")
    print(f"  hər söz böyük  : {elifba.hər_söz_böyük(mətn)!r}")
    print(f"  latınla        : {elifba.latınla(mətn)!r}")

    fərq_b = elifba.böyüyə(mətn) != mətn.upper()
    fərq_k = elifba.kiçiyə(mətn) != mətn.lower()
    if fərq_b or fərq_k:
        print()
        print("  ⚠ Python-un standart çevrilməsi bu mətndə YANLIŞ nəticə verir.")
    return 0


def əmr_sırala(arqumentlər: list[str]) -> int:
    if not arqumentlər:
        çap_xəta("`sırala` əmri üçün sözlər lazımdır")
        return 3
    print(f"  Alqor (az-AZ) : {elifba.sırala(arqumentlər)}")
    print(f"  Python        : {sorted(arqumentlər)}")
    print()
    print(f"  Əlifba sırası : {' '.join(elifba.KICIK)}")
    return 0


def əmr_söhbət(arqumentlər: list[str]) -> int:
    """İnteraktiv rejim (REPL)."""
    from alqor.sohbet import söhbət_başlat
    rəngli = None
    if "--rəngsiz" in arqumentlər or "--rengsiz" in arqumentlər:
        rəngli = False
    return söhbət_başlat(rəngli)


def əmr_ls(arqumentlər: list[str]) -> int:
    """`ls [--stdio]` — Dil Serveri (LSP), stdin/stdout üzərindən."""
    from alqor.alqorls import işə_sal
    if sys.stdin.isatty() and "--stdio" not in arqumentlər:
        print("alqorls — Alqor Dil Serveri (LSP). Redaktor tərəfindən "
              "işə salınır:\n    alqor ls --stdio", file=sys.stderr)
    return işə_sal()


def əmr_dap(arqumentlər: list[str]) -> int:
    """`dap` — Debaq Adapter Protokolu serveri, stdin/stdout üzərindən."""
    from alqor.alqordap import işə_sal
    if sys.stdin.isatty():
        print("alqordap — Alqor debaqçısı (DAP). Redaktor tərəfindən "
              "işə salınır:\n    alqor dap", file=sys.stderr)
    return işə_sal()


def əmr_studio(arqumentlər: list[str]) -> int:
    """Alqor Studio — inkişaf mühiti (`studio/` paketi)."""
    from studio.server import işə_sal
    port = 0
    qovluq = "."
    ilk_fayl = None
    atla = False
    for i, a in enumerate(arqumentlər):
        if atla:
            atla = False
            continue
        if a == "--fayl" and i + 1 < len(arqumentlər):
            ilk_fayl = arqumentlər[i + 1]
            atla = True
            continue
        if a == "--port" and i + 1 < len(arqumentlər):
            try:
                port = int(arqumentlər[i + 1])
            except ValueError:
                çap_xəta(f"port ədəd olmalıdır: {arqumentlər[i + 1]!r}")
                return 3
            atla = True
        elif not a.startswith("-"):
            qovluq = a
    # `alqor studio fayl.alq` — qovluğu açıb faylı göstərir
    if Path(qovluq).is_file():
        ilk_fayl = ilk_fayl or Path(qovluq).name
        qovluq = str(Path(qovluq).resolve().parent)
    başsız = True if {"--başsız", "--bassiz"} & set(arqumentlər) else None
    sınaq = bool({"--sınaq", "--sinaq"} & set(arqumentlər))
    return işə_sal(qovluq, port, başsız, sınaq, ilk_fayl)


def əmr_pm(arqumentlər: list[str]) -> int:
    from alqor.alqorpm import əsas as pm_əsas
    return pm_əsas(arqumentlər)


def əmr_hub(arqumentlər: list[str]) -> int:
    from alqor.alqorhub import əsas as hub_əsas
    return hub_əsas(arqumentlər)


def əmr_lint(arqumentlər: list[str]) -> int:
    from alqor.alqorlint import əsas as lint_əsas
    return lint_əsas(arqumentlər)


def əmr_yerləşdir(arqumentlər: list[str]) -> int:
    """`alqor yerləşdir` — vebə çıxarmaq üçün hazır paket."""
    from alqor import yerlesdir
    from alqor.layihe import Layihə
    fayllar = [a for a in _faylları_topla(arqumentlər)
               if a.endswith((".alq", ".alqor"))]
    if fayllar:
        f = Path(fayllar[0]).resolve()
        if not f.is_file():
            çap_xəta(f"fayl tapılmadı: {fayllar[0]}")
            return 4
        layihə = Layihə(f.parent, {"paket": {"ad": f.stem},
                                   "qurma": {"giriş": f.name,
                                             "çıxış": "qurma/"}})
    else:
        layihə = _layihə(".")
        if layihə is None:
            çap_xəta("`layihe.alq` olan qovluqda işlədin və ya fayl verin: "
                     "alqor yerləşdir proqram.alq")
            return 3
    növ = ("statik" if "--statik" in arqumentlər else
           "server" if "--server" in arqumentlər else None)
    çıxış = None
    if "--çıxış" in arqumentlər:
        i = arqumentlər.index("--çıxış")
        if i + 1 < len(arqumentlər):
            çıxış = Path(arqumentlər[i + 1]).resolve()
    try:
        n = yerlesdir.yerləşdir(layihə, Path(__file__).resolve().parent,
                                növ, çıxış)
    except yerlesdir.YerləşdirməXətası as x:
        çap_xəta(str(x))
        return 2
    try:
        göstər = n.qovluq.relative_to(Path.cwd())
    except ValueError:
        göstər = n.qovluq
    if n.növ == "statik":
        print(f"✓ Statik sayt: {göstər}{os.sep}index.html")
        print("  Ən asan yol: https://app.netlify.com/drop — qovluğu sürükləyin")
    else:
        print(f"✓ Server paketi: {göstər}  (tetbiq.pyz + Dockerfile)")
        print("  Render.com / Fly.io / VPS — Docker ilə")
    print(f"  Addım-addım: {göstər}{os.sep}YERLESDIR.md")
    return 0


def əmr_sənədlər(arqumentlər: list[str]) -> int:
    """`alqor sənədlər` — oflayn sənəd mərkəzini brauzerdə açır."""
    from alqor import sened_merkezi
    kök = Path(__file__).resolve().parent
    if "--qur" in arqumentlər:
        sərbəst = [a for a in arqumentlər if not a.startswith("-")]
        çıxış = Path(sərbəst[0]) if sərbəst else Path("qurma") / "sened"
        indeks = sened_merkezi.qur(kök.parent, çıxış.resolve())
        print(f"✓ {indeks}")
        return 0
    indeks = sened_merkezi.sənəd_qovluğu(kök) / "index.html"
    print(f"Alqor sənədləri: {indeks}")
    if "--açma" not in arqumentlər:
        import webbrowser
        webbrowser.open(indeks.as_uri())
    return 0


def əmr_versiya(_: list[str]) -> int:
    print(f"Alqor {VERSIYA}")
    print(f"Etalon implementasiya — Python {sys.version.split()[0]}")
    print(f"Platforma: {sys.platform}")
    print(f"Çıxış kodlaşdırması: {sys.stdout.encoding}")
    return 0


def əmr_kömək(_: list[str]) -> int:
    print(f"""Alqor {VERSIYA} — Azərbaycan dilində proqramlaşdırma dili

İSTİFADƏ:
    python alqorc.py <əmr> [arqumentlər]

ƏMRLƏR:
    yeni <ad>            Yeni layihə: --şablon konsol|veb|desktop|kitabxana
    işlət [fayl]         Proqramı icra edir (fayl yoxdursa — layihənin
                         giriş nöqtəsi, `layihe.alq`)
                         --tip           icradan əvvəl tipləri yoxlayır
                         --js            JavaScript-ə çevirib node ilə
                         -- arq1 arq2    proqrama arqument ötürür
    tokenlər <fayl>      Faylı leksə edib tokenləri göstərir
                         --ətraflı / -e  əlavə məlumat
    söhbət               İnteraktiv rejim (REPL)
    yoxla <fayl|qovluq>  Leksik, sintaktik VƏ TİP xətalarını yoxlayır
    format <fayl|qovluq> Kodu format edir (alqorfmt): girinti, boşluqlar,
                         ASCII açar sözlər → `əgər`
                         --yoxla  --fərq  --ascii-saxla  --homoqlif-düzəlt
    pm <əmr>             Paket meneceri (alqorpm): əlavə, sil, yüklə,
                         yenilə, siyahı, ağac, axtar, yayımla, yoxla …
    hub                  Paket deposu serveri (alqorhub): --port --qovluq
    lint <fayl|qovluq>   Statik təhlil (alqorlint): üslub, təhlükəsizlik,
                         mürəkkəblik --düzəlt --sərtlik S --json --qaydalar
    sına [yol]           Sınaqlar (@sınaq): --filtr söz  --sənəd  --ətraflı
    sənəd [yol]          API sənədi (///): --format html|markdown  --çıxış q
    qur [--tip]          qurma/<ad>.pyz — tək fayllı paket
                         --quraşdırıcı   + .deb, .rpm, .AppImage, Windows
                                         (zip/Inno Setup), macOS .app və .dmg
                         --platforma linux,windows,macos   --python-daxil
                         --format deb,rpm,appimage,windows,app,dmg
                         --studio        Alqor Studio-nun quraşdırıcıları
                         --exe           tək .exe (Windows) — Alqor/Python
                                         olmayan kompüterdə də işləyir;
                                         --konsol | --pəncərə
                         --alqor         Alqor-un Windows quraşdırıcısı
                                         (Studio + əmrlər + daxili Python)
                         --hədəf js [fayl]   qurma/<ad>.js (Node.js)
                         --hədəf veb [fayl]  qurma/veb/index.html (brauzer)
    təmizlə              qurma/ qovluğunu silir
    tip <fayl|qovluq>    Yalnız tip yoxlaması
                         --rejim sərbəst|normal|sərt
    hərf <mətn>          az-AZ böyük/kiçik çevrilməsini göstərir
    sırala <söz>...      Azərbaycan əlifba sırası ilə sıralayır
    ls                   Dil serveri (LSP) — VS Code, Neovim, Helix üçün
    dap                  Debaqçı (DAP) — dayanma nöqtələri, addım, dəyişənlər
    studio [qovluq]      Alqor Studio — redaktor, vidjet paleti, icra
                         --port N        sabit port
                         --başsız        pəncərə açmır, ünvanı çap edir
                         --sınaq         özünü yoxlayıb çıxır
    yerləşdir [fayl]     Vebə çıxarmaq üçün paket: statik sayt (JS) və ya
                         server (Dockerfile); --statik --server --çıxış q
    sənədlər             Sənədləri (dərsliklər, arayış, nümunələr) brauzerdə
                         açır — internetsiz; --qur [çıxış] statik sayt
    versiya              Versiya məlumatı
    kömək                Bu mətn

NÜMUNƏLƏR:
    python alqorc.py söhbət
    python alqorc.py işlət ../numuneler/02-dovrler.alq
    python alqorc.py tokenlər ../numuneler/01-salam.alq
    python alqorc.py yoxla ../numuneler
    python alqorc.py hərf "ışıq İmran"
    python alqorc.py sırala zəfər ağac çay ışıq ilk

TİP REJİMLƏRİ (`layihe.alq` → [tip] rejim, və ya --rejim):
    sərbəst    yalnız açıq yazılmış tiplər yoxlanılır
    normal     çıxarma + yoxlama (standart)
    sərt       açıq funksiya imzaları məcburi, naməlum üzvlər xətadır

MÜHİT DƏYİŞƏNLƏRİ:
    ALQOR_RENG=həmişə|heçvaxt|avto     rəngli çıxış

VƏZİYYƏT:
    Lekser, parser və interpretator hazırdır.
    Ətraflı: alqorc/VEZIYYET.md""")
    return 0


# ═══════════════════════════════════════════════════════════════════════
#  Dispetçer
# ═══════════════════════════════════════════════════════════════════════

ƏMRLƏR = {
    "işlət": əmr_işlət, "islet": əmr_işlət, "run": əmr_işlət,
    "tokenlər": əmr_tokenlər, "tokenler": əmr_tokenlər,
    "yoxla": əmr_yoxla,
    "söhbət": əmr_söhbət, "sohbet": əmr_söhbət, "repl": əmr_söhbət,
    "tip": əmr_tip, "tiplər": əmr_tip, "tipler": əmr_tip,
    "format": əmr_format, "formatla": əmr_format, "fmt": əmr_format,
    "lint": əmr_lint, "alqorlint": əmr_lint,
    "pm": əmr_pm, "alqorpm": əmr_pm, "paket": əmr_pm,
    "hub": əmr_hub, "alqorhub": əmr_hub,
    "yeni": əmr_yeni, "new": əmr_yeni,
    "sına": əmr_sına, "sina": əmr_sına, "test": əmr_sına,
    "sənəd": əmr_sənəd, "sened": əmr_sənəd, "doc": əmr_sənəd,
    "yerləşdir": əmr_yerləşdir, "yerlesdir": əmr_yerləşdir,
    "deploy": əmr_yerləşdir,
    "sənədlər": əmr_sənədlər, "senedler": əmr_sənədlər, "docs": əmr_sənədlər,
    "dərslik": əmr_sənədlər,
    "qur": əmr_qur, "build": əmr_qur,
    "təmizlə": əmr_təmizlə, "temizle": əmr_təmizlə, "clean": əmr_təmizlə,
    "hərf": əmr_hərf, "herf": əmr_hərf,
    "sırala": əmr_sırala, "sirala": əmr_sırala,
    "studio": əmr_studio,
    "ls": əmr_ls, "lsp": əmr_ls, "dap": əmr_dap, "debaq": əmr_dap,
    "versiya": əmr_versiya, "--versiya": əmr_versiya, "-v": əmr_versiya,
    "kömək": əmr_kömək, "komek": əmr_kömək,
    "--kömək": əmr_kömək, "--komek": əmr_kömək, "-k": əmr_kömək,
}


def çap_xəta(mesaj: str) -> None:
    print(f"✖ {mesaj}", file=sys.stderr)
    print(f"  `python alqorc.py kömək` yazın", file=sys.stderr)


def əsas(arqumentlər: list[str] | None = None) -> int:
    arq = list(sys.argv[1:] if arqumentlər is None else arqumentlər)
    if not arq:
        return əmr_kömək([])

    əmr = arq[0]
    işləyici = ƏMRLƏR.get(əmr)
    if işləyici is None:
        çap_xəta(f"naməlum əmr: {əmr!r}")
        oxşar = [a for a in ƏMRLƏR if a.startswith(əmr[:3])]
        if oxşar:
            print(f"  bəlkə: {', '.join(sorted(set(oxşar))[:3])}",
                  file=sys.stderr)
        return 3
    try:
        return işləyici(arq[1:])
    except KeyboardInterrupt:
        print("\n⊣ dayandırıldı", file=sys.stderr)
        return 130
    except BrokenPipeError:
        # `alqor … | head` — oxuyan tərəf bağlandı, bu xəta deyil
        try:
            sys.stdout = open(os.devnull, "w")
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(əsas())
