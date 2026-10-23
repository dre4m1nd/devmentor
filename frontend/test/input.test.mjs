/**
 * 输入框的文本处理。
 *
 * 覆盖用户实际会输入的各种内容：中文、emoji、符号、连续空格、
 * 反斜杠路径、超长文本。这些都不该被改写或截断。
 *
 * 复刻 Prompt.tsx 里的输入累积逻辑（含换行处理）。
 */

let passed = 0;
let failed = 0;

function check(label, cond, extra = '') {
  if (cond) { passed++; console.log('OK   ' + label); }
  else { failed++; console.log('FAIL ' + label + (extra ? '  [' + extra + ']' : '')); }
}

/** 复刻 Prompt 的输入累积：遇到换行就提交，否则追加 */
function feed(current, inputChar) {
  const nl = inputChar.search(/[\r\n]/);
  if (nl >= 0) {
    const head = inputChar.slice(0, nl);
    return { value: '', submitted: (current + head).trim() };
  }
  return { value: current + inputChar, submitted: null };
}

function typeAll(text) {
  let cur = '';
  for (const ch of text) {
    const r = feed(cur, ch);
    if (r.submitted !== null) return { value: '', submitted: r.submitted };
    cur = r.value;
  }
  return { value: cur, submitted: null };
}

// ---- 内容保真
const cases = {
  '中文': '你好世界',
  'emoji': '你好👋🌍',
  '符号': 'a+b=c&d?e#f',
  '连续空格': 'hello   world',
  '反斜杠路径': 'C:\\Users\\test',
  '引号': '他说"你好"',
  'JSON 片段': '{"key": "value"}',
  '代码': 'if (a > b) { return a; }',
};

for (const [label, text] of Object.entries(cases)) {
  const r = typeAll(text);
  check(label + ' 原样保留', r.value === text, JSON.stringify(r.value?.slice(0, 20)));
}

// ---- 换行提交
{
  const r = feed('你好', '\n');
  check('换行触发提交', r.submitted === '你好');
  check('提交后清空输入', r.value === '');
}

{
  const r = feed('前缀', '后缀\n剩余');
  check('行内换行截断到换行前', r.submitted === '前缀后缀', JSON.stringify(r.submitted));
}

// ---- 空白处理
{
  const r = feed('  ', '\n');
  check('纯空白提交被 trim 为空', r.submitted === '');
}

// ---- 超长
{
  const long = 'x'.repeat(1000);
  const r = typeAll(long);
  check('1000 字符不截断', r.value.length === 1000, '实际 ' + r.value.length);
}

// ---- 特殊：Tab 作为普通字符（粘贴场景）
{
  const r = typeAll('a\tb');
  check('粘贴的 Tab 作为字符保留', r.value === 'a\tb');
}

console.log('');
console.log('结果: ' + passed + ' 通过, ' + failed + ' 失败');
process.exit(failed > 0 ? 1 : 0);
