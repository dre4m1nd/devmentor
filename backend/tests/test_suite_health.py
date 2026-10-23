# -*- coding: utf-8 -*-
"""测试套件自身的健康。

写了三十多轮测试之后，测试代码本身也需要体检：
  - 有没有"永远通过"的假测试（无断言、断言恒真）
  - 有没有重复的测试名
  - 每个源码模块是否都被提到
  - 有没有测试自己启动 pytest 子进程（递归且极慢）

曾经有一条"验证快测 60 秒内完成"的测试，它自己 subprocess 跑一遍
pytest——递归且耗时 138 秒，最后因为自己拖慢而失败。性能交给 CI 计时，
不在测试里递归验证。
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TESTS = BACKEND / "tests"
PKG = BACKEND / "devmentor"


def _test_functions():
    """返回 [(file, func_name, node)]。"""
    for p in sorted(TESTS.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                yield p, node.name, node


# ---------------------------------------------------------------- 假测试

def test_every_test_has_assertions_or_calls():
    """没有断言也不调用被测代码的测试是摆设。

    合理的例外是"验证不抛异常"的测试——调用本身就是断言。
    """
    problems = []

    for p, name, node in _test_functions():
        src = ast.unparse(node)
        has_assert = ("assert " in src or "pytest.raises" in src)
        has_call = "(" in src

        if not has_assert and not has_call:
            problems.append(f"{p.name}::{name}")

    assert not problems, "既无断言也不调用被测代码:\n" + "\n".join(problems)


def test_no_trivially_true_assertions():
    """assert True 这类恒真断言是自欺欺人。"""
    bad = []

    for p, name, node in _test_functions():
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assert):
                t = ast.unparse(sub.test)
                if t in ("True", "1", "2", "None is None"):
                    bad.append(f"{p.name}::{name} -> {t}")

    assert not bad, "\n".join(bad)


def test_no_skip_only_tests():
    """整段只有 pytest.skip 的测试没有价值。"""
    bad = []

    for p, name, node in _test_functions():
        stmts = [
            s for s in node.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
        ]
        if len(stmts) == 1 and ast.unparse(stmts[0]).startswith("pytest.skip"):
            bad.append(f"{p.name}::{name}")

    assert not bad, "\n".join(bad)


# ---------------------------------------------------------------- 命名

def test_no_duplicate_test_names_within_file():
    """同一文件内不能有同名测试函数（后者会覆盖前者）。"""
    for p in sorted(TESTS.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        names = [
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
        ]
        dups = {k for k, v in Counter(names).items() if v > 1}
        assert not dups, f"{p.name} 有重复测试名: {dups}"


def test_test_files_follow_naming_convention():
    """测试文件应叫 test_*.py，pytest 才能收集到。"""
    for p in sorted(TESTS.glob("*.py")):
        assert p.name.startswith("test_"), f"{p.name} 不符合 test_*.py 命名"


# ---------------------------------------------------------------- 规模

def test_no_oversized_test_files():
    """单文件超过 500 行就该拆分，否则难以定位。"""
    big = [
        f"{p.name}: {len(p.read_text(encoding='utf-8').splitlines())} 行"
        for p in sorted(TESTS.glob("*.py"))
        if len(p.read_text(encoding="utf-8").splitlines()) > 500
    ]
    assert not big, "\n".join(big)


def test_suite_is_substantial():
    """测试套件要有一定规模才有防护意义。"""
    total = sum(1 for _ in _test_functions())
    assert total >= 300, f"只有 {total} 个测试，规模不足"


# ---------------------------------------------------------------- 覆盖

def test_every_source_module_has_test_reference():
    """每个源码模块至少被某个测试文件提到。

    这是弱检查：提到不等于覆盖，但"没人提"肯定没覆盖。
    """
    all_tests = "\n".join(p.read_text(encoding="utf-8") for p in TESTS.glob("*.py"))
    orphans = [
        src.name
        for src in sorted(PKG.rglob("*.py"))
        if "__pycache__" not in str(src)
        and src.name != "__init__.py"
        and src.stem not in all_tests
    ]
    assert not orphans, f"这些模块没有任何测试提到: {orphans}"


# ---------------------------------------------------------------- 速度

def test_no_test_spawns_pytest_subprocess():
    """测试不应自己启动 pytest 子进程。

    那会造成递归：套件里有一条测试跑整套套件，耗时翻倍且结论失真。
    性能交给 CI 计时把关。

    用 AST 找 subprocess.run/Popen 调用，而不是搜字符串——否则这条
    测试会因为自己包含 "pytest" 字样而误报自己。
    """
    offenders = []

    for p in sorted(TESTS.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # subprocess.run([...]) / subprocess.Popen([...])
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            if node.func.attr not in ("run", "Popen", "call", "check_output"):
                continue
            # 取参数里的字符串常量
            for arg in node.args:
                strs = [
                    s.value
                    for s in ast.walk(arg)
                    if isinstance(s, ast.Constant) and isinstance(s.value, str)
                ]
                if "pytest" in strs or "-m pytest" in strs:
                    offenders.append(f"{p.name}:{node.lineno}")
                    break

    assert not offenders, f"这些测试会启动 pytest 子进程: {offenders}"