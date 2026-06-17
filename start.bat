@echo off
echo =========================================
echo Starting PRERAK 2.0 (SPA Mode)
echo =========================================
echo.

echo Starting Server...
cd backend
call venv\Scripts\activate.bat
python run.py
pause
