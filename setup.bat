@echo off
SETLOCAL

python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not installed. Install Python and run this script again.
    exit /b 1
)

where ffmpeg >nul 2>&1
IF ERRORLEVEL 1 (
    echo ffmpeg not found. Please install ffmpeg and ensure it is in your PATH.
    pause
    exit /b 1
)

python -m venv .venv

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip

pip install -r requirements.txt

echo Setup completed successfully!
pause
ENDLOCAL
