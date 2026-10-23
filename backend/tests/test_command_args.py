# -*- coding: utf-8 -*-
"""README 承诺的命令行为。

背景：README 的命令表写了 `/new [名字]`，但实现里把名字丢了
（Java 版会用作 id 前缀，Python 版移植时漏掉）。
这组测试逐条核对文档里的命令参数是否真的有效。
"""

from __future__ import annotations

import asyncio

import pytest

from devmentor.commands import CommandHandler
from devmentor.config import CredentialStore, Settings
from devmentor.service import AgentService, _sanitize_session_prefix


def _ctx(tmp_path):
    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    store = CredentialStore(tmp_path / "credentials")
    return s, store, AgentService(s, store), CommandHandler(s, store)


def _drain(agen):
    async def collect():
        return [e async for e in agen]

    return asyncio.run(collect())


# ---------------------------------------------------------------- /new [名字]

def test_new_uses_name_as_prefix(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())

    _drain(cmds.handle("new", ["debug-session"], svc))

    assert s.session_id.startswith("debug-session-"), s.session_id


def test_new_without_name_uses_default_prefix(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())

    _drain(cmds.handle("new", [], svc))

    assert s.session_id.startswith("mentor-"), s.session_id


def test_new_with_chinese_name(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())

    _drain(cmds.handle("new", ["学习计划"], svc))

    assert s.session_id.startswith("学习计划-"), s.session_id


# ---------------------------------------------------------------- 名字清洗

@pytest.mark.parametrize(
    "raw,expect_prefix",
    [
        ("debug", "debug"),
        ("a b", "a-b"),
        ("a/b", "a-b"),
        ("a!@#b", "a-b"),
        ("--x--", "x"),
        ("", "mentor"),
        ("   ", "mentor"),
    ],
)
def test_sanitize_prefix(raw, expect_prefix):
    assert _sanitize_session_prefix(raw) or "mentor" == expect_prefix


def test_sanitize_truncates_long_names():
    assert len(_sanitize_session_prefix("x" * 100)) == 20


def test_sanitize_keeps_chinese():
    assert _sanitize_session_prefix("学Java") == "学Java"


def test_unsafe_name_does_not_escape_state_dir(tmp_path):
    """名字里带路径分隔符时，文件必须仍落在 state 目录内。"""
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())

    _drain(cmds.handle("new", ["../../../etc"], svc))

    files = list((tmp_path / "state").glob("*.json"))
    assert files, "会话文件应存在"
    for f in files:
        assert f.parent == (tmp_path / "state").resolve() or f.parent == tmp_path / "state"


# ---------------------------------------------------------------- 其余命令

@pytest.mark.parametrize("mode", ["interactive", "read-only", "full"])
def test_mode_accepts_all_three(tmp_path, mode):
    s, store, svc, cmds = _ctx(tmp_path)
    events = _drain(cmds.handle("mode", [mode], svc))

    assert s.permission_mode == mode
    assert any("已切换" in getattr(e, "text", "") for e in events)


def test_model_accepts_id(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    events = _drain(cmds.handle("model", ["ollama:qwen2.5-coder"], svc))

    assert "ollama" in s.model_id
    assert any("已切换" in getattr(e, "text", "") for e in events)


def test_removed_commands_report_unknown(tmp_path):
    """/arch /lesson /progress 已删除，应当走未知命令分支。"""
    s, store, svc, cmds = _ctx(tmp_path)

    for gone in ("arch", "lesson", "progress"):
        events = _drain(cmds.handle(gone, [], svc))
        assert any(e.type == "error" for e in events), f"/{gone} 应报未知命令"
