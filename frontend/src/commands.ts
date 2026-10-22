import type { MenuOption } from './types.js';

export type CommandDef = {
  name: string;
  desc: string;
  /** 固定参数取值，用于二级补全 */
  args?: string[];
};

/**
 * 命令表。与后端 devmentor/commands.py 的 DEFINITIONS 对应。
 *
 * 前端保留一份是为了：补全菜单能立即响应（不必等后端），
 * 且参数候选能在本地算出来。缺任何命令都不会破坏功能——
 * 命令最终都发给后端执行，前端只负责补全体验。
 */
export const COMMANDS: CommandDef[] = [
  { name: '/help', desc: '显示帮助' },
  { name: '/new', desc: '开启新会话' },
  { name: '/reset', desc: '清空当前会话上下文' },
  { name: '/mode', desc: '切换权限档位', args: ['interactive', 'read-only', 'full'] },
  { name: '/plan', desc: '切换 plan 模式', args: ['on', 'off'] },
  { name: '/arch', desc: '架构评审：静态分析当前项目' },
  { name: '/lesson', desc: '列出或阅读课程' },
  { name: '/progress', desc: '查看学习进度' },
  { name: '/lang', desc: '切换讲解语言', args: ['zh', 'en'] },
  { name: '/login', desc: '登录：选择厂商并输入 API Key' },
  { name: '/logout', desc: '清除已保存的 API Key' },
  { name: '/model', desc: '查看或切换模型' },
  { name: '/tools', desc: '列出可用工具' },
  { name: '/workspace', desc: '显示工作区与代码目录' },
  { name: '/session', desc: '显示当前会话信息' },
  { name: '/verbose', desc: '切换工具输出全量/摘要' },
  { name: '/think', desc: '切换是否显示推理过程' },
  { name: '/quit', desc: '退出' },
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
