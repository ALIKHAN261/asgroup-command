@echo off
taskkill /F /FI "WINDOWTITLE eq AS GROUP Command - backend" >nul 2>&1
if errorlevel 1 (
  echo No running AS GROUP Command backend found.
) else (
  echo AS GROUP Command backend stopped.
)
pause
