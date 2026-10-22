# -*- coding: utf-8 -*-
"""权限档位测试：三档必须真的产生不同行为。

这是安全功能，不能只改提示文案。
"""

from agentscope.permission import PermissionBehavior

from devmentor.agent import _permission_for, build_toolkit
from devmentor.config import Settings
from devmentor.workspace import Workspace

WRITE_TOOLS = {"progress_record", "java_run_snippet"}
READ_TOOLS = {"arch_scan", "curriculum_list"}


def _decisions(mode):
    """返回 {工具名: behavior}，behavior 为 deny/ask/allow/None(default)。"""
    s = Settings()
    s.permission_mode = mode
    tk = build_toolkit(s, Workspace(s.workspace_dir))
    out = {}
    for group in tk.tool_groups:
        for t in getattr(group, "tools", []) or []:
            p = getattr(t, "_permission", None)
            beh = getattr(p, "behavior", None)
            out[t.name] = getattr(beh, "value", None) or (str(beh).split(".")[-1].lower() if beh else None)
    return out


def test_read_only_denies_write_tools():
    d = _decisions("read-only")
    for name in WRITE_TOOLS:
        assert d[name] == "deny", f"{name} 在 read-only 下应被拒绝"


def test_interactive_asks_write_tools():
    d = _decisions("interactive")
    for name in WRITE_TOOLS:
        assert d[name] == "ask", f"{name} 在 interactive 下应询问"


def test_full_allows_write_tools():
    d = _decisions("full")
    for name in WRITE_TOOLS:
        assert d[name] == "allow", f"{name} 在 full 下应放行"


def test_read_tools_never_denied():
    """只读工具在任何档位都不该被拦。"""
    for mode in ("read-only", "interactive", "full"):
        d = _decisions(mode)
        for name in READ_TOOLS:
            assert d[name] != "deny", f"{name} 是只读工具，不该在 {mode} 下被拒"


def test_ask_is_bypass_immune():
    """interactive 的 ASK 必须不能被 allow 规则静默放行。"""
    d = _permission_for("interactive", write_tool=True)
    assert d.bypass_immune is True


def test_default_mode_is_interactive():
    assert Settings().permission_mode == "interactive"


def test_invalid_mode_falls_back_to_interactive():
    d = _permission_for("bogus", write_tool=True)
    assert d.behavior is PermissionBehavior.ASK