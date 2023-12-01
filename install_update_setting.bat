@echo off
title Windrecorder - installing dependence and updating

cd /d %~dp0

echo -git: updating repository
git pull

echo -updating dependencies
python -m pip install poetry==1.7.1
python -m poetry install

for /F "usebackq tokens=*" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat


@REM update routine
python "%~dp0\update_routine.py"

cls
color 0e
title Windrecorder - Quick Setup
python "%~dp0\onboard_setting.py"

pause