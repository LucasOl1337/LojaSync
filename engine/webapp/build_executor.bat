@echo off
setlocal EnableDelayedExpansion

REM Diretório deste script (webapp/)
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"

REM Nome do executável final
set APP_NAME=LojaSyncExecutor

REM Limpar builds anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APP_NAME%.spec del %APP_NAME%.spec

REM Garantir PyInstaller instalado e dependências do executor disponíveis
python -m pip install --upgrade pip >nul
if exist requirements.txt (
    python -m pip install -r requirements.txt
)
python -m pip install pyinstaller

REM Arquivos a serem empacotados junto ao executor
set ADD_DATA_ARGS=^
 --add-data "..\modules;modules"^
 --add-data "data;data"

REM Empacotar executor.py em modo onefile
pyinstaller executor.py --noconfirm --clean --onefile --noconsole --name %APP_NAME% %ADD_DATA_ARGS%

popd

echo.
echo Build final disponível em dist\%APP_NAME%.exe
