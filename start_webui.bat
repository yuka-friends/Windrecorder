@echo off
call env\Scripts\activate.bat

color 7D
title Windrecorder - Webui Dashboard: http://localhost:8501
echo Starting webui...
cd /d %~dp0
python -m streamlit run "%~dp0\webui.py"
pause