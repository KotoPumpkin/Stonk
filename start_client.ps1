# Stonk - 客户端启动脚本 (PowerShell)
# 支持跨机器连接配置

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Stonk - 股票模拟交易系统" -ForegroundColor Cyan
Write-Host "  客户端启动程序" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python 已安装：$pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# ==================== 服务器地址配置 ====================
# 默认连接本地服务器，如需连接远程服务器，请修改下面的变量
# $env:STONK_SERVER_HOST = "192.168.1.100"  # 服务器 IP 地址
# $env:STONK_SERVER_PORT = "8765"           # 服务器端口

# 显示当前服务器配置
if ($env:STONK_SERVER_HOST) {
    Write-Host "[CONFIG] 服务器地址：$env:STONK_SERVER_HOST" -ForegroundColor Yellow
} else {
    Write-Host "[CONFIG] 服务器地址：127.0.0.1 (本地)" -ForegroundColor Gray
}

if ($env:STONK_SERVER_PORT) {
    Write-Host "[CONFIG] 服务器端口：$env:STONK_SERVER_PORT" -ForegroundColor Yellow
} else {
    Write-Host "[CONFIG] 服务器端口：8765" -ForegroundColor Gray
}

if ($env:STONK_SERVER_HOST) {
    Write-Host ""
    Write-Host "[提示] 正在连接到远程服务器：$env:STONK_SERVER_HOST`:$env:STONK_SERVER_PORT" -ForegroundColor Yellow
    Write-Host "[提示] 请确保服务器可访问且防火墙已开放端口" -ForegroundColor Yellow
}

Write-Host ""

# 设置 PYTHONPATH 为项目根目录
$env:PYTHONPATH = (Get-Location).Path
Write-Host "[OK] PYTHONPATH 已设置为：$env:PYTHONPATH" -ForegroundColor Green

# 启动客户端 UI（前台，日志输出到控制台）
Write-Host "`n[启动] 启动客户端 UI..." -ForegroundColor Yellow
Write-Host "[提示] 客户端日志将在此控制台窗口显示" -ForegroundColor Gray
Write-Host ""

# 直接在前台运行客户端，这样日志会输出到当前控制台
python client/ui/main_window.py

Write-Host "`n[完成] 客户端已关闭" -ForegroundColor Green
