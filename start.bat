@echo off
setlocal enabledelayedexpansion
title Trikon Voice AI - Launcher
cd /d "%~dp0"

echo ============================================================
echo           Trikon Voice AI - Local Assistant
echo ============================================================
echo.

:: 1. Check Python virtual environment
if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Backend virtual environment not found at backend\.venv\
    echo Please set up the backend virtual environment first:
    echo   cd backend
    echo   py -3.11 -m venv .venv
    echo   .\.venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: 2. Check Node / npm
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 'npm' was not found in your PATH. Please install Node.js 18 or newer.
    pause
    exit /b 1
)

if not exist "frontend\node_modules\" (
    echo [SETUP] Installing frontend dependencies...
    cd /d "%~dp0frontend"
    call npm install
    cd /d "%~dp0"
)

:: 3. Check and start Ollama if needed
echo [CHECK] Checking Ollama service...
curl -s -m 2 http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [OLLAMA] Ollama is not responding at 127.0.0.1:11434.
    echo [OLLAMA] Attempting to launch Ollama in background...
    start /min "Ollama" ollama serve
    ping -n 4 127.0.0.1 >nul
    curl -s -m 3 http://127.0.0.1:11434/api/tags >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARN] Ollama could not be verified automatically.
        echo Please ensure Ollama is installed and running if LLM queries fail.
    ) else (
        echo [OLLAMA] Ollama started successfully.
    )
) else (
    echo [OLLAMA] Ollama service is active.
)

:start_services
:: 4. Check & Start Backend (port 8000)
set BACKEND_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    if not "%%a"=="0" set BACKEND_PID=%%a
)

if defined BACKEND_PID (
    echo [BACKEND] Already running on port 8000 [PID !BACKEND_PID!].
) else (
    echo [BACKEND] Starting FastAPI server on http://127.0.0.1:8000 ...
    start "Trikon Backend" cmd /k "cd /d "%~dp0backend" && title Trikon Backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

:: 5. Check & Start Frontend (port 5173)
set FRONTEND_PID=
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    if not "%%a"=="0" set FRONTEND_PID=%%a
)

if defined FRONTEND_PID (
    echo [FRONTEND] Already running on port 5173 [PID !FRONTEND_PID!].
) else (
    echo [FRONTEND] Starting Vite dev server on http://127.0.0.1:5173 ...
    start "Trikon Frontend" cmd /k "cd /d "%~dp0frontend" && title Trikon Frontend && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"
)

:: 6. Wait for services to be ready
echo.
echo [HEALTH] Verifying services readiness...

set ATTEMPTS=0
:check_backend_loop
set /a ATTEMPTS+=1
curl -s -m 2 http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel% equ 0 goto backend_ok
if %ATTEMPTS% geq 25 (
    echo [WARN] Backend did not respond within 25 seconds.
    goto check_frontend
)
ping -n 2 127.0.0.1 >nul
goto check_backend_loop

:backend_ok
echo [HEALTH] Backend is ready and responding at http://127.0.0.1:8000

:check_frontend
set F_ATTEMPTS=0
:check_frontend_loop
set /a F_ATTEMPTS+=1
curl -s -m 2 http://127.0.0.1:5173 >nul 2>&1
if %errorlevel% equ 0 goto frontend_ok
if %F_ATTEMPTS% geq 20 (
    echo [WARN] Frontend did not respond within 20 seconds.
    goto display_ready
)
ping -n 2 127.0.0.1 >nul
goto check_frontend_loop

:frontend_ok
echo [HEALTH] Frontend is ready at http://127.0.0.1:5173

:display_ready
echo.
echo ============================================================
echo   Trikon Voice AI is UP and RUNNING!
echo.
echo   UI:       http://127.0.0.1:5173
echo   Backend:  http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/docs
echo ============================================================
echo.
echo Opening browser...
start http://127.0.0.1:5173

:menu_loop
echo.
echo Options:
echo   [O] Open browser
echo   [R] Restart services
echo   [S] Stop all services and exit
echo   [Q] Quit launcher window
echo.
set "USER_CHOICE="
set /p USER_CHOICE="Enter choice [O/R/S/Q]: "

if not defined USER_CHOICE (
    ping -n 3 127.0.0.1 >nul
    goto menu_loop
)

if /i "%USER_CHOICE%"=="O" (
    start http://127.0.0.1:5173
    goto menu_loop
)

if /i "%USER_CHOICE%"=="R" (
    echo.
    echo [RESTART] Stopping active services...
    call "%~dp0stop.bat"
    ping -n 3 127.0.0.1 >nul
    echo [RESTART] Starting services again...
    goto start_services
)

if /i "%USER_CHOICE%"=="S" (
    echo.
    echo Stopping all services...
    call "%~dp0stop.bat"
    echo Done.
    exit /b 0
)

if /i "%USER_CHOICE%"=="Q" (
    echo Launcher closed. Backend and Frontend remain running in background.
    exit /b 0
)

goto menu_loop
