# -*- coding: utf-8 -*-
"""仓库结构：Java 版已归档，不该被误认为当前实现。

背景：重构为 Python + Node 后，旧的 Java 版（src/ + pom.xml + install 脚本）
一直留在根目录，与新版本并存。新用户看到两套实现会困惑：
到底该装哪个？README 说 pip install，但 install.ps1 装的是 JAR。

现在统一归档到 legacy/，这组测试保证结构不再回退。
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- 根目录结构

@pytest.mark.parametrize("name", ["backend", "frontend", "legacy"])
def test_expected_top_level_dirs_exist(name):
    assert (ROOT / name).is_dir(), f"缺少 {name}/"


@pytest.mark.parametrize("name", ["src", "pom.xml", "bin", ".mvn"])
def test_java_version_artifacts_not_in_root(name):
    """Java 版的构建与启动文件都不该出现在根目录。

    注意 install.ps1 / install.sh 不在此列：重构后它们被重写成
    Python 版的一键安装脚本，是当前版本的交付物，理应留在根目录。
    """
    assert not (ROOT / name).exists(), (
        f"{name} 应归档到 legacy/，放在根目录会让人误以为项目有两个版本"
    )


def test_legacy_contains_java_version():
    legacy = ROOT / "legacy"
    assert (legacy / "java-src").is_dir()
    assert (legacy / "pom.xml").is_file()
    assert (legacy / "install.ps1").is_file()
    assert (legacy / "bin").is_dir()


def test_legacy_has_explanation():
    """归档目录必须有说明，否则读者不知道这些代码还能不能用。"""
    readme = (ROOT / "legacy" / "README.md").read_text(encoding="utf-8")

    assert "不再维护" in readme or "已废弃" in readme
    assert "README.md" in readme  # 指向当前版本说明


# ---------------------------------------------------------------- 当前实现自洽

def test_backend_does_not_reference_legacy_java():
    """Python 端不应依赖归档的 Java 代码。"""
    backend = ROOT / "backend" / "devmentor"
    for py in backend.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        assert "legacy/java-src" not in text, f"{py.name} 引用了归档的 Java 代码"


def test_templates_not_duplicated_from_legacy():
    """当前版本的模板以 backend/devmentor/templates 为准。"""
    current = ROOT / "backend" / "devmentor" / "templates"
    assert current.is_dir()

    assert (current / "AGENTS.md").is_file()
    assert (current / "curriculum").is_dir()
    assert (current / "skills").is_dir()


def test_readme_documents_legacy_dir():
    """README 要说明 legacy/ 是什么，否则目录看起来莫名其妙。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "legacy/" in readme
    assert "目录说明" in readme or "已废弃" in readme


def test_current_install_path_is_python_not_jar():
    """README 的安装步骤应是 Python 路线，不该再让人装 JAR。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    # 安装章节应出现 pip
    install_section = readme[readme.find("## 安装"):readme.find("## 第一次对话")]
    assert "pip install" in install_section
    assert "java -jar" not in install_section