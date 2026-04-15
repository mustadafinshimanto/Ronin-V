#!/bin/bash
DESKTOP_FILE="$HOME/Desktop/Ronin-V.desktop"
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=Ronin-V
Comment=Vibe Sentinel AI Terminal
Exec=/usr/bin/qterminal -e "$(pwd)/run_ronin.sh"
Icon=utilities-terminal
Path=$(pwd)
Terminal=false
Categories=System;Security;
EOF
chmod +x "$DESKTOP_FILE"
echo "[*] Ronin-V Tactical Shortcut created on Kali Desktop."
