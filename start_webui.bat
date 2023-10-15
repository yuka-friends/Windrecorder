@echo off

title Windrecorder - Webui Dashboard: http://localhost:8501     == Windrecorder == Windrecorder == Windrecorder ==

REM 判断是否存在 env 文件夹
if not exist "env" (
  python -m venv env
)

call env\Scripts\activate.bat

color 7D
echo Starting webui...
echo 初次使用时，可直接回车跳过 streamlit 营销邮件收集
echo When opened at the first time, you can simply press Enter to skip the collection of Streamlit marketing emails.
cd /d %~dp0
python -m streamlit run "%~dp0\webui.py"
pause