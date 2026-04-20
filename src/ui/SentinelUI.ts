import chalk from 'chalk';
import ora from 'ora';
import { input, confirm } from '@inquirer/prompts';
import { RoninAgent } from '../core/Agent.js';
import { CommandResult } from '../executors/Executors.js';
import cliMd from 'cli-markdown';

const BANNER = `
${chalk.hex('#ff003c').bold(' ██▀███   ▒█████   ███▄    █  ██▓ ███▄    █           ██▒   █▓')}
${chalk.hex('#ff003c').bold('▓██ ▒ ██▒▒██▒  ██▒ ██ ▀█   █ ▓██▒ ██ ▀█   █          ▓██░   █▒')}
${chalk.hex('#ff003c').bold('▓██ ░▄█ ▒▒██░  ██▒▓██  ▀█ ██▒▒██▒▓██  ▀█ ██▒          ▓██  █▒░')}
${chalk.hex('#ff003c').bold('▒██▀▀█▄  ▒██   ██░▓██▒  ▐▌██▒░██░▓██▒  ▐▌██▒           ▒██ █░░')}
${chalk.hex('#ff003c').bold('░██▓ ▒██▒░ ████▓▒░▒██░   ▓██░░██░▒██░   ▓██░            ▒▀█░  ')}
${chalk.hex('#ff003c').bold('░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░ ▒░   ▒ ▒ ░▓  ░ ▒░   ▒ ▒             ░ ▐░  ')}
${chalk.hex('#ff4a4a').bold('  >> TACTICAL AUTO-ENGINE v2.1.0 <<')}
`;

export class RoninSentinelUI {
    private agent: RoninAgent;

    constructor(agent: RoninAgent) {
        this.agent = agent;
    }

    clear() {
        console.clear();
        console.log(BANNER);
    }

    async printStatus() {
        const sys = await this.agent.checkSystems();
        const vmName = this.agent.linkedVm ? this.agent.linkedVm.name : "NONE";
        const mode = this.agent.autoMode ? chalk.yellow("AUTO") : chalk.white("MANUAL");
        const gpuStatus = sys.gpu ? chalk.green('ACTIVE') : chalk.dim('OFF');
        const ollamaStatus = sys.ollamaConnected ? chalk.green('CONNECTED') : chalk.red('OFFLINE');

        console.log(chalk.dim('─'.repeat(50)));
        console.log(`${chalk.bold('STATUS:')} ${ollamaStatus} | ${chalk.bold('MODEL:')} ${chalk.cyan(sys.model)} | ${chalk.bold('GPU:')} ${gpuStatus}`);
        console.log(`${chalk.bold('TARGET:')} ${chalk.cyan(vmName)}    | ${chalk.bold('MODE:')} ${mode}`);
        console.log(chalk.dim('─'.repeat(50)));
    }

    async run() {
        this.clear();
        const spinner = ora({ text: chalk.hex('#ff003c').bold('Engaging Neural Link...'), spinner: 'bouncingBar' }).start();
        await this.agent.llm.checkConnection();
        spinner.stop();
        await this.printStatus();

        while (true) {
            try {
                const isVM = this.agent.targetEnv === 'vm' && this.agent.linkedVm;
                const envTag = isVM ? '[VM] ' : '';
                const ctx = isVM ? this.agent.linkedVm!.name : 'sentinel';
                const roleTag = this.agent.currentRole !== "DEFAULT" ? `(${this.agent.currentRole.split(' ')[0]})` : "";
                const prefix = `${chalk.hex('#ff003c').bold(envTag + 'ronin' + roleTag)}/${chalk.hex('#880000')(ctx)} ${chalk.hex('#ff003c').bold('>')}`;

                const userInput = await input({ message: prefix });

                const cleanInput = userInput.trim();
                if (!cleanInput) continue;
                
                if (['exit', 'quit', '/exit'].includes(cleanInput.toLowerCase())) break;

                if (cleanInput.startsWith("/")) {
                    await this.handleSlashCommand(cleanInput);
                    continue;
                }

                await this.missionLoop(cleanInput);

            } catch (e: any) {
                if (e.name === 'ExitPromptError') {
                    console.log(`\n${chalk.yellow('Mission Aborted. Safely exiting.')}`);
                    break;
                }
                console.error(chalk.red.bold(`ERROR: ${e.message}`));
            }
        }
    }

