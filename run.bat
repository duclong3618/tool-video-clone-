@echo off
:: Author: DUC LONG
:: VideoDubAI - Run Script (Windows)

echo =========================================
echo   VideoDubAI - Starting...
echo =========================================

:: Activate venv
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: Create .env if not exists
if not exist .env (
    copy .env.example .env >nul
    echo [OK] Created .env from .env.example
)

:: Start backend
echo [1/2] Starting backend on http://localhost:8000 ...
start "VideoDubAI Backend" cmd /k "uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: Start frontend
echo [2/2] Starting frontend on http://localhost:3000 ...
cd frontend
start "VideoDubAI Frontend" cmd /k "npm run dev"
cd ..

echo.
echo =========================================
echo   VideoDubAI is running!
echo =========================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   Swagger:   http://localhost:8000/docs
echo.
echo   Close the terminal windows to stop
echo =========================================

pause
