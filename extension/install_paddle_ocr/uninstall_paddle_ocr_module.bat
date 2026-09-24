@echo off
echo Loading extension, please stand by.
echo.

cd /d "%~dp0"
call "%~dp0..\..\scripts\activate_runtime.bat"
if errorlevel 1 (
    pause
    exit /b 1
)
chcp 65001

:start_install
cls
echo.
echo   Make sure to exit windrecorder before uninstallation.
echo   卸载前请确保退出了 捕风记录仪。
echo.
echo   Enter Y and press Enter to uninstall RapidOCR (Paddle OCR based on ONNXRuntime) module.
echo   输入 Y 后回车卸载 RapidOCR（Paddle OCR 的 ONNXRuntime 版本）。
echo.
echo   ================================================================================
echo.
set /p choice=   Please enter the options and press Enter:

if /I "%choice%"=="Y" (
    echo Uninstalling...
    goto uninstall_module
)

goto start_install


@REM -------------------------------------------------
:uninstall_module
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\..\scripts\setup.ps1" -RemoveExtra rapidocr
if errorlevel 1 (
    pause
    exit /b 1
)
call "%~dp0..\..\scripts\activate_runtime.bat"
if errorlevel 1 exit /b 1
goto :finish


@REM -------------------------------------------------
:finish
python _uninstall.py
echo.
echo   The uninstallation script has been completed. 已执行完卸载脚本。
echo.
pause
exit
