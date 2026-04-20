import { execa } from 'execa';
import * as fs from 'fs';
import { ConfigLoader, RoninConfig } from '../core/Config.js';

export interface CommandResult {
    command: string;
    exitCode: number;
    stdout: string;
    stderr: string;
    success: boolean;
    timedOut: boolean;
}

export type DataCallback = (data: string) => void;

export class PowerShellExecutor {
    private config: RoninConfig['executors']['powershell'];

    constructor() {
        this.config = ConfigLoader.load().executors.powershell;
    }

    async execute(command: string, timeoutMs?: number, signal?: AbortSignal, onData?: DataCallback): Promise<CommandResult> {
        if (!this.config.enabled) {
            return { command, exitCode: -1, stdout: '', stderr: 'PowerShell executor is disabled.', success: false, timedOut: false };
        }

        const timeout = timeoutMs ?? (this.config.timeout * 1000);
        
        try {
            const child = execa(this.config.shell || 'powershell.exe', [
                '-NoProfile', '-NonInteractive', '-Command', command
            ], { timeout, reject: false, cancelSignal: signal });

            if (onData) {
                child.stdout?.on('data', (chunk) => onData(chunk.toString()));
                child.stderr?.on('data', (chunk) => onData(chunk.toString()));
            }

            const { stdout, stderr, exitCode } = await child;
            
            return { 
                command, 
                exitCode: exitCode ?? -1, 
                stdout: stdout, 
                stderr: stderr, 
                success: exitCode === 0, 
                timedOut: false 
            };
        } catch (e: any) {
            const timedOut = e.timedOut || (e.message && e.message.includes('timed out'));
            return { 
                command, 
                exitCode: -1, 
                stdout: '', 
                stderr: e.isCanceled ? 'Aborted' : e.message, 
                success: false, 
                timedOut: !!timedOut 
            };
        }
    }
}

export class BashExecutor {
    async execute(command: string, timeoutMs: number = 60000, signal?: AbortSignal, onData?: DataCallback): Promise<CommandResult> {
        try {
            const child = execa('bash', ['-c', command], { timeout: timeoutMs, reject: false, cancelSignal: signal });
            
            if (onData) {
                child.stdout?.on('data', (chunk) => onData(chunk.toString()));
                child.stderr?.on('data', (chunk) => onData(chunk.toString()));
            }

            const { stdout, stderr, exitCode } = await child;
            return { command, exitCode: exitCode ?? -1, stdout: stdout, stderr: stderr, success: exitCode === 0, timedOut: false };
        } catch (e: any) {
            const timedOut = e.timedOut || (e.message && e.message.includes('timed out'));
            return { command, exitCode: -1, stdout: '', stderr: e.isCanceled ? 'Aborted' : e.message, success: false, timedOut: !!timedOut };
        }
    }
}

export class PythonExecutor {
    private config: RoninConfig['executors']['python'];

    constructor() {
        this.config = ConfigLoader.load().executors.python;
    }

    async execute(code: string, timeoutMs?: number, signal?: AbortSignal, onData?: DataCallback): Promise<CommandResult> {
        if (!this.config.enabled) {
            return { command: 'python-code', exitCode: -1, stdout: '', stderr: 'Python executor is disabled.', success: false, timedOut: false };
        }

        const timeout = timeoutMs ?? (this.config.timeout * 1000);

        try {
            const child = execa('python', ['-c', code], { timeout, reject: false, cancelSignal: signal });
            
            if (onData) {
                child.stdout?.on('data', (chunk) => onData(chunk.toString()));
                child.stderr?.on('data', (chunk) => onData(chunk.toString()));
            }

            const { stdout, stderr, exitCode } = await child;
            return { command: 'python-code', exitCode: exitCode ?? -1, stdout: stdout, stderr: stderr, success: exitCode === 0, timedOut: false };
        } catch (e: any) {
            const timedOut = e.timedOut || (e.message && e.message.includes('timed out'));
            return { command: 'python-code', exitCode: -1, stdout: '', stderr: e.isCanceled ? 'Aborted' : e.message, success: false, timedOut: !!timedOut };
        }
    }
}

export class VBoxExecutor {
    private vboxPath: string;
    private config: { enabled: boolean; timeout: number; path?: string };

    constructor() {
        const fullConfig = ConfigLoader.load();
        this.config = fullConfig.executors.vbox || { enabled: true, timeout: 60 };
        
        this.vboxPath = this.config.path || 'C:\\Program Files\\Oracle\\VirtualBox\\VBoxManage.exe';
        if (!fs.existsSync(this.vboxPath)) this.vboxPath = 'VBoxManage';
    }

    async listVMs(): Promise<{name: string}[]> {
        try {
            const { stdout } = await execa(this.vboxPath, ['list', 'runningvms']);
            return stdout.split('\n').filter(l => l.includes('"')).map(l => ({ name: l.split('"')[1] }));
        } catch { return []; }
    }

    async testConnection(vmName: string, user: string, pass: string): Promise<boolean> {
        const res = await this.execute(vmName, user, pass, 'whoami', 15000);
        return res.success;
    }

    async execute(vmName: string, user: string, pass: string, command: string, timeoutMs?: number, signal?: AbortSignal, onData?: DataCallback): Promise<CommandResult> {
        if (this.config && !this.config.enabled) {
            return { command, exitCode: -1, stdout: '', stderr: 'VBox executor is disabled.', success: false, timedOut: false };
        }

        const timeout = timeoutMs ?? (this.config.timeout * 1000);

        try {
            const args = [
                'guestcontrol', vmName, 'run',
                '--username', user, '--password', pass,
                '--wait-stdout', '--wait-stderr',
                '--', '/bin/bash', '-c', command
            ];
            const child = execa(this.vboxPath, args, { timeout, reject: false, cancelSignal: signal });
            
            if (onData) {
                child.stdout?.on('data', (chunk) => onData(chunk.toString()));
                child.stderr?.on('data', (chunk) => onData(chunk.toString()));
            }

            const { stdout, stderr, exitCode } = await child;
            return { command, exitCode: exitCode ?? -1, stdout, stderr, success: exitCode === 0, timedOut: false };
        } catch (e: any) {
            const timedOut = e.timedOut || (e.message && e.message.includes('timed out'));
            return { command, exitCode: -1, stdout: '', stderr: e.isCanceled ? 'Aborted' : e.message, success: false, timedOut: !!timedOut };
        }
    }
}
