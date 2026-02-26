@echo off
setlocal EnableDelayedExpansion

REM Diretório deste script
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"

REM Nome do executável final
set APP_NAME=LojaSyncLauncher

REM Limpar pastas de build anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Garantir PyInstaller instalado no ambiente atual
python -m pip install --upgrade pip >nul
if exist requirements.txt (
    python -m pip install -r requirements.txt
)
python -m pip install pyinstaller

REM Montar comando do PyInstaller
set ADD_DATA_ARGS=^
 --add-data "index.html;."^
 --add-data "styles.css;."^
 --add-data "script.js;."^
 --add-data "automation_client.js;."^
 --add-data "data;data"^
 --add-data "static;static"^
 --add-data "..\modules;modules"

pyinstaller --noconfirm --clean LojaSyncLauncher.spec

popd

echo.
echo Build final disponível em dist\%APP_NAME%.exe
echo.
exit /b 0
