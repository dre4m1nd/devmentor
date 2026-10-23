# -*- coding: utf-8 -*-
"""工具输出的可用性：规模、一致性、跨工具衔接。

工具返回的文本是给模型读的。除了"内容对不对"（前几轮验证过），
还要保证：
  - 规模可控，不会一次塞爆上下文
  - 同一事实在不同工具里说法一致，模型不会被矛盾信息误导
  - 报告里的路径能直接喂给其它工具，模型能按 AGENTS.md 的"取证→核实"闭环
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from devmentor.arch import analyze

# 一个足够真实、有缺陷的小项目
PROJECT = None


@pytest.fixture(scope="module")
def sample(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("outproj")
    src = root / "src/main/java/com/acme"

    # 上帝类：触发 god-class 与 long-method
    body = []
    for i in range(30):
        body.append(f"    public int m{i}(int x) {{")
        body += [f"        x = x + {j};" for j in range(18)]
        body += ["        return x;", "    }"]
    (src / "big").mkdir(parents=True)
    (src / "big" / "God.java").write_text(
        "package com.acme.big;\npublic class God {\n" + "\n".join(body) + "\n}\n",
        encoding="utf-8",
    )
    # 普通类
    (src / "user").mkdir(parents=True)
    (src / "user" / "User.java").write_text(
        "package com.acme.user;\npublic class User { }", encoding="utf-8"
    )
    return root


# ---------------------------------------------------------------- 规模

def test_scan_output_is_bounded(sample: Path):
    """概述报告不能过长——它会整段进模型上下文。"""
    text = analyze(sample).render()

    assert len(text) < 8000, f"报告 {len(text)} 字符，过长"
    assert len(text.splitlines()) < 100


def test_findings_one_line_per_defect(sample: Path):
    """arch_findings 每条缺陷必须一行，便于模型按行引用。"""
    result = analyze(sample)

    for f in result.findings:
        rendered = f.render()
        assert "\n" not in rendered, f"{f.rule} 的渲染结果含换行"
        # 四段要素齐全
        for key in ("证据", "建议"):
            assert key in rendered


def test_no_finding_repeats_severity_label_in_body(sample: Path):
    """层级标签只在开头出现一次，正文里不该重复。"""
    for f in analyze(sample).findings:
        rendered = f.render()
        assert rendered.startswith(f"[{f.severity.label}]")


# ---------------------------------------------------------------- 一致性

def test_scan_and_findings_agree_on_count(sample: Path):
    """arch_scan 报的"规则命中 N 条"必须等于 arch_findings 的行数。"""
    result = analyze(sample)
    text = result.render()

    m = re.search(r"规则命中：(\d+) 条", text)
    assert m, "报告里没有规则命中统计"
    assert int(m.group(1)) == len(result.findings)


def test_scan_and_findings_agree_per_rule(sample: Path):
    """同一规则在两个工具里的命中数必须相同。"""
    result = analyze(sample)
    from collections import Counter

    by_rule = Counter(f.rule for f in result.findings)
    text = result.render()

    for rule, count in by_rule.items():
        # 概述里每条命中都有 [级别][规则] 标记
        occurrences = len(re.findall(rf"\[\w+\]\[{re.escape(rule)}\]", text))
        assert occurrences == count, f"{rule} 在概述里出现 {occurrences} 次，应为 {count}"


def test_package_count_consistent(sample: Path):
    from devmentor.tools import ArchitectureTools

    text = ArchitectureTools(sample, sample / "reports").scan()
    m1 = re.search(r"包结构（(\d+) 个包）", text)
    m2 = re.search(r"包级依赖：(\d+) 条边", text)

    assert m1, "缺包结构统计"
    assert m2, "缺依赖统计"


# ---------------------------------------------------------------- 跨工具衔接

def test_paths_in_report_resolve_to_real_files(sample: Path):
    """报告里出现的路径都必须是项目内的真实文件。"""
    text = analyze(sample).render()
    paths = set(re.findall(r"(src/[\w/\-.]+\.java)", text))

    assert paths, "报告里没有任何源码路径"
    for p in paths:
        assert (sample / p).is_file(), f"报告提到了不存在的文件: {p}"


def test_report_paths_are_posix_style(sample: Path):
    """路径统一用 /，跨平台一致，也方便直接传给其它工具。"""
    text = analyze(sample).render()
    for p in re.findall(r"(src/[\w/\-.]+\.java)", text):
        assert "\\" not in p, f"路径含反斜杠: {p}"


def test_evidence_path_usable_by_file_profile(sample: Path):
    """从缺陷证据里抽出的路径，必须能直接喂给 arch_file_profile。

    这是 AGENTS.md 要求的评审闭环：拿缺陷 -> 核实文件。
    """
    from devmentor.tools import ArchitectureTools

    tools = ArchitectureTools(sample, sample / "reports")
    text = tools.findings()

    paths = re.findall(r"(src/[\w/\-.]+\.java)", text)
    assert paths, "缺陷里没有文件路径"

    for p in sorted(set(paths))[:3]:
        profile = tools.file_profile(p)
        assert "不存在" not in profile, f"{p} 无法被 file_profile 读取"


def test_evidence_path_usable_by_read_source(sample: Path):
    from devmentor.tools import ArchitectureTools

    tools = ArchitectureTools(sample, sample / "reports")
    text = tools.findings()
    paths = sorted(set(re.findall(r"(src/[\w/\-.]+\.java)", text)))

    for p in paths[:2]:
        src = tools.read_source(p, 1, 3)
        assert "不存在" not in src
        assert "行" in src


def test_file_profile_mentions_matching_rules(sample: Path):
    """file_profile 应列出该文件命中的规则，便于模型交叉核对。"""
    from devmentor.tools import ArchitectureTools

    tools = ArchitectureTools(sample, sample / "reports")
    profile = tools.file_profile("src/main/java/com/acme/big/God.java")

    assert "god-class" in profile or "long-method" in profile
