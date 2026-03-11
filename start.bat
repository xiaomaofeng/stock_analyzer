@echo off
chcp 65001 >nul
echo =========================================
echo    股票分析系统
echo =========================================
echo.

REM 切换到脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

echo 工作目录: %CD%
echo.

REM 清理已有进程
echo [1/3] 检查并清理已有进程...
taskkill /F /IM "streamlit.exe" 2>nul >nul
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq stock_analyzer*" 2>nul >nul
timeout /t 2 /nobreak >nul
echo      清理完成
echo.

REM 清理Python缓存
echo [2/3] 清理缓存...
rmdir /s /q web\pages\__pycache__ 2>nul >nul
rmdir /s /q config\__pycache__ 2>nul >nul
rmdir /s /q database\__pycache__ 2>nul >nul
echo      清理完成
echo.

REM 确保数据目录存在
echo [3/3] 检查数据目录...
if not exist "data" mkdir data
echo      检查完成
echo.

REM 启动Web服务
echo 正在启动Web服务...
echo 访问地址: http://localhost:8501
echo.
echo 提示: 首次使用请点击左侧 "股票查询" 输入代码如 159892
echo.

REM 使用call确保正确传递控制
call venv\Scripts\streamlit run web\app.py --server.runOnSave false --server.maxUploadSize 200
echo.
echo 服务已停止
pause
