# -*- coding: utf-8 -*-
"""会话持久化测试：往返、隔离、容错。"""

from __future__ import annotations

from pathlib import Path

from agentscope.state import AgentState

from devmentor.config import Settings
from devmentor.store import SessionStore, default_store


def test_save_then_load_roundtrip(tmp_path: Path):
    store = SessionStore(tmp_path)
    state = AgentState(session_id="mentor-20260101-120000")

    path = store.save("mentor-20260101-120000", state)
    assert path is not None and path.is_file()

    loaded = store.load("mentor-20260101-120000")
    assert loaded is not None
    assert loaded.session_id == "mentor-20260101-120000"


def test_load_missing_returns_none(tmp_path: Path):
    store = SessionStore(tmp_path)
    assert store.load("nope") is None


def test_load_corrupt_returns_none(tmp_path: Path):
    """坏文件不该让应用起不来，只当作没有历史。"""
    store = SessionStore(tmp_path)
    store.dir.mkdir(parents=True, exist_ok=True)
    (store.dir / "bad.json").write_text("{not json", encoding="utf-8")

    assert store.load("bad") is None


def test_sessions_are_isolated(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.save("s1", AgentState(session_id="s1"))
    store.save("s2", AgentState(session_id="s2"))

    assert store.load("s1").session_id == "s1"
    assert store.load("s2").session_id == "s2"


def test_clear_removes_only_target(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.save("s1", AgentState(session_id="s1"))
    store.save("s2", AgentState(session_id="s2"))

    store.clear("s1")

    assert store.load("s1") is None
    assert store.load("s2") is not None


def test_clear_missing_is_noop(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.clear("never-existed")  # 不应抛异常


def test_session_id_is_sanitized(tmp_path: Path):
    """带路径分隔符的 id 不能把文件写到目录外。"""
    store = SessionStore(tmp_path)
    path = store.path_for("../../evil")

    assert path.parent == tmp_path or path.parent.resolve() == tmp_path.resolve()
    assert ".." not in path.name


def test_sessions_listed_newest_first(tmp_path: Path):
    import time

    store = SessionStore(tmp_path)
    store.save("old", AgentState(session_id="old"))
    time.sleep(0.02)
    store.save("new", AgentState(session_id="new"))

    listed = store.sessions()
    assert listed[0] == "new"
    assert "old" in listed


def test_save_is_atomic_no_tmp_left_behind(tmp_path: Path):
    """写临时文件再替换，不应残留 .tmp。"""
    store = SessionStore(tmp_path)
    store.save("s1", AgentState(session_id="s1"))

    assert not list(tmp_path.glob("*.tmp"))


def test_default_store_uses_settings_state_dir(tmp_path: Path):
    s = Settings()
    s.state_dir = tmp_path / "mystate"

    store = default_store(s)
    assert store.dir == (tmp_path / "mystate").resolve()
