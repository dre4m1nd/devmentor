# -*- coding: utf-8 -*-
"""用真实 Java 源码验证架构分析。

之前的规则测试全部用手工构造的 SourceFileInfo，从未跑过真实源码。
这组测试补上这一层：写真的 .java 文件，让引擎实际扫描，
确认能检出已知问题、且不误报结构良好的项目。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from devmentor.arch import analyze


def _w(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _rules(root: Path) -> list[str]:
    return [f.rule for f in analyze(root).findings]


# ---------------------------------------------------------------- 应检出

def test_detects_god_class(tmp_path: Path):
    body = []
    for i in range(30):
        body.append(f"    public int m{i}(int x) {{")
        body += [f"        x = x + {j};" for j in range(18)]
        body += ["        return x;", "    }"]
    _w(tmp_path, "src/main/java/com/acme/big/God.java",
       "package com.acme.big;\npublic class God {\n" + "\n".join(body) + "\n}\n")

    assert "god-class" in _rules(tmp_path)


def test_detects_long_method(tmp_path: Path):
    lines = ["package com.acme;", "public class Long {", "    public void run() {"]
    lines += [f"        int v{i} = {i};" for i in range(100)]
    lines += ["    }", "}", ""]
    _w(tmp_path, "src/main/java/com/acme/Long.java", "\n".join(lines))

    assert "long-method" in _rules(tmp_path)


def test_detects_flat_package(tmp_path: Path):
    for i in range(25):
        _w(tmp_path, f"src/main/java/com/acme/flat/C{i}.java",
           f"package com.acme.flat;\npublic class C{i} {{ }}")

    assert "flat-package" in _rules(tmp_path)


def test_detects_package_cycle(tmp_path: Path):
    _w(tmp_path, "src/main/java/com/acme/a/A.java",
       "package com.acme.a;\nimport com.acme.b.B;\npublic class A { B b; }")
    _w(tmp_path, "src/main/java/com/acme/b/B.java",
       "package com.acme.b;\nimport com.acme.a.A;\npublic class B { A a; }")

    findings = analyze(tmp_path).findings
    cycles = [f for f in findings if f.rule == "package-cycle"]

    assert cycles
    # 证据里要标出完整的环
    assert "→" in cycles[0].evidence


def test_detects_layer_violation(tmp_path: Path):
    _w(tmp_path, "src/main/java/com/acme/shop/service/Svc.java",
       "package com.acme.shop.service;\npublic class Svc { }")
    _w(tmp_path, "src/main/java/com/acme/shop/repository/Repo.java",
       "package com.acme.shop.repository;\nimport com.acme.shop.service.Svc;\npublic class Repo { Svc s; }")

    assert "layer-violation" in _rules(tmp_path)


def test_detects_no_tests(tmp_path: Path):
    for i in range(12):
        _w(tmp_path, f"src/main/java/com/acme/C{i}.java",
           f"package com.acme;\npublic class C{i} {{ }}")

    assert "no-tests" in _rules(tmp_path)


def test_detects_many_methods_with_substance(tmp_path: Path):
    body = []
    for i in range(30):
        body.append(f"    public int m{i}(int x) {{")
        body += [f"        x = x * {j + 2} + {j};" for j in range(12)]
        body += ["        return x;", "    }"]
    _w(tmp_path, "src/main/java/com/acme/Rich.java",
       "package com.acme;\npublic class Rich {\n" + "\n".join(body) + "\n}\n")

    assert "many-methods" in _rules(tmp_path)


# ---------------------------------------------------------------- 不应误报

def test_well_structured_project_has_no_findings(tmp_path: Path):
    """分层清晰、有注释、小类、有测试的项目不该有任何命中。"""
    _w(tmp_path, "src/main/java/com/acme/shop/ShopApp.java",
       "package com.acme.shop;\n\n/** 入口。 */\npublic class ShopApp {\n"
       "    public static void main(String[] a) { }\n}\n")
    _w(tmp_path, "src/main/java/com/acme/shop/order/OrderService.java",
       "package com.acme.shop.order;\n\n/** 订单业务。 */\npublic class OrderService {\n"
       "    public void place() { }\n}\n")
    _w(tmp_path, "src/main/java/com/acme/shop/user/UserService.java",
       "package com.acme.shop.user;\n\n/** 用户业务。 */\npublic class UserService { }\n")
    _w(tmp_path, "src/test/java/com/acme/shop/OrderServiceTest.java",
       "package com.acme.shop;\npublic class OrderServiceTest { }\n")

    assert analyze(tmp_path).findings == []


def test_pure_pojo_not_flagged_as_many_methods(tmp_path: Path):
    """30 个 getter 是纯 POJO，不该报"方法过多"。"""
    body = []
    for i in range(30):
        body.append(f"    private int f{i};")
        body.append(f"    public int get{i}() {{ return f{i}; }}")
    _w(tmp_path, "src/main/java/com/acme/Pojo.java",
       "package com.acme;\npublic class Pojo {\n" + "\n".join(body) + "\n}\n")

    assert "many-methods" not in _rules(tmp_path)


def test_has_tests_suppresses_no_tests(tmp_path: Path):
    for i in range(12):
        _w(tmp_path, f"src/main/java/com/acme/C{i}.java",
           f"package com.acme;\npublic class C{i} {{ }}")
    _w(tmp_path, "src/test/java/com/acme/C0Test.java",
       "package com.acme;\npublic class C0Test { }")

    assert "no-tests" not in _rules(tmp_path)


def test_normal_layering_not_flagged(tmp_path: Path):
    """service 依赖 repository 是正常方向，不该报分层违规。"""
    _w(tmp_path, "src/main/java/com/acme/shop/repository/Repo.java",
       "package com.acme.shop.repository;\npublic class Repo { }")
    _w(tmp_path, "src/main/java/com/acme/shop/service/Svc.java",
       "package com.acme.shop.service;\nimport com.acme.shop.repository.Repo;\npublic class Svc { Repo r; }")

    assert "layer-violation" not in _rules(tmp_path)


def test_acyclic_dependencies_not_flagged(tmp_path: Path):
    _w(tmp_path, "src/main/java/com/acme/a/A.java",
       "package com.acme.a;\nimport com.acme.b.B;\npublic class A { B b; }")
    _w(tmp_path, "src/main/java/com/acme/b/B.java",
       "package com.acme.b;\npublic class B { }")

    assert "package-cycle" not in _rules(tmp_path)
