@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment missing. Run setup.bat first.
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Starting SafeCheck sync server on http://127.0.0.1:8077 ...
echo (API docs: http://127.0.0.1:8077/docs)
python run_server.py
if errorlevel 1 (
  echo.
  echo [ERROR] The server exited with an error.
  echo Check the log at data\logs\safecheck.log
  exit /b 1
)
endlocal
