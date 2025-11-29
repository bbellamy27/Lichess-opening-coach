@echo off
cd /d "%~dp0"
echo Starting Lichess Opening Coach...
REM Use the python executable from the virtual environment to run streamlit
..\.venv\Scripts\python.exe -m streamlit run app.py
pause
