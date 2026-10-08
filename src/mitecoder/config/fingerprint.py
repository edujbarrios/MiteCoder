"""Stable configuration and run fingerprints."""

import hashlib
import json
from typing import Any


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def run_fingerprint(
    config: dict[str, Any],
    model_sha256: str,
    version: str,
    git_commit: str,
    benchmark_version: str = "",
) -> str:
    return canonical_hash(
        {
            "benchmark_version": benchmark_version,
            "config": config,
            "git_commit": git_commit,
            "model_sha256": model_sha256,
            "version": version,
        }
    )
