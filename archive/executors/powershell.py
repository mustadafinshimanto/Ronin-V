"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — PowerShell Executor               ║
║         Execute PS commands on the local Windows host     ║
╚══════════════════════════════════════════════════════════╝
"""

import subprocess
import os
from dataclasses import dataclass


from core.types import CommandResult

class PowerShellExecutor:
    """
    Execute PowerShell commands on the local Windows host.
    Captures stdout, stderr, exit code with timeout protection.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Parsed config.yaml as dict
        """
        exec_config = config.get("executors", {}).get("powershell", {})
        self.timeout = exec_config.get("timeout", 60)
        self.shell = exec_config.get("shell", "powershell.exe")
        self.enabled = exec_config.get("enabled", True)

    def execute(self, command: str, timeout: int | None = None, cwd: str | None = None, status_callback=None) -> CommandResult:
        """Execute a PowerShell command with real-time feedback."""
        if not self.enabled:
            return CommandResult(command=command, exit_code=-1, stdout="", stderr="PowerShell executor is disabled in config.", success=False)

        timeout = timeout or self.timeout
        try:
            process = subprocess.Popen(
                [self.shell, "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd or os.getcwd(),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return CommandResult(
                    command=command,
                    exit_code=-1,
                    stdout=stdout,
                    stderr=f"CRITICAL: PowerShell command timed out after {timeout}s",
                    success=False,
                    timed_out=True
                )

            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout or "",
                stderr=stderr or "",
                success=(exit_code == 0)
            )

        except Exception as e:
            return CommandResult(command=command, exit_code=-1, stdout="", stderr=f"Execution error: {str(e)}", success=False)

    def execute_script(self, script_path: str, timeout: int | None = None) -> CommandResult:
        """
        Execute a .ps1 script file.
        """
        command = f"& '{script_path}'"
        return self.execute(command, timeout=timeout)

    def test_connection(self) -> bool:
        """Verify PowerShell is accessible."""
        result = self.execute("Write-Output 'Ronin-V PowerShell OK'", timeout=10)
        return result.success and "OK" in result.stdout
