@echo off
setlocal EnableExtensions EnableDelayedExpansion
title LojaSync - Modo Online (Cloudflare Tunnel)

echo.
echo ============================================================
echo   LojaSync - Iniciando com acesso remoto via Cloudflare
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "CLOUDFLARED=cloudflared"

REM ── Verifica cloudflared ──────────────────────────────────────
where cloudflared >nul 2>nul
if errorlevel 1 (
    set "CLOUDFLARED=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
    if not exist "!CLOUDFLARED!" (
        echo [ERRO] cloudflared nao encontrado. Instale via:
        echo   winget install Cloudflare.cloudflared
        pause & exit /b 1
    )
)

REM ── Inicia o LojaSync em background ──────────────────────────
echo [1/2] Iniciando LojaSync (backend na porta 8800)...
if exist "%VENV_PY%" (
    start "LojaSync Backend" /min "%VENV_PY%" "%SCRIPT_DIR%launcher.py" --no-browser
) else (
    start "LojaSync Backend" /min python "%SCRIPT_DIR%launcher.py" --no-browser
)

REM ── Aguarda o backend subir ───────────────────────────────────
echo     Aguardando backend iniciar...
:wait_loop
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient('127.0.0.1', 8800); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 goto wait_loop
echo     Backend OK!

REM ── Inicia o tunel Cloudflare ─────────────────────────────────
echo.
echo [2/2] Criando tunel Cloudflare...
echo.
echo ============================================================
echo   Aguarde a URL publica aparecer abaixo...
echo   Compartilhe essa URL com seu cliente para acesso remoto.
echo   Feche esta janela para encerrar o tunel.
echo ============================================================
echo.

"%CLOUDFLARED%" tunnel --url http://localhost:8800

echo.
echo Tunel encerrado.
pause
