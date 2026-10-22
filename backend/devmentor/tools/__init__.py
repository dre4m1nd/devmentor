"""Agent 工具：教学验证、课程、进度、架构评审四类。"""

from .architecture import ArchitectureTools
from .curriculum import CurriculumTools
from .java_snippet import compile_check, run_snippet
from .progress import ProgressTools

__all__ = [
    "ArchitectureTools",
    "CurriculumTools",
    "ProgressTools",
    "compile_check",
    "run_snippet",
]
