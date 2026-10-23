# -*- coding: utf-8 -*-
"""会话 id 唯一性：跨 Python 版本都必须成立。

实测发现：Python 3.12 在同一进程里连续调用 datetime.now()，
微秒部分不前进，导致连开两个会话拿到完全相同的 id
（20 次调用只有 1 个唯一值）。3.13 上因为时钟行为不同没暴露。

后果很严重：新会话的状态会覆盖旧的，/new 之后历史静默丢失。
修法是加进程内自增序号，这组测试锁住它。
"""

from __future__ import annotations

from devmentor.service import _new_session_id


def test_ids_unique_in_tight_loop():
    """连续快速生成，不能有重复。"""
    ids = [_new_session_id("u") for _ in range(200)]
    assert len(set(ids)) == len(ids), (
        f"生成 {len(ids)} 个 id 只有 {len(set(ids))} 个唯一值"
    )


def test_id_format():
    sid = _new_session_id("u")
    parts = sid.split("-")
    # mentor / YYYYMMDD / HHMMSS / 微秒 / 序号
    assert parts[0] == "mentor"
    assert parts[1].isdigit() and len(parts[1]) == 8
    assert parts[2].isdigit() and len(parts[2]) == 6
    assert parts[3].isdigit() and len(parts[3]) == 6
    assert parts[4].isdigit()


def test_id_prefix_is_stable_for_sorting():
    """前缀按时间递增，方便 sessions() 按名字排序。"""
    a = _new_session_id("u")
    b = _new_session_id("u")
    assert a < b, "先生成的 id 应当排在前面"


def test_session_ids_from_service_are_distinct(tmp_path):
    """通过 Service 连开两个会话，id 必须不同。"""
    from devmentor.config import CredentialStore, Settings
    from devmentor.service import AgentService

    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    svc = AgentService(s, CredentialStore(tmp_path / "creds"))

    a = svc.start_new_session()
    b = svc.start_new_session()
    assert a != b


def test_many_sessions_do_not_collide(tmp_path):
    """连开 50 个会话，磁盘上应有 50 个不同文件。"""
    from devmentor.config import CredentialStore, Settings
    from devmentor.service import AgentService

    s = Settings()
    s.state_dir = tmp_path / "state"
    s.workspace = tmp_path / "ws"
    svc = AgentService(s, CredentialStore(tmp_path / "creds"))

    for _ in range(50):
        svc.start_new_session()
        svc.save_state(create_if_missing=True)

    files = list((tmp_path / "state").glob("*.json"))
    assert len(files) == 50, f"应有 50 个会话文件，实际 {len(files)}"
