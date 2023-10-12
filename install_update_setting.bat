@echo off
title Windrecorder - installing dependence and updating
REM 判断是否存在 env 文件夹
if not exist "env" (
  python -m venv env
)

call env\Scripts\activate.bat
cd /d %~dp0

rem 安装与更新requirement.txt依赖
pip install -r requirements.txt

rem 更新GitHub仓库
@REM git pull

cls
color 0e
title Windrecorder - Quick Setup
python "%~dp0\onboard_setting.py"

pause