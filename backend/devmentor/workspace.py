"""工作区：首次运行时把模板落盘。

规则是「不存在才写」：已经存在的文件一律不覆盖，这样用户对手写的人设、
课程、偏好做的修改不会被升级冲掉。
"""

from __future__ import annotations

import shutil
from pathlib import Path


class Workspace:
    def __init__(self, path: Path, templates: Path | None = None) -> None:
        self._path = path
        self._templates = templates or Path(__file__).parent / "templates"

    @property
    def path(self) -> Path:
        return self._path

    def ensure(self) -> list[str]:
        """创建目录并落盘缺失的模板文件，返回本次实际写入的相对路径。"""
        self._path.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        if not self._templates.is_dir():
            return written
        for src in self._templates.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(self._templates)
            dst = self._path / rel
            if dst.exists():
                continue  # 不覆盖用户修改
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            written.append(rel.as_posix())
        return written

    def read_agents_md(self) -> str:
        target = self._path / "AGENTS.md"
        try:
            return target.read_text(encoding="utf-8").strip() if target.is_file() else ""
        except OSError:
            return ""
