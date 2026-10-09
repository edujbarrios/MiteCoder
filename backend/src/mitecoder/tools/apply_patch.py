"""Validated unified-diff application."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from mitecoder.repository.workspace import Workspace
from mitecoder.subprocess_utils import combined_output, run_text
from mitecoder.tools.base import Tool, ToolResult

HEADER = re.compile(r"^(?:---|\+\+\+)\s+(?:[ab]/)?([^\t\n]+)", re.MULTILINE)


class ApplyPatchTool(Tool):
    name = "apply_patch"
    description = "Validate and apply a unified diff within the workspace."
    schema = {"type": "object", "required": ["patch"], "properties": {"patch": {"type": "string"}}}

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        patch = arguments.get("patch")
        if not isinstance(patch, str) or not patch.startswith("--- ") or "\n+++ " not in patch:
            return ToolResult(False, "malformed unified diff")
        if "GIT binary patch" in patch or len(patch.encode()) > 500_000:
            return ToolResult(False, "binary or oversized patches are forbidden")
        paths = []
        try:
            for raw in HEADER.findall(patch):
                path = raw.strip()
                if path == "/dev/null":
                    continue
                self.workspace.resolve(path)
                parts = path.replace("\\", "/").lower().split("/")
                name = parts[-1]
                if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
                    return ToolResult(False, "test files are read-only")
                paths.append(path)
        except (OSError, ValueError) as exc:
            return ToolResult(False, str(exc))
        if not paths:
            return ToolResult(False, "patch contains no workspace paths")
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".diff", encoding="utf-8", delete=False
            ) as handle:
                handle.write(patch)
                temp_path = Path(handle.name)
            check = run_text(
                ["git", "apply", "--check", "--", str(temp_path)],
                cwd=self.workspace.root,
                capture_output=True,
                timeout=10,
                check=False,
            )
            if check.returncode:
                return ToolResult(False, combined_output(check).strip())
            applied = run_text(
                ["git", "apply", "--", str(temp_path)],
                cwd=self.workspace.root,
                capture_output=True,
                timeout=10,
                check=False,
            )
            if applied.returncode:
                return ToolResult(False, combined_output(applied).strip())
            diff = run_text(
                ["git", "diff", "--no-ext-diff"],
                cwd=self.workspace.root,
                capture_output=True,
                timeout=10,
                check=False,
            )
            return ToolResult(True, combined_output(diff)[-50_000:], sorted(set(paths)))
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
