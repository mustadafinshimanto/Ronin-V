#!/bin/bash
# ==============================================================================
# RONIN-V
# Vibe Sentinel - Unrestricted AI Terminal Launcher
# ==============================================================================

# Force UTF-8 encoding for Python to support ASCII art and emojis
export PYTHONUTF8=1

# Check if the virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "Please run the installation steps defined in README.md first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate the virtual environment
source .venv/bin/activate

# Launch Ronin-V
python ronin.py

# Keep terminal output visible if it crashes
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo ""
    echo "[!] Ronin-V has crashed or exited with an error."
    read -p "Press Enter to exit..."
fi
