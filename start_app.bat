@echo off
chcp 65001 >nul
echo.
echo   正在加载 Windrecorder，请稍候……
echo   Loading Windrecorder. Please wait...
title Windrecorder
echo.
echo   托盘就绪后此窗口将自动关闭，请勿提前关闭。
echo   This window will close when the tray is ready. Please keep it open.
echo.

cd /d "%~dp0"
call "%~dp0scripts\activate_runtime.bat"
if errorlevel 1 (
    pause
    exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -u "%~dp0scripts\launch_app.py"
if errorlevel 1 (
    echo.
    echo Windrecorder could not start. Check cache\logs\startup.log for details.
    pause
    exit /b 1
)
exit /b 0
