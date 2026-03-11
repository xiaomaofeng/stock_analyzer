@echo off
:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 使用相对路径启动
venv\Scripts\streamlit.exe run web\app.py
pause
