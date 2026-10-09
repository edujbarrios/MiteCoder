"""Optional local llama.cpp inference backend."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mitecoder.config.schema import InferenceConfig
from mitecoder.exceptions import MiteCoderError
from mitecoder.inference.base import InferenceRequest, InferenceResponse
from mitecoder.inference.model_manifest import sha256_file


class LlamaCppBackend:
    def __init__(self, model_path: Path, config: InferenceConfig) -> None:
        if not model_path.is_file():
            raise MiteCoderError(
                "Local model not found. Run the explicit MiteCoder model setup procedure "
                "before offline execution."
            )
        self.model_sha256 = sha256_file(model_path)
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise MiteCoderError(
                "llama-cpp-python is not installed; install MiteCoder with the 'llama' extra"
            ) from exc

        try:
            self._model = Llama(
                model_path=str(model_path),
                n_ctx=config.context_length,
                n_threads=config.threads,
                n_batch=config.batch_size,
                seed=config.seed,
                use_mmap=config.mmap,
                use_mlock=config.mlock,
                verbose=False,
            )
        except Exception as exc:
            raise MiteCoderError(f"Could not load local model: {exc}") from exc
        self._config = config

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            result = self._model.create_chat_completion(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                top_k=self._config.top_k,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise MiteCoderError(f"Local inference failed: {exc}") from exc

        if not isinstance(result, Mapping):
            raise MiteCoderError("llama.cpp returned an invalid completion response")
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise MiteCoderError("llama.cpp completion response contains no choices")
        message = choices[0].get("message")
        text = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(text, str):
            raise MiteCoderError("llama.cpp completion choice contains no message content")

        usage = result.get("usage")
        usage = usage if isinstance(usage, Mapping) else {}
        return InferenceResponse(
            text.strip(),
            _optional_int(usage.get("prompt_tokens")),
            _optional_int(usage.get("completion_tokens")),
        )


def _optional_int(value: Any) -> int | None:
    """Return token counts only when the backend supplied a valid integer."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
