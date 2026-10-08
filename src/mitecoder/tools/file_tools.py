"""Read-only workspace commands."""

from __future__ import annotations

import re
from typing import Any

from mitecoder.repository.content import readable_text
from mitecoder.repository.workspace import Workspace
from mitecoder.tools.base import Tool, ToolResult


class ListFilesTool(Tool):
    name = "list_files"
    description = "List files in the selected workspace."
    schema = {"type": "object", "properties": {"limit": {"type": "integer"}}}

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        limit = max(1, min(int(arguments.get("limit", 200)), 1000))
        paths = [self.workspace.relative(path) for path in self.workspace.iter_files()[:limit]]
        return ToolResult(True, "\n".join(paths), metadata={"count": len(paths)})


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a bounded range from a workspace file or notebook cells."
    schema = {
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer"},
            "end_line": {"type": "integer"},
        },
    }

    def __init__(self, workspace: Workspace, max_lines: int = 400) -> None:
        self.workspace, self.max_lines = workspace, max_lines

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path = str(arguments.get("path", ""))
        start = max(1, int(arguments.get("start_line", 1)))
        end = min(
            int(arguments.get("end_line", start + self.max_lines - 1)), start + self.max_lines - 1
        )
        target = self.workspace.resolve(path, must_exist=True)
        lines = readable_text(target).splitlines()
        output = "\n".join(f"{i}: {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1))
        return ToolResult(True, output)


class SearchCodeTool(Tool):
    name = "search_code"
    description = "Search text files with a literal query."
    schema = {
        "type": "object",
        "required": ["query"],
        "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", ""))
        if not query or len(query) > 300:
            return ToolResult(False, "query must contain 1-300 characters")
        limit = max(1, min(int(arguments.get("limit", 50)), 200))
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        matches: list[str] = []
        for path in self.workspace.iter_files():
            try:
                for line_number, line in enumerate(readable_text(path).splitlines(), 1):
                    if pattern.search(line):
                        matches.append(
                            f"{self.workspace.relative(path)}:{line_number}:{line[:240]}"
                        )
                        if len(matches) >= limit:
                            return ToolResult(
                                True, "\n".join(matches), metadata={"count": len(matches)}
                            )
            except OSError:
                continue
        return ToolResult(True, "\n".join(matches), metadata={"count": len(matches)})
