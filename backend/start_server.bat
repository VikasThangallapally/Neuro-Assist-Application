@echo off
echo ============================================
echo    🧠 Neuro ASSIST - Brain Tumor Detection
echo ============================================
echo.
echo Starting the server with 3D animations...
echo.
cd /d "%~dp0"
python fastapi_app.py
pause