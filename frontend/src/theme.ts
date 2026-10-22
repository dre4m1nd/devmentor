/** 配色与符号。集中管理，方便统一调整视觉。 */

export const theme = {
  brand: 'cyan',
  accent: 'green',
  muted: 'gray',
  danger: 'red',
  warn: 'yellow',
  tool: {
    running: 'cyan',
    success: 'green',
    error: 'red',
    denied: 'yellow',
    interrupted: 'yellow',
  },
} as const;

export const symbols = {
  prompt: '›',
  tool: '⏺',
  result: '↳',
  error: '✖',
  success: '✔',
} as const;
