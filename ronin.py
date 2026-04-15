"""
╔══════════════════════════════════════════════════════════╗
║                      RONIN-V                             ║
║          Vibe Sentinel — Windows-Native AI Terminal       ║
║                                                          ║
║  Usage:                                                  ║
║    python ronin.py              Launch interactive TUI    ║
║    python ronin.py --ask "..."  One-shot question         ║
║    python ronin.py --status     System status check       ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import yaml
import click

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# Create data directories
os.makedirs("data/chroma_db", exist_ok=True)
os.makedirs("data/sessions", exist_ok=True)


def load_config() -> dict:
    """Load and return the config.yaml file."""
    config_path = os.path.join(PROJECT_ROOT, "config.yaml")
    if not os.path.exists(config_path):
        click.echo("ERROR: config.yaml not found in project root.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    RONIN-V — Vibe Sentinel AI Terminal.
    
    Launch without arguments for interactive mode.
    """
    if ctx.invoked_subcommand is None:
        # Default: launch interactive TUI
        launch_interactive()


@cli.command()
@click.argument("question", nargs=-1, required=True)
def ask(question):
    """Ask Ronin-V a one-shot question (no interactive mode)."""
    from rich.console import Console
    from rich.markdown import Markdown
    from ui.themes import CYBERPUNK_THEME
    from core.agent import RoninAgent

    console = Console(theme=CYBERPUNK_THEME)
    config = load_config()
    agent = RoninAgent(config)

    query = " ".join(question)
    console.print(f"\n[ronin.prompt]λ ronin >[/ronin.prompt] {query}\n")

    # Stream the response
    console.print("[ronin.name]Ronin-V:[/ronin.name]", end=" ")
    full = ""
    for chunk in agent.chat(query):
        full += chunk
        sys.stdout.write(chunk)
        sys.stdout.flush()

    console.print()
    agent.shutdown()


@cli.command()
def status():
    """Check system status (Ollama, model, executors)."""
    from rich.console import Console
    from ui.themes import CYBERPUNK_THEME, BANNER
    from core.agent import RoninAgent

    console = Console(theme=CYBERPUNK_THEME)
    config = load_config()

    console.print(BANNER)

    agent = RoninAgent(config)
    with console.status("[bold cyan]Running diagnostics...", spinner="bouncingBar"):
        result = agent.check_systems()

    labels = {
        "ollama_connected": "Ollama Server",
        "model_available": "Dolphin Model",
        "powershell_ok": "PowerShell API",
        "python_ok": "Python Executor",
        "memory_ok": "Memory Engine",
    }
    for key, label in labels.items():
        icon = "[success]✓ ONLINE[/success]" if result.get(key) else "[error]✗ OFFLINE[/error]"
        console.print(f"  {label:.<25} {icon}")

    console.print()
    agent.shutdown()


def launch_interactive():
    """Launch the full interactive terminal UI."""
    from core.agent import RoninAgent
    from ui.terminal import RoninTerminal

    config = load_config()
    agent = RoninAgent(config)
    terminal = RoninTerminal(agent, config)
    terminal.run_loop()


def is_admin():
    """Check if the current process has administrative/root privileges."""
    import platform
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.getuid() == 0
    except Exception:
        return False


def ensure_admin():
    """Request administrative privileges if not already elevated."""
    import platform
    if is_admin():
        return

    print("[*] Requesting administrative privileges for full system access...")
    try:
        if platform.system() == "Windows":
            import ctypes
            # Re-run the current script as admin
            # Use ShellExecuteW with 'runas' verb to trigger UAC
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)
        else:
            # Re-run with sudo for Linux/Kali
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
    except Exception as e:
        print(f"[ERROR] Failed to elevate privileges: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ensure_admin()
    cli()
