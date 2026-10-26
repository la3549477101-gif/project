@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
"%~dp0backend\flask\.venv\Scripts\python.exe" "%~dp0manage.py" stop
set "app_exit_code=%errorlevel%"
if not "%app_exit_code%"=="0" pause
exit /b %app_exit_code%
