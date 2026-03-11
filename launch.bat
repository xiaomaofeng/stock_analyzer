@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo 正在启动股票分析系统...
venv\Scripts\streamlit.exe run web\app.py --server.port 8501
pause
