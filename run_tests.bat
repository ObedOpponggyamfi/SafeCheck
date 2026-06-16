@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment missing. Run setup.bat first.
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Running SafeCheck test suite ...
echo.
set FAILED=0
for %%T in (
  test_inspection_logic
  test_submit_flow
  test_machinery
  test_server
  test_findings
  test_dashboard
  test_reports
) do (
  echo --- %%T ---
  python "tests\%%T.py" || set FAILED=1
  echo.
)
echo --- ui_smoke ---
python "tests\ui_smoke.py" || set FAILED=1

echo.
if "%FAILED%"=="1" ( echo [RESULT] One or more test files reported failures. & exit /b 1 )
echo [RESULT] All test files passed.
endlocal
