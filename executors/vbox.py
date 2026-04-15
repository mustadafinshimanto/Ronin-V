import subprocess
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class VBoxResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int

class VBoxExecutor:
    """
    Executor for running commands inside a VirtualBox Guest VM.
    Uses VBoxManage guestcontrol.
    """

    def __init__(self, config: dict):
        self.config = config.get("vbox", {})
        # Default path for VBoxManage on Windows
        self.vbox_path = self.config.get("path", r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe")
        
        # Verify if VBoxManage exists
        if not os.path.exists(self.vbox_path):
            self.vbox_path = "VBoxManage" # Fallback to PATH

    def test_connection(self, vm_name: str, username: str, password: str) -> bool:
        """Test if we can connect to the guest and run a simple command."""
        result = self.execute(vm_name, username, password, "whoami")
        return result.success

    def execute(self, vm_name: str, username: str, password: str, command: str, args: List[str] = []) -> VBoxResult:
        """
        Execute a command in the guest VM.
        VBoxManage guestcontrol <vm> run --username <user> --password <pass> --wait-stdout -- <cmd>
        """
        try:
            full_cmd = [
                self.vbox_path, "guestcontrol", vm_name, "run",
                "--username", username,
                "--password", password,
                "--wait-stdout",
                "--", command
            ] + args

            process = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 60)
            )

            return VBoxResult(
                success=(process.returncode == 0),
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode
            )
        except subprocess.TimeoutExpired:
            return VBoxResult(False, "", "Command timed out", -1)
        except Exception as e:
            return VBoxResult(False, "", str(e), -1)

    def copy_to_guest(self, vm_name: str, username: str, password: str, source: str, destination: str) -> VBoxResult:
        """Copy a file from host to guest."""
        try:
            full_cmd = [
                self.vbox_path, "guestcontrol", vm_name, "copyto",
                source,
                "--target-directory", destination,
                "--username", username,
                "--password", password
            ]

            process = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 120)
            )

            return VBoxResult(
                success=(process.returncode == 0),
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode
            )
        except Exception as e:
            return VBoxResult(False, "", str(e), -1)
