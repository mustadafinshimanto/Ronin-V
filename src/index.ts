import chalk from 'chalk';
import ora from 'ora';
import { RoninAgent } from './core/Agent.js';
import { RoninSentinelUI } from './ui/SentinelUI.js';
import { render } from 'ink';
import React from 'react';
import { App } from './ui/App.js';

async function main() {
    try {
        const useInk = process.argv.includes('--ui=ink');
        
        if (!useInk) {
            console.clear();
            console.log(`\n${chalk.hex('#ff003c').bold('>>')} Booting Vibe Sentinel v2.1...`);
        }
        
        const agent = new RoninAgent();
        
        const vmSpinner = ora({ text: chalk.dim('Scanning for Active Target VMs...'), spinner: 'dots' });
        if (!useInk) vmSpinner.start();
        
        await agent.init();
        
        if (agent.linkedVm) {
            if (!useInk) vmSpinner.succeed(chalk.green(`Master Link Established: ${chalk.bold(agent.linkedVm.name)}`));
            agent.targetEnv = 'vm';
        } else {
            if (!useInk) vmSpinner.info(chalk.yellow('No Target VMs detected. Operating in Host Mode.'));
            agent.targetEnv = 'host';
        }

        if (useInk) {
            render(React.createElement(App, { agent }));
        } else {
            const ui = new RoninSentinelUI(agent);
            await ui.run();
        }
    } catch (e: any) {
        console.error(`\n[FATAL ERROR] ${e.message}`);
        process.exit(1);
    }
}

main();
