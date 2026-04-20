"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘              RONIN-V â€” Executive Agent                   â•‘
â•‘       The brain: ReAct loop + tool execution              â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
"""

import re
import json
import uuid
import platform
from typing import Generator
from pathlib import Path

from core.llm import RoninLLM
from core.memory import RoninMemory
from core.prompts import RONIN_SYSTEM_PROMPT, OBSERVE_PROMPT, SUGGEST_PROMPT
from core.types import CommandResult
from executors.powershell import PowerShellExecutor
from executors.python_exec import PythonExecutor
from executors.vbox import VBoxExecutor
from executors.bash import BashExecutor


class RoninAgent:
    def __init__(self, config: dict):
        self.config = config
        self.llm = RoninLLM(config)
        self.memory = RoninMemory(config)
        self.ps_executor = PowerShellExecutor(config)
        self.py_executor = PythonExecutor(config)
        self.vbox_executor = VBoxExecutor(config)
        self.bash_executor = BashExecutor(config)

        self.linked_vm = None
        self.session_id = str(uuid.uuid4())[:8]
        self.memory.start_session(self.session_id)
        
        self.auto_mode = config.get("agent", {}).get("auto_mode", False)
        self.stop_signal = False
        self.max_steps = config.get("agent", {}).get("max_steps", 10)
        self.current_role = "DEFAULT"

        self._auto_link_kali()

    def _auto_link_kali(self):
        try:
            vms = self.vbox_executor.list_vms()
            for vm in vms:
                name = vm["name"].lower()
                if "kali" in name or "linux" in name:
                    if self.vbox_executor.test_connection(vm["name"], "kali", "kali"):
                        self.linked_vm = {"name": vm["name"], "user": "kali", "pass": "kali"}
                        break
        except Exception: pass

    def check_systems(self) -> dict:
        status = {
            "os": platform.system(),
            "ollama_connected": self.llm.check_connection(),
            "compute": self.llm.get_compute_info(),
            "llm": self.llm.model_name
        }
        return status

    def setup_neural_bridge(self) -> str:
        import subprocess
        os_type = platform.system()
        report = [f"[*] Configuring Neural Bridge on {os_type}..."]
        
        if os_type == "Windows":
            try:
                subprocess.run(['powershell', '-Command', "[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0', 'User')"], check=True)
                report.append("[success]âœ“[/success] OLLAMA_HOST bound to 0.0.0.0")
                subprocess.run(['powershell', '-Command', 'if (!(Get-NetFirewallRule -DisplayName "Ronin-V Bridge" -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName "Ronin-V Bridge" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11434 }'], check=True)
                report.append("[success]âœ“[/success] Firewall rule active.")
            except Exception as e:
                report.append(f"[error]âœ—[/error] Setup failed: {e}")
        
        return "\n".join(report)

    def chat(self, user_input: str) -> Generator[str, None, None]:
        self.memory.add_message("user", user_input, self.session_id)
        relevant = self.memory.recall(user_input, n=3)
        messages = self._build_messages(user_input, relevant)

        full_response = []
        try:
            for chunk in self.llm.chat(messages, stream=True):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            yield f"\n[LLM ERROR] {e}"

        self.memory.add_message("assistant", "".join(full_response), self.session_id)

    def extract_commands(self, response: str) -> list[dict]:
        commands = []
        patterns = [
            (r"```(?:powershell|ps1|ps)\s*(.*?)```", "powershell"),
            (r"```python\s*(.*?)```", "python"),
            (r"```(?:kali|vbox|vm)\s*(.*?)```", "vbox"),
            (r"```(?:bash|sh|shell)\s*(.*?)```", "bash" if platform.system() == "Linux" else "vbox"),
        ]

        for pattern, executor in patterns:
            for match in re.finditer(pattern, response, re.DOTALL | re.IGNORECASE):
                code = match.group(1).strip()
                if code and not any(c['code'] == code for c in commands):
                    final_exec = executor
                    if executor == "vbox" and not self.linked_vm:
                        final_exec = "powershell" if platform.system() == "Windows" else "bash"
                    commands.append({"executor": final_exec, "code": code})

        if not commands:
            if "âœ…" in response or "complete_task" in response.lower():
                m = re.search(r"(?:âœ…|complete_task)\s*:?\s*(.*)", response, re.IGNORECASE)
                commands.append({"executor": "complete_task", "code": m.group(1).strip() if m else "Task done."})

        return commands

    def execute_proposed_command(self, cmd: dict) -> CommandResult:
        try:
            if cmd["executor"] == "powershell": return self.ps_executor.execute(cmd["code"])
            if cmd["executor"] == "python": return self.py_executor.execute(cmd["code"])
            if cmd["executor"] == "bash": return self.bash_executor.execute(cmd["code"])
            if cmd["executor"] == "vbox":
                return self.vbox_executor.execute(self.linked_vm["name"], self.linked_vm["user"], self.linked_vm["pass"], cmd["code"])
        except Exception as e:
            return CommandResult(cmd["code"], -1, "", str(e), False)
        return CommandResult(cmd["code"], -1, "", "Unknown executor", False)

    def _build_messages(self, user_input: str, memories: list) -> list:
        os_type = platform.system()
        shell = "PowerShell" if os_type == "Windows" else "Bash"
        base_prompt = RONIN_SYSTEM_PROMPT.format(os_type=os_type, shell=shell)
        
        if self.current_role != "DEFAULT":
            base_prompt += f"\n\nCURRENT OPERATIONAL ROLE: {self.current_role}"

        messages = [{"role": "system", "content": base_prompt}]
        
        if self.linked_vm:
            messages.append({"role": "system", "content": f"VM LINKED: {self.linked_vm['name']} as {self.linked_vm['user']}"})
        
        messages.extend(self.memory.get_context())
        return messages

    def set_role(self, role: str):
        if role == "recon":
            self.current_role = "RECON MODE. Phase: Discovery. Focus on Nmap, asset discovery, and endpoint scanning."
        elif role == "audit":
            self.current_role = "AUDIT MODE. Phase: Analysis. Focus on code vulnerability scanning and CVE matching."
        elif role == "vibe":
            self.current_role = "VIBE MODE. Phase: Generation. Focus on rapid full-stack scaffolding and creative coding."
        else:
            self.current_role = "DEFAULT"

    def suggest_next_steps(self) -> Generator[str, None, None]:
        yield from self.chat(SUGGEST_PROMPT)

    def clear_memory(self):
        self.memory.clear_short_term()
        # Ensure we start a fresh session logic
        self.session_id = str(uuid.uuid4())[:8]
        self.memory.start_session(self.session_id)
        self.current_role = "DEFAULT"
