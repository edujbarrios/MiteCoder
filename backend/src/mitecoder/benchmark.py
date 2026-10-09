"""Small isolated MicroSWE benchmark runner."""

from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from mitecoder.config.schema import Config
from mitecoder.repository.workspace import Workspace
from mitecoder.runtime import run_agent


@dataclass
class BenchmarkResult:
    task: str
    status: str
    reason: str
    wall_seconds: float
    steps: int
    input_tokens: int
    output_tokens: int


def load_tasks(root: Path, task_filter: str | None = None) -> list[dict]:
    manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
    tasks = manifest.get("tasks", [])
    selected = [task for task in tasks if not task_filter or task_filter in task["id"]]
    if task_filter and not selected:
        raise ValueError(f"no benchmark tasks matched filter: {task_filter}")
    return selected


def run_benchmark(
    root: Path, config: Config, backend_factory, task_filter: str | None = None
) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for task in load_tasks(root, task_filter):
        with tempfile.TemporaryDirectory(prefix="mitecoder-bench-") as temp:
            source = root / "fixtures" / task["fixture"]
            target = Path(temp) / "repo"
            shutil.copytree(source, target)
            started = time.monotonic()
            result, _ = run_agent(
                task["description"],
                Workspace(target),
                config,
                backend_factory(task),
                write_artifacts=False,
            )
            results.append(
                BenchmarkResult(
                    task["id"],
                    result.status,
                    result.reason,
                    time.monotonic() - started,
                    result.steps,
                    result.input_tokens,
                    result.output_tokens,
                )
            )
    return results


def export_results(results: list[BenchmarkResult], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    data = [asdict(result) for result in results]
    (output / "results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(data[0]) if data else BenchmarkResult.__annotations__
        )
        writer.writeheader()
        writer.writerows(data)
