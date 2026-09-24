param(
    [ValidateSet('rapidocr', 'wechat', 'embedding')][string]$AddExtra,
    [ValidateSet('rapidocr', 'wechat', 'embedding')][string]$RemoveExtra,
    [switch]$Rollback,
    [ValidateSet('main.py', 'onboard_setting.py')][string]$LaunchScript
)
$ErrorActionPreference = 'Stop'
try {
    $root = Split-Path $PSScriptRoot -Parent
    Set-Location -LiteralPath $root
    Write-Host '[Setup] Checking the package manager...' -ForegroundColor Cyan
    # Extensions/old installers may call us after activating a Poetry environment.
    # Bootstrap pip and uv must come from outside the environment being replaced.
    if ($env:VIRTUAL_ENV) {
        $activeScripts = (Join-Path $env:VIRTUAL_ENV 'Scripts').TrimEnd('\')
        $env:PATH = (($env:PATH -split ';') | Where-Object { $_.TrimEnd('\') -ne $activeScripts }) -join ';'
        Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
    }
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCommand) {
        $uvPath = $uvCommand.Source
        $uvVersion = (& $uvPath --version).Split(' ')[1]
    }
    if (-not $uvCommand -or [version]$uvVersion -lt [version]'0.12.18') {
        # Existing users already have Python; install uv without changing that interpreter.
        $uvPath = (& python -c "import os,sysconfig; print(os.path.join(sysconfig.get_path('scripts', scheme='nt_user'), 'uv.exe'))").Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Cannot locate uv.' }
        $installUv = -not (Test-Path -LiteralPath $uvPath)
        if (-not $installUv) { $installUv = [version]((& $uvPath --version).Split(' ')[1]) -lt [version]'0.12.18' }
        if ($installUv) {
            Write-Host '[Setup] Downloading and installing uv. Please wait...' -ForegroundColor Cyan
            & python -m pip install --user 'uv>=0.12.18'
            if ($LASTEXITCODE -ne 0) { throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and retry.' }
        }
    }
    # The migration controller must run outside the environment it replaces.
    if (-not $Rollback) {
        Write-Host '[Setup] Checking Python 3.12 and downloading an update if needed...' -ForegroundColor Cyan
        & $uvPath python install --upgrade 3.12
        if ($LASTEXITCODE -ne 0) { throw 'Python download failed; existing environment has not been changed.' }
    }
    Write-Host '[Setup] Locating Python...' -ForegroundColor Cyan
    $controllerPython = (& $uvPath python find --managed-python 3.12).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot locate managed Python 3.12.' }
    $arguments = @("$PSScriptRoot\manage_environment.py", '--uv', $uvPath)
    if ($AddExtra) { $arguments += @('--add-extra', $AddExtra) }
    if ($RemoveExtra) { $arguments += @('--remove-extra', $RemoveExtra) }
    if ($Rollback) { $arguments += '--rollback' }
    Write-Host '[Setup] Preparing dependencies and checking the environment...' -ForegroundColor Cyan
    & $controllerPython @arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($LaunchScript) {
        Write-Host '[Setup] Environment ready. Opening the application setup...' -ForegroundColor Cyan
        & "$root\.venv\Scripts\python.exe" "$root\$LaunchScript"
    }
    exit $LASTEXITCODE
} catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
