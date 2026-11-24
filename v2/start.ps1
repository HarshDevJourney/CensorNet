# Start CensorNet: PostgreSQL + Redis, the API, the GPU workers, and the frontend.
# From the v2 folder:
#   powershell -ExecutionPolicy Bypass -File .\start.ps1
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Missing $python"
    Write-Host "Create the backend virtualenv first, then install the CUDA PyTorch wheel."
    exit 1
}

function Test-Listening([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Start-Window([string]$Title, [string]$Directory, [string]$Command) {
    $script = "Set-Location -LiteralPath '$Directory'; `$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $script) | Out-Null
    Write-Host "started  $Title"
}

Write-Host "CensorNet"
Set-Location -LiteralPath $root
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose up -d
} else {
    Write-Host "Docker is not on PATH. PostgreSQL and Redis must already be running."
}

$workers = 3
$envFile = Join-Path $backend ".env"
if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^WORKER_COUNT=" } | Select-Object -First 1
    if ($line) { $workers = [int](($line -replace "^WORKER_COUNT=", "").Trim()) }
}

if (Test-Listening 8000) {
    Write-Host "API already listening on http://localhost:8000"
} else {
    Start-Window "CensorNet API" $backend "& '$python' -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
}

if (Test-Listening 3000) {
    Write-Host "Frontend already listening on http://localhost:3000"
} else {
    Start-Window "CensorNet frontend" $frontend "npm run dev"
}

$workersRunning = $false
try {
    $health = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 3
    $workersRunning = [int]$health.workers -ge 1
} catch {
    $workersRunning = $false
}
if ($workersRunning) {
    Write-Host "Workers already online ($($health.workers)). Not starting another set."
} else {
    Start-Window "CensorNet workers" $backend "& '$python' run_workers.py -n $workers"
}
Write-Host ""
Write-Host "Open http://localhost:3000"
Write-Host "API health: http://localhost:8000/health"
if (-not $workersRunning) {
    Write-Host "Started $workers workers. Close the CensorNet workers window to stop them."
}
