# -*- coding: utf-8 -*-
"""错误翻译：每种失败都要给出可操作的下一步。

"Connection error." 这种原始回显对用户没有帮助——
不知道是断网、代理还是地址写错。这组测试锁住常见失败都有中文指引。
"""

from __future__ import annotations

import pytest

from devmentor.service import _friendly


def _first_line(msg: str) -> str:
    return _friendly(Exception(msg)).splitlines()[0]


# ---------------------------------------------------------------- HTTP 状态码

@pytest.mark.parametrize(
    "msg,keyword",
    [
        ("Error code: 401 - Unauthorized", "API Key"),
        ("invalid api key", "API Key"),
        ("Error code: 402 - Insufficient credits", "额度"),
        ("Error code: 403 - Forbidden", "拒绝"),
        ("Error code: 429 - Rate limit exceeded", "限流"),
    ],
)
def test_http_status_errors_are_translated(msg: str, keyword: str):
    assert keyword in _first_line(msg)


# ---------------------------------------------------------------- 连接层失败

def test_connection_error_mentions_network_and_base_url():
    """最容易被看到的一类：只回显 Connection error 没有指导意义。"""
    line = _first_line("Connection error.")
    assert "连接" in line
    assert "base_url" in line or "网络" in line


def test_dns_failure_mentions_domain_resolution():
    """直接透传的 DNS 错误走解析分支。"""
    line = _first_line("[Errno -2] Name or service not known")
    assert "域名解析" in line


def test_wrapped_dns_failure_still_actionable():
    """httpx 会把 DNS 错误包装成 "Connection error."，
    此时落到连接失败分支——提示里要包含地址与网络，同样可操作。"""
    line = _first_line("Connection error.")
    assert "base_url" in line or "网络" in line


def test_ssl_failure_mentions_certificate():
    line = _first_line("SSL: CERTIFICATE_VERIFY_FAILED")
    assert "证书" in line or "TLS" in line


def test_proxy_failure_mentions_proxy_env():
    line = _first_line("Proxy connection failed")
    assert "代理" in line or "PROXY" in line


def test_timeout_mentions_retry():
    line = _first_line("The read operation timed out")
    assert "超时" in line


def test_connection_error_hints_ollama():
    """连不上时，"本地模型"是个可行的退路，值得提示。"""
    full = _friendly(Exception("Connection error."))
    assert "Ollama" in full or "本地" in full


# ---------------------------------------------------------------- 兜底

def test_unknown_error_passes_through():
    """认不出的错误原样返回，至少保留信息。"""
    assert _first_line("Something weird happened") == "Something weird happened"


def test_empty_message_falls_back_to_type_name():
    assert _friendly(Exception("")) == "Exception"


def test_original_message_is_preserved():
    """友好提示之上要保留原始信息，方便排查。"""
    raw = "Connection error."
    assert raw in _friendly(Exception(raw))