    async handleSlashCommand(cmd: string) {
        const parts = cmd.toLowerCase().trim().split(/\s+/);
        const baseCmd = parts[0];

        if (baseCmd === '/auto') {
            this.agent.autoMode = true;
            console.log(chalk.green("* Autonomous Mode ENGAGED."));
        } else if (baseCmd === '/manual') {
            this.agent.autoMode = false;
            console.log(chalk.blue("* Manual Override ACTIVE."));
        } else if (baseCmd === '/vm') {
            this.agent.targetEnv = 'vm';
            console.log(chalk.green('* VM Target Mode ENGAGED.'));
        } else if (baseCmd === '/host') {
            this.agent.targetEnv = 'host';
            console.log(chalk.blue('* Host Target Mode ENGAGED.'));
        } else if (baseCmd === '/clear') {
            this.agent.memory = [];
            this.agent.currentRole = "DEFAULT";
            this.clear();
            await this.printStatus();
        } else if (baseCmd === '/status') {
            await this.printStatus();
        } else if (baseCmd === '/help') {
            console.log(chalk.cyan(`
    Tactical Command Matrix
    /auto       - Engage Autonomous Mode
    /manual     - Return to Manual mode
    /vm         - Target VirtualBox Guest
    /host       - Target Windows Host
    /link       - /link <name> <user> <pass>
    /status     - Show telemetry
    /recon      - Active Recon Mode
    /audit      - Analysis/Audit Mode
    /vibe       - Standard Assistant Mode
    /clear      - Reset Session
    /exit       - Shutdown
            `));
        } else if (['/recon', '/audit', '/vibe'].includes(baseCmd)) {
             this.agent.setRole(baseCmd.substring(1));
             console.log(chalk.green(`* Specialized Role '${baseCmd.substring(1).toUpperCase()}' ACTIVATED.`));
        } else {
            console.log(chalk.yellow(`! Unknown command: ${cmd}`));
        }
    }

