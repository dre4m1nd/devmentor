# -*- coding: utf-8 -*-
"""登录两段式流程：选厂商 -> 输 Key，以及各取消路径。

这组测试覆盖前端需要配合的三种交互：
  stage 1（选厂商）：空输入 = 取消
  stage 2（等 Key）：空/空白 = 取消，不保存
  正常输入 = 保存并切换模型

之前的验证里一度以为"Esc 会误报登录成功"，实际是测试脚本把多个场景
写进同一沙箱导致的串扰。这里每个用例独立 tmp_path，避免同类误判。
"""

from __future__ import annotations

import asyncio

import pytest

from devmentor.commands import CommandHandler
from devmentor.config import PROVIDERS, CredentialStore, Settings
from devmentor.service import AgentService


def _ctx(tmp_path):
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
    return [
        getattr(e, "text", "") or getattr(e, "message", "")
        for e in events
        if getattr(e, "text", "") or getattr(e, "message", "")
    ]


# ---------------------------------------------------------------- 正常登录

def test_login_with_valid_key_saves_and_switches(tmp_path):
    s, store, svc, cmds = _ctx(tmp_path)

    events = _drain(cmds.apply_login(1, "sk-or-v1-test", svc))

    assert store.find("openai") == "sk-or-v1-test"
    assert s.model_id.startswith("openai:")
    assert any(e.type == "success" for e in events)
    assert (tmp_path / "credentials").is_file()


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n", " \t\n "])
def test_login_with_blank_key_cancels(tmp_path, blank):
    """stage 2 收到空白输入必须取消，且不写文件。"""
    s, store, svc, cmds = _ctx(tmp_path)
    before = s.model_id

    events = _drain(cmds.apply_login(1, blank, svc))

    assert store.find("openai") is None
    assert s.model_id == before
    assert not (tmp_path / "credentials").is_file()
    assert any("已取消" in t for t in _texts(events))
    assert not any(e.type == "success" for e in events), "取消时不该报成功"


def test_login_ollama_needs_no_key(tmp_path):
    """Ollama 免 Key，直接完成。"""
    s, store, svc, cmds = _ctx(tmp_path)
    ollama = next(p for p in PROVIDERS if p.provider == "ollama")

    _drain(cmds.apply_login(ollama.id, "", svc))

    assert s.model_id.startswith("ollama:")
    assert not (tmp_path / "credentials").is_file()


def test_login_invalid_provider_id(tmp_path):
    """无效厂商号必须报错且不改动当前模型。

    这条比 test_commands_isolated 里的同名版本更严格（还校验模型未变），
    所以保留这份，另一份已删。
    """
    s, store, svc, cmds = _ctx(tmp_path)
    before = s.model_id

    events = _drain(cmds.apply_login(999, "k", svc))

    assert any(e.type == "error" for e in events)
    assert s.model_id == before


# ---------------------------------------------------------------- stage 1 取消

def test_login_stage1_blank_cancels(tmp_path):
    """选厂商时按 Esc（前端发空文本）应退出登录流程。"""
    from devmentor.server import Server

    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    srv = Server(s)
    srv._login_stage = 1

    async def collect():
        return [e async for e in srv._dispatch_text("")]

    events = asyncio.run(collect())

    assert srv._login_stage == 0, "空输入应退出登录流程"
    assert any("已取消" in t for t in _texts(events))


def test_login_stage1_invalid_number_stays(tmp_path):
    """序号不合法时留在 stage 1，让用户重输。"""
    from devmentor.server import Server

    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    srv = Server(s)
    srv._login_stage = 1

    async def collect():
        return [e async for e in srv._dispatch_text("99")]

    events = asyncio.run(collect())

    assert srv._login_stage == 1, "无效序号不该退出流程"
    assert any(e.type == "error" for e in events)


def test_login_stage1_valid_number_advances(tmp_path):
    from devmentor.server import Server

    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    srv = Server(s)
    srv._login_stage = 1

    async def collect():
        return [e async for e in srv._dispatch_text("1")]

    events = asyncio.run(collect())

    assert srv._login_stage == 2, "选完厂商应进入等 Key 阶段"
    assert any("API Key" in t for t in _texts(events))


# ---------------------------------------------------------------- 隔离

def test_cancel_does_not_leak_to_next_attempt(tmp_path):
    """一次取消后再登录，不会带上上次的残留状态。"""
    s, store, svc, cmds = _ctx(tmp_path)

    _drain(cmds.apply_login(1, "", svc))          # 取消
    _drain(cmds.apply_login(2, "sk-deepseek-x", svc))   # 再登录另一个厂商

    assert store.find("deepseek") == "sk-deepseek-x"
    assert store.find("openai") is None
    assert s.model_id.startswith("deepseek:")