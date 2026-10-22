"""学习进度工具：追加写入工作区的 progress.md，让导师跨会话记得你学到哪了。

对应 Java 版的 ProgressTools。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class ProgressTools:
    def __init__(self, workspace: Path) -> None:
        self._file = workspace / "progress.md"

    def read_progress(self) -> str:
        """读取学习进度记录。"""
        if not self._file.is_file():
            return "还没有任何学习进度记录。"
        try:
            text = self._file.read_text(encoding="utf-8").strip()
        except OSError as e:
            return f"读取进度失败：{e}"
        return text or "还没有任何学习进度记录。"

    def record_progress(self, note: str) -> str:
        """记录一条学习进度。"""
        note = (note or "").strip()
        if not note:
            return "进度内容为空，没有记录。"
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            with self._file.open("a", encoding="utf-8") as fh:
                if self._file.stat().st_size == 0:
                    fh.write("# 学习进度\n\n")
                fh.write(f"- {stamp}  {note}\n")
        except OSError as e:
            return f"写入进度失败：{e}"
        return f"已记录：{note}"
