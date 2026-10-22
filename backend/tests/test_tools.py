"""服务与工具测试：不依赖网络，只验证确定性部分。"""

from __future__ import annotations

from pathlib import Path

from devmentor.config import Settings
from devmentor.tools import ArchitectureTools, CurriculumTools, ProgressTools


# ---------------------------------------------------------------- 课程

def test_curriculum_list_empty_when_missing(tmp_path: Path):
    tools = CurriculumTools(tmp_path)
    assert "没有" in tools.list_courses()


def test_curriculum_list_shows_courses(tmp_path: Path):
    (tmp_path / "curriculum").mkdir()
    (tmp_path / "curriculum" / "01-intro.md").write_text("# 入门\n正文", encoding="utf-8")

    tools = CurriculumTools(tmp_path)
    out = tools.list_courses()
    assert "01-intro" in out
    assert "入门" in out


def test_curriculum_read_returns_content(tmp_path: Path):
    (tmp_path / "curriculum").mkdir()
    (tmp_path / "curriculum" / "01-intro.md").write_text("# 入门\n正文", encoding="utf-8")

    tools = CurriculumTools(tmp_path)
    assert "正文" in tools.read_course("01-intro")
    assert "正文" in tools.read_course("01-intro.md")


def test_curriculum_read_rejects_path_traversal(tmp_path: Path):
    (tmp_path / "curriculum").mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("机密", encoding="utf-8")

    tools = CurriculumTools(tmp_path)
    out = tools.read_course("../secret")
    assert "机密" not in out


def test_curriculum_read_missing_file(tmp_path: Path):
    (tmp_path / "curriculum").mkdir()
    tools = CurriculumTools(tmp_path)
    assert "没有找到" in tools.read_course("nope")


# ---------------------------------------------------------------- 进度

def test_progress_read_empty(tmp_path: Path):
    tools = ProgressTools(tmp_path)
    assert "还没有" in tools.read_progress()


def test_progress_record_then_read(tmp_path: Path):
    tools = ProgressTools(tmp_path)
    tools.record_progress("学完了 Stream 的 filter 与 map")

    assert "filter 与 map" in tools.read_progress()


def test_progress_record_appends(tmp_path: Path):
    tools = ProgressTools(tmp_path)
    tools.record_progress("第一条")
    tools.record_progress("第二条")

    content = tools.read_progress()
    assert "第一条" in content
    assert "第二条" in content


def test_progress_record_rejects_empty(tmp_path: Path):
    tools = ProgressTools(tmp_path)
    assert "为空" in tools.record_progress("   ")


# ---------------------------------------------------------------- 架构

def write_java(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_arch_scan_reports_files(tmp_path: Path):
    write_java(tmp_path, "src/main/java/A.java", "package a; class A { void f() {} }")
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")

    out = tools.scan()
    assert "1 个源文件" in out


def test_arch_scan_missing_dir(tmp_path: Path):
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")
    out = tools.scan(str(tmp_path / "nope"))
    assert "不存在" in out


def test_arch_scan_empty_project(tmp_path: Path):
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")
    assert "没有找到 .java" in tools.scan()


def test_arch_findings_filters_by_severity(tmp_path: Path):
    big = "\n".join(f"// line {i}" for i in range(700))
    write_java(tmp_path, "src/main/java/Big.java", f"package a; public class Big {{\n{big}\n}}")
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")

    high = tools.findings("high")
    assert "god-class" in high or "没有" in high


def test_arch_findings_rejects_bad_severity(tmp_path: Path):
    write_java(tmp_path, "src/main/java/A.java", "package a; class A {}")
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")
    assert "high / medium / low" in tools.findings("critical")


def test_arch_file_profile(tmp_path: Path):
    write_java(tmp_path, "src/main/java/A.java", "package a; class A { void f() {} }")
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")

    out = tools.file_profile("src/main/java/A.java")
    assert "A.java" in out
    assert "行数" in out


def test_arch_file_profile_missing(tmp_path: Path):
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")
    assert "不存在" in tools.file_profile("nope.java")


def test_arch_read_source_has_line_numbers(tmp_path: Path):
    write_java(tmp_path, "src/main/java/A.java", "package a;\nclass A {\n  int x;\n}\n")
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")

    out = tools.read_source("src/main/java/A.java")
    assert "1  package a;" in out
    assert "4  }" in out


def test_arch_read_source_respects_window(tmp_path: Path):
    body = "\n".join(f"// {i}" for i in range(50))
    write_java(tmp_path, "src/main/java/A.java", f"class A {{\n{body}\n}}")
    tools = ArchitectureTools(tmp_path, tmp_path / "reports")

    out = tools.read_source("src/main/java/A.java", start_line=10, max_lines=5)
    assert "第 10-14 行" in out


# ---------------------------------------------------------------- settings

def test_settings_project_dir_defaults_to_cwd():
    s = Settings()
    assert s.project_dir == Path.cwd().resolve()


def test_settings_project_dir_from_explicit_path(tmp_path: Path):
    s = Settings()
    s.project_root = tmp_path
    assert s.project_dir == tmp_path.resolve()
