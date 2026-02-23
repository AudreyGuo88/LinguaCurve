@echo off
echo ====================================
echo   EchoRecall English Launcher
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [INFO] Virtual environment created!
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet

REM Launch Streamlit app
echo.
echo ====================================
echo   Starting EchoRecall English...
echo   The app will open in your browser
echo ====================================
echo.
streamlit run app.py

pause