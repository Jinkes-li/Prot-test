@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====== PortTester Windows Build ======
echo Current dir: %CD%

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version

echo Installing PyInstaller...
pip install pyinstaller --quiet

echo Building exe...
python -m PyInstaller --onefile --name "PortTester" --clean main.py

if errorlevel 1 (
    echo.
    echo Build FAILED. Check errors above.
    pause
    exit /b 1
)

echo.
echo ==============================
echo Build OK!
echo Output: %CD%\dist\PortTester.exe
echo ==============================
pause
