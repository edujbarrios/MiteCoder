"""Deterministic backend for tests and offline demonstrations."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from typing import Any

from mitecoder.inference.base import InferenceRequest, InferenceResponse


class ScriptedInferenceBackend:
    model_sha256 = "scripted"

    def __init__(self, responses: Iterable[str | dict[str, Any]]) -> None:
        self._responses = deque(
            json.dumps(item) if isinstance(item, dict) else item for item in responses
        )

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        if not self._responses:
            raise RuntimeError("scripted inference responses exhausted")
        text = self._responses.popleft()
        return InferenceResponse(text, len(request.prompt) // 4, len(text) // 4)
