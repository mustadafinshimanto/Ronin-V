import os
import sys
import yaml
import click
from ui.terminal import RoninTerminal
from core.agent import RoninAgent

def load_config():
    """Load configuration from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(config_path):
        # Fallback to example config if not exists
        example_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
        if os.path.exists(example_path):
            with open(example_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_elevation_check():
    """Ensure we have administrative/root rights."""
    try:
        if os.name == "nt":
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                # Re-run the script as administrator
                print("[*] Requesting Windows Administrator privileges...")
                params = " ".join([f'"{arg}"' for arg in sys.argv])
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                sys.exit(0)
        else:
            if os.geteuid() != 0:
                print("[!] ERROR: Ronin-V must be run with root privileges (sudo).")
                print("[!] Please run: sudo ./run_ronin.sh")
                sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to elevate privileges: {e}")
        sys.exit(1)

@click.command()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug):
    """Entry point for Ronin-V AI Terminal."""
    # Ensure elevated privileges
    run_elevation_check()
    
    try:
        config = load_config()
        if debug:
            config["log_level"] = "DEBUG"

        # Initialize core components
        agent = RoninAgent(config)
        terminal = RoninTerminal(agent, config)

        # Start the UI
        terminal.run_loop()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    cli()
