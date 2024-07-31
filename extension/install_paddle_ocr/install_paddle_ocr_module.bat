@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat
chcp 65001

:start_install
cls
echo.
echo   This guide will add Paddle OCR as the optical text recognition engine for Windrecorder.
echo   本向导将为捕风记录仪添加 Paddle OCR 作为光学文本识别引擎。
echo.
echo   Support languages: en-US, zh-Hans, zh-Hant
echo   支持语言：英文, 简体中文, 繁体中文
echo.
echo   Enter Y and press Enter to install RapidOCR (Paddle OCR based on ONNXRuntime) module.
echo   输入 Y 后回车以安装 RapidOCR（Paddle OCR 的 ONNXRuntime 版本）。
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
poetry run pip install rapidocr_onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple
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