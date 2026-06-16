@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment missing. Run setup.bat first.
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Starting SafeCheck field application ...
python run_app.py
if errorlevel 1 (
  echo.
  echo [ERROR] The application exited with an error.
  echo Check the log at data\logs\safecheck.log
  exit /b 1
)
endlocal
