"""项目快照：一次扫描的结构化事实。

这是"架构事实"，不含任何判断；判断在 rules.py 里。

对应 Java 版的 ProjectSnapshot / SourceFileInfo。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


@dataclass(slots=True)
class SourceFileInfo:
    """单个 Java 源文件的结构事实。"""

    path: str            # 相对项目根，POSIX 分隔
    package: str
    type_name: str
    line_count: int
    method_count: int
    max_method_lines: int
    comment_lines: int
    imports: list[str] = field(default_factory=list)

    @property
    def is_test(self) -> bool:
        p = self.path.lower()
        return (
            "/src/test/" in p
            or p.startswith("src/test/")
            or PurePosixPath(p).stem.endswith("Test")
            or PurePosixPath(p).stem.endswith("Tests")
        )

    @property
    def avg_method_lines(self) -> int:
        return self.line_count // max(1, self.method_count)


@dataclass(slots=True)
class ProjectSnapshot:
    """整个项目的聚合视图：包结构、依赖图、体量分布。"""

    files: list[SourceFileInfo]
    root_package: str = ""

    def __post_init__(self) -> None:
        if not self.root_package:
            self.root_package = self._infer_root_package()

    def _infer_root_package(self) -> str:
        """取所有包名的公共前缀。

        例如 com.acme.shop.order 与 com.acme.shop.user -> com.acme.shop
        """
        packages = [f.package for f in self.files if f.package]
        if not packages:
            return ""
        parts = packages[0].split(".")
        common = len(parts)
        for pkg in packages[1:]:
            other = pkg.split(".")
            i = 0
            while i < common and i < len(other) and parts[i] == other[i]:
                i += 1
            common = i
        return ".".join(parts[:common]) if common else ""

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def test_file_count(self) -> int:
        return sum(1 for f in self.files if f.is_test)

    def by_package(self) -> dict[str, list[SourceFileInfo]]:
        result: dict[str, list[SourceFileInfo]] = {}
        for f in self.files:
            result.setdefault(f.package, []).append(f)
        return result

    def package_dependencies(self) -> dict[str, set[str]]:
        """包级依赖图：包 -> 它依赖的其它包（基于 import 的真实依赖）。

        只统计项目内部的包（以 root_package 开头的），第三方库不算。
        """
        graph: dict[str, set[str]] = {pkg: set() for pkg in self.by_package()}
        for f in self.files:
            if not f.package:
                continue
            for dep in f.imports:
                if not self.root_package or not dep.startswith(self.root_package):
                    continue
                # import com.acme.shop.user.UserService -> 包 com.acme.shop.user
                dep_pkg = dep.rsplit(".", 1)[0] if "." in dep else dep
                if dep_pkg != f.package and dep_pkg in graph:
                    graph[f.package].add(dep_pkg)
        return graph
