@echo off

title Windrecorder - Webui Dashboard: http://localhost:8501     == Windrecorder == Windrecorder == Windrecorder ==

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat

color 7D
echo Starting webui...
echo When opened at the first time, you can simply press Enter to skip the collection of Streamlit marketing emails.

python -m streamlit run "%~dp0\webui.py"
pause