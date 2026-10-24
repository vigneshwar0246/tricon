@echo off
setlocal
cd /d "%~dp0"
title Trikon Voice AI - Stop Services

echo ============================================================
echo   Trikon Voice AI - Stopping Services
echo ============================================================

set FOUND=0

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    if not "%%a"=="0" (
        echo Stopping Backend on port 8000 [PID %%a]
        taskkill /F /PID %%a >nul 2>&1
        set FOUND=1
    )
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    if not "%%a"=="0" (
        echo Stopping Frontend on port 5173 [PID %%a]
        taskkill /F /PID %%a >nul 2>&1
        set FOUND=1
    )
)

if "%FOUND%"=="0" (
    echo No active Trikon services were found on ports 8000 or 5173.
) else (
    echo All Trikon services have been stopped successfully.
)

echo.
timeout /t 2 >nul
exit /b 0
