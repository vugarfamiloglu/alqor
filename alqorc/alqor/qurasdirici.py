"""
Alqor — quraşdırıcı generatoru (`alqor qur --quraşdırıcı`).

Spesifikasiya § 13.2. `qur`-un yaratdığı `.pyz` paketini hər əməliyyat
sistemi üçün quraşdırılan formaya bükür. Xarici alət TƏLƏB OLUNMUR —
hamısı saf Python ilə yaradılır:

    qurma/<ad>_<versiya>_all.deb            Debian/Ubuntu (apt install ./…)
    qurma/<ad>-<versiya>-1.noarch.rpm       Fedora/RHEL/openSUSE (dnf install)
    qurma/<Ad>-<versiya>-x86_64.AppImage    istənilən Linux (runtime bir dəfə
                                            endirilir, keşlənir)
    qurma/<ad>-<versiya>-windows.zip        Windows: "Qurasdir.cmd" — Başlat
                                            menyusu, masaüstü ikonu, fayl
                                            əlaqələri, "Proqramlar"-da silmə
    qurma/<ad>-<versiya>-windows.iss        Inno Setup skripti (`iscc` varsa
                                            avtomatik `…-setup.exe` qurulur)
    qurma/<ad>-<versiya>-macos.zip          macOS `.app` paketi
    qurma/<ad>-<versiya>.dmg                macOS disk imajı (.app + Applications)

`--python-daxil` Windows paketinə Python-un rəsmi "embeddable" paylamasını,
AppImage-ə python-build-standalone paylamasını qoyur (bir dəfə endirilir,
keşlənir) — hədəf kompüterdə Python quraşdırmaq lazım olmur.

Manifest (`layihe.alq`):

    [quraşdırıcı]
    başlıq = "Kitab Rəfi"            # menyudakı ad (standart: paket adı)
    naşir = "Aysel Məmmədova"
    ikon = "ikon.png"                # .png (Linux/macOS), .ico (Windows)
    konsol = yanlış                  # pəncərəli tətbiq — konsol açılmır
    uzantılar = [".kitab"]           # bu faylları tətbiq açır
"""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import re
import shutil
import stat
import tarfile
import time
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

