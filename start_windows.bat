@echo off
REM ============================================================
REM  PDFly — one-click launcher for Windows
REM  Double-click this file. It will:
REM    1. Check Python
REM    2. Install packages on first run
REM    3. CLOSE any old PDFly server still using port 5000
REM    4. Start the new server (own window with logs)
REM    5. Wait, verify it is alive, then open your browser
REM ============================================================
cd /d "%~dp0"
title PDFly Launcher

echo.
echo  ============================================
echo   PDFly - iLovePDF style PDF toolkit
echo  ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  [!] Python not found. Install it from https://www.python.org/downloads/
    echo      IMPORTANT: tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 (
    echo  [!] Python 3.9 or newer is required. Install it, then run me again.
    pause
    exit /b 1
)

if not exist ".installed" (
    echo  [1/3] Installing Python packages... first run only, takes 1-2 minutes.
    python -m pip install --upgrade pip >nul 2>nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo  [!] Package installation failed. Check your internet and try again.
        pause
        exit /b 1
    )
    echo ok > .installed
) else (
    echo  [1/3] Packages already installed - skipping.
)

echo  [2/3] Closing any OLD pdfly server still on port 5000 (if found)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    echo        closing PID %%a
    taskkill /PID %%a /F >nul 2>nul
)
timeout /t 1 /nobreak >nul

echo  [3/3] Starting server at http://localhost:5000
echo        The "PDFly Server" window shows every upload - keep it open!
echo.
start "PDFly Server" cmd /k "cd /d %~dp0 && python app.py"

echo  Waiting for the server to come alive...
setlocal enabledelayedexpansion
set OK=
for /l %%i in (1,1,12) do (
    timeout /t 1 /nobreak >nul
    set CODE=000
    for /f "delims=" %%c in ('curl -s -o NUL -w "%%{http_code}" http://localhost:5000/health 2^>nul') do set CODE=%%c
    if "!CODE!"=="200" set OK=yes
    if defined OK goto alive
)
echo  [!] Server did not answer yet. Check the "PDFly Server" window for errors.
goto done

:alive
echo  OK - server is UP. Opening your browser...
echo.
echo  If anything looks wrong:
echo    1. Press Ctrl+F5 in the browser (hard refresh, clears the old cache)
echo    2. Keep this window and the "PDFly Server" window open while working
start "" http://localhost:5000

:done
echo.
pause
