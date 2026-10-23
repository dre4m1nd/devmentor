# -*- coding: utf-8 -*-
"""依赖声明检查：pyproject 必须覆盖代码实际 import 的第三方包。

这条曾经出过问题：代码 import tree_sitter_java，但 pyproject 只声明了
agentscope 和 pydantic。agentscope 依赖 tree_sitter 但不依赖
tree_sitter_java，所以照 README 装完，一用架构分析就 ModuleNotFoundError。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

BACKEND = Path(__file__).resolve().parents[1]
PKG = BACKEND / "devmentor"

#: import 名 -> PyPI 包名（两者不一致时需要映射）
IMPORT_TO_PACKAGE = {
    "agentscope": "agentscope",
    "tree_sitter": "tree-sitter",
    "tree_sitter_java": "tree-sitter-java",
}

#: 只在开发/测试时需要的包，不进运行时依赖
DEV_ONLY = {"pytest"}


def _declared_deps() -> list[str]:
    cfg = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    return cfg["project"]["dependencies"]


def _runtime_imports() -> set[str]:
    """收集包代码里 import 的顶层模块名。"""
    found: set[str] = set()
    for py in PKG.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        for line in py.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(?:from|import)\s+([a-zA-Z_][\w]*)", line)
            if m:
                found.add(m.group(1))
    return found


def test_all_third_party_imports_are_declared():
    """每个非标准库 import 都要在 pyproject 里声明。"""
    stdlib = set(sys.stdlib_module_names)
    imports = {
        m
        for m in _runtime_imports()
        if m not in stdlib and m != "devmentor" and m not in DEV_ONLY
    }
    declared = " ".join(_declared_deps()).lower().replace("_", "-")

    missing = []
    for mod in sorted(imports):
        pkg = IMPORT_TO_PACKAGE.get(mod)
        if pkg is None:
            missing.append(f"{mod}（未知包，需在映射表里补充）")
        elif pkg not in declared:
            missing.append(f"{mod} -> {pkg}")

    assert not missing, "pyproject 缺少依赖声明: " + ", ".join(missing)


def test_tree_sitter_java_is_declared():
    """单独锁住这个：agentscope 不带它，漏了会导致 /arch 崩溃。"""
    declared = " ".join(_declared_deps()).lower()
    assert "tree-sitter-java" in declared, (
        "必须显式声明 tree-sitter-java：agentscope 只提供 tree_sitter，"
        "不提供 tree_sitter_java"
    )


def test_declared_packages_are_importable():
    """声明了就得能装上并用——防止写错包名。"""
    for mod in ("agentscope", "pydantic", "tree_sitter", "tree_sitter_java"):
        __import__(mod)


def test_pyproject_is_valid_toml():
    cfg = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    assert cfg["project"]["requires-python"] == ">=3.11"
    assert cfg["project"]["dependencies"]

# ---------------------------------------------------------------- 无用依赖

def test_no_unused_runtime_dependencies():
    """声明的运行时依赖都应该真的被 import。

    曾经声明过 pydantic（agentscope 的传递依赖，代码没直接用）
    和 tomli（requires-python 已是 >=3.11，永远用不上）。
    多余声明会增大安装体积与攻击面，也让人误以为项目直接依赖它们。
    """
    import sys

    declared = _declared_deps()
    imports = _runtime_imports()

    unused = []
    for d in declared:
        pkg = d.split(">")[0].split("=")[0].split("<")[0].split("[")[0].strip()
        mod = IMPORT_TO_PACKAGE.get(pkg, pkg.replace("-", "_"))
        if mod not in imports:
            unused.append(pkg)

    assert not unused, f"这些依赖声明了但代码没 import: {unused}"


def test_python_requirement_excludes_old_versions():
    """requires-python 是 3.11+，就不该留 3.10 及以下的兼容依赖。"""
    cfg = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    requires = cfg["project"]["requires-python"]

    assert "3.11" in requires or "3.12" in requires
    # tomli 是 tomllib 的 3.10 替代品，3.11+ 用不上
    for d in cfg["project"]["dependencies"]:
        assert "tomli" not in d.lower(), "3.11+ 不需要 tomli，标准库已有 tomllib"
