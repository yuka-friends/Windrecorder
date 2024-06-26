@echo off
title Windrecorder - installing dependence and updating
mode con cols=150 lines=50

cd /d %~dp0

echo -git: updating repository
git pull

echo -updating dependencies
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple poetry
python -m poetry config virtualenvs.in-project true
python -m poetry install

for /F "usebackq tokens=*" %%A in (`python -m poetry env info --path`) do call "%%A\Scripts\activate.bat"

color 0e
title Windrecorder - Quick Setup
python "%~dp0\onboard_setting.py"

pause