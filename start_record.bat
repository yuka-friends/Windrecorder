@echo off
call env\Scripts\activate.bat

color 2f
title Windrecorder - Recording Screening
echo Starting Recording Screen...
cd /d %~dp0
python "%~dp0\recordScreen.py"
pause