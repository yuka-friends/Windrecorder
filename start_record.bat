@echo off
title Windrecorder - Recording Screening      == Windrecorder == Windrecorder == Windrecorder ==

cd /d %~dp0
for /F "usebackq delims=" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat

color 60
echo Starting Recording Screen...

python "%~dp0\recordScreen.py"
pause