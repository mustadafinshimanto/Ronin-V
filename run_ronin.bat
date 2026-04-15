@echo off
:: ==============================================================================
:: RONIN-V 
:: Vibe Sentinel - Unrestricted AI Terminal Launcher
:: ==============================================================================

:: Force UTF-8 encoding for Windows console to support ASCII art and emojis
chcp 65001 >nul
set PYTHONUTF8=1

:: Check if the virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. 
    echo Please run the installation steps defined in README.md first.
    pause
    exit /b 1
)

:: Activate the virtual environment
call ".venv\Scripts\activate.bat"

:: Launch Ronin-V
python ronin.py

:: Keep window open if it crashes
if %errorlevel% neq 0 (
    echo.
    echo [!] Ronin-V has crashed or exited with an error. 
    pause
)
