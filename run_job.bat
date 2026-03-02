@echo off
:: Ensure we are in the correct directory
cd /d "%~dp0"

SET "PYTHON_EXE=c:\Users\RAPH-EXT\maker\venv\Scripts\python.exe"
SET "SCRIPT_PATH=c:\Users\RAPH-EXT\maker\maker_studio.py"

:: Check if script exists
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] Could not find %SCRIPT_PATH%
    pause
    exit /b 1
)

if "%~1"=="" (
    echo Usage: run_job.bat "Your Topic" [Category]
    echo Example: run_job.bat "The Nigerian Civil War" "History"
    pause
    exit /b 1
)

SET "TOPIC=%~1"
SET "CATEGORY=%~2"
if "%CATEGORY%"=="" SET "CATEGORY=History"

echo.
echo ============================================================
echo   MAKER STUDIO: Starting Job
echo ============================================================
echo Topic:    %TOPIC%
echo Category: %CATEGORY%
echo.

"%PYTHON_EXE%" "%SCRIPT_PATH%" --topic "%TOPIC%" --category "%CATEGORY%" --produce

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] The job failed. Check logs/maker.log for details.
) else (
    echo.
    echo [SUCCESS] Job completed!
)

echo ============================================================
pause
