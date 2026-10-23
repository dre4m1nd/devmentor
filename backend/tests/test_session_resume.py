# -*- coding: utf-8 -*-
"""会话接续与切换：/new 换会话、/reset 清状态。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from devmentor.commands import CommandHandler
from devmentor.config import CredentialStore, Settings
from devmentor.service import AgentService
from devmentor.store import SessionStore


def _make(tmp_path: Path):
    s = Settings()
    s.state_dir = tmp_path / "state"
    store = CredentialStore(tmp_path / "credentials")
    svc = AgentService(s, store)
    cmds = CommandHandler(s, store)
    return s, svc, cmds


def _run(coro):
    return asyncio.run(coro)


def _drain(agen):
    async def collect():
        return [e async for e in agen]

    return _run(collect())


def test_ready_persists_session(tmp_path: Path):
    """会话一分配就落盘，这样一句话不说就退出也能接续。"""
    s, svc, _ = _make(tmp_path)
    _run(svc.ready_event())

    files = list((tmp_path / "state").glob("*.json"))
    assert len(files) == 1
    assert files[0].stem == s.session_id


def test_ready_resumes_latest_session(tmp_path: Path):
    """重启后应接续最近一次会话，而不是每次开新的。"""
    store = SessionStore(tmp_path / "state")
    from agentscope.state import AgentState

    store.save("mentor-20260101-000000", AgentState(session_id="mentor-20260101-000000"))

    s, svc, _ = _make(tmp_path)
    _run(svc.ready_event())

    assert s.session_id == "mentor-20260101-000000"


def test_new_switches_session_and_keeps_old(tmp_path: Path):
    s, svc, cmds = _make(tmp_path)
    _run(svc.ready_event())
    first = s.session_id

    events = _drain(cmds.handle("new", [], svc))
    second = s.session_id

    assert second != first, "/new 应切换到新会话"
    files = {p.stem for p in (tmp_path / "state").glob("*.json")}
    assert first in files, "旧会话应保留"
    assert second in files, "新会话应落盘"
    assert any("已开启新会话" in (e.text if hasattr(e, "text") else "") for e in events)


def test_reset_clears_current_session_file(tmp_path: Path):
    s, svc, cmds = _make(tmp_path)
    _run(svc.ready_event())
    current = s.session_id
    assert (tmp_path / "state" / f"{current}.json").is_file()

    _drain(cmds.handle("reset", [], svc))

    assert not (tmp_path / "state" / f"{current}.json").is_file(), "/reset 应清掉当前会话状态"


def test_new_session_ids_are_unique_within_same_second(tmp_path: Path):
    """连开两个会话不该撞名（id 带微秒后缀）。"""
    s, svc, _ = _make(tmp_path)
    _run(svc.ready_event())

    a = svc.start_new_session()
    b = svc.start_new_session()
    assert a != b


def test_save_state_creates_empty_state_when_no_agent(tmp_path: Path):
    """还没真正对话时也能落一份空状态。"""
    s, svc, _ = _make(tmp_path)
    _run(svc.ready_event())
    svc.reset_agent()  # 丢掉 agent，模拟没对话就退出

    svc.save_state(create_if_missing=True)
    assert (tmp_path / "state" / f"{s.session_id}.json").is_file()


def test_save_state_noop_without_agent_by_default(tmp_path: Path):
    """默认不创建空状态，避免到处留垃圾文件。"""
    s, svc, _ = _make(tmp_path)
    s.session_id = "manual"
    svc.save_state()
    assert not (tmp_path / "state").exists() or not list((tmp_path / "state").glob("*.json"))
