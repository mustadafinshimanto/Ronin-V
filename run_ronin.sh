#!/bin/bash
# ==============================================================================
# RONIN-V
# Vibe Sentinel - Unrestricted AI Terminal Launcher (Node.js Edition)
# ==============================================================================

# Check if node_modules exists, suggesting npm install has been run
if [ ! -d "node_modules" ]; then
    echo "[ERROR] Dependencies not found."
    echo "Please run 'npm install' first."
    exit 1
fi

echo "[*] Compiling Ronin-V Engine..."
npx tsc

echo "[*] Initializing Terminal..."
node dist/index.js

# Keep terminal output visible if it crashes
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo ""
    echo "[!] Ronin-V has crashed or exited with an error."
    read -p "Press Enter to exit..."
fi
