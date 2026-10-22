"""斜杠命令：与 Java 版 /help 列表保持一致。

命令处理产出 Event（而不是直接打印），因此前端可以按自己的方式渲染。
"""

from __future__ import annotations

from typing import AsyncIterator

from . import protocol as proto
from .config import PROVIDERS, CredentialStore, Settings, provider_by_id
from .protocol import Event, MenuOption


DEFINITIONS: list[tuple[str, str, str]] = [
    ("/help", "/help", "显示帮助"),
    ("/new", "/new [名字]", "开启新会话"),
    ("/reset", "/reset", "清空当前会话上下文"),
    ("/mode", "/mode <interactive|read-only|full>", "切换权限档位"),
    ("/plan", "/plan [on|off]", "切换 plan 模式"),
    ("/arch", "/arch [路径]", "架构评审：静态分析当前项目"),
    ("/lesson", "/lesson [slug]", "列出或阅读课程"),
    ("/progress", "/progress", "查看学习进度"),
    ("/lang", "/lang <zh|en>", "切换讲解语言"),
    ("/login", "/login", "登录：选择厂商并输入 API Key"),
    ("/logout", "/logout [厂商]", "清除已保存的 API Key"),
    ("/model", "/model [id]", "查看或切换模型"),
    ("/tools", "/tools", "列出可用工具"),
    ("/workspace", "/workspace", "显示工作区与代码目录"),
    ("/session", "/session", "显示当前会话信息"),
    ("/verbose", "/verbose", "切换工具输出全量/摘要"),
    ("/think", "/think", "切换是否显示推理过程"),
    ("/quit", "/quit", "退出"),
]


def help_text() -> str:
    lines = ["可用命令："]
    for usage, _, desc in DEFINITIONS:
        lines.append(f"  {usage:<38} {desc}")
    lines.append("")
    lines.append("直接输入内容即与导师对话；Ctrl+C 中断当前回答，Ctrl+D 退出。")
    return "\n".join(lines)


def command_names() -> list[str]:
    return [name for name, _, _ in DEFINITIONS]


def argument_candidates(name: str) -> list[str]:
    """某个命令第一个参数的候选值（供前端补全）。"""
    return {
        "mode": ["interactive", "read-only", "full"],
        "lang": ["zh", "en"],
        "plan": ["on", "off"],
    }.get(name.lower(), [])


def parse(line: str) -> tuple[str, list[str]] | None:
    """解析一行命令；非法返回 None。"""
    line = line.strip()
    if not line.startswith("/"):
        return None
    parts = line[1:].split()
    if not parts:
        return None
    return parts[0].lower(), parts[1:]


# ---------------------------------------------------------------- 命令执行


