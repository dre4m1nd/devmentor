#!/usr/bin/env node
/**
 * DevMentor 前端入口。
 *
 * 职责很轻：解析参数 -> 定位后端目录 -> 渲染 Ink 应用。
 * 所有业务逻辑在后端，这里只做终端渲染与输入。
 */

import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { existsSync } from 'node:fs';

import React from 'react';
import { render } from 'ink';

import { App } from './components/App.js';

type Options = {
  backendDir?: string;
  python?: string;
  projectRoot?: string;
};

function parseArgs(argv: string[]): Options {
  const opts: Options = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--backend' && argv[i + 1]) {
      opts.backendDir = resolve(argv[++i]);
    } else if (arg === '--python' && argv[i + 1]) {
      opts.python = argv[++i];
    } else if (arg === '--project' && argv[i + 1]) {
      opts.projectRoot = resolve(argv[++i]);
    }
  }
  return opts;
}

/** 定位后端目录：优先参数，然后从当前文件位置推。 */
function resolveBackendDir(explicit?: string): string {
  if (explicit) return explicit;

  const here = dirname(fileURLToPath(import.meta.url));
  const candidates = [
    join(here, '..', '..', 'backend'),
    join(here, '..', 'backend'),
    join(process.cwd(), 'backend'),
  ];
  for (const c of candidates) {
    if (existsSync(join(c, 'devmentor', 'server.py'))) {
      return resolve(c);
    }
  }
  // 兜底：交给后端自己报错，比在这里静默失败更好排查
  return resolve(candidates[0]);
}

function main(): void {
  const opts = parseArgs(process.argv.slice(2));
  const backendDir = resolveBackendDir(opts.backendDir);

  const instance = render(
    React.createElement(App, {
      backendDir,
      python: opts.python,
      projectRoot: opts.projectRoot,
    }),
    { exitOnCtrlC: false },
  );

  // Ctrl+C 交给 Ink 自己处理（中断当前请求而不是直接退出）
  process.on('SIGINT', () => {
    instance.unmount();
    process.exit(0);
  });
}

main();
