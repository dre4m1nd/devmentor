import type { MenuOption } from './types.js';

export type CommandDef = {
  name: string;
  desc: string;
  /** 固定参数取值，用于二级补全 */
  args?: string[];
  /** 带参数语法的完整用法，显示在菜单右侧。缺省时只用 name。 */
  usage?: string;
};

/**
 * 命令表。与后端 devmentor/commands.py 的 DEFINITIONS 对应。
 *
 * 前端保留一份是为了：补全菜单能立即响应（不必等后端），
 * 且参数候选能在本地算出来。缺任何命令都不会破坏功能——
 * 命令最终都发给后端执行，前端只负责补全体验。
 */
export const COMMANDS: CommandDef[] = [
  { usage: '/new [名字]', name: '/new', desc: '开启新会话' },
  { name: '/reset', desc: '清空当前会话上下文' },
  { usage: '/mode <interactive|read-only|full>', name: '/mode', desc: '切换权限档位', args: ['interactive', 'read-only', 'full'] },
  { name: '/login', desc: '登录：选择厂商并输入 API Key' },
  { usage: '/logout [厂商]', name: '/logout', desc: '清除已保存的 API Key' },
  { usage: '/model [id]', name: '/model', desc: '查看或切换模型' },
  { name: '/tools', desc: '列出可用工具' },
  { name: '/workspace', desc: '显示工作区与代码目录' },
  { name: '/session', desc: '显示当前会话信息' },
  { name: '/quit', desc: '退出' },
  { name: '/exit', desc: '退出（/quit 的别名）' },
];

/** 把一行输入解析成命令名与参数。 */
export function parseCommand(line: string): { name: string; args: string[] } | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith('/')) return null;
  const parts = trimmed.slice(1).split(/\s+/).filter(Boolean);
  if (parts.length === 0) return null;
  return { name: parts[0].toLowerCase(), args: parts.slice(1) };
}

export type { MenuOption };