PYTHON_VERSİYASI = "3.12.7"
_TRANSLİT = str.maketrans({"ə": "e", "Ə": "e", "ı": "i", "I": "i", "İ": "i",
                           "ş": "s", "Ş": "s", "ç": "c", "Ç": "c", "ğ": "g",
                           "Ğ": "g", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u"})


@dataclass
class Tətbiq:
    """Quraşdırılacaq tətbiqin təsviri (layihədən və ya Studio-dan)."""
    ad: str                          # paket adı (ASCII-yə çevrilir)
    başlıq: str                      # menyuda görünən ad
    versiya: str
    pyz: Path
    təsvir: str = ""
    naşir: str = "Alqor"
    png: Path | None = None
    ico: Path | None = None
    konsol: bool = True
    uzantılar: list[str] = field(default_factory=list)
    arqumentlər: list[str] = field(default_factory=list)  # pyz-dən sonra

    @property
    def sistem_adı(self) -> str:
        """`kitab-refi` — paket/fayl adı üçün təhlükəsiz ASCII."""
        a = self.ad.translate(_TRANSLİT).lower()
        a = re.sub(r"[^a-z0-9.+-]+", "-", a).strip("-.")
        return a or "alqor-tetbiq"

    @property
    def versiya_təmiz(self) -> str:
        v = re.sub(r"[^0-9A-Za-z.+~-]", "", self.versiya)
        return v if v and v[0].isdigit() else "0.1.0"


def layihədən(layihə, pyz: Path, alqorc_kökü: Path) -> Tətbiq:
    q = layihə.məlumat.get("quraşdırıcı") or {}
    ikon = q.get("ikon")
    png = ico = None
    if ikon:
        p = layihə.kök / str(ikon)
        if not p.is_file():
            raise FileNotFoundError(f"ikon tapılmadı: {p}")
        if p.suffix.lower() == ".ico":
            ico = p
        else:
            png = p
        yan = p.with_suffix(".ico" if png else ".png")
        if yan.is_file():
            ico, png = (yan, p) if png else (p, yan)
    res = alqorc_kökü / "alqor" / "resurslar"
    uzantılar = [str(u) if str(u).startswith(".") else "." + str(u)
                 for u in q.get("uzantılar") or []]
    return Tətbiq(
        ad=layihə.ad, başlıq=str(q.get("başlıq") or layihə.ad),
        versiya=layihə.versiya, pyz=pyz, təsvir=layihə.təsvir,
        naşir=str(q.get("naşir") or "Alqor"),
        png=png or res / "ikon-256.png", ico=ico or res / "alqor.ico",
        konsol=bool(q.get("konsol", True)), uzantılar=uzantılar)


# ═══════════════════════════════════════════════════════════════════════
#  Linux — .deb
# ═══════════════════════════════════════════════════════════════════════

def _tar(fayllar: dict[str, tuple[bytes, int]]) -> bytes:
    """{yol: (məzmun, rejim)} → tar.gz (qovluqlar avtomatik)."""
    b = io.BytesIO()
    qovluqlar: set[str] = set()
    for yol in fayllar:
        h = yol.strip("/").split("/")[:-1]
        for i in range(1, len(h) + 1):
            qovluqlar.add("/".join(h[:i]))
    zaman = int(time.time())
    with gzip.GzipFile(fileobj=b, mode="wb", mtime=zaman) as gz:
        with tarfile.open(fileobj=gz, mode="w",
                          format=tarfile.GNU_FORMAT) as t:
            for q in sorted(qovluqlar):
                ti = tarfile.TarInfo("./" + q)
                ti.type, ti.mode, ti.mtime = tarfile.DIRTYPE, 0o755, zaman
                ti.uname = ti.gname = "root"
                t.addfile(ti)
            for yol, (məzmun, rejim) in sorted(fayllar.items()):
                ti = tarfile.TarInfo("./" + yol.strip("/"))
                ti.size, ti.mode, ti.mtime = len(məzmun), rejim, zaman
                ti.uname = ti.gname = "root"
                t.addfile(ti, io.BytesIO(məzmun))
    return b.getvalue()


def _ar(üzvlər: list[tuple[str, bytes]]) -> bytes:
    n = b"!<arch>\n"
    zaman = int(time.time())
    for ad, d in üzvlər:
        baş = (f"{ad:<16}{zaman:<12}{0:<6}{0:<6}{'100644':<8}"
               f"{len(d):<10}`\n").encode("ascii")
        n += baş + d + (b"\n" if len(d) % 2 else b"")
    return n


def _mime_növləri(t: Tətbiq) -> list[str]:
    return [f"application/x-{t.sistem_adı}{u.replace('.', '-')}"
            for u in t.uzantılar]


def _desktop(t: Tətbiq, exec_: str, ikon: str) -> bytes:
    mime = "".join(f"{m};" for m in _mime_növləri(t))
    return ("[Desktop Entry]\nType=Application\n"
            f"Name={t.başlıq}\nComment={t.təsvir or t.başlıq}\n"
            f"Exec={exec_} %F\nIcon={ikon}\n"
            f"Terminal={'true' if t.konsol else 'false'}\n"
            "Categories=Utility;Development;\n"
            + (f"MimeType={mime}\n" if mime else "")).encode("utf-8")


def _mime_xml(t: Tətbiq) -> bytes:
    növlər = "".join(
        f'  <mime-type type="{m}">\n'
        f'    <comment>{_xml(t.başlıq)} faylı</comment>\n'
        f'    <glob pattern="*{u}"/>\n  </mime-type>\n'
        for m, u in zip(_mime_növləri(t), t.uzantılar))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<mime-info xmlns='
            '"http://www.freedesktop.org/standards/shared-mime-info">\n'
            + növlər + "</mime-info>\n").encode("utf-8")


def _linux_fayllar(t: Tətbiq) -> dict[str, tuple[bytes, int]]:
    """`.deb` və `.rpm` üçün ortaq fayl düzülüşü (/usr altında)."""
    ad = t.sistem_adı
    lib = f"usr/lib/{ad}"
    başladıcı = (f'#!/bin/sh\nexec python3 /{lib}/{ad}.pyz '
                 + " ".join(t.arqumentlər) + ' "$@"\n')
    fayllar: dict[str, tuple[bytes, int]] = {
        f"{lib}/{ad}.pyz": (t.pyz.read_bytes(), 0o644),
        f"usr/bin/{ad}": (başladıcı.encode(), 0o755),
    }
    if t.png and t.png.is_file():
        fayllar[f"usr/share/icons/hicolor/256x256/apps/{ad}.png"] = (
            t.png.read_bytes(), 0o644)
    if t.uzantılar:
        fayllar[f"usr/share/mime/packages/{ad}.xml"] = (_mime_xml(t), 0o644)
    fayllar[f"usr/share/applications/{ad}.desktop"] = (
        _desktop(t, ad, ad), 0o644)
    return fayllar


_YENİLƏ_SKRİPTİ = ("#!/bin/sh\n"
                   "command -v update-desktop-database >/dev/null 2>&1 && "
                   "update-desktop-database -q || true\n"
                   "command -v update-mime-database >/dev/null 2>&1 && "
                   "update-mime-database /usr/share/mime || true\n"
                   "exit 0\n")


def deb(t: Tətbiq, çıxış: Path) -> Path:
    ad = t.sistem_adı
    fayllar = _linux_fayllar(t)

    ölçü = sum(len(d) for d, _ in fayllar.values()) // 1024 + 1
    control = (
        f"Package: {ad}\nVersion: {t.versiya_təmiz}\nArchitecture: all\n"
        f"Maintainer: {t.naşir} <noreply@alqor.az>\n"
        "Depends: python3 (>= 3.12)\n"
        f"Installed-Size: {ölçü}\nSection: misc\nPriority: optional\n"
        f"Description: {(t.təsvir or t.başlıq).splitlines()[0]}\n"
        f" Alqor ilə yazılmış tətbiq ({t.başlıq}).\n")
    skript = _YENİLƏ_SKRİPTİ
    nəzarət = {"control": (control.encode("utf-8"), 0o644),
               "postinst": (skript.encode(), 0o755),
               "postrm": (skript.encode(), 0o755)}
    md5 = "".join(f"{hashlib.md5(d).hexdigest()}  {y}\n"
                  for y, (d, _) in sorted(fayllar.items()))
    nəzarət["md5sums"] = (md5.encode(), 0o644)
    hədəf = çıxış / f"{ad}_{t.versiya_təmiz}_all.deb"
    hədəf.write_bytes(_ar([("debian-binary", b"2.0\n"),
                           ("control.tar.gz", _tar(nəzarət)),
                           ("data.tar.gz", _tar(fayllar))]))
    return hədəf


def rpm(t: Tətbiq, çıxış: Path) -> Path:
    """Fedora / RHEL / openSUSE: `sudo dnf install ./…rpm`."""
    from ._qur_rpm import rpm as rpm_yaz
    ad = t.sistem_adı
    v = t.versiya_təmiz.replace("-", "_").replace("~", "_")
    fayllar = {"/" + y: d for y, d in _linux_fayllar(t).items()}
    skript = _YENİLƏ_SKRİPTİ.split("\n", 1)[1]           # shebang-sız
    data = rpm_yaz(ad, v, (t.təsvir or t.başlıq).splitlines()[0],
                   f"{t.təsvir or t.başlıq}\n\nAlqor ilə yazılmış tətbiq "
                   f"({t.başlıq}).", t.naşir, fayllar, [f"/usr/lib/{ad}"],
                   [("python3", "3.12", 4 | 8)], postin=skript,
                   postun=skript)
    hədəf = çıxış / f"{ad}-{v}-1.noarch.rpm"
    hədəf.write_bytes(data)
    return hədəf


# ── AppImage ──────────────────────────────────────────────────────────

APPIMAGE_RUNTIME = ("https://github.com/AppImage/type2-runtime/releases/"
                    "download/continuous/runtime-{arx}")
PBS_BURAXILIŞ = "20241016"
PBS_URL = ("https://github.com/astral-sh/python-build-standalone/releases/"
           "download/{b}/cpython-{v}+{b}-{arx}-unknown-linux-gnu-"
           "install_only.tar.gz")
ARXİTEKTURALAR = ("x86_64", "aarch64")


def _endir(url: str, yol: Path, yoxla) -> Path:
    """Bir dəfə endirir və keşləyir; `yoxla(məzmun_yolu)` doğrulayır."""
    if yol.is_file():
        return yol
    yol.parent.mkdir(parents=True, exist_ok=True)
    müvəqqəti = yol.with_suffix(yol.suffix + ".yeni")
    with urllib.request.urlopen(url, timeout=300) as c, \
            open(müvəqqəti, "wb") as f:
        shutil.copyfileobj(c, f)
    yoxla(müvəqqəti)
    müvəqqəti.replace(yol)
    return yol


def _appimage_runtime(keş: Path, arx: str) -> bytes:
    öz = os.environ.get("ALQOR_APPIMAGE_RUNTIME")
    if öz:
        return Path(öz).read_bytes()

    def yoxla(p: Path) -> None:
        if p.read_bytes()[:4] != b"\x7fELF":
            raise RuntimeError("endirilən AppImage runtime ELF deyil")
    return _endir(APPIMAGE_RUNTIME.format(arx=arx),
                  keş / f"appimage-runtime-{arx}", yoxla).read_bytes()


def _python_müstəqil(keş: Path, arx: str
                     ) -> tuple[dict[str, tuple[bytes, int]], dict[str, str]]:
    """python-build-standalone → ({"usr/python/…": (məzmun, rejim)},
    {simvolik keçid: hədəf})"""
    def yoxla(p: Path) -> None:
        with tarfile.open(p) as t:
            if "python/bin/python3" not in t.getnames():
                raise RuntimeError("endirilən fayl Python paylaması deyil")
    v = PYTHON_VERSİYASI
    tar = _endir(PBS_URL.format(b=PBS_BURAXILIŞ, v=v, arx=arx),
                 keş / f"python-{v}-{arx}-linux.tar.gz", yoxla)
    n: dict[str, tuple[bytes, int]] = {}
    keçidlər: dict[str, str] = {}
    with tarfile.open(tar) as t:
        for m in t.getmembers():
            ad = m.name
            if not ad.startswith("python/") or ".." in ad.split("/"):
                continue
            # sınaqlar və idle lazım deyil — ölçü yarıya enir
            if any(h in ad for h in ("/test/", "/idlelib/", "/tkinter/test",
                                     "/__pycache__/", "/ensurepip/")):
                continue
            hədəf = "usr/" + ad
            if m.issym():
                keçidlər[hədəf] = m.linkname
            elif m.isfile():
                n[hədəf] = (t.extractfile(m).read(), m.mode & 0o777)
    return n, keçidlər


_APPRUN = """#!/bin/sh
# {başlıq} — AppImage başladıcısı (Alqor)
HERE="$(dirname "$(readlink -f "$0")")"
export PYTHONIOENCODING=utf-8
for p in "$HERE/usr/python/bin/python3" python3.13 python3.12 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c \
      'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
    exec "$p" "$HERE/usr/lib/{ad}/{ad}.pyz" {arq} "$@"
  fi
done
msg="{başlıq} üçün Python 3.12+ lazımdır: https://www.python.org/downloads/"
echo "$msg" >&2
command -v zenity >/dev/null 2>&1 && zenity --error --text="$msg"
command -v kdialog >/dev/null 2>&1 && kdialog --error "$msg"
exit 1
"""


def appimage(t: Tətbiq, çıxış: Path, arx: str = "x86_64",
             python_daxil: bool = False, keş: Path | None = None) -> Path:
    """Universal Linux paketi: `chmod +x …AppImage && ./…AppImage`."""
    from ._qur_squashfs import squashfs
    if arx not in ARXİTEKTURALAR:
        raise ValueError(f"arxitektura: {', '.join(ARXİTEKTURALAR)}")
    keş = keş or Path.home() / ".cache" / "alqor"
    ad = t.sistem_adı
    fayllar = _linux_fayllar(t)
    del fayllar[f"usr/bin/{ad}"]
    fayllar["AppRun"] = (_APPRUN.format(
        başlıq=t.başlıq, ad=ad, arq=" ".join(t.arqumentlər)).encode(), 0o755)
    fayllar[f"{ad}.desktop"] = (_desktop(t, ad, ad), 0o644)
    keçidlər = {}
    if t.png and t.png.is_file():
        fayllar[f"{ad}.png"] = (t.png.read_bytes(), 0o644)
        keçidlər[".DirIcon"] = f"{ad}.png"
    if python_daxil:
        py, py_keçidlər = _python_müstəqil(keş, arx)
        fayllar.update(py)
        keçidlər.update(py_keçidlər)
    imaj = squashfs(fayllar, keçidlər)
    hədəf = çıxış / (re.sub(r"[^A-Za-z0-9._-]+", "_",
                            t.başlıq.translate(_TRANSLİT)).strip("_")
                     + f"-{t.versiya_təmiz}-{arx}.AppImage")
    hədəf.write_bytes(_appimage_runtime(keş, arx) + imaj)
    hədəf.chmod(0o755)
    return hədəf


def _xml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ═══════════════════════════════════════════════════════════════════════
#  Windows — zip (PowerShell quraşdırıcısı) + Inno Setup skripti
# ═══════════════════════════════════════════════════════════════════════

_PS_QURAŞDIR = r'''# {başlıq} — quraşdırıcı (Alqor `qur --quraşdırıcı` yaradıb)
# İstifadəçi səviyyəsində quraşdırır — idarəçi hüququ lazım deyil.
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Ad = "{ad}"
$Basliq = "{başlıq_ps}"
$Menbe = $PSScriptRoot
trap {{
    Write-Host "✖ Quraşdırma alınmadı: $_" -ForegroundColor Red
    Read-Host "Bağlamaq üçün Enter basın"
    exit 1
}}
$Hedef = Join-Path $env:LOCALAPPDATA "Programs\$Ad"

function Python-Tap {{
    if (Test-Path (Join-Path $Hedef "python\pythonw.exe")) {{ return $null }}
    foreach ($a in @("py", "pythonw", "python")) {{
        $k = Get-Command $a -ErrorAction SilentlyContinue
        if ($k -and $k.Source -notlike "*WindowsApps*") {{ return $k.Source }}
    }}
    Write-Host "✖ Python 3.12+ tapılmadı: https://www.python.org/downloads/" -ForegroundColor Red
    Read-Host "Bağlamaq üçün Enter"
    exit 1
}}

Write-Host "→ $Basliq quraşdırılır: $Hedef"
if (Test-Path $Hedef) {{ Remove-Item $Hedef -Recurse -Force }}
New-Item -ItemType Directory -Force -Path $Hedef | Out-Null
Copy-Item (Join-Path $Menbe "*") $Hedef -Recurse -Force
Python-Tap | Out-Null

$Baslat = Join-Path $Hedef "$Ad.cmd"
$Ikon = Join-Path $Hedef "ikon.ico"
$Sh = New-Object -ComObject WScript.Shell
function Qisayol($yol) {{
    $q = $Sh.CreateShortcut($yol)
    $q.TargetPath = $Baslat
    $q.WorkingDirectory = $Hedef
    if (Test-Path $Ikon) {{ $q.IconLocation = $Ikon }}
    $q.WindowStyle = {pəncərə_stili}
    $q.Save()
}}
$Menyu = Join-Path ([Environment]::GetFolderPath("Programs")) "$Basliq.lnk"
Qisayol $Menyu
Qisayol (Join-Path ([Environment]::GetFolderPath("Desktop")) "$Basliq.lnk")

# Fayl əlaqələri (yalnız bu istifadəçi üçün)
foreach ($u in @({uzantılar})) {{
    $sinif = "$Ad$u"
    New-Item -Force "HKCU:\Software\Classes\$u" | Out-Null
    Set-ItemProperty "HKCU:\Software\Classes\$u" "(default)" $sinif
    New-Item -Force "HKCU:\Software\Classes\$sinif\shell\open\command" | Out-Null
    Set-ItemProperty "HKCU:\Software\Classes\$sinif" "(default)" "$Basliq faylı"
    New-Item -Force "HKCU:\Software\Classes\$sinif\DefaultIcon" | Out-Null
    Set-ItemProperty "HKCU:\Software\Classes\$sinif\DefaultIcon" "(default)" "$Ikon"
    Set-ItemProperty "HKCU:\Software\Classes\$sinif\shell\open\command" "(default)" "`"$Baslat`" `"%1`""
}}

# "Proqramlar və xüsusiyyətlər"-də silmə
$Sil = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$Ad"
New-Item -Force $Sil | Out-Null
Set-ItemProperty $Sil "DisplayName" $Basliq
Set-ItemProperty $Sil "DisplayVersion" "{versiya}"
Set-ItemProperty $Sil "Publisher" "{naşir_ps}"
Set-ItemProperty $Sil "DisplayIcon" $Ikon
Set-ItemProperty $Sil "InstallLocation" $Hedef
Set-ItemProperty $Sil "UninstallString" "powershell -NoProfile -ExecutionPolicy Bypass -File `"$Hedef\sil.ps1`""
Set-ItemProperty $Sil "NoModify" 1 -Type DWord
Set-ItemProperty $Sil "NoRepair" 1 -Type DWord

Write-Host "✓ $Basliq quraşdırıldı — Başlat menyusunda və masaüstündə." -ForegroundColor Green
Read-Host "Bağlamaq üçün Enter basın"
'''

_PS_SİL = r'''# {başlıq} — silmə
$ErrorActionPreference = "SilentlyContinue"
$Ad = "{ad}"
$Basliq = "{başlıq_ps}"
Remove-Item (Join-Path ([Environment]::GetFolderPath("Programs")) "$Basliq.lnk")
Remove-Item (Join-Path ([Environment]::GetFolderPath("Desktop")) "$Basliq.lnk")
foreach ($u in @({uzantılar})) {{
    Remove-Item -Recurse "HKCU:\Software\Classes\$Ad$u"
    if ((Get-ItemProperty "HKCU:\Software\Classes\$u")."(default)" -eq "$Ad$u") {{
        Remove-Item -Recurse "HKCU:\Software\Classes\$u"
    }}
}}
Remove-Item -Recurse "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$Ad"
$Hedef = Join-Path $env:LOCALAPPDATA "Programs\$Ad"
Set-Location $env:TEMP
Remove-Item -Recurse -Force $Hedef
Write-Host "✓ $Basliq silindi."
'''

_CMD = '''@echo off
rem {ad} - Alqor tetbiqi (qur --qurasdirici yaradib)
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "K=%~dp0"
if exist "%K%python\\{python_exe}" (
    {start}"%K%python\\{python_exe}" "%K%{ad}.pyz" {arq} %*
    exit /b %errorlevel%
)
where {py} >nul 2>nul
if %errorlevel%==0 (
    {start}{py} -3 "%K%{ad}.pyz" {arq} %*
) else (
    {start}{python_sistem} "%K%{ad}.pyz" {arq} %*
)
exit /b %errorlevel%
'''

_ISS = '''; {başlıq} — Inno Setup skripti (Alqor `qur --quraşdırıcı` yaradıb)
; Qurmaq: iscc "{fayl}"
[Setup]
AppId={{{{{app_id}}}
AppName={başlıq}
AppVersion={versiya}
AppPublisher={naşir}
DefaultDirName={{localappdata}}\\Programs\\{ad}
DefaultGroupName={başlıq}
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename={ad}-{versiya}-setup
SetupIconFile={mənbə}\\ikon.ico
UninstallDisplayIcon={{app}}\\ikon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\\Turkish.isl"

[Files]
Source: "{mənbə}\\*"; DestDir: "{{app}}"; Flags: recursesubdirs ignoreversion; Excludes: "qurasdir.ps1,Qurasdir.cmd,sil.ps1"

[Icons]
Name: "{{group}}\\{başlıq}"; Filename: "{{app}}\\{ad}.cmd"; IconFilename: "{{app}}\\ikon.ico"; Flags: {pəncərə_iss}
Name: "{{userdesktop}}\\{başlıq}"; Filename: "{{app}}\\{ad}.cmd"; IconFilename: "{{app}}\\ikon.ico"; Flags: {pəncərə_iss}

[Registry]
{qeydiyyat}
'''


def _ps(s: str) -> str:
    return s.replace("`", "``").replace('"', '`"').replace("$", "`$")


def _python_embed(keş: Path) -> Path:
    """python.org-dan Windows embeddable paylamasını endirir (keşlənir)."""
    ad = f"python-{PYTHON_VERSİYASI}-embed-amd64.zip"
    yol = keş / ad
    if not yol.is_file():
        keş.mkdir(parents=True, exist_ok=True)
        url = (f"https://www.python.org/ftp/python/{PYTHON_VERSİYASI}/"
               f"{ad}")
        müvəqqəti = yol.with_suffix(".yeni")
        with urllib.request.urlopen(url, timeout=120) as c, \
                open(müvəqqəti, "wb") as f:
            shutil.copyfileobj(c, f)
        with zipfile.ZipFile(müvəqqəti) as z:
            if "python.exe" not in z.namelist():
                raise RuntimeError("endirilən fayl Python paylaması deyil")
        müvəqqəti.replace(yol)
    return yol


def windows(t: Tətbiq, çıxış: Path, python_daxil: bool = False,
            keş: Path | None = None) -> list[Path]:
    ad = t.sistem_adı
    qovluq = çıxış / f"{ad}-windows"
    if qovluq.exists():
        shutil.rmtree(qovluq)
    qovluq.mkdir(parents=True)
    shutil.copyfile(t.pyz, qovluq / f"{ad}.pyz")
    if t.ico and t.ico.is_file():
        shutil.copyfile(t.ico, qovluq / "ikon.ico")
    pəncərəli = not t.konsol
    (qovluq / f"{ad}.cmd").write_text(_CMD.format(
        başlıq=t.başlıq, ad=ad, arq=" ".join(t.arqumentlər),
        python_exe="pythonw.exe" if pəncərəli else "python.exe",
        python_sistem="pythonw" if pəncərəli else "python",
        py="pyw" if pəncərəli else "py",
        start='start "" ' if pəncərəli else ""
    ).replace("\n", "\r\n"), encoding="ascii")
    uz = ", ".join(f'"{u}"' for u in t.uzantılar)
    f = dict(ad=ad, başlıq=t.başlıq, başlıq_ps=_ps(t.başlıq),
             naşir_ps=_ps(t.naşir), versiya=t.versiya_təmiz, uzantılar=uz,
             pəncərə_stili=7 if pəncərəli else 1)
    # PowerShell 5.1 UTF-8-i yalnız BOM ilə tanıyır
    # Fayl adları ASCII-dir: cmd.exe .cmd faylını OEM kod səhifəsində
    # oxuyur — `ş`, `ı` olan ad pozulur və skript tapılmır
    (qovluq / "qurasdir.ps1").write_text(
        "﻿" + _PS_QURAŞDIR.format(**f).replace("\n", "\r\n"),
        encoding="utf-8")
    (qovluq / "sil.ps1").write_text(
        "﻿" + _PS_SİL.format(**f).replace("\n", "\r\n"),
        encoding="utf-8")
    (qovluq / "Qurasdir.cmd").write_text(
        "@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "
        '"%~dp0qurasdir.ps1"\r\nif %errorlevel% neq 0 pause\r\n',
        encoding="ascii")
    if python_daxil:
        embed = _python_embed(keş or Path.home() / ".cache" / "alqor")
        py = qovluq / "python"
        with zipfile.ZipFile(embed) as z:
            z.extractall(py)
        # `._pth` — paketimiz və standart kitabxana axtarış yolunda olsun
        for pth in py.glob("python*._pth"):
            sətirlər = [s for s in pth.read_text().splitlines()
                        if s.strip() and not s.startswith("#")]
            sətirlər.append(f"..\\{ad}.pyz")
            sətirlər.append("import site")
            pth.write_text("\r\n".join(sətirlər) + "\r\n")

    # Inno Setup skripti
    qeyd = []
    for u in t.uzantılar:
        sinif = f"{ad}{u}"
        qeyd += [
            f'Root: HKCU; Subkey: "Software\\Classes\\{u}"; ValueType: string; '
            f'ValueName: ""; ValueData: "{sinif}"; Flags: uninsdeletevalue',
            f'Root: HKCU; Subkey: "Software\\Classes\\{sinif}"; ValueType: '
            f'string; ValueName: ""; ValueData: "{t.başlıq} faylı"; '
            'Flags: uninsdeletekey',
            f'Root: HKCU; Subkey: "Software\\Classes\\{sinif}\\DefaultIcon"; '
            'ValueType: string; ValueName: ""; ValueData: "{app}\\ikon.ico"',
            f'Root: HKCU; Subkey: "Software\\Classes\\{sinif}\\shell\\open\\'
            f'command"; ValueType: string; ValueName: ""; ValueData: '
            f'"""{{app}}\\{ad}.cmd"" ""%1"""']
    iss = çıxış / f"{ad}-{t.versiya_təmiz}-windows.iss"
    app_id = uuid.uuid5(uuid.NAMESPACE_URL, f"alqor:{ad}").__str__().upper()
    iss.write_text("﻿" + _ISS.format(
        başlıq=t.başlıq, versiya=t.versiya_təmiz, naşir=t.naşir, ad=ad,
        app_id=app_id, mənbə=f"{ad}-windows", fayl=iss.name,
        pəncərə_iss="runminimized" if pəncərəli else "",
        qeydiyyat="\n".join(qeyd)).replace("\n", "\r\n"), encoding="utf-8")

    zip_yolu = çıxış / f"{ad}-{t.versiya_təmiz}-windows.zip"
    with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(qovluq.rglob("*")):
            if p.is_file():
                z.write(p, f"{ad}/{p.relative_to(qovluq).as_posix()}")
    nəticə = [zip_yolu, iss]
    iscc = shutil.which("iscc") or shutil.which("ISCC.exe")
    if iscc:
        import subprocess
        subprocess.run([iscc, "/Q", str(iss)], cwd=str(çıxış), check=True)
        nəticə.append(çıxış / f"{ad}-{t.versiya_təmiz}-setup.exe")
    return nəticə


# ═══════════════════════════════════════════════════════════════════════
#  macOS — .app
# ═══════════════════════════════════════════════════════════════════════

def _app_fayllar(t: Tətbiq) -> dict[str, tuple[bytes, int]]:
    """macOS `.app` paketinin faylları: {yol: (məzmun, rejim)}"""
    ad = t.sistem_adı
    app = f"{t.başlıq}.app/Contents"
    başladıcı = (
        "#!/bin/sh\n"
        'K="$(cd "$(dirname "$0")/../Resources" && pwd)"\n'
        "export PYTHONIOENCODING=utf-8\n"
        "for p in python3.13 python3.12 python3 /usr/local/bin/python3 "
        "/opt/homebrew/bin/python3; do\n"
        '  if command -v "$p" >/dev/null 2>&1; then\n'
        f'    exec "$p" "$K/{ad}.pyz" {" ".join(t.arqumentlər)} "$@"\n'
        "  fi\ndone\n"
        "osascript -e 'display alert \"Python 3.12+ lazımdır\" message "
        "\"https://www.python.org/downloads/\"'\nexit 1\n")
    sənəd_növləri = "".join(
        "    <dict><key>CFBundleTypeExtensions</key><array><string>"
        f"{u.lstrip('.')}</string></array><key>CFBundleTypeRole</key>"
        "<string>Editor</string></dict>\n" for u in t.uzantılar)
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
        '"-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>CFBundleName</key><string>{_xml(t.başlıq)}</string>\n"
        f"  <key>CFBundleDisplayName</key><string>{_xml(t.başlıq)}</string>\n"
        f"  <key>CFBundleIdentifier</key><string>az.alqor.{ad}</string>\n"
        f"  <key>CFBundleVersion</key><string>{t.versiya_təmiz}</string>\n"
        "  <key>CFBundleShortVersionString</key>"
        f"<string>{t.versiya_təmiz}</string>\n"
        f"  <key>CFBundleExecutable</key><string>{ad}</string>\n"
        "  <key>CFBundlePackageType</key><string>APPL</string>\n"
        "  <key>CFBundleIconFile</key><string>ikon.png</string>\n"
        "  <key>LSMinimumSystemVersion</key><string>11.0</string>\n"
        + (f"  <key>CFBundleDocumentTypes</key><array>\n{sənəd_növləri}"
           "  </array>\n" if t.uzantılar else "")
        + "</dict></plist>\n")
    n = {f"{app}/Info.plist": (plist.encode("utf-8"), 0o644),
         f"{app}/MacOS/{ad}": (başladıcı.encode(), 0o755),
         f"{app}/Resources/{ad}.pyz": (t.pyz.read_bytes(), 0o644)}
    if t.png and t.png.is_file():
        n[f"{app}/Resources/ikon.png"] = (t.png.read_bytes(), 0o644)
    return n


