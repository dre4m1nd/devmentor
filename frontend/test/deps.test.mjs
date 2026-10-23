/**
 * 前端依赖检查：声明的包都要真的被 import。
 *
 * 曾经声明过 zod，但代码里零引用。多余依赖会增大安装体积，
 * 也让读者误以为项目用了它。
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

let passed = 0;
let failed = 0;

function check(label, cond, extra = '') {
  if (cond) { passed++; console.log('OK   ' + label); }
  else { failed++; console.log('FAIL ' + label + (extra ? '  [' + extra + ']' : '')); }
}

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.tsx?$/.test(p)) out.push(p);
  }
  return out;
}

const pkg = JSON.parse(readFileSync('package.json', 'utf8'));
const deps = Object.keys(pkg.dependencies || {});
const sources = walk('src').map(f => readFileSync(f, 'utf8')).join('\n');

// 1. 每个声明的运行时依赖都要被 import
for (const dep of deps) {
  const used = new RegExp(`from ['"]${dep}(/[^'"]*)?['"]`).test(sources);
  check(`依赖 ${dep} 被使用`, used, used ? '' : '零引用');
}

// 2. 不该出现已知的未使用包
check('没有 zod 这类未使用依赖', !deps.includes('zod'));

// 3. 核心依赖必须在
for (const required of ['ink', 'react']) {
  check(`核心依赖 ${required} 存在`, deps.includes(required));
}

// 4. devDependencies 不与 dependencies 重复
const devDeps = Object.keys(pkg.devDependencies || {});
const overlap = deps.filter(d => devDeps.includes(d));
check('runtime 与 dev 依赖不重复', overlap.length === 0, overlap.join(','));

console.log('');
console.log('结果: ' + passed + ' 通过, ' + failed + ' 失败');
process.exit(failed > 0 ? 1 : 0);
