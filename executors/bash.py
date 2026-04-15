import subprocess
import os

class CommandResult:
    def __init__(self, success: bool, stdout: str, stderr: str, exit_code: int):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

class BashExecutor:
    """
    Native Linux/Bash command executor for Ronin-V.
    """
    def __init__(self, config: dict):
        self.config = config.get("executors", {}).get("bash", {})
        self.timeout = self.config.get("timeout", 60)
        self.shell = self.config.get("shell", "/bin/bash")

    def test_connection(self) -> bool:
        """Verify that bash is available and working."""
        try:
            res = subprocess.run([self.shell, "--version"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def execute(self, command: str) -> CommandResult:
        """Execute a bash command and return the result."""
        try:
            # Use -c to execute the command string
            process = subprocess.run(
                [self.shell, "-c", command],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            return CommandResult(
                success=(process.returncode == 0),
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Error: Command timed out after {self.timeout} seconds.",
                exit_code=124
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=1
            )
