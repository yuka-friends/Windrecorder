@echo off
title Windrecorder - Recording Screening      == Windrecorder == Windrecorder == Windrecorder ==

for /F "usebackq delims=" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat

color 60
echo Starting Recording Screen...
cd /d %~dp0
python "%~dp0\recordScreen.py"
pause