@echo off
:: Pinned to Python 3.10.19 for server parity
set "PYTHON_PATH=C:\Users\arpit\AppData\Local\Programs\Python\Python310"
set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"

echo Checking Python Version...
python --version | findstr "3.10"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Python 3.10.19 not found at %PYTHON_PATH%
    echo Current Python version is:
    python --version
    echo.
    echo Please ensure Python 3.10.19 is installed to match your production server.
    echo You can download it from python.org
    pause
)

echo.
echo Syncing dependencies (FastAPI, etc.)...
python -m pip install -r requirements.txt

echo.
echo Starting SetuGeo OCR Service [Python 3.10 Parity Mode]...
python main.py
pause
