$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (Get-Process -Name "SofaScore" -ErrorAction SilentlyContinue) {
    throw "Cierra SofaScore.exe antes de probar el instalador."
}

$versionText = Get-Content -LiteralPath (Join-Path $PSScriptRoot "sofascore\__init__.py") -Raw
if ($versionText -notmatch '__version__\s*=\s*"([^"]+)"') {
    throw "No se pudo leer la version."
}
$version = $Matches[1]
$installer = Join-Path $PSScriptRoot "dist-installer\SofaScore-Setup-$version.exe"
if (-not (Test-Path -LiteralPath $installer)) {
    throw "No existe el instalador: $installer"
}

$testDir = Join-Path $env:TEMP ("SofaScore-installer-test-" + [guid]::NewGuid().ToString("N"))
$appExe = Join-Path $testDir "SofaScore.exe"
$uninstaller = Join-Path $testDir "unins000.exe"
$appProcess = $null

try {
    New-Item -ItemType Directory -Force -Path $testDir | Out-Null
    Write-Host "Instalando en $testDir..."
    $install = Start-Process -FilePath $installer -ArgumentList @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOICONS",
        "/DIR=$testDir"
    ) -Wait -PassThru
    if ($install.ExitCode -ne 0) {
        throw "El instalador devolvio el codigo $($install.ExitCode)."
    }
    if (-not (Test-Path -LiteralPath $appExe)) {
        throw "El instalador no creo SofaScore.exe."
    }
    if (-not (Test-Path -LiteralPath $uninstaller)) {
        throw "El instalador no creo el desinstalador."
    }

    Write-Host "Iniciando la copia instalada..."
    $appProcess = Start-Process -FilePath $appExe -ArgumentList @("--no-window", "--port", "8877") -PassThru
    $health = $null
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8877/api/health" -TimeoutSec 2
            break
        } catch {
            $health = $null
        }
    }
    if (-not $health) {
        throw "La aplicacion instalada no respondio en el puerto 8877."
    }
    if ($health.version -ne $version) {
        throw "Version inesperada: $($health.version); se esperaba $version."
    }
    Write-Host "Aplicacion instalada OK: version $($health.version)."

    Get-Process -Name "SofaScore" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1

    Write-Host "Desinstalando..."
    $uninstall = Start-Process -FilePath $uninstaller -ArgumentList @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART"
    ) -Wait -PassThru
    if ($uninstall.ExitCode -ne 0) {
        throw "El desinstalador devolvio el codigo $($uninstall.ExitCode)."
    }
    Start-Sleep -Seconds 1
    if (Test-Path -LiteralPath (Join-Path $testDir "SofaScore.exe")) {
        throw "El desinstalador no elimino SofaScore.exe."
    }
    Write-Host "Instalador y desinstalador verificados correctamente."
}
finally {
    Get-Process -Name "SofaScore" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $testDir) {
        Remove-Item -LiteralPath $testDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
