/**
 * 协议类型定义。与后端 devmentor/protocol.py 一一对应。
 *
 * 这是前后端唯一契约：后端只发语义事件，前端决定怎么画。
 */

export type MenuOption = {
  value: string;
  label: string;
  desc?: string;
};

export type ServerEvent =
  | {
      type: 'ready';
      model: string;
      session: {
        user: string;
        session: string;
        workspace: string;
        project: string;
        permission: string;
        credentials: string;
        bootstrapped: string[];
      };
    }
  | { type: 'text.delta'; text: string }
  | { type: 'thinking.delta'; text: string }
  | { type: 'tool.call'; name: string; input?: Record<string, unknown> }
  | { type: 'tool.result'; name: string; state: string; preview?: string }
  | { type: 'require.confirm'; calls: Record<string, unknown>[] }
  | { type: 'system'; text: string }
  | { type: 'success'; text: string }
  | { type: 'error'; message: string }
  | { type: 'menu'; title: string; options: MenuOption[] }
  | { type: 'turn.end' }
  | { type: 'bye' };

export type ClientRequest =
  | { type: 'ask'; id?: string; text: string }
  | { type: 'command'; id?: string; name: string; args?: string[] }
  | { type: 'confirm'; id?: string; approved: boolean; reason?: string }
  | { type: 'interrupt'; id?: string }
  | { type: 'shutdown'; id?: string };

/** 渲染到屏幕上的单个条目。 */
export type Entry =
  | { kind: 'user'; text: string }
  | { kind: 'assistant'; text: string }
  | { kind: 'thinking'; text: string }
  | { kind: 'tool'; name: string; state: 'running' | 'success' | 'error' | 'denied' | 'interrupted'; preview?: string }
  | { kind: 'system'; text: string }
  | { kind: 'success'; text: string }
  | { kind: 'error'; text: string };
