@echo off
setlocal
cd /d "%~dp0"

set "PY_CMD="
set "PYW_CMD="

py -3 -c "import sys" >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
    where pyw >nul 2>&1 && set "PYW_CMD=pyw -3"
) else (
    python -c "import sys" >nul 2>&1
    if %errorlevel%==0 (
        set "PY_CMD=python"
        where pythonw >nul 2>&1 && set "PYW_CMD=pythonw"
    )
)

if "%PY_CMD%"=="" (
    echo [Error] Python 3 not found. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

%PY_CMD% -c "import pygame" >nul 2>&1
if not %errorlevel%==0 (
    echo Installing required packages from requirements.txt...
    %PY_CMD% -m pip install -r requirements.txt
    if not %errorlevel%==0 (
        echo [Error] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Launching Texas Hold'em GUI...
if not "%PYW_CMD%"=="" (
    start "" %PYW_CMD% "%~dp0texas_holdem_gui.py"
) else (
    %PY_CMD% "%~dp0texas_holdem_gui.py"
    if not %errorlevel%==0 pause
)
