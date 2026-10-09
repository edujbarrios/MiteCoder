"""MiteCoder command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mitecoder import __version__
from mitecoder.benchmark import export_results, run_benchmark
from mitecoder.config.loader import load_config
from mitecoder.env import environment_report
from mitecoder.exceptions import MiteCoderError
from mitecoder.inference.factory import create_backend
from mitecoder.inference.model_manifest import (
    download_model,
    load_manifest,
    packaged_manifest_path,
    verify_model,
)
from mitecoder.inference.scripted_backend import ScriptedInferenceBackend
from mitecoder.repository.scanner import inspect_workspace
from mitecoder.repository.workspace import Workspace
from mitecoder.runtime import run_agent
from mitecoder.web.server import serve

_SMOKE_FIXES = {
    "parser-boundary-001": (
        "parser.py",
        "def parse_integer(text: str) -> int:\n    return int(text)\n",
    ),
    "missing-function-001": (
        "bounds.py",
        "def clamp(value: int, lower: int, upper: int) -> int:\n"
        "    return max(lower, min(value, upper))\n",
    ),
    "off-by-one-001": (
        "chunks.py",
        '"""Boundary helpers."""\n\n'
        "def chunks(values: list[int], size: int) -> list[list[int]]:\n"
        "    return [values[i:i + size] for i in range(0, len(values), size)]\n",
    ),
    "invalid-validation-001": (
        "users.py",
        "def valid_username(name: str) -> bool:\n    return 0 < len(name) <= 12\n",
    ),
    "incorrect-sort-001": (
        "ranking.py",
        "def rank(records: list[dict]) -> list[dict]:\n"
        '    return sorted(records, key=lambda item: (-item["score"], item["name"]))\n',
    ),
    "state-management-001": (
        "counter.py",
        "class Counter:\n"
        "    def __init__(self) -> None:\n        self.value = 0\n\n"
        "    def increment(self) -> None:\n        self.value += 1\n\n"
        "    def reset(self) -> None:\n        self.value = 0\n",
    ),
}


def _smoke_backend(task: dict[str, object]) -> ScriptedInferenceBackend:
    task_id = str(task["id"])
    try:
        path, content = _SMOKE_FIXES[task_id]
    except KeyError as exc:
        raise MiteCoderError(f"no deterministic smoke action for task: {task_id}") from exc
    return ScriptedInferenceBackend(
        [
            {
                "action": "write_file",
                "arguments": {"path": path, "content": content},
                "summary": "apply deterministic framework smoke fix",
            }
        ]
    )


def _model_manifest_path() -> Path:
    development_manifest = Path("models/manifest.yaml")
    if development_manifest.is_file():
        return development_manifest
    return packaged_manifest_path()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="mitecoder", description="Offline, CPU-first coding agent for Small Language Models"
    )
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="inspect a code folder without an LLM")
    inspect.add_argument("workspace")
    env = commands.add_parser("env", help="report local environment metadata")
    env.add_argument("--json", action="store_true")
    commands.add_parser("models", help="list supported model metadata")
    verify = commands.add_parser("verify-model", help="verify a local model")
    verify.add_argument("model")
    verify.add_argument("--model-dir", default="models")
    download = commands.add_parser("download-model", help="download and verify a supported model")
    download.add_argument("model")
    download.add_argument("--model-dir", default="models")
    download.add_argument("--force", action="store_true", help="replace an invalid existing file")
    run = commands.add_parser("run", help="run the coding agent")
    run.add_argument("--repo", "--workspace", dest="repo", required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--config", required=True)
    run.add_argument("--model-path")
    run.add_argument(
        "--scripted", type=Path, help="JSON file of scripted actions for deterministic testing"
    )
    bench = commands.add_parser("benchmark", help="run isolated MicroSWE tasks")
    bench.add_argument("--suite", choices=["microswe"], default="microswe")
    bench.add_argument("--config", required=True)
    bench.add_argument("--task")
    bench.add_argument("--output", default="benchmark-results")
    bench.add_argument(
        "--model-path", type=Path, help="run the benchmark with a real local GGUF model"
    )
    web = commands.add_parser("web", help="run the offline local web interface")
    web.add_argument("--repo", "--workspace", dest="repo", required=True, type=Path)
    web.add_argument("--config", required=True, type=Path)
    web.add_argument("--model-path", required=True, type=Path)
    web.add_argument("--port", type=int, default=8765)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "inspect":
            print(json.dumps(inspect_workspace(Workspace(args.workspace)).as_dict(), indent=2))
            return 0
        if args.command == "env":
            report = environment_report()
            print(
                json.dumps(report, indent=2)
                if args.json
                else "\n".join(f"{k}: {v}" for k, v in report.items())
            )
            return 0
        manifest = _model_manifest_path()
        if args.command == "models":
            for name, entry in load_manifest(manifest).items():
                print(f"{name}\t{entry.parameters}\t{entry.quantization}\t{entry.upstream_license}")
            return 0
        if args.command == "verify-model":
            entries = load_manifest(manifest)
            if args.model not in entries:
                raise MiteCoderError(f"unknown model: {args.model}")
            path, digest = verify_model(entries[args.model], args.model_dir)
            print(f"Model ready for offline inference.\nFile: {path}\nSHA256: {digest}")
            return 0
        if args.command == "download-model":
            entries = load_manifest(manifest)
            if args.model not in entries:
                raise MiteCoderError(f"unknown model: {args.model}")
            path, digest = download_model(entries[args.model], args.model_dir, force=args.force)
            print(f"Model downloaded and verified.\nFile: {path}\nSHA256: {digest}")
            return 0
        config = load_config(args.config)
        if args.command == "web":
            serve(args.repo, args.config, args.model_path, port=args.port)
            return 0
        if args.command == "run":
            if args.scripted:
                responses = json.loads(args.scripted.read_text(encoding="utf-8"))
                backend = ScriptedInferenceBackend(responses)
            else:
                backend = create_backend(
                    config.inference, Path(args.model_path) if args.model_path else None
                )
            result, artifact = run_agent(args.task, Workspace(args.repo), config, backend)
            print(json.dumps(result.as_dict() | {"artifacts": str(artifact)}, indent=2))
            return 0 if result.status == "COMPLETED" else 1
        if args.command == "benchmark":
            if args.model_path:

                def factory(_task: dict[str, object]):
                    return create_backend(config.inference, args.model_path)
            else:
                factory = _smoke_backend

            results = run_benchmark(Path("benchmarks/microswe"), config, factory, args.task)
            export_results(results, Path(args.output))
            for item in results:
                print(
                    f"{item.task:28} {item.status:20} {item.wall_seconds:.3f}s {item.steps} steps"
                )
            return 0 if all(item.status == "COMPLETED" for item in results) else 1
    except (MiteCoderError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
