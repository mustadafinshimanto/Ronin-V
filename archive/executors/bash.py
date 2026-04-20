import subprocess
import os

from core.types import CommandResult

class BashExecutor:
    """
    Native Linux/Bash command executor for Ronin-V.
    Captures stdout, stderr, exit code with timeout protection.
    """
    def __init__(self, config: dict):
        exec_config = config.get("executors", {}).get("bash", {})
        self.timeout = exec_config.get("timeout", 120)
        self.shell = exec_config.get("shell", "/bin/bash")

    def test_connection(self) -> bool:
        """Verify that bash is available and working."""
        try:
            res = subprocess.run([self.shell, "--version"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def execute(self, command: str, timeout: int | None = None, cwd: str | None = None, status_callback=None) -> CommandResult:
        """Execute a bash command with timeout protection."""
        timeout = timeout or self.timeout
        try:
            process = subprocess.Popen(
                [self.shell, "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd or os.getcwd()
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
                    stderr=f"CRITICAL: Bash command timed out after {timeout}s",
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
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                success=False
            )
