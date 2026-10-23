"""Agent 服务：把 AgentScope 的事件流翻译成协议事件。

这是前后端的唯一接口。它不认识 Ink、不打印任何东西——只产出 Event 对象，
由调用方（server.py）序列化成 JSON 行。
"""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from agentscope.message import UserMsg

from . import protocol as proto
from .agent import MissingCredential, build_agent
from .config import CredentialStore, Settings, provider_by_id, provider_by_name
from .protocol import Event, MenuOption, ToolState
from .store import SessionStore, default_store
from .workspace import Workspace

# AgentScope 事件类型 -> 我们的处理方式（用 isinstance 更稳，但这里只需 type 名）
_TEXT_DELTA = "text_block_delta_event"
_THINKING_DELTA = "thinking_block_delta_event"
_TOOL_CALL_START = "tool_call_start_event"
_TOOL_RESULT_END = "tool_result_end_event"
_REQUIRE_CONFIRM = "require_user_confirm_event"
_EXCEED_MAX_ITERS = "exceed_max_iters_event"


def _event_type_name(event: object) -> str:
    """取事件类型名。

    AgentScope 的事件类是 XXEvent，我们按类型名做映射，避免硬依赖具体类路径
    （库升级时类名比包路径更稳定）。
    """
    name = type(event).__name__
    # TextBlockDeltaEvent -> text_block_delta_event
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


class AgentService:
    """会话级 agent 服务。一个进程一个实例，对应一个会话。"""

    def __init__(self, settings: Settings, store: CredentialStore) -> None:
        self._settings = settings
        self._store = store
        self._workspace = Workspace(settings.workspace_dir)
        self._sessions = default_store(settings)
        self._agent = None
        self._pending_confirm: list[dict] = []

    # ------------------------------------------------------------ 生命周期

    @property
    def settings(self) -> Settings:
        return self._settings

    def reset_agent(self) -> None:
        """丢掉当前 Agent，下次提问时按新配置重建。

        模型在构建期绑定，改 provider 只能重建；会话 id 不变，
        因此新旧 Agent 指向同一份持久化状态。
        """
        self._agent = None
        self._pending_confirm = []

    async def ready_event(self) -> Event:
        written = self._workspace.ensure()
        session_id = self._settings.session_id or self._continue_or_new_session()
        session = {
            "user": self._settings.user_id,
            "session": session_id,
            "workspace": str(self._workspace.path),
            "project": str(self._settings.project_dir),
            "permission": self._settings.permission_mode,
            "credentials": self.credential_status(),
            "bootstrapped": written,
        }
        self._settings.session_id = session_id
        # 会话一被分配就落一份空状态：这样即使一句话没说就退出，
        # 下次启动也能接续到这个会话。
        self.save_state(create_if_missing=True)
        return proto.ready(session, self._settings.model_id)

    def start_new_session(self) -> str:
        """强制开一个新会话，不接续历史。

        /new 用它：直接生成新 id 并记为当前会话，
        之后再调 ready_event 就不会走"恢复最近会话"的分支。
        """
        self._settings.session_id = _new_session_id(self._settings.user_id)
        return self._settings.session_id

    def _continue_or_new_session(self) -> str:
        """默认接续最近一次会话，让重启后还能接着聊。

        只有一条历史都没有时才开新会话。想强制开新的用 /new。
        """
        existing = self._sessions.sessions()
        if existing:
            return existing[0]
        return _new_session_id(self._settings.user_id)

    def credential_status(self) -> str:
        """一行说明当前凭据来源，让用户一眼看出能不能用。"""
        provider = self._settings.provider
        key = self._settings.resolve_api_key(self._store)
        if key:
            return f"已提供（{_mask(key)}）"
        if provider == "ollama":
            return "无需 Key（本地 Ollama）"
        return "未登录 — 输入 /login 选择厂商并填入 API Key"

    # ------------------------------------------------------------ 对话

    async def ask(self, text: str) -> AsyncIterator[Event]:
        """跑一轮对话，把事件翻译成协议事件。

        turn.end 放在最外层 finally：只要这一轮有 ask，无论成功、失败
        还是构造 Agent 时就抛异常，前端都必须收到结束信号，
        否则会永远停在"思考中"且输入框不恢复。
        """
        try:
            agent = self._ensure_agent()
            if agent is None:
                return
            async for event in agent.reply_stream(UserMsg(name="user", content=text)):
                async for out in self._translate(event):
                    yield out
        except MissingCredential as e:
            yield proto.error(str(e))
        except Exception as e:
            yield proto.error(_friendly(e))
        finally:
            # 每轮结束都落盘：进程被杀也只丢最后半轮
            self.save_state()
            yield proto.turn_end()

    async def confirm(self, approved: bool, reason: str = "") -> AsyncIterator[Event]:
        """回送用户对工具调用的确认结果，继续执行。

        与 ask() 同理：turn.end 由最外层 finally 保证，
        构造 Agent 失败也不能让前端卡住。
        """
        from agentscope.event import UserConfirmResultEvent

        try:
            agent = self._ensure_agent()
            if agent is None or not self._pending_confirm:
                return
        except Exception as e:
            yield proto.error(_friendly(e))
            return

        from agentscope.event._event import ConfirmResult

        results = [
            ConfirmResult(confirmed=approved, tool_call=call, rules=None)
            for call in self._pending_confirm
        ]
        self._pending_confirm = []

        try:
            async for event in agent.reply_stream(
                UserConfirmResultEvent(confirm_results=results)
            ):
                async for out in self._translate(event):
                    yield out
        except Exception as e:
            yield proto.error(_friendly(e))
        finally:
            yield proto.turn_end()

    # ------------------------------------------------------------ 事件翻译

    async def _translate(self, event: object) -> AsyncIterator[Event]:
        name = _event_type_name(event)

        if name == _TEXT_DELTA:
            delta = getattr(event, "delta", "") or ""
            if delta:
                yield proto.text_delta(delta)
            return

        if name == _THINKING_DELTA:
            delta = getattr(event, "delta", "") or ""
            if delta:
                yield proto.thinking_delta(delta)
            return

        if name == _TOOL_CALL_START:
            tool_name = getattr(event, "tool_call_name", "") or getattr(event, "name", "")
            tool_input = getattr(event, "tool_input", None) or getattr(event, "input", None) or {}
            yield proto.tool_call(str(tool_name), _as_dict(tool_input))
            return

        if name == _TOOL_RESULT_END:
            state_raw = getattr(event, "state", None)
            state = _map_state(state_raw)
            preview = _preview(event)
            yield proto.tool_result(str(getattr(event, "tool_call_name", "") or ""), state, preview)
            return

        if name == _REQUIRE_CONFIRM:
            calls = getattr(event, "tool_calls", None) or getattr(event, "calls", None) or []
            # 保留原始 ToolCallBlock：回送确认结果时 ConfirmResult 要求它是
            # ToolCallBlock 而非 dict，转成 dict 会在构造时直接 ValidationError。
            self._pending_confirm = list(calls)
            yield proto.require_confirm([_as_dict(c) for c in calls])
            return

        if name == _EXCEED_MAX_ITERS:
            iters = getattr(event, "max_iters", 0)
            yield proto.error(
                f"达到最大推理轮数（{iters}），已停止。可以换个更小的问法，或 /new 开新会话。"
            )
            return

        # 其余事件（模型调用、块开始/结束等）不透传给前端
        return

    # ------------------------------------------------------------ Agent 构建

    def _ensure_agent(self):
        """惰性创建 Agent；缺 Key 时返回 None（已产出的错误事件由调用方负责）。

        创建时尝试从磁盘恢复该会话的历史状态，恢复失败就开新会话——
        坏一个状态文件不该让整个应用起不来。
        """
        if self._agent is not None:
            return self._agent
        try:
            restored = self._sessions.load(self._settings.session_id)
            self._agent = build_agent(
                self._settings, self._workspace, self._store, state=restored
            )
            return self._agent
        except MissingCredential:
            raise
        except Exception:
            raise

    def interrupt(self) -> None:
        """放弃当前待确认的操作，并把状态落盘。

        真正的"停止正在跑的推理"由 Agent 自身的中断机制负责；这里
        只清理本层持有的中间状态，保证下一次提问不会带着残留的
        pending 确认继续跑。
        """
        self._pending_confirm = []
        # create_if_missing=True：中断时即使还没建 Agent，
        # 也要保证当前会话在磁盘上有一份记录，不丢进度。
        self.save_state(create_if_missing=True)

    def save_state(self, create_if_missing: bool = False) -> None:
        """把当前会话状态落盘。任何失败都静默——存不下不该打断对话。

        create_if_missing=True 时，即使还没创建 Agent（例如刚 /new 完
        就退出），也写一份空状态，保证这个会话在磁盘上存在，
        下次启动能被接续。
        """
        agent = self._agent
        state = getattr(agent, "state", None) if agent is not None else None

        if state is None:
            if not create_if_missing:
                return
            from agentscope.state import AgentState

            state = AgentState(session_id=self._settings.session_id)

        self._sessions.save(self._settings.session_id, state)


