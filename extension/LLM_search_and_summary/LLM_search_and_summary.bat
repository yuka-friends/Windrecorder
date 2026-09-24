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
title LLM search and summary - AI-based natural language search - windrecorder
python -m streamlit run "extension\LLM_search_and_summary\_webui.py"
pause
