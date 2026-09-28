@echo off
setlocal
cd /d "%~dp0"

REM ============================================================
REM  Social Media Automation - one-click launcher for Windows
REM ============================================================

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo Install Python 3.11+ from https://www.python.org/downloads/
    echo IMPORTANT: check "Add Python to PATH" during installation, then run this file again.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
)

echo [2/3] Installing requirements... please wait 1-3 minutes...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet --no-cache-dir --disable-pip-version-check
pip install -r requirements.txt --no-cache-dir --disable-pip-version-check

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo [3/3] Starting server...
echo Open your browser at:  http://127.0.0.1:8000
echo (To stop: press Ctrl+C or close this window)
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
