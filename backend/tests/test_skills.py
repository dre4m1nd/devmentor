# -*- coding: utf-8 -*-
"""技能加载：必须真的能被 Toolkit 解析，而不只是文件存在。

Round 1 曾误判"已接入"——只检查了 SKILL.md 文件存在，没验证加载结果。
实际上 LocalSkillLoader 默认不扫子目录，list_skills() 返回 0 个。
这组测试锁住"真的加载出来"。
"""

from __future__ import annotations

import asyncio

from devmentor.agent import build_toolkit
from devmentor.config import Settings
from devmentor.workspace import Workspace


def _skills():
    s = Settings()
    ws = Workspace(s.workspace_dir)
    ws.ensure()
    tk = build_toolkit(s, ws)

    async def collect():
        return await tk.tool_groups[0].list_skills()

    return asyncio.run(collect())


def test_toolkit_loads_all_skills():
    skills = _skills()
    assert len(skills) == 4, f"应加载 4 个技能，实际 {len(skills)}"


def test_skill_names_are_expected():
    names = {getattr(s, "name", None) for s in _skills()}
    assert names == {
        "java-architecture-review",
        "java-code-review",
        "java-debug-coach",
        "java-exercise-designer",
    }


def test_skills_have_descriptions():
    """技能没有描述就不会出现在模型看到的技能清单里。"""
    for sk in _skills():
        desc = getattr(sk, "description", "") or ""
        assert desc.strip(), f"{getattr(sk, 'name', '?')} 缺 description"


def test_no_skills_dir_does_not_crash(tmp_path):
    """工作区没有 skills 目录时应正常构建 Toolkit（只是没有技能）。"""
    s = Settings()
    s.workspace = tmp_path / "emptyws"
    tk = build_toolkit(s, Workspace(s.workspace_dir))

    async def collect():
        return await tk.tool_groups[0].list_skills()

    assert asyncio.run(collect()) == []
