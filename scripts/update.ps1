$ErrorActionPreference = 'Stop'
try {
    Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
    Write-Host '[Update 1/2] Checking the current branch...' -ForegroundColor Cyan
    $branch = & git branch --show-current
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the current Git branch. Check this checkout before retrying.' }
    $branch = "$branch".Trim()
    $upstream = ''
    if ($branch) {
        $upstream = & git for-each-ref '--format=%(upstream)' -- "refs/heads/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Cannot read the Git tracking configuration.' }
        $upstream = "$upstream".Trim()
    }
    if ($upstream) {
        Write-Host "Updating $branch from its configured upstream..." -ForegroundColor Cyan
        Write-Host 'Waiting for the network can take a while. Git will print its result below.'
        & git pull --ff-only
        if ($LASTEXITCODE -ne 0) { throw 'Git update failed. Resolve the reported problem before retrying.' }
    } else {
        if ($branch) {
            Write-Host "Branch '$branch' has no upstream. Skipping the Git update." -ForegroundColor Yellow
        } else {
            Write-Host 'This checkout is at a detached revision. Skipping the Git update.' -ForegroundColor Yellow
        }
        Write-Host 'Continuing setup using the code already in this checkout.'
    }
    # Start a fresh script process so a git update uses the new installer code.
    Write-Host '[Update 2/2] Preparing the application environment...' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\setup.ps1" -LaunchScript onboard_setting.py
    exit $LASTEXITCODE
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
