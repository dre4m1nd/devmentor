"""教学工具：真正编译并运行 Java 片段的工具。

对应 Java 版的 JavaSnippetTools。工具实例无状态：
每次调用都新建临时目录，用完即删，因此可被并发共享。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..config import java_executable

# 匹配 public class/record/interface/enum Name
_PUBLIC_TYPE = re.compile(
    r"\bpublic\s+(?:final\s+|abstract\s+|sealed\s+|non-sealed\s+)*"
    r"(?:class|record|interface|enum)\s+(\w+)"
)
# 匹配任意顶层类型声明（不含 public 时也能定名）
_ANY_TYPE = re.compile(
    r"^\s*(?:final\s+|abstract\s+|sealed\s+|non-sealed\s+)*"
    r"(?:class|record|interface|enum)\s+(\w+)",
    re.MULTILINE,
)


def _source_file_name(source: str) -> str:
    """javac 要求 public class Foo 必须存在 Foo.java 里，否则直接拒绝。"""
    if m := _PUBLIC_TYPE.search(source):
        return m.group(1) + ".java"
    if m := _ANY_TYPE.search(source):
        return m.group(1) + ".java"
    return "Snippet.java"


# 匹配字段声明：修饰符/类型 + 名字 + (可选的 = 初值) + ;
_FIELD_DECL = re.compile(
    r"^\s*(?:(?:private|public|protected|static|final|volatile|transient)\s+)+"
    r"[\w.$<>\[\],\s?]+\s+\w+\s*(?:=[^;]*)?;\s*$"
)
# 匹配方法声明（含方法体）：修饰符 + 返回类型 + 名字 + 参数 + {
_METHOD_DECL = re.compile(
    r"^\s*(?:(?:private|public|protected|static|final|synchronized|abstract)\s+)*"
    r"(?:[\w.$<>\[\],\s?]+)\s+\w+\s*\([^)]*\)\s*\{",
    re.MULTILINE,
)


def _single_decl_kind(source: str) -> str | None:
    """判断片段是不是单个"类成员声明"（字段 / 方法）。

    用户经常贴一个字段或一段方法问"这样写对吗"。这类片段不是语句，
    直接塞进 main 会报"非法的表达式开始"——错误信息对用户毫无帮助。
    识别出来后就该包进类体，而不是方法体。
    """
    stripped = source.strip()
    if not stripped:
        return None
    # 方法：有方法体且不是完整类型声明
    if _METHOD_DECL.search(stripped) and not _ANY_TYPE.search(stripped):
        # 整段只有一个方法（不含其它语句）时按成员处理
        return "method"
    lines = [l for l in stripped.splitlines() if l.strip()]
    if lines and all(_FIELD_DECL.match(l) for l in lines):
        return "field"
    return None


def _normalize(source: str) -> str:
    """让片段可以直接跑：没有类声明时包一层。"""
    if _ANY_TYPE.search(source) or _PUBLIC_TYPE.search(source):
        return source

    kind = _single_decl_kind(source)
    if kind == "field":
        # 字段声明放进类体，再补一个 main 打印/占位，否则无法运行
        body = "\n".join("    " + line for line in source.strip().splitlines())
        return (
            "public class Snippet {\n"
            f"{body}\n"
            "    public static void main(String[] args) {\n"
            '        System.out.println("（片段已编译通过；它为字段声明，无可运行语句）");\n'
            "    }\n"
            "}\n"
        )
    if kind == "method":
        body = "\n".join("    " + line for line in source.strip().splitlines())
        return (
            "public class Snippet {\n"
            f"{body}\n"
            "    public static void main(String[] args) {\n"
            '        System.out.println("（片段已编译通过；它为方法声明，未调用）");\n'
            "    }\n"
            "}\n"
        )

    # 普通语句：包成 main
    body = "\n".join("        " + line for line in source.splitlines())
    return (
        "public class Snippet {\n"
        "    public static void main(String[] args) {\n"
        f"{body}\n"
        "    }\n"
        "}\n"
    )


def compile_check(source: str, timeout_seconds: int = 20, max_source_chars: int = 20000) -> str:
    """用 JDK 编译器检查片段，返回 行:列 诊断。"""
    if len(source) > max_source_chars:
        return f"源码过大（{len(source)} 字符，上限 {max_source_chars}），请缩小范围后重试。"
    javac = java_executable(need_compiler=True)
    if javac is None:
        return "找不到 JDK（需要 java+javac，不是 JRE）。请安装 JDK 17+ 或设置 DEVMENTOR_JAVA_HOME。"

    normalized = _normalize(source)
    with tempfile.TemporaryDirectory(prefix="devmentor-compile-") as tmp:
        path = Path(tmp) / _source_file_name(normalized)
        path.write_text(normalized, encoding="utf-8")
        proc = subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", tmp, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if proc.returncode == 0:
            return "编译通过，没有诊断信息。"
        return (proc.stderr or proc.stdout or "编译失败，但没有输出诊断。").strip()


def run_snippet(
    source: str,
    timeout_seconds: int = 10,
    max_source_chars: int = 20000,
) -> str:
    """真正编译并运行，返回退出码、stdout、stderr，超时强杀。"""
    if len(source) > max_source_chars:
        return f"源码过大（{len(source)} 字符，上限 {max_source_chars}），请缩小范围后重试。"
    java = java_executable()
    javac = java_executable(need_compiler=True)
    if java is None or javac is None:
        return "找不到 JDK（需要 java+javac，不是 JRE）。请安装 JDK 17+ 或设置 DEVMENTOR_JAVA_HOME。"

    normalized = _normalize(source)
    with tempfile.TemporaryDirectory(prefix="devmentor-run-") as tmp:
        src_path = Path(tmp) / _source_file_name(normalized)
        src_path.write_text(normalized, encoding="utf-8")
        build = subprocess.run(
            [javac, "-encoding", "UTF-8", "-d", tmp, str(src_path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds * 2,
        )
        if build.returncode != 0:
            diag = (build.stderr or build.stdout).strip()
            return f"编译失败（退出码 {build.returncode}）：\n{diag}"

        main_class = src_path.stem
        try:
            run = subprocess.run(
                [java, "-cp", tmp, main_class],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return f"运行超时（{timeout_seconds} 秒），已强制终止。"

        # 编译过了但没有 main：这是"类型声明片段"的常态（贴一个 record /
        # interface 问写法对不对）。直接把 JDK 那句"找不到 main 方法"
        # 抛给用户没有意义——他本来就没想运行它。
        combined = (run.stderr or "") + (run.stdout or "")
        if run.returncode != 0 and "找不到 main 方法" in combined:
            return (
                "编译通过（没有诊断信息）。\n"
                f"这段是类型声明（{main_class}），没有 main 方法，因此不执行。\n"
                "想运行它，请补一个 main 并用 java_run_snippet 提交完整代码。"
            )

        parts = [f"退出码：{run.returncode}"]
        if run.stdout:
            parts.append(f"stdout：\n{run.stdout.rstrip()}")
        if run.stderr:
            parts.append(f"stderr：\n{run.stderr.rstrip()}")
        if not run.stdout and not run.stderr:
            parts.append("（没有输出）")
        return "\n".join(parts)