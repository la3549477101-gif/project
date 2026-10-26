@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
"%~dp0backend\flask\.venv\Scripts\python.exe" "%~dp0manage.py" status
set "app_exit_code=%errorlevel%"
pause
exit /b %app_exit_code%
