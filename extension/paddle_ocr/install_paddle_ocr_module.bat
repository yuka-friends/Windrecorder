@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat
chcp 65001

:start_install
cls
echo   Installation options (install the download in the virtual environment of Windrecorder):
echo   安装选项（将下载安装在 Windrecorder 的虚拟环境中）：
echo.
echo   1. Install a version that supports CUDA acceleration for Nvidia graphics cards;
echo      安装支持 Nvidia 显卡 CUDA 加速的版本；
echo.
echo   2. Install CPU version; 安装 CPU 版本；
echo.
echo.
set /p choice=   Please enter the options and press Enter:

if "%choice%"=="1" (
    echo Installing an environment that supports CUDA acceleration; 正在安装支持 CUDA 加速的环境
    goto install_cuda
)

if "%choice%"=="2" (
    echo Installing an environment that supports CPU computing; 正在安装支持 CPU 运算的环境
    goto install_cpu
)

goto start_install


@REM -------------------------------------------------
:install_cpu
poetry run pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
goto :finish


@REM -------------------------------------------------
:install_cuda
poetry run pip install paddlepaddle-gpu==2.6.1.post120 -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html
poetry run pip install paddleocr


@REM -------------------------------------------------
:finish
echo.
echo   checking the installation results... 检查安装结果……
echo.
python test_install.py
echo.
echo   The installation script has been completed. 已执行完安装脚本。
echo.
pause
exit