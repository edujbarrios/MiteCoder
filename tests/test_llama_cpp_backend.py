from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

from mitecoder.config.schema import InferenceConfig
from mitecoder.exceptions import MiteCoderError
from mitecoder.inference.base import InferenceRequest
from mitecoder.inference.llama_cpp_backend import LlamaCppBackend


class FakeLlama:
    init_arguments: dict[str, object] = {}
    completion_arguments: dict[str, object] = {}
    response: object = {
        "choices": [{"message": {"content": '  {\n  "action": "finish"\n}  '}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }

    def __init__(self, **kwargs: object) -> None:
        type(self).init_arguments = kwargs

    def create_chat_completion(self, **kwargs: object) -> object:
        type(self).completion_arguments = kwargs
        return type(self).response


@pytest.fixture
def fake_llama_cpp(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleType("llama_cpp")
    module.Llama = FakeLlama  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "llama_cpp", module)
    FakeLlama.response = {
        "choices": [{"message": {"content": '  {\n  "action": "finish"\n}  '}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }


def model_file(tmp_path: Path) -> Path:
    path = tmp_path / "model.gguf"
    path.write_bytes(b"test model placeholder")
    return path


def test_generate_preserves_multiline_json_and_reports_usage(
    tmp_path: Path, fake_llama_cpp: None
) -> None:
    config = InferenceConfig(context_length=1024, threads=2, batch_size=16)
    backend = LlamaCppBackend(model_file(tmp_path), config)

    response = backend.generate(InferenceRequest("prompt", 64, system_prompt="system"))

    assert response.text == '{\n  "action": "finish"\n}'
    assert response.input_tokens == 11
    assert response.output_tokens == 7
    assert FakeLlama.completion_arguments == {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "prompt"},
        ],
        "max_tokens": 64,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "top_k": config.top_k,
        "response_format": {"type": "json_object"},
    }
    assert FakeLlama.init_arguments["n_ctx"] == 1024
    assert FakeLlama.init_arguments["n_threads"] == 2
    assert backend.model_sha256 == hashlib.sha256(b"test model placeholder").hexdigest()


@pytest.mark.parametrize(
    "response, message",
    [
        ({}, "contains no choices"),
        ({"choices": []}, "contains no choices"),
        ({"choices": [{}]}, "contains no message content"),
        ([], "invalid completion response"),
    ],
)
def test_generate_rejects_malformed_responses(
    tmp_path: Path,
    fake_llama_cpp: None,
    response: object,
    message: str,
) -> None:
    FakeLlama.response = response
    backend = LlamaCppBackend(model_file(tmp_path), InferenceConfig())

    with pytest.raises(MiteCoderError, match=message):
        backend.generate(InferenceRequest("prompt", 8))


def test_generate_ignores_invalid_usage_counts(tmp_path: Path, fake_llama_cpp: None) -> None:
    FakeLlama.response = {
        "choices": [{"message": {"content": "result"}}],
        "usage": {"prompt_tokens": True, "completion_tokens": -1},
    }
    backend = LlamaCppBackend(model_file(tmp_path), InferenceConfig())

    response = backend.generate(InferenceRequest("prompt", 8))

    assert response.input_tokens is None
    assert response.output_tokens is None


def test_missing_model_is_reported_before_import(tmp_path: Path) -> None:
    with pytest.raises(MiteCoderError, match="Local model not found"):
        LlamaCppBackend(tmp_path / "missing.gguf", InferenceConfig())
