"""确定性的架构规则检查。

设计原则（与 Java 版一致）：**只报能给出具体证据的问题**。
宁可少报，也不要产出"建议使用设计模式"这类无法验证的空话——
那种输出对用户毫无价值，也正是纯 LLM 评审的通病。

每条规则都能用数字或文件路径证明，用户可以自己去核对。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .model import ProjectSnapshot, SourceFileInfo


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def label(self) -> str:
        return {"high": "高", "medium": "中", "low": "低"}[self.value]

    @property
    def rank(self) -> int:
        return {"high": 0, "medium": 1, "low": 2}[self.value]


@dataclass(slots=True)
class ArchFinding:
    """一条架构发现。由确定性规则产出（不是模型自由发挥），带证据与修改建议。"""

    rule: str
    severity: Severity
    title: str
    evidence: str
    suggestion: str
    files: list[str] = field(default_factory=list)

    def render(self) -> str:
        """渲染成给模型看的一行（紧凑，避免 token 爆炸）。"""
        parts = [f"[{self.severity.label}][{self.rule}] {self.title}"]
        parts.append(f"证据: {self.evidence}")
        parts.append(f"建议: {self.suggestion}")
        if self.files:
            parts.append("文件: " + ", ".join(self.files))
        return " | ".join(parts)


# ---------------------------------------------------------------- 阈值

GOD_CLASS_LINES = 600        # 超过视为"上帝类"候选
LONG_METHOD_LINES = 80       # 单方法超过视为过长
TOO_MANY_METHODS = 25        # 单文件方法数超过视为职责过多
MIN_AVG_METHOD_LINES = 8     # 平均每方法少于此行数视为纯 POJO，不报"职责过多"
FLAT_PACKAGE_FILES = 20      # 包内文件数超过视为缺少分层


# ---------------------------------------------------------------- 规则

def _check_god_classes(snap: ProjectSnapshot) -> list[ArchFinding]:
    out: list[ArchFinding] = []
    for f in snap.files:
        if f.line_count > GOD_CLASS_LINES and not f.is_test:
            out.append(
                ArchFinding(
                    rule="god-class",
                    severity=Severity.HIGH,
                    title=f"类体量过大，职责很可能不单一：{f.type_name}",
                    evidence=f"{f.path} 共 {f.line_count} 行、{f.method_count} 个方法",
                    suggestion=(
                        "按变化原因拆分：把数据访问、业务规则、外部调用分成不同类；"
                        "先抽出最独立的那一块，保持每步可编译。"
                    ),
                    files=[f.path],
                )
            )
    return out


def _check_long_methods(snap: ProjectSnapshot) -> list[ArchFinding]:
    out: list[ArchFinding] = []
    for f in snap.files:
        if f.max_method_lines > LONG_METHOD_LINES and not f.is_test:
            out.append(
                ArchFinding(
                    rule="long-method",
                    severity=Severity.MEDIUM,
                    title=f"存在超长方法：{f.type_name}",
                    evidence=f"{f.path} 最长方法约 {f.max_method_lines} 行",
                    suggestion=(
                        "超过 80 行的方法通常混了多个抽象层次；"
                        "按「读取→校验→计算→写回」切段，每段提炼成有名字的方法。"
                    ),
                    files=[f.path],
                )
            )
    return out


def _check_too_many_methods(snap: ProjectSnapshot) -> list[ArchFinding]:
    out: list[ArchFinding] = []
    for f in snap.files:
        if f.method_count <= TOO_MANY_METHODS or f.is_test:
            continue
        # 过滤器：平均行长很短说明这是一堆 getter/setter（纯 POJO），不是「多个角色」。
        # 不滤掉的话，每个配置/实体类都会命中，报告里 17% 是噪音。
        if f.avg_method_lines < MIN_AVG_METHOD_LINES:
            continue
        out.append(
            ArchFinding(
                rule="many-methods",
                severity=Severity.MEDIUM,
                title=f"方法数量过多，可能承担了多个角色：{f.type_name}",
                evidence=(
                    f"{f.path} 共 {f.method_count} 个方法，"
                    f"平均每方法约 {f.avg_method_lines} 行"
                ),
                suggestion=(
                    "看看方法名里是否反复出现不同领域的名词（如 order* 与 user*），"
                    "若出现，按领域拆类。"
                ),
                files=[f.path],
            )
        )
    return out


def _is_leaf_package(by_pkg: dict[str, list[SourceFileInfo]], pkg: str) -> bool:
    if not pkg:
        return False
    prefix = pkg + "."
    return not any(other != pkg and other.startswith(prefix) for other in by_pkg)


def _check_flat_packages(snap: ProjectSnapshot) -> list[ArchFinding]:
    out: list[ArchFinding] = []
    by_pkg = snap.by_package()
    for pkg, files in by_pkg.items():
        if len(files) >= FLAT_PACKAGE_FILES and _is_leaf_package(by_pkg, pkg):
            shown = pkg if pkg else "(默认包)"
            out.append(
                ArchFinding(
                    rule="flat-package",
                    severity=Severity.MEDIUM,
                    title=f"包内平铺过多类，缺少子领域划分：{shown}",
                    evidence=f"该包下直接有 {len(files)} 个类，且没有子包",
                    suggestion=(
                        "按职责拆子包（如 domain / application / infrastructure，"
                        "或按业务子域拆分），避免一个包同时容纳实体、服务和适配器。"
                    ),
                    files=[f.path for f in files[:8]],
                )
            )
    return out


def find_cycles(graph: dict[str, set[str]], max_length: int = 12) -> list[list[str]]:
    """用 DFS 找出长度不超过 max_length 的环。

    去重：只保留"起点是最小节点"的那个表示，否则 A→B→C→A 会报三次。
    """
    found: list[list[str]] = []
    seen: set[str] = set()

    def dfs(start: str, current: str, path: list[str], on_path: set[str]) -> None:
        if len(path) > max_length:
            return
        on_path.add(current)
        for nxt in sorted(graph.get(current, ())):
            if nxt == start and len(path) > 1:
                if min(path) == start:
                    cycle = path + [start]
                    key = ">".join(cycle)
                    if key not in seen:
                        seen.add(key)
                        found.append(cycle)
            elif nxt not in on_path and nxt >= start:
                path.append(nxt)
                dfs(start, nxt, path, on_path)
                path.pop()
        on_path.discard(current)

    for start in sorted(graph):
        dfs(start, start, [start], set())
    return found


def _check_cycles(snap: ProjectSnapshot) -> list[ArchFinding]:
    out: list[ArchFinding] = []
    graph = snap.package_dependencies()
    for cycle in find_cycles(graph):
        out.append(
            ArchFinding(
                rule="package-cycle",
                severity=Severity.HIGH,
                title="包之间存在循环依赖",
                evidence=" → ".join(cycle),
                suggestion=(
                    "循环依赖让两个包无法独立理解、独立测试。"
                    "常见解法：把双方共同依赖的部分抽成第三个包；"
                    "或把其中一侧的调用改为事件/接口回调。"
                ),
            )
        )
    return out


def _layer_of(pkg: str) -> str | None:
    low = pkg.lower()
    if any(low.endswith(s) for s in (".controller", ".web", ".api")):
        return "controller"
    if any(low.endswith(s) for s in (".service", ".application")):
        return "service"
    if any(low.endswith(s) for s in (".repository", ".dao", ".mapper", ".infrastructure")):
        return "repository"
    return None


def _layer_rank(layer: str) -> int:
    return {"controller": 3, "service": 2}.get(layer, 1)


def _check_layer_violations(snap: ProjectSnapshot) -> list[ArchFinding]:
    out: list[ArchFinding] = []
    graph = snap.package_dependencies()
    for from_pkg, deps in graph.items():
        from_layer = _layer_of(from_pkg)
        if from_layer is None:
            continue
        for to_pkg in deps:
            to_layer = _layer_of(to_pkg)
            if to_layer is None or to_layer == from_layer:
                continue
            # 反向依赖才算违规：下层（repository，rank 1）依赖上层（service，rank 2）
            # 是分层倒置；上层依赖下层是正常方向。
            if _layer_rank(to_layer) > _layer_rank(from_layer):
                out.append(
                    ArchFinding(
                        rule="layer-violation",
                        severity=Severity.HIGH,
                        title="分层方向被违反",
                        evidence=f"{from_pkg} -> {to_pkg}（{from_layer} 依赖 {to_layer}）",
                        suggestion=(
                            "下层不应知道上层：把 repository 需要的逻辑下沉到 service，"
                            "或者由上层把已经算好的数据作为参数传给 repository。"
                        ),
                    )
                )
    return out


def _check_no_tests(snap: ProjectSnapshot) -> list[ArchFinding]:
    if snap.file_count >= 10 and snap.test_file_count == 0:
        return [
            ArchFinding(
                rule="no-tests",
                severity=Severity.HIGH,
                title="项目里没有任何测试类",
                evidence=f"扫描到 {snap.file_count} 个源文件，测试文件 0 个",
                suggestion=(
                    "先给最核心的一两个纯函数补测试，能跑起来再谈覆盖率；"
                    "没有测试的架构改动风险不可控。"
                ),
            )
        ]
    return []


def _check_no_comments(snap: ProjectSnapshot) -> list[ArchFinding]:
    undocumented = [
        f
        for f in snap.files
        if not f.is_test and f.line_count > 100 and f.comment_lines == 0
    ]
    if len(undocumented) >= 3:
        return [
            ArchFinding(
                rule="no-comments",
                severity=Severity.LOW,
                title="多个较大的类没有任何注释",
                evidence=f"{len(undocumented)} 个超过 100 行的类注释行数为 0",
                suggestion=(
                    "不需要逐行注释；至少在每个公开类的顶部写清「它负责什么、不负责什么」，"
                    "这比方法内注释更有价值。"
                ),
                files=[f.path for f in undocumented[:5]],
            )
        ]
    return []


def _check_mixed_roots(snap: ProjectSnapshot) -> list[ArchFinding]:
    roots: set[str] = set()
    for f in snap.files:
        pkg = f.package.strip()
        roots.add(pkg.split(".")[0] if pkg else "(默认包)")
    if len(roots) > 1:
        return [
            ArchFinding(
                rule="mixed-roots",
                severity=Severity.LOW,
                title="存在多个顶层包根，命名空间不统一",
                evidence=", ".join(sorted(roots)),
                suggestion=(
                    "统一到一个反向域名根（如 com.yourcompany.project）下，"
                    "否则 IDE 的包视图和依赖分析都会变乱。"
                ),
            )
        ]
    return []


def check(snap: ProjectSnapshot) -> list[ArchFinding]:
    """跑全部规则，按严重程度排序返回。"""
    findings: list[ArchFinding] = []
    findings += _check_god_classes(snap)
    findings += _check_long_methods(snap)
    findings += _check_too_many_methods(snap)
    findings += _check_flat_packages(snap)
    findings += _check_cycles(snap)
    findings += _check_layer_violations(snap)
    findings += _check_no_tests(snap)
    findings += _check_no_comments(snap)
    findings += _check_mixed_roots(snap)
    findings.sort(key=lambda f: (f.severity.rank, f.rule))
    return findings
