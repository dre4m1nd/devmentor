/**
 * 后端进程管理：spawn Python 服务，读写 JSON 行。
 *
 * 关键约束：后端把日志写到 stderr，stdout 只有协议 JSON。
 * 这里按行解析 stdout，遇到非 JSON 行直接跳过（容错），
 * 避免后端某天多打一行日志就把前端卡死。
 */

import { spawn, type ChildProcess } from 'node:child_process';
import { createInterface } from 'node:readline';

import type { ClientRequest, ServerEvent } from './types.js';

export type BackendOptions = {
  /** Python 可执行文件 */
  python?: string;
  /** 后端模块所在目录，用于设置 PYTHONPATH */
  backendDir: string;
  /** 额外环境变量 */
  env?: Record<string, string>;
  onEvent: (event: ServerEvent) => void;
  onExit: (code: number | null) => void;
  onStderr?: (line: string) => void;
};

export class Backend {
  private proc: ChildProcess | null = null;
  private readonly opts: BackendOptions;

  constructor(opts: BackendOptions) {
    this.opts = opts;
  }

  start(): void {
    const python = this.opts.python ?? (process.platform === 'win32' ? 'python' : 'python3');
    const env = {
      ...process.env,
      PYTHONPATH: this.opts.backendDir,
      PYTHONIOENCODING: 'utf-8',
      ...this.opts.env,
    };

    this.proc = spawn(python, ['-m', 'devmentor.server'], {
      cwd: this.opts.backendDir,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    // stdout：协议 JSON，一行一条
    if (this.proc.stdout) {
      const rl = createInterface({ input: this.proc.stdout });
      rl.on('line', (line) => {
        const trimmed = line.trim();
        if (!trimmed) return;
        try {
          const event = JSON.parse(trimmed) as ServerEvent;
          this.opts.onEvent(event);
        } catch {
          // 非协议输出（后端误写日志）：忽略而不是崩溃
        }
      });
    }

    // stderr：诊断日志，交给可选的日志回调
    if (this.proc.stderr && this.opts.onStderr) {
      const rl = createInterface({ input: this.proc.stderr });
      rl.on('line', (line) => this.opts.onStderr?.(line));
    }

    this.proc.on('exit', (code) => {
      this.proc = null;
      this.opts.onExit(code);
    });
  }

  send(request: ClientRequest): void {
    if (!this.proc?.stdin?.writable) return;
    this.proc.stdin.write(JSON.stringify(request) + '\n');
  }

  ask(text: string): void {
    this.send({ type: 'ask', text });
  }

  command(name: string, args: string[] = []): void {
    this.send({ type: 'command', name, args });
  }

  confirm(approved: boolean, reason = ''): void {
    this.send({ type: 'confirm', approved, reason });
  }

  shutdown(): void {
    this.send({ type: 'shutdown' });
    // 给后端一点时间优雅退出，超时强杀
    setTimeout(() => this.kill(), 1500).unref();
  }

  kill(): void {
    this.proc?.kill();
    this.proc = null;
  }

  get running(): boolean {
    return this.proc !== null;
  }
}
