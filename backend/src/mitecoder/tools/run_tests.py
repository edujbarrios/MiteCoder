"""Run only administrator-configured test commands."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from mitecoder.repository.workspace import Workspace
from mitecoder.subprocess_utils import combined_output, run_text
from mitecoder.tools.base import Tool, ToolResult


def _split_command(command: str) -> list[str]:
    arguments = shlex.split(command, posix=sys.platform != "win32")
    if sys.platform == "win32":
        arguments = [
            argument[1:-1]
            if len(argument) >= 2 and argument[0] == argument[-1] and argument[0] in "\"'"
            else argument
            for argument in arguments
        ]
    return arguments


class RunTestsTool(Tool):
    name = "run_tests"
    description = "Run a configured test command; model-supplied commands are rejected."
    schema = {"type": "object", "properties": {"index": {"type": "integer"}}}

    def __init__(
        self, workspace: Workspace, commands: tuple[str, ...], timeout: float = 120.0
    ) -> None:
        self.workspace, self.commands, self.timeout = workspace, commands, timeout

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        if "command" in arguments:
            return ToolResult(False, "model-supplied commands are forbidden")
        index = int(arguments.get("index", 0))
        if not 0 <= index < len(self.commands):
            return ToolResult(False, "configured test command index is invalid")
        command = _split_command(self.commands[index])
        if command and Path(command[0]).stem.lower() == "pytest":
            command = [sys.executable, "-m", "pytest", *command[1:]]
            if not any(
                argument == "--rootdir" or argument.startswith("--rootdir=") for argument in command
            ):
                command.extend(("--rootdir", str(self.workspace.root)))
        try:
            # Use a fresh bytecode cache for every check. Otherwise a rapid,
            # same-sized Python edit can be masked by a timestamp-valid stale
            # .pyc file created by the previous test run.
            with tempfile.TemporaryDirectory(prefix="mitecoder-pycache-") as pycache:
                environment = os.environ.copy()
                environment["PYTHONPYCACHEPREFIX"] = pycache
                completed = run_text(
                    command,
                    cwd=self.workspace.root,
                    capture_output=True,
                    timeout=self.timeout,
                    check=False,
                    shell=False,
                    env=environment,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ToolResult(False, f"test execution failed: {exc}")
        output = combined_output(completed)[-20_000:]
        return ToolResult(
            completed.returncode == 0,
            output,
            metadata={"returncode": completed.returncode, "command_index": index},
        )

    def execute_all(self) -> ToolResult:
        """Run every operator-configured check, stopping at the first failure."""
        outputs: list[str] = []
        for index, configured_command in enumerate(self.commands):
            result = self.execute({"index": index})
            outputs.append(f"$ {configured_command}\n{result.output}".rstrip())
            if not result.success:
                return ToolResult(
                    False,
                    "\n\n".join(outputs)[-20_000:],
                    metadata={"failed_command_index": index, "commands_run": index + 1},
                )
        return ToolResult(
            True,
            "\n\n".join(outputs)[-20_000:],
            metadata={"commands_run": len(self.commands)},
        )
