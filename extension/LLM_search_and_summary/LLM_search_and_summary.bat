@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call "%%A\Scripts\activate.bat"
chcp 65001
cls
cd ..
cd ..

:: extension code below
title LLM search and summary - AI-based natural language search - windrecorder
streamlit run "extension\LLM_search_and_summary\_webui.py"
pause