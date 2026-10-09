"""Git diff command."""

import subprocess
from typing import Any

from mitecoder.repository.workspace import Workspace
from mitecoder.subprocess_utils import combined_output, run_text
from mitecoder.tools.base import Tool, ToolResult


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show the current workspace diff."
    schema = {"type": "object", "properties": {}}

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            completed = run_text(
                ["git", "diff", "--no-ext-diff"],
                cwd=self.workspace.root,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ToolResult(False, f"git diff unavailable: {exc}")
        return ToolResult(
            completed.returncode == 0, combined_output(completed)[-50_000:]
        )
