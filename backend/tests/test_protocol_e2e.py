# -*- coding: utf-8 -*-
"""端到端协议测试：在隔离的 HOME 下跑真实子进程。

为什么需要隔离 HOME：
CredentialStore 与 state_dir 都基于 Path.home() 解析。验证协议时如果
直接起子进程，/login 会把测试密钥写进用户真实的 ~/.devmentor/credentials。
这在实际开发中发生过两次。

这里用 monkeypatch 把 HOME/USERPROFILE 指到 tmp_path，子进程整体落进沙箱。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# 这组测试每个用例都要起一个子进程（约 3 秒），整套跑 20+ 秒。
# 日常开发用 -m "not e2e" 跳过；提交前跑全量。
pytestmark = pytest.mark.e2e

BACKEND = Path(__file__).resolve().parents[1]


def _run(reqs: list[dict], home: Path, extra_env: dict | None = None) -> list[dict]:
    """在隔离 HOME 下跑一次 server，返回解析后的事件列表。"""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['USERPROFILE'] = str(home)
    env['HOME'] = str(home)
    # 清掉可能干扰的凭据环境变量
    for k in ('OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY'):
        env.pop(k, None)
    if extra_env:
        env.update(extra_env)

    lines = [json.dumps(r) for r in reqs] + [json.dumps({'type': 'shutdown'})]
    proc = subprocess.run(
        [sys.executable, '-m', 'devmentor.server'],
        input='\n'.join(lines) + '\n',
        capture_output=True,
        text=True,
        env=env,
        cwd=str(BACKEND),
        timeout=180,
        encoding='utf-8',
        errors='replace',
    )
    events = []
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return events


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    home = tmp_path / 'home'
    home.mkdir()
    return home


def test_ready_event_on_startup(sandbox: Path):
    events = _run([], sandbox)
    ready = next((e for e in events if e.get('type') == 'ready'), None)

    assert ready is not None
    assert ready['session']['session']
    assert 'model' in ready


def test_login_writes_into_sandbox_home(sandbox: Path):
    """登录密钥必须落在沙箱 HOME，不能出现在真实主目录。"""
    events = _run(
        [
            {'type': 'command', 'name': 'login', 'args': []},
            {'type': 'command', 'name': '1', 'args': []},
            {'type': 'command', 'name': 'sk-or-v1-sandbox-test', 'args': []},
        ],
        sandbox,
    )

    assert any(e.get('type') == 'menu' for e in events)
    assert any(e.get('type') == 'success' for e in events)
    assert not any(
        e.get('type') == 'error' and '未知命令' in e.get('message', '') for e in events
    )

    cred = sandbox / '.devmentor' / 'credentials'
    assert cred.is_file(), '凭据应写入沙箱 HOME'
    assert 'sk-or-v1-sandbox-test' in cred.read_text(encoding='utf-8')

    # 真实主目录不能被碰
    real = Path(os.path.expanduser('~')) / '.devmentor' / 'credentials'
    if real.is_file():
        assert 'sk-or-v1-sandbox-test' not in real.read_text(encoding='utf-8')


def test_login_reply_accepted_as_command(sandbox: Path):
    """前端把登录阶段的序号当命令发来（"1" -> command name="1"），
    必须被登录状态机接住，而不是报未知命令。"""
    events = _run(
        [
            {'type': 'command', 'name': 'login', 'args': []},
            {'type': 'command', 'name': '2', 'args': []},
        ],
        sandbox,
    )

    assert not any(
        e.get('type') == 'error' and '未知命令' in e.get('message', '') for e in events
    )
    # 应推进到"请粘贴 API Key"
    texts = [e.get('text', '') for e in events if e.get('type') == 'system']
    assert any('API Key' in t for t in texts)


def test_exit_command_bye(sandbox: Path):
    events = _run([{'type': 'command', 'name': 'exit', 'args': []}], sandbox)
    assert any(e.get('type') == 'bye' for e in events)
    assert not any(e.get('type') == 'error' for e in events)


def test_local_commands_do_not_emit_turn_end(sandbox: Path):
    """本地命令不触发 busy 状态，前端据此判断是否显示"思考中"。"""
    events = _run(
        [
            {'type': 'command', 'name': 'session', 'args': []},
            {'type': 'command', 'name': 'workspace', 'args': []},
        ],
        sandbox,
    )
    assert not any(e.get('type') == 'turn.end' for e in events)


def test_ask_always_emits_turn_end(sandbox: Path):
    """对话无论成功失败都必须发 turn.end，否则前端永远卡住。"""
    events = _run([{'type': 'ask', 'text': '你好'}], sandbox)
    assert any(e.get('type') == 'turn.end' for e in events)


def test_unknown_command_reports_error(sandbox: Path):
    events = _run([{'type': 'command', 'name': 'nonexistent', 'args': []}], sandbox)
    assert any(e.get('type') == 'error' for e in events)