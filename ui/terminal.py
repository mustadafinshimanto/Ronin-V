"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Terminal UI                       ║
║         Interactive CLI built on Rich/Prompt-Toolkit     ║
╚══════════════════════════════════════════════════════════╝
"""

import sys
import time
from typing import Generator

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.prompt import Confirm
from rich.table import Table
from rich.columns import Columns
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from ui.themes import CYBERPUNK_THEME, BANNER, MINI_BANNER
from core.agent import RoninAgent
from executors.powershell import CommandResult


class MissionHUD:
    """State-managed tactical display (Sentinel Build)."""
    def __init__(self, console, width: int, agent):
        self.console = console
        self.width = width
        self.agent = agent
        self.strategy_msg = "Awaiting deployment..."
        self.log_buffer = []
        self.response_text = ""
        self.live = None
        self.step_count = 0

    def start(self):
        # Refresh per second reduced to 4 to stop flickering on high-load streaming
        self.live = Live(self._build_ui(), refresh_per_second=4, console=self.console)
        self.live.start()

    def stop(self):
        if self.live:
            self.live.stop()

    def update_strategy(self, msg: str):
        # Extract step count if available
        if "Step " in msg:
            try:
                self.step_count = msg.split("/")[0].split(" ")[1]
            except Exception: pass
            
        self.strategy_msg = msg
        if msg.startswith("Step "):
            self.log_buffer = []
        self._refresh()

    def add_log(self, log: str):
        self.log_buffer.append(f"[dim]>[/dim] {log}")
        if len(self.log_buffer) > 6:
            self.log_buffer.pop(0)
        self._refresh()

    def update_response(self, chunk: str):
        self.response_text += chunk
        self._refresh()

    def _refresh(self):
        if self.live:
            self.live.update(self._build_ui())

    def _build_ui(self):
        # 1. Header: Telemetry
        vm_status = "[success]LINKED[/success]" if self.agent.linked_vm else "[dim]OFFLINE[/dim]"
        header = Columns([
            f"[bold cyan]MISSION STEP:[/bold cyan] {self.step_count}",
            f"[bold cyan]VM STATUS:[/bold cyan] {vm_status}",
            f"[bold cyan]MODE:[/bold cyan] [success]SENTINEL AUTO[/success]"
        ], equal=True, expand=True)

        # 2. Main Grid: Tactical Status
        grid = Table.grid(expand=True)
        grid.add_column(width=12)
        grid.add_column()
        
        status_spinner = Spinner("dots", text=f"[cyan]{self.strategy_msg}[/cyan]")
        grid.add_row("[bold]STRATEGY[/bold]", status_spinner)
        
        # 3. Mission Logs
        logs = "\n".join(self.log_buffer) if self.log_buffer else "[dim]No recent logs.[/dim]"
        
        # Assemble Panels
        main_panel = Panel(
            Group(
                header,
                "[dim]──────────────────────────────────────────────────────────[/dim]",
                grid,
                "[dim]──────────────────────────────────────────────────────────[/dim]",
                "[bold yellow]MISSION LOGS[/bold yellow]",
                logs
            ),
            title="[header]Ronin-V Tactical Sentinel HUD[/header]",
            border_style="cyan",
            width=self.width
        )
        
        elements = [main_panel]
        
        # 4. Streamed Response
        if self.response_text.strip():
            # Apply Markdown for better aesthetics 
            elements.append(Markdown(self.response_text))
            
        return Group(*elements)


class RoninTerminal:
    """
    Main interactive terminal UI for Ronin-V.
    """

    def __init__(self, agent: RoninAgent, config: dict):
        self.agent = agent
        self.console = Console(theme=CYBERPUNK_THEME)
        self.config = config.get("ui", {})
        
        self.kb = KeyBindings()
        
        @self.kb.add('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')
            
        @self.kb.add('c-a')
        def _(event):
            self.agent.auto_mode = not self.agent.auto_mode
            self.console.print(f"\n[info]Mode switched to {'AUTO' if self.agent.auto_mode else 'MANUAL'}[/info]")

        style = Style.from_dict({
            'prompt': '#ff2a2a bold',
            'bottom-toolbar': 'bg:#1a0505 #ff4a4a',
            'rprompt': '#888888',
        })
        
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        
        class SlashCommandCompleter(Completer):
            def __init__(self, commands):
                self.commands = commands
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                if text.startswith('/'):
                    for cmd in self.commands:
                        if cmd.startswith(text):
                            yield Completion(cmd, start_position=-len(text))

        command_completer = SlashCommandCompleter([
            '/help', '/status', '/model', '/clear', '/exit', 
            '/auto', '/manual', '/recon', '/audit', '/vibe',
            '/link', '/suggest', '/bridge'
        ])
        
        self.session = PromptSession(
            history=FileHistory('./data/sessions/history.txt'),
            style=style,
            key_bindings=self.kb,
            completer=command_completer,
            auto_suggest=AutoSuggestFromHistory(),
            bottom_toolbar=self._get_bottom_toolbar
        )

    def _get_bottom_toolbar(self):
        """Dynamic bottom toolbar for the PromptSession."""
        mode_str = "[AUTO]" if self.agent.auto_mode else "[MANUAL]"
        mode_color = "green" if self.agent.auto_mode else "white"
        vm_str = f"VM: {self.agent.linked_vm['name']}" if self.agent.linked_vm else "VM: NONE"
        return HTML(f' <b>Ronin-V CLI</b> | {vm_str} | Mode: <style color="{mode_color}">{mode_str}</style> | Keys: <b>[Ctrl+A]</b> Toggle Auto')

    def print_banner(self):
        """Display the startup ASCII banner."""
        if self.config.get("show_banner", True):
            if self.console.width < 60:
                self.console.print(MINI_BANNER)
            else:
                self.console.print(BANNER)
            self.console.print("\n[system.status]Initializing neural link... unrestricted mode engaged...[/system.status]")

    def print_system_status(self, status: dict):
        """Display verbose subsystem check results."""
        from rich.columns import Columns
        
        # Dynamic API label based on OS
        api_label = "PowerShell API" if status['os'] == "Windows" else "Bash/Linux API"
        api_status = status['powershell_ok'] if status['os'] == "Windows" else status['bash_ok']
        
        # Compute info (GPU/Model)
        compute = status.get("compute", {"name": "Unknown", "gpu": False, "type": "Detecting..."})
        compute_label = f"[success]{compute['type']}[/success]" if compute['gpu'] else f"[dim]{compute['type']}[/dim]"
        
        info_lines = [
            f"[*] Ollama connection: {'[success]ONLINE[/success]' if status['ollama_connected'] else '[error]OFFLINE[/error]'}",
            f"[*] Neural Compute:    {compute_label}",
            f"[*] Active Model:      [cyan]{compute['name']}[/cyan]",
            f"[*] {api_label}:   {'[success]ONLINE[/success]' if api_status else '[error]ERROR[/error]'}",
            f"[*] Python Executor:  {'[success]ONLINE[/success]' if status['python_ok'] else '[error]ERROR[/error]'}",
            f"[*] Kali VM Link:     {'[success]CONNECTED[/success]' if self.agent.linked_vm else '[dim]OFFLINE[/dim]'}",
            f"[*] Memory Engine:    {'[success]READY[/success]' if status['memory_ok'] else '[error]ERROR[/error]'}"
        ]

        self.console.print(Panel(
            Group(
                f"[bold white]OS Environment:[/bold white] {status['os']} {status['os_release']}\n"
                f"[bold white]Model Identity:[/bold white] {self.agent.llm.model_name}\n"
                "[dim]──────────────────────────────────────────────────────────[/dim]",
                Columns(info_lines, equal=True, expand=True)
            ),
            title="[header]Agent Core Initialized[/header]",
            border_style="panel.border",
            expand=False
        ))

    def run_loop(self):
        """Main TUI loop."""
        self.console.clear() 
        self.print_banner()
        
        with self.console.status("[bold cyan]Synchronizing neural state...", spinner="bouncingBar"):
            status = self.agent.check_systems()
            
        self.print_system_status(status)
        
        if not status["ollama_connected"] or not status["model_available"]:
            self.console.print("\n[error]CRITICAL FAILURE:[/error] AI Core offline. Please check Ollama installation and ensure the 'ronin-dolphin' model is created.")
            sys.exit(1)

        self.console.print("\n[info]CLI AI Agent is locked and loaded. Ready for Ethical Hacking... (Type 'exit' to abort)[/info]\n")

        while True:
            try:
                user_input = self.session.prompt("λ ronin > ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "q", "/exit"]:
                    break
                elif user_input.lower() in ["clear", "cls", "/clear", "/cls"]:
                    self.console.clear()
                    # Reset memory state and start a fresh session to escape loops
                    import uuid
                    self.agent.memory.clear_short_term()
                    self.agent.session_id = str(uuid.uuid4())[:8]
                    self.agent.memory.start_session(self.agent.session_id)
                    self.console.print("[info]Terminal cleared and tactical context reset (New Session ID: " + self.agent.session_id + ").[/info]\n")
                    continue
                elif user_input.lower() == "/help":
                    self._show_help()
                    continue
                elif user_input.lower() == "/status":
                    with self.console.status("[bold cyan]Running diagnostics...", spinner="bouncingBar"):
                        status = self.agent.check_systems()
                    self.print_system_status(status)
                    continue
                elif user_input.lower() == "/model":
                    self.console.print(Panel(
                        f"[bold white]Active Model:[/bold white] [success]{self.agent.llm.model_name}[/success]\n"
                        f"[bold white]Context Window:[/bold white] {self.agent.llm.ctx_length} tokens\n"
                        f"[bold white]Temperature:[/bold white] {self.agent.llm.temperature}\n"
                        f"[bold white]Endpoint:[/bold white] {self.agent.llm.client._client.base_url}",
                        title="Model Configuration",
                        border_style="info"
                    ))
                    continue
                elif user_input.lower() == "/auto":
                    self.agent.auto_mode = True
                    self.console.print(Panel("[success]AUTONOMOUS ENGINE ENGAGED[/success]\nAgent will now execute sequences until objective is marked complete.", border_style="success"))
                    continue
                elif user_input.lower() == "/manual":
                    self.agent.auto_mode = False
                    self.console.print(Panel("[info]MANUAL OVERRIDE ENGAGED[/info]\nAll commands will require explicit authorization.", border_style="info"))
                    continue
                elif user_input.lower() in ["/recon", "/audit", "/vibe"]:
                    role = user_input[1:].lower()
                    self.agent.set_role(role)
                    self.console.print(Panel(f"Agent role specialized for: [bold white]{role.upper()}[/bold white]", border_style="panel.border"))
                    continue
                elif user_input.lower().startswith("/link"):
                    parts = user_input.split()
                    if len(parts) != 4:
                        self.console.print("[warning]Usage: /link <vm_name> <user> <pass>[/warning]")
                        continue
                    vm_name, user, password = parts[1], parts[2], parts[3]
                    with self.console.status(f"[bold cyan]Linking to {vm_name}...", spinner="aesthetic"):
                        if self.agent.vbox_executor.test_connection(vm_name, user, password):
                            self.agent.linked_vm = {"name": vm_name, "user": user, "pass": password}
                            self.console.print(Panel(f"[success]Master Link established with {vm_name}[/success]", border_style="success"))
                        else:
                            self.console.print(Panel(f"[error]Failed to link with {vm_name}[/error]", border_style="error"))
                    continue
                elif user_input.lower() == "/suggest":
                    self.console.print(Panel("[bold cyan]Analyzing mission telemetry...[/bold cyan]", border_style="cyan"))
                    self._handle_interaction(user_input)
                    continue
                elif user_input.lower() == "/bridge":
                    self.console.print(Panel("[bold cyan]Neural Bridge Architect rising...[/bold cyan]", border_style="cyan"))
                    result = self.agent.setup_neural_bridge()
                    self.console.print(result)
                    continue

                self._handle_interaction(user_input)

            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self.console.print(f"\n[error]Terminal Error:[/error] {e}")

        self.console.print("[info]Shutting down neural link... Goodbye.[/info]")
        self.agent.shutdown()

    def _show_help(self):
        """Show available CLI commands."""
        table = Table(
            title="Ronin-V Elite CLI Commands", 
            border_style="panel.border",
            collapse_padding=True if self.console.width < 50 else False
        )
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_row("/auto", "Engage Autonomous Engine")
        table.add_row("/manual", "Override to Manual mode")
        table.add_row("/bridge", "Automate Neural Bridge Setup")
        table.add_row("/link", "Connect to a VirtualBox VM")
        table.add_row("/recon", "Switch to RECON role")
        table.add_row("/audit", "Switch to AUDIT role")
        table.add_row("/vibe", "Switch to VIBE role")
        table.add_row("────────────────", "────────────────────────────────────────")
        table.add_row("/status", "System diagnostic check")
        table.add_row("/model", "Display active LLM config")
        table.add_row("/clear", "Clear screen and reset context")
        table.add_row("/help", "Show this manual")
        table.add_row("exit, quit", "Shutdown the AI agent")
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")

    def _handle_interaction(self, user_input: str):
        """Handle turn. Restored for full observability and reasoning support."""
        if self.agent.auto_mode:
            self.console.print(Panel(f"[bold green]Mission Initiated:[/bold green] {user_input}", border_style="success"))
            
            try:
                # We use the robust _stream_response logic for the autonomous loop too
                # This ensures <think> tags are handled and output is visible
                def hud_status(msg):
                    # We print status updates on a new line to avoid interfering with stream
                    if "Step" in msg or "Executing" in msg:
                        self.console.print(f"[dim] {msg}[/dim]")

                # Run the loop
                for chunk in self.agent.run_autonomous_loop(user_input, status_callback=hud_status):
                    # We can't use _stream_response directly on a generator of mixed chunks easily,
                    # so we'll do a simplified version here that handles the yielding.
                    if chunk.startswith("\n\n[bold cyan]─── Observation"):
                        self.console.print(chunk)
                    else:
                        # For regular LLM text, we handle thinking tags
                        self.console.print(chunk, end="")
            except KeyboardInterrupt:
                self.agent.stop_signal = True
                self.console.print("\n[warning]Force Stop engaged.[/warning]")
            except Exception as e:
                self.console.print(f"\n[error]Sentinel Critical Breach:[/error] {str(e)}")
            self.console.print()
        else:
            response_text = self._stream_response(self.agent.chat(user_input))
            self.console.print()
            commands = self.agent.extract_commands(response_text)
            for cmd in commands:
                self._prompt_and_execute(cmd)

    def _stream_response(self, text_generator: Generator[str, None, None]) -> str:
        """Stream text to the terminal, hiding <think> tags."""
        full_text = ""
        think_text = ""
        is_thinking = False
        buffer = ""
        self.console.print("\n[ronin.name]CLI AI Agent:[/ronin.name]")
        panel_width = min(42, self.console.width - 4)
        thinking_ui = Panel(Spinner("dots", text="Neural link initializing..."), border_style="dim", width=panel_width)
        live = Live(thinking_ui, refresh_per_second=15, console=self.console)
        live.start()
        
        try:
            for chunk in text_generator:
                buffer += chunk
                while True:
                    if not is_thinking:
                        start_idx = buffer.find("<think>")
                        if start_idx != -1:
                            full_text += buffer[:start_idx]
                            buffer = buffer[start_idx + 7:]
                            is_thinking = True
                            live.update(Panel(Spinner("dots", text="Neural link processing..."), border_style="dim", width=panel_width))
                            continue
                    else:
                        end_idx = buffer.find("</think>")
                        if end_idx != -1:
                            think_text += buffer[:end_idx]
                            buffer = buffer[end_idx + 8:]
                            is_thinking = False
                            continue
                    break
                    
                if not is_thinking:
                    potential_tag = False
                    for i in range(1, 8):
                        if buffer.endswith("<think>"[:i]):
                            potential_tag = True
                            break
                    if not potential_tag:
                        full_text += buffer
                        buffer = ""
                        if full_text.strip():
                            display_text = full_text
                            lines = full_text.split('\n')
                            if len(lines) > 30:
                                display_text = "...\n" + "\n".join(lines[-30:])
                            live.update(Markdown(display_text))
                else:
                    potential_tag = False
                    for i in range(1, 9):
                        if buffer.endswith("</think>"[:i]):
                            potential_tag = True
                            break
                    if not potential_tag:
                        think_text += buffer
                        buffer = ""
                        
            if not is_thinking and buffer:
                full_text += buffer
                if full_text.strip():
                    live.update(Markdown(full_text))
        finally:
            live.stop()

        if think_text.strip():
            tokens = len(think_text.strip().split())
            self.console.print(f"[dim italic]↳ Analysis complete (~{tokens} tokens).[/dim italic]")
        return full_text

    def _prompt_and_execute(self, cmd_info: dict):
        """Ask user to confirm execution and run."""
        executor = cmd_info["executor"]
        code = cmd_info["code"]
        self.console.print(Panel(code, title=f"Action ({executor.upper()})", border_style="warning"))
        if Confirm.ask(f"[warning]Execute this {executor} code?[/warning]", default=True):
            with self.console.status(f"[bold green]Running...", spinner="dots"):
                if executor == "powershell": result = self.agent.execute_powershell(code)
                elif executor == "bash": result = self.agent.execute_bash(code)
                elif executor == "vbox": result = self.agent.execute_vbox(code)
                else: result = self.agent.execute_python(code)
            if result.success:
                self.console.print("[success]Success[/success]")
                out = result.stdout.strip()
                if len(out) > 1000: out = out[:1000] + "..."
                if out: self.console.print(out)
            else:
                self.console.print(f"[error]Failed ({result.exit_code})[/error]")
                if result.stderr: self.console.print(result.stderr.strip())
                self._stream_response(self.agent.analyze_result(code, result))
        self.console.print()
