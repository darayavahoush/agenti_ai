@echo off
REM Start the backend server with full logging

echo 🚀 Starting VaakSuddhi Backend Server...
echo 📋 Logs will be displayed below...

cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Start server with full logging
uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level debug --reload

pause
