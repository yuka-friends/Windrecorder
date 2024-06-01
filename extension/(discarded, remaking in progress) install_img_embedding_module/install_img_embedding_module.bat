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
echo   本向导将为捕风记录仪安装图像语义索引功能。安装完毕后，可以索引并用自然语言描述来搜索对应画面。
echo.
echo   ================================================================================
echo.
echo   Installation options (install the download in the virtual environment of Windrecorder, occupying about 4G space):
echo   安装选项（将下载安装在 Windrecorder 的虚拟环境中，约占用 4G 空间）：
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
poetry run pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uform
poetry run pip install -i https://pypi.tuna.tsinghua.edu.cn/simple torch
goto :finish


@REM -------------------------------------------------
:install_cuda

:: 查找 Python 版本
for /f "delims=" %%I in ('python --version 2^>^&1') do set "result=%%I"

:: 根据 Python 版本跳转执行命令
echo %result% | findstr /C:"Python 3.10" 1>nul
if errorlevel 1 (
echo %result% | findstr /C:"Python 3.11" 1>nul
if errorlevel 1 (
  echo Other version installed
  goto Other
) else (
  echo Python 3.11 installed
  goto Python311
)) else (
  echo Python 3.10 installed
  goto Python310
)

:Python310
echo Running Python 3.10 specific commands...
@REM using aliyun mirrors
poetry run pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uform
poetry run pip install https://mirrors.aliyun.com/pytorch-wheels/cu121/torch-2.2.0+cu121-cp310-cp310-win_amd64.whl
poetry run pip install https://mirrors.aliyun.com/pytorch-wheels/cu121/torchaudio-2.2.0+cu121-cp310-cp310-win_amd64.whl
poetry run pip install https://mirrors.aliyun.com/pytorch-wheels/cu121/torchvision-0.17.0+cu121-cp310-cp310-win_amd64.whl
goto :finish

:Python311
echo Running Python 3.11 specific commands...
@REM using official source 
@REM poetry run pip install https://download.pytorch.org/whl/cu121/torch-2.1.0%2Bcu121-cp311-cp311-win_amd64.whl
@REM poetry run pip install https://download.pytorch.org/whl/cu121/torchaudio-2.1.0%2Bcu121-cp311-cp311-win_amd64.whl
@REM poetry run pip install https://download.pytorch.org/whl/cu121/torchvision-0.16.0%2Bcu121-cp311-cp311-win_amd64.whl

@REM using aliyun mirrors
poetry run pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uform
poetry run pip install https://mirrors.aliyun.com/pytorch-wheels/cu121/torch-2.2.0+cu121-cp311-cp311-win_amd64.whl
poetry run pip install https://mirrors.aliyun.com/pytorch-wheels/cu121/torchaudio-2.2.0+cu121-cp311-cp311-win_amd64.whl
poetry run pip install https://mirrors.aliyun.com/pytorch-wheels/cu121/torchvision-0.17.0+cu121-cp311-cp311-win_amd64.whl
goto :finish

:Other
echo Error: python3.10 or 3.11 not detected
goto :finish


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