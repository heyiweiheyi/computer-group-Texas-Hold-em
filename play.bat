@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist "%~dp0texas_holdem_gui.py" (
    echo [Error] texas_holdem_gui.py was not found in this folder.
    echo Please download the full repository ZIP ^(Code -^> Download ZIP^),
    echo right-click the ZIP and choose "Extract All", then run play.bat inside the extracted folder.
    pause
    exit /b 1
)

set "PY_CMD="

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :found_python
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :found_python
)

python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python3"
    goto :found_python
)

echo [Error] Python 3.8+ was not found on this computer.
echo Please install Python 3 from https://www.python.org/downloads/ ^(check "Add python.exe to PATH"^) and try again.
pause
exit /b 1

:found_python
echo Using Python: %PY_CMD%

%PY_CMD% -c "import pygame" >nul 2>&1
if not errorlevel 1 goto :launch_game

echo pygame is not installed. Installing from requirements.txt...
%PY_CMD% -m pip install -r "%~dp0requirements.txt"
if not errorlevel 1 goto :verify_pygame

echo Default PyPI failed. Retrying with Tsinghua mirror...
%PY_CMD% -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [Error] Failed to install dependencies. Please check your internet connection or Python pip setup.
    pause
    exit /b 1
)

:verify_pygame
%PY_CMD% -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo [Error] Dependencies installed, but importing pygame still failed.
    pause
    exit /b 1
)

:launch_game
echo Launching Texas Hold'em GUI...
%PY_CMD% "%~dp0texas_holdem_gui.py"
if errorlevel 1 (
    echo.
    echo [Error] The game exited unexpectedly. See the error message above.
    pause
    exit /b 1
)
