import { createPrompt, useState, useKeypress, usePrefix, isEnterKey, isUpKey, isDownKey } from '@inquirer/core';
import chalk from 'chalk';
import * as fs from 'fs';

const HISTORY_FILE = '.ronin_history';
let history: string[] = [];
try {
   history = fs.readFileSync(HISTORY_FILE, 'utf8').split('\n').filter(Boolean);
} catch (e) {}

export const slashPrompt = createPrompt<string, { message: string, commands: string[] }>((config, done) => {
  const [value, setValue] = useState('');
  const [historyIndex, setHistoryIndex] = useState(history.length);
  const prefix = usePrefix({ theme: (config as any).theme });
  
  const suggestions = value.startsWith('/') ? config.commands.filter(c => c.startsWith(value) && c !== value) : [];

  useKeypress((key, rl) => {
    // ALWAYS sync the internal state with the actual readline buffer
    setValue(rl.line);

    if (isEnterKey(key)) {
      const line = rl.line.trim();
      if (line) {
         if (history[history.length - 1] !== line) {
            history.push(line);
            try { fs.writeFileSync(HISTORY_FILE, history.join('\n') + '\n'); } catch(e){}
         }
      }
      done(line);
    } else if (key.name === 'tab' && suggestions.length > 0) {
      const match = suggestions[0];
      rl.line = match;
      (rl as any).cursor = match.length;
      setValue(match);
    } else if (isUpKey(key)) {
      if (historyIndex > 0) {
         const newIndex = historyIndex - 1;
         setHistoryIndex(newIndex);
         rl.line = history[newIndex];
         (rl as any).cursor = rl.line.length;
         setValue(rl.line);
      }
    } else if (isDownKey(key)) {
      if (historyIndex < history.length - 1) {
         const newIndex = historyIndex + 1;
         setHistoryIndex(newIndex);
         rl.line = history[newIndex];
         (rl as any).cursor = rl.line.length;
         setValue(rl.line);
      } else {
         setHistoryIndex(history.length);
         rl.line = '';
         (rl as any).cursor = 0;
         setValue('');
      }
    }
  });

  let msg = `${prefix} ${chalk.bold(config.message)} ${value}`;
  if (suggestions.length > 0) {
     msg += '\n' + chalk.dim('  Suggestions: ') + suggestions.map(s => chalk.cyan(s)).join(', ');
  }
  return msg;
});

