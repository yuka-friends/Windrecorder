@echo off
color 0E
echo Starting webui...
cd /d %~dp0
python -m streamlit run "%~dp0\webui.py"
pause