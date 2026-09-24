@echo off
setlocal
title Windrecorder - install or update
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update.ps1"
if errorlevel 1 echo Update failed. Please read the error above and retry.
pause
