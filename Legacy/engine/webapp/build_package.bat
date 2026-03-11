@echo off
setlocal
set SCRIPT_DIR=%~dp0
call "%SCRIPT_DIR%packaging\build_package.bat" %*
exit /b %ERRORLEVEL%
