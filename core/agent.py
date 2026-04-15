"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Executive Agent                   ║
║       The brain: ReAct loop + tool execution              ║
╚══════════════════════════════════════════════════════════╝
"""

import re
import json
import uuid
from typing import Generator
from pathlib import Path

from core.llm import RoninLLM
from core.memory import RoninMemory
from core.prompts import OBSERVE_PROMPT, ERROR_RECOVERY_PROMPT, SUGGEST_PROMPT
from executors.powershell import PowerShellExecutor, CommandResult
from executors.python_exec import PythonExecutor
from executors.vbox import VBoxExecutor, VBoxResult


class RoninAgent:
    """
    The Executive Agent — orchestrates everything.
    
    Flow:
    1. User sends a message
    2. Agent checks memory for relevant context
    3. Agent sends message + context to LLM
    4. LLM responds (may include commands to execute)
    5. Agent detects and executes commands if user approves
    6. Results fed back to LLM for analysis
    7. Everything logged to memory
    """

    def __init__(self, config: dict):
        """
        Initialize all subsystems.
        
        Args:
            config: Parsed config.yaml as dict
        """
        mem_config = config.get("memory", {})
        data_dir = config.get("ronin", {}).get("data_dir", "./data")
        
        # Initialize subsystems
        self.llm = RoninLLM(config)
        self.memory = RoninMemory(config)
        self.ps_executor = PowerShellExecutor(config)
        self.py_executor = PythonExecutor(config)
        self.vbox_executor = VBoxExecutor(config)

        # VM Link State
        self.linked_vm = None  # {name: "", user: "", pass: ""}
        
        # Session Persistence: Try to resume last session if available
        recent = self.memory.get_recent_sessions(limit=1)
        if recent:
            self.session_id = recent[0]["session_id"]
            # Load history back into short-term RAM window
            history = self.memory.get_session_history(self.session_id)
            for msg in history:
                self.memory.short_term.append({"role": msg["role"], "content": msg["content"]})
        else:
            self.session_id = str(uuid.uuid4())[:8]
            self.memory.start_session(self.session_id)

        # Load local project context (.ronin_ctx) if it exists
        self.project_context = self._load_project_context()

        # Autonomous State
        self.auto_mode = config.get("agent", {}).get("auto_mode", False)
        self.stop_signal = False
        self.max_steps = config.get("agent", {}).get("max_steps", 10)
        
        # Track if system is ready
        self._ollama_ready = False
        self._model_ready = False

    # ─── System Status ───

    def check_systems(self) -> dict:
        """
        Check all subsystems and return status.
        """
        import platform
        status = {
            "os": platform.system(),
            "os_release": platform.release(),
            "ollama_connected": self.llm.check_connection(),
            "model_available": False,
            "powershell_ok": self.ps_executor.test_connection(),
            "python_ok": self.py_executor.test_connection(),
            "memory_ok": True,
        }

        if status["ollama_connected"]:
            status["model_available"] = self.llm.check_model()

        self._ollama_ready = status["ollama_connected"]
        self._model_ready = status["model_available"]

        status["host_ips"] = self._get_host_ips()
        return status

    def _get_host_ips(self) -> list[str]:
        """Get the local IPv4 addresses of the host."""
        import socket
        ips = []
        try:
            # Get all IP addresses associated with the hostname
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            # Filter for IPv4 only (most likely to work for VM bridge)
            ips = [ip for ip in ips if not ip.startswith("127.")]
        except Exception:
            pass
        return ips

    # ─── Neural Bridge Logic ───

    def setup_neural_bridge(self) -> str:
        """
        Automate the host-side setup for the Master-Guest Bridge.
        Detects OS, sets env vars, and configures firewall.
        """
        import platform
        import subprocess
        os_type = platform.system()
        report = []
        
        report.append(f"[*] Initiating Neural Bridge construction on [bold cyan]{os_type}[/bold cyan]...")

        if os_type == "Windows":
            # 1. Set Environment Variable
            try:
                subprocess.run(['powershell', '-Command', 
                    "[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0', 'User')"], 
                    capture_output=True, check=True)
                report.append("[success]✓[/success] Environment OLLAMA_HOST set to 0.0.0.0 (Global).")
            except Exception as e:
                report.append(f"[error]✗[/error] Failed to set environment: {e}")

            # 2. Configure Firewall (Requires Admin which we now have)
            try:
                # Check if rule exists first
                check = subprocess.run(['powershell', '-Command', 'Get-NetFirewallRule -DisplayName "Ronin-V Neural Bridge"'], capture_output=True)
                if check.returncode != 0:
                    subprocess.run(['powershell', '-Command', 
                        'New-NetFirewallRule -DisplayName "Ronin-V Neural Bridge" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11434'], 
                        capture_output=True, check=True)
                    report.append("[success]✓[/success] Firewall rule 'Ronin-V Neural Bridge' created successfully.")
                else:
                    report.append("[info]i[/info] Firewall rule already exists. Skipping.")
            except Exception as e:
                report.append(f"[error]✗[/error] Firewall configuration failed: {e}")

        elif os_type == "Linux":
            # Linux setup (usually just iptables or informing the user about binding)
            report.append("[info]i[/info] Linux/Kali detected. Ensure Ollama is bound to 0.0.0.0 in your systemd service.")
            
        # 3. Get IP for Guest instructions
        ips = self._get_host_ips()
        main_ip = ips[0] if ips else "YOUR_HOST_IP"
        
        report.append("\n[bold green]HOST SETUP COMPLETE[/bold green]")
        report.append("--------------------------------------------------")
        report.append("[important]CRITICAL:[/important] You must **RESTART OLLAMA** in your system tray now.")
        report.append("\n[bold cyan]GUEST VM INSTRUCTIONS:[/bold cyan]")
        report.append("Copy the following into your Guest VM's `config.yaml`:")
        report.append(f"```yaml\nollama:\n  host: \"http://{main_ip}:11434\"\n```")
        
        return "\n".join(report)

    # ─── Main Chat Interface ───

    def chat(self, user_input: str) -> Generator[str, None, None]:
        """
        Process a user message and stream the AI response.
        
        This is the main entry point for conversation.
        
        Args:
            user_input: The user's message
            
        Yields:
            Response chunks (for streaming display)
        """
        # Store user message in memory
        self.memory.add_message("user", user_input, self.session_id)

        # Check for relevant memories (RAG)
        relevant_memories = self.memory.recall(user_input, n=3)

        # Build context-enhanced messages
        messages = self._build_messages(user_input, relevant_memories)

        # Stream response from LLM
        full_response = []
        try:
            for chunk in self.llm.chat(messages, stream=True):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            error_msg = f"\n\n❌ **LLM Error:** {str(e)}"
            full_response.append(error_msg)
            yield error_msg

        # Store assistant response in memory
        complete_response = "".join(full_response)
        self.memory.add_message("assistant", complete_response, self.session_id)

    def chat_no_stream(self, user_input: str) -> str:
        """
        Non-streaming version of chat. Returns full response.
        
        Args:
            user_input: The user's message
            
        Returns:
            Complete response string
        """
        self.memory.add_message("user", user_input, self.session_id)
        relevant_memories = self.memory.recall(user_input, n=3)
        messages = self._build_messages(user_input, relevant_memories)

        try:
            response = self.llm.chat(messages, stream=False)
        except Exception as e:
            response = f"❌ **LLM Error:** {str(e)}"

        self.memory.add_message("assistant", response, self.session_id)
        return response

    # ─── Command Execution ───

    def execute_powershell(self, command: str) -> CommandResult:
        """
        Execute a PowerShell command and log it.
        
        Args:
            command: PowerShell command string
            
        Returns:
            CommandResult
        """
        result = self.ps_executor.execute(command)

        # Log the execution to memory
        self.memory.add_message(
            "assistant",
            f"[EXECUTED PowerShell] `{command}`\nExit: {result.exit_code}\n{result.stdout[:500]}",
            self.session_id,
            metadata={"type": "execution", "executor": "powershell", "exit_code": result.exit_code}
        )

        return result

    def execute_python(self, code: str) -> CommandResult:
        """
        Execute Python code and log it.
        """
        result = self.py_executor.execute(code)

        self.memory.add_message(
            "assistant",
            f"[EXECUTED Python] Exit: {result.exit_code}\n{result.stdout[:500]}",
            self.session_id,
            metadata={"type": "execution", "executor": "python", "exit_code": result.exit_code}
        )

        return result

    def execute_vbox(self, command: str) -> CommandResult:
        """
        Execute a command on the linked VirtualBox VM.
        """
        if not self.linked_vm:
            return CommandResult(
                success=False,
                stdout="",
                stderr="Error: No VirtualBox VM is currently linked. Use /link <vm> <user> <pass> first.",
                exit_code=1
            )
        
        # Call the native vbox executor
        v_res = self.vbox_executor.execute(
            self.linked_vm["name"],
            self.linked_vm["user"],
            self.linked_vm["pass"],
            command
        )

        # Map VBoxResult back to the standard CommandResult for the TUI
        result = CommandResult(
            success=v_res.success,
            stdout=v_res.stdout,
            stderr=v_res.stderr,
            exit_code=v_res.exit_code
        )

        # Log the execution to memory
        self.memory.add_message(
            "assistant",
            f"[EXECUTED Kali VM] `{command}`\nExit: {result.exit_code}\n{result.stdout[:500]}",
            self.session_id,
            metadata={"type": "execution", "executor": "vbox", "exit_code": result.exit_code}
        )

        return result

    def analyze_result(self, command: str, result: CommandResult, autonomous: bool = False) -> Generator[str, None, None]:
        """
        Feed command results back to the LLM for analysis.
        """
        observe_prompt = OBSERVE_PROMPT.format(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout[:2000], 
            stderr=result.stderr[:1000],
        )

        yield from self.chat(observe_prompt)

    def run_autonomous_loop(self, user_input: str, status_callback=None) -> Generator[str, None, None]:
        """
        The core Autonomous Engine loop.
        Plan -> Act -> Observe -> Reflect -> Repeat until done or max steps reached.
        """
        self.stop_signal = False
        step_count = 0
        current_input = user_input
        
        while step_count < self.max_steps and not self.stop_signal:
            step_count += 1
            if status_callback:
                status_callback(f"Step {step_count}/{self.max_steps}: Thinking...")

            # 1. Get LLM response (Plan/Reasoning/Command)
            full_response = ""
            for chunk in self.chat(current_input):
                full_response += chunk
                yield chunk
            
            # 2. Extract commands
            commands = self.extract_commands(full_response)
            
            if not commands:
                # No more commands, check if the goal is complete
                if "✅" in full_response:
                    if status_callback:
                        status_callback("Objective complete.")
                    break
                else:
                    # Might need more information or just finished conversing
                    break
                    
            # 3. Execute commands (In Auto-Mode, we just run them)
            for cmd in commands:
                if self.stop_signal: break
                
                if status_callback:
                    status_callback(f"Executing {cmd['executor']} command...")
                
                if cmd["executor"] == "powershell":
                    result = self.execute_powershell(cmd["code"])
                else:
                    result = self.execute_python(cmd["code"])
                
                # 4. Feed back to LLM (Observation)
                if status_callback:
                    status_callback("Analyzing results...")
                
                analysis_text = ""
                # We consume the analysis generator and yield it to the UI
                for chunk in self.analyze_result(cmd["code"], result, autonomous=True):
                    analysis_text += chunk
                    yield chunk
                
                # For the next turn, the 'input' is the AI's own analysis of the result
                current_input = analysis_text
                
            # If the user input was just a string, future loops use the analysis
            if self.stop_signal:
                yield "\n\n[warning]Autonomous loop interrupted by operator.[/warning]"
                break
                
        if step_count >= self.max_steps:
             yield f"\n\n[error]Max steps ({self.max_steps}) reached. Safety halt engaged.[/error]"

    # ─── Command Detection ───

    def extract_commands(self, response: str) -> list[dict]:
        """
        Extract executable commands from the LLM's response.
        """
        commands = []

        # Match ```powershell ... ``` blocks
        ps_pattern = r"```(?:powershell|ps1|ps)\n(.*?)```"
        for match in re.finditer(ps_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                commands.append({"executor": "powershell", "code": code})

        # Match ```python ... ``` blocks  
        py_pattern = r"```python\n(.*?)```"
        for match in re.finditer(py_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                commands.append({"executor": "python", "code": code})

        # Match ```kali|vbox ... ``` blocks
        vbox_pattern = r"```(?:kali|vbox|vm)\n(.*?)```"
        for match in re.finditer(vbox_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                commands.append({"executor": "vbox", "code": code})

        # Match ```bash ... ``` blocks
        bash_pattern = r"```bash\n(.*?)```"
        for match in re.finditer(bash_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                if self.linked_vm:
                    # If we have a VM linked, prefer running bash on the VM
                    commands.append({"executor": "vbox", "code": code})
                else:
                    # Otherwise fallback to WSL on host
                    commands.append({"executor": "powershell", "code": f"wsl -e bash -c '{code}'"})

        return commands

    # ─── Internal ───

    def _build_messages(self, user_input: str, memories: list[dict]) -> list[dict]:
        """
        Build the message list for the LLM.
        """
        messages = []

        # 1. Project-level context (.ronin_ctx) - Highest priority
        if self.project_context:
            messages.append({
                "role": "system",
                "content": f"LOCAL PROJECT CONTEXT (.ronin_ctx):\n{self.project_context}"
            })

        # 2. Inject relevant memories as context (RAG)
        if memories:
            memory_text = "\n".join([
                f"- [{m['timestamp'][:10]}] {m['content'][:200]}"
                for m in memories
            ])
            messages.append({
                "role": "system",
                "content": f"Relevant context from past conversations:\n{memory_text}"
            })

        # 3. Add conversation history
        context = self.memory.get_context()
        if context and context[-1].get("role") == "user" and context[-1].get("content") == user_input:
            messages.extend(context[:-1])
        else:
            messages.extend(context)

        # 4. Add current user message
        messages.append({"role": "user", "content": user_input})

        return messages

    def _load_project_context(self) -> str | None:
        """Load the .ronin_ctx file if available in the current directory."""
        ctx_file = Path(".ronin_ctx")
        if ctx_file.exists():
            try:
                return ctx_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return None

    def set_role(self, role: str):
        """Switch the agent's professional persona."""
        if role == "recon":
            p = "You are now in RECON MODE. Phase: Discovery. Focus on Nmap, asset discovery, and endpoint scanning."
        elif role == "audit":
            p = "You are now in AUDIT MODE. Phase: Analysis. Focus on code vulnerability scanning and CVE matching."
        elif role == "vibe":
            p = "You are now in VIBE MODE. Phase: Generation. Focus on rapid full-stack scaffolding and creative coding."
        else:
            p = "You are now in DEFAULT MODE. Phase: General execution."
            
        self.system_message["content"] += f"\n\nCURRENT OPERATIONAL ROLE: {p}"
        self.memory.add_message("system", p, self.session_id)

    def suggest_next_steps(self) -> Generator[str, None, None]:
        """Ask the AI to suggest the next 3 tactical commands."""
        yield from self.chat(SUGGEST_PROMPT)

    def shutdown(self):
        """Clean shutdown — close all connections."""
        self.memory.end_session(self.session_id)
        self.memory.close()
