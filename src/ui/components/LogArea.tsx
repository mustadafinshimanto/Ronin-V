import React from 'react';
import { Box, Text } from 'ink';

interface LogEntry {
  role: string;
  content: string;
}

interface Props {
  logs: LogEntry[];
}

export const LogArea: React.FC<Props> = ({ logs }) => (
  <Box flexDirection="column" paddingX={1} minHeight={5}>
    {logs.map((log, i) => {
      const isUser = log.role === 'user';
      let content = log.content;
      
      // Truncate by characters
      if (content.length > 500) {
        content = content.substring(0, 500) + '... [TRUNCATED]';
      }

      // Truncate by lines
      const lines = content.split('\n');
      if (lines.length > 10) {
        content = lines.slice(0, 10).join('\n') + '\n... [TOO MANY LINES]';
      }

      return (
        <Box key={i} flexDirection="column">
          <Text bold color={isUser ? 'cyan' : 'red'}>
            {isUser ? ' ● OPERATOR' : ' ▲ SENTINEL'}
          </Text>
          <Box paddingLeft={2}>
            <Text color="white">{content}</Text>
          </Box>
        </Box>
      );
    })}
  </Box>
);
