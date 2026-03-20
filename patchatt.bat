@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo LojaSync PatchAtt
echo ========================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo Git nao encontrado no computador.
  echo Instale o Git e tente novamente.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo Esta pasta nao e um repositorio Git valido.
  pause
  exit /b 1
)

for /f "delims=" %%i in ('git status --porcelain') do set HAS_CHANGES=1
if defined HAS_CHANGES (
  echo Existem alteracoes locais neste PC.
  echo Commit/stash essas alteracoes antes de rodar o patchatt.
  pause
  exit /b 1
)

git checkout main
if errorlevel 1 (
  echo Falha ao trocar para a branch main.
  pause
  exit /b 1
)

git fetch origin
if errorlevel 1 (
  echo Falha ao buscar atualizacoes do GitHub.
  pause
  exit /b 1
)

git pull --ff-only origin main
if errorlevel 1 (
  echo Falha ao atualizar o LojaSync.
  pause
  exit /b 1
)

echo.
echo LojaSync atualizado com sucesso.
pause
exit /b 0
