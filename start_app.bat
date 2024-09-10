@echo off
title Windrecorder
mode con cols=70 lines=10
color 75
echo.
echo   Initializing Windrecorder, please stand by...
echo.
echo   Please stay in this window until it disappears
echo.


@REM hide CLI, if need debugging, please comment it out.(to :begin)
if "%1"=="h" goto begin
start mshta vbscript:createobject("wscript.shell").run("%~nx0"^&" h",0)^&(window.close) && exit
::start mshta "javascript:new ActiveXObject('WScript.Shell').Run('%~nx0 h',0);window.close();" && exit
:begin

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call "%%A\Scripts\activate.bat"

python "%~dp0\main.py"