@echo off
rem ---------------------------------------------------------------------------
rem  Start ARTEMIS
rem
rem  Double-click this file to open ARTEMIS. Nothing needs to be typed and no
rem  settings need to be changed first.
rem
rem  It runs from wherever this file sits, finds Python on its own, and opens
rem  the interface in the default browser. If something is missing it says so
rem  in plain words rather than flashing a black box and vanishing.
rem ---------------------------------------------------------------------------

title ARTEMIS

rem Work from the folder holding this file, so the app can be moved anywhere.
cd /d "%~dp0"

rem Let Python import ARTEMIS from src\ without the project being installed.
set "PYTHONPATH=%~dp0src"

rem Find a Python. The launcher (py.exe) ships with most Windows installs.
rem The web interface needs a console to stay alive, so the windowless
rem variants (pyw, pythonw) are deliberately not used here.
set "RUNNER="
where py >nul 2>&1 && set "RUNNER=py"
if not defined RUNNER where python >nul 2>&1 && set "RUNNER=python"

if not defined RUNNER (
    echo.
    echo   ARTEMIS could not start because Python is not installed.
    echo.
    echo   Install Python 3.11 or newer from https://www.python.org/downloads/
    echo   During setup, tick "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

rem Check dependencies before starting, so a missing package produces an
rem explanation instead of a stack trace.
%RUNNER% -c "import gradio, watchdog" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Setting up ARTEMIS for first use.
    echo   This happens once and takes a few minutes.
    echo.
    %RUNNER% -m pip install --quiet gradio watchdog typer rich
    if errorlevel 1 (
        echo.
        echo   Setup did not finish. Check the internet connection and try again.
        echo.
        pause
        exit /b 1
    )
)

cls
echo.
echo    A R T E M I S
echo    ---------------------------------------------------------
echo.
echo    Starting up. A browser tab will open in a moment.
echo.
echo    Everything ARTEMIS knows stays on this computer.
echo    Keep this window open while you use it.
echo    Close it, or press Ctrl+C, to stop ARTEMIS.
echo.

%RUNNER% -m artemis.ui.web

rem Only reached if the server stops or fails to start.
echo.
echo    ARTEMIS has stopped.
echo.
pause
