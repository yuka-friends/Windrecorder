@echo off
setlocal
title Windrecorder - install or update
chcp 65001 >nul
echo.
echo   Windrecorder - Install / Update
echo   正在启动安装与升级，请保持此窗口打开。
echo   Starting setup. Please keep this window open.
echo.
echo   首次安装或升级可能需要几分钟，连接网络或安装依赖时可能暂时没有新输出。
echo   Downloads and dependency installation may take several minutes.
echo.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update.ps1"
set "update_status=%errorlevel%"
if not "%update_status%"=="0" echo Update failed. Please read the error above and retry.
pause
exit /b %update_status%
