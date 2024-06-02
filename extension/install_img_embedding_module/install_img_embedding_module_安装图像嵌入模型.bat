@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call "%%A\Scripts\activate.bat"
chcp 65001

:start_install
cls
echo.
echo   This script will install the image semantic indexing function for Windrecorder.
echo   After installation, you can index and search for corresponding images using natural language descriptions.
echo   This functionality is powered by the unum-cloud/uform model.
echo.
echo   本向导将为捕风记录仪安装图像语义索引功能。安装完毕后，可以索引并用自然语言描述来搜索对应画面。
echo.
echo   Enter Y and press Enter to install the image semantic recognition module.
echo   输入 Y 后回车以安装图像语义识别模块。
echo.
echo   ================================================================================
echo.
set /p choice=   Please enter the options and press Enter:

if /I "%choice%"=="Y" (
    echo Installing...
    goto install_module
)

goto start_install


@REM -------------------------------------------------
:install_module
poetry run pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uform
goto :finish


@REM -------------------------------------------------
:finish
echo.
echo   checking the installation results... 检查安装结果……
echo.
python _test_install.py
echo.
echo   The installation script has been completed. 已执行完安装脚本。
echo.
pause
exit