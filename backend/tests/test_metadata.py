# -*- coding: utf-8 -*-
"""项目元数据与 UI 文案的一致性。

Round 4 把定位从"Java 编程导师"改成"编程导师"时，改了 banner、README
和 AGENTS.md，但漏了 package.json / pyproject.toml / __init__.py 的
description，导致元数据里还写着 Java。这组测试防止同类不一致。
"""

from __future__ import annotations

import json

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def test_pyproject_description_is_not_java_only():
    cfg = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    desc = cfg["project"]["description"].lower()
    assert "java programming mentor" not in desc, (
        "pyproject 描述仍写着 Java 专属定位，应为通用编程导师"
    )
    assert "mentor" in desc


def test_package_json_description_is_not_java_only():
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    desc = pkg["description"].lower()
    assert "java programming mentor" not in desc
    assert "mentor" in desc


def test_package_name_is_consistent():
    """后端包名与前端包名都应是 devmentor 系。"""
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    fe = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"].startswith("devmentor")
    assert fe["name"].startswith("devmentor")


def test_root_scripts_have_expected_entries():
    """根脚本要能覆盖：构建、测试（快/全）、启动。"""
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = pkg["scripts"]
    for key in ("build", "test", "test:fast", "start"):
        assert key in scripts, f"缺少 npm 脚本: {key}"


def test_frontend_has_build_script():
    fe = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert "build" in fe["scripts"]
    assert fe["scripts"]["build"], "build 脚本不能为空"


def test_python_package_name_matches():
    init = (BACKEND / "devmentor" / "__init__.py").read_text(encoding="utf-8")
    assert '__version__' in init, "包应声明版本"
    assert "Java programming mentor" not in init
