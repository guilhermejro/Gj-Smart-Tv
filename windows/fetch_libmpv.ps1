#requires -Version 5.1
# Baixa o libmpv-2.dll (build shinchiro/mpv-winbuild-cmake) e SÓ o instala se o SHA-256 conferir.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$Url    = "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20261021/mpv-dev-x86_64-20261021-git-e471496c56.7z"
$Sha256 = "efc719eff3dc5954b4a5efc800632808bcec01cc9034940dd14e5eb7fe9ea633"
$dest   = Join-Path $root "libs\libmpv-2.dll"

if (Test-Path $dest) { Write-Host "libmpv-2.dll já presente em libs\. Nada a fazer."; exit 0 }

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$tmp = Join-Path $env:TEMP ("gjtv-libmpv-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    $archive = Join-Path $tmp "mpv-dev.7z"
    Write-Host "Baixando libmpv (~30 MB)..."
    Invoke-WebRequest -Uri $Url -OutFile $archive -UseBasicParsing
    $got = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLower()
    if ($got -ne $Sha256) { throw "SHA-256 NÃO confere. Esperado $Sha256, obtido $got. Arquivo descartado." }
    Write-Host "SHA-256 do arquivo confere."
    # O arquivo usa o filtro BCJ2: precisa do 7-Zip (preferido) ou do tar.exe do Windows 11 (libarchive).
    $sevenZip = @("$env:ProgramFiles\7-Zip\7z.exe", "${env:ProgramFiles(x86)}\7-Zip\7z.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $sevenZip) { $sevenZip = (Get-Command 7z.exe -ErrorAction SilentlyContinue).Source }
    if ($sevenZip) {
        & $sevenZip e $archive "-o$tmp" libmpv-2.dll -y | Out-Null
    } else {
        Write-Host "7-Zip não encontrado; tentando o tar.exe do Windows..."
        & tar.exe -xf $archive -C $tmp libmpv-2.dll
    }
    if (-not (Test-Path (Join-Path $tmp "libmpv-2.dll"))) {
        throw "Não consegui extrair libmpv-2.dll. Instale o 7-Zip (winget install 7zip.7zip) e rode de novo."
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item (Join-Path $tmp "libmpv-2.dll") $dest
    Write-Host "Instalado: $dest"
    Write-Host ("SHA-256 da DLL: " + (Get-FileHash -Algorithm SHA256 $dest).Hash.ToLower())
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
