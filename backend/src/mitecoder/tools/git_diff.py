"""Git diff command."""

import subprocess
from typing import Any

from mitecoder.repository.workspace import Workspace
from mitecoder.tools.base import Tool, ToolResult


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show the current workspace diff."
    schema = {"type": "object", "properties": {}}

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        completed = subprocess.run(
            ["git", "diff", "--no-ext-diff"],
            cwd=self.workspace.root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return ToolResult(
            completed.returncode == 0, (completed.stdout + completed.stderr)[-50_000:]
        )