def macos(t: Tətbiq, çıxış: Path) -> Path:
    """`.app` paketi zip-də (macOS Finder açır, icazələr saxlanır)."""
    hədəf = çıxış / f"{t.sistem_adı}-{t.versiya_təmiz}-macos.zip"
    with zipfile.ZipFile(hədəf, "w", zipfile.ZIP_DEFLATED) as z:
        for yol, (d, rejim) in _app_fayllar(t).items():
            i = zipfile.ZipInfo(yol, time.localtime()[:6])
            i.external_attr = (stat.S_IFREG | rejim) << 16
            i.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(i, d)
    return hədəf


def dmg(t: Tətbiq, çıxış: Path) -> Path:
    """macOS disk imajı: `.app` + «Applications» keçidi (sürüklə-burax).

    macOS-da `hdiutil` varsa onunla (HFS+), başqa sistemlərdə saf Python
    ilə (ISO 9660 + Rock Ridge, UDIF zlib) yaradılır."""
    hədəf = çıxış / f"{t.sistem_adı}-{t.versiya_təmiz}.dmg"
    fayllar = _app_fayllar(t)
    cild = re.sub(r"[^A-Z0-9_]", "_",
                  t.başlıq.translate(_TRANSLİT).upper())[:32] or "ALQOR"
    hdiutil = shutil.which("hdiutil")
    if hdiutil and os.environ.get("ALQOR_DMG_SAF") != "1":
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as q:
            for yol, (d, rejim) in fayllar.items():
                f = Path(q) / yol
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(d)
                f.chmod(rejim)
            os.symlink("/Applications", Path(q) / "Applications")
            hədəf.unlink(missing_ok=True)
            subprocess.run([hdiutil, "create", "-volname", t.başlıq,
                            "-srcfolder", q, "-ov", "-format", "UDZO",
                            str(hədəf)], check=True, capture_output=True)
        return hədəf
    from ._qur_dmg import iso9660, udif
    imaj = iso9660(fayllar, {"Applications": "/Applications"}, cild)
    hədəf.write_bytes(udif(imaj, t.başlıq))
    return hədəf


