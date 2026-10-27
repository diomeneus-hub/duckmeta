@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" duckmeta.py %*
) else (
  py -3 duckmeta.py %*
)
if errorlevel 1 pause
