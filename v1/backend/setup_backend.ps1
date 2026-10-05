# Creates the supported backend environment and installs its dependencies.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$here = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$python = Join-Path $here ".venv311\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if (-not $pyLauncher) {
        throw "Python 3.11 is required. Install Python 3.11, then run this script again."
    }
    & $pyLauncher.Source -3.11 -m venv (Join-Path $here ".venv311")
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $here "requirements.txt")
& $python -m pip check
Write-Host "Backend dependencies installed in .venv311."
