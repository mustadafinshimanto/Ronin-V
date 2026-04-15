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
from core.prompts import RONIN_SYSTEM_PROMPT, OBSERVE_PROMPT, ERROR_RECOVERY_PROMPT, SUGGEST_PROMPT
from core.types import CommandResult
from executors.powershell import PowerShellExecutor
from executors.python_exec import PythonExecutor
from executors.vbox import VBoxExecutor
from executors.bash import BashExecutor
import platform


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
        self.bash_executor = BashExecutor(config)

        # VM Link State
        self.linked_vm = None  # {name: "", user: "", pass: ""}
        
        # Session Management: Always start fresh for peak reliability
        self.session_id = str(uuid.uuid4())[:8]
        self.memory.start_session(self.session_id)
        self.memory.clear_short_term()

        # Load local project context (.ronin_ctx) if it exists
        self.project_context = self._load_project_context()

        # Autonomous State
        self.auto_mode = config.get("agent", {}).get("auto_mode", False)
        self.stop_signal = False
        self.max_steps = config.get("agent", {}).get("max_steps", 10)
        
        # Auto-Discovery: Find Kali VM and pre-link with default credentials
        self._auto_link_kali()

    def _auto_link_kali(self):
        """Find a Kali VM and try connecting with default credentials."""
        try:
            vms = self.vbox_executor.list_vms()
            for vm in vms:
                name = vm["name"].lower()
                if "kali" in name or "linux" in name:
                    # Attempt connection with default kali/kali
                    if self.vbox_executor.test_connection(vm["name"], "kali", "kali"):
                        self.linked_vm = {
                            "name": vm["name"],
                            "user": "kali",
                            "pass": "kali"
                        }
                        break
        except Exception:
            pass

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
            "bash_ok": self.bash_executor.test_connection(),
            "python_ok": self.py_executor.test_connection(),
            "memory_ok": True,
        }

        if status["ollama_connected"]:
            status["model_available"] = self.llm.check_model()

        self._ollama_ready = status["ollama_connected"]
        self._model_ready = status["model_available"]

        status["host_ips"] = self._get_host_ips()
        status["compute"] = self.llm.get_compute_info()
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

    def execute_powershell(self, command: str, status_callback=None) -> CommandResult:
        """Execute a PowerShell command with safe error handling."""
        if not command.strip():
            return CommandResult(command, -1, "", "Empty command received.", False)
        try:
            return self.ps_executor.execute(command, status_callback=status_callback)
        except Exception as e:
            return CommandResult(command, -1, "", f"PowerShell Wrapper Error: {str(e)}", False)

    def execute_python(self, code: str) -> CommandResult:
        """Execute Python code with safe error handling."""
        if not code.strip():
            return CommandResult(code, -1, "", "Empty script received.", False)
        try:
            return self.py_executor.execute(code)
        except Exception as e:
            return CommandResult(code, -1, "", f"Python Wrapper Error: {str(e)}", False)

    def execute_bash(self, command: str, status_callback=None) -> CommandResult:
        """Execute a native Bash command with safe error handling."""
        if not command.strip():
            return CommandResult(command, -1, "", "Empty command received.", False)
        try:
            return self.bash_executor.execute(command, status_callback=status_callback)
        except Exception as e:
            return CommandResult(command, -1, "", f"Bash Wrapper Error: {str(e)}", False)

    def execute_vbox(self, command: str) -> CommandResult:
        """Execute a command in the linked VM with safe error handling."""
        if not self.linked_vm:
            return CommandResult(command, -1, "", "No VM linked. Use /vbox link first.", False)
        if not command.strip():
            return CommandResult(command, -1, "", "Empty command received.", False)
        try:
            return self.vbox_executor.execute(
                self.linked_vm["name"],
                self.linked_vm["user"],
                self.linked_vm["pass"],
                command
            )
        except Exception as e:
            return CommandResult(command, -1, "", f"VBox Wrapper Error: {str(e)}", False)

    def complete_task(self, final_answer: str) -> CommandResult:
        """Sentinel Termination Tool: Correctly marks a mission as accomplished."""
        self.stop_signal = True
        return CommandResult(
            command="complete_task",
            exit_code=0,
            stdout=f"MISSION ACCOMPLISHED: {final_answer}",
            stderr="",
            success=True
        )

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
        The core Autonomous Engine loop (Sentinel Build).
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
                # No more commands, check for graceful finalization
                if status_callback:
                    status_callback(f"Step {step_count}/{self.max_steps}: [warning]Passive reasoning detected. Forcing action...[/warning]")
                
                # Add a hidden directive to force a command or finalization
                self.memory.add_message("user", "MISSION UPDATE: Your last response contained no executable commands. Use `complete_task` to finalize your mission or provide a code block to proceed.", self.session_id)
                continue
                    
            # 3. Execute commands (In Auto-Mode, we just run them)
            for cmd in commands:
                if self.stop_signal: break
                
                if status_callback:
                    status_callback(f"Executing {cmd['executor']} command...")
                
                if cmd["executor"] == "powershell":
                    result = self.execute_powershell(cmd["code"], status_callback=status_callback)
                elif cmd["executor"] == "bash":
                    result = self.execute_bash(cmd["code"], status_callback=status_callback)
                elif cmd["executor"] == "vbox":
                    result = self.execute_vbox(cmd["code"])
                elif cmd["executor"] == "python":
                    result = self.execute_python(cmd["code"])
                elif cmd["executor"] == "complete_task":
                    result = self.complete_task(cmd["code"])
                    if status_callback:
                        status_callback("Mission Accomplished ✅")
                
                # 4. Show the observation to the user and feed it back for the next turn
                observation_text = f"\n\n[bold cyan]─── Observation (Step {step_count}) ───[/bold cyan]\n"
                observation_text += f"[dim]Exit Code: {result.exit_code}[/dim]\n"
                if result.stdout.strip():
                    observation_text += f"[success]STDOUT:[/success] {result.stdout[:500]}\n"
                if result.stderr.strip():
                    observation_text += f"[error]STDERR:[/error] {result.stderr[:500]}\n"
                
                yield observation_text
                
                # Update input for the next loop iteration
                current_input = f"OBSERVATION: {result.stdout[:1000]}\nERRORS: {result.stderr[:500]}\n\nAnalyze and provide the NEXT command or call `complete_task`."

            if self.stop_signal:
                break

        # MISSION RECOVERY: If we reached max steps but didn't finish, try one last turn
        if step_count >= self.max_steps and not self.stop_signal:
             yield from self.execute_final_turn(status_callback)

    def execute_final_turn(self, status_callback) -> Generator[str, None, None]:
        """Gemini-Inspired Mission Recovery: Give the agent a final chance to summarize."""
        if status_callback:
            status_callback("[error]Max steps reached. Attempting Recovery Summary...[/error]")
        
        recovery_prompt = (
            "MISSION LIMIT REACHED: You have reached the maximum allowed steps. "
            "You MUST now provide a final summary of your findings and call `complete_task` "
            "immediately. Do not attempt further commands."
        )
        
        full_response = ""
        for chunk in self.chat(recovery_prompt):
            full_response += chunk
            yield chunk
            
        commands = self.extract_commands(full_response)
        for cmd in commands:
            if cmd["executor"] == "complete_task":
                self.complete_task(cmd["code"])
                if status_callback:
                    status_callback("Recovery Summary Complete ✅")

    # ─── Command Detection ───

    def extract_commands(self, response: str) -> list[dict]:
        """
        Extract executable commands from the LLM's response.
        """
        commands = []

        # Match completion signals like ✅ or MISSION ACCOMPLISHED
        if "✅" in response or "MISSION ACCOMPLISHED" in response.upper() or "complete_task" in response.lower():
            # Try to grab whatever text is around it as the final answer
            answer_match = re.search(r"(?:MISSION ACCOMPLISHED|✅|complete_task)\s*:?\s*(.*)", response, re.IGNORECASE)
            answer = answer_match.group(1).strip() if answer_match else "Goal achieved."
            commands.append({"executor": "complete_task", "code": answer})
            return commands # Completion takes precedence

        # Match ```powershell ... ``` blocks
        ps_pattern = r"```(?:powershell|ps1|ps)\s*(.*?)```"
        for match in re.finditer(ps_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                commands.append({"executor": "powershell", "code": code})

        # Match ```python ... ``` blocks  
        py_pattern = r"```python\s*(.*?)```"
        for match in re.finditer(py_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                commands.append({"executor": "python", "code": code})

        # Match ```kali|vbox ... ``` blocks
        vbox_pattern = r"```(?:kali|vbox|vm)\s*(.*?)```"
        for match in re.finditer(vbox_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                if platform.system() == "Linux":
                    commands.append({"executor": "bash", "code": code})
                else:
                    commands.append({"executor": "vbox", "code": code})

        # Match ```bash ... ``` blocks
        bash_pattern = r"```(?:bash|sh|shell)\s*(.*?)```"
        for match in re.finditer(bash_pattern, response, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if code and not code.startswith("#"):
                if platform.system() == "Linux":
                    commands.append({"executor": "bash", "code": code})
                elif self.linked_vm:
                    commands.append({"executor": "vbox", "code": code})
                else:
                    # SMART ROUTER: Strip sudo if on Windows as it's a common hallucination
                    if platform.system() == "Windows":
                        code = re.sub(r"^sudo\s+", "", code, flags=re.MULTILINE | re.IGNORECASE)
                        # Fix common linux commands if possible
                        code = code.replace("ls -la", "ls")
                    commands.append({"executor": "powershell", "code": code})

        # Match ``` (no tag) ... ``` blocks  (Fallback for sloppy LLMs)
        generic_pattern = r"```\s*(.*?)```"
        for match in re.finditer(generic_pattern, response, re.DOTALL):
            code = match.group(1).strip()
            # Check if this code has already been captured
            if any(code == c["code"] for c in commands):
                continue
            
            if code and not code.startswith("#"):
                # Detection for complete_task inside generic block
                if "complete_task" in code.lower():
                    commands.append({"executor": "complete_task", "code": code})
                else:
                    executor = "powershell" if platform.system() == "Windows" else "bash"
                    commands.append({"executor": executor, "code": code})

        return commands

    # ─── Internal ───

    def _build_messages(self, user_input: str, memories: list[dict]) -> list[dict]:
        """
        Build the message list for the LLM.
        """
        messages = []
        
        # 1. Base Identity (The most important context)
        os_type = platform.system()
        shell = "PowerShell" if os_type == "Windows" else "Bash"
        prompt = RONIN_SYSTEM_PROMPT.format(os_type=os_type, shell=shell)
        
        messages.append({
            "role": "system",
            "content": prompt
        })

        # 2. Project-level context (.ronin_ctx)
        if self.project_context:
            messages.append({
                "role": "system",
                "content": f"LOCAL PROJECT CONTEXT (.ronin_ctx):\n{self.project_context}"
            })

        # 3. Inject relevant memories as context (RAG)
        if memories:
            memory_text = "\n".join([
                f"- [{m['timestamp'][:10]}] {m['content'][:200]}"
                for m in memories
            ])
            messages.append({
                "role": "system",
                "content": f"Relevant context from past conversations:\n{memory_text}"
            })

        # 4. Add conversation history
        context = self.memory.get_context()
        # Filter duplicates if necessary
        messages.extend(context)

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
