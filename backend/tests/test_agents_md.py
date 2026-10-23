# -*- coding: utf-8 -*-
"""AGENTS.md 的一致性：引用的工具存在、能力边界与代码相符。

AGENTS.md 是给模型的系统提示词。它一旦提到不存在的工具或能力，
模型就会调用失败或许下做不到的承诺——用户看到的是"导师不听话"。
这组测试保证文档与实现同步。

2026-10 裁掉了课程教学、技能、架构评审之后，工具只剩两个：
java_run_snippet 与 java_compile_check。这里的断言随之收窄。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from devmentor.agent import build_toolkit
from devmentor.config import Settings
from devmentor.workspace import Workspace

TEMPLATES = Path(__file__).resolve().parents[1] / "devmentor" / "templates"
AGENTS_MD = TEMPLATES / "AGENTS.md"

#: 反引号里出现的非工具标识符（Java 语法关键字）
NON_TOOL_TOKENS = {"record", "stream", "var", "switch"}

#: 裁剪后应当不存在的旧工具。留着说明文档或代码没改干净。
REMOVED_TOOLS = {
    "curriculum_list",
    "curriculum_read",
    "progress_read",
    "progress_record",
    "arch_scan",
    "arch_findings",
    "arch_dependencies",
    "arch_file_profile",
    "arch_read_source",
}


def _toolkit():
    s = Settings()
    s.workspace = Path(tempfile.mkdtemp()) / "ws"
    s.state_dir = Path(tempfile.mkdtemp()) / "st"
    ws = Workspace(s.workspace_dir)
    ws.ensure()
    return build_toolkit(s, ws)


def _registered_tools() -> set[str]:
    tk = _toolkit()
    names = set()
    for g in tk.tool_groups:
        for t in (getattr(g, "tools", []) or []):
            if getattr(t, "name", None):
                names.add(t.name)
    return names


# ---------------------------------------------------------------- 工具引用

def test_agents_md_referenced_tools_all_exist():
    """AGENTS.md 提到的每个工具都必须真的注册了。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    referenced = set(re.findall(r"`([a-z][a-z_]{3,})`", text)) - NON_TOOL_TOKENS
    registered = _registered_tools()

    missing = referenced - registered
    assert not missing, f"AGENTS.md 提到但未注册的工具: {sorted(missing)}"


def test_every_registered_tool_is_documented():
    """注册的工具都应该在 AGENTS.md 里说明，否则模型不知道何时用它。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    documented = set(re.findall(r"`([a-z][a-z_]{3,})`", text))
    undocumented = _registered_tools() - documented
    assert not undocumented, f"这些工具未在 AGENTS.md 中说明: {sorted(undocumented)}"


def test_only_two_tools_registered():
    """裁剪后只应剩两个工具。多出来说明有没清理干净的功能。"""
    registered = _registered_tools()
    assert registered == {"java_run_snippet", "java_compile_check"}, (
        f"实际注册: {sorted(registered)}"
    )


def test_agents_md_does_not_mention_removed_tools():
    """提示词不该再提已删掉的功能，否则模型会去调用不存在的工具。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    still_there = [t for t in sorted(REMOVED_TOOLS) if t in text]
    assert not still_there, f"AGENTS.md 仍提到已删除的工具: {still_there}"


def test_no_arch_or_curriculum_modules():
    """模块已物理删除，不该还能 import。"""
    with pytest.raises(ModuleNotFoundError):
        __import__("devmentor.arch")
    with pytest.raises(ModuleNotFoundError):
        __import__("devmentor.tools.architecture")
    with pytest.raises(ModuleNotFoundError):
        __import__("devmentor.tools.curriculum")


# ---------------------------------------------------------------- 能力边界

def test_agents_md_states_java_only_boundary():
    """能力边界必须在提示词里写清楚，否则模型会对其它语言编造结论。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "只能验证 Java" in text or "只解析" in text
    assert "没有执行过" in text or "未执行" in text, (
        "必须要求模型对未运行的代码明确声明"
    )


# ---------------------------------------------------------------- 提示词结构

def test_agents_md_is_teaching_only():
    """裁剪后只剩教学模式，不该再提架构评审。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "架构评审" not in text
    assert "教学模式" not in text  # 单一模式，不需要模式判断
    assert "先诊断" in text


def test_agents_md_states_verification_rule():
    """核心承诺：声称能跑的代码必须先真跑。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "java_run_snippet" in text
    assert "真跑" in text or "真正编译" in text


def test_agents_md_requires_examples_runnable():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "最小可运行示例" in text
