from __future__ import annotations

from pathlib import Path

import pytest

from mitecoder.benchmark import load_tasks, run_benchmark
from mitecoder.cli import _smoke_backend
from mitecoder.config.schema import Config

SUITE = Path(__file__).parents[1] / "benchmarks" / "microswe"


def test_unknown_task_filter_is_rejected() -> None:
    with pytest.raises(ValueError, match="no benchmark tasks matched"):
        load_tasks(SUITE, "does-not-exist")


def test_deterministic_smoke_backend_solves_one_fixture() -> None:
    results = run_benchmark(SUITE, Config(), _smoke_backend, "missing-function-001")

    assert len(results) == 1
    assert results[0].status == "COMPLETED"
    assert results[0].reason == "tests_passed"
