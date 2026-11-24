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

# Transformers 4.41.0 depends on tokenizers 0.19.x. That dependency has no
# Windows/Python 3.14 wheel, so prefer the dedicated Python 3.11 environment.
$python = $null
$pythonArgs = ""
$venvCandidates = @(
    (Join-Path $here ".venv311\Scripts\python.exe"),
    (Join-Path $here ".venv\Scripts\python.exe")
)
foreach ($venvPython in $venvCandidates) {
    if (-not $python -and (Test-Path $venvPython)) {
        & $venvPython -c "import sys, pydantic_settings; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $python = (Resolve-Path $venvPython).Path
        }
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
    throw "No usable Python 3.11 environment found. Run .\setup_backend.ps1 to install backend\requirements.txt."
}

Write-Host "Starting $Count workers..."
for ($i = 1; $i -le $Count; $i++) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$here'; & '$python' $pythonArgs -m app.workers.worker"
    Write-Host "Worker $i started"
}
Write-Host "All $Count workers started. Close a window (or Ctrl+C in it) to stop that worker."
