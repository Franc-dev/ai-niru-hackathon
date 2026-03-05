# Start All Services Script
# This starts: Sklearn+RAG Server, Backend, and Frontend

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "STARTING AI NIRU MENTAL HEALTH ASSISTANT" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Check if services are already running
Write-Host "[1/3] Checking existing services..." -ForegroundColor Yellow

$port8002 = netstat -ano | findstr ":8002" | findstr "LISTENING"
$port8000 = netstat -ano | findstr ":8000" | findstr "LISTENING"
$port5173 = netstat -ano | findstr ":5173" | findstr "LISTENING"

if ($port8002) {
    Write-Host "   - Port 8002 (Sklearn+RAG) already in use" -ForegroundColor Yellow
} else {
    Write-Host "   - Port 8002 free" -ForegroundColor Green
}

if ($port8000) {
    Write-Host "   - Port 8000 (Backend) already in use" -ForegroundColor Yellow
} else {
    Write-Host "   - Port 8000 free" -ForegroundColor Green
}

if ($port5173) {
    Write-Host "   - Port 5173 (Frontend) already in use" -ForegroundColor Yellow
} else {
    Write-Host "   - Port 5173 free" -ForegroundColor Green
}

Write-Host "`n[2/3] Starting services..." -ForegroundColor Yellow

# Start Sklearn+RAG Server (port 8002)
if (-not $port8002) {
    Write-Host "   - Starting Sklearn+RAG Server on http://localhost:8002..." -ForegroundColor Cyan
    Start-Process -NoNewWindow -FilePath "training_env\Scripts\python.exe" -ArgumentList "training\scripts\4_serve_sklearn_rag.py"
    Start-Sleep -Seconds 5
    Write-Host "     Started!" -ForegroundColor Green
} else {
    Write-Host "   - Sklearn+RAG Server already running" -ForegroundColor Yellow
}

# Start Backend (port 8000)
if (-not $port8000) {
    Write-Host "   - Starting Backend on http://localhost:8000..." -ForegroundColor Cyan
    Start-Process -NoNewWindow -FilePath "venv\Scripts\uvicorn.exe" -ArgumentList "backend.main:app --reload --port 8000"
    Start-Sleep -Seconds 3
    Write-Host "     Started!" -ForegroundColor Green
} else {
    Write-Host "   - Backend already running" -ForegroundColor Yellow
}

# Start Frontend (port 5173)
if (-not $port5173) {
    Write-Host "   - Starting Frontend on http://localhost:5173..." -ForegroundColor Cyan
    Start-Process -NoNewWindow -WorkingDirectory "frontend" -FilePath "npm.cmd" -ArgumentList "run dev"
    Start-Sleep -Seconds 3
    Write-Host "     Started!" -ForegroundColor Green
} else {
    Write-Host "   - Frontend already running" -ForegroundColor Yellow
}

Write-Host "`n[3/3] Service Status:" -ForegroundColor Yellow
Start-Sleep -Seconds 2

$status8002 = netstat -ano | findstr ":8002" | findstr "LISTENING"
$status8000 = netstat -ano | findstr ":8000" | findstr "LISTENING"
$status5173 = netstat -ano | findstr ":5173" | findstr "LISTENING"

if ($status8002) {
    Write-Host "   [OK] Sklearn+RAG Server: http://localhost:8002" -ForegroundColor Green
} else {
    Write-Host "   [FAIL] Sklearn+RAG Server not running" -ForegroundColor Red
}

if ($status8000) {
    Write-Host "   [OK] Backend API: http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "   [FAIL] Backend not running" -ForegroundColor Red
}

if ($status5173) {
    Write-Host "   [OK] Frontend UI: http://localhost:5173" -ForegroundColor Green
} else {
    Write-Host "   [FAIL] Frontend not running" -ForegroundColor Red
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "SERVICES STARTED!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "`nOpen your browser: http://localhost:5173" -ForegroundColor Yellow
Write-Host "`nTo test the system:" -ForegroundColor Yellow
Write-Host "  - Swahili: 'Nahisi huzuni sana'" -ForegroundColor White
Write-Host "  - English: 'I feel very anxious'" -ForegroundColor White
Write-Host "  - Crisis: 'Nataka kujiua' (should show emergency hotline)" -ForegroundColor White
Write-Host "`nPress Ctrl+C in each terminal to stop services`n" -ForegroundColor Gray
