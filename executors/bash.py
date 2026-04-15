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

    def execute(self, command: str, status_callback=None) -> CommandResult:
        """Execute a bash command with real-time output and potential interaction."""
        try:
            # Use Popen to allow real-time reading and interaction
            process = subprocess.Popen(
                [self.shell, "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            full_stdout = []
            full_stderr = []

            # Monitor the process and yield status
            while True:
                # Check for output
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    full_stdout.append(line)
                    if status_callback:
                        # Detect if the line looks like a prompt (e.g. "[y/N]" or "Password:")
                        if any(p in line for p in ["[y/n]", "[y/N]", "Password:", "Continue?"]):
                             status_callback(f"Process awaiting input: [bold yellow]{line.strip()}[/bold yellow]")
                             # Auto-response logic: Default to 'y' for most prompts
                             if "[y/n]" in line.lower():
                                 process.stdin.write("y\n")
                                 process.stdin.flush()
                                 status_callback("Sending autonomous input: [success]y[/success]")
                        else:
                            status_callback(line.strip())

            # Collect remaining stderr
            stderr_out = process.stderr.read()
            if stderr_out:
                full_stderr.append(stderr_out)

            return CommandResult(
                success=(process.returncode == 0),
                stdout="".join(full_stdout),
                stderr="".join(full_stderr),
                exit_code=process.returncode
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=1
            )
