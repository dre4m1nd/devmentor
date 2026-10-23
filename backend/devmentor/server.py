"""服务端主循环：JSON-lines over stdio。

读取前端发来的请求，产出事件。stdout 只写协议 JSON，
日志一律走 stderr——否则一行日志就会破坏协议解析。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import AsyncIterator

from . import protocol as proto
from .agent import MissingCredential
from .commands import CommandHandler, parse
from .config import CredentialStore, Settings
from .protocol import Event, Request
from .service import AgentService


class Server:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.from_env()
        self._store = CredentialStore()
        self._service = AgentService(self._settings, self._store)
        self._commands = CommandHandler(self._settings, self._store)
        self._login_stage = 0        # 0=空闲 1=等厂商序号 2=等 Key
        self._login_provider = 0

    # ------------------------------------------------------------ 输出

    def emit(self, event: Event) -> None:
        sys.stdout.write(event.to_json() + "\n")
        sys.stdout.flush()

    def log(self, message: str) -> None:
        """诊断信息走 stderr，绝不污染协议流。"""
        sys.stderr.write(message + "\n")
        sys.stderr.flush()

    # ------------------------------------------------------------ 主循环

    async def run(self) -> None:
        self.emit(await self._service.ready_event())

        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                break
            request = Request.parse(line)
            if request is None:
                self.emit(proto.error("无法解析的请求格式。"))
                continue

            if request.type == "shutdown":
                break
            if request.type == "ask":
                async for ev in self._dispatch_text(request.text):
                    self.emit(ev)
            elif request.type == "command":
                # 命令也要过登录状态机：前端把 /login 的序号当命令发过来时，
                # 必须先被登录流程接住，而不是当成未知命令。
                async for ev in self._dispatch_text(
                    "/" + request.name + (" " + " ".join(request.args) if request.args else "")
                ):
                    self.emit(ev)
            elif request.type == "confirm":
                async for ev in self._service.confirm(request.approved, request.reason):
                    self.emit(ev)

        self.emit(proto.bye())

    # ------------------------------------------------------------ 输入分发

    async def _dispatch_text(self, text: str) -> AsyncIterator[Event]:
        text = text.strip()
        if not text:
            return

        # 登录流程是两段式交互，优先处理。
        # 前端把这一阶段的输入也当命令发来（"1" 变成 "/1"），
        # 所以先剥掉开头的 "/"，再交给登录状态机。
        if self._login_stage:
            reply = text[1:] if text.startswith("/") else text
            async for ev in self._handle_login_reply(reply):
                yield ev
            return

        if text.startswith("/"):
            parsed = parse(text)
            if parsed is None:
                yield proto.error("命令格式不对，输入 / 查看全部命令。")
                return
            async for ev in self._handle_command(parsed[0], parsed[1]):
                yield ev
            return

        try:
            async for ev in self._service.ask(text):
                yield ev
        except MissingCredential as e:
            yield proto.error(str(e))
            yield proto.system("提示：输入 /login 登录厂商并填入 API Key。")

    async def _handle_command(self, name: str, args: list[str]) -> AsyncIterator[Event]:
        if name == "login":
            self._login_stage = 1
            self._login_provider = 0
        async for ev in self._commands.handle(name, args, self._service):
            yield ev

    # ------------------------------------------------------------ 登录两段式

    async def _handle_login_reply(self, text: str) -> AsyncIterator[Event]:
        from .config import PROVIDERS, provider_by_id

        if self._login_stage == 1:
            text = text.strip()
            if not text:
                self._login_stage = 0
                yield proto.system("已取消。")
                return
            try:
                pid = int(text)
            except ValueError:
                yield proto.error(f"请输入序号（1-{len(PROVIDERS)}）。")
                return
            provider = provider_by_id(pid)
            if provider is None:
                yield proto.error(f"没有序号 {pid} 对应的厂商。")
                return

            self._login_provider = pid
            if not provider.env_var:
                # Ollama 不需要 Key，直接完成
                self._login_stage = 0
                async for ev in self._commands.apply_login(pid, "", self._service):
                    yield ev
                return

            self._login_stage = 2
            yield proto.system(f"厂商：{provider.label}")
            yield proto.system(f"获取 Key：{provider.hint}")
            yield proto.system("请粘贴 API Key（输入后回车）：")
            return

        if self._login_stage == 2:
            self._login_stage = 0
            async for ev in self._commands.apply_login(
                self._login_provider, text.strip(), self._service
            ):
                yield ev
            return


def main() -> None:
    settings = Settings.from_env()
    server = Server(settings)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()