"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘              RONIN-V â€” Sentinel TUI                      â•‘
â•‘       High-Stability Executive Interface                  â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
"""
import os
import sys
import time
import re
from typing import Optional, List, Dict

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.columns import Columns

from .themes import CYBERPUNK_THEME, BANNER, MINI_BANNER

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.styles import Style as PtStyle
    from prompt_toolkit.cursor_shapes import CursorShape
    HAS_PT = True
except (ImportError, Exception):
    HAS_PT = False

class SentinelStage:
    def __init__(self):
        self.reasoning = ""
        self.status = "Initializing..."
        self.executor = ""
        self.command = ""
        self.output = ""
        self.step = 1

    def __rich__(self) -> Group:
        status_line = Columns([
            Text(f"â–½ PHASE {self.step}", style="bold #ff003c"),
            Text(f"â–½ STATUS: {self.status}", style="italic dim"),
        ], expand=True)

        clean_reasoning = re.sub(r"<think>.*?</think>", "", self.reasoning, flags=re.DOTALL)
        reasoning_display = Panel(
            Markdown(clean_reasoning if clean_reasoning.strip() else "..."),
            title="[bold white]NEURAL ANALYSIS[/bold white]",
            border_style="#ff003c",
            padding=(1, 2)
        )
        elements = [status_line, reasoning_display]
        if self.command:
            syntax = Syntax(self.command, self.executor if self.executor != "vbox" else "bash", theme="monokai")
            elements.append(Panel(syntax, title=f"[bold cyan]EXECUTING: {self.executor.upper()}[/bold cyan]", border_style="cyan"))
        if self.output:
            elements.append(Panel(Text.from_markup(self.output) if "[" in self.output else Text(self.output), title="[bold green]OBSERVATION[/bold green]", border_style="green"))
        return Group(*elements)

class RoninSentinelUI:
    def __init__(self, agent):
        self.agent = agent
        self.console = Console(theme=CYBERPUNK_THEME)
        self.session = None
        if HAS_PT:
            try:
                self.session = PromptSession(
                    history=FileHistory(".ronin_history"),
                    style=PtStyle([("prompt", "#ff003c bold"), ("context", "#880000"), ("input", "#ffffff")])
                )
            except Exception:
                self.session = None

    def clear(self):
        self.console.clear()
        self.console.print(BANNER)

    def print_status(self):
        status = self.agent.check_systems()
        vm_name = self.agent.linked_vm['name'] if self.agent.linked_vm else "NONE"
        grid = Columns([
            f"âœ» [bold]GPU:[/bold] {'[green]ON[/green]' if status.get('compute', {}).get('gpu') else '[dim]OFF[/dim]'}",
            f"âœ» [bold]MODEL:[/bold] [cyan]{self.agent.llm.model_name}[/cyan]",
            f"âœ» [bold]VM:[/bold] [bold cyan]{vm_name}[/bold cyan]",
            f"âœ» [bold]MODE:[/bold] {'[yellow]AUTO[/yellow]' if self.agent.auto_mode else '[white]MANUAL[/white]'}"
        ], equal=True, expand=True)
        self.console.print(Panel(grid, title="[system.status]SYSTEM TELEMETRY[/system.status]", border_style="system.status"))
        self.console.print("\n")

    def run(self):
        self.clear()
        with self.console.status("[bold #ff003c]Engaging Neural Link...", spinner="bouncingBar"):
            self.agent.llm.preload_model()
        self.print_status()

        while True:
            try:
                ctx = self.agent.linked_vm["name"] if self.agent.linked_vm else "sentinel"
                role_tag = f"({self.agent.current_role.split(' ')[0]})" if self.agent.current_role != "DEFAULT" else ""
                
                if self.session:
                    user_input = self.session.prompt(
                        [("class:prompt", f"ronin{role_tag}"), ("class:context", f"/{ctx}"), ("class:prompt", " > ")],
                        cursor=CursorShape.BLINKING_BEAM
                    )
                else:
                    user_input = input(f"ronin{role_tag}/{ctx} > ")

                if not user_input.strip(): continue
                if user_input.lower() in ['exit', 'quit', '/exit']: break
                if user_input.startswith("/"):
                    self._handle_slash_command(user_input)
                    continue
                self._mission_loop(user_input)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self.console.print(f"[bold red]ERROR:[/bold red] {e}")

    def _handle_slash_command(self, cmd: str):
        parts = cmd.strip().split()
        base_cmd = parts[0].lower()

        if base_cmd == "/auto":
            self.agent.auto_mode = True
            self.console.print("[success]* Autonomous Mode ENGAGED.[/success]")
        elif base_cmd == "/manual":
            self.agent.auto_mode = False
            self.console.print("[info]* Manual Override ACTIVE.[/info]")
        elif base_cmd == "/bridge":
            self.console.print(Panel(self.agent.setup_neural_bridge(), title="Neural Bridge Setup", border_style="cyan"))
        elif base_cmd == "/status":
            self.print_status()
        elif base_cmd == "/clear":
            self.agent.clear_memory()
            self.clear()
            self.print_status()
            self.console.print("[info]* Terminal and Session Memory CLEARED.[/info]")
        elif base_cmd == "/suggest":
            self.console.print("[info]* Analyzing context for suggestions...[/info]")
            self._mission_loop("/suggest")
        elif base_cmd in ["/recon", "/audit", "/vibe"]:
            role = base_cmd[1:]
            self.agent.set_role(role)
            self.console.print(f"[success]* Specialized Role '{role.upper()}' ACTIVATED.[/success]")
        elif base_cmd == "/link":
            if len(parts) >= 4:
                name, user, passwd = parts[1], parts[2], parts[3]
                if self.agent.vbox_executor.test_connection(name, user, passwd):
                    self.agent.linked_vm = {"name": name, "user": user, "pass": passwd}
                    self.console.print(f"[success]* Master VM Link established to {name}[/success]")
                else:
                    self.console.print(f"[error]! Failed to link to VM {name}. Check credentials or ensure it is running.[/error]")
            else:
                self.console.print("[warning]! Usage: /link <vm_name> <username> <password>[/warning]")
        elif base_cmd == "/help":
            help_text = """