PLATFORMALAR = ("linux", "windows", "macos")
# Platforma → formatlar (`--format` ilə daraltmaq olar)
FORMATLAR = {"linux": ("deb", "rpm", "appimage"),
             "windows": ("windows",), "macos": ("app", "dmg")}


def qur(t: Tətbiq, çıxış: Path, platformalar: tuple[str, ...] = PLATFORMALAR,
        python_daxil: bool = False,
        formatlar: tuple[str, ...] | None = None,
        xəbərdarlıq=None) -> list[Path]:
    """Quraşdırıcıları yaradır. Endirmə tələb edən format (AppImage
    runtime) alınmasa digərləri yenə qurulur, `xəbərdarlıq` çağırılır."""
    çıxış.mkdir(parents=True, exist_ok=True)
    seçilən = [f for p in platformalar for f in FORMATLAR.get(p, ())
               if formatlar is None or f in formatlar]
    n: list[Path] = []
    for f in seçilən:
        if f == "deb":
            n.append(deb(t, çıxış))
        elif f == "rpm":
            n.append(rpm(t, çıxış))
        elif f == "appimage":
            try:
                n.append(appimage(t, çıxış, python_daxil=python_daxil))
            except (OSError, RuntimeError) as x:
                if xəbərdarlıq is None:
                    raise
                xəbərdarlıq(f"AppImage qurulmadı (runtime endirilmədi: {x}) "
                            "— ALQOR_APPIMAGE_RUNTIME ilə yerli fayl verin")
        elif f == "windows":
            n += windows(t, çıxış, python_daxil)
        elif f == "app":
            n.append(macos(t, çıxış))
        elif f == "dmg":
            n.append(dmg(t, çıxış))
    return n


