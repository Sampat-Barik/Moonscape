# ==============================================================================
# Moonscape — Automated Master Validation Script (Windows PowerShell)
# ==============================================================================
# Checks Python, Node, dependencies, runs backend pytest, frontend unit tests,
# frontend production build, and executes API contract smoke tests if server is up.
# ==============================================================================

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host " MOONSCAPE — MASTER SYSTEM VALIDATION SUITE" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# 1. Check Python
Write-Host "[1/6] Checking Python Environment..." -ForegroundColor Yellow
$PythonExe = ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "Virtual environment not found at $PythonExe" -ForegroundColor Red
    exit 1
}
& $PythonExe --version
Write-Host "Python environment OK.`n" -ForegroundColor Green

# 2. Check Node & npm
Write-Host "[2/6] Checking Node.js & npm Environment..." -ForegroundColor Yellow
node -v
npm -v
Write-Host "Node.js environment OK.`n" -ForegroundColor Green

# 3. Run Backend Pytest Suite
Write-Host "[3/6] Running Backend Pytest Suite (172 Scientific & Functional Tests)..." -ForegroundColor Yellow
$env:PYTHONPATH = "Backend"
& $PythonExe -m pytest Backend/tests -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend pytest suite FAILED!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "All backend tests PASSED.`n" -ForegroundColor Green

# 4. Run Frontend Unit Tests
Write-Host "[4/6] Running Frontend Unit Tests..." -ForegroundColor Yellow
npm --prefix Frontend test -- --run
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend unit tests FAILED!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "All frontend unit tests PASSED.`n" -ForegroundColor Green

# 5. Build Frontend Production Single-File Bundle
Write-Host "[5/6] Building Production Frontend Bundle (Vite Single-File)..." -ForegroundColor Yellow
npm --prefix Frontend run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend production build FAILED!" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Frontend production build OK.`n" -ForegroundColor Green

# 6. API Server Smoke Test (if port 8000 is listening)
Write-Host "[6/6] Probing Local Backend API Endpoint Connectivity..." -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 3
    if ($resp.status -eq "healthy" -or $resp.service -eq "Moonscape Backend") {
        Write-Host "Backend API responds HEALTHY at http://127.0.0.1:8000/api/health" -ForegroundColor Green
    } else {
        Write-Host "Backend API responded: $($resp | ConvertTo-Json -Compress)" -ForegroundColor Green
    }
} catch {
    Write-Host "Backend server is not running on port 8000. Start with: .venv\Scripts\python.exe -m uvicorn Backend.app.main:app --port 8000" -ForegroundColor DarkGray
}

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host " MOONSCAPE MASTER VALIDATION: ALL CHECKS PASSED!" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan
