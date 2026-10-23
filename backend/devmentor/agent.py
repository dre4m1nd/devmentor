"""Agent 装配：把工作区、模型、工具、会话组装成一个可用的导师 Agent。

对应 Java 版的 MentorAgentFactory + MentorAgentConfiguration。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentscope.agent import Agent
from agentscope.credential import (
    AnthropicCredential,
    DashScopeCredential,
    DeepSeekCredential,
    OllamaCredential,
    OpenAICredential,
)
from agentscope.model import (
    AnthropicChatModel,
    DashScopeChatModel,
    DeepSeekChatModel,
    OllamaChatModel,
    OpenAIChatModel,
)
from agentscope.tool import FunctionTool, Toolkit

from .config import CredentialStore, Settings, effective_provider, provider_by_name
from .tools import ArchitectureTools, CurriculumTools, ProgressTools, compile_check, run_snippet
from .workspace import Workspace


FALLBACK_SYSTEM_PROMPT = """你是 DevMentor，一位耐心、严格的编程导师。

- 先诊断再给答案：问清目标、已尝试的方案和报错，再决定怎么讲。
- 结论必须可验证：凡是声称"能运行"的代码，先用 java_run_snippet 真正跑一遍。
- 一次只讲一个概念，给最小可运行示例。
- 练习要附验收标准；学习者卡住时先给提示，不要直接贴答案。
- 默认用中文讲解，代码与术语保留英文。
"""


def build_model(settings: Settings, store: CredentialStore):
    """按 provider:model 构造对应的 ChatModel。

    支持 openai 前缀（含 OpenRouter 等兼容网关）、deepseek、dashscope、
    anthropic、ollama。切换 provider 只需改配置。
    """
    provider_name = settings.provider
    model_name = settings.model_name
    api_key = settings.resolve_api_key(store)
    # 结合 key 前缀判断真正生效的厂商：openai 前缀可能是 OpenRouter
    provider = effective_provider(settings, api_key)

    base_url = settings.base_url or (provider.default_base_url if provider else "")

    if provider_name == "ollama":
        return OllamaChatModel(
            credential=OllamaCredential(host=base_url or "http://localhost:11434"),
            model=model_name,
        )
    if not api_key:
        env = provider.env_var if provider else "该 provider 要求的 API Key"
        raise MissingCredential(
            f"缺少模型凭据。请用 /login 登录，或设置环境变量 {env}。"
        )

    if provider_name == "deepseek":
        return DeepSeekChatModel(
            credential=DeepSeekCredential(
                api_key=api_key, base_url=base_url or None
            ),
            model=model_name,
        )
    if provider_name == "dashscope":
        return DashScopeChatModel(
            credential=DashScopeCredential(api_key=api_key),
            model=model_name,
        )
    if provider_name == "anthropic":
        return AnthropicChatModel(
            credential=AnthropicCredential(api_key=api_key),
            model=model_name,
        )
    # 默认按 OpenAI 兼容处理（含 OpenRouter）
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=api_key, base_url=base_url or None),
        model=model_name,
    )


class MissingCredential(Exception):
    """没有可用的模型凭据。"""


def _permission_for(mode: str, write_tool: bool):
    """按权限档位给写类工具配权限决策。

    三档对应三个行为：
      - read-only   -> DENY：任何写操作直接拒绝
      - interactive -> ASK：执行前必须用户确认（默认，最安全）
      - full        -> ALLOW：不再询问

    只读工具永远 ALLOW，不需要确认。
    """
    if not write_tool:
        return None  # 走 AgentScope 默认（ALLOW）

    from agentscope.permission import PermissionBehavior, PermissionDecision

    normalized = (mode or "interactive").strip().lower()
    if normalized == "read-only":
        return PermissionDecision(
            behavior=PermissionBehavior.DENY,
            message="当前是 read-only 档位，写操作已被拒绝。可用 /mode interactive 放开。",
            decision_reason="permission-mode=read-only",
        )
    if normalized == "full":
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="permission-mode=full，已放行。",
            decision_reason="permission-mode=full",
        )
    return PermissionDecision(
        behavior=PermissionBehavior.ASK,
        message="这是一次写操作，需要确认。",
        decision_reason="permission-mode=interactive",
        bypass_immune=True,
    )


def build_toolkit(settings: Settings, workspace: Workspace) -> Toolkit:
    """注册全部工具。

    工具本身无状态（除课程/进度需要 workspace 路径），可被并发共享。
    """
    ws = workspace.path
    curriculum = CurriculumTools(ws)
    progress = ProgressTools(ws)
    arch = ArchitectureTools(settings.project_dir, ws / "reports")

    tools = [
        FunctionTool(
            _wrap(curriculum.list_courses),
            name="curriculum_list",
            description="列出工作区里可用的课程。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(curriculum.read_course),
            name="curriculum_read",
            description="读取指定课程的完整内容。slug 是课程名，如 01-syntax-and-types。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(lambda: progress.read_progress()),
            name="progress_read",
            description="读取学习进度记录。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(progress.record_progress),
            name="progress_record",
            description="记录一条学习进度，用于跨会话记忆。note 是进度内容。",
            permission=_permission_for(settings.permission_mode, write_tool=True),
        ),
        FunctionTool(
            _wrap(
                lambda source: run_snippet(
                    source,
                    timeout_seconds=settings.java_run_timeout,
                    max_source_chars=settings.max_source_chars,
                )
            ),
            name="java_run_snippet",
            description=(
                "真正编译并运行 Java 代码片段，返回退出码、stdout、stderr。"
                "任何声称『这段能跑』的说法都必须先调用它验证。"
            ),
            permission=_permission_for(settings.permission_mode, write_tool=True),
        ),
        FunctionTool(
            _wrap(
                lambda source: compile_check(
                    source, max_source_chars=settings.max_source_chars
                )
            ),
            name="java_compile_check",
            description="用 JDK 编译器检查 Java 片段，返回 行:列 诊断。不运行代码。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(arch.scan),
            name="arch_scan",
            description=(
                "全项目静态分析：包结构、包级依赖图、体量分布、规则命中清单。"
                "在给出任何架构意见之前必须先调用它。"
            ),
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(arch.findings),
            name="arch_findings",
            description="只看规则命中的缺陷，可按 severity（high/medium/low）过滤。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(arch.dependencies),
            name="arch_dependencies",
            description="只看包级依赖图与循环依赖。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(arch.file_profile),
            name="arch_file_profile",
            description="单文件画像：体量、方法数、命中的规则。",
            is_read_only=True,
        ),
        FunctionTool(
            _wrap(arch.read_source),
            name="arch_read_source",
            description="带行号读取源码，用于引用具体代码。",
            is_read_only=True,
        ),
    ]
    # 把落盘的技能接进 Toolkit：工作区 skills/<name>/SKILL.md 会被解析成
    # 可用技能，模型通过 skill viewer 读取。没有 skills 目录时传空列表。
    skills_dir = ws / "skills"
    skill_paths: list[str] = []
    if skills_dir.is_dir():
        skill_paths = [str(p) for p in sorted(skills_dir.glob("*/SKILL.md"))]

    return Toolkit(tools=tools, skills_or_loaders=skill_paths or None)


def _wrap(fn):
    """把同步函数包成 AgentScope 期望的形式（直接返回字符串即可）。"""
    return fn


def build_agent(settings: Settings, workspace: Workspace, store: CredentialStore) -> Agent:
    """组装 Agent。"""
    workspace.ensure()
    system_prompt = workspace.read_agents_md() or FALLBACK_SYSTEM_PROMPT

    return Agent(
        name="devmentor",
        system_prompt=system_prompt,
        model=build_model(settings, store),
        toolkit=build_toolkit(settings, workspace),
    )