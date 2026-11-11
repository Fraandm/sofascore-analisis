param(
    [switch]$SkipExe
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$versionFile = Join-Path $PSScriptRoot "sofascore\__init__.py"
$versionText = Get-Content -LiteralPath $versionFile -Raw
if ($versionText -notmatch '__version__\s*=\s*"([^"]+)"') {
    throw "No se pudo leer la version desde sofascore\__init__.py"
}
$version = $Matches[1]

if (-not $SkipExe) {
    Write-Host "Compilando SofaScore.exe..."
    & (Join-Path $PSScriptRoot "build_exe.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo al compilar SofaScore.exe."
    }
}

$appExe = Join-Path $PSScriptRoot "SofaScore.exe"
if (-not (Test-Path -LiteralPath $appExe)) {
    throw "No existe SofaScore.exe. Ejecuta build_exe.ps1 primero."
}

$isccCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
    "C:\Program Files\Inno Setup 7\ISCC.exe"
)
$iscc = $null
foreach ($candidate in $isccCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        $iscc = $candidate
        break
    }
}
if (-not $iscc) {
    throw "No se encontro Inno Setup. Instala Inno Setup 6 con: winget install JRSoftware.InnoSetup"
}

$outputDir = Join-Path $PSScriptRoot "dist-installer"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Get-ChildItem -LiteralPath $outputDir -File -Filter "SofaScore-Setup-*.exe" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath $outputDir -File -Filter "SHA256SUMS.txt" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

$scriptPath = Join-Path $PSScriptRoot "installer\SofaScore.iss"
Write-Host "Generando instalador para SofaScore $version..."
& $iscc "/DAppVersion=$version" $scriptPath
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup devolvio el codigo $LASTEXITCODE."
}

$installer = Join-Path $outputDir "SofaScore-Setup-$version.exe"
if (-not (Test-Path -LiteralPath $installer)) {
    throw "No se genero el instalador esperado: $installer"
}

$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$appHash = (Get-FileHash -LiteralPath $appExe -Algorithm SHA256).Hash.ToLowerInvariant()
$checksumPath = Join-Path $outputDir "SHA256SUMS.txt"
@(
    "$appHash  SofaScore.exe",
    "$hash  $(Split-Path -Leaf $installer)"
) | Set-Content -LiteralPath $checksumPath -Encoding ascii

Write-Host ""
Write-Host "Instalador listo: $installer"
Write-Host "SHA-256 instalador: $hash"
Write-Host "SHA-256 portable:   $appHash"
Write-Host "Sumas: $checksumPath"
