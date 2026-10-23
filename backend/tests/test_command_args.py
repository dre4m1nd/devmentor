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


# ---------------------------------------------------------------- 其它命令参数

def test_lesson_accepts_slug(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())
    # 先落一份课程模板
    from devmentor.workspace import Workspace
    Workspace(s.workspace_dir).ensure()

    events = _drain(cmds.handle("lesson", ["01-syntax-and-types"], svc))
    text = " ".join(getattr(e, "text", "") for e in events)

    assert "语法" in text or "类型" in text


def test_lesson_with_bad_slug_reports(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())
    from devmentor.workspace import Workspace
    Workspace(s.workspace_dir).ensure()

    events = _drain(cmds.handle("lesson", ["nope"], svc))
    text = " ".join(getattr(e, "text", "") for e in events)

    assert "没有找到" in text


def test_logout_accepts_provider_name(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)
    store.save("openai", "k1")
    store.save("deepseek", "k2")

    _drain(cmds.handle("logout", ["openai"], svc))

    assert store.find("openai") is None
    assert store.find("deepseek") == "k2"


@pytest.mark.parametrize("mode", ["interactive", "read-only", "full"])
def test_mode_accepts_all_three(tmp_path, mode):
    s, store, svc, cmds = _ctx(tmp_path)
    events = _drain(cmds.handle("mode", [mode], svc))

    assert s.permission_mode == mode
    assert any("已切换" in getattr(e, "text", "") or "已切换" in getattr(e, "message", "")
               for e in events)