# ═══════════════════════════════════════════════════════════════════════
#  Alqor Studio-nun öz quraşdırıcısı
# ═══════════════════════════════════════════════════════════════════════

_STUDIO_BAŞLADICI = '''\
# Alqor Studio — quraşdırılmış tətbiq
import hashlib
import os
import sys
import zipfile
from pathlib import Path


def _aç() -> Path:
    """Studio statik fayllar və alt proseslər (önbaxış, icra) üçün həqiqi
    fayl yolları gözləyir — paket bir dəfə keş qovluğuna açılır."""
    paket = Path(sys.argv[0]).resolve()
    h = hashlib.sha256(paket.read_bytes()).hexdigest()[:16]
    baza = os.environ.get("ALQOR_KES") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.cache"),
        "alqor")
    hədəf = Path(baza) / f"studio-{h}"
    if not (hədəf / ".hazir").exists():
        with zipfile.ZipFile(paket) as z:
            z.extractall(hədəf)
        (hədəf / ".hazir").write_text("1")
    return hədəf


def main() -> int:
    kök = _aç()
    if sys.stdout is None or sys.stderr is None:
        # `pythonw` (konsolsuz) — çıxış jurnal faylına gedir
        jurnal = open(kök / "studio.log", "a", encoding="utf-8")
        sys.stdout = sys.stdout or jurnal
        sys.stderr = sys.stderr or jurnal
    sys.path.insert(0, str(kök))
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import alqorc
    arq = sys.argv[1:]
    # Fayl əlaqəsi: `.alq` faylı → onun qovluğu Studio-da açılır
    if arq and Path(arq[0]).is_file():
        arq = [str(Path(arq[0]).resolve().parent), "--fayl",
               Path(arq[0]).name] + arq[1:]
    elif not arq:
        sənədlər = Path.home() / "Documents" / "Alqor"
        sənədlər.mkdir(parents=True, exist_ok=True)
        arq = [str(sənədlər)]
    return alqorc.əmr_studio(arq)


if __name__ == "__main__":
    sys.exit(main())
'''


