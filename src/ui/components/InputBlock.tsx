import React from 'react';
import { Box, Text } from 'ink';
import TextInput from 'ink-text-input';

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  autoMode: boolean;
}

export const InputBlock: React.FC<Props> = ({ value, onChange, onSubmit, autoMode }) => (
  <Box flexDirection="column" marginTop={1} paddingX={1}>
    <Box>
      <Text color="red" bold> ❯ </Text>
      <TextInput 
        value={value} 
        onChange={onChange} 
        onSubmit={onSubmit} 
        placeholder="Awaiting mission orders..." 
      />
    </Box>
    <Box marginTop={0}>
        <Text dimColor>
            Mode: {autoMode ? "AUTONOMOUS" : "MANUAL"} | Shift+Tab to toggle | /help for commands
        </Text>
    </Box>
  </Box>
);


