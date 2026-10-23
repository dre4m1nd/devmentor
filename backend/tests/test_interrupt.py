# -*- coding: utf-8 -*-
"""中断处理：interrupt 请求必须被响应且能恢复。

之前的问题：协议里定义了 interrupt 类型，前端也留了 SIGINT 处理，
但 server 主循环根本不认这个请求，发过来被静默忽略；而 cli.tsx 的
SIGINT 直接 process.exit(0)，用户想停下回答会把整个程序关掉。
"""

from __future__ import annotations

import asyncio

from devmentor.config import CredentialStore, Settings
from devmentor.service import AgentService


def _svc(tmp_path):
    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    return s, AgentService(s, CredentialStore(tmp_path / "creds"))


def test_interrupt_clears_pending_confirm(tmp_path):
    """中断要清掉待确认的工具调用，否则下次提问会带着残留继续跑。"""
    s, svc = _svc(tmp_path)
    svc._pending_confirm = [{"name": "java_run_snippet"}]

    svc.interrupt()

    assert svc._pending_confirm == []


def test_interrupt_saves_state(tmp_path):
    """中断时把状态落盘，避免丢进度。"""
    s, svc = _svc(tmp_path)
    asyncio.run(svc.ready_event())
    sid = s.session_id
    (tmp_path / "state" / f"{sid}.json").unlink()

    svc.interrupt()

    assert (tmp_path / "state" / f"{sid}.json").is_file(), "中断后应保存会话状态"


def test_interrupt_on_fresh_service_does_not_crash(tmp_path):
    """还没建 Agent 就中断也不能炸。"""
    s, svc = _svc(tmp_path)
    svc.interrupt()  # 不应抛异常


def test_interrupt_is_idempotent(tmp_path):
    s, svc = _svc(tmp_path)
    svc._pending_confirm = [{"name": "x"}]

    svc.interrupt()
    svc.interrupt()
    svc.interrupt()

    assert svc._pending_confirm == []


def test_service_still_usable_after_interrupt(tmp_path):
    """中断后还能正常提问（不会带着坏状态）。"""
    s, svc = _svc(tmp_path)
    asyncio.run(svc.ready_event())
    svc.interrupt()

    # 没有凭据，ask 应该给出 MissingCredential 而不是崩在残留状态上
    async def collect():
        return [e async for e in svc.ask("你好")]

    events = asyncio.run(collect())
    kinds = [e.type for e in events]

    assert "turn.end" in kinds, "ask 必须发 turn.end，否则前端卡死"
    assert "error" in kinds
