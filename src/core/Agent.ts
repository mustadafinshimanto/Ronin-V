import * as os from 'os';
import { RoninLLM } from './LLM.js';
import { PowerShellExecutor, BashExecutor, VBoxExecutor, PythonExecutor, CommandResult } from '../executors/Executors.js';
import { RONIN_SYSTEM_PROMPT } from './Prompts.js';
import { ConfigLoader, RoninConfig } from './Config.js';

export class RoninAgent {
    public llm: RoninLLM;
    public psExecutor: PowerShellExecutor;
    public bashExecutor: BashExecutor;
    public vboxExecutor: VBoxExecutor;
    public pyExecutor: PythonExecutor;
    public config: RoninConfig;

    public linkedVm: { name: string, user: string, pass: string } | null = null;
    public autoMode: boolean;
    public currentRole: string = "DEFAULT";
    public targetEnv: 'host' | 'vm' = 'host';
    public memory: any[] = [];
    public stopSignal: boolean = false;

    constructor() {
        this.config = ConfigLoader.load();
        this.llm = new RoninLLM();
        this.psExecutor = new PowerShellExecutor();
        this.bashExecutor = new BashExecutor();
        this.vboxExecutor = new VBoxExecutor();
        this.pyExecutor = new PythonExecutor();
        this.autoMode = this.config.agent.auto_mode;
    }

    async init() {
        await this.autoLinkKali();
    }

    async autoLinkKali() {
        try {
            const vms = await this.vboxExecutor.listVMs();
            const { vm_user, vm_pass } = this.config.agent;
            for (const vm of vms) {
                const name = vm.name.toLowerCase();
                if (name.includes('kali') || name.includes('linux')) {
                    if (await this.vboxExecutor.testConnection(vm.name, vm_user, vm_pass)) {
                        this.linkedVm = { name: vm.name, user: vm_user, pass: vm_pass };
                        break;
                    }
                }
            }
        } catch (e) {}
    }

    async checkSystems(): Promise<any> {
        let gpu = false;
        try {
            const cmd = 'nvidia-smi';
            const res = os.platform() === 'win32' 
                ? await this.psExecutor.execute(cmd, 2000)
                : await this.bashExecutor.execute(cmd, 2000);
            if (res.success) gpu = true;
        } catch {}

        return {
            os: os.platform(),
            ollamaConnected: await this.llm.checkConnection(),
            model: this.llm.modelName,
            gpu: gpu
        };
    }

    setRole(role: string) {
        if (role === 'recon') this.currentRole = "RECON MODE. Phase: Discovery.";
        else if (role === 'audit') this.currentRole = "AUDIT MODE. Phase: Analysis.";
        else this.currentRole = "DEFAULT";
    }

    async *chat(userInput: string, signal?: AbortSignal): AsyncGenerator<string, void, unknown> {
        this.memory.push({ role: 'user', content: userInput });
        const shell = os.platform() === 'win32' ? 'PowerShell' : 'Bash';
        const { vm_user, vm_pass } = this.config.agent;
        const sysPrompt = RONIN_SYSTEM_PROMPT(os.platform(), shell, vm_user, vm_pass);
        const envPrompt = this.targetEnv === 'vm' ? `\n\n[CRITICAL: YOU MUST EXECUTE ALL ACTIONS IN THE GUEST VM USING \\\`\\\`\\\`vbox\\\`\\\`\\\` OR \\\`\\\`\\\`bash\\\`\\\`\\\`]` : `\n\n[CRITICAL: YOU MUST EXECUTE ALL ACTIONS ON THE LOCAL WINDOWS HOST USING \\\`\\\`\\\`powershell\\\`\\\`\\\`]`;
        const messages = [{ role: 'system', content: sysPrompt + envPrompt + (this.currentRole !== 'DEFAULT' ? `\n\nROLE: ${this.currentRole}` : '') }, ...this.memory];
        let fullResponse = "";
        for await (const chunk of this.llm.chat(messages, signal)) {
            fullResponse += chunk;
            yield chunk;
        }
        this.memory.push({ role: 'assistant', content: fullResponse });
    }

