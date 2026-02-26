@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Elevar para administrador (UAC) se ainda não estiver elevado
net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','\"%~fnx0\" %*' -Verb RunAs"
  exit /b
)

rem Ir para a pasta deste script (webapp)
pushd "%~dp0"

rem Ajustes de performance para romaneios grandes (edite conforme necessário)
set "LLM_DOC_CHUNK_CHARS=16000"
set "LLM_INCLUDE_IMAGES_WITH_TEXT=0"
set "PDF_RENDER_MAX_PAGES=12"
set "PDF_RENDER_ZOOM=1.5"
set "LLM_ROMANEIO_RETRY_VISION_MAX_PAGES=4"
set "LLM_ROMANEIO_RETRY_VISION_ZOOM=1.5"

rem Preferir o launcher do Python (py), senão usar python padrão
where py >nul 2>nul
if %errorlevel%==0 (
  echo Iniciando LojaSync com: py -3 launcher.py
  py -3 launcher.py %*
  set ERR=%ERRORLEVEL%
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    echo Iniciando LojaSync com: python launcher.py
    python launcher.py %*
    set ERR=%ERRORLEVEL%
  ) else (
    echo [ERRO] Python não encontrado no PATH. Instale o Python 3.x ou adicione ao PATH.
    set ERR=9009
  )
)

popd

if not "%ERR%"=="0" (
  echo.
  echo O launcher terminou com código %ERR%.
  echo Pressione qualquer tecla para fechar...
  pause >nul
)

exit /b %ERR%
