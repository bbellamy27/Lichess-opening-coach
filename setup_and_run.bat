@echo off
cd /d "%~dp0"
echo ==========================================
echo   Lichess Opening Coach - One-Click Setup
echo ==========================================

REM 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

REM 2. Check if virtual environment exists, create if not
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

REM 3. Activate virtual environment and install dependencies
echo [INFO] Checking dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt >nul 2>&1

REM 3.5 Create Shortcut (Optional)
if not exist "%USERPROFILE%\Desktop\Lichess Coach.lnk" (
    echo.
    set /p create_shortcut="Create Desktop Shortcut? (Y/N): "
    if /i "%create_shortcut%"=="Y" (
        echo [INFO] Creating shortcut...
        powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\Lichess Coach.lnk');$s.TargetPath='%~dp0setup_and_run.bat';$s.WorkingDirectory='%~dp0';$s.IconLocation='%~dp0app.py,0';$s.Save()"
        echo [INFO] Shortcut created on Desktop!
    )
)

REM 4. Run the App
echo [INFO] Launching App...
echo.
streamlit run app.py

pause
