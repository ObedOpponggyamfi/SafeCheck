@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   SafeCheck - Environment Setup
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH. Install Python 3.10+ and retry.
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo [1/3] Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 ( echo [ERROR] Could not create virtual environment. & exit /b 1 )
) else (
  echo [1/3] Virtual environment already present.
)

echo [2/3] Activating virtual environment ...
call ".venv\Scripts\activate.bat" || ( echo [ERROR] Could not activate venv. & exit /b 1 )

echo [3/3] Installing dependencies ...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Dependency installation failed. & exit /b 1 )

if not exist ".env" (
  if exist ".env.example" ( copy ".env.example" ".env" >nul & echo Created .env from .env.example )
)

echo.
echo Setup complete.
echo   - Start the app:    run_app.bat
echo   - Start the server: run_server.bat
echo   - Run the tests:    run_tests.bat
endlocal
