# -*- coding: utf-8 -*-
"""CI 配置的有效性。

项目有 396 个测试，但此前没有任何 CI——全靠手动跑。
这意味着"测试通过"没有自动保障，任何人 push 代码都不会被验证。

补上 GitHub Actions 后，这组测试锁住配置本身的有效性：
  - YAML 合法、job 齐全
  - 覆盖多个 Python 版本（跨版本问题曾是真实 bug）
  - CI 装 JDK（java_run_snippet 需要）
  - e2e 单独一步跑（失败时日志更好看）

e2e 在隔离 HOME 下的可重复性由 test_protocol_e2e.py 覆盖。
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _load() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 配置存在且合法

def test_ci_workflow_exists():
    assert CI.is_file(), "缺少 .github/workflows/ci.yml"


def test_ci_yaml_is_valid():
    d = _load()
    assert isinstance(d, dict)
    assert "jobs" in d


def test_ci_covers_backend_frontend_delivery():
    jobs = set(_load()["jobs"].keys())
    assert {"backend", "frontend", "delivery"} <= jobs, f"CI 缺少 job: {jobs}"


def test_ci_tests_multiple_python_versions():
    """跨 Python 版本曾是真实 bug（3.12 下 datetime.now() 微秒不前进，
    导致会话 id 全部相同）。CI 必须覆盖多个版本。"""
    versions = _load()["jobs"]["backend"]["strategy"]["matrix"]["python"]
    assert len(versions) >= 2, "至少测两个 Python 版本"
    assert "3.11" in versions, "应覆盖声明的最低版本"


def test_ci_installs_jdk_for_backend():
    """java_run_snippet 需要 JDK，CI 环境默认没有。"""
    text = CI.read_text(encoding="utf-8")
    assert "setup-java" in text, "CI 必须装 JDK"
    assert "17" in text


def test_ci_runs_e2e_separately():
    """e2e 起真实子进程，单独一步失败时日志更好看。"""
    cmds = [s.get("run", "") for s in _load()["jobs"]["backend"]["steps"]]
    assert any("not e2e" in c for c in cmds), "应有快测步骤"
    assert any("e2e" in c and "not e2e" not in c for c in cmds), "应有 e2e 步骤"


def test_ci_frontend_installs_deps():
    cmds = " ".join(s.get("run", "") for s in _load()["jobs"]["frontend"]["steps"])
    assert "npm" in cmds
