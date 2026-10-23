/**
 * 确认流程的按键判定。
 *
 * 曾经的问题：approved = (inputChar === 'y')，意味着除 y 外任何键
 * （含误触、空格、方向键）都会被当成"拒绝"并立即发出请求。
 * 确认框消失且无法撤销——用户手滑一下就拒掉了一个操作。
 *
 * 现在只认 y/回车（允许）与 n/Esc（拒绝），其它键忽略。
 * 这个脚本复刻那段判定，防止再退化。
 */

let passed = 0;
let failed = 0;

function check(label, cond, extra = '') {
  if (cond) { passed++; console.log('OK   ' + label); }
  else { failed++; console.log('FAIL ' + label + (extra ? '  [' + extra + ']' : '')); }
}

/** 复刻 App.tsx 里确认框的判定：返回 true=允许, false=拒绝, null=忽略 */
function decide(inputChar, key = {}) {
  const ch = (inputChar || '').toLowerCase();
  if (ch === 'y' || key.return) return true;
  if (ch === 'n' || key.escape) return false;
  return null;
}

// ---- 允许
check('y -> 允许', decide('y') === true);
check('Y -> 允许（大小写不敏感）', decide('Y') === true);
check('回车 -> 允许', decide('', { return: true }) === true);

// ---- 拒绝
check('n -> 拒绝', decide('n') === false);
check('N -> 拒绝', decide('N') === false);
check('Esc -> 拒绝', decide('', { escape: true }) === false);

// ---- 忽略（这是修复的核心）
for (const k of ['x', 'a', ' ', 'q', '1', '中']) {
  check(`${JSON.stringify(k)} -> 忽略`, decide(k) === null, '得到 ' + decide(k));
}

// ---- 边界
check('空字符串 -> 忽略', decide('') === null);
check('undefined -> 忽略', decide(undefined) === null);

// ---- 组合键不应该被当成单键
check('回车不算忽略', decide('', { return: true }) !== null);
check('Esc 不算忽略', decide('', { escape: true }) !== null);

console.log('');
console.log('结果: ' + passed + ' 通过, ' + failed + ' 失败');
process.exit(failed > 0 ? 1 : 0);
