# Starts WORKER_COUNT worker processes, each in its own PowerShell window.
# Run from any folder:   .\run_workers.ps1          (or  .\run_workers.ps1 -Count 4)
param([int]$Count = 0)

$here = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$envFile = Join-Path $here ".env"
if ($Count -le 0) {
    $Count = 2
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match "^WORKER_COUNT=" }
        if ($line) { $Count = [int](($line -replace "^WORKER_COUNT=", "").Trim()) }
    }
}

# Use the project virtualenv only when its backend dependencies are usable. The
# current project venv is Python 3.14, for which tokenizers has no wheel.
$python = $null
$pythonArgs = ""
$venvPython = Join-Path $here ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -c "import pydantic_settings" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $python = (Resolve-Path $venvPython).Path
    }
}

if (-not $python) {
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & $pyLauncher.Source -3.11 -c "import pydantic_settings" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $python = $pyLauncher.Source
            $pythonArgs = "-3.11"
        }
    }
}

if (-not $python) {
    throw "No usable Python environment found. Install backend\requirements.txt in the project venv or install Python 3.11 dependencies."
}

Write-Host "Starting $Count workers..."
for ($i = 1; $i -le $Count; $i++) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$here'; & '$python' $pythonArgs -m app.workers.worker"
    Write-Host "Worker $i started"
}
Write-Host "All $Count workers started. Close a window (or Ctrl+C in it) to stop that worker."
