"""扫描器测试：验证 tree-sitter 提取的结构事实正确。"""

from __future__ import annotations

from pathlib import Path

import pytest

from devmentor.arch.scanner import scan, scan_file


def write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


SIMPLE = """
package com.acme.shop;

import com.acme.shop.user.UserService;

/**
 * 订单服务。
 */
public class OrderService {
    private int count;

    public void place() {
        count++;
    }

    public int get() {
        return count;
    }
}
"""


def test_extracts_package_and_type_name(tmp_path: Path):
    write(tmp_path, "src/main/java/com/acme/shop/OrderService.java", SIMPLE)
    snap = scan(tmp_path)

    assert snap.file_count == 1
    f = snap.files[0]
    assert f.package == "com.acme.shop"
    assert f.type_name == "OrderService"


def test_counts_methods(tmp_path: Path):
    write(tmp_path, "src/main/java/com/acme/shop/OrderService.java", SIMPLE)
    f = scan(tmp_path).files[0]

    # place() 与 get()，构造函数不算（本例没有）
    assert f.method_count == 2


def test_detects_test_files(tmp_path: Path):
    write(tmp_path, "src/main/java/com/acme/Prod.java", "package com.acme; class Prod {}")
    write(tmp_path, "src/test/java/com/acme/ProdTest.java", "package com.acme; class ProdTest {}")

    snap = scan(tmp_path)
    assert snap.file_count == 2
    assert snap.test_file_count == 1


def test_skips_build_and_ide_dirs(tmp_path: Path):
    write(tmp_path, "src/main/java/A.java", "class A {}")
    write(tmp_path, "target/generated/B.java", "class B {}")
    write(tmp_path, ".idea/C.java", "class C {}")
    write(tmp_path, "node_modules/D.java", "class D {}")

    snap = scan(tmp_path)
    paths = [f.path for f in snap.files]
    assert paths == ["src/main/java/A.java"]


def test_captures_imports_for_dependency_graph(tmp_path: Path):
    write(tmp_path, "src/main/java/com/acme/shop/OrderService.java", SIMPLE)
    f = scan(tmp_path).files[0]

    assert any("UserService" in imp for imp in f.imports)


def test_survives_unparseable_file(tmp_path: Path):
    """坏一个文件不该让整次扫描失败。"""
    write(tmp_path, "src/main/java/Good.java", "package a; class Good { void f() {} }")
    write(tmp_path, "src/main/java/Broken.java", "this is not java at all {{{")

    snap = scan(tmp_path)
    assert snap.file_count == 2  # 语法树容错，仍能产出记录


def test_line_count_includes_last_line(tmp_path: Path):
    write(tmp_path, "src/main/java/A.java", "class A {\n  int x;\n}")
    f = scan(tmp_path).files[0]
    assert f.line_count == 3


def test_scan_file_returns_none_for_unreadable(tmp_path: Path):
    missing = tmp_path / "Missing.java"
    assert scan_file(missing, tmp_path) is None


def test_root_package_is_common_prefix(tmp_path: Path):
    write(tmp_path, "a/OrderService.java", "package com.acme.shop.order; class OrderService {}")
    write(tmp_path, "b/UserService.java", "package com.acme.shop.user; class UserService {}")

    snap = scan(tmp_path)
    assert snap.root_package == "com.acme.shop"
