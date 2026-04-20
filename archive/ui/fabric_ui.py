"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Fabric UI Bridge                  ║
║        Extracted from Microsoft Fabric CLI Pattern        ║
╚══════════════════════════════════════════════════════════╝
"""
import sys
import html
from typing import Any, Optional
from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.styles import Style
from rich.console import Console

# Optimized Style map from Microsoft Fabric CLI
FABRIC_STYLE = Style([
    ("prompt", "fg:#49C5B1 bold"),  # The 'fab' / 'ronin' part
    ("context", "fg:#017864"),       # The path / context
    ("detail", "fg:grey"),           # The separators : and $
    ("input", "fg:white"),           # User input
])

# Iconography from Fabric CLI
SUCCESS_ICON = "<ansigreen>*</ansigreen>"
INFO_ICON = "<ansiblue>*</ansiblue>"
WARN_ICON = "<ansiyellow>!</ansiyellow>"
ERR_ICON = "<ansired>x</ansired>"

def print_done(text: str):
    escaped = html.escape(text)
    print_formatted_text(HTML(f"{SUCCESS_ICON} {escaped}"))

def print_info(text: str, command: Optional[str] = None):
    escaped = html.escape(text)
    cmd_text = f"{command}: " if command else ""
    print_formatted_text(HTML(f"{INFO_ICON} {cmd_text}{escaped}"))

def print_warning(text: str):
    escaped = html.escape(text)
    print_formatted_text(HTML(f"{WARN_ICON} {escaped}"))

def print_error(text: str):
    escaped = html.escape(text)
    print_formatted_text(HTML(f"{ERR_ICON} {escaped}"))

def get_prompt_text(context: str = "sentinel"):
    """Fabric-style HTML prompt."""
    ctx = f"/{context.strip('/')}"
    return HTML(
        f"<prompt>ronin</prompt><detail>:</detail><context>{html.escape(ctx)}</context><detail>$</detail> "
    )