class CommandHandler:
    """执行斜杠命令。

    provider 相关的命令（login/logout）需要改配置并重建 Agent，
    因此持有 service 的引用而不是复制它的状态。
    """

    def __init__(self, settings: Settings, store: CredentialStore) -> None:
        self._settings = settings
        self._store = store
        self._verbose = False
        self._think = False
        self.plan_mode = False

    async def handle(
        self, name: str, args: list[str], service
    ) -> AsyncIterator[Event]:
        name = name.lower()

        if name in ("quit", "exit"):
            yield proto.bye()
            return

        if name == "help":
            yield proto.system(help_text())
            return

        if name == "reset":
            if service._agent is not None:
                # Agent 的上下文重置：重建 Agent 即清空内存上下文
                service.reset_agent()
            yield proto.system("当前会话上下文已清空。")
            return

        if name == "new":
            self._settings.session_id = ""
            service.reset_agent()
            ev = await service.ready_event()
            yield proto.system(f"已开启新会话：{ev.session.get('session', '')}")
            return

        if name == "session":
            yield proto.system(
                f"用户：{self._settings.user_id}\n"
                f"会话：{self._settings.session_id or '(未开始)'}\n"
                f"模型：{self._settings.model_id}\n"
                f"权限：{self._settings.permission_mode}"
            )
            return

        if name == "workspace":
            yield proto.system(
                f"工作区：{self._settings.workspace_dir}\n"
                f"代码目录：{self._settings.project_dir}\n"
                f"状态目录：{self._settings.state_dir.resolve()}"
            )
            return

        if name == "model":
            if not args:
                yield proto.system(f"当前模型：{self._settings.model_id}")
                return
            self._settings.model_id = args[0]
            service.reset_agent()
            yield proto.system(f"已切换模型为 {args[0]}")
            return

        if name == "mode":
            if not args:
                yield proto.system(f"当前权限档位：{self._settings.permission_mode}")
                return
            mode = args[0]
            if mode not in ("interactive", "read-only", "full"):
                yield proto.error("用法：/mode <interactive|read-only|full>")
                return
            self._settings.permission_mode = mode
            service.reset_agent()
            yield proto.system(f"权限档位已切换为 {mode}")
            return

        if name == "lang":
            if not args or args[0] not in ("zh", "en"):
                yield proto.error("用法：/lang <zh|en>")
                return
            self._settings.language = args[0]
            yield proto.system(
                "讲解语言已切换为 " + ("中文" if args[0] == "zh" else "英文")
            )
            return

        if name == "plan":
            if not args:
                yield proto.system(f"plan 模式当前：{'开启' if self.plan_mode else '关闭'}")
                return
            self.plan_mode = args[0] in ("on", "true")
            yield proto.system(
                "plan 模式已" + ("开启（只读设计阶段）" if self.plan_mode else "关闭")
            )
            return

        if name == "think":
            self._think = not self._think
            yield proto.system(f"推理过程：{'显示' if self._think else '隐藏'}")
            return

        if name == "verbose":
            self._verbose = not self._verbose
            yield proto.system(f"工具输出：{'全量' if self._verbose else '摘要'}")
            return

        if name == "tools":
            agent = service._agent
            if agent is None:
                try:
                    agent = agent or None
                except Exception:
                    pass
            yield proto.system(
                "可用工具：\n  curriculum_list, curriculum_read, progress_read, "
                "progress_record, java_run_snippet, java_compile_check, "
                "arch_scan, arch_findings, arch_dependencies, "
                "arch_file_profile, arch_read_source"
            )
            return

        if name == "login":
            async for ev in self._handle_login(service):
                yield ev
            return

        if name == "logout":
            async for ev in self._handle_logout(args, service):
                yield ev
            return

        if name == "arch":
            path = args[0] if args else None
            from .tools import ArchitectureTools

            tool = ArchitectureTools(self._settings.project_dir, self._settings.workspace_dir / "reports")
            yield proto.system(tool.scan(path))
            return

        if name == "lesson":
            from .tools import CurriculumTools

            tool = CurriculumTools(self._settings.workspace_dir)
            if not args:
                yield proto.system(tool.list_courses())
            else:
                yield proto.system(tool.read_course(args[0]))
            return

        if name == "progress":
            from .tools import ProgressTools

            tool = ProgressTools(self._settings.workspace_dir)
            yield proto.system(tool.read_progress())
            return

        yield proto.error(f"未知命令 /{name}，输入 /help 查看用法。")

    # ------------------------------------------------------------ 登录

    async def _handle_login(self, service) -> AsyncIterator[Event]:
        options = [
            MenuOption(
                value=str(p.id),
                label=p.label,
                desc="无需 Key" if not p.env_var else p.hint,
            )
            for p in PROVIDERS
        ]
        yield proto.menu("选择模型厂商：", options)
        # 前端拿到 menu 后回送 command: login.choose 带 value
        # 这里由 server 负责两段式交互，见 Server._handle_login_choice

    async def apply_login(self, provider_id: int, api_key: str, service) -> AsyncIterator[Event]:
        provider = provider_by_id(provider_id)
        if provider is None:
            yield proto.error(f"没有序号 {provider_id} 对应的厂商。")
            return

        if provider.env_var:  # 需要 Key
            key = (api_key or "").strip()
            if not key:
                yield proto.system("已取消，未保存任何凭据。")
                return
            try:
                self._store.save(provider.provider, key)
            except OSError as e:
                yield proto.error(f"保存凭据失败：{e}")
                return
            yield proto.success_event(f"凭据已保存到 {self._store.file}")

        self._settings.model_id = f"{provider.provider}:{provider.default_model}"
        self._settings.base_url = provider.default_base_url
        self._settings.api_key = (api_key or "").strip()
        service.reset_agent()
        yield proto.system(
            f"已登录 {provider.label}，模型：{self._settings.model_id}"
        )

    async def _handle_logout(self, args: list[str], service) -> AsyncIterator[Event]:
        saved = self._store.load()
        if not saved:
            yield proto.system("没有已保存的凭据。")
            return
        target = args[0].lower() if args else self._settings.provider
        if target not in saved:
            yield proto.error(f"没有为 {target} 保存凭据。")
            return
        self._store.remove(target)
        self._settings.api_key = ""
        service.reset_agent()
        yield proto.system(f"已清除 {target} 的凭据。输入 /login 可重新登录。")