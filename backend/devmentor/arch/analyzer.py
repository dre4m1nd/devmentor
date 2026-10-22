"""架构评审入口：扫描 -> 聚合 -> 规则检查 -> 生成报告。

对应 Java 版的 ArchitectureAnalyzer。产出的报告是**纯文本事实**，
模型据此给出判断与优先级建议，而不是让它凭印象猜项目长什么样。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .model import ProjectSnapshot
from .rules import ArchFinding, Severity, check
from .scanner import DEFAULT_EXCLUDED, scan


@dataclass(slots=True)
class AnalysisResult:
    snapshot: ProjectSnapshot
    findings: list[ArchFinding]
    project_root: Path

    @property
    def is_empty(self) -> bool:
        return self.snapshot.file_count == 0

    def count_of(self, severity: Severity) -> int:
        return sum(1 for f in self.findings if f.severity is severity)

    def render(self) -> str:
        """渲染成给人看的报告（分两段：事实 + 规则命中）。"""
        snap = self.snapshot
        lines: list[str] = []
        lines.append(f"项目：{self.project_root}")
        lines.append(f"扫描：{snap.file_count} 个源文件（其中测试 {snap.test_file_count} 个）")
        if snap.root_package:
            lines.append(f"根包：{snap.root_package}")
        lines.append("")

        # ---- 包结构
        by_pkg = snap.by_package()
        lines.append(f"包结构（{len(by_pkg)} 个包）：")
        for pkg, files in sorted(by_pkg.items(), key=lambda kv: -len(kv[1]))[:15]:
            total = sum(f.line_count for f in files)
            lines.append(f"  {pkg or '(默认包)'}: {len(files)} 个类, {total} 行")
        if len(by_pkg) > 15:
            lines.append(f"  ... 其余 {len(by_pkg) - 15} 个包")
        lines.append("")

        # ---- 体量最大的文件
        biggest = sorted(snap.files, key=lambda f: -f.line_count)[:10]
        lines.append("体量最大的文件：")
        for f in biggest:
            lines.append(
                f"  {f.path}: {f.line_count} 行, {f.method_count} 个方法"
            )
        lines.append("")

        # ---- 包级依赖
        graph = snap.package_dependencies()
        edges = sum(len(v) for v in graph.values())
        lines.append(f"包级依赖：{edges} 条边")
        for pkg in sorted(graph):
            deps = sorted(graph[pkg])
            if deps:
                lines.append(f"  {pkg} -> {', '.join(deps)}")
        lines.append("")

        # ---- 规则命中
        if not self.findings:
            lines.append("规则命中：无")
        else:
            high = self.count_of(Severity.HIGH)
            medium = self.count_of(Severity.MEDIUM)
            low = self.count_of(Severity.LOW)
            lines.append(
                f"规则命中：{len(self.findings)} 条（高 {high} / 中 {medium} / 低 {low}）"
            )
            lines.append("")
            for i, f in enumerate(self.findings, 1):
                lines.append(f"{i}. [{f.severity.label}][{f.rule}] {f.title}")
                lines.append(f"   证据：{f.evidence}")
                lines.append(f"   建议：{f.suggestion}")
                if f.files:
                    lines.append(f"   文件：{', '.join(f.files)}")
        return "\n".join(lines)

    def write_report(self, report_dir: Path) -> Path:
        """把报告落盘，返回文件路径。"""
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = self.project_root.name or "project"
        target = report_dir / f"arch-{name}-{stamp}.md"
        target.write_text(self.render(), encoding="utf-8")
        return target


def analyze(
    project_root: Path,
    excluded: frozenset[str] = DEFAULT_EXCLUDED,
    max_files: int = 5000,
) -> AnalysisResult:
    """扫描并检查。"""
    root = Path(project_root).resolve()
    snapshot = scan(root, excluded=excluded, max_files=max_files)
    findings = check(snapshot)
    return AnalysisResult(snapshot=snapshot, findings=findings, project_root=root)
