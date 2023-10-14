@echo off

title Windrecorder - Webui Dashboard: http://localhost:8501     == Windrecorder == Windrecorder == Windrecorder ==

REM 判断是否存在 env 文件夹
if not exist "env" (
  python -m venv env
)

SET folderPath=%~dp0
SET PATH=%PATH%;%folderPath:~0,-1%\env\Scripts
call env\Scripts\activate.bat

color 7D
echo Starting webui...
cd /d %~dp0
python -m streamlit run "%~dp0\webui.py"
pause