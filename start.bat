@echo off
title Veritime
color 0A

echo.
echo  =========================================
echo   Veritime - Attendance System
echo   St. Catherine's College
echo  =========================================
echo.

REM ── Step 1: Check Python is installed ────────────────────────────────────────
set PYTHON=python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo  ERROR: Python was not found on this computer.
        echo.
        echo  Please install Python 3.9 or later from:
        echo    https://www.python.org/downloads/
        echo.
        echo  When installing, make sure to tick:
        echo    "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
    set PYTHON=py
)

REM ── Step 2: Create virtual environment if needed ─────────────────────────────
if not exist "venv\" (
    echo  First-time setup: creating isolated Python environment...
    %PYTHON% -m venv venv
    if errorlevel 1 (
        echo.
        echo  ERROR: Could not create the Python environment.
        echo  Try reinstalling Python and make sure "Add to PATH" was ticked.
        echo.
        pause
        exit /b 1
    )
    echo  Done.
    echo.
)

REM ── Step 3: Activate the virtual environment ─────────────────────────────────
call venv\Scripts\activate.bat

REM ── Step 4: Install / update packages ────────────────────────────────────────
echo  Checking required packages...
pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo  ERROR: Could not install required packages.
    echo  Make sure this computer is connected to the internet for first-time setup.
    echo.
    pause
    exit /b 1
)
echo  Packages ready.
echo.

REM ── Step 5: Detect Arduino COM port (optional — server starts either way) ────
echo  Detecting Arduino...
%PYTHON% configure_port.py
if errorlevel 1 (
    echo.
    echo  Arduino not detected. Veritime will start anyway.
    echo  Plug in the Arduino and it will be detected automatically.
    echo.
) else (
    echo.
)

REM ── Step 5b: Background Arduino detection loop ────────────────────────────
echo  Starting Arduino auto-detect in the background...
start /b "Arduino Poller" %PYTHON% configure_port.py --poll
echo.

REM ── Step 6: Open browser after a short delay ─────────────────────────────────
echo  Opening browser in 4 seconds...
start /b cmd /c "timeout /t 4 >nul && start http://localhost:5000/landing"

REM ── Step 7: Start the server ──────────────────────────────────────────────────
echo  Veritime is running. Close this window to stop.
echo  =========================================
echo.
%PYTHON% app.py

REM ── On exit ───────────────────────────────────────────────────────────────────
echo.
echo  Veritime stopped.
pause
