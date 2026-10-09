"""Bounded source-file writer for complete small-file rewrites."""

from __future__ import annotations

from typing import Any

from mitecoder.repository.workspace import Workspace
from mitecoder.tools.base import Tool, ToolResult
from mitecoder.tools.replace_text import _is_test_path


class WriteFileTool(Tool):
    name = "write_file"
    description = "Rewrite one existing small source file completely; test files are read-only."
    schema = {
        "type": "object",
        "required": ["path", "content"],
        "properties": {
            "path": {"type": "string", "description": "Relative source file path"},
            "content": {"type": "string", "description": "Complete new file content"},
        },
    }

    def __init__(self, workspace: Workspace, max_bytes: int = 100_000) -> None:
        self.workspace = workspace
        self.max_bytes = max_bytes

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path = str(arguments.get("path", ""))
        content = arguments.get("content")
        if not path or not isinstance(content, str):
            return ToolResult(False, "path and complete content are required")
        if _is_test_path(path):
            return ToolResult(False, "test files are read-only")
        if len(content.encode("utf-8")) > self.max_bytes:
            return ToolResult(False, "content is too large")
        try:
            target = self.workspace.resolve(path, must_exist=True)
        except FileNotFoundError:
            return ToolResult(False, "target source file does not exist")
        if not target.is_file() or target.stat().st_size > 2_000_000:
            return ToolResult(False, "target must be a small regular file")
        if not target.parent.is_dir():
            return ToolResult(False, "parent directory does not exist")
        target.write_text(content, encoding="utf-8")
        return ToolResult(True, f"wrote {path}", [path])
