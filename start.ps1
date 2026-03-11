# Stock Analyzer Startup Script
$ErrorActionPreference = "SilentlyContinue"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   Stock Analyzer System" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Host "Working Directory: $(Get-Location)" -ForegroundColor Gray
Write-Host ""

# Kill existing processes
Write-Host "[Step 1/3] Cleaning up existing processes..." -ForegroundColor Yellow

# Kill processes using port 8501
$portProcesses = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $portProcesses) {
    if ($procId) {
        Stop-Process -Id $procId -Force
        Write-Host "           Killed process PID:$procId" -ForegroundColor Gray
    }
}

# Kill all streamlit processes
Get-Process "streamlit" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "           Cleanup done" -ForegroundColor Green
Write-Host ""

# Clean cache
Write-Host "[Step 2/3] Cleaning cache..." -ForegroundColor Yellow
Get-ChildItem -Path "." -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "           Cache cleaned" -ForegroundColor Green
Write-Host ""

# Ensure data directory exists
Write-Host "[Step 3/3] Checking data directory..." -ForegroundColor Yellow
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}
Write-Host "           Directory OK" -ForegroundColor Green
Write-Host ""

# Set environment variables
$env:STREAMLIT_SERVER_HEADLESS = "true"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

# Start service
Write-Host "Starting Web Server..." -ForegroundColor Green
Write-Host "URL: " -NoNewline
Write-Host "http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tip: Click 'Stock Query' on left side, enter code like 159892" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Start streamlit
& "$scriptDir\venv\Scripts\streamlit.exe" run web\app.py --server.port 8501 --server.runOnSave false

Write-Host ""
Write-Host "Server stopped" -ForegroundColor Red
