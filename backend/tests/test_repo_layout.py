# -*- coding: utf-8 -*-
"""仓库结构：不该再出现重构前的 Java 版。

背景：重构为 Python + Node 后，旧的 Java 版（src/ + pom.xml + install 脚本）
一直留在根目录，与新版本并存。新用户看到两套实现会困惑：
到底该装哪个？README 说 pip install，但 install.ps1 装的是 JAR。

Java 版曾短暂归档到 legacy/，2026-10 已整体删除——
重构完成，没有保留价值，只会让人以为项目有两个版本。

这组测试保证结构不再回退。
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- 根目录结构

@pytest.mark.parametrize("name", ["backend", "frontend"])
def test_expected_top_level_dirs_exist(name):
    assert (ROOT / name).is_dir(), f"缺少 {name}/"


@pytest.mark.parametrize(
    "name",
    ["src", "pom.xml", "bin", ".mvn", "legacy", "target", ".idea"],
)
def test_java_version_artifacts_not_in_root(name):
    """Java 版的构建与启动文件都不该出现在根目录。

    注意 install.ps1 / install.sh 不在此列：重构后它们被重写成
    Python 版的一键安装脚本，是当前版本的交付物，理应留在根目录。
    """
    assert not (ROOT / name).exists(), (
        f"{name} 是 Java 版遗留，不该出现在根目录"
    )


def test_no_java_source_anywhere():
    """整个仓库不该还有 .java 源码（架构分析只解析用户的代码，不带自己的）。"""
    java_files = list(ROOT.rglob("*.java"))
    # 只排除 node_modules
    java_files = [f for f in java_files if "node_modules" not in str(f)]
    assert not java_files, f"仍有 Java 源码: {[str(f) for f in java_files[:5]]}"


# ---------------------------------------------------------------- 当前实现自洽

def test_backend_has_no_legacy_references():
    """Python 端不该引用已删除的 Java 代码。"""
    backend = ROOT / "backend" / "devmentor"
    for py in backend.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        assert "legacy" not in text, f"{py.name} 仍引用 legacy/"


def test_templates_are_minimal():
    """课程与技能已删，模板只剩 AGENTS.md 与 preferences.md。"""
    current = ROOT / "backend" / "devmentor" / "templates"
    assert current.is_dir()
    assert (current / "AGENTS.md").is_file()
    assert (current / "preferences.md").is_file()
    assert not (current / "curriculum").exists()
    assert not (current / "skills").exists()


def test_readme_does_not_mention_legacy():
    """README 不该再提 legacy/，那个目录已经不存在。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "legacy" not in readme


def test_current_install_path_is_python_not_jar():
    """README 的安装步骤应是 Python 路线，不该再让人装 JAR。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    # 安装章节应出现 pip
    install_section = readme[readme.find("## 安装"):readme.find("## 第一次对话")]
    assert "pip install" in install_section
    assert "java -jar" not in install_section
