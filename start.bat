@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo =========================================
echo    股票分析系统 (Web版)
echo =========================================
echo.

:: 清理端口
powershell -Command "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

:: 启动
echo 正在启动 Web 服务...
echo 访问地址: http://localhost:8501
echo.
venv\Scripts\streamlit.exe run web\app.py --server.port 8501 --server.runOnSave false

echo.
echo 服务已停止
pause
