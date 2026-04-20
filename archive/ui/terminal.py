"""
                     RONIN-V — Terminal UI
            Fabric-CLI Integration • Pro Sequential Engine
"""
import sys
import time
import re
from typing import Generator

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax
from rich.columns import Columns

from prompt_toolkit import PromptSession
from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.history import FileHistory

# Fabric UI Bridge
from . import fabric_ui

class TacticalUI:
    """The 'Full Package' Sequential Card Engine with Fabric Aesthetics."""
    def __init__(self, console: Console):
        self.console = console
        
    def announce_mission(self, user_input: str):
        self.console.print("\n")
        self.console.print(Panel(
            Text.from_markup(f"[bold cyan]MISSION INITIATED:[/bold cyan] {user_input}"),
            border_style="cyan",
            padding=(1, 2)
        ))

    def render_reasoning(self, text: str, step: int):
        # Clean think tags
        if "<think>" in text:
            if "</think>" in text:
                text = re.sub(r"<think>.*?</think>", "[dim italic]↳ Neural Analysis Complete...[/dim italic]\n", text, flags=re.DOTALL)
            else:
                text = text.split("<think>")[0] + "\n[bold yellow]↳ Thinking...[/bold yellow]"
        
        panel = Panel(
            Markdown(text),
            title=f"[bold white]PHASE {step}: STRATEGY[/bold white]",
            border_style="yellow",
            padding=(1, 2)
        )
        return panel

    def render_action(self, executor: str, code: str):
        syntax = Syntax(code, executor if executor != "vbox" else "bash", theme="monokai", line_numbers=True)
        panel = Panel(
            syntax,
            title=f"[bold cyan]PROPOSED ACTION : {executor.upper()}[/bold cyan]",
            border_style="cyan",
            subtitle="[dim]Awaiting tactical authorization...[/dim]"
        )
        return panel

    def render_observation(self, observation: str, executor: str, exit_code: int):
        color = "green" if exit_code == 0 else "red"
        status = "SUCCESS" if exit_code == 0 else "FAILURE"
        
        clean_obs = observation.strip()
        if not clean_obs:
            clean_obs = "[italic dim]No output received from guest environment.[/italic dim]"
        elif len(clean_obs) > 2500:
            clean_obs = clean_obs[:2500] + "\n\n[dim italic]... (Remaining output truncated for brevity)[/dim italic]"
            
        panel = Panel(
            Text.from_markup(clean_obs) if "[" in clean_obs else Text(clean_obs),
            title=f"[bold {color}]OBSERVATION: {status} ({executor.upper()})[/bold {color}]",
            border_style=color,
            subtitle=f"[dim]Step Finalized | Exit Code: {exit_code}[/dim]",
            padding=(1, 2)
        )
        return panel

