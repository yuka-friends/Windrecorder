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

if exist "hide_CLI_by_python.txt" (
    goto begin
) else (
    goto hide
)

:hide
@REM hide CLI immediately
if "%1"=="h" goto begin
start mshta vbscript:createobject("wscript.shell").run("%~nx0"^&" h",0)^&(window.close) && exit /b

:begin
cd /d "%~dp0"

"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
