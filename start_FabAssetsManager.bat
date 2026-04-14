@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using local virtual environment: .venv\Scripts\python.exe
    ".venv\Scripts\python.exe" app.py
    goto :after_run
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Using Python from PATH
    python app.py
    goto :after_run
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Using Python launcher (py -3)
    py -3 app.py
    goto :after_run
)

echo [ERROR] Python not found.
echo Install Python 3 or create a .venv environment in this folder.
pause
exit /b 1

:after_run
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [WARN] App exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
