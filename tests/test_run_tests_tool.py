from __future__ import annotations

from pathlib import Path

from mitecoder.repository.workspace import Workspace
from mitecoder.tools.run_tests import RunTestsTool, _split_command


def test_split_command_removes_windows_style_argument_quotes() -> None:
    arguments = _split_command('python -c "print(123)"')

    assert arguments == ["python", "-c", "print(123)"]


def test_pytest_command_imports_modules_from_workspace(tmp_path: Path) -> None:
    (tmp_path / "calculator.py").write_text(
        "def add(left, right):\n    return left + right\n", encoding="utf-8"
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_calculator.py").write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    result = RunTestsTool(Workspace(tmp_path), ("pytest -q",)).execute({})

    assert result.success, result.output


def test_execute_all_requires_every_configured_command_to_pass(tmp_path: Path) -> None:
    passing = "python -c \"print('first check passed')\""
    failing = 'python -c "raise SystemExit(7)"'

    result = RunTestsTool(Workspace(tmp_path), (passing, failing)).execute_all()

    assert result.success is False
    assert result.metadata == {"failed_command_index": 1, "commands_run": 2}
    assert "first check passed" in result.output


def test_execute_all_reports_all_checks(tmp_path: Path) -> None:
    command = "python -c \"print('check passed')\""

    result = RunTestsTool(Workspace(tmp_path), (command, command)).execute_all()

    assert result.success is True
    assert result.metadata == {"commands_run": 2}
