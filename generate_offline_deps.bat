@echo off
title Windrecorder - Generate offline dependency package
mode con cols=150 lines=50

cd /d %~dp0

echo ---------------------------------------------------
echo Add export plugin
echo ---------------------------------------------------
python -m poetry self add poetry-plugin-export

echo ---------------------------------------------------
echo Check if the offsine_deps directory exists
echo ---------------------------------------------------
if not exist offline_deps mkdir offline_deps

echo ---------------------------------------------------
echo Exporting project dependencies to requirements file
echo ---------------------------------------------------
rem Using Poetry to export dependencies and generate requirements. txt
python -m poetry export -f requirements.txt --output offline_deps\requirements.txt --without-hashes
if %ERRORLEVEL% neq 0 (
    echo Export dependency failed, please check if the Poetry configuration or plugin was installed successfully.
    pause
    exit /b 1
)

echo ---------------------------------------------------
echo Downloading project dependencies to the offsine_deps folder
echo ---------------------------------------------------
rem Download all packages in the requirements. txt file to the offsine_deps folder
python -m pip download -d offline_deps -r offline_deps\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ---------------------------------------------------
echo Downloading the installation package for Poetry to the offsine_deps folder
echo ---------------------------------------------------
python -m pip download -d offline_deps poetry -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ---------------------------------------------------
echo Completing the required files for dependency building
echo ---------------------------------------------------
python -m pip download -d offline_deps setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ---------------------------------------------------
echo The offline dependency package has been generated. Please transfer the offsine_deps folder along with the project to a computer without a network environment.
echo 离线依赖包生成完毕，请将 offline_deps 文件夹随项目一并转移至无网络环境的电脑。
pause
