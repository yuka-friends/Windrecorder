@echo off
color 0B
title Windrecorder - Recording Screening
echo Starting Recording Screen...
cd /d %~dp0
python "%~dp0\recordScreen.py"
ping 127.0.0.1 -n 1 >nul