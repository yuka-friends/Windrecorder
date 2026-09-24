$ErrorActionPreference = 'Stop'
try {
    Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
    & git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git update failed. Resolve the reported problem before retrying.' }
    # Start a fresh script process so a git update uses the new installer code.
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\setup.ps1" -LaunchScript onboard_setting.py
    exit $LASTEXITCODE
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
