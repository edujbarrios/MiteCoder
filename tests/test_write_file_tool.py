from __future__ import annotations

from pathlib import Path

from mitecoder.repository.workspace import Workspace
from mitecoder.tools.write_file import WriteFileTool


def test_writes_complete_source_file(tmp_path: Path) -> None:
    source = tmp_path / "bounds.py"
    source.write_text('"""Boundary helpers."""\n', encoding="utf-8")

    result = WriteFileTool(Workspace(tmp_path)).execute(
        {"path": "bounds.py", "content": "def clamp(value, low, high):\n    return value\n"}
    )

    assert result.success
    assert "def clamp" in source.read_text(encoding="utf-8")


def test_does_not_write_tests(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    target = tests / "test_value.py"
    target.write_text("assert False\n", encoding="utf-8")

    result = WriteFileTool(Workspace(tmp_path)).execute(
        {"path": "tests/test_value.py", "content": "assert True\n"}
    )

    assert not result.success
    assert target.read_text(encoding="utf-8") == "assert False\n"


def test_does_not_create_unrelated_files(tmp_path: Path) -> None:
    result = WriteFileTool(Workspace(tmp_path)).execute(
        {"path": "invented.py", "content": "value = 1\n"}
    )

    assert not result.success
    assert not (tmp_path / "invented.py").exists()
