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

:start_rollback
python _rollback_old_imgemb_db.py

@REM -------------------------------------------------
:finish
echo.
echo   The rollback script has been completed. 已执行完回滚脚本。
echo.
pause
exit
