from __future__ import annotations

from pathlib import Path

from mitecoder.repository.workspace import Workspace
from mitecoder.tools.replace_text import ReplaceTextTool


def test_replaces_one_exact_fragment(tmp_path: Path) -> None:
    source = tmp_path / "calculator.py"
    source.write_text("return left - right\n", encoding="utf-8")

    result = ReplaceTextTool(Workspace(tmp_path)).execute(
        {"path": "calculator.py", "old": "left - right", "new": "left + right"}
    )

    assert result.success
    assert source.read_text(encoding="utf-8") == "return left + right\n"


def test_rejects_ambiguous_replacement(tmp_path: Path) -> None:
    source = tmp_path / "values.txt"
    source.write_text("same\nsame\n", encoding="utf-8")

    result = ReplaceTextTool(Workspace(tmp_path)).execute(
        {"path": "values.txt", "old": "same", "new": "other"}
    )

    assert not result.success
    assert "exactly once" in result.output
    assert source.read_text(encoding="utf-8") == "same\nsame\n"


def test_accepts_context_line_suffix(tmp_path: Path) -> None:
    source = tmp_path / "calculator.py"
    source.write_text("return left - right\n", encoding="utf-8")

    result = ReplaceTextTool(Workspace(tmp_path)).execute(
        {"path": "calculator.py:1-4", "old": "left - right", "new": "left + right"}
    )

    assert result.success
    assert source.read_text(encoding="utf-8") == "return left + right\n"


def test_infers_unique_source_path_and_protects_tests(tmp_path: Path) -> None:
    source = tmp_path / "calculator.py"
    source.write_text("return left - right\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    test_file = tests / "test_calculator.py"
    test_file.write_text("assert value == 5\n", encoding="utf-8")
    tool = ReplaceTextTool(Workspace(tmp_path))

    inferred = tool.execute({"old": "left - right", "new": "left + right"})
    protected = tool.execute({"path": "tests/test_calculator.py", "old": "5", "new": "-1"})

    assert inferred.success
    assert source.read_text(encoding="utf-8") == "return left + right\n"
    assert not protected.success
    assert test_file.read_text(encoding="utf-8") == "assert value == 5\n"
