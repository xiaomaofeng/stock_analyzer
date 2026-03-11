@echo off
title Stock Analyzer Launcher

echo =========================================
echo    Stock Analyzer System
echo =========================================
echo.

REM Change to script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Run PowerShell script
powershell -ExecutionPolicy Bypass -File "start.ps1"

pause
