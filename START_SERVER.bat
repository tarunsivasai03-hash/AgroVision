@echo off
echo ============================================================
echo AgroVision - Smart Farming Assistant
echo ============================================================
echo.
echo Starting Flask server...
echo.
echo Access the website at: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python app.py
) else (
    py -3.11 app.py
)

pause
