@echo off
setlocal

cd /d "%~dp0"

set /p APP_VERSION=<VERSION
echo Stavim verzi %APP_VERSION%

python -m PyInstaller --noconfirm PujcovnaStroju.spec

echo.
echo Hotovo. Vysledna aplikace verze %APP_VERSION% je v dist\PujcovnaStroju.exe
pause
