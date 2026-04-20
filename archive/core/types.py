from dataclasses import dataclass
from typing import Optional

@dataclass
class CommandResult:
    """Unified result schema for all Ronin-V executors."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    timed_out: bool = False
    
    def __str__(self) -> str:
        output = f"Exit Code: {self.exit_code}"
        if self.timed_out:
            output += " (TIMED OUT)"
        if self.stdout.strip():
            output += f"\n\n{self.stdout.strip()}"
        if self.stderr.strip():
            output += f"\n\nErrors:\n{self.stderr.strip()}"
        return output
