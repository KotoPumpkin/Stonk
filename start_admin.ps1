# Stonk - 管理员端启动脚本
# 此脚本会启动 WebSocket 服务器和管理员 UI

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Stonk - 股票模拟交易系统" -ForegroundColor Cyan
Write-Host "  管理员端启动程序" -ForegroundColor Cyan
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

# 设置 PYTHONPATH 为项目根目录
$env:PYTHONPATH = (Get-Location).Path
Write-Host "[OK] PYTHONPATH 已设置为：$env:PYTHONPATH" -ForegroundColor Green

# 启动 WebSocket 服务器（后台）
Write-Host "`n[启动] 启动 WebSocket 服务器..." -ForegroundColor Yellow
$serverJob = Start-Job -ScriptBlock {
    param($projectPath)
    $env:PYTHONPATH = $projectPath
    Set-Location $projectPath
    python server/websocket_server.py
} -ArgumentList (Get-Location).Path

Write-Host "[等待] 等待服务器启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Write-Host "[OK] WebSocket 服务器已启动 (ws://localhost:8765)" -ForegroundColor Green

# 启动管理员 UI
Write-Host "`n[启动] 启动管理员 UI..." -ForegroundColor Yellow
python server/admin_ui.py

# 清理后台任务（当 UI 关闭时）
Write-Host "`n[清理] 停止 WebSocket 服务器..." -ForegroundColor Yellow
Stop-Job -Job $serverJob
Remove-Job -Job $serverJob
Write-Host "[完成] 管理员端已关闭" -ForegroundColor Green
