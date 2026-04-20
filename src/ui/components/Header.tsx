import React from 'react';
import { Box, Text } from 'ink';
import Spinner from 'ink-spinner';

interface Props {
  isThinking: boolean;
  timeElapsed: number;
  activity?: string;
}

export const Header: React.FC<Props> = ({ isThinking, timeElapsed, activity }) => (
  <Box flexDirection="column" paddingX={1}>
    <Box justifyContent="space-between" width="100%">
      <Box>
        <Text bold color="red">RONIN-V </Text>
        <Text dimColor>| </Text>
        {isThinking ? (
          <Text color="yellow">
            <Spinner type="dots" /> ANALYZING ({timeElapsed}s)
          </Text>
        ) : activity ? (
          <Text color="cyan">
            <Spinner type="binary" /> {activity.toUpperCase()} ({timeElapsed}s)
          </Text>
        ) : (
          <Text color="green">READY</Text>
        )}
      </Box>
      <Text dimColor>v2.1.0 • Tactical Interface</Text>
    </Box>
    <Text dimColor>{"┄".repeat(process.stdout.columns || 80)}</Text>
  </Box>
);

