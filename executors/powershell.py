"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — PowerShell Executor               ║
║         Execute PS commands on the local Windows host     ║
╚══════════════════════════════════════════════════════════╝
"""

import subprocess
import os
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def __str__(self) -> str:
        output = f"Exit Code: {self.exit_code}"
        if self.timed_out:
            output += " (TIMED OUT)"
        if self.stdout.strip():
            output += f"\n\n{self.stdout.strip()}"
        if self.stderr.strip():
            output += f"\n\nErrors:\n{self.stderr.strip()}"
        return output


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
            return CommandResult(command=command, exit_code=-1, stdout="", stderr="PowerShell executor is disabled in config.")

        timeout = timeout or self.timeout
        try:
            process = subprocess.Popen(
                [self.shell, "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                cwd=cwd or os.getcwd(),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                bufsize=1,
                universal_newlines=True
            )

            full_stdout = []
            full_stderr = []

            # Stream stdout
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    full_stdout.append(line)
                    if status_callback:
                        status_callback(line.strip())

            # Collect stderr
            stderr_out = process.stderr.read()
            if stderr_out:
                full_stderr.append(stderr_out)

            return CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout="".join(full_stdout),
                stderr="".join(full_stderr),
            )

        except Exception as e:
            return CommandResult(command=command, exit_code=-1, stdout="", stderr=f"Execution error: {str(e)}")

    def execute_script(self, script_path: str, timeout: int | None = None) -> CommandResult:
        """
        Execute a .ps1 script file.
        
        Args:
            script_path: Path to the PowerShell script
            timeout: Override default timeout
            
        Returns:
            CommandResult
        """
        command = f"& '{script_path}'"
        return self.execute(command, timeout=timeout)

    def test_connection(self) -> bool:
        """Verify PowerShell is accessible."""
        result = self.execute("Write-Output 'Ronin-V PowerShell OK'", timeout=10)
        return result.success and "OK" in result.stdout
