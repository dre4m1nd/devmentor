# -*- coding: utf-8 -*-
"""回归测试：登录状态机、确认流程类型、前后端命令一致性。"""

from __future__ import annotations

import json

import pytest

from devmentor.commands import DEFINITIONS, command_names


# ---------------------------------------------------------------- 命令表

def test_exit_is_visible_in_menu():
    """/exit 是 /quit 的别名，必须出现在菜单里，否则成了隐藏命令。"""
    assert "/exit" in command_names()


def test_frontend_and_backend_commands_match():
    """前端命令表必须与后端一致。

    不一致的后果：前端列出了但后端不认（点了报未知命令），
    或后端有但前端不显示（用户不知道有这个命令）。
    """
    from pathlib import Path

    fe_path = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "commands.ts"
    )
    if not fe_path.is_file():
        pytest.skip("前端源码不在预期位置")

    import re

    text = fe_path.read_text(encoding="utf-8")
    fe_names = {m for m in re.findall(r"name: '(\/[a-z]+)'", text)}
    be_names = set(command_names())

    assert fe_names == be_names, (
        f"仅前端有: {fe_names - be_names}；仅后端有: {be_names - fe_names}"
    )


def test_every_command_has_desc():
    """desc 不能为空，否则菜单右侧是空白。"""
    for name, _usage, desc in DEFINITIONS:
        assert desc.strip(), f"{name} 缺少说明"


# ---------------------------------------------------------------- 登录状态机

def test_login_stage_accepts_slash_prefixed_reply():
    """前端在登录阶段把序号当命令发来（"1" 变成 "/1"）。

    server._dispatch_text 必须剥掉前缀再交给登录状态机，
    否则会报"未知命令 /1"，登录永远完不成。
    """
    from devmentor.server import Server

    srv = Server()
    srv._login_stage = 1

    import asyncio

    events = []

    async def collect():
        async for ev in srv._dispatch_text("/1"):
            events.append(ev)

    asyncio.run(collect())

    kinds = [e.type for e in events]
    # 不应出现"未知命令"
    for e in events:
        if e.type == "error":
            assert "未知命令" not in e.message, "登录阶段不应把序号当命令"
    # 应当推进到等待 Key 的阶段
    assert srv._login_stage == 2, f"应进入等 Key 阶段，实际 {srv._login_stage}"
    assert "system" in kinds


def test_login_nonexistent_provider_keeps_stage():
    from devmentor.server import Server
    import asyncio

    srv = Server()
    srv._login_stage = 1
    events = []

    async def collect():
        async for ev in srv._dispatch_text("99"):
            events.append(ev)

    asyncio.run(collect())
    assert srv._login_stage == 1, "无效序号应停留在选厂商阶段"
    assert any(e.type == "error" for e in events)


# ---------------------------------------------------------------- 确认流程

def test_confirm_result_accepts_raw_tool_call_block():
    """ConfirmResult.tool_call 要求真实 ToolCallBlock，不是 dict。

    之前 _pending_confirm 存的是 _as_dict() 的结果，导致构造时
    ValidationError，确认流程一用就崩。
    """
    from agentscope.event._event import ConfirmResult
    from agentscope.message._block import ToolCallBlock

    blk = ToolCallBlock(
        type="tool_call", id="t1", name="java_run_snippet", input=json.dumps({})
    )
    result = ConfirmResult(confirmed=True, tool_call=blk, rules=None)

    assert result.confirmed is True
    assert result.tool_call.name == "java_run_snippet"


def test_confirm_result_rejects_plain_dict():
    """锁定这个约束：传 dict 必须失败，避免有人改回旧写法。"""
    from agentscope.event._event import ConfirmResult

    with pytest.raises(Exception):
        ConfirmResult(confirmed=True, tool_call={"name": "x"}, rules=None)