# ---------------------------------------------------------------- 辅助


def _new_session_id(user_id: str) -> str:
    """生成会话 id。

    带微秒后缀：同一秒内连开两个会话（如自动化脚本）不会撞名。
    """
    from datetime import datetime

    return f"mentor-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


def _as_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {"value": str(value)}


def _map_state(state: object) -> ToolState:
    raw = str(state or "").lower()
    if "denied" in raw:
        return ToolState.DENIED
    if "interrupt" in raw:
        return ToolState.INTERRUPTED
    if "error" in raw or "fail" in raw:
        return ToolState.ERROR
    return ToolState.SUCCESS


def _preview(event: object, limit: int = 300) -> str:
    """取工具结果的首行预览。"""
    for attr in ("result", "output", "content", "text"):
        value = getattr(event, attr, None)
        if value:
            text = str(value).strip()
            first = text.splitlines()[0] if text else ""
            return first[:limit]
    return ""


def _friendly(e: Exception) -> str:
    """把常见失败翻译成可操作的中文提示。"""
    msg = str(e)
    low = msg.lower()
    if "401" in low or "unauthorized" in low or "invalid api key" in low:
        return f"模型鉴权失败（401）：请检查 API Key 是否正确。\n{msg}"
    if "402" in low or "insufficient" in low:
        return f"账户额度不足（402）：免费模型可能有配额限制，可换模型或稍后再试。\n{msg}"
    if "429" in low or "rate limit" in low:
        return f"触发限流（429）：免费模型请求过于频繁，等几秒重试，或用 /model 换一个模型。\n{msg}"
    if "403" in low or "forbidden" in low:
        return f"模型拒绝服务（403）：该模型可能已下线或需要额外授权，用 /model 换一个。\n{msg}"
    if "timeout" in low or "timed out" in low:
        return f"请求超时：网络或模型响应过慢，可以重试或换模型。\n{msg}"
    return msg or type(e).__name__