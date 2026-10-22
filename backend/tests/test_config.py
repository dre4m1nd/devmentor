"""配置测试：凭据优先级、厂商目录、JDK 查找。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from devmentor.config import (
    PROVIDERS,
    CredentialStore,
    Settings,
    provider_by_id,
    provider_by_name,
    requires_key,
)


# ---------------------------------------------------------------- 厂商目录

def test_first_provider_is_free_one():
    """第一项必须是免费可用路径，否则"开箱即用"的承诺不成立。"""
    assert "OpenRouter" in PROVIDERS[0].label
    assert PROVIDERS[0].default_model.endswith(":free")


def test_provider_ids_are_contiguous():
    for i, p in enumerate(PROVIDERS):
        assert p.id == i + 1


def test_by_id_and_name():
    assert provider_by_id(1).provider == "openai"
    assert provider_by_id(999) is None
    assert provider_by_name("ollama").id == 6
    assert provider_by_name(None) is None


def test_ollama_needs_no_key():
    ollama = provider_by_name("ollama")
    assert requires_key(ollama) is False


def test_cloud_providers_need_key():
    for p in PROVIDERS:
        if p.provider != "ollama":
            assert requires_key(p) is True


# ---------------------------------------------------------------- 凭据存储

def test_credentials_roundtrip(tmp_path: Path):
    store = CredentialStore(tmp_path / "credentials")
    store.save("deepseek", "sk-deepseek-123")

    assert store.find("deepseek") == "sk-deepseek-123"


def test_credentials_overwrite(tmp_path: Path):
    store = CredentialStore(tmp_path / "credentials")
    store.save("openai", "old")
    store.save("openai", "new")

    assert store.load() == {"openai": "new"}


def test_credentials_case_insensitive(tmp_path: Path):
    store = CredentialStore(tmp_path / "credentials")
    store.save("OpenAI", "k1")

    assert store.find("openai") == "k1"
    assert store.find("OPENAI") == "k1"


def test_credentials_remove_only_target(tmp_path: Path):
    store = CredentialStore(tmp_path / "credentials")
    store.save("openai", "k1")
    store.save("deepseek", "k2")
    store.remove("openai")

    assert store.find("openai") is None
    assert store.find("deepseek") == "k2"


def test_credentials_ignores_comments_and_bad_lines(tmp_path: Path):
    file = tmp_path / "credentials"
    file.write_text(
        "# comment\n\nno-equals-sign\nopenai=sk-abc\n  deepseek = sk-def  \n",
        encoding="utf-8",
    )

    store = CredentialStore(file)
    assert store.load() == {"openai": "sk-abc", "deepseek": "sk-def"}


def test_credentials_missing_file_returns_empty(tmp_path: Path):
    store = CredentialStore(tmp_path / "nope")
    assert store.load() == {}


# ---------------------------------------------------------------- 优先级

def test_env_var_beats_local_credentials(tmp_path: Path, monkeypatch):
    """CI 注入的 Key 必须盖掉开发机 /login 存的个人 Key。"""
    store = CredentialStore(tmp_path / "credentials")
    store.save("openai", "local-key")

    monkeypatch.setenv("OPENAI_API_KEY", "ci-key")
    s = Settings()
    s.model_id = "openai:gpt-4.1-mini"

    assert s.resolve_api_key(store) == "ci-key"


def test_local_credentials_used_when_no_env(tmp_path: Path, monkeypatch):
    store = CredentialStore(tmp_path / "credentials")
    store.save("openai", "local-key")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = Settings()
    s.model_id = "openai:gpt-4.1-mini"

    assert s.resolve_api_key(store) == "local-key"


def test_settings_parses_provider_and_model():
    s = Settings()
    s.model_id = "openai:minimax/minimax-m3.1-flash:free"

    assert s.provider == "openai"
    assert s.model_name == "minimax/minimax-m3.1-flash:free"
