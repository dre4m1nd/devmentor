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
    """README 若写了测试数，必须与实际接近。

    README 现在不写具体数字（写死就会过期——曾经写着 77，实际已 364）。
    所以这条只做"写了就必须对"的检查。
    """
    text = _readme()
    actual = _count_test_functions()
    numbers = [int(n) for n in re.findall(r"(\d+)\s*个(?:测试|用例)", text)]

    for n in numbers:
        assert abs(n - actual) / actual <= 0.2, (
            f"README 说 {n} 个测试，实际 {actual} 个"
        )

def test_readme_tool_count_matches_reality():
    text = _readme()
    actual = 2  # java_run_snippet / java_compile_check

    numbers = [int(n) for n in re.findall(r"(\d+)\s*个工具", text)]
    assert numbers, "README 没提工具数"
    assert any(n == actual for n in numbers), f"README 说 {numbers}，实际 {actual}"


def test_no_curriculum_or_skills():
    """课程与技能已删除，模板里不该再有，README 也不该宣传。"""
    tpl = BACKEND / "devmentor" / "templates"
    assert not (tpl / "curriculum").exists()
    assert not (tpl / "skills").exists()

    text = _readme()
    for gone in ("课程", "技能", "curriculum", "skills", "架构评审", "架构规则"):
        assert gone not in text, f"README 仍在宣传已删除的功能: {gone}"


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