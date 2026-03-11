@echo off
chcp 65001 >nul
echo ====================================
echo   Stonk - Stock Simulation System
echo   Admin Panel Launcher
echo ====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python found
echo.

:: Kill any existing StonkServer windows
taskkill /FI "WINDOWTITLE eq StonkServer*" /F >nul 2>&1

:: Set PYTHONPATH to current directory
set PYTHONPATH=%CD%

:: Start WebSocket server in background
echo [STARTING] WebSocket Server...
start "StonkServer" cmd /c "set PYTHONPATH=%CD% && python server/websocket_server.py"

:: Wait for server to start
echo [WAITING] Waiting for server to start...
timeout /t 5 /nobreak >nul

echo [OK] WebSocket Server started (ws://localhost:8765)
echo.

:: Start Admin UI
echo [STARTING] Admin UI...
python server/admin_ui.py

echo.
echo [DONE] Admin panel closed

:: Kill server when UI closes
taskkill /FI "WINDOWTITLE eq StonkServer*" /F >nul 2>&1
pause
