"""Model manifest parsing and local SHA256 verification."""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.request import Request, urlopen

import yaml

from mitecoder.exceptions import ModelVerificationError


@dataclass(frozen=True)
class ModelManifestEntry:
    identifier: str
    family: str
    parameters: str
    format: str
    quantization: str
    filename: str
    sha256: str | None
    context_length: int
    source: str
    upstream_license: str
    recommended_profile: str


def load_manifest(path: str | Path) -> dict[str, ModelManifestEntry]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    models = data.get("models", {}) if isinstance(data, dict) else {}
    if not isinstance(models, dict):
        raise ModelVerificationError("manifest models must be a mapping")
    entries: dict[str, ModelManifestEntry] = {}
    for identifier, raw in models.items():
        if not isinstance(raw, dict):
            raise ModelVerificationError(f"invalid manifest entry: {identifier}")
        try:
            entries[identifier] = ModelManifestEntry(identifier=identifier, **raw)
        except TypeError as exc:
            raise ModelVerificationError(f"invalid manifest entry {identifier}: {exc}") from exc
    return entries


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(entry: ModelManifestEntry, model_dir: str | Path) -> tuple[Path, str]:
    path = Path(model_dir) / entry.filename
    if not path.is_file() or not path.stat().st_size:
        raise ModelVerificationError(f"local model not found: {path}")
    if path.suffix.lower() != ".gguf" or entry.format.lower() != "gguf":
        raise ModelVerificationError("model format is not compatible with GGUF")
    actual = sha256_file(path)
    if not entry.sha256:
        raise ModelVerificationError("manifest SHA256 is unresolved; verification cannot succeed")
    if actual.lower() != entry.sha256.lower():
        raise ModelVerificationError(f"SHA256 mismatch for {path.name}")
    return path, actual


def model_download_url(entry: ModelManifestEntry) -> str:
    return f"{entry.source.rstrip('/')}/resolve/main/{entry.filename}?download=true"


def download_model(
    entry: ModelManifestEntry,
    model_dir: str | Path,
    *,
    force: bool = False,
    opener: Callable[..., BinaryIO] = urlopen,
) -> tuple[Path, str]:
    """Download one manifest model, verify it, and atomically install it."""
    destination_dir = Path(model_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / entry.filename
    if destination.exists() and not force:
        try:
            return verify_model(entry, destination_dir)
        except ModelVerificationError as exc:
            raise ModelVerificationError(
                f"{destination} already exists but is not valid; use --force to replace it"
            ) from exc

    temporary = destination.with_name(f".{destination.name}.part")
    request = Request(model_download_url(entry), headers={"User-Agent": "MiteCoder/0.1"})
    digest = hashlib.sha256()
    downloaded = 0
    try:
        with opener(request, timeout=60) as response, temporary.open("wb") as output:
            total = int(response.headers.get("Content-Length", "0"))
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 / total
                    print(
                        f"\rDownloading {entry.identifier}: {percent:5.1f}% "
                        f"({downloaded / 1024 / 1024:.1f} MiB)",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )
        if downloaded:
            print(file=sys.stderr)
        actual = digest.hexdigest()
        if not entry.sha256 or actual.lower() != entry.sha256.lower():
            raise ModelVerificationError(f"SHA256 mismatch for downloaded {entry.filename}")
        temporary.replace(destination)
        return destination, actual
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
