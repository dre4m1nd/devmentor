# -*- coding: utf-8 -*-
"""架构报告落盘的保留策略。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from devmentor.arch import analyze
from devmentor.arch.analyzer import MAX_REPORTS_PER_PROJECT


def _fake_datetime(second: int):
    """返回一个带有 now() 的假 datetime 模块替身。

    文件名精确到秒，所以每次给不同的 second 即可产生不同文件名，
    不需要真的 sleep。
    """
    import datetime as _dt

    class _Fake:
        @staticmethod
        def now():
            return _dt.datetime(2026, 1, 1, 0, 0, second)

    return _Fake


def _make_result():
    """构造一个最小可用的分析结果，避免依赖真实项目内容。"""

    return analyze(Path(__file__).resolve().parents[1])


def test_write_report_creates_file(tmp_path: Path):
    result = _make_result()
    path = result.write_report(tmp_path)

    assert path.is_file()
    assert path.name.startswith("arch-")
    assert path.read_text(encoding="utf-8")


def test_reports_are_pruned_to_limit(tmp_path: Path):
    """反复评审同一个项目不应让 reports/ 无限增长。

    用递增的假时间来生成不同文件名（文件名精确到秒），
    避免真的 sleep，测试才能秒级完成。
    """
    result = _make_result()
    total = MAX_REPORTS_PER_PROJECT + 3

    for i in range(total):
        with patch("devmentor.arch.analyzer.datetime", _fake_datetime(i)):
            result.write_report(tmp_path)

    files = sorted(tmp_path.glob("*.md"))
    assert len(files) == MAX_REPORTS_PER_PROJECT, (
        f"写入 {total} 次后应保留 {MAX_REPORTS_PER_PROJECT} 份，实际 {len(files)}"
    )


def test_prune_keeps_newest(tmp_path: Path):
    result = _make_result()
    total = MAX_REPORTS_PER_PROJECT + 2
    written = []

    for i in range(total):
        with patch("devmentor.arch.analyzer.datetime", _fake_datetime(i)):
            written.append(result.write_report(tmp_path).name)

    remaining = {p.name for p in tmp_path.glob("*.md")}
    # 最近 MAX 份应当都在，最早的两份应当被删
    assert set(written[-MAX_REPORTS_PER_PROJECT:]) == remaining
    for gone in written[:-MAX_REPORTS_PER_PROJECT]:
        assert gone not in remaining


def test_prune_does_not_touch_other_projects(tmp_path: Path):
    """清理只针对本项目前缀，不能删别的项目的报告。"""
    other = tmp_path / "arch-otherproject-20260101-000000.md"
    other.write_text("别的项目", encoding="utf-8")

    result = _make_result()
    for i in range(MAX_REPORTS_PER_PROJECT + 2):
        with patch("devmentor.arch.analyzer.datetime", _fake_datetime(i)):
            result.write_report(tmp_path)

    assert other.is_file(), "不应删除其它项目的报告"