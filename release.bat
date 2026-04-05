@echo off
setlocal

cd /d "%~dp0"

if "%~1"=="" (
    echo Pouziti: release.bat 1.0.5
    exit /b 1
)

python scripts\release_build.py %1
if errorlevel 1 exit /b %errorlevel%

echo.
echo Hotovo. Nova verze %1 byla postavena, pushnuta a nahrana do GitHub Release.
pause
