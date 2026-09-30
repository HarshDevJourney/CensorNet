$envFile = ".env"

$Count = 4

if (Test-Path $envFile) {
    $line = Get-Content $envFile |
        Where-Object { $_ -match "^WORKER_COUNT=" }

    if ($line) {
        $Count = [int]($line -replace "^WORKER_COUNT=", "")
    }
}

Write-Host "Starting $Count workers..."

for ($i = 1; $i -le $Count; $i++) {
    Start-Process powershell -ArgumentList `
        "-NoExit", `
        "-Command", `
        "python -m app.workers.worker"

    Write-Host "Worker $i started"
}

Write-Host "All $Count workers started."