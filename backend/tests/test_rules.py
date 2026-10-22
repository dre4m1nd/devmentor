"""架构规则测试：每条规则的阈值与噪音过滤。"""

from __future__ import annotations

from devmentor.arch.model import ProjectSnapshot, SourceFileInfo
from devmentor.arch.rules import (
    FLAT_PACKAGE_FILES,
    GOD_CLASS_LINES,
    LONG_METHOD_LINES,
    MIN_AVG_METHOD_LINES,
    TOO_MANY_METHODS,
    Severity,
    check,
    find_cycles,
)


def f(
    path: str = "src/main/java/A.java",
    package: str = "com.acme",
    type_name: str = "A",
    line_count: int = 50,
    method_count: int = 5,
    max_method_lines: int = 10,
    comment_lines: int = 5,
    imports: list[str] | None = None,
) -> SourceFileInfo:
    return SourceFileInfo(
        path=path,
        package=package,
        type_name=type_name,
        line_count=line_count,
        method_count=method_count,
        max_method_lines=max_method_lines,
        comment_lines=comment_lines,
        imports=imports or [],
    )


def snap(*files: SourceFileInfo) -> ProjectSnapshot:
    return ProjectSnapshot(files=list(files))


def rules_hit(s: ProjectSnapshot) -> list[str]:
    return [x.rule for x in check(s)]


# ---------------------------------------------------------------- god-class

def test_god_class_triggers_over_threshold():
    s = snap(f(line_count=GOD_CLASS_LINES + 1))
    assert "god-class" in rules_hit(s)


def test_god_class_not_triggered_at_threshold():
    s = snap(f(line_count=GOD_CLASS_LINES))
    assert "god-class" not in rules_hit(s)


def test_god_class_ignores_test_files():
    s = snap(f(path="src/test/java/ATest.java", line_count=GOD_CLASS_LINES + 100))
    assert "god-class" not in rules_hit(s)


# ---------------------------------------------------------------- long-method

def test_long_method_triggers_over_threshold():
    s = snap(f(max_method_lines=LONG_METHOD_LINES + 1))
    assert "long-method" in rules_hit(s)


def test_long_method_evidence_has_line_number():
    s = snap(f(max_method_lines=LONG_METHOD_LINES + 5))
    finding = next(x for x in check(s) if x.rule == "long-method")
    assert str(LONG_METHOD_LINES + 5) in finding.evidence


# ---------------------------------------------------------------- many-methods

def test_many_methods_triggers():
    s = snap(f(method_count=TOO_MANY_METHODS + 1, line_count=(TOO_MANY_METHODS + 1) * 10))
    assert "many-methods" in rules_hit(s)


def test_many_methods_filters_pure_pojo():
    """getter/setter 堆出来的类不该被报成"职责过多"。"""
    s = snap(
        f(
            method_count=TOO_MANY_METHODS + 5,
            line_count=(TOO_MANY_METHODS + 5) * (MIN_AVG_METHOD_LINES - 2),
        )
    )
    assert "many-methods" not in rules_hit(s)


# ---------------------------------------------------------------- flat-package

def test_flat_package_triggers_for_leaf_package():
    files = [f(path=f"src/main/java/P{i}.java", package="com.acme.flat") for i in range(FLAT_PACKAGE_FILES)]
    assert "flat-package" in rules_hit(snap(*files))


def test_flat_package_not_triggered_when_has_subpackage():
    files = [f(path=f"src/main/java/P{i}.java", package="com.acme") for i in range(FLAT_PACKAGE_FILES)]
    files.append(f(path="src/main/java/Sub.java", package="com.acme.sub"))
    assert "flat-package" not in rules_hit(snap(*files))


# ---------------------------------------------------------------- cycles

def test_find_cycles_detects_simple_cycle():
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
    cycles = find_cycles(graph)
    assert len(cycles) == 1
    assert cycles[0][0] == "a"  # 以最小节点开头


def test_find_cycles_deduplicates_rotations():
    """a→b→c→a 与 b→c→a→b 是同一个环，只报一次。"""
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
    assert len(find_cycles(graph)) == 1


def test_find_cycles_returns_empty_for_dag():
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    assert find_cycles(graph) == []


def test_package_cycle_rule_reports():
    a = f(package="com.acme.a", imports=["com.acme.b.B"])
    b = f(path="src/main/java/b/B.java", package="com.acme.b", imports=["com.acme.a.A"])
    s = snap(a, b)
    assert "package-cycle" in rules_hit(s)


# ---------------------------------------------------------------- layer violation

def test_layer_violation_repository_depending_on_service():
    repo = f(
        path="src/main/java/repo/R.java",
        package="com.acme.repository",
        imports=["com.acme.service.S"],
    )
    svc = f(path="src/main/java/svc/S.java", package="com.acme.service")
    assert "layer-violation" in rules_hit(snap(repo, svc))


def test_layer_violation_not_triggered_for_normal_direction():
    svc = f(
        path="src/main/java/svc/S.java",
        package="com.acme.service",
        imports=["com.acme.repository.R"],
    )
    repo = f(path="src/main/java/repo/R.java", package="com.acme.repository")
    assert "layer-violation" not in rules_hit(snap(svc, repo))


# ---------------------------------------------------------------- no-tests

def test_no_tests_triggers_for_larger_project():
    files = [f(path=f"src/main/java/P{i}.java") for i in range(10)]
    assert "no-tests" in rules_hit(snap(*files))


def test_no_tests_not_triggered_for_small_project():
    files = [f(path=f"src/main/java/P{i}.java") for i in range(3)]
    assert "no-tests" not in rules_hit(snap(*files))


# ---------------------------------------------------------------- no-comments

def test_no_comments_triggers_for_three_large_uncommented_classes():
    files = [
        f(path=f"src/main/java/P{i}.java", line_count=150, comment_lines=0) for i in range(3)
    ]
    assert "no-comments" in rules_hit(snap(*files))


def test_no_comments_not_triggered_when_commented():
    files = [
        f(path=f"src/main/java/P{i}.java", line_count=150, comment_lines=10) for i in range(3)
    ]
    assert "no-comments" not in rules_hit(snap(*files))


# ---------------------------------------------------------------- mixed-roots

def test_mixed_roots_triggers():
    s = snap(f(package="com.acme"), f(path="src/main/java/B.java", package="org.other"))
    assert "mixed-roots" in rules_hit(s)


def test_mixed_roots_not_triggered_for_single_root():
    s = snap(f(package="com.acme"), f(path="src/main/java/B.java", package="com.acme.sub"))
    assert "mixed-roots" not in rules_hit(s)


# ---------------------------------------------------------------- ordering / rendering

def test_findings_sorted_by_severity():
    s = snap(f(line_count=GOD_CLASS_LINES + 1), f(path="src/main/java/B.java", package="org.x"))
    findings = check(s)
    ranks = [x.severity.rank for x in findings]
    assert ranks == sorted(ranks)


def test_render_is_single_line_with_evidence():
    s = snap(f(max_method_lines=LONG_METHOD_LINES + 5))
    finding = next(x for x in check(s) if x.rule == "long-method")
    rendered = finding.render()
    assert "\n" not in rendered
    assert "证据" in rendered
    assert "建议" in rendered
