import React from 'react';
import { Box, Text } from 'ink';

import { theme } from '../theme.js';

/** 工具调用确认框（interactive 权限档位下出现）。 */
export function ConfirmBox({
  calls,
}: {
  calls: Record<string, unknown>[];
}): React.ReactElement {
  return (
    <Box flexDirection="column" borderStyle="round" borderColor={theme.warn} paddingX={1}>
      <Text bold color={theme.warn}>
        需要确认以下操作
      </Text>
      {calls.map((call, i) => {
        const name = String(call.name ?? call.tool_call_name ?? 'unknown');
        const input = JSON.stringify(call.input ?? call.arguments ?? {});
        return (
          <Box key={i} flexDirection="column" marginTop={1}>
            <Text bold>{name}</Text>
            <Text color={theme.muted}>
              {input.length > 120 ? input.slice(0, 120) + '…' : input}
            </Text>
          </Box>
        );
      })}
      <Box marginTop={1}>
        <Text color={theme.muted}>按 y 或回车允许，n 或 Esc 拒绝</Text>
      </Box>
    </Box>
  );
}