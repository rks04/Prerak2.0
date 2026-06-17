@echo off
echo =========================================
echo PRERAK 2.0 Installation Script
echo =========================================
echo.

echo [1/3] Installing Backend Dependencies...
cd backend
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

echo [2/3] Installing Frontend Dependencies ^& Building SPA...
cd frontend
call npm install
call npm run build
cd ..

echo.
echo =========================================
echo Installation Complete!
echo You can now double-click start.bat
echo =========================================
pause
