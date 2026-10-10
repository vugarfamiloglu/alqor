"""
Alqor-un öz Linux və macOS paylaması — `alqor qur --alqor --platforma
linux|macos [--arx x86_64|aarch64]`.

Python daxildir (python-build-standalone), sistemdə heç nə tələb olunmur.

Linux:
  alqor-<v>-linux-<arx>.tar.gz   açın → `./qurasdir.sh` (istifadəçi üçün,
                                 sudo lazım deyil: ~/.local/share/alqor,
                                 əmrlər ~/.local/bin-də, menyuda Studio)
  alqor_<v>_<amd64|arm64>.deb    `sudo apt install ./alqor_…deb` —
                                 /opt/alqor, əmrlər /usr/bin-də

macOS:
  Alqor-<v>-macos-<arx>.dmg      «Alqor Studio.app»-i Applications-a
                                 sürükləyin; terminal əmrləri üçün
                                 tətbiqin içindəki `qurasdir.sh`
  alqor-<v>-macos-<arx>.tar.gz   açın → `./qurasdir.sh` (~/Applications,
                                 əmrlər ~/.local/bin-də)

Hər paylamada: python/, alqorc/, bin/ (alqor, alqorpm, alqorlint,
alqorfmt, alqorls, alqor-studio), nümunələr, bələdçilər, oflayn sənədlər.
"""

from __future__ import annotations

import io
import os
import shutil
import tarfile
from pathlib import Path

from .windows_paylama import ƏMRLƏR, _STUDIO, _kopyala, versiya_təmiz

ARXLAR = ("x86_64", "aarch64")
_ÜÇLÜK = {"linux": "unknown-linux-gnu", "macos": "apple-darwin"}
_DEB_ARX = {"x86_64": "amd64", "aarch64": "arm64"}

_ƏMR = """#!/bin/sh
# {ad} — Alqor {versiya}
K="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/.." && pwd)"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
exec "$K/python/bin/python3" "$K/alqorc/alqorc.py" {əmr}"$@"
"""

_STUDIO_ƏMR = """#!/bin/sh
# Alqor Studio — Alqor {versiya}
K="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/.." && pwd)"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
exec "$K/python/bin/python3" "$K/bin/studio.py" "$@"
"""

_QURAŞDIR_LINUX = """#!/bin/sh
# Alqor {versiya} — istifadəçi üçün quraşdırma (sudo lazım deyil)
set -e
MENBE="$(cd "$(dirname "$0")" && pwd)"
HEDEF="${{XDG_DATA_HOME:-$HOME/.local/share}}/alqor"
BIN="$HOME/.local/bin"
if [ "$MENBE" != "$HEDEF" ]; then
  rm -rf "$HEDEF"
  mkdir -p "$(dirname "$HEDEF")"
  cp -R "$MENBE" "$HEDEF"
fi
mkdir -p "$BIN"
for e in {əmrlər} alqor-studio; do
  ln -sf "$HEDEF/bin/$e" "$BIN/$e"
done
P="${{XDG_DATA_HOME:-$HOME/.local/share}}"
mkdir -p "$P/applications" "$P/mime/packages" "$P/icons/hicolor/256x256/apps"
sed "s|@KOK@|$HEDEF|g" "$HEDEF/share/alqor-studio.desktop" > "$P/applications/alqor-studio.desktop"
cp "$HEDEF/share/alqor.xml" "$P/mime/packages/alqor.xml"
cp "$HEDEF/ikon.png" "$P/icons/hicolor/256x256/apps/alqor.png"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$P/applications" || true
command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$P/mime" || true
echo "✓ Alqor {versiya} quraşdırıldı: $HEDEF"
case ":$PATH:" in
  *":$BIN:"*) echo "  Sınayın: alqor versiya" ;;
  *) echo "  $BIN PATH-da deyil. ~/.profile-a əlavə edin:"
     echo "    export PATH=\\"\\$HOME/.local/bin:\\$PATH\\""
     echo "  və ya indi: $BIN/alqor versiya" ;;
esac
echo "  Silmək: $HEDEF/sil.sh"
"""

_SİL_LINUX = """#!/bin/sh
# Alqor-u silir (layihələriniz toxunulmaz qalır)
HEDEF="${XDG_DATA_HOME:-$HOME/.local/share}/alqor"
P="${XDG_DATA_HOME:-$HOME/.local/share}"
for e in alqor alqorpm alqorlint alqorfmt alqorls alqor-studio; do
  [ -L "$HOME/.local/bin/$e" ] && rm -f "$HOME/.local/bin/$e"
done
rm -f "$P/applications/alqor-studio.desktop" "$P/mime/packages/alqor.xml" \\
      "$P/icons/hicolor/256x256/apps/alqor.png"
rm -rf "$HEDEF"
echo "✓ Alqor silindi"
"""

