"""Inference strategy protocol and typed requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InferenceRequest:
    prompt: str
    max_tokens: int
    system_prompt: str | None = None


@dataclass(frozen=True)
class InferenceResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    time_to_first_token_ms: float | None = None


class InferenceBackend(Protocol):
    def generate(self, request: InferenceRequest) -> InferenceResponse: ...
