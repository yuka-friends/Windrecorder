@echo off
title Windrecorder - Offline installation of dependencies
mode con cols=150 lines=50

cd /d %~dp0

echo ---------------------------------------------------
echo Offline installation of Poetry
echo ---------------------------------------------------
rem Install Poetry from the offsine_deps directory
python -m pip install --no-index --find-links=%~dp0offline_deps poetry

echo ---------------------------------------------------
echo Configure Poetry to place the virtual environment within the project
echo ---------------------------------------------------
python -m poetry config virtualenvs.in-project true

echo ---------------------------------------------------
echo Create (or update) a Poetry virtual environment
echo ---------------------------------------------------
rem Create or update virtual environments using native Python
python -m poetry env use python

echo ---------------------------------------------------
echo Activate the Poetry virtual environment
echo ---------------------------------------------------
for /F "usebackq tokens=*" %%A in (`python -m poetry env info --path`) do set VENV_PATH=%%A
call "%VENV_PATH%\Scripts\activate.bat"

echo ---------------------------------------------------
echo Offline installation project dependencies
echo ---------------------------------------------------
rem Install dependencies listed in requirements. txt offline through pip
pip install --no-index --find-links=%~dp0offline_deps -r offline_deps\requirements.txt


color 0e
title Windrecorder - Quick Settings
python "%~dp0\onboard_setting.py"

pause
