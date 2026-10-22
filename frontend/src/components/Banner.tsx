import React from 'react';
import { Box, Text } from 'ink';

import { theme } from '../theme.js';

export type ReadyInfo = {
  model: string;
  session: string;
  workspace: string;
  project: string;
  permission: string;
  credentials: string;
};

/**
 * 启动横幅。
 *
 * 用 Flexbox 自然排版，不需要像手写 ANSI 那样计算中文占几列。
 */
export function Banner({ info }: { info: ReadyInfo }): React.ReactElement {
  const rows: Array<[string, string]> = [
    ['模型', info.model],
    ['凭据', info.credentials],
    ['会话', info.session],
    ['工作区', info.workspace],
    ['代码目录', info.project],
    ['权限', info.permission],
  ];

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box borderStyle="round" borderColor={theme.brand} paddingX={2}>
        <Text bold color={theme.brand}>
          DevMentor · 编程导师
        </Text>
      </Box>
      <Box flexDirection="column" marginTop={1}>
        {rows.map(([label, value]) => (
          <Box key={label}>
            <Box width={10}>
              <Text color={theme.muted}>{label}</Text>
            </Box>
            <Text>{value}</Text>
          </Box>
        ))}
      </Box>
      <Box marginTop={1}>
        <Text color={theme.muted}>直接提问，或输入 / 查看命令。</Text>
      </Box>
    </Box>
  );
}
