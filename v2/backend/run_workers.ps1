# Starts the workers.   Works from any folder:
#
#   .\run_workers.ps1                 -> WORKER_COUNT workers, each in its OWN window (default 2, set in .env)
#   .\run_workers.ps1 -Count 4        -> 4 windows
#   .\run_workers.ps1 -SingleWindow   -> all workers in THIS terminal (one window, mixed log lines)
param(
    [int]$Count = 0,
    [switch]$SingleWindow
)

$here = $PSScriptRoot                      # the backend folder, wherever this script is started from

# ---- how many workers
if ($Count -le 0) {
    $Count = 2
    $envFile = Join-Path $here ".env"
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match "^WORKER_COUNT=" }
        if ($line) { $Count = [int](($line -replace "^WORKER_COUNT=", "").Trim()) }
    }
}

# ---- which Python: the project's venv, but only if it really has the backend packages installed.
#      (A venv on Python 3.13/3.14 usually has NOTHING installed because torch/tokenizers have no wheels
#       for it; then we fall back to the Python 3.11 launcher, then to python on PATH.)
function Test-Python($exe, $prefix) {
    & $exe @prefix -c "import pydantic_settings, sqlalchemy, redis" 2>$null
    return ($LASTEXITCODE -eq 0)
}

$python = $null
$pyPrefix = @()

$venvPython = Join-Path $here ".venv\Scripts\python.exe"
if ((Test-Path $venvPython) -and (Test-Python $venvPython @())) {
    $python = (Resolve-Path $venvPython).Path
}
if (-not $python) {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher -and (Test-Python $launcher.Source @("-3.11"))) {
        $python = $launcher.Source
        $pyPrefix = @("-3.11")
    }
}
if (-not $python) {
    $onPath = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($onPath -and (Test-Python $onPath.Source @())) { $python = $onPath.Source }
}
if (-not $python) {
    Write-Host ""
    Write-Host "No Python with the backend packages installed was found." -ForegroundColor Red
    Write-Host "Create a Python 3.11 venv and install them (in the backend folder):"
    Write-Host "    py -3.11 -m venv .venv"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    pip install -r requirements.txt"
    exit 1
}
Write-Host ("Using: " + $python + " " + ($pyPrefix -join " "))

# ---- check everything BEFORE opening windows, so a problem shows here instead of in N crashed windows
& $python @pyPrefix (Join-Path $here "check_setup.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Workers NOT started. Fix the items marked X above, then run this again." -ForegroundColor Red
    exit 1
}

if ($SingleWindow) {
    Write-Host "Starting $Count workers in this window (Ctrl+C stops all)..."
    & $python @pyPrefix (Join-Path $here "run_workers.py") -n $Count
    exit $LASTEXITCODE
}

Write-Host "Starting $Count workers (one window each)..."
$prefixText = $pyPrefix -join " "
for ($i = 1; $i -le $Count; $i++) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$here'; & '$python' $prefixText -m app.workers.worker"
    Write-Host "Worker $i started"
}
Write-Host "Done. Each window should say 'worker ... ready' after the models load (first time: a few minutes)."
