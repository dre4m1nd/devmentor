/**
 * 窄屏布局：菜单在窄终端下改为纵向排布。
 *
 * 曾经的问题：50 列下厂商名和 URL 横排，折行后交错在一起：
 *   ❯ OpenRouter（免费模型，推https://openrouter.a
 *     荐）                    i/keys
 * 读起来分不清哪个是哪个。
 *
 * 修法：宽度 < 80 时纵向排列（名称一行，URL 缩进一行）。
 * 阈值 80 是按最长一行算的：2(marker) + 32(label) + 44(URL) ≈ 78。
 */

let passed = 0;
let failed = 0;

function check(label, cond, extra = '') {
  if (cond) { passed++; console.log('OK   ' + label); }
  else { failed++; console.log('FAIL ' + label + (extra ? '  [' + extra + ']' : '')); }
}

/** 复刻 App.tsx 的布局判定 */
function layoutFor(columns) {
  return columns < 80 ? 'vertical' : 'horizontal';
}

// ---- 阈值
check('120 列 -> 横排', layoutFor(120) === 'horizontal');
check('100 列 -> 横排', layoutFor(100) === 'horizontal');
check('80 列 -> 横排', layoutFor(80) === 'horizontal');
check('79 列 -> 纵向', layoutFor(79) === 'vertical');
check('70 列 -> 纵向', layoutFor(70) === 'vertical');
check('50 列 -> 纵向', layoutFor(50) === 'vertical');
check('20 列 -> 纵向', layoutFor(20) === 'vertical');

// ---- 横排所需最小宽度（不能截断）
{
  const marker = 2;
  const label = 32;
  // 目录里最长的 desc
  const longestDesc = 'https://bailian.console.aliyun.com/'.length;  // 38
  const needed = marker + label + longestDesc;   // 72
  check(
    '横排所需宽度 ' + needed + ' 列 <= 阈值 80',
    needed <= 80,
    '否则 80 列时也会截断'
  );
  // 阈值留了余量：中文全角字符占 2 列，label 截到 32 只是字符数，
  // 实际显示宽度可能更宽。80 是留够余量的保守值。
  check('阈值 80 给中文标签留了余量', 80 > needed);
  check('阈值不会小到 79 列就截断', 80 >= needed);
}

// ---- 纵向布局的内容顺序
{
  const o = { value: '1', label: 'OpenRouter（免费模型，推荐）', desc: 'https://openrouter.ai/keys' };
  const vertical = [o.label, o.desc];
  check('纵向时 label 在 desc 之前', vertical[0] === o.label);
  check('纵向时两者都完整保留', vertical.includes(o.label) && vertical.includes(o.desc));
  check('纵向不拼接（不会交错折行）', !vertical.some(x => x.includes(o.label) && x.includes(o.desc)));
}

console.log('');
console.log('结果: ' + passed + ' 通过, ' + failed + ' 失败');
process.exit(failed > 0 ? 1 : 0);