# -*- coding: utf-8 -*-
"""架构工具的语言边界：只解析 Java，对其它语言要给明确提示而不是误导。"""

from __future__ import annotations

from pathlib import Path

from devmentor.tools import ArchitectureTools


def _make(root: Path) -> ArchitectureTools:
    return ArchitectureTools(root, root / "reports")


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_file_profile_rejects_non_java_with_clear_message(tmp_path: Path):
    """传 .py 时要说明"只支持 Java"，不能说"可能被排除目录规则跳过"。"""
    _write(tmp_path, "src/main/java/A.java", "package a; class A { void f() {} }")
    _write(tmp_path, "app.py", "print('hi')")

    out = _make(tmp_path).file_profile("app.py")

    assert "只解析" in out or "只支持" in out
    assert ".java" in out
    # 不能给出误导性解释
    assert "排除目录" not in out


def test_file_profile_works_for_java(tmp_path: Path):
    _write(tmp_path, "src/main/java/com/acme/A.java",
           "package com.acme;\nclass A {\n  void f() {}\n}\n")

    out = _make(tmp_path).file_profile("src/main/java/com/acme/A.java")

    assert "A.java" in out
    assert "行数" in out
    assert "方法数" in out


def test_file_profile_missing_file(tmp_path: Path):
    out = _make(tmp_path).file_profile("nope.java")
    assert "不存在" in out


def test_read_source_works_for_any_language(tmp_path: Path):
    """read_source 是纯文本读取，不该有语言限制。"""
    _write(tmp_path, "app.py", "x = 1\ny = 2\n")

    out = _make(tmp_path).read_source("app.py")

    assert "1  x = 1" in out
    assert "2  y = 2" in out


def test_read_source_does_not_require_java(tmp_path: Path):
    _write(tmp_path, "notes.md", "# 标题\n正文\n")
    out = _make(tmp_path).read_source("notes.md")
    assert "# 标题" in out


def test_arch_scan_on_project_without_java(tmp_path: Path):
    """纯 Python 项目下应明确说没找到 .java，而不是崩掉。"""
    _write(tmp_path, "app.py", "print(1)")

    out = _make(tmp_path).scan()
    assert "没有找到 .java" in out
