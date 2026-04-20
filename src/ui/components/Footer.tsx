import React from 'react';
import { Box, Text } from 'ink';

interface Props {
  workspace: string;
  target: string;
  model: string;
  gpu: boolean;
  ollamaConnected: boolean;
}

export const Footer: React.FC<Props> = ({ workspace, target, model, gpu, ollamaConnected }) => (
  <Box flexDirection="column" marginTop={1} paddingX={1}>
    <Text dimColor>{"┄".repeat(process.stdout.columns || 80)}</Text>
    <Box width="100%" justifyContent="space-between">
      <Text dimColor>DIR: <Text color="cyan">{workspace.split('/').pop()}</Text></Text>
      <Text dimColor>TARGET: <Text color="yellow">{target}</Text></Text>
      <Text dimColor>LLM: <Text color={ollamaConnected ? "magenta" : "red"}>{ollamaConnected ? model : "OFFLINE"}</Text></Text>
      <Text dimColor>GPU: <Text color={gpu ? "green" : "dim"}>{gpu ? "ACTIVE" : "OFF"}</Text></Text>
    </Box>
  </Box>
);

