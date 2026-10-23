# -*- coding: utf-8 -*-
"""用项目自己的架构分析工具检查自己（dogfooding）。"""
import sys, asyncio, tempfile
from pathlib import Path
sys.path.insert(0, 'D:/Code/devmentor/backend')

from devmentor.arch import analyze

out = []

# 1. 检查后端 Python 代码结构（虽然引擎只解析 Java，但可以看包结构事实）
res = analyze(Path("D:/Code/devmentor"))
out.append("=== 对 Java 版代码的分析（引擎主用途）===")
out.append(f"文件: {res.snapshot.file_count}，测试: {res.snapshot.test_file_count}")
out.append(f"根包: {res.snapshot.root_package}")
out.append("")

from collections import Counter
by_rule = Counter(f.rule for f in res.findings)
out.append("规则命中:")
for rule, n in by_rule.most_common():
    out.append(f"  {rule:20} {n} 条")

out.append("")
out.append("=== 详细 ===")
for f in res.findings:
    out.append(f"[{f.severity.label}][{f.rule}] {f.title[:45]}")

open("_self.txt","w",encoding="utf-8").write(chr(10).join(out))