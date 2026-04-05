@echo off
cd /d %~dp0
echo ================================================
echo Spoustim Qt verzi aplikace...
echo ================================================
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Instalace zavislosti selhala.
  pause
  exit /b 1
)
python app.py
if errorlevel 1 (
  echo.
  echo Aplikace spadla. Pokud se vytvoril traceback v konzoli, posli ho sem.
  pause
)
