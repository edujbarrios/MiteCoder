"""Inference backend factory."""

from pathlib import Path
from typing import Any

from mitecoder.config.schema import InferenceConfig
from mitecoder.inference.llama_cpp_backend import LlamaCppBackend
from mitecoder.inference.scripted_backend import ScriptedInferenceBackend


def create_backend(
    config: InferenceConfig,
    model_path: Path | None = None,
    scripted_responses: list[Any] | None = None,
):
    if config.backend == "scripted":
        return ScriptedInferenceBackend(scripted_responses or [])
    if config.backend == "llama_cpp":
        if model_path is None:
            model_path = Path("models") / f"{config.model}.gguf"
        return LlamaCppBackend(model_path, config)
    raise ValueError(f"unknown inference backend: {config.backend}")
