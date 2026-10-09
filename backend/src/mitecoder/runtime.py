"""Runtime composition and artifact persistence."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from mitecoder import __version__
from mitecoder.agent.budget import BudgetManager
from mitecoder.agent.loop import Agent
from mitecoder.config.fingerprint import run_fingerprint
from mitecoder.config.schema import Config
from mitecoder.metrics.collector import MetricsCollector, peak_rss_mb
from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.context_builder import ContextBuilder
from mitecoder.retrieval.factory import create_retriever
from mitecoder.tools.apply_patch import ApplyPatchTool
from mitecoder.tools.file_tools import ListFilesTool, ReadFileTool, SearchCodeTool
from mitecoder.tools.git_diff import GitDiffTool
from mitecoder.tools.registry import ToolRegistry
from mitecoder.tools.replace_text import ReplaceTextTool
from mitecoder.tools.run_tests import RunTestsTool
from mitecoder.tools.write_file import WriteFileTool


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def build_tools(workspace: Workspace, config: Config) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in (
        ListFilesTool(workspace),
        SearchCodeTool(workspace),
        ReadFileTool(workspace),
        ReplaceTextTool(workspace),
        WriteFileTool(workspace),
        ApplyPatchTool(workspace),
        RunTestsTool(workspace, config.testing.commands, config.testing.timeout_seconds),
        GitDiffTool(workspace),
    ):
        registry.register(tool)
    return registry


def run_agent(
    task: str, workspace: Workspace, config: Config, backend, *, write_artifacts: bool = True
):
    metrics = MetricsCollector()
    agent = Agent(
        backend,
        create_retriever(config.retrieval),
        build_tools(workspace, config),
        BudgetManager(config.agent),
        metrics,
        ContextBuilder(config.retrieval.max_context_tokens),
        config.inference.max_output_tokens,
    )
    result = agent.run(task, workspace)
    artifact = None
    if write_artifacts:
        model_sha = str(getattr(backend, "model_sha256", "unverified"))
        run_id = run_fingerprint(
            config.as_dict(), model_sha, __version__, git_commit(workspace.root)
        )[:16]
        artifact = (
            Path(config.runtime.artifact_dir)
            / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')}_{run_id}"
        )
        artifact.mkdir(parents=True, exist_ok=False)
        (artifact / "config.json").write_text(
            json.dumps(config.as_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
        metrics.write_jsonl(artifact / "events.jsonl")
        result_data = result.as_dict() | {
            "peak_rss_mb": peak_rss_mb(),
            "run_id": run_id,
            "model_sha256": model_sha,
        }
        (artifact / "result.json").write_text(
            json.dumps(result_data, indent=2, sort_keys=True), encoding="utf-8"
        )
        diff = build_tools(workspace, config).get("git_diff").execute({}).output
        (artifact / "final.diff").write_text(diff, encoding="utf-8")
    return result, artifact
