@echo off
title Windrecorder - Recording Screening      == Windrecorder == Windrecorder == Windrecorder ==

REM 判断是否存在 env 文件夹
if not exist "env" (
  python -m venv env
)
call env\Scripts\activate.bat

color 2f
echo Starting Recording Screen...
cd /d %~dp0
python "%~dp0\recordScreen.py"
pause