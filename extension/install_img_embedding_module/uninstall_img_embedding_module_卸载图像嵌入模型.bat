@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call "%%A\Scripts\activate.bat"
chcp 65001

:start_uninstall
cls
echo.
echo   Make sure to exit windrecorder before uninstallation.
echo   卸载前请确保退出了 捕风记录仪。
echo.
echo   Enter Y and press Enter to uninstall the image semantic recognition module.
echo   输入 Y 后回车卸载图像语义识别模块。
echo.
echo   Provide feedback on this experimental feature: 
echo   对该实验性功能提供建议反馈：
echo       https://github.com/yuka-friends/Windrecorder/issues
echo.
echo   ================================================================================
echo.
set /p choice=   Please enter the options and press Enter:

if /I "%choice%"=="Y" (
    echo Uninstalling...
    goto uninstall_module
)

goto start_uninstall


@REM -------------------------------------------------
:uninstall_module
:: 这不是一个干净的卸载，但可以移除掉大部分的容量。
:: This is not a clean uninstall, but it removes most of the capacity.
poetry run pip uninstall uform
poetry run pip uninstall torch
poetry run pip uninstall torchaudio
poetry run pip uninstall torchvision

python _uninstall.py
echo.
echo   The uninstallation script has been completed. 已执行完卸载脚本。
echo.
pause
exit