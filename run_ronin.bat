@echo off
:: ==============================================================================
:: RONIN-V 
:: Vibe Sentinel - Unrestricted AI Terminal Launcher (Node.js Edition)
:: ==============================================================================

:: Force UTF-8 encoding for Windows console to support ASCII art and emojis
chcp 65001 >nul

:: Check if node_modules exists, suggesting npm install has been run
if not exist "node_modules\" (
    echo [ERROR] Dependencies not found.
    echo Please run "npm install" first.
    pause
    exit /b 1
)

:: Compile TypeScript (just in case changes were made)
echo [*] Compiling Ronin-V Engine...
call npx tsc

:: Launch Ronin-V via Node.js
echo [*] Initializing Terminal...
node dist/index.js

:: Keep window open if it crashes
if %errorlevel% neq 0 (
    echo.
    echo [!] Ronin-V has crashed or exited with an error.
    pause
)
