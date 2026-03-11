@echo off
setlocal EnableDelayedExpansion

REM Directory of webapp (parent of packaging)
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set WEBAPP_DIR=%%~fI
pushd "%WEBAPP_DIR%"

set APP_NAME=LojaSyncLauncher

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m pip install --upgrade pip >nul
if exist requirements.txt (
    python -m pip install -r requirements.txt
)
python -m pip install pyinstaller

pyinstaller launcher.py --noconfirm --clean --name %APP_NAME% --onefile --windowed ^
 --add-data "index.html;." ^
 --add-data "styles.css;." ^
 --add-data "script.js;." ^
 --add-data "automation_client.js;." ^
 --add-data "theme.css;." ^
 --add-data "theme.js;." ^
 --add-data "themes-complete.css;." ^
 --add-data "layout-improvements.css;." ^
 --add-data "data;data" ^
 --add-data "static;static" ^
 --add-data "..\modules;modules" ^
 --add-data "..\LLM3;LLM3"

popd

echo.
echo Build final available in dist\%APP_NAME%.exe
echo.
exit /b 0
