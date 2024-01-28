@echo off
title Windrecorder - installing dependence and updating

cd /d %~dp0

echo -git: updating repository
git pull

echo -updating dependencies
python -m pip install poetry==1.7.1
python -m poetry config virtualenvs.in-project true
python -m poetry install

for /F "usebackq tokens=*" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat

cls
color 0e
title Windrecorder - Quick Setup
echo 新升级的版本基于 python 3.11，请根据以下步骤更新：
echo - 下载并安装 python 3.11 （需要勾选加入 PATH 选型）：https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe
echo - 删除目录下的 .venv 文件夹，或先前位于 的虚拟环境；
echo - 重新打开这个安装设置脚本即可；
python "%~dp0\onboard_setting.py"

pause