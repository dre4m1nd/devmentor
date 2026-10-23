"""会话状态持久化：让对话跨进程重启存活。

对应 Java 版用 JsonFileAgentStateStore 做的事。这里不引入额外依赖，
直接用 AgentState 自带的 model_dump_json / model_validate_json。

存储布局::

    <state_dir>/
        <session_id>.json

为什么按 session_id 分文件而不是单文件：/new 换会话时天然隔离，
单个会话损坏也不影响其它会话。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from agentscope.state import AgentState

from .config import Settings, _atomic_replace

#: 保留的会话文件上限。0 表示不限制。
#:
#: 为什么要限：会话历史只增不减，重度使用（每天 10 个会话）一年会累积
#: 约 110MB 且永不清理。限制后上限固定（100 个约 3MB）。
#:
#: 为什么用 100 而不是更小：会话是用户的对话资产，删早了会让人翻不回
#: 上周的讨论。100 个对个人使用足够，同时把空间钳在可控范围。
DEFAULT_MAX_SESSIONS = 100



class SessionStore:
    """会话状态的落盘与读取。"""

    def __init__(self, state_dir: Path, max_sessions: int = DEFAULT_MAX_SESSIONS) -> None:
        self._dir = state_dir
        self._max_sessions = max_sessions

    @property
    def dir(self) -> Path:
        return self._dir

    def path_for(self, session_id: str) -> Path:
        # session_id 由我们生成（mentor-YYYYMMDD-HHMMSS），但仍做一次清洗，
        # 防止带 / 或 .. 的 id 把文件写到目录外。
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "default"
        return self._dir / f"{safe}.json"

    def load(self, session_id: str) -> AgentState | None:
        """读取会话状态；不存在或损坏时返回 None（不让坏文件阻断启动）。"""
        path = self.path_for(session_id)
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            return AgentState.model_validate_json(raw)
        except Exception:
            return None

    def save(self, session_id: str, state: AgentState) -> Path | None:
        """保存会话状态；失败时返回 None，不中断对话。"""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self.path_for(session_id)
            payload = state.model_dump_json(indent=1)
            # 先写临时文件再替换：避免写一半崩溃留下半个 JSON
            # 临时文件名带进程号：多进程同时保存同一会话时，
            # 若共用一个 .tmp 会互相抢文件导致 PermissionError。
            tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
            tmp.write_text(payload, encoding="utf-8")
            try:
                _atomic_replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
            self._prune()
            return path
        except Exception:
            return None

    def _prune(self) -> None:
        """超出上限时删掉最旧的会话文件。

        只删会话状态，不碰 workspace 里的课程/技能/进度——
        那些是用户资产，不该被"清理会话"牵连。
        """
        if self._max_sessions <= 0:
            return
        try:
            files = sorted(
                self._dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for stale in files[self._max_sessions :]:
                try:
                    stale.unlink()
                except OSError:
                    pass  # 删不掉不影响本次保存
        except OSError:
            pass

    def clear(self, session_id: str) -> None:
        path = self.path_for(session_id)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def sessions(self) -> list[str]:
        """列出已保存的会话 id（按修改时间倒序，最近的在前）。"""
        if not self._dir.is_dir():
            return []
        files = sorted(
            self._dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [p.stem for p in files]


def default_store(settings: Settings) -> SessionStore:
    return SessionStore(settings.state_dir.resolve())