# -*- coding: utf-8 -*-
"""会话保留上限：防止长期使用无限累积。

实测数据：典型会话（20 轮对话）约 32KB。重度使用（每天 10 个会话）
一年累积约 110MB，而之前没有任何清理机制。

修复是保留最近 100 个（约 3MB）。这里锁住行为，包括几条容易忽略的边界。
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from agentscope.state import AgentState

from devmentor.store import DEFAULT_MAX_SESSIONS, SessionStore


def _save_n(store: SessionStore, n: int, prefix: str = "s") -> list[str]:
    """写 n 个会话，返回 id 列表（按写入顺序）。"""
    ids = []
    for i in range(n):
        sid = f"{prefix}{i}"
        store.save(sid, AgentState(session_id=sid))
        # 让 mtime 有区分，否则清理顺序不确定
        time.sleep(0.005)
        ids.append(sid)
    return ids


# ---------------------------------------------------------------- 上限生效

def test_keeps_only_latest(tmp_path: Path):
    store = SessionStore(tmp_path, max_sessions=5)
    ids = _save_n(store, 10)

    remaining = sorted(p.stem for p in tmp_path.glob("*.json"))
    assert remaining == ids[-5:], "应只保留最新 5 个"


def test_fewer_than_limit_keeps_all(tmp_path: Path):
    store = SessionStore(tmp_path, max_sessions=10)
    ids = _save_n(store, 3)

    assert sorted(p.stem for p in tmp_path.glob("*.json")) == ids


def test_default_limit_applies(tmp_path: Path):
    store = SessionStore(tmp_path)
    _save_n(store, DEFAULT_MAX_SESSIONS + 20)

    assert len(list(tmp_path.glob("*.json"))) == DEFAULT_MAX_SESSIONS


def test_zero_means_unlimited(tmp_path: Path):
    """max_sessions=0 表示不清理，给需要完整历史的用户留个开关。"""
    store = SessionStore(tmp_path, max_sessions=0)
    _save_n(store, 30)

    assert len(list(tmp_path.glob("*.json"))) == 30


def test_negative_means_unlimited(tmp_path: Path):
    store = SessionStore(tmp_path, max_sessions=-1)
    _save_n(store, 20)

    assert len(list(tmp_path.glob("*.json"))) == 20


# ---------------------------------------------------------------- 边界安全

def test_prune_does_not_touch_non_session_files(tmp_path: Path):
    """清理只删会话 json，不能碰工作区里别的数据。"""
    keep = tmp_path / "notes.md"
    keep.write_text("用户笔记", encoding="utf-8")
    other = tmp_path / "config.yaml"
    other.write_text("key: value", encoding="utf-8")

    store = SessionStore(tmp_path, max_sessions=2)
    _save_n(store, 6)

    assert keep.is_file(), "不应删除非 json 文件"
    assert other.is_file()
    assert keep.read_text(encoding="utf-8") == "用户笔记"


def test_prune_keeps_most_recent_for_resume(tmp_path: Path):
    """接续逻辑取 sessions()[0]，清理后它必须仍是最近那个。"""
    store = SessionStore(tmp_path, max_sessions=3)
    ids = _save_n(store, 8)

    latest = store.sessions()[0]
    assert latest == ids[-1], "最近的会话不能被清理掉"


def test_resume_still_works_after_prune(tmp_path: Path):
    """清理后，最近会话的内容仍能完整读回。"""
    store = SessionStore(tmp_path, max_sessions=2)
    _save_n(store, 4)

    latest_id = store.sessions()[0]
    loaded = store.load(latest_id)
    assert loaded is not None
    assert loaded.session_id == latest_id


def test_save_does_not_fail_when_prune_races(tmp_path: Path):
    """清理失败不能影响保存本身。"""
    store = SessionStore(tmp_path, max_sessions=1)
    _save_n(store, 3)

    # 保存新会话依然成功
    store.save("newest", AgentState(session_id="newest"))
    assert (tmp_path / "newest.json").is_file()


# ---------------------------------------------------------------- 规模

def test_large_number_of_saves_stays_bounded(tmp_path: Path):
    """大量写入后占用应稳定在上限，不随时间增长。"""
    store = SessionStore(tmp_path, max_sessions=10)
    for i in range(60):
        store.save(f"s{i}", AgentState(session_id=f"s{i}"))

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 10, f"应稳定在 10 个，实际 {len(files)}"
