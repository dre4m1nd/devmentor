import React from 'react';
import { Box, Text } from 'ink';

import { symbols, theme } from '../theme.js';
import type { Entry } from '../types.js';

/** 渲染历史记录里的一条。 */
export function EntryView({ entry }: { entry: Entry }): React.ReactElement | null {
  switch (entry.kind) {
    case 'user':
      return (
        <Box marginTop={1}>
          <Text bold color={theme.brand}>
            {'你 '}
          </Text>
          <Text color={theme.muted}>{symbols.prompt} </Text>
          <Text>{entry.text}</Text>
        </Box>
      );

    case 'assistant':
      return (
        <Box marginTop={1} flexDirection="column">
          <Text>{entry.text}</Text>
        </Box>
      );

    case 'thinking':
      return (
        <Box flexDirection="column">
          <Text color={theme.muted} dimColor italic>
            {entry.text}
          </Text>
        </Box>
      );

    case 'tool': {
      const color = (theme.tool as Record<string, string>)[entry.state] ?? theme.muted;
      const label =
        entry.state === 'running'
          ? '运行中'
          : entry.state === 'success'
            ? '完成'
            : entry.state === 'denied'
              ? '被拒绝'
              : entry.state === 'interrupted'
                ? '被中断'
                : '失败';
      return (
        <Box flexDirection="column">
          <Text color={color}>
            {symbols.tool} {entry.name}
          </Text>
          <Text color={color}>
            {'  '}
            {symbols.result} {label}
            {entry.preview ? '  ' + entry.preview : ''}
          </Text>
        </Box>
      );
    }

    case 'system':
      return (
        <Box>
          <Text color={theme.muted}>{entry.text}</Text>
        </Box>
      );

    case 'success':
      return (
        <Box>
          <Text color={theme.accent}>
            {symbols.success} {entry.text}
          </Text>
        </Box>
      );

    case 'error':
      return (
        <Box flexDirection="column">
          <Text color={theme.danger}>
            {symbols.error} {entry.text}
          </Text>
        </Box>
      );

    default:
      return null;
  }
}
