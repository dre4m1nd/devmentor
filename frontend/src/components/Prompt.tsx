import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';

import { symbols, theme } from '../theme.js';
import { COMMANDS, type CommandDef } from '../commands.js';

/**
 * 带补全菜单的输入框。
 *
 * 输入以 / 开头时直接在下方列出候选，用上下键选择、Tab 补全。
 * 这是 Ink 相比手写终端控制最省事的地方——候选列表就是普通组件。
 */
export function Prompt({
  disabled,
  onSubmit,
}: {
  disabled: boolean;
  onSubmit: (text: string) => void;
}): React.ReactElement {
  const [value, setValue] = useState('');
  const [selected, setSelected] = useState(0);

  const openMenu = value.startsWith('/') && !value.includes(' ');
  const matches: CommandDef[] = openMenu
    ? COMMANDS.filter((c) => c.name.startsWith(value))
    : [];

  useInput((inputChar, key) => {
    if (disabled) return;

    if (key.return) {
      const text = value.trim();
      if (!text) return;
      // 菜单打开且有选中项时，回车先补全命令名
      if (openMenu && matches.length > 0 && document_hasExactMatch(value, matches) === false) {
        setValue(matches[Math.min(selected, matches.length - 1)].name);
        setSelected(0);
        return;
      }
      onSubmit(text);
      setValue('');
      setSelected(0);
      return;
    }

    if (key.tab) {
      if (openMenu && matches.length > 0) {
        setValue(matches[Math.min(selected, matches.length - 1)].name);
        setSelected(0);
      }
      return;
    }

    if (openMenu && matches.length > 0) {
      if (key.upArrow) {
        setSelected((s) => (s - 1 + matches.length) % matches.length);
        return;
      }
      if (key.downArrow) {
        setSelected((s) => (s + 1) % matches.length);
        return;
      }
    }

    if (key.backspace || key.delete) {
      setValue((v) => v.slice(0, -1));
      setSelected(0);
      return;
    }

    if (key.ctrl || key.meta) return;
    if (inputChar) {
      setValue((v) => v + inputChar);
      setSelected(0);
    }
  });

  return (
    <Box flexDirection="column">
      <Box>
        <Text bold color={theme.brand}>
          {'你 '}
        </Text>
        <Text color={theme.muted}>{symbols.prompt} </Text>
        <Text>{value}</Text>
        {disabled ? null : <Text color={theme.muted}>▌</Text>}
      </Box>

      {openMenu && matches.length > 0 ? (
        <Box flexDirection="column" marginLeft={2} marginTop={1}>
          {matches.map((c, i) => (
            <Box key={c.name}>
              <Box width={2}>
                <Text color={i === selected ? theme.accent : theme.muted}>
                  {i === selected ? '❯' : ' '}
                </Text>
              </Box>
              <Box width={12}>
                <Text bold={i === selected} color={i === selected ? theme.accent : undefined}>
                  {c.name}
                </Text>
              </Box>
              <Text color={theme.muted}>{c.desc}</Text>
            </Box>
          ))}
        </Box>
      ) : null}
    </Box>
  );
}

function document_hasExactMatch(value: string, matches: CommandDef[]): boolean {
  return matches.some((m) => m.name === value);
}
