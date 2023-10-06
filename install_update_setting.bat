@echo off
call env\Scripts\activate.bat
title Windrecorder - Quick Setup
cd /d %~dp0

rem 安装与更新requirement.txt依赖
pip install -r requirements.txt

rem 更新GitHub仓库
@REM git pull

cls
color 0e
python "%~dp0\onboard_setting.py"





pause