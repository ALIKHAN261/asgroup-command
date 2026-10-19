@echo off
setlocal EnableDelayedExpansion
title AS GROUP Command - backend
cd /d "%~dp0backend"

REM ---- 1. Python check ----
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.11+ from https://www.python.org/downloads/
  echo         Tick "Add python.exe to PATH" during install, then double-click start.bat again.
  pause
  exit /b 1
)

REM ---- 2. Virtual environment ----
if not exist ".venv\Scripts\activate.bat" (
  echo [1/3] Creating virtual environment...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

REM ---- 3. Dependencies ----
echo [2/3] Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed. Check your internet connection, then run start.bat again.
  pause
  exit /b 1
)

REM ---- 4. First-run API token ----
findstr /C:"CHANGE_ME_TO_A_LONG_RANDOM_STRING" config.yaml >nul
if not errorlevel 1 (
  echo [3/3] First run: generating your API token...
  for /f "delims=" %%T in ('python -c "import secrets;print(secrets.token_hex(32))"') do set "TOKEN=%%T"
  powershell -NoProfile -Command "$c = Get-Content 'config.yaml'; $c -replace 'CHANGE_ME_TO_A_LONG_RANDOM_STRING', '!TOKEN!' | Set-Content 'config.yaml'"
  echo         Token saved to backend\config.yaml.
  echo         Enter it once in the dashboard ^(gear icon, "API token"^) - saved in your browser.
) else (
  echo [3/3] API token already set.
)

echo.
echo ============================================================
echo  AS GROUP Command is starting - your agents are going online.
echo  Keep this window open ^(minimize is fine, do NOT close it^).
echo  Dashboard: https://asgroup-command-ut-tech.vercel.app/dashboard.html
echo  Stop anytime with stop.bat
echo ============================================================
echo.
python main.py
echo.
echo Server stopped.
pause
