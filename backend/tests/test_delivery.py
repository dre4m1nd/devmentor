# -*- coding: utf-8 -*-
"""交付物检查：项目能否真正交给用户。

前几轮检查了结构、依赖、import、文档数字，这轮补最后一环：
一个开源项目交给别人时需要的东西是否齐全且仍然有效。

发现的过时项：
  .gitattributes 里写着 /mvnw text eol=lf，
  但 mvnw 已随 Java 版归档到 legacy/，路径失效。
  *.cmd 也从多个变成只剩 legacy/bin/devmentor.cmd 一个。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _git_ls(pattern: str) -> list[str]:
    r = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [x for x in r.stdout.splitlines() if x.strip()]


# ---------------------------------------------------------------- 必备交付物

def test_license_exists():
    assert (ROOT / "LICENSE").is_file(), "开源项目必须有 LICENSE"


def test_gitattributes_exists():
    assert (ROOT / ".gitattributes").is_file()


def test_readme_exists():
    assert (ROOT / "README.md").is_file()


def test_gitignore_exists():
    assert (ROOT / ".gitignore").is_file()


# ---------------------------------------------------------------- gitattributes 有效性

def test_gitattributes_paths_exist():
    """.gitattributes 里引用的具体路径必须存在。

    曾经写着 /mvnw，但 mvnw 已归档到 legacy/，规则成了空转。
    """
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("/") and " " in line:
            path = line.split()[0]
            assert (ROOT / path.lstrip("/")).exists(), (
                f".gitattributes 引用了不存在的路径: {path}"
            )


def test_gitattributes_has_no_dead_glob_rules():
    """每个 glob 规则至少要匹配到一个文件，否则是无用规则。"""
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    globs = [
        line.split()[0]
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#") and "*" in line.split()[0]
    ]
    assert globs, "应该有针对文本文件的换行符规则"
    for g in globs:
        assert _git_ls(g), f"规则 {g} 没有匹配任何文件"


# ---------------------------------------------------------------- 换行符约定

def _has_crlf(path: Path) -> bool:
    try:
        return b"\r\n" in path.read_bytes()
    except OSError:
        return False


def test_python_files_use_lf():
    """Python 源码统一 LF，避免跨平台 diff 整个文件。"""
    bad = [f for f in _git_ls("*.py") if _has_crlf(ROOT / f)]
    assert not bad, f"这些 .py 含 CRLF: {bad[:5]}"


def test_ts_files_use_lf():
    bad = [f for f in _git_ls("*.ts") + _git_ls("*.tsx") if _has_crlf(ROOT / f)]
    assert not bad, f"这些 .ts/.tsx 含 CRLF: {bad[:5]}"


def test_cmd_files_use_crlf():
    """cmd 脚本必须是 CRLF，否则 Windows 命令行可能解析出错。"""
    bad = [f for f in _git_ls("*.cmd") if not _has_crlf(ROOT / f)]
    assert not bad, f"这些 .cmd 是 LF: {bad}"


def test_markdown_files_use_lf():
    bad = [f for f in _git_ls("*.md") if _has_crlf(ROOT / f)]
    assert not bad, f"这些 .md 含 CRLF: {bad[:5]}"


# ---------------------------------------------------------------- 安装路径

def test_readme_install_works_with_current_layout():
    """README 的安装命令必须能在当前目录结构下执行。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = readme[readme.find("## 安装"):readme.find("## 第一次对话")]

    assert "pip install" in install
    # backend 与 frontend 都必须存在
    assert (ROOT / "backend").is_dir()
    assert (ROOT / "frontend").is_dir()


def test_no_java_build_files_in_root():
    """根目录不该再出现 Java 构建文件（已归档到 legacy/）。"""
    # install.ps1 / install.sh 是当前版本（Python 路线）的安装脚本，应存在
    for name in ("pom.xml", "src", "bin", ".mvn"):
        assert not (ROOT / name).exists(), f"{name} 应归档到 legacy/"