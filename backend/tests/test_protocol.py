"""协议测试：序列化、解析与容错。"""

from __future__ import annotations

import json

from devmentor import protocol as proto
from devmentor.protocol import Event, MenuOption, Request, ToolState


def test_request_roundtrip():
    req = Request(type="ask", text="你好")
    parsed = Request.parse(req.to_json())

    assert parsed is not None
    assert parsed.type == "ask"
    assert parsed.text == "你好"


def test_parse_rejects_bad_json():
    assert Request.parse("{not json") is None
    assert Request.parse("") is None
    assert Request.parse("   ") is None


def test_parse_rejects_unknown_type():
    assert Request.parse('{"type":"hack"}') is None


def test_parse_rejects_non_object():
    assert Request.parse("[1,2,3]") is None


def test_parse_command_with_args():
    parsed = Request.parse('{"type":"command","name":"mode","args":["read-only"]}')

    assert parsed is not None
    assert parsed.name == "mode"
    assert parsed.args == ["read-only"]


def test_event_drops_empty_fields():
    """空字段不序列化，让前端日志和测试断言更干净。"""
    payload = json.loads(proto.system("hi").to_json())

    assert payload == {"type": "system", "text": "hi"}


def test_event_keeps_nonempty_complex_fields():
    ev = proto.tool_call("arch_scan", {"path": "/tmp"})
    payload = json.loads(ev.to_json())

    assert payload["name"] == "arch_scan"
    assert payload["input"] == {"path": "/tmp"}


def test_menu_serializes_options():
    ev = proto.menu("选择厂商：", [MenuOption(value="1", label="OpenRouter", desc="免费")])
    payload = json.loads(ev.to_json())

    assert payload["title"] == "选择厂商："
    assert payload["options"][0]["label"] == "OpenRouter"


def test_tool_result_carries_state():
    ev = proto.tool_result("arch_scan", ToolState.DENIED, "被拒绝")
    payload = json.loads(ev.to_json())

    assert payload["state"] == "denied"


def test_ensure_ascii_false_keeps_chinese_readable():
    """序列化成 UTF-8 而非 \\uXXXX，便于开发和 grep。"""
    raw = proto.system("中文").to_json()
    assert "中文" in raw


def test_ready_event_shape():
    ev = proto.ready({"session": "s1", "user": "u"}, "openai:x")
    payload = json.loads(ev.to_json())

    assert payload["type"] == "ready"
    assert payload["model"] == "openai:x"
    assert payload["session"]["session"] == "s1"
