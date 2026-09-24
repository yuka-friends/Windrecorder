@echo off
title Windrecorder
mode con cols=70 lines=10
color 75
echo.
echo   Initializing Windrecorder, please stand by...
echo.
echo   Please stay in this window until it disappears
echo.

cd /d "%~dp0"
call "%~dp0scripts\activate_runtime.bat"
if errorlevel 1 (
    pause
    exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -u "%~dp0scripts\launch_app.py"
if errorlevel 1 (
    echo.
    echo Windrecorder could not start. Check cache\logs\startup.log for details.
    pause
    exit /b 1
)
