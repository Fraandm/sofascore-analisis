# Genera SofaScore.exe (un solo archivo, sin consola).
# Uso: clic derecho > "Ejecutar con PowerShell" o:
#   powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (Get-Process -Name "SofaScore" -ErrorAction SilentlyContinue) {
    throw "Cierra SofaScore.exe antes de recompilar."
}

$python = $null
$pythonArgs = @()
foreach ($candidate in @(
    (Join-Path $PSScriptRoot ".venv\Scripts\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Python\bin\python.exe")
)) {
    if (Test-Path $candidate) { $python = $candidate; break }
}
if (-not $python) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { $python = $command.Source }
}
if (-not $python) {
    $command = Get-Command py -ErrorAction SilentlyContinue
    if ($command) {
        $python = $command.Source
        $pythonArgs = @("-3")
    }
}
if (-not $python) {
    throw "No se encontro Python. Instala Python 3.10 o superior."
}

& $python @pythonArgs -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando PyInstaller..."
    & $python @pythonArgs -m pip install --disable-pip-version-check pyinstaller
}

Write-Host "Compilando SofaScore.exe..."
& $python @pythonArgs -m PyInstaller --noconfirm --clean SofaScore.spec

if (Test-Path "SofaScore.exe") {
    Remove-Item "SofaScore.exe" -Force
}
Copy-Item "dist\SofaScore.exe" "SofaScore.exe" -Force
Remove-Item -Recurse -Force "build", "dist"

Write-Host ""
Write-Host "Listo: $(Join-Path $PSScriptRoot 'SofaScore.exe')"
Write-Host "Puedes abrirlo con doble clic desde el Explorador de Windows."
