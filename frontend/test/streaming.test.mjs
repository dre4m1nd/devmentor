/**
 * 流式渲染回归测试。
 *
 * 曾经的问题：text.delta 依赖 last.streaming 判断"是否已在流式中"，
 * 但条目上从未设置该字段，导致每个 delta 都 push 一条新记录——
 * 一段回复会变成几十条重复条目铺满屏幕（实测 20 个 delta 出 20 条）。
 *
 * 修法：用 streamingIdx ref 记住当前流式条目的下标，原地更新。
 * 这个脚本复刻那段逻辑，防止再退化。
 */

let passed = 0;
let failed = 0;

function check(label, cond, extra = '') {
  if (cond) { passed++; console.log('OK   ' + label); }
  else { failed++; console.log('FAIL ' + label + (extra ? '  [' + extra + ']' : '')); }
}

function makeStreamer() {
  let entries = [];
  let streamBuf = '';
  let streamingIdx = -1;

  return {
    get entries() { return entries; },
    delta(text) {
      streamBuf += text;
      const idx = streamingIdx;
      if (idx >= 0 && idx < entries.length && entries[idx]?.kind === 'assistant') {
        const next = entries.slice();
        next[idx] = { kind: 'assistant', text: streamBuf };
        entries = next;
      } else {
        streamingIdx = entries.length;
        entries = [...entries, { kind: 'assistant', text: streamBuf }];
      }
    },
    flush() {
      const text = streamBuf.trim();
      streamBuf = '';
      const idx = streamingIdx;
      streamingIdx = -1;
      if (!text) return;
      if (idx >= 0 && idx < entries.length && entries[idx]?.kind === 'assistant') return;
      entries = [...entries, { kind: 'assistant', text }];
    },
    push(e) { entries = [...entries, e]; },
  };
}

// 1. 一次流式回复只产生一条
{
  const s = makeStreamer();
  '这是一段回复'.split('').forEach(c => s.delta(c));
  check('20+ delta 只产生 1 条记录', s.entries.length === 1, '实际 ' + s.entries.length);
  check('内容是完整拼接', s.entries[0].text === '这是一段回复', s.entries[0].text);
}

// 2. flush 不重复追加
{
  const s = makeStreamer();
  '你好'.split('').forEach(c => s.delta(c));
  s.flush();
  check('flush 后仍为 1 条', s.entries.length === 1, '实际 ' + s.entries.length);
}

// 3. 多轮对话正确累加
{
  const s = makeStreamer();
  '第一轮'.split('').forEach(c => s.delta(c));
  s.flush();
  '第二轮'.split('').forEach(c => s.delta(c));
  s.flush();
  check('两轮后 2 条', s.entries.length === 2, '实际 ' + s.entries.length);
  check('顺序正确', s.entries[0].text === '第一轮' && s.entries[1].text === '第二轮');
}

// 4. 流式之间插入工具记录，不应串到一起
{
  const s = makeStreamer();
  '前半'.split('').forEach(c => s.delta(c));
  s.flush();
  s.push({ kind: 'tool', name: 'arch_scan', state: 'running' });
  '后半'.split('').forEach(c => s.delta(c));
  s.flush();
  const assistants = s.entries.filter(e => e.kind === 'assistant');
  check('工具记录不打断 assistant', assistants.length === 2, '实际 ' + assistants.length);
  check('后段内容独立', assistants[1].text === '后半', assistants[1]?.text);
}

// 5. 空 flush 不产生垃圾
{
  const s = makeStreamer();
  s.flush();
  check('空 flush 不新增', s.entries.length === 0, '实际 ' + s.entries.length);
}

// 6. 大量 delta 性能（不重建整条历史）
{
  const s = makeStreamer();
  '前缀'.split('').forEach(c => s.delta(c));
  s.flush();
  for (let i = 0; i < 10; i++) s.push({ kind: 'system', text: 'x' });
  const before = s.entries.length;
  '长回复'.repeat(100).split('').forEach(c => s.delta(c));
  s.flush();
  check('历史记录保持不变', s.entries.length === before + 1, '实际 ' + s.entries.length);
}

console.log('');
console.log('结果: ' + passed + ' 通过, ' + failed + ' 失败');
process.exit(failed > 0 ? 1 : 0);
