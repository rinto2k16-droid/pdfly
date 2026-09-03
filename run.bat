@echo off
REM PDFly launcher (Windows)
cd /d "%~dp0"
python -c "import flask" 2>nul
if errorlevel 1 (
  echo Installing dependencies...
  pip install -r requirements.txt
)
set PORT=5000
echo PDFly running at http://localhost:5000
python app.py
pause
