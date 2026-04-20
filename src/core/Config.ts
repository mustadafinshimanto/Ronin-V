import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'yaml';

export interface RoninConfig {
    ronin: {
        name: string;
        version: string;
        codename: string;
        data_dir: string;
        log_level: string;
    };
    model: {
        name: string;
        base: string;
        ctx_length: number;
        temperature: number;
        top_p: number;
    };
    ollama: {
        host: string;
        timeout: number;
        keep_alive: string;
    };
    agent: {
        auto_mode: boolean;
        max_steps: number;
        vm_user: string;
        vm_pass: string;
    };
    executors: {
        powershell: {
            enabled: boolean;
            timeout: number;
            shell: string;
        };
        python: {
            enabled: boolean;
            timeout: number;
        };
        vbox?: {
            enabled: boolean;
            timeout: number;
            path?: string;
        };
    };
}

export class ConfigLoader {
    private static instance: RoninConfig | null = null;

    static load(): RoninConfig {
        if (this.instance) return this.instance;

        const configPath = path.join(process.cwd(), 'config.yaml');
        const examplePath = path.join(process.cwd(), 'config.example.yaml');

        let configContent: string;

        if (fs.existsSync(configPath)) {
            configContent = fs.readFileSync(configPath, 'utf8');
        } else if (fs.existsSync(examplePath)) {
            configContent = fs.readFileSync(examplePath, 'utf8');
            // Optionally write the example to config.yaml if it doesn't exist
            fs.writeFileSync(configPath, configContent, 'utf8');
        } else {
            throw new Error('Configuration file not found (config.yaml or config.example.yaml)');
        }

        this.instance = parse(configContent) as RoninConfig;
        return this.instance;
    }
}
