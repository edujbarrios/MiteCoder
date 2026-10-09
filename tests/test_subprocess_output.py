"""Cross-platform regression tests for subprocess text capture."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import mitecoder.repository.scanner as scanner
import mitecoder.runtime as runtime
import mitecoder.tools.git_diff as git_diff
from mitecoder.repository.workspace import Workspace
from mitecoder.subprocess_utils import combined_output, run_text
from mitecoder.tools.run_tests import RunTestsTool


def test_run_text_handles_utf8_and_undecodable_bytes_in_both_streams() -> None:
    completed = run_text(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(bytes([0xe2, 0x82, 0xac, 0x8f])); "
            "sys.stderr.buffer.write(bytes([0x8f]))",
        ],
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0
    assert completed.stdout == "\u20ac\ufffd"
    assert completed.stderr == "\ufffd"


def test_combined_output_accepts_missing_streams() -> None:
    assert combined_output(subprocess.CompletedProcess(["cmd"], 0, None, "message")) == "message"
    assert combined_output(subprocess.CompletedProcess(["cmd"], 0, "message", None)) == "message"
    assert combined_output(subprocess.CompletedProcess(["cmd"], 0, None, None)) == ""


def test_run_tests_tool_captures_invalid_bytes_without_crashing(tmp_path: Path) -> None:
    command = (
        'python -c "import sys; sys.stdout.buffer.write(bytes([0x8f])); '
        'sys.stderr.buffer.write(bytes([0x8f]))"'
    )

    result = RunTestsTool(Workspace(tmp_path), (command,)).execute({})

    assert result.success, result.output
    assert result.metadata["returncode"] == 0
    assert result.output == "\ufffd\ufffd"


def test_git_diff_reports_failure_when_stdout_is_none(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(["git", "diff"], 128, None, "fatal: git failed")

    monkeypatch.setattr(git_diff, "run_text", fake_run)

    result = git_diff.GitDiffTool(Workspace(tmp_path)).execute({})

    assert not result.success
    assert result.output == "fatal: git failed"


def test_git_commit_handles_unavailable_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runtime,
        "run_text",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(["git"], 0, None, None),
    )

    assert runtime.git_commit(tmp_path) == "uncommitted"


def test_inspection_handles_unavailable_git_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        scanner,
        "run_text",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(["git"], 0, None, None),
    )

    assert scanner.inspect_workspace(Workspace(tmp_path)).git_status == "clean"
