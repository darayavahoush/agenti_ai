@echo off
REM Setup script for Vaaksudhi project on Windows

echo ========================================
echo   Vaaksudhi Project Setup (Windows)
echo ========================================
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: uv is not installed or not in PATH
    echo Please install uv with: pip install uv
    echo Or visit https://github.com/astral-sh/uv
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18 or higher from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/7] Creating Python virtual environment with uv...
uv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/7] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    echo If PowerShell blocks execution, run: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
    pause
    exit /b 1
)

echo [3/7] Installing Python dependencies with uv...
cd backend
uv pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

echo [4/7] Setting up environment file...
if not exist .env (
    copy .env.example .env
    echo Created .env file from template
    echo Please edit backend\.env with your database credentials
) else (
    echo .env file already exists
)

echo [5/7] Downloading NLTK data...
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng'); nltk.download('averaged_perceptron_tagger'); nltk.download('cmudict'); nltk.download('punkt')"

echo [6/7] Installing Node.js dependencies...
cd ..\frontend
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Node.js dependencies
    pause
    exit /b 1
)

echo [7/7] Setup complete!
echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To run the project:
echo.
echo 1. Backend:
echo    cd backend
echo    ..\.venv\Scripts\activate
echo    uvicorn app.main:app --reload
echo.
echo 2. Frontend (in new terminal):
echo    cd frontend
echo    npm run dev
echo.
echo Note: Make sure PostgreSQL is running and database 'vaaksudhi' exists
echo.
pause
