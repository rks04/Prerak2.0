@echo off
echo =========================================
echo Starting PRERAK 2.0
echo =========================================
echo.

cd backend
call venv\Scripts\activate.bat
python run.py
pause
