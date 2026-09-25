@echo off
echo Loading extension, please stand by.
echo.

cd /d "%~dp0"
call "%~dp0..\..\scripts\activate_runtime.bat"
if errorlevel 1 (
    pause
    exit /b 1
)
chcp 65001
cls
cd ..
cd ..

:: extension code below
title Custom webui background - windrecorder
python -m streamlit run "extension\set_custom_webui_background\_webui.py"
pause