[bold cyan]Tactical Command Matrix[/bold cyan]
/auto       - Engage Autonomous Mode (Zero-Prompt execution)
/manual     - Return to Manual Authorization mode
/bridge     - Automate Neural Bridge configuration
/link       - /link <name> <user> <pass> (Establish VM Control)
/status     - Comprehensive Neural & Environment diagnostics
/suggest    - Generate AI-driven next steps for current state
/recon      - Specialize agent for Reconnaissance missions
/audit      - Specialize agent for Vulnerability Auditing
/vibe       - Specialize agent for Generation & Scaffolding
/clear      - Purge terminal and reset short-term session RAM
/help       - Display this help menu
/exit       - Safely terminate the neural link
            """
            self.console.print(Panel(help_text, border_style="cyan"))
        else:
            self.console.print(f"[warning]! Unknown command: {cmd}. Type /help for a list of commands.[/warning]")

    def _mission_loop(self, user_input: str):
        stage = SentinelStage()
        current_prompt = user_input
        while True:
            stage.reasoning = ""
            stage.status = "Analyzing tactical data..."
            stage.command = ""
            stage.output = ""
            
            with Live(stage, console=self.console, refresh_per_second=10) as live:
                try:
                    if current_prompt == "/suggest":
                        stream = self.agent.suggest_next_steps()
                    else:
                        stream = self.agent.chat(current_prompt)
                        
                    for chunk in stream:
                        stage.reasoning += chunk
                        live.update(stage)
                except Exception as e:
                    stage.output = f"[error]LLM Stream Error: {e}[/error]"
                    live.update(stage)
                    break
                    
                commands = self.agent.extract_commands(stage.reasoning)
                if not commands:
                    stage.status = "Mission Complete."
                    live.update(stage)
                    break
                for cmd in commands:
                    if cmd["executor"] == "complete_task":
                        stage.status = "Objective Secured."
                        stage.output = f"[bold green]âœ“ {cmd['code']}[/bold green]"
                        live.update(stage)
                        return
                    stage.executor = cmd["executor"]
                    stage.command = cmd["code"]
                    stage.status = f"Executing on {cmd['executor']}..."
                    live.update(stage)
                    
                    if not self.agent.auto_mode:
                        live.stop()
                        self.console.print("\n")
                        confirm = ""
                        if self.session:
                            confirm = self.session.prompt("Confirm Action? (y/N) > ").lower().strip()
                        else:
                            confirm = input("Confirm Action? (y/N) > ").lower().strip()
                            
                        if confirm != 'y':
                            self.console.print("[warning]! Action cancelled by operator.[/warning]")
                            return
                        live.start()

                    result = self.agent.execute_proposed_command(cmd)
                    stage.output = (result.stdout + result.stderr).strip()[:2000]
                    stage.status = "Observation phase..."
                    live.update(stage)
                    current_prompt = f"OBSERVATION: {result.stdout[:1000]}\nProceed."
                    stage.step += 1
            if not self.agent.auto_mode: break
