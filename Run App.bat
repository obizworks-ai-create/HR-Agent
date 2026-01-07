@echo off
setlocal
title Candidate Platform Launcher

echo ===================================================
echo   Starting Candidate Intelligence Platform
echo ===================================================
echo.

:: 1. Backend Setup & Launch
echo [STEP 1/3] Checking Backend...
if not exist "backend\venv" (
    echo    - Virtual environment not found. Creating 'venv'...
    
    :: Try to use python, if not found try py
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        cd backend
        python -m venv venv
        cd ..
    ) else (
        echo    - Python not found in path! Attempting 'py' launcher...
        cd backend
        py -m venv venv
        cd ..
    )
    
    echo    - Activating and installing requirements...
    cd backend
    call venv\Scripts\activate
    pip install -r requirements.txt
    cd ..
) else (
    echo    - Virtual environment found.
)

echo    - Launching Backend Server...
:: Start in new window
start "Backend Server" cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --reload"


:: 2. Frontend Setup & Launch
echo [STEP 2/3] Checking Frontend...
if not exist "frontend\node_modules" (
    echo    - Node modules not found. Installing dependencies...
    echo    - This may take a few minutes...
    cd frontend
    call npm install
    cd ..
) else (
    echo    - Node modules found.
)

echo    - Launching Frontend Server...
:: Start in new window
start "Frontend Server" cmd /k "cd frontend && npm run dev"


:: 3. Launch Browser
echo [STEP 3/3] Opening Application...
echo    - Waiting for servers to spin up...
timeout /t 7 >nul

echo    - Opening Default Browser...
start "" "http://localhost:5173"

echo.
echo ===================================================
echo   SUCCESS! The application is running.
echo   - Backend logging is in the 'Backend Server' window.
echo   - Frontend logging is in the 'Frontend Server' window.
echo   - To stop, simply close those two windows.
echo ===================================================
echo.
pause
