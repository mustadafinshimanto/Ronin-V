import React, { useState, useEffect, useRef } from 'react';
import { Box, useApp, useInput, Text } from 'ink';
import { Header } from './components/Header.js';
import { InputBlock } from './components/InputBlock.js';
import { Footer } from './components/Footer.js';
import { LogArea } from './components/LogArea.js';
import { RoninAgent } from '../core/Agent.js';

interface Props {
  agent: RoninAgent;
}

export const App: React.FC<Props> = ({ agent }) => {
  const [inputValue, setInputValue] = useState('');
  const [logs, setLogs] = useState<{ role: string, content: string }[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [activity, setActivity] = useState<string | undefined>(undefined);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [autoMode, setAutoMode] = useState(agent.autoMode);
  const [targetEnv, setTargetEnv] = useState(agent.targetEnv);
  const [gpuActive, setGpuActive] = useState(false);
  const [ollamaConnected, setOllamaConnected] = useState(false);
  const { exit } = useApp();
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    agent.checkSystems().then(sys => {
        setGpuActive(sys.gpu);
        setOllamaConnected(sys.ollamaConnected);
    });
  }, []);

  useEffect(() => {
    let timer: NodeJS.Timeout | undefined;
    if (isThinking || activity) {
      timer = setInterval(() => setTimeElapsed(t => t + 1), 1000);
    } else {
      setTimeElapsed(0);
    }
    return () => clearInterval(timer);
  }, [isThinking, activity]);

  // Handle Target Env sync with Agent
  useEffect(() => {
    setTargetEnv(agent.targetEnv);
  }, [agent.targetEnv]);

  useInput((input, key) => {
    if (key.tab && key.shift) {
        const nextMode = !autoMode;
        agent.autoMode = nextMode;
        setAutoMode(nextMode);
    }
    if (key.escape && (isThinking || activity)) {
        abortControllerRef.current?.abort();
        setLogs(prev => [...prev, { role: 'assistant', content: 'Mission Aborted (ESC).' }]);
        setIsThinking(false);
        setActivity(undefined);
    }
  });

  const handleSubmit = async (value: string) => {
    const clean = value.trim();
    if (!clean) return;
    
    if (['exit', 'quit', '/exit'].includes(clean.toLowerCase())) {
        exit();
        return;
    }

    if (clean.startsWith('/')) {
        if (clean === '/auto') { agent.autoMode = true; setAutoMode(true); }
        else if (clean === '/manual') { agent.autoMode = false; setAutoMode(false); }
        else if (clean === '/vm') { agent.targetEnv = 'vm'; setTargetEnv('vm'); }
        else if (clean === '/host') { agent.targetEnv = 'host'; setTargetEnv('host'); }
        else if (clean === '/clear') { setLogs([]); agent.memory = []; }
        else if (['/recon', '/audit', '/vibe'].includes(clean)) {
            agent.setRole(clean.substring(1));
            setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: `[SYSTEM] Specialized Role '${clean.substring(1).toUpperCase()}' ACTIVATED.` }]);
        }
        setInputValue('');
        return;
    }

    setLogs(prev => [...prev.slice(-10), { role: 'user', content: clean }]);
    setInputValue('');
    
    let currentPrompt = clean;
    abortControllerRef.current = new AbortController();
    let consecutiveErrors = 0;
    let lastError = "";

    while (true) {
        if (abortControllerRef.current.signal.aborted) break;
        
        setIsThinking(true);
        let reasoning = "";
        try {
            // Add a placeholder for assistant response
            setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: '...' }]);
            
            for await (const chunk of agent.chat(currentPrompt, abortControllerRef.current.signal)) {
                reasoning += chunk;
                // Live streaming
                setLogs(prev => {
                    const next = [...prev];
                    next[next.length - 1] = { role: 'assistant', content: reasoning + ' █' };
                    return next;
                });
            }
            
            setLogs(prev => {
                const next = [...prev];
                next[next.length - 1] = { role: 'assistant', content: reasoning };
                return next;
            });

        } catch (e: any) {
            if (e.name !== 'AbortError') {
                setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: `[ERROR] ${e.message}` }]);
            }
            setIsThinking(false);
            break;
        }
        setIsThinking(false);
        if (abortControllerRef.current.signal.aborted) break;

        const commands = agent.extractCommands(reasoning);
        if (commands.length === 0) break;

        let lastResult = null;
        for (const cmd of commands) {
            if (abortControllerRef.current.signal.aborted) break;
            
            if (cmd.executor === 'complete_task') {
                setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: `[SYSTEM] MISSION SECURED.` }]);
                setIsThinking(false);
                setActivity(undefined);
                return;
            }

            setActivity(`EXECUTING ${cmd.executor.toUpperCase()}`);
            setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: `[EXEC] ${cmd.executor.toUpperCase()}: ${cmd.code.substring(0, 60)}${cmd.code.length > 60 ? '...' : ''}` }]);
            
            // Add a placeholder for live output
            setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: '[WAITING FOR OUTPUT...]' }]);

            const result = await agent.executeCommand(cmd, abortControllerRef.current.signal, (data) => {
                setLogs(prev => {
                    const next = [...prev];
                    const lastEntry = next[next.length - 1];
                    if (lastEntry && lastEntry.content.startsWith('[EXEC]')) {
                        // This shouldn't happen based on the push above, but safety first
                        next.push({ role: 'assistant', content: data });
                    } else {
                        // Append or replace the placeholder
                        const currentContent = lastEntry.content === '[WAITING FOR OUTPUT...]' ? '' : lastEntry.content;
                        // Limit live output per entry for stability
                        const newContent = (currentContent + data).split('\n').slice(-10).join('\n');
                        next[next.length - 1] = { role: 'assistant', content: newContent };
                    }
                    return next;
                });
            });
            lastResult = result;
            const output = (result.stdout + '\n' + result.stderr).trim();
            
            setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: `[OBSERVATION]\n${output || "No output."}` }]);

            if (!result.success) {
                const errorKey = output.substring(0, 100);
                if (errorKey === lastError) {
                    consecutiveErrors++;
                } else {
                    consecutiveErrors = 1;
                    lastError = errorKey;
                }
            } else {
                consecutiveErrors = 0;
            }

            if (consecutiveErrors >= 3) {
                setLogs(prev => [...prev.slice(-10), { role: 'assistant', content: `[CIRCUIT BREAKER] Loop detected. Halting for operator intervention.` }]);
                setIsThinking(false);
                setActivity(undefined);
                return;
            }
        }
        setActivity(undefined);

        if (lastResult) {
            currentPrompt = `OBSERVATION: ${lastResult.stdout.substring(0, 500)}\n${!lastResult.success ? "ANALYSIS: Command failed. Try a different approach or fix permissions." : "Proceed."}`;
        }
        if (!agent.autoMode || abortControllerRef.current.signal.aborted) break;
    }
  };

  return (
    <Box flexDirection="column" paddingBottom={1}>
      <Header isThinking={isThinking} timeElapsed={timeElapsed} activity={activity} />
      
      <Box flexDirection="column">
        <LogArea logs={logs.slice(-6)} /> 
      </Box>

      <InputBlock 
        value={inputValue} 
        onChange={setInputValue} 
        onSubmit={handleSubmit} 
        autoMode={autoMode}
      />
      
      <Footer 
        workspace={process.cwd().replace(/\\/g, '/')} 
        target={targetEnv === 'vm' ? (agent.linkedVm?.name || "KALI") : "WINDOWS HOST"} 
        model={agent.llm.modelName} 
        gpu={gpuActive}
        ollamaConnected={ollamaConnected}
      />
    </Box>
  );
};