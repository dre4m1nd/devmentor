# -*- coding: utf-8 -*-
"""README 的数字必须和代码实际一致。

曾经的问题：README 说"tests/ 77 个测试"，但那时已经 354 个了——
测试一路加，文档没跟上。读者按文档估算工作量会差 4 倍。

这类问题只在有人真的去数的时候才会暴露，所以用测试锁住。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
README = ROOT / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _count_test_functions() -> int:
    """统计 pytest 用例数（def test_ 的个数）。"""
    total = 0
    for p in (BACKEND / "tests").glob("*.py"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if re.match(r"\s*def test_", line):
                total += 1
    return total


def _count_frontend_tests() -> int:
    """前端测试用 console.log("结果: N 通过") 报数。"""
    total = 0
    for p in (FRONTEND / "test").glob("*.mjs"):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"check\(([^)]+)\)", text)
        total += text.count("check(")
    return total


# ---------------------------------------------------------------- 数字一致

def test_readme_test_count_matches_reality():
    """README 提到的测试数必须接近实际（允许注释写法差异）。"""
    text = _readme()
    actual = _count_test_functions()

    # README 里形如 "364 个用例" 或 "354 个测试"
    numbers = [int(n) for n in re.findall(r"(\d+)\s*个(?:测试|用例)", text)]

    assert numbers, "README 里没有提到测试数量"
    # 至少有一个数字与实际接近（差 20% 以内）
    close = any(abs(n - actual) / actual <= 0.2 for n in numbers)
    assert close, f"README 说 {numbers}，实际后端 {actual} 个"


def test_readme_tool_count_matches_reality():
    text = _readme()
    actual = 11  # 由 build_toolkit 注册

    numbers = [int(n) for n in re.findall(r"(\d+)\s*个工具", text)]
    assert numbers, "README 没提工具数"
    assert any(n == actual for n in numbers), f"README 说 {numbers}，实际 {actual}"


def test_readme_rule_count_matches_reality():
    text = _readme()
    m = re.search(r"规则（(\d+) 条）", text)
    assert m, "README 没提规则数"
    assert int(m.group(1)) == 9, "规则数应是 9 条"


def test_readme_curriculum_count():
    text = _readme()
    actual = len(list((BACKEND / "devmentor" / "templates" / "curriculum").glob("*.md")))
    assert actual == 8, f"课程数应为 8，实际 {actual}"
    assert "8 篇" in text or "8 篇课程" in text


def test_readme_skill_count():
    actual = len(list((BACKEND / "devmentor" / "templates" / "skills").iterdir()))
    assert actual == 4, f"技能数应为 4，实际 {actual}"


# ---------------------------------------------------------------- 命令可用

def test_readme_documents_current_install_path():
    """README 的安装步骤应是 Python 路线（不是 Java JAR）。"""
    text = _readme()
    install = text[text.find("## 安装"):text.find("## 第一次对话")]
    assert "pip install" in install
    assert "java -jar" not in install


def test_readme_mentions_legacy_dir():
    text = _readme()
    assert "legacy/" in text
