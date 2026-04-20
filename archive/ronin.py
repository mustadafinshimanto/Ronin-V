import os
import sys
import yaml
import click

# Force UTF-8 for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from ui.sentinel import RoninSentinelUI
from core.agent import RoninAgent

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(config_path):
        example_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
        if os.path.exists(example_path):
            with open(example_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@click.command()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug):
    try:
        config = load_config()
        agent = RoninAgent(config)
        ui = RoninSentinelUI(agent)
        ui.run()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    cli()
