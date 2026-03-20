@echo off
setlocal EnableExtensions

title LojaSync Launcher

if /I "%LOJASYNC_SKIP_ELEVATION%"=="1" goto after_elevation

powershell -NoProfile -Command "if (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { exit 0 } else { exit 1 }" >nul 2>nul
if errorlevel 1 (
  echo Solicitando permissao de administrador...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%ComSpec%' -ArgumentList '/c','\"%~f0\" %*' -Verb RunAs"
  exit /b
)

:after_elevation
pushd "%~dp0" || (
  echo [ERRO] Nao foi possivel acessar a pasta do projeto.
  pause
  exit /b 1
)

set "PYTHON_CMD="
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "RUNNER_CMD="

py -3.11 -V >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.11"

if not defined PYTHON_CMD (
  py -3.12 -V >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)

if not defined PYTHON_CMD (
  python -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  py -3 -V >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  echo [ERRO] Python nao encontrado no PATH.
  echo Instale o Python 3.11+ ou ajuste o PATH do Windows.
  popd
  pause
  exit /b 9009
)

call %PYTHON_CMD% -c "import fastapi, uvicorn" >nul 2>nul
if not errorlevel 1 (
  set "RUNNER_CMD=%PYTHON_CMD%"
)

if exist "%VENV_PY%" (
  call "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>nul
  if errorlevel 1 (
    echo Recriando a .venv com uma versao suportada do Python...
    rmdir /s /q ".venv"
  )
)

if not defined RUNNER_CMD (
  if not exist "%VENV_PY%" (
    echo Preparando ambiente virtual local...
    call %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 (
      echo [ERRO] Nao foi possivel criar a .venv do projeto.
      popd
      pause
      exit /b 1
    )
  )

  call "%VENV_PY%" -c "import pip" >nul 2>nul
  if errorlevel 1 (
    echo Inicializando pip na .venv...
    call "%VENV_PY%" -m ensurepip --upgrade
    if errorlevel 1 (
      echo [ERRO] Falha ao preparar o pip da .venv.
      popd
      pause
      exit /b 1
    )
  )

  call "%VENV_PY%" -c "import fastapi, uvicorn" >nul 2>nul
  if errorlevel 1 (
    echo Instalando dependencias do LojaSync...
    call "%VENV_PY%" -m pip install --upgrade pip
    if errorlevel 1 (
      echo [ERRO] Falha ao atualizar o pip da .venv.
      popd
      pause
      exit /b 1
    )

    call "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
      echo [ERRO] Falha ao instalar as dependencias do projeto.
      popd
      pause
      exit /b 1
    )
  )

  set "RUNNER_CMD=\"%VENV_PY%\""
)

echo Iniciando LojaSync...
echo Pasta: %CD%
echo Comando: %RUNNER_CMD% launcher.py
echo.

call %RUNNER_CMD% launcher.py %*
set "ERR=%ERRORLEVEL%"

popd

if not "%ERR%"=="0" (
  echo.
  echo O launcher terminou com codigo %ERR%.
  echo Pressione qualquer tecla para fechar...
  pause >nul
)

exit /b %ERR%
