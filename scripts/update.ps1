$ErrorActionPreference = 'Stop'
try {
    Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
    Write-Host '[Update 1/2] Connecting to the repository and checking for updates...' -ForegroundColor Cyan
    Write-Host 'Waiting for the network can take a while. Git will print its result below.'
    & git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git update failed. Resolve the reported problem before retrying.' }
    # Start a fresh script process so a git update uses the new installer code.
    Write-Host '[Update 2/2] Preparing the application environment...' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\setup.ps1" -LaunchScript onboard_setting.py
    exit $LASTEXITCODE
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
