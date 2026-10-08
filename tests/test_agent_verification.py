from __future__ import annotations

from pathlib import Path

from mitecoder.config.schema import Config
from mitecoder.config.schema import TestingConfig as RuntimeTestingConfig
from mitecoder.inference.scripted_backend import ScriptedInferenceBackend
from mitecoder.repository.workspace import Workspace
from mitecoder.runtime import run_agent


def test_successful_edit_is_verified_automatically(tmp_path: Path) -> None:
    (tmp_path / "calculator.py").write_text(
        "def add(left, right):\n    return left - right\n", encoding="utf-8"
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_calculator.py").write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    backend = ScriptedInferenceBackend(
        [
            {"action": "run_tests", "arguments": {}, "summary": "establish baseline"},
            {
                "action": "replace_text",
                "arguments": {"old": "left - right", "new": "left + right"},
                "summary": "fix addition",
            },
        ]
    )

    result, _ = run_agent(
        "Fix the failing test", Workspace(tmp_path), Config(), backend, write_artifacts=False
    )

    assert result.status == "COMPLETED"
    assert result.reason == "tests_passed"
    assert result.verification_passed is True
    assert "left + right" in (tmp_path / "calculator.py").read_text(encoding="utf-8")


def test_inference_failure_returns_an_auditable_result(tmp_path: Path) -> None:
    backend = ScriptedInferenceBackend([])

    result, _ = run_agent(
        "Inspect the repository", Workspace(tmp_path), Config(), backend, write_artifacts=False
    )

    assert result.status == "FAILED"
    assert result.reason == "inference_error"
    assert result.llm_calls == 1
    assert "responses exhausted" in result.summary


def test_question_can_be_answered_without_mutating_or_running_tests(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("The service listens on port 8765.\n", encoding="utf-8")
    backend = ScriptedInferenceBackend(
        [
            {
                "action": "answer",
                "arguments": {"text": "The configured service port is 8765."},
                "summary": "answer from workspace context",
            }
        ]
    )

    result, _ = run_agent(
        "Which port does the service use?",
        Workspace(tmp_path),
        Config(),
        backend,
        write_artifacts=False,
    )

    assert result.status == "COMPLETED"
    assert result.reason == "answered"
    assert result.summary == "The configured service port is 8765."
    assert result.tool_calls == 0
    assert result.verification_passed is None


def test_answer_cannot_bypass_verification_after_a_mutation(tmp_path: Path) -> None:
    (tmp_path / "value.py").write_text("value = 1\n", encoding="utf-8")
    config = Config(testing=RuntimeTestingConfig(commands=('python -c "raise SystemExit(1)"',)))
    backend = ScriptedInferenceBackend(
        [
            {
                "action": "replace_text",
                "arguments": {"path": "value.py", "old": "value = 1", "new": "value = 2"},
                "summary": "change value",
            },
            {
                "action": "answer",
                "arguments": {"text": "Done"},
                "summary": "attempt to bypass checks",
            },
        ]
    )

    result, _ = run_agent(
        "Change the value", Workspace(tmp_path), config, backend, write_artifacts=False
    )

    assert result.status != "COMPLETED"
    assert result.reason == "inference_error"
    assert (tmp_path / "value.py").read_text(encoding="utf-8") == "value = 2\n"
