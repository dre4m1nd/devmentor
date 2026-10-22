"""用 tree-sitter 解析 Java 源码，产出结构化事实。

对应 Java 版的 JavaSourceScanner。关键取舍与 Java 版一致：

    刻意不做语义分析（不解析类型、不建符号表）：架构评审只需要结构信息，
    而完整编译要求依赖齐全、构建可跑。语法树解析对任何能编译的源码都成立，
    且不需要 classpath。

Java 版用 JDK 自带的 javac 语法树；Python 没有 javac，改用 tree-sitter-java——
它同样是纯语法解析，同样不需要 classpath，因此这个取舍得以保留。
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_java as tsj
from tree_sitter import Language, Node, Parser

from .model import ProjectSnapshot, SourceFileInfo

# 默认跳过的目录：构建产物、IDE、依赖缓存
DEFAULT_EXCLUDED = frozenset(
    {
        ".git",
        ".idea",
        ".vscode",
        ".settings",
        "target",
        "build",
        "out",
        "node_modules",
        "bin",
        ".gradle",
        ".mvn",
    }
)

_LANGUAGE = Language(tsj.language())

# 可能声明方法/类型的关键字，用于识别"顶层类型"
TYPE_DECLARATIONS = frozenset(
    {
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "record_declaration",
        "annotation_type_declaration",
    }
)

METHOD_DECLARATIONS = frozenset({"method_declaration", "constructor_declaration"})


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _walk(node: Node):
    """深度优先遍历语法树。"""
    yield node
    for child in node.children:
        yield from _walk(child)


def _find_package(root: Node, src: bytes) -> str:
    for child in root.children:
        if child.type == "package_declaration":
            # 取里面的 scoped_identifier
            for sub in _walk(child):
                if sub.type in ("scoped_identifier", "identifier"):
                    return _text(sub, src)
    return ""


def _find_imports(root: Node, src: bytes) -> list[str]:
    imports: list[str] = []
    for child in root.children:
        if child.type != "import_declaration":
            continue
        for sub in _walk(child):
            if sub.type in ("scoped_identifier", "identifier"):
                imports.append(_text(sub, src))
                break
    return imports


def _find_type_name(root: Node, src: bytes) -> str:
    """取第一个顶层类型名；匿名/局部类不算。"""
    for child in root.children:
        if child.type in TYPE_DECLARATIONS:
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                return _text(name_node, src)
    return ""


def _count_methods(root: Node) -> tuple[int, int]:
    """返回 (方法数, 最长方法行数)。"""
    count = 0
    longest = 0
    for node in _walk(root):
        if node.type in METHOD_DECLARATIONS:
            count += 1
            # tree-sitter 的 start_point/end_point 都是 0-based (row, col)
            lines = node.end_point[0] - node.start_point[0] + 1
            longest = max(longest, lines)
    return count, longest


def _count_comment_lines(root: Node) -> int:
    """统计注释覆盖的行数（block_comment + line_comment）。"""
    covered: set[int] = set()
    for node in _walk(root):
        if node.type in ("line_comment", "block_comment"):
            start, end = node.start_point[0], node.end_point[0]
            covered.update(range(start, end + 1))
    return len(covered)


def scan_file(path: Path, root: Path) -> SourceFileInfo | None:
    """解析单个文件；解析失败返回 None（坏一个文件不该让整次扫描失败）。"""
    try:
        src = path.read_bytes()
    except OSError:
        return None

    parser = Parser(_LANGUAGE)
    try:
        tree = parser.parse(src)
    except Exception:
        return None

    node = tree.root_node
    method_count, max_method_lines = _count_methods(node)

    return SourceFileInfo(
        path=path.relative_to(root).as_posix(),
        package=_find_package(node, src),
        type_name=_find_type_name(node, src) or path.stem,
        line_count=src.count(b"\n") + (0 if src.endswith(b"\n") else 1),
        method_count=method_count,
        max_method_lines=max_method_lines,
        comment_lines=_count_comment_lines(node),
        imports=_find_imports(node, src),
    )


def scan(
    project_root: Path,
    excluded: frozenset[str] = DEFAULT_EXCLUDED,
    max_files: int = 5000,
) -> ProjectSnapshot:
    """扫描项目下所有 .java 文件。"""
    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise NotADirectoryError(str(project_root))

    java_files: list[Path] = []
    for path in sorted(project_root.rglob("*.java")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(project_root).parts
        if any(part in excluded for part in rel_parts):
            continue
        java_files.append(path)
        if len(java_files) >= max_files:
            break

    infos: list[SourceFileInfo] = []
    for path in java_files:
        info = scan_file(path, project_root)
        if info is not None:
            infos.append(info)

    return ProjectSnapshot(files=infos)
