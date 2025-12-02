@echo off
cd /d "%~dp0"
echo Starting Chess Improvement Coach for Lichess...

REM Check if .venv exists
if not exist ".venv" (
    echo [INFO] Virtual environment not found. Setting up...
    echo [INFO] Creating .venv...
    python -m venv .venv
    echo [INFO] Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt
    echo [INFO] Setup complete!
)

REM Use the python executable from the virtual environment to run streamlit
.venv\Scripts\python.exe -m streamlit run app.py
pause
