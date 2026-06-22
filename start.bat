@echo off
title AutoDBGuard
echo ============================================
echo   AutoDBGuard - Risk-Aware SQL System
echo ============================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on your PATH.
    echo Please install Python 3.10+ from https://www.python.org
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

:: Activate venv and install dependencies
echo [2/3] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

:: Check .env has been configured
findstr /C:"your_groq_api_key_here" .env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [WARNING] You haven't set your GROQ_API_KEY in the .env file.
    echo Open .env in a text editor and replace "your_groq_api_key_here"
    echo with your real key from https://console.groq.com
    echo.
    pause
)

:: Launch the app
echo [3/3] Starting AutoDBGuard on http://localhost:5000
echo.
echo Press Ctrl+C to stop the server.
echo.
python app.py
pause
