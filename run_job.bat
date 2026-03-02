@echo off
:: ============================================================
::  MAKER STUDIO — Interactive Job Launcher
::  Double-click this file to start a new production session.
:: ============================================================
cd /d "%~dp0"

SET "PYTHON_EXE=c:\Users\RAPH-EXT\maker\venv\Scripts\python.exe"
SET "SCRIPT_PATH=c:\Users\RAPH-EXT\maker\maker_studio.py"
SET "PICK_VOICE=c:\Users\RAPH-EXT\maker\pick_voice.py"

:: ── Sanity check ────────────────────────────────────────────
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python venv not found at %PYTHON_EXE%
    pause & exit /b 1
)
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] maker_studio.py not found at %SCRIPT_PATH%
    pause & exit /b 1
)

cls
echo.
echo  ============================================================
echo   MAKER STUDIO  ^|  Interactive Production Launcher
echo  ============================================================
echo.

:: ── Step 1 : Topic ──────────────────────────────────────────
:ASK_TOPIC
echo  What topic would you like to produce a video on?
echo.
set /p "TOPIC=  >> Topic: "
if "%TOPIC%"=="" (
    echo  [!] Topic cannot be empty. Please try again.
    echo.
    goto ASK_TOPIC
)

:: ── Step 2 : Category ───────────────────────────────────────
echo.
echo  ------------------------------------------------------------
echo  Choose a category  (press ENTER to use "History")
echo.
echo     1. History          6. Science
echo     2. Politics         7. Technology
echo     3. Culture          8. Business
echo     4. Crime            9. Biography
echo     5. Society         10. Other (type your own)
echo.
set /p "CAT_INPUT=  >> Category (number or name): "
if "%CAT_INPUT%"=="" SET "CATEGORY=History"
if "%CAT_INPUT%"=="1"  SET "CATEGORY=History"
if "%CAT_INPUT%"=="2"  SET "CATEGORY=Politics"
if "%CAT_INPUT%"=="3"  SET "CATEGORY=Culture"
if "%CAT_INPUT%"=="4"  SET "CATEGORY=Crime"
if "%CAT_INPUT%"=="5"  SET "CATEGORY=Society"
if "%CAT_INPUT%"=="6"  SET "CATEGORY=Science"
if "%CAT_INPUT%"=="7"  SET "CATEGORY=Technology"
if "%CAT_INPUT%"=="8"  SET "CATEGORY=Business"
if "%CAT_INPUT%"=="9"  SET "CATEGORY=Biography"
:: If user typed a name (not a number 1-9 or empty), use it verbatim
if "%CAT_INPUT%"=="10" (
    echo.
    set /p "CATEGORY=  >> Enter your own category: "
)
:: Catch raw text entries  (not one of the shortcuts above)
for %%N in (1 2 3 4 5 6 7 8 9 10) do if "%CAT_INPUT%"=="%%N" goto CAT_DONE
if not "%CAT_INPUT%"=="" if not defined CATEGORY SET "CATEGORY=%CAT_INPUT%"
:CAT_DONE
if "%CATEGORY%"=="" SET "CATEGORY=History"

:: ── Step 3 : Voice selection ────────────────────────────────
echo.
echo  ------------------------------------------------------------
echo  Now finding the best bold male narrative voices...
echo.

:: Run pick_voice.py and capture the CHOSEN_VOICE=... line
SET "CHOSEN_VOICE="
FOR /F "tokens=1,* delims==" %%A IN ('"%PYTHON_EXE%" "%PICK_VOICE%" 2^>^&1') DO (
    IF "%%A"=="CHOSEN_VOICE" SET "CHOSEN_VOICE=%%B"
    :: also echo every line that is NOT the CHOSEN_VOICE token
    IF NOT "%%A"=="CHOSEN_VOICE" echo %%A=%%B
)
:: Some lines have no = sign — echo them too
FOR /F "eol=C delims=" %%L IN ('"%PYTHON_EXE%" "%PICK_VOICE%" 2^>^&1 ^| findstr /v "CHOSEN_VOICE="') DO (
    echo %%L
)

:: Fallback if something went wrong
if "%CHOSEN_VOICE%"=="" SET "CHOSEN_VOICE=George"

:: ── Step 4 : Confirm & start ────────────────────────────────
echo.
echo  ============================================================
echo   PRODUCTION SUMMARY
echo  ============================================================
echo   Topic   : %TOPIC%
echo   Category: %CATEGORY%
echo   Voice   : %CHOSEN_VOICE%
echo  ============================================================
echo.
set /p "CONFIRM=  Start production? [Y/N]: "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo  Production cancelled.
    pause & exit /b 0
)

echo.
echo  [MAKER STUDIO] Starting production — this may take several minutes.
echo  ============================================================
echo.

"%PYTHON_EXE%" "%SCRIPT_PATH%" --topic "%TOPIC%" --category "%CATEGORY%" --voice "%CHOSEN_VOICE%" --produce

echo.
if %ERRORLEVEL% NEQ 0 (
    echo  [CRITICAL ERROR] The job failed. Check logs\maker.log for details.
) else (
    echo  [SUCCESS] Job completed! Check the jobs\ folder for your output.
)

echo  ============================================================
pause
