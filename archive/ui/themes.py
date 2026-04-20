"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — UI Themes                         ║
║       Cyberpunk color scheme and ASCII art               ║
╚══════════════════════════════════════════════════════════╝
"""
from rich.theme import Theme

# Cyberpunk-inspired color palette
CYBERPUNK_THEME = Theme({
    "info": "bold #ff4a4a",
    "warning": "bold yellow",
    "error": "bold white on red",
    "success": "bold #00ff9f",
    "ronin.name": "bold #ff003c",     # Neon blood red
    "ronin.prompt": "bold #ff2a2a",   # Bright red
    "user.prompt": "bold #ffffff",    # Pure white
    "system.status": "dim #aa0022",   # Dark red
    "header": "bold #ff003c",
    "panel.border": "#ff003c",
    "markdown.code": "bold #ff4a4a on #1a0505",
    "markdown.code_block": "bold #ff4a4a on #1a0505",
})

BANNER = r"""
[bold #ff003c]
██████╗  ██████╗ ███╗   ██╗██╗███╗   ██╗     ██╗   ██╗
██╔══██╗██╔═══██╗████╗  ██║██║████╗  ██║     ██║   ██║
██████╔╝██║   ██║██╔██╗ ██║██║██╔██╗ ██║     ██║   ██║
██╔══██╗██║   ██║██║╚██╗██║██║██║╚██╗██║  _  ╚██╗ ██╔╝
██║  ██║╚██████╔╝██║ ╚████║██║██║ ╚████║ ( )  ╚████╔╝ 
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝  V    ╚═══╝  

    [bold white]>> VIBE SENTINEL v0.1.0 • UNRESTRICTED MODE <<[/bold white]
    [italic #ff4a4a]Built for Penetration Testing & Ethical Hacking[/italic #ff4a4a]
[/bold #ff003c]
"""

MINI_BANNER = r"""
[bold #ff003c]
───[ RONIN-V ]───[ \ / ]───[ ELITE ]───
[/bold #ff003c]
"""
