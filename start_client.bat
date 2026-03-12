@echo off
chcp 65001 >nul
echo ====================================
echo   Stonk - Stock Simulation System
echo   Client Launcher
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

:: ==================== 服务器地址配置 ====================
:: 默认连接本地服务器，如需连接远程服务器，请取消下面一行的注释并修改 IP 地址
:: set STONK_SERVER_HOST=192.168.1.100
:: set STONK_SERVER_PORT=8765

:: 如果设置了环境变量，显示当前配置
if defined STONK_SERVER_HOST (
    echo [CONFIG] Server Host: %STONK_SERVER_HOST%
) else (
    echo [CONFIG] Server Host: 127.0.0.1 (local)
)
if defined STONK_SERVER_PORT (
    echo [CONFIG] Server Port: %STONK_SERVER_PORT%
) else (
    echo [CONFIG] Server Port: 8765
)
echo.

:: 如果有自定义配置，提示用户
if defined STONK_SERVER_HOST (
    echo [INFO] Connecting to remote server: %STONK_SERVER_HOST%:%STONK_SERVER_PORT%
    echo [INFO] Make sure the server is accessible from your network
    echo.
)

:: Set PYTHONPATH to current directory
set PYTHONPATH=%CD%

:: Start Client UI (foreground, logs output to console)
echo [STARTING] Client UI...
echo [INFO] Client logs will be displayed in this console window
echo.

python client/ui/main_window.py

echo.
echo [DONE] Client closed
pause