def studio_pyz(alqorc_kökü: Path, hədəf: Path) -> Path:
    hədəf.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(hədəf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("__main__.py", _STUDIO_BAŞLADICI)
        z.write(alqorc_kökü / "alqorc.py", "alqorc.py")
        for paket in ("alqor", "studio"):
            for f in sorted((alqorc_kökü / paket).rglob("*")):
                if not f.is_file() or "__pycache__" in f.parts \
                        or f.suffix == ".pyc":
                    continue
                z.write(f, f.relative_to(alqorc_kökü).as_posix())
    return hədəf


def studio(alqorc_kökü: Path, çıxış: Path,
           platformalar: tuple[str, ...] = PLATFORMALAR,
           python_daxil: bool = False,
           formatlar: tuple[str, ...] | None = None,
           xəbərdarlıq=None) -> list[Path]:
    from studio import VERSIYA as versiya
    res = alqorc_kökü / "alqor" / "resurslar"
    pyz = studio_pyz(alqorc_kökü, çıxış / "alqor-studio.pyz")
    t = Tətbiq(ad="alqor-studio", başlıq="Alqor Studio", versiya=versiya,
               pyz=pyz, təsvir="Alqor proqramlaşdırma dili üçün IDE",
               naşir="Alqor", png=res / "ikon-256.png", ico=res / "alqor.ico",
               konsol=False, uzantılar=[".alq", ".alqor"])
    return qur(t, çıxış, platformalar, python_daxil, formatlar, xəbərdarlıq)
