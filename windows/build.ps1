#requires -Version 5.1
# Gera dist\gj-smart-tv\ (app) e, se o Inno Setup estiver instalado, installer\GJ-Smart-TV-Setup-*.exe
# Uso:  powershell -ExecutionPolicy Bypass -File windows\build.ps1
param([switch]$SkipTests)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $exe $($arguments -join ' ')" }
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher (py) não encontrado. Instale: winget install Python.Python.3.12"
}
if (-not (Test-Path ".venv\Scripts\python.exe")) { Run "py" @("-3.12", "-m", "venv", ".venv") }
$py = Join-Path $root ".venv\Scripts\python.exe"

Run $py @("-m", "pip", "install", "--upgrade", "pip")
# Dependências do app: versões e hashes fixos (--require-hashes recusa qualquer arquivo adulterado)
Run $py @("-m", "pip", "install", "--require-hashes", "-r", "requirements.lock")
Run $py @("-m", "pip", "install", "-r", "requirements-build.txt")

& "$PSScriptRoot\fetch_libmpv.ps1"

if (-not $SkipTests) {
    $env:QT_QPA_PLATFORM = "offscreen"
    Run $py @("-m", "pytest", "-q")
}

Run $py @("-m", "PyInstaller", "--noconfirm", "--clean", "gj-smart-tv.spec")

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    Run $iscc @("windows\installer.iss")
    Get-ChildItem installer\*.exe | ForEach-Object {
        "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower(), $_.Name
    } | Tee-Object installer\SHA256SUMS.txt
    Write-Host "Instalador pronto em installer\"
} else {
    Write-Host "Inno Setup não encontrado (winget install JRSoftware.InnoSetup). App pronto em dist\gj-smart-tv\gj-smart-tv.exe"
}
