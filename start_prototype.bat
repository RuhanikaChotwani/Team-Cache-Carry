@echo off
title IBVAP - Intelligent Border Surveillance Launcher
echo ======================================================================
echo    IBVAP - Intelligent Border Video Analytics Platform (Prototype)
echo ======================================================================
echo.

set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%Team-Cache-Claude\backend\main.py" (
    set ROOT_DIR=%SCRIPT_DIR%Team-Cache-Claude
) else (
    set ROOT_DIR=%SCRIPT_DIR%
)

echo [1/3] Detecting Python 3.11 environment...
if exist "C:\Program Files\Python311\python.exe" (
    set PYTHON_EXE="C:\Program Files\Python311\python.exe"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PYTHON_EXE=py -3.11
    ) else (
        set PYTHON_EXE=python
    )
)
echo Python executable configured as: %PYTHON_EXE%

echo.
echo [2/3] Starting Backend API Server (Port 8000)...
start "IBVAP Backend [FastAPI:8000]" cmd /c "title IBVAP Backend && cd /d "%ROOT_DIR%\backend" && %PYTHON_EXE% -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo.
echo [3/3] Starting Frontend Dev Server (Port 5173)...
start "IBVAP Frontend [Vite:5173]" cmd /c "title IBVAP Frontend && cd /d "%ROOT_DIR%" && npm run dev"

echo.
echo Waiting 4 seconds for services to initialize...
timeout /t 4 /nobreak >nul

echo Opening IBVAP Prototype in your default browser...
start http://localhost:5173

echo.
echo ======================================================================
echo  IBVAP Prototype is now LIVE:
echo    - Frontend UI:  http://localhost:5173
echo    - Backend API:  http://127.0.0.1:8000
echo    - Health Check: http://127.0.0.1:8000/api/health
echo    - API Docs:     http://127.0.0.1:8000/docs
echo ======================================================================
echo Keep the backend and frontend console windows open while testing.
echo Press any key to exit this launcher window...
pause >nul
