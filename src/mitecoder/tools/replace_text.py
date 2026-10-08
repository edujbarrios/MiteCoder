"""Small-model-friendly, exact text replacement tool."""

from __future__ import annotations

import re
from typing import Any

from mitecoder.repository.workspace import Workspace
from mitecoder.tools.base import Tool, ToolResult


class ReplaceTextTool(Tool):
    name = "replace_text"
    description = "Replace one exact, unique text fragment in a workspace file."
    schema = {
        "type": "object",
        "required": ["path", "old", "new"],
        "properties": {
            "path": {"type": "string", "description": "File path without :line ranges"},
            "old": {"type": "string", "description": "Exact existing source text"},
            "new": {"type": "string", "description": "Replacement source text"},
        },
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path = re.sub(r":\d+(?:-\d+)?$", "", str(arguments.get("path", "")))
        old = arguments.get("old")
        new = arguments.get("new")
        if not isinstance(old, str) or not isinstance(new, str) or not old:
            return ToolResult(False, "non-empty old text and new text are required")
        if len(old.encode()) + len(new.encode()) > 100_000:
            return ToolResult(False, "replacement is too large")

        if not path:
            matches = [
                candidate
                for candidate in self.workspace.iter_files()
                if not _is_test_path(self.workspace.relative(candidate))
                and old in candidate.read_text(encoding="utf-8", errors="replace")
            ]
            if len(matches) != 1:
                return ToolResult(
                    False,
                    "path is required unless old text identifies one source file; "
                    f"found {len(matches)}",
                )
            path = self.workspace.relative(matches[0])
        if _is_test_path(path):
            return ToolResult(False, "test files are read-only")

        target = self.workspace.resolve(path, must_exist=True)
        if not target.is_file() or target.stat().st_size > 2_000_000:
            return ToolResult(False, "target must be a small regular file")
        content = target.read_text(encoding="utf-8")
        occurrences = content.count(old)
        if occurrences != 1:
            preview = content[:4000]
            return ToolResult(
                False,
                f"old text must occur exactly once; found {occurrences}. "
                f"Current {path} content:\n{preview}",
            )

        target.write_text(content.replace(old, new, 1), encoding="utf-8")
        return ToolResult(True, f"replaced text in {path}", [path])


def _is_test_path(path: str) -> bool:
    parts = path.replace("\\", "/").lower().split("/")
    name = parts[-1]
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")
