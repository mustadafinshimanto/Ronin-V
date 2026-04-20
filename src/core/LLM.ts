import { Ollama } from 'ollama';
import { ConfigLoader } from './Config.js';

export class RoninLLM {
    private client: Ollama;
    public modelName: string;

    constructor() {
        const config = ConfigLoader.load();
        this.client = new Ollama({ host: config.ollama.host });
        this.modelName = config.model.name;
    }

    async checkConnection(): Promise<boolean> {
        try {
            await this.client.list();
            return true;
        } catch {
            return false;
        }
    }

    async *chat(messages: any[], signal?: AbortSignal): AsyncGenerator<string, void, unknown> {
        try {
            const response = await this.client.chat({
                model: this.modelName,
                messages: messages,
                stream: true,
            });

            for await (const chunk of response) {
                if (signal?.aborted) {
                    this.client.abort(); // Attempt old method
                    break;
                }
                if (chunk.message?.content) {
                    yield chunk.message.content;
                }
            }
        } catch (e: any) {
            if (e.name === 'AbortError') return;
            yield `\n[LLM ERROR] ${e.message || String(e)}`;
        }
    }
}