    async missionLoop(userInput: string) {
        let currentPrompt = userInput;
        let step = 1;
        let consecutiveErrors = 0;
        let lastError = "";

        const abortController = new AbortController();
        const handleSigint = () => {
            console.log(chalk.yellow('\n\n[!] Mission aborted by operator (Ctrl+C). Halting execution...'));    
            abortController.abort();
        };

        process.on('SIGINT', handleSigint);

        try {
            while (!abortController.signal.aborted) {
                console.log(`\n${chalk.hex('#ff003c').bold(`▽ PHASE ${step}`)}        ${chalk.dim.italic('▽ STATUS: Analyzing tactical data...')}`);
                const spinner = ora({ text: chalk.white.bold('NEURAL ANALYSIS in progress...'), spinner: 'dots' }).start();
                let reasoning = "";

                try {
                    for await (const chunk of this.agent.chat(currentPrompt, abortController.signal)) {
                        if (abortController.signal.aborted) {
                            spinner.fail(chalk.yellow('Mission Aborted during analysis.'));
                            return;
                        }
                        reasoning += chunk;
                    }
                    spinner.succeed(chalk.white.bold('NEURAL ANALYSIS COMPLETE'));
                    // Map 'vbox' to 'bash' for visual rendering so cli-markdown doesn't crash
                    const displayReasoning = reasoning.replace(/```vbox/gi, '```bash');
                    console.log(`\n${cliMd(displayReasoning)}`);
                } catch (e: any) {
                    if (e.name === 'AbortError' || abortController.signal.aborted) {
                        spinner.fail(chalk.yellow('Mission Aborted.'));
                        return;
                    }
                    spinner.fail(`LLM Stream Error: ${e.message}`);
                    break;
                }

                if (abortController.signal.aborted) break;

                const commands = this.agent.extractCommands(reasoning);
                if (commands.length === 0) {
                    console.log(chalk.dim.italic('▽ STATUS: Mission Complete.'));
                    break;
                }

                for (const cmd of commands) {
                    if (abortController.signal.aborted) break;

                    if (cmd.executor === 'complete_task') {
                        console.log(chalk.green.bold(`✓ ${cmd.code}`));
                        return;
                    }

                    console.log(`\n${chalk.cyan.bold('>>>')} ${chalk.bold(`EXECUTING: ${cmd.executor.toUpperCase()}`)}`);
                    console.log(chalk.dim('─'.repeat(20)));
                    console.log(chalk.white(cmd.code));
                    console.log(chalk.dim('─'.repeat(20)));

                    if (!this.agent.autoMode) {
                        process.off('SIGINT', handleSigint);
                        let ok = false;
                        try {
                            ok = await confirm({ message: chalk.yellow('Confirm Action?') });
                        } catch (e: any) {
                            if (e.name === 'ExitPromptError') abortController.abort();
                        }
                        process.on('SIGINT', handleSigint);
                        if (!ok || abortController.signal.aborted) {
                            console.log(chalk.yellow('! Action cancelled by operator.'));
                            return;
                        }
                    }

                    const execSpinner = ora(`Executing on ${cmd.executor}...`).start();
                    let result: CommandResult | null = null;
                    try {
                        result = await this.agent.executeCommand(cmd, abortController.signal, (data) => {
                            execSpinner.text = `Executing on ${cmd.executor}...\n${chalk.dim(data.split('\n').pop()?.substring(0, 50))}`;
                        });
                    } catch (e: any) {
                        if (abortController.signal.aborted) {
                            execSpinner.fail('Execution aborted.');
                            return;
                        }
                    }

                    if (abortController.signal.aborted) {
                         execSpinner.fail('Execution aborted.');
                         return;
                    }

                    if (result && result.success) {
                        execSpinner.succeed('Execution successful');
                        consecutiveErrors = 0;
                    } else {
                        execSpinner.fail('Execution failed');
                        const errorKey = result ? (result.stdout + result.stderr).substring(0, 100) : "unknown";
                        if (errorKey === lastError) {
                            consecutiveErrors++;
                        } else {
                            consecutiveErrors = 1;
                            lastError = errorKey;
                        }
                    }

                    if (consecutiveErrors >= 3) {
                        console.log(chalk.red.bold('\n[CIRCUIT BREAKER] Loop detected. Halting for operator intervention.'));
                        return;
                    }

                    const outputText = result ? (result.stdout + '\n' + result.stderr).trim() : "No output.";
                    const truncatedOutput = outputText.length > 2000 ? outputText.substring(0, 2000) + "\n... [TRUNCATED]" : outputText;
                    
                    console.log(`\n${chalk.green.bold('<<<')} ${chalk.bold('OBSERVATION')}`);
                    console.log(chalk.dim('─'.repeat(20)));
                    console.log(truncatedOutput ? chalk.white(truncatedOutput) : chalk.dim('No output received.'));
                    console.log(chalk.dim('─'.repeat(20)));

                    if (result) {
                        currentPrompt = `OBSERVATION: ${result.stdout.substring(0, 500)}\n${!result.success ? "ANALYSIS: Command failed. Try a different approach or fix permissions." : "Proceed."}`;
                    }
                    step++;
                }
                if (!this.agent.autoMode) break;
            }
        } finally {
            process.off('SIGINT', handleSigint);
        }
    }
}
