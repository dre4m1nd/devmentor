# -*- coding: utf-8 -*-
"""工具在异常参数下的边界处理。

起因：审计工具时发现 arch_read_source 的行号只夹了 start，没管 max_lines。
传 max_lines=0 会输出"第 5-4 行"，传负数会输出"第 5--1 行"，
起点超过文件长度则输出"第 100-10 行"——模型拿到这种荒谬范围会讲错内容。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from devmentor.tools import ArchitectureTools, CurriculumTools, ProgressTools


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src/main/java/com/acme").mkdir(parents=True)
    (root / "src/main/java/com/acme/A.java").write_text(
        "package com.acme;\npublic class A { public int f(){ return 1; } }\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture()
def tools(project: Path) -> ArchitectureTools:
    return ArchitectureTools(project, project / "reports")


# ---------------------------------------------------------------- 行号边界

def _first_line(text: str) -> str:
    return text.splitlines()[0] if text else ""


def test_read_source_normal(tools: ArchitectureTools):
    text = tools.read_source("src/main/java/com/acme/A.java", start_line=1, max_lines=2)
    assert "第 1-2 行" in _first_line(text)


def test_read_source_negative_start_clamped(tools: ArchitectureTools):
    text = tools.read_source("src/main/java/com/acme/A.java", start_line=-5, max_lines=2)
    assert "第 1-" in _first_line(text)


@pytest.mark.parametrize("bad_max", [0, -1, -100])
def test_read_source_nonpositive_max_clamped(tools: ArchitectureTools, bad_max: int):
    """max_lines <= 0 时至少要返回一行，不能出现"第 5-4 行"。"""
    text = tools.read_source("src/main/java/com/acme/A.java", start_line=2, max_lines=bad_max)
    first = _first_line(text)

    assert "--" not in first, f"出现负数行号: {first}"
    assert "第 2-2 行" in first or "第 2-1 行" not in first


def test_read_source_start_beyond_eof(tools: ArchitectureTools):
    """起点超出文件长度时给明确提示，而不是输出倒置范围。"""
    text = tools.read_source("src/main/java/com/acme/A.java", start_line=999, max_lines=5)

    assert "超过文件末尾" in text
    assert "--" not in _first_line(text)


def test_read_source_window_past_eof_clamped(tools: ArchitectureTools):
    text = tools.read_source("src/main/java/com/acme/A.java", start_line=2, max_lines=999)
    first = _first_line(text)

    assert "共 2 行" in first
    assert "第 2-2 行" in first


def test_read_source_missing_file(tools: ArchitectureTools):
    assert "不存在" in tools.read_source("nope.java")


def test_read_source_empty_path(tools: ArchitectureTools):
    """空路径解析到目录本身，应报不存在而不是崩。"""
    assert "不存在" in tools.read_source("")


# ---------------------------------------------------------------- 其它工具边界

def test_file_profile_empty_path(tools: ArchitectureTools):
    assert "不存在" in tools.file_profile("")


def test_file_profile_path_traversal(tools: ArchitectureTools):
    """穿越到项目外的文件应报不存在（root 内解析后找不到）。"""
    result = tools.file_profile("../../outside.java")
    assert "不存在" in result


def test_scan_missing_directory(tools: ArchitectureTools):
    assert "不存在" in tools.scan("/nonexistent/path/xyz")


def test_findings_bad_severity(tools: ArchitectureTools):
    result = tools.findings("bogus")
    assert "high / medium / low" in result


def test_curriculum_empty_slug(tmp_path: Path):
    cur = CurriculumTools(tmp_path)
    (tmp_path / "curriculum").mkdir()
    assert "没有找到" in cur.read_course("")


def test_curriculum_path_traversal(tmp_path: Path):
    cur = CurriculumTools(tmp_path)
    (tmp_path / "curriculum").mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("机密", encoding="utf-8")

    result = cur.read_course("../secret")
    assert "机密" not in result


def test_progress_empty_note(tmp_path: Path):
    prog = ProgressTools(tmp_path)
    assert "为空" in prog.record_progress("")
    assert "为空" in prog.record_progress("   ")


# ---------------------------------------------------------------- Java 工具边界

def test_run_snippet_empty_code():
    from devmentor.tools.java_snippet import run_snippet

    result = run_snippet("", timeout_seconds=15)
    assert "Traceback" not in result


def test_compile_check_empty_code():
    from devmentor.tools.java_snippet import compile_check

    result = compile_check("")
    assert "Traceback" not in result