_QURAŞDIR_MACOS = """#!/bin/sh
# Alqor {versiya} — macOS: terminal əmrləri və (tar.gz-dən) Studio
set -e
MENBE="$(cd "$(dirname "$0")" && pwd)"
case "$MENBE" in
  *.app/Contents/Resources/alqor) KOK="$MENBE" ;;
  *)
    APP="$HOME/Applications/Alqor Studio.app"
    rm -rf "$APP"
    mkdir -p "$HOME/Applications"
    cp -R "$MENBE/Alqor Studio.app" "$APP"
    xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
    KOK="$APP/Contents/Resources/alqor"
    ;;
esac
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
for e in {əmrlər} alqor-studio; do
  ln -sf "$KOK/bin/$e" "$BIN/$e"
done
xattr -dr com.apple.quarantine "$KOK" 2>/dev/null || true
for f in "$HOME/.zprofile" "$HOME/.bash_profile"; do
  if [ -f "$f" ] || [ "$f" = "$HOME/.zprofile" ]; then
    grep -q '.local/bin' "$f" 2>/dev/null || \\
      printf '\\n# Alqor\\nexport PATH="$HOME/.local/bin:$PATH"\\n' >> "$f"
  fi
done
echo "✓ Alqor {versiya}: əmrlər $BIN-də"
echo "  Yeni terminal açın və sınayın: alqor versiya"
"""

_DESKTOP = """[Desktop Entry]
Type=Application
Name=Alqor Studio
GenericName=Alqor IDE
Comment=Azərbaycan dilində proqramlaşdırma dili Alqor üçün IDE
Exec=@KOK@/bin/alqor-studio %F
Icon=alqor
Terminal=false
Categories=Development;IDE;
MimeType=text/x-alqor;
"""

_MIME = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-alqor">
    <comment>Alqor proqramı</comment>
    <sub-class-of type="text/plain"/>
    <glob pattern="*.alq"/>
    <glob pattern="*.alqor"/>
  </mime-type>
