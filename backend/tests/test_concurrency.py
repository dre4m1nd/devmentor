# -*- coding: utf-8 -*-
"""并发安全：多进程同时读写凭据/会话文件时不能丢数据。

实测发现的问题：4 个进程同时 /login 不同厂商（各 100 次），
最终文件里只剩 2 个厂商，另外 2 个的凭据被覆盖丢失。
根因是 save() 的"读取-修改-写入"不是原子操作。

修法：加跨进程文件锁（.lock + O_EXCL，不依赖 fcntl，
Windows 上也可用），并把写入改成 os.replace 原子替换。
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

import pytest

from devmentor.config import CredentialStore


# ---------------------------------------------------------------- 辅助

def _save_many(cred_file: str, provider: str, times: int) -> None:
    """子进程：反复保存同一个 provider 的 key。"""
    store = CredentialStore(Path(cred_file))
    for i in range(times):
        store.save(provider, f"key-{i}")


def _remove_many(cred_file: str, provider: str, times: int) -> None:
    """子进程：反复删除同一个 provider。

    必须是模块级函数：Windows 用 spawn 启动子进程，无法 pickle 嵌套函数。
    """
    store = CredentialStore(Path(cred_file))
    for _ in range(times):
        store.remove(provider)


def _run_parallel(target, arg_lists, timeout=120):
    procs = [mp.Process(target=target, args=args) for args in arg_lists]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout)
    return [p.exitcode for p in procs]


# ---------------------------------------------------------------- 凭据并发

def test_concurrent_saves_do_not_lose_providers(tmp_path: Path):
    """这是修之前会失败的用例：4 个厂商并发写，一条都不能丢。"""
    cred = tmp_path / "credentials"
    providers = ["openai", "deepseek", "dashscope", "anthropic"]

    codes = _run_parallel(
        _save_many,
        [(str(cred), p, 50) for p in providers],
    )
    assert all(c == 0 for c in codes), f"子进程异常: {codes}"

    loaded = CredentialStore(cred).load()
    missing = set(providers) - set(loaded.keys())
    assert not missing, f"这些厂商的凭据被并发覆盖丢失: {sorted(missing)}"


def test_concurrent_save_same_provider_ends_with_valid_value(tmp_path: Path):
    """同一个厂商并发写，最终值必须是某个完整值，不能是半截。"""
    cred = tmp_path / "credentials"

    _run_parallel(_save_many, [(str(cred), "openai", 40) for _ in range(3)])

    loaded = CredentialStore(cred).load()
    assert "openai" in loaded
    assert loaded["openai"].startswith("key-"), f"值不完整: {loaded['openai']!r}"


def test_concurrent_save_and_remove_keeps_other_providers(tmp_path: Path):
    """一个进程删某个厂商时，不能把别的厂商一起抹掉。"""
    cred = tmp_path / "credentials"
    store = CredentialStore(cred)
    store.save("openai", "keep-me")
    store.save("deepseek", "k2")
    store.save("dashscope", "k3")

    _run_parallel(_remove_many, [(str(cred), "dashscope", 30)])

    loaded = CredentialStore(cred).load()
    assert loaded.get("openai") == "keep-me"
    assert loaded.get("deepseek") == "k2"
    assert "dashscope" not in loaded


# ---------------------------------------------------------------- 原子性

def test_write_is_atomic_no_partial_file(tmp_path: Path):
    """写入用临时文件 + 替换，不会留下半截 JSON/文本。"""
    cred = tmp_path / "credentials"
    store = CredentialStore(cred)
    store.save("openai", "k1")

    # 内容可完整解析
    text = cred.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line and not line.startswith("#"):
            assert "=" in line, f"出现半截行: {line!r}"


def test_no_tmp_file_left_behind(tmp_path: Path):
    cred = tmp_path / "credentials"
    CredentialStore(cred).save("openai", "k1")

    leftovers = list(tmp_path.glob("*.tmp"))
    assert not leftovers, f"残留临时文件: {leftovers}"


def test_no_lock_file_left_behind(tmp_path: Path):
    cred = tmp_path / "credentials"
    CredentialStore(cred).save("openai", "k1")

    leftovers = list(tmp_path.glob("*.lock"))
    assert not leftovers, f"残留锁文件: {leftovers}"


def test_lock_is_released_on_exception(tmp_path: Path):
    """_write 抛异常时锁也要释放，否则后续操作全被堵死。"""
    cred = tmp_path / "credentials"
    store = CredentialStore(cred)

    # 让目标路径不可写：先建一个同名目录
    cred.mkdir(parents=True, exist_ok=True)
    try:
        store.save("openai", "k1")
    except Exception:
        pass
    # 目录移除后应能正常保存（说明锁已释放）
    cred.rmdir()
    store.save("openai", "k2")
    assert CredentialStore(cred).load().get("openai") == "k2"