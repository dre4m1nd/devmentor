# -*- coding: utf-8 -*-
"""命令处理器测试：全部走临时目录，不碰用户的真实凭据/状态文件。

这是从一次事故里补的：验证脚本曾用 CredentialStore() 默认路径，
把测试用的假 key 写进了 ~/.devmentor/credentials，污染了真实环境。
这里确保命令层的测试全部可隔离注入。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from devmentor.commands import CommandHandler
from devmentor.config import CredentialStore, Settings
from devmentor.service import AgentService


def _ctx(tmp_path: Path):
    """构造完全隔离的上下文：凭据与状态都落在 tmp_path。"""
    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    store = CredentialStore(tmp_path / "credentials")
    svc = AgentService(s, store)
    cmds = CommandHandler(s, store)
    return s, store, svc, cmds


def _drain(agen):
    async def collect():
        return [e async for e in agen]

    return asyncio.run(collect())


def _texts(events):
    return [getattr(e, "text", "") for e in events if getattr(e, "text", "")]


# ---------------------------------------------------------------- login

def test_login_saves_to_injected_store_not_home(tmp_path: Path):
    """登录必须写进注入的 store，不能碰 ~/.devmentor/credentials。"""
    s, store, svc, cmds = _ctx(tmp_path)

    # Ollama 无需 Key，走完整登录路径但不写凭据
    _drain(cmds.apply_login(6, "", svc))

    assert s.model_id.startswith("ollama:")
    # 真实主目录的文件不应被创建/修改
    home_creds = Path.home() / ".devmentor" / "credentials"
    if home_creds.exists():
        assert "ollama" not in home_creds.read_text(encoding="utf-8")


def test_login_with_key_persists_and_switches_model(tmp_path: Path):
    s, store, svc, cmds = _ctx(tmp_path)

    _drain(cmds.apply_login(1, "sk-or-v1-test-only", svc))

    assert store.find("openai") == "sk-or-v1-test-only"
    assert s.model_id.startswith("openai:")
    # 只写临时文件
    assert (tmp_path / "credentials").is_file()


def test_login_without_key_cancels(tmp_path: Path):
    """需要 Key 的厂商，空 Key 视为取消。"""
    s, store, svc, cmds = _ctx(tmp_path)
    before = s.model_id

    _drain(cmds.apply_login(1, "   ", svc))

    assert s.model_id == before
    assert store.find("openai") is None


# ---------------------------------------------------------------- logout

def test_logout_removes_only_target(tmp_path: Path):
    s, store, svc, cmds = _ctx(tmp_path)
    store.save("openai", "k1")
    store.save("deepseek", "k2")

    _drain(cmds.handle("logout", ["openai"], svc))

    assert store.find("openai") is None
    assert store.find("deepseek") == "k2"


def test_logout_on_empty_store_is_friendly_not_error(tmp_path: Path):
    """一条凭据都没有时，提示比报错更合适。"""
    s, store, svc, cmds = _ctx(tmp_path)
    events = _drain(cmds.handle("logout", [], svc))

    assert any("没有已保存的凭据" in t for t in _texts(events))
    assert not any(e.type == "error" for e in events)


def test_logout_unknown_provider_errors_when_store_not_empty(tmp_path: Path):
    """有凭据但目标不存在时才算错误。"""
    s, store, svc, cmds = _ctx(tmp_path)
    store.save("openai", "k1")

    events = _drain(cmds.handle("logout", ["nope"], svc))
    assert any(e.type == "error" for e in events)


# ---------------------------------------------------------------- 会话

def test_new_session_writes_into_tmp_state_dir(tmp_path: Path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())
    first = s.session_id

    _drain(cmds.handle("new", [], svc))

    assert s.session_id != first
    files = {p.stem for p in (tmp_path / "state").glob("*.json")}
    assert first in files
    assert s.session_id in files


def test_reset_removes_current_state_file(tmp_path: Path):
    s, store, svc, cmds = _ctx(tmp_path)
    asyncio.run(svc.ready_event())
    current = s.session_id
    assert (tmp_path / "state" / f"{current}.json").is_file()

    _drain(cmds.handle("reset", [], svc))
    assert not (tmp_path / "state" / f"{current}.json").exists()


# ---------------------------------------------------------------- 其它

def test_workspace_command_mentions_injected_paths(tmp_path: Path):
    s, store, svc, cmds = _ctx(tmp_path)
    texts = _texts(_drain(cmds.handle("workspace", [], svc)))
    joined = " ".join(texts)
    assert str(tmp_path) in joined


def test_unknown_command_reports_error(tmp_path: Path):
    s, store, svc, cmds = _ctx(tmp_path)
    events = _drain(cmds.handle("bogus", [], svc))
    assert any(e.type == "error" for e in events)