@echo off
setlocal
cd /d "%~dp0"

if exist "SofaScore.exe" (
    start "" "%~dp0SofaScore.exe"
    exit /b 0
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m sofascore.webapp
    exit /b 0
)

if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Python\bin\pythonw.exe" -m sofascore.webapp
    exit /b 0
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw -m sofascore.webapp
    exit /b 0
)

echo No se encontro Python ni SofaScore.exe.
echo.
echo Instala Python 3.10 o superior desde https://www.python.org/downloads/
echo o ejecuta build_exe.ps1 para crear el ejecutable.
pause
exit /b 1

