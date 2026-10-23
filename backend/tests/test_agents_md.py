# -*- coding: utf-8 -*-
"""AGENTS.md 的一致性：引用的工具存在、技能可加载、能力边界与代码相符。

AGENTS.md 是给模型的系统提示词。它一旦提到不存在的工具或能力，
模型就会调用失败或许下做不到的承诺——用户看到的是"导师不听话"。
这组测试保证文档与实现同步。
"""

from __future__ import annotations

import asyncio
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


# ---------------------------------------------------------------- 技能

def test_skills_load_from_templates():
    tk = _toolkit()
    skills = asyncio.run(tk.tool_groups[0].list_skills())
    assert len(skills) == 4


def test_every_skill_has_valid_frontmatter():
    """SKILL.md 的 frontmatter 必须能被 YAML 解析并含 name/description。"""
    yaml = pytest.importorskip("yaml")

    for md in sorted((TEMPLATES / "skills").glob("*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        assert text.startswith("---"), f"{md.parent.name} 缺 frontmatter"

        parts = text.split("---", 2)
        assert len(parts) >= 3
        data = yaml.safe_load(parts[1])

        assert isinstance(data, dict), f"{md.parent.name} frontmatter 不是映射"
        assert data.get("name"), f"{md.parent.name} 缺 name"
        assert data.get("description"), f"{md.parent.name} 缺 description"
        # 描述要足够具体，否则模型无法判断何时该用这个技能
        assert len(data["description"]) >= 20, f"{md.parent.name} 描述太短"


def test_skill_names_match_directory_names():
    yaml = pytest.importorskip("yaml")

    for md in sorted((TEMPLATES / "skills").glob("*/SKILL.md")):
        data = yaml.safe_load(md.read_text(encoding="utf-8").split("---", 2)[1])
        assert data["name"] == md.parent.name, (
            f"目录名 {md.parent.name} 与 frontmatter name {data['name']} 不一致"
        )


# ---------------------------------------------------------------- 能力边界

def test_agents_md_states_java_only_boundary():
    """能力边界必须在提示词里写清楚，否则模型会对其它语言编造结论。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "只解析" in text or "只支持" in text
    assert ".java" in text
    assert "不要假装" in text or "不要凭印象" in text


def test_arch_scan_matches_documented_behavior():
    """文档说纯非 Java 项目返回"没有找到 .java 文件"，实现要一致。"""
    s = Settings()
    s.workspace = Path(tempfile.mkdtemp()) / "ws"
    s.state_dir = Path(tempfile.mkdtemp()) / "st"
    s.project_root = Path(tempfile.mkdtemp())
    ws = Workspace(s.workspace_dir)
    ws.ensure()
    (s.project_root / "app.py").write_text("print(1)", encoding="utf-8")

    tk = build_toolkit(s, ws)
    scan = next(
        t for g in tk.tool_groups for t in (getattr(g, "tools", []) or [])
        if getattr(t, "name", None) == "arch_scan"
    )
    # arch_scan 是同步函数，直接返回字符串
    result = scan._func()
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)

    assert "没有找到 .java" in result


# ---------------------------------------------------------------- 提示词结构

def test_agents_md_defines_two_modes():
    """两种工作模式（教学 / 架构评审）必须都在提示词里定义。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "教学模式" in text
    assert "架构评审" in text


def test_agents_md_states_evidence_rule():
    """架构评审的铁律：先 arch_scan 再下结论。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "arch_scan" in text
    assert "铁律" in text or "不要在没有调用" in text