    extractCommands(response: string): { executor: string, code: string }[] {
        const commands: { executor: string, code: string }[] = [];
        
        // Primary: Triple backtick blocks
        const regex = /```(powershell|ps|python|vbox|bash|sh)\s*([\s\S]*?)```/gi;
        let match;
        while ((match = regex.exec(response)) !== null) {
            let exec = match[1].toLowerCase();
            if (exec === 'ps') exec = 'powershell';
            if (exec === 'sh') exec = 'bash';
            const code = match[2].trim();
            if (code) {
                commands.push({ executor: exec, code });
            }
        }

        // Fallback: Catch executor labels followed by commands (e.g., "VBox: 1. sudo apt update")
        if (commands.length === 0) {
            const lines = response.split('\n');
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim().toLowerCase();
                const cleanLine = line.replace(/[:\-]/g, '').trim();
                
                if (['vbox', 'powershell', 'python', 'bash'].includes(cleanLine)) {
                    let code = "";
                    for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                        const nextLine = lines[j].trim();
                        if (!nextLine) continue;
                        
                        // Handle numbered list or naked command
                        const cmdMatch = nextLine.match(/^(?:\d+[\.\)]?\s+)?(.*)/);
                        if (cmdMatch && cmdMatch[1].length > 2) {
                            code = cmdMatch[1];
                            // If it looks like another executor label, stop
                            if (['vbox', 'powershell', 'python', 'bash'].includes(code.toLowerCase().replace(/[:\-]/g, ''))) break;
                            break;
                        }
                    }
                    if (code && !code.toLowerCase().includes('complete_task')) {
                        commands.push({ executor: cleanLine, code });
                        break; 
                    }
                }
            }
        }

        // Environment post-processing: Lock the executor to the current targetEnv
        for (const cmd of commands) {
            if (this.targetEnv === 'vm' && this.linkedVm) {
                // If targeting VM, force powershell/bash/sh to vbox
                if (['powershell', 'ps', 'bash', 'sh'].includes(cmd.executor)) {
                    cmd.executor = 'vbox';
                }
            } else if (this.targetEnv === 'host') {
                // If targeting host, force bash/sh to powershell on Windows
                if (['bash', 'sh'].includes(cmd.executor) && os.platform() === 'win32') {
                    cmd.executor = 'powershell';
                }
            }
        }

        if (commands.length === 0 && (response.includes('✅') || response.toLowerCase().includes('complete_task'))) {
            commands.push({ executor: 'complete_task', code: 'Mission Secured.' });
        }
        return commands;
    }
async executeCommand(cmd: { executor: string, code: string }, signal?: AbortSignal, onData?: (data: string) => void): Promise<CommandResult> {
    let code = cmd.code;

    // Safety: Prevent bash syntax errors from placeholders like <BSSID>
    if (code.includes('<') && code.includes('>')) {
        return { command: code, exitCode: -1, stdout: '', stderr: `COMMAND REJECTED: Contains placeholders like <...>. You MUST run discovery first to find actual targets.`, success: false, timedOut: false };
    }

    // Auto-fix for sudo in VM:
    if (cmd.executor === 'vbox' && this.linkedVm) {
        const rootCommands = ['wifite', 'apt', 'airmon-ng', 'airodump-ng', 'aireplay-ng', 'iwconfig', 'ifconfig', 'iw', 'netdiscover', 'hcp'];
        const needsSudo = rootCommands.some(c => code.trim().startsWith(c) || code.includes(` ${c} `));
        const alreadyHasSudo = code.includes('sudo ');
        const alreadyHasPipe = code.includes('| sudo -S');

        if ((needsSudo || alreadyHasSudo) && !alreadyHasPipe) {
            const sudoFix = `echo ${this.linkedVm.pass} | sudo -S -p '' `;
            if (code.startsWith('sudo ')) {
                code = code.replace(/^sudo /, sudoFix);
            } else {
                // Prepend sudo fix to the whole command if it needs it but doesn't have it
                code = sudoFix + code;
            }
        }
    }

        // Force non-interactive for VM/Bash commands
        if (cmd.executor === 'vbox' || cmd.executor === 'bash') {
            code = `export DEBIAN_FRONTEND=noninteractive; ${code}`;
        }

        let result: CommandResult;
        if (cmd.executor === 'powershell') result = await this.psExecutor.execute(code, 60000, signal, onData);
        else if (cmd.executor === 'bash') result = await this.bashExecutor.execute(code, 60000, signal, onData);
        else if (cmd.executor === 'python') result = await this.pyExecutor.execute(code, 60000, signal, onData);
        else if (cmd.executor === 'vbox') {
            if (!this.linkedVm) return { command: code, exitCode: -1, stdout: '', stderr: `No VirtualBox VM linked.`, success: false, timedOut: false };
            result = await this.vboxExecutor.execute(this.linkedVm.name, this.linkedVm.user, this.linkedVm.pass, code, 60000, signal, onData);
        } else {
            return { command: code, exitCode: -1, stdout: '', stderr: `Unknown executor: ${cmd.executor}`, success: false, timedOut: false };
        }

        // Sanitize output: Remove "sudo password" prompts that can confuse the LLM
        const sanitize = (text: string) => text.replace(/\[sudo\] password for .+: ?/g, '').trim();
        result.stdout = sanitize(result.stdout);
        result.stderr = sanitize(result.stderr);

        return result;
    }
}
