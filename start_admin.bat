@echo off
chcp 65001 >nul
echo ====================================
echo   Stonk - Stock Simulation System
echo   Admin Panel Launcher
echo ====================================
echo.

:: Use the directory where this bat file is located
cd /d "%~dp0"

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found, activating...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found, activating...
    call .venv\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found, using system Python
)

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python found

:: Check all required packages
python -c "import PySide6; import websockets; import aiosqlite; import numpy" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some dependencies are missing. Installing from requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Please run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
)

echo [OK] Required packages found
echo.

:: Kill any existing StonkServer windows
taskkill /FI "WINDOWTITLE eq StonkServer*" /F >nul 2>&1

:: Set PYTHONPATH to project root (bat file directory)
set "PYTHONPATH=%~dp0"

:: Build the venv activation command for the server window
set "ACTIVATE_CMD="
if exist "venv\Scripts\activate.bat" (
    set "ACTIVATE_CMD=call venv\Scripts\activate.bat && "
) else if exist ".venv\Scripts\activate.bat" (
    set "ACTIVATE_CMD=call .venv\Scripts\activate.bat && "
)

:: Start WebSocket server in a new window (cmd /k keeps window open on error)
echo [STARTING] WebSocket Server...
start "StonkServer" /D "%~dp0." cmd /k "%ACTIVATE_CMD%set PYTHONPATH=%~dp0 && python -u server/websocket_server.py"

:: Wait for server to start
echo [WAITING] Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Verify server is listening on port 8765
python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8765)); s.close()" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Server not ready yet, waiting a bit more...
    timeout /t 3 /nobreak >nul
    python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8765)); s.close()" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] WebSocket Server failed to start. Check the server window for errors.
        echo         Press any key to continue anyway, or close this window to abort.
        pause
    )
)

echo [OK] WebSocket Server started (ws://127.0.0.1:8765)
echo.

:: Start Admin UI (blocking call - waits until UI window is closed)
echo [STARTING] Admin UI...
python server/admin_ui.py

echo.
echo [DONE] Admin panel closed. Shutting down server...

:: Kill server when UI closes
taskkill /FI "WINDOWTITLE eq StonkServer*" /F >nul 2>&1

echo [DONE] Server stopped.
pause
