"""架构评审引擎：语法树扫描 -> 结构化事实 -> 确定性规则。"""

from .analyzer import AnalysisResult, analyze
from .model import ProjectSnapshot, SourceFileInfo
from .rules import ArchFinding, Severity, check, find_cycles
from .scanner import DEFAULT_EXCLUDED, scan

__all__ = [
    "AnalysisResult",
    "analyze",
    "ArchFinding",
    "check",
    "DEFAULT_EXCLUDED",
    "find_cycles",
    "ProjectSnapshot",
    "scan",
    "Severity",
    "SourceFileInfo",
]
