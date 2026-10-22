# -*- coding: utf-8 -*-
"""斜杠命令测试：命令表、解析、已删除命令。"""

from devmentor.commands import (
    DEFINITIONS,
    TOOL_NAMES,
    argument_candidates,
    command_names,
    parse,
)


def test_command_names_are_unique():
    names = command_names()
    assert len(names) == len(set(names))


def test_removed_commands_are_gone():
    """/plan /lang /verbose /think /help 已删除。

    前四个只改状态不改变行为；/help 的信息已被前端 / 菜单覆盖。
    """
    names = set(command_names())
    for gone in ("/plan", "/lang", "/verbose", "/think", "/help"):
        assert gone not in names, f"{gone} 应已删除"


def test_core_commands_exist():
    names = set(command_names())
    for expected in ("/new", "/reset", "/login", "/logout", "/arch", "/lesson",
                     "/progress", "/mode", "/model", "/session", "/workspace",
                     "/tools", "/quit"):
        assert expected in names, f"{expected} 应保留"


def test_quit_and_exit_both_present():
    """/exit 是 /quit 的别名，两个都要在菜单里可见。"""
    names = set(command_names())
    assert "/quit" in names and "/exit" in names


def test_argument_candidates_only_for_mode():
    assert argument_candidates("mode") == ["interactive", "read-only", "full"]
    assert argument_candidates("arch") == []
    # 已删除的命令不该再返回候选
    assert argument_candidates("plan") == []
    assert argument_candidates("lang") == []


def test_parse_simple():
    assert parse("/mode") == ("mode", [])
    assert parse("/quit") == ("quit", [])


def test_parse_with_args():
    assert parse("/mode read-only") == ("mode", ["read-only"])
    assert parse("/arch D:\\proj") == ("arch", ["D:\\proj"])


def test_parse_rejects_non_command():
    assert parse("hello") is None
    assert parse("") is None


def test_every_definition_has_usage_and_desc():
    """帮助信息不能缺字段，否则前端菜单会显示空行。"""
    for name, usage, desc in DEFINITIONS:
        assert name.startswith("/"), f"{name} 应以 / 开头"
        assert usage and desc, f"{name} 缺 usage 或 desc"


def test_tool_names_match_registry():
    """TOOL_NAMES 必须与真实注册的工具一致，否则 /tools 会撒谎。"""
    from devmentor.agent import build_toolkit
    from devmentor.config import Settings
    from devmentor.workspace import Workspace

    s = Settings()
    tk = build_toolkit(s, Workspace(s.workspace_dir))
    registered = set()
    for group in tk.tool_groups:
        for t in getattr(group, "tools", []) or []:
            if getattr(t, "name", None):
                registered.add(t.name)

    assert set(TOOL_NAMES) == registered, (
        f"/tools 与实际注册不符: 多 {set(TOOL_NAMES) - registered} "
        f"少 {registered - set(TOOL_NAMES)}"
    )
