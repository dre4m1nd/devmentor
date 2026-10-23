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
  // 需要用户点选的菜单（如 /login 的厂商列表）。收到 menu 事件时设置，
  // 选中或取消后清空。渲染成可 ↑↓ 选择、回车确认的列表。
  const [activeMenu, setActiveMenu] = useState<{
    title: string;
    options: { value: string; label: string; desc?: string }[];
    selected: number;
  } | null>(null);

  // 流式文本：模型输出是增量事件，累积起来当作一条 assistant 记录
  const streamBuf = useRef('');
  // 当前正在流式输出的 assistant 条目下标；-1 表示没有
  const streamingIdx = useRef(-1);
  const backendRef = useRef<Backend | null>(null);

  const push = useCallback((entry: Entry) => {
    setEntries((prev) => [...prev, entry]);
  }, []);

  const flushStream = useCallback(() => {
    const text = streamBuf.current.trim();
    streamBuf.current = '';
    const idx = streamingIdx.current;
    streamingIdx.current = -1;

    if (!text) return;

    // 流式期间已经渲染过这条内容，flush 只做收尾（保留已渲染的那条），
    // 不能再 push 一条，否则每条回复都会重复两遍。
    setEntries((prev) => {
      if (idx >= 0 && idx < prev.length && prev[idx]?.kind === 'assistant') {
        return prev;   // 已经在位，不动
      }
      return [...prev, { kind: 'assistant', text }];
    });
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
          // 用 ref 记住"当前正在流式的条目下标"，直接原地更新它。
          //
          // 之前靠判断 last.streaming，但条目上根本没设这个字段，
          // 导致每个 delta 都 push 一条新记录——一段 200 字的回复会变成
          // 几十条重复条目铺满屏幕（实测 20 个 delta 出 20 条）。
          setEntries((prev) => {
            const idx = streamingIdx.current;
            if (idx >= 0 && idx < prev.length && prev[idx]?.kind === 'assistant') {
              const next = prev.slice();
              next[idx] = { kind: 'assistant', text: streamBuf.current };
              return next;
            }
            streamingIdx.current = prev.length;
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
          // 不写进历史：这是一个待选择的交互，渲染成菜单更合适
          setActiveMenu({
            title: event.title,
            options: event.options,
            selected: 0,
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
        // 斜杠命令是本地即时响应，不进 busy 状态。
        // 后端只在 ask()/confirm() 结束时发 turn.end，命令不会发——
        // 若这里也 setBusy(true)，会永远卡在"思考中"且输入框消失。
        backend.command(parsed.name, parsed.args);
      } else {
        backend.ask(text);
        setBusy(true);
      }
    },
    [push],
  );

  // Ctrl+C 语义：忙时打断当前回答，空闲时退出程序。
  //
  // 之前只有进程级 SIGINT，而 Ink 开了 exitOnCtrlC:false，导致：
  //   - 忙时按 Ctrl+C 不会中断，只能干等
  //   - 空闲时按 Ctrl+C 行为依赖外部信号，不可靠
  // 统一在组件层处理，两条路径都明确。
  useInput(
    (inputChar, key) => {
      if (!(key.ctrl && inputChar === 'c')) return;
      const backend = backendRef.current;
      if (!backend) return;
      if (busy) {
        backend.interrupt();
        setPendingCalls(null);
        setActiveMenu(null);
      } else {
        backend.shutdown();
      }
    },
    { isActive: !exited },
  );

  // 菜单模式：↑↓ 选择，回车确认，Esc 取消
  useInput(
    (_inputChar, key) => {
      const backend = backendRef.current;
      if (!backend || !activeMenu) return;

      if (key.upArrow) {
        setActiveMenu({
          ...activeMenu,
          selected:
            (activeMenu.selected - 1 + activeMenu.options.length) %
            activeMenu.options.length,
        });
        return;
      }
      if (key.downArrow) {
        setActiveMenu({
          ...activeMenu,
          selected: (activeMenu.selected + 1) % activeMenu.options.length,
        });
        return;
      }
      if (key.return) {
        const chosen = activeMenu.options[activeMenu.selected];
        setActiveMenu(null);
        push({ kind: 'user', text: chosen.value });
        // 登录阶段后端期望裸文本，用 ask 发才能在 _dispatch_text 里被接住
        backend.ask(chosen.value);
        return;
      }
      if (key.escape) {
        setActiveMenu(null);
        push({ kind: 'system', text: '已取消。' });
        backend.ask('');
        return;
      }
    },
    { isActive: activeMenu !== null },
  );

  // 确认模式：只有 y / n 有效，其它键忽略。
  //
  // 之前是 approved = (inputChar === 'y')，意味着按任何其它键（含误触）
  // 都会被当成"拒绝"并立即发出——确认框消失、无法撤销。
  // 现在显式只认 y 和 n，别的键什么都不做，用户可以从容再按。
  useInput(
    (inputChar, key) => {
      const backend = backendRef.current;
      if (!backend) return;

      const ch = inputChar.toLowerCase();
      let approved: boolean | null = null;
      if (ch === 'y' || key.return) {
        approved = true;
      } else if (ch === 'n' || key.escape) {
        approved = false;
      }
      if (approved === null) return;   // 其它键：忽略

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

      {activeMenu ? (
        <Box flexDirection="column" marginTop={1} borderStyle="round" borderColor={theme.accent} paddingX={1}>
          <Text bold color={theme.accent}>
            {activeMenu.title}
          </Text>
          {activeMenu.options.map((o, i) => (
            <Box key={o.value}>
              <Box width={2}>
                <Text color={i === activeMenu.selected ? theme.accent : theme.muted}>
                  {i === activeMenu.selected ? '❯' : ' '}
                </Text>
              </Box>
              <Box width={32}>
                <Text bold={i === activeMenu.selected} color={i === activeMenu.selected ? theme.accent : undefined}>
                  {o.label}
                </Text>
              </Box>
              <Text color={theme.muted}>{o.desc ?? ''}</Text>
            </Box>
          ))}
          <Box marginTop={1}>
            <Text color={theme.muted}>↑↓ 选择，回车确认，Esc 取消</Text>
          </Box>
        </Box>
      ) : null}

      {exited ? null : activeMenu ? null : busy ? (
        <Box marginTop={1}>
          <Text color={theme.muted}>思考中… （Ctrl+C 中断）</Text>
        </Box>
      ) : (
        <Box marginTop={1}>
          <Prompt onSubmit={submit} />
        </Box>
      )}
    </Box>
  );
}