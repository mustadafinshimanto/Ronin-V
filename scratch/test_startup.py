import os
import sys
import yaml
from core.agent import RoninAgent

def load_config():
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

print("[*] Testing System Checks...")
try:
    config = load_config()
    print("[SUCCESS] Config loaded with UTF-8.")
    
    agent = RoninAgent(config)
    print("[*] Initializing system status...")
    status = agent.check_systems()
    
    print("\n--- Diagnostic Results ---")
    print(f"OS: {status['os']}")
    print(f"Ollama: {'ONLINE' if status['ollama_connected'] else 'OFFLINE'}")
    print(f"Model: {status['compute']['name']} ({status['compute']['type']})")
    print(f"Memory: {'READY' if status['memory_ok'] else 'ERROR'}")
    print(f"Python: {'OK' if status['python_ok'] else 'ERROR'}")
    
    if status['os'] == "Windows":
        print(f"PowerShell: {'OK' if status['powershell_ok'] else 'ERROR'}")
    else:
        print(f"Bash: {'OK' if status['bash_ok'] else 'ERROR'}")
    print("--------------------------\n")
    print("[SUCCESS] System checks completed without crashes.")

except Exception as e:
    print(f"[FATAL ERROR] {e}")
    import traceback
    traceback.print_exc()
