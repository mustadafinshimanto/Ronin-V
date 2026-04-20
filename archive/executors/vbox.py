import os
import subprocess
from typing import List
from core.types import CommandResult

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

    def list_vms(self) -> List[dict]:
        """List all currently registered VirtualBox VMs."""
        try:
            result = subprocess.run(
                [self.vbox_path, "list", "vms"],
                capture_output=True,
                text=True,
                check=True
            )
            vms = []
            for line in result.stdout.splitlines():
                if '"' in line:
                    name = line.split('"')[1]
                    vms.append({"name": name})
            return vms
        except Exception:
            return []

    def test_connection(self, vm_name: str, username: str, password: str) -> bool:
        """Test if we can connect to the guest and run a simple command."""
        result = self.execute(vm_name, username, password, "whoami")
        return result.success

    def execute(self, vm_name: str, username: str, password: str, command: str, args: List[str] = []) -> CommandResult:
        """
        Execute a command in the guest VM with shell wrapping for better environment handling.
        """
        try:
            # Join command and args into a single string
            full_user_cmd = " ".join([command] + args)
            
            # ESCAPING: Use a more robust way to pass the command to bash -c
            # We wrap it in single quotes and escape any internal single quotes
            escaped_cmd = full_user_cmd.replace("'", "'\\''")
            
            vbox_args = [
                self.vbox_path, "guestcontrol", vm_name, "run",
                "--username", username,
                "--password", password,
                "--wait-stdout",
                "--wait-stderr",
                "--", "/bin/bash", "-c", f"'{escaped_cmd}'"
            ]

            process = subprocess.run(
                vbox_args,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 60)
            )

            return CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                success=(process.returncode == 0)
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Command timed out",
                success=False,
                timed_out=True
            )
        except Exception as e:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                success=False
            )

    def copy_to_guest(self, vm_name: str, username: str, password: str, source: str, destination: str) -> CommandResult:
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

            return CommandResult(
                command=f"copy {source} to {destination}",
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                success=(process.returncode == 0)
            )
        except Exception as e:
            return CommandResult(
                command=f"copy {source} to {destination}",
                exit_code=-1,
                stdout="",
                stderr=str(e),
                success=False
            )
