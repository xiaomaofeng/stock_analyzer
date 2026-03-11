@echo off
chcp 65001 >nul
echo =========================================
echo    股票分析系统 - 159892已就绪
echo =========================================
echo.
echo 正在启动Web服务...
echo.
cd %~dp0
cd web
..
venv\Scripts\streamlit run app.py
echo.
echo 服务已停止
pause
