@echo off
title Windrecorder - installing dependence and updating

@REM SET folderPath=%~dp0
@REM SET PATH=%PATH%;%folderPath:~0,-1%\python

if not exist "env" (
  echo -installing virtual environment
  pip install virtualenv
  echo -creating virtual environment
  python -m venv env
)

call env\Scripts\activate.bat
cd /d %~dp0

echo -updating dependencies
pip install -r requirements.txt

echo -git: updating repository
git pull

cls
color 0e
title Windrecorder - Quick Setup
python "%~dp0\onboard_setting.py"

pause