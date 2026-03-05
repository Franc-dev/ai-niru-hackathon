# Stop All Services Script
# This stops: Sklearn+RAG Server, Backend, and Frontend

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "STOPPING AI NIRU SERVICES" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Find and kill processes on ports
$ports = @(8002, 8000, 5173)
$portNames = @{
    8002 = "Sklearn+RAG Server"
    8000 = "Backend API"
    5173 = "Frontend UI"
}

foreach ($port in $ports) {
    $connections = netstat -ano | findstr ":$port" | findstr "LISTENING"
    
    if ($connections) {
        # Extract PID (last column)
        $connections -split "`n" | ForEach-Object {
            if ($_ -match '\s+(\d+)$') {
                $pid = $matches[1]
                try {
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Host "[STOPPED] $($portNames[$port]) (PID: $pid)" -ForegroundColor Green
                } catch {
                    Write-Host "[ERROR] Failed to stop $($portNames[$port]) (PID: $pid)" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "[SKIP] $($portNames[$port]) not running" -ForegroundColor Yellow
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "ALL SERVICES STOPPED" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan
