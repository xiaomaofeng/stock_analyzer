@echo off
chcp 65001 >nul
echo =========================================
echo    股票分析系统
echo =========================================
echo.

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

echo 正在启动Web服务...
echo.

%SCRIPT_DIR%venv\Scripts\streamlit run web\app.py

echo.
echo 服务已停止
pause