class RoninTerminal:
    def __init__(self, agent, config):
        self.agent = agent
        self.console = Console()
        self.config = config
        self.session = PromptSession(
            history=FileHistory(".ronin_history"),
            style=fabric_ui.FABRIC_STYLE
        )
        self.ui = TacticalUI(self.console)

    def print_banner(self):
        banner = r"""
 ██████╗  ██████╗ ███╗   ██╗██╗███╗   ██╗     ██╗   ██╗
 ██╔══██╗██╔═══██╗████╗  ██║██║████╗  ██║     ██║   ██║
 ██████╔╝██║   ██║██╔██╗ ██║██║██╔██╗ ██║     ██║   ██║
 ██╔══██╗██║   ██║██║╚██╗██║██║██║╚██╗██║  _  ╚██╗ ██╔╝
 ██║  ██║╚██████╔╝██║ ╚████║██║██║ ╚████║ ( )  ╚████╔╝ 
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝  V    ╚═══╝  
        """
        self.console.print(Text(banner, style="cyan"))
        self.console.print("[bold white]    >> VIBE SENTINEL v1.0.0 • FABRIC-ENGINE EDITION <<[/bold white]")
        self.console.print("[dim]    Built for Persistent Autonomous Penetration Testing[/dim]\n")

    def print_system_status(self, status: dict):
        vm_link_status = "[dim]OFFLINE[/dim]"
        if self.agent.linked_vm:
            vm_link_status = f"[success]CONNECTED[/success] ([bold cyan]{self.agent.linked_vm['name']}[/bold cyan])"

        info_lines = [
            f"[*] Ollama Core:    {'[success]ONLINE[/success]' if status['ollama_connected'] else '[error]OFFLINE[/error]'}",
            f"[*] GPU Accel:      {'[success]ACTIVE[/success]' if status.get('compute', {}).get('gpu') else '[dim]DISABLED[/dim]'}",
            f"[*] Operational Mode: {'[bold cyan]MANUAL[/bold cyan]' if not self.agent.auto_mode else '[bold yellow]AUTO[/bold yellow]'}",
            f"[*] Target VM Link: {vm_link_status}"
        ]
        self.console.print(Panel(
            Columns(info_lines, equal=True, expand=True),
            title="[bold cyan]Fabric Engine Status[/bold cyan]",
            border_style="cyan",
            expand=False
        ))

    def run_loop(self):
        self.console.clear()
        self.print_banner()
        
        with self.console.status("[bold cyan]Warming up neural engines...", spinner="bouncingBar"):
            self.agent.llm.preload_model()
            status = self.agent.check_systems()
            
        self.print_system_status(status)
        
        if not status["ollama_connected"]:
            fabric_ui.print_error("CRITICAL: Ollama connection failed.")
            sys.exit(1)

        print("\n")
        fabric_ui.print_info("Locked and loaded. Ready for mission assignment.", command="Sentinel")

        while True:
            try:
                user_input = self.session.prompt(
                    fabric_ui.get_prompt_text(context=self.agent.linked_vm["name"] if self.agent.linked_vm else "active"),
                    cursor=CursorShape.BLINKING_BEAM
                )
                
                if not user_input.strip(): continue
                if user_input.lower() in ['exit', 'quit']: break
                
                # Tactical Router: Force Host or VM execution
                if user_input.startswith("/host"):
                    user_input = f"{user_input[5:].strip()}\n[FORCE: MUST EXECUTE ON LOCAL HOST COMMANDS ONLY]"
                elif user_input.startswith("/vm") or user_input.startswith("/guest"):
                    user_input = f"{user_input[3:].strip()}\n[FORCE: MUST EXECUTE ON LINKED GUEST VM ONLY]"

                self._handle_interaction(user_input)

            except KeyboardInterrupt:
                fabric_ui.print_warning("\nMission Aborted by User. Safe exit.")
                break
            except Exception as e:
                fabric_ui.print_error(f"RUNTIME ERROR: {str(e)}")
                import traceback
                traceback.print_exc()

    def _handle_interaction(self, user_input: str):
        self.ui.announce_mission(user_input)
        
        current_prompt = user_input
        step_in_mission = 1
        
        while True:
            # Step 1: Reasoning & Proposals
            proposal_full_response = ""
            with Live(self.ui.render_reasoning("...", step_in_mission), console=self.console) as live:
                for chunk in self.agent.chat(current_prompt):
                    proposal_full_response += chunk
                    live.update(self.ui.render_reasoning(proposal_full_response, step_in_mission))
            
            # Step 2: Extraction
            found_commands = self.agent.extract_commands(proposal_full_response)
            
            if not found_commands:
                fabric_ui.print_done("Mission complete or awaiting manual override.")
                break
                
            # Step 3: Authorization Loop
            all_approved = True
            execution_results = []
            
            for cmd in found_commands:
                if cmd['executor'] == "complete_task":
                    fabric_ui.print_done(f"MISSION ACCOMPLISHED: {cmd['code']}")
                    return

                self.console.print(self.ui.render_action(cmd['executor'], cmd['code']))
                
                if not self.agent.auto_mode:
                    self.console.print("\n")
                    # Use plain string to avoid prompt_toolkit vs rich mismatch
                    confirm = self.session.prompt("Authorize execution? (y/N): ").strip().lower()
                    
                    if confirm != 'y':
                        fabric_ui.print_warning("Strategy rejected. Returning to tactical prompt.")
                        all_approved = False
                        break
                
                # Execution & Observation
                with self.console.status(f"[bold cyan]Deploying to {cmd['executor']}...", spinner="point"):
                    res = self.agent.execute_proposed_command(cmd)
                    execution_results.append(res)
                
                self.console.print(self.ui.render_observation(res.stdout + res.stderr, cmd['executor'], res.exit_code))
                self.console.print("\n")

            if not all_approved:
                break
            
            # Step 4: Continuity
            obs_text = "\n".join([f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}" for r in execution_results])
            current_prompt = f"OBSERVATIONS:\n{obs_text}\n\nAnalyze and provide the next step."
            step_in_mission += 1
