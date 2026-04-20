"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Python Executor                   ║
║         Execute Python scripts on the local host          ║
╚══════════════════════════════════════════════════════════╝
"""

import subprocess
import sys
import os
import tempfile
from core.types import CommandResult

class PythonExecutor:
    """
    Execute Python scripts and one-liners on the local host.
    Uses subprocess for isolation — AI-generated code runs in a separate process.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Parsed config.yaml as dict
        """
        exec_config = config.get("executors", {}).get("python", {})
        self.timeout = exec_config.get("timeout", 60)
        self.enabled = exec_config.get("enabled", True)
        self.python_path = sys.executable  # Use the same Python that's running Ronin-V

    def execute(self, code: str, timeout: int | None = None, cwd: str | None = None) -> CommandResult:
        """
        Execute a Python code snippet.
        Writes code to a temp file, runs it as a subprocess.
        
        Args:
            code: Python code to execute
            timeout: Override default timeout (seconds)
            cwd: Working directory
            
        Returns:
            CommandResult with stdout, stderr, exit code
        """
        if not self.enabled:
            return CommandResult(
                command=code[:100] + "..." if len(code) > 100 else code,
                exit_code=-1,
                stdout="",
                stderr="Python executor is disabled in config.",
                success=False
            )

        timeout = timeout or self.timeout

        # Write code to temp file for execution
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                prefix="ronin_exec_",
                delete=False,
                dir=tempfile.gettempdir(),
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name
        except Exception as e:
            return CommandResult(
                command=code[:100],
                exit_code=-1,
                stdout="",
                stderr=f"Failed to create temp script: {e}",
                success=False
            )

        try:
            result = subprocess.run(
                [self.python_path, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.getcwd(),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            return CommandResult(
                command=code[:200] + "..." if len(code) > 200 else code,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=(result.returncode == 0)
            )

        except subprocess.TimeoutExpired:
            return CommandResult(
                command=code[:100],
                exit_code=-1,
                stdout="",
                stderr=f"Script timed out after {timeout} seconds.",
                success=False,
                timed_out=True
            )
        except Exception as e:
            return CommandResult(
                command=code[:100],
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                success=False
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def execute_oneliner(self, code: str, timeout: int | None = None) -> CommandResult:
        """
        Execute a Python one-liner via -c flag (no temp file).
        
        Args:
            code: Single-line Python expression
            timeout: Override default timeout
            
        Returns:
            CommandResult
        """
        timeout = timeout or self.timeout

        try:
            result = subprocess.run(
                [self.python_path, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return CommandResult(
                command=code,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=(result.returncode == 0)
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=code,
                exit_code=-1,
                stdout="",
                stderr=f"Timed out after {timeout}s.",
                success=False,
                timed_out=True
            )
        except Exception as e:
            return CommandResult(
                command=code,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                success=False
            )

    def test_connection(self) -> bool:
        """Verify Python executor works."""
        result = self.execute_oneliner("print('Ronin-V Python OK')", timeout=10)
        return result.success and "OK" in result.stdout
