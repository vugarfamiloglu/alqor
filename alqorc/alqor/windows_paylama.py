"""
Alqor-un Windows quraşdırıcısı — `alqor qur --alqor [çıxış]`.

Bir quraşdırıcıda hər şey:
  • daxili Python (python.org "embeddable" paylaması) — istifadəçinin
    Python qurmasına ehtiyac yoxdur
  • `alqor`, `alqorpm`, `alqorlint`, `alqorfmt`, `alqorls` əmrləri —
    istifadəçi PATH-ına yazılır (terminaldan `alqor yeni layihəm`)
  • Alqor Studio — Başlat menyusu, istəyə görə masaüstü, `.alq` əlaqəsi
  • nümunələr və bələdçilər

İdarəçi hüququ tələb olunmur: `%LOCALAPPDATA%\\Programs\\Alqor`.

Çıxış (`qurma/` altında):
  alqor-windows/                      quraşdırılacaq qovluq
  alqor-<v>-windows-portativ.zip      quraşdırmasız işlədilən versiya
  alqor-<v>.iss                       Inno Setup skripti
  AlqorQurasdirici-<v>.exe            `iscc` varsa (Windows / CI)
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from . import VERSIYA

#  Quraşdırıcının sabit identifikatoru — yeniləmə köhnəni əvəz etsin
APP_ID = "8E4C2D7A-3B1F-4A6E-9C55-A1C0B0D7E9F3"

ƏMRLƏR = {
    "alqor": "",
    "alqorpm": "pm",
    "alqorlint": "lint",
    "alqorfmt": "format",
    "alqorls": "ls",
}

_CMD = """@echo off
rem {ad} - Alqor ({versiya})
setlocal
set "ALQOR_KOK=%~dp0.."
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"%ALQOR_KOK%\\python\\python.exe" "%ALQOR_KOK%\\alqorc\\alqorc.py" {əmr}%*
exit /b %errorlevel%
"""

_TERMİNAL = """@echo off
rem Alqor terminali: PATH-da alqor emrleri ile
set "PATH=%~dp0;%PATH%"
chcp 65001 >nul
echo Alqor {versiya} - terminal
echo   alqor yeni layihem --sablon konsol   yeni layihe
echo   alqor islet                         layiheni isle sal
echo   alqor komek                         butun emrler
echo.
"""

#  Studio başladıcısı — `pythonw.exe` ilə konsolsuz açılır
_STUDIO = '''\
"""Alqor Studio — quraşdırılmış Alqor-dan işə salınır."""
import os
import shutil
import sys
from pathlib import Path

KÖK = Path(__file__).resolve().parent.parent


def _sənədlər() -> Path:
    """İstifadəçinin «Sənədlər» qovluğu (OneDrive yönləndirməsi ilə)."""
    try:
        import ctypes
        from ctypes import wintypes
        bufer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # CSIDL_PERSONAL = 5
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, bufer) == 0:
            return Path(bufer.value)
    except (AttributeError, OSError):
        pass
    return Path.home() / "Documents"


def main() -> int:
    if sys.stdout is None or sys.stderr is None:
        jurnal_q = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Alqor"
        jurnal_q.mkdir(parents=True, exist_ok=True)
        jurnal = open(jurnal_q / "studio.log", "a", encoding="utf-8")
        sys.stdout = sys.stdout or jurnal
        sys.stderr = sys.stderr or jurnal
    sys.path.insert(0, str(KÖK / "alqorc"))
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PATH"] = str(KÖK / "bin") + os.pathsep + os.environ.get("PATH", "")
    import alqorc
    arq = sys.argv[1:]
    if arq and Path(arq[0]).is_file():
        arq = [str(Path(arq[0]).resolve().parent), "--fayl",
               Path(arq[0]).name] + arq[1:]
    elif not arq:
        iş = _sənədlər() / "Alqor"
        if not iş.exists():
            iş.mkdir(parents=True)
            nümunələr = KÖK / "numuneler"
            if nümunələr.is_dir():
                shutil.copytree(nümunələr, iş / "nümunələr")
        arq = [str(iş)]
    return alqorc.əmr_studio(arq)


if __name__ == "__main__":
    sys.exit(main())
'''

_ISS = r'''; Alqor {versiya} — Windows quraşdırıcısı (alqor qur --alqor yaradıb)
; Qurmaq: iscc "{iss_adı}"
#define Ver "{versiya}"

[Setup]
AppId={{{{{app_id}}}
AppName=Alqor
AppVersion={{#Ver}}
AppVerName=Alqor {{#Ver}}
AppPublisher=Alqor
AppPublisherURL=https://alqor.vuqar.pro
AppSupportURL=https://github.com/vugarfamiloglu/alqor/issues
DefaultDirName={{localappdata}}\Programs\Alqor
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=.
OutputBaseFilename=AlqorQurasdirici-{{#Ver}}
SetupIconFile={mənbə}\ikon.ico
UninstallDisplayIcon={{app}}\ikon.ico
UninstallDisplayName=Alqor {{#Ver}}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
ChangesEnvironment=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0

[Messages]
SetupAppTitle=Alqor quraşdırıcısı
SetupWindowTitle=Alqor %1 — quraşdırma
WelcomeLabel1=Alqor-a xoş gəlmisiniz
WelcomeLabel2=Bu proqram kompüterinizə [name/ver] quraşdıracaq: Azərbaycan dilində proqramlaşdırma dili, Alqor Studio və terminal əmrləri.%n%nPython qurmağa ehtiyac yoxdur — hər şey daxildir.
ButtonBack=< &Geri
ButtonNext=&Növbəti >
ButtonInstall=&Quraşdır
ButtonCancel=İmtina
ButtonFinish=&Bitir
ButtonBrowse=&Seç...
SelectDirLabel3=Alqor bu qovluğa quraşdırılacaq.
SelectTasksDesc=Əlavə imkanlar
SelectTasksLabel2=Quraşdırma zamanı nələr edilsin?
ReadyLabel1=Quraşdırmaya hazırdır
ReadyLabel2a=Davam etmək üçün «Quraşdır» düyməsini basın.
InstallingLabel=Alqor quraşdırılır, bir az gözləyin...
FinishedHeadingLabel=Alqor quraşdırıldı
FinishedLabelNoIcons=Alqor kompüterinizə quraşdırıldı.
FinishedLabel=Alqor kompüterinizə quraşdırıldı. Studio-nu Başlat menyusundan açın; terminalda «alqor kömək» yazın.
ClickFinish=Bağlamaq üçün «Bitir» düyməsini basın.
ConfirmUninstall=%1 və onun bütün komponentləri silinsin?
UninstalledAll=%1 kompüterinizdən silindi.
ExitSetupTitle=Quraşdırmadan çıxış
ExitSetupMessage=Quraşdırma bitməyib. Çıxsanız, Alqor quraşdırılmayacaq.%n%nÇıxılsın?

[Tasks]
Name: "path"; Description: "«alqor» əmrlərini PATH-a əlavə et (terminaldan işlətmək üçün)"
Name: "assoc"; Description: ".alq fayllarını Alqor Studio ilə aç"
Name: "desktopicon"; Description: "Masaüstündə Alqor Studio qısayolu"

[Files]
Source: "{mənbə}\*"; DestDir: "{{app}}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{{autoprograms}}\Alqor Studio"; Filename: "{{app}}\python\pythonw.exe"; Parameters: """{{app}}\bin\studio.pyw"""; WorkingDir: "{{app}}"; IconFilename: "{{app}}\ikon.ico"; Comment: "Alqor proqramlaşdırma mühiti"
Name: "{{autoprograms}}\Alqor terminalı"; Filename: "{{cmd}}"; Parameters: "/k ""{{app}}\bin\alqor-terminal.cmd"""; WorkingDir: "{{userdocs}}"; IconFilename: "{{app}}\ikon.ico"
Name: "{{autoprograms}}\Alqor sənədləri"; Filename: "{{app}}\sened\index.html"; IconFilename: "{{app}}\ikon.ico"; Comment: "Dərsliklər, arayış, nümunələr — internetsiz"
Name: "{{autodesktop}}\Alqor Studio"; Filename: "{{app}}\python\pythonw.exe"; Parameters: """{{app}}\bin\studio.pyw"""; WorkingDir: "{{app}}"; IconFilename: "{{app}}\ikon.ico"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.alq"; ValueType: string; ValueName: ""; ValueData: "Alqor.Fayl"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.alqor"; ValueType: string; ValueName: ""; ValueData: "Alqor.Fayl"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Alqor.Fayl"; ValueType: string; ValueName: ""; ValueData: "Alqor proqramı"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Alqor.Fayl\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{{app}}\ikon.ico"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Alqor.Fayl\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{{app}}\python\pythonw.exe"" ""{{app}}\bin\studio.pyw"" ""%1"""; Tasks: assoc

[Run]
Filename: "{{app}}\python\pythonw.exe"; Parameters: """{{app}}\bin\studio.pyw"""; Description: "Alqor Studio-nu indi aç"; Flags: postinstall nowait skipifsilent
Filename: "{{app}}\sened\ilk-addimlar.html"; Description: "«İlk addımlar» sənədini oxu"; Flags: postinstall shellexec nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}"

[Code]
const
  MuhitAcari = 'Environment';

function PathOxu(): string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, MuhitAcari, 'Path', Result) then
    Result := '';
end;

function PathdaVar(Yol, Qovluq: string): Boolean;
begin
  Result := Pos(';' + Uppercase(Qovluq) + ';', ';' + Uppercase(Yol) + ';') > 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Yol, Bin: string;
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('path') then
  begin
    Bin := ExpandConstant('{{app}}\bin');
    Yol := PathOxu();
    if not PathdaVar(Yol, Bin) then
    begin
      if (Yol <> '') and (Copy(Yol, Length(Yol), 1) <> ';') then
        Yol := Yol + ';';
      RegWriteExpandStringValue(HKEY_CURRENT_USER, MuhitAcari, 'Path', Yol + Bin);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Yol, Bin: string;
  P: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Bin := ExpandConstant('{{app}}\bin');
    Yol := ';' + PathOxu() + ';';
    P := Pos(';' + Uppercase(Bin) + ';', Uppercase(Yol));
    if P > 0 then
    begin
      Delete(Yol, P, Length(Bin) + 1);
      Yol := Copy(Yol, 2, Length(Yol) - 2);
      RegWriteExpandStringValue(HKEY_CURRENT_USER, MuhitAcari, 'Path', Yol);
    end;
  end;
end;
'''


def _kopyala(mənbə: Path, hədəf: Path) -> None:
    shutil.copytree(mənbə, hədəf, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", "sinaq", ".pytest_cache", "qurma"))


def python_daxil_et(hədəf: Path, keş: Path | None = None,
                    arxiv: Path | None = None) -> Path:
    """Windows x64 Python-u `hədəf/` qovluğuna açır (python.exe, Lib…)."""
    import tarfile
    from .qurasdirici import PBS_BURAXILIŞ, PBS_URL, PYTHON_VERSİYASI, _endir
    keş = keş or Path.home() / ".cache" / "alqor"
    if arxiv is None:
        def yoxla(p: Path) -> None:
            with tarfile.open(p) as t:
                if "python/python.exe" not in t.getnames():
                    raise RuntimeError("endirilən fayl Windows Python deyil")
        arx = "x86_64-pc-windows-msvc"
        arxiv = _endir(PBS_URL.format(b=PBS_BURAXILIŞ, v=PYTHON_VERSİYASI,
                                      arx=arx).replace("-unknown-linux-gnu", ""),
                       keş / f"python-{PYTHON_VERSİYASI}-{arx}.tar.gz", yoxla)
    hədəf.mkdir(parents=True, exist_ok=True)
    if str(arxiv).endswith(".zip"):
        with zipfile.ZipFile(arxiv) as z:
            z.extractall(hədəf)
        return hədəf
    with tarfile.open(arxiv) as t:
        for m in t.getmembers():
            ad = m.name
            if not ad.startswith("python/") or ".." in ad.split("/"):
                continue
            if any(h in ad for h in ("/test/", "/idlelib/", "/__pycache__/",
                                     "/ensurepip/", "/include/", "/libs/",
                                     "/tkinter/test")):
                continue
            if ad.endswith(".pdb") or "/_test" in ad or "/xxlimited" in ad:
                continue
            nisbi = ad[len("python/"):]
            if not nisbi:
                continue
            y = hədəf / nisbi
            if m.isdir():
                y.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                y.parent.mkdir(parents=True, exist_ok=True)
                y.write_bytes(t.extractfile(m).read())
    return hədəf


def versiya_təmiz() -> str:
    v = VERSIYA.split("-")[0]
    return v if v[:1].isdigit() else "0.1.0"


def paylama_qovluğu(alqorc_kökü: Path, çıxış: Path,
                    keş: Path | None = None,
                    python_zip: Path | None = None) -> Path:
    """`alqor-windows/` qovluğunu qurur (quraşdırıcının məzmunu)."""
    repo = alqorc_kökü.parent
    v = versiya_təmiz()
    q = çıxış / "alqor-windows"
    if q.exists():
        shutil.rmtree(q)
    q.mkdir(parents=True)

    # 1. Daxili Python — python-build-standalone (tam paylama, tkinter
    #    daxil); `ALQOR_PYTHON_EMBED` ilə hazır arxiv vermək olar
    python_daxil_et(q / "python", keş, python_zip)

    # 2. Alqor-un özü
    a = q / "alqorc"
    a.mkdir()
    for f in ("alqorc.py", "alqorfmt.py"):
        shutil.copyfile(alqorc_kökü / f, a / f)
    for paket in ("alqor", "studio"):
        _kopyala(alqorc_kökü / paket, a / paket)

    # 3. Əmrlər
    b = q / "bin"
    b.mkdir()
    for ad, əmr in ƏMRLƏR.items():
        (b / f"{ad}.cmd").write_text(
            _CMD.format(ad=ad, versiya=v, əmr=f"{əmr} " if əmr else "")
            .replace("\n", "\r\n"), encoding="ascii")
    (b / "alqor-terminal.cmd").write_text(
        _TERMİNAL.format(versiya=v).replace("\n", "\r\n"), encoding="ascii")
    (b / "studio.pyw").write_text(_STUDIO, encoding="utf-8")

    # 4. Nümunələr, bələdçilər, ikon
    for ad in ("numuneler", "beledci"):
        if (repo / ad).is_dir():
            _kopyala(repo / ad, q / ad)
    # 5. Oflayn sənəd mərkəzi — dərsliklər, arayış, spesifikasiya
    from .sened_merkezi import qur as sənəd_qur
    sənəd_qur(repo, q / "sened")
    shutil.copyfile(alqorc_kökü / "alqor" / "resurslar" / "alqor.ico",
                    q / "ikon.ico")
    if (repo / "README.md").is_file():
        shutil.copyfile(repo / "README.md", q / "README.md")
    return q


def iss_yaz(çıxış: Path, mənbə_adı: str = "alqor-windows") -> Path:
    v = versiya_təmiz()
    iss = çıxış / f"alqor-{v}.iss"
    mətn = _ISS.format(versiya=v, iss_adı=iss.name, app_id=APP_ID,
                       mənbə=mənbə_adı)
    iss.write_text("﻿" + mətn.replace("\n", "\r\n"), encoding="utf-8")
    return iss


def portativ_zip(q: Path, çıxış: Path) -> Path:
    z_yol = çıxış / f"alqor-{versiya_təmiz()}-windows-portativ.zip"
    with zipfile.ZipFile(z_yol, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(q.rglob("*")):
            if p.is_file():
                z.write(p, f"Alqor/{p.relative_to(q).as_posix()}")
    return z_yol


def iscc_tap() -> str | None:
    import os
    for a in ("iscc", "ISCC.exe"):
        if shutil.which(a):
            return shutil.which(a)
    for baza in (os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("ProgramFiles"),
                 os.environ.get("LOCALAPPDATA")):
        if baza:
            for alt in ("Inno Setup 6", "Programs\\Inno Setup 6"):
                p = Path(baza) / alt / "ISCC.exe"
                if p.is_file():
                    return str(p)
    return None


def qur(alqorc_kökü: Path, çıxış: Path, keş: Path | None = None,
        python_zip: Path | None = None, iscc: str | None = None,
        zip_də: bool = True) -> list[Path]:
    çıxış.mkdir(parents=True, exist_ok=True)
    q = paylama_qovluğu(alqorc_kökü, çıxış, keş, python_zip)
    n: list[Path] = []
    if zip_də:
        n.append(portativ_zip(q, çıxış))
    iss = iss_yaz(çıxış, q.name)
    n.append(iss)
    iscc = iscc or iscc_tap()
    if iscc:
        subprocess.run([iscc, "/Q", iss.name], cwd=str(çıxış), check=True)
        n.append(çıxış / f"AlqorQurasdirici-{versiya_təmiz()}.exe")
    return n
