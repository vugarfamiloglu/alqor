# Alqor — nümunəni brauzerdə bir kliklə açır.
#
# İşlətmək: "Brauzerde-ac.cmd" faylına iki dəfə klikləyin.
# Və ya PowerShell-də:
#     .\brauzerde-ac.ps1                 # 08 — vidjetlər (veb, :8081)
#     .\brauzerde-ac.ps1 -Numune 05      # 05 — veb server (:8080)
#     .\brauzerde-ac.ps1 -Numune 06      # 06 — desktop pəncərəsi
#     .\brauzerde-ac.ps1 -Numune studio  # Alqor Studio (IDE)
#     .\brauzerde-ac.ps1 -Yenile:$false  # git-dən yeniləməmək
#
# Pəncərəni bağlayanda server də dayanır.

param(
    [ValidateSet("05", "06", "08", "09", "10", "studio")]
    [string]$Numune = "08",
    [bool]$Yenile = $true
)

$ErrorActionPreference = "Stop"
# Windows konsolu cp1251-dir — Azərbaycan hərfləri üçün UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$Kok = $PSScriptRoot
$Saxe = "main-o96ikp"

function Yaz($mesaj, $reng = "Gray") { Write-Host $mesaj -ForegroundColor $reng }
function Dayan($mesaj) {
    Yaz "✖ $mesaj" "Red"
    Read-Host "Bağlamaq üçün Enter basın"
    exit 1
}

