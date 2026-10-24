@echo off
"%~dp0backend\flask\.venv\Scripts\python.exe" "%~dp0manage.py" stop
set "app_exit_code=%errorlevel%"
if not "%app_exit_code%"=="0" pause
exit /b %app_exit_code%
