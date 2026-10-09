from __future__ import annotations

from pathlib import Path

from mitecoder.inference.model_manifest import load_manifest
from mitecoder_cli.cli import _model_manifest_path

ROOT = Path(__file__).parents[1]


def test_packaged_manifest_matches_development_manifest() -> None:
    development = load_manifest(ROOT / "models" / "manifest.yaml")
    packaged = load_manifest(ROOT / "backend" / "src" / "mitecoder" / "data" / "models.yaml")

    assert packaged == development


def test_packaged_manifest_is_used_outside_checkout(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    manifest = _model_manifest_path()

    assert manifest.name == "models.yaml"
    assert load_manifest(manifest)
