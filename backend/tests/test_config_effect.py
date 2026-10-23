# -*- coding: utf-8 -*-
"""配置项是否真的生效。

诞生背景：Round 1 从 Java 版移植 Settings 时，有几个字段只定义、没接线：
  enable_shell   —— 只定义，任何地方都没用（AgentScope 也没有 shell 工具）
  language       —— 只从环境变量读进来，从未影响提示词
  max_iters      —— 只定义，实际用的是 AgentScope 默认的 50 轮

这组测试保证"能配的字段确实起作用"，而不是写在那里好看。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import devmentor.agent as A
from devmentor.config import CredentialStore, Settings
from devmentor.workspace import Workspace


def _agent(tmp_path: Path, **overrides):
    s = Settings()
    s.workspace = tmp_path / "ws"
    s.state_dir = tmp_path / "st"
    for k, v in overrides.items():
        setattr(s, k, v)
    with patch.object(A, "build_model", return_value=object()):
        return A.build_agent(s, Workspace(s.workspace_dir), CredentialStore(tmp_path / "c"))


def _react_config(agent):
    for attr in ("react_config", "_react_config"):
        if hasattr(agent, attr):
            return getattr(agent, attr)
    return None


def _system_prompt(agent) -> str:
    for attr in ("system_prompt", "_system_prompt"):
        v = getattr(agent, attr, None)
        if isinstance(v, str):
            return v
    return ""


# ---------------------------------------------------------------- max_iters

def test_max_iters_reaches_react_config(tmp_path):
    """配置的轮数必须传到 ReActConfig，否则用户改了不生效。"""
    agent = _agent(tmp_path, max_iters=7)
    rc = _react_config(agent)

    assert rc is not None, "Agent 上没有 react_config"
    assert rc.max_iters == 7


def test_max_iters_default_is_24(tmp_path):
    agent = _agent(tmp_path)
    assert _react_config(agent).max_iters == 24


# ---------------------------------------------------------------- language

def test_language_zh_has_no_english_override(tmp_path):
    agent = _agent(tmp_path, language="zh")
    assert "Language override" not in _system_prompt(agent)


def test_language_en_adds_english_instruction(tmp_path):
    agent = _agent(tmp_path, language="en")
    prompt = _system_prompt(agent)
    assert "Language override" in prompt
    assert "English" in prompt


def test_language_is_case_insensitive(tmp_path):
    assert "Language override" in _system_prompt(_agent(tmp_path, language="EN"))


def test_language_en_keeps_original_agents_md(tmp_path):
    """加语言指令不能把原有人设覆盖掉。"""
    agent = _agent(tmp_path, language="en")
    prompt = _system_prompt(agent)
    assert len(prompt) > 100, "原人设内容应保留"
    assert prompt.rstrip().endswith("\n") or "Language override" in prompt


# ---------------------------------------------------------------- enable_shell

def test_enable_shell_field_is_gone(tmp_path):
    """AgentScope 没有 shell 工具，这个字段是 Java 版遗留，已删除。"""
    assert not hasattr(Settings(), "enable_shell"), (
        "enable_shell 是从没被使用的死字段，不该存在"
    )


# ---------------------------------------------------------------- env 覆盖

def test_env_overrides_more_fields(tmp_path, monkeypatch):
    """workspace / state_dir / max_iters 也应能用环境变量覆盖。"""
    monkeypatch.setenv("DEVMENTOR_WORKSPACE", str(tmp_path / "custom-ws"))
    monkeypatch.setenv("DEVMENTOR_STATE_DIR", str(tmp_path / "custom-st"))
    monkeypatch.setenv("DEVMENTOR_MAX_ITERS", "11")

    s = Settings.from_env()

    assert s.workspace == tmp_path / "custom-ws"
    assert s.state_dir == tmp_path / "custom-st"
    assert s.max_iters == 11


def test_invalid_max_iters_env_falls_back(monkeypatch):
    """环境变量写错不该让程序起不来。"""
    monkeypatch.setenv("DEVMENTOR_MAX_ITERS", "not-a-number")
    s = Settings.from_env()
    assert s.max_iters == 24  # 保持默认


@pytest.mark.parametrize(
    "var,field",
    [
        ("DEVELOPMENT_MODEL_ID", "model_id"),
        ("DEVELOPMENT_BASE_URL", "base_url"),
        ("DEVMENTOR_LANGUAGE", "language"),
        ("DEVMENTOR_PERMISSION_MODE", "permission_mode"),
        ("DEVMENTOR_PROJECT_ROOT", "project_root"),
    ],
)
def test_documented_env_vars_are_read(tmp_path, monkeypatch, var, field):
    """README 里写到的环境变量都得真的被读取。"""
    monkeypatch.setenv(var, "test-value")
    s = Settings.from_env()
    value = getattr(s, field)
    assert value is not None and str(value) != ""
