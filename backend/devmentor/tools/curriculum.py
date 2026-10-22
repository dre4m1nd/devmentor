"""课程工具：读取工作区里的课程内容。

对应 Java 版的 CurriculumTools。让「按大纲教学」有真实依据，而不是模型自由发挥。
"""

from __future__ import annotations

from pathlib import Path


class CurriculumTools:
    def __init__(self, workspace: Path) -> None:
        self._dir = workspace / "curriculum"

    def list_courses(self) -> str:
        """列出工作区里可用的课程。"""
        if not self._dir.is_dir():
            return "工作区里没有 curriculum 目录。"
        files = sorted(self._dir.glob("*.md"))
        if not files:
            return "课程目录是空的。"
        lines = [f"共 {len(files)} 篇课程："]
        for f in files:
            title = _first_heading(f) or f.stem
            lines.append(f"  {f.stem}  {title}")
        lines.append("\n用 curriculum_read 读取指定课程的正文。")
        return "\n".join(lines)

    def read_course(self, slug: str) -> str:
        """读取指定课程的完整内容。"""
        name = slug if slug.endswith(".md") else f"{slug}.md"
        target = (self._dir / name).resolve()
        # 防路径穿越：解析后必须仍在 curriculum 目录内
        if self._dir.resolve() not in target.parents:
            return f"非法的课程名：{slug}"
        if not target.is_file():
            return f"没有找到课程 {slug}。可用的课程用 curriculum_list 查看。"
        try:
            return target.read_text(encoding="utf-8")
        except OSError as e:
            return f"读取课程失败：{e}"


def _first_heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
    except OSError:
        return ""
    return ""
