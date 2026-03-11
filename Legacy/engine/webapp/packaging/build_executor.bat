@echo off
setlocal EnableDelayedExpansion

REM Directory of webapp (parent of packaging)
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set WEBAPP_DIR=%%~fI
pushd "%WEBAPP_DIR%"

set APP_NAME=LojaSyncExecutor

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APP_NAME%.spec del %APP_NAME%.spec

python -m pip install --upgrade pip >nul
if exist requirements.txt (
    python -m pip install -r requirements.txt
)
python -m pip install pyinstaller

pyinstaller executor.py --noconfirm --clean --onefile --noconsole --name %APP_NAME% ^
 --add-data "..\modules;modules" ^
 --add-data "data;data"

popd

echo.
echo Build final available in dist\%APP_NAME%.exe
exit /b 0
