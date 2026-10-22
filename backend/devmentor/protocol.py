"""前后端协议：JSON-lines over stdio。

设计原则
--------
1. **单向流**：前端 -> 后端只有 request；后端 -> 前端只有 event。
   没有 callback、没有 RPC 反向调用，因此两端可以独立启动、独立测试。
2. **事件即渲染指令**：后端不关心怎么画，只发语义事件（`text.delta`、
   `tool.call`），前端决定用 Ink 组件还是纯文本渲染。
3. **每行一个 JSON**：便于 grep、便于测试、不会被缓冲边界截断。

消息类型
--------
Request（前端 -> 后端）
    {"type": "ask",        "id": "...", "text": "..."}
    {"type": "command",    "id": "...", "name": "login", "args": [...]}
    {"type": "confirm",    "id": "...", "approved": true, "reason": ""}
    {"type": "interrupt",  "id": "..."}
    {"type": "shutdown",   "id": "..."}

Event（后端 -> 前端）
    {"type": "ready",      "session": {...}, "model": "..."}
    {"type": "text.delta",  "text": "..."}
    {"type": "thinking.delta", "text": "..."}
    {"type": "tool.call",  "name": "...", "input": {...}}
    {"type": "tool.result","name": "...", "state": "success", "preview": "..."}
    {"type": "require.confirm", "calls": [{"name": "...", "input": {...}}]}
    {"type": "system",     "text": "..."}
    {"type": "error",      "message": "..."}
    {"type": "menu",       "title": "...", "options": [{"value": "...", "label": "...", "desc": "..."}]}
    {"type": "turn.end"}
    {"type": "bye"}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal


# ---------------------------------------------------------------- 请求

RequestType = Literal["ask", "command", "confirm", "interrupt", "shutdown"]


@dataclass(slots=True)
class Request:
    """前端发来的单条请求。"""

    type: RequestType
    id: str = ""
    text: str = ""
    name: str = ""
    args: list[str] = field(default_factory=list)
    approved: bool = False
    reason: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def parse(line: str) -> "Request | None":
        """解析一行；格式不对返回 None 而不是抛异常，避免一行坏数据打断整个会话。"""
        line = line.strip()
        if not line:
            return None
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(raw, dict):
            return None
        kind = raw.get("type")
        if kind not in ("ask", "command", "confirm", "interrupt", "shutdown"):
            return None
        return Request(
            type=kind,
            id=str(raw.get("id", "")),
            text=str(raw.get("text", "")),
            name=str(raw.get("name", "")),
            args=[str(a) for a in raw.get("args", []) or []],
            approved=bool(raw.get("approved", False)),
            reason=str(raw.get("reason", "")),
        )


# ---------------------------------------------------------------- 事件

class ToolState(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    DENIED = "denied"
    INTERRUPTED = "interrupted"


@dataclass(slots=True)
class MenuOption:
    value: str
    label: str
    desc: str = ""


@dataclass(slots=True)
class Event:
    """后端发给前端的事件。`type` 决定前端选哪个渲染组件。"""

    type: str
    text: str = ""
    name: str = ""
    state: str = ""
    preview: str = ""
    message: str = ""
    model: str = ""
    title: str = ""
    session: dict[str, Any] = field(default_factory=dict)
    input: dict[str, Any] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)
    options: list[MenuOption] = field(default_factory=list)

    def to_json(self) -> str:
        data = asdict(self)
        # 丢掉空字段，让前端日志和测试断言更干净
        return json.dumps(
            {k: v for k, v in data.items() if v not in ("", None, [], {})},
            ensure_ascii=False,
        )


# ---------------------------------------------------------------- 便捷构造器

def ready(session: dict[str, Any], model: str) -> Event:
    return Event(type="ready", session=session, model=model)


def text_delta(text: str) -> Event:
    return Event(type="text.delta", text=text)


def thinking_delta(text: str) -> Event:
    return Event(type="thinking.delta", text=text)


def tool_call(name: str, tool_input: dict[str, Any]) -> Event:
    return Event(type="tool.call", name=name, input=tool_input)


def tool_result(name: str, state: ToolState, preview: str) -> Event:
    return Event(type="tool.result", name=name, state=state.value, preview=preview)


def require_confirm(calls: list[dict[str, Any]]) -> Event:
    return Event(type="require.confirm", calls=calls)


def system(text: str) -> Event:
    return Event(type="system", text=text)


def error(message: str) -> Event:
    return Event(type="error", message=message)


def menu(title: str, options: list[MenuOption]) -> Event:
    return Event(type="menu", title=title, options=options)


def success_event(text: str) -> Event:
    return Event(type="success", text=text)


def turn_end() -> Event:
    return Event(type="turn.end")


def bye() -> Event:
    return Event(type="bye")