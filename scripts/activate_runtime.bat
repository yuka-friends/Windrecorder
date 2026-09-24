@echo off
rem Called by every launcher; preserve its working directory for legacy extensions.
set "WR_ROOT=%~dp0.."
if not exist "%WR_ROOT%\.venv\Scripts\python.exe" goto setup
if not exist "%WR_ROOT%\.uv-state.json" goto setup
"%WR_ROOT%\.venv\Scripts\python.exe" -c "import json,sys; sys.exit(json.load(open(sys.argv[1])).get('status') != 'ready')" "%WR_ROOT%\.uv-state.json"
if not errorlevel 1 goto ready
:setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 exit /b 1
:ready
call "%WR_ROOT%\.venv\Scripts\activate.bat"
exit /b 0
