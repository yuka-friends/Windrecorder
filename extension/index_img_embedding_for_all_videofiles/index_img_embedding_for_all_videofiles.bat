@echo off
echo Loading extension, please stand by.
echo.

cd /d %~dp0
for /F "tokens=* USEBACKQ" %%A in (`python -m poetry env info --path`) do call %%A\Scripts\activate.bat
chcp 65001
cls

python "%~dp0\index_img_embedding_for_all_videofiles.py"
pause