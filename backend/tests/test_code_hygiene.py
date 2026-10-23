# -*- coding: utf-8 -*-
"""代码卫生：不该留下未使用的 import。

重构时常见的情况：某个函数被移除后，它的 import 忘了删。
这类残留不影响运行，但会让读者以为模块依赖了某些东西，
也会让 IDE 的查找引用产生噪音。

实测清理过 15 处（agent.py 4 个、service.py 5 个、server.py 2 个、
arch/model.py 1 个、tools/java_snippet.py 1 个，外加一些同行多余的名字）。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "devmentor"


def _py_files():
    return [p for p in PKG.rglob("*.py") if "__pycache__" not in str(p)]


def test_all_modules_parse():
    """所有模块语法正确——这是下面所有检查的前提。"""
    for p in _py_files():
        ast.parse(p.read_text(encoding="utf-8"))


def test_no_unused_imports():
    """每个 import 的名字都要在文件其余部分出现。"""
    problems = []

    for p in _py_files():
        text = p.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        lines = text.splitlines()

        for node in ast.walk(tree):
            # from __future__ import annotations 是编译指令，不算未使用
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue

            if isinstance(node, ast.ImportFrom):
                names = [(a.asname or a.name) for a in node.names]
            elif isinstance(node, ast.Import):
                names = [(a.asname or a.name.split(".")[0]) for a in node.names]
            else:
                continue

            start = node.lineno
            end = node.end_lineno or start
            # 排除 import 语句本身所在的行
            rest = "\n".join(
                l for i, l in enumerate(lines, 1) if i < start or i > end
            )

            for nm in names:
                if nm == "*":
                    continue
                if not re.search(r"\b" + re.escape(nm) + r"\b", rest):
                    problems.append(f"{p.relative_to(PKG)}:{start} 未使用 {nm}")

    assert not problems, "存在未使用的 import:\n" + "\n".join(problems)


def test_no_star_imports():
    """星号导入会让依赖关系不可追踪。"""
    for p in _py_files():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for a in node.names:
                    assert a.name != "*", f"{p.name} 使用了星号导入"


def test_no_todo_markers():
    """TODO/FIXME 要么解决，要么记进 issue，不该留在代码里。"""
    markers = ("TODO", "FIXME", "XXX", "HACK")
    found = []

    for p in _py_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in markers:
                if m in line and "#" in line:
                    found.append(f"{p.relative_to(PKG)}:{i} {m}")
                    break

    assert not found, "存在未处理的标记:\n" + "\n".join(found)


def test_no_debug_breakpoints():
    """breakpoint() / pdb 不该留在提交里。"""
    bad = []
    for p in _py_files():
        text = p.read_text(encoding="utf-8")
        for pat in ("breakpoint(", "import pdb", "pdb.set_trace"):
            if pat in text:
                bad.append(f"{p.relative_to(PKG)} 含 {pat}")
    assert not bad, "\n".join(bad)


def test_no_unused_private_functions():
    """私有函数（下划线开头）应该在包内至少被调用一次。"""
    all_src = "\n".join(p.read_text(encoding="utf-8") for p in _py_files())
    unused = []

    for p in _py_files():
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            name = node.name
            if not name.startswith("_") or name.startswith("__"):
                continue
            # 定义处算 1 次，调用处再加
            if len(re.findall(r"\b" + re.escape(name) + r"\b", all_src)) <= 1:
                unused.append(f"{p.relative_to(PKG)}:{node.lineno} {name}")

    assert not unused, "未使用的私有函数:\n" + "\n".join(unused)
