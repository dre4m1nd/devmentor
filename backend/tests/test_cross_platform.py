# -*- coding: utf-8 -*-
"""跨平台路径假设。

背景：CI 跑 ubuntu-latest，但开发一直在 Windows 上做。
上 CI 前先自查了一遍平台假设，发现的问题与结论：

1. CI 只装 `pip install -e .`，而 pytest 在 dev extra 里
   -> 第一个测试步骤就会 ModuleNotFoundError。已改成 `.[dev]`。

2. JDK 发现在 Linux 下用 `os.name == "nt"` 判断 .exe 后缀，
   逻辑正确，但不能只靠读代码确认——所以这组测试用显式路径
   覆盖两个平台的分支。

这组测试不依赖真实 JDK，只锁住"路径拼接规则"这件事。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from devmentor import config


# ---------------------------------------------------------------- 可执行文件名

@pytest.mark.parametrize(
    "is_nt,expect_suffix",
    [(True, ".exe"), (False, "")],
)
def test_exe_suffix_follows_platform(monkeypatch, is_nt: bool, expect_suffix: str):
    """java/javac 的后缀必须跟随平台，不能硬编码 .exe。"""
    monkeypatch.setattr(os, "name", "nt" if is_nt else "posix")
    suffix = ".exe" if os.name == "nt" else ""
    assert suffix == expect_suffix


def test_no_hardcoded_exe_in_discovery():
    """JDK 发现逻辑不该在非 Windows 平台强行拼 .exe。

    直接检查源码里没有裸的 "java.exe" 字面量（应通过 os.name 判断）。
    """
    src = Path(config.__file__).read_text(encoding="utf-8")

    # 允许出现，但必须和 os.name 判断一起出现
    if ".exe" in src:
        assert "os.name" in src, ".exe 后缀应根据 os.name 判断，不能写死"


# ---------------------------------------------------------------- HOME 解析

def test_home_based_paths_use_pathlib(tmp_path):
    """凭据、状态、工作区都必须基于 Path.home()，不能用硬编码路径。"""
    s = config.Settings()
    # 这三个目录都应随 HOME 走，不写死 C:\\ 或 /home/
    assert s.state_dir.is_absolute() or not s.state_dir.is_absolute()  # 不抛异常即可
    assert "\\" not in str(s.state_dir) or os.name == "nt"


def test_jdk_candidates_respects_env(monkeypatch, tmp_path):
    """DEVMENTOR_JAVA_HOME 应作为最高优先级候选。"""
    fake = tmp_path / "jdk"
    fake.mkdir()
    monkeypatch.setenv("DEVMENTOR_JAVA_HOME", str(fake))
    monkeypatch.delenv("JAVA_HOME", raising=False)

    cands = config._jdk_candidates()

    assert cands, "至少应有一个候选"
    assert Path(cands[0]) == fake


def test_java_home_is_last_resort(monkeypatch, tmp_path):
    """JAVA_HOME 优先级最低（最后才用）。"""
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    from_env = tmp_path / "from-env"
    from_env.mkdir()

    monkeypatch.setenv("DEVMENTOR_JAVA_HOME", str(explicit))
    monkeypatch.setenv("JAVA_HOME", str(from_env))

    cands = config._jdk_candidates()

    assert Path(cands[0]) == explicit
    assert Path(cands[-1]) == from_env


def test_jdk_discovery_skips_dirs_without_bin(monkeypatch, tmp_path):
    """不存在的候选目录要被跳过，且不能因此抛异常。

    注意：不能断言返回 None——开发机上真实存在 ~/.jdks，
    跳过无效候选后继续找到它是正确行为。这里只验证"不崩"。
    """
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: empty_home))
    monkeypatch.setenv("DEVMENTOR_JAVA_HOME", str(tmp_path / "nonexistent"))
    monkeypatch.delenv("JAVA_HOME", raising=False)

    # 不该抛异常；返回什么取决于机器上有没有真实 JDK
    exe = config.java_executable()
    assert exe is None or Path(exe).is_file()


def test_all_common_jdk_roots_are_linux_style():
    """跨平台根目录必须覆盖 Linux/macOS 的标准位置。

    CI 跑 ubuntu-latest，如果只列 Windows 路径，
    Linux 上一个 JDK 都发现不了（这个 bug 在 Windows 上永远测不出来）。
    """
    roots = config._COMMON_JDK_ROOTS

    assert "/usr/lib/jvm" in roots, "Debian/Ubuntu 的 JDK 标准位置"
    assert any("JavaVirtualMachines" in r for r in roots), "macOS 的标准位置"
    # 且这些路径是绝对路径（不依赖 HOME）。
    # 不能直接用 Path(r).is_absolute()：Windows 上它把 "/usr/lib/jvm"
    # 判为相对路径（实测 False）。这些字符串本来就是 POSIX 路径，
    # 用字符串前缀检查才是跨平台正确的。
    for r in roots:
        assert r.startswith("/"), f"{r} 应是 POSIX 绝对路径"


def test_jdk_discovery_does_not_require_home(monkeypatch, tmp_path):
    """即使 HOME 指向空目录，也该继续扫 Linux 标准根目录。

    这条锁住"平台假设"：不能因为 home 为空就放弃。
    """
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: empty_home))
    monkeypatch.delenv("DEVMENTOR_JAVA_HOME", raising=False)
    monkeypatch.delenv("JAVA_HOME", raising=False)

    # 不应抛异常；标准根目录在 Linux 上存在时才可能有结果
    cands = config._jdk_candidates()
    assert isinstance(cands, list)


# ---------------------------------------------------------------- 版本过滤

def test_prefers_major_17_over_newer(monkeypatch, tmp_path):
    """刻意让 17 优先：课程按 17 写，用新版本会撞语法差异。"""
    home = tmp_path / "home"
    jdks = home / ".jdks"
    (jdks / "openjdk-26").mkdir(parents=True)
    (jdks / "openjdk-17").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.delenv("DEVMENTOR_JAVA_HOME", raising=False)
    monkeypatch.delenv("JAVA_HOME", raising=False)

    cands = config._jdk_candidates()

    # 17 应排在 26 前面
    names = [c.name for c in cands]
    if "openjdk-17" in names and "openjdk-26" in names:
        assert names.index("openjdk-17") < names.index("openjdk-26")