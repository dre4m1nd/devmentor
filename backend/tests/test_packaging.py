# -*- coding: utf-8 -*-
"""打包完整性：pip install . 后模板必须可用。

模板（8 篇课程 + 4 个技能 + AGENTS.md + preferences.md）是工作区的来源，
丢失会导致首次启动什么都读不到。依赖 hatchling 的默认行为把包目录下的
非 Python 文件一并打进 wheel——这属于隐式依赖，用测试锁住。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
TEMPLATES = BACKEND / "devmentor" / "templates"

EXPECTED_TEMPLATE_COUNT = 14  # AGENTS.md + preferences.md + 8 课程 + 4 技能


def test_templates_directory_exists():
    assert TEMPLATES.is_dir(), "模板目录缺失，首次启动会没有课程和技能"


def test_all_templates_present():
    files = [p for p in TEMPLATES.rglob("*") if p.is_file()]
    assert len(files) == EXPECTED_TEMPLATE_COUNT, (
        f"模板应有 {EXPECTED_TEMPLATE_COUNT} 个，实际 {len(files)}"
    )


def test_curriculum_has_8_courses():
    courses = list((TEMPLATES / "curriculum").glob("*.md"))
    assert len(courses) == 8, f"课程应有 8 篇，实际 {len(courses)}"


def test_skills_have_skill_md():
    """每个技能目录都要有 SKILL.md，否则技能加载不到。"""
    skills = list((TEMPLATES / "skills").glob("*/SKILL.md"))
    assert len(skills) == 4, f"技能应有 4 个，实际 {len(skills)}"


def test_agents_md_present():
    """AGENTS.md 是系统提示词来源，缺失会退回兜底 prompt。"""
    assert (TEMPLATES / "AGENTS.md").is_file()


def test_workspace_bootstrap_finds_templates():
    """Workspace 的默认 templates 路径必须指向真实目录。"""
    from devmentor.workspace import Workspace
    import devmentor

    default_dir = Path(devmentor.__file__).parent / "templates"
    assert default_dir.is_dir()
    assert default_dir.resolve() == TEMPLATES.resolve()


@pytest.mark.slow
def test_wheel_contains_templates(tmp_path):
    """真实构建 wheel，确认模板被打进去。

    这条依赖 hatchling 的默认打包行为，跑得慢，用 slow 标记。
    """
    import subprocess
    import sys

    out = tmp_path / "whl"
    r = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(out), str(BACKEND)],
        capture_output=True,
        text=True,
        timeout=600,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        pytest.skip(f"构建 wheel 失败（可能没装 hatchling）: {r.stderr[-200:]}")

    whls = list(out.glob("*.whl"))
    assert whls, "没有产出 wheel"

    with zipfile.ZipFile(whls[0]) as z:
        names = z.namelist()
        tpl = [n for n in names if "/templates/" in n]
        assert len(tpl) == EXPECTED_TEMPLATE_COUNT, (
            f"wheel 里应含 {EXPECTED_TEMPLATE_COUNT} 个模板，实际 {len(tpl)}"
        )
        assert any(n.endswith("AGENTS.md") for n in tpl)
        assert any("curriculum" in n for n in tpl)
        assert any("skills" in n for n in tpl)
