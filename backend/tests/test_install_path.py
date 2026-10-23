# -*- coding: utf-8 -*-
"""安装路径：README 承诺的命令必须真的能跑。

曾经的真实问题：README 开头写"敲 devmentor 就能开始"，
但安装章节教的是 node frontend/dist/cli.js——两者不一致。

更严重的是用户机器上 ~/.devmentor/ 还是重构前装的 Java 版
（jar + bin 脚本），PATH 里的 devmentor 指向那个废弃 JAR。
也就是说：用户按 README 装完新版本，敲 devmentor 跑的却是旧代码。

这组测试锁住安装路径的自洽。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- 承诺与路径一致

def test_readme_opening_claim_matches_install_command():
    """README 开头说"敲 devmentor"，安装步骤就必须真的装出这个命令。"""
    text = _readme()

    # 开头承诺
    assert "devmentor" in text[:500], "README 开头应提到 devmentor 命令"

    # 安装章节必须调用安装脚本（而不是只给手动路径）
    install = text[text.find("## 安装"):text.find("#### 手动安装")]
    assert "install.ps1" in install or "install.sh" in install, (
        "安装章节应提供一键安装脚本"
    )


def test_install_scripts_exist():
    for name in ("install.ps1", "install.sh"):
        assert (ROOT / name).is_file(), f"缺少 {name}"


def test_install_script_writes_devmentor_command():
    """安装脚本必须创建 devmentor 启动器，而不只是装依赖。"""
    for name in ("install.ps1", "install.sh"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "devmentor" in text, f"{name} 没有创建 devmentor 命令"

        # 必须指向当前版本的前端入口
        assert "frontend" in text and "cli.js" in text, (
            f"{name} 的启动器应指向 frontend/dist/cli.js（而不是旧 JAR）"
        )

        # 不该再引用 Java 版 JAR
        assert "devmentor.jar" not in text, f"{name} 仍在引用废弃的 Java JAR"
        assert "mvn" not in text.lower(), f"{name} 仍在调用 Maven"


@pytest.mark.parametrize("name", ["install.ps1", "install.sh"])
def test_install_script_adds_to_path(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    assert "PATH" in text, f"{name} 应把启动器目录加入 PATH"


@pytest.mark.parametrize("name", ["install.ps1", "install.sh"])
def test_install_script_checks_toolchain(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    for tool in ("python", "node"):
        assert tool in text.lower(), f"{name} 应检查 {tool}"


def test_install_script_gives_actionable_errors():
    """装失败时要告诉用户下一步做什么，而不是只 exit 1。"""
    for name in ("install.ps1", "install.sh"):
        text = (ROOT / name).read_text(encoding="utf-8")
        # 至少有失败分支
        assert "exit 1" in text
        # 失败提示应含可操作信息
        assert "pip install" in text or "npm install" in text, (
            f"{name} 的失败提示应告诉用户手动跑什么命令"
        )


# ---------------------------------------------------------------- 前端入口存在

def test_frontend_entry_exists():
    """启动器指向的入口必须真实存在。"""
    assert (ROOT / "frontend" / "src" / "cli.tsx").is_file()


def test_no_java_jar_reference_in_readme():
    """README 安装路径不该再出现 java -jar。"""
    text = _readme()
    install = text[text.find("## 安装"):text.find("## 第一次对话")]
    assert "java -jar" not in install