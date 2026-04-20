import subprocess
import time
import os
import sys

def test_ronin_ui():
    print("[*] Starting Ronin-V UI Test...")
    
    # Run ronin.py using the local venv if possible, or the current python
    cmd = [sys.executable, "ronin.py"]
    
    # Start the process with a pseudo-terminal if possible, but here we just use pipes
    # We want to send commands and capture the output
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        bufsize=0
    )

    try:
        # Give it a few seconds to warm up and print the banner
        time.sleep(5)
        
        # 1. Check for Banner and Initialization
        stdout, stderr = process.communicate(input="/manual\nhello ronin, who are you?\n/exit\n", timeout=30)
        
        print("\n--- CAPTURED STDOUT ---")
        # Print first 500 characters and last 500 to see banner and prompt
        print(stdout[:1000])
        print("...")
        print(stdout[-1000:])
        print("-----------------------")
        
        if "VIBE SENTINEL" in stdout or "RONIN-V" in stdout:
            print("[SUCCESS] Banner detected.")
        else:
            print("[FAILURE] Banner not detected.")
            
        if "ronin/sentinel >" in stdout or "ronin" in stdout:
            print("[SUCCESS] Prompt detected.")
        else:
            print("[FAILURE] Prompt not detected.")

        if stderr:
            print(f"[WARNING] Stderr output: {stderr}")

    except subprocess.TimeoutExpired:
        print("[ERROR] Ronin-V timed out.")
        process.kill()
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        process.kill()

if __name__ == "__main__":
    test_ronin_ui()
