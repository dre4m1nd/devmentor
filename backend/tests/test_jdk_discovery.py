# -*- coding: utf-8 -*-
"""JDK 发现与版本选择。

两个曾经的问题：
1. 只扫 ~/.jdks（IntelliJ 路径），Linux/macOS 的标准位置全找不到
2. 多版本时选最新的（如 26），而教学基线是 17，语法/API 会对不上
"""

from __future__ import annotations

from pathlib import Path

import pytest

import devmentor.config as cfg


# ---------------------------------------------------------------- 版本名解析

@pytest.mark.parametrize(
    "name,expected",
    [
        ("openjdk-17.0.20.1", 17),
        ("openjdk-26.0.2.1", 26),
        ("java-17-openjdk-amd64", 17),
        ("java-21-openjdk-amd64", 21),
        ("temurin-17.jdk", 17),
        ("jdk-21.0.1", 21),
        ("jdk1.8", None),      # 8 太旧，且 1.8 的 1 不该被当成主版本
        ("Home", None),        # 没有数字
        ("jdk", None),
    ],
)
def test_version_from_name(name: str, expected):
    assert cfg._version_from_name(name) == expected


# ---------------------------------------------------------------- 平台路径发现

def _fake_jdk(root: Path, name: str, exe: str = "java") -> Path:
    binp = root / name / "bin"
    binp.mkdir(parents=True, exist_ok=True)
    (binp / exe).write_text("#!/bin/sh\n", encoding="utf-8")
    return root / name


def test_discovers_linux_jvm_root(tmp_path: Path, monkeypatch):
    """/usr/lib/jvm/java-17-openjdk-amd64 这类路径要能被发现。"""
    jvm = tmp_path / "usr" / "lib" / "jvm"
    _fake_jdk(jvm, "java-17-openjdk-amd64")
    _fake_jdk(jvm, "java-21-openjdk-amd64")

    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", (str(jvm),))
    dirs = cfg._discover_jdk_dirs()

    assert any("java-17-openjdk-amd64" in str(d) for d in dirs)
    assert any("java-21-openjdk-amd64" in str(d) for d in dirs)


def test_discovers_macos_contents_home(tmp_path: Path, monkeypatch):
    """macOS 的 *.jdk/Contents/Home 才是真正的 JAVA_HOME。"""
    jvms = tmp_path / "JavaVirtualMachines"
    jdk = jvms / "temurin-17.jdk"
    home = jdk / "Contents" / "Home" / "bin"
    home.mkdir(parents=True)
    (home / "java").write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", (str(jvms),))
    dirs = cfg._discover_jdk_dirs()

    assert jdk in dirs
    assert jdk / "Contents" / "Home" in dirs, "Contents/Home 也要作为候选"


def test_missing_roots_do_not_crash(tmp_path: Path, monkeypatch):
    """根目录不存在时安静跳过。"""
    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", (str(tmp_path / "nope"),))
    assert isinstance(cfg._discover_jdk_dirs(), list)


# ---------------------------------------------------------------- 版本优先级

def test_prefers_teaching_baseline_over_newer(tmp_path: Path, monkeypatch):
    """同时有 17 和 26 时，17 必须排前面。"""
    jdks = tmp_path / ".jdks"
    _fake_jdk(jdks, "openjdk-17.0.20.1")
    _fake_jdk(jdks, "openjdk-26.0.2.1")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", ())
    monkeypatch.delenv("DEVMENTOR_JAVA_HOME", raising=False)
    monkeypatch.delenv("JAVA_HOME", raising=False)

    names = [p.name for p in cfg._jdk_candidates()]
    assert names.index("openjdk-17.0.20.1") < names.index("openjdk-26.0.2.1")


def test_explicit_home_wins(tmp_path: Path, monkeypatch):
    """DEVMENTOR_JAVA_HOME 永远排第一。"""
    explicit = tmp_path / "my-jdk-21"
    monkeypatch.setenv("DEVMENTOR_JAVA_HOME", str(explicit))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", ())

    assert cfg._jdk_candidates()[0] == explicit


def test_old_jdks_are_filtered_out(tmp_path: Path, monkeypatch):
    """比 17 旧的 JDK 不该进候选。"""
    jdks = tmp_path / ".jdks"
    _fake_jdk(jdks, "jdk1.8")
    _fake_jdk(jdks, "openjdk-17.0.20.1")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", ())
    monkeypatch.delenv("DEVMENTOR_JAVA_HOME", raising=False)
    monkeypatch.delenv("JAVA_HOME", raising=False)

    names = [p.name for p in cfg._jdk_candidates()]
    assert "jdk1.8" not in names
    assert "openjdk-17.0.20.1" in names


def test_java_home_appended_last(tmp_path: Path, monkeypatch):
    """JAVA_HOME 是兜底，排在自动发现的后面。"""
    jdks = tmp_path / ".jdks"
    _fake_jdk(jdks, "openjdk-17.0.20.1")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(cfg, "_COMMON_JDK_ROOTS", ())
    monkeypatch.delenv("DEVMENTOR_JAVA_HOME", raising=False)
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "env-jdk"))

    cands = cfg._jdk_candidates()
    assert cands[-1] == tmp_path / "env-jdk"
