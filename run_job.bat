@echo off
:: ============================================================
::  MAKER STUDIO — AI video generator
:: ============================================================
cd /d "%~dp0"

SET "PYTHON_EXE=c:\Users\RAPH-EXT\maker\venv\Scripts\python.exe"
SET "SCRIPT_PATH=c:\Users\RAPH-EXT\maker\maker_studio.py"
SET "PICK_VOICE=c:\Users\RAPH-EXT\maker\pick_voice.py"
SET "VOICE_TMP=%TEMP%\maker_voice_pick.txt"

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
echo   MAEKER STUDIO  ^| COR
echo  ============================================================
echo.

:: ── Step 1 : Topic ──────────────────────────────────────────
:ASK_TOPIC
echo  insert Topic
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

if "%CAT_INPUT%"==""  SET "CATEGORY=History"   & goto CAT_DONE
if "%CAT_INPUT%"=="1" SET "CATEGORY=History"   & goto CAT_DONE
if "%CAT_INPUT%"=="2" SET "CATEGORY=Politics"  & goto CAT_DONE
if "%CAT_INPUT%"=="3" SET "CATEGORY=Culture"   & goto CAT_DONE
if "%CAT_INPUT%"=="4" SET "CATEGORY=Crime"     & goto CAT_DONE
if "%CAT_INPUT%"=="5" SET "CATEGORY=Society"   & goto CAT_DONE
if "%CAT_INPUT%"=="6" SET "CATEGORY=Science"   & goto CAT_DONE
if "%CAT_INPUT%"=="7" SET "CATEGORY=Technology" & goto CAT_DONE
if "%CAT_INPUT%"=="8" SET "CATEGORY=Business"  & goto CAT_DONE
if "%CAT_INPUT%"=="9" SET "CATEGORY=Biography" & goto CAT_DONE
if "%CAT_INPUT%"=="10" (
    echo.
    set /p "CATEGORY=  >> Enter your own category: "
    if "%CATEGORY%"=="" SET "CATEGORY=History"
    goto CAT_DONE
)
:: User typed a raw category name
SET "CATEGORY=%CAT_INPUT%"
:CAT_DONE

:: ── Step 3 : Voice selection ────────────────────────────────
echo.
echo  ------------------------------------------------------------

:: Delete any stale temp file
if exist "%VOICE_TMP%" del "%VOICE_TMP%"

:: Run pick_voice.py — it handles all user interaction and writes the result
"%PYTHON_EXE%" "%PICK_VOICE%" --out "%VOICE_TMP%"

:: Read chosen voice from temp file
SET "CHOSEN_VOICE=George"
if exist "%VOICE_TMP%" (
    set /p CHOSEN_VOICE=<"%VOICE_TMP%"
    del "%VOICE_TMP%"
)
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
    echo  Starting over — let's pick a new topic.
    echo.
    goto ASK_TOPIC
)

echo.
echo  [MAKER STUDIO] Starting production - this may take several minutes.
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