</mime-info>
"""


def _keş(keş: Path | None) -> Path:
    return keş or Path.home() / ".cache" / "alqor"


def python_arxivi(platforma: str, arx: str, keş: Path | None = None) -> Path:
    """python-build-standalone arxivi (bir dəfə endirilir)."""
    from .qurasdirici import PBS_BURAXILIŞ, PBS_URL, PYTHON_VERSİYASI, _endir
    if arx not in ARXLAR:
        raise ValueError(f"arxitektura: {', '.join(ARXLAR)}")
    öz = os.environ.get(f"ALQOR_PYTHON_{platforma.upper()}_{arx.upper()}")
    if öz:
        return Path(öz)

    def yoxla(p: Path) -> None:
        with tarfile.open(p) as t:
            if "python/bin/python3" not in t.getnames():
                raise RuntimeError("endirilən fayl Python paylaması deyil")
    url = PBS_URL.format(b=PBS_BURAXILIŞ, v=PYTHON_VERSİYASI, arx=arx) \
        .replace("unknown-linux-gnu", _ÜÇLÜK[platforma])
    return _endir(url, _keş(keş) / f"python-{PYTHON_VERSİYASI}-{arx}-"
                  f"{platforma}.tar.gz", yoxla)


def _python_aç(arxiv: Path, hədəf: Path) -> None:
    """Simvolik keçidləri və icazələri saxlayaraq açır."""
    with tarfile.open(arxiv) as t:
        for m in t.getmembers():
            ad = m.name
            if not ad.startswith("python/") or ".." in ad.split("/"):
                continue
            if any(h in ad for h in ("/test/", "/idlelib/", "/__pycache__/",
                                     "/ensurepip/", "/tkinter/test",
                                     "/lib2to3/tests")):
                continue
            nisbi = ad[len("python/"):]
            if not nisbi:
                continue
            y = hədəf / nisbi
            if m.isdir():
                y.mkdir(parents=True, exist_ok=True)
            elif m.issym():
                y.parent.mkdir(parents=True, exist_ok=True)
                if m.linkname.startswith("/") or not os.path.normpath(
                        y.parent / m.linkname).startswith(str(hədəf)):
                    continue                     # paylamadan kənara keçid
                y.unlink(missing_ok=True)
                os.symlink(m.linkname, y)
            elif m.isfile():
                y.parent.mkdir(parents=True, exist_ok=True)
                y.write_bytes(t.extractfile(m).read())
                y.chmod(m.mode & 0o755 | 0o644)


def paylama_qovluğu(alqorc_kökü: Path, q: Path, platforma: str, arx: str,
                    keş: Path | None = None) -> Path:
    """Paylamanın məzmunu `q/` qovluğunda."""
    repo = alqorc_kökü.parent
    v = versiya_təmiz()
    if q.exists():
        shutil.rmtree(q)
    q.mkdir(parents=True)
    _python_aç(python_arxivi(platforma, arx, keş), q / "python")

    a = q / "alqorc"
    a.mkdir()
    for f in ("alqorc.py", "alqorfmt.py"):
        shutil.copyfile(alqorc_kökü / f, a / f)
    for paket in ("alqor", "studio"):
        _kopyala(alqorc_kökü / paket, a / paket)
    # Windows-a aid ikili fayllar lazım deyil
    for f in (a / "alqor" / "resurslar").glob("baslatici-*.exe"):
        f.unlink()

    b = q / "bin"
    b.mkdir()
    for ad, əmr in ƏMRLƏR.items():
        f = b / ad
        f.write_text(_ƏMR.format(ad=ad, versiya=v,
                                 əmr=f"{əmr} " if əmr else ""),
                     encoding="utf-8")
        f.chmod(0o755)
    f = b / "alqor-studio"
    f.write_text(_STUDIO_ƏMR.format(versiya=v), encoding="utf-8")
    f.chmod(0o755)
    (b / "studio.py").write_text(_STUDIO, encoding="utf-8")

    for ad in ("numuneler", "beledci"):
        if (repo / ad).is_dir():
            _kopyala(repo / ad, q / ad)
    from .sened_merkezi import qur as sənəd_qur
    sənəd_qur(repo, q / "sened")
    shutil.copyfile(alqorc_kökü / "alqor" / "resurslar" / "ikon-256.png",
                    q / "ikon.png")
    if (repo / "README.md").is_file():
        shutil.copyfile(repo / "README.md", q / "README.md")

    əmrlər = " ".join(ƏMRLƏR)
    if platforma == "linux":
        s = q / "share"
        s.mkdir()
        (s / "alqor-studio.desktop").write_text(_DESKTOP, encoding="utf-8")
        (s / "alqor.xml").write_text(_MIME, encoding="utf-8")
        skriptlər = {"qurasdir.sh": _QURAŞDIR_LINUX.format(versiya=v,
                                                           əmrlər=əmrlər),
                     "sil.sh": _SİL_LINUX}
    else:
        skriptlər = {"qurasdir.sh": _QURAŞDIR_MACOS.format(versiya=v,
                                                           əmrlər=əmrlər)}
    for ad, m in skriptlər.items():
        (q / ad).write_text(m, encoding="utf-8")
        (q / ad).chmod(0o755)
    return q


# ── Arxivlər ──────────────────────────────────────────────────────────

def _tar_qovluq(q: Path, kök_adı: str, gz: bool = True) -> bytes:
    """Qovluq → tar(.gz); sahib root, keçidlər saxlanır."""
    b = io.BytesIO()

    def süz(ti: tarfile.TarInfo) -> tarfile.TarInfo:
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        return ti
    with tarfile.open(fileobj=b, mode="w:gz" if gz else "w",
                      format=tarfile.GNU_FORMAT) as t:
        t.add(q, arcname=kök_adı, filter=süz)
    return b.getvalue()


def tar_gz(q: Path, çıxış: Path, ad: str, kök_adı: str) -> Path:
    h = çıxış / ad
    h.write_bytes(_tar_qovluq(q, kök_adı))
    return h


def deb(q: Path, çıxış: Path, arx: str) -> Path:
    """`/opt/alqor` + `/usr/bin` keçidləri + menyu + `.alq` növü."""
    from .qurasdirici import _ar, _tar
    v = versiya_təmiz()
    kök = çıxış / "deb-kök"
    if kök.exists():
        shutil.rmtree(kök)
    opt = kök / "opt" / "alqor"
    shutil.copytree(q, opt, symlinks=True)
    for f in ("qurasdir.sh", "sil.sh"):
        (opt / f).unlink(missing_ok=True)
    usr = kök / "usr"
    (usr / "bin").mkdir(parents=True)
    for ə in (*ƏMRLƏR, "alqor-studio"):
        os.symlink(f"/opt/alqor/bin/{ə}", usr / "bin" / ə)
    paylaşım = usr / "share"
    for alt, ad, m in (
            ("applications", "alqor-studio.desktop",
             _DESKTOP.replace("@KOK@", "/opt/alqor").encode()),
            ("mime/packages", "alqor.xml", _MIME.encode()),
            ("icons/hicolor/256x256/apps", "alqor.png",
             (q / "ikon.png").read_bytes())):
        (paylaşım / alt).mkdir(parents=True, exist_ok=True)
        (paylaşım / alt / ad).write_bytes(m)
    ölçü = sum(p.stat().st_size for p in kök.rglob("*")
               if p.is_file() and not p.is_symlink()) // 1024 + 1
    control = (
        f"Package: alqor\nVersion: {v}\nArchitecture: {_DEB_ARX[arx]}\n"
        "Maintainer: Vüqar Familoğlu <noreply@alqor.vuqar.pro>\n"
        "Homepage: https://alqor.vuqar.pro\n"
        f"Installed-Size: {ölçü}\nSection: devel\nPriority: optional\n"
        "Description: Alqor — Azərbaycan dilində proqramlaşdırma dili\n"
        " Dil, Alqor Studio IDE, paket meneceri, linter, formatter, LSP\n"
        " serveri və oflayn sənədlər. Python daxildir.\n")
    skript = ("#!/bin/sh\n"
              "command -v update-desktop-database >/dev/null 2>&1 && "
              "update-desktop-database -q || true\n"
              "command -v update-mime-database >/dev/null 2>&1 && "
              "update-mime-database /usr/share/mime || true\nexit 0\n")
    nəzarət = {"control": (control.encode("utf-8"), 0o644),
               "postinst": (skript.encode(), 0o755),
               "postrm": (skript.encode(), 0o755)}
    data = io.BytesIO()

    def süz(ti: tarfile.TarInfo) -> tarfile.TarInfo:
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        return ti
    with tarfile.open(fileobj=data, mode="w:gz",
                      format=tarfile.GNU_FORMAT) as t:
        for p in sorted(kök.iterdir()):
            t.add(p, arcname=f"./{p.name}", filter=süz)
    h = çıxış / f"alqor_{v}_{_DEB_ARX[arx]}.deb"
    h.write_bytes(_ar([("debian-binary", b"2.0\n"),
                       ("control.tar.gz", _tar(nəzarət)),
                       ("data.tar.gz", data.getvalue())]))
    shutil.rmtree(kök)
    return h


# ── macOS .app / .dmg ─────────────────────────────────────────────────

_APP_BAŞLADICI = """#!/bin/sh
# Alqor Studio (macOS)
K="$(cd "$(dirname "$0")/../Resources/alqor" && pwd)"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
exec "$K/python/bin/python3" "$K/bin/studio.py" "$@"
"""


def _plist(v: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
        '"-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        "  <key>CFBundleName</key><string>Alqor Studio</string>\n"
        "  <key>CFBundleDisplayName</key><string>Alqor Studio</string>\n"
        "  <key>CFBundleIdentifier</key><string>pro.vuqar.alqor.studio"
        "</string>\n"
        f"  <key>CFBundleVersion</key><string>{v}</string>\n"
        f"  <key>CFBundleShortVersionString</key><string>{v}</string>\n"
        "  <key>CFBundleExecutable</key><string>alqor-studio</string>\n"
        "  <key>CFBundlePackageType</key><string>APPL</string>\n"
        "  <key>CFBundleIconFile</key><string>ikon.png</string>\n"
        "  <key>LSMinimumSystemVersion</key><string>11.0</string>\n"
        "  <key>NSHumanReadableCopyright</key><string>Vüqar Familoğlu · "
        "alqor.vuqar.pro</string>\n"
        "  <key>CFBundleDocumentTypes</key><array><dict>"
        "<key>CFBundleTypeExtensions</key><array><string>alq</string>"
        "<string>alqor</string></array><key>CFBundleTypeName</key>"
        "<string>Alqor proqramı</string><key>CFBundleTypeRole</key>"
        "<string>Editor</string></dict></array>\n"
        "</dict></plist>\n")


_DMG_OXU = ("Alqor {v}\n\n"
            "1. «Alqor Studio»-nu «Applications» qovluğuna sürükləyin.\n"
            "2. İlk açılışda: sağ klik → «Open» (tətbiq imzalanmayıb).\n"
            "3. Terminal əmrləri (alqor, alqorpm…) üçün Terminalda:\n"
            '   "/Applications/Alqor Studio.app/Contents/Resources/alqor/'
            'qurasdir.sh"\n\nSayt: https://alqor.vuqar.pro\n')


def app_qovluğu(q: Path, çıxış: Path) -> Path:
    """`Alqor Studio.app` — paylamanın hamısı Resources/alqor-dadır."""
    app = çıxış / "Alqor Studio.app"
    if app.exists():
        shutil.rmtree(app)
    c = app / "Contents"
    (c / "MacOS").mkdir(parents=True)
    (c / "Resources").mkdir()
    shutil.copytree(q, c / "Resources" / "alqor", symlinks=True)
    (c / "Info.plist").write_text(_plist(versiya_təmiz()), encoding="utf-8")
    b = c / "MacOS" / "alqor-studio"
    b.write_text(_APP_BAŞLADICI, encoding="utf-8")
    b.chmod(0o755)
    shutil.copyfile(q / "ikon.png", c / "Resources" / "ikon.png")
    return app


def _fayl_xəritəsi(kök: Path, ön: str
                   ) -> tuple[dict[str, tuple[bytes, int]], dict[str, str]]:
    fayllar: dict[str, tuple[bytes, int]] = {}
    keçidlər: dict[str, str] = {}
    for p in sorted(kök.rglob("*")):
        y = f"{ön}/{p.relative_to(kök).as_posix()}"
        if p.is_symlink():
            keçidlər[y] = os.readlink(p)
        elif p.is_file():
            fayllar[y] = (p.read_bytes(), p.stat().st_mode & 0o777)
    return fayllar, keçidlər


def dmg(app: Path, çıxış: Path, arx: str) -> Path:
    """macOS-da `hdiutil` ilə (HFS+, UDZO); başqa sistemdə saf Python ilə
    (ISO 9660 + UDIF) — buraxılışlar CI-da macOS-da qurulur."""
    v = versiya_təmiz()
    h = çıxış / f"Alqor-{v}-macos-{arx}.dmg"
    oxu = _DMG_OXU.format(v=v)
    hdiutil = shutil.which("hdiutil")
    if hdiutil and os.environ.get("ALQOR_DMG_SAF") != "1":
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as q:
            shutil.copytree(app, Path(q) / app.name, symlinks=True)
            os.symlink("/Applications", Path(q) / "Applications")
            (Path(q) / "OXU.txt").write_text(oxu, encoding="utf-8")
            h.unlink(missing_ok=True)
            subprocess.run([hdiutil, "create", "-volname", f"Alqor {v}",
                            "-srcfolder", q, "-ov", "-format", "UDZO",
                            "-fs", "HFS+", str(h)], check=True)
        return h
    from ._qur_dmg import iso9660, udif
    fayllar, keçidlər = _fayl_xəritəsi(app, app.name)
    keçidlər["Applications"] = "/Applications"
    fayllar["OXU.txt"] = (oxu.encode("utf-8"), 0o644)
    imaj = iso9660(fayllar, keçidlər, "ALQOR")
    h.write_bytes(udif(imaj, f"Alqor {v}"))
    return h


def qur(alqorc_kökü: Path, çıxış: Path, platforma: str,
        arx: str = "x86_64", keş: Path | None = None) -> list[Path]:
    if platforma not in ("linux", "macos"):
        raise ValueError("platforma: linux | macos")
    çıxış.mkdir(parents=True, exist_ok=True)
    v = versiya_təmiz()
    iş = çıxış / f"alqor-{platforma}-{arx}"
    q = paylama_qovluğu(alqorc_kökü, iş / f"alqor-{v}", platforma, arx, keş)
    n: list[Path] = []
    if platforma == "linux":
        n.append(tar_gz(q, çıxış, f"alqor-{v}-linux-{arx}.tar.gz",
                        f"alqor-{v}"))
        n.append(deb(q, çıxış, arx))
    else:
        app = app_qovluğu(q, iş)
        n.append(dmg(app, çıxış, arx))
        # tar.gz: Studio.app + qurasdir.sh (terminal əmrləri)
        t = iş / "tar"
        if t.exists():
            shutil.rmtree(t)
        t.mkdir()
        shutil.copytree(app, t / app.name, symlinks=True)
        shutil.copyfile(q / "qurasdir.sh", t / "qurasdir.sh")
        (t / "qurasdir.sh").chmod(0o755)
        n.append(tar_gz(t, çıxış, f"alqor-{v}-macos-{arx}.tar.gz",
                        f"alqor-{v}"))
    shutil.rmtree(iş, ignore_errors=True)
    return n
