# -*- coding: utf-8 -*-
"""打包完整性：pip install . 后模板必须可用。

模板（AGENTS.md + preferences.md）是工作区的来源，丢失会导致首次启动
读不到系统提示词、退回兜底 prompt。依赖 hatchling 的默认行为把包目录下的
非 Python 文件一并打进 wheel——这属于隐式依赖，用测试锁住。

2026-10 裁掉了课程（8 篇）与技能（4 个），模板从 14 个降到 2 个。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
TEMPLATES = BACKEND / "devmentor" / "templates"

EXPECTED_TEMPLATE_COUNT = 2  # AGENTS.md + preferences.md


def test_templates_directory_exists():
    assert TEMPLATES.is_dir(), "模板目录缺失，首次启动会没有系统提示词"


def test_all_templates_present():
    files = [p for p in TEMPLATES.rglob("*") if p.is_file()]
    assert len(files) == EXPECTED_TEMPLATE_COUNT, (
        f"模板应有 {EXPECTED_TEMPLATE_COUNT} 个，实际 {len(files)}"
    )


def test_no_curriculum_or_skills_templates():
    """课程与技能已删除，模板目录里不该再有它们。"""
    assert not (TEMPLATES / "curriculum").exists(), "curriculum 已删"
    assert not (TEMPLATES / "skills").exists(), "skills 已删"


def test_agents_md_present():
    """AGENTS.md 是系统提示词来源，缺失会退回兜底 prompt。"""
    assert (TEMPLATES / "AGENTS.md").is_file()


def test_agents_md_has_no_removed_tools():
    """打包出去的提示词不能提已删除的工具。"""
    text = (TEMPLATES / "AGENTS.md").read_text(encoding="utf-8")
    for gone in ("arch_scan", "curriculum_list", "progress_record"):
        assert gone not in text, f"AGENTS.md 仍提到 {gone}"


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
