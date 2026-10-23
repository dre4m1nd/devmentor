"""Agent 工具：代码验证。

只有一类工具——把用户贴的代码真编译真运行，让导师的每句话都可验证。
"""

from .java_snippet import compile_check, run_snippet

__all__ = [
    "compile_check",
    "run_snippet",
]
