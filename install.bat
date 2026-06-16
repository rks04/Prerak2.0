@echo off
echo =========================================
echo PRERAK 2.0 Installation Script
echo =========================================
echo.

cd backend

echo [1/3] Creating Python Virtual Environment...
python -m venv venv

echo [2/3] Activating Virtual Environment...
call venv\Scripts\activate.bat

echo [3/3] Installing Dependencies...
pip install -r requirements.txt

echo.
echo =========================================
echo Installation Complete!
echo You can now double-click start.bat
echo =========================================
pause
