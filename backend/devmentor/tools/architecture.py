"""架构评审工具：让智能体独立读取用户项目并给出**有证据**的缺陷判断。

工具本身不做"评价"，只做确定性分析；评价交给模型，模型拿到的是一份可核对的
事实清单，因此不会产出"建议使用设计模式"这种空话。

对应 Java 版的 ArchitectureTools。
"""

from __future__ import annotations

from pathlib import Path

from ..arch import Severity, analyze


class ArchitectureTools:
    def __init__(self, default_project_root: Path, report_dir: Path) -> None:
        self._root = default_project_root
        self._reports = report_dir

    def _resolve(self, path: str | None) -> Path:
        return Path(path).resolve() if path else self._root

    def scan(self, path: str | None = None) -> str:
        """全项目静态分析：包结构 + 依赖图 + 规则命中。"""
        root = self._resolve(path)
        if not root.is_dir():
            return f"目录不存在：{root}"
        try:
            result = analyze(root)
        except Exception as e:
            return f"静态分析失败：{e}"
        if result.is_empty:
            return f"在 {root} 下没有找到 .java 文件。"
        report = result.render()
        try:
            saved = result.write_report(self._reports)
            report += f"\n\n报告已保存：{saved}"
        except OSError:
            pass
        return report

    def findings(self, severity: str | None = None, path: str | None = None) -> str:
        """只看规则命中的缺陷，可按严重程度过滤（high/medium/low）。"""
        root = self._resolve(path)
        if not root.is_dir():
            return f"目录不存在：{root}"
        try:
            result = analyze(root)
        except Exception as e:
            return f"静态分析失败：{e}"

        items = result.findings
        if severity:
            want = severity.strip().lower()
            if want not in ("high", "medium", "low"):
                return "severity 只能是 high / medium / low。"
            items = [f for f in items if f.severity is Severity(want)]

        if not items:
            return "没有命中的规则。" if not severity else f"没有 {severity} 级别的命中。"
        return "\n".join(f.render() for f in items)

    def dependencies(self, path: str | None = None) -> str:
        """只看包级依赖图与循环。"""
        root = self._resolve(path)
        if not root.is_dir():
            return f"目录不存在：{root}"
        try:
            result = analyze(root)
        except Exception as e:
            return f"静态分析失败：{e}"

        graph = result.snapshot.package_dependencies()
        lines = [f"包级依赖图（{len(graph)} 个包）："]
        for pkg in sorted(graph):
            deps = sorted(graph[pkg])
            lines.append(f"  {pkg} -> {', '.join(deps) if deps else '(无项目内依赖)'}")
        cycles = [f for f in result.findings if f.rule == "package-cycle"]
        if cycles:
            lines.append("\n循环依赖：")
            lines.extend(f"  {c.evidence}" for c in cycles)
        else:
            lines.append("\n没有发现循环依赖。")
        return "\n".join(lines)

    def file_profile(self, path: str) -> str:
        """单文件画像：体量、方法数、命中的规则。"""
        root = self._root
        target = Path(path)
        if not target.is_absolute():
            target = root / path
        target = target.resolve()
        if not target.is_file():
            return f"文件不存在：{target}"
        # 架构分析引擎只解析 Java。对其它语言直接说明，不要给出
        # "可能被排除目录规则跳过"这种误导性提示。
        if target.suffix.lower() != ".java":
            return (
                f"{target.name} 不是 Java 文件。架构分析引擎目前只解析 .java 源码，"
                "无法为其它语言生成文件画像。"
            )
        try:
            result = analyze(root)
            rel = target.relative_to(root).as_posix()
        except ValueError:
            return f"{target} 不在项目根 {root} 之下。"
        except Exception as e:
            return f"静态分析失败：{e}"

        info = next((f for f in result.snapshot.files if f.path == rel), None)
        if info is None:
            return f"没有在扫描结果里找到 {rel}（可能被排除目录规则跳过）。"

        lines = [
            f"文件：{info.path}",
            f"包：{info.package or '(默认包)'}",
            f"类型：{info.type_name}",
            f"行数：{info.line_count}",
            f"方法数：{info.method_count}",
            f"最长方法：{info.max_method_lines} 行",
            f"注释行：{info.comment_lines}",
            f"是否测试文件：{'是' if info.is_test else '否'}",
        ]
        hits = [f for f in result.findings if info.path in f.files]
        if hits:
            lines.append("\n命中的规则：")
            lines.extend(f"  {h.render()}" for h in hits)
        else:
            lines.append("\n没有命中规则。")
        return "\n".join(lines)

    def read_source(self, path: str, start_line: int = 1, max_lines: int = 200) -> str:
        """带行号读取源码，用于引用具体代码。"""
        target = Path(path)
        if not target.is_absolute():
            target = self._root / path
        target = target.resolve()
        if not target.is_file():
            return f"文件不存在：{target}"
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            return f"读取失败：{e}"

        total = len(lines)
        # 行号参数要夹到合法区间。之前只夹了 start，max_lines 为 0 或负数
        # 时 end < start，会输出"第 5-4 行"甚至"第 5--1 行"这种无意义范围。
        start = max(1, start_line)
        count = max(1, max_lines)
        if start > total:
            return (
                f"{target.name} 共 {total} 行，起始行 {start_line} 已超过文件末尾。"
                f"请把 start_line 改到 1 到 {total} 之间。"
            )
        end = min(total, start + count - 1)

        out = [f"{target.name}（第 {start}-{end} 行，共 {total} 行）"]
        for no in range(start, end + 1):
            out.append(f"{no:>5}  {lines[no - 1]}")
        return "\n".join(out)