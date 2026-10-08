from __future__ import annotations

import json
from pathlib import Path

from mitecoder.config.schema import Config, RuntimeConfig
from mitecoder.inference.scripted_backend import ScriptedInferenceBackend
from mitecoder.repository.workspace import Workspace
from mitecoder.runtime import run_agent


def test_artifacts_are_unique_and_record_backend_fingerprint(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    artifact_root = tmp_path / "runs"
    config = Config(runtime=RuntimeConfig(artifact_dir=str(artifact_root)))

    _, first = run_agent("inspect", Workspace(repository), config, ScriptedInferenceBackend([]))
    _, second = run_agent("inspect", Workspace(repository), config, ScriptedInferenceBackend([]))

    assert first is not None and second is not None
    assert first != second
    first_result = json.loads((first / "result.json").read_text(encoding="utf-8"))
    assert first_result["model_sha256"] == "scripted"
