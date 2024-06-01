@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call "%%A\Scripts\activate.bat"
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