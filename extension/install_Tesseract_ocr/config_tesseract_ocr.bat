@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
chcp 65001

for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat
python _test_install.py
echo.
echo   The installation script has been completed. 已执行完安装脚本。
echo.
pause
exit