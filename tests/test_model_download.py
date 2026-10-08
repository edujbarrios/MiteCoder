from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest

from mitecoder.exceptions import ModelVerificationError
from mitecoder.inference.model_manifest import ModelManifestEntry, download_model


class Response(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}


def entry_for(content: bytes) -> ModelManifestEntry:
    return ModelManifestEntry(
        identifier="tiny-test",
        family="test",
        parameters="1",
        format="gguf",
        quantization="Q4",
        filename="tiny.gguf",
        sha256=hashlib.sha256(content).hexdigest(),
        context_length=128,
        source="https://example.invalid/models/tiny",
        upstream_license="Apache-2.0",
        recommended_profile="test",
    )


def test_download_model_verifies_and_installs_atomically(tmp_path: Path) -> None:
    content = b"GGUF test content"

    path, digest = download_model(
        entry_for(content), tmp_path, opener=lambda *_args, **_kwargs: Response(content)
    )

    assert path.read_bytes() == content
    assert digest == hashlib.sha256(content).hexdigest()
    assert not (tmp_path / ".tiny.gguf.part").exists()


def test_download_model_removes_partial_file_after_checksum_failure(tmp_path: Path) -> None:
    content = b"expected"

    with pytest.raises(ModelVerificationError, match="SHA256 mismatch"):
        download_model(
            entry_for(content),
            tmp_path,
            opener=lambda *_args, **_kwargs: Response(b"corrupt"),
        )

    assert not (tmp_path / "tiny.gguf").exists()
    assert not (tmp_path / ".tiny.gguf.part").exists()
