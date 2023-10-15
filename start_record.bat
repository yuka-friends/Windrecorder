@echo off
title Windrecorder - Recording Screening      == Windrecorder == Windrecorder == Windrecorder ==

REM 判断是否存在 env 文件夹
if not exist "env" (
  echo -installing virtual environment
  pip install virtualenv
  echo -creating virtual environment
  python -m venv env
)

cd /d %~dp0
call env\Scripts\activate.bat

color 60
echo Starting Recording Screen...
python "%~dp0\recordScreen.py"
pause