# ── 1. Python ──────────────────────────────────────────────────────────
$Python = $null
foreach ($ad in @("py", "python", "python3")) {
    $k = Get-Command $ad -ErrorAction SilentlyContinue
    if ($k -and $k.Source -notlike "*WindowsApps*") { $Python = $k.Source; break }
}
if (-not $Python) {
    Dayan "Python tapılmadı. https://www.python.org/downloads/ ünvanından 3.12+ quraşdırın (`"Add python.exe to PATH`" işarələnsin)."
}
$PyArg = @()
if ((Split-Path $Python -Leaf) -eq "py.exe") { $PyArg = @("-3") }
$Versiya = & $Python @PyArg -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$Versiya -lt [version]"3.12") {
    Dayan "Python $Versiya köhnədir — Alqor 3.12 və ya yenisini tələb edir."
}
Yaz "✓ Python $Versiya" "Green"

# ── 2. Kodu yenilə ─────────────────────────────────────────────────────
if ($Yenile -and (Get-Command git -ErrorAction SilentlyContinue)) {
    Push-Location $Kok
    # PowerShell 5.1: "Stop" rejimində git-in stderr sətirləri xəta sayılır
    $ErrorActionPreference = "Continue"
    try {
        $cari = (git rev-parse --abbrev-ref HEAD 2>$null)
        $temiz = -not (git status --porcelain 2>$null)
        git fetch --quiet origin $Saxe 2>$null
        if ($cari -ne $Saxe) {
            if ($temiz) {
                Yaz "→ '$Saxe' şaxəsinə keçilir…"
                git checkout --quiet $Saxe 2>$null
                if ($LASTEXITCODE -ne 0) { git checkout --quiet -b $Saxe "origin/$Saxe" }
            } else {
                Yaz "! Yerli dəyişikliklər var — şaxə dəyişdirilmədi ($cari)." "Yellow"
            }
        }
        if ((git rev-parse --abbrev-ref HEAD) -eq $Saxe) {
            git pull --quiet --ff-only origin $Saxe 2>$null
            Yaz "✓ Kod yeniləndi: $(git log --oneline -1)" "Green"
        }
    } catch {
        Yaz "! git yeniləməsi alınmadı — mövcud kodla davam edilir." "Yellow"
    } finally { Pop-Location; $ErrorActionPreference = "Stop" }
}

# ── Alqor Studio — öz pəncərəsini açır ────────────────────────────────
if ($Numune -eq "studio") {
    Yaz "→ Alqor Studio açılır… (pəncərəni bağlayanda bitir)" "Cyan"
    & $Python @PyArg (Join-Path $Kok "alqorc\alqorc.py") studio $Kok
    exit $LASTEXITCODE
}

# ── 3. Nümunə və port ──────────────────────────────────────────────────
$Numuneler = @{
    "05" = @{ Fayl = "05-veb-server.alqor"; Arq = @();        Port = 8080 }
    "06" = @{ Fayl = "06-desktop.alqor";    Arq = @();        Port = 0 }
    "08" = @{ Fayl = "08-vidjetler.alqor";  Arq = @("--", "veb"); Port = 8081 }
    "09" = @{ Fayl = "09-tapsiriqlar.alqor"; Arq = @();       Port = 0 }
    "10" = @{ Fayl = "10-kitab-refi\esas.alqor"; Arq = @();   Port = 8083 }
}
$N = $Numuneler[$Numune]
$Fayl = Join-Path $Kok "numuneler\$($N.Fayl)"
$Alqorc = Join-Path $Kok "alqorc\alqorc.py"
if (-not (Test-Path $Fayl)) { Dayan "Nümunə tapılmadı: $Fayl" }

function PortAciqdir($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port); $c.Close(); return $true
    } catch { return $false }
}

# Desktop nümunəsi öz pəncərəsini açır — brauzer lazım deyil
if ($N.Port -eq 0) {
    Yaz "→ Desktop pəncərəsi açılır… (bağlayanda proqram bitir)" "Cyan"
    & $Python @PyArg $Alqorc islet $Fayl @($N.Arq)
    exit $LASTEXITCODE
}

$Unvan = "http://127.0.0.1:$($N.Port)/"
if (PortAciqdir $N.Port) {
    Yaz "! Port $($N.Port) artıq məşğuldur — köhnə server işləyir ola bilər." "Yellow"
    Yaz "  Brauzer açılır; köhnə serveri bağlamaq üçün onun pəncərəsini bağlayın." "Yellow"
    Start-Process $Unvan
    exit 0
}

# ── 4. Serveri işə sal, hazır olanda brauzeri aç ───────────────────────
Yaz "→ Server işə düşür: $($N.Fayl)" "Cyan"
$Jurnal = Join-Path $env:TEMP "alqor-server.log"
$Arqumentler = @($PyArg + @("`"$Alqorc`"", "islet", "`"$Fayl`"") + $N.Arq)
$Server = Start-Process -FilePath $Python -ArgumentList $Arqumentler `
    -WorkingDirectory (Join-Path $Kok "alqorc") -NoNewWindow -PassThru `
    -RedirectStandardError $Jurnal

$hazir = $false
for ($i = 0; $i -lt 60; $i++) {
    if ($Server.HasExited) { break }
    if (PortAciqdir $N.Port) { $hazir = $true; break }
    Start-Sleep -Milliseconds 250
}
if (-not $hazir) {
    Yaz "✖ Server qalxmadı. Xəta jurnalı:" "Red"
    if (Test-Path $Jurnal) { Get-Content $Jurnal -Encoding UTF8 | Select-Object -Last 20 }
    Dayan "Yuxarıdakı xətaya baxın."
}

Yaz "✓ Hazırdır: $Unvan" "Green"
Start-Process $Unvan
Yaz ""
Yaz "Server işləyir. Dayandırmaq üçün bu pəncərəni bağlayın və ya Ctrl+C basın." "Cyan"
try {
    $Server.WaitForExit()
    if ($Server.ExitCode -ne 0) {
        Yaz "✖ Server xəta ilə dayandı:" "Red"
        if (Test-Path $Jurnal) { Get-Content $Jurnal -Encoding UTF8 | Select-Object -Last 20 }
        Read-Host "Bağlamaq üçün Enter basın"
    }
} finally {
    if (-not $Server.HasExited) { Stop-Process -Id $Server.Id -Force }
}
