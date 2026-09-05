# IBVAP - Intelligent Border Video Analytics Platform Launcher
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   IBVAP - Intelligent Border Video Analytics Platform (Prototype)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$scriptDir\Team-Cache-Claude\backend\main.py") {
    $rootDir = "$scriptDir\Team-Cache-Claude"
} else {
    $rootDir = $scriptDir
}

# Determine Python Executable
$pythonExe = "C:\Program Files\Python311\python.exe"
if (-not (Test-Path $pythonExe)) {
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) {
        $pythonExe = "py"
    } else {
        $pythonExe = "python"
    }
}
Write-Host "[1/3] Using Python: $pythonExe" -ForegroundColor Green

# Start Backend
Write-Host "[2/3] Launching Backend API on port 8000..." -ForegroundColor Green
$backendArgs = "-m uvicorn main:app --host 127.0.0.1 --port 8000"
Start-Process -FilePath $pythonExe -ArgumentList $backendArgs -WorkingDirectory "$rootDir\backend"

# Start Frontend
Write-Host "[3/3] Launching Frontend Dev Server on port 5173..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $rootDir

Start-Sleep -Seconds 4

Write-Host "Verifying service health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 3
    Write-Host "Backend Status: $($health.status) (Version: $($health.version))" -ForegroundColor Green
} catch {
    Write-Host "Backend is still warming up..." -ForegroundColor Yellow
}

Start-Process "http://localhost:5173"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " IBVAP Prototype is now LIVE:" -ForegroundColor Cyan
Write-Host "   - Frontend UI:  http://localhost:5173" -ForegroundColor White
Write-Host "   - Backend API:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "   - Health Check: http://127.0.0.1:8000/api/health" -ForegroundColor White
Write-Host "   - API Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
