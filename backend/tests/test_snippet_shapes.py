# -*- coding: utf-8 -*-
"""Java 片段包装：字段/方法/类型声明各自的处理。

起因：验证课程代码块时发现用户贴一个字段声明（如
"private volatile boolean running = true;"）会被塞进 main 方法，
报"非法的表达式开始"——错误信息对用户毫无帮助，他写的明明是合法字段。

真实的教学习惯是贴一个字段、一段方法问"这样写对吗"，
所以这三种片段形态都要给出准确反馈。
"""

from __future__ import annotations

import pytest

from devmentor.tools.java_snippet import _normalize, _single_decl_kind


# ---------------------------------------------------------------- 片段分类

@pytest.mark.parametrize(
    "code,expected",
    [
        ("private volatile boolean running = true;", "field"),
        ("private int a = 1;\nprivate String b = \"x\";", "field"),
        ("public int add(int x, int y) { return x + y; }", "method"),
        ("int a = 1;\nSystem.out.println(a);", None),
        ("record Order(String c, int a) {}", None),
        ("", None),
    ],
)
def test_classify_snippet(code, expected):
    assert _single_decl_kind(code) == expected


# ---------------------------------------------------------------- 包装结果

def test_field_snippet_wrapped_into_class_body():
    """字段要进类体，不是方法体。"""
    normalized = _normalize("private volatile boolean running = true;")

    assert "class Snippet" in normalized
    # 字段在 main 之前
    field_pos = normalized.find("private volatile")
    main_pos = normalized.find("main(String[] args)")
    assert field_pos > 0 and main_pos > field_pos


def test_method_snippet_wrapped_into_class_body():
    normalized = _normalize("public int add(int x, int y) { return x + y; }")

    assert "class Snippet" in normalized
    assert "public int add(int x, int y)" in normalized


def test_plain_statement_wrapped_into_main():
    normalized = _normalize("int a = 1;\nSystem.out.println(a);")

    main_pos = normalized.find("main(String[] args)")
    stmt_pos = normalized.find("int a = 1;")
    assert stmt_pos > main_pos, "普通语句应放进 main 方法体"


def test_type_declaration_not_wrapped():
    """类型声明原样返回，由 run_snippet 单独解释。"""
    code = "record Order(String c, int a) {}"
    assert _normalize(code) == code


def test_public_type_not_wrapped():
    code = "public class A { }"
    assert _normalize(code) == code


# ---------------------------------------------------------------- 实际运行

def test_field_snippet_runs_without_compile_error():
    from devmentor.tools.java_snippet import run_snippet

    result = run_snippet("private volatile boolean running = true;", timeout_seconds=15)

    assert "非法的表达式开始" not in result, "字段片段不该被当成语句"
    assert "已编译通过" in result or "退出码：0" in result


def test_method_snippet_runs_without_compile_error():
    from devmentor.tools.java_snippet import run_snippet

    result = run_snippet("public int add(int a, int b) { return a + b; }", timeout_seconds=15)

    assert "非法的表达式开始" not in result


def test_type_declaration_explained_not_raw_error():
    """类型声明没有 main 时，要解释原因，不能把 JDK 原话直接抛给用户。"""
    from devmentor.tools.java_snippet import run_snippet

    result = run_snippet("record Order(String c, int a) {}", timeout_seconds=15)

    assert "编译通过" in result
    assert "类型声明" in result
    assert "想运行它" in result


def test_plain_statement_still_runs():
    from devmentor.tools.java_snippet import run_snippet

    result = run_snippet("int a = 41 + 1;\nSystem.out.println(a);", timeout_seconds=15)

    assert "42" in result
