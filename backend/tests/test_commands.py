# -*- coding: utf-8 -*-
"""斜杠命令测试：命令表、解析、已删除命令。"""

from devmentor.commands import (
    DEFINITIONS,
    TOOL_NAMES,
    argument_candidates,
    command_names,
    help_text,
    parse,
)


def test_help_text_lists_all_commands():
    text = help_text()
    for name, _, _ in DEFINITIONS:
        assert name in text


def test_command_names_are_unique():
    names = command_names()
    assert len(names) == len(set(names))


def test_removed_commands_are_gone():
    """/plan /lang /verbose /think 是纯摆设（不改变任何行为），已删除。"""
    names = set(command_names())
    for gone in ("/plan", "/lang", "/verbose", "/think"):
        assert gone not in names, f"{gone} 应已删除"


def test_login_and_logout_exist():
    names = set(command_names())
    assert "/login" in names
    assert "/logout" in names


def test_argument_candidates_only_for_mode():
    assert argument_candidates("mode") == ["interactive", "read-only", "full"]
    assert argument_candidates("arch") == []
    assert argument_candidates("plan") == []  # 已删除


def test_parse_simple():
    assert parse("/help") == ("help", [])


def test_parse_with_args():
    assert parse("/mode read-only") == ("mode", ["read-only"])


def test_parse_rejects_non_command():
    assert parse("hello") is None
    assert parse("") is None


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
