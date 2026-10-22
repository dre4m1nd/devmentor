import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Box, Text, useApp, useInput } from 'ink';

import { Backend } from '../backend.js';
import { parseCommand } from '../commands.js';
import type { Entry, ServerEvent } from '../types.js';
import { Banner, type ReadyInfo } from './Banner.js';
import { ConfirmBox } from './ConfirmBox.js';
import { EntryView } from './EntryView.js';
import { Prompt } from './Prompt.js';
import { theme } from '../theme.js';

export type AppProps = {
  backendDir: string;
  python?: string;
  projectRoot?: string;
};

export function App({ backendDir, python, projectRoot }: AppProps): React.ReactElement {
  const { exit } = useApp();
  const [info, setInfo] = useState<ReadyInfo | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(false);
  const [pendingCalls, setPendingCalls] = useState<Record<string, unknown>[] | null>(null);
  const [exited, setExited] = useState(false);

  // 流式文本：模型输出是增量事件，累积起来当作一条 assistant 记录
  const streamBuf = useRef('');
  const backendRef = useRef<Backend | null>(null);

  const push = useCallback((entry: Entry) => {
    setEntries((prev) => [...prev, entry]);
  }, []);

  const flushStream = useCallback(() => {
    const text = streamBuf.current.trim();
    streamBuf.current = '';
    if (text) {
      setEntries((prev) => [...prev, { kind: 'assistant', text }]);
    }
  }, []);

  const handleEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case 'ready':
          setInfo({
            model: event.model,
            session: event.session.session,
            workspace: event.session.workspace,
            project: event.session.project,
            permission: event.session.permission,
            credentials: event.session.credentials,
          });
          break;

        case 'text.delta':
          streamBuf.current += event.text;
          // 立刻反映到界面：把缓冲区当成临时 assistant 记录渲染
          setEntries((prev) => {
            const last = prev[prev.length - 1];
            if (last?.kind === 'assistant' && (last as { streaming?: boolean }).streaming) {
              return [...prev.slice(0, -1), { kind: 'assistant', text: streamBuf.current }];
            }
            return [...prev, { kind: 'assistant', text: streamBuf.current }];
          });
          break;

        case 'thinking.delta':
          push({ kind: 'thinking', text: event.text });
          break;

        case 'tool.call':
          flushStream();
          push({ kind: 'tool', name: event.name, state: 'running' });
          break;

        case 'tool.result': {
          const state = (
            ['success', 'error', 'denied', 'interrupted'].includes(event.state)
              ? event.state
              : 'success'
          ) as 'success' | 'error' | 'denied' | 'interrupted';
          setEntries((prev) => {
            // 更新最近一条同名 running 的工具记录
            for (let i = prev.length - 1; i >= 0; i--) {
              const e = prev[i];
              if (e.kind === 'tool' && e.name === event.name && e.state === 'running') {
                const next = [...prev];
                next[i] = { ...e, state, preview: event.preview };
                return next;
              }
            }
            return [...prev, { kind: 'tool', name: event.name, state, preview: event.preview }];
          });
          break;
        }

        case 'require.confirm':
          flushStream();
          setPendingCalls(event.calls);
          break;

        case 'system':
          flushStream();
          push({ kind: 'system', text: event.text });
          break;

        case 'success':
          flushStream();
          push({ kind: 'success', text: event.text });
          break;

        case 'error':
          flushStream();
          push({ kind: 'error', text: event.message });
          break;

        case 'menu':
          flushStream();
          push({ kind: 'system', text: event.title });
          event.options.forEach((o) => {
            push({
              kind: 'system',
              text: '  ' + o.value + ') ' + o.label + (o.desc ? '  ' + o.desc : ''),
            });
          });
          break;

        case 'turn.end':
          flushStream();
          setBusy(false);
          break;

        case 'bye':
          setExited(true);
          flushStream();
          setTimeout(() => exit(), 50);
          break;

        default:
          break;
      }
    },
    [push, flushStream, exit],
  );

  useEffect(() => {
    const backend = new Backend({
      backendDir,
      python,
      env: projectRoot ? { DEVMENTOR_PROJECT_ROOT: projectRoot } : undefined,
      onEvent: handleEvent,
      onExit: (code) => {
        if (code !== 0 && code !== null) {
          push({ kind: 'error', text: '后端进程已退出（code ' + code + '）。' });
        }
        setExited(true);
        exit();
      },
    });
    backendRef.current = backend;
    backend.start();
    return () => backend.kill();
  }, [backendDir, python, projectRoot, handleEvent, push, exit]);

  const submit = useCallback(
    (text: string) => {
      const backend = backendRef.current;
      if (!backend) return;
      if (text === '/quit' || text === '/exit') {
        backend.shutdown();
        return;
      }
      push({ kind: 'user', text });
      const parsed = parseCommand(text);
      if (parsed) {
        backend.command(parsed.name, parsed.args);
      } else {
        backend.ask(text);
      }
      setBusy(true);
    },
    [push],
  );

  // 确认模式：y/n 决定是否放行
  useInput(
    (inputChar) => {
      const backend = backendRef.current;
      if (!backend) return;
      const approved = inputChar.toLowerCase() === 'y';
      backend.confirm(approved, approved ? '' : '用户拒绝了该操作');
      setPendingCalls(null);
      setBusy(true);
    },
    { isActive: pendingCalls !== null },
  );

  const visible = useMemo(() => entries, [entries]);

  return (
    <Box flexDirection="column">
      {info ? <Banner info={info} /> : <Text color={theme.muted}>正在启动后端…</Text>}

      {visible.map((entry, i) => (
        <EntryView key={i} entry={entry} />
      ))}

      {pendingCalls ? <ConfirmBox calls={pendingCalls} /> : null}

      {exited ? null : busy ? (
        <Box marginTop={1}>
          <Text color={theme.muted}>思考中… （Ctrl+C 中断）</Text>
        </Box>
      ) : (
        <Box marginTop={1}>
          <Prompt disabled={false} onSubmit={submit} />
        </Box>
      )}
    </Box>
  );
}
