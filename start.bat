@echo off
set "PYTHON_PATH=C:\Users\arpit\AppData\Local\Programs\Python\Python313"
set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"

echo Checking Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo Python not found at %PYTHON_PATH%. Please verify the installation path.
    pause
    exit /b
)

echo.
echo Starting SetuGeo OCR Service...
python main.py
pause
