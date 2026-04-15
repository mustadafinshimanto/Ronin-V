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
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from ui.themes import CYBERPUNK_THEME, BANNER
from core.agent import RoninAgent
from executors.powershell import CommandResult


class RoninTerminal:
    """
    Main interactive terminal UI for Ronin-V.
    """

    def __init__(self, agent: RoninAgent, config: dict):
        self.agent = agent
        self.console = Console(theme=CYBERPUNK_THEME)
        self.config = config.get("ui", {})
        
        # Setup input session with history
        # Setup keys for mode switching and navigation
        self.kb = KeyBindings()
        
        @self.kb.add('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')
            
        @self.kb.add('c-a')
        def _(event):
            self.agent.auto_mode = not self.agent.auto_mode
            self.console.print(f"\n[info]Mode switched to {'AUTO' if self.agent.auto_mode else 'MANUAL'}[/info]")

        # Setup input session with history and UI enhancements
        style = Style.from_dict({
            'prompt': '#ff2a2a bold',
            'bottom-toolbar': 'bg:#1a0505 #ff4a4a',
            'rprompt': '#888888',
        })
        
        # Setup auto-completion and auto-suggestions (ghost text)
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
        
        info_lines = [
            f"[*] Ollama connection: {'[success]ONLINE[/success]' if status['ollama_connected'] else '[error]OFFLINE[/error]'}",
            f"[*] PowerShell API:   {'[success]ONLINE[/success]' if status['powershell_ok'] else '[error]ERROR[/error]'}",
            f"[*] Python Executor:  {'[success]ONLINE[/success]' if status['python_ok'] else '[error]ERROR[/error]'}",
            f"[*] Kali VM Link:     {'[success]CONNECTED[/success]' if self.agent.linked_vm else '[dim]DISCONNECTED[/dim]'}",
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
                # Get input using prompt_toolkit for history/navigation
                # Get input using prompt_toolkit for history/navigation/toolbar
                user_input = self.session.prompt("λ ronin > ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "q", "/exit"]:
                    break
                elif user_input.lower() in ["clear", "cls", "/clear", "/cls"]:
                    self.console.clear()
                    self.agent.memory.start_session(self.agent.session_id) # Reset internal short-term memory
                    self.console.print("[info]Terminal cleared and context reset.[/info]\n")
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
                    self.console.print(Panel("[success]AUTONOMOUS ENGINE ENGAGED[/success]\nAgent will now execute sequences until objective is marked complete (✅).", border_style="success"))
                    continue
                elif user_input.lower() == "/manual":
                    self.agent.auto_mode = False
                    self.console.print(Panel("[info]MANUAL OVERRIDE ENGAGED[/info]\nAll commands will require explicit [y/n] authorization.", border_style="info"))
                    continue
                elif user_input.lower() in ["/recon", "/audit", "/vibe"]:
                    role = user_input[1:].lower()
                    self.agent.set_role(role)
                    self.console.print(Panel(f"Agent role specialized for: [bold white]{role.upper()}[/bold white]\nPrompt and priority logic synchronized.", border_style="panel.border"))
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
                            self.console.print(Panel(f"[success]Master Link established with {vm_name}[/success]\nRonin-V can now execute commands directly on this Kali VM.", border_style="success"))
                        else:
                            self.console.print(Panel(f"[error]Failed to link with {vm_name}[/error]\nCheck if Guest Additions are installed and credentials are correct.", border_style="error"))
                    continue

                elif user_input.lower() == "/suggest":
                    self.console.print(Panel("[bold cyan]Analyzing mission telemetry... generating next tactical steps.[/bold cyan]", border_style="cyan"))
                    response_text = self._stream_response(self.agent.suggest_next_steps())
                    self.console.print()
                    continue

                elif user_input.lower() == "/bridge":
                    self.console.print(Panel("[bold cyan]Neural Bridge Architect rising...[/bold cyan]", border_style="cyan"))
                    result = self.agent.setup_neural_bridge()
                    self.console.print(result)
                    self.console.print()
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
        from rich.table import Table
        
        # Responsive table: hide padding if narrow
        table = Table(
            title="Ronin-V Elite CLI Commands", 
            border_style="panel.border",
            collapse_padding=True if self.console.width < 50 else False
        )
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        table.add_row("/auto", "Engage Autonomous Engine (Zero-Prompt Mode)")
        table.add_row("/manual", "Override to Manual Authorization mode")
        table.add_row("/bridge", "Automate Master-Guest Bridge Setup")
        table.add_row("/link", "Connect to a VirtualBox VM (Kali/Linux)")
        table.add_row("/recon", "Switch to RECON Sub-Agent (Discovery focus)")
        table.add_row("/audit", "Switch to AUDIT Sub-Agent (Code scanning focus)")
        table.add_row("/vibe", "Switch to VIBE Sub-Agent (Scaffolding focus)")
        table.add_row("────────────────", "────────────────────────────────────────")
        table.add_row("/status", "System diagnostic & Environment check")
        table.add_row("/model", "Display active LLM configuration")
        table.add_row("/clear, cls", "Clear screen and reset session RAM")
        table.add_row("/help", "Show this mastery manual")
        table.add_row("exit, quit", "Shutdown the AI agent")

        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")

    def _handle_interaction(self, user_input: str):
        """Handle interaction turn. Uses autonomous loop if auto_mode is ON."""
        self.console.print()
        
        if self.agent.auto_mode:
            # Autonomous Path: Run Plan-Act-Observe loop
            self.console.print("[ronin.name]CLI AI Agent [AUTO]:[/ronin.name]")
            
            # Responsive sizing: don't exceed console width
            panel_width = min(60, self.console.width - 4)
            
            # Use a Group to combine the Thought Panel (with Spinner) and the actual streamed Output
            status_panel = Panel(Spinner("aesthetic", text="Agent initializing autonomous sequence..."), border_style="cyan", width=panel_width)
            live = Live(status_panel, refresh_per_second=15, console=self.console)
            live.start()
            
            def update_status(msg):
                panel = Panel(Spinner("aesthetic", text=msg), border_style="cyan", title="Autonomous Engine", width=panel_width)
                # Combine the thinking panel with whatever response has been collected so far
                if response_text.strip():
                    live.update(Group(panel, Markdown(response_text)))
                else:
                    live.update(panel)
            
            # Execute the loop
            response_text = ""
            try:
                for chunk in self.agent.run_autonomous_loop(user_input, status_callback=update_status):
                    response_text += chunk
                    # Update live display with new text segment
                    update_status(f"Step {self.agent.max_steps}: Processing...") # Re-trigger layout refresh
            except KeyboardInterrupt:
                self.agent.stop_signal = True
                self.console.print("\n[warning]Force Stop: Autonomous loop terminated.[/warning]")
            finally:
                live.stop()
                
            self.console.print()
        else:
            # Manual Path: Normal chat + permission prompts
            response_text = self._stream_response(self.agent.chat(user_input))
            self.console.print()

            commands = self.agent.extract_commands(response_text)
            for cmd in commands:
                self._prompt_and_execute(cmd)

    def _stream_response(self, text_generator: Generator[str, None, None]) -> str:
        """Stream text to the terminal and return the full string, hiding <think> tags."""
        full_text = ""
        think_text = ""
        is_thinking = False
        has_started_output = False
        buffer = ""
        
        self.console.print("\n[ronin.name]CLI AI Agent:[/ronin.name]")
        
        # Responsive sizing: don't exceed console width
        panel_width = min(42, self.console.width - 4)
        
        # Immediately display a moving aesthetic spinner while waiting for the model
        thinking_ui = Panel(Spinner("aesthetic", text="Neural link initializing..."), border_style="dim", width=panel_width)
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
                            live.update(Panel(Spinner("aesthetic", text="Neural link processing intents..."), border_style="dim", width=46))
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
                    # Check if the end of the buffer might be part of a "<think>" tag
                    potential_tag = False
                    for i in range(1, 8):
                        if buffer.endswith("<think>"[:i]):
                            potential_tag = True
                            break
                    if not potential_tag:
                        full_text += buffer
                        buffer = ""
                        # Only transition from spinner to markdown if actual content starts streaming
                        if full_text.strip():
                            has_started_output = True
                            
                            # SMART SCROLLER: Only show the last N lines if it gets too big
                            display_text = full_text
                            lines = full_text.split('\n')
                            if len(lines) > 30:
                                display_text = "...\n" + "\n".join(lines[-30:])
                                
                            live.update(Markdown(display_text))
                else:
                    # Check for partial "</think>"
                    potential_tag = False
                    for i in range(1, 9):
                        if buffer.endswith("</think>"[:i]):
                            potential_tag = True
                            break
                    if not potential_tag:
                        think_text += buffer
                        buffer = ""
                        
            # Flush any remaining buffer when stream completes
            if not is_thinking and buffer:
                full_text += buffer
                if full_text.strip():
                    live.update(Markdown(full_text))
                    
        finally:
            live.stop()

        if think_text.strip():
            # Create a minimized visualization of the thought process
            tokens = len(think_text.strip().split())
            self.console.print(f"[dim italic]↳ Internal analysis completed (~{tokens} thought tokens).[/dim italic]")

        return full_text

    def _prompt_and_execute(self, cmd_info: dict):
        """Ask user to confirm execution, then run if approved."""
        executor = cmd_info["executor"]
        code = cmd_info["code"]

        self.console.print(Panel(
            f"[{'cyan' if executor == 'powershell' else 'yellow'}]{code}[/]",
            title=f"Proposed Action ({executor.upper()})",
            border_style="warning"
        ))

        # Ask for confirmation
        should_run = Confirm.ask(f"[warning]Execute this {executor} code?[/warning]", default=True)
        
        if not should_run:
            self.console.print("[info]Skipped execution.[/info]\n")
            return

        # Execute
        with self.console.status(f"[bold green]Executing {executor} command...", spinner="dots"):
            if executor == "powershell":
                result = self.agent.execute_powershell(code)
            elif executor == "vbox":
                result = self.agent.execute_vbox(code)
            else:
                result = self.agent.execute_python(code)

        # Show result
        if result.success:
            self.console.print("[success]Execution successful[/success]")
            # Print output truncated if too long
            out = result.stdout.strip()
            if len(out) > 1000:
                out = out[:1000] + "\n... [Output truncated]"
            if out:
                self.console.print(f"[{'cyan' if executor == 'powershell' else 'yellow'}]{out}[/]")
        else:
            self.console.print(f"[error]Execution failed (Exit Code: {result.exit_code})[/error]")
            if result.stderr:
                self.console.print(f"[error]{result.stderr.strip()}[/error]")

        # Handle Analysis Automatically
        if not result.success:
            self.console.print("[warning]Automatically analyzing failure context...[/warning]\n")
            self._stream_response(self.agent.analyze_result(code, result))
            self.console.print()
        else:
            self.console.print()
